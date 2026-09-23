"""Can word boxes be found at all? Measure the gap-width distribution of a line.

The H/N screen needs each site's WORD box found automatically. That reduces to
one question, and it is cheap to answer:

    on a real line crop, are BETWEEN-WORD gaps separable from BETWEEN-LETTER
    gaps - i.e. is the distribution of blank-column run lengths BIMODAL?

If it is bimodal there is a threshold between the modes and word segmentation
is possible. ⛔ If it is unimodal, no threshold exists, word boxes cannot be
cut this way, and the screen cannot be built on column gaps - which is an
ANSWER, not a failure.

⚠ This reports the distribution. It does NOT pick a threshold, and it does not
decide the question on a summary statistic - print the runs and look.

    python tools/thorlaks_hn_gapmodes.py                 # default line crops
    python tools/thorlaks_hn_gapmodes.py line25.png ...
    python tools/thorlaks_hn_gapmodes.py --selftest

## --selftest, and its known-bad control

`--selftest` feeds SYNTHETIC ink matrices straight to `gap_modes()` — no image
files, no Pillow. It asserts the invariant the docstring states: a unimodal line
is reported as unimodal, and no threshold is invented for it.

⛔ A control that passes on broken code is not a control. `HEXAPLA_FORCE_BIMODAL=1`
makes the classifier always report a separable threshold — exactly the
"unimodal squeezed into a threshold" defect this docstring forbids. Both
directions must hold:

    python tools/thorlaks_hn_gapmodes.py --selftest                          # exit 0
    HEXAPLA_FORCE_BIMODAL=1 python tools/thorlaks_hn_gapmodes.py --selftest  # exit 1

⚠ The variable is honoured ONLY while the selftest drives a synthetic line;
the printed output of a normal run is unaffected.
"""
import io
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DEFAULT = ["line25.png", "line40.png", "line41.png"]

#: Set by selftest() while it drives a synthetic line; ⛔ never true in a normal run.
_IN_SELFTEST = False


def force_bimodal():
    """⚠ The known-bad control: always claim a separable threshold exists."""
    return _IN_SELFTEST and os.environ.get("HEXAPLA_FORCE_BIMODAL") == "1"


def gap_runs(ink, w, h):
    """Blank-column run lengths across the whole line, ignoring the margins."""
    cols = [any(ink[y][x] for y in range(h)) for x in range(w)]
    try:
        first, last = cols.index(True), len(cols) - 1 - cols[::-1].index(True)
    except ValueError:
        return None
    runs, n = [], 0
    for x in range(first, last + 1):
        if cols[x]:
            if n:
                runs.append(n)
            n = 0
        else:
            n += 1
    return runs


def gap_modes(runs):
    """Classify a blank-run list. -> a dict; the ARTIFACT both the report and
    the selftest read, so the control flips the LOGIC rather than the result.

    keys: runs, hist, lo, hi, band (widest EMPTY band, or None), separable,
          counts ((threshold, word_count) over 2..15), flat (bool), flat_n.
    ⛔ `separable` and `flat` are the honest pair: a continuous distribution is
    NOT separable, and a word count that drifts is NOT flat. `force_bimodal()`
    lies about exactly those two.
    """
    hist = {}
    for r in runs:
        hist[r] = hist.get(r, 0) + 1
    lo, hi = min(hist), max(hist)
    empty = [g for g in range(lo, hi + 1) if g not in hist]
    band = None
    if empty:
        bands, cur = [], [empty[0]]
        for g in empty[1:]:
            if g == cur[-1] + 1:
                cur.append(g)
            else:
                bands.append(cur)
                cur = [g]
        bands.append(cur)
        band = max(bands, key=len)
    counts = [(t, 1 + sum(1 for r in runs if r >= t)) for t in range(2, 16)]
    in_band = [n for t, n in counts if 7 <= t <= 12]
    flat = len(set(in_band)) == 1

    separable = band is not None and flat
    if force_bimodal():
        # ⚠ The known-bad path: invent a threshold and call a drifting count
        # "flat", so a UNIMODAL line is reported as separable.
        separable = True
        flat = True
        if band is None:
            band = [7, 8]
    return {"runs": runs, "hist": hist, "lo": lo, "hi": hi, "band": band,
            "separable": separable, "counts": counts, "flat": flat,
            "flat_n": in_band[0] if in_band else None}


def report(name, w, m):
    """Print the histogram and the verdict for one line from `gap_modes()`."""
    runs, hist = m["runs"], m["hist"]
    print("\n=== %s  (%d gaps, width %d)" % (name, len(runs), w))
    for k in sorted(hist):
        print("   gap %3d px : %-4d %s" % (k, hist[k], "#" * min(hist[k], 60)))
    if m["band"] is not None:
        print("   widest EMPTY band: %d..%d px (%d wide)"
              % (m["band"][0], m["band"][-1], len(m["band"])))
        if m["separable"]:
            print("   -> a valley exists here; word/letter gaps may separate")
    else:
        print("   NO empty band between %d and %d px." % (m["lo"], m["hi"]))
        if not m["separable"]:
            print("   -> the distribution is CONTINUOUS: every threshold cuts")
            print("      through real data. ⛔ No word/letter separation.")

    print("   word count vs threshold (a real valley is FLAT here):")
    print("      " + "  ".join("%d:%d" % (t, n) for t, n in m["counts"]))
    in_band = [n for t, n in m["counts"] if 7 <= t <= 12]
    if m["flat"]:
        print("      FLAT at %d words across thresholds 7-12." % in_band[0])
        print("      ⇒ word boxes ARE cuttable on this line.")
    else:
        print("      NOT flat across 7-12: %s" % in_band)
        print("      ⇒ ⛔ the threshold cuts through real data; this line")
        print("         must be SKIPPED, never guessed.")


