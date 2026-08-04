from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"C:\Users\jason\OneDrive\Desktop\Claude")
SOURCE = ROOT / "tmp" / "pdfs" / "dugger"
OUTPUT = ROOT / "dugger_estimate" / "crops"


CROPS = {
    "floor_left.png": ("sheet-06.png", (120, 130, 1420, 2210)),
    "floor_center.png": ("sheet-06.png", (1080, 130, 2460, 2210)),
    "floor_right.png": ("sheet-06.png", (2150, 130, 3440, 2210)),
    "dims_left.png": ("sheet-07.png", (80, 80, 1500, 2280)),
    "dims_center.png": ("sheet-07.png", (1040, 80, 2500, 2280)),
    "dims_right.png": ("sheet-07.png", (2060, 80, 3520, 2280)),
    "ceiling_left.png": ("sheet-09.png", (120, 130, 1500, 2210)),
    "ceiling_center.png": ("sheet-09.png", (1050, 130, 2500, 2210)),
    "ceiling_right.png": ("sheet-09.png", (2100, 130, 3450, 2210)),
    "foundation_main.png": ("sheet-04.png", (150, 100, 3400, 2220)),
    "roof_main.png": ("sheet-11.png", (150, 100, 3400, 2220)),
    "site_main.png": ("sheet-02.png", (300, 120, 2150, 2240)),
    "grading_main.png": ("sheet-03.png", (300, 120, 2150, 2240)),
    "workshop_main.png": ("sheet-14.png", (50, 100, 3450, 2250)),
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for output_name, (source_name, box) in CROPS.items():
        source = Image.open(SOURCE / source_name).convert("RGB")
        crop = source.crop(box)
        draw = ImageDraw.Draw(crop)
        draw.rectangle((0, 0, crop.width - 1, crop.height - 1), outline=(220, 0, 0), width=3)
        crop.save(OUTPUT / output_name)
        manifest.append(f"{output_name}: {source_name} {box} -> {crop.size}")

    for source_name in (
        "sheet-02.png",
        "sheet-03.png",
        "sheet-04.png",
        "sheet-07.png",
        "sheet-11.png",
        "sheet-14.png",
    ):
        source = Image.open(SOURCE / source_name).convert("RGB")
        draw = ImageDraw.Draw(source)
        for x in range(0, source.width, 100):
            color = (210, 70, 70) if x % 500 else (180, 0, 0)
            draw.line((x, 0, x, source.height), fill=color, width=1)
            draw.text((x + 3, 3), str(x), fill=(180, 0, 0))
        for y in range(0, source.height, 100):
            color = (70, 100, 210) if y % 500 else (0, 40, 180)
            draw.line((0, y, source.width, y), fill=color, width=1)
            draw.text((3, y + 3), str(y), fill=(0, 40, 180))
        output_name = source_name.replace(".png", "-grid.png")
        source.save(OUTPUT / output_name)
        manifest.append(f"{output_name}: 100-pixel coordinate grid")
    (OUTPUT / "manifest.txt").write_text("\n".join(manifest), encoding="utf-8")


if __name__ == "__main__":
    main()
