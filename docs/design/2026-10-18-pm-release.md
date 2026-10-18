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
| 4 | What it reads | Both: an announcement the team already posted (when the person passes its link) to confirm scope, and the tracker's items to write the sentences | Tickets only; the announcement only |
| 5 | Known issues | In the internal note only | Both editions; neither |
| 6 | Generic, not one team's | Channel, template and cadence are config values | Building around the owner's company's release practice |

## Goals

- From one tag, write every configured edition, each in its readers' words.
- Every item in an edition traces to a source: a ticket, a change between tags, or the
  announcement. An item with no source is not written.
- Nothing is published without preview → go.

## Non-goals

- Pre-release approval. Where a team has one (an engineer posts, leads approve), this skill reads
  it and does not replace it.
- Submitting to app stores, or sending announcements.
- A chat edition in the first version. No chat adapter has a write call, and the repository ships
  only calls that were run (`trackers/README.md:37-42`). A team pastes the file's text where it
  wants it.
- An operator / customer edition in the floor. A team that needs one defines it in config.
- Measuring the release afterwards. That is `pm:readout`, which is held.

## Design

### 1. The unit: a version tag

- **A release is one tag.** Its contents are the changes between it and the previous *release*
  tag in `release.repo`. Release tags match `release.tag_pattern`, and pre-release tags such as
  `-rc` and `-beta` are excluded by `release.prerelease_pattern`. Without the exclusion, a final
  release's range would shrink to "the last release candidate → final" (designer's call).
- **A repository with no tags** (designer's call): the person is asked for the range — two refs,
  or a milestone name where a GitHub mirror with milestones is configured
  (`task.hierarchy.milestone_projects`). Milestones exist only there; the floor has none.
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
  prerelease_pattern: "-(rc|beta|alpha)"   # tags matching this are never a release boundary
  item_ref_pattern: null      # a regex for a ticket key or task-file name in a PR's title, body
                              # or branch, e.g. "[A-Z]+-[0-9]+". null → closing references only
  defects:                    # where open defects for a version are read, for known issues
    label: null               # the tracker label or type that marks a defect. null → skipped
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
2. **The tracker items behind them.** No adapter today says which item a pull request belongs to;
   the only link is record → ticket url. That question is new, so the tracker adapter contract
   (`trackers/README.md`) gains a row for it. The match runs in this order (designer's call):
   1. The repository host's own closing references (e.g. "Closes #123") to issues in a GitHub
      mirror.
   2. `release.item_ref_pattern`, searched in the pull request's title, body and branch. It finds a
      ticket key or a task file name, which is then resolved through the adapter.
   3. Otherwise "no item". The change is written from its pull request alone, and marked so.

   Never matched by title. From each matched item and its parent, the skill takes the requirement,
   the done conditions and the QA pass list — the closest thing to a reader's sentence about the
   change. Done conditions and QA lists live on mirror tickets. Under the local floor (markdown
   record, no mirror), expect most changes to be "no item" unless pull requests name their task
   file. The report says how many matched.
3. **The announcement, when the person passes its link** (designer's call: no channel search in
   the first version). A chat-thread link is read the way `/pm:task draft` reads a thread; a
   document link is read with the doc tool the team uses. It is read to confirm scope. An item
   announced but not in the tag range, or in the range but not announced, is listed for the
   person to settle. Neither is dropped or added silently.
4. **Open defects** for the same version, for the internal note's known issues.
   - Read from the tracker: open items carrying `release.defects.label` under that version.
   - A QA report file, if the person passes one, is read as well. `/fig:qa` writes no file today;
     review S15 proposes one.
   - With neither, the section says none were found, not that there are none.
5. **The handoff line** in each matched task record, for the internal note's design links. It sits
   under the heading key review S14 settles.

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

### Build order

Built after the local-first change and the `/pm:task` merge, on the markdown floor:

- S13: the markdown tracker's file-name rule
- S14: the handoff heading key
- the adapter row in section 3

Building it on today's three task skills would mean rewriting it at the merge.

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
- how often merged pull requests in a recent range link to tracker items, counted as the share
  matched by closing references or by `item_ref_pattern`. This decides how much of an edition
  comes from items, and how much from pull request titles.
- reading open defects by label under a version, through the mirror adapter

## Done when

- **Fixture repository** with two tags, linked items and one unlinked pull request:
  - both editions are written to `./releases/<tag>.md`
  - the unlinked change is marked "no item"
  - nothing appears with no source
- **Announcement configured:** a mismatch between the announcement and the tag range is listed,
  not resolved silently.
- **Known issues:** with a QA report present, they appear in the internal note only. With none
  present, the section says none were found.
- **No quiet writes:** nothing reaches Notion or git without its own go.
- **Pre-release tags:** with an `-rc` tag between two finals, the final release's range starts at
  the previous final.
- **A team's override:** a config with its own edition sections and language produces them.
- **Checks and docs:** `bash tools/verify-all.sh` passes, and the READMEs and CHANGELOG are in place.

## Designer's calls — check these while reading

1. A repository with no tags means the range is asked for: two refs, or a milestone where a
   GitHub mirror has them.
2. The floor ships `internal` and `users` editions with Keep a Changelog sections.
3. A change is matched to an item by closing references first, then `item_ref_pattern`, never by
   title. Unmatched changes are written from the pull request and marked. The adapter contract
   gains that row.
4. Announcement / tag mismatches are listed for the person, never settled silently.
5. Internal-only changes are kept out of the user notice unless they change behaviour.
6. A local write and each external destination have their own go.
7. An existing release file is never overwritten unseen.
8. A private-repository access failure stops the run.
9. Pre-release tags never bound a release.
10. The announcement is read only from a link the person passes; there is no channel search in the
    first version.
11. Known issues come from tracker defects by label, plus a QA report file if one is passed.
12. No chat edition in the first version.
13. Built after the local-first change and the `/pm:task` merge.

## Left to the builder

- `gh` calls, and pagination for long ranges.
- The exact classification prompts, and wording in `meta.language`.
- Version number, README and CHANGELOG text.
