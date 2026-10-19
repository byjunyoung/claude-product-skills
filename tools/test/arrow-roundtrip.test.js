/* Round trip: arrows drawn by arrow-build.js must pass audit-flow.js.
 *
 *     node --test tools/test/
 *
 * Each script has its own tests against hand-made fixtures, so they can agree with their fixtures
 * and still disagree with each other. Here the real arrow-build draws into a fake figma that
 * records the vectors it creates, and the resulting page goes to the real audit-flow.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const DIR = join(__dirname, "..", "..", "plugins", "fig", "_common", "scripts");
const BUILD = readFileSync(join(DIR, "arrow-build.js"), "utf8");
const AUDIT = readFileSync(join(DIR, "audit-flow.js"), "utf8");

const CFG = {
  naming: { arrow_delimiter: " --> ", state_chain_delimiter: " ~ ", label_prefix: "[label] ", state_chain_prefix: "[state] " },
  arrows: { audit: { edge_tolerance: 2, gap_range: [9, 15], label_clear: 30 } },
  pages: {},
};

const frame = (name, x, y, w = 100, h = 100) => ({ type: "FRAME", id: "f:" + name, name, x, y, width: w, height: h });
const section = (name, y, children) => ({
  type: "SECTION", id: "s:" + name, name, x: 0, y, children,
  appendChild(c) { this.children.push(c); },
});

// Records every vector arrow-build creates; the vector keeps its network where Figma's does.
const fakeFigma = () => {
  let n = 0;
  return {
    createVector: () => ({
      type: "VECTOR", id: "v" + ++n, x: 0, y: 0,
      async setVectorNetworkAsync(net) { this.vectorNetwork = net; },
    }),
  };
};

const draw = async (sections, steps) => {
  const figma = fakeFigma();
  const lib = new Function("CFG", "figma", BUILD + "\nreturn { straight, trunkElbow, detour, stateLink };")(CFG, figma);
  for (const step of steps) await step(lib);
  return new Function("CFG", "figma", AUDIT)(CFG, { currentPage: { name: "[UI] Fixture", children: sections } });
};

const PASS = { pass: true, findings: [] };

test("straight, elbow and detour arrows drawn by arrow-build pass audit-flow", async () => {
  // 1. side by side
  const s1 = section("S1", 0, [frame("a1", 0, 200), frame("b1", 200, 200)]);
  // 2. offset in both axes, the target lower and further right
  const s2 = section("S2", 1000, [frame("a2", 0, 200), frame("b2", 300, 400)]);
  // 3. a frame in between: the long hop detours over it through the corridor above the row
  const s3 = section("S3", 2000, [frame("a3", 0, 200), frame("m3", 150, 200), frame("c3", 300, 200)]);
  const out = await draw([s1, s2, s3], [
    L => L.straight(s1, "a1", "b1"),
    L => L.trunkElbow(s2, "a2", "b2"),
    L => L.straight(s3, "a3", "m3"),
    L => L.straight(s3, "m3", "c3"),
    L => L.detour(s3, "a3", "c3"),
  ]);
  assert.deepStrictEqual(out, PASS);
});

test("a state link drawn by arrow-build passes audit-flow", async () => {
  const s = section("S1", 0, [frame("p_default", 0, 200), frame("p_empty", 0, 400)]);
  const out = await draw([s], [L => L.stateLink(s, "p_default", "p_empty")]);
  assert.deepStrictEqual(out, PASS);
});
