# pm

## 0.25.1 — 2026-09-18
- **The four checks in `/pm:prd`'s consistency pass read a rule only as far as it was written, never past it.** A vague word, a contradiction, an undefined case, a number with no rule around it — each catches what is on the page, none ask what the page leaves off it. Two more join: **the other half of the switch**, where an entry says how something turns on and never what turning it off, deleting, or undoing it leaves behind; and **what it does outside the screen it is written for**, where a setting reaches an end customer or another surface the entry never names. Same rule as the other three — settle it, turn it into a question, or mark it TBD

## 0.25.0 — 2026-09-16
- **A board read a verdict rests on could not be made reliably, and the adapter only warned about it.** `item-list` truncates without a word, raising the limit moves the cut rather than removing it, and a truncated board turns an existing ticket into an *unfiled* finding — which proposes creating the duplicate
- **The GitHub adapter now carries the paginated GraphQL read.** `--paginate` follows `pageInfo` itself, and the same call returns each task's parent and that parent's milestone, where a version is read when `milestone_on` is `parent`. One request replaces a listing plus a second pass over every issue
- **Two Notion shapes that cost a run each.** A date property cannot be queried under its own name — SQL splits it into `date:{name}:start` and two more — and the failure reads like a wrong property name rather than a shape. A select value the property has no option for is now reported rather than written, because adding one means rewriting the whole option list and a name left out empties every row holding it
- **`version stale` gains a case it must not copy, and says how to judge it.** A value the record's property cannot hold is reported. A milestone that looks wrong for the ticket is judged by the ticket's project label and never by its title — a title naming one product on a ticket filed under another is the ordinary case, not the drift

## 0.24.0 — 2026-09-14
- **Which release a task is tied to lived only in the tracker.** A planning list read on its own could say what was in progress and how far along, but not whether it was going out this month or sitting in the backlog — the milestone was on a ticket, usually on that ticket's parent, one click and one level away. `task.field_owner` had kept it off the list on purpose, so that no copy could fall behind
- **Now the list can carry one, and the copy runs one way.** `task.properties.version` names a record property that shows the milestone the ticket sits under, read at the level `task.hierarchy.milestone_on` names. The tracker stays the only place a release is decided. `/pm:task-publish` writes the copy in the same approval that files the ticket or moves a parent's milestone — and moves the records under that parent with it — and `/pm:task-sync` diagnoses a copy that fell behind as *version stale* and corrects it toward the tracker, never the other way
- **An open task with no milestone says so.** `task.properties.version_unset` is what it shows, and a new record from `/pm:task-draft` starts there. A closed record that never had a ticket is left blank, because a placeholder on finished work reads as a decision still pending; a filed one keeps its milestone as history. A backlog bucket is copied by name like any other milestone — whether it counts as a version is the rule document's call, not this plugin's
- Both keys ship `null`, and with them unnamed nothing is read or written. `/pm:setup` asks whether the list has such a column. The Notion adapter gains two things that bite: a select value with no option yet, and a property write that fires the database's own automations

## 0.23.0 — 2026-09-11
- **The check that kept engineering wording out of a spec only ever read nouns.** `forbidden_terms` catches *API*, *endpoint*, *cache* — and a sentence carrying none of them describes the machine just as well. *The view switches depending on whether an active job exists* passes every string check there is, and the designer reading it still does not know what appears on screen. That was the whole of the defence, so a spec drafted from code or from an engineering plan came out in that document's voice with nothing to stop it
- **`/pm:prd` now reads its own sentences back, as a second verification check beside the terminology one.** One question decides each rule, behaviour row and case row: does this say what a person sees, or what the system decided? The half that is a list stays a list; this half is a judgement and ships without one, because a vocabulary of banned framings is a file somebody has to keep true and it never is
- **Three rules with an answer, rather than a preference.** A number is written with its meaning beside it — a threshold on its own is a value, not a requirement. A cell in the behaviour or cases table says what happens instead of naming it: not *Transition*, but *the banner clears*. A term the reader may not have is explained inside the sentence that first uses it, and the team's own word is kept and glossed rather than replaced with something folksier
- **And a guard, because a pass over the wording is the easiest place to lose a decision.** Values, decisions, section order and table structure stay exactly where they were; only the sentences move. Rounding a number while tidying the sentence around it breaks the document more thoroughly than the wording ever did
- The rule is about the shape of a sentence and not about which language it is written in, so it holds under any `meta.language`. No new config key — the audience for a product spec is not a setting, it is what the document is

