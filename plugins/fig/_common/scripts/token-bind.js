/* =============================================================================
 * token-bind.js — binds hand-typed colours to the design system's tokens (WRITES)
 *
 * The bind half of /fig:tokens. Its scan is audit-tokens.js with MODE "collect", and the check after it
 * is audit-tokens.js in its default mode. Its preview is this file with DRY_RUN; the real run follows
 * only the go to that preview, with the same MAPPING.
 *
 * Usage — the CFG line, the MAPPING line, optionally SECTION and DRY_RUN lines, then this file, to use_figma.
 *
 * Inputs
 *   CFG      naming.arrow_delimiter / label_prefix / state_chain_prefix and placeholder_style (the
 *            <scaffolding> block), pages.exclude_sections
 *   MAPPING  [{ hex, variableKey, nodes?, accept? }] — hex in collect's form ("#RRGGBB" where alpha is 1,
 *            "#RRGGBBAA" otherwise), variableKey one of the keys collect's dictionary lists. Several
 *            entries may share a hex: each paint takes the first entry that names its node and can be
 *            bound to it, so one colour can go to a fill token on fills and a text token on text.
 *            nodes: [ids] limits the entry to those nodes; without it, every node in scope. A node no
 *            entry for its colour names is neither bound nor reported.
 *            accept: true means the person saw, in the preview, that binding this entry changes what
 *            those nodes show — a near colour (grade 2), another opacity, or a token that renders another
 *            value in the mode a node is set to — and said go to that change, node by node. It needs
 *            nodes: an entry with accept and no nodes is rejected before anything is written, so a go
 *            never covers a node its preview did not list. Without accept, any such difference is skipped.
 *   SECTION  optional — that section and the sections nested in it; without it, the whole page
 *   DRY_RUN  optional — true writes nothing (a library token is still imported to be read; no node or
 *            paint changes) and returns what the same MAPPING would do, for the preview:
 *            { wouldBind: [{ node, name, kind, hex, variable, variableKey, change? }], skipped }
 *            one entry per paint that would bind — variable the token's name, change set where the
 *            screen would show something else there ("#3B66FF → #3366FF", "opacity 20% → 100%",
 *            "#FFFFFF → #1E1E1E (mode Dark)"), which happens only on an accepted node
 *
 * What it binds: exactly the colours audit-tokens.js reports — the <paint-scope> block, shared with it
 * byte for byte — whose colour and alpha equal a MAPPING hex. A fill, stroke or text colour is bound with
 * setBoundVariableForPaint, an effect colour with setBoundVariableForEffect; the node's array is rebuilt
 * and reassigned, every other entry left as it was. The paint's own opacity is left as Figma returns it.
 *
 * What it leaves, and returns in `skipped` with the reason — only for a colour, on a node, MAPPING names:
 *   - inside an instance, including overrides on its layers, and an instance's own paint on a property
 *     it does not override
 *   - working scaffolding (the <scaffolding> block)
 *   - a property applied through a style: binding it would detach the style. A text node whose style id
 *     is figma.mixed — part of it in a style — is left too, here only: the audit still reports it
 *   - a token that renders something else on that node than the colour it replaces — another RGB or
 *     alpha, read with resolveForConsumer, so in the node's own mode — unless the entry says accept:
 *     true. The reason names what it would render, and the mode where the node sets one. A token
 *     whose value cannot be read on the node counts as differing
 *   - a token whose `scopes` do not include the property the colour is on (ALL_SCOPES fits every one,
 *     and a token scoped to nothing — hidden from every picker — fits none)
 *   - a variableKey that is not a local colour variable and cannot be imported
 * Not read at all, as in the audit: hidden layers and what they hold, excluded sections, a section's or
 * component set's own paint, paints switched off, and paints already bound.
 *
 * Tokens: a local colour variable with that key is used as it is (an unpublished one cannot be
 * imported); any other is imported with importVariableByKeyAsync. Every one is found before the first write.
 *
 * Returns { bound, skipped } (DRY_RUN: { wouldBind, skipped }) — bound counts paints, as collect's
 *   `count` does; skipped is [{ node, reason, change?, variableKey? }], one per node and reason, the
 *   reason opening "<node name>: <kind> <hex> — ". change and variableKey are set where the skip is a
 *   visible difference that accept: true with that node would lift — the rows a preview asks about.
 *   MAPPING empty or malformed, accept without nodes, or SECTION not on the page → throws before
 *   anything is written. SECTION inside an excluded section → { bound: 0 (or wouldBind: []),
 *   skipped: [{ node: SECTION, reason }] }.
 * ========================================================================== */

const C = typeof CFG !== "undefined" ? CFG : {};
const P = C.pages || {};
const anyOf = a => (a && a.length ? new RegExp(a.join("|")) : null);
const SEC_EXCLUDE = anyOf(P.exclude_sections);
const skipSection = s => !!(SEC_EXCLUDE && SEC_EXCLUDE.test(s.name));

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

