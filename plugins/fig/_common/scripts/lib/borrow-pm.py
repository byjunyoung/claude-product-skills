#!/usr/bin/env python3
"""What fig borrows from pm — whether pm is installed here, whether it is new enough, and which of
its documents a run reads from or writes into.

fig keeps no PRD and no task file of its own. Where pm is installed, its PRD is the plan of record
a screen is drawn and audited against, and its markdown task files are where a handoff writes its
one line. Every fig skill that crosses into pm asks this script rather than deciding for itself,
so there is one answer to "which pm, which version, which document, which folder".

Usage
    python3 borrow-pm.py where                         → {"root", "version", "ok"}
    python3 borrow-pm.py prd [--spec-url V] [fileKey]  → where the PRD is
    python3 borrow-pm.py task [fileKey]                → what to do with a handoff's line

Each prints one JSON object. Exit 0 for every answer — "print the line instead" is an answer, not
a failure. Exit 3 when fig's own config stops on a key written without its pair; its message
passes through untouched, so it reads the same as from every other skill. Exit 6 when --spec-url
names something this cannot read as a PRD. Exit 1 on a usage error, or where fig's own config
could not be read at all — a malformed figma-conventions.yaml, or its reader timing out — with
that reader's stderr passed through.

The PRD is looked for in this order, and the first step that answers is the answer:
    1. --spec-url, read by spec_kind. A .md file is answered as the one candidate.
    2. qa.baseline.prd in fig's config. null, or type none: no PRD, and pm is not asked. A ref:
       that document — a markdown folder's PRD files, or a .md file as the one candidate, with
       any `#…` kept in the ref. A type other than markdown with no ref: none, with a note asking
       for the link — the config says the PRD lives somewhere pm's files are not, so pm's files
       are not a stand-in for it. A plain string is an older config's Notion page, an empty one
       included.
    3. pm's prd.markdown.dir — only where the type is markdown (written, or the floor's) and the
       ref is null, and pm is installed, new enough, and keeps its PRD in markdown or git.
    4. none.

It reads and never writes. pm's config is read by pm's own resolve-config.py, never by fig's
copy: each copy finds the bundled defaults beside itself, so fig's copy would read pm's file
against fig's floor. pm's version is read from the plugin.json of the copy that would run, not
from the registry — the registry says what was installed, the manifest says what is there.

The helpers above main() are imported by preflight.py, so nothing here runs on import and
find_pm never raises: a missing, unreadable or malformed file is treated as absent.
"""
import argparse, json, os, re, subprocess, sys, urllib.parse

PM_MIN = "0.38.0"               # the first pm whose task files and PRD sit in local markdown
HEADING = "Design changes"      # where a handoff's line goes when task_tracker.ui_section_heading is unset

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_RESOLVE = os.path.join(HERE, "resolve-config.py")
PM_NAME = "pm-conventions.yaml"
# The pair every pm skill asks for. Borrowing stops where pm itself would stop.
PM_AUTHORED = "task.record.type,task.record.ref"
INSTALL_NOTE = "Installing pm writes this line into the task file."


# ---- finding pm

