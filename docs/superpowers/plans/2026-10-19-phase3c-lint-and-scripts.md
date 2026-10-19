# Phase 3c — lint and the scripts it runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/fig:lint` grades from the scripts' own structured output, takes one section at a time, and catches unbound colours. Every piece of JavaScript that fig pastes into `use_figma` lives in a checked, tested script instead of in a SKILL.md.

**Architecture:**
- Each audit script returns `{ pass, findings, note? }`, and every finding carries its own grade. lint stops reading grades off message text.
- A new `audit-tokens.js` gives lint its `[unbound]` check, and gives `/fig:tokens` the scan it binds from. tokens keeps binding only.
- The JavaScript still written inline in tokens, sync and proto moves into `_common/scripts/` and gets tests. Each SKILL.md keeps the calling pattern: one config line plus the whole file, pasted into `use_figma`.

**Tech Stack:** Figma plugin JavaScript, run through `use_figma` (top-level `await`/`return`). Node `node:test` for tests, run against fake `figma`/`CFG` globals. Python 3.9 for `tools/verify.py`.

**Spec:** on branch `worktree-local-first-design`, `docs/design/2026-10-18-skill-review.md`:
- S3 "Code in prose → scripts" (~124-136)
- S7 (~186-195)
- D3 (~325-334)

Facts with file:line at main 09e6661: `/Users/junyoungkim/.claude/jobs/7319b67a/tmp/phase3c-facts.md`.

**Not in this plan (Phase 3d):**
- S4's remaining alignment with the official Figma skills: generate-design boundary, prep batching, code `download_assets`, read's REST section, deck `create_new_file`, proto `get_design_context`.
- S15, qa against the handed-over version.
- D4, proto's Code layer.
- handoff searching for a task, and pm publish's "which handover line".
- `deck.template_file`, `fidelity` and `batch_size`.
- §11 *Ready for dev*, which waits on probe A.

## Global Constraints

- Scripts run inside `use_figma`. The caller pastes one `const CFG = {...};` line from `python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --js <fileKey>`, any optional input lines, then the whole file.
  - Scripts may use top-level `await` and `return`.
  - `lib/check.sh` syntax-checks every `*.js` in `_common/scripts`.
- Tests load the script text and run it through `AsyncFunction` against fake `figma`/`CFG` globals, as the existing `tools/test/audit-*.test.js` do. `verify-all.sh` finds new `*.test.js` and `*.test.py` files by itself.
- A pasted helper block shared by several scripts is a byte-identical copy between `// <name>` and `// </name>` markers. `tools/verify.py` compares the copies.
  - This is how S7's "one shared walker" is met: `use_figma` takes one pasted text, so 3.27.0 chose checked copies over a separate file to concatenate.
  - This plan keeps that choice and extends the check.
- Repo `CLAUDE.md`:
  - a CHANGELOG line and a version bump together (fig 3.30.0; pm is untouched, so no pm bump);
  - both root READMEs every time, English first and the Korean the same document;
  - "What `/fig:lint` looks at" changes when a lint check is added;
  - every rule ships in its general shape, and a convention that cannot be assumed ships `null`;
  - no skill count in prose.
- Descriptions are one sentence plus triggers, ≤500 characters. verify now fails a longer one.
- Python 3.9. Any test that starts git drops every `GIT_*` variable from the environment.
- Commits are Korean, `type(scope): what changed, in a sentence`, with a short Korean body and the session trailers.

## Review Focus

1. **A file with no colour tokens at all** (a team without a design system). `[unbound]` must not flag every fill. It returns `pass: true` with a `note` saying the check was skipped, and it emits no findings. Test: Task 5.
2. **A section filter naming a section that is not on the page, or that sits inside an excluded parent.** Neither may come back as a silent PASS.
   - Not found → a blocking `[section]` finding.
   - Excluded → a warning `[section]` finding saying that nothing was audited.
   - Test: Task 2.
3. **A caller still waiting for `STRUCT PASS` / `FLOW PASS` / `COMPONENT PASS`.** After Task 1, no SKILL.md or README tells a reader to look for those strings, except where a document describes the change. Test: Task 1.
4. **Paints that are not plain solid colours** — a gradient, an image, a paint bound through an alias, a mixed fill.
   - None of them is reported as an unbound SOLID.
   - Effect colours (`effects[].color`) are checked the way tokens' prose already promises.
   - Test: Task 5.
5. **The moved sync comparison drifting from what the skill tells the agent to run.** The sync test loads the script file and still passes every case it passes today. Test: Task 7.

---

### Task 1: Audit scripts return graded findings

