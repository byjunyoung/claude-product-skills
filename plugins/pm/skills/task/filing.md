# filing — the rules for putting a ticket in the tracker

Read by `publish.md` where it files a ticket, and by `sync.md` where it creates one. The title rules are in `SKILL.md`, in the section on writing for the people who act on the ticket, and both modes follow them; *Labels* also depends on *The tracker's own rules — `publish` and `sync`* there. This file holds the rest. Both adapters are read before any of this runs — *Adapters* in `SKILL.md` — so every call to either side is the one they give.

## Resolve the parent

Only where `task.hierarchy.parent_kind` is set. With it `null`, tasks are a flat list — there is nothing to resolve.

Search the mirror for open parents **of this task's project**, and read their titles to find
the one this task belongs under.

Do not filter the candidates by group. The group is a hint, not a key: a team that adopted a
`[{parent_kind}] [{group}] ...` title convention partway through has older parents without the
bracket, and those are exactly the long-running ones a new task most often belongs to. Filtering
on the group hides them, and the run then concludes there is no parent and offers to create a
duplicate of one that already exists.

- **One obvious match** → use it, and say which, so a wrong read is visible
- **None** → ask: create one / name an existing one / leave it without one, where `task.hierarchy.parent_required` is `false` / stop. Creating one is its own preview → go
- **Several plausible** → let the user pick. Do not break the tie yourself

**A task with no parent is a real answer where the config allows it.** A one-off fix, a chore, a ticket somebody's merge opened by itself — none of those has a feature to hang under, and inventing a parent for them is what produces the empty umbrella ticket everything unrelated then collects under. Say what it costs at the same time: with `milestone_on: parent` a task with no parent cannot carry a version, so it is invisible to anything reading the milestone. Where the work does belong to a feature, the parent is still the right answer. With `parent_required` `true` the option is not offered — the tracker requires one.

A newly created parent is titled by `task.hierarchy.parent_title`, is built on `task.template.parent` where one is named, and carries whatever `task.mirror_extras` specifies for its type and board placement. Its assignees and every other setting are filled the way a task's are filled — from this project's existing parents first, then by asking — and its title follows the wording those parents already use. **`task.ticket.default_labels` is the task level's and does not follow it up** — a parent carries the mapped project label and the labels the rule document requires of its kind, and nothing else; where there is no rule document the project label is all it carries. The project label is not optional: the adapter finds candidate parents by searching on it, so a parent filed without one is invisible to the next run and gets filed again. A parent filed with a label nobody's rules asked for is worse than one filed bare: the label is what other people's filters and boards are built on. Where the project uses milestones, the milestone is set **on the parent** — see *Milestone* below.

## Labels

**Labels have two sources and the preview names which.** `task.ticket.default_labels` plus the mapped project and priority are the config's. **A label the rule document requires is the other** — a kind of ticket that has to carry one, a level that does. Those are read off the document rather than listed here, because a list here is a copy of a rule that changes at a meeting the config was not in, and a copy that falls behind is invisible: the ticket comes out looking finished and drops out of the filter the rule exists to feed. **A required label the tracker does not have is reported, never created** — a label is somebody's filter and somebody's board column, and creating one from inside a ticket run is how a near-duplicate of an existing label starts collecting tickets.

## Create

**Before anything is created, look for the ticket already there.** List the mirror's newest issues and match the exact title about to be sent — the adapter says how. A match stops the run and offers to link that ticket instead; filing past it is how a run that died after the write, or a second run of the same task, makes a duplicate.

Create it with the assembled title, body, labels and assignee. **Right after the create returns, write the link property into the record** — still inside the same "go", and before the ticket is attached to anything. Attaching is the part that can fail halfway, and a ticket that exists with no link in the record is one the next run cannot match and files again.

## Milestone

**A milestone is not set on the task** where `task.hierarchy.milestone_on` is `parent` — that level owns it.

- **Copy the version back to the record**, where `task.properties.version` is named — the milestone now in effect for this task, which under `milestone_on: parent` is the parent's, or `task.properties.version_unset` where there is none. Where this run set or moved a parent's milestone, every other record whose ticket sits under that parent now shows the old one: they are listed in the preview and move in the same "go". A version left behind on one sibling is the drift `/pm:task sync` would otherwise have to find

## Attach to the board

- Link it under the parent, where the tracker has a parent-child relation
- Add it to the board named in `task.mirror_extras`, capturing the returned item id
- Set the board's custom fields from `task.mirror_extras` — project field, dates
- Dates go **on the task only**. A parent's schedule is managed separately and is never touched here
- **Seat it in the right column.** Where `task.status_map` has an entry for the record's current
  status, set the board's status field to it. Without an entry, leave the board's own default
  alone rather than guessing a column. **A placeholder ticket — one filed before its contract is complete; every ticket `sync` creates is one — overrides this and goes to the
  backlog**, whatever the record's status maps to — the seating is what stops it being picked up

Seating is not ownership. `task.field_owner.status` still says which side wins afterwards — with
it `mirror`, this is the only time this skill touches the status, and every later move belongs to
whoever runs the board. The reason to seat it at all is that a task whose spec is already written
lands in the backlog column otherwise, and the mirror's readers act on that.

Anything under `task.mirror_extras` is read verbatim. This skill does not interpret it, which is what lets a tracker it has never seen still work.

## Write the link back

The link property is written the moment the ticket exists — *Create* above. After that the record takes only:

- **The spec link** (`publish` only) — only where the interview produced a new one
- **The change summary** (`publish` only) — only where the interview produced a new one. Where the record already had it, leave it alone. Append rather than replace, so the history survives: one dated line under what is already there

**The done conditions and the QA checklist are not written back.** They live in the ticket, where they are ticked. Copying them into the record is the second source this design exists to avoid.
