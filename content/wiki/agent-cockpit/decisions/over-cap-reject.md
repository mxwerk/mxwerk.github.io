---
title: A launch over the cap is refused
description: A launch that would exceed the concurrency cap is refused with a conflict status instead of queued, and the count and the reservation happen in one transaction.
draft: false
cites:
  - path: docs/adr/002-over-cap-dispatch-policy-reject.md
    lines: 12-35
  - path: backend/src/db/index.ts
    lines: 105-163
  - path: backend/src/dispatch/dispatch.ts
    lines: 454-476
  - path: backend/src/api/server.ts
    lines: 191-198, 254-256
  - path: backend/src/config/env.ts
    lines: 42, 57-59
  - path: backend/test/db.spec.ts
    lines: 166-180
verified_at: 75e94b4
---

# A launch over the cap is refused

> **TL;DR** — All agents share one subscription and one rate limit, so only a few may run
> at once (5 by default). A launch beyond that is refused with HTTP 409 and forgotten;
> there is no queue. The check and the reservation are one database transaction, so two
> clicks at the boundary cannot both pass. The current count is served on its own route so
> the UI can show it before the operator clicks. [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

An operator can click "dispatch" faster than the shared rate limit tolerates. Three
answers were on the table: queue the extra launch, warn and launch anyway, or refuse.

## The decision

ADR 002 refuses. A queue needs a table, a worker, an order, cancellation and a way to
survive a reboot, all for one operator and about five agents, and a queued launch waits
without bound, which breaks the 10-second launch target by design. Warning and launching
anyway courts exactly the throttling the cap exists to prevent, and a run that fails
half-way has already spent tokens.

## How it works

The cap is not a counter. A reservation is a provisional row in the sessions table with
status `running` ([[wiki/agent-cockpit/concepts/reservation-row]]), so "how many are active" is one `COUNT`
over that table. `reserveSlotForKey` counts and inserts inside a single synchronous
transaction. Before it counts, the dispatch path marks every `running` row that is not one of
its own live runs as interrupted, so a dead run does not hold a slot.

A resume goes through the same gate as a new launch
([[wiki/agent-cockpit/decisions/reboot-reconciliation]]).

## What it costs

- **The operator retries by hand.** A refused launch leaves no trace in the system.
- **No order among racing launches.** Whichever transaction runs first wins.
- **The count comes from the database, not from the processes.** The ADR's second
  follow-up asked for the running units to be the source of the count. The code counts
  rows and corrects them from the set of runs this process started.
- **Only dispatched runs hold a slot at launch time.** The freshen before the count also
  flips live sessions that were started by hand and found by the poller
  ([[wiki/agent-cockpit/components/discovery-poller]]). The cap therefore limits what the cockpit launches,
  not the number of agents running on the machine.
- **Atomicity holds inside one process.** The guarantee is the synchronous transaction of
  a single Node process; a second backend on the same file is not a tested case.

What the tests show: with one slot left, exactly one of two reservations succeeds and the
final count equals the cap.

## Later changes

The reservation gained an idempotency key ([[wiki/agent-cockpit/decisions/idempotent-dispatch]]). The queue
is still deferred, and no refusal rate has been recorded that would trigger it.
