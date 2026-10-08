---
title: Verdicts come from two sources
description: The live verdict list is fetched from the judge's own HTTP endpoint and the trend from Prometheus, because neither source carries both the reason text and the history.
draft: false
cites:
  - path: docs/adr/005-warden-verdict-surface-consolidation.md
    lines: 41-104
  - path: backend/src/substrate/wardenReader.ts
    lines: 1-25, 45-82
  - path: backend/src/substrate/wardenHistory.ts
    lines: 1-28, 63-119
  - path: backend/src/config/env.ts
    lines: 10-17, 46-47, 68-79
  - path: backend/src/api/server.ts
    lines: 258-270
verified_at: 75e94b4
---

# Verdicts come from two sources

> **TL;DR** — agent-warden judges what coding agents claim. Its daemon serves only the
> latest snapshot, with the full reason for each verdict and no history. Its metrics export
> has the history as counters and drops the reason. The cockpit therefore shows two panels,
> each fed by the source that carries its data, and reports a source that is down as down.
> [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

The operator wanted one place to look at verdicts instead of a separate dashboard. A live
verdict without its reason is of little use, and a trend needs history that the daemon
does not keep.

## The decision

ADR 005 uses both sources. Reading everything from the metrics store would lose the
reason and delay the live view. Reading only the daemon would leave the old dashboard in
place for history. Adding storage to the judge so that the cockpit could read it was
rejected as a large change to the observed system for the observer's benefit.

## How it works

`fetchVerdicts` calls the daemon with a 2-second limit and validates each verdict field by
field; a malformed verdict is dropped, the rest are kept. `fetchVerdictHistory` asks
Prometheus for the increase of the verdict counter per hour over the last 24 hours, summed
by pathology and kind, with a 3-second limit. `increase` is used so that a counter reset
after a daemon restart does not show up as a drop.

Unreachable, a non-2xx answer and a body that is not a JSON object each become a feed
with `source_up: false` and the reason as text, instead of an exception. A daemon that is up but has produced no snapshot yet is a different state
and is reported as up with nothing ([[wiki/agent-cockpit/concepts/surface-never-silent]]). Both addresses
come from configuration and are checked to be valid URLs at startup.

## What it costs

- **Two couplings:** the daemon's JSON shape and the metric's name and labels. The verdict
  type is mirrored by hand; no type crosses the repository boundary.
- **The trend needs the judge's telemetry export switched on.** Without it the panel is
  empty, correctly, and looks the same as a judge that has nothing to report.
- **A dropped verdict is invisible.** Tolerating a malformed entry means nobody is told
  that one was discarded.
- **Whether the old dashboard was retired is not visible here.** The ADR orders that step
  after both panels are verified; it happens outside this repository.

## Later changes

None.
