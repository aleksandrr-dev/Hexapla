# -*- coding: utf-8 -*-
"""eBible.org ces1613 USFM (Bible kralická, 1613) -> app asset.

Source: https://eBible.org/Scriptures/ces1613_usfm.zip — explicitly
Public Domain (copr.htm; PGP-signed bundle), the 1613 "last hand"
text. Litmus 6/7 verified 2026-07-16 — Lk 2:33 «otec» is the accepted
pre-1881 Luther-class reading (de_luther/gda precedent). Research
report: Hexapla-releases/research/kralicka_report.md.

The cleanest USFM in the project (markers: id/h/toc1-3/mt1/c/p/v only —
no footnotes, no headings, no apparatus). NATIVE continental numbering
is KEPT: 62 title-psalms (all +1/+2, handled by build_versemap.py's
mechanical psalm_title_runs engine) and 29 curated chapters — every
seam text-verified 2026-07-17 (Exod 2:11+12 merge; the Num/1 Sam/
1 Kgs/Dan/Jonah/Hag Hebrew seams; the Job arrangement: 31:40 split,
KJV 37:1 = bkr 36:34, KJV 40:1-5 = bkr 39:31-35 — Kralická keeps the
lion verses IN ch 38, unlike Luther; Eccl straddles KJV 8:1 across
7:30/8:1; SNG 5:17 = KJV 6:1; John 1:38 split; Acts 19:40+41 and
2 Cor 13:12+13 merges; 3 Jn 15; Rev 12:18).

Book names from \\toc2 («1 Mojžíšova», «Žalmy», «Zjevení Janovo»).

Usage: python convert_kralicka.py <ces1613_usfm.zip> <dst.json>
"""
import io
import json
import os
import re
import sys
import zipfile

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

SKIP = {"h", "toc1", "toc2", "toc3", "mt1", "ide", "rem"}
CONT = {"p"}


def clean(text):
    text = re.sub(r"\s+", " ", text).strip()
    assert "\\" not in text, text
    return text


def parse_usfm(raw, path):
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
        elif marker == "toc2":
            name = rest
        elif marker in SKIP:
            cur_verse = None
        elif marker == "c":
            cur = int(rest.split()[0])
            assert cur not in chapters, (path, cur)
            chapters[cur] = {}
            cur_verse = None
        elif marker == "v":
            vn, _, text = rest.partition(" ")
            assert "-" not in vn, (path, cur, vn)
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
    z = zipfile.ZipFile(src_zip)
    parsed, names = {}, {}
    for zn in sorted(z.namelist()):
        if not zn.endswith(".usfm"):
            continue
        code, name, chapters = parse_usfm(z.read(zn).decode("utf-8-sig"), zn)
        parsed[code] = chapters
        names[code] = name
    assert sorted(parsed) == sorted(CANON_ORDER), sorted(parsed)

    books = []
    for code in CANON_ORDER:
        chapters = parsed[code]
        out_chapters = []
        for c in range(1, len(chapters) + 1):
            vs = chapters[c]
            assert sorted(vs) == list(range(1, max(vs) + 1)), (code, c)
            assert all(vs[v] for v in vs), (code, c, "empty verse")
            out_chapters.append([vs[v] for v in range(1, max(vs) + 1)])
        books.append({"name": names[code], "chapters": out_chapters})
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    out.write(f"{dst}: 83 book slots (66 canon), {total} verses (native "
              f"numbering, versemap pivots), {os.path.getsize(dst)} bytes\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
