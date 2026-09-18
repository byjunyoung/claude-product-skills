# Working in this repository

A skill and the documents describing it drift apart silently: the skill runs either way, and the
document only fails when somebody trusts it. So changing a skill is not finished when the skill
works — it is finished when the sentences that describe it are still true.

## After changing anything under `plugins/`

1. **Changelog and version together.** A line in `plugins/<p>/CHANGELOG.md` saying what changed and
   why, and the version in `plugins/<p>/.claude-plugin/plugin.json` raised. `verify.py` fails if a
   version has no entry — an installed version nobody can read the reason for is the worst of the two.
2. **Open the documents that carry a claim about what you changed.** Which ones, by what you touched:

   | Changed | Open |
   |---|---|
   | What a skill does | its row in `plugins/<p>/README.md`, and in both root READMEs — the skills table **and** the paragraph that describes it |
   | What a skill needs — a tool, a token, a connector | root READMEs: *Prerequisites* and *What each skill needs* |
   | A check `/fig:lint` runs | root READMEs: *What `/fig:lint` looks at* |
   | Anything crossing `fig` ↔ `pm` | root READMEs: *Where the two meet*, and `.github/two-plugins.html` if the picture names it |
   | A default that ships on or off | wherever a README states that default — a promise turned off in code stays a promise in prose |
   | A config key a document names | `_common/conventions.example.yaml`, whose comments are the schema's own guide |

3. **Both root READMEs, every time.** `README.md` is the original and `README.ko.md` is the same
   document, not a summary of it. Write the English first, then carry the change over.
4. **Generalize it before it ships.** Whatever prompted the change is one team's instance of it,
   not its definition. A rule goes in as the general shape — a canonical page and an archive of it,
   a tracker that may be any tool, a state list each team writes for itself — and the value that
   made you think of it goes in `conventions.example.yaml` as an example, or nowhere. Where a
   convention cannot be assumed at all, the key ships `null` and the check is skipped, rather than
   firing on every file that does it differently. This is the step with no checker behind it: the
   string check below sees names, never framing.
5. `bash tools/verify-all.sh` — every check CI runs. A `pre-push` hook runs this same script and
   blocks the push on failure, so a missed CHANGELOG entry is caught here rather than in a follow-up
   commit after CI fails. It only fires once this clone has run `git config core.hooksPath .githooks`
   — do that once per clone, since git does not read hooks from a versioned path on its own.

## What the checker catches, and what it cannot

`tools/verify.py` catches the mechanical half: a skill missing from a README's skills table, a
command in one language's README and not the other, a section count that has drifted apart, a config
key or a skill reference that does not exist, a version with no changelog entry, a team's own value
left in a shipped file.

It cannot read a sentence and tell whether it is still true. Every drift found by hand on
2026-09-01 was of that kind — a README still promising a Figma write that had turned out to be
impossible, a token described as one skill's when a second had started needing it, a lint table
naming one component check when there were three. Nor can it see framing: a rule written around the
way one team happens to work passes every string check there is. A green `verify-all` means nothing
was left undeclared — steps 2 and 4 are what make it true, and true for somebody else's team.

## Conventions

- Commit messages are Korean, in the form `type(scope): what changed, in a sentence`; the body says
  why, and what was tried. Documents and code comments are English.
- The READMEs are read by designers and PMs, not by engineers. A term gets three or four words of
  explanation the first time it appears — `null`, a token, a tracker — and a command that shows up in
  the prose is one the reader can hand to Claude instead of typing. Deep material (troubleshooting
  entries, the repository tree, anything aimed at whoever edits the plugins) sits inside `<details>`
  so the page stays short for the person reading it for the first time.
- Prose never carries a skill count — it goes stale the day a skill is added, and `verify.py` fails
  on one. List the skills, or say "the skills".
- The example config is a schema **and** a guide: a new key arrives with the comment explaining what
  it governs and what happens when it is `null`.
- `_common/scripts/lib/resolve-config.py` and `preflight.py` are copies in each plugin, byte for
  byte. Change one, copy it across — `verify.py` compares them.
- Anything belonging to one team — a brand colour, a product name, a document id — never ships.
  `tools/team-strings.local.txt` is what the check reads; it is gitignored, so a fresh clone skips
  that check and says so. It covers the files inside a plugin, and the ones outside it that are just
  as public: this file, `tools/`, and the diagram sources under `.github/`.
