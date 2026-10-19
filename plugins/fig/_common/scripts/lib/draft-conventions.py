#!/usr/bin/env python3
"""probe-page.js observations → a figma-conventions.yaml draft.

    python3 draft-conventions.py --file-key KEY probe1.json probe2.json ...

KEY is the fileKey in figma.com/design/<fileKey>/... — the file the probes were read from.

The draft holds two kinds of line and nothing else:
  · a value the probes observed, with its evidence (sample count and ratio) as a comment. A thin
    or split sample leaves the value null, with the reason, rather than filling it in
  · a key only a person can answer (INTERVIEW_KEYS), left null for /fig:setup to ask
A key that is neither is not written. The bundled defaults supply it, and keep supplying it when
they change — a default copied in here would read as somebody's choice, and stay frozen there.
Rules about pages are facts about one file, so what the probes suggest for them goes under
files.<KEY>.pages, never at the top level of a config that may serve every file.

**Not writing an inference as though it were settled is the whole of this tool** — what is
ambiguous has to be filled in by a person.
"""
import argparse, json, re, sys
from collections import Counter

MIN_SUPPORT = 3          # fewer samples than this does not count as a convention
DOMINANCE = 0.6          # a mode below this ratio counts as split

# What observation cannot settle and a person can. Written null, so /fig:setup asks; every other
# line the draft writes carries its evidence.
INTERVIEW_KEYS = (
    "naming.required_states",
    "layout.section_padding",
    "layout.reference_frame_width",
    "arrows.trunk",
    "arrows.trunk_to_target_min",
    "arrows.parallel_offset",
    "arrows.label.offset_from_target",
)


def mode(vals, min_support=MIN_SUPPORT, dominance=DOMINANCE):
    """(value, evidence string) or (None, reason)."""
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, "0 observed"
    c = Counter(json.dumps(v, sort_keys=True, ensure_ascii=False) for v in vals)
    top, n = c.most_common(1)[0]
    ratio = n / len(vals)
    if len(vals) < min_support:
        return None, f"{len(vals)} samples — too few"
    if ratio < dominance:
        return None, f"split (mode {n}/{len(vals)}, {ratio:.0%})"
    return json.loads(top), f"{n}/{len(vals)} ({ratio:.0%})"


def snap(vals, grid=4):
    """Rounds to a grid to absorb coordinate noise, then takes the mode."""
    return [round(v / grid) * grid for v in vals if isinstance(v, (int, float)) and v > 0]


def y(v):
    return json.dumps(v, ensure_ascii=False) if v is not None else "null"


def parse_args(argv):
    ap = argparse.ArgumentParser(
        prog="draft-conventions.py",
        description="probe-page.js observations → a figma-conventions.yaml draft")
    ap.add_argument("--file-key", required=True,
                    help="the fileKey in figma.com/design/<fileKey>/... — page rules are drafted under files.<fileKey>")
    ap.add_argument("probes", nargs="+", help="probe-page.js results, one JSON file per page (or a list of them)")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9]+", a.file_key):
        ap.error(f"--file-key takes the key alone, not {a.file_key!r} — the part after /design/ in the file's URL")
    return a


