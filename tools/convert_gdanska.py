# -*- coding: utf-8 -*-
"""gratis-bible poland.xml (Biblia Gdańska, 1632/1881 lineage, OSIS) +
scrollmapper PolGdanska.json (CrossWire module re-export) -> app asset.

Both sources are Public Domain (gratis-bible <rights>; CrossWire .conf
DistributionLicense=Public Domain) and carry the SAME wording — two
containers of one 1881-lineage digitization. Litmus 6/7 verified
2026-07-16 (Lk 2:33 "ojciec" = the pre-1881 Luther-class reading the
owner accepts); research report:
Hexapla-releases/research/gdanska_report.md. ⚠ The modernized UBG is
BLOCKED (CC BY-ND per eBible AND NC per CrossWire) — never source it.

Why two sources (every claim below verified against the bytes 2026-07-16):

poland.xml is PRIMARY — its Psalter keeps titles correctly and 95% of
chapters sit on the KJV grid with native numbers as inline "N.N " text
fragments (stripped here under a census assertion). But it has real
defects, each handled explicitly:
  * 1-2 Chronicles is structurally broken. The div after 2 Kings is a
    per-chapter UNION of 2 Chr and 1 Chr (2 Chr verses shadow 1 Chr at
    shared coordinates; only 1 Chr's overflow survives); the NEXT div is
    a COMPLETE, correct 2 Chronicles (822 verses); a truncated real
    1 Chronicles (1:1 "Adam, Set, Enos" through 16:5, which it cuts
    MID-VERSE) sits after Revelation.
    => 2 Chr from the complete div; 1 Chr chapters 1-15 from the
    trailing fragment, chapter 16 onward from the MODULE (the fragment's
    complete 16:1-4 byte-match the module — the boundary witness). The
    module's own
    1 Chr 7 has a squeeze defect (empty 7:40, content shifted) — dodged,
    because ch7 comes from the fragment; the module portion is verified
    verse-by-verse against poland's surviving overflow witnesses.
  * FOUR damaged chapters, proven drops (module has the text, KJV
    agrees): Deut 5 (KJV v22 "These words the LORD spake" missing —
    the survivor sits at id 22 with id 23 skipped), Ps 105 (v15 "Touch
    not mine anointed" missing), Ps 107 (KJV 28-29 missing AND 30/31
    swapped), Ezek 17 (v1 "the word of the LORD came" missing).
    => whole-chapter overrides from the module (all four are untitled
    psalms/prose, so the module's title-squeeze cannot bite; each
    module chapter verified dense + KJV-count + correct content).
  * Ps 42 has GAPPED verse ids (…9, 12, 13) around correct KJV-shaped
    content => dense repack by document order (11 verses, KJV grid).
  * The module's Psalter is NEVER used outside the three overrides: its
    compile gives psalm titles their own slot and silently merges each
    titled psalm's tail (confirmed at Ps 3) — the DutSVV defect class.

True NATIVE features (1.0 similarity: poland's verse == module's two
verses joined) are KEPT and curated in build_versemap.py, not patched:
3 Jn/Rev 12:18 tails are pre-merged by the source itself; Lev 24:23
split; Num 29:40=30:1 chapter seam; 1 Sam 20:42 split; Ps 51/52/54/60
superscriptions as their own verse 1 (like the Synodal); Ps 146:1-2,
Jer 29:31-32, Acts 19:40-41, 2 Cor 11:32-33, 2 Cor 13:13-14,
Gal 1:23-24 merges.

Usage: python convert_gdanska.py <poland.xml> <PolGdanska.json> <dst.json>
"""
import io
import json
import os
import re
import sys
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
KJV = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "en_kjv.json")

OSIS_ORDER = [
    "Gen", "Exod", "Lev", "Num", "Deut", "Josh", "Judg", "Ruth", "1Sam", "2Sam",
    "1Kgs", "2Kgs", "1Chr", "2Chr", "Ezra", "Neh", "Esth", "Job", "Ps", "Prov",
    "Eccl", "Song", "Isa", "Jer", "Lam", "Ezek", "Dan", "Hos", "Joel", "Amos",
    "Obad", "Jonah", "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
    "Matt", "Mark", "Luke", "John", "Acts", "Rom", "1Cor", "2Cor", "Gal", "Eph",
    "Phil", "Col", "1Thess", "2Thess", "1Tim", "2Tim", "Titus", "Phlm", "Heb",
    "Jas", "1Pet", "2Pet", "1John", "2John", "3John", "Jude", "Rev",
]

MODULE_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "I Samuel", "II Samuel", "I Kings", "II Kings",
    "I Chronicles", "II Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "I Corinthians", "II Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "I Thessalonians", "II Thessalonians",
    "I Timothy", "II Timothy", "Titus", "Philemon", "Hebrews", "James",
    "I Peter", "II Peter", "I John", "II John", "III John", "Jude",
    "Revelation of John",
]

