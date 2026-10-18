/* =============================================================================
 * arrow-build.js — flow arrow creation helpers (preamble)
 *
 * This is not an audit but a **build preamble**. Prepend the config, append the actual
 * creation calls, and hand the whole thing to use_figma. The same shape as a deck preamble.
 *
 *   const CFG = {...};        ← resolve-config.py --js
 *   <this whole file>
 *   const sec = figma.currentPage.children.find(c => c.name === "01. Member - List");
 *   await straight(sec, "Login-Default", "Home-Default");
 *   return { createdNodeIds: [...] };
 *
 * Coordinates are never computed outside and passed in. They are looked up live inside the
 * script with find() — the user may have rearranged the canvas in the meantime.
 *
 * The config decides the rules (colour, weight, trunk, clearance, labels). Where the page already
 * has arrows, reading their stroke and following it comes first; these defaults apply only otherwise.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const AR = C.arrows || {}, LB = AR.label || {}, NM = C.naming || {};

const hx = h => {
  const n = parseInt(String(h).replace("#", ""), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
};

const COLOR = hx(AR.color || "#4A5463");
const WEIGHT = AR.stroke_weight != null ? AR.stroke_weight : 3;
const DASH = AR.dash_conditional || [12, 8];
const GAP = AR.head_gap != null ? AR.head_gap : 12;
const TRUNK = AR.trunk != null ? AR.trunk : 120;
const OFFSET = AR.parallel_offset != null ? AR.parallel_offset : 24;
const CAP = AR.cap || { start: "ROUND", end: "ARROW_EQUILATERAL" };

const ARROW_D = NM.arrow_delimiter || " --> ";
const CHAIN_D = NM.state_chain_delimiter || " ~ ";
const LABEL_P = NM.label_prefix || "[label] ";
const STATE_P = NM.state_chain_prefix || "[state] ";

const arrowName = (from, to) => from + ARROW_D + to;
const chainName = (from, to) => STATE_P + from + CHAIN_D + to;

/** Live lookup of a frame's coordinates within a section. Returns section-relative coordinates.
 *  A cross-section arrow adds section.x/y to convert to absolute before computing. */
function find(section, name) {
  const n = section.children.find(c => c.name === name && c.type === "FRAME");
  if (!n) throw new Error(`frame not found: ${name}`);
  return { x: n.x, y: n.y, w: n.width, h: n.height,
           r: n.x + n.width, b: n.y + n.height,
           cx: n.x + n.width / 2, cy: n.y + n.height / 2 };
}

/** The stroke paint: opts.stroke's colour and opacity over the config's colour. */
function paintOf(st) {
  const p = { type: "SOLID", color: st.color || COLOR };
  if (st.opacity != null && st.opacity !== 1) p.opacity = st.opacity;
  return p;
}

/** Creates an arrow from an array of vertices. Two points is a straight line, three or more a right-angle elbow.
 *  opts: { dashed, bidirectional, stroke: { color, weight, dash, opacity } }
 *  A field present in opts.stroke overrides the config's COLOR / WEIGHT / DASH; `dash: null` is solid
 *  even with `dashed`. A re-sync passes in what styleOf() read off the arrow it replaces. */
async function arrow(parent, name, pts, opts) {
  const o = opts || {};
  const st = o.stroke || {};
  const minX = Math.min(...pts.map(p => p[0])), minY = Math.min(...pts.map(p => p[1]));
  const v = figma.createVector();
  await v.setVectorNetworkAsync({
    vertices: pts.map((p, i) => ({
      x: p[0] - minX, y: p[1] - minY,
      ...(i === 0 ? { strokeCap: o.bidirectional ? CAP.end : CAP.start } : {}),
      ...(i === pts.length - 1 ? { strokeCap: CAP.end } : {})
    })),
    segments: pts.slice(1).map((_, i) => ({ start: i, end: i + 1 }))
  });
  v.strokes = [paintOf(st)];
  v.strokeWeight = st.weight != null ? st.weight : WEIGHT;
  const dash = "dash" in st ? st.dash : (o.dashed ? DASH : null);
  if (dash && dash.length) v.dashPattern = dash;
  v.name = name;
  parent.appendChild(v);          // appendChild first, coordinates after
  v.x = minX; v.y = minY;
  return v.id;
}

/** Reads the style off an existing arrow, so a re-sync can hand it to arrow() as opts before the old
 *  vector is deleted. Returns null when the vector has no SOLID stroke (the config's style applies).
 *  Bidirectional means the first vertex carries the end cap, the way arrow() draws it. */
function styleOf(vector) {
  const s = vector.strokes && vector.strokes[0];
  if (!s || s.type !== "SOLID") return null;
  const dash = vector.dashPattern;
  const v0 = vector.vectorNetwork && vector.vectorNetwork.vertices && vector.vectorNetwork.vertices[0];
  return {
    stroke: {
      color: s.color, weight: vector.strokeWeight, dash: dash && dash.length ? [...dash] : null,
      ...(s.opacity != null && s.opacity !== 1 ? { opacity: s.opacity } : {})
    },
    bidirectional: !!v0 && v0.strokeCap === CAP.end
  };
}

