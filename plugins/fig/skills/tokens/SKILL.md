---
name: tokens
description: Binds the hand-typed colours on a Figma page or section to the design system's tokens, after showing which token each colour maps to and what binding changes, once /fig:lint has flagged unbound colours or whenever a colour may have been typed in by hand. Triggers - "/fig:tokens", "bind these colors to tokens", "check the token bindings", "find unbound colors", "토큰 바인딩 검수", "하드코딩 색상 검사", "디자인시스템 연동 점검", "토큰으로 묶어줘".
allowed-tools: AskUserQuestion, Bash, Read, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__search_design_system, mcp__plugin_figma_figma__get_screenshot, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__whoami
---

# fig:tokens — bind hand-typed colours to design system tokens

Connects colours typed in by hand to the design system's variables, through **a mapping that has evidence behind it**. Theming, rebranding, and consistency only hold if every color goes through a token. Finding those colours is `/fig:lint`'s job — its `[unbound]` check, which holds a section back from handoff where a colour matches a token exactly. This skill binds them, after the person has seen what each colour maps to and what binding it changes.

**Prerequisites**: always load the `figma:figma-use` skill before calling `use_figma`.

**Seat check before the first write** — call `whoami` once. Where every plan it lists carries `seat: View`, stop before any `use_figma` write and say so: the reading half of this skill runs on a View seat, the writing half needs an Edit seat on the file's plan, and no retry changes that. Where the seats are mixed, go ahead — and if the first write comes back as a permission error, report the seat table and stop rather than retrying.

## When to invoke

- `/fig:lint` reported `[unbound]` colours and they should go onto tokens
- "convert the hardcoded hex values to tokens", "bind these colours to tokens"
- A section held back from handoff by an exact-token colour

A request that only asks to check — "find unbound colors", "check the token bindings" — runs the scan (step 1), reports it, and stops before binding.

## When NOT to invoke

- Only finding the unbound colours → `/fig:lint` (its colour-token check reads and never writes)
- Frame naming and section tidying → `/fig:prep`
- Structure and flow rule violations → `/fig:lint`
- Flow arrows → `/fig:arrows`
- Creating the tokens (variables) themselves → `figma:figma-generate-library`
- Designing screens → `/fig:draw`

## Inputs

- `figma_url` (required): the page to bind
- `section` (optional): a section link or a section name, read the way `/fig:lint` reads it — that section and the sections nested in it. Omitted, the whole page. The scripts scope by page or section, so a link to a frame narrows to the section that holds it, and the preview says so. A frame that sits in no section narrows nothing: the preview says that too, and that the run covers the whole page

The rules come from `figma-conventions.yaml` — read the `design_system` section (library, token groups, threshold), the scaffolding names in `naming` and `pages.exclude_sections` with `resolve-config.py --js <fileKey>`.

## Why the work is in scripts

- **`get_metadata` cannot see colors.** Metadata carries node id, type, coordinates, and size, with no fill, stroke, or effect color. On a large frame it also blows the token limit and fails wholesale. So **all color reading and binding walks nodes directly through a `use_figma` script.**
- **`search_design_system` does not return a token's hex.** It returns the name, key, scope, and owning library. The colour comes from the scan (below).
- **The scan and the bind agree on which colours are the design's own.** Both scripts carry the same `<paint-scope>` block, so the bind never touches a paint the scan left alone — one inside an instance, or one applied through a style, which binding would detach from its style.

## Where token values come from — the scan's dictionary

A mapping is only as trustworthy as your knowledge of "what color is this token, really". The scan builds that dictionary from the file itself.

1. **Every colour variable already bound on the page, plus the file's own local colour variables**, each read in its collection's default mode, aliases followed. That shows exactly what colour this file renders each token as, which makes it the primary evidence for any mapping.
2. **Where a library token's own value cannot be read** (a collection the script is not given), the colour its bound paints show stands in.
3. **A library token nobody in this file has bound yet cannot be seen from a script.** `search_design_system` over the groups in `design_system.token_prefixes` finds it by name and key (`design_system.library` picks the library; on `auto`, the one the file is connected to) — never by colour, so a mapping to such a token has no colour evidence, and the preview says so. **Never hardcode a library name in this document** — it differs per file.

The dictionary holds each token's variable key with its scopes — the properties it may be bound to. Names for the preview come from `search_design_system` by key; a key it does not return is shown as the key.

