import sys, math, collections; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[5]; PPF=18.0
GREEN=(0.243,0.357,0.184)
segs=[]
for dr in p.get_drawings():
    col=dr.get('color')
    if col is None or tuple(round(x,3) for x in col)!=GREEN: continue
    for it in dr['items']:
        if it[0]=='l':
            a,b=it[1],it[2]
            L=math.hypot(b.x-a.x,b.y-a.y)
            if L>1.0: segs.append(((a.x,a.y),(b.x,b.y),L))
        elif it[0]=='re':
            r=it[1]
            c=[(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1)]
            for i in range(4):
                a,b=c[i],c[(i+1)%4]; L=math.hypot(b[0]-a[0],b[1]-a[1])
                if L>1.0: segs.append((a,b,L))
print('roof segments:', len(segs), ' total LF:', round(sum(s[2] for s in segs)/PPF,1))
xs=[q[0] for s in segs for q in (s[0],s[1])]; ys=[q[1] for s in segs for q in (s[0],s[1])]
print(f'roof extent: x {min(xs)/PPF:.2f}-{max(xs)/PPF:.2f} ft ({(max(xs)-min(xs))/PPF:.2f} wide), y {min(ys)/PPF:.2f}-{max(ys)/PPF:.2f} ft ({(max(ys)-min(ys))/PPF:.2f} tall)')
# angle histogram
ang=collections.Counter()
for a,b,L in segs:
    t=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])) % 180
    ang[round(t/5)*5]+=1
print('angle histogram (deg mod 180):', sorted(ang.items()))
