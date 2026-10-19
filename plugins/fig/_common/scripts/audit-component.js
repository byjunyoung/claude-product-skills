/* =============================================================================
 * audit-component.js — component default residue audit (read-only, zero writes)
 *
 * A duplicated instance carries the component's defaults with it. A display toggle that is on
 * in the library stays on even where that screen does not use it, rendering an empty slot.
 * It is invisible in a zoomed-out screenshot and keeps escaping eye inspection — only measurement catches it.
 *
 * The basis is not a rules document but **how that same file actually uses the component**.
 * A property whose value also varies across production screens is a per-use choice, not a violation, and is not reported.
 *
 * Two stages. setCurrentPageAsync runs once per call, so a different page means a different call.
 *   MODE="collect" : gather the boolean property distribution per component from a reference page → return STAT
 *   MODE="compare" : compare the working page against STAT → return { pass, findings }; each finding
 *                    is { tag, grade, node, msg }. A property the collect pass never saw is listed
 *                    in a separate `unknown: string[]` — undecidable, not a violation, never part of `pass`.
 *
 * What to prepend
 *   const CFG  = {...};                      resolve-config.py --js
 *   const MODE = "collect";                  or "compare"
 *   const PAGE = "<part of the page name>";
 *   const STAT = {...};                      compare mode only. The collect result as it is
 *   const SECTION = "<section node id>";     compare mode only, optional. Audit that section and the
 *                                            sections nested in it, nothing else. Not on the page: one
 *                                            blocking [section] finding. Inside a section that
 *                                            pages.exclude_sections excludes: pass with a `note`.
 *                                            Collect mode ignores it; reference statistics come from reference pages.
 *
 * One reference page leaves components without enough samples. Where the target uses both forms and lists,
 * take one reference of each and sum the STATs. What is still missing is undecidable, not a violation.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const CA = C.component_audit || {};
const MIN_N = CA.min_samples != null ? CA.min_samples : 5;
const DOMINANCE = CA.dominance != null ? CA.dominance : 0.9;
const BODY = CA.body_offset || { left: 0, top: 0 };
const LABEL = (C.naming || {}).label_prefix || "[label] ";
const PATTERN_PAGE = (C.naming || {}).pattern_page_pattern;

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
const page = figma.root.children.find(p => p.name.indexOf(PAGE) !== -1);
if (!page) throw new Error(`page not found: ${PAGE}`);
await figma.setCurrentPageAsync(page);

// An instance is keyed by its master's name, not its own.
// Instances are often renamed, and keying on that drops them from the convention comparison entirely.
async function masterName(n) {
  const m = await n.getMainComponentAsync();
  if (!m) return n.name;
  return m.parent && m.parent.type === "COMPONENT_SET" ? m.parent.name : m.name;
}
const boolKeys = p => Object.keys(p).filter(k => typeof p[k].value === "boolean");
const propName = k => k.split("#")[0];        // property ids differ per file, so only the name is used

if (MODE === "collect") {
  const stat = {};
  for (const n of page.findAll(x => x.type === "INSTANCE" && x.componentProperties)) {
    const p = n.componentProperties, keys = boolKeys(p);
    if (!keys.length) continue;
    const cname = await masterName(n);
    for (const k of keys) {
      const key = cname + "|" + propName(k);
      stat[key] = stat[key] || { t: 0, f: 0 };
      p[k].value ? stat[key].t++ : stat[key].f++;
    }
  }
  return stat;
}

// compare — the shared shell (side nav, top bar) is the same instance on every screen, so it is not a target.
// Only the content area is examined.
//
// A pattern page has no shell. Its frames are compositions a few hundred pixels wide, so every
// instance on one sits inside the offset meant to skip a nav column, and the whole page reads as
// nothing to check — measured on a live file, where the page came back PASS having examined zero
// instances. The offset is therefore dropped on a page matching naming.pattern_page_pattern.
const S = typeof STAT !== "undefined" ? STAT : {};
const isPatternPage = !!(PATTERN_PAGE && new RegExp(PATTERN_PAGE).test(page.name));
const issues = [], unknown = {};
// Without SECTION nothing is excluded here (as before); with it, the exclusion decides the note.
const exclude = (C.pages || {}).exclude_sections;
const EXCL = exclude && exclude.length ? new RegExp(exclude.join("|")) : null;
const walked = sectionsDeep(page.children, SEC ? s => !!(EXCL && EXCL.test(s.name)) : () => false);
const scope = SEC ? scopeOf(walked) : null;
const add = (tag, grade, node, msg) => ({ tag, grade, node, msg });
if (scope && scope.missing) return { pass: false, findings: [add("[section]", "blocking", null, `section ${SEC} is not on this page`)], unknown: [] };
if (scope && scope.excluded) return { pass: true, findings: [], note: `section ${SEC} is excluded by pages.exclude_sections; nothing audited`, unknown: [] };
for (const { s } of walked.filter(d => !SEC || (scope.ids.has(d.s.id) && !d.skipped))) {
  for (const f of s.children.filter(c => c.type === "FRAME" && !c.name.startsWith(LABEL))) {
    const fb = f.absoluteBoundingBox;
    if (!fb) continue;
    for (const n of f.findAll(x => x.type === "INSTANCE" && x.componentProperties)) {
      const b = n.absoluteBoundingBox;
      if (!b) continue;
      if (!isPatternPage && (b.x - fb.x < BODY.left || b.y - fb.y < BODY.top)) continue;
      const p = n.componentProperties, keys = boolKeys(p);
      if (!keys.length) continue;
      const cname = await masterName(n);
      for (const k of keys) {
        const key = cname + "|" + propName(k);
        const st = S[key];
        if (!st) { unknown[key] = (unknown[key] || 0) + 1; continue; }
        const tot = st.t + st.f;
        if (tot < MIN_N) continue;
        const norm = st.t / tot >= DOMINANCE ? true : (st.f / tot >= DOMINANCE ? false : null);
        if (norm === null || p[k].value === norm) continue;   // a split convention is a per-use choice
        issues.push({ tag: "[default]", grade: "blocking", node: n.id == null ? null : n.id,
                      msg: `${f.name} / ${n.name === cname ? cname : n.name + "(" + cname + ")"}` +
                           ` ${propName(k)}=${p[k].value} (convention ${norm}, samples ${tot})` });
      }
    }
  }
}
// unknown is undecidable rather than a violation — a signal that more reference pages are needed
// It stays out of `findings`, so `pass` means what it always did: no violation found.
return { pass: issues.length === 0, findings: issues, unknown: Object.keys(unknown).map(k => k + " x" + unknown[k]) };
