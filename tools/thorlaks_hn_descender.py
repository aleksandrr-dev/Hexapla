#!/usr/bin/env python
"""Measure DESCENDER INK under a capital, to test the owner's H/N rule.

    python tools/thorlaks_hn_descender.py            # the p37 panel set
    python tools/thorlaks_hn_descender.py --selftest

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

## What this is for

The owner ruled H/N on 2026-09-14 by naming a feature, not a verdict:

    ▶ «N in nafn is the only one with the tail going down.
       the rest have the tail going up.»

★★ **A descender is ARITHMETIC, not perception.** «Ink below the baseline» can
be counted. That makes his rule FALSIFIABLE without any model looking at the
page — which matters, because every model instrument tried on this letter has
been MEASURED UNFIT:

- two Sonnet `ø` readers, 30/30 controls closed, **disjoint** result sets;
- the H/N adjudicator invented the RIGHT-STEM feature and called a known-`H`
  word `N` at moderate-high confidence;
- the locator, **told** the words were `Hun` and `Høfud`, transcribed them
  `Nun` and `Nøfud` anyway.

⇒ ⛔ A model's perceptual verdict on this typeface is not evidence. A pixel
COUNT is a different instrument, and this is the first one built.

## ⛔ What it is NOT

⛔ **NOT a corpus patcher and NOT an adjudicator.** It measures FIVE recorded
boxes on one page to see whether the owner's stated feature survives
measurement. It assigns no letter to any site in `research/_parts/`.
⛔ `NOT BY REGEX, NOT BY DICTIONARY` is unaffected — this is neither.

## ⛔⛔ RESULT 2026-09-14: THE CONTROL DID NOT FIRE. THIS TOOL IS NOT A SCREEN.

After two REAL bugs were fixed — a 2 px "capital" (speck, not letter) and a
baseline parked at row 57 inside the descender tail — the two KNOWN letters
still do not separate, and they separate the WRONG WAY:

    control-N  Nafn      6.4 % ink below the baseline
    control-H  Herodes  10.2 %

⇒ ⛔ **Below-baseline ink does not distinguish `N` from `H` on this page.**

⚠⚠ **THE HONEST READING IS THAT THIS MEASURES THE WRONG FEATURE, NOT THAT THE
OWNER IS WRONG.** His words were «the tail going down / the tail going up».
That is plausibly the RIGHT STEM'S TERMINAL DIRECTION, not a descender crossing
the baseline — and note the measured-unfit adjudicator independently located
its (wrong-valued) signal on the same right stem. Both describers point at the
right side of the letter; only my operationalisation assumed "down" meant
"below the baseline".

★★ **STOPPED HERE ON PURPOSE.** Fixing a 2 px segmentation bug is repairing an
instrument; redefining the FEATURE until the control passes is tuning the
instrument to produce the expected answer, which is the failure this project
hammers. ▶ The next step is not another constant — it is asking the owner what
the tail IS. ▶ `research/_evidence/thorlaks_hn_owner_verdict_2026-09-14.md`

## The control, and it must fire before any probe is believed

`Nafn` is 29:0 `N` across the merged corpus; `Herodes` is a confident `H` on the
same printed line. ▶ **If the measurement cannot separate those two, it is
INERT and every probe number it prints is meaningless.** Exit 3 in that case.

⚠ The baseline is derived from EACH LINE's own ink profile. A crop whose edge is
in the wrong place corrupts its own yardstick (the `idx 54` / line-cliff class).
The three crops used here are from `mark_kit` p37, prepped 2026-09-06.

Exit 0 = the control separated the two knowns; probe numbers printed.
Exit 3 = control INERT, or a crop/box could not be read.
"""
import argparse
import io
import os
import sys

try:
    from PIL import Image
except ImportError:                                           # noqa: BLE001
    sys.stderr.write("pillow not available\n")
    sys.exit(3)

PREP = "research/_prep/mark_kit/p37"

# Recorded in research/_evidence/thorlaks_hn_second_adjudication_2026-09-13.md.
# (label, line file, x0, x1, kind)  kind: control-N / control-H / probe
PANELS = [
    ("Nafn",    "line25.png", 1063, 1221, "control-N"),
    ("Herodes", "line25.png",  692,  922, "control-H"),
    ("Nuors",   "line40.png", 1157, 1321, "probe"),
    ("Hun",     "line40.png",  362,  488, "probe"),
    ("Hofud",   "line41.png",   83,  255, "probe"),
]


def otsu(hist, total):
    best_t, best_var = 128, -1.0
    sum_all = sum(i * hist[i] for i in range(256))
    w0 = 0.0
    sum0 = 0.0
    for t in range(256):
        w0 += hist[t]
        if w0 == 0:
            continue
        w1 = total - w0
        if w1 == 0:
            break
        sum0 += t * hist[t]
        m0 = sum0 / w0
        m1 = (sum_all - sum0) / w1
        var = w0 * w1 * (m0 - m1) ** 2
        if var > best_var:
            best_var, best_t = var, t
    return best_t


def load_ink(path):
    """-> (ink rows as list of lists of bool, width, height). Ink = dark."""
    img = Image.open(path).convert("L")
    w, h = img.size
    px = list(img.getdata())
    hist = [0] * 256
    for v in px:
        hist[v] += 1
    t = otsu(hist, w * h)
    ink = [[px[y * w + x] <= t for x in range(w)] for y in range(h)]
    return ink, w, h


