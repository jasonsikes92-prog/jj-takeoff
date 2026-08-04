import sys, math, json, collections; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
PPF=18.0; K=1/math.cos(math.radians(45))
VIEWS=[(7,'E1_FRONT',fitz.Rect(95,120,2395,660),649.1),(7,'E3_REAR',fitz.Rect(95,880,2395,1470),1466.5),
       (8,'E2_LEFT',fitz.Rect(500,130,2150,710),706.9),(8,'E4_RIGHT',fitz.Rect(620,860,2000,1495),1493.1)]
# rotated-wing extent expressed in each elevation's own x axis (from master frame 92.20..130.18 in x, 45.33..83.31 in y)
def rot_range(nm):
    if nm=='E1_FRONT': return (92.20,130.18)
    if nm=='E3_REAR':  return (138.39-130.18,138.39-92.20)
    if nm=='E4_RIGHT': return (121.46-83.31,121.46-45.33)
    if nm=='E2_LEFT':  return (45.33+14.72,83.31+14.72)
NAMES={1:'LAP',2:'B&B',3:'STONE'}
Z=5.0
tot={'LAP':0.0,'B&B':0.0,'STONE':0.0}; det=[]; grand=0.0
for pi,nm,clip,grade in VIEWS:
    r=J.gable_area(page=d[pi], ppf=PPF, clip=clip)
    # above-plate texture map for material sampling inside triangles
    up=fitz.Rect(clip.x0, clip.y0, clip.x1, grade-9.5*PPF)
    p=d[pi]; pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z),clip=up)
    img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3]
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    strong=np.hypot(gx,gy)>40
    hl=(strong&(np.abs(gy)>np.abs(gx))); vl=(strong&(np.abs(gx)>=np.abs(gy)))
    lo,hi=rot_range(nm)
    A=r['total_sf']; U=r['unpaired_sf']
    scale_unpaired = (A+U)/A if A>0 else 1.0
    for g in r['gables']:
        ax=g['apex_x']; base=g['base_ft']; rise=g['rise_ft']; a=g['area_sf']*scale_unpaired
        fores = (lo-1 <= ax <= hi+1)
        a_true = a*K if fores else a
        # sample material inside the triangle
        cx=(ax-up.x0/PPF)*PPF*Z
        apex_y_px=(g['apex_y'])  # ft above plate-ish; sample a band under the apex
        x0=int(max(0,cx-base/2*PPF*Z)); x1=int(min(gray.shape[1]-1,cx+base/2*PPF*Z))
        y1=gray.shape[0]-1; y0=int(max(0,y1-rise*PPF*Z))
        H=hl[y0:y1,x0:x1]; V=vl[y0:y1,x0:x1]
        h=int(H.sum()); v=int(V.sum())
        if h+v<50: mat={'LAP':0.30,'B&B':0.60,'STONE':0.10}
        else:
            eh=h/(h+v)
            mat={'LAP':1.0,'B&B':0.0,'STONE':0.0} if eh>0.70 else ({'LAP':0.0,'B&B':1.0,'STONE':0.0} if eh<0.32 else {'LAP':0.0,'B&B':0.0,'STONE':1.0})
        for k in tot: tot[k]+=a_true*mat[k]
        grand+=a_true
        det.append({'elev':nm,'apex_x':ax,'base_ft':base,'rise_ft':rise,'as_drawn_sf':round(a,1),
                    'foreshortened':fores,'true_sf':round(a_true,1),'material':max(mat,key=mat.get)})
print(f"{'elev':<10}{'apex_x':>8}{'base':>7}{'rise':>7}{'drawn SF':>10}{'rot45':>7}{'TRUE SF':>9}  material")
for g in det: print(f"{g['elev']:<10}{g['apex_x']:8.1f}{g['base_ft']:7.1f}{g['rise_ft']:7.1f}{g['as_drawn_sf']:10.1f}{str(g['foreshortened']):>7}{g['true_sf']:9.1f}  {g['material']}")
print(f"\nGABLE TOTAL (incl. unpaired rakes, foreshorten-corrected): {grand:.0f} SF")
print(f"   LAP {tot['LAP']:.0f} | B&B {tot['B&B']:.0f} | STONE {tot['STONE']:.0f}")
json.dump({'gables':det,'total_sf':round(grand,1),'by_material':{k:round(v,1) for k,v in tot.items()}},open('cladding_gables.json','w'),indent=1)
