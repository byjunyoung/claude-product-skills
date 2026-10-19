---
name: task
description: Works on task records in three modes. draft turns a request source (a chat thread, a page, a spoken agreement) into a task record's context table, with fact, inference and undecided labelled apart. publish files one task record as a ticket in the engineering tracker, or updates the one already there, with done conditions and a QA checklist. sync reconciles the planning-side task list against that tracker and proposes fixes before writing. Triggers - "/pm:task", "/pm:task draft", "/pm:task publish", "/pm:task sync", "draft a task from this thread", "file this task as a ticket", "reconcile the tasks", "일감 초안 잡아줘", "깃헙에 일감 등록해줘", "일감 동기화해줘".
allowed-tools: AskUserQuestion, Read, Write, Bash, Agent, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-create-pages, mcp__claude_ai_Notion__notion-update-page, mcp__claude_ai_Notion__notion-query-data-sources, mcp__claude_ai_Notion__notion-get-users, mcp__claude_ai_Slack__slack_read_thread, mcp__claude_ai_Slack__slack_read_channel, mcp__plugin_figma_figma__get_metadata, mcp__plugin_figma_figma__get_design_context, mcp__plugin_github_github__issue_read, mcp__plugin_github_github__issue_write, mcp__plugin_github_github__add_issue_comment, mcp__plugin_github_github__sub_issue_write, mcp__plugin_github_github__list_issues, mcp__plugin_github_github__search_issues
---

# task — one task record, three ways to work on it

**Part of a plugin.** The scripts this skill runs ship beside it under `${CLAUDE_PLUGIN_ROOT}`. If that path does not resolve, this file was installed on its own — stop and say the plugin itself is needed (`claude plugin install pm@byjunyoung`), rather than improvising what the scripts do.

Pick the mode from what the person asked for, then read that mode's file and follow it.

| Mode | File | Job |
|---|---|---|
| `draft` | `draft.md` | Turn a request source into a task record's context table |
| `publish` | `publish.md` | File one task record as a ticket in the engineering tracker, or update the one already there |
| `sync` | `sync.md` | Reconcile the planning-side task list against the tracker it mirrors |
