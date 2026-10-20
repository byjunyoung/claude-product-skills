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
check("qa baseline table points at the pinned version, with the live file as the fall-back (3e)",
      "version-id" in row and "live file" in row and "not yet compared" not in row, row[:120])

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

# ---- 3e Task 1: handoff marks Ready for dev last, where a team switches it on (§11) -----------------------
RFD = REPO / "plugins/fig/_common/ready-for-dev.md"
rfd = RFD.read_text(encoding="utf-8") if RFD.exists() else ""
hb = ex.split("\nhandoff:", 1)[1].split("\n# ---", 1)[0]
check("handoff ready_for_dev ships off",
      re.search(r"^\s+ready_for_dev:\s*false\b", hb, re.M) is not None
      and "never offered" not in ho and "is not set by any skill" not in ex)
h5, h6 = ho.find("### 5. Read back"), ho.find("### 6. Mark Ready for dev")
s6 = ho[h6:].split("\n## ", 1)[0] if h6 >= 0 else ""
check("handoff marks Ready for dev last, after the line is written and read back",
      0 <= h5 < h6 and "ready-for-dev.md" in s6 and "handoff.ready_for_dev" in s6, f"{h5} {h6}")
s4 = ho.split("### 4.", 1)[1].split("### 5.", 1)[0]
check("handoff's line preview names the mark where it is switched on",
      "handoff.ready_for_dev" in s4 and "Ready for dev" in s4)
check("ready-for-dev.md names its route and its read-back",
      all(k in rfd for k in ("m=dev", "Mark as ready for dev", "devStatus", "READY_FOR_DEV",
                              "tools.figma_token_env", "/v1/files/")), rfd[:80])
check("ready-for-dev.md hands it back with no browser or the wrong account",
      "hand it back" in rfd and "wrong" in rfd)
rfd1 = " ".join(rfd.split())   # prose wraps mid-sentence; judge sentences, not lines
check("an already-marked section is skipped, not clicked again",
      re.search(r"already[^.]*Ready for dev[^.]*skip|skip[^.]*already[^.]*Ready for dev", rfd1, re.I) is not None)
check("nothing is marked when the run stops before the line",
      "marks nothing" in s6 or "nothing is marked" in s6.lower())
check("sync still leaves Completed unset",
      "Dev Mode status (*Completed*) is not set and not offered" in read(SK + "sync/SKILL.md"))
for rel in ("README.md", "README.ko.md"):
    ch = next((l for l in read(rel).splitlines() if "Claude in Chrome" in l and "/fig:handoff" in l), "")
    check(f"{rel} Chrome row says handoff marks Ready for dev where ready_for_dev is on",
          "handoff.ready_for_dev" in ch and "Ready for dev" in ch, ch[:100])

# ---- 3e Task 2: qa compares against the version the handover pinned (S15) ----------------------------------
qa1 = " ".join(qa.split())
check("qa takes the pinned version from the last hand-over line, through version-pin.md",
      "version-pin.md" in qa and "last hand-over line" in qa1 and "qa.baseline.tasks" in qa)
check("qa falls back to the live file in each named case, and never stops on it",
      all(k in qa1 for k in ("no `version-id`", "no hand-over line", "no token", "comes back `null`",
                              "never stops")), qa1[qa1.find("version-pin.md") - 200:][:300])
head = next((l for l in qa.splitlines() if "baseline documents —" in l), "")
check("qa's report head says which design it judged against", "live file —" in head and "version" in head, head)
vp1 = " ".join(vp.split())
check("version-pin.md reads a pinned version back as an image",
      "## Reading a pinned version as an image" in vp and "/v1/images/" in vp and "version=" in vp
      and "file_content:read" in vp and "/fig:qa" in vp.split("## Steps", 1)[0], vp1[:200])
for rel in ("README.md", "README.ko.md"):
    tok = next((l for l in read(rel).splitlines() if l.startswith("| **") and
                ("personal access token" in l or "개인 액세스 토큰" in l)), "")
    check(f"{rel} token row names /fig:qa", "/fig:qa" in tok, tok[:80])
check("figma_token_env comment names qa", "qa" in tl.split("#", 1)[1], tl)

# ---- 3e final-review fixes ----------------------------------------------------------------------------------
vpimg = " ".join(vp.split("## Reading a pinned version as an image", 1)[-1].split("## Never", 1)[0].split())
check("ready-for-dev and the pinned image read treat any status but 200 alike, 403 named",
      "403" in rfd1 and "anything but a 200" in rfd1.lower() and "403" in vpimg and "anything but a 200" in vpimg.lower(),
      vpimg[-300:])
for rel in ("README.md", "README.ko.md"):
    ls = read(rel).splitlines()
    k = next((i for i, l in enumerate(ls) if "<summary>" in l and "401" in l), None)
    tr = "\n".join(ls[k:k + 6]) if k is not None else ""
    check(f"{rel} token troubleshooting names 403 and /fig:qa", "403" in tr and "/fig:qa" in tr, tr[:120])
check("the Korean lint paragraph has no leftover sentence the English lacks",
      "보고서는 그 색이 몇 개인지 세고 그 페이지를 가리킵니다" not in read("README.ko.md"))
wd = qa1[qa1.find("**Which design.**"):][:1400]
check("qa finds the hand-over line in pm's task file when qa.baseline.tasks is unset",
      "borrow-pm.py task" in wd and "list --dir" in wd and "{heading}" in wd, wd[:200])
for rel, task_file in (("README.md", "task file"), ("README.ko.md", "일감 파일")):
    para = next((l for l in read(rel).splitlines() if l.startswith("`qa`")), "")
    check(f"{rel} qa paragraph says where the hand-over line is read from",
          ("hand-over line" in para or "넘김 줄" in para) and "qa.baseline.tasks" in para and task_file in para, para[:100])
s6n = " ".join(s6.split())
check("handoff decides the print case for Ready for dev",
      "`print`" in s6n and "after the go" in s6n and "`print`" in " ".join(rfd.split("## Never", 1)[1].split()))
tk = " ".join(read(SK + "tokens/SKILL.md").split())
check("tokens says every case the pin cannot cover, not just one",
      "The one case the pin cannot cover" not in tk and "could not read what the token renders" in tk)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all passed")
