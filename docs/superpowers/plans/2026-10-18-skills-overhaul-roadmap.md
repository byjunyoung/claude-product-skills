# Skills overhaul — roadmap

The designs in `docs/design/2026-10-18-*.md` cover several independent changes. They are built as
phases, each its own branch, its own release (version bumps and CHANGELOG in every plugin it
touches) and its own PR. Each phase gets a detailed plan when it starts; only Phase 1's is written
now, because the later phases depend on probe results and on `main` as it will be then.

| Phase | Builds | Design sections | Gate before starting |
|---|---|---|---|
| 0 — Prepare | Probes and a fresh base. No code | — | — |
| 1 — Foundations | The checker's reach, plugin identity in the shared scripts, hook robustness, audit scripts that see nested sections, arrows that keep their style, a picture-render script | review S1; S7 (nested sections, tests); S8 (identity); Bin A 1, 2, 9; audit-flow start edge | none |
| 2 — Local-first defaults | The pm floor, guards, markdown tracker hardening, fig's PRD and tracker reading, generators, setup reordered, the log on by default, prd's addressable output, pm fixes | local-first §1–§5 with corrections; review S2, S10, S12, S13, S16, D5; S7 (`body_offset` floor → null); S8 (pm version check when fig borrows); Bin A 3–7 | Phase 1 merged |
| 3 — Merges and removals | `/pm:task` router, deck merge, diff removal with sync's direct comparison, tokens' audit in lint, lint's section filter and structured output, handoff's gates and Ready for dev, official-skill alignment, `allowed-tools`, qa against the pinned version, the handoff → pm seam, trimmed descriptions (length check WARN → FAIL), the rename sweep | local-first §6–§11; review S3, S4, S5, S6, S7 (section filter, structured output), S9, S14, S15, D1, D3, D4 | Phase 2 merged; probe A for §11 |
| 4 — New capability | prd goals and metrics; `pm:release`; `fig:review` | `2026-10-18-prd-goals-metrics.md`, `-pm-release.md`, `-fig-review.md` | Phase 3 merged; probes B–D |
| 5 — Surfaces | Everything public and the owner's private list, in step with each release | review *Surfaces to update*; README restructure (S11) | lands with each phase's release, not after it |

## Phase 0 — prepare

1. **A fresh base.** Branch each phase from the latest `origin/main`, not from the design branch.
   The design branch is documents only; read its specs by path.
2. **Probes**, on an account with an edit seat on a real Figma file and read access to the team's
   code repositories. Record each result in the design it gates:
   - **A.** Mark a section *Ready for dev* in the web app through the browser, and read the status
     back → local-first §11.
   - **B.** Read a file's comments: an MCP comment reader first, then REST with a token carrying
     `file_comments:read` → fig-review probe 1.
   - **C.** Resolve a comment in the web app and read the state back → fig-review probe 2.
   - **D.** `gh` tag listing and comparing two tags; the share of merged PRs in a recent range that
     link a tracker item; reading open defects by label under a version → pm-release probes.
3. Install the latest released plugins on the machine that runs the probes. The installed copies
   lag the repository.

## Release and surfaces, every phase

Each phase's last task does the same three things:

- **The repository's own documents for what changed:** the README rows, both languages, and any
  `.github` picture that names a changed skill. Re-render pictures with the script Phase 1 adds.
- **The release:** version bumps, CHANGELOG lines, `bash tools/verify-all.sh` passing, and the
  PR opened only after preview → go.
- **From Phase 2 on, the surfaces outside the repository** that the phase made stale: the
  portfolio page, and the owner's private list (team guides, team config, personal skills). Each
  is a preview → go write. A GitHub release is cut when a phase changes user-visible commands
  (Phase 3, Phase 4).
