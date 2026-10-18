# Skill review — pm and fig

Status: review, 2026-10-18. Findings and proposals only; nothing here is built. Read it alongside
`2026-10-18-local-first-defaults.md` (the local-first design), which this review corrected in
place and whose section numbers the proposals below refer to (§1–§11).

## How this was done

- Six reviewers each read a set of skills end to end, together with every script, adapter and
  config section those skills run or name: pm documents (prd, setup); pm tasks; pm log and the
  repository frame; fig early stages (setup, read, sketch, prep, draw); fig quality (arrows,
  tokens, lint, sync); fig delivery (handoff, qa, proto, code, deck, deck-setup). `/fig:diff` was
  left out, since decision 7 removes it.
- Each reviewer was given the same six lenses: purpose and boundary, structure, correctness and
  drift, robustness, value over plain Claude and the official Figma skills, and gaps in the skill's
  own job.
- A seventh pass mapped the skills onto the product lifecycle and compared them with the official
  Figma plugin skills and public PM and design skill collections.
- High-severity claims that this document relies on were re-read in the source before writing:
  - `draft-conventions.py:215` writes `task_tracker: type: none`.
  - `handoff.version.enabled` and `log.enabled` both ship `false`.
  - tokens has no `Bash` while its body runs `resolve-config.py`.
  - `audit-struct.js` reads only the direct children of top-level sections.
  - `arrow-build.js:68-70` always paints the configured stroke.
  - sync's first signal is the AS-IS/TO-BE pair.
  - draw never reads `annotation_category`.
  - each `resolve-config.py` copy resolves its floor relative to itself.
  - `preflight.py` `dig()` returns `None` on a string.
  - task-publish's `--need task.link_property` runs before its mirror-none stop.

  Other findings are the reviewers' and are cited to file and line, so they can be checked.
- **One calibration.** A tool missing from `allowed-tools` was reported as "cannot" in several
  places. That list pre-approves tools; it does not restrict them. A missing entry costs a
  permission prompt in the middle of a run. That is a real problem for an unattended run and
  friction everywhere else, but it is never an inability. Those findings are rated medium here.

## Verdicts

| Skill | Verdict | Why, in one line |
|---|---|---|
| pm:prd | slim | The voice and coherence checks are the real value; tools, config drift and markdown naming are the problems |
| pm:setup | restructure | Configures tasks only, writes floor values, and its config stops the next command it recommends |
| pm:task-draft | slim | Clear single job; Notion-only phrasing, unused tools, thin markdown creation |
| pm:task-publish | restructure | Contract coverage is the value; the template pass and the contract mode move out, the constraints block repeats the body |
| pm:task-sync | keep | The drift diagnosis earns its place; two gates are too strict and its writes have no adapter calls |
| pm:log | slim | Unattended discipline is real value; "explicit invocation only" is not enforced |
| pm:log-review | keep | Must stay apart from log: one never asks, the other has to |
| fig:setup | keep, slim | Clear job; starter path moves to a reference file and the drafter is fixed |
| fig:read | restructure | Its token path breaks in zsh, and a token-free read through `use_figma` already exists |
| fig:sketch | keep | The leanest skill; only where `[differs]` lands and its tools need care |
| fig:prep | slim | Contradicts itself on annotations, carries dead code, and fights the official call-batching rule |
| fig:draw | restructure | Its hand-off to the official generate-design conflicts with that skill, and the pattern write comes before agreement |
| fig:arrows | keep, fix | Unique; re-sync overwrites line styles it promises to keep |
| fig:tokens | restructure | The audit belongs in lint; tokens keeps binding. Overlaps Figma's own *Check designs* |
| fig:lint | keep, slim | Structure and flow checks are unique; blind to nested sections, no section filter, grades by text match |
| fig:sync | keep, restructure | Its main signal moves to a direct working-vs-canonical comparison (D1); writes config without preview; version save described but not possible from its tools |
| fig:handoff | keep, fix | Two write gates in the wrong order; its pinned version does not reach pm under local defaults |
| fig:qa | restructure | Compares against the current file, not the pinned version; evidence capture and output paths are thin |
| fig:proto | restructure | The publish path lags the official Code layers workflow and is one person's gallery setup |
| fig:code | slim | Behind the official design-to-code on Code Connect, motion and assets |
| fig:deck | slim | Most of its length is pitfalls and one team's template values; its config keys are wired to nothing |
| fig:deck-setup | merge (decided) | Writes to Figma with no go gate; that problem moves into deck with the merge |

