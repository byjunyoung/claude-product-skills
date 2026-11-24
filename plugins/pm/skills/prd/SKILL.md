---
name: prd
description: Writes a product requirements document against a format, or fills out an existing one, in markdown files by default or in a repo or Notion by config. Triggers - "/pm:prd", "write the PRD", "draft the requirements", "PRD 작성", "PRD 만들어줘", "기능 항목 추가", "PRD 보강", "사용자 그룹 추가".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, WebSearch, WebFetch, mcp__claude_ai_Slack__slack_read_thread, mcp__claude_ai_Slack__slack_read_channel, mcp__plugin_figma_figma__get_metadata, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-duplicate-page, mcp__claude_ai_Notion__notion-create-pages, mcp__claude_ai_Notion__notion-update-page, mcp__claude_ai_Notion__notion-query-data-sources
---

# prd — writing and extending a format-based requirements document

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install pm@byjunyoung`), rather than improvising what the scripts do.

When a PRD is being written or worked on, the material is gathered and analysed first, and the result becomes a **recommended answer**. The user adopts it with a single "go", or writes a different answer instead. Every question carries the option judged most fitting, marked (recommended).

**It is read by people who cannot open the code** — whoever designs the screens, settles the scope, runs the product once it ships. A requirement is worth what the sentence carrying it is worth to them: 2.5 and `voice.md` are the rule, the second check in 3 is the gate.

**It keeps growing, so every entry has a unit, a shape and a budget.** 2.1 decides what one entry is, Appendix B what it holds, section by section, and the fourth check in 3 holds it there. Detail that does not fit goes to the tickets and the design file, not into a longer entry.

**The premise**: writes happen only after preview → "go" — a markdown file as much as a Notion page. Reading, searching, and gathering come first, without confirmation.

## When to invoke

- Writing the requirements for a new product or feature for the first time
- Adding entries to an existing PRD, or bringing it in line with what shipped
- Design material and meeting notes exist but nothing is in document form yet

## When NOT to invoke

- Tidying or auditing a design file → `/fig:prep` · `/fig:lint`
- Drawing the screens this document describes → `/fig:draw`, which reads the published document as its source for copy rather than inventing any
- Comparing a shipped screen against the baseline → `/fig:qa`
- Turning a request into a task record → `/pm:task draft`; filing or syncing tickets → `/pm:task publish` · `/pm:task sync`

## Configuration

The rules and values are set by `pm-conventions.yaml`, not by this document.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml --authored task.record.type,task.record.ref
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/preflight.py --quiet
```

A FAIL stops the run only when its row concerns what this run touches — the connector `prd.target` needs, the record type read for Linked tasks, or a source this run reads; print its fix lines and nothing else. Any other FAIL row, and an UNKNOWN (exit 2, the last line says so), is reported in one line and the run continues. `task.record.type` is asked for because the Linked tasks section is built from it (step 4); a config that never named it would otherwise run on the floor's copy without anyone having chosen it.

The layers merge bundled defaults → `~/.claude/pm-conventions.yaml` → `./pm-conventions.yaml`. Later layers cover earlier ones, so **only the keys you need have to be written.** If it ran on bundled defaults alone, say so in the result.

**`prd.target` decides how it gets published.** The skeleton is the same either way; only step 4 differs.

    markdown   local files. The default — no other tool required
    git        written as markdown, then a branch and a PR
    notion     a Notion page. Requires the prd.notion section filled in

A `null` setting means "skip that collection, integration or check". Do not stop for want of a value — record what was skipped in the result.

## The shape of it

```
1. Prepare            mode (new / extend) + gather material + confirm the format
2. Draft & interview  decide the entries → absorb the material → recommended answers, adopted with "go"
3. Verify             terminology · voice · shape · length · evidence · completeness · coherence (zero writes)
4. Preview & publish  preview → "go" → write (in stages)
```

**Stop immediately on a failed step.** If step 3 catches something, go back to step 2. Nothing publishes without a "go".

---

## 1. Prepare

### 1.1 Which mode

Settle new versus extend first. Do not ask when the request makes it obvious.

- **New** — stand up the format skeleton and absorb the material
- **Extend** — read the target document first, lay out "what is already there and what is changing", then proceed

In extend mode, **do not improve adjacent entries on your own.** Touch only what was asked for; other problems that catch the eye get reported, not fixed.

### 1.2 Gather the material

