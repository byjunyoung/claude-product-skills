#!/usr/bin/env python3
"""Fixtures for preflight.py — which connector a config makes required, and what it says when
there is no config. Connector rows depend on the machine (`claude mcp list`), so only the
lines that do not are asserted: the `required by` line and the verdict's first words.

    python3 tools/test/preflight.test.py
"""
import json, os, shutil, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "pm" / "_common" / "scripts" / "lib" / "preflight.py"
failures = []


def run(cwd, home):
    env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase())
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    return r.stdout


def line(out, prefix):
    return next((ln for ln in out.splitlines() if ln.startswith(prefix)), "")


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


with tempfile.TemporaryDirectory() as tmp:
    home, proj = Path(tmp) / "home", Path(tmp) / "proj"
    (home / ".claude").mkdir(parents=True); proj.mkdir()

    out = run(proj, home)
    check("no config → says nothing is needed yet", "Nothing is needed yet" in out.splitlines()[0], out.splitlines()[0])
    check("no config → needed-because line says so", "no settings yet" in line(out, "needed because"), line(out, "needed because"))

    (proj / "pm-conventions.yaml").write_text("task:\n  record: {type: notion, ref: 'collection://x'}\n")
    out = run(proj, home)
    check("record notion → Notion required", "task.record.type: notion" in line(out, "needed because"), line(out, "needed because"))

    # A type the plugin has never heard of, whose adapter declares its connector
    (proj / "pm-adapters" / "trackers").mkdir(parents=True)
    (proj / "pm-adapters" / "trackers" / "gsheet.md").write_text("# Sheets\n\nconnector: Google Drive\n")
    (proj / "pm-conventions.yaml").write_text("task:\n  record: {type: gsheet, ref: 'abc'}\n")
    out = run(proj, home)
    check("unknown type → connector taken from the adapter's connector: line",
          "task.record.type: gsheet → Google Drive" in line(out, "needed because"), line(out, "needed because"))
    check("unknown type → a row named after that connector (whatever its state)", any(ln.startswith("connector Google Drive") for ln in out.splitlines()), out)

    # Where the claude CLI is absent — a CI runner — a required connector must not read as answered
    # A PATH with node but without claude — /usr/bin alone would also lose node and fail on the host row
    import shutil
    bare_bin = Path(tmp) / "bin"; bare_bin.mkdir()
    for tool in ("node", "gh"):
        found = shutil.which(tool)
        if found:
            (bare_bin / tool).symlink_to(found)
    bare = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase(), PATH=f"{bare_bin}:/usr/bin:/bin")
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=proj, env=bare, capture_output=True, text=True, timeout=120)
    check("no claude CLI → verdict says it cannot tell", r.stdout.startswith("Cannot tell"), r.stdout.splitlines()[0] if r.stdout else r.stderr)
    check("no claude CLI → exit 2, not PASS", r.returncode == 2 and "UNKNOWN" in r.stdout.splitlines()[-1], f"rc={r.returncode}")

    # The same type with no adapter falls back to the type name, and says so
    (proj / "pm-adapters" / "trackers" / "gsheet.md").unlink()
    out = run(proj, home)
    check("unknown type, no adapter → the type name itself", "task.record.type: gsheet" in line(out, "needed because") and "→" not in line(out, "needed because"), line(out, "needed because"))

    # A ref written without its type: the floor used to fill the type in, so it must be written
    (proj / "pm-conventions.yaml").write_text("task:\n  record:\n    ref: ./x\n")
    out = run(proj, home)
    fix = out.split("Fix first", 1)[1].split("\n\n", 1)[0] if "Fix first" in out else ""
    check("ref without type → FAIL naming the key",
          out.splitlines()[-1].endswith("· FAIL") and "task.record.type" in fix, out.splitlines()[-1] if out else "")

    # A Notion record with no mirror never reads task.link_property, so preflight must not fail it
    (proj / "pm-conventions.yaml").write_text("task:\n  record:\n    type: notion\n    ref: \"collection://x\"\n")
    out = run(proj, home)
    fix = out.split("Fix first", 1)[1].split("\n\n", 1)[0] if "Fix first" in out else ""
    check("notion record, no mirror, no link property → not FAIL",
          "task.link_property" not in fix and "task.record.type: notion" in line(out, "needed because"), fix or line(out, "needed because"))

    # pm needs node only for the Notion-log importer, so no node is not a failure
    (proj / "pm-conventions.yaml").unlink()
    nonode = Path(tmp) / "nonode-bin"; nonode.mkdir()
    env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase(), PATH=str(nonode))
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=proj, env=env, capture_output=True, text=True, timeout=120)
    fix = r.stdout.split("Fix first", 1)[1].split("\n\n", 1)[0] if "Fix first" in r.stdout else ""
    last = r.stdout.splitlines()[-1] if r.stdout else ""
    row_node = next((ln for ln in r.stdout.splitlines() if ln.startswith("host      node")), "")
    check("pm without node → not a failure",
          "node" not in fix and not last.endswith("FAIL") and "absent" in row_node, f"{last!r} {row_node!r} {r.stderr[-200:]}")

