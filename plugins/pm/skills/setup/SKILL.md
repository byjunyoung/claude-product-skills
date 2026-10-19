---
name: setup
description: Sets up pm-conventions.yaml. It starts local — tasks, specs and a daily log as markdown files, no other tool needed — and attaches a tracker after, reading its schema rather than guessing and querying ids nobody finds by hand (board fields, option ids, issue types). It asks what publishing and syncing need, and leaves null what nobody can answer. Run it first on a new workspace. Triggers - "/pm:setup", "set up the pm config", "read my tracker schema", "pm 설정 만들어줘", "트래커 스키마 읽어줘", "일감 설정 초안".
allowed-tools: AskUserQuestion, Read, Write, Bash, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-get-users, mcp__plugin_github_github__list_issues, mcp__plugin_github_github__search_issues, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__get_me, mcp__plugin_github_github__list_repository_collaborators
---

# pm:setup — read the schemas, draft the config

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install pm@byjunyoung`), rather than improvising what the scripts do.

The `pm` skills read every value from `pm-conventions.yaml`. This is where that file comes from.

**It reads schemas rather than inferring from samples.** A design file has no schema, so `/fig:setup` has to count occurrences and take the dominant value. A document database and an issue tracker both publish theirs — property names, select options, labels, field ids. So this skill queries, and only interviews for what a schema genuinely cannot answer.

**What it never does is guess.** A value the schema does not settle is written as `null`, and `null` means that check or that step is skipped. Filling a blank with a plausible value is how a config ends up describing a workspace nobody has.

## When to invoke

- Opening these skills on a new workspace, a new company, or a new tracker
- The tracker was restructured — fields renamed, a board rebuilt, options changed
- `/pm:task publish` stopped with "this project is not mapped"
- You need the board ids for `mirror_extras` and do not want to write GraphQL by hand

## When NOT to invoke

- Drafting a task's context table → `/pm:task draft`
- Design file conventions → `/fig:setup`. Separate file, separate config

## Inputs

- `record` (optional): the planning-side list — a database url, a repo, or a directory
- `mirror` (optional): the engineering tracker — usually `owner/repo`
- `out` (optional): where to write. Defaults to `~/.claude/pm-conventions.yaml`; pass `./pm-conventions.yaml` for a project-local one. On the local start — specs or tasks kept local — it is `<repo>/pm-conventions.yaml` unless one was passed, and the paths in it are relative to that repository
- `side` (optional): `record`, `mirror`, or `both` (the default). For when the two sides are reachable from different machines — the doc tool from one, the tracker from another. A run with a side writes only that side's keys into `out` and leaves the other side's byte for byte, so two runs on two machines finish one file

Anything omitted is asked for at the start, together, in one round.

## How it runs — the ladder

Nine steps, and the person sees them before the first question. Show this ladder at the
start, and at every transition say which step is beginning and whether it reads or writes:

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

**Open with what this produces, before asking anything.** One paragraph: after this, a
request pasted from chat becomes a task with your own rows (`/pm:task draft`), kept as a
markdown file beside your specs and a daily log — nothing has to be installed or connected
first. A tracker attaches whenever there is one, and from then on a task becomes a ticket where
engineering looks (`/pm:task publish`) and the two stay reconciled (`/pm:task sync`). A couple
of minutes for the local start, five to ten with a tracker to read. Nothing is written into
your tools; what is written is local — a few folders, a README and one settings file — and each
is shown first.

## Talking to the person

The file speaks in keys. The questions do not.

| The key | Ask it as | Always offered |
|---|---|---|
| `prd.target` | Where do your specs live? — markdown files here, markdown in a git repo with a pull request per change, Notion pages | local files — recommended |
| `task.record` | Where do you first write a task down? — markdown files here, a Notion database, GitHub issues, somewhere else | local files — recommended, and the answer to "nothing yet" · a tool this plugin has never seen |
| `task.mirror` | Where does engineering watch progress? — nowhere yet, the same place, a GitHub repo, somewhere else | nowhere yet — recommended for a local start · the same place |
| `sources.chat_type` | Where do requests arrive as chat? — Slack, another chat tool, none | none — a thread can still be pasted in as text |
| `sources.calendar_type` | Which calendar should the daily log read? — Google Calendar, another calendar, none | none — the log leaves meetings out |
| `task.record.scope` | Does the record list hold only your team's work, or everything engineering tracks? — `members` keeps it to tickets assigned to someone on `assignee_map` | members — a ticket held by somebody outside the map gets no record |
| `task.link_property` | Which field on a task should hold the ticket's link? — the url fields the schema has; for a markdown record, `ticket`, the key its skeleton already carries | none exists — it has to be created first |
| `task.status_map` | When a spec is finished, which board column should its ticket sit in? | leave it blank — whoever runs the board fills it |
| `task.properties.progress` · `.start` · `.end` | Does a task record say how far along it is, and when it started and finished? — name those properties | leave them blank — the progress and schedule checks stay off |
| `task.required_fields` | For each task status, which fields must already be filled — a start date once work begins, an end date once it is done? | leave it blank — the check stays off |
| `task.field_owner` | When the two sides disagree on a title or an assignee, which one is right? | leave it blank — it is reported and left alone |
| `task.hierarchy.parent_kind` | Are tasks grouped under something bigger — an epic, a project? | none — a flat list |
| `task.context_rows` | The rows your team asks about a task — these defaults, or your own words | the defaults |
| `task.contract.level` | Which ticket carries the done conditions and the QA list — each task, or the parent it hangs under? | none — no contract, a summary and links only · leave it blank — kept out of the file, so `/pm:task publish` stops and names the key before it files anything — answer it by running `/pm:setup` again. `/pm:task sync` stops the same way |
| `task.progress_source` | Should a task's progress be counted from the ticked boxes of its done conditions and QA list? | leave it blank — the progress and schedule checks stay off |
| `log.enabled` | Keep a daily log — what moved, what was on the calendar, what was decided? It is written only when you run `/pm:log` | no — `/pm:log` says it is off when called · leave it blank — not written, so the bundled default applies and the log is on |
| `log.me.tracker_user_id` | Which of the tracker's users are you? — the user list the schema read | leave it blank — the log keeps every row under yours and says so |
| `log.sources.calendar` · `.chat_channels` · `.notes_channel` | Which calendar, which channels to read for the day, and is there a channel only you write notes in? | leave them blank — each is skipped and named in the log |
| `prd.notion.template` · `.inline_db` · `.task_db` · `.parent` | Which page is your spec template, and under which page do new specs go? — the template's inline databases are read from it, not asked | leave them blank — `/pm:prd` asks for a page the first time it writes |

**When a script stops, say what it means — never the code or the path.**

| The script says | Say to the person |
|---|---|
| preflight `Not ready` | what is missing and the one thing that fixes it, from the `Fix first` lines |
| preflight `Cannot tell` | connections could not be checked on this machine; confirm them, or run where Claude Code is installed |
| `… is not supported yet` (exit 3) | "this tool isn't supported yet — I can write the support from what's connected here" — then 4c |
| `… supported as the other side` (exit 4) | "this tool is set up as the {other} side; I can add the {this} side" — then 4c |
| `… is not set in …, while … is` (`--authored`, in ⑦) | which setting was written without the one it needs beside it, and that this run writes the missing one |

Three rules —

- **One question per turn in ⑤. ② is the only grouped round** — five questions, asked as two calls, since one call takes at most four
- **Every question carries options, a recommendation grounded in what ① and ④ saw, and "leave it blank"** — a blank is `null`, written with the question beside it, and it is a complete answer, not a failure to answer
- **Say what is being read before reading it, and what was found after.** A step that takes seconds in silence reads as a hang

## Procedure

### 1. Check this machine — can it run at all (required)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/preflight.py
```

