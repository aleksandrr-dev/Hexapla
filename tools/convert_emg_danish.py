"""emg Danish OSIS (OT 1871 + NT 1819, Ulrik Sandborg-Petersen, PD) ->
app asset da_1819.json, remapped from native continental numbering to
KJV versification (2026-07-11; replaces the defective Beblia-derived
asset that had 16 "*** POSSIBLE ERROR ***" placeholders and missing
verses at continental chapter boundaries).

Sources:
  https://github.com/emg/Danish-Bible-OT-1871 (OSIS/DA_OT1871.OSIS.xml)
  https://github.com/emg/Danish-Bible-NT-1819 (OSIS/DA_NT1819.OSIS.xml)
"NT total exactly matches KJV; text complete and vigorously proofread."

Remap rules (each verified against the actual text, see comments):
  1. Psalm titles: continental counts the title as v1 (v1-2 for long
     titles) — merged into the first content verse, KJV-style, matching
     how the rest of the app's assets (and the KJV itself) carry titles.
  2. Books where only chapter BOUNDARIES differ (Gen 42/43, Lev 5/6,
     Num 29/30, Job 38-41, Eccl 4/5, Hos, Joel 2/3, Jonah 1/2, Mic 4/5,
     Nah 1/2, Zech 1/2, Dan 5/6, 1 Sam 23/24): the book's verse sequence
     is identical, so it is re-split by the KJV chapter sizes.
  3. Continental verse splits (two verses = one KJV verse) -> merge:
     1 Sam 20:42-43, 1 Kgs 22:43-44, John 1:38-39, 3 John 14-15.
  4. Continental verse merges (one verse = two KJV verses) -> split at
     curated boundaries: Isa 63:19, Dan 10:18, Acts 4:36, Acts 19:40,
     2 Cor 13:12.
  5. Rev 12:18 ("Og jeg stod paa Havets Sand.") -> prepended to 13:1,
     where the KJV carries that sentence.

Usage: python convert_emg_danish.py <DA_OT1871.OSIS.xml> <DA_NT1819.OSIS.xml>
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "da_1819.json")
KJV = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "en_kjv.json")

OSIS_BOOKS = ["Gen","Exod","Lev","Num","Deut","Josh","Judg","Ruth","1Sam","2Sam",
    "1Kgs","2Kgs","1Chr","2Chr","Ezra","Neh","Esth","Job","Ps","Prov","Eccl",
    "Song","Isa","Jer","Lam","Ezek","Dan","Hos","Joel","Amos","Obad","Jonah",
    "Mic","Nah","Hab","Zeph","Hag","Zech","Mal",
    "Matt","Mark","Luke","John","Acts","Rom","1Cor","2Cor","Gal","Eph","Phil",
    "Col","1Thess","2Thess","1Tim","2Tim","Titus","Phlm","Heb","Jas","1Pet",
    "2Pet","1John","2John","3John","Jude","Rev"]

sys.path.insert(0, HERE)
from convert_beblia import NAMES

# (book, chapter, verse) pairs to merge with the following verse.
MERGES = [("1Sam", 20, 42), ("1Kgs", 22, 43), ("John", 1, 38), ("3John", 1, 14)]

# (book, chapter, verse, split marker): text from the marker onward
# becomes the next verse. Markers verified against the emg text.
SPLITS = [
    ("Isa", 63, 19, "gid du vilde sønderrive Himlene"),
    ("Dan", 10, 18, "og han sagde: Frygt ikke, du højlig elskede Mand!"),
    ("Acts", 4, 36, "solgte en Ager,"),
    ("Acts", 19, 40, "Og der han dette havde sagt,"),
    ("2Cor", 13, 12, "Alle de Hellige hilse Eder."),
]

# Rare OCR defects in the emg transcription, verified by eye.
TYPOS = {"Rong Nebukadnezar": "Kong Nebukadnezar"}

VERSE = re.compile(r'<verse osisID="([^".]+)\.(\d+)\.(\d+)" sID="[^"]*"/>(.*?)<verse eID=', re.S)
NOTE = re.compile(r"<note\b[^>]*>.*?</note>", re.S)
TAGS = re.compile(r"<[^>]+>")


def parse(path):
    raw = NOTE.sub("", open(path, encoding="utf-8").read())
    out = {}
    for book, c, v, text in VERSE.findall(raw):
        text = re.sub(r"\s+", " ", TAGS.sub("", text)).strip()
        for bad, good in TYPOS.items():
            text = text.replace(bad, good)
        out.setdefault(book, {}).setdefault(int(c), {})[int(v)] = text
    return out


def main(ot_path, nt_path):
    da = parse(ot_path)
    da.update(parse(nt_path))
    kjv = json.load(open(KJV, encoding="utf-8"))
    assert len(da) == 66

    # dict -> ordered lists
    text = {b: [[chs[c][v] for v in sorted(chs[c])] for c in sorted(chs)]
            for b, chs in da.items()}

    # 5. Rev 12:18 -> 13:1 (before anything else)
    rev = text["Rev"]
    assert rev[11][17].startswith("Og jeg stod paa Havets Sand")
    rev[12][0] = rev[11][17] + " " + rev[12][0]
    del rev[11][17]

    # 3. merges
    for book, c, v in MERGES:
        ch = text[book][c - 1]
        ch[v - 1] = ch[v - 1] + " " + ch[v]
        del ch[v]

    # 4. splits
    for book, c, v, marker in SPLITS:
        ch = text[book][c - 1]
        t = ch[v - 1]
        i = t.index(marker)  # raises if the source text changed
        ch[v - 1: v] = [t[:i].rstrip(), t[i:]]

    # 1. Psalm titles into the first content verse
    kj_ps = [len(c) for c in kjv[18]["chapters"]]
    for ci, ch in enumerate(text["Ps"]):
        extra = len(ch) - kj_ps[ci]
        assert extra in (0, 1, 2), (ci + 1, extra)
        if extra:
            text["Ps"][ci] = [" ".join(ch[: extra + 1])] + ch[extra + 1:]

    # 2. re-split books whose sequence matches but boundaries differ
    books = []
    for bi, code in enumerate(OSIS_BOOKS):
        want = [len(c) for c in kjv[bi]["chapters"]]
        have = [len(c) for c in text[code]]
        if have != want:
            flat = [v for ch in text[code] for v in ch]
            assert len(flat) == sum(want), (code, len(flat), sum(want))
            out, i = [], 0
            for n in want:
                out.append(flat[i:i + n])
                i += n
            text[code] = out
        books.append({"name": NAMES["da"][bi], "chapters": text[code]})

    # final gates
    for bi in range(66):
        assert [len(c) for c in books[bi]["chapters"]] == \
               [len(c) for c in kjv[bi]["chapters"]], OSIS_BOOKS[bi]
        for ch in books[bi]["chapters"]:
            for v in ch:
                assert v.strip(), (OSIS_BOOKS[bi], "empty verse")
                assert "POSSIBLE ERROR" not in v
    total = sum(len(c) for b in books for c in b["chapters"])
    assert total == 31102, total

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"da_1819.json rebuilt: 66 books, {total} verses, KJV-versified")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
