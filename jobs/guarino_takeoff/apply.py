# -*- coding: utf-8 -*-
import openpyxl, pickle
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
SRC=r"C:\Users\jason\.claude\skills\jnj-estimate-takeoff\templates\estimate-template.xlsx"
OUT=r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\Guarino Residence - Estimate.xlsx"
F,G=pickle.load(open("fills.pkl","rb"))
BAKE=G["BAKE"]; HG=G["HG"]; STAINED=G["STAINED"]; ROOF=G["ROOF"]; TODAY=G["TODAY"]
MKT={"MATERIAL":15,"FEE":15,"LABOR":7,"SUBCONTRACTOR":7,"EQUIPMENT":7,"ALLOWANCE":8}  # per-type markup %
wb=openpyxl.load_workbook(SRC); ws=wb["Estimate"]
LEAF={"MATERIAL","LABOR","SUBCONTRACTOR","ALLOWANCE","FEE","EQUIPMENT"}

# ---- map name->toplevel group for rollup ----
# Build parent lookup by row using Name/Parent columns
name_rows={}
for r in range(2,ws.max_row+1):
    nm=ws.cell(r,1).value
    if nm: name_rows.setdefault(str(nm),r)
def toplevel(r):
    seen=0
    cur=r
    while seen<30:
        seen+=1
        par=ws.cell(cur,2).value
        if par is None or str(par).strip()=="":
            return str(ws.cell(cur,1).value)
        pr=name_rows.get(str(par))
        if pr is None or pr==cur: return str(par)
        cur=pr
    return str(ws.cell(r,1).value)

NOTES=[]  # (row,item,qty,unit,amount,basis)
DESCS={}
def setrow(r,q,h,note,desc):
    ct=ws.cell(r,3).value
    H = ws.cell(r,8).value if h is None else h
    if H is None: H=0
    ws.cell(r,7).value=q
    ws.cell(r,8).value=H
    k=MKT.get(str(ct).upper(),0)/100.0
    ws.cell(r,11).value=round(k*100,2)
    J=q*H; L=J*k; M=H*(1+k); N=q*M
    ws.cell(r,10).value=round(J,2)
    ws.cell(r,12).value=round(L,2)
    ws.cell(r,13).value=round(M,4)
    ws.cell(r,14).value=round(N,2)
    if desc is not None: ws.cell(r,15).value=desc
    nm=ws.cell(r,1).value
    NOTES.append((r,str(nm),q,ws.cell(r,9).value,round(N,2),note))
    return q*H, N

raw=0.0; sub=0.0
# zero all leaf rows first (clean slate for unfilled)
for r in range(2,ws.max_row+1):
    if str(ws.cell(r,3).value) in LEAF and r not in F:
        ws.cell(r,7).value=0; ws.cell(r,10).value=0; ws.cell(r,12).value=0; ws.cell(r,14).value=0
# apply fills
for r,(q,h,note,desc) in sorted(F.items()):
    c,n=setrow(r,q,h,note,desc)
    raw+=c; sub+=n

