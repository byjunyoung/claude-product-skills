# fig

A bundle for a Figma file several people share. It builds your to-draw list before you start, draws each screen anchored to your file's own conventions, and keeps the canonical page current afterwards.

You type these the way you type anything else to Claude — `/fig:lint`, and it answers in words. Nothing here asks you to write code.

```bash
claude plugin marketplace add byjunyoung/claude-product-skills
claude plugin install fig@byjunyoung
```

| Command | What it does |
|---|---|
| `/fig:setup` | Reads how your file already names and spaces things, and writes it down as your settings |
| `/fig:read` | Lists every page and screen in the file |
| `/fig:prep` | Makes names consistent · puts screens in their section · leaves a placeholder for each screen you still owe |
| `/fig:draw` | Draws a screen or fills a placeholder — agreeing the direction first as a rough text sketch of each state, then following the pattern your file already uses, cloned from its nearest canonical screen |
| `/fig:arrows` | Creates and re-syncs flow arrows |
| `/fig:lint` | The audit everything else has to pass. It reads and reports, and never edits |
| `/fig:handoff` | Gates on lint · pins the version handed over · hands over the links |
| `/fig:tokens` | Checks colours are bound to design-system tokens rather than typed in by hand |
| `/fig:sync` | Finds what never made it into the canonical page → applies it → archives the working copy |
| `/fig:diff` | Annotates what changed · writes up the task doc |
| `/fig:proto` | A working single-file HTML prototype |
| `/fig:code` | Applies the design to the front-end code |
| `/fig:qa` | Compares what actually shipped against the plan, and writes up the defects |
| `/fig:deck-setup` | Measures a team presentation template into deck assets |
| `/fig:deck` | Turns a source into a presentation deck (Figma Slides) |

**One settings file decides the rules** — `figma-conventions.yaml`, holding how your team names screens, how far apart they sit, what a section looks like. Three layers merge, bundled defaults → `~/.claude/figma-conventions.yaml` → `./figma-conventions.yaml`, so **only the lines you actually want to change have to be written.** You never have to open it yourself: tell Claude what to change in your own words and it edits the file.

On a file you are opening for the first time, run `/fig:setup` first and let it observe the conventions. It opens by checking this machine — the Figma plugin, the two programs the audit runs on (`python3` with PyYAML, and `node`), and which of your connected tools actually answer — so anything missing is named up front rather than quietly narrowing the run. The full explanation is in the [repository README](https://github.com/byjunyoung/claude-product-skills).

The skills that write — `prep`, `draw`, `arrows`, `diff`, `sync`, `tokens`, `deck` — check your Figma seat before their first write, and stop on a View seat — one that can read a file but not edit it — instead of failing halfway.

## The other half

[`pm`](../pm/README.md) writes the spec this file is drawn against and opens the task the changes belong to. The two never call each other, but they share two objects: point `qa.baseline.prd` at the spec `pm` writes and `task_tracker.ref` at the record it opens, and `/fig:qa` gains a baseline while `/fig:diff` gains somewhere to put the comparison table. Neither is required — left empty (`null` and `none`), both skills still run. The [repository README](https://github.com/byjunyoung/claude-product-skills#where-the-two-meet) draws the whole loop.
