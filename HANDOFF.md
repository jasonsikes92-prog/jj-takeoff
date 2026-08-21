# J&J Takeoff — Engineering Handoff (Zero-ink autonomy era)

**Written:** 2026-08-21 16:26 EDT · **Repo:** `C:\Users\jason\JJ-Takeoff` · **Branch:** `virtual-takeoff` @ `2b007c0`
**Prior handoff:** `HANDOFF-archive-2026-08-21-1626.md` (best source for the overnight corpus-acquisition story and relay-era state; the acquisition recipes themselves live in `docs/training/RUN_STATE.md`)

---

## 1. Mission

Jason's goal, his words (8/18): **"teach you to draw your own lines and take your own
measurements"** — his markup is training signal and exception handling, never the
operating mode. The training corpus is built (his 5,400+ Buildern measurement rows
across 10 jobs = ground truth), cal #72 shipped the outer-face capability, and the
zero-ink scoreboard went 0 → **4 MATCHED + 1 NEAR, 0 wrong** in one night. Done looks
like: engine-drawn walks that certify against an independent side and price.

## 2. Current State

**Verified at `2b007c0` (gates run 2026-08-21, output quoted from `jj.py verify`):**
- Engine gates GREEN: golden 6/6 houses, self-test ALL PASS, unit battery 7/7,
  fixture cert re-pinned `2026-08-21T19:36:11Z`. Two `[FAIL]` lines remain and are
  **pre-existing stopped-track drift, not this session's**: `offline system test`
  (v3 contract: `run_phase1_measurement_observations.mjs → anthropic_structured_
  vision_client.mjs` import edge, in the tree since 8/4) and `readiness 16/13 vs
  baseline 18/11`. Engine-change gate set = golden + self-test + battery + cert.
- **cal #72 shipped** (`4d54781`): `foundation_wall_loops` now also emits
  `outer_area_sf` / `outer_polygon_pts` — the component grown one max-wall-thickness
  into its own sealed band; contour = the dimensioned face. Additive keys only.
- **Zero-ink scoreboard (harness v5, `fb6e0f2`)** — engine loops + cross-page chain
  pools + cal #68 solver + cal #71 schedule window, graded vs Jason's Buildern Inputs:
  Roberts **full heated envelope 2,126 vs his 2,127.25 = 0.08%** + garage 703/715
  1.6% (2/2 loops declared); Davis garage 899/898 0.12% + envelope 3,302/3,551 7.0%
  NEAR; Zegarra garage 547/537 1.9%. **0 wrong numbers across every run all night.**
  Raw per-loop records: `training/auto_areas_scorecard.json`; honest buckets:
  `python training/autonomy_report.py`.
- **Training corpus** (`training/`, gitignored, ~700MB): `ground_truth.json` (10 jobs'
  measurements + 20 estimates normalized), 9 budgets w/ actuals, 8 all-drawings plan
  PDFs (his traces burned in + per-segment sizes as text → `segment_sizes.json`),
  10 original plan sets (8 vector-readable; Mason + Dugger local copies are rasters),
  167 POs, `qbo_sales_by_customer.json`, `learned_rates.json` (484 name+qty matched
  rate lines), `readability_scorecard.json` (census: davis 206 chains … watkins 0).
