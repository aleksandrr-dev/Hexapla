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

MULTI = {
    "glen_ezra_nehemiah_1-6.md": [("EZRA", 14), ("NEHEMIAH", 15)],
    "glen_nehemiah_7-13_esther.md": [("NEHEMIAH", 15), ("ESTHER", 16)],
    "glen_ecclesiastes_song.md": [("ECCLESIASTES", 20), ("SONG", 21)],
    "glen_hosea_joel.md": [("HOSEA", 27), ("JOEL", 28)],
    "glen_amos_obadiah_jonah_micah.md": [("AMOS", 29), ("OBADIAH", 30),
                                         ("JONAH", 31), ("MICAH", 32)],
    "glen_nahum_habakkuk_zephaniah_haggai_malachi.md": [
        ("Nahum", 33), ("Habakkuk", 34), ("Zephaniah", 35),
        ("Haggai", 36), ("Malachi", 38)],
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
        for label, idx in MULTI[base]:
            m = re.search(r"(?mi)^#+ *(?:BOOK: *)?" + label + r"\b", text)
            if m:
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
    rows = []
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
