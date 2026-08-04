import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
Z=4.0; PPF=18.0; PPX=PPF*Z; T=int(0.40*PPX)
VIEWS=[(7,'E1_FRONT',fitz.Rect(95,120,2395,700)),(7,'E3_REAR',fitz.Rect(95,760,2395,1340)),
       (8,'E2_LEFT',fitz.Rect(500,120,2150,770)),(8,'E4_RIGHT',fitz.Rect(620,830,2000,1410))]
NAMES={1:'LAP',2:'B&B',3:'STONE',4:'ROOF'}
COLS={1:(0,200,255),2:(255,130,0),3:(170,0,255),4:(50,50,50)}
def blocks(a,T):
    h,w=a.shape; h-=h%T; w-=w%T
    return a[:h,:w].reshape(h//T,T,w//T,T)
def runlen_rows(mask):
    """per-pixel horizontal run length"""
    out=np.zeros(mask.shape,np.float32); H,W=mask.shape
    m=mask.astype(np.int8)
    d=np.diff(np.pad(m,((0,0),(1,1))),axis=1)
    for y in range(H):
        s=np.where(d[y]==1)[0]; e=np.where(d[y]==-1)[0]
        if len(s)==0: continue
        for a,b in zip(s,e): out[y,a:b]=b-a
    return out
res={}
for pi,nm,clip in VIEWS:
    p=d[pi]; pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z),clip=clip)
    img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3].copy()
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY); H,W=gray.shape
    ink=(gray<210).astype(np.uint8)
    big=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((int(0.9*PPX)|1,)*2,np.uint8))
    ff=big.copy(); m=np.zeros((H+2,W+2),np.uint8); cv2.floodFill(ff,m,(0,0),2)
    sil=cv2.morphologyEx((ff!=2).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    n,lb,st,_=cv2.connectedComponentsWithStats(sil,8)
    if n>1:
        keep=[i for i in range(1,n) if st[i,cv2.CC_STAT_AREA]>(2.0*PPX*PPX)]
        sil=np.isin(lb,keep).astype(np.uint8)
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    strong=np.hypot(gx,gy)>40
    hline=(strong&(np.abs(gy)>np.abs(gx))).astype(np.uint8)
    vline=(strong&(np.abs(gx)>=np.abs(gy))).astype(np.uint8)
    RL=runlen_rows(hline>0)                       # long runs = lap; short = shingle tabs
    Bh=blocks(hline.astype(np.float32),T).mean(axis=(1,3))
    Bv=blocks(vline.astype(np.float32),T).mean(axis=(1,3))
    Bs=blocks(sil.astype(np.float32),T).mean(axis=(1,3))
    RLb=blocks(RL,T); msk=blocks((hline>0).astype(np.float32),T)
    meanrun=RLb.sum(axis=(1,3))/np.maximum(msk.sum(axis=(1,3)),1)   # px
    inside=Bs>0.5; tot=Bh+Bv+1e-9; evh=Bh/tot
    lab=np.zeros(Bh.shape,np.uint8)
    tex=inside&((Bh+Bv)>0.010)
    lab[tex&(evh>0.72)]=1
    lab[tex&(evh<0.30)]=2
    lab[tex&(evh>=0.30)&(evh<=0.72)]=3
    lab[(lab==1)&(meanrun < 0.95*PPX)] = 4        # broken horizontal courses -> ROOF shingle
    unf0=int((inside&(lab==0)).sum())
    for _ in range(80):
        holes=inside&(lab==0)
        if not holes.any(): break
        best=np.zeros_like(lab); bc=np.zeros(lab.shape,np.float32)
        for v in NAMES:
            c=cv2.filter2D((lab==v).astype(np.float32),-1,np.ones((3,3),np.float32))
            u=holes&(c>bc); best[u]=v; bc[u]=c[u]
        if not (best>0).any(): break
        lab[holes&(best>0)]=best[holes&(best>0)]
    tsf=(T/PPX)**2; ins=int(inside.sum())
    cnt={v:int((lab==v).sum()) for v in NAMES}
    wall=sum(cnt[v] for v in (1,2,3))*tsf
    res[nm]={'silhouette_sf':round(ins*tsf,1),'coverage_pct':round(100*(inside&(lab>0)).sum()/max(ins,1),2),
             'unclassified_before_fill_sf':round(unf0*tsf,1),'WALL_total_sf':round(wall,1),
             **{NAMES[v]:round(cnt[v]*tsf,1) for v in NAMES}}
    ov=img.copy()
    for v in NAMES:
        ys,xs=np.where(lab==v)
        for y,x in zip(ys,xs): cv2.rectangle(ov,(x*T,y*T),((x+1)*T-1,(y+1)*T-1),COLS[v],-1)
    cv2.imwrite(f'evidence/tex4_{nm}.png',cv2.cvtColor(cv2.addWeighted(img,0.45,ov,0.55,0),cv2.COLOR_RGB2BGR))
    print(f"{nm:<10} sil {ins*tsf:7.1f} cov {res[nm]['coverage_pct']:6.2f}%  ROOF {cnt[4]*tsf:7.1f} | WALL {wall:7.1f}  (LAP {cnt[1]*tsf:6.1f} B&B {cnt[2]*tsf:6.1f} STONE {cnt[3]*tsf:6.1f})")
json.dump(res,open('texture_split.json','w'),indent=1)
