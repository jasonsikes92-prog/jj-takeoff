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
6. **⛔ Draw EVERY measurement on the plan** (Jason 9/26, Villanueva: "How can I verify your measurements?"). Every quantity is a line, box or dot in the viewer, drawn on the sheet it was read from. That means the enlarged kitchen/bath sheets at their own scale, and the elevations for windows, corners and bay walls. Never ship a typed-in number (from labels, room dims or math) as MEASURED. Before calling a takeoff ready, list the items with `add_qty` or no pieces; that list must be empty. Drawing the 26 typed-in Villanueva items caught:
   - **Labels undercount fillers.** The SB36 hall vanity is 3.31 LF wall to wall; the master labels summed to 6.0 but the run is 6.27.
   - **Math hides wrong guesses.** Linen shelves ran the wrong way without checking where the door was: 7.3 LF, really 9.3.
   - **Numbers that can't be drawn are made up.** The "2 side corners" couldn't be found on the elevations.
   - **Misses go both ways.** Window casing 332 → 359 LF; living-room upper walls 367 → 405 SF.
   - **Drawing to the plan fill is not the whole rule.** I redrew the vanity tops to the cabinet fill only and dropped the splashes, breaking the countertop-against-a-wall rule below. Apply every convention to the drawn pieces too.
   - **Check the drawing, not your memory of it.** I "found" a missed upper cabinet that was already counted with the tall cabinets.
   - **Look at every auto-snap.** The window snap caught light fixtures and roof lines; render it and check.

## Output
Every line gets three columns:
- **RAW**: the measured quantity.
- **WASTE %**: from the template.
- **ORDER**: raw × (1 + waste).

Never bake waste into raw. Tag each line MEASURED, PLAN-STATED, ASSUMED, or JASON (answered). Keep the open questions on a second tab.

