---
name: handoff
description: Hands finished sections to engineering. Runs /fig:lint as the gate, lets the person pick which passing sections go, pins the named version handed over, hands over the section links, and writes one line into the task file (or page, or issue) where a tracker is set, or prints it where none is. It never sets a Dev Mode status. Nothing else is touched. Triggers - "/fig:handoff", "hand this off", "send this to engineering", "개발 넘겨줘", "핸드오프 해줘", "이 섹션 개발팀에 넘겨".
allowed-tools: AskUserQuestion, Bash, Read, Skill, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-update-page, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__issue_write, mcp__plugin_github_github__add_issue_comment, mcp__claude-in-chrome__list_connected_browsers, mcp__claude-in-chrome__select_browser, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__tabs_close_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__find
---

# fig:handoff — hand finished sections to engineering

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install fig@byjunyoung`), rather than improvising what the scripts do.

The moment a feature's screens, states and arrows are drawn, somebody has to say "this is ready"
where engineering looks. The signal is the section links, pinned to a named version of the file,
written into the task doc engineering builds from — and only for sections that pass the audit.

**The audit decides, the person chooses, the skill hands over.** `/fig:lint` says which sections
are fit to hand over; the person says which of those go now; this skill pins the version, hands
over the links, and leaves one line in the task doc. It draws nothing, moves nothing, renames
nothing.

**Prerequisites**: load `figma:figma-use` before calling `use_figma`. Every write goes through
preview → go.

**Dev Mode status (*Ready for dev*, *Completed*) is not part of this skill, and is never offered.** `use_figma` rejects the getter and the setter alike — `"devStatus" is not a supported API` — on an Edit seat as much as a View one (checked on a live file, 2026-08-31), and Figma's REST API reads the status but has no endpoint that sets it. Kept as an option, it came back as "I can mark these ready for dev" run after run, a step the skill could not take. It was removed outright in 3.26.0. Do not propose it, and do not list it as something left to do; where the person wants the status, it is theirs to set in Dev Mode.

## When to invoke

- A feature's screens, states and arrows are drawn and it is time to hand them to engineering
- Something handed over was revised and needs handing over again
- "Which of these sections is actually ready?" — the gate answers that even when nothing is marked

## When NOT to invoke

- Laying the skeleton and stubbing missing states → `/fig:prep`
- Checking rules only → `/fig:lint`
- Looking at what changed between two versions of a design → Dev Mode's *Compare changes* in Figma
- Filing the task as a ticket → `/pm:task publish`
- After release, bringing canonical current → `/fig:sync`

## Inputs

- `page` (required): the page the sections are on
- `sections` (optional): names or numbers. Omitted, every section on the page that passes the gate is a candidate
- `task` (optional): where the line goes — a Notion page url, a GitHub issue, or a task file's path

## Where the rules come from

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --js <fileKey>
```

`handoff.version` — whether a handover pins a named version, and how that version is named, matched and written out. `task_tracker.ui_section_heading` — the heading the one line goes under in a Notion or GitHub doc; in pm's markdown records pm's `task.design_heading` decides it, and `borrow-pm.py task` returns the heading to use.

