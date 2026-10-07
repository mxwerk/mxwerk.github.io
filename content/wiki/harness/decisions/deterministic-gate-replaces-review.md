---
title: A deterministic gate replaces review on trunk
description: On a trunk-based repo the pipeline commits straight to main, and a deterministic local gate takes the place of the pull-request review.
draft: false
cites:
  - path: docs/adr/010-trunk-execution-path-sdlc-pipeline.md
    lines: 22-47
  - path: rules/git-workflow.md
    lines: 86-104
  - path: orchestrator/gates/run.py
    lines: 588-596, 678-690
verified_at: 3c2f0d1
---

# A deterministic gate replaces review on trunk

> **TL;DR** — On a solo, trunk-based repository a pull request has no second
> reader, so its review step protects nothing. The pipeline commits straight to
> `main` instead, and what a reviewer would have caught is moved into a gate
> that runs the same way every time: green, or the change does not land.
> [[wiki/harness/index|↑ Wiki]]

## The problem

The workflow rules named trunk-based development as the default for solo
repositories, but every pipeline component ended in "open a merge request"
and never read which mode the repository was in. The pipeline could not run on
the very repository that defines it.

## The decision

The trunk path is **pure commit-to-main**. A short-lived local branch is an
escape hatch, not the standard.

| Option | Why not |
|---|---|
| Short-lived branch as the default | What matters is integration frequency, not that a branch exists. An agent that integrates on every run already meets it — the branch is pure overhead. |
| Keep the pipeline MR-only | Contradicts the documented default and blocks trunk repositories outright. |

## What takes the reviewer's place

The land step is fixed: run the full local gate, `git pull --rebase`, re-run
the gate if trunk moved, then commit and push. Breakage found after the push is
fixed forward, never auto-reverted.

`--gate all` runs the gates the locked rulesets require plus a universal set
that applies to every repository. The exit code is the contract: `fail`
exits 1, `error` exits 2. A gate that could not check — no type checker
configured, say — reports `unverifiable`: it exits 0 so that a legitimate
absence does not get the whole gate switched off, but the verdict is not
recorded as a pass.

## What it costs

The human checkpoint is gone, so the gate has to be deterministic in earnest or
trunk breaks. The ADR left four risks open for the implementation — atomicity
of gate-then-push, push contention between parallel tasks, auto-revert, and
rebase conflicts across machines.

## Later narrowed

This decision covers *who reviews on trunk*. A later one adds a second
question — *who authored the change* — and puts agent-authored changes behind
a review gate in either mode (ADR-071, ADR-085).
