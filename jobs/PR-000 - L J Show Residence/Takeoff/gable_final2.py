import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
PPF=18.0; K=1/math.cos(math.radians(45)); Z=5.0
VIEWS=[(7,'E1_FRONT',fitz.Rect(95,120,2395,660)),(7,'E3_REAR',fitz.Rect(95,880,2395,1470)),
       (8,'E2_LEFT',fitz.Rect(500,130,2150,710)),(8,'E4_RIGHT',fitz.Rect(620,860,2000,1495))]
def rot_range(nm):
    return {'E1_FRONT':(92.20,130.18),'E3_REAR':(138.39-130.18,138.39-92.20),
            'E4_RIGHT':(121.46-83.31,121.46-45.33),'E2_LEFT':(45.33+14.72,83.31+14.72)}[nm]
tot={'LAP':0.0,'B&B':0.0,'STONE':0.0}; det=[]; grand=0.0
for pi,nm,clip in VIEWS:
    r=J.gable_area(page=d[pi], ppf=PPF, clip=clip)
    p=d[pi]; pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z),clip=clip)
    img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3]
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    strong=np.hypot(gx,gy)>40
    hl=(strong&(np.abs(gy)>np.abs(gx))).astype(np.uint8)
    vl=(strong&(np.abs(gx)>=np.abs(gy))).astype(np.uint8)
    lo,hi=rot_range(nm); A=r['total_sf']; U=r['unpaired_sf']
    sc=(A+U)/A if A>0 else 1.0
    for g in r['gables']:
        ax,ay,base,rise=g['apex_x'],g['apex_y'],g['base_ft'],g['rise_ft']
        a=g['area_sf']*sc
        fores=(lo-1<=ax<=hi+1); a_true=a*K if fores else a
        # triangle in crop pixels
        px=(ax*PPF-clip.x0)*Z; py=(ay*PPF-clip.y0)*Z
        hw=(base/2)*PPF*Z; hgt=rise*PPF*Z
        tri=np.array([[px,py],[px-hw,py+hgt],[px+hw,py+hgt]],np.int32)
        mask=np.zeros(gray.shape,np.uint8); cv2.fillPoly(mask,[tri],1)
        mask=cv2.erode(mask,np.ones((9,9),np.uint8))     # stay inside the rakes
        h=int((hl&mask).sum()); v=int((vl&mask).sum()); tt=h+v
        if tt<80: mat={'LAP':0.30,'B&B':0.60,'STONE':0.10}; conf='low'
        else:
            eh=h/tt; conf='ok'
            if eh>0.70: mat={'LAP':1.0,'B&B':0.0,'STONE':0.0}
            elif eh<0.32: mat={'LAP':0.0,'B&B':1.0,'STONE':0.0}
            else: mat={'LAP':0.0,'B&B':0.0,'STONE':1.0}
        for k in tot: tot[k]+=a_true*mat[k]
        grand+=a_true
        det.append({'elev':nm,'apex_x':round(ax,1),'base_ft':base,'rise_ft':rise,'as_drawn_sf':round(a,1),
                    'rot45':fores,'true_sf':round(a_true,1),'material':max(mat,key=mat.get),'evh':round(h/tt,3) if tt else None,'conf':conf})
print(f"{'elev':<10}{'apex_x':>8}{'base':>7}{'rise':>7}{'drawn':>9}{'rot45':>7}{'TRUE SF':>9}{'evh':>7}  material")
for g in det: print(f"{g['elev']:<10}{g['apex_x']:8.1f}{g['base_ft']:7.1f}{g['rise_ft']:7.1f}{g['as_drawn_sf']:9.1f}{str(g['rot45']):>7}{g['true_sf']:9.1f}{(g['evh'] if g['evh'] is not None else 0):7.2f}  {g['material']}")
print(f"\nGABLE TOTAL {grand:.0f} SF   LAP {tot['LAP']:.0f} | B&B {tot['B&B']:.0f} | STONE {tot['STONE']:.0f}")
json.dump({'gables':det,'total_sf':round(grand,1),'by_material':{k:round(v,1) for k,v in tot.items()}},open('cladding_gables.json','w'),indent=1)
