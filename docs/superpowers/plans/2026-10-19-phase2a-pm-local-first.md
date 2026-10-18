# Phase 2a — Local-first defaults, pm side Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pm` runs end to end with no config and nothing connected: the floor keeps tasks as
markdown files in `./tasks` and writes a daily log, a ref written without its type stops instead of
silently changing meaning, the markdown tracker is a tested script, and setup, prd, the task skills
and the log are rewritten around that default.

**Architecture:** Config changes go in the floor (`plugins/pm/_common/conventions.example.yaml`).
The paired-key guard goes in the shared `resolve-config.py` and `preflight.py`, which stay
byte-identical in both plugins. Every markdown-tracker operation moves out of inline Python in
`trackers/markdown.md` into one pm-only script, `markdown-tracker.py`, with subcommands and
fixtures. The skill bodies change only where they call those, or where the spec changes what they
do.

**Tech Stack:** Python 3 (stdlib, PyYAML), git, bash. Fixtures follow `tools/test/*.test.py`:
`check()` plus a failure list, the script run as a subprocess, `HOME` a temp dir, and
`PYTHONUSERBASE` pinned.

**Spec:** On branch `worktree-local-first-design`:
`docs/design/2026-10-18-local-first-defaults.md` §1, §2 and §5, with decisions 1, 2 and designer's
calls 5 and 6; `docs/design/2026-10-18-skill-review.md` S2 (pm half), S10, S12, S13, S16, D5, Bin A
3–7, and the appendix rows for prd, setup, task-*, log and log-review that these touch;
`docs/superpowers/plans/2026-10-18-skills-overhaul-roadmap.md`, the Phase 2 row and *Release and
surfaces, every phase*.

**Split.** Phase 2 is two plans. The full list is 17 tasks in two areas a reviewer can approve
apart: pm's defaults and skills (this plan), and fig's reading of pm (2b,
`2026-10-19-phase2b-fig-borrows-pm.md`). 2b depends on this plan's released pm: its version floor
(`PM_MIN = "0.38.0"`), the markdown-tracker interface frozen in Task 3, and the floor values in
Task 2. So this plan merges and ships first, and leaves the repository releasable without 2b.

## Global Constraints

- Branch `overhaul-phase2`, cut at `c868dad` (the final Phase 1 commit). Line numbers below are
  against `c868dad`. The roadmap gate is "Phase 1 merged": rebase onto `origin/main` once it is.
- Commit messages are Korean, `type(scope): what changed, in a sentence`. The body says why.
- Documents and code comments are English.
- These stay byte-identical across the two plugins (`SHARED`, verify.py:46-47):
  - `_common/scripts/lib/resolve-config.py`
  - `_common/scripts/lib/preflight.py`
  - `hooks/shared-config.py`
  - `hooks/hooks.json`

  Change the pm copy, then `cp` it to fig.
- No team-specific value in any shipped file or in this plan. Prose never carries a skill count.
- Versions: pm `0.37.1 → 0.38.0`. fig `3.27.0 → 3.27.1`, because its copies of the shared files
  change. Both get CHANGELOG entries.
- Every SKILL.md this plan edits leaves with a `description` of 500 characters or fewer, counted on
  the YAML-parsed value. The shape is one sentence on what it does and when, then the trigger
  phrases in both languages. Detail moves into the body only where the body lacks it. `verify.py`
  then prints no length WARN for that skill.
- Every write outside this repository — the PR, the team-config repository, the portfolio page —
  is preview → go.
- Run `bash tools/verify-all.sh` before pushing, and never chain it with `&&` to a push.
  `tools/team-strings.local.txt` is never committed.
- Task 3's interface block is frozen once this plan merges. 2b copies it verbatim.

## Review Focus

1. **A config that writes `task.record.ref` and not `task.record.type`.** Yesterday it read as
   Notion; under the new floor it would read as a folder. `--authored task.record.type` exits 3
   and names both keys, and preflight FAILs naming the type.
   → Task 1 `paired: ref without type → --authored stops`, `ref without type → FAIL naming the key`.
2. **A first run where `./tasks` does not exist yet, or where `task.record.ref` names a file.** A
   missing folder is "no records yet": exit 0, said on stderr, and created by the first `new`. A
   file in its place stops with exit 2.
   → Task 3 `list on a missing dir`, `new on a missing dir creates it`, `list on a file → exit 2`.
3. **A record saved with Windows line endings.** Writing the link or appending a line keeps CRLF
   throughout, so git shows one changed line, not the whole file.
   → Task 3 `set-link on CRLF keeps CRLF`, `append-under on CRLF keeps CRLF`.
4. **Two tasks whose titles slug to the same name, or a title in a non-Latin script.** The second
   file gets `-2`. Letters in any script are kept, and nothing is overwritten.
   → Task 3 `new twice with one title → -2`, `slug keeps non-Latin letters`.
5. **Today's edit, saved but not committed, when `/pm:log` runs.** It counts as moved, and a past
   day says it counted commits only.
   → Task 3 `moved counts an uncommitted edit today`, `moved on a past date is commits only`.

---

### Task 1: A ref written without its type stops, and pm no longer needs node

