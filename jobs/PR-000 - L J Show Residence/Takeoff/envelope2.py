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
def U(nm):
    ps=[Polygon(f).buffer(0) for f in facets(COL[nm])]
    return unary_union([q for q in ps if q.is_valid and q.area>0.01])
H=U('HEATED'); G=U('GARAGE'); RP=U('REAR PATIO'); FP=U('FRONT PATIO')
B=0.30
env=unary_union([H,G]).buffer(B).buffer(-B)
g = env if env.geom_type=='Polygon' else max(env.geoms,key=lambda q:q.area)
def simplify_ring(ring, tol=0.12):
    co=list(ring.coords)
    out=[co[0]]
    for q in co[1:]:
        if math.hypot(q[0]-out[-1][0],q[1]-out[-1][1])>tol: out.append(q)
    # merge collinear
    res=[out[0]]
    for i in range(1,len(out)-1):
        a,b,c=res[-1],out[i],out[i+1]
        a1=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])); a2=math.degrees(math.atan2(c[1]-b[1],c[0]-b[0]))
        if abs((a1-a2+180)%360-180)>3: res.append(b)
    res.append(out[-1])
    return res
ring=simplify_ring(g.exterior)
segs=[]
for i in range(len(ring)-1):
    a,b=ring[i],ring[i+1]
    L=math.hypot(b[0]-a[0],b[1]-a[1])
    if L<0.4: continue
    ang=round(math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])))%180
    segs.append({'i':len(segs),'len':round(L,2),'ang':ang,'mid':[round((a[0]+b[0])/2,2),round((a[1]+b[1])/2,2)],
                 'a':[round(a[0],2),round(a[1],2)],'b':[round(b[0],2),round(b[1],2)]})
tot=sum(s['len'] for s in segs)
print(f'MERGED heated+garage envelope: area {g.area:.1f} SF   EXTERIOR WALL PERIMETER {tot:.2f} LF   ({len(segs)} segments)')
byang=collections.Counter()
for s in segs: byang[s['ang']]+=s['len']
print('LF by bearing:', {k:round(v,1) for k,v in sorted(byang.items(),key=lambda t:-t[1])})
print()
# which walls face a covered porch (rear patio / front patio) -> those are porch-side walls
RPb=RP.buffer(1.2); FPb=FP.buffer(1.2)
from shapely.geometry import LineString
for s in segs:
    ls=LineString([s['a'],s['b']])
    s['porch'] = 'REAR' if ls.intersection(RPb).length > 0.5*ls.length else ('FRONT' if ls.intersection(FPb).length>0.5*ls.length else '')
    s['rot45'] = s['ang'] in (45,135)
for s in segs:
    print(f"   w{s['i']:<3}{s['len']:7.2f} LF  brg {s['ang']:3d}  {'ROT45' if s['rot45'] else '     '}  {'porch:'+s['porch'] if s['porch'] else ''}")
json.dump(segs, open('envelope_walls.json','w'), indent=1)
print()
print(f"  walls facing REAR covered porch: {sum(s['len'] for s in segs if s['porch']=='REAR'):.1f} LF")
print(f"  walls facing FRONT covered porch: {sum(s['len'] for s in segs if s['porch']=='FRONT'):.1f} LF")
print(f"  rotated-45 walls (garage wing): {sum(s['len'] for s in segs if s['rot45']):.1f} LF")
# rear porch outer edge (the open sides where columns/beam are) -- perimeter not shared with house
rp = RP if RP.geom_type=='Polygon' else max(RP.geoms,key=lambda q:q.area)
shared = rp.exterior.intersection(g.buffer(0.8)).length
print(f"  REAR PORCH outline {rp.exterior.length:.1f} LF, of which {shared:.1f} LF abuts the house -> OPEN edge {rp.exterior.length-shared:.1f} LF")
fp = FP if FP.geom_type=='Polygon' else max(FP.geoms,key=lambda q:q.area)
sh2 = fp.exterior.intersection(g.buffer(0.8)).length
print(f"  FRONT PORCH outline {fp.exterior.length:.1f} LF, of which {sh2:.1f} LF abuts the house -> OPEN edge {fp.exterior.length-sh2:.1f} LF")
