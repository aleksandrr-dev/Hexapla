# -*- coding: utf-8 -*-
"""Split the four MERGED psalm verses in fr_martin.json (Bible Martin 1744).
Dry run by default.

    python tools/fix_fr_martin_psalms.py            # dry run + witness
    python tools/fix_fr_martin_psalms.py --apply    # write, re-read, re-check

Found 2026-10-22 (s67). Ps 69, 102, 108 and 140 each carry two printed verses
in one slot, so every later verse of the psalm sits one slot early and the last
slot is EMPTY. docs/ASSET_DEFECTS.md called these four «TAIL (benign)» - a
merge in the scrape, not a versification difference: Martin numbers the title
as verse 1 like Luther and the Hebrew, and versemap.json ALREADY maps mar to
that numbering (Ps 69: KJV 2-36 <-> mar 3-37), so the map stays as it is and
points at the right verses only once the asset is split.

Split points (each asserted to occur exactly once in its verse):
  Ps 69:2   at the double space «l’âme.  Je suis enfoncé»
  Ps 102:1  at « 2.» - the printed verse number, dropped
  Ps 108:1  after the title «Cantique de Psaume de David.»
  Ps 140:1  after the title «Psaume de David, donné au maître chantre.»

WITNESS (0 tokens): Luther 1545 (de_luther.json) uses the same numbering.
Per psalm, the correlation of verse lengths mar vs lut must RISE after the
split; if any psalm does not improve, nothing is written (rc 2).

Controls: byte-exact json round-trip; the last slot is empty before and filled
after; verse counts unchanged; every other verse in the file byte-identical;
the joined text of each psalm is unchanged except the dropped «2.».
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app/src/main/assets/bibles"
ASSET = ROOT / "fr_martin.json"
WITNESS = ROOT / "de_luther.json"
DUMP = dict(ensure_ascii=False, separators=(",", ":"))
PSALMS = 18

# psalm, 1-based verse holding the merge, left part ends with, right part starts with, dropped
SPLITS = [
    (69, 2, "l’âme.", "Je suis enfoncé", "  "),
    (102, 1, "devant l’Eternel.", "Eternel ! écoute", " 2."),
    (108, 1, "Cantique de Psaume de David.", "Mon coeur est disposé", " "),
    (140, 1, "Psaume de David, donné au maître chantre.", "Eternel, délivre-moi", " "),
]


def corr(a, b):
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    sa = sum((x - ma) ** 2 for x in a) ** 0.5
    sb = sum((y - mb) ** 2 for y in b) ** 0.5
    return sab / (sa * sb) if sa and sb else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    raw = ASSET.read_text(encoding="utf-8")
    books = json.loads(raw)
    if json.dumps(books, **DUMP) != raw:
        sys.exit("CONTROL: asset does not round-trip byte-exact; refusing")
    lut = json.loads(WITNESS.read_text(encoding="utf-8"))[PSALMS]["chapters"]
    before = json.loads(raw)
    worse = []
    for ps, vs, left_end, right_start, drop in SPLITS:
        ch = books[PSALMS]["chapters"][ps - 1]
        if ch[-1] != "":
            sys.exit(f"CONTROL: Ps {ps} last slot is not empty: {ch[-1][:60]!r}")
        v = ch[vs - 1]
        seam = left_end + drop + right_start
        if v.count(seam) != 1:
            sys.exit(f"CONTROL: Ps {ps}:{vs} has {v.count(seam)}x seam {seam!r}, want 1")
        i = v.index(seam)
        left, right = v[:i + len(left_end)], v[i + len(left_end) + len(drop):]
        new = ch[:vs - 1] + [left, right] + ch[vs:-1]
        if len(new) != len(ch) or not new[-1]:
            sys.exit(f"CONTROL: Ps {ps} shape/last slot wrong after split")
        # the psalm's words are the same, minus «2.» where that is the drop
        want = " ".join(ch).split()
        if drop.strip():
            want.remove(drop.strip() + right_start.split()[0])
            want.insert(want.index(left_end.split()[-1]) + 1, right_start.split()[0])
        if " ".join(new).split() != want:
            sys.exit(f"CONTROL: Ps {ps} text changed beyond the seam")
        w = [len(x) for x in lut[ps - 1]]
        c0 = corr([len(x) for x in ch], w)
        c1 = corr([len(x) for x in new], w)
        print(f"Ps {ps}: {len(ch)} verses; split {vs} -> {vs},{vs + 1}; "
              f"length-corr vs Luther {c0:+.2f} -> {c1:+.2f}")
        print(f"   v{vs}:   {left[-60:]!r}")
        print(f"   v{vs + 1}: {right[:60]!r}")
        print(f"   last: {new[-1][:70]!r}")
        if c1 <= c0:
            worse.append(ps)
        books[PSALMS]["chapters"][ps - 1] = new
    if worse:
        sys.exit(f"CONTROL: witness did not improve for Ps {worse}; nothing written")
    touched = {(PSALMS, ps - 1) for ps, *_ in SPLITS}
    for bi, b in enumerate(books):
        for ci, c in enumerate(b["chapters"]):
            if (bi, ci) not in touched and c != before[bi]["chapters"][ci]:
                sys.exit(f"CONTROL: {b['name']} {ci + 1} changed; nothing written")
    print(f"\n{len(SPLITS)} psalms re-split; every other chapter byte-identical")
    if not a.apply:
        print("DRY RUN - nothing written (--apply to write)")
        return
    ASSET.write_text(json.dumps(books, **DUMP), encoding="utf-8", newline="")
    if json.loads(ASSET.read_text(encoding="utf-8")) != books:
        sys.exit("CONTROL: re-read differs from what was written")
    print(f"WROTE {ASSET}")


if __name__ == "__main__":
    main()
