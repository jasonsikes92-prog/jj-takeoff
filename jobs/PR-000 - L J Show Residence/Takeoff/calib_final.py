import sys, math, collections; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz
PDF=r'C:\Users\jason\Downloads\L J show BID SET (1).pdf'
d=fitz.open(PDF)

def dim_labels(page):
    ws=list(page.get_text('words')); rows=collections.defaultdict(list)
    for w in ws: rows[(round(w[1],1), round(w[3],1))].append(w)
    out=[]
    for k,g in rows.items():
        g.sort(key=lambda w:w[0]); s=' '.join(x[4] for x in g); ft=J.parse_dim(s)
        if ft and 3<ft<200:
            r=fitz.Rect(min(x[0] for x in g),min(x[1] for x in g),max(x[2] for x in g),max(x[3] for x in g))
            out.append((ft,s,r))
    return out

def lines(page):
    H=collections.defaultdict(list); V=collections.defaultdict(list)
    for dr in page.get_drawings():
        for it in dr['items']:
            if it[0]!='l': continue
            p1,p2=it[1],it[2]
            if abs(p1.y-p2.y)<=0.6 and abs(p2.x-p1.x)>4:
                H[round((p1.y+p2.y)/2,1)].append((min(p1.x,p2.x),max(p1.x,p2.x)))
            elif abs(p1.x-p2.x)<=0.6 and abs(p2.y-p1.y)>4:
                V[round((p1.x+p2.x)/2,1)].append((min(p1.y,p2.y),max(p1.y,p2.y)))
    return H,V

def solve(page,label,verbose=False):
    H,V=lines(page); D=dim_labels(page); votes=[]
    for ft,s,r in D:
        cx,cy=(r.x0+r.x1)/2,(r.y0+r.y1)/2
        # HORIZONTAL dim: two collinear runs flanking the text on (nearly) the same y
        for y,runs in H.items():
            if abs(y-cy)>26: continue
            left=[x for x in runs if x[1] <= r.x0+3 and x[1] > cx-ft*30]
            right=[x for x in runs if x[0] >= r.x1-3 and x[0] < cx+ft*30]
            if not left or not right: continue
            span=max(x[1] for x in right)-min(x[0] for x in left)
            # require the flanking runs to actually abut the text gap
            if abs(max(l[1] for l in left)-r.x0)>34 or abs(min(rr[0] for rr in right)-r.x1)>34: continue
            votes.append((span/ft, ft, s,'H'))
        for x,runs in V.items():
            if abs(x-cx)>26: continue
            up=[t for t in runs if t[1] <= r.y0+3]; dn=[t for t in runs if t[0] >= r.y1-3]
            if not up or not dn: continue
            span=max(t[1] for t in dn)-min(t[0] for t in up)
            if abs(max(u[1] for u in up)-r.y0)>34 or abs(min(t[0] for t in dn)-r.y1)>34: continue
            votes.append((span/ft, ft, s,'V'))
    b=collections.Counter(round(v[0],1) for v in votes)
    top=b.most_common(4)
    print(f'{label:<20} labels={len(D):<4} solved={len(votes):<4} ppf modes {top}')
    if verbose:
        for ppf,ft,s,o in sorted(votes,key=lambda v:-v[1])[:10]:
            print(f'      {o} {s:<20} {ft:8.3f} ft -> {ppf:7.3f} pts/ft')
    return b, votes

R={}
for i,name in [(2,'p3 FDN PLUMBING'),(3,'p4 SLAB'),(4,'p5 MAIN FLOOR'),(5,'p6 ROOF')]:
    b,v=solve(d[i],name,verbose=True); R[i]=(b,v); print()
