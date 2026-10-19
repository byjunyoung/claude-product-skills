/* =============================================================================
 * sync-ops.js — /fig:sync's apply-step helpers (preamble)
 *
 * Used like prep-ops.js: the config line, this file, then the actual calls. Only declarations here,
 * nothing runs on its own. Run the structure comparison on each page in its own call
 * (one setCurrentPageAsync per script).
 * ========================================================================== */

/** Finding the keywords in canonical frames. Returns { keyword: [frame names] }; an empty array
 *  means that keyword is absent from canonical. `root` is the page (or any node) to dig through. */
function tf(n, acc) {   // dig through the section hierarchy, collect screen frames only
  for (const c of n.children || []) {
    if (c.type === 'SECTION') tf(c, acc);
    else if (['FRAME','COMPONENT','INSTANCE'].includes(c.type) && !c.name.startsWith('[label]')) acc.push(c);
  }
  return acc;
}
function findKeywords(root, words) {
  const res = {};
  for (const kw of words) res[kw] = [];
  for (const f of tf(root, [])) {
    const txt = f.findAll(x => x.type === 'TEXT').map(t => t.characters).join('');
    for (const kw of words) if (txt.includes(kw)) res[kw].push(f.name);
  }
  return res;
}

/** Structure comparison (can this be a value edit?). The list is one entry per text, parent name
 *  first. Same length, same order, same parent names on both sides -> only values differ -> a value
 *  edit is safe. */
function structureOf(f) {
  return f.findAll(x => x.type === 'TEXT').map(t => `${t.parent.name}|${t.characters.replace(/\n/g,' ')}`);
}
function sameStructure(a, b) {
  const sa = structureOf(a).map(s => s.split('|')[0]), sb = structureOf(b).map(s => s.split('|')[0]);
  return sa.length === sb.length && sa.every((p, i) => p === sb[i]);
}

/** Value edit (guard plus font loading). editValues aborts before touching anything when the number
 *  of edits is not the one the audit settled on. */
async function editValue(t, v) {
  const fonts = new Set();
  for (const s of t.getStyledTextSegments(['fontName'])) fonts.add(JSON.stringify(s.fontName));
  for (const fs of fonts) await figma.loadFontAsync(JSON.parse(fs));
  t.characters = v;
  return t.id;
}
async function editValues(edits, EXPECTED) {   // edits: [textNode, newValue] pairs
  if (edits.length !== EXPECTED) throw new Error(`aborted: expected ${EXPECTED}, got ${edits.length}`);
  const fonts = new Set();
  for (const [t] of edits) for (const s of t.getStyledTextSegments(['fontName'])) fonts.add(JSON.stringify(s.fontName));
  for (const fs of fonts) await figma.loadFontAsync(JSON.parse(fs));
  for (const [t, v] of edits) t.characters = v;
  return { mutatedNodeIds: edits.map(([t]) => t.id) };
}

/** Four-edge intersection check before stretching a section. w and h are the post-stretch values;
 *  `clear` must be true to be safe, `hits` names the sections in the way. */
function fourEdgeClear(target, w, h) {
  const t = target.absoluteBoundingBox;
  const T = { x: t.x, y: t.y, r: t.x + w, b: t.y + h };   // computed with the post-stretch values
  const hits = figma.currentPage.children.filter(c => c.type === 'SECTION' && c.id !== target.id)
    .map(s => { const b = s.absoluteBoundingBox;
      return { name: s.name, hit: b.x < T.r && b.x + b.width > T.x && b.y < T.b && b.y + b.height > T.y }; })
    .filter(s => s.hit);
  return { clear: hits.length === 0, hits };
}