def read_json(path):
    """The parsed file, or None where it is missing, unreadable or not JSON."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, RecursionError):
        return None


def config_dir(env):
    """Where Claude Code keeps its plugins and settings for this environment."""
    if env.get("CLAUDE_CONFIG_DIR"):
        return env["CLAUDE_CONFIG_DIR"]
    return os.path.join(env.get("HOME") or os.path.expanduser("~"), ".claude")


def real(path):
    try:
        return os.path.realpath(path)
    except (OSError, ValueError, TypeError):
        return None


def within(path, root):
    """True where `path` is `root` or sits below it, after symlinks — a temp dir on macOS is
    /var/... by one name and /private/var/... by the other."""
    p, r = real(path), real(root)
    if not p or not r:
        return False
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


def pm_at(root):
    """{"root", "version"} where `root` holds a plugin.json naming pm, else None."""
    if not isinstance(root, str) or not root:
        return None
    manifest = read_json(os.path.join(root, ".claude-plugin", "plugin.json"))
    if not isinstance(manifest, dict) or manifest.get("name") != "pm":
        return None
    version = manifest.get("version")
    return {"root": root, "version": version if isinstance(version, str) else ""}


def enabled_flag(env, cwd, key):
    """What the settings say about enabledPlugins[key], later files covering earlier; None where
    none of them says anything."""
    flag = None
    for path in (os.path.join(config_dir(env), "settings.json"),
                 os.path.join(cwd, ".claude", "settings.json"),
                 os.path.join(cwd, ".claude", "settings.local.json")):
        data = read_json(path)
        plugins = data.get("enabledPlugins") if isinstance(data, dict) else None
        if isinstance(plugins, dict) and key in plugins:
            flag = plugins[key]
    return flag


def registry_pm(env, cwd):
    """(marketplace, installPath) for every pm entry this cwd can see, in registry order, with the
    marketplace fig itself was installed from moved to the front. An entry is seen when its scope
    is user or its projectPath is cwd or one of cwd's parents."""
    data = read_json(os.path.join(config_dir(env), "plugins", "installed_plugins.json"))
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return []
    here = os.path.abspath(__file__)
    own, found = None, []
    for key, entries in plugins.items():
        if not isinstance(key, str) or "@" not in key or not isinstance(entries, list):
            continue
        name, market = key.split("@", 1)
        for e in entries:
            if not isinstance(e, dict) or not isinstance(e.get("installPath"), str):
                continue
            if name == "fig" and own is None and within(here, e["installPath"]):
                own = market
            elif name == "pm":
                project = e.get("projectPath")
                if e.get("scope") == "user" or (isinstance(project, str) and within(cwd, project)):
                    found.append((market, e["installPath"]))
    return sorted(found, key=lambda c: c[0] != own)        # stable: the rest keep registry order


def find_pm(env, cwd):
    """{"root", "version"} for the pm a run here would use, or None. FIG_PM_ROOT first — a
    --plugin-dir session or a test — then the plugin registry. An entry switched off in the
    settings is not installed, whatever the registry says."""
    pm = pm_at(env.get("FIG_PM_ROOT"))
    if pm:
        return pm
    for market, path in registry_pm(env, cwd):
        if enabled_flag(env, cwd, f"pm@{market}") is False:
            continue
        pm = pm_at(path)
        if pm:
            return pm
    return None


def version_ok(version, minimum=PM_MIN):
    """Whether `version` is at least `minimum`, compared part by part as numbers. A part that is
    not all digits — a pre-release tag, an empty string — is not a version this can vouch for."""
    def parts(v):
        if not isinstance(v, str):
            return None
        out = v.split(".")
        return [int(p) for p in out] if all(re.fullmatch(r"[0-9]+", p) for p in out) else None
    a, b = parts(version), parts(minimum)
    if a is None or b is None:
        return False
    n = max(len(a), len(b))
    return a + [0] * (n - len(a)) >= b + [0] * (n - len(b))


# ---- what a --spec-url is

