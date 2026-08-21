# Overnight self-calibration — morning report (8/18 → 8/19)

**Mandate:** pull every Buildern takeoff, cross-reference my measurements against
yours (yours = ground truth), cross-reference pricing against POs/bids/actuals/
invoices, fix what's wrong, calibrate. cal #71 approved and wired in.

---

## What got built overnight

**1. The corpus (628MB+, `training/`, raw data gitignored, tools committed):**
- **10 jobs with your measurement ground truth** — 5,400+ rows normalized into
  `ground_truth.json`: Roberts, Davis, Zegarra, Guarino V3, Show, Pace Kinards,
  Dugger, Burns, Mason, Watkins.
- **20 estimates** (the 10 above + Waddell, Thomas, Villanueva, Miller, Hernandez,
  Holbrook, Stiggers, Wilson, Lankford, Peterson, Talbot).
- **8 takeoff-drawing PDF sets** — your traced measurements burned onto every
  sheet at 300 DPI with legends + per-segment sizes (Davis 83MB, Show 112MB,
  Dugger 184MB, Burns 108MB, ...). Per-segment values parse straight out of the
  text pages (`segment_sizes.json`: Roberts 97, Davis 96, Guarino 113 segments).
- **10 original plan sets** hunted from local disk + Buildern Files.
- 167 approved POs ($2.08M), QBO per-job revenue, projects inventory.

**2. Access proven end-to-end (all four):** Buildern (your Chrome), QuickBooks
MCP, your Gmail, and **Keli's inbox** via JARVIS IMAP — invoice PDFs fetch and
extract to text (Builders FirstSource, HD Trade Credit, Padgett's
Peterson/Talbot invoices spotted immediately).

**3. Engine readability census across all 11 plan sets** (`readability_scorecard.json`):

| verdict | jobs |
|---|---|
| ✓ fully readable (scale + chains) | Roberts 88ch · Davis 206ch · Guarino 146ch · Show 168ch · Pace 144ch · Burns 64ch · Holbrook 55ch · Zegarra 122ch |
| ⚠ scale but no chains | Watkins — census independently reproduced calibration.md's documented finding (Lifestyle Design plans: dims are OUTLINED VECTOR glyphs, not text; known measurement-hostile) |
| ✗ raster scans (no text layer) | Dugger, Mason (Buildern traces rasters; our chain-verification cannot — OCR frontier) |

**4. Zero-ink autonomy harness on all readable jobs** (`auto_areas.py` — engine's
own wall loops + cross-page chain pools + cal #68 closure solver + cal #71
schedule window, graded vs your Inputs):

| job | target | yours | engine (zero ink) | delta | verdict |
|---|---|---|---|---|---|
| roberts | Garage | 715 | 703 | **1.6%** | **MATCHED** |
| davis | Garage | 898 | 908 | **1.1%** | **MATCHED** |
| davis | First floor | 3,551 | 3,302 | 7.0% | NEAR (inside-face bias) |
| — | 6 other targets | | | | NOT PRODUCED (refused, never wrong) |

