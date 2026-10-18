#!/usr/bin/env python3
"""Repository consistency check — every plugin registered in the marketplace.

    python3 tools/verify.py      # this check alone
    bash tools/verify-all.sh     # this plus every fixture — the list CI runs

Run this after editing a skill. It is the regression gate for as long as `plugin eval` stays
behind early access. It checks one thing: has the documentation drifted from the reality —
a config key a skill references that is not in the schema, a skill it points at that does not
exist, a skill no README introduces, a section one language's README has and the other does not,
a version with no changelog entry, a team-specific value left in.

What it cannot do is read a sentence and judge whether it is still true. That half is a checklist,
in CLAUDE.md at the repository root.

This is a repository development tool, so it does not live inside a plugin. It never ships to an install.

Exit code 0 pass / 1 violations.
"""
import json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKET = REPO / ".claude-plugin" / "marketplace.json"

# A skill's description is loaded into every session that has the plugin installed, so its length is
# a standing cost. Over the limit is reported as a warning for now; Phase 3 turns it into a failure.
DESC_LIMIT = 500
DESC_LIMIT_OVERRIDE = {("fig", "deck"): 700, ("pm", "task"): 700}

# The team config filename differs per plugin. Only fig keeps the older name (it is a file already in use)
TEAM_FILE = {"fig": "figma-conventions.yaml"}

# Files that live as copies across plugins. Let them diverge and one gets fixed while the other ships —
# during the fig rework the audit code had already split into three copies. Keep the copies, but check they match.
# Config paths below which the keys are named by the user, not by the schema:
# a fileKey, an environment name, a project the team happens to have, a tracker's
# own field ids. The schema declares the map; its members cannot be checked.
FREE_KEY_MAPS = (
    "files.", "qa.environments.",
    "task.mirror_extras.", "task.label_map.", "task.assignee_map.",
    "task.status_map.", "task.field_owner.", "task.required_fields.",
    "task.hierarchy.milestone_format.",
)

SHARED = ["_common/scripts/lib/resolve-config.py", "_common/scripts/lib/preflight.py",
          "hooks/shared-config.py", "hooks/hooks.json"]

fails, warns, counts = [], [], []


# Team-value check. **One pattern at a time** — joining several with | tangles the escaping
# and silently returns zero (one case was actually missed that way).
#
# Two layers. A value that differs per team and a value that **identifies** a team are different things.
#   · SKILL.md carries judgement only, so no value belongs in it → check all of them
#   · conventions defaults and READMEs exist to carry values. But anything pointing at someone
#     else's company — a brand colour, a product name, a document id — must not ship → check identifiers only
#
# The strings themselves name a company, so they are not written in this file: a checker that
# carries them is the leak it exists to prevent. They live in tools/team-strings.local.txt, which
# is gitignored — one per line, `!` prefix for an identifier. See team-strings.example.txt.
# Without that file the check is skipped and says so, rather than passing quietly.
def load_team_strings():
    p = Path(__file__).resolve().parent / "team-strings.local.txt"
    if not p.exists():
        warns.append("no tools/team-strings.local.txt — the team-value check is skipped")
        return [], []
    team, ident = [], []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            line = line[1:].strip()
            ident.append(line)
        team.append(line)
    return team, ident


TEAM_STRINGS, IDENTITY_STRINGS = load_team_strings()


# Only **spatial numbers measured in a specific file**. One test decides it — would shipping this
# value as a default make every frame in someone else's file report as a violation?
# Style, tolerance, and statistical thresholds are defaults somebody has to pick, so overlapping with
# a team's value is normal; widening to them produces 42 warnings. A warning that is always on never gets read.
MEASURED_KEYS = {
    "layout.column_grid", "layout.section_padding", "layout.frame_gap",
    "layout.section_gap_same_row", "layout.domain_row_gap",
    "layout.section_resize_margin",
}


