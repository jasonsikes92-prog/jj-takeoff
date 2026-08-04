import fitz, math
doc = fitz.open(r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf")
p = doc[5]
segs=[]
for d in p.get_drawings():
    for it in d["items"]:
        if it[0]=="l": segs.append((it[1].x,it[1].y,it[2].x,it[2].y))
        elif it[0]=="re":
            r=it[1]
            for s in [(r.x0,r.y0,r.x1,r.y0),(r.x0,r.y1,r.x1,r.y1),(r.x0,r.y0,r.x0,r.y1),(r.x1,r.y0,r.x1,r.y1)]:
                segs.append(s)
def L(s): return math.hypot(s[2]-s[0],s[3]-s[1])
# horizontal dim line near bottom y 1455-1480
print("H segs near y=1455-1482 (the 106'-5 overall dim line):")
cand=[s for s in segs if abs(s[1]-s[3])<2 and 1450<s[1]<1485 and L(s)>200]
cand=sorted(set((round(min(s[0],s[2])),round(max(s[0],s[2])),round(L(s),1)) for s in cand),key=lambda z:-z[2])
for c in cand[:12]: print("  x",c[0],"->",c[1],"len",c[2])
# Vertical dim line near right for 106'-5 (right side) y range
print("\nV segs len>200 with x near right plan edge (x 1480-1560):")
cv=[s for s in segs if abs(s[0]-s[2])<2 and 1460<s[0]<1580 and L(s)>200]
cv=sorted(set((round(min(s[1],s[3])),round(max(s[1],s[3])),round(L(s),1)) for s in cv),key=lambda z:-z[2])
for c in cv[:12]: print("  y",c[0],"->",c[1],"len",c[2])
# Overall wall cluster bbox (exclude title block x>1700)
xs=[];ys=[]
for s in segs:
    for (x,y) in [(s[0],s[1]),(s[2],s[3])]:
        if 150<x<1650 and 600<y<1520: xs.append(x);ys.append(y)
print(f"\nWall-cluster bbox: x {min(xs):.0f}-{max(xs):.0f} (w={max(xs)-min(xs):.0f}pt)  y {min(ys):.0f}-{max(ys):.0f} (h={max(ys)-min(ys):.0f}pt)")
