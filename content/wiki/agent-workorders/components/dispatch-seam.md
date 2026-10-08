---
title: The dispatch seam
description: Handing a work order to whatever runs agents goes through one port with two adapters, and a single configuration property decides which adapter answers it.
draft: false
cites:
  - path: docs/charter.md
    lines: 38-50
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/AgentDispatchPort.java
    lines: 5-73
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/DispatchInstruction.java
    lines: 8-62
  - path: src/main/java/dev/…/agentworkorders/modules/agent/application/PermanentDispatchFailure.java
    lines: 5-38
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/CockpitAgentDispatch.java
    lines: 20-67, 77-107, 121-155
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/LoggingAgentDispatch.java
    lines: 10-57
  - path: src/main/java/dev/…/agentworkorders/modules/agent/infrastructure/AgentModuleConfiguration.java
    lines: 28-31, 33-90
  - path: src/main/resources/application.properties
    lines: 37-61
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/application/DispatchOutboxDrainer.java
    lines: 29-40, 62-66, 122-184, 246-285
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/DispatchOutboxDrainerSchedule.java
    lines: 16-19, 37-42
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/infrastructure/WorkOrderModuleConfiguration.java
    lines: 73-91
  - path: src/main/java/dev/…/agentworkorders/config/SchedulingConfiguration.java
    lines: 15-27
  - path: docs/adr/010-the-idempotency-contract-comes-before-the-durability-mechanism.md
    lines: 30-39, 52-60
  - path: docs/adr/013-a-dispatch-that-cannot-succeed-gives-up.md
    lines: 17-22, 53-62
  - path: src/test/java/dev/…/agentworkorders/modules/agent/infrastructure/CockpitAgentDispatchTest.java
    lines: 32-59, 80-228
  - path: src/test/java/dev/…/agentworkorders/modules/agent/infrastructure/CockpitDispatchWiringTest.java
    lines: 13-39
  - path: src/test/java/dev/…/agentworkorders/modules/agent/infrastructure/DispatchAdapterWiringTest.java
    lines: 13-44
  - path: src/test/java/dev/…/agentworkorders/modules/agent/infrastructure/LoggingAgentDispatchTest.java
    lines: 32-60
verified_at: 262e98e
---

# The dispatch seam

> **TL;DR** — This application records who is assigned what; running an agent is another system's
> job (agent-cockpit). The boundary between them is one interface, `AgentDispatchPort`, in the agent
> module. Two adapters implement it: a stub that only logs, and an HTTP adapter that posts to the
> cockpit. The HTTP adapter is selected when the property `agent.cockpit.base-url` is set, and the
> stub otherwise. The adapter's behaviour is tested against a mock HTTP peer only.
> [[wiki/agent-workorders/index|↑ Wiki]]

## What it is

The charter decided on a standalone application with an integration seam: this side owns the
persistent model, the cockpit does live orchestration, and the two meet at a dispatch port.

`AgentDispatchPort` (in `modules/agent/application`) has two methods:

| Method | Argument | Meaning |
| --- | --- | --- |
| `dispatch` | `DispatchInstruction` | hand an assigned work order to its agent |
| `cancel` | `WorkOrderId` | say that a work order is no longer wanted |

Both return nothing. Failure is reported by throwing, and the port draws one distinction between
failures: `PermanentDispatchFailure` means the receiver will give the same refusal on every later
call; any other exception is read as transient.

`DispatchInstruction` is a record of five components: the work order id, the agent id, an
idempotency key, a target directory and a prompt. It refuses a null component and a blank target
directory. The caller assembles it, because the adapter lives in the agent module's infrastructure
and the module rules do not let it read a work order (see [[wiki/agent-workorders/concepts/modules-by-id]] and
[[wiki/agent-workorders/components/quality-gate]]).

## How it works

**The caller.** A grep over `src/main` finds one call of `dispatch.dispatch(...)`:
`DispatchOutboxDrainer`, in the work-order module. For each pending obligation it reads the work
order and its project, builds the instruction (target directory = the project's root; prompt =
title, blank line, description), and calls the port outside any database transaction. A normal
return removes the obligation. The mechanism around that call is described in
[[wiki/agent-workorders/decisions/dispatch-outbox]] and [[wiki/agent-workorders/decisions/dispatch-gives-up]].

