import sys, math, collections; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
PPF=18.0
# GRADE LINE: the long horizontal at the base of each elevation
for pi,nm,ylo,yhi in [(7,'E1 FRONT',120,700),(7,'E3 REAR',760,1340),(8,'E2 LEFT',120,770),(8,'E4 RIGHT',830,1410)]:
    p=d[pi]; H=collections.defaultdict(float)
    for dr in p.get_drawings():
        for it in dr['items']:
            if it[0]!='l': continue
            a,b=it[1],it[2]
            if abs(a.y-b.y)>0.7: continue
            y=(a.y+b.y)/2
            if not (ylo<y<yhi): continue
            H[round(y,1)]+=abs(b.x-a.x)
    top=sorted(H.items(), key=lambda t:-t[1])[:8]
    grade=max(t[0] for t in top)          # lowest on page = largest y among the long runs
    print(f'{nm}: longest horizontals (y, total LF-of-line):')
    for y,L in sorted(top): print(f'      y={y:8.1f}  ink {L/PPF:8.1f} ft   -> {(grade-y)/PPF:6.2f} ft above grade')
    print(f'   GRADE LINE y={grade:.1f}')
    print()