> **Caution — a token's real value may differ from the hex you were given.** "Change this grey to `fill/primary`" can still mean `fill/primary` is slightly different from that grey (which is fine if tokenizing is the goal). Whenever the color changes, **the preview must say "this token is #AAA, so the screen becomes #BBB".**

## Properties

fill · stroke · text color (a TEXT node's fills) · effect color (an effect's color) are all read and bound. Different properties take different token scopes — a background fill `FRAME_FILL`/`SHAPE_FILL`, a border `STROKE_COLOR`, text `TEXT_FILL`, an effect `EFFECT_COLOR`. **The bind script binds a colour only to a token whose scopes include its property** — never a text color to a border token — and returns the rest in `skipped`. The scan grades by the same rule (both scripts carry the same `<token-fit>` block), so a colour counts as exact only against a token that could be bound where it is, and `/fig:lint` never holds a section back for a token this skill would refuse. One colour that needs a fill token on fills and a text token on text takes two mapping entries for the same hex; each paint takes the first that fits.

## Left alone (read for the report, never bound)

| Target | Why |
|---|---|
| Colours **inside a component instance**, including overrides on its layers, and an instance's own paint on a property it does not override | They belong to the component — tokenize them on its source in the library. The instance's *own* override is in scope; its layers are not, overrides on them included |
| Paints applied through a style, and text with part of it in a style | Already on the design system; binding one would detach it from its style. Text in several styles is left by the bind only — `/fig:lint` still reports its colour |
| Working scaffolding | Arrows, labels and state chains by the names in `naming` (`arrow_delimiter`, `label_prefix`, `state_chain_prefix`), placeholders by their `placeholder_style` paint, and a section's or component set's own paint — `/fig:arrows` and `/fig:prep` output, not design to tokenize |
| Sections in `pages.exclude_sections`, and hidden layers | Archives, templates, and the like; what nobody sees |

Excluded items that turn up are **reported, never fixed** — colours inside instances in particular are grouped separately as "a component repair issue".

## Grading — only auto-propose what is safe

The scan grades each unbound colour against the dictionary, colour and opacity together, counting only the tokens scoped for the property the colour is on — the same grades `/fig:lint` reports, except that lint calls a colour on a node loose on the canvas, outside every section, a warning whatever its grade, since handoff gates sections. The scan still grades it, and binding it is as safe as anywhere.

| Grade | Basis | Handling |
|---|---|---|
| 1 — exact | Colour and opacity both equal a token's that is scoped for that property | Binding changes nothing you can see in the token's default mode → **auto-propose the mapping**. A node set to another mode, where the token renders something else, is not bound without asking (step 3) |
| 2 — near | Every colour channel within `design_system.match_threshold_channel` of the nearest token scoped for that property, opacity aside — so the same colour at another opacity is near, never exact | Binding changes the colour or the opacity → **show the change; the person decides** |
| 3 — none | Further from every token scoped for that property, or a brand or special colour. Also an exact colour whose tokens are all scoped for other properties — a rectangle's fill matching a text-only token; its row's `nearest` is its own hex and its `tokens` are empty | Binding not advised, report only. For an exact colour with no token scoped for it, say so: the fix is the token's scopes, in the library, not a binding here |

The threshold is a baseline, not a verdict — for borderline colors, show the delta so the user can judge. `null` makes it 0, so only the same colour at another opacity is near.

## Procedure

Every step runs a script under `${CLAUDE_PLUGIN_ROOT}/_common/scripts/`, called the way `/fig:lint` calls its audits: the single `const CFG = {...};` line from `resolve-config.py --js <fileKey>`, the input lines below, then the whole file, handed to `use_figma` — with one `setCurrentPageAsync` line first where the page is not the first. The code is not copied into this document.

### 1. Scan (read-only)

Run `audit-tokens.js` with `const MODE = "collect";`, and `const SECTION = "<section id>";` where a section was given. It returns:

- `dictionary` — `{ hex: [{ key, scopes }, …] }`, each colour the file's tokens render and the tokens that render it, each with the properties it may be bound to (`null` where they cannot be read)
- `unbound` — `[{ hex, kind, count, nodes, grade, nearest, tokens }]`, the directly editable colours on no token, one row per colour and kind (`fill`, `text`, `stroke`, `effect`), split again where the tokens that fit differ — a frame's fill and a shape's, say. `count` is paints, `nodes` the node ids, `nearest` the dictionary entry it was graded against, and `tokens` the keys at `nearest` scoped for every paint in the row — `[]` where none is
- `inInstance` — `[{ hex, count }]`, colours held inside instances, for the "component repair issue" line
- `note` — a dictionary left empty, or colour variables that could not be read; print it

