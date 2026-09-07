#!/usr/bin/env python3
"""Starter conventions — a rule set for a file that has nothing to observe yet.

/fig:setup observes a file and takes the dominant value as the convention. A team on its first
file has no dominant value, and a draft made of nulls checks nothing. This writes the other
kind of draft: a set of rules *chosen* rather than observed, each line saying so, for a person
to operate under until their file can be measured.

Only three things are decided by the person — the screen width, the state list, the prefix of
the pages that count. Spacing is derived from the width by fixed ratios, so a desktop file and
a phone file both get gaps that look deliberate. The prefix carries more than the one page: the
working and archive prefixes are made by swapping the word inside it, which is what gives
/fig:sync its three axes on a file that has no divider bands yet. Section style, placeholder
style and arrow style are not written at all: the bundled defaults already carry them, and
writing them here would only make them harder to change later.

Usage
    python3 starter-conventions.py --width 1440 --states Default,Empty,Loading,Error,Validation,Selected --prefix "[UI] "
    python3 starter-conventions.py --width 390 > ./figma-conventions.yaml

Nothing here is measured. Every value carries a comment that says where it came from.
"""
import re, sys

DEFAULT_STATES = ["Default", "Empty", "Loading", "Error", "Validation", "Selected"]

# Gaps as a fraction of the screen width. A 1440 screen gets a 120 gap, a 390 screen gets 32 —
# the ratios are the plugin's opinion, and the comment on each line says so.
GAP_RATIO = 1 / 12

# The word inside the page prefix — 'UI' in '[UI] ', 'Screens' in '[Screens] '. Swapping
# it keeps whatever brackets or spacing the person chose, so the three kinds read as one family.
LABEL_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*|[\uac00-\ud7a3]+")


def derived_names(prefix):
    """What the chosen prefix implies: the page released work is collected on, and the label
    the divider carries.

    The prefix names the canonical page — what is running right now. Released work does not
    stay on it; it is gathered version by version onto a second page, and '[UI] ' gives
    '[Update] ' for that. The pages still being drawn are not found by name at all: each one
    is its own page, named however the person drawing it likes, and what marks them is sitting
    under a divider. So the third value is that divider's label, not a prefix.

    A prefix with no word in it — an emoji, a bare symbol — derives nothing, and the caller
    leaves the sync axes null rather than inventing a page name the team never said.
    """
    m = LABEL_RE.search(prefix)
    if not m:
        return None, None
    korean = "\uac00" <= m.group()[0] <= "\ud7a3"
    released = "\uc5c5\ub370\uc774\ud2b8" if korean else "Update"
    divider = "\uac1c\ubc1c \uc11c\ubc84 \uc5c5\ub370\uc774\ud2b8 \uc644\ub8cc" if korean else "shipped to dev"
    return prefix[:m.start()] + released + prefix[m.end():], divider


def take(argv, flag, default=None):
    if flag not in argv:
        return default
    i = argv.index(flag)
    if i + 1 >= len(argv):
        sys.exit(f"{flag} needs a value after it")
    val = argv[i + 1]
    del argv[i:i + 2]
    return val


def round8(n):
    """Spacing snaps to a multiple of 8, the grid most design tools nudge by."""
    return max(8, int(round(n / 8.0)) * 8)


