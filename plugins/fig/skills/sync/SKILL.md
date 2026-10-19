---
name: sync
description: Audits whether changes finished on working and update pages made it into the canonical page, applies what did not and archives the working copies, each step behind its own preview and go, after a release or whenever working pages have piled up. Triggers - "/fig:sync", "find what never made it into canonical", "bring the canonical page current", "정본 반영 안 된 것 찾아줘", "운영 페이지 최신화", "교체 안 된 화면 찾아줘".
allowed-tools: AskUserQuestion, Bash, Read, Write, Edit, Skill, mcp__plugin_figma_figma__use_figma, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot, mcp__plugin_figma_figma__whoami, mcp__claude-in-chrome__list_connected_browsers, mcp__claude-in-chrome__select_browser, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__tabs_close_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__find
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

- Looking at what changed between two versions of a design → Dev Mode's *Compare changes* in Figma — it needs a Dev Mode seat, and compares a frame with its own version history, not two separate frames
- Naming and section tidying, stubbing placeholders → `/fig:prep`
- Checking for violations only → `/fig:lint`
- Flow arrows → `/fig:arrows`
- Applying to frontend code → `/fig:code`
- Just understanding the file structure → `/fig:read`

## Where the rules come from — the config file (same source as fig:prep and fig:lint)

The rules are set by **`figma-conventions.yaml`**, read through `resolve-config.py --js <fileKey>`.

