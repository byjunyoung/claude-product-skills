---
name: prd
description: Writes a product requirements document against a format, or fills out an existing one. Gathers and analyzes code repos, docs, designs, and chat history first, then proposes recommended answers so the interview can be settled with a single "go". Before writing anything it verifies read-only for vague wording, empty definitions, and engineering terms that do not belong in a product doc, then reads the entries against each other for roles nobody defined, entries that contradict, cases nobody wrote, and thresholds nobody can count. It writes for the people who read a spec rather than for the people who build it, so a rule says what somebody sees rather than what the system decided. Where the doc lives — markdown files, a git repo, or Notion — is decided by config. Triggers - "/pm:prd", "write the PRD", "draft the requirements", "PRD 작성", "PRD 만들어줘", "기능 항목 추가", "PRD 보강", "사용자 그룹 추가".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-duplicate-page, mcp__claude_ai_Notion__notion-create-pages, mcp__claude_ai_Notion__notion-update-page, mcp__claude_ai_Notion__notion-query-data-sources
---

# prd — writing and extending a format-based requirements document

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install pm@byjunyoung`), rather than improvising what the scripts do.

When a PRD is being written or worked on, the material is gathered and analysed first, and the result becomes a **recommended answer**. The user adopts it with a single "go", or writes a different answer instead. Every question carries the option judged most fitting, marked (recommended).

A PRD keeps growing. Keep the body thin and push the detail out into the entry list, the tickets, and the design file.

**And it is read by people who cannot open the code.** Whoever designs the screens, settles the scope, runs the product once it ships. A requirement is worth what the sentence carrying it is worth to them — 2.4 is the rule, and the second check in 3 is the gate.

**The premise**: external writes happen only after preview → "go". Reading, searching, and gathering come first, without confirmation.

## When to invoke

- Writing the requirements for a new product or feature for the first time
- Adding entries to an existing PRD, or bringing it in line with what shipped
- Design material and meeting notes exist but nothing is in document form yet

## When NOT to invoke

- Tidying or auditing a design file → `/fig:prep` · `/fig:lint`
- Comparing a shipped screen against the baseline → `/fig:qa`
- Filing or syncing tickets → whatever ticket tool you use

## Configuration

The rules and values are set by `pm-conventions.yaml`, not by this document.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py --name pm-conventions.yaml
```

The layers merge bundled defaults → `~/.claude/pm-conventions.yaml` → `./pm-conventions.yaml`. Later layers cover earlier ones, so **only the keys you need have to be written.** If it ran on bundled defaults alone, say so in the result.

**`prd.target` decides how it gets published.** The skeleton is the same either way; only step 4 differs.

    markdown   local files. The default — no other tool required
    git        written as markdown, then a branch and a PR
    notion     a Notion page. Requires the prd.notion section filled in

A `null` setting means "skip that collection or integration". Do not stop for want of a value — record what was skipped in the result.

## The shape of it

