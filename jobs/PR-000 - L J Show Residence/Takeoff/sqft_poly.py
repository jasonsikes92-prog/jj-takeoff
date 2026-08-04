import sys, math, collections; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[1]
COL={(0.0,1.0,0.0):'HEATED',(1.0,0.0,0.0):'GARAGE',(0.502,0.0,1.0):'REAR PATIO',(0.0,1.0,1.0):'FRONT PATIO'}
areas=collections.defaultdict(float); tris=collections.defaultdict(list)
for dr in p.get_drawings():
    f=dr.get('fill')
    if f is None: continue
    key=tuple(round(c,3) for c in f)
    if key not in COL: continue
    # gather the path vertices
    pts=[]
    for it in dr['items']:
        if it[0]=='l': pts += [it[1],it[2]]
        elif it[0]=='re':
            r=it[1]; pts += [fitz.Point(r.x0,r.y0),fitz.Point(r.x1,r.y0),fitz.Point(r.x1,r.y1),fitz.Point(r.x0,r.y1)]
        elif it[0]=='c': pts += [it[1],it[4]]
    # dedupe preserving order
    seen=[]; 
    for q in pts:
        if not seen or math.hypot(q.x-seen[-1].x,q.y-seen[-1].y)>0.01: seen.append(q)
    if len(seen)<3: continue
    a=0.0
    for i in range(len(seen)):
        x1,y1=seen[i]; x2,y2=seen[(i+1)%len(seen)]
        a += x1*y2-x2*y1
    a=abs(a)/2
    areas[COL[key]] += a
    tris[COL[key]].append((a,[(round(q.x,1),round(q.y,1)) for q in seen]))
print('Triangulated fill areas on p2 SQFT (pts^2):')
tot=0
for k in ['HEATED','GARAGE','REAR PATIO','FRONT PATIO']:
    print(f'   {k:<12} {areas[k]:12.1f} pts^2   ({len(tris[k])} facets)')
    tot+=areas[k]
print(f'   {"TOTAL":<12} {tot:12.1f} pts^2')
print()
SCHED={'HEATED':3246,'GARAGE':1038,'REAR PATIO':1168,'FRONT PATIO':77}
print('Implied pts/ft if these polygons equal the schedule areas:')
for k in ['HEATED','GARAGE','REAR PATIO','FRONT PATIO']:
    print(f'   {k:<12} sqrt({areas[k]:.0f}/{SCHED[k]}) = {math.sqrt(areas[k]/SCHED[k]):7.4f} pts/ft')
print(f'   {"TOTAL":<12} sqrt({tot:.0f}/5529) = {math.sqrt(tot/5529):7.4f} pts/ft')