**A missing connector does not announce itself.** A skill cannot call a tool it was never
given, and it does not fail loudly when one is absent — the run simply comes back thin, and
that reads as the skill having found nothing. This is the one step that says so out loud.

Read the person the verdict and the fix lines in their words — the table underneath is detail for a second look. Then judge it:

- **FAIL** — stop and hand over the fix lines. Nothing below this works without them
- **UNKNOWN** — the claude CLI is not on this machine, so the connectors could not be checked. Confirm them by hand before going on, or run this where the CLI is
- **Worth knowing** lines are not blockers — one sentence each, then move on
- **absent** on an optional connector — fine as it is. Say so, because a config key pointed
  there in a later step will not reach it
- **Nothing beyond the host can fail yet.** Whether GitHub matters depends on an answer ②
  has not asked for, so on a machine with no config every connector reads as optional and the
  summary says so. ② runs the check again with the answers, and that pass is the verdict

### 2. Where your work lives

Ask once, grouped, in the words of the table above — five questions: where specs live, where a task is first written down, where engineering watches progress, which chat tool requests arrive in, and which calendar the log reads. One question call takes at most four, so the round is two calls back to back — specs, tasks and engineering in the first, chat and the calendar in the second. **Options, not a blank line** — people recognise their tool from a list and cannot name its "type". Local files are the recommended answer for specs and tasks, and "nowhere yet" for engineering: that start needs nothing installed, and a tool attaches later without moving anything. For chat and the calendar, recommend what ① found connected, and `none` where nothing was.