def main():
    args = parse_args(sys.argv[1:])
    probes = []
    for f in args.probes:
        d = json.load(open(f, encoding="utf-8"))
        probes.extend(d if isinstance(d, list) else [d])
    probes = [p for p in probes if not p.get("error")]
    if not probes:
        sys.exit("no observations")

    L = []

    def line(k, v, why, indent=2):
        L.append(f"{' ' * indent}{k}: {y(v)}" + (f"   # {why}" if why else ""))

    def ask(path, why):
        """A key only a person can answer, left null for /fig:setup to ask."""
        assert path in INTERVIEW_KEYS, path
        line(path.split(".")[-1], None, why, indent=2 * path.count("."))

    # ── Naming ────────────────────────────────────────────────
    frames = [n for p in probes for n in p.get("frameNames", [])]
    secnames = [s["name"] for p in probes for s in p.get("sections", [])]
    fr_re = r'^.+-[^-\s]+$'        # restricting the suffix to Latin characters false-positives every non-Latin state name
    fr_hit = sum(1 for n in frames if re.match(fr_re, n))
    fr_ok = frames and fr_hit / len(frames) >= DOMINANCE
    fr_ev = f"{fr_hit}/{len(frames)} match" if frames else "0 observed"

    sec_num = sum(1 for n in secnames if re.match(r'^\d{2}\. ', n))
    sec_ok = secnames and sec_num / len(secnames) >= DOMINANCE
    sec_ev = f"{sec_num}/{len(secnames)} number-prefixed" if secnames else "0 observed"

    suf = Counter()
    for p in probes:
        suf.update(p.get("suffixes", {}))
    states = [k for k, v in suf.most_common() if v >= 2]
    carried = sum(suf[k] for k in states)

    L.append("naming:")
    line("frame", "{screen}-{state}" if fr_ok else None, fr_ev)
    line("frame_pattern", fr_re if fr_ok else None, fr_ev if fr_ok else f"{fr_ev} — no pattern found, check disabled")
    line("section", "NN. {domain} - {feature}" if sec_ok else None, sec_ev)
    line("section_pattern", r'^\d{2}\. .+$' if sec_ok else None, sec_ev)
    line("states", states or None,
         f"{carried}/{sum(suf.values())} suffixed frames carry one seen twice or more · most frequent observed: {dict(suf.most_common(8))}"
         if suf else "0 observed")
    ask("naming.required_states", "needs a screen-type judgement, so it cannot be inferred — /fig:setup asks")
    # The non-English alternatives here and below are detection breadth, not untranslated text:
    # section names are written in the team's own language, so dropping them would narrow the probe.
    # A shared page or a pattern page is adopted on purpose and may live outside this file, so
    # neither key is written unless a candidate turned up — and then only to say so.
    ncommon = [s for s in secnames if re.match(r'^공통|^common', s, re.I)]
    if ncommon:
        line("common_page_pattern", None, f"sections named like a shared page observed: {ncommon[:5]} — needs confirming")
    npat = [p.get("page", "") for p in probes if re.match(r'^\[?패턴|^\[?pattern', p.get("page", "") or "", re.I)]
    if npat:
        line("pattern_page_pattern", None, f"observed: {npat} — needs confirming")
    L.append("")

    # ── Layout ────────────────────────────────────────────────
    fx = snap([v for p in probes for v in p["gaps"]["frameX"]])
    fy = snap([v for p in probes for v in p["gaps"]["frameY"]])
    sx = snap([v for p in probes for v in p["gaps"]["sectionX"]])
    sy = snap([v for p in probes for v in p["gaps"]["sectionY"]])
    coldiffs = snap([v for p in probes for v in p.get("columnPitch", [])])

    fg, fgw = mode(fx + fy)
    cg, cgw = mode(coldiffs)
    sgx, sgxw = mode(sx)
    sgy, sgyw = mode(sy)
    L.append("layout:")
    line("column_grid", cg, cgw)
    ask("layout.section_padding", "section padding cannot be separated from frame positions alone — /fig:setup asks")
    line("frame_gap", fg, fgw)
    line("section_gap_same_row", sgx, sgxw)
    line("domain_row_gap", sgy, sgyw)
    ws = [s["w"] for p in probes for s in p.get("sections", [])]
    ask("layout.reference_frame_width",
        f"the probe measures sections, not screens (median section width {sorted(ws)[len(ws)//2] if ws else '-'}) — /fig:setup asks")
    L.append("")

    # ── Section style ─────────────────────────────────────────
    S = [s for p in probes for s in p.get("sections", [])]
    fill, fw = mode([s["fill"] for s in S])
    strk, sw = mode([s["stroke"] for s in S])
    swt, swtw = mode([s["strokeWeight"] for s in S])
    sal, salw = mode([s["strokeAlign"] for s in S])
    dash, dw = mode([s["dash"] for s in S])
    rad, rw = mode([s["radius"] for s in S])
    L.append("section_style:")
    line("fill", fill["hex"] if fill else None, fw)
    line("fill_opacity", fill["opacity"] if fill else None, fw)
    line("stroke", strk["hex"] if strk else None, sw)
    line("stroke_weight", swt, swtw)
    line("stroke_align", sal, salw)
    line("dash", dash, dw)
    line("corner_radius", rad, rw)
    L.append("")

    # ── placeholder ──────────────────────────────────────────
    # Only the frame is observed. The text inside a dashed frame is not, so its font, colour and
    # prefix stay with the bundled defaults.
    D = [d for p in probes for d in p.get("dashedFrames", [])]
    pf, pfw = mode([d["fill"] for d in D])
    ps, psw = mode([d["stroke"] for d in D])
    pw, pww = mode([d["strokeWeight"] for d in D])
    pd, pdw = mode([d["dash"] for d in D])
    L.append("placeholder_style:")
    line("fill", pf["hex"] if pf else None, pfw)
    line("stroke", ps["hex"] if ps else None, psw)
    line("stroke_weight", pw, pww)
    line("dash", pd, pdw)
    L.append("")

    # ── Arrows ────────────────────────────────────────────────
    A = [a for p in probes for a in p["arrows"]["styles"]]
    HG = snap([v for p in probes for v in p["arrows"]["headGaps"]], grid=1)
    LB = [l for p in probes for l in p["labels"]["styles"]]
    ac, acw = mode([a["color"] for a in A])
    aw_, aww = mode([a["weight"] for a in A])
    hg, hgw = mode(HG)
    dashes = [a["dash"] for a in A if a["dash"]]
    dc, dcw = mode(dashes)
    dash_ev = f"{len(dashes)}/{len(A)} arrows dashed" if A else "0 observed"
    if dashes and dc is None:
        dash_ev += f" — {dcw}"
    L.append("arrows:")
    line("color", ac["hex"] if ac else None, acw)
    line("stroke_weight", aw_, aww)
    line("dash_conditional", dc, dash_ev)
    line("head_gap", hg, hgw)
    ask("arrows.trunk", "only shows on elbow paths, so inference is unreliable — /fig:setup asks")
    ask("arrows.trunk_to_target_min", "the trunk family — /fig:setup asks")
    ask("arrows.parallel_offset", "the trunk family — /fig:setup asks")
    lf, lfw = mode([l["font"] for l in LB])
    lp, lpw = mode([l["padding"] for l in LB])
    lr, lrw = mode([l["radius"] for l in LB])
    lfl, lflw = mode([l["fill"] for l in LB])
    lst, lstw = mode([l["stroke"] for l in LB])
    ltc, ltcw = mode([l["textColor"] for l in LB])
    L.append("  label:")
    line("font", lf, lfw, 4)
    line("padding", lp, lpw, 4)
    line("corner_radius", lr, lrw, 4)
    line("fill", lfl["hex"] if lfl else None, lflw, 4)
    line("stroke", lst["hex"] if lst else None, lstw, 4)
    line("text_color", ltc["hex"] if ltc else None, ltcw, 4)
    ask("arrows.label.offset_from_target", "the trunk family — /fig:setup asks")
    L.append("  audit:")
    line("gap_range", [hg - 3, hg + 3] if hg else None, f"head_gap ±3 — {hgw}", 4)
    L.append("")

    # ── Sync ──────────────────────────────────────────────────
    # AS-IS / TO-BE section names are written in whatever language the team works in.
    # Widen the alternation only when this file actually contains non-ASCII names —
    # otherwise a team that never sees those words gets them baked into their config, and the
    # bundled patterns stand.
    names = [s_["name"] for s_ in S] + [p_.get("page") or "" for p_ in probes]
    # Letters only — an em-dash or a curly quote is non-ASCII but not another language.
    wide = [n for n in names if any(ord(ch) > 127 and ch.isalpha() for ch in n)]
    if wide:
        L.append("sync:")
        L.append(f"  pair_patterns:   # non-ASCII names observed ({len(wide)}/{len(names)}) — widen these to your own wording")
        L.append("    to_be: 'to.?be|개선|after'")
        L.append("    as_is: 'as.?is|현행|before'")
        L.append("")

    # ── This file's pages ─────────────────────────────────────
    # Which page is canonical, strict or read-only is not on the canvas; /fig:setup asks and
    # writes the answers beside these. Only sections that look like scaffolding are observed.
    excl = sorted({s for s in secnames if re.match(r'^템플릿$|^[Tt]emplate$|^\[?[Aa]rchive|^9\d\.', s)})
    if excl:
        L.append("files:")
        L.append(f"  {y(args.file_key)}:")
        L.append("    pages:")
        line("exclude_sections", [f"^{re.escape(s)}$" for s in excl],
             f"exclusion candidates observed: {excl}", 6)

    head = [
        "# figma-conventions.yaml — auto-draft from /fig:setup",
        "#",
        f"# observed {len(probes)} pages · {len(S)} sections · {len(frames)} frames"
        f" · {sum(p['arrows']['count'] for p in probes)} arrows · file {args.file_key}",
        "#",
        "# Two kinds of line are written here. An observed value carries its evidence as a comment —",
        "# the n/m is how many observations out of how many carried that value, and a thin or split",
        "# sample is null with the reason. A null left as it is means what its reader makes of it: an",
        "# audit skips that check; a style value makes the drawing skills fall back to their built-in",
        "# defaults, and sections get no fill or stroke from it. Write the observed value, or delete",
        "# the line to keep the bundled default. A null whose comment says /fig:setup asks is a",
        "# question only a person can answer.",
        "# Nothing else is written: what is missing comes from the bundled defaults, and keeps coming",
        "# from them when they change. Rules about this file's pages go under",
        f"# files.{y(args.file_key)}.pages, never at the top level.",
        "",
    ]
    print("\n".join(head + L))
    pd_ = sum(p.get("pageDirectFrames", 0) for p in probes)
    if pd_:
        print(f"\n# Note: {pd_} frames observed sitting directly on a page outside any section — this file's section convention may be loose.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
