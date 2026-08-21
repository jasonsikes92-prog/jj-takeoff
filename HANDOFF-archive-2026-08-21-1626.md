# J&J Takeoff — Engineering Handoff (Overnight self-calibration relay)

**Written:** 2026-08-18 23:40 EDT · **Repo:** `C:\Users\jason\JJ-Takeoff` · **Branch:** `virtual-takeoff` @ `9ddbb19`
**Prior handoff:** `HANDOFF-archive-2026-08-18-2340.md` (best source for the viewer/teach-loop era: Phase 0/A/B/D architecture, teach-mode mechanics, cal #66/#67 context, repo layout)

---

## 1. Mission

Jason's goal, stated 8/18: **teach the system to draw its own lines and take its own
measurements** — his markup is training signal, not the operating mode. Tonight's
mandate: overnight self-calibration against ALL his real jobs — pull every Buildern
takeoff/estimate/PO, cross-reference my measurements vs his hand-done ones (his are
ground truth), cross-reference pricing vs POs/bids/QBO actuals/sub invoices, fix what's
wrong, keep going until each thing works. This is a RELAY session: at ~60% context,
update this handoff and continue in a fresh session (his explicit rule).

## 2. Current State

**Verified tonight:**
- **Autonomy lane v0 works** (`jobs/roberts_levelground/auto_declare.py`, commit
  `a7f501b`): engine-drawn garage walk with zero human ink = 702.4 SF, closure 0.00,
  6/6 legs match Jason's certified walk (0.22%). Scoreboard 2/5 auto-declared, 1/5 in
  gate, 0 wrong numbers. Full gap list in `docs/ROADMAP.md` "THE GOAL" section.
- **cal #71 APPROVED + recorded** (`reference/calibration.md`, commit `9ddbb19`):
  printed AREAS schedule may SELECT the dimensioned face among closure-valid
  all-printed-legs readings; never feeds a quantity.
- **All four data sources verified reachable** — see `docs/training/RUN_STATE.md`
  "Access" section (Buildern via Jason's Chrome; QBO MCP; Jason Gmail MCP; Keli's
  mailbox via JARVIS `agent/email-tool.js` + `KELI_IMAP_USER/PASSWORD` in JARVIS/.env).
- **Buildern acquisition pattern PROVEN on Roberts** and documented step-by-step in
  RUN_STATE (project list export ✓, 167 POs ✓, Roberts measurements 566 rows ✓ +
  estimate 602 rows ✓ staged under `training/`).

**Uncommitted:** `.gitignore` (root-anchored `/training/` — the unanchored pattern was
silently ignoring `docs/training/` too), `docs/training/RUN_STATE.md`. Commit these
first.

**Not run tonight:** full gate suite (no engine files touched — auto_declare.py is an
additive job-local tool). Any session that touches `tools/jnj_takeoff.py` must run
`python jj.py verify` + fixture cert refresh per convention.

**Exact next action:** execute Phase A of RUN_STATE — loop the ~26 priority jobs
through the proven Buildern export pattern (collect each project's internal id from
the projects list row link; Roberts = 29093), staging into `training/<job>/`. Then
A2 (QBO per-job actuals), A3 (email sweeps), then Phase B measurement calibration.

## 3. Decisions Made (and Why)

| Decision | Alternatives | Reason | Reversibility |
|---|---|---|---|
| Autonomy is the goal; supervised loop = training rig (Jason 8/18) | keep "autonomous defunded" doctrine | his explicit ruling; gates make autonomy safe | settled — his words in memory + ROADMAP |
| cal #71 schedule-as-face-selector | refuse all face-ambiguous readings | inside-face vs outside-face families both close; the sheet's own figure picks the family; Jason ran the same check by hand | his ruling — settled |
| Cross-page chain pooling (p3+p4) in the solver | single-page pools | his own garage cert needed p4 dims to settle a p3 ambiguity | measured: true reading only reachable pooled |
| Ambiguity judged by AREA spread, not value-tie | refuse on any tie | 12.54-vs-12.52 is one measurement, not two readings | in auto_declare.py, tunable consts |
| Overnight engine fixes allowed, gates green, morning ratify | diagnose-only | Jason: "figure out how to fix it… you have full access"; rate-book VALUES stay proposals | his mandate, this run only |
| Buildern browser crawling authorized (supersedes ask-for-export) | JARVIS BUILDERN_* headless | his explicit instruction; Chrome verified logged in; JARVIS creds = fallback | mandate for this run |
| QBO MCP replaces Buildern Bills/Invoices UI (no export button there) | scrape the grids | bills are QB-synced anyway; MCP is cheaper and structured | trivial |

## 4. Architecture & Key Files

**Created tonight:**
- `jobs/roberts_levelground/auto_declare.py` — the autonomy lane: engine loop shape →
  cross-page printed-chain pools → per-axis closure solver (cal #68: ≤1 derived/axis,
  ±0.05) → walk-level candidate evaluation (area-equivalence 1.0%, decisive margin
  0.5 ft, cal #71 schedule window ±2%) → scoreboard vs `declared_walks.json` +
  certified areas → `auto_walks.json`. Report-only; never writes declared/evidence.
- `docs/training/RUN_STATE.md` — **the run's persistent brain.** Access paths, rules,
  phase checklist, proven Buildern export pattern, staged inventory, priority-job
  list, log. Update it after every milestone; it's what survives relays.
- `docs/HANDOFF_AI_INTEL.md` — Handoff.ai/H1 competitor recon (their 3-artifact
  deliverable contract, TakeoffBench-V1, what we cloned).
- `training/` (gitignored) — raw corpus: `buildern_projects.xlsx` (69 jobs),
  `buildern_purchase_orders.xlsx` (167 POs), `roberts/measurements.xlsx` +
  `estimate_items.xlsx`.

**Modified:** `docs/ROADMAP.md` (goal restated + autonomy-lane results + gap list),
`reference/calibration.md` (#71), `.gitignore` (`/training/`).

**Don't touch unless the task demands:** `tools/jnj_takeoff.py` (engine — gates +
ratify discipline applies), golden `expected.yaml` values, `declared_walks.json`
(Jason's certified answers — grading truth, never inputs to autonomy).

## 5. Gotchas & Hard-Won Knowledge

- **Unanchored `.gitignore` dir patterns match at any depth** — `training/` swallowed
  `docs/training/` and the run state was invisible to git. Root-anchor: `/training/`.
- **Buildern SPA screenshots time out while it renders** — wait 4-6s and retry the
  screenshot; do NOT re-click (a double-click on Download Excel produced duplicate
  exports).
- **Buildern search box persists filters across sessions** — the projects list opened
  pre-filtered to "rober" and looked like a 2-project account. Clear it first.
- **Buildern update modal** blocks the dashboard on fresh loads; Escape does nothing —
  click "Try it out now" to dismiss.
- **Buildern Bills/Client-Invoices grids have no export UI** (POs and Projects do).
- **The autonomy seed is the INSIDE wall face** (engine loops). All 5,000 crawlspace
  closing readings cluster ~1965 SF vs certified 2106 — no snapping fixes a
  wrong-face seed; outer-face loop emission is the #1 engine lever (needs ratify).
- **His measurements can differ by CONVENTION, not error** — cal #70: his Buildern
  shingle lines are FLAT plan traces (+15% waste); ours is pitch-corrected surface;
  ratio 1.404 = blended pitch factor. Phase B must classify DEFECT vs CONVENTION vs
  MY-ERROR before "fixing" anything.
- **QBO duplicate projects silently zero reports** (standing memory) — reconcile job
  names before trusting per-job actuals.
- `polygon_outline` + solver consts live at the top of auto_declare.py — CAND_TOL_FT
  1.6 exists because inside-face legs sit up to 2 wall-thicknesses from printed values.

## 6. Conventions In Play

Per `~\.claude\CLAUDE.md`, `Desktop\Claude\CLAUDE.md`, and this repo's standards:
gates after any engine change (`python jj.py verify` + cert refresh); additive keys
only; fail-closed refusals everywhere; calibration entries append-only, numbered,
Jason's rulings only; commits descriptive with `Co-Authored-By: Claude Fable 5
<noreply@anthropic.com>`; job PDFs/exports out of git (`/training/` ignored on
purpose); **Jason's output preference: BRIEF — status lines, detail in files**;
Jason-only steps go to JARVIS "Waiting on You" via `agent/jason-todos.js addTodo`;
read-only in Buildern/QBO/email — no sends, no approvals, no state changes there.

## 7. Open Questions

1. **Outer-face loop emission** — `foundation_wall_loops` knows both lines of each
   wall pair; emitting the outer loop is an engine edit. Next session: prototype it
   behind the gates, present for ratify. (Next-session question, not Jason's.)
2. **Floor-plan envelope detection** — heated/deck have no autonomous shape source;
   loop decomposition resolves closet-scale rooms only. Approach TBD.
3. **Independent second side for blind autonomous runs** — what verifies an auto walk
   on a job with no Jason stroke? (Candidate: outer-face pixel area once #1 lands.)
4. **Jason (morning):** review the overnight report; ratify any engine commits made
   during the run; the 8/14 ratify backlog (`todo_takeoff_engine_ratify_0814`) is
   still open too.
5. **Jason (whenever):** send Handoff the TakeoffBench-V1 research request (15
   external graded blueprint sets) — see `docs/HANDOFF_AI_INTEL.md` §4.

## 8. Do Not Touch

- `declared_walks.json` and golden `expected.yaml` values — grading truth.
- Rate-book VALUES in `reference/` — proposals only, even under "full access".
- The certified Roberts component names/scopes (cal #67 wrong-scope discipline).
- Buildern/QBO/email write paths — this run is read-only in external systems.
- `estimator_accuracy/` (Desktop\Claude) — harvest-only, stopped track.

## 9. Resume Command

> Read `HANDOFF.md`, then `docs/training/RUN_STATE.md`, then follow its NEXT line:
> commit the two uncommitted files, then run the Buildern acquisition loop across the
> priority jobs (pattern proven on Roberts — internal ids from the projects list),
> staging to `training/<job>/` and updating RUN_STATE after each. Then QBO per-job
> actuals, then email sweeps, then Phase B measurement calibration (classify
> DEFECT/CONVENTION/MY-ERROR; engine fixes need gates green + commit-with-evidence).
> Keep chat output brief. Do not touch declared_walks.json, golden values, or
> rate-book values. At ~60% context, update RUN_STATE + this handoff and relay again.
