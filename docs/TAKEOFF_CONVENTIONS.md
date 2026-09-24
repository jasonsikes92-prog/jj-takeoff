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
- **Walls (siding, brick, stone): GROSS.** Never deduct window or door openings; Jason's siding sub doesn't either. Wall height = slab to top of plate. Gable triangles are added.
- **Corner boards** = every inside and outside corner on siding walls × full wall height.
- **Slab footers** = the whole slab perimeter PLUS added footers where each porch meets the house and where the garage wall meets the house.
- **Mono slab**: the "Concrete" line = the whole slab (house + garage + porch slabs).
- **Roof**: plan face area × pitch factor, by pitch.
  - Decorative dormers take the main pitch; read it off the SIDE elevations.
  - Low-slope porch roofs (3:12) are METAL.
- **Roof insulation**: spray foam at the roof deck = roof area (Davis, Anderson). Walls are batts.
- **Windows**: count on the elevations and reconcile against the plan tags. A mulled (2)3050 counts as 2. Decorative dormer windows count.
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
- **Plumbing**: full fixtures are anything with a drain (WC, lav, tub, shower, sinks, washer, dog wash, mop sink). Half fixtures are supply only (dishwasher, ice maker, each hose bib, extra shower valve).
- **Add lines the template lacks** when the plan shows them: laundry cabinets and top, utility sink, closet shelving, stone veneer or columns, dog wash, pass-through doors.

## Scoring against a key
- Keys mix raw and with-waste numbers, so compare against both. Shingle rows are confirmed with-waste (Davis: 7,105 = 5,684 × 1.25).
- A key can carry the estimator's own shortcuts (Skip on Davis #2), so not every difference is a measuring error.
- Once a key has been seen, any re-measure is NOT blind. Tag those changes RE-READ and score RULE changes separately.

## Open conflict (ask Jason)
- `jnj-estimate-takeoff/SKILL.md` says shingle waste is +15% and "do NOT use 25%". Jason's template and the Davis #2 key use 25%. Which one is right?
