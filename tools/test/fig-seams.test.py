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

# ---- Task 2: draw and prep name what they take from generate-design; prep's batching has a reason ----
draw = read(SK + "draw/SKILL.md")
prep = read(SK + "prep/SKILL.md")
used = next((l for l in draw.splitlines() if "What draw takes from" in l), "")
used_part, _, not_part = used.partition("What it does not take")
check("draw names generate-design's parts used and not used",
      "component discovery" in used_part and "existing screen" in used_part
      and "wrapper" in not_part and "html_to_figma" in not_part
      and "canonical screen" in not_part and "html_to_figma" not in used_part
      and draw.count("html_to_figma") == 1, used[:120])
check("draw names both skills in mutating calls",
      "skillNames" in draw and "figma-generate-design" in draw.split("skillNames", 1)[1][:200]
      and "before the first mutating" in draw.lower())
bat = next((l for l in prep.splitlines() if "safe retry" in l or "retry-safe" in l), "")
check("prep's batching states retry safety, not a count",
      bool(bat) and "orphan" in bat and "absorb" in bat and "rename" in bat.lower()
      and "ten operations" not in prep and not re.search(r"≤\s*10|no more than ten", prep, re.I), bat[:120])

# ---- Task 3: code, proto and deck obey the official skills' MUST lines ----------------------------------
code = read(SK + "code/SKILL.md")
check("code pulls assets through get_design_context",
      "download_assets" not in code and "get_design_context` response" in code)
proto = read(SK + "proto/SKILL.md")
dtc = proto.find("figma:figma-design-to-code")
gdc = proto.find("get_design_context", proto.find("## Procedure"))
check("proto loads design-to-code before get_design_context",
      "Skill" in [x.strip() for x in tools_line(proto).split(",")] and 0 <= dtc < gdc, f"{dtc} vs {gdc}")
deck = read(SK + "deck/SKILL.md")
setup = read(SK + "deck/setup.md")
check("deck lists Skill", "Skill" in [x.strip() for x in tools_line(deck).split(",")])
for name, text in (("SKILL.md", deck), ("setup.md", setup)):
    calls = [m.start() for m in re.finditer(r"`create_new_file`(?:, editorType| \(editorType)", text)]
    skill = text.find("figma:figma-create-new-file")
    check(f"deck {name} loads create-new-file before create_new_file",
          bool(calls) and 0 <= skill < calls[0] and "default light theme" in text, f"{skill} vs {calls}")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all passed")
