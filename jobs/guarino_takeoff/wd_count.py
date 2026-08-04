import fitz, re, collections
src = r"G:\Other computers\My Computer\House Plans\Darryle Guarino\Projects\Darryle Guarino\Darryle Guarino V3.pdf"
doc = fitz.open(src)
# Window/door codes appear on floor plan (p6), elevations (p9,10). Count unique placements on floor plan p6 (plan view = authoritative placement)
pat = re.compile(r'^\(?\d?\)?\d{3,5}(SH|FX|MU|XO)?$')
for pg in [6,9,10]:
    words = doc[pg-1].get_text("words")
    codes=[]
    for w in words:
        t=w[4].strip()
        if re.match(r'^\(?2?\)?\d{4,5}(SH|FX|MU)?$', t) or re.match(r'^\d{4}(SH|FX)$',t):
            codes.append(t)
    print(f"\n=== PAGE {pg} codes ({len(codes)}) ===")
    print(collections.Counter(codes))
