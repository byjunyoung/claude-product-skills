/* Runs the helpers in _common/scripts/sync-ops.js (the preamble /fig:sync's apply step uses) against
 * fake nodes.
 *
 *     node --test tools/test/sync-ops.test.js
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = (() => {
  try {
    return readFileSync(
      join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "sync-ops.js"),
      "utf8"
    );
  } catch (e) {
    return "";
  }
})();

let seq = 0;
const walk = (n, pred, acc = []) => {
  for (const c of n.children || []) {
    if (pred(c)) acc.push(c);
    walk(c, pred, acc);
  }
  return acc;
};
const text = (characters, parentName) => ({ type: "TEXT", id: `t${++seq}`, characters, parent: { name: parentName || "Frame" }, children: [] });
const frame = (name, texts) => {
  const f = { type: "FRAME", id: `f${++seq}`, name, children: texts };
  f.findAll = (pred) => walk(f, pred);
  return f;
};
const section = (name, children) => ({ type: "SECTION", id: `s${++seq}`, name, children });

const ops = (figma = {}) => {
  assert.ok(SRC, "_common/scripts/sync-ops.js was not found");
  return new Function("figma", SRC + "\nreturn { findKeywords, sameStructure, editValue, editValues, fourEdgeClear };")(figma);
};

test("findKeywords lists, per keyword, the frames whose text holds it; absent stays empty", () => {
  const { findKeywords } = ops();
  const page = {
    children: [
      section("01. A", [
        frame("Login-Default", [text("Log in"), text("Forgot password?")]),
        frame("[label] note", [text("Forgot password?")]),
      ]),
    ],
  };
  const r = findKeywords(page, ["Forgot", "Nowhere"]);
  assert.deepStrictEqual(r["Forgot"], ["Login-Default"]);
  assert.deepStrictEqual(r["Nowhere"], []);
});

test("sameStructure is true only for same length, same order, same parent names", () => {
  const { sameStructure } = ops();
  const a = frame("A", [text("Hello", "Row"), text("World", "Row")]);
  const b = frame("B", [text("Hallo", "Row"), text("Welt", "Row")]);
  const c = frame("C", [text("Hallo", "Row")]);
  const d = frame("D", [text("Hallo", "Row"), text("Welt", "Other")]);
  assert.strictEqual(sameStructure(a, b), true);   // only values differ
  assert.strictEqual(sameStructure(a, c), false);
  assert.strictEqual(sameStructure(a, d), false);
});

test("editValue loads every font the text uses, then writes the value", async () => {
  const loaded = [];
  const { editValue } = ops({ loadFontAsync: async (f) => loaded.push(f.family) });
  const t = {
    id: "t1", characters: "old",
    getStyledTextSegments: () => [{ fontName: { family: "A", style: "R" } }, { fontName: { family: "B", style: "R" } }, { fontName: { family: "A", style: "R" } }],
  };
  await editValue(t, "new");
  assert.deepStrictEqual(loaded.sort(), ["A", "B"]);
  assert.strictEqual(t.characters, "new");
});

test("editValues aborts before touching anything when the count is not the expected one", async () => {
  const { editValues } = ops({ loadFontAsync: async () => {} });
  const t = { id: "t1", characters: "old", getStyledTextSegments: () => [] };
  await assert.rejects(() => editValues([[t, "x"]], 2), /aborted: expected 2, got 1/);
  assert.strictEqual(t.characters, "old");
  const r = await editValues([[t, "x"]], 1);
  assert.deepStrictEqual(r, { mutatedNodeIds: ["t1"] });
  assert.strictEqual(t.characters, "x");
});

test("fourEdgeClear tests the post-stretch box against the other sections on all four edges", () => {
  const box = (id, x, y, w, h) => ({ type: "SECTION", id, name: id, absoluteBoundingBox: { x, y, width: w, height: h } });
  const target = box("T", 0, 0, 100, 100);
  const others = [box("right", 150, 0, 100, 100), box("below", 0, 150, 100, 100)];
  const page = { children: [target, ...others, { type: "FRAME", id: "f", name: "f" }] };
  const { fourEdgeClear } = ops({ currentPage: page });
  assert.deepStrictEqual(fourEdgeClear(target, 100, 100), { clear: true, hits: [] });
  const wide = fourEdgeClear(target, 200, 100);   // stretching right runs into "right"
  assert.strictEqual(wide.clear, false);
  assert.deepStrictEqual(wide.hits.map((h) => h.name), ["right"]);
  assert.deepStrictEqual(fourEdgeClear(target, 100, 200).hits.map((h) => h.name), ["below"]);
});
