#!/usr/bin/env python3
"""Renders a /pm:review report from the findings a review wrote, always in the same shape.

    python3 review-report.py DATA.json --out PATH [--lang LANG] [--format html|markdown]
    python3 review-report.py --help         this text, the shape of DATA.json included
    stdout: the written path, then one summary line
    exit 0 written · 1 written, with cells over budget (each on stderr) · 2 usage or bad data

pm-only — not one of the byte-identical shared files. The layout, the verdict's counts and every
cell's budget live here rather than in SKILL.md's prose: runs of the same skill once produced two
different page skeletons, and cards that grew past two thousand characters. A cell over budget is
still written, so the page can be looked at, but exit 1 means the review is not finished: the
overflow moves to the item's `more`, the budget does not move. Stdlib only.

The report is the reviewer's to the person who decides. Top to bottom: the request; the brief of
the plan (in a line, why, the flow as screens, what changes, scope, who builds it, what is already
decided, what waits on others); the conclusion, whether to hand it over now, with its grounds; the
decisions to take, each with the recommended one and how to answer; one card per decision with its
evidence; what is left; and notes, folded. A section with nothing in it is not drawn.

DATA.json (title, as_of and items are required; leave out what does not apply)
  title            the feature, in the plan's own words
  plan             "own", or the author's name
  asked            {by, at, link, note}: who asked, when, the request's link, and what they asked for
  reviewer         who ran the review
  as_of            when the review started
  latest           {name, at, link}: the material edited last
  unread           [str] sources the run could not read
  brief            the plan itself, before any finding: see below
  previous         {date, link, items: [{title, status, note}]} when the plan comes back after an
                   earlier review; status is resolved, withdrawn or open
  surfaces_last    the item number (from 1) that would surface last if nobody decided, for a colleague's plan
  ticket_url       the tracker's address for one ticket, with {n} for its number; every #123 on the
                   page then links to its ticket
  items            [item], one per decision
  before_handover  [str]
  not_checked      [str] what the review did not look at, and the risk that leaves
  left_out         [{what, why}]
  sources          [{name, link, note}]

brief (what and flow are required): the plan as its materials describe it; it does not judge
  what             one sentence: what is being built, for whom
  why              the problem it answers, and who asked for it when
  flow             [{label, text, image, crop, link}] how it works, in the order a person meets it:
                   a label of two or three words, the step as a sentence, and the screen it happens on
  changes          [{what, now, after}] what a person meets differently; "now" from the code or the
                   running screen
  in, out          [str] what this round builds, and what it leaves for later or to others
  in_label, out_label  what to call the two, such as a release name
  work             {summary, items: [{name, link, owner, status}]} who builds it: a line, and the tickets
  decided          [{what, when, link}] decisions already taken, so nobody reopens them
  waiting          [str] answers the plan waits on from others, which are not this review's findings
  links            [{name, link}] the spec, the design, the parent ticket

item (kind, title, problem, recommend and ask are required; evidence may be [])
  kind             "fix" (decide before handover) | "opinion" (the author's call)
  area             a short noun phrase
  title            the decision to take, or the problem, in a line
  recommend        the recommended decision, short, for the list on the first screen
  where            [{name, link}] where the fix goes: the spec entry and section, the frame, the ticket
  problem          what is wrong, and between which materials
  ask              the recommended decision in full: what changes, where
  reason           why that one, in a clause
  options          [str] the other choices, each a line; none where there is no real choice
  if_left          what gets built, or does not, if nobody decides
  evidence         [evidence] at most two; a capture counts as one and goes above the cells
  owner, then      who moves once it is decided, as a role (a person's name only where a ticket's
                   assignee field gives it), and what they do
  paste            {to, text}: the exact text for the spec or ticket, only where the evidence already
                   settles it (a typo, a stale link, wording another document uses); never beside options
  more             [evidence | {"table": {caption, head, rows}} | {"note", "inferred"}], folded
  looked           where you looked, behind a claim that something is not there: a sentence or a list

evidence
  kind             spec | design | ticket | code | chat | screen
  source           where it is: the entry and section, the frame, the ticket, path:lines@commit, author and time
  link             an http(s) URL
  quote            the words as written (for code, the lines)
  image            a capture, relative to DATA.json: the whole frame, as a PNG
  crop             [x, y, w, h] the part of the capture to show, as fractions of its width and height
  marks            [{box: [x, y, w, h]}] up to three boxes, as fractions of the whole capture (0 to 1),
                   numbered on the page; for something missing, where it should be. A frame's capture
                   lines up with the node positions in its metadata; an instance's does not, since its
                   capture takes in its shadow
  inferred         true where this is your reasoning rather than something you found

Besides length and sentence count, a prose cell is flagged for a dash setting off an aside, a list
strung on middle dots, an arrow standing in for a verb, more than two quotations, or a ticket number
standing alone: a cell names the ticket and keeps the number in brackets, as in "the server ticket
(#12)". Text inside quotation marks or backticks is not read for any of these.
"""
import argparse, base64, html, json, re, shutil, struct, sys, textwrap
from pathlib import Path

KINDS = ("fix", "opinion")
EVIDENCE_KINDS = ("spec", "design", "ticket", "code", "chat", "screen")
PREVIOUS_STATUS = ("resolved", "withdrawn", "open")

# Characters per cell. Scripts that pack a word into fewer characters get these as they are;
# every other language gets twice as many.
BUDGET = {"brief_what": 80, "brief_why": 150, "step": 70, "label": 10, "change": 40, "scope": 50,
          "work": 80, "decided": 50, "waiting": 60,
          "title": 40, "area": 12, "recommend": 50, "reason": 60, "problem": 150, "ask": 120,
          "option": 80, "if_left": 90, "owner": 12, "then": 60, "paste": 200,
          "quote": 160, "source": 70, "line": 100, "what": 60, "why": 100}
SENTENCES = {"problem": 2, "if_left": 1, "ask": 1, "reason": 1, "brief_what": 1, "brief_why": 2}
SHOWN_EVIDENCE = 2
OPTIONS = 3
WHERE = 2
MARKS = 3
BRIEF_LIMITS = {"flow": 6, "changes": 5, "in": 4, "out": 4, "decided": 5, "waiting": 3, "links": 4}
DENSE = {"ko", "ja", "zh"}

