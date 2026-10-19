#!/usr/bin/env python3
"""Adapter lookup — which file carries the calls for a tool, or that none does.

The calls for one tool live in one file, named by the type the config uses: trackers/<type>.md
for a task tracker, sources/<type>.md for chat or a calendar. The bundled ones sit under
_common/ beside this script. The ones you draft live outside the plugin — `adapters.dirs` in
the config — so an update does not overwrite them. Later dirs cover earlier, like the config
layers, so a file of yours with the same name replaces a bundled one.

Usage
    python3 adapter.py --kind trackers --type notion     → the path to read
    python3 adapter.py --kind sources  --type slack
    python3 adapter.py --kind trackers --type none       → prints "none", exit 0 — no adapter needed
    python3 adapter.py --kind trackers --type linear     → exit 3, stderr says where the template is
    python3 adapter.py --kind trackers --type github --role record
                                                          → exit 4: the file exists but answers as a mirror
    --name pm-conventions.yaml                             the config filename, as resolve-config takes it

--type is required: without it the script exits 1. A skill whose config names no tool passes
`none` explicitly, so a forgotten flag cannot read as "no tool".

Exit 3 is the one a skill stops on. It means the type names a tool nobody has written the calls
for. The fix is /pm:setup drafting them from the tools connected on this machine — never a
skill improvising them from what it remembers of the tool's API.

Exit 4 is the other stop. The file exists, but its `roles:` line does not include the side
the skill is reading — a mirror-only adapter asked for a record's list, say. Half an adapter
is not an adapter for the other half; /pm:setup's step 4c drafts the missing side.
"""
import importlib.util, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.normpath(os.path.join(HERE, "..", ".."))
KINDS = ("trackers", "sources")
ROLES = {"trackers": ("record", "mirror"), "sources": ("chat", "calendar")}


def declared_roles(path):
    """The `roles:` line near the top, as a set. None where the file declares nothing — an
    undeclared file is taken to serve every side, which is how a hand-written one keeps working."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        for _ in range(12):
            m = re.match(r"^roles:\s*(.+?)\s*$", f.readline())
            if m:
                return {r.strip().lower() for r in m.group(1).split(",") if r.strip()}
    return None


def take(argv, flag):
    if flag not in argv:
        return None
    i = argv.index(flag)
    if i + 1 >= len(argv):
        sys.exit(f"{flag} needs a value after it")
    val = argv[i + 1]
    del argv[i:i + 2]
    return val


def config_dirs(name):
    """adapters.dirs from the resolved config, ~ expanded. Empty where the config cannot be read —
    the bundled files are still looked at, and resolve-config's own error says why."""
    spec = importlib.util.spec_from_file_location("resolve_config", os.path.join(HERE, "resolve-config.py"))
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cfg, _ = mod.resolve(None, name)
    except (SystemExit, Exception):
        return []
    dirs = (cfg.get("adapters") or {}).get("dirs") or []
    return [os.path.expanduser(d) for d in dirs if isinstance(d, str) and d]


def main():
    argv = sys.argv[1:]
    kind = take(argv, "--kind")
    raw_typ = take(argv, "--type")
    typ = (raw_typ or "").strip().lower()
    name = take(argv, "--name") or "pm-conventions.yaml"
    role = (take(argv, "--role") or "").strip().lower()
    if kind not in KINDS:
        sys.exit("--kind is one of: " + ", ".join(KINDS))
    if raw_typ is None:
        sys.exit("--type is required — pass none where there is no tool")
    if role and role not in ROLES[kind]:
        sys.exit(f"--role for {kind} is one of: " + ", ".join(ROLES[kind]))
    if typ in ("", "none"):
        print("none")
        return

    # Absolute, so the path a skill is handed does not depend on where it happens to be run from
    candidates = [os.path.join(COMMON, kind, f"{typ}.md")]
    candidates += [os.path.join(d, kind, f"{typ}.md") for d in config_dirs(name)]
    candidates = [os.path.abspath(c) for c in candidates]
    found = [p for p in candidates if os.path.exists(p)]
    if found:
        roles = declared_roles(found[-1])
        if role and roles is not None and role not in roles:
            print(f"{typ} is supported as the {' and '.join(sorted(roles))} side, but this needs it as the {role} side — {found[-1]}", file=sys.stderr)
            print(f"/pm:setup can add the {role} side from the tools connected on this machine. Support for one side does not cover the other.", file=sys.stderr)
            sys.exit(4)
        print(found[-1])
        return
    template = os.path.join(COMMON, kind, "_template.md")
    print(f"{typ} is not supported yet — nothing here describes how to work with it (looked for {kind}/{typ}.md in: " + ", ".join(candidates) + ")", file=sys.stderr)
    print(f"/pm:setup can write that support from the tools connected on this machine. A template to start from: {template}", file=sys.stderr)
    sys.exit(3)


if __name__ == "__main__":
    main()
