#!/usr/bin/env python3
"""Fixtures for tools/verify.py — does the checker read every file a skill can live in?
Each case copies the repository, plants one file, and runs the copy's own verify.py.

    python3 tools/test/verify.test.py
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def copy_repo(tmp) -> Path:
    """A throwaway copy of the repository. The machine's own team-strings file is dropped so every
    case starts from the same baseline; a case that needs one writes its own."""
    dst = Path(tmp) / "repo"
    shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns(".git", "node_modules", "node_modules.nosync", ".claude"))
    (dst / "tools" / "team-strings.local.txt").unlink(missing_ok=True)
    return dst


def verify(repo):
    r = subprocess.run([sys.executable, str(repo / "tools" / "verify.py")], cwd=repo, capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout + r.stderr


def case(label, plant, code, *contains):
    with tempfile.TemporaryDirectory() as tmp:
        repo = copy_repo(tmp)
        plant(repo)
        rc, out = verify(repo)
        ok = rc == code and all(s in out for s in contains)
        check(label, ok, f"exit {rc}, wanted {code}; missing {[s for s in contains if s not in out]}\n{out[-1500:]}")


def write(repo, rel, text, append=False):
    f = repo / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a" if append else "w", encoding="utf-8") as h:
        h.write(text)


case("clean copy passes", lambda r: None, 0)

case("stale reference in a mode file",
     lambda r: write(r, "plugins/pm/skills/prd/notes.md", "see /pm:nonexistent\n"),
     1, "plugins/pm/skills/prd/notes.md → /pm:nonexistent does not exist")

case("cross-plugin stale reference in _common",
     lambda r: write(r, "plugins/pm/_common/trackers/README.md", "\n→ /fig:nonexistent\n", append=True),
     1, "→ /fig:nonexistent does not exist")

case("stale reference in the example config",
     lambda r: write(r, "plugins/fig/_common/conventions.example.yaml", "\n# → /pm:nonexistent\n", append=True),
     1, "→ /pm:nonexistent does not exist")

case("unknown config key in a mode file",
     lambda r: write(r, "plugins/fig/skills/lint/extra.md", "`qa.nonexistent_key`\n"),
     1, "extra.md: `qa.nonexistent_key` is not in the schema")


def plant_team(r):
    write(r, "tools/team-strings.local.txt", "ZZTEAMZZ\n")
    write(r, "plugins/pm/skills/prd/notes.md", "ZZTEAMZZ\n")


case("team string in a mode file", plant_team, 1, "team value 'ZZTEAMZZ'")

case("no team strings file → skipped, not failed", lambda r: None, 0,
     "no tools/team-strings.local.txt — the team-value check is skipped")

case("a url containing /pm: is not a reference",
     lambda r: write(r, "plugins/pm/skills/prd/notes.md", "`https://example.com/a/pm:b`\n"), 0)

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("verify fixtures · PASS")