**Files:**
- Modify, byte-identical in both plugins: `plugins/{pm,fig}/_common/scripts/lib/resolve-config.py`
  - the usage block at :14-17
  - a new `AUTHORED_WITH` and `unpaired()` after `DEFAULT_NAME` at :66
  - `inherited()` at :164-167
  - the message in `main()` at :278-288
- Modify, byte-identical in both plugins: `plugins/{pm,fig}/_common/scripts/lib/preflight.py`
  - `load_config()` at :146-165 (and its docstring at :150-153, which says the floor's record type
    is notion)
  - `settle_requirements()` at :195-217
  - the node row in `host_checks()` at :233-237
- Test: `tools/test/resolve-config.test.py`, `tools/test/preflight.test.py`

**Interfaces:**
- Produces, in `resolve-config.py`:
  - `AUTHORED_WITH = (("task.record.type", "task.record.ref", frozenset()),
    ("task.link_property", "task.record.type", frozenset({"markdown"})))`. Each entry is
    `(key, trigger, exempt trigger values)`. 2b appends
    `("task_tracker.type", "task_tracker.ref", frozenset())`.
  - `def unpaired(user: dict) -> list[tuple[str, str]]`. It returns `(key, trigger)` for each entry
    where the trigger is present in `user`, the trigger's written value (`str(v).lower()`) is not
    in the exempt set, and the key is not present.
  - `inherited(keys, name)`. A key listed in `AUTHORED_WITH` counts as borrowed only when it
    appears in `unpaired(user)`. Every other key keeps today's rule.
  - stderr for a paired key, exit 3. The first line starts
    `{key} is not set in {name}, while {trigger} is —`. The rest says the key used to come from
    the plugin's defaults and that default changed, then to write it beside the trigger. The
    origin lines follow, as today.
- Produces, in `preflight.py`:
  - For each `(key, trigger)` from `unpaired(user)` whose key ends in `.type`, a row
    `("config", key, "missing", "{trigger} is set but {key} is not — write {key} beside it")`.
    That makes the verdict FAIL.
  - Only the ref → type pairs are reported, because those are where a floor change silently
    changes what a written value means. `task.link_property` stays an `--authored` check that only
    publish and sync run, at stage 2 (Task 6). A Notion record with no mirror never reads it, so
    preflight must not fail it.
  - Where `PLUGIN == "pm"`, the node row is never `missing`: it is `ok` or `absent`, with the note
    "pm needs it only for the Notion-log importer (`import-notion-export.mjs`)".

- [ ] **Step 1: Write the failing tests.** In `resolve-config.test.py`, a new numbered block after
  case 8. Every case writes `proj/pm-conventions.yaml`, under a `bare` home with no layer of its
  own.

| Test name | Project layer | Run | Assert |
|---|---|---|---|
| `paired: ref without type → --authored stops` | `task:\n  record:\n    ref: ./x\n` | `--authored task.record.type` | rc 3. stderr contains `task.record.type is not set in pm-conventions.yaml, while task.record.ref is` |
| `paired: neither written → passes` | none | `--authored task.record.type` | rc 0 |
| `paired: both written → passes` | `record: {type: markdown, ref: ./t}` under `task` | `--authored task.record.type` | rc 0 |
| `paired: a non-markdown type needs its link property` | `record: {type: notion, ref: "collection://x"}` | `--authored task.link_property` | rc 3, stderr names `task.link_property` |
| `paired: a markdown type exempts the link property` | `record: {type: markdown, ref: ./t}` | `--authored task.link_property` | rc 0 |

  Case 7 (`floor-only key → --authored exits 3` on `task.contract.level`) must keep passing
  unchanged.

  In `preflight.test.py`:

