---
name: handoff
description: Hands finished sections to engineering. Runs /fig:lint as the gate, lets the person pick which passing sections go, pins the named version handed over, hands over the section links, and writes one line into the task doc where a tracker is configured. It never sets a Dev Mode status. Nothing else is touched. Triggers - "/fig:handoff", "hand this off", "send this to engineering", "개발 넘겨줘", "핸드오프 해줘", "이 섹션 개발팀에 넘겨".
allowed-tools: AskUserQuestion, Bash, Read, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-update-page, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__add_issue_comment, mcp__claude-in-chrome__list_connected_browsers, mcp__claude-in-chrome__select_browser, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__tabs_close_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__find
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
- Marking what changed and writing it up → `/fig:diff`
- Filing the task as a ticket → `/pm:task-publish`
- After release, bringing canonical current → `/fig:sync`

## Inputs

- `page` (required): the page the sections are on
- `sections` (optional): names or numbers. Omitted, every section on the page that passes the gate is a candidate

## Where the rules come from

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --js <fileKey>
```

`handoff.version` — whether a handover pins a named version, and how that version is named, matched and written out. `task_tracker.type` and `task_tracker.ui_section_heading` — where the one line goes; `none` writes none.

## Procedure

### 1. The gate — `/fig:lint` on the page (zero writes)

Call `/fig:lint` (via the Skill tool) on the page. **No audit lives here**; the verdict is lint's alone, and it is the only thing that makes a section a candidate.

The gate reads **blocking only** (lint, "Severity"). A section is not held back by how it is filed — it is held back by what engineering would build wrong.

- A section with zero blocking is a candidate, warnings and all
- **Warnings never remove a candidate.** They ride along to step 3 and into the report, so the handover happens knowing what is still untidy
- A section carrying any blocking is out, with those reasons beside its name. It is not offered, and if the person names it anyway, say why it cannot go and leave it out — "hand it over now and fix it later" is what the gate is meant to prevent

### 2. Choose

Show the candidates as a table — name and warnings still open (`—` where none) — and ask which go: all, or some. One question. Sections held back by blocking appear below the table with those reasons, so the person sees why they are not offered.

### 3. Pin the version

Only where `handoff.version.enabled`. With it off, skip to step 4 and the doc line carries the links and a date alone.

**A handover names a moment in the file.** Without one, every later edit silently moves what "matches the design" means, and a ticket whose done conditions lean on that line is being checked against a target that shifted after it was written.

Figma's named versions are that moment — a snapshot of the whole file, so every section going over in one run shares the label and differs only in the node. Nothing is copied, and no frozen duplicate of the file exists to fall out of date.

**`use_figma` cannot save one** — its allowlist rejects the version API (`"saveVersionHistoryAsync" is not a supported API`). **The web app can**, so where browser automation is available this step does not have to be handed to a person:

- In the design tool's web app, signed in on the profile that owns the file: main menu → *File → Save to version history*, then fill the name and description and save
- Type the name through the clipboard rather than keystrokes where the label is not plain ASCII — synthesized typing mangles multi-byte text, and a mangled label is a pin nobody can match later
- It is a write to a shared file, so it goes through the same preview → go as any other. What it writes is one entry in the history; the file's contents are untouched, and removing the entry's name undoes it
- Where no browser is connected, or the account signed in there is the wrong one, hand it back: show the name and ask for it to be saved under exactly that name

Either way:

1. Ask which release this handover belongs to — a value the person has, never one inferred from the file
2. Settle the name `handoff.version.name` produces, and save it — through the browser, or by asking
3. Read it back, newest first, and take the first entry matching `handoff.version.match`:

```bash
curl -s -H "X-Figma-Token: $FIGMA_TOKEN" \
  "https://api.figma.com/v1/files/{fileKey}/versions?page_size=10"
```

That entry carries the label, its `created_at` — **the date in `handoff.version.ref` is the version's, not today's** — and its `id`, which is what a deeplink pins with.

- **No token, or an expired one** (`{"status": 401, "err": "Token has expired"}`) → say so, and ask for the version's link to be pasted instead; `version-id` is in its query string. Never carry on unpinned, and never substitute today's date for the version's
- **Nothing matches** → it was not saved, or was saved under another name. Show what the newest few are actually called and stop, rather than pinning the wrong moment

Every section link from here on carries the pin: `…/?node-id={id}&version-id={version id}`.

### 4. Preview → go

One preview with everything this run will do:

- the sections going over
- the section links: `https://figma.com/design/{fileKey}/?node-id={section id with : replaced by -}` — the same links `/fig:prep` hands over, because engineering opens sections, not frames
- where a version was pinned: the label, its date, and the `&version-id=` every link now carries
- where `task_tracker.type` is not `none`: the one line that goes into the task doc — the links, "handed over {date}, {n} sections", and the pinned version written as `handoff.version.ref` — under `task_tracker.ui_section_heading`, appended after what is already there, by the method `/fig:diff` uses for that tracker. **That line is what `/pm:task-publish` reads to fill a ticket's referenced-version row**, so the label and the date go in as they came back from the file, not as they were typed

Then the go.

### 5. Write

The task-doc line, where configured — nothing in the Figma file.

### 6. Read back

Re-read the task doc where the line went and confirm it landed under the heading, with the pinned links as written. A mismatch is reported, not retried.

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
[task doc]   {where the line went, or "no tracker configured"}
```

## Constraints

- The writes are the version entry (through the web app, behind the go) and the one doc line. Frames, sections, names, positions and Dev Mode status are never touched
- A section carrying a lint **blocking** is never handed over, whoever asks. A warning alone never withholds one
- **Never hand over unpinned where `handoff.version.enabled`.** An unpinned handover reads as pinned to whoever gets it, and that is worse than stopping
- Never save a version, rename one, or write a date that is not the version's own
- Never offer to set *Ready for dev* or *Completed*, and never list it as remaining work
