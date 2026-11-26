---
name: review
description: Reviews a plan — spec entries, design and tickets — just before it goes to engineering, whether a colleague asked for the review or the plan is your own, keeping only what would change what gets built, writing each finding as four short cells on one fixed page with the spec line, design capture, code or message it rests on, and saying whether the plan can be handed over. Triggers - "/pm:review", "review this plan", "is this ready for engineering", "기획 리뷰해줘", "이거 검토해줘", "개발 넘기기 전에 봐줘", "최종 검토".
allowed-tools: AskUserQuestion, Read, Write, Bash, Glob, Grep, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-query-data-sources, mcp__claude_ai_Notion__notion-get-version-changes, mcp__claude_ai_Slack__slack_read_thread, mcp__claude_ai_Slack__slack_read_channel, mcp__claude_ai_Slack__slack_search_public_and_private, mcp__claude_ai_Slack__slack_send_message_draft, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot
---

# review — the last read before a plan goes to engineering

You are the last reader before engineering starts, and the person you report to has ten minutes. Raise only what would change what gets built. Write each finding so it can be checked and acted on in one read, without opening anything else. Everything you leave out gets one line saying why. End the report with what you did not look at and the risk that leaves.

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install pm@byjunyoung`), rather than improvising what the scripts do.

This skill finds and reports. It does not fix: a fix to the spec goes through `/pm:prd`, to a ticket through `/pm:task`, to the design through the design-side skills.

## Whose plan

- **A colleague's.** Someone asked for a review, usually a chat message linking the spec, the design and the parent ticket. The report goes to the person running this first; a reply on the request is drafted only after they have read it and ask for one.
- **Your own.** You are about to say it is ready for engineering. The report is your list of fixes and its verdict says whether the plan can go. There is no reply step.

The request's author decides which. The checks, the ladder and the report are the same.

## Config

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml
```

The keys this skill reads: `review.report_dir`, `review.format`, `review.ready_statuses`, `review.ready_checks`; the spec from `prd.target`; the QA section of a ticket from `task.contract.sections.qa`; the report's language from `meta.language`.

Tickets are read through `task.mirror.type`'s adapter — or `task.record.type`'s, where the mirror is `none`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind trackers --type {task.mirror.type} --role mirror
```

Chat goes through `sources.chat_type`'s adapter (`--kind sources --role chat`); Slack ships. **Exit 3 or 4 means no usable adapter** — say it in the person's words ("this tool isn't supported yet; `/pm:setup` can add it from what's connected here"), never the exit code, and carry on with what can be read. A source the run could not read goes in the report's `unread`, at the top.

## Before you check

Start from a link to the review request, or to the plan itself: spec entries, a design section, the parent ticket. With nothing, ask for one of them. Then read all of it.

- **The request and every reply under it.** A later reply can take part of the plan out or put it back ("that part isn't ready yet" … "please review it now"). A part held back comes back in when a later reply asks for the review and its material was edited after the hold-back; otherwise it stays out, and *Left out* says so.
- **Spec.** Each linked entry at its latest revision, with its status and the link between revisions. Entries the plan changed but did not link come from the parent ticket and the spec's change log.
- **Tickets.** The parent and every child: each child's scope, and the QA section (`task.contract.sections.qa`) of whichever ticket holds it.
- **Design.** List the frames of every linked section first; capture the ones a check lands on.
- **Decisions.** The threads the request and tickets link, and a chat search for the feature's name. A rename, a scope moved to another month, a "we agreed verbally" lives here and nowhere else.
- **Current behaviour.** Where a claim is about how the product works today, read the code or the running screen when either is reachable, and say which, with the commit or the date.

Note each material's last-edited time. The latest of those and the time you started are the report's *as of*.

## The checks

Run all eight on every plan. Each produces candidates, not findings.

| # | Check | What it looks like |
|---|---|---|
| 1 | Spec, tickets and design disagree | the ticket's QA line allows what the spec forbids; the design labels a tab differently from the spec |
| 2 | A state the spec names is not drawn | the spec disables a button in some state; every frame shows it enabled |
| 3 | Work no engineering ticket covers | the plan needs a server change and a screen change; the children cover only one. A person named in a thread is not coverage; a ticket whose scope names the work is |
| 4 | A reference that does not resolve | "same as screen X" where screen X has no such thing; a design link to a node that no longer exists |
| 5 | The same value on another screen | a total the plan changes is also shown on a dashboard the spec never mentions |
| 6 | A name or pattern the product already has | raw system values shown where the product already has display names for them; a dialog whose buttons do not say what they do |
| 7 | Changed differently within the same work | two spec entries got a new revision and a third was edited in place |
| 8 | Ready to hand over | every linked spec entry is in one of `review.ready_statuses`; every rule QA has to see happen is in the QA section; each sentence in `review.ready_checks` holds |

Check 8 is skipped where `review.ready_statuses` is `null`, and its third part where `review.ready_checks` is empty. What it finds goes under *Before handover*, not among the items. For a colleague's plan still under review, entries in a draft status are expected there.

## What stays

Take each candidate through these in order:

1. **Would the answer change what gets built** — the engineering scope, the spec, the design? Wording in the request message, a stale line in a progress note, a fix that builds the same thing: out.
2. **Was it settled already** in a thread, a ticket or a later reply? Out, with where.
3. **Can you find out yourself** — read the code, open the frame, search the chat? Then find out. A question goes to the author only when nothing you can reach answers it, and never when the answer would not change the build.
4. **Fact or preference?** A **fix** is a mismatch, a gap or a dead reference, between the materials or between the plan and a rule the product already follows on its screens. A spec decision that breaks such a rule is still a fix: the conflict is the fact. An **opinion** rests on preference and overturns a decision the spec states; its first piece of evidence is that decision, quoted. An opinion with nothing it would fix is out.

Everything out goes in *Left out*, one line with its reason. That line is what keeps the author from asking whether you looked.

## The item

Each finding is four cells. What does not fit goes in `more`, folded under the card. A cell is never squeezed to fit and a budget is never raised.

| Cell | Holds | Budget |
|---|---|---|
| title | the problem as a statement, not a topic | one line |
| problem | what is wrong, and between which materials | two sentences |
| if left | what gets built, or does not, if nobody acts | one sentence |
| evidence | the one or two things that prove it | two pieces |
| ask | what to change and where, the recommendation first. Options only where the choice is real | one sentence, three options |
| more | the full comparison, further quotes, code, what you inferred | folded |
| looked | where you looked, behind a claim that something is not there | folded |

The renderer holds the character budget of each cell, and the report is not finished while one is over.

## Evidence

Every item carries at least one piece. Without one it is rendered *evidence needed*, or dropped.

| Kind | What goes in it |
|---|---|
| `spec` | The sentence that decides it, verbatim, with the entry, the section and the link |
| `design` | A capture of the smallest node that shows it (the button row, the caption, the cell) with the node link; where no node fits, the frame's image cropped to the region. Saved the moment it is looked at, named `{item}-{what it shows}` |
| `ticket` | The line, verbatim, with the ticket's title as written, its number and link |
| `code` | Path, line range and commit; the lines themselves as the quote |
| `chat` | Author, time and link; the words as written |
| `screen` | The running screen: where, as which role, when |

What you infer is marked `inferred`, apart from what you found.

## The report

Write the findings as a JSON file, review.json, beside the captures. The shape is at the top of the renderer: head fields, then each item's cells, evidence, `more` and `looked`, then `before_handover`, `not_checked`, `left_out` and `sources`. Then render:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/review-report.py review.json \
  --out <review.report_dir, or ./reviews>/<date>-<slug(feature)>.<html|md> \
  --lang <meta.language> --format <review.format>
```

