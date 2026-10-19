# publish — one task record into one tracker ticket

Files a single task record as a ticket in the engineering tracker, or updates the one already there.

**The ticket carries a summary and links, not a copy of the body.** Detail — the spec, the design, the description of what changed — stays in the record, and the ticket points at it. Two copies means one gets edited and they drift; there is also no reliable way to carry embedded images across, so a copied body arrives broken.

**Two sections are the exception, and they originate here.** The done conditions and the QA checklist are not a copy of anything. They are the contract the work is finished against, and the boxes are ticked where engineering works, so that is where they live. The record answers *why this is being done*; the tracker answers *what counts as done*. Writing them on both sides would be the drift this rule exists to prevent.

**`task.contract.level` decides which ticket carries them** — the task itself, or the parent the task hangs under. Put them wherever review happens. Where a tracker closes tasks on a merge and reviews the feature at the parent, the contract belongs at the parent: a condition and the step confirming it, split across two tickets, cannot be checked against each other, and the coverage rule in step 2 stops meaning anything. With `level: none` there is no contract and this skill files a summary and links only.

## What decides where things go

Config, the adapters, the rules every mode follows — matching, titles, mappings, preview → go — and the tracker's own rules — the rule document and the template — are in `SKILL.md`, read before this file. What follows is publish's own.

## Inputs

- `record` (required): the task record's url
- `--contract` (optional): writes only the contract's own sections — the two binding ones, plus the requirements section where `contract.sections.requirements` is set — to whichever level `task.contract.level` names. Without it the run files or updates the task's ticket. Omitted with `level: parent`, a run that files a task says at the end whether its parent already has a contract, and offers to write it as a separate run
- `--template` (optional): reads both adapters as *Adapters* in `SKILL.md` says, then runs *Bringing a ticket back to the template* below on the ticket the record links to, and nothing else. A record with no link yet has no ticket to bring back, and with `task.template` null there is no template to bring it to — either way, say so and stop

**Why the contract is its own run at `level: parent`.** One parent holds many tasks. Rewriting its contract every time a sibling is filed puts a large diff behind a preview nobody reads closely, and the moment the contract is actually written is a different moment — it is what lets the parent leave the planning column. Keeping it separate makes that moment visible.

## When NOT to invoke

- Filling the record's context table → `/pm:task draft`
- Reconciling many tasks across both sides → `/pm:task sync`
- Writing the requirements → `/pm:prd`

## Procedure

### 0. Take the record

Take the record's URL from the argument, or ask for it.

### 1. Read the record and its materials (zero writes)

Read both adapters first — *Adapters* in `SKILL.md`. Every call to either side from here on, the parent search and the duplicate check included, is the one they give.

Read the record's properties — title, project, group, priority, assignee, status, schedule, the link property, and any link to a published spec.

**Read the body too.** The change summary, the design links, and the spec links inside it are the defaults the interview starts from. Reading them first is what keeps the interview short.

Then read the two things step 2 is drafted from:

- **The spec entry the record links to** — its behaviour table, its states and cases, its rules and exceptions. This is where most done conditions already exist as sentences somebody wrote on purpose
- **The design the record links to**, where the tool can be read — **structure only**: which state variants are actually drawn, what the screens are called, and where the flow goes

**Read the design for what exists, not for how it looks.** Colour, spacing and size never become conditions — step 2 says why. Copy is taken from the spec first: a design still carrying placeholder text would otherwise freeze a wrong string into the contract, and reading a screen in full costs far more than reading its structure. Go deeper on one screen only where the spec left its copy blank.

Where the record's design section carries a handover line — the links, the date, and the version the handover was pinned to — **that line is what the referenced-version row is built from, verbatim.** Do not restate it in your own words and do not substitute today's date: the point of the pin is that it names a moment somebody else can go back to.

Then branch:

- **The project has no entry in `task.label_map.project`** → stop. Say that this project is not mirrored. Do not guess a label
- **The link property is empty** → create
- **The link property is filled** → update

### 2. Draft the two binding sections

**These are the only sections that bind engineering.** Everything else in the ticket is a pointer, and a disagreement about it is settled wherever your team settles such things — not by this document.

They are drafted the same way whatever level carries them. What changes with `task.contract.level` is only where they are written and what the materials are read at: at `task`, this record's own spec entry and design; at `parent`, the spec entries of every task under it, so the contract covers the feature rather than one slice of it.

**Draft, do not invent.** Every line traces back to a sentence in the spec, a row of its states table, or a state variant that is actually drawn. Where the materials settle nothing, the line is not written. Where they settle nothing at all, step 6 stops rather than filing a placeholder.

