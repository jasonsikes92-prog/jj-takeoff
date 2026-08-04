# -*- coding: utf-8 -*-
import openpyxl, datetime, pickle
SRC=r"C:\Users\jason\.claude\skills\jnj-estimate-takeoff\templates\estimate-template.xlsx"
wb=openpyxl.load_workbook(SRC)
ws=wb["Estimate"]

# ---- Geometry (measured) ----
HEATED=2637; GARAGE=1204; FPORCH=77; RPORCH=270; PORCH=FPORCH+RPORCH
UNDER_ROOF=HEATED+GARAGE+PORCH      # 4188
ROOF=4850; WALL_AREA=3074; CLAD=2800; HG=HEATED+GARAGE  # 3841
PERIM=340; BATH_FLR=210; STAINED=HG-BATH_FLR  # 3631
BAKE=0.1211
TODAY=datetime.date.today().isoformat()

F={}
def f(r,q,h=None,note="",desc=None): F[r]=(q,h,note,desc)

# INPUTS
f(3,10,None,"Std 10-mo build (Jason)")
f(5,HEATED,None,"Sheet 1/3 AREAS: 1st-floor living")
f(8,GARAGE,None,"Sheet 1/3 AREAS: garage (CONDITIONED)")
f(9,PORCH,None,"Front porch 77 (schedule) + rear covered porch ~270 (roof-plan backout)")
f(10,UNDER_ROOF,None,"Total under roof = heated+garage+covered porches")
# GENERAL REQUIREMENTS
f(14,1,None,"Plan design")
f(15,1,2500,"Engineering - modern w/ I-joist roof & big openings (bumped)")
f(16,1,None,"Blueprint copies")
f(17,1,None,"Boundary survey")
f(18,1,None,"Erosion control plan (Newton Co)")
f(19,HEATED+GARAGE*0.5,2.0,"Permit = (heated + 1/2 garage) x $2.0/SF. NEWTON CO - FLAG: pre-qualify actual","JJCH cannot be sure on exact permit costs, so this is an allowance. Anything above estimated will be billed at cost plus 20% via a change order.")
f(20,10,None,"Temp toilet 1/mo x10")
f(21,10,None,"Temp utilities 1/mo x10")
# SITE WORK - pasture, minimal
f(24,750,None,"Silt fence = disturbed-area perimeter. Pasture. FLAG measure")
f(26,1,None,"Grubbing/mulch - pasture light")
f(27,2,None,"Topsoil strip + house-pad cut 2 days (pasture, NO demo) - Excavation code")
f(28,1,None,"Concrete washout pit")
f(30,1,None,"Driveway entrance culvert at Meadow View")
f(31,110,None,"Construction drive mat ~110 LF")
f(32,110*12,0.80,"Construction drive #34 gravel 110LF x12' x$0.80/SF")
# UTILITIES
f(35,1,3800,"Public water: tap 8in main on Meadow View + meter. FLAG Newton tap fee","Connection to public water main, meter and tap fee. Allowance - billed at cost.")
f(40,1,13000,"Septic system+plan+permit - 4-bath new lot, likely engineered (bumped). FLAG get quote","Septic system installed by a GA licensed septic contractor, per Newton County specs. Allowance.")
f(46,1,7500,"1,000-gal buried propane tank allowance (Jason)","1,000-gallon buried propane tank - allowance.")
f(47,1,None,"Bury propane tank + line")
# FOUNDATION - monolithic slab
f(80,8,None,"Mesh chairs - slab")
f(81,58,185,"Flat mono-slab field concrete = 3,841 SF x0.0151 = 58 cu yd (thickened-edge concrete carried separately on line 52)")
f(83,HG,None,"Mono slab labor 3,841 SF")
f(84,2,None,"Pump truck - 2 pours")
f(85,6,None,"Vapor barrier rolls under slab")
f(86,6,None,"1/2in gravel base loads under slab")
# FRAMING
f(99,UNDER_ROOF,4.5,"Wall framing lumber (2x6, plates, LVL/steel at big openings). VOLATILE - date-stamped "+TODAY+", get quote")
f(100,ROOF,6.0,"I-JOIST ROOF as engineered floor (material) = roof area 4,850 SF @ $6 (low-slope open-span)")
f(101,UNDER_ROOF,5.5,"Framing labor (walls + set I-joist roof) on total-under-roof")
# ROOFING
f(104,ROOF,11.0,"Standing-seam METAL roof low-slope (1/2:12 & 1:12) mechanically-seamed @ $11/SF turnkey. FLAG roofer quote","Standing-seam metal roof, low-slope, mechanically-seamed, turnkey installed.")
# WINDOWS
f(110,24,625,"~24 window openings (plan 14 + clerestory band ~10). FLAG exact count","Vinyl single-hung & fixed windows, black exterior, Low-E double-pane, no grid (modern).")
f(111,8,None,"Window tape rolls")
f(112,24,None,"Window install labor")
# FRONT DOOR
f(115,1,None,"Double entry door. FLAG modern glass/pivot option","Double entry door, modern.")
f(118,1,None,"Front door lockset"); f(119,1,None,"Front door install"); f(120,1,None,"Lockset install")
# OTHER EXT DOORS
f(122,2,None,"Side/garage man doors (2680/2880)","Exterior single hinged doors.")
f(123,2,None,"Patio double doors (6080/5080)","Exterior double glass doors, black.")
f(124,1,None,"8' slider (8080)","8' sliding glass door, black.")
f(125,1,5500,"12' multi-slide (12080). FLAG multi-slide may run $8-12k","12' sliding/multi-slide glass door to rear porch, black.")
f(128,5,None,"Ext door locksets"); f(129,3,None,"Install hinged ext doors"); f(130,2,None,"Install sliders")
# INTERIOR DOORS
f(146,9,None,"8'0in SOLID-core at bedrooms/master (Jason)","Solid-core flat-stock 8' doors at bedrooms.")
f(144,13,None,"8'0in hollow flat-stock - common areas","Hollow-core flat-stock 8' doors.")
f(137,5,None,"6'8in hollow - closets/utility")
f(149,1,None,"Garage entry door 8' solid (fire-rated)")
f(154,28,None,"Door knobs"); f(155,28,None,"Door stops"); f(156,28,None,"Hardware install")
# TRIM
f(158,750,None,"Base molding LF (modern flat-stock)","Modern flat-stock base trim.")
f(159,400,None,"Window casing/jambs LF")
f(160,1200,None,"Trim labor")
f(180,HG,None,"Trim labor - qtr round, hardware (per SF)")
# PLUMBING
f(189,20,700,"Fixture openings (4 baths+powder). FLAG confirm count")
f(190,12,None,"Water openings (6 hose bibs + fridge/ice/DW/washer/2 WH)")
f(191,2,1800,"2 water heaters - electric heat-pump. FLAG gas tankless option off propane","Two high-efficiency water heaters. Allowance.")
# HVAC
f(194,1,8500,"House HVAC - 1 zoned system (spray foam) + master damper. FLAG quote","HVAC system for residence with zoning; high-efficiency.")
f(196,1,6500,"Garage HVAC - conditioned garage (Jason)","HVAC for conditioned garage.")
f(195,HEATED,None,"House flex duct")
f(197,GARAGE,None,"Garage flex duct")
f(193,2,None,"Gas lines to 2 gas stoves (Jason). FLAG add tankless if gas WH")
# ELECTRICAL
f(200,HG,8.0,"Electrical SF (heated+garage) @ $8 - modern, some exposed conduit. FLAG quote")
f(201,1,None,"Upgrade to 400A - all-electric+2 HVAC+EV. FLAG")
f(206,1,5000,"Low-voltage/security/data allowance","Low-voltage, data, security rough-in - allowance.")
# INSULATION - full spray foam
f(210,WALL_AREA,3.0,"Spray-foam WALLS @ $3.0/SF. FLAG open vs closed cell")
f(211,ROOF,4.5,"Spray-foam ROOF DECK closed-cell unvented low-slope @ $4.5/SF - EXPOSED")
# DRYWALL - walls only
f(213,21139,None,"Drywall WALLS only (Level 4) - NO ceilings (exposed). J&J method: Sum(room perimeter x ceiling height); tall stepped walls run to exposed deck. Matches Jason's measured takeoff (21,139). Prior shortcut (heated x3.2=8,400) was wrong.","Drywall hung, taped, finished (Level 4) on interior walls; ceilings left exposed per design.")
# SIDING / CLADDING
f(217,CLAD,14.0,"STANDING-SEAM METAL wall cladding ~2,800 SF @ $14/SF turnkey incl WRB/trim","Standing-seam metal wall cladding, factory-finished (no field paint).")
f(227,PERIM,11.0,"Metal fascia/parapet coping perimeter 340 LF")
f(229,PORCH,None,"Covered porch ceilings T&G 347 SF @ $5.5 STANDING RULE. FLAG may be exposed metal soffit","Tongue-and-groove ceiling at covered porches.")
# KITCHEN
f(243,20,200,"Kitchen lowers LF @ high-end $200","High-end cabinetry, kitchen.")
f(244,12,200,"Kitchen uppers LF")
f(245,10,200,"Kitchen island LF")
f(247,6,350,"Tall cabinets")
f(248,1,None,"Vent hood cabinet")
f(249,40,None,"Cabinet install labor")
f(252,80,85,"Kitchen counters 80 SF @ $85 level-6","Level-6 granite/quartz (or concrete) countertops, fabricated & installed.")
f(260,1,None,"Kitchen undermount sink"); f(261,1,None,"Kitchen faucet"); f(262,1,None,"Sink cutout"); f(254,1,None,"Pot filler")
f(269,45,None,"Backsplash SF"); f(270,45,None,"Backsplash sundries"); f(271,45,None,"Backsplash labor")
f(273,1,12000,"Appliance allowance (mid-high, incl 2 GAS stoves). FLAG often owner-supplied","Appliance allowance incl two gas ranges. Often owner-supplied - allowance.")
f(274,1,None,"Appliance install")
f(276,1,None,"Under-cabinet LED")
# PANTRY/BUTLER
f(291,12,175,"Butler/pantry lowers LF"); f(292,10,175,"Butler/pantry uppers LF")
f(298,15,55,"Butler pantry counter SF"); f(303,30,None,"Pantry shelving SF")
# COMMON
f(609,8,None,"Fans/light fixtures")
f(611,45,None,"Can/disk lights"); f(612,45,None,"Can light wiring")
# GUTTERS
f(617,200,None,"Gutters low eaves 200 LF. FLAG low-slope drainage/scuppers")
f(618,100,None,"Downspouts")
# PAINT
f(622,HEATED,None,"Interior WALL paint (ceilings exposed-coated)","Interior walls painted.")
f(623,GARAGE,None,"Garage wall paint")
f(624,0,None,"Exterior paint = $0 (metal cladding factory-finished)")
# GLASS
f(630,2,None,"Frameless glass shower enclosures. FLAG count","Frameless glass shower enclosure(s).")
# GARAGE DOOR
f(638,1,None,"16'x8' double garage door modern flush","Modern flush 16'x8' garage door.")
f(639,1,None,"Opener"); f(640,1,None,"Install")
# FINAL GRADING & DRIVEWAY
f(660,1,None,"Final grading"); f(661,1,None,"Grading labor/equip"); f(662,3,None,"Backfill dirt loads")
f(665,2400,None,"Concrete drive+walks LABOR ~2,400 SF. FLAG measure")
f(666,42,None,"Concrete drive+walks ~42 cu yd (~5in). Conservative per calibration")
# LANDSCAPING
f(669,1,2500,"Sod allowance","Sod / lawn establishment - allowance.")
f(672,1,3000,"Plant package allowance","Landscape plant package - allowance.")
f(673,1,2500,"Seed & straw disturbed area")
f(670,1,3000,"Irrigation allowance. FLAG confirm","Irrigation system - allowance.")
# CLEANING
f(675,HG,None,"Final clean interior")
f(676,3,None,"Dumpsters - 3 pulls")
f(677,HG,None,"Exterior pressure wash")
f(678,24,None,"Final window cleaning")
f(679,1,None,"Termite protection (slab)")