## 0.22.0 — 2026-09-11
- **Nothing watched a task while it was being worked on.** `/pm:task-publish` seated the board column and the dates once, at filing, and said in so many words that every later move belonged to whoever runs the board; `/pm:task-sync` diagnosed existence, duplication, parentage and fields, and never looked at how far along anything was. So between the day a task was filed and the day somebody noticed, the progress figure and the schedule were the two things no skill would ever correct — and a list where those are stale reads as a team that has stopped working
- **`/pm:task-sync` gains three diagnoses: progress stale, schedule blank, schedule past.** Progress is compared against the ticked fraction of the contract checklist, because that is the one number neither side has to invent. Dates are filled from the day something happened — the column moved, the first box was ticked, the last one was — and never from the day the run happened to take place. A slipped end date is reported and nothing is proposed: moving it is a decision, and a skill that quietly moves it makes the slip disappear
- **Where the checklist is the thing that is stale, it says so and asks.** Boxes ticked before the work behind them finished would otherwise be copied into the record as a number that was never true, which is how a task comes to read as done twice
- **`/pm:task-publish` moves the record and the board in the same "go" as the body edit.** An update that changes what is ticked has changed how far along the task is, and a second gate for that is a gate that gets skipped. The line sits in the preview beside the body change
- **New config: `task.properties.progress` · `.start` · `.end`, and `task.progress_source`.** All ship `null` bar the last, and with them unnamed these checks do not run at all — a blank field is not a drift when nothing was configured to fill it. `/pm:setup` asks for them once

## 0.21.0 — 2026-09-04
- **A ticket this workflow itself filed wrong had no way back.** 0.20.0 made new tickets match the tracker's template and left every existing one where it was, on the rule that the contract writer never touches what it does not own. That rule is right about somebody else's prose and wrong about a ticket these skills produced under headings a stale config invented — the sections are this workflow's own output in the wrong place, and nothing could reach them. `/pm:task-publish` now offers to bring one ticket back to the template
- **What separates it from the bulk edit that is still refused is the person.** One ticket, one preview, one "go", and a question for every piece of content that has to move — never a batch. `/pm:task-sync` sees the same drift across a whole list and still only reports it, now naming the way out instead of leaving the finding as a dead end
- **The pass moves text and does not author it.** Headings are renamed and sections reordered as whole blocks, so a ticked checkbox stays ticked; an empty section the template lacks is dropped; a section holding anything is never moved or deleted without being asked about, and *leave it here* is one of the answers. Re-drafting belongs to the contract run, which has the materials and the coverage pass
- **An empty section is not always harmless, and adding one can defeat a gate.** Where the rule document says a column is gated on a section existing — the machine checks presence, not quality — writing that heading with nothing under it lets the ticket through. Those are named in the preview and left out; every other missing template section is added empty and listed

## 0.20.0 — 2026-09-04
- **A tracker that publishes a ticket template was being ignored, and a skill wrote headings of its own instead.** `task.template.task` and `.parent` name it, and its headings — in its order, including the ones no slot maps onto — are the skeleton a ticket is built on. The config's section names stop deciding which sections exist and go back to what they are for: saying which slot each heading is. A section invented by a run outlives everything, because the contract writer leaves what it does not own byte for byte and no later run reaches it
- **A configured section name that is no longer in the template now stops the run and names both.** One of the two is stale and nothing on the machine can tell which — so writing the configured heading next to the template's is the one answer that must not be taken. Two sections then hold the same thing, the tracker's gates read one of them, and nothing about the ticket looks wrong. This is the failure that prompted the release: a config a few versions behind a template, and a ticket that came out looking finished
- **Labels a rule document requires are applied, and the preview says where each label came from.** They are read off `task.policy.doc` rather than listed in config, for the reason 0.18.0 gave for the rules themselves — a list here is a copy of a rule that changes at a meeting the file was not in. A required label the tracker does not have is reported, never created. `ticket.default_labels` is stated as the task level's and does not follow a newly created parent up
- **`/pm:task-sync` gained the one diagnosis nothing else could make.** A ticket filed by hand, or before the template existed, or by an older version of these skills, drifts from the template and no writer ever goes back to look — every one of them leaves what it does not own alone. The sync reads both and **reports**: which ticket, what differs. It proposes nothing and rewrites nothing, because the sections hold prose somebody wrote and a survey across a whole list is the worst place to edit it
- `/pm:setup` finds the templates rather than asking for them — the tracker publishes them, which is what this skill reads schemas for — and asks the one thing no schema answers: whether the tracker is run by a rules document, and where it lives. That key shipped in 0.18.0 with nothing to fill it in

