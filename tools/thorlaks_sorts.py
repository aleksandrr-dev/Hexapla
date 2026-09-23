# -*- coding: utf-8 -*-
"""Adjudicate p-family sorts in the Þorláksbiblía by MEASUREMENT, not by eye.

⚠⚠ WHY THIS EXISTS. The campaign's hardest decision is telling `þ ꝑ ꝥ p`
apart, and it has already been got wrong twice: Philemon and James BOTH
recorded `ꝑ = fyrer` as *confirmed*, each with genuine same-page
corroboration, and both were wrong (SESSION_HANDOFF_2026-08-11 §2). The
failure mode is not bad eyesight — it is that the Icelandic word "wants" an
`f`, so a reader supplies one and the result reads fluently either way. No
downstream check catches it, because nothing about the output looks wrong.

▶ So this tool never looks at words, never looks at context, and does not know
what the text says. It measures ink geometry on ONE line crop and reports
numbers. The transcriber still decides; the tool's job is to make the decision
falsifiable.

⚠ AND IT REPLACES ADVICE THAT CANNOT WORK. `_prep/<chunk>/MANIFEST.md` tells
the transcriber to re-render a disputed line at 20-40x. But `prep_chunk.py`
sets `READ_ZOOM = 8.3` and documents it as *the native ceiling of these
scans* — the crops are already at it. Rendering higher only interpolates: it
adds pixels and zero evidence, while feeling like progress. Magnification was
never the answer; discrimination is.

## The discriminator

In this face the four sorts differ by where the ink goes relative to the
body band (the x-height zone, which every minuscule occupies):

    þ  ascender, no descender          ꝑ  descender, no ascender, barred
    ꝥ  ascender + bar                  p  descender, no ascender, unbarred

So `ascends?` and `descends?` separate þ/ꝥ from ꝑ/p outright, and the two
questions are answerable from a row-ink profile without reading anything.

    python tools/thorlaks_sorts.py --dir research/_prep/2peter/p207 --line 41
    python tools/thorlaks_sorts.py --dir ... --line 41 --montage

⚠ THE BAR (ꝑ vs p, þ vs ꝥ) IS NOT MEASURED. A bar is a few pixels of ink
crossing a stem and at 8.3x it is at the noise floor. The tool reports
ascend/descend only and says UNRESOLVED for the bar. Do not infer it from
this tool's silence.

⚠ CALIBRATE BEFORE TRUSTING. `--calibrate` measures every glyph on the line
and prints the band it derived. If the band is wrong (a line of majuscules, a
drop-cap run, a line that merged two rows), every measurement on that line is
wrong TOGETHER and consistently — which is the dangerous kind. Eyeball the
band against `page.png` once per page before believing a verdict.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ink threshold as a fraction of the line's dynamic range. Deliberately NOT
# Otsu: prep_kxii.py documents Otsu failing on these scans where a fixed
# percentile held, because the paper tone varies far more than the ink does.
INK_FRAC = 0.55

# A column run shorter than this is speckle, not a glyph stem.
MIN_GLYPH_W = 3

# Fraction of the line's peak row-ink that still counts as "body band".
BAND_FRAC = 0.45

# Ink this far outside the band counts as a real ascender/descender rather
# than the natural overshoot of round letters (o, e, s bulge a pixel or two).
OVERSHOOT = 0.12       # as a fraction of band height


def load_ink(path):
    """-> (w, h, ink[y][x] bool). Ink is dark-on-light, so invert."""
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    vals = [px[x, y] for y in range(h) for x in range(w)]
    lo, hi = min(vals), max(vals)
    cut = lo + (hi - lo) * (1.0 - INK_FRAC)
    ink = [[px[x, y] <= cut for x in range(w)] for y in range(h)]
    return w, h, ink


def body_band(w, h, ink):
    """(top, bottom) of the x-height zone, from the row-ink profile.

    Every minuscule puts ink in this zone, so it is the profile's plateau.
    Ascenders and descenders are the thin tails above and below it.
    """
    rows = [sum(1 for x in range(w) if ink[y][x]) for y in range(h)]
    peak = max(rows) if rows else 0
    if not peak:
        return None
    cut = peak * BAND_FRAC
    hits = [y for y, n in enumerate(rows) if n >= cut]
    return (min(hits), max(hits)) if hits else None


def column_extents(w, h, ink):
    """Per-column (top, bottom) ink row, or None. The primitive that works.

    ⚠ THIS REPLACED GLYPH SEGMENTATION, WHICH DOES NOT WORK HERE. The first
    version of this tool split the line into column runs of ink and measured
    each as a glyph. In this face the letters TOUCH — a "run" came back 116px
    wide, several letters joined — so almost every run reported BOTH an
    ascender and a descender and the verdicts were meaningless. Same lesson
    prep_kxii.py records: geometry alone cannot pick the unit; measure
    something that does not need the unit isolated.

    A p-family sort is decided by its STEM, and a stem is a narrow column of
    ink that runs well above or well below the body band. So measure columns,
    not glyphs, and let the transcriber point at the stem.
    """
    out = []
    for x in range(w):
        top = bot = None
        for y in range(h):
            if ink[y][x]:
                if top is None:
                    top = y
                bot = y
        out.append((top, bot))
    return out


def window_verdict(cols, band, at, half):
    """Measure the extreme ascender/descender in a narrow window around `at`."""
    b_top, b_bot = band
    bh = max(1, b_bot - b_top)
    lo, hi = max(0, at - half), min(len(cols) - 1, at + half)
    best_a = best_d = 0.0
    ax = dx = None
    for x in range(lo, hi + 1):
        top, bot = cols[x]
        if top is None:
            continue
        a = (b_top - top) / bh
        d = (bot - b_bot) / bh
        if a > best_a:
            best_a, ax = a, x
        if d > best_d:
            best_d, dx = d, x
    return best_a, ax, best_d, dx


def ascender_strip(cols, band, w, step):
    """A whole-line map: where does ink rise above / fall below the band?

    Lets the transcriber FIND the stems without knowing an x in advance —
    align the strip under the line image and the p-family sorts stand out.
    """
    b_top, b_bot = band
    bh = max(1, b_bot - b_top)
    up, dn, ruler = [], [], []
    for i, x in enumerate(range(0, w, step)):
        a = d = 0.0
        for xx in range(x, min(w, x + step)):
            top, bot = cols[xx]
            if top is None:
                continue
            a = max(a, (b_top - top) / bh)
            d = max(d, (bot - b_bot) / bh)
        up.append("A" if a > OVERSHOOT else ("." if a > 0 else " "))
        dn.append("D" if d > OVERSHOOT else ("." if d > 0 else " "))
        ruler.append("|" if (x // step) % 10 == 0 else " ")
    return "".join(up), "".join(dn), "".join(ruler)


def glyph_runs(w, h, ink):
    """Column runs of ink -> [(x0, x1)]. COARSE INDEX ONLY — see the warning
    in column_extents: these are touching-letter clusters, not glyphs."""
    cols = [any(ink[y][x] for y in range(h)) for x in range(w)]
    runs, start = [], None
    for x, on in enumerate(cols + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            if x - start >= MIN_GLYPH_W:
                runs.append((start, x - 1))
            start = None
    return runs


def measure(run, h, ink, band):
    """Ascender/descender extent of one column run, in pixels and band-units."""
    x0, x1 = run
    top, bot = None, None
    for y in range(h):
        if any(ink[y][x] for x in range(x0, x1 + 1)):
            if top is None:
                top = y
            bot = y
    if top is None:
        return None
    b_top, b_bot = band
    bh = max(1, b_bot - b_top)
    asc = (b_top - top) / bh
    desc = (bot - b_bot) / bh
    return {
        "x0": x0, "x1": x1, "top": top, "bot": bot,
        "asc": asc, "desc": desc,
        "ascends": asc > OVERSHOOT,
        "descends": desc > OVERSHOOT,
    }


def verdict(m):
    """p-family verdict from geometry ALONE. Never consults a word."""
    if m["ascends"] and not m["descends"]:
        return "ascender-only  -> þ / ꝥ family (bar UNRESOLVED)"
    if m["descends"] and not m["ascends"]:
        return "descender-only -> ꝑ / p family (bar UNRESOLVED)"
    if m["ascends"] and m["descends"]:
        return "BOTH — not a p-family sort (or a merged run)"
    return "neither — x-height letter"


def montage(path, runs, band, out):
    """Candidate glyphs side by side with the band drawn, for confirmation."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    strips = [im.crop((max(0, x0 - 2), 0, min(w, x1 + 3), h)) for x0, x1 in runs]
    if not strips:
        return None
    gap = 8
    total = sum(s.width for s in strips) + gap * (len(strips) + 1)
    sheet = Image.new("RGB", (total, h + 24), "white")
    x = gap
    for s in strips:
        sheet.paste(s, (x, 12))
        x += s.width + gap
    # band guides: everything between these lines is x-height
    for y in (band[0] + 12, band[1] + 12):
        for xx in range(sheet.width):
            sheet.putpixel((xx, y), (220, 30, 30))
    sheet.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="a _prep/<chunk>/pNNN directory")
    ap.add_argument("--line", type=int, required=True)
    ap.add_argument("--at", type=int, default=None,
                    help="x pixel of the disputed stem; omit for the line map")
    ap.add_argument("--half", type=int, default=8,
                    help="half-width of the --at window, px (default 8 = one stem)")
    ap.add_argument("--calibrate", action="store_true",
                    help="print the derived band and every run")
    ap.add_argument("--stems", action="store_true",
                    help="list descender-only stems (the p-family candidates)")
    ap.add_argument("--montage", action="store_true")
    a = ap.parse_args()

    path = Path(a.dir) / f"line{a.line:02d}.png"
    if not path.exists():
        sys.exit(f"no such crop: {path}")
    w, h, ink = load_ink(path)
    band = body_band(w, h, ink)
    if not band:
        sys.exit("no ink found — wrong crop?")
    print(f"{path.name}: {w}x{h}px   body band rows {band[0]}-{band[1]} "
          f"(height {band[1]-band[0]})")
    print("⚠ confirm that band looks like the x-height zone before trusting "
          "any verdict below\n")

    cols = column_extents(w, h, ink)

    if a.at is not None:
        asc, ax, desc, dx = window_verdict(cols, band, a.at, a.half)
        print(f"window x={a.at}±{a.half}")
        print(f"  max ascender  {asc:5.2f} band-heights"
              f"{'' if ax is None else f' at x={ax}'}")
        print(f"  max descender {desc:5.2f} band-heights"
              f"{'' if dx is None else f' at x={dx}'}")
        m = {"asc": asc, "desc": desc,
             "ascends": asc > OVERSHOOT, "descends": desc > OVERSHOOT}
        print(f"  -> {verdict(m)}")
        print("\n⚠ If BOTH fire, the window spans two letters — narrow --half "
              "until only the stem is inside.")
        return

    if a.stems:
        b_top, b_bot = band
        bh = max(1, b_bot - b_top)
        runs, cur = [], None
        for x in range(w):
            top, bot = cols[x]
            ok = False
            if top is not None:
                ok = ((bot - b_bot) / bh > OVERSHOOT
                      and (b_top - top) / bh <= OVERSHOOT)
            if ok and cur is None:
                cur = x
            elif not ok and cur is not None:
                if x - cur >= 3:
                    runs.append((cur, x - 1))
                cur = None
        print("descender-only stems — the ꝑ/p candidates on this line:")
        for x0, x1 in runs:
            print(f"  x {x0}-{x1}   centre {(x0 + x1) // 2}")
        print("\n⚠ NOT all of these are ꝑ. In this face f, g, j, y and the "
              "virgule descend too.\n  What the tool rules OUT is þ/ꝥ — which "
              "is exactly the confusion that\n  put a wrong «fyrer» into two "
              "books.")
        return

    step = max(1, w // 190)
    up, dn, ruler = ascender_strip(cols, band, w, step)
    print(f"ascender/descender map  (1 char = {step}px, | every {step*10}px)")
    print("  A = rises above band   D = falls below band\n")
    print("  " + up)
    print("  " + dn)
    print("  " + ruler)
    print("\nA column with A and no D under it is a þ/ꝥ stem; D with no A is "
          "ꝑ/p.\nRe-run with --at <x> for the number at one stem.")

    if a.montage:
        out = Path(a.dir) / f"line{a.line:02d}_sorts.png"
        montage(path, glyph_runs(w, h, ink), band, out)
        print(f"\nmontage -> {out}")
        print("red guides = body band. A þ breaks the TOP line; a ꝑ breaks "
              "the BOTTOM one.")


if __name__ == "__main__":
    main()
