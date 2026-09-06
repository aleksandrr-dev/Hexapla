# -*- coding: utf-8 -*-
"""Build HALF-WIDTH native-resolution (8.3x) contact sheets from prep line crops.

Two uses:
  1. the o/ø retrofit — the stroke is not resolvable on 6.3x sheets;
  2. ANY TALL-BLOCK PAGE. When line_rects() merges lines into blocks the kit
     builds one packed sheet for the whole page, which is a LOW-RESOLUTION read.
     ⛔ Do NOT fall back to re-rendering the PDF into bands: measured 2026-09-06,
     4.0x PDF bands came back blurrier than these crops and a chunk agent
     flagged ~6 words LOW CONFIDENCE because of it. The prep crops are already
     at the scan's native ceiling; use them.

    python tools/thorlaks_o_sheets.py --chunk mark_kit 36

⚠ Width is capped at 1200 px ON PURPOSE. The reader downscales wider images,
so a full-width 2316 px line crop is shown at ~0.55x — BELOW the 6.3x sheets
this retrofit exists to improve on. Half-width at native 8.3x is the whole
point of the convention's wording.
⛔ Never upscale: prep_chunk's 8.3x IS the scan's native ceiling (see
thorlaks_sorts.py). More pixels would be interpolation, not evidence.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import argparse

# ⚠ BEFORE argparse: the docstring carries ⛔/⚠ and argparse prints it for
# --help. Windows stdout defaults to cp1252, so without this line `--help`
# dies with a UnicodeEncodeError — a tool whose own help crashes is the
# "a check that cannot run is not a check that passed" shape.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_ap = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_ap.add_argument("--chunk", default="matthew_kit", help="prep chunk dir under research/_prep/")
_ap.add_argument("pages", nargs="+", help="page indices, e.g. 32 36 49")
_a = _ap.parse_args()
PREP = Path("C:/Projects/Hexapla-releases/research/_prep") / _a.chunk
OUT  = Path("C:/Projects/Hexapla-releases/_work/sheets") / f"{_a.chunk}_native"
OUT.mkdir(parents=True, exist_ok=True)
HALF_W, OVERLAP, LBL = 1200, 90, 18
# ⚠ PACK BY HEIGHT, NOT BY ROW COUNT. A tall-block page (one whose lines the
# detector merged — matthew idx 10 crops are 318 px, not 65) would otherwise
# build a 2,700 px sheet, and the reader DOWNSCALES anything that tall. That
# would silently drop the read below the 6.3x sheets this retrofit exists to
# beat, which is the exact failure the retrofit is correcting.
MAX_H = 820

def halves(img):
    w, h = img.size
    if w <= HALF_W:
        return [("F", img)]
    return [("L", img.crop((0, 0, HALF_W, h))),
            ("R", img.crop((max(w - HALF_W, HALF_W - OVERLAP), 0, w, h)))]

pages = _a.pages
total = 0
for pg in pages:
    d = PREP / f"p{pg}"
    crops = sorted(d.glob("line*.png"))
    items = []
    for c in crops:
        im = Image.open(c).convert("L")
        for tag, half in halves(im):
            items.append((f"p{pg} {c.stem} {tag}", half))
    batches, cur, cur_h = [], [], 8
    for label, im in items:
        h = im.size[1] + LBL
        if cur and cur_h + h > MAX_H:
            batches.append(cur); cur, cur_h = [], 8
        cur.append((label, im)); cur_h += h
    if cur: batches.append(cur)
    for i, batch in enumerate(batches):
        H = sum(im.size[1] + LBL for _, im in batch) + 8
        sheet = Image.new("L", (HALF_W, H), 255)
        dr = ImageDraw.Draw(sheet); y = 4
        for label, im in batch:
            dr.text((4, y + 3), label, fill=0)
            y += LBL
            sheet.paste(im, (0, y)); y += im.size[1]
            dr.line((0, y + 1, HALF_W, y + 1), fill=180)
        f = OUT / f"p{pg}_o{i:02d}.png"
        sheet.save(f); total += 1
print(f"{total} contact sheets -> {OUT}")
