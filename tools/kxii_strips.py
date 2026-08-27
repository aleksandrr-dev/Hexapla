# -*- coding: utf-8 -*-
"""Render Karl XII 1703 pages as per-column reading strips.

    python tools/kxii_strips.py --pages 636-645 --out judith
    python tools/kxii_strips.py --pages 645 --strips 5 --out judith_tail

Companion to `prep_kxii.py`, not a replacement. prep_kxii cuts LINE crops,
which are the letter-level authority; this cuts each column into a handful of
tall strips, which is what makes reading a page affordable at all — a page
carries ~150 line crops but only 6 strips.

## ⚠ WHY THIS IS ALLOWED HERE WHEN `thorlaks_strips.py` FORBIDS IT

That tool says "never transcribe from a strip", and it is right about ITS
source: the Þorláksbiblía scans are aged, uneven, and their native ceiling is
8.3x, so letter decisions there genuinely need a line crop. This print is a
different object — clean dense movable type photographed at 2500x3423 — and
strip legibility was checked directly before this tool was written (the
745/746 seam, two columns at 1700 px, read word-for-word including the
small-type chapter argument).

▶ **The rule that carries over is the important one: when a word is not
certain, go to the line crop.** `prep_kxii.py --out <same name>` has already
written them. Strips make reading cheap; they do not make guessing acceptable.

## ⚠⚠ USE `--strips 5` OR MORE. THREE IS NOT ENOUGH TO READ THE DIACRITICS.

Found 2026-08-14, partway through the Judith chunk. At `--strips 3` a column
gives ~25 lines per image ≈ 80 px per line after the reader's downscale, and at
that scale **ä (two dots) and å (ring) are not reliably separable**. The
symptom is a run of readings that all look like å exactly where modern Swedish
has ä — «såkre», «Kåre», «wål», «åst» — which is a systematic misreading, not a
run of archaic spellings.

▶ Re-cropped at ~2.4x, the print separates them plainly: «sättia», «när»,
«sände» carry two dots; «åldsta», «mått» carry a ring. **The print really does
distinguish them, so the transcription must too**, and some of the å-looking
words ARE genuinely å — which is precisely why guessing by modern spelling is
not a repair.

`--strips 5` gives ~15 lines per image ≈ 130 px per line, above the resolution
at which the distinction was verified. Do not go back to 3 to save reads.

## ⚠ THE TRAP PAIRS OF THIS TYPEFACE

Calibrate on the large type at the head of each page before reading the body:
  · **ſ vs f** — the long-s has no crossbar, or only a left-side nub.
    Normalised to `s` (the ONE glyph normalisation this campaign allows).
  · **f vs p**, and **ʒ**-tailed sorts.
  · **w vs rv**, **å/ä/ö** as set — keep the print's own inconsistencies.
Everything else is transcribed diplomatically, as printed. Expansions go
per-site in the chunk's findings, never silently into the text.

## ⚠ WHAT IS DELIBERATELY NOT IN A STRIP

The marginal note columns sit OUTSIDE the printed frame and are apparatus, not
scripture; the frame-derived crop excludes them, exactly as prep_kxii does.
The chapter ARGUMENTS (smaller type, inline «v.25»-style references) ARE inside
the frame and will appear — they are not verses. Do not transcribe them as
scripture and do not let their digits enter the verse stream.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prep_kxii as P                                    # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(r"C:/Projects/Hexapla-releases/research/_strips_kxii")
LONG_EDGE = 2000        # the reader downscales past this; rendering bigger
                        # only wastes bytes and buys no legibility
OVERLAP = 0.04          # strips overlap slightly so no line falls in a seam

# ⚠ X-PAD IS NOT COSMETIC. `trim_column` fits ONE x-range to a whole column,
# but these scans are skewed by a fraction of a degree, so the true left edge
# drifts several px between the top and the foot of the same column. Measured
# on printed 637 column R: the drift clipped the FIRST CHARACTER off several
# lines low on the strip («så giöra» printed as «å giöra», «kom them vppå» as
# «them vppå»). A clipped initial is the most dangerous defect this pipeline
# can produce, because the line still reads as fluent Swedish and invites the
# transcriber to supply the missing letter from context — which is fabrication.
# The marginal note columns sit far outside the frame, so a pad this small
# cannot pull apparatus into the crop.
XPAD = 26


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="PRINTED page(s), e.g. 636-645")
    ap.add_argument("--out", required=True)
    ap.add_argument("--strips", type=int, default=3,
                    help="vertical strips per column (default 3 ≈ 25 lines)")
    # ⚠ HAND-FRAMING OVERRIDE. `find_frame` deliberately SKIPS a page rather
    # than guess, and BOOK-TRANSITION pages (a book ends and the next begins
    # mid-page) legitimately defeat it - 740 and 742 did on 2026-08-19, and the
    # campaign notes ~10 such pages remain. Without an override the only route
    # was cutting them by hand in a one-off script, which is how geometry stops
    # being reproducible. Pass the rules/band you measured instead.
    ap.add_argument("--rules", help="hand frame: 'L,C,R' x-positions of the "
                                    "left frame, centre rule and right frame")
    ap.add_argument("--band", help="hand text band: 'y0,y1'")
    ap.add_argument("--probe", action="store_true",
                    help="print rule candidates and the detected frame/band, "
                         "write nothing - use this to MEASURE a failing page")
    a = ap.parse_args()

    def _ints(txt, n, what):
        try:
            v = [int(x) for x in txt.split(",")]
        except ValueError:
            raise SystemExit("--%s wants %d integers, got %r" % (what, n, txt))
        if len(v) != n or list(v) != sorted(v):
            raise SystemExit("--%s wants %d increasing integers, got %r"
                             % (what, n, txt))
        return v

    hand_rules = _ints(a.rules, 3, "rules") if a.rules else None
    hand_band = _ints(a.band, 2, "band") if a.band else None

    lo, _, hi = a.pages.partition("-")
    pages = list(range(int(lo), int(hi or lo) + 1))
    outdir = OUT / a.out
    outdir.mkdir(parents=True, exist_ok=True)

    skipped = []
    for printed in pages:
        src = P.fetch(printed)
        im = Image.open(src).convert("L")
        if a.probe:
            cands = P.rule_candidates(im)
            fr = P.find_frame(im)
            print(f"  p{printed}: size={im.size} auto_frame={fr}")
            print(f"    rule candidates: {cands}")
            if fr:
                print(f"    auto band: {P.text_band(im, *fr)}")
            continue

        fr = hand_rules or P.find_frame(im)
        if not fr:
            skipped.append(printed)
            print(f"  p{printed}: NO FRAME FOUND — skipped", flush=True)
            continue
        L, C, R = fr
        if hand_band:
            y0, y1 = hand_band
            bnote = "HAND"
        else:
            y0, y1, bnote = P.text_band(im, L, C, R)
        if hand_rules:
            bnote = "HAND-RULES " + bnote
        full = Image.open(src)
        for tag, (bx0, bx1) in (("L", (L + 6, C - 6)), ("R", (C + 6, R - 6))):
            cx0, cx1 = P.trim_column(im, bx0, bx1, y0, y1)
            cx0, cx1 = max(cx0 - XPAD, 0), min(cx1 + XPAD, im.size[0])
            h = (y1 - y0) / a.strips
            pad = h * OVERLAP
            for i in range(a.strips):
                sy0 = max(y0 + i * h - pad, y0)
                sy1 = min(y0 + (i + 1) * h + pad, y1)
                c = full.crop((cx0, int(sy0), cx1, int(sy1)))
                k = LONG_EDGE / max(c.width, c.height)
                c.resize((int(c.width * k), int(c.height * k))).save(
                    outdir / f"p{printed}_{tag}{i+1}.png")
        print(f"  p{printed}: band {y0}-{y1} [{bnote}], "
              f"{a.strips} strips x 2 columns", flush=True)

    if skipped:
        print(f"\n⚠ NO FRAME, must be cut by hand: {skipped}")
    print(f"\nstrips: {outdir}")


if __name__ == "__main__":
    main()