**Files:**
- Modify: `plugins/fig/_common/scripts/audit-struct.js`, `audit-flow.js`, `audit-component.js`
- Modify: `plugins/fig/skills/lint/SKILL.md` (Running it ~:149-169; the severity section ~:109-135)
- Modify: every SKILL.md or README sentence naming `STRUCT PASS` / `FLOW PASS` / `COMPONENT PASS` (grep)
- Test: `tools/test/audit-struct.test.js`, `audit-flow.test.js`, `audit-component.test.js`; new `tools/test/lint-grades.test.js`

**Interfaces:**
- Produces:
  - `Finding = { tag: string, grade: "blocking" | "warning", node: string | null, msg: string }`. `tag` is the bracketed tag as emitted today, e.g. `"[arrow]"`. `node` is the offending node's id, where there is one.
  - `AuditResult = { pass: boolean, findings: Finding[], note?: string }`, where `pass === findings.length === 0`.
  - audit-struct.js and audit-flow.js return an `AuditResult`.
  - audit-component.js:
    - `MODE = "collect"` keeps its stats object;
    - `MODE = "compare"` returns an `AuditResult`, and the old `unknown` entries become `{ tag: "[unknown]", grade: "warning" }` findings.
  - Grades are lint's table today (lint ~:113-135), now decided in the scripts:
    - `[arrow]` and `[state]` are blocking only for *orphan* and *passes through*. Every geometry finding (edge offset, target gap, entry direction, elbows, name order) is a warning.
    - `[label]` is a warning.
    - `[coverage] orphan frame` is blocking.

- [ ] **Step 1: Failing tests.**
  - Each existing audit test asserts on `findings` (tag, grade, node) instead of regexes over strings.
  - Add `audit-flow: orphan arrow is blocking, edge offset is a warning`.
  - Add `audit-struct: clean page → { pass: true, findings: [] }`.
  - New `lint-grades.test.js`: `every tag a script can emit has a row in lint's severity table, and every table tag is emitted by some script`. It parses the table rows' backticked tags from `lint/SKILL.md` and the tag literals from the three scripts. The rows for a missing required state are prose; exempt them by name.
- [ ] **Step 2: Run** `node --test tools/test/audit-*.test.js tools/test/lint-grades.test.js`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Each emit site builds a `Finding`, and the return builds an `AuditResult`.
  - lint's "Running it" says that the return is an `AuditResult`, that the grade is read from `grade`, and that `pass` replaces the three PASS strings.
  - The severity table stays as the reader's explanation of the scripts' grades. Its lead-in sentence says the scripts set the grades.
- [ ] **Step 4: Run** the tests, `bash plugins/fig/_common/scripts/lib/check.sh` and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `refactor(fig): 감사 스크립트가 등급까지 붙인 결과를 돌려주고 lint는 그 등급을 읽는다`

### Task 2: One section at a time

**Files:**
- Modify: the three audit scripts; `lint/SKILL.md` (Inputs ~:36, Running it, and the "narrow and re-run" sentences ~:115, :179); `audit-flow.js:76` message
- Test: the three audit tests

