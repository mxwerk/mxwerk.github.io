---
title: agent-warden — Checking What Coding Agents Claim
description: A supervisory layer that checks a coding agent's claims ("tests pass", "file created") against real evidence using local LLMs — tiered, measured, human-in-the-loop.
tags:
  - ai
  - typescript
  - engineering
date: 2026-09-15
---

# agent-warden — Checking What Coding Agents Claim

> **Note for readers:** a personal project, private repository. This page
> describes the design and the measurements, not the code.

## The premise

Coding agents rarely lie on purpose — but they routinely *assert* things the
artifacts don't support: "tests pass" when no test ran, "file created" when a
different file was touched, a step marked done that was skipped.

Grading those claims against the agent's own narration is gameable. So
agent-warden grounds every verdict in **observable evidence** — git diffs, test
runs, hook payloads — and never lets the worker grade itself.

## How it works: claim → evidence → verdict

Each claim is checked by a critic for one failure class — a claimed file that
wasn't touched, a test without a real assertion (fake green), a skipped step, a
sub-agent handoff that drifted from its brief, parallel sessions duplicating work.
A verdict carries the failure class, a confidence, and the evidence
(claimed vs. actual).

**Two tiers, both self-hosted.** A small local model (via Ollama) triages every
claim. Low-confidence verdicts escalate to a larger local model; if the tiers
disagree, the case is flagged for mandatory human review. Nothing leaves the
machine.

**One daemon, pluggable clients.** The project started as a VS Code extension.
Building it showed that the editor panel was not the product — the evidence
pipeline was. It was re-scoped (and documented in ADRs) into an
editor-independent daemon with thin clients: a CLI, an MCP adapter that feeds
verdicts back into an agent session (advisory only, rate-capped), and VS Code as
one optional viewer.

## Measured, not assumed

The interesting part is not that an LLM judges — it's whether that judgment is
any good. The repo contains its own measurement harnesses and audit reports:

| Question | Result |
|---|---|
| LLM critic vs. a deterministic regex extractor (recall, hand-labelled set) | **78 % vs. 33 %**, no false positives either way |
| Does the larger tier earn its latency? (same fixtures) | skipped-step recall 67 % → 100 %, cross-session duplicates 88 % → 100 %, handoff drift unchanged |
| Evidence budget vs. latency target | the larger model missed an 8 s target by ~4.6× at the planned budget — the budget was retargeted to the measured number |

The reports state their own limits (small corpora), and the judge stays
**advisory — it never gates**. Promoting it to a gate would need more evidence
than exists.

## Engineering details worth noting

- **Check-use-check on evidence files.** The daemon verifies that the file
  descriptor it reads is the file it checked. The guarantee is Linux-specific,
  so on other platforms the daemon *refuses* verified reads instead of silently
  degrading.
- **CI without carve-outs.** Lint, typecheck, the full test suite and build run
  on every push and pull request, deliberately without path filters — "a gate
  with a path filter is a gate with a hole." The web-component UI is tested in a
  real browser, with the browser build pinned to the CI image.
- **Dependency advisories handled on the record** — remediation goes through
  pull requests, and a stale risk-acceptance note is rewritten rather than
  silently deleted.
- **23 ADRs** covering the pivot, the escalation design, the MCP contract and the
  security hardening.

## Stack

| Area | Technology |
|---|---|
| Core | TypeScript, Node.js |
| Models | Ollama (two self-hosted tiers) |
| Clients | CLI, Model Context Protocol SDK, VS Code Extension API, Lit |
| Telemetry | OpenTelemetry, uPlot |
| Build & test | esbuild, Vitest (incl. browser mode via Playwright) |
| CI | Forgejo Actions on a self-hosted rootless runner |

**Status:** in active development (milestone 1). Part of a self-hosted agent
platform together with [[projects/claude-setup|the SDLC system]] and
[[projects/agent-cockpit|agent-cockpit]].
