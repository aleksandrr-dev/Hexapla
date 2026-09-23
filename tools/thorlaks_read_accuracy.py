#!/usr/bin/env python
"""thorlaks_read_accuracy.py - score a READ against an adjudicated GOLD page.

WHY THIS EXISTS
---------------
The campaign has never had a measured word-accuracy figure for any page. The
method was tuned to maximise effort, not to hit a stated target, so every
proposal to make it cheaper ran into an argument instead of a number. This
tool turns "is it correct?" into a measurement.

Measured 2026-09-20 over Luke p61/p63/p65/p67 (3,434 gold words): a SINGLE
read is 88.50% word-accurate against the adjudicated page, and the two reads
of a page score within 1.5 points of each other every time. That figure is
the baseline any cheaper method has to beat - or be knowingly traded away.

WHAT IT DOES NOT DO
-------------------
- It does NOT tell you the gold is right. The gold is the adjudicated part
  file; it is the best reading this campaign has produced, not ground truth.
  A tool that scored against the print would need the print.
- It does NOT score coverage. A read that omits a verse entirely is reported
  separately (VERSES ABSENT) and is NOT averaged into the word figure, because
  a missing verse is a different defect class from a misread word and hiding
  one inside the other is how a chunk that never happened looks fine.

SCORING
-------
Word accuracy = matched gold words / total gold words, from a per-verse
difflib alignment. Three folds are reported because they answer different
questions:

  raw        - exactly as written, the number that matters for shipping
  case       - case-folded; isolates capital H/N flourish disputes
  diacritic  - also folds d/th and strips combining marks; isolates
               orthographic drift (a reader writing modern Icelandic accents
               the print does not carry) from substantive misreading

The gap between `raw` and `diacritic` IS the orthographic-drift bill. On the
four Luke pages it runs 1 to 5 points, which is large enough that quoting a
single unqualified accuracy figure for this corpus is misleading.

CONTROLS - both ways, per the campaign rule that a new screen is broken until
a control fires:
    python tools/thorlaks_read_accuracy.py --selftest
      known-good: a file scored against itself must read 100.00%
      known-bad : gold corrupted at a known rate must read at/below that rate
    HEXAPLA_NO_ACCURACY=1 makes the scorer inert, so a harness that reports a
    number with it set is reading its own stub and is broken.

USAGE
-----
    python tools/thorlaks_read_accuracy.py \\
        --gold C:/Projects/Hexapla-releases/research/_parts/luke_p67.md \\
        --read C:/Projects/Hexapla-releases/_work/luke_p67_readB_2026-09-20.md

    # several reads against one gold, as a table
    python tools/thorlaks_read_accuracy.py --gold <gold> --read <a> --read <b>

    # every _parts page that has a matching _work read, the FULL denominator
    python tools/thorlaks_read_accuracy.py --sweep <book>

Exit codes: 0 scored; 1 a read fell below --floor; 2 bad arguments or no
overlapping verses (never 0 - a scorer that cannot run did not pass).
"""
import argparse
import difflib
import glob
import os
import re
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

VERSE = re.compile(r"^(\d{1,3}) +(.*)$")
CROP_ADDR = re.compile(r"\u2014\s*line\d+(?:-line\d+)?\s*$")
BRACKET = re.compile(r"\[[^\]]*\]")
SPLIT = re.compile(r"[\s/.,:;\u00ab\u00bb()?*]+")


def load_verses(path):
    """Verse number -> body, with crop addresses and [editorial notes] removed.

    Both are stripped on purpose: the address is provenance, not text, and a
    bracketed note is the transcriber talking, not the print. Leaving either
    in would score a read down for annotating well.
    """
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = VERSE.match(line)
            if not m:
                continue
            body = CROP_ADDR.sub("", m.group(2))
            body = BRACKET.sub("", body)
            out[int(m.group(1))] = body
    return out


def tokens(text):
    return [w for w in SPLIT.split(text) if w]


def fold_case(word):
    return word.lower()


def fold_diacritic(word):
    word = word.lower().replace("\u00f0", "d").replace("\u00fe", "th")
    return "".join(
        c for c in unicodedata.normalize("NFD", word)
        if unicodedata.category(c) != "Mn"
    )


FOLDS = (("raw", lambda w: w), ("case", fold_case), ("diacritic", fold_diacritic))


def score(gold, read, folder):
    """Return (gold_words, matched_words) over the verses both files carry."""
    total = matched = 0
    for v in sorted(set(gold) & set(read)):
        g = [folder(w) for w in tokens(gold[v])]
        r = [folder(w) for w in tokens(read[v])]
        sm = difflib.SequenceMatcher(None, g, r)
        matched += sum(b.size for b in sm.get_matching_blocks())
        total += len(g)
    return total, matched