A colour at full opacity is written `#RRGGBB` and any other `#RRGGBBAA`, in every field. A section that is not on the page makes the scan throw; ask which one was meant.

### 2. Settle the mapping (user's choice)

- Present grade 1 as a table: hex and kind → token (name and key), count, a few nodes. **Propose only a key from the row's `tokens`** — never one read off the dictionary, which also holds tokens scoped for other properties that the bind would refuse. **When one row lists two tokens with different meanings** (white matching both a static white and a background token, say), do not pick — present the difference in meaning and let the user choose
- Show grade 2 with what binding changes — a near colour, or **the same colour at another opacity, which is an opacity change** ("the 20% shadow becomes opaque", in the two values it has) — and ask about each such row on its own. A row the person wants goes into the draft mapping as it is; the dry run in step 3 shows, node by node, what it would change
- Grade 3 is reported only; the user decides whether to proceed
- The draft mapping is `MAPPING = [{ hex, variableKey }]`, an entry per row chosen, its `variableKey` from that row's `tokens` and its hex written as the scan wrote it — no `accept` yet

### 3. Bind (dry run → preview → go → run the dry run's `mapping`)

1. **Dry run the draft.** Run `token-bind.js` with `const MAPPING = [...];`, `const DRY_RUN = true;`, and `SECTION` where a section was given. `DRY_RUN` is required, `true` or `false`: left out, or anything else — `"true"`, `1` — it throws before the file is read, so a forgotten line never turns into a write. Nothing in the file changes — no node, no paint, and no import: a dry run never imports a token. It returns:
   - `paints` — `[{ node, name, kind, hex, candidates }]`, one row per paint the mapping names that is not left alone — a colour left alone (inside an instance, scaffolding, through a style) is only in `skipped`. `candidates` are the entries tried on it, in the order the bind will try them, up to the first that binds: `[{ variableKey, accept?, variable?, status, reason?, change? }]`, `accept: true` where the entry is an accepted one, `status` being `bind`, `skip` (its `reason` says why) or `unchecked` — a library token not in the file yet (nobody here has bound it), whose scopes and value on the node cannot be read without importing it
   - `wouldBind` — `[{ node, name, kind, hex, variable, variableKey, change? }]`, one row per paint settled to bind: a `bind` candidate and no `unchecked` one
   - `skipped` — what the real run would return (step 4) for the colours left alone, the paints settled not to bind, and a token that could not be read on a settled paint
   - `unchecked` — `[{ variableKey, nodes }]`, each token not in the file yet and the nodes it is tried on
   - `mapping` — the MAPPING to run after the go (step 4)

   A `skip` that carries `change` is a visible difference the person can accept on that node: a near colour (`#3B66FF → #3366FF`), another opacity (`opacity 20% → 100%`), or a token that renders something else in the mode the node is set to (`#FFFFFF → #1E1E1E (mode Dark)`) — a grade-1 colour included, since the grade was read in the default mode
2. **Ask about each visible change, node by node** — every `skip` candidate with a `change` on a paint not in `wouldBind` (for a paint settled not to bind, the same rows are in `skipped`). For the nodes the person accepts, add an entry `{ hex, variableKey, accept: true, nodes: [those ids] }` right after the plain entry whose change it lifts — no `paints`: the dry run in step 3 fills them in. **`accept: true` means the person saw that change on those nodes and said go to it**, so it always names them — the script rejects an `accept` without `nodes` before anything is written, and a go never covers a node its preview did not list
3. **Dry run the final mapping, and build the preview from it** — the page or section; each hex → token with its count; every `wouldBind` row that carries a `change`, listed node by node with what changes there; every paint with an `unchecked` candidate, node by node in its `candidates` order: each token not in the file yet, wherever it falls in that order, and what follows where it does not fit the property or would change the colour — the next candidate's outcome, or that the paint is left and reported where none is left to try; and what stays as it is (`skipped` by reason, colours inside instances, grade 2 and 3 rows not chosen). Get a **go**
4. **Run that dry run's `mapping` with the same `SECTION` and `const DRY_RUN = false;`.** `mapping` is the MAPPING just previewed with `nodes` on every entry — plain ones too — set to the node ids the dry run listed under it, and on each accepted entry `paints` — `[{ node, prop, index }]`, the paints the dry run listed it for; an entry that listed none is left out, and an empty `mapping` has nothing to bind. Because every entry names its nodes, a node the preview did not show — a frame drawn since the dry run, say — is neither bound nor reported; because an accepted entry names its paints, its change lands on no other paint. So the run binds only nodes that preview listed, each to a token listed for that node, and makes no visible change the preview did not show on that paint: where a token cannot be imported, the paint goes on to the next token listed for its node, and binds only where the colour stays the same or with the accepted change the preview showed there. It returns `{ bound, changed, skipped }` — `bound` in paints; `changed` as `[{ node, name, kind, hex, variable, variableKey, change }]`, every paint it bound with a visible change, an accepted one; `skipped` as `[{ node, reason, change?, variableKey? }]`, one row per node and reason: inside an instance, scaffolding, applied through a style or text with part of it in one, a visible change not accepted on that node (with its `change` and `variableKey`), a token not scoped for that property, a token that could not be imported — that one even where a later token binds that paint. A paint no token could bind has a row for every token it tried. A section that is not on the page, an `accept` without `nodes`, or an `accept` without `paints` — one not taken from a dry run's `mapping` — throws before anything is written

