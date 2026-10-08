---
title: Modules by id
description: An aggregate names a neighbouring module only by its id type, and any dependency beyond that must travel along an edge declared in an allowlist that ArchUnit checks.
draft: false
cites:
  - path: docs/adr/004-modules-reference-each-other-only-by-id.md
    lines: 9-17, 21-29, 33-46, 57-59
  - path: docs/adr/008-module-dependencies-are-directional.md
    lines: 12-48, 52-99, 108-122
  - path: docs/adr/012-the-work-order-names-a-project-not-a-directory.md
    lines: 77-83
  - path: src/test/java/dev/…/agentworkorders/architecture/ArchitectureFitness.java
    lines: 25-28, 88-107, 119-181, 192-199, 206-226
  - path: src/test/java/dev/…/agentworkorders/architecture/ModuleWallProbeTest.java
    lines: 20-24, 31-45, 47-97
  - path: src/main/java/dev/…/agentworkorders/modules/agent/domain/AgentId.java
    lines: 9-12, 16-37
  - path: src/main/java/dev/…/agentworkorders/modules/project/domain/ProjectId.java
    lines: 16-19, 23-44
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/domain/WorkOrder.java
    lines: 3-5, 39-53, 76, 201-206
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/WorkOrderEntity.java
    lines: 42-44, 90-95
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/AssignWorkOrder.java
    lines: 3-5, 119-133
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/PlaceWorkOrder.java
    lines: 15-20
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/DispatchInstruction.java
    lines: 3-5, 19-22, 37-42
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderController.java
    lines: 234-236
  - path: src/main/resources/db/migration/V3__create_work_orders.sql
    lines: 16-20
  - path: src/main/resources/db/migration/V7__add_work_order_project.sql
    lines: 12-18
verified_at: 262e98e
---

# Modules by id

> **TL;DR** — The code is split into four modules: user, agent, project and workorder. A
> domain class may name another module only through its id type, so `WorkOrder` holds an
> `AgentId` and never an `Agent`. Layers above the domain may depend on a neighbour, but
> only along an edge written into an allowlist, and the resulting graph must have no cycle.
> All of this is checked by ArchUnit rules, and a second test proves each module rule can
> fail. [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

`WorkOrder` sits between a user, an agent and a project and refers to all three. If it held
their objects, the modules would be one module spread over several directories: none could
be saved, locked or moved without the others. The first ADR on this was written before the
second module existed, on the argument that a rule added after the coupling is there is a
refactor.

That first rule was too wide. It forbade every layer from naming anything in a neighbour
except an id type. Assigning a work order needs the agent's WIP limit, read under a lock,
plus a count of that agent's orders, in one transaction. The use case that does this must
name the agent module's repository, which is not an id type, so it had no legal home
anywhere under `modules/`. The second ADR found that two rules had been bundled: "aggregates
refer to each other by identity", which the design rests on, and "a module may not know a
neighbour at all", which it does not.

## How it works

**Ids are small wrapper types.** `AgentId` and `ProjectId` are records around a `UUID`,
created in the domain rather than by the database. The wrapper exists so one kind of id
cannot be passed where another is expected.

**The aggregate holds ids only.** `WorkOrder` imports three types from other modules:
`AgentId`, `ProjectId`, `UserId`. Its fields are `requestedBy`, `runsIn` and `assignedTo`.
The WIP limit reaches `assignTo` as two plain integers because the aggregate cannot see the
agent. In the row mapping the three references are bare `UUID` columns.

**The schema follows the same rule.** `requested_by`, `assigned_to` and `project_id` have no
foreign key. The migration comments give the reason: a foreign key would be the cross-module
coupling written into the schema.

**Three ArchUnit rules cover modules**, in `ArchitectureFitness`:

- `DOMAIN_NAMES_NEIGHBOURS_ONLY_BY_ID` — classes in a `domain` package may not depend on
  another module, except on a class whose simple name ends in `Id`.
- `MODULE_DEPENDENCIES_ARE_DECLARED` — for the other layers, a dependency on another module
  is refused unless an allowlist entry names that pair of packages. Id types are exempt here
  too.
- `MODULE_DEPENDENCIES_ARE_ACYCLIC` — the module graph must be free of cycles, again
  ignoring id types.

A fourth rule, `LAYERS_POINT_INWARD`, keeps `web` and `infrastructure` from being accessed
by any layer.

**The allowlist has 8 entries, all starting in workorder:**

| From | To | Entries |
| --- | --- | --- |
| workorder application | agent application, agent domain | 2 |
| workorder infrastructure | agent application | 1 |
| workorder application | project application, project domain | 2 |
| workorder infrastructure | project application | 1 |
| workorder web | user application, user domain | 2 |

The "application → neighbour domain" entries exist because a port returns its aggregate:
`AgentRepository.findByIdForUpdate` hands back an `Agent`, so `AssignWorkOrder` holds one
for the length of the use case. The infrastructure entries cover the module's wiring class,
which must name what it injects.

**Ids may travel against the direction.** `DispatchInstruction` in the agent module names
`WorkOrderId` and `DispatchAttemptId` from workorder. The cycle rule ignores id types, so
this is not a cycle.

**Each module rule is shown to fail.** `ModuleWallProbeTest` runs the three rules against
probe modules that live in the test source set: 4 of its 7 tests expect a rejection and
check that the message names the offending class or a cycle, and 3 expect a legal shape to
pass. The real rule run excludes test classes, so the probes do not affect it.

| Option | Why not |
| --- | --- |
| Aggregates hold whole neighbour objects | The modules become one module; the coupling stays hidden until someone tries to separate them. |
| Convention only, no rule | A convention nobody can fail is not a boundary. |
| Keep the flat id-only rule, add a layer above the modules | That layer sits outside the module packages, where the rules do not look; the lock still crosses modules; the use case ends up away from the invariant it enforces. |
| Keep the flat rule, exempt one module | A named hole with no principle behind it is what every later violation would cite. |

## What it costs

- No navigation across modules. Showing a requester's name next to an order needs an
  explicit lookup.
- With no foreign key, an id can point at nothing. `PlaceWorkOrder` does not check that the
  project exists; its comment leaves that to the caller.
- The id exemption matches on a name suffix, so any class named `…Id` passes regardless of
  what it is.
- An allowlist can be widened one entry at a time, which is a smaller act than breaching a
  flat prohibition. The cycle rule is what bounds it.

## Later changes

- The first ADR is marked superseded by the second. What survives from it is the domain
  rule; what was dropped is its application to every layer.
- The second ADR names two directions, `workorder → agent` and `workorder → user`. The code
  has three: `workorder → project` was added with [[wiki/agent-workorders/decisions/work-order-names-project]].
- The ADR left `workorder → user` out of the allowlist because only `UserId` was needed. It
  is in the allowlist now, and it starts in the `web` layer, a shape the ADR's three rules
  do not describe: the controller resolves the caller through the user module's provisioning
  use case. See [[wiki/agent-workorders/components/user-module]].
- The use case that motivated the change is described in
  [[wiki/agent-workorders/decisions/cross-aggregate-invariants]]; the port that carries ids against the direction
  is in [[wiki/agent-workorders/components/dispatch-seam]].
