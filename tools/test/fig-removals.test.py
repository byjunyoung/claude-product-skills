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


def fm_of_text(text):
    import yaml
    return yaml.safe_load(text.split("---")[1])


# ---- /fig:diff -----------------------------------------------------------------------------------
check("diff skill folder is gone", not (REPO / "plugins/fig/skills/diff").exists())

MAP_FILES = ("README.md", "README.ko.md")


def stale_lines(files, name, map_start):
    """Lines naming a retired skill. The one exemption is the map line of the two root READMEs."""
    return [f"{rel}:{n}" for rel, text in files
            for n, line in enumerate(text.splitlines(), 1)
            if name in line and not (rel in MAP_FILES and line.startswith(map_start))]


DIFF_MAP, SETUP_MAP = "`/fig:diff` → (", "`/fig:deck-setup` → `/fig:deck`"
check("the map-line exemption covers the root READMEs' map lines only",
      stale_lines([("plugins/fig/skills/x/SKILL.md", DIFF_MAP + "removed — …)")], "/fig:diff", DIFF_MAP)
      and stale_lines([("plugins/fig/README.md", SETUP_MAP + " (…)")], "deck-setup", SETUP_MAP)
      and not stale_lines([("README.md", DIFF_MAP + "removed — …)")], "/fig:diff", DIFF_MAP))
stale = stale_lines(tracked_text_files(), "/fig:diff", DIFF_MAP)
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
check("sync's config write shows the block and edits in place",
      "files.<fileKey>" in step16 and "`Edit`" in step16 and "never a whole-file rewrite" in step16)

# Which side a difference sits on decides the bucket (review D1): working-only text missing from
# canonical is not applied; text only canonical has may be later work there, so it is needs checking.
def section_of(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0] if start in text else ""


def row(table, bucket):
    return next((l for l in table.splitlines() if l.startswith(f"| {bucket} |")), "")


buckets = section_of(sync, "**The result has exactly three buckets**", "### Step 3")
applied, not_applied, needs = row(buckets, "Applied"), row(buckets, "Not applied"), row(buckets, "Needs checking")
check("Applied needs all three signals to agree",
      bool(applied) and all(s in applied for s in ("signal 1", "signal 2", "signal 3")))
check("canonical-only text alone is needs checking, never not applied",
      "canonical-only" in needs and "may be later work" in needs and "canonical-only" not in not_applied.split("—")[0])
check("a mixed frame lists its canonical-only strings to confirm",
      "may be later work — confirm" in not_applied)
check("the stale identical-means-needs-checking row is gone",
      "text is identical and heights match" not in sync)
canon_only = next((l for l in sig1.splitlines() if "only in the canonical frame" in l), "")
check("signal 1: the canonical-only bullet grades needs checking",
      "Needs checking" in canon_only and "Not applied" not in canon_only, canon_only)
step3 = section_of(sync, "### Step 3", "### Step 4")
check("step 3's preview lists every canonical-only string the apply would remove",
      "may be later work — confirm" in step3 and "archive" in step3 and "queue" in step3)
check("a frame differing only in height or master takes the move path in step 3",
      bool(re.search(r"height or (a )?(component )?master[^.\n]*\*\*move", step3, re.I)))
check("step 3's confirm is per frame, and a declined frame stays in its bucket",
      "declined" in step3 and "as a whole" in step3)
report = section_of(sync, "## Reporting", "## Implementation")
check("the report counts declined frames and gives a new frame's before line",
      "declined" in report and "(new screen)" in report and "which the person confirmed" not in report)
# Every string is compared; the length key only shortens how a long one is shown
check("signal 1 compares every string whatever its length",
      not re.search(r"length\s*<\s*CFG\.sync\.text_diff_max_len", sync) and "whatever its length" in sig1)
ex_cfg = next((l for l in read("plugins/fig/_common/conventions.example.yaml").splitlines()
               if l.strip().startswith("text_diff_max_len:")), "")
check("the example config says text_diff_max_len only shortens display",
      "not used as diff keys" not in ex_cfg and "compared" in ex_cfg and "…" in ex_cfg, ex_cfg)
step4 = section_of(sync, "### Step 4", "### Step 5")
unseen = "not detected by any signal"
check("report and archive preview both say a visual-only change goes unseen",
      unseen in section_of(sync, "## Reporting", "## Implementation") and unseen in step4)

# The name test is the file's own pattern, and null means exact names
snippet = section_of(sync, "**Name-matched text comparison", "**Finding the keywords")
check("sync tests names with naming.frame_pattern, not a hardcoded shape",
      "frame_pattern" in snippet and "\\S-\\S" not in sync and "naming.frame_pattern" in sig1)
check("null frame_pattern matches by exact name", "exact" in sig1 and "null" in sig1)
check("sync's snippet skips excluded sections on both pages", "exclude_sections" in snippet)

