import sys, math, json, collections; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
Z=5.0; PPF=18.0; PPX=PPF*Z; T=int(0.35*PPX)
# region ABOVE the 10ft plate band, up to the top of the drawing
UP=[(7,'E1_FRONT',649.1,95,2395,120),(7,'E3_REAR',1466.5,95,2395,880),
    (8,'E2_LEFT',706.9,500,2150,130),(8,'E4_RIGHT',1493.1,620,2000,860)]
NAMES={1:'LAP',2:'B&B',3:'STONE',4:'ROOF'}; COLS={1:(0,200,255),2:(255,130,0),3:(170,0,255),4:(60,60,60)}
def blocks(a,T):
    h,w=a.shape; h-=h%T; w-=w%T
    return a[:h,:w].reshape(h//T,T,w//T,T)
res={}
for pi,nm,grade,x0,x1,ytop in UP:
    clip=fitz.Rect(x0, ytop, x1, grade-10.0*PPF)
    p=d[pi]; pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z),clip=clip)
    img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3].copy()
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY); H,W=gray.shape
    ink=(gray<215).astype(np.uint8)
    big=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((int(0.7*PPX)|1,)*2,np.uint8))
    ff=big.copy(); m=np.zeros((H+2,W+2),np.uint8)
    for seed in [(0,0),(W-1,0)]: cv2.floodFill(ff,m,seed,2)
    sil=cv2.morphologyEx((ff!=2).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    strong=np.hypot(gx,gy)>40
    hl=(strong&(np.abs(gy)>np.abs(gx))).astype(np.uint8)
    vl=(strong&(np.abs(gx)>=np.abs(gy))).astype(np.float32)
    # run length of horizontal lines -> long = lap ; short = shingle tabs
    RL=np.zeros(gray.shape,np.float32); mh=(hl>0)
    dd=np.diff(np.pad(mh.astype(np.int8),((0,0),(1,1))),axis=1)
    for y in range(H):
        s=np.where(dd[y]==1)[0]; e=np.where(dd[y]==-1)[0]
        for a,b in zip(s,e): RL[y,a:b]=b-a
    Bh=blocks(hl.astype(np.float32),T).mean(axis=(1,3)); Bv=blocks(vl,T).mean(axis=(1,3))
    Bs=blocks(sil.astype(np.float32),T).mean(axis=(1,3))
    mrun=blocks(RL,T).sum(axis=(1,3))/np.maximum(blocks(mh.astype(np.float32),T).sum(axis=(1,3)),1)
    inside=Bs>0.5; tot=Bh+Bv+1e-9; evh=Bh/tot
    lab=np.zeros(Bh.shape,np.uint8); tex=inside&((Bh+Bv)>0.008)
    lab[tex&(evh>0.70)]=1; lab[tex&(evh<0.32)]=2; lab[tex&(evh>=0.32)&(evh<=0.70)]=3
    lab[(lab==1)&(mrun<1.10*PPX)]=4
    lab[(lab==3)&(mrun<0.55*PPX)&(Bh>Bv)]=4
    unf=int((inside&(lab==0)).sum())
    for _ in range(80):
        holes=inside&(lab==0)
        if not holes.any(): break
        best=np.zeros_like(lab); bc=np.zeros(lab.shape,np.float32)
        for v in NAMES:
            c=cv2.filter2D((lab==v).astype(np.float32),-1,np.ones((3,3),np.float32))
            u=holes&(c>bc); best[u]=v; bc[u]=c[u]
        if not (best>0).any(): break
        lab[holes&(best>0)]=best[holes&(best>0)]
    tsf=(T/PPX)**2; cnt={v:int((lab==v).sum()) for v in NAMES}
    wall=sum(cnt[v] for v in (1,2,3))*tsf
    res[nm]={'upper_silhouette_sf':round(int(inside.sum())*tsf,1),'ROOF_sf':round(cnt[4]*tsf,1),
             'GABLE_wall_sf':round(wall,1),'LAP':round(cnt[1]*tsf,1),'B&B':round(cnt[2]*tsf,1),'STONE':round(cnt[3]*tsf,1),
             'coverage_pct':round(100*(inside&(lab>0)).sum()/max(int(inside.sum()),1),2)}
    ov=img.copy()
    for v in NAMES:
        ys,xs=np.where(lab==v)
        for y,x in zip(ys,xs): cv2.rectangle(ov,(x*T,y*T),((x+1)*T-1,(y+1)*T-1),COLS[v],-1)
    cv2.imwrite(f'evidence/gable_{nm}.png',cv2.cvtColor(cv2.addWeighted(img,0.45,ov,0.55,0),cv2.COLOR_RGB2BGR))
    print(f"{nm:<10} above-plate sil {res[nm]['upper_silhouette_sf']:7.1f}  cov {res[nm]['coverage_pct']:6.2f}%  ROOF {cnt[4]*tsf:7.1f} | GABLE-WALL {wall:7.1f}  (LAP {cnt[1]*tsf:6.1f} B&B {cnt[2]*tsf:6.1f} STONE {cnt[3]*tsf:6.1f})")
json.dump(res,open('gables.json','w'),indent=1)
print(f"\nTOTAL gable/upper wall across 4 elevations: {sum(res[k]['GABLE_wall_sf'] for k in res):.1f} SF")
