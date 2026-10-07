---
title: Draft first, plans append-only
description: Generated documentation lands hidden and reaches readers only through an operator-approved promotion, and plans can be corrected but never deleted.
draft: false
cites:
  - path: skills/stack-agnostic/maintain-docs/SKILL.md
    lines: 21-25, 80-90, 133-148, 164-165, 200-209
  - path: hooks/protect-plans.sh
    lines: 1-20, 29-44
  - path: orchestrator/tests/test_protect_plans_hook.py
    lines: 1-11
  - path: docs/adr/015-wiki-capability-extends-maintain-docs.md
    lines: 78-81
verified_at: 82cca7c
---

# Draft first, plans append-only

> **TL;DR** — Anything the documentation skill writes by itself carries a draft
> flag and stays invisible until the operator approves it. Plans work the other
> way round: they are visible and may be edited, but a hook blocks deleting or
> moving them.
> [[wiki/harness/index|↑ Wiki]]

## The idea

Automatic writing and publishing are separated by an approval step. A wrong
generated page costs a rejected draft instead of a published error. For plans the
risk is the reverse: the harm is losing the record of what was intended, so the
control protects existence, not content.

## Where it is enforced

- **Draft flag.** The skill's core invariant: every merge or ingest gets a
  page, but auto-written content has `draft: true`, which the site renderer
  strips. Drafts are created without approval because they are invisible; the
  skill is told never to auto-fill their prose.
- **Promotion.** Each draft gets proposed content, one approval per page.
  Approval writes the content and removes the flag; rejection leaves the draft.
  Nothing is published without that step.
- **Fail-closed flag name.** Invisibility comes from the key the renderer
  strips, not from what the skill writes. If the configured key is not one the
  renderer recognises, the skill halts instead of falling back, because
  otherwise pages would publish with no error anywhere.
- **Plans.** `protect-plans.sh` is a pre-tool hook on shell commands. It blocks
  `rm`, `git rm`, `mv`, `shred`, `truncate` and `unlink` aimed at a plans
  directory (exit 2), and points to a new entry as the correction.
  Its test asserts the block, because a regression to a silent allow would
  report nothing.

## What it costs / where it does not reach

The plan hook is deliberately narrow. It watches only shell verbs; edits and
writes to a plan stay allowed so the plan can be maintained, and shell
redirection is excluded as too noisy, so a plan can still be emptied by
overwriting it. A trailing comment overrides it. It is a guard against
accident, not against intent.

Draft-first moves the bottleneck to the operator: unpromoted drafts accumulate,
and the skill logs rejected items only so it does not re-propose them. The
invisibility also rests on the renderer's behaviour, which this repository does
not control. The same reasoning, with a human gate before authority, appears in
[[wiki/harness/concepts/shadow-before-authority|shadow before authority]].
