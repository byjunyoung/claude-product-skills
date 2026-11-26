---
name: review
description: Reviews a plan — spec entries, design and tickets — just before it goes to engineering, whether a colleague asked for the review or the plan is your own, keeping only what would change what gets built, writing each finding with the spec line, design capture, code or message it rests on, and saying whether the plan can be handed over. Triggers - "/pm:review", "review this plan", "is this ready for engineering", "기획 리뷰해줘", "이거 검토해줘", "개발 넘기기 전에 봐줘", "최종 검토".
allowed-tools: AskUserQuestion, Read, Write, Bash, Glob, Grep, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-query-data-sources, mcp__claude_ai_Notion__notion-get-version-changes, mcp__claude_ai_Slack__slack_read_thread, mcp__claude_ai_Slack__slack_read_channel, mcp__claude_ai_Slack__slack_search_public_and_private, mcp__claude_ai_Slack__slack_send_message_draft, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot
---

# review — the last read before a plan goes to engineering

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install pm@byjunyoung`), rather than improvising what the scripts do.

A plan reaches engineering as three things written at different times — the spec entries, the design, the tickets — and the gaps between them cost a sentence now and a rebuild later. A review is worth what it finds that would change what gets built, and each finding is worth what it rests on: the line of the spec, the corner of the screen, the ticket, the message. The person reading the report should be able to check every item without opening anything else, and act on it without asking you what you meant.

## Two cases, one run

- **A colleague's plan.** Someone asked for a review — usually a chat message linking the spec, the design and the parent ticket. The report goes to the person running this first; a reply on the request is drafted only after they have read it and ask for one.
- **Your own plan.** You are about to say it is ready for engineering. The report is your list of fixes, and its first line says whether the plan can go. There is no reply step.

Whose plan it is decides which: the request's author, or the person running this. The checks, the filter and the report are the same.

This skill finds and reports. It does not fix — a fix to the spec goes through `/pm:prd`, to a ticket through `/pm:task`, to the design through the design-side skills.

## Config

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml
```

The keys this skill reads: `review.report_dir`, `review.format`, `review.ready_statuses`, `review.ready_checks`; the spec from `prd.target`; the QA section of a ticket from `task.contract.sections.qa`; the report's language from `meta.language`.

