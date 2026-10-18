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

- **Figma comments**, through the REST API with the token named in `tools.figma_token_env`
  (`GET /v1/files/:key/comments`, scope `file_comments:read`). The Figma MCP plugin's documented
  tools include no comment reader (plugin 2.2.157, checked locally), hence the token.
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
| Decided | The thread shows agreement on a change, and nothing later reopens it | A proposed PRD change |
| Open | A question, a disagreement, or a proposal with no agreement | A pin on the node it concerns |
| Out of scope | A request the current PRD does not cover | A task candidate |
| No action | Praise, acknowledgement, or a duplicate of another piece | The report only |

- **When a thread is unclear,** it is Open. Decided needs agreement visible in the thread itself,
  never inferred from silence.
- **Conflicting decisions** across sources make the piece Open. Both sources are quoted.

### 4. Writing back

- **Decided → `/pm:prd`.**
  - A list of proposed changes, each naming the PRD entry by the reader's name for it, quoting the
    feedback, and linking the source.
  - With `pm` installed, the list is handed to `/pm:prd` as an extend run, so its verification
    applies. That is the synergy rule from the local-first design.
  - Without `pm`, the list is printed.
- **Open → pins.** An annotation on the anchored node, in the wording `/fig:prep` and `/fig:draw`
  already use for undecided facts, so one search finds every open question in the file. It
  carries no category.
- **Out of scope → task candidates.**
  - A list in `/pm:task draft`'s input shape — the source and its quoted request.
  - With `pm` installed, the person can run draft on each.
  - Nothing is filed by this skill.

### 5. The original comments

- **Figma comments** whose piece was written back are resolved in the web app through the browser:
  open the comment, then *Resolve*.
  - This is the same route the version pin already uses, and it goes behind the same preview → go.
  - The status is read back in the page before anything is reported as resolved.
- **Gate.** Only after the resolve probe passes. Until then, and wherever no browser is connected,
  comments are left as they are, and the report lists which would have been resolved.
- **Chat threads** are never touched.

### 6. The report

One table in the conversation, not a file: each piece of feedback, its class, where it went, and a
link to both ends. Pieces left Open or No action are listed too, so nothing silently disappears.

## Probes before building

On an account with an edit seat on a real file:

1. **Reading comments** through REST with the configured token. Confirm node anchors and replies
   come back as described.
2. **Resolving a comment** in the web app through the browser, and reading the resolved state
   back.

If probe 1 fails, the skill does not ship. If probe 2 fails, section 5's resolve step is dropped
and comments are left as they are.

## Done when

- **Fixture file** with anchored comments covering all four classes:
  - each goes to exactly one place
  - pins use the undecided wording with no category
  - the report lists every comment
- **pm installed:** decided pieces arrive in `/pm:prd` as an extend run.
- **pm absent:** the list is printed.
- **No invented decisions:** an ambiguous thread is classed Open.
- **No quiet writes:** pins, the PRD hand-off and resolves each wait on preview → go.
- **Probe 2 failed or no browser:** no comment changes state.
- **Checks and docs:** `bash tools/verify-all.sh` passes, and the READMEs and CHANGELOG are in place.

## Designer's calls — check these while reading

1. On demand only, with an explicit scope.
2. Four classes. Unclear threads and conflicting decisions are Open, and Decided needs visible
   agreement.
3. Open pins reuse prep/draw's undecided wording and carry no category.
4. Task candidates are a list for `/pm:task draft`. This skill files nothing.
5. No summary document. The report is a table in the conversation.
6. Resolving goes through the web app, behind the probe and preview → go. Chat threads are never
   touched.
7. Pasted notes are placed on nodes only when the person says where.

## Left to the builder

- REST pagination, and the date filter.
- How a node anchor is resolved when the node has since been deleted (report it, place nothing).
- Wording in `meta.language`. Version, README and CHANGELOG text.
