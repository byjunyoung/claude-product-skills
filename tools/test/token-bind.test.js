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
const bind = (figma, MAPPING, { cfg = baseCfg(), SECTION, DRY_RUN } = {}) =>
  new AsyncFunction("CFG", "MAPPING", "SECTION", "DRY_RUN", "figma", '"use strict";\n' + BIND)(cfg, MAPPING, SECTION, DRY_RUN, figma);
const audit = (figma, { cfg = baseCfg(), SECTION, MODE } = {}) =>
  new AsyncFunction("CFG", "SECTION", "MODE", "figma", AUDIT)(cfg, SECTION, MODE, figma);

const boundTo = (p) => (p && p.boundVariables && p.boundVariables.color ? p.boundVariables.color.id : null);
// The skill's own path: a dry run, then the real run of the `mapping` it returned — the only way a real
// run gets an accepted entry, whose `paints` only a dry run can fill in.
const viaPreview = async (figma, MAPPING, opts = {}) =>
  bind(figma, (await bind(figma, MAPPING, { ...opts, DRY_RUN: true })).mapping, opts);

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
    { hex: "#3366FF33", variableKey: "key:primary", ...(accept ? { accept: true, nodes: ["id:Soft-Default", "id:Glow-Default"] } : {}) },
    { hex: "#3B66FF", variableKey: "key:primary", ...(accept ? { accept: true, nodes: ["id:Near-Default"] } : {}) },
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
  const loose = await viaPreview(fakeFigma(p2, lib), MAP(true));
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
  // The rows that render the same bind as they are; the accepted entry covers only the nodes it names.
  const accepted = await viaPreview(fakeFigma(p2, lib), [
    { hex: "#FFFFFF", variableKey: "key:surface" },
    { hex: "#FFFFFF", variableKey: "key:surface", accept: true, nodes: ["id:Dark-Default", "id:Card"] },
  ]);
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
  assert.deepStrictEqual(two.skipped.map((s) => s.reason), [
    "Rule: stroke #FFFFFF — token bg is not scoped for stroke colours",
    "Rule: stroke #FFFFFF — token on-primary is not scoped for stroke colours",
  ], "a paint neither entry can bind has a row for each token it tried");

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

