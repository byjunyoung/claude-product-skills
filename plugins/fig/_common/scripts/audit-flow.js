/* =============================================================================
 * audit-flow.js — flow audit (read-only, zero writes)
 *
 * Checks: transition arrow geometry · entry direction · pass-through · label z-order · [state] dashes · coverage orphans
 *
 * Used the same way as audit-struct.js. Returns: an array of violations, or "FLOW PASS"
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

const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));
const isScreen = n => n.type === "FRAME" && !n.name.startsWith(LABEL) &&
  !n.name.startsWith(STATE) && !n.name.includes(ARROW);

const allSecs = figma.currentPage.children.filter(c => c.type === "SECTION");
const liveSecs = allSecs.filter(s => !skipSection(s));

// Frame dictionary (absolute coordinates). Pass-through checks and name lookups are only
// accurate with excluded sections included.
const frames = [];
for (const s of allSecs)
  for (const f of s.children)
    if (isScreen(f))
      frames.push({ name: f.name, sec: s.name, excluded: skipSection(s),
                    x: s.x + f.x, y: s.y + f.y, r: s.x + f.x + f.width, b: s.y + f.y + f.height });
const byName = Object.fromEntries(frames.map(f => [f.name, f]));

const dup = frames.map(f => f.name).filter((n, i, a) => a.indexOf(n) !== i);
const issues = [];
if (dup.length)
  issues.push(`[duplicate name] ${[...new Set(dup)].join(", ")} — a name lookup catches only one, so narrow to a single section and re-run`);

for (const s of liveSecs) {
  for (const n of s.children) {
    if (n.type !== "VECTOR") continue;
    const toAbs = v => ({ x: s.x + n.x + v.x, y: s.y + n.y + v.y });

    // ── Transition arrows ──────────────────────────────────────────
    if (n.name.includes(ARROW) && !n.name.startsWith(STATE)) {
      const [fr, to] = n.name.split(ARROW).map(t => t.trim());
      const F = byName[fr], T = byName[to];
      if (!F || !T) { issues.push(`[arrow] ${n.name}: orphan (${!F ? fr : to} missing)`); continue; }
      const vs = n.vectorNetwork.vertices.map(toAbs), p0 = vs[0], pe = vs[vs.length - 1];

      const dE = Math.min(Math.abs(p0.x - F.x), Math.abs(p0.x - F.r),
                          Math.abs(p0.y - F.y), Math.abs(p0.y - F.b));
      if (dE > EDGE_TOL) issues.push(`[arrow] ${n.name}: start off the edge by ${dE.toFixed(0)}px`);

      const gx = pe.x < T.x ? T.x - pe.x : pe.x > T.r ? pe.x - T.r : 0;
      const gy = pe.y < T.y ? T.y - pe.y : pe.y > T.b ? pe.y - T.b : 0;
      const gap = Math.max(gx, gy);
      if (gap < GAP[0] || gap > GAP[1]) issues.push(`[arrow] ${n.name}: target gap ${gap.toFixed(0)}px (expected ${GAP[0]}–${GAP[1]})`);

      // Entry direction — the final segment has to be perpendicular to the target edge.
      // Parallel leaves the arrowhead pointing at empty space beside it, which a distance check alone misses.
      const prev = vs[vs.length - 2];
      if (prev) {
        const dL = Math.abs(pe.x - T.x), dR = Math.abs(pe.x - T.r);
        const dT = Math.abs(pe.y - T.y), dB = Math.abs(pe.y - T.b);
        const vEdge = Math.min(dL, dR) <= Math.min(dT, dB);
        const finalH = Math.abs(pe.y - prev.y) < 2, finalV = Math.abs(pe.x - prev.x) < 2;
        if (vEdge ? !finalH : !finalV) issues.push(`[arrow] ${n.name}: arrowhead parallel to the target edge (wrong direction)`);
      }

      for (let i = 1; i < vs.length; i++) {
        const sx = Math.min(vs[i-1].x, vs[i].x), sr = Math.max(vs[i-1].x, vs[i].x);
        const sy = Math.min(vs[i-1].y, vs[i].y), sb = Math.max(vs[i-1].y, vs[i].y);
        for (const f of frames) {
          if (f.name === fr || f.name === to) continue;
          if (sx < f.r && sr > f.x && sy < f.b && sb > f.y)
            issues.push(`[arrow] ${n.name}: seg${i} passes through ${f.name}`);
        }
      }
    }

    // ── [state] chains ─────────────────────────────────────────────
    if (n.name.startsWith(STATE) && n.name.includes(CHAIN)) {
      const [a, b] = n.name.slice(STATE.length).split(CHAIN).map(t => t.trim());
      const F = byName[a], T = byName[b];
      if (!F || !T) { issues.push(`[state] ${n.name}: orphan (${!F ? a : b} missing)`); continue; }
      const vs = n.vectorNetwork.vertices.map(toAbs), p0 = vs[0], pe = vs[vs.length - 1];

      // It has to be a 2-vertex vertical straight line. An elbow curls over its own from and to
      // and slips past the pass-through check.
      if (vs.length !== 2 || Math.abs(p0.x - pe.x) > 2) {
        issues.push(`[state] ${n.name}: not vertical / elbowed (vertex ${vs.length}) — regenerate as vertical in one column, or gather the placement`);
        continue;
      }
      if (F.y > T.y) issues.push(`[state] ${n.name}: name order reversed (from is below)`);
      if (Math.abs(p0.y - F.b) > EDGE_TOL) issues.push(`[state] ${n.name}: start is ${Math.abs(p0.y - F.b).toFixed(0)}px off from's bottom edge`);
      if (Math.abs(pe.y - T.y) > EDGE_TOL) issues.push(`[state] ${n.name}: end is ${Math.abs(pe.y - T.y).toFixed(0)}px off to's top edge`);

      const lx = p0.x, top = Math.min(p0.y, pe.y), bot = Math.max(p0.y, pe.y);
      for (const f of frames) {
        if (f.name === a || f.name === b) continue;
        if (f.x < lx && f.r > lx && f.y < bot && f.b > top)
          issues.push(`[state] ${n.name}: passes through ${f.name} — a placement problem (wedged between the parent and its variant)`);
      }
    }
  }

  // ── Labels ────────────────────────────────────────────────────
  // A label breaks three ways. Too low in z-order and the line runs through the text;
  // too close to the arrowhead and it hides where the arrow goes; sitting on another
  // arrow's line and it becomes ambiguous which arrow it belongs to.
  const segsOf = n => {
    const vs = n.vectorNetwork.vertices.map(v => ({ x: s.x + n.x + v.x, y: s.y + n.y + v.y }));
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
      issues.push(`[label] ${p.name}: pill is below the arrow in z-order`);
    if (p.width == null) continue;
    const box = { x: s.x + p.x, y: s.y + p.y, r: s.x + p.x + p.width, b: s.y + p.y + p.height };

    // Does it hide its own arrowhead — a violation when the target point falls inside the pill grown by label_clear
    if (v && v.type === "VECTOR") {
      const { head } = segsOf(v);
      if (head && head.x > box.x - CLEAR && head.x < box.r + CLEAR &&
                  head.y > box.y - CLEAR && head.y < box.b + CLEAR)
        issues.push(`[label] ${p.name}: within ${CLEAR}px of the arrowhead — it hides the target point`);
    }

    // Does it cover another arrow's line — a label sitting on a shared trunk is the usual culprit
    for (const a of arrowsHere) {
      if (a.name === owner) continue;
      const { segs } = segsOf(a);
      if (segs.some(g => box.x < g.r && box.r > g.x && box.y < g.b && box.b > g.y)) {
        issues.push(`[label] ${p.name}: covers ${a.name}'s line`);
        break;
      }
    }
  }
}

// ── Coverage orphans — every screen frame must appear in the flow at least once ──────
// The connected set includes arrows from excluded sections too (a frame an archive points
// at is still connected). But only frames in live sections are required to be connected.
const connected = new Set();
for (const s of allSecs)
  for (const c of s.children) {
    if (c.type !== "VECTOR") continue;
    if (c.name.startsWith(STATE) && c.name.includes(CHAIN))
      c.name.slice(STATE.length).split(CHAIN).map(t => t.trim()).forEach(x => connected.add(x));
    else if (c.name.includes(ARROW))
      c.name.split(ARROW).map(t => t.trim()).forEach(x => connected.add(x));
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
    if (!f.excluded && !connected.has(f.name))
      issues.push(`[coverage] orphan frame (absent from the flow): ${f.name} — ${f.sec}`);

return issues.length ? issues : "FLOW PASS";
