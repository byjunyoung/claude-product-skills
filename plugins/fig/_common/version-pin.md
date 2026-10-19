# Pinning a named version

Used by `/fig:handoff` (Step 3) and `/fig:sync` (Step 6). Read it when `handoff.version.enabled`
is set, or when `sync.named_version` is not `null`. With either off, no version is saved and
nothing here runs.

**A named version is a moment in the file.** Without one, every later edit silently moves what
"matches the design" means. Figma's named versions are a snapshot of the whole file, so every
section handed over in one run shares the label and differs only in the node. Nothing is copied,
and no frozen duplicate of the file exists to fall out of date.

## Why it goes through the web app

`use_figma` cannot save a version: its allowlist rejects the version API
(`"saveVersionHistoryAsync" is not a supported API`, checked on a live file with an Edit seat,
2026-08-31). The web app can, so where browser automation is available the step does not have to
be handed to a person.

## Steps

Each caller supplies two things: the **name** to save, and **how its entry is recognised** when
read back. The two callers today: handoff names it with `handoff.version.name` and recognises it
by `handoff.version.match`; sync saves `sync.named_version` (`{date}` and `{n}` filled in) and
recognises the entry by that exact title.

1. **Settle the name.** For handoff, ask which release the handover belongs to — a value the
   person has, never one inferred from the file.
2. **Preview, then go.** Show the name and say it is one entry added to the file's version history;
   the file's contents are untouched, and removing the entry's name undoes it. Nothing is saved
   before the go. **One gate:** a caller that has already shown this preview and got the go
   continues from step 3.
3. **Save it.** In the web app, signed in on the profile that owns the file: main menu →
   *File → Save to version history*, fill the name and description, save. Type the name through
   the clipboard rather than keystrokes where the label is not plain ASCII — synthesized typing
   mangles multi-byte text, and a mangled label is a pin nobody can match later. Where no browser
   is connected, or the account signed in there is the wrong one, hand it back: show the name and
   ask for it to be saved under exactly that name.
4. **Read it back**, newest first, and take the first entry the caller recognises (handoff:
   matching `handoff.version.match`; sync: the exact title it saved):

   ```bash
   curl -s -H "X-Figma-Token: $FIGMA_TOKEN" \
     "https://api.figma.com/v1/files/{fileKey}/versions?page_size=10"
   ```

   - **No token, or an expired one** (`{"status": 401, "err": "Token has expired"}`) → say so, and
     ask for the version's link to be pasted instead; `version-id` is in its query string. Never
     carry on unpinned where the caller pins
   - **Nothing matches** → it was not saved, or was saved under another name. Show what the newest
     few are actually called and stop, rather than taking the wrong entry

   **Handoff only:** the entry carries the label, its `created_at` — the date in
   `handoff.version.ref` is the version's, not today's, never a substituted one — and its `id`,
   which is what a link pins with.

   **Sync only:** it hands over no link, so it only confirms the entry exists and reports its title.

## The pinned link (handoff)

Every section link handoff hands over carries the pin: `…/?node-id={id}&version-id={version id}`.

## Never

- Save a version without the go, rename one, or write a date that is not the version's own
- Carry on unpinned where handoff's pin is switched on — an unpinned handover reads as pinned to whoever
  gets it
