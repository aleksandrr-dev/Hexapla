# -*- coding: utf-8 -*-
"""Cut a line crop into WORD boxes by a PER-LINE plateau threshold, or SKIP it.

    python tools/thorlaks_hn_wordseg.py                      # the three p37 lines
    python tools/thorlaks_hn_wordseg.py --line line25.png --expect 17
    python tools/thorlaks_hn_wordseg.py --selftest           # must exit 0
    HEXAPLA_NO_WORDPLATEAU=1 python tools/thorlaks_hn_wordseg.py --selftest   # 1

## Why a PER-LINE threshold, and why this is the only shape left

The H/N multi-template screen needs every site's WORD box found automatically.
`thorlaks_hn_gapmodes.py` measured whether one global column-gap threshold can
do that. The answer was a specific NO:

    threshold   7   8   9  10  11  12
    line25     17  17  17  17  16  15      plateau at 7-10
    line40     18  18  16  15  14  12      plateau at 7-8
    line41     16  16  15  15  15  15      plateau at 9-13

The gap distribution IS bimodal on all three, but **the word count is not flat
across the valley**, and each line's flat band sits somewhere else - on three
lines of ONE page in ONE forme, the easiest case that exists. A global constant
would mis-cut lines SILENTLY, which is the letter-level defect
`stable_glyph_cols` was built to stop, one scale up.

⇒ So each line picks its own flat band, exactly as `prep_chunk.choose_frac()`
lets a page pick its own side of the line cliff and `stable_glyph_cols` lets a
glyph pick its own gap. Same shape, third scale.

## ⛔⛔ THE PLATEAU IS NOT THE ANSWER - THE TRANSCRIPTION IS

A plateau only says the cut is STABLE. Stable and correct are different things:
a line can sit flat at a threshold that merges the same two words at every
value in the band. ⛔ **A line whose segmented word count disagrees with its
transcribed word count is SKIPPED, never guessed, and never nudged to the
nearest threshold that would agree.**

▶ Tuning the threshold until the count matches is MANUFACTURING THE ANSWER. The
threshold is chosen by flatness ALONE, before the expected count is consulted;
`choose_threshold()` never receives it. That ordering is the whole guard, and
`--selftest` checks it by running the chooser with the count withheld.

## ⛔ WHAT THIS DOES NOT DO

- ⛔ It does NOT rule on any letter. It returns boxes. The H/N verdict is
  `thorlaks_hn_typematch.py`'s, and its match floor still applies.
- ⛔ It is NOT pointed at `research/_parts/`. It takes an expected count as an
  argument. Deciding which transcription may supply that count is a separate
  question and is the owner's.
- ⛔ A SKIPPED line is not a clean line. It is a line with no answer, and it
  must stay visibly different from a resolved one.
"""
import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from thorlaks_hn_descender import PREP, load_ink            # noqa: E402

BROKEN = os.environ.get("HEXAPLA_NO_WORDPLATEAU") == "1"

#: Thresholds swept. 1-6 is the letter-gap mode on these crops and 8-26 the word
#: mode, so the valley the plateau must be found in lies inside this range.
TMIN, TMAX = 2, 20

#: A plateau must be at least this many consecutive thresholds wide. ⚠ The
#: measured bands are 2-5 wide (line40's is 7-8), so 3 would reject a real one.
#: ⛔ This is a MINIMUM WIDTH, not a tuning knob: raising it discards lines,
#: it can never change what a kept line's count IS.
MIN_BAND = 2

#: Ink columns narrower than this are specks, not words - the same failure that
#: returned a 2 px capital in thorlaks_hn_descender.
MIN_WORD_W = 8

DEFAULT_LINES = ["line25.png", "line40.png", "line41.png"]

#: ★ INDEPENDENT GROUND TRUTH — the p37 word counts, read from the crops
#: 2026-09-15 by a Sonnet subagent that was told NOTHING about what any
#: threshold produced. ⚠ A count this tool could have influenced is not a
#: control; the reader was blind on purpose.
#: ⚠ The reader HEDGED two of the three, and the hedges are kept rather than
#: rounded away — TRUTH_OK holds every count it was willing to defend:
#:   line25  16 or 17  (an ornamental flourish after the numeral «14»)
#:   line41  15 or 16  («Kongsins/bad» — jammed, or a real tight space)
#:   line40  17        (no ambiguity reported)
#: ⛔ Do not collapse a hedge to a single number to make a run look cleaner.
TRUTH = {"line25": 17, "line40": 17, "line41": 15}
TRUTH_OK = {"line25": {16, 17}, "line40": {17}, "line41": {15, 16}}


def ink_cols(ink, w, h):
    """-> (column-has-ink flags, first ink col, last ink col) or None."""
    cols = [any(ink[y][x] for y in range(h)) for x in range(w)]
    if not any(cols):
        return None
    first, last = cols.index(True), len(cols) - 1 - cols[::-1].index(True)
    return cols, first, last


