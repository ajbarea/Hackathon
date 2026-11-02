# IMPL

## Resume (2026-11-02 18:15, site polish slice 1 of 3, PAUSED by Heph)

Brief: `~/.local/state/fleet-orchestrator/task-site-deslop.src` (Hackathon, then talks, then
fleet-briefing). This branch is `polish/site-deslop`, worktree `.claude/worktrees/polish`.
`gh` defaults to upstream AHRTLab: pass `-R ajbarea/Hackathon` (issues are on there).

Done (audit only, no site edits yet):
- prose_check on docs/*.md and README: clean apart from 4 long sentences; 0 em-dashes in docs,
  deck, overrides, web/index.html.
- 28 non-anchor links on the live site: all 200.
- Live audit (axe + console + images) at 1920 light/dark and 390 phone: report and the script in
  `~/.local/state/fleet-orchestrator/site-polish/` (audit.py, before-report.json). Re-run:
  `flock -o /tmp/fleet-heavy.lock uv run --with playwright python -I audit.py OUT before URL...`
  (it scrolls each page first so the shared reveal.js sections show in full-page shots).

Findings to fix (next):
1. Award name: the certificate reads "AWARE-AI Fall 2026 Hackathon" (Oct 23, 2026); the site says
   "AWARE-AI Fall Hackathon 2026" (index.md hero + description, zensical.toml site_description).
2. Deck TOC links (`a[href$="#s1"]`...): link-in-text-block contrast 2.16:1 light, 1.78:1 dark;
   underline or recolour them (docs/deck/index.html).
3. Sim (web/): chase camera button 4.25:1 (#e8eaed on #3d5afe, needs 4.5); #bridge-url, latency and
   drop sliders, course select have no labels. web/ came from the organizers; keep edits to
   aria-labels and one colour.
4. Code blocks: Material line-number anchors have no accessible name (axe link-name); check the
   highlight config in zensical.toml (anchor_linenums).
5. Not a bug: reveal.js hides below-fold sections until scrolled (canonical copy lives in techne).
6. Check deck slide images 07-17 load (axe saw them unloaded; likely loading=lazy).

Next after fixes: before/after shots to fleet-briefing/shots/2026-11-02/hackathon-<issue>-*,
issue then PR (assigned ajbarea), independent opus review, merge; then talks, then fleet-briefing.
Verify: re-run audit.py on the PR's Pages build or a local `zensical serve`.
