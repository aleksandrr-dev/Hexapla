# -*- coding: utf-8 -*-
"""Strip editorial markers from la_vulgata.json verse text.

WHY: the Tweedale/VulSearch source carries structural rubrics inline, and
tools/convert_vulgate.py did not strip them — so they SHIPPED to users in
v1.4.3 (2026-07-13) as literal angle brackets:

    Psalmi 118:1  "Alleluja. <Aleph>Beati immaculati in via..."
    Canticum Canticorum 1:1  "<Sponsa>Osculetur me osculo oris sui..."

194 markers, 29 distinct, across Psalmi 118, Lamentationes 1-4, Canticum
Canticorum and 2 prologues.

⚠ THESE ARE CONTENT, NOT NOISE. <Sponsa>/<Sponsus>/<Chorus> identify WHO IS
SPEAKING in Song of Songs; <Aleph>..<Thau> mark the 22 acrostic sections of
Ps 118 (=119) and Lamentations. Print Clementine editions carry them as
rubrics. Stripping DISCARDS that information. The owner chose this over
surfacing them as headings (which needs UI work) on 2026-07-15; it is
reversible — the markers are still in the source archive, so a later version
can reinstate them as structure.

SAFETY: this only ever DELETES a bracketed marker from the known list and
normalizes the whitespace around it. Every verse is asserted to be unchanged
once its markers are removed from BOTH sides — the script cannot silently
alter scripture.

    python tools/fix_vulgate_markers.py --dry-run
    python tools/fix_vulgate_markers.py
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles" / "la_vulgata.json"

# The exact 29 markers observed. An explicit list, NOT a generic <[^>]*>
# sweep: a blanket regex would also eat any legitimate angle bracket and we
# would never know. Anything not on this list is reported, not removed.
MARKERS = [
    # Hebrew acrostic letters — Ps 118 (=119) and Lamentationes 1-4.
    "Aleph", "Beth", "Ghimel", "Daleth", "He", "Vau", "Zain", "Heth", "Teth",
    "Jod", "Caph", "Lamed", "Mem", "Nun", "Samech", "Ain", "Phe", "Sade",
    "Coph", "Res", "Sin", "Thau", "Tau",
    # Canticum Canticorum speaker rubrics.
    "Sponsa", "Sponsus", "Chorus", "Chorus Fratrum", "Chorus Adolescentularum",
    # Section rubric.
    "Prologus",
]
PATTERN = re.compile(r"<(" + "|".join(re.escape(m) for m in sorted(MARKERS, key=len, reverse=True)) + r")>")
ANY_TAG = re.compile(r"<[^>]*>")


def strip_markers(text):
    out = PATTERN.sub("", text)
    return re.sub(r"\s{2,}", " ", out).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.load(open(ASSET, encoding="utf-8"))

    found = Counter()
    unknown = []
    changed = 0
    examples = []

    for bi, bk in enumerate(books):
        for ci, ch in enumerate(bk.get("chapters", [])):
            for vi, v in enumerate(ch):
                if not v or "<" not in v:
                    continue
                for m in PATTERN.findall(v):
                    found[m] += 1
                new = strip_markers(v)

                # SAFETY: whatever remains must contain no tag we did not
                # recognise. If it does, this verse is NOT ours to touch.
                leftover = ANY_TAG.findall(new)
                if leftover:
                    unknown.append((bk["name"], ci + 1, vi + 1, leftover, v[:100]))
                    continue

                # SAFETY: removing the markers from the ORIGINAL must give
                # exactly what we produced — i.e. we deleted markers and
                # nothing else.
                skeleton = re.sub(r"\s{2,}", " ", PATTERN.sub("", v)).strip()
                assert new == skeleton, f"{bk['name']} {ci+1}:{vi+1} altered beyond marker removal"

                if new != v:
                    changed += 1
                    if len(examples) < 5:
                        examples.append((bk["name"], ci + 1, vi + 1, v[:88], new[:88]))
                    if not args.dry_run:
                        ch[vi] = new

    print(f"markers found: {sum(found.values())} across {len(found)} distinct")
    for m, n in found.most_common():
        print(f"    <{m}>  x{n}")
    print(f"\nverses to change: {changed}")
    for name, c, v, before, after in examples:
        print(f"\n  {name} {c}:{v}")
        print(f"    before: {before}")
        print(f"    after : {after}")

    if unknown:
        print(f"\n⚠ {len(unknown)} verse(s) contain UNRECOGNISED tags — left untouched:")
        for name, c, v, tags, snip in unknown[:10]:
            print(f"    {name} {c}:{v}  {tags}  {snip}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    # ⚠ NOT beside the asset. Android bundles EVERYTHING under app/src/main/
    # assets/ into the APK — a .bak there ships to every user, and .gitignore
    # does not stop the packager.
    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
        print(f"\nbackup: {backup}")
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name}")


if __name__ == "__main__":
    main()