Sections read: `pages` (the three axes, excluded sections) · `sync` (diff length limit, version pages) · `naming` (`frame_pattern`, the file's frame rule that names are matched by).

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
6. **Record the confirmed convention in `files.<fileKey>`** (the label and the three axes) — behind a preview, not silently. The preview names the file it writes and the layer: the person's own `~/.claude/figma-conventions.yaml` or the project's `./figma-conventions.yaml`. Ask which. If the person's own config is a symlink into a shared team repository, say so plainly: writing there changes it for everyone who uses that repository. The preview shows the exact `files.<fileKey>` block being added, as it will appear in the file:

   ```yaml
   files:
     "<fileKey>":
       label: "<file name>"
       pages:
         canonical: { match: name,    pattern: '<pattern>' }
         archive:   { match: name,    pattern: '<pattern>' }
         queue:     { match: divider, pattern: '<divider label>' }
   ```

   Write only after a go, and write it with `Edit` as an in-place edit — the new key under an existing `files:` (or a `files:` added at the end), never a whole-file rewrite, because the config may be a symlink into a shared team repository and every other line in it belongs to somebody else. Only where the chosen file does not exist yet is it created, with `Write`, holding that block alone. On a no, carry the axes for this run only. The next run starts at point 1. If the page list stops matching the convention, confirm again

### Step 2 — audit (zero writes, three-signal judgement)

Check each piece of work in the archive and queue against canonical.

**Frame names settle nothing.** The working copy and canonical keep the same frame names — it is the same screen — so a name comparison always says "match". You have to look at the content.

**Signal 1 — text diff (the main one)**

Compare each finished working frame directly with the canonical frame of the same name — the `[screen]-[state]` name `/fig:prep` normalises: take the text set of each and difference them. Identical text means applied, as far as this signal goes; the bucket table below adds what signals 2 and 3 must say. Any difference is shown as it stands, never summarised, and **which side a string sits on decides what it means**:

- A string only in the working frame → it **must be present** on the canonical page to count as applied. Missing there, the frame is **Not applied**
- A string only in the canonical frame → it may be what this work removed or reworded, or what canonical gained from other work since, and the file cannot tell which. A frame whose only differences are of this kind goes under **Needs checking**, labelled "may be later work"
- Both kinds in one frame → **Not applied** for its working-only strings, with its canonical-only strings listed beside them as "may be later work — confirm". Step 3 removes none of them without that confirmation
- **Names are matched by the file's own frame rule, `naming.frame_pattern`.** A working frame that passes it and has no canonical twin is reported as "new — not on the canonical page", with its whole text as candidates. It counts as **Not applied**
- A working frame whose name fails `naming.frame_pattern` (renamed, never prepped) is not called new: it is reported as "unmatched by name — asked", and the person is pointed at `/fig:prep` to normalise names first. This outcome exists only where a pattern is set
- Where `naming.frame_pattern` is `null`, the file has no frame rule: frames are matched by exact name alone, none is reported as unmatched for its shape, and a name with no canonical twin is new
- A name that appears more than once on the canonical page cannot be matched to one frame: every match is listed and the working frame goes under **Needs checking**. Sections matching `pages.exclude_sections` are skipped on both pages, so a reference copy kept in an excluded section does not make a screen ambiguous
- A canonical frame with no working twin is not audited. A whole frame removed from the working page is invisible to this signal

**Signal 2 — frame height**

Changes that add or remove elements change the height. A matching height is the second condition of applied. Where the text is identical and the heights differ, something without text was added or removed on one side, and the file cannot say which side moved — the frame goes under **Needs checking**, never Not applied. Where the text already differs, the height only supports what signal 1 found.

**Signal 3 — component master**

Component-level changes (a state added, hierarchy tidied) do not show up in frame text. Get the master id from a canonical frame's instance via `getMainComponentAsync()` and compare it with the working copy's instance. **Referencing the same master means it is already merged** — if the master lives on the canonical page, editing the working copy *is* updating canonical. The same masters are the third condition of applied. Where the text and the height match and a master differs, which side moved is again unknown — canonical may have moved to a newer component since — so the frame goes under **Needs checking**, with both masters named.

**The result has exactly three buckets**

| Bucket | Basis |
|---|---|
| Applied | All three agree: identical text (signal 1), matching heights (signal 2) and the same component masters (signal 3) |
| Not applied | A working-only string is missing from canonical, or the working frame is new (no canonical twin) — in a frame with both kinds of difference, its canonical-only strings ride along as "may be later work — confirm" |
| Needs checking | Only canonical-only strings differ ("may be later work"); the name repeats on the canonical page; or the text is identical and signal 2 or signal 3 differs, so which side moved cannot be told |

**Not detected by any signal:** a visual-only change — a colour, a font, a position — inside the same height, with the same components and the same text, is graded Applied. The report says so in plain words every run, and Step 4's archive preview repeats it.

**Never decide the needs-checking cases.** Collect them, report them, and ask whether to run a screenshot comparison — it costs per item, so it does not run automatically. Where the person answers that canonical-only text is this work's own removal, the frame goes on to Step 3; where it is later work on canonical, the frame is left as it is.

### Step 3 — apply (structure comparison decides the method)

Only the not-applied cases, and needs-checking ones the person has since confirmed as this work's. For each one, **compare the structure first.**

List the text nodes of the canonical frame and the working frame in document order as `parent name|characters` and compare.

- **Order, count, and parent names all match** → only the values differ. **Edit the values.** Node ids survive, so external deep links hold. Count the intended edits in advance and put a guard in the script that aborts when the count differs from expected
- **Anything differs** → the structure changed. **Move the frame** as the convention prescribes, and note in the report that external links pointing at the old canonical frame id will break (see the deep link audit)

Value edits are text edits, so **read the target node's current fonts with `getStyledTextSegments(['fontName'])` and load them** before writing. Never assume a default font.

**Preview → go.** State the target frames, what will change and how many, the method (value edit or move), and the reasoning. **List every canonical-only string the apply would remove, each labelled "may be later work — confirm"** — for frames from archive pages and queue pages alike, since both are judged against the same canonical page. Nothing is removed silently: where the person does not confirm a string, it stays, and the frame it sits in is left out of this apply and reported under needs checking. With several pieces, split them and pass a gate per piece.

Right after applying, run the same comparison again and confirm the result matches the working frame.

### Step 4 — archive

Move working pages whose changes are now in canonical into the archive.

**Preview → go** before the first move: the pages, the archive page and section each goes to, and the sentence from the report, repeated — *a visual-only change inside the same height, with the same components and the same text, is not detected by any signal*, so a page graded applied can still carry one. Archiving is where such a change would stop being looked at.

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
  may be later work — confirm: the canonical-only strings, and which the person confirmed

[unmatched by name — asked]
· name — fails naming.frame_pattern; run /fig:prep to normalise names first

[needs checking]
· name — why: canonical-only text (may be later work) · name repeats on canonical
  · identical text with a different height or component master — and whether a screenshot comparison is needed

[not detected by any signal]
· a visual-only change inside the same height, with the same components and the same text, is graded applied

[archived]
· working page → archive location, whether deleted

[handoff]
· version saved: {title}   (or: off — sync.named_version)
```

If nothing was un-applied, report just that, briefly, with the not-detected line.

## Implementation snippets

**Name-matched text comparison (one whole archive page)**

```js
const N = CFG.naming || {}, P = CFG.pages || {};
const NAME_RE = N.frame_pattern ? new RegExp(N.frame_pattern) : null;   // null: match by exact name, never "unmatched"
const EXCLUDE = P.exclude_sections && P.exclude_sections.length ? new RegExp(P.exclude_sections.join('|')) : null;
const LATER = 'may be later work — confirm';
const texts = n => [...new Set(n.findAll(x => x.type === 'TEXT').map(t => t.characters.trim()).filter(s => s && s.length < CFG.sync.text_diff_max_len))];
async function masters(n) {   // signal 3: every instance's component master, as one sorted key
  const ids = new Set();
  for (const i of n.findAll(x => x.type === 'INSTANCE')) { const m = await i.getMainComponentAsync(); if (m) ids.add(m.id); }
  return [...ids].sort().join(',');
}
function frames(n, acc) {   // dig through the section hierarchy, collect screen frames only; excluded sections are skipped on both pages
  for (const c of n.children || []) {
    if (c.type === 'FRAME') acc.push(c);
    else if (c.type === 'SECTION' && !(EXCLUDE && EXCLUDE.test(c.name))) frames(c, acc);
  }
  return acc;
}
const canonPage = await figma.getNodeByIdAsync(CANON_PAGE_ID);   // the canonical page, from the confirmed axes
await figma.setCurrentPageAsync(canonPage);
const canon = {};   // frame name -> every canonical frame carrying it (a repeated name is kept, not overwritten)
for (const f of frames(canonPage, []))
  (canon[f.name] = canon[f.name] || []).push({ id: f.id, set: new Set(texts(f)), height: Math.round(f.height), masters: await masters(f) });
const page = await figma.getNodeByIdAsync(PAGE_ID);   // the working or archive page being judged
await figma.setCurrentPageAsync(page);
const out = [];
for (const f of frames(page, [])) {
  if (NAME_RE && !NAME_RE.test(f.name)) { out.push({ frame: f.name, mode: 'unmatched', note: 'unmatched by name — asked (fails naming.frame_pattern; run /fig:prep to normalise names first)' }); continue; }
  const W = new Set(texts(f)), C = canon[f.name];
  if (!C) { out.push({ frame: f.name, mode: 'new', bucket: 'not applied', note: 'new — not on the canonical page', all: [...W].slice(0, 70) }); continue; }
  if (C.length > 1) { out.push({ frame: f.name, mode: 'ambiguous', bucket: 'needs checking', canonicalIds: C.map(c => c.id) }); continue; }
  const c = C[0];
  const onlyWorking = [...W].filter(x => !c.set.has(x));     // must reach canonical
  const onlyCanonical = [...c.set].filter(x => !W.has(x));   // may be later work on canonical: never removed without a confirm
  const height = { working: Math.round(f.height), canonical: c.height };
  const sameMasters = (await masters(f)) === c.masters;
  let bucket, why;
  if (onlyWorking.length) [bucket, why] = ['not applied', 'working-only text missing from canonical'];
  else if (onlyCanonical.length) [bucket, why] = ['needs checking', 'only canonical-only text differs — may be later work'];
  else if (height.working !== height.canonical) [bucket, why] = ['needs checking', 'identical text, height differs (signal 2)'];
  else if (!sameMasters) [bucket, why] = ['needs checking', 'identical text, component master differs (signal 3)'];
  else [bucket, why] = ['applied', 'text, height and component masters all agree'];
  out.push({ frame: f.name, mode: onlyWorking.length || onlyCanonical.length ? 'differs' : 'identical', bucket, why,
    onlyWorking, onlyCanonical, ...(onlyCanonical.length ? { confirm: LATER } : {}), height, sameMasters });
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
| Canonical gained text from other work after this work was made | Text only canonical has is graded needs checking ("may be later work"), never not applied, and step 3's preview lists any string an apply would remove for a confirm |
| A visual-only change inside the same height, components and text | No signal detects it and it is graded applied. Say so in the report and in the archive preview |
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
- Never "improve" canonical in a direction the working frame does not have. Applying means matching the working frame, and stopping there — except that a canonical-only string goes only once the person has confirmed it in step 3's preview