## 0.19.0 — 2026-09-04
- **A key nobody wrote still answers, and `--need` cannot see that.** A config that omits a block resolves to the bundled floor's value, so the block is not missing — it is somebody else's, and a run decides the shape of what it writes from a default the team never saw. `--authored` is the axis beside `--need`: `/pm:task-publish` and `/pm:task-sync` refuse to write a contract on an inherited `task.contract.level`, name the key, and say where the copy came from. Preflight already kept the floor apart for this reason — a requirement comes from a value somebody wrote, never from a default nobody chose
- **A config shared across a team is a copy on every machine, and a copy has no way of knowing its own age.** `--origin` reports what the filesystem can answer: whether the file is a symlink, whether it resolves into a git work tree, how far behind that tree is, and when it last fetched. Nothing is declared and nothing has to be kept true by hand — a stamp naming the version a file was written for is a claim about the past nobody updates, and the person who reads the warning silences it by editing the stamp. A file written before any of this existed is described just as accurately
- **A `SessionStart` hook says when a shared copy has fallen behind, and says nothing when it has not.** Where the config resolves into a work tree, that is the team saying so structurally; anywhere else the hook returns without a word. `CLAUDE_SHARED_CONFIG` takes `off`, `fetch` (the default — looks, changes no file) or `pull`. Two plugins over one work tree do not fetch it twice, and a machine with no route out is not retried every session
- `/pm:setup` gained a ninth step that asks — once, at the end — whether anybody else runs these skills against the same tracker, and wires up a shared config where the answer is yes. A "no" ends it in a sentence: one machine cannot see whether its config is a copy, and a run that assumes a team nags a person working alone

## 0.18.0 — 2026-09-02
- **A tracker can be governed by written rules of its own, and now those are read rather than copied.** `task.policy.doc` names the document; the ticket skills read it once before the first write of a session, and where it disagrees with anything in the config or in the skill, it wins. Copying its gist into config is how a config goes quietly stale — the rules change at a meeting the file was not in, and nothing tells the file
- **A task with no parent is a legitimate answer**, under `task.hierarchy.parent_required: false`. A one-off fix, a chore, a ticket somebody's merge opened by itself — none of those has a feature to hang under, and forcing one produces the empty umbrella ticket that then collects everything unrelated. The preview says what it costs: with `milestone_on: parent` such a task cannot carry a version
- **The contract can now carry what the work has to do, apart from when it is finished** — `contract.sections.requirements`, for trackers whose template keeps the two apart and gates a column on the first existing. It holds one pointer per spec entry, never a copy: a requirement pasted into a ticket is the second source this whole design avoids, and it answers the gate by creating the drift. The sections are written in the order the map names them, which is the tracker's template order and not the drafting order
- **A milestone is never invented for a project whose naming somebody else owns.** A project listed in `milestone_projects` with no `milestone_format` entry still uses milestones — the open ones are offered and none is created. An invented one sits beside theirs looking official, and label derivation reads the title's prefix, so a wrong one mislabels everything under it
- **Closing is not always the sync's to do, and an automated close is not a decision.** Where the rules gate closing a parent on a person's sign-off, a close from here is reverted and the reopen carries no record of why; where the tracker's own enforcement closed a ticket for going stale, reconciling the record to closed turns a housekeeping sweep into a cancelled task. Both are reported and asked about instead
- **A map keeps the order the schema declares, and writing every one of its keys is how that order is changed.** Section order was silently the bundled file's, so a config that wrote `contract.sections` out in its tracker's template order got the default's back — and these sections are written into a ticket in that order. Partial overrides are untouched: naming one section must not move it to the front
- A parent is created with a sentence rather than with headings of its own. The contract writer leaves every section it does not own byte for byte, so a heading invented by the creation call outlives all of it

