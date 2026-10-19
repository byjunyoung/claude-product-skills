#!/usr/bin/env python3
"""Fixtures for the fig skills that were removed or folded into another.
Reads the repository as it stands (no copy); every case is a plain look at a tracked file.

    python3 tools/test/fig-removals.test.py
"""
import os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def clean_env():
    # Inside a git hook, GIT_DIR and friends point at the real repository; drop every GIT_* key.
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def tracked_text_files():
    """Tracked text files, minus docs/, the plugins' CHANGELOGs (history says what it said), binaries
    and this file."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, env=clean_env(),
                         capture_output=True, text=True, check=True).stdout
    files = []
    for rel in filter(None, out.split("\0")):
        p = REPO / rel
        parts = Path(rel).parts
        if parts[0] == "docs" or p.resolve() == SELF or not p.is_file():
            continue
        if len(parts) == 3 and parts[0] == "plugins" and parts[2] == "CHANGELOG.md":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        files.append((rel, text))
    return files


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


# ---- /fig:diff -----------------------------------------------------------------------------------
check("diff skill folder is gone", not (REPO / "plugins/fig/skills/diff").exists())

stale = [f"{rel}:{n}" for rel, text in tracked_text_files()
         for n, line in enumerate(text.splitlines(), 1)
         if "/fig:diff" in line and "/fig:diff` → (" not in line]
check("no tracked file still names /fig:diff (outside the README map)", not stale, ", ".join(stale))

cfg = read("plugins/fig/_common/conventions.example.yaml")
check("retired diff keys gone from the schema",
      "annotation_category" not in cfg and "scope_tags" not in cfg)
check("keys other skills read stay", "ui_section_heading" in cfg and "text_diff_max_len" in cfg)

handoff = read("plugins/fig/skills/handoff/SKILL.md")
check("handoff owns the notion and github write",
      "ui_section_heading" in handoff and "add_issue_comment" in handoff
      and "issue_write" in handoff and "notion-update-page" in handoff
      and "/fig:diff" not in handoff)

for rel, marker in (("README.md", "/fig:diff` → (removed"), ("README.ko.md", "/fig:diff` → (삭제")):
    lines = [l for l in read(rel).splitlines() if marker in l]
    check(f"{rel} maps the removed /fig:diff", bool(lines) and all("Compare changes" in l for l in lines))

# ---- sync judges by name, not by pair -------------------------------------------------------------
RETIRED = "pair_" + "patterns"
sync = read("plugins/fig/skills/sync/SKILL.md")
sig1 = sync.split("**Signal 1", 1)[1].split("**Signal 2", 1)[0] if "**Signal 1" in sync else ""
check("sync compares by name, not by pair",
      "[screen]-[state]" in sig1 and RETIRED not in sync and "canonical" in sig1.lower()
      and "not on the canonical page" in sync)

holders = [f"{rel}:{n}" for rel, text in tracked_text_files()
           for n, line in enumerate(text.splitlines(), 1) if RETIRED in line]
check("the retired pair key is named nowhere", not holders, ", ".join(holders))

step16 = sync.split("Record the confirmed convention", 1)[1].split("### Step 2", 1)[0] if "Record the confirmed convention" in sync else ""
check("sync previews its config write",
      "preview" in step16.lower() and "~/.claude/figma-conventions.yaml" in step16
      and "./figma-conventions.yaml" in step16 and "symlink" in step16.lower())

draw = read("plugins/fig/skills/draw/SKILL.md")
check("draw no longer sends before-and-after to the AS-IS section",
      "AS-IS" not in draw and "canonical page and the working page" in draw)

# ---- one version-pin procedure --------------------------------------------------------------------
check("version-pin.md exists", (REPO / "plugins/fig/_common/version-pin.md").exists())
check("handoff and sync name version-pin.md",
      "version-pin.md" in handoff and "version-pin.md" in sync)
holders = [rel for rel, text in tracked_text_files()
           if rel.startswith("plugins/fig") and "api.figma.com/v1/files/{fileKey}/versions" in text]
check("the versions call lives in exactly one file", holders == ["plugins/fig/_common/version-pin.md"], ", ".join(holders))
sync_tools = sync.split("allowed-tools:", 1)[1].split("\n", 1)[0]
check("sync lists the browser tools", "mcp__claude-in-chrome__navigate" in sync_tools)
check("sync report counts unmatched-by-name items",
      "unmatched" in sync.split("## Reporting", 1)[1].split("## Implementation", 1)[0])

# ---- handoff previews before each write ------------------------------------------------------------
handoff = read("plugins/fig/skills/handoff/SKILL.md")
h_tools = handoff.split("allowed-tools:", 1)[1].split("\n", 1)[0]
check("handoff lists Skill", "Skill" in [t.strip() for t in h_tools.split(",")])
body = handoff.split("## Procedure", 1)[1]
def first(pat, text):
    m = re.search(pat, text, re.I)
    return m.start() if m else None


def without_heading(step):
    return step.split("\n", 1)[1] if "\n" in step else ""


vstep = without_heading(body.split("### 3.", 1)[1].split("### 4.", 1)[0]) if "### 3." in body else ""
g, sv = first(r"\bthe go\b", vstep), first(r"\bsave", vstep)
check("version step: go comes before save", g is not None and sv is not None and g < sv)
dstep = without_heading(body.split("### 4.", 1)[1].split("### 5.", 1)[0]) if "### 4." in body else ""
g, w = first(r"\bthe go\b", dstep), first(r"append-under", dstep)
check("doc-line step has its own go before the write", g is not None and w is not None and g < w)
check("notion write does not lean on a callout",
      "usually behind an empty callout" not in handoff and "whatever block opens the section" in handoff)

# ---- deck-setup folds into deck --------------------------------------------------------------------
check("deck-setup folder is gone", not (REPO / "plugins/fig/skills/deck-setup").exists())
stale = [f"{rel}:{n}" for rel, text in tracked_text_files()
         for n, line in enumerate(text.splitlines(), 1)
         if "deck-setup" in line and " → " not in line]
check("no tracked file names deck-setup (outside history and the README map)", not stale, ", ".join(stale))
for rel in ("README.md", "README.ko.md"):
    check(f"{rel} maps deck-setup to deck", "`/fig:deck-setup` → `/fig:deck`" in read(rel))

deck_dir = "plugins/fig/skills/deck/"
deck = read(deck_dir + "SKILL.md")
check("deck names setup.md and pitfalls.md", "setup.md" in deck and "pitfalls.md" in deck)
setup = read(deck_dir + "setup.md") if (REPO / (deck_dir + "setup.md")).exists() else ""
mirror = setup.split("## 1.", 1)[1].split("## 2.", 1)[0] if "## 1." in setup else ""
build = setup.split("## 5.", 1)[1] if "## 5." in setup else ""
check("setup checks the seat with whoami before the mirror file",
      "whoami" in mirror and first(r"whoami", mirror) < first(r"create_new_file", mirror))
m_list = without_heading(mirror).split("\n1.", 1)[-1]
w, g, c = first(r"\bwhoami\b", m_list), first(r"\bthe go\b", m_list), first(r"`create_new_file`", m_list)
check("mirror step order: whoami, then the go, then create_new_file",
      None not in (w, g, c) and w < g < c)
b_list = without_heading(build).split("\n1.", 1)[-1]
g, b = first(r"\bthe go\b", b_list), first(r"\bbuild a slide\b", b_list)
check("build step order: the go comes before the first build", None not in (g, b) and g < b)
check("setup never builds into the team's own template file",
      "never go into the team's own template file" in setup)
check("setup's mirror step waits for a go", bool(re.search(r"\bgo\b", mirror)))
check("setup's build step waits for a go", bool(re.search(r"\bgo\b", build)))
check("setup's report names the mirror file",
      "mirror file" in build.split("Report", 1)[-1] if "Report" in build else False)
tools = deck.split("allowed-tools:", 1)[1].split("\n", 1)[0]
check("deck lists the tools setup calls",
      all(t in tools for t in ("create_new_file", "whoami", "get_screenshot", "use_figma")))
dm = re.search(r"^description: (.*)$", deck, re.M)
check("deck description carries setup's triggers and stays under 700",
      bool(dm) and len(dm.group(1)) <= 700 and "덱 템플릿 뽑아줘" in dm.group(1)
      and "extract the slide template" in dm.group(1))
check("deck's structural step reads margins from the spec", "1792" not in deck and "128 /" not in deck)

pit = read(deck_dir + "pitfalls.md") if (REPO / (deck_dir + "pitfalls.md")).exists() else ""
check("pitfalls read from the template", bool(pit) and not any(x in pit for x in ("1920", "1792", "128 /")))

# ---- allowed-tools match the calls ---------------------------------------------------------------
import yaml


def fm_of(skill):
    return yaml.safe_load(read(f"plugins/fig/skills/{skill}/SKILL.md").split("---")[1])


def tools_of(skill):
    return [x.strip() for x in fm_of(skill)["allowed-tools"].split(",")]


FIG = "mcp__plugin_figma_figma__"
want = {
    "tokens": ["Bash", "Read"], "read": [FIG + "use_figma"],
    "arrows": ["Skill"], "sync": ["Skill"], "setup": ["Edit", "Skill"], "prep": ["Skill"],
}
gone = {
    "lint": ["mcp__claude_ai_Notion__notion-fetch"], "sync": ["mcp__claude_ai_Notion__notion-fetch"],
    "sketch": [FIG + "get_design_context"], "draw": [FIG + "get_design_context"],
}
miss = [f"{s}:{x}" for s, xs in want.items() for x in xs if x not in tools_of(s)]
extra = [f"{s}:{x}" for s, xs in gone.items() for x in xs if x in tools_of(s)]
check("fig allowed-tools match the calls", not miss and not extra, f"missing {miss}; still listed {extra}")
for rel in ("README.md", "README.ko.md"):
    row = next((l for l in read(rel).splitlines() if "**Notion**" in l and "/fig:prep" in l), "")
    check(f"{rel} Notion row no longer names lint and sync",
          bool(row) and "/fig:lint" not in row and "/fig:sync" not in row, row)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all passed")