#### Cover the materials first, then write

**Work the materials row by row.** A draft written from a general sense of the feature comes out short and plausible, and what it left out is invisible — which is the failure this section exists to prevent. Go through, in order:

- **Every row of the spec's behaviour table.** Each is a condition unless another line already covers it
- **Every row of its states and cases** — empty, loading, error, no permission, and whatever else that table carries
- **Every rule and exception** — inheritance, defaults, value constraints, and what happens where two rules meet
- **Every state variant actually drawn** in the design that the spec did not already produce a line for
- **The round trip.** After a create, edit or delete, where the result has to appear: the list it came from, and the other screens reading the same value

Four kinds have to be present or explicitly not applicable: **happy path, states and cases, rules and exceptions, round trip.** A fifth is required whenever `contract.design_match_line` is in play: **the side-by-side comparison**, one step per screen. A draft missing one of them is nearly always incomplete rather than small.

**Read what kind of entry it is before calling a kind absent.** A policy entry keeps its states inside its rules table rather than in a states table of its own, so "no states and cases" there is the entry's shape and not a gap. A behaviour entry with no states table *is* a gap. Reporting the two the same way is how a thin entry passes as a covered one.

**A row that produces no condition is named, not dropped.** Carry it into the preview as skipped with its reason — outside this ticket, already covered by another line, or nothing in the materials settles it. Silence is what lets a thin draft look finished.

**Those reasons are not equivalent, so the preview keeps them apart.** A row another line covers is bookkeeping. A kind that is empty because nothing anywhere says what should happen is a hole in the requirement — it will surface as a defect argument long after this ticket is closed, and the entry, not the ticket, is where it gets fixed. Count those separately, name each one, and where two or more kinds are empty for that reason, offer in step 6 to fill the entry first. The offer does not block: a coverage count that only measures how well somebody else wrote the entry should at least say so out loud.

**Where the materials settle nothing at all, draft nothing.** A ticket can legitimately come before its requirement — a board needs the row, a parent needs its child, a date is already agreed — and step 6 has a path for that. Padding the section to avoid an empty one is the failure that path exists to prevent.

#### Done conditions

One checkbox per line.

- The subject is the user or the screen, and the result is something a checker can see
- **One condition per line.** Nothing joined by "and"
- **It has to come out true or false.** "Works properly", "displays correctly", "behaves naturally" cannot be checked, and a line containing one is not a condition
- **Behaviour, state, thresholds and copy are written as words.** These are exactly what a design cannot settle on its own — a toast that disappears after three seconds is not visible in a still frame, and two people read the same empty screen differently
- **What is confirmed by comparing a value against the design is not written.** `contract.design_match_line` covers all of it in one line
- How it is built is not written

The line to draw is not appearance versus behaviour. It is **decided by looking versus decided by measuring**:

| Written | Not written |
|---|---|
| Used items appear with no background box | The box fill is `#F5F5F5` |
| The toast disappears after three seconds | The toast sits 16 above the bottom |
| With no items, "Nothing here yet" is shown | The empty-state text is 14 regular |
| The list is ordered most recent first | Cards are 8 apart |

The left column is presence, order, copy and timing — checkable without a ruler. The right column is a value to compare against, and the design is where that comparison belongs.

Three reasons it belongs there and not here, worth knowing because they decide the edge cases:

1. **A value written twice goes stale.** Change it in the design and the ticket still says the old number, and now somebody has to work out which one is authoritative
2. **The list can never be complete, and what is missing reads as exempt.** Ten of a screen's hundred values written down does not mean ninety are free — but that is how it gets read
3. **Nobody performs the measurement.** "16 of padding" is verified by eye in practice; two screens side by side catch the same error faster and catch the other ninety with it

`contract.design_match_line` is appended **only where the design side is handing something over**. A ticket the engineering side filed for itself does not carry it — that side writes its own QA checklist too.

**The line and the pinned version travel together: neither is written without the other.** A condition naming a version that was never saved cannot come out true or false, and it reads as satisfiable, which is worse than absent — the checker ticks it because there is nothing to check against. So where the record's design section carries no handover line, the match line, the per-screen comparison steps and the referenced-version row all stay out, and the ticket says in its links section that the design has not been handed over yet. They go in on the update pass, once it has. Where the label can be read back from the design tool, confirm it exists before writing it rather than trusting the record's text; where it cannot, the record's handover line is the authority and an invented label is never a substitute.

**Where that line is present, the QA section carries one step per screen** — `contract.design_match_step`, filled in for each:

```
- [ ] {design_match_step, screen 1}
- [ ] {design_match_step, screen 2}
- [ ] …
```

The done-conditions side stays a single line. It is the verdict; these are the work. Splitting the two is the point: a checklist saying only "confirm it matches the design" is confirmed by a glance, and naming every screen *inside* one checkbox is still one tick — the reader looks at the list rather than at the screens. One box per screen makes the screen nobody opened visible as the box nobody ticked.

The screens come from the design's structure — every frame in the handed-over section that this contract's conditions touch, state variants included. An empty state that only exists as a variant is exactly the kind of screen a hurried comparison skips.

**Where the count runs past `contract.design_match_max`, say so in the preview and offer to split the ticket.** Twenty comparison steps is a ticket covering twenty screens, not a rule that grew too heavy, and splitting is the same signal the grouping section already names. With the value unset there is no ceiling and no prompt.

#### QA checklist

Derived from the done conditions, **after** those are settled.

- Entry path → action → expected result, in that order
- A precondition, where one is needed, goes on the first line
- **Every done condition has at least one step that confirms it.** They need not be one to one, but a done condition no step reaches is the gap this section exists to close
- **Write the whole path every time.** "Same as above" hides the step that actually differs. The one exception is a variant sitting on a path already written out in full and differing by a single value — there, name the variant and that value
- **The expected result is what gets looked at, not a verdict.** "The tab opens" is not one. "The tab lists only used items" is
- A condition reachable several ways — another role, another device, an empty account — is several steps, not one step with a list inside it
- Device or OS goes last, and only where it changes the verdict
- **Nothing that needs internal state or a server response.** That is engineering's own verification, not an acceptance step

Entry paths come from the design's flow where it has one, and from the spec's behaviour table otherwise.

#### Grouping, and when to split instead

A contract written to cover a whole feature runs to dozens of lines, and a flat list of eighty is read the way any wall of text is read: the first screenful, then a scroll to the end. The lines are not the problem — each one is a requirement somebody needs — the missing structure is. So both binding sections are grouped, and the group, not the line, is the unit somebody reads.

- **One group per scenario** — one thing a person sets out to do, named the way they would say it: a list and its filters, registering and editing, one settings screen. A spec entry is usually one group; two entries serving one goal share one, and an entry covering two goals splits across two
- **The group heading sits one level below the section heading**, so whatever reads the section headings — a gate, a parser, a template check — sees exactly the sections it saw before
- **The same groups, the same names, the same order in both sections.** A condition and the step confirming it then sit across from each other, and a group with conditions but no steps is visible as the gap it is
- **What every group would otherwise repeat is written once.** Loading, failing to load, a save confirmation shared by several screens — these go in a group of their own, first, whose name says what it spans
- **Groups follow the order a person meets them in** — the flow's order where the design has one, the spec's otherwise
- **Grouping changes how the contract reads, never what it says.** No line is dropped, merged or shortened to even the groups out, and the coverage pass is unchanged. A group with one line is fine; a group nobody can name is two groups

Several conditions coming out of one spec entry still grow lines rather than splitting the entry. The ticket number is the identifier; there is no second version axis to maintain. There is no target line count, for the contract or for a group: a ticket carries as many as the work it covers.

**Where the groups outnumber `contract.split_offer_at`, the preview offers to split the parent instead** — one parent per scenario, each with its own contract. A parent is meant to be one scenario's worth of work in most trackers that have one, and a contract that needs that many groups is usually describing several. It is an offer, never a stop:

- **Splitting is not this run's to do.** It creates parents and moves the tasks under them, which is the tracker lead's call and its own preview. The offer names the groups as they would become parents, and the contract is filed grouped either way
- **Where the parent already has children, or the record says its shape was decided, say so in one line and file grouped.** Re-proposing a structure somebody already settled costs more than a long contract does
- With the key unset there is no threshold and no offer

### 3. Interview, once (grouped)

Ask everything still missing in one `AskUserQuestion` round. **Never ask for what the record, the spec or step 2 already answers.**

| Item | Where it comes from |
|---|---|
| Summary | The record's title by default, with an option to type another |
| Done conditions | Drafted in step 2. Ask only to confirm, or for a line the materials left blank |
| QA checklist | Drafted in step 2, the same way |
| What changed | The body's change summary if it has one. Empty → ask, and write it back in step 9 |
| Spec link | The record's spec property if set. Empty → ask, and store it back so the next run has it |
| Design link | The design section of the body, else ask |
| Referenced design version | The handover line in the record's design section, where the design side pinned one. Ask only where the line has no version, and drop the row where nobody can supply one — an invented label is worse than an absent row |
| Other links | Ask — dependencies, policies |
| Milestone | Only where `task.hierarchy.milestone_on` is not `none`, and only for a project listed in `milestone_projects`. With no `milestone_format` entry for that project, the options are the milestones already open and none is created |

