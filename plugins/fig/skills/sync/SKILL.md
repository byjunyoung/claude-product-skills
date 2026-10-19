---
name: sync
description: Audits whether changes finished on working and update pages made it into the canonical page, applies what did not, then archives the working copies, each step behind its own preview and go gate. Triggers - "/fig:sync", "find what never made it into canonical", "bring the canonical page current", "정본 반영 안 된 것 찾아줘", "운영 페이지 최신화", "교체 안 된 화면 찾아줘".
allowed-tools: AskUserQuestion, Bash, Read, Write, Skill, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot, mcp__plugin_figma_figma__whoami, mcp__claude-in-chrome__list_connected_browsers, mcp__claude-in-chrome__select_browser, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__tabs_close_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__find
---

# fig:sync — bring canonical current (audit → apply → archive)

Checks every finished screen against the canonical page to see whether it actually landed there, applies what did not, then moves the working copies into the archive. This is the post-release procedure, executed instead of remembered.

The canonical page is supposed to be "what is running right now", but shipping and updating canonical happen at different moments. Left alone, the gap widens and engineering and QA start making decisions against an old screen. **That lag is the accident this skill prevents.**

**Prerequisites**: always load `figma:figma-use` before calling `use_figma`. Step 1 (audit) is **zero writes** — `use_figma` is used as a read-only script that only `return`s a report.

**Seat check before the first write** — call `whoami` once. Where every plan it lists carries `seat: View`, stop before step 3's first `use_figma` write and say so: the reading half of this skill runs on a View seat, the writing half needs an Edit seat on the file's plan, and no retry changes that. Where the seats are mixed, go ahead — and if the first write comes back as a permission error, report the seat table and stop rather than retrying.

## When to invoke

- "find what never made it into canonical", "bring the canonical page current", "check everything that wasn't replaced"
- Right after a release or a batch of shipped work, to bring canonical in line
- When working pages have piled up long enough that nobody knows what was applied
- As a periodic sweep — roughly monthly, to keep the lag from opening

## When NOT to invoke

- Looking at what changed between two versions of a design → Dev Mode's *Compare changes* in Figma
- Naming and section tidying, stubbing placeholders → `/fig:prep`
- Checking for violations only → `/fig:lint`
- Flow arrows → `/fig:arrows`
- Applying to frontend code → `/fig:code`
- Just understanding the file structure → `/fig:read`

## Where the rules come from — the config file (same source as fig:prep and fig:lint)

The rules are set by **`figma-conventions.yaml`**, read through `resolve-config.py --js <fileKey>`.

Sections read: `pages` (the three axes, excluded sections) · `sync` (diff length limit, version pages) · `naming`.

**There are two ways to apply a change, and a structure comparison decides which.** Moving the frame is the default, but when the layer composition is identical and only values differ, edit the values instead — node ids have to survive or the deep links in specs and tickets break. Step 3 executes that decision, and the report says which was used and why.

If the team keeps a written guide, point `guide_source` at it. It is not fetched on every run.

## Inputs

- `figma_url` (required): the target file URL. A specific page can be given, but the audit is file-wide by default
- `scope` (optional): to narrow the audit to a domain or a period

## Procedure

### Step 1 — settle the axes (never guess; record them per file)

Conventions differ per file. Some group by version, some by period, some split progress with divider pages (empty pages named `## title ##`).

1. **If `files.<fileKey>.pages` already has the three axes, use them.** Skip to step 2 of the procedure
2. Otherwise read **the page list and its order** from `figma.root.children`. The file-level response from `get_metadata` returns an incomplete page list, so it is not used
3. Infer the three axes, remembering there are two ways to match — **by name** (`match: name`) and **by the band beneath a divider** (`match: divider`)

   | Axis | What it is | Signals |
   |---|---|---|
   | canonical | The page everything is compared against | A production prefix, strictly tidied structure |
   | archive | Applied work, already tidied away | A version or period prefix, date or version section hierarchy |
   | queue | Shipped by engineering, not yet in canonical | A divider group label (done, deployed), individual working pages |

