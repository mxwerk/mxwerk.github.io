---
title: The MCP surface
description: The MCP adapter is a loopback-only, stateless, read-and-evaluate wrapper over the daemon, with a capability set fixed at build time and guards that run before anything reaches the daemon.
draft: false
cites:
  - path: docs/adr/0017-mcp-adapter-contract.md
    lines: 34-43, 60-65, 71-75, 77-96, 111-122
  - path: src/surfaces/mcp/capabilities.ts
    lines: 4-12, 219-228, 317-342
  - path: src/surfaces/mcp/server.ts
    lines: 69-78, 88-174
  - path: src/surfaces/mcp/guards.ts
    lines: 48, 181-189, 212-227
  - path: src/surfaces/mcp/binding.ts
    lines: 35-60
  - path: src/surfaces/mcp/index.ts
    lines: 38-63, 65-93
verified_at: ae9e10a
---

# The MCP surface

> **TL;DR** — The MCP surface lets another agent ask the daemon for a verdict
> over the Model Context Protocol. It listens on loopback only, exposes eleven
> evaluation tools and two read-only resources, and cannot push anything to the
> client. Every request passes guards before the daemon sees it.
> [[wiki/agent-warden/index|↑ Wiki]]

## What it is for

The caller of this surface is the party the warden is judging. The surface
wraps the daemon's own HTTP API for that caller and stays advisory: it reads and
evaluates, never acts. Daemon side: [[wiki/agent-warden/components/daemon]].

## How it is built

- **Closed capability table.** `capabilities.ts` holds the tools and resources
  as constant data; no code can add a twelfth at runtime. Tools are `fileClaim`,
  `sessionVerdict`, `assertionFreeTests`, `skippedStep`, `skippedStepCritic`,
  `handoffFidelity`, `handoffCritic`, `crossSession`, `crossSessionCritic`,
  `critique` and `critiqueEscalate`. Resources are `warden://verdicts` and
  `warden://health`.
- **No push affordance.** It uses the SDK's low-level `Server` and declares
  `subscribe`, `listChanged` as `false`, because the high-level `McpServer`
  overwrites a declared `false` once anything registers (ADR 0017). Every
  non-POST request gets 405 before the SDK is touched.
- **Stateless.** A fresh server and transport per POST; the daemon client and
  escalation cap outlive them.
- **Ordered guards.** Unknown argument names are refused. A revision starting
  with `-` is refused. Each path is resolved against the allowlist and forwarded
  in resolved form with a flag the daemon uses for its descriptor check
  ([[wiki/agent-warden/decisions/evidence-read-hardening]]). Only then is the
  escalation cap charged, and only for `critiqueEscalate`.
- **Fail-closed cap.** If the cap or window setting is absent or unparseable,
  escalation is refused outright, never unlimited.
- **Loopback binding.** It listens on the loopback interface only and requires a port and a
  root directory, refusing to start otherwise. A second process on the same
  port fails with an address-in-use error, which is what keeps the cap unique.

## What it does not do

- **Persist the cap.** The rolling window lives in process memory, so a
  restart empties it; the ADR accepts this as a rate guardrail, not a
  security boundary.
- **Expose chat or the watcher snapshot.**
- **Import from the core.** The path and revision checks are duplicated on
  purpose to keep that boundary.

ADR 0017 lists the absent-path race as an open residual; ADR 0020 later closed
its absent-tail half, and the resolved-prefix half is covered on the daemon side.
