---
title: A dispatch that cannot succeed gives up
description: A dispatch obligation ends either on a refusal the adapter calls permanent or once it is older than a configured age, and ending it fails the work order.
draft: false
cites:
  - path: docs/adr/013-a-dispatch-that-cannot-succeed-gives-up.md
    lines: 13-47, 53-88, 91-113, 117-138, 144-157, 172-190
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/PermanentDispatchFailure.java
    lines: 14-38
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/AgentDispatchPort.java
    lines: 45-61
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/CockpitAgentDispatch.java
    lines: 42-55, 93, 104-136
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainer.java
    lines: 42-57, 109-111, 144-181, 186-189, 214-244
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutbox.java
    lines: 14-17
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/FailureReason.java
    lines: 11-30
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrder.java
    lines: 201-206, 294-319
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/WorkOrderModuleConfiguration.java
    lines: 58-68, 82-90
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/DispatchOutboxDrainerSchedule.java
    lines: 37-39
  - path: src/main/resources/db/migration/V3__create_work_orders.sql
    lines: 37-38, 46-49
  - path: src/main/resources/db/migration/V5__create_dispatch_outbox.sql
    lines: 35-38
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainerTest.java
    lines: 282-332, 348-487
  - path: src/test/java/dev/…/agentworkorders/modules/agent/infrastructure/CockpitAgentDispatchTest.java
    lines: 117-219
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrderTest.java
    lines: 338-396
verified_at: 262e98e
---

# A dispatch that cannot succeed gives up

> **TL;DR** — The [[wiki/agent-workorders/decisions/dispatch-outbox|dispatch outbox]] made an
> obligation durable and gave it no end, so a refusal that would never change
> was retried on every pass while its work order stayed `ASSIGNED` and held a
> WIP slot. ADR 013 adds two endings: the adapter may throw
> `PermanentDispatchFailure`, which ends the obligation on the first
> occurrence, and any other failure ends it once the obligation is older than
> a configured age. Either ending moves an `ASSIGNED` order to `FAILED` with
> the reason `DISPATCH_FAILED` and deletes the outbox row. [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

`DispatchOutboxDrainer` caught every `RuntimeException`, recorded it on the
row and left the row standing. For a receiver (agent-cockpit) that is restarting, that is the
intended behaviour. For two answers it is not: `403`, where the target
directory resolves outside the receiver's projects root, and `400`, where this
side built a body the receiver will not take. Neither changes on the next
call.

An earlier note on the drainer priced such a row as harmless: one call per
interval, no other row blocked. ADR 013 points out the cost was measured in
the wrong place. The work order stays `ASSIGNED`, `assignTo` checks the
agent's load against its WIP limit, and to the aggregate nothing failed.

Two things were missing. Nothing could tell a permanent failure from a
transient one, since only the adapter sees an HTTP status and the drainer may
not learn HTTP ([[wiki/agent-workorders/concepts/modules-by-id]]). And the outbox had two endings
only: row removed, or row still owed.

## The decision

- **Permanence is classified by the adapter.** `AgentDispatchPort.dispatch`
  declares `PermanentDispatchFailure`. `CockpitAgentDispatch.isPermanent`
  returns true for exactly two statuses, `400` and `403`, and the handler
  puts the status, the request URI and the response body into the exception
  message. What crosses the port is the judgement, never the status code.
- **A permanent failure ends the obligation at once.** The drainer has a
  dedicated `catch (PermanentDispatchFailure ...)` ahead of the general one
  and calls `abandon` without recording a failed attempt first.
- **Everything else is bounded by age.** After a general failure the drainer
  saves the counted attempt, then asks whether `createdAt + giveUpAfter` has
  been reached. `giveUpAfter` comes from the property
  `workorder.dispatch-outbox.give-up-after` and defaults to 24 hours; a
  negative value is refused by the constructor.
- **A missing work order or project is transient.** The lookup runs inside the
  same `try`, throws `IllegalStateException`, and is bounded by the age like
  any other failure. ADR 013 gives the reason: a project can be registered
  after the obligation was written.
- **Abandoning fails the order.** `abandon` loads the order and, only if its
  status is `ASSIGNED`, calls `WorkOrder.failDispatch`, which sets
  `DISPATCH_FAILED`, stores the detail and makes the order `FAILED`. The
  outbox row is removed in the same transaction callback whatever the status
  was.
- **Running and terminal orders are left alone.** `failDispatch` requires
  `ASSIGNED`: a running order shows the dispatch arrived, a terminal one ended.
- **No migration.** `failure_reason` is `VARCHAR(20)` and its check constraint
  only ties "set" to `FAILED`; `failure_detail` is `TEXT`.

| Option | Why not |
| --- | --- |
| Dead-letter the outbox row only | Stops the retry loop but leaves the order `ASSIGNED` and the slot taken, which was the actual cost. |
| Unassign back to `OPEN` | For a `403` the next assignment sends the same project root and is refused again, in a loop; it also reuses `unassign` to report a failure. |
| A cap on attempts instead of an age | The drain interval is a property, so the same count means a different wall-clock tolerance per configuration. |
| Let the drainer infer permanence from the exception | The drainer would match on strings or HTTP types, which is the module direction broken where it is hardest to see. |

## What it costs

- **The drainer and the overdue reaper are no longer independent.** `abandon`
  writes `work_orders`. If it loses the version race it catches
  `OptimisticLockingFailureException`, logs at debug level and leaves the row
  for the next pass. A search for that exception type under `src/test` finds
  it in the reaper's tests and the work-order repository's test only, so this
  branch of the drainer has no test at this commit.
- **A wrong "permanent" is final.** The order fails and has to be placed
  again. That is why the list is two named statuses and not a rule about all
  4xx answers.
- **The default bound is a guess**: chosen, not measured, per ADR 013.
- **An order can fail for a reason its requester did not cause.**
  `FailureReason` calls `DISPATCH_FAILED` an infrastructure failure wearing a
  domain enum.

What the tests show: `DispatchOutboxDrainerTest` asserts that a permanent
refusal fails an assigned order and is asked exactly once across two drains;
that a transient failure one minute inside the bound leaves order and row in
place while one minute past it ends both; and that a running or cancelled
order keeps its status while the row is dropped. `CockpitAgentDispatchTest`
asserts `403` and `400` throw the permanent type and `409`, `501` and `502`
do not. `WorkOrderTest` asserts `failDispatch` is refused for open, running
and cancelled orders.

## Later changes

- **This amends the outbox decision.** ADR 011 argued that the drainer never
  writes `work_orders`; ADR 013 §4 narrows that to "only on abandonment". The
  interface javadoc on `DispatchOutbox` still carries the unamended sentence,
  and the column comment in the outbox migration still describes a stuck row
  as costing only a call per interval.
- **The guard is narrower than ADR 013 first drew it.** The record says the
  `RUNNING` case was found while building.
- **The failure detail is a composed sentence, not the bare last error.** ADR
  013 §3 says the order carries "the obligation's last error". In the code a
  permanent refusal stores a fixed prefix plus the exception message, and an
  aged-out row stores the bound, the attempt count and the last error.
- **A permanent refusal is not written to the row.** The javadoc on
  `PermanentDispatchFailure` says the drainer records the message on the
  obligation; the permanent branch goes straight to `abandon`, which deletes
  it. The message survives on the failed order only.
- The state this ends in is described in [[wiki/agent-workorders/concepts/work-order-lifecycle]];
  the port and adapters in [[wiki/agent-workorders/components/dispatch-seam]].
