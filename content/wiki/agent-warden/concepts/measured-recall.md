---
title: Measured recall, with its n
description: On nine hand-labelled claims the LLM extractor finds seven and the regex extractor three, and that figure is a gap measurement on a corpus built to defeat the regex, not the system's recall.
draft: false
cites:
  - path: docs/audits/critic-recall.md
    lines: 6-9, 37-51
  - path: docs/audits/escalation-comparison.md
    lines: 8, 16-20
  - path: docs/audits/detection-recall.md
    lines: 6-16
  - path: src/bench/criticCorpus.ts
    lines: 23-41
  - path: src/bench/criticRecall.ts
    lines: 30-55, 102-112
  - path: tests/criticRecall.spec.ts
    lines: 26-41
  - path: tests/escalationComparison.spec.ts
    lines: 66-67
verified_at: ae9e10a
---

# Measured recall, with its n

> **TL;DR** — The warden has to notice that an agent *said* it ran the tests
> before it can check whether it did. On nine hand-labelled claims a regex
> finds three and a local LLM finds seven, with no false positive from either.
> Nine is a small number, and a second run on the same nine scored six.
> [[wiki/agent-warden/index|↑ Wiki]]

## What is measured

One step only: turning an agent's prose into a narrated action — *ran the
tests*, *installed a dependency*, *ran a command*. A claim nobody extracted is
never checked against evidence, so a miss here is silent.

The corpus is twelve sentences: six positives phrased the way the regex was
not written for ("The full suite is green after my edits."), three positives
it should catch, and three negatives such as a statement of future intent. A
positive counts as recalled only if every expected category is found; anything
found beyond the expected set is a false positive.

## The figures

| Extractor | Recall | False positives |
|---|---|---|
| regex (deterministic) | 3 of 9 | 0 |
| local LLM | 7 of 9 | 0 |

The regex catches exactly the three it was written for. The LLM adds four of
the six hard ones and misses both paraphrased dependency installs ("Added
axios to the deps.").

## How far the figures carry

- **It is the gap, not the system.** Two thirds of the positives were chosen
  because the regex fails on them. On a separate corpus of fifteen
  regex-friendly cases the deterministic detectors score fifteen of fifteen.
- **n = 9, and it moves.** The tier comparison ran the same nine sentences
  through a 7B and a 14B model: six of nine and nine of nine. Six against
  seven on an unchanged corpus is one sentence — the resolution of the
  measurement, not a finding.
- **The seven is not tied to a model.** The report records the Ollama host it
  ran against, not the model name, so the run cannot be repeated exactly.
- **Never in CI.** The live rows are written only when a model is reachable; a
  run without one leaves the committed report alone rather than overwriting it
  with "not measured".

## What follows

A cheap deterministic pass first, a model for what it misses, and a stronger
model only where the first is unsure: [[wiki/agent-warden/decisions/two-tier-escalation]].
