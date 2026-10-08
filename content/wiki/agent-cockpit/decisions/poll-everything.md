---
title: Poll everything
description: The browser fetches every live panel on a timer at one of two intervals, and the log tail is a cursor read against the event table the store keeps anyway.
draft: false
cites:
  - path: docs/adr/001-live-view-transport-poll-everything.md
    lines: 12-33
  - path: frontend/src/hooks/queries.ts
    lines: 27-32, 251-252
  - path: backend/src/api/server.ts
    lines: 370-382
  - path: backend/src/db/index.ts
    lines: 86
  - path: backend/src/index.ts
    lines: 168-180, 226
verified_at: 75e94b4
---

# Poll everything

> **TL;DR** — There is no socket and no event stream between the cockpit's backend and its
> browser. Every live panel is a `fetch` on a timer: 1.5 seconds for what the operator is
> looking at, 20 seconds for the background catalog. A log tail asks for events with an id
> above the last one it saw. WebSocket and server-sent events were both considered and set
> aside. [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

The cockpit shows the status, usage and log tail of a handful of running agents to one
operator, who may have a laptop and a phone open at once. The charter asks for at most
2 seconds of staleness on the active pane and 30 on the catalog. The log source is already
a stream, which makes a push transport the obvious choice.

## The decision

ADR 001 chose polling at two intervals instead. The argument rests on one fact: every
stream event has to be written to a table anyway, because recovery after a reboot needs it
([[wiki/agent-cockpit/decisions/reboot-reconciliation]]). Once that table exists, a log tail is a cursor query
against it and costs no new mechanism. A push channel would add a second mechanism, with
reconnect handling and a proxy that must not buffer, to beat a freshness target that
polling already meets.

## How it works

The two intervals are named constants in the frontend's query hooks, not literals at the
call sites. File contents and directory listings are the exception: they are fetched once
when opened. The backend has its own third timer: it re-reads the terminal multiplexer and
the transcripts every 5 seconds ([[wiki/agent-cockpit/components/discovery-poller]]). A failed tick is logged
and the next one retries, so a database fault during a poll cannot take the HTTP server
down with it.

The log route takes a `since` cursor and refuses anything that is not a non-negative
integer.

## What it costs

- **Requests while nothing changes.** Each device polls on its own whether or not the
  server has anything new.
- **Freshness is bounded by the interval,** not by when an event arrives.
- **The log tail reads more than it returns.** The prepared statement selects every event
  above the cursor for all sessions, and the route then filters to the requested session
  in memory, so the read grows with the activity of every session, not of the one shown.
- **The intervals were never confirmed by measurement.** The ADR left that as a follow-up,
  together with the number that would justify switching to push. Neither is recorded.

## Later changes

None. Server-sent events remain the named upgrade path and are not built.