## Bin A — fixes that need no decision

Bugs and drift. Each is a designer's call to fix during implementation, listed in the appendix with
evidence. The ones that matter most:

1. **Audit scripts cannot see inside nested sections.** `audit-struct.js:35,45`, `audit-flow.js`,
   `audit-component.js`. A frame placed at (5000, 5000) inside a nested section passed both
   structure and flow. sync builds exactly that nesting when it archives, then trusts lint.
2. **arrows re-sync overwrites line style.** It promises to preserve colour, weight and dash
   (arrows:139, :189), but `arrow-build.js:68-70` always applies the configured values.
3. **Generators write floor values as if a person chose them.**
   - `draft-conventions.py:215` writes `task_tracker.type: none`, among other floor values.
   - `/pm:setup` 1b writes "everything else" from the floor (setup:155).

   Later default changes never reach those teams, and `--authored` gates are bypassed. This is
   also structural move S2.
4. **pm-only installs fail preflight without node.** `preflight.py:210-214` is a hard `missing`,
   but no pm skill runs node.
5. **The config setup writes stops the next command.** setup never asks `task.contract.level` or
   `task.progress_source`, which publish and sync require (task-publish:22-23, task-sync:19).
6. **Parent tickets duplicate.** publish creates parents without labels (task-publish:229). The
   GitHub adapter searches for parents by project label (github.md:41) and labels them when it
   creates them (:158-162). A parent made by publish's rule is not found next time, so another is
   created.
7. **A ticket can duplicate after a partial failure.** publish writes the record's link last
   (step 9), after the step that can fail. Write the link right after creating the ticket, and
   check the mirror by exact title before creating.
8. **`/fig:read` breaks in the default macOS shell.**
   - `${!VAR}` is bash-only (read:47).
   - `$FIGMA_TOKEN` is hard-coded instead of `tools.figma_token_env` (read:76, handoff:90).
   - It offers five options where AskUserQuestion takes four (read:103).
9. **The SessionStart hook can error on every session.**
   - `shared-config.py:87-90` catches `Exception`, but a missing PyYAML raises `SystemExit`.
   - The 20-second fetch has no `GIT_TERMINAL_PROMPT=0` or `BatchMode`.
10. **Dead or unread config keys:**
    - `prd.notion.heading_style`, `prd.reference_docs`
    - `sync.version_page_pattern`
    - `pages.strict` and `pages.free` in scripts
    - `deck.template_file`, `deck.fidelity`, `deck.batch_size`
    - `annotation_category` and `scope_tags` once diff is gone (now in §8)

## Bin B — structural moves, to approve as a block

**S1. Widen `verify.py` first. This is a prerequisite for the merges.** Today the config-key,
skill-reference, team-string and absolute-path checks read only `skills/<sk>/SKILL.md`, and skill
references are checked within one plugin (verify.py:192-238).

- After §6 and §7 move bodies into `draft.md`, `publish.md`, `sync.md` and `setup.md`, hundreds of
  lines would leave every check, including the team-string check.
- Scan these, against both plugins' skill names, CHANGELOG excepted:
  - `skills/**/*.md`
  - `_common/**/*.md` and `_common/**/*.py`
  - `.github/*.html`
- Add a description-length check (§9).
- Compare `plugin.json` and `marketplace.json` descriptions; today they differ and omit the log.

**S2. Generators write only what was observed or asked.** Covers the fig drafter and `/pm:setup`
1b, plus the fig drafter writing page rules at the top level of the user-wide config
(draft:94-101 against setup:271, which says they belong under `files.<fileKey>`).

