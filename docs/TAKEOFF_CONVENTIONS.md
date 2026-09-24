# J&J Hand-Takeoff Conventions (taught by Jason, 9/23/26)

This is how Jason measures, taught on Davis #2 and Anderson. **Follow it on every takeoff.** Copies live in:
- `C:\Users\jason\Astra-Takeover\TAKEOFF_CONVENTIONS.md` (canonical)
- `JJ-Takeoff` branch `astra-import` → `docs/TAKEOFF_CONVENTIONS.md`
- `~\.claude\skills\jnj-estimate-takeoff\reference\takeoff_conventions.md`

The item list is Jason's blank template, `Downloads\Measurements - Newest template 12_8_2025.xlsx`. The waste % comes from that template too.

## Process
1. **Enumerate every sheet** in the index and flag any that are missing. Look at every sheet visually; text-only skims miss fixtures.
2. **Verify scale on each sheet** against its own dimension strings. Chief Architect 1/4" = 1' is 18 pt/ft; 1" = 40' site is 1.8 pt/ft.
3. **Send Jason ONE batch of intake questions before measuring.** It must cover:
   - foundation type
   - missing sheets
   - exterior materials
   - door solid/hollow split
   - flooring by room
   - shower tile height
   - water, sewer and water heaters
   - driveway material and width
   - wooded or not
   - which way the lot falls
   - hose bibs and pull-down stairs
   - project duration

   Standard details on most plans (deck ledger, "basement" details) are NOT scope; ask about them rather than include them.
4. **Follow the job's own memory notes.** The Davis note said spray foam, and assuming attic insulation was a miss.
5. **Freeze the takeoff (sha256 + timestamp) before looking at any answer key.**

## Output
Every line gets three columns:
- **RAW**: the measured quantity.
- **WASTE %**: from the template.
- **ORDER**: raw × (1 + waste).

Never bake waste into raw. Tag each line MEASURED, PLAN-STATED, ASSUMED, or JASON (answered). Keep the open questions on a second tab.

## Measurement rules
- **Siding method (Jason 9/24):** measure wall LF off the FLOOR PLAN (it catches the hidden recess walls) × the correct height for EACH wall. Read that height off the elevation dimension (bottom of siding to top plate); the garage may differ. Draw gables separately on the elevations, and always show the height used.
- **Dormers get siding:** the front face plus both side (cheek) walls. Only one side shows on an elevation, so multiply it (2 per dormer).
- **Walls (siding, brick, stone): GROSS.** Never deduct window or door openings; Jason's siding sub doesn't either. Wall height = slab to top of plate. Gable triangles are added.
- **Corner boards** = every inside and outside corner on siding walls × full wall height.
- **Slab footers** = the whole slab perimeter PLUS added footers where each porch meets the house and where the garage wall meets the house.
- **Mono slab**: the "Concrete" line = the whole slab (house + garage + porch slabs).
- **Roof**: plan face area × pitch factor, by pitch.
  - Decorative dormers take the main pitch; read it off the SIDE elevations.
  - Low-slope porch roofs (3:12) are METAL.
- **Roof insulation**: spray foam at the roof deck = roof area (Davis, Anderson). Walls are batts.
- **Windows**: count on the elevations and reconcile against the plan tags. A mulled (2)3050 counts as 2. Decorative dormer windows count.
  - **Oversized tempered window at a tub gets its OWN line**, separate from the standard window count, because it costs more (Jason, Roberts 9/23). Check every window at a tub or shower for a tempered/oversized note.
- **Doors**: leaves by height (6'8 / 8'). Jason gives the solid/hollow split; on Anderson, bedrooms, office and man cave are solid.
  - A closet pair = 2 leaves.
  - Barn doors are easy to miss: look for panel lines drawn beside an opening.
  - Cased openings get their own list.
- **Can lights**: count the plan symbols exactly (verify by symbol, not by the "R4" labels), then add Jason's standards on a separate line:
  - cans in the garage (Anderson: 6);
  - a can over every tub and every shower;
  - never a fan/light combo: the exhaust fan and the light are separate.
- **Vanity bars** (3 circles) are not cans.
- **Islands**: a 48"-deep island has cabinets on both faces, so LF × 2.
- **Tall cabinets** include the fridge surround, oven tower and linen tower.
- **Tile floor goes UNDER tubs and cabinets** (correct method; Skip's Davis key skipped under-cabinet). The **shower floor is its own line** (a different tile), never inside bath floor tile.
- **LVP does NOT go under tubs or cabinets.** Deduct tub, vanity, base cabinet and island footprints.
- **Bedroom flooring gets its own line**, separate from common-area flooring.
- **Primary shower tile runs to the CEILING** (wall LF × ceiling height). Secondary tub/showers get fiberglass surrounds unless the plan shows tile.
- **Shelving** = shelf LF × number of shelves:
  - pantries and bath linen closets: × 3;
  - bedroom/other closets: 1 shelf + rod, so × 1.
- **Stone columns** = 4 sides.
- **Plumbing** (Jason 9/23):
  - **Full fixtures**: anything with a drain (WC, lav, tub, shower, sinks, laundry washer box, dog wash, mop sink), PLUS **every water heater, whether or not it's drawn** (2 WH = 2 fixtures), PLUS **each shower head** in a multi-head shower (Davis markup: master shower 2 heads = 2 fixtures).
  - **Half fixtures**: supply only (dishwasher, fridge/ice maker, each hose bib).
- **Downspouts**: one at each gutter-end roof corner, **13 ft each on a 1-story** (Jason 9/23).
- **Corner boards**: count each face of an outside corner (Anderson markup).
- **Driveway off a main highway**: carry a concrete apron at the road even if the drive is gravel (Jason 9/23).
- **Add lines the template lacks** when the plan shows them: laundry cabinets and top, utility sink, closet shelving, stone veneer or columns, dog wash, pass-through doors.

## Scoring against a key
- ⛔ Confirm the key was measured on the SAME plan revision (Anderson: it wasn't). Read the key's markup pages, not just its totals.
- **The plans are the source of truth.** Work from them exclusively unless the owner directs otherwise. A key estimate (e.g. Skip's) may carry homeowner changes, but it can also carry mistakes, so VERIFY every scope conflict with Jason; never adopt one silently.
- Keys mix raw and with-waste numbers, so compare against both. Shingle rows are confirmed with-waste (Davis: 7,105 = 5,684 × 1.25).
- A key can carry the estimator's own shortcuts (Skip on Davis #2), so not every difference is a measuring error.
- Once a key has been seen, any re-measure is NOT blind. Tag those changes RE-READ and score RULE changes separately.

## Rulings (Jason, 9/23/26)
- **Shingle waste = 25%.** This settles the conflict with `jnj-estimate-takeoff/SKILL.md`, which said 15%; the skill now says 25%. The engine's `roofing_estimate()` still hard-codes 15%, so override it.
- **Roberts windows = 22.**
