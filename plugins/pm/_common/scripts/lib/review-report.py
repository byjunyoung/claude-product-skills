#!/usr/bin/env python3
"""Renders a /pm:review report from the findings a review wrote, always in the same shape.

    python3 review-report.py DATA.json --out PATH [--lang LANG] [--format html|markdown]
    stdout: the written path, then one summary line
    python3 review-report.py --help         this text, the shape of DATA.json included
    exit 0 written · 1 written, with cells over budget (each on stderr) · 2 usage or bad data

pm-only — not one of the byte-identical shared files. The layout, the verdict's counts and every
cell's budget live here rather than in SKILL.md's prose: runs of the same skill once produced two
different page skeletons, and cards that grew past two thousand characters. A cell over budget is
still written, so the page can be looked at, but exit 1 means the review is not finished: the
overflow moves to the item's `more`, the budget does not move. Stdlib only.

DATA.json (title, as_of and items are required; leave out what does not apply)
  title            the feature, in the plan's own words
  plan             "own", or the author's name
  asked            {by, at, link} for a colleague's plan
  reviewer         who ran the review
  as_of            when the review started
  latest           {name, at, link}: the material edited last
  brief            the plan itself, before any finding: see below
  unread           [str] sources the run could not read
  surfaces_last    the item number the verdict names, for a colleague's plan
  ticket_url       the tracker's address for one ticket, with {n} for its number; every #123 on the
                   page then links to its ticket
  items            [item]
  before_handover  [str]
  not_checked      [str] what the review did not look at, and the risk that leaves
  left_out         [{what, why}]
  sources          [{name, link, note}]

brief (what and flow are required): what the plan is and how it works, as its materials describe it
  what             one sentence: what is being built, for whom
  why              the problem it answers
  flow             [str] how it works, in the order a person meets it, one step each
  in, out          [str] what this round builds, and what it leaves for later or to others
  capture          {source, link, image}: the one screen that shows the plan best
  links            [{name, link}] the spec, the design, the parent ticket

item (kind, title, problem and ask are required; evidence may be [])
  kind             "fix" | "opinion"
  area, title      short noun phrases
  problem          what is wrong
  if_left          what gets built, or does not, if nobody acts
  evidence         [evidence] shown on the card; [] marks the item evidence-needed
  ask              what to change and where, the recommendation first
  options          [str] where there is a choice, the recommended one first
  more             [evidence | {"table": {caption, head, rows}} | {"note", "inferred"}], folded
  looked           where you looked, behind a claim that something is not there; folded

evidence
  kind             spec | design | ticket | code | chat | screen
  source           where it is: the entry and section, the frame, the ticket, path:lines@commit, author and time
  link             an http(s) URL
  quote            the words as written (for code, the lines)
  image            a capture, relative to DATA.json
  inferred         true where this is your reasoning rather than something you found

Besides length and sentence count, a prose cell is flagged for a dash setting off an aside, a list
strung on middle dots, an arrow standing in for a verb, more than two quotations, or a ticket number
standing alone: a cell names the ticket and keeps the number in brackets, as in "the server ticket
(#12)". Text inside quotation marks or backticks is not read for any of these.
"""
import argparse, base64, html, json, re, shutil, sys, textwrap
from pathlib import Path

KINDS = ("fix", "opinion")
EVIDENCE_KINDS = ("spec", "design", "ticket", "code", "chat", "screen")

# Characters per cell. Scripts that pack a word into fewer characters get these as they are;
# every other language gets twice as many.
BUDGET = {"brief_what": 80, "brief_why": 150, "step": 70, "scope": 50,
          "title": 40, "area": 12, "problem": 150, "if_left": 90, "ask": 120, "option": 80,
          "quote": 160, "source": 70, "line": 100, "what": 60, "why": 100}
SENTENCES = {"problem": 2, "if_left": 1, "ask": 1, "brief_what": 1, "brief_why": 2}
SHOWN_EVIDENCE = 2
BRIEF_LIMITS = {"flow": 6, "in": 4, "out": 4, "links": 4}
OPTIONS = 3
DENSE = {"ko", "ja", "zh"}