# ---- append modern-specific leaf rows before Summary (row 680) ----
ins_at=680
extra=[
 ("Stained & sealed concrete floors","Room Finishes - Kitchen","SUBCONTRACTOR","15",STAINED,7.0,"ft2",
   "Stained & sealed concrete finish floors (slab IS the finish floor) = heated+garage 3,841 - bath tile 210 = 3,631 SF @ $7","Stained and sealed concrete finished floors throughout (polished/sealed slab)."),
 ("Spray-coat exposed structure / ducts / foam - BLACK","Paint/Stain","SUBCONTRACTOR","14",HG,3.5,"ft2",
   "Spray-coat exposed I-joists, ductwork & spray-foam ceilings BLACK; includes ignition-barrier coating for exposed foam = heated+garage 3,841 SF @ $3.5","Exposed ceiling structure, ductwork and insulation spray-coated black (industrial finish); includes code ignition-barrier coating."),
 ("Slab reinforcing - #4 rebar grid 24in OC","Monolithic Slab","MATERIAL","4.15",192,14.0,"each",
   "Slab #4 rebar grid 24in OC per slab detail = ~3,841 LF / 20ft sticks = 192","Slab reinforcing steel."),
 ("HVAC zone damper - master suite","Mechanical / HVAC","SUBCONTRACTOR","9",1,1500.0,"each",
   "Zoned damper + thermostat to separate master cooling from rest of house (Jason)","Zoned damper to separate master-suite cooling."),
 ("Permanent power connection from transformer","Electrical","SUBCONTRACTOR","8",1,2500.0,"each",
   "Permanent power service connection from subdivision transformer (short run)","Permanent power service connection."),
]
for mr in list(ws.merged_cells.ranges): ws.unmerge_cells(str(mr))
ws.insert_rows(ins_at,len(extra))
for i,(nm,par,ct,code,q,h,unit,note,desc) in enumerate(extra):
    r=ins_at+i
    ws.cell(r,1).value=nm; ws.cell(r,2).value=par; ws.cell(r,3).value=ct; ws.cell(r,4).value="Complete"
    ws.cell(r,5).value=code; ws.cell(r,6).value="Flat rate"; ws.cell(r,9).value=unit
    c,n=setrow(r,q,h,note,desc); raw+=c; sub+=n

# ---- Summary / margin stack ----
sumr=ins_at+len(extra)+2
# clear stale template summary tail
for rr in range(ins_at+len(extra), ws.max_row+1):
    for cc in range(1,16): ws.cell(rr,cc).value=None
def S(rr,label,val,bold=True,fill=None,money=True):
    ws.cell(rr,13).value=label
    if money: ws.cell(rr,14).value=round(val,2)
    else: ws.cell(rr,14).value=val
    if bold: ws.cell(rr,13).font=Font(bold=True); ws.cell(rr,14).font=Font(bold=True)
    if fill:
        for c in (13,14): ws.cell(rr,c).fill=PatternFill("solid",fgColor=fill)
mkpct=(sub/raw-1)*100 if raw else 0
ws.cell(sumr-1,13).value="SUMMARY"; ws.cell(sumr-1,13).font=Font(bold=True,size=12)
S(sumr,  "Raw trades cost (incl. waste)",raw,bold=False)
S(sumr+1,"Per-line markup (15/7/8 by type)",sub-raw,bold=False)
S(sumr+2,"ESTIMATE SUBTOTAL (cost + waste + markup)",sub,fill="FFFF00")
S(sumr+4,"$ / heated SF (subtotal)",round(sub/G["HEATED"],2),bold=False)
S(sumr+5,"$ / under-roof SF (subtotal)",round(sub/G["UNDER_ROOF"],2),bold=False)
ws.cell(sumr+6,13).value="NOTE: Overhead/Profit & Contingency are applied in Buildern's"
ws.cell(sumr+7,13).value="Summary section — NOT carried as estimate line items."
ws.cell(sumr+6,13).font=Font(italic=True); ws.cell(sumr+7,13).font=Font(italic=True)

print(f"RAW COST (incl waste)   {raw:>12,.0f}")
print(f"PER-LINE MARKUP 15/7/8  {sub-raw:>12,.0f}  ({mkpct:.1f}% blended)")
print(f"ESTIMATE SUBTOTAL       {sub:>12,.0f}   (${sub/G['HEATED']:,.0f}/heated SF | ${sub/G['UNDER_ROOF']:,.0f}/under-roof SF)")
print(f"O&P + contingency -> applied in Buildern summary (not in lines)")

# ---- group rollup ----
roll={}
for r in range(2,ws.max_row+1):
    if str(ws.cell(r,3).value) in LEAF:
        N=ws.cell(r,14).value or 0
        if N: roll[toplevel(r)]=roll.get(toplevel(r),0)+N
