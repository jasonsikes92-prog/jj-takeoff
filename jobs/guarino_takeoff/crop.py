import fitz, os
src = r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf"
out = r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\pages"
doc = fitz.open(src)
def crop(page, clip, name, zoom=4.0):
    p = doc[page-1]
    pix = p.get_pixmap(matrix=fitz.Matrix(zoom,zoom), clip=clip)
    pix.save(os.path.join(out,name)); print("saved",name,pix.width,pix.height)
# page rect is 2592x1728
# Site plan p2: center area with house + streets
crop(2, fitz.Rect(150,150,1100,1300), "p2_site.png", 3.0)
# Floor plan p6 bottom area (pool/porch) - bottom third center
crop(6, fitz.Rect(150,800,1500,1300), "p6_pool.png", 4.0)
# Floor plan p6 full left (baths)
crop(6, fitz.Rect(150,500,900,1250), "p6_left.png", 4.0)
crop(6, fitz.Rect(850,500,1600,1250), "p6_right.png", 4.0)