**S3. One copy of each shared procedure, in `_common`.**

- **Version pin.** One reference used by handoff, sync and §11 (Ready for dev), in place of three
  diverging descriptions: handoff:68-100, sync:134 (which claims a browser it does not have), and
  example config:203-205 ("by hand", with a broken sentence).
- **Adapter lookup and exit handling.** Written three times today (draft:128, publish:491,
  sync:81). Goes into the `/pm:task` router.
- **Ticket filing rules.** sync creates "by publish's rules" (sync:119). A `filing.md` read by both
  modes keeps sync from loading all of publish.
- **Code in prose moves into scripts**, so `check.sh` and tests cover it:
  - tokens' audit (tokens:116-216), which also ignores its own scaffolding exclusions
  - sync's snippets (sync:160-235)
  - proto's text walk (proto:66-80), which qa needs for copy evidence

**S4. The official Figma skills own how Figma is called; fig skills own this file's conventions.**

- **draw and prep vs generate-design.** generate-design's wrapper frame at the page's top level and
  its `html_to_figma` path both bypass the clone of a canonical screen, which is the point of draw.
  Name the parts of generate-design that draw and prep use (component discovery; editing an
  existing screen) and the parts they do not.
- **prep's batching** ("verify after each step", "≤10 per call", prep:127, :194) fights figma-use's
  rule against splitting calls only to verify. Align with it, or state why not.
- **code** hands Figma reading, assets, Code Connect and motion to design-to-code /
  implement-motion. It keeps its own job: reading the repo's conventions, the comparison table, the
  three checks, and the PR gate. Its `download_assets` use conflicts with design-to-code:23.
- **deck's pitfalls** that the official figma-use-slides already states are replaced by pointers to
  it. The rest move to `deck/pitfalls.md`, with numbers taken from `template-spec.md` instead of
  one team's values (deck:94 and several pitfalls).
- **read** drops its personal-token REST section and lists pages through a read-only `use_figma`
  call, which works from any seat (setup:91 already does this).
- **Unused Figma tools** come off the lists. `get_design_context` in sketch and draw obliges the
  official design-to-code skill to load.

**S5. Every write gate in the order it happens.**

- **handoff** today saves the version (step 3) before its only preview (step 4). Step 5 says it
  writes nothing to Figma, and the constraints say the version entry follows go. Make the order:
  1. preview the version name → go → save → read it back
  2. preview the doc line together with *Ready for dev* → go → write the line → mark *Ready for
     dev* last, because marking notifies developers

  §11 has to edit handoff:23, :139, :143 and the config's "never offered" comment. Reading the
  status back through REST is an unrun call, so it belongs in §11's probe.
- **deck-setup** creates a file and builds slides with no go (deck-setup:38, :105-111). It also
  leaves its mirror file behind unreported. Gate both before the merge carries them into deck.
- **sync** writes `files.<fileKey>` into a config layer with no preview and no choice of layer.
  That layer may be a shared team repository.

**S6. `allowed-tools` matches what the body does.**

