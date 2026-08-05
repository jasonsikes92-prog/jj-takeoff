# J&J Takeoff Calibration — Conversion Factors & Unit Conventions
Recovered from the completed **Roberts Residence** (1-story farmhouse, 2,127 heated SF, crawlspace house + slab garage, well + septic, rural wooded lot). These are the formulas the Excel export strips out. Trust the **$/unit basis**, not the template's unit label.

## CURRENT AREA AUTHORITY OVERRIDE — 2026-07-17
Core heated and under-roof square footage must come from measured component geometry with two independent proofs and saved overlays. Designer SF schedules are comparison evidence only; they never populate a priced quantity. `heated_sf` and `framing_sf` are derived exactly once from certified components. Any older note below that calls a schedule authoritative or says a printed number beats measurement is historical and superseded by this rule. If the geometry cannot certify, the result is **MORE INFORMATION REQUIRED**, not a schedule fallback.

## Quantity bases (the non-obvious ones)
| Estimate line | Quantity basis | Roberts value |
|---|---|---|
| Framing lumber | TOTAL under roof (heated+garage+covered) | 3,403 SF |
| Framing labor | TOTAL under roof | 3,403 SF |
| Engineered floor | heated only (crawlspace) | 2,128 SF |
| Electrical SF price | heated + garage | 2,842 SF |
| Final clean / exterior paint | heated + garage | 2,842 SF |
| Interior paint | heated SF | 2,127 |
| Garage paint | garage SF | 715 |
| Roof / ceiling insulation | **ROOF area** (not floor) | 4,256 SF |
| Floor insulation | crawlspace floor | 2,312 SF |
| Wall insulation | exterior wall area | 2,346 SF |
| Building permit | (heated + ½ garage) | 2,485 |
| Drywall | ceilings SF + walls SF (int 2-side + ext 1-side) | 3,127 + 7,939 |

## Material conversions
- **Roof area** = footprint-under-roof × blended pitch factor. Weight by AREA of each pitch zone. Roberts: 5:12 (1.083) ×750 + 8:12 (1.202) ×1,738 + 12:12 (1.414) ×1,794 = **4,283 SF**, blended **1.257**. (Pitch factor = √(rise²+144)/12.)
- **#34 gravel** = drive LF × width(ft) × $0.80/SF. Priced by AREA, not loads. Roberts: 895 × 12 = 10,737 SF. (Drive length from the SITE PLAN — it's labeled.)
- **Driveway mat** = drive LF × 1 @ $1.75.
- **Footer concrete (cu yd)** = footer LF × (footer W × H in ft) ÷ 27. 16×18" footer = 2.0 SF section.
- **Footer form boards** = footer LF × 1 (NOT ×2). **Footer rebar** = 2 bars × footer LF ÷ 20 = sticks.
- **Block count** = wall SF × 1.27 (material, incl. waste) / × 1.125 (labor). 1 block = 0.889 SF.
- **4" slab concrete** ≈ slab SF × 0.0157 = cu yd (≈5" effective with thickened edges).
- **Shingle roof** = turnkey @ ~$2.25/SF PLUS per-pitch upcharge @ ~$1.50/SF per pitch band.
- **Windows** counted per opening (mulled doubles/triples = individual lites). Roberts: 23.
- **Fixture openings** (tubs/showers/toilets/sinks) and **water openings** (fridge/ice/washer/hose bibs/DW) counted separately.

## Rates seen on Roberts (anchor; refresh vs. national avg, use higher)
framing lumber $10/SF · engineered floor $9 · framing labor $5.5 · electrical $5.5 · shingle turnkey $2.25 · brick (all-in) $10/SF · fixture opening $700 · water opening $350 · permit $1.50/SF · gravel $0.80/SF · vanity cab $256/LF · LVP $5.25/SF all-in · gutters/downspouts $7/LF.

## Cost structure (Roberts)
- Sell estimate **$591,341** = builder cost $486,774 + overhead/margin ~28% (ONE layer) + insurance.
- Original cost budget $455,089 · **Actual cost $443,274** (came in ~$12K under).
- Margin ≈ 25% of sell / ~29% of cost.

## First-pass misses to actively avoid
- Roof **+19% high** (assumed steep pitch dominant — weight by area instead).
- Footers −32% low, slab −30% low (missed porch/flatwork slab), brick **−61% low** (1,274 SF actual), roof insul **−49% low** (used floor area).
- Backsplash, gutters, downspouts, fans all low.
- **Missed entirely:** silt fence (1,006 LF = cleared-area perimeter, NOT house perimeter), permanent power from pole (966 LF), concrete flatwork (1,256 SF walks/apron).
- Front door = **double** wood; garage = **1 double** door; interior doors mostly hollow (12 hollow / 1 solid / 2 pocket).
- Don't stack per-line markup + overhead (double-counts margin).

## Category drift (estimate vs. actual on Roberts — for realism)
Foundation **+46% over** · HVAC **−49% under** · Site **−28% under**. Pad foundation; trim HVAC.

---

# Data point #2 — Hernandez (4820 Goolsby Rd, Monticello, Jasper Co.)
Slab-on-grade **barndominium**, 1,863 heated SF + 713 garage/mech + 697 covered porch = **3,273 SF under roof**. Well + septic, 12-ac wooded lot, standing-seam metal roof, Hardie board-and-batten, all-electric. **No crawlspace / no block / no engineered floor** (slab) — zero out those template sections.
Blind first pass reproduced the **original cost budget ($441,916) to -1.0%** after fixing three rate misses. Actuals: orig $441,916 / revised $480,804 / **actual $485,255**.

## RATE corrections learned (template was low - bump these)
- **Framing lumber: template $8/SF -> ~$16/SF actual on this barndo.** Single biggest miss. Use **$14-16/SF** for steep-pitch / 10' wall / timber-accent barndos (complex truss roof drives it). Frame labor held ~$6/SF.
- **Standing-seam metal roof: ~$9/SF turnkey** (template $5.50 = exposed-fastener/material only; exposed-fastener R-panel ~$6-7).
- **Windows: ~$722 each** actual (template $400). Use ~$700/opening for mid-grade vinyl.
- **Electrical: ran > $7/SF template** - used $8.5/SF; actual category came in even higher ($40k).

## Structural notes for grading vs a Buildertrend budget
- Their budget folds **well + septic + underground water into the PLUMBING category** (07.15/07.20). The estimate template puts them under *Utilities Improvements*. When grading, combine.
- Their cost budget carries **Supervision + Overhead/Business Costs (02) ~ $41k ~ 9% of cost as COST lines.** The estimate template has NO such line - it lives in the single 25% margin layer. Don't double-add it.
- **Appliances came in ~$0** (homeowner-supplied). Keep an allowance but flag it's often homeowner-supplied.
- Margin: Jason confirmed **25% margin ON SELL** (sell = cost / 0.75 = cost x1.333), single layer, per-line markup zeroed.

## Category drift, Hernandez (actual vs original) - where bids ran light
Carpentry/Countertops **+72% over** / Landscaping **+182% over** (change orders) / Roofing **+42%** / HVAC **+47%** / Foundation **+37%** / Electrical **+39%**. Framing **-6% under** / Plumbing **-10% under**.
**Pattern across both jobs: pad Foundation, HVAC, and finish carpentry/countertops; don't trust the template's framing-lumber and metal-roof rates.**

---

# Data point #3 — Darwish / Curtis Miller (Henry Co.) + 3-JOB SYNTHESIS
**High-end, all-brick, two-story**, architect-designed (Joel Aviles), shingle roof. Orig budget $698,041 -> Actual $754,718 (**+8.1%**; scope-adjusted vs Revised **+6.2%**). Sell $882,200, **15.2% margin** (missed 18-22% target). 17-mo build, Henry County. **4 of 5 change orders REJECTED** (only the $17k driveway approved) — so overruns could NOT be recovered via COs. First job up at the $750k/high-end/2-story/brick tier.

## What 3 jobs now prove (Roberts crawl farmhouse / Hernandez slab barndo / Darwish brick 2-story)
Use the **variance ledger** (`Downloads/JJ Estimating Variance Ledger.xlsx`) — rebuilds from each job's Buildertrend Budget List. Buckets:
- **SYSTEMATIC OVER (fix the rate, pad it):** FOUNDATION +46/+37/+34% — *3 for 3, pad ~15%*. Roofing & GUTTERS +4/+42/+78% (gutters chronically underbid). Paint +9/+29/+20%. Preliminary/PERMITS +56/+103/+82% — **permits vary ~2x by county** (Henry ran 2x Jasper); pre-qualify with the county before contract.
- **ZERO-TRAP — always budget on every contract:** Punch-out (+1773/+478%), Landscaping ($0->$15k). Appliances usually homeowner-supplied (came in ~$0) — keep small allowance, flag.
- **HIGH SCATTER — real contingency 12-15%, get firm sub quotes first:** HVAC (-49/+47/-27), Electrical (-12/+38/-15), Masonry/Fireplace (-21/+138/-12), Site (-28/+9/+75), Flooring/Tile (-3/-11/+63), Cleanup, Glass.
- **PREDICTABLE (2-3% buffer):** Plumbing (0/-10/-3), Windows & Doors (+11/+7/+8), Insul & Drywall (mostly small).
- **VOLATILE — do NOT bank it:** FRAMING LUMBER. Hernandez ran HIGH ($16/SF), Darwish came in **-$55k / -48% on market timing**. Same line, opposite directions. Budget conservatively, **DATE-STAMP the rate**, treat a good buy as found contingency (not the baseline). This supersedes the earlier "bump framing lumber to $15" — it's market-driven, not a fixed rate.

## Other 3-job notes
- **All-brick masonry budgets WELL at the category level** (Darwish 17-Masonry $68.6k->$60.6k, -12%). The "+$20k masonry" in the post-mortem was a stone sub-line / scope creep, not the brick rate. Brick instinct is sound; risk is uncaptured stone CHANGE ORDERS — sign them immediately.
- **Supervision/business-overhead is budgeted as a COST line on the bigger jobs** (Hernandez ~$42k, Darwish ~$43k = ~6% of cost) but $0 on Roberts (carried in margin). Inconsistent — pick ONE convention per estimate and don't double-count with the 25% margin.
- **Accuracy scales with size/complexity:** scope-adjusted error -1.1% / +0.9% / +6.2%. The big high-end 2-story was genuinely harder; widen the contingency as $ size and finish level climb.
- Darwish warranty/QC drag (re-tiled shower, re-stained stairs, granite redo, gutter-guard leaks) = rework cost not in any estimate — a tighter-sub-QC issue, flag as build risk not estimate line.

