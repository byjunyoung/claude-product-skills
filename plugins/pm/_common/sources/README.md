# Source adapters — chat and calendar

Two skills read a chat tool, one reads a calendar, and none of them knows which. The calls
live in `sources/<type>.md`, where `<type>` is `sources.chat_type` or
`sources.calendar_type` in the config. Slack and Google Calendar ship. Anything else —
Teams, Discord, Mattermost, Outlook — is a file somebody writes, and `/pm:setup` drafts it
from the tools connected on the machine, the same way it drafts a tracker adapter.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/adapter.py --name pm-conventions.yaml --kind sources --type teams
```

Bundled files sit here; yours live in `adapters.dirs` under `sources/`. Exit 3 means there is
no adapter for that tool, and the skill stops on it.

## What a chat adapter has to answer

| Question | Who asks | What the answer carries |
|---|---|---|
| **A thread from a link** — the root and every reply, in order | `/pm:task draft`, `/fig:qa` | How the link resolves to the thread root. What attachments come back as |
| **A channel on a day** — every message, in local time | `/pm:log` | The call, and how the day is bounded |
| **Messages about me on a day** — sent by me, or mentioning me, across channels | `/pm:log` | The search call, and its response cap. Page rather than widen |
| **My notes channel** — a place only I write in | `/pm:log` | The same channel read, plus how to tell a message an app posted on my behalf from one I typed |
| **A permalink** for any message, and **a sender's display name** | `/pm:log` | The calls. A quote is recorded with both |

## What a calendar adapter has to answer

| Question | Who asks | What the answer carries |
|---|---|---|
| **A day's events** in local time, ordered by start, with attendees | `/pm:log` | The call. Which entries are noise — working location, birthdays, out of office |

## Always

**Things that bite** — each because it happened. A search that fails outright above a size
and returns nothing, which reads as a quiet day. Retention that expires, which is why text is
carried across rather than linked.
