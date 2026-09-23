# -*- coding: utf-8 -*-
"""PROTOTYPE, OFF TO THE SIDE: the merged-line pages are SKEWED, and a shear fixes them.

    python tools/prep_deskew_proto.py --vol 3 --pages 55-71
    python tools/prep_deskew_proto.py --selftest

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

⛔ **THIS WRITES NOTHING AND CHANGES NO CROP.** `prep_chunk.py` is untouched by
it; the ~270 already-merged pages are not re-addressed and nothing is re-cut.
It exists to measure whether the discriminator is real before anyone proposes
putting it behind a flag in the live tool. The owner's standing ruling
(2026-09-14): prototype it off to the side, opt-in, never the default.

## ⚠ IT IS NOT THE MECHANISM THE OWNER GUESSED, AND THE MEASUREMENT SAYS SO

The brief was «horizontal CLUSTERING — a short line's ink is contiguous near the
left margin, descender ink is scattered across the full width». That is the right
mechanism for `short_line_rects()`' problem (a one-word line), and it is already
implemented there. It is **not** what ails Luke p66. Measured here:

    idx  block    rects  pitch  drift   per-strip steps
     64  240.0pt     52     14     +1   [0, 0, 0, 0, 0, 0, 1]     healthy
     65  239.5pt     52     14     -1   [-1, 0, 0, 0, 0, 0, 0]    healthy
     66  280.0pt     44     14     +8   [0, 1, 2, 2, 1, 0, 2]   <- CLIFF PAGE
     61  240.0pt     55     14     -8   [-2,-1,-1,-1,-1,-1,-1]  <- re-prepped
     62  238.5pt     52     14     +7   [1, 1, 1, 0, 1, 2, 1]   <- re-prepped

★★ **The line pitch is 14 rows on every page in the kit, and the three cliff
pages drift 7-8 rows across the block — HALF A LINE.** The scan is rotated by
about one degree, so a row that is inter-line space on the left of the block is
solid text on the right. Averaging the row to one pixel (`band.resize((1, h))`)
then smears every gap, and no threshold can separate what the average has
already mixed. ▶ That is why `--robust-block`, the block-narrowing sweep and
every re-threshold left p66 on the cliff: they all keep the skew.

▶ Split the same merged rect in half and the two halves are clean AND OUT OF
PHASE — the direct observation, from the same band and the same ink cut:

    line38 LEFT   0.00 0.05 0.11 0.26 0.41 ... 0.07 0.06 0.06 0.14 ...
    line38 RIGHT  0.40 0.31 0.10 0.00 0.00 ... 0.25 0.20 0.34 0.21 ...

## The gate, and why TOTAL DRIFT ALONE IS NOT IT

idx 57 drifts -4 and idx 71 drifts -6, and both are healthy (54 and 51 rects).
Their drift is **all in the first step or two** — `[-3,-1,0,0,0,0,0]`,
`[-4,-1,-1,0,0,0,0]` — a drop cap or marginal ink in the leftmost strip, not a
rotation. A rotation shows as a drift that is *distributed*: every step carries
part of it and they all share a sign. So the gate is

    median(|step|) >= 1  AND  every non-zero step has the same sign

which separates {61, 62, 66} from all fourteen other pages in idx 55-71, with no
constant fitted to p66. ⚠ It is still a SORTING AID over one kit; ⛔ it has not
been run over the whole corpus and it rules on nothing.

## The correction is a SHEAR, not a rotation

The drift is measured in rows per pixel of x, so it is undone exactly by
shifting column x up by `round(slope * x)` — integer pixel moves, no resampling,
no interpolation, and no ambiguity about which way a rotation turns. A page the
gate does not fire on is never sheared at all: it takes the identical code path
it takes today, so ⛔ **a healthy page cannot move**, and that is a property of
the control flow, not of a tolerance.

## The control, and it must fire BOTH ways

- ▶ idx 66 MUST be gated as skewed, and the shear MUST raise its run count
  materially above **44**.
- ▶ idx 64 and 65 MUST NOT be gated, and their counts MUST stay **52 / 52** —
  byte-identical, because the code never touches them.
- ▶ `HEXAPLA_NO_DESKEW=1` forces the gate open on every page: healthy counts
  then move, and the selftest MUST fail. A run that passes both ways is inert.

Exit 0 = every control fired. Exit 1 = a control failed. Exit 3 = could not run.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fitz                      # noqa: E402
from PIL import Image            # noqa: E402

import prep_chunk as pc          # noqa: E402  the pipeline itself

# ★ MOVED 2026-09-16. The gate and the shear now live in `prep_chunk.py`, which
# is where `--deskew` uses them, so there is exactly ONE implementation. This
# file keeps its selftest, and that selftest is now also the control that the
# move was FAITHFUL: idx 66 must still gate and gain runs, idx 64/65 must still
# be byte-identical at 52/52, and `HEXAPLA_NO_DESKEW=1` must still break it.
# ⛔ Do not re-inline copies here to "decouple" the two — a second copy would
# agree with itself while the shipped one drifted.
STRIPS = pc.SKEW_STRIPS
STEP_MAXLAG = pc.SKEW_STEP_MAXLAG
SKEW_MIN_MEDIAN_STEP = pc.SKEW_MIN_MEDIAN_STEP


def band_for(page, block):
    """The profile band. ⚠ Copied VERBATIM from line_rects()' first four lines,
    so this measures what the pipeline measures and not something beside it."""
    im = pc._gray(page, pc.PROFILE_ZOOM)
    x0 = int((block.x0 - page.rect.x0) * pc.PROFILE_ZOOM)
    x1 = int((block.x1 - page.rect.x0) * pc.PROFILE_ZOOM)
    return im.crop((max(x0, 0), 0, min(x1, im.width), im.height))


def runs_of(band):
    """Run count for a band. ⚠ The body of line_rects() after the crop, verbatim:
    same resize-to-one-column mean, same choose_frac, same _runs(min_len=6)."""
    col = band.resize((1, band.height))
    rows = [col.getpixel((0, y)) / 255.0 for y in range(band.height)]
    frac, note = pc.choose_frac(rows)
    return len(pc._runs(rows, frac, min_len=6)), frac, note


def plateau_ratio(band):
    """-> (ratio, peak) by choose_frac()'s OWN health test, or (-1.0, 0).

    ⚠⚠ THE RUN COUNT AT THE THRESHOLD A BAND HAPPENS TO PICK IS NOT COMPARABLE
    ACROSS TWO BANDS — they pick different thresholds, and the sheared band
    routinely picks a different one from the original (measured 2026-09-16:
    v2:86 0.400 -> 0.650, v2:146 0.450 -> 0.650, v3:255 0.750 -> 0.650). The
    plateau ratio IS comparable, and it is the pipeline's own criterion:
    `counts[LINE_FRAC] >= FRAC_KEEP * peak` over FRAC_SWEEP, straight out of
    choose_frac(). ⛔ A failure returns -1.0, never a plausible number.
    """
    col = band.resize((1, band.height))
    rows = [col.getpixel((0, y)) / 255.0 for y in range(band.height)]
    counts = {f: len(pc._runs(rows, f, min_len=6)) for f in pc.FRAC_SWEEP}
    peak = max(counts.values())
    if not peak:
        return -1.0, 0
    return counts.get(pc.LINE_FRAC, 0) / float(peak), peak


# ---- DELEGATIONS. ⛔ No logic lives here any more; see the note by STRIPS. ----
ink_cut = pc._skew_ink_cut
strip_profile = pc._skew_strip_profile
best_lag = pc._skew_best_lag
skew_steps = pc.skew_steps
gated = pc.skew_gated


def shear(band, drift, span):
    """Shift column x up by round(drift * x / span). Integer moves, no resampling.

    ⚠ The prototype's band-relative signature, kept so the selftest below still
    reads as it did. `pc.shear_image` takes the DIMENSIONLESS slope instead,
    because it also has to shear a full page raster at a different zoom.
    """
    return pc.shear_image(band, drift / float(span), x_origin=0)


def measure(page):
    """-> dict for one page. Never raises past a measurement failure."""
    block, note = pc.text_block(page)
    band = band_for(page, block)
    before, frac_b, _ = runs_of(band)
    ratio_b, peak_b = plateau_ratio(band)
    row = {"block": block.width, "note": note, "before": before,
           "frac": frac_b, "steps": None, "drift": None, "span": None,
           "gated": False, "after": before, "deg": 0.0,
           "ratio_b": ratio_b, "peak_b": peak_b,
           "ratio_a": ratio_b, "peak_a": peak_b}
    steps, drift, span = skew_steps(band)
    row.update(steps=steps, drift=drift, span=span)
    if steps is None:
        row["after"] = -1                 # a failed measurement is not a pass
        row["ratio_a"] = -1.0
        return row
    row["deg"] = math.degrees(math.atan2(drift, span))
    if gated(steps):
        row["gated"] = True
        shb = shear(band, drift, span)
        after, _, _ = runs_of(shb)
        row["after"] = after
        row["ratio_a"], row["peak_a"] = plateau_ratio(shb)
    return row


def run(vol, idxs):
    doc = fitz.open(pc.RESEARCH / ("thorlaks_v%d.pdf" % vol))
    out = {}
    for idx in idxs:
        out[idx] = measure(doc[idx])
    doc.close()
    return out


def report(rows):
    print("%4s %8s %7s %7s %6s %6s %7s %7s  %s"
          % ("idx", "block", "before", "after", "plat_b", "plat_a",
             "drift", "deg", "steps"))
    for idx in sorted(rows):
        r = rows[idx]
        mark = "  <- SHEARED" if r["gated"] else ""
        print("%4d %7.1fpt %7d %7d %6.2f %6.2f %+7s %+7.2f  %s%s"
              % (idx, r["block"], r["before"], r["after"],
                 r["ratio_b"], r["ratio_a"],
                 r["drift"] if r["drift"] is not None else "?",
                 r["deg"], r["steps"], mark))
    # ⚠⚠ A FAILED MEASUREMENT MUST NOT BE COUNTED AS A MOVED PAGE. The first
    # corpus pass printed "31 ungated pages moved (must be 0)" and every one of
    # the 31 was a page this tool could not measure at all (after = -1). The
    # two are different findings and a reader cannot act on them together.
    failed = [i for i, r in rows.items() if r["steps"] is None]
    moved = [i for i, r in rows.items()
             if r["steps"] is not None and not r["gated"]
             and r["after"] != r["before"]]
    gated = [i for i, r in rows.items() if r["gated"]]
    lost = [i for i in gated if rows[i]["after"] < rows[i]["before"]]
    # ⚠⚠ A COUNT DROP IS NOT A LOST LINE. Measured over all twelve dropping
    # pages (2026-09-16): 6 went from OFF the cliff to ON the plateau, 5 were
    # already on it both ways, 1 stayed off, and NONE regressed — the peak run
    # count over FRAC_SWEEP moved by at most 4 on any of them. The drop was the
    # count being read at two DIFFERENT thresholds, because the sheared band
    # re-picks frac. ▶ The alarm worth raising is a page that leaves the
    # plateau; a page that joins it has been repaired, whatever the count did.
    regressed = [i for i in gated
                 if rows[i]["ratio_b"] >= pc.FRAC_KEEP > rows[i]["ratio_a"] >= 0]
    repaired = [i for i in gated
                if rows[i]["ratio_b"] < pc.FRAC_KEEP <= rows[i]["ratio_a"]]
    stilloff = [i for i in gated
                if rows[i]["ratio_b"] < pc.FRAC_KEEP and 0 <= rows[i]["ratio_a"] < pc.FRAC_KEEP]
    print()
    print("%d page(s) measured, %d COULD NOT BE MEASURED (block detection "
          "collapsed or the lag pinned at the search ceiling)."
          % (len(rows) - len(failed), len(failed)))
    if failed:
        print("   unmeasured: %s" % ",".join(str(i) for i in sorted(failed)))
    print("%d page(s) gated as skewed; %d ungated page(s) moved (must be 0)."
          % (len(gated), len(moved)))
    if repaired:
        print("✅ %d gated page(s) moved OFF THE CLIFF ON TO THE PLATEAU: %s"
              % (len(repaired), ",".join(str(i) for i in sorted(repaired))))
    if stilloff:
        print("⚠ %d gated page(s) are STILL OFF THE CLIFF after the shear — "
              "the shear is not the whole story there: %s"
              % (len(stilloff), ",".join(str(i) for i in sorted(stilloff))))
    if regressed:
        print("⛔ %d gated page(s) LEFT THE PLATEAU after the shear — a real "
              "finding, not a tuning target: %s"
              % (len(regressed), ",".join(str(i) for i in sorted(regressed))))
    if lost:
        print("   (%d gated page(s) read a lower COUNT after the shear: %s — "
              "⛔ not by itself a lost line, see plat_b/plat_a above)"
              % (len(lost), ",".join(str(i) for i in sorted(lost))))
    print("⛔ NOTHING WAS WRITTEN. This is a measurement, not a re-prep.")
    print("⛔ A HIGHER RUN COUNT IS NOT A CORRECT READ. It says the lines were "
          "separated, nothing about what they say.")


def selftest():
    rows = run(3, [61, 62, 64, 65, 66, 67])
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %-42s %-14s (want %s) %s"
              % (label, got, want, "OK" if good else "FAIL"))

    check("idx 66 gated as skewed", rows[66]["gated"], True)
    check("idx 64 NOT gated (healthy)", rows[64]["gated"], False)
    check("idx 65 NOT gated (healthy)", rows[65]["gated"], False)
    check("idx 64 count unchanged", rows[64]["after"], rows[64]["before"])
    check("idx 65 count unchanged", rows[65]["after"], rows[65]["before"])
    print("  %-42s %s -> %s"
          % ("idx 66 runs before -> after", rows[66]["before"], rows[66]["after"]))
    # ⚠ The bar is set by the PAGE, not by what this run happened to produce.
    # p66's three over-tall rects measure 2.17x, 3.86x and 2.04x the page's own
    # median rect height, so they hold about 2, 4 and 2 text lines — five lines
    # more than the three crops they are cut as. A shear that recovers fewer
    # than five has not resolved what the height screen already named.
    gain = rows[66]["after"] - rows[66]["before"]
    good = rows[66]["before"] == 44 and gain >= 5
    ok = ok and good
    print("  %-42s %+d (want >= +5, the lines its own crop heights imply) %s"
          % ("idx 66 material gain", gain, "OK" if good else "FAIL"))
    if os.environ.get("HEXAPLA_NO_DESKEW"):
        print("  (HEXAPLA_NO_DESKEW=1: the gate is forced open — healthy pages "
              "are sheared and the checks above MUST fail)")
    if ok:
        print("SELFTEST PASSED — the gate fires on the cliff page, leaves every "
              "healthy page on its existing code path, and the shear recovers "
              "the merged lines.")
        return 0
    print("SELFTEST FAILED.")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vol", type=int, default=3, choices=(1, 2, 3))
    ap.add_argument("--pages", help="PDF index, e.g. 66 or 55-71")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.pages:
        sys.stderr.write("--pages or --selftest required.\n")
        return 3
    lo, _, hi = a.pages.partition("-")
    idxs = list(range(int(lo), int(hi or lo) + 1))
    report(run(a.vol, idxs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
