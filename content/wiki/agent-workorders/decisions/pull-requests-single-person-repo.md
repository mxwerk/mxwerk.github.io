---
title: Pull requests in a single-person repository
description: Every change reaches the main branch through a pull request with zero required approvals, so the CI checks stand in for the reviewer that does not exist.
draft: false
cites:
  - path: docs/adr/005-pull-requests-in-a-single-person-repository.md
    lines: 11-21, 25-37, 41-55
  - path: .claude/project-config.yml
    lines: 1-9, 22-36, 42-56, 68-80
  - path: .forgejo/pull_request_template.md
    lines: 1-25
  - path: .forgejo/workflows/ci.yml
    lines: 18-21, 34-37, 85-92, 100-110, 120-129, 193-201, 275-276
verified_at: 262e98e
---

# Pull requests in a single-person repository

> **TL;DR** — The repository has one author and still routes every change
> through a pull request from an issue-named branch. The reason is not review:
> an agent that proposes changes needs somewhere for a change to sit between
> "done" and "accepted". Required approvals are zero, because the forge does
> not let an author approve their own pull request. The CI status checks are
> the gate, which is why the pipeline runs the full `check` task with nothing
> carved out for speed. [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

ADR 005 records that the project charter put the repository in trunk mode:
commit to `main`, Conventional Commits, no merge-request ceremony. That fitted
a repository with one author, no tracker and no gate.

It stopped fitting for one specific reason. The plan is for an agent to
propose changes for inspection and to turn CI failures into tracked work.
Milestones, issues and a proposed-but-not-yet-accepted change all need
something to attach to, and a direct push to `main` offers nothing. The ADR
frames the question narrowly: where does a change live between "done" and
"accepted" when nobody is watching a terminal?

## The decision

- **Every change goes through a pull request** from a branch named after an
  issue. The project configuration declares `workflow: mr-based`, and its
  opening comment repeats the reason: not because the repository has
  reviewers, but because issues, milestones and agent-opened changes need a
  place to attach.
- **`main` refuses direct pushes.** This is a setting on the forge, not a file
  in the repository; the ADR records it as decided and as observed (see
  below).
- **Required approvals are zero.** The required status checks are the gate.
  The ADR calls this the part most easily misread as laziness: with no second
  person, a positive number is not stricter, it blocks every merge.
- **Issue first, branch second.** The configuration fixes the branch shape as
  `<type>/<id>-<slug>` with a real issue id, and lists seven allowed type
  prefixes: `feat`, `fix`, `chore`, `docs`, `ci`, `refactor`, `test`. It also
  sets `milestone_required: true`.
- **A ready label marks the handover.** `status::ready` is described in the
  configuration as the point where an issue's acceptance conditions are
  concrete enough to check without asking anyone.
- **The pull request template asks for reasons.** It opens with `Closes #` and
  has three sections: what changed and why, how it was verified, and what was
  deliberately left out. The verification section says "tests pass" is not an
  answer, and asks how a newly added gate was watched failing.
- **CI runs on every pull request** and on pushes to `main`. The `build` job
  runs `./gradlew --no-daemon check`; its comment lists compile, Checkstyle,
  PMD, SpotBugs, the whole test suite including the Testcontainers tier, and
  the JaCoCo thresholds, and states that nothing is split into a fast subset.

| Option | Why not |
| --- | --- |
| Stay on trunk | Least friction and what the charter said, but a proposed change has no artefact: an agent either commits to `main` or does nothing. |
| Pull requests with one required approval | The forge refuses self-approval, so in a one-person repository every merge would deadlock. |

## What it costs

- **Ceremony for small fixes.** A one-line human fix takes a branch and a pull
  request; the ADR counts two round trips where trunk needed one.
- **The gate carries the reviewer's whole weight.** The substitution holds
  only while the gate covers the change. A faster subset would, in the ADR's
  words, turn "reviewed" into "compiled". This is the reason the pipeline is
  not optimised for speed.
- **A check that did not run can look like a pass.** The workflow's own
  comments note that a skipped job reports success to the commit status. With
  no human reading the diff, that failure mode matters more here than it would
  with a reviewer; one job is written without `if:` or `needs:` for that
  reason.
- **Bootstrap broke its own rule.** The first commits landed directly on
  `main`, because branch protection cannot precede a gate that a pull request
  could pass. The ADR states this instead of leaving it to be discovered.
- **Merging stays a human act.** An agent can open a change without landing
  it. The ADR lists this as the benefit; it is also a standing manual step.

What was observed, according to the ADR: a direct push to `main` was refused
by the forge's pre-receive hook, and a pull request with a red pipeline was
refused at merge with the message "Not all required status checks
successful". Both refusals are recorded as having been watched. Neither can be
re-checked from the repository's files, since branch protection lives on the
forge.

## Later changes

- **The pipeline has grown beyond the `check` task the ADR names.** The
  workflow now defines four jobs: `runner-plumbing`, `branch-report`,
  `ruleset-gate` and `build`. The ADR mentions only the last one's command.
  `build` declares `needs: runner-plumbing`, so a daemon that cannot be
  reached fails early with a plain message.
- **A branch that changes product code owes a written report.** The
  `branch-report` job runs on pull requests only and reads what counts as
  product code from the project configuration. Its comment explains why it is
  a CI job and not a pre-push hook: a hook whose runner is absent reports
  green without having run.
- **The ruleset gate reads rules committed with the change**; see
  [[wiki/agent-workorders/decisions/ci-judges-committed-artifact]]. The full set of checks is laid
  out in [[wiki/agent-workorders/components/quality-gate]].
- **One configuration value has drifted.** The project configuration names the
  runner label `jdk25`, while each of the four jobs in the workflow declares
  `runs-on: jdk25-rootless`.
- **Which checks the forge requires is not recorded in the repository.** The
  ADR says "the required status checks are the gate" without listing them, and
  the workflow file cannot say which of its jobs branch protection waits for.
