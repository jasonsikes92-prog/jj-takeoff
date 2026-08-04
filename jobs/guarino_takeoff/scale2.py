import fitz, math
src = r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf"
doc = fitz.open(src)
p = doc[5]
words = p.get_text("words")  # x0,y0,x1,y1,text
# find the 106'-5" labels
targets = ["106'-5\"","45'-5","44'-10\"","53'-9\""]
for t in targets:
    for w in words:
        if w[4].replace(" ","")==t.replace(" ","") or t[:5] in w[4]:
            print(f"{w[4]!r} at x={w[0]:.0f}-{w[2]:.0f} y={w[1]:.0f}-{w[3]:.0f}")
            break
# collect segments excluding borders
segs=[]
for d in p.get_drawings():
    for it in d["items"]:
        if it[0]=="l":
            segs.append((it[1].x,it[1].y,it[2].x,it[2].y))
def L(s): return math.hypot(s[2]-s[0],s[3]-s[1])
# Find a horizontal dimension line near a 106'-5" label: long H segment whose y is near the label y, length 800-1800pt
print("\nLong horizontal segments (length 800-1900pt) with their y:")
H=[s for s in segs if abs(s[1]-s[3])<2 and 800<L(s)<1900]
H=sorted(set([(round(L(s),1), round(s[1])) for s in H]))
for l,y in H[:30]: print(" len",l,"y",y)
