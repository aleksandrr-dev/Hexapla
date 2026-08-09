# -*- coding: utf-8 -*-
"""Build the Glen defect inventory from the chunk reports' MARKER STREAMS.

This is the input to two things: the 1845 witness adjudication, and the defect
table `build_glen_ot.py` needs so a defective printed numeral cannot restart the
converter's verse counter.

⚠ DERIVED FROM THE ARTIFACT, NOT THE PROSE. A report's flag text is commentary
and has been wrong in both directions during this campaign — sites flagged that
turned out genuine, sites normalized away with a flag still describing them. The
marker stream is what the converter will actually parse, so the marker stream is
what the inventory is built from. Prose is used only to attach evidence.

Classification, from the sequence shape at the deviation:
  DUP      printed numeral repeats, the next value never appears
           (e.g. 6,8,8,9 = «۷» skipped, «۸» printed twice)
  SUBST    a wrong value in an otherwise correct run
           (e.g. 5,2,7 at position 6 = «۲» printed for «۶»; the bare-«۱»-for-«۹»
           class is this shape)
  SHORT    one fewer marker than the reference expects, sequence contiguous
           (= a numeral omitted outright, content running on unmarked)
  LONG     one more marker than the reference expects

    python tools/glen_defect_inventory.py                 # all books
    python tools/glen_defect_inventory.py --csv out.csv
"""
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
sys.path.insert(0, str(RESEARCH))
_argv = sys.argv[:]
sys.argv = ["scan_markers"]
import scan_markers as sm  # noqa: E402
sys.argv = _argv

KJV = r"C:/Projects/Hexapla/app/src/main/assets/bibles/en_kjv.json"

# file -> [(book_index, section-heading regex or None)]
# Single-book files map straight to an index; multi-book files are split on
# their own book headers, which differ per file because different agents wrote
# them. Anything not listed is scanned without a reference count.
BOOKS = {
    "genesis": 0, "exodus": 1, "leviticus": 2, "numbers": 3, "deuteronomy": 4,
    "joshua": 5, "judges": 6, "ruth": 7, "1samuel": 8, "2samuel": 9,
    "1kings": 10, "2kings": 11, "1chronicles": 12, "2chronicles": 13,
    "job": 17, "psalms": 18, "proverbs": 19, "isaiah": 22, "jeremiah": 23,
    "lamentations": 24, "ezekiel": 25, "daniel": 26, "zechariah": 37,
}
# ⚠ NOT canonical transcriptions — second-witness passes, spot-checks,
# reconstruction notes, and superseded partial files that OVERLAP a complete
# one. Including them double-counts sites and (for the re-witness files) mixes
# a second reading into an inventory that must describe the shipped text.
EXCLUDE = (
    "rewitness", "spotcheck", "recon", "headings",
    "glen_joshua_10-12.md",        # subset of glen_joshua_1-12.md
    "glen_deuteronomy_28-34.md",   # subset of glen_deuteronomy_16-34.md
)

# Multi-book files, as (book_index, start-of-section regex). `None` means the
# section starts at the top of the file.
# ⚠ EVERY FILE HEADS ITS BOOKS DIFFERENTLY — different agents, different weeks:
# «# نحمیاه (Nehemiah)», «## استیر — فصلِ اوّل», «# BOOK: AMOS»,
# «## SONG OF SOLOMON», «## Habakkuk (idx …)». An earlier version assumed one
# uniform style, matched nothing in three files, and silently fell through to a
# single-book scan — which MERGES two books' chapter numbers and manufactured
# five phantom "Ezra" defects (Ezra 3 reading 32 markers against KJV 13).
# Match the real headings, and assert below that every section was found.
MULTI = {
    "glen_ezra_nehemiah_1-6.md": [
        (14, None), (15, r"(?m)^#\s*نحمیاه")],
    "glen_nehemiah_7-13_esther.md": [
        (15, None), (16, r"(?m)^##\s*استیر")],
    "glen_ecclesiastes_song.md": [
        (20, None), (21, r"(?mi)^##\s*SONG OF SOLOMON")],
    "glen_hosea_joel.md": [
        (27, None), (28, r"(?mi)^##+\s*JOEL")],
    "glen_amos_obadiah_jonah_micah.md": [
        (29, None), (30, r"(?mi)^#\s*BOOK:\s*OBADIAH"),
        (31, r"(?mi)^#\s*BOOK:\s*JONAH"), (32, r"(?mi)^#\s*BOOK:\s*MICAH")],
    "glen_nahum_habakkuk_zephaniah_haggai_malachi.md": [
        (33, None), (34, r"(?mi)^##\s*Habakkuk"),
        (35, r"(?mi)^##\s*Zephaniah"), (36, r"(?mi)^##\s*Haggai"),
        (38, r"(?mi)^##\s*Malachi")],
}
FA = "۰۱۲۳۴۵۶۷۸۹"


