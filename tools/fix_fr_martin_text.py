# -*- coding: utf-8 -*-
"""Repair scrape and OCR defects in fr_martin.json (Bible Martin 1744, tid
"mar"). The ASSET is fixed (Android and the web build both read it), so the
reader and the narration see the same text. Dry run by default.

    python tools/fix_fr_martin_text.py            # dry run: every change shown
    python tools/fix_fr_martin_text.py --apply    # write, re-read, re-check

Found 2026-10-22 (s67) while preparing the fr render (narrate.py would have
SPOKEN all of it):

1. SCRAPE JUNK - 36 book-final verses end in the source web page's chrome:
   a run of «=====» (22), «Retournez au Début =====» (8), or «Retournez au
   Début This Website is Hosted by ../../lilacsandbutterflies/images/
   EClilacsbanner.gif =====» (6). Stripped from the first junk token to the
   end. The list of verses is derived, then ASSERTED to be exactly 36.

2. OCR - 16 single-site substitutions, every one length-preserving, each
   listed with its verse and asserted to occur exactly once there:
   «1’»->«l’», «0r»->«Or», «0n»->«On», «I1»/«II»->«Il», «peup1e», «voic1»,
   «aujourd’hu1», «¨ô»->« ô», U+0096 (C1 control, a cp1252 en dash)->«-».

NOT FIXED HERE (structural, needs the versemap rebuilt; owner question):
Ps 69, 102, 108, 140 each have one MERGED verse (Ps 102:1 even carries the
printed «2.»), so every later verse of the psalm sits one slot early and the
last slot is empty. docs/ASSET_DEFECTS.md lists them as benign TAILs.

Controls (any failure writes nothing, rc 2): the file round-trips byte-exact
through json (ensure_ascii=False, separators=(",", ":")); the shape (books x
chapters x verses) is unchanged; every verse not listed is byte-identical;
after the fix no verse contains «=», «Retournez au Début», «Website», a digit,
U+0096, «¨» or a standalone «II».
"""
import argparse
import json
import re
import sys
from pathlib import Path

ASSET = Path(__file__).resolve().parent.parent / "app/src/main/assets/bibles/fr_martin.json"
DUMP = dict(ensure_ascii=False, separators=(",", ":"))

JUNK = re.compile(r"\s*(?:Retournez au Début\s*)?(?:This Website is Hosted by \S+\s*)?=+\s*$")
JUNK_EXPECTED = 36

# (book index, chapter, verse, old, new) - 1-based chapter/verse
OCR = [
    (1, 35, 21, "1’offrande", "l’offrande"),
    (2, 19, 6, "II se", "Il se"),
    (3, 9, 14, "II y", "Il y"),
    (8, 9, 9, "0r c’était", "Or c’était"),
    (8, 11, 13, "0n ne", "On ne"),
    (18, 136, 17, "I1 a", "Il a"),
    (19, 16, 25, "II y", "Il y"),
    (23, 39, 18, "1’Eternel", "l’Eternel"),
    (25, 7, 20, "II avait", "Il avait"),
    (40, 1, 15, "1’Evangile", "l’Evangile"),
    (43, 8, 9, "peup1e", "peuple"),
    (45, 2, 2, "Jésus\u0096Christ", "Jésus-Christ"),
    (45, 3, 15, "1’oeuvre", "l’oeuvre"),
    (57, 10, 7, "voic1,", "voici,"),
    (57, 13, 8, "aujourd’hu1,", "aujourd’hui,"),
    (65, 3, 15, ";¨ô", "; ô"),
]
# Ps 102:1's «2.Eternel» is the merged-verse defect above, left alone.
RESIDUE = re.compile(r"=|Retournez au Début|Website|\u0096|¨|\bII\b")
DIGIT_OK = {(18, 102, 1)}


def plan(books):
    changes = {}
    for bi, ch, vs, old, new in OCR:
        v = changes.get((bi, ch, vs), books[bi]["chapters"][ch - 1][vs - 1])
        if v.count(old) != 1:
            sys.exit(f"CONTROL: {books[bi]['name']} {ch}:{vs} has {v.count(old)}x {old!r}, want 1")
        if len(old) != len(new):
            sys.exit(f"CONTROL: {old!r}->{new!r} is not length-preserving")
        changes[(bi, ch, vs)] = v.replace(old, new)
    junk = 0
    for bi, b in enumerate(books):
        for ci, c in enumerate(b["chapters"]):
            for vi, v in enumerate(c):
                key = (bi, ci + 1, vi + 1)
                cur = changes.get(key, v)
                m = JUNK.search(cur)
                if m and m.group(0).strip():
                    junk += 1
                    changes[key] = cur[:m.start()]
    if junk != JUNK_EXPECTED:
        sys.exit(f"CONTROL: {junk} junk verses, expected {JUNK_EXPECTED}")
    return changes, junk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    raw = ASSET.read_text(encoding="utf-8")
    books = json.loads(raw)
    if json.dumps(books, **DUMP) != raw:
        sys.exit("CONTROL: asset does not round-trip byte-exact; refusing")
    shape = [[len(c) for c in b["chapters"]] for b in books]
    changes, junk = plan(books)
    for (bi, ch, vs), new in sorted(changes.items()):
        old = books[bi]["chapters"][ch - 1][vs - 1]
        tail = old[len(new):] if old.startswith(new) else None
        print(f"{books[bi]['name']} {ch}:{vs}")
        if tail is not None:
            print(f"   strip {tail[:90]!r}{'...' if len(tail) > 90 else ''}  -> ends {new[-40:]!r}")
        else:
            print(f"   {old!r}\n-> {new!r}")
        books[bi]["chapters"][ch - 1][vs - 1] = new
    bad = []
    for bi, b in enumerate(books):
        for ci, c in enumerate(b["chapters"]):
            for vi, v in enumerate(c):
                if RESIDUE.search(v) or (re.search(r"\d", v) and (bi, ci + 1, vi + 1) not in DIGIT_OK):
                    bad.append((b["name"], ci + 1, vi + 1, v[:80]))
    if bad:
        for x in bad:
            print("RESIDUE", x)
        sys.exit(f"CONTROL: {len(bad)} verse(s) still carry a defect; nothing written")
    if [[len(c) for c in b["chapters"]] for b in books] != shape:
        sys.exit("CONTROL: shape changed; nothing written")
    print(f"\n{len(changes)} verse(s) changed: {junk} junk tails, {len(OCR)} OCR sites; "
          f"0 residue; shape unchanged")
    if not a.apply:
        print("DRY RUN - nothing written (--apply to write)")
        return
    ASSET.write_text(json.dumps(books, **DUMP), encoding="utf-8", newline="")
    again = json.loads(ASSET.read_text(encoding="utf-8"))
    if again != books:
        sys.exit("CONTROL: re-read differs from what was written")
    print(f"WROTE {ASSET} - now run check_asset_integrity.py --update --note ...")


if __name__ == "__main__":
    main()
