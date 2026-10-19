/* Every tag an audit script can emit has a row in lint's severity table, and every tag in the
 * table is emitted by some script. The grade lives in the scripts; the table is the reader's
 * explanation of them, so the two have to name the same tags.
 *
 *     node --test tools/test/
 *
 * Rows for a missing required state ("Missing required state ...") are prose, judged by the agent
 * from a screenshot, and no script emits them — they carry no backticked tag and are exempt by name.
 */
const { test } = require("node:test");
const assert = require("node:assert");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");

const ROOT = join(__dirname, "..", "..", "plugins", "fig");
const SCRIPTS = ["audit-struct.js", "audit-flow.js", "audit-component.js"];

const LINT = readFileSync(join(ROOT, "skills", "lint", "SKILL.md"), "utf8");

// The table rows between the "## Severity" heading and the next heading.
const severity = LINT.split(/^## Severity/m)[1].split(/^## /m)[0];
const rows = severity.split("\n").filter((l) => l.startsWith("|") && !/^\|[-| ]+\|$/.test(l));
const EXEMPT = /^\|\s*Missing required state/;

const tableTags = new Set();
for (const row of rows) {
  if (EXEMPT.test(row)) continue;
  const firstCell = row.split("|")[1];
  for (const m of firstCell.matchAll(/`(\[[^\]`]+\])/g)) tableTags.add(m[1]);
}
tableTags.delete("[In the output]");

// Emit sites: add("[tag]", ...) in struct and flow, { tag: "[tag]", ... } in component.
const emitted = new Map();
for (const name of SCRIPTS) {
  const src = readFileSync(join(ROOT, "_common", "scripts", name), "utf8");
  for (const m of src.matchAll(/(?:\badd\(\s*|\btag:\s*)"(\[[^"]+\])"/g)) {
    if (!emitted.has(m[1])) emitted.set(m[1], new Set());
    emitted.get(m[1]).add(name);
  }
}

test("every tag a script can emit has a row in lint's severity table, and every table tag is emitted by some script", () => {
  assert.ok(tableTags.size >= 15, "the table parse found its rows: " + [...tableTags]);
  assert.ok(emitted.size >= 15, "the script parse found its emit sites: " + [...emitted.keys()]);
  const noRow = [...emitted.keys()].filter((t) => !tableTags.has(t));
  const noEmit = [...tableTags].filter((t) => !emitted.has(t));
  assert.deepStrictEqual(noRow, [], "emitted but not in lint's severity table");
  assert.deepStrictEqual(noEmit, [], "in lint's severity table but emitted by no script");
});

// ── The grade in the table equals the grade at every emit site ──
// [arrow] and [state] split by wording: "orphan" / "passes through" are blocking, geometry is a
// warning. An emit site is matched to a row by whether its message line says one of those.
const SPLIT = new Set(["[arrow]", "[state]"]);
const SPECIAL = /orphan|passes through/;
const key = (tag, special) => (SPLIT.has(tag) ? tag + (special ? "|orphan-or-passes-through" : "|geometry") : tag);

const expected = new Map();   // key -> the grade the table states
for (const row of rows) {
  if (EXEMPT.test(row)) continue;
  const cells = row.split("|");
  const grade = cells[2].trim();
  if (!["blocking", "warning"].includes(grade)) continue;       // the header row
  for (const m of cells[1].matchAll(/`(\[[^\]`]+\])/g))
    expected.set(key(m[1], SPLIT.has(m[1]) && SPECIAL.test(cells[1])), grade);
}

const sites = [];             // { script, tag, grade, key }
for (const name of SCRIPTS) {
  const src = readFileSync(join(ROOT, "_common", "scripts", name), "utf8");
  const lines = src.split("\n");
  lines.forEach((line, i) => {
    if (/const add = /.test(line)) return;
    // add("[tag]", "grade", node, msg…)  or  { tag: "[tag]", grade: "grade", … msg: … }
    if (!/(^|[^.\w])add\(/.test(line) &&!/\btag:\s*"/.test(line)) return;
    const m = line.match(/(?:\badd\(\s*|\btag:\s*)"(\[[^"]+\])",\s*(?:grade:\s*)?"(blocking|warning)"/);
    assert.ok(m, `${name}:${i + 1} has a grade that is not a literal — resolve it or list it in this test by name`);
    const text = lines.slice(i, i + 3).join(" ");           // the message may start on the next line
    sites.push({ script: `${name}:${i + 1}`, tag: m[1], grade: m[2], key: key(m[1], SPECIAL.test(text)) });
  });
}

test("the grade in lint's table equals the grade at every emit site of that tag", () => {
  assert.ok(sites.length >= 30, "the emit-site parse found its sites: " + sites.length);
  const bad = sites.filter((s) => expected.get(s.key) !== s.grade)
    .map((s) => `${s.script} ${s.key}: script says ${s.grade}, table says ${expected.get(s.key)}`);
  assert.deepStrictEqual(bad, []);
  const seen = new Set(sites.map((s) => s.key));
  assert.deepStrictEqual([...expected.keys()].filter((k) => !seen.has(k)), [], "a table row no emit site matches");
});