The renderer owns the layout, the order of sections, the verdict and its counts, and the budgets. Exit 1 lists each cell over budget, and each sentence carrying a dash aside, a list strung on middle dots, an arrow or a pile of quotations. Rewrite those cells and render again. Exit 2 is bad data and nothing is written.

```
head              whose plan, who asked and when, who reviewed, as of, the latest edit
verdict           own plan: ready, or N fixes before handover
                  colleague's: N fixes, M opinions, and the item that surfaces last
items             number, fix or opinion, area, title
cards             one per item, the four cells, with more and looked folded
before handover   what check 8 found
not checked       what you did not look at, and the risk
left out          folded, one line each
sources read      folded
```

For a colleague's plan, `surfaces_last` is the fix that would come to light latest if nobody acted on it: work no ticket covers, or a state nobody drew, before a wording conflict.

`html` (the default) is one page with the captures inside it, so it opens with a double-click and travels as one file; `markdown` copies the captures into a folder beside the file. The report goes to your own folder, so it is written without a preview. Open it for the person afterwards. The response carries the verdict, the item titles and the file's path.

## Voice

Read `voice.md` before writing the first cell. The renderer catches length and punctuation. It cannot catch a sentence that is short and still reads as if a machine wrote it.

## The reply

A colleague's plan only, after the person has read the report and asks for it. Preview the full text, then go, then save it as a draft on the request's thread with the chat tool's draft call. Never sent.

- The fixes first, one line each in the order of the report, then the opinions, marked as such.
- The reply stands on its own for someone who never opens the report; the report goes with it as an attachment the person adds.
- Find an earlier review reply by the same person in that channel and follow its shape and voice.

## Never cut

Evidence on every item. The *as of* line. *Not checked* and *Left out*, even when each is one line. A question that nothing you can reach answers. The spec's own words inside a quote.

## Common mistakes

| What happened | Instead |
|---|---|
| A card read as an essay: four paragraphs, a table, a search log and a four-part ask | Four cells; the table, the log and the rest in `more` and `looked` |
| The report listed conclusions and the reader had to ask what each one rested on | Evidence on every card, before anyone asks |
| A ticket's full title, tags and all, repeated in every sentence | The full title once, in the evidence; a short name and the number in the cells |
| A tidy-up of the request message's wording went in as an item | Left out: the build does not change |
| A question went to the author that the code or the frame would have answered | Read it; ask only what nothing reachable answers |
| "There is no X" after one search | `looked` names where, or keep looking |
| An item flagged as missing had been settled in a later reply | Read every reply under the request before the checks |
| A preference written as a fix | An opinion, with the decision it overturns as its first evidence |