**"They are the same place" is a real answer.** Then `mirror.type` is `none`, `/pm:task sync` has nothing to reconcile, and half the config below does not apply. Do not talk anyone into a second tracker.

**"Nothing yet" is a real answer too** — it is the local start, and ③ lays it out. And **a tool this plugin has never seen is not a wrong answer** — write its type as the team calls it, and 4c drafts the adapter.

**With `side: record` or `side: mirror`, ask only that side's question** — where a task is first written, or where engineering watches. Specs, chat and the calendar belong to a run with no `side`, the only run that writes them.

**Then run the preflight again with what was named**, so its verdict means something. Where ② named no tool, there is nothing to require and the first pass stands:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/preflight.py --require Notion,GitHub   # whichever ② named
```

Two rows decide a GitHub mirror: the `gh` CLI — the tracker adapter runs on it, not on the
connector — and the tracker itself, which the check tries to open as the account `gh` is logged
in to. **A `missing` here is a fact about this machine, not about the schema.** Either fix it
with the line the row carries, or finish the side that is reachable here and run `side: mirror`
on the machine that can reach the other. Do not interview around a side that cannot be read —
a value typed from memory in place of a schema read is exactly the config this skill exists to
prevent.

### 3. Lay out the local start

The default. One markdown repository holds whatever ② left local, and every tool attaches later without moving anything:

```
<repo>/
  pm-conventions.yaml    written in ⑥ — only what was settled, nothing copied from the defaults. This is `out`
  docs/prd/              one file per product — prd.markdown.dir, split by product
  tasks/                 one file per task, its front matter the properties — trackers/markdown.md
  logs/YYYY/MM/          one file per day — /pm:log; laid out because log.enabled is on
  highlights/            /pm:log-review's accumulating document
  pm-adapters/           adapters drafted for tools attached later
  README.md              what lives where, and the loop: draft → (publish and sync once a tracker is attached)
