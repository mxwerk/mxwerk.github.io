---
title: Path containment
description: One function resolves a path through every symlink and refuses it unless the result lies inside a given root, and every route that takes a path from a caller goes through it.
draft: false
cites:
  - path: backend/src/files/safe-path.ts
    lines: 1-69
  - path: backend/src/dispatch/dispatch.ts
    lines: 21-29, 446-452, 539-551
  - path: backend/src/api/server.ts
    lines: 102-106, 272-310, 323-340
  - path: backend/test/safe-path.spec.ts
    lines: 27-108
verified_at: 75e94b4
---

# Path containment

> **TL;DR** — The cockpit starts processes in directories and serves file contents, and in
> both cases the path comes from a request. `resolveWithinRoot` turns such a path into its
> real location, following every symlink on the way, and answers one of three things: the
> real path, "missing", or "refused". Containment is checked before existence, so a path
> outside the root is refused whether or not it exists. [[wiki/agent-cockpit/index|↑ Wiki]]

## What it is

A module of under 70 lines with one exported function and no dependency beyond the standard
library. It makes read-only filesystem calls. Dispatch uses it for the directory an agent
is started in; the file viewer uses it for what it reads.

## How it works

A relative candidate is resolved against the root, never against the directory the
process happens to run in. The candidate is then resolved to its real path, which follows
a symlink in any segment, not only the last one. A file that sits behind a symlinked
directory pointing out of the root therefore shows its true location and is refused.

If the path does not exist, the function walks up to the deepest ancestor that does and
resolves that. Containment can then still be judged, and a non-existent path that would
lie outside is `refused`, not `missing`. The difference matters to a caller: "missing"
confirms that the location would have been allowed.

The comparison is on path boundaries. A sibling directory whose name merely starts with
the root's name is outside.

Only "does not exist" is treated as missing. Permission errors and symlink loops are
thrown, because they are failures and not answers.

Dispatch calls the function before it reserves or spawns anything
([[wiki/agent-cockpit/components/dispatch]]). Resume calls it again on the stored directory, because a
directory can be moved or re-pointed between a launch and its resume
([[wiki/agent-cockpit/decisions/reboot-reconciliation]]). The file-read and directory-listing routes call it too, and catalog reads are
additionally limited to the named catalog directories.

## What it costs / limits

- **Check, then use.** The function returns a path that was inside the root when it was
  resolved. A symlink changed between that moment and the spawn or the read is not
  detected. Nothing in the repository closes or discusses that window.
- **A dangling symlink inside the root reads as missing.** The function cannot tell it
  from an absent file; the code documents this and a test pins it.
- **The root must exist.** It is resolved first, and a missing root throws.

What the tests show: ten cases, among them the parent-directory escape, a symlink as the
last segment, a symlink in the middle, a non-existent escape, the look-alike sibling
directory, and a root that is itself a symlink.

## Later changes

None.
