#!/usr/bin/env python3
"""Fixtures for review-report.py — the /pm:review report renderer.

    python3 tools/test/review-report.test.py

Every case writes a DATA.json into a temp dir and runs the script as a subprocess. What only a browser
can show (the carousel, the viewer) is checked by hand; these cases hold the data, the budgets and
the page's structure.
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
    base = {"kind": "fix", "area": "Tickets", "title": "Who builds the server side",
            "recommend": "Open a server ticket",
            "problem": "Saving the form needs a server change. No child ticket names it.",
            "ask": "Open a server ticket under the parent before handover.",
            "reason": "The screen cannot save without it.",
            "if_left": "The screen ships and saves nothing.",
            "evidence": [{"kind": "ticket", "source": "Store setup (#12)", "link": "https://example.com/12",
                          "quote": "Children: screen only"}],
            "owner": "Planning", "then": "Add the ticket under the parent"}
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


ev = {"kind": "spec", "source": "Entry", "quote": "q"}
SHOT = {"kind": "design", "source": "Dialog (1:2)", "image": "shot.png", "marks": [{"box": [0.1, 0.2, 0.3, 0.1]}]}
BRIEF = {"what": "Head office registers and edits stores in one screen.", "why": "Store settings are hard-coded today.",
         "flow": [{"label": "Register", "text": "Register a store", "image": "shot.png", "link": "https://example.com/f1"},
                  {"label": "Status", "text": "Set its status"},
                  {"label": "Kiosk", "text": "Save the kiosk setup", "image": "shot.png", "crop": [0, 0, 0.5, 0.5]}],
         "changes": [{"what": "Store list", "now": "No hidden tag", "after": "Hidden stores tagged"}],
         "in": ["registration"], "out": ["the app list"], "in_label": "December",
         "work": {"summary": "Front end 1, server 1.", "items": [{"name": "Server (#3)", "owner": "Lee", "status": "open"}]},
         "decided": [{"what": "Two tabs", "when": "10-27", "link": "https://example.com/d"}],
         "waiting": ["Server's answer on numbering"],
         "links": [{"name": "Spec", "link": "https://example.com/spec"}]}

# A clean report: exit 0, the verdict counted, the decisions as a table, one card each
r, out = run(doc(items=[item(), item(kind="opinion", title="Button wording", options=["Keep it"])], surfaces_last=1))
page = out.read_text() if out.exists() else ""
check("clean data exits 0", r.returncode == 0, r.stderr)
check("a colleague's verdict recommends against handover while decisions are open", "Not ready yet: 1 decision to make, 1 opinion" in page)
check("verdict names the item that surfaces last", "Surfaces last if nobody decides: 1, Who builds the server side" in page)
check("the decisions are a table, a row per decision", page.count('<tr data-href="#i') == 2 and "<th>Decision</th>" in page)
check("each row shows the recommended decision and its other options",
      "<td>Open a server ticket</td>" in page and '<td class="c">none</td>' in page and '<td class="c">1</td>' in page)
check("an opinion is tagged in the decisions table", 'tag opinion">Opinion</span></td>' in page)
check("the answer line tells a colleague's reviewer how to answer", "reply to the author is drafted" in page)
check("every card's cells are a two-column table", page.count('<table class="kv">') == 2
      and all(page.count(f"<tr><th>{c}</th>") == 2 for c in ("Problem", "Recommended", "If undecided", "Evidence", "Then")))
check("the reason rides under the recommendation", "Why: The screen cannot save without it." in page)
check("summary line on stdout", "items 2 (fix 1, opinion 1), over budget 0" in r.stdout)

# Own plan: the verdict is about handing over
r, out = run(doc(plan="own", items=[]))
check("own plan with nothing raised is ready", r.returncode == 0 and "Ready to hand over" in out.read_text())
r, out = run(doc(plan="own"))
page = out.read_text()
check("own plan with one fix", "1 decision before handover" in page and "the fixes follow from it" in page)
r, out = run(doc(items=[item(kind="opinion")]))
check("a colleague's plan with no fixes is ready", "Ready to hand over, 1 opinion" in out.read_text())

# The brief: a table, the flow as a carousel, the parts a decision rests on
r, out = run(doc(brief=BRIEF))
page = out.read_text()
check("a brief renders as a table before the verdict", r.returncode == 0 and page.index("The plan") < page.index('class="verdict')
      and page.index('<table class="kv">') < page.index('class="verdict'), r.stderr)
check("the flow is a carousel with a button per step", 'data-car' in page and page.count('data-go="') == 3
      and page.count('class="slide"') == 3)
check("each screen in the carousel opens large in the page", page.count('class="sbtn" data-zoomit') == 2 and "open in the design tool" in page)
check("a step without a screen still has its slide", '<figure class="slide" data-i="1"><figcaption>' in page)
check("what changes is a table of now and after", "<th>Now</th><th>After</th>" in page and "Hidden stores tagged" in page)
check("scope uses the given label", ">December<" in page and ">Not this round<" in page)
check("who builds it folds its tickets", "1 tickets</summary>" in page and "<td>Lee</td>" in page)
check("decided and waiting are listed", "Two tabs" in page and "Server&#x27;s answer on numbering" in page)
check("the viewer and its script ship once", page.count('id="viewer"') == 1 and page.count("[data-car]") == 1)
r, _ = run(doc(brief=dict(BRIEF, flow=[{"label": f"s{k}", "text": f"step {k}"} for k in range(8)])))
check("a flow over six steps is flagged", "brief flow: 8 lines, budget 6" in r.stderr, r.stderr)
r, _ = run(doc(brief=dict(BRIEF, what="It registers stores. It edits them.")))
check("a two-sentence what is flagged", "brief brief_what: 2 sentences" in r.stderr, r.stderr)
r, _ = run(doc(brief=dict(BRIEF, changes=[{"what": "x", "now": "y" * 100, "after": "z"}])))
check("a long change cell is flagged", "brief changes change: 100 characters, budget 80" in r.stderr, r.stderr)
r, out = run(doc(brief=BRIEF), fmt="markdown")
md = out.read_text()
check("markdown brief before the verdict", md.index("## The plan") < md.index("> **") and "Register › Status › Kiosk" in md)

# Budgets: written anyway, exit 1, each overflow named
r, out = run(doc(items=[item(problem="x" * 400, ask="One. Two.")]))
check("over budget exits 1 and still writes", r.returncode == 1 and out.exists())
check("length overflow is named", "item 1 problem: 400 characters, budget 300" in r.stderr, r.stderr)
check("sentence overflow is named", "item 1 ask: 2 sentences, budget 1" in r.stderr, r.stderr)
r, _ = run(doc(items=[item(recommend="r" * 120)]))
check("a long recommendation is flagged", "item 1 recommend: 120 characters, budget 100" in r.stderr, r.stderr)
r, _ = run(doc(items=[item(problem="The list drops the row — nobody asked for that.")]))
check("a dash aside in prose is flagged", r.returncode == 1 and "dash sets off an aside" in r.stderr, r.stderr)
r, _ = run(doc(items=[item(problem='The ticket "Server — sync" is closed.')]))
check("a dash inside a quotation is not flagged", r.returncode == 0, r.stderr)
r, _ = run(doc(items=[item(problem="Register · edit · delete have no ticket.")]))
check("a list strung on middle dots is flagged", "strung on ' · '" in r.stderr, r.stderr)
r, _ = run(doc(items=[item(problem="Save → refresh loses the row.")]))
check("an arrow in a sentence is flagged", "arrow inside a sentence" in r.stderr, r.stderr)
r, _ = run(doc(items=[item(evidence=[ev, ev, ev])]))
check("a third piece of evidence on the card is flagged", "3 on the card, budget 2" in r.stderr, r.stderr)
r, out = run(doc(items=[item(evidence=[ev], more=[ev, ev, {"note": "guess", "inferred": True},
                                                     {"table": {"head": ["a"], "rows": [["b"]]}}])]))
check("more holds anything and is folded", r.returncode == 0 and "More evidence (4)" in out.read_text(), r.stderr)
r, _ = run(doc(items=[item(paste={"to": "Spec, rules", "text": "Saved values follow the last save."}, options=["a", "b"])]))
check("a paste beside options is flagged", "paste beside options decides for the author" in r.stderr, r.stderr)
r, out = run(doc(items=[item(paste={"to": "Spec, rules", "text": "Saved values follow the last save."})]))
check("a paste renders under the recommendation", r.returncode == 0 and 'class="paste">Saved values follow the last save.' in out.read_text(), r.stderr)

# Dense scripts get the base budget, others twice it
r, _ = run(doc(items=[item(problem="가" * 200)]), lang="ko")
check("Korean budget is the base", "200 characters, budget 150" in r.stderr, r.stderr)
r, out = run(doc(), lang="ko")
page = out.read_text()
check("Korean labels", "<th>안 정하면</th>" in page and "아직 넘기지 않기를 권합니다. 정하실 것 1건" in page and "<th>결정할 것</th>" in page)
r, out = run(doc(), lang="xx")
check("unknown language falls back to English", r.returncode == 0 and "<th>Problem</th>" in out.read_text()
      and "no labels for 'xx'" in r.stderr)

# Evidence-needed, escaping, unsafe links
r, out = run(doc(items=[item(evidence=[], title="<script>x</script>")]))
page = out.read_text()
check("an item with no evidence is marked", "evidence needed" in page)
check("text is escaped", "<script>x" not in page and "&lt;script&gt;" in page)
r, out = run(doc(items=[item(evidence=[{"kind": "chat", "source": "Thread", "link": "javascript:alert(1)"}])]))
check("a non-http link is not linked", "javascript:alert" not in out.read_text())

# Captures: marked, cropped, above the cells, zoomable; copied beside markdown
r, out = run(doc(items=[item(evidence=[SHOT, ev])]))
page = out.read_text()
check("a mark is drawn on its capture", 'class="mk" style="left:10.00%;top:20.00%;width:30.00%;height:10.00%"><b>1</b>' in page, r.stderr)
check("the capture sits above the cells", page.index('class="shot"') < page.index("<th>Problem</th>"))
check("the capture opens large with its marks", 'data-marks="0.1,0.2,0.3,0.1"' in page and "data-zoom" in page)
r, out = run(doc(items=[item(evidence=[dict(SHOT, crop=[0.0, 0.1, 0.5, 0.5])])]))
page = out.read_text()
check("a crop shows part of the capture and moves the marks with it",
      'class="frame crop"' in page and 'class="mk" style="left:20.00%;top:20.00%;width:60.00%;height:20.00%"' in page, r.stderr)
r, out = run(doc(items=[item(evidence=[SHOT])]), fmt="markdown")
md = out.read_text()
check("markdown links the copied capture and says the marks are in the html",
      "](report/shot.png)" in md and (out.parent / "report" / "shot.png").is_file() and "(marked in the HTML report)" in md, md)

# Ticket numbers: named in a cell, linked on the page
r, _ = run(doc(items=[item(ask="Open a ticket under #12 before handover.")]))
check("a ticket number standing alone is flagged", "ticket number standing alone" in r.stderr, r.stderr)
r, out = run(doc(ticket_url="https://example.com/issues/{n}", items=[item(ask="Open a ticket under the store setup epic (#12).")]))
page = out.read_text()
check("a named ticket with its number in brackets passes", r.returncode == 0, r.stderr)
check("ticket numbers link through ticket_url", '<a href="https://example.com/issues/12">#12</a>' in page)
r, out = run(doc(ticket_url="https://example.com/issues/{n}", items=[item(
    evidence=[{"kind": "code", "source": "a.css:1", "quote": "color: #123456;"}])]))
check("numbers inside code are not linked", "issues/123456" not in out.read_text())

# The rest of the page: open items, the notes folded, empty sections dropped
r, out = run(doc(not_checked=["the kiosk repo"], unread=["a DM"], before_handover=["Spec rows still in draft."],
                 reviewer="Reviewer A", latest={"name": "Parent ticket", "at": "10:00"}, left_out=[{"what": "x", "why": "y"}],
                 previous={"date": "01-02", "items": [{"title": "No server ticket", "status": "resolved", "note": "Opened."},
                                                      {"title": "Who cancelled", "status": "withdrawn", "note": "Withdrawn."}]}))
page = out.read_text()
check("the verdict carries its grounds and the last review", "Grounds: 1 not checked, 1 sources unread" in page
      and "Since the last review (01-02): resolved 1, withdrawn 1, still open 0" in page)
check("open holds before handover and not checked", page.index("<h2>Open</h2>") < page.index("Before handover") < page.index('id="nc"'))
check("unread sources are listed under not checked", page.index('id="nc"') < page.index("Could not read: a DM"))
check("notes fold the earlier review, left out and the foot", page.index("<h2>Notes</h2>") < page.index('id="prev"')
      and "Left out (1)" in page and page.index("Reviewed by") > page.index("<h2>Notes</h2>"))
r, out = run(doc())
page = out.read_text()
check("empty sections are not drawn", "Left out" not in page and "Grounds:" not in page and "<h2>Open</h2>" not in page)
r, out = run(doc(items=[item(where=[{"name": "Spec, store setup, rules", "link": "https://example.com/s"}])]))
check("a card opens with where the fix goes", 'class="where">Where:' in out.read_text())
r, _ = run(doc(items=[item(where=[{"name": "a"}, {"name": "b"}, {"name": "c"}])]))
check("more than two locations is flagged", "item 1 where: 3, budget 2" in r.stderr, r.stderr)
r, out = run(doc(items=[item(looked=["searched the tracker", "read the parent"])]))
check("where-I-looked may be a list", "<li>read the parent</li>" in out.read_text(), r.stderr)

# --help carries the data shape
h = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
check("--help prints the shape of DATA.json", h.returncode == 0 and "recommend" in h.stdout and "decided" in h.stdout)
check("--help prints the budgets in numbers", "problem 150" in h.stdout and "Brief lines: flow 6" in h.stdout)
r, _ = run(doc(items=[item(ask="Link section 05. Maintenance under the parent.")]))
check("a numbered heading is not a second sentence", "sentences" not in r.stderr, r.stderr)

# Bad data: exit 2, nothing written
for label, data in (("items missing", {"title": "t", "as_of": "now"}),
                    ("an item without a recommendation", doc(items=[item(recommend="")])),
                    ("missing ask", doc(items=[item(ask="")])),
                    ("unknown kind", doc(items=[item(kind="nit")])),
                    ("unknown evidence kind", doc(items=[item(evidence=[{"kind": "rumour"}])])),
                    ("brief without flow", doc(brief={"what": "x"})),
                    ("brief without what", doc(brief={"flow": [{"label": "a", "text": "b"}]})),
                    ("flow steps without labels", doc(brief={"what": "x", "flow": ["a"]})),
                    ("changes without after", doc(brief=dict(BRIEF, changes=[{"what": "a", "now": "b"}]))),
                    ("work without a summary", doc(brief=dict(BRIEF, work={"items": []}))),
                    ("previous with an unknown status", doc(previous={"date": "x", "items": [{"title": "a", "status": "done"}]})),
                    ("where that is not a list of names", doc(items=[item(where=["a"])])),
                    ("more entry without a kind", doc(items=[item(more=[{"source": "x"}])])),
                    ("left_out without a reason", doc(left_out=[{"what": "x"}])),
                    ("ticket_url without {n}", doc(ticket_url="https://example.com/issues/")),
                    ("surfaces_last out of range", doc(surfaces_last=5)),
                    ("a mark outside the capture", doc(items=[item(evidence=[dict(SHOT, marks=[{"box": [0.8, 0, 0.5, 0.1]}])])])),
                    ("a crop outside the capture", doc(items=[item(evidence=[dict(SHOT, crop=[0.6, 0, 0.6, 1])])])),
                    ("a paste without text", doc(items=[item(paste={"to": "x"})])),
                    ("missing capture", doc(items=[item(evidence=[{"kind": "design", "image": "nope.png"}])]))):
    r, out = run(data)
    check(f"bad data exits 2: {label}", r.returncode == 2 and not out.exists(), r.stderr)

print()
if failures:
    print(f"{len(failures)} failed")
    sys.exit(1)
print("all passed")