def leaf_kv(o, prefix=""):
    """Leaf nodes only, as (path, value)."""
    if isinstance(o, dict) and o:
        for k, v in o.items():
            p = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict) and v:
                yield from leaf_kv(v, p)
            else:
                yield p, v


def leaf_paths(o, prefix=""):
    if isinstance(o, dict) and o:
        for k, v in o.items():
            p = f"{prefix}.{k}" if prefix else k
            yield p
            yield from leaf_paths(v, p)


def check_plugin(name, root, yaml):
    """Checks one plugin. root is <repo>/plugins/<name>."""
    common = root / "_common"
    skills = root / "skills"
    example = common / "conventions.example.yaml"

    if not skills.is_dir():
        fails.append(f"[{name}] no skills/")
        return
    # The skill list comes from the directory — a hand-written list does not grow when a skill is added
    names = sorted(d.name for d in skills.iterdir() if (d / "SKILL.md").exists())
    if not names:
        fails.append(f"[{name}] no SKILL.md at all")
        return

    schema, known = {}, set()
    if example.exists():
        schema = yaml.safe_load(example.read_text()) or {}
        known = set(leaf_paths(schema))
    else:
        warns.append(f"[{name}] no conventions.example.yaml — config checks skipped")

    # Manifest
    pj = root / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        fails.append(f"[{name}] no .claude-plugin/plugin.json")
    else:
        try:
            d = json.loads(pj.read_text())
            if d.get("name") != name:
                fails.append(f"[{name}] plugin.json name mismatch: {d.get('name')}")
            if not d.get("version"):
                fails.append(f"[{name}] plugin.json has no version")
        except Exception as e:
            fails.append(f"[{name}] plugin.json failed to parse: {e}")

    # Does every team config key exist in the schema
    team = Path.home() / ".claude" / TEAM_FILE.get(name, f"{name}-conventions.yaml")
    if team.exists() and known:
        tcfg = yaml.safe_load(team.read_text()) or {}
        for p in leaf_paths(tcfg):
            # Maps whose keys the user names — a fileKey, an environment name. The schema
            # declares the map, never its members, so membership cannot be checked here.
            if any(p.startswith(f) for f in FREE_KEY_MAPS):
                continue
            if p not in known:
                fails.append(f"[{name}] key present only in the team config: {p}")

        # A bundled default identical to the team's value means a measured number shipped.
        # The whole layout section once went out byte-identical to the team config.
        # It can also coincide, so this stays a warning — a person makes the call
        tv, sv = dict(leaf_kv(tcfg)), dict(leaf_kv(schema))
        leaked = sorted(k for k in tv
                        if k in MEASURED_KEYS and k in sv
                        and tv[k] == sv[k] and tv[k] is not None)
        if leaked:
            warns.append(f"[{name}] default identical to team value: {', '.join(leaked[:6])}"
                         + (f" and {len(leaked)-6} more" if len(leaked) > 6 else "")
                         + " — check whether a measured value shipped")
    elif not team.exists():
        warns.append(f"[{name}] no team config ({team.name}) — running on bundled defaults")

    # Team values leak into the scripts too. Watching SKILL.md alone once shipped a team font
    # name left in a comment — because the check only covered the documents.
    if (common / "scripts").is_dir():
        for f in sorted((common / "scripts").rglob("*")):
            if not f.is_file() or f.suffix not in (".js", ".py", ".sh"):
                continue
            t = f.read_text(errors="ignore")
            for w in TEAM_STRINGS:
                if w in t:
                    fails.append(f"[{name}] {f.name}: team value '{w}'")

    # Script syntax
    chk = common / "scripts" / "lib" / "check.sh"
    if chk.exists():
        # Call it as `bash <path>` — running it directly relies on the executable bit,
        # which a file shipped through the GitHub Contents API does not carry (confirmed on an install).
        r = subprocess.run(["bash", str(chk)], capture_output=True, text=True)
        if r.returncode != 0:
            fails.append(f"[{name}] check.sh failed:\n" + r.stdout + r.stderr)

    cfg_ref = re.compile(r"`([a-z_]+(?:\.[a-z_]+)+)`")
    legacy_ref = re.compile(r"(?<![\w-])figma-([a-z-]+)")

    # A skill is a folder, not one file: later phases move bodies out of SKILL.md into sibling mode
    # files, so every check that reads prose reads every *.md under the skill. Only the frontmatter
    # belongs to SKILL.md alone. Skill references are checked repo-wide in check_references().
    for sk in names:
        s = (skills / sk / "SKILL.md").read_text()

        m = re.search(r"^---\n(.*?)\n---", s, re.S)
        if not m:
            fails.append(f"[{name}:{sk}] no frontmatter")
        else:
            fm = m.group(1)
            got = re.search(r"^name:\s*(\S+)", fm, re.M)
            if not got or got.group(1) != sk:
                fails.append(f"[{name}:{sk}] frontmatter name does not match the directory ({got.group(1) if got else 'missing'})")
            if "description:" not in fm:
                fails.append(f"[{name}:{sk}] no description")
            # Claude Code parses this frontmatter leniently; other installers do not. `npx skills`
            # walked our repository and silently skipped the two skills whose description carried a
            # bare `: ` — a colon and a space start a mapping in YAML, so the value stopped being a
            # string. Skipped, not failed: the skill simply was not there, and nothing said why.
            try:
                parsed = yaml.safe_load(fm)
                desc = parsed.get("description") if isinstance(parsed, dict) else None
                if isinstance(desc, str):
                    limit = DESC_LIMIT_OVERRIDE.get((name, sk), DESC_LIMIT)
                    if len(desc) > limit:
                        warns.append(f"[{name}:{sk}] description is {len(desc)} characters (limit {limit})")
            except yaml.YAMLError as e:
                where = getattr(e, "problem_mark", None)
                spot = f" (line {where.line + 1}, column {where.column + 1})" if where else ""
                fails.append(f"[{name}:{sk}] frontmatter is not valid YAML{spot}"
                             " — a strict parser drops the skill instead of reading it."
                             " Usually a `: ` inside the description")

        for f in sorted((skills / sk).rglob("*.md")):
            s = f.read_text()
            rel = f.relative_to(REPO)

            for ref in sorted(set(cfg_ref.findall(s))):
                if ref.split(".")[0] not in schema:   # skip code expressions that are not config paths
                    continue
                if ref not in known:
                    fails.append(f"[{name}:{sk}] {rel}: `{ref}` is not in the schema")

            # Script paths must use the plugin root variable — an absolute path breaks when the install location changes
            if "~/.claude/skills/" in s:
                fails.append(f"[{name}:{sk}] {rel}: an absolute path is left in (replace with ${{CLAUDE_PLUGIN_ROOT}})")

            for w in TEAM_STRINGS:
                if w in s:
                    fails.append(f"[{name}:{sk}] {rel}: team value '{w}'")

    # Every ${CLAUDE_PLUGIN_ROOT}/… a document points at must exist. A renamed script and a
    # skill still naming the old path fail only at run time, in someone else's install.
    for f in sorted(list(skills.rglob("SKILL.md")) + list(common.rglob("*.md")) + [root / "README.md"]):
        if not f.exists():
            continue
        for ref in sorted(set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", f.read_text()))):
            target = root / ref.rstrip("./")
            if not target.exists():
                fails.append(f"[{name}] {f.relative_to(root)} → ${{CLAUDE_PLUGIN_ROOT}}/{ref} does not exist")

    # An adapter has to say which connector it runs on and which sides it answers for — preflight
    # reads the first, adapter.py the second. The bundled ones are held to it; a person's own can
    # omit both and is then taken to serve every side.
    allowed = set()
    for sk in names:
        m = re.search(r"^allowed-tools:\s*(.*)$", (skills / sk / "SKILL.md").read_text(), re.M)
        if m:
            allowed.update(t.strip() for t in m.group(1).split(","))
    ROLE_WORDS = {"trackers": {"record", "mirror"}, "sources": {"chat", "calendar"}}
    for kind, words in ROLE_WORDS.items():
        d = common / kind
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if f.name in ("README.md", "_template.md"):
                continue
            head = "\n".join(f.read_text().splitlines()[:12])
            if not re.search(r"^connector:\s*\S", head, re.M):
                fails.append(f"[{name}] {kind}/{f.name}: no `connector:` line — preflight cannot tell which connector this type needs")
            rm = re.search(r"^roles:\s*(.+)$", head, re.M)
            if not rm:
                fails.append(f"[{name}] {kind}/{f.name}: no `roles:` line — adapter.py cannot tell which side it answers for")
            else:
                bad = {r.strip() for r in rm.group(1).split(",")} - words
                if bad:
                    fails.append(f"[{name}] {kind}/{f.name}: roles {sorted(bad)} — for {kind} they are {sorted(words)}")
            # The tools an adapter names have to be ones some skill is allowed to call, or the
            # first call prompts for permission and reads as the skill hanging
            for tool in sorted(set(re.findall(r"\b(slack_[a-z_]+|notion-[a-z-]+|list_events|search_files|read_file_content|get_file_metadata)\b", f.read_text()))):
                if not any(tool in a for a in allowed):
                    fails.append(f"[{name}] {kind}/{f.name} names `{tool}`, which no skill's allowed-tools carries")

    # Every skill has to be introduced where a reader goes looking for one. The three READMEs each
    # open with a table of commands, and a skill added without a row there exists for whoever wrote
    # it and nobody else — which is exactly how the Korean README came to name /pm:log in its
    # requirements table without ever saying what /pm:log is.
    #
    # The skills table is the one naming the MOST of this plugin's commands, one per row. Other
    # tables mention commands too — what each skill needs, prerequisites — but a row there is
    # usually several commands in one cell, and never the whole set. Picking by count rather than
    # by position means reordering the document cannot change which table is judged.
    row_cmd = re.compile(rf"^`/{name}:([a-z-]+)`$")
    for f in (root / "README.md", REPO / "README.md", REPO / "README.ko.md"):
        if not f.exists():
            continue
        block, blocks = 0, {}
        for line in f.read_text().splitlines():
            if not line.startswith("|"):
                block += 1
                continue
            cells = line.split("|")
            m = row_cmd.match(cells[1].strip()) if len(cells) > 2 else None
            if m:
                blocks.setdefault(block, set()).add(m.group(1))
        if not blocks:
            fails.append(f"[{name}] {f.name}: no table of commands at all — the skills are never introduced")
            continue
        listed = max(blocks.values(), key=len)
        missing = sorted(set(names) - listed)
        if missing:
            fails.append(
                f"[{name}] {f.name}: the skills table is missing {', '.join('/' + name + ':' + s for s in missing)}"
                " — a skill nobody introduces is one nobody runs")

    # A version bump with no changelog entry loses the only account of what changed. The manifest
    # is the version people install; the changelog is where they read why.
    ch = root / "CHANGELOG.md"
    ver = json.loads((root / ".claude-plugin" / "plugin.json").read_text()).get("version") if (root / ".claude-plugin" / "plugin.json").exists() else None
    if ver and ch.exists() and not re.search(rf"^##\s+{re.escape(ver)}\b", ch.read_text(), re.M):
        fails.append(f"[{name}] CHANGELOG.md has no entry for {ver} — the version people install is undocumented")

    # A skill count written into prose is wrong the day a skill is added. The list of skills is
    # the directory; prose says "the skills" or lists them, never a number
    COUNT_WORDS = r"(\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|twenty)"
    for f in [root / "README.md", REPO / "README.md", REPO / "README.ko.md", MARKET] + sorted((REPO / ".github").glob("*.html")):
        if not f.exists():
            continue
        t = f.read_text()
        for m in re.finditer(rf"\b{COUNT_WORDS} (skills|in all)\b|스킬 (\d+|한|두|세|네|다섯|여섯|일곱|여덟|아홉|열\S*) *개|(\d+) *개의? 스킬", t, re.I):
            fails.append(f"[{name}] {f.name}: a skill count in prose — '{m.group(0)}' goes stale; list the skills or say 'the skills'")

    # Identifiers leak outside SKILL.md too, so these files are read for them. (Skill-name references
    # in the same files are check_references()'s job.)
    for f in (example, root / "README.md", REPO / "README.md", REPO / "README.ko.md"):
        if not f.exists():
            continue
        t = f.read_text()
        for w in IDENTITY_STRINGS:
            if w in t:
                fails.append(f"[{name}] {f.name}: identifier '{w}' — the shipped copy points at someone else's company")
        # (skill references in these files are checked by check_references())
        if f.parent == REPO:
            continue                              # the root READMEs name the official figma-* skills on purpose
        for ref in sorted(set(legacy_ref.findall(t))):
            if ref == "conventions":              # figma-conventions.yaml is a config filename
                continue
            fails.append(f"[{name}] {f.name}: old name 'figma-{ref}'")

    counts.append(f"{name} {len(names)} skills / {len(known)} keys")


# A reference to a skill can sit in any document and name either plugin. The lookbehind keeps a URL
# or a path (`example.com/a/pm:b`) from reading as a command. CHANGELOGs are never scanned — they
# name skills that no longer exist, on purpose.
SKILL_REF = re.compile(r"(?<![\w/.-])/(fig|pm):([a-z][a-z-]*)")


def check_references(plugins: dict[str, set[str]]) -> None:
    """Every /plugin:skill a shipped document names must be a skill that exists, in either plugin."""
    targets = []                                   # (file, tag)
    for p in sorted(plugins):
        root = REPO / "plugins" / p
        for f in sorted((root / "skills").rglob("*.md")):
            sk = f.relative_to(root / "skills").parts[0]
            targets.append((f, f"{p}:{sk}"))
        for pat in ("*.md", "*.py"):
            targets += [(f, p) for f in sorted((root / "_common").rglob(pat))]
        targets += [(root / "README.md", p),
                    (root / "_common" / "conventions.example.yaml", p)]   # a comment there once kept a pre-rename name
    targets += [(REPO / "README.md", "repo"), (REPO / "README.ko.md", "repo")]
    targets += [(f, "repo") for f in sorted((REPO / ".github").glob("*.html"))]

    for f, tag in targets:
        if not f.is_file():
            continue
        text = f.read_text(errors="ignore")
        for plug, ref in sorted(set(SKILL_REF.findall(text))):
            if ref not in plugins.get(plug, set()):
                fails.append(f"[{tag}] {f.relative_to(REPO)} → /{plug}:{ref} does not exist")


def main():
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML required")

    if not MARKET.exists():
        sys.exit(f"marketplace not found: {MARKET}")
    market = json.loads(MARKET.read_text())
    entries = market.get("plugins", [])
    if not entries:
        sys.exit("marketplace.json has no plugins entry")

    roots = {}
    for e in entries:
        name, src = e.get("name"), e.get("source")
        if not isinstance(src, str):
            warns.append(f"[{name}] source is not a local path — skipped")
            continue
        root = (REPO / src).resolve()
        if not root.is_dir():
            fails.append(f"[{name}] source path does not exist: {src}")
            continue
        roots[name] = root
        check_plugin(name, root, yaml)

        # One description per plugin: plugin.json is the source, the marketplace entry repeats it.
        pj = root / ".claude-plugin" / "plugin.json"
        if pj.exists() and json.loads(pj.read_text()).get("description") != e.get("description"):
            fails.append(f"[{name}] plugin.json and marketplace.json descriptions differ")

    # After every plugin is known: a reference may name the other plugin's skills
    check_references({n: {d.name for d in (r / "skills").iterdir() if (d / "SKILL.md").exists()}
                      for n, r in roots.items()})

    # Files outside plugins/ ship too — the repository is public, so a diagram, a dev checklist or a
    # tool carries a team's name just as far as a SKILL.md does. The per-plugin check never looked
    # at them, because it walks a plugin's own directory.
    #
    # Strict where the file has no reason to hold a value (a checklist, a tool), identifiers only
    # where it does: the READMEs and the diagrams show example config, and an example config is
    # values.
    repo_files = [(REPO / "CLAUDE.md", TEAM_STRINGS)]
    repo_files += [(f, TEAM_STRINGS) for f in sorted((REPO / "tools").glob("*.py")) + sorted((REPO / "tools").glob("*.sh"))]
    repo_files += [(f, IDENTITY_STRINGS) for f in sorted((REPO / ".github").rglob("*.html"))]
    repo_files += [(f, IDENTITY_STRINGS) for f in sorted((REPO / ".github" / "workflows").glob("*.yml"))]
    for f, words in repo_files:
        if not f.exists():
            continue
        t_ = f.read_text(errors="ignore")
        for w in words:
            if w in t_:
                fails.append(f"[repo] {f.relative_to(REPO)}: team value '{w}' — this repository is public")

    # The two root READMEs are one document in two languages, so they drift the way a translation
    # drifts: something is added to the English and the Korean is never opened. It went unnoticed
    # for four days that the Korean README had no /pm:log section at all.
    #
    # Two signals, both cheap. The set of commands each names, and how many headings each carries
    # per level. A whole section added on one side moves the second number; a command added to a
    # table moves the first.
    en, ko = REPO / "README.md", REPO / "README.ko.md"
    if en.exists() and ko.exists():
        cmd = re.compile(rf"/(?:{'|'.join(map(re.escape, roots))}):[a-z-]+")
        te, tk = en.read_text(), ko.read_text()
        for label, only in (("README.md", set(cmd.findall(te)) - set(cmd.findall(tk))),
                            ("README.ko.md", set(cmd.findall(tk)) - set(cmd.findall(te)))):
            if only:
                other = "README.ko.md" if label == "README.md" else "README.md"
                fails.append(f"[docs] {' '.join(sorted(only))} appears in {label} but not in {other}")
        head = lambda s: {n: len(re.findall(rf"^#{{{n}}} ", s, re.M)) for n in (2, 3)}
        he, hk = head(te), head(tk)
        if he != hk:
            diff = ", ".join(f"{'#' * n} {he[n]} vs {hk[n]}" for n in he if he[n] != hk[n])
            fails.append(f"[docs] README.md and README.ko.md have different sections ({diff})"
                         " — one side gained a section the other never got")

    # Have the shared copies diverged
    for rel in SHARED:
        seen = {}
        for name, root in roots.items():
            f = root / rel
            if f.exists():
                seen.setdefault(f.read_bytes(), []).append(name)
        if len(seen) > 1:
            groups = " vs ".join("+".join(v) for v in seen.values())
            fails.append(f"[shared] copies of {rel} have diverged: {groups}")

    # The audit scripts are sent to the Figma sandbox one file at a time and cannot import a helper,
    # so the section walker is pasted into each between markers. Compare the marked blocks.
    for root in roots.values():
        blocks = {}
        for f in sorted((root / "_common" / "scripts").glob("audit-*.js")):
            m = re.search(r"// <sections-deep>\n.*?// </sections-deep>", f.read_text(encoding="utf-8"), re.S)
            blocks[f.name] = m.group(0) if m else None   # a deleted marker must not pass as "no copy"
        if any(blocks.values()):
            ref = next(b for b in blocks.values() if b)
            for name, b in blocks.items():
                if b != ref:
                    fails.append(f"[fig] sections-deep copies differ: {name}")

    print("=" * 60)
    for x in warns:
        print("WARN ", x)
    for x in fails:
        print("FAIL ", x)
    print("=" * 60)
    print("plugins " + " · ".join(counts) + f" · {len(fails)} violations · {len(warns)} warnings")
    print("PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