# BATH 1 = MASTER
f(316,1,None,"Master toilet"); f(319,18,175,"Master double vanity cabinet")
f(320,18,None,"Vanity hardware"); f(321,18,100,"Vanity install")
f(323,2,None,"Master 2 sinks"); f(324,2,None,"Cutouts"); f(325,2,None,"Faucets")
f(326,2,None,"Mirrors"); f(327,2,None,"Towel bars"); f(328,2,None,"Install mirror"); f(329,2,None,"Install towel")
f(330,2,None,"Vanity lights"); f(331,2,None,"Drain kits")
f(332,32,85,"Master vanity quartz 32 SF level-6","Level-6 quartz vanity tops.")
f(334,2,None,"Master shower valves (rain+hand)")
f(339,130,7,"Master shower tile wall material 130 SF @ $7"); f(340,130,None,"Sundries"); f(341,130,None,"Schluter"); f(342,130,None,"Tile wall labor")
f(343,1,None,"Niche labor"); f(344,3,None,"Niche tile"); f(345,1,None,"Shower bench"); f(346,1,None,"Bench labor")
f(348,40,None,"Master shower mud bed"); f(349,40,None,"Shower floor tile")
f(353,1,2000,"Master freestanding tub","Freestanding soaking tub, master."); f(354,1,None,"Tub valve")
f(374,70,8,"Master bath floor tile 70 SF @ $8"); f(375,70,None,"Sundries"); f(376,70,None,"Floor tile labor")
# BATH 2
f(382,1,None,"Bath2 toilet"); f(385,9,None,"vanity"); f(386,9,None,"hw"); f(387,9,100,"install")
f(389,1,None,"sink"); f(390,1,None,"cutout"); f(391,1,None,"faucet"); f(392,1,None,"mirror"); f(393,1,None,"towel")
f(394,1,None,"inst mirror"); f(395,1,None,"inst towel"); f(396,1,None,"light"); f(397,1,None,"drain")
f(398,14,85,"Bath2 quartz 14 SF level-6"); f(400,1,None,"Bath2 shower valve")
# BATH 3
f(482,1,None,"Bath3 toilet"); f(485,9,None,"vanity"); f(486,9,None,"hw"); f(487,9,100,"install")
f(489,1,None,"sink"); f(490,1,None,"cutout"); f(491,1,None,"faucet"); f(492,1,None,"mirror"); f(493,1,None,"towel")
f(494,1,None,"inst mirror"); f(495,1,None,"inst towel"); f(496,1,None,"light"); f(497,1,None,"drain")
f(498,14,85,"Bath3 quartz 14 SF level-6"); f(500,1,None,"Bath3 shower valve")
f(503,90,7,"Bath3 shower tile walls 90 SF"); f(505,90,None,"tile labor"); f(511,36,None,"mud bed"); f(512,36,None,"floor tile")
f(537,45,8,"Bath3 floor tile 45 SF"); f(538,45,None,"sundries"); f(539,45,None,"labor")
# BATH 4
f(545,1,None,"Bath4 toilet"); f(548,9,None,"vanity"); f(549,9,None,"hw"); f(550,9,100,"install")
f(552,1,None,"sink"); f(553,1,None,"cutout"); f(554,1,None,"faucet"); f(555,1,None,"mirror"); f(556,1,None,"towel")
f(557,1,None,"inst mirror"); f(558,1,None,"inst towel"); f(559,1,None,"light"); f(560,1,None,"drain")
f(561,14,85,"Bath4 quartz 14 SF level-6"); f(563,1,None,"Bath4 shower valve")
f(566,90,7,"Bath4 shower tile walls 90 SF"); f(568,90,None,"tile labor"); f(574,36,None,"mud bed"); f(575,36,None,"floor tile")
f(600,45,8,"Bath4 floor tile 45 SF"); f(601,45,None,"sundries"); f(602,45,None,"labor")
# Bath 2 shower tile rows (locate by name)
for r in range(401,443):
    nm=str(ws.cell(r,1).value or ""); par=str(ws.cell(r,2).value or "")
    if "Tile Walls  - Material allowance - Bath 2" in nm and "Shower" in par: f(r,90,7,"Bath2 shower tile walls 90 SF")
    if nm=="Tile wall labor - Bath 2" and "Shower" in par: f(r,90,None,"Bath2 tile wall labor")
    if "Shower mud bed - Bath 2" in nm: f(r,36,None,"Bath2 mud bed")
    if "Shower floor tile allowance - Bath 2" in nm: f(r,36,None,"Bath2 floor tile")
    if "Flooring Tile - Bath 2" in nm: f(r,45,8,"Bath2 floor tile 45 SF")

