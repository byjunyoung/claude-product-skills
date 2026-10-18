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
  type: "FRAME", name, x, y, width: w, height: h, children: [], visible: true, fills: [], strokes: [],
  clipsContent: false, absoluteBoundingBox: { x, y, width: w, height: h }, findAll: () => [],
});
const section = (name, x, y, w, h, children) => ({ type: "SECTION", name, x, y, width: w, height: h, children });

const run = (pageChildren, cfg = baseCfg()) =>
  new AsyncFunction("CFG", "figma", SRC)(cfg, {
    currentPage: { name: "[UI] Fixture", children: pageChildren, findAllWithCriteria: () => [] },
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
  assert.ok(out.some((i) => /\[bounds\] .*C-Default outside/.test(i)), out);
});

test("top-level sections behave as before", async () => {
  const out = await run([section("S1", 0, 0, 500, 300, [frame("A-Default", 0, 0), frame("B-Default", 200, 0)])]);
  assert.strictEqual(out, "STRUCT PASS");
});

test("excluded parent excludes nested sections", async () => {
  const cfg = baseCfg();
  cfg.pages.exclude_sections = ["^Outer$"];
  const out = await run(nested(), cfg);
  assert.ok(!Array.isArray(out) || !out.some((i) => /\[bounds\]/.test(i)), out);
});

const patterned = () => {
  const cfg = baseCfg();
  cfg.naming.section_pattern = "^\\d+\\. ";
  return cfg;
};

test("nested section names are not checked against section_pattern", async () => {
  const out = await run([section("01. Period", 0, 0, 2000, 2000, [section("Work", 50, 50, 500, 300, [frame("A-Default", 0, 0)])])], patterned());
  assert.strictEqual(out, "STRUCT PASS");
});

test("a top-level section name that misses section_pattern is still reported", async () => {
  const out = await run([section("Period", 0, 0, 2000, 2000, [section("Work", 50, 50, 500, 300, [frame("A-Default", 0, 0)])])], patterned());
  assert.ok(out.some((i) => /\[naming\] section Period/.test(i)), out);
  assert.ok(!out.some((i) => /section Work/.test(i)), out);
});

test("a nested section inside its parent is not a section overlap", async () => {
  const out = await run([section("Outer", 0, 0, 2000, 2000, [section("Inner", 50, 50, 500, 300, [frame("A-Default", 0, 0)])])]);
  assert.strictEqual(out, "STRUCT PASS");
});
