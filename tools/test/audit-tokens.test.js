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
const colorVar = (id, valuesByMode, collection = "c1") =>
  ({ id, key: "key:" + id, name: id, resolvedType: "COLOR", variableCollectionId: collection, valuesByMode });
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
        node("INSTANCE", "Button", { fills: blue() }, [                              // the instance's own override counts
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
  assert.ok(out.findings.every((f) => f.grade === "blocking"));
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
        { type: "DROP_SHADOW", visible: true, color: { ...rgb("#3366FF"), a: 0.2 }, offset: { x: 0, y: 2 }, radius: 4, spread: 0 },
        { type: "INNER_SHADOW", visible: true, color: value("#3366FF"), offset: { x: 0, y: 1 }, radius: 2, spread: 0,
          boundVariables: { color: alias("primary") } },
        { type: "LAYER_BLUR", visible: true, radius: 4 },
      ],
    }),
  ])]);
  assert.strictEqual(out.findings.length, 1, JSON.stringify(out));
  const f = out.findings[0];
  assert.strictEqual(f.tag, "[unbound]");
  assert.strictEqual(f.grade, "blocking");
  assert.strictEqual(f.node, "id:Card-Default");
  assert.match(f.msg, /effect #3366FF/);
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
      "#3366FF": ["key:primary"],
      "#FFFFFF": ["key:surface"],
      "#111111": ["key:lib-ink"],
    },
    unbound: [
      { hex: "#3366FF", count: 3, nodes: ["id:Home-Default", "id:Divider"], grade: 1, nearest: "#3366FF" },
      { hex: "#FAFAFA", count: 1, nodes: ["id:Body"], grade: 2, nearest: "#FFFFFF" },
      { hex: "#FF0000", count: 1, nodes: ["id:Alert"], grade: 3, nearest: null },
    ],
    note: "3 colour variables could not be resolved to a colour and were left out of the dictionary",
  });
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
  const scoped = await run(page(), lib, { SECTION: "id:01. Home", MODE: "collect" });
  assert.deepStrictEqual(scoped.unbound, [{ hex: "#3366FF", count: 2, nodes: ["id:Home-Default", "id:Sub-Default"], grade: 1, nearest: "#3366FF" }]);
});
