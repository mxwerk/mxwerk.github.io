---
title: Two-tier escalation
description: A small model judges every claim, only low-confidence verdicts are re-judged by a larger model, and a disagreement between the two forces human review.
draft: false
cites:
  - path: docs/adr/0009-cloud-escalation-relaxes-local-only.md
    lines: 13-23, 40-49, 59-63, 76-105, 115-121, 130-134
  - path: src/core/harness/escalate.ts
    lines: 1-22, 39-50, 65-68, 129-184
  - path: docs/audits/escalation-comparison.md
    lines: 12-21, 23-31
  - path: src/core/harness/types.ts
    lines: 28-35
  - path: src/core/config/env.ts
    lines: 151-154
verified_at: ae9e10a
---

# Two-tier escalation

> **TL;DR** — A small local model triages every claim. A verdict at or below a
> confidence threshold is re-judged by a larger model, both verdicts are shown,
> and if their kinds differ the case is flagged for mandatory human review.
> The strong tier turned out to be a larger model on the operator's own
> machine, not a cloud API, so a failure degrades to the local verdict.
> [[wiki/agent-warden/index|↑ Wiki]]

## The problem

A tiered design needs a stronger judge, but the project was local-only, and an
escalated payload can contain a diff from graded coursework or another
project's data. The question was where the strong tier runs.

## The decision

- The local triage model sees every claim. If its confidence is at or below
  0.6 (the default threshold), the same case is re-judged by the strong tier.
- The strong tier is a larger model (around 14B) on the operator's own
  hardware. Nothing goes to a third party.
- Both verdicts are returned. If their kinds differ the result carries
  `disagreement`, the mandatory-review signal. Escalation never gates.
- If the strong tier is unreachable, times out (120 s default) or is
  rate-limited, the local verdict comes back marked degraded. It never blocks.
- The rate limit is a rolling window: three strong-tier calls per fifteen
  minutes by default.

| Option | Why not |
|---|---|
| Third-party API judge with redaction | Data leaves the machine and raises a controller question. Kept as a documented fallback if the larger model is not good enough. |
| Larger model on the always-on server | No discrete GPU and too little free memory for anything above the 7B (ADR-0009). |
| Second local model, no escalation host | Judged RAM-infeasible next to the triage model, the editor and the agent on 16 GB. |

## What it costs

- The strong tier is slow: the timeout is 120 s because a cold reload of the
  14B approached 60 s.
- The audit measured the lift on small sets: handoff judging 15 of 16 for both models, cross-session
  duplicates 7 of 8 against 8 of 8, and skipped-step recall 6 of 9 against 9 of
  9 (`docs/audits/escalation-comparison.md`). The audit calls these small
  hand-labelled sets, and says a model that only matches the 7B does not
  justify its cost.

## Later changes

The original plan called the strong tier "cloud", with a euro budget and an
8 s latency target. The budget went with the cloud; the 8 s proved
unreachable and became 40 s
([[wiki/agent-warden/decisions/evidence-read-hardening]]). Why the verdict carries `disagreement` as a field:
[[wiki/agent-warden/concepts/claim-evidence-verdict]]. The recall that feeds this tiering:
[[wiki/agent-warden/concepts/measured-recall]].