Project, group, priority and dates come from the record and are not asked. Where the record has several assignees and the tracker takes one, ask which.

**The assignee is checked against the project's own tickets, not taken from the record alone.** Before the preview, read the assignees on this project's recent tickets **of the same kind** — parents against parents, tasks against tasks, and for tasks the same role (design, front end, server). A project usually has a pattern nobody wrote down: every parent carries the same two people, front-end tasks go to one person and server tasks to another. Where the precedent shows one, apply it, and where the record disagrees with it, show both in the preview and say which one was used. Where the precedent is mixed, ask rather than pick. A ticket filed with only the person who happened to file it is the usual way the pattern drifts.

**No ticket setting is left blank without a reason.** Go through everything the tracker takes for this kind of ticket — type, labels, priority, assignee, milestone, parent, board column, start and end dates — and fill each one from, in order: the record, the project's precedent above, then this interview. What none of those settles is asked here in the same round, never left empty and never guessed. The only blanks allowed are the ones a rule requires (a milestone the rules say a task inherits from its parent, say), and the preview names each one with the rule. A blank type is the costly one: a tracker that tells parents from tasks by type will read an untyped parent as a task and act on it — strip its milestone, warn about its assignees — without anyone noticing.

### 4. Resolve the parent

Follow `filing.md`, *Resolve the parent*. Only where `task.hierarchy.parent_kind` is set; with it `null`, tasks are a flat list — skip to step 5.

### 5. Assemble the ticket body

```
### {sections.project}
- Project: {project label}
- Version: {milestone, or "Not set"}

### {sections.summary}
{what this task covers, and where it stops. see below}

### {sections.done}
{this task's own completion — what its holder has to produce}

### {sections.links}
- {link_rows.spec}: {entry name} ({url})
- {link_rows.design}: {screen name} — {url}
- {link_rows.version}: {referenced version}     ← dropped when absent
- {link_rows.record}: {record url}
{any other links from the interview}

## {sections.schedule}
- Start: {date, or "Not set"}
- End: {date, or "Not set"}
```

**Where `task.template` names a template, that template is the skeleton** — its headings, in its order, including the ones no slot above maps onto. Fill the slots you can; leave every other section exactly as the template wrote it, placeholder text and all, and name those in the preview as left for a person. A template's placeholder is what tells whoever picks the ticket up that the section is theirs to fill, and deleting it hides the section instead of finishing it. **Write no heading the template does not have.** A section invented here outlives everything: the contract writer leaves what it does not own byte for byte, so an invented heading is never revisited by any later run, and the person who has to remove it is the one who did not put it there.

With the key null there is no template, and headings come from `task.ticket.sections`, written in the order that map is written; a slot set to `null` is dropped.

**Either way the names are the tracker's, never yours.** A ticket template is shared with everyone who files tickets, most of whom have nothing to do with this workflow, so renaming its sections to suit one process is a cost paid by people who get no benefit. What goes *inside* a section is yours to decide; what the section is called is not.

**No pointer to the parent is written either.** Where the tracker links a task to its parent, the parent is already on the screen, and a line naming it only adds a second thing to keep correct. It is also where an in-house word for the two binding sections tends to get invented — the ticket is read by people who were not in the conversation that coined it. Link rows come from `task.ticket.link_rows`, and a row whose value is missing is dropped rather than written as an empty bullet.

**The title and the sentences under it follow the title rules in `SKILL.md`** — what somebody will see or do, not what the machine does underneath.

#### The summary is a scope boundary, not a restated title

The one thing a task says that nothing else can. The parent describes the whole feature; this section says which slice is this one's, and where the neighbours start.

- Where the title already settles the scope, **write nothing**. A sentence repeating the title is worse than an empty section — it looks like content
- Where it does not, say what is in, what is out, and which ticket has the part that is out. A task that only says what it includes leaves the gap between siblings invisible until QA
- The split is known: drafting the contract reads every task under the parent, so which condition belongs to which task is already worked out

#### A task's own done conditions are not the contract

The contract says the feature behaves correctly. A task's done conditions say **this slice of work is finished** — what its holder has to produce. They sit at different levels and do not overlap, and a task whose done conditions restate the contract is the copy this whole design avoids.

