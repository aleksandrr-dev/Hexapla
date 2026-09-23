#!/usr/bin/env python
"""Control, BOTH WAYS, for the contact-sheet row-packing slice bug (2026-09-21).

    python tools/test_contact_sheet_wrap.py          -> exit 0 (the fix holds)
    HEXAPLA_NO_SHEETWRAP=1 python tools/...          -> exit 1 (known-bad fires)

THE BUG
-------
`build()` packed rows against a budget of `sum(tile.width + pad)` while the
drawing loop starts at `x = pad`. Every row was therefore exactly `pad` wider
than the packer believed. `sheet_w` was then computed as
`min(max_width, ...)`, so that overflow was not wrapped to the next row and not
widened away - it was SLICED off the right edge of the sheet.

Why that is not cosmetic: the sheet is an ADJUDICATION INSTRUMENT. A tile
sliced in half is still a tile a reader will rule on, and the reader cannot
tell a clipped glyph from a glyph that is genuinely missing its right-hand
stroke. That is the same failure shape as the amputated-descender crops that
made a subagent answer COMPLETE on seven broken capitals (handoff 2026-09-21
§6): the defect is invisible in the artifact that carries it.

WHAT IS ASSERTED
----------------
1. WRAP: with tiles packed to --max-width, every tile's right edge lies inside
   the sheet. Nothing is sliced.
2. NO-SHRINK: a single tile WIDER than max_width widens the sheet instead of
   losing pixels (the `if cur` guard lets such a tile through on purpose - the
   alternative, dropping it, would silently shrink the denominator).
3. The known-bad env var reproduces the original arithmetic, and assertion 1
   then FAILS. A control that cannot fail is not a control.
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

import contact_sheet  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BROKEN = os.environ.get("HEXAPLA_NO_SHEETWRAP") == "1"
PAD = 8
TILE_H = 60


# build() loads its source through a CLOSURE (`_src` is nested), so it cannot
# be monkeypatched - and should not be. A real file on disk exercises the real
# path, which is what a control is for.
_SRC_PATH = os.path.join(tempfile.gettempdir(), "_hexapla_sheet_control_src.png")


def _ensure_src():
    if not os.path.exists(_SRC_PATH):
        Image.new("RGB", (4000, 200), (200, 200, 200)).save(_SRC_PATH)
    return _SRC_PATH


def rows_of(boxes, max_width):
    """Build a real sheet and measure what it DREW."""
    return contact_sheet.build(
        _ensure_src(), boxes, TILE_H, max_width, PAD, label_h=12
    )


def tile_widths(boxes):
    """The widths build() will scale each box to (normalised to a common height)."""
    out = []
    for x0, y0, x1, y1, _ in boxes:
        h = y1 - y0
        w = x1 - x0
        out.append(max(1, int(round(w * TILE_H / float(h)))))
    return out


def right_margin_is_clean(sheet):
    """True when the sheet's rightmost PAD columns are pure background.

    ★ This measures THE ARTIFACT, not a re-derivation of the packer's
    arithmetic. An earlier version of this control re-implemented the correct
    packing and compared it to the sheet width - which asserts only that the
    test agrees with itself, and it PASSED under the known-bad env var. A
    control that passes on broken code is not a control.

    Correct behaviour leaves exactly `pad` of white margin at the right. The
    bug slices the last tile flush against the edge, so tile ink (grey) reaches
    the final column.
    """
    w, h = sheet.size
    px = sheet.load()
    # ⚠ Check the LAST TWO columns, not the last `pad`. The tile's grey
    # outline rectangle is drawn at `x + tile.width`, i.e. legitimately on the
    # FIRST column of the margin - counting that as ink made this assertion
    # fire on correct output too, and an assertion that fires both ways is as
    # useless as one that fires neither.
    for x in range(max(0, w - 2), w):
        for y in range(h):
            if px[x, y] != (255, 255, 255):
                return False, x
    return True, None


def main():
    fails = []

    # --- 1. WRAP: tuned so the MISSING LEAD PAD is exactly what overflows. ---
    # Boxes are 60px tall and TILE_H is 60, so width passes through unscaled.
    # w + pad = 250 and max_width = 1000, so four tiles measure exactly
    # max_width under the broken (lead=0) budget and are packed into one row;
    # drawing them from x=pad then needs 1008px, and the old `min()` clamped
    # the sheet to 1000 and sliced 8px off the last tile. With the lead pad
    # counted, only three tiles go in a row and nothing is clipped.
    boxes = [(i * 300, 0, i * 300 + 242, 60, "t%d" % i) for i in range(7)]
    sheet = rows_of(boxes, 1000)
    clean, bad_x = right_margin_is_clean(sheet)
    if not clean:
        fails.append(
            "WRAP: tile ink reaches column %d of a %dpx sheet - the last tile "
            "in the row is sliced off the right edge" % (bad_x, sheet.width)
        )
    else:
        print("  ✅ WRAP           %dpx sheet, right margin clean (no tile sliced)"
              % sheet.width)

    # --- 2. NO-SHRINK: one tile wider than max_width must widen the sheet ---
    big = [(0, 0, 3000, 60, "huge")]
    sheet2 = rows_of(big, 400)
    need = PAD + tile_widths(big)[0] + PAD
    if sheet2.width < need:
        fails.append(
            "NO-SHRINK: a tile needing %dpx was drawn onto a %dpx sheet"
            % (need, sheet2.width)
        )
    else:
        print("  ✅ NO-SHRINK      sheet widened to %dpx for a %dpx tile"
              % (sheet2.width, need))

    if BROKEN:
        if fails:
            print("\nknown-bad control (HEXAPLA_NO_SHEETWRAP=1): "
                  "the slice REPRODUCED, as it must")
            for f in fails:
                print("    " + f)
            return 1
        print("\n⛔ known-bad control did NOT reproduce the slice - "
              "the control is broken, and a control that cannot fail proves nothing")
        return 1

    if fails:
        print("\n⛔ FAIL")
        for f in fails:
            print("    " + f)
        return 1
    print("\ncontact_sheet wrap: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