// ── MAPPING: colour key → its entries, in the order given ──
if (typeof MAPPING === "undefined" || !Array.isArray(MAPPING) || !MAPPING.length)
  throw new Error("MAPPING is a non-empty array of { hex, variableKey, nodes?, accept? }");
const DRY = typeof DRY_RUN !== "undefined" && DRY_RUN === true;
const keyOf = h => {
  const s = String(h == null ? "" : h).replace(/^#/, "").toUpperCase();
  if (!/^[0-9A-F]{6}([0-9A-F]{2})?$/.test(s)) throw new Error(`MAPPING hex "${h}" is not #RRGGBB or #RRGGBBAA`);
  return "#" + (s.length === 8 && s.endsWith("FF") ? s.slice(0, 6) : s);
};
const wanted = new Map();
for (const m of MAPPING) {
  if (!m || !m.variableKey) throw new Error(`MAPPING entry ${JSON.stringify(m)} has no variableKey`);
  const k = keyOf(m.hex), has = m.nodes !== undefined && m.nodes !== null;
  if (m.accept === true && !(Array.isArray(m.nodes) && m.nodes.length))
    throw new Error(`MAPPING entry for ${k} has accept: true but no nodes — accept covers only the nodes a preview listed, so name them`);
  if (has && !(Array.isArray(m.nodes) && m.nodes.length && m.nodes.every(x => typeof x === "string" && x)))
    throw new Error(`MAPPING entry for ${k}: nodes is a list of node ids`);
  if (!wanted.has(k)) wanted.set(k, []);
  wanted.get(k).push({ variableKey: String(m.variableKey), accept: m.accept === true, nodes: has ? new Set(m.nodes) : null });
}
// Whether an entry, or any entry for a colour, names this node.
const covers = (e, n) => !e.nodes || e.nodes.has(n.id);
const named = (n, key) => wanted.has(key) && wanted.get(key).some(e => covers(e, n));

// ── Scope, then the walk (reads only) ──
const page = figma.currentPage;
const allSecs = sectionsDeep(page.children, skipSection);
const scope = SEC ? scopeOf(allSecs) : null;
if (scope && scope.missing) throw new Error(`section ${SEC} is not on this page`);
if (scope && scope.excluded) {
  const skippedAll = [{ node: SEC, reason: `section ${SEC} is excluded by pages.exclude_sections; nothing bound` }];
  return DRY ? { wouldBind: [], skipped: skippedAll } : { bound: 0, skipped: skippedAll };
}

const skipped = [], skipSeen = new Set();
const skip = (n, c, why, extra) => {
  const reason = `${n.name}: ${c.kind} ${c.key} — ${why}`;
  if (!skipSeen.has(n.id + "\n" + reason)) { skipSeen.add(n.id + "\n" + reason); skipped.push({ node: n.id, reason, ...(extra || {}) }); }
};
const LEFT = {
  instance: "inside an instance, including overrides on its layers",
  scaffolding: "working scaffolding, not design",
  style: "applied through a style; binding it would detach the style",
};
// A text node in several styles reports figma.mixed as its style id. The audit counts that as no style
// (and reports the colour); the bind leaves it, since binding could detach the part that has one. This
// stays outside <paint-scope> so the audit does not change.
const STYLE_ID = { fills: "fillStyleId", strokes: "strokeStyleId", effects: "effectStyleId" };
const partStyled = (n, c) => n.type === "TEXT" && n[STYLE_ID[c.prop]] === figma.mixed;
const S = scaffoldingCfg(C);
const targets = [];   // { n, c }
for (const { n } of rootsOf(page, allSecs, scope ? scope.ids : null))
  walkColours(n, S, (m, c) => {
    if (!named(m, c.key)) return;
    if (partStyled(m, c)) skip(m, c, "part of this text uses a style; binding it could detach that part");
    else targets.push({ n: m, c });
  }, (m, c, why) => { if (named(m, c.key)) skip(m, c, LEFT[why]); });

// ── Every token the targets name, found before the first write ──
const local = new Map();
for (const v of await figma.variables.getLocalVariablesAsync("COLOR")) local.set(v.key, v);
const tokens = new Map();   // variableKey → { v } or { error }
for (const key of new Set(targets.flatMap(t => wanted.get(t.c.key).filter(e => covers(e, t.n)).map(e => e.variableKey)))) {
  if (local.has(key)) { tokens.set(key, { v: local.get(key) }); continue; }
  try {
    const v = await figma.variables.importVariableByKeyAsync(key);
    tokens.set(key, v && v.resolvedType === "COLOR" ? { v } : { error: `token ${key} is not a colour variable` });
  } catch (e) {
    tokens.set(key, { error: `token ${key} could not be imported (${e && e.message ? e.message : e})` });
  }
}

// The scopes a colour can be bound under, by the property it is on (Figma's VariableScope).
const FRAMELIKE = new Set(["FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"]);
const scopesFor = (n, kind) => kind === "stroke" ? ["STROKE_COLOR"] : kind === "effect" ? ["EFFECT_COLOR"]
  : kind === "text" ? ["TEXT_FILL", "ALL_FILLS"] : [FRAMELIKE.has(n.type) ? "FRAME_FILL" : "SHAPE_FILL", "ALL_FILLS"];
const fits = (v, n, kind) => !Array.isArray(v.scopes) || v.scopes.includes("ALL_SCOPES") || scopesFor(n, kind).some(s => v.scopes.includes(s));
// What the token renders on this node, keyed like a paint — in the node's own mode, aliases followed —
// or null where it cannot be read. The grade came from the collection's default mode; this is what the
// screen would show.
const renderedOn = (v, n) => {
  try {
    const r = v.resolveForConsumer(n), val = r && r.value;
    return val && typeof val.r === "number" ? colourKey(val, val.a) : null;
  } catch (e) { return null; }
};
const alphaOf = k => (k.length === 9 ? parseInt(k.slice(7), 16) : 255);
const pct = a => Math.round(a / 255 * 100) + "%";
// The name of the mode the node sets for the token's collection, where it sets one and it can be read.
const colCache = new Map();
const modeOn = async (v, n) => {
  const id = n.resolvedVariableModes ? n.resolvedVariableModes[v.variableCollectionId] : null;
  if (!id) return null;
  if (!colCache.has(v.variableCollectionId)) {
    let col = null;
    try { col = await figma.variables.getVariableCollectionByIdAsync(v.variableCollectionId); } catch (e) { col = null; }
    colCache.set(v.variableCollectionId, col);
  }
  const col = colCache.get(v.variableCollectionId), m = col && Array.isArray(col.modes) ? col.modes.find(x => x.modeId === id) : null;
  return m ? m.name : null;
};
const ACCEPT = " — binding changes what you see; accept: true binds it anyway";
const changeOn = async (v, n, rk, ck) => {
  if (rk === null) return `what token ${v.name} renders here could not be read, so the bind could change it; accept: true binds it anyway`;
  const mode = await modeOn(v, n), here = mode ? ` here (mode ${mode})` : " here";
  return (rk.slice(0, 7) === ck.slice(0, 7)
    ? `token ${v.name} is ${pct(alphaOf(rk))} opaque${here} and the colour ${pct(alphaOf(ck))}`
    : `token ${v.name} renders ${rk}${here}, not ${ck}`) + ACCEPT;
};
// The same difference, short, for the preview: "#3B66FF → #3366FF", "opacity 20% → 100%", plus the mode.
const changeText = async (v, n, rk, ck) => {
  if (rk === null) return "unknown — what the token renders here could not be read";
  const mode = await modeOn(v, n);
  return (rk.slice(0, 7) === ck.slice(0, 7) ? `opacity ${pct(alphaOf(ck))} → ${pct(alphaOf(rk))}` : `${ck} → ${rk}`)
    + (mode ? ` (mode ${mode})` : "");
};

// ── Choose a token per colour: the first entry that names the node and can be bound to it ──
const plan = new Map();   // node id → { n, props: Map(prop → [{ i, v }]) }
const wouldBind = [];
for (const { n, c } of targets) {
  let chosen = null, first = null;
  for (const e of wanted.get(c.key)) {
    if (!covers(e, n)) continue;
    const t = tokens.get(e.variableKey);
    if (t.error) { first = first || { why: t.error }; continue; }
    const v = t.v;
    if (!fits(v, n, c.kind)) { first = first || { why: `token ${v.name} is not scoped for ${c.kind} colours` }; continue; }
    const rk = renderedOn(v, n), change = rk === c.key ? null : await changeText(v, n, rk, c.key);
    if (change && !e.accept) {
      first = first || { why: await changeOn(v, n, rk, c.key), extra: { change, variableKey: e.variableKey } };
      continue;
    }
    chosen = v;
    wouldBind.push({ node: n.id, name: n.name, kind: c.kind, hex: c.key, variable: v.name, variableKey: e.variableKey, ...(change ? { change } : {}) });
    break;
  }
  if (!chosen) { skip(n, c, first.why, first.extra); continue; }
  if (!plan.has(n.id)) plan.set(n.id, { n, props: new Map() });
  const props = plan.get(n.id).props;
  if (!props.has(c.prop)) props.set(c.prop, []);
  props.get(c.prop).push({ i: c.i, v: chosen });
}

if (DRY) return { wouldBind, skipped };

// ── Write: rebuild each array and reassign it — a paint array is read-only in place ──
let bound = 0;
for (const { n, props } of plan.values())
  for (const [prop, list] of props) {
    const next = [...n[prop]];
    for (const { i, v } of list)
      next[i] = prop === "effects" ? figma.variables.setBoundVariableForEffect(next[i], "color", v)
                                   : figma.variables.setBoundVariableForPaint(next[i], "color", v);
    n[prop] = next;
    bound += list.length;
  }

return { bound, skipped };
