#!/usr/bin/env python3
"""Preflight — says whether this machine can actually run the skills, before one is run.

This file lives as a copy in each plugin. Change one and not the other and verify catches it.

The README's own troubleshooting says it plainly: a skill cannot call a tool it was never
given, and it does not fail loudly when one is missing — it simply cannot reach it. A first
run then looks like it did nothing. This runs before that happens and names what is absent.

Which plugin it is speaking for comes from its own path, so the two copies stay identical.

What counts as required is not fixed. Before a config exists nothing beyond the host rows can
be, because whether GitHub matters depends on a value nobody has written yet. Once the config
names a tracker, the connector it needs is required — and a setup skill that has just asked
which tools are in play passes them with --require, so the verdict means something on a
machine that has no config yet.

Usage
    python3 preflight.py                          → a report, exit 1 if a hard requirement is missing
    python3 preflight.py --quiet                  → only the lines that need attention, and the summary
    python3 preflight.py --require Notion,GitHub  → treat these connectors as required for this run

What it cannot see: Claude in Chrome is a browser extension, not an MCP server, so it does
not appear in `claude mcp list`. It is reported as unknown rather than guessed at. A Figma
seat is not visible from the shell either — the skills that write check it with `whoami`.
"""
import importlib.util, json, os, re, subprocess, sys

def plugin_name(here):
    """The plugin these scripts ship in, read from the nearest .claude-plugin/plugin.json above
    `here`. A checkout that happens to sit under a directory called pm/ is still the fig plugin.
    Falls back to the path rule when no manifest is found or it names neither plugin (a renamed
    fork); never raises."""
    try:
        d = os.path.abspath(here)
        while True:
            manifest = os.path.join(d, ".claude-plugin", "plugin.json")
            if os.path.isfile(manifest):
                with open(manifest, encoding="utf-8") as f:
                    name = json.load(f).get("name")
                if name in ("fig", "pm"):
                    return name
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    except (OSError, ValueError, AttributeError):
        pass
    return "pm" if f"{os.sep}pm{os.sep}" in here else "fig"


HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = plugin_name(HERE)
QUIET = "--quiet" in sys.argv

RULE = "=" * 60

# Connectors are named by what `claude mcp list` prints, matched case-insensitively as a
# substring. `plugin:figma` is the Figma MCP plugin; the claude.ai connectors carry that prefix.
#
# required — the plugin cannot work without it
# optional — a config key decides whether the skill ever reaches for it, so its absence is
#            a fact worth knowing, not a failure — until the config names it (see below)
CONNECTORS = {
    "fig": [
        ("plugin:figma", True, "every fig skill reads and writes Figma through it"),
        ("Notion", False, "where a config key points at a Notion page"),
        ("GitHub", False, "where task_tracker.type is github"),
        ("Slack", False, "where /fig:qa takes its request source from a thread"),
    ],
    "pm": [
        ("Notion", False, "where prd.target or the tracker is notion"),
        ("GitHub", False, "where task.mirror.type is github"),
        ("Slack", False, "where /pm:task-draft drafts from a thread"),
    ],
}

