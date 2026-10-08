---
title: Cross-aggregate invariants
description: The per-agent WIP limit is decided by the work-order aggregate from two numbers that the assignment use case reads while holding a row lock on the agent.
draft: false
cites:
  - path: docs/adr/007-cross-aggregate-invariants-and-their-locking.md
    lines: 10-25, 29-56, 58-93, 97-107, 111-117
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/AssignWorkOrder.java
    lines: 23-44, 108-140
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrder.java
    lines: 57-68, 201-210
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WipLimitExceededException.java
    lines: 5-31
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/WorkOrderRepository.java
    lines: 28-39
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/JpaWorkOrderRepository.java
    lines: 36-37, 57-60
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/WorkOrderEntityJpaRepository.java
    lines: 20
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/WorkOrderEntity.java
    lines: 23-28, 40, 72-74
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/WorkOrderModuleConfiguration.java
    lines: 47-56
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/OverdueReaper.java
    lines: 67-94
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/AgentRepository.java
    lines: 27-44
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/AgentEntityJpaRepository.java
    lines: 20-34
  - path: src/main/java/dev/…/agentworkorders/modules/agent/domain/Agent.java
    lines: 15-20, 197-208, 272-273
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderController.java
    lines: 133-138, 189-192
  - path: src/main/java/dev/…/agentworkorders/config/SecurityConfiguration.java
    lines: 117-118
  - path: src/main/resources/db/migration/V2__create_agents.sql
    lines: 10-14, 26
  - path: src/main/resources/db/migration/V3__create_work_orders.sql
    lines: 10-14, 72-74
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrderTest.java
    lines: 186-227
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/AssignWorkOrderIntegrationTest.java
    lines: 34-46, 100-124, 172-200
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/AssignWorkOrderTest.java
    lines: 135-145, 198-240
  - path: src/test/java/dev/…/agentworkorders/modules/agent/infrastructure/JpaAgentRepositoryIntegrationTest.java
    lines: 158-176
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/infrastructure/JpaWorkOrderRepositoryIntegrationTest.java
    lines: 133-162
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderEndpointIntegrationTest.java
    lines: 68-73, 199-235
verified_at: 262e98e
---

# Cross-aggregate invariants

