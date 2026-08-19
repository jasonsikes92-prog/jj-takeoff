# J&J Takeoff Engine — Build Roadmap

Created 2026-08-03. **This is the tracking document.** Update status here as phases complete;
`HANDOFF.md` records what happened, this records what's next.

---

## ⭐ THE GOAL — restated by Jason 2026-08-18

**"The goal is not to keep having to draw on each plan. The goal is to teach you to
draw your own lines and take your own measurements."** His markup is TRAINING SIGNAL
and exception handling — never the permanent operating mode. This formally retires the
"autonomous stays defunded" doctrine line: autonomy is the product, but it runs BEHIND
the fail-closed gates this repo built, never instead of them. (Handoff built H1 the
same way — founders hand-marked thousands of blueprints as training data; see
`docs/HANDOFF_AI_INTEL.md` for the full competitor recon.)

**Architecture consequence:** the supervised loop and the autonomous product are one
system. Certification (walks vs the sheets' own chains, 2% gate) is an autonomous
GRADER; Jason's certified strokes are the labeled corpus; the teach loop is the
exception path. Autonomy = engine proposes → gates grade → Jason adjudicates failures.

### Autonomy lane v0 — first measured run (2026-08-18, `jobs/roberts_levelground/auto_declare.py`)

Engine-drawn walks with NO human ink: shape from `foundation_wall_loops` (the engine's
own paired-wall decomposition), lengths from BOTH plan sheets' printed chains pooled
(p3+p4 — Jason's own garage certification needed cross-sheet dims), solved under
cal #68 rules (≤1 derived leg/axis, closure ≤0.05 ft), ambiguity judged by AREA,
plan's printed AREAS schedule used as a face-SELECTOR only (⚠ pending ruling below).
Report-only: writes `auto_walks.json`, never touches `declared_walks.json` or the engine.

| Component | Result | vs certified | Why |
|---|---|---|---|
| garage slab | ✅ auto-declared 702.4 SF, closure 0.00 | **0.22%** — 6/6 legs match Jason's walk | full chain worked |
| front porch slab | ⚠ auto-declared 203.8 SF | 2.74% — wrong V split (8.17/10.40 vs his 9.38/7.77) | schedule window admits 4 readings; no independent side to referee |
| crawlspace envelope | ✋ refused | all 5,000 closing readings are the INSIDE face (~1965 SF vs 2106) | loop = inside face + micro-jogs; outside-face shape doesn't exist autonomously |
| heated envelope | ✋ refused | — | floor-plan loop decomposition resolves rooms, not the envelope |
| rear deck | ✋ refused | — | same — no autonomous shape source |

**Scoreboard: 2/5 auto-declared, 1/5 inside the 2% gate, 0 wrong numbers shipped**
(every failure refused loudly with a named cause — the zero-false-positive property held).

### The three named gaps (next levers, in order)

1. **Outside-face shape** — the loop decomposition knows both lines of every wall pair;
   emitting the OUTER loop (engine edit, needs Jason's ratify + full gates) unlocks
   crawlspace and sharpens every snap. This is the single highest-value lever.
2. **Floor-plan envelope detection** — heated/deck have no autonomous shape at all today.
   Candidate: outermost wall-pair boundary on floor plans, or elevation-reconciled extents.
3. **An independent second side for autonomous runs** — on Roberts, Jason's stroke was
   the pixel side. Blind runs need a non-chain verification (outer-face pixel area, or
   schedule-as-verification once ruled) before an auto walk can ever certify.

### Pending Jason rulings (autonomy lane)

- **Proposed cal #71:** the plan's printed AREAS schedule may SELECT which closure-valid,
  all-printed-legs reading is the dimensioned face (never feed a quantity). Both v0
  auto-declarations depend on it; walks carry `selected_by` marking the dependency.
- The 8/14 engine-edit ratify backlog (`todo_takeoff_engine_ratify_0814`) still open.

### Cloned from Handoff (recon 8/18, mapped to this roadmap)

- **Summary-report contract** (assumptions / missing info / clashes per run):
  `auto_declare.py` exceptions are v0; formalize as a required emission per cert run.
- **Cross-sheet reading** ("a detail on page 40 changes the quantity on page 12"):
  adopted as cross-page chain pooling; grows into Phase 3 reconciliation.
- **Clash detection** (schedule-vs-elevation counts): already Phase 3's opening move.
- **TakeoffBench-V1** (their 15-set benchmark, harness in "OpenHarbor", data by research
  request): external fixtures for grading autonomy beyond Roberts — Jason to send the
  research request when ready.

---

## The product

A program that reads a residential plan PDF and fills J&J's measurement sheet — all 230
measurable rows — correctly. Jason's estimate template turns that sheet into an estimate by
formula, so **the measurement sheet is the entire deliverable.** Nothing downstream needs
building.

**Ship = Skip stops doing 5–8 hour hand takeoffs.** The engine fills the sheet; a human
reviews an overlay and answers a short selections form.

## The metric (replaces the 98% gate)

**Answered fraction at zero false positives.** Not "98% accurate on everything."

A wrong quantity that looks right is worse than a blank — Jason would bid it. The system
already has the rare property of never emitting a confident wrong number: all 10 graded
houses terminate `more_information_required` with **zero false positives**. That property is
the product. Grow what it answers without ever losing it.

| | Today |
|---|---|
| Answered fraction | **0.3%** (8 of 2,880) |
| False positives | **0** |
| Reference: Handoff H1 (state of the art) | 81.6% |
| Reference: experienced human estimator | 77–78% |

98% remains the long-term goal. It is not the gate, and nobody in the industry is there.

---

## Where the pipeline actually breaks

Verified 2026-08-03 against the release contract (18 of 29 gates pass):

```
pages identified + roles verified        DONE   (certified)
schedules masked on mixed pages          DONE   (certified)
linework extracted                       DONE   304,106 segments / 82 regions
scale verified                           DONE   51 regions, all deterministic
  -------------------------------------- BREAK HERE --------------------------------------
field observation (what IS this?)        OFF    624 requests staged, 552 fail-closed,
                                                0 model calls, paidApiCallLimit = 0
cross-drawing reconciliation             MISSING  not one function exists
measurement ledgers                      0 of 7
predictions / scope / estimate           blocked downstream
```

Two of the three layers a takeoff needs are built. Borrowing Handoff's own framing —
*text, objects, cross-drawing connectivity*:

| Layer | Status |
|---|---|
| **Text** — tags, schedules, dimensions, callouts | DONE |
| **Objects** — what is this symbol / region | **gated off at zero** |
| **Cross-drawing connectivity** — same object across sheets | **does not exist** |

## The shape of the sheet (measured, not assumed)

- 230 measurable rows; 288 registry fields (230 template + 58 extension)
- Per house: ~186 scoreable targets — **~69 positive, ~118 explicit zeros (63%)**
- **~62% of rows are room-scoped** (Kitchen, Baths 1–4, Game Room, Laundry, Common, Bedrooms)
- Ground truth: 10 houses, 690 positive truths, 1,167 explicit zeros, all Buildern-shaped
- Grader covers **42.85%** of the registry; 58 fields have no truth anywhere in the cohort

Four classes of row, only one of which is "measure it off the plan":

| Class | Count | Source |
|---|---|---|
| Geometry — area / linear / vertical / roof | 130 | trace + verified scale |
| Counts | 84 | perception + reconciliation |
| **Selections** — wood vs iron door, granite vs quartz, tile vs LVP | 11+ groups | **human; plan cannot say** |
| **Not in the plan set** — silt fence, driveway, well, septic, duration | ~14 | **site plan or intake** |

---

## Phases, in dependency order

Status: ⬜ not started · 🔨 in progress · ✅ done

### 🔨 Phase 0 — Make progress visible
Nothing can be steered until it can be measured. The old scorer reports 0% against a 98%
gate, so every improvement looks identical to no improvement.

- ✅ `estimator_accuracy/coverage.py` — **answered fraction at zero false positives**, per
  house, split positive vs proven-zero. Wired into `python jj.py verify`.
- ✅ **Baseline recorded 2026-08-03: 0.3% answered (8 of 2,880), 0 false positives, and
  zero proven absences in any of the ten houses** — the 63% of the sheet that is zeros has
  never been touched.
- ⬜ Separate **"differs from Jason"** from **"is wrong"** — Jason's Inputs-block truth comes
  off the printed SQFT schedule, so a traced 5,529.8 against his 5,529 scores as an error
  today. Ruling 2026-08-03: **measurement is the authority, schedule is the cross-check.**
  Not urgent while the engine answers nothing; **must land with Phase 1**, or the first real
  measurements get graded as failures and we train the engine to copy the schedule.

**Exit:** coverage curve in `verify` ✅; schedule-vs-measured scoring split ⬜.

### ⬜ Phase 1 — Switch on perception, with a hard cost cap
The 552 fail-closed requests are the single biggest unlock in the plan. Plumbing is built and
certified — 624 requests staged and validated. Only the model calls are gated at zero.

- **Model identifies and locates. It never emits a quantity.** Geometry comes from the
  304,106 already-extracted segments against verified scale. Determinism is preserved where
  it matters.
- Explicit call cap **and** USD cap before any spend (`v3_model_pricing.json` expired
  2026-07-25 — re-price first)
- Start on PR-072 only, measure cost per house, then widen

**Exit:** answered fraction rises materially on PR-072 at **zero false positives**; cost per
house recorded. **Blocked on Jason authorising paid calls + a cap.**

### ⬜ Phase 2 — Structural determination → the zeros
63% of the sheet is proving absence, and zeros are the false-positive check set — getting
them right is what proves the engine doesn't hallucinate. They cascade: no basement kills ~5
rows, no metal roof 8, two baths instead of four ~44, no game room ~12, no fireplace ~5.

- ~15–20 structural calls, each producing a `zero_review` artifact proving the sheets were
  searched (a blank fails coverage; a proven zero passes)

**Exit:** explicit-zero targets correct across all 7 measurement-eligible houses, 0 FP.

### ⬜ Phase 3 — Cross-drawing connectivity
The missing layer, and the one that makes the system self-checking. An object exists once and
appears in several views; those views must agree. A flat list of 279 numbers cannot catch its
own errors — a building model can.

First target is **openings**, because we know the answer: L J Show returned 22 from plan tags
and 46 from elevations, both functions working correctly, nothing to reconcile them.

- Reconciliation constraints: room areas sum to heated SF · roof footprint × pitch factor =
  roof surface · wall perimeter × ceiling height = wall area · every opening appears in plan
  **and** elevation

**Exit:** openings reconcile to 46 on L J Show with evidence from both views, and reconcile
across the 7 graded houses. **Needs a ruling from Jason on what "reconciled" means.**

### ⬜ Phase 4 — Room identification and scoping
Blocks ~62% of the sheet's rows. The dangerous failure mode: every quantity correct, every
line wrong, and the estimate total still looks right.

**Resolved 2026-08-03 — there is no numbering rule to learn.** Jason: plans routinely label
three bathrooms all "BATH" and three bedrooms all "BEDROOM". The physical-room → sheet-row
assignment is arbitrary and differs on every plan set, so asking him for his convention was
the wrong question.

The fix is to stop scoring on it:

- **Assign deterministically** by a stated rule (same input → same assignment, every run)
- **Score permutation-invariantly within a room class** — compare the *set* of bath-vectors
  against the set of truth bath-vectors, not bath-by-bath. An arbitrary permutation is not
  an error and must not be counted as one.
- Verified 2026-08-03: Baths 2/3/4 carry the **same item set** (vanity, sink, granite, valve,
  pan, mud bed, surround, tile walls, niche, bench, glass), only reordered — 21/21/20 rows.
  So a permutation among them is genuinely neutral. **"Full Bath 1" is different (22 rows)**
  and reads as the primary suite, so it is identified on its own merits, not by ordering.

**Exit:** rooms identified, deterministically assigned, and scored permutation-invariantly
across all 7 houses.

### ⬜ Phase 5 — Geometry and counts
The ~69 positive quantities per house. Order within the phase by dollar weight, not by row
order. Known-hard: cabinet LF by type, masonry SF (−49% on L J Show), beam wrap LF (121 vs
291), interior bearing lines for footer LF (no framing plan = no bearing lines).

**Exit:** answered fraction hits the agreed target at 0 FP.

### ⬜ Phase 6 — Selections + intake form
What turns a partly-filled sheet into a shippable one. ~11 selection groups the plan cannot
answer, plus ~14 rows needing a site plan or Jason's input.

**Exit:** the sheet is 100% populated — every row measured, declared, or explicitly flagged.
Nothing blank.

### ⬜ Phase 7 — Review artifact + Buildern export
- Marked-up drawing set showing what was detected where — the thing that makes "without
  error" checkable in minutes instead of by redoing the takeoff
- Export in Buildern measurement-sheet format

**Exit:** Skip reviews a house in under 30 minutes and imports it.

### ⬜ Phase 8 — Prospective holdout
The prospective registry is empty (0 of 10 registered). Everything above is historical replay,
which the contract itself flags as *not a strict holdout*.

**Exit:** coverage holds on houses never used during development.

---

## Decisions owed by Jason

| # | Decision | Blocks | Status |
|---|---|---|---|
| 1 | Paid vision calls | Phase 1 | ✅ **approved 2026-08-03, per-run: quote the cost, get approval, then spend** |
| 2 | Room numbering rule | Phase 4 | ✅ resolved — no rule exists; score permutation-invariantly instead |
| 3 | **What "reconciled" means** for an object across views | Phase 3 | ⬜ owed |
| 4 | **Selections** — short form, infer from finish schedule, or flag? | Phase 6 | ⬜ owed |
| 5 | The other ~18 Buildern measurement sheets | grader ceiling (42.85%) | ⬜ owed |

**Spend protocol (Jason, 2026-08-03):** never spend without quoting the amount first and
getting an explicit yes. No open-ended API budgets. Price each run before it happens, start
on one house, measure actual cost, then widen.

## Settled — do not relitigate

- **Measurement is the authority; the printed schedule is a cross-check** (2026-08-03)
- **Never wrong beats always answers.** Fail-closed is the product, not a limitation
- **98% is the destination, not the gate** — H1 is at 81.6%, humans at 77–78%
- **Models perceive; geometry measures.** No quantity ever originates from a model
- **Don't buy Handoff H1** — $719/mo billed annually, and the result wouldn't change the plan
- Structural *layout* (bearing lines, beams, posts) is in scope; member *schedules*
  (sizes, species, grades) are out until something consumes them
