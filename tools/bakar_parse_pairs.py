# -*- coding: utf-8 -*-
"""Parse the gap-chapter correspondence maps into versemap runs, validating hard.

    python tools/bakar_parse_pairs.py <journal.jsonl> <out.json>

The readers return a chapter's whole correspondence as a compact string, e.g.
    "1-18=1-18, 19-20=19, 21-32=20-31"
meaning KJV 1-18 pair with Bakar 1-18; KJV 19 AND 20 are the single Bakar verse
19; KJV 21-32 are Bakar 20-31.

Nothing is trusted. A map is accepted only if:
  * it covers every KJV verse of the chapter exactly once, in order;
  * every Bakar verse it names exists and is NON-EMPTY (naming an empty slot
    means the reader mapped scripture onto a gap — the exact defect this whole
    pass exists to remove);
  * equal-length ranges pair one-for-one.
Anything else is rejected whole, because a correspondence with a hole in it is
not partially usable — it silently shifts every verse after the hole.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"


def rng(tok):
    tok = tok.strip()
    if "-" in tok:
        a, b = tok.split("-", 1)
        return int(a), int(b)
    return int(tok), int(tok)


def main():
    rows = []
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("type") == "result" and isinstance(r.get("result"), dict):
            rows += r["result"].get("findings", [])
    bak = json.loads((A / "ka_bakar.json").read_text(encoding="utf-8"))
    kjv = json.loads((A / "en_kjv.json").read_text(encoding="utf-8"))

    ok, bad, unmappable = {}, [], []
    for f in rows:
        if f.get("mappable") is False or not f.get("pairs"):
            # The reader judged that no verse-level correspondence exists —
            # a different recension, or one that crosses chapter boundaries.
            # That is a finding, not a failure; the chapter stays identity.
            unmappable.append((f["book"], f["chapter"], f.get("note", "")[:120]))
            continue
        bi, ci, spec = f["book"], f["chapter"], f["pairs"]
        if bi == 18:
            # Psalms belongs to the LXX psalter engine, which already maps the
            # 151-psalm arrangement including its chapter offset. A per-chapter
            # map here would fight it — and the reader's own note shows why:
            # Bakar psalm 34 is KJV psalm 35, so its "verses" are not even
            # numbered against the same psalm.
            bad.append((bi, ci, "Psalms", "handled by the psalter engine",
                        f.get("confidence")))
            continue
        ch = bak[bi]["chapters"][ci - 1]
        kmax = len(kjv[bi]["chapters"][ci - 1])
        filled = {i + 1 for i, t in enumerate(ch) if t.strip()}
        runs, expect, err = [], 1, None
        for seg in spec.split(","):
            if "=" not in seg:
                err = "segment without '=': %r" % seg
                break
            lhs, rhs = seg.split("=", 1)
            try:
                # `+` is accepted on EITHER side: the readers used "23+24=23"
                # for two KJV verses in one Bakar verse, mirroring the "15+16"
                # form specified for the other direction. Both mean the same
                # thing to a run, so both are read the same way.
                if "+" in lhs:
                    parts = [int(x) for x in lhs.split("+")]
                    k0, k1 = min(parts), max(parts)
                else:
                    k0, k1 = rng(lhs)
            except ValueError:
                err = "bad KJV range %r" % lhs
                break
            if k0 != expect:
                err = "KJV %d follows %d — gap or overlap" % (k0, expect - 1)
                break
            expect = k1 + 1
            rhs = rhs.strip()
            if rhs == "none":
                continue                       # KJV verse absent here; unmapped
            try:
                if "+" in rhs:
                    a, b = [int(x) for x in rhs.split("+")]
                    t0, t1 = a, b
                else:
                    t0, t1 = rng(rhs)
            except ValueError:
                err = "bad Bakar range %r" % rhs
                break
            if not (1 <= t0 <= len(ch) and 1 <= t1 <= len(ch)):
                err = "Bakar %d-%d outside 1..%d" % (t0, t1, len(ch))
                break
            empty_hit = [p for p in range(t0, t1 + 1) if p not in filled]
            if empty_hit:
                err = "maps onto EMPTY slot(s) %s" % empty_hit
                break
            if (k1 - k0) != (t1 - t0) and not (k0 == k1 or t0 == t1):
                err = "range lengths differ: KJV %d-%d vs Bakar %d-%d" % (k0, k1, t0, t1)
                break
            runs.append((ci, k0, k1, ci, t0, t1))
        if not err and expect != kmax + 1:
            err = "map ends at KJV %d, chapter has %d" % (expect - 1, kmax)
        if err:
            bad.append((bi, ci, kjv[bi]["name"], err, f.get("confidence")))
            continue
        runs = [r for r in runs if not (r[1] == r[4] and r[2] == r[5])]
        if runs:
            ok.setdefault(bi, []).extend(runs)

    print("chapters mapped and VALID : %d" % (len(rows) - len(bad) - len(unmappable)))
    print("chapters UNMAPPABLE       : %d  (no correspondence exists)" % len(unmappable))
    print("chapters REJECTED         : %d" % len(bad))
    for b in bad:
        print("    book %-2d ch %-3d %-16s [%s] %s" % (b[0], b[1], b[2], b[4], b[3]))
    print("\nruns: %d over %d books" % (sum(len(v) for v in ok.values()), len(ok)))
    Path(sys.argv[2]).write_text(
        json.dumps({str(k): [list(r) for r in v] for k, v in sorted(ok.items())},
                   ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