```

A part ② sent to a tool leaves the tree — `tasks/` where the record is a tracker, `docs/prd/` where specs live in Notion — and ④ attaches it instead.

Why this and not a tool: it needs nothing installed, git is the audit trail (`/pm:log` reads what moved from it), and a tracker joins later as the mirror — `side: mirror` on the machine that can see it — with the record untouched.

Ask two things: where the repository is (an existing directory, or one to create), and whether to `git init` where it is not one. Then interview only what markdown cannot supply — `task.properties.projects` (the products, one file each under `docs/prd/`), `task.context_rows` (the defaults, in `meta.language`), `task.properties.priority` (the defaults unless the team says otherwise). **The config carries only what ② and ③ settled.** A key nobody was asked about stays out of the file, so the plugin's own default keeps applying — and a later change to that default reaches this file too. ②'s answers are always written, even where they match the default: where tasks and specs live is a decision, and `task.record.ref` goes with `task.record.type`. Only "the defaults" as an answer to `task.context_rows` or `task.properties.priority`, taken as they ship, is left out the same way.

**The config goes into the repository.** On this start `out` is `<repo>/pm-conventions.yaml` unless one was passed: `./tasks`, `./logs` and `./docs/prd` are relative to the repository, and in the user-wide `~/.claude` file they would point wherever a session happened to start. That holds where specs or tasks stay local. Where ② sent both to tools, ③ lays out only `logs/`, and `out` keeps `~/.claude/pm-conventions.yaml`.

Preview the tree and the README, with the config lines ② and ③ settled beside them, and on a go create the folders and the README. The config itself is written once, in ⑥, after ⑤ has asked its questions. Nothing here is an external write, but it is somebody's working directory: create only what is listed, and inside a directory that already has content of its own, say which files are new. Where ⑤ turns the log off, remove `logs/` while it is still empty, and the README's line for it.

**Where the tree already exists** — a run made again to attach a tracker — add only what is missing. A README somebody has edited is never overwritten; say what it no longer covers instead.

Where ② named no tracker, and no chat tool or calendar this plugin has never seen, ④ has nothing to do — go on to ⑤. A run with `side: mirror` is attaching a tracker to a start that already exists, and skips this step.

### 4. Attach a tracker

Only where ② named one — a tool for the record, the mirror, or both. Where it named none, the local start is complete without this step. It is also how a tracker joins later: run `/pm:setup` again and name the tool in ②.

A chat tool or calendar ② named comes here too, only to check that its adapter exists:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind sources --type {sources.chat_type} --role chat
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind sources --type {sources.calendar_type} --role calendar
```

Exit 3 is a tool this plugin has never seen — 4c drafts it, under `sources/`. There is no schema to read and nothing to pair for these; with no tracker named, go on to ⑤ after 4c.

#### 4a. Read the record side's schema

Read the tracker's own adapter first — the calls, and what the tool cannot do:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type {record.type} --role record
```

Exit 3 means no adapter exists for that type, exit 4 that the one there answers only as a mirror: go to 4c, draft one from what is connected here, and come back.

| Read | Fills |
|---|---|
| Property names and types | `task.context_rows` candidates, and which property could hold the ticket url |
| Select options on the status property | `task.properties.status_initial`, `task.status_map` keys |
| Select options on priority | `task.properties.priority` |
| Select options on project | `task.properties.projects` |
| The user list | `task.assignee_map` left-hand side |

**`link_property` is the one that matters most and the one a schema cannot decide.** List every url-typed property as candidates and ask. Where none exists, say so plainly: this property has to be created before `/pm:task publish` can work, because it is the only thing matching runs on. For a markdown record, recommend `ticket` — the key the record skeleton already carries.

**Where the schema read itself fails** — a database the connected account cannot see, a tracker type with no adapter — stop this side: write its keys as `null` with the comment `# unreachable from this machine`, carry on with the other, and say in the report which machine or account can finish it.

#### 4b. Read the mirror's schema

