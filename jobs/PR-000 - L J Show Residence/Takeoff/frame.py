import sys, math, json; sys.path.insert(0,r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import fitz
OFF=(-121.713,-36.523)          # p2 ft -> master(p6) ft
W=json.load(open('envelope_walls.json'))
for s in W:
    for k in ('a','b','mid'):
        s[k]=[round(s[k][0]+OFF[0],3), round(s[k][1]+OFF[1],3)]
json.dump(W,open('walls_master.json','w'),indent=1)
xs=[q for s in W for q in (s['a'][0],s['b'][0])]; ys=[q for s in W for q in (s['a'][1],s['b'][1])]
print(f'walls in MASTER frame: x {min(xs):.2f}-{max(xs):.2f}  y {min(ys):.2f}-{max(ys):.2f}')
# elevation page-x ranges (pts) measured earlier
EL={'E1_FRONT':(101.2,2382.7),'E3_REAR':(108.2,2360.7),'E2_LEFT':(527.8,2130.9),'E4_RIGHT':(647.7,1987.3)}
for k,(a,b) in EL.items(): print(f'  {k:<9} page x {a:7.1f}-{b:7.1f} = {a/18:7.2f}-{b/18:7.2f} ft  span {(b-a)/18:6.2f}')
# garage door tag centres
GD={'E1_FRONT':[1888.8,2054.3,2219.8],'E4_RIGHT':[936.7,1102.2,1267.7]}
print()
print('garage doors, E1 FRONT -> master x :', [round(v/18,2) for v in GD['E1_FRONT']])
print('garage doors, E4 RIGHT elev-ft     :', [round(v/18,2) for v in GD['E4_RIGHT']])
# longest 45-deg garage wall
g=sorted([s for s in W if s['ang'] in (45,135)], key=lambda s:-s['len'])[:4]
print()
for s in g: print(f"  w{s['i']:<3}{s['len']:6.2f} LF brg {s['ang']}  ({s['a'][0]:7.2f},{s['a'][1]:7.2f})->({s['b'][0]:7.2f},{s['b'][1]:7.2f})")
# test both orientations for E4 using the door wall's dy/dx sign
door_wall=g[0]
dx=door_wall['b'][0]-door_wall['a'][0]; dy=door_wall['b'][1]-door_wall['a'][1]
print(f'\n longest 45 wall w{door_wall["i"]}: dx {dx:+.2f} dy {dy:+.2f}  -> as x increases y {"DEcreases" if dx*dy<0 else "INcreases"}')
ymin,ymax=11.32,85.48
for rev in (False,True):
    lo=GD['E4_RIGHT'][0]/18; vals=[]
    for v in GD['E4_RIGHT']:
        f=v/18
        vals.append(round(ymax-(f-EL['E4_RIGHT'][0]/18),2) if rev else round(ymin+(f-EL['E4_RIGHT'][0]/18),2))
    print(f'   E4 {"REVERSED" if rev else "direct  "}: door master-y {vals}  -> y {"DEcreasing" if vals[0]>vals[-1] else "INcreasing"}')
