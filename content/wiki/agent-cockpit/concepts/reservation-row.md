---
title: The reservation row
description: A slot is held by a provisional row in the sessions table, which is later renamed to the real session, deleted, or swept at startup.
draft: false
cites:
  - path: backend/src/db/index.ts
    lines: 105-200
  - path: backend/src/dispatch/dispatch.ts
    lines: 169-210, 273-291, 459-476, 594-606, 642-650
  - path: backend/src/ingest/poller.ts
    lines: 162-178
  - path: backend/test/db.spec.ts
    lines: 145-258
verified_at: 75e94b4
---

# The reservation row

> **TL;DR** — Between "the operator clicked" and "the agent reported its session id" a
> launch has no identity yet, but it must already count against the cap. The cockpit
> represents that interval as a row in the sessions table with the id `reserve:<uuid>` and
> the status `running`. The cap, the idempotency key, resume and crash cleanup are all
> operations on that one row. [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

The session id of an agent run is only known once the process prints its first event. If
the slot were claimed at that moment, two launches started in the same second would both
pass the cap. If it were claimed in memory, a crash would leave nothing to clean up and
nothing to count.

## How it works

`reserveSlotForKey` inserts the provisional row inside the transaction that counted the
active rows. Because the row has the status `running`, the same `COUNT` that covers real
sessions covers it, with no second counter to keep in step. From there the row has four
ends:

| End | When | Effect |
|---|---|---|
| promoted | a new launch reports its first event | the row is renamed to the real session id |
| confirmed | a resumed run reports its first event | the existing session row is set to `running` and the reservation is deleted, in one transaction |
| rolled back | spawn fails, the first event never arrives, or a write fails during capture | the reservation is deleted and the slot is free |
| swept | the backend starts | every `reserve:` row is deleted |

Renaming would collide with the primary key on resume, where the real row already exists;
that is why resume confirms instead of promoting. If a resume fails after it was confirmed,
the session row is put back to `interrupted`, not deleted, because it holds the directory,
usage and event counter of the earlier run.

The liveness reconcile skips `reserve:` rows, so a reservation is not mistaken for a dead
session while its process is still starting.

## What it costs

- **The id column carries a type.** Whether a row is a reservation is decided by a string
  prefix. Each reader of the table has to know that, and four places in the code check it.
- **The sweep assumes one backend.** Deleting every reservation at startup is correct only
  if no other process is in the middle of a launch on the same file.
- **Promotion fails loudly.** A rename that matches no row throws; the comment calls a
  silent no-op there a bug.

## Later changes

The row gained the idempotency key ([[wiki/agent-cockpit/decisions/idempotent-dispatch]]). See
[[wiki/agent-cockpit/decisions/over-cap-reject]] for why there is a cap, and [[wiki/agent-cockpit/components/dispatch]] for the
launch around it.
