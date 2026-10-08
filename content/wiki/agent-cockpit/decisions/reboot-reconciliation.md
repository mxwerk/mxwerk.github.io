---
title: The database is the record, the process is only probed
description: Every stream event is written in its own transaction, and at startup every session still marked running is set to interrupted unless a probe confirms it alive.
draft: false
cites:
  - path: docs/adr/003-reboot-reconciliation-sqlite-authoritative.md
    lines: 12-39
  - path: backend/src/db/index.ts
    lines: 53-56, 90-103
  - path: backend/src/db/schema.sql
    lines: 5-26
  - path: backend/src/dispatch/dispatch.ts
    lines: 414-441, 511-560, 622-673
  - path: backend/src/index.ts
    lines: 144-153, 235-243
  - path: backend/test/reconcile.spec.ts
    lines: 52-118
verified_at: 75e94b4
---

# The database is the record, the process is only probed

> **TL;DR** — An agent process does not survive a reboot, but its session id does, and the
> session can be resumed from it. So the cockpit writes the id, the usage and the event to
> SQLite on every single stream event, in one transaction, in WAL mode. On startup it sets
> every row still marked `running` to `interrupted` unless a probe says the process is
> alive. Resume is a button, not an automatic relaunch. [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

After a crash or reboot the cockpit has to know which runs were cut off, without losing
their session id or the usage recorded so far. The process supervisor cannot answer that:
its record of transient units is in memory and is gone after the reboot it would have to
explain.

## The decision

ADR 003 makes the database authoritative and treats the running process as something to
probe, never as the record. Writes are per event, not batched, because a buffer dies with
the process and reopens the loss the decision is meant to close.

## How it works

`appendEventAndUpsertSession` appends the event row and updates the session row in one
transaction. `reconcileStartup` runs before the server accepts a request and before the
first poll: it walks the `running` rows, asks the probe, and marks the rest `interrupted`
with id and usage kept. Reservation rows left behind by a crash are swept in the same
step.

`resume` refuses a session that is not `interrupted`, checks that the recorded directory
still exists and still resolves inside the projects root
([[wiki/agent-cockpit/components/path-containment]]), and then competes for a slot like any launch
([[wiki/agent-cockpit/decisions/over-cap-reject]]). The event counter continues from the stored value.

## What it costs

- **The probe is narrower than the ADR describes.** The ADR names the terminal
  multiplexer and the service manager as the probe. The code passes a probe that only
  knows the runs this process started, and that set is empty at boot. So every `running`
  row becomes `interrupted` on any restart, including a restart that a still-living
  process would have survived.
- **A clean shutdown therefore kills what it started.** The signal handler sends SIGKILL
  to each dispatched process group, so nothing keeps running untracked.
- **A crash of the backend is not covered.** No handler runs, the children keep running,
  and the next boot marks them interrupted while they are alive.
- **Usage after a resume** is the stored snapshot until the resumed stream reports a new
  one; the code does not query usage separately.

## Later changes

The shutdown kill and its registry of process ids were added because a detached child
survived the backend's own termination. A later fix moved the registration from the first
event to the spawn, since a child that had not yet reported was still missed.
