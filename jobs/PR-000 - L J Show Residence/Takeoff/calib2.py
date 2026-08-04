import sys, math, collections; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')

def segs(page):
    out=[]
    for dr in page.get_drawings():
        for it in dr['items']:
            if it[0]=='l':
                p1,p2=it[1],it[2]
                L=math.hypot(p2.x-p1.x,p2.y-p1.y)
                if L>8: out.append((L,p1,p2))
    return out

def dims(page):
    """Rebuild multi-token dimension strings like  60'-2  5  8\"  from words on one line."""
    ws=[w for w in page.get_text('words')]
    rows=collections.defaultdict(list)
    for w in ws: rows[(round(w[1],1), round(w[3],1))].append(w)
    out=[]
    for k,g in rows.items():
        g.sort(key=lambda w:w[0])
        s=' '.join(x[4] for x in g)
        ft=J.parse_dim(s)
        if ft and 3<ft<200:
            r=fitz.Rect(min(x[0] for x in g),min(x[1] for x in g),max(x[2] for x in g),max(x[3] for x in g))
            out.append((ft,s,r))
    return out

def calibrate(page, label, tol=0.006, near=46.0):
    S=segs(page); D=dims(page); votes=[]
    for ft,s,r in D:
        cx,cy=(r.x0+r.x1)/2,(r.y0+r.y1)/2
        for L,p1,p2 in S:
            mx,my=(p1.x+p2.x)/2,(p1.y+p2.y)/2
            if math.hypot(mx-cx,my-cy) > near: continue
            dx,dy=abs(p2.x-p1.x),abs(p2.y-p1.y)
            # dimension line should be roughly parallel to the text baseline (horizontal) or vertical
            ppf = L/ft
            if 3.0 < ppf < 40.0: votes.append((ppf, ft, s))
    # cluster
    buckets=collections.Counter()
    for ppf,ft,s in votes: buckets[round(ppf,1)] += 1
    top=buckets.most_common(6)
    print(f'{label:<20} dims={len(D):<4} votes={len(votes):<5} top ppf: {top}')
    return votes, D

for i,name in [(2,'p3 FDN PLUMBING'),(3,'p4 SLAB'),(4,'p5 MAIN FLOOR'),(5,'p6 ROOF'),(7,'p8 FRONT/REAR EL'),(8,'p9 SIDE EL'),(11,'p12 SECTIONS'),(10,'p11 CAB EL')]:
    calibrate(d[i], name)