Where the line goes is not read off `task_tracker.type` here. Ask:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/borrow-pm.py task <fileKey>
```

It prints `{"action", "dir", "heading", "script", "adapter", "note"}`, and `action` decides:

| action | What this skill does |
|---|---|
| `write` | Write the line into a markdown task file (below). `{script}` is pm's `markdown-tracker.py`, `{dir}` the task folder, `{heading}` the heading. Show `note` beside the written line where there is one |
| `print` | Put the line in the response, with `note` beside it where there is one. Nothing is written |
| `notion` | Insert the line into the task page, directly after the `{heading}` heading (below) |
| `github` | Insert the line under that section of the issue body; where the body has no such section, add it as a comment (below) |

- **Exit 3** — fig's own config has a `task_tracker.ref` without its `task_tracker.type`. Stop, and name the setting the message names
- **Exit 1** — say what it printed and stop. Do not fall back to `print`
- **`action` always decides; the `task` input never overrides it.** Under `print`, nothing is written even when a file path was given — show the line and the note. Under `notion` or `github`, a `task` url names the page or issue to update, as before. When the input's kind disagrees with the action (a GitHub issue while the action is `write`, say), the action decides and the skill says so
- **The task file** (`write` only) is the `task` input; `Read` the path before the preview, and a missing file stops there and says so. Without one, run `python3 {script} list --dir {dir}` and pick: one record whose `title` clearly matches the feature → use it, and say which; otherwise ask
- **`list` prints nothing** — the folder is missing or empty, so no task exists yet. Handle it as `print`, with the note "no task file yet — `/pm:task draft` makes one, and the next handoff writes into it"

## Procedure

### 1. The gate — `/fig:lint` on the page (zero writes)

Call `/fig:lint` (via the Skill tool) on the page. **No audit lives here**; the verdict is lint's alone, and it is the only thing that makes a section a candidate.

The gate reads **blocking only** (lint, "Severity"). A section is not held back by how it is filed — it is held back by what engineering would build wrong.

- A section with zero blocking is a candidate, warnings and all
- **Warnings never remove a candidate.** They ride along to step 3 and into the report, so the handover happens knowing what is still untidy
- A section carrying any blocking is out, with those reasons beside its name. It is not offered, and if the person names it anyway, say why it cannot go and leave it out — "hand it over now and fix it later" is what the gate is meant to prevent

### 2. Choose

Show the candidates as a table — name and warnings still open (`—` where none) — and ask which go: all, or some. One question. Sections held back by blocking appear below the table with those reasons, so the person sees why they are not offered.

### 3. Pin the version — preview → go → save → read back

Only where `handoff.version.enabled`. With it off, skip to step 4 and the doc line carries the links and a date alone.

This is the first write, so it has its own preview. Ask which release this handover belongs to, settle the name `handoff.version.name` produces, and show that name as the one entry about to be added to the file's version history. After the go, follow `${CLAUDE_PLUGIN_ROOT}/_common/version-pin.md` to save it and read it back. Nothing is saved before the go.

Every section link from here on carries `&version-id={version id}`, and the date in `handoff.version.ref` is the version's own.

### 4. Preview the doc line → go → write

The second write has its own preview, so a version that went in is never followed by a doc line nobody has seen. One preview with everything this step will do:

- the sections going over
- the section links: `https://figma.com/design/{fileKey}/?node-id={section id with : replaced by -}` — the same links `/fig:prep` hands over, because engineering opens sections, not frames
- where a version was pinned: the label, its date, and the `&version-id=` every link now carries
- where `action` is not `print`: the one line that goes into the task doc — the links, "handed over {date}, {n} sections", and the pinned version written as `handoff.version.ref` — under `{heading}`, appended after what is already there. For `write` the preview names the file and shows the line under the heading; for `notion` it names the page and the heading the line goes after, and for `github` the issue and whether it is the body or a comment. **That line is what `/pm:task publish` reads to fill a ticket's referenced-version row**, so the label and the date go in as they came back from the file, not as they were typed

Then the go. After it, the task-doc line, where `action` writes one — nothing in the Figma file. For `write`, with the heading and the line passed single-quoted and every `'` inside them written as `'\''` — a `"`, `$` or backtick in a version label then reaches the file as it is, rather than ending the argument or being expanded by the shell:

```bash
python3 {script} append-under --path {file} --heading '{heading}' --line '{line}'
```

It adds the heading when it is missing, and a second run gives one heading. Exit 4 means the file named in the preview is missing — stop and say so. Under `print` the line goes in the response instead.

For `notion` and `github` the heading is `task_tracker.ui_section_heading`, or the default `borrow-pm.py task` returned, and the `task` input names the page or issue:

| action | Target | Method |
|---|---|---|
| `notion` | the `ui_section_heading` section of the task page — directly after the heading, and after whatever block opens the section (such as a callout) | `notion-update-page` with `update_content`, taking the heading as `old_str`, plus whatever opening block sits right under it where there is one, and **inserting the line after them**. `old_str` never relies on a particular block being there. Never replace the whole body |
| `github` | the task issue | If the body has that section, insert the line beneath it with `issue_write` (send the whole edited body back, changing nothing else). If it does not, add the line as a comment with `add_issue_comment` |

- **Search for the target section first.** Where the heading is missing or named differently, confirm where the line should go. Where there is already content under it, do not overwrite — append after it
- **Never replace the whole body** of a page or an issue, and never touch a section other than that one
- If no task was found, say so and print the line instead

### 5. Read back

Re-read the task doc where the line went and confirm it landed under the heading, with the pinned links as written. For a file, `Read` it: the line sits under the heading, once. A mismatch is reported, not retried.

## Report

```
[handed over]
· 01. Account - Login    https://figma.com/design/…&version-id=…
· 02. Account - Signup   https://figma.com/design/…&version-id=…

[not offered]
· 03. Account - Recovery   blocking — 2 frames outside any section · Recovery-Error missing

[handed over with warnings open]
· 02. Account - Signup   warning — section number 02 disagrees with its place on canvas

[version]    {label} · {date} · version-id {id}   (or "not pinned — handoff.version is off")
[task doc]   {the file or the page (with `note` after it where there is one), "printed — {note}", or "no tracker configured"}
```

## Constraints

- The writes are the version entry (through the web app) and the one doc line, each behind its own preview and go, in that order. Frames, sections, names, positions and Dev Mode status are never touched
- A section carrying a lint **blocking** is never handed over, whoever asks. A warning alone never withholds one
- **Never hand over unpinned where `handoff.version.enabled`.** An unpinned handover reads as pinned to whoever gets it, and that is worse than stopping
- Never save a version, rename one, or write a date that is not the version's own
- Never offer to set *Ready for dev* or *Completed*, and never list it as remaining work
