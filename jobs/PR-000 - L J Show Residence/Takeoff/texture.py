import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
Z=4.0; PPF=18.0; PPX=PPF*Z            # px per ft
VIEWS=[(7,'E1_FRONT',fitz.Rect(95,120,2395,700)),(7,'E3_REAR',fitz.Rect(95,760,2395,1340)),
       (8,'E2_LEFT',fitz.Rect(500,120,2150,770)),(8,'E4_RIGHT',fitz.Rect(620,830,2000,1410))]
TILE=int(0.45*PPX)          # ~0.45 ft tiles
def classify(pi,nm,clip):
    p=d[pi]
    pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z), clip=clip)
    img=np.frombuffer(pm.samples,dtype=np.uint8).reshape(pm.height,pm.width,pm.n)
    gray=cv2.cvtColor(img[:,:,:3],cv2.COLOR_RGB2GRAY)
    H,W=gray.shape
    ink=(gray<205).astype(np.uint8)
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    lab=np.zeros((H//TILE, W//TILE),np.uint8)   # 0 empty 1 lap 2 bnb 3 stone/other
    meta=np.zeros_like(lab,np.float32)
    for ty in range(lab.shape[0]):
        for tx in range(lab.shape[1]):
            ys,xs=slice(ty*TILE,(ty+1)*TILE), slice(tx*TILE,(tx+1)*TILE)
            gxx=gx[ys,xs]; gyy=gy[ys,xs]; ii=ink[ys,xs]
            dens=ii.mean()
            if dens<0.02 or dens>0.85: continue
            mag=np.hypot(gxx,gyy); sel=mag>40
            if sel.sum()<TILE: continue
            # gradient of a HORIZONTAL line is vertical (gy dominant)
            evh=(np.abs(gyy[sel])>np.abs(gxx[sel])).mean()
            meta[ty,tx]=dens
            if evh>0.78: lab[ty,tx]=1        # horizontal lines -> lap / shingle
            elif evh<0.22: lab[ty,tx]=2      # vertical lines  -> board&batten
            else: lab[ty,tx]=3               # mixed -> stone
    return img,gray,lab,meta,clip
COLS={1:(0,180,255),2:(255,120,0),3:(0,0,255)}
summary={}
for pi,nm,clip in VIEWS:
    img,gray,lab,meta,clip=classify(pi,nm,clip)
    ov=img[:,:,:3].copy()
    cnt={1:0,2:0,3:0}
    for ty in range(lab.shape[0]):
        for tx in range(lab.shape[1]):
            v=lab[ty,tx]
            if v==0: continue
            cnt[v]+=1
            cv2.rectangle(ov,(tx*TILE,ty*TILE),((tx+1)*TILE-1,(ty+1)*TILE-1),COLS[v],-1)
    blend=cv2.addWeighted(img[:,:,:3],0.55,ov,0.45,0)
    cv2.imwrite(f'evidence/tex_{nm}.png',cv2.cvtColor(blend,cv2.COLOR_RGB2BGR))
    tile_sf=(TILE/PPX)**2
    summary[nm]={'lap_or_shingle_sf':round(cnt[1]*tile_sf,1),'bnb_sf':round(cnt[2]*tile_sf,1),'stone_sf':round(cnt[3]*tile_sf,1)}
    print(f'{nm:<10} horiz-line(lap+shingle) {cnt[1]*tile_sf:8.1f} SF | vert-line(B&B) {cnt[2]*tile_sf:8.1f} SF | mixed(stone) {cnt[3]*tile_sf:8.1f} SF')
json.dump(summary,open('texture_raw.json','w'),indent=1)
