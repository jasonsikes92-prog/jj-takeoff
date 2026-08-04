import sys, math, collections, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[5]; PPF=18.0; Z=3.0; PPX=PPF*Z          # px per foot
GREEN=(0.243,0.357,0.184)
CLIP=fitz.Rect(90,180,2400,1560)
W=int(CLIP.width*Z); H=int(CLIP.height*Z)
canvas=np.zeros((H,W),np.uint8)
n=0
for dr in p.get_drawings():
    col=dr.get('color')
    if col is None or tuple(round(x,3) for x in col)!=GREEN: continue
    for it in dr['items']:
        pts=[]
        if it[0]=='l': pts=[it[1],it[2]]
        elif it[0]=='re':
            r=it[1]; c=[fitz.Point(r.x0,r.y0),fitz.Point(r.x1,r.y0),fitz.Point(r.x1,r.y1),fitz.Point(r.x0,r.y1)]
            for i in range(4):
                a,b=c[i],c[(i+1)%4]
                cv2.line(canvas,(int((a.x-CLIP.x0)*Z),int((a.y-CLIP.y0)*Z)),(int((b.x-CLIP.x0)*Z),int((b.y-CLIP.y0)*Z)),255,2); n+=1
            continue
        if len(pts)==2:
            a,b=pts
            cv2.line(canvas,(int((a.x-CLIP.x0)*Z),int((a.y-CLIP.y0)*Z)),(int((b.x-CLIP.x0)*Z),int((b.y-CLIP.y0)*Z)),255,2); n+=1
print('drew',n,'roof segments')
closed=cv2.morphologyEx(canvas,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
# flood exterior
ff=closed.copy(); mask=np.zeros((H+2,W+2),np.uint8)
cv2.floodFill(ff,mask,(0,0),128)
interior=((ff!=128)&(closed==0)).astype(np.uint8)
nlab,lab,stats,cent=cv2.connectedComponentsWithStats(interior,4)
faces=[(i,stats[i,cv2.CC_STAT_AREA]) for i in range(1,nlab) if stats[i,cv2.CC_STAT_AREA] > 0.5*PPX*PPX]
faces.sort(key=lambda t:-t[1])
print(f'{nlab-1} components, {len(faces)} faces > 0.5 SF')
tot=sum(a for _,a in faces)/PPX**2
print(f'total enclosed face area = {tot:.1f} SF   (engine roof_footprint = 6159.0 SF)')
PITCH=[(345.7,725.5,1),(708.4,542.2,1),(1034.6,348.6,1),(1395.6,461.0,1),
       (645.3,1268.6,2),(860.7,1432.6,2),(1406.2,1021.6,2),(961.1,911.2,3),(1177.7,1032.6,4),
       (380.0,1259.4,6),(462.7,1103.5,6),(489.7,1260.7,6),(499.1,953.0,6),(781.9,1263.5,6),
       (891.5,712.3,6),(899.6,1118.4,6),(1051.8,924.1,6),(1200.2,697.9,6),(1411.7,733.0,6),
       (1440.7,626.2,6),(1474.8,1356.5,6),(1529.4,1171.5,6),(1758.2,563.2,6),(1900.8,1019.7,6)]
# assign each callout to the face under/near it
assign=collections.defaultdict(set)
for x,y,r in PITCH:
    px,py=int((x-CLIP.x0)*Z),int((y-CLIP.y0)*Z)
    found=None
    for rad in range(0,140,4):
        for dx,dy in [(0,0),(rad,0),(-rad,0),(0,rad),(0,-rad),(rad,rad),(-rad,-rad),(rad,-rad),(-rad,rad)]:
            qx,qy=px+dx,py+dy
            if 0<=qx<W and 0<=qy<H and lab[qy,qx]>0:
                found=lab[qy,qx]; break
        if found: break
    if found: assign[found].add(r)
areas=collections.defaultdict(float); unassigned=0.0
for i,a in faces:
    sf=a/PPX**2
    if i in assign:
        rs=assign[i]
        r=min(rs)   # conservative: if two callouts land in one face take the lower pitch
        areas[r]+=sf
    else: unassigned+=sf
print()
print('FOOTPRINT BY PITCH ZONE (measured @ 18.0 pts/ft):')
for r in sorted(areas): print(f'   {r}:12   {areas[r]:8.1f} SF footprint   pitch factor {J.pitch_factor(r):.4f}')
print(f'   UNASSIGNED {unassigned:8.1f} SF  ({unassigned/(sum(areas.values())+unassigned)*100:.1f}%)')
cv2.imwrite('evidence/roof_faces.png', cv2.applyColorMap((lab*37%255).astype(np.uint8),cv2.COLORMAP_JET)*(interior[:,:,None]>0))
json.dump({str(k):v for k,v in areas.items()} | {'unassigned':unassigned,'total':tot}, open('roof_zones.json','w'), indent=1)
