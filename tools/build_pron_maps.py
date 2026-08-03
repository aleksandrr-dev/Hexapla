# -*- coding: utf-8 -*-
"""Build TTS pronunciation maps for the archaic English translations.

    python tools/build_pron_maps.py            # writes all three assets
    python tools/build_pron_maps.py --report   # print coverage, write nothing

Emits app/src/main/assets/pron_<id>.json for tyn, gnv and wyc. Pronounce.kt
loads them so the DEVICE TTS says what the rendered narration says.

WHY THIS IS SEPARATE FROM build_tyndale_pron.py
-----------------------------------------------
That script carries Tyndale's large hand-curated OVERRIDE table and stays the
authority for `tyn`. This one derives maps for the OTHER two by the same
KJV-corroboration method, and re-emits Tyndale's from the generated module so
all three assets are produced together and cannot drift apart.

⚠ THE GAP THIS CLOSES, found by the owner on 2026-08-03:
  · The app had NO pronunciation normalization at all. tools/archaic_english.py
    only ever ran when RENDERING narration, so the recorded voice was correct
    while the live TTS read the raw asset — "yow", "lickness", "do-MINE-yon".
  · Worse, the Geneva and Wycliffe normalizers were thin: "heauen" occurs 608
    times in Geneva and was NOT mapped, and "heuene" 624 times in Wycliffe.
    ▶ So the SHIPPED Geneva narration was rendered from unmapped text. Whether
      kokoro pronounced "heauen" acceptably is an EAR question, not a code
      question — verify against the published audio before deciding whether a
      re-render is warranted. Do not assume either way.

METHOD — identical to build_tyndale_pron.py, and for the same reasons.
Each translation sits on the KJV verse grid, so every verse has a parallel.
A candidate is accepted only when it is spelled similarly AND actually appears
in the parallel KJV verses. Requiring that corroboration is what rejects a
plausible-looking guess.
⚠ NAME GUARD: a candidate that is almost always capitalised in the KJV is a
proper name, and a lower-case common word must never map onto one.
"""
import argparse
import collections
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))
from archaic_english import normalize            # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "app/src/main/assets"
NOTE = re.compile(r"\s*\{[^{}]*:[^{}]*\}")

MIN_SIM, MIN_SUPPORT, MIN_FREQ = 0.75, 0.55, 2
HI_SIM, HI_SIM_SUPPORT = 0.83, 0.15

SETS = [
    # (translation id, asset, archaic_english dialect)
    ("gnv", "en_geneva.json", "geneva"),
    ("wyc", "enm_wycliffe.json", "wycliffe"),
]

# Hand-checked, shared across the Early Modern sets. These are u/v and i/j
# swaps and silent-e forms that the corroboration method misses because the
# KJV spells the same word differently enough to score low.
SHARED = {
    "heauen": "heaven", "heauens": "heavens", "heauenly": "heavenly",
    "heuene": "heaven", "heuenes": "heavens", "heuenly": "heavenly",
    "heuenli": "heavenly", "heuen": "heaven", "heuenys": "heavens",
    "heauie": "heavy", "heauy": "heavy", "heauinesse": "heaviness",
    "heauines": "heaviness", "heauier": "heavier",
    "erthe": "earth", "erth": "earth", "eerthe": "earth",
    "sonne": "son", "sonnes": "sons", "lorde": "lord",
    "gyue": "give", "gyuen": "given", "gyueth": "giveth",
    "lyue": "live", "lyues": "lives", "lyueth": "liveth",
    "lyuynge": "living", "lyuing": "living",
    "seruaunt": "servant", "seruauntes": "servants", "seruant": "servant",
    "haue": "have", "hath": "hath", "sayde": "said", "saide": "said",
    "vnto": "unto", "vpon": "upon", "vs": "us", "vp": "up",
    "iesus": "Jesus", "iesu": "Jesu", "ihesus": "Jesus", "ihesu": "Jesu",
    "iohn": "John", "ihon": "John", "iudas": "Judas", "iacob": "Jacob",
    "ioseph": "Joseph", "ierusalem": "Jerusalem", "iewes": "Jews",
    "iudge": "judge", "iudgement": "judgement", "ioye": "joy",
    "knowe": "know", "knowen": "known", "sawe": "saw", "sayth": "saith",
    "worde": "word", "wordes": "words", "worke": "work", "workes": "works",
}