| Test name | Setup | Assert |
|---|---|---|
| `ref without type → FAIL naming the key` | `proj/pm-conventions.yaml` = `task:\n  record:\n    ref: ./x\n` | last line ends `· FAIL`; a line under `Fix first` contains `task.record.type` |
| `pm without node → not a failure` | no config; `PATH` = an empty temp bin dir | no `Fix first` line names `node`; last line does not end `FAIL`; a details row starts `host      node` with `absent` |
| `notion record, no mirror, no link property → not FAIL` | `task:\n  record:\n    type: notion\n    ref: "collection://x"\n` | no `Fix first` line names `task.link_property`; `needed because` names `task.record.type: notion` |

  The existing `gsheet` fixtures — type and ref written, no link property — must keep their
  current verdicts (`Cannot tell`, rc 2, where the claude CLI is absent).

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/resolve-config.test.py; python3 tools/test/preflight.test.py`
Expected: FAIL on the `paired:` cases that expect rc 3 and on both new preflight cases.
`neither written` passes today.

- [ ] **Step 3: Implement** `AUTHORED_WITH`, `unpaired()`, the new `inherited()` and the message in
  `resolve-config.py`. Add a usage line for the paired rule at :14-17. In `preflight.py`, call
  `mod.unpaired(user)` inside `load_config()`, so it returns `(user, full, unpaired)`. Add the
  guard rows in `settle_requirements()`, for `.type` keys only. Gate the node row on `PLUGIN`. Rewrite the docstring at
  :150-153 so it no longer names a floor type. Then copy both files to fig:
  `cp plugins/pm/_common/scripts/lib/{resolve-config,preflight}.py plugins/fig/_common/scripts/lib/`.

- [ ] **Step 4: Run**

Run: `python3 tools/test/resolve-config.test.py && python3 tools/test/preflight.test.py && python3 tools/verify.py`
Expected: PASS. `verify.py` reports no `[shared] copies … have diverged`.

- [ ] **Step 5: Commit**

```bash
git add plugins/*/_common/scripts/lib/resolve-config.py plugins/*/_common/scripts/lib/preflight.py tools/test/resolve-config.test.py tools/test/preflight.test.py
git commit -m "feat(shared): 타입 없이 ref만 적은 설정은 기본값이 바뀌어도 조용히 다른 곳을 읽지 않고 멈춘다"
```

### Task 2: The pm floor moves to local files

**Files:**
- Modify: `plugins/pm/_common/conventions.example.yaml`
  - the header at :16-20: one line saying a ref written without its type stops
  - `task.record` at :144-146
  - `task.link_property` at :154-158
  - `log.enabled` at :427-428
- Test: `tools/test/resolve-config.test.py`, cases 1 and 2 at :46-57

**Interfaces:**
- Produces these floor values, which Tasks 3–8 and 2b rely on:
  - `task.record.type: markdown`
  - `task.record.ref: "./tasks"`. The comment says a relative path resolves against the directory
    the skill runs in, and the folder is created with the first record.
  - `task.link_property: ticket`. The comment says this is the markdown skeleton's key, and that
    a config naming another record type has to name its own (the guard from Task 1).
  - `log.enabled: true`. The comment says `/pm:log` runs only when called by name (Task 4), and
    writes one file under `log.out.dir`.
- Unchanged: `task.mirror.type: none`, `prd.target: markdown`, `sources.chat_type: slack`,
  `sources.calendar_type: google`.

- [ ] **Step 1: Write the failing tests.** Rewrite case 1 as `no config → the local floor`: rc 0;
  `task.record.type == "markdown"`, `task.record.ref == "./tasks"`,
  `task.link_property == "ticket"`, `log.enabled is True`, `task.mirror.type == "none"`. Case 2
  keeps its three assertions on `--need task.mirror.ref`, which is still null. Add:
  - `no config → --authored task.record.type passes` — rc 0.
  - `explicit notion config resolves as written`. The project layer is `task: {record: {type:
    notion, ref: "collection://x"}, link_property: Ticket}`. All three values come back as
    written, and `--authored task.record.type,task.link_property` exits 0.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/resolve-config.test.py`
Expected: FAIL on `no config → the local floor`.

- [ ] **Step 3: Change the four values and their comments.**

- [ ] **Step 4: Run**

Run: `python3 tools/test/resolve-config.test.py && python3 tools/test/preflight.test.py && python3 tools/verify.py`
Expected: PASS. The preflight case `no config → says nothing is needed yet` still passes, because
a floor value never makes a requirement.

- [ ] **Step 5: Commit**

```bash
git add plugins/pm/_common/conventions.example.yaml tools/test/resolve-config.test.py
git commit -m "feat(pm): 설정 없이도 일감은 ./tasks 마크다운으로, 일지는 켜진 채로 시작한다"
```

### Task 3: The markdown tracker becomes a tested script

**Files:**
- Create: `plugins/pm/_common/scripts/lib/markdown-tracker.py`
- Modify: `plugins/pm/_common/trackers/markdown.md`, rewritten around the script:
  - :6-9: `{dir}` and its base directory
  - :11-33: the skeleton gains the header row, and `ticket:` becomes the floor's link key
  - :38-69: reading and *what moved* become `list` and `moved`
  - :71-93: writing back becomes `set-link` and `append-under`
  - :95-107: things that bite gain CRLF and not-a-directory
- Modify: `plugins/pm/_common/trackers/README.md`. The record table at :50-61 gains the row
  `**Appending a line under a heading** | /pm:task-publish | Append after what is already in that
  section; add the heading when it is missing; never a second heading`. 2b adds `/fig:handoff`
  to that row once handoff calls it.
- Create: `tools/test/markdown-tracker.test.py`

**Interfaces — frozen. 2b's Consumes copies this block verbatim:**

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

- `slug(name: str) -> str`. The steps, in order:
  - NFC-normalise, then lower-case.
  - Turn each run of whitespace, or of any of `/\:*?"<>|#%`, into `-`.
  - Keep every other character, in any script.
  - Collapse repeated `-` and strip `-` from both ends.
  - Cut at 60 characters. An empty result is `untitled`.
- Paths keep the form `DIR` was given in, joined with `os.path.join` and never made absolute. A
  relative `DIR` resolves against the working directory.
- `list` prints `{"path": …, **front_matter}`, or `{"path": …, "error": "no front matter"}` for a
  file without one. When `DIR` is missing it prints nothing, exits 0, and writes
  `{dir} does not exist yet — no records` to stderr.
- `new`:
  - Runs `mkdir -p DIR`. It writes `DIR/{slug(title)}.md`, or the first free `-2`, `-3`, …. It
    never overwrites.
  - Front matter order: `title`, then each `--set` in the order given, then `{link-key}:` left
    empty (default `ticket`). A value is quoted when a YAML reader would not read it back as the
    same string.
  - Body:
    - `## Context`
    - the header row `| | |`
    - `|---|---|`
    - one `| LABEL | VALUE |` row per `--row`, in order, with `|` written as `\|` and a newline as
      `<br>`
    - a blank line
    - `## Change summary`