def fa(n):
    return "".join(FA[int(d)] for d in str(n))


def kjv_counts():
    d = json.load(open(KJV, encoding="utf-8"))
    return [[len(c) for c in b["chapters"]] for b in d], [b["name"] for b in d]


def classify(got, expected):
    """Return list of (kind, position, printed_glyph_value)."""
    out = []
    for i, v in enumerate(got, 1):
        if v != i:
            # the first deviation characterises the site
            kind = "DUP" if got.count(v) > 1 else "SUBST"
            out.append((kind, i, v))
            break
    if not out and expected is not None and len(got) != expected:
        out.append(("SHORT" if len(got) < expected else "LONG",
                    len(got), None))
    return out


def sections(path, name):
    """Yield (book_index, chapter_dict) for one report file."""
    base = os.path.basename(path)
    if base in MULTI:
        text = open(path, encoding="utf-8").read()
        marks = []
        for idx, pat in MULTI[base]:
            if pat is None:
                marks.append((0, idx))
                continue
            m = re.search(pat, text)
            if not m:
                # Never fall through to a single-book scan: that is exactly the
                # failure that manufactured the phantom Ezra defects.
                raise SystemExit(f"{base}: section pattern {pat!r} matched "
                                 f"nothing — fix the pattern, do not guess")
            marks.append((m.start(), idx))
        marks.sort()
        for i, (s, idx) in enumerate(marks):
            e = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            tmp = RESEARCH / "_inv_seg.md"
            tmp.write_text(text[s:e], encoding="utf-8")
            _, ch = sm.scan(str(tmp))
            tmp.unlink()
            yield idx, ch
        return
    idx = None
    for key, v in BOOKS.items():
        if key in base:
            idx = v
            break
    _, ch = sm.scan(path)
    yield idx, ch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    args = ap.parse_args()

    counts, names = kjv_counts()

    # ⚠ DEDUPE ACROSS FILES FIRST. Chunk boundaries overlap: a chapter can
    # appear both as the trailing fragment of one chunk and in full in the
    # chunk that owns it (Numbers 25 sits in both the 11-24 and 25-36 files).
    # Classifying both produced a phantom "SHORT" defect from the fragment.
    # Keep the copy whose marker count matches the reference; failing that, the
    # longest — a fragment is never longer than the whole chapter.
    best = {}
    for path in sorted(glob.glob(str(RESEARCH / "glen_*.md"))):
        if ".bak" in path or any(x in os.path.basename(path)
                                 for x in EXCLUDE):
            continue
        for bidx, chapters in sections(path, None):
            for c in sorted(chapters):
                got = chapters[c]
                if not got:
                    continue
                exp = None
                if bidx is not None and c - 1 < len(counts[bidx]):
                    exp = counts[bidx][c - 1]
                key = (bidx, c)
                prev = best.get(key)
                if prev is None:
                    best[key] = (got, exp, path)
                else:
                    pgot = prev[0]
                    better = (len(got) == exp and len(pgot) != exp) or \
                             (exp is None and len(got) > len(pgot)) or \
                             (len(pgot) != exp and len(got) > len(pgot))
                    if better:
                        best[key] = (got, exp, path)

    rows = []
    if True:
        for (bidx, c), (got, exp, path) in sorted(
                best.items(), key=lambda kv: (kv[0][0] if kv[0][0] is not None
                                              else 99, kv[0][1])):
            if True:
                for kind, pos, val in classify(got, exp):
                    rows.append({
                        "book": names[bidx] if bidx is not None else "?",
                        "bidx": bidx, "chapter": c, "position": pos,
                        "kind": kind,
                        "printed": fa(val) if val is not None else "(none)",
                        "expected": fa(pos),
                        "markers": len(got), "kjv": exp if exp else "?",
                        "file": os.path.basename(path),
                    })

    rows.sort(key=lambda r: (r["bidx"] if r["bidx"] is not None else 99,
                             r["chapter"]))
    print(f"{'book':<14}{'ch':>4}{'v':>5}  {'kind':<6}{'printed':>8}"
          f"{'want':>6}  {'n/KJV':>9}")
    print("-" * 62)
    for r in rows:
        print(f"{r['book']:<14}{r['chapter']:>4}{r['position']:>5}  "
              f"{r['kind']:<6}{r['printed']:>8}{r['expected']:>6}  "
              f"{str(r['markers'])+'/'+str(r['kjv']):>9}")
    print(f"\n{len(rows)} defect sites across "
          f"{len({r['bidx'] for r in rows})} books")
    from collections import Counter
    print(Counter(r["kind"] for r in rows))

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print("wrote", args.csv)


if __name__ == "__main__":
    main()
