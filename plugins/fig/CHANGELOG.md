# fig

## 3.19.1 — 2026-09-22

- **3.19.0 reasoned about the pattern page from the rules and named the wrong check.** It said a page of patterns would come back as `[coverage] orphan` the day it was created. Running it on a live file says otherwise: coverage collects frames from **sections only**, so patterns sitting directly on a page are never looked at, and what actually fires is `[membership]` — which the structure script applies to every page-level frame without reading page strictness at all. The exception added in 3.19.0 is still the one that matters, but only once the patterns are filed in sections, which is where they belong for the other reason anyway. `/fig:draw`, `/fig:lint` and the example config now say so, and the measured behaviour of both checks is written down beside them
- **And the component check could never see a pattern page.** `component_audit.body_offset` exists to skip a full screen's nav column and top bar; a pattern frame is narrower than that offset, so every instance on one was skipped and the page returned `COMPONENT PASS` having examined zero instances — a clean report that measured nothing, which is worse than a violation. The offset is dropped on a page matching `naming.pattern_page_pattern`

## 3.19.0 — 2026-09-22

- **The cycle diagram had a step with no skill behind it.** Between `prep` and `arrows` it said "Draw the screens (official plugins, or by hand)" — the one step in the whole loop this bundle didn't actually do, so nothing carried the file's own conventions into it. What came back was two kinds of gap, both from the same cause: a screen drawn as an isolated component with no canonical context around it, so nobody could tell what the actual final screen looked like — and a state left as a bare dashed placeholder even where most of it was already knowable, because leaving it blank felt safer than drawing it wrong. `/fig:draw` is the new skill that fills that step: it clones the nearest canonical screen and changes only what the target describes, instead of building the new piece alone on an empty canvas; it searches the design system and the file's own sibling screens for how a state like this already renders before inventing new visual language; and where one fact is genuinely still undecided, it draws the rest for real and pins the open question as an annotation on the exact node it affects, rather than blanking the whole frame over it. `prep`'s placeholder step now hands off to it by name — "the design step" was always this skill waiting to be written
- **A design system holds the parts and nothing holds the arrangement, which is where a file actually drifts.** The same kind of row drawn twice a fortnight apart comes out two ways, each one defensible, because nothing in the file said how that row is built here — and neither the library (which owns the button) nor the common page (which owns one copy of a repeated state) is where that rule could have lived. So `/fig:draw` looks for it on a third page before it draws anything. Where the pattern is there it is followed; where it is not but two screens already agree, the rule is derived from them and **written to the pattern page**, which is the moment it either gets recorded or gets forgotten; where nothing answers at all, the run stops, because defining one binds every screen after this one and is not a detail of this screen. That last case takes its own preview and its own call — the pattern page is a different page, a script may switch pages only once, and an error rolls the whole call back, so a combined write would lose the screen along with the pattern. New config: `naming.pattern_page_pattern` and `naming.pattern_frame_prefix`, both shipping `null` — and `null` here does not turn a check off, it makes the skill propose adopting the page
- **A page of patterns would have failed the audit on the day it was created.** Coverage requires every screen frame to appear in the flow, and a pattern is an arrangement nobody navigates to, so all of them would have come back as `[coverage] orphan` — blocking. `audit-flow.js` now drops that page the same way it already drops the common page, and `/fig:lint` says so. With the setting still `null` the whole page reports as orphans, which is the signal to record it rather than a bug
- `prep`, `code`, and `tokens` pointed "designing the screens" at `figma:figma-generate-design` for lack of anything more specific to this bundle's own conventions. They now point at `/fig:draw`, which is built on the same primitives but reads the file's `pages.canonical` and `naming` before it writes anything
- **The spec is now read at both ends of a feature, not just after it ships.** `/fig:draw` takes `qa.baseline.prd` as its default source for copy — the same document `/fig:qa` judges against later — so a screen is drawn against the document it will be measured by. The reason it matters is downstream: a ticket's acceptance conditions are written from the design's structure and its copy, so a label invented while drawing becomes a line engineering builds against and ticks off. Left `null`, the skill asks for a source rather than assuming one

