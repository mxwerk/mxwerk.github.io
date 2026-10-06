---
title: Engineering AI-Assisted Development
description: A quality-first SDLC system built around Claude Code — spec-driven workflow, deterministic gates, a principal-agent framework for AI oversight, and an autonomous issue-to-pull-request chain.
tags:
  - ai
  - devops
  - engineering
date: 2026-06-28
---

# Engineering AI-Assisted Development: A Quality-First Approach

> **Note for readers:** This is a sanitized architectural writeup of a personal
> SDLC engineering project — not a product, not open-source (it holds private
> configuration). It documents the system design, principles, and engineering
> decisions. The goal is to show *how* I think about AI-assisted development, not
> to hand out the repo.

---

## The Problem: Vibecoding Produces Bad Code

AI coding assistants are genuinely powerful — and genuinely risky. The common
failure mode is what practitioners now call "vibecoding": accepting model output
without systematic verification, accumulating implicit dependencies, and shipping
code that compiles but violates the project's own architecture, test coverage
expectations, and style contracts.

The gap isn't in the model's capability. It's in the *principal-agent structure*
around it.

When a developer delegates work to an AI agent, the classic principal-agent
problem appears: information asymmetry, misaligned incentives (the agent
optimizes for a plausible next token, not for your team's architecture), and
monitoring cost. The developer — now the principal — needs controls that make
delegated work *verifiable*, not just plausible.

This project is my answer to that problem.

---

## What I Built

A personal multi-agent SDLC system built on top of Claude Code, structured around
a single premise: **quality is not willpower, it is a system.**

The setup consists of:

- **31 slash commands** and **49 skills** covering the full development
  lifecycle: requirements elicitation, spec writing, plan generation, code
  review, test generation, dependency auditing, ADR authoring, CI optimization
- **30+ scoped subagents** — each knows exactly what it is responsible for and,
  critically, what it is *not*
- **Deterministic quality gates** that run before any commit lands: secret
  scanning, test coverage floors, type checking, lint, architecture dependency
  rules, and forbidden patterns
- **34 lifecycle hooks** — shell and Python commands that fire on Claude Code
  events (`PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`) to
  enforce invariants without relying on agent judgment — including a hook that
  detects when the system's own documentation drifts from its inventory
- **43 policy-as-code rulesets** — YAML-declared rules per tech stack, injected
  only when the agent edits a matching file (zero memory overhead for irrelevant
  rules)
- **96 Architecture Decision Records (ADRs)** for every non-trivial design choice,
  so the reasoning is preserved and reviewable, not just the outcome

---

## The Core Engineering Principle: Spec-Driven Development

The most important workflow decision is the gate *before* the agent writes a
single line of code.

```
Spec → Plan → Tasks → Code → Gates → Land
```

No task enters the implementation stage without a written spec. The spec drives
the plan; the plan is decomposed into tasks with explicit pre- and
post-conditions. Each task is handed to a scoped subagent — not an omnibus
"do everything" prompt.

This mirrors how a senior engineer reviews a ticket before writing code, except
it is enforced structurally, not by discipline. An agent that skips the spec
cannot reach the coder subagent.

**Why this matters:** ad-hoc prompting ("just add this feature") produces code
the agent cannot validate against anything. Spec-driven prompting gives the agent
and the quality gates a shared contract to check against.

---

## Quality Gates: The Floor That Doesn't Move

Human code review is inconsistent across fatigue, distraction, and time pressure.
Agent-generated code review is inconsistent across context window limits and
hallucination. Deterministic gates are neither.

Gates run unconditionally before any commit and must pass for the land step to
proceed. Core gate set:

| Gate | Tool | What it catches |
|---|---|---|
| Secret scanning | gitleaks | credentials, API keys, tokens in diff |
| Type checking | tsc / mypy | type contract violations |
| Lint | ESLint / Ruff | style + banned patterns |
| Unit + integration coverage | Vitest / pytest-cov | coverage floor per module |
| Architecture rules | dependency-cruiser | imports that violate the declared layer graph |
| SAST | semgrep (rules) | common security anti-patterns |

The architecture gate is worth singling out. dependency-cruiser encodes the
project's layer contract — e.g. "UI components do not import directly from the
data layer" — and fails the build if any new import violates it. An AI agent
cannot unconsciously collapse the architecture by taking a convenient shortcut.

Since the first version, the gate layer has grown to cover the process itself:
whether a repo's declared workflow allows a direct push, whether CI config and
documentation stayed the single source of truth, dead code, and one unified
forbidden-pattern engine that replaced per-ruleset duplicates once the ruleset
count made duplication a maintenance problem.

---

## Principal-Agent Framing for AI Work

Economics has a well-developed theory of what happens when you delegate work to
an agent who has different information and different incentives than the principal.
The standard controls are: **monitoring**, **output verification**, and
**incentive alignment**.

Applied to AI-assisted development:

- **Monitoring** → the hook system observes every file the agent edits in real
  time; out-of-scope writes trigger an alert
- **Output verification** → the quality gates and
  [[projects/agent-warden|agent-warden]] check agent output against real evidence
  before it is trusted
- **Incentive alignment** → scoped subagent prompts constrain what each agent is
  *allowed* to optimize for; a reviewer agent is explicitly told it cannot write
  code

This isn't a coincidence of vocabulary. Principal-agent theory is exactly the
right frame for AI oversight: the problems are structurally identical, and so are
the solutions.

---

## Verifying the Agents: agent-warden

The verification layer grew into its own project. **agent-warden** checks what a
coding agent *claims* ("tests pass", "file created") against observable evidence,
using two tiers of self-hosted models — and measures its own recall instead of
assuming it (78 % for the LLM critic vs. 33 % for a regex baseline). It started as
a VS Code extension and was re-scoped into an editor-independent daemon.

→ [[projects/agent-warden|Read the agent-warden writeup]]. The system also has a
web console for operating it: [[projects/agent-cockpit|agent-cockpit]].

---

## Level-3 Autonomy

Most AI-assisted development setups are reactive: the developer prompts, the
agent responds. This system operates *proactively* — agents initiate work on a
schedule, coordinate through a shared message bus, and keep per-agent state
across sessions.

The foundation was built in four phases, each recorded as an Accepted ADR:

1. **Autonomous triggers** — scheduled jobs without a human prompt, deliberately
   moved from a cloud scheduler to the home server's crontab once an always-on
   machine made the cloud dependency unnecessary.
2. **Agent-to-agent message bus** — a flat directory of append-only JSONL
   channels; the first live flow was CI monitoring → CI diagnosis with no human
   in the middle.
3. **Per-agent persistent state** — each autonomous agent owns a standing
   objective, a last-run record, and bounded memory for recurring patterns.
4. **Push-router and spawn protocol** — a deterministic router (no LLM needed for
   routing) dispatches consumers and can spawn agents on demand.

Since then, the scheduled loops grew from 9 to **31** and the bus from 9 to
**23 channels**. A single registry file is now the source of truth for both
router dispatch and cadence; the crontab is *generated* from it, and the
generator refuses to apply a change that silently adds or drops a loop.

---

## From Issue to Pull Request, Autonomously

The biggest step since the first version: the system no longer only *detects*
problems — it implements tracker issues end to end.

```
issue → implement (spec/plan/code/gates) → pull request → automated review → bounded fix → human merge
```

- **Implementation** reuses the existing pipeline, so autonomous work passes the
  same gates as supervised work. Starting an irreversible step needs an explicit
  one-shot confirmation marker.
- **Review and fix loops** post findings and a review status automatically; a
  fixer applies bounded corrections (capped rounds, escalates when it stops
  making progress).
- **Dedicated identities.** Agent-authored writes carry a bot account, not mine.
  When the same bot was both author and reviewer of a pull request, two
  independent guards silently declined every review. The fix was a *second*
  identity for the reviewer — separation of duties, not a bypass.
- **Credentials are checked for capability, not just identity.** A scheduled check
  proves each bot credential can actually perform its job. An agent whose
  credential fails halts with a diagnosis. It never switches to a more
  privileged credential.
- **Floors that a config typo can't remove.** For irreversible actions, the
  confirmation requirement is the union of per-channel policy data and a
  hard-coded structural check. A missing flag in the registry cannot silently
  disable it.
- **Scheduled jobs run pinned code.** Scheduled jobs execute a separate pinned
  checkout, never whatever branch happens to be checked out in the working
  copy.

### Shadow before you arm it

Merging is the one step still reserved for a human. An autonomous merge decision
exists, but **only in shadow mode**: it records what it *would* have merged and is
measured against what was actually merged. It gets merge authority only once the
measurements justify it. The design is recorded as a proposed ADR.

### Honest status

Two correctness bugs in the live review path are open and documented. In one, a
review is recorded as posted while the comment never lands. In the other, a label
update silently does nothing. The second was traced into the Forgejo API
definition: the edit endpoint's request structure has no labels field, confirmed
against a known upstream issue. The first guess, "a permissions problem", was
wrong. The backlog of the system itself is currently being triaged for which
items are safe to hand to the same autonomous chain.

---

## Engineering Decisions Worth Noting

**Why hook-based gates instead of agent-run gates?**  
Agents can be talked out of gates. A shell hook cannot be. The deterministic path
is the unconditional path.

**Why scoped agents instead of one general agent?**  
A general agent accumulates context that biases its decisions. A scoped agent
starts cold with exactly the context it needs. Scoping is also the mechanism that
prevents an agent from doing work outside its stated responsibility — the software
engineering equivalent of least privilege.

**Why ADRs for a personal project?**  
Because the cost of "why did I do this?" six months later is higher than the cost
of writing three paragraphs now. ADRs are not process ceremony — they are
compressed context that survives the next conversation.

**Why policy-as-code rulesets over inline instructions?**  
Inline prompt instructions are loaded unconditionally and consume context window
on every turn. YAML rulesets are injected by a pre-edit hook only when the edited
file matches the ruleset's glob. A React ruleset costs zero tokens on a Python
file.

**Why shadow mode before autonomy?**  
An automation with real consequences should earn its authority with data. Running
the decision silently next to the human decision costs almost nothing and turns
"I think it's safe" into a measurement.

---

## What This Demonstrates

For a recruiter or engineering lead reading this:

1. **I don't just use AI — I have a principled framework for working with it.**
   Spec-driven workflow, scoped agents, deterministic gates, and a formal
   principal-agent model are the difference between "I use Claude" and "I
   engineered the system around Claude."

2. **Quality discipline is structural, not motivational.** The gates run
   whether I'm tired, distracted, or pressured by a deadline. I built the
   system precisely so that quality doesn't depend on my willpower in any given
   moment.

3. **I think in systems.** See a repeating problem, derive the principle behind
   it, build the mechanism that eliminates it. This isn't a project about AI — it
   is a project about making quality structural instead of accidental.

4. **I automate carefully.** Separate identities, confirmation floors, and shadow
   measurement before granting authority. Autonomy is added step by step, and
   each step has to prove itself.

5. **Self-reflection over the sunk-cost trap.** The Claude setup is where I
   invest flow-state hours. Other projects (the PWA) I flagged honestly as
   over-engineered. The difference is whether the complexity *served the goal* —
   economic thinking applied to my own work.

---

*Built 2025–present. Python (orchestrator, gates, scheduled loops), shell (hooks),
TypeScript ([[projects/agent-warden|agent-warden]],
[[projects/agent-cockpit|agent-cockpit]]). Self-hosted on a Debian home server
via Tailscale, with a private Forgejo instance for code, CI and the issue
tracker. Not open-source — private configuration, memory, and credentials are
part of the repo. Inventory figures last verified against the live system
2026-09-15.*
