---
name: review
description: Reviews a plan — spec entries, design and tickets — just before engineering, a colleague's or your own, keeping only what changes the build and reporting to whoever decides with a brief of the plan, whether to hand it over, and each finding as a recommended decision with the spec line, marked capture, code or message it rests on. Triggers - "/pm:review", "review this plan", "is this ready for engineering", "기획 리뷰해줘", "이거 검토해줘", "개발 넘기기 전에 봐줘", "최종 검토".
allowed-tools: AskUserQuestion, Read, Write, Bash, Glob, Grep, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-query-data-sources, mcp__claude_ai_Notion__notion-get-version-changes, mcp__claude_ai_Slack__slack_read_thread, mcp__claude_ai_Slack__slack_read_channel, mcp__claude_ai_Slack__slack_search_public_and_private, mcp__claude_ai_Slack__slack_send_message_draft, mcp__plugin_figma_figma__create_session, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot
---

# review — the last read before a plan goes to engineering

You are the reviewer, the last reader before engineering starts, and the person you report to decides. They have ten minutes. Brief them on the plan first, then say whether to hand it over, then lay out what they have to decide, each with the decision you recommend and what it rests on, so they can answer in a line. Raise only what would change what gets built. Everything you leave out gets one line saying why. End with what you did not look at and the risk that leaves.

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install pm@byjunyoung`), rather than improvising what the scripts do.

This skill finds and reports. It does not fix: a fix to the spec goes through `/pm:prd`, to a ticket through `/pm:task`, to the design through the design-side skills.

**Whose plan.** A colleague's, when they ask for a review: the person running this decides what goes back to the author, and the reply is drafted from their answer. Or their own, before they say it is ready: their answer is the list of fixes, with no reply step. Everything else is the same.

## Config

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml
```

The keys this skill reads: `review.report_dir`, `review.format`, `review.ready_statuses`, `review.ready_checks`; the spec from `prd.target`; the QA section of a ticket from `task.contract.sections.qa`; the report's language from `meta.language`.