The two kinds look different in practice:

| Task | Its done conditions are about |
|---|---|
| One that produces the requirement — spec, design, handover | The artefacts: the spec entry updated, screens and states drawn, the section handed over, the parent's links and contract filled in |
| One that builds against it | That slice built, and anything the slice touches that no sibling covers |

`task.ticket.done_defaults` lists the artefacts a recurring kind of task always produces, so a draft starts from them. Lines that do not apply are dropped at the preview, not left in.

**A default is a seed, never the finished line.** Filed as written, every task of a kind carries the same five sentences, and a checklist that reads the same on each ticket stops being read at all — it gets ticked. Three rules keep them from arriving generic:

- **Fill in the target, or drop the line.** "The spec entry is updated" becomes "the *sold-out and unavailable* entry gains its self-pickup rule"; "screens and states are drawn" becomes "the menu list's sold-out, unavailable and self-pickup states are drawn". Where the draft cannot name what is updated or drawn, the materials have not settled enough to claim the line, and it comes out
- **Every undecided item in the record earns its own line.** They are the most concrete thing a planning task produces, and they are what the parent is waiting on
- **At least one line has to be specific to this task.** Where none is, the preview says so rather than filing a ticket whose done conditions would fit any sibling

The preview counts them apart — `{n} specific · {n} from defaults` — because that ratio is the readable signal, and a page of defaults is the failure mode this section exists to catch.

**The task that fills the parent's contract is ordinary work with ordinary done conditions.** It is also what lets the parent leave the planning column, so those lines are the ones worth being exact about.

**The spec row carries the entry's name, not only its url.** A bare link says nothing about which requirement this ticket answers, and the reader has to open it to find out.

**The design link goes in exactly as it was handed over.** Where it is pinned to a specific version of the file, that pin is what makes the design-match line checkable at all; rewriting the link to a plain one silently unpins the contract. The referenced version is a file-level label, so tickets out of one handover share it and differ only in which screen they point at.

The record link is **for a person to click**. It is not what matching reads.

#### The contract block

Written into whichever ticket `task.contract.level` names — this one, or the parent.

```
### {contract.sections.requirements}            ← only where the key is set
- {spec entry name} — {one line of what it has to do} ({url})

### {contract.sections.done}
#### {shared group — what it spans}             ← only where groups repeat a line
- [ ] {one condition per line}
#### {scenario 1}
- [ ] {one condition per line}
#### {scenario 2}
- [ ] …
- [ ] {contract.design_match_line}              ← design-side only, after the last group
- {link_rows.version}: {referenced version}     ← directly beneath it, when pinned

### {contract.sections.qa}
#### {the same groups, same names, same order}
- [ ] {entry path → action → expected result}
- [ ] {contract.design_match_step, one per screen}   ← design-side only, last
```

**A contract small enough to read at a glance — one scenario, a handful of lines — is written without group headings.** A heading over every three lines is structure for its own sake.

**The sections go in the order `contract.sections` writes them**, which is the order the tracker's own template puts them in — not the order they were drafted. Drafting runs done first and QA from it; where the template reads QA before done, that is how it is written out.

#### The requirements section

Only where `contract.sections.requirements` is set. It answers a different question from the done conditions: **what the work has to do**, as against when it is finished. Trackers that gate a column on this section's presence are asking whether anybody wrote the requirement down at all.

- **One line per spec entry this contract answers** — the entry's name, one line of what it has to do, and the link
- **Never a copy of the entry.** The requirement has a source, and pasting it here makes a second one that will be edited on only one side. A pointer answers the gate honestly; a paste answers it by creating the drift this whole design avoids
- **The entries are the ones step 2 was drafted from**, so this section and the done conditions cannot name different requirements
- Where nothing is settled yet, the section says what is being waited on, the same way the placeholder's links rows do — an empty heading reads as something that got deleted

A section written to satisfy a gate and nothing else is worth noticing rather than filling: where there is no entry to point at, the requirement does not exist yet, and step 6's fork is the honest path.

**The version goes inside the match line, not on a line of its own.** `contract.design_match_line` takes `{version}`, so the condition reads as a verdict somebody can reach without looking elsewhere, and the section stays checkboxes with nothing else mixed in. The same label goes into each comparison step in the QA section, and those steps go last — they are the only ones with no click path, so putting them among the click-through steps breaks the reading order. Because the version is file-level, every ticket out of one handover carries the same label and only the node differs — which is why the link itself lives once, in the contract's links rows, rather than beside every task.

#### When the requirement does not exist yet

