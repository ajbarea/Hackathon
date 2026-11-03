# IMPL

## Resume (2026-11-03, site polish slice 1 of 3: Hackathon)

Brief: `~/.local/state/fleet-orchestrator/task-site-deslop.src` (Hackathon, then talks, then
fleet-briefing). Branch `polish/site-deslop`, worktree `.claude/worktrees/polish`.
`gh` defaults to upstream AHRTLab: pass `-R ajbarea/Hackathon`. Issues were off on the fork; turned
on 11-03 for issue #16 (labels only: issue types exist only on org repos).

Done:
- ✅ Issue #16 filed and assigned. Commit 015c05c: award name from the certificate ("AWARE-AI Fall
  2026 Hackathon", Oct 23 2026), team credit (AJ led development and data collection with Claude
  Code; Jose, Kiran, Xinyi recorded the four-driver calibrations), deck slide-number links
  underlined, code-block line anchors off, sim labels / aria-pressed / #304ffe.
- ✅ Sim: `npm test` 65 passed, `tsc` + build clean.
- ✅ Docs differential: Zensical defaults copied into zensical.toml build byte-identical to no
  table (0 files differ); anchors off changes only the 5 pages with code blocks, anchors only.
- ✅ Links: 28 live links 200.

Next:
- 📋 Before/after shots from the audit (`audit.py`, scratch `shots/`) to
  fleet-briefing/shots/2026-11-03/Hackathon-16-*, one line in shots/README.md.
- 📋 PR (assignee ajbarea, closes #16), independent opus review, merge, check the Pages deploy.

Left as is (theme or organizers' pages): axe `region` on Material's progress bar, `landmark-unique`
on BRIEF's code nav.

Re-run the audit: `flock -o /tmp/fleet-heavy.lock uv run --with playwright python -I audit.py OUT
TAG URL...` from `~/.local/state/fleet-orchestrator/site-polish/`.
