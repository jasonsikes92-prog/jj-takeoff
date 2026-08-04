# -*- coding: utf-8 -*-
import fitz, re
doc=fitz.open(r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf")
def ft(s):  # "12'-4" or 12'-4 1 2" -> decimal feet
    s=s.strip().replace('"','')
    m=re.match(r"(\d+)'\s*-?\s*(\d+)?\s*(\d+)?\s*(\d+)?",s)
    if not m: return None
    f=int(m.group(1)); inch=int(m.group(2) or 0)
    if m.group(3) and m.group(4): inch+=int(m.group(3))/int(m.group(4))
    return f+inch/12
# page 3 SQFT sheet text - find W X L pairs
txt=doc[2].get_text()
pairs=re.findall(r"(\d+'-\d+(?:\s+\d+\s+\d+)?\")\s*[xX]\s*(\d+'-\d+(?:\s+\d+\s+\d+)?\")",txt)
print("found",len(pairs),"dim pairs on SQFT sheet")
tot_a=0; tot_p=0; rows=[]
for w,l in pairs:
    W=ft(w); L=ft(l)
    if W and L:
        a=W*L; p=2*(W+L); tot_a+=a; tot_p+=p
        rows.append((round(W,1),round(L,1),round(a),round(p)))
for r in sorted(rows,key=lambda z:-z[2]):
    print(f"  {r[0]:>5} x {r[1]:>5}  area={r[2]:>5}  perim={r[3]:>4}")
print(f"\nSUM area={tot_a:,.0f} SF   SUM perimeter={tot_p:,.0f} LF")
print(f"heated target=2637  (garage 1204, total 3841)")
# implied wall drywall at various avg heights
for h in (9,10,11,12,13,14):
    print(f"  walls @ {h}ft = {tot_p*h:,.0f} SF   (Jason=21,139)")
