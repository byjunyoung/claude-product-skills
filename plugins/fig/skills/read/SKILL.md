---
name: read
description: Lists every page of a Figma file and every top-level frame on the page you pick as a markdown tree built from the URL alone, when you need a file's structure before working in it. Triggers - "/fig:read", "read this Figma file", "list every frame", "피그마 파일 읽어줘", "프레임 전부 뽑아줘", "전체 구조 보여줘".
allowed-tools: AskUserQuestion, Skill, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_screenshot, mcp__plugin_figma_figma__use_figma
---

# fig:read — collecting every frame in a Figma file

Takes a single Figma file URL, walks the page → frame structure automatically, and collects every top-level frame on the pages you pick as metadata plus screenshots. It works without selecting anything in the desktop app.

## When to invoke

- The user hands over a Figma **file** URL (no node specified) and says "read all of it", "show me the structure", "pull every frame"
- Taking a screen inventory before spec or canonical-page work
- An explicit "/fig:read"

## When NOT to invoke

- Frame naming and section tidying → `/fig:prep`
- Auditing rule violations → `/fig:lint`
- Auditing whether working changes landed in the canonical page → `/fig:sync`
- Design context for a code implementation → the `figma:figma-design-to-code` skill · carrying it into the front-end repo → `/fig:code`

## Inputs

- `figma_url` (required): a URL of the form figma.com/design/:fileKey/...
  - A node-id parameter is ignored and the whole file is used (the user picks the page)

## Procedure

### 1. Parse the URL

Extract the fileKey from the Figma URL:
- Pattern: `figma.com/design/([A-Za-z0-9]+)/...`
- If no fileKey comes out, ask the user for the exact URL again

### 2. List the pages

Read page names and **order** with one read-only `use_figma` call (`fileKey` from step 1). Load `figma:figma-use` before it, as every `use_figma` call requires, and pass `figma-use` in `skillNames` on the call (`figma-use` SKILL.md:11), read-only or not.

```js
return figma.root.children.map((p, i) => `${i}\t${p.id}\t${p.name}`).join("\n");
```

- Each line is `index<TAB>id<TAB>name` — the page's node id is what step 3-2 passes to `get_metadata`
- `get_metadata` with a fileKey alone returns an incomplete page list, so it is not used to list pages
- If the node-id in the user's URL is a page (canvas type), include that page as a direct entry candidate too
- Zero pages back, or the call fails: say so and stop — do not guess page names

With only one page, skip the selection step and go straight to 3-2.

### 3. Pick the pages (when there are ≥ 2)

Present the page list through `AskUserQuestion`:
- `multiSelect: true`
- One page name per option label (at most 4 can be shown — with 5 or more pages, offer the first 3 plus "all" plus "pick manually")
- With far too many (over 8), print a numbered markdown list and have the user type the numbers

### 3-2. Read the frame tree

Call `get_metadata` for each selected page:
- `fileKey` + the page `nodeId`
- depth 2 is enough (the page's direct children are the top-level frames)

Collect the top-level frame ids for each page.

### 4. Frame-count guard

If the total frame count exceeds `tools.frame_count_guard`, warn before proceeding:
- Print, as markdown, "{N} frames found. Pulling screenshots too will cost significant time and context. Continue?"
- Branch through `AskUserQuestion`: "all of it / metadata only (skip screenshots) / pick pages again"

### 5. Collect per frame (in parallel)

For each frame, both calls go out in parallel inside one message:
- `mcp__plugin_figma_figma__get_metadata` (fileKey + nodeId)
- `mcp__plugin_figma_figma__get_screenshot` (fileKey + nodeId)

Too many at once is heavy, so send them **in batches of 5**.

If a screenshot call fails, keep the metadata and state the failure in the output (`screenshot: failed`).

### 6. Emit the markdown tree

Print to the conversation in this form:

```
# {file name}

## {page name 1}

### {frame name} (`{nodeId}`)
- Link: https://figma.com/design/{fileKey}/?node-id={nodeId with : → -}
- Size: {width}×{height}
- Children: {childCount}
- Screenshot: {path, or "failed"}

### {frame name 2} ...

## {page name 2} ...
```

Show the image `get_screenshot` returned as it is (inline in the assistant's response).

### 7. Point at what comes next

One line at the end of the output:
> Candidates for the next step: `/fig:prep` (tidy the structure) · `/fig:lint` (audit) · `/fig:sync` (audit against the canonical page)

## Output contract

- Everything is markdown, in the conversation only (no files, no external pages created)
- Node links are clickable figma.com URLs — the nodeId's `:` becomes `-`
- Failures are marked "failed" explicitly, never silently dropped

## Constraints

- No external writes of any kind — this is a pure read skill
- Beyond page selection, keep the interviewing minimal (as little burden on the user as possible)
- What is collected stays in context, so structure it for the next skill to pick up

## Notes

- The plugin:figma MCP's `get_metadata` and `get_screenshot` need only fileKey + nodeId — the desktop app's selection state is irrelevant
- But plugin MCP `get_metadata(fileKey only)` is bound to the desktop app's context and exposes only some pages → every page is enumerated through `figma.root.children` in `use_figma`
- Expanding down into components, instances, and vectors is deliberately not done. It stops at top-level frames
- When a design changes often there is no point caching the result — call again each time