**Zero-ink scoreboard: 2 MATCHED / 1 NEAR / 6 not produced — and 0 wrong numbers.**
Two different houses' garages now auto-measure inside the 2% certification gate
with no human ink. Loop dispositions across all 38 candidate loops: 14 diagonal
(trace chamfers/angled walls — splitter cap is the lever), 9 too-complex (dense
chain pools — per-page pooling first is the lever), 7 no-solution (inside-face
offsets — the outer-face engine lever), 4 ambiguous (missing AREAS schedule on
those designers' formats), 4 auto-declared. Every refusal is named and rankable —
this is the calibration loop doing its job.

**5. Rate learning started** (`learned_rates.json` — 484 lines, name+qty joint
matched, full provenance):
- Fiber-cement horizontal siding **$2.50/ft² sub** (Burns, Roberts, Show) — Davis
  ran **$3.20** → variance to explain (sub change? height/complexity premium?)
- Vertical fiber-cement **$4.60/ft²** (Roberts)
- Tile shower walls material allowance **$4.00/ft² universal** across 9 jobs
- Bath floor tile **assembly $16/ft² = $4 allowance + $3 sundries + $9 labor** —
  assemblies decompose cleanly into components
- Tall cabinets $300–350/LF; exterior accent wall $7.00/ft²
- Your estimate cost-types: MATERIAL / LABOR / SUBCONTRACTOR / EQUIPMENT / FEE /
  ALLOWANCE / ASSEMBLY

## Post-ratification update (cal #72, same day)

You ratified outer-face loops; built behind the full gates (golden 6/6,
self-test, 7/7 units, cert re-pinned) and wired into the harness with inner-face
fallback. **Zero-ink scoreboard moved 2 MATCHED / 1 NEAR → 4 MATCHED / 1 NEAR,
still 0 wrong:**

| job | target | yours | engine | delta |
|---|---|---|---|---|
| roberts | **First floor (full envelope)** | 2,127.25 | 2,126 | **0.08%** |
| roberts | Garage | 715 | 703 | 1.6% |
| davis | Garage | 898 | 899 | **0.12%** |
| davis | First floor | 3,551 | 3,302 | 7.0% (NEAR, inner fallback) |
| zegarra | Garage | 537 | 547 | 1.9% |

Also closed: `todo_takeoff_engine_ratify_0814` + the morning-review todo;
cal #72 recorded. Known pre-existing FAIL left alone per do-not-touch:
the stopped v3 track's offline contract (phase1→vision-client import edge, in
the tree since 8/4 — predates this run; readiness 16/13 vs baseline 18/11 is
the same drift). Worth a look when you're in that codebase next.

## Honest gaps + next levers

1. **Whole-envelope autonomy still needs the outer-face loop** (the 8/18 finding
   stands): loops trace inside faces; heated envelopes on floor plans mostly
   don't loop at all. Garage-scale slabs auto-declare; big envelopes refuse.
   Lever: outer-face emission from the wall-pair decomposition (engine edit,
   your ratify).
2. **Watkins**: already ruled measurement-hostile in calibration.md (#537 block —
   outlined-vector dims; your cold-vision test there measured ±1.8% after the
   porch fix). No parser fix owed; treat as the vision-lane case it already is.
3. **Dugger + Mason are rasters** — Buildern Files may hold vector originals
   (Zegarra's did); else they're the OCR frontier and stay measurement-corpus-only.
4. Invoice PDF → line-item parsing (BFS/HD layouts) for the pricing ledger.
5. Budget exports (actuals by cost code) per job — not pulled yet.
6. Estimate-tail leftovers: Bouchard, Hetherington, Bozeman, Dolsen, Wilson PR-044.

## Refusal-diagnosis session (8/21 evening) — 4 MATCHED → 5, still 0 wrong

Ran the diagnosis your handoff queued: why show/pace/holbrook/guarino refuse
everything. Three causes found, three fixes shipped (bd9786d, 2a48662, 36c4407 —
gates green, cert re-pinned):

1. **Phantom loops from junk-scale pages.** Holbrook's entire slate was 4.8–7.7k
   SF ghosts from pages with a 0.73 px/ft "scale" and zero dimension text,
   crowding its real floor-plan loops out of the budget. Pages now seed loops
   only with parsed dimension text or a high/good scale vote.
2. **The 14-leg cap refused notched footprints** (10 of 23 refusals, 15–26 legs)
   before the real runaway guard ever ran. Cap removed; the guard rules.
3. **Micro-jog artifacts blocked real garages.** Pace's garage loop carried
   0.6–1.7 ft band-contour steps no designer dimensions — nearest printed dims
   2.33+. Undimensioned sub-2-ft jogs now fold into their neighbor leg (closure
   math untouched; real dimensioned bumps keep their printed value and survive).

| job | target | yours | engine (zero ink) | delta |
|---|---|---|---|---|
| **pace kinards** | **Garage** | **623.71** | **630.6** | **1.1% — NEW MATCHED** |
| roberts | First floor | 2,127.25 | 2,126 | 0.08% |
| roberts | Garage | 715 | 701.5 | 1.8% (was 703; 0.21% off your certified 703) |
| davis | Garage | 898 | 899 | 0.12% |
| davis | First floor | 3,551 | 3,302 | 7.0% NEAR |
| zegarra | Garage | 537 | 547 | 1.9% |

Pace's garage declared from TWO pages independently (637.0 and 630.6, both
schedule-selected to its printed 630.27) — a 1% cross-page agreement, no ink.
Holbrook also declares its garage (671.3 vs printed 666, 0.8%) and covered deck
(492.5 vs 483, window-edge pick on a wide spread — shakiest of the night), but
holbrook has no Buildern Inputs, so those grade against the sheet only.

