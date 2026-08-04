import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
Z=4.0; PPF=18.0; PPX=PPF*Z
VIEWS=[(7,'E1_FRONT',fitz.Rect(95,120,2395,700)),(7,'E3_REAR',fitz.Rect(95,760,2395,1340)),
       (8,'E2_LEFT',fitz.Rect(500,120,2150,770)),(8,'E4_RIGHT',fitz.Rect(620,830,2000,1410))]
TILE=int(0.45*PPX)
# class: 1 lap  2 bnb  3 stone  4 shingle(roof)  5 metal(roof, smooth/ribbed)
NAMES={1:'LAP',2:'B&B',3:'STONE',4:'SHINGLE-roof',5:'METAL-roof'}
COLS={1:(0,200,255),2:(255,120,0),3:(160,0,255),4:(0,90,90),5:(0,255,0)}
res={}
for pi,nm,clip in VIEWS:
    p=d[pi]
    pm=p.get_pixmap(matrix=fitz.Matrix(Z,Z),clip=clip)
    img=np.frombuffer(pm.samples,np.uint8).reshape(pm.height,pm.width,pm.n)[:,:,:3]
    gray=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY); H,W=gray.shape
    ink=(gray<205).astype(np.uint8)
    gx=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray.astype(np.float32),cv2.CV_32F,0,1,ksize=3)
    # short vertical tick map: vertical edges whose connected run is SHORT (shingle butt joints)
    vedge=((np.abs(gx)>60)&(np.abs(gx)>np.abs(gy)*1.6)).astype(np.uint8)
    n,lb,st,_=cv2.connectedComponentsWithStats(vedge,8)
    shortv=np.zeros_like(vedge)
    for i in range(1,n):
        h=st[i,cv2.CC_STAT_HEIGHT]; w=st[i,cv2.CC_STAT_WIDTH]
        if h< 0.42*PPX and w<0.18*PPX: shortv[lb==i]=1
    lab=np.zeros((H//TILE,W//TILE),np.uint8)
    for ty in range(lab.shape[0]):
        for tx in range(lab.shape[1]):
            ys,xs=slice(ty*TILE,(ty+1)*TILE),slice(tx*TILE,(tx+1)*TILE)
            gxx,gyy,ii=gx[ys,xs],gy[ys,xs],ink[ys,xs]
            dens=ii.mean()
            if dens<0.02 or dens>0.88: continue
            mag=np.hypot(gxx,gyy); sel=mag>40
            if sel.sum()<TILE: continue
            evh=(np.abs(gyy[sel])>np.abs(gxx[sel])).mean()
            tick=shortv[ys,xs].mean()
            if evh>0.78:
                lab[ty,tx]= 4 if tick>0.008 else 1     # staggered butts -> shingle, else lap
            elif evh<0.22: lab[ty,tx]=2
            else: lab[ty,tx]=3
    ov=img.copy(); cnt={k:0 for k in NAMES}
    for ty in range(lab.shape[0]):
        for tx in range(lab.shape[1]):
            v=lab[ty,tx]
            if v==0: continue
            cnt[v]+=1; cv2.rectangle(ov,(tx*TILE,ty*TILE),((tx+1)*TILE-1,(ty+1)*TILE-1),COLS[v],-1)
    cv2.imwrite(f'evidence/tex2_{nm}.png',cv2.cvtColor(cv2.addWeighted(img,0.5,ov,0.5,0),cv2.COLOR_RGB2BGR))
    t=(TILE/PPX)**2
    res[nm]={NAMES[k]:round(cnt[k]*t,1) for k in NAMES}
    print(f'{nm:<10}', ' | '.join(f'{NAMES[k]} {cnt[k]*t:7.1f}' for k in NAMES))
json.dump(res,open('texture_split.json','w'),indent=1)
