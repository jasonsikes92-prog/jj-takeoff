import sys, math, json, pickle, collections; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import numpy as np
W=json.load(open('walls_master.json')); MAPS=pickle.load(open('labelmaps.pkl','rb'))
NAMES={1:'LAP',2:'B&B',3:'STONE'}
# ---- outward normal: envelope ring; use signed area to fix handedness
pts=[tuple(s['a']) for s in W]
A=0.0
for i in range(len(pts)):
    x1,y1=pts[i]; x2,y2=pts[(i+1)%len(pts)]; A+=x1*y2-x2*y1
ccw = A>0
for s in W:
    dx=s['b'][0]-s['a'][0]; dy=s['b'][1]-s['a'][1]; L=math.hypot(dx,dy)
    nx,ny=(dy/L,-dx/L) if ccw else (-dy/L,dx/L)
    s['n']=[round(nx,4),round(ny,4)]
# view directions (unit vectors FROM viewer INTO the building), master frame (y down)
#  E1 FRONT viewer at +y looking -y ; E3 REAR viewer at -y ; E4 RIGHT viewer at +x ; E2 LEFT viewer at -x
VIEW={'E1_FRONT':(0,-1),'E3_REAR':(0,1),'E4_RIGHT':(-1,0),'E2_LEFT':(1,0)}
# elevation x-axis mapping: master coord -> elevation feet
def to_elev(nm, x, y):
    if nm=='E1_FRONT':  return x
    if nm=='E3_REAR':   return 138.39 - x
    if nm=='E4_RIGHT':  return 121.46 - y
    if nm=='E2_LEFT':   return y + 14.72        # direct: master_y = elev_ft - 14.72
    raise KeyError(nm)
H_GAR=10.975; H_MAIN=11.2
def wall_height(s):
    return H_GAR if s['ang'] in (45,135,136) else H_MAIN
def sample(nm, e0, e1):
    """material fractions over elevation-ft span [e0,e1] within the wall band"""
    M=MAPS[nm]; lab=M['lab']; ins=M['inside']; T=M['T']; PPX=M['PPX']; x0=M['x0_pt']
    c0=int(((min(e0,e1)*18.0)-x0)*(PPX/18.0)/T); c1=int(((max(e0,e1)*18.0)-x0)*(PPX/18.0)/T)
    c0=max(0,min(lab.shape[1]-1,c0)); c1=max(0,min(lab.shape[1]-1,c1))
    if c1<c0: c0,c1=c1,c0
    sub=lab[:,c0:c1+1]; si=ins[:,c0:c1+1]
    cnt={v:int(((sub==v)&si).sum()) for v in NAMES}
    tot=sum(cnt.values())
    if tot==0: return None
    return {NAMES[v]:cnt[v]/tot for v in NAMES}
rows=[]; tot_by={'LAP':0.0,'B&B':0.0,'STONE':0.0}
for s in W:
    nx,ny=s['n']; L=s['len']; h=wall_height(s); area=L*h
    seen=[(nm,-(nx*v[0]+ny*v[1])) for nm,v in VIEW.items()]
    seen=[(nm,d) for nm,d in seen if d>0.30]
    seen.sort(key=lambda t:-t[1])
    frac=None; used=None
    for nm,dpr in seen:
        e0=to_elev(nm,*s['a']); e1=to_elev(nm,*s['b'])
        f=sample(nm,e0,e1)
        if f: frac=f; used=nm; break
    if frac is None:
        frac={'LAP':0.264,'B&B':0.603,'STONE':0.134}; used='HIDDEN->global ratio'
    for k in tot_by: tot_by[k]+=area*frac[k]
    rows.append({'w':s['i'],'lf':L,'brg':s['ang'],'ht':h,'area_sf':round(area,1),'elev':used,
                 **{k:round(area*frac[k],1) for k in NAMES.values()}})
print(f"{'wall':<6}{'LF':>7}{'brg':>5}{'ht':>7}{'gross SF':>10}  {'elev':<12}{'LAP':>8}{'B&B':>8}{'STONE':>8}")
for r in rows:
    print(f"w{r['w']:<5}{r['lf']:7.2f}{r['brg']:5d}{r['ht']:7.2f}{r['area_sf']:10.1f}  {r['elev']:<12}{r['LAP']:8.1f}{r['B&B']:8.1f}{r['STONE']:8.1f}")
g=sum(r['area_sf'] for r in rows)
print(f"\nWALL BAND TOTAL {g:.0f} SF   LAP {tot_by['LAP']:.0f} | B&B {tot_by['B&B']:.0f} | STONE {tot_by['STONE']:.0f}")
json.dump({'rows':rows,'band_total_sf':round(g,1),'band_by_material':{k:round(v,1) for k,v in tot_by.items()}},open('cladding_walls.json','w'),indent=1)
