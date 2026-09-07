#!/usr/bin/env python3
"""Fixtures for starter-conventions.py — the rule set written when a file has nothing to observe.

    python3 tools/test/starter-conventions.test.py

Two claims are checked: every key it writes exists in the schema, so a starter file never trips
the "key present only in the team config" check; and laid over the bundled defaults as a project
layer, the merged config has the values lint and prep need — spacing filled, pages named.
"""
import os, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "plugins" / "fig" / "_common" / "scripts" / "lib"
SCHEMA = REPO / "plugins" / "fig" / "_common" / "conventions.example.yaml"
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def starter(*args):
    r = subprocess.run([sys.executable, str(LIB / "starter-conventions.py"), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def leaf_paths(o, prefix=""):
    if isinstance(o, dict) and o:
        for k, v in o.items():
            yield from leaf_paths(v, f"{prefix}{k}.")
    else:
        yield prefix.rstrip(".")


def null_paths(o, prefix=""):
    """The keys the schema leaves null — a slot rather than a value.

    What shape fills one is the business of the skill that reads it: `pages.canonical` takes
    `{match, pattern}`, and the schema documents that in a comment a parser cannot see. Writing
    into a slot is filling a documented hole, so it is not the thing this check is looking for —
    a key nobody declared is.
    """
    if isinstance(o, dict) and o:
        for k, v in o.items():
            yield from null_paths(v, f"{prefix}{k}.")
    elif o is None:
        yield prefix.rstrip(".")


import yaml
schema = yaml.safe_load(SCHEMA.read_text())
known = set(leaf_paths(schema)) | {p for p in (".".join(x.split(".")[:i]) for x in leaf_paths(schema) for i in range(1, len(x.split(".")))) }
slots = tuple(s + "." for s in null_paths(schema))

rc, out, err = starter("--width", "1440")
cfg = yaml.safe_load(out) if rc == 0 else None
check("1440 → runs and parses", rc == 0 and isinstance(cfg, dict), err)
if cfg:
    unknown = sorted(k for k in leaf_paths(cfg) if k not in known and not k.startswith(slots))
    check("1440 → every key is in the schema", not unknown, ", ".join(unknown))
    lo = cfg["layout"]
    check("1440 → gap 120, grid 1560", lo["frame_gap"] == 120 and lo["column_grid"] == 1560, str(lo))
    check("1440 → strict page prefix escaped", cfg["pages"]["strict"] == ["^\\[UI\\]\\ "], str(cfg["pages"]["strict"]))
    check("1440 → profile is starter", cfg["meta"]["profile"] == "starter")
    check("1440 → every line of layout says where it came from", all("#" in ln for ln in out.splitlines() if ln.startswith("  ") and ":" in ln and "layout" not in ln and ln.strip().split(":")[0] in lo), out)
    pg = cfg["pages"]
    check("1440 → released work is collected on a page derived from the prefix",
          pg.get("free") == ["^\\[Update\\]\\ "]
          and pg.get("archive", {}).get("pattern") == "^\\[Update\\]\\ ", str(pg))
    check("1440 → canonical and archive match by name",
          all(pg.get(k, {}).get("match") == "name" for k in ("canonical", "archive")), str(pg))
    check("1440 → queue is a divider band, since a page being drawn has no name to match",
          pg.get("queue", {}).get("match") == "divider"
          and pg["queue"]["pattern"] != pg["free"][0], str(pg.get("queue")))
    check("1440 → canonical is the page engineering builds from",
          pg.get("canonical", {}).get("pattern") == pg["strict"][0], str(pg.get("canonical")))
    check("1440 → what was put away is audited by nothing",
          any("rchive" in x for x in pg["exclude_sections"]), str(pg["exclude_sections"]))

# A prefix with no word in it has nothing to swap. Inventing a page name the team never said is
# worse than leaving sync unconfigured, so it writes neither.
rc, out, err = starter("--prefix", "\U0001f3a8 ")
cfg = yaml.safe_load(out) if rc == 0 else None
check("a wordless prefix → runs", rc == 0, err)
if cfg:
    # readonly and exclude_sections are fixed safety rules, not derivations — they go out whatever
    # the prefix is. What must not appear is a page name that could only have come from swapping.
    check("a wordless prefix → nothing derived from it",
          not ({"free", "canonical", "queue", "archive"} & set(cfg["pages"])), str(cfg["pages"]))

rc, out, err = starter("--width", "390", "--states", "Empty,Error", "--prefix", "[App] ")
cfg = yaml.safe_load(out) if rc == 0 else None
check("390 → runs", rc == 0, err)
if cfg:
    lo = cfg["layout"]
    check("390 → spacing snaps to 8", all(v % 8 == 0 for v in (lo["frame_gap"], lo["section_padding"], lo["section_gap_same_row"], lo["domain_row_gap"])), str(lo))
    check("390 → Default forced into the states", cfg["naming"]["states"][0] == "Default", str(cfg["naming"]["states"]))
    check("390 → required_states only from the chosen list", set(cfg["naming"]["required_states"]["list"]) <= set(cfg["naming"]["states"]), str(cfg["naming"]["required_states"]))
    check("390 → own prefix", cfg["pages"]["strict"] == ["^\\[App\\]\\ "], str(cfg["pages"]["strict"]))

rc, out, err = starter("--width", "12")
check("a width that is not a width → refused", rc != 0)

# Laid over the bundled defaults as a project layer, lint and prep have what they need
with tempfile.TemporaryDirectory() as tmp:
    home, proj = Path(tmp) / "home", Path(tmp) / "proj"
    (home / ".claude").mkdir(parents=True); proj.mkdir()
    (proj / "figma-conventions.yaml").write_text(starter("--width", "1440")[1])
    env = dict(os.environ, HOME=str(home), PYTHONUSERBASE=site.getuserbase())
    r = subprocess.run([sys.executable, str(LIB / "resolve-config.py")], cwd=proj, env=env, capture_output=True, text=True)
    import json
    merged = json.loads(r.stdout) if r.returncode == 0 else {}
    check("merged → layout filled where the bundle had null", merged.get("layout", {}).get("frame_gap") == 120 and merged["layout"]["section_padding"] == 120, r.stderr)
    check("merged → bundled arrow style still there", merged.get("arrows", {}).get("stroke_weight") == 3)
    check("merged → strict pages set", merged.get("pages", {}).get("strict") == ["^\\[UI\\]\\ "])

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("starter-conventions fixtures · PASS")