Read the mirror's adapter, then run the id queries it carries:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type {mirror.type} --role mirror
```

Exit 3 means no adapter exists for that type, exit 4 that the one there answers only as a record — 4c, then back here.

| Read | Fills |
|---|---|
| Label list | `task.label_map.project` and `.priority` candidates |
| Board fields and their single-select options | `task.mirror_extras` — field ids, option ids |
| Board node id | `task.mirror_extras` |
| Issue types available | `task.mirror_extras`, where the tracker has typed issues |
| Collaborators | `task.assignee_map` right-hand side |
| A handful of existing tickets | `task.ticket.title` pattern, `task.hierarchy.parent_kind` and `parent_title` |
| Milestones | `task.hierarchy.milestone_format`, `milestone_projects` |
| Ticket templates the tracker publishes | `task.template.task` and `.parent` |

**A template is found, not asked for.** Where the tracker publishes ticket templates, list them and match one to each level — the task's, and the parent kind's. Two candidates for a level is a question, not a guess. Where there are none, both keys stay `null` and the section names in the config decide alone, which is the ordinary answer for a tracker nobody has set a template on.

**These queries are the reason this skill exists.** Board field ids and single-select option ids are not visible in any user interface, and a person configuring by hand simply cannot find them.

Three things have to line up for them, and only the first shows in any error message: the account `gh` is logged in to can see the repo — a personal account against a company org gets a 404 that reads as if the repo did not exist; that account is a member of the org; and its token carries `read:project`, without which the repo answers and the board queries come back empty. The preflight row for `gh` names the account and the scopes. Read it before reading a 404 as a missing repo.

#### 4c. A tool with no adapter — draft one here

Exit 3 from `adapter.py` on either side means the type names a tool this plugin has never seen. That is not a dead end, and not a reason to type calls from memory. The contract is `${CLAUDE_PLUGIN_ROOT}/_common/trackers/README.md` (chat and calendar: `sources/README.md`); the draft is built from what is actually connected:

1. **Find the connector** in the preflight table — the row named by the type. Absent means stop: an adapter cannot be drafted for a tool this machine cannot reach
2. **List the tools it exposes** and read their descriptions. The names are what the adapter will carry, exactly as this machine has them. Put the connector's name on a `connector:` line near the top, and the sides the file answers for on a `roles:` line — preflight reads the first to know which connector this type requires, `adapter.py` the second to refuse the file for a side it does not serve
3. **Probe the read-only ones against the real workspace** — the schema, the list, one record — and keep the call that returned, pasted as run. Whether the list is exhaustive or a search is answered by what the call actually does, not by what its name suggests
4. **Answer the write questions with the tool that would do it, marked `(unverified)`.** The first run in any `/pm:task` mode that uses a marked call clears its mark once the call succeeds, and a call that fails keeps it and stops that run — `/pm:task` says how
5. **"Things that bite" starts with one line — `nothing recovered yet`.** It is filled by what bites
6. **Preview, then write** to the last dir in `adapters.dirs` — `{dir}/trackers/<type>.md` or `{dir}/sources/<type>.md` — never inside the plugin, which an update overwrites. Then go back to the step that stopped

The report lists every answer marked unverified. A config whose adapter is half verified is usable; one whose adapter was guessed is not, and the mark is what tells them apart. A mark on a source call that only `/pm:log` runs — a calendar read, say — stays until somebody removes it by hand, since nothing that clears marks runs that call; the report says so beside it.

#### 4d. Pair the two sides

`label_map`, `assignee_map` and `status_map` join names across systems, and neither system knows about the other.

- **Propose pairs by name similarity, then confirm them.** A record project called `Store App` and a label called `project: Store` are almost certainly the same thing — almost. Show the proposed pairing and let it be corrected in one pass
- **A record value with no counterpart stays unmapped**, and unmapped means "not mirrored". That is a legitimate state, and it is what makes `/pm:task publish` stop cleanly rather than invent a label
- **Never invent a label to complete a pair.** A missing ticket is easy to spot later; a ticket under a wrong label is not
- **`status_map` will not fall out of name similarity — ask it.** A record's statuses describe how far the planning side has got; a board's columns describe whose turn it is. `Not started` and `Backlog` may line up, but the two in the middle rarely do, and a wrong guess seats finished specs in the backlog column where the engineering side reads them as untouched. Show the two lists side by side and ask which column each status should file into, saying that a status left unpaired keeps the board's own default — and that no answer at all is also an answer: an empty `status_map` seats nothing, and the file carries the question for whoever runs the board

### 5. Ask what no schema knows

One at a time, most consequential first, each with a recommendation grounded in what ① and ④ actually saw. Show the whole list first so the scale is clear — the same shape `/fig:setup` uses. Ask only the questions that apply: most of them belong to a mirror, and a local start has a handful.

**Every question here has a "do not know" answer, and it is `null`.** Say so before asking. Someone new to a team cannot say which column a finished spec should sit in or which side owns the assignee field — that is knowledge about how the team works, not about the tools, and the person who has it runs the board. A `null` is written with the question beside it as a comment, so whoever can answer finds it in the file rather than in a chat history. Never fill it with the recommendation just because a recommendation was offered.

**One exception: `task.contract.level`.** The skills check whether anybody wrote it, and a written `null` would pass that check with no level behind it. Its blank keeps the key out of the file — the question stays, as a comment — so `/pm:task publish` stops and names the key rather than filing on a level nobody chose — answer it by running `/pm:setup` again. `/pm:task sync` stops the same way.

Where a mirror is attached:

- `task.contract.level` — "Which ticket carries the done conditions and the QA list — each task, or the parent it hangs under?" `/pm:task publish` and `/pm:task sync` will not run on a level the plugin supplied, so a config that never answers this stops the next command. Recommend from where review happens on the tickets 4b read; `none` turns the contract off
- `task.progress_source` — is a task's progress counted from the ticked fraction of its done conditions and QA list (`contract`), or not at all (`null`)? `/pm:task sync` needs it answered wherever the record names a progress property
- `hierarchy.parent_kind` — do tasks hang under something, and what is it called. Existing ticket titles usually give this away
- `hierarchy.milestone_on` — which level carries a version, if any
- `hierarchy.milestone_projects` — which projects use them. Often only one does
- `properties.version` and `version_unset` — does the task list have a column showing which milestone a task's ticket sits under, and what an open task with none should say. The tracker owns the value and the skills only copy it, so this is a question about the list's columns, not about who decides a release. Recommend it only where ④ found such a property; `null` is the ordinary answer
- `field_owner` — which side wins per field. **The default is deliberately small**; a field nobody claims is reported as a difference and left alone, which is safer than an arbitrary winner
- `policy.doc` — is this tracker run by written rules of its own, and where do they live. **No schema answers this**, and it is the one setting that outranks everything else in the file: what may carry a version, who may close what, which labels a kind of ticket has to have. A team that has such a document usually knows exactly where it is; a team that does not says so in a word, and `null` is the honest answer

Always:

- `context_rows` — the defaults, or what this team actually asks. Skip it where ③ already asked
- `log.enabled` — keep a daily log. The recommendation is yes: it is written only when `/pm:log` is called by name, and the local start already has a folder for it. Either answer is written — it is a decision, not a default taken as it ships. A blank is not written: the bundled default applies, and the log is on

Only where it applies:

- `log.me.tracker_user_id` — only for a shared tracker, where the record holds other people's tasks too. Offer the users 4a read
- `log.sources.calendar`, `log.sources.chat_channels` and `log.sources.notes_channel` — only where ② named the tool. The calendar's id, the channels worth reading for the day, and a channel only this person writes notes in
- Where `prd.target` is `notion`: `prd.notion.template`; the ids of its inline databases, `prd.notion.inline_db.users` and `prd.notion.inline_db.features`, read from the template page with `notion-fetch` rather than asked; `prd.notion.task_db`; and `prd.notion.parent`, the page a new document goes under when there is no template

With a `side`, ask only that side's questions — the `prd`, `sources` and `log` keys are left to a run with none.

### 6. Write the file

Preview in three groups — what the schema settled, what the person answered, what stayed blank — and get the go. Then write to `out`, every inferred value carrying its evidence as a line comment, in the same form `/fig:setup` uses.

**Only what ③–⑤ settled or a schema showed is written** — ②'s answers among them, carried through ③. A key nobody asked about is not written, so a later change to the plugin's default reaches it; a file that copies the defaults in full freezes them on the day setup ran. Where the file already exists — an earlier run wrote it — read it first and change only the keys this run settled.

Two keys are written in pairs, because the default no longer completes them: `task.record.ref` goes with `task.record.type`, and a type other than `markdown` goes with `task.link_property`. ⑦ checks both.

```yaml
task:
  properties:
    projects: [Store App, Kiosk, Admin]   # 3 select options read from the schema
  label_map:
    project:
      Store App: "project: Store"         # paired by name, confirmed
      Kiosk:     "project: Kiosk"         # paired by name, confirmed
      Admin:     null                     # no matching label — not mirrored
  hierarchy:
    parent_kind: Epic                     # 12 of 14 open tickets titled [EPIC]
    milestone_on: parent                  # no task carries a milestone; 8 parents do
  status_map: {}                          # not settled — which column should a finished spec sit in? ask whoever runs the board
  mirror_extras:
    project_node_id: null                 # unreachable from this machine — run `side: mirror` where gh can see the org
