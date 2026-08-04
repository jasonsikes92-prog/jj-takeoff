import sys, math, json, collections; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
G=json.load(open('cladding_gables.json'))['gables']
# ---- FASCIA/SOFFIT: roof-plan perimeter (horizontal projection) + rake slope uplift
PERIM=402.0
uplift=0.0; rake_true=0.0
for g in G:
    b=g['base_ft']/2.0; r=g['rise_ft']
    t=math.hypot(b,r)
    rake_true += 2*t
    uplift += 2*(t-b)
FASCIA=PERIM+uplift
print(f'ROOF EDGE: plan perimeter {PERIM:.1f} LF + rake slope uplift {uplift:.1f} LF = FASCIA/SOFFIT {FASCIA:.1f} LF')
print(f'   (true rake length across {len(G)} gables = {rake_true:.1f} LF)')
# ---- CORNERS: count outside corners on the envelope ring x wall height
Wl=json.load(open('walls_master.json'))
n=len(Wl); corners=0
for i in range(n):
    a=Wl[i]; b=Wl[(i+1)%n]
    d1=(a['b'][0]-a['a'][0], a['b'][1]-a['a'][1]); d2=(b['b'][0]-b['a'][0], b['b'][1]-b['a'][1])
    cross=d1[0]*d2[1]-d1[1]*d2[0]
    if abs(cross)>0.01: corners+=1
avg_h=11.05
print(f'CORNERS: {corners} direction changes on the envelope ring x {avg_h} ft = {corners*avg_h:.0f} LF corner board')
# ---- TRIMMED OPENINGS: count window/door tags on the four elevations (unique positions)
TAGRE=None
import re
def tags(pi, ylo, yhi):
    p=d[pi]; seen=[]
    for w in p.get_text('words'):
        s=w[4]
        if not re.fullmatch(r'\(?\d\)?\d{3,5}(FX|SH|PT)?', s): continue
        cy=(w[1]+w[3])/2
        if not (ylo<cy<yhi): continue
        cx=(w[0]+w[2])/2
        if any(abs(cx-a)<2 and abs(cy-b)<2 for a,b in seen): continue
        seen.append((cx,cy))
    return seen
op=collections.Counter()
for pi,nm,ylo,yhi in [(7,'E1_FRONT',120,700),(7,'E3_REAR',880,1500),(8,'E2_LEFT',130,780),(8,'E4_RIGHT',860,1500)]:
    t=tags(pi,ylo,yhi); op[nm]=len(t)
    print(f'   {nm}: {len(t)} tagged openings')
print(f'TRIMMED OPENINGS total (all 4 elevations): {sum(op.values())}')
# ---- window/door schedule off the FLOOR PLAN (authoritative count)
p5=d[4]; cnt=collections.Counter(); seen=[]
for w in p5.get_text('words'):
    s=w[4]
    if not re.fullmatch(r'\(?\d\)?\d{3,5}(FX|SH|PT)?', s): continue
    cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2
    if any(abs(cx-a)<2 and abs(cy-b)<2 for a,b in seen): continue
    seen.append((cx,cy)); cnt[s]+=1
print(f'\nFLOOR PLAN opening tags: {sum(cnt.values())} total')
for k,v in sorted(cnt.items(), key=lambda t:-t[1]): print(f'    {k:<28}{v}')
json.dump({'fascia_soffit_lf':round(FASCIA,1),'rake_true_lf':round(rake_true,1),'corners_n':corners,
           'corner_lf':round(corners*avg_h,1),'elev_openings':dict(op),'plan_tags':dict(cnt)},open('trim.json','w'),indent=1)