def report(gold_path, read_path, floor):
    gold = load_verses(gold_path)
    read = load_verses(read_path)
    if os.environ.get("HEXAPLA_NO_ACCURACY"):
        print("  HEXAPLA_NO_ACCURACY=1 - scorer inert, no figure produced")
        return None
    shared = set(gold) & set(read)
    if not shared:
        print("  \u26d4 no overlapping verses - NOT a score of 0, a failure to run")
        return None
    figures = {}
    for name, folder in FOLDS:
        total, matched = score(gold, read, folder)
        figures[name] = 100.0 * matched / total if total else 0.0
    absent = sorted(set(gold) - set(read))
    extra = sorted(set(read) - set(gold))
    total, _ = score(gold, read, lambda w: w)
    print("  %-38s raw %6.2f%%  case %6.2f%%  diacritic %6.2f%%  (%d gold words)"
          % (os.path.basename(read_path), figures["raw"], figures["case"],
             figures["diacritic"], total))
    if absent:
        print("     \u26a0 VERSES ABSENT FROM THE READ (not averaged in): %s"
              % ", ".join(str(v) for v in absent))
    if extra:
        print("     \u26a0 verses the read has and the gold does not: %s"
              % ", ".join(str(v) for v in extra))
    if floor is not None and figures["raw"] < floor:
        print("     \u26d4 BELOW FLOOR %.2f%%" % floor)
    return figures


def selftest():
    """Both ways. A scorer that only ever passes is not a control."""
    gold = {1: "Og hann kiende j einu af Samkundu", 2: "Enn er Jesus leit hana"}
    total, matched = score(gold, dict(gold), lambda w: w)
    good = abs(100.0 * matched / total - 100.0) < 1e-9
    print("  known-good (file against itself): %.2f%%  %s"
          % (100.0 * matched / total, "PASS" if good else "FAIL"))

    # corrupt exactly one word in four
    bad = {}
    for v, body in gold.items():
        ws = tokens(body)
        bad[v] = " ".join("XXXX" if i % 4 == 0 else w for i, w in enumerate(ws))
    total, matched = score(gold, bad, lambda w: w)
    got = 100.0 * matched / total
    ok = got <= 76.0
    print("  known-bad  (1 word in 4 corrupted): %.2f%%  %s (must be <= 76%%)"
          % (got, "PASS" if ok else "FAIL"))

    inert = bool(os.environ.get("HEXAPLA_NO_ACCURACY"))
    print("  HEXAPLA_NO_ACCURACY currently %s" % ("SET - scorer inert" if inert else "unset"))
    return 0 if (good and ok) else 1


def sweep(book, floor):
    releases = r"C:\Projects\Hexapla-releases"
    parts = sorted(glob.glob(os.path.join(releases, "research", "_parts",
                                          "%s_p*.md" % book.lower())))
    if not parts:
        print("no gold part files for %s" % book)
        return 2
    seen = 0
    for gold_path in parts:
        stem = os.path.basename(gold_path)[:-3]
        reads = sorted(glob.glob(os.path.join(releases, "_work", "%s_read*.md" % stem)))
        reads = [r for r in reads if not r.endswith((".bak", ".pre-recut"))]
        if not reads:
            continue
        print("%s" % stem)
        for r in reads:
            report(gold_path, r, floor)
        seen += 1
    if not seen:
        print("\u26a0 no gold page had a matching read - nothing was scored")
        return 2
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gold", help="adjudicated part file")
    ap.add_argument("--read", action="append", default=[], help="a read to score; repeatable")
    ap.add_argument("--sweep", help="score every page of this book that has a read")
    ap.add_argument("--floor", type=float, default=None,
                    help="exit 1 if any read's raw accuracy falls below this")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.sweep:
        return sweep(args.sweep, args.floor)
    if not args.gold or not args.read:
        ap.error("need --gold and at least one --read, or --sweep, or --selftest")
    if not os.path.exists(args.gold):
        print("gold not found: %s" % args.gold)
        return 2
    print(os.path.basename(args.gold))
    below = False
    for r in args.read:
        if not os.path.exists(r):
            print("  read not found: %s" % r)
            return 2
        figs = report(args.gold, r, args.floor)
        if figs is None:
            return 2
        if args.floor is not None and figs["raw"] < args.floor:
            below = True
    return 1 if below else 0


if __name__ == "__main__":
    sys.exit(main())
