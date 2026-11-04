# IMPL

## Resume (2026-11-03 ~19:45, site polish, moved to a fresh session mid-review)

Brief: `~/.local/state/fleet-orchestrator/task-site-deslop.src` (Hackathon, then talks, then
fleet-briefing). This branch `polish/site-deslop`, worktree `.claude/worktrees/polish`.
`gh` defaults to upstream AHRTLab: pass `-R ajbarea/Hackathon`. Helper scripts and reports:
`~/.local/state/fleet-orchestrator/site-polish/` (audit.py; the others hard-code the old session's
scratch path in `S=`, so edit that line before reuse).

### Hackathon: issue #16, PR #17 (assigned ajbarea, CI build green)
- ✅ 015c05c copy + a11y: award "AWARE-AI Fall 2026 Hackathon" (certificate), team credit (AJ led
  development and data collection with Claude Code; Jose, Kiran, Xinyi recorded the four-driver
  calibrations), deck slide numbers underlined, code-block line anchors off, sim labels,
  aria-pressed, #304ffe, RTLX dialog.
- ✅ c403b52 sim panels are named regions (`panel(pos, id, label)`); tsc clean, CI green.
- ✅ Verified: sim `npm test` 65 passed; docs differential (defaults copy byte-identical, anchors
  off changes only 5 pages); axe before/after: deck 17→0, code links 39→0, sim 5→0
  (hackathon-before/after-11-03.json). Not yet re-audited: the sim's `region` count after c403b52
  (`sim-recheck.sh`).
- ✅ Shots: fleet-briefing/shots/2026-11-03/Hackathon-16-*, line in shots/README.md.
- ✅ Round 1 (Opus, report:
  `/tmp/claude-1001/-home-ajbar-ajsoftworks/6cc660d4-db59-48b9-82a6-172475e68e09/scratchpad/review-hackathon17.md`): 0 Blocking, 4 Should-fix,
  6 Nits. Fixed: RTLX form is a native `<dialog>` (showModal, Escape = Skip, focus in and back); repo
  description award name; team credit (AJ published both releases; the 10-23 release holds the other
  drivers' recordings, docs/data.md said otherwise); finish result in a `role=status` region; active
  camera button underline; slider `aria-valuetext`; zensical defaults upgrade note; e2e asserts for each.
- 📋 Unit + e2e (m2, m4 on chrome) under the heavy lock; re-audit sim at HEAD (region count for the PR
  table); round 2 fresh reviewer; merge; check the Pages deploy.

### fleet-briefing: ✅ PR #6 merged 11-03 (round 1 + verify clean); klepsydra#306 filed (sync skips done/).
📋 Confirm the C: checkout picks up the merged README (log line "briefing synced after a rebase").

### talks: worktree ~/ajsoftworks/talks/.claude/worktrees/polish, branch polish/site-deslop
- ✅ 109 links and assets on the site return 200. Glossary grep: one fix (FA deck "neither ...
  nor" recast). Kourai deck claims match kourai main (10 agents, MAX_ITERATIONS 5).
- ✅ Deslop: no slop beyond the neither/nor fix. Alt text, svg labels, link rel clean in all decks.
- ✅ Live audit (1920, phone, dark): 0 console errors, 0 failed requests, no x-overflow; one axe
  hit per deck, `landmark-complementary-is-top-level` on reveal's `<aside class="controls">` -> fixed
  in shared/deck.js (role=group, "Slide controls"), uncommitted. Same aside in techne's web starter.
- 📋 slides-check vs techne main (pass SLIDES= and SPHRAGIS= to exported copies; needs Playwright
  1.63.0 Chromium, now installed); commit, issue, PR, shots, review, merge; techne issue for starter.
  Duet deck is presented Fri 11-06: fix only gate failures and clear bugs there.

Left as is (theme or organizers' pages): axe `region` on Material's progress bar, `landmark-unique`
on BRIEF's code nav, slide 1 image text (the deck as presented).
