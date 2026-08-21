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

## Waiting on you

- Ratify list: overnight commits are all additive tools/docs — no engine files
  touched, gates untouched. (8/14 backlog `todo_takeoff_engine_ratify_0814`
  still open.)
- Rulings queued: outer-face loop emission (engine); Watkins notation sample.
