# -*- coding: utf-8 -*-
"""scrollmapper FinBiblia JSON (Biblia 1776, Vanha kirkkoraamattu) -> app asset.

Source: https://raw.githubusercontent.com/scrollmapper/bible_databases/
master/formats/json/FinBiblia.json — a byte-identical re-export of the
CrossWire FinBiblia SWORD module (DistributionLicense=Public Domain; the
finbible.fi digitization, whose own site said PUBLIC DOMAIN — recovered
via Wayback, the site itself is offline). Deity-verse litmus verified 7/7
2026-07-16 — research report: Hexapla-releases/research/biblia1776_report.md.

Handled here (all surveyed 2026-07-16 against these exact bytes):
  * The source is the 83-book KJVA layout (apocrypha BETWEEN the
    testaments) — canon books are selected BY NAME, and the apocrypha is
    EXCLUDED: 5 of its 17 books are 100% empty in the module and several
    others have gaps (see the research report). Empty slots keep the
    app's usual 83-slot shape.
  * 229 native-numbering apparatus fragments "(H n:m)" / "(n:m)" baked
    into verse text in EXACTLY three books — 1 Samuel (22), Job (91),
    Psalms (116) — stripped under a census-match assertion. Supplied
    words use plain (parentheses) WITHOUT digits/colon and are KEPT
    (the house rule: no colon = supplied words).
  * ⚠ 1 Sam 23:29 is a literal "[]" placeholder in the module — the
    compile DROPPED native verse 24:1 entirely. Backfilled with the SAME
    digitization's own text, recovered from finbible.fi via the Wayback
    Machine (kooste/1Samuel/1Samuel_24.htm, snapshot 20210226133437):
    «Biblia1776 29. (H24:1) Ja David meni sieltä ylös ja asui EnGedin
    linnoissa.» The converter asserts the placeholder is still there
    before patching, so an upstream fix cannot be silently overwritten.
  * Native versification exceeds the KJV grid in exactly two places,
    curated in build_versemap.py: 3 Jn 14/15 and Rev 12:18 (real text,
    «Ja minä seisoin meren sannalla») -> 13:1.
  * Book names in the source are ENGLISH; the asset gets standard
    Finnish (Lutheran-tradition) names curated below.

Usage: python convert_biblia1776.py <FinBiblia.json> <dst.json>
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KJV = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "en_kjv.json")

CANON_EN = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "I Samuel", "II Samuel",
    "I Kings", "II Kings", "I Chronicles", "II Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "I Corinthians", "II Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "I Thessalonians", "II Thessalonians",
    "I Timothy", "II Timothy", "Titus", "Philemon", "Hebrews", "James",
    "I Peter", "II Peter", "I John", "II John", "III John", "Jude",
    "Revelation of John",
]

NAMES_FI = [
    "1. Mooseksen kirja", "2. Mooseksen kirja", "3. Mooseksen kirja",
    "4. Mooseksen kirja", "5. Mooseksen kirja",
    "Joosua", "Tuomarien kirja", "Ruut", "1. Samuelin kirja", "2. Samuelin kirja",
    "1. Kuninkaiden kirja", "2. Kuninkaiden kirja", "1. Aikakirja", "2. Aikakirja",
    "Esra", "Nehemia", "Ester", "Job", "Psalmit", "Sananlaskut",
    "Saarnaaja", "Korkea veisu", "Jesaja", "Jeremia", "Valitusvirret",
    "Hesekiel", "Daniel", "Hoosea", "Joel", "Aamos",
    "Obadja", "Joona", "Miika", "Nahum", "Habakuk",
    "Sefanja", "Haggai", "Sakarja", "Malakia",
    "Matteus", "Markus", "Luukas", "Johannes", "Apostolien teot",
    "Roomalaiskirje", "1. Korinttilaiskirje", "2. Korinttilaiskirje",
    "Galatalaiskirje", "Efesolaiskirje", "Filippiläiskirje", "Kolossalaiskirje",
    "1. Tessalonikalaiskirje", "2. Tessalonikalaiskirje", "1. Timoteuskirje",
    "2. Timoteuskirje", "Tituskirje", "Filemonkirje", "Heprealaiskirje",
    "Jaakobin kirje", "1. Pietarin kirje", "2. Pietarin kirje",
    "1. Johanneksen kirje", "2. Johanneksen kirje", "3. Johanneksen kirje",
    "Juudaksen kirje", "Johanneksen ilmestys",
]

APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

APPARATUS = re.compile(r"\s*\(H?\s*\d+:\d+\)\s*")
APPARATUS_BOOKS = {"I Samuel": 22, "Job": 91, "Psalms": 116}

# 1 Sam 23:29 backfill — same digitization, via Wayback (see module docstring).
SAM_23_29 = "Ja David meni sieltä ylös ja asui EnGedin linnoissa."


def convert(src, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    kjv = json.load(open(KJV, encoding="utf-8"))
    data = json.load(open(src, encoding="utf-8"))
    by_name = {b["name"]: b for b in data["books"]}
    missing = [n for n in CANON_EN if n not in by_name]
    assert not missing, missing

    stripped = 0
    stripped_by_book = {}
    books = []
    empty_slots, extras = [], []
    patched = False
    for bi, en in enumerate(CANON_EN):
        src_b = by_name[en]
        kch = kjv[bi]["chapters"]
        assert len(src_b["chapters"]) == len(kch), (en, len(src_b["chapters"]), len(kch))
        out_chapters = []
        for ch in src_b["chapters"]:
            c = ch["chapter"]
            kn = len(kch[c - 1])
            vmax = max(v["verse"] for v in ch["verses"])
            verses = [""] * max(kn, vmax)
            for v in ch["verses"]:
                text = v["text"]
                text, n = APPARATUS.subn(" ", text)
                if n:
                    stripped += n
                    stripped_by_book[en] = stripped_by_book.get(en, 0) + n
                text = re.sub(r"\s+", " ", text).strip()
                if en == "I Samuel" and c == 23 and v["verse"] == 29:
                    assert text == "[]", f"1 Sam 23:29 placeholder changed upstream: {text!r}"
                    text = SAM_23_29
                    patched = True
                assert "[" not in text and "]" not in text, (en, c, v["verse"], text)
                verses[v["verse"] - 1] = text
            for vn in range(1, kn + 1):
                if not verses[vn - 1]:
                    empty_slots.append(f"{en} {c}:{vn} (empty slot)")
            for vn in range(kn + 1, len(verses) + 1):
                if verses[vn - 1]:
                    extras.append(f"{en} {c}:{vn} beyond KJV count {kn} "
                                  f"(native versification -> curate in build_versemap.py)")
            out_chapters.append(verses)
        books.append({"name": NAMES_FI[bi], "chapters": out_chapters})
    assert patched, "1 Sam 23:29 was never seen"
    assert stripped == 229, (stripped, stripped_by_book)
    assert stripped_by_book == APPARATUS_BOOKS, stripped_by_book

    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    filled = sum(1 for b in books for c in b["chapters"] for v in c if v)
    out.write(f"{dst}: 83 book slots (66 canon), {total} verse slots, "
              f"{filled} with text, {os.path.getsize(dst)} bytes\n")
    out.write(f"apparatus stripped: {stripped} {stripped_by_book}\n")
    out.write("1 Sam 23:29 backfilled from the Wayback finbible.fi kooste page\n")
    out.write(f"empty KJV slots: {len(empty_slots)}\n")
    for s in empty_slots:
        out.write("  " + s + "\n")
    out.write(f"beyond-KJV verses: {len(extras)}\n")
    for s in extras:
        out.write("  " + s + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
