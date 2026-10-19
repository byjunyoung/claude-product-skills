#!/usr/bin/env python3
"""Fixtures for draft-conventions.py — observations in, a draft out, and nothing invented.

    python3 tools/test/draft-conventions.test.py

A synthetic probe has the shape probe-page.js returns. Three tidy pages must yield a convention
with its evidence; a thin sample and a split vote must yield null with the reason; no
observations must refuse. And every key the draft writes must be one verify.py accepts in a
team config — the draft *becomes* the team config, so a key verify rejects is a draft that
breaks the next run.

Every leaf the draft writes is one of two kinds: a value the probes observed, with its evidence
on its own line or on the line that opens its block, or a key only a person can answer, left
null for /fig:setup to ask. A floor value written as though somebody chose it is the third kind,
and the one this test keeps out: a team whose config carries it stops receiving the default's
changes.
"""
import importlib.util, json, re, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "plugins" / "fig" / "_common" / "scripts" / "lib"
SCHEMA = REPO / "plugins" / "fig" / "_common" / "conventions.example.yaml"
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def probe(page, frames, gap=120, pitch=1560, sec_gap=240, row_gap=480, fill="#6B7280"):
    n = len(frames)
    return {
        "page": page,
        "frameNames": frames,
        "suffixes": {"Default": n // 2, "Empty": n // 4, "Error": n // 4},
        "sections": [{"name": f"0{i}. Account - Feature {i}", "w": 3000, "fill": {"hex": fill, "opacity": 0.04},
                      "stroke": {"hex": fill}, "dash": [20, 20], "radius": 72, "strokeWeight": 1, "strokeAlign": "INSIDE"} for i in (1, 2, 3)],
        "gaps": {"frameX": [gap] * n, "frameY": [gap] * 3, "sectionX": [sec_gap] * 3, "sectionY": [row_gap] * 2},
        "columnPitch": [pitch] * n,
        "dashedFrames": [{"fill": {"hex": "#FAFAFB"}, "stroke": {"hex": "#B3B3BF"}, "dash": [10, 8], "strokeWeight": 2}] * 3,
        "arrows": {"count": 4, "styles": [{"color": {"hex": "#4A5463"}, "weight": 3, "dash": None}] * 4, "headGaps": [12, 12, 12, 13]},
        "labels": {"styles": [{"font": {"family": "Inter", "style": "Medium", "size": 20}, "padding": [10, 5], "radius": 8,
                               "fill": {"hex": "#FFFFFF"}, "stroke": {"hex": "#D9DBE3"}, "textColor": {"hex": "#59616E"}}] * 3},
        "pageDirectFrames": 0,
    }


def run(probes, file_key="ABC123"):
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i, p in enumerate(probes):
            f = Path(tmp) / f"p{i}.json"; f.write_text(json.dumps(p)); paths.append(str(f))
        key = ["--file-key", file_key] if file_key else []
        r = subprocess.run([sys.executable, str(LIB / "draft-conventions.py"), *key, *paths], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr


INTERVIEW_KEYS = {
    "naming.required_states",
    "layout.section_padding",
    "layout.reference_frame_width",
    "arrows.trunk",
    "arrows.trunk_to_target_min",
    "arrows.parallel_offset",
    "arrows.label.offset_from_target",
}
EVIDENCE = re.compile(r"\d+/\d+|0 observed|too few|split|observed")
COMMENT = re.compile(r"\s+#\s")     # a comment, not the # inside "#6B7280"


def unvouched(text):
    """Leaves that are neither observed nor an interview key left null, as 'path — line'.

    The dotted path is built from indentation. A leaf is vouched for by the evidence in its own
    comment or in the comment of its nearest parent line — so a `key:   # … observed`
    comment covers the leaves under it, and a comment further up covers nothing.
    """
    bad, stack = [], []                               # stack of (indent, key, comment)
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        parts = COMMENT.split(raw.strip(), maxsplit=1)
        body, comment = parts[0], (parts[1] if len(parts) > 1 else "")
        key, _, value = body.partition(":")
        key, value = key.strip().strip("\"'"), value.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if not value:                                 # opens a block
            stack.append((indent, key, comment))
            continue
        path = ".".join([k for _, k, _ in stack] + [key])
        parent = stack[-1][2] if stack else ""
        if path in INTERVIEW_KEYS and value == "null":
            continue
        if EVIDENCE.search(comment) or EVIDENCE.search(parent):
            continue
        bad.append(f"{path} — {raw.strip()}")
    return bad


import yaml
tidy = [probe(f"[UI] Page {i}", [f"Screen{j}-Default" for j in range(6)] + [f"Screen{j}-Empty" for j in range(3)]) for i in range(3)]
tidy[0]["sections"].append(dict(tidy[0]["sections"][0], name="Template"))   # a section the audit should skip
rc, out, err = run(tidy)
cfg = yaml.safe_load(out) if rc == 0 else None
check("three tidy pages → a draft", rc == 0 and isinstance(cfg, dict), err)
if cfg:
    check("naming inferred with evidence", cfg["naming"]["frame"] == "{screen}-{state}" and "match" in out)
    check("frame_gap 120 as the mode", cfg["layout"]["frame_gap"] == 120, str(cfg["layout"]))
    check("column_grid 1560", cfg["layout"]["column_grid"] == 1560)
    check("section fill read off the file", cfg["section_style"]["fill"] == "#6B7280")
    check("head_gap ±3 becomes gap_range", cfg["arrows"]["audit"]["gap_range"] == [9, 15], str(cfg["arrows"]["audit"]))
    bad = unvouched(out)
    check("every leaf is observed or an interview key", not bad, "; ".join(bad))
    top = [k for k in ("pages", "task_tracker", "tools", "guide_source", "design_system", "component_audit") if k in cfg]
    check("no top-level pages, task_tracker, tools, guide_source, design_system, component_audit", not top, ", ".join(top))
    check("ASCII names → no sync block, the floor's patterns stand", "sync" not in cfg, str(cfg.get("sync")))
    mine = ((cfg.get("files") or {}).get("ABC123") or {}).get("pages") or {}
    check("exclusion candidates under the file key", mine.get("exclude_sections") == ["^Template$"], str(cfg.get("files")))
    check("no page rules at the top level — a person decides, per file",
          "pages" not in cfg and not {"strict", "free", "readonly"} & set(mine), str(mine))

    # The drafter's own list is the one this test holds it to — a key added on one side fails here
    spec = importlib.util.spec_from_file_location("draft", LIB / "draft-conventions.py")
    draft = importlib.util.module_from_spec(spec); spec.loader.exec_module(draft)
    theirs = set(getattr(draft, "INTERVIEW_KEYS", ()))
    check("the drafter's INTERVIEW_KEYS are these seven", theirs == INTERVIEW_KEYS, str(sorted(theirs ^ INTERVIEW_KEYS)))

    # The draft becomes the team config. Every key must be one verify.py accepts there.
    spec = importlib.util.spec_from_file_location("verify", REPO / "tools" / "verify.py")
    # verify.py runs checks on import, so lift just the two helpers out of its source instead
    src = (REPO / "tools" / "verify.py").read_text()
    ns = {}
    exec(src[src.index("def leaf_kv"):src.index("def check_plugin")], ns)
    known = set(ns["leaf_paths"](yaml.safe_load(SCHEMA.read_text())))
    unknown = sorted(k for k in ns["leaf_paths"](cfg) if k not in known and not k.startswith("files."))
    check("every key the draft writes is one verify accepts in a team config", not unknown, ", ".join(unknown))

rc, out, err = run(tidy[:1])
cfg = yaml.safe_load(out) if rc == 0 else {}
check("one page → gaps still inferred from six frames", cfg.get("layout", {}).get("frame_gap") == 120)
thin = [probe("[UI] Thin", ["A-Default", "B-Default"], gap=120)]
thin[0]["gaps"]["frameX"] = [120]; thin[0]["gaps"]["frameY"] = []; thin[0]["sections"] = thin[0]["sections"][:1]
thin[0]["gaps"]["sectionX"] = []; thin[0]["gaps"]["sectionY"] = []
rc, out, err = run(thin)
cfg = yaml.safe_load(out) if rc == 0 else {}
check("thin sample → frame_gap null with the reason", cfg.get("layout", {}).get("frame_gap") is None and "too few" in out, out[:200])

split = [probe("[UI] Split", [f"S{j}-Default" for j in range(6)], gap=120), probe("[UI] Split 2", [f"T{j}-Default" for j in range(6)], gap=200)]
rc, out, err = run(split)
cfg = yaml.safe_load(out) if rc == 0 else {}
check("split vote → frame_gap null, says split", cfg.get("layout", {}).get("frame_gap") is None and "split" in out, out[:200])

rc, out, err = run([{"error": "page not found"}])
check("no observations → refuses", rc != 0 and "no observations" in (err + out))

rc, out, err = run(tidy, file_key=None)
check("--file-key missing → refuses", rc != 0 and "usage" in err.lower(), f"rc={rc} {err[:200]}")

# Section and page names are written in the team's own language. Non-ASCII letters used to widen
# the sync pair patterns; sync now compares by name, so the drafter writes no such block — and still runs.
umlaut = [probe("Menü", [f"Screen{j}-Default" for j in range(6)] + [f"Screen{j}-Empty" for j in range(3)]) for _ in range(3)]
rc, out, err = run(umlaut)
cfg = yaml.safe_load(out) if rc == 0 else {}
check("non-ASCII names → the draft still runs and writes no pair patterns",
      rc == 0 and ("pair_" + "patterns") not in out and "pair_" + "patterns" not in str((cfg or {}).get("sync") or {}),
      err[:200])
bad = unvouched(out) if rc == 0 else [f"no draft — {err[:200]}"]
check("non-ASCII names → every leaf is still observed or an interview key", not bad, "; ".join(bad))

# probe-page.js now reports nested sections too, with a depth. Their names are not held to the
# section naming rule (audit-struct checks top-level names only), so they must not dilute it.
nested = [probe("Page", [f"Screen{j}-Default" for j in range(6)]) for _ in range(3)]
for p in nested:
    p["sections"] += [{"name": n, "depth": 1, "w": 900, "fill": None, "stroke": None, "dash": None, "radius": 0,
                       "strokeWeight": 1, "strokeAlign": "INSIDE"} for n in ("Work", "Personal", "Shared", "Admin")]
rc, out, err = run(nested)
cfg = yaml.safe_load(out) if rc == 0 else {}
check("nested sections do not dilute the section naming evidence",
      rc == 0 and (cfg.get("naming") or {}).get("section_pattern") is not None, err[:200] + out[:200])

print()
if failures:
    print(f"{len(failures)} failed — " + ", ".join(failures)); sys.exit(1)
print("draft-conventions fixtures · PASS")
