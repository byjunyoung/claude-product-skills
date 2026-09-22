#!/usr/bin/env python3
"""probe-page.js observations → a figma-conventions.yaml draft.

    python3 draft-conventions.py probe1.json probe2.json ... [--pages pages.txt]

Every value carries its evidence (sample count and ratio) as a comment, and a thin sample
leaves the value out as null rather than filling it in.
**Not writing an inference as though it were settled is the whole of this tool** — what is
ambiguous has to be filled in by a person.
"""
import json, re, sys
from collections import Counter

MIN_SUPPORT = 3          # fewer samples than this does not count as a convention
DOMINANCE = 0.6          # a mode below this ratio counts as split


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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    probes = []
    for f in args:
        d = json.load(open(f, encoding="utf-8"))
        probes.extend(d if isinstance(d, list) else [d])
    probes = [p for p in probes if not p.get("error")]
    if not probes:
        sys.exit("no observations")

    L, notes = [], []

    def line(k, v, why, indent=2):
        L.append(f"{' ' * indent}{k}: {y(v)}" + (f"   # {why}" if why else ""))

    # ── Naming ────────────────────────────────────────────────
    frames = [n for p in probes for n in p.get("frameNames", [])]
    secnames = [s["name"] for p in probes for s in p.get("sections", [])]
    fr_re = r'^.+-[^-\s]+$'        # restricting the suffix to Latin characters false-positives every non-Latin state name
    fr_hit = sum(1 for n in frames if re.match(fr_re, n))
    fr_ok = frames and fr_hit / len(frames) >= DOMINANCE

    sec_num = sum(1 for n in secnames if re.match(r'^\d{2}\. ', n))
    sec_ok = secnames and sec_num / len(secnames) >= DOMINANCE

    suf = Counter()
    for p in probes:
        suf.update(p.get("suffixes", {}))
    states = [k for k, v in suf.most_common() if v >= 2]

    L.append("naming:")
    line("frame", "{screen}-{state}" if fr_ok else None, f"{fr_hit}/{len(frames)} match" if frames else "0 observed")
    line("frame_pattern", fr_re if fr_ok else None, "" if fr_ok else "no pattern found — check disabled")
    line("section", "NN. {domain} - {feature}" if sec_ok else None, f"{sec_num}/{len(secnames)} number-prefixed")
    line("section_pattern", r'^\d{2}\. .+$' if sec_ok else None, "")
    line("states", states or None, f"most frequent suffixes: {dict(suf.most_common(8))}" if suf else "0 observed")
    L.append("  required_states: null   # needs a screen-type judgement, so it cannot be inferred — fill it in")
    for k, v in [("arrow_delimiter", " --> "), ("state_chain_delimiter", " ~ "),
                 ("label_prefix", "[label] "), ("state_chain_prefix", "[state] ")]:
        L.append(f"  {k}: {y(v)}")
    # The non-English alternatives here and below are detection breadth, not untranslated text:
    # section names are written in the team's own language, so dropping them would narrow the probe.
    ncommon = [s for s in secnames if re.match(r'^공통|^common', s, re.I)]
    line("common_page_pattern", None, "a shared page may live outside this file, so nothing is inferred" if not ncommon else f"{len(ncommon)} sections observed — needs confirming")
    line("common_frame_prefix", None, "")
    npat = [p.get("page", "") for p in probes if re.match(r'^\[?패턴|^\[?pattern', p.get("page", "") or "", re.I)]
    line("pattern_page_pattern", None, "a pattern page is adopted on purpose, so nothing is inferred" if not npat else f"observed: {npat} — needs confirming")
    line("pattern_frame_prefix", None, "")
    L.append("")

    # ── Pages ─────────────────────────────────────────────────
    excl = sorted({s for s in secnames if re.match(r'^템플릿$|^[Tt]emplate$|^\[?[Aa]rchive|^9\d\.', s)})
    L.append("pages:")
    L.append("  strict: []     # cannot be inferred — which page is canonical is something a person knows")
    L.append("  free: []")
    L.append("  readonly: []")
    line("exclude_sections", [f"^{re.escape(s)}$" for s in excl] or [], f"exclusion candidates observed: {excl}" if excl else "no candidates")
    L.append("  protected_numbers: []")
    for k in ("canonical", "archive", "queue"):
        L.append(f"  {k}: null   # confirmed and filled on the first /fig:sync run")
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
    line("section_padding", None, "section padding cannot be separated from frame positions alone — fill it in")
    line("frame_gap", fg, fgw)
    line("section_gap_same_row", sgx, sgxw)
    line("domain_row_gap", sgy, sgyw)
    L.append("  section_resize_margin: [80, 160]")
    L.append("  row_bucket: 1000")
    ws = [s["w"] for p in probes for s in p.get("sections", [])]
    L.append(f"  reference_frame_width: null   # needs a screen-width observation (median section width {sorted(ws)[len(ws)//2] if ws else '-'})")
    L.append("")

    # ── Section style ─────────────────────────────────────────
    S = [s for p in probes for s in p.get("sections", [])]
    fill, fw = mode([s["fill"] for s in S])
    strk, sw = mode([s["stroke"] for s in S])
    dash, dw = mode([s["dash"] for s in S])
    rad, rw = mode([s["radius"] for s in S])
    L.append("section_style:")
    line("fill", fill["hex"] if fill else None, fw)
    line("fill_opacity", fill["opacity"] if fill else None, "")
    line("stroke", strk["hex"] if strk else None, sw)
    line("stroke_weight", mode([s["strokeWeight"] for s in S])[0], "")
    line("stroke_align", mode([s["strokeAlign"] for s in S])[0], "")
    line("dash", dash, dw)
    line("corner_radius", rad, rw)
    L.append("")

    # ── placeholder ──────────────────────────────────────────
    D = [d for p in probes for d in p.get("dashedFrames", [])]
    pf, pfw = mode([d["fill"] for d in D])
    ps, psw = mode([d["stroke"] for d in D])
    pd, pdw = mode([d["dash"] for d in D])
    L.append("placeholder_style:")
    line("fill", pf["hex"] if pf else None, pfw)
    line("stroke", ps["hex"] if ps else None, psw)
    line("stroke_weight", mode([d["strokeWeight"] for d in D])[0], "")
    line("dash", pd, pdw)
    L.append("  font: null   # check the text inside a dashed frame yourself and fill it in")
    L.append("  text_color: null")
    L.append('  text_prefix: "Placeholder — "')
    L.append("")

    # ── Arrows ────────────────────────────────────────────────
    A = [a for p in probes for a in p["arrows"]["styles"]]
    HG = snap([v for p in probes for v in p["arrows"]["headGaps"]], grid=1)
    LB = [l for p in probes for l in p["labels"]["styles"]]
    ac, acw = mode([a["color"] for a in A])
    aw_, aww = mode([a["weight"] for a in A])
    hg, hgw = mode(HG)
    L.append("arrows:")
    line("color", ac["hex"] if ac else None, acw)
    line("stroke_weight", aw_, aww)
    dashes = [a["dash"] for a in A if a["dash"]]
    line("dash_conditional", mode(dashes)[0] if dashes else None, f"{len(dashes)} dashed arrows")
    line("head_gap", hg, hgw)
    L.append("  trunk: null            # only shows on elbow paths, so inference is unreliable")
    L.append("  trunk_to_target_min: null")
    L.append("  parallel_offset: null")
    L.append('  cap: { start: ROUND, end: ARROW_EQUILATERAL }')
    L.append("  label:")
    lf, lfw = mode([l["font"] for l in LB])
    L.append(f"    font: {y(lf)}   # {lfw}")
    lp, lpw = mode([l["padding"] for l in LB])
    L.append(f"    padding: {y(lp)}   # {lpw}")
    L.append(f"    corner_radius: {y(mode([l['radius'] for l in LB])[0])}")
    lfl, _ = mode([l["fill"] for l in LB])
    lst, _ = mode([l["stroke"] for l in LB])
    ltc, _ = mode([l["textColor"] for l in LB])
    L.append(f"    fill: {y(lfl['hex'] if lfl else None)}")
    L.append(f"    stroke: {y(lst['hex'] if lst else None)}")
    L.append(f"    text_color: {y(ltc['hex'] if ltc else None)}")
    L.append("    offset_from_target: null")
    L.append("  audit:")
    L.append("    edge_tolerance: 2")
    L.append(f"    gap_range: {y([hg - 3, hg + 3] if hg else None)}   # head_gap ±3")
    L.append("    label_clear: 30")
    L.append("")

    L.append("component_audit:")
    L.append("  min_samples: 5")
    L.append("  dominance: 0.9")
    L.append("  body_offset: null   # the shared shell's width and height — open one screen and measure")
    L.append("")
    L.append("design_system:\n  library: auto\n  token_prefixes: []\n  match_threshold_channel: 8\n")
    L.append("sync:")
    # AS-IS / TO-BE section names are written in whatever language the team works in.
    # Widen the alternation only when this file actually contains non-ASCII names —
    # otherwise a team that never sees those words gets them baked into their config.
    names = [s_["name"] for s_ in S] + [p_.get("page", "") for p_ in probes]
    # Letters only — an em-dash or a curly quote is non-ASCII but not another language.
    if any(ord(ch) > 127 and ch.isalpha() for n in names for ch in n):
        L.append("  pair_patterns:   # non-ASCII names observed — widen these to your own wording")
        L.append("    to_be: 'to.?be|개선|after'")
        L.append("    as_is: 'as.?is|현행|before'")
    else:
        L.append("  pair_patterns:   # add your team's wording if it is not English")
        L.append("    to_be: 'to.?be|after'")
        L.append("    as_is: 'as.?is|before'")
    L.append("  text_diff_max_len: 40\n  version_page_pattern: null\n")
    L.append("task_tracker:\n  type: none\n  ref: null\n  ui_section_heading: null")
    L.append('  annotation_category: "Changed"\n  scope_tags: []\n')
    L.append("tools:\n  figma_token_env: FIGMA_TOKEN\n  frame_count_guard: 20")
    L.append('  proto_output_dir: "."')
    L.append("  proto_publish:\n    repo: null\n    account: null\n    local: null")
    L.append("    visibility: private\n    pages_url: null\n    landing: index.html\n")
    L.append("guide_source:\n  type: none\n  ref: null\n")
    L.append("files: {}")

    head = [
        "# figma-conventions.yaml — auto-draft from /fig:setup",
        "#",
        f"# observed {len(probes)} pages · {len(S)} sections · {len(frames)} frames"
        f" · {sum(p['arrows']['count'] for p in probes)} arrows",
        "#",
        "# null means 'not inferred'. It is left empty so an inference is never written as settled,",
        "# and left as it is, that check is skipped. Fill in whatever you know.",
        "# The n/m in each line comment is how many observations out of how many carried that value.",
        "",
    ]
    print("\n".join(head + L))
    pd_ = sum(p.get("pageDirectFrames", 0) for p in probes)
    if pd_:
        print(f"\n# Note: {pd_} frames observed sitting directly on a page outside any section — this file's section convention may be loose.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
