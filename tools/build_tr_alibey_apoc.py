# -*- coding: utf-8 -*-
"""Build the 1665 Ali Bey apocrypha (Kadir Akın's transliteration) into grid
slots 66-82, from the event stream of `alibey_apoc_extract.py`. 0 tokens.

    python tools/build_tr_alibey_apoc.py            # DRY RUN (the default)
    python tools/build_tr_alibey_apoc.py --write    # write _work/alibey_apoc/tr_alibey_apoc.json
    python tools/build_tr_alibey_apoc.py --book Esther   # one book, per chapter

⛔ LICENCE: page 2 reserves all rights to Kadir Akın. Owner 2026-09-25: build
it, do NOT ship it until the permission answer is reported. So this writes
ONLY under `_work/alibey_apoc/`, never into app assets, and has no flag that
does. Wiring it into an asset is a later, separate, owner-gated step.

Reads `_work/alibey_apoc/events.jsonl`; the page map and every decision below
come from `_work/alibey_apoc/SLOT_MAPPING_NOTES_2026-09-25.md` + the
2026-09-26 ADDENDUM.

## NATIVE NUMBERING (build_apocrypha_sv.py precedent)
A verse numbered n goes to index n-1 of its chapter. Verse counts that differ
from the KJV stay as printed. The extractor has already resolved doubled
numerals by position (its `n`; the print's own numeral is in `n_printed`).
The only reshaping is the chapter-level placement declared in PLACE below, and
each is a text-verified alignment with the KJV, not a guess.

## WHAT IS NOT SCRIPTURE, AND IS DROPPED (each is checked, not assumed)
- `catch` events: facsimile page-end catchwords. Each must be the opening
  of the next verse text (checked; a mismatch is fatal).
- stray catchwords p285 / p1799 / p1835 (same check).
- colophons (Tobit p435, 3 Macc p1935), running heads, notes, headings,
  the modern-Turkish (italic) layer, and the modern subtitles.
- Sirach 51's subtitle «Sarâh oğlu Yesûʿuŋ duâsı» (p789) - a heading; the KJV
  sets it as a title, not as 51:1.
- Sirach's two prologues (p443-p447) are NOT in any slot (the grid has none).
  OWNER RULING 2026-09-26: keep them - the KJV 1611 prints both («A Prologue
  made by an uncertain Author» and «The Prologue of the Wisdom of Jesus the
  son of Sirach»). They ship the way the Vulgate's «Prologus» and the Bakar's
  scholia do: as RUBRICS on Sirach 1:1 (output `rubrics`, key "71:1:1", the
  Rubrics.kt format [offset 0, text]), rendered above the verse and outside
  the verse text, so the KJV grid and verse numbering are untouched.

## KEPT FROM STRAY TEXT (each is authentic 1665 text with no numeral)
- p839 superscription (four upright lines) = KJV Baruch 6:1 (Epistle of
  Jeremiah); the print's 6:1..72 therefore go to 6:2..73 (Karl XII does this).
- p1715 «…….ve Mordehây bunlar Allahdaŋ olmuşdur dėdi» = KJV Add. Esther
  10:4 (the dots are the editor's; print notes vv1-4 missing in 1664-65).

## ESTHER: print chapters -> KJV chapters (text-aligned)
print ch7 v5-13 = KJV 10:5-13 (native numerals), its v14 «Batlomyos …
Dosît…» = KJV 11:1; print ch1 v1 «…Artahşeşt…» = 11:2, so print ch1 sits at
11:2ff; print ch2-6 = KJV 12-16. Chapters 1-9 of the slot stay empty, as in
en_kjv.json.
"""
import argparse
import json
import re
import unicodedata
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORK = Path(r"C:/Projects/Hexapla-releases/_work/alibey_apoc")
EVENTS = WORK / "events.jsonl"
OUT = WORK / "tr_alibey_apoc.json"
KJV = Path(__file__).resolve().parent.parent / "app/src/main/assets/bibles/en_kjv.json"

