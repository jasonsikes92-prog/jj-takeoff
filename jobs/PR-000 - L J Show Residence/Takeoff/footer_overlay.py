import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
from shapely.geometry import Polygon
from shapely.ops import unary_union
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[1]; PPF=9.0; Z=4.0
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
        if len(s)>=3: out.append([(q.x,q.y) for q in s])   # keep PAGE points
    return out
def U(nm):
    ps=[Polygon(f).buffer(0) for f in facets(COL[nm])]
    u=unary_union([q for q in ps if q.is_valid and q.area>0.01])
    return u if u.geom_type=='Polygon' else max(u.geoms,key=lambda q:q.area)
H,G,RP,FP=U('HEATED'),U('GARAGE'),U('REAR PORCH'),U('FRONT PORCH')
env=unary_union([H,G]).buffer(0.30*PPF).buffer(-0.30*PPF)
env=env if env.geom_type=='Polygon' else max(env.geoms,key=lambda q:q.area)
clip=fitz.Rect(1050,330,2350,1180)
pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z), clip=clip)
img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3].copy()
img=cv2.cvtColor(img,cv2.COLOR_RGB2BGR)
def draw(geom,color,thick,label=None,dash=False):
    co=list(geom.exterior.coords)
    pts=[(int((x-clip.x0)*Z),int((y-clip.y0)*Z)) for x,y in co]
    for i in range(len(pts)-1):
        if dash and i%2: continue
        cv2.line(img,pts[i],pts[i+1],color,thick,cv2.LINE_AA)
    if label:
        cx=int(sum(q[0] for q in pts)/len(pts)); cy=int(sum(q[1] for q in pts)/len(pts))
        cv2.putText(img,label,(cx-120,cy),cv2.FONT_HERSHEY_SIMPLEX,0.85,(0,0,0),5,cv2.LINE_AA)
        cv2.putText(img,label,(cx-120,cy),cv2.FONT_HERSHEY_SIMPLEX,0.85,color,2,cv2.LINE_AA)
draw(env,(0,0,230),5,'ENVELOPE 393.00 LF')
draw(RP,(200,0,200),5,'REAR PORCH 203.34 LF')
draw(FP,(0,150,0),5,'FRONT PORCH 44.85 LF')
draw(G,(120,120,120),2,None,dash=True)
y0=30
for t,c in [('FOOTER LF = envelope + FULL porch outlines',(0,0,0)),
            ('  envelope (house+garage, one pour)   393.00',(0,0,230)),
            ('  rear porch full outline             203.34',(200,0,200)),
            ('  front porch full outline             44.85',(0,150,0)),
            ('  TOTAL                               641.19  (Jason 635)',(0,0,0))]:
    cv2.putText(img,t,(18,y0),cv2.FONT_HERSHEY_SIMPLEX,0.78,(255,255,255),6,cv2.LINE_AA)
    cv2.putText(img,t,(18,y0),cv2.FONT_HERSHEY_SIMPLEX,0.78,c,2,cv2.LINE_AA)
    y0+=34
cv2.imwrite('evidence/footer_lines.png',img)
print('overlay written')
print(f'envelope    {env.exterior.length/PPF:8.2f} LF')
print(f'rear porch  {RP.exterior.length/PPF:8.2f} LF')
print(f'front porch {FP.exterior.length/PPF:8.2f} LF')
print(f'TOTAL       {(env.exterior.length+RP.exterior.length+FP.exterior.length)/PPF:8.2f} LF')
