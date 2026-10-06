#!/usr/bin/env python3
"""Wiki gate — no dead links, no orphan pages, no uncited or stale wiki pages.

Run:   python3 tools/check_wiki.py content                  # portfolio deploy
       python3 tools/check_wiki.py docs/wiki --repo . --project   # project repo
Check: python3 tools/test_check_wiki.py                     (proven red)

Gates (exit 1 on any hit):
  1. every [[wikilink]] resolves to a published page (Quartz "shortest"
     resolution; draft: true pages are dropped by RemoveDrafts, so a link to
     one is dead on the live site)
  2. every page under wiki/ is reachable from a page outside wiki/ — a
     second brain nobody can navigate into does not exist for the reader
  3. every page under wiki/ declares `cites:` and `verified_at:`
  4. with --repo: each cited path exists at HEAD, and none changed since
     verified_at (`git diff --quiet <verified_at> HEAD -- <paths>`) — STALE
  6. with --public: no docs/ or .claude/ file is tracked (plans and agent
     config name private hosts; this repo is public)

--project: the root IS the wiki (no wiki/ subfolder) and nothing is published
from here, so every page counts as a wiki page, drafts are checked too, and
reachability starts at index pages.

Gate 5 (no links to private targets) lives in the private sync tool: listing
the private names here would publish them.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

LINK = re.compile(r"!?\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FENCE = re.compile(r"```.*?```", re.S)


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def field(fm, name):
    m = re.search(rf"^{name}:[ \t]*(.*)$", fm, re.M)
    return m.group(1).strip().strip("'\"") if m else None


def cited_paths(fm):
    m = re.search(r"^cites:[ \t]*\n((?:[ \t]+.*\n?)*)", fm, re.M)
    if not m:
        return []
    return [p.strip().strip("'\"") for p in
            re.findall(r"^[ \t]*-?[ \t]*(?:path:)?[ \t]*([^\s:][^\n]*?)[ \t]*$", m.group(1), re.M)
            if not re.match(r"^\s*lines:", p)]


def load(root):
    pages = {}
    for f in sorted(root.rglob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        pages[f.relative_to(root).with_suffix("").as_posix()] = {
            "text": text, "fm": fm, "draft": field(fm, "draft") == "true"}
    return pages


def resolve(target, published):
    t = target.strip().removesuffix(".md").strip("/")
    if t in published:
        return t
    hits = [p for p in published if p.endswith("/" + t) or p.rsplit("/", 1)[-1] == t]
    return hits[0] if len(hits) == 1 else None


def is_wiki(slug):
    return slug.startswith("wiki/") or "/wiki/" in slug or slug.split("/")[0] == "wiki"


def check(root, repo=None, public=False, project=False):
    pages = load(root)
    published = {s: p for s, p in pages.items() if project or not p["draft"]}
    is_wiki = (lambda s: True) if project else globals()["is_wiki"]
    errors, edges = [], {s: set() for s in published}

    for slug, page in published.items():
        for target in LINK.findall(FENCE.sub("", page["text"])):
            hit = resolve(target, published)
            if hit is None:
                errors.append(f"{slug}: dead link [[{target}]]")
            else:
                edges[slug].add(hit)

    seen = [s for s in published if not is_wiki(s) or (project and s.endswith("index"))]
    reached = set(seen)
    while seen:
        for nxt in edges[seen.pop()] - reached:
            reached.add(nxt)
            seen.append(nxt)
    for slug in published:
        if is_wiki(slug) and slug not in reached and not slug.endswith("index"):
            errors.append(f"{slug}: orphan — not reachable from any project page")

    for slug, page in published.items():
        if not is_wiki(slug) or slug.endswith("index"):
            continue
        paths, sha = cited_paths(page["fm"]), field(page["fm"], "verified_at")
        if not paths:
            errors.append(f"{slug}: no cites:")
        if not sha:
            errors.append(f"{slug}: no verified_at:")
        if repo and paths and sha:
            for p in paths:
                if subprocess.run(["git", "-C", repo, "cat-file", "-e", f"HEAD:{p}"],
                                  capture_output=True).returncode:
                    errors.append(f"{slug}: cited path missing at HEAD: {p}")
            diff = subprocess.run(["git", "-C", repo, "diff", "--quiet", sha, "HEAD", "--", *paths],
                                  capture_output=True)
            if diff.returncode == 1:
                errors.append(f"{slug}: STALE — cited files changed since {sha}")
            elif diff.returncode:
                errors.append(f"{slug}: verified_at {sha} unknown to git")

    if public:
        tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--full-name",
                                  ":(top)docs", ":(top).claude"],
                                 capture_output=True, text=True).stdout.split()
        errors += [f"private file tracked in public repo: {t}" for t in tracked]
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--repo", help="git repo the cites: paths are relative to")
    ap.add_argument("--public", action="store_true", help="also run gate 6")
    ap.add_argument("--project", action="store_true", help="root is the wiki; check drafts")
    a = ap.parse_args()
    errors = check(a.root, a.repo, a.public, a.project)
    for e in errors:
        print(e)
    print(f"{len(load(a.root))} page(s) checked, {len(errors)} problem(s).")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