```
### {contract.sections.done}
> {contract.incomplete_note}

  ← {contract.sections.qa} is not written. The note says it is coming, and an
    empty heading reads as something that got deleted

### {contract.sections.links}
- {link_rows.spec}:   {not settled yet — what is being waited on}
- {link_rows.design}: {not settled yet — what is being waited on}
- {link_rows.version}: {when it will be filled in}
```

The note goes in **as a quote, never as a checkbox.** A checkbox invites ticking, which is how a placeholder ends up looking satisfied — the same failure that made "TBD" stop meaning anything. `{missing}` is filled from what the coverage pass could not settle, named specifically: a bare "not decided" tells the next reader nothing about what would unblock it.

**The links section stays, and every row says its own state.** The rule that drops a row with no value is for a ticket whose other rows are filled — one absent row among several reads as "not applicable here". It inverts on a placeholder: drop them all and only the heading is left, which reads as a section somebody emptied, and nothing tells the reader apart "not decided yet" from "forgot to fill it in". So each row is written and names what it is waiting on. The referenced-version row is the one that can say *when* rather than *what* — there is nothing to pin until a design exists.

### 6. Preview → "go"

```
[ticket preview]
Repo / board : {mirror.ref}
Parent       : #{n} {title}
Title        : {task.ticket.title, filled in}
Labels       : {label} ({where it came from — config, or the rule that requires it})
               required by the rules but not in the tracker: {label} — reported, not created
Assignee     : {mapped username} ({record, or the project's precedent — both where they disagree})
Blank on purpose: {setting} — {the rule that requires it}
Contract     : {level} → #{n} {title}   (or "this ticket", or "off")
Template     : {task.template.task or .parent}   (or "none published")
               left for a person: {section} — the template's own placeholder kept
Drafted from : {spec entry} · {design, or "no design"}
Coverage     : behaviour {n}/{n} · states {n}/{n} · rules {n}/{n} · round trip {n}
               covered elsewhere: {row} — {which line}
Materials    : {entry name} ({entry kind})
               {kind}: {why nothing came out — "rules table carries it", or
                        "nothing in the materials settles it"}
Sections     : {n} done ({n} specific · {n} from defaults) · {n} QA
               {n} requirements rows (where the section is set)
               comparison: {n} screens (or "no design handed over")
Groups       : {group} ({n} done · {n} QA) · {group} (…) · …
               {split offered — past contract.split_offer_at, or "parent already has children"}
Adapter marks : {call} ({file}) — comes off if it succeeds   ← only where a call this run makes is marked (unverified)

--- body ---
{step 5 in full}
--- end ---

{if the interview produced a new change summary:}
[to be written back into the record]
{the text}

{where task.properties.version is named:}
[version on the record]
{record}: {current value} → {milestone now in effect, or version_unset}
{every other record under a parent whose milestone this run set or moved, one line each}

shall I proceed? (go / changes)
```

**Where the done conditions came out empty, this is the fork.** Say which materials were read and what they did not settle, then offer both:

- **File it as a placeholder** — the contract block takes the form in step 5, `contract.incomplete_label` goes on where one is configured, and step 8 seats it in the backlog whatever `task.status_map` says. A ticket nobody can start yet does not belong in a column somebody picks work up from
- **Stop, and write the requirement first** — the right answer whenever nothing is waiting on the ticket existing

Where the tracker already gates on the sections existing — a column a ticket cannot leave without them — say so and prefer leaving `incomplete_label` unset. The gate does the same job without a label somebody has to remember to remove.

`contract.allow_tbd: true` takes the first without asking. It is not permission to file a bare ticket: the note and the seating happen either way, and the only difference is whether the fork is put to a person.

**A placeholder is never filed silently.** The report says what it is, and the run says plainly that `/pm:task publish` has to be run again before work starts.

**Three lighter forks sit alongside it.** None of them blocks — each offers the cheaper fix while the ticket is still cheap to change:

- **Two or more kinds empty for want of material** → offer to fill the spec entry first. Filing anyway is fine and often right, but a coverage count that is really measuring the entry should not pass as a measure of the ticket
- **No line specific to this task** → say which defaults it would be filed with, and ask what this one actually produces. A done-conditions list that would fit any sibling is not one
- **Comparison steps past `contract.design_match_max`** → offer to split the ticket. The screens are the work; the ticket is what is too big
- **Groups past `contract.split_offer_at`** → offer to split the parent, one per scenario, naming the groups as they would become parents. The contract is filed grouped whichever way the answer goes

