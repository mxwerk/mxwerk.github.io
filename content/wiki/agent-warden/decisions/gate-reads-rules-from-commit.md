---
title: The CI gate reads its rules from the commit
description: A check counts as the CI gate only if every input it judges against is in the commit or pinned by it, so the ruleset scan runs from a committed artifact and the producer half of the workflow check stays out of CI.
draft: false
cites:
  - path: docs/adr/0024-a-gate-reads-its-rules-from-the-commit.md
    lines: 93-108, 119-130, 153-172, 227-250, 300-321, 346-349, 454-457, 499-532
  - path: .claude/project-config.yml
    lines: 1-33
  - path: .forgejo/workflows/ci.yml
    lines: 41-46, 73-100, 125-131, 181-228, 242-249
  - path: scripts/gate-artifact.py
    lines: 1-25
verified_at: ae9e10a
---

# The CI gate reads its rules from the commit

> **TL;DR** — This repo has no human reviewer, so a green CI gate has to
> stand in for one. That only works if two runs of one commit cannot disagree,
> so the rules the gate applies are copied into the commit and checked against a
> lock. One half of one check, who produced a change, is left out on purpose.
> [[wiki/agent-warden/index|↑ Wiki]]

## The problem

The project config claimed the pipeline "carves nothing out". It was false:
four gates ran only when someone typed them by hand (ADR 0024). They were not
failing, but nothing would turn red the day they stopped being true.

The ruleset gate also read its rules from outside the repository, and the lock
recorded name and version, not content. Two runs of one commit could be judged
by different rules.

## The decision

A check is admissible as the gate only if every input it judges against is in
the commit, or pinned by it to a verifiable digest.

- **Rules come from a committed artifact.** `.claude/gate/` holds the gate
  runner and only the rulesets the lock pins. CI fails if artifact and lock
  disagree in either direction, so a forgotten rebuild cannot quietly narrow the
  scan.
- **A list replaces the claim.** The config names the three CI jobs instead.
- **One exception.** `npm audit` reads an advisory database at run time. It
  stays, because it judges the code against the world, where re-evaluation is
  the point.

## The producer half is not wired

The workflow check asks two questions. Does the config declare a workflow? That
reads the commit and runs in CI. Who authored this change? That reads an
environment variable and a session marker, which in a container is whatever the
pusher says, so a gate on it cannot fail. It would look like an identity control
and enforce nothing. Identity is left to the forge's branch protection.

| Option | Why not |
|---|---|
| Mount the config directory into the runner | Verdict depends on one machine's private state |
| Add coverage thresholds to the test config | Gives the floor a second home that drifts |

## Limits

- The verifier compares the artifact to the lock, not to the config repo it was
  built from. An in-place ruleset edit there goes unnoticed, and the rebuild is
  a manual step.
- The producer check stays review-time; naming it in the config is a record, not
  enforcement.
- The decision binds this repo only.
