import sys, math, collections, statistics; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz
PDF=r'C:\Users\jason\Downloads\L J show BID SET (1).pdf'
d=fitz.open(PDF)

def labels(page):
    """Rebuild full dim strings incl. stacked fractions (tokens on slightly different y)."""
    ws=list(page.get_text('words'))
    ws.sort(key=lambda w:(round((w[1]+w[3])/2,0), w[0]))
    groups=[]; cur=[]
    for w in ws:
        if cur and (abs((w[1]+w[3])/2-(cur[-1][1]+cur[-1][3])/2) < 7 and w[0]-cur[-1][2] < 9):
            cur.append(w)
        else:
            if cur: groups.append(cur)
            cur=[w]
    if cur: groups.append(cur)
    out=[]
    for g in groups:
        s=' '.join(x[4] for x in g); ft=J.parse_dim(s)
        if ft and 4<ft<200:
            r=fitz.Rect(min(x[0] for x in g),min(x[1] for x in g),max(x[2] for x in g),max(x[3] for x in g))
            out.append((ft,s,r))
    return out

def hv(page):
    H=collections.defaultdict(list); V=collections.defaultdict(list)
    for dr in page.get_drawings():
        for it in dr['items']:
            if it[0]!='l': continue
            a,b=it[1],it[2]
            if abs(a.y-b.y)<=0.7 and abs(b.x-a.x)>12: H[round((a.y+b.y)/2,1)].append((min(a.x,b.x),max(a.x,b.x)))
            elif abs(a.x-b.x)<=0.7 and abs(b.y-a.y)>12: V[round((a.x+b.x)/2,1)].append((min(a.y,b.y),max(a.y,b.y)))
    return H,V

def clean_spans(page,label):
    H,V=hv(page); res=[]
    for ft,s,r in labels(page):
        cx,cy=(r.x0+r.x1)/2,(r.y0+r.y1)/2
        for y,runs in H.items():
            if abs(y-cy)>20: continue
            L=[x for x in runs if x[1]<r.x0+2 and x[1]>r.x0-30]
            R=[x for x in runs if x[0]>r.x1-2 and x[0]<r.x1+30]
            if len(L)!=1 or len(R)!=1: continue          # exactly one run each side = clean break
            span=R[0][1]-L[0][0]
            res.append((span/ft, ft, s, 'H'))
        for x,runs in V.items():
            if abs(x-cx)>20: continue
            U=[t for t in runs if t[1]<r.y0+2 and t[1]>r.y0-30]
            D=[t for t in runs if t[0]>r.y1-2 and t[0]<r.y1+30]
            if len(U)!=1 or len(D)!=1: continue
            span=D[0][1]-U[0][0]
            res.append((span/ft, ft, s, 'V'))
    vals=[r[0] for r in res if 3<r[0]<40]
    if not vals: print(f'{label}: NO CLEAN SPANS'); return None
    med=statistics.median(vals)
    keep=[v for v in vals if abs(v-med)/med<0.03]
    print(f'{label:<18} n={len(keep):<3} ppf median={statistics.median(keep):7.3f}  mean={statistics.mean(keep):7.3f}  sd={(statistics.stdev(keep) if len(keep)>1 else 0):5.3f}  range {min(keep):.2f}-{max(keep):.2f}')
    for v,ft,s,o in sorted(res,key=lambda r:-r[1])[:8]:
        if abs(v-med)/med<0.03: print(f'      {o} {s:<24}{ft:8.3f} ft -> {v:7.3f}')
    return statistics.median(keep)

PPF={}
for i,name in [(1,'p2 SQFT'),(2,'p3 FDN PLUMB'),(3,'p4 SLAB'),(4,'p5 MAIN FLOOR'),(5,'p6 ROOF'),(6,'p7 ELEC')]:
    PPF[i]=clean_spans(d[i],name); print()
print('LOCKED:', {k:(round(v,3) if v else None) for k,v in PPF.items()})