**Which adapter answers.** `AgentModuleConfiguration` declares two beans of the port type:

| Bean | Condition | Class |
| --- | --- | --- |
| `cockpitAgentDispatch` | property `agent.cockpit.base-url` is present | `CockpitAgentDispatch` |
| `loggingAgentDispatch` | no other bean of the port type exists | `LoggingAgentDispatch` |

There is no separate "enabled" flag. In the committed `application.properties` the property appears
only as a commented-out line, so the default is the stub. Two context tests fix this: without the
property the injected port is a `LoggingAgentDispatch`, and with it a `CockpitAgentDispatch`. The
second test states that the configured address is never dialled.

**What the cockpit adapter does.** `dispatch` sends `POST <base-url>/api/dispatch` with a JSON body
of three fields: `targetDir`, `prompt` and `idempotencyKey` (the obligation's own id, as a string).
It is built on `RestClient` with a connect timeout of 5 seconds and a read timeout of 30 seconds by
default, both overridable by property. The outcomes:

| Response | Adapter | Read by the drainer as |
| --- | --- | --- |
| `200` | returns, logs at info | delivered |
| `400`, `403` | throws `PermanentDispatchFailure` with status, URI and body | permanent: abandon |
| any other 4xx or 5xx | lets `RestClient`'s own exception through | transient: retry |

The class comment names `409` (slot full, or the same key still in flight), `501` and `502` as the
transient cases it reasoned about. Only `400` and `403` are called permanent, on purpose: a status
nobody reasoned about is left transient. `cancel` makes no HTTP call; it logs a warning that the
cockpit has no endpoint for it.

**What the stub does.** `LoggingAgentDispatch` logs one info line per `dispatch` and per `cancel`
and calls nothing.

**Tests.** `CockpitAgentDispatchTest` binds a `MockRestServiceServer` to the client and has one case
per status above: the three body fields, `200`, `409` (throws, and is not the permanent type), `403`
and `400` (permanent, message carries status and body), `501`, `502`, and `cancel` sending nothing.
`LoggingAgentDispatchTest` covers the stub's four cases.

## What it costs / limits

- **No evidence of a run against a real cockpit.** The adapter's tests use a mock HTTP peer, and the
  wiring test never dispatches. Nothing cited here shows the adapter exchanging a request with an
  actual cockpit process.
- **The path is not reachable over HTTP yet.** The port is called for a recorded assignment, and an
  assignment names an agent. A grep over `src/main` for mapping annotations finds controllers for
  users, work orders and projects and none in the agent module, and `RegisterAgent` is constructed
  as a bean but called by no controller. So an agent row cannot be created through the API.
- **The drain loop is off under the `test` profile.** Scheduling is enabled only outside that
  profile; the default interval is 5 seconds after a 1-minute initial delay.
- **`cancel` has no caller.** A grep over `src/main` finds no invocation of the port's `cancel`.
- **Safety under retry depends on the receiver.** Delivery is at-least-once, so the same key can
  arrive twice. The drainer's comment says it must never be pointed at a receiver that does not
  honour the key.

## Later changes

- **The charter planned a stub only.** It describes a port `dispatch(workOrder)` with a stub adapter
  and calls a real adapter YAGNI until the cockpit's API exists. The code now has the real adapter
  beside the stub, the port takes a `DispatchInstruction` instead of a work order, and a second
  method, `cancel`, is declared.
- **The idempotency key changed between records.** ADR 010 found that the cockpit's endpoint
  accepted no key at the time, and planned a key derived from the work-order and agent ids. The
  adapter sends the obligation's own id instead and gives the reason in a comment: an order can be
  assigned to the same agent twice, and a derived key would make the second dispatch a replay of the
  first.
- **`400` and `403` used to be retried.** ADR 013 records that the adapter first documented them as
  retried forever and introduced the permanent failure type to end that.