## 0.17.0 — 2026-09-02
- **Verification reads the entries against each other, not just each one on its own.** The six checks it had all answer "is anything missing or malformed", and a spec with no blank left in it can still contradict itself, skip a case, or name a number nobody can count — which is the version that survives review and falls over mid-build. Three checks added, and one that has to run before them
- **The roles have to be defined before anything else can be judged.** Every role, permission and account word an entry uses is looked up in the user-group table, and a word with no row is reported as undefined rather than as a contradiction. Two entries that look like they disagree may be naming one role twice or two different ones, and only that table settles which — judged without it the report comes out confident and wrong, which costs more than saying nothing
- What the material settles is settled and rewritten. What needs a person is asked — together where the questions are independent, one at a time where an answer moves the other entries. What cannot be answered now becomes a TBD carrying who decides it and by when, and without those two it does not pass

## 0.16.0 — 2026-09-02
- **The design comparison is one QA step per screen**, from the new `task.contract.design_match_step`. Naming every screen inside a single checkbox is still a single tick — the reader goes through the list, not through the screens — and the one condition with no click path of its own is exactly the one that gets read past. One box per screen makes the screen nobody opened visible as the box nobody ticked. The done-conditions side stays one line: that is the verdict, these are the work. `design_match_max` offers a ticket split past a screen count, since the screens are the work and the ticket is what got too big
- **No pin, no line.** Where the record carries no handover line, the match line, the comparison steps and the version row all stay out and the ticket says the design has not been handed over. A condition naming a version nobody saved cannot come out true or false, so it reads as satisfied — worse than absent
- Frontmatter is checked with a strict YAML parser, and every skill that runs bundled code says at the top that it needs the plugin rather than the file on its own — the same two fixes as `fig` 3.13.0
- **Coverage separates the entry's shape from the entry's holes.** A policy entry keeps its states in its rules table, so "no states and cases" there is its shape, not a gap; the same words about a behaviour entry are a gap. Rows covered by another line are reported apart from kinds nothing in the materials settles, and two or more of the latter offer to fill the entry first — a count that is really measuring how well somebody else wrote the entry should say so out loud
- **A default is a seed, not a finished line.** Every `done_defaults` line names its target or comes out, every undecided item in the record earns a line, and at least one line has to be specific to this task. The preview counts specific against default, because a checklist that reads the same on every ticket stops being read and starts being ticked

## 0.15.3 — 2026-09-01
- On a placeholder publish the links section stays, and every row says what it is waiting on. Dropping a row with no value is right when the other rows are filled — one absent row reads as "not applicable here". It inverts when none of them are: drop them all and only a heading is left, which reads as a section somebody emptied, and nothing separates "not decided yet" from "forgot to fill it in"
- This plugin's README is written for the person who runs these commands. The command table says what each one does in plain words, the settings file is described as something Claude edits for you rather than something you open, and the two operator-level sections — the scheduling wrapper and the Notion importer — fold away so what a first-time reader needs is what stays on the page

## 0.15.2 — 2026-09-01
- A ticket's section names come from the tracker's own template, not from this skill's preference. That template is shared with everyone who files a ticket, most of whom have nothing to do with this workflow, so renaming its sections to suit one process is a cost paid by people who get no benefit. What goes inside a section is ours to decide; what the section is called is not — and the project and version block is written again for the same reason, where the template asks for one

## 0.15.1 — 2026-09-01
- `task.hierarchy.milestone_format` takes a map keyed by project name, not one string only. A team whose projects run on different milestone axes — one on the month, another on a release version — had no way to write that down, and `verify` counted each project's entry as a key the schema did not know. Key it by the name the tracker shows, since that is what makes an existing milestone come up as a candidate

