# pm

A bundle for product specs and the tasks that come out of them. Write the spec, draft the task, file it, keep both sides reconciled — and keep a record of what you actually did.

You type these the way you type anything else to Claude — `/pm:prd`, and it asks you what it cannot work out on its own. Nothing here asks you to write code.

```bash
claude plugin marketplace add byjunyoung/claude-product-skills
claude plugin install pm@byjunyoung
```

| Command | What it does |
|---|---|
| `/pm:setup` | Reads how your own tools are set up and writes your first settings file |
| `/pm:prd` | Writes a new requirements document, or extends one — in language its readers can act on |
| `/pm:task-draft` | Turns a request — a chat thread, a page, a conversation — into a task's context table |
| `/pm:task-publish` | Files one task as a ticket wherever engineering tracks its work |
| `/pm:task-sync` | Reconciles the planning list against that tracker |
| `/pm:log` | Writes a day's work log as a file from the same tracker |
| `/pm:log-review` | Turns a period of those logs into accomplishment statements |

## Where it writes

Where it is stored is decided by `prd.target` in `pm-conventions.yaml`. The skeleton is the same either way; only the publishing differs.

```
markdown   local files. The default — no other tool required
git        written as markdown, then a branch and a PR
notion     a Notion page. Requires the prd.notion section filled in
```

## What a ticket carries

The detail stays in the record and the ticket links to it, so there is one place to edit. Two sections are the exception — the done conditions and the QA checklist. They start life in the ticket, because the record answers why the work is happening while the ticket answers what finishes it, and the boxes are ticked where engineering works.

`/pm:task-publish` drafts both from the spec entry and the design before it asks anything, as a coverage pass: every row of the behaviour table, every state and case, every rule and exception either produces a condition or is named in the preview as skipped. `task.contract.level` decides which ticket holds them — the task, or the parent it hangs under — and `none` files a summary and links alone. Where the design side hands over a pinned version, `contract.design_match_line` writes the one condition that is settled by looking rather than by measuring.

**And a ticket is written for the people who will act on it.** Most of who opens one does not read the system it is built on — whoever draws the screens, whoever decides what is in this release, whoever answers for it once it ships. So the title names the outcome rather than the internals' own word for it, and a clause number or a spec path sits under the notes heading instead of inside the condition it explains. Where the record's title is the one written in that vocabulary, the preview offers a plainer one beside it rather than renaming anything quietly. Plain is not licence to write a sentence, though: a title is a noun phrase naming the work, in the grammar the list's other rows already use — a symptom stated as a sentence is what a defect is called. `/pm:task-sync` reports the same drift across a list and stops there: rewording sentences other people wrote, on one approval, is the edit neither skill makes.

A ticket filed before its requirement exists says so, as a quote rather than a checkbox, and names what is missing.

**The rest of the ticket is your tracker's shape, not this plugin's.** `task.template` names the ticket skeleton everyone else files on and `task.policy.doc` the rules the tracker is run by; both are read at run time and both outrank the config. The headings, their order and the labels the rules require come from there, so a ticket filed by these skills is not distinguishable from one filed by hand. Where a section name in the config is no longer in the template, the run names both and stops rather than adding a second section next to the first. A ticket already filed is never rewritten behind your back, but it is not stranded either: `/pm:task-publish` offers to bring one back to the template under its own preview, moving whole blocks rather than re-drafting them and asking where each orphaned piece of content goes. `/pm:task-sync` surveys the rest and only reports — the same edit across a whole list on one approval is what neither skill does.

## Tools it has never seen

How to work with one tool is written in one file, and the tool's name in your settings picks it. Notion, GitHub, markdown, Slack and Google Calendar come built in. Name anything else — Linear, Jira, Teams — and `/pm:setup` writes the support for it from the tools connected on your machine, into `pm-adapters/` next to your settings, marking what it could not verify. Until that file exists, the skills stop and say the tool is not supported yet, rather than guessing. What such a file has to cover is in [`trackers/README.md`](_common/trackers/README.md) and [`sources/README.md`](_common/sources/README.md).

## Starting from nothing

"Nothing yet" is an answer `/pm:setup` takes. It lays out one markdown repository — `docs/prd/`, `tasks/`, `logs/`, `highlights/` — that needs no other tool, with git as the audit trail. A tracker attaches later as the mirror, on whichever machine can see it, with the record untouched.

## The log side

Two of these skills are not about the spec at all. They keep a daily record of your own work, from the same tracker the task skills already read.

**They are split in two on purpose.** `/pm:log` runs unattended and records only facts and evidence — what moved, what was decided, what someone said about your work, the links that prove it happened. It never rates the importance of anything. `/pm:log-review` runs when you ask it, reads a period of those files, and interviews you for the three things a file cannot know: your role, what the result can be measured by, and what you learned.

The split is the point. An unattended agent writing daily about the significance of its own work fills a log with sentences nobody can check six months later. Judgement is asked for, never assumed.

```
every workday   /pm:log          one file — facts, quotes, evidence
now and then    /pm:log-review   a period of those files → accomplishment statements
```

**The first run is already useful.** A day's file is a written end-of-day summary — what moved, the meetings and what came out of them, the threads still open, what to pick up tomorrow. That it also accumulates into review material is the second benefit, not the first one you feel.

<details>
<summary><b>Running it on a schedule — the wrapper, and why launchd rather than cron</b></summary>

`/pm:log` is built to run with nobody watching. A wrapper and a calendar entry is the whole setup. Open only the tools it needs — `--dangerously-skip-permissions` is the wrong instrument for something that reaches your documents and your workspace.