4. **Always sweep the groups split by dividers.** The pages in a band whose label means "done" are the un-applied candidates. Comparing only the archive pages found by name prefix misses real un-applied work — measured. This is exactly why the queue is usually not findable by name
5. **Confirm the inference once** — list N canonical, M archive, K queue pages and ask whether that is right
6. **Record the confirmed convention in `files.<fileKey>`** (the label and the three axes) — behind a preview, not silently. The preview names the file it writes and the layer: the person's own `~/.claude/figma-conventions.yaml` or the project's `./figma-conventions.yaml`. Ask which. If the person's own config is a symlink into a shared team repository, say so plainly: writing there changes it for everyone who uses that repository. Write only after a go; on a no, carry the axes for this run only. The next run starts at point 1. If the page list stops matching the convention, confirm again

### Step 2 — audit (zero writes, three-signal judgement)

Check each piece of work in the archive and queue against canonical.

**Frame names settle nothing.** The working copy and canonical keep the same frame names — it is the same screen — so a name comparison always says "match". You have to look at the content.

**Signal 1 — text diff (the main one)**

Compare each finished working frame directly with the canonical frame of the same `[screen]-[state]` name: take the text set of each and difference them. Identical text means applied. Any difference is shown as it stands, never summarised.

- A string only in the working frame → it **must be present** on the canonical page to count as applied
- A string only in the canonical frame → it **must be absent** once applied (this is what catches rewording and removals)
- A working frame named `[screen]-[state]` with no canonical twin is reported as "new — not on the canonical page", with its whole text as candidates. It counts as **Not applied**
- A working frame whose name does not follow `[screen]-[state]` (renamed, never prepped) is not called new: it is reported as "unmatched by name — asked", and the person is pointed at `/fig:prep` to normalise names first
- A `[screen]-[state]` name that appears more than once on the canonical page cannot be matched to one frame: every match is listed and the working frame goes under **Needs checking**
- A canonical frame with no working twin is not audited. A whole frame removed from the working page is invisible to this signal
- A difference is read as it stands. This signal does not infer which side changed — a canonical-only string can be something canonical gained after the work

**Signal 2 — frame height**

Changes that add or remove elements change the height. If the working frame's height matches the canonical frame's, that is evidence of applied; a height that differs is evidence of not applied (or of canonical having moved on since). Never decisive alone — it supports signal 1.

**Signal 3 — component master**

Component-level changes (a state added, hierarchy tidied) do not show up in frame text. Get the master id from a canonical frame's instance via `getMainComponentAsync()` and compare it with the working copy's instance. **Referencing the same master means it is already merged** — if the master lives on the canonical page, editing the working copy *is* updating canonical.

**The result has exactly three buckets**

| Bucket | Basis |
|---|---|
| Applied | At least one signal clearly supports it, with no signal against |
| Not applied | A working-frame-only string is missing from canonical, a canonical-only string is still there, or the working frame is new (no canonical twin) |
| Needs checking | All three signals are silent — a purely visual change where the two frames' text is identical and heights match |

**Never decide the needs-checking cases.** Collect them, report them, and ask whether to run a screenshot comparison — it costs per item, so it does not run automatically. A working frame edited after the release so that it now matches canonical lands here too, and says nothing about whether the work was applied.

### Step 3 — apply (structure comparison decides the method)

Only the not-applied cases. For each one, **compare the structure first.**

List the text nodes of the canonical frame and the working frame in document order as `parent name|characters` and compare.

- **Order, count, and parent names all match** → only the values differ. **Edit the values.** Node ids survive, so external deep links hold. Count the intended edits in advance and put a guard in the script that aborts when the count differs from expected
- **Anything differs** → the structure changed. **Move the frame** as the convention prescribes, and note in the report that external links pointing at the old canonical frame id will break (see the deep link audit)

Value edits are text edits, so **read the target node's current fonts with `getStyledTextSegments(['fontName'])` and load them** before writing. Never assume a default font.

**Preview → go.** State the target frames, what will change and how many, the method (value edit or move), and the reasoning. With several pieces, split them and pass a gate per piece.

Right after applying, run the same comparison again and confirm the result matches the working frame.

### Step 4 — archive

Move working pages whose changes are now in canonical into the archive.

