"""eBible.org sandev USFM (Sanskrit NT, Devanagari) -> app asset format.

Source: https://eBible.org/Scriptures/sandev_usfm.zip — the 1851
Calcutta Baptist Missionaries NT (Yates/Wenger revision), digitized by
SanskritBible.in (2018), CC BY-SA 4.0 (attribution in sources_text).

Output matches grc_byz.json's NT-only shape exactly: 83 book slots —
OT slots 0-38 present but empty (English names, "chapters": []), NT in
slots 39-65 with Devanagari names taken from the source's \toc1
headers, apocrypha slots 66-82 empty.

KJV-indexing guard (the convert_beblia.py lesson: compare per-chapter
verse counts against en_kjv.json and inspect every divergence BEFORE
shipping): every chapter is checked here, in this converter. A TR
verse the source omitted would be emitted as an empty "" slot so KJV
indexing holds — this corpus omits NONE (Acts 8:37, Luke 17:36, Acts
15:34, Rom 16:24 are all present, verified 2026-07-11). The two real
divergences, both reported by the run:
  * 3 John 14/15 continental split — kept native (15 verses), curated
    in build_versemap.py under ("san",) like gen1599/alm/cus/cuv.
  * Rev 12:18 exists in the source only as a literal "[]" placeholder;
    the edition numbers the continental seam but prints the KJV
    arrangement ("I stood upon the sand of the sea" opens 13:1), so
    the empty placeholder is dropped and Revelation is KJV-shaped.

Usage: python convert_sanskrit_nt.py <usfm-dir> <dst.json>
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KJV = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "en_kjv.json")

NT_ORDER = [
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL", "EPH",
    "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM", "HEB", "JAS",
    "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
]

# Empty-slot names, byte-identical to grc_byz.json's.
OT_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi",
]
APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

KNOWN_MARKERS = {"id", "h", "toc1", "toc2", "toc3", "mt1", "c", "p", "v"}
# The source's numbered-but-empty continental seam (content is in 13:1).
DROP_PLACEHOLDERS = {("REV", 12, 18)}


def parse_usfm(path):
    """-> (book code, \\toc1 name, {chapter: {verse: text}})."""
    code = name = None
    chapters, cur = {}, None
    cur_verse = None
    for line in open(path, encoding="utf-8-sig"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"\\([a-z0-9]+)\s*(.*)$", line)
        if not m:
            # bare continuation line of the current verse (none in sandev)
            assert cur_verse is not None, (path, line)
            chapters[cur][cur_verse] += " " + line
            continue
        marker, rest = m.group(1), m.group(2).strip()
        assert marker in KNOWN_MARKERS, (path, marker)
        if marker == "id":
            code = rest.split()[0]
        elif marker == "toc1":
            name = rest
        elif marker == "c":
            cur = int(rest)
            assert cur not in chapters, (path, cur)
            chapters[cur] = {}
            cur_verse = None
        elif marker == "v":
            vn, _, text = rest.partition(" ")
            vn = int(vn)
            text = text.strip()
            assert vn not in chapters[cur], (path, cur, vn)
            if (code, cur, vn) in DROP_PLACEHOLDERS:
                assert text == "[]", (code, cur, vn, text)
                print(f"  dropped placeholder {code} {cur}:{vn} (text {text!r})")
                continue
            assert text, (path, cur, vn)
            assert "POSSIBLE ERROR" not in text
            assert not any(ch in text for ch in "\\{}<>[]*"), (path, cur, vn, text)
            chapters[cur][vn] = text
            cur_verse = vn
    assert code and name and chapters, path
    assert sorted(chapters) == list(range(1, len(chapters) + 1)), (path, sorted(chapters))
    return code, name, chapters


def convert(src_dir, dst):
    kjv = json.load(open(KJV, encoding="utf-8"))
    parsed = {}
    names = {}
    for path in sorted(glob.glob(os.path.join(src_dir, "*.usfm"))):
        code, name, chapters = parse_usfm(path)
        parsed[code] = chapters
        names[code] = name
    assert sorted(parsed) == sorted(NT_ORDER), sorted(parsed)

    books = [{"name": n, "chapters": []} for n in OT_NAMES]
    empty_slots, extras = [], []
    for bi, code in enumerate(NT_ORDER, start=39):
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
                if vn not in vs:
                    empty_slots.append(f"{code} {c}:{vn} (KJV verse absent from source -> empty slot)")
            for vn in sorted(vs):
                if vn > kn:
                    extras.append(f"{code} {c}:{vn} beyond KJV count {kn} (native versification -> curate in build_versemap.py)")
            out_chapters.append(verses)
        books.append({"name": names[code], "chapters": out_chapters})
    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    filled = sum(1 for b in books for c in b["chapters"] for v in c if v)
    print(f"{dst}: 83 book slots (27 NT), {total} verse slots, {filled} with text, "
          f"{os.path.getsize(dst)} bytes")
    print(f"empty KJV slots: {len(empty_slots)}")
    for s in empty_slots:
        print(" ", s)
    print(f"beyond-KJV verses: {len(extras)}")
    for s in extras:
        print(" ", s)


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
