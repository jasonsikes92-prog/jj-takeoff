import numpy as np
from PIL import Image
from collections import deque
px_per_ft = 2.0*13.41  # render matrix 2.0 * 13.41 pts/ft
im = Image.open(r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\pages\p6.png").convert("RGB")
a = np.asarray(im).astype(int)
R,G,B = a[...,0],a[...,1],a[...,2]
# crop to plan region (pt*2): x 181-1649 -> 362-3298 ; y 619-1491 -> 1238-2982 ; pad
x0,x1,y0,y1 = 300,3360,1180,3040
sub = a[y0:y1, x0:x1]
r,g,b = sub[...,0],sub[...,1],sub[...,2]
# dark/black walls: low brightness AND not strongly blue (dims are blue: b>>r)
bright = (r+g+b)/3
dark = (bright<110) & (b - r < 60)   # exclude blue dimension lines
# downsample for speed factor 2
ds=2
wall = dark[::ds,::ds]
H,W = wall.shape
# flood fill background from border
bg = np.zeros((H,W),bool)
dq=deque()
for x in range(W):
    for y in (0,H-1):
        if not wall[y,x] and not bg[y,x]: bg[y,x]=True; dq.append((y,x))
for y in range(H):
    for x in (0,W-1):
        if not wall[y,x] and not bg[y,x]: bg[y,x]=True; dq.append((y,x))
while dq:
    y,x=dq.popleft()
    for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
        ny,nx=y+dy,x+dx
        if 0<=ny<H and 0<=nx<W and not wall[ny,nx] and not bg[ny,nx]:
            bg[ny,nx]=True; dq.append((ny,nx))
inside = (~bg)  # walls + interior = footprint
# largest connected component of 'inside' to drop stray text blobs
lbl=np.zeros((H,W),int); cur=0; comps=[]
for sy in range(H):
    for sx in range(W):
        if inside[sy,sx] and lbl[sy,sx]==0:
            cur+=1; cnt=0; dq=deque([(sy,sx)]); lbl[sy,sx]=cur
            while dq:
                y,x=dq.popleft(); cnt+=1
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    ny,nx=y+dy,x+dx
                    if 0<=ny<H and 0<=nx<W and inside[ny,nx] and lbl[ny,nx]==0:
                        lbl[ny,nx]=cur; dq.append((ny,nx))
            comps.append((cnt,cur))
comps.sort(reverse=True)
big=comps[0][1]
foot = (lbl==big)
px_area = foot.sum()*(ds**2)
sf = px_area/(px_per_ft**2)
# perimeter: boundary pixels of foot
fy,fx=np.where(foot)
print("footprint area px:",px_area,"=> SF:",round(sf))
print("bbox ft: w=",round((fx.max()-fx.min())*ds/px_per_ft,1)," h=",round((fy.max()-fy.min())*ds/px_per_ft,1))
print("top components px:",[c[0]*ds*ds for c in comps[:4]])
np.save(r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\foot.npy",foot)
# perimeter via boundary count
shift=np.zeros_like(foot)
bound = foot & ~(
    np.roll(foot,1,0)&np.roll(foot,-1,0)&np.roll(foot,1,1)&np.roll(foot,-1,1))
# better perimeter: marching - count edges between foot and non-foot
edges=0
edges+=np.sum(foot[:, :-1]!=foot[:,1:])
edges+=np.sum(foot[:-1,:]!=foot[1:,:])
per_ft = edges*ds/px_per_ft/2*1.0
print("approx perimeter LF (edge/2):", round(edges*ds/px_per_ft))
