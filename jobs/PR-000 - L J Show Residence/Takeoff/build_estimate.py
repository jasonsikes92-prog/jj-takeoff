# -*- coding: utf-8 -*-
import sys, json, math, collections
sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J

RB = json.load(open(r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\reference\rate_book.json'))
LINES = RB['lines']

# ================= MEASURED TAKEOFF =================
HEATED = 3245.7; GARAGE = 1038.5; REARP = 1168.8; FRONTP = 76.8
UNDER = HEATED + GARAGE + REARP + FRONTP          # 5529.8
COVERED = REARP + FRONTP                          # 1245.6
SLAB = UNDER
ROOF_FP = 6159.0; ROOF_PERIM = 402.0
SHINGLE_SURF = 4859.7; METAL_SURF = 1822.5
LAP = 1658.0; BNB = 3318.0; STONE = 562.0
FASCIA = 456.2; CORNER_LF = 354.0; WINTRIM = 310.0
DRY_WALLS = 15881.0; DRY_CEIL = 4284.2
WINDOWS = 22; INT_DOORS = 27; EXT_DOORS = 8; GAR_DOORS = 3
CANS = 59; ELEC_SF = HEATED + GARAGE
FULL_BATH = 5; HALF_BATH = 1
HVAC_UNITS = 1
WALL_INSUL = 4292.0; ROOF_SURF = 6682.2
BASE_LF = 1527.0
W = {'concrete': .10, 'siding': .10, 'shingle': .15, 'metal': .15,
     'drywall': .10, 'insul': .10}

Q = {}
def q(name, group, qty, note=''):
    Q[(name, group)] = (round(float(qty), 2), note)

# --- General requirements / site
q('Plan Design', 'General Requirements', 1)
q('Engineering Services', 'General Requirements', 1)
q('Blueprint Copies', 'General Requirements', 6)
q('Boundary Survey', 'General Requirements', 1)
q('Erosion Control Plan', 'General Requirements', 1)
q('Building Permits', 'General Requirements', round(HEATED + GARAGE / 2, 0), 'heated + 1/2 garage')
q('Temporary Toilets', 'General Requirements', 10, '10-month build')
q('Temporary Utilities (Electric, Water, Gas)', 'General Requirements', 10)
q('Temporary Erosion Control', 'Clearing and Grading', 900, 'ASSUMED - no site plan')
q('Temporary Dumpster Rental or Debris Removal', 'Clearing and Grading', 6, 'ASSUMED')
q('Grubbing and mulching', 'Clearing and Grading', 3, 'ASSUMED days')
q('Lot Clearing & Excavation', 'Clearing and Grading', 4, 'ASSUMED days')
q('Concrete wash out pit', 'Clearing and Grading', 1)
q('#34 Gravel to house site - 12\u0027 wide', 'Construction Drive', 3600, 'ASSUMED 300 LF - no site plan')
q('Culvert Pipe', 'Construction Drive', 1)
q('Well - 300 FT depth', 'Water', 1)
q('Electrical for well', 'Water', 150, 'ASSUMED distance')
q('Water: Water Softener & Filtration System', 'Water', 1)
q('Sewer: Septic System, Plan, & Permit', 'Sewage', 1)
q('Gas: Propane Tank (500 Gallon)', 'Gas/Propane', 1)
q('Bury Propane tank', 'Gas/Propane', 1)

# --- Foundation: MONOLITHIC SLAB (Jason confirmed) -- thickened edge, NO footer labour
q('Concrete- 4 inches - Slab', 'Concrete Slab 4"', SLAB * (4 / 12) / 27 * 1.10, '4in over %.0f SF +10%%' % SLAB)
q('Labor - Monolithic slab', 'Concrete Slab 4"', SLAB)
q('Wire Mesh - Slab', 'Concrete Slab 4"', math.ceil(SLAB / 750))
q('Mesh Chairs 100 pack - Slab', 'Concrete Slab 4"', math.ceil(SLAB / 400))
q('Vapor Barrier - Slab', 'Concrete Slab 4"', math.ceil(SLAB / 1000))
q('1/2" Gravel - Slab', 'Concrete Slab 4"', math.ceil(SLAB * 0.33 / 27 / 18))
q('Pump Truck - Slab pour', 'Concrete Slab 4"', 1)
q('Concrete - Grade Beams', 'Grade Beams', 387.69 * 1.0 * 1.5 / 27 * 1.10, 'thickened edge 387.7 LF')
q('#4 Rebar 20\u0027 - Grade Beams', 'Grade Beams', math.ceil(387.69 * 2 / 20), '2 bars continuous, 20-ft sticks')

# --- MONO-SLAB FOOTER (Jason standing rules 7/31/26):
#   * footer LF = whole-slab OUTER perimeter + every internal STEP line, each counted ONCE
#     (all one pour, but garage + porch slabs step down so those transitions get a turndown)
#   * ALWAYS assume a 16x18 footer unless Jason specifies otherwise
#   * ALWAYS assume 3 sticks of rebar (3 bars continuous)
#   * MATERIAL only -- no footer labour (that sits in 'Labor - Monolithic slab' $/SF)
FOOTER_LF   = 394.32 + 75.42 + 100.33 + 25.81      # outer + garage/rear-porch/front-porch steps
FOOTER_CY_LF = (16 * 18 / 144.0) / 27.0            # 16x18 section = 0.07407 CY/LF
q('Form Boards - Footer', 'Footers 16x18', FOOTER_LF,
  'whole-slab outer perimeter 394.32 + garage step 75.42 + rear porch 100.33 + front porch 25.81')
q('Concrete - Footer', 'Footers 16x18', FOOTER_LF * FOOTER_CY_LF * 1.10, '16x18 footer +10%')
q('#4 Rebar 20" Sticks - Footer', 'Footers 16x18', math.ceil(FOOTER_LF * 3 / 20 * 1.10),
  '3 bars continuous, 20-ft sticks, +10%')

# --- Framing = TOTAL UNDER ROOF
q('Framing Lumber', 'Framing', UNDER)
q('Framing Labor - SF Price', 'Framing', UNDER)

# --- Roofing: shingle 6:12 only; metal on the low-slope planes
q('Shingle Roof - Turnkey', 'Roofing', SHINGLE_SURF * (1 + W['shingle']), '6:12 surface +15%')
q('Metal Roofing - Standing Seam', 'Roofing', METAL_SURF * (1 + W['metal']), 'low-slope planes +15%')

# --- Windows and doors
q('Windows', 'Windows', WINDOWS)
q('Windows - Labor to Install', 'Windows', WINDOWS)
q('Window Tape', 'Windows', math.ceil(WINTRIM / 100))
q('Front Door - Double (Wood Door)', 'Front Door', 1)
q('Front Door - Lockset', 'Front Door', 1)
q('Front Door - Labor to install Door', 'Front Door', 1)
q('Front Door - Lockset installation', 'Front Door', 1)
q('Exterior Doors - Single Door', 'Other Exterior Doors', 4)
q('Exterior Doors - Double Door', 'Other Exterior Doors', 4)
q('Exterior Door Lockset', 'Other Exterior Doors', EXT_DOORS)
q('Exterior Doors - Labor to Install Hinged doors', 'Other Exterior Doors', EXT_DOORS)
q('Exterior Doors Lockset Installation', 'Other Exterior Doors', EXT_DOORS)
q('8\u00270" Single', '8\u0027 Doors - Solid', INT_DOORS)
q('Door knobs', 'Attic doors and Knobs', INT_DOORS)
q('Door Stops', 'Attic doors and Knobs', INT_DOORS)
q('Interior Door Hardware Installation', 'Attic doors and Knobs', INT_DOORS)
q('Attic Pulldown Staircase', 'Attic doors and Knobs', 1)

# --- Insulation: FULL SPRAY FOAM envelope (Jason)
q('Insulation - Spray Foam Roof Deck', 'Insulation', ROOF_SURF * (1 + W['insul']))
q('Insulation - Spray Foam Walls', 'Insulation', WALL_INSUL * (1 + W['insul']))

# --- Drywall V3 (net measured x 1.10 at $1.44)
q('Drywall - Level 4', 'Drywall', (DRY_WALLS + DRY_CEIL) * (1 + W['drywall']), 'net %.0f SF +10%%' % (DRY_WALLS + DRY_CEIL))

# --- Cladding measured per elevation
q('Siding (Vertical)', 'Siding', BNB * (1 + W['siding']), 'B&B measured per elevation')
q('Siding (Fiber Cement, Horizontal)', 'Siding', LAP * (1 + W['siding']), 'lap measured per elevation')
q('Corner Boards', 'Siding', CORNER_LF)
q('1x4 Around Windows', 'Siding', WINTRIM)
q('Freize at roof', 'Siding', FASCIA)
q('Flashing / Water Table', 'Siding', 173.0, 'stone-to-siding transition')
q('Garage Wrap', 'Siding', GAR_DOORS)
q('Gable Brackets', 'Siding', 13, 'one per measured gable')
q('Fascia (Metal and Vinyl)', 'Siding for Eaves / Cornice', FASCIA)
q('Porch Ceilings', 'Siding for Eaves / Cornice', COVERED * (1 + W['siding']), 'T&G both covered porches')
q('Wrap Porch Beams', 'Siding for Eaves / Cornice', 121.0, 'porch open edge')
q('Column Wrap 12x12 (cedar)', 'Siding for Eaves / Cornice', 10, 'ASSUMED count')
q('Stone Material', 'Stone', STONE * (1 + W['siding']))
q('Stone Labor', 'Stone', STONE * (1 + W['siding']))

# --- Plumbing / HVAC / Electrical
q('Plumbing - Base Contract (rough-in + set)', 'Plumbing', 1)
q('Count Each Fixture Opening', 'Plumbing', FULL_BATH * 3 + HALF_BATH * 2 + 3)
q('Count Each Water Opening', 'Plumbing', FULL_BATH * 3 + HALF_BATH * 1 + 3)
q('Water Heater', 'Plumbing', 2)
q('HVAC - Air Handler and Condensing Units', 'Mechanical / HVAC', HVAC_UNITS, '3,246 htd / 800 = 4.06 t -> ONE unit')
q('Flex Duct work', 'Mechanical / HVAC', HEATED)
q('Blower Door / HERS Test', 'Mechanical / HVAC', 1)
q('Gas Lines', 'Mechanical / HVAC', 3)
q('Electrical - SF Price', 'Electrical', ELEC_SF)
q('Upgrade to 400 AMP service', 'Electrical', 1)
q('Electrical - Permanent Power Connection', 'Electrical', 300, 'ASSUMED - no site plan')
q('Exterior Light Fixtures - Allowance', 'Audio & Security', 18)

# --- Trim / interior carpentry
q('Trim Labor', 'Trim Material', ELEC_SF, '(heated+garage) SF x $2')
q('Base molding - Choose size', 'Trim Material', BASE_LF, 'room perimeter measured')
q('Trim - 1x4 Window casing and Jambs', 'Trim Material', WINTRIM)
q('Mudroom Built-ins / Drop Zone - Allowance', 'Trim Material', 12)
q('Fireplace - Allowance', 'Fireplace', 1)
q('Mantle', 'Fireplace', 1)
q('Hearth Top', 'Fireplace', 12)
q('Surround material', 'Surround', 60)
q('Surround labor to install', 'Surround', 60)

# --- Cabinets / kitchen (measured off E5-E8)
q('LF of Lowers - Kitchen', 'Cabinets', 24)
q('LF of Uppers  - Kitchen', 'Cabinets', 18)
q('LF of Island  - Kitchen', 'Cabinets', 12)
q('LF of Tall Cabinet (Fridge, Oven, Linen)  - Kitchen', 'Cabinets', 8)
q('Each Vent Hood Cabinet  - Kitchen', 'Cabinets', 1)
q('Labor to assemble and install cabinets  - Kitchen', 'Cabinets', 62)
q('Granite or Quartz  - Kitchen', 'Cabinets', 96)
q('Backsplash - Material allowance', 'Backsplash - Material allowance', 72)
q('Backsplash - Tile labor', 'Backsplash - Material allowance', 72)
q('Appliance Package  - Kitchen', 'Appliances', 1)
q('Appliance Installation  - Kitchen', 'Appliances', 1)
q('Kitchen Sink - Farm Sink', 'Kitchen Sink - Farm Sink', 1)
q('Kitchen Sink - Faucet', 'Kitchen Sink - Farm Sink', 1)
q('LF of Lowers', 'Cabinets Pantry', 10)
q('LF of Uppers', 'Cabinets Pantry', 10)
q('Countertops', 'Cabinets Pantry', 22)
q('Labor to assemble and install cabinets', 'Cabinets Pantry', 20)
q('Shelving - Pantry', 'Cabinets Pantry', 24)

json.dump({'%s||%s' % k: v for k, v in Q.items()}, open('quantities.json', 'w'), indent=1)

# ---- match to rate book
matched = []
unmatched = []
idx = {}
for i, l in enumerate(LINES):
    idx.setdefault((str(l.get('name', '')).strip(), str(l.get('group', '')).strip()), []).append(i)
for (nm, gp), (qty, note) in Q.items():
    key = (nm.strip(), gp.strip())
    if key in idx:
        matched.append((idx[key][0], qty, note))
    else:
        cand = [i for i, l in enumerate(LINES)
                if str(l.get('name', '')).strip().lower() == nm.strip().lower()
                and str(l.get('group', '')).strip().lower() == gp.strip().lower()]
        if cand:
            matched.append((cand[0], qty, note))
        else:
            unmatched.append((nm, gp, qty))
print('MATCHED %d   UNMATCHED %d' % (len(matched), len(unmatched)))
for u in unmatched:
    print('   NO MATCH:', u)
json.dump([[i, qy, nt] for i, qy, nt in matched], open('matched.json', 'w'), indent=1)
