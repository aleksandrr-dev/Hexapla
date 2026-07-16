# -*- coding: utf-8 -*-
"""Repair de_luther.json from its own clean upstream.

THE DEFECT (audited 2026-07-15, full-corpus diff — not a sample):
de_luther.json is an UNPROOFREAD OCR of the Bolsinger/luther-bibel-1545.de
digitization. It has shipped since v1.1. Census over 4,010,960 chars of German:

    ä = 0        (master: 11,719)
    ö = 1        (master: 11,189)
    Ä, Ö, Ü = 0  (master: 1,050 / 260 / 306)

Zero ä in a four-million-character German Bible is categorically impossible.
23,508 of 30,964 comparable verses (75.9%) are damaged; all 66 books, none
below 50%. 41,981 of 56,109 accented characters destroyed (74.8%).

    über→uber (1,553)   soll→soil (1,499)   König→Konig (1,201)
    um→urn (845)        allen→alien (699)   für→fur (684)
    daß→dafi/dad/daü    Salomo→Saiomo       Blut→Biut

Including the owner's own litmus verse — 1 Tim 3:16 ships as
"Und kundlich GRAFT ist das gottselige Geheimnis" (groß → graft).

WHY A MARKUP REGEX MISSED IT: 13,781 verses differ from the master ONLY by
stripped umlauts — no entity, no tag, nothing greppable. The initial scan found
20 verses. The real number is 23,508: an undercount of ~1,175x. Silent
corruption is invisible to pattern-matching; it needs a reference text.

THE SOURCE: Zefania SF_2009-01-20_GER_LUTH1545 (sourceforge.net/projects/
zefania-sharp, Bibles/GER/Lutherbibel/Luther 1545) — the SAME digitization the
app already ships, unmangled. 66 books, 31,170 verses, ä=11,719. CrossWire
ships the same text as GerLut1545. Since the app already ships this
transcription, using its clean upstream adds ZERO new licensing exposure.

LITMUS on the master, verified before use: 1 Tim 3:16 "GOtt ist offenbaret im
Fleisch" PASS; Comma present; Acts 8:37 present; Rom 16:24 present; Jn 1:1 PASS.
Lk 2:33 "sein Vater und Mutter" is Luther's own reading, already accepted for
de_luther in CLAUDE.md. This is a pure character-fidelity repair — no
doctrinal change whatsoever.

SAFETY: a verse is replaced ONLY when its skeleton (lowercased, de-umlauted,
alphanumeric-only) matches the master's at >= MIN_RATIO. Anything below that
is LEFT EXACTLY AS-IS. The script can restore characters; it cannot move or
invent scripture.

⚠ TWO TRAPS, both hit while writing this — do not reintroduce either:

1. difflib.SequenceMatcher's AUTOJUNK. For sequences over 200 elements it
   treats any element in >1% of them as "popular" and ignores it. Our skeletons
   are 250+ char letter strings, so 'e'/'n'/'r' get junked and the ratio
   collapses to noise: "auf dafi der HERR sein Wort erwecke" vs "auf daß der
   HErr sein Wort erwecke" scored 0.03. MUST pass autojunk=False.

2. GENUINE VERSIFICATION OFFSETS EXIST and a length check will not catch them.
   de_luther keeps German-native numbering (CLAUDE.md), so e.g. 2. Samuel 19 is
   off by one against the master: our 19:7 IS the master's 19:8. Length ratio
   1.06 — a length test waves it straight through. Only the text ratio
   distinguishes "same verse, mangled" from "different verse entirely". This is
   why the ratio gate cannot simply be lowered to catch heavy damage.

    python tools/fix_de_luther.py --master <path-to-xml> --dry-run
    python tools/fix_de_luther.py --master <path-to-xml>
"""
import argparse
import difflib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "de_luther.json")
MIN_RATIO = 0.85          # fast path: clearly the same verse
DAMAGED_FLOOR = 0.45      # below the fast path but still the same verse
NEIGHBOUR_MARGIN = 0.25   # a neighbour beating us by this much => offset
ACCENTED = "äöüßÄÖÜ"

# Classifying sub-MIN_RATIO pairs — measured over all 100 of them, 2026-07-15.
# The two populations do not overlap, and the discriminator is NOT a threshold:
#
#   OFFSET  (78): ratio 0.09-0.34 vs same coords, but a NEIGHBOUR scores
#                 0.99-1.00. All of 2. Samuel 19 is shifted by +1 — our 19:1 is
#                 the master's 19:2, straight down the chapter. de_luther keeps
#                 German-native numbering (CLAUDE.md), so this is EXPECTED.
#                 Repairing these by coordinate would overwrite scripture with
#                 the neighbouring verse.
#   DAMAGED (22): ratio 0.45-0.82, no neighbour matches better. Same verse,
#                 mangled past the fast path, e.g.
#                 "Auge urn Auge ... Fufi urn Fuß" (0.82),
#                 "sollt ihrtun ... mannlich" (0.57).
#
# So: ask whether a NEIGHBOUR fits better before repairing. Length alone cannot
# do this — 2. Samuel 19:7's offset pair has a length ratio of 1.06.

