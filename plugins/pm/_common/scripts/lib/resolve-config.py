#!/usr/bin/env python3
"""Config resolver — finds the config files, deep-merges them, emits one line of JSON.

This file lives as a copy in each plugin. Change one and not the other and verify catches it.

The Figma plugin sandbox has no filesystem. So the config is resolved on the host and the
resulting JSON is prepended to the audit script as `const CFG = {...};` before it goes to use_figma.

Usage
    python3 resolve-config.py [fileKey]      → JSON (stdout)
    python3 resolve-config.py --js [fileKey] → one `const CFG = {...};` line
    python3 resolve-config.py --where        → which files were used, nothing else
    python3 resolve-config.py --name pm-conventions.yaml   → change the filename to look for
    python3 resolve-config.py --need task.record.ref,task.link_property
                                             → exit 2 naming any of these that is null, no JSON
    python3 resolve-config.py --authored task.contract.level
                                             → exit 3 naming any of these no layer of yours sets
                                             A key that only means something beside another (a ref and its
                                             type) is held to this only when the other is written without it
    python3 resolve-config.py --origin       → where this machine's config came from, nothing else

A skill that cannot run without a value asks for it with --need. A null there is a config
gap — setup writes it — and the skill stops on the key's name instead of running on nothing,
which is how a run on an unfinished config used to come back thin and look like a result.

--authored is the axis beside it, and --need cannot see what it sees. A key no config of
yours mentions still resolves — to the floor's value — so it is not missing, it is somebody
else's. Where that value decides the shape of what a run writes out, the run is deciding it
on a default the team never saw. Preflight already keeps the floor apart for the same
reason: a requirement comes from a value somebody wrote, never from a default nobody chose.

The layers merge (later covers earlier). A config holding only some keys works as it is —
missing keys are filled by the defaults, and only what is written gets covered.
    1. ../conventions.example.yaml           bundled defaults (the floor)
    2. ~/.claude/<name>                      the user's shared config
    3. ./<name>                              per project (strongest)

Deleting a key does not switch a check off — write null for that. Deleting restores the default.
A map keeps the order the schema declares; write every one of its keys to reorder it.
"""
import json, os, subprocess, sys, time

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
DEFAULT_NAME = {"pm": "pm-conventions.yaml"}.get(PLUGIN, "figma-conventions.yaml")

# Keys that must be written beside another. (key, trigger, trigger values that exempt it.)
# A written trigger whose key is absent is completed by the bundled default, and that default
# was chosen for some other case — a ref read against a type that has since changed, a tracker
# handed the floor's local folder — so the pair is written together. A key listed here is
# checked by --authored only while its trigger is written without it — a config that writes
# neither is not asking anything of it.
AUTHORED_WITH = (
    ("task.record.type", "task.record.ref", frozenset()),
    ("task.link_property", "task.record.type", frozenset({"markdown"})),
    ("task.record.ref", "task.record.type", frozenset({"markdown", "none"})),
    ("task_tracker.type", "task_tracker.ref", frozenset()),
)

# Why each pair stops, said after `{key} is not set in {name}, while {trigger} is —`. {value} is
# what the trigger says. A pair with no entry here gets the rule itself rather than a reason
# that belongs to another pair.
AUTHORED_WHY = {
    ("task.record.type", "task.record.ref"):
        "{key} used to come from the plugin's own defaults, and that default has changed, so the "
        "value you wrote would now be read some other way",
    ("task.link_property", "task.record.type"):
        "the record's tracker has to say which of its properties holds the ticket's link, and the "
        "plugin's own default names the key a markdown file carries, not one of yours",
    ("task.record.ref", "task.record.type"):
        "a record kept in {value} has to say which database or repository it points at, and the "
        "plugin's own default is a local folder",
    ("task_tracker.type", "task_tracker.ref"):
        "the plugin's own default leaves {key} unset, which borrows pm's task record where there is "
        "one, so a ref written alone no longer says which kind of tracker it points at",
}
AUTHORED_RULE = "{key} is read together with {trigger}, so the two are written together"


def candidates(name):
    """From the floor upward. Later covers earlier."""
    return [
        os.path.normpath(os.path.join(HERE, "..", "..", "conventions.example.yaml")),
        os.path.expanduser(os.path.join("~/.claude", name)),
        os.path.join(os.getcwd(), name),
    ]


