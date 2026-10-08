---
title: A source that is down is shown as down
description: The readers keep a source that is unreachable apart from one that is up with nothing to report, and the bus reader also marks one that is stale.
draft: false
cites:
  - path: backend/src/substrate/busReader.ts
    lines: 19-25, 66-70, 112-118, 165-176
  - path: backend/src/substrate/wardenReader.ts
    lines: 1-6, 19-21, 45-49, 75-81
  - path: backend/src/substrate/wardenHistory.ts
    lines: 6-10, 106-111
  - path: backend/src/config/env.ts
    lines: 49-53, 68-79
  - path: backend/src/ingest/poller.ts
    lines: 132-147
verified_at: 75e94b4
---

# A source that is down is shown as down

> **TL;DR** — A monitoring surface that shows an empty list when its source is unreachable
> tells the operator that all is well exactly when it knows least. The cockpit's readers
> therefore keep "cannot be reached" apart from "reachable with nothing to report", and the
> bus reader adds "reachable but old". Which form "unreachable" takes depends on whether an
> outage is expected. The rule is applied unevenly; the limits are listed below. [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

Each panel reads something the cockpit does not own: files of another repository, a
daemon that is not always running, a metrics store. "No verdicts" and "could not ask" look
identical in a list unless the reader carries the difference through.

## How it works

**An outage that should not happen is an error.** The bus directory must exist. If it
cannot be read, `readBusSummary` throws, and the request fails instead of returning an
empty summary that would read as an idle system.

**An outage that is expected is data.** The judge's daemon is often not running. Its
reader never throws: unreachable, a non-2xx answer and a body that is not a JSON
object each become a feed with `source_up: false` and the reason as text. The
trend reader does the same, and additionally treats a query error that the metrics store
reports with HTTP 200 as down.

**Up with nothing is its own state.** A daemon that answers but has no snapshot yet is
`source_up: true` with a null timestamp.

**Unknown age counts as stale.** A channel is stale when its file is older than 24 hours,
and also when no modification time can be read at all. A bus line that cannot be parsed is
counted as pending.

**A session without a transcript is still listed.** An agent that is running but for which
no transcript file is found is recorded as `untracked` ([[wiki/agent-cockpit/components/discovery-poller]]).

The same rule is applied to configuration: a missing bind address or an invalid source URL
stops the backend at startup with a message.

## What it costs

- **Staleness exists for the bus only.** The verdict readers pass the snapshot's timestamp
  through without judging it, so a snapshot from a watcher that stopped hours ago is served
  like a fresh one. The ADR asked for a stale state there as well.
- **Any JSON object counts as an answer.** A reply from the judge's daemon that is an
  object without a verdict list is served as up with zero verdicts, which is the outcome
  the rule is meant to exclude.
- **The bus summary has no panel.** The route exists; nothing in the frontend fetches it,
  so its stale flag reaches no screen yet.
- **A transcript that exists but yields no lines is not flagged.** It produces no
  `untracked` row, and an existing row is set to interrupted.
- **Tolerant parsing hides single losses.** A malformed verdict is dropped and nothing
  counts it. The rule holds for whole sources, not for single entries.
- **One threshold for all channels.** A channel that is legitimately quiet for a day is
  marked stale.
- **Two conventions to remember:** throw for the bus, a flag for the judge. Which one a
  new reader should follow is a judgement about whether its outage is normal.

## Later changes

None. See [[wiki/agent-cockpit/decisions/substrate-read-only]] and
[[wiki/agent-cockpit/decisions/warden-verdicts-two-sources]] for the two decisions this rule comes from.
