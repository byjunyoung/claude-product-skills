#!/usr/bin/env python3
"""Fixtures for adapter.py — where the calls for a tool are found, and the exit a skill stops on.

    python3 tools/test/adapter.test.py

HOME is a temp dir for every case, with PYTHONUSERBASE pinned back so a `--user` PyYAML is
still found (see resolve-config.test.py).
"""
import os, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMMON = REPO / "plugins" / "pm" / "_common"
SCRIPT = COMMON / "scripts" / "lib" / "adapter.py"
failures = []


def run(cwd, home, *args):
    env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase())
    return subprocess.run([sys.executable, str(SCRIPT), "--name", "pm-conventions.yaml", *args],
                          cwd=cwd, env=env, capture_output=True, text=True)


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


with tempfile.TemporaryDirectory() as tmp:
    home, proj = Path(tmp) / "home", Path(tmp) / "proj"
    (home / ".claude").mkdir(parents=True)
    proj.mkdir()

    r = run(proj, home, "--kind", "trackers", "--type", "notion")
    check("bundled tracker → its path", r.returncode == 0 and Path(r.stdout.strip()) == COMMON / "trackers" / "notion.md", r.stdout + r.stderr)
    r = run(proj, home, "--kind", "sources", "--type", "slack")
    check("bundled source → its path", r.returncode == 0 and Path(r.stdout.strip()) == COMMON / "sources" / "slack.md", r.stdout + r.stderr)
    r = run(proj, home, "--kind", "trackers", "--type", "none")
    check("none → 'none', exit 0", r.returncode == 0 and r.stdout.strip() == "none")
    r = run(proj, home, "--kind", "trackers")
    check("no --type → exit 1, says it is required", r.returncode == 1 and "--type is required" in r.stderr and r.stdout.strip() == "", f"rc={r.returncode} {r.stderr}")
    r = run(proj, home, "--kind", "trackers", "--type", "linear")
    check("unknown → exit 3", r.returncode == 3, f"rc={r.returncode}")
    check("unknown → template named on stderr", "_template.md" in r.stderr and "linear" in r.stderr, r.stderr)
    check("unknown → nothing on stdout", r.stdout.strip() == "")

    # A drafted adapter in the project dir (the default adapters.dirs) is found
    (proj / "pm-adapters" / "trackers").mkdir(parents=True)
    (proj / "pm-adapters" / "trackers" / "linear.md").write_text("# Linear\n")
    r = run(proj, home, "--kind", "trackers", "--type", "linear")
    check("project adapter → found", r.returncode == 0 and r.stdout.strip().endswith("pm-adapters/trackers/linear.md"), r.stdout + r.stderr)

    # A user copy with a bundled name covers the bundled one; a project copy covers both
    (home / ".claude" / "pm-adapters" / "trackers").mkdir(parents=True)
    (home / ".claude" / "pm-adapters" / "trackers" / "notion.md").write_text("# mine\n")
    r = run(proj, home, "--kind", "trackers", "--type", "notion")
    check("home adapter → covers bundled", Path(r.stdout.strip()).resolve() == (home / ".claude" / "pm-adapters" / "trackers" / "notion.md").resolve(), r.stdout)
    (proj / "pm-adapters" / "trackers" / "notion.md").write_text("# project\n")
    r = run(proj, home, "--kind", "trackers", "--type", "notion")
    check("project adapter → covers home", Path(r.stdout.strip()).resolve() == (proj / "pm-adapters" / "trackers" / "notion.md").resolve(), r.stdout)

    # adapters.dirs from the config is honoured, and ~ expands
    (proj / "pm-conventions.yaml").write_text('adapters:\n  dirs: ["~/my-adapters"]\n')
    (home / "my-adapters" / "sources").mkdir(parents=True)
    (home / "my-adapters" / "sources" / "teams.md").write_text("# Teams\n")
    r = run(proj, home, "--kind", "sources", "--type", "teams")
    check("adapters.dirs from config, ~ expanded", r.returncode == 0 and Path(r.stdout.strip()).resolve() == (home / "my-adapters" / "sources" / "teams.md").resolve(), r.stdout + r.stderr)

    # --role: a bundled mirror file asked for the record side is refused with exit 4.
    # The case above pointed adapters.dirs elsewhere; put the default back first
    (proj / "pm-conventions.yaml").unlink()
    r = run(proj, home, "--kind", "trackers", "--type", "github", "--role", "record")
    check("github as record → exit 4", r.returncode == 4 and "supported as the mirror side" in r.stderr, f"rc={r.returncode} {r.stderr}")
    r = run(proj, home, "--kind", "trackers", "--type", "github", "--role", "mirror")
    check("github as mirror → found", r.returncode == 0 and r.stdout.strip().endswith("trackers/github.md"), r.stderr)
    r = run(proj, home, "--kind", "sources", "--type", "slack", "--role", "calendar")
    check("slack as calendar → exit 4", r.returncode == 4, f"rc={r.returncode}")
    (proj / "pm-adapters" / "trackers" / "linear.md").write_text("# Linear\n")   # no roles line
    r = run(proj, home, "--kind", "trackers", "--type", "linear", "--role", "mirror")
    check("adapter without roles: → serves every side", r.returncode == 0, r.stderr)
    r = run(proj, home, "--kind", "trackers", "--type", "github", "--role", "chat")
    check("a role that is not a tracker role → refused", r.returncode not in (0, 4), f"rc={r.returncode}")

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("adapter fixtures · PASS")