draw = read("plugins/fig/skills/draw/SKILL.md")
check("draw no longer sends before-and-after to the AS-IS section",
      "AS-IS" not in draw and "canonical page and the working page" in draw)

# ---- one version-pin procedure --------------------------------------------------------------------
check("version-pin.md exists", (REPO / "plugins/fig/_common/version-pin.md").exists())
check("handoff and sync name version-pin.md",
      "version-pin.md" in handoff and "version-pin.md" in sync)
pin = read("plugins/fig/_common/version-pin.md")
readback = section_of(pin, "4. **Read it back**", "## The pinned link")
check("version-pin's no-token branch says what sync does: report the entry unconfirmed",
      "sync" in readback.split("No token", 1)[-1].split("Nothing matches", 1)[0].lower()
      and "could not be confirmed" in readback)
check("version-pin's read-back compares a non-ASCII label after normalising escapes",
      "\\u" in readback and "non-ASCII" in readback)
for rel in ("README.md", "README.ko.md"):
    tok = next((l for l in read(rel).splitlines() if l.startswith("| **") and ("personal access token" in l or "개인 액세스 토큰" in l)), "")
    check(f"{rel} token row names handoff and sync", "/fig:handoff" in tok and "/fig:sync" in tok, tok[:80])
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
g, w = first(r"\bthe go\b", dstep), first(r"\{script\} append-under", dstep)
check("doc-line step has its own go before the write", g is not None and w is not None and g < w)
check("notion write does not lean on a callout",
      "usually behind an empty callout" not in handoff and "whatever block opens the section" in handoff)

# Where the line lands: after the last hand-over line already there, else after the heading and its
# opening block — oldest to newest, the way markdown's append-under reads. Every place that says
# where agrees.
LAST = "after the last hand-over line"
spots = {
    "action table": next((l for l in handoff.splitlines() if l.startswith("| `notion` |") and "Insert" in l), ""),
    "preview": next((l for l in dstep.splitlines() if "where `action` is not `print`" in l), ""),
    "method table": next((l for l in dstep.splitlines() if l.startswith("| `notion` |")), ""),
    "search rule": next((l for l in dstep.splitlines() if "Search for the target section first" in l), ""),
}
off = [k for k, l in spots.items() if LAST not in l]
check("every place handoff says where the line goes agrees: after the last hand-over line", not off, ", ".join(off))
check("handoff's lines read oldest to newest", "oldest to newest" in handoff)
check("handoff without a task input prints the line under notion or github",
      bool(re.search(r"no `task` input.*print", handoff, re.I)))
h_desc = fm_of_text(handoff)["description"]
check("handoff's description says it pins a named version", "named version" in h_desc)

# ---- deck-setup folds into deck --------------------------------------------------------------------
check("deck-setup folder is gone", not (REPO / "plugins/fig/skills/deck-setup").exists())
stale = stale_lines(tracked_text_files(), "deck-setup", SETUP_MAP)
check("no tracked file names deck-setup (outside history and the README map)", not stale, ", ".join(stale))
for rel in ("README.md", "README.ko.md"):
    check(f"{rel} maps deck-setup to deck", "`/fig:deck-setup` → `/fig:deck`" in read(rel))

deck_dir = "plugins/fig/skills/deck/"
deck = read(deck_dir + "SKILL.md")
check("deck names setup.md and pitfalls.md", "setup.md" in deck and "pitfalls.md" in deck)
setup = read(deck_dir + "setup.md") if (REPO / (deck_dir + "setup.md")).exists() else ""
mirror = setup.split("## 1.", 1)[1].split("## 2.", 1)[0] if "## 1." in setup else ""
build = setup.split("## 5.", 1)[1] if "## 5." in setup else ""
w, c = first(r"whoami", mirror), first(r"create_new_file", mirror)
check("setup checks the seat with whoami before the mirror file",
      None not in (w, c) and w < c, f"whoami at {w}, create_new_file at {c}")
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
# Every trigger deck-setup answered to (as of 3daf4d6), except its own retired name, now reaches deck
SETUP_TRIGGERS = ("extract the slide template", "set up the deck assets", "덱 템플릿 뽑아줘",
                  "발표 템플릿 추출", "템플릿 다시 추출")
lost = [t for t in SETUP_TRIGGERS if dm and f'"{t}"' not in dm.group(1)]
check("deck's description carries every deck-setup trigger", not lost, ", ".join(lost))

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
    "arrows": ["Skill"], "sync": ["Skill", "Edit"], "setup": ["Edit", "Skill"], "prep": ["Skill"],
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

# ---- sentences that have to stay true ----------------------------------------------------------------
# Compare changes is offered as diff's replacement, so wherever it is, its limits are said beside it
limits = []
for rel in ("README.md", "README.ko.md"):
    for l in read(rel).splitlines():
        if "Compare changes" in l and not ("Dev Mode seat" in l or "Dev Mode 좌석" in l):
            limits.append(rel)
