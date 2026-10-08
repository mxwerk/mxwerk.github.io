---
title: The dispatch outbox
description: An assignment records a dispatch obligation in its own transaction, and that row's id is the idempotency key every retry presents.
draft: false
cites:
  - path: docs/adr/010-the-idempotency-contract-comes-before-the-durability-mechanism.md
    lines: 12-19, 30-46, 50-69, 75-81, 101-109
  - path: docs/adr/011-the-dispatch-outbox-keyed-by-its-own-row.md
    lines: 18-35, 40-46, 50-83, 89-98, 112-124, 134-135
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/AssignWorkOrder.java
    lines: 29-39, 119-140
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutbox.java
    lines: 14-17, 19-58
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainer.java
    lines: 29-40, 122-130, 138-184, 214-224
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/DispatchAttempt.java
    lines: 33-40, 73-76, 92-98
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/DispatchAttemptId.java
    lines: 30-53
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/DispatchEffect.java
    lines: 13-17
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrder.java
    lines: 201-202, 222-223
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/JpaDispatchOutbox.java
    lines: 26-45
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/DispatchOutboxEntity.java
    lines: 19-22, 28-42
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/DispatchOutboxEntityJpaRepository.java
    lines: 26-27
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/DispatchOutboxDrainerSchedule.java
    lines: 16-19, 37-42
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/WorkOrderModuleConfiguration.java
    lines: 73-91
  - path: src/main/java/dev/…/agentworkorders/config/SchedulingConfiguration.java
    lines: 15-26
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/CockpitAgentDispatch.java
    lines: 80-94
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/AgentModuleConfiguration.java
    lines: 28-31, 59-61, 86-90
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderController.java
    lines: 72-73, 133-138
  - path: src/main/java/dev/…/agentworkorders/modules/user/web/UserController.java
    lines: 36-37
  - path: src/main/java/dev/…/agentworkorders/modules/project/web/ProjectController.java
    lines: 52-53
  - path: src/main/resources/application.properties
    lines: 1-61
  - path: src/main/resources/db/migration/V5__create_dispatch_outbox.sql
    lines: 10-12, 17-49
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/AssignWorkOrderTest.java
    lines: 147-196
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainerTest.java
    lines: 164-241
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/domain/DispatchAttemptTest.java
    lines: 36-61
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/infrastructure/JpaDispatchOutboxIntegrationTest.java
    lines: 102-124, 136-153
  - path: src/test/java/dev/…/agentworkorders/modules/agent/infrastructure/CockpitAgentDispatchTest.java
    lines: 80-106
verified_at: 262e98e
---

# The dispatch outbox

