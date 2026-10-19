# Tracker adapters — what one file has to answer

The skills here do not know any tracker. They know a **record** (where a task is planned) and
a **mirror** (where engineering tracks it), and they read the calls for each from one file:
`trackers/<type>.md`, where `<type>` is the word the config uses in `task.record.type` or
`task.mirror.type`. Notion, GitHub and markdown ship. Anything else is a file somebody writes —
and `/pm:setup` writes the first draft from the tools actually connected on the machine.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type linear
```

That prints the file to read. Bundled files sit here; yours live in `adapters.dirs` (by
default `~/.claude/pm-adapters/trackers/` and `./pm-adapters/trackers/`), outside the plugin
so an update does not overwrite them. Later dirs cover earlier, so a file of yours named
`notion.md` replaces the bundled one. **Exit 3 means no adapter exists for that type**, and
every skill stops on it rather than improvising the calls.

## The two lines the scripts read

Near the top of the file:

```
connector: Google Drive        # the connector's name as `claude mcp list` prints it
roles: record                  # the sides this file answers for — record, mirror, or both
```

`connector:` is how preflight knows which connector to require for a type — the word a team
writes in the config (`gsheet`) and the connector's name are rarely the same. `roles:` is how
`adapter.py --role` refuses to hand a mirror-only file to a skill reading the record side: the
bundled GitHub file answers as a mirror, the Notion and markdown files as records, and a config
that puts one on the other side gets exit 4 with that sentence rather than a skill improvising
the missing half. `verify.py` fails a bundled adapter that lacks either line.

## The rule the bundled files keep

**Every call in an adapter was run, and every warning was hit.** The GitHub file says a 503
does not mean the issue was not created because that happened; the Notion file says search is
not a listing because rows went missing that way. An adapter written from documentation alone
has none of that, which is why this plugin does not ship one for a tool nobody here has used.
When you draft one, the same rule applies: the first version carries the calls that worked
today, and "Things that bite" grows as they bite.

## What the file has to answer

A skill reads the whole file before its first call, then looks for the answer it needs. The
headings are yours; the questions are not. A question the tool cannot answer is answered with
*how it cannot* — that sentence is what the coverage line in a report is built from.

### As the record — `task.record.type`

| Question | Who asks | What the answer carries |
|---|---|---|
| **The schema** — property names and types, the options of every select, the user list | `/pm:setup` | The call, and which property could hold the mirror's url |
| **The list** — every record with title, project, group, priority, status, assignee, and the link property | `/pm:task sync`, `/pm:log` | The call, and whether it is **exhaustive**. Where it is a search, say so and say what a search misses |
| **One record** — its properties and its body | `/pm:task draft`, `/pm:task publish` | The call. Which part of the body is the context table |
| **What moved on a day** — rows last edited on a date, split by assignee | `/pm:log` | Filter on last-edited, never created. How the day filter is applied, and whether it is exact |
| **A new record** — with the properties the interview settled and the context table as its body | `/pm:task draft` | The call. Whether a database template is applied on create — usually not, which is what `task.notion.body_template` and its equivalents are for |
| **Writing the link property** | `/pm:task publish`, `/pm:task sync` | The call. This is the one property matching runs on, so say how to verify it landed |
| **Appending a change summary** — one dated line after what is already there | `/pm:task publish` | Append, never replace. How to catch the end of the existing text |
| **Appending a line under a heading** — the change summary, and `/fig:handoff`'s line under `task.design_heading` | `/pm:task publish`, `/fig:handoff` | Append after what is already in that section; add the heading when it is missing; never a second heading |
| **A user directory** — id to display name | `/pm:log` | The call, so a name is looked up rather than guessed |

### As the mirror — `task.mirror.type`

| Question | Who asks | What the answer carries |
|---|---|---|
| **Every ticket** — title, state, labels, parent, milestone, url, **open or closed** | `/pm:task sync` | The exhaustive read, and where a listing truncates silently. Closed tickets are where every `duplicate` and `resurrected` verdict lives, so a limit that drops the oldest drops the diagnosis |
| **Labels, board fields and their option ids, issue types, collaborators, milestones** | `/pm:setup` | The queries. These are the ids no screen shows, and the reason setup exists |
| **Creating a ticket** — title, body, labels, assignee | `/pm:task publish`, `/pm:task sync` | The call. What a network error after the write looks like, and how to confirm by exact title before retrying |
| **Creating a parent** and attaching a ticket under it | `/pm:task publish`, `/pm:task sync` | The calls, where the tracker has a hierarchy. Where it does not, say so and `task.hierarchy.parent_kind` stays `null` |
| **Seating on a board** — the project field, the status column, the dates | `/pm:task publish`, `/pm:task sync` | Which id each write takes; they are rarely the same id |
| **Milestones** — list open ones, create one, set it on the parent | `/pm:task publish`, `/pm:task sync` | Only where `task.hierarchy.milestone_projects` names a project |
| **Updating a ticket's body** | `/pm:task publish` | Read before overwrite. Keep the row that links back to the record |

`/fig:handoff` writes its one line into a markdown record through `append-under`. Where `task_tracker` names Notion or GitHub it makes those calls itself, and does not read these files.

### Always

**Things that bite** — one line per thing, each because it happened. A read straight after a
write that returns the old snapshot. A success return on an edit that matched nothing. Text
typed by hand that corrupts. This section is the adapter's value; an empty one is a draft.

## How `/pm:setup` drafts one

Given a type with no file, setup does not ask you to write it. It reads `claude mcp list` for
the connector, lists the tools that connector exposes, reads their descriptions, and probes
the read-only ones — schema, list, one record — against the real workspace. Each question above
is answered with the call that actually returned, pasted as it was run. Questions that need a
write are answered with the tool that would do it, marked *unverified* until a run in any
`/pm:task` mode uses the call and it succeeds, which takes the mark off. The draft is previewed,
then written to the last dir in `adapters.dirs` as `trackers/<type>.md`, and the report says
which answers are verified and which are not.

Start from [`_template.md`](_template.md) when writing one by hand.
