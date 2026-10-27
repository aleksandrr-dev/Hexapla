# -*- coding: utf-8 -*-
"""Find where Tyndale's «the» is the pronoun THEE, for the narration only.

    python tools/derive_tyn_thee_sites.py            # dry run: counts + samples
    python tools/derive_tyn_thee_sites.py --write    # write tools/tyn_thee_sites.json

WHY
---
Tyndale spells the pronoun «thee» as «the» («I will blesse the»). The page is
right and stays as printed; the narrator reads «the» as the article. Owner
2026-09-28: «do thee per verse». So the SPOKEN text of each such site says
«thee», through synthesis_overrides.apply (display, asset and align_words'
reference text untouched: same word, respelled).

HOW A SITE IS ACCEPTED (under-correct on purpose: a missed «thee» is the old
state; an article spoken «thee» is a new defect)
  1. the verse, normalized exactly as narrate does, is token-aligned to the
     KJV verse, and the tyn «the» sits in an equal-length replace block
     opposite KJV «thee»;
  2. the next tyn word is NOT one that follows the article in the asset
     much more often than it follows an object pronoun (him/them/me/vs/the
     sites of rule 1). A noun after «the» means the article.
A site is stored as (book, chapter, verse, n): the n-th whole-word «the»
(case-insensitive) in the ASSET verse. synthesis_overrides re-counts at
synthesis time and skips the verse if the count no longer matches.
"""
import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from archaic_english import normalize  # noqa: E402

ASSET = ROOT / "app/src/main/assets/bibles/en_tyndale.json"
KJV = ROOT / "app/src/main/assets/bibles/en_kjv.json"
OUT = ROOT / "tools/tyn_thee_sites.json"
W = re.compile(r"[A-Za-z]+")
PRON = {"him", "them", "me", "vs", "us", "her", "you"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", type=int, default=15)
    a = ap.parse_args()
    tyn = json.loads(ASSET.read_text(encoding="utf-8"))
    kjv = json.loads(KJV.read_text(encoding="utf-8"))

    after_art, after_pron = Counter(), Counter()
    for b in tyn:
        for c in b["chapters"]:
            for v in c:
                ws = [w.lower() for w in W.findall(v or "")]
                for x, y in zip(ws, ws[1:]):
                    if x == "the":
                        after_art[y] += 1
                    elif x in PRON:
                        after_pron[y] += 1

    cand = []
    for bi, (tb, kb) in enumerate(zip(tyn, kjv)):
        for ci, (tc, kc) in enumerate(zip(tb["chapters"], kb["chapters"])):
            for vi, (tv, kv) in enumerate(zip(tc, kc), 1):
                if not tv or not kv:
                    continue
                raw = W.findall(tv)
                # normalize word by word so indices stay those of the asset
                tn = [normalize(w, "tyndale").lower() for w in raw]
                kw = [w.lower() for w in W.findall(re.sub(r"\{[^}]*\}", "", kv))]
                sm = SequenceMatcher(None, tn, kw, autojunk=False)
                for op, a1, a2, b1, b2 in sm.get_opcodes():
                    if op != "replace" or a2 - a1 != b2 - b1:
                        continue
                    for i in range(a1, a2):
                        if raw[i].lower() == "the" and kw[b1 + i - a1] == "thee":
                            n = sum(1 for w in raw[:i] if w.lower() == "the")
                            nxt = raw[i + 1].lower() if i + 1 < len(raw) else ""
                            cand.append((bi, ci + 1, vi, n, nxt, tb["name"], tv))

    keep, drop = [], []
    for c in cand:
        nxt = c[4]
        art, pro = after_art[nxt], after_pron[nxt]
        # the article's typical followers: seen after «the» 5x+ and at least
        # 4x as often as after an object pronoun (normalised per total)
        if nxt and art >= 5 and art / sum(after_art.values()) > 4 * (pro + 1) / sum(after_pron.values()):
            drop.append(c)
        else:
            keep.append(c)
    print(f"KJV-aligned «the»=thee sites {len(cand)}; kept {len(keep)} in "
          f"{len({c[:3] for c in keep})} verses; dropped by next-word test {len(drop)}")
    print("dropped next words:", Counter(c[4] for c in drop).most_common(20))
    print("kept next words   :", Counter(c[4] for c in keep).most_common(20))
    for c in keep[:a.show]:
        print(f"  {c[5]} {c[1]}:{c[2]} #{c[3]}  {c[6][:110]}")
    if a.write:
        OUT.write_text(json.dumps(
            {"_doc": "tools/derive_tyn_thee_sites.py; [book_idx, chapter(1-based), verse, nth «the»]",
             "sites": [list(c[:4]) for c in keep]}, ensure_ascii=False, indent=0),
            encoding="utf-8", newline="\n")
        print("wrote", OUT)
    else:
        print("DRY RUN - --write to store the sites")


if __name__ == "__main__":
    main()
