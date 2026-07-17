# -*- coding: utf-8 -*-
"""eBible.org srp1865 USFM (Karadžić NT 1847 / Daničić OT 1865-68,
Latin script, ekavian) -> app asset.

Source: https://eBible.org/Scriptures/srp1865_usfm.zip — explicitly
Public Domain (copr.htm) and Redistributable=True in eBible's catalog
(unlike srp1868, the Cyrillic edition, whose catalog flag is under
inquiry — see store-assets/ebible_arabic_email_draft.txt). Litmus 6/7
verified 2026-07-16; the one deviation, Acts 20:28 «crkvu Gospoda i
Boga» ("church of the Lord and God"), is the conflate reading ALREADY
SHIPPED in cu_elizabeth and ru_synodal — same Slavonic lineage. Research
report: Hexapla-releases/research/karadzic_report.md.

⚠ The CrossWire SrKDIjekav module (Cyrillic, ijekavian — Karadžić's
authentic dialect) was surveyed 2026-07-17 and deferred: 94 divergent
chapters (whole Psalter on native numbering with vacuous trailing
slots) — integrable later as a second Serbian the way zh ships two
scripts. This eBible edition pre-aligns the Psalter (KJV grid, titles
as \\d markers) and leaves 17 native-divergent chapters, all curated
in build_versemap.py with seam text verified.

Handled here (surveyed 2026-07-16/17 against these exact bytes):
  * 126 \\d psalm superscriptions PREPENDED to verse 1 (KJV convention;
    concatenation-safe for multi-line titles, the Arabic lesson).
  * \\cl chapter labels, \\s1/\\s2 section heads, \\r refs, \\mt2 etc.
    dropped; q1/q2/p/b/pc continuation text appended to current verse.
  * ⚠ MODERN-PARAPHRASE SEAM DUPLICATES REPLACED: where native chapter
    boundaries diverge from the KJV grid, eBible filled the KJV slot
    with a MODERN Serbian rendering while the native slot keeps the
    authentic 1865 wording (e.g. Num 13:1 «A potom pođe narod od
    Asirota» = Daničić, vs the backfilled 12:16 «Posle toga narod je
    otišao iz Asirota» = contemporary Serbian). In a translation
    labeled 1847/1865 those anachronisms are replaced with the native
    slot's own text; the versemap pivots the coordinates anyway.
  * Native-divergent chapters (17) curated in build_versemap.py:
    Num 12/13 + 29/30 seams, 1 Sam 20:42 split, 1 Sam 23:29=24:1,
    1 Kgs 22:43 split, Song 5:17=KJV 6:1, Ezek 20:45-49=21:1-5,
    Hos 11:12=12:1, Jonah 1:17=2:1, 3 Jn 14/15, and the German-style
    Job reflow (srp 39 = KJV 38:39-40:5; srp 40 = KJV 40:6-41:9;
    srp 41 = KJV 41:10-34 — every boundary text-verified).
  * Book names from \\toc2 («1. Mojsijeva», «Psalmi», «Matej»).

Usage: python convert_serbian.py <srp1865_usfm.zip> <dst.json>
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

SKIP = {"h", "toc1", "toc2", "toc3", "mt1", "mt2", "mt3", "cl", "s1", "s2",
        "r", "ib", "ili", "im", "imt1", "ip", "ipr", "is1", "rem", "ide"}
CONT = {"q1", "q2", "p", "b", "pc", "nb", "m"}
TERMINAL = tuple(".!?…»)")

# (book code, KJV-slot chapter:verse) <- (native chapter:verse) — the
# KJV slot's modern paraphrase is replaced by the native slot's text.
SEAM_REPLACEMENTS = [
    ("NUM", (12, 16), (13, 1)),
    ("NUM", (29, 40), (30, 1)),
    ("1SA", (23, 29), (24, 1)),
    ("JOB", (38, 39), (39, 1)),
    ("JOB", (38, 40), (39, 2)),
    ("JOB", (38, 41), (39, 3)),
]


def clean(text):
    text = re.sub(r"\\f\s.*?\\f\*", "", text)
    text = re.sub(r"\\\+?[a-z]+[0-9]?\s*\*?", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    assert "\\" not in text, text
    return text


def parse_usfm(raw, path):
    code = name = None
    chapters, cur, cur_verse = {}, None, None
    pending_title = None
    titles = 0
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
        elif marker == "d":
            t = clean(rest)
            if t:
                t = t if t.endswith(TERMINAL) else t + "."
                pending_title = (pending_title + " " + t) if pending_title else t
                titles += 1
            cur_verse = None
        elif marker in SKIP:
            cur_verse = None
        elif marker == "c":
            cur = int(rest.split()[0])
            assert cur not in chapters, (path, cur)
            chapters[cur] = {}
            cur_verse = None
            pending_title = None
        elif marker == "v":
            vn, _, text = rest.partition(" ")
            assert "-" not in vn, (path, cur, vn)
            vn = int(vn)
            assert vn not in chapters[cur], (path, cur, vn)
            text = clean(text)
            if pending_title is not None:
                text = (pending_title + " " + text).strip()
                pending_title = None
            chapters[cur][vn] = text
            cur_verse = vn
        elif marker in CONT:
            if rest and cur_verse is not None:
                chapters[cur][cur_verse] = (
                    chapters[cur][cur_verse] + " " + clean(rest)).strip()
        else:
            raise AssertionError((path, marker))
    if code in ("FRT", "INT"):
        return code, None, None, 0
    assert code and name and chapters, path
    assert sorted(chapters) == list(range(1, len(chapters) + 1)), (path, sorted(chapters))
    return code, name, chapters, titles


def convert(src_zip, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    kjv = json.load(open(KJV, encoding="utf-8"))
    z = zipfile.ZipFile(src_zip)
    parsed, names, total_titles = {}, {}, 0
    for zn in sorted(z.namelist()):
        if not zn.endswith(".usfm"):
            continue
        code, name, chapters, titles = parse_usfm(z.read(zn).decode("utf-8-sig"), zn)
        if chapters is None:
            continue
        parsed[code] = chapters
        names[code] = name
        total_titles += titles
    assert sorted(parsed) == sorted(CANON_ORDER), sorted(parsed)
    assert total_titles == 126, total_titles

    replaced = 0
    for code, (kc, kv), (nc, nv) in SEAM_REPLACEMENTS:
        slot, native = parsed[code][kc].get(kv), parsed[code][nc].get(nv)
        assert slot and native, (code, kc, kv)
        assert slot != native, (code, kc, kv, "already native — upstream changed")
        parsed[code][kc][kv] = native
        replaced += 1

    books = []
    empty_slots, extras = [], []
    for bi, code in enumerate(CANON_ORDER):
        chapters = parsed[code]
        kch = kjv[bi]["chapters"]
        assert len(chapters) == len(kch), (code, len(chapters), len(kch))
        out_chapters = []
        for c in range(1, len(chapters) + 1):
            vs = chapters[c]
            assert sorted(vs) == list(range(1, max(vs) + 1)), (code, c)
            kn = len(kch[c - 1])
            verses = [vs[v] for v in range(1, max(vs) + 1)]
            for vn in range(1, min(kn, len(verses)) + 1):
                if not verses[vn - 1]:
                    empty_slots.append(f"{code} {c}:{vn}")
            if len(verses) != kn:
                extras.append(f"{code} {c}: {len(verses)} vs KJV {kn}")
            out_chapters.append(verses)
        books.append({"name": names[code], "chapters": out_chapters})
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83
    assert not empty_slots, empty_slots[:5]

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    out.write(f"{dst}: 83 book slots (66 canon), {total} verse slots, "
              f"{os.path.getsize(dst)} bytes\n")
    out.write(f"psalm titles prepended: {total_titles}\n")
    out.write(f"modern-paraphrase seam slots replaced with native text: {replaced}\n")
    out.write(f"native-divergent chapters ({len(extras)}, all versemap-curated):\n")
    for s in extras:
        out.write("  " + s + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
