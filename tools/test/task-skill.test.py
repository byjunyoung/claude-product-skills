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

# --- the router holds what the three modes share ---
ROUTER = (TASK / "SKILL.md").read_text(encoding="utf-8")
MODE_FILES = sorted(TASK.glob("*.md"))

# each shared block once — a lifted block is deleted from the mode files, not copied
SHARED = ["**Part of a plugin.**", "Exit 3 means no adapter exists", "Matching runs on `task.link_property`",
          "These tasks are kept as records only", "Never invent a mapping", "before the first write of the session",
          "Written for the people who will act on it"]
bad = []
for s in SHARED:
    where = {p.name: p.read_text(encoding="utf-8").count(s) for p in MODE_FILES}
    total = sum(where.values())
    if total != 1 or where.get("SKILL.md") != 1:
        bad.append(f"{s!r}: " + ", ".join(f"{k}×{v}" for k, v in where.items() if v) if total else f"{s!r}: nowhere")
check("each shared block once", not bad, "; ".join(bad))

# argument grammar
GRAMMAR = ["/pm:task draft <source> [<record>]", "/pm:task publish <record> [--contract | --template]", "/pm:task sync [all | mine]"]
absent = [g for g in GRAMMAR if g not in ROUTER]
old_input = [f"{p.name}: {s}" for p in MODE_FILES for s in ("--mode contract", "`mode` (optional)")
             if s in p.read_text(encoding="utf-8")]
check("argument grammar", not absent and not old_input, f"missing {absent}; old input still named {old_input}")


def first_command(text, needle):
    """The first command line holding `needle`, with its backslash continuations joined."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if needle in line:
            cmd = [line]
            while cmd[-1].rstrip().endswith("\\") and i + 1 < len(lines):
                i += 1
                cmd.append(lines[i])
            return " ".join(l.rstrip().rstrip("\\") for l in cmd)
    return None


# record-only check comes before the mode's --need
first = first_command(ROUTER, "resolve-config.py")
msg_at = ROUTER.find("These tasks are kept as records only")
need_at = ROUTER.find("--need task.record.ref,task.link_property")
check("record-only check comes before the mode's --need",
      first is not None and "--need" not in first and 0 <= msg_at < need_at,
      f"first call {first!r}; message at {msg_at}, first --need at {need_at}")

# unverified marks are cleared by a run in any mode — and setup and the trackers contract say the same
paragraphs = re.split(r"\n\s*\n", ROUTER)
described = any("(unverified)" in p and "remove" in p and "any `/pm:task` mode" in p for p in paragraphs)
ANY_MODE = "any `/pm:task` mode"
setup = read("plugins/pm/skills/setup/SKILL.md")
promise = [l for l in setup.splitlines() if "(unverified)" in l and "/pm:task" in l]
contract = " ".join(read("plugins/pm/_common/trackers/README.md").split())
check("unverified marks are cleared by a run",
      described and promise and all(ANY_MODE in l for l in promise) and ANY_MODE in contract,
      f"router paragraph with remove + (unverified) + any mode: {described}; setup lines {promise}; "
      f"trackers/README.md says any mode: {ANY_MODE in contract}")

# the router stays short
n = len(ROUTER.splitlines())
check("the router stays short", n < 200, f"{n} lines")

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("task skill · PASS")
