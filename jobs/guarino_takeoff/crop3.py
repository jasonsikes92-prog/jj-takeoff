import fitz
doc=fitz.open(r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf")
def crop(pg,clip,name,z=4):
    pix=doc[pg-1].get_pixmap(matrix=fitz.Matrix(z,z),clip=fitz.Rect(*clip)); pix.save("pages/"+name); print(name,pix.width,pix.height)
# floor plan rear porch (bottom center-right) p6
crop(6,(350,1050,1300,1480),"p6_rearporch.png",5)
# site plan driveway region p2 (house to Meadow View, lower center)
crop(2,(1050,850,1750,1450),"p2_drive.png",4)
