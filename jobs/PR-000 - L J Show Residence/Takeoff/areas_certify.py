import sys, math, collections, json, os
sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz, numpy as np, cv2
PDF=r'C:\Users\jason\Downloads\L J show BID SET (1).pdf'
d=fitz.open(PDF); p2=d[1]; PPF=9.0
os.makedirs('evidence',exist_ok=True)
COL={'HEATED':(0.0,1.0,0.0),'GARAGE':(1.0,0.0,0.0),'REAR PATIO':(0.502,0.0,1.0),'FRONT PATIO':(0.0,1.0,1.0)}

# ---------- METHOD A: vector fill-path shoelace on p2 ----------
def facets(ck):
    out=[]
    for dr in p2.get_drawings():
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
        if len(s)>=3: out.append(s)
    return out
def bnd(fs,q=1):
    c=collections.Counter()
    for poly in fs:
        n=len(poly)
        for i in range(n):
            a=(round(poly[i].x,q),round(poly[i].y,q)); b=(round(poly[(i+1)%n].x,q),round(poly[(i+1)%n].y,q))
            if a!=b: c[tuple(sorted([a,b]))]+=1
    return [e for e,k in c.items() if k==1]
def chain(edges):
    adj=collections.defaultdict(list)
    for a,b in edges: adj[a].append(b); adj[b].append(a)
    loops=[];used=set()
    for st in list(adj):
        if st in used: continue
        loop=[st];used.add(st);cur=st;prev=None
        while True:
            nx=[n for n in adj[cur] if n!=prev and n not in used]
            if not nx: break
            loop.append(nx[0]);used.add(nx[0]);prev,cur=cur,nx[0]
        if len(loop)>=3: loops.append(loop)
    return loops
def shoe(l):
    a=0.0
    for i in range(len(l)):
        x1,y1=l[i];x2,y2=l[(i+1)%len(l)]; a+=x1*y2-x2*y1
    return abs(a)/2

VEC={}
for nm,ck in COL.items():
    ls=chain(bnd(facets(ck))); ls.sort(key=shoe,reverse=True)
    VEC[nm]=shoe(ls[0])/PPF**2

# ---------- METHOD B: raster colour-mask pixel count on rendered p2 ----------
ZOOM=4.0; PPX=PPF*ZOOM      # pixels per foot
pix=p2.get_pixmap(matrix=fitz.Matrix(ZOOM,ZOOM))
raw='evidence/p2_render.png'; pix.save(raw)
img=cv2.imread(raw); b,g,r=[img[:,:,i].astype(int) for i in range(3)]
MASKS={
 'HEATED':      (g>110)&(g-r>40)&(g-b>40),
 'GARAGE':      (r>110)&(r-g>45)&(r-b>45),
 'REAR PATIO':  (b>110)&(r>60)&(b-g>45)&(r-g>25)&(b-r>25),
 'FRONT PATIO': (g>110)&(b>110)&(g-r>45)&(b-r>45),
}
RAS={}
for nm,m in MASKS.items():
    mm=(m.astype(np.uint8))*255
    mm=cv2.morphologyEx(mm,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    n,lab,stats,_=cv2.connectedComponentsWithStats(mm,8)
    px=int(stats[1:,cv2.CC_STAT_AREA].sum()) if n>1 else 0
    RAS[nm]=px/PPX**2
    ov=img.copy(); ov[mm>0]=(0,0,255)
    cv2.imwrite(f"evidence/{nm.lower().replace(' ','-')}-verification.png", ov)
    # primary overlay = vector loop drawn
    ov2=img.copy()
    ls=chain(bnd(facets(COL[nm]))); ls.sort(key=shoe,reverse=True)
    poly=np.array([[int(x*ZOOM),int(y*ZOOM)] for x,y in ls[0]],np.int32)
    cv2.polylines(ov2,[poly],True,(255,0,255),3)
    cv2.imwrite(f"evidence/{nm.lower().replace(' ','-')}-primary.png", ov2)

print(f"{'component':<14}{'vector shoelace':>17}{'raster mask':>14}{'delta':>9}")
for nm in COL:
    dv=abs(VEC[nm]-RAS[nm])/RAS[nm]*100
    print(f'{nm:<14}{VEC[nm]:14.1f} SF{RAS[nm]:11.1f} SF{dv:8.2f}%')
json.dump({'vector':VEC,'raster':RAS,'ppf':PPF,'ppx':PPX},open('areas.json','w'),indent=1)
