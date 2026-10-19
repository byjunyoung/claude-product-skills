/* Parity fixture for audit-component.js — nested sections.
 *
 *     node --test tools/test/
 *
 * The only thing that may change a finding is where a frame lives, never how deep. The same frame
 * is placed once in a top-level section and once in a section inside another, and both runs have
 * to report the same thing. Instance positions come from absoluteBoundingBox, which the sandbox
 * already composes, so the fixture does not depend on section coordinates at all.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "audit-component.js"),
  "utf8"
);
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

// Ten production uses all turn "Icon" on: that is the file's convention.
const STAT = { "Button|Icon": { t: 10, f: 0 } };

const instance = (iconOn) => ({
  type: "INSTANCE", id: "I:1", name: "Button",
  absoluteBoundingBox: { x: 10, y: 10, width: 80, height: 40 },
  componentProperties: { "Icon#1:2": { type: "BOOLEAN", value: iconOn } },
  getMainComponentAsync: async () => ({ name: "Button", parent: null }),
});
const screen = () => {
  const inst = instance(false);                   // the stray: Icon left off
  return {
    type: "FRAME", name: "Home-Default",
    absoluteBoundingBox: { x: 0, y: 0, width: 1000, height: 800 },
    findAll: (pred) => [inst].filter(pred),
  };
};
const section = (name, children) => ({ type: "SECTION", name, x: 0, y: 0, width: 4000, height: 4000, children });

const run = (pageChildren, bodyOffset = { left: 0, top: 0 }, SECTION, pages = {}) => {
  const page = { name: "[UI] Fixture", children: pageChildren };
  return new AsyncFunction("CFG", "MODE", "PAGE", "STAT", "SECTION", "figma", SRC)(
    { pages, component_audit: { min_samples: 5, dominance: 0.9, body_offset: bodyOffset } },
    "compare", "Fixture", STAT, SECTION,
    { root: { children: [page] }, setCurrentPageAsync: async () => {} }
  );
};

test("a frame in a nested section yields the same findings as in a top-level section", async () => {
  const flat = await run([section("S1", [screen()])]);
  const deep = await run([section("Outer", [section("S1", [screen()])])]);
  assert.strictEqual(flat.findings.length, 1, "the fixture must produce a finding");
  assert.strictEqual(flat.findings[0].tag, "[default]");
  assert.strictEqual(flat.findings[0].grade, "blocking");
  assert.strictEqual(flat.findings[0].node, "I:1");
  assert.match(flat.findings[0].msg, /^Home-Default \/ Button Icon=false/);
  assert.deepStrictEqual(deep, flat);
});

test("body_offset null examines the whole frame", async () => {
  const r = await run([section("S1", [screen()])], null);
  assert.strictEqual(r.findings.length, 1);
  assert.strictEqual(r.findings[0].tag, "[default]");
});

test("a set body_offset still exempts the shell", async () => {
  const r = await run([section("S1", [screen()])], { left: 270, top: 120 });
  assert.deepStrictEqual(r, { pass: true, findings: [], unknown: [] });
});

test("compare with an unseen property → pass true, unknown lists it", async () => {
  const page = { name: "[UI] Fixture", children: [section("S1", [screen()])] };
  const r = await new AsyncFunction("CFG", "MODE", "PAGE", "STAT", "figma", SRC)(
    { component_audit: { min_samples: 5, dominance: 0.9 } }, "compare", "Fixture", {},
    { root: { children: [page] }, setCurrentPageAsync: async () => {} }
  );
  assert.strictEqual(r.pass, true);
  assert.deepStrictEqual(r.findings, []);
  assert.deepStrictEqual(r.unknown, ["Button|Icon x1"]);
});

// ── SECTION — audit one section and the ones nested in it (compare mode) ──
const sec = (id, children) => Object.assign(section(id, children), { id });
const levels = () => [
  sec("L1", [screen(), sec("L2", [screen(), sec("L3", [screen()])])]),
  sec("Other", [screen()]),
];

test("SECTION limits the audit to that section and its nested sections", async () => {
  assert.strictEqual((await run(levels())).findings.length, 4);
  assert.strictEqual((await run(levels(), undefined, "L2")).findings.length, 2);
  assert.strictEqual((await run(levels(), undefined, "L3")).findings.length, 1);
});

test("unknown SECTION is a blocking [section] finding", async () => {
  const r = await run(levels(), undefined, "nope");
  assert.strictEqual(r.pass, false);
  assert.deepStrictEqual(r.findings, [{ tag: "[section]", grade: "blocking", node: null, msg: "section nope is not on this page" }]);
});

test("SECTION inside an excluded parent audits nothing and says so", async () => {
  const r = await run(levels(), undefined, "L3", { exclude_sections: ["^L1$"] });
  assert.deepStrictEqual(r, {
    pass: true, findings: [], unknown: [],
    note: "section L3 is excluded by pages.exclude_sections; nothing audited",
  });
});