def main(argv):
    from thorlaks_hn_descender import PREP, load_ink
    names = argv[1:] or DEFAULT
    for name in names:
        path = os.path.join(PREP, name)
        if not os.path.exists(path):
            print("MISSING %s - not a pass." % path)
            return 3
        ink, w, h = load_ink(path)
        runs = gap_runs(ink, w, h)
        if not runs:
            print("%s: no ink" % name)
            continue
        report(name, w, gap_modes(runs))
    return 0


# ---------------------------------------------------------------- selftest ---

def _line(pattern):
    """A one-row ink matrix. `pattern` is a string: '#' ink, '.' blank."""
    return [[c == "#" for c in pattern]], len(pattern), 1


def _bimodal():
    """2 letters, 2-wide letter gaps, 14-wide word gaps: three words.

    ⚠ The word gap is 14, not 9, because the tool's flat test is hard-wired to
    thresholds 7..12: an empty band must CONTAIN that whole window or the count
    drifts through the second mode. That coupling is the tool's real behaviour
    and this fixture is built to sit inside it, not around it.
    """
    return _line("#" * 4 + "." * 2 + "#" * 4 + "." * 14 + "#" * 4 +
                 "." * 2 + "#" * 4 + "." * 14 + "#" * 4)


def _unimodal():
    """Every gap exactly 3 wide - one mode, no valley, nothing to separate."""
    return _line("#" * 4 + "." * 3 + "#" * 4 + "." * 3 + "#" * 4 +
                 "." * 3 + "#" * 4)


def selftest():
    global _IN_SELFTEST
    _IN_SELFTEST = True          # arm the known-bad control for this process
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    try:
        # -- 1. margins are ignored ---------------------------------------
        core = "#" * 4 + "." * 3 + "#" * 4
        padded = "." * 20 + core + "." * 20
        check(gap_runs(*_line(padded)) == gap_runs(*_line(core)) == [3],
              "margins: 20 blank columns either side do not appear as gaps")

        # -- 2. a clearly BIMODAL line, asserted by VALUE ------------------
        m = gap_modes(gap_runs(*_bimodal()))
        want = sorted([2, 14, 2, 14])
        check(sorted(m["runs"]) == want,
              "bimodal: the run multiset is exactly %s" % want)
        check(m["runs"].count(2) == 2 and m["runs"].count(14) == 2,
              "bimodal: the 2s and the 14s have the right counts")
        check(m["separable"] is True and m["flat"] is True,
              "bimodal: the tool reports a separable, flat threshold")

        # -- 3. a clearly UNIMODAL line -----------------------------------
        u = gap_modes(gap_runs(*_unimodal()))
        check(u["runs"] == [3, 3, 3], "unimodal: every gap is 3 wide")
        check(u["separable"] is False,
              "unimodal: reported as NOT separable - no split is invented")
        check(u["flat"] is False or u["band"] is None,
              "unimodal: the word count is not claimed flat")

        # -- 4. an all-blank line -> None ---------------------------------
        check(gap_runs(*_line("." * 30)) is None,
              "all-blank: returns None (the ValueError path), not a crash")

        # -- 5. a solid block -> [] ---------------------------------------
        solid = gap_runs(*_line("#" * 30))
        check(solid == [] and solid is not None,
              "solid block: an EMPTY run list, not None")

        # -- 6. a gap touching the last ink column ------------------------
        check(gap_runs(*_line("#" * 4 + "." * 5 + "#" * 4)) == [5],
              "trailing: a gap before the final block is counted once")
        check(gap_runs(*_line("#" * 4 + "." * 5)) == [],
              "trailing: trailing blank columns are a MARGIN, not a gap")

        # -- the known-bad control, asserted against the ARTIFACT ---------
        u2 = gap_modes(gap_runs(*_unimodal()))
        if force_bimodal():
            check(u2["separable"] is False,
                  "HEXAPLA_FORCE_BIMODAL=1 is active: a unimodal line is "
                  "reported as separable (this run is SUPPOSED to fail overall)")
        else:
            check(u2["separable"] is False,
                  "the unimodal verdict is honest when the control is off")
    finally:
        pass

    bad = [w for ok, w in results if not ok]
    print()
    print("%d assertion(s), %d failed" % (len(results), len(bad)))
    if bad:
        print("⛔ SELFTEST FAILED")
        return 1
    print("✅ selftest passed")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main(sys.argv))