def load(path):
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML missing — run `pip3 install pyyaml`, or put a .json of the same name in place")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge(base, over):
    """over covers base. Dicts merge deeply, everything else wholesale.

    Key order is the base's, so a partial override cannot shuffle a map whose order is read
    out — ticket.sections is written into a ticket in the order it is written down here, and
    a team naming one section should not move it to the front. Writing the map ENTIRE is how
    that order is changed: name every key the schema declares, in the order your tracker's
    own template puts them, and that order is what comes out.
    """
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    if over and set(over) >= set(base):
        out = {k: out[k] for k in list(over) + [x for x in out if x not in over]}
    return out


def resolve(file_key=None, name=DEFAULT_NAME):
    cands = candidates(name)
    cfg, used = {}, []
    for p in cands:
        if os.path.exists(p):
            cfg = merge(cfg, load(p))
            used.append(p)
    if not used:
        sys.exit("No config file found: " + " / ".join(cands))
    src = used[-1]              # the strongest layer. Reported so it is clear which config it ran on

    files = cfg.pop("files", None) or {}
    if file_key and file_key in files:
        cfg = merge(cfg, {k: v for k, v in files[file_key].items() if k != "label"})
        cfg.setdefault("meta", {})["file_label"] = files[file_key].get("label", file_key)
    elif file_key:
        cfg.setdefault("meta", {})["file_label"] = None      # no per-file convention registered
    cfg.setdefault("meta", {})["source"] = src
    cfg["meta"]["layers"] = used
    return cfg, src


def unmet(cfg, keys):
    """The dotted keys whose value is missing, null, or an empty string. An empty list or map
    is a value — `label_map: {}` says nothing is mapped, which is a legitimate state."""
    out = []
    for k in keys:
        cur = cfg
        for part in k.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur is None or cur == "":
            out.append(k)
    return out


def present(d, dotted):
    """Whether the dotted key exists as a chain of keys, whatever its value. A key written
    `null` is present — somebody decided that, and --need is what reads the decision. A key
    nobody wrote at all is not."""
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def user_layers(name):
    """(the layers above the floor, merged), (the paths they came from). Empty where a
    machine has no config of its own and every value is the plugin's."""
    cfg, used = {}, []
    for p in candidates(name)[1:]:
        if os.path.exists(p):
            cfg = merge(cfg, load(p))
            used.append(p)
    return cfg, used


