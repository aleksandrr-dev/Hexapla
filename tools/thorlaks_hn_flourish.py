#!/usr/bin/env python
"""Measure the TOP-LEFT FLOURISH's terminal height — the owner's H/N feature.

    python tools/thorlaks_hn_flourish.py            # the p37 panel set
    python tools/thorlaks_hn_flourish.py --selftest

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

## The feature, as the owner drew it (2026-09-14, annotated sheet)

He circled the **TOP-LEFT FLOURISH** of each capital and labelled it:

    Nafn     -> circled top-left, "Down"      (known N)
    Herodes  -> circled top-left, "up"        (known H)
    Huors / Hun / Hofud -> circled top-left, "up"

⛔ **NOT the right stem** — that is where the MEASURED-UNFIT adjudicator looked
(«plain straight vertical = N; curled/hooked shoulder = H») and it produced a
confident wrong answer on a known-`H` word.
⛔ **NOT a descender** — that was THIS session's wrong guess;
`tools/thorlaks_hn_descender.py` measured ink below the baseline, failed its
two-way control (`Nafn` 6.4 % vs `Herodes` 10.2 %, the wrong way round) and is
kept only as a recorded negative result.

★★ Both earlier attempts failed by mislocating the feature, not by mismeasuring
it. The owner's annotation is the first statement of WHERE to look that did not
come from a model.

## ⚠⚠ PRE-REGISTERED — ONE FEATURE, ONE TEST, REPORTED EITHER WAY

Stated BEFORE running, so the result cannot be chosen after the fact:

    feature = vertical position of the ink in the glyph's LEFTMOST columns,
              as a fraction of the glyph's own height (0.0 = top, 1.0 = bottom)

    If the flourish sweeps UP, its left extremity sits HIGH  -> small fraction.
    If the flourish hooks DOWN, its left extremity sits LOW  -> large fraction.

    ⇒ PREDICTION: known-N `Nafn` scores HIGHER than known-H `Herodes`.

⛔ **If it does not, that is the answer and it gets reported as the answer.**
Re-running with a different window, a different statistic or a different
threshold until the controls separate is not measuring — it is manufacturing.
The 2026-09-14 rule stands: repairing a segmentation bug is fixing an
instrument; redefining the feature until the control passes is tuning it.

## ⚠ TWO CONTROLS IS THIN

Even if this separates `Nafn` from `Herodes`, that is **one known letter of
each**. ⛔ It is not yet a screen and must not be pointed at
`research/_parts/`. A screen needs more known sites with known pixel boxes, and
locating those is itself unsolved (the locator agent is measured-unfit too).

Exit 0 = controls separated in the predicted direction; probes printed.
Exit 3 = they did not, or a crop/box could not be read. ⛔ Never a usable list.
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:                                           # noqa: BLE001
    sys.stderr.write("pillow not available\n")
    sys.exit(3)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thorlaks_hn_descender import (                           # noqa: E402
    PANELS, PREP, load_ink, first_glyph_cols,
)

#: Fraction of the glyph's width, from its LEFT edge, that holds the flourish's
#: terminal. ⚠ Declared before the first run; ⛔ do not sweep it.
LEFT_FRAC = 0.20


def measure(panel, cache):
    label, fname, x0, x1, kind = panel
    path = os.path.join(PREP, fname)
    if path not in cache:
        if not os.path.exists(path):
            return None
        cache[path] = load_ink(path)
    ink, w, h = cache[path]
    span = first_glyph_cols(ink, h, x0, min(x1, w))
    if span is None:
        return None
    gx0, gx1 = span

    # the glyph's own vertical extent, so the score is scale-free
    ys = [y for y in range(h) for x in range(gx0, gx1) if ink[y][x]]
    if not ys:
        return None
    gtop, gbot = min(ys), max(ys)
    gh = gbot - gtop
    if gh <= 0:
        return None

    lx1 = gx0 + max(1, int(round((gx1 - gx0) * LEFT_FRAC)))
    left_ys = [y for y in range(h) for x in range(gx0, lx1) if ink[y][x]]
    if not left_ys:
        return None
    centroid = sum(left_ys) / float(len(left_ys))
    return {
        "label": label, "kind": kind,
        "cols": (gx0, gx1), "left_cols": (gx0, lx1),
        "gtop": gtop, "gbot": gbot,
        "frac": (centroid - gtop) / gh,
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
    separated = n_ctl["frac"] > h_ctl["frac"]        # the PRE-REGISTERED call

    # ★★ THE HIDDEN CONTROL. `Hun` is 12:0 H across the merged corpus — it is
    # the accidental known-H word that disqualified the delegated adjudication
    # in thorlaks_hn_second_adjudication_2026-09-13.md. It is ground truth from
    # the corpus, not from this session, and it makes the test HARDER.
    # ⛔ Do not remove it to make a run pass.
    hun = by["Hun"]
    mid = (n_ctl["frac"] + h_ctl["frac"]) / 2.0
    hun_ok = hun["frac"] < mid                        # must land on the H side
    margin = abs(hun["frac"] - mid)
    spread = n_ctl["frac"] - h_ctl["frac"]

    if a.selftest:
        print("  control-N  Nafn     left-flourish height = %.3f (1.0 = bottom)"
              % n_ctl["frac"])
        print("  control-H  Herodes  left-flourish height = %.3f" % h_ctl["frac"])
        print("  predicted N > H ?   %s (want True)" % separated)
        print("  control-H  Hun (12:0 H in corpus) = %.3f  vs midpoint %.3f"
              % (hun["frac"], mid))
        print("  Hun lands on the H side ? %s (want True)  margin %.4f"
              % (hun_ok, margin))
        print("  known-letter spread = %.4f" % spread)
        if separated and hun_ok and margin > spread / 4.0:
            print("SELFTEST PASSED - separates the knowns AND holds on Hun.")
            return 0
        print("SELFTEST FAILED - REPORT IT, do not retune.")
        if separated and not hun_ok:
            print("  ⛔ It calls the known-H word `Hun` an N — the EXACT failure")
            print("     that disqualified the delegated adjudication.")
        elif separated and margin <= spread / 4.0:
            print("  ⛔ `Hun` sits %.4f from the midpoint against a %.4f spread:"
                  % (margin, spread))
            print("     a knife-edge, not a discriminator.")
        return 3

    print("%-9s %-10s %11s %11s   %s"
          % ("panel", "kind", "glyph cols", "left cols", "flourish height"))
    print("-" * 74)
    for r in rows:
        print("%-9s %-10s %11s %11s   %.3f"
              % (r["label"], r["kind"], "%d-%d" % r["cols"],
                 "%d-%d" % r["left_cols"], r["frac"]))
    print()
    # ⛔ The main path is gated on the SAME controls as --selftest. A run that
    # printed "CONTROLS SEPARATED" and exited 0 while the selftest exited 3
    # would be a trap: the probe lines read as verdicts.
    if not separated:
        sys.stderr.write("CONTROLS DID NOT SEPARATE AS PREDICTED: Nafn %.3f "
                         "vs Herodes %.3f. Probes above are NOISE.\n"
                         % (n_ctl["frac"], h_ctl["frac"]))
        return 3
    if not hun_ok:
        sys.stderr.write(
            "⛔ INSTRUMENT UNFIT: it calls the known-H word `Hun` (12:0 H in "
            "the merged corpus) an N — %.3f against a midpoint of %.3f. That "
            "is the EXACT failure that disqualified the delegated "
            "adjudication. Probes above are NOISE.\n" % (hun["frac"], mid))
        return 3
    if margin <= spread / 4.0:
        sys.stderr.write(
            "⛔ INSTRUMENT UNFIT: `Hun` sits %.4f from the midpoint against a "
            "known-letter spread of only %.4f — a knife-edge, not a "
            "discriminator. Probes above are NOISE.\n" % (margin, spread))
        return 3
    print("CONTROLS HELD: known-N %.3f > known-H %.3f (midpoint %.3f), and the"
          % (n_ctl["frac"], h_ctl["frac"], mid))
    print("hidden control `Hun` landed on the H side by %.4f." % margin)
    for r in rows:
        if r["kind"] != "probe":
            continue
        side = "N (flourish down)" if r["frac"] > mid else "H (flourish up)"
        print("  %-8s %.3f  -> %s" % (r["label"], r["frac"], side))
    print()
    print("⚠ THREE CONTROLS ONLY. NOT a screen, and ⛔ not to be pointed at")
    print("  research/_parts/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
