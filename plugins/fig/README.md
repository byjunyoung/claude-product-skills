# fig

A bundle for a Figma file several people share. It builds your to-draw list before you start, draws each screen anchored to your file's own conventions, and keeps the canonical page current afterwards.

You type these to Claude like anything else — `/fig:lint` — and it answers in words. No code.

```bash
claude plugin marketplace add byjunyoung/claude-product-skills
claude plugin install fig@byjunyoung
```

## The cycle

```
/fig:setup    ──▶  your file's conventions, written down      once per file
     │
/fig:prep     ──▶  sections + a dashed placeholder per missing screen
     │             = your to-draw list
/fig:sketch   ──▶  the direction, agreed in text            writes nothing
     │             (only when a screen looks or behaves differently)
/fig:draw     ──▶  each placeholder becomes a real screen
     │
/fig:arrows   ──▶  transition arrows and state links
     │
/fig:lint     ──▶  findings, each blocking or a warning       reads only
     │  nothing blocking
/fig:handoff  ──▶  section links to engineering
     │  after release
/fig:sync     ──▶  canonical page current, working copy archived
```

<img src="../../.github/prep-stubs.png" alt="Three finished screens above five dashed placeholder frames, each named for the state it stands for" width="100%">

*`/fig:prep` — the screens you still owe, as named placeholders before anyone draws.*

<img src="../../.github/arrows-before-after.png" alt="Before and after running /fig:arrows on a section: the same four screens gain a labelled transition arrow and dashed state links" width="100%">

*`/fig:arrows` — the same section before and after.*

## Commands

| Command | What it does |
|---|---|
| `/fig:setup` | Reads how your file already names and spaces things, and writes it down as your settings. Run it first on a new file |
| `/fig:read` | Lists every page and screen in the file |
| `/fig:prep` | Makes names consistent · puts screens in their section · leaves a placeholder for each screen you still owe |
| `/fig:sketch` | Agrees what a screen will look like before anything is drawn — one decision at a time, then a rough text wireframe of each state. Writes nothing |
| `/fig:draw` | Draws a screen or fills a placeholder, cloned from the nearest canonical screen |
| `/fig:arrows` | Creates and re-syncs flow arrows |
| `/fig:lint` | The audit everything else has to pass. Reads and reports, never edits |
| `/fig:handoff` | Hands the sections that pass lint to engineering, with their links |
| `/fig:sync` | Finds what never made it into the canonical page → applies it → archives the working copy |
| **Around the cycle** | |
| `/fig:tokens` | Checks colours are bound to design-system tokens rather than typed in by hand |
| `/fig:diff` | Annotates what changed · writes up the task doc |
| `/fig:proto` | A working single-file HTML prototype |
| `/fig:code` | Applies the design to the front-end code |
| `/fig:qa` | Compares what actually shipped against the plan, and writes up the defects with a screenshot for each |
| `/fig:deck-setup` | Measures a team presentation template into deck assets |
| `/fig:deck` | Turns a source into a presentation deck (Figma Slides) |

## How draw draws

```
1  Agree the direction   /fig:sketch, or skipped when it already ran in this conversation
                         (only when a screen is about to look or behave differently)
2  Find the pattern      the file's pattern page → two screens that already agree
                         → neither: stop and ask, rather than invent one
3  Clone and change      the nearest canonical screen, changing only what differs
                         an undecided fact is pinned on its node, not left as a blank frame
4  Check                 lint + tokens on every drawn frame,
                         then all of them in one image — a dark screen among light
                         ones looks fine on its own
```

## What lint catches

```
Structure    screens outside a section · overlaps · names · a colour mode nobody set
             · a control cut off by its cell or hanging off the screen
Flow         arrows through unrelated screens · arrowheads into empty space
             · screens on no flow
Components   variants stacked on each other · settings a duplicate carried along
```

```
finding ─┬─ blocking ──▶  the section is held back from /fig:handoff
         └─ warning  ──▶  it goes along, and the warning is shown with it
```

<img src="../../.github/lint-catches.png" alt="A tidy-looking section with three numbered violations marked: an arrow crossing an unrelated screen, an arrowhead in empty space, and a screen on no flow" width="100%">

## Settings

```
bundled defaults                    the floor
     ↓ covered by
~/.claude/figma-conventions.yaml    yours, for every file
     ↓ covered by
./figma-conventions.yaml            this project (strongest)
```

One file holds your team's rules — how screens are named, how far apart they sit, what a section looks like. The layers merge, so **you only write the lines you want to change**, and you never have to open it: tell Claude what to change.

The skills that write to Figma check your seat first and stop on a View seat — one that can read a file but not edit it — instead of failing halfway.

## The other half

```
pm                              fig
/pm:prd          ── spec ──▶    qa.baseline.prd    /fig:qa judges against it
/pm:task-publish ── task ──▶    task_tracker.ref   /fig:diff writes its table there
```

[`pm`](../pm/README.md) writes the spec this file is drawn against and opens the task the changes belong to. Both links are optional — left empty, both skills still run. The full explanation is in the [repository README](https://github.com/byjunyoung/claude-product-skills).
