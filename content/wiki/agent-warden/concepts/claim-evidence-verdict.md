---
title: Claim, evidence, verdict
description: Every check turns an agent's claim plus an observable artifact into a Verdict that is confirmed, refuted or abstain, and a missing signal yields abstain, never a clean pass.
draft: false
cites:
  - path: src/core/harness/critic.ts
    lines: 9-14, 21-22, 24-40, 52-90
  - path: src/core/harness/types.ts
    lines: 1-8, 9-27, 28-43
  - path: README.md
    lines: 15-24
  - path: docs/adr/0010-grounding-harness-design.md
    lines: 21-26, 70-72, 78-81, 90-94
verified_at: ae9e10a
---

# Claim, evidence, verdict

> **TL;DR** — The warden never judges what an agent says about its work. It
> takes a claim, compares it with an artifact such as a git diff, and emits a
> Verdict of confirmed, refuted or abstain. When the signal needed to judge is
> missing, the answer is abstain, not a pass. [[wiki/agent-warden/index|↑ Wiki]]

## The model

The entry point is `critiqueClaim(claim, artifact) → Verdict`. The claim is
what the agent asserted ("tests pass", "created file X"). The artifact is
something observable: a diff, a file list, a test run. The design rests on one
rule: judgments anchor to artifacts, never to the agent's self-narration,
because a judge that reads the agent's reasoning can be talked round. The
critic's own comments state this, and the prompt it builds says "Judge ONLY the
diff".

## What a Verdict carries

- `pathology` — which failure class produced it, such as
  `file-claim-mismatch` or `claim-substantiation`.
- `kind` — `confirmed`, `refuted` or `abstain`.
- `confidence` — 0 to 1. The type comment says abstain is always low and crisp
  artifact signals are high.
- `reason` — one sentence.
- `evidence` — optional, class-specific: claimed, actual, missing and extra
  file lists, assertion-free tests, cross-session collisions.

Two evidence fields flag verdicts to read with care. `disagreement` marks a
case where the local and escalated models disagreed
([[wiki/agent-warden/decisions/two-tier-escalation]]). `truncatedChars` is set when the evidence
exceeded a size budget, so the verdict was judged on a clipped artifact and is
not a judgement on the whole change.

## Abstain means "could not check"

The design record resolved this explicitly: when there is no diff signal
(a git failure), an empty claim, or an unreadable transcript, the result is
abstain, not a passing verdict. The LLM critic follows the same path: a failed
model call yields abstain with confidence 0 and reason "critic unavailable",
and an answer that cannot be parsed yields abstain with "unparseable critic
response". A genuine abstain from the model gets confidence 0 as well.

## Honest limits

- The LLM critic is advisory. Its confidence is fixed at 0.5 for confirmed and
  refuted, its reason is tagged `[local-critic, advisory]`, and the comments say
  a verdict must never gate a loop.
- The file-claim check is strict set equality, so a deliberately partial claim
  reads as refuted. The design record lists this, and that `git diff` omits
  untracked new files, as known gaps.

Each pathology has its own critic: [[wiki/agent-warden/components/critics]]. How well claims are
found in the first place: [[wiki/agent-warden/concepts/measured-recall]].
