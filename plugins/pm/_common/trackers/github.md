# GitHub as the mirror

connector: GitHub
roles: mirror

The calls behind the abstract steps in `/pm:task-publish` and `/pm:task-sync`, for a mirror
whose `task.mirror.type` is `github`. Every placeholder in braces comes from the config —
`{repo}` is `task.mirror.ref`, and everything under `{extras.*}` is `task.mirror_extras`.

**These are recovered from a working setup, gotchas included.** Where a line carries a warning,
the warning is there because it was hit.

## The rule document

Where `task.policy.doc` is set, read it before the first write of the session. A private repo
serves nothing over the plain URL, so go through the API — the same credentials the writes use:

```bash
# from a github.com/{owner}/{repo}/blob/{ref}/{path} url
gh api "repos/{owner}/{repo}/contents/{path}?ref={ref}" --jq '.content' | base64 -d
```

**A 404 here is usually the token, not the path** — a doc in another repo needs a token scoped
to that repo. Say which document could not be read rather than proceeding as if none was named.

## Reading

```bash
# every task and parent on the board, with title, status, milestone and url
gh project item-list {extras.project_number} --owner {extras.project_owner} \
  --format json --limit {above the board's item count}

# open / closed is a property of the issue, not the board column — read it separately
gh issue view {n} --repo {repo} --json state,body --jq '{state, body}'

# EVERY issue for a project — this is the exhaustive read, and --paginate is why
gh api -X GET "repos/{repo}/issues" -f labels="{project label}" -f state=all \
  -f per_page=100 --paginate --jq '.[] | {number, title, state, url: .html_url}'

# candidate parents for a project
gh issue list --repo {repo} --label "{project label}" --state open \
  --json number,title,url \
  --jq '.[] | select(.title | test("\\[{parent_kind}\\]"; "i"))'
```

**`gh issue list --limit N` truncates the same way, and what it drops is the half you
need.** It returns newest-first, so a limit below the real count silently discards the
*oldest* issues — which are the closed ones. On one project `--limit 300` returned exactly
300 rows: open issues were complete at 113, while closed came back as 187 against a true
427. Every `resurrected` and `duplicate` verdict rests on closed issues, so a limited
listing does not merely under-report, it under-reports precisely where the diagnosis
lives. Use the `--paginate` call above for any read a verdict depends on, and keep
`gh issue list` for eyeballing.

**`item-list` truncates silently, and a big board cannot be listed at all.** The default
`--limit` is 30. Raising it does not solve the problem, it moves it: on one real board
`--limit 400` returned exactly 400 rows — the newest item was not among them — and
`--limit 2000` did not return inside two minutes. A truncated read is worse than a failed
one, because `/pm:task-sync` reads the missing rows as *unfiled* and offers to create
tickets that already exist.

**For a read a verdict depends on, page the board through GraphQL instead.** `--paginate`
follows `pageInfo` itself, so there is no limit to guess at and nothing is cut without
saying so. The same call also carries what `item-list` does not: each task's parent and
that parent's milestone — where a version is read when `milestone_on` is `parent` — so one
request replaces a listing plus a second pass over every issue.

```bash
gh api graphql --paginate --slurp -F query=@board.graphql > board.json
```

```graphql
query ($endCursor: String) {
  organization(login: "{owner}") {            # a personal account: user(login:)
    projectV2(number: {n}) {
      items(first: 100, after: $endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content { ... on Issue {
            number title state stateReason url
            milestone { title }
            issueType { name }
            parent { number title state milestone { title } }
            assignees(first: 5) { nodes { login } }
            labels(first: 20) { nodes { name } }
          } }
          fieldValues(first: 25) { nodes {
            ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2SingleSelectField { name } } }
            ... on ProjectV2ItemFieldDateValue        { date field { ... on ProjectV2Field { name } } }
          } }
        }
      }
    }
  }
}
```

**Give the query as a file — `-F query=@file`, not an inline `-f query='…'`.** A multi-line
query inline mis-parses on a brace the shell reflowed, and the error names a line and column
in a string nobody can see. `--slurp` returns one array whose elements are pages, so flatten
`nodes` across them, and an item whose `content` is null is a draft rather than an issue.

So: **compare the returned count against the limit you asked for. Equal means truncated —
say so in the coverage line rather than treating the read as exhaustive.** When you only need
to confirm one item you already have the id for, address it directly instead of listing:

```bash
# one board item, by the id `item-add` returned
gh api graphql -f query='{ node(id: "{item id}") { ... on ProjectV2Item {
  content { ... on Issue { number title } }
  fieldValues(first: 25) { nodes {
    ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2SingleSelectField { name } } }
    ... on ProjectV2ItemFieldDateValue        { date field { ... on ProjectV2Field { name } } }
  } } } } }'
```

## Creating a task

```bash
gh issue create --repo {repo} \
  --title "{task.ticket.title, filled in}" \
  --body  "{assembled body}" \
  --label "{default_labels},{priority label},{project label}" \
  --assignee "{mapped username}"
```

**A 5xx from `issue create` does not mean the issue was not created.** One real run got
`503 Service Unavailable ... connection termination` and the issue was already there — the
error came after the write. Retrying on the error would have filed it twice. Before any retry,
list the newest issues and match the **exact** title you sent:

```bash
gh issue list --repo {repo} --state all --limit 20 \
  --json number,title,createdAt --jq '.[] | select(.title == "{the exact title}")'
```

