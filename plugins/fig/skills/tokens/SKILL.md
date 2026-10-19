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

## When NOT to invoke

- Only finding the unbound colours → `/fig:lint` (its colour-token check reads and never writes)
- Frame naming and section tidying → `/fig:prep`
- Structure and flow rule violations → `/fig:lint`
- Flow arrows → `/fig:arrows`
- Creating the tokens (variables) themselves → `figma:figma-generate-library`
- Designing screens → `/fig:draw`

## Inputs

- `figma_url` (required): the page to bind
- `section` (optional): a section link or a section name, read the way `/fig:lint` reads it — that section and the sections nested in it. Omitted, the whole page. The scripts scope by page or section, so a link to a frame narrows to the section that holds it, and the preview says so

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

The dictionary holds variable keys. Names for the preview come from `search_design_system` by key; a key it does not return is shown as the key.

> **Caution — a token's real value may differ from the hex you were given.** "Change this grey to `fill/primary`" can still mean `fill/primary` is slightly different from that grey (which is fine if tokenizing is the goal). Whenever the color changes, **the preview must say "this token is #AAA, so the screen becomes #BBB".**

## Properties

fill · stroke · text color (a TEXT node's fills) · effect color (an effect's color) are all read and bound. Different properties take different token scopes — a background fill `FRAME_FILL`/`SHAPE_FILL`, a border `STROKE_COLOR`, text `TEXT_FILL`, an effect `EFFECT_COLOR`. **The bind script binds a colour only to a token whose scopes include its property** — never a text color to a border token — and returns the rest in `skipped`. One colour that needs a fill token on fills and a text token on text takes two mapping entries for the same hex; each paint takes the first that fits.

## Left alone (read for the report, never bound)

| Target | Why |
|---|---|
| Colours **inside a component instance**, and an instance's own paint on a property it does not override | They belong to the component — tokenize them on its source in the library. The instance's *own* override is in scope; its *children* are not |
| Paints applied through a style | Already on the design system; binding one would detach it from its style |
| Working scaffolding | Arrows, labels and state chains by the names in `naming` (`arrow_delimiter`, `label_prefix`, `state_chain_prefix`), placeholders by their `placeholder_style` paint, and a section's or component set's own paint — `/fig:arrows` and `/fig:prep` output, not design to tokenize |
| Sections in `pages.exclude_sections`, and hidden layers | Archives, templates, and the like; what nobody sees |

Excluded items that turn up are **reported, never fixed** — colours inside instances in particular are grouped separately as "a component repair issue".

## Grading — only auto-propose what is safe

The scan grades each unbound colour against the dictionary, colour and opacity together — the same grades `/fig:lint` reports.

| Grade | Basis | Handling |
|---|---|---|
| 1 — exact | Colour and opacity both equal a token's | Binding changes nothing you can see → **auto-propose the mapping** |
| 2 — near | Every colour channel within `design_system.match_threshold_channel` of the nearest token, opacity aside — so the same colour at another opacity is near, never exact | Binding changes the colour or the opacity → **show the change; the person decides** |
| 3 — none | Further from every token, or a brand or special colour | Binding not advised, report only |

The threshold is a baseline, not a verdict — for borderline colors, show the delta so the user can judge. `null` makes it 0, so only the same colour at another opacity is near.

## Procedure

Every step runs a script under `${CLAUDE_PLUGIN_ROOT}/_common/scripts/`, called the way `/fig:lint` calls its audits: the single `const CFG = {...};` line from `resolve-config.py --js <fileKey>`, the input lines below, then the whole file, handed to `use_figma` — with one `setCurrentPageAsync` line first where the page is not the first. The code is not copied into this document.

### 1. Scan (read-only)

Run `audit-tokens.js` with `const MODE = "collect";`, and `const SECTION = "<section id>";` where a section was given. It returns:

- `dictionary` — `{ hex: [variableKey, …] }`, each colour the file's tokens render and the tokens that render it
- `unbound` — `[{ hex, count, nodes, grade, nearest }]`, the directly editable colours on no token, one row per colour; `count` is paints, `nodes` the node ids, `nearest` the dictionary entry it was graded against
- `inInstance` — `[{ hex, count }]`, colours held inside instances, for the "component repair issue" line
- `note` — a dictionary left empty, or colour variables that could not be read; print it

A colour at full opacity is written `#RRGGBB` and any other `#RRGGBBAA`, in every field. A section that is not on the page makes the scan throw; ask which one was meant.

### 2. Settle the mapping (user's choice)

- Present grade 1 as a table: hex → token (name and key), count, a few nodes. **When one colour matches two tokens with different meanings equally** (white matching both a static white and a background token, say), do not pick — present the difference in meaning and let the user choose
- Show grade 2 with what binding changes. **A row that differs only in opacity is an opacity change** — "the 20% shadow becomes opaque", in the two values it has — and is asked about on its own. Only a row the person accepts goes into the mapping with `acceptAlpha: true`
- Grade 3 is reported only; the user decides whether to proceed
- The settled mapping is `MAPPING = [{ hex, variableKey, acceptAlpha? }]`, with each hex written as the scan wrote it

### 3. Bind (preview → go, split into steps)

- Show the settled mapping as a **preview** — the page or section, each hex → token with its count, every change in colour or opacity, and what stays as it is (colours inside instances, grade 2 and 3 rows not chosen) — and get a **go**
- With a lot to do, **split by section (`SECTION`) or by colour (part of `MAPPING`)** — never write it all at once
- Run `token-bind.js` with `const MAPPING = [...];`, and `SECTION` where the preview named one. It binds the colours the scan reported whose colour and opacity equal a mapped hex, and returns `{ bound, skipped }`: `bound` in paints, and `skipped` as `[{ node, reason }]` — inside an instance, scaffolding, applied through a style, an opacity the token does not share without `acceptAlpha`, a token not scoped for that property, a token that could not be imported. A section that is not on the page throws before anything is written

### 4. Verify (required)

- **Run `audit-tokens.js` again in its default mode** on the same scope and confirm no mapped colour is left as `[unbound]`, except on the nodes `skipped` named
- Where `skipped` names no token problem (opacity, scope, import), `bound` equals the sum of the mapped rows' `count` from the scan — both scripts walk the same paints, so a gap is a fault to report, not a rounding to explain
- Report `skipped` by reason, `inInstance`, and the grade 2 and 3 rows not chosen, as out of scope for this pass

## Constraints

- **Preview → go before writing.** Settling the mapping and running the binding are separate; binding is split by section or by colour
- **Never touch colors inside instances or scaffolding, or a paint applied through a style** — report only
- Only bind where the property and the token's scope agree — the bind script holds to it and returns the rest in `skipped`
- Any mapping that changes the colour or the opacity says so in the preview — never assume the color is unchanged from the token's name
- Keep each call small, verifying between steps with the audit or a screenshot
- Never write "done" without verification — prove zero remaining with the audit

## Notes

- The primary evidence for a mapping is always **what value this file actually renders that token as** (the scan's dictionary). Never infer from how a token's name sounds
- "Lots of unbound colors" does not automatically mean somebody forgot — off-palette colors may simply have found their way in, so grades 2 and 3 go back to design judgement
- A mass of hardcoded colors inside instances is not this skill's scope; raise it separately as **a component library repair task**
