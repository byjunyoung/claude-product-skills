/* Runs _common/scripts/image-fills.js (proto's read-only image scan) against fake nodes.
 *
 *     node --test tools/test/image-fills.test.js
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = (() => {
  try {
    return readFileSync(join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "image-fills.js"), "utf8");
  } catch (e) {
    return "";
  }
})();
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

const node = (id, name, type, fills, children = [], w = 100, h = 50) =>
  ({ id, name, type, fills, children, width: w, height: h });

test("image-fills lists image paints by node", async () => {
  assert.ok(SRC, "_common/scripts/image-fills.js was not found");
  const photo = node("2", "Photo", "RECTANGLE", [{ type: "IMAGE" }], [], 120.4, 80.6);
  const map = node("3", "Map", "FRAME", [{ type: "SOLID" }, { type: "IMAGE" }], [node("4", "Pin", "ELLIPSE", [{ type: "SOLID" }])]);
  const root = node("1", "Screen", "FRAME", [{ type: "SOLID" }], [photo, map, node("5", "Plain", "FRAME", [])]);
  const byId = { 1: root };
  const figma = { currentPage: { id: "p", children: [root] }, getNodeByIdAsync: async (id) => byId[id], setCurrentPageAsync: async () => {} };
  const r = await new AsyncFunction("figma", "ROOT_ID", SRC)(figma, "1");
  assert.deepStrictEqual(r, [
    { id: "2", name: "Photo", type: "RECTANGLE", w: 120, h: 81, kids: 0 },
    { id: "3", name: "Map", type: "FRAME", w: 100, h: 50, kids: 1 },   // kids > 0 = has overlays
  ]);
});
