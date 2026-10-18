# Local-first defaults, two skill merges, one removal

Status: design, 2026-10-18. Decisions 1–8 agreed with the owner; the designer's calls are pending
the owner's review. Not built. Corrected after the same day's skill review
(`2026-10-18-skill-review.md`), which also carries proposals keyed to this document's sections.

## Intent

Both plugins should run with nothing connected but Figma. A person who installs them and writes no
config gets a working loop on local markdown files: the PRD and the task records. (The log is not
part of it yet: `log.enabled` ships `false`, so `/pm:log` stops on its first run. Whether that
default changes is an open decision in the review.) A team that
already runs on Notion and GitHub keeps running exactly as before, because its config names those
tools and the config wins over the bundled floor.

`pm` already leans this way — `prd.target` ships as `markdown`, and `/pm:setup` 1b lays out a
markdown repository. What breaks the loop today is on the seams:

- With no config, task drafting stops: `task.record.type` ships as `notion` with `ref: null`.
- `fig` reads the PRD only through `notion-fetch` (`spec_url`, `qa.baseline.prd` as a Notion id).
  `/fig:qa` has no file-reading tool at all. A PRD in a local file is invisible to `/fig:draw`,
  which takes its copy from it.
- `/fig:handoff` (and `/fig:diff`, removed in 8) writes to a task record only in Notion or GitHub.
  Any other type prints in the response.

Two merges and one removal ride along, because the same files are being opened. They answer the
question of whether the skills are cut too finely: mostly not — each skill is called at its own
moment, and shared logic already lives in `_common` scripts rather than being copied — but two
boundaries do not earn their keep, and one skill writes a record nobody reads.

## Decisions

Settled with the owner, one at a time.

| # | Question | Chosen | Not chosen |
|---|---|---|---|
| 1 | What changes | The bundled defaults only. A config that names Notion keeps it | Moving an existing team's source of truth to markdown |
| 2 | How far the pm floor moves | Documents and tasks go local. Chat and calendar types stay `slack` / `google`; an unreachable source is named and skipped | Every source type `none` (would silently stop chat and calendar reads for configs that rely on the floor for them) |
| 3 | How fig is told where the PRD is | Explicit `type` / `ref` keys | Inferring the type from the value's shape (for config keys; the per-call `spec_url` is still read by shape — designer's call 2) |
| 4 | How fig writes to a markdown task record | Through `pm`'s markdown tracker adapter | A markdown row of fig's own; printing only |
| 4a | What that does to "the two never call each other" | Reworded: each works alone; installed together, they borrow from each other | Keeping strict separation |
| 5 | Skill granularity | Merge `deck-setup` into `deck`; merge `task-draft`, `task-publish`, `task-sync` into one `/pm:task` | No merges; a full regrouping into stage-level entry points |
| 6 | The retired commands | Removed outright; CHANGELOG and READMEs name the new form | Redirect stubs for one version (`disable-model-invocation: true` would have kept them out of the listing) |
| 7 | `/fig:diff` | Removed. Nobody reads the AS-IS/TO-BE table it writes into the task doc; looking at what changed is Dev Mode's *Compare changes* | Keeping it; folding it into `/fig:handoff` |
| 8 | `/fig:handoff` | Kept — its pinned version is what the ticket's done conditions and QA steps name. What `use_figma` cannot do goes through the web app in the browser, or is left out | Removing it in favour of marking *Ready for dev* by hand |

## Goals

- No config, both plugins installed, nothing connected but Figma: PRD → task → design → handoff
  runs end to end on local files.
- Every key a team's config writes resolves to the same value after the change.
- Fewer entry points where a skill is only ever a step of another.
- Shorter skill descriptions, so the skill listing stops dropping them (it drops descriptions once
  the listing passes its budget, least-used skills first).

## Non-goals

- Changing any team's config. One that sets `notion` explicitly needs nothing.
- New tracker or chat adapters (Linear, Jira, …).
- Building the Figma Specs integration. Only its place is described (see *Later*).
- Removing fig's dependency on Figma. That is the plugin's job.
- Any merge beyond the two named.

## Anti-goals — a failure even if it works

- A config that worked on Notion yesterday reads a Notion url as a directory today.
- `fig` refuses to run because `pm` is not installed.
- A source quietly stops being read without the closing summary saying so.

## Constraints

- `resolve-config.py` and `preflight.py` are byte-identical copies in both plugins; `verify.py`
  compares them.
- Adapters ship only calls that were actually run. Nothing is written from documentation alone.
- Documents are English first, then `README.ko.md`. No team value ships. Prose carries no skill
  count.