**Ask this first.** The quality of a recommended answer is proportional to how much input there is. Offer only the places switched on in `sources`.

> "What should we start from? As much as you have — the more there is, the more accurate the recommendations."
> · design material, code repos · existing documents (policy, research, meeting notes, an earlier PRD) · design files · chat history · nothing

Read whatever comes back **immediately, without confirmation**. For several sources, split them and read in parallel.

### 1.3 Existing assets first

Look for what already exists before making anything new. Search for similar plans, research, and earlier PRDs first, and where personas or domains are already defined, use them as they are. One or two failed searches do not mean "nothing there" — change the keywords and look again.

**Domain splitting** goes by the count in `prd.domains.range`, cut so the domains do not overlap. Where `align_with_design` is true, match the design file's page structure one to one; where the two disagree, the design file wins, and the range is what to aim for when there is no design file to follow yet.

---

## 2. Draft and interview

Absorb what was gathered and produce a draft with a recommended answer in every slot. What could not be filled is not invented — it gets `prd.tbd_label`. Your own inference carries `prd.assumption_label` so it never mixes with what was found.

**Do not leave ambiguity — resolve it into a definition.** TBD is for what someone else has to decide, or what the material cannot settle. Anything decidable from context, confirmed material or precedent is written as a value — never deferred with 'appropriately', 'as the situation requires', 'if needed', 'and so on', never hedged with 'for now', 'enough', 'about', 'occasionally', 'once it settles'. A hedge is a value somebody has not written down yet: write the value, the condition or the person who owns it. Four things in particular do not work as blanks:

    the unit of judgement, aggregation, and dispatch
    the target fields of filtering, search, and sorting — and a list's default order and its tie-break
    the criteria for picking a 'representative' or a 'priority'
    the definition of state transitions and recovery

A status of 'under review' means a concrete proposal is up for review, not a blank. What genuinely cannot be decided stays TBD and carries who decides it and by when.

### 2.1 Deciding the entries

Settle which entries there are before writing any of them. Entries cut at different sizes cannot be read against each other, and one that grew to hold three jobs is read as none of them.

| Entry | What one is | Named |
|---|---|---|
| Feature | One thing a person sets out to do on the product — a list and its filters, registering and editing something, one settings screen. Usually one screen or one dialog | The way that person would say it: *the branch list*, *registering a product* |
| Policy | A rule that holds whichever screen it is met on — the product's own state names, what a value may be, when something may be deleted, what a law or a contract requires. It is the business's constraint; a feature is what a person does under it | By what it rules: *branch states*, *product input rules* |

| When | Then |
|---|---|
| Two feature entries state the same rule | The rule moves into one policy entry; both features name it (*see Product input rules*) and do not restate it |
| An entry holds two things somebody sets out to do, or rules two things — different people reach its parts at different times, or one part changes without the other | It splits, one entry per unit. Length is never the reason: an entry that is one unit stays one entry however long, and a split by count leaves two halves that only make sense together |
| Two entries always change together and are reached together | They merge |
| The product has states of its own that several entries name | That vocabulary is settled first, as a policy entry — 3.1's item 0 reads it back |

### 2.2 New — what to fill in

1. **Product overview** — in `structure.overview` order. Background separates fact from supposition
2. **User groups** — named by **role**, not by team name, with the same persona names across documents. Each group's body is the `structure.user_group_rows` table (Appendix A)
3. **Domains, then the entries 2.1 decided**, each in Appendix B's shape
4. **A feature entry, the first time it is drafted, gets a precedent check** — skipped where `prd.precedent.enabled` is off. Before its structure is proposed, look for how a comparable product covers the same ground: `prd.precedent.archive_dir` first if set, then each service in `prd.precedent.reference_sources` (a library of real product screens, reached through a connector), then the web. A listed service not connected in this session is skipped and named in the report; one named only there is not in this skill's `allowed-tools`, so its first call will prompt for permission — expected, not a hang. A screen is read as a shape to compare, never as a fact about that product's rules. **1.3 outranks it**: a shape this team already decided against, for a reason a document gives, is a decision, and precedent does not reopen it. What precedent turns up is folded into the recommendation for that entry, not presented as a separate finding, and logged in its references under a `Precedent —` line. A policy entry does not get this

### 2.3 Extend — units of work

