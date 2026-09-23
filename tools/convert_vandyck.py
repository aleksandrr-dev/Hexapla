# -*- coding: utf-8 -*-
"""eBible.org arb-vd USFM (Smith-Van Dyck 1865, Arabic) -> app asset.

Source: https://eBible.org/Scriptures/arb-vd_usfm.zip — explicitly Public
Domain (copr.htm; eBible's catalog marks two OTHER Arabic Bibles © in the
same file, so the PD label is a deliberate per-title call). Deity-verse
litmus verified 7/7 on 2026-07-16 against these bytes (1 Tim 3:16
«ٱللهُ ظَهَرَ فِي ٱلْجَسَدِ», Comma present, Acts 8:37, Rom 16:24, Joseph
at Lk 2:33, church of God at Acts 20:28, "who is in heaven" at Jn 3:13) —
research report: Hexapla-releases/research/vandyck_report.md. The
vocalization-lineage open question (CrossWire's module credits an NC
tashkeel source) is tracked there + in the eBible provenance email draft;
owner chose to ship on eBible's explicit PD declaration 2026-07-16.

Structure (surveyed 2026-07-16): markers id/h/toc1-3/mt1/c/cl/s1/p/v,
plus Psalms-only: \\d psalm superscriptions (120), \\qa acrostic letter
headings in Ps 119 (22), one empty \\qc, one empty \\nb (Mark 9). No
footnotes, no inline markup, no verse bridges.

  * \\d titles are PREPENDED to the following verse 1, matching the KJV
    asset's inline-title convention («[A Psalm of David...] LORD, how...»).
    convert_tamil_irv.py DROPPED its \\d titles on the incorrect claim
    that the KJV asset drops them too — the Synodal missing-titles defect
    class. Do not copy that SKIP here; Tamil gets its own repair.
  * \\qa acrostic letters are dropped — same owner decision as the
    la_vulgata <Aleph>..<Thau> markers (2026-07-15).
  * \\cl («المزمور الثالث» chapter labels) and \\s1 section heads dropped.
  * Native numbering exceeds the KJV grid in exactly two places, both
    text-verified splits curated in build_versemap.py: 3 Jn 14/15
    (continental split, same as ta/mar) and 1 Tim 6:21 -> 21+22 (the
    grace-benediction numbered separately).

Usage: python convert_vandyck.py <arb-vd_usfm.zip> <dst.json>
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

SKIP = {"h", "toc1", "toc2", "toc3", "mt1", "cl", "s1", "qa", "qc", "ide", "rem"}
CONT = {"p", "nb"}

TERMINAL = tuple(".!؟…»)")


def clean(text):
    text = re.sub(r"\s+", " ", text).strip()
    assert "\\" not in text, text
    return text


def parse_usfm(raw, path):
    """-> (book code, \\toc1 name, {chapter: {verse: text}}, title count)."""
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
        elif marker == "toc1":
            name = rest
        elif marker == "d":
            # Four psalms (56, 57, 59, 88) split their superscription over
            # TWO consecutive \d lines — concatenate, never overwrite.
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
        parsed[code] = chapters
        names[code] = name
        total_titles += titles
    assert sorted(parsed) == sorted(CANON_ORDER), sorted(parsed)

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
    out.write(f"psalm titles prepended: {total_titles}\n")
    out.write(f"empty KJV slots: {len(empty_slots)}\n")
    for s in empty_slots:
        out.write("  " + s + "\n")
    out.write(f"beyond-KJV verses: {len(extras)}\n")
    for s in extras:
        out.write("  " + s + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
