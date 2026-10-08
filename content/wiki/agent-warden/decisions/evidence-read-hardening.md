---
title: Evidence-read hardening
description: The daemon refuses a malformed evidence selector, refuses a swapped file path, and bounds evidence size, because an agent that controls the request could otherwise make the warden silently judge nothing, or the wrong file.
draft: false
cites:
  - path: docs/adr/0018-daemon-evidence-selector-hardening.md
    lines: 42-61, 69-93, 111-127, 129-134
  - path: docs/adr/0019-evidence-size-budget-for-the-latency-guardrail.md
    lines: 77-94, 190-198, 205-220, 305-319
  - path: docs/adr/0020-mcp-absent-path-refusal-scoped-by-use.md
    lines: 72-92, 94-109
  - path: docs/adr/0021-check-use-check-on-the-opened-evidence-descriptor.md
    lines: 46-57, 61-69, 92-126
  - path: src/core/harness/verifiedRead.ts
    lines: 89-90, 116-130
  - path: src/core/harness/evidenceBudget.ts
    lines: 71-72, 93-122
  - path: src/core/harness/gitEvidence.ts
    lines: 97-108
  - path: src/surfaces/mcp/guards.ts
    lines: 48, 97-168
  - path: src/core/daemon/router.ts
    lines: 101-136
  - path: README.md
    lines: 191-225
verified_at: ae9e10a
---

# Evidence-read hardening

> **TL;DR** — The party being judged supplies the revision and the file paths
> the warden reads as evidence, so each one is a way to make the warden judge
> nothing or the wrong thing. Four small mechanisms close that: reject a bad
> revision, refuse an absent path that will be opened, verify the opened
> descriptor, and cap evidence size. The path check works only on Linux.
> [[wiki/agent-warden/index|↑ Wiki]]

## The threat

The supervised agent owns the worktree and builds the requests, so it can:

- **Pass an existing repo path as the revision.** Git reads it as a pathspec
  and filters the diff to nothing, which the warden reported as a clean abstain.
- **Swap a directory for a symlink** between the surface's boundary check and
  the daemon's read, so an out-of-bounds file is read. It controls the
  filesystem and can retry.

## What was decided

1. **A bad revision is a 400; a real gap still abstains.** The daemon runs
   `git rev-parse --verify` first and throws if the revision is not a commit.
2. **Absent paths are refused only where they are opened.** `transcriptPath`
   and `transcriptDir` get `path_not_found`. `claimedPaths` are only compared,
   and absence is what the file-claim check measures, so they still pass.
3. **The opened descriptor is checked.** The surface flags its paths as
   resolved; the daemon opens the path as given, asks the kernel where the
   descriptor points, and refuses a mismatch with `400 evidence_path_changed`
   before reading. Re-resolving at read time failed, because it happens after
   the swap.
4. **Evidence is capped at 3,000 characters** by default, with a visible
   truncation marker. On one host and model (n = 5 per budget) the p95 at that
   cap was 36.62 s, against 19.69 s at 800.

| Option | Why not |
|---|---|
| Revision-shape allowlist | `main` and a directory path look identical |
| Treat a bad revision as abstain | Reopens the evasion |
| Refuse every absent path | Disables the file-claim check |
| `O_NOFOLLOW` alone | Covers only the final path component |

## Limits

- **Linux only.** The check needs `/proc/self/fd`. Elsewhere the daemon answers
  `503 verified_read_unavailable` to a flagged request; unflagged, it runs
  unverified.
- Only the MCP surface sets the flag; CLI reads are unverified.
- The original 8 s latency target was unreachable: an empty-evidence call took a
  median 7.30 s (n = 3). The charter now says 40 s.

ADR 0019 and 0021 were amended later; this follows the amended text. See
[[wiki/agent-warden/components/mcp-surface]].
