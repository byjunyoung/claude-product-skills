# fig:review — send design-review feedback back where it belongs

Status: design, 2026-10-18. Decisions agreed with the owner; the designer's calls are pending the
owner's review. Not built. Third item of the skill review's D2 (`2026-10-18-skill-review.md`).
Gated on two probes (see *Probes*).

## Intent

After a design review, the feedback sits in comments on the Figma file and in chat threads. Some
of it settles something, some of it opens a question, and some of it asks for work outside this
release. Unless someone carries each piece to where it belongs, decisions are lost and open
questions are forgotten:

- a decision belongs in the requirements
- an open question belongs on the screen it concerns
- a new request belongs on the task list

The value is in that write-back. A summary list on its own would repeat the lesson of the removed
`/fig:diff`: a table nobody reads. So this skill writes no summary document of its own (designer's
call). What it changed is in the run's report.

## Decisions

| # | Question | Chosen | Not chosen |
|---|---|---|---|
| 1 | Where feedback is read from | Figma comments on the file, and chat threads through the chat adapter. Pasted notes are always accepted | Meeting notes in a document tool |
| 2 | How decisions reach the PRD | A list of proposed PRD changes handed to `/pm:prd`, so prd's checks apply. With `pm` absent, the list is printed | fig:review editing the PRD directly; screen notes only |
| 3 | What happens to the original comments | Figma comments are resolved once the resolve path is proven (through the web app, after preview → go). Until then, and for chat threads, they are left as they are | Replying on each comment; leaving them always |
| 4 | Where an agreed design change goes — one that changes how a screen looks, not what it does | Handed to `/fig:draw` as a per-screen change list. draw runs its own direction agreement before drawing | A "to apply" pin on the screen; recording it in the PRD |

## Goals

- Every piece of feedback in scope ends in exactly one place — a proposed PRD change, a pin on a
  node, a task candidate, or "no action" — and the report says which.
- No feedback is turned into a decision that the thread did not reach.
- Nothing is written to Figma, the PRD or a tracker without preview → go.

## Non-goals

- AI critique of the design. Other skills do that, and this one reads what people said.
- Summarising comments into a Figma Spec. Figma's own agent offers that.
- Replying in chat threads, or sending anything.

## Design

### 1. Calling it

Called by name, with a scope (designer's call):

- a Figma file and optionally a page or section, plus a date to read from
- and/or chat thread links
- and/or pasted notes

It does not run on a schedule. The writes it proposes need a person.

### 2. Reading

- **Figma comments.** Two possible paths, in this order:
  1. An MCP comment reader. The public tool list of the Figma plugin (2.2.157) shows none, but its
     Cursor-only variant documents a `get_comments` tool (`skills-figquery/figma-use/SKILL.md:241`).
     Probe 1 tries this first.
  2. The REST API (`GET /v1/files/:key/comments`), with the token named in
     `tools.figma_token_env`. The token needs the `file_comments:read` scope. A token made by the
     repository's current guidance (file content, read-only) gets a 403 here. Write the needed
     scopes where the READMEs list what each skill needs; review S4 removes `/fig:read`'s token
     section, where that guidance lives today.
  - Each comment's node anchor, if any, ties it to a screen.
  - Replies are read with their root.
  - Already-resolved threads are skipped.
- **Chat threads,** through the chat adapter (`sources/<chat_type>.md`), parent and replies, as
  `/pm:task draft` reads them.
- **Pasted notes** are taken as given. They carry no anchor, so placing them on a node is asked,
  not guessed.

Source: <https://developers.figma.com/docs/rest-api/comments-endpoints/> (read, post, delete and
reactions only; no resolve endpoint).

### 3. Sorting