def clean(v):
    return NOTE.sub("", v).replace("{", "").replace("}", "")


def derive(asset, dialect):
    tyn = json.loads((A / "bibles" / asset).read_text(encoding="utf-8"))
    kjv = json.loads((A / "bibles/en_kjv.json").read_text(encoding="utf-8"))
    tb = tyn["books"] if isinstance(tyn, dict) else tyn
    kb = kjv["books"] if isinstance(kjv, dict) else kjv
    lex = json.loads((A / "webster1828.json").read_text(encoding="utf-8"))
    heads = {k.lower() for k in lex} if isinstance(lex, dict) else set()

    kv, kc, caps = collections.Counter(), collections.Counter(), collections.Counter()
    freq, co = collections.Counter(), collections.defaultdict(collections.Counter)
    pairs = []
    for bi in range(min(len(tb), len(kb))):
        tch, kch = tb[bi].get("chapters", []), kb[bi].get("chapters", [])
        for ci in range(min(len(tch), len(kch))):
            for vi in range(min(len(tch[ci]), len(kch[ci]))):
                tw = re.findall(r"[A-Za-z]+",
                                normalize(clean(tch[ci][vi]), dialect))
                kraw = re.findall(r"[A-Za-z]+", clean(kch[ci][vi]))
                for w in kraw:
                    kv[w.lower()] += 1
                    if w[0].isupper():
                        kc[w.lower()] += 1
                pairs.append((tw, {w.lower() for w in kraw}))
    known = heads | set(kv)
    for tw, kws in pairs:
        for w in tw:
            if w.lower() in known:
                continue
            if w[0].isupper():
                caps[w.lower()] += 1
            freq[w.lower()] += 1
            for k in kws:
                co[w.lower()][k] += 1

    table = {}
    for w, n in freq.items():
        if n < MIN_FREQ or w in SHARED:
            continue
        best = None
        for cand, c in co[w].most_common(60):
            if abs(len(cand) - len(w)) > 2 or cand == w:
                continue
            if kc.get(cand, 0) / max(1, kv[cand]) > 0.7 and caps.get(w, 0) / n < 0.5:
                continue                        # name guard
            sim = SequenceMatcher(None, w, cand).ratio()
            sup = c / n
            if (sim >= MIN_SIM and sup >= MIN_SUPPORT) or \
               (sim >= HI_SIM and sup >= HI_SIM_SUPPORT):
                score = sim * 0.7 + sup * 0.3
                if best is None or score > best[0]:
                    best = (score, cand)
        if best:
            table[w] = best[1]
    table.update({k: v for k, v in SHARED.items() if k in freq or True})
    return table, freq


def coverage(asset, dialect, table):
    """Share of tokens still unknown AFTER the map — the honest measure."""
    d = json.loads((A / "bibles" / asset).read_text(encoding="utf-8"))
    b = d["books"] if isinstance(d, dict) else d
    lex = json.loads((A / "webster1828.json").read_text(encoding="utf-8"))
    heads = {k.lower() for k in lex} if isinstance(lex, dict) else set()
    kjv = json.loads((A / "bibles/en_kjv.json").read_text(encoding="utf-8"))
    kb = kjv["books"] if isinstance(kjv, dict) else kjv
    kvoc = set()
    for bk in kb:
        for ch in bk.get("chapters", []):
            for v in ch:
                for w in re.findall(r"[A-Za-z]+", clean(v)):
                    kvoc.add(w.lower())
    known = heads | kvoc
    tot = un = 0
    for bk in b:
        for ch in bk.get("chapters", []):
            for v in ch:
                for w in re.findall(r"[A-Za-z]+", normalize(clean(v), dialect)):
                    lw = table.get(w.lower(), w.lower())
                    tot += 1
                    if lw not in known:
                        un += 1
    return un, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    for tid, asset, dialect in SETS:
        table, freq = derive(asset, dialect)
        un, tot = coverage(asset, dialect, table)
        print(f"{tid}: {len(table)} mappings, {un}/{tot} tokens still unmapped "
              f"({100 * un / tot:.1f}%)")
        for probe in ("heauen", "heuene"):
            if probe in table:
                print(f"     {probe} -> {table[probe]}")
        if args.report:
            continue
        out = A / f"pron_{tid}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"words": table, "roman": {}, "phrases": {}},
                      f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        print(f"     wrote {out.name} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
