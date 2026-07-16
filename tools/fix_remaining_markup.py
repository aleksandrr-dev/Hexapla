# -*- coding: utf-8 -*-
"""Remove the last two markup-debris defects found by audit_asset_markup.py.

1. en_kjv.json — "Additions to Esther" 10:4 opens with an orphaned closing tag:
       "</title> Then Mardocheus said, God hath done these things."
   The opening half was almost certainly the KJV apocrypha's editorial rubric
   ("The rest of the chapters of the book of Esther, which are found neither in
   the Hebrew, nor in the Chaldee..."), an editor's heading, not scripture —
   so deleting the debris loses nothing scriptural. Apocrypha slot, outside the
   66-book canonical grid: bookmarks/versemap untouched.

2. zh_cuv_s.json + zh_cuv_t.json — Joshua 24:14 carries a leaked annotation
   marker, twice, splitting the idiom 诚心实意 ("in sincerity and in truth"):
       诚心<WAHb>实意地<WAHb> 事奉他
   Present in BOTH scripts at the same verse — the defect predates our OpenCC
   t2s step; it is in the upstream Traditional source. Removing the tags (and
   the stray ASCII space the second one carries) restores the idiom exactly.

Owner approved 2026-07-15. Same safety pattern as the other fixes: match the
exact known markers only, assert the expected counts and locations, refuse
anything unexpected, back up OUTSIDE app/src/main/assets (Android bundles that
whole tree into the APK).

    python tools/fix_remaining_markup.py --dry-run
    python tools/fix_remaining_markup.py
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSETS = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"
BACKUPS = Path("C:/Projects/Hexapla-releases/asset-backups")


def fix_kjv(books, dry):
    hits = []
    for bi, bk in enumerate(books):
        for ci, ch in enumerate(bk.get("chapters", [])):
            for vi, v in enumerate(ch):
                if v and "</title>" in v:
                    hits.append((bi, ci, vi, bk.get("name", "?")))
    if len(hits) != 1:
        sys.exit(f"en_kjv: expected exactly 1 '</title>', found {len(hits)} — refusing")
    bi, ci, vi, name = hits[0]
    if name != "Additions to Esther" or (ci, vi) != (9, 3):
        sys.exit(f"en_kjv: tag at unexpected location {name} {ci+1}:{vi+1} — refusing")
    old = books[bi]["chapters"][ci][vi]
    new = old.replace("</title>", "", 1).strip()
    assert new in old and "</title>" not in new
    print(f"  {name} 10:4")
    print(f"    before: {old[:90]}")
    print(f"    after : {new[:90]}")
    if not dry:
        books[bi]["chapters"][ci][vi] = new
    return True


def fix_cuv(books, fname, dry):
    hits = []
    for bi, bk in enumerate(books):
        for ci, ch in enumerate(bk.get("chapters", [])):
            for vi, v in enumerate(ch):
                if v and "<WAHb>" in v:
                    hits.append((bi, ci, vi, bk.get("name", "?"), v.count("<WAHb>")))
    if len(hits) != 1 or hits[0][4] != 2:
        sys.exit(f"{fname}: expected 1 verse with 2 '<WAHb>', got {hits} — refusing")
    bi, ci, vi, name, _ = hits[0]
    if (ci, vi) != (23, 13):
        sys.exit(f"{fname}: marker at unexpected location {name} {ci+1}:{vi+1} — refusing")
    old = books[bi]["chapters"][ci][vi]
    # The second marker carries a stray ASCII space: "<WAHb> 事奉他".
    new = old.replace("<WAHb> ", "").replace("<WAHb>", "")
    assert "<" not in new and " " not in new.replace("， ", "，")
    print(f"  {name} 24:14")
    print(f"    before: {old[:80]}")
    print(f"    after : {new[:80]}")
    if not dry:
        books[bi]["chapters"][ci][vi] = new
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    BACKUPS.mkdir(parents=True, exist_ok=True)

    for fname, fixer in [("en_kjv.json", fix_kjv),
                         ("zh_cuv_s.json", lambda b, d: fix_cuv(b, "zh_cuv_s", d)),
                         ("zh_cuv_t.json", lambda b, d: fix_cuv(b, "zh_cuv_t", d))]:
        path = ASSETS / fname
        books = json.load(open(path, encoding="utf-8"))
        n_books = len(books)
        n_verses = sum(len(c) for bk in books for c in bk["chapters"])
        print(f"=== {fname} ===")
        fixer(books, args.dry_run)
        assert len(books) == n_books
        assert sum(len(c) for bk in books for c in bk["chapters"]) == n_verses
        if not args.dry_run:
            bak = BACKUPS / (fname + ".bak")
            if not bak.exists():
                shutil.copy2(path, bak)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
            print(f"    wrote {fname} (backup: {bak.name})")
        print()
    if args.dry_run:
        print("(dry run — nothing written)")


if __name__ == "__main__":
    main()
