# Phase 3e — what the probes unlocked Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The items 3d left *Gated* are settled by the 2026-10-20 probes: the ones that passed ship (handoff can mark *Ready for dev*, qa compares against the handed-over version), the ones that failed or needed nothing close, and the seams 3c deferred close — setup's `section_style` mixing in nested sections, the bind pinning the change a preview showed, and the instance note telling library instances apart.

**Architecture:** Prose changes to handoff, qa and the shared `_common` procedures, with one new shared procedure (`_common/ready-for-dev.md`) shaped like `version-pin.md`, because both are web-app writes read back through REST. Script changes in `draft-conventions.py`, `token-bind.js` and `audit-tokens.js`. Every behaviour is pinned by a doc test in `tools/test/fig-seams.test.py` or a unit test beside the script (`draft-conventions.test.py`, `token-bind.test.js`, `audit-tokens.test.js`). No new Figma script.

**Tech Stack:** Markdown skills; Python 3.9 tests; Figma REST (`/v1/files/:key/nodes`, `/v1/files/:key/versions`, `/v1/images/:key`); claude-in-chrome for the web-app click.

**Spec:** on branch `worktree-local-first-design`, `docs/design/2026-10-18-skill-review.md`: S5 handoff order (~155-166), S15 (~268-284), D4 (~336-350). 3d's *Gated* list (`docs/superpowers/plans/2026-10-19-phase3d-official-skills-and-seams.md:15-19`).

**Probe record:** the owner's checklist `~/Documents/XYZ/fig_실측_1020/20261020_fig-pm_개편_실측_체크리스트.md`, table 「기록」, run 2026-10-20 on a Full seat (XYZ, pro) with fig 3.31.0. Facts below are from it and from main `1c5e552`.

## What the probes settled

| 3d gated item | Probe result (2026-10-20) | In this plan |
|---|---|---|
| S15 image export by version | `GET /v1/files/{key}/versions` → `GET /v1/images/{key}?ids={node}&version={versionId}&format=png` returns that version's image URL (View-seat token) | Task 2 |
| §11 *Ready for dev* — probe A | Reached, clicked, read back. `?node-id={section}&m=dev` opens Dev Mode with the section selected; the left panel's **Mark as ready for dev** is a DOM button (no canvas coordinates); one click marks it, no confirmation dialog; `GET /v1/files/{key}/nodes?ids={section}` returns `devStatus: {type: "READY_FOR_DEV", description: ""}` at once (absent before). `use_figma` still rejects `devStatus` | Task 1 |
| D4 Code layer | `whoami.code_layers_enabled` is `false` at the top level and on both plans (Full/pro, View/starter) | Closed — the Pages gallery stays proto's default, as D4 already decided. No file changes |
| 3c: library-only token dictionary | All 8 team files have zero local colour variables; on one page 34/34 bound library variables resolved through `getVariableCollectionByIdAsync`, 30/30 aliases followed, the bound-paint fallback unused | Closed — no change |
| 3c: translucent token opacity after a bind | 50% black paint bound to a local `#00000080` token renders 127/255 on white, equal to an unbound 50% swatch (25% renders 191): not multiplied | Closed — no opacity rule in `token-bind.js` |
| 3c: sync's real page switch | With the working page current, 125/125 instances in the canonical frame resolve `getMainComponentAsync()`; `sameMasters: true` is real | Closed — no reordering in `sync-compare.js` |

**Gated — not in this plan until probed:**
- Paint opacity against token alpha when they differ (a 100% paint bound to a 50% token, and the reverse). The probe above had both at 50%, so it cannot say which wins. It decides whether `token-bind.js`'s accepted `opacity 100% → 50%` change shows what the screen will do.
- Dev Mode *Completed* for `/fig:sync`. Probe A covered *Ready for dev* only; sync:159 keeps saying *Completed* is not set.

**Found during the probes — not planned unless the owner adds it:** `sync-compare.js` collects every FRAME in a section, so `[label] A --> B` pills come back as `new — not on the canonical page` (17 of 57 entries on one queue page). The `<scaffolding>` block already names them.

**Deferred by 3c, now planned** (the 3c PR's deferred list, quoted in the 3d session's record): setup's `section_style` mixing in nested sections → Task 3; pinning the change value an accepted entry was shown → Task 4; the instance note counting library instances too ("a note only, no effect on the verdict") → Task 5.

