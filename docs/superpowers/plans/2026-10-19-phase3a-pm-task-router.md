# Phase 3a — `/pm:task` router (pm side of Merges and removals) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/pm:task-draft`, `/pm:task-publish` and `/pm:task-sync` become one skill, `/pm:task draft|publish|sync`, whose router holds every block the three used to repeat; sync files tickets from a shared `filing.md` instead of loading publish; fig and pm agree on one heading for the design section; the task skills' `allowed-tools` match what they call.

**Architecture:** `plugins/pm/skills/task/` holds a short `SKILL.md` (the router: guard, config order, mode choice, adapter lookup and exits, the rules every mode shares) and one file per mode (`draft.md`, `publish.md`, `sync.md`) plus `filing.md`, read by publish and sync. Blocks lifted into the router are deleted from the mode files, not copied. The old names stop existing in the same release; no redirect stubs.

**Tech Stack:** Markdown skill files, Python 3.9 tests (`tools/test/*.test.py`), the repository checker `tools/verify.py`, bash.

**Spec:** on branch `worktree-local-first-design`:
- `docs/design/2026-10-18-local-first-defaults.md` §7 (the merge) and §9 (descriptions)
- `docs/design/2026-10-18-skill-review.md` S3 (adapter lookup and filing rules only — the version pin and code-in-prose bullets are Phase 3b), S6 (the rows for the task skills, prd, setup and log), S9 (the router), S14 (the handoff → pm seam)
- `docs/superpowers/plans/2026-10-18-skills-overhaul-roadmap.md`, Phase 3 and *Release and surfaces*

§10 ("Where the two meet") already shipped in fig 3.28.0 and is not in this plan. Phase 3b (fig: deck merge, diff removal, tokens into lint, lint output, write gates, qa against the pinned version, the description FAIL switch) is a separate plan.

## Global Constraints

- Branch `overhaul-phase3`, cut at `origin/main` 7c40e6f (fig 3.28.1, pm 0.38.2). Line numbers below are against 7c40e6f.
- No redirect stubs. `/pm:task-draft`, `/pm:task-publish`, `/pm:task-sync` stop existing in this release. CHANGELOG history is left as written (decision 6, §7).
- The new forms are `/pm:task draft`, `/pm:task publish`, `/pm:task sync` in prose, and `task draft` / `task publish` / `task sync` where a picture names commands without the slash.
- `SKILL.md` stays under 500 lines. The task skill's `description` is 700 characters or fewer; every other pm skill's is 500 or fewer, counted on the YAML-parsed value (`verify.py` `DESC_LIMIT_OVERRIDE` already holds `("pm","task"): 700`).
- `_common/scripts/lib/resolve-config.py` and `preflight.py` stay byte-identical across `plugins/pm` and `plugins/fig`; change the pm copy, then `cp` it to fig.
- Shipped scripts run on Python 3.9 (no `X | None` annotations evaluated at def time). Any test that starts a subprocess drops every `GIT_*` variable from its environment (`clean_env` in `tools/test/markdown-tracker.test.py`).
- No team-specific value in any shipped file. Documents and code comments English; commit messages Korean, `type(scope): …`.
- Run `bash tools/verify-all.sh` on its own before a push. Before every push, `git branch --show-current` and `git log -1` must name the branch and commit you mean to push — the pre-push hook checks the working tree, not the pushed ref. An implementer that checks out another commit (to see a test fail on old code) returns to the branch before committing.
- Every write outside this repository — the PR, the GitHub release, the team-config repository, the team's Notion guides — is preview → go.

## Review Focus