## Rate refinements from the Darwish takeoff (apply on HIGH-END / brick jobs)
- **All-brick (full masonry veneer): use ~$15-16/SF installed**, not $13. A blind takeoff at $13/SF x 4,300 SF undershot the actual masonry by ~$7k on a 2-story all-brick. Brick area on a 2-story is denser than it looks (walls x ~20' + minimal gables on a hip roof).
- **HIGH-END finish UP-TIER — the mid-grade template rates run low on luxury jobs:** Paint/wallcovering ran well above $3/SF (Darwish paint cat $25.6k vs a mid-grade ~$19k calc). Flooring/tile, carpentry/counters, and plumbing fixtures all tier up too. On a clearly high-end job, bump finish allowances ~25-40% over mid-grade and FLAG.
- **High-end windows: don't over-price them.** A blind pass at $650-700/window over-shot 47 luxury windows by ~$11k vs actual — big tall windows aren't linearly pricier. Treat window unit cost as ~$550-650 even on high-end unless a premium brand is specified.
- **Two-story slab + framed 2nd floor:** framing basis still = total-under-roof for lumber+labor; ADD engineered 2nd-floor (floor trusses) = 2nd-floor SF x ~$9. Roof footprint = FIRST-floor footprint+garage+porch (2nd floor is under the same roof), x pitch factor (Darwish all 6:12 = 1.118).

---

# Data point #4 — Waddell (560 River Rd, Jasper Co.) — FIRST TRUE COLD TEST
Single-story slab farmhouse, 1,882 heated / 2,967 under-roof, Hardie B&B+lap, architectural shingle (12:12-dominant), wood-burning fireplace, well+septic, 80' CONCRETE drive. Built blind from plans+intake, number committed BEFORE seeing budget. Orig $340,839 / Revised $346,689 / **Actual $336,100**.
**Result: direct construction cost landed -2.0% vs original budget, -0.5% vs actual** (apples-to-apples). The only real overage was a structural plug: assumed $40k supervision when this job carried $19,525. The takeoff itself was on the money cold.

## Lessons (apply going forward)
- **SUPERVISION / business-ops is NOT fixed — ASK IT per job.** Across 4 jobs: Roberts $0 (in margin) / Hernandez $41.6k / Darwish $43k / Waddell $19.5k. Never plug $40k. Ask Jason, or use ~6% of cost and FLAG. This was the single biggest miss on the Waddell cold test.
- **FLOORING & TILE runs ~$20k on a ~1,900 SF home, NOT ~$11k.** Cold pass at LVP $5.25 + sparse tile was HALF actual ($20,238). Granite-everywhere clients tile more (baths fully tiled, bigger showers) and LVP grade is richer. Bump flooring/tile ~+60-80% over the bare LVP calc.
- **Carpentry + cabinets + countertops together ≈ $32-34k** on these (granite all tops + farmhouse trim), not ~$28k. Trim carpentry alone is bigger than a base+casing calc — budget ~$10-14k just for trim labor+material.
- **Electrical is HIGH-SCATTER, both ways:** Hernandez ran $8.5+/SF, Waddell ran ~$7/SF ($18k actual on 2,439 HG-SF). Don't auto-use $8.5; mid-grade Jasper slab ~ $7/SF.
- **Exterior Hardie is often pre-finished (ColorPlus) — less exterior paint.** Cold pass at $2/SF exterior overshot; Waddell paint actual only $8.4k. Confirm pre-finished vs field-paint in intake.
- **WINS that held cold:** steep 12:12 shingle @ ~$3/SF turnkey nailed actual ($14.1k) and beat J&J's own low original; $14/SF conservative lumber (Aug-2025 buy) landed $59k vs $56k actual; HVAC, windows, plumbing, glass, foundation, appliances all within a few %. **Zero-trap budgeting (landscaping+punch @ $4k each) beat J&J's own original budget** — both lines overran to $13.3k/$6.3k.
- **Across 4 jobs the cold/blind takeoff direction is reliable; residual error concentrates in FINISH lines (flooring, carpentry/cabinets) running light, and SUPERVISION being a guess. Fix: bump finishes, ask supervision.**

## ⭐ MODEL UPDATE (supersedes all earlier supervision guidance) — confirmed by Jason
**Supervision / business-operations is NO LONGER a cost line. In Jason's current model it lives INSIDE the margin + overhead.** So:
- **COGS / builder cost = TRADES ONLY.** Do NOT add a supervision, coordinator, or business-ops line to the cost. (Older jobs Hernandez/Darwish/Waddell carried it as cost line 02 — that's the OLD model; ignore it for new estimates.)
- **Sell = trades-only direct cost ÷ (1 − margin%).** The single margin layer (Jason's 25%) now covers supervision + overhead + profit together. Still ONE layer, per-line markup zeroed.
- When grading a cold estimate vs an OLD-model budget, compare against the budget's trades-only total (Original minus the 02-Business Ops line), not the grand total.
- **Flag for Jason (his call, not the estimator's):** because the 25% now also absorbs supervision (~6% of cost) that used to be separate COGS, his NET profit inside that 25% is ~19%. If he intends 25% to be true profit, the margin % may need to rise. Don't assume — surface it.

---

# Data point #5 — Grotsky (481 Lakeshore Dr, Jackson GA, BUTTS Co.) — FIRST WALKOUT BASEMENT + FIRST DEMO
Jackson-Lake walkout: 1,848 heated (1,324 main + 525 upper) over a **1,325 SF unfinished walkout basement**, 650 SF covered deck, 387 SF basement patio. Poured 8" concrete walls (~103 LF, 9'), vinyl siding (shake+lap+B&B), 30-yr shingle (10:12 + 3:12), 42" ventless gas FP, **existing public water meter (no well) + new septic w/ ejector pump**. **An existing house W/ basement was demolished first** (figured off the red site-plan overlay: ~960 SF L-shape + deck/patio/porch/steps). OLD-MODEL job (supervision is a cost line). Actuals pulled from **QuickBooks** (not Buildertrend).
**Cold result: +3.9% over with HVAC in, but the FAIR read is −2.7% UNDER once the one-off self-performed HVAC is normalized out of both sides** ($412,034 est vs $423,649 actual, ex-HVAC). Actual sell $515,548 / COGS $463,356 / supervision (02) $38,528 = **7.6% of sell** / net income $48,040 (**9.3%** — old-model job run thin). ⚠️ **OLD JOB — do NOT reset current rates (esp. drywall) off these actuals; pricing has risen since.**

## Line lessons (corrected per Jason)
- **HVAC STAYS IN EVERY ESTIMATE.** The $450 actual was a ONE-OFF — this customer owned an HVAC company and self-performed. My $28.6k HVAC was CORRECT; it just doesn't count against the grade here. Do NOT make this an "ask if HVAC is owner-supplied" rule — keep HVAC fully budgeted every job.
- **J&J has NO demo cost code → demo books to EXCAVATION (03.05).** The $17,966 "Excavation" line IS the demo. My demo $22,500 vs ~$17,966 actual = **+25%** (fine for a first demo; trim slightly next time). When reading J&J QBO actuals, treat the Excavation line as demo/sitework, not pure dirt-moving.
- **DRIVEWAY: never assume the existing drive is reused — actual concrete driveway $20,488 (I carried $1k).** Even with an existing drive on site they rebuilt it. Budget a real driveway every time unless Jason says otherwise. −$25.6k miss (deck+driveway). [Real miss — keep.]
- **WALLPAPER is a real line on these (+$10,240); paint+wall ran $19,700 vs $5,544 est.** Don't zero finishes just because siding is pre-finished vinyl. Add a wallpaper/accent allowance and keep interior paint full. −$14.2k. [Real miss — keep.]
- **MASONRY ~$9,295 even on a "vinyl" house** (stone fireplace/skirt/water-table). Carry a masonry-labor allowance even when siding is vinyl. −$8.3k. [Real miss — keep.]
- (Drywall actual $4,500 looked low vs my $12,150 — but this is an OLD job; do NOT lower the current drywall rate off it.)
- **Frame lumber actual $41,449 vs my $32,487; electrical actual $32,010 vs my $21,596.** Note these are OLD-job actuals vs a current-rate estimate, so don't over-read the gap — but directionally consistent with "lumber is volatile / electrical scatters high." Don't rebase current rates off an old job.
- **Flooring & tile −$7.9k light** (finishes run light cold — persistent pattern). Plumbing/septic +$9.3k over (I double-padded septic+pump; actual septic one line $12,850).
- General/permits: my soft costs (engineering, survey, erosion-control plan ~$8k) are NOT in QBO COGS on this job — they're carried in supervision/overhead/pre-con. When grading vs QBO, don't expect plan/survey/engineering in COGS.

## ⭐ STANDING RULE (Jason) — T&G ceilings over ALL covered porches/decks/patios
**Any roof over a patio/deck/porch ALWAYS gets tongue-and-groove ceiling at $5.50/SF.** Add it every time there is covered outdoor SF (here: 650 SF covered deck → ~$3,575). Use the "Porch Ceilings" line at $5.50/SF — never skip it.

## Walkout-basement takeoff notes (first data point)
- Foundation poured-wall LF comes straight off the WALL SCHEDULE ("8" concrete stem wall" totals); walkout = ~3 sides concrete + lake side framed. Use the template "Walkout Basement: 9' Poured 8" Concrete walls" assembly. Foundation+concrete cold = $38,234 vs actual $39,872 (**-4%, nearly dead-on**) — the walkout foundation model is GOOD.
- Framing & Siding cold $87,057 vs actual $84,931 (**+3%**), Windows & Doors +2%, Roofing+gutters +19% — envelope modeled well.
- Site-plan SCALE was rescaled (nominal 1"=10' → measured ~4.64 pt/ft); always verify off a printed wall callout before measuring an overlay.

---

# Data point #6 — Anthony / Tierra (Lot 7 Bagley Rd, Forsyth, MONROE Co.) — FIRST MODERN / FIRST I-JOIST ROOF / FIRST MONO-SLAB-ON-SLOPE
Two-story modern, 2,980 heated (1,938 main + 1,041 second) + 486 garage + 382 covered rear patio. **Monolithic slab** (the 16"/8" "concrete stem wall" schedule entries are the integral thickened slab edges on the sloped lot — NOT separate walls). **Low-slope 1:12/3:12 roof framed as a FLOOR with I-joists** (open spans). **Standing-seam metal** roof. **Three claddings: stucco + Hardie lap + stone veneer.** Heavily glazed (~47 separated window units + 12' patio multi-slide + 16' double garage door). Well + septic, upper-mid finish, **full spray-foam insulation**. Built cold; actuals from **QuickBooks**.
**Cold result: trades-only cost −3.6% UNDER actual** ($511,626 est vs $530,869 actual trades-only; actual sell $595,864 / COGS $541,927 / supervision $11,058 = 1.9% of sell / net $51,094 = 8.6%).

## WINS (held cold on a brand-new style)
- **Monolithic slab −8%, standing-seam roof −7%, site −4%, insul+drywall −8%, final grade −1%** — near dead-on. Slab + metal-roof models solid.
- **Heavily-glazed window count held: +12%** (~47 units @ $675). Modern glass-wall unit pricing was close — don't panic on glazed moderns.

## MISSES → fixes (modern-specific)
- **CLADDING −51% (the big one).** Stucco + stone are MASONRY-priced and ran far higher: actual Hardie siding $26,699 + masonry (stucco/stone) $26,840 = $53,539 vs my $26,200. **Use stucco ~$14-16/SF installed (Jason approved $15.00/SF 2026-07-27), stone veneer ~$25-30/SF all-in (not $16).** ⛔ The "Hardie ~$7-8/SF on a modern" figure is **SUPERSEDED — see data point #60**: measured turnkey Hardie lap is $2.50/SF and the apparent shortfall was missing trim lines, not a low rate. On multi-cladding moderns the cladding total is still ~2x a vinyl/lap job, but reach that total by measuring every trim run, not by inflating the field rate.
- **FRAMING +22% OVER even with the I-joist done right.** Avoided the rafter+I-joist double count, but engineered-floor I-joist ($10.46 blend, roof @ $11) + $11 walls-lumber summed to $99k vs actual $81k. **Dial the I-joist roof rate to ~$8-9/SF.** Jason's "don't make framing too high" warning was right — still came in 22% hot.
- **SEPTIC/UNDERGROUND bigger on a new lot:** septic $22,000 + underground water/sewer $14,770 = ~$37k vs my ~$19k. Budget well+septic+underground ~$35-40k on a fresh lot; sloped/engineered septic runs $20k+.
- **DRIVEWAY under AGAIN (−56%, actual $17,789).** 2nd job running I under-budgeted concrete drive — carry ~$15-18k, stop assuming cheap.
- **Finishes light AGAIN:** trim/cabinets/counters −30% (cabinets $17,778, modern flat-stock trim), flooring/tile −38% (tile labor alone $14,500 — moderns are tile-heavy). Bump finish allowances harder on modern/upper-mid.

## ⭐ HVAC "+112% over" was NOT a miss — it's SPRAY FOAM (Jason)
This house was **full spray-foam insulation**, which tightens the envelope and **cuts HVAC to ONE system** (actual HVAC $15,467). My 2-system assumption (batt-insulation logic) is what was wrong. The takeaway is a RULE, not a scatter:

## ⭐ STANDING RULES (Jason) — Insulation / HVAC / Crawlspace
- **Default insulation now = SPRAY FOAM at the roof rafters + BATT in the walls** (sometimes spray foam the walls too — ASK in intake). This raises the insulation line above batt-only rates.
- **Spray foam lets HVAC size DOWN.** A ~3,000 SF home on full spray foam = **ONE system**, not two. Don't auto-spec 2 systems by SF — check the insulation spec first. (This explains Anthony's HVAC.)
- **Crawlspace jobs are almost ALWAYS encapsulated** — add a crawlspace encapsulation line (sealed liner / conditioned crawl) on every crawl job.
- Intake additions: (1) insulation spec — spray-foam roof + batt walls (default), or full spray foam? (2) on crawl, confirm encapsulation (assume yes).

## Reading note for QBO moderns
Multi-cladding jobs split cladding across **05.10 Siding (Hardie) AND 17 Masonry (stucco + stone)** — combine 05-siding + 17 when grading cladding; don't read either alone. Drywall held fine at $1.35 here (newer job) — confirms NOT to permanently lower the rate off the old Grotsky job.

---

# Data point #7 — Guarino (Lot 11 River Cove Meadows; NEWTON Co) — 2nd MODERN, FIRST ALL-METAL / EXPOSED-INDUSTRIAL / FIRST GRADED AGAINST JASON'S OWN ESTIMATE
Single-story MODERN, 2,637 heated + 1,204 CONDITIONED garage + ~347 covered porch. **Monolithic slab** (thickened edges; "12in/4in stem wall" = slab turn-downs). **Low-slope ½:12 & 1:12 roof framed as I-joist floor.** **Standing-seam METAL roof AND walls** (-> $0 exterior paint). **OPEN-CELL spray foam.** **Exposed structure throughout main + garage** (no ceiling drywall; I-joists/ducts/foam sprayed black). **Stained concrete floors.** **2 HVAC + master zone damper** (garage conditioned). Public water + new septic, 1,000-gal buried propane + 2 gas ranges. High-end.
**Cold takeoff vs Jason's written estimate: my line-subtotal $734k vs his $728k = +0.8% (raw +2%). Dead-on total, large offsetting category errors.** After reconciling with his QUOTES/measures/corrections, reconciled cost = $692,669; estimate subtotal w/ 15/7/8 markup = $753,317.

## ⭐ MARKUP MODEL — CONFIRMED FROM JASON'S ACTUAL ESTIMATE (supersedes the "zero per-line markup / single 25% layer" note in #4 for how to BUILD the estimate)
- **Estimate lines carry PER-LINE markup by type: Material 15% / Labor 7% / Subcontractor 7% / Equipment 7% / Allowance 8% / Fee 15%.** (Buildern import "Markup" column = the $ amount = base × type%.)
- **Overhead/Profit (his 20%) AND Contingency are applied in BUILDERN'S SUMMARY SECTION — NOT as estimate line items.** Do NOT add an O&P line or a Contingency line to the estimate. Leave all cost, waste, and per-line markup only.
- His actual Guarino summary: Builder Fixed Cost + Allowances (=raw) + Markup (per-line) + Overheads (20%) = Total. No contingency line on that sheet (he adds it in summary when he wants it).
- Net effect still ≈ his target margin; the structure is what changed. ALWAYS output the estimate this way now.

## ⭐ RATE / METHOD corrections (Jason confirmed)
- **HVAC ~$68k QUOTED. Driver = exposed/open rafters force ALL HARD SPIRAL DUCT (not soft flex) -> duct ~$32.6k.** RULE: on exposed-ceiling/open-rafter builds price hard spiral duct (big premium); a 2-system + conditioned-garage modern runs ~$65-70k. Don't apply "spray foam -> 1 system" size-down when 2 systems / conditioned garage / exposed duct specified.
- **Standing-seam METAL roof = $9/SF (Jason)** + **15% metal-roof waste** on roof area. (His own sheet had $5.50 = LIGHT.) Roof framing also quoted.
- **INSULATION = OPEN CELL is J&J default, vendor ~$1/SF (walls $0.98, roof $1.27).** SUPERSEDES earlier "spray foam raises insulation"/closed-cell pricing. Closed cell only if specified. Open-cell roof deck can be exposed + painted.
- **DRYWALL method (J&J standard): walls = Σ(room interior perimeter × ceiling height); ceilings = floor SF; total = walls + ceilings.** Use REAL per-zone heights (Guarino main house 15.5 ft [17 front/14 back], garage ~10 ft). NEVER use a heated-SF multiplier (my cold 8,400 vs real ~17,900). Exposed-ceiling jobs: NO ceiling drywall -> black-coat the exposed structure instead (heated+garage SF @ ~$3.5).
- **Mono slab — thickened edge = EXTRA CONCRETE + REBAR only; NO separate footer LABOR** (the monolithic slab labor covers forming/pouring the thickened edge — you don't form & pour a separate footer). Carry: flat-slab concrete (~0.0151 yd/SF) + additional thickened-edge concrete (~+0.006 yd/SF) + edge rebar (+ grade beams if any). Still pad foundation (runs over). [Corrected by Jason — earlier "add 445 LF @ $20 footer labor" was WRONG for a mono slab.]
- **Pre-con soft costs (Architectural Plans, Engineering & Surveys, Boundary Survey, Erosion-Control Plan) ARE COGS line items** — NOT overhead. BUT they're sometimes already done, so they don't always need to be carried. **ASK in intake which to include** (see Step 0). [Corrected by Jason — earlier "not COGS / in overhead" was WRONG.]
- Metal WALL cladding ~$8/SF on GROSS area (he used 4,682 SF gross). Accent: carry a small stone/masonry line even on all-metal modern (~282 SF here).
- **Hardie lap (fiber-cement) rate UPDATE: $3.15/SF** (was template $2.50), effective Jun-2026.

## Cost codes / output format
- J&J's Buildern cost codes (file: Downloads/"J & J Custom Homes, LLC - Cost Codes.xlsx") use codes like 04.15 / 05.05 = my template's E codes with leading zero (4.15 -> 04.15). Map by code -> Cost Code Title + Group. See **reference/buildern_output.md** and **reference/waste_factors.md**.

---

# Data point #8 — Lyndall (Kristen Lyndall) — FIRST GRADE OF JASON'S OWN SIGNED CONTRACT vs QBO ACTUALS
**COMPLETED AUGUST 2025** — ⚠️ ~10 months stale vs Jun-2026 pricing. **Where Lyndall came in UNDER, do NOT lower current rates off it — material/labor have risen since (Jason's explicit caution).** Under-bids here only get MORE relevant (pad harder); unders are likely Aug-2025-cheap, not a current-rate signal.
**2-story rural mid-grade**, ~4,950 heated / ~5,491 under-roof / ~4,400 SF main-floor slab. **Monolithic slab** (16x16 mono footings, "for main house, porch and garage"), **well + septic** (city couldn't set a water meter -> went to well; main water-line item zeroed in contract), buried 500-gal **propane** + 2 gas ranges, **FULL SPRAY FOAM (entire house)** — contract budgeted R-13 batt but it was upgraded to full spray foam (explains insulation +17%). **2 HVAC systems** — correct here NOT because of insulation but because it's a large ~4,950 SF 2-story with TWO separate living areas (two kitchens) needing zoned/independent units; spray-foam-→-1-system does NOT override a big two-living-area layout. Board-&-batten Hardie + 30-yr shingle, **structural steel** beams, 5+ beds. Modest finishes (single-hung vinyl no-grid windows, LVP, builder fixtures). OLD-MODEL contract: markup = Overhead 9% + Builders Fee 9% + Super 5% + Coordinator 1% + Insurance 1% = **25% on cost**. **Supervision was a COST line here (old model) — J&J NO LONGER carries supervision as a line item; it's now in margin/overhead (confirms data point #4 model update). Don't count Lyndall's $28k supervision against current estimating.**
**This data point is NOT a cold-engine test** (the plan PDF was image-only/no text, so no fresh takeoff). It grades **Jason's own signed-contract budget against the QBO Project-Profitability actuals** — i.e. where J&J's *own* estimating runs light. Files: Downloads/Contract.pdf, Downloads/"Projectprofitability (2).pdf". Recon workbook: Downloads/"Lyndall - Budget vs Actual Reconciliation.xlsx".

## The numbers (tie-out exact)
- Contract: direct-cost subtotal **$565,811.91** + 25% markup ($142,810.93) = sell **$708,622.84**.
- Actual: income **$706,161.48** (net change orders ~ -$2,461, basically flat) / **COGS $609,094.25** / gross profit **$97,067.23 (13.7%)** / net income **$94,472.96 (13.4%)**.
- **Direct-cost accuracy (apples-to-apples):** pull the markup-bucket soft costs that landed in COGS (Supervision $28,147 + Insurance $1,276 + job-Overhead $660 = $30,083) out of actual COGS -> actual direct **$584,463 vs bid $565,812 = +3.3% over.** Tight at the TOTAL level.
- **But margin still eroded ~$45.7k** (planned 20.2% of price -> actual 13.7%): trade overruns +$18.7k, plus real Supervision/soft costs hitting the job ledger that the % markup was "supposed" to cover. The 9% company-overhead allocation mostly stayed in the job as retained margin (only $660 booked to job), which is the only reason net held at 13.4%.

## ⭐ Category variance — where J&J's OWN bid ran light (the calibration gold)
The +3.3% total HID big compensating category errors. Systematic UNDER-bids to fix:
- **SITE / EXCAVATION / FINAL GRADING +427% — THE BIG ONE ($6,500 bid -> $34,225 actual).** Final grading ($15,882) was essentially NOT in the bid; dirt/gravel ($11,343) + excavation ($7,000) under-carried. This is the chronic "Site comes in UNDER" drift (Roberts -28%, Grotsky +75%, Anthony) but here it's the largest absolute miss. **RULE: carry a real sitework package — final grading ~$15k + dirt/gravel + excavation; never let Site total fall to ~$6k. Final grading is its own line (19.05), do NOT fold it into rough grade.**
- **PAINT +78% ($13,953 -> $24,766 ≈ $5.00/heated SF all-in).** Paint bid badly light AGAIN (finishes-run-light pattern, every job). **Bump interior+exterior paint to ~$5/heated SF.**
- **DOORS & WINDOWS (ext) +47% ($29,760 -> $43,698)** — windows materials $19.2k + garage doors $15k ran hot.
- **ENVELOPE / SIDING +40% ($32,856 -> $46,009)** — board-&-batten Hardie + labor. Matches Anthony cladding-light pattern; bump Hardie B&B labor+mat.
- **(Prices rose since Aug-2025 — these under-bids are if anything WORSE at today's rates. Pad Site/grading, Paint, Siding, Doors&Windows harder.)**
- Also over: Masonry/stone +29%, Tile +22%, Trim/finish-carpentry +20%, HVAC +14%, Gutters +43% (chronic underbid).
- **Insulation +17% ($8,847 -> $10,363) is NOT a rate miss — the house was UPGRADED from budgeted R-13 batt to FULL SPRAY FOAM.** Scope change, not estimating error.
- **NOT a miss: the 01.20 "Temp Utilities" $6,293 overage was a PROPANE TANK, captured by CHANGE ORDER (income side covered it).** ❌ Do NOT read this as a temp-power under-bid; the earlier "carry ~$6k temp power every job" rule was WRONG for this job — delete it. Temp power was fine.

## Offsetting OVER-bids (came in under — mostly allowance/selection + Aug-2025 pricing; do NOT lower current rates off these)
- **LANDSCAPING $12,750 -> $0 booked. RESOLVED (Jason): the CLIENT paid for landscaping OUT OF POCKET, specifically to help J&J cover overruns in other areas.** So it's a real done scope funded directly by the owner (off the J&J ledger) — a one-off goodwill offset, NOT a "don't budget landscaping" signal. Keep budgeting landscaping; just know it bailed out this job's margin.
- **APPLIANCES -57%** (homeowner-supplied pattern, 3rd+ time — keep allowance, flag).
- **ACCESSORIES -78%, CABINETS -28%, DRYWALL -20%, COUNTERTOPS -14%, FLOORING -11%.** Modest mid-grade selections AND Aug-2025 pricing. ⚠️ Do NOT rebase current cabinet/drywall/flooring/countertop rates down off these — prices have risen ~10 months since (same caution as the old Grotsky job).

## Lessons that GENERALIZE
- **The total can look great (+3.3%) while half the categories are badly mis-bid** — overs and unders cancel. The unders that bailed out the overs were partly a one-off (client self-funded landscaping to offset overruns) — don't count on that repeating. **Tighten the big-risk lines (Site/grading, Paint, Siding, Doors&Windows) rather than trusting the bottom line.**
- **Structural steel ($15.2k) lives OUTSIDE framing-lumber in QBO (05.20).** Bid folded it into the framing material package; when grading framing, add 05.20 back to 05.05+05.00 (combined framing was accurate, mono-slab foundation dead-on).
- **Mono-slab foundation model is GOOD again** (Foundation -3%, matches Anthony/Guarino) — keep it.
- **2 HVAC systems can be right even on FULL SPRAY FOAM** when the home is large + multi-living-area (Lyndall: ~4,950 SF 2-story, two kitchens). The "spray foam -> 1 system" size-down (Anthony) is for a single ~3,000 SF envelope; it does NOT override zoning/independent-unit needs on a big two-living-area house. Check layout, not just SF + insulation.
- **$/SF on a mid-grade rural 2-story runs LOW:** ~$123/heated-SF COGS, ~$143/heated-SF sell ($110.9 / $128.6 per under-roof SF) — vs Guarino's $281/heated. Finish level + SF-efficiency (2 kitchens, big simple boxes) drive $/SF more than size. Don't anchor mid-grade rural to the high-end moderns. (Aug-2025 $/SF — today's would run higher.)

## Category-drift scoreboard (8 jobs) — for realism padding
SITE/grading: now -28 / +9 / +75 / +427% — **single most volatile-light line; pad hard, itemize final grading.** PAINT: +9/+29/+20/+78 — **always pad, finishes light.** GUTTERS chronically light. FOUNDATION (mono) now reliably ±3-8%. Framing volatile (market). Appliances/landscaping = zero-trap both directions (ask, allowance, flag).

---

# Data point #9 — Martin (Maynards Mill Rd, MONROE Co.) — ⭐ FIRST TRUE CLOSED-LOOP COLD TEST (committed cold from plans, THEN graded vs actuals)
Single-story, **monolithic slab**, 3,093 heated / 975 garage / 922 covered porch = **4,991 under-roof**. Well+septic, 15-ac wooded rural lot, 10:12-dominant shingle, Hardie lap + B&B + stone accent, maple lacquer cabinets, batt insul (R-39/R-19) + 2 HVAC, gas stub (a fireplace was added later). Built **cold from a vector plan set** (no contract, no budget), number committed, **THEN** actuals released. ⚠️ **Job completed FEB 2025; I priced at Jun-2026 rates (~16 mo inflation embedded).**
**Result: my cold COST $669,308 vs actual COGS $603,951 = +10.8% OVER raw; ~+1% once deflated ~9% for the 16-month date gap.** Tight at the TOTAL — but the total HID ~6 offsetting category errors >$7k each (the recurring trap). Actual income $663,150 / gross 8.9% / $195 per heated-SF COGS.

## ⭐ The foundation-type trap (I FELL IN IT — Jason caught it)
Inferred CRAWLSPACE from a "FLOOR TRUSS FTR-16" callout + the generic "crawlspace venting / wood-joist girders / FLOORS R-19" boilerplate. **It was a MONOLITHIC SLAB** (sheet 4); the FTR-16 trusses were CEILING framing, the 16"/8" "stem walls" were slab turndowns. This is the exact Anthony trap. **RULE REINFORCED: never read foundation type from boilerplate or a truss callout — open the foundation sheet and confirm slab vs crawl explicitly; a "floor framing/ceiling framing" sheet title is ambiguous.**

## ⭐ METHOD/RATE errors to FIX (real, not date-driven — overs)
- **DRYWALL +82% — but the METHOD is right; my APPLICATION was wrong (Jason corrected this twice — do NOT use a multiplier).** I computed it as wall-schedule INTERIOR-LF ×2 + EXT-LF ×1, all at full 10' height + ceiling → **21,547 SF** vs actual ~12,000. The error was using the *schedule LF shortcut* and full height everywhere, NOT the perimeter×height concept. **CORRECT METHOD (standing, confirmed): measure EACH interior room's perimeter × THAT room's real ceiling height, summed over every room (closets/halls/baths included); ceilings = heated floor SF.** Do NOT substitute ~SF-per-heated-SF or any multiplier — Jason explicitly rejects shortcuts here. If a plan only dimensions major rooms, scale the rest off the plan geometry. (Villanueva done correctly room-by-room = 9,588 SF on 2,149 heated.)
- **CABINETS +95%.** $300/LF maple lacquer ≈ DOUBLE. Actual ≈ **$185/LF installed** (mat $18.2k + install $5k + hdw $0.9k for ~130 LF). Drop the cabinet rate hard for maple/standard.
- **FRAMING +24% even after cutting to $11/SF.** Actual = **$9.2/SF lumber + $5.35/SF labor** (Feb-2025) on under-roof. For a conventional truss single-story use **~$9.5-10 lumber / ~$5.5 labor**, NOT $11-13. (Jason flagged framing-over twice — believe him on conventional roofs.)
- **SITE +48% — I OVER-corrected the Lyndall lesson.** Padded final grading to $15k; **actual final grade was $1,250.** Don't blanket-pad final grade to $15k — it's high-scatter, not always-high. (Driveway itself: my $12.2k vs $13.8k actual = nearly dead-on AFTER the 150-LF fix.)
- **ROOFING +33%:** used $3.25/SF; actual shingle **$2.44/SF** turnkey. Roof AREA model fine; rate was high.

## Under-bids (consistent patterns — but Feb-2025 actuals, so don't lower current rates; pad these in CURRENT estimates)
- **FLOORING -42%** ($14k vs $25k; LVP labor alone $23.3k — labor ran huge). **PAINT -25%** (ran **$6.70/heated-SF**, even higher than Lyndall's $5 — bump paint to ~$6.5). **ELECTRICAL -24%** (ran **$11.3/SF** of heated+garage — high-scatter-high AGAIN; Hernandez/this both >$11). **WINDOWS/ext-doors -21%** (fir/double ext doors ran hot). **MASONRY -67%** (fireplace added + stone I'd zeroed).
- **Missed scope:** fence ($2.4k), irrigation ($2.2k), custom closet shelving ($5.5k, code 12.01), mirrors. Add small allowances for fence/irrigation on rural lots.

## ⭐ The meta-lesson (3rd job running)
**A near-perfect TOTAL is hiding big compensating category errors.** Martin +1% date-adjusted, but Drywall +82% / Cabinets +95% / Framing +24% canceled Flooring -42% / Paint -25% / Electrical -24%. **Stop trusting the bottom line; the per-line accuracy is still ±25-95% on the big trades. Tighten drywall method, cabinet rate, framing rate, and the always-light finishes (paint/flooring/electrical).**

## Driveway-off-a-plat lesson
Measured the gravel drive cold at **475 LF** off the recorded plat (scale verified 2.77 ft/pt via the 991' boundary AND the 97' house-width cross-check) — but the **actual was ~150 LF**; the plat **sites the house schematically**, much farther back than where it was actually built. **RULE: driveway length off a rural plat is unreliable — confirm actual house setback with the builder; don't trust the plat placement.**

## Date-stamp caution
Feb-2025 actuals. The OVERS (drywall method, cabinet/framing/roofing rates) are real and fixable regardless of date. The UNDERS partly reflect 2025 pricing — do NOT lower current rates off them; if anything current rates are higher.

---

# Data point #10 — Villanueva (Hwy 20, Conyers, ROCKDALE Co.) — 2nd CLOSED-LOOP COLD TEST (intake answered up front)
Two-story, **slab**, 2,148.6 heated (1,578 main + 571 second) / 534 garage / **431 unfinished bonus (shell)** / 664 covered porch / 3,778 under-roof. Public water + **septic**, **batt walls + blown attic**, **2 HVAC (priced)**, mid-grade, architectural shingle, **Hardie lap**, **electric fireplace**, wooded + **rocky soil**, 10-mo, 6 dumpsters, **concrete driveway (county-required, not the gravel the plan showed)**. ⭐ First job where I **answered the full intake up front** (Jason confirmed slab/water/insul/finish/etc.) before pricing — the correct workflow.
**Result: my cold COST $451,325 vs actual COGS $406,878 = +10.9% OVER** (same ~11% high as Martin — I have a consistent slight-overestimate bias). Actual income $419,134 / gross **2.9%** / net $9,274 — J&J priced this one razor-thin. $189/heated-SF actual COGS vs my $210. **⭐ Completed FEB 2026, priced at Jun-2026 rates (~4 mo apart = essentially CURRENT pricing). So the +10.9% is a REAL overestimate, NOT inflation** — the downward bias correction is valid at current rates, and the over-categories (cabinets/HVAC/electrical/appliances/supervision/landscaping) are genuinely over-priced in my model.

## ⭐ THE WIN — drywall room-by-room method VINDICATED
Measured **each interior room's perimeter × its ceiling height** (9' main / 8' second), all rooms incl closets/halls, + ceilings = heated SF + garage firewall → **9,588 SF**. Actual drywall **$13,796** ≈ ~9,200 SF → **my quantity within ~4%** (vs Martin's +82% with the multiplier shortcut). The +15% on dollars was rate ($1.65 vs ~$1.44/SF actual). **CONFIRMED: always measure room-by-room; never a heated-SF multiplier.** Also framing **$9.5/SF lumber** matched actual **$9.35** — the calibrated-down framing rate is right.

## Category errors that CANCELLED to +10.9% (the meta-trap, 4th job running)
OVER: **Cabinets +111%** ($185/LF too rich → mid/stock ~**$120-150/LF** installed; actual cab material ~$118/LF, install often folded into trim labor). **Appliances +179%** (homeowner-supplied AGAIN — carry small allowance, flag). **Landscaping +420%** (only sod booked $1,345 — owner did the rest; budget light + flag). **HVAC +55%** (2 systems too much for 2,148 SF — actual $14.2k ≈ 1 system + zone; **on <2,500 SF default 1 system + zone damper, not 2**). **Electrical +63%** (ran **$6.4/SF** here vs Martin's $11/SF — HIGH-SCATTER both ways; use ~$7/SF mid + flag, don't anchor). **Supervision +56%** ($32k carried vs $15.2k actual — scale supervision to job size/price, this was a thin ~$419k job).
UNDER: **Siding/Envelope −34%** (Hardie ran $28k — 2-story wall area + rate; bump Hardie). **Trim −35%** (runs heavy, $23k incl closet shelving $3.1k, trim mat $9.2k). **Utilities/Septic −31%** (**rocky soil → septic $21.2k** vs my $13k; pad septic on rocky/difficult lots). **Punch-out −52%** (actual $7,577 vs my $2,200 — punch runs high). **Gutters −50%** (chronic underbid, every job).

## Driveway — over-measured 2× off the site plan
Measured ~3,400 SF concrete ($25.5k); actual driveway **$13,094** ≈ ~1,640 SF. The survey's hatch/fill layering made the paved polygon fuzzy (I flagged it) and I over-measured ~2×. **Lesson: when a site-plan drive area is hatch-ambiguous, confirm paved SF with the builder.** Final grading is genuine SCATTER (Martin $1,250 / Villanueva $11,980) — don't anchor either way.

## Standing takeaways after 2 cold closed-loop tests (Martin, Villanueva)
1. **Consistent +11% high at the total** — apply a gentle downward bias / treat my cold cost as a ceiling.
2. **Per-line is still ±30-400%** and cancels — the total is partly luck. Tighten: cabinets (down), HVAC (1 system <2,500 SF), electrical (scatter, ~$7), appliances (HO-supplied), supervision (scale to job), septic on rock (up), siding (up), trim (up), gutters (up), punch (up).
3. **Drywall room-by-room and framing $9.5 lumber are now PROVEN** — keep them.
4. **Always answer the intake up front** (did it here) — clean scope, no foundation-trap.

---

# Data point #11 — Sailview / Fairview Cottage (Sailview Dr, MORGAN Co.) — IN-PROGRESS partial grade (completed trades only)
2-story cottage (BDG Plan 1969), SLAB-on-grade, 2,375 heated (1,969 main + 406 finished up) / 559 gar / 3,198 under-roof. Public water + septic, **spray-foam roof + batt walls**, **1 HVAC 3-ton (via Jason's 1-ton/800-SF rule)**, arch shingle, B&B+brick cottage cladding, electric FP, mid-grade, wooded lot. Graded my COLD number vs J&J's live budget tracker (`Downloads/House Budgets.xlsx`, Sailview tab; col D=Actual, E=✔completed). ⛔ Per hygiene rule, IGNORED J&J's Original/Revised (Jason said it's off/over-budget); graded ONLY ✔-complete trades with real actuals.
**Whole-job: my cold cost $425,166 vs their PROJECTED final $422,689 = +0.6%** (revised contract $485,604 / proj. profit 13%). Nearly dead-on at the total.

## ⭐ THE BIG FINDING — my bias is SPLIT by trade phase, NOT a uniform +10%
**Completed (structural/envelope) trades graded −16% UNDER** ($161,023 mine vs $191,733 actual). The "consistent +10% high" from Martin/Villanueva was the NET — driven entirely by FINISH trades (cabinets/HVAC/electrical/appliances) running OVER, which MASKED the structural UNDER. **CORRECT BOTH DIRECTIONS: bump structural/envelope UP, bring finish DOWN — do NOT apply a blanket −10% haircut.**
- ✅ **DRYWALL room-by-room −3% — PROVEN A 3RD TIME** (Villanueva +15%, Sailview −3%). Method locked; never a multiplier.
- ✅ Framing +9% (lumber $9.24/SF ≈ my $9.5; just trim the beam/deck adds). Windows +4%.
- 🔴 **SIDING −49% — MY WORST, MOST REPEATED MISS (3rd job). Jason: "don't play with my money, this ain't no guessing matter."** Actual 05.10 $26,086 vs my $13,266. **ROOT CAUSE + FIX (standing, also in SKILL.md Step 4):** (1) **MEASURE each cladding material off the ELEVATIONS by geometry — brick/stone/B&B/lap separately; DON'T GUESS the split.** (2) **GROSS area — do NOT deduct windows/openings; let them absorb as waste.** (3) **Hardie B&B field = $4.40/SF (mat+labor) FIELD ONLY** — not $3.15-3.50. (4) **ADD a separate, significant TRIM line:** corner boards, frieze, band boards, **column wrapping**, window/door casings, rake/eave trim (the part that "takes so much to measure" but is real money). (5) ⛔ **THE "lap ~$7-8/SF installed" FIGURE WAS WRONG — SUPERSEDED 2026-07-27, see data point #60.** It was a shortcut invented to avoid measuring elevations, and it inflated the lap rate ~3x to hide the missing trim lines. Measured turnkey lap is **$2.50/SF**. Brick/stone ~$14-16+/SF stands. Martin envelope +40%, Villanueva $28k (−34%), Sailview $26k (−49%) — I underbid every time by guessing area + omitting trim.
- 🔴 **ROOFING −36%** — steep cottage ran **$4.27/SF** turnkey (Martin was $2.44). Roofing SCATTERS by pitch/complexity: simple ~$2.5, steep/cut-up cottage ~$4+. Read the roof; don't anchor $2.75.
- 🔴 **SITE/excavation −31%** — wooded lot excavation $18,382 (I had $14k). Wooded/clearing sites run high.
- 🔴 **FOUNDATION −16%** (slab $26.3k), **EXT DOORS −44%** (arched front door + premium units $10.6k vs my $6k), **ENGINEERING −65%** ($4,250 soft costs vs my $1,500 — bump survey/engineering). Permit +57% (Morgan Co cheap).

## Scope notes (Jason confirmed)
- **LVP is HOMEOWNER-SUPPLIED** (HO doing own flooring) — REMOVE flooring from J&J scope (~$10.5k off my cold cost → ~$414.6k). HO-supplied watch list now = **appliances, flooring, landscaping** (ask each job).
- **Underground Sewage (07.15) = $0 because SEPTIC (07.20) is its own line** — don't double-budget underground sewage when on septic.
- ✔-but-$0 rows (Temp Utilities, Plumbing Materials, Mirrors) = trivial/unbilled; excluded from grade (asked, didn't assume).
- ⭐ **HVAC 1-ton/800-SF rule worked cleanly** (2,375÷800=2.97t→1×3-ton; budget $13k). HVAC actual-to-date $11,317 (not ✔ yet) tracks toward ~$13-14k — rule looks right.

---

# Data point #12 — Bethanie Burns (Jasper Co.) — MEASUREMENT-ACCURACY grade (my cold takeoff vs J&J's MANUAL takeoff)
Single-story farmhouse, NO garage, mono slab, 1,951 heated, well+septic, FULL spray foam, 1 HVAC (3-ton via 800-rule), arch shingle (6/8/10:12), all-lap + BRICK skirt, concrete patios (NOT decks). Graded my COLD-measured QUANTITIES vs J&J's manual takeoff (`Downloads/Measurements - Burns, Bethanie.xlsx`) — measurements are clean geometry ground-truth (legit to grade, unlike a priced estimate).

## ⭐ EXTERIOR CLADDING METHOD VALIDATED (the rebuild worked)
**Siding (lap+vertical) my 1,969 SF vs manual 2,057 (1,675 lap + 382 vert) = −4%.** On a line I'd missed −40 to −49% the three prior jobs, the triangulation method (plan+elevation, gross/openings-as-waste, materials separated) landed within 4%. KEEP IT. Also within a few %: heated 0%, covered porch +2%, **drywall room-perimeters +6%** (room-by-room proven again), cabinets LF ~0%, windows +1, wall-insul perimeter +5%.

## MEASUREMENT misses to fix
- 🔴 **MASONRY SKIRT −35% — I GUESSED THE HEIGHT instead of asking (Jason had offered).** I used 2.5' stone; actual = **~3.6' BRICK** (823.5 SF vs my 538). **RULE: ASK the skirt/wainscot height — don't eyeball it off a ¼"=1' elevation — and CONFIRM the material (brick vs stone).** J&J measures it as "Brick Veneer Ext" (area) + "Brick sill & frieze" (linear trim). Skirt here ≈ perimeter 229 × 3.6'.
- 🔴 **ROOF −12% AND I omitted the 15% shingle waste.** J&J measures each PITCH ZONE separately (6/8/10:12 = 772 + 2,376 + 496 = 3,644 raw) then **+15% shingle waste → 4,190 order**. My footprint×blended-factor (×1.31) undershot overhangs + the steeper blend. **FIX: measure roof by pitch zone (or use a higher effective factor ~1.45-1.49 incl. overhangs) and ALWAYS apply 15% shingle waste to the order qty.**
- 🔴 **Interior doors −5** (my 14 vs 19: 17 hollow + 2 pocket) and **countertops −27%** (my 55 vs ~75 SF). Count doors off the plan precisely; measure tops per room.
- House PERIMETER my 215 vs manual 229 (−6%) — slightly low; trace the full footprint incl. wing jogs.

## J&J manual-takeoff STRUCTURE to mirror (their line list = the right granularity)
Siding split horizontal/vertical (area, +10%); **Corner Boards** (LF, 8 corners × wall ht); **Fascia & Soffit** (LF); **Brick sill & frieze** (LF); **Ext beam wrap** (LF — porch beams); **Brick Veneer** (area, +10%); **Porch Ceilings T&G** (roof-area, +10%); **1x4 window trim** (LF); **Gable Brackets** (count). Roof by pitch zone +15%. Room Perimeters (sum, for drywall). Footers = perimeter +10%. Silt fence / construction driveway / permanent-power-from-pole as separate LF lines. Plumbing fixtures + ½-fixtures counted. This is the takeoff granularity to match going forward.

---

# Data point #12b — Bethanie Burns ESTIMATE-vs-ESTIMATE (my trued-up estimate vs Jason's Buildern estimate, SAME manual-takeoff quantities)
Both estimates use the identical manual takeoff, so every gap is PURE RATE. Jason's builder cost **$319,372** vs mine **$401,440** (+26%). ⚠️ Jason's estimate is NOT ground truth (his estimates slip light → over-budget jobs); actuals decide. Sorted:
- **MY CLEAR ERROR — SUPERVISION IS NOT A BUILDER-COST LINE.** I carried $24k supervision in cost; Jason's estimate keeps it in the **SUMMARY OVERHEAD**, not builder cost. **RULE: never put supervision in the estimate's builder-cost lines — it lives in the summary overhead/margin** (this matches the "supervision in margin" model; the QBO ACTUALS book it as a cost only for grading, add it back THEN). Removing it: my cost → $375k / +17%.
- **MY OVER-PADS (Jason likely right):** Plumbing mine $22.5k vs his $12.6k — **use ~$12-15k for a ~1,950 SF / 18-fixture mid house.** Septic mine $15k vs his $8.5k — **normal-soil septic ~$8.5-10k; only pad to $15-21k on ROCKY/difficult lots** (Villanueva). Permit: his rate **$1.50/SF** (I used $1.75).
- **JUDGMENT SPLITS — I'm higher AND Jason's actuals run light here (I may be right; do NOT drop to his estimate):** Exterior finishes mine $49.9k vs his $29.9k (his Sailview siding est was −49% vs $26k actual); Roofing my $3 vs his $1.96/SF (Sailview actual $4.27); Trim, Cleaning/PUNCH-OUT (Martin/Villanueva punch came in $7,577 each vs his $3,306 cleaning), Landscaping ($5k vs his $0 zero-trap). These are exactly the categories that put J&J over budget — my conservative pricing is likely closer to actuals.
- **WHERE JASON IS HIGHER (pad mine UP):** Foundation his $28.8k vs mine $21.2k (slab actuals run over — Villanueva $26k); Room finishes his $57k vs mine $49k.
- **AGREEMENT (validates the method):** DRYWALL mine $10,888 vs his $11,179 (<3% — room-by-room matches his manual takeoff AND his estimate). Gutters, HVAC, framing within a few %.
- **Net lesson:** strip supervision + trim plumbing/septic → ~$359k vs his $319k; the residual ~$40k is concentrated in his historically-light lines (exterior/roofing/trim/punch/landscaping). Don't blanket-match his estimate; fix the supervision-line error and the plumbing/septic pads, hold firm on the overrun-prone lines until the in-progress ACTUALS settle it.

---

# Data point #12c — Bethanie Burns VENDOR PO ACTUALS (real contracted sub prices — strongest ground truth)
12 subcontractor POs (PR-091) = actual contracted prices, same house/quantities. **Net on 12 subbed trades: my est $129k vs actual POs $110k = +18% over** — but wrong in BOTH directions (over-pads offset under-bids), not uniform. RATE TRUTH (use these):
- ✅ **DEAD-ON:** Well $12.5k (my $12k); Insulation $5,437 (my $5,667 — full spray foam ≈ $2.2/SF held); Electrical **$6.50/SF** (my $7, close — PO = SF price + can-light wiring + perm-power connect); Gutters **$6.50/LF** (my $8); Housewrap $865.
- 🔴 **MY OVER-PADS (fix down):** **SEPTIC = $8,150 normal Jasper soil** (my $15k = +84%; Jason's $8.5k was right — only pad septic to $15-21k on ROCKY lots). **PLUMBING LABOR = $8,300** (my $14k = +69%; plumbing rough+set labor is ~$8-9k for a ~1,950 SF/2.5-bath house, fixtures separate). **ROOFING = $1.92/SF** here ($8,053 on 4,190 SF; my $3.0 = +56%, Jason's $1.96 nailed it). Windows materials $4,600 (~$354/window budget vinyl; my $650 all-in was high). 
- 🔴 **MY UNDER-BIDS (fix up):** **SIDING + punch = $22,742 ≈ $11/SF** (my $7.50 = −25%; siding is the CHRONIC under-bid — even the "corrected" $7.50 was too low. **USE ~$11/SF installed incl punch.**). **HVAC = $15,942** for ONE 3-ton (my $13k = −18%; the 1-ton/800 rule got the COUNT right, the $ was low — budget a single 3-ton system at ~$16k). **EXT DOORS = $7,108** (my $5,300 = −25%; front double wood + 2 patio doubles run higher).
- ⭐ ~~**ROOFING IS HIGH-SCATTER ±2×:** Bethanie $1.92/SF vs Sailview actual $4.27/SF~~ **← SUPERSEDED by data point #13.** The "scatter" was an artifact of dividing by footprint/heated-SF; per *square of true surface* the rate is flat (~$174-175/sq). Roofing is now DECODED — see #13.
- **Meta:** my geometry is dialed (siding −4%, drywall <3% vs manual), but my RATES are wrong both ways. The +10% net bias from earlier was masking large compensating rate errors (septic/plumbing/roofing HIGH; siding/HVAC/doors LOW). Apply the sub-priced rates above, not a blanket bias.
- ⚠️ Working budget file (`Downloads/House Budgets.xlsx`) had NO Burns tab (tabs were other addresses) — asked Jason which address = Bethanie Burns / for the updated file before grading completion status.

# Data point #13 — ROOFING DECODED (Southern Expert Roofing actuals + J&J takeoffs/estimate, Burns + Peterson — June 2026)
The trade-by-trade rate-mechanism dive. Cracked roofing the way #12 cracked siding. **Roofing is priced by the SQUARE of true roof SURFACE — NOT $/SF-of-footprint.** Southern's two estimates side-by-side: shingle field **$174/sq (Burns, CT Landmark)** vs **$175/sq (Peterson, GAF Timberline HDZ)** — the per-square rate is FLAT regardless of pitch/complexity. Accessories separate: **Hip&Ridge cap $4.25/LF, Drip edge $1.85/LF (full perimeter), Pipe boots $50 flat.** Underlayment / 18" ice&water valley / ridge vent are BUNDLED (listed $0). Field shingle ≈ 85% of roof total.
- **Pitch is the whole cost driver, and you CANNOT eyeball it.** Surface = Σ(footprint zone × pitch factor): 5:12=1.083, 6:12=1.118, 8:12=1.202, 10:12=1.302, 12:12=1.414, **16:12=1.667**. Peterson read "12:12-ish" off a raster image → actually 5/12/**16:12** (16:12 = 54% of area); my raster guess (40-42 sq) came in **17% LOW** vs Jason's measured 48.97 sq. READ the pitch callouts; never assume.
- **WHY EST ≠ ACTUAL (Peterson — the real lesson Jason pushed for): the takeoff's 15% waste was DROPPED at the takeoff→estimate handoff.** Estimate priced the **raw 4,897 SF** surface at $1.98/SF = $9,707; with waste (5,631 SF × $1.98 = $11,162) it matches Southern's actual **$11,204 to 0.4%.** The $1,455 shingle shortfall = 100% the missing waste. **The $1.98/SF all-in rate was CORRECT** — the failure was a process drop, not a bad number. ALWAYS price the waste-loaded surface; reconcile estimate qty back to takeoff qty.
- **Waste is a FLAT ~10-11%, does NOT escalate with cut-up.** Southern actual over J&J measured surface: Burns 36.44→40.33 sq = +10.7%; Peterson 48.97→54.0 = +10.3%. J&J's blanket **15% is correct, ~4% conservative.** (My earlier "+26% waste on Burns" was wrong — artifact of MY under-measured geometry, see next.)
- **My cold geometry under-measured Burns surface by a UNIFORM −12.4%** across all 3 pitches (31.9 vs 36.44 sq) → not a pitch error, a **footprint/OVERHANG** miss (traced drip at 1-ft overhang; real ~2 ft). Measure overhang off the eave/cornice section — this is where my structural under-bid bias lives.
- **Metal: Jason does NOT use Southern for metal (too expensive) — separate vendor.** (Peterson estimate carried metal at 6.58 sq vs takeoff 3.34 sq ≈ 2× — flagged but parked at Jason's direction; focus was shingles.)
- Scope: Burns 6/8/10:12 simple gable, 36.44 sq measured. Peterson (Fairview Cottage) 5/12/16:12 steep+cutup, 48.97 sq shingle + 2.9 sq metal. Peterson 54 sq vs Burns 40 sq = pure pitch×footprint geometry, same rate/waste.

# Data point #14 — Jeffries / Roberts Residence (788 Jeffries Rd, Shady Dale; PR-051) — 1st BLIND siding cold-takeoff vs J&J takeoff + Southern PO actuals
Mixed brick/lap/B&B single-story, crawlspace, steep 12:12 gables. Blind test: did cold siding takeoff, THEN graded vs Jason's manual takeoff and Southern's contracted POs ($20,695 siding+trim + $2,475 punch = **$23,170 actual**, lump-sum POs). **Foundation trap caught AGAIN:** the foundation sheet literally reads "BACKFILLED SLAB / MONOLITHIC SLAB WALLS" but it's a CRAWLSPACE (Jason corrected) — never trust the sheet text. Crawlspace base = **brick water table** wrapping the house (brick = mason scope, not siding).
- ⭐⭐ **RATE CARD VALIDATED ON A 4TH HOUSE:** pricing JASON's (accurate) quantities with the model rates (lap $250, B&B $430, S&F $11/LF, T&G $540/sq, beam $23/LF, gable bracket ~$535) = siding+trim **~$19,700 vs Southern $20,695 (within 5%)** and punch **~$2,400 vs $2,475 (within 3%)**. **Rates are dialed.** The remaining error is MY quantities, not the rates.
- ⛔ **MY ENVELOPE-MEASUREMENT UNDER-BIAS, CONFIRMED & QUANTIFIED (~20% light) — now the #1 thing to fix in siding takeoffs.** My cold vs Jason's: Lap **−23%** (12 vs 15.6 sq), field total **−20%** (18 vs 22.4 sq), soffit&fascia **−22%** (250 vs 320 LF), corners **−24%** (80 vs 106 LF). These move TOGETHER = one systematic miss (I read less *building* than is there), not separate errors. What I got RIGHT (judgment is sound): B&B gables (−12%), gable brackets (3 vs 3 exact), porch T&G (−9%), and the brick/siding split (correctly excluded brick = 12.7 sq mason). **Root cause here: I over-discounted lap height for the brick water table — cut walls to 7.5' when Jason's lap implies ~9' (near full plate); the brick band is SHORT, mostly below grade.** Fix: clad height runs ~full plate (don't over-subtract for water table), and capture FULL perimeter (garage/wing walls). This is the SAME under-read as Burns roof (−12% overhang) and Wilson B&B — my structural/envelope geometry is consistently ~15-23% LIGHT; pad/re-measure it.
- **Method notes (J&J takeoff conventions):** Jason measures window trim as **LF of 1x4 (440 LF)**, not per-opening (Southern bills trimmed openings per-each — both reconcile in $). Combines "brick sill & frieze" into one LF line. Measures **brick veneer** (12.7 sq) on the takeoff even though it's mason scope, for the record. "Ext beam wrap" still lumps beam+posts (58 LF here).
- Scope: Heated 2161 + garage 707 + front porch 201 + rear deck 362. Front = full brick field + Hardie B&B gable; sides/rear = brick water table + lap field + B&B gables.

# Data point #15 — McPherson / "Foxtail Farm" (2-story Craftsman, 3-car garage, crawlspace) — 2nd BLIND siding cold-takeoff; the ENVELOPE FIX VALIDATED on area, new EDGE bias found
Southern Siding estimate #283239 (3/16/2026) = **$39,440** (siding only). Image-only (raster) redline set; 2908 SF heated (1822 main + 1086 second), garage 897, porches 515; 66'×67'8" L/U footprint; Hardie lap + B&B gables + **cultured-stone wainscot base (mason, excluded)**.
- ⭐⭐ **THE ENVELOPE FIX WORKED ON FIELD AREA — went from −20% (Jeffries) to +1.5%.** My cold field **~49 sq** vs Southern **48.35** (lap 40.75 + B&B 7.6) vs Jason **48.2** (raw, all-horizontal). What fixed it: **full 2-story height stack (~20'), full perimeter through the L-jogs, gross openings, exclude the masonry wainscot.** Field-area measurement is now calibrated. (My lap/B&B split was slightly off — over-called B&B 10 vs 7.6 — but total nailed. Jason lumps all siding as "horizontal," doesn't split B&B.)
- ⛔ **NEW BIAS FOUND — LINEAR/EDGE TRIM still runs 30-65% LIGHT, separate from the area bias (now fixed).** My soffit&fascia **320 vs 704 LF (−55%)**, corner boards **180 vs 517 LF (−65%)**, frieze 380 vs 530 (−28%), openings 30 vs 36, porch ceiling 5.1 vs 8.4. ROOT CAUSE: I anchored trim LF to FOOTPRINT PERIMETER (~280). But **soffit/fascia/frieze scale with TOTAL ROOF EDGE** (every eave + gable rake + porch/garage return + dormer ≈ **2-2.5× footprint perimeter** on a cut-up 2-story; here ~700 LF). And **corner boards scale with STACKED HEIGHT** (2-story corner ≈ 20', L-shape has 12+). FIX: measure S&F/frieze off the **ROOF PLAN edge**, not the wall perimeter; corners = count × full stacked height.
- **NEW/REFINED RATES (Southern, 3/2026):** Lap **PRODUCT/EXPOSURE drives rate** — Smooth 8.25"/7" exp = $250/sq, **Cedarmill 6.25"/5" exp = $350/sq** (narrower exposure = more boards = pricier). **Soffit&fascia rate by SOFFIT WIDTH + vented/solid:** 12" solid $13.50, 16" solid $14.25, 24" vented $16.50, 30" vented $18.50 /LF (the flat $11 was a narrow soffit; deep craftsman overhangs cost more — S&F was $10,850 of the $39,440!). **Frieze 4/4×10 = $6/LF** (vs 4/4×6 $4.50 — wider=more). **Porch soffit/ceiling can be Hardie panel $430/sq** (not only wood T&G $540). Garage wrap 16×7 $190 / 8×7 $130. Trimmed opening back to $65 (3/2026). Porch beam Hardie-wrapped $11/LF (confirmed again, 70 LF).
- **Method (Jason's takeoff):** classifies ALL siding as "Fiber Cement Horizontal" (no B&B split); measures masonry wainscot as "Brick Veneer Ext" (1,140 ft²) even when it's cultured stone; corner boards a single 517 LF line; window trim by LF (670 LF 1x4) not per-opening; "Ext beam wrap" lumps beam+posts (111 LF).

# Data point #16 — Leone Watkins (6000 Hwy 81 Loganville; "L-3574" turret 2-story) — 3rd BLIND siding test; I OVER-CORRECTED (field +30%, edge +30%) and MISSED crown moulding
Southern Siding #294726 (5/4/2026) = **$38,952** (siding only; punch separate, not provided). Image-only redline; big 2-story, TURRET, 3-car garage, very cut-up roof, LAP whole house + tiny shake/B&B accents, stone veneer on turret base + chimney (mason, excluded).
- ⛔⛔ **FIELD IS NOT "SOLVED" — IT'S VOLATILE. Honest correction to #15's claim.** Cold field went −20% (Jeffries) → +1.5% (McPherson) → **+30% (Leone, ~62 vs 47.7 sq)**. McPherson's bullseye was partly luck. **A big/complex/turret house does NOT mean more lap field** — turret + stone + big glass + porches mean Leone's lap (47.7 sq) ≈ McPherson's (48) despite looking bigger. I inflated on "big house = pad it." Don't blindly pad; the gross-openings rule already carries waste. Field swings ±30% on complex houses — DO NOT trust it unreviewed.
- ⛔ **THE EDGE MULTIPLIER IS A TRAP — there is NO constant.** Roof-edge ÷ footprint-perimeter was ~2.5× on McPherson but ~1.5× on Leone. I applied 2× and overshot S&F (650 vs 498, +31%), frieze (620 vs 490), corners (480 vs 312, +54%). FIX: **actually TRACE the eaves + each gable rake off the roof plan/elevations per house — never multiply perimeter by a fixed factor.** ("Edge > perimeter" was right as a direction; the shortcut multiplier is wrong.)
- ⛔ **MISSED SCOPES (add to siding checklist):** (1) **Exterior CROWN MOULDING — 680 LF @ $6.50/LF labor = $4,420 (11% of the job!)** "Endurathane Granada" cornice crown; historic/Victorian/Craftsman houses carry it — I didn't even have the line. (2) **Band board** (5/4×12 between-floor horizontal band) 120 LF @ $7.50. (3) **Shake accent** — don't take "lap whole house" literally; check gables for shake ($820/sq Hardie shake panel) / B&B accents.
- **Under-measured PORCHES** (this house is porch-heavy): porch beam 148 LF (I had 80, −46%), porch ceiling 7.9 sq (I had 5, −37%). ✅ **NAILED openings (50 vs 53)** and the lap/stone split.
- **RATES:** Lap by EXPOSURE not texture — Cedarmill **7" = $240/sq**, Smooth 7" = $250, Cedarmill **5" = $350** (5" exposure is the pricey one, not the texture). Hardie SHAKE panel **$820/sq**. Frieze 5/4×12 **$7.50/LF**; Band 5/4×12 $7.50. Corners double 5/4×6 **$4.50/LF**. Trimmed opening 5/4×6 w/ 2" cap **$68/ea**. Exterior crown (Endurathane Granada) **$6.50/LF**. Cantilever soffit 24" $9/LF. Porch beam Hardie $11/LF (148 LF). S&F here back to flat $11 (narrow 12"/8").

# Data point #16b — Leone RE-DONE piece-by-piece (no formulas) + the WASTE-CONVERTER lesson
Re-measured Leone honestly wall-by-wall (front 68'×20', rear 54'×20', sides ~45'×20'; perim 213') → **raw field ~43 sq.** Initially called myself "light" vs Southern's 47.7 — WRONG comparison. **My measurement is RAW surface; Southern's quoted squares are WASTE-LOADED (~10%).** Raw 43 × 1.10 = **47.3 sq ≈ Southern 47.7 (within 1%).** So piece-by-piece measurement is ACCURATE; the +30% formula run (62 sq) was the real error, and the "light" was a self-inflicted raw-vs-loaded comparison mistake.
- ⭐ **WASTE IS THE RAW→QUOTED CONVERTER. GRADE LIKE-TO-LIKE.** Measured field = raw. To match SOUTHERN'S QUOTE, add J&J 10% siding waste. To match JASON'S TAKEOFF quantity, compare RAW-to-RAW (his "Quantity" column is pre-waste; he applies 10% separately). Don't compare my raw to a waste-loaded quote.
- ⛔ **Waste does NOT fix the edge-trim gap.** My fascia/soffit ~400 LF; +10% = 440 vs Southern 498 — still light. That's the real eave-tracing weakness (can't trace every porch/bay/turret/dormer eave on a dimensionless raster), separate from waste. Only measuring every run fixes it.
- ⭐ **Side-width sanity check saved me:** auto-read right side at 81' (≈2×); caught it against floor-plan depth 46'6" → real ~45'. Always sanity-check elevation widths vs the floor-plan footprint.

# Data point #16c — Leone FASCIA/SOFFIT solved via ROOF-PLAN cross-reference (Jason's method)
My edge-trim under-read is FIXED by cross-referencing, not unfixable: **flat eaves off the ROOF PLAN** (true horizontal length — catches every bay/porch/turret/dormer eave the elevations hide) + **gable/dormer rakes off the ELEVATIONS** (true sloped length — roof plan drops the pitch). Leone: elevation-only S&F = 400 LF (−20% vs Southern 498); roof-plan eaves ~260 + elevation rakes ~200 = **~460 LF, within ~8% of 498.** I had wrongly concluded "can't trace eaves on a raster" — I just hadn't OPENED the roof plan (it was on p6, I'd missed it). ALWAYS pull the roof plan for fascia/soffit/frieze eaves. Complete siding method now: walls (elev + floor-plan hidden walls), gables (elev, separate triangles), flat eaves (ROOF PLAN), rakes (elev), raw × ~10% waste = Southern's quoted qty.

# Data point #17 — ENGINE BUILD: scale auto-calibration SOLVED (clustering, not nearest-neighbor) + PER-PAGE rule
The takeoff engine (`tools/jnj_takeoff.py`) now auto-detects pt/ft on ANY vector sheet, robust to busy floor plans — the blocker that beat the first build.
- ⛔ **OLD bug:** matched each dimension to the *single nearest* line segment. On a busy floor plan "nearest" grabs a wall, not the dim's witness line → junk (Wilson floor plans returned 10.97 / 3.31 / 2.30 pt/ft).
- ⭐⭐ **FIX = consensus clustering.** For every dimension TEXT, emit *all* plausible (drawn_span ÷ value) ratios from two independent signals — the dimension LINE the text sits on, AND the WITNESS-LINE PAIR straddling it — then take the densest cluster (the mode). The true scale is reinforced by dozens–hundreds of independent dims; junk scatters and never piles up. `calibrate_scale()` + `_cluster_mode()` + `detect_scale()` (self-aware verdict: high/good/review/low).
- **PROVEN:** Wilson floor plans now 17.99 (294 votes) / 13.55 (420) / 18.04 — clean standards where the old code returned garbage. Burns nails 1/4" (286 votes).
- ⛔⛔ **PER-PAGE RULE (Jason's warning):** SCALES DIFFER WITHIN ONE SET — Wilson is 3/16"=1' on p3/p15/p16 AND 1/4"=1' on p4/p6/p7/p8/p13/p14, same PDF. **Calibrate EVERY page from its own dimensions before measuring off it. Never carry one page's scale to another. Never assume.** detect_scale runs per-page by design; a page that won't independently lock gets flagged for Jason, not guessed. See [[feedback-verify-scale-per-page]].
- ⭐ **Rescaled-set (Jeffries) — measure with the cluster, NOT the textbook scale.** Jeffries clusters at 16.65/16.71/16.55 = 0.925 × 18.0 (its 3/16 sheet = 12.51 = 0.927 × 13.5): exported at ~92.5% of native. The recovered cluster ratio reproduces the real dims; snapping to 18.0 would make every measurement 8% too big. The 0.925 cross-sheet pattern is a SANITY CHECK only — it never supplies a page's scale or skips that page's own calibration.
- ⭐ **Scans correctly ABSTAIN:** Leone & McPherson (raster) → every page "none" (no vector dims) = the engine's signal to switch to the OCR/CV path instead of returning confident garbage. The engine knows what it doesn't know.
- NEXT BRICKS: (1) vector geometry extraction — footprint perimeter + slab SF for FOUNDATION (cleanest trade to prove measure-the-geometry on the now-solid per-page scale); (2) OCR/CV raster path; (3) per-trade measure+count templates. Each graded vs Jason's actual takeoff quantities.

# Data point #18 — FOUNDATION WALL actuals (GV Construction, Inc — Griffin GA) — Wilson basement, inv #1196 3/12/2026, $27,326
First foundation ACTUALS for engine calibration. "Wall only, not slab." Bill-to 515 Pope Trail, Covington GA 30014 = **Wilson JOBSITE** (confirmed by Jason; J&J office is 133 W Washington St Suite D, Monticello GA 31064). Perimeter match (~157 vs 156) corroborates.
- ⭐ **WALL PRICED BY HEIGHT × THICKNESS, $/LF (rate climbs with height):** 10'×10" & 10'×8" = **$105/ft**; 8'×8" = **$90/ft**; 6'×8" = **$80/ft**; 4'×8" = **$70/ft**. Wall steps with grade (walkout): 10' on buried side → 4' at daylight.
- **WILSON WALL QTYS:** 10' = **96 LF** (68 @10×10 + 28 @10×8), 8' = **21 LF**, 6' = **12 LF**, 4' = **27 LF** → **156 LF total wall**. Wall concrete labor+mat = $14,820.
- **FOOTING:** 2'×1' (24"w × 12"d) continuous = **$25/ft**; **156 LF** (= wall LF exactly, continuous under all wall) = $3,900.
- **REBAR:** 12" o.c. **$1.20/ft**, 4,220 LF = $5,064 (sub-supplied; don't measure — get from sub).
- **ACCESSORIES (per-each, from sub):** anchor straps $4/ea (43), sleeves $10/ea (6), pump truck rental $1,500/ea (2 — drives cost on deep/long pours), window blockout $200/ea, angle corner $50, rod chairs $60/box.
- ⭐ **SCOPE LESSON:** "foundation wall" 156 LF = **BASEMENT poured-wall perimeter only**, NOT full-building envelope (~207 LF). Garage sits on slab w/ turn-down (flatwork sub, no poured foundation wall). Measure the BASEMENT poured-wall outline for wall LF, not the whole footprint.
- ⭐⭐ **JASON'S FOUNDATION CONVENTIONS (confirmed):** (1) Wall qty = poured-wall perimeter × **FULL height** — he does NOT estimate the step-downs (sub invoices 10/8/6/4; takeoff just runs perimeter at full 10' = slightly conservative). **Never derive the step split.** (2) 156 LF = **poured walls ONLY**, excludes thickened/turn-down slab edges (those = flatwork). (3) Footer LF = wall LF (continuous). (4) **Two subs:** foundation-wall sub (footer+poured walls, GV Construction) vs **flatwork sub** (slabs + thickened edges) — separate line groups. => Foundation-WALL takeoff reduces to ONE measurement: trace the poured-wall (basement) perimeter. See [[feedback-foundation-takeoff]].
- ⛔ **MEASUREMENT STATUS:** scale verified per-page (p4 = 1/4"=1', 70 votes). Basement perimeter box-bound ≈157 LF ≈ 156 actual (confirms house + scope). BUT box-bound ≠ piece-by-piece trace (curve + steps), and per-height split (10/8/6/4) is NOT on these sheets (needs wall sections/grade). NEXT BRICK: polygon extractor to trace the basement outer-wall loop exactly + de-dup the double-line geometry.

# Data point #19 — ENGINE WIN: first trade measurement validated against actuals (Wilson basement foundation-wall perimeter)
The engine traced Wilson's poured-foundation-wall (basement) perimeter **automatically** and hit the actual.
- **Method (Brick 2, `trace_enclosed_region()` in jnj_takeoff.py):** render p4 at verified scale (1/4"=1', per-page) → isolate axis-aligned wall runs (drops the garage X-diagonals, text, dim ticks) → flood the interior, kill exterior → pick the left interior region (basement; garage X-zone is right) → close partition notches (~1.6 ft kernel) → trace outline.
- **RESULT: 155.9 LF (inside-face) vs 156 LF invoiced.** Visual overlay confirms it follows the real basement loop and correctly EXCLUDES the garage slab + curved porch (= poured walls only, Jason's scope). Centerline run is ~3-4 ft longer per loop, so report as ~156-159 LF, not a false-precise point. Basement interior area ≈ 1,372 sf (free-space; slab SF a bit more w/ under-partitions).
- ⛔ **What's Wilson-specific still:** the `clip` rect and prefer='left' were hand-set for this sheet. GENERALIZE next: auto-find the drawing region (exclude title/notes/dim margins) and let vision tag which enclosed region is the target. Core measurement is proven + reusable.
- ⭐ **Significance:** scale auto-detect (Brick 1) + enclosed-region trace (Brick 2) now chain into a real, validated quantity. Pair with the GV rate card (#18) → priced foundation wall. First trade end-to-end.

# Data point #20 — ENGINE: dimension-chain reader built (Brick 1c)
`read_dimension_chains()` / `overall_dims()` in jnj_takeoff.py. Pulls every dim label (line-level text, merges fractions; classifies H/V by writing direction), groups collinear labels into chains by SPACING CONSISTENCY (adjacent centers must be (v_i+v_j)/2*ppf apart), and cross-checks each chain's run-sum vs its drawn span (rejects chains where span_ck disagrees >4% — kills stray "16\"" o.c. notes that align by luck).
- PROVEN Wilson p4: recovers width 61'-4", depth 42'-8"/39'-11"; top breakdown 37'-8"+5'-2"+18'-6"=61'-4" (span_ck matches). p6 slab plan shows 70' wide / 62'-8" deep = patio extends past the 61'-4" house (flatwork extent).
- ROLE: reads EXACT labeled lengths the way Jason reads a plan; complements the pixel trace (Brick 2) — use chains to snap traced contour edges to true values (centerline-accurate perimeter) and to get per-run wall/segment lengths. Architects stack breakdowns on multiple dim lines; reader reads each line correctly, doesn't force-merge across lines.

# Data point #21 — SLAB / FLATWORK concrete model RECONCILED (Wilson, FFCI $12,099 = 67.2 yd @ $180)
Concrete supplier = Fowler Flemister (FFCI), ~**$180/yd**. **Builder buys concrete + pump trucks direct; flatwork sub provides all OTHER material + labor.** Wilson slabs = 2 pours: house slab (4/10, $8,529=47.4yd) + rear porch (4/13, $3,570=19.8yd) = $12,099 / 67.2 yd. (Statement is $-only; ÷ $180 = yd.)
- ⭐⭐ **JASON'S SLAB CONCRETE MODEL (now in `slab_concrete()`):** 4" slab over the full footprint, PLUS **full beam sections** for: **16"×18" thickened edge** and **8"×8" grade beams under interior walls**. Add **~8-10% waste/over-order**.
- ⛔⛔ **THICKENED EDGE RUNS ONLY WHERE THE SLAB EDGE IS *NOT* ON A FOUNDATION-WALL FOOTING.** Basement slab perimeter sits on the 156 LF poured wall → **NO thickened edge there.** TE is on the slab-on-grade edges only (garage + porch perimeters).
- ⛔ **COUNT THE FULL BEAM, not the extra-below-slab.** I first netted the slab out (16×14=1.556 cf/LF) and came in 27% low. Jason counts the whole 16×18 beam (2.0 cf/LF) + the 4" slab over the full area (minor overlap left in as conservatism). Same for grade beams (full 8×8 = 0.444 cf/LF).
- **WILSON RECONCILIATION:** flat 37.0 (2,996 sf: basement 1,372 + garage 889 + rear porch ~735) + edge 20.7 (≈279 LF garage+porch full perimeters) + grade beams 4.1 (≈250 LF interior walls, ESTIMATED) = **61.8 yd in-place × 1.08 waste = 66.7 yd = $12,008 vs delivered 67.2 yd / $12,099 (within ~1%).**
- ⛔ **Still to firm up:** interior grade-beam LF was estimated (250) — measure interior-wall run for precision; waste 8-10% is the swing factor. Rear porch = the slab at TOP of plan, 12' deep. Engine: `slab_concrete(area_sf, perim_edge_lf, grade_beam_lf, price_per_yd=180, over_order=...)`.

# Data point #22 — FLATWORK SUB rates + AREA VALIDATION (GEO Concrete, Wilson, $11,125, 4/14/2026)
Geo Concrete LLC (McDonough GA) = Wilson flatwork sub. Provides all material + labor EXCEPT concrete + pump trucks (builder-bought). Invoice $11,125:
- Basement + garage finish labor, **2,311 sqft** = $4,275 → **$1.85/sf standard finish labor**
- Tractor work (prep/grade) = **$300** flat
- Plastic, wire, rebar, form boards, chairs, scraps (materials pkg) = **$2,278** (~$0.75/sf of total slab)
- **Stamped & colored patio + mat rental** (rear porch, premium) = **$4,272** (~$5.80/sf over ~735 sf; ~$4/sf premium over broom finish)
- ⭐⭐ **AREA MEASUREMENT VALIDATED:** engine trace basement 1,372 + garage 889 = **2,261 sf vs GEO's stated 2,311 sf = within 2.2%** (inside-face; gross even closer). Independent confirmation of `trace_enclosed_region` — now corroborated by BOTH the concrete volume (#21) AND the flatwork sub's stated area. The slab-AREA trace is trustworthy.
- ⭐ **FULL WILSON SLAB COST:** concrete (FFCI) $12,099 + flatwork (GEO) $11,125 = **$23,224** + pump trucks (builder-bought, TBD). Stamped/colored areas carry a big premium ($4,272 for the porch alone — price stamped patios separately).
- ⛔ Still open: pump-truck cost for slab pours (builder-bought, not in either invoice); isolate stamped $/sf with a 2nd job (this one bundles mat rental).

# Data point #23 — PUMP TRUCKS + complete Wilson foundation/concrete cost
- **Pump truck = $1,500 each; ONE pump per pour.** Footer pour (1) + wall pour (1) = 2 pumps = $3,000 — **already in GV's foundation-wall invoice** (#18). Slab pour (1) = $1,500 — **builder-bought, separate** (NOT in GEO flatwork or FFCI concrete). So a basement house = 3 pumps total ($4,500): footer, wall, slab.
- ⭐ **COMPLETE WILSON FOUNDATION/CONCRETE (fully calibrated, 4 invoices):** Foundation wall+footer incl 2 pumps (GV) $27,326 + slab concrete (FFCI) $12,099 + slab flatwork labor+mat (GEO) $11,125 + slab pump (builder) $1,500 = **$52,050.** Whole trade measured off the plan + reconciled to real actuals. Foundation = first trade DONE end-to-end.

# Data point #24 — BLIND GENERALIZATION TEST: Holbrook foundation (5020 Watson Fain Rd, Loganville) — 2nd house, cold
2nd foundation, run cold to test if the engine generalizes off Wilson. Actuals: GV wall #1200 $35,829 (178 LF wall, mostly 9' @ $100/ft; footing 3'×1' @ $38 + 5'6"×1' @ $69; 2 pumps; "basement wall" + "retaining wall") + SRM ready-mix **67 yd 3000psi @ $167/yd + fiber = $11,938** (slab pour) + GEO flatwork **basement slab 3,122 sf @ $1.80/sf = $10,864** + slab pump. Foundation = slab-on-grade + thickened edges + PARTIAL poured wall (rear/retaining). 17-page set, 1/4".
- ✅ **SCALE GENERALIZES:** p5 slab plan auto-calibrated 1/4" (70 votes); p3 foundation-wall sheet had ~0 dims but bbox (82.0×62.1 ft) matched the 81'-11½" overall → confirmed 1/4". Per-page rule held: p4 returned shaky 19.36 → correctly flagged "review" (not used).
- ✅ **SLAB AREA generalizes AFTER a fix:** original `trace_enclosed_region` returned 1,600 sf = the largest ROOM, not the footprint (subdivided slab). NEW `trace_footprint()` (exterior flood-fill + dash/door sealing) → **2,954 sf vs GEO 3,122 (~5% low, inside-face).** Double-validated: SRM 67 yd over 3,122 sf = 7" effective, same as Wilson. Slab-area measurement now proven on 2 houses.
- ❌ **WALL-LF EXTRACTION FAILS:** p3 poured wall is a PARTIAL outline; summing axis-aligned segments grabbed section detail + hatching + dims = 774 LF vs 178 actual. Need layer/color isolation or vision-guided region to pull just the wall. NEXT BRICK.
- ⚠️ **Chain reader missed the 82' overall** (returned 35' sub-dim as max). Fix singleton/overall capture.
- ⛔⛔ **RATES ARE PER-JOB, NOT UNIVERSAL:** Holbrook GV 9' wall $100/ft (Wilson 10' $105), footing **3'×1' $38** (Wilson 2'×1' $25 — wider footing here), concrete **$167/yd SRM** (Wilson $180 FFCI). Flatwork finish $1.80/sf (Wilson $1.85 — consistent). MUST pull each job's actual rates from its invoices; don't carry one house's rates to another.
- VERDICT: scale ✅, slab area ✅ (2 houses), slab-concrete model ✅ transfers; wall-LF isolation ❌ + chain-reader overall ⚠️ are the open bricks. Engine improvement banked: `trace_footprint()`.

# Data point #25 — WALL-LF ISOLATION brick built (skeletonization) — Holbrook p3
Built the wall-isolation brick (the most-needed gap from #24; wall is the biggest foundation cost). `measure_wall_lf()`: isolate the poured wall as the LARGEST CONNECTED linework (drops section detail/notes/3D) → close double-line faces into one band → **skeletonize** (skimage) → sum centerline (axis steps=1, diagonal=√2).
- **RESULT: 162 LF vs 178 actual (~9% low)** — up from the naive-summing FAILURE (774 LF). Axis-aligned-only skeleton = 133 (misses angled returns); including diagonals (all ink) = 162.
- ⛔ **Remaining ~9% gap = judgment, not mechanics:** the long top diagonals (angled wall returns vs. the separately-billed "retaining wall" the GV invoice lists) + clip still semi-manual (must exclude the wall-section detail + title block). Tighten by: confirming which segments are poured wall vs grade/retaining, and a 2nd house.
- Dependencies added: opencv-python-headless, scikit-image. Engine now: scale → footprint area (`trace_footprint`) + room area (`trace_enclosed_region`) + wall LF (`measure_wall_lf`) → slab_concrete + rate cards.

# Data point #25b — wall-LF correction: diagonals ARE wall; 162 stable; the bottleneck is region-isolation + skeleton corner-rounding
Jason confirmed the long top diagonals on Holbrook p3 ARE part of the poured foundation wall (so including them = correct). Stable result with a clean hand-set clip (wall component bbox 70×27 ft): **162 LF vs 178 actual (~9% low).** The 9% is NOT missing wall:
- **Skeleton corner-rounding:** closing the double-line into a band + skeletonize cuts each right-angle corner short (~band_width/2). ~15 corners ≈ most of the 16 LF gap. Fix: corner/endpoint length correction, or finer band.
- **Region-isolation fragility:** extending the clip to be "safe" made largest-component grab the title-block border / section detail (188, 240 LF — wrong). A correct measure needs a clip that cleanly bounds the wall drawing (excludes title block + section detail + 3D + notes). **Auto region-selection is THE recurring bottleneck** across slab area AND wall LF — vision-steered (human picks the region) works to ~5-10%; full-auto doesn't yet.
- VERDICT: wall LF now measurable to ~9% (from a 774 failure), diagonals handled. To get under 5%: corner-correction on the skeleton + robust auto-region detection (the general engine gap).

# Data point #26 — AUTO REGION-SELECTION: vision-guided + clip-invariant measurement (the real fix)
Pure-geometry region detection FAILED (tried density-threshold, percentile, long-segment CC, densest-component): section details are denser than a thin wall outline, page borders span everything, dim lines bridge building->title block, and notes-text closes into a blob that beats the wall. The peripherals are geometrically indistinguishable from the drawing.
- ✅ **SOLUTION = the committed architecture: vision identifies WHERE, code measures.** `render_with_grid(page, out)` draws a labeled pt-coordinate grid; the model VIEWS it and reads the drawing bbox (excluding title block / section detail / 3D) — reliable because vision trivially separates them. That bbox is the `clip`.
- ✅ **Made the measurement INVARIANT to the clip** so the vision-read region needn't be precise: `measure_wall_lf` now drops small connected components (text/notes) before banding. Result: Holbrook p3 wall = **159 LF across clips (150,80,2050,1050)/(560,300,2010,1100)/(400,200,2100,1050) — identical.** Region just needs to exclude the title block + section detail; text inside is harmless.
- Holbrook wall now 159 LF vs 178 (~11%); residual = skeleton corner-rounding + sub-2.5ft segments dropped by text filter. Slab-area `trace_footprint` should get the same text-drop treatment next.
- VERDICT: region-selection solved the robust way — vision-guided (grid render -> read bbox) + clip-invariant bricks. Not a brittle pure-CV heuristic. Engine adds: `render_with_grid`, text-robust `measure_wall_lf`.

# Data point #26b — slab-area trace is ALREADY clip-invariant (no text-drop needed)
Tested `trace_footprint` across clips on Holbrook p5: clips that fully contain the slab all return **3,175 sf / 244 LF identically** (the earlier 2,954 was a too-tight clip cutting the slab). Largest-contour naturally ignores the notes/title-block blobs, so — unlike the wall (text-removal) — the slab trace needed NO change; it just needs a clip that CONTAINS the full drawing, which the vision-read region guarantees. **3,175 vs GEO 3,122 = within 1.7%** (tighter than the tight-clip 2,954). Overlay confirms full footprint, no patio over-grab.
- BOTH geometry bricks now robust: wall LF clip-invariant via text-drop (159 LF); slab area clip-invariant via largest-contour (3,175 sf). Region-selection = `render_with_grid` -> vision reads bbox -> measure. Engine generalizes across houses.

# Data point #27 — Lankford (530 Milton Dr, McDonough) — 3rd basement, SCANNED plan: honest result
GV wall invoice #1211 ($37,289): wall **198 LF** (146@10' $105, 17@9' $100, 9@7' $90, 16@6' $85, 10@5' $80); footing **183 LF** 2'×1' @ $25; slab/brickledge 178' @ $5; **pump trucks $2,000/ea (UP from $1,500!)**; line-pump mix fee $700; rebar 5,640' @ $1.20; 64 anchor straps. Plan "Lankford-red lined.pdf" = SCANNED (0 text, drawing in raster images; vector paths = redlines only). Foundation = p5 (3/16"=1', 10" basement walls + brick ledge).
- ✅ **VISION-GUIDED SCALE WORKS ON A SCAN:** no vector dims, so read the overall dim off the raster (72'-0" = 18+20.5+12+20.5) and measured its pixel span (x600→x1490 = 890pt) → **12.36 pt/ft** (scan rescaled to 91.5% of native 3/16"=13.5). Sub-segments cross-checked 12.2-12.5. New capability: scale a scan from a read dimension.
- ❌ **AUTOMATED GEOMETRY FAILS on the scanned, dimension-cluttered, redlined foundation plan:** measure_wall_lf grabbed everything (1490 vs 198 LF — wall not on a clean sheet, mixed w/ dims/beams/notes, all connected). trace_footprint grabbed the DIMENSION-LINE ENVELOPE (514 LF / 4,848 sf) not the wall — the building wall has openings, so exterior-fill leaked out to the surrounding dim lines. The wall outline IS visible/readable; the bricks just can't isolate it amid dim/redline clutter.
- ⛔ **CONFIRMS the confidence read:** scans + busy foundation plans (wall mixed with all the dim/beam/note linework) defeat the current bricks. They were validated on CLEAN vector sheets (Holbrook p3 wall-only; Wilson/Holbrook slab as dominant enclosed region). The path for scans = vision-guided polygon trace (read footprint corners off the grid) OR read the full dimension chains and sum the outline — both semi-manual, not the automated engine. PUMP RATE not fixed: $1,500 (Wilson/Holbrook) → $2,000 (Lankford); price per-job.

# Data point #28 — Lankford dimension-chain tracer: built, but two honest limits on this scan
Built `polygon_outline()` (assemble outline from vision-read labeled dims -> perimeter+area + CLOSURE self-check) and `render_no_redline()` (declutter). Self-test passes; in engine. Vision read the HORIZONTAL chains cleanly: top 72'-0" (18+20'6"+12+20'6"), bottom 72' (15'9"+8'5"+10'6"+5'4"+30').
- ⛔ **LIMIT 1 — scan legibility:** the VERTICAL (rotated) dims are not reliably readable on this low-quality scan — the overall height read as 62'-4" on one crop, 83'-4" on another. Can't trace the full outline from dims I can't read. (Horizontal/large dims OK; rotated/small ones marginal.)
- ⛔⛔ **LIMIT 2 — wall LF != footprint perimeter (the bigger insight):** wall=198, footing=183, but the full footprint perimeter is much larger (72' wide × 62-83' deep => 268-310 LF bounding). So the poured 10" basement wall wraps only PART of the footprint; the rest is brick ledge / crawl / slab-on-grade (per "brickledge" notes; footing 183 < wall 198). **Getting the 198 requires tracing the BASEMENT sub-region (where the 10" walls are), not the whole footprint — a scope read on top of the geometry.** Even a perfect outline trace gives footprint perimeter, not wall LF.
- VERDICT: tool + method sound and validated in pieces, but I could NOT reliably produce 198 on this scan — refused to fabricate from guessed dims. Reinforces the confidence read: scans + mixed-scope foundations are at/beyond the reliable limit. Path: trace WITH Jason confirming the rotated dims + which segments are poured wall, or use a legible (vector/clean) copy.

# Data point #29 — GREEN-TRACE workflow PROVEN on a scan + the centerline-to-billed wall factor (0.89)
Jason traced the poured basement wall in GREEN on the Lankford lower-floor-plan screenshot (correctly skipping the patio/covered-patio = scope handled by his marking). `measure_colored_path()` isolated the green, skeletonized the stroke, summed centerline. Scale from the 72'-0" top run on the same screenshot = 603px/72ft = **8.4 px/ft** (sub-segments 18'->8.6, 20'6"->8.3 confirm).
- ✅ **SCAN PATH WORKS:** green centerline = 1487px / 8.4 = **177 LF**. The whole scan problem (legibility + scope) is solved by Jason marking in color — I follow his clean line, not the faint scan, and only what he marks counts.
- ⭐⭐ **CENTERLINE-TO-BILLED WALL FACTOR ≈ 0.89, validated on 2 houses / 2 methods:** Lankford 177/198 = **0.894**; Holbrook (auto-skeleton) 159/178 = **0.893** — nearly identical. So **billed wall LF = measured centerline ÷ 0.89**: Lankford 177/0.89 = **199 ≈ 198 ✓**; Holbrook 159/0.89 = **179 ≈ 178 ✓** (both ~1%). Likely skeleton corner-cutting on heavily-jogged basement walls; consistent because these are similar stepped basements.
- ⛔ Honest: 2 data points (striking match, but want a 3rd to confirm it's a constant, not coincidence/scale-absorption). If it holds, wall LF goes from the ~11%-low soft spot to ~1-2% via the 0.89 conversion. Engine: `measure_colored_path` (color isolation + skeleton).
- Lankford GV rates also banked (#27): pump trucks $2,000 (up from $1,500), 10' wall $105, footing 2'×1' $25.

# Data point #29b — PUMP RATE CORRECTION (Jason): $2,000 was site-specific, NOT a rate change
The Lankford pump jump $1,500 -> $2,000 was a SPECIAL CIRCUMSTANCE: site conditions blocked a standard BOOM pump, forcing a more expensive LINE pump (+ the $700 line-pump mix fee). **Standard pump stays ~$1,500 (boom). Line pump ~$2,000 + $700 mix fee = only when site access prevents a boom pump.** Don't carry $2,000 forward as the rate.
- ⭐ **Estimating rule: pump TYPE is a SITE-ACCESS variable, not a market rate.** Default boom $1,500/pour; flag line-pump ($2,000 + $700) only when the lot/access can't take a boom. Confirm per-job from site conditions.
- ⭐ **Broader lesson — rate "variance" is largely EXPLAINABLE by scope/site, not random:** footing $25 vs $38 = footing WIDTH (2'×1' vs 3'×1'); pump $1,500 vs $2,000 = boom vs line (site access); concrete $180 vs $167 = different SUPPLIER (FFCI vs SRM, region). Capture those drivers (footing size, site access, supplier) and forward rates are far more predictable than the raw spread looked. This RAISES forward-estimate confidence vs my earlier "rates swing ±15% randomly" read.

# Data point #30 — Pace (4th house): 0.90 wall factor CONFIRMED on a true blind prediction
Pace foundation (vector p5 "Foundation Wall Layer" 1/4"=1' + Jason's green trace on screenshot). Garage excluded (monolithic slab, no stem walls — Jason's note + green skips it). Green centerline measured = 2178px / 14.0 px/ft = **155.6 LF** (scale from bottom sub-dims 12'->14.2, 4'6"->14.0, 4'8"->13.9). **PREDICTED billed wall = 155.6/0.89 = ~175 LF BEFORE seeing Jason's number (true blind prediction). Jason's manual takeoff = 171.81 LF → match within 1.8%.**
- ⭐⭐⭐ **CENTERLINE-TO-RUN FACTOR LOCKED at ~0.90 across 3 houses / 2 methods / 2 bases:** Holbrook 159/178=0.893 (auto, billed), Lankford 177/198=0.894 (green, billed), Pace 156/171.81=0.906 (green, manual takeoff). Apply **÷0.90**: Holbrook→177, Lankford→197, Pace→173 — ALL within ~1%. The 0.89(billed) vs 0.91(manual) spread = subs bill a hair over Jason's takeoff. 
- **RULE: wall/footer LF = measured centerline (skeleton, auto or green-trace) ÷ 0.90.** Validated 3 houses. Skeleton cuts corners on jogged basement walls by a consistent ~10%; the factor corrects it. Wall LF moves from the ~11%-low soft spot to ~1-2% SOLVED.
- ⭐ **Matching Jason's MANUAL TAKEOFF (not just the invoice) is the engine's actual job** — Pace had no invoice yet; reproducing his 171.81 within 1.8% is the core goal (replace the manual takeoff). 

# Data point #31 — NEW TRADE: Foundation Waterproofing + French Drain (CGS Waterproofing LLC)
Only on BASEMENT/CRAWLSPACE homes — NOT monolithic slabs. Vendor: CGS Waterproofing (Norcross GA).
- **WORKFLOW:** Jason MARKS the walls that get waterproofing (green trace, like the poured-wall workflow); I measure the marked length × rate. "Everywhere I mark walls you apply waterproofing."
- ⭐ **RATE: ~$55.50/LF, BUNDLED** (waterproofing system + french drain in ONE per-LF line: asphalt sealer + plastic/6mil barrier + drain mat + perforated pipe + gravel). Stable: $55.50 (Wilson 2024) → $55.50 (Holbrook 2026) → $56 (Lankford 2026). **Walls always ~9-10 ft → rate is flat per-LF, NO height scaling needed** (Jason: "always assume 9-10 ft").
- ⭐⭐ **ESTIMATE OFF THE FULL MARKED WALL LENGTH — not the vendor's tighter measured number.** Jason: "Go off wall length. I like the cushion." Marked wall runs ~15-35% over what CGS contracts (CGS measures tight / omits retaining walls); the over-estimate is INTENTIONAL margin protection. Don't try to match the CGS LF.
- **SCOPE:** basement-level garage walls (poured foundation, buried) GET it. Retaining walls (marked) GET it (length often "TBD" on plan — flag that it'll firm up). Walkout/daylight faces + monolithic-slab garages do NOT.
- **CGS actuals (their contracted LF, < marked):** Wilson 112 LF @ $55.50 = $6,216; Holbrook 133 @ $55.50 = $7,381.50; Lankford 98 @ $56 = $5,488 (only left+right elevations). 
- **WILSON marked-wall measurement (green trace, foundation wall plan, ppf 13.3):** ~150 LF → ~$8,325 estimate (incl retaining wall; cushion over CGS's $6,216 is intended). Engine: `measure_colored_path` (green isolation + skeleton).

# Data point #32 — NEW TRADE: Plumbing (count-based) + margin-protected model. Plumber: David Holman
First COUNT trade (vs measure). Plumber bids ROUGH + TRIM. JJCH furnishes fixtures (so estimate = labor+rough; in some Holman quotes he furnished a few = "JASCO furnished", back those out).
- **FIXTURE CLASSIFICATION (Jason):** WHOLE (drain+supply) = toilet, sink (all: lav/kitchen/laundry/utility/bar), tub, shower, water heater, washing machine box, sump+grinder. HALF (supply OR drain only) = dishwasher, refrigerator/ICEMAKER line, hose bibb/spigot, floor drain. (Note: dishwasher is HALF per Jason, even though it has both — ties to sink drain.)
- ⭐ **COUNTING VALIDATED:** counted Holbrook fixtures cold off the floor plans (p6 main, p7 second) and matched Holman's professional list EXACTLY (5 toilets, 1 tub, 3 showers, WH, dishwasher, washer box, fridge, 3 hose bibs) — AND caught a main-floor LAUNDRY SINK Holman omitted (his clause: "if not listed, charged extra"). The count catches omissions = protects against back-charges.
- ⛔ **FLAT per-fixture UNDER-BIDS (don't use):** Jason's gut $700/whole+$400/half (flat, no base) comes in LOW vs every Holman actual — Sailview -33% ($9,700 vs $14,500), Holbrook -11%, Wilson -13%. Reason: big FIXED BASE (water/sewer service + mobilization + DWV mains) that doesn't scale with fixtures, so small houses get badly under-bid. Holman's effective $/fixture-unit is NOT constant: ~$1,074 small house, ~$825 big house.
- ⭐⭐ **MARGIN-PROTECTED MODEL (LOCKED): plumbing sub cost = $8,000 base + $450/whole + $400/half.** Covers all 3 Holman actuals with +3-6% cushion (never under): Sailview $14,950 vs $14,500; Holbrook $18,550 vs $17,900 (my count w/ laundry sink $19,000); Wilson(labor) $19,300 vs $18,150. Scales correctly across house sizes (fixes the small-house under-bid). Engine: `plumbing_estimate(whole, half)`. Then J&J sub markup + O&P/contingency per the estimate-format layer on top. Fixtures (JJCH-furnished) estimated separately as allowances/selections.

# Data point #33 — NEW TRADE: Framing (materials + labor SEPARATE). Lumber vendor: Builders FirstSource
How Jason estimates framing (his words): materials and labor priced SEPARATELY; labor = price per sqft UNDER ROOF (blended); most roofs STICK-FRAMED so roof framing is in the lumber package; engineered floor system priced separately but paid to same vendor (BFS).
- **LABOR = blended $/sf of area UNDER ROOF that gets FRAMED, summed PER LEVEL.** Count basement + main + any 2nd floor + garage + covered porches/decks. ⛔ EXCLUDE slab-on-grade patios/stoops (that's flatwork, already paid under the flatwork sub — counting it double-dips and UNDER-states the rate, losing money on the next bid). Jason confirmed: drop the basement patio.
- ⭐⭐ **MEASURE EACH FLOOR ON ITS OWN SHEET — floors do NOT always stack.** A 2nd floor can be smaller than the footprint (partial / bonus-over-garage). Never footprint × stories. Same discipline as the per-page scale rule: measure what's drawn on each sheet, sum the actual areas.
- ⭐ **J&J plans often carry a printed designer SQFT SCHEDULE** (Wilson Sheet 4 = "SQFT AREAS"). The engine may extract it with `read_sqft_schedule(page)` for comparison and discrepancy detection, but it cannot feed `heated_sf`, `framing_sf`, or pricing. The actual estimate basis is the certified component geometry required by the current-area override above.
- ⭐⭐⭐ **LABOR RATE LOCKED at $6.50/sf blended, validated on 3 ACTUALS: Wilson $38,210/5,792.59=$6.60; Watkins $28,862/4,518=$6.39; Peterson/Sailview $20,688/3,198=$6.47. Weighted = $6.497.** DEFINITIVELY FLAT across 3,198→5,792 sf — smallest house ($6.47) sits between the others, so NO size dependence; the ~3% spread is complexity/site. Engine `FRAMING_LABOR_RATE=6.50` reconciles all 3 within ~2% (Wilson −1.5%, Watkins +1.7%, Peterson +0.5%). Margin-protective alt = $6.60 (covers the high house; Jason's call, ~$500/bid).
  - **Peterson/Sailview area note:** 3,198 sf = "home + porches" — Jason's OWN Buildern frame-labor basis (and my cold estimate). His budget used $5.25/sf ($16,790); actual $20,688 = +23% → SAME quote-to-actual gap as Wilson, confirms it's systemic. ✅ **RESOLVED via the designer's printed SQUARE FOOTAGE table** (Fairview Cottage / `Fairview Cottage - Slab Foundation (2).pdf` p2): First-floor heated 1,969 + garage 559 + outdoor living (courtyard) 258 + covered entry 6 + **FUTURE EXPANSION 406** = **TOTAL UNDER ROOF 3,198.** So the 406 = the "future expansion" = the UNFINISHED 2nd floor Jason is finishing (NOT a deck, NOT the courtyard — courtyard is the separate 258 "outdoor living"), and it's ALREADY inside the 3,198. My framing area (3,198) already counts it → **3,198/$6.47 stands, $6.50 holds across all 3 houses.** Also ties off the "2,375 heated" on record = 1,969 first floor + 406 future expansion (finished). ⚠️ **Measurement lesson: in my COLD estimate I listed that 406 as a SEPARATE "2nd-floor deck" line — but it was already in my 3,198 under-roof total = a DOUBLE-COUNT (and a mislabel). On a schedule-less cold read, beware adding an area that's already inside the under-roof total.**
  - ⭐ **CLASSIFICATION RULE — "FUTURE EXPANSION"/unfinished bonus is framed whether or not it is finished.** Use labels/notes to classify the measured polygon; do not take its SF from the schedule. If J&J finishes it, it also becomes heated SF for the finish trades.
  - **DECK CONVENTION (still open):** covered decks fold into the under-roof $/sf area at $6.50 (Wilson's 667-sf covered deck was in its 5,792.59). For an UNCOVERED deck/balcony, confirm whether it folds in at $6.50 or carries a separate lower-rate line — hasn't come up on a real house yet.
- ⛔⛔ **THE BIG LESSON — Jason's rate was QUOTE-anchored and quotes run ~25% UNDER actual.** Wilson framing-labor QUOTE was $30,424 (=$5.25/sf) but ACTUAL was $38,210 (=$6.60/sf, +26%). That's why $5.25/$5.50 looked plausible but bleed margin: at $5.50 he'd under-bid Wilson by $6,351 (17%) and Watkins by $4,013 (14%) — ~$4-6k/house, every house. **ALWAYS calibrate framing labor to ACTUAL spend, never the framer's quote.** (My earlier "rate flexes UP on small houses" hypothesis was WRONG — killed by actuals; bigger Wilson is higher, not lower.)
- ⭐ **DECK FRAMING counts at the normal $/sf (Jason):** his framer frames the deck (joists/beams/subfloor) at the blended rate, but does NOT do deck flooring or railings (separate scope). So framing-labor area = heated(all levels)+garage+covered porches + DECKS (covered or open, the framed structure); only slab-on-grade patios are excluded. Wilson's covered deck (667 sf) is already in the 5,792.59.
- **Materials (BFS plug-ins) ACTUAL vs quote also diverge — and NOT in one direction:** Wilson lumber actual $37,661 (quote $46,360, −19% — lumber market fell) but eng-floor actual $24,014 (quote $14,442, +66%). Materials are quotes Jason plugs in (no rate to calibrate), but flag the quote→actual swing when budgeting; don't bank a lumber windfall.
- **WATKINS measurement test (my COLD vision number vs Jason's actual SF) — engine on a measurement-HOSTILE plan** (Lifestyle Design Service, outside designer, 2-story SLAB, NO sqft schedule, dims/labels OUTLINED VECTOR not text → auto-scale + schedule-reader + flood-fill footprint all FAIL; 16' garage door defeats flood seal). Scale recovered by VISION off the garage's labeled 20'-0" interior (365pt → ppf 18.25, 1/4"). My committed total 4,900 sf vs actual 4,518 = +8.5%, BUT that was almost entirely a PORCH DOUBLE-COUNT (footprint envelope already includes porches, then I added porch again); strip it and my measure was +1.8%. Upper level (flagged ±20%) came in −1.3% (nearly exact; it's a near-full 2nd story, 1,925 > main 1,538). ⭐ **LESSON: on a schedule-less plan my footprint TOTAL is good to ~±5%, but I can't split heated/garage/porch by tracing — and for framing LABOR I don't need to (it's total-under-roof). Just never add porches that already sit inside the traced footprint.** Schedule reader auto-extracted all 6 Wilson rows and tagged the basement patio (1,154.48 sf) flatwork, leaving 5,792.59 framed (main 2406.22 + bsmt 1507.40 + garage 898.36 + covered deck/screened porch 667.02 + front porch 313.59). **STILL DIALING IN — Jason gathering more houses to confirm whether $5.50 is flat or flexes with size/complexity (like wall $/LF held at $105 Wilson+Lankford).** `FRAMING_LABOR_RATE = 5.50` in engine.
- **MATERIALS = two BFS plug-in quotes (NOT taken off stick-by-stick):** (1) lumber package = all lumber/OSB/subfloor/nails/straps/glue/anchors + stick-framed roof; (2) engineered floor system. Wilson refs (on 5,792.59 sf base): lumber $46,360 = $8.00/sf; engineered floor $14,442. Engineered floor covers every FRAMED floor deck — main deck over basement/crawl, any 2nd floor, + GARAGE CEILING (engineered joists for the span). Slab-on-grade gets none; a 1-story slab w/ no garage = $0 engineered floor (2-story or garage slab still does). Engine: `framing_estimate(framed_sf, lumber_pkg, eng_floor)`.
- **Wilson framing total = labor $30,411 + lumber $46,360 + eng floor $14,442 = $91,213** (before J&J markup + O&P/contingency).
- **Calibration method change:** framing is paid across many draws/invoices — Jason gives the TOTAL spent per house+bucket (labor / lumber / eng-floor), I measure the area off the plans and back out the rate. Cleaner than parsing draws.

# Data point #34 — Pack Residence: FIRST full-estimate cold run + MASONRY measurement lessons (the big ones)
Big single-story slab J&J set (16 sheets; **NOT 911 pages — PDF metadata misread, it's 16**). SQFT schedule: heated 4,326 + attached garage 1,215 + DETACHED garage/shop 1,003 + covered patios 828 (4 pieces) + uncovered patio 254 = 7,626. Slab-on-grade whole house; uniform **8:12** roof; brick + stone exterior; mid-grade. Intake captured (full spray foam main; detached shop = spray foam + ½" sanded-plywood walls/open-rafter clg + half bath + own mini-split; city water + SEPTIC; arch shingle; pavers = rear patio + walkway only; J&J supplies all; carry permits, other pre-con done).
- ⭐ **WORKFLOW VALIDATED end-to-end:** Step-0 intake gating caught unspecified roof-covering + sewer (don't assume). **Per-page scale verified: 3/16" on plans, 1/4" on electrical** — different per sheet, never assume. `read_sqft_schedule` + window/door/Note schedules harvested clean.
- ⭐⭐ **APPLY CALIBRATION OVER THE TEMPLATE — the template is STALE.** Template still carries framing labor at **$5.50/sf**; our 3-house actual is **$6.50** → blindly using the template under-bids framing ~$1/sf (~$7,400 on Pack's 7,372 under-roof). The engine's whole ROI is catching the template's stale rates. (Also: template plumbing = flat $800/$400 = the under-bidding structure; use the margin-protected base+fixture model.)
- ⭐ **GREEN-TRACE perimeter works where auto-trace fails.** On a sprawling, dimension-dense, TWO-STRUCTURE sheet the one-shot `trace_footprint` FAILED (detached garage came back 142 sf vs known 1,003). Fix = Jason green-traces the exterior walls → isolate green, skeletonize, **calibrate the screenshot's ppf off a KNOWN AREA (detached garage 1,003 sf → ppf 5.76)**, measure centerline, apply the 0.90 jog factor. Got perimeter 524 LF centerline → ~560 LF wall run. The main loop enclosed 6,090 sf (≈ heated+att gar+enclosed patio) = calibration sanity check passed.
- ⭐⭐⭐ **GABLE STONE = Σ ½·|run|·|rise| over EVERY roof RAKE on EVERY elevation (front/rear/sides).** Each rake is a right triangle; both rakes of a gable sum to the full triangle, so summing all rakes = total gable area. Pull rake segments (slope ≈ 0.667 for 8:12 — they read EXACTLY at the pitch, confirming real rakes), dedupe double-drawn edges. Pack measured = front/rear 610 + sides 855 = **1,465 sf gable area.** ⭐ **SELF-CHECK against the story pole:** side-gable rises 15.9' + 9' plate = 24.9' ≈ the 25.5' ridge ✓; front rises 10.8' → 19.8' ≈ 20.6' ridge ✓. **⛔ NEVER ASSUME GABLE HEIGHT** — I first eyeballed ~7' rise / 80 sf-per-gable and came in at 560 sf (2.6× LOW). The elevations + roof plan + story pole had everything needed. (Story pole Sheet 12: grade 0, header 6.4', plate/ceiling **9.0'**, ridges 20.6'/25.5', garage-gable apex 26'.)
- ⭐⭐⭐ **UNIFY — MASONRY IS PART OF THE EXTERIOR-CLADDING TAKEOFF, NOT A SEPARATE PROBLEM (Jason's correction).** Brick, stone, lap, B&B, shake, vinyl are ALL just cladding MATERIALS measured the SAME way — the siding method already trained on: off the elevations, measure every wall segment (L×H) + every gable (its own triangle) **BY MATERIAL**, no formulas, no blanket assumptions; each material's area × its rate (brick $10/sf, stone $14/sf, lap/B&B/shake $/sq…). **A stone gable is measured identically to a shake/lap gable — only the material+rate switches.** The "material map" (reading which surface is which material) IS step one of the cladding takeoff, not a masonry special case. ⛔ **Don't silo gables or masonry.** `gable_area()` is just the triangle-math HELPER inside the one cladding takeoff — NOT a standalone masonry tool, and it does NOT need separate gable-area ground truth (RETRACTED): the SIDING training already calibrated this measurement; brick/stone plug into it with masonry rates. (Meta: my failure mode is siloing one problem into many — gable/masonry/siding are ONE exterior-cladding takeoff.)
- ⛔⛔ **MATERIAL-MAP RULE — read each elevation SECTION-BY-SECTION for the ACTUAL cladding; NEVER apply a blanket "brick walls / stone gables."** I applied the intake uniformly (all walls brick, all gables stone) and never read the front elevation's pattern change → I bucketed **~630 sf of stone entry-wall as brick** (came out brick-HIGH / stone-LOW while the TOTAL stayed within 3%). The skill's siding rule already says it: *"MEASURE each cladding material SEPARATELY off every elevation — DO NOT GUESS the material split."* **Pack actual map:** STONE = the central ENTRY FEATURE wall (random-coursed, larger irregular blocks) + most gables; BRICK = garage end, the GARAGE GABLE (brick, not stone!), and the flanking wings (regular small coursing). Read the texture at high zoom — stone = irregular/varied blocks, brick = uniform rows.
- **PACK MASONRY ACTUALS (Jason ground-truth, INCL his 10% waste):** brick **5,067 sf**, stone **2,307 sf.** At template installed rates ($10/sf brick = $5 mat+$5 lab; $14/sf stone = $7+$7): brick $50,670 + stone $32,298 = **masonry $82,968.** My measured-but-misallocated pass was brick 5,040(raw)/stone 1,465(raw) — total within 3% but split wrong; the stone was under both ways (under-measured gable height + mis-bucketed the stone wall).
- **Plan gotchas:** Sections sheet (16) was BLANK + no eave/cornice detail anywhere → plate height comes from the elevation STORY POLE, and roof overhang can't be measured (flag/estimate). Detached shop likely has a taller plate than 9' (open-rafter, 8' OH doors) — confirm for its brick height.
- ⭐⭐ **DRYWALL (Pack actual = 20,760 SF incl 10% waste). Jason's method + my misses:** (1) ⛔⛔ **ALWAYS ASK base ceiling height AND whether any rooms are VAULTED / RAISED / higher — NEVER assume a standard height. THERE IS NO STANDARD CEILING HEIGHT (add it to Step-0 intake, every house).** Pack base = 9' (my story-pole read was RIGHT — that's why brick@9' matched the 5,067 actual), but the LIVING ROOM is raised to **14'**; Jason blended the whole house to 10' as a ONE-OFF to absorb that extra living-room drywall. **10' is NOT a standard — it was this house only.** (2) **Drywall INCLUDES the detached garage** (don't zero it just because its walls are plywood-finished). (3) **10% waste.** (4) Method = Σ(each room perimeter × ITS ceiling height) for walls + (heated + attached-garage area) for ceilings. **My miss: assumed a uniform 9' + excluded the detached garage + hadn't applied waste → came in ~11% low. Every bit avoidable by ASKING ceiling heights/vaults up front.** Brick height (~9' to soffit) ≠ interior drywall height (full ceiling) — keep them separate.
- ⭐⭐ **CABINETS (Pack actuals; my raw-code total was −4.7% but CLASSIFICATION was wrong).** Method: extract cabinet codes off the floor plan (`SB36`=36" sink base=3.0 LF; width = digits after the letter prefix), dedupe double-draws, EXCLUDE door tags (D##). ⛔ **Then BUCKET BY JASON'S STRUCTURE, by ROOM — not a blanket base/upper sort:** **Kitchen** (lower / upper / **island** / **tall**), **Pantry** (lower / upper / tall, @ **$175/LF** not kitchen's $150), **Game Room** (lower / upper), **Vanity per bath** (one LF number per bath, baths' linen/storage folds INTO the vanity — don't call it "upper"). ⛔ **Classify FRIDGE/OVEN/LINEN towers as TALL ($300 kitchen / $350 pantry), NOT upper** (double the rate — I called 13 LF of tall "upper"). ⛔ **Garage cabinets were NOT in Jason's count** — don't lump garage/laundry/utility storage into kitchen uppers (that was my whole +29 LF upper overage). Pack actuals: Kitchen lower 16.2 / upper 16.37 / island 24.41 / tall 8.90; Pantry lower 17.3 / upper 10.28 / tall 4.19; Game Room lower 36.03 / upper 8.98; Vanities 13.71+9.26+6.24+9.77 = 39.0 LF (4 baths). Total 181.6 LF ≈ **$30k** at rates (vs my lumped $16k kitchen-only — I'd under-bid by counting kitchen only). The raw measurement was fine; **measure by room + classify by type the way the SUB/Buildern lines are structured.**
- ⭐⭐ **POCKET/BARN DOOR IDENTIFICATION (Pack) — built a TOOL when none existed.** On a floor plan: HINGED = swing ARC (lies on a circle of radius ≈ door width); POCKET = no arc, panel slides INTO wall; BARN = no arc, panel + track ON wall face. Built a **HoughCircles swing-arc detector** (per-door crop → detect circle in the door-width radius band → arc = hinged). VALIDATED before trusting (D03 known-pocket → 0 arcs ✓; D10 known-hinged → 3 arcs ✓) — but it was **~86% (missed 3 pockets via FALSE-POSITIVE arcs** from a tub curve / adjacent fixtures near bath doors). ⛔ **TOOL FIXES (Jason): (1) ARC EXTENT VARIES BY PLAN — 90° here, can be 30° elsewhere; tune the vote threshold (param2) LOWER to catch partial arcs, NEVER assume 90°. (2) require the detected arc's CENTER at the door JAMB to reject stray curves.** ⛔ **The door panel is NOT pink-coded for pocket — "pink wall = offset insulated wall" per the note schedule; don't read pink as a door.** ⛔⛔ **COUNT DOUBLE DOORS AS 2 LEAVES** (D16 4068 = 2 → 21 tags = 22 leaves). **Pack VERIFIED classification (reconciled EXACTLY to Jason's manual 9/6/7):** POCKET 9 (solid, $950) = D03,D04,D06,D11,D14,D22,D24,D31,D36 [D14 is a 3'5"-wide bath — physically can't swing → must be pocket]; SOLID swing 6 (bedrooms, $400) = D05,D12,D16×2,D29,D30; HOLLOW 7 ($160) = D10,D13,D20,D21,D23,D25,D26. Interior doors = $12,570 + attic pulldown $500 + hardware. **POCKETS ARE THE EXPENSIVE DOOR ($950 vs $160 hollow) — missing them under-bids ~$7,850; always classify all of them, count doubles as 2.**
- ⭐ **TRIM & INTERIOR DOORS (Pack, Jason):** Base molding = Σ room perimeters; window casing per window — formulas CONFIRMED correct. ⛔ **DOOR CASING is INCLUDED in the door price — do NOT add a separate door-casing trim line (double-count).** ⛔ **ALWAYS separate INTERIOR doors ($160 hollow / $400 solid / $950 pocket·barn) from EXTERIOR ($1,000 hinged single / $2,200 dbl / $4,500-5,500 slider / front-door allowance / garage OH ~$3k) — they are NOT the same price; never one "doors" line.** SOLID interior doors = **bedrooms + pocket + barn**; everything else hollow (Pack: 8 solid / 14 hollow of 22 interior; classify off the door schedule's room names + pocket/barn tags). CROWN = **main living areas EXCL closets** (which rooms is a SELECTION — ASK; Pack = main living excl closets). ⛔⛔ **DON'T MISS CEILING FEATURES — coffered / tray / beamed / vaulted ceilings carry BIG trim (wood BEAMS by LF + CROWN around each coffer AND the room perimeter). Check the ceiling-framing plan + ceiling details, not just the floor plan.** Pack living room has a coffered ceiling (crown + beams) Jason had to flag — add to the trim checklist + the intake ceiling question (vaulted/coffered/tray?).
- ⭐ **META-LESSON:** the engine's judgment + rate work (intake, scale, schedules, calibrated rates, framing-rate catch, green-trace) is strong and automated; the repeat misses are GEOMETRY-READING DISCIPLINE + NOT ASKING — assuming instead of measuring/asking when the answer was a question away (gable height; material map; ceiling height/vaults). Hard rules: sum rake triangles for gables; read the material map per elevation section; ASK ceiling heights + vaults at intake.

# Data point #35 — NEW TRADE: Countertops (Pack). Jason's method + the SHORTCUT THAT RAN ME 8% LIGHT
How Jason estimates tops (his words): **ALL countertops measured by SQUARE FOOT, room by room.** Rates **Level 3 granite/quartz = $55/SF** (kitchen, mid-grade here), **Level 1 / remnant = $35/SF** (every other room). Tops waste ≈ **1.24%**; kitchen tile backsplash waste **10%** (off his measurement file).
- ⛔⛔⛔ **THE STEADFAST RULE — MEASURE THE TRUE SLAB POLYGON, NEVER base-cabinet-LF × nominal depth.** The granite polygon = **outer overhang edge → wall**, run **CONTINUOUS through corners and ACROSS cooktops/ranges** (a slide-in/drop-in range does NOT break the slab; the slab carries past it, you just don't lay counter *on* the appliance — net, the front edge is one unbroken line). **Effective depth measures ~27" (24" cabinet + ~3" overhang), NOT 25.5".** The LF×depth shortcut drops THREE things — the corner, the appliance span, and the overhang — and on Pack's kitchen it ran me **−8% (95.3 vs Jason's 103.70 SF).** This is the same disease as [[feedback-measure-dont-formula]] (siding): measure every piece off the drawing, no multiplier.
- **MY TWO MEASURED ERRORS (Pack kitchen, both made me LOW):** (1) **DEPTH** — priced 25.5"; actual MEASURED off [p6] = back wall face y403.0→overhang front y433.3 = **26.9"**, right wall = **27.4"**. I was reading to the cabinet face, not the slab edge (~3" overhang, not 1.5"). (2) **RUN LENGTH** — used Jason's 16.2 LF of base cabinet; the granite FRONT EDGE runs **17.48 ft** (back leg 8.96 + right leg 8.52, MEASURED) because it carries through the 45° diagonal corner (DCB36R) AND across the slide-in range. Corrected perimeter = (8.96+8.52)×2.24 = **39.2 SF** (his 40.31, last ~1 SF = the corner). Island: my 60.9 (measured to cabinet/seating edge) vs his 63.39 — missed the ~1.5" overhang on the back + two ends; with them ≈ 63.4. **Corrected kitchen ≈ 102.9 vs his 103.70 — within 1%.**
- ⭐ **KITCHEN (Level 3) rules:** measure top polygon; **keep the sink IN** (don't deduct), **take the stove OUT**; **MEASURE the stove opening — we're custom, NOT always a 30" range** (Pack = slide-in 30" gas, W3024 hood confirms). **Include the island seating overhang** (Pack island = 12.06 ft × ~5.05 ft incl a measured 12" seating overhang on the living side; two 24" rows back-to-back = the 24.41 LF). Island is Level 3 (kitchen stone).
- ⭐ **KITCHEN BACKSPLASH = TILE, a SEPARATE line (NOT stone).** Jason: "kitchen is usually tile backsplash to the countertop flat surface." Compute SF = **wall-touching counter LF × a height multiplier: ×2 standard run, ×4 at the stove, ×6 where there are NO upper cabinets** (the multiplier ≈ splash height in ft — 2' under uppers, 4' behind range to hood, 6' full-height open wall). Feeds the TILE trade, not the countertop $.
- ⭐ **ALL OTHER ROOMS (Level 1 / remnant, $35):** measure top polygon, **keep sinks IN**. ⛔ **SPLASH METHOD (Jason's, CORRECTED — validated against his full takeoff):** there is **NO separate 4" splash LINE.** Instead **OVER-MEASURE the top polygon 4-6" (~5") into EVERY wall it touches** — the back edge AND each run-end that abuts a wall — which folds the splash straight into the slab SF. An **alcove vanity touches 3 walls** (back + 2 ends) so it catches the over-measure on three edges — that's most of why vanities measure bigger than a plain top. (My first L1 pass added a separate +38 SF splash line = WRONG, overshot +18%; his lines are the over-measured polygons.) Engine `l1_top_sf(run, depth, wall_ends)`.
- ⛔⛔ **MEASURE EACH TOP'S FULL EXTENT — CROP WIDE.** My worst vanity miss: I cropped tight on Lynn's vanity and **dropped a 3-ft cabinet section** (measured 4.5 LF / 9.5 SF; full run is 7.5 LF / 15.4 SF). Render the WHOLE room, capture every base cabinet in the run, THEN measure the polygon. Vanities ran me −12% purely from under-captured extent + the omitted over-measure.
- ⭐⭐ **PACK FULL RECONCILIATION (his complete countertop takeoff (4).pdf):** his L1 lines = Pantry 46.32 + Game Room 54.44 + 4 baths (19.5/13.51/10.3/25.27) = **169.34 SF (w/ waste); L3 kitchen 104.98; tile backsplash 48.33.** My BIG RUNS were DEAD ON (my scullery+laundry+mudroom+bar 99.3 vs his pantry+game 99.5 = **−0.2%**); my full-extent vanities 62.5 vs his ~67.7; total measured tops 161.8 vs his 167.3 raw = **−3.3%, the gap being exactly his 4-6" over-measure.** ⭐ The polygon method is validated end-to-end; the only disciplines were full-extent capture + the over-measure. Pack countertops = $5,774 (L3) + $5,927 (L1) = **$11,701** + tile backsplash on the tile line. **Don't get hung up on his room NAMES — "Game Room"/"Pantry" are his labels, not the architect's; just find every base-cabinet top on the sheet and measure it** (Pack had no 36-LF "game room" run on rev 4-2 — his names group differently than the plan).
- ⛔⛔ **THE CABINET FILE IS NOT THE COUNTERTOP ENUMERATION — measure tops off the PLAN, room by room.** Jason's cabinet measurement listed kitchen/island/pantry/game-room/4 vanities only; I ASSUMED that was every top and zeroed laundry + garages. WRONG — **laundry gets a top, and CHECK BOTH GARAGES** (detached has a half-bath vanity at minimum; "the plans show the same as the rest of the house"). Pack top surfaces to find/measure: kitchen perimeter + island (L3); scullery/pantry, Lynn's craft room (= Jason's "game room", 36 LF base), 4 vanities, laundry, both garages (L1). Enumerate every base/vanity run on the floor plan — no surface gets skipped because it's absent from the cabinet sheet.
- **HOW I MEASURED (repeatable):** verified per-page scale (p6 = 3/16"=1ft → ppf 13.5, consensus-matched off dimension lines), then for each slab pulled the OUTERMOST counter edge lines + the wall face from `get_drawings()` and computed front-edge run × (front-overhang→wall) depth — the island bounding box agreed with Jason's 24.41 LF within 1%, which validated the geometry method. **Do this per slab; don't shortcut.** Carry Jason's 104.98 SF (w/ waste) as the Pack L3 kitchen line (ground truth).

# Data point #36 — TRIM / Interior Carpentry (Pack, in progress) + THE TEMPLATE-STRUCTURE RULE
⭐⭐⭐ **USE JASON'S ESTIMATE TEMPLATE AS THE SOURCE OF TRUTH FOR PRICING + STRUCTURE — stop asking for rates that are already in it.** Template = `Downloads/Newest template 12_8_2025 - Estimate Items.xlsx` (sheet "Estimate"; cols: Name/Parent/Cost Type/Cost Code/Quantity/Unit cost/Unit/Markup%). **Jason is GRANULAR: material AND labor are SEPARATE lines for MOST trades.** The ONLY **TURNKEY** trades (sub furnishes own material, single line) = **poured concrete walls, plumbing, HVAC, electrical, insulation, drywall, siding, roofing, paint.** Everything else splits mat/labor (incl exterior doors = door allowance + separate install labor; cabinets = material + install labor; beams/crown = mat + labor lines). Markup: most lines 15% (material/allowance) or 7% (labor/sub).
- ⛔⛔ **THE TEMPLATE HAS UNIT MISCUES — VERIFY THE UNIT MATCHES THE ITEM TYPE, don't plug it blind.** Quarter round is listed as `$0.75/sq ft` but QR is a LINEAR item — Jason confirmed it's a template mistake: **QR = $0.75/LF.** A trim/molding item in SQ FT, or an "each" item in LF, is a RED FLAG to catch, not a number to use. (I flagged QR as not-fitting before using it — that instinct was right; make it a standard check.) ⭐ **TRIM TRADE LOCKED (Pack):** base $5,972 + crown(incl coffers) $13,762 + beams $2,015 + int doors $9,700 + mantel $350 + window casing (25 openings × 18 LF, std 3×6, **mulled=2**) $675 + QR (1,185 LF = base 1,357 − bath perims) $889 + custom closets (Lynn+Ralph ~80 LF @ $300/LF) $24,000 + shelf/pantry×3 $1,080 = **$58,443.**
- ⛔⛔⛔ **THE TEMPLATE QUANTITY CELLS ARE BLANK — the transforms live in JASON'S FILL CONVENTIONS, not visible cell formulas.** "Any good estimator knows the calc." I must apply the right quantity basis per line, not just read the unit rate. THE ONE THAT BIT ME:
- ⭐⭐⭐ **FAUX/BOX BEAMS HAVE 3 SIDES → quantity = ACTUAL beam length × 3** (bottom + 2 faces all get wrapped). Template carries beams at **$2.50/LF material + $3/LF labor** ON A ×3 QUANTITY. Jason gave me **$7.50 mat + $9 labor = the SAME thing pre-multiplied ($2.50×3, $3×3)** so I can measure ONLY the actual centerline length. **Net: actual beam LF × $16.50.** ⛔ DON'T "override" the template's $2.50/$3 thinking it's low — you'd drop the ×3.
- ⭐⭐ **SLOPED/VAULTED-CEILING BEAMS: multiply actual length by the SLOPE MULTIPLIER** (√(1+slope²) = √(p²+12²)/12), exactly like roofing surface or a gable rake — a beam up a vault is longer than its plan projection. Flat ceiling = run as drawn. (ALWAYS check the ceiling type before measuring beams.)
- **PACK TRIM RATES (read from template rows 133-187):** Base molding $2/LF mat · Window casing (1x4 + jambs) $1.5/LF mat · **Trim Labor $2/ft** (the package = hang ALL interior doors + base + window casing; pocket-frame install, beams, crown, stairs/railing are NOT in it — all additional) · Crown $5 mat + $5 labor ($10/LF) · Beams ($2.50+$3)×3 · Interior doors 6'8 hollow $160 / solid single $400 / pocket $950 / barn $950 / garage-entry $600 (+8' sizes 267/650/850/1100) · Attic pulldown $500 · Door hardware knobs $25 + install $25 + stops $6 · **Mantle $350** · Quarter-round/bath trim $0.75/sqft.
- **CROWN ROOMS (Pack, Jason):** living/family, kitchen, entry, ALL baths, hallway, ALL bedrooms (NOT closets/garage/laundry/utility/scullery/office). **Stairs/railing = $0** (single-story slab).
- **TEMPLATE GAPS — Jason's rates (build these from components, DON'T use the template's bundled lines):**
  - ⭐ **POCKET DOOR = split into components** (template lumps pocket+barn at one $950 line — break it out): **frame $100 mat + frame install $100 + slab $300 + slab install (IN trim labor, $0 separate) = $500/door** + the trim-labor hang. (Frame install happens after framing, before drywall — a separate stage.)
  - ⭐ **BARN DOOR = track + track install + slab $300** (track $ + install $ not yet given — get per house; Pack has 0 barns).
  - Pocket/barn **slabs ≈ $300 each** (they're solid).
  - ⭐ **CUSTOM CLOSET SYSTEM = $300/LF allowance** (LF of system run along the closet walls, like cabinet LF) — the big walk-ins (Lynn's/Ralph's etc., tagged "custom closet system" on the plan).
  - ⭐ **OTHER CLOSET SHELVING = $12/LF** (wire shelf OR wood shelf + rod, the template's "Shelving–Pantry" line applied to every closet). ⛔⛔ **PANTRY shelving × 3** (3 STACKED runs — another hidden ×qty convention like the beam ×3); every OTHER closet = 1 run. Plan note schedule: big closets = "custom closet system" ($300/LF); small closets = "1 wood shelf with metal rod" ($12/LF); NO bookcases / floating shelves drawn.
  - **Pack family-room coffered ceiling is FLAT** (no slope mult); **crown = room perimeter + inside EACH coffer**; beams = the coffer grid members.
- ⛔⛔⛔⛔ **FOUNDATIONAL RULE (Jason, emphatic) — MEASURE INTERIOR WALL PERIMETERS OFF THE GEOMETRY, FROM THE START. One measurement feeds BASE + CROWN + DRYWALL** (all three run on the same room perimeters). ⛔ **NEVER rely on printed room dimensions** — not every plan has them, and matching labels→dims is incomplete (Pack: half the rooms came back "no dim matched"). ⛔ **I had NEVER measured Pack's interior wall perimeters** — the drywall 20,760 SF was JASON'S ACTUAL that he handed me; my own drywall pass was an ASSUMPTION estimate (uniform 9', excluded detached garage, no waste) that ran −11%. Trying to build base off labels exposed the gap. **THE FIX = a geometry-based room-perimeter takeoff.** Engine: `room_perimeters(page, ppf, clip)` (raster wall-mask → seal → enclosed rooms → notch-close → contour perimeter).
- ⛔⛔⛔⛔⛔ **THE PLAN-READING DISCIPLINE (Jason, hardest lesson — "measure, measure, measure"; recognize walls/doors/columns/labels like a person, don't blob-detect blind):**
  - ⛔⛔ **A "VALIDATED" TOTAL CAN BE TOTALLY WRONG INSIDE.** My first room tool hit 1,384 LF, +4% off the drywall target — and it was measuring the **open breezeway, the front porch, and the rear porch**, and had **MISSED the living room, kitchen, dining, entry, main hall, and attached garage** entirely. The errors CANCELLED so the total looked right. ⛔ **NEVER trust a total without verifying each ROOM is correctly identified and present.** (Same trap as the offsetting category errors across whole-job grades.)
  - ⛔ **PURE PIXEL/BLOB DETECTION CANNOT tell a conditioned room from a PORCH (roof + COLUMNS, open sides), a BREEZEWAY (open passage), or a GARAGE.** That is a SEMANTIC call, not a geometry one. Convention (researched): exterior walls draw THICK, interior THIN; doors = line + swing arc (pocket = line into a rectangle, slider = 2 lines meeting mid, bifold = triangles); windows = thin rect in wall; **porches/breezeways are bounded by COLUMNS (isolated posts), not continuous walls**; every space has a LABEL; legend is in the title block.
  - ⭐⭐⭐ **THE FIX = LABEL-ANCHORED, SELF-VERIFIED reading:** (1) read EVERY room label; classify conditioned (LIVING/KITCHEN/DINING/ENTRY/HALL/BED/BATH/CLOSET/OFFICE/CRAFT/LAUNDRY/UTILITY) vs EXCLUDE (PATIO/PORCH/GARAGE/BREEZEWAY/DECK). (2) Only measure regions a CONDITIONED label actually sits in — porches/garages/breezeway drop out by their own labels (validated: Pack now excludes GARAGE 855 + PATIO, captures living/family/entry). (3) **SELF-VERIFY against the plan's OWN data — the three gates that must ALL pass before "done": conditioned area RECONCILES to the heated SQFT schedule (Pack 4,326); EVERY interior label appears in the measured list; NO exterior label does.** (4) Use VISION to confirm the annotated overlay before trusting it. I own the judgment + verify it myself — no asking Jason to mark/approve.
  - **Open issue (tractable):** rooms still merge with an adjacent garage/porch through their connecting door (→ "mixed" region, dropped) — SEAL the conditioned↔exterior doors (known from the door schedule: dining/garage, utility/garage, patio doors) before flooding. Then re-validate area = 4,326.
  - ⭐⭐⭐ **GARAGES ARE PART OF THE HOUSE for interior finishes (Jason) — INCLUDE BOTH attached AND detached in the room/perimeter measurement** (drywall, paint, etc.). ⛔ I wrongly excluded them. Apply the RIGHT finish per garage by READING its plan note: **attached garage = drywall + paint; detached (Pack) = ½" sanded plywood walls + open-rafter ceiling (a plywood line, NOT drywall) + paint.** Base/crown generally stay OUT of garages. So there are TWO perimeter sums: BASE/CROWN = heated rooms only; DRYWALL/PAINT = heated rooms + BOTH garages. The SQFT-schedule answer key for drywall = heated + attached gar + detached gar (Pack 4,326 + 1,215 + 1,003).
  - ⭐⭐⭐ **HOW TO HARDEN THE TOOL = READ PLANS WITH A HUMAN EYE + REASONING (Jason's directive). INVERT THE HIERARCHY: VISION + reasoning DECIDES, code only MEASURES, the SQFT schedule VERIFIES.** A human doesn't flood-fill — they look, reason ("that's a porch with columns; this is the family room, here are its walls; family+kitchen+dining are ONE open space → trace the outer walls + partition stubs, not 3 rectangles"), and measure to the scale. Method: render at readable zoom + CALIBRATED GRID (the scale ruler) → eye enumerates + classifies every space → eye traces each space's walls → code computes the perimeter from what I identified → reconcile to the SQFT key. CV flood-fill is only a fast FIRST DRAFT my eye audits/corrects, NEVER the decider. The room-by-room eye-read (same discipline that nailed countertops/doors) is the reliable method TODAY; each plan read that way is training data to harden the auto-tool.
  - ⛔ **VERIFY BY LOOKING AT THE RESULT, not the code's label.** I claimed "garages captured (orange overlay)" off the code's text output WITHOUT opening the overlay — Jason looked, they weren't cleanly there (garage interiors LEAK through the 14-16' garage-door openings, same as patio doors; only the enclosed toilet stayed a region). SEAL garage doors too. And the disk-seal I used draws a fake ARC into the space + eats area — seal with a STRAIGHT THRESHOLD LINE along the wall, not a circle. Always crop+view the overlay at each space before claiming it.

# Data point #37 — ⭐⭐⭐⭐⭐ THE ENGINE'S CORE ARCHITECTURE: MASTER MEASUREMENTS → TRADE DERIVATIONS (Jason's design)
**The whole estimator is built on a FEW MASTER MEASUREMENTS, read once with vision+geometry, verified, then MOST TRADES are DERIVATIONS off them.** This is WHY Jason's manual measurement list starts with perimeters + heights — they're the inputs the most trades divide from. Program the engine this way; don't re-measure the house per trade.
- ⭐ **MASTER 1 — EXTERIOR perimeter (+ wall heights):** the SHELL skeleton. `perimeter × height = exterior wall area`. **Feeds: siding/brick/stone field area, exterior framing, sheathing, house wrap, exterior insulation, exterior paint (all = perim×height); foundation footing LF + slab edge + foundation wall; fascia/soffit/gutters (eave run ≈ perimeter); corner boards (#corners×height); termite; waterproofing.** A dozen+ trades off one measured loop — that's why it's a FIRST measurement.
- ⭐ **MASTER 2 — INTERIOR room model:** per room = {name, type, floor_area, wall_perimeter, ceiling_height, floor/wall/ceiling finish, conditioned?, wet?, gets_base/crown/QR?}. **Feeds (AREA): flooring per room, tile floors, ceiling drywall+paint, ceiling insulation, electrical/HVAC/final-clean ($/SF). (PERIMETER): base, quarter round, crown(+coffers). (PERIM×HEIGHT): drywall walls, wall paint, tile walls/wainscot.** ⛔ GARAGES are part of the model (attached=drywall, detached=plywood, both paint). Open-concept = ONE space (outer walls, not N rectangles).
- ⭐ **MASTER 3+ — roof planes+pitch, gables, site (driveway/sod off site plan):** feed roofing (Σ footprint×pitch factor), cladding gables (Σ½·run·rise), sitework.
- ⭐⭐⭐ **THE METHOD IS SYSTEM-WIDE:** vision IDENTIFIES (read like a human — walls/doors/columns/labels), code MEASURES (geometry), footprint/schedule VERIFIES — for floor plans, elevations, roof, AND site. Engine: `room_perimeters` is MASTER 2's start; build a parallel exterior-perimeter master + the room-model struct so every interior+shell trade reads from them. **Measure the skeleton once, accurately; derive the rest.**

# Data point #38 — ⭐⭐⭐⭐⭐ TILE: THE PER-ROOM METHOD (Jason: "you just killed it... this is exactly how you estimate. this is how each room should be done")
**Tile is done ROOM BY ROOM. For each wet room: read the room off the plan (bounded by WALLS + DOORS, never by interior partitions), find the wet zone, measure footprints + wall runs, apply ceiling height, add waste. Lynn's Bath ran ≈$19.5k and matched Jason's number closely.**

⭐ **ROOM = walls + door openings.** A partition/pony wall does NOT start a new room. Measure the WHOLE room wall-to-wall, door-to-door. (FAILURE that triggered this: I cropped Lynn's bath to the shower partition and lopped off the freestanding tub + half the shower — undercounted the room ~25%. Jason: "you cut part of lynns shower off... that is a crucial part." Always render the FULL room and confirm boundaries before measuring.)

⭐ **SHOWER BOUNDARY = where the enclosure starts** = the GLASS door/wall, OR (this plan) the PARTITION-WALL OPENING. Look every time for which it is — sometimes glass, sometimes just an opening. That boundary line is where the **mud bed + shower floor START**. Wet-zone footprint = area inside that line.

⭐ **FREESTANDING TUB — tile rules (2 cases):**
  - ALWAYS: floor tile runs UNDER the tub.
  - Tub INSIDE the shower (Lynn's): the walls encompassing it get **FULL-HEIGHT** tile (they're shower walls); and the **mud bed runs under the tub too** (it's in the wet room).
  - Tub STANDALONE outside the shower: floor tile under it **+ a 3–4 ft tile surround** on all walls that encompass it (NOT full height).

⭐ **FLOOR TILE = GROSS room area — tile runs UNDER the vanity, do NOT deduct cabinet footprints.** Dry-floor SF = room SF − wet-zone SF (the wet zone is billed as shower floor, not field floor).

⭐ **PONY/PARTITION WALL is FULL HEIGHT and gets tile** (shower side).

⭐ **10% WASTE on ALL tile + flooring/wall products** (apply to the measured QUANTITY; whole per-SF line scales — same convention as trim's 10%).

⭐ **CEILING HEIGHT drives "full height."** Pack 1st floor = 9'-0" [MEASURED p11 "Ceiling Finish – 1st Floor 9.0'"]. Found it on the ELEVATIONS, not a notes table. "Full height" shower/wet-wall tile = floor→ceiling.

⭐ **PACK HAS NO INTERIOR ELEVATIONS** — sheets 14 (Kitchen/Pantry/Mud) and 15 (Other Room Elevations) are BLANK template sheets (title block + logo only; confirmed via vector count, image scan, render). So tile HEIGHTS/scope are not drawn → they're builder selections (mud-bed extent, wall height, niche, glass). Footprints + wall RUNS still come off the floor plan; only the vertical info is missing.

**TEMPLATE RATES (per SF installed, mat+labor bundled):** floor tile $16 ($4 allow+$3 sundries+$9 labor); shower/wet wall tile $27 ($4+$3+$5 Schluter+$15 labor); mud bed $75/SF; shower floor tile $15/SF; niche $300 labor + $15/ft tile; shower bench $500+$350; glass framed $1,500 / frameless master $2,000 / tub-shower framed $1,200; fiberglass surround or pan $500 each (alt when NOT tiled). Kitchen backsplash $36/SF ($15 allow+$3+$18 labor).

**LYNN'S BATH worked example (LOCKED):** room 25.4'×7.96'=202 SF, ceiling 9'. Wet zone (west wall→partition, 10.7'×7.96')=85 SF. Walls 34 LF×9'−window=292 SF. With 10% waste: mud bed 93.5 SF×$75=$7,013; shower floor tile 93.5×$15=$1,403; shower walls 321.2 SF×$27=$8,672; dry floor 128.7 SF×$16=$2,059; niche×1=$360; open shower (no glass)=$0. **TILE = ≈$19,500.**

# Data point #39 — ⭐⭐⭐⭐⭐ CABINETS = LINEAR FEET, ALWAYS, EVERY ROOM (Jason rule) + COUNTERTOP IS ALWAYS A MEASURED POLYGON (never LF×nominal depth)
**ALL cabinets are measured by LINEAR FOOT — never by box/each — in EVERY room, always.** Base cabs, island, uppers, uppers-to-ceiling, full-height, vanities — all LF. The estimate template's "ft²" unit on Vanity Cabinets (r319 $150, r320 hardware $6, r321 install $100) is a UNIT MISCUE — read it as **per LF**. Tall/full-height cabinet rate = $300/LF (template r247, kitchen "LF of Tall Cabinet"); stain-grade extra $110/LF (r250). (Same family of template unit miscues as QR-by-SF→LF, data point #36.)
- LYNN'S vanity measured: 10.67 LF run = 7.48 LF base + 3.19 LF full-height linen towers (2×U18). By LF: base 7.48×$150=$1,122 + towers 3.19×$300=$957 + hw 10.67×$6 + install 10.67×$100 ≈ $3,210. (Box-based ft² interpretation had over-stated it ~$5.5k — LF is right and Jason-confirmed.)
⛔ **REPEAT-OFFENDER GUARD — COUNTERTOP:** I again gave a countertop as "16 SF (7.5 LF × 2.1 deep)" = the BANNED base-LF×nominal-depth shortcut (data point #35). Jason: "you did not give me the countertop." A countertop is ALWAYS the MEASURED slab POLYGON: actual run × actual depth (front overhang edge → back wall, measured off the plan), then L1 non-kitchen rule = over-measure +4–6" into every wall the top touches (folds the 4" back/side splash in). Lynn's vanity top MEASURED = 7.48 LF × (2.17' measured depth + 0.42' back-wall over-measure) = **19.4 SF** L1 ×$35 + $100 sink cutout. NEVER state a countertop SF without the measured run AND measured depth behind it.
**ROOM-LEVEL FINISH SCHEDULE works** (Jason asked for ALL finishes in Lynn's bath): cabinets(LF)+countertop(polygon)+tile+tub+toilet+plumbing fixtures(allowances)+plumbing rough-in($800/fixture-opening, template r189)+light fixtures/accessories. Template per-bath allowances (Bath-1 ref): toilet $150, vanity sink $125 + faucet $150 + drain kit $20, mirror $120+$25 install, towel/accessories $50+$25, vanity light fixture $100, shower valve+head $400, freestanding tub $1,000 + tub valve $600 (alcove tub $500+$400 valve; drop-in $700+$400+platform). Lynn's bath ALL finishes ≈ $29,400 builder cost (tile $19.5k = ~2/3).

# Data point #40 — ⭐⭐⭐⭐⭐ TILE-UNDER-TUB depends on TUB TYPE + ALWAYS ASK FOR THE SELECTION CHOICE + DON'T PATTERN-MATCH ROOM CONTENTS (Jason: "excellent measuring... always ask for selection choice")
⭐ **TILE UNDER A TUB DEPENDS ON THE TUB TYPE:**
  - **FREESTANDING** tub → floor tile runs UNDER it (data #38, Lynn's).
  - **ALCOVE / BUILT-IN** tub → tile does NOT go under; DEDUCT the tub footprint from floor tile (Jason confirmed, craft bath: floor = 82 SF − 13 SF tub = 69 SF).
⭐ **TUB-SHOWER COMBO** (alcove tub with a shower over it): the TUB IS THE PAN → **no mud bed, no shower-floor tile**. Just the fixture + a **tile surround** on the 3 enclosing walls (deck→ceiling, full height per the tub-in-wet rule). Alcove tub allowance $500 + valve $400. Tub-wall tile rate = $22/SF ($4 mat + $3 sundries + $15 labor, NO Schluter on tub walls).
⭐⭐ **ALWAYS ASK FOR THE SELECTION CHOICE.** Where scope has an owner-selection fork, surface it — never silently assume. Known forks: **tub surround TILE vs FIBERGLASS ($500 flat)**; freestanding vs alcove vs drop-in tub; shower TILE vs fiberglass surround/pan ($500); countertop **L1 $35 vs L3 $55**; fixture allowance tiers. (Craft bath: it's tile, but "some people choose fiberglass — so always ask.")
⛔ **DON'T PATTERN-MATCH ROOM CONTENTS — LOOK.** I almost listed the craft bath as "vanity + toilet" from the small-bath pattern; it has a TUB (Jason: "what did you miss?"). EVERY room: render + enumerate EVERY fixture off the plan before pricing. Pattern-matching = the laziness that skips the measurement.
**CRAFT BATH worked (LOCKED ≈$9,200):** 82 SF room (label 11'-11×6'-11 verified). Alcove tub+valve $900; tile surround 72 SF×$22=$1,738; floor 69 SF (tub deducted)×$16=$1,216; niche $360; vanity 5.17 LF×$150+hw+install $1,324; L1 counter 11.7 SF $510; toilet $150; sink/faucet/drain $295; rough-in 3×$800=$2,400; light+accessories $320. **RUNNING BATH TOTALS: Lynn's $29.4k · Ralph's $17.6k · Guest $11.7k · Craft $9.2k.**

# Data point #41 — COUNTERTOP LEVEL SELECTION (Jason, Pack): L3 = kitchen + BOTH master/primary-suite baths; L1 = everywhere else
**Default countertop-level pattern:** **L3 granite/quartz ($55/SF)** on the **kitchen** and **every bath attached to the master/primary bedroom** (Pack = Lynn's + Ralph's his/hers master baths). **L1 remnant ($35/SF)** on **all other rooms** (guest, craft, powder, detached/pool baths, laundry). This resolves the L1-vs-L3 fork from data #39; still surface it as a selection (data #40) but this is the default. Pack update: Lynn's counter 19.4 SF→$55=$1,067; Ralph's 14.6 SF→$55=$803 (both +$100 cutout). REVISED BATH TOTALS: Lynn's $29.8k · Ralph's $17.9k · Guest $11.7k · Craft $9.2k · Powder $4.8k · Detached $4.4k · Kitchen backsplash $1.9k = **~$79.7k whole-house tile+bath finishes.**

# Data point #42 — INSULATION method + SPRAY-FOAM rates + DETACHED-GARAGE / roof-to-eaves scope (Pack; Jason grinding for accuracy)
**INSULATION derives off Master-1 (exterior perimeter + heights) + gables — the "easy" trade IF the envelope is measured.** Method (Jason): WALLS = heated exterior perimeter × wall height (9') + gable areas + the garage/house common wall (garage = unconditioned). CEILING/ROOF = SELECTION: **blown → ceiling SF; spray foam → ROOF SF.** Read the plan NOTES for which — Pack Note 19 "OPEN CELL SPRAY FOAM IN ROOF AND ATTIC" (house), Note 18 "SPRAY FOAM IN ROOF AND WALLS" (det. garage). Note 21 = "pink wall = offset insulated wall." **DON'T ask what's on the plan — read the note schedule (research routine).**
⭐ **SPRAY-FOAM RATES (Jason, override the template's blown/batt $1.25 wall / $0.85 ceiling): WALLS $1.00/SF, ROOF $1.35/SF.** The template insulation lines ($1/floor, $1.25/wall, $0.85/ceiling) are BLOWN/BATT — do not use them on a spray-foam job; foam roof is the expensive line.
⭐ **ROOF FOAM SPRAYS ALL THE WAY OUT (to the eaves), not just over conditioned space** (Jason). Roof foam SF = full roof-plan footprint (heated + eave band) × pitch factor. Pack eave = only ~1 ft (shallow; roof width 107.4' vs wall 105.3'); pitch 8:12 everywhere → factor 1.202. House roof = (4,326 + ~350 eave)×1.202 = 5,620 SF; garage roof = (1,003+130)×1.202 = 1,361 SF.
⛔ **MISS Jason caught: I scoped only the house and forgot the DETACHED GARAGE is CONDITIONED this job** (Note 18 spray foam roof+walls) → it's a SECOND insulated envelope (walls perim 129'×9' + gable ends + roof). Always ask/verify per-job which outbuildings are conditioned. Attached garage assumed unconditioned (common wall only) — flag.
**PACK INSULATION ≈ $14,975:** house walls ~4,110 SF×$1 + house roof 5,620×$1.35=$7,587 + gar walls ~1,441×$1 + gar roof 1,361×$1.35. ⚠️ House wall perimeter still ~345'±10' — the complex U/wing footprint auto-trace FAILED (contour zig-zagged); must do the manual segment-by-segment walk (plan+elevation cross-ref for hidden walls). ENVELOPE PERIMETER on complex footprints = my #1 unreliable capability (confirmed again).


# Data point #39 — PACK RESIDENCE (Ralph & Lynn Pack; 16-sheet set; PR-Pack) — full cold estimate vs J&J takeoff, RECONCILED
Single-story 4,326 htd + 1,215 att garage + 1,003 DETACHED conditioned shop (mini-split) + 828 covered patio; MONO SLAB everywhere; city water + septic; ALL-MASONRY exterior (brick+stone, NO siding); metal-wrap fascia + vinyl soffit; 8:12 roof throughout (arch shingle); open-cell spray foam roof/attic + batt walls; 9ft ceilings, 12ft living room; Control4 + cameras + security + powered gate; engineered-wood floor throughout + tile wet areas. Cold subtotal $985,795 vs Jason $1,051,449 (amount w/ per-line markup) = -6.2%; RECONCILED to $1,143,083 after catching Jason gaps.
- ⭐⭐ GEOMETRY ENGINE VALIDATED cold vs Jason hand takeoff: Framing SF 7,372=7,372 EXACT; Brick 5,070 vs 5,068 EXACT; Stone 2,170 vs 2,308 (-6%); Footing 760 vs 756 LF EXACT; Roof surface 11,721 vs 12,205 SF (-4%); Drywall 21,996 vs 20,760 (+6%). The ASSUMED 70/30 brick/stone split hit his actual almost dead-on. Roofing $ reconciled to the dollar using decoded Southern rate ($175/sq field, my $28.2k vs his 12,205 SF x$2.25 = $29.4k).
- ⛔ KNOWN BIASES REAPPEARED EXACTLY: wall insulation area -15% (5,880 vs 6,919) and fascia/roof-edge -17% (550 vs 661 LF) — my envelope/edge contour trace reads LESS building than is there (smooths jogs/porches, loses rake foreshortening). PAD envelope + edge, or measure every run.
- ⛔ JUDGMENT-UNDER-MISSING-INFO is where I lost, not geometry: (1) Interior elevation sheets 14/15 were BLANK -> I biased cabinets/trim LOW (-$54k): missed 332 LF wood beams, a 37-LF mud/bar cabinet run, full crown (1250 vs 900 LF), and trim labor on LF not the 6,544-SF shop basis. RULE: blank elevations = ASK for cabinet/trim numbers, do NOT silently bias low. (2) Un-scalable site items (driveway not dimensioned, sod area unknown) -> I PLACEHOLDERED low (300 LF gravel vs his 6,736 SF concrete; 1 sod unit vs his 40 pallets). RULE: a $20-40k line that cannot be scaled gets an ASK, never a $450 placeholder. (3) I INVENTED scope: added a $3,500 water softener nothing called for (city water). RULE: never add a line the plans/notes do not call for.
- ⛔ I over-enumerated PLUMBING openings (30 fix+20 water vs his 24+9 — double-counted drain+supply per fixture, counted hose bibs as openings) -> +$30k high. Count a fixture opening per FIXTURE, water openings sparingly.
- ✅ ENGINEERED FLOOR OVER GARAGES — CORRECTED RULE (I was WRONG): I zeroed Jason's 2,218 SF engineered floor because 'mono slab = no engineered floor.' WRONG. Jason puts an engineered floor/CEILING system over LONG CLEAR-SPAN GARAGES with no bearing walls to carry the ceiling/roof load. On a slab house, engineered floor line = garage/shop long-span ceiling support (area = garage+shop SF). Do NOT zero it; expect it over big open garages/shops.
- ✅ CLAUDE CAUGHT (ground-level-risk value, his budget carried $0): Low-voltage/Control4/cameras/security/powered gate — note schedule explicitly requires all of it; $0 = $40-60k change-order exposure. Carried as flagged allowances ($28k LV + $18k Control4 + $10k gate). Also his roof insulation was $0.85/SF (a BATT rate) on 12,205 SF while notes call for OPEN-CELL FOAM (~$1.75-2.10/SF) -> repriced (his AREA was right = roof surface; his RATE was low). NOTE spray-foam AREA = roof SURFACE, not footprint (my error was footprint). Jason caught the $9,500 generator I missed — two independent takeoffs each catch the other's holes.

# Data point #43 — ⭐ GOLDEN TEST HARNESS built + CABINET DETECTOR rebuilt (engine reliability backbone)
Built the regression suite the engine was missing: `tools/tests/run_golden.py` + `tools/tests/golden/<house>/expected.yaml`. Runs headless, prints per-house per-trade table (measured|expected|delta%|PASS/FAIL) + summary, exits non-zero on any FAIL. Every expected value traces to THIS file (none invented). One command: `python tools/tests/run_golden.py`.
- ⭐ **WIRED + GREEN today (8/8 graded asserts PASS, exit 0):** WILSON — framing 5,792.6 SF (=5,792.59, given-data 0%), heated 3,913.6 (0%), foundation-wall 152.2 LF (vs 156 invoiced, −2.5%), basement area 1,349 SF (vs ~1,372, −1.7%). PACK — framing 7,372 SF EXACT (0%), heated 4,326 (0%), kitchen cabinet base run 48.7 LF (vs 49.5, −1.6%). BURNS — heated 1,950.7 (vs 1,951, 0%). 3 houses fully green.
- ⚠️ **KNOWN-GAP (reported, not build-breaking):** HOLBROOK slab area — `trace_footprint` with a generic clip traces ONE room of the subdivided slab (~1,688 SF) not the whole footprint; #24 only hit 2,954 SF with a hand-tuned clip + dash-sealing. **Auto-region on subdivided slabs is THE open engine gap** (same recurring bottleneck as #26). Flagged `known_gap: true` so it's visible + auto-promotes to PASS if the engine ever closes it.
- ⚠️ **NEEDS PLAN FILE FROM JASON (fixtures exist, expected values recorded, marked plan_missing):** PETERSON (only a 2-page estimate PDF on disk, no dimensioned Fairview drawing set) — roof 48.97 sq, heated 2,375. ROBERTS (only image-only estimate exports, no plan) — framing 3,403, heated 2,127, sell $591,341 (full-cost reproduction needs an estimate-assembly probe the engine doesn't expose yet). LANKFORD present but a RASTER scan (0 vector text) → vector probes correctly abstain; its 198 LF wall / 98 LF waterproofing came from Jason's GREEN trace, not the raw PDF (probes not wired to a marked screenshot).
- ⭐⭐ **CABINET_RUN_LF REBUILT (Deliverable B).** The old scaffold returned ~19 LF (missed island) / ~900 LF (ate floor hatch) because casework shares the vector layer with the tile hatch + dim lines — un-isolable by a bare 24"-offset filter. **FIX = CABINET-TAG-ANCHORED:** the plan LABELS every cabinet with its nominal item width (B36=36", SB50=50", DCB36R=36" corner, U242496=24" tower, OTC33=33" oven tall, W=upper). Cabinet tags are direct item dimensions, not an area schedule and not a substitute for the core-area measurement gate. Read codes in the kitchen clip, dedupe double-draws, classify lower/upper/tall; DETECT the island (two back-to-back lower rows sharing a >4ft x-span) and measure it as its TWO parallel faces × length (a plan island's LF counts both faces — tag widths under-count it). **Pack kitchen: base run 48.7 LF vs Jason 49.5 (−1.6%) WITH the island captured (23.96 vs 24.41, −1.8%)** = lower 12.0 + island 23.96 + tall 12.75. Matches #34 structure.
- ⛔ **STILL `calibrated: False` — BY DESIGN.** DEV_SPEC B3 requires ±10% with island captured on ≥3 REAL kitchens before flipping True; only PACK has cabinet-LF ground truth + a clean plan wired today (Wilson/Burns kitchen cabinet-LF + clips not yet sourced). So the function keeps returning `calibrated: False` and the estimate must fall back to a hand-traced number — the same do-not-auto-ship discipline as the roofing placeholder. **UPDATE (see #44): the Wilson/Burns kitchen ground truth WAS found, but the tag-anchored method doesn't transfer to their plans (Wilson tags cabinets on a separate elevation sheet; Burns tags no width codes) — so calibrated stays False and reaching 3 kitchens needs a different (elevation-parse or pixel) method, not just wiring more clips. A clip-independence fix WAS shipped (auto-cluster).**
- **Meta:** the harness makes accuracy PROVABLE and non-regressing (also the Level Ground proof-of-accuracy backbone). Engine self-test (parser/framing/gable) still ALL PASS after the cabinet rebuild — no regression.

# Data point #44 — CABINET calibration attempt on Wilson + Burns: ground truth FOUND, but the tag-anchored method does NOT generalize (honest STOP, calibrated stays False)
Tried to flip `cabinet_run_lf` to calibrated:True by validating 2 more kitchens (Wilson + Burns) alongside Pack. Found the KITCHEN base-run GROUND TRUTH for all 3 in Jason's own files (no reverse-fit):
- **PACK** (calibration.md #34; his hand takeoff): lower 16.2 + island 24.41 + tall 8.90 = **base run 49.5 LF**.
- **WILSON** (`Downloads/Wilson, Ken and Dang - Post Precon Meeting - Estimate Items.xlsx`, r171/r173, "Room Finishes - Kitchen"): LF of Lowers 18 + LF of Island 18 (no tall line) = **base run 36 LF**. (Uppers 22, uppers-at-ceiling 22, vent-hood cabinet 1 ea — not base.)
- **BURNS** (`Downloads/Measurements - Burns, Bethanie.xlsx`, "Measurements" sheet r255/r264/r266, source "bid set - page 5"): Cabinets-Lower 23.96 + LF of Island 5.51 + LF of Tall (Fridge/Oven/Linen) 5.92 = **base run 35.39 LF**. (Uppers 10.79 — not base.)
- ⛔⛔ **THE METHOD DOESN'T TRANSFER — a real structural finding, not a tuning miss.** The tag-anchored reader needs the plan to LABEL each base box with a width code (B36/SB50/DCB36R/U242496…) **in plan view on the FLOOR PLAN.** True for Pack. But: **WILSON** tags cabinets only on a separate cabinet-DETAIL sheet (p15 = "S4 …", 3/16") that mixes plan callouts with MULTIPLE elevation views (4+ "KITCHEN" labels + an "ISLAND" elevation) → the same box appears in both a plan callout and an elevation (double-count), and the island is drawn as an elevation, not a closed plan box, so the parallel-face island geometry can't read it. Wilson's FLOOR PLAN (p8) carries only elevation-reference bubbles (E10/E11…), zero width codes. **BURNS** tags NO width codes anywhere on the floor plan (p5) — only room labels + ELEVATION bubbles (E5/E6/E7); cabinets are drawn but unlabeled. So `_classify_cab` finds 0 tags on both floor plans.
- ✅ **KEPT calibrated:False + hand-trace fallback** (guardrail: don't auto-ship an uncalibrated cabinet number; don't reverse-fit; don't loosen tolerance). Only Pack passes the tag method; the 3-kitchen bar is unmet.
- ✅ **ROBUSTNESS FIX SHIPPED anyway (clip-independence):** `cabinet_run_lf` now AUTO-ISOLATES the kitchen casework cluster (`_cluster_cabs`, single-linkage on base tags, link_ft=7 default; kitchen = densest cluster by total width). Pack now returns base 48.7 LF / island 24.0 captured identically for EVERY clip from a tight box up to the WHOLE PAGE (0,0,2592,1728) — the old bespoke-clip dependency (32 LF + dropped island on a rough clip) is gone. The golden harness now probes Pack cabinets with a whole-page clip and PASSES (-1.6%), and requires island_captured before returning a number.
- ⭐ **NEXT to actually reach 3 kitchens:** the tag method is Pack-specific; Wilson/Burns need EITHER (a) parse the cabinet-ELEVATION sheet (dedupe plan-vs-elevation views of the same box; read the island off its plan callout) — Wilson's codes are all there on p15; OR (b) a pixel/geometry plan-view tracer that doesn't rely on labels (Burns has no labels at all). Ground truth above is banked so that method can be graded immediately when built. Engine self-test still ALL PASS; golden suite still exit 0 (8/8).


---
## Data point #40 — TEMPLATE AUDIT + CONFIRMED CONVENTIONS (7/5/2026, Jason direct)
Jason handed the canonical takeoff sheets ("Measurements/Estimate - Newest template 12_8_2025 (3)"),
installed at templates/ (old ones -SUPERSEDED-2026-07-05). Full-row audit -> reference/template_gap_memo_2026-07-05.md;
corrected v2 DRAFTs in Downloads (pending Jason's review before promotion to canonical).
**CONFIRMED BY JASON (supersede anything contrary):**
1. **Roof pitch-zone quantities = SLOPED SURFACE per zone** (his takeoff software applied the pitch
   multiplier per slope as he measured; zones summed). Engine must NOT re-apply pitch factors to his
   sheet quantities. (Engine-measured footprints still get pitch_factor applied — the convention is
   about what HIS sheet rows contain.)
2. **Shingle waste = 15%** (approved changing his sheet's 25%; matches Southern reconciliation).
3. **Markup rationale:** subs/labor 7%, materials 15% (= tax + markup), allowances 8% (= tax cover).
   FEE 15, EQUIPMENT 7. Allowance rows drifted to 15% in his template — normalized to 8 in v2.
4. Template gaps found (now lines in v2, engine must always carry): laundry room section, column
   wraps EACH (6x6 $270 / 12x12 $480), stone veneer measurement line, spray-foam roof line,
   crawl encapsulation, punch-out allowance, flashing/water-table $3.50/LF, band board $7.50/LF,
   ext crown $6.50/LF, ceiling-height + #HVAC inputs, closet shelving, screened porch input.
5. Stale rates corrected + date-stamped in v2: framing lumber 8->14, framing labor 5.50->6.50,
   plumbing restructured to $8,000 base + $450/fixture + $400/water, lap 2.50->3.30 (CONFIRM live),
   frieze 3->4.50, beam wrap split 11 Hardie/23 cedar, brick labor 5->9, #34 gravel -> $0.80/SF.
6. UNCONFIRMED rates flagged in v2 descriptions (set at first use): spray foam $1.75/SF, encapsulation
   $4/SF, punch-out $2,500, blower door $450, shiplap $3.50+$3, mudroom built-ins $1,500.
7. Still open from memo: "Garage Wrap" $200 line meaning; treads $35 basis confirmed per-TREAD (meas
   sheet row renamed "count TREADS").

**#40 addendum (7/5/26, Jason direct):**
- **Garage HVAC = measured off garage SQFT** (the SF determines the unit size), NOT each —
  v2 estimate corrected back; quantity = garage SF, unit cost = per sized system at bid.
- **GENERIC ROOM REQUIREMENT:** plans will contain rooms no template pre-programs (theater,
  scullery, office, gym...). The engine must identify what a room IS from the plan, know/research
  what goes in it, and measure each component — a generic room record + room-type registry with
  research fallback, not fixed sections. Registry seeds = the template's known rooms (kitchen,
  pantry, game room, baths, laundry). Unknown room label -> resolve_unknown path -> bank it.
- Estimate v2 APPROVED by Jason (with the HVAC fix); both v2s promoted to templates/ canonical.

**#40 rates CONFIRMED (7/5/26, Jason direct — now in the canonical templates):**
spray foam ROOF $1.35/SF (area = roof surface) · spray foam WALLS $1.00/SF (new line) ·
crawl encapsulation $3/SF · blower door $450 ok · shiplap/accent $5.50/SF turnkey (single SUB line) ·
mudroom built-ins $300/LF (per-LF, new measurement line) · GARAGE WRAP = trim around the exterior
framing of EACH garage door (header+surround), $200/each, qty = # garage doors (matches Southern's
decoded $195/ea 8x7 wrap). Still UNCONFIRMED: punch-out $2,500 placeholder.

**#40 addendum 2 (7/5/26, Jason direct):**
- **Foam≈batt market context:** post-COVID competition dropped spray-foam pricing in J&J's area to
  ~batt parity (foam roof $1.35, foam walls $1.00, batt walls holding ~$1.25). The $1.00 foam-wall
  rate is CORRECT, not an error. Re-check this parity when re-confirming rates — it's market-driven.
- **Punch-out DERIVED FROM ACTUALS (code 20.10, 4 closed jobs — data point #41):** Roberts $3,950
  (2,127 htd = $1.86/SF), Hernandez $1,595 (1,863 = $0.86), Darwish $11,747 (4,517 = $2.60),
  Waddell $3,248 (1,882 = $1.73). Mean $1.76/SF, weighted $1.98/SF. **RATE: $1.75/heated SF standard,
  $2.50/SF high-end** (Darwish evidence). Quantity basis = HEATED SF. Anthony excluded (finishes not
  complete at export); Grotsky in QBO only. Punch scales with size/finish — never a flat allowance.
- **"Punch" AMBIGUITY (vocabulary):** Southern Siding titles their timber/column/bracket wood-wrap
  package "Punch <job>" — a Southern "Punch Estimate" PDF is NOT end-of-job punch-out labor. Three
  such PDFs re-confirm as billed ACTUALS: Burns punch = 8x 6x6 columns $270 + gable-truss wraps
  $695/$925 = $3,780; Wilson punch = 6x 6x6 + 15x 12x12 $480 + 2x gable brackets $535 + vertical
  porch trim $385 = $10,275; Peterson (1301 Sailview) punch = 2x 12x12 + corbels $105/$135 = $2,460.
  All match the decoded rate book exactly — PUNCH-scope (wood-wrap) rates now invoice-confirmed on 3 jobs.
- **⭐ THE TWO-ROLE MANDATE (Jason, verbatim intent):** Role 1 (most important): I am his SENIOR
  ESTIMATOR — he must trust me to do the job with AS LITTLE INPUT FROM HIM AS POSSIBLE ("if I have
  to do everything then I don't need you"). Highly detail-oriented, sharp — I CANNOT MISS. Role 2:
  everything built here becomes the Level Ground end-user product + J&J efficiency. Default to
  resolving things myself (plans → banked data → his files → QBO → research) and only ask when a
  decision is genuinely his (scope/selections/policy) — never make him do my legwork.

---
## Data point #42 — ENGINE: AUTONOMY GATE FIRST PASS (7/5/26)
New engine functions (validated then landed in jnj_takeoff.py + golden suite):
- **`find_drawing_region(page)`** — auto-locates the main drawing (walls = ONE connected network;
  2-ft grid clustering splits off title block/notes/details). Kills hand-fed clip= for wired probes.
- **`trace_footprint_clean(page)`** — footprint from CLASSIFIED wall segments only (solid, non-blue,
  wall-length, near-axis) rasterized to a blank canvas; clutter (text/dims/hatch/furniture) can NEVER
  enter the mask. Holbrook: blind trace 1,688 jumbled → 2,294 STABLE at any sealing (clutter immunity
  proven); remaining −27% = slab pocket not drawn in wall layers → close with dims-first
  polygon_outline (Phase 4 primary method on cut-up slabs; pixel trace = the cross-check).
- **Wilson foundation probes now FULLY AUTONOMOUS** (auto scale + auto region + prefer='largest',
  zero hand inputs) and IMPROVED: wall 155.9 vs 156 GV invoice (−0.0%, was −2.5% hand-fed);
  basement 1,371.5 vs 1,372 (−0.0%, was −1.7%). Autonomy ≠ accuracy tradeoff — it beat the hand clip.
- Golden suite: 12/12 PASS, 0 errors after the change (regression gate held).

**#42 addendum — ROBERTS + PETERSON PLANS DELIVERED (7/5/26):**
- **"Precon notes Jefferies (1).pdf" = the ROBERTS plan set** (title block "Roberts Residence"
  every sheet; Jefferies = 788 Jeffries Rd). 12 vector sheets; NONSTANDARD scale ppf=16.714
  (print-rescaled — dim-voting handled it, 187 votes). Roberts now GRADED: schedule reads
  heated 2,161 / framing 3,431 both +0.0%. ⚠ OPEN: plan prints heated 2,161 vs calibration #1's
  2,127 (Jason's basis) — +1.6%; reconcile with Jason (plan revision vs estimate basis).
- **"Precon notes Sailview (1).pdf" = the PETERSON plan set** — 11 vector sheets with ZERO
  text layer (all labels are curves). THE Phase-2 OCR fixture; probes SKIP by design until
  in-code OCR lands (never eyeball pitch/scale from pixels — the 17%-low "12:12-ish" lesson).
- Suite after wiring: **4 houses graded, 14/14 PASS, 0 errors** (burns, pack, roberts, wilson).

**#43 — PHASE 2 OCR LANDED: PETERSON READS END-TO-END (7/5/26)**
New engine functions: `ocr_words`, `vote_numeric`, `ocr_numeric_cell(psm8)`, `read_sqft_schedule_ocr`.
- **THE OCR LESSONS (hard-won, keep):** (1) plan-font digits mis-read under tesseract psm-7
  (Peterson 1969→1269 at conf 80 — HIGH confidence on a WRONG read, so confidence alone can't
  pick the culprit); **psm-8 (single word) + psm-13 majority voting reads them 18/18.**
  (2) Value cells must be read from the token's OWN bbox from the full-page pass — a hand-typed
  clip catches the neighbor (258 → 7528). (3) **The schedule's printed TOTAL row = the
  enumeration gate in code:** parts must sum to it; an unreadable cell is SOLVED from the total
  and flagged 'review', never silently shipped (ENTRY '6' too small to vote → healed to 6 exact).
- Peterson p2 integrated: heated 1969 (voted) + garage 559 + outdoor 258 + entry 6 (healed) +
  expansion 406 = printed TOTAL 3,198 exact. **Jason's heated basis 2,375 = 1,969 + 406**
  (future expansion built out — Jason confirmed).
- **Golden suite: 5 houses graded, 15/15 PASS, 0 errors** (burns, pack, peterson, roberts,
  wilson). Peterson heated_sf +0.0% via OCR — first zero-text-layer fixture to grade. This is
  the exact capability Level Ground needs for scanned homeowner uploads.
- NEXT (Phase 2 remainder): OCR the dimension strings + pitch callouts (16:12/5:12) on the
  Peterson roof/elevations → scale via scale_from_reference → roof_surface_sq assert (48.97 sq
  ±8%); then fold ocr_words fallback into detect_scale/read_dimension_chains.

**#43 addendum — PETERSON ROOF PLAN DECODED BY EYE (7/5/26, sheet p4):**
- ⛔ **OCR PITCH TRAP: tesseract reads "16/12 P." as "12/12"** (the stylized 6 collapses to 2) —
  a WRONG pitch at high confidence, the exact class of error that caused the original 17%-low
  miss. RULE: pitch callouts from OCR must be VOTED and, on any roof where zones matter,
  visually confirmed (render the callout crops) or cross-checked against the elevations'
  rise/run L-symbols. Never accept a single-pass OCR pitch.
- **True pitch inventory (read by eye off the sheet): 3/12, 6/12, 12/12, 16/12 + RADIUS
  (curved) roof sections** ("SEE RADIUS ROOF SECTION" ×2). Richer than cal #13's "5/12+16:12"
  shorthand — the PLAN is truth. Sheet prints SCALE: 1/4"=1'-0" (verify actual ppf via dims —
  set may be print-rescaled like Roberts' 16.714).
- Zone boundaries all drawn + labeled (RIDGE/VALLEY/HIP/PITCH CHANGE lines) — the surface
  measurement is footprint-per-zone × pitch factor + radius sections from their section detail.
- Roof framing notes on-sheet: 2x10 hips/ridges/valleys, 2x6 rafters @16" OC, plate hts in
  rake details — harvest for framing scope when estimating this house type.
- **PETERSON p4 DECODED INPUTS (read by eye, both halves — permanent fixture data):**
  Title block = "PLAN 1969, FAIRVIEW COTTAGE" (Elite Design Group 3/14/24 — plan number IS the
  first-floor heated SF). **OVERHANGS PRINTED IN CORNICE DETAILS: 12-inch soffit at siding
  walls, 17-inch at brick-veneer walls** (the exact input whose omission caused Burns' uniform
  −12.4% roof-footprint bias — measure, never default). **RADIUS RAFTER SECTION fully
  dimensioned** (curved rafter from 2x12: 3'-4" run, ~6'-7.5" radius, 2'-4" rise, bears common
  rafters on plate) — the bellcast/flared eave zones are computable. Zone-callout arrows
  ("N/12 P.") across both halves: 3/12, 6/12, 12/12 (many), 16/12 (many). The lone rise/run
  L-symbols are in rafter-bearing DETAIL boxes (not zone callouts) — don't map them to zones.
  A red-pen squiggle on the 8x8 timber detail = redline present; read redlines when estimating.
- NEXT concrete step for roof_surface_sq: face-decompose the roof outline by RIDGE/VALLEY/HIP/
  PITCH-CHANGE linework -> assign each face its arrow callout pitch -> footprint x factor +
  radius-flare additions from the section dims; verify ppf first (sheet says 1/4"=1' but check
  vs a printed dim — Roberts' set was print-rescaled to 16.714).

**#44 — PETERSON ROOF SURFACE GRADED: FACE DECOMPOSITION + SHEET-SOLVED SCALE (7/5/26).**
The first zero-text-layer GEOMETRY grade: **46.5 sq (mid) vs Southern's reconciled 48.97 =
−5.1%, PASS ±8%** — suite now 16/16 across 5 houses, exit 0. Engine: `roof_zone_surface()`
in jnj_takeoff.py; probe `peterson/roof_surface_sq` wired.
- **METHOD (validated end-to-end):** rasterize solid + DASHED vector segments (dashed
  pitch-change lines are REAL plane boundaries) → morph-close (45px @ zoom 3) → flood
  exterior → 31 connected components = roof planes; 18 assigned from 22 eye-verified pitch
  callouts (majority vote resolved the one conflict — a stray arrow tail crossing a ridge);
  surface = Σ face×pitch_factor, scaled by outline/faces = 1.072 (distributes boundary ink
  + slivers at the avg factor 1.475).
- **⛔ SCALE MUST BE SOLVED PER PAGE — this set proves it hard:** floor plan p2 = ppf 10.03
  (solved from TWO CAR GARAGE 559 SF face; second room OUTDOOR LIVING 258 → 9.74, agrees
  ~3%), roof plan p4 = ppf **16.2–16.5** (≈ Roberts' 16.714 print rescale — same "Precon
  notes" pipeline?). Same PDF, 60% scale difference page-to-page. Carrying p2's scale to p4
  would have read the roof at 115 sq (+135%). Wilson rule now twice-proven.
- **SCALE SOLVE WITHOUT ANY TEXT (the new trick):** filled roof-outline area A + eave
  perimeter P satisfy A/ppf² = underroof_SF + (P/ppf)·OH + 4·OH² — quadratic in 1/ppf.
  underroof 2,792 = OCR-verified schedule TOTAL 3,198 − 406 upstairs FUTURE EXPANSION; OH =
  the PRINTED 12"/17" cornice overhangs. Bounds honest: OH 12"→45.5 sq, 17"→47.5 sq.
- **Bias note (consistent with #39):** −5.1% mid is another "I read less building than is
  there" result — unmodeled bellcast/radius flares + zone-edge effects. Direction known; if
  a roof lands near tolerance edge, pad per the #39 envelope rule before pricing.
- **Failure modes hit + fixed on the way:** (1) interior-only mask ("solid = not-exterior"
  minus ink) makes every room/face its own island — largest CC was ONE room, not the
  envelope; envelope = interior|ink. (2) p2 bbox cross-ref DOA: dimension extension lines
  connect to walls, closing bridges the whole collage sheet (145×124 ft "envelope") — on
  collage sheets bbox cross-refs need the drawing isolated first. (3) Pitch callouts stay
  eye/VLM-verified, never raw OCR (#43 trap: "16/12 P." → "12/12").

**#45 — LANKFORD AUTO-MEASURED: OCR SCALE FALLBACK + PAIRED-PARALLEL WALL EXTRACTION (7/5/26).**
The "scanned, nothing auto-probed" fixture note was WRONG — Lankford is a ZERO-TEXT VECTOR
set (Peterson-class: full linework, curve-font labels). Two new engine functions:
- **`detect_scale_ocr(page)`** — scale from OCR'd dimension-CHAIN tokens: adjacent chain
  values v1,v2 sit ~(v1+v2)/2·ppf apart center-to-center; median over all pairs. Lankford
  p5: ppf **12.474** (printed 3/16"=1' print-rescaled ~92%; 0.8% spread). **HONESTY GATE
  VALIDATED:** on thin-CAD-font sheets tesseract yields junk and the gate returns None
  (Wilson p4, Peterson p2 both correctly refused) — the banked "tesseract misreads CAD
  dims" rejection stands; this fires only when the dim font is big/clean enough to vote.
- **`foundation_wall_loops(page, ppf)`** — poured walls by the PAIRED-PARALLEL geometry
  signal (two solid near-axis strokes 0.4–1.0 ft apart = a wall; hairline dims/extension
  lines and dashed beams have no partner → never enter the mask). Main basement loop
  **259.1 LF inside-face / 2,476 SF — STABLE across close 1–4 ft** (the raw-ink tracers
  had failed: enclosed-region gave 1 room, width-opening got nothing — the wall band is
  HOLLOW, two faces + sparse speckle; LOOK at the wall drawing style before picking an
  extractor).
- ⛔ **GEOMETRY ≠ SCOPE:** GV invoice #1211 = 198 LF, a SUBSET of the 259-LF loop (GV
  poured the 10' basement walls; wing/stem/walkout split needs wall-HEIGHT
  cross-referencing off the elevations — Phase 4 — or the green trace). Wired as
  known_gap, NOT tuned toward the target. Full loop inventory: main 2,476 SF/259.1 LF,
  wing 931/123.5, stair pocket 133/46.8.
- ⛔ **NOTE-BOX TRAP:** double-line text-box borders pair like walls (a 401-SF "loop" was
  the engineer's-note box) — pick loops by size/position, never sum blindly.
- Suite: 16/16 PASS + 2 documented known-gaps (holbrook pocket, lankford scope), exit 0.

**#46 — HOLBROOK KNOWN-GAP CLOSED: TRACER CHOICE IS A BOUNDARY-STYLE DECISION (7/5/26).**
slab_area_sf promoted from known_gap to hard PASS: **3,175 SF vs GEO invoice 3,122 = +1.7%,
fully autonomous** (detect_scale 18.084 high + find_drawing_region + trace_footprint).
Suite now **6 houses green, 17/17 PASS, exit 0** — Holbrook joins the graded set.
- **ROOT CAUSE of the -26.5% gap:** Holbrook's slab boundary is SHORT-DASH linework — every
  dash is under trace_footprint_clean's 1.2-ft segment floor, so the classified-segment
  canvas never contained the boundary at all (include_dashed changes nothing; the dashes
  are dropped by LENGTH, not dash-flag). Dash-merge (collinear pieces -> virtual lines) was
  built and tested but didn't extend the outline; the ALL-INK tracer already seals dashes.
- ⭐ **THE RULE (bank it): pick the tracer by BOUNDARY STYLE.** Solid drawn walls ->
  `trace_footprint_clean` (classified segments, clutter-immune — Wilson/Lankford class).
  Dashed/below-grade boundary (slab edges, footing lines) -> `trace_footprint` (all-ink +
  dash/door sealing, largest-contour ignores note blobs — #26b clip-invariance). Wrong
  tracer = stable-looking but WRONG number (2,294 was rock-stable and 27% low).
- ⛔ **AUTO-REGION PAD MATTERS:** find_drawing_region's default 2-ft pad clipped the dashed
  edge (2,848 SF = -8.8%); pad 3-15 ft ALL return the identical 3,175 plateau. Probe uses
  pad_ft=8. Clip-invariance across a wide pad range = the convergence signal to trust.
- The answer was already in THIS FILE (#26b measured 3,175 clip-invariant a week ago) —
  re-reading the calibration history before re-deriving saved the day. Remaining Holbrook
  item: foundation wall LF 178 (skeleton method read 159, -11%) still unwired.

**#47 — LANKFORD HATCH-DENSITY CROSS-REFERENCE (7/5/26): the concrete hatch ENCODES wall type.**
Per-edge scope classification of the 259-LF main loop, using the EXPLODED giant hatch path
(the whole plan's concrete speckle = ONE vector path with 3,124 items; explode items ->
25,269 mark positions -> per-edge density). Result: ALL 16 edges hatched (all poured), but
in TWO clean density tiers, ~26 vs ~100 marks/10ft, and the partition cross-references the
GV invoice:
- **DENSE tier = 163.7 LF vs GV's 10'+9' basement walls (146+17) = 163 LF -> +0.4% MATCH.**
- LIGHT tier = 95.5 LF = the 7'/6'/5' short walls (9+16+10=35 LF) + ~60 LF of shallow
  frost/brick-ledge wall (GV bills "slab/brickledge 178 LF @ $5" as a SEPARATE line;
  Jason's red "Brick Ledge" note sits on that side). Final 35-of-95.5 split needs wall
  heights off the elevations, or Jason's one-liner.
- ⭐ LESSONS: (1) drafters draw the concrete hatch as ONE page-spanning path — tiny-bbox
  filtering finds ~nothing (308 marks); EXPLODE d["items"] of any path with 500+ items.
  (2) Hatch DENSITY is a legend signal — tiers separated cleanly (26 vs 100, no overlap);
  cross-reference each tier's LF against the invoice height schedule. (3) First
  speckle-density attempt mis-classified 7 edges "framed" off noise-level counts — with a
  thin signal the CLASSIFICATION is garbage even when the geometry is exact; get the dense
  source first.
- Probe stays known_gap (measured full loop 259.1 vs asserted 198) with the tier finding
  in the gap note. Suite unchanged: 6 houses green, 17/17 PASS, exit 0.

**#47b — LANKFORD FOUNDATION-SCOPE GAP CLOSED FROM THE LOWER-FLOOR ENVELOPE (7/22/26).**
The 259.1-LF p6 foundation loop was the wrong geometry for the invoice comparison because
it inventories basement walls plus garage/frost/brick-ledge runs. The p4 LOWER FLOOR PLAN
isolates the basement-wall envelope. At OCR zoom 4, its own dimension chains solve
**12.500 px/ft with 0.3% spread**; `trace_enclosed_region()` returns **197.685 LF** at
2-ft, 8-ft, and 15-ft drawing-region pads (exactly clip-invariant), versus GV invoice
#1211's **198 LF** (-0.16%). The probe now measures p4 and is a hard PASS. The p6 259.1-LF
loop remains useful foundation inventory, but it must never be substituted for scoped
poured-wall LF. The golden command now also fails if any future `known_gap` remains.

**#48 — run_takeoff() LANDED: THE PHASE-5 LIBRARY CONTRACT (7/6/26).**
The one entrypoint every product consumes — `run_takeoff(plan_pdf, sheet_map,
area_specs=..., evidence_dir=...)` in jnj_takeoff.py. **CURRENT CONTRACT (7/17/26):**
the MODEL identifies WHERE; the LIBRARY calculates each area component with primary and
independent geometry traces, saves both overlays, reconciles them within 2%, and derives
`heated_sf` and `framing_sf` exactly once. Schedule values are comparison-only `checks`,
the legacy `underroof_sf` argument is ignored, and `estimate_from_takeoff()` re-certifies
the evidence before pricing. Other measured/count lines retain structured fields such as
trade, qty, unit, source, method, confidence, page, and note. The J&J
estimate writer, Level Ground Risk & Gap Report, CLI, and future web UI are thin
adapters over this contract — no rewrite needed to productize.
- **Validated on 3 houses first run:** WILSON all-high (heated 3,913.6 / framing 5,792.6
  / foundation 155.9 LF / basement 1,371.5 — golden-suite exact); HOLBROOK two-tracer
  reconcile FIRED correctly (clean 2,294 vs all-ink 3,175 disagree >8% -> reports 3,175
  at 'review' with both visible — cal #46's tracer rule is now CODE, not judgment);
  PETERSON ocr-schedule heal note propagated + roof 46.5 sq with solved ppf and
  overhang bounds in the line note.
- Scale policy in code: text-dims -> OCR-chains -> NEVER a nominal/guessed scale
  (not_measured instead). Roof policy in code: no pitch_calls = not_measured with the
  cal-#43 trap cited — the OCR pitch trap can't be silently automated away.
- Suite 17/17 + self-test ALL PASS after insert (no regression).
- NEXT for the contract: rooms/generic-room registry lines (Phase 5 remainder), rate-book
  application -> estimate adapter (unlocks roberts sell_total probe), model-portability
  run (golden + one run_takeoff under a cheap model, expect identical numbers).

**#49 — ESTIMATE-ASSEMBLY MATH IN CODE + ROBERTS GROUND-TRUTH DISCREPANCY (7/6/26).**
`assemble_estimate(lines)` landed in jnj_takeoff.py: per line builder_cost = qty x
unit_cost, markup by the line's own pct (defaults MATERIAL 15 / LABOR-SUB-EQUIP 7 /
FEE 15 / ALLOWANCE 8 / ASSEMBLY 0), amount, rollups by group + cost type. **Probe
roberts/estimate_amount_usd: re-priced all 589 lines of Jason's reference estimate from
raw inputs (qty, unit cost, markup%) -> $516,557 vs the file's stored $516,589 = -0.006%
PASS** (the $32 = the file's own one rounding exception; bulk line check: builder=qty x uc
1 violation, amount=builder+markup 0 violations across 589 lines). Pricing/markup/rollup
pipeline = regression-tested code; measurement probes prove the geometry; the halves
meet at run_takeoff (#48).
- ⛔ **GROUND-TRUTH DISCREPANCY (flagged, not papered over): the golden sell_total 591,341
  (cal #1 narrative) appears NOWHERE in the examples file, and the file's own Buildern
  footer says Total 649,312.39** — which also does NOT sum from its own items (footer:
  fixed 388,530.80 + allowances 107,407.24 + overheads 527.42 + markup 42,892.28 =
  539,357.74; items actually total 516,589). Buildern export footers can be STALE vs the
  sheet — never trust a summary block without re-summing the items. sell_total stays
  SKIP; Jason to call the true number (JARVIS todo_roberts_sell).
- Reference markup% census (old-model file): MATERIAL 15 (147 lines), LABOR 7 (41),
  SUB 7 (98, 6 at 15), ALLOWANCE 15 (190!) + 8 (19) — the ALLOWANCE-8 convention is
  NEWER than this file; reproduce a file's own pcts when grading against it, apply the
  current convention (8) on new estimates.

**#49 addendum — RESOLVED BY JASON (7/6/26): Roberts sell truth = the CONTRACT, $591,341.33.**
The original estimate was based on that signed contract number. The examples file is a
LATER template re-priced rebuild — its items (516,589) and stale Buildern footer (649,312)
are NOT the contract and never will be; grade assembly MATH against the file's own items
(done, -0.006%), grade SELL against the contract. sell_total_usd stays a documented
contract reference (no probe can derive a 2024 signed number from a re-priced file) —
the assert is retired to a comment, not left as a misleading SKIP.

**#50 — THE FULL CHAIN IS GREEN: PLAN PDF -> PRICED DOLLARS, ZERO HANDS (7/6/26).**
`estimate_from_takeoff(takeoff, rate_book)` landed: run_takeoff's measured JSON ->
RATE_BOOK (LOCKED calibrated rates ONLY, each entry cites its calibration point;
unmapped measured lines carried in `unpriced`, NEVER placeholder-priced) ->
assemble_estimate. Measurement source/confidence flows through to each priced line
(review-yellow survives into the estimate).
- **First chain grade: wilson/framing_labor_cost_usd = $37,652 vs ACTUAL vendor spend
  $38,210 = -1.5% PASS** (schedule p4 read autonomously -> 5,792.6 SF x locked $6.50,
  cal #33). This is the end-to-end proof: plans in, graded dollars out.
- RATE_BOOK v1 (deliberately small): framing labor $6.50/SF (cal #33, 3 actuals) +
  punch-out $1.75/heated SF (cal #41, 4 actuals). Growth rule: a rate enters ONLY when
  validated on actuals AND its quantity basis is exactly what run_takeoff emits.
- **Suite: 6 houses green, 19/19 PASS, exit 0.** Roberts sell RESOLVED by Jason =
  contract $591,341.33 (#49 addendum); assert retired to contract reference.
- ⛔ Build lesson: a lander that writes yaml must write REAL newlines — an escaped
  "\n" corrupted wilson/expected.yaml (suite silently dropped 2 asserts: count went
  18->17, only caught by WATCHING THE ASSERT COUNT). Rule: after any fixture edit,
  verify the graded-assert COUNT, not just exit 0.

**#51 — SECOND FULL-CHAIN GRADE: PETERSON ROOFING $ FROM THE PLAN (7/6/26).**
Chain #2 green: zero-text roof plan -> roof_zone_surface (46.5 sq measured, #44) ->
RATE_BOOK "roofing all-in" $227.70/sq (= $1.98/SF all-in x 1.15 shingle waste x 100,
derived from cal #13's Southern reconciliation) -> **$10,588 vs Southern Expert Roofing
ACTUAL $11,204 = -5.5% PASS (tol 8)**. The -5.5% is the KNOWN measurement bias (#44
bellcast flares), not pricing error — pricing from Jason's own raw surface reconciles
to 0.5%. Two chains now graded end-to-end against real vendor dollars: Wilson framing
labor -1.5%, Peterson roofing -5.5%. **Suite: 6 houses green, 20/20 PASS, exit 0.**
- ⛔ LANDER IDEMPOTENCY TRAP (2nd fixture-tooling lesson in 2 days): checking
  'is "roof_surface_sq" in file' matched the STRING inside run_takeoff and silently
  skipped adding the RATE_BOOK entry -> probe returned None -> SKIP. The assert COUNT
  (19 not 20, skips +1) caught it, same as #50's newline bug. Rule holds: after every
  fixture/probe change, verify graded-assert count went UP by exactly the additions.

**#52 — SELF-LEARNING LANDED, SPLIT BY SAFETY (Phase 4b start, 7/6/26).**
The system now learns identifications and NEVER auto-learns prices — the split that
protects the estimator mandate:
- **IDENTIFICATION auto-learns (safe):** `bank_knowledge` / `recall_knowledge` +
  persistent `reference/research_cache.json` (kinds: symbols / terms / room_types).
  `resolve_unknown` now WRITES BACK every plan-legend hit and READS the cache before
  anything else — so a symbol/term/room is researched ONCE, then reused for free (the
  cheap/local runtime stays fast, the engine gets smarter each job). Refuses to bank an
  empty answer or a sourceless fact. Seeded with 4 real conventions (HB=hose bib,
  "P."=pitch suffix, scullery + safe room room-types).
- **VALUATION is HUMAN-GATED (never auto):** `propose_rate` files a candidate WITH its
  evidence to `rate_candidates.json`; it NEVER touches RATE_BOOK. A rate is priced only
  after Jason/I confirm it against actuals and hand-add it — the calibration discipline
  as a queue, not prose. Self-test PROVES RATE_BOOK is unchanged (still 3 locked trades)
  after a propose_rate call. WHY: an ID error is low-stakes + self-correcting (next
  plan's legend catches it, and it's cited); a bad RATE compounds silently across every
  future bid — the estimator's cardinal sin.
- Self-test ALL PASS (recall, learn->persist->reload->recall, refusals, locked-book
  invariance, resolve-via-cache). Suite unchanged: 6 houses green, 20/20 PASS, exit 0.
- ⛔ HONEST GAP (Jason asked): the coded RATE_BOOK still prices only 3 trades; the other
  banked rates (garage-HVAC-by-SF, mudroom built-ins $300/LF, garage wrap, shiplap $5.50,
  encapsulation $3, foam roof $1.35/walls $1.00, etc.) live in the v2 TEMPLATE + this
  file, NOT yet in the chain. Closing that = the mechanical per-trade wiring (lock rate ->
  teach run_takeoff the basis -> RATE_BOOK line -> chain probe), separate from
  self-learning. shiplap $5.50 filed as the first rate candidate to demonstrate the gate.

**#53 — ALL 603 TEMPLATE LINES WIRED INTO THE CODED RATE BOOK (7/6/26, Jason's push).**
Jason (rightly): "wire all template trades into the rate book — I thought that was what
we'd been doing." Clarified the gap and CLOSED it: the rates always lived in the v2
template + this file (knowledge), but the CODE could only price 3 trades. Now:
- `reference/rate_book.json` = machine-readable extract of the ENTIRE canonical v2
  template: **603 lines, 504 priced**, each with unit_cost / cost_type / markup% /
  unit / group / description, source+date stamped.
- ⭐ **v2 TEMPLATE VERIFIED FULLY CURRENT** during extraction: every calibration-locked
  rate matches (framing $6.50, punch $1.75, shiplap $5.50, encapsulation $3, mudroom
  $300/LF, garage wrap $200/door, foam roof $1.35 / walls $1.00) — ZERO stale values,
  zero overrides needed. The 7/5 template rebuild really did carry everything.
- Engine: `load_rate_book()` + `find_rate(query)` (substring search — stop hand-reading
  the xlsx) + `price_lines({line name: qty})` -> assemble_estimate. ANY set of template
  lines is now priceable in code from measured or hand-taken-off quantities; unknown or
  ambiguous names RAISE (never silently dropped, cross-group collisions need
  'Group/Name'). Self-test: framing-labor line reproduces $37,652 exactly; suite still
  6 houses green, 20/20, exit 0.
- ARCHITECTURE now: TWO books, one discipline. rate_book.json = the full priced catalog
  (what everything costs). RATE_BOOK (in-code map) = which measured run_takeoff trades
  auto-price without a human (3 today; grows only with chain-graded validation). Rate
  changes flow rate_candidates.json -> Jason confirms -> template + re-extract.

---

# Data point #54 — DAVIS (Lawrence Davis; PR-109; 12-sheet J&J set) — ⭐ GRADED COLD vs J&J's OWN (Skip's) estimate + measurements
Single-story **monolithic slab**, 3,551 heated / 898 garage / 588 covered porch = **5,037 under-roof**. Public water + septic, FULL spray foam, stick-framed hip roof (6:12 + tiny 2:12 entry), Hardie lap + stacked-stone wainscot + cedar entry posts, electric-linear FP, standard steel garage doors (16'+9'), garage NOT conditioned. Built cold from the plans; THEN graded against J&J's own Buildern estimate (Skip's) + a 16-page measurements export. ⚠️ **Graded vs an ESTIMATE, not actuals → these are METHOD fixes, not new locked rates.**

## The tie-out (how J&J's export reads)
J&J total **$827,963** = Builder Cost $404,304 + Allowances $217,684 (= direct **$621,988**) + per-line Markup $67,982 + Overheads 20% $137,994. My cold direct **$546,643** = **~12% under** at the direct level. **BUT ~90% of the gap was SCOPE I excluded per Jason** (site work TBD — no site plan; garage HVAC — not conditioned; generator/landscaping/2nd-appliance/propane Skip carried), NOT measuring error. On identical scope we're within ~1%.

## ⛔ READING A J&J BUILDERN EXPORT (new QA rule — cost me a wrong "I'm way low" read)
The raw leaf-"Amount" sum DOUBLE-COUNTS. Exclude **ASSEMBLY parent rows** (children carry cost) AND **"don't calculate"** lines (switched off in Buildern but still export an Amount). Davis had **$23,041 of don't-calculate**: `Footer Labor` $10,860 + `Cap Block` + `Ladder Mesh` (live stray children under a ZEROED "Crawlspace: Block walls" assembly — on a SLAB house) + garage-HVAC set. Excluding exactly those reconciled my reparse ($645,029) to J&J's stated Builder+Allowances **$621,988 to the dollar**. Grade at the DIRECT level; reconcile to `Builder Cost + Allowances`, never a raw sum.

## ⭐ FOUR genuine method misses → FIXED IN ENGINE (jnj_takeoff.py, with self-tests; golden suite still 6/6 green)
1. **CLADDING/VENEER — `cladding_by_elevation()` forcing function.** My stone = 450 SF (measured front + "partial sides," skipped faces). J&J's estimate OVER-wrapped to 1,127 SF (≈ full-perimeter × 3, counting a REAR that is all siding). Truth ~**587 SF** (band ~3.5' × front 65 + left 30 + right 40 LF + 2 piers + chimney; rear = none). The function REQUIRES all four cardinal faces (`[]` = "none here"), RAISES on an omitted face, and flags a material `<60%` (skipped) or `>140%` (over-wrapped) of perimeter×band. **A wainscot rarely wraps all 4 sides — never assume.**
2. **`trim_labor()` = (heated+garage) SF × $2** — NOT base-LF. I priced ~$2,350; J&J's SF basis = **$8,898** (−$6.5k).
3. **RETIRED 2026-07-20 — the old `cabinet_boxes()` installation-pricing lesson is no longer active.** Jason's controlling rule is $150/LF material and $75/LF installation, with tall-cabinet LF counted twice for both. Use `cabinet_pricing(runs)`; box counts are schedule-reconciliation evidence only.
4. **`roofing_turnkey()` — ESTIMATE LINE bills template TURNKEY $2.25/SF** of waste-loaded surface. My decoded `roofing_estimate()` $2.07 ran ~9% light; keep it only as the itemized cross-check.
Minor: corner boards (I under-count outside corners on L-shaped/jogged plans — went 12→19), interior window/door casing (600→~1,200 LF both-sides).

## Other confirmations
- **MONO SLAB confirmed right:** thickened edge = extra concrete + rebar, NO separate footer LABOR. A live "Footer Labor" LF line on a slab = the crawl-assembly don't-calculate artifact, not scope. My foundation matched within a few CY.
- **HELD dead-on (cold):** framing SF 5,037 EXACT, electrical SF 4,449 EXACT, duct 3,551 EXACT, paint basis EXACT, **drywall room-by-room 18,150 vs J&J 19,195 (within 5%)**, lap siding 3,578 vs 3,343, doors+windows total within $197, plumbing/insulation/LVP within a few %.
- **⭐ Jason PRICES BY $/UNDER-ROOF-SF, not heated** — lead with it. Davis final: subtotal $627,252 ($125/UR-SF) → +20% O&P → +5% contingency = **sell $790,338 ($157/UR-SF)** vs J&J's $827,963 ($164/UR-SF); the ~$7/SF residual = site/landscaping still TBD (no site plan). My framing at Jason's $10 is ~$10k ABOVE Skip's $8, so the residual is scope, not softness.
- **Meta:** the near-total match hid the usual offsetting errors — I ran LIGHT on finishes (trim labor, cabinet install) + masonry (stone) and HIGH on framing/tile/glass. Same chronic pattern as #9/#39: pad finishes + cladding, and go face-by-face.

# Data point #55 — SYSTEM AUDIT: four latent engine holes the golden suite never caught (7/6/26)
Full adversarial read of jnj_takeoff.py (2,900+ lines) + rate_book.json + Level Ground report. Four
CODE bugs (not rates) found, PROVEN empirically, and FIXED with self-test asserts; golden suite
unchanged (6/6 green, 20/20, exit 0). Every one was LATENT — each lives on a path the golden probes
don't exercise, so all-green never meant all-correct.
1. **run_takeoff DOUBLE-COUNTED framing SF (2.00x ≈ $33k phantom labor at $6.50/SF).** read_sqft_schedule
   returns a "TOTAL UNDER ROOF" row tagged 'framed' ("under roof" is a _FRAME_FRAMED keyword);
   run_takeoff summed that TOTAL alongside its components (heated+garage+porches) → 10,074 vs true 5,037
   on a Davis-sized schedule. The OCR sibling read_sqft_schedule_ocr already excluded TOTAL|UNDER ROOF;
   the text path + run_takeoff didn't. Davis dodged it only because that estimate was hand-built, not
   run through the autonomous chain — the next auto-run with a total row would silently 2x framing.
2. **run_takeoff MIS-FRAMED 'uncovered' (slab) patios.** Its rule `"covered" in label` also matches
   "un**covered**" (substring) → a slab-on-grade patio (flatwork) added into framed SF. The golden
   helper guarded this; run_takeoff didn't — engine↔test had DRIFTED, and that drift HID both #1 and #2.
   FIX: one canonical `framed_under_roof_sf(rows)` (framed + covered-back, minus totals, guards
   'uncovered', total-fallback if no components); run_takeoff AND the golden harness now both call it —
   they can never drift again.
3. **_page_scale silently REFUSED a 'good' scale.** It accepted confidence in ('high','review') but NOT
   'good' — the verdict for a scale that SNAPS to a standard architectural scale with 6-14 votes
   (strictly better than 'review'). Effect: run_takeoff refused to measure foundation/slab on a perfectly
   good sheet, or fell to noisier OCR. No probe ever hit _page_scale, so it was wholly untested. FIX: accept 'good'.
4. **price_lines could silently price a line at $0.** On a duplicated (group,name) — a real Buildern
   ASSEMBLY container ($0) + its priced leaf under the same name — the qualified lookup was last-wins and
   could return the $0 container. FIX: resolver filters ASSEMBLY, collapses identical leaves, and RAISES
   on a true rate conflict — never a silent $0.
Doc-only: cladding_by_elevation docstring now states it's for a VENEER/WAINSCOT band (pass band_ht = wall
height for a full-height FIELD material, else the >140% over-wrap flag false-fires on a full wall).
**ESCALATED to Jason (rate-book DATA + methodology — NOT auto-fixed, per the human-gated rule):**
(a) 23 zero-cost non-ASSEMBLY rate-book lines — mostly INPUTS, but a few scope lines that would price $0
if selected (Windows-Curtain-wall, Electrical-Quote, Siding-Quote, Stucco, Bath specialty lighting, Fence);
(b) 3 EXACT-duplicate tile leaves in rate_book.json (Flooring Tile / sundries / Labor each appear twice —
a double-import; dedupe at source); (c) **Level Ground Risk & Gap Report headline numbers don't reconcile**
— the sample flags $74–118k of exposure but its "independent range" is only $31–77k over the bid (range top
should be ~$706k, shown $664k), and per-finding "realistic" $ aren't derived from the calibrated rate book
(countertop $15–22k for 142 SF vs J&J's OWN ~$6k). Recommend a reconciliation forcing function + wire the
report's realistic ranges to the rate book before it ships to homeowners (a builder shown the report will
impeach numbers that contradict the builder's own pricing).
**RESOLVED 7/6/26 (Jason's direction):** (a)+(b) rate-book dups + zero-cost lines confirmed INTENTIONAL —
Jason prices BY ROOM (dups expected) and the zeros are estimate-template PLACEHOLDERS that price only if
measured — no change (price_lines hardening stands, handles the dups). (c) **Level Ground report FIXED in
BOTH copies** (`lg_report_template.html` + `site/sample-report.html`): the "independent range" is now DERIVED
as bid + the documented gaps, so the three headline numbers reconcile BY CONSTRUCTION (range − bid ≡ exposure,
every dollar traces to a finding); a **reconciliation forcing function** warns + shows a "draft — doesn't
reconcile" flag if a hand-set range ever contradicts the findings; and every finding now carries a traceable
**`basis`** (measured qty × stated rate / regional comps). The indefensible countertop $15–22k → $9–14k
(≈142 SF × $65–100/SF installed). Verified: JSON parses, renders $587,400 / $656k–$698k / $68k–$110k, guard
clean, no console errors. REMAINING (future build, no live pipeline yet): auto-populate the report's findings
+ ranges from `run_takeoff()` + the rate book so real reports are engine-derived, not hand-authored.

# Data point #56 — LEVEL GROUND PHASE 1: report_from_takeoff() PRE-BID pipeline LANDED (7/6/26)
Wired the Risk & Gap Report to `run_takeoff()`. Jason's directions locked: **agent-run delivery first**,
**reuse the decoded rate book + a GC-markup band** for pricing (Phase 2), **honesty contract stays**.
- **`report_from_takeoff(takeoff, home, region, ...)`** (jnj_takeoff.py): a run_takeoff() result +
  homeowner intake → the exact report JSON the LG HTML renders. **PRE-BID (plans only, no bid):** maps
  measured lines → `quantities[]` (source+confidence flow through as the "measured off your drawings"
  chip), emits the **STANDARD-SCOPE CHECKLIST** (`PRE_BID_SCOPE_CHECKLIST`, 8 items = the chronic
  zero-traps: site/driveway/final-grade, gutters, low-voltage/security, defined allowances, landscaping,
  insulation-grade, no-vague-lumps, change-order pricing) as dollarless `findings` + the meeting
  `questions` + standard `unknowns`; `bid_total`/`our_range` = None so the report hides the verdict
  strip. Anything run_takeoff could NOT measure → `unknowns` (honest, never hidden).
- **Report HTML is now report-type-aware** (guarded — bid_gap path byte-identical): pre_bid hides the
  bid/range/exposure strip, relabels "What we found" → "Scope to confirm your bid covers", and drops the
  "in the bid" line on dollarless findings.
- **Both site samples now GENERATED FROM THE ONE TEMPLATE** (`Level Ground/gen_reports.py`) — killed the
  two-copy drift I flagged. `site/sample-report.html` = bid_gap; `site/sample-prebid-report.html` = the
  pre_bid demo.
- **VERIFIED** (preview + self-test + golden): pre-bid renders "Pre-Bid Report" / strip hidden / 5 measured
  quantities / 8 checklist findings / 8 questions / 4 unknowns; bid_gap still $587,400 / $656k–$698k /
  $68k–$110k reconciled with ZERO regression; no console errors; self-test ALL PASS (new report_from_takeoff
  assert); golden 6/6, 20/20, exit 0.
- **NEXT:** Phase 2 = market pricing (decoded rate × qty × GC-markup band) → cost ranges on the quantities;
  Phase 3 = builder-bid ingestion → findings by comparison (fills the already-reconciled headline).
  run_takeoff COVERAGE to extend for richer reports: exterior wall SF, window/door counts, countertop SF,
  slab perimeter. ⛔ Not one-click: run_takeoff still needs the VLM "which sheet + verify pitch" pass
  (agent-run absorbs it).

# Data point #57 — LEVEL GROUND PHASE 2: market pricing -> expected build-cost range (7/6/26)
Put a defensible "what a build like this costs in your market" range on the pre-bid report.
- **`MARKET_RATE_BOOK` + `price_report(quantities, home, market_book)`** (jnj_takeoff.py): range =
  under-roof SF (heated fallback) × the finish-level **SELL $/UR-SF** band. Bands are from J&J's own
  completed-job actuals, Middle GA (reuse the calibration, don't invent): **mid $115–155 / custom
  $140–195 / high $195–290** (each cites its jobs — Villanueva/Lyndall/Hernandez, Davis/Anthony/Roberts,
  Guarino/Darwish). ⚠️ **VALUATION → `_confirmed: False`, PROVISIONAL until Jason confirms vs actuals**
  (cardinal-sin rule: never silently lock a rate). `price_report` never fabricates an area (returns None
  if no area quantity is present).
- `report_from_takeoff` gains **`market_book=`**: when given, sets `meta.our_range` = expected build
  cost, `meta.cost_basis` (finish · market · $/sf), `meta.pricing_confirmed`; the verdict note explains
  it's a provisional regional **sanity check, not a quote**.
- Report HTML verdict strip refactored to **THREE modes** (guarded, bid_gap byte-identical): (1) bid_gap
  = Builder's bid | derived range | exposure; (2) pre-bid + pricing = **"Your home | Estimated build cost
  | Market basis"** hero (red exposure styling dropped — it's a basis, not a warning); (3) pre-bid no-
  pricing = strip hidden.
- **VERIFIED:** pre-bid sample (custom, 3,214 htd / 4,400 UR) renders **"$616k–$858k · custom finish ·
  Middle Georgia · $140–195/sf under-roof"**; bid_gap still $587,400 / $656k–$698k / $68k–$110k with NO
  regression; no console errors; self-test ALL PASS (new price_report assert); golden 6/6, 20/20, exit 0.
- ⛔ **WAITING ON JASON:** confirm/tune the $/SF market bands vs actuals — the one input that most moves
  the headline (provisional until he signs off). **NEXT: Phase 3 = builder-bid ingestion → auto findings
  that fill the already-reconciled bid_gap headline.**

# Data point #58 — LEVEL GROUND PHASE 3: builder-bid ingestion + auto findings (7/6/26)
Closed the loop: **plans + a builder's bid → the reconciled bid_gap report, ENGINE-GENERATED** (no more
hand-authoring). Split by difficulty as scoped: ANALYSIS (structured bid → findings) built + tested;
INGESTION of arbitrary PDF/photo is the v2 front-end.
- **Bid contract:** `{total, lines:[{desc, amount, is_lump?}]}`. `ingest_bid(lines, total)` normalizes;
  `ingest_bid_xlsx(path)` reads the common Excel bid (flags a big 1–2-word line as a lump).
- **Checklist items gained detector metadata** (`detect` dollar|grade|process, `scope_keys`, `expected`
  band).
- **`findings_from_bid(bid, home, checklist)`** generates the report findings:
    DOLLAR item → finding if the bid line is ABSENT or under expected_low (missing / low);
    GRADE item  → mispriced when the plan wants an upgrade (home flag, e.g. foam) the bid under-carries;
    VAGUE LUMP  → any is_lump bid line → unverifiable, flagged, NEVER priced (0 exposure).
  Per-scope bands PROVISIONAL / regional (same human-gated caveat as the $/SF bands).
- **`report_from_takeoff(..., bid=)`** → report_type auto `bid_gap`, bid_total set, findings from the
  bid; the HTML derives range = bid + exposure (reconciles by construction) and cross-checks it against
  the Phase-2 market range — the guard is now **OVERLAP-based** (flags only if the two ranges are >12%
  disjoint, so the broad market range never false-flags).
- **Both site samples now ENGINE-GENERATED** from the template + adapter (`gen_reports.py`): bid_gap
  from a structured bid, pre_bid from plans only. Killed the last hand-authoring.
- **VERIFIED:** bid_gap sample renders **$587,400 / $657k–$704k / $69k–$116k**, 6 auto-findings
  (Site / Gutters / Home-tech / Landscaping / Insulation-mispriced / Electrical-lump), reconciles, no
  draft flag, no console errors; pre-bid still $616k–$858k; self-test ALL PASS (new findings_from_bid
  assert); golden 6/6, 20/20, exit 0.
- **NEXT (v2):** arbitrary-bid INGESTION (PDF / photo / messy xlsx → the structured contract) is the
  fuzzy front-end; extend run_takeoff coverage (wall SF, window/door counts, countertop SF) so more
  scopes are measurable; add a low-allowance detector for measured scopes (countertop qty × rate vs bid).
- ⛔ **STILL WAITING ON JASON:** confirm the $/SF market bands AND the per-scope expected bands (both
  provisional; JARVIS `todo_lg_market_bands`).

**#58 addendum — Jason CONFIRMED the $/SF bands + MARKET_RATE_BOOK is now MARKET-AWARE (7/7/26).**
Jason locked the SELL $/under-roof-SF bands **for HIS market**: Middle GA **mid $140–160 / custom
$160–200 / high $200–300**. ⭐ Key: he flagged he only knows his own market ("I don't know all US
markets"), so MARKET_RATE_BOOK is restructured **markets-keyed** — `middle_ga` carries the confirmed
bands (`_confirmed: True`); `_resolve_market()` matches a report's market by name/alias, and an
UNCALIBRATED market returns **`market_calibrated: False`** (report flags "no calibrated pricing for
your market -- rough proxy, confirm locally") so an unknown US market is NEVER silently priced as if
it were Middle GA. Extend to other markets via a regional cost index off this base, or local
confirmation (v2). Sample pre-bid now $704k–$880k (custom, 4,400 UR); self-test ALL PASS (California →
uncalibrated flag), golden 6/6. **Per-scope gap bands (site/gutters/low-voltage/landscaping/insulation)
remain PROVISIONAL** — the only pricing left on the JARVIS list.

# Data point #59 — LEVEL GROUND: US MARKET COST INDEX researched + installed (7/7/26)
So EVERY market (not just Middle GA) gets an expected-cost range. Method = the HYBRID Jason picked:
anchor on his GA actuals × a published regional CONSTRUCTION cost index, validated against researched
anchor markets. Metro/MSA granularity, state fallback.
- **Research** (10-agent workflow `us-market-cost-index`): 51 states + DC + 35 major metros, national =
  1.00, from RSMeans 2021 CCI/Gordian + calcsummit + roofobservations + Mortenson; medium confidence.
  **GA anchor = 0.87.** Installed in `MARKET_RATE_BOOK["index"]` (state_index dict + metro_overrides list
  + ga_index + demand_note).
- **THREE TIERS** in `price_report` (+ `meta.pricing_tier`): `calibrated` (Middle GA only — actuals,
  delivered, confirmed) / `regional_estimate` (any other market: band = GA band × market_index/ga_index;
  metro override when city+state match, else state index; CONSTRUCTION-cost basis, report flags "regional
  estimate" + "confirm locally") / `uncalibrated` (can't place → GA proxy, flagged). ⛔ Fixed a real bug:
  `_resolve_market` now requires STATE match for a calibrated hit — the bare "ga" alias would have matched
  Atlanta / Las Ve**ga**s, and the "Monroe" county alias would have matched Monroe **LA**. Atlanta now →
  indexed 1.034, not GA-calibrated.
- ⛔⛔ **KEY FINDING (anchor validation) — the index is a HARD-COST FLOOR.** Cost-similar markets
  (GA / Birmingham / Columbus) align once the heated-vs-under-roof basis is accounted; but HIGH-DEMAND
  metros (Austin / Denver / Seattle / SF Bay) run WELL ABOVE it (up to ~2×) on land + soft costs + builder
  margin the index can't see — and **demand does NOT track the construction index** (Austin's construction
  cost is BELOW national yet it's a hot market). So we do NOT fabricate a demand curve; indexed ranges are
  honest construction-cost estimates + a "high-demand runs higher, confirm locally" flag. A market earns
  DELIVERED-price accuracy only by getting local ACTUALS (the path GA took). Confirmed to Jason 7/7.
- Verified: self-test ALL PASS (3-tier + Seattle ×1.23 + uncalibrated), golden 6/6; spot-checked 15 markets
  (Atlanta indexed not calibrated, Savannah → GA state, Monroe LA cross-state handled, SF $1.05–1.32M
  construction). Samples unchanged (GA calibrated).
- OPEN: per-scope gap bands still provisional (JARVIS); improve hot markets with local actuals; v2
  arbitrary-bid ingestion.

---

# Data point #60 — ⭐⭐⭐⭐⭐ VENDOR-DOCUMENT RATE EXTRACTION: the siding/roofing "miss" was NEVER a rate problem (2026-07-27, Jason confirmed)

Built a PDF line-item extractor (`estimator_accuracy/extract_vendor_quotes.py`) and ran it over 344 vendor
documents on this machine. **635 rows extracted, 356 passed math validation** (qty x unit price = total),
across 50 documents and 26 named scopes. Vendor "Square(Sq)" is converted explicitly: **1 square = 100 SF**.

## ⛔ THE FINDING — my rates were right; my LINE COUNT was wrong
**8 of 12 comparable rates match the J&J template almost exactly:**
frieze $4.50/LF (23 obs, 15 docs) · soffit+fascia $11.00/LF (20 obs, 13 docs) · water-table flashing $3.50/LF
(11 obs) · porch beam cedar 4/4 $23.00/LF (9 obs) · band board $7.50/LF · porch ceiling T&G $5.40/SF (15 obs) ·
B&B $4.30/SF (15 obs, **zero variance**) · porch beam Hardie $11.00/LF.

**The siding misses (−34% Villanueva, −49% Sailview, −51% Anthony) came from PRICING 3-4 LINES AGAINST A
17-27 LINE REALITY.** A Southern Siding & Gutters exterior package carries 17-27 itemized lines. The template
had no line at all for: rake, cantilever soffit, trimmed openings, window wrap sets, door wrap sets, Hardie 5/4
trim, Hardie shake, splash blocks — nor for the roofing detail layer (drip edge, hip & ridge, brick flashing).

## ⛔ STANDING RULE (Jason, verbatim): "no shortcuts. everything gets measured"
**Siding and roofing are quoted TURNKEY — material AND labor in the unit rate.** The old "lap ~$7-8/SF
installed" note was a shortcut I invented to avoid measuring elevations; it tripled the field rate to hide the
missing trim lines. **It is dead.** Use the vendor line-item format below and measure every run off the
elevations. Do NOT inflate a field rate to cover scope you did not measure.

## MEASURED TURNKEY RATES (mat+labor, Southern Siding & Gutters / Southern Expert Roofing, 2025-10 to 2026-07)
| Scope | Rate | Obs | Docs |
|---|---|---|---|
| Siding — Hardie lap (horizontal) | **$2.50/SF** (range 2.40-3.50) | 13 | 13 |
| Siding — Hardie board & batten | **$4.30/SF** (zero variance) | 15 | 15 |
| Siding — Hardie shake | $8.20/SF | 2 | 2 |
| Soffit + fascia (12" vented w/ 8" fascia) | **$11.00/LF** | 20 | 13 |
| Cantilever soffit (16") | $9.00/LF | 8 | 8 |
| Porch ceiling — wood 1x6 T&G | $5.40/SF | 15 | 15 |
| Porch beam wrap — cedar 4/4 | $23.00/LF | 9 | 9 |
| Porch beam wrap — Hardie | $11.00/LF | 6 | 6 |
| Frieze — Hardie | $4.50/LF | 23 | 15 |
| Rake — Hardie | $5.00/LF | 4 | 4 |
| Band board — Hardie | $7.50/LF | 4 | 4 |
| Trim — Hardie 5/4 stock | $4.50/LF (3.50-6.00 by width) | 34 | 11 |
| Flashing — water table | $3.50/LF | 11 | 11 |
| Trimmed opening — Hardie | $65.00 ea | 7 | 7 |
| Column wrap — cedar | $350 ea (270-480 by size) | 12 | 11 |
| Gable bracket — cedar | $120 ea (105-150) | 8 | 4 |
| Garage wrap | $190 ea | 9 | 7 |
| Window wrap set | $30 ea | 5 | 5 |
| Door wrap set | $60 ea | 5 | 5 |
| House wrap | **$0.35/SF** | 10 | 10 |
| Shingles — architectural (GAF HDZ / CT Landmark) | **$1.75/SF** ($174-184/square) | 12 | 12 |
| Drip edge — 1.5" aluminum | $1.85/LF (zero variance) | 12 | 12 |
| Hip & ridge cap | $4.25/LF | 5 | 5 |
| Brick flashing / trim coil | $12.00/LF | 2 | 2 |
| Gutters — 6" K-style | **$6.00/LF** (Jason approved) | 4 | 4 |
| Splash blocks | $7.00 ea | 4 | 4 |

## Template rate corrections found (4 real deltas)
- **Gable bracket: template $250 vs measured $120 — 108% HIGH.**
- **Siding Hardie lap: template $3.30 vs measured $2.50 — 32% HIGH.**
- **Gutters: template $7.00 vs measured $5.50-6.00 — 27% HIGH** (corroborated 3 ways: QBO 2 projects,
  4 vendor docs, RL Gutters quote). Jason set $6.00; downspouts also $6.00.
- **Column wrap cedar: template $270 vs measured $350 — 23% LOW.**

## Method note — the extractor
`extract_vendor_quotes.py` validates every row with qty x unit price = total before accepting it (98 rows
failed and were REJECTED, not guessed). Four documents extracted nothing (Addison gutter quotes from both RL
and Pitch Perfect, Pitch Perfect EST0736, Lankford waterproofing) — likely scanned images needing OCR.

## Cross-check that QBO is a weak unit-rate source
955 QBO records produced only **3 usable rates**; one siding PDF produced 17. QBO bills are mostly lump-sum
(`quantity: 1`), and four of the seven items that cleared the policy floor were commingling units
($0.01 to $15.00 inside one "Electrical" item). **Vendor documents are the primary unit-rate channel; QBO is
for category variance, not unit rates.** Decisions recorded in `private/v3_qbo_candidate_decisions.json`.

## Other Jason decisions this session
- **Drywall stays $1.44/SF** (Burns invoice); QBO's $1.28 from RLM noted but rejected.
- **Excavation is NOT a per-SF trade — it behaves as a per-DAY rate and must be set per job.** Never derive an
  excavation unit rate from history. (Corroborates the existing scatter: Martin final grade $1,250 vs
  Villanueva $11,980 vs Sailview wooded $18,382.)
- ⭐ **ELECTRICAL = $6.50/SF of UNDER-ROOF AREA MINUS COVERED PORCHES (Jason, standing rule).** Line E205.
  Counts **basement (finished OR unfinished) + every floor + garage**; excludes covered porches (M009) and
  uncovered porches/patios (M010). Jason: "a house on an unfinished basement with a garage would count all of
  that area at $6.50." The certified E205 formula `CEILING(M004+M005+M006+M007+M008)` already sums exactly
  those five fields — verified 2026-07-27, no formula change needed. Registered as an **approved** rate (not a
  quote) so it cannot expire and silently fall back to the old $7.00 template rate. Jason's number and an
  independent Buildern quote landed on $6.50 from different directions.
  *Worked example: unfinished basement 1,200 + main 1,800 + garage 600 = 3,600 SF billable (400 SF covered
  porch excluded) x $6.50 = $23,400.*
- Stucco $15.00/SF, vinyl lap $2.30/SF, vinyl vertical $3.50/SF, wood floor material $6.00/SF + labor $4.00/SF.

---

# Data point #61 — ⛔ SKIP'S TAKEOFF IS NOT INFALLIBLE GROUND TRUTH (Jason, 2026-07-27)

Two corrections from Jason while grading counts against the Buildern measurement sheets. Both
matter more than the numbers themselves, because they change what "ground truth" means here.

## ⭐ CAN LIGHTS — Jason's method ruling (RESOLVED 2026-07-27)
**Burns has exactly 37 recessed can lights — the 37 `R4` tags on the electrical sheet (p8). The
ENGINE was right and Skip's 32 was wrong.** Jason: *"the rest of them are different type light
fixtures that skip counted as can lights because he is lazy, and this is exactly what I am trying
to avoid. The human laziness trap."*
**STANDING RULE: a can light is a RECESSED CAN, identified by its `R4`/`R6` tag. Vanity lights and
single room/ceiling fixtures are their own lines and must NEVER be folded into the can-light
count.** Rolling every ceiling fixture into "can lights" is the exact shortcut this system exists
to eliminate — it prices the wrong fixture at the wrong rate on both lines.

## ⭐ WINDOWS — mulled units (Jason, same day)
**A mulled unit is separate windows: a double mull = 2, a triple = 3.** Burns' single unlabelled
`5450MU` is 2 windows, so Burns is **14**, not the 13 on Skip's sheet. Roberts resolves to exactly
23 (4x `6062MU` DOUBLE = 8, 2x `9062MU` TRIPLE = 6, 1x unlabelled `6044MU` = 2, + 7 singles).

## ⛔ THE STANDING LESSON
Skip's Buildern measurement sheets are the best geometry reference available and are worth grading
against — but they contain **method errors and miscounts**. Two of the first three counts checked
disagreed with him and **Jason ruled for the engine both times**. Never auto-correct the engine
toward Skip's number. A disagreement is a QUESTION FOR JASON, not proof the engine is wrong.

## ✅ FIXTURE PLAN VERIFIED — earlier drift concern RETRACTED
I flagged the golden `burns/plan.pdf` as a stale revision after Jason mentioned lights "on page 10".
**Wrong.** Jason sent the plan and it is BYTE-IDENTICAL to the registered fixture — sha256
`a04414655c5dbda29e52df82...`, 9 pages, 37 `R4` on p8. The fixture is correct and every Burns
assertion measured off it stands. Verify a hash before calling a fixture stale.

## ⭐ GUTTERS / LINEAR TRADES — VENDOR QUOTE IS THE TRUTH (Jason, 2026-07-27)
Where a sub's itemized quote and Skip's takeoff disagree on a linear quantity, **the vendor quote
wins.** It is what was actually measured, bought, and installed.

Measured disagreement that forced the ruling:
| Line | Skip's takeoff | Vendor quote | Skip is |
|---|---|---|---|
| Roberts gutters + downspouts | 252.18 + 189.0 = 441.2 LF | **360 LF** (Southern) | **+22%** |
| Roberts soffit + fascia | 320.56 LF | **336 LF** (222 + 114) | −5% |
| Burns soffit + fascia | 326.94 LF | **280 LF** (116 + 164) | **+17%** |

Note the vendor prices gutters and downspouts as ONE combined LF line at $5.50 — Skip splits them
into two measurements. When grading, compare Skip's gutters + downspouts against the single vendor
line, not against gutters alone.

Vendor gutter runs on file (all Southern, all $5.50/LF): Roberts 360, Sailview 453, 6000 Hwy 81 810.

**Grading order for linear trades from here: vendor quote > engine measurement > Skip's takeoff.**

---

# Data point #62 — ⭐⭐⭐⭐⭐ MEASUREMENT PROBES: the engine now GRADES ITSELF (2026-07-27)

The golden suite went from **10 measurement assertions to 15** in one session — the first new ones in
months, and the first ever graded against Skip's own Buildern takeoffs and J&J's vendor quotes rather
than against calibration prose.

| Probe | Engine | Truth | Delta |
|---|---|---|---|
| burns window_count | 14 | 14 (Jason) | 0.0% |
| roberts window_count | 23 | 23 (Skip) | 0.0% |
| burns recessed_can_count | 37 | 37 (Jason) | 0.0% |
| roberts fascia_lf | 327.4 | 336 (Southern) | −2.6% ⚠ see caveat |
| roberts gutter_main_lf | 182.8 | 178.47 (Jason) | +2.4% |

## ⭐ NEW ENGINE CAPABILITIES (all drafter-independent by design)
- **`window_count`** — counts manufacturer size tags on the FLOOR PLAN. ⛔ NEVER the elevations:
  they draw each opening on more than one view (burns 26 tags for 13 real windows, ~2x).
  Mulled units expand per Jason: `6062MU` labelled DOUBLE = 2, `9062MU` TRIPLE = 3, an unlabelled
  `MU` defaults to 2 (a mull is at least two units).
- **`interior_door_count`** — built but NOT wired: a `2868` tag gives size, never hollow vs solid vs
  pocket, which is exactly the split J&J's line items need. Burns matching 17 was coincidence.
- **`recessed_can_count`** — `R4`/`R6` tags only.
- **`roof_outline_segments`** — isolates roof linework by **PITCH-CALLOUT ENCLOSURE**. ⛔ NOT colour:
  colour is a drafter's choice and on roberts the "roof colour" resolves to the RED REDLINE layer
  (242 LF of roof, 17,706 LF dumped in "other"). NOT largest-component either — on burns the true
  roof is the RUNNER-UP (623.8) behind a 1,041 LF blob. Pitch callouts are a construction
  requirement, so every roof plan has them.
- **`slope_arrows`** — reads the slope arrows Jason actually reads. Shaft + two barbs converging at
  ONE end = the head, pointing downslope. **Shaft length varies by drafter (roberts 33pt, burns
  96pt)** so discrimination is by the barbs. A DIMENSION line has heads at BOTH ends — reject it.
- **`classify_roof_lines`** — splits eave / rake / ridge / hip-valley / shed-transition.
- **`render_roof_line_overlay`** — draws the classification back on the sheet. **This is what broke
  the logjam.** Three rounds of theorising achieved nothing; one overlay + Jason's markup fixed four
  classifications in one pass.

## ⭐ GEOMETRY RULES LEARNED (each one cost a wrong answer first)
1. **Roof linework is DOUBLE-DRAWN.** Burns: 40 strokes for 27 real lines. Dedupe FIRST or every
   length is ~1.5x. The pre-existing `roof_line_ft = 624` assertion measures doubled linework.
2. **Ray-cast parity cannot decide inside/outside here.** Parity needs a CLOSED polygon; roof
   linework is a graph full of interior ridges, so every interior line flips it. Use an EXTERIOR
   FLOOD FILL. (Validated: 228.9 LF boundary on burns, matching a hand trace to the decimal.)
3. **A roof plan is a PROJECTION.** Eaves and ridges are level so drawn length is true length;
   RAKES and HIPS run up the slope and must be multiplied by the pitch factor. Missing this read
   both houses ~18-19% short.
4. **A ridge has the same roof falling AWAY on both sides.** A shallow shed running into a steeper
   roof is a TRANSITION — regular shingles, **no ridge cap**. Roberts was counting 48 LF of shed
   line as ridge and would have ordered cap at $4.25/LF for it.
5. **Use the arrow on the side the ROOF is on.** Taking whichever side was populated made mirror-
   image edges disagree — burns' north wing read eave on the left and rake on the right because the
   right one reached across and grabbed the MAIN body's arrow.
6. **An interior run with roof on one side only is an EDGE, not a ridge** (a step-down). If its
   arrow runs ALONGSIDE it, it is a RAKE. Requiring parallel is what protects genuine ridges.
7. ⛔ **Plane-binding arrows to their own roof plane REGRESSED it** (fascia −2.6% → −6.5%). Tried
   and reverted. Nearest-on-the-roof-side stands until something demonstrably beats it.

## ⛔ THE PATTERN THAT KEEPS BITING: OFFSETTING ERRORS
Three times in one session a total looked good because two errors cancelled:
- roberts fascia "+6.8%" — half a real fix, half a newly-broken ridge
- the "consistent −8% on both houses" — a short perimeter plus an oversized rake
- **the wired fascia probe itself passes partly by cancellation.** Jason's gutter (eave 252.18 raw)
  and Southern's fascia (336 installed) jointly imply a raw boundary of **314.7 LF**; the engine
  isolates **290.6** — the perimeter is **~24 LF SHORT** — but lands near 336 because too much of it
  is classified rake and multiplied by 1.34. **Fixing either error alone will make that assertion
  FAIL. That is correct.** The fixture carries this warning inline.

## ⭐ GUTTER SCOPE (Jason, resolved)
Roberts gutters 252.18 LF = **six main runs 33.33 + 29.77 + 44.70 + 43.05 + 13.29 + 14.33 = 178.47**
plus **73.71 LF of PORCH**, all outer perimeter (no returns against the wall). Engine eave reads
182.8 = **+2.4% vs the main runs** — the eave measurement was right all along; the apparent −27.5%
was entirely un-classified porch. ⛔ The porch roof IS in the linework (outline encloses 3,503 SF vs
the schedule's 3,431 SF under-roof, +2.1%) — it is a CLASSIFICATION gap, not missing geometry.
⛔ **Waste is a SEPARATE COLUMN on Skip's takeoff — 252.18 is RAW.** Compare raw to raw or invent a
phantom 10%.

## ⭐ SHOW THE WORK
Jason: *"The only way to be sure is if you show me what you are measuring, then I can tell you."*
Every geometry probe from here ships with an overlay first. Rendering the classification and letting
Jason mark it up resolved in two rounds what three rounds of reasoning could not.

## ⭐ 1x4 WINDOW TRIM — Jason's method ruling (2026-07-27)
**Trim runs around the whole ASSEMBLY. The mullion strip is built into the window, so a double
mull gets ONE perimeter, not two. DOORS GET NO TRIM.** Measured on the elevations by hand; the
plan's floor-plan size tags are a faithful proxy (a `3050` tag is 3'-0" x 5'-0" = 16 LF).

⛔ **The manual takeoffs measure per SASH and therefore run OVER on both graded houses:**
| | Skip | Jason's rule | Skip is over by |
|---|---|---|---|
| Burns | 214.79 | **206.67** | 8.1 LF |
| Roberts | 439.75 | **283.33** | **156.4 LF (~$700 at $4.50/LF)** |

The tell on Roberts: 439.75 over 14 openings is **31.41 LF per opening**, but the LARGEST opening
on that plan (`9062MU`, 9'-0" x 6'-2") has a perimeter of only 30.33 — impossible under the
assembly rule. Per WINDOW it is 19.12 LF, which matches a single `3062` sash at 18.33. Skip's Burns
window COUNT (13) carries the same error Jason overruled on the mulls — he read that unlabelled
`5450MU` as one window, and his trim number follows the same assumption.

⚠ Waste is a SEPARATE column (10% on this line) — 214.79 and 439.75 are RAW. Compare raw to raw.

---

## Data point #63 — L J SHOW RESIDENCE (Spalding Co., GA) — 7/31/26
### First head-to-head against Jason's own digital takeoff + estimate. Graded COLD.

**Grade: I ran +15.0% over on DIRECT cost.** Mine $694,024 vs Jason's stated
Builder Fixed Cost $383,494 + Allowances $220,062 = **$603,556**. Markup was near-exact
(mine $62,454 vs $60,872, +2.6%). His sell $797,314.

⭐ **THE HEADLINE: the overage was RATES, not measuring.** On the 12 lines comparable
line-for-line, my QUANTITY differences were worth **−$11,524** and my RATE differences
**+$43,562**. Framing lumber alone: I used the template's $14/SF against Jason's real
**$8/SF** on 5,530 SF = $33k of the gap. *The template is a candidate, never evidence* —
I knew that rule and leaned on the template anyway. **Ask for the live rate on the top-5
$ lines (framing lumber, framing labor, electrical $/SF, siding $/sq, drywall $/SF)
BEFORE pricing; never ship a template rate on a six-figure line.**

**MEASUREMENT VALIDATED (my geometry engine is sound):**
| quantity | mine | Jason | Δ |
|---|---|---|---|
| under-roof / framing SF | 5,529.8 | 5,529 | **0.0%** |
| porch ceiling SF | 1,370.2 | 1,370.7 | **0.0%** |
| electrical SF (heated+garage) | 4,284.2 | 4,284 | **0.0%** |
| slab SF | 5,529.8 | 5,473.8 | +1% |
| interior doors | 27 | 26 | +4% |
| fascia/soffit LF | 456.2 | 421 | +8% |
| gas lines | 3 | 3 | 0 |

Both of us independently split **metal from shingle by pitch zone** (his Metal 1/2/3-pitch,
my 1:12/2:12/3:12) — the low-slope-can't-be-shingled read was right.

**WHERE I WAS WRONG — and the fix now in code:**
1. ⛔⛔ **WINDOWS 22 vs his 46 (−52%). My worst miss ever on a count.** I counted
   FLOOR-PLAN tags. He counts openings **on the ELEVATIONS, sheet by sheet** (32 on
   sheet 8 front+rear, 14 on sheet 9 sides). My own elevation scan had already found 53
   tagged openings and I shipped the plan number anyway.
   → **`elevation_opening_count()`** counts off every elevation, derives opening-trim LF
   from the same count, and returns ok=False if the plan and elevation counts diverge
   >20%. Re-run on this set: **43 windows (sheet 9 exact at 14)** vs the shipped 22.
   → **`parse_opening_tag()`** reads J&J tags properly: `10080`=10'x8' (NOT 1'x8'),
   `80100`=8'x10', `(2)3060SH`=2 lites, `1260` sidelight kept.
2. **Masonry 562 SF vs his 1,105 SF (−49%).** Third job running I under-measure masonry.
   His takeoff shades each face as its own labelled polygon (413+408+120+163 SF).
   → **`cladding_completeness()`** forces every measured SF into a material bucket and
   reports the unallocated remainder. My first classifier silently DROPPED unclassified
   tiles — that is the leak; make it impossible, don't hope.
3. **Ext beam wrap 121 vs 291 LF (−58%).** I measured only the horizontal porch edge.
   His markup draws a vertical down **every porch post** and bills it in the same LF line.
   → **`beam_wrap_lf(horizontal, posts, post_ht)`**.
4. **1x4 window trim 310 vs 467 LF (−34%)** — a pure consequence of the bad window count;
   fixed by #1 (trim now derives from the counted openings' perimeters).
5. Over the other way: room perimeter 1,527 vs 1,220 LF (+25%, drove drywall +14% over —
   the flag I raised WAS real), corner boards +39%, gutters +47%, silt fence 900 vs 251 LF.
6. ⭐⭐ **MONO-SLAB FOOTER RULE (Jason, standing, confirmed 7/31/26): on a monolithic
   slab, carry the footer MATERIAL lines and NO footer labor.** The material —
   `Form Boards - Footer` + `Concrete - Footer` + `#4 Rebar Sticks - Footer` — is how
   J&J books the **extra concrete and rebar the thickened edge needs**. The labor is
   already inside `Labor - Monolithic slab` ($/SF), so a separate `Footer Labor` line
   would double-pay it. Show: assembly `Footers 16x18` = $8,892 = form boards $1,270 +
   concrete $6,144 + rebar $1,478, material only. **I carried NEITHER and ran $4,182
   light** on the thickened-edge scope (I had only a small grade-beam line).
   ⛔ The live **`Footer Labor` 635 LF x $20 = $12,700 in his export is the Davis #54
   crawl artifact** — it is parented to the *Crawlspace: Block walls* group, not to
   `Footers 16x18`. It is most of the $15,145 gap between a raw live-leaf reparse
   ($618,701) and Jason's stated direct ($603,556). Exclude it when grading.
   ⭐⭐ **FOOTER / THICKENED-EDGE LF.** Jason, 7/31/26, in three corrections:
   *"anywhere a porch or garage meets the house you have to include that area as LF of
   footer as well"* → *"the garage is one pour so no separate line"* → *"there still is a
   thickened slab edge between house and garage and porches"* → *"but the garages and
   porches are all one pour."*
   **RESOLVED MEANING:** it is ALL one monolithic pour, but the garage and porch slabs
   STEP DOWN from the house floor, so every internal transition still takes a thickened
   edge. Count each line exactly ONCE:
   `footer LF = outer perimeter of the WHOLE slab + every internal STEP line + interior bearing`
   L J Show measured off the sheet-2 SQFT polygons: outer 394.32 + garage step 75.42 +
   rear porch step 100.33 + front porch step 25.81 = **595.88 LF vs his 634.79 raw (−6.1%)**.
   ⭐⭐ **STANDING DEFAULTS (Jason, 7/31/26): ALWAYS assume a 16x18 footer unless he
   specifies different, and ALWAYS assume 3 sticks of rebar (3 bars continuous).**
   16x18 = **0.07407 CY/LF**. Rebar sticks = LF x 3 / 20, +10% waste (validated: his
   105.6 sticks = 634.79 x 3 / 20 x 1.10 = 104.74).
   ⛔ I had ASSUMED 16x18 by reading the template GROUP NAME `Footers 16x18` rather than a
   section detail — right answer, wrong method. And I used **2** bars, ~33% light on steel.
   ⚠ **FOUND IN HIS FILE:** his footer concrete is **32 CY on 634.79 LF**, but 16x18 over
   that length needs **47.02 CY** — 32 CY only covers **432 LF**. **Short 15.02 CY = $2,884**
   at $192/CY. Flagged to Jason.

   ✅ **RESIDUAL RESOLVED (Jason): basis + waste.** He draws his line down the MIDDLE of
   the footer; I trace the OUTER EDGE — *"which is the correct way to do it."* On a closed
   loop that basis shift is worth only ~4 LF (offsetting a loop by d changes it ~2*pi*d,
   independent of loop length: +12in = +7.9 LF, centreline −4in = −4.1 LF), so it never
   explains a 39 LF gap on its own. **The 10% waste factor absorbs the rest:**
   my raw 595.88 x 1.10 = **655.47 LF ordered, which EXCEEDS his raw 634.79 by 3.3%** —
   the scope is covered. ⚠ Note the logic precisely: waste multiplies BOTH numbers so it
   does not close a *percentage* gap between raw measures; what it does is make the gap
   immaterial **in ordering**. Money: the whole 38.91 LF is **$686 = 0.089%** of a
   $770,411 estimate (form boards $78 + concrete $553 + rebar $54).
   **Lesson: size the disagreement in DOLLARS before spending more measurement on it.**
   I chased a $686 line through three wrong hypotheses.
   ⛔⛔ **I HIT 635 TWICE BY ACCIDENT AND WAS WRONG BOTH TIMES:**
   (a) a **"1.64× perimeter" ratio** reverse-engineered from his total — pure curve-fitting;
   (b) **envelope + FULL porch outlines = 635.88 (+0.14%)** — which *double-counts* every
   house↔porch step and *omits* the house↔garage step entirely. It matched to a foot and
   was structurally wrong. **Matching the number is not the same as being right** — decompose
   the formula physically before accepting agreement as validation.
   Also: use the **UN-BUFFERED** perimeter; a 0.30 ft merge buffer rounds corners (+1.4%).
   → **`footer_lf(outer_perimeter_lf, step_lf, interior_bearing_lf)`**, self-tested at 595.88.

**FINDINGS IN JASON'S FILE (raised to him):**
- **Metal roof: takeoff 2,113 SF, estimate carries 264 SF** (~$14.8k hole). 264 × $8 =
  $2,112 ≈ his metal SF 2,112.97 — the quantity looks entered as a dollar amount.
- **Shingle waste dropped at the handoff:** takeoff 6,301.69 SF **@25%** = 7,877 SF;
  estimate carries 6,322 SF (~$3.5k). The Peterson leak, again. Also 25% is high —
  Southern bills ~10–11% over true surface, so **15% stands**.
- Drywall at $1.35 (V3 approved $1.44, 7/15/26); all cladding priced as one horizontal
  fiber-cement line at $2.50/SF with **no B&B line**, though the elevations are
  dominantly board-and-batten ($430/sq vs lap $330/sq).

**HIS TAKEOFF METHOD (adopt this structure):** alternating pages — a marked-up plan sheet
then a legend of what was measured on it. Each piece is its own **labelled polygon**
(126.36 ft², 205.58 ft², …), openings are **point markers**, trim is a **red perimeter
line per opening**, beam wrap is a **magenta vertical per post**. Waste is a SEPARATE
column per line (25% shingle / 15% metal / 10% siding, masonry, insulation) — his
quantities are RAW, so **compare raw-to-raw**.

## Data point #64 — ⭐⭐⭐⭐⭐ FRAMING LABOR IS PER FRAMED **LAYER**, NOT PER FOOTPRINT (Jason, 2026-08-04)

**This supersedes #33's "LABOR RATE LOCKED at $6.50/sf blended, DEFINITIVELY FLAT."** That
conclusion was wrong, and it was wrong in the most dangerous way available: it reconciled all
three actuals to within ~2% while being structurally incorrect.

### The framer's actual formula (Jason's words)
$6.00/SF buys **one framed system** over a given area. Count the systems:

| What | Layers | $/SF |
|---|---|---|
| Basement / 1st / 2nd / 3rd / garage, **including the roof over them** | 1 | $6 |
| Covered porch, or any roofed area outside the house | 1 | $6 |
| Deck — framing and posts only, no roof | 1 | $6 |
| **Covered deck** — the deck **and** the roof over it | **2** | **$12** |
| **Covered concrete patio** — the roof only; a slab is not framed | **1** | **$6** |

### It reconciles all three actuals at Jason's stated $6.00

| job | framed SF | covered deck | layered @ $6 | ACTUAL | Δ |
|---|---|---|---|---|---|
| Watkins | 4,518.00 | 292 | $28,860 | $28,862 | **+0.0%** |
| Peterson/Sailview | 3,198.00 | 258 (courtyard) | $20,736 | $20,688 | **+0.2%** |
| Wilson | 5,792.59 | 667.02 | $38,758 | $38,210 | **+1.4%** |

Flat $6.00 without the layer rule reads Wilson −9.0%, Peterson −7.3%, Watkins −6.1%.

### Why $6.50 "worked" and why that was the trap
The missing second layers averaged ~8% of framing labor. A flat rate absorbed them as a fake
premium, and the residual then got explained away in #33 as *"the ~3% spread is
complexity/site"* and *"DEFINITIVELY FLAT — NO size dependence."* Both readings were fitting
noise that was really structure. **Same failure as the two earlier `footer_lf` formulas that
hit Jason's number through cancelling errors: matching the number is not the same as being
right, and a fudge factor breaks the moment the geometry changes.**

Jason surfaced it by explaining the formula when the engine's assertion disagreed with his
stated rate. **The assertion firing is what produced the correction** — had the tolerance been
widened to make $6.00 pass, the structural rule would never have been found.

### Engine
- `framing_estimate(framed_sf, covered_deck_sf=...)` — the deck subset buys its second layer.
- `covered_deck_sf(rows)` — reads roofed DECK rows off the SQFT schedule **by label**, and
  returns a `review` list for what the label cannot settle. ⛔ `'uncovered'` contains
  `'covered'`; an uncovered deck has no roof and must NOT be doubled.
- ⚠ **A covered PORCH on a framed floor is also two layers and reads identical to a
  slab-on-grade porch in the schedule.** Wilson's COVERED FRONT PORCH (313.59) is treated as
  one layer, which is what reconciles it to +1.4% — but the label never proved that. Confirm
  slab vs framed per house. L J Show's rear covered porch: **Jason confirms PORCH on slab = 1
  layer** (house is slab), so the shipped estimate is unaffected.
- ⚠ Watkins' 292 SF is **Jason-confirmed, not yet measured off the sheet.** Independent
  measurement still owed.
