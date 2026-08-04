# -*- coding: utf-8 -*-
"""Validate and convert CROSS-CHAPTER correspondence segments into versemap runs.

    python tools/bakar_cross_runs.py <journal.jsonl> <out.json>

Segment form, both sides always carrying an explicit chapter:
    "41:1-8=40:20-27, 41:9-10=41:1, 41:12-34=41:3-25, 6:7=none"

Checks, all of which must pass for a GROUP to be accepted:
  * every KJV chapter the group touches is covered exactly once, end to end;
  * no run names an empty Bakar slot;
  * every chapter and verse referenced actually exists.

Note what is deliberately ALLOWED: two segments may point at the SAME Bakar
verse. That is not an error — it is how a genuine many-to-one is expressed when
the KJV verses involved sit in different KJV chapters, which is exactly the
case at Haggai (KJV 1:15 and 2:1 share one Bakar verse) and in the LXX
Proverbs transposition. The reverse — one KJV verse mapped twice — IS an error
and is rejected.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"
SEG = re.compile(r"^\s*(\d+):(\d+)(?:-(\d+))?\s*=\s*(?:(\d+):(\d+)(?:-(\d+))?|none)\s*$")


def main():
    rows = []
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("type") == "result" and isinstance(r.get("result"), dict):
            rows += r["result"].get("findings", [])
    bak = json.loads((A / "ka_bakar.json").read_text(encoding="utf-8"))
    kjv = json.loads((A / "en_kjv.json").read_text(encoding="utf-8"))

    out, rejected = {}, []
    for f in rows:
        bi = f["book"]
        runs, cover, err = [], {}, None
        for seg in f["segments"].split(","):
            m = SEG.match(seg)
            if not m:
                err = "unparsable segment %r" % seg.strip()
                break
            kc, k0, k1, tc, t0, t1 = m.groups()
            kc, k0 = int(kc), int(k0)
            k1 = int(k1) if k1 else k0
            if kc > len(kjv[bi]["chapters"]) or k1 > len(kjv[bi]["chapters"][kc - 1]):
                err = "KJV %d:%d-%d outside the book" % (kc, k0, k1)
                break
            cover.setdefault(kc, []).extend(range(k0, k1 + 1))
            if tc is None:
                continue                      # "=none": no Bakar counterpart
            tc, t0 = int(tc), int(t0)
            t1 = int(t1) if t1 else t0
            if tc > len(bak[bi]["chapters"]) or t1 > len(bak[bi]["chapters"][tc - 1]):
                err = "Bakar %d:%d-%d outside the book" % (tc, t0, t1)
                break
            ch = bak[bi]["chapters"][tc - 1]
            hit = [p for p in range(t0, t1 + 1) if not ch[p - 1].strip()]
            if hit:
                err = "Bakar %d:%s is an EMPTY slot" % (tc, hit)
                break
            runs.append((kc, k0, k1, tc, t0, t1))
        if not err:
            for kc, vs in cover.items():
                kmax = len(kjv[bi]["chapters"][kc - 1])
                if sorted(vs) != list(range(1, kmax + 1)):
                    dupes = sorted({x for x in vs if vs.count(x) > 1})
                    miss = [x for x in range(1, kmax + 1) if x not in vs]
                    err = "KJV ch %d incomplete (missing %s, doubled %s)" % (
                        kc, miss[:6], dupes[:6])
                    break
        if err:
            rejected.append((bi, kjv[bi]["name"], err, f.get("confidence")))
            continue
        runs = [r for r in runs if not (r[0] == r[3] and r[1] == r[4] and r[2] == r[5])]
        out.setdefault(str(bi), []).extend(runs)

    print("groups ACCEPTED : %d" % (len(rows) - len(rejected)))
    print("groups REJECTED : %d" % len(rejected))
    for r in rejected:
        print("    book %-2d %-16s [%s] %s" % (r[0], r[1], r[3], r[2]))
    print("\nruns: %d over %d books" % (sum(len(v) for v in out.values()), len(out)))
    Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
