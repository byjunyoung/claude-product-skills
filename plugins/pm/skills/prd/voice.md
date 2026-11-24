# voice — the language a spec comes out in

Read before drafting (`SKILL.md` 2.5) and again at the voice check (step 3, item 2).

**Who reads a spec decides how it is written.** The people who design the screens, settle the scope, run the product once it ships and answer for it when it breaks — some read code, none should have to. Write the plainest sentence that still carries the whole requirement, with no word they must look up before they can act. Plain is not simplified: the reader knows the product better than anyone, just not its internals, so nothing is rounded off to read easily.

This is not the terminology list. That list reads nouns, and a sentence containing none of them can still describe a machine rather than a product.

## The rules

**A rule says what a person sees and does** — not what the system decided on their behalf.

| Written from the inside | Written from the reader's side |
|---|---|
| The view switches depending on whether an active job exists | While something is being made, the screen stays on the progress view |
| The evaluation is valid for 30 minutes | If nothing has been confirmed for 30 minutes, it counts as finished and the screen goes back to normal |
| Applied regardless of the account's state | Everyone sees it, signed in or not |

**A number is written with its meaning beside it.** A threshold, a period or a count alone is a value, not a requirement — say what it does to the person it happens to. "Locks after 3 failures" becomes *three wrong tries in a row locks it, and one correct entry clears the count*.

**A cell in the behaviour or cases table says what happens**, not a noun standing in for it. Not *Transition*, *Restore*, *Refresh*, but *the banner clears*, *the list goes back to how it was*.

**A table cell holds one piece of information.** *Repeats every 30 minutes until it is fixed* is three — an interval, a behaviour and an end condition. Name a column for each and put one value in each cell: *repeat │ every 30 min │ until resolved*. Where a value shares its cell with its reason, or an action with its timing, split the column. The meaning a number carries still gets written — in its own column, or in the rule above the table — never folded into the value's cell. A list of the values one attribute can take is one piece of information and stays in one cell.

**Where a rule branches, it is laid out, not narrated.** A rule that turns on several cases — a second event arriving while the first is open, a state changing before its timer runs out, a higher-priority case overtaking a lower one — gets three things: a table of situation against outcome, one row per case; a flowchart of the order the rule is checked in; and one worked timeline walking a concrete sequence of events through the rule, with times. The table is where the case an essay skips shows up as an empty row.

**A word the reader may not have is explained where it first appears**, in three or four words, inside the sentence. Where the team's own term is the accurate one, keep it and gloss it; a folksy substitute invented to avoid it reads worse.

**A concept the field already has a name for is called by that name.** A threshold, a retry interval, a grace period, an incident — where people who run this kind of product share a standard term, use it rather than a description invented to avoid it. Prefer the form established in the document's language; fall back to the original-language term only where no established equivalent exists. Terms the entries rely on go in a **terms table** — term, meaning, original-language term — once per document, in the policy entry the others point to (or at the head of the entry using them). A term there means the same thing in every entry, and its official source is one line under references. The line this draws is between a field's standard vocabulary, which is defined and kept, and engineering's private jargon, which is still rewritten from the reader's side.

**A spec is written, not spoken.** Declarative sentences in the written register. A conversational verb, a metaphor or slang standing in for the precise word becomes that word: *ping the operator* → *notify the operator*; *the alert keeps nagging* → *the alert repeats every 30 minutes*; *the shop goes dark* → *every menu item becomes unavailable*.

**Written register changes how a sentence ends, not its words.** Keep the everyday word the reader would use; a rewrite that swaps plain words for dense nominal compounds reads worse than the speech it replaced. A cell that reads long is split into columns or rows, never compressed.

**The register holds in the cells, the open items and the evidence lines too** — the parts written last and fastest, where speech gets back in.

- A cell of a rules or open-items table ends as a short noun phrase or a value, not a clause somebody would say aloud (a behaviour or cases cell still says what happens, as above): *whether the drink goes in the powder dispenser* → *dispenser assignment for the drink*
- An open item names what is to be settled and leaves the person to the owner column — not a question to the room, not an instruction: *block the change on the server* → *blocking the change on the server*
- An evidence line states its reason or fact and its date, not how something looks to the writer: *it shows up as powder on screen* → *displayed as powder*
- A definition, a condition or a source is not bracketed inside a rule sentence or a cell — it gets its own column, its own sentence or a references line. The date and source closing an evidence line, and a TBD's owner, are the format's own
- A step from one thing to another is written out (*A is merged into B*), never chained with an arrow inside a sentence. Arrows in a flowchart are the flowchart's

## What stays out

Research turns up far more than the spec needs, and most of it is the grounds for a decision rather than the decision. Before a line goes in, ask whether the person deciding scope, drawing the screen or answering for the product would do anything differently for having read it. Where they would not, it does not go in.

| Found during research | What the entry carries |
|---|---|
| Where a fact comes from inside the system — a table, a lookup, a service, a document of engineering's | The fact as the person meets it: *a branch with no location does not appear on the app's map*. The source, if worth keeping, is one line under references |
| A value no screen shows and nobody chooses — a default engineering sets, a field left from an older system | Nothing. If engineering needs telling, that is the ticket's job |
| A value an operator enters and changes on a screen — a capacity, a threshold, a flag on some items — as it stands in today's data | Only the rule for entering and changing it: the range, who sets it, when a change takes effect. *A dispenser holds 2,000 g* is today's data; *capacity is set per container size and applies to every location* is the rule. Confirming or tidying today's value is a note to whoever owns the data, not an open item of the spec |
| How something is enforced — what a check looks at, which condition has to change | What the person sees until it is done, and who still owes the work: *closed branches stay listed in the app until the app side is changed* |
| A list of examples — vendors, models, codes | The kind of thing it is (*the card payment provider*), unless the reader picks from exactly that list on the screen |
| How a decision was reached — who proposed what, what changed on which date | Nothing in the background. The decision in force gets one line in the references' decision log |
| Something out of scope | Its name in the reader's words, not the command or channel it currently lives in |

The system is what is being specified, not the values somebody keeps in it: today's value written as a rule is wrong the next time an operator changes it.

A reason earns one clause, not a paragraph. A rule needing three sentences of background to justify itself is carrying research that belongs under references.

## The two guards

**Cutting a line must not cut a decision.** Before dropping one, check whether it held something somebody settled — a requirement, a default the reader chose, a dependency they must track. Keep that; drop only the mechanism around it.

**Changing how it reads must not change what it says.** Values, decisions, section order and table structure stay exactly as they were; only the sentences move. A wording pass that rounds a number or softens a rule has broken the document it was tidying.

## Symptoms to read again

Systems vocabulary is a symptom, not a banned list — *active*, *trigger*, *propagate*, *the presence or absence of*, *upon*, *the relevant*, rules chained with arrows in a sentence. Meeting one is a reason to read that sentence again from the reader's side; rewritten that way, the word usually has nowhere left to sit. A standard term from the terms table is not a symptom — *threshold*, defined once there, is the accurate word.

The examples here are English because this file is; the rules are about the shape of a sentence, and `meta.language` decides the language. Each reads the same translated.