def lookup(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def unpaired(user):
    """(key, trigger) for each AUTHORED_WITH entry whose trigger is written in `user`, whose
    written value does not exempt it, and whose key is not."""
    out = []
    for key, trigger, exempt in AUTHORED_WITH:
        if not present(user, trigger) or present(user, key):
            continue
        if str(lookup(user, trigger)).lower() in exempt:
            continue
        out.append((key, trigger))
    return out


def inherited(keys, name):
    """The dotted keys no layer of yours mentions. A key listed in AUTHORED_WITH counts only
    when it is unpaired; every other key counts whenever it is absent."""
    user, _ = user_layers(name)
    pairs = dict(unpaired(user))
    paired_keys = {k for k, _, _ in AUTHORED_WITH}
    return [k for k in keys if (k in pairs if k in paired_keys else not present(user, k))]


def git(root, *args, timeout=5):
    """git, read-only and off the network. None where it cannot answer — not a repository,
    no git on the machine, a command that took too long."""
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def days(path):
    """Whole days since the file was last written, or None where it is not there."""
    try:
        return int((time.time() - os.path.getmtime(path)) / 86400)
    except OSError:
        return None


def origin_state(name):
    """What this machine can say about where its config came from, as fields.

    A config shared across a team is a copy on every machine, and a copy says nothing about
    its own age — which is how one goes quietly stale while every run on it succeeds. None
    of this asks the config to declare anything: a stamp naming the version a file was
    written for is a claim about the past that nobody updates, and the person who reads the
    warning silences it by editing the stamp. Everything here is read off the filesystem
    instead, so a config written before any of this existed is described just as accurately.

    `root` is set only where the strongest layer resolves into a git work tree — one way to
    share a config, not the only one. Nothing here goes near the network: the count git can
    give is as of the last fetch, so `fetched` travels beside `behind` and a fetch that has
    not run in days is the more useful of the two findings.
    """
    _, used = user_layers(name)
    if not used:
        return {"path": None}
    path = used[-1]
    real = os.path.realpath(path)
    st = {"path": path, "real": real, "linked": real != os.path.abspath(path),
          "edited": days(real), "root": None, "dirty": False, "behind": None, "fetched": None}
    root = git(os.path.dirname(real), "rev-parse", "--show-toplevel")
    if not root:
        return st
    st["root"] = root
    st["dirty"] = bool(git(root, "status", "--porcelain", "--", real))
    behind = git(root, "rev-list", "--count", "HEAD..@{u}")
    if behind is None:
        return st                      # no upstream — nothing for it to be behind
    st["behind"] = int(behind or 0)
    gitdir = git(root, "rev-parse", "--absolute-git-dir")
    st["fetched"] = days(os.path.join(gitdir, "FETCH_HEAD")) if gitdir else None
    return st


def origin(name):
    """origin_state as sentences, deepest rung last. A team that shares nothing stops at the
    first line, and the rungs below it simply do not apply."""
    st = origin_state(name)
    if not st.get("path"):
        return [f"no {name} of your own — every value came from the plugin's defaults"]
    seen = f"last edited {st['edited']}d ago" if st["edited"] is not None else "never read"
    out = [f"{st['path']} → {st['real']}, {seen}" if st["linked"]
           else f"{st['path']} — its own file, {seen}"]
    if not st["root"]:
        return out
    out.append(f"kept in git at {st['root']}")
    if st["dirty"]:
        out.append("edited here and not committed — this change is on this machine only")
    if st["behind"] is None:
        out.append("no upstream branch — there is nothing for it to be behind")
        return out
    f = st["fetched"]
    when = "not fetched since it was cloned" if f is None else f"fetched {f}d ago"
    out.append(f"{st['behind']} commit(s) behind upstream, {when} — "
               f"`git -C {st['root']} pull --ff-only`" if st["behind"]
               else f"level with upstream, {when}")
    if f is not None and f > 1:
        out.append("git knows only what that fetch told it, so the count above is a floor")
    return out


def take(argv, flag):
    """The value after a flag, removed from argv. None where the flag is absent."""
    if flag not in argv:
        return None
    i = argv.index(flag)
    if i + 1 >= len(argv):
        sys.exit(f"{flag} needs a value after it")
    val = argv[i + 1]
    del argv[i:i + 2]
    return val


def main():
    argv = sys.argv[1:]
    as_js = "--js" in argv
    where = "--where" in argv
    show_origin = "--origin" in argv
    name = take(argv, "--name") or DEFAULT_NAME
    need = [k.strip() for k in (take(argv, "--need") or "").split(",") if k.strip()]
    owned = [k.strip() for k in (take(argv, "--authored") or "").split(",") if k.strip()]
    args = [a for a in argv if not a.startswith("--")]
    cfg, src = resolve(args[0] if args else None, name)
    gaps = unmet(cfg, need)
    if gaps:
        for k in gaps:
            print(f"{k} is not set in {name} — this cannot run without it. /{PLUGIN}:setup fills it in, or write it by hand", file=sys.stderr)
        sys.exit(2)
    borrowed = inherited(owned, name)
    if borrowed:
        user = user_layers(name)[0]
        trigger_of = dict(unpaired(user))
        for k in borrowed:
            if k in trigger_of:
                t = trigger_of[k]
                why = AUTHORED_WHY.get((k, t), AUTHORED_RULE).format(key=k, trigger=t, value=lookup(user, t))
                print(f"{k} is not set in {name}, while {t} is — {why}. Write {k} beside {t} "
                      f"— the schema and what each value governs are in _common/conventions.example.yaml "
                      f"— and run again.", file=sys.stderr)
                continue
            print(f"{k} is not set in {name} — the value in play came from the plugin's own "
                  f"defaults, which nobody on your team chose. Writing on one puts a shape into "
                  f"your tracker that no one decided on. Set it — the schema and what each value "
                  f"governs are in _common/conventions.example.yaml — and run again.", file=sys.stderr)
        print("", file=sys.stderr)
        for line in origin(name):
            print(f"  {line}", file=sys.stderr)
        sys.exit(3)
    if show_origin:
        for line in origin(name):
            print(line)
    elif where:
        print(src)
    elif as_js:
        print("const CFG = " + json.dumps(cfg, ensure_ascii=False) + ";")
    else:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
