# Phase 1 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository's checks and shared scripts trustworthy before the larger changes:
the checker reads every file a skill can live in, the shared scripts know which plugin they belong
to, the session hook cannot fail a session, the audit scripts see nested sections, and re-synced
arrows keep their style.

**Architecture:** All changes are to tools and to the scripts under `plugins/*/_common` and
`plugins/*/hooks`. The audit and arrow scripts run alone inside the Figma sandbox and cannot
import one another, so a shared helper is duplicated between markers, and the checker keeps the
copies identical. Tests follow the repository's pattern: Python fixtures run the script as a
subprocess, and Node fixtures build the script with `new Function` and fake `figma` globals.

**Tech Stack:** Python 3 (stdlib, PyYAML), Node `node:test`, bash, headless Chrome for images.

**Spec:** `docs/design/2026-10-18-skill-review.md` (S1, S7, S8; Bin A 1, 2, 9; the fig lint
appendix row on the start-edge check) and the roadmap
`docs/superpowers/plans/2026-10-18-skills-overhaul-roadmap.md`. Both are on branch
`worktree-local-first-design`.

## Global Constraints

- Branch from the latest `origin/main`. Line numbers below are against `5139446`.
- Commit messages are Korean, `type(scope): what changed, in a sentence`. The body says why.
- Documents and code comments are English.
- `_common/scripts/lib/resolve-config.py`, `preflight.py`, `hooks/shared-config.py` and
  `hooks/hooks.json` stay byte-identical across the two plugins (`SHARED`, verify.py:39-40).
  Change one, copy it across.
- No team-specific value in any shipped file. Prose never carries a skill count.
- Every change under `plugins/<p>/` raises that plugin's version (`plugin.json`) and adds a
  CHANGELOG entry.
- Run `bash tools/verify-all.sh` before pushing, and never chain it with `&&` to a push.

## Review Focus

1. **A clone with no `tools/team-strings.local.txt`.** The team-string check is skipped with a
   WARN, and the checker still passes. → Task 1 test `no team strings file → skipped, not failed`.
2. **Sections nested three deep, under an excluded parent.** Everything inside an excluded section
   is excluded, at any depth. → Task 5 test `excluded parent excludes nested sections`.
3. **An existing arrow with no stroke.** `styleOf` returns `null`, and the config's style is used.
   → Task 7 test `styleOf on an unstroked vector is null`.
4. **A shared script with no `plugin.json` above it**, e.g. a file shipped alone. Identity falls
   back to the path rule and never raises. → Task 3 test `no plugin.json → path fallback`.
5. **A reference-like string that is not a reference**, such as a URL path containing `/pm:` or
   `/fig:` inside a link. Only `/fig:<name>` and `/pm:<name>` tokens count, bounded by a non-word
   character. → Task 1 test `a url containing /pm: is not a reference`.

---

### Task 1: The checker reads every file a skill can live in

**Files:**
- Modify: `tools/verify.py` (the per-skill loop at :193-237; a new repo-wide reference pass
  called from `main()` at :353)
- Create: `tools/test/verify.test.py`

**Interfaces:**
- Produces:
  - Failure lines in exactly this form, which later phases' sweeps rely on:
    - `[{plugin}:{skill}] {path} → /{plugin2}:{ref} does not exist`
    - `[{plugin}:{skill}] {path}: `{key}` is not in the schema`
    - `[{plugin}:{skill}] {path}: team value '{w}'`
  - `{path}` is relative to the repository root.
  - A helper `copy_repo(tmp) -> Path` inside the test file, reused by Tasks 2 and 4.

The per-skill checks — config keys, skill references, absolute paths, team strings — run over
every `*.md` under `skills/<sk>/`, not only `SKILL.md`. Skill references are also checked
repo-wide, against both plugins' skill names, in:

- `plugins/*/skills/**/*.md`
- `plugins/*/_common/**/*.md` and `plugins/*/_common/**/*.py`
- `plugins/*/README.md`, `README.md`, `README.ko.md`
- `.github/*.html`

CHANGELOGs are never scanned. The root READMEs' existing exemption for official `figma-*` names
(verify.py:344) stays.

- [ ] **Step 1: Write the failing tests** in `tools/test/verify.test.py`. Same shape as
  `preflight.test.py`: `check(label, cond, detail)` and a failure list. `copy_repo` copies the
  repository into a temp dir, ignoring `.git`, `node_modules`, `node_modules.nosync` and `.claude`.
  Each case plants one file and runs `python3 <tmp>/tools/verify.py`.

