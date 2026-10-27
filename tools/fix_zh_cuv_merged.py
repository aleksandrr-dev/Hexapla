# -*- coding: utf-8 -*-
"""Blank the bare «a» slots in zh_cuv_s / zh_cuv_t (the CUV's merged verses).

    python tools/fix_zh_cuv_merged.py                  # DRY RUN (the default)
    python tools/fix_zh_cuv_merged.py --limit 3        # dry run, first 3 slots
    python tools/fix_zh_cuv_merged.py --apply          # write both assets
    python tools/fix_zh_cuv_merged.py --selftest       # exit 0
    HEXAPLA_NO_ZHFIX=1 python tools/fix_zh_cuv_merged.py --selftest   # exit 1

WHAT THE «a» IS. The Chinese Union Version translates some verse groups as one
unit (Num 1:20-21, Exod 38:14-15, ...) and prints the text once. The source
this asset came from kept the KJV slot grid and put a literal «a» in the slot
the merge left over; the reader rendered it as «15 a». The scripture is NOT
missing - it is in the slot BEFORE, which carries both verses.

WHAT THIS DOES - the same shape the ja_meiji range repair shipped
(docs/ASSET_DEFECTS.md, 2026-09-20): the text stays in the first slot of its
range, the tail slot becomes EMPTY, no address moves. The reader skips a
blank verse, so the CUV's own printing (one block for the group) is what
shows. Nothing is re-worded, moved or taken from another translation.

GATES - a slot is changed only if ALL hold, else it is REFUSED and printed:
  1. it is exactly «a» (after strip);
  2. the SAME address in the sibling asset (_s <-> _t) is also «a» - two
     independent script conversions agree it is a merge placeholder;
  3. the first populated slot before it (before the whole «a» run, for a
     three-verse group like Ps 8:6-8) is longer than the chapter's median
     verse - the witness that it carries the merged verses' text.

Backups go to C:/Projects/Hexapla-releases/_work/, never next to the asset
(anything in assets/bibles/ is packaged into the APK). The asset is re-read
after the write and the census re-run in-process: 0 «a» slots or exit 1.

HEXAPLA_NO_ZHFIX=1 disables gate 3's witness (every slot passes it), so the
selftest's planted non-merge «a» is changed and the selftest MUST fail.
"""
import argparse
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ASSETS = Path(__file__).parent.parent / "app/src/main/assets/bibles"
PAIR = ("zh_cuv_s", "zh_cuv_t")
BACKUP_DIR = Path("C:/Projects/Hexapla-releases/_work")
# Hand-ruled merges gate 3 cannot witness (the group is short), each read in
# BOTH scripts: (book index, chapter, verse) of the «a» slot, 1-based ch/v.
# Eph 6:3 - v2 «要孝敬父母，使你得福，在世长寿。」这是第一条带应许的诫命» already
#   carries v3's «that it may be well with thee ... live long» (2026-09-24).
RULED = {(48, 6, 3)}


def plan(a, b):
    """-> (changes, refused) for asset `a` given its sibling `b`.
    changes/refused: [(bi, ci, vi, why)] with 0-based indices."""
    changes, refused = [], []
    for bi, book in enumerate(a):
        for ci, ch in enumerate(book["chapters"]):
            lens = [len(v.strip()) for v in ch if v.strip() and v.strip() != "a"]
            med = statistics.median(lens) if lens else 0
            for vi, v in enumerate(ch):
                if v.strip() != "a":
                    continue
                try:
                    sib = b[bi]["chapters"][ci][vi].strip()
                except (IndexError, KeyError):
                    sib = None
                # A three-verse group (Ps 8:6-8) leaves two «a» in a row: the
                # witness is the first populated slot before the run.
                j = vi - 1
                while j >= 0 and ch[j].strip() == "a":
                    j -= 1
                prev = ch[j].strip() if j >= 0 else ""
                if sib != "a":
                    refused.append((bi, ci, vi, f"sibling slot is {sib!r}, not «a»"))
                elif not prev or prev == "a":
                    refused.append((bi, ci, vi, "no populated previous slot"))
                elif (len(prev) <= med and (bi, ci + 1, vi + 1) not in RULED
                      and os.environ.get("HEXAPLA_NO_ZHFIX") != "1"):
                    refused.append((bi, ci, vi, f"previous slot {len(prev)} chars <= "
                                                f"chapter median {med} - no merge witness"))
                else:
                    changes.append((bi, ci, vi, f"witness {ci + 1}:{j + 1} {len(prev)} chars, "
                                                f"median {med}"
                                                + (", RULED" if (bi, ci + 1, vi + 1) in RULED else "")))
    return changes, refused