#: Row-ink fraction of the line's peak that marks the BASELINE.
#: ⚠ Measured on mark_kit p37 2026-09-14: the x-height body holds >80 % of peak
#: down to row ~48, then falls off a cliff (49→73 %, 51→53 %, 53→33 %) into a
#: long 20→5 % descender tail. The knee sits at ~50 %. ⛔ An earlier 20 %
#: threshold put the baseline at row 57 — INSIDE the descender tail — so almost
#: no ink could count as "below" and the control went inert.
BASELINE_FRAC = 0.50

#: A capital is ~33-42 px wide on these 1976 px crops. ⚠ Anything much narrower
#: is a speck, not a letter: the first attempt returned 2 px for `Nafn`'s N.
MIN_GLYPH_W = 18


def baseline(ink, w, h):
    """Row where the dense body band ends = the baseline.

    ⚠ Derived from THIS LINE's own profile. A crop whose edge is in the wrong
    place corrupts its own yardstick (the line-cliff class) — which is why the
    two known letters must separate before any probe is read.
    """
    rows = [sum(1 for x in range(w) if ink[y][x]) for y in range(h)]
    peak = max(rows) if rows else 0
    if peak == 0:
        return None
    thresh = peak * BASELINE_FRAC
    hi = rows.index(peak)
    while hi + 1 < h and rows[hi + 1] >= thresh:
        hi += 1
    return hi


def first_glyph_cols(ink, h, x0, x1, gap=3):
    """Columns of the FIRST REAL glyph in the box = the capital.

    ⚠ Runs narrower than MIN_GLYPH_W are skipped as specks — a stray mark a few
    px left of the letter otherwise ends the scan immediately.
    """
    cols = [any(ink[y][x] for y in range(h)) for x in range(x0, x1)]
    i = 0
    n = len(cols)
    while i < n:
        while i < n and not cols[i]:
            i += 1
        if i >= n:
            return None
        start = i
        blanks = 0
        end = n
        for j in range(i, n):
            if cols[j]:
                blanks = 0
            else:
                blanks += 1
                if blanks >= gap:
                    end = j - blanks + 1
                    break
        else:
            end = n
        if end - start >= MIN_GLYPH_W:
            return x0 + start, x0 + end
        i = end + 1                      # a speck — keep looking
    return None


def measure(panel, cache):
    label, fname, x0, x1, kind = panel
    path = os.path.join(PREP, fname)
    if path not in cache:
        if not os.path.exists(path):
            return None
        cache[path] = load_ink(path)
    ink, w, h = cache[path]
    base = baseline(ink, w, h)
    if base is None:
        return None
    span = first_glyph_cols(ink, h, x0, min(x1, w))
    if span is None:
        return None
    gx0, gx1 = span
    below = 0
    total = 0
    for x in range(gx0, gx1):
        for y in range(h):
            if ink[y][x]:
                total += 1
                if y > base:
                    below += 1
    if total == 0:
        return None
    return {
        "label": label, "kind": kind, "baseline": base,
        "cols": (gx0, gx1), "ink": total, "below": below,
        "frac": 100.0 * below / total,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    cache = {}
    rows = []
    for p in PANELS:
        r = measure(p, cache)
        if r is None:
            sys.stderr.write("COULD NOT MEASURE %s - not a pass.\n" % p[0])
            return 3
        rows.append(r)

    by = dict((r["label"], r) for r in rows)
    n_ctl, h_ctl = by["Nafn"], by["Herodes"]
    separated = n_ctl["frac"] > h_ctl["frac"]

    if a.selftest:
        print("  control-N Nafn    below-baseline ink = %5.1f %%" % n_ctl["frac"])
        print("  control-H Herodes below-baseline ink = %5.1f %%" % h_ctl["frac"])
        print("  N > H ? %s (want True)" % separated)
        if separated:
            print("SELFTEST PASSED - the two KNOWN letters separate on this feature.")
            return 0
        print("SELFTEST FAILED - INERT. The probe numbers below would be noise.")
        return 3

    print("%-9s %-10s %9s %9s %9s   %s"
          % ("panel", "kind", "baseline", "ink px", "below", "below-baseline %"))
    print("-" * 78)
    for r in rows:
        print("%-9s %-10s %9d %9d %9d   %5.1f %%"
              % (r["label"], r["kind"], r["baseline"], r["ink"],
                 r["below"], r["frac"]))
    print()
    if not separated:
        sys.stderr.write("CONTROL INERT: Nafn (%.1f %%) did not exceed "
                         "Herodes (%.1f %%). Probes above are NOISE.\n"
                         % (n_ctl["frac"], h_ctl["frac"]))
        return 3
    print("CONTROL FIRED: known-N %.1f %% > known-H %.1f %% below the baseline."
          % (n_ctl["frac"], h_ctl["frac"]))
    mid = (n_ctl["frac"] + h_ctl["frac"]) / 2.0
    print("Midpoint between the two knowns: %.1f %%." % mid)
    for r in rows:
        if r["kind"] != "probe":
            continue
        side = "N (tail down)" if r["frac"] > mid else "H (tail up)"
        print("  %-8s %5.1f %%  falls on the %s side" % (r["label"], r["frac"], side))
    print()
    print("MEASUREMENT ONLY - five boxes on one page. It tests the owner's")
    print("stated feature; it does not adjudicate any site in research/_parts/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