## 0.15.0 — 2026-09-01
- **The contract has a level.** `task.contract.level` says which ticket carries the done conditions and the QA checklist — the task, or the parent it hangs under. Put them where review happens: a condition and the step confirming it, split across two tickets, cannot be checked against each other and the coverage rule stops meaning anything. `level: none` files a summary and links only
- At `level: parent` the contract is its own run (`mode: contract`) rather than a rewrite triggered by every sibling task, and it is a body edit on an existing parent — the two sections are replaced and every other section of that parent is left byte for byte
- The referenced-version line is written directly beneath the design-match line, wherever that line goes. A line saying the build matches a design *at a version*, sitting on a different ticket from the version it names, points at nothing
- **A task's own done conditions are not the contract, and the two no longer collide.** The contract says the feature behaves correctly; a task's done conditions say this slice of work is finished — the artefacts for a task that produces the requirement, the built slice for one that works against it. `task.ticket.done_defaults` seeds the recurring artefacts so a draft starts from them
- The task summary is a scope boundary: what this slice covers, where it stops, which ticket has the rest. Where the title already settles it, nothing is written — a sentence repeating the title looks like content and is worse than an empty section
- **Where a design-match line is in play, the QA section must carry the comparison step, and that step enumerates every screen.** It is the one condition with no click path of its own, so it is the one read past; "confirm it matches the design" is confirmed by a glance, while a list is confirmed by going through it and a skipped screen shows. Added as a fifth required coverage kind
- `task.contract` now holds `level`, `sections`, `allow_tbd`, `incomplete_note`, `incomplete_label` and `design_match_line`; `task.ticket` keeps the task body's own slots. Where a tracker already gates on the sections existing, the guidance is to leave `incomplete_label` unset and let the gate do it
- A ticket now carries the two sections that decide when the work is finished — done conditions and a QA checklist — and they originate in the ticket rather than being copied from anywhere. The record answers why the work is happening; the ticket answers what counts as done, and the boxes are ticked where engineering works
- `/pm:task-publish` drafts both from the spec entry and the design before it asks anything. Behaviour, state, thresholds and copy are written as words; what is confirmed by comparing a value against the design is not written at all, and `ticket.design_match_line` covers it in one line against a pinned version. The rule is decided-by-looking versus decided-by-measuring, not appearance versus behaviour
- The design is read for structure — which state variants exist, what the screens are called, where the flow goes — never for how it looks, and copy comes from the spec first so placeholder text cannot freeze into the contract
- **Drafting is a coverage pass, not an impression.** Every row of the behaviour table, every state and case, every rule and exception, every state variant actually drawn, and the round trip after a write — each either produces a condition or is named in the preview as skipped with its reason. Happy path, states and cases, rules and exceptions and round trip all have to be present or explicitly not applicable, and the preview carries a coverage line so a thin draft is visible instead of silent
- Every QA step traces to a done condition, and a done condition no step reaches is the gap the section exists to close. A step writes its path out in full — "same as above" hides the step that differs — and its expected result is what gets looked at rather than a verdict
- **A ticket filed before its requirement exists says so.** Where the materials settle nothing, the preview forks — file it as a placeholder, or stop and write the requirement first. A placeholder carries `incomplete_note` under the done heading as a quote rather than a checkbox (a checkbox invites ticking, which is how "TBD" stopped meaning anything), names specifically what is missing, drops the QA heading the note already accounts for, takes `incomplete_label`, and is seated in the backlog whatever `status_map` says — a ticket nobody can start does not belong in a column somebody picks work up from. Filling it later is the ordinary second pass. New keys: `ticket.incomplete_note`, `ticket.incomplete_label`
- The update path reconciles instead of overwriting: a surviving line keeps its tick, a dropped line is named in the preview, a new line arrives unticked
- `ticket.sections` is a keyed map rather than a list, so a team can rename a section without the skill losing track of which slot it is. New keys: `sections.done`, `sections.qa`, `link_rows.version`, `allow_tbd_done`, `design_match_line`
- `/pm:task-sync` leaves the binding sections empty and reports the tickets it created as still needing `/pm:task-publish` — drafting a contract is not something a bulk reconciliation should do unwatched

## 0.14.0 — 2026-08-29
- Every sentence a person reads during a run is in plain words — the preflight verdicts and fix lines, what the scripts say when they stop ("is not supported yet", "is not set", "supported as the other side"), the README's troubleshooting as what-you-see · what-it-means · what-to-do, and a rule in every skill to say what a stop means rather than its code or path

## 0.13.0 — 2026-08-29
- Preflight reads the `connector:` line of a type's adapter, so a type a team writes (`gsheet`) requires the connector it actually runs on (Google Drive) rather than a name nobody prints. Found by running `/pm:setup` 3b for real against a Google Sheet
- Adapters declare `roles:` too, and `adapter.py --role` refuses a file for a side it does not serve with exit 4 — the schema allowed `record.type: github` and `mirror.type: notion`, and neither bundled file answered for that side
- The adapter templates and contract carry both lines, and 3b writes them
- `verify.py` now fails on a `${CLAUDE_PLUGIN_ROOT}` path that does not exist, a bundled adapter without `connector:` or `roles:`, an adapter naming a tool no skill may call, and a skill reference in the root README that does not exist. Every script under `_common` has a fixture or a syntax check in CI
- Preflight, draft-generator and importer fixtures under `tools/test`, run in CI

