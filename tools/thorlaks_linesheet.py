# -*- coding: utf-8 -*-
"""Stack a page's pre-cut line crops into a few labelled sheets, for ONE read each.

    python tools/thorlaks_linesheet.py --dir research/_prep/philippians_v2/p181
    python tools/thorlaks_linesheet.py --dir ... --per 23 --out _work/sheets

## Why this exists

`prep_chunk.py` cuts every text line of a page to its own `lineNN.png` at 8.3x.
That is exactly right for *re-reading one disputed line* and exactly wrong for
*reading the page*: a 46-line page becomes 46 image reads, and the campaign's
own cost rule (CLAUDE.md) is to batch small images into one composite rather
than spend one read per site.

This stacks them back into a small number of sheets.

## The resolution arithmetic, which is the whole point

The vision API scales an image so its LONG edge is at most ~1568 px. A line
crop is ~2001 px wide, so width is the long edge and the scale factor is
1568/2001 = 0.78 **no matter how many lines are stacked** - right up until the
stack grows taller than it is wide. So:

    effective zoom = 8.3 * 0.78 = ~6.5x   for any stack up to ~2000 px tall

Stacking 23 lines therefore costs one read at ~6.5x, and stacking 1 line costs
one read at the same ~6.5x. The sheet is free resolution-wise, and 6.5x is far
above the 2.6x this campaign calls confident continuous-transcription zoom.

## What it does NOT do

It does not read anything - same contract as `prep_chunk.py`. Pixels only.

WARNING A sheet is for CONTINUOUS READING. A disputed letter is settled on the
individual `lineNN.png` at the full 8.3x, or by `thorlaks_sorts.py`, never by
squinting at the sheet. The sheet lowers cost; it does not lower the evidence
bar.

WARNING Line N is not verse N. `prep_chunk.py`'s segmentation is a heuristic
that can merge touching lines and split a line carrying a tall initial. The
labels here are crop indices, nothing more - they exist so a disputed line can
be named and re-read, not to number anything in the text.
"""
import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GUTTER = 62          # left margin holding the crop index
PAD = 6              # vertical gap between lines
BG = (255, 255, 255)
RULE = (170, 170, 170)
LABEL = (0, 0, 0)
# A crop this narrow is a failed block detection, not a line of text. p180 of
# the philippians_v2 prep emits 46-px-wide crops for exactly this reason; they
# are dropped with a warning rather than silently stacked into a useless sheet.
MIN_WIDTH = 200


def line_crops(d):
    fs = sorted(d.glob("line*.png"),
                key=lambda p: int(re.search(r"(\d+)", p.name).group(1)))
    if not fs:
        sys.exit(f"no line*.png under {d}")
    return fs


def build(d, per, outdir):
    fs = line_crops(d)
    good, bad = [], []
    for f in fs:
        im = Image.open(f)
        (good if im.width >= MIN_WIDTH else bad).append((f, im))
    if bad:
        print(f"  WARNING dropped {len(bad)} crop(s) under {MIN_WIDTH}px wide "
              f"(failed block detection): {', '.join(f.name for f, _ in bad)}")
    if not good:
        print(f"  WARNING {d.name}: no usable line crops - read page.png instead")
        return []

    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for s in range(0, len(good), per):
        batch = good[s:s + per]
        w = GUTTER + max(im.width for _, im in batch)
        h = sum(im.height + PAD for _, im in batch) + PAD
        sheet = Image.new("RGB", (w, h), BG)
        draw = ImageDraw.Draw(sheet)
        y = PAD
        for f, im in batch:
            n = re.search(r"(\d+)", f.name).group(1)
            draw.text((8, y + im.height // 2 - 6), n, fill=LABEL)
            sheet.paste(im, (GUTTER, y))
            y += im.height + PAD
            draw.line([(0, y - PAD // 2), (w, y - PAD // 2)], fill=RULE)
        out = outdir / f"{d.name}_sheet{s // per}.png"
        sheet.save(out)
        # The scale the API will apply, so the effective zoom is never a guess.
        scale = 1568 / max(sheet.size)
        written.append(out)
        print(f"  {out.name}: {len(batch)} lines ({batch[0][0].name}-"
              f"{batch[-1][0].name}), {sheet.width}x{sheet.height}px, "
              f"~{8.3 * min(scale, 1.0):.1f}x effective")
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True,
                    help="a prep page directory, e.g. research/_prep/<chunk>/p181")
    ap.add_argument("--per", type=int, default=23,
                    help="line crops per sheet (default 23; see the docstring's "
                         "resolution arithmetic before raising it)")
    ap.add_argument("--out", default=None,
                    help="output dir (default: <dir>/../_sheets)")
    a = ap.parse_args()
    d = Path(a.dir)
    if not d.is_dir():
        sys.exit(f"not a directory: {d}")
    outdir = Path(a.out) if a.out else d.parent / "_sheets"
    print(f"{d}:")
    build(d, a.per, outdir)


if __name__ == "__main__":
    main()
