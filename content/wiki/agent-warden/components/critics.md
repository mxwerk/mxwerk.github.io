---
title: The critics
description: Each critic checks one failure class; the file-diff, test-source, skipped-step and collision checks are deterministic, while the model-backed critics are advisory and never gate.
draft: false
cites:
  - path: src/core/harness/fileClaimMismatch.ts
    lines: 47-92
  - path: src/core/harness/assertionFreeTest.ts
    lines: 9-12, 19-21, 41-73
  - path: src/core/harness/skippedStep.ts
    lines: 23-43, 100-135
  - path: src/core/harness/skippedStepEvidence.ts
    lines: 20-22, 29-39
  - path: src/core/harness/skippedStepCritic.ts
    lines: 19-26, 85-121
  - path: src/core/harness/handoffFidelity.ts
    lines: 24-30, 38-38, 71-98
  - path: src/core/harness/handoffCritic.ts
    lines: 14-19, 24-24
  - path: src/core/harness/crossSession.ts
    lines: 9-19, 32-77
  - path: src/core/harness/crossSessionCritic.ts
    lines: 7-16, 21-21
  - path: src/core/harness/critic.ts
    lines: 4-15, 22-22, 52-90
  - path: src/core/harness/transcript.ts
    lines: 15-20
  - path: src/core/harness/testEvidence.ts
    lines: 9-9, 21-44
  - path: src/core/harness/gitEvidence.ts
    lines: 110-137
  - path: docs/audits/detection-recall.md
    lines: 6-16, 22-32
  - path: docs/audits/critic-judge-recall.md
    lines: 8-20
verified_at: ae9e10a
---

# The critics

> **TL;DR** — Each critic hunts one failure class and returns a verdict of
> `confirmed`, `refuted` or `abstain`. The ones with a ground-truth artifact (a
> git diff, test source, tool calls) are deterministic; the ones that must
> judge meaning call a local model and are advisory, with confidence 0.5.
> [[wiki/agent-warden/index|↑ Wiki]]

## The table

| Critic (pathology) | Failure class | Deterministic or model | Evidence it reads | Confidence |
|---|---|---|---|---|
| file-claim-mismatch | Files the agent says it touched differ from the diff | deterministic | paths from Edit/Write/MultiEdit/NotebookEdit tool calls vs `git diff --name-only` | 1 |
| assertion-free-test | A test that asserts nothing | deterministic (regex) | changed `*.spec`/`*.test` files; `expect`/`assert` in each `it`/`test` block | 0.8 |
| skipped-step | Narrated action never performed ("ran the tests") | regex claim, deterministic judge | prose claims vs Bash commands and dependency-manifest changes in the diff | 0.7 |
| handoff-fidelity | A subagent's report not matching what happened | deterministic | paths in the subagent result vs the diff; empty diff after "done" | 0.6 |
| cross-session-collision | Parallel sessions editing the same file | deterministic | edited paths per session | 0.8 |
| claim-substantiation | A free-form claim the diff may not support | model | the unified diff, size-bounded | 0.5 |

Model-backed variants sit beside them. The skipped-step critic uses the model
only to *extract* claims; the deterministic check still judges. The handoff
critic (brief against result) and the duplicate-work critic (session intents)
genuinely judge, since no artifact answers "same work"; both are advisory and
pull-only.

Every critic abstains (confidence 0) when its signal source is absent, rather than returning a clean verdict.

## Measured figures

- **Deterministic detectors:** 15 of 15 injected faults flagged (5 of 5 per
  class for file-claim, assertion-free, skipped-step), and 8 of 8 controls held
  (`detection-recall.md`). The audit's caveat: the fixtures are hand-seeded and
  were authored together with the detectors, so this shows the pipeline is
  internally consistent and a regression floor, not real-world recall,
  especially for skipped-step.
- **Judging critics:** handoff-semantic 6 of 6, duplicate-work 4 of 4, with no
  false positives or negatives (`critic-judge-recall.md`). The audit calls the
  set small and hand-labelled, "necessary, not sufficient"; it needs a live
  model and does not run in the CI gate.

## Limits

The deterministic claim sides are gameable regexes. `git diff` does not list
untracked files, so a newly created, claimed file is not covered. Handoff
checks attribute a session-wide diff to each subagent. Extraction recall is in
[[wiki/agent-warden/concepts/measured-recall]]; the claim-to-verdict model is in
[[wiki/agent-warden/concepts/claim-evidence-verdict]].