- **Adding an entry** — 2.1 decides whether it is a feature, a policy, or a rule that belongs in an entry already there. Appendix B's shape; status starts at the first value in `properties.status`. A feature gets 2.2's precedent check
- **Extending or updating an entry** — lay out before and after so the user can see what changes. A decision that replaces an earlier one replaces its line; the old one does not stay beside it — the change log, or the earlier revision where the team keeps one, holds the history
- **Every entry change carries its change-log line in the same preview**, where the document has a change log — re-read the log's last row just before writing
- **An entry already over budget is not rebuilt to fit.** The budgets and step 3's length check apply to what this change adds or rewrites. An overrun already there is reported once — with the split 2.1 would make where the entry holds two units, as an overrun and nothing more where it holds one — for somebody to decide; 1.1 holds
- **Adding a user group** — with the `user_group_rows` skeleton
- **Adding a property option** — change the config first. Do not let each document grow its own

### 2.4 Interview principles

Ask about the gaps **together, in one pass**, each with a material-backed recommendation marked (recommended), so a short answer finishes it. (The exception is 3.1: where one answer changes the next question, they go one at a time.) New ambiguity mid-write is asked again or marked TBD, never settled on your own. Before the pass goes up, drop every question the material or an earlier decision already answers and say which were dropped; put each remaining one in the reader's words with one concrete case, not in the rule's own terms.

**The gap list is not the list of blank fields.** A blank is a question the format already knew to ask; the ones that cost a second round are the questions an *answer* creates. Adopt *it can be deleted* and two decisions appear that were on no form — what becomes of what was already there, and what somebody on another screen sees. So for each recommendation about to go up, ask what adopting it would settle next, and put that into this pass rather than leaving it for 3.1 to find.

### 2.5 The language it comes out in

**Read `voice.md` before drafting.** It holds the rules below with their examples, the table of what research leaves out, and the two guards. The reader is whoever designs the screens, settles the scope and runs the product: write at the level they already stand at — the plainest written sentence that still carries the whole requirement.

| Rule | Not | But |
|---|---|---|
| A rule says what a person sees and does | *The view switches depending on whether an active job exists* | *While something is being made, the screen stays on the progress view* |
| A number carries its meaning | *Locks after 3 failures* | *Three wrong tries in a row lock it; one correct entry clears the count* |
| A cell says what happens, and holds one piece of information | *Restore* · *Repeats every 30 minutes until fixed* | *The list goes back to how it was* · *repeat │ every 30 min │ until resolved* |
| A rule that branches is laid out | Paragraphs walking through the cases | A situation-against-outcome table, a flowchart, a worked timeline |
| A word the reader may not have is glossed where it first appears; the field's standard term is used and defined once | A paraphrase invented to avoid the term | The term, in the terms table with its original-language form |
| Written, not spoken — in cells, open items and evidence lines too | *ping the operator* · *whether the drink goes in the dispenser* | *notify the operator* · *dispenser assignment for the drink* |
| What the reader cannot act on stays out | Where a value is stored, a vendor list, today's value of a setting | The fact as the person meets it; the rule for setting the value |
| Wording changes, decisions do not | A number rounded or a rule softened while tidying | Values, decisions, section order and tables exactly as they were |

---

## 3. Verify (zero writes)

Self-check, read-only. Anything caught sends it back to step 2.

1. **Terminology** — `prd.forbidden_terms` in the body is replaced with product-side wording. Write as far as "what" (the requirement) and leave "how" to engineering or a TBD
2. **Voice** — the check above reads nouns; this one reads sentences, against every row of 2.5 with `voice.md` beside it, in the rules, the cells, the open items, the evidence lines and the references. Change nothing but the sentence; cut what the reader would not act on, never a decision. A value an operator sets on a screen keeps only the rule for setting it
3. **Shape** — Appendix B, section by section: every section present and in order, each holding only what its row says. Sources sit in an evidence line or the references, never folded into a rule sentence as "source:". One piece of information per table cell. A rule turning on more than two cases is laid out. Every standard term is in the terms table, in one sense
4. **Length and repetition** — the budgets in Appendix B's last column. Then **every fact appears once in the body of an entry**: a rule in a table is not said again in a bullet, another table or an evidence line, and a rule another entry also states moves to a policy entry by 2.1. Its one other place is the decision-log line that settled it. References keep only the decisions in force. An entry over budget is first cut — repetition, then `voice.md`'s *What stays out* — never by dropping a decision. Rules still past `prd.limits.rule_topics` after that are a prompt to run 2.1's unit test, not a reason to split: two units, propose the split; one unit, it stays whole and the overrun is reported in one line. In extend mode this reads only what the change adds or rewrites (2.3)
5. **Evidence** — no facts, quotations, or statistics without a source. Without one, TBD or "evidence needed"
6. **Completeness** — the `structure.sections` skeleton is all present; user groups, domains and entries are not empty; every blank is an explicit TBD
7. **Vague wording** — reject 'appropriately', 'as the situation requires', 'if needed', 'etc.', a hedge where the material has the value, a TBD with no reason or no owner, an empty **target** for filtering, search or sorting, a list with no default order, an undefined **unit** for judgement, dispatch or aggregation. One TBD the material could have settled is not a pass
8. **Language and notation** — as `meta.language` and `prd.emoji` have it; on `auto`, the conversation's language