- Every change under `plugins/` raises the version and adds a CHANGELOG line.
- Preflight requirements come only from values a person wrote, never from the floor. Keep it so.

## Design

### 1. pm bundled defaults

| Key | Now | After |
|---|---|---|
| `task.record.type` | `notion` | `markdown` |
| `task.record.ref` | `null` | `"./tasks"` |
| `task.mirror.type` | `none` | unchanged |
| `prd.target` | `markdown` | unchanged |
| `sources.chat_type` / `calendar_type` | `slack` / `google` | unchanged |

**Guard (designer's call).** A config that writes `task.record.ref` but not `task.record.type` used
to get `notion` from the floor and will now get `markdown`. Treat `task.record.type` as an authored
key whenever `task.record.ref` is written: `resolve-config.py --authored` stops and names the key,
the same way `contract.level` does today. That turns the one silent break into a one-line fix.

### 2. Sources that cannot be reached

`/pm:log` already reports an unreachable source as missing and skips it. Bring `/pm:task draft` in
line: given a chat link while the chat connector is unavailable, say so in one line and ask for the
thread pasted as text, which it already accepts. No preflight change.

### 3. fig: where the PRD is read from

`qa.baseline.prd` becomes:

```yaml
qa:
  baseline:
    prd:
      type: markdown     # markdown | notion | none. figma-spec is reserved (see Later)
      ref:  null         # markdown: a file, or a directory of one file per product
                         # notion: a page id or collection url
```

Resolution order, used by `/fig:draw`, `/fig:sketch` and `/fig:qa`:

1. The `spec_url` argument. It is pasted per call, not configured, so its type is read from the
   value (designer's call): a path to a `.md` file → markdown; a Notion url or 32-hex id → notion;
   a figma.com Spec link → say it is not supported yet.
2. `qa.baseline.prd`. A plain string is read as `{type: notion, ref: <string>}` and keeps working
   (designer's call), so no team config has to change.
3. With `pm` installed and its resolved `prd.target` `markdown` or `git`: `prd.markdown.dir`. One file per
   product; pick the matching one, ask when more than one could fit (designer's call — this is the
   synergy case of 4a). **Constraint:** run `pm`'s copy of `resolve-config.py`, not fig's. Each
   copy finds the bundled floor relative to its own file (`resolve-config.py:40-52`), so fig's
   copy run with `--name pm-conventions.yaml` lays fig's floor under pm's config and finds no
   `prd.target` at all. `prd.split: domain` (one file per domain) has to be handled here too.
4. Nothing: `/fig:draw` asks for a source or records that there is none; `/fig:sketch` goes on and
   says so. Both as today.

`/fig:qa` takes no `spec_url` (its inputs are source, target, mode, env), so it starts at step 2.
Its body never calls `resolve-config.py`, so `qa.baseline` is not resolved today. It gains that
step. `Bash`, `Read` and `Glob` join its `allowed-tools`. That list pre-approves tools rather than
restricting them, so their absence today means a permission prompt mid-run, not an inability.
draw and sketch gain `Read` and `Glob` the same way.

In `preflight.py`, `qa.baseline.prd.type` joins `NAMED_TOOLS` for fig with `{none, markdown}` as the
types that need no connector; `notion` needs the Notion connector. The legacy string form needs a
special case. `dig()` returns `None` when it meets a string (`preflight.py:105-111`), so today a
string `qa.baseline.prd` would be judged as needing no connector. Read a string as `notion` there,
as step 2 does.

### 4. fig: writing to a markdown task record

`task_tracker.type: markdown`, `task_tracker.ref` the task directory. The task file itself is named
to `/fig:handoff` (its path), as a Notion page url is today. With `/fig:diff` removed (8), handoff's
one line is the only thing fig writes into a task record.

**fig's own default (designer's call).** `task_tracker.type` ships unset (`null`) instead of `none`.

| fig `task_tracker.type` | What `/fig:handoff` does |
|---|---|
| unset, `pm` installed, `pm`'s resolved `task.record.type` is `markdown` | borrow `pm`'s `task.record` and write its line into the task file |
| unset, any other case | print the line, plus the note below |
| `markdown` | write into the task file through `pm`; without `pm`, print plus the note |
| `none` | print only, as today |
| `notion`, `github` | unchanged |

- Borrowing stops at `markdown`. A team whose fig config never named a tracker while its pm config
  names Notion would otherwise start writing into Notion pages where it printed yesterday.
- `task_tracker.ref` written without `task_tracker.type` stops with the authored-key message, the
  same guard as `task.record` in 1. The floor no longer settles what a written Notion id means.
- **The fig drafter defeats "unset" today.** `/fig:setup`'s `draft-conventions.py:215` writes
  `task_tracker: type: none` into every drafted config, so a team that ran setup never reaches the
  borrowing row. The drafter has to stop writing that key, and every other value it copies from the
  floor rather than observes. See the review, structural move S2.
- **Writing.** fig asks `pm`'s `adapter.py --kind trackers --type markdown --role record` for the
  adapter, and uses it to find and read the record. Handoff's line goes under the
  `ui_section_heading` heading of the task file, and the heading is appended if the file has none.
  `ui_section_heading` ships `null`; when it is null, the heading is "Design changes" in
  `meta.language` (designer's call). It is never `## Change summary`, which is the adapter's
  append-only dated log.
- **The note**, when printing because `pm` is missing: one line saying that installing `pm` writes
  this into the task file.
- **Preflight.** `markdown` joins the no-connector types for `task_tracker.type`.
  - With no config at all, preflight still ends early with PASS, as today. The rule that
    requirements come only from written values stands.
  - When a config writes `markdown` and `pm` cannot be found, the row shows `attention` with the
    fallback named. The verdict is not FAIL.

How fig finds the installed `pm` is left to the builder, with one condition: it is proven on an
installed plugin pair, not only on a development checkout.

### 5. Publishing and syncing with no mirror

Unchanged in behaviour: `/pm:task publish` and `/pm:task sync` stop when `task.mirror.type` is
`none`. The message says the local setup is record-only and names `task.mirror` as the key that
attaches a tracker later (designer's call — a local "mirror" of markdown tickets would be a second
copy of the same file).

### 6. Merge: `deck-setup` into `deck`

`/fig:deck` already opens by sending a person to `/fig:deck-setup` when the assets are missing, so
the measuring step is always a prefix of a deck.

- `skills/deck/SKILL.md` gains a first step: when `deck.assets_dir` lacks `template-spec.md` or
  `template.js`, or the person says the template was revised, run the measuring step.
- The current `deck-setup` body moves to `skills/deck/setup.md`, referenced once from `SKILL.md`.
- `deck-setup`'s triggers ("extract the slide template", "덱 템플릿 뽑아줘", …) move into `deck`'s
  description. `skills/deck-setup/` is removed.

### 7. Merge: the three task skills into `/pm:task`

One task's life in three moments: drafted from a request, filed as a ticket, kept in step with the
tracker. They share the config resolution, the adapter lookup and the record/mirror model.

```
skills/task/
  SKILL.md     what it does, config, adapters, which mode to run
  draft.md     the current task-draft body
  publish.md   the current task-publish body, with a contents list at the top
  sync.md      the current task-sync body
```

- Mode comes from the argument (`/pm:task draft|publish|sync`), else from the request: a thread or
  page to turn into a task → draft; "file / publish / update the ticket" → publish; "reconcile /
  sync" → sync. Ask only when it is still unclear.
- `SKILL.md` stays short; each mode file is one level deep from it. This also takes `task-publish`
  (over 600 lines today) under the 500-line guidance for `SKILL.md`.
- `allowed-tools` is the union of the three.
- Every reference to the old names moves to the new form. CHANGELOG history is left as written.
  Places to cover:
  - fig skills, the example config comments, all three READMEs
  - `.github/two-plugins.html`, where the names appear without the slash
  - `/pm:setup`, `/pm:log`, `/pm:log-review`
  - `_common/trackers/*.md` and `_common/sources/README.md`
  - `preflight.py` around line 51, in both byte-identical copies
  - for deck-setup: `deck-base.js:5` and `conventions.example.yaml` around 221–223

  `verify.py` checks skill references only inside one plugin's SKILL.md files, so most of these
  would slip past it (review, structural move S1).
- No redirect stubs (decision 6). `/pm:task-draft`, `/pm:task-publish`, `/pm:task-sync`,
  `/fig:deck-setup` and `/fig:diff` stop existing in the release that merges or removes them. That
  release's CHANGELOG entry in each plugin opens with the old → new names (for diff: none, see 8).
  Both root READMEs carry the same mapping where the skills are listed, so someone typing an old
  name finds the new one.
- **Callers outside this repository** are not seen by `verify.py`. Found on the owner's machine when
  this was written, all of them name mentions rather than calls:
  - a personal session-review skill: two lines, plus its design note
  - a shared team-config repository: its README, one config comment, and the comment on its
    coverage exclusion for AS-IS sections. The exclusion itself stays, since those sections remain
    in existing files.
  - a personal deck-planning skill that hands off to `/fig:deck`. It points at a template-spec path
    that already does not exist. Point it at `deck.assets_dir` when the deck merge lands.

  Update them in the same change. Rerun the search before the release, because new callers may
  appear by then.

### 8. Remove `/fig:diff`

What it did: annotate the changed elements in Figma, and write an AS-IS/TO-BE table and a scope
callout into the task doc. The table is not read (decision 7). Looking at what changed is covered by
Dev Mode's *Compare changes*, with its limits: it compares a frame against its own version history,
or two components with each other — not two separate frames — and it needs a Dev Mode seat.

- Remove `skills/diff/`.
- `/fig:handoff` borrowed diff's write method ("the one line … by diff's method"). Move that method
  into handoff: for notion, insert after the `ui_section_heading` heading; for github, insert under
  that section, or add a comment when there is none; for markdown, follow 4; for none, print.
- Keys:
  - `ui_section_heading` stays, because handoff reads it.
  - `text_diff_max_len` stays, because `/fig:sync` reads it.
  - `annotation_category` and `scope_tags` go. diff was their only reader. `/fig:draw` mentions
    the category only to say it belongs to diff and must not be used (draw:118, :265). Remove both
    keys from `conventions.example.yaml` and from `draft-conventions.py:216`, and reword draw's two
    lines as "annotations carry no category".
- Routing lines that send work to diff become something else, or go. They sit in code, draw,
  handoff, setup (its list of skills that write), sketch and sync, and in `_common/trackers/README.md`
  around line 75. The fig README names diff under "The other half" (around lines 109–113), not in
  the cycle diagram. The same goes for the root READMEs' rows and the two-plugins picture if it
  names diff.
- The CHANGELOG entry says what replaces it: Dev Mode's *Compare changes* for looking, and no
  written AS-IS/TO-BE record.
- AS-IS reference sections that diff already cloned into files are left alone.
- **Consequence found in review: `/fig:sync` loses its main signal.** sync's first signal is the text
  difference between an AS-IS/TO-BE pair (`sync.pair_patterns`, sync:74-77), and diff was the only
  skill that made those pairs. Without them, sync falls back to scanning a section's text, which
  misses deletions and rewordings. draw:205 and :249 also still describe the AS-IS section as where
  before/after lives. How to respond is an open decision in the review (D1).

### 9. Shorter descriptions

Each `description`: one sentence on what it does and when, then the trigger phrases in both
languages. Behaviour detail moves into the body. Target 500 characters or fewer, 700 for the two
merged skills that carry several skills' triggers (designer's call). Characters, not bytes — the
unit Claude Code's listing caps use; today they run 389–1,212, about 14,800 in all. The listing
budget is shared with every other installed skill, so this is the part that pays even where nothing
is merged.

### 10. "Where the two meet"

`plugins/pm/README.md` says the two never call each other. Reword, and carry the same into both root
READMEs' *Where the two meet* and `.github/two-plugins.html` if the picture names it:

> Each works on its own. Installed together, `fig` reads the PRD where `pm` writes it and writes into
> task records through `pm`'s adapters. They still share two objects: the PRD and the task record.

### 11. Handoff: *Ready for dev* through the web app

**Status quo.**

- `use_figma` rejects both `saveVersionHistoryAsync` and `devStatus`. The latest Figma plugin's API
  reference no longer lists either (2.2.157; 2.2.127 still did), so the block is presumed to stand —
  not re-probed.
- The version pin already goes around it. Handoff saves the named version in the web app (*File →
  Save to version history*) through browser automation, and asks the person to save it under the
  given name when no browser is connected.
- *Ready for dev* went the other way: 3.26.0 removed the step and its keys outright, because it kept
  being offered as something a run could do.

**Proposal (designer's call, decision 8).** Bring *Ready for dev* back by the same route as the
version pin, not through `use_figma`:

- After the pin, select each chosen section in the web app and mark it *Ready for dev*. Figma then
  notifies the developers who follow the file, which is the signal a handover exists to send.
- It is a write to a shared file, so it goes through preview → go with the rest. No browser, the
  wrong account, or a seat without Dev Mode → list the sections and hand the marking to the person.
  Never say it was marked without reading the status back in the page.
- A new key `handoff.ready_for_dev` ships `null` (off). A team that marks *Ready for dev* turns it
  on. With it off, handoff behaves exactly as today and never offers the step. That keeps 3.26.0's
  point: nothing is offered that the run will not do.
- **Gate.** Click it through once on a real file, with a Full or Dev seat signed in, before this
  ships. The repository ships only calls that were run, and the seat on hand when this was written is
  View-only. If the probe fails, this section is dropped and handoff stays as it is.

## Later: Figma Specs

Not built now. This section reserves the place.

**What it is.** Figma Specs (open beta from 2026-10-15) are markdown documents in Figma — a
standalone file, or blocks embedded on a Design or FigJam canvas (`SPEC_BLOCK` nodes). The official
Figma plugin's `figma-spec` skill reads and writes them through the Figma MCP (`figma.spec.getContent`
/ `setContent` / `editContent` / `comments.*`), after checking with `whoami` that the plan has
`specs_enabled`.

**Where it fits.**

- `fig`: `qa.baseline.prd.type: figma-spec`, `ref` a Spec link. Reading costs no new connector — fig
  already requires the Figma MCP. This is the strongest reason to do it.
- `pm`: `prd.target: figma-spec`. Here it adds a connector `pm` does not need today, and needs code in
  `preflight.py` (the prd row has a fixed no-connector set and no adapter kind) and in prd's publish
  step. It is not a drop-in adapter file.
- A Spec body is GitHub-flavoured markdown, so a local markdown PRD can stay the source and a Spec
  be one place it is published. Canvas embeds and comment markers (`[comment:<uuid>]…`) will not
  survive a round trip into plain markdown (assumption — check when probing).

**Before building.** Probe every call against a plan with Specs enabled; a View seat cannot prove the
writes. Use `editContent` for anything but an empty first draft.

**Terms.** In this repository "spec" already means the PRD — `spec_url`, `link_rows.spec`, "the spec
entry". Write "Figma Spec" for Figma's documents, always with the prefix. Renaming `spec_url` to
`prd_url` belongs with this work, not before it.

## Done when

- **Fresh directory, both plugins, no config:**
  - `/pm:prd` writes `docs/prd/<product>.md`.
  - `/pm:task draft` on pasted text writes `tasks/<task>.md`.
  - `/fig:draw` reads that PRD through step 3.
  - `/fig:handoff` writes its line into the task file.
- **The same, with `pm` uninstalled:** `/fig:handoff` prints its line plus the one-line note.
  Preflight still passes. With a config that writes `task_tracker.type: markdown`, its row shows
  `attention`.
- **No silent new writes:** a fig config with no `task_tracker` and a pm config on Notion still
  prints, and writes nothing.
- **Existing configs:** for a config that sets Notion explicitly, `resolve-config.py` gives the same
  value for every key it writes, before and after. Floor-only differences are listed and explained.
- **The guard:** a config with `task.record.ref` and no `type` stops with the authored-key message.
- **Merged decks:** `/fig:deck` with no assets runs the measuring step.
- **Merged tasks:** `/pm:task` runs all three modes. The old names appear nowhere outside CHANGELOG
  history.
- **Diff removed:** no `/fig:diff` reference is left outside CHANGELOG history, and handoff carries
  its own write method.
- **Ready for dev:**
  - Either the probe in 11 passed and was recorded — with `handoff.ready_for_dev` on, the sections
    show *Ready for dev* when the page is read back, and with it off the step never appears.
  - Or the probe failed and 11 was dropped.
- **Descriptions:** every one is 500 characters or fewer.
- **Checks and docs:** `bash tools/verify-all.sh` passes, and both root READMEs are updated, English
  first.

## Designer's calls — check these while reading

1. A string `qa.baseline.prd` is read as Notion.
2. `spec_url`'s type comes from its value.
3. Fallback to `pm`'s `prd.markdown.dir` when `pm` is installed.
4. Without `pm`, a markdown task tracker prints and says why.
5. Publish and sync keep stopping with no mirror; no local mirror.
6. `task.record.type` becomes an authored key once `ref` is written, for every skill that reads
   `task.record`, `/pm:log` included. The same applies to `task_tracker.type` once `task_tracker.ref`
   is written. Each guard fires only on a ref a person wrote, never on the floor's.
7. Descriptions capped at 500 characters (700 for the merged two).
8. Figma Specs: this section only, no reserved values in code.
9. fig's `task_tracker.type` ships unset. Unset borrows `pm`'s record only when that record is
   markdown.
10. A null `ui_section_heading` writes under "Design changes".
11. Step 3 of the PRD order covers `prd.target: git` as well, since it also writes markdown to
    `prd.markdown.dir`.
12. *Ready for dev* comes back through the web app. It ships off, under a new `handoff.ready_for_dev`
    key, and only after a live probe; without the probe it stays out.

## Left to the builder

- How `fig` locates the installed `pm` (subject to the proof condition in 4).
- Version numbers and how each CHANGELOG entry reads.
- `verify.py` changes the removals and renames need.
- Exact wording of the stop and fallback messages.
