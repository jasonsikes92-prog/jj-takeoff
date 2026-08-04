# v1 × OpenTakeoff — Evaluation

**Run:** 2026-08-04 · **Scope:** the handoff brief "ESTIMATING PROGRAM v1 × OPENTAKEOFF × LEVEL GROUND"
**Method:** every claim below is either MEASURED (I ran it today, command shown) or READ (I read the file, path shown). Nothing here is inferred from the handoff brief.

---

## 0. Headline

**The brief's premise does not survive contact with the disk.** Three corrections, in order of how much they change the decision:

1. **"v1" is two programs, not one, and they are in opposite health.** One is green and shipping; one is stuck at 0.3%. Forking away from "v1" would throw out the working one.
2. **The Level Ground report engine is already built, tested, and wired** — pre-bid report, market pricing, builder-bid ingestion, and bid-gap findings all live in `jnj_takeoff.py` and pass self-tests. The brief lists these as things to build.
3. **On 1 of the 6 golden plan sets, trusting the printed scale note is wrong by −14.5% on area, silently — and nothing on the sheet tells you which set you are on.** I measured this across all six houses. It is the most decision-relevant finding in this document, and it inverts the fork recommendation.

**Recommendation: do not fork OpenTakeoff as the base. Adopt three parts of it into v1-supervised.** Detail in [FORK_PLAN.md](FORK_PLAN.md).

---

## 1. What is actually on disk

The brief's Phase A step 0 says the v1 code may be missing and to stop and ask. It is not missing. It is in two places.

### 1a. v1-SUPERVISED — `C:\Users\jason\.claude\skills\jnj-estimate-takeoff\`

| | |
|---|---|
| Engine | `tools/jnj_takeoff.py` — **5,626 lines**, ~150 functions |
| Method ledger | `reference/calibration.md` — **1,619 lines, 63 numbered data points** |
| Golden corpus | 6 houses with `plan.pdf` + `expected.yaml` (burns, holbrook, lankford, pack, peterson, roberts, wilson) |
| Rate book | `reference/rate_book.json`, `templates/estimate-template.xlsx` |

**MEASURED today — `python tools/tests/run_golden.py`:**
```
houses graded : 6   houses green : 6
asserts graded: 22   PASS 22   FAIL 0
comparison checks: 13   PASS 13   FAIL 0
known-gaps: 0    skipped/needs-plan: 0    errors: 0
worst delta: holbrook slab_area_sf +1.7%
```

**MEASURED today — `python tools/jnj_takeoff.py`:** `ALL PASS` (~25 inline assertions, each pinned to a real Jason/vendor number).

This engine produced the complete 253-line L J Show estimate and matched Jason's own hand takeoff at **0.0%** on under-roof framing SF, porch ceiling SF, and electrical SF. **This is not a failing program.** Its known misses (windows 22 vs 46, masonry −49%) already have fixes written and self-tested; they are un-applied, not un-solved.

### 1b. v1-AUTONOMOUS — `C:\Users\jason\OneDrive\Desktop\Claude\estimator_accuracy\`

| | |
|---|---|
| Size | 233 `.mjs` + 30 `.py` = **66,378 lines** in root scripts alone |
| Corpus | 10 registered jobs, `PR-053 … PR-105` |
| Ground truth | `private/measurement_truth_v3.json` — 2,047 source rows, **690 positive**, **1,167 explicit zeros**, sha256-bound to each plan |

**MEASURED today — `python estimator_accuracy/coverage.py`:**
```
answered            8 of 2880  (0.3%)
false positives     0   <-- THE CONSTRAINT
all 10 jobs terminal: more_information_required
```

**This is the program that is stuck.** But read why it is stuck before concluding the code is bad:

| Layer | State |
|---|---|
| Text — tags, schedules, dimensions | DONE, certified |
| Linework + scale | DONE — 304,106 segments, 51 regions, all deterministic |
| **Objects — "what is this symbol?"** | **gated at zero model calls by policy** (624 requests staged, 552 fail-closed) |
| **Cross-drawing connectivity** | **does not exist** |

