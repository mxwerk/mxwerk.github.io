---
title: The quality gate
description: One CI job runs lint, type check, the committed ruleset gate, the unit suites and a screenshot comparison in a pinned browser image on every pull request, with no path filter.
draft: false
cites:
  - path: .forgejo/workflows/ci.yml
    lines: 1-22, 26-56, 58-167
  - path: .forgejo/workflows/sast.yml
  - path: .githooks/pre-push
    lines: 1-10, 54-73
  - path: scripts/visual-in-image.sh
    lines: 1-32
  - path: frontend/playwright.config.ts
  - path: .claude/project-config.yml
    lines: 1-10
verified_at: 75e94b4
---

# The quality gate

> **TL;DR** — The repository has one author and no human reviewer, so the pipeline is what
> says yes to a change. A single job runs ESLint, the type check, a pattern gate whose
> rules are committed with the code, the unit suites of both packages, and a comparison of
> 16 screenshots against stored baselines. It runs on every pull request and every push to
> the main branch, with nothing skipped by path. [[wiki/agent-cockpit/index|↑ Wiki]]

## What it is

The workflow `ci.yml` with two jobs, a nightly `sast.yml`, and a pre-push hook that runs
the screenshot tier locally when a push touches frontend sources.

## How it works

**`gate`** runs the steps in order and stops at the first failure: install from the
frozen lockfile, lint, type check, verify that the committed gate artifact still matches
its lock file, run the forbidden-pattern rules over backend and frontend, check that only
one UI primitive framework is in use, run the gate artifact's own tests, run the unit
tests, run the visual tier.

**The pattern rules travel with the commit.** They come from a private configuration
repository that is never cloned onto a runner. A copy of the pinned rulesets and the
runner is committed, and a verify step fails when copy and lock disagree in either
direction.

**The visual tier has one renderer.** A screenshot baseline belongs to the machine that
rendered it. The job runs in a browser image pinned to the same version as the lockfile,
and the local hook runs the tier inside that same image instead of on the developer's
machine. The 16 baselines are 8 states of the shell at two viewport widths, among them
the error state and the judge being offline.

**`branch-report`** fails a pull request that changes product code without the written
report it owes. It is a separate job because it answers in seconds and needs none of the
browser setup.

**The hook is narrower than the gate on purpose.** It runs the visual tier only for
frontend changes, and if its own scope check errors it runs the tier instead of skipping.

## What it costs / limits

- **Coverage is reported, not enforced.** The unit step fails on a failing test and writes
  a coverage summary; a comment in the workflow says no threshold is applied in CI.
- **The image pin lives in three places** that have to move together: the workflow's
  runner label, the local script, and the runner's own configuration outside the
  repository.
- **Dependency advisories are checked nightly,** not per pull request, so a vulnerable
  dependency can merge and be reported the next day.
- **The runner label must exist.** A label no runner offers does not fail the job; it
  queues forever. The workflow's header records that this happened.
- This page reads the configuration. No pipeline run was made while writing it.

## Later changes

The gate replaced an earlier workflow that ran only the visual tier and only for frontend
paths. A comment in the local script still speaks of twelve baselines; the directory holds
sixteen.