**Interfaces:**
- Consumes: `AuditResult`, `Finding` (Task 1).
- Produces: an optional input line `const SECTION = "<section node id>";`, prepended after the CFG line.
  - When it is absent, the whole page is audited (today's behaviour).
  - When it is present, only that section and the sections nested in it are audited, at any depth.
  - Not on the page → `{ pass: false, findings: [{ tag: "[section]", grade: "blocking", node: null, msg: "section <id> is not on this page" }] }`.
  - Inside a section that `pages.exclude_sections` excludes → `{ pass: true, findings: [], note: "section <id> is excluded by pages.exclude_sections; nothing audited" }`.
  - flow's coverage check: with `SECTION` set, `[coverage] orphan frame` counts only arrows that start or end inside that section. A frame reached from outside it is not an orphan, so arrows elsewhere on the page are still read.

- [ ] **Step 1: Failing tests**, one set per script:
  - `SECTION limits the audit to that section and its nested sections` (3 levels deep);
  - `unknown SECTION is a blocking [section] finding`;
  - `SECTION inside an excluded parent audits nothing and says so`;
  - flow only: `a frame reached by an arrow from outside SECTION is not an orphan`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
  - lint gains an input, `section` (optional): a section link or name.
  - lint resolves a name to one id with a read-only `use_figma` call. If the name matches none or several sections, it asks.
  - "Narrow to a single section and re-run" now names the input.
- [ ] **Step 4: Run** the tests and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(fig): lint가 섹션 하나만 골라 검사할 수 있다`

### Task 3: The section walk reaches every script that walks sections

**Files:**
- Modify:
  - `audit-component.js` (collect mode's `page.findAll`; compare mode's `sectionsDeep(page.children, () => false)`)
  - `probe-page.js:25` and the uses that follow it
  - `prep-ops.js` `resizeSection` (~:63-71)
  - `tools/verify.py:498-509`
- Test:
  - `tools/test/audit-component.test.js`, `audit-struct.test.js`, `audit-flow.test.js` (3-level fixtures)
  - new `tools/test/probe-page.test.js` and `prep-ops.test.js`
  - `tools/test/verify.test.py`

**Interfaces:**
- Consumes: the `// <sections-deep>` block, signature `sectionsDeep(nodes, skip, ox = 0, oy = 0, inherited = false) → [{ s, ax, ay, skipped }]`.
- Produces:
  - verify's copy check applies to every script under `plugins/fig/_common/scripts` that contains a `// <sections-deep>` marker, not only `audit-*.js`.
  - The check is generalised to any marker name listed in `MARKED_BLOCKS = ["sections-deep", "scaffolding"]`. Task 5 adds the second marker.
  - The reference copy is the first file in sorted path order. A drift message names both files: `[fig] <marker> copy in <file> differs from <reference file>`. Today's message names only one file, so the reader cannot tell which side to fix.

- [ ] **Step 1: Failing tests.**
  - `component compare and collect skip pages.exclude_sections`.
  - `struct, flow and component see a frame three sections deep`.
  - `probe-page reports nested sections with their depth`.
  - `resizeSection checks the sections beside it in the same parent, at any depth`.
  - verify.test: `a drifted sections-deep copy in probe-page.js fails, naming it and the reference file`, and `a drifted scaffolding copy fails`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Component collect walks sections with the shared helper and the `pages.exclude_sections` skip; compare passes the same skip.
  - probe-page uses the helper and adds `depth` to each reported section, for `/fig:setup`'s observation.
  - prep-ops' `resizeSection` compares against `section.parent.children` sections.
  - `renumber` stays top-level, because numbering is a page-level convention. Say so in its comment.
- [ ] **Step 4: Run** all tests and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): 중첩 섹션을 컴포넌트 감사·페이지 관찰·섹션 늘리기까지 같은 방식으로 본다`

### Task 4: State links measured on both axes, and arrows checked end to end

**Files:**
- Modify: `audit-flow.js` (`[state]` check ~:129-135)
- Test: `tools/test/audit-flow.test.js`; new `tools/test/arrow-roundtrip.test.js`

**Interfaces:**
- Consumes: arrow-build.js `arrow()`, `stateLink()`, `styleOf()`; audit-flow's `AuditResult`.
- Produces: `[state]` also checks that the link's start x lies within the from-frame's x-span and its end x within the to-frame's x-span. A miss is a geometry warning.

- [ ] **Step 1: Failing tests.**
  - `a [state] link starting beside the frame's x-span is a warning`.
  - `arrow-roundtrip.test.js`: `straight, elbow and detour arrows drawn by arrow-build pass audit-flow`. Build three frame pairs (side by side; offset in both axes; with a frame in between) with the real `arrow()` against a fake figma that records the created vectors. Run audit-flow over the result and expect `{ pass: true, findings: [] }`. Do the same for one `stateLink()`.
- [ ] **Step 2: Run.** Expected: the x-span test fails. If the round trip fails, that is a real disagreement between the two scripts. Fix the script that is wrong and say which one in the report.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `fix(fig): 상태 연결선을 가로로도 재고, 그린 화살표가 감사를 통과하는지 끝까지 확인한다`

### Task 5: `[unbound]` — lint catches a colour left off the tokens

**Files:**
- Create: `plugins/fig/_common/scripts/audit-tokens.js`
- Modify:
  - `lint/SKILL.md`: checks table, a new group D "Colour tokens"; severity table; Running it; scope input; When NOT :29 — the token-binding line now points to `/fig:tokens` for *binding*
  - README "What `/fig:lint` looks at": `README.md` ~:386 and the Korean counterpart
- Test: new `tools/test/audit-tokens.test.js`

