#!/usr/bin/env python
"""Ask whether a disputed capital is THE SAME PIECE OF METAL as a known one.

    python tools/thorlaks_hn_typematch.py            # the p37 panel set
    python tools/thorlaks_hn_typematch.py --selftest

Run from the DATA dir (`C:\\Projects\\Hexapla-releases`).

## ★★ WHY THIS IS A DIFFERENT QUESTION FROM THE THREE THAT FAILED

The 1644 Þorláksbiblía is HAND-SET METAL TYPE. Every impression of a capital
`N` on the page came from the same sort, or from a handful of identical sorts
cast in the same mould. So the question does not have to be

    «does this glyph LOOK like an N?»          <- perception; measured unfit

it can instead be

    «is this the SAME SORT as a capital we already know the letter of?»

★ That is TEMPLATE IDENTITY — normalised cross-correlation — and it is
arithmetic. It is the one witness the campaign actually has: ⛔ no transcription
of the 1644 edition exists to compare against (searched 2026-09-14), and a
modern Icelandic Bible is only a LEXICAL witness, which is the closed dictionary
argument wearing a coat — it says what SHOULD be printed, never what IS.
⚠ The project's standing rule is that a printed reading which disagrees with the
expected text is a FINDING, NEVER A CORRECTION.

## The three instruments this replaces, and how each died

| instrument | feature | verdict on known-`H` `Hun` |
|---|---|---|
| delegated adjudication 2026-09-13 | right stem | **N**, moderate-high confidence |
| `thorlaks_hn_descender.py` | ink below baseline | controls INVERTED |
| `thorlaks_hn_flourish.py` | top-left flourish height | **N**, by 0.0011 |

★★ Two of the three had the WRONG PART OF THE GLYPH. The owner's annotation
(`_work/hn_p37_owner_annotated_2026-09-14.jpg`) located the feature on the
TOP-LEFT FLOURISH — but this tool does not need a feature at all, which is
exactly the point.

## The controls — and `Hun` is the one with teeth

- `Nafn`    is the known-`N` template (29:0 `N` across the merged corpus).
- `Herodes` is the known-`H` template (confident `H`, same printed line).
- ★★ `Hun` is **12:0 `H`** in the corpus and the owner ruled it `H` on the
  sheet. It is the accidental control that disqualified the delegated
  adjudication and then `thorlaks_hn_flourish.py`. ⛔ **If this tool does not
  match `Hun` to the `H` template, it is unfit and says so.**
- ⛔ Do not remove a control to make a run pass. ⛔ Do not sweep the resize
  geometry until the answer changes.

⚠ TWO TEMPLATES ON ONE PAGE is a feasibility probe, not a screen. Same-forme
impressions are the easiest possible case. ⛔ Do not point this at
`research/_parts/` on the strength of five panels.

Exit 0 = every control matched its own letter; probe matches printed.
Exit 3 = a control failed, or a crop/box could not be read.
"""
import argparse
import os
import sys
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)

try:
    from PIL import Image
except ImportError:                                           # noqa: BLE001
    sys.stderr.write("pillow not available\n")
    sys.exit(3)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thorlaks_hn_descender import (                           # noqa: E402
    PANELS, PREP, load_ink, first_glyph_cols,
)

#: Templates are normalised to this box before correlating. ⚠ Declared once;
#: ⛔ do not sweep it to move a verdict.
TW, TH = 32, 44

#: A site must hold the SAME first-glyph width over at least this many
#: consecutive gap values, starting at gap=1, before its segmentation is used.
#:
#: ⚠ HOW THE SEGMENTATION BUG WAS FOUND. The shared default in
#: thorlaks_hn_descender is gap=3, and at 3 the scan on `Nuors` runs straight
#: through into the following letter: a 65 px "capital" against 40-48 for every
#: other panel, which is exactly why typematch used to call it unresolved - it
#: was correlating two letters against one.
#: ⛔ Deliberately NOT changed in thorlaks_hn_descender: its rc=3 and the
#:   flourish tool's are RECORDED NEGATIVES, and silently re-segmenting them
#:   would rewrite a result the record depends on.
MIN_PLATEAU = 2


