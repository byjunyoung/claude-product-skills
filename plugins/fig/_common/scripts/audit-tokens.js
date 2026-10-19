/* =============================================================================
 * audit-tokens.js — colours left off the design system's tokens (read-only, zero writes)
 *
 * Checks: [unbound] — a SOLID fill, stroke or effect colour on an editable node that is not bound to
 *         a colour variable.
 *
 * Usage — the same as audit-struct.js: the CFG line, any optional input lines, then this file, to use_figma.
 *
 * Inputs
 *   CFG      naming.arrow_delimiter / label_prefix / state_chain_prefix and placeholder_style (the
 *            <scaffolding> block), pages.exclude_sections, design_system.match_threshold_channel
 *   SECTION  optional — that section and the sections nested in it, as in audit-struct.js
 *   MODE     optional — "audit" (the default, what /fig:lint runs) or "collect" (what /fig:tokens scans with)
 *
 * The dictionary — what this file's tokens look like. Every colour variable bound anywhere on the page
 * (inside instances, excluded sections and scaffolding too, and the whole page even under SECTION: a
 * binding there is evidence of a token, not something to report), plus the file's local colour
 * variables. Each is resolved in its collection's default mode, following aliases. Where a variable's
 * own value cannot be read (a library collection the sandbox does not return), the colour its bound
 * paints show stands in. One with neither is left out and counted in `note`. A library token nobody in
 * this file has bound yet cannot be seen from a script at all.
 *
 * Colours are compared with their alpha, written "#RRGGBB" where alpha is 1 and "#RRGGBBAA" otherwise —
 * in findings, as the dictionary's keys and as each unbound entry's `hex`. A paint's alpha is its
 * opacity, an effect's its colour's `a`, a variable's its resolved value's `a`. Grades, per unbound colour:
 *   1  colour and alpha both match a dictionary entry                    → blocking
 *   2  every colour channel within design_system.match_threshold_channel  → warning
 *      of the nearest entry, alpha aside — the same colour at another opacity is near, never exact.
 *      null makes the threshold 0, so only that case is near
 *   3  neither                                                           → warning
 *
 * Not reported: anything inside an instance, including overrides on its layers, and an instance's own
 * paint unless the instance overrides that property (its `overrides` entry for itself lists fills,
 * strokes or effects) — otherwise the paint is the component's and is reported there. Also: working
 * scaffolding (the <scaffolding> block), sections excluded by pages.exclude_sections, hidden nodes and
 * everything under them, non-SOLID paints (gradient, image, video), text with several fills
 * (figma.mixed), paints and effects switched off, paints already bound to a variable, and a property
 * applied through a style (its fillStyleId / strokeStyleId / effectStyleId is a non-empty string).
 * Which paints those rules leave is the <paint-scope> block, shared byte for byte with token-bind.js,
 * so the bind touches exactly the paints this file reports.
 *
 * Returns
 *   audit    { pass, findings, note? } — one [unbound] finding per node and colour, the section named in
 *            msg. A dictionary left empty → { pass: true, findings: [], note }: the check is skipped,
 *            never run against nothing. The note says whether no colour variable was found at all or
 *            some were found and none resolved.
 *   collect  { dictionary: { [hex]: variableKey[] }, unbound: [{ hex, count, nodes, grade, nearest }],
 *              inInstance: [{ hex, count }], note? }
 *            count is paints, nodes the distinct node ids; nearest is the matching entry (grade 1), the
 *            closest one within the threshold (grade 2), or null (grade 3). inInstance counts the colours
 *            inside instances, including overrides on its layers — every layer inside one, and an
 *            instance's own paint on a property it does not override — none of which is bound here.
 *            Both lists are sorted by count, then hex.
 *   SECTION not on the page → audit: one blocking [section] finding; collect: throws.
 *   SECTION inside an excluded section → a `note` saying nothing was audited, and no findings.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const P = C.pages || {}, DS = C.design_system || {};
const MODE_ = typeof MODE !== "undefined" && MODE ? String(MODE) : "audit";
if (MODE_ !== "audit" && MODE_ !== "collect") throw new Error(`MODE is "audit" or "collect", not "${MODE_}"`);
const COLLECT = MODE_ === "collect";

const anyOf = a => (a && a.length ? new RegExp(a.join("|")) : null);
const SEC_EXCLUDE = anyOf(P.exclude_sections);
const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));
// Left out → the bundled default; null → 0, so only the same colour at another opacity grades 2.
const TH = DS.match_threshold_channel === undefined ? 8 : Number(DS.match_threshold_channel) || 0;

// <sections-deep>
// Every SECTION at any depth with its absolute origin. A section's children carry x/y relative to
// it and nested sections compose, so a loop over page.children alone never reaches a frame that
// sits one section deeper. `skipped` is inherited: a section inside an excluded one is excluded.
const sectionsDeep = (nodes, skip, ox = 0, oy = 0, inherited = false) => {
  const out = [];
  for (const s of nodes) {
    if (s.type !== "SECTION") continue;
    const ax = ox + s.x, ay = oy + s.y, skipped = inherited || !!skip(s);
    out.push({ s, ax, ay, skipped }, ...sectionsDeep(s.children, skip, ax, ay, skipped));
  }
  return out;
};
// </sections-deep>

// <scaffolding>
// Working scaffolding: what /fig:arrows, /fig:prep and Figma itself draw around a design. None of it is
// design, so none of it is tokenized or bound. Read by every script that walks colours, the same way:
// top down, asking both questions of each node.
//   scaffoldRoot(n, S)   true → leave n and everything under it: an arrow (its name holds
//                        naming.arrow_delimiter), a state chain (naming.state_chain_prefix), a label pill
//                        (naming.label_prefix) with its text, a placeholder frame (painted with
//                        placeholder_style's fill and stroke, and dashed where that style dashes) with its
//                        caption. A text layer is never one: Figma names text after what it says.
//   ownPaintsExempt(n)   true → leave n's own paints, still walk its children: a SECTION, whatever it is
//                        painted (section_style is how /fig:prep paints one, and any section is page
//                        organization, never built), and a COMPONENT_SET, whose dashed border Figma draws.
// S = scaffoldingCfg(CFG), resolved once. hexOf(c) turns an RGB(A) colour into "#RRGGBB".
const hexOf = c => "#" + [c.r, c.g, c.b].map(x => Math.round(x * 255).toString(16).padStart(2, "0")).join("").toUpperCase();
const scaffoldingCfg = cfg => {
  const nm = (cfg && cfg.naming) || {}, ps = (cfg && cfg.placeholder_style) || {};
  const up = h => (h ? ("#" + String(h).replace(/^#/, "")).toUpperCase() : null);
  return {
    arrow: (nm.arrow_delimiter || " --> ").trim(),
    label: nm.label_prefix || "[label] ",
    state: nm.state_chain_prefix || "[state] ",
    phFill: up(ps.fill), phStroke: up(ps.stroke), phDashed: !!(ps.dash && ps.dash.length),
  };
};
const scaffoldRoot = (n, S) => {
  const name = n.name || "";
  if (n.type !== "TEXT" && (name.includes(S.arrow) || name.startsWith(S.label) || name.startsWith(S.state))) return true;
  if (n.type !== "FRAME" || !(S.phFill || S.phStroke)) return false;
  const painted = (arr, h) => !h || (Array.isArray(arr) && arr.some(p => p && p.type === "SOLID" && hexOf(p.color) === h));
  return painted(n.fills, S.phFill) && painted(n.strokes, S.phStroke) && (!S.phDashed || !!(n.dashPattern && n.dashPattern.length));
};
const ownPaintsExempt = n => n.type === "SECTION" || n.type === "COMPONENT_SET";
// </scaffolding>

// <paint-scope>
// Which colours are the design's own: the ones the audit reports and the bind may touch. Read by every
// script that reads or binds colours, the same way, so the bind never touches a paint the audit leaves
// alone — binding a paint applied through a style would detach it from the style. Uses <scaffolding>.
//   colourKey(c, alpha)   "#RRGGBB" where alpha is 1, "#RRGGBBAA" otherwise
//   coloursOf(n)          n's SOLID fills and strokes and its effect colours, as { prop, i, kind, key, on,
//                         varId, styled }. prop and i place it in n[prop]; key is the colour with its alpha
//                         (a paint's opacity, an effect colour's a); on is false for one switched off; varId
//                         is the variable it is bound to, or null; styled is true where the property comes
//                         from a style, its style id a non-empty string (figma.mixed is not one). A text
//                         node's figma.mixed fills, gradients, images and videos are not returned.
//   walkColours(n, S, take, pass?)
//                         top down from n, S = scaffoldingCfg(CFG). A hidden node is left with everything
//                         under it, a section is left to rootsOf, and a section's or component set's own
//                         paint is never read. take(node, colour) gets each colour switched on, unbound and
//                         the node's own: not through a style, not in scaffolding, nothing inside an
//                         instance, and an instance's own paint only on a property its overrides entry for
//                         itself lists. pass(node, colour, why), where given, gets the other colours switched
//                         on and unbound, why being "style", "instance" or "scaffolding"; without it, an
//                         instance's insides and scaffolding are not read at all.
//   rootsOf(page, all, ids)
//                         what to walk, as { n, where }: the children of every section neither excluded nor
//                         hidden nor nested in a hidden one (all = sectionsDeep's output), only those in ids
//                         where SECTION narrowed it, and the nodes loose on the page where it did not.
const colourKey = (c, alpha) => {
  const a = Math.round((alpha == null ? 1 : alpha) * 255);
  return hexOf(c) + (a === 255 ? "" : a.toString(16).padStart(2, "0").toUpperCase());
};
const styledBy = id => typeof id === "string" && id !== "";
const coloursOf = n => {
  const out = [];
  for (const prop of ["fills", "strokes"]) {
    const arr = n[prop];
    if (!Array.isArray(arr)) continue;
    const styled = styledBy(n[prop === "fills" ? "fillStyleId" : "strokeStyleId"]);
    arr.forEach((p, i) => {
      if (p && p.type === "SOLID" && p.color)
        out.push({ prop, i, kind: prop === "strokes" ? "stroke" : n.type === "TEXT" ? "text" : "fill", key: colourKey(p.color, p.opacity),
                   on: p.visible !== false, styled, varId: p.boundVariables && p.boundVariables.color ? p.boundVariables.color.id : null });
    });
  }
  if (Array.isArray(n.effects)) {
    const styled = styledBy(n.effectStyleId);
    n.effects.forEach((e, i) => {
      if (e && e.color)
        out.push({ prop: "effects", i, kind: "effect", key: colourKey(e.color, e.color.a), on: e.visible !== false, styled,
                   varId: e.boundVariables && e.boundVariables.color ? e.boundVariables.color.id : null });
    });
  }
  return out;
};
const overridden = n => {
  const o = Array.isArray(n.overrides) ? n.overrides.find(x => x && x.id === n.id) : null;
  return new Set(o && Array.isArray(o.overriddenFields) ? o.overriddenFields : []);
};
const walkColours = (n, S, take, pass, ctx = null) => {
  if (n.visible === false || n.type === "SECTION") return;
  if (!ctx && scaffoldRoot(n, S)) ctx = "scaffolding";
  if (ctx && !pass) return;
  if (!ownPaintsExempt(n)) {
    const mine = !ctx && n.type === "INSTANCE" ? overridden(n) : null;
    for (const c of coloursOf(n)) {
      if (!c.on || c.varId) continue;
      const why = c.styled ? "style" : ctx || (mine && !mine.has(c.prop) ? "instance" : null);
      if (!why) take(n, c);
      else if (pass) pass(n, c, why);
    }
  }
  const inner = ctx || (n.type === "INSTANCE" ? "instance" : null);
  if (!n.children || (inner && !pass)) return;
  for (const ch of n.children) walkColours(ch, S, take, pass, inner);
};
const rootsOf = (page, all, ids) => {
  const hidden = new Set(), hide = s => { hidden.add(s.id); for (const c of s.children) if (c.type === "SECTION") hide(c); };
  for (const { s } of all) if (s.visible === false) hide(s);
  const out = [];
  for (const { s, skipped } of all)
    if (!skipped && !hidden.has(s.id) && (!ids || ids.has(s.id))) for (const n of s.children) out.push({ n, where: s.name });
  if (!ids) for (const n of page.children) out.push({ n, where: null });
  return out;
};
// </paint-scope>

const issues = [];
const add = (tag, grade, node, msg) => issues.push({ tag, grade, node: node == null ? null : node, msg });
// <scope-of>
// SECTION narrows an audit to one section and every section nested in it. Given the walk's output,
// scopeOf returns { ids } (the in-scope section ids), { missing: true } or { excluded: true };
// each caller words its own finding or note.
const SEC = typeof SECTION !== "undefined" && SECTION ? String(SECTION) : null;
const scopeOf = all => {
  const t = all.find(d => d.s.id === SEC);
  if (!t) return { missing: true };
  if (t.skipped) return { excluded: true };
  const ids = new Set(), take = n => { ids.add(n.id); for (const c of n.children) if (c.type === "SECTION") take(c); };
  take(t.s);
  return { ids };
};
// </scope-of>
const page = figma.currentPage;
const allSecs = sectionsDeep(page.children, skipSection);
const scope = SEC ? scopeOf(allSecs) : null;
// Before anything else: a mistyped section must not come back as "no tokens, skipped".
if (scope && scope.missing) {
  if (COLLECT) throw new Error(`section ${SEC} is not on this page`);
  add("[section]", "blocking", null, `section ${SEC} is not on this page`);
  return { pass: false, findings: issues };
}

// ── The dictionary: colour key → the keys of the colour variables that resolve to it ──
// `seenAs` keeps, per bound variable, the colours its paints show. That is the evidence that stands in
// where the variable's own value cannot be read — a library collection the sandbox does not return.
const seenAs = new Map();
const gather = n => {
  for (const c of coloursOf(n))
    if (c.varId) { if (!seenAs.has(c.varId)) seenAs.set(c.varId, new Set()); seenAs.get(c.varId).add(c.key); }
  if (n.children) for (const ch of n.children) gather(ch);
};
for (const n of page.children) gather(n);

const varCache = new Map(), colCache = new Map();
const getVar = async id => {
  if (!varCache.has(id)) varCache.set(id, await figma.variables.getVariableByIdAsync(id));
  return varCache.get(id);
};
const getCol = async id => {
  if (!colCache.has(id)) colCache.set(id, await figma.variables.getVariableCollectionByIdAsync(id));
  return colCache.get(id);
};
// The value in the collection's default mode, alpha included; an alias is followed into its own
// collection's default mode.
const resolveKey = async (v, seen = new Set()) => {
  if (!v || v.resolvedType !== "COLOR" || seen.has(v.id)) return null;
  seen.add(v.id);
  const col = await getCol(v.variableCollectionId);
  const val = col && v.valuesByMode ? v.valuesByMode[col.defaultModeId] : null;
  if (!val) return null;
  if (val.type === "VARIABLE_ALIAS") return resolveKey(await getVar(val.id), seen);
  return typeof val.r === "number" ? colourKey(val, val.a) : null;
};

const candidates = new Map();
for (const id of seenAs.keys()) candidates.set(id, await getVar(id));
for (const v of await figma.variables.getLocalVariablesAsync("COLOR")) candidates.set(v.id, v);
const dictionary = {};
const put = (k, varKey) => (dictionary[k] = dictionary[k] || []).push(varKey);
let found = 0, unresolved = 0;
for (const [id, v] of candidates) {
  if (v && v.resolvedType !== "COLOR") continue;
  found++;
  const k = await resolveKey(v);
  if (k) { put(k, v.key); continue; }
  if (v && seenAs.has(id)) { for (const seen of seenAs.get(id)) put(seen, v.key); continue; }
  unresolved++;
}
for (const k of Object.keys(dictionary)) dictionary[k] = [...new Set(dictionary[k])].sort();
const dictKeys = Object.keys(dictionary);

const notes = [];
if (unresolved)
  notes.push(unresolved === 1
    ? "1 colour variable could not be resolved to a colour and was left out of the dictionary"
    : `${unresolved} colour variables could not be resolved to a colour and were left out of the dictionary`);
const withNote = (o, extra) => {
  const all = extra ? [extra, ...notes] : notes;
  return all.length ? { ...o, note: all.join("; ") } : o;
};

if (scope && scope.excluded) {
  const why = `section ${SEC} is excluded by pages.exclude_sections; nothing audited`;
  return COLLECT ? withNote({ dictionary, unbound: [], inInstance: [] }, why) : withNote({ pass: true, findings: [] }, why);
}
if (!dictKeys.length && !COLLECT)
  return { pass: true, findings: [], note: found
    ? `${found} colour variable${found === 1 ? "" : "s"} found, none could be resolved; [unbound] skipped`
    : "no colour tokens found in this file; [unbound] skipped" };

// ── Grade: 1 colour and alpha both agree, 2 every colour channel within the threshold (alpha may
// differ, so the same colour at another opacity is near, never exact), 3 neither ──
const channels = k => [1, 3, 5, 7].map(i => (i < k.length ? parseInt(k.slice(i, i + 2), 16) : 255));
const gradeOf = k => {
  if (dictionary[k]) return { grade: 1, nearest: k, d: 0, da: 0 };
  const a = channels(k);
  let best = null, bd = Infinity, bda = Infinity;
  for (const t of dictKeys) {
    const b = channels(t), d = Math.max(...[0, 1, 2].map(i => Math.abs(a[i] - b[i]))), da = Math.abs(a[3] - b[3]);
    if (d < bd || (d === bd && (da < bda || (da === bda && t < best)))) { bd = d; bda = da; best = t; }
  }
  return best !== null && bd <= TH ? { grade: 2, nearest: best, d: bd, da: bda } : { grade: 3, nearest: null, d: bd };
};

// ── Scan the editable nodes in scope — the <paint-scope> walk ──
// Sections come from the walk above, every depth. Collect also counts what an instance holds and does
// not override, so /fig:tokens can report it apart.
const S = scaffoldingCfg(C);
const hits = [], inInst = new Map();   // hits: { n, where, kind, key }
const held = COLLECT ? (n, c, why) => { if (why === "instance") inInst.set(c.key, (inInst.get(c.key) || 0) + 1); } : null;
for (const { n, where } of rootsOf(page, allSecs, scope ? scope.ids : null))
  walkColours(n, S, (m, c) => hits.push({ n: m, where, kind: c.kind, key: c.key }), held);

if (COLLECT) {
  const byCount = (x, y) => y.count - x.count || (x.hex < y.hex ? -1 : x.hex > y.hex ? 1 : 0);
  const agg = new Map();
  for (const h of hits) {
    if (!agg.has(h.key)) agg.set(h.key, { count: 0, nodes: new Set() });
    const a = agg.get(h.key);
    a.count++; a.nodes.add(h.n.id);
  }
  const unbound = [...agg].map(([hex, a]) => {
    const g = gradeOf(hex);
    return { hex, count: a.count, nodes: [...a.nodes], grade: g.grade, nearest: g.nearest };
  }).sort(byCount);
  const inInstance = [...inInst].map(([hex, count]) => ({ hex, count })).sort(byCount);
  return withNote({ dictionary, unbound, inInstance }, dictKeys.length || found ? null : "no colour tokens found in this file");
}

// One finding per node and colour: the kinds it is used for on that node are named together.
const groups = new Map();
for (const h of hits) {
  const k = h.n.id + "|" + h.key;
  if (!groups.has(k)) groups.set(k, { n: h.n, where: h.where, key: h.key, kinds: [] });
  const g = groups.get(k);
  if (!g.kinds.includes(h.kind)) g.kinds.push(h.kind);
}
for (const g of groups.values()) {
  const r = gradeOf(g.key), loc = g.where ? `${g.where} / ${g.n.name}` : g.n.name, what = `${g.kinds.join(", ")} ${g.key}`;
  const pct = Math.round(r.da / 255 * 100), alpha = r.da ? `, opacity off by ${pct ? pct + "%" : "<1%"}` : "";
  if (r.grade === 1) add("[unbound]", "blocking", g.n.id, `${loc}: ${what} — an exact token for this colour exists and was not used`);
  else add("[unbound]", "warning", g.n.id, r.grade === 2
    ? `${loc}: ${what} — near a token (${r.nearest}, ${r.d} off per channel${alpha}); a designer decides whether to snap it`
    : `${loc}: ${what} — no token within ${TH} per channel; a designer decides whether it needs one`);
}

return withNote({ pass: issues.length === 0, findings: issues });