# ================= RECONCILIATION PATCH (Jason quotes/measures + waste) =================
# Drywall - room-perimeter x real height (main 15.5ft, garage 10ft); ceilings exposed
f(213, 17939, None, "Drywall WALLS: main 1,067 LF x 15.5ft = 16,539 + garage ~140 LF x 10ft = 1,400 = 17,939 SF. Ceilings EXPOSED (no ceiling drywall). J&J room-perimeter method.","Drywall hung, taped, finished (Level 4) on interior walls; ceilings left exposed per design.")
# Metal roof: Jason rate $9/SF + J&J 15% metal-roof waste
f(104, round(4850*1.15), 9.0, "Standing-seam metal roof: 4,850 roof area x1.15 (J&J 15% metal waste) = 5,578 SF @ $9/SF (Jason rate). Roof framing/metal QUOTED.","Standing-seam metal roof, low-slope, mechanically-seamed, turnkey installed.")
# HVAC - QUOTED; high b/c exposed rafters force all HARD SPIRAL duct
f(194,1,17000,"HVAC house equipment - QUOTED (Jason)","HVAC system for residence; high-efficiency.")
f(195,1,32569,"HVAC house DUCT = all HARD SPIRAL (exposed rafters, not soft flex) - QUOTED. Driver of high HVAC.","Hard spiral ductwork (exposed-structure design).")
f(196,1,6500,"Garage HVAC - QUOTED (conditioned garage)","HVAC for conditioned garage.")
f(197,1204,4,"Garage flex duct")
# Insulation - OPEN CELL, current vendor rates (waste in vendor qty)
f(210,7986,0.98,"OPEN-CELL spray foam WALLS 7,986 SF @ $0.98 (current vendor). Supersedes closed-cell.","Open-cell spray foam insulation, walls.")
f(211,5585,1.27,"OPEN-CELL spray foam ROOF DECK 5,585 SF @ $1.27 (current vendor)","Open-cell spray foam insulation, roof deck.")
# Foundation - separate footer/thickened-edge line (+10% waste on forms)
f(51,round(445*1.10),2,"Footer/thickened-edge form boards 445 LF +10% waste")
f(52,23,192,"Thickened-EDGE extra concrete ~23 cu yd (beyond flat slab; mono-slab thickened end)")
f(53,74,14,"Thickened-edge #4 rebar")
# NOTE: NO separate footer LABOR on a monolithic slab - slab labor (line 83) covers forming/pouring the thickened edge (Jason)
# General Requirements - pull pre-con soft costs OUT of COGS (Jason keeps in overhead)
for rr in (14,15,17,18):
    if rr in F: del F[rr]
