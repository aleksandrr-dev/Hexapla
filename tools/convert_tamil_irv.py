# -*- coding: utf-8 -*-
"""eBible.org tam2017 USFM (Tamil IRV 2019, full Bible) -> app asset format.

Source: https://eBible.org/Scriptures/tam2017_usfm.zip — Indian Revised
Version, Tamil (2019), Bridge Connectivity Solutions, CC BY-SA 4.0
(attribution in sources_text). A light modernization of the TR-based
1871 Bower/Union "Old Version" lineage; deity-verse litmus verified
7/7 on 2026-07-13 (1 Tim 3:16 தேவன், Comma present, Acts 8:37,
Joseph at Lk 2:33, Rom 16:24, church of God at Acts 20:28, "who is
in heaven" at Jn 3:13) — see the session notes in CLAUDE.md.

Output: 83 book slots — 66 canonical books with Tamil \\toc1 names,
apocrypha slots 66-82 empty (English names, byte-identical to the
grc/sa layout). File order inside the zip is NOT canonical (Acts is
file 74); books are placed by their \\id code.

Structure handled (per the 2026-07-13 survey of the zip):
  * skipped whole-line markers: book intros (is1/ip/io1/iot), section
    heads (s1), parallel refs (r), chapter labels (cl), running heads
    (h/toc*/mt1);
  * psalm titles (\\d, 137 in Psalms) are PREPENDED to the following
    verse 1, matching the KJV asset's inline-title convention.
    ⚠ Until 2026-07-16 this converter DROPPED them, on the false claim
    that the KJV asset drops titles too (it carries them inline —
    "[A Psalm of David...] LORD, how..."). That was the same
    missing-superscriptions defect class repaired in ru_synodal and
    cu_elizabeth; found while writing convert_vandyck.py, whose source
    uses the same \\d convention. Asset regenerated same day; diff
    verified to touch ONLY the 137 title verses.
  * continuation markers (q1/q2/q3/m/p/pi1/b) append their text to
    the current verse (poetry lines);
  * inline: \\f...\\f* footnotes removed wholesale (incl. fr/ft/fq/fp
    within), \\wj/\\k markers unwrapped keeping content;
  * the KJV-indexing guard from convert_sanskrit_nt.py: every chapter
    compared against en_kjv.json; KJV verses the source lacks become
    empty "" slots (indexing holds), beyond-KJV verses are reported
    for build_versemap.py curation; verse bridges (\\v N-M) put the
    text at N and empty slots after it, and are reported.

Usage: python convert_tamil_irv.py <tam2017_usfm.zip> <dst.json>
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

SKIP = {"h", "toc1", "toc2", "toc3", "mt1", "cl", "is1", "ip", "io1",
        "iot", "s1", "r", "fp", "rem", "sts"}
CONT = {"q1", "q2", "q3", "m", "p", "pi1", "b", "nb", "li1"}
TERMINAL = tuple(".!?…»)")


def clean(text):
    text = re.sub(r"\\f\s.*?\\f\*", "", text)          # footnotes, wholesale
    text = re.sub(r"\\\+?[a-z]+[0-9]?\s*\*?", " ", text)  # unwrap wj/k etc.
    text = re.sub(r"\s+", " ", text).strip()
    assert "\\" not in text, text
    return text


def parse_usfm(raw, path):
    """-> (book code, \\toc1 name, {chapter: {verse: text}}, [bridge notes])."""
    code = name = None
    chapters, cur, cur_verse = {}, None, None
    bridges = []
    pending_title = None
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
            t = clean(rest)
            if t:
                t = t if t.endswith(TERMINAL) else t + "."
                pending_title = (pending_title + " " + t) if pending_title else t
            cur_verse = None
        elif marker in SKIP:
            cur_verse = None          # heading breaks verse continuation
        elif marker == "c":
            cur = int(rest.split()[0])
            assert cur not in chapters, (path, cur)
            chapters[cur] = {}
            cur_verse = None
            pending_title = None
        elif marker == "v":
            vn, _, text = rest.partition(" ")
            if "-" in vn:             # bridged verses: text at first, rest empty
                lo, hi = (int(x) for x in vn.split("-"))
                bridges.append(f"{code} {cur}:{lo}-{hi}")
                for n in range(lo + 1, hi + 1):
                    chapters[cur][n] = ""
                vn = lo
            else:
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
    return code, name, chapters, bridges


def convert(src_zip, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    kjv = json.load(open(KJV, encoding="utf-8"))
    z = zipfile.ZipFile(src_zip)
    parsed, names, all_bridges = {}, {}, []
    for zn in sorted(z.namelist()):
        if not zn.endswith(".usfm"):
            continue
        code, name, chapters, bridges = parse_usfm(
            z.read(zn).decode("utf-8-sig"), zn)
        parsed[code] = chapters
        names[code] = name
        all_bridges += bridges
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
            # REV 12:17-18 arrives as a bridge whose 18 is empty; 13:1 opens
            # with the sand-of-the-sea sentence, i.e. the edition numbers the
            # continental seam but prints the KJV arrangement (same as the
            # Sanskrit source). Drop the vacuous slot: Revelation stays
            # KJV-shaped.
            if (code, c) == ("REV", 12) and len(verses) == 18 and not verses[17]:
                verses = verses[:17]
                out.write("  dropped vacuous REV 12:18 bridge remainder\n")
            for vn in sorted(vs):
                if vn > kn and verses[vn - 1:vn] != []:
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
    out.write(f"verse bridges: {all_bridges}\n")
    out.write(f"empty KJV slots: {len(empty_slots)}\n")
    for s in empty_slots:
        out.write("  " + s + "\n")
    out.write(f"beyond-KJV verses: {len(extras)}\n")
    for s in extras:
        out.write("  " + s + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
