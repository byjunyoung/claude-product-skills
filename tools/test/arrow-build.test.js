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

// ── [state] links and opacity ──
const buildState = () => {
  const frames = [
    { type: "FRAME", name: "a", x: 0, y: 0, width: 100, height: 100 },
    { type: "FRAME", name: "b", x: 0, y: 200, width: 100, height: 100 },
  ];
  const figma = {
    createVector: () => ({ id: "v1", async setVectorNetworkAsync(net) { this.vectorNetwork = net; } }),
  };
  const section = { children: frames, appendChild(v) { this.vector = v; } };
  return { section, ...new Function("CFG", "figma", SRC + "\nreturn { stateLink, arrow, styleOf };")({}, figma) };
};

test("a state link created with opts.stroke carries it", async () => {
  const { section, stateLink } = buildState();
  await stateLink(section, "a", "b", { stroke: STROKE });
  assert.deepStrictEqual(section.vector.strokes[0].color, { r: 1, g: 0, b: 0 });
  assert.strictEqual(section.vector.strokeWeight, 2);
  assert.deepStrictEqual(section.vector.dashPattern, [4, 4]);
});

test("a state link with dash null is solid, and without opts stays dashed", async () => {
  const s1 = buildState();
  await s1.stateLink(s1.section, "a", "b", { stroke: { dash: null } });
  assert.ok(!s1.section.vector.dashPattern || s1.section.vector.dashPattern.length === 0);
  const s2 = buildState();
  await s2.stateLink(s2.section, "a", "b");
  assert.ok(s2.section.vector.dashPattern && s2.section.vector.dashPattern.length > 0);
});

test("stroke opacity survives styleOf -> arrow", async () => {
  const { arrow, styleOf } = build(), p = parent();
  await arrow(p, "a --> b", [[0, 0], [10, 0]], { stroke: { ...STROKE, opacity: 0.5 } });
  assert.strictEqual(p.vector.strokes[0].opacity, 0.5);
  const st = styleOf(p.vector);
  assert.strictEqual(st.stroke.opacity, 0.5);
  const p2 = parent();
  await build().arrow(p2, "a --> b", [[0, 0], [10, 0]], st);
  assert.strictEqual(p2.vector.strokes[0].opacity, 0.5);
});

test("an opaque arrow carries no opacity in its style", async () => {
  const { arrow, styleOf } = build(), p = parent();
  await arrow(p, "a --> b", [[0, 0], [10, 0]], { stroke: STROKE });
  p.vector.strokes[0].opacity = 1;
  assert.ok(!("opacity" in styleOf(p.vector).stroke));
});
