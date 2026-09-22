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
 *   MODE="compare" : compare the working page against STAT → return violations + undecidable
 *
 * What to prepend
 *   const CFG  = {...};                      resolve-config.py --js
 *   const MODE = "collect";                  or "compare"
 *   const PAGE = "<part of the page name>";
 *   const STAT = {...};                      compare mode only. The collect result as it is
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

const page = figma.root.children.find(p => p.name.indexOf(PAGE) !== -1);
if (!page) return `page not found: ${PAGE}`;
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
for (const s of page.children.filter(c => c.type === "SECTION")) {
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
        issues.push(`[default] ${f.name} / ${n.name === cname ? cname : n.name + "(" + cname + ")"}` +
                    ` ${propName(k)}=${p[k].value} (convention ${norm}, samples ${tot})`);
      }
    }
  }
}
// unknown is undecidable rather than a violation — a signal that more reference pages are needed
return {
  component: issues.length ? issues : "COMPONENT PASS",
  unknown: Object.keys(unknown).map(k => k + " x" + unknown[k])
};
