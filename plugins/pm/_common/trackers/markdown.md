# Markdown as the record side

connector: none
roles: record

For a `task.record.type` of `markdown`. `{dir}` is `task.record.ref` — a directory, `./tasks`
unless the config says otherwise. A relative `{dir}` resolves against the working directory the
skill runs in, and every path below keeps the form `{dir}` was given in. One file per task, and
the properties live in the file's front matter under the names the config uses. No other tool
is involved, which is what makes this the tracker a team can start on today and the one a skill
can read exhaustively.

Every operation is one call to a script, so line endings, quoting and the file name are decided
in one place:

```
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py <op> ...
```

Exit codes: `0` done, `1` usage, `2` `{dir}` exists and is not a directory, `4` the file is
missing (for `set-link`, or has no front matter).

## The shape of a record

```markdown
---
title: Notification settings — push
project: Store App           # a value from task.properties.projects
group: Notifications         # what task.hierarchy.parent_kind groups by
status: Not started          # task.properties.status_initial on a new record
priority: medium             # a value from task.properties.priority
assignee: jane               # whatever string your team uses. task.assignee_map's left side is this string
start: 2026-08-01
end: 2026-08-14
ticket:                      # the key task.link_property names. empty until /pm:task-publish files it
---

## Context
| | |
|---|---|
| Request source | … |
| Initial request | … |
…                            # one row per task.context_rows, in that order

## Change summary
```

The header row `| | |` is there so the table renders; the label is the left column. The front
matter **is** the schema. `/pm:setup` reads the keys the files already carry; a directory with
no files yet has no schema, and the interview supplies the names.

**The path is the id, and the file name is the slug.** Match a record to its ticket by
`{task.link_property}`, and a record to itself by path — never by title, which gets rewritten.
The slug is the title lower-cased, with each run of whitespace or of `/\:*?"<>|#%` turned into
`-`, cut at 60 characters; letters of any script are kept, and an empty result is `untitled`. A
second record with the same title gets `-2`, `-3`, … and nothing is ever overwritten.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py slug "Notification settings"
```

## Reading the list

A directory can be listed in full, so the coverage line is `exhaustive` — there is no
relevance ranking here to miss a row.

```bash
# every record, as one JSON line each — path, then the front matter; sorted by path
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py list --dir {dir}
```

A file without front matter comes back as `{"path": …, "error": "no front matter"}`. A `{dir}`
that does not exist yet prints nothing, exits 0 and says so on stderr: that is "no records",
not a failure.

**What moved on a day** (`/pm:log`):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py moved --dir {dir} --date {date}
# {"paths": [...], "method": "git+uncommitted" | "git" | "mtime" | "none"}
```

Where `{dir}` sits in a git work tree, the paths are the files committed on that date; for
today, files edited and not yet committed are added too (`git+uncommitted`). Outside git the
answer is the modification times (`mtime`), which survive neither a clone nor a checkout — say
in the log that the day was read that way. A missing `{dir}` is `[]` with method `none`.

`log.me.tracker_user_id` is the assignee string, since there is no user id. Where it is null,
rows are not split between mine and the team's. `/pm:log` puts every row under *My tasks* and says in its summary that they were not split, naming `log.me.tracker_user_id`.

## Writing back

```bash
# the link property, after a ticket is filed — replaces the one line, never adds a second key
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py set-link \
  --path {path} --key {task.link_property} --value "{ticket url}"
```

**A change summary is `append-under --heading "Change summary" --line "- {date} {text}"`.**
The line lands after what is already in that section, and the heading is added when it is
missing — never a second one. The section exists to keep the history, so it is never replaced.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py append-under \
  --path {path} --heading "Change summary" --line "- {date} {text}"
```

**A new record:**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py new --dir {dir} \
  --title "{title}" --set project="{project}" --set status="{task.properties.status_initial}" \
  --link-key {task.link_property} \
  --row "Request source={source}" --row "Initial request={text}"
# stdout: the new file's path
```

Each `--set` becomes a front matter line, in the order given, then the link key is written
empty. Each `--row` becomes a row of the context table, one per `task.context_rows` entry in that
order. `task.notion.body_template` does not apply here.

## Things that bite

- **Front matter must be the first thing in the file** — `---` on the first line, `---` on
  its own line to close. A file that opens with a heading is not a record; report it rather
  than guessing which heading was meant as the title.
- **Keys are the config's words.** The skills look the link up by the name `task.link_property`
  holds. A file that spells it differently is a file without a link, and it will be filed twice.
- **Two files with the same title are two records.** The path is the identity.
- **Dates are `YYYY-MM-DD`.** A relative date in front matter is a string nobody can sort.
- **Use the config's own status words** in `status:` — `task.status_map`'s left-hand side is
  matched on the string as written.
- **Line endings and encoding are kept.** A file written with CRLF stays CRLF, and a leading
  BOM stays. A write that re-encodes the file shows up in git as a whole-file change, and the
  history the change summary keeps is gone. That is why nothing here edits a record with `sed`.
- **A `{dir}` that is a file** stops with exit 2 and `is not a directory`. Report it; do not
  delete or rename the file to make room.
