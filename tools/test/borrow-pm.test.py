#!/usr/bin/env python3
"""Fixtures for borrow-pm.py — fig finding the installed pm and deciding what it borrows from it.

    python3 tools/test/borrow-pm.test.py

Every case runs fig's script as a subprocess with a temp CLAUDE_CONFIG_DIR (the plugin registry
and settings), a temp HOME (so no ~/.claude config of the machine's leaks in) and a cwd of its own
holding that case's configs. PYTHONUSERBASE is pinned back to the real user base, since moving
HOME moves the user site-packages where PyYAML may live. Every GIT_* variable is dropped: a
pre-push hook exports GIT_DIR, and the children inherit whatever this hands them.

pm is "installed" by copying plugins/pm into <cfg>/plugins/cache/m/pm/<ver> and naming it in a
registry as pm@m. The machine's own registry is never read.
"""
import importlib.util, json, os, re, shutil, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "fig" / "_common" / "scripts" / "lib" / "borrow-pm.py"
PM_SRC = REPO / "plugins" / "pm"
PM_VERSION = json.loads((PM_SRC / ".claude-plugin" / "plugin.json").read_text())["version"]
HEX = "0123456789abcdef0123456789abcdef"
failures = []


def clean_env(**extra):
    base = {k: v for k, v in os.environ.items()
            if not k.startswith("GIT_") and k not in ("FIG_PM_ROOT", "CLAUDE_CONFIG_DIR")}
    return dict(base, **extra)


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def parse(r):
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {}