# Interior + garage paint on MEASURED WALL AREA
f(622,17939,1.15,"Interior wall paint on measured wall area 17,939 SF @ ~$1.15 (matches Jason's ~$20.5k)","Interior walls painted.")
f(623,0,None,"(garage wall paint folded into 622 wall-area total)")
# Metal wall cladding - gross area @ $8/SF (Jason measure; waste/wrap in gross)
f(217,4682,8.0,"Standing-seam METAL wall cladding 4,682 SF GROSS @ $8/SF (Jason measure)","Standing-seam metal wall cladding, factory-finished (no field paint).")
# Exterior stone accent wall ~282 SF
f(239,282,4.0,"Exterior stone ACCENT wall 282 SF - material","Stone veneer accent wall."); f(240,282,3.5,"Accent wall stone labor")
# Apply J&J 10% waste to material area lines (tile, backsplash, T&G, flatwork concrete)
for rr in (229, 269,270, 339,340,341, 374,375, 666):
    if rr in F:
        q,h,nt,ds=F[rr]; f(rr, round(q*1.10,1), h, nt+" | +10% waste", ds)

print("fills defined:",len(F))
pickle.dump((F,dict(HEATED=HEATED,GARAGE=GARAGE,PORCH=PORCH,UNDER_ROOF=UNDER_ROOF,ROOF=ROOF,WALL_AREA=WALL_AREA,CLAD=CLAD,HG=HG,STAINED=STAINED,BAKE=BAKE,TODAY=TODAY)),open("fills.pkl","wb"))
print("stashed OK")
