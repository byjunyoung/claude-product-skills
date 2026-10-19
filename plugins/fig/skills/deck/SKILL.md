---
name: deck
description: Turns a document, a dataset, or a spoken brief into a Figma Slides deck. Reads the source, agrees an outline before writing anything, then builds slides from the team template's archetypes and audits overlap and wording before handing back. It also measures the team template into local assets the first time, or after the template is revised. Triggers - "/fig:deck", "make this into a deck", "turn this doc into slides", "extract the slide template", "set up the deck assets", "슬라이드로 만들어줘", "발표 자료 만들어줘", "덱 만들어줘", "덱 템플릿 뽑아줘", "템플릿 다시 추출".
allowed-tools: Read, Write, Bash, AskUserQuestion, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__create_new_file, mcp__plugin_figma_figma__upload_assets, mcp__plugin_figma_figma__get_screenshot, mcp__plugin_figma_figma__whoami
---

# deck — building a presentation deck (Figma Slides)

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install fig@byjunyoung`), rather than improvising what the scripts do.

Moves one source into a presentation flow and builds a deck in **a Figma Slides file**. The slide count follows the source's volume and the presentation conditions (it is not fixed).

The design comes from the local assets in `deck.assets_dir` — `template-spec.md` (values and the archetype catalog) and `template.js` (palette, constants, builders). It does not re-read a remote template on every run; it Reads these two.

**Never build by inventing values** — an invented slide leaves the type scale without exception. When the assets are missing, or the template was revised, step 0 measures them first.

## Triggers

- Natural language: "turn this into slides", "presentation material", "make a deck", "this doc as slides"
- Explicit: `/fig:deck <source>` (a document link, a file path, a topic)

## Procedure

The shape — **prepare** (assets / 0) → **align** (intent and source / 1–2) → **design** (agree the outline / 3) → **build** (assets and build / 4–5) → **audit** (structure and wording / 6–7) → **output** (8)

### 0. Check the template assets

Look in `deck.assets_dir` for `template-spec.md` and `template.js`. If either is missing, or the person says the team template was revised, read `setup.md` (beside this file) and run it before anything else — it measures the template into those files, and its Figma writes (the mirror file, the verification builds) each wait for their own preview and go. When the request was only to measure the template (no source given), stop after `setup.md`'s report. Otherwise, once the assets are there — or when both files were there and nothing was revised — go on to step 1.

### 1. Confirm the intent

Do not ask everything at once; start with what actually branches. These three are usually enough.

- **The source** — which document or dataset is being moved. Take a link or a path
- **The occasion** — in front of whom, for how long. The presentation length decides the slide count (10 minutes is around 12 slides; 30 minutes carries 25 or more comfortably)
- **The form** — a standalone deck, or a section of an existing one

**Match the density to the source first.** Compress a long report into a short deck and "this feels thin" comes back. Where the source has several tables, lists, and findings, work out first whether each is worth a slide of its own; if a condensed version is what is wanted, confirm with the user what gets dropped.

### 2. Read the source

- Read the source in full. Never build an outline from a summary or a table of contents — what carries a presentation is the numbers, the quotations, and the photographs in the body
- A large document's fetch result lands in a file. Image URLs swamp the body, so substitute them out before reading
- Where the body has drawings or photographs worth using, pull them into a list. Presigned S3 URLs for document images download with `curl` without authentication (they expire quickly, so fetch them immediately)
- Never invent a fact in the deck that the source does not have. Where evidence is needed, go back through the source

### 3. Agree the outline (the gate before writing)

**Agree the composition as a table before building any slides.** Changing the structure after everything is built costs a rearrangement and a re-extraction.

What the table holds: slide number / title / what it carries / which archetype. Whether to follow the source's structure or rearrange it into a presentation flow is settled here too.

- Work the slide count back from the presentation length
- Where four or more slides of the same character run consecutively, put a section transition or a differently shaped slide between them
- For an item with no image, decide here whether it becomes a diagram, a table, or a figure rather than leaving an empty card
- **How closely to follow the template is settled here too.** An archetype is a per-slide rule and the template is a menu rather than a deck, so the more of it you draw on, the more the title positions and content tops scatter. Offer two routes to choose from — ⓐ use the archetypes' own coordinates but hold the title family to one ⓑ go back to the archetypes entirely. Either way the principle is **never to invent a coordinate** (pitfalls 24 and 25)

The file gets created after the "go".

### 4. Prepare the assets

Images go up to Figma to get an imageHash, which is handed to the builder.

1. Collect them into a working folder with ASCII filenames (`pickup-worktop.png` style)
2. Strip the macOS quarantine: `xattr -d com.apple.quarantine <file>`
3. **Measure the original aspect ratio** — `sips -g pixelWidth -g pixelHeight`. Matching the image box to that ratio is what keeps `FIT` from leaving margins (pitfall 6)
4. A scratch folder can be emptied between sessions. Re-collect from the source when it is needed again
5. **Do not trust filenames — open all of them.** A file called `fig10_bakery-display` turned out to be a photograph of a closed-for-business notice. A name is the intent at the moment of shooting, not the content of the photograph. **Confirm a candidate by eye before it goes on a slide** — opening 27 images one at a time costs nothing but tokens, so build a single contact sheet with headless Chrome and look at them at once.
6. **Sweep the source exhaustively for drawings it already has.** A chart drawn for the report and never carried into the deck is a common find. List the whole folder and pick what to use; when comparing several, make a single contact sheet and look at them at once — opening photographs one by one only costs tokens
7. **A report's drawings cannot be used as they are.** Caption paragraphs, footnotes that only work in a document, and the source's section numbers are baked into the image. Crop those out before it goes on a slide. Cropping changes the ratio, so recompute the box size

### 5. Build

The order is **create the file → apply the team template (the user does this) → lay out with archetypes**.

1. **Load the skills** — pass `figma-use` and `figma-use-slides` together in `skillNames`
2. **Read the local assets** — `template-spec.md` and `template.js` from `deck.assets_dir`. They attach to the top of the build script in this order:
   `${CLAUDE_PLUGIN_ROOT}/_common/scripts/deck-base.js` **→** `template.js`.
   Generic helpers first, team constants and builders second (helpers are declarations and hoist; constants are read at call time).
   **Pick from the spec's archetype catalog first.** Where nothing fits the shape of the content, do not improvise a layout — cut the content to the nearest archetype, or split the slide. An invented layout always leaves the type scale
3. **A new file** — check the planKey and the seat with `whoami`. A plan listed with `seat: View` cannot take the `use_figma` writes the build is made of, so a file created there could not be built; stop and say so rather than trying. Then `create_new_file` (editorType `slides`)
4. **MCP cannot apply the team template.** Once the file exists, ask the user to apply the team's shared template from the Templates panel, and wait. Applying it is what brings in the team fonts, colours, and named text styles. Without it, everything breaks into substitute fonts and 'Pick a style'
5. **Confirm what applying it did** — it can pull in the sample slides wholesale. Take one of them as the theme reference (`REF_SLIDE`) and `clone` it to make new slides, then **delete the samples once the build is done**
6. **Upload the images** — get hashes with `upload_assets`. Uploading leaves frames on the page, so clear them along with everything else after the build
7. **Three to five slides per call.** A slide is an isolated subtree, so batched building is safe
8. **Reordering** — a new slide attaches at the end of the row. Repeating `row.appendChild(slide)` in final order sorts them (safer than computing insertChild indices)
9. **Bind the text styles** — after the build, bind each TEXT to the file's named styles by `family|style|size`. Sizes outside the scale and SemiBold staying raw is normal

### 6. Structural verification

Check each batch with a read-only script. Passing saves screenshots.

- **How many distinct values** — count opacity values, accent colours, and font sizes exhaustively and look at how many kinds there are. Secondary-text opacity is one value; accent colours only where meaning is attached (pitfalls 41 and 42)
- **Orphan lines** — count lines holding a single word, and lines under 25% of the width. Exclude short complete sentences (pitfall 39)
- **Order** — put the source's contents and the deck's slide numbers side by side and look for reversals and omissions. Skipping a parent section and coming back to it is the most common mistake
- **Item counts** — compare the number of items the source covers against the number of slots on the slide. Check them against a figure written on an earlier slide ("7 stores") too. A layout truncating content is caught by this check alone
- **The skeleton** — sweep the whole deck at once and count ⓐ how many title positions there are ⓑ how many content-top y values ⓒ whether any slide breaks the margins. Look at the **provenance** of the values, not their **count** — is every value that turned up a number that exists in `template-spec.md`? One value not in the template means it was invented on the spot. Where the families were held to one, check that promise too
- **Out of bounds** — nodes outside the slide frame (Figma Slides' fixed 1920×1080) in slide coordinates. Check the margin bounds the spec states for left and right alongside
- **Automatic wrapping** — per block, check whether `height / (fontSize × lineHeight)` exceeds `characters.split('\n').length`. Larger means the typesetter is breaking in mid-word (pitfalls 31, 33, 34)
- **Empty cards** — slides where the gap between the card's bottom and the content's bottom is over 100px. Shrink the card to the content and level the heights within a row
- **Alignment** — text whose `textAlignHorizontal` is not LEFT. Any CENTER left outside diagram labels and pull quotes is a node carried over from another family
- **Body contrast** — a template's dimmed colour is usually **for secondary text**. Actually compute the effective contrast against the background and see whether it merely scrapes the WCAG AA floor (4.5:1). If it only scrapes it, use it for subtitles, captions, and sources alone and **keep reading body copy opaque**. Check too that the body colour does not split into two across the deck
- **Line height** — body copy is **1.5×** the font size (WCAG 1.4.12). A template line height tighter than that means it was set for one- or two-line captions and is not enough for a paragraph. Blocks of three lines or more get around 8px of paragraph spacing too
- **The type scale** — slides carrying a `fontSize` outside the spec's scale. Even one means that slide has too much content
- **Surface colour** — more than one card surface colour in a deck is a failure. Use the spec's single card colour
- **Density** — over 40 nodes per slide. A transplanted table trips this immediately
- **Screenshot checkpoints** — the first batch (the visual system) and the last (overall quality). Walk these one at a time
  - [ ] Does the image read large inside its box, without excessive margin above and below
  - [ ] Does the card look empty at the bottom (a fixed height larger than the content makes an empty box)
  - [ ] Does a title already inside the image duplicate the slide title
  - [ ] Do the table's columns encroach on each other
  - [ ] Did the intended font actually apply

### 7. Wording audit (the last gate, particular to decks)

Correct structure with wrong sentences still means rebuilding. Slides carry many short sentences, so the following pile up especially fast. **Dump the whole deck's text and sweep it in one pass.**

- **Do not join sentences with a middle dot.** `did A · did B` becomes two sentences. Keep the tight dot inside compounds and short lists of equals
- **Cut parenthetical dashes.** `there are rules — 20 seconds, 120 seconds` → break it into sentences or change the word order. A dash separating a table's labels can stay
- **Do not use words that point at a position in the deck.** "as covered on the previous slide", "see the next slide" become false the moment a slide moves once. After a rearrangement, sweep with a regex for previous/next/earlier slide and check nothing is left. Where a pointer is genuinely needed, point by name rather than by position ("the robots were covered separately")
- **Do not carry over identifiers that only work inside the source document.** Section numbers, stage codes, and ticket numbers become names and figures. The audience is not listening with the source open
- **Remove parenthetical insertions.** Definitions, conditions, and dates get written out as sentences rather than wedged into parentheses
- **Unify proper nouns.** Where one thing appears under two names (a short form and a full form), settle on one
- **Fix translationese and passive voice.** The "with respect to", "by way of", "was observed to be", "is being permitted" family
- **Recount the figures.** Compare the count in a title against the actual row count, and the same figure on an earlier slide against a later one
- **Cut overstatement.** Replace it with the evidence figure, or delete it
- **Break lines at the boundaries of meaning.** Never mid-word; between subject and predicate, or at a clause boundary, is fine. `the bakery display and the chilled showcase ⏎ form the browsing path` is correct; `from entering the store and receiving a drink ⏎ to leaving` splits one unit.
  **Do not settle on "one sentence per line."** Fix that and you start cutting sentences to fit the column width, and the source's writing disappears wholesale.
  **Roughly level the line counts against the neighbouring column** — one column full of fragments makes that column look misaligned.
  The automatic check: per text, `rendered line count > manual newline count` means automatic wrapping happened. Only touch it then.
- **Insert manual line breaks wherever CJK text breaks mid-syllable-cluster.** In a narrow column the typesetter cuts mid-word, because CJK has no spaces to break at. The automatic check catches all of it — per text, `rendered line count > manual newline count` means automatic wrapping happened.
  When the lines will not level, do not just add breaks — shorten the sentence. A line on a slide is supposed to be short

Finer points of style follow whatever writing standard applies where it is being written. Without one, the items above already filter most of it.

### 8. Output

- The deliverable is the Figma deck URL. Hand it over with a summary of the slide composition
- Speaker notes get filled in only on request
- A re-run edits the existing slides. It does not delete and rebuild (only when the user says "from scratch")

## Archetypes

The builders live in `template.js` in `deck.assets_dir`. Do not improvise a new layout; use what is there and pass variations as parameters. Below are the standard names the measuring step (`setup.md`) produces — where the template has no such form, that builder does not exist either.

| Builder | Use |
|---|---|
| `titleSlide` | Cover — the official background image full-bleed, plus title and subtitle |
| `sectionSlide` | Part transition — one large sentence |
| `cardGridSlide` | N cards of a label plus a key statement |
| `autoCardSlide` | A tall card with a status badge, a title, and evidence lines (auto-layout) |
| `imageDescSlide` | N cards of real screens or photographs |
| `metricsSlide` | Numeric results — a large figure, the metric name, a description |
| `timelineSlide` | Milestones and roadmaps |
| `closingSlide` | Closing — the background rotated 180° plus a footer |
| `statusBadge` | A status chip — done, planned, undecided, by colour |
| `phoneMock` | An app-screen phone mock-up — bezel plus screen |
| `nameSection` | Naming a slide row (section) |
| `applyTextStyles` | Binding named text styles after the build |

**The cover and closing backgrounds use the official assets as they are.** Upload the background images from `template-assets/` and pass them as `bgImageHash`. Where a wordmark, a phrase, or a motif is baked into the image, do not reproduce it with shapes — a reproduction always ends up wrong. Templates commonly have the closing slide reuse the same background flipped.

**Image fit defaults to `FIT`.** On a UI screenshot, a cropped header, tab, or button takes the message with it. `FILL` is for photographs and backgrounds, where cropping is fine. A tall app screen goes in `phoneMock`; a wide one goes in a box.

**Where the source is a narrative report, the list above is not enough.** Two frequent derivatives get assembled by hand.

- **A findings slide** — a photograph or chart on the left, a subheading and an evidence list on the right. Size the photograph's box to the original ratio, and make the right side a vertical auto-layout frame
- **A table slide** — hold the column x coordinates in an array and put a 1px rule under each row. Distinguish status and character values by colour. Up to about 12 rows fits on one slide

An item with no screen becomes a diagram rather than an empty card. A chain (A→B→C), a contrast (two boxes, system and customer), and a 2×2 of cards cover most of it.

## Pitfalls

The numbered list is in `pitfalls.md` beside this file. Open it before the build (step 5) and the structural verification (step 6); pitfall numbers cited in this file refer to it.

## Related

- No template assets, or stale ones → `setup.md`, via step 0
- The numbered pitfalls are in `pitfalls.md`
- Design values and the archetype catalog are in `template-spec.md` in `deck.assets_dir`, the builders in `template.js`, the generic helpers in `${CLAUDE_PLUGIN_ROOT}/_common/scripts/deck-base.js`
- Where a recurring deck needs its own data collection, finish that collection upstream and hand it to this skill as the source
