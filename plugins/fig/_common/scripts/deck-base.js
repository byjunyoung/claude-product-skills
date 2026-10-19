/* =====================================================================
 * DECK BASE — shared helpers for Figma Slides builds
 *
 * Put this file at the top of a build script, and below it the template.js that
 * the measuring step of /fig:deck (setup.md) produced (palette C · type T · layout constants · archetype builders).
 * The order has to be this way round — the functions here are declarations and hoist,
 * while C and T are read only at call time, so they may be defined below.
 *
 * **There are no values in this file.** Colours, sizes, and coordinates all belong to template.js.
 * Pin a value here and it leaks straight through into another team's template.
 *
 * What template.js has to define
 *   C     { bg, text, textMuted, cardSurface, ... }   colours in the 0–1 range
 *   T     { title, h1, h2, body1, ... }               {size, style, ls, lh}
 *   FAMS  ['<team font>', 'Inter']                    font candidates in order of preference
 *
 * The use_figma rules are baked in — appendChild before x/y, load the font before characters,
 * colours in 0–1, fills reassigned as a new array.
 * ===================================================================== */

function hx(h) {
  const n = parseInt(h.slice(1), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
}

/* ---- Fonts ------------------------------------------------------------
 * A cloud environment may not have the team font. Probe the candidates in order and use
 * whichever exists. Weight names differ per family (Inter says 'Semi Bold', most say
 * 'SemiBold'), so f() wraps that difference. */
let FAM = null;
async function loadFonts() {
  const avail = await figma.listAvailableFontsAsync();
  const fams = new Set(avail.map(a => a.fontName.family));
  const want = (typeof FAMS !== 'undefined' && FAMS.length) ? FAMS : ['Inter'];
  FAM = want.find(x => fams.has(x)) || (fams.has('Inter') ? 'Inter' : want[0]);
  const styles = FAM === 'Inter'
    ? ['Bold', 'Semi Bold', 'Medium', 'Regular']
    : ['Bold', 'SemiBold', 'Medium', 'Regular'];
  await Promise.all(styles.map(s => figma.loadFontAsync({ family: FAM, style: s }).catch(() => {})));
  return FAM;
}
function f(style) {
  if (FAM === 'Inter' && style === 'SemiBold') return { family: FAM, style: 'Semi Bold' };
  return { family: FAM, style: style };
}

/* ---- Binding named text styles ----------------------------------------
 * After the build, bind each TEXT to the file's named styles by family|style|size.
 * What cannot be found stays as a raw value — normal for sizes outside the scale, or
 * where a font was substituted. Colour is left alone (a text style carries type only). */
let _styleIdx = null;
async function applyTextStyles(root) {
  if (!_styleIdx) {
    _styleIdx = {};
    for (const s of await figma.getLocalTextStylesAsync()) {
      _styleIdx[`${s.fontName.family}|${s.fontName.style}|${s.fontSize}`] = s.id;
    }
  }
  const texts = root.type === 'TEXT' ? [root] : root.findAllWithCriteria({ types: ['TEXT'] });
  let bound = 0;
  for (const t of texts) {
    if (typeof t.fontName === 'symbol') continue;          // a run with mixed formatting
    const id = _styleIdx[`${t.fontName.family}|${t.fontName.style}|${t.fontSize}`];
    if (id && t.textStyleId !== id) { try { await t.setTextStyleIdAsync(id); bound++; } catch (e) {} }
  }
  return bound;
}

/* ---- Element helpers (appendChild → properties → x/y) ------------------
 * Change the order and the node shifts. Using the helpers forces the order. */

// Give it the id of a themed sample slide and it clones that to inherit the theme.
// Left empty, createSlide makes a bare slide — fonts and colours break into 'Pick a style'.
let REF_SLIDE = null;
function newSlide(bg) {
  let s;
  if (REF_SLIDE) {
    const ref = figma.getNodeById(REF_SLIDE);
    s = ref.clone();
    for (const c of [...s.children]) c.remove();
  } else {
    s = figma.createSlide();
  }
  s.fills = [{ type: 'SOLID', color: bg || C.bg }];
  return s;
}

function addText(parent, o) {
  const t = figma.createText(); parent.appendChild(t);
  const p = o.preset ? T[o.preset] : {};
  t.fontName = f(o.style || p.style || 'Regular');
  t.characters = o.chars || '';
  t.fontSize = o.size || p.size || 24;
  t.textAlignHorizontal = o.align || 'LEFT';
  t.fills = [{ type: 'SOLID', color: o.color || C.text, opacity: (o.fillOpacity != null ? o.fillOpacity : 1) }];
  const ls = (o.ls != null ? o.ls : p.ls); if (ls != null) t.letterSpacing = { unit: 'PERCENT', value: ls };
  const lh = (o.lh != null ? o.lh : p.lh); if (lh != null) t.lineHeight = { unit: 'PERCENT', value: lh };
  if (o.w) { t.textAutoResize = 'HEIGHT'; t.resize(o.w, t.height); }
  if (o.x != null) t.x = o.x; if (o.y != null) t.y = o.y;
  return t;
}

function addRect(parent, o) {
  const r = figma.createRectangle(); parent.appendChild(r);
  r.resize(o.w, o.h);
  r.fills = [{ type: 'SOLID', color: o.fill || C.cardSurface }];
  if (o.radius) r.cornerRadius = o.radius;
  if (o.x != null) r.x = o.x; if (o.y != null) r.y = o.y;
  return r;
}

// scaleMode 'FIT' does not crop (the default). 'FILL' crops — photographs and backgrounds only.
function addImageRect(parent, o) {
  const r = figma.createRectangle(); parent.appendChild(r);
  r.resize(o.w, o.h);
  if (o.radius) r.cornerRadius = o.radius;
  r.fills = o.imageHash
    ? [{ type: 'IMAGE', imageHash: o.imageHash, scaleMode: o.scaleMode || 'FIT' }]
    : [{ type: 'SOLID', color: C.cardSurface }];       // the slot before the image is ready
  if (o.x != null) r.x = o.x; if (o.y != null) r.y = o.y;
  return r;
}

function addLine(parent, o) {                            // hairlines and diagonal motifs. rot is in degrees
  const l = figma.createLine(); parent.appendChild(l);
  l.resize(o.len, 0);
  if (o.rot) l.rotation = o.rot;
  l.strokes = [{ type: 'SOLID', color: o.color || C.text }];
  l.strokeWeight = o.weight || 1;
  if (o.x != null) l.x = o.x; if (o.y != null) l.y = o.y;
  return l;
}

// text inside an auto-layout frame. layoutSizing directly under a slide throws
function alText(parent, o) {
  const t = addText(parent, o);
  if (o.fill) t.layoutSizingHorizontal = 'FILL';
  return t;
}

/* ---- Measurement ------------------------------------------------------
 * The basis for the auto-wrap check. A rendered line count greater than the manual
 * newline count means the typesetter is cutting mid-word. */
function renderedLines(t) {
  const lh = (t.lineHeight && t.lineHeight.unit === 'PERCENT') ? t.lineHeight.value / 100 : 1.2;
  return Math.round(t.height / (t.fontSize * lh));
}
function manualLines(t) {
  return typeof t.characters === 'string' ? t.characters.split('\n').length : 1;
}
function isWrapped(t) { return renderedLines(t) > manualLines(t); }

/* ---- Coordinates ------------------------------------------------------
 * A slide child's x/y is relative to its parent, not to the slide.
 * Writing a value read from absoluteBoundingBox as-is pushes it over by the slide's width. */
function relTo(slide, node) {
  const a = node.absoluteBoundingBox, s = slide.absoluteBoundingBox;
  return { x: a.x - s.x, y: a.y - s.y, w: a.width, h: a.height };
}