| Skill | Add | Remove |
|---|---|---|
| prd | Figma read tools, Slack read, `WebFetch`; say that `reference_sources` connectors will prompt | — |
| setup | `Edit` | — |
| tokens | `Bash` | — |
| qa | `Bash`, `Read`, `Glob` | — |
| read | `use_figma` | — |
| arrows, sync, setup, prep | `Skill` | — |
| task skills | — | unused GitHub MCP tools (the adapters use `gh`) |
| lint, sync | — | `notion-fetch` (and the README's claim that they need Notion) |
| log | — | `issue_read` |

**S7. Audit scripts.**

- One recursive section walker shared by struct, flow and component.
- A section filter: lint already tells people to "narrow to one section", and no script accepts one.
- Structured output (`{tag, grade, node, msg}`) instead of grading by matching message text.
- Tests for struct, component and arrow-build. A straight / elbow / detour → FLOW PASS round trip
  was drafted during review and can seed them.
- `component_audit.body_offset` ships `null`, not one team's 270/120.

**S8. Plugin identity in the shared scripts.** Keep the byte-identical copies: a plugin dependency
would force `pm` on `fig`. Three changes:

- Identify the plugin from `plugin.json`'s name, not a `/pm/` substring of the path.
- Give each copy its own `DEFAULT_NAME`.
- When fig borrows from pm (§3, §4), check pm's installed version. Below the version that ships
  §4, fall back to printing.

**S9. The `/pm:task` router, specified.**

- **Order.** Resolve without flags → branch on mirror `none` → resolve again with the mode's own
  `--need` and `--authored`. Today publish's `--need task.link_property` exits before its
  record-only message can show.
- **Argument grammar.** `draft <source>`, `publish <record> [--contract | --template]`,
  `sync`. "mode" already names publish's task/contract switch, and sync and publish send people to
  a template pass that §7's routing cannot reach.
- **What the router holds:**
  - the plugin guard
  - adapter lookup and exits
  - matching on `link_property` alone
  - reading the policy doc and template once per session
  - title rules
  - the no-invented-mappings rule
  - preview → go
  - `(unverified)` handling — setup:215 promises publish clears it, and nothing does

  Blocks lifted into the router are deleted from the mode files, not copied.
- sync's `--authored progress_source, contract.level` applies only when `task.properties.progress`
  is named.

**S10. Explicit-only where nothing is previewed.** `/pm:log` says "explicit invocation only" and
writes without preview. Give it `disable-model-invocation: true`, which per Claude Code's docs takes
its description out of context and leaves `/pm:log` working. Confirm that a scheduled
`claude -p "/pm:log"` still runs before relying on it.

**S11. READMEs.**

- The root README keeps one paragraph per plugin and links to the plugin README.
- The quick start shows the no-config path first.
- One claim lives in one place. Several sentences appear word for word in up to five places today.

**S12. pm:setup, reordered for local-first.**

- The no-tool start (1b) becomes the default path, and reading a tracker's schema becomes
  "attach a tracker".
- setup also covers what it skips today: `prd.*` (including the Notion ids nobody can find by
  hand), `sources.*_type` and `log.*`.
- 1b's proof stops relying on `--need task.record.ref`, which the new floor satisfies with no file
  written. preflight also has to apply §1's guard: today it would PASS the very config the guard
  exists for.

**S13. Hardening the markdown tracker, now that it is the default.**

- A file-name rule. "The path is the id" needs one.
- A base directory, and a `mkdir` when the folder does not exist.
- A header row in the context table.
- CRLF-safe front-matter parsing (`s[4:]`, markdown.md:78).
- Stop when the ref is not a directory, instead of returning nothing.
- An "append a line under a heading" operation for §4.
- `link_property`'s default matches the skeleton's `ticket:`.
- For `/pm:log`, today's run combines `git status --porcelain` with that day's mtimes. Otherwise
  an uncommitted edit reads as a quiet day. Backfill says it counts commits only.

**S14. The handoff → pm seam.** Replaces designer's call 10 in the design.

- fig writes under, and pm's publish reads, one language-independent heading key.
- "Design changes" in `meta.language` would duplicate the heading when the conversation language
  changes, and pm does not read it today (task-publish:72, :199-200).
- The design's Done-when gains a step: run `/pm:task publish` on that record and see the version
  row filled.
- Under the floor, `handoff.version.enabled` is `false`, so a new install pins nothing. That stays
  a config choice.

**S15. qa judges against the handed-over version.** handoff pins a version so that "matches the
design" stays put, but qa reads the current file (qa:4).

- Give `qa.baseline.tasks` the same `{type, ref}` shape as §3, or borrow pm's record.
- Read the `version-id` from the handover line, and open the `?version-id=` link in the browser qa
  already drives.
- Image export by version through REST has not been run; probe it before use.
- Defects go to a markdown file under local-first. "Record on the ticket" and "draft a reply" need
  tools qa does not have (qa:187), and contradict qa:25.

**S16. prd's markdown output is addressable.**

- A file-name rule, and stable anchors per entry, so `spec_url` and `link_rows.spec` can point at
  one.
- `split: domain` handled.
- How "Linked tasks" fills from `./tasks`.
- A destination when `target: notion` has no template (no parent-page key exists).

## Bin C — decisions for the owner

In the order they should be taken. Each changes what gets built.

**D1. diff's removal and sync's signal — decided.** sync's main signal was the AS-IS/TO-BE pair,
and only diff made pairs.

- **Decision:** compare each finished working frame directly with its counterpart on the canonical
  page.
  - Identical text means applied.
  - A difference is shown as it is, which also catches deletions and rewording.
  - No counterpart means a new screen.
- **Conditions (designer's call):**
  - Frames are matched by the `[screen]-[state]` name that `/fig:prep` normalizes.
  - Differences that come from other work landing on the canonical page in the meantime are graded
    "needs checking", not "not applied".
- **What it retires:** no AS-IS copy is needed, so `sync.pair_patterns` and sync's pair path go
  with diff.
- **Not chosen:**
  - draw keeping an AS-IS copy of every canonical screen it edits
  - accepting a whole-section text signal
  - comparing against the pinned version through REST

**D2. Which lifecycle gaps to fill — decided.** See the next section.

- **In scope:**
  - define-further 1: prd's overview gains problem, goal, success metric and In / Out
  - a new `pm:release`
  - a new `fig:review`, gated on probing how Figma comments can be read. The MCP is unverified, and
    REST needs a personal token.
- **Held:** `pm:readout` (it waits on define-further 1 being in use) and `pm:research`.
- **Before the new skills are built:** each gets its own design pass — inputs, outputs, who reads
  them, write gates. This review only places them. For `fig:review`, the value is the write-back
  (decisions into PRD entries, open questions as pins on nodes); a summary list on its own would
  repeat diff's unread table.

**D3. tokens — decided: the audit moves to lint.**

- lint gains an `[unbound]` check, so a colour left off the tokens is caught at handoff's gate.
- The audit code moves out of tokens' prose into a script under `_common/scripts`, where checks and
  tests cover it.
- tokens keeps binding only. Its "lint mode" wording goes, since the name collides with
  `/fig:lint`.

Figma's *Check designs* was not chosen. Its plan and beta status come from the reviewer and are
unverified: <https://help.figma.com/hc/en-us/articles/39592284074263-Check-designs-in-Figma>.

**D4. proto's publish default — decided: the GitHub Pages gallery stays the default.** A Code layer
next to the source frame, through the official figma-code-workflows (`send_code_to_figma`), is
offered as an option only where `whoami.code_layers_enabled` is true.

First decided the other way round. Reversed the same day because the feature had not reached the
owner's account: the toolbar showed no Code tool in Design mode. A default that cannot run would
detour on every run. Revisit once code layers are generally available.

Conditions on the option, from Figma's help article
(<https://help.figma.com/hc/en-us/articles/44193259600535>):

- Code layers are in open beta, rolling out gradually.
- Creating one needs a Full seat and edit access.
- Imports cost no AI credits. Editing a code layer through the agent is free on paid plans until
  2026-11-04 and uses credits after that.
- The article does not say whether people without edit access can play a code layer, or whether
  there is a share link.

**D5. The log's default — decided: on.** `log.enabled` ships `true`. This is safe because:

- preflight requires only values a person wrote, and null sources are skipped and named in the
  summary
- with S10, `/pm:log` runs only when called by name

With no config, it writes the day's log to `./logs` from what moved in `./tasks`. The design's
no-config promise includes the log again; see its Intent.

## Lifecycle gaps

```
discovery / research   thin    prd's precedent check only
problem framing        thin    task-draft's fact / inference / undecided rows
requirements           strong  prd
design — explore       medium  sketch (one direction; no side-by-side alternatives)
design — draw          strong  prep, draw, arrows, tokens
design — review        thin    lint checks rules; no human-feedback or accessibility pass
handoff                strong  handoff, /pm:task publish
build                  medium  code, proto
QA                     strong  qa
release                thin    sync applies to the canonical page; no notes or announcement
measure & learn        none
team ops               medium  log, log-review, deck, /pm:task sync (personal records)
```

prd has no term for metric, success or hypothesis. Its sections are Overview, Requirements, Linked
tasks, Design, Change log (`conventions.example.yaml:43`).

**Define further before adding anything:**

1. **prd's overview gains problem, goal, success metric and In / Out.** This unblocks the measure
   stage without a new skill. It ranks first.
2. **lint gains a contrast and accessibility set,** reusing tokens' token → hex mapping.
3. **handoff accepts a Figma Spec link** as what is handed over; the pinned version stays.
4. **fig:setup reads library Guidelines** as a convention source, if the MCP can read them (probe).
5. **`/pm:task` does not double-file** what a Figma Spec exports to an issue tracker (inference).
6. **prep's boundary with Figma's system check:** screen and flow states here, library component
   states there (inference).
7. **proto's choice between single HTML and a Code layer** (with D4).
8. **qa gains a `figma-spec` baseline type**, already reserved in the design's *Later*.

**Candidate skills.** Each one has to pass the question that removed diff: who reads what it
produces?

| Candidate | Stage | Job | Who reads the output | Overlap |
|---|---|---|---|---|
| `pm:release` | release | Turn a milestone into internal release notes and a user-facing announcement draft, from the tracker milestone, done conditions, the pinned version and open QA defects | Users, stakeholders — a real audience | Medium. The owner's personal reporting and messaging skills already write for some of the same readers; a public general release-notes skill exists |
| `fig:review` | design review | Sort review comments into decided / open / out of scope, and send each back to its PRD entry or node pin | The designer and PM deciding — **check this before building**; a decision log nobody opens repeats diff's table | Medium. Figma's agent already gathers comments into a Spec; Figma comments need the REST API and a token |
| `pm:readout` | measure, retro | After release, compare plan with actual: scope cut, milestones moved, defects, metric against goal | The team and its lead, once per release | Medium. Needs define-further 1 first; numbers are typed in, since no analytics connector is attached (inference) |
| `pm:research` | discovery | Turn interviews and feedback into sourced evidence rows for prd's appendix | prd itself | High. Hold — better as an input contract on prd than a skill |

**Ranking for a UX lead doing PM work** with Figma, a doc tool and an issue tracker:

1. define-further 1
2. `pm:release`
3. `fig:review`
4. define-further 2
5. define-further 3 and 4, after probing the MCP
6. `pm:readout`
7. `pm:research` (held)

**What was compared:**

- **Official Figma plugin 2.2.157** (read locally). Skills: code-connect, code-workflows,
  create-new-file, design-to-code, generate-design, generate-diagram, generate-library,
  generative-plugins, implement-motion, shaders, spec, swiftui, use, use-figjam, use-motion,
  use-slides. Workflow skills: generate-project-plan (a PRD to a FigJam plan board) and
  video-interaction-mapper (a screen recording to a state map). Planning boards, diagrams and
  recording analysis are therefore left out of the candidates.
- **Anthropic knowledge-work plugins — product management** (checked):
  - Skills: competitive-brief, metrics-review, product-brainstorming, roadmap-update,
    sprint-planning, stakeholder-update, synthesize-research, write-spec.
  - Source: <https://api.github.com/repos/anthropics/knowledge-work-plugins/contents/product-management/skills>
  - Its design plugin, per the reviewer: accessibility-review, design-critique, design-handoff,
    design-system, research-synthesis, user-research, ux-copy.
- **Other public collections** (reviewer-sourced, not opened for this document):
  - <https://github.com/phuryn/pm-skills>
  - <https://github.com/deanpeters/Product-Manager-Skills>
  - <https://github.com/Owl-Listener/designer-skills>
- **Figma's 2026-10-15 launches** — Specs, Code layers, library Guidelines:
  - <https://www.figma.com/blog/introducing-figma-specs/>
  - <https://help.figma.com/hc/en-us/articles/44049066011671>

## Appendix — findings by skill

Severity: H high, M medium, L low. Line numbers are against the branch this document sits on.

### pm

| Skill | Sev | Finding | Evidence |
|---|---|---|---|
| prd | M | Tools the body uses are missing (Figma read, Slack read, WebFetch) | prd:4 against :76-81, :111; yaml:86, :121-124 |
| prd | M | Markdown file name and entry anchors undefined; `split: domain` ignored by §3 | prd:221; yaml:102 |
| prd | M | `target: notion` with no template has no destination; prd never runs preflight | prd:36-38 |
| prd | L | Appendix row and column names drift from the config | prd:173, :237-242, :257; yaml:48-51 |
| prd | L | Ticket routing names no skill, so a rename sweep misses it | prd:30 |
| prd | L | Unclear whether a local markdown write needs go | prd:213, :217 |
| setup | H | Never writes `contract.level` or `progress_source`, which publish and sync require | setup:297-299; task-publish:22-23; task-sync:19 |
| setup | H | `node` row fails pm-only installs | preflight.py:210-214; pm README:127 |
| setup | M | 1b writes floor values; 1b's proof passes with no file | setup:155, :157 |
| setup | M | 1b lays out a log and a "draft → publish → sync" loop that do not run under its own defaults | setup:144-150; yaml:417 |
| setup | M | Side ownership omits `task.template`, `task.policy` and `task.contract` | setup:267, :200-202 |
| setup | L | Step ladder is off by one against the procedure | setup:40-52, :112, :157 |
| setup | L | `import-notion-export.mjs`: no CLI, unrouted, hard-coded `logs/`, overwrites day files, Korean-only defaults | import-notion-export.mjs:11, :67, :112, :114 |
| task-draft | M | No check for an existing record from the same source; Notion-only sentence on every run | draft:132 |
| task-publish | H | `--need link_property` exits before the record-only stop | task-publish:22, :30 |
| task-publish | H | Parent label rule contradicts the adapter → duplicate parents | task-publish:229; github.md:41, :158-162 |
| task-publish | M | Link written after the step that can fail → duplicate tickets | task-publish:484 onward |
| task-publish | M | Assignee rules conflict; `done` section names collide at level `task` | task-publish:206, :581, :241, :300-321; yaml:332-333 |
| task-publish | L | "three" introduces four items | task-publish:442 |
| task-sync | M | Relies on publish's body to create; lacks the create tool for record-less tickets | task-sync:94, :119 |
| task-sync | M | Writes (close, reopen, reparent, field edits, archive) exist in no adapter | trackers/README:63-73; task-sync:88-101 |
| task-sync | L | `--authored` stricter than the skill's own use | task-sync:19, :37, :125 |
| log | H | Markdown "what moved today" reads commits only | trackers/markdown.md:62-67; log:53, :66 |
| log | M | `log.me.tracker_user_id: null` leaves mine / team undefined | yaml:422; log:61 |
| log | M | "explicit invocation only" not enforced | log:3 |
| log | L | `adapter.py` without `--type` prints `none` and exits 0; log abbreviates the command | adapter.py:74, :81; log:76-77 |
| log-review | L | "Dropped for lack of url" contradicts the title-match rule | log-review:46, :59, :98 |
| frame | M | SessionStart hook exception and prompt handling | shared-config.py:73, :87-90 |
| frame | M | Plugin identified by path substring; same `DEFAULT_NAME` in both copies | resolve-config.py:42-43; preflight.py:30 |

### fig

| Skill | Sev | Finding | Evidence |
|---|---|---|---|
| setup | H | Drafter writes `task_tracker.type: none` and other floor values | draft-conventions.py:215-217 |
| setup | M | Page rules drafted into the user-wide config | draft:94-101; setup:58, :271 |
| setup | M | Interview lacks `qa.baseline.prd {type, ref}`; `guide_source` never read; S5 hands prep a page it cannot create | setup:127-134, :229; yaml:270 |
| setup | L | List of skills that write omits draw and handoff | setup:82 |
| read | H | `${!VAR}` breaks in zsh; hard-coded `$FIGMA_TOKEN`; five options | read:47, :76, :103 |
| sketch | L | `get_design_context` listed, unused | sketch:4 |
| prep | M | Batching rule fights figma-use; screenshot per frame with no cap | prep:108, :127, :194 |
| prep | L | Contradicts itself on Default annotations; dead `commonRef` | prep:68, :73, :139; prep-ops.js:4, :113 |
| draw | H | generate-design's wrapper and `html_to_figma` paths bypass the canonical clone | draw:13 |
| draw | M | Pattern written before the sketch is agreed | draw step 4 vs step 5 |
| draw | L | Claims lint reads Default annotations as coverage | draw:85; audit-struct.js:190-209 |
| probe-page.js | M | State-suffix regex is Latin-only | probe-page.js:56; setup:147 |
| arrows | H | Re-sync overwrites stroke colour, weight and dash | arrow-build.js:68-70; arrows:139, :189 |
| arrows | L | Mentions a midpoint check that does not exist; mirror unimplemented; detour up only, 80px fixed | arrows:173; arrow-build.js:77, :101 |
| lint | H | Nested sections unseen by all three audits | audit-struct.js:35, :45; audit-flow.js:35, :41-45; audit-component.js:72-73 |
| lint | M | "Narrow to one section" with no filter; grades by text match; "all PASS" forces out-of-scope fixes | lint:111-135, :115, :139, :179 |
| lint | L | Start-point distance measured to an infinite line | audit-flow.js:65-66 |
| tokens | H | No `Bash`, so its config is never resolved; no plugin-root path | tokens:4, :34 |
| tokens | M | Audit code lives in prose, unchecked; ignores scaffolding; effects claimed, not scanned | tokens:52, :116-216 |
| tokens | M | Calls itself the last check before handoff; handoff gates on lint | tokens:9, :19; handoff:56 |
| sync | H | Main signal lost with diff | sync:74-77; diff:63-71 |
| sync | M | Writes config without preview or layer choice | sync step 1.6, :253 |
| sync | M | Claims a browser version save without browser tools | sync:4, :134; yaml:203-205 |
| sync | M | Moving frames leaves the existing canonical frame undefined; cites a missing "deep link audit" | sync:106 |
| sync, arrows, tokens | L | Read-only page rules disagree with what writes the archive; arrows and tokens never check `pages.readonly` | starter-conventions.py:117; prep:48; draw:48 |
| handoff | H | Write gates out of order | handoff:80, :86, :101-109, :114, :139 |
| handoff | H | Pinned version does not reach pm under local defaults | yaml:207; markdown.md:11-37; task-publish:72, :199-200 |
| qa | H | Compares against the current file, not the pinned version | qa:4; handoff:72 |
| qa | M | Copy evidence needs a text walk; capture naming needs disk saves; "record on ticket" needs tools it lacks | qa:62, :131-135, :187, :25 |
| qa | L | Describes `/fig:code` as sending differences back into the file | qa:23 |
| proto | M | Publish path lags Code layers; "no dedicated skill" note stale; skips design-to-code before `get_design_context` | proto:13, :27, :108, :150-163 |
| code | M | No Code Connect, no motion route, `download_assets` against design-to-code | code:75, :96; design-to-code:21, :23 |
| deck | M | Config keys wired to nothing; neither deck nor deck-setup resolves config | yaml:228-234; deck:52, :81 |
| deck | M | One team's values in the body; archetype table names builders deck-setup does not make | deck:94, :140-155; deck-setup:96 |
| deck | L | `skillNames` described as loading skills; cloned slides not placed in the grid (inference) | deck:72; deck-base.js:78-80 |
| deck-setup | M | Creates a file and builds slides with no go; mirror file left behind; no `whoami` | deck-setup:38, :105-111 |
| READMEs | L | Stale numbers and rows: "thirteen skills", "four rules", handoff missing from tool rows, deck assets path, lint table tags, sync "has no audit code" | _common/README:3; README:129, :145-147, :227, :362-368, :616, :699 |
