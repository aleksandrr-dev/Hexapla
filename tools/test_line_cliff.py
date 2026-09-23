# -*- coding: utf-8 -*-
"""Control for prep_chunk.choose_frac() — the merged-line cliff fix.

    PYTHONIOENCODING=utf-8 python tools/test_line_cliff.py        # must exit 0
    HEXAPLA_NO_CLIFF=1 ... python tools/test_line_cliff.py        # must exit 1

⛔ IF BOTH EXIT 0 THE CONTROL IS INERT AND PROVES NOTHING. The second run
disables the fix inside choose_frac; the broken pages must go back to being
broken, or this file is testing nothing.

Two assertions, both required, because either alone is passable by a stub:

  KNOWN-GOOD  six healthy v3 pages must keep LINE_FRAC exactly and emit the
              SAME number of line rects as before the fix. ~270 pages are
              already prepped, read and MERGED at that geometry; a fix that
              moves them voids sound addresses to repair broken ones.
  KNOWN-BAD   the three pages thorlaks_crop_heights.py names as having a
              broken line finder must re-choose, and must land inside the
              kit's own line band. 31 crops on a page printing ~54 lines is
              the defect; anything still under the band has not been fixed.

⚠ The expected counts below are RAW line_rects() runs, not crop counts —
short_line_rects() adds its recoveries afterwards in main().
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz

import prep_chunk as pc

VOL = 3
# idx: line_rects() runs at LINE_FRAC, measured 2026-09-13 before the fix.
HEALTHY = {59: 50, 60: 55, 63: 55, 64: 52, 65: 52, 67: 53}
# idx: runs before the fix — the defect. crop_heights.py flags all three.
BROKEN = {61: 27, 62: 25, 66: 11}
BAND_LO = 40        # a v3 page of continuous setting prints ~50-60 lines
DISABLED = bool(os.environ.get("HEXAPLA_NO_CLIFF"))


def rows_for(doc, idx):
    page = doc[idx]
    block, _ = pc.text_block(page)
    im = pc._gray(page, pc.PROFILE_ZOOM)
    x0 = int((block.x0 - page.rect.x0) * pc.PROFILE_ZOOM)
    x1 = int((block.x1 - page.rect.x0) * pc.PROFILE_ZOOM)
    band = im.crop((max(x0, 0), 0, min(x1, im.width), im.height))
    col = band.resize((1, band.height))
    return [col.getpixel((0, y)) / 255.0 for y in range(band.height)]


def main():
    pdf = pc.RESEARCH / ("thorlaks_v%d.pdf" % VOL)
    if not pdf.is_file():
        sys.stderr.write("CANNOT RUN: %s not found. A check that cannot run "
                         "did not pass.\n" % pdf)
        return 2
    doc = fitz.open(pdf)
    fails = []
    print("mode: %s" % ("FIX DISABLED (known-bad control)" if DISABLED
                        else "fix live"))

    for idx, before in sorted(HEALTHY.items()):
        rows = rows_for(doc, idx)
        frac, note = pc.choose_frac(rows)
        n = len(pc._runs(rows, frac, min_len=6))
        ok = (frac == pc.LINE_FRAC and n == before)
        print("  known-good idx %-3d frac %.2f  %2d runs (was %2d)  %s"
              % (idx, frac, n, before, "ok" if ok else "MOVED"))
        if not ok:
            fails.append("healthy idx %d moved: frac %.2f, %d runs, expected "
                         "%.2f and %d" % (idx, frac, n, pc.LINE_FRAC, before))

    for idx, before in sorted(BROKEN.items()):
        rows = rows_for(doc, idx)
        frac, note = pc.choose_frac(rows)
        n = len(pc._runs(rows, frac, min_len=6))
        ok = (frac != pc.LINE_FRAC and n >= BAND_LO and n > before)
        print("  known-bad  idx %-3d frac %.2f  %2d runs (was %2d)  %s"
              % (idx, frac, n, before, "recovered" if ok else "STILL BROKEN"))
        if not ok:
            fails.append("broken idx %d not recovered: frac %.2f, %d runs "
                         "(was %d, band floor %d)"
                         % (idx, frac, n, before, BAND_LO))
    doc.close()

    if fails:
        for f in fails:
            sys.stderr.write("FAIL: %s\n" % f)
        if DISABLED:
            print("\n^ EXPECTED with the fix disabled. The control fires.")
        return 1
    if DISABLED:
        sys.stderr.write(
            "\nFAIL: the fix was DISABLED and every page still passed. The "
            "control is inert and proves nothing about the live run.\n")
        return 1
    print("\nPASS: 6 healthy pages unmoved, 3 broken pages recovered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
