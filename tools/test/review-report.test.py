#!/usr/bin/env python3
"""Fixtures for review-report.py — the /pm:review report renderer.

    python3 tools/test/review-report.test.py

Every case writes a DATA.json into a temp dir and runs the script as a subprocess.
"""
import base64, json, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "pm" / "_common" / "scripts" / "lib" / "review-report.py"
failures = []
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def item(**kw):
    base = {"kind": "fix", "area": "Tickets", "title": "No ticket covers the server work",
            "problem": "Saving the form needs a server change. No child ticket names it.",
            "if_left": "The screen ships and saves nothing.",
            "evidence": [{"kind": "ticket", "source": "Store setup (#12)", "link": "https://example.com/12",
                          "quote": "Children: screen only"}],
            "ask": "Open a server ticket under the parent before handover."}
    base.update(kw)
    return base


def run(data, *args, fmt="html", lang="en"):
    d = Path(tempfile.mkdtemp())
    (d / "shot.png").write_bytes(PNG)
    (d / "data.json").write_text(json.dumps(data), encoding="utf-8")
    out = d / ("report.html" if fmt == "html" else "report.md")
    r = subprocess.run([sys.executable, str(SCRIPT), str(d / "data.json"), "--out", str(out),
                        "--lang", lang, "--format", fmt, *args], capture_output=True, text=True)
    return r, out


def doc(**kw):
    base = {"title": "Store setup", "plan": "Dana", "as_of": "2026-01-05 10:00", "items": [item()]}
    base.update(kw)
    return base


# A clean report: exit 0, the four cells, the verdict counted from the items
r, out = run(doc(items=[item(), item(kind="opinion", title="Confirm button wording")], surfaces_last=1))
page = out.read_text() if out.exists() else ""
check("clean data exits 0", r.returncode == 0, r.stderr)
check("verdict counts the items", "1 fix, 1 opinion" in page)
check("verdict names the item that surfaces last", "Surfaces last if nobody acts: 1, No ticket covers" in page)
check("every card has the four cells", all(page.count(f"<dt>{c}</dt>") == 2 for c in ("Problem", "If left", "Evidence", "Ask")))
check("items table links to the cards", 'href="#i2"' in page and 'id="i2"' in page)
check("summary line on stdout", "items 2 (fix 1, opinion 1), over budget 0" in r.stdout)

# Own plan: the verdict is about handing over
r, out = run(doc(plan="own", items=[]))
check("own plan with nothing raised is ready", r.returncode == 0 and "Ready to hand over" in out.read_text())
r, out = run(doc(plan="own"))
check("own plan with one fix", "1 fix before handover" in out.read_text())

# Budgets: written anyway, exit 1, each overflow named
r, out = run(doc(items=[item(problem="x" * 400, ask="One. Two.")]))
check("over budget exits 1 and still writes", r.returncode == 1 and out.exists())
check("length overflow is named", "item 1 problem: 400 characters, budget 300" in r.stderr, r.stderr)
check("sentence overflow is named", "item 1 ask: 2 sentences, budget 1" in r.stderr, r.stderr)

r, _ = run(doc(items=[item(problem="The list drops the row — nobody asked for that.")]))
check("a dash aside in prose is flagged", r.returncode == 1 and "dash sets off an aside" in r.stderr, r.stderr)
r, _ = run(doc(items=[item(problem='The ticket "Server — sync" is closed.')]))
check("a dash inside a quotation is not flagged", r.returncode == 0, r.stderr)
r, _ = run(doc(items=[item(problem="Register · edit · delete have no ticket.")]))
check("a list strung on middle dots is flagged", "strung on ' · '" in r.stderr, r.stderr)
r, _ = run(doc(items=[item(problem="Save → refresh loses the row.")]))
check("an arrow in a sentence is flagged", "arrow inside a sentence" in r.stderr, r.stderr)

ev = {"kind": "spec", "source": "Entry", "quote": "q"}
r, _ = run(doc(items=[item(evidence=[ev, ev, ev])]))
check("a third piece of evidence on the card is flagged", "3 on the card, budget 2" in r.stderr, r.stderr)
r, out = run(doc(items=[item(evidence=[ev], more=[ev, ev, {"note": "guess", "inferred": True},
                                                     {"table": {"head": ["a"], "rows": [["b"]]}}])]))
check("more holds anything and is folded", r.returncode == 0 and "More evidence (4)" in out.read_text(), r.stderr)

# Dense scripts get the base budget, others twice it
r, _ = run(doc(items=[item(problem="가" * 200)]), lang="ko")
check("Korean budget is the base", "200 characters, budget 150" in r.stderr, r.stderr)
r, out = run(doc(), lang="ko")
check("Korean labels", "<dt>안 고치면</dt>" in out.read_text() and "고칠 것 1건, 의견 0건" in out.read_text())
r, out = run(doc(), lang="xx")
check("unknown language falls back to English", r.returncode == 0 and "<dt>Problem</dt>" in out.read_text()
      and "no labels for 'xx'" in r.stderr)

# Evidence-needed, escaping, unsafe links
r, out = run(doc(items=[item(evidence=[], title="<script>x</script>")]))
page = out.read_text()
check("an item with no evidence is marked", "evidence needed" in page)
check("text is escaped", "<script>x" not in page and "&lt;script&gt;" in page)
r, out = run(doc(items=[item(evidence=[{"kind": "chat", "source": "Thread", "link": "javascript:alert(1)"}])]))
check("a non-http link is not linked", "javascript:" not in out.read_text())