**Open — needs the owner:**
- Task 1 contradicts the owner's 2026-10-08 rule that a handover ends at the named version, the ticket's link and Plan-Ready, with *Ready for dev* kept out of the procedure (the reason then: no tool could set it). The checklist's own rule says §11 ships when probe A passes. The plan therefore ships it **off by default**; confirm, or drop Task 1.
- Accepting a visible change per paint rather than per node (the other half of 3c's deferred tokens item). Today the person accepts node by node and the dry run pins the entry to the paints it showed on those nodes, so a node whose fill and stroke both change is accepted as one. Recommendation: keep per node — a second question per node costs more than it saves unless nodes with two differing changes turn out to be common. Not planned.

## Global Constraints

- Repo `CLAUDE.md`: CHANGELOG + version together (fig 3.32.0; pm untouched, no pm bump); both root READMEs, English first; a config key a doc names exists in `conventions.example.yaml`; rules in their general shape; no skill count in prose.
- A default that ships off stays off in every README sentence that names it.
- Descriptions one sentence + triggers, ≤500. `bash tools/verify-all.sh` ends `· PASS`, no WARN.
- Tests that run git drop every `GIT_*` variable. Python 3.9.
- Every web-app write keeps version-pin's shape: preview → go → act → read back through REST; no browser or the wrong account → hand it back, never claim it was done.

## Review Focus

1. **`handoff.ready_for_dev: true` with no browser connected, or signed in as another account** — nothing is marked; the report says where to click and the section stays unmarked in the report. Test: Task 1.
2. **A section that is already *Ready for dev*** — no click (the button is absent and the canvas shows the badge); reported as already marked. Test: Task 1.
3. **A handover that stops before its doc line** (version pin failed, token missing, no go) — nothing is marked, because the mark comes last. Test: Task 1.
4. **qa where the last handover line has no `version-id`** (pinning off) — qa reads the live file and the report says the design was judged as it stands now. Test: Task 2.
5. **qa with no token, or a frame id absent at the pinned version** — that frame (or every frame, with no token) falls back to the live file, named in the report; QA carries on. Test: Task 2.

---

### Task 1: handoff marks *Ready for dev* last, where a team switches it on (§11)

**Files:**
- Create: `plugins/fig/_common/ready-for-dev.md` — why the web app; steps; read back; never. Same headings as `version-pin.md`
- Modify: `plugins/fig/skills/handoff/SKILL.md` — :3 description; :23 the "never offered" paragraph; step 4 (:99-125) preview and order; :144 report line; :150 and :154 constraints
- Modify: `plugins/fig/_common/conventions.example.yaml` :197-199 comment and the `handoff` block (:200) — new key
- Modify: both root READMEs where handoff's writes and "never a Dev Mode status" are described; *What each skill needs* — handoff's `allowed-tools` already carries the claude-in-chrome tools for the version pin (:4), so only the row's wording changes: the browser now also marks the status where it is switched on
- Test: `tools/test/fig-seams.test.py`

**Interfaces:**
- Produces: config key `handoff.ready_for_dev: false` (boolean). A new name on purpose: the `handoff.dev_status` retired in 3.26.0 may still sit in old configs, and must not switch this on.
- Produces: `_common/ready-for-dev.md`, read by handoff step 4 only.

**Decisions:**
- Off by default, because marking notifies developers and the 2026-10-08 team rule ends a handover without it (see *Open*).
- Order (S5): one preview for the doc line **and** the mark → go → write the line → read it back → mark each section → read each back. The mark is last; any earlier stop marks nothing.
- The click: open `https://www.figma.com/design/{fileKey}/?node-id={section id, : → -}&m=dev`, find the button by its label "Mark as ready for dev", click it. A section showing the *Ready for dev* badge and no button is already marked: skip it and say so.
- Read back: `GET /v1/files/{fileKey}/nodes?ids={section id}` and require `nodes[id].document.devStatus.type == "READY_FOR_DEV"`. The token is resolved the way `version-pin.md` step 4 does (`tools.figma_token_env`, checked non-empty before the call); the doc names the endpoint and says the token's scopes must allow reading file nodes — confirm the scope name against Figma's REST docs when writing it, since the probe token's scopes were not listed.
- `use_figma` is still never used for the status (`"devStatus" is not a supported API`, re-checked 2026-10-20). handoff:23 keeps that fact and drops the conclusion that no tool can set it.

- [ ] **Step 1: Failing tests** — `handoff ready_for_dev ships off`: `conventions.example.yaml` has `ready_for_dev: false` under `handoff`; no sentence in handoff says "never offered". `handoff marks last`: in step 4 the mark follows "write the line" and "Read back". `ready-for-dev.md names its route`: contains `m=dev`, `Mark as ready for dev`, `devStatus`, `READY_FOR_DEV`, `tools.figma_token_env`, and a hand-back sentence for no browser / wrong account. `already marked is skipped`: the skip sentence present. `sync still leaves Completed`: sync:159 unchanged.
- [ ] **Step 2: Run** `python3 tools/test/fig-seams.test.py`. Expected: FAIL.
- [ ] **Step 3: Write** `ready-for-dev.md`; edit handoff, the config comment and key, both READMEs.
- [ ] **Step 4: Run** tests and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(fig): handoff가 켜 둔 팀에서만 웹 앱으로 Ready for dev를 맨 마지막에 표시하고 REST로 되읽는다`

### Task 2: qa compares against the version the handover pinned (S15)

**Files:**
- Modify: `plugins/fig/_common/version-pin.md` — new section *Reading a pinned version as an image (qa)* after *The pinned link*; its first line under the title says qa uses it too
- Modify: `plugins/fig/skills/qa/SKILL.md` — :82 baseline row; step 2's design reading; the report header's baseline line (~:181)
- Modify: `plugins/fig/_common/conventions.example.yaml` `tools.figma_token_env` comment (:280) — qa reads with it too
- Modify: both root READMEs' token row (names handoff and sync today) and qa's row in *What each skill needs*
- Test: `tools/test/fig-seams.test.py`

**Interfaces:**
- Consumes: the handover line format from handoff step 4 — section links carrying `&version-id={id}`, oldest to newest under `task_tracker.ui_section_heading`.

**Decisions:**
- Where the line comes from: the task record qa already reads (`qa.baseline.tasks`, or pm's record through `borrow-pm.py`). The **last** handover line under the design heading wins, as pm publish reads it (3d Task 5).
- Image: for each frame qa would have read live, `GET /v1/images/{fileKey}?ids={frame id}&version={version id}&format=png`, then download the returned URL. A `null` image for an id (the frame did not exist at that version) falls back to the live frame for that id only.
- No `version-id` in the line, no line at all, or no token → the live file, and the report's baseline line says which and that the design was judged as it stands now. QA never stops on this.
- qa:82 drops "not yet compared"; the CHANGELOG entry replaces the 3.31.0 pointer.

- [ ] **Step 1: Failing tests** — `qa reads the pinned version`: qa names `version-pin.md` and the last handover line; qa:82 no longer says "not yet compared". `version-pin has the image read`: contains `/v1/images/` and `version=`. `qa falls back and says so`: the three fall-back cases and the per-frame `null` case each have a sentence. `token row names qa`: both READMEs' token row name `/fig:qa`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Edit.**
- [ ] **Step 4: Run** + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `feat(fig): qa가 넘김 줄이 고정한 버전의 이미지와 비교하고, 못 찾으면 지금 파일로 보고 그렇다고 말한다`

### Task 3: setup drafts `section_style` from top-level sections only

**Files:**
- Modify: `plugins/fig/_common/scripts/lib/draft-conventions.py:159` — `S` keeps `depth == 0`, as `secnames` does at :98
- Test: `tools/test/draft-conventions.test.py`

**Decision:** A nested section is grouping inside a section, often painted differently or not at all; counted alongside the top level it dilutes the mode below `DOMINANCE` (0.6, :24), or wins where nesting is common, and `/fig:prep` then paints new top-level sections with the inner style. Naming already ignores depth > 0 for the same reason. Exclusion candidates keep reading every depth (:232).

- [ ] **Step 1: Failing test** — `nested sections do not vote on section_style`: probes with three depth-0 sections filled `#8306FF` at 0.04 and five depth-1 sections filled `#FFFFFF` at 1 (today the inner style wins 5/8 ≥ 0.6; three keeps the top level at `MIN_SUPPORT`, :23) → the drafted `section_style.fill` is `#8306FF` and `fill_opacity` 0.04.
- [ ] **Step 2: Run** `python3 tools/test/draft-conventions.test.py`. Expected: FAIL.
- [ ] **Step 3: Filter** `S` to `s.get("depth", 0) == 0`, with a comment pointing at :98.
- [ ] **Step 4: Run** + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): setup 초안의 섹션 스타일을 맨 위 섹션으로만 관찰한다`

### Task 4: an accepted change binds only while the token still renders what the preview showed

**Files:**
- Modify: `plugins/fig/_common/scripts/token-bind.js` — the dry run's `mapping` (accepted entries' `paints`) and the real run's accepted-entry check
- Modify: `plugins/fig/skills/tokens/SKILL.md` step 3.4 and *Verify* — the sentence "binds only … with the accepted change the preview showed there" becomes enforced, and says what happens when the token moved
- Test: `tools/test/token-bind.test.js`

**Interfaces:**
- Produces: accepted entries' `paints: [{ node, prop, index, expect }]`. `expect` is the colour key `renderedOn` read for that paint in the dry run (`"#RRGGBB"` / `"#RRGGBBAA"`), or `null` where the token was `unchecked` and nothing could be read.

**Decisions:**
- Real run, accepted paint with `expect` set: bind only if `renderedOn(v, n) === expect`; otherwise the candidate is a `skip` with reason `token {name} now renders {rk} here; the preview showed {expect} — run the dry run again` and its `change`, and the paint goes on to its next candidate, as an import failure does today.
- `expect: null` keeps today's behaviour for a token no dry run could read (it binds, and `changed` names the change). The SKILL says this is the one case the pin cannot cover.
- A real run whose accepted `paints` lack the `expect` key altogether throws before anything is written, as one without `paints` does: the mapping must come from a dry run of this version.

- [ ] **Step 1: Failing tests** — `accepted change is pinned to the previewed value`: paint `#000000`, token `#00000080` accepted in the dry run (`expect: "#00000080"`); the token's value set to `#00000066` before the real run → `bound` 0, one `skipped` row naming both values. `unchanged token still binds`: same, value unchanged → `bound` 1, `changed` has the row. `expect key required on a real run`: accepted paints without `expect` → throws, nothing written.
- [ ] **Step 2: Run** `node --test tools/test/token-bind.test.js`. Expected: FAIL.
- [ ] **Step 3: Implement** in `token-bind.js`; edit the SKILL sentences.
- [ ] **Step 4: Run** + `bash plugins/fig/_common/scripts/lib/check.sh` + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): 승인한 색 변화는 미리보기 때 값 그대로일 때만 묶고, 토큰이 바뀌었으면 건너뛰고 알린다`

### Task 5: the instance note tells this file's components from library ones

**Files:**
- Modify: `plugins/fig/_common/scripts/audit-tokens.js` — the audit note and collect's `inInstance`
- Modify: `plugins/fig/skills/lint/SKILL.md` (D's *Not read* paragraph and *Running it*'s note description), `plugins/fig/skills/tokens/SKILL.md` (`inInstance` in step 1)
- Test: `tools/test/audit-tokens.test.js`

**Interfaces:**
- Produces: `inInstance: [{ hex, count, source }]`, `source` `"local"` or `"library"`; the audit note in two halves, each left out at zero.

**Decisions:**
- For each colour the walk passes up as `"instance"`, find its outermost INSTANCE ancestor through `parent` in `audit-tokens.js` itself — the shared `<paint-scope>` block stays byte-identical. After the walk, `await getMainComponentAsync()` once per distinct outermost instance; `remote === true` is library.
- Note wording: `{a} hand-typed colours sit inside instances of this file's components — run lint on {page names}` and `{b} sit inside library components — fix them in the library that publishes them`. The page names come from the master's PAGE ancestor. Neither half changes `pass` or a count.
- On BarisON `[UI] 🤖 운영관리` (2026-10-20) the note read "461 … run lint on the page that holds their masters" for a file with no local colour tokens, so most of it pointed at a page that is not in the file (inference — not split then).

