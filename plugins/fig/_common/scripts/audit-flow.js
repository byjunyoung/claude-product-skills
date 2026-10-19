/* =============================================================================
 * audit-flow.js — flow audit (read-only, zero writes)
 *
 * Checks: transition arrow geometry · entry direction · pass-through · label z-order · [state] dashes · coverage orphans
 *
 * Used the same way as audit-struct.js, including the optional `const SECTION = "<section node id>";`
 * input: only that section and the sections nested in it are audited. Name lookups and pass-through
 * still see the whole page, and coverage counts only arrows that start or end inside the section, so a
 * frame an arrow from outside reaches is not an orphan. A duplicate name is judged inside the section.
 * Returns: { pass, findings } — each finding is
 * { tag, grade, node, msg }, graded here at the emit site; `pass` is true exactly when `findings` is empty.
 *
 * Excluded sections (templates, archives, deprecated ranges) are treated three different ways.
 *   · dropped from the audit       arrows and labels inside them are not checked
 *   · dropped from coverage        their frames are not required to be connected
 *   · kept as pass-through targets a line actually crossing one is still a broken line
 * Without this distinction, an archive's old arrows come back as violations every run.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const N = C.naming || {}, P = C.pages || {};
const A = (C.arrows || {}).audit || {};

const anyOf = a => (a && a.length ? new RegExp(a.join("|")) : null);
const SEC_EXCLUDE = anyOf(P.exclude_sections);

const ARROW = (N.arrow_delimiter || " --> ").trim();      // the delimiter inside a name
const CHAIN = N.state_chain_delimiter || " ~ ";
const LABEL = N.label_prefix || "[label] ";
const STATE = N.state_chain_prefix || "[state] ";

const EDGE_TOL = A.edge_tolerance != null ? A.edge_tolerance : 2;
const GAP = A.gap_range || [9, 15];
const CLEAR = A.label_clear != null ? A.label_clear : 30;

// Distance from p to the frame's boundary, not to the lines through its edges. Each side is a
// segment: clamp p onto it and measure to the clamped point, then keep the nearest. A point
// far along an edge's line is measured to that segment's end, so it no longer passes.
const distToEdge = (p, R) => {
  const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
  const onTopBottom = [R.y, R.b].map(y => Math.hypot(p.x - clamp(p.x, R.x, R.r), p.y - y));
  const onLeftRight = [R.x, R.r].map(x => Math.hypot(p.x - x, p.y - clamp(p.y, R.y, R.b)));
  return Math.min(...onTopBottom, ...onLeftRight);
};

const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));
const isScreen = n => n.type === "FRAME" && !n.name.startsWith(LABEL) &&
  !n.name.startsWith(STATE) && !n.name.includes(ARROW);

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
const issues = [];
const add = (tag, grade, node, msg) => issues.push({ tag, grade, node: node == null ? null : node, msg });
const allSecs = sectionsDeep(figma.currentPage.children, skipSection);
const scope = SEC ? scopeOf(allSecs) : null;
if (scope && scope.missing) { add("[section]", "blocking", null, `section ${SEC} is not on this page`); return { pass: false, findings: issues }; }
if (scope && scope.excluded) return { pass: true, findings: [], note: `section ${SEC} is excluded by pages.exclude_sections; nothing audited` };
const inSec = d => !SEC || scope.ids.has(d.s.id);
const liveSecs = allSecs.filter(d => !d.skipped && inSec(d));

// Frame dictionary (absolute coordinates). Pass-through checks and name lookups are only
// accurate with excluded sections included, at any depth.
const frames = [];
for (const { s, ax, ay, skipped } of allSecs)
  for (const f of s.children)
    if (isScreen(f))
      frames.push({ id: f.id, name: f.name, sec: s.name, excluded: skipped, scoped: inSec({ s }),
                    x: ax + f.x, y: ay + f.y, r: ax + f.x + f.width, b: ay + f.y + f.height });
// In-scope frames come last so a name that also exists elsewhere resolves to the chosen section's.
const byName = Object.fromEntries([...frames.filter(f => !f.scoped), ...frames.filter(f => f.scoped)].map(f => [f.name, f]));

const dup = frames.filter(f => f.scoped).map(f => f.name).filter((n, i, a) => a.indexOf(n) !== i);
if (dup.length)
  add("[duplicate name]", "blocking", null, `${[...new Set(dup)].join(", ")} — a name lookup catches only one, ${SEC ? "and the duplicate is inside the chosen section" : "so narrow with the section input and re-run"}`);

for (const { s, ax, ay } of liveSecs) {
  for (const n of s.children) {
    if (n.type !== "VECTOR") continue;
    const toAbs = v => ({ x: ax + n.x + v.x, y: ay + n.y + v.y });

    // ── Transition arrows ──────────────────────────────────────────
    if (n.name.includes(ARROW) && !n.name.startsWith(STATE)) {
      const [fr, to] = n.name.split(ARROW).map(t => t.trim());
      const F = byName[fr], T = byName[to];
      if (!F || !T) { add("[arrow]", "blocking", n.id, `${n.name}: orphan (${!F ? fr : to} missing)`); continue; }
      const vs = n.vectorNetwork.vertices.map(toAbs), p0 = vs[0], pe = vs[vs.length - 1];

      const dE = distToEdge(p0, F);
      if (dE > EDGE_TOL) add("[arrow]", "warning", n.id, `${n.name}: start off the edge by ${dE.toFixed(0)}px`);

      const gx = pe.x < T.x ? T.x - pe.x : pe.x > T.r ? pe.x - T.r : 0;
      const gy = pe.y < T.y ? T.y - pe.y : pe.y > T.b ? pe.y - T.b : 0;
      const gap = Math.max(gx, gy);
      if (gap < GAP[0] || gap > GAP[1]) add("[arrow]", "warning", n.id, `${n.name}: target gap ${gap.toFixed(0)}px (expected ${GAP[0]}–${GAP[1]})`);

      // Entry direction — the final segment has to be perpendicular to the target edge.
      // Parallel leaves the arrowhead pointing at empty space beside it, which a distance check alone misses.
      const prev = vs[vs.length - 2];
      if (prev) {
        const dL = Math.abs(pe.x - T.x), dR = Math.abs(pe.x - T.r);
        const dT = Math.abs(pe.y - T.y), dB = Math.abs(pe.y - T.b);
        const vEdge = Math.min(dL, dR) <= Math.min(dT, dB);
        const finalH = Math.abs(pe.y - prev.y) < 2, finalV = Math.abs(pe.x - prev.x) < 2;
        if (vEdge ? !finalH : !finalV) add("[arrow]", "warning", n.id, `${n.name}: arrowhead parallel to the target edge (wrong direction)`);
      }

      for (let i = 1; i < vs.length; i++) {
        const sx = Math.min(vs[i-1].x, vs[i].x), sr = Math.max(vs[i-1].x, vs[i].x);
        const sy = Math.min(vs[i-1].y, vs[i].y), sb = Math.max(vs[i-1].y, vs[i].y);
        for (const f of frames) {
          if (f.name === fr || f.name === to) continue;
          if (sx < f.r && sr > f.x && sy < f.b && sb > f.y)
            add("[arrow]", "blocking", n.id, `${n.name}: seg${i} passes through ${f.name}`);
        }
      }
    }

    // ── [state] chains ─────────────────────────────────────────────
    if (n.name.startsWith(STATE) && n.name.includes(CHAIN)) {
      const [a, b] = n.name.slice(STATE.length).split(CHAIN).map(t => t.trim());
      const F = byName[a], T = byName[b];
      if (!F || !T) { add("[state]", "blocking", n.id, `${n.name}: orphan (${!F ? a : b} missing)`); continue; }
      const vs = n.vectorNetwork.vertices.map(toAbs), p0 = vs[0], pe = vs[vs.length - 1];

      // It has to be a 2-vertex vertical straight line. An elbow curls over its own from and to
      // and slips past the pass-through check.
      if (vs.length !== 2 || Math.abs(p0.x - pe.x) > 2) {
        add("[state]", "warning", n.id, `${n.name}: not vertical / elbowed (vertex ${vs.length}) — regenerate as vertical in one column, or gather the placement`);
        continue;
      }
      if (F.y > T.y) add("[state]", "warning", n.id, `${n.name}: name order reversed (from is below)`);
      if (Math.abs(p0.y - F.b) > EDGE_TOL) add("[state]", "warning", n.id, `${n.name}: start is ${Math.abs(p0.y - F.b).toFixed(0)}px off from's bottom edge`);
      if (Math.abs(pe.y - T.y) > EDGE_TOL) add("[state]", "warning", n.id, `${n.name}: end is ${Math.abs(pe.y - T.y).toFixed(0)}px off to's top edge`);

      // The y checks above leave the column free: a line on the right row but beside the frame is
      // not attached to it. Its x has to lie within each frame's x-span, same tolerance as the edges.
      if (p0.x < F.x - EDGE_TOL || p0.x > F.r + EDGE_TOL) add("[state]", "warning", n.id, `${n.name}: start x is outside from's x-span (${F.x.toFixed(0)}–${F.r.toFixed(0)})`);
      if (pe.x < T.x - EDGE_TOL || pe.x > T.r + EDGE_TOL) add("[state]", "warning", n.id, `${n.name}: end x is outside to's x-span (${T.x.toFixed(0)}–${T.r.toFixed(0)})`);

      const lx = p0.x, top = Math.min(p0.y, pe.y), bot = Math.max(p0.y, pe.y);
      for (const f of frames) {
        if (f.name === a || f.name === b) continue;
        if (f.x < lx && f.r > lx && f.y < bot && f.b > top)
          add("[state]", "blocking", n.id, `${n.name}: passes through ${f.name} — a placement problem (wedged between the parent and its variant)`);
      }
    }
  }

  // ── Labels ────────────────────────────────────────────────────
  // A label breaks three ways. Too low in z-order and the line runs through the text;
  // too close to the arrowhead and it hides where the arrow goes; sitting on another
  // arrow's line and it becomes ambiguous which arrow it belongs to.
  const segsOf = n => {
    const vs = n.vectorNetwork.vertices.map(v => ({ x: ax + n.x + v.x, y: ay + n.y + v.y }));
    const out = [];
    for (let i = 1; i < vs.length; i++)
      out.push({ x: Math.min(vs[i-1].x, vs[i].x), r: Math.max(vs[i-1].x, vs[i].x),
                 y: Math.min(vs[i-1].y, vs[i].y), b: Math.max(vs[i-1].y, vs[i].y) });
    return { segs: out, head: vs[vs.length - 1] };
  };
  const arrowsHere = s.children.filter(c => c.type === "VECTOR" && c.name.includes(ARROW) && !c.name.startsWith(STATE));

  for (const p of s.children) {
    if (!p.name.startsWith(LABEL)) continue;
    const owner = p.name.slice(LABEL.length);
    const v = s.children.find(c => c.name === owner);
    if (v && s.children.indexOf(p) < s.children.indexOf(v))
      add("[label]", "warning", p.id, `${p.name}: pill is below the arrow in z-order`);
    if (p.width == null) continue;
    const box = { x: ax + p.x, y: ay + p.y, r: ax + p.x + p.width, b: ay + p.y + p.height };

    // Does it hide its own arrowhead — a violation when the target point falls inside the pill grown by label_clear
    if (v && v.type === "VECTOR") {
      const { head } = segsOf(v);
      if (head && head.x > box.x - CLEAR && head.x < box.r + CLEAR &&
                  head.y > box.y - CLEAR && head.y < box.b + CLEAR)
        add("[label]", "warning", p.id, `${p.name}: within ${CLEAR}px of the arrowhead — it hides the target point`);
    }

    // Does it cover another arrow's line — a label sitting on a shared trunk is the usual culprit
    for (const a of arrowsHere) {
      if (a.name === owner) continue;
      const { segs } = segsOf(a);
      if (segs.some(g => box.x < g.r && box.r > g.x && box.y < g.b && box.b > g.y)) {
        add("[label]", "warning", p.id, `${p.name}: covers ${a.name}'s line`);
        break;
      }
    }
  }
}

// ── Coverage orphans — every screen frame must appear in the flow at least once ──────
// The connected set includes arrows from excluded sections too (a frame an archive points
// at is still connected). But only frames in live sections are required to be connected.
// Every arrow on the page is read, so under SECTION a frame reached from outside the section is
// not an orphan; only frames of the section are required to be connected (below).
const connected = new Set();
const reach = names => names.forEach(x => connected.add(x));
for (const { s } of allSecs)
  for (const c of s.children) {
    if (c.type !== "VECTOR") continue;
    if (c.name.startsWith(STATE) && c.name.includes(CHAIN))
      reach(c.name.slice(STATE.length).split(CHAIN).map(t => t.trim()));
    else if (c.name.includes(ARROW))
      reach(c.name.split(ARROW).map(t => t.trim()));
  }
// Canonical state frames on a shared page are expected not to appear in per-screen flow, and
// neither are the compositions on a pattern page — a pattern is how a row is built, not a screen
// anybody navigates to. Either page is dropped from coverage whole. With the setting null the
// exception does not apply, which is why a file that has just adopted a pattern page and not yet
// recorded it in the config still reports every pattern frame as an orphan.
const EXEMPT_PAGE = [N.common_page_pattern, N.pattern_page_pattern]
  .filter(Boolean).map(p => new RegExp(p));
const isExemptPage = EXEMPT_PAGE.some(re => re.test(figma.currentPage.name));
if (!isExemptPage)
  for (const f of frames)
    if (!f.excluded && f.scoped && !connected.has(f.name))
      add("[coverage]", "blocking", f.id, `orphan frame (absent from the flow): ${f.name} — ${f.sec}`);

return { pass: issues.length === 0, findings: issues };
