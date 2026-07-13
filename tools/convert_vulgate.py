# -*- coding: utf-8 -*-
"""Clementine Vulgate (Tweedale/VulSearch 'clemtext') -> app asset format.

Source: Quasimodo.zip from sourceforge.net/projects/vulsearch — the
Clementine Text Project (M. Tweedale et al., 2005), principally from
the Colunga & Turrado 1946 edition, every book proofread twice.
Released into the PUBLIC DOMAIN (acknowledgment requested, given in
sources_text). One .lat file per book, Latin-1, one verse per line
("chapter:verse text"); '/' marks poetry line breaks, trailing '\\'
paragraph ends, '[' ']' paragraphs in poetry — all stripped here. Book display names are the short
Latin titles from data.txt (Genesis, Regum I, Psalmi, Matthæus...).

Layout mirrors the shipped Wycliffe asset (same Vulgate tradition):
native versification kept everywhere (Gallican/LXX psalter with
titles as verse 1, Daniel 14 chapters with the Song of the Three at
3:24-90, Esther 16 chapters with the additions from 10:4); the seven
standalone deuterocanon books go to the apocrypha slots (Tobit,
Judith, Wisdom, Sirach, Baruch incl. the Epistle of Jeremiah as its
native ch. 6, 1-2 Maccabees). The KJV-backbone mapping is handled by
tools/build_versemap.py, not here. Litmus notes (verified 2026-07-13,
research + this converter's output): Comma Johanneum PRESENT, Acts
8:37 PRESENT, Rom 16:24 PRESENT, ecclesiam Dei at Acts 20:28, qui est
in cælo at Jn 3:13; Jerome's own readings at 1 Tim 3:16 ("quod
manifestatum est", no Deus) and Lk 2:33 ("pater ejus") — both already
shipped in this app via Wycliffe, owner-accepted 2026-07-13.

Usage: python convert_vulgate.py <clemtext-source-dir> <dst.json>
"""
import io
import json
import os
import re
import sys

# abbreviation -> app book slot (canonical 0-65, apocrypha 66-82)
SLOTS = {
    "Gn": 0, "Ex": 1, "Lv": 2, "Nm": 3, "Dt": 4, "Jos": 5, "Jdc": 6,
    "Rt": 7, "1Rg": 8, "2Rg": 9, "3Rg": 10, "4Rg": 11, "1Par": 12,
    "2Par": 13, "Esr": 14, "Neh": 15, "Est": 16, "Job": 17, "Ps": 18,
    "Pr": 19, "Ecl": 20, "Ct": 21, "Is": 22, "Jr": 23, "Lam": 24,
    "Ez": 25, "Dn": 26, "Os": 27, "Joel": 28, "Am": 29, "Abd": 30,
    "Jon": 31, "Mch": 32, "Nah": 33, "Hab": 34, "Soph": 35, "Agg": 36,
    "Zach": 37, "Mal": 38,
    "Mt": 39, "Mc": 40, "Lc": 41, "Jo": 42, "Act": 43, "Rom": 44,
    "1Cor": 45, "2Cor": 46, "Gal": 47, "Eph": 48, "Phlp": 49, "Col": 50,
    "1Thes": 51, "2Thes": 52, "1Tim": 53, "2Tim": 54, "Tit": 55,
    "Phlm": 56, "Hbr": 57, "Jac": 58, "1Ptr": 59, "2Ptr": 60, "1Jo": 61,
    "2Jo": 62, "3Jo": 63, "Jud": 64, "Apc": 65,
    # deuterocanon -> apocrypha slots (Baruch's ch. 6 IS the Epistle of
    # Jeremiah, kept native like the Wycliffe asset; slot 73 stays empty)
    "Tob": 68, "Jdt": 69, "Sap": 70, "Sir": 71, "Bar": 72,
    "1Mcc": 75, "2Mcc": 76,
}

# Empty-slot names, matching the other assets.
CANON_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John",
    "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]
APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]


def parse_book(path):
    """-> {chapter: {verse: text}}; strips '/' line breaks and [] marks."""
    chapters = {}
    last = None
    for line in io.open(path, encoding="latin-1"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+):(\d+)\s+(.*)$", line)
        if not m:
            # wrapped continuation of the previous verse (defensive)
            assert last is not None, (path, line)
            chapters[last[0]][last[1]] += " " + line
            continue
        c, v, text = int(m.group(1)), int(m.group(2)), m.group(3)
        chapters.setdefault(c, {})
        assert v not in chapters[c], (path, c, v)
        chapters[c][v] = text
        last = (c, v)
    for c, vs in chapters.items():
        for v in vs:
            t = (vs[v].replace("/", " ").replace("\\", " ")
                 .replace("[", "").replace("]", ""))
            t = re.sub(r"\s+", " ", t).strip()
            assert t, (path, c, v)
            vs[v] = t
    assert sorted(chapters) == list(range(1, len(chapters) + 1)), path
    return chapters


def convert(src, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    names = {}
    for line in io.open(os.path.join(src, "data.txt"), encoding="latin-1"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = line.split("/")
        if f[0] in SLOTS:
            names[f[0]] = f[2]
    assert sorted(names) == sorted(SLOTS), set(SLOTS) ^ set(names)

    books = [{"name": n, "chapters": []} for n in CANON_NAMES + APOC_NAMES]
    total = 0
    for abbr, slot in SLOTS.items():
        chapters = parse_book(os.path.join(src, abbr + ".lat"))
        out_ch = []
        for c in range(1, len(chapters) + 1):
            vs = chapters[c]
            assert sorted(vs) == list(range(1, len(vs) + 1)), (abbr, c)
            out_ch.append([vs[v] for v in range(1, len(vs) + 1)])
            total += len(vs)
        books[slot] = {"name": names[abbr], "chapters": out_ch}
    assert len(books) == 83

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    out.write(f"{dst}: {sum(1 for b in books if b['chapters'])} books, "
              f"{total} verses, {os.path.getsize(dst)} bytes\n")
    # headline shape notes for the versemap pass
    for slot, label in ((18, "Psalms"), (26, "Daniel"), (16, "Esther"), (65, "Revelation")):
        out.write(f"  {label}: {len(books[slot]['chapters'])} chapters\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
