---
title: Where judgment rules are encoded
description: A rule about how to reason before acting is prose in two places, the always-loaded rules and the agent contracts, because no lint rule or edit-time hook can express it.
draft: false
cites:
  - path: docs/adr/013-behavioral-rule-encoding-surface.md
    lines: 19-53
  - path: rules/git-workflow.md
    lines: 195-206
  - path: agents/reviewer.md
    lines: 128-131
  - path: rules/README.md
    lines: 1-20
  - path: docs/TODO/2026-05-22-detection-and-self-healing-cluster.md
    lines: 26-38
verified_at: 82cca7c
---

# Where judgment rules are encoded

> **TL;DR** — Some rules tell an agent how to reason, not what pattern to
> forbid. "The pre-push hook is a floor, not a ceiling" cannot be a lint rule,
> so it lives as prose in the always-loaded rules plus a mirror in the agent
> contracts. The cost is that it depends on the agent following it. [[wiki/harness/index|↑ Wiki]]

## The problem

An agent ran a unit-only gate, saw green, and pushed a selector rename that
only the end-to-end tier exercised. The lesson sat in one project's memory, so
a sibling repository could repeat it. There was no recorded convention for
which surface holds a rule like this.

## The decision

Two constraints drove the answer. Always-loaded rules must stay free of any
particular stack, while lazily injected reference files are for stack-specific
prose and fire on edit. Rulesets hold only regex over source and code-style
notes; neither expresses "read your diff and ask what the hook will not catch".

| Surface | Verdict | Reason |
|---|---|---|
| Ruleset pattern or idiom | rejected | Cannot express a diff-reasoning predicate; an earlier lint attempt was a poor fit. |
| Lazy reference injection | rejected | Fires on edit, not on push, so it is the wrong moment. |
| Static diff-to-tier table | deferred | Would duplicate a planned change-impact router. |
| Pre-push warning hook | optional | Feasible, not required. |
| Always-loaded rule plus agent mirror | chosen | Covers hand-driven sessions and dispatched agents. |

The rule now reads as a short section: before pushing, read the diff and ask
what the hook will not catch, run that tier, and if it cannot be run, say so in
the push message. The reviewer contract carries the pipeline-side mirror and
raises a finding when only the unit tier ran.

## What it costs

This is the weakest enforcement class in the setup. The ADR says plainly that
correctness rests on the agent's adherence until a mechanism exists, and that
two surfaces must be edited together if the wording changes. The project's own
gate still enforces the floor; this rule governs what sits above it.

## Later

No later ADR supersedes this one. The deferred mechanism is still open: the
backlog lists change-impact-aware test routing as a research-class item, and no
such router exists under the scripts, gates, hooks or skills. The rule is
therefore still prose judgment, and holds only as long as the agent follows it.
Compare how harder-edged rules are moved to the edit boundary in
[[wiki/harness/components/edit-boundary-hooks|edit-boundary hooks]] and why a green check
needs its own test in [[wiki/harness/concepts/verify-the-verifier|verify the verifier]].