| Test name | Plant | Assert |
|---|---|---|
| `clean copy passes` | nothing | exit 0 |
| `stale reference in a mode file` | `plugins/pm/skills/prd/notes.md`: "see /pm:nonexistent" | exit 1, stdout contains `plugins/pm/skills/prd/notes.md → /pm:nonexistent does not exist` |
| `cross-plugin stale reference in _common` | append "→ /fig:nonexistent" to `plugins/pm/_common/trackers/README.md` | exit 1, stdout contains `→ /fig:nonexistent does not exist` |
| `unknown config key in a mode file` | `plugins/fig/skills/lint/extra.md`: "`qa.nonexistent_key`" | exit 1, stdout contains ``extra.md: `qa.nonexistent_key` is not in the schema`` |
| `team string in a mode file` | write `tools/team-strings.local.txt` = `ZZTEAMZZ`, plant "ZZTEAMZZ" in `plugins/pm/skills/prd/notes.md` | exit 1, stdout contains `team value 'ZZTEAMZZ'` |
| `no team strings file → skipped, not failed` | none, no strings file | exit 0, stdout contains the existing skip WARN |
| `a url containing /pm: is not a reference` | `plugins/pm/skills/prd/notes.md`: "`https://example.com/a/pm:b`" | exit 0 |

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/verify.test.py`
Expected: FAIL on the three "mode file" cases and the `_common` case. The clean and URL cases may
already pass.

- [ ] **Step 3: Implement in `tools/verify.py`.**
  - Iterate `sorted(skills.joinpath(sk).rglob("*.md"))` for the per-skill checks, and report
    `{path}`.
  - Add `def check_references(plugins: dict[str, set[str]]) -> None`, called once from `main()`
    with every plugin's skill names. It scans the files listed above with
    `re.compile(r"(?<![\w/.-])/(fig|pm):([a-z][a-z-]*)")`.
  - Keep the frontmatter checks on `SKILL.md` only.

- [ ] **Step 4: Run the tests, then the real repository**

Run: `python3 tools/test/verify.test.py && python3 tools/verify.py`
Expected: all PASS. If the real repository now fails on genuine stale references, fix those
references in this task, and say which in the commit body.

- [ ] **Step 5: Commit**

```bash
git add tools/verify.py tools/test/verify.test.py
git commit -m "feat(tools): 검사기가 스킬 폴더의 모든 문서와 공통 문서를 두 플러그인 이름으로 훑는다"
```

### Task 2: Description length, and one description per plugin

**Files:**
- Modify: `tools/verify.py`, `.claude-plugin/marketplace.json`
- Test: `tools/test/verify.test.py`

**Interfaces:**
- Consumes: `copy_repo` (Task 1).
- Produces:
  - `DESC_LIMIT = 500` and `DESC_LIMIT_OVERRIDE = {("fig", "deck"): 700, ("pm", "task"): 700}`
    in `verify.py`. Phase 3 changes the length report from WARN to FAIL.
  - WARN line: `[{plugin}:{skill}] description is {n} characters (limit {limit})`.
  - FAIL line: `[{plugin}] plugin.json and marketplace.json descriptions differ`.

- [ ] **Step 1: Write the failing tests**

| Test name | Plant | Assert |
|---|---|---|
| `long description warns` | rewrite `plugins/pm/skills/log-review/SKILL.md`'s description to 600 × "a" | exit 0, stdout contains `description is 600 characters (limit 500)` |
| `override limit applies` | a 650-character description on a copy renamed to `plugins/pm/skills/task/SKILL.md` | no WARN for it |
| `marketplace and plugin.json differ` | change pm's description in `plugin.json` only | exit 1, stdout contains `[pm] plugin.json and marketplace.json descriptions differ` |

Count characters of the YAML-parsed description, not bytes.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/verify.test.py`
Expected: the three new cases FAIL.

- [ ] **Step 3: Implement both checks.** Then make `marketplace.json`'s pm description equal to
  pm's `plugin.json` description. `plugin.json` is the source. Phase 2 rewrites both together.

- [ ] **Step 4: Run tests and the real repository**

Run: `python3 tools/test/verify.test.py && python3 tools/verify.py`
Expected: PASS, with WARN lines for today's long descriptions. That is expected until Phase 3.

- [ ] **Step 5: Commit**

```bash
git add tools/verify.py tools/test/verify.test.py .claude-plugin/marketplace.json
git commit -m "feat(tools): 설명 길이를 알리고 마켓·plugin.json 소개가 어긋나면 막는다"
```

### Task 3: Shared scripts know their plugin by name

