/* =============================================================================
 * probe-page.js — infers conventions from one page (read-only, zero writes)
 *
 * Used by /fig:setup when drafting a conventions.yaml for an unfamiliar file.
 * It decides no rules and emits **observations only** — what counts as a convention is aggregated on the host.
 *
 * What to prepend: `const PAGE_ID = "<page id>";`
 * Returns: an observation object of the shape below. `sections` lists every section at any depth,
 * each with a `depth` (0 = directly on the page) and an absolute x/y.
 *
 * Why it decides nothing — with one page as the sample, coincidence hardens into convention.
 * Only after running several pages in parallel and summing them does the mode count as a convention.
 * ========================================================================== */

const page = await figma.getNodeByIdAsync(PAGE_ID);
if (!page) return { error: `page not found: ${PAGE_ID}` };
await figma.setCurrentPageAsync(page);

const hex = c => "#" + [c.r, c.g, c.b].map(v =>
  Math.round(v * 255).toString(16).padStart(2, "0").toUpperCase()).join("");
const paint = arr => (Array.isArray(arr) && arr[0] && arr[0].type === "SOLID")
  ? { hex: hex(arr[0].color), opacity: arr[0].opacity != null ? +arr[0].opacity.toFixed(3) : 1 }
  : null;
const g = (n, k) => { try { return n[k]; } catch (e) { return undefined; } };

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

// The probe observes every section, scaffolding included: what counts as scaffolding is a
// convention the host is still working out, so nothing is skipped here.
const walked = sectionsDeep(page.children, () => false);
const secs = walked.map(d => d.s);
const depthOf = s => { let d = 0; for (let p = s.parent; p && p.type === "SECTION"; p = p.parent) d++; return d; };
const out = {
  page: page.name,
  sectionCount: secs.length,
  sections: [],
  frameNames: [],
  suffixes: {},
  gaps: { frameX: [], frameY: [], sectionX: [], sectionY: [] },
  columnPitch: [],
  arrows: { count: 0, styles: [], headGaps: [] },
  labels: { count: 0, styles: [] },
  stateLinks: 0,
  dashedFrames: [],          // placeholder candidates
  pageDirectFrames: 0        // screen frames outside a section = a signal that this page is loose
};

for (const f of page.children) if (f.type === "FRAME") out.pageDirectFrames++;

for (const { s, ax, ay } of walked) {
  out.sections.push({
    name: s.name, x: Math.round(ax), y: Math.round(ay),     // absolute, so nested sections compare with top-level ones
    depth: depthOf(s),                                      // 0 = directly on the page
    w: Math.round(s.width), h: Math.round(s.height),
    fill: paint(g(s, "fills")), stroke: paint(g(s, "strokes")),
    strokeWeight: g(s, "strokeWeight"), strokeAlign: g(s, "strokeAlign"),
    dash: g(s, "dashPattern"), radius: g(s, "cornerRadius"),
    children: s.children.length
  });

  const frames = s.children.filter(c => c.type === "FRAME");
  for (const f of frames) {
    out.frameNames.push(f.name);
    const m = f.name.match(/-([A-Za-z][\w]*)$/);        // the state part of [screen name]-[state]
    if (m) out.suffixes[m[1]] = (out.suffixes[m[1]] || 0) + 1;
    if (Array.isArray(g(f, "dashPattern")) && f.dashPattern.length)
      out.dashedFrames.push({ name: f.name, dash: f.dashPattern,
        stroke: paint(g(f, "strokes")), fill: paint(g(f, "fills")),
        strokeWeight: g(f, "strokeWeight") });
  }

  // Gaps count **adjacent pairs only**. Counting every pair floods the list with multiples
  // (distances skipping two or three slots) and the mode collapses — measured, frame_gap fell
  // to 24/69 (35%) and became impossible to infer.
  const bucket = (arr, key) => {
    const m = {};
    for (const f of arr) { const k = Math.round(f[key] / 8); (m[k] = m[k] || []).push(f); }
    return Object.values(m);
  };
  for (const row of bucket(frames, "y")) {
    row.sort((a, b) => a.x - b.x);
    for (let i = 1; i < row.length; i++) {
      out.gaps.frameX.push(Math.round(row[i].x - (row[i - 1].x + row[i - 1].width)));
      out.columnPitch.push(Math.round(row[i].x - row[i - 1].x));   // column grid = the difference between adjacent column origins
    }
  }
  for (const col of bucket(frames, "x")) {
    col.sort((a, b) => a.y - b.y);
    for (let i = 1; i < col.length; i++)
      out.gaps.frameY.push(Math.round(col[i].y - (col[i - 1].y + col[i - 1].height)));
  }

  for (const n of s.children) {
    if (n.type !== "VECTOR") continue;
    const st = { color: paint(g(n, "strokes")), weight: g(n, "strokeWeight"), dash: g(n, "dashPattern") };
    if (n.name.startsWith("[state]") || (n.name.includes("~") && !n.name.includes("-->"))) {
      out.stateLinks++;
    } else if (n.name.includes("-->")) {
      out.arrows.count++;
      if (out.arrows.styles.length < 8) out.arrows.styles.push(st);
      // the gap between the arrowhead and the target frame — for inferring the default
      const to = n.name.split("-->")[1];
      const T = to && frames.find(f => f.name === to.trim());
      if (T) {
        const vs = n.vectorNetwork.vertices;
        const pe = vs[vs.length - 1];
        const ax = n.x + pe.x, ay = n.y + pe.y;
        const gx = ax < T.x ? T.x - ax : ax > T.x + T.width ? ax - (T.x + T.width) : 0;
        const gy = ay < T.y ? T.y - ay : ay > T.y + T.height ? ay - (T.y + T.height) : 0;
        const gap = Math.round(Math.max(gx, gy));
        if (gap > 0 && gap < 100) out.arrows.headGaps.push(gap);
      }
    }
  }

  for (const n of s.children) {
    if (!n.name.startsWith("[label]")) continue;
    out.labels.count++;
    if (out.labels.styles.length >= 5) continue;
    const t = n.findOne ? n.findOne(x => x.type === "TEXT") : null;
    out.labels.styles.push({
      fill: paint(g(n, "fills")), stroke: paint(g(n, "strokes")),
      radius: g(n, "cornerRadius"),
      padding: [g(n, "paddingLeft"), g(n, "paddingTop")],
      font: t ? { family: t.fontName.family, style: t.fontName.style, size: t.fontSize } : null,
      textColor: t ? paint(g(t, "fills")) : null
    });
  }
}

// Gaps between sections — adjacent pairs only, for the same reason as frames. Only sections that
// share a parent are neighbours: their x/y are in the same coordinate space, and a nested section
// beside a top-level one is not a gap anyone drew.
const sbucket = (key) => {
  const m = {};
  secs.forEach(s => {
    const pid = s.parent ? s.parent.id : "";
    const k = pid + "|" + Math.round(s[key] / 40);
    (m[k] = m[k] || []).push(s);
  });
  return Object.values(m);
};
for (const row of sbucket("y")) {
  row.sort((a, b) => a.x - b.x);
  for (let i = 1; i < row.length; i++)
    out.gaps.sectionX.push(Math.round(row[i].x - (row[i - 1].x + row[i - 1].width)));
}
for (const col of sbucket("x")) {
  col.sort((a, b) => a.y - b.y);
  for (let i = 1; i < col.length; i++)
    out.gaps.sectionY.push(Math.round(col[i].y - (col[i - 1].y + col[i - 1].height)));
}

return out;