```

**A `null` is not a gap to be filled later by guessing.** It says the schema did not settle it, so the check or the step is skipped until a person writes a value.

**With a `side`, read the existing file first** and rewrite only the keys that side owns. Record: `task.record`, `task.properties`, `task.required_fields`, `task.context_rows`, `task.link_property`, `task.notion`. Mirror: `task.mirror`, `task.mirror_extras`, `task.ticket`, `task.hierarchy`, `task.template`, `task.policy`, `task.contract`, `task.progress_source`. The maps that join the two — `task.label_map`, `task.assignee_map`, `task.status_map` — and `task.field_owner` belong to whichever run can see both sides, and are left alone otherwise. The `prd`, `sources` and `log` sections are written only by a run with no `side`. Everything else in the file stays byte for byte, comments included. An adapter drafted in 4c is written where 4c says, never into this file.

### 7. Prove it

**Do not stop at writing the file.** Three read-only checks.

The file resolves, and it is the one just written:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml --where
```

It prints the strongest layer — the file every skill will actually read. Where it names another, that one wins: a `./pm-conventions.yaml` in the directory the session runs in outranks one written to `~/.claude`. Say which, and do not count it as a pass.

Every key that has to be written beside another was:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml --authored task.record.type,task.record.ref,task.link_property
```

Exit 0. Exit 3 names the half ⑥ left out — write it, and run this again.

For a markdown record, the folder reads:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py list --dir {task.record.ref}
```