- [ ] **Step 1: Failing tests** — `instance note splits local and library`: one instance of a local master on page `Components` holding 2 hand-typed colours, one of a remote master holding 3 → the note has both halves with 2, `Components`, and 3; `pass` unchanged. `library-only note`: only the remote instance → the local half absent. `inInstance carries source`.
- [ ] **Step 2: Run** `node --test tools/test/audit-tokens.test.js`. Expected: FAIL.
- [ ] **Step 3: Implement**; edit both SKILLs.
- [ ] **Step 4: Run** + check.sh + verify.py. Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): 인스턴스 안 색 안내가 이 파일 컴포넌트와 라이브러리 컴포넌트를 나눠 센다`

### Task 6: Release fig 3.32.0

**Files:** `plugins/fig/.claude-plugin/plugin.json` 3.31.0 → 3.32.0, `plugins/fig/CHANGELOG.md`, `plugins/fig/README.md`, both root READMEs.

- [ ] **Step 1:** Version + CHANGELOG. Opens with what a designer sees: qa judges against the handed-over version; handoff can mark *Ready for dev* where a team switches it on (off by default); setup's drafted section style ignores nested sections; an accepted colour change binds only while the token still renders what the preview showed; lint's instance note says which colours belong to a library. One line records the probes that closed D4 and 3c's three live checks with no change.
- [ ] **Step 2:** README sweep, English then Korean — the off default stated wherever handoff's writes are listed.
- [ ] **Step 3:** `bash tools/verify-all.sh` → `· PASS`, no WARN.
- [ ] **Step 4: Commit** `chore(release): fig 3.32.0 — qa가 넘긴 버전과 비교하고, handoff가 켜 둔 팀에서 Ready for dev를 표시한다`. The controller pushes, previews the PR, waits for go.