test("accept: true without nodes is rejected before anything is written; nodes limit an entry to those ids", async () => {
  const page = () => [section("01. Home", [
    frame("Near-A", { fills: [solid("#3B66FF")] }),
    frame("Near-B", { fills: [solid("#3B66FF")] }),
    frame("Exact-A", { fills: [solid("#3366FF")] }),
    frame("Exact-B", { fills: [solid("#3366FF")] }),
  ])];

  const p1 = page();
  await assert.rejects(bind(fakeFigma(p1, LIB()), [{ hex: "#3366FF", variableKey: "key:primary" }, { hex: "#3B66FF", variableKey: "key:primary", accept: true }]),
    /MAPPING entry for #3B66FF has accept: true but no nodes/);
  await assert.rejects(bind(fakeFigma(p1, LIB()), [{ hex: "#3B66FF", variableKey: "key:primary", accept: true, nodes: [] }]), /accept: true but no nodes/);
  await assert.rejects(bind(fakeFigma(p1, LIB()), [{ hex: "#3B66FF", variableKey: "key:primary", accept: true }], { DRY_RUN: true }), /accept: true but no nodes/,
    "a dry run holds to the same rule");
  await assert.rejects(bind(fakeFigma(p1, LIB()), [{ hex: "#3366FF", variableKey: "key:primary", nodes: "id:Exact-A" }]), /nodes is a list of node ids/);
  assert.deepStrictEqual(p1[0].children.map((f) => boundTo(f.fills[0])), [null, null, null, null], "the rejected runs wrote nothing");

  // A real run takes an accepted entry only with the paints its dry run listed it for
  await assert.rejects(bind(fakeFigma(p1, LIB()), [{ hex: "#3B66FF", variableKey: "key:primary", accept: true, nodes: ["id:Near-A"] }]),
    /MAPPING entry for #3B66FF has accept: true but no paints/);
  assert.deepStrictEqual(p1[0].children.map((f) => boundTo(f.fills[0])), [null, null, null, null], "still nothing written");

  const p2 = page();
  const out = await viaPreview(fakeFigma(p2, LIB()), [
    { hex: "#3B66FF", variableKey: "key:primary", accept: true, nodes: ["id:Near-A"] },
    { hex: "#3366FF", variableKey: "key:primary", nodes: ["id:Exact-B"] },
  ]);
  assert.deepStrictEqual(out, { bound: 2, skipped: [] }, "a node no entry names is neither bound nor reported");
  assert.deepStrictEqual(p2[0].children.map((f) => boundTo(f.fills[0])), ["primary", null, null, "primary"]);
});

test("a dry run writes nothing and returns, per node, what would bind, what would change and what is skipped", async () => {
  const modal = { id: "c1", defaultModeId: "m1", modes: [{ modeId: "m1", name: "Light" }, { modeId: "dark", name: "Dark" }] };
  const lib = {
    vars: [colorVar("primary", { m1: value("#3366FF"), dark: value("#3366FF") }), colorVar("surface", { m1: value("#FFFFFF"), dark: value("#1E1E1E") })],
    local: ["primary", "surface"],
    collections: [modal],
  };
  const page = () => [section("01. Home", [
    frame("Home-Default", { fills: [solid("#FFFFFF")], strokes: [solid("#3366FF")] }, [
      node("RECTANGLE", "Near", { fills: [solid("#3B66FF")] }),
      node("INSTANCE", "Chip", { fills: [solid("#3366FF")] }),
    ]),
    frame("Dark-Default", { fills: [solid("#FFFFFF")], resolvedVariableModes: { c1: "dark" } }),
  ])];
  const first = [
    { hex: "#FFFFFF", variableKey: "key:surface" },
    { hex: "#3366FF", variableKey: "key:primary" },
    { hex: "#3B66FF", variableKey: "key:primary" },
  ];

  // 1. The plain mapping: what binds as it is, and what would change if accepted
  const p1 = page();
  const dry = await bind(fakeFigma(p1, lib), first, { DRY_RUN: true });
  assert.deepStrictEqual(Object.keys(dry).sort(), ["mapping", "paints", "skipped", "unchecked", "wouldBind"]);
  assert.deepStrictEqual(dry.unchecked, [], "every token here is local");
  assert.deepStrictEqual(dry.wouldBind, [
    { node: "id:Home-Default", name: "Home-Default", kind: "fill", hex: "#FFFFFF", variable: "surface", variableKey: "key:surface" },
    { node: "id:Home-Default", name: "Home-Default", kind: "stroke", hex: "#3366FF", variable: "primary", variableKey: "key:primary" },
  ]);
  const changes = dry.skipped.filter((s) => s.change);
  assert.deepStrictEqual(changes.map((s) => [s.node, s.variableKey, s.change]), [
    ["id:Near", "key:primary", "#3B66FF → #3366FF"],
    ["id:Dark-Default", "key:surface", "#FFFFFF → #1E1E1E (mode Dark)"],
  ]);
  assert.match(dry.skipped.find((s) => s.node === "id:Chip").reason, /inside an instance/);
  assert.strictEqual(dry.skipped.find((s) => s.node === "id:Chip").change, undefined, "a skip accept cannot lift carries no change");
  assert.deepStrictEqual([p1[0].children[0].fills[0], p1[0].children[0].strokes[0], p1[0].children[1].fills[0]].map(boundTo), [null, null, null],
    "nothing written");

  // 2. The mapping the person said go to: accepted rows name their nodes, and the dry run shows each change
  const final = [...first, { hex: "#3B66FF", variableKey: "key:primary", accept: true, nodes: ["id:Near"] }];
  const p2 = page();
  const preview = await bind(fakeFigma(p2, lib), final, { DRY_RUN: true });
  assert.deepStrictEqual(preview.wouldBind.find((w) => w.node === "id:Near"),
    { node: "id:Near", name: "Near", kind: "fill", hex: "#3B66FF", variable: "primary", variableKey: "key:primary", change: "#3B66FF → #3366FF" });
  assert.ok(preview.skipped.some((s) => s.node === "id:Dark-Default"), "the mode node was not accepted, so it stays skipped");

  // 3. The real run of that preview's mapping writes exactly what it listed
  const real = await bind(fakeFigma(p2, lib), preview.mapping);
  assert.strictEqual(real.bound, preview.wouldBind.length);
  assert.deepStrictEqual(real.skipped, preview.skipped);
  assert.deepStrictEqual(["Home-Default", "Near", "Dark-Default"].map((n) => boundTo(find(p2, n).fills[0])), ["surface", "primary", null]);

  // An opacity change reads as one
  const p3 = [section("01. Home", [frame("Soft-Default", { fills: [solid("#3366FF", { opacity: 0.2 })] })])];
  const soft = await bind(fakeFigma(p3, lib), [{ hex: "#3366FF33", variableKey: "key:primary" }], { DRY_RUN: true });
  assert.deepStrictEqual(soft.skipped.map((s) => s.change), ["opacity 20% → 100%"]);
});

test("a dry run never imports", async () => {
  const C2 = { id: "c2", defaultModeId: "light" };
  const lib = {
    vars: [
      colorVar("primary", { m1: value("#3366FF") }),                                       // local
      colorVar("lib-ink", { light: value("#111111") }, { variableCollectionId: "c2" }),   // a library token bound on the page
      colorVar("lib-red", { m1: value("#FF0000") }),                                       // a library token nowhere in the file yet
    ],
    local: ["primary"],
    published: ["lib-ink", "lib-red"],
    collections: [C1, C2],
  };
  const page = [section("01. Home", [
    frame("Home-Default", { fills: [solid("#3366FF")] }, [
      node("TEXT", "Ink", { fills: [{ ...solid("#111111"), boundVariables: { color: alias("lib-ink") } }] }),
      node("TEXT", "Body", { fills: [solid("#111111")] }),
      node("RECTANGLE", "Alert", { fills: [solid("#FF0000")] }),
      node("RECTANGLE", "Alert 2", { strokes: [solid("#FF0000")] }),
    ]),
  ])];
  const figma = fakeFigma(page, lib);
  const MAPPING = [
    { hex: "#3366FF", variableKey: "key:primary" },
    { hex: "#111111", variableKey: "key:lib-ink" },
    { hex: "#FF0000", variableKey: "key:lib-red" },
  ];
  const dry = await bind(figma, MAPPING, { DRY_RUN: true });
  assert.deepStrictEqual(figma.imports, [], "nothing imported — the file is as it was");
  assert.deepStrictEqual(dry.wouldBind.map((w) => [w.node, w.variable]), [["id:Home-Default", "primary"], ["id:Body", "lib-ink"]],
    "a library token already bound on the page is read without importing it");
  assert.deepStrictEqual(dry.unchecked, [{ variableKey: "key:lib-red", nodes: ["id:Alert", "id:Alert 2"] }]);
  assert.deepStrictEqual(dry.skipped, []);
  assert.deepStrictEqual(["Home-Default", "Body", "Alert"].map((n) => boundTo(find(page, n).fills[0])), [null, null, null]);

  const real = await bind(figma, MAPPING);
  assert.deepStrictEqual(figma.imports, ["key:lib-ink", "key:lib-red"], "the real run imports every non-local token, as before");
  assert.deepStrictEqual(real, { bound: 4, skipped: [] });
});

test("the real run still skips a mode difference for a token the dry run could not check", async () => {
  const modal = { id: "c1", defaultModeId: "m1", modes: [{ modeId: "m1", name: "Light" }, { modeId: "dark", name: "Dark" }] };
  const lib = { vars: [colorVar("lib-surface", { m1: value("#FFFFFF"), dark: value("#1E1E1E") })], local: [], published: ["lib-surface"], collections: [modal] };
  const page = [section("01. Home", [
    frame("Light-Default", { fills: [solid("#FFFFFF")] }),
    frame("Dark-Default", { fills: [solid("#FFFFFF")], resolvedVariableModes: { c1: "dark" } }),
  ])];
  const figma = fakeFigma(page, lib);
  const MAPPING = [{ hex: "#FFFFFF", variableKey: "key:lib-surface" }];

  const dry = await bind(figma, MAPPING, { DRY_RUN: true });
  assert.deepStrictEqual(dry.wouldBind, []);
  assert.deepStrictEqual(dry.skipped, []);
  assert.deepStrictEqual(dry.unchecked, [{ variableKey: "key:lib-surface", nodes: ["id:Light-Default", "id:Dark-Default"] }]);
  assert.deepStrictEqual(dry.paints.map((p) => [p.node, p.candidates]), [
    ["id:Light-Default", [{ variableKey: "key:lib-surface", status: "unchecked" }]],
    ["id:Dark-Default", [{ variableKey: "key:lib-surface", status: "unchecked" }]],
  ]);
  assert.deepStrictEqual(figma.imports, []);

  const real = await bind(figma, MAPPING);
  assert.strictEqual(real.bound, 1);
  assert.deepStrictEqual(["Light-Default", "Dark-Default"].map((n) => boundTo(find(page, n).fills[0])), ["lib-surface", null]);
  assert.deepStrictEqual(real.skipped.map((s) => [s.node, s.change]), [["id:Dark-Default", "#FFFFFF → #1E1E1E (mode Dark)"]]);
  assert.match(real.skipped[0].reason, /renders #1E1E1E here \(mode Dark\), not #FFFFFF — binding changes what you see/);

  // Now the token is in the file, a dry run can check the node, and accepting it goes through the usual gate
  const again = await bind(figma, [...MAPPING, { hex: "#FFFFFF", variableKey: "key:lib-surface", accept: true, nodes: ["id:Dark-Default"] }], { DRY_RUN: true });
  assert.deepStrictEqual(again.unchecked, []);
  assert.deepStrictEqual(again.wouldBind.map((w) => [w.node, w.change]), [["id:Dark-Default", "#FFFFFF → #1E1E1E (mode Dark)"]]);
});

test("a dry run shows every token a paint tries, in order, past one it cannot check yet", async () => {
  // Two entries for one colour, the first a library text token nobody in the file has bound yet
  const lib = {
    vars: [
      colorVar("lib-text", { m1: value("#111111") }, { scopes: ["TEXT_FILL"] }),
      colorVar("fill", { m1: value("#111111") }, { scopes: ["FRAME_FILL", "SHAPE_FILL"] }),
    ],
    local: ["fill"],
    published: ["lib-text"],
  };
  const page = [section("01. Home", [node("TEXT", "Label", { fills: [solid("#111111")] }), frame("Card", { fills: [solid("#111111")] })])];
  const figma = fakeFigma(page, lib);
  const MAPPING = [{ hex: "#111111", variableKey: "key:lib-text" }, { hex: "#111111", variableKey: "key:fill" }];

  const dry = await bind(figma, MAPPING, { DRY_RUN: true });
  assert.deepStrictEqual(figma.imports, [], "still no import");
  assert.deepStrictEqual(dry.paints, [
    { node: "id:Label", name: "Label", kind: "text", hex: "#111111", candidates: [
      { variableKey: "key:lib-text", status: "unchecked" },
      { variableKey: "key:fill", variable: "fill", status: "skip", reason: "token fill is not scoped for text colours" },
    ] },
    { node: "id:Card", name: "Card", kind: "fill", hex: "#111111", candidates: [
      { variableKey: "key:lib-text", status: "unchecked" },
      { variableKey: "key:fill", variable: "fill", status: "bind" },
    ] },
  ], "Card's fallback to fill is in the preview, behind the token that cannot be read yet");
  assert.deepStrictEqual(dry.wouldBind, [], "neither paint is settled until lib-text is read");
  assert.deepStrictEqual(dry.skipped, []);
  assert.deepStrictEqual(dry.unchecked, [{ variableKey: "key:lib-text", nodes: ["id:Label", "id:Card"] }]);
  assert.deepStrictEqual(dry.mapping, [
    { hex: "#111111", variableKey: "key:lib-text", nodes: ["id:Label", "id:Card"] },
    { hex: "#111111", variableKey: "key:fill", nodes: ["id:Label", "id:Card"] },
  ]);
  assert.deepStrictEqual(["Label", "Card"].map((n) => boundTo(find(page, n).fills[0])), [null, null], "nothing written");

  const real = await bind(figma, dry.mapping);
  assert.deepStrictEqual(real, { bound: 2, skipped: [] });
  assert.deepStrictEqual(["Label", "Card"].map((n) => boundTo(find(page, n).fills[0])), ["lib-text", "fill"],
    "Label takes the text token; Card, which it does not fit, falls to fill — the order the preview showed");
});

test("DRY_RUN is true or false: anything else throws before the file is read", async () => {
  const page = [section("01. Home", [frame("Home-Default", { fills: [solid("#3366FF")] }), node("RECTANGLE", "Alert", { fills: [solid("#FF0000")] })])];
  const figma = fakeFigma(page, LIB());
  let reads = 0;
  const watched = new Proxy(figma, { get: (t, k) => { reads++; return t[k]; } });
  const MAPPING = [{ hex: "#3366FF", variableKey: "key:primary" }, { hex: "#FF0000", variableKey: "key:lib-red" }];
  for (const bad of ["true", 1, null])
    await assert.rejects(bind(watched, MAPPING, { DRY_RUN: bad }), /DRY_RUN is true or false/, `DRY_RUN = ${JSON.stringify(bad)}`);
  assert.strictEqual(reads, 0, "the file is not read");
  assert.deepStrictEqual(figma.imports, []);
  assert.deepStrictEqual(["Home-Default", "Alert"].map((n) => boundTo(find(page, n).fills[0])), [null, null], "nothing written");

  assert.strictEqual((await bind(figma, MAPPING, { DRY_RUN: false })).bound, 2, "false is the real run, as no DRY_RUN is");
});

test("the real run takes the dry run's mapping, so a frame added after the preview is left alone", async () => {
  const page = () => [section("01. Home", [
    frame("Home-Default", { fills: [solid("#3366FF")] }, [
      node("INSTANCE", "Chip", { fills: [solid("#3366FF")] }),
      frame("Styled", { fills: [solid("#3366FF")], fillStyleId: "S:1" }),
    ]),
  ])];
  const added = () => frame("Added-Default", { fills: [solid("#3366FF")] });
  const MAPPING = [{ hex: "#3366FF", variableKey: "key:primary" }, { hex: "#FF0000", variableKey: "key:lib-red" }];

  const p1 = page();
  const figma = fakeFigma(p1, LIB());
  const dry = await bind(figma, MAPPING, { DRY_RUN: true });
  assert.deepStrictEqual(dry.mapping.map((e) => ({ ...e, nodes: [...e.nodes].sort() })),
    [{ hex: "#3366FF", variableKey: "key:primary", nodes: ["id:Chip", "id:Home-Default", "id:Styled"] }],
    "a plain entry names its nodes too, the ones it leaves included; an entry that listed none is left out");

  p1[0].children.push(added());   // drawn after the preview
  const real = await bind(figma, dry.mapping);
  assert.strictEqual(real.bound, dry.wouldBind.length);
  assert.deepStrictEqual(real.skipped, dry.skipped, "what it leaves is still reported, as the preview said");
  assert.deepStrictEqual(["Home-Default", "Added-Default"].map((n) => boundTo(find(p1, n).fills[0])), ["primary", null]);

  // The same MAPPING without nodes would have bound it
  const p2 = page();
  p2[0].children.push(added());
  await bind(fakeFigma(p2, LIB()), MAPPING);
  assert.strictEqual(boundTo(find(p2, "Added-Default").fills[0]), "primary");
});

test("a paint no token can bind reports every token it tried, and each change accept could lift", async () => {
  const lib = {
    vars: [
      colorVar("ink", { m1: value("#3B66FF") }, { scopes: ["TEXT_FILL"] }),   // the very colour, for text only
      colorVar("primary", { m1: value("#3366FF") }),                         // fits, and renders a near colour
    ],
    local: ["ink", "primary"],
  };
  const page = () => [section("01. Home", [node("RECTANGLE", "Near", { fills: [solid("#3B66FF")] })])];
  const MAPPING = [{ hex: "#3B66FF", variableKey: "key:ink" }, { hex: "#3B66FF", variableKey: "key:primary" }];
  const both = [
    { node: "id:Near", reason: "Near: fill #3B66FF — token ink is not scoped for fill colours" },
    { node: "id:Near", reason: "Near: fill #3B66FF — token primary renders #3366FF here, not #3B66FF — binding changes what you see; accept: true binds it anyway",
      change: "#3B66FF → #3366FF", variableKey: "key:primary" },
  ];

  const p1 = page();
  const dry = await bind(fakeFigma(p1, lib), MAPPING, { DRY_RUN: true });
  assert.deepStrictEqual(dry.skipped, both);
  assert.deepStrictEqual(dry.paints[0].candidates.map((c) => [c.variableKey, c.status, c.change]),
    [["key:ink", "skip", undefined], ["key:primary", "skip", "#3B66FF → #3366FF"]]);
  assert.deepStrictEqual(await bind(fakeFigma(p1, lib), MAPPING), { bound: 0, skipped: both });

  // The later token's change, once accepted on that node, binds
  const p2 = page();
  const accepted = await viaPreview(fakeFigma(p2, lib), [...MAPPING, { hex: "#3B66FF", variableKey: "key:primary", accept: true, nodes: ["id:Near"] }]);
  assert.deepStrictEqual(accepted, { bound: 1, skipped: [] });
  assert.strictEqual(boundTo(find(p2, "Near").fills[0]), "primary");
});

test("a token that cannot be imported is reported, and an accepted change binds only the paints its preview showed it on", async () => {
  // libfill is a library token bound elsewhere on the page, so a dry run reads it; the editor cannot import it
  const lib = {
    vars: [
      colorVar("libfill", { m1: value("#3B66FF") }, { scopes: ["SHAPE_FILL"] }),
      colorVar("primary", { m1: value("#3366FF") }),
    ],
    local: ["primary"],
    published: [],
  };
  const page = [section("01. Home", [
    node("RECTANGLE", "Ref", { fills: [{ ...solid("#3B66FF"), boundVariables: { color: alias("libfill") } }] }),
    node("RECTANGLE", "Badge", { fills: [solid("#3B66FF")], strokes: [solid("#3B66FF")] }),
  ])];
  const figma = fakeFigma(page, lib);
  const MAPPING = [
    { hex: "#3B66FF", variableKey: "key:libfill" },
    { hex: "#3B66FF", variableKey: "key:primary" },
    { hex: "#3B66FF", variableKey: "key:primary", accept: true, nodes: ["id:Badge"] },
  ];

  const dry = await bind(figma, MAPPING, { DRY_RUN: true });
  assert.deepStrictEqual(dry.paints.map((p) => [p.kind, p.candidates]), [
    ["fill", [{ variableKey: "key:libfill", variable: "libfill", status: "bind" }]],
    ["stroke", [
      { variableKey: "key:libfill", variable: "libfill", status: "skip", reason: "token libfill is not scoped for stroke colours" },
      { variableKey: "key:primary", variable: "primary", status: "skip",
        reason: "token primary renders #3366FF here, not #3B66FF — binding changes what you see; accept: true binds it anyway", change: "#3B66FF → #3366FF" },
      { variableKey: "key:primary", accept: true, variable: "primary", status: "bind", change: "#3B66FF → #3366FF" },
    ]],
  ], "a candidate says when its entry is an accepted one");
  assert.deepStrictEqual(dry.mapping, [
    { hex: "#3B66FF", variableKey: "key:libfill", nodes: ["id:Badge"] },
    { hex: "#3B66FF", variableKey: "key:primary", nodes: ["id:Badge"] },
    { hex: "#3B66FF", variableKey: "key:primary", nodes: ["id:Badge"], accept: true, paints: [{ node: "id:Badge", prop: "strokes", index: 0 }] },
  ], "the accepted entry carries the one paint the preview showed it binding");

  const real = await bind(figma, dry.mapping);
  assert.deepStrictEqual(figma.imports, ["key:libfill"]);
  const failed = "token key:libfill could not be imported (no published variable with key key:libfill)";
  assert.deepStrictEqual(real, {
    bound: 1,
    skipped: [
      { node: "id:Badge", reason: `Badge: fill #3B66FF — ${failed}` },
      { node: "id:Badge", reason: "Badge: fill #3B66FF — token primary renders #3366FF here, not #3B66FF — binding changes what you see; accept: true binds it anyway",
        change: "#3B66FF → #3366FF", variableKey: "key:primary" },
      { node: "id:Badge", reason: `Badge: stroke #3B66FF — ${failed}` },
    ],
  }, "the fill never takes the change accepted for the stroke; every import failure is named, the stroke's too");
  const badge = find(page, "Badge");
  assert.deepStrictEqual([boundTo(badge.fills[0]), boundTo(badge.strokes[0])], [null, "primary"], "the stroke binds as previewed");
});

test("a plain exact fallback after an import failure still binds, and the failure is still reported", async () => {
  const lib = {
    vars: [colorVar("lib-ink", { m1: value("#111111") }), colorVar("ink", { m1: value("#111111") })],
    local: ["ink"],
    published: [],                                                                  // lib-ink cannot be imported
  };
  const page = [section("01. Home", [node("TEXT", "Body", { fills: [solid("#111111")] })])];
  const figma = fakeFigma(page, lib);
  const dry = await bind(figma, [{ hex: "#111111", variableKey: "key:lib-ink" }, { hex: "#111111", variableKey: "key:ink" }], { DRY_RUN: true });
  assert.deepStrictEqual(dry.paints[0].candidates, [
    { variableKey: "key:lib-ink", status: "unchecked" },
    { variableKey: "key:ink", variable: "ink", status: "bind" },
  ]);

  const real = await bind(figma, dry.mapping);
  assert.deepStrictEqual(real, {
    bound: 1,
    skipped: [{ node: "id:Body", reason: "Body: text #111111 — token key:lib-ink could not be imported (no published variable with key key:lib-ink)" }],
  });
  assert.strictEqual(boundTo(find(page, "Body").fills[0]), "ink");
});
