#!/usr/bin/env python3
"""Fixtures for tools/verify.py — does the checker read every file a skill can live in?
Each case copies the repository, plants one file, and runs the copy's own verify.py.

    python3 tools/test/verify.test.py
"""
import json, re, shutil, subprocess, sys, tempfile
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

def set_description(text, desc):
    """Replace the frontmatter description (one line or folded) with a one-line value."""
    head, rest = text.split("\n---", 1)[0], text.split("\n---", 1)[1]
    head = re.sub(r"^description:.*?(?=^\S|\Z)", f"description: {desc}\n", head + "\n", flags=re.S | re.M).rstrip("\n")
    return head + "\n---" + rest


def plant_desc(r, skill, desc, dest=None):
    src = r / "plugins" / "pm" / "skills" / skill / "SKILL.md"
    text = set_description(src.read_text(), desc)
    if dest:
        text = re.sub(r"^name:.*$", f"name: {dest}", text, count=1, flags=re.M)
        shutil.copytree(src.parent, r / "plugins" / "pm" / "skills" / dest, dirs_exist_ok=True)   # dest may already be a real skill
        src = r / "plugins" / "pm" / "skills" / dest / "SKILL.md"
    src.write_text(text, encoding="utf-8")


case("long description fails",
     lambda r: plant_desc(r, "log-review", "a" * 600),
     1, "[pm:log-review] description is 600 characters (limit 500)")

with tempfile.TemporaryDirectory() as tmp:
    repo = copy_repo(tmp)
    plant_desc(repo, "log-review", "a" * 650, dest="task")
    rc, out = verify(repo)
    lines = [l for l in out.splitlines() if "[pm:task] description is" in l]
    check("override limit applies", not lines, "\n".join(lines))

case("a 750-character deck description fails even under its 700 override",
     lambda r: (r / "plugins/fig/skills/deck/SKILL.md").write_text(
         set_description((r / "plugins/fig/skills/deck/SKILL.md").read_text(), "a" * 750), encoding="utf-8"),
     1, "[fig:deck] description is 750 characters (limit 700)")


def plant_market_drift(r):
    f = r / "plugins" / "pm" / ".claude-plugin" / "plugin.json"
    d = json.loads(f.read_text())
    d["description"] += " (edited)"
    f.write_text(json.dumps(d, indent=2, ensure_ascii=False))


case("marketplace and plugin.json differ", plant_market_drift,
     1, "[pm] plugin.json and marketplace.json descriptions differ")

def plant_sections_deep_drift(r):
    f = r / "plugins" / "fig" / "_common" / "scripts" / "audit-flow.js"
    t = f.read_text(encoding="utf-8")
    start = t.index("// <sections-deep>")
    # Change one character inside the marked block only
    f.write_text(t[:start] + t[start:].replace("inherited = false", "inherited = true", 1), encoding="utf-8")


case("sections-deep copies differ", plant_sections_deep_drift,
     1, "[fig] sections-deep copy in audit-flow.js differs from audit-component.js")


def plant_probe_drift(r):
    """probe-page.js is not an audit-*.js script, and still carries the block."""
    f = r / "plugins" / "fig" / "_common" / "scripts" / "probe-page.js"
    t = f.read_text(encoding="utf-8")
    start = t.index("// <sections-deep>")
    f.write_text(t[:start] + t[start:].replace("inherited = false", "inherited = true", 1), encoding="utf-8")


case("a drifted sections-deep copy in probe-page.js fails, naming it and the reference file",
     plant_probe_drift,
     1, "[fig] sections-deep copy in probe-page.js differs from audit-component.js")


def plant_missing_marker(r):
    f = r / "plugins" / "fig" / "_common" / "scripts" / "audit-struct.js"
    f.write_text(f.read_text(encoding="utf-8").replace("// <sections-deep>", "// (marker removed)"), encoding="utf-8")


case("an audit script that lost its sections-deep marker fails", plant_missing_marker,
     1, "[fig] sections-deep marker missing from audit-struct.js")