# (first page, slot, expected print chapters). A book begins at the first
# head or «1*» verse on or after its first page (a page can end the book
# before). Daniel's additions are one run, split on the numbering restarts.
BOOKS = [
    (9, 69, 16),     # Judith
    (141, 70, 19),   # Wisdom
    (351, 68, 14),   # Tobit
    (437, 74, 1),    # Prayer of Manasses
    (443, 71, 53),   # Sirach: 2 prologues + 51 chapters
    (801, 72, 6),    # Baruch (ch6 = Epistle of Jeremiah)
    (859, 75, 16),   # 1 Maccabees
    (1123, 76, 15),  # 2 Maccabees (headless)
    (1317, 66, 9),   # 1 Esdras («ʿAzdrâ sâlis»)
    (1445, 67, 16),  # 2 Esdras («Le 4. Livres d'Esdras»)
    (1667, 78, 7),   # Additions to Esther (7 print chapters)
    (1723, 79, 3),   # Azariah / Susanna / Bel, split below
    (1799, 77, 7),   # 3 Maccabees («Şemʿon»), ch6 headless
]
DANIEL_SLOTS = (79, 80, 81)

# Catchword-like strays: must be the opening of the next verse, then dropped.
STRAY_CATCH = {285, 1799, 1835}
# Strays that are headings / modern copies / editorial notes: dropped. Every
# stray not in STRAY_CATCH, STRAY_DROP or the two KEPT cases is fatal.
STRAY_DROP_RE = re.compile(
    r"^(I|a\)|\(.*|Eklesiyastikus.*|Sarah’ın bilgeliği|- Bilinmeyen.*|"
    r"Sara oğlu Yesus’un.*|Sarâh oğlu Yesûʿuŋ duâsı|Ezra’nın kuşkulu.*|Ezra da derler\.|"
    r"ayete kadar eksiktir\.\)|ona 3\. Makabeliler diyor\.\))\s*$")

# Catchwords that match nothing by rule, each read by hand against the page's
# text (a spelling drift, not lost text). Page -> what was seen.
CATCH_REVIEWED = {
    747: "«mühürgen» = next verse's «muhr-gen» (spelling drift)",
    783: "«borỉları» = run-over verse's «borıları» (spelling drift)",
    1257: "«hatâları»: p1259 opens «içỉn rencîde oluna» - Akın's text omits the "
          "word; the text layer is complete (2026-09-26 page-top probe)",
    1459: "«muayyen» = p1461's first line «muʿîn ol» (spelling drift)",
    1607: "«tozdan» (KJV 2 Esd 13:11 «dust») is NOT on p1609 in Akın's PRINT either: "
          "the rendered page (crop read 2026-09-26) has an empty first-line slot above "
          "«tütünüŋ», and the modern line also lacks it. The 1665 word(s) are unknown "
          "beyond the catchword, so the verse stays as Akın printed it (p1257 class)",
    # p795 was fatal until 2026-09-26: p797 is set in 12 pt and lost Sirach
    # 51:37's tail + 51:38-39; fixed in alibey_apoc_extract.PAGE_BODY (control
    # HEXAPLA_ALIBEY_NO797=1 brings the failure back).
}

# A chapter heading («İkinci Bâb», «(Evvelki Bâb)») starts a print chapter even
# when its first verse is not «1*».
CH_HEAD = re.compile(r"(?i)\bb[âa]b\b")
NOTE_MARK = re.compile(r"\s*\+{1,2}(?=\s|$)")

KNOWN_HOLES = {
    (71, 2): "Sirach 2: the print skips «8» in BOTH layers (7 -> 9) - a "
             "numbering skip, no lost text (ADDENDUM 2026-09-26 §3)",
    (78, 10): "Add. Esther 10:1-3 are missing in 1664-65 (the print says so, "
              "p1715); indices 0-2 stay empty exactly as en_kjv's own ch10",
}


def die(msg):
    raise SystemExit("FATAL: " + msg)


def norm(s):
    s = s.replace("∞", "").replace("…", "").strip(" .")
    # Comparison key for catchwords only (never applied to verse text): the
    # catchword's spelling drifts from the page's («sefihe» / «sefîhe»,
    # «İllâ» / «illâ»), so fold case, diacritics and the transliteration's
    # special letters.
    s = unicodedata.normalize("NFD", re.sub(r"\s+", " ", s).casefold())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.translate(str.maketrans({"ı": "i", "ŋ": "n", "ʿ": None, "ʾ": None, "'": None, "’": None}))


