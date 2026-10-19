/* Runs _common/scripts/text-walk.js (proto's read-only text pass) against fake nodes.
 *
 *     node --test tools/test/text-walk.test.js
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = (() => {
  try {
    return readFileSync(join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "text-walk.js"), "utf8");
  } catch (e) {
    return "";
  }
})();
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

const text = (id, characters, x, y, visible = true) =>
  ({ type: "TEXT", id, characters, visible, absoluteBoundingBox: { x, y, width: 10, height: 10 } });
const box = (id, children, type = "FRAME") => ({ type, id, children });

const run = async (page, ROOT_ID) => {
  assert.ok(SRC, "_common/scripts/text-walk.js was not found");
  const byId = {};
  const index = (n, parent) => { n.parent = parent; byId[n.id] = n; (n.children || []).forEach((c) => index(c, n)); };
  index(page, null);
  const figma = {
    currentPage: page,
    getNodeByIdAsync: async (id) => byId[id] || null,
    setCurrentPageAsync: async () => {},
  };
  return new AsyncFunction("figma", "ROOT_ID", SRC)(figma, ROOT_ID);
};

test("text-walk returns every text with absolute position, hidden flag and id, sorted", async () => {
  const page = box("p", [box("f", [text("t3", "Right", 100.4, 10), text("t2", "Below", 5, 40), text("t1", "Left", 5.6, 10)])], "PAGE");
  const r = await run(page, "f");
  assert.deepStrictEqual(r, [
    { id: "t1", text: "Left", x: 6, y: 10, hidden: false },
    { id: "t3", text: "Right", x: 100, y: 10, hidden: false },
    { id: "t2", text: "Below", x: 5, y: 40, hidden: false },
  ]);
});

test("nested and hidden texts are included and marked; blank texts are left out", async () => {
  const page = box("p", [box("f", [box("g", [text("a", "Deep", 0, 0), text("b", "Helper text", 0, 20, false), text("c", "   ", 0, 30)])])], "PAGE");
  const r = await run(page, "f");
  assert.deepStrictEqual(r.map((o) => [o.id, o.text, o.hidden]), [["a", "Deep", false], ["b", "Helper text", true]]);
});

test("without ROOT_ID the current page is walked", async () => {
  const page = box("p", [box("f", [text("a", "One", 0, 0)]), box("g", [text("b", "Two", 0, 5)])], "PAGE");
  const r = await run(page);
  assert.deepStrictEqual(r.map((o) => o.text), ["One", "Two"]);
});
