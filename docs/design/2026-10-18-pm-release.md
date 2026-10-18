# pm:release — release notes for several readers from one release

Status: design, 2026-10-18. Decisions agreed with the owner; the designer's calls are pending the
owner's review. Not built. Second item of the skill review's D2 (`2026-10-18-skill-review.md`).

## Intent

When something ships, several people need to hear about it in different words. A team usually
has the raw material:

- a version tag in the code repository
- the tickets and parent items behind it
- the QA report's open defects
- often an announcement someone already posted

Turning that into something each reader can use is done by hand, late, or not at all.

`pm:release` takes one release and writes one edition per reader from the same material. The
skill is generic. A team's channels, document templates and release cadence are values in its
config, not shapes in the skill.

## Decisions

| # | Question | Chosen | Not chosen |
|---|---|---|---|
| 1 | Who reads it | Several readers from one run: one edition per reader | One internal audience only; operators only; end users only |
| 2 | Which editions ship by default | An internal note and a user notice. Editions are defined in config, so a team can add or drop one | An operator / customer edition in the floor |
| 3 | What one release is | One version tag in the code repository | A tracker milestone; a date range |
| 4 | What it reads | Both: an announcement the team already posts (where config names one) to confirm scope, and the tracker's items to write the sentences | Tickets only; the announcement only |
| 5 | Known issues | In the internal note only | Both editions; neither |
| 6 | Generic, not one team's | Channel, template and cadence are config values | Building around the owner's company's release practice |

## Goals

- From one tag, write every configured edition, each in its readers' words.
- Every item in an edition traces to a source: a ticket, a change between tags, or the
  announcement. An item with no source is not written.
- Nothing is published or sent without preview → go. Chat output is a draft, never a sent
  message.

## Non-goals

- Pre-release approval. Where a team has one (an engineer posts, leads approve), this skill reads
  it and does not replace it.
- Submitting to app stores, or sending announcements.
- An operator / customer edition in the floor. A team that needs one defines it in config.
- Measuring the release afterwards. That is `pm:readout`, which is held.

## Design

### 1. The unit: a version tag

- **A release is one tag.** Its contents are the changes between it and the previous tag matching
  `release.tag_pattern` in `release.repo`.
