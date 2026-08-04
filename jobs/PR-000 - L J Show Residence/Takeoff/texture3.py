import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
Z=4.0; PPF=18.0; PPX=PPF*Z
VIEWS=[(7,'E1_FRONT',fitz.Rect(95,120,2395,700)),(7,'E3_REAR',fitz.Rect(95,760,2395,1340)),
       (8,'E2_LEFT',fitz.Rect(500,120,2150,770)),(8,'E4_RIGHT',fitz.Rect(620,830,2000,1410))]
T=int(0.40*PPX)
NAMES={1:'LAP',2:'B&B',3:'STONE',4:'SHINGLE-roof',5:'METAL-roof'}
COLS={1:(0,200,255),2:(255,130,0),3:(160,0,255),4:(60,60,60),5:(0,230,0)}
def blocks(a,T):
    h,w=a.shape; h-=h%T; w-=w%T
    return a[:h,:w].reshape(h//T,T,w//T,T)
out={}
for pi,nm,clip in VIEWS:
    p=d[pi]; pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z),clip=clip)
    img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3].copy()
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY); H,W=gray.shape
    ink=(gray<210).astype(np.uint8)
    # ---- SILHOUETTE: close the drawing, flood from border, invert -> every px of the building
    big=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((int(0.9*PPX)|1,int(0.9*PPX)|1),np.uint8))
    ff=big.copy(); m=np.zeros((H+2,W+2),np.uint8); cv2.floodFill(ff,m,(0,0),2)
    sil=(ff!=2).astype(np.uint8)
    sil=cv2.morphologyEx(sil,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    n,lb,st,_=cv2.connectedComponentsWithStats(sil,8)
    if n>1:
        keep=[i for i in range(1,n) if st[i,cv2.CC_STAT_AREA] > (2.0*PPX*PPX)]
        sil=np.isin(lb,keep).astype(np.uint8)
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    mag=np.hypot(gx,gy); strong=(mag>40)
    hgrad=(strong&(np.abs(gy)>np.abs(gx))).astype(np.float32)   # horizontal LINES
    vgrad=(strong&(np.abs(gx)>=np.abs(gy))).astype(np.float32)  # vertical LINES
    # short vertical ticks (shingle butt joints) -- vectorised via CC stats
    ve=((np.abs(gx)>60)&(np.abs(gx)>np.abs(gy)*1.6)).astype(np.uint8)
    n2,lb2,st2,_=cv2.connectedComponentsWithStats(ve,8)
    if n2>1:
        hh=st2[:,cv2.CC_STAT_HEIGHT]; ww=st2[:,cv2.CC_STAT_WIDTH]
        ok=np.zeros(n2,bool); ok[1:]=(hh[1:]<0.42*PPX)&(ww[1:]<0.18*PPX)
        tick=ok[lb2].astype(np.float32)
    else: tick=np.zeros_like(gray,np.float32)
    Bh=blocks(hgrad,T).mean(axis=(1,3)); Bv=blocks(vgrad,T).mean(axis=(1,3))
    Bt=blocks(tick,T).mean(axis=(1,3));  Bs=blocks(sil.astype(np.float32),T).mean(axis=(1,3))
    Bi=blocks(ink.astype(np.float32),T).mean(axis=(1,3))
    inside = Bs>0.5
    tot=Bh+Bv+1e-9; evh=Bh/tot
    lab=np.zeros(Bh.shape,np.uint8)
    textured = inside & ((Bh+Bv)>0.010)
    lab[textured & (evh>0.72)] = 1
    lab[textured & (evh<0.30)] = 2
    lab[textured & (evh>=0.30) & (evh<=0.72)] = 3
    lab[(lab==1) & (Bt>0.006)] = 4                      # staggered butts -> shingle
    # ---- FILL every remaining inside tile from its nearest classified neighbour (no silent drops)
    unfilled0=int((inside&(lab==0)).sum())
    for _ in range(60):
        holes = inside & (lab==0)
        if not holes.any(): break
        best=np.zeros_like(lab); bestc=np.zeros(lab.shape,np.int16)
        for v in NAMES:
            cnt=cv2.dilate((lab==v).astype(np.uint8),np.ones((3,3),np.uint8))
            cntf=cv2.filter2D((lab==v).astype(np.float32),-1,np.ones((3,3),np.float32))
            upd=holes&(cntf>bestc)
            best[upd]=v; bestc[upd]=cntf[upd].astype(np.int16)
        if not (best>0).any(): break
        lab[holes&(best>0)]=best[holes&(best>0)]
    tsf=(T/PPX)**2
    ins=int(inside.sum()); filled=int((inside&(lab>0)).sum())
    cnt={v:int((lab==v).sum()) for v in NAMES}
    out[nm]={'silhouette_sf':round(ins*tsf,1),'coverage_pct':round(100*filled/max(ins,1),2),
             'initially_unclassified_sf':round(unfilled0*tsf,1),
             **{NAMES[v]:round(cnt[v]*tsf,1) for v in NAMES}}
    ov=img.copy()
    for v in NAMES:
        ys,xs=np.where(lab==v)
        for y,x in zip(ys,xs): cv2.rectangle(ov,(x*T,y*T),((x+1)*T-1,(y+1)*T-1),COLS[v],-1)
    cv2.imwrite(f'evidence/tex3_{nm}.png',cv2.cvtColor(cv2.addWeighted(img,0.5,ov,0.5,0),cv2.COLOR_RGB2BGR))
    print(f"{nm:<10} silhouette {out[nm]['silhouette_sf']:8.1f} SF  coverage {out[nm]['coverage_pct']:6.2f}%  "
          + ' | '.join(f'{NAMES[v]} {cnt[v]*tsf:7.1f}' for v in NAMES))
json.dump(out,open('texture_split.json','w'),indent=1)
