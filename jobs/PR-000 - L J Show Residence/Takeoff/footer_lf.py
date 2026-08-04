import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
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
H,G,RP,FP=U('HEATED'),U('GARAGE'),U('REAR PORCH'),U('FRONT PORCH')
def seam(a,b,tol=0.6):
    """shared boundary length between two abutting slabs"""
    return round(a.exterior.intersection(b.buffer(tol)).length, 2)
print('SLAB PERIMETERS (measured)')
for nm,g in [('HEATED',H),('GARAGE',G),('REAR PORCH',RP),('FRONT PORCH',FP)]:
    print(f'   {nm:<13}{g.area:9.1f} SF   perimeter {g.exterior.length:8.2f} LF')
env=unary_union([H,G]).buffer(0.30).buffer(-0.30)
env=env if env.geom_type=='Polygon' else max(env.geoms,key=lambda q:q.area)
print(f'\n   heated+garage merged envelope perimeter {env.exterior.length:8.2f} LF')
gs=(H.exterior.length+G.exterior.length-env.exterior.length)/2.0
print(f'\nINTERFACE (transition) LINES -- each gets a footer:')
print(f'   garage  <-> house  {gs:8.2f} LF   (dissolved by the union: (P_h+P_g-P_env)/2)')
rs=seam(RP,unary_union([H,G])); fs=seam(FP,unary_union([H,G]))
print(f'   rear porch <-> house {rs:7.2f} LF')
print(f'   front porch<-> house {fs:7.2f} LF')
tot_if=gs+rs+fs
print(f'   TOTAL interface       {tot_if:7.2f} LF')
print()
FOOTER = env.exterior.length + tot_if
print(f'FOOTER LF = envelope {env.exterior.length:.2f} + interfaces {tot_if:.2f} = {FOOTER:.2f} LF')
print(f'   Jason actual                                  = 635.00 LF')
print(f'   delta                                         = {FOOTER-635.0:+.2f} LF  ({100*(FOOTER-635)/635:+.1f}%)')
json.dump({'envelope_lf':round(env.exterior.length,2),'garage_seam_lf':round(gs,2),
           'rear_porch_seam_lf':rs,'front_porch_seam_lf':fs,'footer_lf':round(FOOTER,2)},
          open('footer_lf.json','w'), indent=1)