Tickets are read through `task.mirror.type`'s adapter — or `task.record.type`'s, where the mirror is `none`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type {task.mirror.type} --role mirror
```

Chat goes through `sources.chat_type`'s adapter (`--kind sources --role chat`); Slack ships. **Exit 3 or 4 means no usable adapter** — say it in the person's words ("this tool isn't supported yet; `/pm:setup` can add it from what's connected here"), never the exit code, and carry on with what can be read: a review with one source missing names it at the top of the report rather than stopping.

## Input

A link to the review request, or links to the plan itself — spec entries, a design section, the parent ticket. With nothing, ask for one of them.

## Flow

1. **Scope.** Read the request and every reply under it — a later reply can take part of the plan out or put it back ("that part isn't ready yet" … "please review it now"). A part held back comes back in when a later reply asks for the review and that part's material was edited after the hold-back; where its material has not moved since, it stays out and the report says so. List every material the plan consists of, and each one's last-edited time. The latest of those, and the time you start, make the report's *as of* line.
2. **Read all of it.**
   - Spec: each linked entry at its latest revision, with its status and the link between revisions. Entries the plan changed but did not link are found from the parent ticket and the spec's change log.
   - Tickets: the parent and every child — each child's scope, and the QA section (`task.contract.sections.qa`) of whichever ticket holds it.
   - Design: list the frames of every linked section first; capture the ones a check below lands on.
   - Decisions: the threads the request and tickets link, and a search of the chat tool for the feature's name. A rename, a scope moved to another month, a "we agreed verbally" lives here and nowhere else.
   - Current behaviour: where a claim is about how the product works today — a mode that exists, a screen that shows a total, a value's display name — read the code or the running screen when either is reachable. Say which, with the commit or the date.
3. **Find the candidates** — *The checks*.
4. **Filter** — *What stays*.
5. **Attach the evidence** — *Evidence*.
6. **Write the report and open it** — *The report*. The response carries the verdict line, the item list and the file's path.
7. **Reply** — a colleague's plan only, and only when the person asks after reading the report. *The reply*.

## The checks

Run all eight on every plan. Each produces candidates, not findings.

| # | Check | What it looks like |
|---|---|---|
| 1 | Spec, tickets and design disagree | the ticket's QA line allows what the spec forbids; the design labels a tab differently from the spec |
| 2 | A state the spec names is not drawn | the spec disables a button in some state; every frame shows it enabled |
| 3 | Work no engineering ticket covers | the plan needs a server change and a screen change; the children cover only one of them. A person named in a thread to do it is not coverage — a ticket whose scope names the work is |
| 4 | A reference that does not resolve | "same as screen X" where screen X has no such thing; a design link to a node that no longer exists |
| 5 | The same value on another screen | a total the plan changes is also shown on a dashboard the spec never mentions |
| 6 | A name or pattern the product already has | raw system values shown where the product already has display names for them; a dialog whose buttons do not say what they do |
| 7 | Changed differently within the same work | two spec entries got a new revision and a third was edited in place |
| 8 | Ready to hand over | every linked spec entry is in one of `review.ready_statuses`; every rule QA has to see happen is in the QA section; each sentence in `review.ready_checks` holds |

Check 8 is skipped where `review.ready_statuses` is `null`, and its third part where `review.ready_checks` is empty. For a colleague's plan still under review, entries in a draft status are expected — they go under *Before handover*, not among the findings.

## What stays

Every candidate goes through these, in order:

1. **Would the answer change what gets built** — the engineering scope, the spec, the design? Wording in the request message, an outdated line in a progress note, a fix that produces the same build: left out.
2. **Was it already settled** in a thread, a ticket or a later reply? Left out, with where it was settled.
3. **Can you find out yourself** — read the code, open the frame, search the chat? Then find out. A question goes to the author only when nothing you can reach answers it, and a question whose answer would not change the build is not asked at all.
4. **Fact or preference.** A **fix** is a mismatch, a gap or a dead reference — between the materials, or between the plan and a rule the product already follows on its screens (an existing display name, an established pattern). Where the spec decided something on purpose and that decision breaks such a rule, it is still a fix: the conflict is the fact. An **opinion** is a proposal that rests on preference and overturns a decision the spec states; it is labelled as one, with the decision quoted, and it carries evidence of what it would fix like any other item — with none, it is left out.

Everything left out goes in the report's *Left out* list with its reason, one line each. Writing down what was not raised is half of a review: it is what keeps the author from asking about it, and the reader from wondering whether you looked.

## Evidence

Every item carries at least one. Without one it is marked *evidence needed*, or dropped.

| Kind | How |
|---|---|
| Spec | Quoted verbatim, never paraphrased inside the quote, with the entry's name and link |
| Design | A capture of the smallest node that shows it — the button row, the caption, the cell — with the node link. Where no node fits, crop the frame's image to the region. Saved the moment it is looked at, named `{item}-{what it shows}` |
| Ticket | Quoted line, with the ticket written as *title (#number)* — never the number alone, since nobody keeps numbers in their head |
| Code | Path, line range and commit |
| Chat | Author, time and link; the words quoted as written |

What you infer is labelled *inferred* and kept apart from what you found. A claim that something does not exist names where you looked.

## The report

`review.format` decides the file: `html` (the default) is one self-contained page with every capture embedded as a data URI, so it opens with a double-click and can be passed on as one file; `markdown` is a file with the captures in a folder beside it, linked relatively. It goes to `<review.report_dir>/<date>-<slug(feature)>`, or to `./reviews` where that key is `null`. It is your own folder, so it is written without a preview; open it for the person afterwards.

A capture becomes a data URI with:

```bash
python3 -c "import base64,sys;print('data:image/png;base64,'+base64.b64encode(open(sys.argv[1],'rb').read()).decode())" capture.png
```

In this order:

1. **Head** — whose plan, who asked and when (or "own plan"), who reviewed, and the *as of* line.
2. **Verdict** — one line. Own plan: "ready to hand over", or "N fixes before handover". A colleague's: "N fixes, M opinions", then the title of the fix that would surface latest if nobody acted on it — work no ticket covers, or a state nobody drew, before a wording conflict.
3. **Items** — a table: number, fix or opinion, area, title. Each title links to its card.
4. **Cards** — one per item: what is wrong in two or three sentences, the evidence, and the ask — what to change, where, and the recommendation where there is a choice.
5. **Before handover** — what check 8 found: entries not yet in a ready status, QA lines missing, team checks not met.
6. **Left out** — each with its reason.
7. **Sources read** — every material, with links.

Prose is plain and declarative, table cells are short noun phrases, quotes stay in their original wording, and the language is `meta.language`. The page has to read on a phone: tables scroll inside their own box rather than widening the page.

## The reply

A colleague's plan only, after the person has read the report and asks for it. Preview the full text → go → saved as a draft on the request's thread with the chat tool's draft call. Never sent.

- The fixes first, one line each in the order of the report, then the opinions, marked as such.
- The reply stands on its own for someone who never opens the report; the report goes with it as an attachment the person adds.
- Find an earlier review reply by the same person in that channel and follow its shape and voice.

## Before showing the report

- Every item has evidence of a kind in the table above, or is marked *evidence needed*.
- Every ticket is written as *title (#number)*.
- No item fails the first two questions of *What stays*; no question to the author that the third one answers.
- The verdict's counts match the items.
- The *as of* line is there, and *Left out* is there even when it is short.

## Common mistakes

| What happened | Instead |
|---|---|
| The report listed conclusions and the reader had to ask what each one rested on | Evidence on every card, before anyone asks |
| A tidy-up of the request message's wording went in as a request | Left out — the build does not change |
| A question went to the author that the code or the frame would have answered | Read it; ask only what nothing reachable answers |
| "There is no X" after one search | Name where you looked, or keep looking |
| Ticket numbers alone in the report | *title (#number)* |
| An item flagged as missing had been settled in a later reply | Read every reply under the request before the checks |
| A preference written as a fix | An opinion, with the decision it overturns quoted |
