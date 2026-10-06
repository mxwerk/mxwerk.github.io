"""Run: python3 tools/test_check_wiki.py — proves every gate can report RED.

Each test builds a tiny site in a temp dir with exactly one defect and asserts
the gate names it; the clean site must pass. A gate nobody watched fail is a
hypothesis, not evidence.
"""
import subprocess
import tempfile
from pathlib import Path

from check_wiki import check

PAGE = "---\ntitle: {t}\n{fm}---\n\n{body}\n"


def site(files, git=False):
    root = Path(tempfile.mkdtemp())
    for rel, text in files.items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    if git:
        run = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)
        run("init", "-q")
        run("-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    return root


def head(root):
    return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


CITED = "cites:\n  - path: src/a.py\n    lines: 1-2\nverified_at: {sha}\n"


def clean(sha="abc1234"):
    return {
        "projects/p.md": PAGE.format(t="P", fm="", body="See [[wiki/p/judge|the judge]]."),
        "wiki/p/judge.md": PAGE.format(t="Judge", fm=CITED.format(sha=sha), body="Back to [[p]]."),
        "src/a.py": "x = 1\n",
    }


def test_clean_site_passes():
    root = site(clean())
    assert check(root) == [], check(root)


def test_dead_link():
    files = clean()
    files["projects/p.md"] = PAGE.format(t="P", fm="", body="[[wiki/p/judge]] and [[nowhere]]")
    assert any("dead link [[nowhere]]" in e for e in check(site(files)))


def test_link_to_draft_is_dead():
    files = clean()
    files["wiki/p/judge.md"] = files["wiki/p/judge.md"].replace("title: Judge\n", "title: Judge\ndraft: true\n")
    assert any("dead link" in e for e in check(site(files)))


def test_orphan():
    files = clean()
    files["wiki/p/lonely.md"] = PAGE.format(t="L", fm=CITED.format(sha="abc1234"), body="nobody links here")
    assert any("wiki/p/lonely: orphan" in e for e in check(site(files)))


def test_missing_cites():
    files = clean()
    files["wiki/p/judge.md"] = PAGE.format(t="J", fm="", body="[[p]]")
    errs = check(site(files))
    assert any("no cites:" in e for e in errs) and any("no verified_at:" in e for e in errs), errs


def test_fresh_then_stale():
    root = site(clean(), git=True)
    page = root / "wiki/p/judge.md"
    page.write_text(page.read_text().replace("abc1234", head(root)))
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qam", "verify"], check=True)
    assert check(root, repo=str(root)) == [], check(root, repo=str(root))
    (root / "src/a.py").write_text("x = 2\n")
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qam", "change cited code"], check=True)
    assert any("STALE" in e for e in check(root, repo=str(root)))


def test_cited_path_missing():
    files = clean()
    files["wiki/p/judge.md"] = files["wiki/p/judge.md"].replace("src/a.py", "src/gone.py")
    root = site(files, git=True)
    assert any("missing at HEAD: src/gone.py" in e for e in check(root, repo=str(root)))


def test_private_dirs_tracked():
    files = clean()
    files["docs/plans/x.md"] = "secret host\n"
    root = site(files, git=True)
    assert any("docs/plans/x.md" in e for e in check(root, public=True))


def project_site():
    return {
        "index.md": PAGE.format(t="Wiki", fm="", body="[[decisions/gate]]"),
        "decisions/gate.md": PAGE.format(t="Gate", fm="draft: true\n" + CITED.format(sha="abc1234"), body="x"),
    }


def test_project_mode_clean_passes():
    assert check(site(project_site()), project=True) == []


def test_project_mode_checks_drafts_without_wiki_folder():
    files = project_site()
    files["decisions/gate.md"] = PAGE.format(t="Gate", fm="draft: true\n", body="x")
    files["decisions/lonely.md"] = PAGE.format(t="L", fm=CITED.format(sha="abc1234"), body="x")
    root = site(files)
    blind = check(root)  # default mode: no wiki/ folder, so no cites/orphan gate
    assert not any("no cites" in e or "orphan" in e for e in blind), blind
    errs = check(root, project=True)
    assert any("decisions/gate: no cites:" in e for e in errs), errs
    assert any("decisions/lonely: orphan" in e for e in errs), errs


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print("ok  ", name)
    print(f"{len(tests)} passed")