def strip_scaffolding(r):
    # The real copies (audit-tokens.js, and the bind script after it) would join either case below,
    # so each case starts from scripts that carry none.
    pat = re.compile(r"// <scaffolding>\n.*?// </scaffolding>\n?", re.S)
    for f in (r / "plugins" / "fig" / "_common" / "scripts").glob("*.js"):
        t = f.read_text(encoding="utf-8")
        if pat.search(t):
            f.write_text(pat.sub("", t), encoding="utf-8")


def plant_scaffolding_drift(r):
    strip_scaffolding(r)
    d = r / "plugins" / "fig" / "_common" / "scripts"
    for name, body in (("audit-flow.js", "// one"), ("audit-struct.js", "// two")):
        f = d / name
        f.write_text(f.read_text(encoding="utf-8") + f"\n// <scaffolding>\n{body}\n// </scaffolding>\n", encoding="utf-8")


case("a drifted scaffolding copy fails", plant_scaffolding_drift,
     1, "[fig] scaffolding copy in audit-struct.js differs from audit-flow.js")


def plant_lone_scaffolding(r):
    strip_scaffolding(r)
    f = r / "plugins" / "fig" / "_common" / "scripts" / "audit-flow.js"
    f.write_text(f.read_text(encoding="utf-8") + "\n// <scaffolding>\n// one\n// </scaffolding>\n", encoding="utf-8")


case("a marked block carried by one file only passes", plant_lone_scaffolding, 0)

def plant_paint_scope_drift(r):
    f = r / "plugins" / "fig" / "_common" / "scripts" / "token-bind.js"
    t = f.read_text(encoding="utf-8")
    start = t.index("// <paint-scope>")
    f.write_text(t[:start] + t[start:].replace('id !== ""', 'id !== "-"', 1), encoding="utf-8")


case("a drifted paint-scope copy fails, so the bind cannot read a style the audit does not",
     plant_paint_scope_drift,
     1, "[fig] paint-scope copy in token-bind.js differs from audit-tokens.js")

case("unknown config key in a _common document",
     lambda r: write(r, "plugins/pm/_common/trackers/README.md", "\n`task.nonexistent_key`\n", append=True),
     1, "[pm] plugins/pm/_common/trackers/README.md: `task.nonexistent_key` is not in the schema")


def plant_team_common(r):
    write(r, "tools/team-strings.local.txt", "ZZTEAMZZ\n")
    write(r, "plugins/pm/_common/trackers/README.md", "\nZZTEAMZZ\n", append=True)


case("team string in a _common document", plant_team_common,
     1, "[pm] plugins/pm/_common/trackers/README.md: team value 'ZZTEAMZZ'")

case("stale reference in a _common script comment",
     lambda r: write(r, "plugins/fig/_common/scripts/deck-base.js", "\n// see /fig:nonexistent\n", append=True),
     1, "→ /fig:nonexistent does not exist")

case("a rename map to a skill that exists passes",
     lambda r: [write(r, f, "\n`/pm:old-name → /pm:setup`\n", append=True) for f in ("README.md", "README.ko.md")],
     0)

case("a rename map to a skill that does not exist still fails",
     lambda r: write(r, "README.md", "\n`/pm:old-name → /pm:nonexistent`\n", append=True),
     1, "→ /pm:nonexistent does not exist")

case("a rename map with both ends backticked passes",
     lambda r: [write(r, f, "\n`/pm:old-name` → `/pm:setup`\n", append=True) for f in ("README.md", "README.ko.md")],
     0)

case("a bare stale name next to a backticked rename map still fails",
     lambda r: write(r, "README.md",
                     "\n`/fig:old-name` → `/fig:read`\n\nRun /fig:old-name to see it.\n", append=True),
     1, "→ /fig:old-name does not exist")

case("a removal note in either language passes",
     lambda r: [write(r, f, n, append=True) for f, n in (
         ("README.md", "\n`/fig:old-name` → (removed — nothing replaces it)\n"),
         ("README.ko.md", "\n`/fig:old-name` → (삭제 — 대체하는 스킬은 없다)\n"))],
     0)

case("a bare stale name next to a removal note still fails",
     lambda r: write(r, "README.md",
                     "\n`/fig:old-name` → (removed — nothing replaces it)\n\nRun /fig:old-name to see it.\n", append=True),
     1, "→ /fig:old-name does not exist")

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("verify fixtures · PASS")