NOTION_ID = re.compile(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                       r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def host_of(value):
    v = value if "://" in value else "https://" + value
    try:
        return (urllib.parse.urlsplit(v).hostname or "").lower()
    except ValueError:
        return ""


def on(host, domain):
    return host == domain or host.endswith("." + domain)


def spec_kind(value, cwd):
    """(kind, value): markdown where the part before `#` is a .md file that exists, notion for a
    Notion url or page id, figma for any Figma url, unknown otherwise."""
    v = (value or "").strip()
    path = os.path.expanduser(v.split("#", 1)[0])
    if path.lower().endswith(".md") and os.path.isfile(path if os.path.isabs(path) else os.path.join(cwd, path)):
        return "markdown", value
    host = host_of(v)
    if on(host, "notion.so") or on(host, "notion.site") or NOTION_ID.fullmatch(v):
        return "notion", value
    if on(host, "figma.com"):
        return "figma", value
    return "unknown", value


# ---- reading PRD files

def front_matter(path):
    """The file's front matter as a dict; {} where it has none or it cannot be read."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            if f.readline().rstrip("\r\n") != "---":
                return {}
            lines = []
            for line in f:
                if line.rstrip("\r\n") == "---":
                    break
                lines.append(line.rstrip("\r\n"))
            else:
                return {}
    except (OSError, UnicodeDecodeError):
        return {}
    try:
        import yaml
    except ImportError:
        out = {}
        for line in lines:
            m = re.match(r"^([A-Za-z_]+):\s*(.*?)\s*$", line)
            if m:
                out[m.group(1)] = m.group(2).strip("\"'")
        return out
    try:
        data = yaml.safe_load("\n".join(lines))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def named(fm, key, fallback):
    v = fm.get(key)
    return str(v).strip() if v is not None and str(v).strip() else fallback


def listing(d):
    try:
        return sorted(n for n in os.listdir(d) if not n.startswith("."))
    except OSError:
        return []


def candidates(ref, split, cwd):
    """Every PRD file under the folder `ref`, as {"path", "product", "domain"}, sorted by path.
    split product reads {ref}/*.md, one file per product; split domain reads {ref}/*/*.md, a
    folder per product holding index.md and a file per domain. Paths keep the form `ref` was
    given in, the way pm's own scripts print them."""
    base = ref if os.path.isabs(os.path.expanduser(ref)) else os.path.join(cwd, ref)
    base = os.path.expanduser(base)
    out = []
    if split == "domain":
        for folder in listing(base):
            if not os.path.isdir(os.path.join(base, folder)):
                continue
            for name in listing(os.path.join(base, folder)):
                full = os.path.join(base, folder, name)
                if not name.endswith(".md") or not os.path.isfile(full):
                    continue
                fm = front_matter(full)
                out.append({"path": os.path.join(ref, folder, name),
                            "product": named(fm, "product", folder),
                            "domain": named(fm, "domain", None if name == "index.md" else name[:-3])})
    else:
        for name in listing(base):
            full = os.path.join(base, name)
            if not name.endswith(".md") or not os.path.isfile(full):
                continue
            fm = front_matter(full)
            out.append({"path": os.path.join(ref, name),
                        "product": named(fm, "product", name[:-3]),
                        "domain": named(fm, "domain", None)})
    return sorted(out, key=lambda c: c["path"])


def one_file(ref, cwd):
    """The .md file `ref` names — the part before `#` — as the one candidate, [] where there is
    none. The path keeps the form `ref` was given in; the `#…` stays in the answer's ref, where it
    names the entry to start from."""
    given = ref.strip().split("#", 1)[0]
    path = os.path.expanduser(given)
    full = path if os.path.isabs(path) else os.path.join(cwd, path)
    if not given.lower().endswith(".md") or not os.path.isfile(full):
        return []
    fm = front_matter(full)
    return [{"path": given, "product": named(fm, "product", os.path.splitext(os.path.basename(given))[0]),
             "domain": named(fm, "domain", None)}]


def guess_split(base):
    """For a folder nobody's config describes: domain where a product folder holds index.md."""
    return "domain" if any(os.path.isfile(os.path.join(base, n, "index.md")) for n in listing(base)) else "product"


# ---- running the config readers

def run_py(script, args, cwd):
    try:
        return subprocess.run([sys.executable, script, *args], cwd=cwd, capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess([script], 1, "", f"{os.path.basename(script)}: {e}\n")


def lines_of(text):
    return [l.strip() for l in (text or "").splitlines() if l.strip()]


def fig_config(cwd, file_key, authored=None):
    """fig's resolved config. Where fig's reader stops, its stderr passes through and this exits
    with its code — 3 for a key written without its pair."""
    args = (["--authored", authored] if authored else []) + ([file_key] if file_key else [])
    r = run_py(FIG_RESOLVE, args, cwd)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(r.returncode)
    try:
        cfg = json.loads(r.stdout)
    except ValueError:
        sys.stderr.write("resolve-config.py printed no config\n")
        sys.exit(1)
    return cfg if isinstance(cfg, dict) else {}


def pm_lib(pm, name):
    return os.path.join(pm["root"], "_common", "scripts", "lib", name)


def pm_config(pm, cwd):
    """(pm's resolved config, None), or (None, why it could not be read). Read by pm's own reader,
    with the same --authored pair pm's skills ask for."""
    r = run_py(pm_lib(pm, "resolve-config.py"), ["--name", PM_NAME, "--authored", PM_AUTHORED], cwd)
    lines = lines_of(r.stderr)
    if r.returncode == 3 and lines:
        return None, f"pm's own config stops here, so fig does not borrow from it — {lines[0]}"
    if r.returncode == 0:
        try:
            cfg = json.loads(r.stdout)
            if isinstance(cfg, dict):
                return cfg, None
        except ValueError:
            pass
    return None, "pm's config could not be read — " + (failure(r.stderr) or f"exit {r.returncode}")


def failure(stderr):
    """The part of a reader's stderr that says why it failed. Under a traceback that is the
    exception line and every line after it — a YAML error carries the file, line and column on
    lines of their own, and the exception line alone would drop where the mistake is. Without a
    traceback, the last line."""
    raw = (stderr or "").splitlines()
    heads = [i for i, l in enumerate(raw) if l.startswith("Traceback (most recent call last)")]
    if heads:
        tail = raw[heads[-1] + 1:]
        for i, l in enumerate(tail):
            if l.strip() and not l[0].isspace():          # frames are indented; the exception is not
                return "; ".join(x.strip() for x in tail[i:] if x.strip())
    lines = lines_of(stderr)
    return lines[-1] if lines else None


def dig(cfg, dotted):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def text(v):
    """A non-empty string, stripped, or None."""
    return v.strip() if isinstance(v, str) and v.strip() else None


def word(v):
    """A config value as a lowercase word, None where it is unset."""
    return str(v).strip().lower() if v is not None and str(v).strip() else None


def old_pm(pm):
    return (f"pm {pm['version'] or '(no version)'} is installed, and fig borrows from pm {PM_MIN} "
            f"or later — update pm.")


# ---- the two decisions

def decide_task(cfg, pm, cwd):
    tt = cfg.get("task_tracker") if isinstance(cfg.get("task_tracker"), dict) else {}
    out = {"action": "print", "dir": None, "heading": text(tt.get("ui_section_heading")) or HEADING,
           "script": None, "adapter": None, "note": None}
    kind = word(tt.get("type"))
    if kind == "none":
        return out
    if kind in ("notion", "github"):
        out["action"] = kind
        return out
    if kind not in (None, "markdown"):
        out["note"] = (f"task_tracker.type {tt.get('type')} is not one fig writes to "
                       f"(markdown, notion, github or none), so the line is printed instead.")
        return out
    if pm is None:
        out["note"] = INSTALL_NOTE
        return out
    if not version_ok(pm["version"]):
        out["note"] = old_pm(pm)
        return out
    pcfg, why = pm_config(pm, cwd)
    if why:
        out["note"] = why
        return out
    record, folder = word(dig(pcfg, "task.record.type")), text(dig(pcfg, "task.record.ref"))
    own = text(tt.get("ref")) if kind == "markdown" else None
    if own:
        folder = own
    elif record != "markdown":
        out["note"] = (f"pm keeps its task records in {record or 'no tracker'}, and fig writes only "
                       f"into pm's markdown task files, so the line is printed instead.")
        return out
    elif not folder:
        out["note"] = "pm's task.record.ref names no folder, so the line is printed instead."
        return out
    script = pm_lib(pm, "markdown-tracker.py")
    r = run_py(pm_lib(pm, "adapter.py"),
               ["--name", PM_NAME, "--kind", "trackers", "--type", "markdown", "--role", "record"], cwd)
    adapter = text(r.stdout)
    if r.returncode != 0 or not adapter or not os.path.isfile(script):
        lines = lines_of(r.stderr)
        out["note"] = ("pm's markdown tracker cannot be used here — "
                       + (lines[0] if lines else f"{script} is missing") + " — so the line is printed instead.")
        return out
    theirs = text(dig(pcfg, "task.design_heading")) or HEADING
    mine = text(tt.get("ui_section_heading"))
    out.update(action="write", dir=folder, script=script, adapter=adapter, heading=theirs)
    if mine and mine != theirs:
        out["note"] = (f"The line goes under pm's heading \"{theirs}\" (task.design_heading, or \"{HEADING}\" "
                       f"where pm sets none), not under "
                       f"task_tracker.ui_section_heading \"{mine}\" — fig's heading applies to Notion "
                       f"and GitHub only.")
    return out


def decide_prd(cfg, pm, cwd):
    out = {"type": "none", "ref": None, "from": None, "split": None, "candidates": [], "note": None}
    baseline = dig(cfg, "qa.baseline")
    prd = baseline.get("prd") if isinstance(baseline, dict) else None
    if isinstance(prd, str):                       # an older config: a string is a Notion page, "" too
        prd = {"type": "notion", "ref": prd}
    if not isinstance(prd, dict):
        if prd is not None:
            out["note"] = "qa.baseline.prd is neither { type, ref } nor a page, so no PRD is read."
        return out                                 # null: this team has no PRD, and pm is not asked
    kind, ref = word(prd.get("type")), text(prd.get("ref"))
    if kind in (None, "none"):
        return out
    if not ref and kind != "markdown":
        # The config says the PRD is in notion (or elsewhere) without saying which page. pm's
        # markdown files are not that document, so they are not offered in its place.
        out.update(note=f"qa.baseline.prd names {str(prd.get('type')).strip()} but no page "
                        f"— pass the PRD's link", **{"from": "qa.baseline.prd"})
        return out
    if ref:
        if kind == "notion":
            out.update(type="notion", ref=ref, **{"from": "qa.baseline.prd"})
        elif kind == "markdown":
            out.update(type="markdown", ref=ref, **{"from": "qa.baseline.prd"})
            path = os.path.expanduser(ref.split("#", 1)[0])
            full = path if os.path.isabs(path) else os.path.join(cwd, path)
            if os.path.isdir(full):
                out["split"] = guess_split(full)
                out["candidates"] = candidates(ref, out["split"], cwd)
                if not out["candidates"]:
                    out["note"] = f"{ref} holds no PRD files yet."
            elif os.path.isfile(full):
                out["candidates"] = one_file(ref, cwd)
            else:
                out["note"] = f"{ref} does not exist here."
        else:
            out["note"] = (f"qa.baseline.prd.type {prd.get('type')} is not one fig reads "
                           f"(markdown, notion or none), so no PRD is read.")
        return out
    # type markdown and ref null: pm's PRD, where pm is installed
    if pm is None:
        out["note"] = "qa.baseline.prd names no document and pm is not installed, so there is no PRD to read."
        return out
    if not version_ok(pm["version"]):
        out["note"] = old_pm(pm)
        return out
    pcfg, why = pm_config(pm, cwd)
    if why:
        out["note"] = why
        return out
    target, folder = word(dig(pcfg, "prd.target")), text(dig(pcfg, "prd.markdown.dir"))
    if target not in ("markdown", "git"):
        out["note"] = (f"pm keeps its PRD in {target or 'no target'} — name that document in "
                       f"qa.baseline.prd for fig to read it.")
        return out
    if not folder:
        out["note"] = "pm's prd.markdown.dir names no folder, so there is no PRD to read."
        return out
    split = "domain" if word(dig(pcfg, "prd.markdown.split")) == "domain" else "product"
    out.update(type="markdown", ref=folder, split=split, candidates=candidates(folder, split, cwd),
               **{"from": "pm"})
    if not out["candidates"]:
        out["note"] = f"{folder} holds no PRD files yet."
    return out


# ---- CLI

class Parser(argparse.ArgumentParser):
    def error(self, message):              # exit 1, not argparse's 2 — 2 is not an answer here
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: {message}\n")
        sys.exit(1)


def main(argv):
    p = Parser(prog="borrow-pm.py", description="What fig borrows from pm.")
    sub = p.add_subparsers(dest="op", required=True)
    sub.add_parser("where")
    sp = sub.add_parser("prd")
    sp.add_argument("--spec-url")
    sp.add_argument("file_key", nargs="?")
    st = sub.add_parser("task")
    st.add_argument("file_key", nargs="?")
    a = p.parse_args(argv)

    env, cwd = dict(os.environ), os.getcwd()
    if a.op == "where":
        pm = find_pm(env, cwd)
        res = {"root": pm and pm["root"], "version": pm and pm["version"],
               "ok": bool(pm) and version_ok(pm["version"])}
    elif a.op == "task":
        cfg = fig_config(cwd, a.file_key, authored="task_tracker.type")
        res = decide_task(cfg, find_pm(env, cwd), cwd)
    else:
        if a.spec_url is not None:
            kind, value = spec_kind(a.spec_url, cwd)
            if kind == "figma":
                sys.stderr.write(f"{a.spec_url} is a Figma link — a design is not read as a PRD yet. "
                                 "Pass the spec as a .md file or a Notion page, or leave --spec-url out.\n")
                sys.exit(6)
            if kind == "unknown":
                sys.stderr.write(f"{a.spec_url}: cannot tell what kind of document this is — pass a .md "
                                 "file that exists here, or a Notion page url or id.\n")
                sys.exit(6)
            res = {"type": kind, "ref": value, "from": "spec_url", "split": None,
                   "candidates": one_file(value, cwd) if kind == "markdown" else [], "note": None}
        else:
            cfg = fig_config(cwd, a.file_key)
            res = decide_prd(cfg, find_pm(env, cwd), cwd)
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
