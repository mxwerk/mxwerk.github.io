---
title: agent-cockpit wiki
kind: index
---

# agent-cockpit wiki

Distilled, cross-linked knowledge about this project. Every page cites the
files it describes and the commit it was checked against (`cites:` /
`verified_at:`); the portfolio's `check_wiki.py --project --repo .` reports a page
STALE once a cited file changes. Pages start as `draft: true`; the operator approves a page
by setting `draft: false`.

## Concepts

- [[wiki/agent-cockpit/concepts/reservation-row|The reservation row]] — A slot is held by a provisional row in the sessions table, which is later renamed to the real session, deleted, or swept at startup.
- [[wiki/agent-cockpit/concepts/surface-never-silent|A source that is down is shown as down]] — The readers keep a source that is unreachable apart from one that is up with nothing to report, and the bus reader also marks one that is stale.

## Decisions

- [[wiki/agent-cockpit/decisions/poll-everything|Poll everything]] — The browser fetches every live panel on a timer at one of two intervals, and the log tail is a cursor read against the event table the store keeps anyway.
- [[wiki/agent-cockpit/decisions/over-cap-reject|A launch over the cap is refused]] — A launch that would exceed the concurrency cap is refused with a conflict status instead of queued, and the count and the reservation happen in one transaction.
- [[wiki/agent-cockpit/decisions/reboot-reconciliation|The database is the record, the process is only probed]] — Every stream event is written in its own transaction, and at startup every session still marked running is set to interrupted unless a probe confirms it alive.
- [[wiki/agent-cockpit/decisions/substrate-read-only|The harness is read from disk, never written]] — The cockpit reads the agent harness's message bus straight from the filesystem under a configured root, through one module that imports no write call.
- [[wiki/agent-cockpit/decisions/warden-verdicts-two-sources|Verdicts come from two sources]] — The live verdict list is fetched from the judge's own HTTP endpoint and the trend from Prometheus, because neither source carries both the reason text and the history.
- [[wiki/agent-cockpit/decisions/idempotent-dispatch|A repeated dispatch returns the first result]] — A caller may attach a key to a dispatch, and a repeat with the same key returns the first call's session instead of starting a second agent.

## Components

- [[wiki/agent-cockpit/components/dispatch|Dispatch]] — Dispatch starts a headless agent process in a checked directory, waits a bounded time for its first event, and then writes every event until the process ends or is killed.
- [[wiki/agent-cockpit/components/discovery-poller|The discovery poller]] — Every five seconds the backend lists terminal-multiplexer sessions that run an agent, finds each one's transcript, and stores lines it has not seen.
- [[wiki/agent-cockpit/components/path-containment|Path containment]] — One function resolves a path through every symlink and refuses it unless the result lies inside a given root, and every route that takes a path from a caller goes through it.
- [[wiki/agent-cockpit/components/quality-gate|The quality gate]] — One CI job runs lint, type check, the committed ruleset gate, the unit suites and a screenshot comparison in a pinned browser image on every pull request, with no path filter.
