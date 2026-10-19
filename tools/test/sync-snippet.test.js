/* Runs /fig:sync's name-matched comparison snippet, as written in its SKILL.md, against fake pages.
 *
 *     node --test tools/test/sync-snippet.test.js
 *
 * The snippet is prose a model copies into use_figma, so it is lifted out of the document rather than
 * kept as a second copy here. It reads `CFG`, `figma`, `CANON_PAGE_ID` and `PAGE_ID` and returns one
 * entry per working frame; these cases hold its buckets to the rules the document states.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const DOC = readFileSync(
  join(__dirname, "..", "..", "plugins", "fig", "skills", "sync", "SKILL.md"),
  "utf8"
);
const after = DOC.split("**Name-matched text comparison", 2)[1] || "";
const SRC = (after.match(/```js\n([\s\S]*?)```/) || [])[1] || "";
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

// ---- fake Figma nodes ------------------------------------------------------------------------------
let seq = 0;
const walk = (n, pred, acc = []) => {
  for (const c of n.children || []) {
    if (pred(c)) acc.push(c);
    walk(c, pred, acc);
  }
  return acc;
};
const text = (characters) => ({ type: "TEXT", id: `t${++seq}`, characters, children: [] });
const instance = (masterId) => ({
  type: "INSTANCE", id: `i${++seq}`, children: [],
  getMainComponentAsync: async () => ({ id: masterId }),
});
const frame = (name, strings, { height = 800, masters = [] } = {}) => {
  const f = {
    type: "FRAME", id: `f${++seq}`, name, height,
    children: [...strings.map(text), ...masters.map(instance)],
  };
  f.findAll = (pred) => walk(f, pred);
  return f;
};
const section = (name, children) => ({ type: "SECTION", id: `s${++seq}`, name, children });
const page = (id, children) => ({ type: "PAGE", id, children });

const baseCfg = (over = {}) => ({
  naming: { frame_pattern: "^.+-[^-\\s]+$", ...(over.naming || {}) },
  pages: { exclude_sections: [], ...(over.pages || {}) },
  sync: { text_diff_max_len: 40 },
});

const run = async (canonChildren, workChildren, cfg = baseCfg()) => {
  assert.ok(SRC, "the name-matched comparison snippet was not found in sync/SKILL.md");
  const pages = { CANON: page("CANON", canonChildren), WORK: page("WORK", workChildren) };
  const figma = {
    getNodeByIdAsync: async (id) => pages[id],
    setCurrentPageAsync: async () => {},
  };
  return new AsyncFunction("CFG", "figma", "CANON_PAGE_ID", "PAGE_ID", SRC)(cfg, figma, "CANON", "WORK");
};
const one = (out, name) => out.find((o) => o.frame === name);

// ---- I1 / I2: which side a difference sits on decides the bucket ------------------------------------
test("a working-only string missing from canonical → not applied", async () => {
  const out = await run(
    [section("01. Account", [frame("Login-Default", ["Log in", "Email"])])],
    [section("01. Account", [frame("Login-Default", ["Log in", "Email", "Forgot password?"])])]
  );
  const r = one(out, "Login-Default");
  assert.strictEqual(r.bucket, "not applied", JSON.stringify(r));
  assert.deepStrictEqual(r.onlyWorking, ["Forgot password?"]);
});

test("only canonical-only strings differ → needs checking, may be later work", async () => {
  const out = await run(
    [section("01. Account", [frame("Login-Default", ["Log in", "Email", "Sign in with SSO"])])],
    [section("01. Account", [frame("Login-Default", ["Log in", "Email"])])]
  );
  const r = one(out, "Login-Default");
  assert.strictEqual(r.bucket, "needs checking", JSON.stringify(r));
  assert.deepStrictEqual(r.onlyCanonical, ["Sign in with SSO"]);
  assert.match(JSON.stringify(r), /may be later work/);
});

test("mixed frame → not applied, its canonical-only strings flagged to confirm", async () => {
  const out = await run(
    [section("01. Account", [frame("Login-Default", ["Sign in", "Email", "Sign in with SSO"])])],
    [section("01. Account", [frame("Login-Default", ["Log in", "Email"])])]
  );
  const r = one(out, "Login-Default");
  assert.strictEqual(r.bucket, "not applied", JSON.stringify(r));
  assert.deepStrictEqual(r.onlyWorking, ["Log in"]);
  assert.deepStrictEqual(r.onlyCanonical.sort(), ["Sign in", "Sign in with SSO"]);
  assert.match(JSON.stringify(r), /may be later work — confirm/);
});

test("identical text, same height, same component masters → applied", async () => {
  const out = await run(
    [frame("Login-Default", ["Log in", "Email"], { height: 812, masters: ["M1", "M2"] })],
    [frame("Login-Default", ["Email", "Log in"], { height: 812, masters: ["M2", "M1"] })]
  );
  assert.strictEqual(one(out, "Login-Default").bucket, "applied", JSON.stringify(out));
});

test("identical text but the height differs → needs checking", async () => {
  const out = await run(
    [frame("Login-Default", ["Log in", "Email"], { height: 812, masters: ["M1"] })],
    [frame("Login-Default", ["Log in", "Email"], { height: 900, masters: ["M1"] })]
  );
  assert.strictEqual(one(out, "Login-Default").bucket, "needs checking", JSON.stringify(out));
});

test("identical text and height but a component master differs → needs checking", async () => {
  const out = await run(
    [frame("Login-Default", ["Log in", "Email"], { height: 812, masters: ["M1"] })],
    [frame("Login-Default", ["Log in", "Email"], { height: 812, masters: ["M9"] })]
  );
  assert.strictEqual(one(out, "Login-Default").bucket, "needs checking", JSON.stringify(out));
});

test("no canonical twin → new, not applied", async () => {
  const out = await run([], [frame("Signup-Default", ["Create account"])]);
  const r = one(out, "Signup-Default");
  assert.strictEqual(r.mode, "new");
  assert.strictEqual(r.bucket, "not applied");
});

// ---- I5: the name test is the file's own pattern -----------------------------------------------------
test("a name failing naming.frame_pattern → unmatched by name, asked", async () => {
  const cfg = baseCfg({ naming: { frame_pattern: "^[A-Z][A-Za-z]+_[A-Za-z]+$" } });
  const out = await run(
    [frame("Login_Default", ["Log in"]), frame("Login-Default", ["Log in"])],
    [frame("Login_Default", ["Log in"]), frame("Login-Default", ["Log in"])],
    cfg
  );
  // Login_Default passes this file's own pattern even though it has no hyphen; Login-Default fails it
  assert.notStrictEqual(one(out, "Login_Default").mode, "unmatched", JSON.stringify(out));
  assert.strictEqual(one(out, "Login-Default").mode, "unmatched", JSON.stringify(out));
});

test("naming.frame_pattern null → match by exact name, never unmatched for its shape", async () => {
  const cfg = baseCfg({ naming: { frame_pattern: null } });
  const out = await run(
    [frame("Login screen", ["Log in"])],
    [frame("Login screen", ["Log in"]), frame("Frame 12", ["Draft"])],
    cfg
  );
  assert.ok(!out.some((o) => o.mode === "unmatched"), JSON.stringify(out));
  assert.strictEqual(one(out, "Login screen").bucket, "applied", JSON.stringify(out));
  assert.strictEqual(one(out, "Frame 12").mode, "new", JSON.stringify(out));
});

// ---- Minor 6: excluded sections are skipped on the canonical page too ---------------------------------
test("a reference copy in an excluded canonical section does not make a screen ambiguous", async () => {
  const cfg = baseCfg({ pages: { exclude_sections: ["^Reference$"] } });
  const out = await run(
    [
      section("01. Account", [frame("Login-Default", ["Log in"])]),
      section("Reference", [frame("Login-Default", ["Log in (old)"])]),
    ],
    [frame("Login-Default", ["Log in"])],
    cfg
  );
  const r = one(out, "Login-Default");
  assert.notStrictEqual(r.mode, "ambiguous", JSON.stringify(r));
  assert.strictEqual(r.bucket, "applied", JSON.stringify(r));
});

test("a repeated canonical name outside excluded sections stays ambiguous → needs checking", async () => {
  const out = await run(
    [section("01. Account", [frame("Login-Default", ["Log in"])]), section("02. Other", [frame("Login-Default", ["Log in"])])],
    [frame("Login-Default", ["Log in"])]
  );
  const r = one(out, "Login-Default");
  assert.strictEqual(r.mode, "ambiguous");
  assert.strictEqual(r.bucket, "needs checking");
});
