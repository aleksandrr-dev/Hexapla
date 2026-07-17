# -*- coding: utf-8 -*-
"""CrossWire ArmWestern SWORD module (Western Armenian NT, 1853) -> app asset.

Source: https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/
ArmWestern.zip — .conf DistributionLicense=Public Domain. Litmus 7/7
with zero deviations (research report:
Hexapla-releases/research/armenian_report.md; re-verified on the
converted asset). NT-only (grc/sa_nt precedent): OT and apocrypha slots
empty. Read via pysword (MIT, dev-only dependency).

⚠ The module's "Versification=KJV" is a FORCE-FIT. The full seam
analysis (2026-07-17 session; scripts arm_*.py in the session
scratchpad) found and resolved:

  * NATIVE MERGES (the 1853's own numbering, kept + versemap-curated):
    Mt 17:14=KJV 14+15 (native ch = 26); Acts 7:55=KJV 55+56 and
    7:59=KJV 60+8:1a (classical Armenian chapter seam; native ch = 59);
    Acts 14:6=KJV 6+7; Acts 19:40=KJV 40+41; 2 Cor 13:12=KJV 12+13;
    1 Thess 4:11=KJV 11+12; Heb 13:24=KJV 24+25; Lk 4:44=KJV 43+44
    (native also SPLITS KJV 4:38 across 38/39 — count-preserving, the
    module carries it faithfully); Jn 6:71=KJV 70+71 (native splits
    KJV 6:51 across 51/52); Jn 10:42=KJV 41b+42.
    The trailing EMPTY slots the force-fit left (Mt 17:27, Mk 9:50,
    Acts 7:60/14:28/19:41, 2 Cor 13:14, 1 Th 4:18, Heb 13:25) are
    dropped — native chapters are shorter.
  * ONE MODULE SQUEEZE restored by splitting: native Mk 8 has 39 verses
    (its v39 = KJV 9:1, the classical chapter boundary) but the KJV
    scheme caps Mk 8 at 38, so the compile fused 38+39. Split here at
    the unambiguous sentence boundary («...հրեշտակներուն հետ»: ||
    Եւ ըսաւ անոնց...), verified against KJV 8:38/9:1.
  * FIVE self-duplicated verses (module data bug — text repeated
    verbatim): Acts 7:59, 14:6, 19:40, 1 Th 4:11, Heb 13:24. Deduped
    under an exact-half assertion.
  * TWO verses ABSENT from the module entirely: 2 Cor 2:1 and 6:1
    (whole-NT phrase sweep confirmed). PATCHED with the 1853 edition's
    own wording (PD by age), transcribed from the WARMB digitization of
    the 1853 (bible.com/versions/1987; an archive.org scan of the print
    exists: TheHolyBibleInArmenianWestern1853NT). Content matches KJV
    exactly. NOTE: the patches carry the 1853's classic register
    («Վասն զի») while the module's language reads more modernized —
    an open observation about the module's true edition, recorded here
    and in CLAUDE.md for future review.

Usage: python convert_armwestern.py <ArmWestern.zip> <dst.json>
"""
import io
import json
import os
import re
import sys

from pysword.modules import SwordModules

OT_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
]

NT_NAMES_HY = [
    "Մատթէոս", "Մարկոս", "Ղուկաս", "Յովհաննէս", "Գործք Առաքելոց",
    "Առ Հռովմայեցիս", "Առ Կորնթացիս Ա", "Առ Կորնթացիս Բ",
    "Առ Գաղատացիս", "Առ Եփեսացիս", "Առ Փիլիպպեցիս", "Առ Կողոսացիս",
    "Առ Թեսաղոնիկեցիս Ա", "Առ Թեսաղոնիկեցիս Բ", "Առ Տիմոթէոս Ա",
    "Առ Տիմոթէոս Բ", "Առ Տիտոս", "Առ Փիլիմոն", "Առ Եբրայեցիս",
    "Յակոբոս", "Պետրոս Ա", "Պետրոս Բ", "Յովհաննէս Ա", "Յովհաննէս Բ",
    "Յովհաննէս Գ", "Յուդա", "Յայտնութիւն",
]

APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

# module book name -> (canon index, expected KJV-slot squeeze empties)
DEDUPE = {("Acts", 7, 59), ("Acts", 14, 6), ("Acts", 19, 40),
          ("I Thessalonians", 4, 11), ("Hebrews", 13, 24)}
DROP_EMPTY_TAIL = {("Matthew", 17), ("Mark", 9), ("Acts", 7), ("Acts", 14),
                   ("Acts", 19), ("II Corinthians", 13),
                   ("I Thessalonians", 4), ("Hebrews", 13)}
# 2 Cor 2:1 and 6:1 — absent from the module; the 1853's own wording.
PATCHES = {
    ("II Corinthians", 2, 1):
        "Սակայն ես ինծմէ որոշեցի, որ նորէն տրտմութիւնով չգամ ձեզի։",
    ("II Corinthians", 6, 1):
        "Ուստի մենք ալ գործակից ըլլալով՝ կաղաչենք որ Աստուծոյ շնորհքը "
        "պարապ տեղ ընդունած չըլլաք։",
}
MK8_SPLIT = "Եւ ըսաւ անոնց"     # native Mk 8:39 (= KJV 9:1) begins here


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def convert(src_zip, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    kjv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "app", "src", "main", "assets", "bibles", "en_kjv.json")
    kjv = json.load(open(kjv_path, encoding="utf-8"))

    modules = SwordModules(src_zip)
    found = modules.parse_modules()
    assert "ArmWestern" in found, found.keys()
    bible = modules.get_bible_from_module("ArmWestern")
    nt_books = bible.get_structure().get_books()["nt"]
    assert len(nt_books) == 27, len(nt_books)

    deduped, patched, split_done = 0, 0, False
    books = [{"name": n, "chapters": []} for n in OT_NAMES]
    total = 0
    for i, book in enumerate(nt_books):
        bi = 39 + i
        kch = kjv[bi]["chapters"]
        assert book.num_chapters == len(kch), (book.name, book.num_chapters)
        chapters = []
        for c in range(1, book.num_chapters + 1):
            kn = len(kch[c - 1])
            verses = []
            for v in range(1, kn + 1):
                t = clean(bible.get(books=[book.name], chapters=[c], verses=[v]))
                if (book.name, c, v) in DEDUPE:
                    h = len(t) // 2
                    a, b = t[:h].strip(), t[h:].strip()
                    if a != b:  # odd-length middle char
                        a, b = t[:h + 1].strip(), t[h + 1:].strip()
                    assert a == b, (book.name, c, v, "not an exact duplication")
                    t = a
                    deduped += 1
                if not t and (book.name, c, v) in PATCHES:
                    t = PATCHES[(book.name, c, v)]
                    patched += 1
                if not t:
                    assert (book.name, c) in DROP_EMPTY_TAIL and v == kn, \
                        (book.name, c, v, "unexpected empty")
                    continue    # native chapter is shorter — drop the slot
                verses.append(t)
            if book.name == "Mark" and c == 8:
                last = verses[-1]
                idx = last.rindex(MK8_SPLIT)
                assert idx > 0, "Mk 8:38/39 split anchor missing"
                verses[-1] = last[:idx].strip()
                verses.append(last[idx:].strip())
                split_done = True
            total += len(verses)
            chapters.append(verses)
        books.append({"name": NT_NAMES_HY[i], "chapters": chapters})
    assert deduped == 5 and patched == 2 and split_done, (deduped, patched, split_done)
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83
    assert all(v for b in books for ch in b["chapters"] for v in ch)

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    out.write(f"{dst}: 83 book slots (27 NT filled), {total} verses "
              f"(native numbering, versemap pivots), {os.path.getsize(dst)} bytes\n")
    out.write(f"deduped: {deduped}, patched: {patched}, Mk 8:38/39 split: {split_done}\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
