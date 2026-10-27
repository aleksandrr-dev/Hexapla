# -*- coding: utf-8 -*-
"""Build the 1827 J.D. Kieffer Turkish Bible asset from the raw HTML cached by
`fetch_osm_kieffer.py`.

    python tools/build_tr_kieffer.py                 # census + grid report, writes nothing
    python tools/build_tr_kieffer.py --out <file>    # also write the asset

Output: the app's asset shape - a list of 66 {name, chapters: [[verse, ...]]}.

## The source markup (census of every tag inside a verse, 2026-09-25)
Each verse is `<span id="notation_p<BK>.<CCC>.<VVV>" class="notation">`, whose
text follows the `verse_p` numeral div. Inside it:
- `div.quote > a`   a glossed word (the site's pop-up notes) - keep the WORD
- `nobr.nudge_right` a typographic nudge inside a word - keep the letter
- `div.paragraph`, `<p />`, `&nbsp;`  layout - a space
- `div.chapter`      the chapter numeral - dropped
- `span.title`, `span.subHeader`  book title / chapter heading («İkinci fasl»)
  and editorial notes set in a heading - dropped
- `¤`  ends EVERY chapter (367 = the chapter count of the first 13 books).
  Everything after it in the slot is the next heading or an editorial note,
  so the slot is CUT at `¤`.
- `{...}` the transcribers' own brackets: mostly SUPPLIED words (the KJV-italics
  convention: `{yaʿnî}`, `{ki seni öldüre}`), which BibleRepo keeps (no colon).
  A few are EDITORIAL NOTES (`{bk. 22. ayet}` = «see v22»). Those are listed
  by --notes and must be ruled; a note is rewritten into the app's note form
  `{Not: ...}` (colon = stripped from display by BibleRepo.parseAsset).
⛔ Any tag or class NOT in the census is a hard failure: new markup means the
  source changed, and silently stripping it could drop scripture.
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

CACHE = Path("C:/Projects/Hexapla-releases/_work/osm_cache/kieffer1827")
KJV = Path("C:/Projects/Hexapla/app/src/main/assets/bibles/en_kjv.json")

CODES = ("GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB "
         "PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP "
         "HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI "
         "2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV").split()

# Display names: the 1827 print's own book names as the site transcribes them,
# without the site's modern-Turkish glosses in parentheses.
NAMES = [
    "Tekvin", "Hurûc", "Leviyyin", "Adâd", "Tevrat el-Müsenna", "Yoşe",
    "Hakimler", "Raot", "1. Samuel", "2. Samuel", "1. Krallar", "2. Krallar",
    "1. Tarihler", "2. Tarihler", "Ezra", "Nehemya", "Ester", "Eyûb", "Mezamir",
    "Emsal-i Süleyman", "Vaiz-i Süleyman", "Süleyman'ın Ezgisi", "İşaya",
    "Yeremiya", "Yeremiya'nın Ağıtları", "Hezekiel", "Daniyal", "Hoşe", "Yoel",
    "Amos", "Obadya", "Yunus", "Mika", "Nahum", "Habakkuk", "Sefaniya", "Hagay",
    "Zekeriya", "Malakiya",
    "Matta", "Markos", "Luka", "Yuhanna", "Resûllerin Amâli", "Romalılara",
    "1. Korintlilere", "2. Korintlilere", "Galatiyalılara", "Efesuslulara",
    "Filippililere", "Kolosselilere", "1. Selaniklilere", "2. Selaniklilere",
    "1. Timoteos'a", "2. Timoteos'a", "Titus'a", "Filemon'a", "İbranilere",
    "Yakub", "1. Petrus", "2. Petrus", "1. Yuhanna", "2. Yuhanna", "3. Yuhanna",
    "Yahuda", "Apokalipsis",
]
assert len(CODES) == len(NAMES) == 66

SPAN = re.compile(r'<span id="notation_p([A-Z0-9]+)\.(\d+)\.(\d+)" class="notation">')
KNOWN_TAGS = {
    ("div", "verse"), ("div", "quote"), ("div", "paragraph"), ("div", "chapter"),
    ("nobr", ""), ("nobr", "nudge_right"), ("a", ""), ("p", ""), ("center", ""),
    ("span", "title"), ("span", "subHeader"),
}
# Editorial notes the converter recognises; everything else in braces is
# SUPPLIED text and kept. Extend only after reading the site (--notes).
NOTE = re.compile(r"\{(\s*(?:bk\.|Osm metindeki|[^{}]*\d)[^{}]*)\}")

# The print's own verse numbers, which the site keeps inline after re-addressing
# the text onto the KJV grid: «(8)», «(39:1)», «(5.1)», «(38b)», «(-)» at the head
# of a slot, and «(N)» mid-slot where the print starts a verse the KJV does not.
# Only digit/dash markers - «(Romadan Filippililere …)» (Phil 4:23) is text.
LEAD_MARK = re.compile(r"^\((?:\d+(?:[:.]\d+|b)?|-)\)\s*")
MID_MARK = re.compile(r"\s*\(\d+\)\s*")

# U+F25D is private-use. In the site's own font (CharisSIL-R.woff, fetched
# 2026-09-25) it maps to glyph «uni1D7C», the IDENTICAL outline to U+1D7C ᵼ -
# and James 1:17's «yukar?dandır» is the NT's usual «yukarᵼdan» (8 others).
PUA_MAP = {"": "ᵼ"}


def _split_at(text, anchor, where):
    i = text.find(anchor)
    if i <= 0:
        raise SystemExit(f"⛔ {where}: split anchor {anchor!r} not found - the source changed")
    return text[:i].strip(), text[i:].strip()


def fix_grid(books):
    """Move the text the print numbers differently onto the KJV grid. Each rule
    was checked against the KJV text (2026-09-25); each refuses if its anchor
    has moved, so a changed source fails loudly instead of misplacing a verse."""
    sam = books["1SA"]
    # 1 Sam 20: TR v43 is KJV 42b («And he arose and departed …»).
    if (20, 43) not in sam:
        raise SystemExit("⛔ 1SA 20:43 absent - the source changed")
    sam[(20, 42)] = sam[(20, 42)] + " " + sam.pop((20, 43))
    # 1 Sam 23:29: the print's 24:1 opens with it, then «(2)» starts KJV 24:1.
    if (23, 29) in sam:
        raise SystemExit("⛔ 1SA 23:29 present - the source changed")
    sam[(23, 29)], sam[(24, 1)] = _split_at(sam[(24, 1)], "(2)", "1SA 24:1")
    # Eccl: TR 4:17 «(5.1) …» is KJV 5:1; TR 5:1 is only the cross-reference.
    ecc = books["ECC"]
    if not ecc.get((4, 17), "").startswith("(5.1)") or ecc.get((5, 1)) != "(bkz 4.17)":
        raise SystemExit("⛔ ECC 4:17 / 5:1 are not the expected (5.1) / (bkz 4.17) pair")
    ecc[(5, 1)] = ecc.pop((4, 17))
    # Jonah: TR 2:1 opens with the great fish (KJV 1:17), then «(2)» the prayer.
    jon = books["JON"]
    if jon.get((1, 17)) != "{bk. 2:1}":
        raise SystemExit("⛔ JON 1:17 is not the expected {bk. 2:1} note")
    jon[(1, 17)], jon[(2, 1)] = _split_at(jon[(2, 1)], "(2)", "JON 2:1")
    # Neh 4:23 is only the note «see v22»: the print sets KJV 4:22-23 as ONE
    # verse, with no marker between them. Split on MEANING: «ve ben ve
    # karındaşlarım ve oğlanlarım …» is KJV 4:23 «So neither I, nor my brethren,
    # nor my servants …»; what precedes it is KJV 4:22.
    neh = books["NEH"]
    if neh.get((4, 23)) != "{bk. 22. ayet}":
        raise SystemExit("⛔ NEH 4:23 is not the expected {bk. 22. ayet} note")
    neh[(4, 22)], neh[(4, 23)] = _split_at(neh[(4, 22)], "ve ben ve karındaşlarım", "NEH 4:22")


def strip_marks(t):
    t = LEAD_MARK.sub("", t)
    return MID_MARK.sub(" ", t).strip()


def verse_slots(page):
    """-> [(code, ch, v, raw_html)] in page order. A slot runs from its
    notation span to the next one (headings nest their own </span>, so the
    closing tag cannot be used to bound it)."""
    marks = list(SPAN.finditer(page))
    end = page.find('<input name="devent"', marks[-1].end()) if marks else -1
    out = []
    for i, m in enumerate(marks):
        stop = marks[i + 1].start() if i + 1 < len(marks) else end
        out.append((m.group(1), int(m.group(2)), int(m.group(3)), page[m.end():stop]))
    return out


def clean(raw, where, census):
    for name, attrs in re.findall(r"<([a-zA-Z]+)([^>]*)>", raw):
        cls = re.search(r'class="([^"]*)"', attrs)
        key = (name.lower(), cls.group(1) if cls else "")
        census[key] += 1
        if key not in KNOWN_TAGS:
            raise SystemExit(f"⛔ {where}: unknown markup <{name}{attrs[:80]}> - the source changed")
    t = re.sub(r'<div id="chapter_\d+"\s+class="chapter">\d+</div>', " ", raw)
    t = re.sub(r'<div id="verse_p[^"]+" class="verse">\d+</div>', " ", t)
    t = re.sub(r'<center>.*?</center>', " ", t, flags=re.S)       # title / headings
    t = re.sub(r"<div class=\"paragraph\"></div>|<p\s*/>", " ", t)
    t = re.sub(r"<[^>]+>", "", t)                                   # quote/a/nobr wrappers
    t = html.unescape(t).replace("\u00a0", " ")
    for k, v in PUA_MAP.items():
        t = t.replace(k, v)
    pua = [c for c in t if 0xE000 <= ord(c) <= 0xF8FF]
    if pua:
        raise SystemExit(f"⛔ {where}: unmapped private-use {['U+%04X' % ord(c) for c in pua]}"
                         " - identify it in the site's font, never ship it")
    if "¤" in t:
        t = t.split("¤", 1)[0]
    return re.sub(r"\s+", " ", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write the asset here")
    ap.add_argument("--notes", action="store_true", help="list every {...} and how it was classed")
    a = ap.parse_args()

    files = sorted((CACHE / "ot").glob("*.html")) + sorted((CACHE / "nt").glob("*.html"))
    if len(files) != 71:
        print(f"⛔ {len(files)} cached pages, expected 71 (44 OT entries + 27 NT) - run fetch_osm_kieffer.py")
        return 2
    census = Counter()
    books = {c: {} for c in CODES}
    for f in files:
        for code, ch, v, raw in verse_slots(f.read_text(encoding="utf-8")):
            if ch == 0 or v == 0:          # book title / chapter-head slots
                continue
            if code not in books:
                print(f"⛔ {f.name}: unknown book code {code}")
                return 2
            key = (ch, v)
            if key in books[code]:
                print(f"⛔ duplicate {code} {ch}:{v}")
                return 2
            books[code][key] = clean(raw, f"{code} {ch}:{v}", census)
    fix_grid(books)
    for code in books:
        books[code] = {k: strip_marks(t) for k, t in books[code].items()}

    kjv = json.loads(KJV.read_text(encoding="utf-8"))
    asset, diffs, empties, notes, supplied = [], [], [], [], Counter()
    for bi, code in enumerate(CODES):
        got = books[code]
        nch = max((c for c, _ in got), default=0)
        chapters = []
        for c in range(1, nch + 1):
            nv = max((v for cc, v in got if cc == c), default=0)
            vs = []
            for v in range(1, nv + 1):
                t = got.get((c, v))
                if t is None:
                    diffs.append(f"{code} {c}:{v} MISSING in source (gap in numbering)")
                    t = ""
                for m in re.finditer(r"\{([^{}]*)\}", t):
                    if NOTE.fullmatch(m.group(0)):
                        notes.append(f"{code} {c}:{v}  {m.group(0)}")
                    else:
                        supplied[m.group(0)] += 1
                t = NOTE.sub(lambda m: "{Not: " + m.group(1).strip() + "}", t)
                if not re.sub(r"\{[^{}]*:[^{}]*\}", "", t).strip():
                    empties.append(f"{code} {c}:{v}  {t!r}")
                vs.append(t)
            chapters.append(vs)
        kch = kjv[bi]["chapters"]
        if len(kch) != len(chapters):
            diffs.append(f"{code}: {len(chapters)} chapters vs KJV {len(kch)}")
        for c in range(min(len(kch), len(chapters))):
            if len(kch[c]) != len(chapters[c]):
                diffs.append(f"{code} {c + 1}: {len(chapters[c])} verses vs KJV {len(kch[c])}")
        asset.append({"name": NAMES[bi], "chapters": chapters})

    total = sum(len(v) for b in asset for v in b["chapters"])
    ktotal = sum(len(v) for b in kjv[:66] for v in b["chapters"])
    print(f"verses {total} (KJV protestant canon {ktotal})")
    print(f"markup census: {dict(census)}")
    print(f"supplied {{...}}: {sum(supplied.values())} kept; editorial notes: {len(notes)}")
    if a.notes:
        for n in notes:
            print("  NOTE    ", n)
        for s, k in supplied.most_common():
            print(f"  SUPPLIED {k:4d} {s}")
    print(f"\ngrid differences vs KJV: {len(diffs)}")
    for d in diffs:
        print("  ", d)
    print(f"\nempty / note-only slots: {len(empties)}")
    for e in empties:
        print("  ", e)
    letters = Counter(ch for b in asset for c in b["chapters"] for v in c for ch in v
                      if not ch.isalpha() and not ch.isspace())
    print(f"\nnon-letter characters: {letters.most_common()}")
    if a.out:
        Path(a.out).write_text(json.dumps(asset, ensure_ascii=False, separators=(",", ":")),
                               encoding="utf-8", newline="\n")
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
