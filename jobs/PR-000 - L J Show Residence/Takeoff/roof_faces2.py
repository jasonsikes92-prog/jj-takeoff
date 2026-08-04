import sys, math, collections, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[5]; PPF=18.0; Z=3.0; PPX=PPF*Z
GREEN=(0.243,0.357,0.184); CLIP=fitz.Rect(90,180,2400,1560)
W=int(CLIP.width*Z); H=int(CLIP.height*Z); canvas=np.zeros((H,W),np.uint8)
def px(pt): return (int((pt.x-CLIP.x0)*Z), int((pt.y-CLIP.y0)*Z))
for dr in p.get_drawings():
    col=dr.get('color')
    if col is None or tuple(round(x,3) for x in col)!=GREEN: continue
    for it in dr['items']:
        if it[0]=='l': cv2.line(canvas,px(it[1]),px(it[2]),255,2)
        elif it[0]=='re':
            r=it[1]; c=[fitz.Point(r.x0,r.y0),fitz.Point(r.x1,r.y0),fitz.Point(r.x1,r.y1),fitz.Point(r.x0,r.y1)]
            for i in range(4): cv2.line(canvas,px(c[i]),px(c[(i+1)%4]),255,2)
closed=cv2.morphologyEx(canvas,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
ff=closed.copy(); m=np.zeros((H+2,W+2),np.uint8); cv2.floodFill(ff,m,(0,0),128)
interior=((ff!=128)&(closed==0)).astype(np.uint8)
nlab,lab,stats,cent=cv2.connectedComponentsWithStats(interior,4)
faces=[i for i in range(1,nlab) if stats[i,cv2.CC_STAT_AREA]>0.5*PPX*PPX]
PITCH=[(345.7,725.5,1),(708.4,542.2,1),(1034.6,348.6,1),(1395.6,461.0,1),
       (645.3,1268.6,2),(860.7,1432.6,2),(1406.2,1021.6,2),(961.1,911.2,3),(1177.7,1032.6,4),
       (380.0,1259.4,6),(462.7,1103.5,6),(489.7,1260.7,6),(499.1,953.0,6),(781.9,1263.5,6),
       (891.5,712.3,6),(899.6,1118.4,6),(1051.8,924.1,6),(1200.2,697.9,6),(1411.7,733.0,6),
       (1440.7,626.2,6),(1474.8,1356.5,6),(1529.4,1171.5,6),(1758.2,563.2,6),(1900.8,1019.7,6)]
CP=[((x-CLIP.x0)*Z,(y-CLIP.y0)*Z,r) for x,y,r in PITCH]
# 1) callout INSIDE a face wins
inside=collections.defaultdict(list)
for cx,cy,r in CP:
    q=(int(cx),int(cy))
    if 0<=q[0]<W and 0<=q[1]<H and lab[q[1],q[0]]>0: inside[lab[q[1],q[0]]].append(r)
# 2) otherwise nearest callout to face centroid
areas=collections.defaultdict(float); detail=[]
for i in faces:
    sf=stats[i,cv2.CC_STAT_AREA]/PPX**2
    if i in inside: r=min(inside[i]); how='callout-inside'
    else:
        fx,fy=cent[i]
        r=min(CP,key=lambda c:math.hypot(c[0]-fx,c[1]-fy))[2]; how='nearest-callout'
    areas[r]+=sf; detail.append((sf,r,how))
tot=sum(areas.values())
print(f'{len(faces)} faces, total {tot:.1f} SF (engine footprint 6159.0, my raster 6088.1)')
print()
print('FOOTPRINT BY PITCH ZONE:')
zones=[]
for r in sorted(areas):
    pf=J.pitch_factor(r); surf=areas[r]*pf
    zones.append({'footprint_sf':round(areas[r],1),'pitch':r})
    print(f'   {r}:12  footprint {areas[r]:8.1f} SF  x factor {pf:.4f} = surface {surf:8.1f} SF')
print(f'   {"TOTAL":<6} footprint {tot:8.1f} SF                     surface {sum(areas[r]*J.pitch_factor(r) for r in areas):8.1f} SF')
print()
print('10 largest faces:')
for sf,r,how in sorted(detail,reverse=True)[:10]: print(f'   {sf:8.1f} SF -> {r}:12  ({how})')
json.dump(zones, open('roof_zones.json','w'), indent=1)
# scale to the engine's vector footprint 6159.0 for the priced number
K=6159.0/tot
print(f'\nscaled to engine vector footprint (x{K:.4f}):')
for z in zones: z['footprint_sf']=round(z['footprint_sf']*K,1)
for z in zones: print(f"   {z['pitch']}:12  {z['footprint_sf']:8.1f} SF")
json.dump(zones, open('roof_zones.json','w'), indent=1)