- `set-link` replaces the key's line inside the front matter, or adds it before the closing `---`.
  It never writes a second key.
- `append-under`:
  - Finds the first heading (`#` to `######`) whose text equals TEXT. It appends the line as the
    last non-blank line before the next heading of the same or a higher level.
  - With no such heading, it appends `## TEXT`, a blank line, and the line at the end of the file.
  - Two runs write one heading and two lines.
- `moved` has four cases:
  - In a git work tree, it takes the files under DIR from commits dated DATE.
  - When DATE equals `--today` (default: today's local date), it also takes the files
    `git status --porcelain -- DIR` reports whose mtime falls on DATE. The method is
    `git+uncommitted`, or `git` on any other date.
  - Outside git, it uses mtime alone, method `mtime`.
  - A missing DIR gives `[]` and `none`.
- Every write keeps the file's line ending: CRLF if its first line ends in CRLF. It keeps a leading
  UTF-8 BOM.

- [ ] **Step 1: Write the failing tests** in `tools/test/markdown-tracker.test.py`, run as a
  subprocess in a temp dir. The git cases set `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE`.

| Test name | Setup → run | Assert |
|---|---|---|
| `slug keeps non-Latin letters` | `slug "通知 設定 / v2"` | stdout `通知-設定-v2` |
| `slug of punctuation only` | `slug "::"` | `untitled` |
| `new on a missing dir creates it` | `new --dir t --title "Push settings" --set project=App --row "Request source=https://x"` | rc 0; stdout `t/push-settings.md`; file exists |
| `new writes a header row` | same file | the two lines after `## Context` are `\| \| \|` and `\|---\|---\|`; the front matter ends with `ticket:` |
| `new twice with one title → -2` | the same `new` again | stdout `t/push-settings-2.md`; first file unchanged |
| `title with ": " round-trips through list` | `new --title "Billing: refunds"` then `list --dir t` | that record's `title` == `Billing: refunds` |
| `list on a missing dir` | `list --dir nope` | rc 0; stdout empty; stderr contains `does not exist yet` |
| `list on a file → exit 2` | `touch f; list --dir f` | rc 2; stderr contains `is not a directory` |
| `set-link twice → one key` | `set-link … --key ticket --value u1`, then `u2` | exactly one line matching `^ticket:`, value `u2` |
| `set-link on CRLF keeps CRLF` | write a record with `\r\n` endings, then `set-link` | `b"\n"` occurs only as part of `b"\r\n"` |
| `append-under twice → one heading, two lines` | `append-under --heading "Design changes" --line A`, then `--line B` | one `## Design changes`; `A` then `B` under it |
| `append-under stops before the next heading` | a file with `## Change summary\n- old\n## Notes\n` | the new line sits between `- old` and `## Notes` |
| `append-under on CRLF keeps CRLF` | as `set-link on CRLF` | same assertion |
| `append-under on a missing file → exit 4` | | rc 4 |
| `moved counts an uncommitted edit today` | git repo: `a.md` committed dated D; `b.md` edited and left uncommitted; `moved --date D --today D` | paths contain both; method `git+uncommitted` |
| `moved on a past date is commits only` | the same repo, `--date D --today D+1` | paths == [`a.md`]; method `git` |
| `moved without git → mtime` | plain dir, one file touched on D | method `mtime` |

- [ ] **Step 2: Run to verify they fail**

Run: `python3 tools/test/markdown-tracker.test.py`
Expected: every case fails — the script does not exist.

- [ ] **Step 3: Implement `markdown-tracker.py`** to the interface above. It uses `argparse`
  subcommands and reads front matter with `yaml.safe_load`. Then rewrite `markdown.md`:
  - Every inline Python block becomes a `${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py`
    call.
  - Add "**The path is the id, and the file name is the slug**".
  - Add "**A change summary is `append-under --heading "Change summary" --line "- {date} {text}"`**".
  - `log.me.tracker_user_id` is the assignee string. Where it is null, rows are not split: Task 4
    says how the log reads that.
  - Keep `connector: none` and `roles: record` on lines 3-4.

- [ ] **Step 4: Run**

Run: `python3 tools/test/markdown-tracker.test.py && python3 tools/verify.py`
Expected: PASS. `verify.py` finds the `${CLAUDE_PLUGIN_ROOT}/…` path.

- [ ] **Step 5: Commit**

```bash
git add plugins/pm/_common/scripts/lib/markdown-tracker.py plugins/pm/_common/trackers/markdown.md plugins/pm/_common/trackers/README.md tools/test/markdown-tracker.test.py
git commit -m "feat(pm): 마크다운 일감 저장소를 검사되는 스크립트로 옮기고 파일 이름·줄바꿈·폴더 없음을 다룬다"
```

### Task 4: `/pm:log` runs only when called, reads uncommitted work, and says whose rows are whose

**Files:**
- Modify: `plugins/pm/skills/log/SKILL.md`
  - :1-4: `disable-model-invocation: true`; a description of 500 characters or fewer, without the
    "explicit invocation only" clause the flag now enforces
  - :27-33: `--authored task.record.type`; the `log.enabled` sentence (on by default, `false`
    stops)
  - :43-55: a markdown record reads `moved`
  - :57-72: mine and team when `log.me.tracker_user_id` is null; a markdown row's stable url is its
    path
  - :76-77: the full adapter commands
- Modify: `plugins/pm/skills/log-review/SKILL.md` — :3 (description of 500 characters or fewer),
  :44-46, :59, :98
- Modify: `plugins/pm/_common/scripts/lib/adapter.py:71-83` — `--type` required
- Test: `tools/test/adapter.test.py`

**Interfaces:**
- Consumes: `markdown-tracker.py moved` (Task 3). The floor `log.enabled: true` (Task 2).
- Produces:
  - `adapter.py` without `--type` exits 1, with `--type is required — pass none where there is no
    tool`. `--type none` still prints `none` and exits 0.
  - Log rules:
    - Where `log.me.tracker_user_id` is null, every row goes under *My tasks*. The summary says the
      rows were not split, and names the key.
    - A markdown record's url is its `path` as `list` and `moved` print it.
    - The summary names the method `moved` returned. For a backfilled day that is "commits only".
    - A missing task folder is named in the summary as "no task records yet ({dir})". It is not a
      failure.
  - `log-review` stitches by "url, or the record's path where the tracker is markdown". The closing
    line at :98 reports how many groups were stitched by title, and how many items were kept
    single-day for having neither url nor title. It no longer says "dropped for having no url".

- [ ] **Step 1: Write the failing test** `no --type → exit 1, says it is required` in
  `adapter.test.py`. Run `--kind trackers` with no `--type`. Assert rc 1, and stderr contains
  `--type is required`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 tools/test/adapter.test.py`
Expected: FAIL — today it prints `none` and exits 0.

- [ ] **Step 3: Implement** the `adapter.py` change and the two skill edits.

- [ ] **Step 4: Run**

Run: `python3 tools/test/adapter.test.py && python3 tools/verify.py`
Expected: PASS, and no description WARN for `pm:log` or `pm:log-review`.

- [ ] **Step 5: Probe that a scheduled run still works with the flag on.** Run it in an empty
  temp directory. Disable the installed `pm` for this run, so the checkout's copy is the only one
  loaded:

```bash
D=$(mktemp -d) && cd "$D" && claude --plugin-dir <worktree>/plugins/pm \
  --settings '{"enabledPlugins":{"pm@byjunyoung":false}}' \
  -p "/pm:log" --permission-mode acceptEdits --allowedTools "Read" "Write" "Edit" "Glob" "Grep" "Bash"
```

Expected:
- exit 0
- `logs/<YYYY>/<MM>/<YYYY-MM-DD>.md` exists
- the summary names `./tasks` as not existing yet

If the command is reported unknown, or nothing is written, remove `disable-model-invocation`.
Record why in the commit body and in the CHANGELOG line (Task 9). D5's safety argument then rests
on preflight alone; say so in the PR body.

- [ ] **Step 6: Commit**

```bash
git add plugins/pm/skills/log/SKILL.md plugins/pm/skills/log-review/SKILL.md plugins/pm/_common/scripts/lib/adapter.py tools/test/adapter.test.py
git commit -m "feat(pm): 일지는 이름으로 부를 때만 돌고, 커밋 전 수정도 그날 움직인 것으로 센다"
```

### Task 5: `/pm:task-draft` on local records, and a chat link it cannot open

**Files:**
- Modify: `plugins/pm/skills/task-draft/SKILL.md`
  - :1-4: a description of 500 characters or fewer
  - :24-30: config
  - :44-48: the chat-thread branch
  - :105-132: Create
  - :134-136: Verify

**Interfaces:**
- Consumes: `markdown-tracker.py new|list` (Task 3). `--authored task.record.type` (Task 1).
- Produces:
  - **Config:** `resolve-config.py --name pm-conventions.yaml --need task.record.ref --authored
    task.record.type`.
  - **§2:** where the source is a chat link and the adapter's read is not available in this
    session — the connector is absent, or its call fails on access — say so in one line, ask for
    the thread pasted as text, and go on from the paste. The Request source row keeps the link. No
    preflight change.
  - **Before creating:** look for a record that already carries the source link. Markdown:
    `grep -rlF "{link}" {task.record.ref}`. Other types: the adapter's search. Where one is found,
    offer fill/revise on it instead.
  - **Create, markdown:** one `markdown-tracker.py new` call, with properties as `--set` and the
    context rows as `--row` in `task.context_rows` order. Report the printed path.
  - **Create, every other type:** unchanged.
  - **The body-template sentence at :132** applies only where `task.record.type` is `notion`.
  - **Verify, markdown:** `list --dir` reads the new record back.

- [ ] **Step 1: Edit the skill** as above.

- [ ] **Step 2: Verify**

Run: `grep -n "markdown-tracker.py new" plugins/pm/skills/task-draft/SKILL.md && python3 tools/verify.py`
Expected: one match. PASS, and no description WARN for `pm:task-draft`.

- [ ] **Step 3: Commit**

```bash
git add plugins/pm/skills/task-draft/SKILL.md
git commit -m "feat(pm): 일감 초안이 로컬 파일로 만들어지고, 열 수 없는 채팅 링크는 붙여넣기를 청한다"
```

### Task 6: Publish and sync stop on "record only" first; parents and tickets are not filed twice

**Files:**
- Modify: `plugins/pm/skills/task-publish/SKILL.md`
  - :1-4: description
  - :21-30: two-stage config
  - :229: parent labels
  - :453-455: step 7, create
  - :484-491: the adapter block
  - :493-499: step 9
  - :501-512: report
- Modify: `plugins/pm/skills/task-sync/SKILL.md` — :1-4 (description), :13, :15-22
- Modify: `plugins/pm/_common/trackers/github.md:155-163` — the parent's `--label`

**Interfaces:**
- Consumes: `AUTHORED_WITH` (Task 1). The floor (Task 2).
- Produces:
  - **Stage 1, both skills:** `resolve-config.py --name pm-conventions.yaml --authored
    task.record.type`. Where `task.mirror.type` is `none`, stop with this text, shared word for
    word by both skills:
    > These tasks are kept as records only — nothing is set up to file them into. `task.mirror` is
    > the setting that attaches a tracker; `/pm:setup` reads its schema and fills it in.
  - **Stage 2, publish:** `--need task.record.ref,task.link_property,task.mirror.ref --authored
    task.record.type,task.link_property,task.contract.level`.
  - **Stage 2, sync:** the same `--need`. `--authored` also takes `task.progress_source`.
  - **Bin A 6:** a new parent carries the mapped project label, because the adapter's parent search
    at github.md:41 keys on it. It also carries the labels the rule document requires of its
    kind, and nothing else. github.md:161 becomes `--label "{project label}{,labels the rule
    document requires of a parent}"`. The sentence at publish:229 says the same, and says why.
  - **Bin A 7:** before step 7 creates anything, list the mirror's newest issues and match the
    exact title (github.md:131-136). A match stops the run and offers to link that ticket instead.
    Right after the create returns, step 7 writes the link property into the record. That is still
    inside the same go, before step 8 attaches. Step 9 keeps only the spec link and the change
    summary. The report says the link was written at create.

