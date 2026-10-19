# Phase 3d — official Figma skills and the loose seams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every fig skill that touches Figma's official skills says which parts it uses and which it does not, and obeys their mandatory rules; the seams left open by 3a–3c (handoff finding its task, pm reading the last handover line, dead deck keys, qa's version baseline) close.

**Architecture:** Prose changes to SKILL.md files, judged against the installed official skills (figma plugin 2.2.157 under `~/.claude/plugins/cache/claude-plugins-official/figma/`), each pinned by a doc test in `tools/test/fig-removals.test.py` (or a new `fig-seams.test.py`). One new borrow in `borrow-pm.py` (the last handover line). No new Figma scripts. Nothing that needs a live Edit seat ships here — those items are listed under *Gated* with their probe.

**Tech Stack:** Markdown skills; Python 3.9 tests; the official skills read from the plugin cache (read-only).

**Spec:** on branch `worktree-local-first-design`, `docs/design/2026-10-18-skill-review.md`: S4 (~138-155), S15 (~268-289), D4 (~336-355); skill appendix rows for read, prep, draw, code, deck, proto, qa, handoff.

Facts with file:line at main 749257b: `/Users/junyoungkim/.claude/jobs/7319b67a/tmp/phase3c-facts.md` §4–§7 (read before 3c; 3c touched proto's step 2 and tokens, so find places by text).

**Gated — not in this plan until its probe runs on an Edit/Dev seat (controller does the probe, then a follow-up plan):**
- S15 image export by version through REST (`GET /v1/images/:key?version=`) — unrun. Until then qa compares against the live file and says so.
- D4 Code layer via `figma-code-workflows` / `send_code_to_figma` — needs `whoami.code_layers_enabled` on a Full seat.
- §11 *Ready for dev* — probe A (web click-through).
- 3c's live checks: library-only token dictionary; translucent token opacity after a bind; sync's real page switch.

## Global Constraints

- The official skills are the authority on their own tools: a fig skill never contradicts a line marked MANDATORY/MUST in `figma-use`, `figma-generate-design`, `figma-design-to-code`, `figma-create-new-file`, `figma-use-slides`. Where fig deliberately differs, it says why in one sentence and the reason holds (e.g. a write that must be previewed).
- Repo `CLAUDE.md`: CHANGELOG + version together (fig 3.31.0; pm 0.40.0 only if pm's own files change — Task 5 does); both root READMEs, English first; a config key a doc names exists in `conventions.example.yaml`; rules in their general shape; no skill count in prose.
- Descriptions one sentence + triggers, ≤500. `bash tools/verify-all.sh` ends `· PASS`, no WARN.
- Tests that run git drop every `GIT_*` variable. Python 3.9.

## Review Focus

1. **A person on a View seat running `/fig:read`** — after the REST section goes, page listing must still work from any seat through read-only `use_figma`; a View seat must not be told to mint a token. Test: Task 1.
2. **A draw run that needs a new component** — draw must load `figma-generate-design` and, per figma-use:15, name both skills in every mutating call; it must not create a page-level wrapper when a canonical clone exists. Test: Task 2 (doc test on the exact sentences).
3. **`/fig:handoff` under `notion`/`github` with no `task` input and several candidate tasks** — it must list candidates and ask, never pick one. Test: Task 4.
4. **A pm record with three handover lines** — publish reads the last one and says which. Test: Task 5.
5. **A config still setting `deck.template_file`** — not an error; the key is retired with the others. Test: Task 6.

---

### Task 1: read lists pages through `use_figma`; the personal-token REST section goes (S4.5)

**Files:**
- Modify: `plugins/fig/skills/read/SKILL.md` (~:39-95 token check + REST first choice; ~:171-194 PAT setup; :199)
- Modify: `plugins/fig/_common/conventions.example.yaml` `tools.figma_token_env` comment (~:272) — still used by handoff/sync's version read-back; say so
- Modify: both root READMEs' prerequisites row for the token (names read today)
- Test: `tools/test/fig-seams.test.py` (new; `check` helper copied from fig-removals)

- [ ] **Step 1: Failing tests** — `read lists pages with use_figma, not REST`: read/SKILL.md names `figma.root.children`, does not name `api.figma.com` or `X-Figma-Token`; the README token row does not name `/fig:read`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Rewrite** read's page listing to the `setup:89-96` call (one read-only `use_figma` returning index, id, name per page), drop 1.5 and the PAT setup; keep a one-line note that `get_metadata` alone returns an incomplete page list.
- [ ] **Step 4: Run** tests and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `refactor(fig): read가 개인 토큰 없이 use_figma로 페이지를 나열한다`

### Task 2: draw and prep name what they take from generate-design (S4.1), prep's batching rule states its reason (S4.2)

**Files:**
- Modify: `plugins/fig/skills/draw/SKILL.md` (~:13, :55, :199), `plugins/fig/skills/prep/SKILL.md` (~:15, :127, :194-195)
- Test: `tools/test/fig-seams.test.py`

**Decisions:**
- draw uses from generate-design: component discovery (2a-i Code Connect check, 2a-iii inspect existing screens) and editing an existing screen (:419-430). It does not use: the page-level wrapper frame (:221-249) or `html_to_figma` — because draw clones a canonical screen, so the screen already exists inside its section. One sentence each.
- Per figma-use:15, draw loads `figma:figma-generate-design` before its first mutating call and names both skills in `skillNames` of every mutating call.
- prep keeps its per-step verification but states the reason figma-use allows: calls are sized for safe retry — `clone()`/`createFrame` land on the page and need `absorb`, so a failed batch leaves orphans; renames are font-independent and may batch freely. Drop the bare "≤10 per call" number; keep "a batch is one section's worth".

- [ ] **Step 1: Failing tests** — `draw names generate-design's parts used and not used` (both lists present; "html_to_figma" appears only in the not-used sentence); `draw names both skills in mutating calls`; `prep's batching states retry safety, not a count`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Edit.**
- [ ] **Step 4: Run** + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `docs(fig): draw·prep가 공식 generate-design에서 쓰는 부분과 안 쓰는 부분을 적고, prep 묶음 규칙에 이유를 붙인다`

### Task 3: code, proto and deck obey the official skills' MUST lines (S4.3, S4.6, S4.7)

**Files:**
- Modify: `plugins/fig/skills/code/SKILL.md` (:4 drop `download_assets`; :75 → assets come from the `get_design_context` response as design-to-code:23 requires)
- Modify: `plugins/fig/skills/proto/SKILL.md` (:4 keep `get_design_context`; load `figma:figma-design-to-code` before it, as code:46 does; add `Skill` to allowed-tools)
- Modify: `plugins/fig/skills/deck/SKILL.md` and `deck/setup.md` (add `Skill`; load `figma:figma-create-new-file` before every `create_new_file`, and `figma-use-slides` note about the default light theme after it)
- Test: `tools/test/fig-seams.test.py`

- [ ] **Step 1: Failing tests** — `code pulls assets through get_design_context` (no `download_assets` in frontmatter or body); `proto loads design-to-code before get_design_context`; `deck loads create-new-file before create_new_file` (SKILL.md and setup.md; `Skill` in allowed-tools).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Edit.**
- [ ] **Step 4: Run** + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): code·proto·deck이 공식 Figma 스킬의 필수 규칙을 따른다`

### Task 4: handoff finds its task, or lists the candidates and asks (carried)

**Files:**
- Modify: `plugins/fig/skills/handoff/SKILL.md` (:4 add `mcp__claude_ai_Notion__notion-search`, `mcp__plugin_github_github__search_issues`; :72 the no-`task` branch)
- Modify: both root READMEs' Notion/GitHub rows if they list handoff's tools by name
- Test: `tools/test/fig-seams.test.py`

**Decision:** With no `task` input under `notion` or `github`, handoff searches the tracker named by `task_tracker.ref` for the file's name and the section names (Notion: `notion-search` scoped to the database; GitHub: `search_issues` in the repo). Exactly one hit → it names it in the preview and proceeds to the usual preview → go. None or several → it lists them and asks; it never picks. The search is read-only and happens before any preview.

- [ ] **Step 1: Failing test** — `handoff searches the tracker and asks on none or several` (the sentences; the two tools in allowed-tools; the old "cannot search" sentence gone).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Edit.**
- [ ] **Step 4: Run** + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `feat(fig): handoff가 일감 입력이 없으면 트래커를 찾아보고, 하나가 아니면 묻는다`

### Task 5: pm publish reads the last handover line and says so (carried; pm 0.40.0)

**Files:**
- Modify: `plugins/pm/skills/task/publish.md` (:58, :124, :186, :268, :311, :514 — every "a handover line" / "the handover line")
- Modify: `plugins/pm/_common/scripts/lib/borrow-pm.py` only if it returns the line (check; if it only returns the heading, no change)
- Modify: `plugins/pm/.claude-plugin/plugin.json` 0.39.1 → 0.40.0; `plugins/pm/CHANGELOG.md`
- Test: `tools/test/task-skill.test.py`

**Decision:** All three trackers append handover lines oldest to newest (3b), so publish reads the **last** line under the design heading as the referenced version, and its preview says "referenced version: from the last of N handover lines" when N > 1.

- [ ] **Step 1: Failing test** — `publish reads the last handover line` (sentence present; no bare "a handover line").
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Edit**, bump, CHANGELOG.
- [ ] **Step 4: Run** + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `fix(pm): publish가 넘김 줄이 여럿이면 마지막 줄을 참조 버전으로 읽고 그렇다고 말한다`

### Task 6: dead deck keys retire; qa says which design it judges against (S15 doc part)

**Files:**
- Modify: `plugins/fig/_common/conventions.example.yaml` (remove `deck.template_file`, `deck.fidelity`, `deck.batch_size`; `qa.baseline.tasks: null` → `{ type: null, ref: null }` with the §3 shape comment)
- Modify: `plugins/fig/skills/qa/SKILL.md` (:82 baseline table: "The design — the live file; the pinned version a handover named is not yet compared (see CHANGELOG)"; :205-207 "recorded on the ticket / drafted as a reply" → the report goes to the response or a markdown file under `qa.report_dir` (new key, `null` = response only); drop the two destinations qa has no tools for; :25 stays)
- Modify: `plugins/fig/skills/deck/SKILL.md` if it names any of the three keys (facts: it does not)
- Test: `tools/test/fig-seams.test.py`, `tools/test/resolve-config.test.py` (a config setting the retired keys resolves without error)

- [ ] **Step 1: Failing tests** — `retired deck keys are tolerated`; `qa report goes to the response or a markdown file` (no "on the ticket" / "as a reply" destinations); `qa.baseline.tasks has the {type, ref} shape`.
- [ ] **Step 2: Run.** Expected: FAIL (except tolerance, kept as a guard).
- [ ] **Step 3: Edit.** qa gains `Write` for the markdown report, behind the usual preview → go.
- [ ] **Step 4: Run** + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): deck의 읽지 않는 키 셋을 은퇴시키고, qa 보고는 응답이나 마크다운 파일로만 간다`

### Task 7: Release fig 3.31.0 (pm 0.40.0 from Task 5)

**Files:** `plugins/fig/.claude-plugin/plugin.json`, `plugins/fig/CHANGELOG.md`, `plugins/fig/README.md`, both root READMEs (prerequisites: token row; What each skill needs: handoff's search tools, qa's Write; the retired keys note).

- [ ] **Step 1:** Version + CHANGELOG (opens with: read works from any seat; handoff finds its task; draw/prep/code/proto/deck follow the official skills; the retired keys; qa's report destination).
- [ ] **Step 2:** README sweep, English then Korean.
- [ ] **Step 3:** `bash tools/verify-all.sh` → `· PASS`, no WARN.
- [ ] **Step 4: Commit** `chore(release): fig 3.31.0, pm 0.40.0 — 공식 Figma 스킬을 따르고, read는 좌석을 가리지 않으며, handoff가 일감을 찾는다`. The controller pushes, previews the PR, waits for go.
