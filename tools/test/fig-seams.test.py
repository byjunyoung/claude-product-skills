#!/usr/bin/env python3
"""Fixtures for where the fig skills meet Figma's official skills and tools.
Reads the repository as it stands (no copy); every case is a plain look at a tracked file.

    python3 tools/test/fig-seams.test.py
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
    """Tracked text files, minus docs/, the plugins' CHANGELOGs, binaries and this file."""
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


def tools_line(text):
    return text.split("allowed-tools:", 1)[1].split("\n", 1)[0]


SK = "plugins/fig/skills/"

# ---- Task 1: read lists pages through use_figma ----------------------------------------------------
rd = read(SK + "read/SKILL.md")
check("read lists pages with use_figma, not REST",
      "figma.root.children" in rd and "api.figma.com" not in rd and "X-Figma-Token" not in rd
      and "FIGMA_TOKEN" not in rd and "curl" not in rd)
check("read keeps the note that get_metadata alone lists pages incompletely",
      "incomplete page list" in rd)
for rel in ("README.md", "README.ko.md"):
    tok = next((l for l in read(rel).splitlines() if l.startswith("| **") and
                ("personal access token" in l or "개인 액세스 토큰" in l)), "")
    check(f"{rel} token row does not name /fig:read", bool(tok) and "/fig:read" not in tok, tok[:80])
ex = read("plugins/fig/_common/conventions.example.yaml")
tl = next((l for l in ex.splitlines() if l.strip().startswith("figma_token_env:")), "")
check("figma_token_env comment says handoff and sync use it", "handoff" in tl and "sync" in tl, tl)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all passed")
