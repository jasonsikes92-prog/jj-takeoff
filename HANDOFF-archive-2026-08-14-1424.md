# J&J Takeoff — Session Handoff

**Written 2026-08-04.** This is the single entry point. Read it before touching source, running a plan, or authorizing any paid API call.

It replaces the old `START_HERE.md` and supersedes `docs/HANDOFF-2026-08-03.md` and `docs/ROADMAP.md` on **state and next actions** — those two remain the best source for deep method detail and the autonomous engine's phase breakdown, and are accurate through 2026-08-03.

---

## 1. Where everything is

```
C:\Users\jason\JJ-Takeoff\          THE program. git repo, 583 MB, 11 commits.
├── tools\jnj_takeoff.py            the measurement authority (~5,700 lines)
├── tools\tests\                    golden suite — 6 houses with real ground truth
├── reference\calibration.md        1,671 lines, 64 data points — the durable memory
├── reference\rate_book.json        603 template lines + a Jason-approved overrides list
├── templates\                      18-division estimate + measurement sheets
├── eval\coverage.py                answered fraction at zero false positives
├── eval\scale_sweep.py             ⭐ run at intake — catches print-rescaled sets
├── eval\verify_backup.py           proves the OneDrive mirror is byte-faithful
├── eval\push_to_github.ps1         private remote, waits on `gh auth login`
├── eval\truth\ + eval\corpus\      690 positive truths / 1,167 zeros; 10-job corpus
├── levelground\                    report + market pricing + bid-gap engine + live site
├── jobs\                           L J Show, Guarino, Dugger takeoffs
├── docs\                           evaluation, lessons, fork plan, consolidation
└── jj.py                           verify · backup · status · estimate · save
```

