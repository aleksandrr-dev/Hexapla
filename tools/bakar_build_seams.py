# -*- coding: utf-8 -*-
"""Build tools/bak_seams.py from the two independent seam readings + gap analysis.

    python tools/bakar_build_seams.py <compare.json> <batches.json>

Three sources of runs, in priority order:

1. GAP SHIFT (provable, no reading needed). Where the Bakar chapter's NON-EMPTY
   verses number exactly the KJV's, but the chapter contains empty slots, the
   print simply skipped those numbers and the non-empty verses correspond to
   the KJV one-for-one in order. The runs follow by construction.
   ⚠ This class was invisible to the seam readers and to the arithmetic check,
   because both compared SLOT counts. A chapter whose slot count happens to
   equal the KJV's while holding an empty slot looks perfectly aligned and is
   misaligned after the gap — 26 chapters were in exactly that state. Others
   produced PHANTOM SPLITS: a reader sees one extra slot and reports a split
   that does not exist in the text (James 4, Joshua 6 and six more).

2. AGREED SEAM. Two independent blind readings of the same chapter produced the
   same seam type and the same verse. Used only where the chapter has no empty
   slots, so it cannot be a phantom.

3. Everything else is DROPPED to identity — disagreements between the two
   readings, chapters where the second reader became unsure, and chapters that
   hold BOTH empty slots and a genuine seam (Genesis 11 is one: its non-empty
   count is one short of the KJV, so a merge hides somewhere in it as well).
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"


def compact(pairs):
    """[(kjv_v, bak_v)] in order -> minimal contiguous runs."""
    runs, i = [], 0
    while i < len(pairs):
        j = i
        while (j + 1 < len(pairs) and pairs[j + 1][0] == pairs[j][0] + 1
               and pairs[j + 1][1] == pairs[j][1] + 1):
            j += 1
        runs.append((pairs[i][0], pairs[j][0], pairs[i][1], pairs[j][1]))
        i = j + 1
    return runs


def seam_runs(kind, c, v, kmax, tmax):
    if kind == "merge":
        out = [(c, v, v + 1, c, v, v)]
        if v + 2 <= kmax:
            out.append((c, v + 2, kmax, c, v + 1, tmax))
    else:
        out = [(c, v, v, c, v, v + 1)]
        if v + 1 <= kmax:
            out.append((c, v + 1, kmax, c, v + 2, tmax))
    return out


def main():
    cmp_ = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    batches = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    bak = json.loads((A / "ka_bakar.json").read_text(encoding="utf-8"))
    kjv = json.loads((A / "en_kjv.json").read_text(encoding="utf-8"))

    seam_of = {}
    for batch in batches:
        for bi, ci, kind, v, name, tmax, kmax in batch:
            seam_of[(bi, ci)] = (kind, v, name)
    agreed = {tuple(x) for x in cmp_["agree"]}

    runs, gapfix, agreed_used, dropped, mixed = {}, [], [], [], []
    for bi in range(66):
        if not any(bak[bi]["chapters"]):
            continue
        for ci0, ch in enumerate(bak[bi]["chapters"]):
            ci = ci0 + 1
            if ci0 >= len(kjv[bi]["chapters"]):
                continue
            kmax = len(kjv[bi]["chapters"][ci0])
            filled = [i + 1 for i, t in enumerate(ch) if t.strip()]
            empt = len(ch) - len(filled)
            key = (bi, ci)
            if empt and len(filled) == kmax:
                pairs = [(n, p) for n, p in zip(range(1, kmax + 1), filled)]
                rs = [(c0, k0, k1, c0, t0, t1) for c0, k0, k1, t0, t1
                      in [(ci,) + r for r in compact(pairs)]]
                rs = [r for r in rs if not (r[1] == r[4] and r[2] == r[5])]
                if rs:
                    runs.setdefault(bi, []).extend(rs)
                    gapfix.append((bi, ci, kjv[bi]["name"], empt))
                continue
            if empt:
                if key in seam_of:
                    mixed.append((bi, ci, kjv[bi]["name"], empt,
                                  len(filled), kmax))
                continue
            if key in agreed and key in seam_of:
                kind, v, _ = seam_of[key]
                runs.setdefault(bi, []).extend(
                    seam_runs(kind, ci, v, kmax, len(ch)))
                agreed_used.append(key)
            elif key in seam_of:
                dropped.append((bi, ci, kjv[bi]["name"]) + seam_of[key][:2])

    print("GAP-SHIFT chapters (provable, no reading needed) : %d" % len(gapfix))
    print("AGREED seam chapters (two blind readings match)  : %d" % len(agreed_used))
    print("DROPPED — readings disagreed                     : %d" % len(dropped))
    for d in dropped:
        print("      book %-2d ch %-3d %-16s (%s@%d)" % d)
    print("DROPPED — empty slots AND a real seam            : %d" % len(mixed))
    for m in mixed:
        print("      book %-2d ch %-3d %-16s empty=%d filled=%d kjv=%d" % m)
    total = sum(len(v) for v in runs.values())
    print("\ntotal runs: %d over %d books" % (total, len(runs)))
    Path(sys.argv[1]).with_name("bak_runs_final.json").write_text(
        json.dumps({str(k): [list(r) for r in v] for k, v in sorted(runs.items())},
                   ensure_ascii=False), encoding="utf-8")
    print("wrote bak_runs_final.json")


if __name__ == "__main__":
    main()
