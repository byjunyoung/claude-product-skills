# voice — how a review's cells are written

Read before writing the first cell (`SKILL.md`, *Voice*).

**The reader is between two other things.** The plan's author, or whoever acts on the report, knows the product better than you and has not read what you read. They should get each item from its title and its four cells, and open `more` only to check. A cell that needs a second read has failed, however correct it is.

The renderer counts characters, sentences, dashes, middle dots, arrows, quotation marks and ticket numbers left without a name. Everything below is what it cannot count.

## The rules

**The brief describes; it does not judge.** It tells the plan the way its author meant it, from the side of the person using it: *the manager registers a store, and it starts with the app switched off*, not *a POST creates the store record*. No finding, doubt or "but" goes in it; those are items.

**One cell, one job.** *Problem* says what is wrong. *If left* says what happens to the build. *Ask* says what to change. How it got this way, the reasons behind the ask and where you searched go in `more` or `looked`, or nowhere.

**Short declaratives, of uneven length.** A sentence with a subject and a verb, stating a fact. Put a short one next to a long one. A row of cells all the same length reads machine-made before a word of it is read.

**Join with words, not punctuation.** A dash setting off an aside, a list strung on middle dots, an arrow standing in for a verb: each is rewritten with a comma, a conjunction, brackets or a second sentence.

| Punctuation doing the work | Words doing it |
|---|---|
| Register · edit · groups · devices — none has a server ticket | Registering, editing, groups and devices have no server ticket |
| Save → list refreshes → row disappears | After saving, the list refreshes and the row is gone |
| The hide rule changed on the 25th — the design predates it | The design was last changed before the hide rule was |

**Quotations live in evidence.** The plan's exact words go in an evidence quote, as written. A cell names the thing in plain words, *the hide checkbox's label*, instead of quoting it, unless the wording is itself the finding. Then quote that one phrase, once.

**A ticket is named by what it is.** In evidence: its title as written, its number, its link. In a cell, and in the folded notes: a short name the reader recognises, and the number in brackets, such as *the store server ticket (#682)*. Never a bare number, and never the full title with its bracketed tags in a sentence. With `ticket_url` set, each number on the page links to its ticket.

**The location names the place, not the problem.** *Spec, order status and remake, requirements, the bulk remake row*, linked. What is wrong there is the problem cell's job.

**Identifiers stay out of the cells.** Revision ids, node ids, commit hashes, file paths and version ids belong to an evidence `source` or to `more`. A cell says *an archived revision*, *the list frame*, *the main branch*.

**Say it once.** A fact in *problem* is not repeated in *ask*. A quote on the card is not paraphrased in the cell beside it.

**State what you found; mark what you reasoned.** A found fact carries no "may", "might" or "seems". A conclusion you reasoned to goes in evidence or `more`, marked `inferred`. *If left* is a consequence and is written plainly; where it rests on a calculation rather than something seen, it says so in a few words and the calculation goes in `more`, marked `inferred`.

**The ask starts with the change.** A verb, the place, then the recommendation: *Open a server ticket for registering and editing under the parent.* Where there is a real choice, the options are listed under it, recommended first, each one line. The reason for the recommendation is one clause in `more` when it does not fit.

**No headline sentences.** A cell does not end on a punchline, a contrast built for effect, or a summary of itself. The sentence you are pleased with is the one to check first.

**One register for the whole report.** The language is `meta.language`. Use the register the team's own documents are written in and hold it in every cell; a report that changes register between cards reads stitched together.

## Before and after

One finding, as it came out of a run before the cells had budgets, and as four cells.

```
Before
  The epic has 39 children and only one of them, "Store maintenance mode — server
  (#682)", is a server ticket. Registration, editing, status and hiding, groups and
  device setup — none of these has a ticket that connects them to the server. The
  notes and other tickets defer several items "until the server is connected", and
  no ticket receives those either. [12-row table] [search log: six queries] Ask —
  before handover, open server tickets. Suggested grouping: ① … ② … ③ … ④ …

After
  title      Only maintenance mode has a server ticket
  problem    Registering, editing, groups and device setup have no server ticket.
  if left    The screens ship and nothing they save reaches the server.
  evidence   Store setup (#140): 39 children, one server ticket
             Spec, system account: "Created on registration, follows the store's status."
  ask        Open four server tickets under the parent before handover.
  more       the 12-row table of work and coverage; looked: the six queries
```
