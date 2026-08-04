import sys, math, collections, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz, numpy as np, cv2
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
VIEWS=[(7,'E1_FRONT',fitz.Rect(95,120,2395,700)),(7,'E3_REAR',fitz.Rect(95,760,2395,1340)),
       (8,'E2_LEFT',fitz.Rect(500,120,2150,770)),(8,'E4_RIGHT',fitz.Rect(620,830,2000,1410))]
for pi,nm,clip in VIEWS:
    p=d[pi]; S=[]
    for dr in p.get_drawings():
        for it in dr['items']:
            if it[0]!='l': continue
            a,b=it[1],it[2]
            if not (clip.x0<=min(a.x,b.x) and max(a.x,b.x)<=clip.x1 and clip.y0<=min(a.y,b.y) and max(a.y,b.y)<=clip.y1): continue
            L=math.hypot(b.x-a.x,b.y-a.y)
            if L<0.8: continue
            ang=math.degrees(math.atan2(b.y-a.y,b.x-a.x))%180
            S.append((L,ang,a.x,a.y,b.x,b.y))
    hz=[s for s in S if s[1]<8 or s[1]>172]; vt=[s for s in S if 82<s[1]<98]; ot=[s for s in S if not(s[1]<8 or s[1]>172 or 82<s[1]<98)]
    print(f'{nm}: {len(S)} segs | horiz {len(hz)} | vert {len(vt)} | other {len(ot)}')
    for tag,grp in [('HORIZ',hz),('VERT',vt)]:
        Ls=sorted(s[0] for s in grp)
        if Ls:
            q=lambda f: Ls[int(f*(len(Ls)-1))]
            print(f'    {tag} len pts: p10={q(.1):6.1f} p50={q(.5):6.1f} p90={q(.9):7.1f} max={Ls[-1]:7.1f}')