1. **Confirm which archive page and which period (version) section they belong to.** Page id ranges hint at when the work happened, but the actual ship date is not in the file — ask rather than guess
2. **Read padding, spacing, and background style from an existing work section** in the archive and apply the same to the new one. Do not invent a style
3. Move the frames into the new section and place them at the conventional position
4. Delete the emptied working page **after confirming it has zero children**. Page deletion cannot be undone, so ask for it as **an independent gate**, never folded into another confirmation
5. If the archive pages have piled up, only name the candidates for moving into long-term storage — this skill does not rename or move archives itself

**When stretching a section, compute all four edges from real coordinates.** Sections on a page are not vertically ordered, so picking "the section below" by eye is wrong. There are cases that overlap vertically but not horizontally, so all four edges have to be checked.

### Step 5 — verify

- Call `/fig:lint` and confirm frame membership, bounds, and section overlap pass. Mandatory when clone or move was involved
- Confirm the moved frames have the same text node count as before the move
- Reference material kept in canonical but excluded from audits (size variants and the like) goes in a section matching `pages.exclude_sections`. Left in a normal section it reports as a missing state variant or a flow orphan

### Step 6 — name the version

Only after Step 5 passed, and only where `sync.named_version` is set — `null` saves none, and `null` is the default. Follow `${CLAUDE_PLUGIN_ROOT}/_common/version-pin.md` with `sync.named_version`, `{date}` and `{n}` (screens applied) filled in. This step shows no preview of its own, so it uses the procedure's steps 1–2 (preview → go) before the save, then reads it back by the exact title it saved.

Dev Mode status (*Completed*) is not set and not offered: `use_figma` cannot write it and nothing else here can either (removed in 3.26.0).

## Reporting

```
audited N  →  applied X · not applied Y · needs checking Z · unmatched by name — asked W

[not applied — handled]
· name (owner)
  before: what canonical looked like
  applied: what changed and how / method (value edit or move) and why

[unmatched by name — asked]
· name — not `[screen]-[state]`; run /fig:prep to normalise names first

[needs checking]
· name — which signals were silent, whether a screenshot comparison is needed

[archived]
· working page → archive location, whether deleted

[handoff]
· version saved: {title}   (or: off — sync.named_version)
```

If nothing was un-applied, report just that, briefly.

## Implementation snippets

**Name-matched text comparison (one whole archive page)**

```js
const texts = n => [...new Set(n.findAll(x => x.type === 'TEXT').map(t => t.characters.trim()).filter(s => s && s.length < CFG.sync.text_diff_max_len))];
function frames(n, acc) {   // dig through the section hierarchy, collect screen frames only
  for (const c of n.children || []) {
    if (c.type === 'FRAME') acc.push(c); else if (c.type === 'SECTION') frames(c, acc);
  }
  return acc;
}
const canonPage = await figma.getNodeByIdAsync(CANON_PAGE_ID);   // the canonical page, from the confirmed axes
await figma.setCurrentPageAsync(canonPage);
const canon = {};   // [screen]-[state] name -> every canonical frame carrying it (a repeated name is kept, not overwritten)
for (const f of frames(canonPage, [])) (canon[f.name] = canon[f.name] || []).push({ id: f.id, set: new Set(texts(f)) });
const page = await figma.getNodeByIdAsync(PAGE_ID);   // the working or archive page being judged
await figma.setCurrentPageAsync(page);
const out = [];
for (const f of frames(page, [])) {
  const W = new Set(texts(f)), C = canon[f.name];
  if (!/\S-\S/.test(f.name)) { out.push({ frame: f.name, mode: 'unmatched', note: 'unmatched by name — asked (run /fig:prep to normalise names first)' }); continue; }
  if (!C) { out.push({ frame: f.name, mode: 'new', bucket: 'not applied', note: 'new — not on the canonical page', all: [...W].slice(0, 70) }); continue; }
  if (C.length > 1) { out.push({ frame: f.name, mode: 'ambiguous', bucket: 'needs checking', canonicalIds: C.map(c => c.id) }); continue; }
  const onlyWorking = [...W].filter(x => !C[0].set.has(x)), onlyCanonical = [...C[0].set].filter(x => !W.has(x));
  out.push(onlyWorking.length || onlyCanonical.length
    ? { frame: f.name, mode: 'differs', bucket: 'not applied', onlyWorking, onlyCanonical }
    : { frame: f.name, mode: 'identical', bucket: 'applied' });
}
return out;
```

