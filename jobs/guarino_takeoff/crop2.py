import fitz, os
src = r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf"
out = r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\pages"
doc = fitz.open(src)
def crop(page, clip, name, zoom=3.5):
    pix = doc[page-1].get_pixmap(matrix=fitz.Matrix(zoom,zoom), clip=clip)
    pix.save(os.path.join(out,name)); print("saved",name,pix.width,pix.height)
crop(2, fitz.Rect(900,500,2000,1400), "p2_lot.png", 3.0)
