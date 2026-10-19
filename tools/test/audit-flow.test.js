/* Regression fixtures for audit-flow.js — the geometry the report is built on.
 *
 *     node --test tools/test/
 *
 * The script runs inside the Figma sandbox against `CFG` and `figma` globals and returns
 * its findings, so a test supplies both and reads the return value. Only two lines touch
 * `figma` (the page and its children), which is what makes this possible without a sandbox.
 *
 * Every fixture is the same two screens 100px apart. What changes is the one arrow between
 * them — because the point of these checks is that arrows which look identical at working
 * zoom are not, and a distance-only check would pass most of them.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const SRC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts", "audit-flow.js"),
  "utf8"
);

const CFG = {
  naming: {
    arrow_delimiter: " --> ",
    state_chain_delimiter: " ~ ",
    label_prefix: "[label] ",
    state_chain_prefix: "[state] ",
  },
  arrows: { audit: { edge_tolerance: 2, gap_range: [9, 15], label_clear: 30 } },
  pages: {},
};

const frame = (name, x, y) => ({ type: "FRAME", id: "f:" + name, name, x, y, width: 100, height: 100 });
const arrow = (name, ...pts) => ({
  type: "VECTOR", id: "v:" + name, name, x: 0, y: 0,
  vectorNetwork: { vertices: pts.map(([x, y]) => ({ x, y })) },
});

// One section at the origin, so frame coordinates are already absolute.
const run = (children) =>
  new Function("CFG", "figma", SRC)(CFG, {
    currentPage: { name: "[UI] Fixture", children: [{ type: "SECTION", name: "S1", x: 0, y: 0, children }] },
  });

// A: x 0–100. B: x 200–300. Both y 0–100.
// Findings of one tag, and the one finding a test is about.
const tagged = (out, tag) => out.findings.filter((i) => i.tag === tag);
const PASS = { pass: true, findings: [] };
const A = frame("a_default", 0, 0);
const B = frame("b_default", 200, 0);

// Leaves A's right edge, ends 10px short of B's left edge, final segment perpendicular to it.
const GOOD = ["a_default --> b_default", [100, 50], [150, 50], [190, 50]];

test("a well-formed arrow reports nothing", () => {
  assert.deepStrictEqual(run([A, B, arrow(...GOOD)]), PASS);
});

test("target gap outside the configured range is reported", () => {
  // Stops 30px short — still visually near the frame, outside gap_range [9, 15].
  const out = run([A, B, arrow("a_default --> b_default", [100, 50], [150, 50], [170, 50])]);
  const f = tagged(out, "[arrow]").find((i) => /target gap 30px/.test(i.msg));
  assert.ok(f, JSON.stringify(out));
  assert.strictEqual(f.grade, "warning");
  assert.strictEqual(f.node, "v:a_default --> b_default");
});

test("audit-flow: orphan arrow is blocking, edge offset is a warning", () => {
  // The target frame does not exist: the connection points nowhere.
  const orphan = run([A, arrow("a_default --> gone_default", [100, 50], [150, 50], [190, 50])]);
  const o = tagged(orphan, "[arrow]").find((i) => /orphan/.test(i.msg));
  assert.ok(o, JSON.stringify(orphan));
  assert.strictEqual(o.grade, "blocking");
  assert.strictEqual(o.node, "v:a_default --> gone_default");
  assert.ok(!o.msg.startsWith("["), "the tag moved to `tag`");
  assert.strictEqual(orphan.pass, false);
  // The connection is right and only the start is 20px inside the source.
  const off = run([A, B, arrow("a_default --> b_default", [80, 50], [150, 50], [190, 50])]);
  const e = tagged(off, "[arrow]").find((i) => /start off the edge/.test(i.msg));
  assert.strictEqual(e.grade, "warning");
  assert.strictEqual(off.pass, false, "a warning is still a finding");
});

test("a start that is off the source edge is reported", () => {
  // Begins 20px inside A rather than on its edge.
  const out = run([A, B, arrow("a_default --> b_default", [80, 50], [150, 50], [190, 50])]);
  assert.ok(tagged(out, "[arrow]").some((i) => /start off the edge by 20px/.test(i.msg)), JSON.stringify(out));
});

test("a start far along the edge's line is off the edge", () => {
  // Sits on A's top line (y = 0) but 5000px to the right of the frame. The infinite line passes
  // it, so a line-based distance reports 0; the frame's boundary is 4900px away.
  const out = run([A, B, arrow("a_default --> b_default", [5000, 0], [5000, 50], [190, 50])]);
  assert.ok(tagged(out, "[arrow]").some((i) => /start off the edge by/.test(i.msg)), JSON.stringify(out));
});

test("an arrowhead 10px away still fails when its last segment runs parallel to the edge", () => {
  // This is the case distance alone cannot catch: the head sits inside gap_range, but the
  // final segment is vertical against a vertical edge, so it points at empty space beside B.
  const out = run([A, B, arrow("a_default --> b_default", [100, 50], [190, 20], [190, 50])]);
  const f = tagged(out, "[arrow]").find((i) => /arrowhead parallel to the target edge/.test(i.msg));
  assert.ok(f, JSON.stringify(out));
  assert.strictEqual(f.grade, "warning");
  assert.ok(!out.findings.some((i) => /target gap/.test(i.msg)), "the gap itself is within range");
});

test("a segment crossing an unrelated frame is reported", () => {
  // C sits between A and B, directly under the line.
  const C = frame("c_default", 130, 30);
  C.width = 40; C.height = 40;
  const out = run([A, B, C, arrow(...GOOD), arrow("c_default --> b_default", [170, 70], [200, 70], [190, 50])]);
  const f = tagged(out, "[arrow]").find((i) => /passes through c_default/.test(i.msg));
  assert.ok(f, JSON.stringify(out));
  assert.strictEqual(f.grade, "blocking");
});

test("a frame on no flow at all is reported as a coverage orphan", () => {
  const out = run([A, B, frame("d_default", 0, 300), arrow(...GOOD)]);
  const f = tagged(out, "[coverage]").find((i) => /orphan frame .*d_default/.test(i.msg));
  assert.ok(f, JSON.stringify(out));
  assert.strictEqual(f.grade, "blocking");
  assert.strictEqual(f.node, "f:d_default");
});

test("a [state] link must be a two-vertex vertical line", () => {
  const D = frame("a_empty", 0, 200);
  // Elbowed rather than straight — an elbow can curl over its own endpoints and slip
  // past the pass-through check, so shape is enforced before position.
  const out = run([A, B, D, arrow(...GOOD), arrow("[state] a_default ~ a_empty", [50, 100], [80, 150], [50, 200])]);
  const f = tagged(out, "[state]").find((i) => /not vertical \/ elbowed/.test(i.msg));
  assert.ok(f, JSON.stringify(out));
  assert.strictEqual(f.grade, "warning");
});

test("a straight [state] link between the same two frames reports nothing", () => {
  const D = frame("a_empty", 0, 200);
  assert.deepStrictEqual(
    run([A, B, D, arrow(...GOOD), arrow("[state] a_default ~ a_empty", [50, 100], [50, 200])]),
    PASS
  );
});

// ── Nested sections ────────────────────────────────────────────────────────────
// A section's children are relative to it and nested sections compose: the frames below sit at
// abs (150, 100) and (350, 100), and the arrow's own x/y are relative to the inner section too.
const runNested = (children, cfg = CFG) =>
  new Function("CFG", "figma", SRC)(cfg, {
    currentPage: {
      name: "[UI] Fixture",
      children: [{
        type: "SECTION", name: "Outer", x: 100, y: 100, children: [
          { type: "SECTION", name: "Inner", x: 50, y: 0, children },
        ],
      }],
    },
  });

test("an arrow inside a nested section is audited", () => {
  const out = runNested([A, B, arrow("a_default --> b_default", [100, 50], [150, 50], [170, 50])]);
  assert.ok(tagged(out, "[arrow]").some((i) => /target gap 30px/.test(i.msg)), JSON.stringify(out));
});

test("a well-formed arrow inside a nested section passes", () => {
  assert.deepStrictEqual(runNested([A, B, arrow(...GOOD)]), PASS);
});

test("an arrow inside an excluded parent is not audited, at any depth", () => {
  const cfg = { ...CFG, pages: { exclude_sections: ["^Outer$"] } };
  const out = runNested([A, B, arrow("a_default --> b_default", [100, 50], [150, 50], [170, 50])], cfg);
  assert.deepStrictEqual(out, PASS);
});

test("a frame inside an excluded section still blocks a line passing through it", () => {
  // Outer is excluded; the live arrow in S2 crosses the excluded frame, which stays in the dictionary.
  const cfg = { ...CFG, pages: { exclude_sections: ["^Outer$"] } };
  const X = frame("x_default", 130, 30); X.width = 40; X.height = 40;
  const out = new Function("CFG", "figma", SRC)(cfg, {
    currentPage: { name: "[UI] Fixture", children: [
      { type: "SECTION", name: "Outer", x: 0, y: 1000, children: [
        { type: "SECTION", name: "Inner", x: 0, y: 0, children: [X] } ] },
      { type: "SECTION", name: "S2", x: 0, y: 1000, children: [A, B, arrow(...GOOD)] },
    ] },
  });
  const f = tagged(out, "[arrow]").find((i) => /passes through x_default/.test(i.msg));
  assert.ok(f, JSON.stringify(out));
  assert.strictEqual(f.grade, "blocking");
});