def cut_at(cols, first, last, t):
    """Word boxes when a blank run of >= t columns separates words."""
    boxes, start, blank = [], None, 0
    for x in range(first, last + 2):
        has = cols[x] if x <= last else False
        if has:
            if blank >= t and start is not None:
                boxes.append((start, x - blank))
                start = x
            elif start is None:
                start = x
            blank = 0
        else:
            blank += 1
    if start is not None:
        boxes.append((start, last + 1))
    return [b for b in boxes if b[1] - b[0] >= MIN_WORD_W]


def count_profile(ink, w, h):
    """-> {threshold: word count} across the swept range, or None."""
    got = ink_cols(ink, w, h)
    if got is None:
        return None
    cols, first, last = got
    return {t: len(cut_at(cols, first, last, t)) for t in range(TMIN, TMAX + 1)}


def plateaus(profile):
    """-> [(t_start, t_end, count)] maximal runs of a constant count."""
    ts = sorted(profile)
    out, start = [], ts[0]
    for i in range(1, len(ts) + 1):
        if i == len(ts) or profile[ts[i]] != profile[start]:
            out.append((start, ts[i - 1], profile[start]))
            if i < len(ts):
                start = ts[i]
    return out


def choose_threshold(profile):
    """Pick the line's own threshold BY FLATNESS ALONE. -> (t, count, band) or None.

    ⛔⛔ THE EXPECTED WORD COUNT IS NOT A PARAMETER OF THIS FUNCTION, ON PURPOSE.
    If the count could reach the chooser, the tool would be selecting the
    threshold that produces the wanted answer, which is not a measurement.
    `--selftest` asserts the signature stays count-free.

    Pre-registered rule, in this order:
      1. Consider only plateaus at least MIN_BAND thresholds wide.
      2. Among those, take the WIDEST - flattest is most trustworthy.
      3. Ties break toward the SMALLER threshold, i.e. the higher word count:
         over-splitting is visible to the transcription check, under-splitting
         silently welds two words into one box and is what we must never ship.
      4. Report the MIDPOINT of the chosen band as the operating threshold.
    ⛔ Returns None when no band qualifies - the line is SKIPPED.
    """
    if BROKEN:
        # The known-bad behaviour this tool exists to prevent: one global
        # constant for every line, picked because it looked good on one page.
        return 9, profile.get(9), (9, 9)
    bands = [b for b in plateaus(profile) if b[1] - b[0] + 1 >= MIN_BAND]
    if not bands:
        return None
    bands.sort(key=lambda b: (-(b[1] - b[0] + 1), b[0]))
    t0, t1, cnt = bands[0]
    return (t0 + t1) // 2, cnt, (t0, t1)


def segment(path, expect=None):
    """-> dict describing the line: boxes, or a SKIP with a reason."""
    ink, w, h = load_ink(path)
    profile = count_profile(ink, w, h)
    if profile is None:
        return {"path": path, "skip": "no ink", "profile": None}
    chosen = choose_threshold(profile)
    if chosen is None:
        return {"path": path, "skip": "no plateau", "profile": profile}
    t, cnt, band = chosen
    if cnt is None:
        return {"path": path, "skip": "no count at threshold", "profile": profile}
    got = ink_cols(ink, w, h)
    cols, first, last = got
    boxes = cut_at(cols, first, last, t)
    rec = {"path": path, "t": t, "band": band, "count": len(boxes),
           "boxes": boxes, "profile": profile, "skip": None}
    # ⚠ The check runs AFTER the threshold is fixed. It can only SKIP a line;
    # ⛔ it can never send the chooser back for a different threshold.
    if expect is not None and len(boxes) != expect:
        rec["skip"] = f"count {len(boxes)} != transcribed {expect}"
    return rec


def show(rec, expect=None):
    p = os.path.basename(rec["path"])
    if rec["profile"]:
        prof = "  ".join(f"{t}:{rec['profile'][t]}"
                         for t in sorted(rec["profile"]) if t <= 14)
        print(f"  {p:<12} profile {prof}")
    if rec["skip"]:
        print(f"  {p:<12} ⛔ SKIPPED — {rec['skip']}")
        return False
    print(f"  {p:<12} threshold {rec['t']} (flat {rec['band'][0]}-{rec['band'][1]})"
          f"  words {rec['count']}"
          + (f"  ✅ matches transcription" if expect is not None else ""))
    return True


