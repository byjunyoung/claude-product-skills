/* Regression fixtures for arrow-build.js — a re-synced arrow keeps the style of the one it replaces.
 *
 *     node --test tools/test/
 *
 * The script is a build preamble that runs inside the Figma sandbox against `CFG` and `figma`
 * globals. A test supplies both; the fake vector keeps its network on `vectorNetwork`, where
 * Figma's real VectorNode exposes it, so `styleOf` reads the same shape it would read live.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "arrow-build.js"),
  "utf8"
);

const build = () => {
  const figma = {
    createVector: () => ({
      id: "v1",
      async setVectorNetworkAsync(net) { this.vectorNetwork = net; },
    }),
  };
  return new Function("CFG", "figma", SRC + "\nreturn { arrow, styleOf };")({}, figma);
};

const parent = () => ({ vector: null, appendChild(v) { this.vector = v; } });
const STROKE = { color: { r: 1, g: 0, b: 0 }, weight: 2, dash: [4, 4] };

test("stroke override is applied", async () => {
  const { arrow } = build(), p = parent();
  await arrow(p, "a --> b", [[0, 0], [10, 0]], { stroke: STROKE });
  assert.deepStrictEqual(p.vector.strokes[0].color, { r: 1, g: 0, b: 0 });
  assert.strictEqual(p.vector.strokeWeight, 2);
  assert.deepStrictEqual(p.vector.dashPattern, [4, 4]);
});

test("stroke dash null is solid even when dashed", async () => {
  const { arrow } = build(), p = parent();
  await arrow(p, "a --> b", [[0, 0], [10, 0]], { dashed: true, stroke: { dash: null } });
  assert.ok(!p.vector.dashPattern || p.vector.dashPattern.length === 0);
});

test("styleOf round-trips", async () => {
  const { arrow, styleOf } = build(), p = parent();
  await arrow(p, "a --> b", [[0, 0], [10, 0]], { stroke: STROKE });
  assert.deepStrictEqual(styleOf(p.vector), { stroke: STROKE, bidirectional: false });
});

test("styleOf reads a bidirectional arrow", async () => {
  const { arrow, styleOf } = build(), p = parent();
  await arrow(p, "a --> b", [[0, 0], [10, 0]], { bidirectional: true });
  assert.strictEqual(styleOf(p.vector).bidirectional, true);
});

test("styleOf on an unstroked vector is null", () => {
  assert.strictEqual(build().styleOf({ strokes: [] }), null);
});
