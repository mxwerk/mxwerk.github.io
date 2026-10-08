---
title: The harness is read from disk, never written
description: The cockpit reads the agent harness's message bus straight from the filesystem under a configured root, through one module that imports no write call.
draft: false
cites:
  - path: docs/adr/004-cross-repo-substrate-read.md
    lines: 21-55
  - path: backend/src/substrate/busReader.ts
    lines: 1-25, 143-200
  - path: backend/src/config/env.ts
    lines: 35
  - path: backend/src/index.ts
    lines: 186-189
  - path: backend/src/api/server.ts
    lines: 250-252
verified_at: 75e94b4
---

# The harness is read from disk, never written

> **TL;DR** — The loops that run the agents live in another repository and keep their state
> as append-only files: one message file per channel, a status file beside it, and marker
> files for confirmations. The cockpit reads those files directly, on every request,
> resolving the directory from one environment variable. The reader module imports only
> read functions, so no request can change the system it reads. [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

The cockpit should show how deep each channel is, what waits for the operator's
confirmation, and how old the newest message is. That state belongs to a different
repository on the same machine.

## The decision

ADR 004 reads the files in place. Copying them into the cockpit's repository would
duplicate data that changes constantly and add a sync job that can fail. An HTTP service
on the harness side would be a process to run and secure for a read on one host by one
operator, and no such service exists.

## How it works

Every path and file suffix of the bus layout is spelled out once, at the top of
`busReader.ts`. A message counts as pending until its latest status is `done` or
`dismissed`; a line that cannot be parsed counts as pending, because it cannot be shown to
be handled. Confirmation types are discovered from the directory, so a new gate appears
without a code change.

The root comes from the configuration reader and is passed in; the module never reads the
environment itself.

## What it costs

- **A dependency on another repository's layout.** A rename there breaks the reader. It is
  one file to fix, and the ADR names that breakage as the trigger to reconsider a service.
- **Whole files per request.** Each call reads every channel file completely. A comment in
  the reader records about one megabyte in total and names caching as the upgrade.
- **One staleness threshold for everything:** 24 hours, the same for a busy channel and a
  slow one ([[wiki/agent-cockpit/concepts/surface-never-silent]]).
- **Only the bus is built, and only in the backend.** The ADR also lists the event log,
  the backlog and the graph report as sources; there is a reader and a route for the bus
  alone, and no panel in the frontend fetches that route yet.

## Later changes

ADR 005 took the other route for a source that already offered an HTTP contract
([[wiki/agent-cockpit/decisions/warden-verdicts-two-sources]]).
