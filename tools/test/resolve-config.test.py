#!/usr/bin/env python3
"""Fixtures for resolve-config.py — the layering, and the --need gate a skill stops on.

    python3 tools/test/resolve-config.test.py

Runs the pm copy; verify.py already holds the two copies identical. HOME is pointed at a
temp dir for every case, so the machine's own ~/.claude config cannot leak into a fixture.
Moving HOME also moves python's user site-packages, which is where a `pip install --user
pyyaml` lives — so the real user base is pinned back with PYTHONUSERBASE, or every case
fails on a missing module that is in fact installed.
"""
import json, os, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "pm" / "_common" / "scripts" / "lib" / "resolve-config.py"
NAME = "pm-conventions.yaml"

failures = []


def run(cwd, home, *args):
    env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase())
    return subprocess.run([sys.executable, str(SCRIPT), "--name", NAME, *args],
                          cwd=cwd, env=env, capture_output=True, text=True)


def parse(r):
    """The JSON on stdout, or None with the reason printed — a traceback here hides the stderr
    the script wrote, which is the one line that says why."""
    try:
        return json.loads(r.stdout)
    except ValueError:
        print("      no JSON on stdout — stderr: " + r.stderr.strip())
        return None


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


with tempfile.TemporaryDirectory() as tmp:
    home, proj = Path(tmp) / "home", Path(tmp) / "proj"
    (home / ".claude").mkdir(parents=True)
    proj.mkdir()

    # 1. No config anywhere: the bundled floor alone. Local markdown, so the tasks folder and the
    #    log work before anyone has written a settings file.
    r = run(proj, home)
    cfg = parse(r) or {}
    check("no config → the local floor", r.returncode == 0
          and len(cfg.get("meta", {}).get("layers", [])) == 1
          and cfg.get("task", {}).get("record", {}).get("type") == "markdown"
          and cfg.get("task", {}).get("record", {}).get("ref") == "./tasks"
          and cfg.get("task", {}).get("link_property") == "ticket"
          and cfg.get("log", {}).get("enabled") is True
          and cfg.get("task", {}).get("mirror", {}).get("type") == "none", r.stderr)
    check("pm floor: design heading", cfg.get("task", {}).get("design_heading") == "Design changes",
          str(cfg.get("task", {}).get("design_heading")))

    # 2. --need on task.mirror.ref, which the floor leaves null: exit 2, the key named on
    #    stderr, nothing on stdout
    r = run(proj, home, "--need", "task.mirror.ref")
    check("--need on a null → exit 2", r.returncode == 2, f"rc={r.returncode}")
    check("--need on a null → key named on stderr", "task.mirror.ref is not set" in r.stderr, r.stderr)
    check("--need on a null → no JSON on stdout", r.stdout.strip() == "")

    # 1b. The floor writes both halves of the pair, so --authored has nothing to stop on
    r = run(proj, home, "--authored", "task.record.type")
    check("no config → --authored task.record.type passes", r.returncode == 0, r.stderr)

    # 1c. A project that names notion takes its own ref and link property as written
    proj2 = Path(tmp) / "proj2"
    proj2.mkdir()
    (proj2 / NAME).write_text("task:\n  record:\n    type: notion\n    ref: \"collection://x\"\n"
                              "  link_property: Ticket\n")
    r = run(proj2, home, "--authored", "task.record.type,task.link_property")
    cfg = parse(r) or {}
    check("explicit notion config → --authored passes", r.returncode == 0, r.stderr)
    check("explicit notion config → type as written",
          cfg.get("task", {}).get("record", {}).get("type") == "notion")
    check("explicit notion config → ref as written",
          cfg.get("task", {}).get("record", {}).get("ref") == "collection://x")
    check("explicit notion config → link_property as written",
          cfg.get("task", {}).get("link_property") == "Ticket")

    # 3. A project layer writes the key: --need passes and the value comes through
    (proj / NAME).write_text("task:\n  record:\n    type: markdown\n    ref: ./tasks\n")
    r = run(proj, home, "--need", "task.record.ref")
    cfg = parse(r) or {}
    check("project layer → --need passes", r.returncode == 0, r.stderr)
    check("project layer → value read", cfg.get("task", {}).get("record", {}).get("ref") == "./tasks")
    check("project layer → two layers", len(cfg.get("meta", {}).get("layers", [])) == 2)

    # 4. Home + project: project wins, and a deep merge keeps the sibling the project did not write
    (home / ".claude" / NAME).write_text("meta:\n  profile: home\ntask:\n  link_property: Ticket\n  record:\n    ref: ./from-home\n")
    r = run(proj, home)
    cfg = parse(r) or {}
    check("two layers → project covers home", cfg.get("task", {}).get("record", {}).get("ref") == "./tasks")
    check("two layers → sibling from home survives", cfg.get("task", {}).get("link_property") == "Ticket")
    check("two layers → three layers reported", len(cfg.get("meta", {}).get("layers", [])) == 3)

    # 4b. Order — a partial override leaves the map's order alone; writing it whole sets it.
    #     ticket.sections is written into a ticket in this order, so a team whose tracker
    #     template runs QA before done has to be able to say so, and a team naming one
    #     section must not have it jump to the front.
    (home / ".claude" / NAME).write_text("task:\n  ticket:\n    sections:\n      summary: S\n")
    (proj / NAME).write_text("meta:\n  profile: p\n")
    cfg = parse(run(proj, home)) or {}
    keys = list(cfg.get("task", {}).get("ticket", {}).get("sections", {}))
    check("partial override → schema order kept", keys and keys[0] != "summary", str(keys))
    whole = "task:\n  ticket:\n    sections:\n" + "".join(
        f"      {k}: {k}\n" for k in ["schedule", "summary", "project", "done", "links"])
    (home / ".claude" / NAME).write_text(whole)
    cfg = parse(run(proj, home)) or {}
    keys = list(cfg.get("task", {}).get("ticket", {}).get("sections", {}))
    check("whole map written → that order comes out",
          keys == ["schedule", "summary", "project", "done", "links"], str(keys))

    # 5. An explicit null in the stronger layer is a value, not an absence — it does not fall back
    (proj / NAME).write_text("task:\n  link_property: null\n")
    r = run(proj, home, "--need", "task.link_property")
    check("null in project → covers the home value, --need stops", r.returncode == 2, f"rc={r.returncode}")

    # 6. An empty map is a value, so --need does not stop on it
    (proj / NAME).write_text("task:\n  label_map:\n    project: {}\n")
    r = run(proj, home, "--need", "task.label_map.project")
    check("empty map → --need passes", r.returncode == 0, r.stderr)

    # 7. --authored sees what --need cannot: a key only the floor supplies resolves to a value,
    #    so --need passes on it while --authored stops. This is the incident these two split over.
    (home / ".claude" / NAME).write_text("meta:\n  profile: home\ntask:\n  link_property: Ticket\n")
    (proj / NAME).unlink()
    r = run(proj, home, "--need", "task.contract.level")
    check("floor-only key → --need passes (it is not null)", r.returncode == 0, r.stderr)
    r = run(proj, home, "--authored", "task.contract.level")
    check("floor-only key → --authored exits 3", r.returncode == 3, f"rc={r.returncode}")
    check("floor-only key → the key is named", "task.contract.level is not set" in r.stderr, r.stderr)
    check("floor-only key → where the config came from is shown", ".claude" in r.stderr, r.stderr)
    check("floor-only key → no JSON on stdout", r.stdout.strip() == "")

    # 8. A key the person wrote passes --authored, whatever its value — including null, which is
    #    a decision. --need is what reads that decision; the two do not overlap.
    (proj / NAME).write_text("task:\n  contract:\n    level: parent\n")
    r = run(proj, home, "--authored", "task.contract.level")
    check("written key → --authored passes", r.returncode == 0, r.stderr)
    (proj / NAME).write_text("task:\n  contract:\n    level: null\n")
    r = run(proj, home, "--authored", "task.contract.level")
    check("written null → --authored passes (somebody decided)", r.returncode == 0, r.stderr)
    r = run(proj, home, "--need", "task.contract.level")
    check("written null → --need still stops", r.returncode == 2, f"rc={r.returncode}")

    # 8b. A key that only means something beside another stops when the other is written alone.
    #     The floor used to fill the missing half; once it changes, a written ref would silently
    #     point somewhere else, so the pair has to be written together.
    pair_home = Path(tmp) / "pair-home"
    (pair_home / ".claude").mkdir(parents=True)
    pair_proj = Path(tmp) / "pair-proj"
    pair_proj.mkdir()
    pf = pair_proj / NAME
    pf.write_text("task:\n  record:\n    ref: ./x\n")
    r = run(pair_proj, pair_home, "--authored", "task.record.type")
    check("paired: ref without type → --authored stops", r.returncode == 3, f"rc={r.returncode}")
    check("paired: ref without type → message names both keys",
          f"task.record.type is not set in {NAME}, while task.record.ref is" in r.stderr, r.stderr)
    pf.unlink()
    r = run(pair_proj, pair_home, "--authored", "task.record.type")
    check("paired: neither written → passes", r.returncode == 0, r.stderr)
    pf.write_text("task:\n  record: {type: markdown, ref: ./t}\n")
    r = run(pair_proj, pair_home, "--authored", "task.record.type")
    check("paired: both written → passes", r.returncode == 0, r.stderr)
    pf.write_text("task:\n  record: {type: notion, ref: 'collection://x'}\n")
    r = run(pair_proj, pair_home, "--authored", "task.link_property")
    check("paired: a non-markdown type needs its link property",
          r.returncode == 3 and "task.link_property" in r.stderr, f"rc={r.returncode} {r.stderr}")
    pf.write_text("task:\n  record: {type: markdown, ref: ./t}\n")
    r = run(pair_proj, pair_home, "--authored", "task.link_property")
    check("paired: a markdown type exempts the link property", r.returncode == 0, r.stderr)

    # 8c. The reverse pair: a tracker type written without its ref. The floor's ref is a local
    #     folder, so a Notion or GitHub record would be handed ./tasks. markdown and none have no
    #     database to name, so the floor's folder is theirs to take.
    both = "task.record.type,task.record.ref"
    pf.write_text("task:\n  record:\n    type: notion\n")
    r = run(pair_proj, pair_home, "--authored", both)
    check("paired: a tracker type without its ref → --authored stops", r.returncode == 3, f"rc={r.returncode}")
    check("paired: a tracker type without its ref → message names both keys",
          f"task.record.ref is not set in {NAME}, while task.record.type is —" in r.stderr, r.stderr)
    pf.write_text("task:\n  record:\n    type: markdown\n")
    r = run(pair_proj, pair_home, "--authored", both)
    check("paired: markdown without a ref → passes", r.returncode == 0, r.stderr)
    pf.write_text("task:\n  record:\n    type: none\n")
    r = run(pair_proj, pair_home, "--authored", both)
    check("paired: none without a ref → passes", r.returncode == 0, r.stderr)
    pf.unlink()
    r = run(pair_proj, pair_home, "--authored", both)
    check("paired: nothing written → passes with the ref asked for too", r.returncode == 0, r.stderr)

    # 8d. Each pair says its own reason after the shared first clause. "That default has changed"
    #     is true of a ref whose type the floor used to supply, and of nothing else.
    changed = "that default has changed"
    pf.write_text("task:\n  record:\n    ref: ./x\n")
    r = run(pair_proj, pair_home, "--authored", "task.record.type")
    check("reason: ref without type → the default it leaned on changed", changed in r.stderr, r.stderr)
    pf.write_text("task:\n  record: {type: notion, ref: 'collection://x'}\n")
    r = run(pair_proj, pair_home, "--authored", "task.link_property")
    check("reason: link property → which property holds the ticket's link",
          "holds the ticket's link" in r.stderr and changed not in r.stderr, r.stderr)
    pf.write_text("task:\n  record:\n    type: notion\n")
    r = run(pair_proj, pair_home, "--authored", "task.record.ref")
    check("reason: ref → which database or repository, not a local folder",
          "database or repository" in r.stderr and "local folder" in r.stderr and changed not in r.stderr, r.stderr)
    pf.unlink()

    # 9. --origin describes the strongest layer without asking it to declare anything
    r = run(proj, home, "--origin")
    check("--origin → names the layer in play", str(proj / NAME) in r.stdout, r.stdout)
    check("--origin → not a symlink, so no arrow", "→" not in r.stdout, r.stdout)
    empty = Path(tmp) / "empty"
    empty.mkdir()
    bare = Path(tmp) / "bare-home"
    (bare / ".claude").mkdir(parents=True)
    r = run(empty, bare, "--origin")
    check("--origin → says so where there is no config of your own",
          "every value came from the plugin's defaults" in r.stdout, r.stdout)

    # 10. A script knows its plugin by plugin.json, not by the path it was installed under
    import shutil

    def run_script(script, cwd, home, *args):
        env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase())
        return subprocess.run([sys.executable, str(script), *args], cwd=cwd, env=env,
                              capture_output=True, text=True)

    ignore = shutil.ignore_patterns(".git", "__pycache__")
    nested = Path(tmp) / "pm" / "plugins" / "fig"
    shutil.copytree(REPO / "plugins" / "fig", nested, ignore=ignore)
    r = run_script(nested / "_common" / "scripts" / "lib" / "resolve-config.py", empty, bare,
                   "--need", "task_tracker.ref")
    check("fig copied under a path containing /pm/ is still fig",
          "/fig:setup" in r.stderr and "/pm:setup" not in r.stderr, r.stderr.strip())

    (home / ".claude" / "pm-conventions.yaml").write_text("task:\n  contract:\n    level: parent\n")
    r = run_script(SCRIPT, empty, home)
    meta = (parse(r) or {}).get("meta", {})
    check("pm's default name is pm-conventions.yaml",
          any(str(home / ".claude" / "pm-conventions.yaml") in l for l in meta.get("layers", [])), r.stderr.strip())

    bare_copy = Path(tmp) / "pm" / "_common"
    shutil.copytree(REPO / "plugins" / "pm" / "_common", bare_copy, ignore=ignore)
    r = run_script(bare_copy / "scripts" / "lib" / "resolve-config.py", empty, bare)
    check("no plugin.json → path fallback",
          "Traceback" not in r.stderr and r.returncode in (0, 2), f"rc={r.returncode} {r.stderr.strip()}")

    # 11. fig's own floor and its paired key. Run fig's copy; the pm one is identical.
    FIG = REPO / "plugins" / "fig" / "_common" / "scripts" / "lib" / "resolve-config.py"
    FIG_NAME = "figma-conventions.yaml"
    r = run_script(FIG, empty, bare, "--name", FIG_NAME)
    fcfg = parse(r) or {}
    check("fig floor: the local defaults", r.returncode == 0
          and fcfg.get("component_audit", {}).get("body_offset") is None
          and fcfg.get("task_tracker", {}).get("type") is None
          and fcfg.get("qa", {}).get("baseline", {}).get("prd") == {"type": "markdown", "ref": None},
          r.stderr)

    fig_proj = Path(tmp) / "fig-proj"
    fig_proj.mkdir()
    (fig_proj / FIG_NAME).write_text("task_tracker:\n  ref: x\n")
    r = run_script(FIG, fig_proj, bare, "--name", FIG_NAME, "--authored", "task_tracker.type")
    check("fig paired: task_tracker.ref without type → --authored stops",
          r.returncode == 3 and "task_tracker.type is not set in figma-conventions.yaml, while "
          "task_tracker.ref is" in r.stderr, f"rc={r.returncode} {r.stderr.strip()}")

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures))
    sys.exit(1)
print("resolve-config fixtures · PASS")