def count_a(d):
    return sum(v.strip() == "a" for b in d for c in b["chapters"] for v in c)


def _selftest():
    long_ = "甲" * 60
    short = "乙" * 20
    mk = lambda ch: [{"name": "测", "chapters": [ch]}]
    # slot 2: a real merge (prev long). slot 4: «a» after a SHORT verse - no
    # witness, must be refused. slot 6: sibling disagrees - refused.
    s = mk([short, long_, "a", short, "a", short, "a"])
    t = mk([short, long_, "a", short, "a", short, "x"])
    changes, refused = plan(s, t)
    ok = True
    for what, cond in [
        ("the witnessed merge (1:3) is changed", [c[2] for c in changes] == [2]),
        ("«a» after a short verse (1:5) is REFUSED", any(r[2] == 4 for r in refused)),
        ("sibling disagreement (1:7) is REFUSED", any(r[2] == 6 for r in refused)),
    ]:
        print(("ok   - " if cond else "FAIL - ") + what)
        ok &= cond
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()

    data = {k: json.loads((ASSETS / f"{k}.json").read_text(encoding="utf-8")) for k in PAIR}
    plans = {PAIR[0]: plan(data[PAIR[0]], data[PAIR[1]]),
             PAIR[1]: plan(data[PAIR[1]], data[PAIR[0]])}
    rc = 0
    for k in PAIR:
        changes, refused = plans[k]
        d = data[k]
        print(f"{k}: {len(changes)} to blank, {len(refused)} refused "
              f"({count_a(d)} «a» slots) - {'APPLY' if a.apply else 'DRY RUN'}")
        for bi, ci, vi, why in (changes[:a.limit] if a.limit else changes):
            ch = d[bi]["chapters"][ci]
            j = vi - 1
            while j >= 0 and ch[j].strip() == "a":
                j -= 1
            print(f"   {d[bi]['name']} {ci + 1}:{vi + 1}  «a» -> ''   ({why})  "
                  f"{ch[j][:40]}…{ch[j][-20:]}")
        for bi, ci, vi, why in refused:
            print(f"   REFUSED {d[bi]['name']} {ci + 1}:{vi + 1}: {why}")
            rc = 1
    if not a.apply:
        print("dry run - nothing written")
        return rc
    if a.limit:
        sys.exit("--limit is for the dry run only")

    stamp = time.strftime("%Y-%m-%d_%H%M")
    for k in PAIR:
        changes, _ = plans[k]
        src = ASSETS / f"{k}.json"
        raw = src.read_bytes()
        bak = BACKUP_DIR / f"{k}.pre_zhfix_{stamp}.json"
        shutil.copy2(src, bak)
        d = data[k]
        for bi, ci, vi, _ in changes:
            d[bi]["chapters"][ci][vi] = ""
        # Keep the file's existing serialisation: compact vs indented.
        compact = b"\n " not in raw[:2000]
        out = (json.dumps(d, ensure_ascii=False, separators=(",", ":")) if compact
               else json.dumps(d, ensure_ascii=False, indent=1))
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                         dir=src.parent, delete=False, suffix=".tmp") as fh:
            fh.write(out)
        os.replace(fh.name, src)
        back = json.loads(src.read_text(encoding="utf-8"))
        left = count_a(back)
        print(f"{k}: wrote {len(changes)} blanks; re-read shows {left} «a» slots; backup {bak}")
        if left:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