Run it from the repository ③ laid out — a relative `{task.record.ref}` resolves against the directory the session runs in. Exit 0; an empty folder prints nothing, which is right for a start. Exit 2 means the path is a file, not a folder. **Exit 0 with `does not exist yet — no records` on stderr is a fail here:** ③ has just created that folder, so the command ran from the wrong directory or `task.record.ref` points somewhere else. Say which before going on.

With a mirror attached, the pair check follows. Take one existing task that is already filed on both sides and check that the config finds its pair — the link property resolves, the project maps to the label the ticket actually carries, the assignee maps to the username actually on it.

**A config that cannot re-derive a pair that already exists is wrong**, and this is the cheapest place to find that out. Report what was checked and what it matched.

With one side unreachable the pair cannot be checked. Say `not checked` in the report rather than checking the half that can be read and calling it a pass.

### 8. First result — one message, one table, nothing written

**Do not end on a file.** Ask for one request the person has to hand — a chat message, a
sentence someone said in a meeting, pasted or linked — and run `/pm:task draft`'s reading and
sorting on it, stopping at the preview: the context table in `task.context_rows`, a row filled
for each thing the source actually said and `TBD` where it did not. Nothing is written, which
is what makes it safe to run before the config has been used once.

Where there is nothing to hand, use what ⑦ read: show one existing task's context table
as the tool has it. A fresh local start has no task yet, and a sentence the person types now
serves as well. The point is the same — the person sees their own words in the shape the
skills will use.

