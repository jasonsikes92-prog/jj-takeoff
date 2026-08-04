import fitz, numpy as np
from PIL import Image
doc = fitz.open(r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf")
# Render each elevation page at 3x, isolate the dark silhouette, measure width & area by column fill.
def measure(page, regions, zoom=3.0):
    p=doc[page-1]
    pix=p.get_pixmap(matrix=fitz.Matrix(zoom,zoom))
    img=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)[...,:3].astype(int)
    bright=img.mean(2); b=img[...,2]; r=img[...,0]
    dark=(bright<140)&(b-r<70)   # building line work, exclude blue
    ppf=zoom*18.0  # 1/4in=1ft nominal -> 18pt/ft
    out=[]
    for name,(x0,x1,y0,y1) in regions.items():
        x0,x1,y0,y1=[int(v*zoom) for v in (x0,x1,y0,y1)]
        sub=dark[y0:y1,x0:x1]
        cols=np.where(sub.any(0))[0]
        if len(cols)==0: out.append((name,0,0,0)); continue
        wpx=cols.max()-cols.min()
        # per-column height = bottom dark - top dark (silhouette)
        heights=[]
        for c in range(cols.min(),cols.max()+1):
            ys=np.where(sub[:,c])[0]
            if len(ys): heights.append(ys.max()-ys.min())
        area_px=sum(heights)  # px height summed over px width
        out.append((name, wpx/ppf, np.mean(heights)/ppf, area_px/(ppf**2)))
    return out
# page extents are 2592x1728. Use full-page pt coords for regions (single drawing each, top/bottom split)
# p9: E1 front (top half), E3 back (bottom half)
r9={"E1_front":(30,1990,40,580),"E3_back":(30,1990,800,1340)}
# p10: E2 left (top-left), E4 right (mid-left); cross sections on right - avoid x>1100
r10={"E2_left":(60,1100,60,520),"E4_right":(60,1100,640,1180)}
for pg,reg in [(9,r9),(10,r10)]:
    for name,w,h,a in measure(pg,reg):
        print(f"{name}: width {w:.1f} ft, avg height {h:.1f} ft, face area {a:,.0f} SF")