**Closed by evidence, not fixable by selection:** guarino's first floor. Your
2,637 / the sheet's printed 2,599 vs the engine's full solution space — all
16,731 closure-valid readings span 2,693–2,800. The schedule row now parses
(engine fix: "1ST FLOOR LIVING" family + a veto that kept a phantom 2,021 SF
"code-year" row out of burns' golden schedule), but there is nothing in-window
to select. That envelope needs the floor-plan tracer (open question 2), and the
refusal is fail-closed doing its job.

## External review triage (8/21 late — `REVIEW-FINDINGS-2026-08-21.md`)

A read-only audit by another agent (not me — it snapshotted the repo mid-flight
between my commits; provenance unknown, possibly Sol) landed in the repo root.
Verified every claim against the code myself:

**Confirmed real, fixed tonight:**
- *Backup stale + incomplete* — the mirror hadn't run since 8/14; tonight's
  engine wasn't in it and JJ-Takeoff has NO git remote. Ran `jj.py backup`
  (515 files updated) → `eval/verify_backup.py` now says **BACKUP VERIFIED**.
- *cal #72 had no committed regression test* — outer-face keys were proven only
  by the gitignored scorecard. `tools/tests/test_outer_face_loops.py` now pins
  them on the golden Roberts sheet, anchored to YOUR certified 2,127.25 SF
  (engine outer face: 2,142.6, 0.72%). Auto-discovered by the verify battery.
- *Scoreboard could double-count* — grading paired each target with its nearest
  declare and exempted MATCHED from the reuse guard, so one walk could count
  twice. Now a one-to-one assignment; tonight's 5 MATCHED are unchanged (they
  were 5 distinct walks — verified before and after).
- *Verifier printed a false detail* — the offline-test line hard-coded
  "exit 0" even when failing. Now prints the real exit code.

**Confirmed real, YOUR call (they change what "green" means):**
- `coverage.py` fails OPEN: missing scorer output or a nonzero
  falseCertificationCount cannot fail `jj.py verify`.
- The readiness check can NEVER fail verify (it passes a literal True), so the
  16/13-vs-18/11 regression only shows as text.
- `jj.py save` still commits the DESKTOP workspace repo (pre-consolidation
  leftover) — `git add -A` there would sweep the 627MB `_backup/` mirror into
  a commit. Don't use `save` until re-pointed; `backup` alone is safe.
- Hardening any of these makes verify permanently red under the standing
  stopped-track drift — quarantine vs hard-fail is a doctrine choice, queued
  below.

**Race artifacts, no action:** its "scoreboard not current / 3 MATCHED"
readings came from grading a scorecard my background harness was mid-rewrite
on; the completed runs say 5 MATCHED + 1 NEAR of 15, reproducible at
`36c4407`. Its missing-fitz gate failures are its own shell's Python, not the
gates (its recommendation to document the supported runtime is fair).

## Waiting on you

- Ratify list: bd9786d + 36c4407 (harness), **2a48662 (engine — schedule
  keywords + title-row veto, gates green, cert re-pinned)**.
- Review follow-ups queued for ruling: fail-closed coverage/readiness in
  `jj.py verify` (or quarantine the stopped-track checks out of verify),
  re-point `jj.py save` at the engine repo, add a git remote for JJ-Takeoff.
- **cal #73 candidate:** cal #71 says the schedule selects among "all-printed"
  readings — but every selected walk to date (your ratified 2,126 envelope
  included) carries 1–2 derived-by-closure legs. Operative reading: a derived
  leg's value is exactly what the printed legs force, so it counts as printed.
  Bless or narrow?
- Rulings still queued: Watkins notation sample; the stopped-track v3 FAILs.
