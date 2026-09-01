# -*- coding: utf-8 -*-
"""kxii_site_sheets.py - one 9x sheet per site: the site's mark, a RING control
and an <e> control, all cut to the SAME source box from the SAME strip.

    python tools/kxii_site_sheets.py --marks marks.json --outdir sheets/

Input is kxii_hapax_sites.py's output. Each sheet is laid out 2x2 so the whole
sheet stays under the ~2000 px render cap; a wider grid silently drops the
magnification below the 9x floor while still looking fine, which is the failure
the brief's magnification rule exists to stop.

Prints the achieved magnification for every sheet. If it reads below 9.0, the
sheet is void - cut fewer tiles, not smaller ones.
"""
import argparse
import io
import json
import os
import sys

from PIL import Image, ImageDraw


def tile(im, box, bw, bh):
    cx = (box[0] + box[2]) // 2
    cy = (box[1] + box[3]) // 2
    W, H = im.size
    x0 = max(0, min(W - bw, cx - bw // 2))
    y0 = max(0, min(H - bh, cy - bh // 2))
    return im.crop((x0, y0, x0 + bw, y0 + bh))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--marks", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--box", default="105x105")
    ap.add_argument("--site-box", default=None,
                    help="WIDER source window for the SITE tile only, e.g. "
                         "200x105. The HEIGHT must match --box: magnification "
                         "is set by height, so an equal height keeps the site "
                         "and its controls at one scale while letting the site "
                         "show the whole word. Use it when the mark locator "
                         "framed the wrong component.")
    ap.add_argument("--only", default=None, help="comma-separated labels")
    ap.add_argument("--tile-h", type=int, default=945)
    args = ap.parse_args(argv)

    bw, bh = (int(v) for v in args.box.lower().split("x"))
    if args.site_box:
        sw, sh = (int(v) for v in args.site_box.lower().split("x"))
        if sh != bh:
            raise SystemExit("--site-box height must equal --box height, "
                             "otherwise the site and its controls sit at "
                             "different magnifications and the sheet is void")
    else:
        sw, sh = bw, bh
    only = set(args.only.split(",")) if args.only else None
    scale = args.tile_h / float(bh)
    tw, th = int(bw * scale), args.tile_h
    os.makedirs(args.outdir, exist_ok=True)

    for m in json.load(io.open(args.marks, encoding="utf-8")):
        if only and m["label"] not in only:
            continue
        im = Image.open(m["strip"]).convert("L")
        sbox = m["wordbox"] if args.site_box else m["box"]
        items = [(tile(im, sbox, sw, sh), "SITE %s" % m["word"])]
        # ⚠ FOUR TILES IS THE HARD CEILING. Five tiles makes the sheet ~2970 px
        # tall, the renderer scales it to fit ~2000 px, and the whole sheet
        # silently drops to ~6x while still looking perfectly sharp. That is the
        # magnification trap the brief warns about, so the ordering below takes
        # one of each class first and spends the last slot on a spare.
        ring = m.get("ring") or []
        ev = m.get("e") or []
        for kind, cs in (("RING", ring), ("<e>", ev)):
            if not cs:
                print("%-18s ⚠ NO %s CONTROL - sheet is VOID" % (m["label"], kind))
        order = [("RING", c) for c in ring[:1]] + [("<e>", c) for c in ev[:1]]
        spare = [("RING", c) for c in ring[1:]] + [("<e>", c) for c in ev[1:]]
        # A wide whole-word site tile fills its own row, so only TWO controls
        # fit under the 2000 px ceiling; a third would add a third row and
        # quietly cost a third of the magnification.
        for kind, c in (order + spare)[:2 if args.site_box else 3]:
            items.append((tile(im, c["box"], bw, bh),
                          "%s ctrl %s" % (kind, c["form"])))
        label_h, pad = 34, 8
        # rows: the site alone on row 0 when it is a wide whole-word tile,
        # otherwise two per row.
        rows_of = ([[items[0]], items[1:3]] if args.site_box
                   else [items[i:i + 2] for i in range(0, len(items), 2)])
        rows_of = [r for r in rows_of if r]
        widths = [sum(int(c.width * scale) + pad for c, _ in r) + pad
                  for r in rows_of]
        sheet = Image.new("L", (max(widths),
                                len(rows_of) * (th + label_h + pad) + pad), 255)
        dr = ImageDraw.Draw(sheet)
        for ri, row in enumerate(rows_of):
            x = pad
            y = pad + ri * (th + label_h + pad)
            for crop, lab in row:
                w = int(crop.width * scale)
                sheet.paste(crop.resize((w, th), Image.LANCZOS), (x, y))
                dr.rectangle([x, y, x + w, y + th], outline=0)
                dr.text((x + 4, y + th + 8), lab, fill=0)
                x += w + pad
        out = os.path.join(args.outdir, m["label"] + ".png")
        sheet.save(out)
        mag = th / float(bh)
        flag = "" if mag >= 9.0 else "   ⚠ BELOW 9x - VOID"
        print("%-18s %s  %dx%d  %.1fx  strip=%s%s" % (
            m["label"], out, sheet.width, sheet.height, mag,
            os.path.basename(m["strip"]), flag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