- [ ] **Step 1: Edit both skills and the adapter** as above.

- [ ] **Step 2: Verify**

Run: `grep -c "kept as records only" plugins/pm/skills/task-publish/SKILL.md plugins/pm/skills/task-sync/SKILL.md && python3 tools/verify.py`
Expected: 1 and 1. PASS, and no description WARN for either skill.

- [ ] **Step 3: Check stage 1 on a fresh install**

Run: `D=$(mktemp -d) && cd "$D" && HOME="$D" PYTHONUSERBASE=$(python3 -m site --user-base) python3 <worktree>/plugins/pm/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml --authored task.record.type | python3 -c "import json,sys; print(json.load(sys.stdin)['task']['mirror']['type'])"`
Expected: `none`, exit 0. Stage 1 reaches the record-only stop.

- [ ] **Step 4: Commit**

```bash
git add plugins/pm/skills/task-publish/SKILL.md plugins/pm/skills/task-sync/SKILL.md plugins/pm/_common/trackers/github.md
git commit -m "fix(pm): 트래커 없는 설정은 기록 전용이라고 먼저 말하고, 상위 티켓과 티켓이 두 번 생기지 않게 한다"
```

### Task 7: `/pm:prd` writes files and entries that can be linked to

**Files:**
- Modify: `plugins/pm/skills/prd/SKILL.md`
  - :1-4: a description of 500 characters or fewer
  - :30: ticket routing names `/pm:task-draft` and `/pm:task-publish`
  - :32-48: config, plus preflight
  - :215-231: publishing by target
  - :252-269: Appendix B, the anchor line
