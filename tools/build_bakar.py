# -*- coding: utf-8 -*-
"""Build app/src/main/assets/bibles/ka_bakar.json from the TITUS Bakar dump.

    python tools/build_bakar.py --dry-run   # report only, write nothing
    python tools/build_bakar.py             # build + assert + report

Input : titus_bakar/extracted/bakar_raw.json  (tools/extract_bakar.py)
Spec  : Hexapla-releases/research/BAKAR_CONVERTER_SPEC.md — read it first.

Bakar 1743 Moscow, Georgian, FULL CANON (owner, 2026-07-20), under Prof. Jost
Gippert's TITUS grant (credit already in sources_text alongside the Zohrab).

★ STATUS: FIRST PASS. This handles the mechanical bulk — part→slot mapping,
apparatus stripping, label normalization, prologue/Odes exclusion — and then
REPORTS everything the spec says needs curation rather than pretending to have
done it. Esther's inline additions, the Job margin notes, the print-typo label
cascades and the heavy Kings/Exodus/Job versemap work are NOT done here.

⚠⚠ MAP BY PART NUMBER, NEVER BY BOOK LABEL. The label `Jud.` is used for BOTH
Judith (part028, «წიგნი ივდითისა») and Jude (part086). A label-keyed dict
silently collides them — the same class of trap as Zohrab's `Esr.II` prefix,
which merged Ezra into Nehemiah.
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
RAW = Path("C:/Projects/Hexapla-releases/titus_bakar/extracted/bakar_raw.json")
OUT = ASSETS / "ka_bakar.json"

# part number -> app slot. Derived from the dump's own book labels and Georgian
# preambles, checked against the spec's §1 table.
SLOT = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 6, 15: 7,          # Gen..Ruth
    16: 8, 17: 9, 18: 10, 19: 11,                                   # Reg.I-IV
    20: 12, 21: 13,                                                 # Chronicles
    23: 14, 24: 15,                                                 # Ezra, Nehemiah
    29: 16, 30: 17, 31: 18, 33: 19, 34: 20, 35: 21,                 # Esth..Cant
    38: 22, 39: 23,                                                 # Isaiah, Jeremiah
    40: 24, 41: 24,                                                 # Lam.Jer. + Or.Jer. -> Lamentations
    44: 25, 45: 26,                                                 # Ezekiel, Daniel
    46: 27, 47: 28, 48: 29, 49: 30, 50: 31, 51: 32,                 # the Twelve, print order
    52: 33, 53: 34, 54: 35, 55: 36, 56: 37, 57: 38,                 #   = canonical order here
    61: 39, 62: 40, 63: 41, 64: 42, 65: 43, 66: 44, 67: 45, 68: 46, # NT
    69: 47, 70: 48, 71: 49, 72: 50, 73: 51, 74: 52, 75: 53, 76: 54,
    77: 55, 78: 56, 79: 57, 80: 58, 81: 59, 82: 60, 83: 61, 84: 62,
    85: 63, 86: 64, 87: 65,
    25: 66,   # Esr.I_(Esr.III)   = 1 Esdras
    26: 67,   # Esr._III_(Esr._IV) = 2 Esdras   ★ slot empty in every asset
    27: 68,   # Tobit
    28: 69,   # Judith            ⚠ label 'Jud.' collides with Jude (part086)
    36: 70,   # Wisdom
    37: 71,   # Sirach
    42: 72,   # Baruch
    43: 73,   # Epistle of Jeremiah  ★ slot empty in every asset
    22: 74,   # Prayer of Manasses
    58: 75, 59: 76, 60: 77,                                         # 1-3 Maccabees
}
SKIP = {32}          # Od. — the census proved it is a table of contents, not text

# Apparatus the spec §2.3 says to strip. Genuine Georgian punctuation
# ( . , ; : ) stays. `_` is stripped only as the tail of `:_`.
APPARATUS = [("*", None), ("//", None)]


def clean(txt, stats):
    for sym, _ in APPARATUS:
        stats[sym] += txt.count(sym)
        txt = txt.replace(sym, " ")
    stats[":_"] += txt.count(":_")
    txt = txt.replace(":_", ":")
    stats["_"] += txt.count("_")
    txt = txt.replace("_", " ")
    return re.sub(r"\s+", " ", txt).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RAW.read_text(encoding="utf-8"))
    books = raw["books"]
    kjv = json.loads((ASSETS / "en_kjv.json").read_text(encoding="utf-8"))
    slots = [{"name": kjv[i]["name"], "chapters": []} for i in range(83)]
    stats = Counter()
    todo = Counter()
    detail = {}

    for pk in sorted(books, key=lambda x: int(x[4:])):
        n = int(pk[4:])
        if n in SKIP:
            stats["parts_skipped"] += 1
            continue
        if n not in SLOT:
            detail.setdefault("unmapped_parts", []).append((pk, books[pk]["book_label"]))
            continue
        p = books[pk]
        slot = SLOT[n]
        chapters = {}
        for ck, ch in p["chapters"].items():
            if ck == "Prol." or ck.startswith("Prol."):
                # Patristic/Euthalian prologues — 26 of them across the NT.
                # NOT scripture; excluded from the verse flow. They are real
                # content in the print and could later ship the way the
                # Vulgate/Zohrab rubrics do, but that is a separate decision.
                todo["nt_prologues_excluded"] += 1
                continue
            if ck == "":
                todo["unlabelled_chapter_blocks"] += 1
                detail.setdefault("unlabelled", []).append((p["book_label"],))
                continue
            if not ck.isdigit():
                todo["non_numeric_chapter"] += 1
                detail.setdefault("nonnum_ch", []).append((p["book_label"], ck))
                continue
            verses = {}
            for vk, txt in ch["verses"].items():
                t = clean(txt, stats)
                if "|" in t:
                    todo["pipe_merged_units"] += 1
                    detail.setdefault("pipes", []).append((p["book_label"], ck, vk))
                if vk.isdigit():
                    verses[int(vk)] = t
                else:
                    todo["non_numeric_verse"] += 1
                    detail.setdefault("nonnum_v", []).append((p["book_label"], ck, vk))
            if verses:
                chapters[int(ck)] = verses
        if not chapters:
            continue
        # Lam.Jer. (part040) + Or.Jer. (part041) share slot 24; Or.Jer. becomes
        # chapter 5 per spec §6 (it IS KJV Lamentations 5 textually).
        existing = slots[slot].get("_ch")
        if existing:
            # Or.Jer. (part041) already carries its own chapter label "5" —
            # TITUS itself numbers the Prayer of Jeremiah as Lamentations 5,
            # exactly as the Armenian Zohrab does. Merge at the printed
            # numbers; offsetting by the host book's length produced a
            # 9-chapter Lamentations, which the KJV-grid check caught.
            for c, vs in chapters.items():
                assert c not in existing, (
                    "chapter %d collides merging part%03d into slot %d" % (c, n, slot))
                existing[c] = vs
        else:
            slots[slot]["_ch"] = chapters
        if p.get("book_preamble"):
            stats["headings_available"] += 1

    # positional lists
    total = 0
    for s in slots:
        chs = s.pop("_ch", None)
        if not chs:
            continue
        out = []
        for c in range(1, max(chs) + 1):
            vs = chs.get(c, {})
            if not vs:
                out.append([])
                continue
            lst = [""] * max(vs)
            for num, t in vs.items():
                lst[num - 1] = t
            total += sum(1 for x in lst if x)
            out.append(lst)
        s["chapters"] = out

    print("apparatus stripped : %s" % {k: v for k, v in stats.items() if k in ("*", "//", ":_", "_")})
    print("verses placed      : %d" % total)
    print("books with text    : %d / 83" % sum(1 for s in slots if any(s["chapters"])))
    print()
    print("CURATION SURFACE (reported, not done):")
    for k, v in todo.most_common():
        print("   %-28s %d" % (k, v))
    for k in ("unmapped_parts", "pipes", "nonnum_ch", "unlabelled"):
        if k in detail:
            print("   %s: %s" % (k, detail[k][:8]))

    # KJV-grid comparison, so the curation work list is concrete
    print()
    print("CHAPTER-COUNT vs KJV (canonical books only):")
    bad = 0
    for i in range(66):
        if not any(slots[i]["chapters"]):
            continue
        a, b = len(slots[i]["chapters"]), len(kjv[i]["chapters"])
        if a != b:
            bad += 1
            print("   %-18s bakar %3d  kjv %3d" % (kjv[i]["name"], a, b))
    print("   books off-grid: %d" % bad)

    if args.dry_run:
        print("\n[dry-run] nothing written")
        return
    OUT.write_text(json.dumps(slots, ensure_ascii=False), encoding="utf-8")
    print("\nwrote %s (%.1f MB)" % (OUT, OUT.stat().st_size / 1e6))


if __name__ == "__main__":
    main()
