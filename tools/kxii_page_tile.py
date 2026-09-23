# -*- coding: utf-8 -*-
"""kxii_page_tile.py - map a STRIP coordinate back to the RAW PAGE and cut the
tile there, at the scan's true resolution.

    python tools/kxii_page_tile.py --page 715 --tag R2 --strips 5 \
        --site 1430,1419 --label "10:60 h?rlighet" \
        --ctrl 1200,900,"RING gafwor" --out sheet.png

## WHY THIS EXISTS

`kxii_strips.py` upscales each column slice to a 2000 px long edge, which for
this print is roughly **1.6x**. So a tile cut at "9x" from a strip is only
~5.6x of the scan's REAL pixels, and §4-0c's magnification rule is about how
big the LETTERS come out, not the multiplier you typed. That gap is the whole
mechanism behind §4-0c/§4-0c-ii: an inked-up ‹e› read off an under-magnified
tile prints as a ring, and that is the direction that silently flips ä to å.

Cutting from `research/kxii_pages/pNNNN.jpg` removes the upscale from the
budget entirely: the same 2000 px of render now carries ~1.6x more real detail.
1 Macc 8:31 was undecidable on its strip (its mark sits above the slice's top
edge) and unambiguous on the page.

⚠ It still LOCATES ONLY. Controls, the same-strip rule and the 9x floor all
still apply - and the floor is now measured in PAGE pixels, which is stricter.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prep_kxii as P
from PIL import Image, ImageDraw

LONG_EDGE = 2000
OVERLAP = 0.04
XPAD = 26


HAND_RULES = {665: (225, 1050, 1883), 740: (745, 1478, 2221),
              742: (761, 1493, 2224)}   # from the brief; find_frame skips these


def transform(printed, tag, nstrips):
    """-> (cx0, sy0, k) so that page = (cx0 + sx/k, sy0 + sy/k)."""
    src = P.fetch(printed)
    im = Image.open(src).convert("L")
    fr = HAND_RULES.get(printed) or P.find_frame(im)
    if not fr:
        raise SystemExit("no frame for p%d - hand-frame it as kxii_strips does"
                         % printed)
    L, C, R = fr
    y0, y1, _ = P.text_band(im, L, C, R)
    col, idx = tag[0], int(tag[1:]) - 1
    bx0, bx1 = (L + 6, C - 6) if col == "L" else (C + 6, R - 6)
    cx0, cx1 = P.trim_column(im, bx0, bx1, y0, y1)
    cx0, cx1 = max(cx0 - XPAD, 0), min(cx1 + XPAD, im.size[0])
    h = (y1 - y0) / nstrips
    pad = h * OVERLAP
    sy0 = max(y0 + idx * h - pad, y0)
    sy1 = min(y0 + (idx + 1) * h + pad, y1)
    w, hh = cx1 - cx0, int(sy1) - int(sy0)
    k = LONG_EDGE / float(max(w, hh))
    return cx0, int(sy0), k, src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--page", type=int, required=True, help="PRINTED page")
    ap.add_argument("--tag", required=True, help="strip tag, e.g. R2")
    ap.add_argument("--strips", type=int, default=5)
    ap.add_argument("--site", required=True, help="x,y in STRIP pixels")
    ap.add_argument("--label", required=True)
    ap.add_argument("--ctrl", action="append", default=[],
                    help='x,y,"label" in STRIP pixels; repeatable')
    ap.add_argument("--box", default="140x66",
                    help="PAGE-pixel source box for the site (w x h)")
    ap.add_argument("--cbox", default="66x66", help="page box for controls")
    ap.add_argument("--tile-h", type=int, default=920)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    cx0, sy0, k, src = transform(a.page, a.tag, a.strips)
    page = Image.open(src).convert("L")
    bw, bh = (int(v) for v in a.box.lower().split("x"))
    cw, chh = (int(v) for v in a.cbox.lower().split("x"))
    S = a.tile_h / float(bh)

    def cut(sx, sy, w, h):
        px, py = int(cx0 + sx / k), int(sy0 + sy / k)
        W, H = page.size
        x0 = max(0, min(W - w, px - w // 2))
        y0 = max(0, min(H - h, py - h // 2))
        return page.crop((x0, y0, x0 + w, y0 + h))

    sx, sy = (int(v) for v in a.site.split(","))
    rows = [[(cut(sx, sy, bw, bh), "SITE " + a.label)]]
    row = []
    for c in a.ctrl:
        x, y, lab = c.split(",", 2)
        row.append((cut(int(x), int(y), cw, chh), lab.strip('"')))
    if row:
        rows.append(row)
    LH, PAD = 34, 8
    widths = [sum(int(c.width * S) + PAD for c, _ in r) + PAD for r in rows]
    sh = Image.new("L", (max(widths), len(rows) * (a.tile_h + LH + PAD) + PAD), 255)
    dr = ImageDraw.Draw(sh)
    for ri, r in enumerate(rows):
        x, y = PAD, PAD + ri * (a.tile_h + LH + PAD)
        for c, lab in r:
            w = int(c.width * S)
            sh.paste(c.resize((w, a.tile_h), Image.LANCZOS), (x, y))
            dr.rectangle([x, y, x + w, y + a.tile_h], outline=0)
            dr.text((x + 4, y + a.tile_h + 8), lab, fill=0)
            x += w + PAD
    sh.save(a.out)
    print("%s  %s  %.1fx PAGE px (~%.1fx strip-equivalent)  strip->page k=%.3f"
          % (a.out, sh.size, S, S / k, k))
    if max(sh.size) > 2000:
        print("  ⚠ OVER 2000 px - the renderer will shrink it. VOID.")


if __name__ == "__main__":
    sys.exit(main())