def stable_glyph_cols(ink, h, x0, x1, probe=None):
    """first_glyph_cols, but the site picks its own gap - or is SKIPPED.

    ★★ WHY A FIXED GAP CANNOT BECOME A SCREEN. `thorlaks_hn_spanprobe.py`
    shows every panel is flat at gap 1-2 and then steps, but EACH STEPS AT A
    DIFFERENT GAP: Nuors at 3, Hun and Hofud at 4, Nafn and Herodes at 5. A
    single constant sits inside all five plateaus on THIS page by luck - the
    letters happen to be spaced alike in one forme. On a page inked heavier or
    set tighter the common plateau can vanish, and a fixed gap would then
    swallow a neighbour SILENTLY and hand back a two-letter "capital" that
    still correlates with something.

    ⇒ So the width is trusted only where it is FLAT: identical across gaps
      1..MIN_PLATEAU. This is the same shape as prep_chunk.choose_frac() -
      a healthy site is flat in the threshold, a broken one falls off a cliff,
      and the site picks its own side of it.

    ⛔ Returns None where no plateau exists. A site with no plateau is SKIPPED
      and stays `[HN]` - ⛔ NEVER guessed at the nearest gap. An unreadable
      site must not be indistinguishable from a resolved one.
    """
    widths = []
    spans = []
    for g in range(1, MIN_PLATEAU + 1):
        span = first_glyph_cols(ink, h, x0, x1, gap=g)
        if span is None:
            return None
        spans.append(span)
        widths.append(span[1] - span[0])
    if probe is not None:
        probe.append((widths, spans[0]))
    if len(set(widths)) != 1:
        return None                     # no plateau - skip, do not guess
    return spans[0]


def glyph_bitmap(ink, h, gx0, gx1):
    ys = [y for y in range(h) for x in range(gx0, gx1) if ink[y][x]]
    if not ys:
        return None
    gtop, gbot = min(ys), max(ys)
    img = Image.new("L", (gx1 - gx0, gbot - gtop + 1), 0)
    px = img.load()
    for y in range(gtop, gbot + 1):
        for x in range(gx0, gx1):
            if ink[y][x]:
                px[x - gx0, y - gtop] = 255
    return img


def normalised(img, w=TW, h=TH):
    small = img.resize((w, h), Image.BILINEAR)
    v = [p / 255.0 for p in small.getdata()]
    n = len(v)
    mean = sum(v) / n
    dev = [a - mean for a in v]
    norm = sum(a * a for a in dev) ** 0.5
    if norm == 0:
        return None
    return [a / norm for a in dev]


def ncc(a, b):
    return sum(x * y for x, y in zip(a, b))


