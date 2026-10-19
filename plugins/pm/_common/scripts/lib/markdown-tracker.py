#!/usr/bin/env python3
"""The markdown record store: one file per task, properties in the front matter.

    python3 markdown-tracker.py <op> ...
      slug NAME                                   stdout: the slug
      list --dir DIR                              stdout: one JSON object per record, sorted by path
      new --dir DIR --title TITLE [--set KEY=VALUE]... [--row LABEL=VALUE]... [--link-key KEY]
                                                  stdout: the new file's path
      set-link --path FILE --key KEY --value VALUE
      append-under --path FILE --heading TEXT --line TEXT
      moved --dir DIR --date YYYY-MM-DD [--today YYYY-MM-DD]
                                                  stdout: {"paths": [...], "method": ...}
    exit 0 done · 1 usage · 2 DIR exists and is not a directory · 4 FILE missing
    (set-link: or without front matter)

pm-only — not one of the byte-identical shared files. The skills used to copy inline Python from
the adapter document; one script means one place where line endings, quoting and the slug rule
are decided, and one place with tests. Stdlib plus PyYAML.
"""
import argparse, datetime, json, os, re, subprocess, sys, unicodedata
import yaml

BOM = "\ufeff"


class Parser(argparse.ArgumentParser):
    # argparse exits 2 on a usage error, but 2 means "DIR is not a directory" here.
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: {message}\n")
        sys.exit(1)