### 3.1 Does it hold together

The checks above find what is missing, malformed or unreadable — not a document that is complete and wrong. **Read `coherence.md` and run its items in this order**:

| # | Reads | For |
|---|---|---|
| 0 | the roles and product states the entries name | each one defined — in the user groups, or the policy entry holding the states |
| 1 | entries against each other | one allowing what another forbids |
| 2 | each condition | the branch nobody wrote, and the case row holding two cases in one cell |
| 3 | each number | what resets it, its boundary, its unit |
| 4 | each switch | the off, delete or undo half |
| 5 | each setting | who else it reaches, one step away |
| 6 | entries describing today | against the code or a running build — reported, not reconciled |
| 7 | each state | a way out that does not wait on the thing that stopped |
| 8 | each removal | another entry that still needed what was removed |
| 9 | a change to a live product | what already exists shows and does on day one |

What the material settles is settled and rewritten (item 6 excepted). What needs a person becomes a question — together where independent, one at a time where an answer moves the next. What cannot be answered now is a TBD carrying who decides it and by when.

### 3.2 What engineering will ask

On the entries that propose something not built yet, ask the five questions in `coherence.md` — a source for every value shown, where a value is kept and who writes it, where the product's categories and the system's part ways, other systems and two things at once, what is already there. Read the answers off the code where the material has it.

| The answer | Where it goes |
|---|---|
| Changes what a person sees or does | Into the entry, in the reader's words |
| Unknown, and it decides whether the entry can be built as written | `TBD (engineering, needed by …)` in the cell it decides, or one row of the entry's open-items table — one line, no more. `/pm:task publish` carries it to the ticket, where the question is worked |
| Changes nothing anybody sees | Nowhere in the spec |

This does not stand in for engineering's own review; it moves the questions that review reliably asks to before the handover.

---

## 4. Preview and publish

**Always** show the full content and take a "go" before a write — to a markdown file, a branch, or a Notion page alike. The preview names the **target** and the **added, changed, and deleted items**, and closes with `shall I proceed? (go / changes)`. A "go" approves what was shown; nothing else gets slipped in at execution time. If the content changes, preview again → go.

**Do not write a lot at once.** Split it: skeleton → user groups → entries per domain, each preview → go → next.

### Publishing by target

**markdown** — written into `prd.markdown.dir`. Slugs come from `python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/markdown-tracker.py slug NAME`.

    split: product   {dir}/{slug(product)}.md
    split: domain    {dir}/{slug(product)}/index.md             Overview, User groups, Linked tasks, Design, Change log
                     {dir}/{slug(product)}/{slug(domain)}.md    that domain's entries

With `front_matter` true, the front matter carries `title`, `product`, `domain` (domain files only), `status` and `updated`. Tables are pipe tables, and entry properties go in the front matter or as table columns. Each entry gets its anchor from Appendix B, so that a task or a ticket can link to it.

Where `task.record.type` is markdown, the **Linked tasks** section is regenerated on every publish from `markdown-tracker.py list --dir {task.record.ref}`: the records whose `project` equals the product, one line each, `- [{title}]({path relative to the PRD file}) — {status}`. Its first line is `<!-- generated from {task.record.ref}; edits here are replaced -->`. Other record types leave the section as it was.

**git** — written the same as markdown, then a `branch_prefix + product name` branch, and with `open_pr` true, a PR as well. Commits and PRs are external writes too, so they take a preview → go.