# Captures: embedded in html, copied beside markdown
r, out = run(doc(items=[item(evidence=[{"kind": "design", "source": "Frame 1:2", "image": "shot.png"}])]))
check("html embeds the capture", "data:image/png;base64," in out.read_text())
r, out = run(doc(items=[item(evidence=[{"kind": "design", "source": "Frame 1:2", "image": "shot.png"}])]), fmt="markdown")
md = out.read_text()
check("markdown links the copied capture", "](report/shot.png)" in md and (out.parent / "report" / "shot.png").is_file(), md)
check("markdown has the four cells", all(f"**{c}**" in md for c in ("Problem", "If left", "Evidence", "Ask")))

# Ticket numbers: named in a cell, linked on the page
r, _ = run(doc(items=[item(ask="Open a ticket under #12 before handover.")]))
check("a ticket number standing alone is flagged", "ticket number standing alone" in r.stderr, r.stderr)
r, out = run(doc(ticket_url="https://example.com/issues/{n}",
                 items=[item(ask="Open a ticket under the store setup epic (#12).")]))
page = out.read_text()
check("a named ticket with its number in brackets passes", r.returncode == 0, r.stderr)
check("ticket numbers link through ticket_url", '<a href="https://example.com/issues/12">#12</a>' in page)
r, out = run(doc(ticket_url="https://example.com/issues/{n}", items=[item(
    evidence=[{"kind": "code", "source": "a.css:1", "quote": "color: #123456;"}])]))
check("numbers inside code are not linked", "issues/123456" not in out.read_text())
r, out = run(doc(ticket_url="https://example.com/issues/{n}",
                 items=[item(ask="Open a ticket under the store setup epic (#12).")]), fmt="markdown")
check("markdown links ticket numbers too", "[#12](https://example.com/issues/12)" in out.read_text())

# A full stop after a digit does not end a sentence
r, _ = run(doc(items=[item(ask="Link section 05. Maintenance under the parent.")]))
check("a numbered heading is not a second sentence", "sentences" not in r.stderr, r.stderr)

# --help carries the data shape
h = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
check("--help prints the shape of DATA.json", h.returncode == 0 and "surfaces_last" in h.stdout and "inferred" in h.stdout)
check("--help prints the budgets in numbers", "problem 150" in h.stdout and "problem 2" in h.stdout)

# The brief: the plan before the findings
BRIEF = {"what": "Head office registers and edits stores in one screen.", "why": "Store settings are hard-coded today.",
         "flow": ["Register a store", "Set its status", "Save the kiosk setup"], "in": ["registration"], "out": ["the app list"],
         "links": [{"name": "Spec", "link": "https://example.com/spec"}],
         "capture": {"source": "Store list", "image": "shot.png"}}
r, out = run(doc(brief=BRIEF))
page = out.read_text()
check("a brief renders", r.returncode == 0 and "<h2>The plan</h2>" in page and "<dt>How it works</dt>" in page, r.stderr)
check("the brief comes before the verdict", page.index("The plan") < page.index('class="verdict'))
check("the brief carries its capture", page.count("data:image/png;base64,") == 1)
r, _ = run(doc(brief=dict(BRIEF, flow=[f"step {k}" for k in range(8)])))
check("a flow over six steps is flagged", "brief flow: 8 lines, budget 6" in r.stderr, r.stderr)
r, _ = run(doc(brief=dict(BRIEF, what="It registers stores. It edits them.")))
check("a two-sentence what is flagged", "brief brief_what: 2 sentences" in r.stderr, r.stderr)
r, out = run(doc(brief=BRIEF), fmt="markdown")
md = out.read_text()
check("markdown brief before the verdict", md.index("## The plan") < md.index("> **") and "  2. Set its status" in md)

# Bad data: exit 2, nothing written
for label, data in (("items missing", {"title": "t", "as_of": "now"}),
                    ("brief without flow", doc(brief={"what": "x"})),
                    ("brief without what", doc(brief={"flow": ["a"]})),
                    ("more entry without a kind", doc(items=[item(more=[{"source": "x"}])])),
                    ("more table with a row that is not a list", doc(items=[item(more=[{"table": {"head": ["a"], "rows": ["b"]}}])])),
                    ("left_out without a reason", doc(left_out=[{"what": "x"}])),
                    ("not_checked that is not a list of sentences", doc(not_checked="x")),
                    ("ticket_url without {n}", doc(ticket_url="https://example.com/issues/")),
                    ("unknown kind", doc(items=[item(kind="nit")])),
                    ("missing ask", doc(items=[item(ask="")])),
                    ("unknown evidence kind", doc(items=[item(evidence=[{"kind": "rumour"}])])),
                    ("surfaces_last out of range", doc(surfaces_last=5)),
                    ("missing capture", doc(items=[item(evidence=[{"kind": "design", "image": "nope.png"}])]))):
    r, out = run(data)
    check(f"bad data exits 2: {label}", r.returncode == 2 and not out.exists(), r.stderr)

print()
if failures:
    print(f"{len(failures)} failed")
    sys.exit(1)
print("all passed")
