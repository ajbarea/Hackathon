# IMPL

## Resume (2026-11-04 00:40, replacement session on Personal; both PRs measured, final verify passes running)

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
- ✅ Round 1 fixes measured: unit 65, chrome e2e m2+m4 8/8 (bridge venv: `uv venv` + `uv pip install -e
  'bridge[lsl]' pygame numpy`, pass `PYTHON=`), axe 0 with the form closed and open (probe2.py).
- ✅ Round 2 (`review-hackathon17-r2.md`, same scratch folder): A finish status hidden under the modal, B vacuous
  pause test, nits -> fixed in the latest commit; mutant without the C guard killed by the rtlx e2e.
- ✅ Round 3 CLEAN (0 Blocking, 0 Should-fix, 3 Nits; report `/home/ajbar/.local/state/fleet-orchestrator/site-polish/review-hackathon17-r3.md`). The earlier m2/m4 failures are
  bundled-Chromium only, on main too; Google Chrome (the repo's engine) passes 8/8 at HEAD. Possible follow-up issue: sliders test
  fails 5/5 on bundled Chromium (W hold after canvas click never starts the run), main and HEAD alike.
- ✅ 1bde1eb nit fixes: N12 DNF line "x of n gates" (main.ts), N13 Space presses buttons inside a dialog (dom.ts) and keys.ts
  ignores keydown inside an open dialog but always clears held keys on keyup (also fixes a key stuck when released in a slider);
  m4 rtlx e2e now presses Space on Skip.
- ✅ 1bde1eb measured 11-04: unit 65; rtlx e2e baseline passes, mutant (dom.ts closest check removed) fails; Google Chrome e2e
  m2+m4 8/8; sim axe 0 form closed and open; after a real finish axe 0 form open and after close (reviewer r3 spec rerun).
  PR body N14 fixed (after = 1bde1eb).
- 📋 Verify pass (fresh Opus) running; report appends to
  /tmp/claude-1001/-home-ajbar-ajsoftworks/8def2bee-9566-4892-8eb5-2390b263b589/scratchpad/verify-h17.md. If clean: merge, check Pages.

### fleet-briefing: ✅ PR #6 merged 11-03 (round 1 + verify clean); klepsydra#306 filed (sync skips done/).
✅ C: checkout carries the PR #6 merge (checked 11-03 late).

### talks: worktree ~/ajsoftworks/talks/.claude/worktrees/polish, branch polish/site-deslop
- ✅ 109 links and assets on the site return 200. Glossary grep: one fix (FA deck "neither ...
  nor" recast). Kourai deck claims match kourai main (10 agents, MAX_ITERATIONS 5).
- ✅ Deslop: no slop beyond the neither/nor fix. Alt text, svg labels, link rel clean in all decks.
- ✅ Live audit (1920, phone, dark): 0 console errors, 0 failed requests, no x-overflow; one axe
  hit per deck, `landmark-complementary-is-top-level` on reveal's `<aside class="controls">` -> fixed
  in shared/deck.js (role=group, "Slide controls"), uncommitted. Same aside in techne's web starter.
- ✅ Issue #74, PR #77 (main merged in). Every slide at 1920 light/dark + phone view: axe 0 on all decks
  (deck-axe.py in the scratch folder); slides-check 0 blockers; techne#276 filed (starter aside, FAQ backup).
- ✅ Round 2 (report `/home/ajbar/.local/state/fleet-orchestrator/site-polish/review-talks77-r2.md`): 0 Blocking, 1 Should-fix, 3 Nits; Duet-safe. Pushed 569a2b9: phone tabindex only when
  nothing in .reveal .slides is focusable; two-tone focus frame (.reveal-viewport:focus-visible::after, deck.css end); `?receiver`
  (speaker-view previews) is never phone; N3 comment.
- ✅ 569a2b9 measured 11-04: probe as expected (Duet/FA Tab on a figure item, Kourai on the viewport with the frame, tap no
  frame, receiver not phone, desktop unchanged); every-slide axe 0 on all decks, light/dark/phone; landing 0 once animations
  settle (site-polish/audit.py reads it mid-fade; friction.md). CI check green. PR body rewritten (frame, speaker view, 3-rule
  befores, Chrome + WebKit sources).
- 📋 Verify pass (fresh Opus) running; report appends to the same scratch folder, verify-t77.md. If clean: merge, check deploy.

Left as is (theme or organizers' pages): axe `region` on Material's progress bar, `landmark-unique`
on BRIEF's code nav, slide 1 image text (the deck as presented).
