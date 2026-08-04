# Template Gap Memo — Jason's Measurement Sheet + Estimate Template
_Audit date: 2026-07-05 · Files: "Measurements - Newest template 12_8_2025 (3).xlsx" (257 rows) +
"Newest template 12_8_2025 - Estimate Items (3).xlsx" (691 rows). Both fully enumerated (every row
read). Cross-referenced against reference/calibration.md decoded rates + documented misses._

**Verified:** every row of both sheets. **Not checked:** none (full enumeration).

---

## A. MISSING SCOPES (highest $ risk — no line on either sheet)

| # | Missing | Evidence it costs money | Suggested fix |
|---|---------|------------------------|---------------|
| A1 | **Laundry room — entire section absent** (no cabinets/counter/sink/tile) | Cal #35: laundry + BOTH garages get tops (Pack miss) | Add Laundry section: lowers LF, counter SF (L1 $35), sink EA, flooring SF |
| A2 | **Column wraps as EACH** — only "Ext beam wrap" LF exists (meas row 110) | 3-way wood-wrap split: beam=LF ($11 Hardie/$23 cedar), column=EACH ($270 6×6/$480 12×12), bracket=EACH. Wilson: 21 columns = $8,820 hiding in a LF line | Add "Column Wrap 6x6 EA" + "12x12 EA"; keep beam-wrap LF for true horizontal beams only |
| A3 | **Stone veneer — no measurement line** (only Brick Veneer, row 106; estimate HAS stone rows 238–240 with nothing to feed them) | Pack: 70/30 brick-stone split, measured per elevation | Add "Stone Veneer Ext ft2 (10% waste)" |
| A4 | **Spray-foam insulation — no line** (walls $1.25 / roof $0.85 are batt rates) | J&J default = foam roof + batt walls; Pack budget priced foam at batt rate (documented catch); foam AREA = roof surface | Add "Spray Foam Roof ft2 @ foam rate"; keep batt lines as the wall option |
| A5 | **Crawlspace encapsulation — no line** | Standing rule: crawl → assume encapsulation | Add line (crawl floor SF + walls, or flat) |
| A6 | **Punch-out labor — no line** | Documented ZERO-TRAP (landscaping ✓, dumpsters ✓ are covered — punch-out is not) | Add allowance line |
| A7 | **Flashing / water table** | $3.50/LF brick-to-siding transition; missed once before (documented "never omit") | Add LF line |
| A8 | **Band board** | 5/4×12 between-floor band $7.50/LF | Add LF line |
| A9 | **Exterior crown / cornice** | Leone: 680 LF @ $6.50 = $4,420 = 11% of the siding job | Add LF line |
| A10 | **Ceiling heights — no input anywhere** (base or vaulted) | Drives drywall/paint/trim/framing/wall-insul; Pack: uniform-height assumption ran drywall 11% low | Add "Base ceiling height" + "Vaulted rooms (room, height)" inputs |
| A11 | **# HVAC systems — no input** (estimate prices $7,500/each with no count carrier) | Sizing rule: 1 ton/800 SF, max 5 t/unit | Add count input; engine computes from heated SF, confirm at intake |
| A12 | **Closet shelving beyond pantry** (bedrooms/master have none; code 20.05 used only for pantry) | Every house has closets | Add "Closet shelving LF" |
| A13 | **Screened porch input** — estimate row 658 ($140/LF) has no measurement line | — | Add LF input |
| A14 | Minor / ask-at-intake: mudroom built-ins, shiplap/accent walls (group title says "Wall Coverings" but no line), wood-floor option per room (estimate supports it, sheet can't feed it), carpet (absent from both), egress window wells, blower-door/HERS test (GA code — confirm if HVAC sub includes), steel/LVL beam line, exterior light-fixture allowance | — | Add as optional lines or intake questions |

## B. MECHANICAL ERRORS (units / cost types / copy artifacts)

**Estimate — unit errors (each↔ft2 copy-paste):**
rows 152–153 attic doors $600/$900 "ft2"→each · 154 door knobs $25 ft2→each · 155 door stops ft2→each ·
156 hardware install ft2→each · 172 treads&risers $35 "ft2" (basis? per-tread?) · 196 HVAC-garage $6,500
"sq ft"→each · 201 400A upgrade $2,000 "ft2"→each · 202 permanent power $6 "each"→ft (meas sheet says
LF from pole) · 209/210 insulation floors/walls "each"→ft2 · 220 1x4 window trim $5 "ft2"→LF ·
221 corner boards $4.60 "ft2"→LF · 224 gable brackets $250 "ft2"→each (and classify by type — decoded
range $105–925 is 9×) · 225 frieze $3 "ft2"→LF · 629 frameless enclosure $55 "each"→ft2 ·
635/638–644 garage doors+openers "ft2"→each · 656 deck railing material $45 "ft2"→LF ·
660 final grading $2,500 "ft2"→each · 619/647/650 formula-residue rates ($11.1036, $21.4319,
$143.289) — round them.

**Estimate — cost-type drift (drives wrong markup %):**
row 180 trim labor typed MATERIAL · 288 wood-flooring labor typed MATERIAL · 387 vanity install Bath 2
typed MATERIAL (Bath 1's twin is SUBCONTRACTOR) · 654 deck labor typed MATERIAL · 657 deck-railing labor
typed ALLOWANCE · 173 tread labor typed ALLOWANCE. Many ALLOWANCE rows carry 15% markup instead of the
confirmed 8% (e.g. 38, 154, 165, 243–252, 291–297…) — see Question D3.

**Estimate — cost-code miscodes:** rows 175/176 stair landing/bullnose coded 15 (LVP) → 12 (trim carpentry).

**Estimate — template hygiene:** leftover job data — row 26 grubbing qty=1 ($1,800), row 72 sleeves qty=3;
summary total shows $3,164.52 (a clean template should be $0). Row 624 exterior-paint description says
"siding will be metal" (previous-job leftover). Rows 651/663 are "―" placeholders.

**Measurement sheet — artifacts:**
- Baths 2/3/4 "Freestanding Tub" rows 190/212/233: unit **ft2/Area** → should be Count (Bath 1 is correct).
- Rows 119/135/145 "LF of Uppers at Ceiling": name says LF, unit says ft2 — pick one (recommend LF).
- "(copy 1)(copy 1)…" names throughout Baths 2–4 — rename per room; fragile for automation and humans.

## C. RATE STALENESS vs decoded/locked actuals (template dated 12/8/2025 — 7 months old)

| Line | Template | Calibrated actual | Delta |
|------|----------|------------------|-------|
| Framing lumber | $8/SF | volatile $13–16/SF under-roof | **LOW — biggest single exposure** |
| Framing labor | $5.50/SF | $6.50/SF locked on 3 actuals | LOW |
| Plumbing | $800/fixture + $400/water, no base | locked sub: $8,000 base + $450/fixture + $400/half | LOW + wrong shape (12-fix house: $9.6k vs $13.4k) |
| Lap siding | $2.50/SF ($250/sq) | Jason: Smooth jumped to $330/sq late June 2026 | CONFIRM live |
| B&B siding | $4.50/SF ($450/sq) | $430/sq decoded | ✓ close |
| Brick (mat+labor) | $10/SF | ~$15–16/SF installed | LOW |
| Frieze | $3/LF | $4.50 ($5.50 at brick) | LOW |
| Porch beam wrap | $12/LF | $11 Hardie / $23 cedar (material-dependent) | single rate hides 2× |
| Metal roofing | $5.50 exposed-fastener (desc ✓) | standing seam ~$9/SF; meas-sheet header SAYS "Standing seam" | header/line mismatch — add standing-seam row |
| HVAC | $7,500/unit + $4/SF duct (≈$17k on 2,400 SF) | single 3-ton + duct $13–14k decoded | check |
| ✓ current | electrical $7/SF · counters $55/$35 · windows $400+$75 · well $10,100 · septic $8,500 · corner boards $4.60/LF · gutters $7/LF | | |

## D. QUESTIONS to settle before the schema is coded

1. **Shingle waste = 25% on every pitch row.** Reconciled evidence (Burns + Peterson vs Southern's actual
   bills): true overage is 10–11%; 15% is correct and slightly conservative; 25% overprices roofing ~9%.
   Keep 25% deliberately, or set 15%? (If 25% stays, the engine must NOT stack its own 15%.)
2. **Pitch-zone quantity basis:** in "Shingle 6 pitch ft2" do you enter the zone's FOOTPRINT (engine
   multiplies by pitch factor) or the true SURFACE (already multiplied)? Changes every roof number.
3. **Allowance markup:** confirmed model (Guarino) = 8%, but most allowance rows carry 15%. Which is current?
4. **Wall insulation is LINEAR ft** — LF × what height? (ties to missing ceiling-height inputs, A10)
5. **"Garage Wrap" $200 ft2 (row 219)** — what is this line actually?
6. **Room Perimeters** is one aggregate LF input — keep aggregate (× base height + vaulted adders), or
   go per-room rows now that heights vary?

## What's RIGHT (keep as-is)
Pitch-zone roofing rows (matches the decoded model) · countertop waste 1.24% · porch ceilings line ·
gutters LF+10% / downspouts count-with-length · kitchen backsplash 10% · appliance small-allowance model ·
no O&P/contingency line items (Buildern summary carries them) · water softener present as flagged option ·
dumpsters + landscaping zero-traps covered · termite line · supervision correctly absent (margin covers).
