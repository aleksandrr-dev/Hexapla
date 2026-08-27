# -*- coding: utf-8 -*-
"""Render Þorláksbiblía running-head strips as labelled montages.

Navigation aid ONLY. The running head carries the book name and, on a recto,
the folio numeral — enough to locate a book boundary without rendering whole
pages. **Never transcribe from a strip**; the campaign brief fixes 2.6x full
pages as the transcription zoom and 2.0x as the navigation floor.

    python tools/thorlaks_strips.py --vol 3 --from 0 --to 255 --step 8

⚠ The page index is authoritative, not the folio: v1 idx = 2*folio + 14,
v2 idx = 2*folio + 6, v3 idx = 2*folio. Every strip is labelled with its PDF
index so a montage can never be mis-attributed the way the superseded
strip-composite map in `thorlaks_precampaign_checks.md` was.
"""
import argparse
from pathlib import Path

import fitz

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
OUT = Path(r"C:/Users/infer/AppData/Local/Temp/claude/thorlaks_nav")

# fraction of page height kept, measured from the top
HEAD_FRAC = 0.115
ZOOM = 1.7
PER_SHEET = 10
LABEL_W = 118


def render(vol, indices, zoom=ZOOM, head=HEAD_FRAC, per_sheet=PER_SHEET):
    doc = fitz.open(RESEARCH / f"thorlaks_v{vol}.pdf")
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for s in range(0, len(indices), per_sheet):
        batch = [i for i in indices[s:s + per_sheet] if 0 <= i < doc.page_count]
        if not batch:
            continue
        pixes = []
        for idx in batch:
            page = doc[idx]
            r = page.rect
            clip = fitz.Rect(r.x0, r.y0, r.x1, r.y0 + r.height * head)
            pixes.append((idx, page.get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                               clip=clip)))
        w = max(p.width for _, p in pixes) + LABEL_W
        h = sum(p.height + 6 for _, p in pixes)
        sheet = fitz.open()
        pg = sheet.new_page(width=w, height=h)
        y = 0
        for idx, p in pixes:
            pg.insert_image(fitz.Rect(LABEL_W, y, LABEL_W + p.width, y + p.height),
                            pixmap=p)
            pg.insert_text((6, y + p.height / 2), f"idx {idx}",
                           fontsize=15, color=(0.8, 0, 0))
            pg.draw_line(fitz.Point(0, y + p.height + 3),
                         fitz.Point(w, y + p.height + 3), color=(0.7, 0.7, 0.7))
            y += p.height + 6
        out = OUT / f"v{vol}_{batch[0]:04d}_{batch[-1]:04d}.png"
        pg.get_pixmap(matrix=fitz.Matrix(1, 1)).save(out)
        made.append(out)
    doc.close()
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vol", type=int, required=True, choices=(1, 2, 3))
    ap.add_argument("--from", dest="lo", type=int, required=True)
    ap.add_argument("--to", dest="hi", type=int, required=True)
    ap.add_argument("--step", type=int, default=8)
    ap.add_argument("--zoom", type=float, default=ZOOM)
    ap.add_argument("--head", type=float, default=HEAD_FRAC)
    ap.add_argument("--per-sheet", type=int, default=PER_SHEET)
    a = ap.parse_args()
    idxs = list(range(a.lo, a.hi + 1, a.step))
    for p in render(a.vol, idxs, a.zoom, a.head, a.per_sheet):
        print(p)


if __name__ == "__main__":
    main()
