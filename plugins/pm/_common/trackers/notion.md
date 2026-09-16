# Notion as the record side

connector: Notion
roles: record

For a `task.record.type` of `notion`. `{db}` is `task.record.ref` — a `collection://` url.

## Reading the list

**A date property cannot be queried under its own name.** SQL splits it into three columns —
`date:{name}:start`, `date:{name}:end`, `date:{name}:is_datetime` — and a query naming the
property itself fails with *no such column*, which reads like a wrong property name rather
than a shape. The same spelling is what a write uses. So fetch the data source before the
first query and read its table definition: it also names the properties that cannot be
queried in SQL at all.

Try the exhaustive query first:

```
notion-query-data-sources  data_source_url={db}
```

**It is gated behind a plan tier, and a workspace that lacks it returns an error rather than a
partial result.** Do not retry it a second way. Fall back, and say in the report that you did.

### The fallback: search, fetch, filter

```
1  notion-search  data_source_url={db}  page_size=25  max_highlight_length=0
   Run it several times with differently worded queries — per project, per status, per
   assignee. One query is one relevance ranking, not a listing.

2  Dedupe the page ids.

3  notion-fetch each candidate. Keep only rows whose ancestor path contains
   parent-data-source url="{db}".  A search will happily return a sub-page of a task,
   or a row from an entirely different database, and both look like tasks until you check.

4  For a long list, fan the fetches out to sub-agents that each return compact JSON.
```

**What this costs you.** A relevance ranking has no "that was all" signal. Rows matching none of
your queries are absent, with nothing marking their absence. Misses are structural here.

Wrongly *creating* or *closing* something is not, because duplicate detection reads the mirror
exhaustively and every write waits for approval. So the failure mode is silent under-coverage,
which is why the coverage line in `/pm:task-sync`'s result is mandatory rather than decorative.

Where full reconciliation actually matters, ask for a CSV export of the list and run against
the file.

## Writing back

```
# the link property, after a ticket is filed
notion-update-page  page_id={id}  command=update_properties
                    properties={"{task.link_property}": "{ticket url}"}

# the version, copied from the milestone the ticket sits under
notion-update-page  page_id={id}  command=update_properties
                    properties={"{task.properties.version}": "{milestone, or version_unset}"}

# a change summary, appended under what is already there
notion-update-page  page_id={id}  command=update_content
                    content_updates=[{old_str: "...", new_str: "..."}]
```

**Append, never replace.** Catch the end of the existing text as `old_str` and put the new dated
line after it. Replacing the section throws away the history the section exists to keep.

## Things that bite

- **A database template is not applied when a row is created through the API.** Write the body
  skeleton explicitly — that is what `task.notion.body_template` is for.
- **`update_content` reports success when `old_str` matched nothing.** Read back and check the
  content, not the return value.
- **A read straight after a write can return the pre-write snapshot.** Verify by content.
- **Relation properties replace wholesale.** There is no adding one member.
- **A select value with no option yet (unverified).** Writing a milestone the property has no option for may create the option or be refused. Where refused, add it by rewriting the property's option list with every existing name kept — a list that leaves one out deletes that option, and every row holding it goes blank without an error. **So check the option list before the write goes in a proposal** — the schema from the fetch above carries every option, and a value the other side shows that this property has no option for is a finding to report rather than a write to attempt. Whoever adds it should be looking at what else is on that list.
- **A property write can fire the database's own automations.** A database may move a status or stamp a date when a row changes. After the first write of a batch, read that row back and compare the fields you did not send before writing the rest.
- **Text typed by hand corrupts.** Copy the existing string and substitute into it.
- **A table cell edit can push a line break into the cell behind it.** Keep the line count and
  edit row by row.
