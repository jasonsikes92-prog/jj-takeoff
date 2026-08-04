import fitz, os
src = r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf"
out = r"C:\Users\jason\OneDrive\Desktop\Claude\guarino_takeoff"
doc = fitz.open(src)
print("PAGES:", doc.page_count)
# Dump per-page text to a single file + first-line titles
idx = []
with open(os.path.join(out,"alltext.txt"),"w",encoding="utf-8") as f:
    for i,p in enumerate(doc):
        t = p.get_text()
        f.write(f"\n\n===== PAGE {i+1} (size {p.rect.width:.0f}x{p.rect.height:.0f}) =====\n")
        f.write(t)
        # grab a title guess: longest words near top
        words = t.split("\n")
        head = " | ".join([w.strip() for w in words[:6] if w.strip()][:6])
        idx.append((i+1, head[:90]))
print("---INDEX---")
for n,h in idx:
    print(n, h)