- **"No finished sibling in this file" is not the same as no baseline.** `prep` was told to measure a new page against a finished page **in the same file**, which is where the baseline usually is — and never says what to do when the file is new. A file opened for one domain has siblings that are empty too, so the rule read as "there is no baseline here", the fallback table took over, and the page became the first thing in the product built its own way. The search now widens instead of stopping: the file this page was branched from, the product's main design file, whichever file the team's guide names — a baseline one hop away is still the house baseline, and only a search that also comes up empty falls back to the table. Which file and page were read is named either way. The same read now also takes **each frame's height and what sits at its bottom edge**, because a page can carry every state the baseline carries and still cut each one off at an invented height, dropping whatever the finished pages keep down there

## 3.18.0 — 2026-09-21

- **A skeleton that passes every check can still be missing half the screens.** `prep` read a state's kind off its name, and `Empty`, `Loading` and `Error` sound shared — so they went to the common page under one annotation, and a whole class of screens left the to-draw list at once. What decides now is what is on screen: a state still showing that screen's own table, filters and header belongs to that screen however generic its name reads, and only a page replaced by a single message is common. The checklist is run as a union as well — a list with an edit card under the selected row is a list *and* a form, and owes both sets — because settling on the one type that fits best is how the other half goes missing. Ahead of both, the skeleton is measured against **a sibling page in the same file that is already finished**: how many frames one screen carries there is the house baseline, and it outranks the table in this document, which only ever described a floor. And since `/fig:lint` leaves the required-state check to judgement, the report carries coverage per screen — drawn, stubbed, still missing — beside the `PASS`, which is structural and never spoke to coverage. A stub is named as work owed instead of counted as done, because a gap you can see costs less than one you cannot

## 3.17.0 — 2026-09-07

- **A comment is not a declaration.** `proto_publish` was one line in the schema with its members named in a trailing comment, so a team that filled the block in got every key back as "present only in the team config" — the checker reads the schema, and the schema said the map had no members. The six keys `/fig:proto` already documents are declared for real now, which is also what tells anyone opening the file what publishing needs before they go looking for it. Whether publishing is on moved with them: it used to be the whole block being `null`, and it is now whether `repo` is set, so a config that names only the repo and the account inherits the rest instead of having to restate it. `/fig:setup` drafts the same shape

## 3.16.0 — 2026-09-04
- Layers still carrying `Frame 427` are reported, as a **warning**. The check was worth having before it was worth running: it is a regular expression over the names Figma assigns itself, so it cannot produce a false positive, and a page whose count is zero today is not a page that stays there. Layers **inside a component instance are excluded** — the name came from the library that made the component, no rename on this page can reach it, and reporting it here would put a number in front of the one person who cannot act on it. That the grade exists at all is why this could be added: on the old all-or-nothing verdict, one lazily named group would have withheld a whole section from engineering

## 3.15.0 — 2026-09-04
- **A gate that stops everything stops being a gate.** `lint` reported a passing page and a failing one, nothing between, so a section whose number disagreed with its place on the canvas was withheld from engineering on the same footing as one whose variants sit invisibly on top of each other — and `handoff` is written to refuse "hand it over now and fix it later", which left fixing the numbering or going around the gate. Every violation now comes back **blocking** or **warning**, read off the tag the script already emits rather than judged a second time, and `handoff` gates on blocking alone. Warnings travel with the section instead of holding it: they show in the choice table and in the report, so nobody hands over unaware. Nothing about what is audited changed, and a skill that has just written still needs the full `PASS` — the person who would fix the warning is standing right there