LABELS = {
    "en": {
        "asked": "Asked", "brief": "The plan", "b_what": "In a line", "b_why": "Why", "b_flow": "Flow",
        "b_changes": "What changes", "c_what": "What", "c_now": "Now", "c_after": "After",
        "b_scope": "Scope", "b_in": "This round", "b_out": "Not this round", "b_work": "Who builds it",
        "b_work_n": "{n} tickets", "w_name": "Ticket", "w_owner": "Owner", "w_status": "Status",
        "b_decided": "Already decided", "b_waiting": "Waiting on", "b_links": "Materials",
        "decisions": "Decisions", "evidence_h": "Evidence", "open_h": "Open", "notes_h": "Notes",
        "fix": "Fix", "opinion": "Opinion", "recommend": "Recommended", "others_n": "{n} other options",
        "others_none": "no other option", "answer_own": "Answer \"all as recommended\", or only what differs (\"2: the other option\"), and the fixes follow from it.",
        "answer_colleague": "Answer \"all as recommended\", or only what differs (\"2: the other option\"), and the reply to the author is drafted from it.",
        "gloss": "A fix is decided before handover; an opinion is the author's call.",
        "problem": "Problem", "ask": "Recommended", "reason": "Why", "options": "Other options",
        "if_left": "If undecided", "evidence": "Evidence", "then": "Then", "where": "Where",
        "paste": "Text to paste", "more": "More evidence", "looked": "Where I looked", "inferred": "inferred",
        "needed": "evidence needed", "before": "Before handover", "not_checked": "Not checked",
        "left_out": "Left out", "sources": "Sources read", "reviewer": "Reviewed by", "latest": "Last edited",
        "unread": "Could not read", "what": "Candidate", "why": "Why it is out",
        "grounds": "Grounds", "not_checked_n": "{n} not checked", "unread_n": "{n} sources unread",
        "previous": "Since the last review ({date})", "earlier": "Earlier finding", "status": "Status",
        "note": "Note", "earlier_n": "{n} earlier findings",
        "statuses": {"resolved": "resolved", "withdrawn": "withdrawn", "open": "still open"},
        "own": "Own plan", "of": "{plan}'s plan", "asked_at": "asked {at}", "as_of": "as of {at}",
        "markdown_marks": "(marked in the HTML report)", "open_design": "open in the design tool",
        "close": "Close", "prev": "Previous", "next": "Next", "whole": "Whole screen", "part": "The part",
        "d_title": "Decision", "d_others": "Other options", "none": "none", "zoom": "View large", "zoom_hint": "Click a screen to see it full size; arrow keys move, Esc closes.",
        "kinds": {"spec": "Spec", "design": "Design", "ticket": "Ticket", "code": "Code",
                  "chat": "Chat", "screen": "Screen"},
    },
    "ko": {
        "asked": "요청", "brief": "기획 브리핑", "b_what": "한 줄", "b_why": "왜", "b_flow": "흐름",
        "b_changes": "바뀌는 것", "c_what": "무엇", "c_now": "지금", "c_after": "바뀐 뒤",
        "b_scope": "범위", "b_in": "이번에", "b_out": "이번엔 안 함", "b_work": "만드는 쪽",
        "b_work_n": "일감 {n}건", "w_name": "일감", "w_owner": "담당", "w_status": "상태",
        "b_decided": "이미 정함", "b_waiting": "답 기다림", "b_links": "자료",
        "decisions": "결정 필요", "evidence_h": "근거", "open_h": "남은 것", "notes_h": "비고",
        "fix": "고칠 것", "opinion": "의견", "recommend": "권장", "others_n": "다른 안 {n}",
        "others_none": "다른 안 없음",
        "answer_own": "답하는 법: 권장안대로면 \u201c전부 권장대로\u201d, 바꿀 것만 있으면 \u201c2번은 다른 안\u201d처럼 답하시면 그 결정대로 고칠 목록을 만듭니다.",
        "answer_colleague": "답하는 법: 권장안대로면 \u201c전부 권장대로\u201d, 바꿀 것만 있으면 \u201c2번은 다른 안\u201d처럼 답하시면 그 결정대로 작성자에게 보낼 회신 초안을 씁니다.",
        "gloss": "고칠 것은 넘기기 전에 정할 것, 의견은 작성자가 정할 것",
        "problem": "문제", "ask": "권장", "reason": "이유", "options": "다른 안", "if_left": "안 정하면",
        "evidence": "근거", "then": "정하면", "where": "위치", "paste": "붙여 넣을 문장",
        "more": "근거 더 보기", "looked": "찾아본 곳", "inferred": "추정", "needed": "근거 필요",
        "before": "넘기기 전에", "not_checked": "보지 않은 것", "left_out": "뺀 것", "sources": "읽은 자료",
        "reviewer": "검토", "latest": "마지막으로 고친 자료", "unread": "못 읽은 자료",
        "what": "후보", "why": "뺀 이유",
        "grounds": "판단 근거", "not_checked_n": "보지 않은 것 {n}건", "unread_n": "못 읽은 자료 {n}건",
        "previous": "지난 리뷰({date}) 뒤", "earlier": "지난 지적", "status": "판정", "note": "근거",
        "earlier_n": "지난 지적 {n}건",
        "statuses": {"resolved": "반영", "withdrawn": "철회", "open": "남음"},
        "own": "내 기획", "of": "{plan} 기획", "asked_at": "요청 {at}", "as_of": "{at} 기준",
        "markdown_marks": "(표시는 HTML 보고서에)", "open_design": "시안에서 열기",
        "close": "닫기", "prev": "이전", "next": "다음", "whole": "화면 전체", "part": "해당 부분",
        "d_title": "결정할 것", "d_others": "다른 안", "none": "없음", "zoom": "크게 보기", "zoom_hint": "화면을 누르면 이 페이지에서 크게 봅니다. 좌우 화살표로 넘기고 Esc로 닫습니다.",
        "kinds": {"spec": "스펙", "design": "시안", "ticket": "일감", "code": "코드",
                  "chat": "대화", "screen": "화면"},
    },
}


def budget_help():
    cells = ", ".join(f"{k} {v}" for k, v in BUDGET.items())
    told = (f"Budgets, in characters for {', '.join(sorted(DENSE))} and twice as many for other languages: {cells}. "
            f"Sentences: " + ", ".join(f"{k} {v}" for k, v in SENTENCES.items())
            + f". Evidence on a card: {SHOWN_EVIDENCE}. Options: {OPTIONS}. Locations: {WHERE}. Marks per capture: {MARKS}. "
            + "Brief lines: " + ", ".join(f"{k} {v}" for k, v in BRIEF_LIMITS.items()) + ".")
    return textwrap.fill(told, 100)


def verdict(lang, own, fixes, opinions):
    if lang == "ko":
        if own:
            return "넘겨도 됩니다" if not fixes else f"넘기기 전에 정하실 것 {fixes}건"
        if not fixes:
            return f"넘겨도 됩니다. 의견 {opinions}건"
        return f"아직 넘기지 않기를 권합니다. 정하실 것 {fixes}건" + (f", 의견 {opinions}건" if opinions else "")
    plural = lambda n, w: f"{n} {w}" + ("" if n == 1 else "s")
    if own:
        return "Ready to hand over" if not fixes else f"{plural(fixes, 'decision')} before handover"
    if not fixes:
        return f"Ready to hand over, {plural(opinions, 'opinion')}"
    return f"Not ready yet: {plural(fixes, 'decision')} to make" + (f", {plural(opinions, 'opinion')}" if opinions else "")


def grounds(L, data):
    """What the verdict could not see, as counts; a review that read less says so beside its answer."""
    parts = [L[k].format(n=len(data.get(f) or [])) for k, f in (("not_checked_n", "not_checked"), ("unread_n", "unread"))
             if data.get(f)]
    return f"{L['grounds']}: " + ", ".join(parts) if parts else ""


def previous_line(L, prev):
    counts = ", ".join(f"{L['statuses'][st]} {sum(1 for x in prev['items'] if x['status'] == st)}" for st in PREVIOUS_STATUS)
    return f"{L['previous'].format(date=text(prev.get('date')))}: {counts}"


def surfaces_line(lang, n, title):
    if lang == "ko":
        return f"그대로 두면 가장 늦게 드러날 것은 {n}번, {title}"
    return f"Surfaces last if nobody decides: {n}, {title}"


