# Phase 2b — Local-first defaults, fig side Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With both plugins installed and no config, `fig` reads the PRD where `pm` writes it, and
`/fig:handoff` writes its line into pm's markdown task file. Without `pm`, everything still runs
and prints. The fig drafter stops writing defaults as if somebody chose them.

**Architecture:**
- One fig script, `borrow-pm.py`, holds every decision that crosses into `pm`:
  - finding the installed `pm`, and its version
  - the PRD source order of design §3
  - the tracker table of design §4

  Skills call it and act on its JSON. They do not re-derive the rules in prose.
- It reads pm's config by running pm's own `resolve-config.py`, so pm's floor is the one applied.
  It writes through pm's `markdown-tracker.py`, from 2a.
- fig's floor changes three values. The shared `resolve-config.py` and `preflight.py` gain fig's
  rows and stay byte-identical across both plugins.
- The picture script gains a stdlib PNG trim, so re-rendered pictures end on one bottom margin.

**Tech Stack:** Python 3 (stdlib, PyYAML), Node `node:test`, bash, headless Chrome (pictures
only), the `claude plugin` CLI (installed-pair proof only).

**Spec:** On branch `worktree-local-first-design`:
`docs/design/2026-10-18-local-first-defaults.md` §3 and §4, with decisions 3, 4 and 4a, designer's
calls 1–4, 6, 9 and 11, the anti-goals and *Done when*; `docs/design/2026-10-18-skill-review.md`
S2 (fig half), S7 (`component_audit.body_offset` → null), S8 (pm's version when fig borrows), Bin
A 3, and the fig setup appendix rows these touch;
`docs/superpowers/plans/2026-10-18-skills-overhaul-roadmap.md`, Phase 2 and *Release and surfaces,
every phase*.

**Split.** Second of two plans; the first is `2026-10-19-phase2a-pm-local-first.md`, and why they
split is there. This plan needs 2a merged and released. `PM_MIN` is 2a's pm version, and the
tracker calls are 2a's frozen interface.

**Deliberate deviations from the design, and why:**
- **The heading.** A null `task_tracker.ui_section_heading` writes under the fixed heading
  `Design changes`, not "Design changes in `meta.language`" (designer's call 10). `meta.language`
  ships `auto`, so a run in one language and a later run in another would each add their own
  heading. That is the review's S14 finding. Phase 3 (S14) replaces the fixed heading with a key
  both plugins read.
- **"Never call each other" is reworded here, not in Phase 3.** This plan is what makes it false.
  The repository's own sentences about what changed ship with the change (roadmap, *Release and
  surfaces*). The words are §10's.

## Global Constraints

- Start after 2a merges: branch from the latest `origin/main`.
  - Line numbers in fig files 2a did not touch are against `c868dad`.
  - The shared `resolve-config.py` and `preflight.py`, and pm's README, changed in 2a. They are
    cited by function or heading.
- Commit messages are Korean, `type(scope): what changed, in a sentence`. Documents and code
  comments are English.
- `SHARED` files (verify.py:46-47) stay byte-identical. Change the fig copy, then `cp` it to pm.
- No team-specific value in any shipped file or in this plan. Prose never carries a skill count.
- Versions: fig `3.27.1 → 3.28.0`. pm `0.38.0 → 0.38.1`, for its shared copies and its README.
  Both get CHANGELOG entries.
- Every SKILL.md this plan edits leaves with a `description` of 500 characters or fewer.
  - The touched skills: setup, draw, sketch, qa, handoff, arrows.
  - `/fig:diff` is exempt. It changes by one table row here, and Phase 3 removes it.
- `PM_MIN = "0.38.0"`. Where `pm` is older, missing or disabled, nothing is written through it.
  The run prints and says why.
- The rule from design §4, unchanged: a preflight requirement comes only from a value a person
  wrote. With no config at all, fig's preflight still ends early with PASS.
- Every write outside this repository is preview → go. Run `bash tools/verify-all.sh` before
  pushing, never chained to a push. `tools/team-strings.local.txt` is never committed.

## Review Focus

1. **`pm` installed but disabled** (`enabledPlugins` false). It counts as not installed: handoff
   prints with the install note, and nothing is written into a task file.
   → Task 2 `pm disabled in settings → treated as not installed`.
2. **A missing or malformed plugin registry.** Print plus the note, never a traceback.
   → Task 2 `no registry → print with the install note`, `malformed registry → print, no traceback`.
3. **A fig config with no `task_tracker`, beside a pm config on Notion.** It prints and writes
   nothing — the design's "no silent new writes".
   → Task 2 `unset + pm record on notion → print`.
4. **A team config whose `qa.baseline.prd` is still a plain string.** It reads as Notion, and
   preflight still requires the Notion connector.
   → Task 2 `prd: legacy string → notion`; Task 3 `legacy string qa.baseline.prd → Notion required`.
5. **`pm` older than `PM_MIN`.** Handoff prints with "update pm". The PRD lookup skips pm's
   folder and says so.
   → Task 2 `pm below PM_MIN → print with the update note`, `prd: pm below PM_MIN → none, note`.

---

### Task 1: fig's floor — the PRD as `{type, ref}`, the tracker unset, no team's shell offset

**Files:**
- Modify: `plugins/fig/_common/conventions.example.yaml`
  - `component_audit.body_offset` at :159
  - `task_tracker` at :212-219, values and comments
  - `qa.baseline.prd` at :241-244
- Modify, byte-identical in both plugins: `plugins/{fig,pm}/_common/scripts/lib/resolve-config.py`.
  `AUTHORED_WITH` gains fig's pair.
- Test: `tools/test/resolve-config.test.py` (on the fig copy), `tools/test/audit-component.test.js`

**Interfaces:**
- Produces these floor values:
  - `component_audit.body_offset: null`. The comment says it is the shared shell's width and
    height, measured on one screen (`{left, top}`), and that null exempts nothing.
    `audit-component.js:29` already reads null as `{0, 0}`.
  - `task_tracker.type: null`. The comment carries the four cases:
    - unset borrows pm's task record only where it is markdown
    - `markdown` writes through pm
    - `none` prints
    - `notion` or `github` as before
  - The `ui_section_heading` comment: null writes under `Design changes`.
  - `qa.baseline.prd: {type: markdown, ref: null}`. The comment says:
    - the types are `markdown | notion | none`
    - a `ref` is a file, a folder of one file per product, or a Notion page or collection url
    - a plain string is read as `{type: notion, ref: <string>}`
    - an explicit `null`, or `type: none`, means no PRD, and pm is not consulted
    - `ref: null` means pm's PRD where pm is installed
- Produces in `resolve-config.py`: `AUTHORED_WITH` gains
  `("task_tracker.type", "task_tracker.ref", frozenset())`.

- [ ] **Step 1: Write the failing tests.** In `resolve-config.test.py`, run fig's copy under the
  `bare` home:
  - `fig floor: the local defaults` — `component_audit.body_offset is None`,
    `task_tracker.type is None`, `qa.baseline.prd == {"type": "markdown", "ref": None}`.
  - `fig paired: task_tracker.ref without type → --authored stops`. Project layer
    `figma-conventions.yaml` = `task_tracker:\n  ref: x\n`. `--authored task_tracker.type` gives
    rc 3, and stderr contains `task_tracker.type is not set in figma-conventions.yaml, while
    task_tracker.ref is`.

  In `audit-component.test.js`, reuse `STAT`, `screen` and `section`, with the instance moved to
  `absoluteBoundingBox {x: 10, y: 10, …}`:
  - `body_offset null examines the whole frame` — CFG `body_offset: null` reports one `[default]`.
  - `a set body_offset still exempts the shell` — CFG `body_offset: {left: 270, top: 120}` reports
    none.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/resolve-config.test.py; node --test tools/test/audit-component.test.js`
Expected: the `fig floor` and `fig paired` cases FAIL. Both audit-component cases already pass;
they pin behaviour that the floor change now relies on.

- [ ] **Step 3: Change the floor and the pair**, then
  `cp plugins/fig/_common/scripts/lib/resolve-config.py plugins/pm/_common/scripts/lib/`.

- [ ] **Step 4: Run**

Run: `python3 tools/test/resolve-config.test.py && node --test tools/test/*.test.js && python3 tools/verify.py`
Expected: PASS. A team config holding a string `qa.baseline.prd` still passes verify's schema
check, because `qa.baseline.prd` remains a known path.

- [ ] **Step 5: Commit**

```bash
git add plugins/fig/_common/conventions.example.yaml plugins/*/_common/scripts/lib/resolve-config.py tools/test/resolve-config.test.py tools/test/audit-component.test.js
git commit -m "feat(fig): PRD 위치를 종류와 참조로 받고, 트래커는 비워 두며, 한 팀의 셸 여백을 기본값에서 뺀다"
```

### Task 2: `borrow-pm.py` — find pm, check its version, decide what fig borrows

**Files:**
- Create: `plugins/fig/_common/scripts/lib/borrow-pm.py`
- Create: `tools/test/borrow-pm.test.py`

**Interfaces:**
- Consumes (2a, verbatim):

```
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py <op> ...
  slug NAME                                   stdout: the slug
  list --dir DIR                              stdout: one JSON object per record, sorted by path
  new --dir DIR --title TITLE [--set KEY=VALUE]... [--row LABEL=VALUE]... [--link-key KEY]
                                              stdout: the new file's path
  set-link --path FILE --key KEY --value VALUE
  append-under --path FILE --heading TEXT --line TEXT
  moved --dir DIR --date YYYY-MM-DD [--today YYYY-MM-DD]
                                              stdout: {"paths": [...], "method": "git+uncommitted"|"git"|"mtime"|"none"}
exit 0 done · 1 usage · 2 DIR exists and is not a directory · 4 FILE missing (set-link: or without front matter)
```

  `${CLAUDE_PLUGIN_ROOT}` there is pm's root, so from fig the path is the `script` value below.
  Also consumed:
  - Two runs of `append-under` give one heading.
  - pm's PRD file rules (2a Task 7):
    - `{dir}/{slug(product)}.md`
    - or `{dir}/{slug(product)}/index.md` plus `{slug(domain)}.md`
    - front matter `product` and `domain`
  - pm's floor: `task.record` markdown at `./tasks`; `prd.target: markdown`;
    `prd.markdown.dir: "./docs/prd"`; `split: product`.
- Produces — module constants and functions, importable by `preflight.py` (Task 3):
  - `PM_MIN = "0.38.0"`, `HEADING = "Design changes"`.
  - `def config_dir(env: dict) -> str` — `env["CLAUDE_CONFIG_DIR"]` if set, else `~/.claude`.
  - `def find_pm(env: dict, cwd: str) -> dict | None` — returns `{"root": str, "version": str}`,
    or None. Order:
    1. `env["FIG_PM_ROOT"]`, for a `--plugin-dir` session or a test.
    2. `{config_dir}/plugins/installed_plugins.json`. Its format is
       `{"version": 2, "plugins": {"pm@<marketplace>": [{"scope", "installPath", "version",
       "projectPath"?}]}}`.
       - Take the first entry whose scope is `user`, or whose `projectPath` is `cwd` or one of
         its parents.
       - Prefer the marketplace fig itself came from: the `<marketplace>` of the `fig@…` entry
         whose `installPath` contains this script. Otherwise take the first match.

    The candidate must hold `.claude-plugin/plugin.json` named `pm`. Its `version` comes from that
    file, not from the registry. pm is not installed when `enabledPlugins["pm@<marketplace>"]` is
    `false` in any of these, read in order with the later one winning:
    - `{config_dir}/settings.json`
    - `{cwd}/.claude/settings.json`
    - `{cwd}/.claude/settings.local.json`

    A missing, unreadable or malformed file is treated as absent. It never raises.
  - `def version_ok(version: str, minimum: str = PM_MIN) -> bool` — compares as numeric tuples.
    A non-numeric part is False.
  - `def spec_kind(value: str, cwd: str) -> tuple[str, str]` — returns one of:
    - `("markdown", value)` where the part before `#` is an existing `.md` file
    - `("notion", value)` for a `notion.so` or `notion.site` url, or 32 hex digits with or without
      dashes
    - `("figma", value)` for any `figma.com` url
    - `("unknown", value)` otherwise
  - CLI: `borrow-pm.py where | prd [--spec-url V] [fileKey] | task [fileKey]`, printing one JSON
    object.
    - fig's config comes from running fig's own `resolve-config.py` as a subprocess. For `task` it
      adds `--authored task_tracker.type`, so the paired-key message is the one every skill
      prints.
    - pm's config comes from running `{pm root}/_common/scripts/lib/resolve-config.py --name
      pm-conventions.yaml --authored task.record.type` in `cwd`. Never fig's copy: each copy finds
      the floor beside itself.
    - pm's adapter path comes from `{pm root}/_common/scripts/lib/adapter.py --name
      pm-conventions.yaml --kind trackers --type markdown --role record`.
    - `where` → `{"root": str|null, "version": str|null, "ok": bool}`.
    - `prd` → `{"type": "markdown"|"notion"|"none", "ref": str|null, "from":
      "spec_url"|"qa.baseline.prd"|"pm"|null, "split": "product"|"domain"|null, "candidates":
      [{"path", "product", "domain"}], "note": str|null}`.
      - Order:
        1. `--spec-url`, read by `spec_kind`.
        2. `qa.baseline.prd`:
           - a string → notion
           - `null` or `type: none` → `none`, and stop
           - a non-null `ref` → its type
        3. pm, with `version_ok` true and its `prd.target` markdown or git → `prd.markdown.dir`.
        4. `none`.
      - Candidates list the `.md` files under a markdown folder ref or under pm's dir, by split.
        `product` comes from front matter, else the file stem (split product) or the folder name
        (split domain).
    - `task` → `{"action": "write"|"print"|"notion"|"github", "dir": str|null, "heading": str,
      "script": str|null, "adapter": str|null, "note": str|null}`.
      - `heading` is `task_tracker.ui_section_heading`, or `HEADING`.
      - `script` is `{pm root}/_common/scripts/lib/markdown-tracker.py`.
      - The table:
        - type null, pm ok, pm `task.record.type` markdown → `write`, `dir` = pm's
          `task.record.ref`
        - type null, pm ok, any other record type → `print`, with a note that fig writes only into
          pm's markdown task files
        - `markdown`, pm ok → `write`, `dir` = `task_tracker.ref` or else pm's `task.record.ref`
        - null or `markdown`, pm missing or disabled → `print`, note
          `Installing pm writes this line into the task file.`
        - null or `markdown`, pm below `PM_MIN` → `print`, with a note naming the installed
          version, `PM_MIN`, and "update pm"
        - pm's own guard exits 3 → `print`, with a note quoting the first stderr line
        - `none` → `print`, note null
        - `notion`, `github` → that action
    - Exits:
      - 0 for every result above
      - 3 when fig's guard fires; stderr is passed through
      - 6 when `--spec-url` is a figma link ("not read as a PRD yet") or `unknown` ("cannot tell
        what kind of document this is"), said on stderr

- [ ] **Step 1: Write the failing tests** in `tools/test/borrow-pm.test.py`. Fixtures:
  - a temp `CLAUDE_CONFIG_DIR`, a temp `HOME`, and `PYTHONUSERBASE` pinned
  - `plugins/pm` copied to `<cfg>/plugins/cache/m/pm/<ver>`
  - a registry naming it as `pm@m`, scope `user`
  - a temp cwd holding each case's configs
  - `FIG_PM_ROOT` unset unless stated

| Test name | Setup | Assert |
|---|---|---|
| `no registry → print with the install note` | empty config dir | `task`: action `print`, note contains `Installing pm` |
| `malformed registry → print, no traceback` | registry file = `{` | rc 0; action `print`; no `Traceback` on stderr |
| `pm disabled in settings → treated as not installed` | `settings.json` = `{"enabledPlugins": {"pm@m": false}}` | action `print`, note contains `Installing pm` |
| `pm below PM_MIN → print with the update note` | the copy's `plugin.json` version `0.37.1` | action `print`; note contains `0.38.0` and `update` |
| `FIG_PM_ROOT overrides the registry` | no registry; `FIG_PM_ROOT` = the copy | `where`: `ok` true |
| `unset + pm markdown → write into pm's task dir` | no configs | action `write`; `dir == "./tasks"`; `heading == "Design changes"`; `script` ends `markdown-tracker.py`; `adapter` ends `trackers/markdown.md` |
| `unset + pm record on notion → print` | `pm-conventions.yaml`: record notion + ref + `link_property: Ticket` | action `print`; nothing is created under cwd |
| `markdown + pm → write into task_tracker.ref` | `figma-conventions.yaml`: `task_tracker: {type: markdown, ref: ./work}` | `dir == "./work"` |
| `markdown without pm → print with the install note` | same, empty config dir | action `print` |
| `none → print, no note` | `task_tracker: {type: none}` | action `print`; note null |
| `ref without type → exit 3` | `task_tracker: {ref: x}` | rc 3; stderr contains `task_tracker.type is not set` |
| `a set heading is used` | `task_tracker: {ui_section_heading: Handover}` | `heading == "Handover"` |
| `prd: legacy string → notion` | `qa: {baseline: {prd: "0123456789abcdef0123456789abcdef"}}` | type `notion`; from `qa.baseline.prd` |
| `prd: explicit null → none, pm not tried` | `qa: {baseline: {prd: null}}`; pm installed; a PRD file exists | type `none`; from null |
| `prd: floor + pm → pm's files` | `docs/prd/store-app.md` with front matter `product: Store App` | type `markdown`; from `pm`; one candidate with product `Store App` |
| `prd: split domain → the product folder` | pm config `prd: {markdown: {split: domain}}`; `docs/prd/store-app/index.md`, `docs/prd/store-app/payments.md` | split `domain`; two candidates; `payments.md` has domain `payments` |
| `prd: pm below PM_MIN → none, note` | old copy; a PRD file exists | type `none`; note contains `update` |
| `prd: spec_url .md → markdown` | `--spec-url docs/x.md#entry-3`, with the file present | type `markdown`; ref keeps `#entry-3` |
| `prd: spec_url 32-hex → notion` | `--spec-url 0123…` (32 hex) | type `notion` |
| `prd: spec_url figma → exit 6` | `--spec-url https://www.figma.com/design/abc/x` | rc 6 |

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/borrow-pm.test.py`
Expected: every case fails — the script does not exist.

- [ ] **Step 3: Implement `borrow-pm.py`** to the interface above.

- [ ] **Step 4: Run**

Run: `python3 tools/test/borrow-pm.test.py && bash plugins/fig/_common/scripts/lib/check.sh && python3 tools/verify.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/fig/_common/scripts/lib/borrow-pm.py tools/test/borrow-pm.test.py
git commit -m "feat(fig): 설치된 pm과 그 버전을 찾아 PRD와 일감 파일을 빌려 쓸지 한곳에서 정한다"
```

### Task 3: preflight reads the PRD source and the borrowed tracker

**Files:**
- Modify, byte-identical in both plugins: `plugins/{fig,pm}/_common/scripts/lib/preflight.py`
  - `NAMED_TOOLS["fig"]`, at :84-88 in `c868dad`
  - `settle_requirements()`: the type lookup and a new attention row
- Test: `tools/test/preflight.test.py`, fig cases run on `plugins/fig/_common/scripts/lib/preflight.py`

**Interfaces:**
- Consumes: `find_pm`, `version_ok` and `PM_MIN` from `borrow-pm.py` (Task 2). They are loaded
  with `importlib` from `HERE`, only where `PLUGIN == "fig"` and the file exists.
- Produces:
  - `NAMED_TOOLS["fig"]`:
    - `task_tracker` row: its quiet set becomes `{"none", "markdown"}`
    - new row: `(("qa.baseline.prd",), "qa.baseline.prd.type", {"none", "markdown"}, None)`
  - `LEGACY_STRING = {"qa.baseline.prd.type": ("qa.baseline.prd", "notion")}`. Where the type
    key resolves to None and its parent is a string, the type is the mapped value.
  - Where the user wrote `task_tracker.type: markdown` and `find_pm` returns None, a row
    `("tracker", "task_tracker.type: markdown", "attention", "pm is not installed here —
    /fig:handoff prints its line instead of writing it into the task file")`.
  - Where pm is found but `version_ok` is false, the same row with `pm {version} is older than
    {PM_MIN} — …`.
  - The verdict is never FAIL for that row.

- [ ] **Step 1: Write the failing tests** (fig's copy, temp `HOME`, an empty temp
  `CLAUDE_CONFIG_DIR`)

| Test name | `proj/figma-conventions.yaml` | Assert |
|---|---|---|
| `legacy string qa.baseline.prd → Notion required` | `qa:\n  baseline:\n    prd: "0123456789abcdef0123456789abcdef"\n` | `needed because` line contains `qa.baseline.prd.type: notion` |
| `qa.baseline.prd markdown → nothing required` | `prd: {type: markdown, ref: ./docs/prd}` under `qa.baseline` | `needed because` line contains `name no tool` |
| `task_tracker markdown without pm → attention, not FAIL` | `task_tracker:\n  type: markdown\n` | a `Worth knowing` line contains `pm is not installed`; last line does not end `FAIL` |
| `task_tracker.ref without type → FAIL naming the key` | `task_tracker:\n  ref: x\n` | last line ends `· FAIL`; a `Fix first` line contains `task_tracker.type` |
| `fig, no config → nothing needed yet` | none | first line contains `Nothing is needed yet` |

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/preflight.test.py`
Expected: the first and third cases FAIL. The fourth passes from Task 1's pair; keep it as a
guard.

- [ ] **Step 3: Implement**, then copy fig's file to pm.

- [ ] **Step 4: Run**

Run: `python3 tools/test/preflight.test.py && python3 tools/verify.py`
Expected: PASS, with no `[shared]` divergence.

- [ ] **Step 5: Commit**

```bash
git add plugins/*/_common/scripts/lib/preflight.py tools/test/preflight.test.py
git commit -m "feat(shared): 프리플라이트가 PRD 위치의 옛 문자열 형식과 pm 없는 마크다운 트래커를 읽는다"
```

### Task 4: The fig drafter writes only what it observed, and setup asks the rest

**Files:**
- Modify: `plugins/fig/_common/scripts/lib/draft-conventions.py`
  - argument parsing at :42-50: `--file-key` is required
  - naming at :73-89
  - pages at :92-102
  - layout at :121-124
  - section style at :135-138
  - placeholder at :153-155
  - arrows at :169-191
  - the tail at :194-222
- Modify: `plugins/fig/skills/setup/SKILL.md`
  - :1-4: description
  - :111-121: the draft command takes `--file-key {fileKey}`
  - :123-136: the interview table
  - :138-140: the write
  - :271: the note
- Test: `tools/test/draft-conventions.test.py`

**Interfaces:**
- Produces: `draft-conventions.py --file-key KEY probe1.json …`. Without `--file-key` it exits
  non-zero with a usage line. Every leaf it writes is one of two kinds:
  - **(a) observed:** its line comment carries evidence matching
    `\d+/\d+|0 observed|too few|split|observed`.
  - **(b) an interview key left null:** one of `INTERVIEW_KEYS`:
    - `naming.required_states`
    - `layout.section_padding`
    - `layout.reference_frame_width`
    - `arrows.trunk`
    - `arrows.trunk_to_target_min`
    - `arrows.parallel_offset`
    - `arrows.label.offset_from_target`
- These lines are no longer written. The floor covers them, or setup asks:
  - **Naming:**
    - `naming.arrow_delimiter`
    - `naming.state_chain_delimiter`
    - `naming.label_prefix`
    - `naming.state_chain_prefix`
    - the common and pattern page keys, except where candidates were observed
  - **Pages:** every top-level `pages` key.
  - **Layout:** `layout.section_resize_margin` (`[80, 160]` was never the floor) and
    `layout.row_bucket`.
  - **Placeholder:** `placeholder_style.font`, `.text_color` and `.text_prefix`.
  - **Arrows:** `arrows.cap`, `arrows.audit.edge_tolerance` and `.label_clear`.
  - **Whole blocks:** `component_audit` and `design_system`.
  - **Sync:** `sync.pair_patterns`, except in the non-ASCII branch; `text_diff_max_len` and
    `version_page_pattern`.
  - **The rest:** `task_tracker`, `tools`, `guide_source`, and a top-level `files: {}`.
- Observed exclusion candidates go to `files.{KEY}.pages.exclude_sections`, with their evidence
  comment.
- Every observed line that lacks an evidence comment today gains one:
  - `frame_pattern`, `section_pattern`
  - `fill_opacity`, `stroke_weight`, `stroke_align`
  - the label's `corner_radius`, `fill`, `stroke` and `text_color`
  - `dash_conditional` (as `n/m arrows dashed`)
  - `gap_range` (`head_gap ±3 — n/m`)
- Setup's interview table gains three rows:
  - `layout.reference_frame_width` — "the screen width"
  - `qa.baseline.prd` — "Where is the PRD? pm's (installed alongside: leave it unset, fig reads
    it) · a markdown file · a Notion page · none"
  - `task_tracker` — "Where does the handover line go? pm's task files (installed alongside: leave
    it unset) · Notion · GitHub · nowhere". `task_tracker · design_system` leaves the "Facts that
    live outside the file" row.

  Answers for `pages.strict`, `free`, `readonly` and the three sync axes are written under
  `files.{fileKey}.pages`. Line :271 says that is where the draft puts them.

- [ ] **Step 1: Write the failing tests.** `run()` passes `--file-key ABC123`. One tidy probe gains
  a section named `Template`.
  - `every leaf is observed or an interview key`. Walk the output text and build each leaf's dotted
    path from indentation. Assert the path is in `INTERVIEW_KEYS`, or that the evidence regex
    matches the leaf's own comment or the comment of its nearest parent line. That way a block
    such as `pair_patterns:` vouches for its children.
  - `non-ASCII names → pair_patterns under an evidence comment`. Add a probe whose page is named
    `Menü`; the non-ASCII branch writes `sync.pair_patterns`. Run the leaf rule above on that
    output too.
  - `no top-level pages, task_tracker, tools, guide_source, design_system, component_audit` — none
    of these keys is in `cfg`.
  - `exclusion candidates under the file key` —
    `cfg["files"]["ABC123"]["pages"]["exclude_sections"] == ["^Template$"]`.
  - `--file-key missing → refuses` — rc != 0.
  - Replace `strict pages left empty — a person decides` with
    `no page rules at the top level — a person decides, per file`.
  - Keep `every key the draft writes is one verify accepts`. `files.` is a free map.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/draft-conventions.test.py`
Expected: FAIL on the new cases.

- [ ] **Step 3: Implement**, then edit setup's procedure and table as above.

- [ ] **Step 4: Run**

Run: `python3 tools/test/draft-conventions.test.py && python3 tools/verify.py`
Expected: PASS, with no description WARN for `fig:setup`.

- [ ] **Step 5: Commit**

```bash
git add plugins/fig/_common/scripts/lib/draft-conventions.py plugins/fig/skills/setup/SKILL.md tools/test/draft-conventions.test.py
git commit -m "fix(fig): 설정 초안이 관찰한 값만 적고, 파일별 페이지 규칙은 files 아래에 둔다"
```

### Task 5: draw, sketch and qa read the PRD wherever it is

**Files:**
- Modify: `plugins/fig/skills/draw/SKILL.md`
  - :3-4: description; `Read` and `Glob` added to `allowed-tools`
  - :38: `spec_url`
  - :46: the sections read
  - :144-146: step 2
- Modify: `plugins/fig/skills/sketch/SKILL.md`
  - :3-4: description; `Read` and `Glob` added
  - :31: `spec_url`
  - :33-37: config
- Modify: `plugins/fig/skills/qa/SKILL.md`
  - :3-4: description; `Bash`, `Read` and `Glob` added
  - a new *Where the rules come from* section before *1. Settle the target* at :44
  - step 2 at :55-68

**Interfaces:**
- Consumes: `borrow-pm.py prd` (Task 2).
- Produces, in draw, sketch and qa, the same lookup:
  `python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/borrow-pm.py prd [--spec-url {spec_url}] {fileKey}`.
  qa takes no `spec_url` and starts at step 2 of the order. It first gains
  `resolve-config.py --js {fileKey}`, since its body never resolved config before. Then:
  - `markdown` with one candidate → `Read` it. With several → ask which, offering the products.
  - split `domain` → read `index.md` and the domain file the target belongs to.
  - `notion` → `notion-fetch` the ref.
  - `none`:
    - draw asks for a source or records that there is none, as today
    - sketch goes on and says so
    - qa marks every item `needs confirmation`
  - exit 6 → say what it printed and ask for another source.
  - a `note` → one line in the response.

  The old "Omitted, `qa.baseline.prd` from the config is used" sentences at draw:38 and sketch:31
  become "omitted, the lookup decides: the config, then pm's PRD where pm is installed".

- [ ] **Step 1: Edit draw, sketch and qa** as above.

- [ ] **Step 2: Verify**

Run: `grep -c "borrow-pm.py prd" plugins/fig/skills/{draw,sketch,qa}/SKILL.md && python3 tools/verify.py`
Expected: at least 1 in each file. PASS, with no description WARN for draw, sketch or qa.
`verify.py` finds the `${CLAUDE_PLUGIN_ROOT}/…` path.

- [ ] **Step 3: Commit**

```bash
git add plugins/fig/skills/draw/SKILL.md plugins/fig/skills/sketch/SKILL.md plugins/fig/skills/qa/SKILL.md
git commit -m "feat(fig): 그리기·스케치·QA가 노션뿐 아니라 마크다운 PRD와 pm의 PRD를 읽는다"
```

### Task 6: handoff writes into a markdown task file; diff reads an unset tracker as none

**Files:**
- Modify: `plugins/fig/skills/handoff/SKILL.md`
  - :3: the description says where the line goes; still 500 characters or fewer
  - :39-42: a new optional input `task`
  - :44-50: where the rules come from
  - :101-118: preview, write and read back
  - :133-135: the report
- Modify: `plugins/fig/skills/diff/SKILL.md`
  - :38: its config line resolves with `--authored task_tracker.type`, so a ref written without
    its type stops here too (designer's call 6)
  - :107-114: a row `unset (null) | — | As none.`
- Modify: `plugins/pm/_common/trackers/README.md`
  - the *Appending a line under a heading* row (added in 2a) names `/fig:handoff` beside
    `/pm:task-publish`
  - :75 adds that `/fig:handoff` writes its one line into a markdown record through
    `append-under`; the `/fig:diff` sentence stays until Phase 3

**Interfaces:**
- Consumes: `borrow-pm.py task` (Task 2), and `markdown-tracker.py list` / `append-under` through
  its `script` value.
- Produces, in handoff:
  - **Input `task`, optional:** a Notion page url, a GitHub issue, or a task file's path.
  - **Rules:** `borrow-pm.py task {fileKey}` replaces "`task_tracker.type` … `none` writes none".
    Its `action` decides:
    - `write`:
      - The task file is the `task` input. Without one, pick from
        `python3 {script} list --dir {dir}`: one record whose title clearly matches → use it and
        say which; otherwise ask.
      - `list` prints nothing (the folder is missing or empty, so no task exists yet) → handle it
        as `print`, with the note "no task file yet — `/pm:task-draft` makes one, and the next
        handoff writes into it".
      - The preview names the file and shows the line under `{heading}`.
      - After go: `python3 {script} append-under --path {file} --heading "{heading}" --line "{line}"`.
      - Read back: `Read` the file; the line sits under the heading, once.
    - `print`: the line in the response, plus `note` where there is one.
    - `notion`, `github`: unchanged — the method `/fig:diff` uses.
    - exit 3: stop, naming the setting the message names.
  - **The line's content is unchanged:** the links, "handed over {date}, {n} sections", and the
    pinned version as `handoff.version.ref`.
  - **Report `[task doc]`:** the file, the page, "printed — {note}", or "no tracker configured".

- [ ] **Step 1: Edit both skills** as above.

- [ ] **Step 2: Verify**

Run: `grep -c "borrow-pm.py task" plugins/fig/skills/handoff/SKILL.md; grep -c "append-under" plugins/fig/skills/handoff/SKILL.md; python3 tools/verify.py`
Expected: at least 1 and at least 1. PASS.

- [ ] **Step 3: Commit**

```bash
git add plugins/fig/skills/handoff/SKILL.md plugins/fig/skills/diff/SKILL.md plugins/pm/_common/trackers/README.md
git commit -m "feat(fig): 핸드오프가 pm의 마크다운 일감 파일에 한 줄을 남기고, pm이 없으면 출력하고 이유를 말한다"
```

### Task 7: Re-rendered pictures end on one bottom margin

The carried-over task statement said `render-images.sh` renders 8–40 px too tall. The measurement
on 2026-10-19 says otherwise.
- Each diagram's height is its deepest content plus the 48 CSS px bottom padding its own CSS
  declares. That is what the script renders today.
- The committed PNGs disagree with that CSS, and with each other:

  | Committed PNG | Trailing background rows at 2000 px | In CSS px |
  |---|---|---|
  | five of the six diagrams | 37–38 | about 26 |
  | two-plugins | 67 | about 47 |

  No measuring rule reproduces both.

So the script is not changed to measure differently. It trims every re-render to one margin:
26 CSS px, the majority.

**Files:**
- Create: `tools/png-trim.py`
- Modify: `tools/render-images.sh`
  - the header at :11-41: the measured facts above replace the committed-versus-rendered table
  - `render()` at :97-117: a trim after the screenshot, before `QUANTIZE`; the report line
- Create: `tools/test/png-trim.test.py`

**Interfaces:**
- Produces:
  - `python3 tools/png-trim.py FILE --keep N` rewrites FILE so exactly N trailing rows equal its
    last row. A file with N or fewer is left byte for byte. It prints `{w}x{h} -> {w}x{h2}`.
  - `python3 tools/png-trim.py FILE --count` prints `{w}x{h} trailing={n}` and never writes.
  - It handles only non-interlaced 8-bit colour type 2 (RGB) and 6 (RGBA), which is what Chrome
    writes. Anything else exits 2 with `unsupported PNG`, and the file is untouched.
  - `def trailing_rows(rows: list[bytes]) -> int`.
  - In `render-images.sh`:
    - `BOTTOM_CSS=26`.
    - Every picture but `social-preview` is trimmed with `--keep` set to `BOTTOM_CSS × scale`,
      rounded: 37 for the 2000 px diagrams, 26 for `arrows-before-after`.
    - The report line adds the trailing count and the committed picture's size, read from
      `git show HEAD:.github/{name}.png`.

- [ ] **Step 1: Write the failing tests** in `tools/test/png-trim.test.py`. They use a small
  stdlib PNG writer (`zlib`, `struct`, `binascii.crc32`) defined in the test file.

| Test name | Input | Assert |
|---|---|---|
| `keep trims trailing rows` | 10×50 RGB; rows 0–9 black, 10–49 white; `--keep 5` | height 15; `--count` prints `trailing=5` |
| `keep never adds rows` | 10×12 RGB with 2 white trailing rows; `--keep 5` | bytes unchanged |
| `RGBA is handled` | the first case as colour type 6 | height 15 |
| `palette PNG → exit 2, untouched` | colour type 3 | rc 2; bytes unchanged |

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/png-trim.test.py`
Expected: every case fails — no script.

- [ ] **Step 3: Implement** `png-trim.py`, and wire it into `render-images.sh`.

- [ ] **Step 4: Run, then check on one real picture**

Run:
```bash
python3 tools/test/png-trim.test.py
bash tools/render-images.sh config-layers
python3 tools/png-trim.py .github/config-layers.png --count
git checkout -- .github/config-layers.png
```
Expected:
- the tests PASS
- the render reports `trailing=37`, with a height within 10 px of the committed 1364
- the restore leaves `config-layers.png` as committed, since this phase does not change its
  content

- [ ] **Step 5: Commit**

```bash
git add tools/png-trim.py tools/render-images.sh tools/test/png-trim.test.py
git commit -m "fix(tools): 다시 뽑은 그림의 아래 여백을 한 값으로 잘라 그림마다 끝이 같게 한다"
```

### Task 8: Release 2b

**Files:**
- Modify the versions and descriptions:
  - `plugins/fig/.claude-plugin/plugin.json`: `3.27.1 → 3.28.0`, and the description below
  - the fig entry in `.claude-plugin/marketplace.json`, the same description
  - `plugins/pm/.claude-plugin/plugin.json`: `0.38.0 → 0.38.1`
- Modify both CHANGELOGs: `plugins/fig/CHANGELOG.md` and `plugins/pm/CHANGELOG.md`.
- Modify `plugins/fig/README.md`:
  - the cycle at :15-27 and the table rows for `/fig:setup`, `/fig:draw`, `/fig:handoff` and
    `/fig:qa` at :44-58, where what they read or write changed
  - *The other half* at :105-115
- Modify `plugins/pm/README.md`, *The other half*: "The two never call each other" and
  "set `qa.baseline.prd`… and `task_tracker.ref`" become the borrowing defaults.
- Modify `README.md`, English first, then `README.ko.md` at the same places. 2a moved these lines,
  so they are cited by heading:
  - *The skills* (under fig) and the cycle paragraphs above it: the rows and sentences for setup,
    draw, handoff and qa, where what they read or write changed.
  - *What each skill needs*: a row for `/fig:draw` `/fig:sketch` `/fig:qa` `/fig:handoff` —
    **pm** is optional; installed alongside (0.38.0 or later), its PRD and its markdown task files
    are read and written.
  - *What `/fig:lint` looks at*, the mode-check paragraph: "whatever mode the screen, any section
    it sits in, or its page names".
  - Every sentence stating a fig default this plan changes. Grep both READMEs for `body_offset`,
    `task_tracker` and `qa.baseline.prd`.
  - *Troubleshooting*: 2a's entry for the paired stop gains `task_tracker.ref` without
    `task_tracker.type`.
  - *Where the two meet*:
    - The opening becomes §10's text: "Each works on its own. Installed together, `fig` reads the
      PRD where `pm` writes it and writes into task records through `pm`'s adapters. They still
      share two objects: the PRD and the task record."
    - A paragraph on the unset defaults: the PRD order; handoff borrowing only a markdown record;
      without pm, printing.
    - The "Neither link is required" sentence stays true: an explicit `null` still means no PRD.
- Modify `.github/two-plugins.html:25-26` and re-render `.github/two-plugins.png`.
  - h1: `Each works on its own`.
  - sub: "Installed together, fig reads the PRD where pm writes it and writes into task records
    through pm's adapters. They still share two objects, each named twice — and one more thing
    crosses as data: the version a handover is pinned to, which the ticket then cites."
- Modify `plugins/fig/skills/arrows/SKILL.md`. In the helper table at :245, `opts.stroke` becomes
  `{color, weight, dash, opacity}`. The description at :3 goes to 500 characters or fewer.

**Interfaces:**
- The fig description, word for word, in `plugin.json` and the marketplace:
  "Skills for a Figma file several people share: work out its conventions, stub the screens still
  missing, draw them inside those conventions, wire the flow arrows, audit a page before handoff,
  hand sections over pinned to a version, QA what shipped, and bring the canonical page current.
  Installed with pm, it reads pm's PRD and writes into its task files."

- [ ] **Step 1: Raise the versions and write the fig description**, in both `plugin.json` files
  and the marketplace. Step 4 reads pm's `0.38.1` from its installed `plugin.json`, so this comes
  first.
- [ ] **Step 2: Write the CHANGELOG entries**, problem first.
  - **fig 3.28.0:**
    - the PRD is read wherever it is
    - handoff writes into pm's markdown task file
    - unset borrows only markdown
    - `task_tracker.ref` without its type stops
    - the drafter writes only what it observed, and page rules go under `files.<fileKey>`
    - `body_offset` ships null
    - qa resolves its config
    - preflight's rows
    - the arrows table names `opacity`

    The floor-only differences, listed: `task_tracker.type` none → null, `qa.baseline.prd` null
    → `{type: markdown, ref: null}`, `component_audit.body_offset` `{270, 120}` → null.
  - **pm 0.38.1:** the shared reader and preflight carry fig's pair and PRD rows; nothing changes
    for pm configs. *The other half* no longer says the two never call each other.
- [ ] **Step 3: Edit the documents and re-render**

Run: `bash tools/render-images.sh two-plugins && python3 tools/png-trim.py .github/two-plugins.png --count`
Expected: `trailing=37`. Open the PNG next to the committed one and check it by eye before
committing.

- [ ] **Step 4: Prove it on an installed pair** (design §4's condition, and S8). Use a throwaway
  config dir, so the machine's own plugins are untouched:

```bash
T=$(mktemp -d); W=<worktree>
CLAUDE_CONFIG_DIR=$T claude plugin marketplace add "$W"
CLAUDE_CONFIG_DIR=$T claude plugin install fig@byjunyoung
CLAUDE_CONFIG_DIR=$T claude plugin install pm@byjunyoung
P=$(mktemp -d) && cd "$P"
root() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['plugins'][sys.argv[2]][0]['installPath'])" "$T/plugins/installed_plugins.json" "$1"; }
FIG=$(root fig@byjunyoung)
CLAUDE_CONFIG_DIR=$T python3 "$FIG/_common/scripts/lib/borrow-pm.py" task
```

Expected: `action` `write`, `dir` `./tasks`, and `script` under `$(root pm@byjunyoung)`, whose
`plugin.json` says `0.38.1`. The install paths come from the registry rather than a guessed cache
layout. Then, in `$P`:

| Run | Expected |
|---|---|
| that `script`'s `new --dir tasks --title Demo`, then `append-under --heading "Design changes" --line x` twice | one heading, two lines |
| `docs/prd/demo.md` with `product: Demo`, then `borrow-pm.py prd` | `from: pm`, one candidate |
| `claude plugin disable pm@byjunyoung`, then `task` | `print`, with the install note |
| `claude plugin enable pm@byjunyoung`; write a `pm-conventions.yaml` keeping records in notion; `task` | `print` — no new write |
| `claude plugin uninstall pm@byjunyoung`; `figma-conventions.yaml` = `task_tracker: {type: markdown}`; fig's `preflight.py` | an attention row; last line not FAIL |

Every `claude` and `python3` call there carries `CLAUDE_CONFIG_DIR=$T`. Record the outcomes in the
PR body.
- [ ] **Step 5: The owner's real configs.** Never paste their values anywhere.
  - Run fig's `resolve-config.py --authored task_tracker.type` with the owner's layers.
  - Resolve against `c868dad`'s fig floor and against the new one, and list the differences that
    reach the owner. Each must be one of the three above. A team that relied on the old
    `body_offset` now has to write it.
  - Run both floors' fig `preflight.py --quiet` from the same directory and compare the verdicts.
    A string `qa.baseline.prd` now makes Notion required.
  - Fix the shared team-config repository behind preview → go.
- [ ] **Step 6: Run everything**

Run: `bash tools/verify-all.sh`
Expected: `· PASS`. No length WARN for setup, draw, sketch, qa, handoff or arrows. The other
skills' WARN lines remain until Phase 3.

- [ ] **Step 7: Commit**, then push the branch on its own, not chained.
- [ ] **Step 8: Preview the PR** — title, body (the installed-pair results and the
  floor-difference list), version bumps and CHANGELOG lines. Open it after go. The body also lists
  the owner's live check: `/fig:handoff` on a real file with pm installed, writing into a markdown
  task file.
- [ ] **Step 9: Surfaces outside the repository**, each as preview → go:
  - The owner's portfolio page, both languages:
    - the image alt and any sentence saying the two never call each other
    - copy the re-rendered `two-plugins.png`, since the page's diagram is that file
    - run the site's tests, then deploy
  - The owner's private list: team guides, team config and personal skills. Search them for
    "never call each other", `task_tracker`, `qa.baseline.prd` and `body_offset`, and update each
    hit.