- Modify: `plugins/pm/_common/conventions.example.yaml`
  - :98-102: `prd.markdown`'s comments state the file rule
  - :107-116: new key `prd.notion.parent: null`

**Interfaces:**
- Consumes: `markdown-tracker.py slug|list` (Task 3). The floor (Task 2).
- Produces. 2b's `borrow-pm.py` reads these file rules:
  - **File names:**
    - `split: product` → `{prd.markdown.dir}/{slug(product)}.md`
    - `split: domain` → `{dir}/{slug(product)}/index.md`, holding Overview, User groups, Linked
      tasks, Design and Change log; plus `{dir}/{slug(product)}/{slug(domain)}.md` for each
      domain's entries
    - Slugs come from `markdown-tracker.py slug`.
  - **Front matter**, where `prd.markdown.front_matter` is true: `title`, `product`, `domain`
    (domain files only), `status`, `updated`.
  - **Entry anchors:** `<a id="entry-{n}"></a>` on the line before each feature or policy entry's
    heading. `n` is one more than the highest `entry-` id across the product's files. It is never
    renumbered or reused. A link to an entry is `{path}#entry-{n}`, which is the form `spec_url`
    and `task.ticket.link_rows.spec` take.
  - **Linked tasks**, where `task.record.type` is markdown:
    - Regenerated on every publish from `markdown-tracker.py list --dir {task.record.ref}`.
    - Lists the records whose `project` equals the product, as `- [{title}]({path relative to the
      PRD file}) — {status}`.
    - The first line is `<!-- generated from {task.record.ref}; edits here are replaced -->`.
    - Other record types are unchanged.
  - **`prd.notion.parent`** is the page id a new document is created under when
    `prd.notion.template` is null. When both are null, ask for a page and offer to store it. Never
    create at the workspace's top level.
  - **Go applies to every target.** A markdown file is previewed → go like the others, in the
    same stages. The premise at :17 and the opening of 4 at :217 say so.
  - **Config:** `resolve-config.py --name pm-conventions.yaml --authored task.record.type`, then
    `preflight.py --quiet`. A FAIL stops the run, with its fix lines.

