# -*- coding: utf-8 -*-
"""eBible.org nld USFM (Statenvertaling, 1637/1888 spelling) -> app asset.

Source: https://eBible.org/Scriptures/nld_usfm.zip — "De Heilige Schrift
1917", explicitly Public Domain (copr.htm inside the zip; also stated on
https://ebible.org/find/show.php?id=nld). The 1637 Statenvertaling in its
1888 Jongbloed-lineage spelling; deity-verse litmus verified 7/7 on
2026-07-16 against these exact bytes (1 Tim 3:16 «God is geopenbaard in
het vlees», Comma present, Acts 8:37, Rom 16:24, Jozef at Lk 2:33,
Gemeente Gods at Acts 20:28, «Die in den hemel is» at Jn 3:13) — full
research report: Hexapla-releases/research/statenvertaling_report.md.

The source is ALREADY on the KJV grid — 31,102 verses exactly, psalm
titles inline with verse 1, 3 Jn 14/15 merged, Rev 12:18 folded into
13:1 — and marks every seam where native Dutch numbering diverges with a
literal "(chapter:verse)" fragment inside the verse text (Haiola tooling
artifact, e.g. Psalm 3:1 "Een psalm van David ... (3:2) O HEERE! ...").
Those markers are editorial apparatus, not scripture: stripped here, and
the count of stripped markers is asserted against a whole-corpus census
so a format change upstream cannot slip through silently (the survey of
2026-07-16 found exactly 1,396, and every OTHER digit-bearing
parenthetical in the corpus is a real parenthesized passage that must
survive — e.g. Rom 2:14-15 — so the regex must stay anchored to the
exact (N:N) shape).

Markers in this zip (surveyed 2026-07-16): id, ide, h, toc1/2/3, mt1,
c, p, v — no footnotes, no \\d psalm titles, no poetry markers. The
parser asserts on anything else so an upstream re-issue fails loudly.

Usage: python convert_statenvertaling.py <nld_usfm.zip> <dst.json>
"""
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
KJV = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "en_kjv.json")

CANON_ORDER = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
    "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
]

APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

SKIP = {"h", "toc1", "toc2", "toc3", "mt1", "ide"}
CONT = {"p"}

NATIVE_REF = re.compile(r"\s*\(\d+:\d+\)\s*")

stripped_refs = 0


def clean(text):
    global stripped_refs
    text, n = NATIVE_REF.subn(" ", text)
    stripped_refs += n
    text = re.sub(r"\s+", " ", text).strip()
    assert "\\" not in text, text
    return text


def parse_usfm(raw, path):
    """-> (book code, \\toc1 name, {chapter: {verse: text}})."""
    code = name = None
    chapters, cur, cur_verse = {}, None, None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"\\([a-z0-9]+)\s*(.*)$", line)
        assert m, (path, line)
        marker, rest = m.group(1), m.group(2).strip()
        if marker == "id":
            code = rest.split()[0]
        elif marker == "toc1":
            name = rest
            # toc1 doubles as a SKIP marker after capturing the name
        elif marker in SKIP:
            cur_verse = None
        elif marker == "c":
            cur = int(rest.split()[0])
            assert cur not in chapters, (path, cur)
            chapters[cur] = {}
            cur_verse = None
        elif marker == "v":
            vn, _, text = rest.partition(" ")
            assert "-" not in vn, (path, cur, vn)   # no bridges in this source
            vn = int(vn)
            assert vn not in chapters[cur], (path, cur, vn)
            chapters[cur][vn] = clean(text)
            cur_verse = vn
        elif marker in CONT:
            if rest and cur_verse is not None:
                chapters[cur][cur_verse] = (
                    chapters[cur][cur_verse] + " " + clean(rest)).strip()
        else:
            raise AssertionError((path, marker))
    assert code and name and chapters, path
    assert sorted(chapters) == list(range(1, len(chapters) + 1)), (path, sorted(chapters))
    return code, name, chapters


def convert(src_zip, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    kjv = json.load(open(KJV, encoding="utf-8"))
    z = zipfile.ZipFile(src_zip)

    # Whole-corpus census FIRST: the strip regex must account for every
    # (N:N)-shaped fragment, and nothing else digit-parenthesized may
    # match it (real parenthesized passages contain letters).
    census = 0
    for zn in z.namelist():
        if zn.endswith(".usfm"):
            census += len(NATIVE_REF.findall(z.read(zn).decode("utf-8-sig")))
    out.write(f"native-reference markers in corpus: {census}\n")

    parsed, names = {}, {}
    for zn in sorted(z.namelist()):
        if not zn.endswith(".usfm"):
            continue
        code, name, chapters = parse_usfm(z.read(zn).decode("utf-8-sig"), zn)
        parsed[code] = chapters
        names[code] = name
    assert sorted(parsed) == sorted(CANON_ORDER), sorted(parsed)
    assert stripped_refs == census, (stripped_refs, census)

    books = []
    empty_slots, extras = [], []
    for bi, code in enumerate(CANON_ORDER):
        chapters = parsed[code]
        kch = kjv[bi]["chapters"]
        assert len(chapters) == len(kch), (code, len(chapters), len(kch))
        out_chapters = []
        for c in range(1, len(chapters) + 1):
            vs = chapters[c]
            kn = len(kch[c - 1])
            n = max(kn, max(vs))
            verses = [""] * n
            for vn, text in vs.items():
                verses[vn - 1] = text
            for vn in range(1, kn + 1):
                if vn not in vs or not vs[vn]:
                    empty_slots.append(f"{code} {c}:{vn} (empty slot)")
            for vn in sorted(vs):
                if vn > kn:
                    extras.append(f"{code} {c}:{vn} beyond KJV count {kn} "
                                  f"(native versification -> curate in build_versemap.py)")
            out_chapters.append(verses)
        books.append({"name": names[code], "chapters": out_chapters})
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    filled = sum(1 for b in books for c in b["chapters"] for v in c if v)
    out.write(f"{dst}: 83 book slots (66 canon), {total} verse slots, "
              f"{filled} with text, {os.path.getsize(dst)} bytes\n")
    out.write(f"stripped native refs: {stripped_refs} (census-matched)\n")
    out.write(f"empty KJV slots: {len(empty_slots)}\n")
    for s in empty_slots:
        out.write("  " + s + "\n")
    out.write(f"beyond-KJV verses: {len(extras)}\n")
    for s in extras:
        out.write("  " + s + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
