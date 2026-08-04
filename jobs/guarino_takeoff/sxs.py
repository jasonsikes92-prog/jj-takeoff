# -*- coding: utf-8 -*-
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
MINE=r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\Guarino Residence - Estimate.xlsx"
HIS=r"C:\Users\jason\Downloads\Guarino Residence V3 - Estimate Items.xlsx"
LEAF={"MATERIAL","LABOR","SUBCONTRACTOR","ALLOWANCE","FEE","EQUIPMENT"}
def load(path):
    wb=openpyxl.load_workbook(path,data_only=True); ws=wb["Estimate"]
    nr={}
    for r in range(2,ws.max_row+1):
        nm=ws.cell(r,1).value
        if nm: nr.setdefault(str(nm),r)
    def top(r):
        cur=r
        for _ in range(30):
            par=ws.cell(cur,2).value
            if par is None or str(par).strip()=="": return str(ws.cell(cur,1).value)
            pr=nr.get(str(par))
            if pr is None or pr==cur: return str(par)
            cur=pr
        return str(ws.cell(r,1).value)
    raw={}; amt={}
    for r in range(2,ws.max_row+1):
        if str(ws.cell(r,3).value) in LEAF:
            q=ws.cell(r,7).value or 0; h=ws.cell(r,8).value or 0; n=ws.cell(r,14).value or 0
            if n:
                t=top(r); raw[t]=raw.get(t,0)+q*h; amt[t]=amt.get(t,0)+n
    return raw,amt
mr,ma=load(MINE); hr,ha=load(HIS)
# normalize: my stained concrete sits under Kitchen; note only
cats=sorted(set(mr)|set(hr), key=lambda k:-(hr.get(k,0)+mr.get(k,0)))
NOTE={
 "Mechanical / HVAC":"His = QUOTED (hard spiral duct, exposed rafters). TRUE.",
 "Roofing":"Metal roof TRUE = $9/SF. His sheet @ $5.50 is ~$19.5k LIGHT; mine @ $11 a bit high.",
 "Insulation":"Open-cell, his vendor ~$1/SF = TRUE. Mine used closed-cell, too high.",
 "Foundation":"Mono slab needs separate footer line; pad. Mine low.",
 "General Requirements":"Mine carries plan/eng/survey/erosion as COGS; Jason keeps in overhead.",
 "Room Finishes - Kitchen":"Mine includes whole-house stained-concrete floor ($28.5k) in this bucket.",
 "Drywall":"His = full drywall (walls+ceilings). Mine = walls only (exposed ceiling concept).",
 "Paint/Stain":"Mine includes $15k black-coat of exposed structure.",
 "Exterior Finishes":"Both ~$50k; his metal siding $8/SF gross, mine $14/SF net.",
}
wb=openpyxl.Workbook(); ws=wb.active; ws.title="Category Comparison"
hdr=["Category","My COST","Jason COST","Δ Cost $","Δ %","My Amount","Jason Amount","Note"]
ws.append(hdr)
thin=Side(style="thin",color="BBBBBB")
for c in range(1,9):
    cell=ws.cell(1,c); cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="305496")
    cell.alignment=Alignment(wrap_text=True,vertical="center")
trawm=trawh=tamtm=tamth=0
for k in cats:
    cm=mr.get(k,0); ch=hr.get(k,0); am=ma.get(k,0); ah=ha.get(k,0)
    d=cm-ch; pc=(d/ch*100) if ch else (100 if cm else 0)
    ws.append([k,round(cm),round(ch),round(d),round(pc,0),round(am),round(ah),NOTE.get(k,"")])
    trawm+=cm;trawh+=ch;tamtm+=am;tamth+=ah
    rr=ws.max_row
    if abs(d)>=10000:
        for c in range(1,9): ws.cell(rr,c).fill=PatternFill("solid",fgColor="FFF2CC")
