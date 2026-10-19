/* =============================================================================
 * sync-compare.js — /fig:sync's name-matched text comparison for one whole page
 *
 * Inputs (globals the caller prepends, after the CFG line):
 *   PAGE_ID        the working or archive page being judged
 *   CANON_PAGE_ID  the canonical page, from the confirmed axes
 * Returns one entry per working frame: bucket, onlyWorking, onlyCanonical, heights, sameMasters,
 * masters. Read-only.
 * ========================================================================== */

const N = CFG.naming || {}, P = CFG.pages || {};
const NAME_RE = N.frame_pattern ? new RegExp(N.frame_pattern) : null;   // null: match by exact name, never "unmatched"
const EXCLUDE = P.exclude_sections && P.exclude_sections.length ? new RegExp(P.exclude_sections.join('|')) : null;
const LATER = 'may be later work — confirm';
// Every string is compared whatever its length; sync.text_diff_max_len only shortens how the report shows it
const texts = n => [...new Set(n.findAll(x => x.type === 'TEXT').map(t => t.characters.trim()).filter(Boolean))];
async function masters(n) {   // signal 3: every instance's component master, by id, with its name for the report
  const seen = new Map();
  for (const i of n.findAll(x => x.type === 'INSTANCE')) { const m = await i.getMainComponentAsync(); if (m) seen.set(m.id, `${m.name} (${m.id})`); }
  return seen;
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
  (canon[f.name] = canon[f.name] || []).push({ id: f.id, node: f, set: new Set(texts(f)), height: Math.round(f.height) });
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
  let bucket, why, sameMasters = null, differ = null;   // masters are read only where they decide: identical text, same height
  if (onlyWorking.length) [bucket, why] = ['not applied', 'working-only text missing from canonical'];
  else if (onlyCanonical.length) [bucket, why] = ['needs checking', 'only canonical-only text differs — may be later work'];
  else if (height.working !== height.canonical) [bucket, why] = ['needs checking', 'identical text, height differs (signal 2)'];
  else {
    const mw = await masters(f), mc = await masters(c.node);
    differ = { working: [...mw].filter(([id]) => !mc.has(id)).map(([, n]) => n), canonical: [...mc].filter(([id]) => !mw.has(id)).map(([, n]) => n) };
    sameMasters = !differ.working.length && !differ.canonical.length;
    [bucket, why] = sameMasters ? ['applied', 'text, height and component masters all agree']
                                : ['needs checking', 'identical text, component master differs (signal 3)'];
  }
  out.push({ frame: f.name, mode: onlyWorking.length || onlyCanonical.length ? 'differs' : 'identical', bucket, why,
    onlyWorking, onlyCanonical, ...(onlyCanonical.length ? { confirm: LATER } : {}), height, sameMasters,
    ...(sameMasters === false ? { masters: differ } : {}) });   // both sides' masters, named, where they differ
}
return out;