- [ ] **Step 1: Edit the skill and the example config** as above.

- [ ] **Step 2: Verify**

Run: `grep -n 'id="entry-' plugins/pm/skills/prd/SKILL.md && grep -n "parent:" plugins/pm/_common/conventions.example.yaml && python3 tools/verify.py`
Expected: matches in both. PASS — `prd.notion.parent` is now in the schema — and no description
WARN for `pm:prd`.

- [ ] **Step 3: Commit**

```bash
git add plugins/pm/skills/prd/SKILL.md plugins/pm/_common/conventions.example.yaml
git commit -m "feat(pm): PRD 마크다운의 파일 이름과 항목 앵커를 정해 링크로 가리킬 수 있게 한다"
```

### Task 8: `/pm:setup` starts local, attaches a tracker after, and asks what publish and sync need

**Files:**
- Modify: `plugins/pm/skills/setup/SKILL.md`, restructured:
  - :1-4: a description of 500 characters or fewer
  - :38-59: the ladder and the opening paragraph
  - :63-76: the talking table
  - :94-158: steps 0, 1 and 1b
  - :160-243: steps 2-5
  - :245-268: step 6 and side ownership
  - :270-302: steps 7-8
  - :344-356: the report

**Interfaces:**
- Consumes: `--authored` pairs (Task 1). The floor (Task 2). `markdown-tracker.py list` (Task 3).
  `prd.notion.parent` (Task 7).
- Produces. The ladder, word for word. The procedure headings carry the same numbers, one to one:

```
① Check this machine         read-only · seconds
② Where your work lives      one grouped round — specs, tasks, chat, calendar
③ Lay out the local start    the default — preview → go · local folders and one file
④ Attach a tracker           only where ② named one — reads its schema, pairs names
⑤ Ask what no schema knows   one at a time · a recommendation · "leave it blank" always offered
⑥ Write the file             preview → go · one local file
⑦ Prove it                   the file resolves; a tracker pair re-derived where one is attached
⑧ First result               paste one message → a context table · nothing written
⑨ Share it                   only where somebody else runs these too · skipped otherwise
```

- **② asks, with options, and "local files" marked recommended:**
  - where specs live → `prd.target`
  - where a task is first written → `task.record`
  - where engineering watches → `task.mirror`. "Nowhere yet" is recommended for a local start.
  - the chat tool → `sources.chat_type`
  - the calendar → `sources.calendar_type`
- **③ is today's 1b, with three changes:**
  - It writes only what ② and ③ settled. The sentence at :156, "Everything else takes the bundled
    default and is written into the file", goes.
  - The README's loop line becomes "draft → (publish and sync once a tracker is attached)".
  - It lays out `logs/` because `log.enabled` is on.
- **④ is today's 2, 3, 3b and 4**, run only where ② named a tool. For a markdown record, the
  link-property question recommends `ticket`, the key the skeleton already carries.