def load():
    ev = [json.loads(l) for l in EVENTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not ev:
        die("no events in %s" % EVENTS)
    return ev


def next_verse_text(ev, i):
    for e in ev[i + 1:]:
        if e["k"] == "v":
            return e["t"]
    return ""


def check_catch(ev, fuzzy, unmatched):
    """Every catchword must continue the run-over verse or open the next. -> count checked."""
    n = 0
    for i, e in enumerate(ev):
        is_catch = e["k"] == "catch" or (e["k"] == "stray" and e.get("layer") == "R"
                                         and e["p"] in STRAY_CATCH and "∞" in e["t"])
        if not is_catch:
            continue
        cw = re.sub(r"^\[?\d+\]?\*?\s*", "", norm(e["t"]))  # «13 zîrâ ∞»: numeral + word
        if cw.endswith(" bab"):  # norm() folds «bâb»
            n += 1  # a heading catchword; the next event is that heading
            continue
        # The facsimile's catchword is the first word of its next page: either
        # inside the verse that runs over (it carries «cont») or the opening
        # of the next verse. Anything else means text was lost or misplaced.
        nxt = norm(next_verse_text(ev, i))
        prev = next((x for x in reversed(ev[:i]) if x["k"] == "v"), None)
        words = cw.split()
        inside = (prev is not None and prev.get("cont")
                  and re.search(r"(^| )" + re.escape(" ".join(words)) + r"( |$)", norm(prev["t"])))
        if not words or not (nxt.startswith(words[0]) or inside):
            # the catchword's spelling can differ from the page's («hasedden» /
            # «hasetden»), so a near match - same 4-letter stem among the next
            # verse's first 3 words or anywhere in the run-over verse - is
            # reported, not fatal. No match at all is fatal.
            stem = words[0][:4] if words else ""
            near = stem and (any(w.startswith(stem) for w in nxt.split()[:3]) or (
                prev is not None and prev.get("cont")
                and any(w.startswith(stem) for w in norm(prev["t"]).split())))
            if not near:
                if e["p"] not in CATCH_REVIEWED:
                    unmatched.append("p%d «%s» | run-over «…%s» | next «%s»"
                                     % (e["p"], e["t"], norm(prev["t"])[-45:] if prev else "", nxt[:45]))
                n += 1
                continue
            fuzzy.append("p%d «%s» ~ «%s»" % (e["p"], e["t"], nxt[:30]))
        n += 1
    return n


def segment(ev):
    """-> {slot: [ [ (n, text, page) ... ] per print chapter ]}, plus kept strays."""
    starts = sorted(BOOKS)
    books, kept = {}, {}
    bi, cur_ch, new_ch = -1, None, False
    for e in ev:
        p, k = e["p"], e["k"]
        # advance to the next book on a head or a «1*» verse at/after its first page
        while bi + 1 < len(starts) and p >= starts[bi + 1][0] and (
                k == "head" or (k == "v" and e["n"] == 1)):
            bi += 1
            cur_ch = None
            books[starts[bi][1]] = []
        if bi < 0:
            continue
        slot = starts[bi][1]
        if k == "stray":
            t = e["t"].strip()
            if e.get("layer") == "I":
                continue  # modern-Turkish copy
            if p == 839:
                kept.setdefault("baruch6_1", []).append(t)
            elif p == 1715 and not t.startswith("(") and not STRAY_DROP_RE.match(t):
                kept.setdefault("esther10_4", []).append(t)
            elif p in STRAY_CATCH and "∞" in t:
                pass
            elif not STRAY_DROP_RE.match(t):
                die("unclassified stray p%d «%s» - read it, then classify it here" % (p, t))
            continue
        if k == "head" and CH_HEAD.search(e["t"]):
            new_ch = True  # Esther's «Yedinci Bâb» opens at v5 (vv1-4 lost): no «1*»
        if k != "v":
            continue
        if e["n"] == 1 or cur_ch is None or new_ch:
            cur_ch = []
            books[slot].append(cur_ch)
            new_ch = False
        # Akın's footnote marks «+» / «++» sit on a word's end or alone
        # («eyliḡini+ söyler», «ėden + kurtulmaz») - apparatus, never text.
        cur_ch.append((e["n"], NOTE_MARK.sub("", e["t"]).strip(), p))
    return books, kept


# Inline facsimile catchwords: a page-end catchword set INSIDE the column, glued
# to the verse end - «…helâk oldu 4 ve yer ȯnuŋ» where print v4 opens «Ve yer
# ȯnuŋ…» (Wisdom 10:3), or the bare numeral «…ėdeler 3». Stripped ONLY when the
# numeral is the next print verse's and its words open that verse; any other
# trailing numeral stays in the text and the residue gate below dies on it.
INLINE_CATCH = re.compile(r"\s+(\d+)((?:\s+\S+){0,4})\s*$")
# Apparatus marks in the verse text: «•» (5), a lone «‘» or «’.» (editor's
# marks), the note letter «a):» (2 Esd 1:5), a «)» whose «(» is not in the verse.
APPARATUS = [(re.compile(r"\s*•\s*"), " "), (re.compile(r"(^|\s)(‘|’\.)(?=\s|$)"), " "),
             (re.compile(r"\s+a\):?$"), "")]
# Declared patches, each read on its page (never a guess).
PATCH = {
    # Wisdom 13:13: «eyce: íyỉce.» is the editor's gloss of the
    # manuscript's «eyce» - keep the reading, drop the gloss. Akın keeps
    # the manuscript form in the verse and glosses it in a FOOTNOTE at
    # every other site («eylik» p579/p1299/p1359/p1849, notes «+Eylik:
    # íyỉlik.»); this one was set inline. Owner rule 2026-09-25: what the
    # original lacked comes out. (Until 2026-09-26 this kept the gloss.)
    ("eyce: íyỉce.", "eyce"),
}


def clean_chapter(ch, stats):
    """(n, text, page) list -> same, with inline catchwords and marks removed."""
    out = []
    for i, (n, t, p) in enumerate(ch):
        for old, new in PATCH:
            if old in t:
                t = t.replace(old, new); stats["patch"] += 1
        for rx, rep in APPARATUS:
            t2 = rx.sub(rep, t)
            if t2 != t:
                stats["mark"] += 1; t = t2
        if t.endswith(")") and "(" not in t:
            t = t[:-1]; stats["mark"] += 1
        m = INLINE_CATCH.search(t)
        if m and i + 1 < len(ch) and int(m.group(1)) == ch[i + 1][0]:
            words = norm(m.group(2))
            nx = norm(ch[i + 1][1])  # Wis 18:12 «13 ol kimseler ki» / «Ve ol kimseler ki»
            if not words or nx.startswith(words) or nx.startswith("ve " + words):
                t = t[:m.start()]; stats["catch"] += 1
        out.append((n, re.sub(r"\s{2,}", " ", t).strip(), p))
    return out


def place(verses, offset=0):
    """print verse n -> index n-1+offset; die on a duplicate."""
    out = {}
    for n, t, p in verses:
        i = n - 1 + offset
        if i in out:
            die("duplicate verse %d (p%d)" % (n, p))
        out[i] = t
    return [out.get(i, "") for i in range(max(out) + 1)] if out else []


def build(books, kept, kjv):
    names = {i: kjv[i]["name"] for i in range(66, 83)}
    out = {}
    got = {s: len(c) for s, c in books.items()}
    for first, slot, want in BOOKS:
        if got.get(slot) != want:
            die("%s: %s print chapters, expected %d" % (names[slot], got.get(slot), want))

    # Daniel's additions: one segment of three restarts -> three slots.
    dan = books.pop(79)
    for s, ch in zip(DANIEL_SLOTS, dan):
        books[s] = [ch]

    # Sirach: the two prologues are held out of the slot.
    prologues = [[t for n, t, p in ch] for ch in books[71][:2]]
    if [ch[0][2] for ch in books[71][:2]] != [443, 445] or books[71][2][0][2] != 449:
        die("Sirach prologue pages moved: %s" % [ch[0][2] for ch in books[71][:3]])
    books[71] = books[71][2:]

    for slot, chapters in books.items():
        if slot == 78:
            continue
        built = [place(ch) for ch in chapters]
        if slot == 72:  # Epistle of Jeremiah: superscription is 6:1
            sup = " ".join(kept.get("baruch6_1", []))
            sup = re.sub(r"-\s+(?=\w)", "", sup) if sup.count("-") else sup
            if not sup:
                die("Baruch 6:1 superscription not found on p839")
            built[5] = [sup] + place(chapters[5])
        out[slot] = built

    # Esther: print ch1..7 -> KJV 10..16 (text-aligned, see docstring)
    est = books[78]
    ch7 = est[6]
    if ch7[0][0] != 5 or ch7[-1][0] != 14:
        die("Esther print ch7 should run 5..14, runs %d..%d" % (ch7[0][0], ch7[-1][0]))
    frag = " ".join(kept.get("esther10_4", []))
    frag = re.sub(r"^[.…\s]+", "", frag)
    if not frag.startswith("ve Mordehây"):
        die("Esther 10:4 fragment not found: «%s»" % frag)
    c10 = place([v for v in ch7 if v[0] <= 13])
    c10[3] = frag
    c11 = [ch7[-1][1]] + place(est[0])
    out[78] = [[] for _ in range(9)] + [c10, c11] + [place(c) for c in est[1:6]]
    return out, prologues, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write the output (default: dry run)")
    ap.add_argument("--book", help="per-chapter detail for one book (name substring)")
    args = ap.parse_args()

    kjv = json.loads(KJV.read_text(encoding="utf-8"))
    ev = load()
    fuzzy, unmatched = [], []
    ncatch = check_catch(ev, fuzzy, unmatched)
    if unmatched:
        for u in unmatched:
            print("catchword UNMATCHED:", u)
        die("%d catchword(s) match nothing - read each, then list its page in CATCH_REVIEWED" % len(unmatched))
    for f in fuzzy:
        print("catchword near-match:", f)
    books, kept = segment(ev)
    stats = {"catch": 0, "mark": 0, "patch": 0}
    books = {s: [clean_chapter(ch, stats) for ch in chs] for s, chs in books.items()}
    if stats["patch"] != len(PATCH):
        die("declared patches applied %d, declared %d" % (stats["patch"], len(PATCH)))
    print("cleaned: %(catch)d inline catchwords, %(mark)d apparatus marks, %(patch)d patches" % stats)
    out, prologues, names = build(books, kept, kjv)

    total = holes = 0
    print("%-4s %-22s %4s %6s %6s %6s" % ("slot", "book", "chs", "verses", "holes", "kjv"))
    for slot in sorted(out):
        chs = out[slot]
        nv = sum(1 for c in chs for v in c if v)
        nh = 0
        for ci, c in enumerate(chs, 1):
            h = sum(1 for v in c if not v)
            if h and (slot, ci) not in KNOWN_HOLES:
                die("undocumented empty slot(s) in %s %d: %s"
                    % (names[slot], ci, [i + 1 for i, v in enumerate(c) if not v]))
            nh += h
        kv = sum(len(c) for c in kjv[slot]["chapters"])
        print("%-4d %-22s %4d %6d %6d %6d" % (slot, names[slot], len(chs), nv, nh, kv))
        total += nv
        holes += nh
        if args.book and args.book.lower() in names[slot].lower():
            for ci, c in enumerate(chs, 1):
                g = kjv[slot]["chapters"][ci - 1] if ci - 1 < len(kjv[slot]["chapters"]) else []
                print("     ch%-3d %3d v (kjv %3d)  %s" % (ci, len(c), len(g), (c[0][:70] if c else "")))
    print("TOTAL %d verses, %d documented holes; catchwords checked %d; "
          "Sirach prologues -> rubrics 71:1:1: %s verses"
          % (total, holes, ncatch, [len(p) for p in prologues]))
    bad = [(s, ci, vi) for s in out for ci, c in enumerate(out[s]) for vi, v in enumerate(c)
           if re.search(r"[∞*+\[\]•\d]|\s{2}|(^|\s)‘(\s|$)", v)]
    if bad:
        die("editorial marks left in %d verses, first %s" % (len(bad), bad[:3]))

    if not args.write:
        print("DRY RUN - nothing written. --write writes %s" % OUT)
        return 0
    doc = {
        "_note": "Ali Bey 1665 apocrypha, Kadir Akın transliteration. NOT FOR SHIPPING "
                 "until the owner reports permission (page 2 reserves all rights).",
        "books": [{"slot": s, "name": names[s], "chapters": out[s]} for s in sorted(out)],
        # Rubrics.kt shape: "slot:chapter:verse" -> [[offset, text], ...]
        "rubrics": {"71:1:1": [[0, " ".join(p)] for p in prologues]},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=0), encoding="utf-8", newline="\n")
    chk = json.loads(OUT.read_text(encoding="utf-8"))
    n = sum(1 for b in chk["books"] for c in b["chapters"] for v in c if v)
    if n != total:
        die("wrote %d verses, file holds %d" % (total, n))
    print("VERIFIED ON RE-READ: %d verses in %s" % (n, OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