**Finding the keywords in canonical frames**

```js
const KW = [/* the strings from the comparison above */];
function tf(n, acc) {   // dig through the section hierarchy, collect screen frames only
  for (const c of n.children || []) {
    if (c.type === 'SECTION') tf(c, acc);
    else if (['FRAME','COMPONENT','INSTANCE'].includes(c.type) && !c.name.startsWith('[label]')) acc.push(c);
  }
  return acc;
}
const res = {};
for (const kw of KW) res[kw] = [];
for (const f of tf(figma.currentPage, [])) {
  const txt = f.findAll(x => x.type === 'TEXT').map(t => t.characters).join('');
  for (const kw of KW) if (txt.includes(kw)) res[kw].push(f.name);
}
return res;   // an empty array means that keyword is absent from canonical
```

**Structure comparison (can this be a value edit?)**

```js
// Run on each page separately and compare the results (one setCurrentPageAsync per script)
const f = await figma.getNodeByIdAsync(FRAME_ID);
return f.findAll(x => x.type === 'TEXT').map(t => `${t.parent.name}|${t.characters.replace(/\n/g,' ')}`);
// Same length, same order, same parent names on both sides → only values differ → value edit is safe
```

**Value edit (guard plus font loading)**

```js
const edits = [/* [textNode, newValue] pairs */];
if (edits.length !== EXPECTED) throw new Error(`aborted: expected ${EXPECTED}, got ${edits.length}`);
const fonts = new Set();
for (const [t] of edits) for (const s of t.getStyledTextSegments(['fontName'])) fonts.add(JSON.stringify(s.fontName));
for (const fs of fonts) await figma.loadFontAsync(JSON.parse(fs));
for (const [t, v] of edits) t.characters = v;
return { mutatedNodeIds: edits.map(([t]) => t.id) };
```

**Four-edge intersection check before stretching a section**

```js
const t = target.absoluteBoundingBox;
const T = { x: t.x, y: t.y, r: t.x + t.width, b: t.y + t.height };   // computed with the post-stretch values
return figma.currentPage.children.filter(c => c.type === 'SECTION' && c.id !== target.id)
  .map(s => { const b = s.absoluteBoundingBox;
    return { name: s.name, hit: b.x < T.r && b.x + b.width > T.x && b.y < T.b && b.y + b.height > T.y }; })
  .filter(s => s.hit);   // must be empty to be safe
```

## Traps

| Trap | What to do |
|---|---|
| Identical frame names make every name comparison say "match" | Judge on the three content signals. Names are only for pairing |
| Comparing archive pages and stopping there | The "done" band under a divider is where un-applied work actually hides — always include the `match: divider` axis |
| The working frame was edited after the release and now matches canonical | Classify it as needs checking and inspect canonical's structure directly |
| Replacing a whole frame breaks external deep links | When the structure matches, edit values only. If a move is unavoidable, report which links will break |
| A stretched section invades its neighbour | Compute the four-edge intersection with post-stretch coordinates. Do not check vertically alone |
| Mistaking a section child's coordinates for absolute | A section child's x/y are relative to the parent section |
| Editing text without loading the font | Read the node's current fonts and load them. Never assume a default |
| Putting reference material in a canonical section | Put it in a lint-excluded section to prevent false positives |
| Deleting an empty working page as part of another confirmation | Page deletion is its own gate. Confirm zero children first |

## Constraints

- Steps 1 and 2 are **zero writes** — no node changes during the audit
- Every write in steps 3 and 4 goes through **preview → go**. With several pieces, pass a gate per piece
- **Page deletion is an independent gate** — never folded into another confirmation
- Any judgement the config does not cover (value edit versus move) has its reasoning written into the report each time
- Archive pages are never renamed or moved by this skill — only named as candidates
- Never "improve" canonical in a direction the working frame does not have. Applying means matching the working frame, and stopping there