def slug(name):
    s = unicodedata.normalize("NFC", name).lower()
    s = re.sub(r'[\s/\\:*?"<>|#%]+', "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    s = s[:60].strip("-")
    return s or "untitled"


# ---- reading and writing a file without disturbing its bytes

def read_file(path):
    """(text with LF endings, uses_crlf, has_bom). Raises FileNotFoundError."""
    with open(path, "rb") as f:
        raw = f.read().decode("utf-8")
    bom = raw.startswith(BOM)
    if bom:
        raw = raw[1:]
    first = raw.split("\n", 1)[0]
    crlf = "\n" in raw and first.endswith("\r")
    return raw.replace("\r\n", "\n"), crlf, bom


def write_file(path, text, crlf, bom):
    if crlf:
        text = text.replace("\n", "\r\n")
    with open(path, "wb") as f:
        f.write(((BOM if bom else "") + text).encode("utf-8"))


def split_front_matter(text):
    """(front matter lines, rest of the text after the closing ---), or None."""
    if not text.startswith("---\n"):
        return None
    lines = text.split("\n")
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None


def yaml_scalar(value):
    """The value as written after `key: `, quoted only when a reader would change it."""
    try:
        if yaml.safe_load(f"k: {value}") == {"k": value}:
            return value
    except yaml.YAMLError:
        pass
    return json.dumps(value, ensure_ascii=False)  # a JSON string is a valid YAML double-quoted one


def not_a_dir(d):
    sys.stderr.write(f"{d} is not a directory\n")
    return 2


# ---- ops

def op_slug(a):
    print(slug(a.name))
    return 0


def op_list(a):
    if os.path.exists(a.dir) and not os.path.isdir(a.dir):
        return not_a_dir(a.dir)
    if not os.path.isdir(a.dir):
        sys.stderr.write(f"{a.dir} does not exist yet — no records\n")
        return 0
    found = []
    for root, _, files in os.walk(a.dir):
        for name in files:
            if name.endswith(".md"):
                found.append(os.path.join(root, name))
    for path in sorted(found):
        try:
            text, _, _ = read_file(path)
            fm = split_front_matter(text)
            if fm is None:
                print(json.dumps({"path": path, "error": "no front matter"}, ensure_ascii=False))
                continue
            data = yaml.safe_load("\n".join(fm[0])) or {}
            if not isinstance(data, dict):
                raise ValueError("front matter is not a mapping")
            print(json.dumps({"path": path, **data}, ensure_ascii=False, default=str))
        except (yaml.YAMLError, ValueError, UnicodeDecodeError):
            print(json.dumps({"path": path, "error": "unreadable front matter"}, ensure_ascii=False))
    return 0


def split_pair(s, flag):
    if "=" not in s:
        sys.stderr.write(f"{flag} wants KEY=VALUE, got {s!r}\n")
        sys.exit(1)
    k, v = s.split("=", 1)
    return k, v


def op_new(a):
    if os.path.exists(a.dir) and not os.path.isdir(a.dir):
        return not_a_dir(a.dir)
    sets = [split_pair(s, "--set") for s in a.set]
    rows = [split_pair(s, "--row") for s in a.row]
    os.makedirs(a.dir, exist_ok=True)
    fm = [f"title: {yaml_scalar(a.title)}"]
    fm += [f"{k}: {yaml_scalar(v)}" for k, v in sets]
    fm.append(f"{a.link_key}:")
    cell = lambda s: s.replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")
    body = ["---", *fm, "---", "", "## Context", "| | |", "|---|---|"]
    body += [f"| {cell(k)} | {cell(v)} |" for k, v in rows]
    body += ["", "## Change summary", ""]
    content = "\n".join(body)
    base, n = slug(a.title), 1
    while True:
        name = base + ("" if n == 1 else f"-{n}") + ".md"
        path = os.path.join(a.dir, name)
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as f:  # "x": never overwrite
                f.write(content)
            break
        except FileExistsError:
            n += 1
    print(path)
    return 0


def op_set_link(a):
    try:
        text, crlf, bom = read_file(a.path)
    except FileNotFoundError:
        sys.stderr.write(f"{a.path} does not exist\n")
        return 4
    fm = split_front_matter(text)
    if fm is None:
        sys.stderr.write(f"{a.path} has no front matter\n")
        return 4
    head, rest = fm
    line = f"{a.key}: {yaml_scalar(a.value)}"
    for i, l in enumerate(head):
        if l.startswith(a.key + ":"):
            head[i] = line  # the one key's line — a second key would make the file unreadable
            break
    else:
        head.append(line)
    write_file(a.path, "---\n" + "\n".join(head) + "\n---\n" + rest, crlf, bom)
    return 0


HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")


def op_append_under(a):
    try:
        text, crlf, bom = read_file(a.path)
    except FileNotFoundError:
        sys.stderr.write(f"{a.path} does not exist\n")
        return 4
    lines = text.split("\n")
    trailing = lines and lines[-1] == ""
    if trailing:
        lines.pop()
    in_fence, start, level, end = False, None, 0, len(lines)
    for i, l in enumerate(lines):
        if l.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else HEADING.match(l)
        if not m:
            continue
        if start is None:
            if m.group(2) == a.heading:
                start, level = i, len(m.group(1))
        elif len(m.group(1)) <= level:
            end = i
            break
    if start is None:
        while lines and lines[-1] == "":
            lines.pop()
        lines += ([""] if lines else []) + [f"## {a.heading}", "", a.line]
    else:
        at = end
        while at > start + 1 and lines[at - 1].strip() == "":
            at -= 1
        lines.insert(at, a.line)
    write_file(a.path, "\n".join(lines) + "\n", crlf, bom)
    return 0


def local_date(ts):
    return datetime.date.fromtimestamp(ts).isoformat()


def git_out(d, *args):
    """git in `d`. Paths print as they are: under git's default core.quotePath a non-ASCII name
    comes back quoted with octal escapes, ends in `.md"`, and drops out of the `.md` filter —
    every task with a Hangul or CJK title. No git on the machine reads as "not a work tree", so
    `moved` falls through to modification times instead of a traceback."""
    cmd = ["git", "-c", "core.quotePath=false", "-C", d, *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return subprocess.CompletedProcess(cmd, 127, "", "")


def op_moved(a):
    today = a.today or datetime.date.today().isoformat()
    if os.path.exists(a.dir) and not os.path.isdir(a.dir):
        return not_a_dir(a.dir)
    if not os.path.isdir(a.dir):
        print(json.dumps({"paths": [], "method": "none"}))
        return 0
    paths = set()
    inside = git_out(a.dir, "rev-parse", "--is-inside-work-tree")
    if inside.returncode == 0 and inside.stdout.strip() == "true":
        method = "git"
        log = git_out(a.dir, "log", f"--since={a.date} 00:00:00", f"--until={a.date} 23:59:59",
                      "--name-only", "--relative", "--format=", "--", ".")
        paths.update(p for p in log.stdout.splitlines() if p.endswith(".md"))
        if a.date == today:
            method = "git+uncommitted"
            top = git_out(a.dir, "rev-parse", "--show-toplevel").stdout.strip()
            st = git_out(a.dir, "status", "--porcelain", "-z", "--untracked-files=all", "--", ".")
            entries, skip = st.stdout.split("\0"), False
            for e in entries:
                if skip:  # a rename or copy lists its origin as a second entry
                    skip = False
                    continue
                if len(e) < 4:
                    continue
                skip = e[0] in "RC" or e[1] in "RC"
                full = os.path.join(top, e[3:])
                if full.endswith(".md") and os.path.isfile(full) and local_date(os.path.getmtime(full)) == a.date:
                    paths.add(os.path.relpath(full, os.path.realpath(a.dir)))
        out = sorted(os.path.join(a.dir, p) for p in paths)
    else:
        method = "mtime"
        for root, _, files in os.walk(a.dir):
            for name in files:
                p = os.path.join(root, name)
                if name.endswith(".md") and local_date(os.path.getmtime(p)) == a.date:
                    paths.add(p)
        out = sorted(paths)
    print(json.dumps({"paths": out, "method": method}, ensure_ascii=False))
    return 0


def main(argv):
    p = Parser(prog="markdown-tracker.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="op", required=True, parser_class=Parser)
    s = sub.add_parser("slug"); s.add_argument("name"); s.set_defaults(fn=op_slug)
    s = sub.add_parser("list"); s.add_argument("--dir", required=True); s.set_defaults(fn=op_list)
    s = sub.add_parser("new")
    s.add_argument("--dir", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--set", action="append", default=[])
    s.add_argument("--row", action="append", default=[])
    s.add_argument("--link-key", default="ticket")
    s.set_defaults(fn=op_new)
    s = sub.add_parser("set-link")
    for f in ("--path", "--key", "--value"):
        s.add_argument(f, required=True)
    s.set_defaults(fn=op_set_link)
    s = sub.add_parser("append-under")
    for f in ("--path", "--heading", "--line"):
        s.add_argument(f, required=True)
    s.set_defaults(fn=op_append_under)
    s = sub.add_parser("moved")
    s.add_argument("--dir", required=True)
    s.add_argument("--date", required=True)
    s.add_argument("--today")
    s.set_defaults(fn=op_moved)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