Then close with the commands that apply, in the order they are used. With `mirror.type: none`:

    /pm:task draft <message or link>     a request → a task file with this table
    /pm:prd                              a spec, written where prd.target points
    /pm:log                              today's log — runs only when called by name

Say that publishing and syncing arrive with a tracker, and that `task.mirror` is the key that attaches one — through ④, whenever there is one. With a mirror attached:

    /pm:task draft <message or link>     a request → a task with this table
    /pm:task publish <task url or file>  a task → a ticket where engineering looks
    /pm:task sync                        both sides reconciled — any time

Where the config went into `<repo>`, say that these run in Claude Code opened in `<repo>`: the settings there are read only by a session started in it.

### 9. Share it — only where somebody else runs these too

Ask once, at the end: **does anybody else run these skills against the same tracker?** A "no"
ends the step in a sentence — say the file is theirs alone and this can be done later — and
nothing is written. Do not guess the answer: one machine cannot see whether its config is a
copy of somebody else's, and a run that assumes a team is a run that nags a person working
alone.

Where the answer is yes, the config stops being one person's file and becomes a copy on every
machine, and a copy has no way of knowing its own age. The failure is quiet: every run
succeeds, and the first sign that somebody was working from an old one is what it wrote into
the tracker. Anything that asks the file to declare its own version fails here twice — a file
written before a key existed cannot say anything about that key, and whoever reads the warning
can silence it by editing the stamp rather than the file.

So the copy is not asked. **Keep the file in a repository and symlink it into `~/.claude`.**
The skills read where their config came from and say when a copy has fallen behind, and that
answer needs nothing kept true by hand.

- **A repository already exists** — take its url, clone it, and replace the local file with a
  symlink. Show the existing file's diff against the shared one first: a value somebody
  entered by hand is easy to erase here and hard to recover
- **Nobody has made one yet** — say what goes in it, that it holds the config and nothing else,
  and that it has to be private where the config carries ids or account names. Creating it and
  granting access is theirs to do; offer to write the file into the clone once it exists
- **Neither** — a shared drive, a pasted block, anything else still works. The skills simply
  have less to say about it: the age of the file is all they can report, not how far behind it
  is. Say that plainly rather than arguing for the repository

Then offer the line that keeps it current, and say what it does before writing it:

```json
{ "env": { "CLAUDE_SHARED_CONFIG": "pull" } }
```

The default without it looks and reports but changes no file. `pull` fast-forwards the work
tree at the start of a session, and it is skipped whenever the tree has uncommitted work.
`off` turns the whole thing off. Write it into settings only with a go — it is the one part of
this that acts on its own afterwards.

## Report

Lead with three lines a person can act on — what you have now, what stayed blank and who can
fill it, what to run next. The lists below are the detail.

- Which keys came from a schema, and which were interviewed
- Which were left `null`, and what each one blocks — and a `task.contract.level` left blank, which is kept out of the file: `/pm:task publish` and `/pm:task sync` stop on it until `/pm:setup` answers it, so say so beside the commands ⑧ names
- Which were left out because nobody was asked — they follow the plugin's defaults, later changes included
- Unmapped projects and users, listed by name — these are the ones that will be skipped
- ⑦'s checks — the file `--where` named, whether the pairs were written, and the folder read for a markdown record — then the pairing check where a mirror is attached: passed against which task, or `not checked`, and why
- Which side this run wrote, and what was left for another machine
- Where the mirror is GitHub, the account `gh` was on — so a later 404 can be read against it
- Adapters drafted in 4c — where each was written, and which of its answers are still `(unverified)`
- For the local start: the tree ③ created, and which parts ② sent to a tool instead. Where the config went into `<repo>`, that the next commands run in Claude Code opened in `<repo>` — the settings there are read only by a session started in it