def who_parts(L, data):
    """Whose plan, when it was asked for (with the request's link), and as of when."""
    plan = text(data.get("plan"))
    parts = [(L["own"] if plan in ("", "own") else L["of"].format(plan=plan), "")]
    asked = data.get("asked") or {}
    if text(asked.get("at")):
        parts.append((L["asked_at"].format(at=text(asked["at"])), asked.get("link")))
    parts.append((L["as_of"].format(at=text(data.get("as_of"))), ""))
    return parts


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

    def count(self, where, key, rows, limit):
        if len(rows) > limit:
            self.warnings.append(f"{where} {key}: {len(rows)} lines, budget {limit}")


# --- data ---------------------------------------------------------------------------------------

def text(v):
    return v.strip() if isinstance(v, str) else ""


def looked(item):
    v = item.get("looked")
    return [text(x) for x in v if text(x)] if isinstance(v, list) else ([text(v)] if text(v) else [])


def safe_link(v):
    v = text(v)
    return v if re.match(r"https?://", v) else ""


def is_box(box):
    return (isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box)
            and all(0 <= v <= 1 for v in box) and box[2] > 0 and box[3] > 0
            and box[0] + box[2] <= 1.001 and box[1] + box[3] <= 1.001)


def check_evidence(where, ev):
    if not isinstance(ev, dict) or ev.get("kind") not in EVIDENCE_KINDS:
        raise BadData(f"{where}: kind must be one of {', '.join(EVIDENCE_KINDS)}")
    marks = ev.get("marks") or []
    if (marks or ev.get("crop")) and not text(ev.get("image")):
        raise BadData(f"{where}: marks and crop need an image")
    for m in marks if isinstance(marks, list) else [None]:
        if not (isinstance(m, dict) and is_box(m.get("box"))):
            raise BadData(f"{where}: a mark is {{box: [x, y, w, h]}}, fractions of the capture between 0 and 1")
    if ev.get("crop") is not None and not is_box(ev["crop"]):
        raise BadData(f"{where}: crop is [x, y, w, h], fractions of the capture between 0 and 1")


