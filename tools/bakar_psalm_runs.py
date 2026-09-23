# -*- coding: utf-8 -*-
"""Turn the psalm seam readings into BAK_PSALTER overrides for the versemap.

    python tools/bakar_psalm_runs.py <journal.jsonl> <out.py>

The LXX psalter engine takes an `overrides` map {kjv psalm: [runs]} for psalms
whose difference is NOT a leading title verse. The Bakar needs many of these,
because it prints every psalm title INLINE at the head of verse 1 — so any
surplus or deficit is a real seam, never a title.

Validated exactly like the other passes: every KJV verse of the psalm covered
once, no run naming an empty Bakar slot, everything in range. A psalm that
fails is dropped and falls back to the engine's own handling.

⚠ Whole-psalm blocks are what this replaces. A run whose sides differ in length
is a BLOCK, and the reader prints the entire other side under EVERY verse of
it — so mapping a psalm as one block repeated the whole psalm under all ten or
twenty verses. Keep blocks to a verse or two.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A = Path(__file__).parent.parent / "app" / "src" / "main" / "assets" / "bibles"


def side(tok):
    tok = tok.strip()
    if "+" in tok:
        p = [int(x) for x in tok.split("+")]
        return min(p), max(p)
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

    ok, bad = {}, []
    notes = {}
    for f in rows:
        kc, tc = f["kjv_psalm"], f["bak_psalm"]
        kmax = len(kjv[18]["chapters"][kc - 1])
        ch = bak[18]["chapters"][tc - 1]
        runs, cover, err = [], [], None
        for seg in f["pairs"].split(","):
            if "=" not in seg:
                err = "bad segment %r" % seg.strip()
                break
            lhs, rhs = seg.split("=", 1)
            try:
                k0, k1 = side(lhs)
            except ValueError:
                err = "bad KJV side %r" % lhs
                break
            cover += list(range(k0, k1 + 1))
            if rhs.strip() == "none":
                continue
            try:
                t0, t1 = side(rhs)
            except ValueError:
                err = "bad Bakar side %r" % rhs
                break
            if not (1 <= t0 <= len(ch) and 1 <= t1 <= len(ch)):
                err = "Bakar %d:%d-%d out of range" % (tc, t0, t1)
                break
            hit = [p for p in range(t0, t1 + 1) if not ch[p - 1].strip()]
            if hit:
                err = "Bakar %d:%s is EMPTY" % (tc, hit)
                break
            # Only an UNEQUAL run is a block. Equal-length runs pair verse
            # for verse and are safe at any size — "1-73=1-73" is 73 clean
            # pairings, not a 73-verse block.
            if (k1 - k0) != (t1 - t0) and max(k1 - k0, t1 - t0) > 2:
                err = "block of %d/%d verses — too large to render" % (
                    k1 - k0 + 1, t1 - t0 + 1)
                break
            runs.append((kc, k0, k1, tc, t0, t1))
        if not err and sorted(cover) != list(range(1, kmax + 1)):
            miss = [x for x in range(1, kmax + 1) if x not in cover]
            dup = sorted({x for x in cover if cover.count(x) > 1})
            err = "coverage: missing %s, doubled %s" % (miss[:5], dup[:5])
        if err:
            bad.append((kc, tc, err, f.get("confidence")))
            continue
        ok[kc] = runs
        notes[kc] = (f.get("note") or "").replace("\n", " ")[:150]

    print("psalms ACCEPTED : %d" % len(ok))
    print("psalms REJECTED : %d" % len(bad))
    for x in bad:
        print("    KJV %-4d (bak %-4d) [%s] %s" % (x[0], x[1], x[3], x[2]))

    out = ['# -*- coding: utf-8 -*-',
           '"""Bakar psalter overrides — GENERATED (tools/bakar_psalm_runs.py).',
           '',
           'The Bakar prints psalm titles INLINE at the head of verse 1, so the LXX',
           'psalter engine\'s title-offset assumption never applies here: any surplus or',
           'deficit is a genuine seam. Each psalm below was read against the KJV, and',
           'validated to cover every KJV verse once and name no empty slot.',
           '"""', '', 'BAK_PSALTER = {']
    for kc in sorted(ok):
        out.append('    # Ps %d (Bakar %d): %s' % (kc, ok[kc][0][3], notes[kc]))
        out.append('    %d: [%s],' % (kc, ", ".join(str(r) for r in ok[kc])))
    out.append('}')
    Path(sys.argv[2]).write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\nwrote %s (%d psalms)" % (sys.argv[2], len(ok)))


if __name__ == "__main__":
    main()