def tree(d):
    return sorted(str(p.relative_to(d)) for p in Path(d).rglob("*"))


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    home = tmp / "home"
    (home / ".claude").mkdir(parents=True)
    counter = [0]

    def new_dir(name):
        counter[0] += 1
        d = tmp / f"{name}-{counter[0]}"
        d.mkdir(parents=True)
        return d

    def copy_pm(cfg, mkt="m", version=None):
        """plugins/pm copied into cfg's cache. version rewrites the copy's plugin.json."""
        dest = cfg / "plugins" / "cache" / mkt / "pm" / (version or PM_VERSION)
        shutil.copytree(PM_SRC, dest, ignore=shutil.ignore_patterns("__pycache__"))
        if version:
            mf = dest / ".claude-plugin" / "plugin.json"
            data = json.loads(mf.read_text())
            data["version"] = version
            mf.write_text(json.dumps(data))
        return dest

    def registry(cfg, plugins):
        (cfg / "plugins").mkdir(parents=True, exist_ok=True)
        (cfg / "plugins" / "installed_plugins.json").write_text(
            json.dumps({"version": 2, "plugins": plugins}))

    def entry(path, scope="user", version=PM_VERSION, **more):
        return dict({"scope": scope, "installPath": str(path), "version": version,
                     "installedAt": "2026-10-19T00:00:00.000Z", "lastUpdated": "2026-10-19T00:00:00.000Z"},
                    **more)

    def installed(version=None):
        """A config dir with pm@m installed at user scope. The registry always says the current
        version — the version that counts is the copy's own plugin.json."""
        cfg = new_dir("cfg")
        root = copy_pm(cfg, version=version)
        registry(cfg, {"pm@m": [entry(root)]})
        return cfg, root

    def run(cfg, cwd, *args, env=None):
        e = clean_env(HOME=str(home), CLAUDE_CONFIG_DIR=str(cfg),
                      PYTHONUSERBASE=site.getuserbase(), **(env or {}))
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, env=e,
                              capture_output=True, text=True)

    def project(fig=None, pm=None, files=None):
        cwd = new_dir("proj")
        if fig is not None:
            (cwd / "figma-conventions.yaml").write_text(fig)
        if pm is not None:
            (cwd / "pm-conventions.yaml").write_text(pm)
        for rel, text in (files or {}).items():
            (cwd / rel).parent.mkdir(parents=True, exist_ok=True)
            (cwd / rel).write_text(text)
        return cwd

    cfg_ok, pm_ok = installed()
    cfg_old, pm_old = installed(version="0.37.1")
    cfg_empty = new_dir("cfg")

    # --- task: finding pm
    r = run(cfg_empty, project(), "task")
    out = parse(r)
    check("no registry → print with the install note",
          r.returncode == 0 and out.get("action") == "print" and "Installing pm" in (out.get("note") or ""),
          f"rc={r.returncode} {r.stdout}{r.stderr}")

    cfg_bad = new_dir("cfg")
    (cfg_bad / "plugins").mkdir()
    (cfg_bad / "plugins" / "installed_plugins.json").write_text("{")
    r = run(cfg_bad, project(), "task")
    check("malformed registry → print, no traceback",
          r.returncode == 0 and parse(r).get("action") == "print" and "Traceback" not in r.stderr,
          f"rc={r.returncode} {r.stdout}{r.stderr}")

    cfg_off, _ = installed()
    (cfg_off / "settings.json").write_text(json.dumps({"enabledPlugins": {"pm@m": False}}))
    r = run(cfg_off, project(), "task")
    out = parse(r)
    check("pm disabled in settings → treated as not installed",
          out.get("action") == "print" and "Installing pm" in (out.get("note") or ""), r.stdout + r.stderr)

    r = run(cfg_old, project(), "task")
    out = parse(r)
    note = out.get("note") or ""
    check("pm below PM_MIN → print with the update note",
          out.get("action") == "print" and "0.38.0" in note and "update" in note, r.stdout + r.stderr)

    r = run(cfg_empty, project(), "where", env={"FIG_PM_ROOT": str(pm_ok)})
    check("FIG_PM_ROOT overrides the registry", parse(r).get("ok") is True, r.stdout + r.stderr)

    # --- task: the decision table
    cwd = project()
    r = run(cfg_ok, cwd, "task")
    out = parse(r)
    check("unset + pm markdown → write into pm's task dir",
          r.returncode == 0 and out.get("action") == "write" and out.get("dir") == "./tasks"
          and out.get("heading") == "Design changes"
          and (out.get("script") or "").endswith("markdown-tracker.py")
          and (out.get("adapter") or "").endswith(os.path.join("trackers", "markdown.md")),
          r.stdout + r.stderr)
    check("unset + pm markdown → nothing written", tree(cwd) == [], str(tree(cwd)))

    cwd = project(pm="task:\n  record:\n    type: notion\n    ref: \"collection://x\"\n  link_property: Ticket\n")
    before = tree(cwd)
    r = run(cfg_ok, cwd, "task")
    out = parse(r)
    check("unset + pm record on notion → print",
          out.get("action") == "print" and "markdown task files" in (out.get("note") or "")
          and tree(cwd) == before, f"{r.stdout}{r.stderr} {tree(cwd)}")

    r = run(cfg_ok, project(pm="task:\n  record:\n    type: notion\n"), "task")
    out = parse(r)
    check("pm's own guard exits 3 → print, with a note quoting the first stderr line",
          r.returncode == 0 and out.get("action") == "print"
          and "task.record.ref is not set" in (out.get("note") or ""), r.stdout + r.stderr)

    r = run(cfg_ok, project(pm="task:\n  record: {type: [\n"), "task")
    note = parse(r).get("note") or ""
    check("pm's config unreadable → print, the note keeps the error and where it is",
          parse(r).get("action") == "print" and "while parsing" in note
          and "pm-conventions.yaml" in note and re.search(r"line \d+, column \d+", note) is not None,
          r.stdout + r.stderr)

    fig_md = "task_tracker:\n  type: markdown\n  ref: ./work\n"
    r = run(cfg_ok, project(fig=fig_md), "task")
    out = parse(r)
    check("markdown + pm → write into task_tracker.ref",
          out.get("action") == "write" and out.get("dir") == "./work", r.stdout + r.stderr)

    r = run(cfg_empty, project(fig=fig_md), "task")
    out = parse(r)
    check("markdown without pm → print with the install note",
          out.get("action") == "print" and "Installing pm" in (out.get("note") or ""), r.stdout + r.stderr)

    r = run(cfg_ok, project(fig="task_tracker:\n  type: none\n"), "task")
    out = parse(r)
    check("none → print, no note",
          r.returncode == 0 and out.get("action") == "print" and "note" in out and out["note"] is None,
          r.stdout + r.stderr)

    r = run(cfg_ok, project(fig="task_tracker:\n  ref: x\n"), "task")
    check("ref without type → exit 3",
          r.returncode == 3 and "task_tracker.type is not set" in r.stderr, f"rc={r.returncode} {r.stderr}")

    r = run(cfg_ok, project(fig="task_tracker:\n  ui_section_heading: Handover\n"), "task")
    check("a set heading is used", parse(r).get("heading") == "Handover", r.stdout + r.stderr)

    # --- prd: the lookup order
    r = run(cfg_ok, project(fig=f"qa:\n  baseline:\n    prd: \"{HEX}\"\n"), "prd")
    out = parse(r)
    check("prd: legacy string → notion",
          out.get("type") == "notion" and out.get("from") == "qa.baseline.prd", r.stdout + r.stderr)

    store = "---\nproduct: Store App\n---\n\n# Store App\n"
    r = run(cfg_ok, project(fig="qa:\n  baseline:\n    prd: null\n", files={"docs/prd/store-app.md": store}), "prd")
    out = parse(r)
    check("prd: explicit null → none, pm not tried",
          out.get("type") == "none" and "from" in out and out["from"] is None and out.get("candidates") == [],
          r.stdout + r.stderr)

    for label, fig in (("prd: notion without ref → none, note", "prd: {type: notion, ref: null}"),
                       ("prd: notion with an empty ref → none, note", "prd: {type: notion, ref: \"\"}"),
                       ("prd: legacy empty string → none, note", "prd: \"\"")):
        r = run(cfg_ok, project(fig=f"qa:\n  baseline:\n    {fig}\n", files={"docs/prd/store-app.md": store}), "prd")
        out = parse(r)
        check(label, out.get("type") == "none" and out.get("from") == "qa.baseline.prd"
              and out.get("candidates") == [] and "link" in (out.get("note") or ""), r.stdout + r.stderr)

    r = run(cfg_ok, project(files={"docs/prd/store-app.md": store}), "prd")
    out = parse(r)
    cands = out.get("candidates") or []
    check("prd: floor + pm → pm's files",
          out.get("type") == "markdown" and out.get("from") == "pm" and len(cands) == 1
          and cands[0].get("product") == "Store App", r.stdout + r.stderr)

    r = run(cfg_ok, project(pm="prd:\n  markdown:\n    split: domain\n",
                            files={"docs/prd/store-app/index.md": "# Store App\n",
                                   "docs/prd/store-app/payments.md": "# Payments\n"}), "prd")
    out = parse(r)
    cands = out.get("candidates") or []
    pay = [c for c in cands if (c.get("path") or "").endswith("payments.md")]
    check("prd: split domain → the product folder",
          out.get("split") == "domain" and len(cands) == 2 and len(pay) == 1
          and pay[0].get("domain") == "payments" and pay[0].get("product") == "store-app",
          r.stdout + r.stderr)

    r = run(cfg_old, project(files={"docs/prd/store-app.md": store}), "prd")
    out = parse(r)
    check("prd: pm below PM_MIN → none, note",
          out.get("type") == "none" and "update" in (out.get("note") or ""), r.stdout + r.stderr)

    r = run(cfg_ok, project(files={"docs/x.md": "# X\n"}), "prd", "--spec-url", "docs/x.md#entry-3")
    out = parse(r)
    check("prd: spec_url .md → markdown",
          out.get("type") == "markdown" and out.get("ref") == "docs/x.md#entry-3"
          and out.get("from") == "spec_url", r.stdout + r.stderr)

    r = run(cfg_ok, project(), "prd", "--spec-url", HEX)
    check("prd: spec_url 32-hex → notion", parse(r).get("type") == "notion", r.stdout + r.stderr)

    r = run(cfg_ok, project(), "prd", "--spec-url", "https://www.figma.com/design/abc/x")
    check("prd: spec_url figma → exit 6", r.returncode == 6, f"rc={r.returncode} {r.stdout}{r.stderr}")

    # --- beyond the table: the registry rules the installed pair depends on
    cfg_two = new_dir("cfg")
    old_a = copy_pm(cfg_two, mkt="a", version="0.37.1")
    new_b = copy_pm(cfg_two, mkt="b")
    pair = {"pm@a": [entry(old_a)], "pm@b": [entry(new_b)]}
    registry(cfg_two, pair)
    r = run(cfg_two, project(), "where")
    check("two marketplaces, no fig entry → the first match", parse(r).get("version") == "0.37.1",
          r.stdout + r.stderr)
    registry(cfg_two, dict(pair, **{"fig@b": [entry(REPO / "plugins" / "fig")]}))
    r = run(cfg_two, project(), "where")
    out = parse(r)
    check("fig's own marketplace is preferred",
          out.get("ok") is True and os.path.realpath(out.get("root") or "") == os.path.realpath(new_b),
          r.stdout + r.stderr)

    cfg_proj = new_dir("cfg")
    root_p = copy_pm(cfg_proj)
    parent = new_dir("repo")
    (parent / "sub").mkdir()
    registry(cfg_proj, {"pm@m": [entry(root_p, scope="project", projectPath=str(parent))]})
    r = run(cfg_proj, parent / "sub", "where")
    check("project scope → seen from below its projectPath", parse(r).get("ok") is True, r.stdout + r.stderr)
    r = run(cfg_proj, project(), "where")
    check("project scope → not seen from elsewhere", parse(r).get("root", "x") is None, r.stdout + r.stderr)

    # --- the module, as preflight loads it
    sys.dont_write_bytecode = True        # no __pycache__ left beside the plugin's script
    try:
        spec = importlib.util.spec_from_file_location("borrow_pm", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        loaded = (mod.PM_MIN == "0.38.0" and mod.HEADING == "Design changes"
                  and mod.config_dir({"CLAUDE_CONFIG_DIR": "/x"}) == "/x"
                  and mod.config_dir({"HOME": "/h"}) == os.path.join("/h", ".claude")
                  and mod.version_ok("0.38.0") and mod.version_ok("1.0") and not mod.version_ok("0.37.9")
                  and not mod.version_ok("0.38.0-beta") and not mod.version_ok("")
                  and mod.spec_kind("https://acme.notion.site/Page-" + HEX, str(tmp))[0] == "notion"
                  and mod.spec_kind("0123abcd-0123-4567-89ab-0123456789ab", str(tmp))[0] == "notion"
                  and mod.spec_kind("docs/none.md", str(tmp))[0] == "unknown"
                  and mod.find_pm({"CLAUDE_CONFIG_DIR": str(cfg_bad)}, str(tmp)) is None)
        detail = ""
    except Exception as e:  # the RED run, before the script exists
        loaded, detail = False, f"{type(e).__name__}: {e}"
    check("the module loads by path and its helpers answer", loaded, detail)

print()
print("FAILED: " + ", ".join(failures) if failures else "all passed")
sys.exit(1 if failures else 0)
