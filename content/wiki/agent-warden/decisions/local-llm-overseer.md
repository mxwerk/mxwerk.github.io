---
title: A local LLM as the overseer
description: The warden judges agents with a small local model anchored to artifacts and a human in the loop, because research favoured external grounding over self-critique and the hardware is a 16 GB laptop.
draft: false
cites:
  - path: docs/adr/0007-local-llm-overseer-direction.md
    lines: 17-29, 33-52, 67-78, 80-108
  - path: docs/research/local-llm-overseer-prior-art.md
    lines: 15-25, 29-45
  - path: docs/adr/0009-cloud-escalation-relaxes-local-only.md
    lines: 76-94
verified_at: ae9e10a
---

# A local LLM as the overseer

> **TL;DR** — The project sets a small local model above a coding agent to
> check the agent's claims against artifacts, and a human decides what to do
> about the result. The model never treats the agent's own narration as a source
> of truth, and it does not act on the agent in the first phase. The "stronger
> judge" in the original plan later became a larger local model, not a cloud
> API. [[wiki/agent-warden/index|↑ Wiki]]

## The problem

Coding agents assert things the artifacts do not support: a step declared done
that was skipped, a test that asserts nothing. The record names these as
laziness and premature self-satisfaction. The earlier chat and observability panel was reclassified as a sense organ,
not the product. The stated hardware ceiling is 16 GB RAM on an Apple M1.

## The decision

An evidence-grounded, tiered, human-in-the-loop overseer. Four principles carry
most of the weight: verdicts anchor to git diffs, real test runs, telemetry and
hook payloads, not the transcript; phase one detects and surfaces but does not
act on the agent; a small local critic triages and a stronger judge takes the
ambiguous cases; and the overseer runs as a separate model from the agent it
judges.

## Rejected alternatives

| Option | Why not |
|---|---|
| Always-on small critic that reads the transcript | The research summary calls it refuted: sub-1B models fail and reasoning-reading judges are gameable. |
| Self-critique inside the worker | No reliability floor, and the same model grades itself. |
| Autonomous overseer that acts on the agent | It can itself be wrong, so acting on unproven verdicts is high-risk. Deferred to a later phase. |

The research behind this (23 sources) found external-grounded correction more
stable than self-correction, and treated AI judges as a complement to humans,
not a replacement.

## What it costs

- More moving parts: a local model, an escalation tier and a grounding harness
  that did not exist before.
- Open-model judges are weaker than frontier ones. The tiering exists to
  cover that gap, and the record names it as a risk.
- The overseer needs guardrails of its own against bias.

## Later change

The original text says ambiguous cases go to a "stronger (cloud) judge". A
later decision resolved that tier to a larger model on hardware the operator
owns, so nothing leaves it: [[wiki/agent-warden/decisions/two-tier-escalation]]. The core model
the overseer applies is in [[wiki/agent-warden/concepts/claim-evidence-verdict]].