NAMES_PL = [
    "1 Mojżeszowa", "2 Mojżeszowa", "3 Mojżeszowa", "4 Mojżeszowa",
    "5 Mojżeszowa", "Jozue", "Sędziów", "Ruty", "1 Samuelowa", "2 Samuelowa",
    "1 Królewska", "2 Królewska", "1 Kronik", "2 Kronik", "Ezdrasz",
    "Nehemijasz", "Estery", "Ijob", "Psalmy", "Przypowieści Salomonowe",
    "Kaznodzieja Salomonowy", "Pieśń Salomonowa", "Izajasz", "Jeremijasz",
    "Treny Jeremijaszowe", "Ezechyjel", "Danijel", "Ozeasz", "Joel", "Amos",
    "Abdyjasz", "Jonasz", "Micheasz", "Nahum", "Abakuk", "Sofonijasz",
    "Aggieusz", "Zacharyjasz", "Malachyjasz",
    "Mateusz", "Marek", "Łukasz", "Jan", "Dzieje Apostolskie", "Rzymian",
    "1 Koryntów", "2 Koryntów", "Galatów", "Efezów", "Filipensów",
    "Kolosensów", "1 Tesalonicensów", "2 Tesalonicensów", "1 Tymoteusza",
    "2 Tymoteusza", "Tytus", "Filemon", "Żydów", "Jakób", "1 Piotr",
    "2 Piotr", "1 Jan", "2 Jan", "3 Jan", "Judasz", "Objawienie Jana",
]

APOC_NAMES = [
    "1 Esdras", "2 Esdras", "Tobit", "Judith", "Wisdom of Solomon",
    "Sirach", "Baruch", "Epistle of Jeremiah", "Prayer of Manasses",
    "1 Maccabees", "2 Maccabees", "3 Maccabees", "Additions to Esther",
    "Prayer of Azariah", "Susanna", "Bel and the Dragon", "Laodiceans",
]

MARKER = re.compile(r"\s*\b\d{1,3}\.\d{1,3}\s+")
MODULE_CHAPTER_OVERRIDES = [(4, 5), (18, 105), (18, 107), (25, 17)]   # proven drops
# (book, chapter) whose count is ALLOWED to differ from KJV — every one
# individually text-verified and curated in build_versemap.py.
NATIVE_DIVERGENT = {
    (2, 24), (3, 29), (3, 30), (8, 20),
    (18, 51), (18, 52), (18, 54), (18, 60), (18, 146),
    (23, 29), (43, 19), (46, 11), (46, 13), (47, 1),
}


def clean(text):
    global stripped_markers
    text, n = MARKER.subn(" ", " " + text)
    stripped_markers += n
    # poland.xml carries 8 stray escaped brackets (e.g. 1 Kgs 22:45 opens
    # "&gt; A inne sprawy...") — XML-escape debris, not content. Only
    # gt/lt are dropped; other entities would be real characters and
    # audit_asset_markup.py would flag any that slip through.
    text = re.sub(r"&(gt|lt);", " ", text)
    return re.sub(r"\s+", " ", text).strip()


stripped_markers = 0


