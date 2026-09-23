# -*- coding: utf-8 -*-
"""Restore Псалом 144's title to verse 1 in ru_synodal.json.

THE DEFECT: the converter lifted «<title type="psalm">Хвала Давида.</title>»
out of Псалом 144 and appended it to the END of Псалом 143:15 — the previous
psalm's last verse. So Ps 143 ends with the next psalm's title, and Ps 144
opens with no title at all.

WHY INLINE IN v1, NOT A NEW VERSE — the question that decides whether this is
safe. Cross-checked against the app's OWN Clementine Vulgate, same LXX psalter
tradition:

    Vulgate Ps 144:1  "Laudatio ipsi David. Exaltabo te, Deus meus rex..."   21 verses
    Synodal Ps 144:1  "Буду превозносить Тебя, Боже мой, Царь [мой]..."      21 verses

«Laudatio ipsi David» IS «Хвала Давида», carried INLINE at the head of verse 1,
and the Vulgate's verse count matches ours exactly. The Vulgate's Ps 143 also
ends cleanly at "Beatum dixerunt populum" with no trailing title, confirming
ours is the misplaced one. Hebrew Ps 145 (= Synodal 144) likewise has 21 verses
with «תהלה לדוד» inside v1.

So this restores text WITHOUT changing any verse count. That matters: a
versification change would ripple into versemap.json, bookmarks, notes and
highlights (CLAUDE.md — the Synodal LXX psalter is already special-cased
there). This edit touches none of that.

NOT DONE HERE, flagged for the owner: the Church Slavonic asset (cu_elizabeth)
ALSO lacks the title at its Ps 144:1, and Псалом 145:1 reads "Хвали, душа моя,
Господа." where the Synodal conventionally opens "Аллилуия. Хвали, душа моя,
Господа." There may be a WIDER title-dropping defect across the psalter in both
assets. This script fixes only the one case with hard evidence.

    python tools/fix_psalm144_title.py --dry-run
    python tools/fix_psalm144_title.py
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "ru_synodal.json")
PSALMS = 18
TITLE = "Хвала Давида."
NOTE = re.compile(r"\s*\{Заголовок следующего псалма:\s*([^{}]*)\}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.load(open(ASSET, encoding="utf-8"))
    ps = books[PSALMS]["chapters"]

    n143, n144 = len(ps[142]), len(ps[143])
    v143_15, v144_1 = ps[142][-1], ps[143][0]

    print(f"Псалом 143: {n143} verses   Псалом 144: {n144} verses")
    print(f"\n  143:15 before: {v143_15[:120]}")
    print(f"  144:1  before: {v144_1[:120]}")

    m = NOTE.search(v143_15)
    if not m:
        sys.exit("\nno title note on 143:15 — already fixed, or the note format changed")
    if TITLE not in m.group(1):
        sys.exit(f"\nunexpected note body {m.group(1)!r} — refusing to guess")
    if v144_1.startswith(TITLE):
        sys.exit("\n144:1 already carries the title — nothing to do")

    new_143_15 = re.sub(r"\s{2,}", " ", NOTE.sub("", v143_15)).strip()
    new_144_1 = f"{TITLE} {v144_1}"

    print(f"\n  143:15 after : {new_143_15[:120]}")
    print(f"  144:1  after : {new_144_1[:120]}")

    # SAFETY: nothing but the title moves, and no verse is created or destroyed.
    assert NOTE.sub("", v143_15).strip() == new_143_15, "143:15 altered beyond note removal"
    assert new_144_1.endswith(v144_1), "144:1 altered beyond the title prefix"
    assert len(ps[142]) == n143 and len(ps[143]) == n144, "verse count changed!"

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    ps[142][-1] = new_143_15
    ps[143][0] = new_144_1
    assert len(books[PSALMS]["chapters"][142]) == n143
    assert len(books[PSALMS]["chapters"][143]) == n144

    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".psalm144.bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
        print(f"\nbackup: {backup}")
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name}  (verse counts unchanged: 143={n143}, 144={n144})")


if __name__ == "__main__":
    main()
