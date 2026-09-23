# -*- coding: utf-8 -*-
"""Normalize ' - ' (hyphen-as-dash) to ' — ' (em dash) in ru_synodal.json.

THE DEFECT (owner spotted it at Пс 22:1 «Господь - Пастырь мой», 2026-07-16):
the digitization is internally INCONSISTENT — 2,056 dashes typed as
space-hyphen-space alongside 1,083 proper spaced em dashes (and 0 en dashes).
Print Synodal uses «—». Sampled contexts confirm every ' - ' is a real тире
(sentence dash), not a hyphen: «повелел Иисусу сказать народу - так, как…».

Normalization: ' - ' -> ' — ' only (exact three-character pattern). Unspaced
em dashes and word-internal hyphens are untouched. Both are one character
between two spaces, so EVERY VERSE'S LENGTH IS UNCHANGED — asserted per verse.

    python tools/fix_ru_dashes.py --dry-run
    python tools/fix_ru_dashes.py
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "ru_synodal.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    books = json.load(open(ASSET, encoding="utf-8"))
    replaced = verses_touched = 0
    example = None
    for bk in books:
        for ch in bk["chapters"]:
            for i, v in enumerate(ch):
                if not v or " - " not in v:
                    continue
                new = v.replace(" - ", " — ")
                assert len(new) == len(v), "length changed — refusing"
                replaced += v.count(" - ")
                verses_touched += 1
                if example is None:
                    example = (v[:70], new[:70])
                if not args.dry_run:
                    ch[i] = new

    print(f"dashes normalized: {replaced:,} across {verses_touched:,} verses")
    if example:
        print(f"  before: {example[0]}")
        print(f"  after : {example[1]}")
    if args.dry_run:
        print("(dry run — nothing written)")
        return

    backup_dir = Path("C:/Projects/Hexapla-releases/asset-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (ASSET.name + ".predash.bak")
    if not backup.exists():
        shutil.copy2(ASSET, backup)
    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {ASSET.name}")


if __name__ == "__main__":
    main()
