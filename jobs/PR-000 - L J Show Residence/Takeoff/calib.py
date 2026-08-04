import sys; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz, math
PDF = r'C:\Users\jason\Downloads\L J show BID SET (1).pdf'
d = fitz.open(PDF)

def geom_bbox(page, min_len=5.0):
    """Bounding box of substantive drawn geometry (excludes title block via x filter later)."""
    xs=[]; ys=[]
    for dr in page.get_drawings():
        for it in dr['items']:
            if it[0]=='l':
                p1,p2=it[1],it[2]
                if abs(p1.x-p2.x)+abs(p1.y-p2.y) < 1: continue
                xs += [p1.x,p2.x]; ys += [p1.y,p2.y]
            elif it[0]=='re':
                r=it[1]; xs+=[r.x0,r.x1]; ys+=[r.y0,r.y1]
    return min(xs),min(ys),max(xs),max(ys)

# Locate a dimension TEXT and the segment(s) near it that match its value
def dim_words(page):
    out=[]
    for w in page.get_text('words'):
        t=w[4]
        ft = J.parse_dim(t)
        if ft and ft>3:
            out.append((ft, fitz.Rect(w[:4])))
    return out

def segments(page):
    segs=[]
    for dr in page.get_drawings():
        for it in dr['items']:
            if it[0]=='l':
                p1,p2=it[1],it[2]
                L=math.hypot(p2.x-p1.x,p2.y-p1.y)
                if L>3: segs.append((L,p1,p2))
    return segs

def solve_ppf(page, label, targets):
    """targets: list of (feet, tolerance_pct). Find the drawn segment whose length/feet
    clusters consistently -> ppf. Reports each target's independent solution."""
    segs=segments(page)
    print(f'--- {label}: {len(segs)} segments')
    for ft in targets:
        best=[]
        for ppf_guess in (18.0, 9.0, 4.5, 36.0):
            want = ft*ppf_guess
            hits=[s for s in segs if abs(s[0]-want)/want < 0.004]
            if hits: best.append((ppf_guess, len(hits), min(abs(h[0]-want) for h in hits)))
        print(f'   printed {ft:>8.3f} ft -> ppf candidates {best}')

# Known printed OVERALL dims that appear on multiple sheets
# floor p5 / roof p6 both print: 60'-2 5/8", 43'-5", 68'-1", 55'-4", 53'-8", 25'-10", 8'-8"
tg = [60.21875, 43.4167, 68.0833, 55.3333, 53.6667, 25.8333, 8.6667, 28.0, 14.0]
solve_ppf(d[4], 'p5 MAIN FLOOR PLAN', tg)
solve_ppf(d[5], 'p6 ROOF PLAN', tg)
solve_ppf(d[3], 'p4 SLAB PLAN', tg)
solve_ppf(d[2], 'p3 FDN PLUMBING', [24.5833, 17.9167, 12.375, 16.5625, 8.8333])