> **TL;DR** — An agent may hold at most `wipLimit` work orders at once. The work order
> cannot check that itself, because the rule is about the agent and about every other order
> that agent holds. So `AssignWorkOrder` locks the agent's row, counts the agent's active
> orders, and passes the count and the limit into `WorkOrder.assignTo`, which decides. A
> test with two threads against a real PostgreSQL checks that only one of two racing
> assignments passes. [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

Two rules of the work order cannot be checked from inside it.

- **The WIP limit.** The limit is a field of the agent, and the load is a count over other
  work orders. The aggregate knows an `AgentId` and nothing behind it (see
  [[wiki/agent-workorders/concepts/modules-by-id]]).
- **The deadline.** Nothing about an order changes when its deadline passes, so no method
  call can notice.

Both need code outside the aggregate, and where that code sits decides what still holds when
two writers arrive together. Counting without a lock lets two assignments read the same load
and both pass. A background job that fails overdue orders is a second writer on rows that
agents report into.

## The decision

- **The rule stays in the domain; its inputs are passed in.** `assignTo(agent, currentLoad,
  wipLimit, now)` throws `WipLimitExceededException` when `currentLoad >= wipLimit`. It is a
  function of its arguments and has a unit test with no database.
- **The use case reads the inputs in a fixed order, in one transaction.** `AssignWorkOrder`
  first reads the agent with `findByIdForUpdate`, then refuses an agent that is not
  available, then calls `countActiveFor`, then loads the order, calls `assignTo` and saves.
- **The lock is a pessimistic write lock on the agent's row.** The query carries
  `@Lock(PESSIMISTIC_WRITE)`. It is a separate, explicitly named method so that an ordinary
  lookup takes no lock.
- **"Active" means `ASSIGNED` or `RUNNING`.** The count is a derived query over those two
  statuses, and a partial index covers exactly those rows.
- **The limit is at least one.** The agent aggregate guards that, and the agents table
  repeats it as a check constraint.
- **A capacity refusal has its own exception type.** It is the one refusal a caller is
  expected to act on by trying another agent. The controller maps it to `409`.
- **The deadline gets a scheduler and a version column.** The work-order row carries
  `@Version`; it is the only entity with one. `OverdueReaper` fails each overdue order in
  its own transaction and treats an optimistic-lock failure as the correct outcome: the
  other writer committed first.

Options the ADR weighed for the WIP limit:

| Option | Why not |
| --- | --- |
| Count and check, no lock | Two concurrent assignments read the same load and both pass; a single-threaded test of it can only be green. |
| Optimistic lock on the agent | Bumps the version of an aggregate that does not change, and the retry is a code path with its own failure modes. |
| Database trigger or constraint | The central rule would live in a migration instead of in the model. |

Options for the deadline race:

| Option | Why not |
| --- | --- |
| Conditional `UPDATE … WHERE status IN (…)` | The transition would happen in SQL with no domain test, and other writer pairs stay unprotected. |
| Pessimistic lock per order | The background job would block requests on the orders that are trying to finish. |
| Accept the race | A completed order could end up recorded as failed. |

What the tests show, as read:

- `AssignWorkOrderIntegrationTest` releases two threads through a `CyclicBarrier` to assign
  two orders to one agent with a limit of one. It asserts that exactly 1 of the 2 succeeds,
  that the loser gets `WipLimitExceededException` rather than a database error, and that the
  agent then holds 1 active order.
- The agent repository's integration test opens a transaction, takes the locked read, and
  asserts that a second connection cannot lock the same row.
- The unit test asserts the locked read was used, that a refused assignment leaves the order
  unassigned, that a completed order does not count against the limit, and that a retired
  agent is refused.
- The work-order repository's integration test loads one row twice, saves the first copy,
  and asserts the second save raises an optimistic-lock failure.

## What it costs

- Assignments to one agent serialize on its row.
- Two locking strategies exist side by side: pessimistic where a read must be trusted before
  a decision, optimistic where two writers may race.
- Every writer of a work order must be prepared to lose. The domain class carries a
  `version` field it never interprets, because the loaded version has to travel back to the
  store for the check to work.
- Correctness of the deadline rule depends on a background job; if it stops, overdue orders
  stay open.
- The transaction is programmatic, not annotation-driven. The class comment gives the
  reason: an annotated method called from a sibling method of the same bean would run
  without a transaction and release the lock unnoticed.

## Later changes

- **The ADR's sketch is not the code.** The sketch is five lines under `@Transactional` and
  calls `findForUpdate`. The code uses `TransactionOperations`, the method is
  `findByIdForUpdate`, there is an added availability check, and the use case returns the
  assigned order.
- **Assignment now also writes an outbox row** in the same transaction, so the duty to tell
  the agent commits or rolls back with the assignment. See [[wiki/agent-workorders/decisions/dispatch-outbox]].
- **There is a third writer.** The outbox drainer may fail an `ASSIGNED` order when its
  dispatch is given up on, which frees the WIP slot. See [[wiki/agent-workorders/decisions/dispatch-gives-up]] and
  [[wiki/agent-workorders/concepts/work-order-lifecycle]].
- **The module rule the ADR leaned on was replaced.** The use case names the agent module's
  repository, which the earlier rule forbade; the ADR's reference section records that.
- **Reach over HTTP is partial.** `POST /api/work-orders/{id}/assignment` exists and
  requires the `admin` role. No controller registers an agent: the endpoint test calls the
  `RegisterAgent` use case directly and says so. Until that route exists, the assignment
  route has no agent to name unless one is created some other way.