# OCR mangles ß into many things, so the skeleton drops it entirely rather than
# mapping it to one letter — comparing "dafi"/"dad"/"daü" against "daß" only
# works if the contested character is absent from both sides.
_FOLD = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "Ä": "a", "Ö": "o",
                       "Ü": "u", "ß": "", "ſ": "s"})


def skeleton(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().translate(_FOLD))


def load_master(path):
    root = ET.parse(path).getroot()
    out = {}
    for bk in root.findall(".//BIBLEBOOK"):
        b = int(bk.get("bnumber"))
        for ch in bk.findall("CHAPTER"):
            c = int(ch.get("cnumber"))
            for v in ch.findall("VERS"):
                out[(b - 1, c - 1, int(v.get("vnumber")) - 1)] = \
                    "".join(v.itertext()).strip()
    return out


def census(books):
    c = Counter()
    n = 0
    for bk in books:
        for ch in bk.get("chapters", []):
            for v in ch:
                if not v:
                    continue
                n += len(v)
                for x in v:
                    if x in ACCENTED:
                        c[x] += 1
    return c, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True, help="Zefania LUTH1545 XML")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.load(open(ASSET, encoding="utf-8"))
    master = load_master(args.master)
    print(f"master: {len(master):,} verses")

    before_c, before_n = census(books)
    print(f"before: accented {sum(before_c.values()):,} "
          f"({sum(before_c.values())/before_n*1000:.2f}/1000)  {dict(before_c)}")

    def ratio(a, b):
        # autojunk=False is LOAD-BEARING — see the header. With it on,
        # near-identical 250-char verses score 0.03.
        return difflib.SequenceMatcher(None, skeleton(a), skeleton(b),
                                       autojunk=False).ratio()

    repaired = repaired_damaged = skipped_missing = identical = 0
    skipped_offset = skipped_unclear = 0
    examples, misaligned = [], []

    for bi, bk in enumerate(books):
        for ci, ch in enumerate(bk.get("chapters", [])):
            for vi, v in enumerate(ch):
                if not v:
                    continue
                m = master.get((bi, ci, vi))
                if m is None:
                    skipped_missing += 1
                    continue
                if v == m:
                    identical += 1
                    continue

                r = ratio(v, m)
                if r < MIN_RATIO:
                    # Does a NEIGHBOUR fit better? That is the offset
                    # signature, and the only reliable way to tell a shifted
                    # verse from a badly-mangled one. A length check cannot:
                    # 2. Samuel 19:7's offset pair has a length ratio of 1.06.
                    best_d, best_r = None, r
                    for d in (-2, -1, 1, 2):
                        mn = master.get((bi, ci, vi + d))
                        if mn:
                            rn = ratio(v, mn)
                            if rn > best_r:
                                best_d, best_r = d, rn
                    if best_d is not None and best_r > r + NEIGHBOUR_MARGIN:
                        skipped_offset += 1
                        if len(misaligned) < 6:
                            misaligned.append((bk["name"], ci + 1, vi + 1, r,
                                               best_d, best_r))
                        continue
                    if r < DAMAGED_FLOOR:
                        skipped_unclear += 1
                        continue
                    repaired_damaged += 1

                if len(examples) < 6 and any(x in m for x in ACCENTED):
                    examples.append((bk["name"], ci + 1, vi + 1, v[:78], m[:78]))
                repaired += 1
                if not args.dry_run:
                    ch[vi] = m

    print(f"\n  repaired              : {repaired:,}"
          f"  (incl. {repaired_damaged} below the {MIN_RATIO} fast path)")
    print(f"  already identical     : {identical:,}")
    print(f"  skipped, no master    : {skipped_missing:,}")
    print(f"  skipped, VERSIFICATION OFFSET: {skipped_offset:,}  "
          f"(neighbour fits better — repairing would overwrite scripture)")
    print(f"  skipped, unclear      : {skipped_unclear:,}  "
          f"(< {DAMAGED_FLOOR}, no better neighbour)")

    for name, c, v, b, a in examples:
        print(f"\n  {name} {c}:{v}")
        print(f"    before: {b}")
        print(f"    after : {a}")

    if misaligned:
        print(f"\n  versification offsets left untouched:")
        for name, c, v, r, d, br in misaligned:
            print(f"    {name} {c}:{v}  same-coords r={r:.2f}, "
                  f"neighbour {d:+d} r={br:.2f}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    after_c, after_n = census(books)
    print(f"\nafter : accented {sum(after_c.values()):,} "
          f"({sum(after_c.values())/after_n*1000:.2f}/1000)  {dict(after_c)}")

    # ⚠ NOT beside the asset. Android bundles EVERYTHING under app/src/main/
    # assets/ into the APK — a .bak there ships ~4 MB of the corrupt text we
    # just repaired to every user, and .gitignore does not stop the packager.
    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
        print(f"backup: {backup}")
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name}")


if __name__ == "__main__":
    main()
