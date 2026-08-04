import fitz, math, collections
doc = fitz.open(r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf")
p = doc[5]
pf=13.41
col_len=collections.defaultdict(float)
col_segs=collections.defaultdict(list)
for d in p.get_drawings():
    col = d.get("color")
    w = d.get("width") or 0
    for it in d["items"]:
        if it[0]=="l":
            a,b=it[1],it[2]; Lp=math.hypot(b.x-a.x,b.y-a.y)
            key=(tuple(round(c,2) for c in col) if col else None, round(w,1))
            col_len[key]+=Lp
            if 150<a.x<1700 and 600<a.y<1520:
                col_segs[key].append((a.x,a.y,b.x,b.y,Lp))
# show color/width layers by total length
tot=sorted(col_len.items(),key=lambda z:-z[1])[:15]
for k,v in tot: print(f"color/width {k}: total {v/pf:,.0f} ft  ({v:,.0f} pt)")
