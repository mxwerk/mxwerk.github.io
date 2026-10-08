---
title: One daemon, pluggable surfaces
description: A single always-on daemon owns capture and judgment, and the CLI, MCP and editor clients are thin HTTP clients of it, so adding a surface needs no daemon rework.
draft: false
cites:
  - path: docs/adr/0008-product-form-hybrid-daemon.md
    lines: 7-8, 22-31, 35-46, 48-52, 66-69
  - path: docs/adr/0011-surface-form-pluggable-clients.md
    lines: 10-16, 38-60, 62-66, 74-76
  - path: docs/adr/0012-daemon-transport-http-mcp-deferred.md
    lines: 20-29, 33-39, 41-48, 61-65
  - path: src/surfaces/daemonClient.ts
    lines: 1-6, 24-28, 35-43
  - path: src/core/daemon/server.ts
    lines: 30-32
  - path: src/surfaces/cli/index.ts
    lines: 12-12
  - path: src/surfaces/mcp/index.ts
    lines: 40-40
  - path: src/surfaces/vscode/webview/ObservabilityViewProvider.ts
    lines: 1-16
  - path: src/surfaces/vscode/webview/ChatViewProvider.ts
    lines: 1-20
verified_at: ae9e10a
---

# One daemon, pluggable surfaces

> **TL;DR** — One always-on daemon captures agent activity and runs the checks.
> The CLI and the MCP adapter are thin clients that talk to it over HTTP on the
> loopback interface. The editor was first meant to be the viewer; a later
> decision demoted it to one client among several, and the editor panel has
> not been moved onto the daemon yet.
> [[wiki/agent-warden/index|↑ Wiki]]

## The problem

The signals the warden reads (agent hooks, transcript files, telemetry) are
emitted whether or not an editor is open, and long agent runs happen when it
is not. An editor-only design would miss those events and would put the
critic model's memory on top of the editor's.

## The decision

- A daemon owns capture, the grounding harness and the local critic, and is
  the single source of truth.
- Display is a set of clients attached over the daemon's local API: a CLI as
  the primary surface, an MCP adapter that is advisory only, an optional web
  dashboard, and the VS Code panel as an optional client.
- The internal transport is HTTP, bound to `127.0.0.1`. The client class
  states that a surface talks to the daemon only over HTTP and JSON and never
  imports daemon internals.
- MCP is a surface that wraps the HTTP API, not the internal bus.

| Option | Why not |
|---|---|
| Editor extension only | Loses events while the editor is closed; stacks the critic's RAM on the editor host. |
| Editor as the only viewer | Wrong place for an operator who works in a terminal; later superseded. |
| MCP as the internal transport | Handshake and JSON-RPC overhead for non-LLM clients, a browser cannot use it, and it ties the core to an evolving spec. |
| Unix socket | A browser cannot use it, so HTTP would be rebuilt later. |

## What it costs

- Two processes, a client protocol and a daemon lifecycle to manage.
- The MCP surface must stay advisory, or it silently crosses the line from
  informing to acting on the agent.
- The loopback bind is deliberate: verdict payloads may hold sensitive data.
- The decision is ahead of the code. The CLI and the MCP adapter go through
  the daemon client; the VS Code panel still queries the model runtime and the
  metrics store directly.

## Later changes

The viewer half of the first decision was superseded by the pluggable-client
decision; the daemon-owns-capture half stands. The MCP surface is described in
[[wiki/agent-warden/components/mcp-surface]] and the daemon in [[wiki/agent-warden/components/daemon]].