LABELS = {
    "en": {
        "fix": "Fix", "opinion": "Opinion", "problem": "Problem", "if_left": "If left",
        "evidence": "Evidence", "ask": "Ask", "recommended": "recommended",
        "more": "More evidence", "looked": "Where I looked", "inferred": "inferred",
        "needed": "evidence needed", "items": "Items", "before": "Before handover",
        "not_checked": "Not checked", "left_out": "Left out", "sources": "Sources read",
        "plan": "Plan", "own": "Own plan", "asked": "Asked by", "reviewer": "Reviewed by",
        "as_of": "As of", "latest": "Last edited", "unread": "Could not read",
        "type": "Type", "area": "Area", "title": "Title", "what": "Candidate", "why": "Why it is out",
        "ready": "Ready to hand over",
        "brief": "The plan", "b_what": "What", "b_why": "Why", "b_flow": "How it works",
        "b_scope": "Scope", "b_in": "In", "b_out": "Out", "b_links": "Materials",
        "kinds": {"spec": "Spec", "design": "Design", "ticket": "Ticket", "code": "Code",
                  "chat": "Chat", "screen": "Screen"},
    },
    "ko": {
        "fix": "고칠 것", "opinion": "의견", "problem": "문제", "if_left": "안 고치면",
        "evidence": "근거", "ask": "할 일", "recommended": "권장",
        "more": "근거 더 보기", "looked": "찾아본 곳", "inferred": "추정",
        "needed": "근거 필요", "items": "항목", "before": "넘기기 전에",
        "not_checked": "보지 않은 것", "left_out": "뺀 것", "sources": "읽은 자료",
        "plan": "기획", "own": "내 기획", "asked": "요청", "reviewer": "검토",
        "as_of": "기준 시각", "latest": "마지막으로 고친 자료", "unread": "못 읽은 자료",
        "type": "구분", "area": "영역", "title": "제목", "what": "후보", "why": "뺀 이유",
        "ready": "넘겨도 됩니다",
        "brief": "기획 브리핑", "b_what": "무엇", "b_why": "왜", "b_flow": "동작",
        "b_scope": "범위", "b_in": "넣는 것", "b_out": "빼는 것", "b_links": "자료",
        "kinds": {"spec": "스펙", "design": "시안", "ticket": "일감", "code": "코드",
                  "chat": "대화", "screen": "화면"},
    },
}


def budget_help():
    cells = ", ".join(f"{k} {v}" for k, v in BUDGET.items())
    told = (f"Budgets, in characters for {', '.join(sorted(DENSE))} and twice as many for other languages: {cells}. "
            f"Sentences: " + ", ".join(f"{k} {v}" for k, v in SENTENCES.items())
            + f". Evidence on a card: {SHOWN_EVIDENCE}. Options: {OPTIONS}.")
    return textwrap.fill(told, 100)


def verdict(lang, own, fixes, opinions):
    if lang == "ko":
        if own:
            return "넘겨도 됩니다" if not fixes else f"넘기기 전에 고칠 것 {fixes}건"
        return f"고칠 것 {fixes}건, 의견 {opinions}건"
    plural = lambda n, w: f"{n} {w}" + ("" if n == 1 else ("es" if w.endswith("x") else "s"))
    if own:
        return "Ready to hand over" if not fixes else f"{plural(fixes, 'fix')} before handover"
    return f"{plural(fixes, 'fix')}, {plural(opinions, 'opinion')}"


def surfaces_line(lang, n, title):
    if lang == "ko":
        return f"그대로 두면 가장 늦게 드러날 것은 {n}번, {title}"
    return f"Surfaces last if nobody acts: {n}, {title}"


class BadData(Exception):
    pass


# --- budgets ------------------------------------------------------------------------------------

QUOTED = re.compile(r"「[^」]*」|“[^”]*”|\"[^\"]*\"|‘[^’]*’|『[^』]*』|`[^`]*`")
DASH = re.compile(r"[—–]")
DOT_LIST = re.compile(r"\s·\s")
ARROW = re.compile(r"→|⇒|->")
QUOTE_OPEN = re.compile(r"[「“『‘]")
BRACKETED = re.compile(r"\([^()]*\)")
BARE_NUMBER = re.compile(r"(?<![\w/])#\d+")


def sentences(text):
    t = text.strip()
    n = len(re.findall(r"(?<!\d)[.!?。](?=\s|$)", t))
    return n + (0 if re.search(r"(?<!\d)[.!?。]$", t) else 1)


class Budget:
    def __init__(self, lang):
        self.scale = 1 if lang in DENSE else 2
        self.warnings = []

    def cell(self, where, key, text, prose=True):
        if not text:
            return
        limit = BUDGET[key] * self.scale
        if len(text) > limit:
            self.warnings.append(f"{where} {key}: {len(text)} characters, budget {limit}")
        if key in SENTENCES and sentences(text) > SENTENCES[key]:
            self.warnings.append(f"{where} {key}: {sentences(text)} sentences, budget {SENTENCES[key]}")
        if prose:
            self.style(where, key, text)

    def style(self, where, key, text):
        """What the cells' sentences are held to; the folded notes are held to it too, without a length."""
        bare = QUOTED.sub("", text)
        if DASH.search(bare):
            self.warnings.append(f"{where} {key}: a dash sets off an aside; use a comma, brackets or a new sentence")
        if DOT_LIST.search(bare):
            self.warnings.append(f"{where} {key}: a list strung on ' · '; use commas")
        if ARROW.search(bare):
            self.warnings.append(f"{where} {key}: an arrow inside a sentence; write the step out")
        if BARE_NUMBER.search(BRACKETED.sub("", bare)):
            self.warnings.append(f"{where} {key}: a ticket number standing alone; name the ticket, number in brackets")
        quotes = len(QUOTE_OPEN.findall(text)) + text.count('"') // 2
        if quotes > 2:
            self.warnings.append(f"{where} {key}: {quotes} quotations; exact wording belongs in the evidence")