**Interfaces:**
- Consumes: `AuditResult`/`Finding` (Task 1); `SECTION` (Task 2); `sectionsDeep` (Task 3).
- Produces: `audit-tokens.js`.
  - Inputs: `CFG` (`naming.arrow_delimiter`, `naming.label_prefix`, `naming.state_chain_prefix`, `section_style`, `placeholder_style`, `pages.exclude_sections`, `design_system.match_threshold_channel`); optional `SECTION`; optional `MODE`.
  - `MODE = "audit"` (default) → `AuditResult` with `[unbound]` findings.
  - `MODE = "collect"` → `{ dictionary: { [hex]: string[] /* variable keys */ }, unbound: [{ hex, count, nodes: string[], grade: 1 | 2 | 3, nearest: string | null }] }`. This is what `/fig:tokens` builds its mapping table from.
  - The dictionary is every colour variable bound anywhere on the page, plus the file's local colour variables, each resolved to hex.
  - Grading follows tokens' existing scale (tokens ~:64-74):
    - 1 = exact hex in the dictionary;
    - 2 = within `design_system.match_threshold_channel` per channel;
    - 3 = none.
  - Finding grades: grade 1 → blocking (`[unbound]` — "a token for this exact colour exists and was not used"); grades 2 and 3 → warning (a designer has to choose).
  - What counts: SOLID fills, strokes and effect colours on editable nodes.
  - What does not: nodes inside instances (fixed at the component source); working scaffolding (arrows, labels, state chains, section and placeholder styling, as tokens ~:50-62 lists); sections excluded by `pages.exclude_sections`; non-solid paints; paints already bound.
  - The scaffolding test lives in a `// <scaffolding>` block, which Task 6 copies into the bind script.
  - Empty dictionary → `{ pass: true, findings: [], note: "no colour tokens found in this file; [unbound] skipped" }`.

- [ ] **Step 1: Failing tests:**
  - `exact-match unbound fill is blocking`;
  - `near and unmatched are warnings`;
  - `instance children, scaffolding, excluded sections and bound paints are not reported`;
  - `gradient, image and mixed paints are ignored`;
  - `an unbound effect colour is reported`;
  - `no colour tokens → pass with note, no findings`;
  - `collect mode returns the dictionary and graded aggregates`;
  - `SECTION applies`.
- [ ] **Step 2: Run.** Expected: FAIL (no script).
- [ ] **Step 3: Implement** the script.
  - lint runs it as group D under the same calling pattern, `scope` gains `tokens`, and the severity table gains the two `[unbound]` rows.
  - The README's "What `/fig:lint` looks at" gains the check, in both languages.
- [ ] **Step 4: Run** the tests, `check.sh`, `lint-grades.test.js` and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(fig): lint가 토큰에 묶이지 않은 색을 [unbound]로 잡는다`

### Task 6: `/fig:tokens` binds; the scan and the bind are scripts

**Files:**
- Create: `plugins/fig/_common/scripts/token-bind.js`
- Modify:
  - `tokens/SKILL.md`: description; Inputs `mode` :31-32; remove "Lint mode" :76-82; Procedure :84-114 calls `audit-tokens.js` (collect) to scan, `token-bind.js` to bind, `audit-tokens.js` (audit) to verify; delete "Implementation snippets" :116-216
  - `draw/SKILL.md` :191 (step 9: the tokens check is now part of the `/fig:lint` run at :190), :29, :57, :266, :274
  - `setup/SKILL.md:83` if its wording names tokens' modes
  - `README.md` and `README.ko.md`: command list ~:308/:304, mermaid node and flow ~:345/:353, skills table ~:375/:371, diagram ~:776
  - `plugins/fig/README.md:55`
- Test: new `tools/test/token-bind.test.js`; extend `tools/test/fig-removals.test.py` (or a new `fig-scripts.test.py`) with `tokens has no lint mode and no inline js`

**Interfaces:**
- Consumes: `audit-tokens.js` collect output (Task 5); the `// <scaffolding>` block (Task 5).
- Produces: `token-bind.js`.
  - Inputs: `CFG`; `MAPPING = [{ hex: string, variableKey: string }]`; optional `SECTION`.
  - Returns `{ bound: number, skipped: [{ node: string, reason: string }] }`.
  - It writes. It imports by key (`importVariableByKeyAsync`), binds with `setBoundVariableForPaint`, rebuilds the paint array, and never touches instance children or scaffolding (the same `// <scaffolding>` copy).

- [ ] **Step 1: Failing tests.**
  - `token-bind binds exact mapped hexes on editable nodes and rebuilds the paint array`.
  - `skips instances and scaffolding and says why`.
  - The doc test: `tokens/SKILL.md has no "lint mode" and no js block`.
  - The doc test: `draw step 9 no longer calls /fig:tokens`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** the script and rewrite the docs.
  - tokens' description stays one sentence plus triggers, ≤500. It says what tokens does (binds colours to the design system's tokens after showing the mapping) and when.
  - No trigger phrase is dropped; list any that has to change.
