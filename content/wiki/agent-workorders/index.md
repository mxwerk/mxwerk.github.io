---
title: agent-workorders wiki
kind: index
---

# agent-workorders wiki

Distilled, cross-linked knowledge about this project. Every page cites the
files it describes and the commit it was checked against (`cites:` /
`verified_at:`); `check_wiki.py --project --repo .` reports a page STALE once a
cited file changes. Pages start as `draft: true`; the operator approves a page
by setting `draft: false`.

## Concepts

- [[wiki/agent-workorders/concepts/modules-by-id|Modules by id]] — An aggregate names a neighbouring module only by its id type, and any dependency beyond that must travel along an edge declared in an allowlist that ArchUnit checks.
- [[wiki/agent-workorders/concepts/work-order-lifecycle|Work-order lifecycle]] — A work order moves through six states, and every transition is a method on the aggregate that refuses to run from the wrong state.

## Decisions

- [[wiki/agent-workorders/decisions/ci-judges-committed-artifact|CI judges from a committed artifact]] — The ruleset gate in CI reads its rules and its own code from a directory committed in the repository, checked against a hand-maintained digest per ruleset, so the rules in force are the ones in the commit being judged.
- [[wiki/agent-workorders/decisions/consent-is-a-timestamp|Consent is a timestamp]] — Consent is three nullable timestamps on the user row, and withdrawing data-processing consent erases the stored address in the same operation.
- [[wiki/agent-workorders/decisions/cross-aggregate-invariants|Cross-aggregate invariants]] — The per-agent WIP limit is decided by the work-order aggregate from two numbers that the assignment use case reads while holding a row lock on the agent.
- [[wiki/agent-workorders/decisions/dispatch-gives-up|A dispatch that cannot succeed gives up]] — A dispatch obligation ends either on a refusal the adapter calls permanent or once it is older than a configured age, and ending it fails the work order.
- [[wiki/agent-workorders/decisions/dispatch-outbox|The dispatch outbox]] — An assignment records a dispatch obligation in its own transaction, and that row's id is the idempotency key every retry presents.
- [[wiki/agent-workorders/decisions/pull-requests-single-person-repo|Pull requests in a single-person repository]] — Every change reaches the main branch through a pull request with zero required approvals, so the CI checks stand in for the reviewer that does not exist.
- [[wiki/agent-workorders/decisions/work-order-names-project|Work order names a project]] — A work order stores the id of a project, and the project row is the single place that holds the directory an agent is told to work in.

## Components

- [[wiki/agent-workorders/components/dispatch-seam|The dispatch seam]] — Handing a work order to whatever runs agents goes through one port with two adapters, and a single configuration property decides which adapter answers it.
- [[wiki/agent-workorders/components/quality-gate|The quality gate]] — One Gradle command, check, fails the build on a static-analysis finding, a coverage shortfall, a broken architecture rule or a failing integration test against a real PostgreSQL, and CI runs that same command.
- [[wiki/agent-workorders/components/user-module|The user module]] — A user is the identity provider's subject claim plus a profile and an optional address that this application owns, created the first time a token for that subject arrives.
