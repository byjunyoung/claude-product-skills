/* =============================================================================
 * prep-ops.js — page tidying helpers (preamble)
 *
 * Section creation · absorption · renumbering · placeholders · shared-page reference annotations.
 * Used the same way as arrow-build.js — config + this file + the actual calls.
 *
 * This writes, so keep each call small and confirm with an audit at every stage.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const SS = C.section_style || {}, PS = C.placeholder_style || {};
const LO = C.layout || {}, PG = C.pages || {};

const hx = h => {
  const n = parseInt(String(h).replace("#", ""), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
};

/** Section creation. Dropping it to the bottom of the z-order is mandatory —
 *  without it the new section covers existing frames with a white background. */
function createSection(name, x, y, w, h) {
  const s = figma.createSection();
  s.name = name;
  s.x = x; s.y = y;
  s.resizeWithoutConstraints(w, h);
  // the d.ts has fills only, but the runtime SectionNode supports strokes and cornerRadius
  if (SS.fill) s.fills = [{ type: "SOLID", color: hx(SS.fill), opacity: SS.fill_opacity != null ? SS.fill_opacity : 1 }];
  if (SS.stroke) {
    s.strokes = [{ type: "SOLID", color: hx(SS.stroke) }];
    s.strokeWeight = SS.stroke_weight != null ? SS.stroke_weight : 1;
    s.strokeAlign = SS.stroke_align || "INSIDE";
  }
  if (SS.dash) s.dashPattern = SS.dash;
  if (SS.corner_radius != null) s.cornerRadius = SS.corner_radius;
  figma.currentPage.insertChild(0, s);
  return s;
}

/** Absorption — makes a frame a direct child of a section.
 *  appendChild is refused with a font-load failure where the text uses a local font (not cloud-synced),
 *  but group→ungroup does not go through font validation. No manual dragging needed.
 *  jobs: [[frameId, sectionId], ...] */
async function absorb(jobs) {
  const mutatedNodeIds = [];
  for (const [frameId, sectionId] of jobs) {
    const f = await figma.getNodeByIdAsync(frameId);
    const s = await figma.getNodeByIdAsync(sectionId);
    // The coordinate correction is judged from the parent **before** the group call.
    // If it is already that section's child the coordinates are already relative, so subtracting
    // unconditionally double-subtracts and shoots the frame outside the section.
    const already = f.parent.id === s.id;
    const preX = f.x, preY = f.y;
    const g = figma.group([f], s);
    figma.ungroup(g);
    if (!already) { f.x = preX - s.x; f.y = preY - s.y; }
    mutatedNodeIds.push(frameId);
  }
  return { mutatedNodeIds };
}

/** Section resize + neighbour-invasion check.
 *  Sections do not auto-resize. The most common accident when growing one to fit a placeholder is
 *  invading the row below or beside. All four edges have to be checked — vertical alone misses it.
 *  The neighbours are the sections in the same parent, whether that is the page or another section:
 *  their x/y share one coordinate space, so a nested section is checked against its own siblings. */
function resizeSection(section, contentW, contentH) {
  const m = LO.section_resize_margin || [80, 160];
  section.resizeWithoutConstraints(contentW + m[0] * 2, contentH + m[0] * 2);
  const T = { x: section.x, y: section.y, r: section.x + section.width, b: section.y + section.height };
  return section.parent.children
    .filter(c => c.type === "SECTION" && c.id !== section.id)
    .filter(s => s.x < T.r && s.x + s.width > T.x && s.y < T.b && s.y + s.height > T.y)
    .map(s => s.name);          // safe only when empty
}

/** Renumbering — reassigns NN. in canvas order (row-major).
 *  Protected ranges (numbers slated for deprecation, say) are left alone.
 *  Top-level sections only, on purpose: the NN. number is a page-level convention, one sequence
 *  down the canvas, and a section nested inside one is part of that feature, not a new number. */
function renumber() {
  const BUCKET = LO.row_bucket || 1000;
  const PROT = PG.protected_numbers || [];
  const sections = figma.currentPage.children
    .filter(c => c.type === "SECTION" && /^\d+\./.test(c.name) && !PROT.some(p => c.name.startsWith(p)))
    .sort((a, b) => (Math.round(a.y / BUCKET) - Math.round(b.y / BUCKET)) || (a.x - b.x));
  const mutatedNodeIds = [];
  sections.forEach((s, i) => {
    const next = s.name.replace(/^\d+\./, String(i + 1).padStart(2, "0") + ".");
    if (next !== s.name) { s.name = next; mutatedNodeIds.push(s.id); }
  });
  return { mutatedNodeIds, renamed: mutatedNodeIds.length };
}

/** A placeholder frame. Make it a child of the right section at creation time —
 *  that is the principle, rather than absorbing it later. Where the policy is undecided, note TBD in desc. */
async function placeholder(section, name, desc, w, h, relX, relY) {
  const font = PS.font || { family: "Inter", style: "Regular", size: 28 };
  await figma.loadFontAsync({ family: font.family, style: font.style });
  const f = figma.createFrame();
  f.name = name;                                   // follows the naming rule — it becomes an arrow target later
  f.resize(w, h);
  f.fills = [{ type: "SOLID", color: hx(PS.fill || "#FAFAFB") }];
  f.strokes = [{ type: "SOLID", color: hx(PS.stroke || "#B3B3BF") }];
  f.strokeWeight = PS.stroke_weight != null ? PS.stroke_weight : 2;
  f.dashPattern = PS.dash || [10, 8];               // a dashed border identifies a placeholder
  const t = figma.createText();
  t.fontName = { family: font.family, style: font.style };
  t.fontSize = font.size;
  t.characters = (PS.text_prefix || "Placeholder — ") + desc;
  t.fills = [{ type: "SOLID", color: hx(PS.text_color || "#73787F") }];
  f.appendChild(t); t.x = 40; t.y = 40;
  section.appendChild(f);
  f.x = relX; f.y = relY;
  return f.id;
}

/** Repeated shared states (generic Empty, Error, Loading) are not duplicated per screen.
 *  One copy lives on a shared page, and each screen's Default carries a reference annotation to it.
 *  Cross-page node hyperlinks (setRangeHyperlink NODE) are blocked, so a URL deep link is used. */
function commonRef(defaultFrame, fileKey, commonPageId, label) {
  const url = `https://www.figma.com/design/${fileKey}/?node-id=${String(commonPageId).replace(":", "-")}`;
  defaultFrame.annotations = [{ labelMarkdown: `${label || "empty / error / loading states"} → [shared page](${url})` }];
  return { mutatedNodeIds: [defaultFrame.id] };
}