## 0.12.0 — 2026-08-29
- `/pm:setup` runs as an onboarding: it opens with what it produces and how long it takes, shows an eight-step ladder and names each step, asks in the person's words rather than the file's keys, offers "leave it blank" on every question, and ends on a first result — a context table drafted from one pasted message, nothing written — with the commands that follow
- Preflight leads with a verdict in words and the lines to fix; the table is detail underneath. A 400 on the GitHub connector says what usually causes it

## 0.11.0 — 2026-08-29
- Adapters are open. The calls for a tool live in `trackers/<type>.md` or `sources/<type>.md`, the type in the config picks the file, and `adapter.py` finds it — bundled, or yours in `adapters.dirs` outside the plugin. A type with no file stops the skill on exit 3
- What an adapter has to answer is written down — `trackers/README.md`, `sources/README.md` — with a template for each
- `/pm:setup` drafts an adapter for a tool it has never seen from the tools connected on the machine, marking the answers it could not verify. It also takes "nothing yet" and lays out one markdown repository that needs no other tool
- Chat and calendar are adapters too — `sources.chat_type`, `sources.calendar_type`; Slack and Google Calendar ship, every call checked against the live tool's schema and run once
- Preflight requires whatever tool the config names, not only the three it knew — a value somebody wrote, never a default alone

## 0.10.0 — 2026-08-29
- Preflight reads the config: a connector the config names is required, and a machine with no config yet is told nothing beyond the host can fail
- Preflight checks the `gh` CLI the GitHub adapter runs on — which account it is logged in to, whether the token carries `read:project`, and whether that account can open the tracker at all. A connector that is configured but not answering is reported apart from one that is absent
- `resolve-config.py --need` stops a skill on a `null` it cannot run without, naming the key, instead of running on nothing. `/pm:task-draft`, `/pm:task-publish` and `/pm:task-sync` ask for theirs
- `/pm:setup` takes `side` for a doc tool and a tracker reachable from different machines, re-runs the preflight with what step 1 named, and writes `null` with the question beside it for anything a person cannot answer
- A markdown tracker adapter, so `task.record.type: markdown` reads and writes a directory of files as the README already said it would
- Config-resolution fixtures under `tools/test`, run in CI

## 0.9.0 — 2026-08-28
- `/pm:log` reads the tracker through its adapter like every other skill here, instead of assuming one
- `/pm:log-review` asks an item's three questions in one round, and stops at `log.review.max_items`
- The log side is documented — why it is split in two, how to schedule it, and how to import an existing Notion log

## 0.8.1 — 2026-08-28
- `/pm:log-review` stitches by title where a period's files carry no urls, instead of returning every day as its own item

## 0.8.0 — 2026-08-28
- `/pm:log` reads the channel you type notes to yourself in, and carries the text across rather than a link that expires

## 0.7.0 — 2026-08-28
- `/pm:log` writes a day's work log as a file, and fills the days an earlier run missed
- `/pm:log-review` turns a period of those logs into accomplishment statements, asking for the role, the measure and the learning it cannot derive

## 0.6.0 — 2026-08-28
- `/pm:setup` opens with the same preflight
- Getting started reaches `/pm:setup` without going through the fig path first

## 0.5.3 — 2026-08-28
- `/pm:prd` declares the Notion tools it writes with

## 0.5.2 — 2026-08-27
- An empty search is no longer treated as evidence of absence

## 0.5.1 — 2026-08-27
- Issue listing no longer truncates where the diagnosis lives

## 0.5.0 — 2026-08-27
- A filed task is seated in the right board column

## 0.4.1 — 2026-08-27
- Corrected three claims the first real run disproved

## 0.4.0 — 2026-08-26
- `/pm:setup` and per-tracker recipe docs

## 0.3.0 — 2026-08-26
- `/pm:task-draft`, `/pm:task-publish`, `/pm:task-sync`

## 0.2.0 — 2026-08-26
- English release