pickle.dump((NOTES,roll,dict(raw=raw,sub=sub)),open("results.pkl","wb"))

# ---- TAKEOFF NOTES tab ----
if "Takeoff Notes" in wb.sheetnames: del wb["Takeoff Notes"]
tn=wb.create_sheet("Takeoff Notes")
tn.append(["Row","Item","Qty","Unit","Amount (incl baked markup)","Takeoff basis / conversion (internal)"])
for c in range(1,7): tn.cell(1,c).font=Font(bold=True)
for (r,item,q,unit,amt,basis) in NOTES:
    tn.append([r,item,q,unit,amt,basis])
tn.append([]); tn.append(["GEOMETRY (measured)","","","","",""])
for k,v in [("Heated SF",G["HEATED"]),("Garage SF (conditioned)",G["GARAGE"]),("Covered porches SF",G["PORCH"]),
            ("Total under roof SF",G["UNDER_ROOF"]),("Roof area SF (low-slope x1.003)",ROOF),
            ("Exterior wall area SF",G["WALL_AREA"]),("Metal cladding net SF",G["CLAD"]),
            ("Slab / stained-concrete SF",HG),("Perimeter LF",340)]:
    tn.append(["",k,v,"","",""])
tn.append(["","Scale verified","","","","Floor plan 106'-5\" overall dim = 1427 pt -> 13.41 pt/ft (matches 3/16in). Elevations 18 pt/ft (side width 54.2'=53'-9\" check)."])
for col,w in zip("ABCDEF",[6,46,10,10,16,80]): tn.column_dimensions[col].width=w