1. **Someone types an old name after upgrading** (`/pm:task-publish`). Nothing answers to it; the root READMEs and the CHANGELOG's first lines map old → new so the search finds the new form. → Task 1 test `readmes map the old names`.
2. **`/pm:task publish` on a record-only setup** (`task.mirror.type: none`). The record-only message shows before any `--need task.link_property` exit can (S9 "Order"). → Task 2 test `record-only check comes before the mode's --need`.
3. **A team whose Notion records head the design section with something other than "Design changes".** publish finds no heading named by `task.design_heading`, falls back to the section that plays that role, and says which section it read. No regression for a team that never sets the key. → Task 4 test `publish falls back to the role and says so`.
4. **fig's `task_tracker.ui_section_heading` written, and fig borrowing pm's markdown record.** The line goes under pm's `task.design_heading`, and the answer's `note` says fig's heading was not used and why. → Task 4 test `fig heading differs → pm's heading, with a note`.
5. **sync files a missing ticket.** It reads `filing.md` and never `publish.md`. → Task 3 test `sync reads filing, never publish`.

---

### Task 1: One skill folder, the old names gone everywhere

The bodies move unchanged; only names change. This task and the rename sweep are one because `verify.py` fails any reference to a skill that does not exist (`SKILL_REF`, verify.py:378, existence at :437).

**Files:**
- Create: `plugins/pm/skills/task/SKILL.md`, `draft.md`, `publish.md`, `sync.md` (the three bodies move with `git mv`, so history follows)
- Delete: `plugins/pm/skills/task-draft/`, `task-publish/`, `task-sync/`
- Modify every file in the facts list below (the old names, 127 hits at 7c40e6f, all outside `plugins/*/CHANGELOG.md` and `docs/`):
  - both root READMEs (18 each), `plugins/pm/README.md` (7), `plugins/fig/README.md:113`
  - `plugins/pm/skills/setup/SKILL.md` (18), `log/SKILL.md:138-140`, `log-review/SKILL.md:103`, `prd/SKILL.md:30`
  - `plugins/fig/skills/handoff/SKILL.md:36,71,129`
  - `plugins/pm/_common/conventions.example.yaml:132,144,247,256,347`, `_common/sources/README.md:20`, `_common/trackers/README.md:55-74`, `trackers/github.md:6,59,152`, `markdown.md:35`, `notion.md:47`
  - `plugins/{pm,fig}/_common/scripts/lib/preflight.py:74` (byte-identical)
  - `.github/context-table.html:29`, `.github/two-plugins.html:29,38` (the PNGs are re-rendered in Task 7)
- Create: `tools/test/task-skill.test.py`

**Interfaces:**
- Produces: the folder `plugins/pm/skills/task/` with `SKILL.md` (name `task`) and three mode files. This task's `SKILL.md` is a stub: the frontmatter (the union of the three `allowed-tools` lists for now — Task 5 trims it; the description joins the three — Task 6 rewrites it), one sentence, and a table pointing each mode at its file. Tasks 2–6 build on it.
- Produces: `tools/test/task-skill.test.py` with a `check(label, cond, detail)` helper in the style of `tools/test/verify.test.py`, constants `TASK = REPO/"plugins/pm/skills/task"` and `OLD = ("task-draft", "task-publish", "task-sync")`. Later tasks add cases to this file.

- [ ] **Step 1: Write the failing tests** in `tools/test/task-skill.test.py`:
  - `one folder` — `TASK/"SKILL.md"`, `draft.md`, `publish.md`, `sync.md` exist; none of `plugins/pm/skills/task-draft`, `task-publish`, `task-sync` exists.
  - `no old name outside history` — over the files `git ls-files` lists (run with every `GIT_*` variable dropped from its environment), skipping `docs/`, `plugins/*/CHANGELOG.md`, binary files and this test file, none contains any string in `OLD`.
  - `readmes map the old names` — `README.md` contains each of `/pm:task-draft → /pm:task draft`, `/pm:task-publish → /pm:task publish`, `/pm:task-sync → /pm:task sync`; `README.ko.md` contains the same three arrows.
  - `the skill table lists task once` — `plugins/pm/README.md`, `README.md` and `README.ko.md` each have exactly one table row whose first cell is `` `/pm:task` ``.
- [ ] **Step 2: Run** `python3 tools/test/task-skill.test.py`. Expected: all four FAIL.
- [ ] **Step 3: Move and rename.**
  - `git mv` each `SKILL.md` to its mode file; strip each mode file's frontmatter (it moves to the stub). Inside the mode files, self-references become the new forms. publish's `--mode contract` input stays as it is here (Task 2 changes the grammar).
  - Write the stub `SKILL.md`.
  - Sweep every listed file. In prose, `/pm:task-draft` → `/pm:task draft` and so on; in the pictures' HTML, `task-draft` → `task draft`. Grammar around a renamed name stays correct (e.g. "`/pm:task publish` reads that line").
  - The three README skill tables replace the three rows with one `/pm:task` row describing all three modes, and both root READMEs gain, beside the table, the three old → new arrows exactly as the test spells them (English; the Korean README carries the same arrows).
  - `cp plugins/pm/_common/scripts/lib/preflight.py plugins/fig/_common/scripts/lib/` after editing pm's.
- [ ] **Step 4: Run** `python3 tools/test/task-skill.test.py && python3 tools/verify.py`. Expected: PASS; verify reports no stale skill reference.
- [ ] **Step 5: Commit**
```bash
git add -A plugins tools/test/task-skill.test.py README.md README.ko.md .github/*.html
git commit -m "refactor(pm): 일감 스킬 셋을 /pm:task 한 폴더로 옮기고 옛 이름을 저장소에서 지운다"
```

### Task 2: The router holds what the three modes share

**Files:**
- Modify: `plugins/pm/skills/task/SKILL.md` (the router), `draft.md`, `publish.md`, `sync.md` (lifted blocks deleted)
- Test: `tools/test/task-skill.test.py`

**Interfaces:**
- Consumes: Task 1's folder and test file.
- Produces, in `SKILL.md`, in this order:
  1. **The plugin guard** — the "Part of a plugin." paragraph (today at line 9 of all three).
  2. **Which mode.** Argument grammar, verbatim: `/pm:task draft <source> [<record>]`, `/pm:task publish <record> [--contract | --template]`, `/pm:task sync`. Without a mode word, the request decides: a thread, page or conversation to turn into a task → draft; "file / publish / update the ticket" → publish; "reconcile / sync" → sync. Ask only when it is still unclear (§7). `--contract` replaces publish's `mode: contract` input (publish:59, :568); `--template` runs publish's "Bringing a ticket back to the template" pass directly (publish:535-581), which sync's off-template rows (sync:123, :143, :166) now name.
  3. **Config, in S9's order.** First `resolve-config.py --name pm-conventions.yaml --authored task.record.type,task.record.ref` with no `--need`. For publish and sync, `task.mirror.type: none` stops here with the record-only message (publish:30-33, verbatim, kept once). Then the mode's own call: draft `--need task.record.ref`; publish and sync `--need task.record.ref,task.link_property,task.mirror.ref --authored task.record.type,task.record.ref,task.link_property,task.contract.level`, sync adding `task.progress_source` to `--authored` only where `task.properties.progress` is named (sync:38). The stderr notes (a null names a config gap that `/pm:setup` writes; `--authored` is the other half) appear once.
  4. **Adapter lookup and exits** — the `adapter.py` calls and the exit-3 / exit-4 paragraph (draft:135-141, publish:501-509, sync:94-100), once, with which roles each mode reads.
  5. **Rules every mode follows** — matching on `task.link_property` alone (publish:48, sync:44); `task.policy.doc` and `task.template` read once per session before the first write (publish:50-54, sync:51-52); title rules (publish:280-299 with draft's title row at draft:115 and sync's "Reads as internals" row at sync:122 pointing to them); the no-invented-mappings rule (publish:600, sync:167, draft:15); preview → go before every external write.
  6. **`(unverified)` marks.** `/pm:setup` 4c writes the calls it drafted into the person's adapter file marked `(unverified)` (setup:251, trackers/_template.md:8). After a marked call succeeds in a publish or sync run and its result reads back, the mark is removed from that line of the person's adapter file — never from a bundled adapter. The edit is listed in the run's preview, and a call that fails keeps its mark and stops the run, naming it.
  7. **The mode table** — each mode, its file, and its one-line job.
- Mode files keep only what is their own; every lifted block is deleted from them, and where a mode file needs a lifted rule it names the router section instead.

- [ ] **Step 1: Add the failing tests:**
  - `each shared block once` — across `TASK/*.md`, each of these strings occurs exactly once, and in `SKILL.md`: `**Part of a plugin.**`, `Exit 3 means no adapter exists`, `Matching runs on \`task.link_property\``, `These tasks are kept as records only`, `Never invent a mapping`, `before the first write of the session`, `Written for the people who will act on it`.
  - `argument grammar` — `SKILL.md` contains the three grammar lines verbatim; no file under `TASK` contains `--mode contract` or `` `mode` (optional) ``.
  - `record-only check comes before the mode's --need` — in `SKILL.md`, the first `resolve-config.py` line has no `--need`, and the offset of `These tasks are kept as records only` is smaller than the offset of the first `--need task.record.ref,task.link_property`.
  - `unverified marks are cleared by a run` — `SKILL.md` contains `(unverified)`, and `plugins/pm/skills/setup/SKILL.md` no longer says the first `/pm:task publish` run removes marks unless `SKILL.md` describes that removal (assert both strings `remove` and `(unverified)` occur in one paragraph of `SKILL.md`).
  - `the router stays short` — `SKILL.md` has fewer than 200 lines.
- [ ] **Step 2: Run** `python3 tools/test/task-skill.test.py`. Expected: the five new cases FAIL.
- [ ] **Step 3: Write the router and delete the lifted blocks from the mode files.** Update `setup/SKILL.md:251` to say the first `/pm:task publish` or `sync` run that uses a marked call clears its mark, and check `trackers/README.md:90` and `trackers/_template.md:8` still agree.
- [ ] **Step 4: Run** `python3 tools/test/task-skill.test.py && python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add plugins/pm tools/test/task-skill.test.py
git commit -m "refactor(pm): 세 모드가 되풀이하던 설정 순서·어댑터·공통 규칙을 /pm:task 라우터 한 곳에 둔다"
```

### Task 3: `filing.md` — the rules for filing a ticket, read by publish and sync

**Files:**
- Create: `plugins/pm/skills/task/filing.md`
- Modify: `publish.md`, `sync.md`, `SKILL.md` (the mode table names `filing.md`)
- Test: `tools/test/task-skill.test.py`

**Interfaces:**
- Produces: `filing.md` with these sections, moved out of publish (line numbers against 7c40e6f's task-publish): `## Resolve the parent` (226-246), `## Labels` (the "Labels have two sources" rule, 475), `## Create` (the duplicate check, create, and the link written right after create, 469-473), `## Milestone` (481, 489), `## Attach to the board` (483-509 minus the adapter lookup, which Task 2 lifted), `## Write the link back` (511-518). Title rules are the router's (Task 2); filing names that section.
- `publish.md` names `filing.md` at the step where it files; `sync.md:139-145` says "Creating follows `filing.md`" in place of "the same rules as `/pm:task publish`", keeps its own minimal-body and no-contract rules (141, 145), and reports tickets it created as still needing `/pm:task publish`.

- [ ] **Step 1: Add the failing tests:**
  - `filing holds the filing rules` — `filing.md` exists and contains the six `##` headings above; `Labels have two sources` occurs once across `TASK/*.md`, in `filing.md`.
  - `sync reads filing, never publish` — `sync.md` contains `filing.md` and does not contain `publish.md`.
  - `publish reads filing` — `publish.md` contains `filing.md`.
- [ ] **Step 2: Run** the test file. Expected: the three new cases FAIL.
- [ ] **Step 3: Move the sections; rewrite the two references.**
- [ ] **Step 4: Run** `python3 tools/test/task-skill.test.py && python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add plugins/pm/skills/task tools/test/task-skill.test.py
git commit -m "refactor(pm): 티켓 올리는 규칙을 filing.md로 빼 sync가 publish 전체를 읽지 않게 한다"
```

### Task 4: One heading for the design section, read by both plugins (S14)

**Files:**
- Modify: `plugins/pm/_common/conventions.example.yaml` (the `task:` block, beside `link_property` at :167), `plugins/pm/skills/task/publish.md` (the design-section reads at today's publish:88, 154, 215-216, 341, 384, 614), `plugins/fig/_common/scripts/lib/borrow-pm.py` (:45 `HEADING`, :395 in `decide_task`), `plugins/fig/skills/handoff/SKILL.md:51`, `plugins/fig/_common/conventions.example.yaml:230` (the `ui_section_heading` comment), `plugins/pm/_common/trackers/markdown.md` (the record skeleton)
- Test: `tools/test/borrow-pm.test.py`, `tools/test/resolve-config.test.py`, `tools/test/task-skill.test.py`

**Interfaces:**
- Produces the pm key `task.design_heading`, floor `"Design changes"`. Comment: the heading of the record's section that holds the handover line; `/fig:handoff` writes under it in pm's markdown records and `/pm:task publish` reads the pinned version from under it; language-independent — it is matched as written, so a conversation in another language does not change it.
- `borrow-pm.py task`: where `action` is `write`, `heading` is pm's resolved `task.design_heading` (fig already resolves pm's config through pm's own reader). Where fig's `task_tracker.ui_section_heading` is written and differs, `note` says the line goes under pm's heading and that fig's heading applies to Notion and GitHub only. For `notion` and `github`, `heading` stays fig's `ui_section_heading` or `HEADING`. `HEADING` stays as the last fallback.
- `publish.md`: the design section is the one headed `task.design_heading`; where no such heading exists, it falls back to the section that plays that role today and says in the report which heading it read.

- [ ] **Step 1: Add the failing tests:**
  - `resolve-config.test.py`: `pm floor: design heading` — the resolved pm floor has `task.design_heading == "Design changes"`.
  - `borrow-pm.test.py`: `write uses pm's design heading` — pm config `task: {design_heading: Handover}`, fig unset → `heading == "Handover"`, `note` null. `fig heading differs → pm's heading, with a note` — the same pm config plus fig `task_tracker: {ui_section_heading: Notes}` → `heading == "Handover"`, `note` contains `ui_section_heading`. Keep the existing `a set heading is used` case meaningful for `notion`/`github` (fig `task_tracker: {type: notion, ref: x, ui_section_heading: Handover}` → `heading == "Handover"`).
  - `task-skill.test.py`: `publish falls back to the role and says so` — `publish.md` contains `task.design_heading` and a sentence containing both `falls back` and `says which`.
- [ ] **Step 2: Run** the three test files. Expected: the new cases FAIL.
- [ ] **Step 3: Implement** the key, borrow-pm's rule, publish's read, the two comments, and handoff's line 51. The markdown skeleton in `markdown.md` gains the section `## Design changes` after `## Change summary`, with a comment naming `task.design_heading`.
- [ ] **Step 4: Run** `python3 tools/test/borrow-pm.test.py && python3 tools/test/resolve-config.test.py && python3 tools/test/task-skill.test.py && python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add plugins tools/test
git commit -m "feat: 핸드오프가 쓰고 pm 게시가 읽는 설계 절 제목을 pm의 task.design_heading 하나로 맞춘다"
```

### Task 5: `allowed-tools` matches what each pm skill calls (S6)

**Files:**
- Modify: frontmatter of `plugins/pm/skills/task/SKILL.md`, `log/SKILL.md:5`, `prd/SKILL.md`, `setup/SKILL.md`
- Test: `tools/test/task-skill.test.py`

**Interfaces:**
- task: the union of the three old lists minus every `mcp__plugin_github_github__*` tool (none is called; the GitHub adapter runs `gh` — trackers/github.md) and minus Figma tools publish never calls. Notion and Slack read tools stay: `trackers/notion.md` and `sources/slack.md` call them.
- log: remove `mcp__plugin_github_github__issue_read`.
- prd: add the Figma read tools it uses, Slack read tools and `WebFetch`, and one sentence in its body saying that connectors named only under `reference_sources` will prompt for permission.
- setup: add `Edit`.
- `verify.py`'s tool check (adapter-named tools must appear in some skill's `allowed-tools`, around verify.py:300) still passes.

- [ ] **Step 1: Add the failing test** `allowed-tools match the calls` — task's `allowed-tools` has no `mcp__plugin_github_github__` entry; log's has no `issue_read`; prd's has `WebFetch`; setup's has `Edit`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Edit the four frontmatters and prd's sentence.**
- [ ] **Step 4: Run** `python3 tools/test/task-skill.test.py && python3 tools/verify.py`. Expected: PASS.
- [ ] **Step 5: Commit**
```bash
git add plugins/pm/skills tools/test/task-skill.test.py
git commit -m "fix(pm): 스킬마다 미리 허용하는 도구를 실제로 부르는 것에 맞춘다"
```

### Task 6: Descriptions in one shape (§9)

**Files:**
- Modify: `description` of `plugins/pm/skills/task/SKILL.md` and `plugins/pm/skills/setup/SKILL.md`; any other pm skill whose description is not one sentence plus triggers

**Interfaces:**
- task: one sentence on what it does and when (draft a task from a request, file it as a ticket, keep the list in step with the tracker), then the trigger phrases of all three old skills in both languages, restoring the two English triggers 2a dropped to fit 500 ("update the GitHub task", "sync notion and github"); ≤700.
- setup: one sentence plus triggers (deferred from 2a), ≤500.

- [ ] **Step 1: Add the failing test** `descriptions in one shape` — task's description ≤700 and contains `/pm:task`, `update the GitHub task`, `sync notion and github`, and the Korean triggers `일감 초안 잡아줘`, `티켓 갱신해줘`, `일감 동기화해줘`; setup's description ≤500 and has exactly one sentence before `Triggers` (count `. ` before the word `Triggers`).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Rewrite the descriptions;** behaviour detail that leaves a description moves into its body where the body lacks it.
- [ ] **Step 4: Run** `python3 tools/test/task-skill.test.py && python3 tools/verify.py`. Expected: PASS, no WARN for any pm skill.
- [ ] **Step 5: Commit**
```bash
git add plugins/pm/skills tools/test/task-skill.test.py
git commit -m "docs(pm): 스킬 설명을 한 문장과 트리거 모양으로 맞추고 task에 세 스킬의 트리거를 모은다"
```

### Task 7: Release 3a

**Files:**
- `plugins/pm/.claude-plugin/plugin.json`: `0.38.2 → 0.39.0`; `plugins/fig/.claude-plugin/plugin.json`: `3.28.1 → 3.28.2`
- `plugins/pm/CHANGELOG.md`, `plugins/fig/CHANGELOG.md`
- `plugins/pm/README.md` (the paragraphs at :48, :50, :54, :64 now name modes), `README.md` and `README.ko.md` (the cycle block, the task paragraphs, *What each skill needs*, the repository tree at README.md:789-790 / README.ko.md:785-786)
- `.github/two-plugins.png`, `.github/context-table.png` — re-rendered

**Interfaces:**
- pm 0.39.0's entry opens with the three old → new names, then: the router and what it holds; `filing.md`; `--contract` and `--template`; `(unverified)` cleared by a run; `task.design_heading` (new key); `allowed-tools` trimmed; descriptions. fig 3.28.2's entry: handoff writes under pm's `task.design_heading` in pm's markdown records, with a note where fig's `ui_section_heading` differs; preflight's copy names `/pm:task draft`.

- [ ] **Step 1: Versions, CHANGELOGs, READMEs** (English first, then the same in Korean).
- [ ] **Step 2: Re-render** `bash tools/render-images.sh two-plugins context-table`; look at each next to its committed version (`git show HEAD:.github/<name>.png`) and confirm the new names render and nothing is clipped.
- [ ] **Step 3: Run** `bash tools/verify-all.sh` on its own. Expected: `· PASS`; no description WARN for any pm skill (fig's remain until 3b).
- [ ] **Step 4: Commit** — `chore(release): pm 0.39.0, fig 3.28.2 — 일감 스킬 셋이 /pm:task 하나가 된다`.
- [ ] **Step 5 (controller): owner's configs, read-only.** Resolve the owner's layers with the new pm and with 0.38.2; the only difference allowed is the new `task.design_heading` leaf. Never paste values.
- [ ] **Step 6 (controller): callers outside the repository.** Rerun the search (§7: "new callers may appear"). Known at 7c40e6f: the personal sessions skill (`claude-settings/skills/sessions/SKILL.md:23,63`, `DESIGN.md:33`), the team-config repository (`README.md:11`, `pm-conventions.yaml:59-60` comments), and the team's Notion guides (*AI 스킬로 일하기*, *일감 관리*), which name the old skills throughout. The personal skill is edited and committed in its repository; the team-config repository and the Notion guides are previews → go.
- [ ] **Step 7 (controller): push, PR, release.** Confirm branch and head, push, preview the PR (title, body with the old → new map, Step 5's difference list, and the owner's live check from S14's Done-when: `/fig:handoff` writes its line into a markdown record, then `/pm:task publish` on that record fills the referenced-version row) → go → open. After merge, the GitHub release for pm 0.39.0 is a preview → go (roadmap: a phase that changes user-visible commands cuts one).