# A tool the config names is a required connector, whatever the tool. The trigger is a value
# somebody wrote — a ref, a type, a channel id — and the name comes from the resolved type, so a
# default type still counts once a ref was written against it, and a default alone never does.
# A machine that has never run setup has nothing required here, and is told so rather than
# PASSing as if that meant something.
#   (keys the user must have written, the type key, type values that need no connector, adapter kind)
NAMED_TOOLS = {
    "fig": [
        (("task_tracker.ref", "task_tracker.type"), "task_tracker.type", {"none", "markdown"}, "trackers"),
        (("qa.baseline.prd",), "qa.baseline.prd.type", {"none", "markdown"}, None),
        (("guide_source.ref", "guide_source.type"), "guide_source.type", {"none", "file", "url"}, None),
    ],
    "pm": [
        (("task.record.ref", "task.record.type"), "task.record.type", {"none", "markdown"}, "trackers"),
        (("task.mirror.ref", "task.mirror.type"), "task.mirror.type", {"none"}, "trackers"),
        (("prd.target", "prd.notion.template", "prd.notion.task_db",
          "prd.notion.inline_db.users", "prd.notion.inline_db.features"), "prd.target", {"markdown", "git"}, None),
        (("log.sources.chat_channels", "log.sources.notes_channel"), "sources.chat_type", {"none"}, "sources"),
        (("log.sources.calendar",), "sources.calendar_type", {"none"}, "sources"),
    ],
}
# How a type reads in `claude mcp list`. A type not here is looked up in its adapter file — the
# `connector:` line near the top says what the connector is called, because the type a team
# writes (gsheet) and the connector's name (Google Drive) are rarely the same word. Failing
# both, the type name itself is matched, which is at least honest about what it looked for.
# An older config wrote the PRD as one plain string, a Notion page. Where the type key resolves to
# nothing and its parent is such a string, the type is what that string always meant.
#   type key → (parent key, the type a string there stands for)
LEGACY_STRING = {"qa.baseline.prd.type": ("qa.baseline.prd", "notion")}
CONNECTOR_NAME = {"notion": "Notion", "github": "GitHub", "slack": "Slack", "google": "Google Calendar"}
COMMON = os.path.normpath(os.path.join(HERE, "..", ".."))

# Where the tracker is GitHub, the tracker adapter runs on the gh CLI, not on the connector.
# This is the config key holding the repo the check tries to open.
TRACKER_REF = {"fig": "task_tracker.ref", "pm": "task.mirror.ref"}

CHROME_SKILLS = {"fig": "/fig:proto, /fig:code and /fig:qa drive a real browser", "pm": None}
CONFIG_NAME = {"fig": "figma-conventions.yaml", "pm": "pm-conventions.yaml"}[PLUGIN]

rows, missing, required, because = [], [], {}, []      # required: lower-case name → display name


def arg_after(flag):
    argv = sys.argv[1:]
    if flag in argv and argv.index(flag) + 1 < len(argv):
        return argv[argv.index(flag) + 1]
    return None


def row(kind, name, state, note=""):
    rows.append((kind, name, state, note))
    if state == "missing":
        missing.append(name)


