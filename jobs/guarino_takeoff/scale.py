import fitz, math, collections
src = r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf"
doc = fitz.open(src)
p = doc[5]  # page 6 floor plan
# gather line segments from drawings
segs=[]
for d in p.get_drawings():
    for it in d["items"]:
        if it[0]=="l":
            a,b=it[1],it[2]
            segs.append((a.x,a.y,b.x,b.y))
        elif it[0]=="re":
            r=it[1]
            segs.append((r.x0,r.y0,r.x1,r.y0));segs.append((r.x1,r.y0,r.x1,r.y1))
            segs.append((r.x1,r.y1,r.x0,r.y1));segs.append((r.x0,r.y1,r.x0,r.y0))
print("total segs", len(segs))
# horizontal segs (dy~0), find longest -> likely overall building length, known 106'-5" = 106.417 ft
H=[s for s in segs if abs(s[1]-s[3])<1.5]
V=[s for s in segs if abs(s[0]-s[2])<1.5]
def L(s): return math.hypot(s[2]-s[0],s[3]-s[1])
H.sort(key=L,reverse=True); V.sort(key=L,reverse=True)
print("longest H lengths(pts):", [round(L(s),1) for s in H[:8]])
print("longest V lengths(pts):", [round(L(s),1) for s in V[:8]])
# nominal scale 3/16in=1ft -> 0.1875*72=13.5 pts/ft
print("expected pts/ft @3/16in=1ft:", 0.1875*72)
# if longest H is the 106.417ft overall:
if H: print("implied pts/ft from longest H/106.417:", round(L(H[0])/106.417,3))