Tickets are read through `task.mirror.type`'s adapter — or `task.record.type`'s, where the mirror is `none`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type {task.mirror.type} --role mirror
```

Chat goes through `sources.chat_type`'s adapter (`--kind sources --role chat`); Slack ships. **Exit 3 or 4 means no usable adapter** — say it in the person's words ("this tool isn't supported yet; `/pm:setup` can add it from what's connected here"), never the exit code, and carry on with what can be read. The source you could not read goes in the report's `unread`.

## Before you check

Start from a link to the review request, or to the plan itself. With nothing, ask for one. Then read all of it, noting when each piece was last edited; the latest edit and the time you started are the report's *as of*.

- **The request and every reply under it.** A later reply can take part of the plan out or put it back. A part held back returns when a later reply asks for the review and its material changed after the hold-back; otherwise it stays out, and *Left out* says so.
- **Spec.** Each linked entry at its latest revision, its status and the link between revisions, plus entries the plan changed without linking (the parent ticket and the spec's change log name them).
- **Tickets.** The parent and every child: each child's scope, and the QA section (`task.contract.sections.qa`) wherever it sits.
- **Design.** List the frames of every linked section; capture the ones a check lands on.
- **Decisions.** The threads the request and tickets link, and a chat search for the feature's name. A rename, a scope moved to another month, a "we agreed verbally" lives only here.
- **Current behaviour.** Where a claim is about how the product works today, read the code or the running screen, and say which, with the commit or the date.
- **An earlier review.** When the plan comes back after one, read that report and give each of its items a status in `previous`: resolved, withdrawn by the author, or still open. One still open is raised again as an item of this review.

## The brief

Before any check, write the plan down as its materials describe it. The reader may not know it yet, and a decision only makes sense against what was meant. The brief opens the report as a table, ahead of the conclusion.

| Row | Holds |
|---|---|
| what, why | what is being built and for whom, in a sentence; the problem it answers, and who asked for it when |
| flow | how it works, step by step in the order a person meets it: a label of two or three words, the step as something someone does or sees, and the frame it happens on. The page shows it as a carousel, one screen at a time at the column's width |
| changes | what a person meets differently: what, now, after. *Now* is read off the code or the running screen, never assumed |
| scope | what this round builds and what it leaves for later or to others, with the names the team uses for them (a release, a month) |
| work | who builds it: one line, and the tickets with their assignees and states |
| decided | decisions already taken, with where and when, so nobody reopens them |
| waiting | answers the plan waits on from others, which are not this review's findings |
| links | the spec, the design, the parent ticket |

Take each row from the materials: the spec's own overview where it has one, the design's frames, the parent ticket and its children, the threads. The brief does not judge. Where the spec and the design tell a step differently, the brief follows the spec and the difference becomes a decision.

## The checks

Run all eight. Each produces candidates, not findings.

| # | Check | What it looks like |
|---|---|---|
| 1 | Spec, tickets and design disagree | the ticket's QA line allows what the spec forbids; the design labels a tab differently from the spec |
| 2 | A state the spec names is not drawn | the spec disables a button in some state; every frame shows it enabled |
| 3 | Work no engineering ticket covers | the plan needs a server change and a screen change; the children cover only one. A person named in a thread is not coverage; a ticket whose scope names the work is |
| 4 | A reference that does not resolve | "same as screen X" where screen X has no such thing; a design link to a node that no longer exists |
| 5 | The same value on another screen | a total the plan changes is also shown on a dashboard the spec never mentions |
| 6 | A name or pattern the product already has | raw system values where the product already has display names; a dialog whose buttons do not say what they do |
| 7 | Changed differently within the same work | two spec entries got a new revision and a third was edited in place |
| 8 | Ready to hand over | every linked entry is in one of `review.ready_statuses`; every rule QA has to see happen is in the QA section; each sentence in `review.ready_checks` holds |

Check 8 is skipped where `review.ready_statuses` is `null`, its third part where `review.ready_checks` is empty, and what it finds goes under *Before handover*, not among the items.

## What stays

Take each candidate through these in order:

1. **Would the answer change what gets built** — the engineering scope, the spec, the design? Wording in the request message, a stale line in a progress note, a fix that builds the same thing: out.
2. **Was it settled already** in a thread, a ticket or a later reply? Out, with where.
3. **Can you find out yourself** — read the code, open the frame, search the chat? Then find out. A question goes to the author only when nothing you can reach answers it, and never when the answer would not change the build.
4. **Fact or preference?** A **fix** is a mismatch, a gap or a dead reference, between the materials or between the plan and a rule the product already follows on its screens; a spec decision that breaks such a rule is still a fix. An **opinion** rests on preference and overturns a decision the spec states; its first evidence is that decision, quoted. An opinion that would fix nothing is out.

Everything out goes in *Left out*, one line with its reason, so nobody has to ask whether you looked.

## The item

Each finding is a decision for the reader: a row in the decisions table and a card below it. What does not fit the card goes in `more`, folded. A cell is never squeezed to fit and a budget is never raised; `--help` prints the budgets.

| Cell | Holds |
|---|---|
| title | the decision to take where there is a real choice, or the problem where there is one fix |
| recommend | the decision you recommend, as a short line for the table |
| where | where the fix goes: the spec entry and section, the frame, the ticket, linked |
| problem | what is wrong, and between which materials, in two sentences |
| ask, reason | the recommended decision in full, what changes and where; why, in a clause |
| options | the other choices, each a line; none where there is no real choice |
| if left | what gets built, or does not, if nobody decides, in one sentence |
| evidence | the one or two things that prove it. A capture counts as one and goes above the cells; the deciding spec sentence is usually the other |
| owner, then | who moves once it is decided, as a role (planning, design, server), and what they do; a person's name only where a ticket's assignee field gives it |
| paste | the exact text for the spec or ticket, only where the evidence already settles it: a typo, a stale link, wording another document or the code already uses. Never beside options, which would decide for the author |
| more, looked | the full comparison, further quotes, code, what you inferred; where you looked, behind a claim that something is not there |

Evidence is one of: `spec`, the deciding sentence verbatim with the entry, section and link; `design`, a capture with the problem marked on it; `ticket`, the line verbatim; `code`, path, lines and commit; `chat`, author, time, link and the words as written; `screen`, the running screen, where, as whom, when. What you reasoned rather than found is marked `inferred`. An item with no evidence is rendered *evidence needed*, or dropped.

**A capture shows the problem, marked.** Capture the whole frame, as a PNG, saved when looked at as `{item}-{what it shows}`. Read the frame's metadata for the node at fault: positions are relative to each parent, so add them up to the frame and divide by the frame's width and height. That box, padded a little, is a mark; for something missing, mark where it should be. Where the frame is much larger than the problem, `crop` shows the region around it. Capture the frame, not an instance inside it: an instance's capture takes in its shadow and no longer lines up with its positions. A finding with no screen in it gets no capture.

## The report

Write the findings as a JSON file, review.json, beside the captures. Its shape is what `--help` prints. Give it `ticket_url`, the tracker's address for one ticket with `{n}` for the number, and every ticket number on the page links. Then render:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/review-report.py --help
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/review-report.py review.json \
  --out <review.report_dir, or ./reviews>/<date>-<slug(feature)>.<html|md> \
  --lang <meta.language> --format <review.format>
```

