#!/usr/bin/env python3
"""Fixtures for markdown-tracker.py — the pm plugin's markdown record store, one op per case.

    python3 tools/test/markdown-tracker.test.py

Every case runs the script as a subprocess in a temp dir. The git cases pin author and committer
dates, since "what moved on a day" is read from commit dates.
"""
import datetime, json, os, site, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "pm" / "_common" / "scripts" / "lib" / "markdown-tracker.py"
failures = []


def clean_env(**extra):
    # Inside a git hook, GIT_DIR and friends point at the real repository; a child git would then
    # act on it instead of the temp dir. Drop every GIT_* key, then add only the case's own.
    base = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return dict(base, **extra)


def run(cwd, *args, env=None):
    env = clean_env(PYTHONUSERBASE=site.getuserbase(), **(env or {}))
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, env=env,
                          capture_output=True, text=True)


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def git(cwd, *args, date=None):
    # Global/system config is blanked so a developer's hooks or signing settings cannot leak in.
    env = clean_env(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{date}T12:00:00"
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True)


def lone_lf(data):
    """True when every LF in `data` is part of a CRLF."""
    return data.replace(b"\r\n", b"").count(b"\n") == 0


def parse(r):
    return json.loads(r.stdout) if r.stdout.strip() else {}


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    r = run(tmp, "slug", "通知 設定 / v2")
    check("slug keeps non-Latin letters", r.returncode == 0 and r.stdout.strip() == "通知-設定-v2", r.stdout + r.stderr)
    r = run(tmp, "slug", "::")
    check("slug of punctuation only", r.stdout.strip() == "untitled", r.stdout + r.stderr)
    r = run(tmp, "slug", "  A" + "b" * 80 + "  ")
    check("slug cuts at 60", r.stdout.strip() == "a" + "b" * 59, r.stdout)

    # --- new / list
    new_args = ["new", "--dir", "t", "--title", "Push settings", "--set", "project=App",
                "--row", "Request source=https://x"]
    r = run(tmp, *new_args)
    check("new on a missing dir creates it",
          r.returncode == 0 and r.stdout.strip() == "t/push-settings.md" and (tmp / "t/push-settings.md").is_file(),
          r.stdout + r.stderr)
    f1 = tmp / "t/push-settings.md"
    first = f1.read_text(encoding="utf-8") if f1.exists() else ""
    lines = first.split("\n")
    i = lines.index("## Context") if "## Context" in lines else -1
    fm_end = lines.index("---", 1) if lines and lines[0] == "---" else -1
    check("new writes a header row",
          i >= 0 and lines[i + 1:i + 3] == ["| | |", "|---|---|"] and fm_end > 0 and lines[fm_end - 1] == "ticket:",
          first)
    check("new writes rows then the summary heading",
          "| Request source | https://x |\n\n## Change summary\n" in first, first)
    r = run(tmp, *new_args)
    check("new twice with one title → -2",
          r.stdout.strip() == "t/push-settings-2.md" and f1.read_text(encoding="utf-8") == first,
          r.stdout + r.stderr)
    run(tmp, "new", "--dir", "t", "--title", "Billing: refunds")
    r = run(tmp, "list", "--dir", "t")
    recs = [json.loads(x) for x in r.stdout.splitlines() if x.strip()]
    check("title with \": \" round-trips through list",
          any(x.get("title") == "Billing: refunds" for x in recs), r.stdout + r.stderr)
    check("list is sorted by path", [x["path"] for x in recs] == sorted(x["path"] for x in recs))
    r = run(tmp, "new", "--dir", "t", "--title", "Pipes", "--row", "A|B=x|y\nz")
    check("new escapes a pipe and a newline in a row",
          "| A\\|B | x\\|y<br>z |" in (tmp / "t/pipes.md").read_text(encoding="utf-8"), r.stderr)
    r = run(tmp, "list", "--dir", "nope")
    check("list on a missing dir", r.returncode == 0 and r.stdout == "" and "does not exist yet" in r.stderr, r.stderr)
    (tmp / "f").write_text("")
    r = run(tmp, "list", "--dir", "f")
    check("list on a file → exit 2", r.returncode == 2 and "is not a directory" in r.stderr, f"rc={r.returncode} {r.stderr}")
    r = run(tmp, "new", "--dir", "f", "--title", "X")
    check("new on a file → exit 2", r.returncode == 2, f"rc={r.returncode}")

    # --- set-link
    rec = "t/push-settings.md"
    run(tmp, "set-link", "--path", rec, "--key", "ticket", "--value", "u1")
    r = run(tmp, "set-link", "--path", rec, "--key", "ticket", "--value", "u2")
    keys = [x for x in (tmp / rec).read_text(encoding="utf-8").splitlines() if x.startswith("ticket:")]
    check("set-link twice → one key", r.returncode == 0 and keys == ["ticket: u2"], str(keys))
    crlf = tmp / "crlf.md"
    crlf.write_bytes(b"---\r\ntitle: A\r\nticket:\r\n---\r\n\r\n## Change summary\r\n- old\r\n")
    run(tmp, "set-link", "--path", "crlf.md", "--key", "ticket", "--value", "u3")
    data = crlf.read_bytes()
    check("set-link on CRLF keeps CRLF", lone_lf(data) and b"ticket: u3\r\n" in data, repr(data))
    bom = tmp / "bom.md"
    bom.write_bytes(b"\xef\xbb\xbf---\ntitle: A\n---\nbody\n")
    run(tmp, "set-link", "--path", "bom.md", "--key", "ticket", "--value", "u4")
    check("set-link keeps a BOM and adds a missing key",
          bom.read_bytes() == b"\xef\xbb\xbf---\ntitle: A\nticket: u4\n---\nbody\n", repr(bom.read_bytes()))
    (tmp / "plain.md").write_text("# no front matter\n")
    r = run(tmp, "set-link", "--path", "plain.md", "--key", "ticket", "--value", "u")
    check("set-link without front matter → exit 4", r.returncode == 4, f"rc={r.returncode}")
    r = run(tmp, "set-link", "--path", "gone.md", "--key", "ticket", "--value", "u")
    check("set-link on a missing file → exit 4", r.returncode == 4, f"rc={r.returncode}")

    # --- append-under
    run(tmp, "append-under", "--path", rec, "--heading", "Design changes", "--line", "A")
    r = run(tmp, "append-under", "--path", rec, "--heading", "Design changes", "--line", "B")
    txt = (tmp / rec).read_text(encoding="utf-8")
    check("append-under twice → one heading, two lines",
          r.returncode == 0 and txt.count("## Design changes") == 1 and txt.rstrip("\n").endswith("## Design changes\n\nA\nB"),
          txt)
    sec = tmp / "sec.md"
    sec.write_text("## Change summary\n- old\n## Notes\n")
    run(tmp, "append-under", "--path", "sec.md", "--heading", "Change summary", "--line", "- new")
    check("append-under stops before the next heading",
          sec.read_text() == "## Change summary\n- old\n- new\n## Notes\n", sec.read_text())
    blank = tmp / "blank.md"
    blank.write_text("## Change summary\n- old\n\n## Notes\n")
    run(tmp, "append-under", "--path", "blank.md", "--heading", "Change summary", "--line", "- new")
    check("append-under keeps the blank line before the next heading",
          blank.read_text() == "## Change summary\n- old\n- new\n\n## Notes\n", blank.read_text())
    crlf.write_bytes(b"---\r\ntitle: A\r\n---\r\n\r\n## Change summary\r\n- old\r\n")
    run(tmp, "append-under", "--path", "crlf.md", "--heading", "Change summary", "--line", "- new")
    data = crlf.read_bytes()
    check("append-under on CRLF keeps CRLF", lone_lf(data) and data.endswith(b"- old\r\n- new\r\n"), repr(data))
    r = run(tmp, "append-under", "--path", "gone.md", "--heading", "X", "--line", "y")
    check("append-under on a missing file → exit 4", r.returncode == 4, f"rc={r.returncode}")
    r = run(tmp, "frobnicate")
    check("unknown op → exit 1", r.returncode == 1, f"rc={r.returncode}")

    # --- moved
    D, D2 = "2026-03-10", "2026-03-11"
    mt = datetime.datetime(2026, 3, 10, 15, 0).timestamp()
    repo = tmp / "repo"
    (repo / "t").mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "t/a.md").write_text("a\n")
    (repo / "t/b.md").write_text("b\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "init", date="2026-03-01")
    (repo / "t/a.md").write_text("a2\n")
    git(repo, "commit", "-q", "-am", "edit a", date=D)
    (repo / "t/b.md").write_text("b2\n")
    os.utime(repo / "t/b.md", (mt, mt))
    out = parse(run(repo, "moved", "--dir", "t", "--date", D, "--today", D))
    check("moved counts an uncommitted edit today",
          set(out.get("paths", [])) == {"t/a.md", "t/b.md"} and out.get("method") == "git+uncommitted", str(out))
    out = parse(run(repo, "moved", "--dir", "t", "--date", D, "--today", D2))
    check("moved on a past date is commits only",
          out.get("paths") == ["t/a.md"] and out.get("method") == "git", str(out))
    # A non-Latin file name, which slug keeps. git quotes such a path by default (core.quotePath),
    # so it prints as "t/\354...md" and ends in `.md"`. The developer's own git config is blanked
    # and the default forced, so a machine that already switched quotePath off cannot hide this.
    uni = tmp / "unirepo"
    (uni / "t").mkdir(parents=True)
    git(uni, "init", "-q")
    git(uni, "config", "user.email", "t@example.com")
    git(uni, "config", "user.name", "t")
    (uni / "t/알림-설정.md").write_text("a\n", encoding="utf-8")
    git(uni, "add", ".")
    git(uni, "commit", "-q", "-m", "add", date=D)
    quoted = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "GIT_CONFIG_COUNT": "1",
              "GIT_CONFIG_KEY_0": "core.quotePath", "GIT_CONFIG_VALUE_0": "true"}
    out = parse(run(uni, "moved", "--dir", "t", "--date", D, "--today", D2, env=quoted))
    check("moved keeps a committed non-Latin file name",
          out.get("paths") == ["t/알림-설정.md"] and out.get("method") == "git", str(out))
    # No git on PATH: outside git the answer is modification times (trackers/markdown.md), never
    # a traceback.
    # The script runs by absolute path; PATH holds python3 and nothing else.
    nogit = tmp / "nogit-bin"
    nogit.mkdir()
    os.symlink(sys.executable, nogit / "python3")
    r = run(repo, "moved", "--dir", "t", "--date", D, "--today", D2, env={"PATH": str(nogit)})
    out = parse(r) if r.returncode == 0 else {}
    check("moved with no git on PATH → mtime",
          r.returncode == 0 and "Traceback" not in r.stderr and out.get("method") == "mtime"
          and out.get("paths") == ["t/b.md"], f"rc={r.returncode} {r.stdout}{r.stderr}")
    plain = tmp / "plainrepo"
    (plain / "t").mkdir(parents=True)
    (plain / "t/x.md").write_text("x\n")
    os.utime(plain / "t/x.md", (mt, mt))
    out = parse(run(plain, "moved", "--dir", "t", "--date", D))
    check("moved without git → mtime", out.get("method") == "mtime" and out.get("paths") == ["t/x.md"], str(out))
    r = run(plain, "moved", "--dir", "none", "--date", D)
    check("moved on a missing dir → [] and none",
          r.returncode == 0 and parse(r) == {"paths": [], "method": "none"}, r.stdout + r.stderr)

print()
print("FAILED: " + ", ".join(failures) if failures else "all passed")
sys.exit(1 if failures else 0)
