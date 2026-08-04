# -*- coding: utf-8 -*-
"""Print one Bakar chapter beside its KJV counterpart, for seam reading.

    python tools/bakar_pair.py <book-index> <chapter>      # 0-based book, 1-based chapter
    python tools/bakar_pair.py 0 7

Used by the versemap curation pass: the question at each divergent chapter is
always WHERE the two texts stop lining up, which needs both columns in view.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"


def main():
    bi, ci = int(sys.argv[1]), int(sys.argv[2])
    bak = json.loads((A / "ka_bakar.json").read_text(encoding="utf-8"))
    kjv = json.loads((A / "en_kjv.json").read_text(encoding="utf-8"))
    b = bak[bi]["chapters"][ci - 1]
    k = kjv[bi]["chapters"][ci - 1]
    print("BOOK %d (%s) CHAPTER %d — bakar %d verses, KJV %d verses"
          % (bi, kjv[bi]["name"], ci, len(b), len(k)))
    print()
    print("== BAKAR (Georgian) ==")
    for i, t in enumerate(b, 1):
        print("[%d] %s" % (i, t))
    print()
    print("== KJV (English reference) ==")
    for i, t in enumerate(k, 1):
        print("(%d) %s" % (i, t))


if __name__ == "__main__":
    main()
