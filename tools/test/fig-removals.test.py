#!/usr/bin/env python3
"""Fixtures for the fig skills that were removed or folded into another.
Reads the repository as it stands (no copy); every case is a plain look at a tracked file.

    python3 tools/test/fig-removals.test.py
"""
import os, subprocess, sys
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

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all passed")