**No external write happens before "go"** — not the ticket, not the write-back into the record. Both are in this one preview because both are writes.

**Title**: `task.ticket.title` as configured. Do not append your own qualifiers; add a short one only where the task's name alone leaves the kind of work unclear.

### 7. Create the ticket

Follow `filing.md`, *Labels* and *Create*: look for the ticket already there, create it, and write the link property into the record right after — all inside the same "go".

**At `contract.level: parent` the contract is a body edit on a ticket that already exists**, never a creation. Read the parent's current body, replace only the sections `contract.sections` names — the two binding ones, the requirements section where it is set, and the shared links section where `contract.sections.links` is set — and leave every other section of it byte for byte — a parent carries scenario, scope and links somebody else wrote, and this skill has no business rewriting them. Where the parent has no such sections yet, insert them **where `task.template.parent` puts them**, and where no template is named, where `contract.sections` orders them relative to what is already there, rather than appending to the end.

**The rest of the ticket is not this edit's to change, but it is not out of reach either.** A parent filed before any of this — headings somebody invented, a label the rules now require — keeps them through a contract write. Where `task.template` is set and the body does not match it, say so and offer the pass below. Never fold it into the contract write silently: they are two different changes, and one "go" should not cover both.

The milestone rules are *Milestone* in `filing.md`.

### 8. Attach it

Follow `filing.md`, *Attach to the board* — and *Milestone*, whose version copy-back lands in the record in this same "go".

### 9. Write back into the record

Follow `filing.md`, *Write the link back*.

### 10. Report

```
[done]
Ticket        : {url}
Parent        : #{n}
Contract      : {n} conditions · {n} steps · {n} rows skipped → #{n} {level}
                (or "placeholder — run again before work starts", or "off")
Link property : written at create
{spec link stored, where applicable}
{change summary written, where applicable}
```

---

## Bringing a ticket back to the template

Offered wherever `task.template` names one and the ticket's body does not match it, and run on its own with `--template` — the way out `/pm:task sync` names for a ticket it finds off template. **It is one ticket, one person, one preview and one "go"** — that is the whole reason it is allowed here and refused in `/pm:task sync`, where the same edit across a list would rewrite a hundred tickets somebody else wrote on a single approval.

**The case this exists for is a ticket this workflow itself produced.** A ticket filed before the template was named, or by a config that had fallen behind it, carries sections these skills invented — not somebody else's prose, this workflow's own output under the wrong headings. Refusing to touch it on the grounds that the contract writer never touches what it does not own is the right rule applied to the wrong ticket.

### What it does on its own

- **Renames a heading** to the template's name, where the two clearly correspond
- **Reorders sections** into the template's order. Blocks are moved whole, so a ticked checkbox stays ticked and a link stays a link — nothing is re-drafted on the way
- **Drops an empty section the template does not have.** Empty means empty: a placeholder comment is not content, an unticked checkbox is
- **Names the labels the rule document requires and the ticket lacks**, for the same approval

### What it never does on its own

- **Move content between sections.** Where a section the template does not have holds something, **ask**: which template section it belongs under, or the record, or leave it where it is. Leaving it is a real answer — the ticket stays off-template and that is the person's call, not a failure
- **Delete a section that holds anything**
- **Add a section the rules gate on, empty.** Where `task.policy.doc` says a column is gated on a section existing, writing that heading with nothing under it makes the ticket pass a gate it should not. Name it in the preview and say why it was left out. Other missing template sections are added empty and listed
- **Re-draft anything.** The contract sections are written by their own run, from the materials, with their own coverage pass. This pass moves text; it does not author it

### Preview

```
[template pass] #{n} {title}
Template : {task.template.parent or .task}

  heading                      → what happens
  {current}                    → renamed {template's name}
  {current}                    → moved to position {n}
  {current}                    → dropped (empty, not in the template)
  {template's, missing}        → added empty
  {template's, missing, gated} → NOT added — the rules gate {column} on it, and an
                                 empty one passes that gate. Fill it with
                                 /pm:task publish <record> --contract instead
  {current, has content}       → asked below

Labels   : + {label} (required by {the rule})
Content to place, one at a time:
  「{section}」 {n} lines — where does this go?
     {template section} / the record / leave it here

shall I proceed? (go / changes)
```

The questions come before the "go", not after it. An approval given without knowing where the content lands is not an approval of this edit.

**Report what stayed off-template.** A pass that moved four things and left one is a ticket that still differs, and saying "done" hides the one. Name it, and name why — the person chose to leave it, or the rules gate it.

## The update path

Taken when the link property was already filled.

