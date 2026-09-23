/* =============================================================================
 * audit-struct.js — structural audit (read-only, zero writes)
 *
 * Checks: frame membership · out of bounds · frame overlap · section overlap · naming
 *         · variant stacking · library sibling overlap · implicit variable mode
 *         · clipped or overflowing content
 *
 * Usage
 *   1) python3 scripts/lib/resolve-config.py --js <fileKey>   → `const CFG = {...};`
 *   2) prepend that one line to this file and hand it to use_figma
 *   3) for another page, one setCurrentPageAsync line at the top (once per script)
 *
 * Returns: an array of violation strings, or "STRUCT PASS"
 *
 * A null pattern skips that check — it keeps a file with no convention from reporting everything.
 * Coordinate and parent checks always run regardless of config (geometry holds with or without a rule).
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const N = C.naming || {}, P = C.pages || {};

const reOrNull = s => (s ? new RegExp(s) : null);
const anyOf = a => (a && a.length ? new RegExp(a.join("|")) : null);

const NAME_RE = reOrNull(N.frame_pattern);
const SEC_RE = reOrNull(N.section_pattern);
const SEC_EXCLUDE = anyOf(P.exclude_sections);
const LABEL = N.label_prefix || "[label] ";

const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));
const isScreen = n => n.type === "FRAME" && !n.name.startsWith(LABEL);
const r = v => Math.round(v);

const issues = [];
const secs = figma.currentPage.children.filter(c => c.type === "SECTION");

// A screen frame sitting directly on the page = the absorb step was missed.
// clone() and createFrame default their parent to currentPage, so anything not absorbed leaks out here.
for (const f of figma.currentPage.children)
  if (isScreen(f))
    issues.push(`[membership] directly on page (not absorbed into a section): ${f.name} @abs ${r(f.x)},${r(f.y)}`);

for (const s of secs) {
  if (skipSection(s)) continue;
  const frames = s.children.filter(isScreen);

  for (const f of frames) {
    // Out of bounds — a section child's x/y is relative to the section.
    // Write an absolute coordinate there and the frame shoots outside the section.
    if (f.x < 0 || f.y < 0 || f.x + f.width > s.width || f.y + f.height > s.height)
      issues.push(`[bounds] ${s.name} / ${f.name} outside (rel ${r(f.x)},${r(f.y)} ${r(f.width)}x${r(f.height)} vs section ${r(s.width)}x${r(s.height)})`);
    if (NAME_RE && !NAME_RE.test(f.name))
      issues.push(`[naming] ${s.name} / ${f.name} (pattern mismatch)`);
  }

  for (let i = 0; i < frames.length; i++)
    for (let j = i + 1; j < frames.length; j++) {
      const a = frames[i], b = frames[j];
      if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
        issues.push(`[frame overlap] ${s.name}: ${a.name} ∩ ${b.name}`);
    }

  if (SEC_RE && !SEC_RE.test(s.name))
    issues.push(`[naming] section ${s.name} (pattern mismatch)`);
}

// Section overlap — an excluded section on either side is dropped from the check
for (let i = 0; i < secs.length; i++)
  for (let j = i + 1; j < secs.length; j++) {
    const a = secs[i], b = secs[j];
    if (skipSection(a) || skipSection(b)) continue;
    if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
      issues.push(`[section overlap] ${a.name} ∩ ${b.name}`);
  }

// ── Ordering mismatch — does the NN. number agree with the canvas order (row-major) ──
// Protected number ranges are never reassigned, so they are not checked either.
const BUCKET = (C.layout || {}).row_bucket || 1000;
const PROT = P.protected_numbers || [];
const numbered = secs
  .filter(s => !skipSection(s) && /^\d+\./.test(s.name) && !PROT.some(p => s.name.startsWith(p)))
  .sort((a, b) => (Math.round(a.y / BUCKET) - Math.round(b.y / BUCKET)) || (a.x - b.x));
numbered.forEach((s, i) => {
  const want = String(i + 1).padStart(2, "0");
  const have = s.name.match(/^(\d+)\./)[1];
  if (have !== want) issues.push(`[order] ${s.name} → ${want}. (${i + 1} on canvas)`);
});

// ── Split state variants — are one screen's variants broken apart within a column ──
// A transition result (a modal, a dialog) wedged between the parent screen and its variant
// gets crossed by the [state] dashed line, which is straight. Catching it at the placement
// stage is what keeps the arrow stage clean.
const screenOf = n => n.replace(/-[^-]+$/, "");     // [screen name] with the trailing suffix removed
for (const s of secs) {
  if (skipSection(s)) continue;
  const frames = s.children.filter(isScreen)
    .map(f => ({ name: f.name, screen: screenOf(f.name), x: f.x, y: f.y, b: f.y + f.height }));
  const byScreen = {};
  for (const f of frames) (byScreen[f.screen] = byScreen[f.screen] || []).push(f);
  for (const [screen, group] of Object.entries(byScreen)) {
    if (group.length < 2) continue;
    // Only compare within one column (close in x) — a different column is not a [state] target at all
    const cols = {};
    for (const f of group) { const k = Math.round(f.x / 8); (cols[k] = cols[k] || []).push(f); }
    for (const col of Object.values(cols)) {
      if (col.length < 2) continue;
      col.sort((a, b) => a.y - b.y);
      for (let i = 1; i < col.length; i++) {
        const top = col[i - 1].b, bot = col[i].y;
        const intruder = frames.find(o =>
          o.screen !== screen && Math.abs(o.x - col[i].x) < 8 && o.y >= top && o.y < bot);
        if (intruder)
          issues.push(`[split state] ${s.name}: ${intruder.name} is wedged between ${col[i - 1].name} and ${col[i].name}`);
      }
    }
  }
}

// ── Variant stacking — a component set whose variants sit on top of one another ──
// A variant added to a set with no layout lands on the last one's coordinates, and the set then
// reads as a single component: three states look like one. It survives review because nothing
// about it looks broken — the top variant renders fine and the ones beneath it are simply gone.
// An auto-layout set places every new variant on its own, which is why the note points there.
for (const cs of figma.currentPage.findAllWithCriteria({ types: ["COMPONENT_SET"] })) {
  const v = cs.children;
  let hit = null;
  for (let i = 0; i < v.length && !hit; i++)
    for (let j = i + 1; j < v.length && !hit; j++) {
      const a = v[i], b = v[j];
      if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
        hit = `${a.name} ∩ ${b.name}`;
    }
  if (hit)
    issues.push(`[variant stack] ${cs.name}: ${hit}${cs.layoutMode === "NONE" ? " (set has no auto-layout)" : ""}`);
}

// ── Library sibling overlap — a set or component covering the one placed beside it ──
// Frame overlap above only looks at frames, so a library page passes it while its components
// sit on top of each other. A set that grows — one variant more, a layout applied — runs past
// the gap it was placed with and buries its neighbour.
const isLib = c => c.type === "COMPONENT_SET" || c.type === "COMPONENT";
for (const s of secs) {
  if (skipSection(s)) continue;
  const kids = s.children.filter(isLib);
  for (let i = 0; i < kids.length; i++)
    for (let j = i + 1; j < kids.length; j++) {
      const a = kids[i], b = kids[j];
      if (a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y)
        issues.push(`[library overlap] ${s.name}: ${a.name} ∩ ${b.name}`);
    }
}

// ── Default layer names — layers still carrying Figma's auto-generated name ──
// "Frame 427" tells the next person nothing. It is not wrong, it is unread — the file can only be
// navigated by whoever drew it. Layers inside a component instance are the library's, not this
// page's: they cannot be renamed here, so they are excluded and belong to the source library.
const DEFAULT_NAME = /^(Frame|Group|Rectangle|Ellipse|Vector|Line|Polygon|Star|Slice|Component|Union|Subtract|Intersect|Exclude|Image|Arrow)( \d+)?$/;
const inInstance = n => {
  for (let a = n.parent; a && a.type !== "PAGE"; a = a.parent) if (a.type === "INSTANCE") return true;
  return false;
};
for (const s of secs) {
  if (skipSection(s)) continue;
  for (const f of s.children.filter(isScreen)) {
    const hits = f.findAll(n => DEFAULT_NAME.test(n.name) && !inInstance(n));
    if (hits.length)
      issues.push(`[layer name] ${s.name} / ${f.name}: ${hits.length} on Figma defaults (${hits.slice(0, 3).map(n => n.name).join(", ")}${hits.length > 3 ? ", \u2026" : ""})`);
  }
}

// ── Implicit variable mode — a screen whose colours resolve in a mode nobody chose ──
// A screen bound to a collection with several modes (light/dark, brand A/B) renders in whatever
// mode its nearest ancestor sets — itself, its section, its page — and in the collection default
// where none does. Clone a screen that looked light only because its old page or parent set the
// mode, land it somewhere that does not, and it comes back in the default: bound colours flip and
// anything hand-typed for the old mode vanishes. Nothing about the node looks wrong; only a render
// shows it, and a check that compares it with its siblings misses the case where every screen on
// the page was cloned the same way. So the rule is per screen: bind to a multi-mode collection,
// and some ancestor has to name the mode — even where the default is what it wants, because an
// explicit default survives the next move.
const colCache = {}, varCache = {};
const collectionOf = async id => {
  if (!(id in varCache)) varCache[id] = await figma.variables.getVariableByIdAsync(id);
  const v = varCache[id];
  if (!v) return null;
  if (!(v.variableCollectionId in colCache))
    colCache[v.variableCollectionId] = await figma.variables.getVariableCollectionByIdAsync(v.variableCollectionId);
  return colCache[v.variableCollectionId];
};
const boundIds = n => {
  const ids = [];
  for (const k of ["fills", "strokes"]) {
    const ps = n[k];
    if (Array.isArray(ps)) for (const p of ps) if (p.boundVariables && p.boundVariables.color) ids.push(p.boundVariables.color.id);
  }
  return ids;
};
for (const s of secs) {
  if (skipSection(s)) continue;
  for (const f of s.children.filter(isScreen)) {
    const ids = new Set(boundIds(f));
    f.findAll(n => { for (const id of boundIds(n)) ids.add(id); return false; });
    const named = new Set([f, s, figma.currentPage].flatMap(n => Object.keys(("explicitVariableModes" in n && n.explicitVariableModes) || {})));
    const unset = {};
    for (const id of ids) {
      const col = await collectionOf(id);
      if (!col || col.modes.length < 2 || named.has(col.id)) continue;
      const u = unset[col.id] = unset[col.id] || { col, n: 0 };
      u.n++;
    }
    for (const { col, n } of Object.values(unset)) {
      const def = (col.modes.find(m => m.modeId === col.defaultModeId) || {}).name || "default";
      issues.push(`[mode] ${s.name} / ${f.name}: ${n} colour(s) bound to "${col.name}" with no mode set on the screen, its section or the page — renders in the default (${def})`);
    }
  }
}

// ── Clipped and overflowing content — a control cut by its own box, or hanging off the screen ──
// A 28px button inside a cell whose padding leaves 12px, a floating button placed past the frame's
// bottom edge: both come across intact from a canonical screen, both look like a rendering glitch
// in the file, and neither trips a placement check, because every frame is where it should be.
// What is measured is painted content — text, and anything with a visible fill or stroke — so an
// empty wrapper wider than its parent is not reported: nothing of it can be seen being cut. Layout
// boxes, not render bounds, because render bounds come back already clipped and hide the cut.
// Only a clipping box a component defines — a cell, a slot, a field — is judged for cuts. A frame
// the screen clips itself is how a scrolling list, a carousel track or a cropped image is drawn,
// and nothing on the node tells those apart from an accident, so they are left alone.
const painted = n => n.type === "TEXT" ||
  ["fills", "strokes"].some(k => Array.isArray(n[k]) && n[k].some(p => p.visible !== false && (p.opacity == null || p.opacity > 0)));
const union = (a, b) => !a ? b : !b ? a : (() => {
  const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
  return { x, y, width: Math.max(a.x + a.width, b.x + b.width) - x, height: Math.max(a.y + a.height, b.y + b.height) - y };
})();
const contentBox = n => {
  if (!n.visible) return null;
  if (painted(n) || !("children" in n)) return painted(n) ? n.absoluteBoundingBox : null;
  let u = null;
  for (const c of n.children) u = union(u, contentBox(c));
  return u;
};
const inComponent = n => { for (let a = n; a && a.type !== "PAGE"; a = a.parent) if (a.type === "INSTANCE") return true; return false; };
const past = (b, p) => Math.max(p.x - b.x, b.x + b.width - p.x - p.width, p.y - b.y, b.y + b.height - p.y - p.height);
for (const s of secs) {
  if (skipSection(s)) continue;
  for (const f of s.children.filter(isScreen)) {
    const fbox = f.absoluteBoundingBox;
    const hits = [];
    const walk = (n, clippedBelow) => {
      if (!n.visible) return;
      if (n !== f && !clippedBelow && painted(n) && past(n.absoluteBoundingBox, fbox) > 2)
        hits.push(`${n.name} hangs off the screen`);
      if (n !== f && n.clipsContent && "children" in n && inComponent(n)) {
        const p = n.absoluteBoundingBox;
        for (const c of n.children) {
          const cb = contentBox(c);
          if (cb && cb.width <= p.width * 3 && past(cb, p) > 2) hits.push(`${c.name} cut ${Math.round(past(cb, p))}px by ${n.name}`);
        }
      }
      if ("children" in n) for (const c of n.children) walk(c, clippedBelow || (n !== f && n.clipsContent));
    };
    walk(f, false);
    if (hits.length)
      issues.push(`[clip] ${s.name} / ${f.name}: ${hits.length} (${hits.slice(0, 3).join("; ")}${hits.length > 3 ? ", \u2026" : ""})`);
  }
}

return issues.length ? issues : "STRUCT PASS";
