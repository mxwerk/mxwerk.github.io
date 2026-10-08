---
title: Verdict telemetry
description: The watcher can push every verdict as OTLP metrics and logs to an existing collector, which gives a trend history that a sibling project reads, at the cost of a stack the warden does not ship.
draft: false
cites:
  - path: src/core/services/verdictTelemetry.ts
    lines: 30-41, 84-95, 113-123, 135-156, 165-171, 193-221, 233-268
  - path: src/core/daemon/server.ts
    lines: 258-269, 297-306
  - path: src/core/config/env.ts
    lines: 160-161
  - path: docs/adr/0013-verdict-telemetry-and-grafana-surface.md
    lines: 20-25, 36-41, 43-46, 51-61, 75-77
  - path: docs/adr/0014-persistent-telemetry-daemon-and-cockpit-consumer.md
    lines: 38-42, 66-70
  - path: docs/reference/observability-queries.md
    lines: 7-13, 15-21
  - path: tests/dashboardStructure.spec.ts
    lines: 7-10
  - path: README.md
    lines: 74-76
verified_at: ae9e10a
---

# Verdict telemetry

> **TL;DR** — `GET /verdicts` holds only the latest watch cycle, so history
> would otherwise be lost. With `WARDEN_TELEMETRY=1` the watcher emits each
> snapshot as OTLP metrics (for Prometheus) and logs (for Loki), and a
> sibling project, agent-cockpit, reads them. It is opt-in, write-only and
> best-effort. [[wiki/agent-warden/index|↑ Wiki]]

## What it is for

Without persistence a trend view is impossible (ADR 0013). Emitting to an
already running collector avoids a second pipeline; the daemon dials out, so
no container has to reach the host. See [[wiki/agent-warden/components/daemon]].

## How it is built

- **Two signal paths.** Metrics are bounded and aggregate:
  `warden_verdict_total` (labels `pathology`, `kind`, `tier`, `repo`),
  `warden_verdict_confidence` (a histogram in ten 0.1-wide buckets), and
  `warden_escalation_disagreement_total`. Logs carry the detail: one record per
  verdict, with `reason` as the body and, for collisions, the file and session
  list as attributes.
- **Bounded labels only.** Free text never becomes a metric label, which
  would explode cardinality and leak paths or prompt fragments. The pure
  mapping functions are the enforcement point and have unit tests.
- **Wiring.** The watcher's snapshot handler calls `recordSnapshot`; the
  exporter pushes every 15 seconds by default to `http://127.0.0.1:4318`
  unless `WARDEN_OTLP_ENDPOINT` is set.
- **Failure is silent to the loop.** `recordSnapshot` catches errors and warns
  once; a telemetry fault cannot stop the watch loop.

## Who consumes it

A Grafana dashboard, `warden-verdicts`, was built over these signals; its
canonical copy is provisioned from the sibling stack, and the repo keeps a
fixture for a structural test. ADR 0014 then makes agent-cockpit the
consuming surface: a live list from `/verdicts` and a trend from the
Prometheus metrics. It retires the dashboard after parity but keeps the
emission.

## What it does not do

It is write-only: nothing acts on or routes an agent. `recordSnapshot` has one caller, the watcher's snapshot handler, so on-demand
`/verdict/*` calls are not emitted.

## Limits

- The dashboard is not self-contained: it needs the collector, Prometheus and
  Loki running.
- The repo's query reference covers the agent's own telemetry, not these
  verdict metrics; there is no written query set for them here.
- The repo does not record whether the Grafana dashboard was retired; the
  decision only plans it.
