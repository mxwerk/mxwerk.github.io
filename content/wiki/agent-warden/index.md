---
title: agent-warden wiki
kind: index
---

# agent-warden wiki

Distilled, cross-linked knowledge about this project. Every page cites the
files it describes and the commit it was checked against (`cites:` /
`verified_at:`). `node scripts/check-wiki-freshness.mjs --repo .` reports a page
STALE once a commit changes a cited file without touching the page, and it runs
in CI on every pull request and every push to `main`. Pages start as
`draft: true`; the operator approves a page by setting `draft: false`, and the
checker skips a draft because an unapproved page claims nothing.

Until 2026-10-20 this paragraph named `check_wiki.py --project --repo .`, and
that program existed nowhere — not in this repo, not in the user-scope config,
and no CI job invoked any wiki checker. Eleven pages carried a `verified_at:`
that nothing validated, which reads as evidence and was not. Recorded here
rather than quietly corrected, because a reader who trusted the old sentence
deserves to know which of the two they were reading (#112).

## Concepts

- [[wiki/agent-warden/concepts/claim-evidence-verdict|Claim, evidence, verdict]] — Every check turns an agent's claim plus an observable artifact into a Verdict that is confirmed, refuted or abstain, and a missing signal yields abstain, never a clean pass.
- [[wiki/agent-warden/concepts/measured-recall|Measured recall, with its n]] — On nine hand-labelled claims the regex extractor finds three, the default 3B model all nine but with four false positives, and a 7B model seven with none, so recall alone would pick the wider net over the better one.

## Decisions

- [[wiki/agent-warden/decisions/evidence-read-hardening|Evidence-read hardening]] — The daemon refuses a malformed evidence selector, refuses a swapped file path, and bounds evidence size, because an agent that controls the request could otherwise make the warden silently judge nothing, or the wrong file.
- [[wiki/agent-warden/decisions/gate-reads-rules-from-commit|The CI gate reads its rules from the commit]] — A check counts as the CI gate only if every input it judges against is in the commit or pinned by it, so the ruleset scan runs from a committed artifact and the producer half of the workflow check stays out of CI.
- [[wiki/agent-warden/decisions/hybrid-daemon-pluggable-surfaces|One daemon, pluggable surfaces]] — A single always-on daemon owns capture and judgment, and the CLI, MCP and editor clients are thin HTTP clients of it, so adding a surface needs no daemon rework.
- [[wiki/agent-warden/decisions/local-llm-overseer|A local LLM as the overseer]] — The warden judges agents with a small local model anchored to artifacts and a human in the loop, because research favoured external grounding over self-critique and the hardware is a 16 GB laptop.
- [[wiki/agent-warden/decisions/two-tier-escalation|Two-tier escalation]] — A small model judges every claim, only low-confidence verdicts are re-judged by a larger model, and a disagreement between the two forces human review.

## Components

- [[wiki/agent-warden/components/critics|The critics]] — Each critic checks one failure class; the file-diff, test-source, skipped-step and collision checks are deterministic, while the model-backed critics are advisory and never gate.
- [[wiki/agent-warden/components/daemon|The localhost daemon]] — The daemon is a loopback-by-default HTTP server plus an opt-in file watcher that turns transcripts and git diffs into verdicts without ever acting on an agent.
- [[wiki/agent-warden/components/mcp-surface|The MCP surface]] — The MCP adapter is a loopback-only, stateless, read-and-evaluate wrapper over the daemon, with a capability set fixed at build time and guards that run before anything reaches the daemon.
- [[wiki/agent-warden/components/verdict-telemetry|Verdict telemetry]] — The watcher can push every verdict as OTLP metrics and logs to an existing collector, which gives a trend history that a sibling project reads, at the cost of a stack the warden does not ship.
