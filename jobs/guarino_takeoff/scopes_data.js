// Scope narrative content for Guarino Residence bid packages.
// Quantities tables are populated separately from scope_lines.json.
module.exports = function (PROJ) {
  const C = PROJ.county;
  return [

  // ---------------- 01 SITE WORK ----------------
  {
    num: "01", title: "Site Work & Earthwork",
    subtitle: "Clearing · Grading · Construction Drive",
    overview: "Contractor to furnish all labor, equipment, and materials to clear, strip, and rough-grade the building site and construct a stable gravel construction drive. Lot is a pasture (subdivision corner lot) — no tree clearing or demolition anticipated. Silt fence and erosion controls are a separate package (Scope 01B).",
    includes: [
      "Grubbing and mulching of the building pad and drive corridor.",
      "Lot clearing and excavation / rough cut-and-fill to establish building pad.",
      "Construct concrete wash-out pit per local code.",
      "Set culvert pipe at drive entrance and install driveway mat.",
      "Place #34 gravel construction drive to house site, 12 ft wide (≈1,320 SF)."
    ],
    excludes: [
      "Silt fence and temporary erosion/sediment controls (Scope 01B).",
      "Final grading, backfill, sod, and landscaping (Scope 27).",
      "Final concrete driveway and walkways (Scope 26B).",
      "Footing/foundation excavation and slab gravel (Scope 05).",
      "Septic system and drain field (Scope 02); utility trenching for water/electric.",
      "Boundary survey and erosion-control plan engineering (by others)."
    ],
    note: "Grubbing/mulching and lot clearing are carried as allowances — quantities above estimate are billed at cost plus 20% via signed change order. Confirm disturbed-area limits before mobilizing. Erosion controls (Scope 01B) must be in place before ground disturbance.",
    codes: [
      "2018 IRC Chapter 18 — Soils and Foundations",
      "Georgia Erosion and Sediment Control Act (OCGA 12-7)",
      "NPDES Construction General Permit — Georgia EPD",
      `${C} Land Disturbance Permit requirements`,
      "OSHA 29 CFR 1926 Subpart P — Excavation Safety"
    ],
    prework: [
      "Confirm property lines, building corners, and finished-floor elevation with J & J.",
      "Confirm land-disturbance permit is issued before any ground disturbance.",
      "Locate and mark all existing utilities (call 811) before digging."
    ],
    completion: [
      "Building pad cut to correct elevation and compacted; drains positively away from pad.",
      "Construction drive passable for concrete and delivery trucks in wet weather.",
      "Disturbed area ready; erosion controls (Scope 01B) confirmed in place."
    ]
  },

  // ---------------- 01B SILT FENCE & EROSION CONTROL ----------------
  {
    num: "01B", title: "Silt Fence & Erosion Control",
    subtitle: "BMPs · Silt Fence · NPDES",
    overview: "Contractor to furnish all labor and materials to install and maintain temporary erosion and sediment control best-management-practices (BMPs) — silt fence on all downhill slopes of disturbed areas — in accordance with the approved erosion-control plan and the NPDES Construction General Permit. Controls must be in place before any ground disturbance.",
    includes: [
      "Install silt fence on all downhill slopes of disturbed areas, per local code (≈750 LF).",
      "Trench in and anchor silt fence; install supplementary BMPs as the plan requires (inlet protection, check dams, construction exit).",
      "Inspect and maintain BMPs through construction; repair after storm events.",
      "Remove temporary controls at final stabilization."
    ],
    excludes: [
      "Clearing, grading, and construction drive (Scope 01).",
      "Concrete wash-out pit (Scope 01).",
      "Final grading, sod, and permanent stabilization (Scope 27).",
      "Erosion-control plan engineering and NOI/NOT filing (by others)."
    ],
    note: "Silt fence and BMPs must be installed BEFORE any land disturbance and maintained per the NPDES permit. Quantity (≈750 LF) is based on estimated disturbed-area perimeter — confirm actual disturbed limits before mobilizing.",
    codes: [
      "Georgia Erosion and Sediment Control Act (OCGA 12-7)",
      "NPDES Construction General Permit — Georgia EPD",
      "Georgia Manual for Erosion and Sediment Control (Green Book)",
      `${C} — Land Disturbance Permit / erosion-control inspection`
    ],
    prework: [
      "Confirm approved erosion-control plan and disturbed-area limits with J & J.",
      "Confirm land-disturbance permit is issued before installing controls.",
      "Confirm BMP locations (silt fence, inlet protection, construction exit)."
    ],
    completion: [
      "Silt fence installed continuously on all downhill perimeters and trenched in.",
      "All required BMPs in place before ground disturbance begins.",
      "Passes initial county/EPD erosion-control inspection.",
      "Maintenance plan understood; repairs made after rain events."
    ]
  },

  // ---------------- 02 SEPTIC ----------------
  {
    num: "02", title: "Septic System",
    subtitle: "Design · Permit · Install · 4-Bath",
    overview: "Licensed Georgia septic contractor to design, permit, and install a complete on-site sewage management system sized for a 4-bathroom residence, per Newton County Environmental Health specifications. Likely engineered/Level-3 system on a new subdivision lot.",
    includes: [
      "Soil/percolation evaluation and septic system design.",
      "Septic permit application and fees through Newton County Environmental Health.",
      "Supply and install tank, distribution box, and drain field/absorption lines.",
      "Excavation, bedding, backfill, and final grade over the field.",
      "Coordinate sewer stub-out location with plumber (Scope 09)."
    ],
    excludes: [
      "Interior plumbing and building sewer to the 5-ft line (Scope 09).",
      "Final landscape grading and seeding over the field (Scope 27).",
      "Public water service (Scope 09 — water meter/tap)."
    ],
    note: "Carried as a $13,000 allowance. System type (conventional vs. engineered/pump) must be confirmed against the county-approved design; cost reconciled by change order once the permit is issued.",
    codes: [
      "Georgia DPH Rule 511-3-1 — On-Site Sewage Management Systems",
      "Newton County Environmental Health Department requirements",
      "2018 IRC Chapter 32 — Plumbing reference"
    ],
    prework: [
      "Confirm approved septic design and permit are in hand before excavation.",
      "Confirm field location does not conflict with drive, well/water line, or structure setbacks."
    ],
    completion: [
      "System installed per approved design; as-built provided to J & J.",
      "Passes Newton County Environmental Health final inspection.",
      "Tank locations and clean-outs documented for the owner."
    ]
  },

  // ---------------- 04 PROPANE ----------------
  {
    num: "04", title: "Propane & Gas Supply",
    subtitle: "1,000-Gal Buried Tank · Set & Bury",
    overview: "Contractor to furnish and set a 1,000-gallon buried propane tank, including excavation, anchoring, and backfill, and coordinate first fill. Gas piping to appliances is by the mechanical trade (Scope 10).",
    includes: [
      "Furnish 1,000-gallon propane tank (buried) — allowance.",
      "Excavate, set, anchor, and bury tank per NFPA 58 separation distances.",
      "Backfill and rough-grade over tank.",
      "Coordinate tank location and stub with the gas/mechanical trade and J & J."
    ],
    excludes: [
      "Gas distribution piping from tank to appliances (Scope 10 — HVAC & Interior Gas).",
      "Final grade and landscaping over tank (Scope 27).",
      "Appliance and fireplace connections."
    ],
    note: "Tank is carried as a $7,500 allowance plus $1,000 to bury. Confirm whether owner prefers gas tankless water heaters off this tank (currently estimated as electric heat-pump units).",
    codes: [
      "NFPA 58 — Liquefied Petroleum Gas Code",
      "NFPA 54 / 2018 IFGC — National Fuel Gas Code",
      "Georgia Public Service Commission — LP gas regulations"
    ],
    prework: [
      "Confirm tank location meets NFPA 58 clearances from structure, drive, and ignition sources.",
      "Confirm utility/electric and septic locations to avoid conflict."
    ],
    completion: [
      "Tank set level, anchored, and buried to manufacturer spec.",
      "System leak-tested; first fill scheduled.",
      "Location documented for the mechanical trade tie-in."
    ]
  },

  // ---------------- 05 FOUNDATION ----------------
  {
    num: "05", title: "Foundation & Monolithic Slab",
    subtitle: "Footers · 4\" Slab · Vapor Barrier · Termite",
    overview: "Contractor to furnish all labor, equipment, and materials to form and pour the footings and a monolithic slab-on-grade foundation, including sub-slab gravel, vapor barrier, reinforcing, and termite pre-treatment. 3,000 PSI fiber-reinforced concrete.",
    includes: [
      "Form and pour footers (≈490 LF form board; ≈23 CY concrete; #4 rebar continuous).",
      "Place #57 sub-slab stone (≈6 truck loads) and 6-mil vapor barrier.",
      "Set mesh chairs and #4 rebar grid at 24\" OC; pour 4\" monolithic slab (≈58 CY).",
      "Labor to place, finish, and cure monolithic slab (≈3,841 SF).",
      "Pump truck for slab pour.",
      "Termite soil pre-treatment by a licensed applicator (≈$900)."
    ],
    excludes: [
      "Footing/pad excavation and rough grade (Scope 01).",
      "Under-slab plumbing and electrical rough-in (Scopes 09 / 11) — coordinate before pour.",
      "Slab staining/sealing as the finished floor (Scope 21).",
      "Exterior flatwork — drive, walks, porch slabs poured later (Scope 26B)."
    ],
    note: "The slab is the finished floor (stained/sealed — Scope 21). Finish flatness and freedom from cracking, stains, and control-joint defects are critical. Coordinate all under-slab rough-ins and inspect before pour. Slab reinforcing was upgraded to a #4 rebar grid.",
    codes: [
      "2018 IRC Chapter 4 — Foundations (R401–R408)",
      "2018 IRC R506 — Concrete slab-on-ground floors",
      "ACI 318 — Building Code Requirements for Structural Concrete",
      `${C} — Foundation/slab inspection requirements`,
      "OSHA 29 CFR 1926 Subpart Q — Concrete and Masonry Construction"
    ],
    prework: [
      "Confirm building pad elevation, dimensions, and squareness with J & J.",
      "Verify all under-slab plumbing/electrical is installed, inspected, and protected.",
      "Confirm termite pre-treat is applied and documented before pour.",
      "Confirm vapor barrier is continuous and lapped before steel placement."
    ],
    completion: [
      "Footing and slab pass county inspection prior to and after pour as required.",
      "Slab finished flat and clean — suitable to receive stain/seal as the final floor.",
      "Control/saw joints cut per plan; no spalling or surface defects.",
      "Termite treatment certificate provided to J & J."
    ]
  },

  // ---------------- 07 FRAMING ----------------
  {
    num: "07A", title: "Framing Lumber — Materials",
    subtitle: "Supply Scope · J&J Will Purchase",
    supply: true,
    overview: "Supplier to furnish and deliver the framing lumber package for the residence. This is a material-supply scope for pricing only — J & J purchases the package. Framing labor is a separate scope (07B); the engineered floor system is a separate scope (07C).",
    includes: [
      "Framing lumber package — 2x4 walls, 2x8 ceiling joists, 2x6 rafters (SYP/SPF), ≈4,188 SF.",
      "All plates, headers, blocking, and miscellaneous dimensional lumber per plan.",
      "Connectors/hardware (Simpson Strong-Tie) per the connector schedule if included.",
      "Delivery to site, staged per J & J direction."
    ],
    excludes: [
      "Engineered floor/roof system — I-joists/trusses (Scope 07C).",
      "Framing labor (Scope 07B).",
      "Sheathing/cladding (Scope 14); roofing (Scope 08)."
    ],
    note: "Lumber pricing is volatile and date-stamped 2026-06-25 — confirm current pricing and lead time at award. Provide a takeoff-based package quote against the framing plans.",
    codes: [
      "2018 IRC Chapters 5, 6, 8 — Floors, Walls, Roof-Ceiling Construction",
      "AWC Wood Frame Construction Manual (WFCM)",
      "PS 20 — American Softwood Lumber Standard (grade stamps required)"
    ],
    prework: [
      "Confirm species/grade, package scope, and current pricing at award.",
      "Confirm connector/hardware schedule with the EOR.",
      "Confirm delivery date and staging with J & J."
    ],
    completion: [
      "Package delivered complete and grade-stamped; quantities verified against ticket.",
      "Materials staged and protected from weather on site.",
      "Any shortages/back-orders reported to J & J immediately."
    ]
  },

  // ---------------- 07B FRAMING LABOR ----------------
  {
    num: "07B", title: "Framing Labor",
    subtitle: "Labor Only · J&J Supplies All Materials",
    overview: "Contractor to furnish all labor and equipment to frame the residence complete — walls, low-slope engineered roof/ceiling structure, beams, and blocking. J & J furnishes all framing lumber (Scope 07A) and the engineered floor system (Scope 07C); this scope is labor only.",
    includes: [
      "Frame all walls, set ceiling/roof structure, beams, headers, and blocking, ≈4,188 SF.",
      "Install all Simpson Strong-Tie connectors and hardware per the connector schedule.",
      "Set engineered floor/roof members furnished under Scope 07C.",
      "Install windows/exterior doors if directed (coordinate with Scope 15).",
      "Report any material shortages or defects to J & J immediately."
    ],
    excludes: [
      "Framing lumber and engineered members — furnished by J & J (Scopes 07A / 07C).",
      "Metal wall cladding, fascia, and porch ceilings (Scope 14).",
      "Roofing membrane/panels (Scope 08).",
      "Interior trim, doors, and stairs (Scope 16); insulation (Scope 12)."
    ],
    note: "Roof is low-slope (½:12 / 1:12) framed as an engineered open-span system. Exposed structure must be clean and consistent because ceilings are LEFT EXPOSED and sprayed black (Scope 17) — framing quality is a finished-appearance item, not just structural.",
    codes: [
      "2018 IRC Chapters 5, 6, 8 — Floors, Walls, Roof-Ceiling Construction",
      "AWC Wood Frame Construction Manual (WFCM)",
      "Simpson Strong-Tie Connector Installation Guide",
      `${C} — Framing inspection requirements`
    ],
    prework: [
      "Confirm slab dimensions and squareness before plating.",
      "Confirm engineered roof/floor layout and connector schedule with the EOR.",
      "Confirm lumber and engineered package (Scopes 07A/07C) are on site and complete."
    ],
    completion: [
      "Structure framed plumb, level, and square; all connectors installed per plan.",
      "Exposed framing is clean and consistent (it remains visible in finished home).",
      "Passes county framing inspection.",
      "Ready to receive cladding, roofing, and rough-in trades."
    ]
  },

  // ---------------- 07C ENGINEERED FLOOR ----------------
  {
    num: "07C", title: "Engineered Floor System — Materials",
    subtitle: "Supply Scope · J&J Will Purchase · I-Joists/Trusses",
    supply: true,
    overview: "Supplier to design, furnish, and deliver the engineered floor/roof system (wood I-joists or trusses) for the low-slope open-span structure, ≈4,850 SF. This is a material-supply scope for pricing only — J & J purchases the package; framing labor sets it (Scope 07B).",
    includes: [
      "Engineered wood I-joists or trusses for the low-slope roof/floor system, ≈4,850 SF.",
      "Sealed engineering layout, member design, and hangers/connectors as required.",
      "Rim board, bridging/strongbacks, and accessories per the engineered layout.",
      "Delivery to site coordinated with the framing schedule."
    ],
    excludes: [
      "Dimensional framing lumber (Scope 07A).",
      "Framing labor / installation (Scope 07B).",
      "Roofing (Scope 08); insulation (Scope 12)."
    ],
    note: "Priced as an open-span engineered system because rafters are dropped (no double-count). Provide a sealed layout and current pricing/lead time at award. Confirm whether I-joists or trusses best suit the low-slope exposed design.",
    codes: [
      "2018 IRC R502 / R802 — Engineered wood floor & roof framing",
      "ANSI/TPI 1 — National Design Standard for Metal Plate Connected Wood Truss Construction",
      "APA / manufacturer (I-joist) engineering and installation specifications"
    ],
    prework: [
      "Confirm structural layout, spans, and loads with the EOR.",
      "Confirm I-joist vs. truss selection for the exposed low-slope design.",
      "Confirm sealed layout, pricing, and lead time at award."
    ],
    completion: [
      "Sealed engineered layout and members delivered complete; verified against ticket.",
      "Hangers/accessories included; staged and protected on site.",
      "Any shortages/back-orders reported to J & J immediately."
    ]
  },

  // ---------------- 08 ROOFING ----------------
  {
    num: "08", title: "Roofing & Gutters",
    subtitle: "Standing-Seam Metal · Low-Slope · 6\" K-Style",
    overview: "Contractor to furnish and install a standing-seam metal roof system, mechanically-seamed for low slope, turnkey, plus gutters and downspouts. Roof is nearly flat (½:12 / 1:12) and requires a low-slope-rated panel and underlayment assembly.",
    includes: [
      "Standing-seam metal roof, mechanically-seamed low-slope panels, ≈5,578 SF, turnkey (allowance).",
      "High-temp underlayment and all flashings, closures, ridge/eave trim.",
      "6\" K-style gutters (≈200 LF) and 3\" downspouts (≈100 LF).",
      "All penetrations flashed watertight; coordinate with plumbing/HVAC vents."
    ],
    excludes: [
      "Roof framing and decking (Scope 07).",
      "Fascia and metal wall cladding (Scope 14).",
      "Interior gutters/scuppers if drainage design changes (confirm)."
    ],
    note: "Low-slope roof is the single largest line and biggest risk — confirm panel profile, seam type, and warranty, and obtain a low-slope-rated roofer quote ($9–13/SF range). Confirm whether parapet/internal drains or scuppers are required instead of K-style gutters.",
    codes: [
      "2018 IRC Chapter 9 — Roof Assemblies (R901–R908)",
      "2018 IRC R905.10 — Metal roof panels (low-slope assembly per mfr listing)",
      "2018 IRC R903.3 — Gutters and downspouts",
      "NRCA Roofing Manual — Low-slope metal systems"
    ],
    prework: [
      "Confirm low-slope panel system is listed/warranted for the actual roof pitch.",
      "Confirm decking/underlayment assembly with manufacturer.",
      "Coordinate all roof penetration locations before installation."
    ],
    completion: [
      "Roof watertight; water-test or inspect all seams, flashings, and penetrations.",
      "Gutters sloped to downspouts; downspouts discharge away from foundation.",
      "Manufacturer warranty documentation provided to J & J.",
      "Passes county roofing/dry-in inspection."
    ]
  },

  // ---------------- 09 PLUMBING ----------------
  {
    num: "09", title: "Plumbing",
    subtitle: "Water Tap · Rough-In · Fixtures · 4 Baths",
    overview: "Contractor to furnish all labor and materials for complete plumbing: public water tap/meter connection, under-slab and rough-in DWV and supply, water heaters, and set all fixtures for a 4-bathroom + kitchen + laundry residence. Fixture and fixture-trim items are owner allowances.",
    includes: [
      "Connect to public water main; meter and tap fee (allowance, billed at cost).",
      "Under-slab and above-slab rough-in: 20 fixture openings + 12 water openings (fridge, ice maker, washer, hose bibs).",
      "Two high-efficiency water heaters (allowance).",
      "Set all fixtures: kitchen sink + faucet + pot filler; 4 toilets; vanity sinks/faucets/drains (baths 1–4); master freestanding tub + valve; shower valves/heads (all baths).",
      "Hose bibs, washer box, and all trim/connections."
    ],
    excludes: [
      "Septic system and building sewer beyond the 5-ft line (Scope 02).",
      "Gas piping to appliances/water heaters (Scope 10).",
      "Tile shower pans/mud beds (Scope 18); shower glass (Scope 23).",
      "Vanity cabinets and countertops (Scopes 19 / 20)."
    ],
    note: "Confirm electric heat-pump vs. gas tankless water heaters (propane is available on site — Scope 04). All fixtures are allowances; final selections and trim finishes to be confirmed before rough-in of valves.",
    codes: [
      "2018 IPC — International Plumbing Code",
      "Georgia State Minimum Standard Plumbing Code",
      "2018 IRC Chapters 25–32 — Plumbing",
      `${C} — Plumbing permit and inspection`
    ],
    prework: [
      "Confirm fixture selections, locations, and rough-in heights with J & J/owner.",
      "Confirm water heater type (electric vs. gas tankless) before rough-in.",
      "Coordinate under-slab rough-in and inspection BEFORE slab pour (Scope 05)."
    ],
    completion: [
      "Rough-in passes inspection; pressure/DWV tests pass.",
      "All fixtures set, sealed, and operational; no leaks.",
      "Water heaters operational; hose bibs and washer box functional.",
      "Final plumbing inspection passed."
    ]
  },

  // ---------------- 10 HVAC ----------------
  {
    num: "10", title: "HVAC & Interior Gas",
    subtitle: "2 Systems · Master Zone · Exposed Duct · Gas Lines",
    overview: "Contractor to furnish all labor and materials for complete HVAC: two systems (house + conditioned garage), a master-suite zone damper, all ductwork, and interior gas piping to appliances. Per the exposed-structure design, main ductwork is hard spiral/exposed and must be installed to a finished-appearance standard.",
    includes: [
      "House air handler and condensing unit, high-efficiency (allowance).",
      "Separate HVAC system for the conditioned garage.",
      "Hard spiral / exposed ductwork for main living areas (design intent: exposed).",
      "Flex duct work to garage; supply/return registers and grilles.",
      "Zoned damper to separate master-suite cooling.",
      "Interior gas piping to fireplace, furnace, tankless WH, ranges (2 connections)."
    ],
    excludes: [
      "Propane tank set and bury (Scope 04).",
      "Spray-coating exposed duct black (Scope 17 — painting).",
      "Electrical connections/disconnects to equipment (Scope 11)."
    ],
    note: "Main ductwork is EXPOSED and sprayed black (Scope 17) — runs must be straight, level, and laid out cleanly as a finished element, not hidden. Two systems are driven by the conditioned garage and master comfort. Get equipment + exposed-spiral-duct quote; this is a high-scatter line.",
    codes: [
      "2018 IMC — International Mechanical Code",
      "2018 IFGC — International Fuel Gas Code; NFPA 54",
      "Georgia State Minimum Standard Mechanical Code",
      "ASHRAE 62.2 — Ventilation and Indoor Air Quality",
      `${C} — Mechanical and gas permit`
    ],
    prework: [
      "Confirm exposed-duct routing and layout with J & J before fabrication (appearance matters).",
      "Confirm equipment selections, zoning, and load calc (Manual J/D).",
      "Coordinate gas appliance locations and propane tank stub (Scope 04)."
    ],
    completion: [
      "Both systems operational; refrigerant charged; condensate drained properly.",
      "Exposed ductwork straight, level, and clean — ready for black spray-coat.",
      "Gas piping leak-tested and inspected.",
      "Master zone damper functional; final mechanical/gas inspections passed."
    ]
  },

  // ---------------- 11 ELECTRICAL ----------------
  {
    num: "11", title: "Electrical",
    subtitle: "400A Service · Wiring · Lighting · Low-Voltage",
    overview: "Contractor to furnish all labor and materials for complete electrical: 400-amp service and panel, code-minimum wiring throughout, lighting, and low-voltage/security rough-in. Additional electrical beyond code minimum is billed at cost plus 20%.",
    includes: [
      "Code-minimum wiring on SF basis (≈3,841 SF); 200A service/panel base, upgraded to 400A.",
      "Permanent power service connection from transformer.",
      "Low-voltage, data, alarm, and camera rough-in (allowance).",
      "45 can lights + wiring; 8 fans/lights; under-cabinet LED at kitchen.",
      "Vanity light fixtures at all 4 baths.",
      "Smoke/CO alarms, devices, plates, and panel labeling."
    ],
    excludes: [
      "Light fixtures beyond those listed (decorative fixtures may be owner-supplied — confirm).",
      "HVAC equipment wiring beyond disconnects (coordinate with Scope 10).",
      "Exposed conduit feature wiring unless directed (industrial aesthetic — confirm)."
    ],
    note: "Industrial-modern design may call for exposed conduit, which is pricier — confirm with J & J and get a quote (high-scatter line). 400A service and LV allowance are carried.",
    codes: [
      "NFPA 70 — National Electrical Code (NEC) 2020",
      "Georgia State Minimum Standard Electrical Code",
      "2018 IRC R314 — Smoke alarms; R315 — CO alarms",
      `${C} — Electrical permit and inspection`
    ],
    prework: [
      "Confirm service size/location and meter base with utility and J & J.",
      "Confirm lighting plan, device locations, and any exposed-conduit design.",
      "Coordinate panel and rough-in with framing and exposed-ceiling design."
    ],
    completion: [
      "Service energized; panel labeled; all circuits tested.",
      "Devices, fixtures, and smoke/CO alarms installed and functional.",
      "Rough-in and final electrical inspections passed.",
      "Low-voltage rough-in coordinated and documented."
    ]
  },

  // ---------------- 12 INSULATION ----------------
  {
    num: "12", title: "Insulation",
    subtitle: "Open-Cell Spray Foam · Walls & Roof Deck",
    overview: "Contractor to furnish and install spray-foam insulation at walls and roof deck. Roof deck is an unvented low-slope assembly with the foam left exposed (then sprayed black — Scope 17), so foam must be installed to a clean, consistent finished appearance.",
    includes: [
      "Spray-foam insulation at walls (≈7,986 SF) — allowance.",
      "Spray-foam insulation at roof deck / ceiling (≈5,585 SF) — allowance.",
      "Achieve Georgia Climate Zone 3 R-value minimums.",
      "Mask and protect adjacent surfaces; trim foam clean at exposed areas."
    ],
    excludes: [
      "Ignition-barrier / black spray-coat over exposed foam (Scope 17).",
      "Drywall (Scope 13)."
    ],
    note: "CONFIRM open-cell vs. closed-cell. An unvented low-slope roof deck typically requires closed-cell at the deck; walls may be open-cell. Because foam is exposed, the finished spray must be uniform. Confirm the code-compliant ignition-barrier path with Newton County.",
    codes: [
      "Georgia Energy Code — R-value minimums (Climate Zone 3)",
      "2018 IRC Chapter 11 — Energy Efficiency",
      "2018 IRC R316 — Foam plastic / ignition & thermal barrier requirements",
      "2018 IRC R302.11 — Fireblocking"
    ],
    prework: [
      "Confirm open-cell vs. closed-cell at walls and roof deck.",
      "Confirm unvented roof assembly detail and ignition-barrier path with the county.",
      "Confirm all rough-ins are inspected and complete before foam."
    ],
    completion: [
      "Coverage and depth meet specified R-values; no voids.",
      "Exposed foam trimmed clean and uniform, ready for black coating.",
      "Insulation inspection passed."
    ]
  },

  // ---------------- 13 DRYWALL ----------------
  {
    num: "13", title: "Drywall",
    subtitle: "Level 4 · Walls Only · Exposed Ceilings",
    overview: "Contractor to furnish all labor and materials to hang, tape, and finish drywall to Level 4 on interior walls. Ceilings are LEFT EXPOSED per the design (exposed structure, ducts, and foam) — no ceiling board.",
    includes: [
      "Hang, tape, and finish drywall Level 4 on interior walls (≈17,939 SF).",
      "Corner bead, fasteners, and joint treatment.",
      "Garage fire-separation assembly per code where required.",
      "Sand and prep walls ready for paint (Scope 17)."
    ],
    excludes: [
      "Ceiling drywall — ceilings remain exposed (Scopes 07/10/12 finish).",
      "Painting (Scope 17); insulation (Scope 12).",
      "Tile backer/cement board at wet walls (Scope 18)."
    ],
    note: "Ceilings are intentionally exposed — do NOT board ceilings. Wall terminations at the exposed ceiling/structure must be clean and detailed since the transition is visible.",
    codes: [
      "2018 IRC Section R702 — Interior Covering",
      "2018 IRC R302.6 — Dwelling/garage fire separation",
      "ASTM C840 — Application of gypsum board"
    ],
    prework: [
      "Confirm insulation and all in-wall rough-ins are inspected and complete.",
      "Confirm wall-to-exposed-ceiling termination detail with J & J.",
      "Confirm garage fire-separation requirements."
    ],
    completion: [
      "Walls finished Level 4, smooth, and ready for paint.",
      "Garage fire separation complete and inspected.",
      "Exposed-ceiling terminations clean; no damage to exposed structure."
    ]
  },

  // ---------------- 14 EXTERIOR FINISHES ----------------
  {
    num: "14", title: "Exterior Finishes — Metal Cladding",
    subtitle: "Standing-Seam Metal Siding · Fascia · Porch Ceilings",
    overview: "Contractor to furnish and install standing-seam metal wall cladding (factory-finished, no field paint), metal/vinyl fascia, and tongue-and-groove covered-porch ceilings. All cladding is standing-seam metal per the modern design.",
    includes: [
      "Standing-seam metal wall cladding, factory-finished, ≈4,682 SF (incl. waste).",
      "Weather-resistive barrier and all trims, closures, and flashings.",
      "Fascia (metal and vinyl), ≈340 LF.",
      "Tongue-and-groove covered-porch ceilings, ≈382 SF."
    ],
    excludes: [
      "Metal roofing (Scope 08).",
      "Exterior paint — none; cladding is factory-finished.",
      "Windows and exterior doors (Scope 15)."
    ],
    note: "Modern metal cladding is chronically under-budgeted — confirm panel/profile and obtain a quote. Coordinate cladding-to-window/door flashing with Scope 15. Confirm whether porch ceilings are T&G wood or exposed metal soffit per the all-metal aesthetic.",
    codes: [
      "2018 IRC Chapter 7 — Wall Covering (R703)",
      "2018 IRC R703.2 — Water-resistive barrier",
      "Manufacturer installation instructions for standing-seam wall panels",
      `${C} — Housewrap/WRB inspection`
    ],
    prework: [
      "Confirm panel profile, finish color, and trim details with J & J.",
      "Confirm WRB and window/door flashing sequence before cladding.",
      "Confirm porch ceiling material (T&G wood vs. metal soffit)."
    ],
    completion: [
      "Cladding installed plumb, true, and watertight; trims and closures complete.",
      "Fascia straight and continuous; porch ceilings complete.",
      "No oil-canning or finish damage; touch-up per manufacturer."
    ]
  },

  // ---------------- 15 WINDOWS & EXTERIOR DOORS ----------------
  {
    num: "15", title: "Windows & Exterior Doors",
    subtitle: "Black Low-E Windows · Multi-Slide · Entry Doors",
    overview: "Contractor to furnish and install all windows and exterior doors, including a double front entry, hinged exterior doors, and large sliding/multi-slide glass doors. Windows are black-exterior, Low-E, double-pane, no grid (modern). Window/door units are allowances.",
    includes: [
      "24 windows — vinyl single-hung & fixed, black exterior, Low-E double-pane, no grid (allowance).",
      "Window flashing tape and installation labor (24 ea).",
      "Double front entry door + lockset, modern (allowance) + install.",
      "2 single + 2 double exterior doors (black glass) + locksets (allowance) + install.",
      "8' sliding glass door and 12' multi-slide door to rear porch (allowance) + install."
    ],
    excludes: [
      "Interior doors and hardware (Scope 16).",
      "Garage doors (Scope 24).",
      "Metal cladding and exterior trim/flashing integration (coordinate with Scope 14).",
      "Shower/mirror glass (Scope 23)."
    ],
    note: "Confirm exact window count and grade (≈14 plan + ≈10 clerestory band) — do not over-price tall/clerestory windows. Multi-slide door may run $8–12k; confirm the door schedule and unit sizes before ordering.",
    codes: [
      "AAMA 2400 — Window Installation Standard",
      "Georgia Energy Code — Window U-factor & SHGC, Climate Zone 3",
      "2018 IRC R308 — Safety glazing requirements"
    ],
    prework: [
      "Confirm window/door schedule, sizes, swing, and finishes against the plans.",
      "Confirm rough openings with framer (Scope 07).",
      "Coordinate flashing sequence with metal cladding (Scope 14)."
    ],
    completion: [
      "All units installed plumb, level, square; operate smoothly; locked and weather-sealed.",
      "Flashing integrated with WRB/cladding; no leaks.",
      "Energy-rating labels retained for inspection; glazing meets safety requirements."
    ]
  },

  // ---------------- 16 INTERIOR TRIM ----------------
  {
    num: "16", title: "Interior Trim & Carpentry",
    subtitle: "Flat-Stock Trim · Interior Doors · Hardware",
    overview: "Contractor to furnish material and labor for interior finish carpentry: modern flat-stock base and window casing, interior doors and hardware, and trim/hardware installation. J & J furnishes door slabs and hardware allowances; contractor provides installation labor and trim materials as noted.",
    includes: [
      "Modern flat-stock base molding (≈750 LF, allowance) and 1x4 window casing/jambs (≈400 LF).",
      "Trim labor (≈1,200 LF) and quarter-round / bath / door / cabinet hardware install (≈3,841 SF basis).",
      "Hang interior doors: 13 hollow-core 8' + 9 solid-core 8' (bedrooms) + 5 6'8\" hinged + 8' garage entry door.",
      "Install door knobs (28), door stops (28), and door hardware.",
      "Install bath accessories/towel bars and pantry shelving (coordinate)."
    ],
    excludes: [
      "Cabinets (Scope 19) and countertops (Scope 20).",
      "Exterior doors (Scope 15); garage doors (Scope 24).",
      "Painting/finishing of trim (Scope 17)."
    ],
    note: "Modern flat-stock profile — confirm base size and casing detail. Bedrooms get solid-core 8' doors; balance hollow-core flat-stock. Confirm door and hardware counts against the plan.",
    codes: [
      "2018 IRC R311.7 — Stairways (if applicable)",
      "2018 IRC R312 — Guards",
      "2018 IRC R302.5 — Dwelling/garage door opening protection"
    ],
    prework: [
      "Confirm trim profiles, door styles/cores, and hardware finishes with J & J.",
      "Confirm door and casing counts against the plan.",
      "Confirm walls are painted/primed status for install sequence."
    ],
    completion: [
      "All doors hung plumb; operate and latch correctly; hardware set.",
      "Trim tight, mitered clean, and caulk-ready; no gaps.",
      "Accessories and shelving installed level and secure."
    ]
  },

  // ---------------- 17 PAINTING ----------------
  {
    num: "17", title: "Painting & Exposed-Structure Coating",
    subtitle: "Interior Walls · Black Spray-Coat Structure/Duct/Foam",
    overview: "Contractor to furnish all labor and materials to paint interior walls and to spray-coat the exposed ceiling structure, ductwork, and spray-foam insulation BLACK as an industrial finish — including the code-required ignition-barrier coating over exposed foam.",
    includes: [
      "Paint interior walls (≈17,939 SF) — prime + finish coats.",
      "Spray-coat exposed structure / ducts / foam black (≈3,841 SF), including ignition-barrier coating over exposed foam.",
      "Mask and protect floors (stained slab), windows, cabinets, and fixtures.",
      "Caulk and prep trim; final touch-up."
    ],
    excludes: [
      "Exterior finishes — metal cladding is factory-finished (Scope 14).",
      "Concrete floor staining/sealing (Scope 21).",
      "Cabinet and countertop finishing (Scopes 19 / 20)."
    ],
    note: "The black spray-coat over exposed foam must serve as / be compatible with a code-listed ignition barrier — CONFIRM the product and code path with Newton County before spraying. Protect the stained-concrete floor and exposed ductwork finish during all painting.",
    codes: [
      "2018 IRC R316 — Foam plastic ignition/thermal barrier (intumescent coating per listing)",
      "2018 IRC R702 — Interior wall finish",
      "Manufacturer application specifications; low-VOC per Georgia requirements",
      "Coating manufacturer ESR/listing for ignition-barrier use over spray foam"
    ],
    prework: [
      "Confirm wall colors/sheens and the black coating product (ignition-barrier listing).",
      "Confirm drywall is finished and exposed structure/duct is complete and clean.",
      "Protect stained-concrete floors and exposed metal duct before spraying."
    ],
    completion: [
      "Walls uniformly coated, no holidays/lap marks.",
      "Exposed structure/duct/foam fully and evenly coated black; ignition-barrier coverage rate documented.",
      "No overspray on floors, glass, cabinets, or fixtures."
    ]
  },

  // ---------------- 18 TILE ----------------
  {
    num: "18", title: "Tile",
    subtitle: "Kitchen Backsplash · 4 Tiled Baths · Showers",
    overview: "Contractor to furnish labor and material allowances to install all tile: kitchen backsplash and fully-tiled bath walls, showers (mud beds, benches, niches, Schluter), and bath floors across all 4 baths. Tile material is owner allowance; labor and sundries by contractor.",
    includes: [
      "Kitchen backsplash — tile + sundries + labor (≈45–50 SF).",
      "Bath 1 (master): tile walls + Schluter + shower mud bed, bench, niche + floor tile.",
      "Baths 2–4: tile walls, shower mud beds, shower floor tile, floor tile.",
      "All thinset, grout, spacers, sealers, and waterproofing membrane.",
      "Waterproof and slope all shower pans per code."
    ],
    excludes: [
      "Stained-concrete main floors (Scope 21).",
      "Plumbing fixtures, valves, and drains (Scope 09).",
      "Shower glass enclosures and mirrors (Scope 23).",
      "Vanity cabinets and tops (Scopes 19 / 20)."
    ],
    note: "Finish tier is HIGH-END (fully-tiled showers, benches, niches). Confirm tile selections, layout, and grout colors before starting. Coordinate shower pan waterproofing with plumbing valve/drain rough-in.",
    codes: [
      "ANSI A108 — Ceramic Tile Installation",
      "TCNA Handbook for Ceramic, Glass, and Stone Tile Installation",
      "ANSI A118.10 — Waterproof membranes"
    ],
    prework: [
      "Confirm tile selections, layouts, niches, and bench locations with J & J/owner.",
      "Confirm shower valve/drain rough-in is set and inspected (Scope 09).",
      "Confirm wall substrate (cement board/membrane) at wet areas."
    ],
    completion: [
      "All showers flood-tested watertight before tile where applicable.",
      "Tile flat, aligned, full-coverage thinset; grout uniform and sealed.",
      "Niches, benches, and Schluter edges clean and square."
    ]
  },

  // ---------------- 19 CABINETS ----------------
  {
    num: "19", title: "Cabinetry",
    subtitle: "Kitchen · 4 Vanities · Supply & Install",
    overview: "Contractor to furnish and install high-end cabinetry: kitchen lowers/uppers/island/tall units/vent-hood cabinet and vanity cabinets for all 4 baths, including hardware and installation labor. Cabinet and vanity material are owner allowances.",
    includes: [
      "Kitchen: 20 LF lowers, 12 LF uppers, 10 LF island, 6 LF tall (fridge/oven/linen), vent-hood cabinet (allowance).",
      "Laundry/utility: lowers (12 LF) + uppers (10 LF) + counter.",
      "Vanity cabinets baths 1–4 + cabinet hardware (allowance).",
      "Labor to assemble and install all cabinets and vanities; install towel bars."
    ],
    excludes: [
      "Countertops (Scope 20).",
      "Plumbing fixtures/faucets (Scope 09); mirrors (Scope 23).",
      "Appliances and appliance install (by others / owner-supplied)."
    ],
    note: "High-end cabinetry allowance ($200/LF kitchen). Confirm door style, finish, and box construction. Coordinate vent-hood cabinet with kitchen appliance/hood selection and HVAC.",
    codes: [
      "ANSI/KCMA A161.1 — Cabinet standards",
      "CARB ATCM 93120 — Formaldehyde emissions compliance"
    ],
    prework: [
      "Confirm cabinet layout, sizes, door style, and finish against the plan/selections.",
      "Confirm appliance and fixture dimensions before setting cabinets.",
      "Confirm walls/floors are complete (stained slab protected)."
    ],
    completion: [
      "Cabinets level, plumb, securely fastened; doors/drawers aligned.",
      "Hardware installed; fillers and scribes clean.",
      "Ready to template for countertops (Scope 20)."
    ]
  },

  // ---------------- 20 COUNTERTOPS ----------------
  {
    num: "20", title: "Countertops",
    subtitle: "Level-6 Quartz / Granite · Kitchen & Baths",
    overview: "Contractor to template, fabricate, and install Level-6 granite/quartz (or concrete) countertops at the kitchen and all 4 bath vanities, including cutouts and edge profiles. Countertop material is owner allowance.",
    includes: [
      "Kitchen countertops — Level-6 granite/quartz, ≈80 SF (allowance) + cutouts.",
      "Bath 1–4 vanity tops — Level-6 quartz, ≈14–32 SF each (allowance) + cutouts.",
      "Template, fabricate, deliver, and install; seam and seal.",
      "Sink/faucet cutouts coordinated with plumbing (Scope 09)."
    ],
    excludes: [
      "Cabinets and vanities (Scope 19).",
      "Sinks, faucets, and plumbing connections (Scope 09).",
      "Backsplash tile (Scope 18)."
    ],
    note: "High-end finish tier — confirm slab material, color, edge profile, and seam locations before fabrication. Template only after cabinets are set and verified level.",
    codes: [
      "MIA Dimension Stone Design Manual",
      "ANSI/NSF 51 — Food equipment materials"
    ],
    prework: [
      "Confirm material, color, edge profile, and overhangs with J & J/owner.",
      "Confirm cabinets are set and level before templating.",
      "Confirm sink/faucet/cooktop cutout specs with plumbing/appliances."
    ],
    completion: [
      "Tops installed level, fully supported; seams tight and inconspicuous.",
      "Cutouts accurate; edges polished per spec; sealed if natural stone.",
      "No chips or scratches; cleaned and protected."
    ]
  },

  // ---------------- 21 FLOORING ----------------
  {
    num: "21", title: "Flooring — Stained & Sealed Concrete",
    subtitle: "Polished/Stained Slab · Finished Floor Throughout",
    overview: "Contractor to grind, stain, and seal the concrete slab as the finished floor throughout the living areas (≈3,631 SF). The slab IS the finish floor per the design — no LVP or wood. High-end grind/stain/seal.",
    includes: [
      "Surface prep/grind of slab to receive stain.",
      "Stain and seal concrete floors, ≈3,631 SF.",
      "Multiple seal/wear coats per specification.",
      "Mask and protect walls, cabinets, and adjacent finishes."
    ],
    excludes: [
      "Slab placement and finishing (Scope 05).",
      "Bath floor tile (Scope 18).",
      "Wall painting (Scope 17)."
    ],
    note: "Confirm finish (stain color vs. polish) and sheen with owner. Slab finish from Scope 05 must be clean and crack-controlled — coordinate timing so the finished floor is protected through the balance of construction.",
    codes: [
      "ASTM F2170 — RH testing in concrete slabs",
      "ASTM F1869 — Moisture vapor emission rate",
      "Stain/sealer manufacturer installation specifications"
    ],
    prework: [
      "Confirm stain color, sheen, and sealer system with J & J/owner.",
      "Confirm slab moisture is within sealer tolerances (test).",
      "Confirm slab is clean and free of defects before grinding."
    ],
    completion: [
      "Floors uniformly stained and sealed; consistent color/sheen.",
      "No roller/lap marks, bubbles, or contamination.",
      "Floor protected from subsequent trades until handover."
    ]
  },

  // ---------------- 22 MASONRY ----------------
  {
    num: "22", title: "Masonry — Stone Veneer",
    subtitle: "Adhered Stone Accent Wall",
    overview: "Contractor to furnish and install adhered stone veneer at the accent wall (≈282 SF), including substrate prep, lath, scratch coat, setting bed, and grouting/pointing as the selected stone requires.",
    includes: [
      "Furnish stone veneer material, ≈282 SF (allowance).",
      "Install lath, weather-resistive barrier, scratch coat as required.",
      "Set stone veneer; point/grout joints per stone type.",
      "Clean and seal as specified."
    ],
    excludes: [
      "Fireplace and chimney (none on this project).",
      "Metal cladding and other exterior finishes (Scope 14).",
      "Framing/substrate (Scope 07)."
    ],
    note: "Confirm exact location (entry accent wall) and stone selection. Confirm whether veneer is interior or exterior to set the correct WRB/flashing detail. Carried as a stone-veneer accent only — no fireplace.",
    codes: [
      "2018 IRC R703.12 — Adhered masonry veneer",
      "TMS 402/602 — Building Code Requirements & Specification for Masonry Structures",
      "ASTM C1670 — Adhered manufactured stone masonry veneer units"
    ],
    prework: [
      "Confirm stone selection, location, and extent with J & J/owner.",
      "Confirm substrate and WRB/flashing detail (interior vs. exterior).",
      "Confirm framing/blocking is adequate for veneer weight."
    ],
    completion: [
      "Veneer fully bonded; no loose units; joints pointed clean.",
      "WRB/flashing intact behind veneer (if exterior).",
      "Sealed and cleaned per spec; no staining of adjacent finishes."
    ]
  },

  // ---------------- 23 GLASS ----------------
  {
    num: "23", title: "Glass & Shower Enclosures",
    subtitle: "Frameless Shower Glass · Vanity Mirrors",
    overview: "Contractor to furnish and install frameless glass shower enclosures and vanity mirrors at all baths. Master and additional showers receive frameless tempered-glass enclosures; each vanity receives a mirror.",
    includes: [
      "2 frameless glass shower enclosures (allowance), tempered safety glass.",
      "Vanity mirrors: 2 at bath 1, 1 each at baths 2–4 (allowance) + installation.",
      "All clips, hinges, channels, and sealant.",
      "Measure after tile is complete (Scope 18)."
    ],
    excludes: [
      "Tile and shower pans (Scope 18).",
      "Plumbing fixtures and valves (Scope 09).",
      "Windows and exterior glass doors (Scope 15)."
    ],
    note: "Field-measure frameless enclosures only AFTER tile is complete and verified plumb. All glass must be tempered safety glass per code.",
    codes: [
      "2018 IRC R308 — Safety glazing (hazardous locations)",
      "ANSI Z97.1 — Safety glazing materials",
      "CPSC 16 CFR 1201 — Safety standard for architectural glazing"
    ],
    prework: [
      "Confirm enclosure configurations and hardware finishes with J & J/owner.",
      "Confirm tile walls/curbs are complete, plumb, and waterproof before measuring.",
      "Confirm mirror sizes and locations against vanities."
    ],
    completion: [
      "Enclosures installed plumb; doors swing/seal correctly; no leaks.",
      "All glass tempered and labeled; clips/sealant clean.",
      "Mirrors level and securely mounted."
    ]
  },

  // ---------------- 24 GARAGE DOORS ----------------
  {
    num: "24", title: "Garage Doors",
    subtitle: "Modern Flush 16'x8' · Opener",
    overview: "Contractor to furnish and install a modern flush 16'x8' double garage door with opener at the conditioned garage, including tracks, springs, weatherstripping, and operator.",
    includes: [
      "Modern flush 16'x8' double garage door (allowance).",
      "Garage door opener (allowance) + installation.",
      "Tracks, springs, hardware, and weatherstripping.",
      "Test and adjust operation and safety reverse."
    ],
    excludes: [
      "Garage entry (man) door (Scope 16).",
      "Electrical outlet/wiring for opener (Scope 11).",
      "Garage HVAC (Scope 10)."
    ],
    note: "Garage is conditioned — confirm insulated door and weatherstripping for the conditioned space. Confirm flush modern panel style and color.",
    codes: [
      "UL 325 — Door operators (entrapment protection)",
      "ANSI/DASMA 102 — Sectional Doors",
      "2018 IRC R309 — Garages"
    ],
    prework: [
      "Confirm door style, color, insulation value, and opener with J & J/owner.",
      "Confirm rough opening and headroom with framing.",
      "Confirm opener power/outlet is available (Scope 11)."
    ],
    completion: [
      "Door operates smoothly; balanced springs; weatherseal complete.",
      "Opener safety reverse and photo-eyes functional.",
      "No damage to finish; remotes/keypads provided."
    ]
  },

  // ---------------- 26B DRIVEWAY ----------------
  {
    num: "26B", title: "Driveway & Concrete Walkways",
    subtitle: "End-of-Job · 4\" Concrete Drive",
    overview: "Contractor to furnish all labor, equipment, and materials for the final concrete driveway and walkways (≈2,400 SF, 4\" slab). End-of-job scope performed after exterior work is complete to avoid construction damage.",
    includes: [
      "Fine-grade and prep drive/walk subgrade.",
      "Form, place, and finish 4\" concrete driveway and walkways (≈2,400 SF; ≈46 CY).",
      "Labor & equipment for placement and finishing.",
      "Control joints, broom/finish per spec, and cure."
    ],
    excludes: [
      "Construction gravel drive and culvert (Scope 01).",
      "Final grading, sod, and landscaping (Scope 27).",
      "Building slab (Scope 05)."
    ],
    note: "Drive length (~110 LF) and area were estimated and must be FIELD-CONFIRMED before pour. GDOT/county driveway entrance requirements apply at the county road. End-of-job scope — schedule after exterior trades are complete.",
    codes: [
      "ACI 302.1R — Guide for Concrete Floor and Slab Construction",
      "2018 IRC R301.1 — Application of design criteria",
      "GDOT driveway entrance requirements at county road",
      `${C} — Driveway permit requirements (if applicable)`
    ],
    prework: [
      "Field-verify drive layout, length, width, and grade with J & J.",
      "Confirm entrance/culvert and county driveway permit requirements.",
      "Confirm exterior work is complete to avoid damaging finished drive."
    ],
    completion: [
      "Drive/walks placed to correct grade; positive drainage away from structure.",
      "Control joints cut; finish uniform; no cracking/spalling.",
      "Cured and protected; entrance meets county/GDOT requirements."
    ]
  },

  // ---------------- 27 LANDSCAPING ----------------
  {
    num: "27", title: "Landscaping",
    subtitle: "Final Grade · Sod · Irrigation · Plants",
    overview: "Contractor to furnish all labor, equipment, and materials for final grading, backfill, lawn establishment (sod/seed), irrigation, and a landscape plant package, achieving final site stabilization.",
    includes: [
      "Final grading around structure (positive drainage away from foundation).",
      "Backfill dirt as needed (≈3 loads, allowance).",
      "Sod / lawn establishment (allowance) and seed & straw on balance.",
      "Irrigation system (allowance) with backflow preventer.",
      "Landscape plant package (allowance)."
    ],
    excludes: [
      "Concrete driveway and walkways (Scope 26B).",
      "Erosion control during construction (Scope 01).",
      "Septic field final grade (Scope 02)."
    ],
    note: "Confirm scope, plant package, and irrigation extent with owner. Achieve final site stabilization per Georgia EPD before NOT (Notice of Termination).",
    codes: [
      "Georgia EPD — Final site stabilization requirements",
      `${C} — Irrigation backflow preventer inspection`
    ],
    prework: [
      "Confirm final grade plan and drainage with J & J.",
      "Confirm plant package, sod type, and irrigation zones with owner.",
      "Confirm hardscape (Scope 26B) is complete."
    ],
    completion: [
      "Final grade drains away from foundation; no ponding.",
      "Sod/seed established; irrigation operational; backflow inspected.",
      "Site stabilized per EPD; ready for NOT."
    ]
  },

  // ---------------- 28A FINAL CLEAN ----------------
  {
    num: "28A", title: "Final Clean — Interior",
    subtitle: "End-of-Job · Whole-House Detail Clean",
    overview: "Contractor to perform a complete interior final clean of the residence (≈2,637 SF heated) prior to the owner walkthrough — all interior surfaces detailed and move-in ready. All trades must be complete and off-site before cleaning begins.",
    includes: [
      "Clean all floors (stained concrete + tile), baseboards, and trim.",
      "Clean countertops, cabinets (inside and out), and all fixtures.",
      "Clean all bathroom surfaces, mirrors, and glass enclosures.",
      "Clean light fixtures, switch plates, and interior of windows.",
      "Remove all construction dust, debris, stickers, and protective films."
    ],
    excludes: [
      "Exterior surfaces and pressure washing (Scope 28C).",
      "Exterior window glass (Scope 28B).",
      "Touch-up painting (Scope 17) and punch repairs (builder)."
    ],
    note: "Use non-damaging agents on the stained-concrete floor and exposed-metal duct/structure. No construction activity after final clean without J & J approval.",
    codes: [
      "OSHA 29 CFR 1926.57 — Ventilation during cleaning operations",
      "EPA 40 CFR Part 745 — Lead RRP awareness (new-construction reference)",
      "Contractor must use non-damaging cleaning agents on all finished surfaces"
    ],
    prework: [
      "Confirm all trades are complete and off-site.",
      "Confirm finished floor and exposed structure cleaning agents are non-damaging.",
      "Confirm walkthrough date with J & J."
    ],
    completion: [
      "All interior surfaces clean, streak-free, and move-in ready.",
      "No dust on exposed structure/duct, ledges, or fixtures.",
      "Passes J & J pre-walkthrough inspection."
    ]
  },

  // ---------------- 28B WINDOW CLEANING ----------------
  {
    num: "28B", title: "Window Cleaning",
    subtitle: "End-of-Job · Interior & Exterior Glass",
    overview: "Contractor to clean all window and glass-door glass, interior and exterior (24 windows plus exterior glass doors), removing all construction film, labels, and overspray, and to clean and reinstall screens.",
    includes: [
      "Clean interior and exterior glass of all 24 windows.",
      "Clean exterior glass doors and sliding/multi-slide glass.",
      "Remove stickers, labels, paint overspray, and construction film.",
      "Clean and reinstall all screens."
    ],
    excludes: [
      "Interior surface cleaning (Scope 28A).",
      "Exterior pressure washing (Scope 28C).",
      "Glazing repair/replacement (builder/Scope 15)."
    ],
    note: "All glass is Low-E safety glass — do NOT use abrasive tools or scrapers that scratch coatings. Use non-streaking products and follow ladder/lift safety.",
    codes: [
      "Contractor must use non-abrasive, non-streaking window cleaning products",
      "All glass is safety glass per 2018 IRC R308 — do not use abrasive tools",
      "OSHA 29 CFR 1926 Subpart R — ladder and lift access safety"
    ],
    prework: [
      "Confirm all trades complete; no further overspray expected.",
      "Confirm safe ladder/lift access for clerestory/high glass.",
      "Confirm Low-E coating cleaning method."
    ],
    completion: [
      "All glass clean and streak-free, interior and exterior.",
      "No scratches to Low-E coatings; labels/film removed.",
      "Screens cleaned and reinstalled."
    ]
  },

  // ---------------- 28C PRESSURE WASH ----------------
  {
    num: "28C", title: "Exterior Pressure Washing",
    subtitle: "End-of-Job · Cladding · Porches · Flatwork",
    overview: "Contractor to pressure wash all exterior surfaces — metal cladding, stone veneer, porches, walks, and driveway — using appropriate pressure for each material, prior to owner walkthrough.",
    includes: [
      "Pressure wash metal cladding and fascia (lower pressure for finish).",
      "Pressure wash stone veneer, covered porches, walks, and driveway.",
      "Remove construction dirt, splatter, and residue.",
      "Protect electrical fixtures, outlets, and vents from water intrusion."
    ],
    excludes: [
      "Interior cleaning (Scope 28A) and window glass (Scope 28B).",
      "Touch-up to cladding finish (Scope 14)."
    ],
    note: "Use the correct PSI per surface — factory-finished metal cladding requires lower pressure than concrete. Protect all electrical fixtures, outlets, and vents; contain wash water away from drainage features per EPD.",
    codes: [
      "OSHA 29 CFR 1910.137 — Electrical safety during pressure washing near fixtures",
      "Manufacturer guidelines for pressure ratings on siding, masonry, and trim",
      "Georgia EPD — Stormwater runoff; contain and direct wash water away from drainage"
    ],
    prework: [
      "Confirm correct PSI per surface (cladding vs. concrete).",
      "Protect electrical fixtures, outlets, and vents.",
      "Confirm all exterior trades are complete."
    ],
    completion: [
      "All exterior surfaces clean; no finish damage or oil-canning.",
      "No water intrusion at fixtures/vents.",
      "Site presentable for owner walkthrough."
    ]
  }

  ];
};