for sk in ("code", "draw", "handoff", "sync", "sketch"):
    for l in read(f"plugins/fig/skills/{sk}/SKILL.md").splitlines():
        if "Compare changes" in l and "->" not in l and "Dev Mode seat" not in l:
            limits.append(sk)
check("every offer of Compare changes says it needs a Dev Mode seat and compares one frame's history",
      not limits and "Dev Mode seat" in read("plugins/fig/skills/sketch/SKILL.md"), ", ".join(limits))
check("CLAUDE.md says a long description fails", "reported as a warning" not in read("CLAUDE.md"))
seat = read("plugins/fig/skills/setup/SKILL.md").split("The seat is not visible", 1)[-1].split("\n- ", 1)[0]
check("setup does not claim handoff checks the seat with whoami",
      not re.search(r"`/fig:handoff`[^—]*— check it themselves with `whoami`", seat), seat[:200])
for rel in ("README.md", "README.ko.md"):
    t = read(rel)
    check(f"{rel} gives the deck assets default and the shared-folder option",
          "`./deck-assets`" in t and "deck.assets_dir" in t
          and all("deck.assets_dir" in l for l in t.splitlines() if "~/.claude/deck-assets" in l))
check("README names the Chrome row rather than counting it",
      "The first Chrome row" not in read("README.md") and "첫 Chrome 줄" not in read("README.ko.md"))

# ---- tokens binds; /fig:lint checks colours ---------------------------------------------------------
tokens = read("plugins/fig/skills/tokens/SKILL.md")
check('tokens/SKILL.md has no "lint mode" and no js block',
      "lint mode" not in tokens.lower() and "check-only" not in tokens.lower() and "```js" not in tokens)
check("tokens scans, binds and verifies through the scripts",
      all(s in tokens for s in ("audit-tokens.js", "token-bind.js", 'MODE = "collect"', "acceptAlpha", "inInstance")))
t_head = fm_of_text(tokens)["description"].partition(" Triggers - ")[0]
check("tokens' description says it binds, not that it audits",
      "binds" in t_head.lower() and "audit" not in t_head.lower(), t_head)
# Every trigger tokens answered to before it stopped checking (as of 181711b) still reaches it
TOKENS_TRIGGERS = ("/fig:tokens", "check the token bindings", "find unbound colors",
                   "토큰 바인딩 검수", "하드코딩 색상 검사", "디자인시스템 연동 점검")
t_desc = fm_of_text(tokens)["description"]
lost = [x for x in TOKENS_TRIGGERS if f'"{x}"' not in t_desc]
check("tokens' description keeps every trigger it had", not lost, ", ".join(lost))

draw = read("plugins/fig/skills/draw/SKILL.md")
step9 = section_of(draw, "### 9. Verify", "\n## ")
check("draw step 9 no longer calls /fig:tokens",
      bool(step9) and "[unbound]" in step9 and not re.search(r"[Cc]all `/fig:tokens`", step9)
      and "check-only" not in draw and "/fig:tokens` after every run" not in draw)
check("draw's report gates on lint alone", "[gates]      lint · tokens" not in draw)
for rel in ("README.md", "README.ko.md"):
    t = read(rel)
    check(f"{rel}: tokens is a repair lint routes to, not a step before it",
          "arrows --> tokens" not in t and "arrows --> lint" in t and "--> tokens --> lint" in t)
    check(f"{rel}: the tree lists both colour scripts", "audit-tokens.js" in t and "token-bind.js" in t)

# ---- descriptions in one shape ---------------------------------------------------------------------
import glob
for f in sorted(glob.glob(str(REPO / "plugins/fig/skills/*/SKILL.md"))):
    sk = Path(f).parent.name
    desc = yaml.safe_load(Path(f).read_text(encoding="utf-8").split("---")[1])["description"]
    limit = 700 if sk == "deck" else 500
    head, sep, rest = desc.partition(" Triggers - ")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", head.strip()) if s]
    ok = bool(sep) and len(desc) <= limit and len(sentences) == 1 and head.rstrip().endswith(".") \
        and rest.startswith('"/fig:' + sk + '"')
    check(f"fig descriptions in one shape: {sk}", ok,
          f"{len(desc)} chars (limit {limit}), {len(sentences)} sentences before Triggers")
    # The CHANGELOG says every description says what the skill does and when
    check(f"{sk}'s description says when, not only what",
          bool(re.search(r"\b(when|whenever|before|after|once)\b", head)), head)
    if sk == "deck":
        check("deck's description does not glue setup's job on with ', and'", ", and it measures" not in head, head)
    if sk in ("handoff", "code", "sync", "arrows"):   # the ones a review found running on clause after clause
        check(f"{sk}'s description reads as one sentence, not a chain of clauses", head.count(",") <= 3, head)

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("all passed")
