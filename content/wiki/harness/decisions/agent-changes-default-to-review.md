---
title: Agent-authored changes default to review
description: Whether a change needs review depends on who wrote it, not only on the repository's mode, so the land gate resolves a second axis, the producer.
draft: false
cites:
  - path: docs/adr/071-mr-default-under-autonomy-trunk-escape-hatch.md
    lines: 19-64
  - path: docs/adr/085-producer-axis-lands-adr-071.md
    lines: 27-37, 63-92, 111-117
  - path: orchestrator/gates/workflow_check.py
    lines: 172-195, 213-228
  - path: rules/git-workflow.md
    lines: 6-12, 57-70
verified_at: 82cca7c
---

# Agent-authored changes default to review

> **TL;DR** — "Trunk or merge request?" mixes two questions: what the
> repository does, and who wrote the change. For a change an agent wrote, the
> default is a small reviewed merge request in either mode; committing straight
> to trunk is a per-change escape hatch. The gate classifies this reliably; what
> it can reject depends on a per-clone hook. [[wiki/harness/index|↑ Wiki]]

## The problem

The earlier trunk decision ([[wiki/harness/decisions/deterministic-gate-replaces-review|a deterministic gate replaces review]])
assumed hand-written work, where a merge request on a solo repo has an empty or
weak review slot. Once runs became semi-autonomous, the slot turned
load-bearing: the reviewer is a human gating a machine, and a bad direct push is
on `main` already. The first ADR (071) also found that a trunk repo keeps the
same branch forever, so a phase-approval marker that goes stale only on a
branch switch never goes stale.

## The decision

ADR-071 separates integration frequency (merge to trunk quickly) from the review
gate (none or mandatory). Keeping review does not require long-lived branches if
merge requests stay small and are squash-merged fast.

ADR-085 then found that the default was written in prose only: the mode
resolver reads repository shape, and nothing in the chain read the author. It
added a second axis rather than a skill-layer default, because a convention that
lives in one skill is bypassed by every other entry point.

| Axis | Question | Resolved by |
|---|---|---|
| Mode | What does this repository do? | `workflow:` in the project config |
| Producer | Who authored this change? | `CLAUDE_CHANGE_PRODUCER`, else a session marker |

An explicit value wins; otherwise a Claude Code session marker means agent;
otherwise human. An unrecognised value falls through to the marker test, so a
typo in the escape hatch does not grant it. On a trunk repo an agent change now
gets `review: mr-required` instead of `green-gate`, and the directive names which
record it followed.

A later amendment exempts pushes that touch only the backlog directory, judged
per commit and failing closed, because a seven-step ceremony for a ticket gets
skipped exactly when filing matters.

## What it costs and what is not enforced

The producer is inferred from an environment variable, so "human" is a claim by
whoever sets it. ADR-085 stated the gap openly: the gate classified but did not
reject. The current rule text says a pre-push gate now rejects an agent push to
the default branch, but it **fails open** and runs only where the tracked script
is installed as the clone's hook, which does not travel with the repository.
An absent block is not evidence the push was allowed.

## Later

ADR-085 supersedes nothing: the trunk gate still governs human trunk work, and
ADR-071 governs agent work. Related: [[wiki/harness/concepts/principal-agent-framing|principal-agent framing]]
and [[wiki/harness/components/gate-runner|the gate runner]].