- **⑤ adds these questions:**
  - Where a mirror is attached: `task.contract.level` ("Which ticket carries the done conditions
    and the QA list — each task, or the parent it hangs under?") and `task.progress_source`. This
    is Bin A 5.
  - `log.enabled` — keep a daily log; the recommendation is yes.
  - `log.me.tracker_user_id`, only for a shared tracker.
  - `log.sources.calendar`, `.chat_channels` and `.notes_channel`, only where ② named the tool.
  - Where `prd.target` is notion: `prd.notion.template`, the ids of its inline databases (read
    from the template page with `notion-fetch`), `task_db`, and `parent`.
- **⑥ writes only what ③–⑤ settled or a schema showed.** A key nobody asked about is not written,
  so a later change to the floor reaches it. Side ownership adds `task.template`, `task.policy`,
  `task.contract` and `task.progress_source` to the mirror side. `prd.*`, `sources.*` and `log.*`
  are written only by a run without `side`.
- **⑦ proves the file in three steps.** It no longer leans on `--need task.record.ref`, which the
  floor now satisfies:
  - `resolve-config.py --name pm-conventions.yaml --where` names the file just written.
  - `--authored task.record.type,task.link_property` exits 0.
  - For a markdown record, `markdown-tracker.py list --dir {task.record.ref}` exits 0.

  With a mirror attached, today's pair check follows.
- **⑧ closes with the commands that apply.** With `mirror.type: none`: `/pm:task-draft`,
  `/pm:prd`, `/pm:log`. With a mirror: draft, publish, sync.
- **The talking table gains a row per question** in ② and ⑤ above.

- [ ] **Step 1: Restructure the skill** as above. Steps ⑨ and 3b keep their current text.

- [ ] **Step 2: Verify**

Run: `grep -c "Everything else takes the bundled default" plugins/pm/skills/setup/SKILL.md; grep -c "\-\-need task.record.ref" plugins/pm/skills/setup/SKILL.md; grep -c "task.contract.level" plugins/pm/skills/setup/SKILL.md; python3 tools/verify.py`
Expected: `0`, `0`, at least `1`. PASS, and no description WARN for `pm:setup`.

- [ ] **Step 3: Commit**

```bash
git add plugins/pm/skills/setup/SKILL.md
git commit -m "feat(pm): 셋업이 로컬 시작을 기본으로 깔고 트래커는 나중에 붙이며, 게시·동기화가 요구하는 값을 묻는다"
```

### Task 9: Release 2a

**Files:**
- Modify the versions and descriptions:
  - `plugins/pm/.claude-plugin/plugin.json`: `0.37.1 → 0.38.0`, and the description below
  - `plugins/fig/.claude-plugin/plugin.json`: `3.27.0 → 3.27.1`
  - the pm entry in `.claude-plugin/marketplace.json`, the same description
- Modify both CHANGELOGs: `plugins/pm/CHANGELOG.md` and `plugins/fig/CHANGELOG.md`.
- Modify `plugins/pm/README.md`:
  - the table at :12-20
  - *Where it writes* at :22-30
  - *Starting from nothing* at :48-50, now the default
  - *The log side* at :52-65, on by default and run only when called
  - :127: pm needs `node` only for the Notion-log importer
- Modify `README.md`, English first, then `README.ko.md` at the same places:
  - the pm block of the first five minutes at :103-113, and "Neither writes into anything of
    yours" at :111. `/pm:log` writes a local file without a preview.
  - the node row at :130: fig's scripts, and pm's Notion-log importer
  - step 2's pm paragraphs at :213-225: the local start first, then attaching a tracker
  - pm's cycle and table at :386-405
  - "The task side assumes nothing" at :418: local records by default
  - the log side at :446-459
  - *Troubleshooting*: a new `<details>` entry after "A skill stops saying a setting 'is not
    set'" at :658-662, for the paired stop. It covers what the message means (a ref written
    without its type), why it stops (the default type changed), and the one-line fix. That
    existing entry stays true: a fresh install no longer meets `task.record.ref is not set`,
    since the floor fills it.

**Interfaces:**
- The pm description, word for word, in `plugin.json` and the marketplace:
  "Product specs, the tasks that come out of them, and a daily record of the work — on local
  markdown files, with nothing else connected. Write a spec against a format and verify it; turn
  a request into a task's context table; keep a work log and turn a period of it into
  accomplishment statements. Notion or an issue tracker attaches through config when you want
  one."

- [ ] **Step 1: Raise the versions and write the pm description** in both `plugin.json` files and
  the marketplace, then edit the READMEs listed above.
- [ ] **Step 2: Write the CHANGELOG entries**, problem first, in the repository's habit.
  - **pm 0.38.0:**
    - the floor moves local, with the floor-only differences listed: `task.record` notion/null →
      markdown/`./tasks`, `task.link_property` null → `ticket`, `log.enabled` false → true
    - the paired-key guard
    - the log runs only when called (or the reason from Task 4 Step 5)
    - the markdown tracker script
    - setup reordered
    - prd's file and anchor rules, and `prd.notion.parent`
    - publish and sync stop on "record only" first
    - parent labels, and the link written at create
    - node needed only for the Notion-log importer
    - `adapter.py --type` required
    - log-review stitches by path
  - **fig 3.27.1:** the shared config reader and preflight carry pm's paired-key guard. Nothing
    changes for fig configs. fig's own pair arrives with the change that makes its tracker type
    unset.
- [ ] **Step 3: Check the owner's real configs before anything ships.** Never paste their values
  into the plan, the PR or a commit.
  - Run `python3 plugins/pm/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml
    --authored task.record.type,task.link_property` from a working directory the owner uses. An
    exit 3 names the line to add. Fix the shared team-config repository behind preview → go.
  - Resolve the same layers against the old floor:
    `git archive c868dad plugins/pm | tar -x -C "$(mktemp -d)"`, and run that copy's
    `resolve-config.py`. Diff the two JSONs, leaf by leaf.
  - Run both copies' `preflight.py --quiet` from the same directory and compare the verdicts.
    `log.enabled` turning on makes log channels the config names, but never switched on, required
    now.
  - List every difference the owner's config sees, value or verdict. Each must follow from the
    three floor changes above. Put the list, without values, in the PR body.
- [ ] **Step 4: Run everything**

Run: `bash tools/verify-all.sh`
Expected: `· PASS`. No length WARN for any pm skill. fig's WARN lines stay until 2b and Phase 3.

- [ ] **Step 5: Commit**, then push the branch on its own, not chained.
- [ ] **Step 6: Preview the PR** — title, body (with the difference list from Step 3), version
  bumps and CHANGELOG lines. Open it only after go.
- [ ] **Step 7: Surfaces outside the repository**, each as preview → go:
  - The owner's portfolio page, both languages. "pm writes only after a preview" stops being true
    with the log on by default. Then run the site's tests and deploy.
  - The owner's private list: team guides, team config and personal skills. Search them for
    `log.enabled`, `task.record`, `link_property` and setup's old flow ("reads your tracker
    first"), and update each hit.
