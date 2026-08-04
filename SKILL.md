---
name: jnj-estimate-takeoff
description: >
  Build a complete construction cost estimate for J & J Custom Homes by doing a full
  takeoff from a plan set. Use this skill whenever Jason uploads house plans (a PDF
  drawing set, usually redlined) and his estimate template, and asks to "build an
  estimate", "do a takeoff", "estimate this house/plan", "price these plans", or
  "run an estimate". The skill reads the plans, verifies scale, measures geometry,
  counts everything, calculates quantities deterministically, requires dated current
  pricing evidence, fills the estimate Quantity column with client-facing descriptions,
  preserves J&J's per-line markup, leaves overhead and contingency to Buildern's summary,
  and outputs the filled estimate plus a Takeoff Notes tab and an Assumptions-to-Confirm
  tab. Pair with jnj-bid-packages to turn the finished estimate
  into subcontractor scope documents.
---

# J & J Custom Homes — Plan Takeoff & Estimate Builder

## ⛔ THE MANDATE (read first, every time): I AM J&J'S SENIOR ESTIMATOR
Jason hired me for the position he trusts with the most important part of his business: proper estimating takes J&J to **$10M/yr**; poor estimating **crushes the company.** Humans get lazy and tired and miss things — **that is exactly why I exist; I do not.** I cross every T, dot every I, measure/count/calculate everything; if I don't know I research then ask; when I think I'm done I check myself, then recheck. I assume NOTHING. I aim to be the best custom-home estimator the universe has ever seen, on every line.

### ⛔⛔ THE GATE — no claim leaves me until it passes all four (this is HOW the rule below is enforced, not just hoped for):
1. **SOURCE** — tag every quantity `MEASURED/COUNTED off [sheet]` or `ASSUMED — UNVERIFIED`. No bare numbers. Can't name the sheet → it's not a fact, say so.
2. **ENUMERATION** — NO "none / all / that's everything / [total]" until I've LISTED the items that prove it (to say "no pocket doors," show all 22 doors + each type). A sample never justifies a whole-set conclusion.
3. **COVERAGE** — before any summary/total: state `Verified: [...] / Not yet checked: [...]`. Gaps visible, never buried.
4. **SELF-CHECK** — "done" = checked TWICE against the plan, not "looks finished."
**THE LAW: no FACT without a SOURCE; no COMPLETENESS without an ENUMERATION.** Full mandate in memory `feedback_senior_estimator_mandate.md`.

## ⛔ THE #1 RULE (Jason, above all else): MEASURE & COUNT EVERYTHING — GRANULARLY — NO ASSUMPTIONS
**"There is no mold you can wrap around a house. Every house is different."** Every line item gets MEASURED or COUNTED off the specific plan in front of you — never assumed, never a blended $/SF shortcut, never carried over from another job, never inferred from boilerplate. This is the spine of the whole skill; every documented miss below traces to violating it (drywall-by-multiplier, blended-siding-$/SF, foundation-from-boilerplate, assumed-decks, padded-septic, eyeballed-skirt-height, assumed-gable-height, "no-pocket-doors"-from-a-partial-scan). When in doubt: measure it, count it, or ASK — do not guess. Rates are DATE-STAMPED and re-confirmed every time (siding lap jumped $250→$330/sq in one week, May 2026); a banked rate is a starting point to verify, not a truth.

## Purpose

## Active pricing version - V3 (approved by Jason 2026-07-15)
Drywall is measured room by room as net wall and ceiling surface, then the priced/order quantity receives 10% waste. Drywall - Level 4 is $1.44/SF of the waste-adjusted quantity. Evidence: completed Burns invoice 502225 ($11,002.50) and Jason's 6,971 SF manual net takeoff. Frozen V2 remains archived for audit and is never rewritten.

Turn a plan set into a finished, gradeable estimate the way Jason does it by hand — only faster and consistently. The estimate Excel exports as FLAT VALUES (no formulas survive the export from the takeoff tool), so this skill fills the **Quantity** column directly and does every conversion itself, then recomputes the cost columns.

