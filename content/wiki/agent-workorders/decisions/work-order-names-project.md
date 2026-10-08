---
title: Work order names a project
description: A work order stores the id of a project, and the project row is the single place that holds the directory an agent is told to work in.
draft: false
cites:
  - path: docs/adr/012-the-work-order-names-a-project-not-a-directory.md
    lines: 12-23, 39-55, 59-71, 75-120, 126-145, 161-182
  - path: src/main/java/dev/…/agentworkorders/modules/project/domain/Project.java
    lines: 21-26, 49-59, 73-75, 116-156
  - path: src/main/java/dev/…/agentworkorders/modules/project/domain/ProjectId.java
    lines: 9-19, 23-44
  - path: src/main/java/dev/…/agentworkorders/modules/project/application/ProjectRepository.java
    lines: 15-27
  - path: src/main/java/dev/…/agentworkorders/modules/project/application/RegisterProject.java
    lines: 14-16, 41-43
  - path: src/main/java/dev/…/agentworkorders/modules/project/web/ProjectController.java
    lines: 76-96, 114-118
  - path: src/main/java/dev/…/agentworkorders/config/SecurityConfiguration.java
    lines: 103-104, 119-120
  - path: src/main/resources/db/migration/V6__create_projects.sql
    lines: 7-36
  - path: src/main/resources/db/migration/V7__add_work_order_project.sql
    lines: 4-23
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/PlaceWorkOrder.java
    lines: 15-20, 63-80
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/web/PlaceWorkOrderRequest.java
    lines: 34-39
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderController.java
    lines: 106-118, 221-224
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrder.java
    lines: 42-53, 94
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainer.java
    lines: 138-181, 246-264, 280-285
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/DispatchInstruction.java
    lines: 11-17, 37-62
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/AgentDispatchPort.java
    lines: 14-15, 61
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/AgentModuleConfiguration.java
    lines: 59-61, 86-90
  - path: src/test/java/dev/…/agentworkorders/architecture/ArchitectureFitness.java
    lines: 144-160
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainerTest.java
    lines: 243-280, 308-332
  - path: src/test/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderEndpointIntegrationTest.java
    lines: 54-55, 85-93
verified_at: 262e98e
---

# Work order names a project

> **TL;DR** — To hand work to an agent, the receiving system (agent-cockpit) needs a directory and a prompt,
> and the work order held neither. The decision adds a fourth module, `project`: a `Project`
> has its own id, a name and an absolute `root` path. A work order stores only the
> `ProjectId`. When a dispatch is assembled, the drainer looks the project up and sends its
> root as the target directory, with the order's title and description as the prompt.
> [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

The dispatch port had only a logging stand-in behind it. Writing a real adapter was blocked
on a domain question: what does a work order tell an agent to do, and where?

- The receiver's dispatch call requires a target directory and a prompt. The work order held
  an id, requester, assignee, title, description, priority, deadline and status. Nothing in
  it was a path.
- The receiving system calls the thing "project", but has no project row and no project id.
  It derives a project from the directory tree on each read. It keys on the root path; the
  name is a directory basename and can repeat under different parents.
- The adapter cannot fetch the data itself. It lives in the agent module's infrastructure
  layer, and the module rules forbid that layer from reading a work order (see
  [[wiki/agent-workorders/concepts/modules-by-id]]).

## The decision

- **A fourth module, `modules/project/`.** `Project` has a `ProjectId` (a UUID created on
  this side), a `name` and a `root`. The missing remote id was taken as a reason to create a
  local one, not as a reason to skip the aggregate.
- **`root` is the key, `name` is a label.** The table declares `root` `UNIQUE` and puts no
  unique constraint on `name`. The repository port has a lookup by id and no lookup by name
  or root.
- **`root` must be absolute.** The aggregate rejects a root that does not start with `/`,
  and a check constraint repeats that. Whether the directory exists, or lies inside the
  receiver's allowed area, is not checked here; the receiver's own refusal is treated as the
  authority.
- **The work order holds a `ProjectId` and nothing else.** The field is `runsIn`, required
  in the constructor. The column is `project_id UUID NOT NULL`, with an index and no foreign
  key.
- **The target directory is `project.root()`, sent unchanged.**
- **The prompt is the title, a blank line, then the description.** With no description it is
  the title alone. No priority, deadline or id is added, so later columns do not become
  prompt decisions.
- **The payload travels through the port.** `DispatchOutboxDrainer`, in the work-order
  module, reads the order and the project and builds the instruction; the adapter receives
  everything as an argument.

| Option | Why not |
| --- | --- |
| A target-directory field on the work order | A path from another system becomes domain data repeated on every row, each one a copy to migrate if the directory moves. |
| A home directory on the agent | An agent may hold several orders at once, and all of them would be forced into one directory; it also makes the agent stand in for the project. |
| A value object holding only the project name | The name is a basename, not a key; resolving by name also assumes all projects sit flat under one parent. |
| Decide a per-kind prompt template now | The work order has no kind field, so the template would need a new term, a migration and a decision of its own. |

How the code holds it, as read:

- `PlaceWorkOrder.place` takes a `ProjectId` and passes it to `WorkOrder.place`. The request
  record has a `runsIn` UUID, and the controller answers a missing one as a bad request.
- `instructionFor` in the drainer loads the order, then the project by `order.runsIn()`, and
  builds a `DispatchInstruction` with `project.root()` as `targetDir`.
- The drainer's unit test asserts the root arrives as the target directory, and both prompt
  shapes: with and without a description.
- `RegisterProject` does no duplicate check; a second registration of the same root is left
  to the unique constraint, which the controller turns into a `409`. Registering over HTTP
  requires the `admin` role; listing does not.

## What it costs

- A fourth module, two migrations, and three more allowlist entries from the work-order
  module to the project module.
- **A path from another system is stored here.** If the directory moves or is renamed on the
  other side, the stored root is stale and the dispatch is refused there. It is one row to
  fix rather than one per order.
- **Nothing checks that the named project exists when an order is placed.** There is no
  foreign key, and neither `PlaceWorkOrder` nor the controller looks the project up. The
  endpoint test places an order against a random UUID and gets `201`. The gap shows up
  later: the drainer's lookup throws, the failure is recorded on the obligation, and it is
  retried. The unit test for that case asserts one recorded attempt with an error naming the
  missing project.
- **The migration has no backfill.** It adds a `NOT NULL` column without a default, so by
  its own comment it fails against a database that already holds work orders.
- **A project cannot be changed.** The aggregate has no mutating method and the table has no
  `updated_at`; both comments say to add them with the first operation that needs them.

## Later changes

- **The port takes one record, not extra arguments.** The ADR says `dispatch` gains the
  target and the prompt as arguments. The code passes a single `DispatchInstruction` record
  with five components, which also rejects a blank target directory when it is built.
- **A real adapter now exists.** The ADR's context describes the logging stand-in as the
  only implementation. The code has a second one, wired only when a base-URL property for
  the receiver is set; otherwise the stand-in is used. See [[wiki/agent-workorders/components/dispatch-seam]].
- **A stale or missing project now has an ending.** The ADR left the failure mode to "the
  adapter's error mapping". A dispatch that keeps failing is given up on after a bound and
  the order is failed; see [[wiki/agent-workorders/decisions/dispatch-gives-up]] and, for the resulting state,
  [[wiki/agent-workorders/concepts/work-order-lifecycle]].
- **The project module got HTTP routes** for registering and listing, which the ADR does not
  mention.
- The outbox that the drainer reads is described in [[wiki/agent-workorders/decisions/dispatch-outbox]].
