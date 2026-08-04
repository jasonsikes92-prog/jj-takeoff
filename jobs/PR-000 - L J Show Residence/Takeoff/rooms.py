import sys, math, re, json, collections; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p5=d[4]; PPF5=18.0
ws=sorted(p5.get_text('words'), key=lambda w:(round((w[1]+w[3])/2,0), w[0]))
lines=collections.defaultdict(list)
for w in ws: lines[round((w[1]+w[3])/2,0)].append(w)
rows=[]
for y in sorted(lines):
    g=sorted(lines[y],key=lambda w:w[0]); s=' '.join(x[4] for x in g)
    rows.append((y, s, min(x[0] for x in g), max(x[2] for x in g)))
# pair ROOM NAME line with the "N'-N" PLT HGT." line just below it
rooms=[]
for i,(y,s,x0,x1) in enumerate(rows):
    m=re.match(r"^(\d+)'-(\d+)(?:\s+(\d+)\s+(\d+))?\"?\s*PLT HGT\.?$", s.strip())
    if not m: continue
    ft=int(m.group(1))+int(m.group(2))/12
    if m.group(3): ft+=int(m.group(3))/int(m.group(4))/12
    # room name = nearest preceding row within 22 pts
    name=None
    for j in range(i-1,max(-1,i-4),-1):
        if y-rows[j][0] < 24 and re.match(r'^[A-Z0-9 /]+$', rows[j][1].strip()) and 'PLT' not in rows[j][1]:
            name=rows[j][1].strip(); break
    rooms.append({'name':name or '?', 'plt_ft':round(ft,3),
                  'x':round((x0+x1)/2/PPF5,2), 'y':round(y/PPF5,2)})
print(f'{len(rooms)} rooms with plate heights on p5:')
for r in sorted(rooms,key=lambda r:-r['plt_ft']):
    print(f"   {r['name']:<18} {r['plt_ft']:6.3f} ft   at ({r['x']:7.2f},{r['y']:7.2f})")
json.dump(rooms,open('rooms.json','w'),indent=1)
xs=[r['x'] for r in rooms]; ys=[r['y'] for r in rooms]
print(f'\nroom-label extent (p5 ft): x {min(xs):.2f}-{max(xs):.2f}  y {min(ys):.2f}-{max(ys):.2f}')
