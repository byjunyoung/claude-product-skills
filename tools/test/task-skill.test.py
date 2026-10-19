#!/usr/bin/env python3
"""The three pm task skills live in one folder, /pm:task, and the old names are gone.

    python3 tools/test/task-skill.test.py
"""
import os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "plugins/pm/skills/task"
OLD = ("task-draft", "task-publish", "task-sync")
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def tracked_files():
    # Inside a git hook, GIT_DIR and friends point at the real repository; drop every GIT_* key.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, env=env, capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


# one folder
missing = [n for n in ("SKILL.md", "draft.md", "publish.md", "sync.md") if not (TASK / n).exists()]
leftover = [o for o in OLD if (REPO / "plugins/pm/skills" / o).exists()]
check("one folder", not missing and not leftover, f"missing {missing}; old folders still there {leftover}")

# no old name outside history. A line that also holds ' → /pm:task ' is the old → new arrow
# the READMEs carry on purpose.
SELF = Path(__file__).resolve()
hits = []
for rel in tracked_files():
    p = REPO / rel
    if rel.startswith("docs/") or re.fullmatch(r"plugins/[^/]+/CHANGELOG\.md", rel) or not p.is_file() or p.resolve() == SELF:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    for n, line in enumerate(text.splitlines(), 1):
        if any(o in line for o in OLD) and " → /pm:task " not in line:
            hits.append(f"{rel}:{n}")
check("no old name outside history", not hits, f"{len(hits)} hits, e.g. {hits[:8]}")

# readmes map the old names
ARROWS = ["/pm:task-draft → /pm:task draft", "/pm:task-publish → /pm:task publish", "/pm:task-sync → /pm:task sync"]
for rel in ("README.md", "README.ko.md"):
    text = read(rel)
    absent = [a for a in ARROWS if a not in text]
    check(f"readmes map the old names ({rel})", not absent, f"missing {absent}")

# the skill table lists task once
for rel in ("plugins/pm/README.md", "README.md", "README.ko.md"):
    rows = [l for l in read(rel).splitlines() if re.match(r"^\|\s*`/pm:task`\s*\|", l)]
    check(f"the skill table lists task once ({rel})", len(rows) == 1, f"{len(rows)} rows")

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("task skill · PASS")
