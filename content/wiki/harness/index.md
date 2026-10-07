---
title: Harness wiki
kind: index
---

# Harness wiki

Distilled, cross-linked knowledge about this development system. Every page
cites the files it describes and the commit it was checked against
(`cites:` / `verified_at:`); `check_wiki.py --project --repo .` reports a page
STALE once a cited file changes. Pages start as `draft: true`; the operator approves a page by setting `draft: false`.

## Decisions

- [[wiki/harness/decisions/agent-changes-default-to-review|Agent-authored changes default to review]] — Whether a change needs review depends on who wrote it, not only on the repository's mode, so the land gate resolves a second axis, the producer.
- [[wiki/harness/decisions/deterministic-gate-replaces-review|A deterministic gate replaces review on trunk]] — On a trunk-based repo the pipeline commits straight to main, and a deterministic local gate takes the place of the pull-request review.
- [[wiki/harness/decisions/judgment-rules-encoding|Where judgment rules are encoded]] — A rule about how to reason before acting is prose in two places, the always-loaded rules and the agent contracts, because no lint rule or edit-time hook can express it.
- [[wiki/harness/decisions/main-thread-orchestrates|The main thread orchestrates, subagents work]] — Interactive gates and operator questions stay in the main session, drafting and review run in disposable subagents, and orchestration depth is capped at one level.
- [[wiki/harness/decisions/push-router-spawn-protocol|A push router replaces per-agent polling]] — One central router reads message channels and starts consumers, and after a substrate change it is a deterministic script rather than the LLM agent the ADR first described.

## Concepts

- [[wiki/harness/concepts/draft-first|Draft first, plans append-only]] — Generated documentation lands hidden and reaches readers only through an operator-approved promotion, and plans can be corrected but never deleted.
- [[wiki/harness/concepts/principal-agent-framing|The developer as principal]] — As agents do the typing, the developer becomes a principal who has to answer a principal-agent problem, and the repository answers it with mechanisms rather than trust.
- [[wiki/harness/concepts/shadow-before-authority|Shadow before authority]] — An automated decision is run in a mode that can only record, and is measured there, before anything gives it the power to act.
- [[wiki/harness/concepts/verify-the-verifier|Verify the verifier]] — A check that reports green is not evidence until it has been shown to report red on a known-bad input.

## Components

- [[wiki/harness/components/edit-boundary-hooks|Edit-boundary hooks]] — Rules that must hold are enforced by hooks on the edit and shell call itself, so no entry point can route around them.
- [[wiki/harness/components/gate-runner|The gate runner]] — One script turns a repository's locked rulesets plus a universal set into a single exit code, and it separates "failed" from "could not check".
- [[wiki/harness/components/issue-to-pr-chain|The issue-to-PR chain]] — Cron-driven scripts take a labeled issue to a reviewed pull request, with an operator marker before any code lands and merging still outside the chain.
