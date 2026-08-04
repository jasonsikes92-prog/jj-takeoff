import sys, math, json, pickle; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
Z=6.0; PPF=18.0; PPX=PPF*Z; T=int(0.30*PPX)
BANDS=[(7,'E1_FRONT',649.1,95,2395),(7,'E3_REAR',1466.5,95,2395),(8,'E2_LEFT',706.9,500,2150),(8,'E4_RIGHT',1493.1,620,2000)]
NAMES={1:'LAP',2:'B&B',3:'STONE'}
def blocks(a,T):
    h,w=a.shape; h-=h%T; w-=w%T
    return a[:h,:w].reshape(h//T,T,w//T,T)
MAPS={}
for pi,nm,grade,x0,x1 in BANDS:
    clip=fitz.Rect(x0, grade-10.0*PPF, x1, grade-0.05*PPF)
    p=d[pi]; pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z),clip=clip)
    img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3].copy()
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY); H,W=gray.shape
    ink=(gray<215).astype(np.uint8)
    big=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((int(0.7*PPX)|1,)*2,np.uint8))
    ff=big.copy(); m=np.zeros((H+2,W+2),np.uint8)
    cv2.floodFill(ff,m,(0,0),2); cv2.floodFill(ff,m,(W-1,0),2)
    sil=cv2.morphologyEx((ff!=2).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    strong=np.hypot(gx,gy)>40
    hl=(strong&(np.abs(gy)>np.abs(gx))).astype(np.float32)
    vl=(strong&(np.abs(gx)>=np.abs(gy))).astype(np.float32)
    Bh=blocks(hl,T).mean(axis=(1,3)); Bv=blocks(vl,T).mean(axis=(1,3)); Bs=blocks(sil.astype(np.float32),T).mean(axis=(1,3))
    inside=Bs>0.5; tot=Bh+Bv+1e-9; evh=Bh/tot
    lab=np.zeros(Bh.shape,np.uint8); tex=inside&((Bh+Bv)>0.008)
    lab[tex&(evh>0.70)]=1; lab[tex&(evh<0.32)]=2; lab[tex&(evh>=0.32)&(evh<=0.70)]=3
    for _ in range(80):
        holes=inside&(lab==0)
        if not holes.any(): break
        best=np.zeros_like(lab); bc=np.zeros(lab.shape,np.float32)
        for v in NAMES:
            c=cv2.filter2D((lab==v).astype(np.float32),-1,np.ones((3,3),np.float32))
            u=holes&(c>bc); best[u]=v; bc[u]=c[u]
        if not (best>0).any(): break
        lab[holes&(best>0)]=best[holes&(best>0)]
    MAPS[nm]={'lab':lab,'inside':inside,'x0_pt':x0,'T':T,'PPX':PPX,'grade':grade}
    print(f'{nm}: label map {lab.shape}  tiles inside {int(inside.sum())}')
pickle.dump(MAPS,open('labelmaps.pkl','wb'))