# ---- ASSUMPTIONS TO CONFIRM tab ----
if "Assumptions to Confirm" in wb.sheetnames: del wb["Assumptions to Confirm"]
ac=wb.create_sheet("Assumptions to Confirm")
ac.append(["ASSUMPTION / OPEN ITEM","My value","Basis / why flagged (★ = biggest $ movers, confirm first)"])
for c in range(1,4): ac.cell(1,c).font=Font(bold=True)
rows=[
 ("★ MARKUP MODEL","12.1% baked + 8% contingency (shown) + 20% O&P (shown)","Per Jason: markup baked into line items; only 20% O&P shown to customer. Compounds to a 25% profit margin AFTER fully reserving the 8% contingency. sell = subtotal x1.08 x1.20."),
 ("★ Standing-seam METAL roof (low slope)","4,850 SF @ $11/SF turnkey","1/2:12 & 1:12 = nearly flat; needs mechanically-seamed low-slope panels. Get roofer quote - could be $9-13. Biggest single line."),
 ("★ Standing-seam METAL wall cladding","2,800 SF @ $14/SF","All cladding is standing-seam metal (Jason) -> NO exterior paint. Premium rate; confirm panel/profile & get quote. Modern cladding chronically under-budgeted (calibration)."),
 ("★ I-joist roof framing","4,850 SF @ $6 material + labor on 4,188","Priced as engineered floor (open-span low-slope), rafters dropped (no double-count). Lumber VOLATILE - date-stamped "+TODAY+"; get current quote."),
 ("★ Septic (new lot, 4-bath)","$13,000","Bumped from template $8,500; likely engineered/level-3 on a subdivision lot. GET SEPTIC QUOTE. Public water tap separate."),
 ("★ HVAC - 2 systems + master zone damper","$ ~ house $8.5k + garage $6.5k + duct + damper","Jason: 2 units (garage conditioned) + master-suite damper. Spray foam would allow 1, but garage+comfort drives 2. High-scatter line - get quote."),
 ("★ Stained concrete floors","3,631 SF @ $7","Slab IS finish floor (Jason). No LVP/wood. Grind/stain/seal high-end. Confirm finish (stain vs polish) & rate."),
 ("★ Exposed structure painted black","3,841 SF @ $3.5","No ceiling drywall; I-joists/ducts/foam exposed & sprayed black (Jason). Includes ignition-barrier coating for exposed foam - CONFIRM code path w/ Newton Co & spray quote."),
 ("★ Finish tier = HIGH-END","level-6 quartz/granite, fully-tiled showers","Counters $85/SF, tile $7-8/SF, cabinets $200/LF. Finishes run light cold (calibration) - bumped. Confirm selections."),
 ("Heated SF basis","2,637","Sheet 1/3 AREAS. Floor plan also shows 2,879 'living area' & 6,216 footprint - using 2,637 per Jason (ignore footprint). Confirm if 2,879 is the contract conditioned SF."),
 ("County / permits","Newton County @ $2.0/SF","Permits swing ~2x by county & chronically under (calibration). PRE-QUALIFY permit cost with Newton Co before contract."),
 ("Water / sewer","Public water tap + new septic","8in main on Meadow View. Confirm Newton tap fee; septic type."),
 ("Insulation - full spray foam","walls $3.0, roof deck $4.5 (closed-cell)","Unvented low-slope roof must be closed-cell at deck; exposed. Confirm open vs closed cell on walls."),
 ("Window count","24 openings @ $625","Plan ~14 + clerestory band ~10. Confirm exact count & grade (don't over-price tall windows - calibration)."),
 ("Exterior doors","front double + 12' multi-slide + 8' slider + 2 dbl + 2 single","Mapped from elevation codes (16080 garage / 12080 / 8080 / 6080 / 5080). Multi-slide may run $8-12k. Confirm schedule."),
 ("Interior doors","9 solid 8' (bedrooms) / 13 hollow 8' / 5 closet","Jason: solid on all bedrooms, flat-stock modern. Confirm counts."),
 ("Propane / gas","1,000-gal buried tank $7,500 + gas lines to 2 stoves","Jason. FLAG: want gas tankless water heaters off the tank? (currently electric heat-pump WH)."),
 ("Water heaters","2 @ $1,800 electric heat-pump","Confirm electric vs gas tankless (propane available)."),
 ("Electrical","$8/SF + 400A + LV allowance","Industrial-modern may have exposed conduit (pricier). Get quote. High-scatter line."),
 ("Driveway + walks","~2,400 SF concrete, ~$15k","Site-plan scale wouldn't auto-verify; drive length ~110 LF ESTIMATED - FIELD-CONFIRM. Carried conservative (calibration: chronic under)."),
 ("Silt fence / clearing","750 LF / pasture, 2 days strip","Disturbed-area perimeter estimated; pasture = no tree clearing, NO demo. Confirm disturbed limits."),
 ("Covered porch ceilings (T&G)","347 SF @ $5.5","Standing rule. With exposed-metal aesthetic these may be exposed metal soffit instead - confirm."),
 ("Rear covered porch SF","~270","Backed out of roof-plan area (4,829) minus walls+overhang. Confirm actual covered rear porch size."),
 ("Masonry","$0","No fireplace, all-metal, mono slab. Confirm no stone/concrete feature wall at entry (calibration: carry masonry even on non-masonry homes)."),
 ("Appliances","$12,000 allowance incl 2 gas ranges","Often owner-supplied (calibration) - confirm in/out of contract."),
 ("Landscaping / irrigation","sod+plants+seed+irrigation ~$11k","Zero-trap line, always budgeted. Confirm scope/irrigation."),
 ("Gutters / roof drainage","200 LF + downspouts","Low-slope parapet may use internal drains/scuppers - confirm drainage design."),
 ("Contingency %","8%","First-of-kind elements (low-slope I-joist + standing-seam everything + exposed industrial). Your call - set higher/lower."),
]
for row in rows: ac.append(row)
ac.cell(2,1).font=Font(bold=True,color="C00000")
for col,w in zip("ABC",[40,40,95]): ac.column_dimensions[col].width=w
ac.row_dimensions[1].height=14

wb.save(OUT)
print("SAVED",OUT)