## 3.14.0 — 2026-09-04
- **A config shared across a team is a copy on every machine, and a copy has no way of knowing its own age.** `--origin` reports what the filesystem can answer — symlink, git work tree, how far behind, when it last fetched — and a `SessionStart` hook says so when a copy has fallen behind, staying silent when it has not. Nothing is declared and nothing has to be kept true by hand. `CLAUDE_SHARED_CONFIG` takes `off`, `fetch` (the default) or `pull`
- `--authored` stops a skill that would write on a value no config of yours mentions. No `fig` skill asks for it yet — no key here changes what gets written when it is inherited — and the resolver carries it because the two plugins hold that file byte for byte

## 3.13.1 — 2026-09-02
- A map keeps the order the schema declares, and writing every one of its keys is how that order is changed. Ordering was silently the bundled file's — a config that wrote a map out in its own order got the default's back, which for a map whose order is read out is a wrong answer with nothing to show for it. Partial overrides are untouched: naming one key must not move it to the front (shared resolver, same fix as `pm` 0.18.0)

## 3.13.0 — 2026-09-02
- The named version can be saved through the browser instead of being handed to a person. `use_figma` still rejects the version API, but the web app's *File → Save to version history* is ordinary DOM, so where a browser is connected and signed in on the right profile the pin happens inside the run. It stays a write to a shared file — same preview → go — and the label goes in through the clipboard rather than synthesized keystrokes, since mangled multi-byte text produces a pin nothing can match afterwards. No browser, or the wrong account signed in, falls back to asking

- Two skills were invisible to any installer with a strict YAML parser. `handoff` and `proto` carried a bare `: ` inside their description, and a colon followed by a space starts a mapping in YAML, so the frontmatter stopped being readable and `npx skills` skipped both without saying why — Claude Code's own parser is lenient enough that nothing ever showed. `verify` now parses every frontmatter the strict way
- Every skill that runs bundled code says so at the top. Installed as a bare file — which is what a skill-level installer produces — `${CLAUDE_PLUGIN_ROOT}` does not resolve and the scripts are simply not there, so the skill stops and names the plugin install instead of improvising the checks

## 3.12.1 — 2026-09-01
- The plugin's own README is written for the person who runs these commands, not for whoever wrote them. What each command does is said in plain words, the settings file is described as something Claude edits for you rather than something you open, and a Figma seat, a connected tool and an empty setting are each explained where they first come up

## 3.12.0 — 2026-09-01
- `/fig:handoff` pins the moment it hands over. A handover names a Figma named version, every section link goes out with `&version-id=`, and the task-doc line carries the label and the version's own date — which is what `/pm:task-publish` reads to fill a ticket's referenced-version row. Without a pin, "matches the design" moves the next time somebody edits the file, and a ticket leaning on it is checked against a target that shifted after it was written
- The version is Figma's own snapshot, so nothing is copied and no frozen duplicate of the file has to be kept current. Saving one stays manual — `use_figma`'s allowlist rejects the version API the same way it rejects `devStatus` — so the skill asks, the person saves, the skill reads it back over REST and stops rather than guessing when the token is missing or nothing matches
- New keys: `handoff.version.enabled`, `.name`, `.match`, `.ref`. Off by default
- `/fig:lint` now reads component sets. A set with no layout drops each new variant on the last one's coordinates, so several states render as a single component — the top variant draws fine and the rest are simply not there, which is why review keeps letting it through (`[variant stack]`). A set that grew past the gap it was placed with and buried its neighbour is caught too (`[library overlap]`) — the existing frame-overlap check looks at frames only, so a component page passed it. Both read coordinates alone and run without any convention configured

## 3.11.2 — 2026-08-31
- `/fig:handoff`'s own one-line description still promised the Ready-for-dev mark 3.11.1 had just turned off — the one line an agent reads before deciding to run it. It now says what the skill does and that the mark is off; `whoami` leaves its tool list with the seat check that is gone

## 3.11.1 — 2026-08-31
- The two Figma writes 3.11.0 shipped as unverified turn out to be unavailable, not untested: `use_figma` rejects `section.devStatus` (getter and setter both) and `figma.saveVersionHistoryAsync` with `"… is not a supported API"`. An Edit seat changes nothing — it is the tool's allowlist, and Figma's REST API reads a dev status but has no endpoint that sets one. `handoff.dev_status` and `sync.named_version` now ship off, the code is kept for a runtime that does expose it, and the skills say what the error means instead of pointing at the seat
- `starter-conventions.py` and `/fig:setup` no longer carry a team's own page prefix as the starter default