> **TL;DR** — Assigning a work order does not tell the agent anything. It
> writes one row into `dispatch_outbox` in the same transaction as the
> assignment, and a scheduled drain loop announces the row afterwards. The
> row's own id is sent as the idempotency key, so a retry repeats the key the
> failed attempt used. The mechanism was held back until the receiving
> endpoint accepted such a key, because a retry against a receiver that cannot
> recognise a repeat starts a second agent. [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

The assignment use case used to commit and then call the dispatch port on the
next line. A throw from that call left the order `ASSIGNED` against an agent
that was never told, holding one of that agent's WIP slots, with nothing that
retried or unwound it (ADR 010, issue #43). Dispatching inside the transaction
was not the way out: an agent told about work that a rollback then removes is
worse than a late dispatch.

Two repair mechanisms were on the table, an outbox table or a `dispatched_at`
column on `work_orders`. Both work by recording the obligation and calling
again later. ADR 010 found that the receiving endpoint read four fields and
silently dropped anything else, so a repeated call would have been accepted
and would have started a second agent process. The blocker was the wire
contract, not the choice of mechanism.

## The decision

- **Contract first, mechanism last.** ADR 010 fixed an order: the receiver (agent-cockpit)
  accepts a caller-supplied key, then this side gets an adapter that sends it,
  then the durability mechanism is built. It deliberately did not pick the
  mechanism.
- **A transactional outbox.** ADR 011 picked it once the receiver's contract
  existed. `AssignWorkOrder.record` saves the order and then calls
  `outbox.save(DispatchAttempt.toDispatch(...))` inside the same transaction
  callback; it no longer calls the dispatch port at all.
- **The key is the row's id.** `DispatchAttemptId` wraps a random UUID that is
  both the primary key of the row and the `idempotencyKey` field
  `CockpitAgentDispatch` posts. `afterFailure` returns a new value with the
  same id and the same `createdAt`.
- **One transaction per obligation, the remote call between them.**
  `DispatchOutboxDrainer.drainOne` reads the row, builds the instruction,
  calls the port outside any transaction, and removes the row in a further
  transaction. A failure is caught, counted on the row with its message, and
  the loop moves to the next id.
- **Delete on success.** `DispatchOutbox.remove` deletes the row; nothing
  marks it. The pending query is therefore every row in the table, ordered by
  `created_at`.
- **The outbox belongs to the work-order module.** The row is written in the
  work-order aggregate's transaction. The table carries no foreign key to
  `work_orders` or `agents`; see [[wiki/agent-workorders/concepts/modules-by-id]].
- **The schedule is separate.** `DispatchOutboxDrainerSchedule` calls `drain`
  with a fixed delay that defaults to five seconds and an initial delay that
  defaults to one minute, both properties. That delay is also the dispatch
  latency.

| Option | Why not |
| --- | --- |
| Build the outbox before the key exists | Its correctness rests on the retry being safe, which was not yet true; it would have shipped switched off. |
| `dispatched_at` column on `work_orders` | A second outbound effect (`cancel`) would need a second column and drain query, and the drainer would write the rows the overdue reaper already writes. |
| Key derived from work-order id and agent id | `unassign` returns an order to `OPEN` and `assignTo` requires `OPEN`, so the same pair can be assigned twice; the second dispatch would look like a repeat of the first and the agent would never hear of it. |
| Derived key plus `assignedAt` | Needs a value that is unique per assignment; a timestamp is not reliably that, and an id that already exists is. |
| Catch the throw and unassign | Undoes an assignment the database accepted, and a dispatch that timed out may have arrived. |

## What it costs

- **At-least-once delivery.** A drainer that stops after the call and before
  the removal announces the row again. That is safe only if the receiver
  honours the key; the drainer's own javadoc says it must never be pointed at
  one that does not.
- **A third background writer**, after the assignment use case and the overdue
  reaper described in [[wiki/agent-workorders/decisions/cross-aggregate-invariants]].
- **Dispatch is never immediate.** An assignment is announced on a later drain
  pass, not on the call that made it.
- **The window stayed open between steps.** ADR 010 accepted that #43 stayed
  unfixed until the mechanism landed.
- **No dispatch history.** Deleting on success means the table cannot say what
  was sent or when.

What the tests show: `AssignWorkOrderTest` asserts that an assignment records
exactly one untried obligation. `DispatchOutboxDrainerTest` asserts that a
retry presents the same key twice and that one refused row does not stop the
row behind it. `DispatchAttemptTest` asserts that two obligations for the same
order and agent get different ids. `JpaDispatchOutboxIntegrationTest` asserts
oldest-first ordering and that a second save updates the row.
`CockpitAgentDispatchTest` asserts the posted body carries the id as the key.

## Later changes

- **The drainer now writes `work_orders` in one case.** ADR 011 chose the
  outbox partly because its drainer never touches that table. Since ADR 013
  the `abandon` path fails the order; see
  [[wiki/agent-workorders/decisions/dispatch-gives-up|a dispatch that cannot succeed gives up]]. The
  javadoc on `DispatchOutbox` and on `DispatchOutboxEntity` still states the
  older claim, and the entity's "only the drainer ever writes these rows"
  leaves out the insert made by the assignment use case.
- **ADR 010's key instruction was overruled.** It asked for a derived key with
  nothing stored; ADR 011 records the deviation and the code follows ADR 011.
  ADR 011 left retention open; the code took its delete-on-success default.
- **What the instruction carries** (project root and prompt) is covered in
  [[wiki/agent-workorders/decisions/work-order-names-project]]; the port and its two adapters in
  [[wiki/agent-workorders/components/dispatch-seam]].
- **Not reachable over HTTP alone at this commit.** The assignment route
  exists on `WorkOrderController`, but a search for `@RestController` under
  `src/main` finds three controllers (user, work order, project) and
  `RegisterAgent` is referenced there only by the agent module's
  configuration, so no request can create the agent an assignment needs
  (issue #94). `application.properties` sets no datasource (issue #92). The
  scheduler is switched off under the `test` profile, so the tests call
  `drain` directly.
