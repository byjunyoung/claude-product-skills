# PRD goals, metrics and scope

Status: design, 2026-10-18. Decisions 1–5 agreed with the owner; the designer's calls are pending
the owner's review. Not built. This is the first item of the skill review's D2
(`2026-10-18-skill-review.md`, define-further 1).

## Intent

A PRD that cannot say how success will be measured leaves the measure-and-learn stage with
nothing to start from. The skill review first read this as "prd has no goals or metrics". That is
true of `/pm:prd`'s body and of the bundled floor, but not of how teams actually work.

**A team's own PRD template**, in use with this plugin, already carries a goals-and-scope
subsection with three rows:

- goals and metrics
- scope in / out
- non-goals

Its guidance asks for "one or two quantitative metrics" beside the goals.

**A PRD written from that template** has well-formed goals and a filled scope. Its metric row,
though, reads "TBD (to be settled once the measurement criteria and the data are in place)".

So two things are wrong:

1. **The structure lives only in one team's template.** The skill does not know it, and the floor
   does not ship it. Someone without that template gets no goals-and-metrics shape at all.
2. **Metrics stall as a single TBD.** The measurement criteria wait on the data, so nothing about
   the metric is decided, even the parts that need no data.

The fix is to generalize the template's subsection into the skill, and to split a metric into
what can be settled now and what has to wait for numbers.

## Decisions

| # | Question | Chosen | Not chosen |
|---|---|---|---|
| 1 | How metrics stop stalling | Settle the measurement plan now (what, from where, when); only the numbers wait, as TBD with who · what · when | Requiring target values before the PRD is confirmed; free text with an emptiness check only |
| 2 | Shape of one metric | A six-column row: goal, metric, data source, check at, current value, target value. One or two metrics per goal | The same plus a leading / lagging split; one sentence per metric |
| 3 | What the skill proposes | Per column. It proposes metric, check-at and data-source candidates with their grounds. It never proposes a number: values come only from a real source, cited, otherwise TBD | Proposing benchmark ranges for targets; proposing nothing |
| 4 | Checks | ① a scope-out item appears as a requirement; ② a goal with neither a metric nor a TBD carrying who · what · when; ③ a metric that cannot be counted | Linking every requirement to a goal; flagging metrics whose check date has passed |
| 5 | Existing PRDs | Not backfilled. New PRDs only | Prompting when an old PRD is next opened; a one-off sweep |

## Goals

- **A new PRD** has a goals-and-scope subsection with numbered goals, a metric table, scope in /
  out and non-goals, whatever its target (markdown, git, Notion).
- **Every metric row** settles its metric, data source and check-at, or carries a TBD that says
  who, what and when.
- **No number in the table** comes from anywhere but a cited source.

## Non-goals

- Analytics or dashboard connectors. Data sources are named, not queried.
- Backfilling existing PRDs (decision 5).
- Requirement-to-goal tracing, and reminders when a check date has passed (decision 4). The second
  belongs with `pm:readout`, which is held.

## Anti-goals

- A plausible-looking target value with no source behind it.
- A metric row that reads as decided when its data source was never confirmed to exist.

## Design

### 1. Structure

