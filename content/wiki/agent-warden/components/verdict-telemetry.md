---
title: Verdict telemetry
description: The watcher can push every verdict as OTLP metrics and logs to an existing collector, which gives a trend history that a sibling project reads, at the cost of a stack the warden does not ship.
draft: false
cites:
  - path: src/core/services/verdictTelemetry.ts
    lines: 30-41, 80-110, 132-155, 157-188, 197-209, 225-265, 277-316
  - path: src/core/daemon/server.ts
    lines: 278-289, 291-343
  - path: src/core/daemon/watcher.ts
    lines: 65-84
  - path: src/core/harness/escalate.ts
    lines: 57-81, 176-196
  - path: src/core/config/env.ts
    lines: 160-161
  - path: docs/adr/0013-verdict-telemetry-and-grafana-surface.md
    lines: 20-25, 36-41, 43-46, 51-61, 75-77
  - path: docs/adr/0014-persistent-telemetry-daemon-and-cockpit-consumer.md
    lines: 38-42, 66-70
  - path: docs/reference/observability-queries.md
    lines: 7-22, 24-30
  - path: tests/dashboardStructure.spec.ts
    lines: 7-10
  - path: README.md
    lines: 75-77
verified_at: 7c50953
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
  `warden_verdict_confidence` (a histogram in ten 0.1-wide buckets),
  `warden_escalation_disagreement_total`, and — since #119 —
  `warden_escalation_latency_ms`, a histogram of the strong-tier round trip whose
  buckets are the measured figures with an edge at the charter's 40s target.
  Logs carry the detail: one record per verdict, with `reason` as the body and,
  for collisions, the file and session list as attributes.
- **The latency metric closed an open half of the guardrail.** The charter's
  escalation clause has a rate half and a latency half, and until #119 only the
  rate was observable (countable from `tier="escalated"`). The latency had a
  mechanism bounding it (`evidenceBudget.ts`) and no emission, so the clause the
  charter calls binding had been measured exactly once, by hand (ADR-0019
  §Correction). The value is produced in `escalate.ts`, carried on
  `evidence.escalationLatencyMs` the way the disagreement flag already was, and
  turned into an observation here — see ADR-0013 §Amendment.
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
  verdict metrics; there is no written query set for them here. Since #108 that
  reference is also historical: the data layer that ran those queries was
  deleted with the VS Code surface (ADR-0025, superseding ADR-0005), and
  agent-cockpit queries Prometheus with a reader of its own. The queries
  themselves still hold — they were extracted from the dashboard, not from the
  deleted code.
- The repo does not record whether the Grafana dashboard was retired; the
  decision only plans it.
