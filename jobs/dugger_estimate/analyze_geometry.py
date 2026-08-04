from pathlib import Path
import sys

ROOT = Path(r"C:\Users\jason\OneDrive\Desktop\Claude")
DEPS = ROOT / ".estimate_deps"
sys.path.insert(0, str(DEPS))

import cv2  # noqa: E402
import numpy as np  # noqa: E402


SOURCE = ROOT / "tmp" / "pdfs" / "dugger"
OUTPUT = ROOT / "dugger_estimate" / "geometry_debug"


def component_report(source_name: str, crop_box: tuple[int, int, int, int]) -> None:
    image = cv2.imread(str(SOURCE / source_name))
    x0, y0, x1, y1 = crop_box
    crop = image[y0:y1, x0:x1]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    report = []
    for threshold in (246, 248, 250, 252):
        blurred = cv2.GaussianBlur(gray, (31, 31), 0)
        mask = np.where(blurred < threshold, 255, 0).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        candidates = sorted(
            (
                (int(stats[i, cv2.CC_STAT_AREA]), tuple(int(v) for v in stats[i, :4]))
                for i in range(1, count)
            ),
            reverse=True,
        )[:12]
        report.append(f"threshold={threshold}: {candidates}")
        overlay = crop.copy()
        tint = np.zeros_like(overlay)
        tint[:, :, 2] = mask
        overlay = cv2.addWeighted(overlay, 0.65, tint, 0.35, 0)
        cv2.imwrite(str(OUTPUT / f"{source_name[:-4]}-t{threshold}.png"), overlay)
    (OUTPUT / f"{source_name[:-4]}-components.txt").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    component_report("sheet-11.png", (150, 180, 3150, 2150))
    component_report("sheet-04.png", (150, 180, 3150, 2150))


if __name__ == "__main__":
    main()
