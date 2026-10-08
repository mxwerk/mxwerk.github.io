---
title: Work-order lifecycle
description: A work order moves through six states, and every transition is a method on the aggregate that refuses to run from the wrong state.
draft: false
cites:
  - path: docs/adr/006-the-work-order-state-machine-and-its-guards.md
    lines: 11-28, 32-76, 78-94
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrder.java
    lines: 57-68, 94-98, 201-210, 222-227, 235-251, 260-268, 282-292, 312-319, 332-338, 350-353, 505-509
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrderStatus.java
    lines: 24-55
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/FailureReason.java
    lines: 11-30
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/Priority.java
    lines: 3-16
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/OverdueReaper.java
    lines: 67-94
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/AssignWorkOrder.java
    lines: 127-134
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainer.java
    lines: 214-224
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/OverdueReaperSchedule.java
    lines: 34-39
  - path: src/main/java/dev/…/agentworkorders/config/SchedulingConfiguration.java
    lines: 24-27
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderController.java
    lines: 106-176, 206-209
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/AgentDispatchPort.java
    lines: 14-19, 63-73
  - path: src/main/resources/db/migration/V3__create_work_orders.sql
    lines: 10-14, 27-30, 43-65, 68-70
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrderTest.java
    lines: 399-499, 501-517
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/OverdueReaperTest.java
    lines: 138-156
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/OverdueReaperIntegrationTest.java
    lines: 106-129
verified_at: 262e98e
---

# Work-order lifecycle

> **TL;DR** — A work order is in one of six states: `OPEN`, `ASSIGNED`, `RUNNING`, and the
> terminal `DONE`, `FAILED`, `CANCELLED`. Each transition is a method on the `WorkOrder`
> aggregate that throws when the order is in the wrong state. The model is complete, but
> only 3 of its 8 transition methods have a caller in production code today; the other 5 are
> reached from tests only. [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

The project charter named five states, `open → assigned → running → done | failed`, and left
the transitions open. Reading those five against the domain showed three holes:

- An agent can be deactivated while it holds an assigned order. With forward-only
  transitions that order has no legal exit.
- A requester can change their mind, and "failed" is the wrong word for a withdrawal.
- Once withdrawal exists, withdrawing work that an external agent is already running needs a
  defined meaning, because the agent will not notice.

The states are persisted values, so the ADR settled them before the first row existed rather
than pay for a migration later.

## How it works

`WorkOrderStatus` has six constants and `isTerminal()` is true for three of them.
`WorkOrder` (`modules/workorder/domain/WorkOrder.java`) has eight transition methods. Each
takes the current instant as an argument and throws `IllegalStateException` when the state
does not fit.

| Method | From | To | Extra guard | Caller under `src/main` |
| --- | --- | --- | --- | --- |
| `assignTo` | OPEN | ASSIGNED | load below the WIP limit | `AssignWorkOrder` |
| `unassign` | ASSIGNED | OPEN | clears the agent | none |
| `start` | ASSIGNED | RUNNING | — | none |
| `complete` | RUNNING | DONE | — | none |
| `failReportedByAgent` | ASSIGNED, RUNNING | FAILED | — | none |
| `failOverdue` | any non-terminal | FAILED | `isOverdue(now)` | `OverdueReaper` |
| `failDispatch` | ASSIGNED | FAILED | — | `DispatchOutboxDrainer` |
| `cancel` | any non-terminal | CANCELLED | — | none |

The caller column comes from a grep for each method call over `src/main`.

- **No retry.** Nothing leaves a terminal state. Re-running work means placing a new order,
  which keeps the record of the failed attempt.
- **The two original fail paths have unequal guards on purpose.** An agent can only fail
  work it holds, so that path starts at `ASSIGNED`. A missed deadline is a missed commitment
  even if nobody picked the work up, so that path also accepts `OPEN`.
- **`FAILED` says why.** `FailureReason` has three values: `AGENT_REPORTED`,
  `DEADLINE_EXCEEDED`, `DISPATCH_FAILED`. A free-text detail is kept for the agent path and
  the dispatch path; the deadline path sets none.
- **Overdue is a predicate, not a state.** `isOverdue(now)` is true for a non-terminal order
  whose deadline is strictly before `now`. A deadline is required at placement, so no order
  can opt out.
- **Priority guards nothing.** It is four plain values and does not derive the deadline.
- **The deadline is enforced from outside.** `OverdueReaper.reap()` lists overdue ids, then
  re-reads and fails each one in its own transaction. A `@Scheduled` method calls it at a
  configurable interval that defaults to one minute; scheduling is switched off under the
  `test` profile.
- **The table repeats two rules.** A check constraint allows a failure reason only on a
  `FAILED` row, and another ties the presence of an assignee to the status (`OPEN` has none;
  `ASSIGNED`, `RUNNING`, `DONE` have one).

The domain test's `IllegalTransitions` group has 8 test methods. 5 of them check one
wrong-state call each (for example `start` on an open order). The other 3 run once per
terminal state and cover `cancel`, `failOverdue` and `isOverdue`; `complete` after a
cancellation is checked separately. The reaper's unit test covers both ways of losing a
race: the order was finished before the re-read, or the save raised an optimistic-lock
failure.

| Option | Why not |
| --- | --- |
| The charter's five states, forward only | An assigned order on a deactivated agent could only be rescued by editing the database. |
| Five states plus retry (`failed → open`) | A new order gives the same result, and re-opening destroys the record of the attempt. |

## What it costs

- Cancelling a running order ends it here at once while the agent outside keeps working. The
  dispatch port reserves a `cancel` method for telling it; the ADR calls that reservation a
  bet, and no production code calls it.
- The deadline rule depends on a background job. If the job stops, overdue orders stay open.
- The aggregate carries a `version` field it never interprets, so that the store can refuse
  a stale write. The integration test shows a reaper holding a stale copy loses to an order
  completed in the meantime.
- Two more transitions than the charter's model, each with guards to keep and test.

## Later changes

- **A third failure path.** The ADR lists seven transitions and two failure reasons. The
  code adds `failDispatch` and `DISPATCH_FAILED`, introduced when a dispatch that cannot
  succeed was given an ending; see [[wiki/agent-workorders/decisions/dispatch-gives-up]]. It is narrower than the
  deadline path: only an `ASSIGNED` order can fail this way.
- **Five transitions are not reachable yet.** The work-order controller has four routes:
  place, assign, list and read one. Nothing in production code calls `start`, `complete`,
  `failReportedByAgent`, `unassign` or `cancel`. The ADR's statement that a late agent
  report surfaces as a `409` describes the controller's handler for `IllegalStateException`,
  but no route accepts such a report today.
- **Assignment has more around it** than the one-line guard in the table: the load is
  counted under a row lock, described in [[wiki/agent-workorders/decisions/cross-aggregate-invariants]].
- **An order now names a project** at placement; see [[wiki/agent-workorders/decisions/work-order-names-project]].
  The neighbours it names are held as ids only, per [[wiki/agent-workorders/concepts/modules-by-id]].
- The enum comment on `DEADLINE_EXCEEDED` says the order "was still open"; the method
  accepts any non-terminal state. The method is the behaviour.