def dig(cfg, path):
    cur = cfg
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def run(cmd, timeout=20):
    """stdout+stderr and the return code, or None where the command is not there or hangs."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or ""), p.returncode
    except (OSError, subprocess.SubprocessError):
        return None, None


def load_config():
    """(the user's layers merged without the bundled floor, the fully resolved config, the
    (key, trigger) pairs written half-way), or (None, None, []) where no user layer exists.

    The floor is kept apart on purpose. A machine whose only config is a profile name must not
    read as "a tool required": a requirement comes from a value somebody wrote, never from a
    default nobody chose. The resolved config is still needed — for the name of the tool once
    a ref was written against a type the floor supplied. The half-written pairs are the other
    side of the same rule: a ref whose type is left to the floor reads differently whenever
    the floor changes, so it is reported rather than resolved."""
    spec = importlib.util.spec_from_file_location("resolve_config", os.path.join(HERE, "resolve-config.py"))
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        user, found = {}, False
        for p in mod.candidates(CONFIG_NAME)[1:]:
            if os.path.exists(p):
                user, found = mod.merge(user, mod.load(p)), True
        full, _ = mod.resolve(None, CONFIG_NAME)
    except (SystemExit, Exception):        # no PyYAML, no file — the host rows say which
        return None, None, []
    return (user, full, mod.unpaired(user)) if found else (None, None, [])


def written(cfg, key):
    return dig(cfg, key) not in (None, "", [], {})


def require(name, why):
    required[name.lower()] = name
    because.append(why)


def declared_connector(cfg, kind, typ):
    """The `connector:` line of the adapter for this type, or None. Same lookup as adapter.py —
    bundled first, then adapters.dirs, later covering earlier."""
    if not kind:
        return None
    dirs = [COMMON] + [os.path.expanduser(d) for d in ((cfg or {}).get("adapters") or {}).get("dirs") or [] if isinstance(d, str)]
    for d in reversed(dirs):
        path = os.path.join(d, kind, f"{typ}.md")
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="ignore") as f:
                for _ in range(12):
                    m = re.match(r"^connector:\s*(.+?)\s*$", f.readline())
                    if m:
                        return m.group(1)
            return None
    return None


def load_borrow():
    """The borrow-pm helpers, or None. Only fig borrows from pm, and only fig ships the file; a
    copy that cannot be loaded reads as "pm not found" rather than stopping the check."""
    path = os.path.join(HERE, "borrow-pm.py")
    if PLUGIN != "fig" or not os.path.exists(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("borrow_pm", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except (SystemExit, Exception):
        return None


def borrow_checks(user):
    """Where the config says task files are markdown, a handoff writes its line through pm. No pm,
    or one too old, is worth a line and never a failure: the handoff prints the line instead."""
    if str(dig(user, "task_tracker.type") or "").lower() != "markdown":
        return
    mod, pm = load_borrow(), None
    if mod:
        try:
            pm = mod.find_pm(dict(os.environ), os.getcwd())
        except Exception:
            pm = None
    if pm and mod.version_ok(pm.get("version")):
        return
    why = (f"pm {pm.get('version') or '(no version)'} is older than {mod.PM_MIN}" if pm
           else "pm is not installed here")
    row("tracker", "task_tracker.type: markdown", "attention",
        f"{why} — /fig:handoff prints its line instead of writing it into the task file")


def settle_requirements():
    for name in (arg_after("--require") or "").split(","):
        if name.strip():
            require(name.strip(), f"--require {name.strip()}")
    user, full, half = load_config()
    if user is None:
        because.append("no settings yet — nothing is needed until setup names your tools")
        return None
    named = False
    # Only the ref -> type pairs fail here. task.link_property stays a check publish and sync
    # make themselves: a record with no mirror never reads it.
    for key, trigger in half:
        if key.endswith(".type"):
            row("config", key, "missing", f"{trigger} is set but {key} is not — write {key} beside it")
    for triggers, type_key, quiet, kind in NAMED_TOOLS[PLUGIN]:
        if not any(written(user, k) for k in triggers):
            continue
        if triggers[0].startswith("log.") and not dig(full, "log.enabled"):
            continue                       # channels named in a log that is switched off
        typ = dig(full, type_key)
        if typ is None and type_key in LEGACY_STRING:
            parent, legacy = LEGACY_STRING[type_key]
            if isinstance(dig(user, parent), str):
                typ = legacy
        typ = str(typ or "none").lower()
        if typ in quiet:
            continue
        name = CONNECTOR_NAME.get(typ) or declared_connector(full, kind, typ) or typ.capitalize()
        require(name, f"{type_key}: {typ}" + (f" → {name}" if name.lower() != typ else ""))
        named = True
    if PLUGIN == "fig":
        borrow_checks(user)
    if not named:
        because.append("your settings name no tool — nothing beyond this machine is needed")
    return full


def is_required(name):
    return name.lower() in required


def host_checks():
    row("host", f"python3 {sys.version.split()[0]}", "ok")

    try:
        import yaml
        row("host", f"PyYAML {getattr(yaml, '__version__', '?')}", "ok")
    except ImportError:
        row("host", "PyYAML", "missing", "run `pip3 install pyyaml` — the settings file cannot be read without it")

    out, code = run(["node", "--version"], timeout=10)
    if code == 0:
        row("host", f"node {out.strip()}", "ok")
    elif PLUGIN == "pm":
        row("host", "node", "absent", "pm needs it only for the Notion-log importer (`import-notion-export.mjs`)")
    else:
        row("host", "node", "missing", "install it from nodejs.org — the Figma scripts are checked with it")


def connector_checks():
    """`claude mcp list` runs a health check per server, so it is slow but authoritative."""
    listing, _ = run(["claude", "mcp", "list"], timeout=120)
    checks = list(CONNECTORS[PLUGIN])
    listed = {n.lower() for n, _, _ in checks}
    checks += [(disp, False, "named by the config") for low, disp in required.items() if low not in listed]

    if listing is None:
        # No claude CLI here — a CI runner, a bare shell. Every connector row is unknown, and a
        # required one stays unknown rather than quietly reading as answered
        row("connector", "claude mcp list", "unknown", "the claude command is not on this machine, so connections cannot be checked here")
        for name, hard, why in checks:
            row("connector", name, "unknown", ("required — " if hard or is_required(name) else "") + "confirm it yourself, or run this where Claude Code is installed")
        return

    lines = listing.splitlines()
    for name, hard, why in checks:
        need = hard or is_required(name)
        hit = next((ln for ln in lines if name.lower() in ln.lower()), None)
        if hit and "Connected" in hit:
            row("connector", name, "ok", "" if hard else why)
        elif hit and "Failed" in hit:
            # Configured and not answering is a different fix from not configured. The tail of
            # the error is what says which — a 400 on the auth header is an empty token variable,
            # not a revoked login
            tail = re.sub(r".*Failed to connect\s*[—-]*\s*", "", hit).strip()[:90]
            if "Authorization header" in tail:
                tail = "the login token it sends is empty. Open Claude Code from the terminal where the token is set, and it comes back"
            row("connector", name, "missing" if need else "failed",
                f"connected, but not responding — {tail}" if tail else "connected, but not responding")
        elif need:
            row("connector", name, "missing", why)
        else:
            row("connector", name, "absent", why)


def gh_checks(cfg):
    """The GitHub tracker adapter runs on the gh CLI. Where GitHub is required this row decides,
    and which account it is logged in to decides more than whether it is installed — a personal
    account against a company org gets a 404 that reads like the repo does not exist."""
    need = is_required("GitHub")
    out, code = run(["gh", "--version"], timeout=10)
    if code != 0:
        row("cli", "gh", "missing" if need else "absent", "install the GitHub command-line tool from cli.github.com — the GitHub side runs on it")
        return
    ver = (out.split() + ["?"])[2] if out.startswith("gh version") else "?"

    status, _ = run(["gh", "auth", "status"])
    account, active = None, None
    for ln in (status or "").splitlines():
        m = re.search(r"account (\S+)", ln)
        if m:
            account = account or m.group(1)
            current = m.group(1)
        if "Active account: true" in ln:
            active = current
    account = active or account
    if not account:
        row("cli", f"gh {ver}", "missing" if need else "attention", "not logged in — run `gh auth login`")
        return

    if not need:                               # one network call fewer where nothing needs GitHub
        row("cli", f"gh {ver}", "ok", f"account {account}")
        return

    hdr, _ = run(["gh", "api", "-i", "user"])
    m = re.search(r"^x-oauth-scopes:\s*(.*)$", hdr or "", re.I | re.M)
    scopes = m.group(1).strip() if m else ""
    note, state = f"logged in as {account}", "ok"
    if scopes:
        if "project" not in scopes:
            note += " · cannot read project boards yet — run `gh auth refresh -s read:project` once"
            state = "attention"                # the repo answers and the board comes back empty — worth a line in --quiet
    else:
        note += " · what this login may read is not reported"
    row("cli", f"gh {ver}", state, note)

    ref = dig(cfg, TRACKER_REF[PLUGIN]) if cfg else None
    if need and isinstance(ref, str) and "/" in ref:
        _, code = run(["gh", "repo", "view", ref, "--json", "name"])
        if code == 0:
            row("tracker", ref, "ok", f"visible to {account}")
        else:
            row("tracker", ref, "missing",
                f"{account} cannot see this repository — switch to the account that can (`gh auth switch`), or ask for access")


def other_checks():
    why = CHROME_SKILLS[PLUGIN]
    if why:
        row("browser", "Claude in Chrome", "unknown", f"cannot be checked from here — {why}")

    for path in (os.path.join(os.path.expanduser("~/.claude"), CONFIG_NAME),
                 os.path.join(os.getcwd(), CONFIG_NAME)):
        if os.path.exists(path):
            row("config", path.replace(os.path.expanduser("~"), "~"), "ok")
            return
    row("config", f"~/.claude/{CONFIG_NAME}", "none yet",
        f"not written yet — /{PLUGIN}:setup creates it")


FIX = {
    # A row's state, in words a person can act on. The note on the row carries the specifics.
    "missing":   "needed here, and not reachable",
    "failed":    "connected, but not responding",
    "attention": "works — read the note",
    "absent":    "not connected. fine until your settings name it",
    "unknown":   "cannot be checked from here",
}


def report():
    """The verdict first, in words. Then what to do. The table last, as detail.

    A person setting up for the first time reads the top line and the fix lines; the table is
    for the second look. Printing the table first made every first run start with a wall of
    state words nobody had seen before."""
    fixes = [r for r in rows if r[2] == "missing"]
    notes = [r for r in rows if r[2] in ("failed", "attention")]
    blind = [r for r in rows if r[2] == "unknown"]
    absent = [r for r in rows if r[2] == "absent"]
    no_config = any(b.startswith("no settings yet") for b in because)
    unchecked = [r for r in blind if r[0] == "connector" and r[3].startswith("required")]

    if fixes:
        print(f"Not ready — {len(fixes)} thing{'s' if len(fixes) != 1 else ''} to fix before /{PLUGIN}:setup can read your tools.")
    elif unchecked:
        print(f"Cannot tell — the claude command is not on this machine, so {len(unchecked)} tool{'s' if len(unchecked) != 1 else ''} your settings need "
              f"({', '.join(n for _, n, _, _ in unchecked)}) could not be checked. Confirm them yourself, or run this where Claude Code is installed.")
    elif no_config:
        print(f"Ready for /{PLUGIN}:setup. Nothing is needed yet — the tools you name there become needed from then on.")
    else:
        named = [b for b in because if not b.startswith("the config") and not b.startswith("--require")]
        print(f"Ready for /{PLUGIN}:setup. " + ("Every tool your settings name is connected." if named else "Your settings name no tool, so nothing beyond this machine is needed."))

    if fixes:
        print()
        print("Fix first")
        for kind, name, state, note in fixes:
            print(f"  · {name} — {note or FIX[state]}")
    if notes:
        print()
        print("Worth knowing")
        for kind, name, state, note in notes:
            print(f"  · {name} — {note or FIX[state]}")
    if blind and not QUIET:
        print()
        for kind, name, state, note in blind:
            print(f"  · {name} — {note}")
    if absent and not QUIET:
        print()
        print("Not connected, and not needed yet: " + ", ".join(n for _, n, _, _ in absent)
              + ". Once your settings name one, it becomes needed and this check will say so.")

    if not QUIET:
        print()
        print("── details " + "─" * 49)
        for kind, name, state, note in rows:
            line = f"{kind:<10}{name:<38}{state:<9}"
            print(f"{line} {note}".rstrip())
        print("─" * 60)
        print("ok = connected · absent = not connected, fine until your settings name it · failed = connected but not responding · missing = needed and unreachable · attention = works, read the note")
        if because:
            print("needed because  " + " · ".join(because))

    # The last line stays machine-readable. Skills and scripts read PASS / FAIL from it.
    tail = f" · {len(absent)} optional connector{'s' if len(absent) != 1 else ''} not connected" if absent else ""
    if missing:
        print(f"{len(missing)} missing — {', '.join(missing)}{tail} · FAIL")
        return 1
    if unchecked:
        print(f"{len(unchecked)} needed, unchecked — {', '.join(n for _, n, _, _ in unchecked)} · UNKNOWN")
        return 2
    print(f"ready for /{PLUGIN}:setup{tail} · PASS")
    return 0


cfg = settle_requirements()
host_checks()
connector_checks()
gh_checks(cfg)
other_checks()
sys.exit(report())
