# Marking sections Ready for dev

Used by `/fig:handoff` (Step 6), and only where `handoff.ready_for_dev` is `true`. With it `false` —
the default — nothing here runs, and the status is not offered.

**Why it ships off.** Marking a section notifies whoever follows the file in Dev Mode, and plenty of
teams hand over with the pinned links and the task line alone. Switch it on where the status is part
of how your team hands over; leave it off where it is not, and the handover is complete without it.

## Why it goes through the web app

`use_figma` rejects the status in both directions — `"devStatus" is not a supported API` (checked on
a live file with an Edit seat, 2026-08-31, and again 2026-10-20) — and Figma's REST API reads the
status but has no endpoint that sets it. The web app sets it with one click, so where browser
automation is available the step does not have to be handed to a person, the same way a named
version is saved (`version-pin.md`).

## Steps

The preview and the go are the caller's: handoff's step 4 preview names every section this will
mark, and its go covers the line and the marks together. Nothing is marked before the line has been
written and read back.

1. **Open the section in Dev Mode.** In the web app, signed in on the profile that owns the file,
   open `https://www.figma.com/design/{fileKey}/?node-id={section id, with : replaced by -}&m=dev`.
   It opens in Dev Mode with the section selected.
2. **Mark it.** Find the left panel's button by its label, "Mark as ready for dev", and click it —
   through the page's accessibility tree, not canvas coordinates. One click marks it; no
   confirmation dialog follows (2026-10-20). Where the section already shows the *Ready for dev*
   badge and the button is not there, it is already marked: skip it and say so, rather than clicking
   a status the section already has.
3. **No browser connected, or the account signed in there is the wrong one** — hand it back: name
   the sections and where the button is (Dev Mode, left panel, "Mark as ready for dev"). A section
   this step did not read back is never reported as marked.
4. **Read it back**, section by section. The read needs a personal access token with the
   `file_content:read` scope — a different scope from the version read-back's `file_versions:read`,
   so a token minted for that one needs this scope added. Resolve the variable name through
   `tools.figma_token_env` and check it is non-empty **before** the call, as `version-pin.md` step 4
   does:

   ```bash
   TOKEN_VAR=$(python3 ${CLAUDE_PLUGIN_ROOT}/_common/scripts/lib/resolve-config.py {fileKey} \
     | python3 -c 'import json,sys; print(json.load(sys.stdin)["tools"].get("figma_token_env") or "FIGMA_TOKEN")')
   if [ -z "${!TOKEN_VAR}" ]; then echo "no token in $TOKEN_VAR"; exit 1; fi   # nothing is sent
   curl -s -H "X-Figma-Token: ${!TOKEN_VAR}" \
     "https://api.figma.com/v1/files/{fileKey}/nodes?ids={section id}&depth=1"
   ```

   The section is marked where `nodes["{section id}"].document.devStatus.type` is `READY_FOR_DEV`.
   - **No `devStatus`, or another type** → the click did not land: report that section as not marked
   - **No token** (caught before the call) → report the sections as clicked but not read back, and
     say why
   - **Anything but a 200** — a 401 or 403 (an expired or wrong token, or one without the
     `file_content:read` scope), a 404, a 400 → show the status and Figma's `err` as they came back,
     and report the sections as clicked but not read back

## Never

- Mark before the line is written and read back — or, under handoff's `print`, where nothing is
  written, before the go — marking notifies, and a notice about a handover that has not landed is
  worse than none
- Mark a section the preview did not name, or one lint held back
- Set *Completed*, or change a status a section already has
- Read or set the status with `use_figma`
