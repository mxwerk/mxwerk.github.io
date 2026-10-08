---
title: CI judges from a committed artifact
description: The ruleset gate in CI reads its rules and its own code from a directory committed in the repository, checked against a hand-maintained digest per ruleset, so the rules in force are the ones in the commit being judged.
draft: false
cites:
  - path: docs/adr/014-ci-judges-from-a-committed-artifact.md
    lines: 12-38, 42-54, 56-112, 147-157, 167-199, 207-239
  - path: .claude/gate/README.md
    lines: 1-9
  - path: .claude/gate/MANIFEST.json
    lines: 1-38
  - path: .claude/gate/orchestrator/gates/run.py
    lines: 68-82, 105-141
  - path: .claude/gate/orchestrator/gates/forbidden_patterns.py
    lines: 1-12, 49-55
  - path: scripts/gate-artifact.py
    lines: 15-24, 109-121, 147-167, 170-203, 206-242, 245-297, 310-396, 399-537, 540-581
  - path: scripts/test_gate_artifact.py
    lines: 1-20, 207-236, 544-560
  - path: .forgejo/workflows/ci.yml
    lines: 112-191
  - path: .claude/rulesets.lock.yaml
    lines: 22-37, 46-80
  - path: .forgejo/ci-image/Dockerfile
    lines: 10-11, 43-52, 58-66
verified_at: 262e98e
---

# CI judges from a committed artifact

> **TL;DR** — A lock file names eight rulesets this repository is judged against, but the rules and
> the program that applies them live in a private configuration repository outside it. ADR 014
> commits a copy of exactly those inputs under `.claude/gate/` and has CI run the gate from that
> copy. A script builds the copy and verifies it against the lock; the lock carries a `sha256` per
> ruleset that a person maintains by hand. The claim is that a changed rule shows up in the diff,
> not that it cannot be changed.
> [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

The lock had pinned eight rulesets for some time, and nothing in CI read any of them. The pattern
gate ran only when someone invoked it by hand, against whatever ruleset versions were in that
person's configuration directory at the moment.

The standard ADR 014 answers comes from a sibling project: a check may gate CI only if every input
it judges against is in the commit it judges, or pinned by that commit to a verifiable digest. The
lock recorded a name and a version per ruleset and no digest. A version is identity, not a pin: any
file that calls itself `1.3.0` satisfies it. The gate runner confirms the gap from its own side: on
a version mismatch it writes a warning and carries on with the ruleset it found.

Two constraints narrowed the choice. The CI job image had no Python interpreter, and the gate is
Python. And a neighbouring project (agent-cockpit) had already built a committed artifact, so the
question was whether to adopt that mechanism or justify a divergence.

## The decision

`.claude/gate/` is committed. `scripts/gate-artifact.py build` writes it, `verify` checks it against
the lock, and a CI job named `ruleset-gate` runs `verify`, then the gates the artifact declares,
then the mechanism's own tests. The CI image gains `python3` and `python3-yaml`.

| Option | Why not |
| --- | --- |
| Point CI at a configuration directory on the runner | The lock held name and version only, so nothing ties the runner's files to the commit. |
| Clone the configuration repository in CI | It also holds instructions, handoffs, memory and a backlog that do not belong on a runner. |
| Port the gate to Node, which the image already had | A reimplementation: the committed thing would no longer be the gate that runs upstream, and a difference between the two could not be seen. |
| Run the gate in a Python container through the Docker daemon | Couples a file-and-regex check to the daemon and adds an image pull per run. |
| Copy all gate modules, as the neighbouring project does (21) | 17 of the 21 never run in a Java repository. An allowlist of 4 is used and proven complete by running it. |
| Pin by version inside the artifact only | A ruleset edited in place keeps its version, which is the weakness that made the lock insufficient. |
| Let `build` write the digest into the lock | One run would then produce the ruleset copy, the manifest entry and the pin meant to check both. |

## How it works

**What is committed.** `MANIFEST.json` lists 13 files with a sha256 each: a README, four gate
modules (`run.py`, `forbidden_patterns.py`, `containment.py`, `text_context.py`) and eight ruleset
files. It also records the lock file's own sha256, each ruleset's version, and the declared gates,
of which there is one: `forbidden_patterns`. Despite its name that gate enforces both patterns that
must not match and patterns that must match at least once.

**`build`** is an operator action. It copies the named modules and only the lock-pinned rulesets
from the configuration directory into a staging directory. It refuses, and leaves the old artifact
in place, when a ruleset's version differs from the lock, when a lock entry has no `sha256`, or when
the bytes do not hash to the pinned value; in the last two cases it prints the digest it measured
instead of writing it. It then runs each declared gate from the staged tree and refuses if a gate
errors, which is how a missing support module is caught. Only then is the staged tree swapped in.

**`verify`** returns a list of problems and exits non-zero if there is one. It checks that:

- the lock's sha256 equals the one the manifest recorded;
- every pinned ruleset is shipped and every shipped ruleset is pinned;
- each shipped ruleset's version and sha256 equal the lock's;
- every file hashes to the manifest's digest, and no unrecorded file is present;
- each declared gate has its module and `run.py` exists;
- no runtime output (`bus/`, `__pycache__`) is tracked inside the artifact, and a failing `git` call
  is reported as unknown, not as clean.

**The CI job** has no `if:` and no `needs:`. It first checks that `python3` and PyYAML are present
and names the image rebuild if not. It runs `verify`, then asks the script for the gate list from
the manifest and runs the artifact's own `run.py` for each with `CLAUDE_CONFIG_DIR` pointed at the
artifact. The runner resolves rulesets from that directory, so the rules applied are the committed
ones. For each gate the job asserts that the reported `files_checked` and `patterns_checked` are
both non-zero, so a run that looked at nothing does not read as a pass.

**The self-tests** are a plain Python script, not a test framework. Each case copies the committed
artifact into a temporary tree, breaks the copy in one way and asserts the refusal. One case edits a
ruleset and rewrites the manifest around the edit: the manifest pass agrees with itself, and the
lock's digest reports the mismatch.

## What it costs / limits

- **Visibility, not impossibility.** Whoever writes a commit can change a rule, rebuild, and change
  the lock's digest too. What the mechanism buys is that this appears as a changed `sha256` under an
  unchanged `version` in the file a reviewer reads.
- **The gate modules are not pinned by the lock.** They are checked against the manifest only, which
  `build` writes. The ADR accepts this on the argument that an edit to them has no routine-looking
  cover.
- **The image is built by hand.** It is not pushed to a registry, so the job fails, with a message
  naming the rebuild, until the image carries the interpreter.
- **A rebuild is owed whenever the lock or a pinned ruleset changes.** `verify` turns a forgotten
  one into a failing job. Adopting a ruleset version is a two-line lock edit, `version` and
  `sha256`.
- **Generated content lives in the tree:** 14 tracked files under `.claude/gate/` (13 in the
  manifest plus the manifest itself).
- **One gate only.** The ADR notes that the runner's coverage gate reports an error here because it
  expects a file this build never writes; coverage is enforced by `check` instead, see
  [[wiki/agent-workorders/components/quality-gate]].

## Later changes

- **Test count.** The ADR says 29 cases. The script defines 30 functions named `test_...` (counted
  with grep), and its `main` runs every such function.
- **The ADR corrected itself twice in place.** An earlier revision claimed the manifest digests
  defend against a coordinated edit; the "Two digests" section withdraws that. It also records that
  the tracked-output check was half broken (the bytecode half matched nothing) and is now one
  function, `_is_output`, shared by the digests and the check.