def need_list(where, v, keys=()):
    if v is None:
        return
    if not isinstance(v, list) or not all(
            (isinstance(x, dict) and all(text(x.get(k)) for k in keys)) if keys else (isinstance(x, str) and x.strip())
            for x in v):
        raise BadData(f"{where} must be a list" + (f" of {{{', '.join(keys)}}}" if keys else " of lines"))


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
        for key in ("title", "problem", "recommend", "ask"):
            if not text(item.get(key)):
                raise BadData(f"item {i}: missing `{key}`")
        for j, ev in enumerate(item.get("evidence") or [], 1):
            check_evidence(f"item {i} evidence {j}", ev)
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
            else:
                check_evidence(where, m)
        need_list(f"item {i} `where`", item.get("where"), ("name",))
        need_list(f"item {i} `options`", item.get("options"))
        if item.get("looked") is not None and not isinstance(item["looked"], (str, list)):
            raise BadData(f"item {i}: `looked` is a sentence or a list of them")
        paste = item.get("paste")
        if paste is not None and not (isinstance(paste, dict) and text(paste.get("text"))):
            raise BadData(f"item {i}: `paste` is {{to, text}}")
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
    prev = data.get("previous")
    if prev is not None:
        rows = prev.get("items") if isinstance(prev, dict) else None
        if not isinstance(rows, list) or not all(
                isinstance(r, dict) and text(r.get("title")) and r.get("status") in PREVIOUS_STATUS for r in rows):
            raise BadData(f"`previous.items` must be a list of {{title, status, note}}, status one of {', '.join(PREVIOUS_STATUS)}")
    brief = data.get("brief")
    if brief is not None:
        if not isinstance(brief, dict) or not text(brief.get("what")):
            raise BadData("`brief` needs `what`")
        flow = brief.get("flow")
        if not isinstance(flow, list) or not flow or not all(
                isinstance(x, dict) and text(x.get("label")) and text(x.get("text")) for x in flow):
            raise BadData("`brief.flow` must be a list of {label, text}")
        for j, step in enumerate(flow, 1):
            if text(step.get("image")) or step.get("crop"):
                check_evidence(f"brief flow {j}", dict(step, kind="design"))
        need_list("`brief.changes`", brief.get("changes"), ("what", "now", "after"))
        need_list("`brief.in`", brief.get("in"))
        need_list("`brief.out`", brief.get("out"))
        need_list("`brief.decided`", brief.get("decided"), ("what",))
        need_list("`brief.waiting`", brief.get("waiting"))
        need_list("`brief.links`", brief.get("links"), ("name",))
        work = brief.get("work")
        if work is not None:
            if not isinstance(work, dict) or not text(work.get("summary")):
                raise BadData("`brief.work` is {summary, items}")
            need_list("`brief.work.items`", work.get("items"), ("name",))
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
        for key in ("flow", "changes", "in", "out", "decided", "waiting", "links"):
            b.count("brief", key, brief.get(key) or [], BRIEF_LIMITS[key])
        for x in brief.get("flow") or []:
            b.cell("brief flow", "label", text(x.get("label")))
            b.cell("brief flow", "step", text(x.get("text")))
        for x in brief.get("changes") or []:
            for k in ("what", "now", "after"):
                b.cell("brief changes", "change", text(x.get(k)))
        for key in ("in", "out"):
            for x in brief.get(key) or []:
                b.cell(f"brief {key}", "scope", text(x))
        if brief.get("work"):
            b.cell("brief work", "work", text(brief["work"].get("summary")))
        for x in brief.get("decided") or []:
            b.cell("brief decided", "decided", text(x.get("what")))
        for x in brief.get("waiting") or []:
            b.cell("brief waiting", "waiting", text(x))
    for i, item in enumerate(data["items"], 1):
        where = f"item {i}"
        for key in ("title", "area", "recommend", "problem", "ask", "reason", "if_left", "then"):
            b.cell(where, key, text(item.get(key)))
        b.cell(where, "owner", text(item.get("owner")), prose=False)
        locs = item.get("where") or []
        if len(locs) > WHERE:
            b.warnings.append(f"{where} where: {len(locs)}, budget {WHERE}")
        for w in locs:
            b.cell(where, "source", text(w.get("name")), prose=False)
        options = item.get("options") or []
        if len(options) > OPTIONS:
            b.warnings.append(f"{where} options: {len(options)}, budget {OPTIONS}")
        for o in options:
            b.cell(where, "option", text(o))
        if item.get("paste"):
            b.cell(where, "paste", text(item["paste"].get("text")), prose=False)
            if options:
                b.warnings.append(f"{where} paste: a paste beside options decides for the author; keep one or the other")
        shown = item.get("evidence") or []
        if len(shown) > SHOWN_EVIDENCE:
            b.warnings.append(f"{where} evidence: {len(shown)} on the card, budget {SHOWN_EVIDENCE}; move the rest to `more`")
        for ev in shown + [m for m in item.get("more") or [] if m.get("kind")]:
            if len(ev.get("marks") or []) > MARKS:
                b.warnings.append(f"{where} marks: {len(ev['marks'])} on one capture, budget {MARKS}")
        for ev in shown:
            b.cell(where, "quote", text(ev.get("quote")), prose=False)
            b.cell(where, "source", text(ev.get("source")), prose=False)
        for j, m in enumerate(item.get("more") or [], 1):
            if text(m.get("note")):
                b.style(f"{where} more {j}", "note", text(m["note"]))
        for x in looked(item):
            b.style(where, "looked", x)
    for r in (data.get("previous") or {}).get("items") or []:
        b.cell("previous", "what", text(r.get("title")), prose=False)
        b.cell("previous", "why", text(r.get("note")))
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
:root{--fg:#1d1d1f;--muted:#6b6b70;--line:#e4e4e7;--bg:#fff;--soft:#f5f5f6;--fix:#b42318;--fix-bg:#fef3f2;--op:#175cd3;--op-bg:#eff8ff;--ok:#067647;--ok-bg:#ecfdf3;--mark:#e5484d}
@media (prefers-color-scheme:dark){:root{--fg:#ececf1;--muted:#a1a1aa;--line:#34343a;--bg:#16161a;--soft:#202026;--fix:#fda29b;--fix-bg:#3a1714;--op:#84caff;--op-bg:#102a43;--ok:#75e0a7;--ok-bg:#0f2e1f;--mark:#ff6369}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",sans-serif;word-break:keep-all;overflow-wrap:anywhere}
main{max-width:800px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:21px;line-height:1.35;margin:0 0 4px}
h2{font-size:15px;margin:30px 0 10px;color:var(--muted)}
a{color:var(--op)}
.who{margin:0 0 6px;color:var(--muted);font-size:14px}
.asked{margin:0 0 18px}
.box{border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 18px}
.box h2{margin:0 0 10px}
.rows{display:grid;grid-template-columns:6.5em 1fr;gap:10px 14px;margin:0}
.rows>dt{color:var(--muted);font-size:14px;font-weight:600}
.rows>dd{margin:0;min-width:0}
.lead{font-weight:600}
table.kv,table.grid{width:100%;border-collapse:separate;border-spacing:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:14.5px;margin:0 0 6px}
table.kv>tbody>tr>th,table.kv>tbody>tr>td,table.grid th,table.grid td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
table.kv>tbody>tr:last-child>th,table.kv>tbody>tr:last-child>td,table.grid tbody tr:last-child td{border-bottom:0}
table.kv>tbody>tr>th{width:6.8em;background:var(--soft);color:var(--muted);font-weight:600;white-space:nowrap}
table.kv>tbody>tr>td{min-width:0}
table.grid thead th{background:var(--soft);color:var(--muted);font-weight:600;white-space:nowrap}
table.grid tbody tr[data-href]{cursor:pointer}
table.grid tbody tr[data-href]:hover td{background:var(--soft)}
table.grid td.k,table.grid td.c{white-space:nowrap;color:var(--muted)}
.car .steps{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.car .steps button{font:inherit;font-size:13px;padding:4px 10px;border-radius:999px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}
.car .steps button[aria-current=true]{background:var(--op);border-color:var(--op);color:#fff}
.car .slide{margin:0 0 12px;text-align:center}
.car.js .slide{display:none;margin:0}
.car.js .slide.on{display:block}
.car .slide .frame:not(.crop) img{max-height:440px;width:auto}
.car .slide .frame.crop{margin:0 auto}
.car .slide figcaption{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;text-align:left;margin-top:6px;font-size:14px}
.car .pos{color:var(--muted);font-size:13px}
.car .nav{display:none;gap:6px}
.car.js .nav{display:flex}
.car button.sbtn{font:inherit;font-size:13px;padding:2px 10px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}
[data-zoom]:hover{outline:2px solid var(--op);outline-offset:1px}
@media print{.car.js .slide{display:block}.car .nav,.car .steps{display:none}}
[data-zoom]{cursor:zoom-in}
.hint{font-size:13px;color:var(--muted);margin:6px 0 0}
#viewer{position:fixed;inset:0;z-index:10;background:rgba(10,10,12,.97);display:none;flex-direction:column}
#viewer .vf{position:relative;max-width:100%}
#viewer .vf.crop{overflow:hidden;width:min(100%,960px);border-radius:4px;background:#fff}
#viewer .vf.crop img{position:absolute;max-width:none;border-radius:0}
#viewer .vf .mk{pointer-events:none}
#viewer.on{display:flex}
#viewer .bar{display:flex;gap:8px;align-items:center;padding:10px 14px;color:#fff;font-size:14px}
#viewer .bar .cap{flex:1;min-width:0}
#viewer .bar a{color:#9cc7ff}
#viewer button{font:inherit;color:#fff;background:rgba(255,255,255,.12);border:0;border-radius:6px;padding:6px 12px;cursor:pointer}
#viewer .stage{flex:1;overflow:auto;display:flex;align-items:flex-start;justify-content:center;padding:0 14px 14px}
#viewer img{display:block;max-width:100%;height:auto;background:#fff;border-radius:4px;cursor:zoom-out}
.strip figcaption{font-size:13px;margin-top:4px;line-height:1.4}
.strip figcaption b{display:block}
.chain{color:var(--muted)}
.mini{border-collapse:collapse;width:100%;font-size:14px}
.mini th,.mini td{text-align:left;vertical-align:top;padding:4px 8px 4px 0;border-bottom:1px solid var(--line)}
.mini th{color:var(--muted);font-weight:600;white-space:nowrap}
.scope{display:grid;grid-template-columns:max-content 1fr;gap:2px 10px}
.verdict{padding:14px 16px;border-radius:10px;background:var(--fix-bg);font-size:19px;font-weight:700;margin:0 0 6px}
.verdict.ok{background:var(--ok-bg)}
.verdict p{margin:4px 0 0;font-size:14px;font-weight:400}
.decisions{list-style:none;margin:0;padding:0}
.decisions li{display:grid;grid-template-columns:1.6em 1fr auto;gap:2px 8px;padding:10px 0;border-bottom:1px solid var(--line)}
.decisions .k{color:var(--muted);font-weight:600}
.decisions .t{font-weight:600}
.decisions .r{grid-column:2/4}
.decisions .r b{color:var(--ok);font-weight:600;margin-right:6px}
.decisions .o{color:var(--muted);font-size:13px;white-space:nowrap}
.answer{margin:10px 0 0;padding:10px 12px;background:var(--soft);border-radius:8px;font-size:14px}
.n{color:var(--muted);font-size:13px;margin-left:4px}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600;white-space:nowrap}
.tag{display:inline-block;font-size:12px;font-weight:600;line-height:20px;padding:0 8px;border-radius:999px;white-space:nowrap;color:var(--muted);background:var(--soft)}
.tag.fix{color:var(--fix);background:var(--fix-bg)}
.tag.opinion{color:var(--op);background:var(--op-bg)}
.card{border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
.card header{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px;color:var(--muted)}
.card h3{font-size:17px;line-height:1.4;margin:6px 0 4px}
.card .where{margin:0 0 12px;font-size:13px;color:var(--muted)}
.cells{display:grid;grid-template-columns:5.5em 1fr;gap:10px 12px;margin:0}
.cells dt{color:var(--muted);font-size:14px;font-weight:600}
.cells dd{margin:0}
.rec{font-weight:600}
.why{display:block;color:var(--muted);font-size:14px;font-weight:400}
.ev+.ev{margin-top:10px}
.src{font-size:13px;color:var(--muted)}
blockquote{margin:4px 0 0;padding:6px 12px;border-left:3px solid var(--line);background:var(--soft);border-radius:0 6px 6px 0;white-space:pre-wrap}
pre{margin:4px 0 0;padding:8px 12px;background:var(--soft);border-radius:6px;overflow-x:auto;font-size:13px;line-height:1.5}
.shot{margin:0 0 14px}
.frame{position:relative;display:inline-block;max-width:100%;vertical-align:top}
.frame img{display:block;max-width:100%;border:1px solid var(--line);border-radius:6px}
.frame.crop{display:block;overflow:hidden;border:1px solid var(--line);border-radius:6px}
.frame.crop img{position:absolute;max-width:none;border:0;border-radius:0}
.mk{position:absolute;border:2px solid var(--mark);border-radius:4px}
.mk b{position:absolute;left:-11px;top:-11px;width:20px;height:20px;border-radius:50%;background:var(--mark);color:#fff;font-size:12px;line-height:20px;text-align:center}
.shot figcaption{margin-top:4px}
.paste{margin-top:8px;padding:8px 12px;border:1px dashed var(--line);border-radius:6px;white-space:pre-wrap}
ul.opts{margin:0;padding-left:1.1em}
details{margin-top:10px;font-size:14px}
summary{cursor:pointer;color:var(--muted);font-weight:600}
details>*:not(summary){margin-top:8px}
.note{margin:8px 0 0}
.caption{font-size:13px;color:var(--muted);margin:10px 0 4px}
ul.plain{margin:0;padding-left:1.2em}
h3.sub{font-size:14px;margin:14px 0 6px;color:var(--muted)}
.foot{display:grid;grid-template-columns:max-content 1fr;gap:2px 14px;margin:14px 0 0;color:var(--muted);font-size:13px}
.foot dd{margin:0}
@media (max-width:560px){table.kv>tbody>tr>th,table.kv>tbody>tr>td{display:block;width:auto}table.kv>tbody>tr>th{border-bottom:0;padding-bottom:2px}table.kv>tbody>tr>td{padding-top:4px}.rows,.cells{grid-template-columns:1fr;gap:2px}.rows>dd,.cells dd{margin-bottom:10px}.decisions li{grid-template-columns:1.6em 1fr}.decisions .o{grid-column:2}}
"""

TICKET_URL = ""

CAROUSEL = """<script>(function(){
[].slice.call(document.querySelectorAll('[data-car]')).forEach(function(c){
var slides=[].slice.call(c.querySelectorAll('.slide')),steps=[].slice.call(c.querySelectorAll('[data-go]')),at=0;
function show(i){at=(i+slides.length)%slides.length;slides.forEach(function(s,j){s.classList.toggle('on',j===at);});
steps.forEach(function(b,j){b.setAttribute('aria-current',j===at?'true':'false');});}
c.classList.add('js');show(0);
c.addEventListener('click',function(e){var t=e.target.closest('button');if(!t)return;
if(t.dataset.go)show(+t.dataset.go);else if(t.dataset.step)show(at+(+t.dataset.step));
else if(t.hasAttribute('data-zoomit')){var im=slides[at].querySelector('[data-zoom]');if(im)im.click();}});});
[].slice.call(document.querySelectorAll('tr[data-href]')).forEach(function(r){r.addEventListener('click',function(e){
if(e.target.closest('a'))return;location.hash=r.dataset.href;});});
})();</script>"""

# Every capture on the page opens here at full size, in order, without leaving the report.
VIEWER = """<div id="viewer" role="dialog" aria-modal="true"><div class="bar"><button type="button" data-act="prev">{prev}</button>
<button type="button" data-act="next">{next}</button><span class="cap"></span>
<button type="button" data-act="whole" data-whole="{whole}" data-part="{part}"></button><a class="go" target="_blank" rel="noopener">{open}</a>
<button type="button" data-act="close">{close}</button></div><div class="stage"><div class="vf"><img alt=""></div></div></div>
<script>(function(){{
var v=document.getElementById('viewer'),img=v.querySelector('img'),vf=v.querySelector('.vf'),cap=v.querySelector('.cap'),go=v.querySelector('.go'),wb=v.querySelector('[data-act=whole]');
var items=[].slice.call(document.querySelectorAll('[data-zoom]')),at=0,whole=false;
function frame(){{var c=(items[at].dataset.crop||'').split(',').map(Number);var on=c.length===4&&!whole;wb.style.display=c.length===4?'':'none';
wb.textContent=whole?wb.dataset.part:wb.dataset.whole;vf.className=on?'vf crop':'vf';
if(!on){{vf.style.aspectRatio='';img.style.cssText='';return;}}
var fit=function(){{vf.style.aspectRatio=(c[2]*img.naturalWidth)+'/'+(c[3]*img.naturalHeight);
img.style.cssText='width:'+(100/c[2])+'%;left:'+(-c[0]/c[2]*100)+'%;top:'+(-c[1]/c[3]*100)+'%';}};
if(img.complete&&img.naturalWidth)fit();else img.onload=fit;}}
function marks(){{[].slice.call(vf.querySelectorAll('.mk')).forEach(function(m){{m.remove();}});
var c=(items[at].dataset.crop||'').split(',').map(Number);if(c.length!==4||whole)c=[0,0,1,1];
(items[at].dataset.marks||'').split(';').filter(Boolean).forEach(function(b,i){{b=b.split(',').map(Number);
var m=document.createElement('span');m.className='mk';m.innerHTML='<b>'+(i+1)+'</b>';
m.style.cssText='left:'+((b[0]-c[0])/c[2]*100)+'%;top:'+((b[1]-c[1])/c[3]*100)+'%;width:'+(b[2]/c[2]*100)+'%;height:'+(b[3]/c[3]*100)+'%';vf.appendChild(m);}});}}
function src(el){{if(el.tagName==='IMG')return el.src;var m=getComputedStyle(el).backgroundImage.match(/url\\(["']?(.*?)["']?\\)/);return m?m[1]:'';}}
function show(i){{at=(i+items.length)%items.length;var el=items[at];img.src=src(el);cap.textContent=(at+1)+' / '+items.length+'  '+(el.dataset.cap||'');
if(el.dataset.link){{go.href=el.dataset.link;go.style.display='';}}else{{go.style.display='none';}}whole=false;frame();marks();v.classList.add('on');v.querySelector('.stage').scrollTop=0;}}
function close(){{v.classList.remove('on');}}
items.forEach(function(el,i){{el.addEventListener('click',function(e){{e.preventDefault();show(i);}});}});
v.addEventListener('click',function(e){{var a=e.target.dataset&&e.target.dataset.act;if(a==='prev')show(at-1);else if(a==='next')show(at+1);else if(a==='whole'){{whole=!whole;frame();marks();}}else if(a==='close'||e.target===v||e.target===img)close();}});
document.addEventListener('keydown',function(e){{if(!v.classList.contains('on'))return;if(e.key==='Escape')close();else if(e.key==='ArrowLeft')show(at-1);else if(e.key==='ArrowRight')show(at+1);}});
}})();</script>"""


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


def png_size(p):
    head = p.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise BadData(f"crop needs a PNG capture: {p.name}")
    return struct.unpack(">II", head[16:24])


def html_table(t, cls=""):
    head = "".join(f"<th>{E(h)}</th>" for h in t.get("head") or [])
    rows = "".join("<tr>" + "".join(f"<td>{E(c)}</td>" for c in r) + "</tr>" for r in t.get("rows") or [])
    cap = f'<p class="caption">{E(t.get("caption"))}</p>' if text(t.get("caption")) else ""
    return f'{cap}<div class="tw"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def html_source(L, ev):
    inferred = f' <span class="tag">{E(L["inferred"])}</span>' if ev.get("inferred") else ""
    return f'<span class="tag">{E(L["kinds"][ev["kind"]])}</span> {a(ev.get("source") or "", ev.get("link"))}{inferred}'


def html_frame(base, ev):
    p = image_path(base, ev)
    cx, cy, cw, ch = ev.get("crop") or [0, 0, 1, 1]
    marks = "".join(
        f'<span class="mk" style="left:{(m["box"][0] - cx) / cw * 100:.2f}%;top:{(m["box"][1] - cy) / ch * 100:.2f}%;'
        f'width:{m["box"][2] / cw * 100:.2f}%;height:{m["box"][3] / ch * 100:.2f}%"><b>{j}</b></span>'
        for j, m in enumerate(ev.get("marks") or [], 1))
    cap = text(ev.get("source") or ev.get("label"))
    crop = ",".join(str(v) for v in ev.get("crop") or [])
    boxes = ";".join(",".join(str(v) for v in m["box"]) for m in ev.get("marks") or [])
    img = (f'<img src="{data_uri(p)}" alt="{E(cap, False)}" data-zoom data-crop="{crop}" data-marks="{boxes}" data-cap="{E(cap, False)}" '
           f'data-link="{E(safe_link(ev.get("link")), False)}"')
    if ev.get("crop"):
        w, h = png_size(p)
        return (f'<div class="frame crop" style="width:{cw * w:.0f}px;aspect-ratio:{cw * w:.0f}/{ch * h:.0f}">'
                f'{img} style="width:{100 / cw:.2f}%;left:{-cx / cw * 100:.2f}%;top:{-cy / ch * 100:.2f}%">{marks}</div>')
    return f'<div class="frame">{img}>{marks}</div>'


def html_figure(L, base, ev):
    return f'<figure class="shot">{html_frame(base, ev)}<figcaption class="src">{html_source(L, ev)}</figcaption></figure>'


def html_evidence(L, base, ev):
    if text(ev.get("image")):
        return html_figure(L, base, ev)
    out = f'<div class="ev"><div class="src">{html_source(L, ev)}</div>'
    q = text(ev.get("quote"))
    if q:
        out += f"<pre><code>{E(q, False)}</code></pre>" if ev["kind"] == "code" else f"<blockquote>{E(q)}</blockquote>"
    return out + "</div>"


def html_more(L, base, entry):
    if "table" in entry:
        return html_table(entry["table"])
    if "note" in entry:
        inferred = f'<span class="tag">{E(L["inferred"])}</span> ' if entry.get("inferred") else ""
        return f'<p class="note">{inferred}{E(entry["note"])}</p>'
    return html_evidence(L, base, entry)


def kv(rows):
    return '<table class="kv"><tbody>' + "".join(f"<tr><th>{E(k)}</th><td>{v}</td></tr>" for k, v in rows) + "</tbody></table>"


def html_flow(L, base, flow):
    """The flow as a carousel: the steps by name, one screen at a time at the column's width."""
    if not any(text(x.get("image")) for x in flow):
        return ('<span class="chain">' + " › ".join(E(x["label"]) for x in flow) + "</span>"
                + '<ul class="opts">' + "".join(f"<li>{E(x['text'])}</li>" for x in flow) + "</ul>")
    steps = "".join(f'<button type="button" data-go="{j}">{j + 1}. {E(x["label"])}</button>' for j, x in enumerate(flow))
    slides = []
    for j, x in enumerate(flow):
        pic = html_frame(base, dict(x, source=f'{text(x["label"])}: {text(x["text"])}')) if text(x.get("image")) else ""
        tools = ""
        if pic:
            tools += f'<button type="button" class="sbtn" data-zoomit>{E(L["zoom"])}</button>'
        if safe_link(x.get("link")):
            tools += f'<a class="src" href="{E(safe_link(x["link"]), False)}">{E(L["open_design"])}</a>'
        slides.append(f'<figure class="slide" data-i="{j}">{pic}<figcaption><span class="pos">{j + 1} / {len(flow)}</span>'
                      f'<b>{E(x["label"])}</b><span>{E(x["text"])}</span>{tools}</figcaption></figure>')
    nav = (f'<div class="nav"><button type="button" class="sbtn" data-step="-1">‹ {E(L["prev"])}</button>'
           f'<button type="button" class="sbtn" data-step="1">{E(L["next"])} ›</button></div>')
    return f'<div class="car" data-car><div class="steps">{steps}</div>{"".join(slides)}{nav}</div>'


def html_brief(L, base, brief):
    rows = [(L["b_what"], f'<span class="lead">{E(brief["what"])}</span>')]
    if text(brief.get("why")):
        rows.append((L["b_why"], E(brief["why"])))
    rows.append((L["b_flow"], html_flow(L, base, brief["flow"])))
    if brief.get("changes"):
        rows.append((L["b_changes"], html_table({"head": [L["c_what"], L["c_now"], L["c_after"]],
                                                 "rows": [[x["what"], x["now"], x["after"]] for x in brief["changes"]]}, "mini")))
    scope = "".join(
        f'<span class="src">{E(text(brief.get(k + "_label")) or L["b_" + k])}</span><span>{"<br>".join(E(x) for x in brief[k])}</span>'
        for k in ("in", "out") if brief.get(k))
    if scope:
        rows.append((L["b_scope"], f'<div class="scope">{scope}</div>'))
    work = brief.get("work")
    if work:
        body = E(work["summary"])
        if work.get("items"):
            body += (f'<details><summary>{E(L["b_work_n"].format(n=len(work["items"])))}</summary>'
                     f'<table class="mini"><thead><tr><th>{E(L["w_name"])}</th><th>{E(L["w_owner"])}</th><th>{E(L["w_status"])}</th></tr></thead><tbody>'
                     + "".join(f"<tr><td>{a(x['name'], x.get('link'))}</td><td>{E(x.get('owner'))}</td><td>{E(x.get('status'))}</td></tr>"
                               for x in work["items"]) + "</tbody></table></details>")
        rows.append((L["b_work"], body))
    if brief.get("decided"):
        rows.append((L["b_decided"], '<ul class="opts">' + "".join(
            f"<li>{E(x['what'])}" + (f' <span class="src">{a(x.get("when") or "", x.get("link"))}</span>' if text(x.get("when")) else "")
            + "</li>" for x in brief["decided"]) + "</ul>"))
    if brief.get("waiting"):
        rows.append((L["b_waiting"], '<ul class="opts">' + "".join(f"<li>{E(x)}</li>" for x in brief["waiting"]) + "</ul>"))
    if brief.get("links"):
        rows.append((L["b_links"], ", ".join(a(x.get("name"), x.get("link")) for x in brief["links"])))
    return f'<h2>{E(L["brief"])}</h2>' + kv(rows)


def html_card(L, base, k, item):
    out = [f'<article class="card" id="i{k}"><header><b>{k}</b>'
           f'<span class="tag {item["kind"]}">{E(L[item["kind"]])}</span>']
    if text(item.get("area")):
        out.append(f"<span>{E(item['area'])}</span>")
    out.append(f'</header><h3>{E(item["title"])}</h3>')
    if item.get("where"):
        out.append(f'<p class="where">{E(L["where"])}: ' + ", ".join(a(w.get("name"), w.get("link")) for w in item["where"]) + "</p>")
    evidence = item.get("evidence") or []
    shots = [ev for ev in evidence if text(ev.get("image"))]
    words = [ev for ev in evidence if not text(ev.get("image"))]
    out += [html_figure(L, base, ev) for ev in shots]
    rows = [(L["problem"], E(item["problem"]))]
    rec = f'<span class="rec">{E(item["ask"])}</span>'
    if text(item.get("reason")):
        rec += f'<span class="why">{E(L["reason"])}: {E(item["reason"])}</span>'
    paste = item.get("paste")
    if paste:
        to = f", {E(paste.get('to'))}" if text(paste.get("to")) else ""
        rec += f'<div class="src" style="margin-top:8px">{E(L["paste"])}{to}</div><div class="paste">{E(paste["text"], False)}</div>'
    rows.append((L["ask"], rec))
    options = item.get("options") or []
    if options:
        rows.append((L["options"], '<ul class="opts">' + "".join(f"<li>{E(o)}</li>" for o in options) + "</ul>"))
    if text(item.get("if_left")):
        rows.append((L["if_left"], E(item["if_left"])))
    if words or not evidence:
        rows.append((L["evidence"], "".join(html_evidence(L, base, ev) for ev in words)
                     or f'<span class="tag fix">{E(L["needed"])}</span>'))
    if text(item.get("then")):
        who = f"{E(item['owner'])}: " if text(item.get("owner")) else ""
        rows.append((L["then"], f"{who}{E(item['then'])}"))
    out.append(kv(rows))
    more = item.get("more") or []
    if more:
        out.append(f'<details><summary>{E(L["more"])} ({len(more)})</summary>'
                   + "".join(html_more(L, base, m) for m in more) + "</details>")
    if looked(item):
        out.append(f'<details><summary>{E(L["looked"])}</summary><ul class="plain">'
                   + "".join(f"<li>{E(x)}</li>" for x in looked(item)) + "</ul></details>")
    return "".join(out) + "</article>"


def render_html(data, L, lang, base):
    items = data["items"]
    own = text(data.get("plan")) in ("", "own")
    fixes = sum(1 for i in items if i["kind"] == "fix")
    out = [f'<!doctype html><html lang="{E(lang)}"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{E(data["title"], False)}</title><style>{CSS}</style></head><body><main>',
           f'<h1>{E(data["title"])}</h1>',
           '<p class="who">' + ", ".join(a(t, link) for t, link in who_parts(L, data)) + "</p>"]
    note = text((data.get("asked") or {}).get("note"))
    if note:
        out.append(f'<p class="asked"><span class="tag">{E(L["asked"])}</span> {E(note)}</p>')
    if data.get("brief"):
        out.append(html_brief(L, base, data["brief"]))

    out.append(f'<div class="verdict{"" if fixes else " ok"}">{E(verdict(lang, own, fixes, len(items) - fixes))}')
    n = data.get("surfaces_last")
    if n and not own:
        out.append(f"<p>{E(surfaces_line(lang, n, items[n - 1]['title']))}</p>")
    prev = data.get("previous")
    if prev and prev.get("items"):
        out.append(f'<p><a href="#prev">{E(previous_line(L, prev), False)}</a></p>')
    g = grounds(L, data)
    if g:
        out.append(f'<p><a href="#nc">{E(g, False)}</a></p>')
    out.append("</div>")

    if items:
        out.append(f'<h2>{E(L["decisions"])}</h2><div class="tw"><table class="grid"><thead><tr><th>#</th>'
                   f'<th>{E(L["d_title"])}</th><th>{E(L["recommend"])}</th><th>{E(L["d_others"])}</th><th>{E(L["then"])}</th>'
                   '</tr></thead><tbody>')
        for k, item in enumerate(items, 1):
            others = len(item.get("options") or [])
            tag = f' <span class="tag opinion">{E(L["opinion"])}</span>' if item["kind"] == "opinion" else ""
            out.append(f'<tr data-href="#i{k}"><td class="k">{k}</td><td><a href="#i{k}">{E(item["title"], False)}</a>{tag}</td>'
                       f'<td>{E(item["recommend"])}</td><td class="c">{others if others else E(L["none"])}</td>'
                       f'<td class="c">{E(item.get("owner"))}</td></tr>')
        out.append(f'</tbody></table></div><p class="answer">{E(L["answer_own" if own else "answer_colleague"])}</p>'
                   f'<p class="caption">{E(L["gloss"])}</p>')
        out.append(f'<h2>{E(L["evidence_h"])}</h2>')
        out += [html_card(L, base, k, item) for k, item in enumerate(items, 1)]

    before = [E(x) for x in data.get("before_handover") or [] if text(x)]
    unseen = [E(x) for x in data.get("not_checked") or [] if text(x)]
    if data.get("unread"):
        unseen.insert(0, f'{E(L["unread"])}: {E(", ".join(text(u) for u in data["unread"]))}')
    if before or unseen:
        out.append(f'<h2>{E(L["open_h"])}</h2>')
        if before:
            out.append(f'<h3 class="sub">{E(L["before"])}</h3><ul class="plain">' + "".join(f"<li>{x}</li>" for x in before) + "</ul>")
        if unseen:
            out.append(f'<h3 class="sub" id="nc">{E(L["not_checked"])}</h3><ul class="plain">' + "".join(f"<li>{x}</li>" for x in unseen) + "</ul>")

    notes = []
    if prev and prev.get("items"):
        notes.append(f'<details id="prev"><summary>{E(L["earlier_n"].format(n=len(prev["items"])))}</summary>'
                     + html_table({"head": ["#", L["earlier"], L["status"], L["note"]],
                                   "rows": [[k, r.get("title"), L["statuses"][r["status"]], r.get("note")]
                                            for k, r in enumerate(prev["items"], 1)]}) + "</details>")
    left = data.get("left_out") or []
    if left:
        notes.append(f'<details><summary>{E(L["left_out"])} ({len(left)})</summary>' + html_table(
            {"head": [L["what"], L["why"]], "rows": [[r.get("what"), r.get("why")] for r in left]}) + "</details>")
    srcs = data.get("sources") or []
    if srcs:
        notes.append(f'<details><summary>{E(L["sources"])} ({len(srcs)})</summary><ul class="plain">'
                     + "".join(f"<li>{a(s.get('name') or '', s.get('link'))}"
                               + (f", {E(s.get('note'))}" if text(s.get("note")) else "") + "</li>" for s in srcs)
                     + "</ul></details>")
    foot = []
    if text(data.get("reviewer")):
        foot.append((L["reviewer"], E(data["reviewer"])))
    latest = data.get("latest") or {}
    if text(latest.get("name")):
        foot.append((L["latest"], a(latest["name"], latest.get("link")) + (f", {E(latest.get('at'))}" if text(latest.get("at")) else "")))
    if foot:
        notes.append('<dl class="foot">' + "".join(f"<dt>{E(k)}</dt><dd>{v}</dd>" for k, v in foot) + "</dl>")
    if notes:
        out.append(f'<h2>{E(L["notes_h"])}</h2>' + "".join(notes))
    out.append(CAROUSEL)
    out.append(VIEWER.format(close=E(L["close"]), prev=E(L["prev"]), next=E(L["next"]), open=E(L["open_design"]),
                             whole=E(L["whole"]), part=E(L["part"])))
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
        if ev.get("marks"):
            lines.append(f"{indent}  {L['markdown_marks']}")
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
    out = [f"# {text(data['title'])}", "", ", ".join(md_link(t, link) for t, link in who_parts(L, data))]
    note = text((data.get("asked") or {}).get("note"))
    if note:
        out += ["", f"`{L['asked']}` {md_text(note)}"]
    brief = data.get("brief")
    if brief:
        out += ["", f"## {L['brief']}", "", f"- **{L['b_what']}** {md_text(brief['what'])}"]
        if text(brief.get("why")):
            out.append(f"- **{L['b_why']}** {md_text(brief['why'])}")
        out.append(f"- **{L['b_flow']}** " + " › ".join(text(x["label"]) for x in brief["flow"]))
        for j, x in enumerate(brief["flow"], 1):
            out.append(f"  {j}. **{text(x['label'])}** {md_text(x['text'])}")
            if text(x.get("image")):
                out.append(f"     ![{text(x['label'])}]({assets(image_path(base, x))})")
        if brief.get("changes"):
            out += ["", f"**{L['b_changes']}**", ""] + md_table(
                {"head": [L["c_what"], L["c_now"], L["c_after"]], "rows": [[x["what"], x["now"], x["after"]] for x in brief["changes"]]}) + [""]
        for k in ("in", "out"):
            if brief.get(k):
                out.append(f"- **{text(brief.get(k + '_label')) or L['b_' + k]}** " + "; ".join(md_text(x) for x in brief[k]))
        work = brief.get("work")
        if work:
            out.append(f"- **{L['b_work']}** {md_text(work['summary'])}")
            out += [f"  - {md_link(x['name'], x.get('link'))}, {text(x.get('owner'))}, {text(x.get('status'))}" for x in work.get("items") or []]
        if brief.get("decided"):
            out.append(f"- **{L['b_decided']}**")
            out += [f"  - {md_text(x['what'])}" + (f" ({md_link(x.get('when') or '', x.get('link'))})" if text(x.get("when")) else "")
                    for x in brief["decided"]]
        if brief.get("waiting"):
            out.append(f"- **{L['b_waiting']}** " + "; ".join(md_text(x) for x in brief["waiting"]))
        if brief.get("links"):
            out.append(f"- **{L['b_links']}** " + ", ".join(md_link(x.get("name"), x.get("link")) for x in brief["links"]))
    out += ["", f"> **{verdict(lang, own, fixes, len(items) - fixes)}**"]
    n = data.get("surfaces_last")
    if n and not own:
        out += [">", f"> {surfaces_line(lang, n, items[n - 1]['title'])}"]
    prev = data.get("previous")
    if prev and prev.get("items"):
        out += [">", f"> {previous_line(L, prev)}"]
    g = grounds(L, data)
    if g:
        out += [">", f"> {g}"]
    if items:
        out += ["", f"## {L['decisions']}", ""]
        for k, item in enumerate(items, 1):
            others = len(item.get("options") or [])
            o = L["others_n"].format(n=others) if others else L["others_none"]
            out.append(f"{k}. [{md_text(item['title'])}](#{k}) ({o})" + (f" `{L['opinion']}`" if item["kind"] == "opinion" else ""))
            out.append(f"   **{L['recommend']}** {md_text(item['recommend'])}")
        out += ["", L["answer_own" if own else "answer_colleague"], "", f"*{L['gloss']}*", "", f"## {L['evidence_h']}"]
    for k, item in enumerate(items, 1):
        out += ["", f'<a id="{k}"></a>', f"### {k}. {text(item['title'])}", "",
                f"`{L[item['kind']]}`" + (f" `{text(item['area'])}`" if text(item.get("area")) else ""), ""]
        if item.get("where"):
            out += [f"{L['where']}: " + ", ".join(md_link(w.get("name"), w.get("link")) for w in item["where"]), ""]
        evidence = item.get("evidence") or []
        for ev in [e for e in evidence if text(e.get("image"))]:
            out += md_evidence(L, base, ev, assets, indent="") + [""]
        out.append(f"- **{L['problem']}** {md_text(item['problem'])}")
        out.append(f"- **{L['ask']}** {md_text(item['ask'])}" + (f" ({L['reason']}: {md_text(item['reason'])})" if text(item.get("reason")) else ""))
        paste = item.get("paste")
        if paste:
            to = f", {text(paste.get('to'))}" if text(paste.get("to")) else ""
            out += [f"  - {L['paste']}{to}", "    ```", *[f"    {x}" for x in text(paste["text"]).split("\n")], "    ```"]
        for o in item.get("options") or []:
            out.append(f"- **{L['options']}** {md_text(o)}")
        if text(item.get("if_left")):
            out.append(f"- **{L['if_left']}** {md_text(item['if_left'])}")
        words = [e for e in evidence if not text(e.get("image"))]
        if words or not evidence:
            out.append(f"- **{L['evidence']}**" + ("" if words else f" `{L['needed']}`"))
            for ev in words:
                out += md_evidence(L, base, ev, assets)
        if text(item.get("then")):
            who = f"{text(item['owner'])}: " if text(item.get("owner")) else ""
            out.append(f"- **{L['then']}** {who}{md_text(item['then'])}")
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
        if looked(item):
            out += ["", f"<details><summary>{L['looked']}</summary>", ""] + [f"- {md_text(x)}" for x in looked(item)] + ["", "</details>"]
    before = [md_text(x) for x in data.get("before_handover") or [] if text(x)]
    unseen = [md_text(x) for x in data.get("not_checked") or [] if text(x)]
    if data.get("unread"):
        unseen.insert(0, f"{L['unread']}: " + ", ".join(text(u) for u in data["unread"]))
    if before or unseen:
        out += ["", f"## {L['open_h']}"]
        if before:
            out += ["", f"**{L['before']}**", ""] + [f"- {x}" for x in before]
        if unseen:
            out += ["", f"**{L['not_checked']}**", ""] + [f"- {x}" for x in unseen]
    notes = []
    if prev and prev.get("items"):
        notes += ["", f"<details><summary>{L['earlier_n'].format(n=len(prev['items']))}</summary>", ""]
        notes += md_table({"head": ["#", L["earlier"], L["status"], L["note"]],
                           "rows": [[k, r.get("title"), L["statuses"][r["status"]], r.get("note")] for k, r in enumerate(prev["items"], 1)]})
        notes += ["", "</details>"]
    left = data.get("left_out") or []
    if left:
        notes += ["", f"<details><summary>{L['left_out']} ({len(left)})</summary>", ""]
        notes += md_table({"head": [L["what"], L["why"]], "rows": [[r.get("what"), r.get("why")] for r in left]})
        notes += ["", "</details>"]
    srcs = data.get("sources") or []
    if srcs:
        notes += ["", f"<details><summary>{L['sources']} ({len(srcs)})</summary>", ""]
        notes += [f"- {md_link(s.get('name') or '', s.get('link'))}" + (f", {md_text(s.get('note'))}" if text(s.get("note")) else "") for s in srcs]
        notes += ["", "</details>"]
    if text(data.get("reviewer")):
        notes += ["", f"{L['reviewer']}: {text(data['reviewer'])}  "]
    latest = data.get("latest") or {}
    if text(latest.get("name")):
        notes += [f"{L['latest']}: {md_link(latest['name'], latest.get('link'))}" + (f", {text(latest.get('at'))}" if text(latest.get("at")) else "")]
    if notes:
        out += ["", f"## {L['notes_h']}"] + notes
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