**Do not reach for `--search` here.** It lies in two directions, and one run hit both. A
partial title matches something else — a search on a fragment returned an unrelated ticket
from another project, which was then reported as the one just created. And the search index
lags: an issue confirmed to exist by number came back as zero results a moment after it was
made. **An empty search is not evidence of absence.** The listing above goes at the issues
endpoint directly and has neither problem.

Creating several in one pass, confirm each by number before starting the next, and do not
trust a loop's own bookkeeping about which title went where.

The same caution applies to every write below: on a network-level error, read the current
state before acting on the assumption that nothing happened.

**Never pass `--milestone` on a task** where `task.hierarchy.milestone_on` is `parent`.
The parent owns the milestone; a task carrying one is the policy violation `/pm:task-sync`
reports as `Policy`.

## Creating a parent

```bash
gh issue create --repo {repo} \
  --title "{task.hierarchy.parent_title, filled in}" \
  --body  "{one line: what this parent covers}" \
  --label "{default_labels},{priority label},{project label}" \
  --assignee "{mapped usernames}"
```

**Seed it with a sentence, never with headings of your own.** The contract arrives later under
the names `contract.sections` gives, and the writer leaves every section it does not own byte
for byte — so a heading invented by this call outlives all of it, sitting beside the real ones.
Where the tracker has an issue template for parents, its headings are the ones to start from.

The issue **type** is not a CLI flag — it is a GraphQL mutation, and it must be set or the
item shows up untyped on the board:

```bash
gh api graphql -f query='
  mutation { updateIssue(input: {
    id: "{parent node id}", issueTypeId: "{extras.epic_issue_type}"
  }) { issue { id } } }'
```

## Attaching a task to its parent

```bash
gh api graphql -f query='
  mutation { addSubIssue(input: {
    issueId: "{parent node id}", subIssueId: "{task node id}"
  }) { issue { id } } }'
```

## Putting it on the board

```bash
# add — takes the project NUMBER
gh project item-add {extras.project_number} --owner {extras.project_owner} \
  --url {issue url} --format json --jq '.id'
```

**Capture that id.** Every field write below addresses the *item*, not the issue, and there is
no second way to look it up cheaply.

```bash
# the single-select project field
gh api graphql -f query='
  mutation { updateProjectV2ItemFieldValue(input: {
    projectId: "{extras.project_node_id}",
    itemId:    "{item id}",
    fieldId:   "{extras.project_field_id}",
    value: { singleSelectOptionId: "{extras.project_field_options[label]}" }
  }) { projectV2Item { id } } }'

# the status column — only where task.status_map has an entry for the record's status
gh api graphql -f query='
  mutation { updateProjectV2ItemFieldValue(input: {
    projectId: "{extras.project_node_id}",
    itemId:    "{item id}",
    fieldId:   "{extras.status_field_id}",
    value: { singleSelectOptionId: "{extras.status_field_options[status_map[record status]]}" }
  }) { projectV2Item { id } } }'

# the date fields — task only. A parent's schedule is managed elsewhere
gh project item-edit --project-id {extras.project_node_id} --id {item id} \
  --field-id {extras.start_date_field} --date {YYYY-MM-DD}
gh project item-edit --project-id {extras.project_node_id} --id {item id} \
  --field-id {extras.end_date_field}   --date {YYYY-MM-DD}
```

**`item-add` takes the project number; `item-edit` takes the project node id.** They are not
interchangeable and the error message does not say which one it wanted.

## Milestones

Only where the project appears in `task.hierarchy.milestone_projects`.

```bash
# what already exists, open only, so the interview offers real options
gh api repos/{repo}/milestones --paginate \
  -q '.[] | select(.title | startswith("{prefix}")) | select(.state=="open") | .title'

# create one, after a preview — ONLY where milestone_format has an entry for this project
# a map keyed by project name takes this project's entry; one string serves every project
gh api -X POST repos/{repo}/milestones -f title="{task.hierarchy.milestone_format, filled in}"

# set it on the parent
gh issue edit {parent number} --repo {repo} --milestone "{title}"
```

**A project in `milestone_projects` with no `milestone_format` entry still uses milestones** —
it is another team's naming, not an omission. Offer the open ones the listing returned and
create nothing. A milestone invented in that project's name sits beside theirs looking official,
and label derivation reads the title's prefix, so a wrong one mislabels every issue under it.

**`{prefix}` is the project's own name as the tracker spells it**, which is not always the
project label's — a listing filtered on the wrong spelling comes back empty and reads as "this
project has no milestones", which is how the invented one gets created.

## Updating an existing ticket

```bash
gh issue view {n} --repo {repo} --json body --jq .body     # read before you overwrite
gh issue edit {n} --repo {repo} --body "{new body}"
```

Keep the row that links back to the record. It is what a person clicks to find the detail —
it is never what matching reads.

## Finding the ids for `mirror_extras`

`/pm:setup` runs these for you. They are here so the values can be checked by hand.

```bash
# project node id
gh api graphql -f query='{ organization(login: "{owner}") {
  projectV2(number: {n}) { id } } }' --jq '.data.organization.projectV2.id'

# fields, and the option ids of every single-select
gh api graphql -f query='{ organization(login: "{owner}") { projectV2(number: {n}) {
  fields(first: 50) { nodes {
    ... on ProjectV2Field { id name }
    ... on ProjectV2SingleSelectField { id name options { id name } }
  } } } } }'

# issue types available to the org
gh api graphql -f query='{ organization(login: "{owner}") {
  issueTypes(first: 20) { nodes { id name } } } }'
```

For a personal account rather than an org, swap `organization(login:)` for `user(login:)`.
