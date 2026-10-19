/* Fixtures for token-bind.js — the bind half of /fig:tokens.
 *
 *     node --test tools/test/
 *
 * The script reads `CFG`, `MAPPING`, `SECTION` and `figma` globals, writes, and returns
 * `{ bound, skipped }`. The fakes follow audit-tokens.test.js and the Plugin API's own shapes:
 * `setBoundVariableForPaint` / `setBoundVariableForEffect` return a new paint or effect bound to the
 * variable, `importVariableByKeyAsync` finds a published variable by key, and a variable resolves on a
 * node through `resolveForConsumer`. The audit runs on the same fake tree afterwards, so a bind that
 * strays from what the audit reports shows up as a finding.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const DIR = join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts");
const BIND = readFileSync(join(DIR, "token-bind.js"), "utf8");
const AUDIT = readFileSync(join(DIR, "audit-tokens.js"), "utf8");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const MIXED = Symbol("figma.mixed");

const baseCfg = () => ({
  naming: { arrow_delimiter: " --> ", label_prefix: "[label] ", state_chain_prefix: "[state] ", state_chain_delimiter: " ~ " },
  section_style: { fill: "#6B7280", stroke: "#6B7280" },
  placeholder_style: { fill: "#FAFAFB", stroke: "#B3B3BF", dash: [10, 8] },
  pages: { exclude_sections: ["^Template$"] },
  design_system: { match_threshold_channel: 8 },
});

// ── Paints ──
const rgb = (h) => ({ r: parseInt(h.slice(1, 3), 16) / 255, g: parseInt(h.slice(3, 5), 16) / 255, b: parseInt(h.slice(5, 7), 16) / 255 });
const alias = (id) => ({ type: "VARIABLE_ALIAS", id });
const solid = (h, more = {}) => ({ type: "SOLID", color: rgb(h), opacity: 1, visible: true, ...more });
const shadow = (h, a = 1, more = {}) => ({ type: "DROP_SHADOW", visible: true, color: { ...rgb(h), a }, offset: { x: 0, y: 2 }, radius: 4, spread: 0, ...more });

// ── Nodes (ids are "id:" + name). Paint arrays and the paints in them are frozen ──
const deepFreeze = (x) => {
  if (x && typeof x === "object" && !Object.isFrozen(x)) { Object.freeze(x); for (const v of Object.values(x)) deepFreeze(v); }
  return x;
};
const node = (type, name, props = {}, children = []) => {
  const n = { type, id: "id:" + name, name, fills: [], strokes: [], effects: [], ...props, children };
  for (const k of ["fills", "strokes", "effects"]) if (Array.isArray(n[k])) deepFreeze(n[k]);
  return n;
};
const frame = (name, props, children) => node("FRAME", name, props, children);
const section = (name, children, props = {}) => node("SECTION", name, { x: 0, y: 0, width: 4000, height: 4000, ...props }, children);
const find = (nodes, name) => {
  for (const n of nodes) {
    if (n.name === name) return n;
    const hit = n.children && find(n.children, name);
    if (hit) return hit;
  }
  return null;
};

// ── Variables ──
const value = (h, a = 1) => ({ ...rgb(h), a });
const C1 = { id: "c1", defaultModeId: "m1" };
const colorVar = (id, valuesByMode, more = {}) =>
  ({ id, key: "key:" + id, name: id, resolvedType: "COLOR", variableCollectionId: "c1", valuesByMode, ...more });

// A fake figma whose variables resolve on a node through resolveForConsumer — in the mode the node's
// resolvedVariableModes names for that collection, else the default, aliases followed — and whose
// binding helpers return a new paint or effect bound to the variable.
const fakeFigma = (pageChildren, { vars = [], local = [], published = [], collections = [C1] } = {}) => {
  const byId = (id) => vars.find((v) => v.id === id) || null;
  const resolve = (v, consumer, seen = new Set()) => {
    if (!v || seen.has(v.id)) return null;
    seen.add(v.id);
    const col = collections.find((c) => c.id === v.variableCollectionId);
    const modes = (consumer && consumer.resolvedVariableModes) || {};
    const val = col ? v.valuesByMode[modes[col.id] || col.defaultModeId] : Object.values(v.valuesByMode)[0];
    return val && val.type === "VARIABLE_ALIAS" ? resolve(byId(val.id), consumer, seen) : val;
  };
  for (const v of vars) v.resolveForConsumer = (n) => ({ value: resolve(v, n), resolvedType: "COLOR" });
  const imports = [];
  return {
    mixed: MIXED,
    imports,
    currentPage: { type: "PAGE", name: "[UI] Fixture", children: pageChildren },
    variables: {
      getLocalVariablesAsync: async (type) => vars.filter((v) => local.includes(v.id) && (type == null || v.resolvedType === type)),
      getVariableByIdAsync: async (id) => byId(id),
      getVariableCollectionByIdAsync: async (id) => collections.find((c) => c.id === id) || null,
      importVariableByKeyAsync: async (key) => {
        imports.push(key);
        const v = vars.find((x) => x.key === key && published.includes(x.id));
        if (!v) throw new Error(`no published variable with key ${key}`);
        return v;
      },
      setBoundVariableForPaint: (paint, field, v) => ({ ...paint, boundVariables: { ...(paint.boundVariables || {}), [field]: alias(v.id) } }),
      setBoundVariableForEffect: (effect, field, v) => ({ ...effect, boundVariables: { ...(effect.boundVariables || {}), [field]: alias(v.id) } }),
    },
  };
};

// Strict mode, with every fixture paint and paint array frozen (see node()): a write into either in
// place throws instead of passing quietly, so "rebuilt and reassigned, never edited" is asserted directly.
const bind = (figma, MAPPING, { cfg = baseCfg(), SECTION } = {}) =>
  new AsyncFunction("CFG", "MAPPING", "SECTION", "figma", '"use strict";\n' + BIND)(cfg, MAPPING, SECTION, figma);
const audit = (figma, { cfg = baseCfg(), SECTION, MODE } = {}) =>
  new AsyncFunction("CFG", "SECTION", "MODE", "figma", AUDIT)(cfg, SECTION, MODE, figma);

const boundTo = (p) => (p && p.boundVariables && p.boundVariables.color ? p.boundVariables.color.id : null);

// One local token (#3366FF), one library token only importable by key (#FF0000).
const LIB = () => ({
  vars: [colorVar("primary", { m1: value("#3366FF") }), colorVar("lib-red", { m1: value("#FF0000") })],
  local: ["primary"],
  published: ["lib-red"],
});

test("token-bind binds exact mapped hexes on editable nodes and rebuilds the paint array", async () => {
  const gradient = { type: "GRADIENT_LINEAR", visible: true, gradientStops: [] };
  const off = solid("#3366FF", { visible: false });
  const page = [section("01. Home", [
    frame("Home-Default", { fills: [gradient, solid("#3366FF"), off], strokes: [solid("#3366FF")] }, [
      node("TEXT", "Title", { fills: [solid("#3366FF")] }),
      node("RECTANGLE", "Near", { fills: [solid("#3B66FF")] }),                         // not mapped: untouched
      node("RECTANGLE", "Alert", { fills: [solid("#FF0000")] }),                        // the library token
      frame("Card", { effects: [shadow("#3366FF"), { type: "LAYER_BLUR", visible: true, radius: 4 }] }),
    ]),
  ])];
  const home = page[0].children[0];
  const before = { fills: home.fills, near: find(page, "Near").fills, effects: find(page, "Card").effects };
  const figma = fakeFigma(page, LIB());

  const out = await bind(figma, [{ hex: "#3366FF", variableKey: "key:primary" }, { hex: "#FF0000", variableKey: "key:lib-red" }]);
  assert.deepStrictEqual(out, { bound: 5, skipped: [] }, "fill, stroke, text, effect and the library fill — paints, not nodes");

  assert.notStrictEqual(home.fills, before.fills, "the paint array is rebuilt and reassigned, never edited in place");
  assert.strictEqual(home.fills.length, 3);
  assert.strictEqual(home.fills[0], gradient, "a gradient in the same array is left as it was");
  assert.strictEqual(boundTo(home.fills[1]), "primary");
  assert.strictEqual(home.fills[2], off, "a paint switched off is left as it was");
  assert.strictEqual(boundTo(home.strokes[0]), "primary");
  assert.strictEqual(boundTo(find(page, "Title").fills[0]), "primary");
  assert.strictEqual(find(page, "Near").fills, before.near, "a node with no mapped colour keeps its array");
  assert.strictEqual(boundTo(find(page, "Alert").fills[0]), "lib-red");
  const card = find(page, "Card");
  assert.notStrictEqual(card.effects, before.effects);
  assert.strictEqual(boundTo(card.effects[0]), "primary", "an effect colour is bound too");
  assert.strictEqual(card.effects[1], before.effects[1]);
  assert.deepStrictEqual(figma.imports, ["key:lib-red"], "a local token is used as it is; only the library one is imported");

  const after = await audit(figma);
  assert.deepStrictEqual(after.findings.map((f) => [f.node, f.grade]), [["id:Near", "warning"]], JSON.stringify(after));
});

test("skips instances and scaffolding and says why", async () => {
  const blue = () => [solid("#3366FF")];
  const page = [
    section("01. Home", [
      frame("Home-Default", {}, [
        node("INSTANCE", "Button", { fills: blue() }, [node("TEXT", "Button label", { fills: blue() })]),
        node("INSTANCE", "Override", { fills: blue(), overrides: [{ id: "id:Override", overriddenFields: ["fills"] }] }),
        frame("Styled", { fills: blue(), fillStyleId: "S:fill,1:2" }),
        frame("Hidden", { fills: blue(), visible: false }),
        node("RECTANGLE", "Red", { fills: [solid("#FF0000")] }, []),                    // in no mapping
      ]),
      node("VECTOR", "Home-Default --> Detail-Default", { strokes: blue() }),
      frame("[label] Home-Default --> Detail-Default", { fills: blue() }, [node("TEXT", "Pill text", { fills: blue() })]),
      frame("Home-Empty", { fills: [solid("#FAFAFB")], strokes: [solid("#B3B3BF")], dashPattern: [10, 8] }, [
        node("TEXT", "Placeholder caption", { fills: blue() }),
      ]),
    ], { fills: blue() }),
    section("Template", [frame("Tpl-Default", { fills: blue() })]),
  ];
  const untouched = ["Button", "Button label", "Styled", "Hidden", "Red", "Pill text", "Placeholder caption", "Tpl-Default"]
    .map((n) => [n, find(page, n).fills]);
  const arrowStrokes = find(page, "Home-Default --> Detail-Default").strokes;
  const sectionFills = page[0].fills;
  const figma = fakeFigma(page, LIB());

  const out = await bind(figma, [{ hex: "#3366FF", variableKey: "key:primary" }]);
  assert.strictEqual(out.bound, 1, "only the instance's own overridden fill: " + JSON.stringify(out));
  assert.strictEqual(boundTo(find(page, "Override").fills[0]), "primary");
  for (const [n, fills] of untouched) assert.strictEqual(find(page, n).fills, fills, `${n} keeps its array`);
  assert.strictEqual(find(page, "Home-Default --> Detail-Default").strokes, arrowStrokes);
  assert.strictEqual(page[0].fills, sectionFills, "a section's own paint is never touched");

  const why = Object.fromEntries(out.skipped.map((s) => [s.node, s.reason]));
  assert.deepStrictEqual(Object.keys(why).sort(), [
    "id:Button", "id:Button label", "id:Home-Default --> Detail-Default", "id:Pill text",
    "id:Placeholder caption", "id:Styled", "id:[label] Home-Default --> Detail-Default",
  ].sort(), JSON.stringify(out.skipped, null, 1));
  assert.match(why["id:Button"], /^Button: fill #3366FF — inside an instance/);
  assert.match(why["id:Button label"], /text #3366FF — inside an instance/);
  assert.match(why["id:Home-Default --> Detail-Default"], /stroke #3366FF — working scaffolding/);
  assert.match(why["id:Placeholder caption"], /working scaffolding/);
  assert.match(why["id:Styled"], /applied through a style/);
});

test("a visible change — colour or opacity — is skipped unless the entry accepts it", async () => {
  const lib = {
    vars: [colorVar("primary", { m1: value("#3366FF") }), colorVar("scrim", { m1: value("#000000", 0.5) })],
    local: ["primary", "scrim"],
  };
  const page = () => [section("01. Home", [
    frame("Soft-Default", { fills: [solid("#3366FF", { opacity: 0.2 })] }),            // #3366FF33 against an opaque token
    frame("Scrim-Default", { fills: [solid("#000000", { opacity: 0.5 })] }),           // RGBA agrees
    frame("Glow-Default", { effects: [shadow("#3366FF", 0.2)] }),
    frame("Near-Default", { fills: [solid("#3B66FF")] }),                              // grade 2: a colour change
  ])];
  const MAP = (accept) => [
    { hex: "#3366FF33", variableKey: "key:primary", ...(accept ? { accept: true } : {}) },
    { hex: "#3B66FF", variableKey: "key:primary", ...(accept ? { accept: true } : {}) },
    { hex: "#00000080", variableKey: "key:scrim" },
  ];

  const p1 = page();
  const strict = await bind(fakeFigma(p1, lib), MAP(false));
  assert.strictEqual(strict.bound, 1, JSON.stringify(strict));
  assert.strictEqual(boundTo(find(p1, "Scrim-Default").fills[0]), "scrim");
  assert.strictEqual(boundTo(find(p1, "Soft-Default").fills[0]), null);
  assert.deepStrictEqual(strict.skipped.map((s) => s.node), ["id:Soft-Default", "id:Glow-Default", "id:Near-Default"]);
  for (const s of strict.skipped.slice(0, 2))
    assert.match(s.reason, /token primary is 100% opaque here and the colour 20% — binding changes what you see; accept: true binds it anyway/, s.reason);
  assert.match(strict.skipped[2].reason, /^Near-Default: fill #3B66FF — token primary renders #3366FF here, not #3B66FF — binding changes what you see/);

  const p2 = page();
  const loose = await bind(fakeFigma(p2, lib), MAP(true));
  assert.deepStrictEqual(loose, { bound: 4, skipped: [] });
  assert.strictEqual(boundTo(find(p2, "Glow-Default").effects[0]), "primary");
  assert.strictEqual(boundTo(find(p2, "Near-Default").fills[0]), "primary");

  // A token whose value cannot be read on the node counts as differing.
  const p3 = page();
  const blind = fakeFigma(p3, lib);
  for (const v of lib.vars) v.resolveForConsumer = () => { throw new Error("no access"); };
  const out = await bind(blind, [{ hex: "#00000080", variableKey: "key:scrim" }]);
  assert.strictEqual(out.bound, 0);
  assert.match(out.skipped[0].reason, /what token scrim renders here could not be read, so the bind could change it; accept: true/);
});

test("a token that renders another colour in a node's mode is skipped there, and bound elsewhere", async () => {
  const modal = { id: "c1", defaultModeId: "m1", modes: [{ modeId: "m1", name: "Light" }, { modeId: "dark", name: "Dark" }] };
  const lib = { vars: [colorVar("surface", { m1: value("#FFFFFF"), dark: value("#1E1E1E") })], local: ["surface"], collections: [modal] };
  const dark = { resolvedVariableModes: { c1: "dark" } };
  const page = () => [section("01. Home", [
    frame("Light-Default", { fills: [solid("#FFFFFF")] }),
    frame("Dark-Default", { fills: [solid("#FFFFFF")], ...dark }, [node("RECTANGLE", "Card", { fills: [solid("#FFFFFF")], ...dark })]),
    frame("Default-Mode", { fills: [solid("#FFFFFF")], resolvedVariableModes: { c1: "m1" } }),   // set, and to the default
  ])];

  const p1 = page();
  const out = await bind(fakeFigma(p1, lib), [{ hex: "#FFFFFF", variableKey: "key:surface" }]);
  assert.strictEqual(out.bound, 2, JSON.stringify(out));
  assert.deepStrictEqual(["Light-Default", "Dark-Default", "Card", "Default-Mode"].map((n) => boundTo(find(p1, n).fills[0])),
    ["surface", null, null, "surface"]);
  assert.deepStrictEqual(out.skipped.map((s) => s.node), ["id:Dark-Default", "id:Card"]);
  for (const s of out.skipped)
    assert.match(s.reason, /fill #FFFFFF — token surface renders #1E1E1E here \(mode Dark\), not #FFFFFF — binding changes what you see; accept: true binds it anyway/, s.reason);

  const p2 = page();
  const accepted = await bind(fakeFigma(p2, lib), [{ hex: "#FFFFFF", variableKey: "key:surface", accept: true }]);
  assert.deepStrictEqual(accepted, { bound: 4, skipped: [] });
});

test("text with part of it in a style is left alone, and the audit still reports it", async () => {
  const page = [section("01. Home", [
    node("TEXT", "Mixed", { fills: [solid("#3366FF")], fillStyleId: MIXED }),
    node("TEXT", "Plain", { fills: [solid("#3366FF")] }),
    node("TEXT", "Outlined", { strokes: [solid("#3366FF")], strokeStyleId: MIXED }),
  ])];
  const figma = fakeFigma(page, LIB());
  const out = await bind(figma, [{ hex: "#3366FF", variableKey: "key:primary" }]);
  assert.strictEqual(out.bound, 1, JSON.stringify(out));
  assert.strictEqual(boundTo(find(page, "Plain").fills[0]), "primary");
  assert.deepStrictEqual(out.skipped.map((s) => s.node), ["id:Mixed", "id:Outlined"]);
  assert.match(out.skipped[0].reason, /^Mixed: text #3366FF — part of this text uses a style/);
  const after = await audit(figma);
  assert.deepStrictEqual(after.findings.map((f) => f.node), ["id:Mixed", "id:Outlined"], "the shared paint scope is unchanged");
});

test("a token is bound only to a property its scopes allow", async () => {
  const lib = {
    vars: [
      colorVar("bg", { m1: value("#FFFFFF") }, { scopes: ["FRAME_FILL", "SHAPE_FILL"] }),
      colorVar("on-primary", { m1: value("#FFFFFF") }, { scopes: ["TEXT_FILL"] }),
      colorVar("raw-white", { m1: value("#FFFFFF") }, { scopes: [] }),                 // a primitive, hidden from every picker
    ],
    local: ["bg", "on-primary", "raw-white"],
  };
  const page = () => [section("01. Home", [frame("Home-Default", { fills: [solid("#FFFFFF")] }, [
    node("TEXT", "Label", { fills: [solid("#FFFFFF")] }),
    node("RECTANGLE", "Rule", { strokes: [solid("#FFFFFF")] }),
  ])])];

  const p1 = page();
  const one = await bind(fakeFigma(p1, lib), [{ hex: "#FFFFFF", variableKey: "key:bg" }]);
  assert.strictEqual(one.bound, 1);
  assert.strictEqual(boundTo(p1[0].children[0].fills[0]), "bg");
  assert.deepStrictEqual(one.skipped.map((s) => s.node), ["id:Label", "id:Rule"]);
  assert.match(one.skipped[0].reason, /token bg is not scoped for text colours/);

  // Two entries for one colour: each paint takes the first whose scope fits.
  const p2 = page();
  const two = await bind(fakeFigma(p2, lib), [{ hex: "#FFFFFF", variableKey: "key:bg" }, { hex: "#FFFFFF", variableKey: "key:on-primary" }]);
  assert.strictEqual(two.bound, 2);
  assert.strictEqual(boundTo(find(p2, "Label").fills[0]), "on-primary");
  assert.deepStrictEqual(two.skipped.map((s) => s.node), ["id:Rule"]);

  const p3 = page();
  const none = await bind(fakeFigma(p3, lib), [{ hex: "#FFFFFF", variableKey: "key:raw-white" }]);
  assert.strictEqual(none.bound, 0);
  assert.match(none.skipped[0].reason, /token raw-white is not scoped for fill colours/);
});

test("a token that cannot be imported is skipped, and the rest of the mapping still binds", async () => {
  const page = [section("01. Home", [frame("Home-Default", { fills: [solid("#3366FF")] }), frame("Red-Default", { fills: [solid("#FF0000")] })])];
  const fills = page[0].children.map((f) => f.fills);
  const out = await bind(fakeFigma(page, LIB()), [{ hex: "#3366FF", variableKey: "key:gone" }, { hex: "#FF0000", variableKey: "key:lib-red" }]);
  assert.strictEqual(out.bound, 1);
  assert.deepStrictEqual(out.skipped.map((s) => s.node), ["id:Home-Default"]);
  assert.match(out.skipped[0].reason, /token key:gone could not be imported/);
  assert.strictEqual(page[0].children[0].fills, fills[0]);
});

test("SECTION narrows the bind; a missing one throws before writing; an excluded one binds nothing", async () => {
  const blue = () => [solid("#3366FF")];
  const page = () => [
    section("01. Home", [frame("Home-Default", { fills: blue() }), section("01-1. Sub", [frame("Sub-Default", { fills: blue() })])]),
    section("02. Other", [frame("Other-Default", { fills: blue() })]),
    section("Template", [section("Inside template", [frame("T-Default", { fills: blue() })])]),
    frame("Loose-Default", { fills: blue() }),
  ];
  const MAP = [{ hex: "#3366FF", variableKey: "key:primary" }];

  const p1 = page();
  const one = await bind(fakeFigma(p1, LIB()), MAP, { SECTION: "id:01. Home" });
  assert.deepStrictEqual(one, { bound: 2, skipped: [] });
  assert.deepStrictEqual(["Home-Default", "Sub-Default", "Other-Default", "Loose-Default", "T-Default"].map((n) => boundTo(find(p1, n).fills[0])),
    ["primary", "primary", null, null, null]);

  const p2 = page();
  const whole = await bind(fakeFigma(p2, LIB()), MAP);
  assert.strictEqual(whole.bound, 4, "every section but the excluded one, and the frame loose on the page");

  const p3 = page();
  await assert.rejects(bind(fakeFigma(p3, LIB()), MAP, { SECTION: "id:nope" }), /section id:nope is not on this page/);
  assert.strictEqual(boundTo(find(p3, "Home-Default").fills[0]), null);

  const p4 = page();
  const excluded = await bind(fakeFigma(p4, LIB()), MAP, { SECTION: "id:Inside template" });
  assert.strictEqual(excluded.bound, 0);
  assert.match(excluded.skipped[0].reason, /excluded by pages\.exclude_sections/);

  await assert.rejects(bind(fakeFigma(page(), LIB()), []), /MAPPING/);
  await assert.rejects(bind(fakeFigma(page(), LIB()), [{ hex: "blue", variableKey: "key:primary" }]), /MAPPING hex "blue"/);
});

test("collect, bind the exact rows, audit: the counts agree and nothing exact is left", async () => {
  const C2 = { id: "c2", defaultModeId: "light" };
  const lib = {
    vars: [
      colorVar("primary", { m1: value("#3366FF") }),
      colorVar("scrim", { m1: value("#000000", 0.5) }),
      colorVar("lib-ink", { light: value("#111111") }, { variableCollectionId: "c2" }),
    ],
    local: ["primary", "scrim"],
    published: ["lib-ink"],
    collections: [C1, C2],
  };
  const page = [section("01. Home", [
    frame("Home-Default", { fills: [solid("#3366FF")], strokes: [solid("#3366FF")] }, [
      node("TEXT", "Body", { fills: [solid("#111111")] }),
      node("TEXT", "Ink", { fills: [{ ...solid("#111111"), boundVariables: { color: alias("lib-ink") } }] }),
      node("RECTANGLE", "Veil", { fills: [solid("#000000", { opacity: 0.5 })] }),
      node("RECTANGLE", "Shade", { fills: [solid("#000000")] }),                       // same RGB, other alpha: grade 2
      node("RECTANGLE", "Near", { fills: [solid("#3B66FF")] }),
      node("INSTANCE", "Chip", { fills: [solid("#3366FF")] }, [node("TEXT", "Chip label", { fills: [solid("#111111")] })]),
      frame("Styled", { fills: [solid("#3366FF")], fillStyleId: "S:1" }),
    ]),
  ])];
  const figma = fakeFigma(page, lib);

  const col = await audit(figma, { MODE: "collect" });
  const exact = col.unbound.filter((u) => u.grade === 1);
  assert.deepStrictEqual(exact.map((u) => u.hex).sort(), ["#00000080", "#111111", "#3366FF"]);
  const MAPPING = exact.map((u) => ({ hex: u.hex, variableKey: col.dictionary[u.nearest][0] }));
  const out = await bind(figma, MAPPING);
  assert.strictEqual(out.bound, exact.reduce((s, u) => s + u.count, 0), "bound counts paints, as collect's count does");

  const after = await audit(figma);
  assert.deepStrictEqual(after.findings.filter((f) => f.grade === "blocking"), [], JSON.stringify(after));
  assert.deepStrictEqual(after.findings.map((f) => f.node).sort(), ["id:Near", "id:Shade"]);
  // What the bind passed over is exactly what collect counted inside instances, plus the styled paint.
  assert.deepStrictEqual(out.skipped.map((s) => s.node).sort(), ["id:Chip", "id:Chip label", "id:Styled"]);
});
