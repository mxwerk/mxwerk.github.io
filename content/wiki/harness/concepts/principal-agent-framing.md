---
title: The developer as principal
description: As agents do the typing, the developer becomes a principal who has to answer a principal-agent problem, and the repository answers it with mechanisms rather than trust.
draft: false
cites:
  - path: docs/adr/071-mr-default-under-autonomy-trunk-escape-hatch.md
    lines: 20-27, 50-58
  - path: docs/adr/085-producer-axis-lands-adr-071.md
    lines: 62-80, 111-116
  - path: orchestrator/gates/workflow_check.py
    lines: 67, 280
  - path: rules/agent-identity.md
    lines: 13-24, 31-35
  - path: docs/adr/096-autonomous-merger-is-a-watcher-not-a-bus-effector.md
    lines: 27-30, 55-56
  - path: docs/adr/093-autonomous-review-findings-carry-resolvable-evidence.md
    lines: 31-40
verified_at: 82cca7c
---

# The developer as principal

> **TL;DR** — Once agents write the code, the developer delegates and cannot
> observe every action. That is a principal-agent problem. The repository does
> not assume the agent is aligned; it adds a reviewer chosen by who produced the
> change, separate identities, and checks on the evidence.
> [[wiki/harness/index|↑ Wiki]]

## The idea

A principal delegates work to an agent whose actions are only partly visible.
The standard remedies are monitoring, separation of roles and verifiable
reporting. Each has a counterpart here.

## Where it is enforced

- **Review chosen by producer.** ADR-071 reasons that once code is not
  hand-written, the review slot stops being ceremony and becomes the human
  gating the machine. ADR-085 gives it an input: `workflow_check` resolves a
  producer (an explicit environment variable, else a session marker) and sets
  `review_required` when that producer is an agent. A value that is neither
  `human` nor `agent` falls through, so a typo cannot open the escape hatch.
  See [[wiki/harness/decisions/agent-changes-default-to-review|agent changes default to review]].
- **Identity separation.** The agent-identity rule says a rejected credential is a
  halt, not a branch: the agent reports and stops rather than trying other
  secrets, because a write under the wrong identity corrupts the record of who
  did what. Separately, the review verdict is written only by a dedicated
  review account, and the merger is its own account, since the forge's
  self-review rule keys on the account.
- **Evidence checks.** An autonomous review's finding counts only if its
  `path:line` citation resolves. When this was first measured, a large share of
  cited findings pointed at lines that did not exist.

## What it costs / where it does not reach

ADR-085 states that the gate classifies but does not reject: a direct push that
ignores `review_required` is not stopped until a per-clone pre-push hook is
active. Producer detection defaults to `agent` whenever a session marker is
present, so it over-triggers by design and the opt-out is a self-declared
variable. Identity separation limits what an agent can do, not whether the
operator, who holds the whitelist, will read what they approve. Evidence checks
test that a citation exists, not that the claim is true. The controls reduce
what must be trusted; they do not remove the operator from the loop.
Compare [[wiki/harness/concepts/verify-the-verifier|verify the verifier]] for the checks on
the checks.