def main():
    argv = sys.argv[1:]
    width = int(take(argv, "--width", "1440"))
    states = [s.strip() for s in take(argv, "--states", ",".join(DEFAULT_STATES)).split(",") if s.strip()]
    prefix = take(argv, "--prefix", "[UI] ")
    if width < 100:
        sys.exit("--width is a screen width in px, e.g. 1440 or 390")
    if "Default" not in states:
        states = ["Default"] + states      # every screen has a resting state, and the checks assume its name

    gap = round8(width * GAP_RATIO)
    prefix_pattern = "^" + re.escape(prefix)
    released_prefix, divider_label = derived_names(prefix)
    released_pattern = "^" + re.escape(released_prefix) if released_prefix else None
    q = lambda s: "'" + s.replace("'", "''") + "'"

    L = []
    L.append("# figma-conventions.yaml — starter")
    L.append("#")
    L.append("# Chosen, not observed. /fig:setup wrote this for a file that had nothing to measure")
    L.append("# yet. Every value below is a starting rule, and the comment on each line says how it")
    L.append("# was picked. When the file has grown enough to have habits of its own, run /fig:setup")
    L.append("# again and let it observe them — or change a line here the moment a rule stops fitting.")
    L.append("")
    L.append("meta:")
    L.append("  profile: starter          # stamped on reports, so it is clear which rules ran")
    L.append("")
    L.append("naming:")
    L.append('  frame: "{screen}-{state}"                   # starter — one screen, one state, one dash: Login-Default, Login-Error')
    L.append("  frame_pattern: '^.+-[^-\\s]+$'                # starter — what lint checks the frame rule with")
    L.append('  section: "NN. {domain} - {feature}"           # starter — the number is the order a user meets the feature')
    L.append("  section_pattern: '^\\d{2}\\. .+$'")
    L.append(f"  states: [{', '.join(states)}]   # {'starter — the six most screens need' if states == DEFAULT_STATES else 'chosen in setup'}")
    L.append("  required_states:                            # starter — what a screen of each kind must have before handoff")
    L.append(f"    list:   [{', '.join(s for s in ['Default', 'Empty', 'Loading', 'Error'] if s in states)}]")
    L.append(f"    form:   [{', '.join(s for s in ['Default', 'Validation'] if s in states)}]")
    L.append(f"    search: [{', '.join(s for s in ['Default', 'Empty'] if s in states)}]")
    L.append("")
    L.append("pages:")
    L.append(f"  strict:   [{q(prefix_pattern)}]   # starter — {prefix!r} is what is running right now; every rule applies there")
    if released_prefix:
        L.append(f"  free:     [{q(released_pattern)}]   # starter — {released_prefix!r} collects released work version by version. Add your own")
        L.append("            #             working-page names here too: they are drawn in, so the minimum rules only")
    L.append("  readonly: ['^\\[?[Aa]rchive']   # starter — anything named Archive is read by these skills and written by none")
    L.append("  exclude_sections: ['^Template$', '^\\[?[Aa]rchive']   # starter — a template, and anything put away, are audited by nothing")
    if released_prefix:
        L.append("")
        L.append("  # The three axes /fig:sync compares on.")
        L.append("  #")
        L.append("  # A screen being revised gets its own page, named however the person drawing it likes,")
        L.append("  # so no pattern can find it. What marks one as done is where it sits: drag it under an")
        L.append(f"  # empty divider page named '## {divider_label} ##' the moment engineering has it on")
        L.append("  # the dev server. Everything below that divider is waiting to reach canonical, and that")
        L.append("  # is the band sync sweeps. Then sync applies it to canonical and files the page under")
        L.append(f"  # {released_prefix!r} with the version it went out in.")
        L.append(f"  canonical: {{ match: name,    pattern: {q(prefix_pattern)} }}   # starter — what is running right now")
        L.append(f"  queue:     {{ match: divider, pattern: {q(divider_label)} }}   # starter — on the dev server, not yet in canonical")
        L.append(f"  archive:   {{ match: name,    pattern: {q(released_pattern)} }}   # starter — released, collected by version")
    L.append("")
    L.append("layout:                                       # starter — derived from the screen width, nothing measured")
    L.append(f"  reference_frame_width: {width:<12}# chosen in setup")
    L.append(f"  frame_gap:             {gap:<12}# width / 12, snapped to 8")
    L.append(f"  column_grid:           {width + gap:<12}# width + gap: the pitch from one screen's left edge to the next")
    L.append(f"  section_padding:       {gap:<12}# same as the gap, so a section hugs its screens evenly")
    L.append(f"  section_gap_same_row:  {gap * 2:<12}# two gaps between sections on one row")
    L.append(f"  domain_row_gap:        {gap * 4:<12}# four gaps between one domain's row and the next")
    L.append(f"  section_resize_margin: {f'[{gap}, {gap * 2}]':<12}# a section may hug its content by one gap, at most two")
    print("\n".join(L))


if __name__ == "__main__":
    main()