```bash
#!/bin/bash
set -uo pipefail
cd "$HOME/path/to/your/log-repo" || exit 1

claude -p "/pm:log" --permission-mode acceptEdits --output-format text \
  --allowedTools "Read" "Write" "Edit" "Glob" "Grep" "Bash(date:*)" \
    "mcp__claude_ai_Notion__notion-fetch" \
    "mcp__claude_ai_Notion__notion-query-data-sources" \
    "mcp__claude_ai_Notion__notion-search" \
    "mcp__claude_ai_Notion__notion-get-users" \
    "mcp__claude_ai_Slack__slack_read_channel" \
    "mcp__claude_ai_Slack__slack_read_thread" \
    "mcp__claude_ai_Slack__slack_search_public_and_private" \
    "mcp__claude_ai_Google_Calendar__list_events"

[ -n "$(git status --porcelain logs)" ] && git add logs \
  && git commit -qm "log: $(date '+%Y-%m-%d')" && git push -q
```

Trim that tool list to the connectors you actually named in the config. **A tool the skill needs but the list omits is not an error you will see** — the run continues and the section comes out empty, so read the summary the first few times.

On macOS use a launchd agent with `StartCalendarInterval`: unlike cron it runs a missed job when the machine next wakes, so a laptop asleep at the scheduled hour catches up instead of losing the day. Elsewhere, cron plus the backfill window covers the same ground — every run re-checks the last `log.backfill.business_days` days and fills what it missed.

</details>

### Where meeting notes go

`log.sources.notes_channel` is a channel only you write in — your own direct message to yourself works. Everything there is yours by definition, so nothing has to be tagged or prefixed while a meeting is underway. Anything an app posted there on your behalf is excluded by `log.sources.notes_exclude_apps`.

The text is carried into the day's file rather than linked. Chat retention expires; a log that points at a message nobody can open years later has not recorded anything.

<details>
<summary><b>Coming from a Notion log — the importer, and what it learned on a real export</b></summary>

`_common/scripts/import-notion-export.mjs` converts a Notion "Markdown & CSV" export of a daily-log database into one file per day. Three things it learned the hard way, on a real 354-page export:

- Unzip with `ditto -x -k`, not `unzip` — the latter mangles non-ASCII filenames. The archive also contains a second archive.
- The date comes from the property Notion writes **into the body**, not from the file name. Exported titles can be rendered relative to the export moment (`@yesterday`, `@Monday`).
- Where the title carries an absolute date and the property disagrees, the title wins — and every disagreement is reported. On that export two pages had the wrong property, and trusting it would have buried two real days under empty templates.

Nothing is dropped silently: undated pages, duplicates and unclaimed folders all land in `logs/_unresolved/` with a reason.

</details>

## Configuration

```
the plugin's bundled defaults        the floor
      ↓ covered by
~/.claude/pm-conventions.yaml        your own shared config
      ↓ covered by
./pm-conventions.yaml                per project (strongest)
```

Three layers merge, so **only the lines you actually want to change have to be written.** Everything that can be set is listed with a comment in `_common/conventions.example.yaml`, and `/pm:setup` drafts your copy by reading how your tools are already set up — including the board fields and option ids no interface shows you. It opens by checking this machine — the two programs it runs on (`python3` with PyYAML, and `node`) and which of your connected tools actually answer — so anything missing is named up front. You never have to open the file yourself: say what to change and Claude edits it.

`/pm:setup` takes a `side` where the doc tool and the tracker are reachable from different machines, and leaves blank — with the question beside it — anything you cannot answer. A skill that cannot run without a setting stops and names the setting, rather than running on nothing.

## What this skill holds to

**It leaves no ambiguity.** The unit of judgement and aggregation, the target of filtering and sorting, the criteria for picking a 'representative', the definition of a state transition — a feature does not work with those four left blank, so they get filled with values. One slot left TBD that the material could have settled does not pass verification.

**It does not turn a product spec into an engineering doc.** Anything on the `forbidden_terms` list appearing in the body is rejected. Write as far as "what" (the requirement) and leave "how" (the implementation) to engineering or to a TBD.

**It writes for the person holding the document, not for the one building the thing.** The term list reads names, and a sentence carrying none of those names can still describe a machine: *the view switches depending on whether an active job exists* passes every string check and tells a designer nothing. So the sentences are read separately, against one question — does this say what a person sees, or what the system decided? A number is written with its meaning beside it, a table cell says what happens rather than naming it, and a term the reader may not have is explained where it first appears. What none of that may do is change the document: values, decisions and structure stay put, and only the wording moves.

**A document with no blank left in it can still be wrong.** The finished entries are read against each other — two that contradict, a condition with two branches and one outcome, a case row holding two conditions in one cell, a threshold nobody can count, a rule written only in the direction where something is switched on. Roles and the product's own state names are read first, since two entries that look like they disagree are as often one thing under two names, which is settled by the entry holding that vocabulary rather than by guessing. Last, an entry saying *this is how it works today* is read against what actually ships, and what turns up is quoted from both sides rather than reconciled toward the code.

**It stops before writing.** Verification is read-only, publishing happens only after preview → "go", and even then split into skeleton → user groups → feature entries.

## The other half

[`fig`](../fig/README.md) works the design file this spec is drawn into. The two never call each other, but they share two objects. If you install both, set `qa.baseline.prd` in `figma-conventions.yaml` to the spec this config writes, and `task_tracker.ref` to the task record it opens — otherwise `/fig:qa` has no baseline to judge against and `/fig:diff` has nowhere to write the comparison. The [repository README](https://github.com/byjunyoung/claude-product-skills#where-the-two-meet) draws the whole loop.
