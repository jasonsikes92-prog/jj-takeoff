import sys, math, json, itertools; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
from shapely.geometry import Polygon
from shapely.ops import unary_union
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[1]; PPF=9.0
COL={'HEATED':(0.0,1.0,0.0),'GARAGE':(1.0,0.0,0.0),'REAR PORCH':(0.502,0.0,1.0),'FRONT PORCH':(0.0,1.0,1.0)}
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
    u=unary_union([q for q in ps if q.is_valid and q.area>0.01])
    return u if u.geom_type=='Polygon' else max(u.geoms,key=lambda q:q.area)
S={k:U(k) for k in COL}
print('SLAB PIECES')
for k,g in S.items(): print(f'   {k:<13}{g.area:9.1f} SF   own perimeter {g.exterior.length:8.2f} LF')
tot_own=sum(g.exterior.length for g in S.values())
print(f'   sum of own perimeters {tot_own:8.2f} LF')
# whole-slab union outer perimeter
whole=unary_union(list(S.values())).buffer(0.25).buffer(-0.25)
whole=whole if whole.geom_type=='Polygon' else max(whole.geoms,key=lambda q:q.area)
print(f'\nWHOLE-SLAB union outer perimeter {whole.exterior.length:8.2f} LF   (area {whole.area:.1f} SF)')
print('\nINTERNAL STEP LINES (every pair that touches):')
seams={}
for a,b in itertools.combinations(S,2):
    L=S[a].exterior.intersection(S[b].buffer(0.6)).length
    if L>1.0:
        seams[f'{a} <-> {b}']=round(L,2)
        print(f'   {a:<12} <-> {b:<12}{L:8.2f} LF')
tot_seam=sum(seams.values())
print(f'   TOTAL internal steps {tot_seam:8.2f} LF')
print()
outer=whole.exterior.length
cands=[('outer + internal steps', outer+tot_seam),
       ('sum of each slab own perimeter', tot_own),
       ('house+garage envelope + full porch outlines (prev)', 387.69+203.34+44.85)]
for n,v in cands:
    print(f'   {n:<52}{v:8.2f} LF   vs 634.79 raw = {100*(v-634.79)/634.79:+6.1f}%')
json.dump({'outer':round(outer,2),'seams':seams,'own':round(tot_own,2)},open('footer2.json','w'),indent=1)