- **A repository with no tags** (designer's call): the release is the tracker milestone with the
  same name as the version. Where milestones are named by version, this is the same unit.
- **The tag is asked for when not given.** The skill shows the newest few that match. It never
  picks one silently.

### 2. Config

The floor shown here is in English. Every value is replaceable, and none of it is one team's.

```yaml
release:
  target: markdown            # markdown | git | notion — where editions are written
  out_dir: "./releases"       # markdown / git: one file per release, <tag>.md, one section per edition
  repo: null                  # owner/repo whose tags define releases. null → asked
  tag_pattern: "v*"           # which tags count as releases
  announcement:               # an announcement the team already posts. optional
    type: none                # chat | doc | none
    ref: null                 # a channel (read through the chat adapter) or a document location
  editions:
    internal:
      title: "Release note"
      reader: "people inside the company who answer for the product"
      sections: [Summary, Added, Changed, Fixed, Removed, Security, Known issues, Links]
      known_issues: true
    users:
      title: "What's new"
      reader: "people who use the product"
      sections: [What's new, Fixed]
      max_items: 5
      known_issues: false
```

- **Sections.** The section names follow Keep a Changelog's change types — Added, Changed,
  Deprecated, Removed, Fixed, Security — whose first principle is that a changelog is for humans
  (<https://keepachangelog.com/en/1.1.0/>). A section with nothing in it is left out.
- **A team's own template.** A team with an established release-note shape overrides
  `editions.*.sections` and `title` in its own config, in its own language.

### 3. What it reads

All of it is read-only, through the plugin's existing adapters.

1. **The changes between the two tags.** Commits and merged pull requests, through the
   repository host (`gh`).
2. **The tracker items behind them,** through `task.mirror` / `task.record`. Matching uses the
   adapter's link rules, never titles. From each item and its parent it takes the requirement, the
   done conditions and the QA pass list, the closest thing to a reader's sentence about the change.
   With no linked item, the change is written from its pull request and marked "no item".
3. **The announcement, where `release.announcement` names one.** It is read to confirm scope. An
   item announced but not in the tag range, or in the range but not announced, is listed for the
   person to settle. Neither is dropped or added silently.
4. **Open defects from QA** for the same version, for the internal note's known issues. Under
   local-first, `/fig:qa` writes its report to a markdown file (review S15). Where no report
   exists, the section says none were found, not that there are none.
5. **The handoff line** in each task record, for the internal note's design links.

When one source is missing, the skill goes on with the others and says which was missing (decision
4). The same rule `/pm:log` follows.

### 4. Writing the editions

- **Classify each change** into a change type, then drop what no reader of an edition needs.
  Internal refactors, build and CI changes, and dependency bumps stay out of the user notice.
  They appear in the internal note only when they change behaviour.
- **Voice.** prd's reader rules apply to every edition. A sentence says what someone sees or can
  do, and `prd.forbidden_terms` applies. The user notice also drops internal names: ticket
  numbers, code names, team names. It keeps to `max_items`, choosing by reader impact.
- **Known issues** go only where `known_issues: true` (decision 5). Each says what a reader will
  run into and what to do meanwhile, if there is a workaround.
- **Traceability.** Every item in the internal note links its source. The user notice carries no
  links, but the run's report maps each of its lines to a source.

### 5. Gates

- **Preview.** Every edition is shown in full before anything is written.
- **One go per destination.** The local file is one go. A Notion page or a git commit / PR is
  another, after the file.
- **Chat.** Where a team wants a chat version, it is saved as a draft through the chat adapter
  and never sent. This follows the skill set's rule that chat output stops at a draft.

### 6. Edges

- **A tag already written.** The existing file is shown beside the new draft, and the person
  chooses replace or keep. Never overwrite unseen.
- **A hotfix tag between two releases** is its own release. The previous matching tag is the
  boundary.
- **Private repositories** need an account that can read them. When access fails, the skill says
  so and stops, rather than writing from the announcement alone as though it were complete.

## Probes before building

Run on an account that sees the team's repositories:

- tag listing and comparing two tags through `gh`
- how often merged pull requests link to tracker items. This decides how much of an edition comes
  from items, and how much from pull request titles.

## Done when

- **Fixture repository** with two tags, linked items and one unlinked pull request:
  - both editions are written to `./releases/<tag>.md`
  - the unlinked change is marked "no item"
  - nothing appears with no source
- **Announcement configured:** a mismatch between the announcement and the tag range is listed,
  not resolved silently.
- **Known issues:** with a QA report present, they appear in the internal note only. With none
  present, the section says none were found.
- **No quiet writes:** nothing reaches Notion, git or chat without its own go, and chat output is
  a draft.
- **A team's override:** a config with its own edition sections and language produces them.
- **Checks and docs:** `bash tools/verify-all.sh` passes, and the READMEs and CHANGELOG are in place.

## Designer's calls — check these while reading

1. A repository with no tags falls back to the same-named version milestone.
2. The floor ships `internal` and `users` editions with Keep a Changelog sections.
3. Matching changes to items uses adapter link rules only. Unlinked changes are written from the
   pull request and marked.
4. Announcement / tag mismatches are listed for the person, never settled silently.
5. Internal-only changes are kept out of the user notice unless they change behaviour.
6. A local write and each external destination have their own go.
7. An existing release file is never overwritten unseen.
8. A private-repository access failure stops the run.

## Left to the builder

- `gh` calls, and pagination for long ranges.
- The exact classification prompts, and wording in `meta.language`.
- Version number, README and CHANGELOG text.