**Two new config keys**, under `prd.structure`, plus a pointer saying which overview item holds
them (designer's call). The bundled floor ships English names; a team's config overrides them,
like every other structure key.

```yaml
prd:
  structure:
    overview: [One-line definition, Background, Core value, Goals and scope, User groups]
    goals_item: Goals and scope        # which overview item carries the rows below
    goal_rows: [Goals and metrics, Scope in / out, Non-goals]
    metric_columns: [Goal, Metric, Data source, Check at, Current value, Target value]
```

**What the goals item holds,** in the PRD body:

```
Goals and scope
├─ Goals and metrics
│    ① <goal>
│    ② <goal>
│    | Goal | Metric | Data source | Check at | Current value | Target value |
│    | ①    | ...    | ...         | ...      | TBD — ...     | TBD — ...    |
├─ Scope in / out
│    In  — ...
│    Out — ...
└─ Non-goals
     — ...
```

- Goals are outcomes, numbered, so a metric row names its goal by number.
- One or two metrics per goal. More is allowed, but the skill does not propose a third.
- **Notion target:** the table sits under the goals-and-metrics row of the template's subsection.
  It replaces the row's placeholder text, and nothing else.
- **markdown / git target:** the same shape in the PRD file.

### 2. The measurement plan comes first

A metric row has two kinds of column.

| Settled now | Waits for data |
|---|---|
| Goal, Metric, Data source, Check at | Current value, Target value |

- **Settled now.** The interview settles these when the PRD is written. They need no data. A data
  source that nobody has confirmed exists is written as "source unconfirmed", not left looking
  settled.
- **Waits for data.** Each holds either a number with its source — a link, a file, a query name —
  or "TBD — who · what · when". The template's own rule holds: with any of the three missing, the
  TBD counts as empty.

### 3. What the skill proposes

This follows prd's existing method of gathering material first and offering a recommended answer
that a single go can accept.

| Column | Proposed? | From where |
|---|---|---|
| Metric | Yes, as a recommended answer | Derived from the goal's wording. Phrased as something counted: a rate, a count, a time, a share |
| Check at | Yes, as a recommended answer | A period after release, e.g. two weeks after release |
| Data source | Yes, only with a ground | Something the connected code repository actually records, cited to the file — a logged event, a stored field, an order record. Otherwise "source unconfirmed" |
| Current value, Target value | **Never** | A value read from a real source, with the source cited. Otherwise TBD |
| TBD's who · when | Yes, as a recommended answer | For the person to confirm. Not filled in silently |

No benchmark ranges, no "industry typical" figures and no comparable-product targets. A number
with no source becomes an anchor the team never chose.

### 4. Checks

These are added to prd's read-only verification (section 3 of the skill), before anything is
written.

- **① Scope-out leak.** An item under "Out" whose name, or whose core requirement text, matches a
  requirement entry. It is reported as a candidate with both texts side by side, never auto-failed
  (designer's call). The match is by meaning as well as by name, so a person decides.
- **② Unmeasured goal.** A numbered goal with no metric row, and no TBD that carries who · what ·
  when.
- **③ Uncountable metric.** A metric with nothing to count, such as "better satisfaction" or
  "improved convenience". This extends prd's existing check for thresholds nobody can count to the
  metric column.

Each check is a warning in the verification report, with the row it points at. None of them blocks
writing; the person decides.

### 5. When the checks run

Decision 5 limits the change to new PRDs (designer's call on what that means in practice).

- The overview checks run when a PRD is written new (prd 2.1), or when its goals item is the thing
  being edited.
- Extending an existing PRD — adding an entry, updating an entry, adding a user group — does not
  run them. An old PRD with a single "metrics TBD" is not flagged on every visit.

### 6. Config, documents and the team layer

- **`conventions.example.yaml`.** Add `goals_item`, `goal_rows` and `metric_columns` with comments.
  Per repository convention, the comment says what each key governs and what `null` does. With
  `goals_item: null`, the subsection is not written and the checks are skipped.
- **`/pm:prd` body.** Section 2.1 item 1 describes the goals item. Section 3 gains the three
  checks. The appendices show the table shape.
- **READMEs.** Describe the new subsection and checks in the pm README and both root READMEs,
  English first.
- **Team layer (outside this repository).** A team that already writes this subsection in its own
  language adds its names for the three keys to its config, so its PRDs keep the template's
  wording. For the owner's team-config repository, this is a shared write: preview → go at
  implementation.

## Done when

- **markdown target, no config:** a new PRD has the goals item with numbered goals, a metric table
  in the floor's column names, scope in / out and non-goals.
- **No invented numbers.** In a fixture where the repository has no recorded data, every current
  and target value is TBD with who · what · when, and every data source is either cited or
  "source unconfirmed".
- **The checks fire.** Each of ① ② ③ fires on a fixture written to trigger it, and on none of the
  others.
- **Old PRDs stay quiet.** Extending an existing PRD that has a bare "metrics TBD" runs none of the
  overview checks.
- **A team with its own names** (a config that overrides the three keys) gets its own column and
  row names in the output.
- **Checks and docs.** `bash tools/verify-all.sh` passes, and the CHANGELOG entry and version
  bump are in place.

## Designer's calls — check these while reading

1. A `goals_item` pointer names which overview item carries the rows. `null` turns the subsection
   and its checks off.
2. Goals are numbered, and metric rows refer to them by number.
3. The skill proposes at most two metrics per goal.
4. A data source nobody confirmed is written "source unconfirmed".
5. Check ① reports candidates side by side and never auto-fails. Matching is by meaning as well as
   by name.
6. All three checks are warnings that do not block writing.
7. "New PRDs only" means the checks run when a PRD is written new, or when its goals item is
   edited.
8. In Notion, the table replaces only the placeholder of the goals-and-metrics row.

## Left to the builder

- Exact wording of the interview prompts and warnings, in `meta.language`.
- Fixture content for the checks.
- Version number and CHANGELOG wording.
