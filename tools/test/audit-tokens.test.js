/* Fixtures for audit-tokens.js — colours left off the design system's tokens.
 *
 *     node --test tools/test/
 *
 * Same approach as the other audit tests: the script reads `CFG`, `SECTION`, `MODE` and `figma`
 * globals and returns its result. The fakes follow the Plugin API's own shapes — a bound paint
 * carries `boundVariables.color = { type: "VARIABLE_ALIAS", id }`, a variable resolves through its
 * collection's `defaultModeId`, a text node with several fills reports `figma.mixed`.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "audit-tokens.js"),
  "utf8"
);
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
const bound = (h, id) => solid(h, { boundVariables: { color: alias(id) } });

// ── Nodes (ids are "id:" + name, so names are unique within a fixture) ──
const node = (type, name, props = {}, children = []) =>
  ({ type, id: "id:" + name, name, fills: [], strokes: [], effects: [], ...props, children });
const frame = (name, props, children) => node("FRAME", name, props, children);
const section = (name, children, props = {}) => node("SECTION", name, { x: 0, y: 0, width: 4000, height: 4000, ...props }, children);

// ── Variables ──
const value = (h) => ({ ...rgb(h), a: 1 });
const colorVar = (id, valuesByMode, collection = "c1", more = {}) =>
  ({ id, key: "key:" + id, name: id, resolvedType: "COLOR", variableCollectionId: collection, valuesByMode, ...more });
const C1 = { id: "c1", defaultModeId: "m1" };

// One local colour token, #3366FF, and a local alias of it.
const LIB = {
  collections: [C1],
  vars: [colorVar("primary", { m1: value("#3366FF") }), colorVar("brand", { m1: alias("primary") })],
  local: ["primary", "brand"],
};

const fakeFigma = (pageChildren, { vars = [], local = [], collections = [] } = {}) => ({
  mixed: MIXED,
  currentPage: { type: "PAGE", name: "[UI] Fixture", children: pageChildren },
  variables: {
    getLocalVariablesAsync: async (type) => vars.filter((v) => local.includes(v.id) && (type == null || v.resolvedType === type)),
    getVariableByIdAsync: async (id) => vars.find((v) => v.id === id) || null,
    getVariableCollectionByIdAsync: async (id) => collections.find((c) => c.id === id) || null,
  },
});

const run = (pageChildren, lib = LIB, { cfg = baseCfg(), SECTION, MODE } = {}) =>
  new AsyncFunction("CFG", "SECTION", "MODE", "figma", SRC)(cfg, SECTION, MODE, fakeFigma(pageChildren, lib));

const ids = (out) => out.findings.map((f) => f.node);

test("exact-match unbound fill is blocking", async () => {
  const out = await run([section("01. Home", [frame("Home-Default", { fills: [solid("#3366FF")] })])]);
  assert.strictEqual(out.pass, false);
  assert.strictEqual(out.findings.length, 1, JSON.stringify(out));
  const f = out.findings[0];
  assert.strictEqual(f.tag, "[unbound]");
  assert.strictEqual(f.grade, "blocking");
  assert.strictEqual(f.node, "id:Home-Default");
  assert.match(f.msg, /^01\. Home \/ Home-Default: fill #3366FF/);
  assert.match(f.msg, /exact token/);
  assert.ok(!f.msg.startsWith("["), "the tag lives in `tag`, msg keeps the text only");
});

test("near and unmatched are warnings", async () => {
  const page = () => [section("01. Home", [
    frame("Near-Default", { fills: [solid("#3B66FF")] }),   // 8 off on one channel — at the threshold
    frame("Over-Default", { fills: [solid("#3C66FF")] }),   // 9 off — past it
    frame("Far-Default", { fills: [solid("#FF0000")] }),
  ])];
  const out = await run(page());
  assert.deepStrictEqual(ids(out), ["id:Near-Default", "id:Over-Default", "id:Far-Default"]);
  for (const f of out.findings) {
    assert.strictEqual(f.tag, "[unbound]");
    assert.strictEqual(f.grade, "warning", f.msg);
    assert.doesNotMatch(f.msg, /exact token/, "lint-grades tells the two [unbound] rows apart by these words");
  }
  const [near, over, far] = out.findings.map((f) => f.msg);
  assert.match(near, /near a token \(#3366FF, 8 off per channel\)/);
  assert.match(over, /no token within 8 per channel/);
  assert.match(far, /no token within 8 per channel/);

  // A null threshold counts exact matches only: the near colour is graded with the far ones.
  const cfg = baseCfg();
  cfg.design_system.match_threshold_channel = null;
  const strict = await run(page(), LIB, { cfg });
  assert.ok(strict.findings.every((f) => f.grade === "warning" && /no token within 0 per channel/.test(f.msg)), JSON.stringify(strict));
});

test("instance children, scaffolding, excluded sections and bound paints are not reported", async () => {
  const blue = () => [solid("#3366FF")];
  const page = [
    section("01. Home", [
      frame("Home-Default", { fills: [bound("#3366FF", "primary")] }, [            // bound: fine
        node("INSTANCE", "Button", { fills: blue(), overrides: [{ id: "id:Button", overriddenFields: ["fills"] }] }, [   // the instance overrides its own fill: that counts
          node("TEXT", "Button label", { fills: blue() }),                           // fixed at the component source
          frame("Icon slot", { strokes: blue() }, [node("VECTOR", "Glyph", { fills: blue() })]),
        ]),
        node("RECTANGLE", "Aliased", { fills: [bound("#3366FF", "brand")] }),       // bound through an alias: fine
      ]),
      node("VECTOR", "Home-Default --> Detail-Default", { strokes: blue() }),        // an arrow
      frame("[label] Home-Default --> Detail-Default", { fills: blue() }, [node("TEXT", "Pill text", { fills: blue() })]),
      node("VECTOR", "[state] Home-Default ~ Home-Empty", { strokes: blue() }),      // a state chain
      frame("Home-Empty", { fills: [solid("#FAFAFB")], strokes: [solid("#B3B3BF")], dashPattern: [10, 8] }, [
        node("TEXT", "Placeholder caption", { fills: blue() }),                      // a placeholder and its caption
      ]),
    ], { fills: blue(), strokes: blue() }),                                          // the section's own paints
    section("Template", [
      frame("Tpl-Default", { fills: blue() }),
      section("Nested in template", [frame("Deep-Default", { fills: blue() })]),
    ]),
    node("COMPONENT_SET", "Button set", { strokes: [solid("#9747FF")], dashPattern: [10, 5] }, [   // Figma's own frame round variants
      node("COMPONENT", "State=Default", { fills: blue() }),                          // a main component is editable: it counts
    ]),
  ];
  const out = await run(page);
  assert.deepStrictEqual(ids(out), ["id:Button", "id:State=Default"], JSON.stringify(out, null, 1));
  assert.deepStrictEqual(out.findings.map((f) => f.grade), ["blocking", "warning"], "the component set sits loose on the page, in no section");
});

test("gradient, image and mixed paints are ignored", async () => {
  const out = await run([section("01. Home", [
    frame("Home-Default", {
      fills: [
        { type: "GRADIENT_LINEAR", visible: true, gradientStops: [{ position: 0, color: value("#3366FF") }, { position: 1, color: value("#FF0000") }] },
        { type: "IMAGE", visible: true, imageHash: "abc", scaleMode: "FILL" },
        { type: "VIDEO", visible: true, videoHash: "def", scaleMode: "FILL" },
      ],
    }, [
      node("TEXT", "Two-colour text", { fills: MIXED }),
      node("RECTANGLE", "Hidden paint", { fills: [solid("#FF0000", { visible: false })] }),
    ]),
  ])]);
  assert.deepStrictEqual(out, { pass: true, findings: [] });
});

test("an unbound effect colour is reported", async () => {
  const out = await run([section("01. Home", [
    frame("Card-Default", {
      effects: [
        { type: "DROP_SHADOW", visible: true, color: value("#3366FF"), offset: { x: 0, y: 2 }, radius: 4, spread: 0 },
        { type: "INNER_SHADOW", visible: true, color: value("#3366FF"), offset: { x: 0, y: 1 }, radius: 2, spread: 0,
          boundVariables: { color: alias("primary") } },
        { type: "LAYER_BLUR", visible: true, radius: 4 },
      ],
    }),
    // The same colour at 20%: an effect's alpha is part of its colour, so this is near, never exact.
    frame("Soft-Default", { effects: [{ type: "DROP_SHADOW", visible: true, color: { ...rgb("#3366FF"), a: 0.2 }, offset: { x: 0, y: 2 }, radius: 4, spread: 0 }] }),
  ])]);
  assert.deepStrictEqual(out.findings.map((f) => [f.tag, f.grade, f.node]),
    [["[unbound]", "blocking", "id:Card-Default"], ["[unbound]", "warning", "id:Soft-Default"]], JSON.stringify(out));
  assert.match(out.findings[0].msg, /effect #3366FF —/);
  assert.match(out.findings[1].msg, /effect #3366FF33 — near a token \(#3366FF, 0 off per channel, opacity off by 80%\)/);
});

test("an opaque fill against a translucent token is not exact", async () => {
  const lib = { collections: [C1], vars: [colorVar("scrim", { m1: { ...rgb("#000000"), a: 0.5 } })], local: ["scrim"] };
  const page = [section("01. Home", [
    frame("Opaque-Default", { fills: [solid("#000000")] }),                          // same RGB, alpha 1 against 0.5
    frame("Scrim-Default", { fills: [solid("#000000", { opacity: 0.5 })] }),           // RGBA agrees
  ])];
  const out = await run(page, lib);
  assert.deepStrictEqual(out.findings.map((f) => [f.node, f.grade]), [["id:Opaque-Default", "warning"], ["id:Scrim-Default", "blocking"]], JSON.stringify(out));
  assert.match(out.findings[0].msg, /fill #000000 — near a token \(#00000080/);
  assert.match(out.findings[1].msg, /fill #00000080 — an exact token/);
  const col = await run(page, lib, { MODE: "collect" });
  assert.deepStrictEqual(col.dictionary, { "#00000080": [{ key: "key:scrim", scopes: null }] }, "alpha 1 writes #RRGGBB, anything else #RRGGBBAA");
  assert.deepStrictEqual(col.unbound.map((u) => [u.hex, u.grade, u.nearest]), [["#000000", 2, "#00000080"], ["#00000080", 1, "#00000080"]]);
});

test("paints and effects applied through a style are not reported", async () => {
  const blue = () => [solid("#3366FF")];
  const shadow = () => [{ type: "DROP_SHADOW", visible: true, color: value("#3366FF"), offset: { x: 0, y: 2 }, radius: 4, spread: 0 }];
  const out = await run([section("01. Home", [
    frame("Styled-Default", { fills: blue(), fillStyleId: "S:fill,1:2", strokes: blue(), strokeStyleId: "S:stroke,1:3", effects: shadow(), effectStyleId: "S:fx,1:4" }),
    frame("Half-Default", { fills: blue(), strokes: blue(), strokeStyleId: "S:stroke,1:3" }),          // the fill has no style: reported
    frame("Empty-Default", { fills: blue(), fillStyleId: "" }),                                        // an empty id is no style
    node("TEXT", "Mixed styles", { fills: blue(), fillStyleId: MIXED }),                              // figma.mixed is not a style id
  ])]);
  assert.deepStrictEqual(out.findings.map((f) => f.node), ["id:Half-Default", "id:Empty-Default", "id:Mixed styles"], JSON.stringify(out));
  assert.match(out.findings[0].msg, /: fill #3366FF/, "only the unstyled property is named");
});

test("an instance's own paint counts only where the instance overrides it", async () => {
  const blue = () => [solid("#3366FF")];
  const out = await run([section("01. Home", [
    node("INSTANCE", "Plain", { fills: blue() }),                                                       // the source's colour
    node("INSTANCE", "Child override", { fills: blue(), overrides: [{ id: "I:child", overriddenFields: ["fills"] }] }),
    node("INSTANCE", "Stroke override", { fills: blue(), strokes: blue(), overrides: [{ id: "id:Stroke override", overriddenFields: ["strokes"] }] }),
  ])]);
  assert.deepStrictEqual(out.findings.map((f) => f.node), ["id:Stroke override"], JSON.stringify(out));
  assert.match(out.findings[0].msg, /: stroke #3366FF/, "the fill it did not override is the component's");
});

test("hidden nodes and what they hold are not reported", async () => {
  const blue = () => [solid("#3366FF")];
  const out = await run([
    section("01. Home", [
      frame("Shown-Default", { fills: blue() }),
      frame("Hidden-Default", { fills: blue(), visible: false }, [node("RECTANGLE", "Inside hidden", { fills: blue() })]),
    ]),
    section("02. Hidden section", [frame("In hidden section", { fills: blue() }), section("Nested in hidden", [frame("Deeper", { fills: blue() })])], { visible: false }),
  ]);
  assert.deepStrictEqual(out.findings.map((f) => f.node), ["id:Shown-Default"], JSON.stringify(out));
});

test("a library token whose collection cannot be read is taken from the paint bound to it", async () => {
  // The variable is there, its collection lookup returns null: the bound paint's colour stands in.
  const lib = { collections: [], vars: [colorVar("lib-blue", { light: value("#3366FF") }, "c-lib")], local: [] };
  const page = [section("01. Home", [
    frame("Bound-Default", { fills: [bound("#3366FF", "lib-blue")] }),
    frame("Typed-Default", { fills: [solid("#3366FF")] }),
  ])];
  const out = await run(page, lib);
  assert.deepStrictEqual(out.findings.map((f) => [f.node, f.grade]), [["id:Typed-Default", "blocking"]], JSON.stringify(out));
  assert.strictEqual(out.note, undefined);
  const col = await run(page, lib, { MODE: "collect" });
  assert.deepStrictEqual(col.dictionary, { "#3366FF": [{ key: "key:lib-blue", scopes: null }] });
});

test("colour variables that all fail to resolve skip the check and say so", async () => {
  const lib = { collections: [], vars: [colorVar("a", { m1: value("#3366FF") }, "gone"), colorVar("b", { m1: value("#FF0000") }, "gone")], local: ["a", "b"] };
  const out = await run([section("01. Home", [frame("Home-Default", { fills: [solid("#3366FF")] })])], lib);
  assert.deepStrictEqual(out, { pass: true, findings: [], note: "2 colour variables found, none could be resolved; [unbound] skipped" });
});

test("no colour tokens → pass with note, no findings", async () => {
  const out = await run([section("01. Home", [
    frame("Home-Default", { fills: [solid("#FFFFFF")], strokes: [solid("#E5E7EB")] }, [node("TEXT", "Title", { fills: [solid("#111827")] })]),
  ])], { vars: [], local: [], collections: [] });
  assert.deepStrictEqual(out, { pass: true, findings: [], note: "no colour tokens found in this file; [unbound] skipped" });
});

test("collect mode returns the dictionary and graded aggregates", async () => {
  const C2 = { id: "c2", defaultModeId: "light" };
  const lib = {
    collections: [C1, C2],
    vars: [
      colorVar("primary", { m1: value("#3366FF") }),
      colorVar("surface", { m1: alias("lib-white") }),                              // an alias into another collection
      colorVar("lib-white", { light: value("#FFFFFF"), dark: value("#000000") }, "c2"),   // library: neither local nor bound
      colorVar("lib-ink", { light: value("#111111"), dark: value("#EEEEEE") }, "c2"),     // library: bound inside an instance only
      colorVar("broken", { m1: alias("gone") }),                                     // points at nothing
      colorVar("loop-a", { m1: alias("loop-b") }),
      colorVar("loop-b", { m1: alias("loop-a") }),
      { id: "spacing", key: "key:spacing", name: "spacing", resolvedType: "FLOAT", variableCollectionId: "c1", valuesByMode: { m1: 8 } },
    ],
    local: ["primary", "surface", "broken", "loop-a", "loop-b", "spacing"],
  };
  const page = [section("01. Home", [
    frame("Home-Default", { fills: [solid("#3366FF")] }, [
      node("RECTANGLE", "Divider", { fills: [solid("#3366FF")], strokes: [solid("#3366FF")] }),
      node("TEXT", "Body", { fills: [solid("#FAFAFA")] }),                            // 5 off #FFFFFF
      node("RECTANGLE", "Alert", { fills: [solid("#FF0000")] }),
      node("INSTANCE", "Avatar", {}, [node("ELLIPSE", "Ring", { strokes: [bound("#111111", "lib-ink")] })]),
    ]),
  ])];
  const out = await run(page, lib, { MODE: "collect" });
  assert.deepStrictEqual(out, {
    dictionary: {
      "#3366FF": [{ key: "key:primary", scopes: null }],
      "#FFFFFF": [{ key: "key:surface", scopes: null }],
      "#111111": [{ key: "key:lib-ink", scopes: null }],
    },
    unbound: [
      { hex: "#3366FF", kind: "fill", count: 2, nodes: ["id:Home-Default", "id:Divider"], grade: 1, nearest: "#3366FF", tokens: ["key:primary"] },
      { hex: "#3366FF", kind: "stroke", count: 1, nodes: ["id:Divider"], grade: 1, nearest: "#3366FF", tokens: ["key:primary"] },
      { hex: "#FAFAFA", kind: "text", count: 1, nodes: ["id:Body"], grade: 2, nearest: "#FFFFFF", tokens: ["key:surface"] },
      { hex: "#FF0000", kind: "fill", count: 1, nodes: ["id:Alert"], grade: 3, nearest: null, tokens: [] },
    ],
    inInstance: [],
    note: "3 colour variables could not be resolved to a colour and were left out of the dictionary",
  });
});

test("collect counts the colours held inside instances apart", async () => {
  const out = await run([section("01. Home", [
    frame("Home-Default", {}, [
      node("INSTANCE", "Chip", { fills: [solid("#3366FF")], strokes: [solid("#FF0000")], overrides: [{ id: "id:Chip", overriddenFields: ["strokes"] }] }, [
        node("TEXT", "Chip label", { fills: [solid("#111111")] }),
        node("INSTANCE", "Icon", { fills: [solid("#111111")] }, [node("VECTOR", "Glyph", { fills: [solid("#111111")] })]),
        node("RECTANGLE", "Bound", { fills: [bound("#3366FF", "primary")] }),         // bound: not counted
        node("RECTANGLE", "Styled", { fills: [solid("#3366FF")], fillStyleId: "S:1" }), // on the system: not counted
        node("RECTANGLE", "Hidden", { fills: [solid("#3366FF")], visible: false }),    // not seen: not counted
      ]),
    ]),
    node("VECTOR", "Home-Default --> Detail-Default", { strokes: [solid("#3366FF")] }), // scaffolding: not counted
  ])], LIB, { MODE: "collect" });
  assert.deepStrictEqual(out.unbound.map((u) => [u.hex, u.nodes]), [["#FF0000", ["id:Chip"]]], "the stroke the instance overrides is its own");
  assert.deepStrictEqual(out.inInstance, [{ hex: "#111111", count: 3 }, { hex: "#3366FF", count: 1 }],
    "the instance's own fill it does not override, and every layer inside it");
  const audit = await run([section("01. Home", [node("INSTANCE", "Chip", { fills: [solid("#3366FF")] })])]);
  assert.strictEqual(audit.inInstance, undefined, "the audit result carries no inInstance");
});

test("an opacity one step off a token reads <1%, never 0%", async () => {
  const out = await run([section("01. Home", [
    frame("Faint-Default", { effects: [{ type: "DROP_SHADOW", visible: true, color: { ...rgb("#3366FF"), a: 254 / 255 }, offset: { x: 0, y: 2 }, radius: 4, spread: 0 }] }),
  ])]);
  assert.strictEqual(out.findings.length, 1, JSON.stringify(out));
  assert.match(out.findings[0].msg, /effect #3366FFFE — near a token \(#3366FF, 0 off per channel, opacity off by <1%\)/);
});

test("SECTION applies", async () => {
  const blue = () => [solid("#3366FF")];
  // The only token is a library one, bound in a section other than the one asked for.
  const lib = { collections: [{ id: "c2", defaultModeId: "light" }], vars: [colorVar("lib-blue", { light: value("#3366FF") }, "c2")], local: [] };
  const page = () => [
    section("01. Home", [frame("Home-Default", { fills: blue() }), section("01-1. Sub", [frame("Sub-Default", { fills: blue() })])]),
    section("02. Other", [frame("Other-Default", { fills: blue(), strokes: [bound("#3366FF", "lib-blue")] })]),
    section("Template", [section("Inside template", [frame("T-Default", { fills: blue() })])]),
    frame("Loose-Default", { fills: blue() }),
  ];

  const whole = await run(page(), lib);
  assert.deepStrictEqual(ids(whole), ["id:Home-Default", "id:Sub-Default", "id:Other-Default", "id:Loose-Default"]);

  const one = await run(page(), lib, { SECTION: "id:01. Home" });
  assert.deepStrictEqual(ids(one), ["id:Home-Default", "id:Sub-Default"], "the section and what is nested in it, nothing loose");
  assert.ok(one.findings.every((f) => f.grade === "blocking"), "the dictionary is the page's, so a token bound outside the section still counts");

  const missing = await run(page(), lib, { SECTION: "id:nope" });
  assert.strictEqual(missing.pass, false);
  assert.deepStrictEqual(missing.findings.map((f) => [f.tag, f.grade, f.node]), [["[section]", "blocking", null]]);

  const noTokens = await run(page(), { vars: [], local: [], collections: [] }, { SECTION: "id:nope" });
  assert.deepStrictEqual(noTokens.findings.map((f) => f.tag), ["[section]"], "a mistyped section is not hidden behind the no-tokens note");

  const excluded = await run(page(), lib, { SECTION: "id:Inside template" });
  assert.strictEqual(excluded.pass, true);
  assert.deepStrictEqual(excluded.findings, []);
  assert.match(excluded.note, /excluded by pages\.exclude_sections; nothing audited/);

  await assert.rejects(run(page(), lib, { SECTION: "id:nope", MODE: "collect" }), /section id:nope is not on this page/);
  const exCol = await run(page(), lib, { SECTION: "id:Inside template", MODE: "collect" });
  assert.deepStrictEqual([exCol.unbound, exCol.inInstance], [[], []]);
  assert.match(exCol.note, /nothing audited/);
  const scoped = await run(page(), lib, { SECTION: "id:01. Home", MODE: "collect" });
  assert.deepStrictEqual(scoped.unbound,
    [{ hex: "#3366FF", kind: "fill", count: 2, nodes: ["id:Home-Default", "id:Sub-Default"], grade: 1, nearest: "#3366FF", tokens: ["key:lib-blue"] }]);
});

test("the audit notes hand-typed colours held inside instances, which it does not grade", async () => {
  const MASTERS = "inside component instances — run lint on the page that holds their masters";
  const out = await run([section("01. Home", [
    frame("Home-Default", { fills: [bound("#3366FF", "primary")] }, [
      node("INSTANCE", "Chip", { fills: [solid("#3366FF")] }, [                         // its own fill, not overridden: the component's
        node("TEXT", "Chip label", { fills: [solid("#111111")] }),
        node("RECTANGLE", "Bound", { fills: [bound("#3366FF", "primary")] }),         // bound: not counted
        node("RECTANGLE", "Styled", { fills: [solid("#3366FF")], fillStyleId: "S:1" }), // on the system: not counted
      ]),
    ]),
    node("VECTOR", "Home-Default --> Detail-Default", { strokes: [solid("#3366FF")] }), // scaffolding: not counted
  ])]);
  assert.deepStrictEqual(out, { pass: true, findings: [], note: `2 hand-typed colours sit ${MASTERS}` });

  const one = await run([section("01. Home", [node("INSTANCE", "Chip", {}, [node("TEXT", "Chip label", { fills: [solid("#111111")] })])])]);
  assert.strictEqual(one.note, `1 hand-typed colour sits ${MASTERS}`);

  const none = await run([section("01. Home", [frame("Home-Default", { fills: [solid("#3366FF")] })])]);
  assert.strictEqual(none.note, undefined, "no instance colour, no note");

  const scoped = await run([
    section("01. Home", [node("INSTANCE", "Chip", {}, [node("TEXT", "Chip label", { fills: [solid("#111111")] })])]),
    section("02. Other", [frame("Other-Default", {})]),
  ], LIB, { SECTION: "id:02. Other" });
  assert.strictEqual(scoped.note, undefined, "only the instances in the audited scope count");
});

test("a colour loose on the canvas, outside every section, is a warning even where an exact token exists", async () => {
  const out = await run([
    section("01. Home", [frame("Home-Default", { fills: [solid("#3366FF")] })]),
    frame("Loose-Default", { fills: [solid("#3366FF")] }),
  ]);
  assert.deepStrictEqual(out.findings.map((f) => [f.node, f.grade]), [["id:Home-Default", "blocking"], ["id:Loose-Default", "warning"]], JSON.stringify(out));
  assert.match(out.findings[1].msg, /^Loose-Default: fill #3366FF — matches a token exactly but sits outside every section/);
  assert.doesNotMatch(out.findings[1].msg, /exact token/, "lint-grades reads these words as blocking");
  const col = await run([frame("Loose-Default", { fills: [solid("#3366FF")] })], LIB, { MODE: "collect" });
  assert.strictEqual(col.unbound[0].grade, 1, "collect still grades it exact: binding it is as safe as anywhere");
});

// ── Scopes: a token counts only where it can be bound — the <token-fit> block token-bind.js shares ──
// One token per colour, each scoped differently: text only, nothing (a primitive), frame fills only,
// every property.
const SCOPED = {
  collections: [C1],
  vars: [
    colorVar("ink", { m1: value("#111111") }, "c1", { scopes: ["TEXT_FILL"] }),
    colorVar("raw", { m1: value("#222222") }, "c1", { scopes: [] }),
    colorVar("panel", { m1: value("#333333") }, "c1", { scopes: ["FRAME_FILL"] }),
    colorVar("any", { m1: value("#444444") }, "c1", { scopes: ["ALL_SCOPES"] }),
  ],
  local: ["ink", "raw", "panel", "any"],
};

test("an exact colour is blocking only where a token of it is scoped for that property", async () => {
  const out = await run([section("01. Home", [
    node("TEXT", "Label", { fills: [solid("#111111")] }),                        // ink fits text: blocking
    node("RECTANGLE", "Swatch", { fills: [solid("#111111")] }),                 // ink is text only: warning
    node("RECTANGLE", "Raw", { fills: [solid("#222222")] }),                    // scoped to nothing: warning
    frame("Panel-Default", { fills: [solid("#333333")] }),                      // a frame fill: blocking
    node("RECTANGLE", "Chip", { fills: [solid("#333333")] }),                   // a shape fill: warning
    node("RECTANGLE", "Rule", { strokes: [solid("#444444")] }),                 // ALL_SCOPES: blocking
  ])], SCOPED);
  assert.deepStrictEqual(out.findings.map((f) => [f.node, f.grade]), [
    ["id:Label", "blocking"], ["id:Swatch", "warning"], ["id:Raw", "warning"],
    ["id:Panel-Default", "blocking"], ["id:Chip", "warning"], ["id:Rule", "blocking"],
  ], JSON.stringify(out, null, 1));
  const msg = (id) => out.findings.find((f) => f.node === id).msg;
  assert.match(msg("id:Swatch"), /^01\. Home \/ Swatch: fill #111111 — exact colour, no token scoped for fill colours/);
  assert.match(msg("id:Raw"), /fill #222222 — exact colour, no token scoped for fill colours/);
  assert.match(msg("id:Chip"), /fill #333333 — exact colour, no token scoped for fill colours/);
  for (const id of ["id:Swatch", "id:Raw", "id:Chip"]) assert.doesNotMatch(msg(id), /exact token/, "lint-grades reads these words as blocking");
});

test("a node's fill and stroke of one colour are graded apart where their scopes differ", async () => {
  const out = await run([section("01. Home", [
    frame("Card-Default", { fills: [solid("#333333")], strokes: [solid("#333333")] }),   // panel fits the fill, not the stroke
  ])], SCOPED);
  assert.deepStrictEqual(out.findings.map((f) => [f.node, f.grade]), [["id:Card-Default", "blocking"], ["id:Card-Default", "warning"]], JSON.stringify(out));
  assert.match(out.findings[0].msg, /: fill #333333 — an exact token/);
  assert.match(out.findings[1].msg, /: stroke #333333 — exact colour, no token scoped for stroke colours/);
});

test("an exact colour with only unfit tokens still offers a fitting near token", async () => {
  const lib = {
    collections: [C1],
    vars: [
      colorVar("ink", { m1: value("#111111") }, "c1", { scopes: ["TEXT_FILL"] }),
      colorVar("dark", { m1: value("#141414") }, "c1", { scopes: ["SHAPE_FILL"] }),   // 3 off, and a shape can take it
    ],
    local: ["ink", "dark"],
  };
  const page = () => [section("01. Home", [
    node("RECTANGLE", "Swatch", { fills: [solid("#111111")] }),
    node("TEXT", "Label", { fills: [solid("#111111")] }),
  ])];
  const out = await run(page(), lib);
  assert.deepStrictEqual(out.findings.map((f) => [f.node, f.grade]), [["id:Swatch", "warning"], ["id:Label", "blocking"]], JSON.stringify(out));
  assert.match(out.findings[0].msg, /fill #111111 — near a token \(#141414, 3 off per channel\); this exact colour's tokens are scoped for other properties/);
  assert.doesNotMatch(out.findings[0].msg, /exact token/, "lint-grades reads these words as blocking");
  const col = await run(page(), lib, { MODE: "collect" });
  assert.deepStrictEqual(col.unbound.map((u) => [u.kind, u.grade, u.nearest, u.tokens]), [
    ["fill", 2, "#141414", ["key:dark"]],
    ["text", 1, "#111111", ["key:ink"]],
  ]);
});

test("a near colour is graded only against tokens scoped for its property", async () => {
  const out = await run([section("01. Home", [
    frame("Panel-Default", { fills: [solid("#333336")] }),                      // 3 off panel, which fits a frame
    node("RECTANGLE", "Chip", { fills: [solid("#333336")] }),                   // panel does not fit a shape
  ])], SCOPED);
  assert.deepStrictEqual(out.findings.map((f) => [f.node, f.grade]), [["id:Panel-Default", "warning"], ["id:Chip", "warning"]]);
  assert.match(out.findings[0].msg, /near a token \(#333333, 3 off per channel\)/);
  assert.match(out.findings[1].msg, /no token within 8 per channel/, "the frame-only token is not offered for a shape");
});

test("collect splits each colour by kind and lists, per row, only the tokens that fit it", async () => {
  const out = await run([section("01. Home", [
    node("TEXT", "Label", { fills: [solid("#111111")] }),
    node("RECTANGLE", "Swatch", { fills: [solid("#111111")] }),
    frame("Panel-Default", { fills: [solid("#333333")], strokes: [solid("#333333")] }),
    node("RECTANGLE", "Chip", { fills: [solid("#333336")] }),
    frame("Pane-Default", { fills: [solid("#333336")] }),
  ])], SCOPED, { MODE: "collect" });
  assert.deepStrictEqual(out.dictionary, {
    "#111111": [{ key: "key:ink", scopes: ["TEXT_FILL"] }],
    "#222222": [{ key: "key:raw", scopes: [] }],
    "#333333": [{ key: "key:panel", scopes: ["FRAME_FILL"] }],
    "#444444": [{ key: "key:any", scopes: ["ALL_SCOPES"] }],
  }, "the dictionary keeps each token's scopes beside its key");
  assert.deepStrictEqual(out.unbound, [
    { hex: "#111111", kind: "fill", count: 1, nodes: ["id:Swatch"], grade: 3, nearest: "#111111", tokens: [] },
    { hex: "#111111", kind: "text", count: 1, nodes: ["id:Label"], grade: 1, nearest: "#111111", tokens: ["key:ink"] },
    { hex: "#333333", kind: "fill", count: 1, nodes: ["id:Panel-Default"], grade: 1, nearest: "#333333", tokens: ["key:panel"] },
    { hex: "#333333", kind: "stroke", count: 1, nodes: ["id:Panel-Default"], grade: 3, nearest: "#333333", tokens: [] },
    { hex: "#333336", kind: "fill", count: 1, nodes: ["id:Pane-Default"], grade: 2, nearest: "#333333", tokens: ["key:panel"] },
    { hex: "#333336", kind: "fill", count: 1, nodes: ["id:Chip"], grade: 3, nearest: null, tokens: [] },
  ], "sorted by count, hex, kind, then grade");
});