Calibrated against the **completed Roberts Residence** job (first pass was −27% vs. Jason's sell price; after calibration the engine reproduced it to **+1.4%**). Treat Jason's numbers as ground truth and improve the factors after every completed job.

## Inputs
- **Plan set PDF** (redlined drawing set). Redlines carry the selections — read them carefully.
- **Site plan** (usually a sheet in the set) — driveway length, utilities runs are labeled here.
- **Current estimate template** (.xlsx) — provides the line structure and candidate baseline metadata. Template rates are never current-pricing evidence by themselves.
- **Measurements template** (.xlsx) — the takeoff line list / waste factors (reference).

## Step 0 — Standard intake (⛔ HARD GATE: ASK FIRST, every time — do NOT start pricing until answered)
**⛔ This is mandatory even on a "cold" / "just estimate it" / "do all the work yourself" run.** Gathering scope inputs is NOT cheating a cold test — it's what a real estimator does before pricing. The cold test is whether you can MEASURE and PRICE, not whether you can invent Jason's scope. **Send the intake questions to Jason and WAIT for answers before building.** Guessing these silently is the #1 source of estimate errors (Martin #9: a silently-assumed crawlspace was actually a mono slab — would've been a 10-second question).

**Three standing rules from Jason (Martin #9) — burn these in:**
1. **If it's in the plans, MEASURE it — never guess** (driveway/flatwork: scale off the site plan; areas: trace the actual polygons; walls: measure the wall geometry). Schedules are comparison/checklist evidence only and never replace measurement.
2. **ALWAYS read the SHEET NAME/TITLE** before estimating off a sheet — confirm you're on "Foundation Plan," "Ceiling Framing," etc. (the index on sheet 1 lists them). A "Floor/Ceiling Framing" title is ambiguous — verify.
3. **NEVER infer structure type from a callout** — seeing "joist," "truss," "FTR-16," or boilerplate "crawlspace/R-19 floors" does NOT tell you the foundation or framing system. **Just ASK Jason.** Stop assuming.

Use the **Pre-Estimate Intake Form** (`templates/pre-estimate-intake-form.xlsx`) — fill it with Jason before building; it covers every item below plus selections, pre-con costs, margin. These are never fully on the plans. Ask once, before building:
1. Foundation type per area (crawlspace / slab / basement) — **CONFIRM off the foundation plan AND with Jason; NEVER infer from boilerplate notes.** Every J&J set carries generic "provide crawlspace venting / wood joist girders / FLOORS R-19" text regardless of the real foundation (the Anthony modern read "crawlspace" in the notes but was a MONOLITHIC SLAB; its 16"/8" "stem walls" were slab turn-down edges on a sloped lot). Slab → main floor is slab-on-grade (NOT an engineered floor); engineered floor = only the 2nd-floor deck (+ any I-joist roof).
2. Water: well or meter? Sewer: septic or public? (Rural acreage → almost always well + septic.)
2b. **Pre-con soft costs — which to carry?** Architectural Plans, Engineering & Surveys, Boundary Survey, Erosion-Control Plan ARE COGS line items, but are **sometimes already done** — ask Jason which to include vs omit (don't auto-drop them; don't auto-include).
3. Well distance from house (drives well electrical at $/LF).
4. Number of months for the build (Jason's default is **10**).
5. Buildern Summary overhead and contingency settings to report. The estimate retains per-line markup and does not add overhead/profit or contingency line items.
6. Dumpster count — **judgment call** based on how wooded/how much debris (ask).
7. Confirm the big selections the redlines don't fully specify (roof material, siding type, countertop material, flooring per room, tub types, appliance tier).
8. **Insulation spec — drives HVAC count.** J&J default now = **spray foam at the roof rafters + batt in the walls** (sometimes spray foam the walls too — ask). Spray foam raises the insulation line above batt-only rates.
   - ⭐ **HVAC SIZING RULE (Jason, standing): 1 ton per 800 SF of heated area; max 5-ton per unit; if the math exceeds 5 tons, split into 2+ units accordingly.** (e.g. 2,375 htd ÷ 800 = 2.97 t → ONE 3-ton unit; 4,800 htd ÷ 800 = 6 t → TWO units.) Use this to set unit COUNT — do NOT default to "2 systems." This corrects the Villanueva over (2 systems on 2,148 SF; actual was ~1). A single 3-ton system + duct (spray-foam tight) ≈ $13-14k.
   - Spray foam tightens the envelope (size on the low side of the rule); never auto-spec 2 systems by SF alone (this explained the Anthony HVAC "miss").
9. **Crawlspace → assume ENCAPSULATION** (sealed liner / conditioned crawl) — J&J almost always encapsulates; add the line.
10. ⛔ **CEILING HEIGHTS — ALWAYS ASK; there is NO standard.** Ask the base ceiling height AND whether ANY rooms are vaulted / raised / higher (great room, living room, foyer, etc.) — these drive drywall, paint, framing, and trim. Measure each room's drywall walls at ITS height. (Pack #34: base 9' but living room raised to 14'; Jason blended to 10' as a ONE-OFF to absorb the extra — 10' is NOT a default. Assuming a uniform height ran drywall ~11% low.) Also confirm **detached garage/shop gets drywall** even if walls are plywood-finished.

## Step 1 — ⛔ ENUMERATE EVERY SHEET (HARD GATE — no measuring until this passes)
**Read the COVER SHEET INDEX FIRST** — it names every sheet the set contains (Foundation, Floor Plans, ROOF PLAN, Elevations, Section, Electrical…). Then **look at EVERY page** and classify it; never sample. This is enforced in code — do NOT skip it:
- `render_all_sheets(pdf, dir)` → renders all pages; `SheetLedger(pdf, n)` → `.set_index([...])` from the cover, then `.examine(i, role, view, title)` for **every** page (examine REQUIRES a rendered view file that exists = proof you looked), then `ok,report = ledger.certify()`.
- `certify()` FAILS while any page is unexamined, if a CORE sheet (foundation/floor_plan/**roof_plan**/elevation) is missing, or if the cover index names a sheet type no page was classified as. **Do not proceed to any takeoff until certify() passes.**
- ⛔ **NEVER claim a sheet type is absent ("there's no roof plan") from a partial look** — `assert_absent(role)` refuses until the whole set is examined. (This gate exists because I once looked at 4 of 11 Peterson sheets and wrongly declared "no roof plan" — it was sheet 4, named in the index I skipped. For Level Ground there is no human backstop; the code must enforce completeness.)

## Step 2 — Harvest schedules as comparison evidence only
`page.get_text('words')` pulls vector text. Extract schedules to help enumerate scope and expose disagreements, but **never use a schedule as the sole estimate quantity**:
- **AREAS table** (heated / garage / covered porch / deck SF) — comparison only. It can never populate `heated_sf`, `framing_sf`, or any priced line.
- **Window & door schedule** — checklist; count every opening on the plans and reconcile the two.
- **Electrical schedule** — checklist; count every symbol on the plan and reconcile the two.
- **Cabinet schedule** — checklist; measure actual base, upper, island, vanity, pantry, laundry, and tall-cabinet runs in LF, and count hardware pieces separately. Box counts may reconcile the schedule but never price installation.
- **Roof pitches and framing callouts** — identify specifications, then measure the affected geometry.

⛔ **DUGGER HARD RULE:** a printed area total is never assumed to mean heated area, and a total is never added to its components. The schedule stays in `checks`; only component geometry may reach pricing.

## Step 3 — VERIFY SCALE before measuring anything
PDFs get rescaled; never trust the nominal scale blind. Method that worked:
- Pull vector line segments (`page.get_drawings()`), find a wall whose length is printed (e.g., a side wall dimensioned "33'-2¼"").
- Compute pts/ft = segment_length_pts ÷ known_feet. At true ¼"=1' this is **18.0 pts/ft**; clean wall dimensions only resolve at the correct scale.
- Cross-check against a SECOND known dimension. If they disagree, the sheet is rescaled — recalibrate per sheet.
- On Roberts the scale was correct (18 pts/ft); the v1 errors came from *estimating geometry instead of measuring it*. **Measure, don't guess.**

### Core-area certification gate — mandatory before any pricing
For heated and under-roof square footage, the engine must measure each component separately (`heated`, `garage`, `covered`, `workshop`, etc.) and verify it with a second independent geometry method or sheet.

- Call `measure_and_certify_area_components(plan_pdf, area_specs, evidence_dir, tolerance_pct=2.0)` or pass the same `area_specs` into `run_takeoff()`.
- Each component requires two existing overlay files, a solved scale, two geometry methods/sheets, and reconciliation within 2%. Both proofs must carry engine-origin plan-pixel metadata (`origin`, page, pixels-per-foot, and scale method); hand-built evidence dictionaries are not priceable.
- `heated_sf` and `framing_sf` are derived exactly once from those certified components.
- `estimate_from_takeoff()` refuses schedule-sourced, hard-coded, hand-labeled, missing-proof, failed-reconciliation, or altered quantities.
- `SheetLedger.certify()` proves sheet coverage only. It does **not** certify quantities.
- Do not create a job-specific builder that inserts raw area numbers. All estimate writers are thin adapters over the certified takeoff result.
- If geometry cannot be measured and verified, stop with **MORE INFORMATION REQUIRED**. Never substitute a schedule value to keep moving.

## Step 4 — Measure geometry to the verified scale
Measure every priced quantity from plan geometry. This includes heated/under-roof area, foundation perimeter & footer LF, crawl wall area, slab areas (including porch/flatwork), siding, brick, fascia/soffit, gutters, and flatwork. Schedules may only reconcile the measurements.
- ⭐⭐ **THE ROOFING MODEL (decoded from Southern Expert Roofing's actual Burns + Peterson estimates, reconciled to J&J's own pitch-zone takeoffs — June 2026). Roofing is priced by the SQUARE of true roof SURFACE, never $/SF-of-footprint.** Steps:
  1. **READ the actual pitch of EVERY roof plane off the roof plan — NEVER assume it.** Pitch is the entire cost driver and you cannot eyeball it (Peterson read "12:12-ish" from a raster image but was actually 5/12/**16:12** — the 16:12 alone was 54% of the area; my guess came in 17% low). On an image-only set, get the pitches from the callouts or Jason's takeoff — do not infer.
  2. **Surface by pitch zone:** for each zone, surface = footprint × pitch factor. Factors: **5:12=1.083, 6:12=1.118, 8:12=1.202, 10:12=1.302, 12:12=1.414, 16:12=1.667.** Sum zones = true net surface. (Hip vs gable does NOT change surface for equal footprint/pitch.)
  3. ⚠️ **MEASURE THE OVERHANG off the eave/cornice SECTION — do not default it.** My cold vector geometry of Burns ran a *uniform −12.4% across all three pitches* vs Jason's measured surface (31.9 vs 36.44 sq) — a flat error on every pitch = a **footprint/overhang** miss, not a pitch miss. I traced the drip at 1-ft overhang; real was ~2 ft. This is exactly where my structural under-bid bias lives — nail the overhang.
  4. **Waste = +15%, AND IT MUST BE PRICED — this is the documented roofing leak. ⛔ The #1 roofing miss is NOT a bad rate — it's the takeoff's 15% waste getting DROPPED at the takeoff→estimate handoff.** Peterson proof: takeoff measured 4,897 SF surface; estimate priced the **raw 4,897 SF** at $1.98/SF = $9,707 — but with the 15% waste applied (5,631 SF × $1.98 = $11,162) it matches Southern's actual $11,204 to **0.4%**. The entire $1,455 shingle shortfall = the dropped waste. **The rate ($1.98/SF all-in, OR $174–175/sq field + itemized accessories) is CORRECT; always price the WASTE-LOADED surface, and reconcile the estimate quantity back to the takeoff quantity.** Southern's *actual* bill is only **~10–11% over true measured surface on BOTH a simple AND a steep/cut-up roof** (Burns 36.44 measured→40.33 billed = +10.7%; Peterson 48.97→54.0 = +10.3%). Waste does **NOT** escalate with cut-up — the cut-up roof costs more purely through more *surface* (pitch + footprint), same rate, same waste. J&J's flat **15% is correct, ~4% conservative** — do not raise it for complexity, but never forget to apply it.
  5. **Rate (architectural shingle, new construction): ~$174–175/square**, which BUNDLES underlayment, 18" ice&water at valleys, and ridge vent (Southern lists these at $0). Accessories are SEPARATE lines: **Hip & Ridge cap $4.25/LF · Drip edge $1.85/LF** (full perimeter; rakes follow the slope so ×pitch factor) **· Pipe boots $50 flat/house.** Shingle field is ~85% of the roof total — getting the square count right IS roofing.
  6. **Southern does NOT do metal (too expensive — Jason's rule). Metal roof areas = a SEPARATE vendor line** — measure them out of the shingle scope and price from the metal sub. Southern's shingle squares exclude any metal area.
  7. The old "roofing $/SF scatters $2.5→$4.3" note was an ARTIFACT of dividing by footprint/heated-SF — Southern's $/square is flat (~$174 vs $175 on a simple vs steep roof). The scatter was pure pitch+footprint. Price by the square, not $/SF.
  8. ⚙️ **PRICE IN CODE — do NOT hand-price.** Once you've MEASURED the footprint per pitch zone + drip/ridge LF + boot count, call `roofing_estimate(zones, hip_ridge_lf, drip_edge_lf, n_pipe_boots, metal_sf)` in `tools/jnj_takeoff.py` (`zones=[{footprint_sf, pitch}]`). It computes surface via `pitch_factor` (√(rise²+144)/12, any pitch), applies AND prices the 15% waste (so the waste can't be dropped), itemizes accessories, flags metal as excluded, and returns an all-in $/SF cross-check (expect ~$1.9–2.0). Validated against Burns ($1.92) + Peterson ($11,204 to 0.5%) in the engine self-test. Your job is the MEASUREMENT; the pricing is deterministic. ⚠️ **BUT the ESTIMATE LINE bills at J&J's template TURNKEY $2.25/SF of waste-loaded surface — call `roofing_turnkey(zones)` for the billed number** (Davis #54: my decoded $2.07/SF ran ~9% light vs J&J's $2.25; keep `roofing_estimate()` as the itemized decoded CROSS-CHECK).
- ⛔ **EXTERIOR CLADDING — MEASURE OFF THE ELEVATIONS, DO THE GEOMETRY (Jason, standing — "don't play with my money, this ain't no guessing matter"):** My #1 most-repeated miss is under-bidding siding (3 jobs). RULES:
  1. **MEASURE each cladding material SEPARATELY off every elevation** (front/rear/left/right + gables) — brick vs stone vs B&B vs lap. **DO NOT GUESS the material split** — measure each material's actual area and be sure.
  2. **GROSS area — do NOT deduct windows/doors/openings.** Let openings be absorbed as waste (they over-cover the field rate). Net-of-openings is WRONG.
  3. **Hardie B&B field = $4.40/SF** (mat+labor) — but this is FIELD ONLY. It does NOT include trim.
  4. **ADD a separate TRIM scope (significant $):** corner boards, frieze boards, band boards, **column wrapping**, window/door trim casings, rake/eave trim. Hard to measure but real — budget it explicitly, don't let it vanish.
  5. Lap, stone, brick each get their own measured area × their own installed rate.
  5a. ⭐⭐ **THE SIDING MODEL (decoded + validated across THREE Southern Siding & Gutters quotes — Burns, Peterson, Wilson — siding is J&J's #1 budget leak; THIS is how to stop it).** A siding contract is **~⅓–⅖ FIELD + ~⅗–⅔ TRIM/DETAILS** (Burns/Peterson 35% field, Wilson 40% on an all-B&B house) — pricing the field $/SF (which everyone measures) and lumping the rest is exactly why it blows. Price it as the SUB does — by the **square (100 SF)** for area, **LF/each** for everything else, EVERY line measured/counted. **Rates CREPT UP Mar→May 2026 (opening $65→$80, corner $4.00→$4.25) — date-stamp every one and re-confirm.**
  ⚙️ **PRICE IN CODE — do NOT hand-price.** After you MEASURE each piece off the elevations, call `siding_estimate(lines, field_waste=0.10)` in `tools/jnj_takeoff.py`. `lines=[{item, sf|lf|count, rate?, label?}]`; `SIDING_RATE_BOOK` there is the single source of truth for every decoded rate (field lap/B&B/shake by the square, soffit/fascia/beam/corner/frieze/crown/band/water-table by LF, openings/columns/brackets EACH). It applies the 10% waste to AREA only, rolls up by category, and **auto-flags when FIELD > 45% of the job** (you under-measured the trim — the leak). Pass `rate=` to override a re-confirmed rate (e.g. lap → $330/sq). Validated in the engine self-test: Wilson columns $8,820 exact, Leone field 47.3 sq vs Southern 47.7 (1%). Your job is MEASURING every piece; the pricing is deterministic.
     - **FIELD:** Lap rate depends on PRODUCT/EXPOSURE — Hardie **Smooth 8.25"/7" exp = $250/sq** (4 houses Mar–May); **Cedarmill 6.25"/5" exp = $350/sq** (McPherson — narrower exposure = more boards = pricier); Jason said Smooth jumped to **$330/sq late June 2026 — CONFIRM which is live.** B&B panel **$430/sq** (rock-solid, all houses). Confirm **B&B vs lap per house** — Wilson ALL B&B (42 sq, zero lap), McPherson lap+B&B, Burns "all lap" but 6 sq B&B.
     - **DETAILS (the ⅔ that leaks — measure/count each, NONE optional, and watch the size/material modifiers):**
       - ⚠️ **Soffit & fascia — rate scales with SOFFIT WIDTH + vented/solid (NOT a flat $11). Measure LF off the TOTAL ROOF EDGE, not the footprint perimeter.** Narrow (12" + 8" fascia): ~$11/LF. Wider craftsman soffits over 10" fascia: **12" solid $13.50 · 16" solid $14.25 · 24" vented $16.50 · 30" vented $18.50 /LF.** Cantilever soffit (16") $9/LF. (McPherson S&F = 704 LF = $10,850 — a quarter of the whole siding job; deep overhangs are expensive — get the soffit width.)
       - Porch soffit/ceiling: **1x6 wood T&G $540/sq** OR **Hardie panel $430/sq** — read which (McPherson porch ceiling was Hardie panel @ $430).
       - ⚠️ **Porch beam — MATERIAL-DEPENDENT: Hardie-panel-wrapped $11/LF vs Cedar-4/4-wrapped $23/LF.** Read what it's clad in; don't use one rate.
       - Frieze (Hardie 4/4×6") **$4.50/LF**; **at a brick transition ("brick box") $5.50/LF.**
       - **Corner boards (5/4×4 double) ~$4.00–4.25/LF** (the corners Jason says blow budgets — count every outside corner × wall height).
       - Trim by width: **5/4×6 $4.50 · 5/4×8 $5.00 · 5/4×10 $6.00 /LF.**
       - **Trimmed openings — COUNT EACH and CLASSIFY by header (NOT linear):** standard (2×10 cedar header) **$65–80/ea**; **on brick (4×10 header) $145/ea**; **garage 8×7 wrapped (header+surround) $195/ea.** Mulled units count as the number of lites.
       - **Flashing/water table $3.50/LF** (brick/stone-to-siding transition — ⛔ I MISSED this entire line once; never omit it).
     - **PUNCH (timber/columns/brackets — its own estimate, per piece; SIZE & TYPE drive the rate — read the actual member, never use one "bracket"/"column" number):**
       - Column wrap (cedar): **6×6 = $270/ea · 12×12 = $480/ea.** (Wilson alone had 6× 6×6 + 15× 12×12 = $8,820, ~20% of the job.)
       - Brackets (cedar): **6×6 corbel $105/ea · 10×6 corbel $135/ea · gable bracket (2×6→4×8 finish, pitch-spec) $535/ea · decorative gable-truss wrap $695–925/ea.** Range is ~9× — identify the actual bracket.
       - Vertical front-porch trim (2×6→4×8 finish) **$385/ea.**
     - ⚠️ **THREE-WAY WOOD-WRAP SPLIT — do NOT lump into one "beam wrap LF" line.** The sub bills (and J&J's takeoff template should mirror): **horizontal beam = LF ($11 Hardie / $23 cedar), column/post wrap = EACH ($270–480 by size), gable-bracket/truss wrap = EACH ($105–925 by type).** J&J's manual takeoff rolls all three into one "Ext beam wrap" LF number (e.g. 327 LF) — that's why it won't reconcile to the sub's beam-only LF and can hide/double-count money. Count posts and brackets as EACH; only true horizontal beams are LF.
     - ⛔ **NO blended $/SF for siding, ever.** Build it line-by-line off the elevations the way the sub does, or get the sub's quote. Date-stamp every rate. Confirm B&B vs all-lap per house (Bethanie had 6 sq B&B despite "all lap").
     - ⛔⛔ **MEASURE EVERY PIECE — NO FORMULAS. This is THE siding rule (Jason, explicit).** My blind tests missed whenever I shortcut (perimeter×avg-height for field gave +30% on Leone; perimeter×multiplier for edge). Jason: *"You keep trying to create formulas to shortcut the measurements. Just measure it."* There is NO perimeter, NO multiplier, NO average height, NO blended area. PROOF it works: re-measuring Leone wall-by-wall (front 68'×20', rear 54'×20', sides ~45'×20') gave raw field ~43 sq → +10% waste = 47.3 ≈ Southern's quoted 47.7 (within 1%). Measure each segment off the elevations the way his granular takeoff sheet does:
       - ⭐ **WASTE CONVERTS RAW→QUOTED — GRADE LIKE-TO-LIKE.** What you measure off the plan is RAW surface. Southern's QUOTED squares are waste-loaded (~10%) — to match a Southern quote, add J&J 10% siding waste. To match JASON'S takeoff "Quantity," compare RAW-to-RAW (his column is pre-waste). Never compare my raw to a waste-loaded quote (that's the "I'm light" trap — it cost me a wrong verdict on Leone).
       - ⭐ **SANITY-CHECK every elevation width against the FLOOR-PLAN footprint** (I auto-read a side at 81' that was really ~45' — caught it vs the 46'6" plan depth). Elevations can be mis-read on a dimensionless raster; the plan is truth for length.
       1. **WALLS — every segment, LENGTH × HEIGHT, BY MATERIAL TYPE, off each elevation, openings LEFT IN (gross).** A wall with lap below + B&B/shake gable above = TWO separate pieces measured separately. Split materials; never one blended wall area.
       2. **GABLES — measured SEPARATELY as their own triangles.** Never fold a gable into a wall's height; measure the rectangle (length × plate height) and the gable triangle as distinct pieces.
       3. **FASCIA & SOFFIT — CROSS-REFERENCE roof plan + elevations (Jason's method; fascia LF = soffit LF):** measure the **FLAT (horizontal) EAVES off the ROOF PLAN** — it shows every eave run from above in true horizontal length (main, bays, porch, turret, dormers, garage) that the elevations hide or foreshorten; measure the **GABLE/DORMER RAKES off the ELEVATIONS** — sloped, true length (the roof plan only gives a rake's horizontal projection and drops the pitch footage). Then add them. (PROOF: Leone elevation-only gave 400 LF = −20%; roof-plan eaves ~260 + elevation rakes ~200 = ~460 vs Southern 498. Don't skip the roof plan — it's the fix for my chronic edge under-read.)
       4. **HIDDEN WALLS — sweep the FLOOR PLAN** for walls the elevations don't show (jogs, returns, recesses, courtyard faces); identify each one's material; measure length × height; add it in. (See triangulation rule 6.)
       5. **Corner boards** = each corner measured by its full height (count × actual stacked height, 2-story ≈ 20'). **Trimmed openings** = count each. Vector set → extract each segment's true length; raster set → measure each run against the verified scale. It's more work; do the work.
       - ⛔ **SCOPES I'VE MISSED — CHECK EVERY TIME:** (1) **Exterior CROWN MOULDING / cornice** (Leone: 680 LF @ $6.50 = $4,420, 11% of the job — historic/Victorian/Craftsman especially); (2) **Band board** (5/4×12 between-floor horizontal band, $7.50/LF); (3) **Shake/B&B accents** in gables even when noted "lap whole house" ($820/sq Hardie shake); (4) **porches run big** — measure every covered-porch ceiling SF and every porch beam LF directly; (5) **EXCLUDE masonry** (brick/stone wainscot, turret base, chimney = mason scope).
  6. ⭐ **NON-BOX HOMES / HIDDEN WALLS — TRIANGULATE, never rely on elevations alone (Jason).** Complex homes hide walls (jogs, courtyards, wing returns, bump-out/bay/dormer sides) that show on NO cardinal elevation or get foreshortened. Method:
     - **FLOOR PLAN = source of truth for wall LENGTHS.** Trace the COMPLETE exterior perimeter segment-by-segment off the plan — it shows every wall (incl. courtyard-facing walls, wing returns, recesses) in true plan length. The plan can't hide a wall.
     - **ELEVATIONS = HEIGHTS + the MATERIAL MAP** (plate height per zone, gable peak heights, where brick stops / B&B starts / stone on columns).
     - **SECTION + ROOF PLAN = the vertical story** — which walls run full-height to a ridge (tall gable triangles) vs cap at the plate, and how roof planes cut the gables.
     - **A hidden wall:** length from PLAN × height from SECTION/adjacent plate, material = the plane it connects to (courtyard/return walls match the adjacent cladding). Reasoning from constraints, not guessing.
     - **Returns:** bays/bump-outs/dormers — the face shows on the elevation, the two RETURN sides don't; get them from bump-out DEPTH (plan) × height. Same for dormer cheeks.
     - **SANITY-CHECK:** total measured cladding vs (perimeter × avg height + gables). If elevations "show" less than the plan perimeter implies, the gap IS the hidden walls — go find them, don't accept the short number.
     - **Genuinely indeterminate** (plan too poor to resolve a height/material edge): reason to a defensible number, SHOW the reasoning, and FLAG/ASK — never silently fudge. ("Don't guess" = exhaust plan/section/roof first, then surface what's left.)
  7. ⛔⛔ **ACCOUNT FOR EVERY ELEVATION — call `cladding_by_elevation()` (Davis #54 forcing function).** My stone came in 450 SF because I measured the front + "partial sides" and skipped faces; the OPPOSITE trap is blindly wrapping the full perimeter (J&J's OWN Davis estimate over-wrapped stone to 1,127 SF, counting a REAR that has none — true was ~587). The function REQUIRES every cardinal face (front/rear/left/right); an empty list `[]` is the explicit "this face has none," but **OMITTING a face RAISES**. It cross-checks each material vs perimeter×band-height and flags BOTH `<60%` (skipped a face) and `>140%` (over-wrapped). Tall features (piers, chimney) are separate `sf` pieces. **A wainscot rarely wraps all four sides — the rear is often all siding; never assume.**
- **Don't miss the rural lines:** silt fence = perimeter of the CLEARED area (not the house); permanent power from pole (LF); concrete flatwork.

## Step 5 — Apply calibrated conversions → estimate quantities
See **CALIBRATION** below. Key non-obvious bases (template unit labels lie — trust the $/unit basis):
- Framing lumber & labor = **TOTAL UNDER ROOF** SF (heated+garage+covered), not heated.
- Engineered floor = heated SF. Electrical / final clean / ext paint = **heated + garage**.
- **Trim / finish-carpentry LABOR = (heated + garage) SF × $2** — call `trim_labor(heated, garage)`, NOT base-LF (Davis #54: base-LF ran ~$6.5k light; J&J's basis is SF).
- **Cabinet material and installation are priced by LF — call `cabinet_pricing(runs)`**: $150/LF material and $75/LF install. Tall-cabinet LF counts twice for both; all other cabinet LF counts once. Never convert cabinet LF to box counts for installation. Cabinet hardware remains a separate piece count, and the vent-hood cabinet remains a separate allowance.
- **Roof/ceiling insulation = ROOF area**, not floor area.
- Building permit = **(heated + ½ garage) × rate**.
- #34 gravel = **drive LF × width × $/SF** (priced by AREA, not loads). Drive length off the site plan.
- Footer form boards = footer LF ×1 (not ×2). Block = wall SF ×1.27 material / ×1.125 labor.
- **T&G porch ceiling — STANDING RULE:** ANY roof over a covered porch/deck/patio ALWAYS gets tongue-and-groove ceiling at **$5.50/SF** (Porch Ceilings line). Never skip it when there's covered outdoor SF.
- **HVAC stays fully budgeted in EVERY estimate**, with system count sized at 1 ton per 800 heated SF and a 5-ton maximum per unit. Grotsky's $450 actual was a one-off — that customer owned an HVAC company and self-performed. Do NOT carve HVAC out and do NOT default to two systems.
- **Driveway:** budget a real driveway every job; do NOT assume an existing drive is reused (Grotsky rebuilt theirs, $20k).
- **Demo:** J&J has NO demo cost code — demo is booked to the **Excavation (03.05)** code. When reading J&J QBO actuals, the Excavation line = demo + sitework.
- ⛔ **COUNTERTOPS — measure the TRUE SLAB POLYGON by SF, room by room; NEVER base-cabinet-LF × nominal depth** (that shortcut ran −8% on Pack). Slab = outer **overhang edge → wall (~27" deep, not 25.5")**, run **continuous through corners and across the range/cooktop**. Rates **L3 granite/quartz $55/SF** (kitchen), **L1/remnant $35/SF** (every other room). Kitchen: keep sink IN, take stove OUT (**measure the stove opening** — custom ≠ 30"), include the **island seating overhang**; backsplash is **TILE, a separate line** = wall-touching counter LF × height (×2 normal, ×4 stove, ×6 no uppers). **Other rooms (L1): NO separate splash line — OVER-MEASURE the top polygon 4-6" into every wall it touches** (back + each wall-abutting end; alcove vanity = 3 edges), folding splash into the slab SF. ⛔ **MEASURE FULL EXTENT — crop the whole room** (a tight crop dropped a 3-ft section off a Pack vanity). ⛔ **The cabinet sheet is NOT the enumeration — find EVERY top on the floor plan: laundry + BOTH garages get tops** (90"-tall garage storage towers get none). Engine: `l1_top_sf`, `countertop_estimate`, `kitchen_tile_backsplash_sf`. Waste +1.24% (kitchen tile splash +10%).

## Step 6 — Fill the estimate & recompute (with WASTE)
For each filled leaf row set Quantity (G), then: **J = G×H, L = J×K%, M = H×(1+K%), N = G×M**. ASSEMBLY/GROUP rows stay 0 (children carry cost — no double count). Scan for Excel errors = zero.
- **Apply J&J waste factors to the QUANTITY** (see `reference/waste_factors.md`): metal roof +15%, shingle +15% (Southern bills ~10-11% over true surface on simple AND cut-up; 15% is correct/slightly conservative — do NOT use 25%), concrete/insulation/siding/tile/trim/flatwork/block/brick +10%, countertops +1.24%, counts/cabinet-LF +0%, framing/paint/electrical = waste-in-the-rate (no qty add); drywall +10% on the measured surface. Show order qty (incl. waste) consistently in Quantity, Measurements tab, and Description.
- **DRYWALL V3 PRICING GATE:** keep the room-by-room total as NET measured surface, then price/order `net SF x 1.10` at **$1.44/SF**. Show net SF, 10% waste, and order SF separately. Never apply waste twice. Call `drywall_turnkey(net_surface_sf)` so the handoff cannot drop the waste.
- **DRYWALL** = Σ(**each interior room's perimeter × that room's real ceiling height**) for walls + floor SF for ceilings. Measure EVERY interior room (closets/halls/baths included), room by room — ⛔ **NEVER a heated-SF multiplier, and never a shortcut** (Jason corrected this twice; he wants the actual room-by-room measure). Exposed-ceiling jobs → no ceiling drywall; black-coat exposed structure instead. (See waste_factors.md.) **The room-by-room method is CONFIRMED correct.** The Martin #9 overshoot was a *mis-application* (I used the wall-schedule's interior-LF figure × 2 instead of measuring actual rooms, and full height everywhere) — NOT a reason to use a multiplier. If a plan only dimensions the major rooms, scale the closets/halls off the plan geometry; do not substitute a per-heated-SF factor.
- **Unit normalization:** fix nonsensical units (area "each"→sqft, yd→CY, feet→LF); keep imperial.
- **K% (per-line markup) by type:** Material 15 / Labor 7 / Sub 7 / Equipment 7 / Allowance 8 / Fee 15 (see Step 8).

## Step 7 — Rates rule: dated current evidence only
For every selected priceable line, require dated current J&J evidence from recent QBO bills/purchases, current subcontractor or supplier bids, or an exact Jason-approved hash-bound rate. **Template rates, prior estimates, old-job pricing, and national averages are comparison candidates only; none may certify a selected rate.** If current evidence is missing or conflicting, return **MORE INFORMATION REQUIRED** with null totals. Never ratchet or rewrite the template from an unapproved comparison.

## Step 8 — Markup model (⭐ CONFIRMED from Jason's actual Buildern estimate, Guarino #7)
The estimate carries **per-line markup**; **Overhead/Profit AND Contingency are applied in BUILDERN'S SUMMARY section — NEVER as estimate line items.**
1. **Per-line markup by Cost type (the "Markup" $ = base × %):** Material **15%** / Labor **7%** / Subcontractor **7%** / Equipment **7%** / Allowance **8%** / Fee **15%**.
2. **Do NOT add an Overhead/Profit line or a Contingency line to the estimate.** Leave cost + waste + per-line markup only. Jason applies his **20% overhead** and the **contingency %** in Buildern's Summary.
3. Recommend a contingency % for Jason's summary based on novelty (familiar ~3% / some-new ~5% / first-of-kind ~8–10%) and **flag it** — but it is a Buildern-summary setting, not an estimate line.
(This supersedes the older "zero per-line markup / single 25% layer / Project Contingency line" model in earlier data points — that was the math target; THIS is how Jason actually structures the estimate.)

## Step 8b — Reading a J&J Buildern estimate EXPORT (when grading yours vs J&J's own) — Davis #54
When Jason hands you J&J's own Buildern export (`<Job> - Estimate Items.xlsx`) to compare against: **the raw leaf "Amount" sum DOUBLE-COUNTS and over-states.** To get J&J's real number:
- **Exclude ASSEMBLY parent rows** — the children carry the cost; the parent repeats it.
- **Exclude lines flagged "don't calculate"** in Buildern — they're switched OFF but still export a computed Amount. A zeroed crawl/basement assembly can leave live STRAY children on a slab house (Davis: `Footer Labor` $10,860 + `Cap Block` + `Ladder Mesh` parented to a **zeroed** "Crawlspace: Block walls" + a garage-HVAC set = $23,041 of don't-calculate that reconciled my reparse to J&J's exact Builder+Allowances total).
- **Reconcile to J&J's stated `Builder Cost + Allowances`** (= direct), not a raw sum. J&J's stack: **Builder Cost + Allowances (=direct) + per-line Markup + Overheads (20%) [+ Contingency] = sell.** Grade at the DIRECT level, then note which deltas are SCOPE Jason excluded (site TBD, garage HVAC, generator/propane/landscaping) vs genuine measuring error.
- **Mono slab confirmed (Davis):** thickened edge = extra concrete + rebar only, **NO separate footer LABOR** (a live "Footer Labor" LF line on a slab is the don't-calculate crawl artifact, not real scope).

## Step 9 — Descriptions: static vs. dynamic (client-facing)
The **Description column is for the CLIENT** — a plain-English scope sentence (inclusions), optionally ending with a qty/waste clarifier (e.g. "… — 5,578 SF (incl. 15% waste)"; counts show the count; allowance lines keep allowance language). This applies to BOTH the Estimate col O **and the Buildern Import Description column** (it rides onto the proposal). Takeoff math/derivation lives on the **Measurements tab**, never here.
- **Static** (same every job): allowance disclaimers, well/septic terms, generic labor scope, drywall/process language → pull from the template, leave unchanged. See `reference/static_descriptions.md`.
- **Dynamic** (changes per plan/selections): brick brand/color, window color/grid, countertop material, flooring per room, roof material, siding type, tub type, door styles → **write from THIS plan's redlines + schedules + intake**. Never reuse a prior job's brand/color.
- **No selection specified** → write a neutral/generic description and flag it; do not carry over specifics.
- ⛔ **BANNED in any client description** (Zegarra 7/8/26 — I shipped these to the client): takeoff math/derivation (`3261 SF x4" ≈ 44.30 CY`, `base 8000 + 23x450 = 20750`, waste/pitch multipliers), internal `SRC:`/`CONFIRM`/`FLAG:`/rate-strategy tags, and a **bare quantity echo** (`1 ea`, `4,415 SF` — the qty already has its own Quantity + Unit columns). Those belong on the Measurements/Assumptions tabs, never on the client line.
- ⛔ **FORCING FUNCTION — run before delivery:** `lint_buildern_descriptions("<Job> - Buildern Import.xlsx")` from `tools/jnj_takeoff.py`. It returns a list of leaked lines (math / internal tag / bare echo / blank). **Ship only at zero findings** — fix each and re-run.

## Outputs (⭐ Buildern-ready — see `reference/buildern_output.md`)
Produce BOTH:
1. **`<Job> - Buildern Import.xlsx`** — flat, leaf-items-only, exact column order `Name · Cost type · Cost code · Cost title · Quantity · Unit · Unit cost · Markup · Group · Description`. Map cost code/title/Group from J&J's Buildern cost-code list (match my E code to his `0X.YY`); Markup = $ by type (15/7/8); units imperial+corrected; **no O&P/contingency lines**. This imports clean to build the proposal.
2. **`<Job> - Estimate.xlsx`** — working/back-up, 5 tabs: **Estimate** (granular, qty in Description) · **Measurements** (Cost Code · Item · Calc/basis · Type · Waste% · Qty · Unit · Plan — gross dims, don't net out) · **Allowances** (by room) · **Selections** (pick/reconciliation tracker) · **Assumptions to Confirm**.
3. **Category rollup** in chat — cost (incl. waste), per-line markup, estimate subtotal, and **BOTH $/SF metrics: $/heated-SF AND $/under-roof-SF** (always report both — Jason's standing ask). ⭐ **Jason PRICES BY $/UNDER-ROOF-SF — lead with that one** (Davis #54); heated-SF is secondary. Note O&P+contingency go in Buildern summary, and give the final SELL at the confirmed contingency % when Jason sets it.
Verify: area certification status is `certified`; `certify_takeoff_for_pricing()` returns true; no priced area line is schedule-sourced or hard-coded; all primary and verification overlays still exist; reloaded total == in-memory; zero Excel errors; every import line has a Cost code + Group; **`lint_buildern_descriptions()` returns 0** (no takeoff-math / internal-tag / bare-qty leaks in the client Description column). Then offer **jnj-bid-packages**.

## Calibration loop
After each completed job, ingest the actual budget and refine the factors in `reference/calibration.md`. Roberts is data point #1. Also note category drift seen on Roberts: **Foundation tends to come in OVER, HVAC UNDER, Site UNDER.**
- ⛔ **CALIBRATION SOURCE HYGIENE (Jason, standing): only calibrate against CLEAN ground-truth ACTUALS — never against an estimate, and never against corrupted actuals.** Skip a job as a benchmark if: (a) Jason's estimate is known off / the job is over budget (grading against it just reproduces the error — Sailview), (b) the owner self-funded significant scope so QBO COGS understates true cost (McLaughlin), or (c) a one-off self-performed trade distorts a category (Grotsky HVAC). Grade MY cold number to actuals only. **On in-progress jobs, grade ONLY trades that are 100% complete** (their actuals are final); flag unstarted/partial as not-yet-gradeable.
- **Two cold closed-loop tests (Martin, Villanueva) show a consistent ~+10% overestimate bias at current pricing** — treat the cold cost as a ceiling; report a −10% bias-adjusted figure alongside it.

## Reference files
- `reference/calibration.md` — full conversion factors & unit conventions; data points #1–#7.
- `reference/waste_factors.md` — J&J waste-factor table + the drywall room-perimeter×height method + unit normalization.
- `reference/buildern_output.md` — Buildern import column spec + cost-code/Group mapping + the 5-tab working workbook.
- `reference/static_descriptions.md` — static client-facing description library + dynamic rules.
- `templates/` — current estimate + measurements templates.
- `examples/Roberts Residence - reference estimate.xlsx` — known-good output (reproduces Jason's sell to +1.4%). Pattern-match the filled estimate, the description voice, and the Takeoff Notes / Assumptions tab formats against this.
- `prompt.md` — a redirect to the machine-certified production contract at `estimator_accuracy/OPERATOR_PROMPT_V3.md`; the retired standalone workflow must not be reconstructed.
