/* Fixtures for prep-ops.js — resizeSection's neighbour check and renumber's scope.
 *
 *     node --test tools/test/
 *
 * prep-ops.js is a preamble of function declarations, so the test appends a return of the ones it
 * calls and runs the text against fake `CFG` and `figma` globals, as use_figma would.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "prep-ops.js"), "utf8");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const load = (page) =>
  new AsyncFunction("CFG", "figma", SRC + "\nreturn { resizeSection, renumber };")(
    { layout: { section_resize_margin: [10, 20] }, pages: {} }, { currentPage: page });

const sec = (name, x, y, w, h, children = []) => {
  const s = { type: "SECTION", id: "id:" + name, name, x, y, width: w, height: h, children,
    resizeWithoutConstraints(nw, nh) { this.width = nw; this.height = nh; } };
  for (const c of children) c.parent = s;
  return s;
};

test("resizeSection checks the sections beside it in the same parent, at any depth", async () => {
  const mine = sec("Mine", 0, 0, 100, 100);
  const beside = sec("Beside", 150, 0, 100, 100);        // reached once Mine grows to 200 wide
  const far = sec("Far", 5000, 0, 100, 100);
  const outer = sec("Outer", 0, 0, 9000, 9000, [mine, beside, far]);
  // Overlaps Beside in its own coordinates, but lives in another parent: not a neighbour of Mine.
  const stranger = sec("Stranger", 150, 0, 100, 100);
  const page = { children: [outer, stranger] };
  for (const c of page.children) c.parent = page;
  const { resizeSection } = await load(page);
  assert.deepStrictEqual(resizeSection(mine, 180, 80), ["Beside"]);
  // A top-level section still compares against its top-level siblings.
  const top = sec("Top", 0, 0, 10, 10);
  top.parent = page;
  page.children.push(top);
  assert.deepStrictEqual(resizeSection(top, 140, 80), ["Outer", "Stranger"]);
});

test("renumber stays on top-level sections", async () => {
  const inner = sec("02. Inner", 0, 0, 10, 10);
  const outer = sec("05. Outer", 0, 0, 100, 100, [inner]);
  const page = { children: [outer] };
  const { renumber } = await load(page);
  renumber();
  assert.strictEqual(outer.name, "01. Outer");
  assert.strictEqual(inner.name, "02. Inner");
});
