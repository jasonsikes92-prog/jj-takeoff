import fitz, math
doc=fitz.open(r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf")
p=doc[1] # site plan
words=p.get_text("words")
# find distance labels to set scale
for w in words:
    t=w[4]
    if any(k in t for k in ["462","87.2","350","98,5","2.26"]):
        print(f"{t!r} at ({w[0]:.0f},{w[1]:.0f})")
# segments
segs=[]
for d in p.get_drawings():
    for it in d["items"]:
        if it[0]=="l": segs.append((it[1].x,it[1].y,it[2].x,it[2].y))
def L(s): return math.hypot(s[2]-s[0],s[3]-s[1])
# longest segments = lot lines; the 462' line should be ~462*scale
segs=sorted(segs,key=L,reverse=True)
print("\nLongest site segments (pt) & endpoints:")
for s in segs[:8]:
    print(f"  len {L(s):.0f}  ({s[0]:.0f},{s[1]:.0f})->({s[2]:.0f},{s[3]:.0f})")