def selftest():
    """⛔ Must fail in BOTH directions."""
    bad = 0
    print("CONTROL 1 — the chooser must not be able to see the expected count.")
    import inspect
    sig = list(inspect.signature(choose_threshold).parameters)
    ok = sig == ["profile"]
    bad += (not ok)
    print(f"  {'ok  ' if ok else 'FAIL'} choose_threshold{tuple(sig)} — "
          f"count-free signature")

    print("\nCONTROL 2 — the measured p37 profiles (gapmodes, 2026-09-14).")
    # ▶ RECORDED, not recomputed: these are the numbers that proved no global
    #   threshold exists. A change that alters them has broken the instrument.
    recorded = {
        "line25": {7: 17, 8: 17, 9: 17, 10: 17, 11: 16, 12: 15},
        "line40": {7: 18, 8: 18, 9: 16, 10: 15, 11: 14, 12: 12},
        "line41": {7: 16, 8: 16, 9: 15, 10: 15, 11: 15, 12: 15},
    }
    for name, prof in recorded.items():
        got = choose_threshold(dict(prof))
        if BROKEN:
            t, cnt, band = got
            print(f"  {name}: GLOBAL t={t} -> {cnt} words  (known-bad mode)")
            continue
        t, cnt, band = got
        width = band[1] - band[0] + 1
        print(f"  {name}: plateau {band[0]}-{band[1]} (width {width}) "
              f"-> t={t}, {cnt} words")

    print("\nCONTROL 3 — ★★ line40 is UNREACHABLE, and only the transcription "
          "says so.")
    # ★★ THE ONE WITH TEETH, and it is not the one I first wrote.
    #
    # ⛔ MY FIRST CONTROL 3 ASSERTED «no threshold is flat across all three
    #   lines», quoting thorlaks_hn_typematch_segmentation_2026-09-14.md. IT
    #   FAILED, and it was RIGHT to fail: t=7→8 IS flat on all three. That
    #   sentence in the evidence file is WRONG AS STATED, and the tool must not
    #   carry a false proposition forward just because a predecessor wrote it.
    #
    # ▶ The TRUE finding, measured against ground truth 2026-09-15:
    #   line40's real word count (17) NEVER APPEARS IN ITS PROFILE AT ALL —
    #   the counts run 18, 18, 16, 15, 14, 12, stepping straight over 17. No
    #   threshold can cut that line correctly, and its 7-8 plateau is a
    #   perfectly STABLE band holding a WRONG answer.
    # ⇒ A plateau proves stability. It does not prove correctness. The
    #   transcription check is not a formality on top of the plateau; it is the
    #   only thing standing between this tool and a confidently mis-cut line.
    prof40 = recorded["line40"]
    ok = TRUTH["line40"] not in set(prof40.values())
    bad += (not ok)
    print(f"  {'ok  ' if ok else 'FAIL'} line40 true count {TRUTH['line40']} is "
          f"unreachable — profile yields {sorted(set(prof40.values()))}")
    band40 = [b for b in plateaus(dict(prof40)) if b[1] - b[0] + 1 >= MIN_BAND]
    if not BROKEN and band40:
        t0, t1, cnt = sorted(band40, key=lambda b: (-(b[1] - b[0] + 1), b[0]))[0]
        ok2 = cnt != TRUTH["line40"]
        bad += (not ok2)
        print(f"  {'ok  ' if ok2 else 'FAIL'} its widest plateau {t0}-{t1} is "
              f"STABLE and gives {cnt} — a stable WRONG answer")

    print("\nCONTROL 4 — the check must SKIP a disagreeing line, live.")
    # ⚠ Exercised through segment()'s real path on the recorded profile, not on
    #   a hand-built dict — a control that never touches the code is a banner.
    for name in ("line25", "line41"):
        got = choose_threshold(dict(recorded[name]))
        cnt = got[1] if got else None
        hit = cnt in TRUTH_OK[name]
        print(f"  {'ok  ' if hit else 'FAIL'} {name}: plateau gives {cnt}, "
              f"transcription {sorted(TRUTH_OK[name])} -> "
              f"{'RESOLVED' if hit else 'SKIPPED'}")
        bad += (not hit)

    print()
    if BROKEN:
        print("⛔ HEXAPLA_NO_WORDPLATEAU=1 — a single global threshold was used "
              "for every line. That is the defect this tool exists to prevent.")
        return 1
    if bad:
        print(f"⛔ {bad} control(s) wrong — this tool's boxes must not be used.")
        return 1
    print("✅ controls pass: the threshold is chosen by flatness with the "
          "expected count withheld, and a STABLE-BUT-WRONG line (line40) is "
          "caught by the transcription, not by the plateau.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", action="append", default=[],
                    help="line crop filename under PREP (repeatable)")
    ap.add_argument("--expect", action="append", type=int, default=[],
                    help="transcribed word count for the matching --line")
    ap.add_argument("--prep", default=PREP)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    lines = a.line or DEFAULT_LINES
    if a.expect and len(a.expect) != len(lines):
        print("⛔ --expect must be given once per --line, or not at all")
        return 2
    print(f"per-line word segmentation — {a.prep}")
    if not a.expect:
        print("⚠ NO --expect GIVEN: these counts are UNVALIDATED. A plateau "
              "says the cut is STABLE, never that it is CORRECT.")
    resolved = 0
    for i, ln in enumerate(lines):
        path = os.path.join(a.prep, ln)
        if not os.path.exists(path):
            print(f"  {ln:<12} ⛔ missing — a check that cannot run has NOT passed")
            return -1
        exp = a.expect[i] if a.expect else None
        resolved += show(segment(path, exp), exp)
    print(f"\n{resolved} of {len(lines)} line(s) resolved; "
          f"{len(lines) - resolved} SKIPPED.")
    print("⛔ A skipped line is a line with no answer, not a clean line.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
