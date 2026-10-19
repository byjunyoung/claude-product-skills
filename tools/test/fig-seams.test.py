#!/usr/bin/env python3
"""Fixtures for where the fig skills meet Figma's official skills and tools.
Reads the repository as it stands (no copy); every case is a plain look at a tracked file.

    python3 tools/test/fig-seams.test.py
"""
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


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
vp = read("plugins/fig/_common/version-pin.md")
check("figma_token_env comment says handoff and sync use it", "handoff" in tl and "sync" in tl, tl)
check("version-pin reads the token through tools.figma_token_env, checks it is set, names the scope",
      "tools.figma_token_env" in vp and "file_versions:read" in vp and "non-empty" in vp
      and "$FIGMA_TOKEN" not in vp)

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
dtc = proto.find("figma:figma-design-to-code", proto.find("## Procedure"))
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

# ---- Task 4: handoff finds its task, or lists the candidates and asks -------------------------------------
ho = read(SK + "handoff/SKILL.md")
ho_tools = [x.strip() for x in tools_line(ho).split(",")]
nt = next((l for l in ho.splitlines() if l.startswith("- **No `task` input")), "")
check("handoff searches the tracker and asks on none or several",
      "mcp__claude_ai_Notion__notion-search" in ho_tools
      and "mcp__plugin_github_github__search_issues" in ho_tools
      and "cannot search the tracker" not in ho
      and "notion-search" in nt and "search_issues" in nt and "task_tracker.ref" in nt
      and "exactly one" in nt.lower() and "never picks" in nt and "read-only" in nt.lower()
      and "before any preview" in nt, nt[:160])

# ---- Task 6: dead deck keys retire; qa says which design it judges against and where its report goes ----
dk = ex.split("\ndeck:", 1)[1].split("\n# ---", 1)[0]
check("retired deck keys are gone from the example",
      not any(k in dk for k in ("template_file", "fidelity:", "batch_size")) and "assets_dir" in dk, dk[:80])
tm = re.search(r"^\s+tasks:\s*\{ type: null, ref: null \}", ex, re.M)
check("qa.baseline.tasks has the {type, ref} shape",
      tm is not None and "markdown | notion | none" in ex[:tm.start()][-900:]
      and "does not read past decisions" in ex[:tm.start()][-900:])
qa = read(SK + "qa/SKILL.md")
qa_tools = [x.strip() for x in tools_line(qa).split(",")]
check("qa report goes to the response or a markdown file",
      "Write" in qa_tools and "qa.report_dir" in qa and "recorded on the ticket" not in qa
      and "as a reply" not in qa and "markdown file" in qa.split("## Delivering the report", 1)[1]
      and re.search(r"^\s+report_dir:\s*null", ex, re.M) is not None
      and "response only" in ex.split("report_dir", 1)[0][-400:])
row = next((l for l in qa.splitlines() if l.startswith("| The design")), "")
check("qa baseline table says the design is read live and the pin is not compared",
      "live file" in row and "not yet compared" in row, row[:120])

# ---- Carried from Tasks 1-3: the skills load what they call -------------------------------------------
check("prep no longer says 'Never all at once'", "Never all at once" not in prep)
check("proto says where it differs from design-to-code",
      "does not re-request" in proto and "get_screenshot" in proto.split("What proto takes from", 1)[1][:1500])
check("code lists Skill", "Skill" in [x.strip() for x in tools_line(code).split(",")])
pg = prep.find("figma:figma-generate-design")
check("prep loads generate-design with figma-use, names both in skillNames, and limits its use",
      pg >= 0 and "skillNames" in prep and "figma-generate-design" in prep.split("skillNames", 1)[1][:200]
      and "component discovery" in prep and "page-level wrapper" in prep
      and pg < prep.find("**Seat check"), f"{pg}")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all passed")