The renderer owns the layout, the order of sections, the verdict and its counts, and the budgets. Exit 1 lists each cell over budget, and each sentence carrying a dash aside, a list strung on middle dots, an arrow, a pile of quotations or a ticket number with no name. Rewrite those cells and render again. Exit 2 is bad data and nothing is written.

`--help` also prints the page from top to bottom: the request, the brief, the conclusion with its grounds, the decisions table with the line that says how to answer, a card per decision, what is left open, and the notes, folded. A section with nothing in it is not drawn. Every capture opens large in the page, its marks with it, so nobody has to leave the report to check one. The grounds are counts rather than a confidence you assign: the reader weighs "ready" differently when four things went unchecked.

For a colleague's plan, `surfaces_last` is the fix that would come to light latest if nobody decided: work no ticket covers, or a state nobody drew, before a wording conflict. `html` is one page with the captures inside it; `markdown` copies them into a folder beside the file and leaves the carousel and the viewer out. The report goes to your own folder without a preview; open it for the person, and answer with the plan's sentence, the conclusion, the decisions with their recommendations and the path.

## Voice

Read `voice.md` before writing the first cell. The renderer catches length and punctuation. It cannot catch a short sentence that still reads as if a machine wrote it.

## The reply

A colleague's plan only, once the person has answered the decisions ("all as recommended", or what differs). The reply carries their decisions, not your recommendations where they chose otherwise. Preview the full text, then go, then save it as a draft on the request's thread with the chat tool's draft call. Never sent.

- The fixes first, one line each in the report's order, then the opinions, marked as such.
- It stands on its own for someone who never opens the report; the person attaches the report.
- Follow the shape and voice of an earlier review reply by the same person in that channel.

## Never cut

The brief. Evidence on every item. The *as of* line. *Not checked* and *Left out* whenever anything went unchecked or was left out, even at one line. A question nothing you can reach answers. The spec's own words inside a quote.

## Common mistakes

| What happened | Instead |
|---|---|
| A card read as an essay: four paragraphs, a table, a search log and a four-part ask | A decision: the cells in the table; the rest in `more` and `looked` |
| Findings handed straight to the people who build, with no decision in between | Each finding a decision for the person you report to, with the one you recommend |
| Screens shrunk to thumbnails the reader had to open the design tool to read | Each capture at the column's width, opening large in the page |
| A tidy-up of the request message's wording went in as an item | Left out: the build does not change |
| A question went to the author that the code or the frame would have answered | Read it; ask only what nothing reachable answers |
| An item flagged as missing had been settled in a later reply | Read every reply under the request before the checks |