## 3.11.0 — 2026-08-29
- `/fig:handoff` — the last step of the cycle. `/fig:lint` is the gate, the person picks which passing sections go, the skill marks them *Ready for dev* in Figma (the status engineering sees in Dev Mode), hands over the section links, and writes one line into the task doc where a tracker is configured. `/fig:sync` marks sections *Completed* after canonical apply and saves a named version. `handoff.dev_status` switches the statuses, `sync.named_version` names the version. The starter skeleton opens with a Cover page. Measured against Figma's file-organization and Dev Mode guides
- The Figma writes for status and version are marked as not yet run on a live file — the seat where they were written could only view; the first run on an Edit seat verifies them
- No skill count is written anywhere any more; `verify.py` fails on one, because it went stale every time a skill was added

## 3.10.0 — 2026-08-29
- Preflight (shared with pm) speaks in plain words — verdict, then what to fix, then the table as detail. The README's troubleshooting is rewritten as what-you-see · what-it-means · what-to-do

## 3.9.0 — 2026-08-29
- Preflight (shared with pm) reads a `connector:` line from a tracker adapter, so `task_tracker.type` can be any word a team uses

## 3.8.0 — 2026-08-29
- `/fig:setup` takes a starter path when there is nothing to observe — a first file, a team with no conventions yet. Four rules in plain words with what lint catches for each, three questions, a config generated by `starter-conventions.py` that says on every line it was chosen rather than measured, and the first skeleton laid with `/fig:prep` as the first result. "Settle a few conventions first" is no longer the answer
- Starter fixtures under `tools/test`, run in CI

## 3.7.0 — 2026-08-29
- `/fig:setup` runs as an onboarding: it opens with what it produces, shows a six-step ladder and names each step, asks in the person's words, offers "leave it blank" on every question, and closes on the first lint as the first result with the commands that follow. `/fig:deck-setup` opens the same way
- Preflight (shared with pm) leads with a verdict in words and the lines to fix; the table is detail underneath

## 3.6.0 — 2026-08-29
- Preflight (shared with pm) requires whatever tool `task_tracker.type` or `guide_source.type` names, not only the ones it knew

## 3.5.0 — 2026-08-29
- The six skills that write to Figma — `prep`, `arrows`, `diff`, `sync`, `tokens`, `deck` — check the seat with `whoami` before the first write, and stop on a View seat instead of failing halfway
- Preflight (shared with pm) reads the config, treats a tracker it names as required, and checks the `gh` CLI where that tracker is GitHub
- `/fig:setup` says what the preflight cannot see — the seat — and which skills check it

## 3.4.0 — 2026-08-28
- `/fig:setup` opens with a preflight — python3 and PyYAML, node, and which connectors actually answer
- Getting started branches by what you installed: `fig`, `pm`, or a deck template
- Both plugin READMEs say what the setup step checks before it runs

## 3.3.1 — 2026-08-28
- `/fig:deck-setup` and `/fig:proto` state the figma-use prerequisite the other skills carry
- `/fig:deck` and `/fig:deck-setup` declare the Figma tools they call
- README states what each skill needs beyond `plugin:figma` — Chrome, Notion, Slack, GitHub
- Scope wording covers before the drawing as well as after

## 3.3.0 — 2026-08-26
- English as the default language across skills, scripts and manifests

## 3.2.0 — 2026-08-26
- `/fig:deck`, `/fig:deck-setup`

## 3.1.0 — 2026-08-26
- `/fig:qa` — baseline-referenced QA

## 3.0.0 — 2026-08-26
- Repository restructured to hold several plugins; `fig` moved under `plugins/fig`

Versions before 3.0.0 were a single-plugin repository and are not listed.