# A renamed fork (manifest name is neither fig nor pm) must not die on a table lookup
with tempfile.TemporaryDirectory() as tmp2:
    fork = Path(tmp2) / "forked"
    shutil.copytree(REPO / "plugins" / "pm" / "_common", fork / "_common", ignore=shutil.ignore_patterns("__pycache__"))
    (fork / ".claude-plugin").mkdir()
    (fork / ".claude-plugin" / "plugin.json").write_text('{"name": "forked-fig"}')
    home2, proj2 = Path(tmp2) / "home", Path(tmp2) / "proj"
    (home2 / ".claude").mkdir(parents=True); proj2.mkdir()
    env2 = dict(os.environ, HOME=str(home2), PYTHONUSERBASE=site.getuserbase())
    r = subprocess.run([sys.executable, str(fork / "_common" / "scripts" / "lib" / "preflight.py")],
                       cwd=proj2, env=env2, capture_output=True, text=True, timeout=300)
    check("renamed fork → no traceback", "Traceback" not in r.stderr and r.stdout.strip() != "", r.stderr[-400:])

# fig borrows pm's PRD and task files, so its config can name a markdown PRD or tracker that
# needs no connector. Run on fig's copy with no pm reachable: FIG_PM_ROOT unset, an empty
# CLAUDE_CONFIG_DIR, a temp HOME. Every GIT_* key is dropped, as a pre-push hook exports GIT_DIR.
FIG_SCRIPT = REPO / "plugins" / "fig" / "_common" / "scripts" / "lib" / "preflight.py"


def run_fig(cwd, home, cfgdir):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "FIG_PM_ROOT"}
    env.update(HOME=str(home), CLAUDE_CONFIG_DIR=str(cfgdir), PYTHONUSERBASE=site.getuserbase())
    r = subprocess.run([sys.executable, str(FIG_SCRIPT)], cwd=cwd, env=env, capture_output=True, text=True, timeout=300)
    return r.stdout


def section(out, title):
    return out.split(title, 1)[1].split("\n\n", 1)[0] if title in out else ""


with tempfile.TemporaryDirectory() as tmp3:
    home3, proj3, cfg3 = Path(tmp3) / "home", Path(tmp3) / "proj", Path(tmp3) / "claude"
    (home3 / ".claude").mkdir(parents=True); proj3.mkdir(); cfg3.mkdir()
    conv = proj3 / "figma-conventions.yaml"

    out = run_fig(proj3, home3, cfg3)
    # The verdict's first line depends on whether the Figma connector is up on this machine (fig
    # has a hard one, pm none), so the machine-free line is the one asserted.
    check("fig, no config → nothing needed yet", "no settings yet" in line(out, "needed because"), line(out, "needed because"))

    conv.write_text('qa:\n  baseline:\n    prd: "0123456789abcdef0123456789abcdef"\n')
    out = run_fig(proj3, home3, cfg3)
    check("legacy string qa.baseline.prd → Notion required",
          "qa.baseline.prd.type: notion" in line(out, "needed because"), line(out, "needed because"))

    conv.write_text("qa:\n  baseline:\n    prd: {type: markdown, ref: ./docs/prd}\n")
    out = run_fig(proj3, home3, cfg3)
    check("qa.baseline.prd markdown → nothing required",
          "name no tool" in line(out, "needed because"), line(out, "needed because"))

    # Not FAIL because of this row: the verdict itself can FAIL here on a machine without the
    # Figma connector, so the assertion is that the Fix-first list never names the tracker.
    conv.write_text("task_tracker:\n  type: markdown\n")
    out = run_fig(proj3, home3, cfg3)
    check("task_tracker markdown without pm → attention, not FAIL",
          "pm is not installed" in section(out, "Worth knowing") and "task_tracker" not in section(out, "Fix first"),
          section(out, "Worth knowing") or (out.splitlines()[-1] if out else ""))

    conv.write_text("task_tracker:\n  ref: x\n")
    out = run_fig(proj3, home3, cfg3)
    check("task_tracker.ref without type → FAIL naming the key",
          out.splitlines()[-1].endswith("· FAIL") and "task_tracker.type" in section(out, "Fix first"),
          out.splitlines()[-1] if out else "")

    # A pm whose manifest carries no version, installed through a registry of this temp config dir.
    cfg4, pm4 = Path(tmp3) / "claude-nover", Path(tmp3) / "claude-nover" / "plugins" / "cache" / "m" / "pm" / "x"
    (pm4 / ".claude-plugin").mkdir(parents=True)
    (pm4 / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "pm"}))
    (cfg4 / "plugins" / "installed_plugins.json").write_text(
        json.dumps({"version": 2, "plugins": {"pm@m": [{"scope": "user", "installPath": str(pm4)}]}}))
    conv.write_text("task_tracker:\n  type: markdown\n")
    out = run_fig(proj3, home3, cfg4)
    check("task_tracker markdown, pm without a version → the row says (no version)",
          "pm (no version) is older than" in section(out, "Worth knowing"), section(out, "Worth knowing"))

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("preflight fixtures · PASS")
