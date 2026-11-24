# coherence — reading the entries against each other, and as engineering will

Read at step 3 (`SKILL.md` 3.1 and 3.2). The checks before these find what is missing, malformed or unreadable. These find a spec with no blank left in it that still contradicts itself, skips a case, or names a number nobody can count.

## Does it hold together — run in this order

**0. Every role and every state it names is defined.** Collect the roles, permissions and account words the entries use, and look each one up in the user-group table. Then collect the product's own state names — what the entries call the condition a machine, a screen or an order is in right now — and look those up too. A word with nothing behind it is reported as exactly that, *not defined anywhere*, never as a contradiction. It runs first because two entries that seem to disagree may be one thing under two names, or two different things; only the definition says which.

`structure.cases` is not where states are looked up: those rows are the shapes any screen can be in, the same in every document. A product's own states live in one policy entry, written like any other. Where none exists and the names have already gone three ways across three entries, propose one and settle it there, rather than reconciling entries pair by pair.

**1. Entries that contradict each other.** One allows what another forbids, or two say different things about the same object. Quote both, and say which fact would settle it.

**2. The case nobody wrote.** A condition with two branches and one outcome; a states-and-cases row left at `—` where the case plainly applies. Ask about the branch, not the table.

The inverse survives every check because the cell is not blank: **a row holding two cases in one cell** — an empty state written *nothing registered yet / nothing matched the filter*, an error row written *save failed / a required field is missing*. Each pair is two screens — one a whole page reached with no data at all, the other a line beside the field just typed in — and whoever draws from that row draws one of them. Split it into two rows under the same case name (Appendix B), or say which of the two this entry means.

**3. A number with no rule around it.** A threshold, a count or a period that is stated but not countable — what resets it, the boundary, the unit. "Locks after 3 failures" is not a requirement until it says when the counter goes back to zero.

**4. The other half of the switch.** An entry saying how something is turned on, created or added, but never what happens when it is turned off, deleted or undone. Ask what is left behind — the stored values, the places that displayed them, what somebody reopening the screen would find.

**5. What it does outside the screen it is written for.** Where an entry's setting reaches somebody it never mentions — the end customer, another surface, a display further down — say in one line what that person sees. Entries are split by the screen an operator works in, so a consequence one step away belongs to no entry unless one claims it.

**6. An entry that says this is how it works today, against what works today.** Only on entries describing what already ships — one proposing something new is supposed to differ. Where the material includes the code or a running build, read the values, cases and state names off it. Report; do not reconcile: a build drifts from an approved decision as easily as a document drifts from a build, and an entry quietly rewritten to match the code is how an approved decision disappears. Quote both sides and name the fact that would settle it. Where there was no code or build, say the check did not run.

**7. A state with a way in and no way out.** Collect the states an entry passes through — in progress, waiting, paused, stopped on an error — and find how each one ends. Where every way out waits on a signal from the very thing that stopped — a device that broke or was switched off, a service gone quiet — ask for one exit that does not: after a stated time, or by somebody's hand. Then ask what the screen shows while the signal is not arriving at all.

**8. Hiding something another entry still holds on to.** When an entry hides, removes or stops showing something, look for entries that reach that same thing to finish a job — closing, archiving, editing, registering it — and say how that job ends now. Item 5 follows a setting outward to the people it reaches; this follows a removal inward to the entries that relied on it.

**9. What is already there on the day it ships.** Where an entry brings a rule, a default or a state into a product people already use, find what existed before — records, accounts, locations already running — and say what each shows and does on day one: whether it starts from the new default or keeps what it had, whether somebody must act before it works the new way, and what becomes of a record the new rule cannot hold. On a product nobody uses yet, skip it.

**What to do with what it finds.** Settle and rewrite whatever the material settles — bar item 6, where which side gives way is somebody's decision. What needs a person becomes a question: together where independent, **one at a time where an answer changes the next**, since resolving a contradiction usually moves other entries. What cannot be answered now is a TBD **carrying who decides it and by when**.

## What engineering will ask

Engineering reads a spec once more from the system's side when it starts to build, and the questions that read raises arrive after the handover — each answer a round trip, an unanswered one settled by whoever is building. Most are not engineering's to decide: the question is how the system holds something, the answer changes what a person sees. Ask them here, on the entries proposing something not built yet, each only where it applies; one that does not apply is skipped, not written down.

1. **Every value the screen shows has a source.** A countdown in minutes and seconds needs the system to know the seconds; a failure message naming its reason needs the system to report one
2. **Where a value is kept, and who writes it.** A setting kept on the device and one kept on the account behave differently once somebody signs in on a second device; a state no part of the system records never appears anywhere
3. **Where the product's categories and the system's part ways.** A bundle the entry treats as one kind of item, the system files under a category it may not be in; a status the system has and the screen has no place for, which then shows as its nearest neighbour
4. **Other systems, and two things at once.** An outside service, or two actions that can overlap — a refund still running when the customer starts to pay: what the person sees while the other side is slow, refuses or answers late
5. **What is already there.** Whether existing records can be carried into the new rule as they stand — the other half of item 9

Read the answer off the code or build where the material has it; otherwise the question stays open. Where each answer goes is `SKILL.md` 3.2's table: into the entry when a person would see it, one `TBD (engineering, needed by …)` line when it decides whether the entry can be built, nowhere when nobody sees it.