## Measurement rules
- **Siding method (Jason 9/24):** measure wall LF off the FLOOR PLAN (it catches the hidden recess walls) × the correct height for EACH wall. Read that height off the elevation dimension (bottom of siding to top plate); the garage may differ. Draw gables separately on the elevations, and always show the height used.
- **Dormers get siding:** the front face plus both side (cheek) walls. Only one side shows on an elevation, so multiply it (2 per dormer).
- **Walls (siding, brick, stone): GROSS.** Never deduct window or door openings, and that includes the GARAGE DOOR (Jason 9/24); Jason's siding sub doesn't deduct them either. Wall height = slab to top of plate. Gable triangles are added.
- **Corner boards** = every inside and outside corner on siding walls × full wall height.
- **Slab footers** = the whole slab perimeter PLUS added footers where each porch meets the house and where the garage wall meets the house. Where the garage meets a porch, that line gets a footer too (Villanueva garage/rear porch, Jason 9/25).
- **Mono slab**: the "Concrete" line = the whole slab (house + garage + porch slabs).
- **Roof**: plan face area × pitch factor, by pitch.
  - Decorative dormers take the main pitch; read it off the SIDE elevations.
  - Low-slope porch roofs (3:12) are METAL by default, but CONFIRM per house - Villanueva's 3:12 front porch is SHINGLE (Jason 9/25).
  - **A porch roof runs up to the wall it dies into** (Jason, Villanueva 9/25): between two front gables the porch roof continues up to the 2nd-floor wall. The roof plan's dashed outline stops short there, so draw the gap in.
  - **Small gable returns (the kick at the base of a front gable) take the gable's MAIN pitch** and belong inside the gable face (Jason, Villanueva 9/25: folded the 8:12 returns into the 10:12 faces). Never a separate low-pitch line.
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
- **Gutters** (Jason approved Anderson 9/24): eaves only; none on rakes/gable ends or dormers. **Downspouts go at BOTH ends of every gutter run** (a rear porch gutter between two wings gets 2), plus one where a long eave steps at a jog (Anderson front entry). Anderson = 8 downspouts, not 6.
- **Doors** (Jason approved Anderson 9/24): count one per LEAF off the plan swings (closet pair = 2). Doors from a BEDROOM into a shared (jack-and-jill) bath are **SOLID**, not hollow. Bedrooms, master, office, man cave = solid. Anderson = 12 hollow + 7 solid.
- **Centerline marks are NOT fixtures:** the CL symbol (a C with an L through it) on a plumbing plan marks a centerline dimension, not a shower head or drain. Count fixtures only from the drawn fixture symbols (Anderson: my 2nd master shower head was a CL mark; Jason 9/24).
- **Countertops against a wall** (Jason 9/24): where a top meets a wall WITHOUT a tile backsplash, draw the top out INTO the wall to cover the back splash and side splash(es). Always.
- **Two parallel cabinet lines on a wall = a row of LOWERS (line farther from the wall) + a row of UPPERS (line closer to the wall).** Kitchen uppers = the dashed line over the lowers, none over the hood or tall cabinets.
- **Pantry shelving: x3 shelves** on every shelf run (Jason 9/24).
- **Vent hood:** always count the kitchen vent hood cabinet (1 EA over the range) - it is its own line, not part of the uppers (Jason 9/24: I missed it in the viewer).
- **LVP NEVER goes under any cabinetry** - kitchen runs, island, vanities, laundry/mud room lowers (Jason 9/24). Cut every cabinet footprint out of the floor.
- **Niche in every tiled tub/shower:** any tub or shower with TILE walls gets a niche, **24x18 minimum, even if the plan does not show one** (Jason 9/24). Fiberglass/alcove surrounds do not.
- **Master wet room** (Anderson, Jason edit): the shower floor (mud bed) covers the wet room; the bath floor tile is the vanity side + WC only.
- **Spray foam (roof-deck foam jobs):** foam the roof deck over the HEATED house only - the **garage roof is NOT foamed**. The insulation company blocks off the garage with housewrap in the attic where it meets the house wall and foams that wall; count it (wall length x roof height above the plate). Overhangs and porches not foamed. The great-room SLOPED ceiling reads as 8:12 to a center ridge; openings are never deducted from drywall/insulation/base (Jason 9/25).
- **Everything above the ceiling joists gets foam** (Jason 9/25): roof deck over the heated house + every gable end over heated space + dormer walls + the housewrap-blocked wall at the garage. Garage gables/roof are not foamed.
- **Framed SF counts a porch ONLY when it has a roof over it** (Jason 9/25). Covered porch = framed (its roof is framed); an uncovered porch/patio/slab gets no framing. Anderson: front porch (under the main roof) + rear patio (metal roof) both count.
- **Drywall: measure EVERY wall in EVERY room** - both sides of every interior wall (Jason had to add the second side of walls I missed). **Never deduct doors or openings** - the drywaller buys the full sheet and cuts the opening out, so it counts (Jason 9/25).
- **Window casing:** every window gets interior casing + jambs - including DORMER windows and GARAGE windows (Jason added the dormer casing on Anderson 9/25). Measure the rough-opening perimeter; a mulled pair is one opening.
- **Door casing (interior):** every door gets casing - interior doors BOTH sides (2 legs x 6-8 + head, each side), closet pairs per opening, exterior doors (front/rear) on the inside only, garage entry both sides. Door and window casing go on the same casing-and-jambs line (Jason 9/25).
- **Window perimeter LF (one measurement, three uses)** (Jason 9/25): measure each window opening perimeter once (mulled pair = one opening). Use it for (1) the estimate line **1x4 Hardie / exterior casing**, (2) interior wood window casing, and (3) **wood window jambs if the customer wants wood jambs**. Door casing is separate (interior, both sides).
- **Baseboard = the full perimeter of every room, garage included** (Jason redrew Anderson 9/25: 685 -> 892 LF). Do NOT deduct cabinet runs, vanities, tubs, the fireplace or wet walls - like drywall, measure it all.
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