**Files:**
- Modify, kept byte-identical across both plugins:
  - `plugins/{fig,pm}/_common/scripts/lib/resolve-config.py:41-43`
  - `plugins/{fig,pm}/_common/scripts/lib/preflight.py:29-30`
  - `plugins/{fig,pm}/hooks/shared-config.py:30-31`
- Test: `tools/test/resolve-config.test.py`

**Interfaces:**
- Produces, in each of the three files:
  - `def plugin_name(here: str) -> str`. It walks up from `here` to the first
    `.claude-plugin/plugin.json` and returns its `"name"`. When none is found, it falls back to
    today's path rule (`"pm"` if `/pm/` is in the path, else `"fig"`). It never raises.
  - `PLUGIN = plugin_name(HERE)`.
  - In `resolve-config.py`, `DEFAULT_NAME = {"pm": "pm-conventions.yaml"}.get(PLUGIN, "figma-conventions.yaml")`.

- [ ] **Step 1: Write the failing tests** in `resolve-config.test.py`:
  - `fig copied under a path containing /pm/ is still fig`. Copy `plugins/fig` to
    `<tmp>/pm/plugins/fig` and run its `resolve-config.py` with no `--name`. `meta.layers[0]` ends
    with `fig/_common/conventions.example.yaml`.
  - `pm's default name is pm-conventions.yaml`. Run pm's copy with no `--name`, with only
    `~/.claude/pm-conventions.yaml` present. That file appears in `meta.layers`.
  - `no plugin.json → path fallback`. Copy only `plugins/pm/_common` to `<tmp>/pm/_common` and run.
    The exit code is not a traceback (0 or the script's own "no config" exit), and stderr has no
    `Traceback`.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/resolve-config.test.py`
Expected: the first two FAIL.

- [ ] **Step 3: Implement `plugin_name`** in `resolve-config.py`, then copy the function into the
  other two files. Copy each file across plugins so `SHARED` holds.

- [ ] **Step 4: Run**

Run: `python3 tools/test/resolve-config.test.py && python3 tools/test/preflight.test.py && python3 tools/verify.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/*/_common/scripts/lib/resolve-config.py plugins/*/_common/scripts/lib/preflight.py plugins/*/hooks/shared-config.py tools/test/resolve-config.test.py
git commit -m "fix(shared): 공통 스크립트가 경로 대신 plugin.json 이름으로 자기 플러그인을 안다"
```

### Task 4: The session hook cannot fail or hang a session

**Files:**
- Modify: `plugins/{fig,pm}/hooks/shared-config.py`, byte-identical (the git call at :73, the
  guard at :87-90)
- Create: `tools/test/shared-config.test.py`

**Interfaces:**
- Produces: the git call passes `env = {**os.environ, "GIT_TERMINAL_PROMPT": "0",
  "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}`. The top-level guard catches `BaseException`.

- [ ] **Step 1: Write the failing tests**
  - `no PyYAML → silent exit 0`. Make a temp `HOME` with `.claude/figma-conventions.yaml`
    containing `meta: {profile: x}`. Run `python3 -S plugins/fig/hooks/shared-config.py`; `-S`
    keeps site-packages, and so PyYAML, out. Assert returncode 0 and empty stderr.
  - `git never prompts`. Load the hook with `importlib`, replace `resolver()` with a fake whose
    `origin_state` returns `{"root": "/x", "dirty": False}`, set `due` to return `True`, and
    capture `subprocess.run`'s `env`. Assert `env["GIT_TERMINAL_PROMPT"] == "0"` and
    `"BatchMode=yes" in env["GIT_SSH_COMMAND"]`.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/shared-config.test.py`
Expected: both FAIL.

- [ ] **Step 3: Implement**, then copy the file to the other plugin.

- [ ] **Step 4: Run**

Run: `python3 tools/test/shared-config.test.py && python3 tools/verify.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/*/hooks/shared-config.py tools/test/shared-config.test.py
git commit -m "fix(hooks): PyYAML이 없거나 git이 인증을 물어도 세션 시작을 막지 않는다"
```

### Task 5: The audits see nested sections

**Files:**
- Modify:
  - `plugins/fig/_common/scripts/audit-struct.js:35-45` and every later `for (const s of secs)`
  - `plugins/fig/_common/scripts/audit-flow.js:35-46`, `:53-55`, `:134`, `:170`
  - `plugins/fig/_common/scripts/audit-component.js:72`
  - `tools/verify.py`: a marker-copy check
- Create: `tools/test/audit-struct.test.js`
- Modify: `tools/test/audit-flow.test.js`, `tools/test/verify.test.py`

**Interfaces:**
- Produces, identical in all three audit scripts, between the lines `// <sections-deep>` and
  `// </sections-deep>`:
  - `sectionsDeep(nodes, skip, ox = 0, oy = 0, inherited = false) -> Array<{ s, ax, ay, skipped }>`
  - Every SECTION at any depth, with its absolute origin.
  - `skipped` is true when the section or any ancestor matches `skip`.
- `verify.py` FAILs with `[fig] sections-deep copies differ: {file}` when the marked blocks
  differ.

- [ ] **Step 1: Write the failing tests**
  - In `audit-struct.test.js`, reusing `audit-flow.test.js`'s `frame` / `run` style. Fixture: an
    outer section at (0, 0), sized 2000×2000, holding an inner section at (50, 50), sized 500×300,
    holding `A-Default` at (0, 0), `B-Default` at (200, 0) and `C-Default` at (5000, 5000).
    - `a frame outside a nested section is out of bounds` — the result includes a line matching
      `/\[bounds\] .*C-Default outside/`.
    - `top-level sections behave as before` — the existing single-section fixture still returns
      `"STRUCT PASS"`.
    - `excluded parent excludes nested sections` — with `CFG.pages.section_exclude` matching the
      outer name, there is no `[bounds]` line.
  - In `audit-flow.test.js`: `an arrow inside a nested section is audited`. The same fixture plus
    the vector `A-Default --> B-Default` from (100, 50) to (170, 50) reports `/target gap 30px/`.
    The well-formed version, ending at (190, 50), passes.
  - In `verify.test.py`: `sections-deep copies differ`. Change one character inside the marked
    block of `audit-flow.js` → exit 1.

  For `audit-component.js`, a parity test: a frame in a nested section produces the same findings
  as the same frame in a top-level section.

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tools/test/ && python3 tools/test/verify.test.py`
Expected: the new cases FAIL.

- [ ] **Step 3: Implement `sectionsDeep`** in each script, and replace the top-level section loops
  with it. In `audit-flow.js`, absolute frame coordinates become `ax + f.x` / `ay + f.y`, and
  `toAbs` uses `ax`/`ay`. Then add the marker check to `verify.py`.

- [ ] **Step 4: Run**

Run: `node --test tools/test/ && python3 tools/test/verify.test.py && bash plugins/fig/_common/scripts/lib/check.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/fig/_common/scripts/audit-*.js tools/test/audit-struct.test.js tools/test/audit-flow.test.js tools/verify.py tools/test/verify.test.py
git commit -m "fix(fig): 감사 스크립트가 중첩 섹션 안의 프레임과 화살표까지 본다"
```

### Task 6: An arrow's start is measured to the frame's edge, not its line

**Files:**
- Modify: `plugins/fig/_common/scripts/audit-flow.js` (the `dE` computation after :65)
- Test: `tools/test/audit-flow.test.js`

**Interfaces:**
- Produces: `distToEdge(p: {x, y}, R: {x, y, r, b}) -> number`. It returns the distance from `p`
  to the nearest point on the rectangle's boundary: for each of the four edge segments, the
  distance to its closest point after clamping, and the minimum of those.

- [ ] **Step 1: Write the failing test** `a start far along the edge's line is off the edge`. Use
  the vector `a_default --> b_default` with points (5000, 0), (5000, 50), (190, 50). The result
  includes `/start off the edge by/`. The existing `GOOD` fixture still passes.

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tools/test/audit-flow.test.js`
Expected: FAIL. Today this returns `"FLOW PASS"`.

- [ ] **Step 3: Implement `distToEdge`** and use it for `dE`.

- [ ] **Step 4: Run**

Run: `node --test tools/test/`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/fig/_common/scripts/audit-flow.js tools/test/audit-flow.test.js
git commit -m "fix(fig): 화살표 시작점을 프레임 변의 연장선이 아니라 변까지의 거리로 잰다"
```

### Task 7: Re-synced arrows keep their style

**Files:**
- Modify: `plugins/fig/_common/scripts/arrow-build.js` (`arrow()` at :52-71, and its callers'
  `opts` pass-through)
- Modify: `plugins/fig/skills/arrows/SKILL.md` (sync step 3, around :189)
- Create: `tools/test/arrow-build.test.js`

**Interfaces:**
- Produces:
  - `arrow(parent, name, pts, opts)`, where `opts` also takes `stroke: { color: {r,g,b},
    weight: number, dash: number[] | null }`. Any field present overrides `COLOR`, `WEIGHT` or
    `DASH`. `dash: null` means solid, even when `opts.dashed`.
  - `styleOf(vector) -> { stroke: { color, weight, dash }, bidirectional: boolean } | null`. It
    reads `strokes[0].color`, `strokeWeight` and `dashPattern` (empty → `null`), and is
    bidirectional when the first vertex's `strokeCap` equals `CAP.end`. It returns `null` when the
    vector has no SOLID stroke.

- [ ] **Step 1: Write the failing tests.** Build with
  `new Function("CFG", "figma", SRC + "\nreturn { arrow, styleOf };")`. The fake `figma` has
  `createVector()`, which returns a plain object whose `setVectorNetworkAsync(net)` stores `net`.
  - `stroke override is applied` — `arrow(parent, "a --> b", [[0,0],[10,0]], { stroke: { color:
    {r:1,g:0,b:0}, weight: 2, dash: [4,4] } })` sets `strokes[0].color` to `{r:1,g:0,b:0}`,
    `strokeWeight` to `2` and `dashPattern` to `[4,4]`.
  - `styleOf round-trips` — `styleOf` on that vector equals the stroke passed in, with
    `bidirectional: false`.
  - `styleOf on an unstroked vector is null` — `styleOf({ strokes: [] })` returns `null`.

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tools/test/arrow-build.test.js`
Expected: FAIL. `styleOf` is not defined.

- [ ] **Step 3: Implement both**, pass `opts` through every path helper, and reword arrows' sync
  step 3: "before deleting the old vector, read `styleOf(old)`; pass its `stroke` and
  `bidirectional` into the new arrow's `opts`; where it returns `null`, the config's style
  applies."

- [ ] **Step 4: Run**

Run: `node --test tools/test/ && bash plugins/fig/_common/scripts/lib/check.sh && python3 tools/verify.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/fig/_common/scripts/arrow-build.js plugins/fig/skills/arrows/SKILL.md tools/test/arrow-build.test.js
git commit -m "fix(fig): 화살표를 다시 그릴 때 기존 선 색·두께·점선·양방향을 그대로 옮긴다"
```

### Task 8: A script that renders the README pictures

**Files:**
- Create: `tools/render-images.sh`
- Modify: `CLAUDE.md`: one line in the "Anything crossing fig ↔ pm" row saying how pictures are
  re-rendered

**Interfaces:**
- Produces: `bash tools/render-images.sh [name ...]`. It renders `.github/<name>.html` to
  `.github/<name>.png` with headless Chrome: `--headless=new --hide-scrollbars
  --force-device-scale-factor=1 --screenshot`. `social-preview` uses `--window-size=1280,640`, and
  the diagrams use the width their HTML sets. With no names, it renders all of them. It stops with
  a clear message when no Chrome binary is found. It is not part of `verify-all.sh`, since CI has
  no Chrome.

- [ ] **Step 1: Run on one existing picture**

Run: `bash tools/render-images.sh social-preview && git diff --stat .github/social-preview.png`
Expected: the PNG is 1280×640 (`sips -g pixelWidth -g pixelHeight` or `file`), and visually the
same as before.

- [ ] **Step 2: Render the diagrams once**, and compare dimensions with the committed PNGs. Record
  the sizes in the script's header comment.

- [ ] **Step 3: Commit**

```bash
git add tools/render-images.sh CLAUDE.md
git commit -m "chore(tools): README 그림을 다시 뽑는 스크립트를 남긴다"
```

### Task 9: Release

**Files:**
- Modify: `plugins/fig/.claude-plugin/plugin.json` (3.26.0 → 3.27.0),
  `plugins/pm/.claude-plugin/plugin.json` (0.37.0 → 0.37.1), the matching `marketplace.json`
  entries, `plugins/fig/CHANGELOG.md`, `plugins/pm/CHANGELOG.md`
- Modify: the root READMEs' *What `/fig:lint` looks at* (nested sections are now read, and the
  start edge is measured to the edge), both languages, English first
- Modify: `CLAUDE.md` *What the checker catches*: mode files, `_common`, cross-plugin references,
  description length, the `sections-deep` copies

- [ ] **Step 1: Write the CHANGELOG entries.** Say what changed and why, per the repository's
  habit.
  - fig: nested sections in the audits, start-edge distance, arrow style kept.
  - pm: plugin identity and the hook.
- [ ] **Step 2: Run everything**

Run: `bash tools/verify-all.sh`
Expected: `· PASS`. WARN lines for long descriptions are expected.

- [ ] **Step 3: Commit**, then push the branch on its own (not chained).
- [ ] **Step 4: Preview the PR** — title, body, version bumps, CHANGELOG lines. Open it only after
  go.
