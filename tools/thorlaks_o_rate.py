# -*- coding: utf-8 -*-
"""Derive the ø rate for a Þorláksbiblía book — per page AND for the whole book.

    python tools/thorlaks_o_rate.py --book Mark

## ⚠ WHY THIS EXISTS

The per-page rate is the campaign's only signal that a page was read at the
wrong resolution: `THORLAKS_CONVENTIONS.md` expects 19-31 % per BOOK and calls a
book under 10 % a defect rather than a dialect. Until now every rate was
hand-computed in the page record it belonged to, so:

* only p43-p49 of Mark had one at all — eleven of the eighteen pages carried no
  denominator, and the «14.7 %» that stood for Mark was seven pages of it;
* the whole-book figure — the one the convention actually states a band for —
  could not be computed without redoing eleven hand counts;
* two consecutive pages share their boundary verse, so adding per-page
  denominators double-counts it.

⛔⛔ **A PER-PAGE RATE IS NOT THE FIGURE THE CONVENTION BOUNDS.** p46 read 8.0 %
and p47 read 26.1 % on the same instrument, in the same session, one page apart:
the rate is driven by VOCABULARY (the Passion narrative is dense with
«Høfudprest-», «kølludu», «høfdu»; Mark 12-13's teaching material is not). So a
low PAGE is not evidence of a bad read, and only the BOOK figure may be compared
to the band.

## ⚠ WHAT THE DENOMINATOR IS

Every letter-o POSITION in the part-file text for the verses the page covers —
that is, `o` plus already-stroked `ø`, both cases. This is the same definition
the p44-p49 records used by hand ("o-positions in the … part-file text"), and
this tool CONTROLS itself against those recorded numbers on every run: a
derivation that disagrees with the hand counts is reported as a FAILURE, not
quietly used.

⛔ It is a count over the TRANSCRIPTION, not over the image. A page whose
transcription is short or wrong has a wrong denominator, and that is a finding
about the transcription — `thorlaks_part_check.py` is what tests it.

## ⛔ WHAT IT DOES NOT DO

It does not read images, it does not adjudicate, and it never writes. It is a
0-token derivation, so it runs over the WHOLE book every time — never a sample.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from thorlaks_o_patch import (BOOK_PARTS, REC, WORK, build_verse_index,
                              clean_word, part_for, pages_for, verse_ref)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# «Page spans Mark 1:1–1:31.» / «SCRIPTURE spans Mark 15:12–15:47 and ENDS AT …»
SPAN = re.compile(
    r"(?:Page|SCRIPTURE)\s+spans\s+[A-Za-z]+\s*"
    r"(\d+):(\d+)\s*[-–—]\s*(?:[A-Za-z]+\s*)?(\d+):(\d+)")
# «DENOMINATOR: 113 o-positions …» — the hand count, for the control only.
DENOM = re.compile(r"DENOMINATOR:\s*(\d+)\s+o-positions")
O_CHARS = "oOøØöÖ"


def page_of(name):
    m = re.search(r"_p(\d+)[_a-z]*_READJUDICATED", name)
    return int(m.group(1)) if m else None


# ⚠⚠ EDITORIAL ASIDES ARE COUNTED, BECAUSE THE HAND COUNTS COUNT THEM.
# The part files bracket two different things: a multi-word English aside from
# the transcriber ("[unnumbered - printed v1, no numeral visible under the
# chapter head ...]") and a SHORT supplied fragment that is printed text
# ("[u]", "[ta]", "[er]"). Excluding the asides looks obviously right and is
# WRONG here: it moved p45, p46 and p47 OFF hand counts they had reproduced
# exactly - p46's note alone holds nine English o's that its recorded 137
# includes. The denominator is defined as the o-positions in the part-file
# TEXT, and that is what the adjudicators counted.
# ⛔ So this strips the verse NUMBER and nothing else. A rule that fits one
# page by breaking three is not a fix; p49 is reported as a finding instead.
VERSE_NO = re.compile(r"(?m)^\d+\s")


def strip_nontext(text):
    """-> the verse text without its leading verse number."""
    return VERSE_NO.sub("", text)


def count_o(text):
    """-> (o-positions, of which already stroked). ⚠ Every letter-o POSITION,
    which includes the ones already reading ø — otherwise a page that has been
    patched would show a shrinking denominator and a rising rate."""
    positions = sum(text.count(c) for c in O_CHARS)
    stroked = sum(text.count(c) for c in "øØöÖ")
    return positions, stroked


def verses_between(idx, lo, hi):
    """-> the (chapter, verse) keys of `idx` between lo and hi inclusive."""
    return [k for k in idx
            if (lo[0], lo[1]) <= (k[0], k[1]) <= (hi[0], hi[1])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="Mark")
    ap.add_argument("--glob", default="o_retrofit_*READJUDICATED*.txt")
    a = ap.parse_args()

    rng = pages_for(a.book)
    if rng is None:
        print(f"⛔ «{a.book}» has no row in BOOK_PARTS — add its page ranges.")
        return 1

    parts, idxs = {}, {}
    for _lo, _hi, stem in BOOK_PARTS[a.book.lower()]:
        pf = part_for(a.book, _lo)
        parts[pf] = pf.read_text(encoding="utf-8")
        idxs[pf] = build_verse_index(parts[pf])

    rows, control, book_verses, book_sites = [], [], set(), 0
    for f in sorted(WORK.glob(a.glob)):
        page = page_of(f.name)
        if page is None or not (rng[0] <= page <= rng[1]):
            continue
        txt = f.read_text(encoding="utf-8")
        m = SPAN.search(txt.replace("\n", " "))
        if not m:
            print(f"  ⛔ p{page}: no «Page spans …» line in {f.name} — "
                  f"NO DENOMINATOR CAN BE DERIVED. This page is UNMEASURED, "
                  f"which is not the same as a low rate.")
            rows.append((page, None, None, None, None))
            continue
        lo = (int(m.group(1)), int(m.group(2)))
        hi = (int(m.group(3)), int(m.group(4)))

        pf = part_for(a.book, page)
        keys = verses_between(idxs[pf], lo, hi)
        text = "".join(parts[pf][idxs[pf][k][0]:idxs[pf][k][1]] for k in keys)
        positions, stroked = count_o(strip_nontext(text))

        # confirmed sites, counted exactly as the patcher counts them
        sectioned = "## CONFIRMED ø" in txt
        section, n_sites = "", 0
        for raw in txt.splitlines():
            line = raw.rstrip()
            if line.startswith("##"):
                section = line
            r = REC.match(line)
            if not r or line.startswith("#"):
                continue
            if sectioned and "CONFIRMED ø" not in section:
                continue
            if "UNCERTAIN" in r.group(4).upper():
                continue
            w = clean_word(r.group(4))
            if w and " " not in w:
                n_sites += 1

        rows.append((page, f"{lo[0]}:{lo[1]}–{hi[0]}:{hi[1]}",
                     n_sites, positions, stroked))
        book_verses.update((pf, k) for k in keys)
        book_sites += n_sites

        d = DENOM.search(txt)
        if d:
            control.append((page, int(d.group(1)), positions))

    print(f"ø RATE — {a.book}\n")
    print(f"{'page':>5}  {'verses':<16} {'ø sites':>7} {'o-pos':>6} "
          f"{'rate':>7}  {'already ø':>9}")
    for page, span, n, pos, stroked in rows:
        if span is None:
            print(f"{page:>5}  {'— UNMEASURED —':<16}")
            continue
        print(f"{page:>5}  {span:<16} {n:>7} {pos:>6} "
              f"{n / pos * 100:>6.1f}% {stroked:>9}")

    # ---- the BOOK figure, over the union of verses so no boundary is counted
    #      twice. Two consecutive pages share their boundary verse.
    total_pos = total_stroked = 0
    for pf, k in book_verses:
        s, e = idxs[pf][k]
        pos, st = count_o(strip_nontext(parts[pf][s:e]))
        total_pos += pos
        total_stroked += st
    measured = [r for r in rows if r[1] is not None]
    print(f"\n▶ WHOLE BOOK ({len(measured)} page(s) measured, "
          f"{len(book_verses)} distinct verse(s) — shared boundary verses "
          f"counted ONCE):")
    print(f"    {book_sites} confirmed ø / {total_pos} o-positions = "
          f"{book_sites / total_pos * 100:.1f} %")
    band = 19 <= book_sites / total_pos * 100 <= 31
    print(f"    convention band is 19-31 % per BOOK: "
          f"{'INSIDE' if band else '⚠ OUTSIDE'}")
    if not band:
        print("    ⚠ OUTSIDE THE BAND IS A QUESTION, NOT A VERDICT. The band "
              "was set on other books; a page-level refutation of "
              "«under-detection» already exists (p47 read 26.1 % on the same "
              "instrument that read 8.0 % on p46). ▶ Ask what the book's "
              "VOCABULARY is before touching the method.")
    if total_stroked:
        print(f"    ⚠ {total_stroked} o-position(s) already read ø in the "
              f"transcription. If a patch has been applied they are counted "
              f"here, so this figure is NOT additive with the sites above.")

    print("\n▶ CONTROL — derived denominator vs the hand count recorded "
          "in the page's own file")
    if not control:
        print("    ⛔ NO PAGE RECORDS A HAND COUNT — the derivation is "
              "UNCONTROLLED. Do not quote these figures until one does.")
        return 1
    bad = 0
    for page, hand, derived in control:
        ok = hand == derived
        bad += not ok
        print(f"    p{page}: recorded {hand:>4}   derived {derived:>4}   "
              f"{'✅' if ok else '⛔ DISAGREE'}")
    if bad:
        drift = sum(h - d for _p, h, d in control if h != d)
        alt = book_sites / (total_pos + drift) * 100
        here = book_sites / total_pos * 100
        same = (19 <= alt <= 31) == (19 <= here <= 31)
        print(f"\n⛔⛔ {bad} of {len(control)} controlled page(s) DISAGREE with "
              f"their own recorded hand count. A page that disagrees is a "
              f"FINDING about THAT PAGE \u2014 the hand count or the transcription "
              f"moved since it was written \u2014 and it is resolved by re-reading "
              f"that page's record, never by tuning this rule until it fits. "
              f"(A filter that fitted p49 moved p45, p46 and p47 OFF counts "
              f"they had reproduced exactly.)")
        print(f"   \u25b6 BOUND ON THE BOOK FIGURE: taking every recorded hand "
              f"count in preference to this derivation would give {alt:.1f} % "
              f"instead of {here:.1f} % \u2014 "
              + ("the same conclusion against the band."
                 if same else "⚠ A DIFFERENT CONCLUSION against the band."))
        print(f"   ⚠ So the BOOK figure may be quoted with this caveat "
              f"attached. The PER-PAGE figure for a disagreeing page may not "
              f"be quoted at all.")
        return 1
    print(f"    ✅ all {len(control)} controlled page(s) reproduce exactly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