def panels(cache):
    out = {}
    for label, fname, x0, x1, kind in PANELS:
        path = os.path.join(PREP, fname)
        if path not in cache:
            if not os.path.exists(path):
                return None
            cache[path] = load_ink(path)
        ink, w, h = cache[path]
        span = stable_glyph_cols(ink, h, x0, min(x1, w))
        if span is None:
            return None
        bmp = glyph_bitmap(ink, h, span[0], span[1])
        if bmp is None:
            return None
        vec = normalised(bmp)
        if vec is None:
            return None
        out[label] = {"kind": kind, "vec": vec, "w": span[1] - span[0]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    cache = {}
    p = panels(cache)
    if p is None:
        sys.stderr.write("COULD NOT BUILD THE PANEL SET - not a pass.\n")
        return 3

    tN, tH = p["Nafn"]["vec"], p["Herodes"]["vec"]

    # ★★ THE MATCH FLOOR, derived from the data and not chosen:
    # the two KNOWN-DIFFERENT letters correlate at ncc(N-template, H-template).
    # A claimed identity must BEAT the score two different letters already get,
    # or it is not a match — it is the nearest of two bad fits.
    # ⇒ Below the floor the site is UNRESOLVED and stays `[HN]`, which is what
    #   the bracket is for. ⛔ Do not lower this to harvest verdicts.
    FLOOR = ncc(tN, tH)

    rows = []
    for label in ("Nafn", "Herodes", "Nuors", "Hun", "Hofud"):
        sN, sH = ncc(p[label]["vec"], tN), ncc(p[label]["vec"], tH)
        best = max(sN, sH)
        if best <= FLOOR:
            reads = "[HN] unresolved"
        else:
            reads = "H" if sH > sN else "N"
        rows.append((label, p[label]["kind"], p[label]["w"], sN, sH, sH - sN,
                     reads))

    # ⛔ Controls. Hun is corpus ground truth (12:0 H) AND the owner's ruling.
    byl = dict((r[0], r) for r in rows)
    hun = byl["Hun"]
    # ⚠ Must MATCH the H template above the floor — not merely lean that way.
    # A lean between two bad fits is what the flourish tool called a verdict.
    hun_ok = (hun[6] == "H")
    # ⛔ And the templates must still recover THEMSELVES, or the pipeline that
    # built them is broken and every score below is meaningless.
    tmpl_ok = (byl["Nafn"][6] == "N" and byl["Herodes"][6] == "H")

    if a.selftest:
        print("  template-N Nafn / template-H Herodes built from p37 line25")
        print("  control `Hun` (12:0 H in corpus, owner ruled H):")
        print("     vs N template %.4f   vs H template %.4f   H-N = %+.4f"
              % (hun[3], hun[4], hun[5]))
        print("     match floor (two KNOWN-DIFFERENT letters) = %.4f" % FLOOR)
        print("     reads as: %s" % hun[6])
        print("  Hun matches H ? %s (want True)" % hun_ok)
        print("  templates recover themselves ? %s (want True)" % tmpl_ok)

        # ★ SEGMENTATION CONTROL, with a KNOWN-BAD side. The plateau gate is
        # only worth having if it actually rejects the swallow it was built
        # for, so re-measure that swallow here rather than trusting it.
        # ⛔ A gate whose selftest does not exercise its failure mode is a
        #    green banner, not a control.
        ink, w, h = cache[os.path.join(PREP, "line40.png")]
        x0, x1 = 1157, 1321                       # the `Nuors` box
        bad = first_glyph_cols(ink, h, x0, min(x1, w), gap=3)
        good = stable_glyph_cols(ink, h, x0, min(x1, w))
        bad_w = None if bad is None else bad[1] - bad[0]
        good_w = None if good is None else good[1] - good[0]
        print("  segmentation control on `Nuors`:")
        print("     gap=3 (the shared default)  width %s  <- KNOWN BAD, "
              "swallows the next letter" % bad_w)
        print("     plateau-gated               width %s  (want <= 48)"
              % good_w)
        seg_ok = (bad_w == 65 and good_w is not None and good_w <= 48)
        print("  segmentation gate rejects the swallow ? %s (want True)"
              % seg_ok)

        if hun_ok and tmpl_ok and seg_ok:
            print("SELFTEST PASSED - type identity separates the known letters.")
            return 0
        print("SELFTEST FAILED - it calls the known-H word `Hun` an N.")
        print("  ⛔ The SAME failure as the delegated adjudication and the")
        print("     flourish measurement. REPORT IT; do not retune.")
        return 3

    print("%-9s %-10s %6s %10s %10s %10s   %s"
          % ("panel", "kind", "width", "vs N tmpl", "vs H tmpl", "H - N", "reads as"))
    print("-" * 86)
    for label, kind, w, sN, sH, d, reads in rows:
        print("%-9s %-10s %6d %10.4f %10.4f %+10.4f   %s"
              % (label, kind, w, sN, sH, d, reads))
    print("match floor (two KNOWN-DIFFERENT letters correlate this well) = %.4f"
          % FLOOR)
    print("A score at or below the floor is NOT a match: the site stays [HN].")
    print()
    if not tmpl_ok:
        sys.stderr.write("⛔ INSTRUMENT UNFIT: the templates do not recover "
                         "themselves. The glyph pipeline is broken.\n")
        return 3
    if not hun_ok:
        sys.stderr.write("⛔ INSTRUMENT UNFIT: the known-H word `Hun` matched "
                         "the N template (H-N = %+.4f). Probes above are "
                         "NOISE.\n" % hun[5])
        return 3
    print("CONTROL HELD: `Hun` matched the H template by %+.4f." % hun[5])
    print("⚠ TWO TEMPLATES, ONE PAGE, SAME FORME - a feasibility probe only.")
    print("⛔ NOT a screen. Do not point it at research/_parts/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
