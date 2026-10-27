#!/usr/bin/env python
"""
kxii_initials_sheet.py - contact sheets of kxii_initials_detect.py detections,
for ONE look that says which cells are printed initials (0 model cost to build).

    python tools/kxii_initials_sheet.py --json det.json --out DIR [--pages 770-790]

Each cell = the detection box plus 1.5 box-widths of the text to its right
(an initial is recognised by the text LINES beside it), scaled to fit. Cells
are numbered; DIR/cells.tsv maps number -> page, column, full-res box.
Every sheet is <= 1.15 MP (the image-read rule).
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

PAGES = r"C:\Projects\Hexapla-releases\research\kxii_pages"
CW, CH = 150, 104          # cell incl. 14 px label strip
PER_ROW = 8
MAX_PX = 1150000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", help="restrict, e.g. 770-799")
    a = ap.parse_args()
    lo, hi = 0, 10 ** 6
    if a.pages:
        s, _, e = a.pages.partition("-")
        lo, hi = int(s), int(e or s)
    det = json.load(open(a.json, encoding="utf-8"))
    cells = []
    for r in det:
        p = int(r["page"][1:5])
        if lo <= p <= hi:
            cells += [(p, b) for b in r["boxes"] if b["keep"]]
    rows_per = max(1, MAX_PX // (CW * PER_ROW) // CH)
    per_sheet = rows_per * PER_ROW
    os.makedirs(a.out, exist_ok=True)
    font = ImageFont.load_default()
    tsv = open(os.path.join(a.out, "cells.tsv"), "w", encoding="utf-8", newline="\n")
    tsv.write("n\tsheet\tpage\tcol\tx\ty\tw\th\n")
    cache = {}
    for si in range(0, len(cells), per_sheet):
        chunk = cells[si:si + per_sheet]
        nrows = (len(chunk) + PER_ROW - 1) // PER_ROW
        sheet = Image.new("L", (CW * PER_ROW, CH * nrows), 255)
        d = ImageDraw.Draw(sheet)
        for k, (p, b) in enumerate(chunk):
            n = si + k + 1
            if p not in cache:
                cache = {p: Image.open(os.path.join(PAGES, "p%04d.jpg" % p)).convert("L")}
            im = cache[p]
            pad = 12
            box = (max(0, b["x"] - pad), max(0, b["y"] - pad),
                   min(im.size[0], b["x"] + int(2.5 * b["w"]) + pad),
                   min(im.size[1], b["y"] + b["h"] + pad))
            crop = im.crop(box)
            crop.thumbnail((CW - 4, CH - 16))
            cx, cy = (k % PER_ROW) * CW, (k // PER_ROW) * CH
            sheet.paste(crop, (cx + 2, cy + 14))
            d.text((cx + 3, cy + 1), str(n), fill=0, font=font)
            d.rectangle((cx, cy, cx + CW - 1, cy + CH - 1), outline=160)
            tsv.write("%d\t%d\t%d\t%s\t%d\t%d\t%d\t%d\n" % (
                n, si // per_sheet + 1, p, b["col"], b["x"], b["y"], b["w"], b["h"]))
        assert sheet.size[0] * sheet.size[1] <= MAX_PX
        path = os.path.join(a.out, "sheet%02d.png" % (si // per_sheet + 1))
        sheet.save(path)
        print("%s  cells %d-%d  %dx%d" % (path, si + 1, si + len(chunk), sheet.size[0], sheet.size[1]))
    tsv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