**notion** — where `prd.notion.template` exists, start by duplicating it; the published document keeps none of the template's scaffolding — its instructions, example rows and empty embeds go in the same staged write, named in the preview. Where it is null, create the document under `prd.notion.parent`; where both are null, ask for a page and offer to store its id in the config — never create at the workspace's top level. Rows go into the inline DB (`inline_db`), linked to `task_db` if there is one. **Re-read the template and the DB immediately before writing** to confirm the current heading formats, properties, and options, and match them — never trust option values pinned in this document or in the config. Read back after writing to verify. The things to watch are in appendix C.

Once published, list the remaining TBDs and the manual follow-ups **once**, with the open items owned by engineering named apart — those are the ones to raise before the handover.

---

## Appendix A — the user-group body

Based on the `structure.user_group_rows` default. Where the config differs, follow the config.

| Row | Content |
|---|---|
| Account and access scope | The login unit and permissions. For an output-only product, say so |
| Environment | Device, place, context |
| Primary domains | The functional areas this group mostly uses |
| Representative scenarios | One or two core flows |
| Pain points | Only with evidence; otherwise TBD |
| Expectations and asks | Only with evidence; otherwise TBD |
| Evidence | Source links |
| TBD | Unsettled items (with reasons) |

Product-specific rows are absorbed into the row content rather than added to the skeleton. A skeleton that differs per document cannot be compared.

## Appendix B — the entry contract

**Properties** — type, status, and priority from `prd.properties`, plus target users and the design link. 'Who' goes in the target-users property and 'when' into the background; neither gets a row.

**The anchor** — on a markdown target, the line before each entry's heading is `<a id="entry-{n}"></a>`. `n` is one more than the highest `entry-` id across all of the product's files, and 1 when none exists yet. Extending an old file anchors the new entries only. An id is never renumbered or reused: a removed entry stays as a short "(removed)" tombstone that keeps its anchor. A link to an entry is `{path}#entry-{n}`; that is the form `spec_url` and `task.ticket.link_rows.spec` take.

**A feature entry** (`structure.feature_sections`) holds these sections, in this order, and nothing else:

| Section | Holds | Budget |
|---|---|---|
| Background | Why the entry exists and in what context. How a decision was reached is not background — its line in the decision log carries it | `prd.limits.background` sentences |
| Core requirement | What the feature does as a whole | One sentence |
| Detailed behaviour | Table: behaviour │ condition │ input │ result | One behaviour per row |
| States and cases | Table: case │ screen, behaviour. Rows in `structure.cases` order, every one present, `—` where it does not apply, `other` for anything off the list. A case that is two screens gets two rows under the same case name, the difference after a dash | One case per row |
| Rules and exceptions | An optional lead of one or two sentences; then one subheading per topic, each with an `item │ rule` table — or, for a rule that branches, a situation │ outcome table, a flowchart and a worked timeline — and under it at most one line `Evidence — {why the table's rules are so, in a sentence} ({date}, {source})` — the reason, not the table's values again. Anything unsettled that is not a cell of those tables goes last, in an `item │ owner │ needed by` table | No other bullets or paragraphs. Past `prd.limits.rule_topics` topics, step 3's fourth check asks whether it is still one entry |
| References | The sources behind the entry, one per line: what the source is and its date, with the link. Then a decision log, one line per decision: `{date} {occasion} ({who}) — {what it settled, as noun phrases}`; a decision that is replaced is replaced here too. A `Precedent —` line for 2.2 item 4's find, which says what the shape was checked against rather than backing a fact | One line per source or decision; decisions in force only |

**A policy entry** (`structure.policy_sections`): background and references as above, and its rules in the same shape as a feature's rules and exceptions. Where the document has a terms table — term │ meaning │ original-language term — it lives in the policy entry the others point to.

## Appendix C — things to watch when target is notion

- Editing a table cell can push a line break into the cell behind it. Keep the line count, edit row by row, and read back to verify
- Non-ASCII text typed by hand corrupts easily. Copying existing text and substituting into it is safer
- Relation properties are **replaced wholesale** with an array of page URLs. There is no adding just one
- Code blocks need their language stated. Left empty, they get read as another language
- Reading back right after an edit can return an old snapshot. Confirm by content, not by the call succeeding
- Pipe tables carry no column widths; the tag form in `_common/trackers/notion.md` does. Starting widths for this document's tables, adjusted to what the cells hold: the user-group body (`Row | Content`) 180 / 540; detailed behaviour (`behaviour | condition | input | result`) 200 / 180 / 140 / 200. Line breaks inside a cell are `<br />`
