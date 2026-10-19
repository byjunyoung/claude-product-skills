/* Regression fixtures for audit-struct.js — nested sections.
 *
 *     node --test tools/test/
 *
 * Same approach as audit-flow.test.js: the script reads `CFG` and `figma` globals and returns
 * its findings. audit-struct.js awaits (variable lookups), so it is built as an async function,
 * the way use_figma runs it.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "audit-struct.js"),
  "utf8"
);
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

const baseCfg = () => ({
  naming: { label_prefix: "[label] " },
  pages: {},
});

// An empty screen: the later checks (layer names, pins, modes, clipping) find nothing to report.
const frame = (name, x, y, w = 100, h = 100) => ({
  type: "FRAME", id: "id:" + name, name, x, y, width: w, height: h, children: [], visible: true, fills: [], strokes: [],
  clipsContent: false, absoluteBoundingBox: { x, y, width: w, height: h }, findAll: () => [],
});
const section = (name, x, y, w, h, children) => ({ type: "SECTION", id: "id:" + name, name, x, y, width: w, height: h, children });

const run = (pageChildren, cfg = baseCfg(), SECTION, sets = []) =>
  new AsyncFunction("CFG", "SECTION", "figma", SRC)(cfg, SECTION, {
    currentPage: { name: "[UI] Fixture", children: pageChildren, findAllWithCriteria: () => sets },
  });

// Outer 2000x2000 at the origin holds an inner 500x300 at (50, 50). The inner section holds two
// frames that fit and one placed far outside it.
const nested = () => [
  section("Outer", 0, 0, 2000, 2000, [
    section("Inner", 50, 50, 500, 300, [
      frame("A-Default", 0, 0),
      frame("B-Default", 200, 0),
      frame("C-Default", 5000, 5000),
    ]),
  ]),
];

test("a frame outside a nested section is out of bounds", async () => {
  const out = await run(nested());
  const f = out.findings.find((i) => i.tag === "[bounds]");
  assert.ok(f, JSON.stringify(out));
  assert.strictEqual(f.grade, "blocking");
  assert.strictEqual(f.node, "id:C-Default");
  assert.match(f.msg, /C-Default outside/);
  assert.ok(!f.msg.startsWith("["), "the tag moved to `tag`, msg keeps the text only");
});

test("top-level sections behave as before", async () => {
  const out = await run([section("S1", 0, 0, 500, 300, [frame("A-Default", 0, 0), frame("B-Default", 200, 0)])]);
  assert.deepStrictEqual(out, { pass: true, findings: [] });
});

test("audit-struct: clean page → { pass: true, findings: [] }", async () => {
  const out = await run([]);
  assert.deepStrictEqual(out, { pass: true, findings: [] });
});

test("pass is exactly findings.length === 0, and every finding carries the four fields", async () => {
  const out = await run([section("S1", 0, 0, 500, 300, [frame("A-Default", 0, 0), frame("B-Default", 50, 0)])]);
  assert.strictEqual(out.pass, out.findings.length === 0);
  assert.ok(out.findings.length > 0);
  for (const f of out.findings) {
    assert.deepStrictEqual(Object.keys(f).sort(), ["grade", "msg", "node", "tag"]);
    assert.ok(["blocking", "warning"].includes(f.grade));
  }
});

test("frame overlap is blocking and a naming mismatch is a warning", async () => {
  const cfg = baseCfg();
  cfg.naming.frame_pattern = "^[A-Z]-Default$";
  const out = await run([section("S1", 0, 0, 500, 300, [frame("A-Default", 0, 0), frame("bad", 50, 0)])], cfg);
  const by = (t) => out.findings.find((i) => i.tag === t);
  assert.strictEqual(by("[frame overlap]").grade, "blocking");
  assert.strictEqual(by("[naming]").grade, "warning");
  assert.strictEqual(by("[naming]").node, "id:bad");
});

test("excluded parent excludes nested sections", async () => {
  const cfg = baseCfg();
  cfg.pages.exclude_sections = ["^Outer$"];
  const out = await run(nested(), cfg);
  assert.ok(!out.findings.some((i) => i.tag === "[bounds]"), JSON.stringify(out));
});

const patterned = () => {
  const cfg = baseCfg();
  cfg.naming.section_pattern = "^\\d+\\. ";
  return cfg;
};

test("nested section names are not checked against section_pattern", async () => {
  const out = await run([section("01. Period", 0, 0, 2000, 2000, [section("Work", 50, 50, 500, 300, [frame("A-Default", 0, 0)])])], patterned());
  assert.strictEqual(out.pass, true);
});

test("a top-level section name that misses section_pattern is still reported", async () => {
  const out = await run([section("Period", 0, 0, 2000, 2000, [section("Work", 50, 50, 500, 300, [frame("A-Default", 0, 0)])])], patterned());
  assert.ok(out.findings.some((i) => i.tag === "[naming]" && /section Period/.test(i.msg)), JSON.stringify(out));
  assert.ok(!out.findings.some((i) => /section Work/.test(i.msg)), JSON.stringify(out));
});

test("a nested section inside its parent is not a section overlap", async () => {
  const out = await run([section("Outer", 0, 0, 2000, 2000, [section("Inner", 50, 50, 500, 300, [frame("A-Default", 0, 0)])])]);
  assert.strictEqual(out.pass, true);
});

// ── [mode] — a mode set on an outer section reaches the screens inside nested ones ──
const COL = { id: "C1", name: "Theme", modes: [{ modeId: "L", name: "Light" }, { modeId: "D", name: "Dark" }], defaultModeId: "D" };
const boundFrame = (name) => ({
  ...frame(name, 0, 0),
  fills: [{ type: "SOLID", boundVariables: { color: { id: "V1" } } }],
});
const runVars = (pageChildren) =>
  new AsyncFunction("CFG", "figma", SRC)(baseCfg(), {
    currentPage: { name: "[UI] Fixture", children: pageChildren, findAllWithCriteria: () => [] },
    variables: {
      getVariableByIdAsync: async () => ({ variableCollectionId: "C1" }),
      getVariableCollectionByIdAsync: async () => COL,
    },
  });
const withModes = (sec, modes) => Object.assign(sec, { explicitVariableModes: modes });

test("a mode set on an outer section covers the screens in a nested one", async () => {
  const out = await runVars([
    withModes(section("Outer", 0, 0, 2000, 2000, [section("Inner", 50, 50, 500, 300, [boundFrame("A-Default")])]), { C1: "L" }),
  ]);
  assert.ok(!out.findings.some((i) => i.tag === "[mode]"), JSON.stringify(out));
});

test("no mode anywhere above a nested screen is still reported", async () => {
  const out = await runVars([
    section("Outer", 0, 0, 2000, 2000, [section("Inner", 50, 50, 500, 300, [boundFrame("A-Default")])]),
  ]);
  const f = out.findings.find((i) => i.tag === "[mode]");
  assert.ok(f && /Inner \/ A-Default/.test(f.msg), JSON.stringify(out));
  assert.strictEqual(f.grade, "blocking");
  assert.strictEqual(f.node, "id:A-Default");
});

// ── SECTION — audit one section and the ones nested in it ──
// Three levels. Every level holds a frame outside its own bounds, and "Other" is a sibling of
// "L1" that is bad too; only what sits under the chosen section may be reported.
const levels = () => [
  section("L1", 0, 0, 3000, 3000, [
    frame("Bad1-Default", 9000, 9000),
    section("L2", 50, 50, 2000, 2000, [
      frame("Bad2-Default", 9000, 9000),
      section("L3", 50, 50, 500, 300, [frame("Bad3-Default", 9000, 9000)]),
    ]),
  ]),
  section("Other", 5000, 0, 500, 300, [frame("BadO-Default", 9000, 9000)]),
];
const boundsOf = (out) => out.findings.filter((i) => i.tag === "[bounds]").map((i) => i.node).sort();

test("SECTION limits the audit to that section and its nested sections", async () => {
  assert.deepStrictEqual(boundsOf(await run(levels())), ["id:Bad1-Default", "id:Bad2-Default", "id:Bad3-Default", "id:BadO-Default"]);
  assert.deepStrictEqual(boundsOf(await run(levels(), baseCfg(), "id:L2")), ["id:Bad2-Default", "id:Bad3-Default"]);
  assert.deepStrictEqual(boundsOf(await run(levels(), baseCfg(), "id:L3")), ["id:Bad3-Default"]);
});

test("SECTION leaves out page-level findings that belong to no section", async () => {
  const out = await run([frame("Loose-Default", 0, 0), ...levels()], baseCfg(), "id:L3");
  assert.ok(!out.findings.some((i) => i.tag === "[membership]"), JSON.stringify(out));
});

test("unknown SECTION is a blocking [section] finding", async () => {
  const out = await run(levels(), baseCfg(), "id:nope");
  assert.deepStrictEqual(out, {
    pass: false,
    findings: [{ tag: "[section]", grade: "blocking", node: null, msg: "section id:nope is not on this page" }],
  });
});

test("SECTION inside an excluded parent audits nothing and says so", async () => {
  const cfg = baseCfg();
  cfg.pages.exclude_sections = ["^L1$"];
  const out = await run(levels(), cfg, "id:L3");
  assert.deepStrictEqual(out, {
    pass: true, findings: [],
    note: "section id:L3 is excluded by pages.exclude_sections; nothing audited",
  });
});

test("SECTION that is itself excluded audits nothing and says so", async () => {
  const cfg = baseCfg();
  cfg.pages.exclude_sections = ["^L2$"];
  const out = await run(levels(), cfg, "id:L2");
  assert.deepStrictEqual(out, {
    pass: true, findings: [],
    note: "section id:L2 is excluded by pages.exclude_sections; nothing audited",
  });
});

test("SECTION still reports the target overlapping its neighbour", async () => {
  const overlaps = (out) => out.findings.filter((i) => i.tag === "[section overlap]");
  // top level: A (0..500) and B (400..900) overlap; C is clear of both
  const top = () => [section("A", 0, 0, 500, 300, []), section("B", 400, 0, 500, 300, []), section("C", 3000, 0, 500, 300, [])];
  assert.strictEqual(overlaps(await run(top(), baseCfg(), "id:A")).length, 1);
  assert.strictEqual(overlaps(await run(top(), baseCfg(), "id:C")).length, 0);
  // nested: P1 and P2 overlap inside Outer; Q is far away
  const nest = () => [section("Outer", 0, 0, 5000, 5000, [
    section("P1", 0, 0, 500, 300, []), section("P2", 400, 0, 500, 300, []), section("Q", 3000, 0, 500, 300, []),
  ])];
  assert.strictEqual(overlaps(await run(nest(), baseCfg(), "id:P2")).length, 1);
  assert.strictEqual(overlaps(await run(nest(), baseCfg(), "id:Q")).length, 0);
});

test("SECTION keeps only the [variant stack] findings of component sets inside it", async () => {
  const set = (id, parent) => ({
    type: "COMPONENT_SET", id, name: id, layoutMode: "NONE", parent,
    children: [{ x: 0, y: 0, width: 50, height: 50, name: "v1" }, { x: 10, y: 10, width: 50, height: 50, name: "v2" }],
  });
  const page = [
    section("In", 0, 0, 500, 300, []),
    section("Out", 3000, 0, 500, 300, []),
  ];
  const sets = [set("cs:in", page[0]), set("cs:out", page[1])];
  const stacks = (out) => out.findings.filter((i) => i.tag === "[variant stack]").map((i) => i.node);
  assert.deepStrictEqual(stacks(await run(page, baseCfg(), undefined, sets)), ["cs:in", "cs:out"]);
  assert.deepStrictEqual(stacks(await run(page, baseCfg(), "id:In", sets)), ["cs:in"]);
});
