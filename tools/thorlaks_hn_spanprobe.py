"""Diagnose first_glyph_cols: is the capital's span STABLE in the gap threshold?

`thorlaks_hn_typematch.py` calls `Nuors` unresolved, and its first-glyph span
is ~65 px where the other panels get 40-48.  Two hypotheses:

  (a) the run-termination gap (default 3 blank columns) sits BELOW the
      intra-word letter gap on that panel, so the scan runs straight through
      into the next letter and the "template" is two letters wide;
  (b) the N really is that wide there.

The discriminator, borrowed from the line-cliff fix: **a correctly segmented
glyph's width is FLAT in the gap threshold** - raising the gap cannot add
columns once the letter has ended.  A swallowing segmentation instead shows a
STEP: small gap -> swallows, larger gap -> snaps back to the true letter.

⛔ This tool does not choose a gap. It prints the profile so the step (or its
absence) is visible. Redefining the parameter until a verdict changes is
manufacturing the answer; repairing a segmentation bug is not - and the
profile is what tells the two apart.

    python tools/thorlaks_hn_spanprobe.py
    python tools/thorlaks_hn_spanprobe.py --selftest

## --selftest, and its known-bad control

`--selftest` feeds SYNTHETIC ink matrices to `first_glyph_cols` through a thin
seam (`_glyph_span`), so it needs no panel crops and does not import Pillow. It
asserts the invariant the docstring states: a correctly segmented glyph's width
is FLAT across the whole sweep, and a swallowing segmentation shows a STEP.

⛔ A control that passes on broken code is not a control. `HEXAPLA_PIN_GAP=1`
pins the sweep to ONE gap value, collapsing the profile to a single point so a
STEP becomes invisible - exactly the blindness the profile exists to prevent.
Both directions must hold:

    python tools/thorlaks_hn_spanprobe.py --selftest                     # exit 0
    HEXAPLA_PIN_GAP=1 python tools/thorlaks_hn_spanprobe.py --selftest   # exit 1

⚠ The variable is honoured ONLY while the selftest drives a synthetic panel;
the tool still does NOT choose a gap.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

GAPS = range(1, 13)

#: Set by selftest() while it drives a synthetic panel; ⛔ never true otherwise.
_IN_SELFTEST = False
#: ⚠ The known-bad control's single fixed gap (docs: 3 blank columns).
_PINNED_GAP = 3
#: Callable used by `_glyph_span`; set to a dependency-free stand-in by the
#: selftest so no Pillow import is needed on the synthetic path.
_SPAN_FN = None


def pin_gap():
    """⚠ The known-bad control: collapse the sweep to one gap."""
    return _IN_SELFTEST and os.environ.get("HEXAPLA_PIN_GAP") == "1"


def _gaps():
    """The sweep the tool actually runs. ⛔ Not a chosen default - a control."""
    return (_PINNED_GAP,) if pin_gap() else GAPS


def _local_first_glyph_cols(ink, h, x0, x1, gap=3):
    """A dependency-free copy of `thorlaks_hn_descender.first_glyph_cols`.

    ⚠ Only the selftest's synthetic path uses this. It forwards the EXACT same
    algorithm (and the same MIN_GLYPH_W speck rule), so the span logic under
    test is the tool's own - it just does not drag in Pillow. The real run uses
    the real function via `_glyph_span`.
    """
    MIN_GLYPH_W = 18
    cols = [any(ink[y][x] for y in range(h)) for x in range(x0, x1)]
    i, n = 0, len(cols)
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
        i = end + 1
    return None


def _glyph_span(ink, h, x0, x1, gap):
    """The thin testable seam over `first_glyph_cols`.

    ⚠ Imported lazily so --selftest never needs Pillow, which
    `thorlaks_hn_descender` pulls in at import time. The synthetic path swaps
    in `_local_first_glyph_cols`; a real run forwards to the real function.
    """
    fn = _SPAN_FN
    if fn is None:
        from thorlaks_hn_descender import first_glyph_cols as fn  # noqa: PLC0415
    return fn(ink, h, x0, x1, gap=gap)


def profile(ink, w, h, x0, x1):
    """Sweep the gap for ONE panel -> [(gap, width or None), ...]."""
    out = []
    for g in _gaps():
        span = _glyph_span(ink, h, x0, min(x1, w), gap=g)
        out.append((g, None if span is None else span[1] - span[0]))
    return out


def classify(prof):
    """Judge one profile. -> dict with the ARTIFACT both the report and the
    selftest read.

    keys: gaps, widths, vals, distinct, span, flat, step
    ⛔ `flat` is the discriminator: one distinct width across the sweep. A
    profile with only a single point cannot be judged and is reported as such,
    never called flat.
    """
    gaps = [g for g, _v in prof]
    widths = [v for _g, v in prof]
    vals = [v for v in widths if v is not None]
    distinct = len(set(vals))
    span = (max(vals) - min(vals)) if vals else 0
    return {"gaps": gaps, "widths": widths, "vals": vals,
            "distinct": distinct, "span": span,
            "flat": distinct == 1 and len(vals) > 1,
            "step": distinct > 1}


def main():
    from thorlaks_hn_descender import PANELS, PREP, load_ink
    cache = {}
    print("first-glyph span width vs gap threshold")
    print("gap:      " + "".join("%5d" % g for g in GAPS))
    if pin_gap():
        print("⛔ PINNED to a single gap: the profile is one point; a STEP "
              "cannot show.")
    rows = []
    for label, fname, x0, x1, kind in PANELS:
        path = os.path.join(PREP, fname)
        if path not in cache:
            if not os.path.exists(path):
                print("MISSING %s - not a pass." % path)
                return 3
            cache[path] = load_ink(path)
        ink, w, h = cache[path]
        prof = profile(ink, w, h, x0, x1)
        by_gap = dict(prof)
        widths = [by_gap.get(g) for g in GAPS]
        rows.append((label, kind, widths))
        cells = "".join("    ?" if v is None else "%5d" % v for v in widths)
        print("%-9s %s   %s" % (label, cells, kind))

    print("\nflatness (distinct widths over the sweep; 1 = perfectly stable):")
    bad = []
    for label, kind, widths in rows:
        vals = [v for v in widths if v is not None]
        distinct = len(set(vals))
        span = (max(vals) - min(vals)) if vals else 0
        flag = ""
        if distinct > 1:
            flag = "  <-- STEP, span varies by %d px" % span
            bad.append(label)
        print("   %-9s %d distinct, %d..%d%s"
              % (label, distinct, min(vals), max(vals), flag))
    if bad:
        print("\nNOT FLAT: %s" % ", ".join(bad))
        print("A width that grows as the gap SHRINKS is the scan running into")
        print("the next letter. Read the step's location before changing any")
        print("default - the flat plateau is the letter's true width.")
    return 0


# ---------------------------------------------------------------- selftest ---

def _panel(blocks):
    """A one-row ink matrix from [(ink_width, gap_after), ...]."""
    cells, pattern = [], ""
    for i, (width, gap) in enumerate(blocks):
        pattern += "#" * width
        if i < len(blocks) - 1:
            pattern += "." * gap
    pattern = pattern.rstrip(".")
    cells.append([c == "#" for c in pattern])
    return cells, len(pattern), 1


def _flat_panel():
    """One 40-wide glyph, a WIDE 30-blank gap, then the next letter.

    ⚠ In this implementation the scan terminates when `blanks >= gap`, so a
    larger gap terminates LATER. A glyph followed by a gap wider than every
    gap in the sweep therefore measures FLAT: nothing in the sweep can reach
    past it into the next letter.
    """
    return _panel([(40, 30), (30, 0)])


def _step_panel():
    """40-wide glyph, a NARROW 2-blank gap, a 25-wide letter, then a wide gap.

    Below the 2-blank gap the scan stops at the true letter (40); at gap >= 3
    it runs straight through and swallows the neighbour (67). The step sits at
    exactly gap 3 - the tool's own documented default.
    """
    return _panel([(40, 2), (25, 30), (10, 0)])


def selftest():
    global _IN_SELFTEST, _SPAN_FN
    _IN_SELFTEST = True          # arm the known-bad control for this process
    _SPAN_FN = _local_first_glyph_cols   # no Pillow on the synthetic path
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    # -- 1. a FLAT case ---------------------------------------------------
    ink, w, h = _flat_panel()
    fprof = profile(ink, w, h, 0, w)
    f = classify(fprof)
    check(all(v == 40 for _g, v in fprof),
          "flat: the span is 40 at EVERY gap in the sweep")
    check(f["distinct"] == 1 and f["span"] == 0,
          "flat: the whole profile is constant, not just its endpoints")
    check(f["flat"] is True and f["step"] is False,
          "flat: reported as flat and NOT as a step (false-positive control)")

    # -- 2. a STEP case ---------------------------------------------------
    ink, w, h = _step_panel()
    sprof = profile(ink, w, h, 0, w)
    s = classify(sprof)
    by_gap = dict(sprof)
    check(by_gap.get(3) == 67,
          "step: at gap 3 the span swallows both letters (67)")
    check(by_gap.get(2) == 40,
          "step: below the intra-word gap it snaps back to 40")
    check(s["step"] is True and s["span"] == 27,
          "step: the profile is a step, varying by 27 px")
    check([g for g, v in sprof if v == 67][:1] == [3],
          "step: the snap-back happens at gap 3, the expected threshold")

    # -- 3. step vs flat are distinguished -------------------------------
    check(s["flat"] is False and f["flat"] is True,
          "the step case is NOT flat and the flat case is NOT a step")

    # -- 4. a glyph running to the right edge ----------------------------
    ink, w, h = _panel([(40, 0)])
    e = classify(profile(ink, w, h, 0, w))
    check(e["vals"] and all(v == 40 for v in e["vals"]),
          "right edge: a glyph with no terminating gap is handled, span 40")
    check(e["step"] is False, "right edge: no spurious step is reported")

    # -- 5. an all-blank panel -------------------------------------------
    ink = [[False] * 30]
    w, h = 30, 1
    b = classify(profile(ink, w, h, 0, w))
    check(b["vals"] == [] and b["flat"] is False and b["step"] is False,
          "all-blank: no span of 0 is reported as a real measurement")

    # -- the known-bad control, asserted against the ARTIFACT ------------
    if pin_gap():
        pink, pw, ph = _step_panel()
        check(len(profile(pink, pw, ph, 0, pw)) > 1,
              "HEXAPLA_PIN_GAP=1 is active: the sweep is collapsed to one "
              "point, so the STEP is invisible (this run is SUPPOSED to fail)")
    else:
        check(len(f["vals"]) == len(list(GAPS)),
              "the sweep visits every gap when the control is off")

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
    sys.exit(main())