- **Access proven ×4**: Buildern (Jason's Chrome; JARVIS `BUILDERN_*` env fallback),
  QBO MCP, Jason Gmail MCP, **Keli IMAP** via JARVIS `agent/email-tool.js`
  `searchEmail`/`fetchPdfAttachment` with `{account:{user:KELI_IMAP_USER,pass:
  KELI_IMAP_PASSWORD}}` (env in `JARVIS/.env`) — invoice PDFs extract to text.
- **Blocked/refused (correctly):** show 0/3, pace_kinards 0/4, holbrook 0/8 loops
  declared; guarino_v3 declares only a 430 SF room (its envelope never loops);
  burns/dugger/watkins produce 0 loops in range on their readable pages.

**Exact next action:** refusal diagnosis. Load `training/auto_areas_scorecard.json`,
tabulate per-loop `face × status` for show / pace_kinards / holbrook / guarino_v3,
and pick the dominant blocker (expected mix: no-solution on both faces = chain-pool
coverage; missing AREAS schedule = designer formats for `read_sqft_schedule`;
floor-plan envelopes never looping = the same shape gap heated has everywhere).

## 3. Decisions Made (and Why)

| Decision | Alternatives | Reason | Reversibility |
|---|---|---|---|
| **cal #71** (Jason): printed AREAS schedule may SELECT the dimensioned face among closure-valid all-printed readings; never feeds a quantity | refuse all face-ambiguity | inside/outside-face families both close; the sheet's own figure picks; he ran the same check by hand | his ruling — settled |
| **cal #72** (Jason, verbatim "ratify both"): outer-face emission + 8/14 engine pair blessed | keep inner-only | inner face capped envelopes at ~7%; his dim strings run to outside faces even on shared walls (garage 26'-8" = inner 25.25 + 2 walls) | his ruling — settled |
| Outer face = geodesic band-grow (dilate component by `thick_ft[1]`, ∩ sealed, contour) | polygon offset math | raster truth already in hand; sealed spans face-to-face; ~15 lines, additive | easy to refine |
| Harness seeds outer face FIRST, inner fallback per loop | outer-only (v4) | measured: each face solves loops the other refuses (outer→envelope 0.08%; inner→garage 1.6%) | settled by data |
| Union chain pool primary; page-tier only rescues too-complex | page-first (v2) | a single page CLOSES ON A WRONG READING (garage p3→665 vs true 703 needing p4) — reproduces the exact ambiguity Jason's own cert hit | load-bearing |
| Ambiguity judged by AREA of resulting walks; quarter-inch printed variants = one reading; decisive-margin else refuse | refuse all ties | 12.54-vs-12.52 isn't two readings; 8.75-vs-10.4 is — refuse only real spreads | tunable consts, top of `auto_declare.py` |
| Complexity guard: candidate-product > 300k or > 14 legs → refuse "too-complex" | let it run | 4^17 tier-0 products ran away on Davis' 206-chain pool (killed a live run) | tunable |
| His measurements are GROUND TRUTH; disagreement classifies DEFECT / CONVENTION / MY-ERROR | treat diffs as errors | cal #70 proved conventions differ (his flat roof traces vs our pitch-corrected) | doctrine |
| Raw corpus stays out of git (`/training/` ignored, root-anchored); tools force-added | commit everything | client data; tools are code | settled |
| Stopped-track v3 FAILs left untouched, flagged to Jason | "fix" them | `estimator_accuracy` is harvest-only per standing doctrine; drift predates this work | his call |

## 4. Architecture & Key Files

**Engine (modified this session):**
- `tools/jnj_takeoff.py` — the outer-face block inside `foundation_wall_loops`
  (~line 806): grows each interior component one max wall thickness into `sealed`,
  emits `outer_area_sf` + `outer_polygon_pts`. Only session engine change.

**Autonomy harness (created this session, all force-added under `training/`):**
- `training/auto_areas.py` — cross-job zero-ink harness v5: per-loop `_solve_seed`
  (outer→inner), two-tier pools, complexity guard, cal #71 window, grades vs Inputs.
- `training/autonomy_report.py` — honest buckets (a loop grades a target only ≤10%;
  MATCHED ≤2 / CLOSE ≤5 / NEAR ≤10 / else NOT PRODUCED).
- `training/parse_corpus.py` → `ground_truth.json`; `training/readability_scan.py` →
  `readability_scorecard.json` (per-page ppf/chains, consumed by the harness).
- `jobs/roberts_levelground/auto_declare.py` — Roberts-local v0; the harness imports
  its solver machinery (`solve_axis`, `evaluate_combos`, consts) verbatim.

**Docs/records:** `reference/calibration.md` (#71, #72 appended — append-only),
`docs/training/RUN_STATE.md` (recipes: Buildern export dances, queues, inventory),
`docs/training/MORNING_REPORT.md` (Jason-facing scoreboards),
`docs/HANDOFF_AI_INTEL.md` (Handoff.ai/H1 recon incl. TakeoffBench access path).

**Outside this repo:** `Desktop\Claude\estimator_accuracy\golden_fixture_certification_
2026-07-20.json` — rewritten by the cert refresher this session, **uncommitted in the
workspace repo** (that repo also carries pre-existing `v3_execution_readiness.*` drift
+ untracked `_backup/`, `multi-agent-guide/` — none of it this session's).

**Looks touchable, isn't:** `tools/tests/golden/*/expected.yaml` values,
`jobs/roberts_levelground/declared_walks.json` (Jason's certified answers = grading
truth, never autonomy input), `reference/` rate-book VALUES, `estimator_accuracy/`.

## 5. Gotchas & Hard-Won Knowledge

- **Each wall face solves loops the other refuses.** Outer-only seeding (v4) silently
  dropped v3's inner-face wins. Always try both.
- **A single sheet can close on a wrong reading** (v2): garage from p3-only chains =
  665 SF closure-valid and wrong. Cross-sheet union first; page-pool only for rescue.
- **Solver combinatorics run away on dense chain pools** — Davis' 206-chain union hung
  a run (killed by PID). Guard BEFORE `solve_axis`, refuse "too-complex".
- **`foundation_wall_loops` on floor plans finds closet-scale rooms, not envelopes**
  (guarino's lone declare = a 430 SF room). The ≤10% grading window in
  `autonomy_report.py` is what keeps such declares from polluting the scoreboard.
- **`A && B && python x.py &` backgrounds the whole chain** in Git Bash — a commit
  once silently didn't land. Verify `git log` after committing; never trust `&`.
- Unanchored `.gitignore` dir patterns match at any depth — `training/` swallowed
  `docs/training/` until root-anchored to `/training/`.
- **Watkins dims are OUTLINED VECTOR glyphs** (calibration #537's documented
  measurement-hostile case) — census reproduced it; vision lane, no parser fix owed.
- Buildern UI (recipes with coordinates in RUN_STATE): search inputs need
  find→`form_input` (typed text gets overwritten by late hydration); download menus
  shift position per page-state — screenshot before the second click; **navigating
  away kills an in-flight "Preparing download" render**; the Chrome extension drops
  every few hours and recovers on retry.
- Keli mailbox: the export is `searchEmail` (NOT searchMailbox); `fetchPdfAttachment`
  already returns extracted `text` + saved `path`; ambiguous matches return
  `candidates` — re-call with `uid`.
- `jj.py verify` includes stopped-track checks that fail pre-existing; a red VERIFY
  does not automatically mean the engine gates failed — read the line items.

## 6. Conventions In Play

Gates after ANY `tools/jnj_takeoff.py` edit: `python jj.py verify` + `python
Desktop\Claude\estimator_accuracy\refresh_golden_fixture_certification.py --write`
(refuses unless golden is green). Additive keys only in engine dicts. Fail-closed:
refuse loudly with a named reason, never guess (the 0-wrong streak is the product).
Calibration entries: numbered, append-only, Jason's rulings only — next is **#73**.
Commits: descriptive line + consequences body + `Co-Authored-By: Claude Fable 5
<noreply@anthropic.com>`. Chat output to Jason: BRIEF, lead with the number.
Buildern/QBO/email: read-only. Rate-book VALUES: proposals only, never edited.
Governing files: `~\.claude\CLAUDE.md`, `Desktop\Claude\CLAUDE.md`, this file.

## 7. Open Questions

1. *(next session)* Show/Pace/Holbrook: which blocker dominates their all-refused
   loops — both-face no-solution, missing schedule rows, or trace topology? The
   per-loop `face`/`status`/`pool_tier` fields in `auto_areas_scorecard.json` answer
   this without new runs.
2. *(next session)* Floor-plan envelopes never loop (heated everywhere, guarino
   especially). What autonomous shape source closes that — outer-face on the
   FOUNDATION page mapped to heated scope, elevation-reconciled extents, or a new
   floor-plan wall-network tracer?
3. *(next session)* `read_sqft_schedule` returns rows for some designers, empty for
   others — sample the misses and extend, or accept schedule-less jobs refuse more?
4. *(Jason, eventually)* Certification admission for auto walks needs an independent
   second side (his stroke played that role on Roberts). Outer-face raster area vs
   the walk is engine-vs-engine — does that satisfy independence, or does a human
   spot-check stay in the loop? Not ripe until a concrete proposal exists.
5. *(Jason)* The v3 stopped-track contract failure (`phase1 → vision-client` import,
   since 8/4): investigate, bless, or leave? → filed to JARVIS.
6. *(Jason)* Send Handoff the TakeoffBench-V1 research request (15 external graded
   blueprint sets; access path in `docs/HANDOFF_AI_INTEL.md` §4)? → filed to JARVIS.
7. *(Jason)* Davis fiber-cement siding ran $3.20/ft² vs $2.50 on Burns/Roberts/Show
   (`learned_rates.json`) — sub change or scope premium? One-line answer calibrates
   the rate book.

## 8. Do Not Touch

- Golden `expected.yaml` asserted values/tolerances; the 2% reconciliation gate; the
  fail-closed refusals. `_AREA_METHOD_ORIGINS` coupling.
- `declared_walks.json` — grading truth; never an input to the autonomy lane.
- Rate-book VALUES (`reference/`), even under "full access" — proposals only.
- `estimator_accuracy/` source (harvest-only), including its two failing checks.
- The dropdown teach cards (markup-first is settled; cards are verification detail).
- `training/` raw client data stays out of git; `HANDOFF-archive-*.md` history.

## 9. Resume Command

> Read `HANDOFF.md`, then `docs/training/RUN_STATE.md`. Start with refusal diagnosis:
> tabulate per-loop `face × status × pool_tier` from `training/auto_areas_scorecard.json`
> for show, pace_kinards, holbrook, guarino_v3, and pursue the dominant blocker
> (schedule formats → `read_sqft_schedule` samples; chain coverage → pool diagnostics;
> floor-plan envelopes → open question 2). Run `python jj.py verify` before and after
> any engine edit — engine gates are golden/self-test/battery/cert; the offline-v3 and
> readiness FAILs are pre-existing stopped-track drift, leave them. Do not touch golden
> values, `declared_walks.json`, or rate-book values. Keep chat output brief; save
> engine-doctrine changes for Jason's ruling as cal #73+.
