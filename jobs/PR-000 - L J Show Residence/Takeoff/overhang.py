import sys, math, collections, statistics; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[5]; PPF=18.0
GREEN=(0.243,0.357,0.184); GRAY=(0.588,0.588,0.588)
def grab(colkey, minw=None):
    out=[]
    for dr in p.get_drawings():
        col=dr.get('color')
        if col is None or tuple(round(x,3) for x in col)!=colkey: continue
        if minw is not None and (dr.get('width') or 0) < minw: continue
        for it in dr['items']:
            if it[0]=='l':
                a,b=it[1],it[2]
                if math.hypot(b.x-a.x,b.y-a.y)>2: out.append(((a.x,a.y),(b.x,b.y)))
            elif it[0]=='re':
                r=it[1]; c=[(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1)]
                for i in range(4):
                    a,b=c[i],c[(i+1)%4]
                    if math.hypot(b[0]-a[0],b[1]-a[1])>2: out.append((a,b))
    return out
roof=grab(GREEN); wall=grab(GRAY, minw=0.9)
print('roof segs',len(roof),' wall segs',len(wall))
def d_pt_seg(px,py,a,b):
    vx,vy=b[0]-a[0],b[1]-a[1]; L2=vx*vx+vy*vy
    if L2==0: return math.hypot(px-a[0],py-a[1])
    t=max(0,min(1,((px-a[0])*vx+(py-a[1])*vy)/L2))
    return math.hypot(px-(a[0]+t*vx), py-(a[1]+t*vy))
# sample points along each roof segment; take distance to nearest wall line
dists=[]
for a,b in roof:
    L=math.hypot(b[0]-a[0],b[1]-a[1])
    n=max(2,int(L/6))
    for i in range(n+1):
        t=i/n; px,py=a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])
        m=min((d_pt_seg(px,py,c,e) for c,e in wall), default=None)
        if m is not None: dists.append(m/PPF)
dists=[x for x in dists if x<6]
print(f'n samples={len(dists)}')
h=collections.Counter(round(x*4)/4 for x in dists)
print('overhang distance histogram (ft, 3in bins):')
for k in sorted(h):
    if h[k]>=12: print(f'   {k:5.2f} ft ({k*12:5.1f} in)  {"#"*(h[k]//12)} {h[k]}')
print(f'median {statistics.median(dists):.3f} ft')