# --- data ---------------------------------------------------------------------------------------

def text(v):
    return v.strip() if isinstance(v, str) else ""


def safe_link(v):
    v = text(v)
    return v if re.match(r"https?://", v) else ""


def load(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise BadData(f"{path}: {e}")
    if not isinstance(data, dict):
        raise BadData("DATA.json must be an object")
    for key in ("title", "as_of"):
        if not text(data.get(key)):
            raise BadData(f"missing `{key}`")
    if not isinstance(data.get("items"), list):
        raise BadData("`items` must be a list (empty when nothing is raised)")
    for i, item in enumerate(data["items"], 1):
        if not isinstance(item, dict):
            raise BadData(f"item {i} is not an object")
        if item.get("kind") not in KINDS:
            raise BadData(f"item {i}: kind must be one of {', '.join(KINDS)}")
        for key in ("title", "problem", "ask"):
            if not text(item.get(key)):
                raise BadData(f"item {i}: missing `{key}`")
        for j, ev in enumerate(item.get("evidence") or [], 1):
            if not isinstance(ev, dict) or ev.get("kind") not in EVIDENCE_KINDS:
                raise BadData(f"item {i} evidence {j}: kind must be one of {', '.join(EVIDENCE_KINDS)}")
        for j, m in enumerate(item.get("more") or [], 1):
            where = f"item {i} more {j}"
            if not isinstance(m, dict):
                raise BadData(f"{where} is not an object")
            if "table" in m:
                t = m["table"]
                if not (isinstance(t, dict) and isinstance(t.get("head", []), list)
                        and isinstance(t.get("rows", []), list) and all(isinstance(r, list) for r in t.get("rows", []))):
                    raise BadData(f"{where}: a table is {{caption, head: [...], rows: [[...], ...]}}")
            elif "note" in m:
                if not text(m["note"]):
                    raise BadData(f"{where}: an empty note")
            elif m.get("kind") not in EVIDENCE_KINDS:
                raise BadData(f"{where}: a table, a note, or evidence whose kind is one of {', '.join(EVIDENCE_KINDS)}")
        if not isinstance(item.get("options") or [], list):
            raise BadData(f"item {i}: `options` must be a list")
    for key in ("before_handover", "not_checked", "unread"):
        if not isinstance(data.get(key) or [], list) or not all(isinstance(x, str) for x in data.get(key) or []):
            raise BadData(f"`{key}` must be a list of sentences")
    for key, need in (("left_out", ("what", "why")), ("sources", ("name",))):
        rows = data.get(key) or []
        if not isinstance(rows, list) or not all(isinstance(r, dict) and all(text(r.get(k)) for k in need) for r in rows):
            raise BadData(f"`{key}` must be a list of objects, each with {', '.join(need)}")
    url = text(data.get("ticket_url"))
    if url and ("{n}" not in url or not re.match(r"https?://", url)):
        raise BadData("`ticket_url` is an http(s) address with {n} where the number goes")
    brief = data.get("brief")
    if brief is not None:
        if not isinstance(brief, dict) or not text(brief.get("what")):
            raise BadData("`brief` needs `what`")
        flow = brief.get("flow")
        if not isinstance(flow, list) or not flow or not all(isinstance(x, str) and x.strip() for x in flow):
            raise BadData("`brief.flow` must be a list of steps")
        for key in ("in", "out"):
            if not isinstance(brief.get(key) or [], list):
                raise BadData(f"`brief.{key}` must be a list")
        if not isinstance(brief.get("links") or [], list) or not all(
                isinstance(x, dict) and text(x.get("name")) for x in brief.get("links") or []):
            raise BadData("`brief.links` must be a list of {name, link}")
        cap = brief.get("capture")
        if cap is not None and not isinstance(cap, dict):
            raise BadData("`brief.capture` is {source, link, image}")
    n = data.get("surfaces_last")
    if n is not None and not (isinstance(n, int) and 1 <= n <= len(data["items"])):
        raise BadData("`surfaces_last` must be an item number")
    return data


def check(data, lang):
    b = Budget(lang)
    brief = data.get("brief")
    if brief:
        b.cell("brief", "brief_what", text(brief.get("what")))
        b.cell("brief", "brief_why", text(brief.get("why")))
        for key, cell in (("flow", "step"), ("in", "scope"), ("out", "scope")):
            rows = brief.get(key) or []
            if len(rows) > BRIEF_LIMITS[key]:
                b.warnings.append(f"brief {key}: {len(rows)} lines, budget {BRIEF_LIMITS[key]}")
            for x in rows:
                b.cell(f"brief {key}", cell, text(x))
        if len(brief.get("links") or []) > BRIEF_LIMITS["links"]:
            b.warnings.append(f"brief links: {len(brief['links'])}, budget {BRIEF_LIMITS['links']}")
    for i, item in enumerate(data["items"], 1):
        where = f"item {i}"
        for key in ("title", "area", "problem", "if_left", "ask"):
            b.cell(where, key, text(item.get(key)))
        options = item.get("options") or []
        if len(options) > OPTIONS:
            b.warnings.append(f"{where} options: {len(options)}, budget {OPTIONS}")
        for o in options:
            b.cell(where, "option", text(o))
        shown = item.get("evidence") or []
        if len(shown) > SHOWN_EVIDENCE:
            b.warnings.append(f"{where} evidence: {len(shown)} on the card, budget {SHOWN_EVIDENCE}; move the rest to `more`")
        for ev in shown:
            b.cell(where, "quote", text(ev.get("quote")), prose=False)
            b.cell(where, "source", text(ev.get("source")), prose=False)
        for j, m in enumerate(item.get("more") or [], 1):
            if text(m.get("note")):
                b.style(f"{where} more {j}", "note", text(m["note"]))
        if text(item.get("looked")):
            b.style(where, "looked", text(item["looked"]))
    for key, label in (("before_handover", "before handover"), ("not_checked", "not checked")):
        for line in data.get(key) or []:
            b.cell(label, "line", text(line))
    for row in data.get("left_out") or []:
        b.cell("left out", "what", text(row.get("what")), prose=False)
        b.cell("left out", "why", text(row.get("why")))
    return b.warnings


def image_path(base, ev):
    raw = text(ev.get("image"))
    if not raw:
        return None
    p = Path(raw) if Path(raw).is_absolute() else base / raw
    if not p.is_file():
        raise BadData(f"capture not found: {raw}")
    return p


# --- html ---------------------------------------------------------------------------------------

CSS = """
:root{--fg:#1d1d1f;--muted:#6b6b70;--line:#e4e4e7;--bg:#fff;--soft:#f5f5f6;--fix:#b42318;--fix-bg:#fef3f2;--op:#175cd3;--op-bg:#eff8ff;--ok:#067647;--ok-bg:#ecfdf3}
@media (prefers-color-scheme:dark){:root{--fg:#ececf1;--muted:#a1a1aa;--line:#34343a;--bg:#16161a;--soft:#202026;--fix:#fda29b;--fix-bg:#3a1714;--op:#84caff;--op-bg:#102a43;--ok:#75e0a7;--ok-bg:#0f2e1f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",sans-serif;word-break:keep-all;overflow-wrap:anywhere}
main{max-width:760px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:22px;line-height:1.35;margin:0 0 14px}
h2{font-size:16px;margin:36px 0 10px}
a{color:var(--op)}
.meta{display:grid;grid-template-columns:max-content 1fr;gap:2px 14px;margin:0 0 18px;font-size:14px}
.meta dt{color:var(--muted)}
.meta dd{margin:0}
.verdict{padding:14px 16px;border-radius:10px;background:var(--fix-bg);font-size:18px;font-weight:700}
.verdict.ok{background:var(--ok-bg)}
.verdict p{margin:4px 0 0;font-size:14px;font-weight:400}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600;white-space:nowrap}
td.n{color:var(--muted);width:2em}
.tag{display:inline-block;font-size:12px;font-weight:600;line-height:20px;padding:0 8px;border-radius:999px;white-space:nowrap;color:var(--muted);background:var(--soft)}
.tag.fix{color:var(--fix);background:var(--fix-bg)}
.tag.opinion{color:var(--op);background:var(--op-bg)}
.card{border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
.card header{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px;color:var(--muted)}
.card h3{font-size:17px;line-height:1.4;margin:6px 0 14px}
.cells{display:grid;grid-template-columns:5.5em 1fr;gap:10px 12px;margin:0}
.cells dt{color:var(--muted);font-size:14px;font-weight:600}
.cells dd{margin:0}
.ev+.ev{margin-top:10px}
.src{font-size:13px;color:var(--muted)}
blockquote{margin:4px 0 0;padding:6px 12px;border-left:3px solid var(--line);background:var(--soft);border-radius:0 6px 6px 0;white-space:pre-wrap}
pre{margin:4px 0 0;padding:8px 12px;background:var(--soft);border-radius:6px;overflow-x:auto;font-size:13px;line-height:1.5}
img{display:block;max-width:100%;border:1px solid var(--line);border-radius:6px;margin-top:4px}
ol.opts{margin:6px 0 0;padding-left:1.4em}
details{margin-top:12px;font-size:14px}
summary{cursor:pointer;color:var(--muted);font-weight:600}
details>*:not(summary){margin-top:8px}
.note{margin:8px 0 0}
.brief{border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 18px}
.brief h2{margin:0 0 12px}
ol.flow{margin:0;padding-left:1.4em}
ol.flow li+li{margin-top:2px}
.scope{display:grid;grid-template-columns:max-content 1fr;gap:2px 10px}
.caption{font-size:13px;color:var(--muted);margin:10px 0 4px}
ul.plain{margin:0;padding-left:1.2em}
@media (max-width:520px){.cells{grid-template-columns:1fr;gap:2px}.cells dd{margin-bottom:10px}.meta{grid-template-columns:1fr;gap:0}.meta dd{margin-bottom:6px}}
"""

TICKET_URL = ""


def E(s, link_tickets=True):
    out = html.escape(text(s) if not isinstance(s, (int, float)) else str(s))
    if TICKET_URL and link_tickets:
        out = re.sub(r"(?<![\w/&])#(\d+)",
                     lambda m: f'<a href="{html.escape(TICKET_URL.replace("{n}", m.group(1)))}">#{m.group(1)}</a>', out)
    return out


def a(label, link):
    link = safe_link(link)
    return f'<a href="{E(link, False)}">{E(label, False)}</a>' if link else E(label)


def data_uri(p):
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
            ".webp": "image/webp", ".svg": "image/svg+xml"}.get(p.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def html_table(t):
    head = "".join(f"<th>{E(h)}</th>" for h in t.get("head") or [])
    rows = "".join("<tr>" + "".join(f"<td>{E(c)}</td>" for c in r) + "</tr>" for r in t.get("rows") or [])
    cap = f'<p class="caption">{E(t.get("caption"))}</p>' if text(t.get("caption")) else ""
    return f'{cap}<div class="tw"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def html_evidence(L, base, ev):
    tag = f'<span class="tag">{E(L["kinds"][ev["kind"]])}</span> '
    inferred = f' <span class="tag">{E(L["inferred"])}</span>' if ev.get("inferred") else ""
    out = f'<div class="ev"><div class="src">{tag}{a(ev.get("source") or "", ev.get("link"))}{inferred}</div>'
    q = text(ev.get("quote"))
    if q:
        out += f"<pre><code>{E(q, False)}</code></pre>" if ev["kind"] == "code" else f"<blockquote>{E(q)}</blockquote>"
    p = image_path(base, ev)
    if p:
        out += f'<img src="{data_uri(p)}" alt="{E(ev.get("source") or "", False)}">'
    return out + "</div>"


def html_more(L, base, entry):
    if "table" in entry:
        return html_table(entry["table"])
    if "note" in entry:
        inferred = f'<span class="tag">{E(L["inferred"])}</span> ' if entry.get("inferred") else ""
        return f'<p class="note">{inferred}{E(entry["note"])}</p>'
    return html_evidence(L, base, entry)


def html_brief(L, base, brief):
    rows = [(L["b_what"], E(brief["what"]))]
    if text(brief.get("why")):
        rows.append((L["b_why"], E(brief["why"])))
    rows.append((L["b_flow"], '<ol class="flow">' + "".join(f"<li>{E(x)}</li>" for x in brief["flow"]) + "</ol>"))
    scope = "".join(f'<span class="src">{E(L["b_" + k])}</span><span>{"<br>".join(E(x) for x in brief.get(k) or [])}</span>'
                    for k in ("in", "out") if brief.get(k))
    if scope:
        rows.append((L["b_scope"], f'<div class="scope">{scope}</div>'))
    if brief.get("links"):
        rows.append((L["b_links"], ", ".join(a(x.get("name"), x.get("link")) for x in brief["links"])))
    out = f'<section class="brief"><h2>{E(L["brief"])}</h2><dl class="cells">'
    out += "".join(f"<dt>{E(k)}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>"
    cap = brief.get("capture")
    if cap:
        p = image_path(base, cap)
        out += f'<div class="ev" style="margin-top:12px"><div class="src">{a(cap.get("source") or "", cap.get("link"))}</div>'
        out += (f'<img src="{data_uri(p)}" alt="{E(cap.get("source") or "", False)}">' if p else "") + "</div>"
    return out + "</section>"


def render_html(data, L, lang, base):
    items = data["items"]
    own = text(data.get("plan")) in ("", "own")
    fixes = sum(1 for i in items if i["kind"] == "fix")
    opinions = len(items) - fixes
    out = [f'<!doctype html><html lang="{E(lang)}"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{E(data["title"], False)}</title><style>{CSS}</style></head><body><main>',
           f'<h1>{E(data["title"])}</h1><dl class="meta">']
    meta = [(L["plan"], E(L["own"] if own else data.get("plan")))]
    asked = data.get("asked") or {}
    if text(asked.get("by")) or text(asked.get("at")):
        meta.append((L["asked"], a(", ".join(x for x in (text(asked.get("by")), text(asked.get("at"))) if x), asked.get("link"))))
    if text(data.get("reviewer")):
        meta.append((L["reviewer"], E(data["reviewer"])))
    meta.append((L["as_of"], E(data["as_of"])))
    latest = data.get("latest") or {}
    if text(latest.get("name")):
        meta.append((L["latest"], a(latest["name"], latest.get("link")) + (f", {E(latest.get('at'))}" if text(latest.get("at")) else "")))
    if data.get("unread"):
        meta.append((L["unread"], E(", ".join(text(u) for u in data["unread"]))))
    out += [f"<dt>{E(k)}</dt><dd>{v}</dd>" for k, v in meta]
    out.append("</dl>")
    if data.get("brief"):
        out.append(html_brief(L, base, data["brief"]))

    ok = own and not fixes
    out.append(f'<div class="verdict{" ok" if ok else ""}">{E(verdict(lang, own, fixes, opinions))}')
    n = data.get("surfaces_last")
    if n and not own:
        out.append(f"<p>{E(surfaces_line(lang, n, items[n - 1]['title']))}</p>")
    out.append("</div>")

    if items:
        out.append(f'<h2>{E(L["items"])}</h2><div class="tw"><table><thead><tr><th>#</th><th>{E(L["type"])}</th>'
                   f'<th>{E(L["area"])}</th><th>{E(L["title"])}</th></tr></thead><tbody>')
        for k, item in enumerate(items, 1):
            out.append(f'<tr><td class="n">{k}</td><td><span class="tag {item["kind"]}">{E(L[item["kind"]])}</span></td>'
                       f'<td>{E(item.get("area"))}</td><td><a href="#i{k}">{E(item["title"], False)}</a></td></tr>')
        out.append("</tbody></table></div>")

    for k, item in enumerate(items, 1):
        out.append(f'<article class="card" id="i{k}"><header><b>{k}</b>'
                   f'<span class="tag {item["kind"]}">{E(L[item["kind"]])}</span>')
        if text(item.get("area")):
            out.append(f"<span>{E(item['area'])}</span>")
        out.append(f'</header><h3>{E(item["title"])}</h3><dl class="cells">')
        out.append(f'<dt>{E(L["problem"])}</dt><dd>{E(item["problem"])}</dd>')
        if text(item.get("if_left")):
            out.append(f'<dt>{E(L["if_left"])}</dt><dd>{E(item["if_left"])}</dd>')
        evidence = item.get("evidence") or []
        body = "".join(html_evidence(L, base, ev) for ev in evidence) or f'<span class="tag fix">{E(L["needed"])}</span>'
        out.append(f'<dt>{E(L["evidence"])}</dt><dd>{body}</dd>')
        ask = E(item["ask"])
        options = item.get("options") or []
        if options:
            rec = f' <span class="tag">{E(L["recommended"])}</span>'
            ask += '<ol class="opts">' + "".join(
                f"<li>{E(o)}{rec if j == 0 else ''}</li>" for j, o in enumerate(options)) + "</ol>"
        out.append(f'<dt>{E(L["ask"])}</dt><dd>{ask}</dd></dl>')
        more = item.get("more") or []
        if more:
            out.append(f'<details><summary>{E(L["more"])} ({len(more)})</summary>'
                       + "".join(html_more(L, base, m) for m in more) + "</details>")
        if text(item.get("looked")):
            out.append(f'<details><summary>{E(L["looked"])}</summary><p class="note">{E(item["looked"])}</p></details>')
        out.append("</article>")

    for key in ("before_handover", "not_checked"):
        lines = [text(x) for x in data.get(key) or [] if text(x)]
        if lines:
            out.append(f'<h2>{E(L["before" if key == "before_handover" else key])}</h2><ul class="plain">'
                       + "".join(f"<li>{E(x)}</li>" for x in lines) + "</ul>")
    left = data.get("left_out") or []
    out.append(f'<h2>{E(L["left_out"])} ({len(left)})</h2>')
    if left:
        out.append(f'<details><summary>{E(L["left_out"])}</summary>' + html_table(
            {"head": [L["what"], L["why"]], "rows": [[r.get("what"), r.get("why")] for r in left]}) + "</details>")
    srcs = data.get("sources") or []
    if srcs:
        out.append(f'<h2>{E(L["sources"])} ({len(srcs)})</h2><details><summary>{E(L["sources"])}</summary><ul class="plain">'
                   + "".join(f"<li>{a(s.get('name') or '', s.get('link'))}"
                             + (f", {E(s.get('note'))}" if text(s.get("note")) else "") + "</li>" for s in srcs)
                   + "</ul></details>")
    out.append("</main></body></html>\n")
    return "".join(out)


# --- markdown -----------------------------------------------------------------------------------

def md_text(v):
    t = text(v)
    if TICKET_URL:
        t = re.sub(r"(?<![\w/\[])#(\d+)", lambda m: f"[#{m.group(1)}]({TICKET_URL.replace('{n}', m.group(1))})", t)
    return t


def md_cell(v):
    return md_text(v).replace("|", "\\|").replace("\n", " ")


def md_link(label, link):
    link = safe_link(link)
    return f"[{text(label)}]({link})" if link else text(label)


def md_quote(s, indent=""):
    return "\n".join(f"{indent}> {line}" if line else f"{indent}>" for line in text(s).split("\n"))


def md_evidence(L, base, ev, assets, indent="  "):
    lines = [f"{indent}- `{L['kinds'][ev['kind']]}` {md_link(ev.get('source') or '', ev.get('link'))}"
             + (f" `{L['inferred']}`" if ev.get("inferred") else "")]
    q = text(ev.get("quote"))
    if q:
        if ev["kind"] == "code":
            lines += [f"{indent}  ```", *[f"{indent}  {x}" for x in q.split("\n")], f"{indent}  ```"]
        else:
            lines.append(md_quote(q, indent + "  "))
    p = image_path(base, ev)
    if p:
        lines.append(f"{indent}  ![{text(ev.get('source'))}]({assets(p)})")
    return lines


def md_table(t):
    head = t.get("head") or []
    out = [f"*{text(t.get('caption'))}*", ""] if text(t.get("caption")) else []
    out += ["| " + " | ".join(md_cell(h) for h in head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(md_cell(c) for c in r) + " |" for r in t.get("rows") or []]
    return out


def render_markdown(data, L, lang, base, out_path):
    folder = out_path.with_suffix("")
    copied = {}

    def assets(p):
        if p not in copied:
            folder.mkdir(parents=True, exist_ok=True)
            name = p.name
            while (folder / name).exists() and name not in copied.values():
                name = f"{p.stem}-{len(copied) + 1}{p.suffix}"
            shutil.copyfile(p, folder / name)
            copied[p] = name
        return f"{folder.name}/{copied[p]}"

    items = data["items"]
    own = text(data.get("plan")) in ("", "own")
    fixes = sum(1 for i in items if i["kind"] == "fix")
    out = [f"# {text(data['title'])}", ""]
    out.append(f"- {L['plan']}: {L['own'] if own else text(data.get('plan'))}")
    asked = data.get("asked") or {}
    if text(asked.get("by")) or text(asked.get("at")):
        out.append(f"- {L['asked']}: " + md_link(", ".join(x for x in (text(asked.get("by")), text(asked.get("at"))) if x), asked.get("link")))
    if text(data.get("reviewer")):
        out.append(f"- {L['reviewer']}: {text(data['reviewer'])}")
    out.append(f"- {L['as_of']}: {text(data['as_of'])}")
    latest = data.get("latest") or {}
    if text(latest.get("name")):
        out.append(f"- {L['latest']}: {md_link(latest['name'], latest.get('link'))}" + (f", {text(latest.get('at'))}" if text(latest.get("at")) else ""))
    if data.get("unread"):
        out.append(f"- {L['unread']}: " + ", ".join(text(u) for u in data["unread"]))
    brief = data.get("brief")
    if brief:
        out += ["", f"## {L['brief']}", "", f"- **{L['b_what']}** {md_text(brief['what'])}"]
        if text(brief.get("why")):
            out.append(f"- **{L['b_why']}** {md_text(brief['why'])}")
        out.append(f"- **{L['b_flow']}**")
        out += [f"  {j}. {md_text(x)}" for j, x in enumerate(brief["flow"], 1)]
        for k in ("in", "out"):
            if brief.get(k):
                out.append(f"- **{L['b_' + k]}** " + "; ".join(md_text(x) for x in brief[k]))
        if brief.get("links"):
            out.append(f"- **{L['b_links']}** " + ", ".join(md_link(x.get("name"), x.get("link")) for x in brief["links"]))
        cap = brief.get("capture")
        if cap:
            p = image_path(base, cap)
            out += ["", md_link(cap.get("source") or "", cap.get("link"))] + ([f"![{text(cap.get('source'))}]({assets(p)})"] if p else [])
    out += ["", f"> **{verdict(lang, own, fixes, len(items) - fixes)}**"]
    n = data.get("surfaces_last")
    if n and not own:
        out.append(f"> {surfaces_line(lang, n, items[n - 1]['title'])}")
    if items:
        out += ["", f"## {L['items']}", "", f"| # | {L['type']} | {L['area']} | {L['title']} |", "|---|---|---|---|"]
        out += [f"| {k} | {L[i['kind']]} | {md_cell(i.get('area'))} | [{md_cell(i['title'])}](#{k}) |" for k, i in enumerate(items, 1)]
    for k, item in enumerate(items, 1):
        out += ["", f'<a id="{k}"></a>', f"### {k}. {text(item['title'])}", "",
                f"`{L[item['kind']]}`" + (f" `{text(item['area'])}`" if text(item.get("area")) else ""), "",
                f"- **{L['problem']}** {md_text(item['problem'])}"]
        if text(item.get("if_left")):
            out.append(f"- **{L['if_left']}** {md_text(item['if_left'])}")
        evidence = item.get("evidence") or []
        out.append(f"- **{L['evidence']}**" + ("" if evidence else f" `{L['needed']}`"))
        for ev in evidence:
            out += md_evidence(L, base, ev, assets)
        out.append(f"- **{L['ask']}** {md_text(item['ask'])}")
        for j, o in enumerate(item.get("options") or [], 1):
            out.append(f"  {j}. {md_text(o)}" + (f" `{L['recommended']}`" if j == 1 else ""))
        more = item.get("more") or []
        if more:
            out += ["", f"<details><summary>{L['more']} ({len(more)})</summary>", ""]
            for m in more:
                if "table" in m:
                    out += md_table(m["table"]) + [""]
                elif "note" in m:
                    out += [(f"`{L['inferred']}` " if m.get("inferred") else "") + md_text(m["note"]), ""]
                else:
                    out += md_evidence(L, base, m, assets, indent="") + [""]
            out.append("</details>")
        if text(item.get("looked")):
            out += ["", f"<details><summary>{L['looked']}</summary>", "", md_text(item["looked"]), "", "</details>"]
    for key in ("before_handover", "not_checked"):
        lines = [md_text(x) for x in data.get(key) or [] if text(x)]
        if lines:
            out += ["", f"## {L['before' if key == 'before_handover' else key]}", ""] + [f"- {x}" for x in lines]
    left = data.get("left_out") or []
    out += ["", f"## {L['left_out']} ({len(left)})"]
    if left:
        out += ["", f"<details><summary>{L['left_out']}</summary>", ""]
        out += md_table({"head": [L["what"], L["why"]], "rows": [[r.get("what"), r.get("why")] for r in left]})
        out += ["", "</details>"]
    srcs = data.get("sources") or []
    if srcs:
        out += ["", f"## {L['sources']} ({len(srcs)})", "", f"<details><summary>{L['sources']}</summary>", ""]
        out += [f"- {md_link(s.get('name') or '', s.get('link'))}" + (f", {md_text(s.get('note'))}" if text(s.get("note")) else "") for s in srcs]
        out += ["", "</details>"]
    return "\n".join(out) + "\n"


# --- main ---------------------------------------------------------------------------------------

class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: {message}\n")
        sys.exit(2)


def main():
    ap = Parser(description=__doc__ + "\n" + budget_help(), formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--format", choices=("html", "markdown"), default="html")
    args = ap.parse_args()
    lang = args.lang if args.lang in LABELS else "en"
    if lang != args.lang:
        print(f"no labels for '{args.lang}'; writing the report's labels in English", file=sys.stderr)
    L = LABELS[lang]
    base = Path(args.data).resolve().parent
    out_path = Path(args.out)
    global TICKET_URL
    try:
        data = load(args.data)
        TICKET_URL = text(data.get("ticket_url"))
        warnings = check(data, lang)
        body = (render_html(data, L, lang, base) if args.format == "html"
                else render_markdown(data, L, lang, base, out_path))
    except BadData as e:
        print(f"bad data: {e}", file=sys.stderr)
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")
    items = data["items"]
    fixes = sum(1 for i in items if i["kind"] == "fix")
    print(out_path)
    print(f"items {len(items)} (fix {fixes}, opinion {len(items) - fixes}), over budget {len(warnings)}")
    for w in warnings:
        print(w, file=sys.stderr)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
