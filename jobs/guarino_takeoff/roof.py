import fitz, numpy as np
from collections import deque
from PIL import Image
doc=fitz.open(r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf")
# ROOF PLAN p7 at 3x; outline is clean closed polygon
z=3.0; ppf=z*13.41
p=doc[6]
pix=p.get_pixmap(matrix=fitz.Matrix(z,z))
img=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)[...,:3].astype(int)
bright=img.mean(2); b=img[...,2]; r=img[...,0]
dark=(bright<150)&(b-r<70)
# crop to plan area (exclude title block x>2300pt and borders)
x0,x1,y0,y1=[int(v*z) for v in (150,2050,400,1500)]
sub=dark[y0:y1,x0:x1]
# dilate 2px to close tiny gaps
d=sub.copy()
for _ in range(3):
    d=d|np.roll(d,1,0)|np.roll(d,-1,0)|np.roll(d,1,1)|np.roll(d,-1,1)
H,W=d.shape
bg=np.zeros((H,W),bool); dq=deque()
for x in range(W):
    for y in (0,H-1):
        if not d[y,x]: bg[y,x]=True; dq.append((y,x))
for y in range(H):
    for x in (0,W-1):
        if not d[y,x]: bg[y,x]=True; dq.append((y,x))
while dq:
    y,x=dq.popleft()
    for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
        ny,nx=y+dy,x+dx
        if 0<=ny<H and 0<=nx<W and not d[ny,nx] and not bg[ny,nx]:
            bg[ny,nx]=True; dq.append((ny,nx))
inside=~bg
# erode back the 3px dilation
e=inside.copy()
for _ in range(3):
    e=e&np.roll(e,1,0)&np.roll(e,-1,0)&np.roll(e,1,1)&np.roll(e,-1,1)
area=e.sum()/(ppf**2)
ys,xs=np.where(e)
print(f"ROOF plan footprint area: {area:,.0f} SF")
print(f"roof bbox: {(xs.max()-xs.min())/ppf:.1f} x {(ys.max()-ys.min())/ppf:.1f} ft")
