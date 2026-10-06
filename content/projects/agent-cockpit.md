---
title: agent-cockpit — A Web Console for a Multi-Agent System
description: Self-hosted web console to browse, launch and live-track Claude Code agents — React, Express 5, SQLite, 468 passing unit tests, accessibility and visual-regression gates.
tags:
  - web
  - ai
  - typescript
date: 2026-09-15
---

# agent-cockpit — A Web Console for a Multi-Agent System

> **Note for readers:** a personal project, private repository, single operator.

## The problem

My agent system ([[projects/claude-setup|the SDLC setup]]) runs as files and
terminals: agents and skills are file-based definitions, runs live in terminal
sessions, background jobs in system units, isolation in git worktrees. Operating
that by hand has real hazards: concurrent launches can overrun a shared usage
budget, an agent whose session id was never captured becomes untrackable, and a
reboot loses the state of every interrupted run.

agent-cockpit is one console for **observability, dispatch and reboot
recovery** over that fleet.

## Architecture

- **Backend** — Node/TypeScript, Express 5, SQLite (WAL). Modules for the agent
  catalog, headless dispatch and tracking, stream ingestion, a read-only file and
  worktree browser, and a read-only view onto the agent system's own state
  (message bus, warden verdicts from [[projects/agent-warden|agent-warden]]).
- **Frontend** — React + Vite, TanStack Query, a designed pane-based shell, and
  in-browser terminals (xterm.js).
- **Data flow** — every event of an agent's JSON stream is persisted as it
  arrives; the UI polls deltas at differentiated intervals.

## Decisions (5 ADRs)

- **Poll, don't push (yet).** Delta polling against the event table (~1–2 s for the
  active pane, slower for the catalog) instead of SSE/WebSockets — simpler, and
  enough for one operator. Push stays a documented, deferred option.
- **Reject over-cap launches.** Above the concurrent-session limit, a launch is
  rejected with a visible slot count — race-safe, no hidden queue.
- **The database is authoritative after a reboot.** On startup, a run marked
  `running` with no live process is reconciled to `interrupted` and offered for
  resume. Per-event persistence means nothing is lost mid-run.

## Quality

- **468 unit tests passing** (backend 237, frontend 231; Vitest).
- **Accessibility assertions** (vitest-axe) in the component tests.
- **Visual regression** with Playwright screenshot baselines. The CI image is
  pinned to the exact Playwright version, because baselines are per renderer. A
  pre-push hook runs the visual tier on UI changes and fails closed if its own
  scope check errors.
- **Code-split boundary under test.** The chart library is lazy-loaded, and a
  dedicated test fails if anything imports it statically.
- **CI on every push and PR, no path filter:** lint, typecheck, a project-specific
  forbidden-pattern gate, a "one UI framework" check, tests with coverage summary,
  visual tier. Dependency audits run on a daily schedule, outside the PR gate, so
  a newly published advisory can't turn an unchanged PR red.
- **Security basics:** helmet, path-traversal guards on the file browser, request
  bodies with unknown fields are refused rather than silently dropped.

## Stack

| Area | Technology |
|---|---|
| Frontend | React 18, Vite 6, TanStack Query 5, Tailwind v4 + Radix (shadcn/ui pattern), xterm.js, Recharts |
| Backend | Node.js 22, Express 5, better-sqlite3 |
| Testing | Vitest, vitest-axe, Playwright (visual regression) |
| Tooling | pnpm workspaces, Forgejo Actions |

**Status:** the planned v1 slices (catalog and live view, UI shell, headless
dispatch) are delivered. Out of scope for v1 by design: multi-user
authentication (access is restricted to a private network), editing agent
definitions in the UI, non-Claude agents.
