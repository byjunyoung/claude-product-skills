# Phase 3b — fig removals and merges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/fig:diff` and `/fig:deck-setup` stop existing — handoff writes its line into Notion and GitHub itself, sync judges a page by comparing each working frame with its canonical twin, and deck measures its own template behind a go; one version-pin procedure serves handoff and sync; handoff's writes happen in the order they are previewed; every fig skill's `allowed-tools` and description match what it does, and the description length check fails instead of warning.

**Architecture:** Removals go with the sweep of every name that pointed at them, because `verify.py` fails a reference to a skill that does not exist. Shared procedures become one file under `plugins/fig/_common/` that each skill names. No redirect stubs.

**Tech Stack:** Markdown skill files, Python 3.9 (`tools/verify.py`, `draft-conventions.py`, tests), Node (`check.sh`, `node --test`), bash.

**Spec:** on branch `worktree-local-first-design`:
- `docs/design/2026-10-18-local-first-defaults.md` §6 (deck merge), §8 (remove diff, with decision D1), §9 (descriptions)
- `docs/design/2026-10-18-skill-review.md` S3 (version pin only), S4 (deck pitfalls; `get_design_context` off sketch and draw), S5 (handoff, deck-setup and sync write gates), S6 (fig rows), D1
- Facts at main 3daf4d6, file:line for every item: `/Users/junyoungkim/.claude/jobs/7319b67a/tmp/phase3b-facts.md`

Phase 3c (separate plan): tokens' audit into lint as `[unbound]` (D3), lint's section filter and structured output (S7), S4's draw/prep/code/read alignment, qa against the pinned version (S15), code in prose into scripts (S3), and §11 *Ready for dev* after probe A.

## Global Constraints

- Branch `overhaul-phase3b`, cut at `origin/main` 3daf4d6 (fig 3.28.2, pm 0.39.0). Line numbers below and in the facts file are against 3daf4d6.
- No redirect stubs. `/fig:diff` and `/fig:deck-setup` stop existing in this release; CHANGELOG history is left as written. Both root READMEs and fig's CHANGELOG map them: `/fig:deck-setup → /fig:deck` (it measures the template on its first run), `/fig:diff → none` (Dev Mode's *Compare changes* for looking; no written AS-IS/TO-BE record).
- AS-IS reference sections diff already cloned into files are left alone.
- Every fig `description` ends ≤500 characters (deck ≤700), YAML-parsed, one sentence on what and when, then triggers in both languages.
- `_common/scripts/lib/resolve-config.py` and `preflight.py` stay byte-identical across the plugins; change fig's, `cp` to pm.
- Python 3.9; tests drop every `GIT_*` from subprocess environments; tests never read the real `~/.claude`.
- No team-specific value; documents and comments English; commits Korean `type(scope): …`.
- `bash tools/verify-all.sh` on its own before a push; before every push, `git branch --show-current` and `git log -1` name the branch and commit meant. An implementer never checks out another commit (read old files with `git show <rev>:<path>`).
- Every write outside this repository is preview → go.

## Review Focus

1. **A person types `/fig:diff` or `/fig:deck-setup` after upgrading.** Nothing answers; both READMEs and the CHANGELOG say what replaces each. → Task 1 and Task 5 tests `readmes map the removed names`.
2. **handoff on a Notion or GitHub record** — the line still lands under `ui_section_heading` (Notion: inserted after that heading; GitHub: under that section, or as a comment where there is none). → Task 1 test `handoff owns the notion and github write`.
3. **sync on a page with no AS-IS/TO-BE pair** — the common case once diff is gone: each finished working frame is compared with the canonical frame of the same `[screen]-[state]` name; identical text means applied, any difference is shown as it stands; a working frame with no canonical twin is reported as new. → Task 2 test `sync compares by name, not by pair`.
4. **A team config that still sets `annotation_category`, `scope_tags` or `sync.pair_patterns`.** Nothing reads them; nothing fails on them (the resolver tolerates unknown keys — verify it does, and pin it with a test). → Task 2 test `retired keys are tolerated`.
5. **deck on a machine with no assets.** The first step measures the template behind a preview → go, checks the seat with `whoami`, and the report names the mirror file it created. → Task 5 test `deck measures behind a go`.

---

### Task 1: `/fig:diff` gone; handoff writes into Notion and GitHub itself

