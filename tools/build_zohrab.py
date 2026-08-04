# -*- coding: utf-8 -*-
"""Build app/src/main/assets/bibles/hy_zohrab.json from the TITUS Zohrab dump.

    python tools/build_zohrab.py            # build + assert + report
    python tools/build_zohrab.py --dry-run  # report only, write nothing

Input : titus_zohrab/extracted/zohrab_raw.json  (tools/extract_zohrab.py)
Spec  : Hexapla-releases/research/ZOHRAB_CONVERTER_SPEC.md — read it first;
        every decision below is recorded there with the evidence for it.

Zohrab 1805 Venice, Armenian, **OLD TESTAMENT ONLY** (owner, 2026-07-20: the
Zohrab NT authentically lacks the Comma Johanneum, and the app's Armenian NT is
the shipped Western Armenian 1853 `arm`). NT slots stay empty here, exactly as
`arm`'s OT slots are empty — the two assets are complements.

⚠ THE FIVE THINGS THAT WILL BREAK A NAIVE CONVERTER
 1. Book identity comes from the Book-marker VALUE. `Esr.II_(Esr.)` (Ezra) and
    `Esr.II_(Neh.)` (Nehemiah) share the prefix `Esr.II`.
 2. The Twelve are in SEPTUAGINT order in the print. Assigning slots by
    sequence puts Amos in Joel's slot.
 3. TITUS's Esther "Chapter:" labels are SECTION COUNTERS. Block `4` is
    Addition B (the decree), not Esther 4; blocks `5`,`6`,`7` are all Esther 4.
 4. `Or.Jer.` is Lamentations 5, not a book.
 5. `Cant. 8a` is an editorial variant, not scripture.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).parent.parent
ASSETS = REPO / "app" / "src" / "main" / "assets" / "bibles"
RAW = Path("C:/Projects/Hexapla-releases/titus_zohrab/extracted/zohrab_raw.json")
OUT = ASSETS / "hy_zohrab.json"

# ── unit -> canonical slot. BY NAME. Never by sequence (trap 2). ────────────
CANON = {
    "Gen.": 0, "Ex.": 1, "Lev.": 2, "Num.": 3, "Deut.": 4,
    "Jos.": 5, "Ju.": 6, "Ru.": 7,
    "Reg.I_(Sam.I)": 8, "Reg.II_(Sam.II)": 9,
    "Reg.III_(Reg.I)": 10, "Reg.IV_(Reg.II)": 11,
    "Chr.I": 12, "Chr.II": 13,
    "Esr.II_(Esr.)": 14, "Esr.II_(Neh.)": 15,
    "Hiob": 17, "Ps.": 18, "Prov.": 19, "Eccl.": 20, "Cant.": 21,
    "Is.": 22, "Jer.": 23, "Ez.": 25,
    "Hos.": 27, "Joel": 28, "Am.": 29, "Abd.": 30, "Jon.": 31, "Mi.": 32,
    "Nah.": 33, "Hab.": 34, "Soph.": 35, "Agg.": 36, "Zach.": 37, "Mal.": 38,
}
APOCRYPHA = {
    "Esr.I_(Esr.III)": 66, "Tob.": 68, "Jud.": 69, "Sap.Sal.": 70,
    "Bar.": 72, "Macc.I": 75, "Macc.II": 76, "Macc.III": 77,
}
# Handled by dedicated code, not by a table: Esth. (§5), Dan. (§7),
# Lam.Jer.+Or.Jer. (§3), Prov. asterisks (§4), Cant. 8a (§7).
SPECIAL = {"Esth.", "Dan.", "Lam.Jer.", "Or.Jer."}

# Esther: TITUS block -> where it really goes. Read from the Armenian,
# 2026-08-03; see spec §5. (target, chapter, verse-offset-or-None)
ESTHER_CANON = {          # -> slot 16
    "1": 1, "2": 2, "3": 3,
    "5": 4, "6": 4, "7": 4,          # all three ARE canonical chapter 4
    "5@armat448.htm": 5, "6@armat449.htm": 6, "7@armat450.htm": 7,
    "8": 8, "8@armat453.htm": 8,
    "9": 9, "10": 10,
}
ESTHER_ADDITIONS = {      # -> slot 78, keeping the Vulgate chapter numbers
    "11": 11, "11@armat456.htm": 11, "12": 12,
    "4": 13,                          # Addition B = 13:1-7 (trap 3)
    "13": 13, "14": 14, "15": 15, "16": 16,
}
# Esther 4 is blocks 5+6+7 in that order; 6's labels restart at 1 and 7's are
# already canonical, so the pieces are concatenated in reading order rather
# than merged by label.
ESTHER_CH4_ORDER = ["5", "6", "7"]
ESTHER_CH8_ORDER = ["8", "8@armat453.htm"]
ESTHER_CH13_ORDER = ["4", "13"]


# ── Book names ─────────────────────────────────────────────────────────────
# DERIVED FROM THE PRINT'S OWN HEADINGS, then TRIMMED. Never invented: the
# assertion below requires every name here to be a contiguous SUBSTRING of the
# heading the extractor read out of the source, so a hand-typed Armenian word
# that is not in the print fails the build. Trimming is needed because the
# headings are full title sentences — Hosea's carries the whole Twelve-Prophets
# collection title, Proverbs' runs on into Solomon's titulature — and the app's
# bottom nav and reader title have a real label budget.
# (Inventing 48 Armenian names from memory is precisely the ru_stress failure
#  mode; using TITUS's Latin codes is the de_luther/el_vamvas one.)
NAMES = {
    # ⚠ SHORTENED 2026-08-04 after the owner's device pass. Thirteen prophets
    # all began with the identical 14-character «ՄԱՐԳԱՐԷՈՒԹԻՒՆ » ("Prophecy
    # of"), which put the distinguishing word at the END of every line and made
    # the book list unscannable; it also overflowed the reader title on
    # Habakkuk. The genre prefixes «ՄԱՐԳԱՐԷՈՒԹԻՒՆ» and «ԳԻՐՔ» are dropped.
    # Still DERIVED, never invented — the substring assertion below is
    # unchanged, so every name here must still occur in the print's heading.
    # ⚠ These are the print's GENITIVE forms («ԵՍԱՅԱՅ» = "of Isaiah"). Standing
    # alone a native may expect the nominative; flagged for the reviewer.
    "Gen.": "ԾՆՈՒՆԴՔ", "Ex.": "ԵԼՔ", "Lev.": "ՂԵՒՏԱԿԱՆ", "Num.": "ԹԻՒՔ",
    "Deut.": "ԵՐԿՐՈՐԴՈՒՄՆ ՕՐԻՆԱՑ", "Jos.": "ՅԵՍՈՒԱՅ",
    "Ju.": "ԴԱՏԱՒՈՐՔ", "Ru.": "ՀՌՈՒԹ",
    "Reg.I_(Sam.I)": "ԹԱԳԱՒՈՐՈՒԹԵԱՆՑ ԱՌԱՋԻՆ",
    "Reg.II_(Sam.II)": "ԹԱԳԱՒՈՐՈՒԹԵԱՆՑ ԵՐԿՐՈՐԴ",
    "Reg.III_(Reg.I)": "ԹԱԳԱՒՈՐՈՒԹԵԱՆՑ ԵՐՐՈՐԴ",
    "Reg.IV_(Reg.II)": "ԹԱԳԱՒՈՐՈՒԹԵԱՆՑ ՉՈՐՐՈՐԴ",
    "Chr.I": "ՄՆԱՑՈՐԴԱՑ ԱՌԱՋԻՆ", "Chr.II": "ՄՆԱՑՈՐԴԱՑ ԵՐԿՐՈՐԴ",
    "Esr.I_(Esr.III)": "ԵԶՐԻ ԱՌԱՋԻՆ", "Esr.II_(Esr.)": "ԵԶՐԱՅ ԵՐԿՐՈՐԴ",
    "Esr.II_(Neh.)": "ԲԱՆՔ ՆԵԵՄԱՅ", "Esth.": "ԵՍԹԵՐ", "Jud.": "ՅՈՒԴԻԹ",
    "Tob.": "ՏՈՎԲԻԹ",
    "Macc.I": "ԱՌԱՋԻՆ ՄԱԿԱԲԱՅԵՑՒՈՑ",
    "Macc.II": "ԵՐԿՐՈՐԴ ՄԱԿԱԲԱՅԵՑՒՈՑ",
    "Macc.III": "ԵՐՐՈՐԴ ՄԱԿԱԲԱՅԵՑՒՈՑ",
    "Ps.": "ՍԱՂՄՈՍԱՑ", "Prov.": "ԱՌԱԿՔ ՍՈՂՈՄՈՆԻ",
    "Eccl.": "ԲԱՆՔ ԺՈՂՈՎՈՂԻՆ", "Cant.": "ԵՐԳ ԵՐԳՈՑ",
    "Sap.Sal.": "ԻՄԱՍՏՈՒԹԻՒՆ ՍՈՂՈՄՈՆԻ", "Hiob": "ՅՈԲԱՅ",
    "Is.": "ԵՍԱՅԱՅ", "Jer.": "ԵՐԵՄԻԱՅ",
    "Bar.": "ԹՈՒՂԹ ԲԱՐՈՒՔԱՅ", "Lam.Jer.": "ՈՂԲՔ",
    "Ez.": "ԵԶԵԿԻԵԼԻ", "Dan.": "ԴԱՆԻԵԼԻ",
    "Hos.": "ՈՎՍԵԱՅ", "Joel": "ՅՈՎԵԼԵԱՅ",
    "Am.": "ԱՄՈՎՍԱՅ", "Abd.": "ԱԲԴԻՈՒ",
    "Jon.": "ՅՈՎՆԱՆՈՒ", "Mi.": "ՄԻՔԻԱՅ",
    "Nah.": "ՆԱՒՈՒՄԱՅ", "Hab.": "ԱՄԲԱԿՈՒՄԱՅ",
    "Soph.": "ՍՈՓՈՆԻԱՅ", "Agg.": "ԱՆԳԵԱՅ",
    "Zach.": "ԶԱՔԱՐԻԱՅ", "Mal.": "ՄԱՂԱՔԻԱՅ",
}


# ── Editorial rubrics (spec §7 / owner decision 2026-08-03) ────────────────
# Three lines in Ezekiel are not verses but SECTION RUBRICS occupying verse
# slots — «Դարձեալ ՛Ի վերայ Եգիպտոսի ։» ("Again, concerning Egypt"),
# «Ողբք ՛ի վերայ Փարաւոնի եւ Եգիպտոսի ։» ("Lamentation over Pharaoh and
# Egypt"). They are genuinely IN the 1805 print, so they are not discarded:
# following the Clementine precedent (build_vul_rubrics.py / Rubrics.kt) they
# are lifted OUT of the verse flow into rubrics_zoh.json and rendered as
# headings, which is what the print does typographically.
#
# ⚠ This is the opposite call from `Cant. 8a`, and deliberately so: 8a is an
# editorial VARIANT READING supplied from another exemplar, which the app has
# no business presenting as scripture at all, whereas these rubrics are the
# edition's own structure.
#
# Removing them also makes Ezekiel fall onto the KJV grid with no versemap
# curation at all: 29 22->21, 30 27->26, 32 33->32 — each exactly the KJV.
#
# ⚠ VERIFIED NOT TO INCLUDE look-alikes. Job 27:1, 29:1, 40:1, Isaiah 13:1 and
# Joel 1:1 open with the same words but ARE scripture (they are the KJV's own
# verses) and their chapter counts already match. Do not widen this table by
# pattern — it is a curated list of three, each read.
RUBRICS = {
    (25, 29, 17): "Դարձեալ ՛Ի վերայ Եգիպտոսի ։",
    (25, 30, 20): "Դարձեալ ՛ի վերայ Եգիպտոսի ։",
    (25, 32, 17): "Ողբք ՛ի վերայ Փարաւոնի եւ Եգիպտոսի ։",
    # Found the same way, while curating Jeremiah 49's seam: a bare
    # «Concerning Elam» heading standing in a verse slot. Removing it makes
    # Jer 49 land on the KJV grid too (40 -> 39).
    (23, 49, 34): "՛Ի վերայ ելամայ ։",
}


# ── Stichometry colophons ──────────────────────────────────────────────────
# The print closes each psalm with the scribe's line-count — «Տունք . զ՜։»
# ("lines: 6"), sometimes with «Գոբղայս . ի՜ը։» ("kephalaia: 28"). 151 psalms
# carry one, plus 3 in Proverbs. Found on the owner's device pass, visible at
# the end of Psalm 23.
#
# STRIPPED as apparatus. This is the Bakar `*` precedent, not the rubric one:
# a rubric tells the reader what section follows and so is STRUCTURE worth
# keeping, whereas a line-count is production metadata that conveys nothing to
# a reader and mirrors nothing lexical.
#
# ⚠ Anchored to the END of the verse and required to be followed only by
# numerals/punctuation, so a «Տունք» occurring as an ordinary word mid-verse
# is untouched.
# Colophon vocabulary. A trailing run made ONLY of these words plus short
# numeral tokens is apparatus; anything else is prose.
# «Տունս» is the same word in another case; «՛ի սմա» ("in it") also
# appears inside the longer Ps 150 form and passes on length alone.
# Case-folded on comparison: the tail mixes «Տունք» and «տունս». The last
# three close the whole Psalter after Ps 150 ("four canons ... altogether
# psalms"), which is why they appear nowhere else.
COLOPHON_WORDS = {w.casefold() for w in (
    "Տունք", "Տունս", "Գոբղայս", "Կանոն", "Սաղմոս", "Սաղմոսս",
    "Չորք", "Միահամուռ")}
_CSTAT = Counter()
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def strip_colophon(txt, stats):
    """Remove a trailing stichometry colophon, and nothing else.

    ⚠ «Տունք» is ALSO the ordinary word "houses" — «Տունք անօրինաց» (Prov
    14:11), «Տունք նոցա աջողեալք» (Job 21:9). A keyword match alone is not
    enough. A tail only counts as a colophon when EVERY word in it is
    colophon vocabulary and everything else is a short numeral token, which
    those prose verses fail on their very next word.
    """
    best = None
    # Case-insensitive: the print mixes «Տունք» and «տունք» (Ps 49:23).
    for m in re.finditer(r"(?:Տունք|Տունս|Գոբղայս|Կանոն|Սաղմոս)", txt, re.I):
        tail = txt[m.start():]
        words = _WORD_RE.findall(tail)
        if not words or any(w.casefold() not in COLOPHON_WORDS and len(w) > 3
                            for w in words):
            continue
        best = m.start()
        break
    if best is None:
        return txt
    out = txt[:best].strip()
    if out != txt:
        stats["colophons_stripped"] += 1
    return out or txt


def numeric(d):
    """{verse-label: text} -> [(int, text)] sorted, non-numeric dropped.

    Every path into the asset funnels through here, so the colophon strip
    lives here rather than at each call site.
    """
    out = [(int(k), strip_colophon(v, _CSTAT)) for k, v in d.items() if k.isdigit()]
    return sorted(out)


def repack(pairs):
    """Renumber 1..N, discarding the source labels. ONLY for chapters whose
    labels are a known systematic OFFSET, never for chapters with holes."""
    return [(i + 1, t) for i, (_, t) in enumerate(pairs)]


def place(pairs, report, where):
    """[(num, text)] -> positional list, index = num-1. Gaps become "".

    Placement is BY NUMBER, not dense packing: the edition's own verse numbers
    are what versemap pivots on, and repacking would silently shift every
    later verse (the sv_karlxii squeeze defect, in reverse).
    """
    if not pairs:
        return []
    n = max(p[0] for p in pairs)
    lst = [""] * n
    for num, txt in pairs:
        lst[num - 1] = txt
    holes = [i + 1 for i, t in enumerate(lst) if not t]
    if holes:
        report.setdefault("gaps", []).append((where, holes))
    return lst


def concat(blocks, chs, report, where):
    """Concatenate blocks in reading order, renumbering 1..N continuously."""
    out = []
    for b in blocks:
        for _, txt in numeric(chs.get(b, {})):
            out.append(txt)
    return [(i + 1, t) for i, t in enumerate(out)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RAW.read_text(encoding="utf-8"))
    books, headings = raw["books"], raw["book_headings"]
    kjv = json.loads((ASSETS / "en_kjv.json").read_text(encoding="utf-8"))
    west = json.loads((ASSETS / "hy_west1853.json").read_text(encoding="utf-8"))

    slots = [{"name": kjv[i]["name"], "chapters": []} for i in range(83)]
    # NT slot names come from the shipped Armenian NT so the two Armenian
    # assets agree on what a book is called; their contents stay empty here.
    for i in range(39, 66):
        slots[i]["name"] = west[i]["name"]
    report = {}

    # Every curated name must actually occur in the print's own heading.
    for unit, name in NAMES.items():
        h = " ".join(headings[unit].split())
        assert name in h, (
            "curated name %r for %s is NOT a substring of the print heading %r "
            "— names must be DERIVED, never invented" % (name, unit, h))

    def put(slot, chapters, unit=None):
        slots[slot]["chapters"] = chapters
        if unit and unit in NAMES:
            slots[slot]["name"] = NAMES[unit]

    # ── plain books ────────────────────────────────────────────────────────
    for unit, slot in list(CANON.items()) + list(APOCRYPHA.items()):
        if unit in SPECIAL:
            continue
        chs = books[unit]
        keys = sorted((k for k in chs if k.isdigit()), key=int)
        if unit == "Abd.":
            keys = ["_"]                      # TITUS leaves 1-chapter books unlabelled
        elif unit == "Cant.":
            pass                              # 8a deliberately excluded below
        elif unit == "Prov.":
            continue                          # handled below
        out = []
        for k in keys:
            pairs = numeric(chs[k])
            # ⚠ REPACK ONLY WHERE THE OFFSET IS A KNOWN LXX CONVENTION.
            # LXX Psalm 147 IS Masoretic 147:12-20, so its labels legitimately
            # start at 12; syn, csl and vul all store it as 9 dense verses with
            # zero empties, and this asset must agree with them.
            # Every OTHER chapter whose first label is > 1 is a genuinely
            # MISSING opening verse — Prov 1:1, Wisdom 6:1, Jer 16:1,
            # 1 Macc 4:1-9 — and repacking those would slide verse 2's text
            # into verse 1's position, silently mis-citing scripture. Those
            # keep their empty slot, which is honest and visible.
            if unit == "Ps." and k == "147":
                pairs = repack(pairs)
            out.append(place(pairs, report, "%s %s" % (unit, k)))
        put(slot, out, unit)

    # ── Proverbs: Septuagint reordering (spec §4) ──────────────────────────
    pv = books["Prov."]
    prov = []
    for i in range(1, 32):
        pairs = numeric(pv.get(str(i), {}))
        star = pv.get("%d*" % i)
        if star:
            if i == 24:
                # ch24 already holds 1-22 plus the LXX plus 24:22a-f which the
                # extractor renumbered to 23-27. `24*` is KJV 24:23-34 and its
                # labels restart at 1, so it appends AFTER the plus, at 28-39.
                base = max(p[0] for p in pairs)
                pairs += [(base + n, t) for n, (_, t) in enumerate(numeric(star), 1)]
            else:
                # 30* and 31* already carry correct KJV numbers (15.., 10..).
                pairs += numeric(star)
        prov.append(place(pairs, report, "Prov. %d" % i))
    put(19, prov, "Prov.")

    # ── Lamentations: Lam.Jer. 1-4 + Or.Jer. 5 (spec §3) ───────────────────
    lam = [place(numeric(books["Lam.Jer."][str(i)]), report, "Lam %d" % i)
           for i in (1, 2, 3, 4)]
    lam.append(place(numeric(books["Or.Jer."]["5"]), report, "Lam 5"))
    put(24, lam, "Lam.Jer.")

    # ── Daniel: 1-12 canonical, 13 Susanna, 14 Bel (spec §7) ───────────────
    dn = books["Dan."]
    put(26, [place(numeric(dn[str(i)]), report, "Dan %d" % i) for i in range(1, 13)],
        "Dan.")
    slots[80]["chapters"] = [place(numeric(dn["13"]), report, "Susanna")]
    # ⚠ Bel: 42 verses labelled 1-41 and then 65. Placing by number would build
    # a 65-slot chapter with 23 holes. The stray verse is real scripture — «And
    # king Astyages was gathered to his fathers, and Cyrus the Persian received
    # his kingdom» — which the VULGATE prints FIRST, as Daniel 14:1, and Zohrab
    # prints LAST. Repacked to 42, which is exactly the app slot's own count.
    # ⚠ The ordering difference is a versemap/curation item, NOT a defect to
    # "fix": do not move the verse to the front to match the Vulgate.
    bel = numeric(dn["14"])
    assert len(bel) == 42 and bel[-1][0] == 65, "Bel's shape changed — re-read it"
    slots[81]["chapters"] = [place(repack(bel), report, "Bel")]

    # ── Esther (spec §5) ───────────────────────────────────────────────────
    es = books["Esth."]
    est = []
    for ch in range(1, 11):
        if ch == 4:
            pairs = concat(ESTHER_CH4_ORDER, es, report, "Esth 4")
        elif ch == 8:
            pairs = []
            for b in ESTHER_CH8_ORDER:
                pairs += numeric(es[b])
        elif ch == 3:
            # block '4' is Addition B, but its LAST verse is Esther 3:14-15.
            pairs = numeric(es["3"])
            tail = numeric(es["4"])
            pairs.append((max(p[0] for p in pairs) + 1, tail[-1][1]))
        else:
            blk = next(k for k, v in ESTHER_CANON.items()
                       if v == ch and not k.startswith(("3", "4")))
            pairs = numeric(es[blk])
        est.append(place(pairs, report, "Esth %d" % ch))
    put(16, est, "Esth.")

    add = [[] for _ in range(17)]
    for ch in (11, 12, 14, 15, 16):
        blocks = [k for k, v in ESTHER_ADDITIONS.items() if v == ch]
        pairs = []
        for b in sorted(blocks):
            pairs += numeric(es[b])
        add[ch - 1] = place([(i + 1, t) for i, (_, t) in enumerate(pairs)],
                            report, "EsthAdd %d" % ch)
    # ch13 = Addition B (block '4' vv1-7) + Addition C (block '13' vv8-18)
    b4 = numeric(es["4"])[:-1]                # drop the Esther 3:15 tail
    add[12] = place(b4 + numeric(es["13"]), report, "EsthAdd 13")
    slots[78]["chapters"] = add

    # ── lift the editorial rubrics out of the verse flow ───────────────────
    rubrics = {}
    for (bslot, ch, vs), label in sorted(RUBRICS.items()):
        chapter = slots[bslot]["chapters"][ch - 1]
        got = chapter[vs - 1].strip()
        assert got == label.strip(), (
            "rubric moved: expected %r at %d:%d:%d, found %r"
            % (label, bslot, ch, vs, got[:60]))
        del chapter[vs - 1]
        # The rubric heads the section that FOLLOWS it, which after removal is
        # the verse now occupying its index.
        rubrics["%d:%d:%d" % (bslot, ch, vs)] = [[0, label.rstrip(" ։").strip()]]
    (ASSETS.parent / "rubrics_zoh.json").write_text(
        json.dumps(rubrics, ensure_ascii=False, indent=1), encoding="utf-8")
    print("rubrics lifted  : %d -> rubrics_zoh.json" % len(rubrics))
    print("colophons strip : %d (stichometry line-counts)" % _CSTAT["colophons_stripped"])

    # ── assertions ─────────────────────────────────────────────────────────
    assert len(slots) == 83
    assert all(not any(c) for b in slots[39:66] for c in b["chapters"]), \
        "NT slots must be empty — this asset is OT-only"
    total = sum(1 for b in slots for c in b["chapters"] for v in c if v)
    # Every extracted verse must land somewhere, minus the deliberate drops.
    dropped = len(books["Cant."]["8a"]) + len(RUBRICS)
    src = sum(len(v) for bk in books.values() for v in bk.values())
    assert total == src - dropped, \
        "verse loss: %d placed, %d source, %d deliberately dropped" % (
            total, src, dropped)

    print("books with text : %d" % sum(1 for b in slots if any(any(c) for c in b["chapters"])))
    print("verses placed   : %d  (source %d, Cant. 8a dropped %d)"
          % (total, src, dropped))
    print("Ps  chapters    : %d" % len(slots[18]["chapters"]))
    print("Prov 24 verses  : %d" % len(slots[19]["chapters"][23]))
    print("Lam chapters    : %d (verses %d)"
          % (len(slots[24]["chapters"]),
             sum(len(c) for c in slots[24]["chapters"])))
    print("Esther ch4      : %d verses" % len(slots[16]["chapters"][3]))
    print("Susanna / Bel   : %d / %d"
          % (len(slots[80]["chapters"][0]), len(slots[81]["chapters"][0])))
    print("3 Maccabees     : %d chapters (slot 77 was empty in every asset)"
          % len(slots[77]["chapters"]))
    gaps = report.get("gaps", [])
    print("\nchapters with interior gaps: %d" % len(gaps))
    for where, holes in gaps[:12]:
        print("    %-16s missing verse(s) %s"
              % (where, holes if len(holes) < 9 else "%s… (%d)" % (holes[:8], len(holes))))
    if len(gaps) > 12:
        print("    … and %d more" % (len(gaps) - 12))

    if args.dry_run:
        print("\n[dry-run] nothing written")
        return
    OUT.write_text(json.dumps(slots, ensure_ascii=False), encoding="utf-8")
    print("\nwrote %s (%.1f MB)" % (OUT, OUT.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
