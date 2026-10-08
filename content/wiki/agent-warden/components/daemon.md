---
title: The localhost daemon
description: The daemon is a loopback-by-default HTTP server plus an opt-in file watcher that turns transcripts and git diffs into verdicts without ever acting on an agent.
draft: false
cites:
  - path: src/core/daemon/server.ts
    lines: 27-33, 104-105, 262-269, 281-323, 358-381
  - path: src/core/daemon/index.ts
    lines: 10-20
  - path: src/core/daemon/router.ts
    lines: 65-83, 101-123, 156-282
  - path: src/core/daemon/watcher.ts
    lines: 4-16, 47-58, 119-142
  - path: src/core/harness/transcript.ts
    lines: 15-20, 51-81, 108-127, 203-247, 249-270
  - path: src/core/harness/crossSessionEvidence.ts
    lines: 72-99
  - path: src/core/config/env.ts
    lines: 147-148, 156-160
  - path: docs/adr/0008-product-form-hybrid-daemon.md
    lines: 7-8, 35-46
  - path: docs/adr/0014-persistent-telemetry-daemon-and-cockpit-consumer.md
    lines: 7-14, 53-58
verified_at: ae9e10a
---

# The localhost daemon

> **TL;DR** — One long-lived Node process owns evidence capture: it reads
> transcripts and git diffs, runs the critics, and serves the results over
> HTTP. It binds to loopback by default and only reports; nothing in it gates
> or steers an agent. Clients such as the CLI and [[wiki/agent-warden/components/mcp-surface]]
> are thin layers over it. [[wiki/agent-warden/index|↑ Wiki]]

## What it is for

Capture has to outlive any editor session, so the decision (ADR 0008) puts it
in a process of its own; display clients attach to it. Later deployments run
it as a user-level service in watch and telemetry mode (ADR 0014). See
[[wiki/agent-warden/decisions/hybrid-daemon-pluggable-surfaces]].

## How it is built

- **Router** (`router.ts`): a pure `route(method, path, deps, body)` over
  injected capabilities, so it is testable without a socket. Routes:
  `GET /health`, `GET /verdicts`, `POST /chat`, `/verdict/file-claim`,
  `/verdict/session`, `/verdict/assertion-free-tests`, `/verdict/skipped-step`,
  `/verdict/handoff`, `/awareness`, `/verdict/critique`, `/verdict/escalate`.
  A `critic: true` body field on three of them switches to the model-backed
  variant (see [[wiki/agent-warden/components/critics]]). A refuted verdict is still HTTP 200.
- **Server** (`server.ts`): a thin `node:http` adapter. Default bind is
  `127.0.0.1:8787`; `WARDEN_HOST` and `WARDEN_PORT` override it. A thrown error
  becomes a generic 500.
- **Watcher** (`watcher.ts`): off unless `WARDEN_WATCH_MS` is positive. Each
  cycle runs the assertion-free check, plus file-claim, skipped-step and
  handoff checks if `WARDEN_TRANSCRIPT` is set, plus the collision check if
  `WARDEN_TRANSCRIPT_DIR` is set. Model calls stay pull-only. The latest
  snapshot lives in memory and is what `/verdicts` returns.
- **Transcript to claims** (`transcript.ts`): each JSONL line is parsed and
  malformed ones skipped. Edit, Write, MultiEdit and NotebookEdit tool calls
  give claimed paths, made repo-relative with outside-repo paths dropped;
  text blocks give prose; Bash calls give commands; Agent/Task calls are paired
  with their results by id as handoffs.

## Evidence-read guards

A `base` revision starting with `-` is refused with 400. A request carrying
`pathsResolved: true` gets a 503 where the host has no `/proc/self/fd`, rather
than an unverified read presented as verified. See
[[wiki/agent-warden/decisions/evidence-read-hardening]].

## What it does not do

Refuted verdicts are logged to the daemon log, not acted on. The cross-session
reader now walks the transcript directory recursively and skips unchanged
files by modification time and size; ADR 0014's flat-directory limit was lifted
afterwards.

## Limits

- Loopback is the default, not an enforced rule: the host is configurable.
- The original decision has the daemon subscribe to agent hooks and ingest
  telemetry. Neither exists in the source tree: capture today is transcript
  files and git.
- Only the latest snapshot is held; history exists only if telemetry is on
  ([[wiki/agent-warden/components/verdict-telemetry]]).