ws.append(["TOTAL (line cost / amount)",round(trawm),round(trawh),round(trawm-trawh),round((trawm/trawh-1)*100,1),round(tamtm),round(tamth),""])
for c in range(1,9): ws.cell(ws.max_row,c).font=Font(bold=True)
# margin wrapper rows
ws.append([])
ws.append(["--- WRAPPER / SELL ---"]); ws.cell(ws.max_row,1).font=Font(bold=True)
ws.append(["My model","12.1% baked + 8% contingency + 20% O&P","","","","","SELL $951,265 (25% profit after contingency)",""])
ws.append(["Jason sheet","10% markup + 20% overhead, NO contingency","","","","","SELL $845,744 (24.2% on sell)",""])
ws.append(["Roof correction impact","+$19.5k to Jason if metal roof = $9/SF","","","","","Jason corrected -> ~$865k",""])
widths=[40,13,13,12,8,13,13,60]
for i,w in enumerate(widths,1): ws.column_dimensions[chr(64+i)].width=w
for r in range(2,ws.max_row+1):
    for c in range(2,8):
        v=ws.cell(r,c).value
        if isinstance(v,(int,float)): ws.cell(r,c).number_format='#,##0'
ws.freeze_panes="A2"

# KEY LINE ITEMS sheet (big movers)
ws2=wb.create_sheet("Key Line Items")
ws2.append(["Line","My qty","My $/u","My Amount","Jason qty","Jason $/u","Jason Amount","TRUE / note"])
for c in range(1,9): ws2.cell(1,c).font=Font(bold=True,color="FFFFFF"); ws2.cell(1,c).fill=PatternFill("solid",fgColor="305496")
keylines=[
 ("Metal Roof (104)",4850,11.0,53350,5585,5.5,30718,"TRUE $9/SF -> 5,585 x9 = $50,265. Jason sheet LIGHT ~$19.5k; mine high ~$3k"),
 ("HVAC house equip (194)",1,8500,8500,1,17000,17000,"Jason QUOTED - true"),
 ("HVAC house duct (195)",2637,4.0,10548,1,32569,32569,"HARD SPIRAL duct (exposed rafters), not soft flex. Jason QUOTED - true. Mine way low"),
 ("HVAC garage (196)",1,6500,6500,1,6500,6955,"Match"),
 ("Garage duct (197)",1204,4.0,4816,1204,4.0,5153,"Match"),
 ("Insulation walls (210)",3074,3.0,9222,7986,0.98,9000,"Open-cell vendor ~$1/SF (gross area). Jason true; my rate 3x high"),
 ("Insulation roof (211)",4850,4.5,21731,5585,1.27,8157,"Open-cell. Jason true; mine closed-cell, too high"),
 ("Slab concrete (81)",69,185,12806,58,192,12806,"Close"),
 ("Footer labor (63)",0,0,0,445,20,9523,"I MISSED separate footer line on mono slab (~$9.5k)"),
 ("Metal wall cladding",2800,14.0,39200,4682,8.0,40083,"~Same $; his $8/SF x gross 4,682 vs my $14 x net 2,800"),
 ("Drywall (213)",8400,1.35,11340,21139,1.35,28547,"His=full walls+ceiling; mine=walls only (exposed concept)"),
]
for row in keylines:
    ws2.append([row[0],row[1],row[2],round(row[1]*row[2]),row[4],row[5],row[6],row[7]])
for i,w in enumerate([26,9,9,12,9,9,12,62],1): ws2.column_dimensions[chr(64+i)].width=w
for r in range(2,ws2.max_row+1):
    for c in (4,7): ws2.cell(r,c).number_format='#,##0'
ws2.freeze_panes="A2"
OUT=r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\Guarino - Estimate Comparison.xlsx"
wb.save(OUT)
print("SAVED",OUT)
# print chat table
print(f"\n{'CATEGORY':<40}{'MINE cost':>11}{'JASON cost':>12}{'Δ$':>10}{'Δ%':>7}")
for k in cats:
    cm=mr.get(k,0);ch=hr.get(k,0);d=cm-ch;pc=(d/ch*100) if ch else 0
    flag=" *" if abs(d)>=10000 else ""
    print(f"{k:<40}{cm:>11,.0f}{ch:>12,.0f}{d:>10,.0f}{pc:>6.0f}%{flag}")
print(f"{'-'*40}{'-'*11}{'-'*12}{'-'*10}")
print(f"{'TOTAL line cost (G x H)':<40}{trawm:>11,.0f}{trawh:>12,.0f}{trawm-trawh:>10,.0f}{(trawm/trawh-1)*100:>6.1f}%")
