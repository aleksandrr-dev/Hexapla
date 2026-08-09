# -*- coding: utf-8 -*-
"""Whole-corpus completeness audit for the Glen Persian OT chunk reports.

Chunk-level checks do NOT compose into a whole-document guarantee — the NT
campaign paid for that lesson. This aggregates every report, per BOOK, against
the KJV grid and reports what is missing, short, long or absent.

Reuses the section-splitting and file-exclusion logic from
glen_defect_inventory.py so the two cannot drift apart.

    python tools/glen_corpus_audit.py
"""
import glob
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import glen_defect_inventory as inv  # noqa: E402

RESEARCH = inv.RESEARCH
KJV = inv.KJV


def main():
    d = json.load(open(KJV, encoding="utf-8"))
    counts = [[len(c) for c in b["chapters"]] for b in d]
    names = [b["name"] for b in d]

    best = {}
    for path in sorted(glob.glob(str(RESEARCH / "glen_*.md"))):
        if ".bak" in path or any(x in os.path.basename(path)
                                 for x in inv.EXCLUDE):
            continue
        for bidx, chapters in inv.sections(path, None):
            if bidx is None:
                continue
            for c, got in chapters.items():
                if not got:
                    continue
                exp = counts[bidx][c - 1] if c - 1 < len(counts[bidx]) else None
                prev = best.get((bidx, c))
                if prev is None or (len(got) == exp and len(prev) != exp) or \
                        (len(prev) != exp and len(got) > len(prev)):
                    best[(bidx, c)] = got

    grand = grand_exp = 0
    problems = []
    print(f"{'book':<16}{'chs':>8}{'verses':>14}   status")
    print("-" * 56)
    for b in range(39):                      # OT only
        exp = counts[b]
        have = [c for c in range(1, len(exp) + 1) if (b, c) in best]
        tot = sum(len(best[(b, c)]) for c in have)
        grand += tot
        grand_exp += sum(exp)
        miss = [c for c in range(1, len(exp) + 1) if c not in have]
        off = [(c, len(best[(b, c)]), exp[c - 1]) for c in have
               if len(best[(b, c)]) != exp[c - 1]]
        ok = not miss and not off
        status = "OK" if ok else ""
        if miss:
            status += f" MISSING chapters {miss}"
            problems.append((names[b], "missing", miss))
        if off:
            status += f" count-diff {off}"
            problems.append((names[b], "count", off))
        print(f"{names[b]:<16}{len(have):>3}/{len(exp):<4}"
              f"{tot:>7}/{sum(exp):<6}   {status}")

    print("-" * 56)
    print(f"{'TOTAL':<16}{'':>8}{grand:>7}/{grand_exp:<6}")
    print()
    if problems:
        print("⚠ PROBLEMS:")
        for n, kind, v in problems:
            print(f"   {n}: {kind} {v}")
    else:
        print("✅ every OT book present, every chapter present, "
              "every count reconciled")
    print()
    print("NOTE: a count differing from KJV is not automatically wrong — a")
    print("printed numeral omitted or duplicated changes the MARKER count")
    print("without changing the verses. Cross-check against the defect")
    print("inventory before treating any difference as damage.")


if __name__ == "__main__":
    main()