**Files:**
- Delete: `plugins/fig/skills/diff/`
- Modify: `plugins/fig/skills/handoff/SKILL.md` (the action table row and Step 4 preview line that say "the method `/fig:diff` uses", facts §2: handoff:65, :129) — handoff now states the method: **notion** inserts the line after the `ui_section_heading` heading (`notion-update-page`, insert after that heading); **github** inserts it under that section of the issue body, or adds a comment where the body has no such section; **markdown** as today; **none** prints. Add the GitHub tools handoff needs to its `allowed-tools` if missing (it has `issue_read`, `add_issue_comment`; editing a body needs `issue_write`).
- Modify every routing line to diff (facts §2): `code:30`, `draw:31, :118, :280` (draw's two category lines become "annotations carry no category"), `handoff:35`, `setup:82` (the list of skills that write — also add `/fig:draw` and `/fig:handoff`, which it omits), `sketch:75`, `sync:26`, `plugins/pm/_common/trackers/README.md:76`, the `task_tracker` comment block in `plugins/fig/_common/conventions.example.yaml` (~215-228), `plugins/fig/README.md:56`, both root READMEs (facts §2 list: Notion/GitHub needs rows, cycle block, mermaid node and edge, skills table, the two paragraphs, repo tree).
- Modify: `plugins/fig/_common/conventions.example.yaml` — remove `task_tracker.annotation_category` and `task_tracker.scope_tags` (only diff read them). `ui_section_heading` and `sync.text_diff_max_len` stay.
- Test: `tools/test/fig-removals.test.py` (new)

**Interfaces:**
- Produces: `tools/test/fig-removals.test.py` with a `check(label, cond, detail)` helper (style of `tools/test/verify.test.py`) and a helper `tracked_text_files()` over `git ls-files` (GIT_* dropped), skipping `docs/`, `plugins/*/CHANGELOG.md`, binaries and the test file. Task 5 adds cases here.

- [ ] **Step 1: Failing tests:**
  - `diff is gone` — `plugins/fig/skills/diff` does not exist; no tracked text file contains `/fig:diff`, except a line that also contains ` → ` (the README map).
  - `retired diff keys gone from the schema` — the fig example config has no `annotation_category` and no `scope_tags`.
  - `handoff owns the notion and github write` — handoff's SKILL.md contains `ui_section_heading`, `add_issue_comment`, and no `/fig:diff`.
  - `readmes map the removed names` (diff part) — `README.md` and `README.ko.md` each contain a line with `/fig:diff →` naming Dev Mode's *Compare changes*.
- [ ] **Step 2: Run** `python3 tools/test/fig-removals.test.py`. Expected: FAIL.
- [ ] **Step 3: Delete, move the write method into handoff, sweep, edit the schema.**
- [ ] **Step 4: Run** `python3 tools/test/fig-removals.test.py && python3 tools/verify.py`. Expected: PASS (verify reports no stale skill reference and every README skills table matches the skill folders).
- [ ] **Step 5: Commit** `refactor(fig): /fig:diff를 없애고 핸드오프가 노션·깃허브 쓰기를 직접 맡는다`

### Task 2: sync judges by name, not by pair (D1); its config write is previewed (S5)

**Files:**
- Modify: `plugins/fig/skills/sync/SKILL.md` — signal 1 (facts §3: :72-79, the trap at :243, the snippet at :164-183 that reads `CFG.sync.pair_patterns`): each finished working frame is compared with the canonical frame of the same `[screen]-[state]` name; identical text means applied; any difference is shown as it stands; a working frame with no canonical twin is "new — not on the canonical page". The section list at :37 drops "comparison-pair patterns". Step 1.6 (:66): recording the convention in `files.<fileKey>` gets a preview naming the file and layer it writes, and asks which layer (the person's own config or the project's) — never a shared team repository without saying so.
- Modify: `plugins/fig/_common/conventions.example.yaml` — remove `sync.pair_patterns` (~186-188).
- Modify: `plugins/fig/_common/scripts/lib/draft-conventions.py:228-241` — stop writing `sync.pair_patterns`; `tools/test/draft-conventions.test.py:78, :170-171` — the non-ASCII case asserts no `pair_patterns` (and that the drafter still runs).
- Modify: `plugins/fig/skills/draw/SKILL.md:220, :264` — the AS-IS section is no longer where before/after lives; reword per D1 ("before and after is the canonical page and the working page").
- Test: `tools/test/fig-removals.test.py`, `tools/test/draft-conventions.test.py`, `tools/test/resolve-config.test.py`

- [ ] **Step 1: Failing tests:**
  - `sync compares by name, not by pair` — sync's SKILL.md contains `[screen]-[state]` in its signal-1 text and no `pair_patterns`.
  - `pair_patterns retired` — no tracked text file outside history names `pair_patterns`; the drafter's non-ASCII case writes no `pair_patterns`.
  - `retired keys are tolerated` (resolve-config.test.py, fig copy) — a project `figma-conventions.yaml` holding `sync: {pair_patterns: {to_be: x}}` and `task_tracker: {annotation_category: y, scope_tags: [z]}` resolves with exit 0.
  - `sync previews its config write` — sync's Step 1.6 text contains `preview` and names the layer choice.
- [ ] **Step 2: Run.** Expected: FAIL (the tolerance case may already pass — keep it as a guard).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the three test files and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(fig): sync가 비교쌍 대신 같은 이름의 정본과 직접 대조하고, 설정 기록 전에 미리보기를 띄운다`

### Task 3: One version-pin procedure (S3)

**Files:**
- Create: `plugins/fig/_common/version-pin.md` — the procedure handoff's Step 3 holds today (facts §5: handoff:89-121): when `handoff.version.enabled` (or sync's `sync.named_version`) is set; why `use_figma` cannot save a version; saving through the web app in the connected browser (*File → Save to version history*), typing non-ASCII names through the clipboard; behind its own preview → go; reading it back through the REST versions call with the 401 fallback (paste the link); handing it to the person when no browser is connected; the pinned link form `…/?node-id={id}&version-id={version id}`.
- Modify: `plugins/fig/skills/handoff/SKILL.md` Step 3 and `plugins/fig/skills/sync/SKILL.md` Step 6 (:132-136) — each names `version-pin.md` instead of describing it. sync's `allowed-tools` gains the browser tools the procedure uses (the same claude-in-chrome set handoff lists), since today it claims a browser it does not have.
- Modify: `plugins/fig/_common/conventions.example.yaml` — the `handoff.version` comment (~203-205, "by hand", with a broken sentence) points at the same procedure and reads as one sentence.
- Test: `tools/test/fig-removals.test.py`

- [ ] **Step 1: Failing test** `one pin procedure` — `version-pin.md` exists; handoff's and sync's SKILL.md each contain `version-pin.md`; the string `api.figma.com/v1/files/{fileKey}/versions` occurs in exactly one tracked file under `plugins/fig` (version-pin.md); sync's `allowed-tools` lists `mcp__claude-in-chrome__navigate`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the test and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `refactor(fig): 버전 고정 절차를 version-pin.md 하나로 모으고 sync가 그 절차를 쓴다`

### Task 4: handoff's writes in the order they are previewed (S5)

**Files:**
- Modify: `plugins/fig/skills/handoff/SKILL.md` — the procedure becomes: 1 gate (`/fig:lint`); 2 choose; 3 **preview the version name → go → save → read it back** (by `version-pin.md`); 4 **preview the doc line → go → write the line**; 5 read back; report. Step 5's "nothing in the Figma file" and the Constraints line (:166) say the same. *Ready for dev* stays "never offered" (§11 is gated on probe A — Phase 3c). `allowed-tools` gains `Skill` (it calls `/fig:lint` through it, :77).
- Test: `tools/test/fig-removals.test.py`

- [ ] **Step 1: Failing test** `handoff previews before each write` — in handoff's SKILL.md, the first occurrence of `go` after the heading of the version step comes before the first occurrence of `save` in that step, and the doc-line step has its own `go` before `append-under`; `allowed-tools` contains `Skill`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Reorder.**
- [ ] **Step 4: Run** the test and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): 핸드오프가 버전 저장과 문서 한 줄을 각각 미리보기와 go 뒤에 쓴다`

### Task 5: `deck-setup` merged into `deck` (§6), with its writes gated (S5) and its pitfalls trimmed (S4)

**Files:**
- Create: `plugins/fig/skills/deck/setup.md` — deck-setup's body (`git mv`), referenced once from deck's SKILL.md. Its writes gain gates: the mirror file (`create_new_file`, facts §1: deck-setup:36-41) and the verification slide builds (:103-117) each wait for a preview → go; the seat is checked with `whoami` first; the closing report names the mirror file it created.
- Create: `plugins/fig/skills/deck/pitfalls.md` — the pitfalls deck keeps (deck:168-242) minus those `figma-use-slides` already states (facts §1: #1–#5, #47 → one pointer each), with numbers read from `template-spec.md` instead of one team's values (deck:94's 0–1920 / 128 / 1792 and similar).
- Modify: `plugins/fig/skills/deck/SKILL.md` — a first step: when `deck.assets_dir` lacks `template-spec.md` or `template.js`, or the person says the template was revised, run `setup.md`. The pitfalls section becomes a pointer to `pitfalls.md`. `deck:15, :140, :187, :246` stop naming deck-setup. Description ≤700, carrying deck-setup's triggers.
- Delete: `plugins/fig/skills/deck-setup/`
- Modify: `plugins/fig/_common/scripts/deck-base.js:5`, `plugins/fig/_common/conventions.example.yaml:234-238` (deck comments), `plugins/fig/README.md:60`, both root READMEs (facts §1 list).
- Test: `tools/test/fig-removals.test.py`

- [ ] **Step 1: Failing tests:**
  - `deck-setup is gone` — the folder is gone; no tracked text file names `deck-setup` outside history, except a line with ` → ` (the README map).
  - `readmes map the removed names` (deck part) — both root READMEs contain `/fig:deck-setup → /fig:deck`.
  - `deck measures behind a go` — `deck/SKILL.md` names `setup.md`; `deck/setup.md` contains `whoami`, and its mirror-file step and its build step each contain `go`; its report names the mirror file.
  - `pitfalls read from the template` — `deck/pitfalls.md` exists and contains none of `1920`, `1792`, `128 /`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Merge, gate, trim, sweep.**
- [ ] **Step 4: Run** the test and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `refactor(fig): deck-setup을 deck에 합치고 템플릿 측정의 쓰기마다 go를 받는다`

### Task 6: `allowed-tools` match what each fig skill calls (S6, S4's last bullet)

**Files:** frontmatter of fig skills (facts §9): tokens `+Bash, +Read`; read `+use_figma`; arrows, sync, setup, prep `+Skill`; setup `+Edit`; lint and sync `−notion-fetch`; sketch and draw `−get_design_context`. Both root READMEs' Notion row (README.md:146) stops naming lint and sync.
- Test: `tools/test/fig-removals.test.py`

- [ ] **Step 1: Failing test** `fig allowed-tools match the calls` — each change above holds when the frontmatters are YAML-parsed.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Edit.**
- [ ] **Step 4: Run** the test and `python3 tools/verify.py`. Expected: PASS (its adapter-tool check still passes).
- [ ] **Step 5: Commit** `fix(fig): 스킬마다 미리 허용하는 도구를 실제로 부르는 것에 맞춘다`

### Task 7: Descriptions in one shape, and the length check fails (§9)

**Files:** every fig skill's `description`; `tools/verify.py:226-238` (the length line moves from `warns` to `fails`; the comment at :26-27 says so); `tools/test/verify.test.py:99-101` (the "long description warns" case now expects a failure) and `:103-108`.

- [ ] **Step 1: Failing tests** — `verify.test.py`: a planted 600-character description fails (exit 1, the same message); the 650-character `pm:task` case still passes under its 700 override. `fig-removals.test.py`: `fig descriptions in one shape` — each fig description ≤500 (deck ≤700) and has exactly one sentence before `Triggers`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Rewrite each description** (detail leaving a description moves into its body where the body lacks it; no trigger is dropped — list any that is) and flip the check.
- [ ] **Step 4: Run** `python3 tools/test/verify.test.py && python3 tools/test/fig-removals.test.py && python3 tools/verify.py`. Expected: PASS with no description WARN anywhere.
- [ ] **Step 5: Commit** `docs(fig): 스킬 설명을 한 문장과 트리거로 줄이고 길이 검사를 실패로 바꾼다`

### Task 8: Release 3b

**Files:** `plugins/fig/.claude-plugin/plugin.json` `3.28.2 → 3.29.0`; `plugins/pm/.claude-plugin/plugin.json` `0.39.0 → 0.39.1` (its trackers README changed in Task 1, and its shared copies if any changed); both CHANGELOGs; `plugins/fig/README.md`; both root READMEs where a removed skill or a changed behaviour is described; re-render any `.github` picture that names a changed skill (facts §11: none names diff, deck or tokens — confirm).

- fig 3.29.0's entry opens with the two removals and what replaces each, then sync's direct comparison and its previewed config write, the one pin procedure, handoff's gate order, deck's measuring step and gates, `allowed-tools`, descriptions, and the retired keys (`annotation_category`, `scope_tags`, `sync.pair_patterns` — nothing reads them; a config that still sets them is not an error).

- [ ] **Step 1–3:** versions, CHANGELOGs, READMEs (English, then Korean); `bash tools/verify-all.sh` on its own → `· PASS`, no WARN.
- [ ] **Step 4: Commit** `chore(release): fig 3.29.0, pm 0.39.1 — /fig:diff와 /fig:deck-setup이 사라지고 핸드오프·sync·deck이 그 몫을 맡는다`
- [ ] **Step 5 (controller):** owner's configs, read-only — resolve with 3.28.2 and the new fig; the differences allowed are the three retired keys no longer read. Callers outside the repository: the team-config repository's `figma-conventions.yaml` (comments at :41-42 naming `/fig:diff`; keys `pair_patterns`, `annotation_category`, `scope_tags` — removable now) and the team's Notion guides (rows for `/fig:diff`, `/fig:deck-setup`, `/fig:tokens`' "lint mode") — previews → go. Push after confirming branch and head; PR preview → go.
