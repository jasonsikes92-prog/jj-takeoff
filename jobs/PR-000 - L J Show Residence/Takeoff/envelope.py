import sys, math, collections, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
from shapely.geometry import Polygon
from shapely.ops import unary_union
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[1]; PPF=9.0
COL={'HEATED':(0.0,1.0,0.0),'GARAGE':(1.0,0.0,0.0),'REAR PATIO':(0.502,0.0,1.0),'FRONT PATIO':(0.0,1.0,1.0)}
def facets(ck):
    out=[]
    for dr in p.get_drawings():
        f=dr.get('fill')
        if f is None or tuple(round(c,3) for c in f)!=ck: continue
        pts=[]
        for it in dr['items']:
            if it[0]=='l': pts+=[it[1],it[2]]
            elif it[0]=='re':
                r=it[1]; pts+=[fitz.Point(r.x0,r.y0),fitz.Point(r.x1,r.y0),fitz.Point(r.x1,r.y1),fitz.Point(r.x0,r.y1)]
        s=[]
        for q in pts:
            if not s or math.hypot(q.x-s[-1].x,q.y-s[-1].y)>0.01: s.append(q)
        if len(s)>=3: out.append([(q.x/PPF,q.y/PPF) for q in s])
    return out
polys={}
for nm,ck in COL.items():
    ps=[Polygon(f).buffer(0) for f in facets(ck)]
    u=unary_union([q for q in ps if q.is_valid and q.area>0.01])
    polys[nm]=u
    print(f'{nm:<13} union area {u.area:9.1f} SF   bounds {[round(b,2) for b in u.bounds]}')
# CONDITIONED ENVELOPE = heated + garage (both are walled, roofed, cladded boxes)
env = unary_union([polys['HEATED'], polys['GARAGE']]).buffer(0.02).buffer(-0.02)
print()
print(f'HEATED+GARAGE envelope: area {env.area:.1f} SF  perimeter {env.length:.2f} LF  type {env.geom_type}')
g = env if env.geom_type=='Polygon' else max(env.geoms,key=lambda q:q.area)
co=list(g.exterior.coords)
segs=[]
for i in range(len(co)-1):
    a,b=co[i],co[i+1]
    L=math.hypot(b[0]-a[0],b[1]-a[1])
    if L<0.15: continue
    ang=round(math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])))%180
    segs.append({'i':len(segs),'len':round(L,2),'ang':ang,'a':[round(a[0],2),round(a[1],2)],'b':[round(b[0],2),round(b[1],2)]})
print(f'exterior wall segments: {len(segs)}   total {sum(s["len"] for s in segs):.2f} LF')
byang=collections.Counter()
for s in segs: byang[s['ang']]+=s['len']
print('LF by bearing:', {k:round(v,1) for k,v in sorted(byang.items(), key=lambda t:-t[1])})
json.dump(segs, open('envelope_walls.json','w'), indent=1)
print()
for s in segs: print(f"   w{s['i']:<3}{s['len']:7.2f} LF  bearing {s['ang']:3d}   ({s['a'][0]:7.2f},{s['a'][1]:7.2f}) -> ({s['b'][0]:7.2f},{s['b'][1]:7.2f})")