- With a lot to do, **split by section (`SECTION`) or by colour (part of `MAPPING`)** — never write it all at once. Each part is a run of its own, so it gets its own dry run and **its own preview and go**
- **The bind reads what the token renders on each node, in that node's mode**, which is why the preview is built from the dry run and not from the scan. Binding a mode node the person declined at first takes a new dry run with an `accept` entry naming exactly those nodes, then its own preview and go
- **An `unchecked` token is checked by the bind itself**: the real run imports it and, on each node it is tried on, reads its scopes and what it renders there. Where it fits and renders the same colour — or its entry is an accepted one listing that paint — it binds; otherwise that paint goes on to its next candidate, as the preview showed, and where it cannot be imported at all, `skipped` says so for every paint it was tried on and the paint goes on the same way; and a paint none of them binds comes back in `skipped`, a row for every token it tried, a visible change with its `change` and `variableKey`. Once the bind has bound the token somewhere on the page, a later dry run reads it and shows those changes as `skip` candidates, and accepting them follows the usual dry run, preview and go. Where the bind bound it nowhere, the token stays `unchecked` in a dry run; the preview for accepting those nodes then shows the `change` each one carried in that run's `skipped`, and the real run after that go names each change it made in `changed`

### 4. Verify (required)

- **Run `audit-tokens.js` again in its default mode** on the same scope and confirm no mapped colour is left as `[unbound]`, except on the nodes `skipped` named and any drawn since the dry run, which its `mapping` did not name
- `bound` equals the number of `wouldBind` rows in the dry run that was previewed, less those whose token could not be imported and that no later token bound, plus however many of its `paints` rows with an `unchecked` candidate bound. Only a `wouldBind` row is subtracted: a paint whose candidates were unchecked was never counted, so one that bound nothing — its token failed to import, say — takes nothing away. Each paint that did not bind is in `skipped`, a row for every token it tried, and every import failure on a paint that tried the token is there too. The real run follows the previewed `mapping` over the same paints, so any other gap is a fault to report, not a rounding to explain
- Every row in `changed` is a change the person said go to on that paint: one the previewed dry run showed, or, for a token that was `unchecked` there, the change an earlier real run's `skipped` showed. Report them as what changed on screen
- Report `skipped` by reason, `inInstance`, and the grade 2 and 3 rows not chosen, as out of scope for this pass

## Constraints

- **Dry run → preview → go before writing.** Settling the mapping and running the binding are separate; binding is split by section or by colour, each run behind its own dry run, preview and go, and the real run takes the `mapping` the previewed dry run returned, unchanged
- **Never touch colors inside instances or scaffolding, or a paint applied through a style** — report only
- Only bind where the property and the token's scope agree — the bind script holds to it and returns the rest in `skipped`
- Any mapping that changes the colour or the opacity says so in the preview, node by node, and carries `accept: true` — with exactly the `nodes` the preview listed — only after the person said go to that change. Never assume the color is unchanged from the token's name
- Keep each call small, verifying between steps with the audit or a screenshot
- Never write "done" without verification — prove zero remaining with the audit

## Notes

- The primary evidence for a mapping is always **what value this file actually renders that token as** (the scan's dictionary). Never infer from how a token's name sounds
- "Lots of unbound colors" does not automatically mean somebody forgot — off-palette colors may simply have found their way in, so grades 2 and 3 go back to design judgement
- A mass of hardcoded colors inside instances is not this skill's scope; raise it separately as **a component library repair task**
