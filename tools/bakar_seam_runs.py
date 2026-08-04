# -*- coding: utf-8 -*-
"""Turn read seam findings into versemap runs — and reject the ones that cannot be true.

    python tools/bakar_seam_runs.py <findings.json>

The readers report a SEAM TYPE and a KJV verse number; this converts that into
the run tuples the versemap uses. It does not trust them: a "merge" claim means
the Bakar chapter must have exactly one FEWER verse than the KJV's, and a
"split" exactly one MORE. Where the arithmetic disagrees with the claim, the
finding is DROPPED, not patched — a reader who misidentified the seam type has
not shown they located the seam either.

That check matters here because the readers marked every finding "high
confidence", so the workflow's verify stage skipped the merge/split ones
entirely. Arithmetic is the only independent witness those findings got.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"


def runs_for(kind, c, v, kmax, tmax):
    """Runs expressing one seam inside chapter c, KJV verse v."""
    if kind == "merge":                      # KJV v,v+1 live in one Bakar verse
        out = [(c, v, v + 1, c, v, v)]
        if v + 2 <= kmax:
            out.append((c, v + 2, kmax, c, v + 1, tmax))
    else:                                    # split: KJV v is two Bakar verses
        out = [(c, v, v, c, v, v + 1)]
        if v + 1 <= kmax:
            out.append((c, v + 1, kmax, c, v + 2, tmax))
    return out


def main():
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    bak = json.loads((A / "ka_bakar.json").read_text(encoding="utf-8"))
    kjv = json.loads((A / "en_kjv.json").read_text(encoding="utf-8"))

    kept, dropped, reflow = {}, [], []
    for f in data["findings"]:
        bi, ci, kind, v = f["book"], f["chapter"], f["kind"], f["kjv_verse"]
        if kind in ("reflow", "uncertain"):
            reflow.append((bi, ci, kind))
            continue
        try:
            tmax = len(bak[bi]["chapters"][ci - 1])
            kmax = len(kjv[bi]["chapters"][ci - 1])
        except IndexError:
            dropped.append((bi, ci, kind, v, "chapter out of range"))
            continue
        want = kmax - 1 if kind == "merge" else kmax + 1
        if tmax != want:
            dropped.append((bi, ci, kind, v, "counts say %d, a %s needs %d"
                            % (tmax, kind, want))); continue
        if not (1 <= v <= kmax) or (kind == "merge" and v + 1 > kmax):
            dropped.append((bi, ci, kind, v, "seam verse outside 1..%d" % kmax))
            continue
        kept.setdefault(bi, []).extend(runs_for(kind, ci, v, kmax, tmax))

    print("findings in        : %d" % len(data["findings"]))
    print("reflow/uncertain   : %d  (left identity on purpose)" % len(reflow))
    print("seams accepted     : %d chapters over %d books"
          % (sum(1 for b in kept for _ in [0]) and
             sum(len(v) // 2 + 1 for v in kept.values()) * 0 or
             len(data["findings"]) - len(reflow) - len(dropped), len(kept)))
    print("seams REJECTED     : %d" % len(dropped))
    for d in dropped:
        print("    book %-2d ch %-3d %-6s v%-3d — %s" % d)
    print()
    print("REFLOW chapters (no verse-level map asserted):")
    by = {}
    for bi, ci, _ in reflow:
        by.setdefault(bi, []).append(ci)
    for bi in sorted(by):
        print("    book %-2d: %s" % (bi, sorted(by[bi])))

    out = {str(b): [list(r) for r in sorted(set(rs))] for b, rs in sorted(kept.items())}
    Path(sys.argv[1]).with_name("bak_seam_runs.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwrote bak_seam_runs.json — %d books, %d runs"
          % (len(out), sum(len(v) for v in out.values())))


if __name__ == "__main__":
    main()
