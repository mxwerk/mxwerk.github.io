---
title: A repeated dispatch returns the first result
description: A caller may attach a key to a dispatch, and a repeat with the same key returns the first call's session instead of starting a second agent.
draft: false
cites:
  - path: backend/src/db/index.ts
    lines: 58-71, 126-156
  - path: backend/src/db/schema.sql
    lines: 19-25
  - path: backend/src/dispatch/dispatch.ts
    lines: 40-49, 459-476
  - path: backend/src/api/server.ts
    lines: 120-176, 191-198
  - path: backend/test/db.spec.ts
    lines: 259-318
  - path: backend/test/dispatch.spec.ts
    lines: 330-398
  - path: docs/branches/feat/57-idempotency-key-on-dispatch/context.md
verified_at: 75e94b4
---

# A repeated dispatch returns the first result

> **TL;DR** — Another service, agent-workorders, hands work to the cockpit, and a sender
> that retries after a lost answer would start a second agent on the same task. So
> a dispatch may carry an idempotency key: the first call stores it on its row, a repeat
> gets the first call's session id back, and a repeat that arrives while the first is still
> starting is refused. Unknown fields in the request are rejected, not ignored.
> [[wiki/agent-cockpit/index|↑ Wiki]]

## The problem

The sending side was about to gain a retry, which makes its delivery at-least-once: a
dispatch that succeeded but whose answer was lost is sent again. The key was built first,
as the precondition for that retry. Starting an agent is not an action that can be
repeated harmlessly: it costs tokens and may edit the same files twice.

## The decision

The key is stored on the reservation itself. The lookup and the reservation share one
transaction, because checking first and reserving afterwards would let two concurrent
calls with the same key both see "unknown" and both start. A partial unique index on the
key column is the backstop behind that transaction; it is partial so that any number of
dispatches without a key can coexist, which is what the UI sends.

## How it works

`reserveSlotForKey` returns one of four outcomes. `reserved` proceeds to the launch.
`duplicate` returns the stored session id and starts nothing. `in-flight` means the first
call has a reservation but no session id yet, and the route answers 409. `slot-full` is
the ordinary cap refusal ([[wiki/agent-cockpit/decisions/over-cap-reject]]).

Two rules at the HTTP boundary keep the contract honest. An empty key is rejected instead
of being treated as absent. A request with a field the route does not know gets a 400.
Both exist because a caller that believes it sent a key and silently did not is
unprotected without knowing it.

A first attempt that fails before its first event deletes its reservation and so frees the
key for a real retry. The startup sweep does the same for a key whose dispatch died with
the backend.

## What it costs

- **Keys are never expired.** A key stays on its session row for as long as the row
  exists, so a reused key returns an old session indefinitely. That includes a run that
  failed after its first event: the repeat gets the id of the interrupted session back.
- **A full cap wins over a new key.** The cap is checked only after the key is found to be
  unknown, so a first attempt can still be refused for lack of a slot.
- **Resume takes no key.** Only the launch route is protected.
- **No ADR.** The decision is written down in the branch report of the change and in code
  comments, not under `docs/adr/`.

## Later changes

The column was added by a migration step in `openDb`, because a database file created
before the change has no such column.