`~\.claude\skills\jnj-estimate-takeoff` is a **junction** to this repo, so the
`jnj-estimate-takeoff` skill resolves unchanged. Pre-consolidation copy parked at
`~\.claude\_pre-consolidation-2026-08-04\`.

**Not here:** `C:\Users\jason\_ARCHIVE\estimating-exhaust-2026-08-04\` holds 10.9 GB of
autonomous-engine run artifacts plus 2 MB of pre-git engine history. Recoverable, out of the way.
`Desktop\Claude\estimator_accuracy\` (717 MB) still holds the autonomous engine's **source** —
kept for later harvest, not being developed.

---

## 2. Prove it before trusting it

```bash
cd C:\Users\jason\JJ-Takeoff
```
```bash
python jj.py verify
```

**Expected right now — `VERIFY: NOT GREEN`, and that is the correct baseline:**

| Gate | State |
|---|---|
| golden measurement suite | ✅ 6/6 houses green, 22/22 asserts, 13/13 comparisons |
| engine self-test | ✅ ALL PASS |
| fixture certification | ✅ no drift *(re-certified 2026-08-05 after the engine change)* |
| offline system test | ❌ red — pre-existing |
| readiness (expects not_ready) | ⚠ **16 passed / 13 failed** vs an 18/11 baseline |
| coverage | ✅ 8 of 2,880 (0.3%), **0 false positives** |

**All the red is in `estimator_accuracy\` — the stopped autonomous track. None of it blocks
anything in §5.** Three distinct causes, in order of how much they matter (not much):

1. **Two blockers predate the consolidation**, confirmed by running the original `jj.py` from the
   old tree and getting an identical result. Both trace to the 2026-08-03 vision-client landing:
   the production-engine snapshot rejects a new dependency edge
   (`run_phase1_measurement_observations.mjs -> anthropic_structured_vision_client.mjs`), and
   readiness gained `all_fields_implementation_paths_wired`.
   **Owed: is that edge intended?** A ruling, not a patch.
2. **`historical_golden_regression_guard_certified` appeared 2026-08-04**, after the framing-layer
   engine change and the re-certification that followed it. **The underlying golden data is
   healthy** — the certification records `exitCode 0`, 22/22 measurement assertions, 13/13
   comparison checks, 0 known gaps, 0 skipped, 0 errors. The gate reads
   `summary.unwiredProbes / skippedOrNeedsPlan / errors`, and the certification file writes those
   under `result`, not `summary`. It looks like certification *plumbing*, not a quality signal —
   but that was not run to ground, deliberately.
3. ⚠ **If you change `tools/jnj_takeoff.py` or `run_golden.py`, fixture certification WILL drift**
   and cascade into readiness. Fix:
   ```bash
   python C:\Users\jason\OneDrive\Desktop\Claude\estimator_accuracy\refresh_golden_fixture_certification.py --write
   ```
   It refuses to certify unless the golden suite is green at that moment, which is the point.

**Do not spend a session chasing these.** Jason, 2026-08-04: *"don't waste tokens chasing a
ghost."* They guard a track that is not being developed.

**Before shutting the laptop:** `python jj.py save` (mirror + commit). This repo is outside
OneDrive; the `_backup\` mirror is its only backup until the GitHub remote is live.

---

## 3. What changed on 2026-08-04

### The program was consolidated out of eleven locations
13.2 GB of estimating material across the workspace, `~\.claude\`, and Desktop became one 583 MB
git repo. 1,097 MB deleted, 10.9 GB archived, nothing lost — every deletion was verified against
the repo **and** the backup mirror by sha256 first.

⛔ **`.estimate_deps` was not dead weight — it was actively harmful.** It sat at `sys.path[0]` in
two tests and its stale numpy shadowed the working system copy, which is why
`test_area_measurement_integration.py` was dying on `No module named
numpy._core._multiarray_umath`. **Deleting it fixed the test.** Don't re-vendor packages.

### Five live rates loaded (Jason, 2026-08-04)

| Line | Was | Now |
|---|---|---|
| Framing Lumber | $14.00 | **$10.00** /SF under-roof |
| Framing Labor | $6.50 | **$6.00** /SF **per framed layer** |
| Electrical | $7.00 | **$6.00** /SF heated + garage, **porches excluded** |
| Siding — Vertical B&B | $4.50 | **$4.40** /SF wall |
| Siding — Horizontal Lap Hardi | — | **$3.30** /SF wall (confirmed) |
| Drywall Level 4 | — | **$1.44** /SF (confirmed) |

Written into **both** `rate_book.json["lines"]` (what `price_lines()` actually reads) and
`["overrides"]` (the audit trail with evidence + approval date). ⚠ **`price_lines()` does not read
`overrides` — a new rate must go in both or it won't price.**

The template's $14 lumber was the outlier that cost $33k on L J Show; three completed jobs came in
at $9.35, $9.24, $9.20.

### ⭐ Framing labor is per framed LAYER, not per footprint (calibration #64)

**The biggest finding of the session.** $6.00/SF buys **one framed system** over an area:

| What | Layers | $/SF |
|---|---|---|
| Basement / 1st / 2nd / 3rd / garage, **including the roof over them** | 1 | $6 |
| Covered porch, or any roofed area outside the house | 1 | $6 |
| Deck — framing and posts only, no roof | 1 | $6 |
| **Covered deck** — the deck **and** its roof | **2** | **$12** |
| **Covered concrete patio** — roof only; a slab isn't framed | **1** | **$6** |

Reconciles two clean jobs at Jason's $6.00: **Peterson +0.2%, Wilson +1.4%.** Flat $6.00 without
the rule reads −7% to −9%.

**This supersedes calibration #33's "$6.50 blended, DEFINITIVELY FLAT."** That was a fudge factor —
the missing second layers averaged ~8% of framing labor, a flat rate absorbed them as a fake
premium, and the residual got explained away as "complexity/site." It fit three actuals to ~2%
while being structurally wrong, the same failure as the two earlier `footer_lf` formulas that hit
Jason's number through cancelling errors.

**How it was found, and why it matters procedurally:** Jason stated $6.00; the assertion graded it
−7.6% against actuals; the disagreement was surfaced rather than tuned away; Jason explained the
formula. **Widening the tolerance to make $6.00 pass would have buried the rule and left every
deck house under-bid.** Never tune a test to match an unverified rate.

Two deck paths, same arithmetic, different meaning — a `deck paths` self-test pins them apart:
- `covered_deck_sf` — a roofed deck, already inside under-roof SF → buys a **second** layer
- `open_deck_sf` — uncovered deck / balcony / rooftop deck, **not under roof at all** → buys its
  **one** layer as an addition

⛔ **Watkins is not evidence — do not re-open it.** Its master-bedroom deck + rooftop balcony was a
special case settled with a **blanket allowance**, isn't drawn on the only plan set on this machine,
and its 292 SF was solved backward from the actual (circular). Jason: *"don't waste tokens chasing
a ghost."* The rule stands on Wilson + Peterson.

---

## 4. Two rules that cost real money

**1. Never take the scale from the title-block note.** Roughly **1 set in 6** is printed
off-nominal. Roberts says `1/4" = 1'-0"` (18.000 pt/ft) and actually measures **16.714** on 187
dimension votes — trusting the note understates **every area by 14.5%**, and nothing on the sheet
discloses it.

```bash
python eval/scale_sweep.py
```
Flags `WHOLE-SET RESCALED` with the area-error figure, versus isolated mixed-scale detail sheets.
**Run it at intake on every plan set.**

**2. Never wrong beats always answers.** All ten graded jobs terminate
`more_information_required` with **zero false positives**. A wrong quantity that looks right gets
bid. That property is the product — grow what it answers without ever losing it.

---

## 5. What to do next

### Level Ground — the measurement problem is already solved
A pre-bid report needs **six numbers**, not the estimate's 230 rows: `heated_sf`, `framing_sf`,
`roof_surface_sq`, `foundation_wall_lf`, `slab_area_sf`, `basement_area_sf`. Everything else is
static advocacy content — the 8-item `PRE_BID_SCOPE_CHECKLIST` and 4 `STANDARD_UNKNOWNS`. The
golden suite already proves those six at 0.0–1.7% on real plan sets.

1. **End-to-end dry run — the only untested link.** `gen_reports.py` injects a **hardcoded sample**
   takeoff, so `run_takeoff → report_from_takeoff` has never run on a real set. Use roberts: a real
   12-sheet set that is *also* the print-rescaled one, so it exercises the scale guard in the same
   pass. **Time it — that's the unit cost per sale, and it tells you whether $99 works.**
2. **Stripe live activation** — per `levelground\TODO.md` the buy button is still in **test mode**;
   a real customer cannot pay. LLC and EIN are done. This is the actual launch blocker.
3. **Then the bid-gap half** — `ingest_bid()` / `findings_from_bid()` are built and self-tested.
   Reading and reconciliation, an AI strength. Second sale to the same customer.

### J&J takeoff — ordered by dollars
1. **Make the plan side agree with itself.** On L J Show p5, `window_count()` returns **22** while
   the reconcile's own parser returns **30 windows / 40 doors** — same page, two parsers. And 40
   doors on a floor plan is wrong; the "suffix-less tag ≥6'6" is a door" rule over-fires. Fix this
   *before* elevation reconciliation, or the alerts name numbers nobody can act on.
2. **Then openings reconciliation.** Jason's ruling: *match = reconciled; mismatch = alert me, never
   auto-resolve; mulls are the first hypothesis (double = 2 windows, triple = 3).* Measured:
   elevations **48**, Jason's hand takeoff **46**, plan tags **22**. ⚠ On L J Show every plan tag
   came back `basis: single` — that set carries no mull markers at all, and the two sides read mulls
   from different notations (plan wants a nearby DOUBLE/TRIPLE word, elevation wants a `(2)` prefix).
3. **Apply fixes already built but never shipped** — `elevation_opening_count()` returns 43 while
   the shipped L J Show estimate still carries 22; `beam_wrap_lf()` returns 289 vs Jason's 291.
4. **Register a real holdout.** The prospective registry is empty, 0 of 10. Everything to date is
   historical replay and the golden fixtures say so in their own comments. **Until then, "trust" is
   unmeasured** — 6/6 green is regression protection, not accuracy evidence.

---

## 6. Owed by Jason

| # | Item | Blocks |
|---|---|---|
| 1 | `gh auth login`, then `eval\push_to_github.ps1` | off-machine backup. ⚠ what would go up is confidential — `calibration.md` (real client names, job costs, margins), the truth file, the rate book. No live secrets (verified; `.env.local` untracked). The script hard-gates on visibility=PRIVATE before anything leaves the machine |
| 2 | **A learning price log** (his ask) — prices move a lot and nothing currently ages a rate or prompts re-confirmation. `rate_candidates.json` + `propose_rate()` + `overrides` exist; the aging/prompting layer does not. Needs scoping | rate freshness |
| 3 | **National-average × regional multiplier fallback** (his ask) — `MARKET_RATE_BOOK` has a US cost index and correctly *refuses* to price an uncalibrated market, but works at whole-house $/SF, not per line item. Decide the altitude before extending | Level Ground pricing away from Middle GA |
| 4 | Is the 8/3 `anthropic_structured_vision_client` dependency edge intended? | the two red verify gates |
| 5 | Selections — short form, infer from finish schedule, or flag? | full sheet population |
| 6 | The other ~18 Buildern measurement sheets | grader ceiling, stuck at 42.85% |
| 7 | Is $3.30 lap Hardi flat regardless of exposure? | `SIDING_RATE_BOOK` splits lap by exposure (7" vs 5"); Jason gave one flat number. `rate_book.json` is correct today, the code book's lap entries are flagged OPEN |
| 8 | Engineered floor rate — used for basement/2nd/3rd floors **and** as garage ceiling joists to span the long direction. Calibration has ~$9/SF | framing material completeness |

---

## 7. Conventions that are not optional

- **Address Jason by name at the start of every response** (`~\.claude\CLAUDE.md` §10).
- **`calibration.md` is the durable memory.** Every method ruling and cold-test result goes there as
  a numbered data point. **Now at #64 — check the max before appending** (a #55 collision has
  happened).
- **Every new engine function ships with a self-test line** asserting against a real Jason number.
  `python tools/jnj_takeoff.py` must print `ALL PASS`.
- **A tolerance wide enough to never fail is worse than no assertion.** Never widen a tolerance to
  make a number pass — §3 is what that discipline bought.
- **Matching the number is not the same as being right.** `footer_lf` and the $6.50 framing rate
  both hit Jason's numbers while structurally wrong.
- **Conflicts are flagged, never auto-resolved.**
- **Client-facing Descriptions carry no takeoff math or internal tags** — `lint_buildern_descriptions()`
  must return 0 before shipping.
- Per-line markup 15/7/7/7/8/15; **no O&P or contingency lines** (Buildern's summary handles those).
- **Verify provenance before claiming work.** ChatGPT ("Sol") also works on these systems.
- Zero paid API calls without an explicit call cap **and** USD cap quoted to Jason first.

## 8. Do not touch

- **Roof footprint 6,159 SF and the shingle/metal split on L J Show** — settled on physical evidence.
- **`footer_lf()`'s formula** — two earlier versions hit Jason's number by accident and were
  structurally wrong. The current one is deliberately 6.1% off his raw and correct.
- **Drywall $1.44/SF** — Jason re-confirmed 8/4 ("gives us some cushion").
- **`estimator_accuracy\production_runs\`** (now archived) — immutable, never edit in place.
- **Do not re-open Watkins** as framing evidence.
- **Do not claim 98% accuracy** or call historical plans holdouts.

---

## 9. Resume command

> Read `C:\Users\jason\JJ-Takeoff\HANDOFF.md`. Then `cd C:\Users\jason\JJ-Takeoff && python jj.py verify` — expect **`VERIFY: NOT GREEN`**: golden suite 6/6, self-test ALL PASS, certification clean, coverage 0.3% at 0 false positives, and red on the offline system test + readiness **16/13**. That is the correct baseline, not a regression, and all of it lives in the stopped autonomous track.
>
> Highest-value next action is the **Level Ground end-to-end dry run on roberts** — it is the one untested link and it produces the unit-cost number that decides the $99 price. Time it.
>
> Do not widen a test tolerance to make a number pass. Do not re-open Watkins. Run `python jj.py save` before the laptop is shut down or moved.