- [ ] **Step 4: Run** the tests, `check.sh` and `python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit** `refactor(fig): tokens는 묶기만 하고, 훑기와 묶기를 스크립트로 옮긴다`

### Task 7: sync's snippets become scripts

**Files:**
- Create: `plugins/fig/_common/scripts/sync-compare.js` (the name-matched comparison, sync ~:200-252) and `sync-ops.js` (preamble helpers from ~:256-304)
- Modify: `sync/SKILL.md` "Implementation snippets" ~:194-304 → calling instructions in the existing pattern
- Rename and modify: `tools/test/sync-snippet.test.js` → `tools/test/sync-compare.test.js`, loading the script file
- Test: that file, plus new `tools/test/sync-ops.test.js`

**Interfaces:**
- Produces:
  - `sync-compare.js`: inputs `CFG`, `PAGE_ID`, `CANON_PAGE_ID`. It returns exactly what the snippet returns today: per working frame, the bucket, `onlyWorking`, `onlyCanonical`, heights, `sameMasters`, `masters`, and so on.
  - `sync-ops.js` helpers, with names and parameters taken from today's snippets:
    - `findKeywords(frame, words)`
    - `sameStructure(a, b)`
    - `editValue(textNode, value)` — guarded, loads fonts
    - `fourEdgeClear(section, w, h)`
- [ ] **Step 1:** Move the 15 existing cases to `sync-compare.test.js`, reading the script file. It fails until the script exists. Add one case per `sync-ops` helper, taken from the SKILL.md's own description of it.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
  - The code moves verbatim first. Change only what a script file needs: the input lines become globals the caller prepends.
  - sync's SKILL.md keeps every sentence about what the comparison decides, and replaces each code block with the call.
- [ ] **Step 4: Run** the tests, `check.sh` and `python3 tools/verify.py`. Expected: PASS, with all 15 earlier cases unchanged.
- [ ] **Step 5: Commit** `refactor(fig): sync의 비교·편집 코드를 스크립트로 옮기고 테스트를 그 파일에 건다`

### Task 8: proto's text walk and image scan become scripts

**Files:**
- Create: `plugins/fig/_common/scripts/text-walk.js` (proto ~:66-81) and `image-fills.js` (proto ~:87-102)
- Modify: `proto/SKILL.md` step 2 (the two blocks → calls)
- Test: new `tools/test/text-walk.test.js` and `image-fills.test.js`

**Interfaces:**
- Produces:
  - `text-walk.js`: optional `ROOT_ID` (default: the current page). It returns `[{ id, text, x, y, hidden }]`, sorted by y then x, with absolute coordinates — today's output plus `id`. Phase 3d's qa copy evidence reads this.
  - `image-fills.js` returns today's output.
- [ ] **Step 1: Failing tests:**
  - `text-walk returns every text with absolute position, hidden flag and id, sorted`;
  - `nested and hidden texts are included and marked`;
  - `image-fills lists image paints by node`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Move the code verbatim, then add `id`.
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: Commit** `refactor(fig): proto의 글자 훑기와 이미지 찾기를 스크립트로 옮긴다`

### Task 9: Release fig 3.30.0

**Files:**
- `plugins/fig/.claude-plugin/plugin.json` 3.29.0 → 3.30.0
- `plugins/fig/CHANGELOG.md`
- `plugins/fig/README.md`
- Both root READMEs, wherever lint, tokens, sync or proto behaviour is described
- `.github/lint-catches.html`: re-render with `bash tools/render-images.sh lint-catches` if it lists lint's checks
- `tools/test/verify.test.py`

- [ ] **Step 1: Failing test** in verify.test.py: `a 750-character deck description fails even under its 700 override`.
- [ ] **Step 2: Run.** Expected: FAIL only if verify allows it today. If it already fails as it should, keep the test as a guard and say so.
- [ ] **Step 3:** Version bump and CHANGELOG entry.
  - The entry opens with what a designer sees: lint can take one section; lint catches unbound colours; tokens only binds.
  - It then covers the graded output, the nested walk in component, probe and prep, the state x-span, and the scripts that moved.
  - Each change carries its reason.
- [ ] **Step 4:** README sweep (English, then Korean): the skills table row for tokens; the cycle block; the mermaid flow (tokens is no longer a check step between arrows and lint); "What `/fig:lint` looks at"; `plugins/fig/README.md`. Re-render `lint-catches` if it lists checks.
- [ ] **Step 5:** Run `bash tools/verify-all.sh`. Expected: `· PASS`, no WARN.
- [ ] **Step 6: Commit** `chore(release): fig 3.30.0 — lint가 섹션 하나·묶이지 않은 색까지 보고, 글 속 코드가 스크립트가 된다`. The controller pushes, previews the PR and waits for go.