Each piece of feedback gets one class (designer's call on the rules).

| Class | Test | Goes to |
|---|---|---|
| Decided — requirement | Agreement on a change to what the product does: a behaviour, a rule, a condition | A proposed PRD change → `/pm:prd` |
| Decided — design | Agreement on a change to how a screen looks: size, spacing, order, wording on screen, layout | A per-screen change → `/fig:draw` (decision 4) |
| Open | A question, a disagreement, a proposal with no agreement, or a new request nobody agreed to | A pin on the node it concerns |
| Deferred | Agreed to do, but explicitly not in this release | A task candidate |
| No action | Praise, acknowledgement, or a duplicate of another piece | The report only |

- **When a thread is unclear,** it is Open. Decided needs agreement visible in the thread itself,
  never inferred from silence.
- **Conflicting decisions** across sources make the piece Open. Both sources are quoted.
- **A decision that changes both behaviour and looks** goes to both, as two pieces with one source.
- **Deferred replaces "out of scope"** (designer's call). It is judged from the thread's own words
  ("next release", "later"), not by comparing against the PRD. So sorting does not depend on
  finding a PRD.

### 4. Writing back

- **Decided — requirement → `/pm:prd`.**
  - A list of proposed changes, each naming the PRD entry by the reader's name for it, quoting the
    feedback, and linking the source comment.
  - With `pm` installed, the list is handed to `/pm:prd` as an extend run, so its verification
    applies. That is the synergy rule from the local-first design.
  - Without `pm`, the list is printed.
  - `/pm:prd` has no input for such a list today; its extend mode starts from its own gathering
    interview (prd SKILL.md:75-80). Section 2.2 gains a unit of work that takes a proposed-changes
    list as its material. That pm change is part of this build, with its own version and
    CHANGELOG line. The source link goes under the entry's References, which is what a later run
    checks.
- **Decided — design → `/fig:draw`.**
  - A per-screen list: the node link, the change in the reader's words, and the quoted feedback
    with its source link.
  - It is handed to `/fig:draw` as its target. draw runs its own sketch and agreement step before
    anything is drawn, so fig:review never draws.
- **Open → pins.**
  - An annotation on the anchored node, in `/fig:draw`'s undecided-fact form, with no category.
  - `/fig:prep` writes undecided text into placeholders instead (`prep-ops.js:105`), so finding
    every open question takes two searches, not one.
  - The pin carries the source comment's link.
- **Deferred → task candidates.**
  - A list in `/pm:task draft`'s input shape: the source and its quoted request.
  - With `pm` installed, the person can run draft on each.
  - Nothing is filed by this skill. This depends on the `/pm:task` merge (local-first §7) for its
    name.

**Running it again (designer's call).** Every destination carries the source comment's link: the
pin, the PRD entry's References, the draw hand-off, the task candidate. A later run skips any
comment whose link already appears at its destination, so pins and proposals are not repeated.
The date filter is secondary.

### 5. The original comments

- **Which comments, and when (designer's call).** A Figma comment is resolved only when its piece
  reached its destination in this run, and that destination was read back:
  - **No action:** after the report is shown.
  - **Decided — requirement / design:** after the person confirms in the same session that the
    `/pm:prd` or `/fig:draw` run it was handed to finished. Those runs have their own interviews, so
    this skill cannot see their outcome. Otherwise the comment is listed as "resolve after hand-off".
  - **Open and Deferred:** never. The discussion is still live, or the request is not yet filed.
- **How.** Resolved in the web app through the browser — open the comment, then *Resolve* — the
  same kind of route the version pin uses. It goes behind its own preview → go, in the order
  review S5 sets out for handoff: preview, go, write, read back. The status is read back in the
  page before anything is reported as resolved.
- **Gate.** Only after the resolve probe passes. Until then, and wherever no browser is connected,
  comments are left as they are, and the report lists which would have been resolved.
- **Chat threads** are never touched.

### 6. The report

One table in the conversation, not a file: each piece of feedback, its class, where it went, and a
link to both ends. Pieces left Open or No action are listed too, so nothing silently disappears.

## Probes before building

On an account with an edit seat on a real file:

1. **Reading comments.** First through an MCP comment reader if one is exposed, then through REST
   with a token carrying `file_comments:read`. Confirm node anchors and replies come back as
   described.
2. **Resolving a comment** in the web app through the browser, and reading the resolved state
   back.

If probe 1 fails, the skill does not ship. If probe 2 fails, section 5's resolve step is dropped
and comments are left as they are.

## Done when

- **Fixture file** with anchored comments covering all five classes:
  - each goes to exactly one place, or two for a decision that changes both behaviour and looks
  - pins use draw's undecided form with no category
  - the report lists every comment
- **Second run:** run on the same file, it proposes nothing already placed.
- **pm installed:** requirement decisions arrive in `/pm:prd` through its new proposed-changes unit.
- **Design decisions:** they arrive in `/fig:draw` as targets, and nothing is drawn by this skill.
- **pm absent:** the list is printed.
- **No invented decisions:** an ambiguous thread is classed Open.
- **No quiet writes:** pins, the PRD hand-off and resolves each wait on preview → go.
- **Probe 2 failed or no browser:** no comment changes state.
- **Checks and docs:** `bash tools/verify-all.sh` passes, and the READMEs and CHANGELOG are in place.

## Designer's calls — check these while reading

1. On demand only, with an explicit scope.
2. Five classes. Unclear threads, conflicting decisions and unagreed new requests are Open, and
   Decided needs visible agreement.
3. Open pins use draw's undecided annotation form and carry no category.
4. Deferred (agreed, not this release) replaces "out of scope". Task candidates are a list for
   `/pm:task draft`, and this skill files nothing.
5. No summary document. The report is a table in the conversation.
6. Resolving goes through the web app, behind the probe and preview → go. Chat threads are never
   touched.
7. Pasted notes are placed on nodes only when the person says where.
8. Every destination carries the source comment's link, and a rerun skips what is already placed.
9. Comments are resolved only after their destination is confirmed. Open and Deferred are never
   resolved.
10. `/pm:prd` gains a proposed-changes unit of work in this build.
11. Comment reading tries an MCP reader before REST. The REST token needs `file_comments:read`.

## Left to the builder

- REST pagination, and the date filter.
- How a node anchor is resolved when the node has since been deleted (report it, place nothing).
- Wording in `meta.language`. Version, README and CHANGELOG text.
