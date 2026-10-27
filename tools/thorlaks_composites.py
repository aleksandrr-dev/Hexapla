"""Build 2 labelled composites (left half / right half, native scale) per adjudication chunk.
Usage: python adj_composites.py <kit_page_dir> <out_dir> <first>-<last> [<first>-<last> ...]

The image reader DOWNSCALES any image over ~1.15 MP (not only >1568 px on a side),
so a bigger composite is seen BELOW native scale (measured 2026-09-27: witness-gold
sheets of 1.4-3.3 MP were read at 0.6-0.9x). A range whose composite would exceed
MAX_MP is REFUSED (rc 2, nothing written for it) - split the range; the file names
are a contract with the prompts (chunk n -> adj_cn_{L,R}.png), so no silent split.
Control: HEXAPLA_COMPOSITE_MP=0.1 must refuse any normal range.
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

kit, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
try:
    font = ImageFont.truetype("arial.ttf", 22)
except OSError:
    font = ImageFont.load_default()
LAB = 90
MAX_MP = float(os.environ.get("HEXAPLA_COMPOSITE_MP", "1.15"))
refused = []
for n, rng in enumerate(sys.argv[3:], 1):
    a, b = (int(x) for x in rng.split("-"))
    rows = [(i, Image.open(os.path.join(kit, f"line{i:02d}.png")).convert("RGB")) for i in range(a, b + 1)]
    W = max(im.width for _, im in rows)
    half = W // 2
    sides = []
    for side, (x0, x1) in (("L", (0, half + 30)), ("R", (half - 30, W))):
        parts = [(i, im.crop((x0, 0, min(x1, im.width), im.height))) for i, im in rows]
        w = LAB + max(p.width for _, p in parts)
        h = sum(p.height for _, p in parts) + 3 * len(parts)
        sides.append((side, parts, w, h))
    mp = max(w * h for _, _, w, h in sides) / 1e6
    if mp > MAX_MP:
        refused.append(rng)
        print(f"REFUSED {rng}: composite {mp:.2f} MP > {MAX_MP} MP (would be downscaled below native) - split it",
              file=sys.stderr)
        continue
    for side, parts, w, h in sides:
        c = Image.new("RGB", (w, h), "white")
        d = ImageDraw.Draw(c)
        y = 0
        for i, p in parts:
            c.paste(p, (LAB, y))
            d.text((4, y + p.height // 2 - 11), f"line{i:02d}", fill="red", font=font)
            y += p.height
            d.line((0, y + 1, w, y + 1), fill="red", width=1)
            y += 3
        path = os.path.join(out, f"adj_c{n}_{side}.png")
        c.save(path)
        print(path, c.size)

if refused:
    sys.exit(2)