```
1. Prepare            mode (new / extend) + gather material + confirm the format
2. Draft & interview  absorb the material → propose recommended answers, adopted with "go"
3. Verify             terminology · format · vague wording · completeness (zero writes)
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

**Domain splitting** goes by the count in `prd.domains.range`, cut so the domains do not overlap. Where `align_with_design` is true, match the design file's page structure one to one.

---

## 2. Draft and interview

Absorb what was gathered and produce a draft with a recommended answer in every slot. What could not be filled is not invented — it gets `prd.tbd_label`. Your own inference carries `prd.assumption_label` so it never mixes with what was found.

**Do not leave ambiguity — resolve it into a definition.** TBD is for *what someone else has to decide, or what the material cannot settle*. **Anything decidable** from context, confirmed material, or precedent **must be specified concretely** — never deferred with 'appropriately', 'as the situation requires', 'if needed', 'and so on'.

These four in particular do not work as blanks, so fill them with values.

    the unit of judgement, aggregation, and dispatch
    the target fields of filtering, search, and sorting
    the criteria for picking a 'representative' or a 'priority'
    the definition of state transitions and recovery

A status of 'under review' means *a concrete proposal has been put up for review*, not *this is left blank*. Only what genuinely cannot be decided stays TBD, and it carries (who, what, when).

### 2.1 New — what to fill in

1. **Product overview** — in `structure.overview` order. Background separates fact from supposition
2. **User groups** — name groups by **role** (not by team name). Reuse the same persona names across documents so they stay consistent. Each group's body goes in the `structure.user_group_rows` table
3. **Domains + feature and policy entries** — settle the domains, then each entry in the appendix format below

### 2.2 Extend — units of work

- **Adding an entry** — appendix B's format. Status starts at the first value in `properties.status`
- **Extending or updating an entry** — lay out before and after so the user can see what changes
- **Adding a user group** — with the `user_group_rows` skeleton
- **Adding a property option** — where a value is needed that is not on the list, change the config first. Do not let each document grow its own

### 2.3 Interview principles

Ask about the gaps **together, in one pass**. Do not scatter the questions. (The exception is 3.1: where one answer changes the next question, they go one at a time.) Attach a material-backed recommendation to each, marked (recommended), so a short answer finishes it. If new ambiguity turns up mid-write, do not settle it yourself — ask again, or mark it TBD.

### 2.4 The language it comes out in

**Who reads a spec is what decides how it is written.** The people who design the screens, settle what is in scope, run the product once it ships and answer for it when it breaks — some of them read code, and none of them should have to. Write at the level the reader is already standing at: the plainest sentence that still carries the whole requirement, and no word they have to look up before they can act on it. Plain is not simplified — the reader knows the product better than anyone, just not its internals, so nothing gets rounded off to make it read easily.

This is not the terminology list. That list reads nouns, and a sentence containing none of them can still describe a machine rather than a product.

**A rule says what a person sees and does** — not what the system decided on their behalf.

| Written from the inside | Written from the reader's side |
|---|---|
| The view switches depending on whether an active job exists | While something is being made, the screen stays on the progress view |
| The evaluation is valid for 30 minutes | If nothing has been confirmed for 30 minutes, it counts as finished and the screen goes back to normal |
| Applied regardless of the account's state | Everyone sees it, signed in or not |

**A number is written with its meaning beside it.** A threshold, a period or a count on its own is a value, not a requirement — say what it does to the person it happens to. "Locks after 3 failures" becomes *three wrong tries in a row locks it, and one correct entry clears the count*.

**A cell in the behaviour or cases table says what happens** — not a noun standing in for it. Not *Transition*, *Restore*, *Refresh*, but *the banner clears*, *the list goes back to how it was*.

**A word the reader may not have is explained where it first appears**, in three or four words, inside the sentence rather than in a glossary nobody scrolls to. Where the team's own term is the accurate one, keep the term and gloss it; a folksy substitute invented to avoid it reads worse than the term did.

**The guard: changing how it reads must not change what it says.** Values, decisions, section order and table structure stay exactly as they were, and only the sentences move. A pass over the wording that quietly rounds a number or softens a rule has broken the document it was tidying.

Systems vocabulary is a symptom to watch for, not a list to ban — *active*, *trigger*, *threshold*, *evaluate*, *propagate*, *the presence or absence of*, *upon*, *the relevant*, rules chained together with arrows. Meeting one is a reason to read that sentence again from the reader's side; rewritten that way, the word usually has nowhere left to sit. The examples above are English because this file is, and the rule is about the shape of the sentence rather than the language it is in — `meta.language` decides that, and every one of these reads the same way translated.

---

## 3. Verify (zero writes)

Self-check, read-only. Anything caught sends it back to step 2.

1. **Terminology** — look for `prd.forbidden_terms` in the body. Where they appear, replace with product-side wording. Write as far as "what" (the requirement) and leave "how" (the implementation) to engineering or to a TBD
2. **Voice** — the check above reads nouns; this one reads sentences, which is where the same problem survives every string check there is. Read the rules, the behaviour rows and the case rows back as somebody who cannot open the code: does each one say what a person sees, or what the system decided? Rewrite whatever fails by 2.4 — and change nothing but the sentence
3. **Format** — re-read only the places that are easy to break
   - Functional requirements go in a **table** (behaviour │ condition │ input │ result). Not bullet sentences
   - States and cases go in a **table**, with the rows fixed to `structure.cases`. Not applicable is `—`; anything off the list is `other`
   - Sources and evidence collect in the **references** section. Never dissolved into a rule or exception sentence as "source:"
4. **Evidence** — no facts, quotations, or statistics without a source. Without one, mark it TBD or "evidence needed"
5. **Completeness** — the `structure.sections` skeleton is all present, and the user groups, domains, and feature entries are not empty. Every blank is explicitly a TBD
6. **Vague-wording scan** — reject on 'appropriately', 'as the situation requires', 'if needed', 'etc.', a TBD with no reason; on an empty **target** for filtering, search, or sorting; on an undefined **unit** for judgement, dispatch, or aggregation. **One slot left TBD that the material could have settled is not a pass**
7. **Language and notation** — as `meta.language` and `prd.emoji` have it. On `auto`, follow the conversation's language

### 3.1 Does it hold together

The checks above find what is missing, malformed or unreadable. They do not find a document that is complete and wrong — and a spec with no blank left in it can still contradict itself, skip a case, or name a number nobody can count. Read the entries against each other, in this order.

**0. Every role it names is defined.** Collect the roles, permissions and account words the entries actually use, and look each one up in the user-group table. A word with no row there is reported as exactly that — *this role is not defined anywhere* — and never as a contradiction.

This one comes first because the rest cannot be judged without it. Two entries that look like they disagree may be naming the same role twice under different words, or two genuinely different roles; only the group table settles which. Judged without it, the report is confident and wrong, which costs more than saying nothing.

**1. Entries that contradict each other.** One entry allows what another forbids, or two say different things about the same object. Quote both, and say which fact would settle it.

**2. The case nobody wrote.** A condition with two branches and one outcome. A states-and-cases row left at `—` where the case plainly applies. Ask about the branch, not about the table.

**3. A number with no rule around it.** A threshold, a count or a period that is stated but not countable — what resets it, what the boundary is, what unit it is in. "Locks after 3 failures" is not a requirement until it says when the counter goes back to zero.

**What to do with what it finds.** Whatever the material settles, settle it and rewrite the entry. What needs a person becomes a question — asked together where the questions are independent, and **one at a time where one answer changes the next**, since resolving a contradiction usually moves other entries with it. What genuinely cannot be answered now becomes a TBD **carrying who decides it and by when**; without those two it does not pass, the same rule every other TBD in this document lives under.

---

## 4. Preview and publish

**Always** show the full content and take a "go" before an external write. The preview names the **target** and the **added, changed, and deleted items**, and closes with `shall I proceed? (go / changes)`.

A "go" approves what was shown. Nothing that was not in the preview gets slipped in at execution time because it seemed better. If the content changes, preview again → go.

**Do not write a lot at once.** Split it: skeleton → user groups → feature entries per domain, each preview → go → next.

### Publishing by target

**markdown** — written into `prd.markdown.dir`. With `split` at `product`, one file per product; at `domain`, one file per domain. With `front_matter` true, title, status, and updated date go in the front matter. Tables are pipe tables, and entry properties go in the front matter or as table columns.

**git** — written the same as markdown, then a `branch_prefix + product name` branch, and with `open_pr` true, a PR as well. Commits and PRs are external writes too, so they take a preview → go.

**notion** — where `prd.notion.template` exists, start by duplicating it. Rows go into the inline DB (`inline_db`), linked to `task_db` if there is one. **Re-read the template and the DB immediately before writing** to confirm the current heading formats, properties, and options, and match them — never trust option values pinned in this document or in the config. Read back after writing to verify. The things to watch are in appendix C.

Once published, list the remaining TBDs and the manual follow-ups **once**. Do not repeat it every turn.

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

## Appendix B — the feature and policy entry format

**Properties** — type, status, and priority from `prd.properties`, plus target users and the design link.

**A feature entry's body** (`structure.feature_sections`):

```
Background        why + when and in what context
Core requirement  one line on what this feature does as a whole
Detailed behaviour  | behaviour | condition | input | result |
States and cases    | case | screen, behaviour |   ← rows fixed to structure.cases
Rules and exceptions  rules and exceptions (sources are not dissolved in here)
References        source and evidence links
```

'Who' and 'when' do not get their own rows — who goes in the target-users property, when is absorbed into the background.

**A policy entry's body** (`structure.policy_sections`): background / rules / references.

## Appendix C — things to watch when target is notion

- Editing a table cell can push a line break into the cell behind it. Keep the line count, edit row by row, and read back to verify
- Non-ASCII text typed by hand corrupts easily. Copying existing text and substituting into it is safer
- Relation properties are **replaced wholesale** with an array of page URLs. There is no adding just one
- Code blocks need their language stated. Left empty, they get read as another language
- Reading back right after an edit can return an old snapshot. Confirm by content, not by the call succeeding
