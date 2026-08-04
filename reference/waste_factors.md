# J&J Waste Factors & Measurement Conventions
Source: J&J's Buildern **Measurements** template. Waste is added to the **takeoff QUANTITY** for material lines; rate-based turnkey lines carry waste in the $/unit. Confirmed/extended on Guarino (data point #7).

## Waste % by category (apply to quantity)
| Category | Waste | Basis |
|---|--:|---|
| Shingle roof | **15%** | true roof **surface** (Σ footprint×pitch factor), NOT footprint/heated. ⛔ MUST be priced — the #1 roofing leak is this waste being computed in the takeoff then DROPPED in the estimate (Peterson: priced 4,897 raw SF instead of 5,631 waste-loaded = $1,455 short). Southern bills only ~10-11% over surface on simple AND cut-up; 15% is correct/slightly conservative. (Was 25% — corrected June 2026 vs Burns + Peterson actuals.) |
| **Standing-seam metal roof** | **15%** | roof surface. Metal = SEPARATE vendor (not Southern — too expensive) |
| Concrete (footer, slab, 6", flatwork), block, brick veneer | **10%** | area / linear |
| Insulation (wall / floor / roof) | **10%** | area (note: J&J uses OPEN-CELL ~$1/SF) |
| Siding / cladding (incl. metal wall panel), corner, fascia, frieze | **10%** | area / linear |
| Tile, LVP, backsplash, T&G porch/interior ceiling, mud bed, Schluter | **10%** | area |
| Trim / base / crown / wrapped beams / 1x4 window trim | **10%** | linear |
| Stair railing (angled) | **33%** | linear |
| Countertops (granite / quartz) | **1.24%** | area (slab yield) |
| Doors, windows, fixtures, cabinet LF, garage doors | **0%** | count / linear |
| **Drywall** | **10%** | net room-by-room wall + ceiling surface; price the waste-adjusted order quantity |
| **Framing lumber, paint, electrical, duct, cleaning, grading** | **none on qty** | waste is in the $/SF turnkey rate |

Show the order quantity (incl. waste) the same in the Estimate `Quantity`, the Measurements tab, and the `Description` (e.g. "5,578 SF (incl. 15% waste)") so a sub/customer can trace it end-to-end.

## ⭐ DRYWALL — J&J takeoff method (NEVER use a heated-SF multiplier)
- **V3 order/priced quantity = net measured drywall x 1.10.** Price at **$1.44/SF**. Preserve net and waste-adjusted quantities separately; never apply waste twice. Source: completed Burns invoice 502225 and Jason's manual takeoff, confirmed 2026-07-15.
- **Walls** = Σ over rooms ( room interior **perimeter × ceiling height** ). Summing each room's perimeter counts shared partitions from both rooms (2 faces) and exterior walls once (interior face) — correct automatically.
- **Ceilings** = floor SF of each room with a drywalled ceiling.
- **Total drywall = walls + ceilings.**
- Use the **REAL per-zone ceiling height** — tall/stepped/exposed-deck walls run far above plate height. (Guarino: main house 15.5 ft avg [17' front / 14' back], garage ~10 ft. A flat 9-10 ft multiplier under-counted by ~2.5x.)
- **Exposed-ceiling builds: NO ceiling drywall** — instead spray-coat the exposed I-joists/ducts/foam black (heated+garage SF @ ~$3.5/SF; includes ignition-barrier coating for exposed foam — confirm code path).

## Unit normalization (fix on output)
Correct nonsensical template units to the real measure: area lines mislabeled "each" -> **sqft**; `yd`/`YD3` -> **CY**; `feet`/`ft` -> **LF**; keep real units (Rolls, Truck load, box, Days, month). Keep all measurements **imperial**.
