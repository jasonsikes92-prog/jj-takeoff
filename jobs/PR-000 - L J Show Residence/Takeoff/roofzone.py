import sys, json; sys.path.insert(0, r'C:\Users\jason\.claude\skills\jnj-estimate-takeoff\tools')
import jnj_takeoff as J, fitz
d=fitz.open(r'C:\Users\jason\Downloads\L J show BID SET (1).pdf')
p=d[5]
PITCH=[(345.7,725.5,1),(708.4,542.2,1),(1034.6,348.6,1),(1395.6,461.0,1),
       (645.3,1268.6,2),(860.7,1432.6,2),(1406.2,1021.6,2),
       (961.1,911.2,3),(1177.7,1032.6,4),
       (380.0,1259.4,6),(462.7,1103.5,6),(489.7,1260.7,6),(499.1,953.0,6),
       (781.9,1263.5,6),(891.5,712.3,6),(899.6,1118.4,6),(1051.8,924.1,6),
       (1200.2,697.9,6),(1411.7,733.0,6),(1440.7,626.2,6),(1474.8,1356.5,6),
       (1529.4,1171.5,6),(1758.2,563.2,6),(1900.8,1019.7,6)]
UNDER=5529.8
clip=fitz.Rect(90,180,2400,1560)
r=J.roof_zone_surface(p, clip, PITCH, UNDER, overhang_in=(17.0,19.0), nominal_ppf=18.0)
if r is None:
    print('DECOMPOSITION FAILED')
else:
    for k,v in r.items():
        if isinstance(v,list) and len(v)>12: print(f'  {k}: [{len(v)} items]')
        else: print(f'  {k}: {v}')