/* ── Three path patterns (target on the right. Other directions mirror on the axis) ─── */

/** 1) Straight — when the cross-axis coordinates match */
async function straight(section, fromName, toName, opts) {
  const s = find(section, fromName), d = find(section, toName);
  return arrow(section, arrowName(fromName, toName),
    [[s.r, s.cy], [d.x - GAP, s.cy]], opts);
}

/** 2) Branching trunk elbow — from one source to several targets.
 *  trunkX must be shared, one per source frame, so the trunks overlap and read as a single line. */
async function trunkElbow(section, fromName, toName, trunkX, opts) {
  const s = find(section, fromName), d = find(section, toName);
  const tx = trunkX != null ? trunkX : s.r + TRUNK;
  return arrow(section, arrowName(fromName, toName),
    [[s.r, s.cy], [tx, s.cy], [tx, d.cy], [d.x - GAP, d.cy]], opts);
}

/** 3) Detour (a U shape) — up into the corridor above the row when the direct path crosses another frame.
 *  Arriving from above or below must target the top or bottom edge, not the left or right —
 *  aiming at the left edge and descending vertically leaves the arrowhead parallel to that edge,
 *  pointing at empty space beside it. */
async function detour(section, fromName, toName, corridorY, opts) {
  const s = find(section, fromName), d = find(section, toName);
  const cy = corridorY != null ? corridorY : Math.min(s.y, d.y) - 80;
  return arrow(section, arrowName(fromName, toName),
    [[s.cx, s.y], [s.cx, cy], [d.cx, cy], [d.cx, d.y - GAP]], opts);
}

/** The label pill. Always call it after every arrow is made — the pill has to be above in z-order
 *  or the line runs through the label text. (cx, cy) is the centre point on the line it sits on. */
async function pill(section, forArrowName, text, cx, cy) {
  const font = LB.font || { family: "Inter", style: "Medium", size: 20 };
  await figma.loadFontAsync({ family: font.family, style: font.style });
  const pad = LB.padding || [10, 5];
  const p = figma.createAutoLayout("HORIZONTAL", { name: LABEL_P + forArrowName });
  p.paddingLeft = pad[0]; p.paddingRight = pad[0];
  p.paddingTop = pad[1]; p.paddingBottom = pad[1];
  p.cornerRadius = LB.corner_radius != null ? LB.corner_radius : 8;
  p.fills = [{ type: "SOLID", color: hx(LB.fill || "#FFFFFF") }];
  p.strokes = [{ type: "SOLID", color: hx(LB.stroke || "#D9DBE3") }];
  p.strokeWeight = 1;
  const t = figma.createText();
  t.fontName = { family: font.family, style: font.style };
  t.fontSize = font.size;
  t.characters = text;
  t.fills = [{ type: "SOLID", color: hx(LB.text_color || "#59616E") }];
  p.appendChild(t);
  section.appendChild(p);
  p.x = cx - p.width / 2;         // centred after the hug measurement completes
  p.y = cy - p.height / 2;
  return p.id;
}

/** [state] chain — a headless dashed line joining one screen's adjacent state variants.
 *  It marks a grouping, not a transition. Use it only on pairs that touch vertically in one column —
 *  another frame in between gets crossed by the straight line.
 *  opts.stroke works as in arrow(); a re-sync passes styleOf()'s stroke so the style survives. Dashed
 *  unless opts.stroke.dash says otherwise (`dash: null` is solid). */
async function stateLink(section, fromName, toName, opts) {
  const st = (opts && opts.stroke) || {};
  const f = find(section, fromName), t = find(section, toName);
  const v = figma.createVector();
  await v.setVectorNetworkAsync({                 // no strokeCap = no arrowhead
    vertices: [{ x: 0, y: 0 }, { x: 0, y: t.y - f.b }],
    segments: [{ start: 0, end: 1 }]
  });
  v.strokes = [paintOf(st)];
  v.strokeWeight = st.weight != null ? st.weight : WEIGHT;
  const dash = "dash" in st ? st.dash : DASH;
  if (dash && dash.length) v.dashPattern = dash;
  v.name = chainName(fromName, toName);
  section.appendChild(v);
  v.x = f.cx; v.y = f.b;
  return v.id;
}

/** Whether the path crosses another frame. Judge with straight first, and on a hit promote to trunkElbow or detour. */
function hits(section, pts, exclude) {
  const skip = new Set(exclude || []);
  const rects = section.children
    .filter(c => c.type === "FRAME" && !c.name.startsWith(LABEL_P) && !skip.has(c.name))
    .map(c => ({ name: c.name, x: c.x, y: c.y, r: c.x + c.width, b: c.y + c.height }));
  const out = [];
  for (let i = 1; i < pts.length; i++) {
    const sx = Math.min(pts[i-1][0], pts[i][0]), sr = Math.max(pts[i-1][0], pts[i][0]);
    const sy = Math.min(pts[i-1][1], pts[i][1]), sb = Math.max(pts[i-1][1], pts[i][1]);
    for (const f of rects)
      if (sx < f.r && sr > f.x && sy < f.b && sb > f.y) out.push(f.name);
  }
  return [...new Set(out)];
}
