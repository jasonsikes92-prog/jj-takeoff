import fitz, os
src = r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf"
out = r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff\pages"
doc = fitz.open(src)
for i in range(doc.page_count):
    p = doc[i]
    pix = p.get_pixmap(matrix=fitz.Matrix(2.0,2.0))
    pix.save(os.path.join(out, f"p{i+1}.png"))
    print("saved", i+1, pix.width, pix.height)