It answers nothing because perception was switched off pending a spend decision, and because the reconciliation layer was never written. Neither is a bad-rules problem. `ROADMAP.md` already diagnoses this correctly.

### 1c. LEVEL GROUND — already a product, not artifacts

| Where | What |
|---|---|
| `Desktop\Level Ground\site\` | Deployed Vercel site, getlevelground.com, live API routes, Stripe checkout wired (test mode pending live activation) |
| `Desktop\Level Ground\lg_report_template.html` | The one report template; `gen_reports.py` regenerates both samples from it |
| `jnj_takeoff.py:4461-4944` | **The report engine itself** |
| `estimator_accuracy\LEVEL_GROUND_BRIDGE_CONTRACT_V1.md` | Privacy contract — the bridge strips J&J identity, rates, costs, markup, vendor and QBO data before anything reaches a homeowner |

**MEASURED today, from the engine self-test:**
```
OK  report_from_takeoff pre-bid: 2 qty, 8 checklist findings, bid hidden, not-measured surfaced
OK  price_report tiers: Middle-GA calibrated $704,000-880,000; Seattle regional x1.23; Nowheresville uncalibrated
OK  findings_from_bid: 6 findings (4 missing, 1 mispriced, 1 vague-lump); bid_gap $587,400
```

The brief's proposed milestones (d) "Level Ground risk-report generator" and (e) "bid ingestion + bid-vs-scope gap report" are **done**. `PRE_BID_SCOPE_CHECKLIST` (8 entries) is the advocacy IP — the scopes builders most often omit, each with a dollar band and the question the homeowner should ask. `MARKET_RATE_BOOK` correctly refuses to price an uncalibrated market rather than silently applying Middle-GA rates.

---

## 2. OpenTakeoff — verified against current `main`

Cloned `ab8895f`, **2026-08-04** (same day). Apache-2.0 confirmed. Very much alive.

**Verified true from the brief §4:** 38 MCP tools (I enumerated all 38); `oneclick.ts` is huge (176 KB); `scheduleParse.ts`/`scheduleScan.ts` token-based and OCR-shareable; `confidence.ts` documents that 1.0 means "nothing to flag," never "verified"; `server/adapters/base.py` is a clean pluggable AI socket; withhold-and-flag doctrine is real and consistently applied.

**Corrections to the brief §4:**

| Brief says | Actually |
|---|---|
| `server/adapters/ollama.py` exists | It does not. Only `base.py` + `heuristic.py`. Ollama is named as an *example* in a docstring |
| 3 AI endpoints | **4** — `/ai/suggest-scale`, `/ai/detect-rooms`, `/ai/classify-finish`, **`/ai/parse-schedule`** (VLM path for scanned schedule tables) |
| ~38.6K lines | web/src 20,216 + mcp/src 5,405 + server 415 ≈ **26K** in the parts that matter |
| "lacks full-construction-set sheet classification" | Half right. `sheetgraph.ts:68 classifySheetRole()` **exists** with regex signals + confidence + evidence. The *taxonomy* is short: `plan/schedule/legend/detail/elevation/demolition/unknown`. Extending it is a config change, not a build |

**Additional findings the brief does not mention:**
- **102 of its own test files** (excluding vendored). Genuinely well-tested.
- `docs/ESTIMATING_ROADMAP.md` — upstream **plans** a unit-cost estimate worksheet + material kits + proposals. Generic, not 18-division. It will not converge on J&J's needs, but it also will not conflict.
- `mcp/src/scalewarn.ts` — a mixed-scale guard. **It cannot catch the failure in §3** (see below).
- The AI sandbox fails closed: `/ai/*` returns 401 when `OT_SANDBOX_API_KEY` is unset, never open-because-unconfigured.

---

## 3. BENCH — the decisive measurement

**Job:** Roberts Residence (PR-051), the real 12-sheet vector set in the golden corpus.
**Test:** give both engines the same PDF and ask each what the scale is.

### 3a. Scale

| Sheet | OpenTakeoff `detected_scale` (title-block note) | implied pt/ft | v1 `calibrate_scale` (dimension-string regression) | votes |
|---|---|---|---|---|
| p4 | `1/4" = 1'-0"` | 18.000 | **16.646** | 86 |
| p5 | `1/4" = 1'-0"` | 18.000 | **16.714** | 187 |
| p6 | `3/16" = 1'-0"` | 13.500 | **12.506** | 114 |
| p7 | `1/4" = 1'-0"` | 18.000 | **16.549** | — |

The set is **printed at ~92.5% of nominal**. The ratios agree across sheets independently (0.9248, 0.9285, 0.9264, 0.9194) — a uniform print reduction, not noise. On p5 the 187 votes cluster tightly with the mode dead on 16.6717.

The fixture file said so all along, in a line written before this evaluation existed:

> `scale_note: "p4 detect_scale ppf=16.714 (187 votes) — NONSTANDARD (print-rescaled set); per-page dim-voting required, never assume 18.0"`

### 3b. What that costs, measured

I drove OpenTakeoff's MCP to trace rooms on p5, then measured **the identical traces** at both scales:

```
seed(px)        area @ OT-detected   area @ v1-measured    delta
(1800, 900)        101.5 SF            117.8 SF          -13.8%
(1800,1200)        101.5 SF            117.8 SF          -13.8%
(1800,1800)        142.1 SF            164.8 SF          -13.8%
(1800,2100)        142.1 SF            164.8 SF          -13.8%
------------------------------------------------------------------
TOTAL              487.3 SF            565.2 SF          -13.8%
```

The delta is **exactly** `(16.714/18)² = 0.862` on every trace, which is the proof that the bench isolates the scale decision and nothing else.

**Direction matters: trusting the title block UNDER-states.** Every square foot, every linear foot (−7.1%), on every sheet. Roberts was a $591,341 signed contract; if SF-driven direct cost is ~60% of that, a 13.8% area shortfall is roughly **$45–50K of scope you did not bid**. You would find out on site.

### 3c. Is this fair to OpenTakeoff?

Mostly. Three mitigations, none sufficient:

- **It does not auto-apply.** `sheet_info` reported `scale_set: false`, and `set_scale`'s own description says *"The detected scale is never applied automatically."* Honest design. But it offers `use_detected: true` as one of four options, and on a set whose title block confidently says `1/4"`, that is the option an operator or an agent takes.
- **`set_scale {calibrate: {p1, p2, feet}}` exists.** The mechanism is there. It requires the operator to already suspect the sheet is rescaled — which is exactly the knowledge v1 encodes and OpenTakeoff does not.
- **`scalewarn.ts` cannot fire here.** It warns only when a scale note *disagrees with the adopted scale*. On this set the note and the adopted scale agree perfectly with each other. Both are wrong versus the paper. The guard is built for enlarged detail viewports, not for a set printed to fit.

**The gap is not that OpenTakeoff lacks a calibrate button. It is that it treats the printed note as evidence, and v1 treats it as a claim to be tested.** On this set, v1 is right and the note is wrong.

### 3e. Does it generalise? — the sweep across all 6 golden houses

I ran `calibrate_scale()` on every page of every golden plan set and compared each result to its nearest standard scale. **28 pages cleared 25 votes.** The answer is more nuanced than Roberts alone suggests, and it is worth stating precisely:

| House | pages >2% off nominal | pattern |
|---|---|---|
| **roberts** | **4 of 4** | **uniform ~0.925 across all four, 36–187 votes — the whole set is rescaled** |
| holbrook | 2 of 5 | isolated: p3 +2.5% (143 votes), p17 +10.6% (25 votes) |
| pack | 1 of 5 | isolated: p5 +11.2% (53 votes) |
| wilson | 3 of 10 | isolated: p2 −13.5% (42), p10 −3.1% (37), p12 +6.9% (36) |
| burns | 1 of 4 | isolated: p4 −5.7% (26 votes) |
| lankford | — | no page cleared the vote threshold |

**Two distinct phenomena, and they need different responses:**

1. **Whole-set print rescaling — rare but catastrophic.** Roberts only, 1 of 6 houses. All four well-supported pages agree on the same ~0.925 ratio. Costs **−14.5% on every area in the set**. Nothing in the PDF discloses it.
2. **Mixed or nonstandard scales on individual sheets — common but contained.** 11 of 28 pages across 5 houses. Note the discriminator: **every isolated off-nominal page has low vote support (25–53), while every high-vote page (100–506 votes) lands on nominal within 0.5%.** These read as detail/section sheets carrying their own scale — which is exactly the case OpenTakeoff's `scalewarn.ts` *is* built to catch.

**What this does to the recommendation: nothing, and here is the honest reason.** OpenTakeoff would get 5 of 6 of these houses right. But you cannot know in advance that you are not on Roberts — the title block on a rescaled set looks identical to the title block on a true one. A 1-in-6 chance of a silent −14.5% on a $591,341 contract is not a risk profile a bid-grade tool can carry, and the only way to retire it is to do the regression on every set. That is precisely what `calibrate_scale()` is for.

**Correction to my own framing:** my first pass implied print-rescaling was the norm on Jason's plans. It is not — it is roughly 1 in 6. The finding is not "OpenTakeoff's scale detection is broken"; it is "OpenTakeoff's scale detection has no way to know when it is wrong, and v1 does."

*(Caveat on the per-house means in the raw sweep output: averaging ratios across pages of very different vote support is not meaningful for the isolated-page houses. The per-page table above is the reliable read.)*

### 3d. What OpenTakeoff did well on the same file

Load and parse were clean and fast: 12 sheets, correct page geometry, `seg_count: 1238` on p1, `has_vector_linework: true`, scale notes found on 7 of 12 sheets. The flood tracer produced plausible, repeatable room rings from bare seed coordinates with zero configuration. Its ingestion and tracing are good. Its **measurement authority** is the problem.

---

## 4. Capability matrix

Legend — **KEEP**: v1 wins, port it · **REPLACE**: OpenTakeoff wins · **BUILD**: neither has it · **DROP**: nobody needs it

| # | Capability | v1 | OpenTakeoff | Verdict |
|---|---|---|---|---|
| 1 | PDF/vector ingestion | PyMuPDF, works, no UI | Cleaner, pdf.js, sheet keys, multi-file merge, journaled | **REPLACE** |
| 2 | Raster / scanned plans | OCR path (`ocr_words`, `read_sqft_schedule_ocr`), tesseract-dependent | `rastermask.ts` — Bradley-Roth adaptive threshold, polarity check, binary closing; same tracer runs on scans | **REPLACE** |
| 3 | Sheet identification | `SheetLedger` forcing function (blocks "no roof plan" from a partial look) + deterministic page roles in `estimator_accuracy` | `classifySheetRole()` — good machinery, short taxonomy | **REPLACE the machinery, KEEP the SheetLedger discipline, BUILD the residential taxonomy** |
| 4 | **Scale detection** | **Per-page regression over printed dimension strings, 86–187 votes, never trusts the note** | Reads the title-block note | **KEEP — decisively. §3** |
| 5 | Dimension-string reading | `parse_dim`, `read_dimension_chains`, `overall_dims`; handles dimension lines broken around centered text | Essentially absent — one comment in `detectRooms.ts` | **KEEP** |
| 6 | Area measurement | `trace_footprint` converged to 0.6% across 3 sheets; `trace_footprint_clean` unreliable on dashed linework | Sealed flood + contour trace + vertex snapping, gap-seal disclosure, door wedges, min-passage rule | **REPLACE** |
| 7 | Linear measurement | `measure_wall_lf`, `footer_lf`, `beam_wrap_lf`, roof-line classification w/ topology refinement | `measure_line`, generic | **KEEP** (v1's are trade-semantic, not just geometric) |
| 8 | Symbol / fixture counting | `window_count`, `recessed_can_count`, `interior_door_count`, `parse_opening_tag` (J&J's WWHH tag encoding) | `symbol_sweep` — deterministic, vector-linework matching, reports near-misses | **REPLACE the mechanism, KEEP the J&J tag semantics** |
| 9 | Schedule extraction | `read_sqft_schedule`, `read_sqft_schedule_ocr` | `scheduleParse`/`scheduleScan` — token-based, one parser for vector + OCR | **REPLACE, then BUILD window/door schedule semantics** |
| 10 | Cross-sheet reconciliation | Four functions: `elevation_opening_count` (plan vs elevation, `ok=False` on >20% divergence), `reconcile_roof_footprint`, `cladding_completeness`, `certify_area_measurements` | None | **KEEP the four, BUILD the rest** — this is still the missing layer in both |
| 11 | Confidence / provenance | `Quantity` class, `certify()`, `certify_explicit_scale`, MEASURED/ASSUMED tagging, fail-closed terminals | `confidence.ts` — 0–1 with named factors, per-shape `origin`, journaled edits, honest about what 1.0 means | **REPLACE the scoring, KEEP the certification gates** |
| 12 | Estimate output | 18-division Buildern import, per-line markup, `lint_buildern_descriptions()` at 0 | Nothing. Upstream roadmap plans a generic worksheet | **KEEP** |
| 13 | Level Ground mode | Built + tested: pre-bid report, market pricing w/ uncalibrated-market refusal, bid ingestion, gap findings, privacy bridge | Nothing, deliberately — "no estimate, pricing, risk, or scope surface here" | **KEEP** |
| 14 | Verification UX | **None.** Static PNG overlays | Interactive canvas, `view_sheet {overlay}`, `mark_verdict`, `edit_shape`, RFI, marked-PDF export | **REPLACE — this is OpenTakeoff's biggest genuine contribution** |
| 15 | Agent interface | Python functions called ad hoc | 38 MCP tools, journaled, provenance on every edit, `undo_last` | **REPLACE** |
| 16 | Test coverage | 6-house golden suite + ~25 inline asserts + `coverage.py` | 102 test files | **KEEP both** — different jobs. v1's grade against *real ground truth*; OpenTakeoff's are unit tests |
| 17 | License | Private | Apache-2.0, `NOTICE`, `THIRD-PARTY-NOTICES.md` | Clean either way |
| 18 | The calibration ledger | **63 numbered data points, many closed-loop cold tests graded against QBO actuals** | N/A | **KEEP — irreplaceable** |
| 19 | v1-autonomous's 66K-line orchestration layer | 0.3% answered after months | N/A | **DROP as a build target, KEEP the corpus + truth + grader** |

---

## 5. Stays / goes ledger (supersedes the brief §6)

### Stays — non-negotiable
- **The 10-job corpus and `measurement_truth_v3.json`.** 690 positive truths, 1,167 explicit zeros, sha256-bound. The most valuable asset in this entire picture and it exists nowhere else.
- **`calibration.md`, all 63 data points.** The brief proposes writing `LESSONS_FROM_V1.md` by extracting bad rules. That file already exists and is better than what the extraction would produce.
- **v1's scale + dimension modules.** §3 is the proof.
- **The Level Ground engine and privacy bridge.**
- **18-division template, markup structure, `lint_buildern_descriptions()`.**
- **`coverage.py`'s metric** — answered fraction at zero false positives. Correct metric, correctly chosen.
- **The four reconciliation/certification functions.**
- OpenTakeoff's tracer, MCP layer, schedule parser, symbol sweep, raster path, confidence model, verification canvas.

### Goes
- **v1-autonomous as a build target.** Not the code — the *ambition*. 66,378 lines chasing full autonomy produced 0.3%. The supervised path already prices houses. Stop funding the race and harvest what it built: the corpus, the truth file, the grader, the page-role work, the linework extraction.
- **`trace_footprint_clean` / `trace_enclosed_region`** — documented unreliable on dashed linework (returned 80–99 SF for a 5,500 SF building). Superseded by OpenTakeoff's tracer.
- **`roof_zone_surface()`** — solved ppf 19.94 against a verified 18.00 and left 61% unassigned.
- **Static PNG overlay review.** Replaced by the interactive canvas.

### Undecided — needs Jason
- Whether Level Ground runs on a forked OpenTakeoff canvas (homeowners upload plans, client-side, never leaves the browser — which also answers the copyright/ToS concern in the brief §7) or stays server-side.
- Whether the 10-job corpus becomes the fork's eval harness or stays in `estimator_accuracy`.

---

## 6. What the brief got right

Worth stating plainly, because most of it holds:

- **The eval-harness-first mandate.** Correct, and already satisfied — v1 has three harnesses (`run_golden.py`, `_verify_selftest()`, `coverage.py`) and `jj.py verify` runs all five gates in one command.
- **Measured vs purchased quantity must be separated.** Correct and live: HANDOFF §5 records *"His takeoff quantities are RAW with waste in a separate column. Compare raw-to-raw."*
- **Actuals ≠ plan quantities.** Correct. `calibration.md` uses actuals for the variance layer, estimates for takeoff accuracy.
- **Holdouts.** Correct and currently violated — `ROADMAP.md` Phase 8 records the prospective registry is empty (0 of 10 registered); everything to date is historical replay.
- **The trust trap** — "a tool that can't show *which* numbers to distrust saves zero time. Verification UX is the product." This is the strongest line in the brief and it is exactly why OpenTakeoff is worth adopting. Just not as the base.
- **Printed dimensions are truth; pixels are a cross-check.** §3 is this rule, measured.

---

## 7. Risks I am flagging rather than solving

- ~~**Roberts is one set.**~~ **Closed — §3e.** Swept all 6 houses, 28 well-supported pages. Whole-set rescaling is 1 in 6, not the norm; isolated mixed-scale sheets are common. The recommendation survives, but the claim is narrower than my first pass stated.
- **The vote-count discriminator is an inference, not a proven rule.** I observed that isolated off-nominal pages all have low vote support and high-vote pages sit on nominal — which reads as detail/section sheets with their own scale. I did not open those pages to confirm. Worth 30 minutes before relying on it as a heuristic.
- **The corpus is not a holdout.** Six golden houses were used during development. `coverage.py`'s 0.3% is honest; the golden suite's 6/6 green is not independent accuracy evidence, and the fixture files say so in their own comments (`window_trim_lf`: *"NOT independent accuracy evidence, because the expected value is derived from the same tags the probe reads"*).
- **OpenTakeoff is one maintainer's project** moving fast (commit the same day I cloned it). Adopting its MCP layer means tracking a moving upstream. Apache-2.0 makes a hard fork legal at any time; the cost is that you stop getting the improvements.
- **Level Ground's Stripe is still in test mode** per its own TODO — a real customer cannot pay today. Unrelated to this evaluation, but it is the actual launch blocker, not the report engine.
- **`jj.py save` commits on every run** (`BACKUP_MANIFEST.json` gets a fresh timestamp), so git history has noise. Pre-existing, noted in HANDOFF §2.

---

## 8. Reproducing this evaluation

```bash
python C:/Users/jason/.claude/skills/jnj-estimate-takeoff/tools/tests/run_golden.py
```
```bash
python C:/Users/jason/.claude/skills/jnj-estimate-takeoff/tools/jnj_takeoff.py
```
```bash
python C:/Users/jason/OneDrive/Desktop/Claude/estimator_accuracy/coverage.py
```

The two bench scripts are in this session's scratchpad (`bench_ot.mjs`, `bench_area.mjs`). They need OpenTakeoff cloned with `npm install` in `mcp/` **and** `npm install --no-save pdfjs-dist pdf-lib zod @napi-rs/canvas` at the repo root — the MCP server imports from `web/src/lib`, so Node resolves those deps from the repo root, not from `mcp/node_modules`. Say the word and I will move them somewhere permanent.
