import sys, math, collections; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
exec(open('calib2.py').read().split('def calibrate')[0].split("d=fitz.open")[0]) if False else None

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
    ws=list(page.get_text('words')); rows=collections.defaultdict(list)
    for w in ws: rows[(round(w[1],1), round(w[3],1))].append(w)
    out=[]
    for k,g in rows.items():
        g.sort(key=lambda w:w[0]); s=' '.join(x[4] for x in g); ft=J.parse_dim(s)
        if ft and 3<ft<200:
            r=fitz.Rect(min(x[0] for x in g),min(x[1] for x in g),max(x[2] for x in g),max(x[3] for x in g))
            out.append((ft,s,r))
    return out

def perp_ok(cx,cy,p1,p2,maxperp=34.0):
    vx,vy=p2.x-p1.x,p2.y-p1.y; L2=vx*vx+vy*vy
    if L2==0: return False
    t=((cx-p1.x)*vx+(cy-p1.y)*vy)/L2
    if not (-0.08 <= t <= 1.08): return False
    px,py=p1.x+t*vx, p1.y+t*vy
    return math.hypot(cx-px,cy-py) <= maxperp

def calibrate(page,label):
    S=segs(page); D=dims(page); votes=[]
    for ft,s,r in D:
        cx,cy=(r.x0+r.x1)/2,(r.y0+r.y1)/2
        for L,p1,p2 in S:
            ppf=L/ft
            if not (4.0 < ppf < 30.0): continue     # plausible arch scales only
            if not perp_ok(cx,cy,p1,p2): continue
            votes.append((round(ppf,2), ft, s))
    b=collections.Counter(round(v[0],1) for v in votes)
    print(f'{label:<18} dims={len(D):<4} votes={len(votes):<5} {b.most_common(5)}')
    for ppf,ft,s in sorted(votes, key=lambda v:-v[1])[:6]:
        print(f'      {s:<22} = {ft:8.3f} ft  -> ppf {ppf}')
    return b

for i,name in [(3,'p4 SLAB'),(4,'p5 MAIN FLOOR'),(5,'p6 ROOF'),(2,'p3 FDN PLUMB')]:
    calibrate(d[i],name); print()
