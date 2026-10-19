/* Fixtures for probe-page.js — the page probe /fig:setup reads.
 *
 *     node --test tools/test/
 *
 * The script takes PAGE_ID and `figma`, and returns an observation object. Nested sections must be
 * reported with their depth, and the frames inside them must be observed like any others.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "probe-page.js"), "utf8");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

const frame = (name, x, y) => ({ type: "FRAME", name, x, y, width: 100, height: 100, children: [] });
const section = (name, x, y, children) => {
  const s = { type: "SECTION", name, x, y, width: 1000, height: 1000, children };
  for (const c of children) c.parent = s;
  return s;
};
const probe = (pageChildren) => {
  const page = { type: "PAGE", name: "[UI] Fixture", children: pageChildren };
  for (const c of pageChildren) c.parent = page;
  return new AsyncFunction("PAGE_ID", "figma", SRC)("p:1", {
    getNodeByIdAsync: async () => page, setCurrentPageAsync: async () => {},
  });
};

test("probe-page reports nested sections with their depth", async () => {
  const out = await probe([
    section("L1", 0, 0, [
      frame("A-Default", 0, 0),
      section("L2", 200, 200, [frame("B-Default", 0, 0), frame("B-Empty", 200, 0),
        section("L3", 400, 400, [frame("C-Default", 0, 0)])]),
    ]),
  ]);
  assert.deepStrictEqual(out.sections.map((s) => [s.name, s.depth]), [["L1", 0], ["L2", 1], ["L3", 2]]);
  assert.strictEqual(out.sectionCount, 3);
  assert.deepStrictEqual(out.frameNames.sort(), ["A-Default", "B-Default", "B-Empty", "C-Default"]);
  assert.deepStrictEqual(out.suffixes, { Default: 3, Empty: 1 });
  assert.deepStrictEqual(out.gaps.frameX, [100]);       // B-Default to B-Empty, within one section
});