1. **Read the current ticket body first**, including which boxes are already ticked
2. Steps 2–5 as before. **Skip resolving the parent** — it is already attached. Ask whether to replace the whole body or only the summary and links sections. The change summary is the point of most updates: read it from the record, and ask only when it is new
3. **A placeholder being filled is the ordinary second pass.** The note comes out, the two sections go in, `contract.incomplete_label` comes off, and the board seating is handed back to `task.status_map`. Say in the report that the ticket now has a contract, because that is the moment it becomes startable
4. **A ticket already in progress is the delicate case.** Re-draft the two binding sections from the current materials, then reconcile rather than overwrite: a line that survives unchanged keeps its tick, a line the spec dropped is removed and said so in the preview, and a new line arrives unticked. Silently resetting a checklist somebody has been working down destroys the only record of what was verified
5. Preview → go → edit the ticket, keeping the record link row intact
6. **Move the record and the board together, in the same "go".** An update that changes what is ticked has changed how far along the task is, and the two sides read that from different fields. Where `task.properties` names them, set the record's progress from the checklist as counted in this run, its start date where work has begun and the field is empty, and its end date where every condition is now ticked; seat the board column by `task.status_map` and set the board's own date fields to the same days. Put the line in the preview beside the body change rather than making it a second approval — **a separate gate is one that gets skipped**, and a ticket whose body moved while its board did not is precisely the drift `/pm:task sync` then has to go and find. Dates are the days things happened, not the day this ran
7. **Where the body still does not match `task.template`, offer the template pass above** — its own preview, its own "go", after this edit has landed. Two changes, two approvals, and the second one starts from what the first actually wrote
8. Write back into the record — the spec link only where newly given; the link property is already there; the version where it no longer matches the milestone the ticket sits under. Append the new change summary under the existing one

---

## Constraints

On top of *Rules every mode follows* and *The tracker's own rules — `publish` and `sync`* in `SKILL.md`, and the filing rules in `filing.md`:

- **Never overrule the tracker's own rule document.** Where `task.policy.doc` disagrees with a default here, the document wins, and a write it forbids is reported rather than attempted
- **Never name a milestone for a project whose naming somebody else owns.** No `milestone_format` entry means offering what is already open, and nothing more
- **Never write the contract at two levels.** `task.contract.level` names one. A copy on the other side is the drift the whole design avoids
- **Never rewrite a parent beyond its contract sections.** Read its body, replace those two, leave the rest untouched
- **Never reshape a ticket to the template without its own preview and its own "go".** It is a separate change from the contract, and one approval covers one change
- **Never add a gated section empty.** Where the rules gate a column on a section existing, an empty one defeats the gate. Report it instead
- **Never write a heading the tracker's template does not have.** Where `task.template` names one, its headings are the set and its order is the order. A section invented here is one no later run will revisit
- **Never resolve a template-against-config disagreement by writing both.** A configured section name absent from the template means one of the two is stale — name both and stop. Two sections holding the same thing is the failure this rule exists for
- **Never create a label to satisfy a rule.** A label the rule document requires but the tracker does not have is reported. Creating one puts a near-duplicate beside somebody's existing filter
- **Never file an empty ticket that looks complete.** Filing before the requirement exists is allowed and sometimes necessary; doing it without the note, the label and the backlog seating is not
- **Never draft a condition the materials do not support.** A plausible-sounding line nobody agreed to is worse than a short list, because it will be built
- **Never let a thin draft pass as a finished one.** The coverage line in the preview names every row that produced nothing and why. A short list is fine when the work is short, and visibly wrong when it is not
- **Never write a done condition that sends the reader to the design for behaviour.** Behaviour, state, thresholds and copy are words; only what is checked by comparing a value belongs to the design, under one line
- **Never name a version that was not pinned.** No handover line means no match line, no comparison steps and no version row — an unverifiable condition reads as satisfied
- **Never file a task whose done conditions are defaults only.** A list that would fit any sibling says nothing about this one
- **Read the tracker's current schema before writing** rather than trusting ids pinned in the config — options get renamed
- **Never edit a checklist and leave the progress and the dates behind.** The tick is what a progress figure is counted from, so an edit that moves one without the other puts the record and the ticket in disagreement the moment it lands. They move in the same approval
- **Never decide a version on the record side.** It is copied from the milestone the ticket sits under, and a different version is set there, on the tracker
- **Never copy the body across.** The record stays the single source, and the ticket links to it — apart from the two binding sections, which have no copy on the other side
- Verify after writing, and report what was actually written rather than what was intended
