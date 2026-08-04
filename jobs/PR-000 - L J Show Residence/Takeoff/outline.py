import sys, math, collections; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[1]
COL={(0.0,1.0,0.0):'HEATED',(1.0,0.0,0.0):'GARAGE',(0.502,0.0,1.0):'REAR_PATIO',(0.0,1.0,1.0):'FRONT_PATIO'}
PPF=9.0
def facets(color_key):
    out=[]
    for dr in p.get_drawings():
        f=dr.get('fill')
        if f is None: continue
        if tuple(round(c,3) for c in f)!=color_key: continue
        pts=[]
        for it in dr['items']:
            if it[0]=='l': pts += [it[1],it[2]]
            elif it[0]=='re':
                r=it[1]; pts += [fitz.Point(r.x0,r.y0),fitz.Point(r.x1,r.y0),fitz.Point(r.x1,r.y1),fitz.Point(r.x0,r.y1)]
        seen=[]
        for q in pts:
            if not seen or math.hypot(q.x-seen[-1].x,q.y-seen[-1].y)>0.01: seen.append(q)
        if len(seen)>=3: out.append(seen)
    return out

def boundary(fs, q=1):
    """Edges appearing once = boundary of the union."""
    cnt=collections.Counter()
    for poly in fs:
        n=len(poly)
        for i in range(n):
            a=(round(poly[i].x,q),round(poly[i].y,q)); b=(round(poly[(i+1)%n].x,q),round(poly[(i+1)%n].y,q))
            if a==b: continue
            cnt[tuple(sorted([a,b]))]+=1
    return [e for e,c in cnt.items() if c==1]

def chain(edges):
    adj=collections.defaultdict(list)
    for a,b in edges: adj[a].append(b); adj[b].append(a)
    loops=[]; used=set()
    for start in list(adj):
        if start in used: continue
        loop=[start]; used.add(start); cur=start; prev=None
        while True:
            nxts=[n for n in adj[cur] if n!=prev and n not in used]
            if not nxts:
                if start in adj[cur] and len(loop)>2: pass
                break
            nxt=nxts[0]; loop.append(nxt); used.add(nxt); prev,cur=cur,nxt
        if len(loop)>=3: loops.append(loop)
    return loops

def shoelace(loop):
    a=0.0
    for i in range(len(loop)):
        x1,y1=loop[i]; x2,y2=loop[(i+1)%len(loop)]
        a+=x1*y2-x2*y1
    return abs(a)/2

for key,name in COL.items():
    fs=facets(key)
    ed=boundary(fs)
    loops=chain(ed)
    loops.sort(key=shoelace, reverse=True)
    tot=sum(shoelace(l) for l in loops)
    print(f'=== {name}: {len(fs)} facets, {len(ed)} boundary edges, {len(loops)} loop(s)')
    for l in loops[:3]:
        print(f'    loop {len(l)} verts  area {shoelace(l)/PPF**2:9.1f} SF')
    print(f'    TOTAL outline area = {tot/PPF**2:9.1f} SF')
    if name in ('GARAGE','FRONT_PATIO') and loops:
        L=loops[0]
        print('    edges (ft):', [round(math.hypot(L[(i+1)%len(L)][0]-L[i][0], L[(i+1)%len(L)][1]-L[i][1])/PPF,2) for i in range(len(L))])
    print()

print('='*70); print('HEATED main loop edge list (ft) @ 9.0 pts/ft'); print('='*70)
fs=facets((0.0,1.0,0.0)); loops=chain(boundary(fs)); loops.sort(key=shoelace,reverse=True)
L=loops[0]
import math
edges=[]
for i in range(len(L)):
    a=L[i]; b=L[(i+1)%len(L)]
    dx,dy=b[0]-a[0],b[1]-a[1]
    ln=math.hypot(dx,dy)/PPF
    ang=round(math.degrees(math.atan2(dy,dx)),1)
    edges.append((round(ln,3), ang))
for i,(ln,ang) in enumerate(edges): print(f'  e{i:<3} {ln:8.3f} ft   bearing {ang:7.1f} deg')
print(f'  PERIMETER = {sum(e[0] for e in edges):.2f} LF   AREA = {shoelace(L)/PPF**2:.1f} SF')
