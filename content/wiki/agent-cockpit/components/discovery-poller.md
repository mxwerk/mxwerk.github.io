---
title: The discovery poller
description: Every five seconds the backend lists terminal-multiplexer sessions that run an agent, finds each one's transcript, and stores lines it has not seen.
draft: false
cites:
  - path: backend/src/ingest/poller.ts
    lines: 1-10, 56-67, 83-130, 132-147, 149-208, 212-223, 229-254, 291-324
  - path: backend/src/index.ts
    lines: 155-180, 226
  - path: backend/test/poller.spec.ts
verified_at: 75e94b4
---

# The discovery poller

> **TL;DR** — Agents that the operator started by hand, in a terminal, are not launched by
> the cockpit and still have to appear in it. A poller lists the panes of the terminal
> multiplexer, keeps those whose process tree runs the agent CLI, maps each pane's working
> directory to the transcript file the CLI writes, and stores new lines. A session it saw
> last time and does not see now is marked interrupted. [[wiki/agent-cockpit/index|↑ Wiki]]

## What it is

`pollOnce` and its production dependencies in the backend's ingest module. It is the
second way a session enters the store, next to [[wiki/agent-cockpit/components/dispatch]], and it uses the
same write path and the same liveness rule.

## How it works

1. **List.** One call returns every pane with its process id and working directory.
2. **Filter.** For each pane the process listing is read and the tree below the pane's
   process is walked; the pane counts if any process in it is named like the agent CLI.
   Only the first such pane of a multiplexer session is kept.
3. **Resolve.** The CLI stores transcripts in a directory named after the working
   directory with the separators replaced. The newest file there is taken.
4. **Ingest.** Lines are grouped by session id. The session row's event counter is the
   cursor: lines up to it were stored before and are skipped.
5. **Reconcile.** Every `running` row whose id was not seen in this cycle, and which
   dispatch does not hold as live, is set to `interrupted`.

A pane that runs an agent but has no transcript file to resolve is stored as
`untracked:<directory>` and shown, flagged ([[wiki/agent-cockpit/concepts/surface-never-silent]]).

External commands are called with an argument array and a 5-second limit, without a
shell.

## What it costs / limits

- **One missed cycle flips a live session.** If a transcript cannot be read once, the
  session is marked interrupted. Finding it again does not undo that by itself: the row
  goes back to `running` only when a line beyond the cursor is ingested, so a quiet
  session stays interrupted. A comment in the code names a grace count as the upgrade.
- **A dispatch flips discovered sessions too.** Before it counts free slots, dispatch
  marks every `running` row it did not start itself as interrupted. That includes live
  sessions this poller found. They therefore do not hold a slot against a launch, the
  slot count shown between two launches is higher than the one a launch uses, and a
  hand-started session can appear interrupted while it runs.
- **The whole transcript is read every cycle.** The cursor avoids duplicate rows, not the
  read.
- **One pane per multiplexer session, newest file per directory.** Two sessions in the same directory are told apart only if both
  appear in the newest transcript; an older file's session is not ingested.
- **Matching is by process name.** Any process whose name contains the CLI's name makes
  its pane count.

## Later changes

The tick was wrapped so that an exception is logged and the next cycle retries; before
that, a database fault during a poll ended the process and the HTTP server with it.
