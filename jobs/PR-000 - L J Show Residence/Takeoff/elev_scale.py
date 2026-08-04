import sys, math, collections, statistics; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
def rects(page, box):
    """axis-aligned rectangles assembled from H/V segments inside box"""
    H=collections.defaultdict(list); V=collections.defaultdict(list)
    for dr in page.get_drawings():
        for it in dr['items']:
            if it[0]=='l':
                a,b=it[1],it[2]
                if not (box.x0<min(a.x,b.x) and max(a.x,b.x)<box.x1 and box.y0<min(a.y,b.y) and max(a.y,b.y)<box.y1): continue
                if abs(a.y-b.y)<0.6 and abs(b.x-a.x)>3: H[round((a.y+b.y)/2,1)].append((round(min(a.x,b.x),1),round(max(a.x,b.x),1)))
                elif abs(a.x-b.x)<0.6 and abs(b.y-a.y)>3: V[round((a.x+b.x)/2,1)].append((round(min(a.y,b.y),1),round(max(a.y,b.y),1)))
            elif it[0]=='re':
                r=it[1]
                if box.x0<r.x0 and r.x1<box.x1 and box.y0<r.y0 and r.y1<box.y1:
                    H[round(r.y0,1)].append((round(r.x0,1),round(r.x1,1))); H[round(r.y1,1)].append((round(r.x0,1),round(r.x1,1)))
                    V[round(r.x0,1)].append((round(r.y0,1),round(r.y1,1))); V[round(r.x1,1)].append((round(r.y0,1),round(r.y1,1)))
    out=[]
    ys=sorted(H); xs=sorted(V)
    for i,y0 in enumerate(ys):
        for y1 in ys[i+1:]:
            if y1-y0<4 or y1-y0>200: continue
            for x0 in xs:
                if not any(s<=y0+1 and e>=y1-1 for s,e in V[x0]): continue
                for x1 in xs:
                    if x1<=x0+3 or x1-x0>200: continue
                    if not any(s<=y0+1 and e>=y1-1 for s,e in V[x1]): continue
                    if not any(s<=x0+1 and e>=x1-1 for s,e in H[y0]): continue
                    if not any(s<=x0+1 and e>=x1-1 for s,e in H[y1]): continue
                    out.append((x0,y0,x1,y1,x1-x0,y1-y0))
    return out

for pi,name,tag,W,Hf in [(7,'p8 FRONT/REAR','2020FX',2.0,2.0),(8,'p9 SIDE','2020FX',2.0,2.0)]:
    p=d[pi]
    tags=[( (w[0]+w[2])/2,(w[1]+w[3])/2 ) for w in p.get_text('words') if w[4]==tag]
    seen=set(); sols=[]
    for cx,cy in tags:
        if any(abs(cx-a)<3 and abs(cy-b)<3 for a,b in seen): continue
        seen.add((cx,cy))
        box=fitz.Rect(cx-70,cy-70,cx+70,cy+70)
        rs=rects(p,box)
        # a 2x2 window: near-square, side 20-50pt, centred on the tag
        cand=[r for r in rs if abs(r[4]-r[5])/max(r[4],r[5])<0.14 and 18<r[4]<60]
        for r in sorted(cand,key=lambda r:-r[4])[:1]:
            sols.append(r[4]/W); sols.append(r[5]/Hf)
    if sols:
        sols=[s for s in sols if 8<s<30]
        print(f'{name}: {len(sols)//2} square windows measured -> ppf median {statistics.median(sols):.3f}  mean {statistics.mean(sols):.3f}  sd {statistics.pstdev(sols):.3f}')
        print('    samples:', [round(s,2) for s in sorted(sols)])
