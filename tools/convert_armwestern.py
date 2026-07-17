# -*- coding: utf-8 -*-
"""⚠ WORK IN PROGRESS — NOT YET PRODUCING AN ASSET (2026-07-17).
BLOCKED ON: the module's "Versification=KJV" is a FORCE-FIT hiding 10
squeeze sites (the DutSVV defect class; the research pass verified the
scheme's structure, not content alignment). Scan results (scratchpad
arm_empty.py): empty slots at Mt 17:27, Mk 9:50, Acts 7:60, Acts 14:28,
Acts 19:41, 2 Cor 2:1, 2 Cor 6:1, 2 Cor 13:14, 1 Thess 4:18, Heb 13:25 —
each chapter's TAIL content is shifted (e.g. the fish-coin verse KJV
Mt 17:27 sits at label 26), i.e. the 1853's native numbering was
squeezed into KJV slots with a trailing empty. RESUME PLAN: for each of
the 10 chapters, locate the true native merge/seam by reading the
Armenian against the KJV, restore NATIVE numbering (dense, no empties),
and curate versemap runs — the srb/kar/bkr discipline. ~10 sites, one
careful session. No asset shipped from this converter yet.

CrossWire ArmWestern SWORD module (Western Armenian NT, 1853) -> app asset.

Source: https://www.crosswire.org/ftpmirror/pub/sword/packages/rawzip/
ArmWestern.zip — .conf DistributionLicense=Public Domain (quoted in the
research report). The 1853 Constantinople Western Armenian New
Testament; litmus 7/7 with zero deviations, and zero versification
mismatches against the KJV grid across all 260 NT chapters (both
verified in the research pass and re-asserted here). Research report:
Hexapla-releases/research/armenian_report.md.

NT-only (grc/sa_nt precedent): OT slots 0-38 stay empty with English
names, apocrypha slots 66-82 empty. NT book names in classical Armenian
forms appropriate to the 1853 edition.

Read via pysword (MIT, dev-only dependency — not bundled with the app).

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


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text)
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
    structure = bible.get_structure()
    nt_books = structure.get_books()["nt"]
    assert len(nt_books) == 27, len(nt_books)

    books = [{"name": n, "chapters": []} for n in OT_NAMES]
    total = 0
    for i, book in enumerate(nt_books):
        bi = 39 + i
        kch = kjv[bi]["chapters"]
        assert book.num_chapters == len(kch), (book.name, book.num_chapters, len(kch))
        chapters = []
        for c in range(1, book.num_chapters + 1):
            kn = len(kch[c - 1])
            verses = []
            for v in range(1, kn + 1):
                t = clean(bible.get(books=[book.name], chapters=[c], verses=[v]))
                assert t, (book.name, c, v, "empty verse")
                verses.append(t)
            # the module must not have MORE verses than the KJV grid
            try:
                extra = bible.get(books=[book.name], chapters=[c], verses=[kn + 1])
            except Exception:
                extra = ""
            assert not clean(extra or ""), (book.name, c, "extra verse beyond KJV")
            total += kn
            chapters.append(verses)
        books.append({"name": NT_NAMES_HY[i], "chapters": chapters})
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    out.write(f"{dst}: 83 book slots (27 NT filled), {total} verses, "
              f"{os.path.getsize(dst)} bytes\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
