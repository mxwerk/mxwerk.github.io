---
title: Measured recall, with its n
description: On nine hand-labelled claims the regex extractor finds three, the default 3B model all nine but with four false positives, and a 7B model seven with none, so recall alone would pick the wider net over the better one.
draft: false
cites:
  - path: docs/audits/critic-recall.md
    lines: 6-15, 44-58
  - path: docs/audits/escalation-comparison.md
    lines: 8, 16-20
  - path: docs/audits/detection-recall.md
    lines: 6-16
  - path: src/bench/criticCorpus.ts
    lines: 23-41
  - path: src/bench/criticRecall.ts
    lines: 57-99, 101-118
  - path: tests/criticRecall.spec.ts
    lines: 33-67
  - path: tests/escalationComparison.spec.ts
    lines: 66-67
verified_at: 786cda0
---

# Measured recall, with its n

> **TL;DR** — The warden has to notice that an agent *said* it ran the tests
> before it can check whether it did. On nine hand-labelled claims a regex
> finds three. The default 3B model finds all nine — and also fires on four
> negatives; a 7B model finds seven and fires on none. Nine is a small number,
> and recall alone would have ranked the wider net above the better one.
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
| `llama3.2:3b` (the default critic) | 9 of 9 | 4 |
| `qwen2.5:7b-instruct-q4_K_M` | 7 of 9 | 0 |

The regex catches exactly the three it was written for. The 7B model adds four
of the six hard ones and misses both paraphrased dependency installs ("Added
axios to the deps."). The default 3B model catches those two as well — and
reports an action in all three negatives, including a statement of future
intent, so its perfect recall comes with a false positive on every case where
the right answer was *nothing*.

## How far the figures carry

- **It is the gap, not the system.** Two thirds of the positives were chosen
  because the regex fails on them. On a separate corpus of fifteen
  regex-friendly cases the deterministic detectors score fifteen of fifteen.
- **n = 9, and it moves.** The tier comparison ran the same nine sentences
  through a 7B and a 14B model: six of nine and nine of nine. Six against
  seven on an unchanged corpus is one sentence — the resolution of the
  measurement, not a finding. That is now measured twice rather than argued:
  `qwen2.5:7b-instruct-q4_K_M` scored six there and seven here, on the same
  corpus, with nothing changed but the run.
- **The seven belonged to the 7B model** — established by re-measurement, not
  by the record. The report used to name only the Ollama host, so its `7 of 9`
  could be attributed to no model at all (#103); re-running both models on the
  unchanged corpus reproduces `7 of 9, 0 false positives` for
  `qwen2.5:7b-instruct-q4_K_M`, which is where that figure came from. Each row
  now carries its model.
- **The 3B's four false positives are not a stable four.** Two runs both
  scored 9 of 9 with four, but on different negatives — so the count is the
  measurement's resolution, and *which* negative it fires on is not.
- **Never in CI.** The live rows are written only when a model is reachable; a
  run without one leaves the committed report alone rather than overwriting it
  with "not measured".

## What follows

A cheap deterministic pass first, a model for what it misses, and a stronger
model only where the first is unsure: [[wiki/agent-warden/decisions/two-tier-escalation]].