def sim(a, b):
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def convert(poland_path, module_path, dst):
    out = io.open(1, "w", encoding="utf-8", closefd=False)
    kjv = json.load(open(KJV, encoding="utf-8"))
    raw = open(poland_path, encoding="utf-8").read()
    mod = json.load(open(module_path, encoding="utf-8"))
    mod_books = {b["name"]: b for b in mod["books"]}

    def module_chapter(bi, c):
        ch = mod_books[MODULE_NAMES[bi]]["chapters"][c - 1]["verses"]
        vs = {v["verse"]: re.sub(r"\s+", " ", v["text"]).strip() for v in ch}
        assert all(vs.get(v) for v in range(1, max(vs) + 1)), (bi, c)
        return [vs[v] for v in range(1, max(vs) + 1)]

    # --- div spans ---
    spans = [(m.start(), m.group(1)) for m in re.finditer(r"<div type='book' osisID='([^']+)'", raw)]
    spans.append((len(raw), "END"))
    bodies = [raw[spans[i][0]:spans[i + 1][0]] for i in range(len(spans) - 1)]
    div_ids = [s[1] for s in spans[:-1]]
    assert div_ids[12] == div_ids[13] == "2Chr" and div_ids[66] == "1Chr", div_ids

    def parse_body(body):
        ch = {}
        for m in re.finditer(r"<verse osisID='[^.]+\.(\d+)\.(\d+)'[^>]*>(.*?)</verse>", body, re.S):
            c, v = int(m.group(1)), int(m.group(2))
            ch.setdefault(c, {}).setdefault(v, clean(m.group(3)))
        return ch

    # --- assemble 1 Chronicles: fragment (1..16:5) + module (16:6..29) ---
    frag = parse_body(bodies[66])
    assert frag[1][1].startswith("Adam, Set"), frag[1][1][:40]
    union = parse_body(bodies[12])       # 2Chr-shadowed union, for witnesses
    k1 = kjv[12]["chapters"]
    chr1 = []
    witness_checks = witness_low = 0
    for c in range(1, 30):
        kn = len(k1[c - 1])
        if c <= 15:
            vs = frag[c]
            assert sorted(vs) == list(range(1, kn + 1)), ("frag 1Chr", c, sorted(vs)[-3:])
            chr1.append([vs[v] for v in range(1, kn + 1)])
        else:
            mch = module_chapter(12, c)
            assert len(mch) == kn, ("module 1Chr", c, len(mch), kn)
            if c == 16:
                # The fragment ends MID-VERSE at 16:5 («...Zachary» cut
                # mid-name), so the module takes over from 16:5; the four
                # complete boundary verses must agree between the sources.
                for v in range(1, 5):
                    assert sim(frag[16][v], mch[v - 1]) > 0.9, ("1Chr 16", v)
                assert mch[4].startswith(frag[16][5][:30]), "1Chr 16:5 prefix"
            # verify module against poland's surviving overflow witnesses
            k2n = len(kjv[13]["chapters"][c - 1]) if c <= 36 else 0
            for v, t in union.get(c, {}).items():
                if v > k2n:              # beyond 2 Chr's range => 1 Chr witness
                    witness_checks += 1
                    if sim(t, mch[v - 1]) < 0.9:
                        witness_low += 1
                        out.write(f"  LOW WITNESS 1Chr {c}:{v}\n")
            chr1.append(mch)
    assert witness_checks >= 50 and witness_low == 0, (witness_checks, witness_low)
    out.write(f"1 Chr module portion verified against {witness_checks} poland overflow witnesses\n")

    # --- assemble all books ---
    books = []
    for bi, code in enumerate(OSIS_ORDER):
        kch = kjv[bi]["chapters"]
        if bi == 12:
            books.append({"name": NAMES_PL[bi], "chapters": chr1})
            continue
        # div index == canonical index throughout: divs 0-11 are Gen..2Kgs,
        # div 12 is the union (handled above as 1 Chr), div 13 is the
        # complete 2 Chronicles, divs 14-65 are Ezra..Revelation, div 66
        # is the trailing 1 Chr fragment (consumed above).
        parsed = parse_body(bodies[bi])
        assert len(parsed) == len(kch), (code, len(parsed), len(kch))
        chapters = []
        for c in range(1, len(kch) + 1):
            kn = len(kch[c - 1])
            if (bi, c) in [(o[0], o[1]) for o in MODULE_CHAPTER_OVERRIDES]:
                mch = module_chapter(bi, c)
                assert len(mch) == kn, (code, c)
                chapters.append(mch)
                continue
            vs = parsed[c]
            ids = sorted(vs)
            if bi == 18 and c == 42:               # gapped ids -> dense repack
                assert len(ids) == kn, ("Ps42", ids)
                chapters.append([vs[i] for i in ids])
                continue
            if ids != list(range(1, len(ids) + 1)):
                raise AssertionError((code, c, "non-dense ids", ids[-3:]))
            if len(ids) != kn:
                assert (bi, c) in NATIVE_DIVERGENT, (code, c, len(ids), kn)
            chapters.append([vs[v] for v in ids])
        books.append({"name": NAMES_PL[bi], "chapters": chapters})

    books += [{"name": n, "chapters": []} for n in APOC_NAMES]
    assert len(books) == 83
    empty = [(b["name"], ci + 1, vi + 1) for b in books[:66]
             for ci, ch in enumerate(b["chapters"]) for vi, v in enumerate(ch) if not v]
    assert not empty, empty[:5]
    leftover = [(b["name"], ci + 1, vi + 1) for b in books[:66]
                for ci, ch in enumerate(b["chapters"]) for vi, v in enumerate(ch)
                if MARKER.search(" " + v)]
    assert not leftover, leftover[:5]

    with open(dst, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    total = sum(len(c) for b in books for c in b["chapters"])
    out.write(f"{dst}: 83 book slots (66 canon), {total} verse slots, "
              f"{os.path.getsize(dst)} bytes\n")
    out.write(f"markers stripped: {stripped_markers}\n")
    out.write(f"module chapter overrides: {MODULE_CHAPTER_OVERRIDES}\n")
    out.write(f"native-divergent chapters (versemap-curated): {sorted(NATIVE_DIVERGENT)}\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2], sys.argv[3])
