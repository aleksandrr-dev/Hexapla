# -*- coding: utf-8 -*-
"""Build a repair_verses.py queue as the UNION of
  (verses a pronunciation-lexicon word changes)  ∪  (verses already repaired),
per chapter.

    python tools/build_union_queue.py --word elisha --out _work/q.txt

## ⛔ WHY THE UNION, AND NOT JUST THE VERSES YOU MEAN TO CHANGE

`repair_verses.py` rebuilds each chapter from `narration/<dir>_qa_fail_originals/`
and splices in ONLY the verses named in the queue. Any verse that has been
repaired before and is NOT named therefore **REVERTS to its pre-repair take** —
silently, because the chapter still re-encodes and its mtime still changes.
18 of one run's 43 chapters carried prior repairs.

So for every chapter this touches, the queue must also name every verse with a
record in that chapter's `<c>.qa.json`.

## ⚠ IT ALSO REPORTS TEXT-EXPLAINED VERSES IT IS FORCED TO INCLUDE

A verse whose gate flag is explained by the PRINTED TEXT can never pass: the gate
fires on scripture, so all 3 redraws fail and the GPU is spent for nothing
(measured: Revelation 11:15, Exodus 3:15, II Kings 5:25). The union rule requires
them in the queue anyway, or they revert. That contradiction is unresolved in
this project — `repair_verses.py` would need to splice such a verse WITHOUT
redrawing it. This tool cannot fix that; it PRINTS which verses will burn futile
draws so the cost is visible rather than discovered afterwards.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(r"C:\Projects\Hexapla")
DATA = Path(r"C:\Projects\Hexapla-releases")
ASSET = REPO / "app/src/main/assets/bibles/en_ylt.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", required=True, help="whole word the lexicon rewrites")
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--dir", default="ylt", help="narration/<dir>")
    ap.add_argument("--out")
    a = ap.parse_args()

    books = json.loads(ASSET.read_text(encoding="utf-8"))
    books = books["books"] if isinstance(books, dict) and "books" in books else books
    rx = re.compile(rf'\b{re.escape(a.word)}\b', re.I)

    changed = defaultdict(set)       # (b,c) -> {verse numbers}
    for bi, b in enumerate(books):
        for ci, ch in enumerate(b["chapters"] if isinstance(b, dict) else b):
            for vi, v in enumerate(ch):
                if isinstance(v, str) and rx.search(v):
                    changed[(bi, ci)].add(vi + 1)

    nar = DATA / "narration" / a.dir
    rows, futile, repaired_added = [], [], 0
    for (bi, ci) in sorted(changed):
        verses = set(changed[(bi, ci)])
        qa = nar / str(bi) / f"{ci}.qa.json"
        if qa.exists():
            try:
                q = json.loads(qa.read_text(encoding="utf-8"))
            except Exception as e:                       # noqa: BLE001
                print(f"⛔ {qa} unreadable ({e}) — REFUSING to build a queue that "
                      f"might silently revert verses")
                return 1
            for r in q.get("repairs", []):
                v = r.get("verse")
                if v is None:
                    continue
                if v not in verses:
                    repaired_added += 1
                verses.add(v)
                if r.get("still_failing"):
                    futile.append((bi, ci, v, ",".join(r["still_failing"])))
        rows.append((bi, ci, sorted(verses)))

    total = sum(len(v) for _, _, v in rows)
    print(f"word «{a.word}»: {sum(len(v) for v in changed.values())} verses in "
          f"{len(changed)} chapters")
    print(f"union with prior repairs: {total} verses in {len(rows)} chapters "
          f"(+{repaired_added} verses added ONLY to stop them reverting)")

    if futile:
        seen = {(b, c, v) for b, c, v, _ in futile}
        print(f"\n⚠ {len(seen)} verse(s) in this queue have a still-failing gate "
              f"record. If the flag is explained by the printed text they will be "
              f"redrawn 3× and fail 3× — visible cost, not a surprise:")
        for b, c, v, why in sorted(set(futile)):
            print(f"    {b} {c} v{v}   [{why}]")

    lines = [f"# UNION queue for lexicon word «{a.word}» — built by "
             f"tools/build_union_queue.py",
             f"# {total} verses / {len(rows)} chapters. "
             f"{repaired_added} verse(s) are here ONLY because they carry a prior",
             f"# repair record and would REVERT if omitted. ⛔ Do not trim this file.",
             ""]
    for bi, ci, vs in rows:
        lines.append(f"{bi} {ci} {','.join(str(v) for v in vs)}")

    if a.out:
        Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nwrote {a.out}")
    else:
        print()
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
