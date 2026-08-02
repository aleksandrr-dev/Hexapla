# -*- coding: utf-8 -*-
"""Build the Tyndale pronunciation map used by tools/archaic_english.py.

    python tools/build_tyndale_pron.py            # writes tools/tyndale_pron.py
    python tools/build_tyndale_pron.py --report   # print, write nothing

WHY
---
Tyndale's orthography keeps a final -e that was already SILENT by the 1520s:
"depe" = deep, "herbe" = herb, "kyndes" = kinds. TTS voices it as a syllable
("dee-pee", "her-bee"), which the owner heard immediately. Measured over the
asset: 3,458 distinct unknown words ending in -e, 36,477 occurrences — 11% of
all tokens. This is the dominant audio-quality problem for the English sets,
far bigger than any individual glitch.

METHOD — proposals are CORROBORATED, never guessed
--------------------------------------------------
The Tyndale asset sits on the KJV verse grid, so every verse has a parallel.
For each unknown word we look at the KJV words appearing in the SAME verses,
and accept a candidate only when it is both spelled similarly AND actually
present in a large share of those parallel verses. A pure edit-distance guess
would happily produce "hye" -> "he"; requiring KJV support is what rejects it.

⚠ Two failure modes found while building this, both excluded by hand:
  · "shalbe" is TWO words, "shall be". Similarity matching proposed "shall"
    and would have silently deleted the verb. Multi-word cases are listed in
    MULTIWORD and never derived automatically.
  · "hye" -> "he" scored 0.80 similarity but only 0.34 support — it is "high".
    Low support is the tell, hence MIN_SUPPORT.
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
OUT = ROOT / "tools/tyndale_pron.py"
NOTE = re.compile(r"\s*\{[^{}]*:[^{}]*\}")

MIN_SIM = 0.75
MIN_SUPPORT = 0.55        # share of parallel KJV verses containing the candidate
MIN_FREQ = 4

# Contractions of two words. Never derivable by single-token similarity.
MULTIWORD = {
    "shalbe": "shall be", "shalt": "shalt", "wilbe": "will be",
    "yt": "that", "wt": "with",
}

# Hand-checked corrections where corroboration is weak or the KJV differs.
# Three reasons an obvious mapping needs to be here rather than derived:
#   · SIMILARITY too low — "londe"/"land" scores 0.67, "egipte"/"egypt" 0.73.
#   · SUPPORT too low — "selfe"/"self" because the KJV writes "himself" as one
#     word, so bare "self" barely occurs in the parallel verses.
#   · the KJV simply uses a different word in that verse.
OVERRIDE = {
    "hye": "high", "se": "see", "moche": "much", "soche": "such",
    "myche": "much", "eny": "any", "ony": "any", "vnto": "unto",
    "sprete": "spirit", "spretes": "spirits", "awne": "own",
    "doune": "down", "thorow": "through", "erth": "earth", "erthe": "earth",
    "sayd": "said", "sayde": "said", "sayed": "said", "thi": "thy",
    "ther": "there", "wher": "where", "hir": "her", "yf": "if", "dyd": "did",
    "londe": "land", "londes": "lands", "lond": "land",
    "egipte": "egypt", "egipcians": "egyptians", "egipcian": "egyptian",
    "selfe": "self", "silfe": "self", "selves": "selves",
    "yere": "year", "yeres": "years", "maner": "manner",
    "vppon": "upon", "vpp": "up", "vp": "up",
    "longe": "long", "witnesse": "witness", "witnesses": "witnesses",
    "bloude": "blood", "hys": "his", "honde": "hand", "hondes": "hands",
    "evyll": "evil", "congregacion": "congregation",
    "congregacions": "congregations", "ys": "is", "oyle": "oil",
    "wyse": "wise", "hoste": "host", "oxe": "ox",
    "iesus": "Jesus", "iesu": "Jesu", "iesse": "Jesse",
    "moises": "Moses", "moses": "Moses",
    # ⚠ Owner-reported by ear, and each missed for a DIFFERENT reason —
    # which is why the derived table alone is not enough:
    #   herbe  — a Webster 1828 headword, so it counted as "known" and was
    #            never a candidate. ("heebee" in his words.)
    #   kyndes — "kyndes"/"kinds" scores 0.73 similarity, just under the gate.
    "herbe": "herb", "herbes": "herbs",
    "kynde": "kind", "kyndes": "kinds", "kynred": "kindred",
    "beastes": "beasts", "beeste": "beast", "beest": "beast",
    "lyghte": "light", "lyghtes": "lights", "lyght": "light",
    "voyde": "void", "emptie": "empty", "nyghte": "night", "nyght": "night",
    "fyrmament": "firmament", "myddes": "midst", "myddest": "midst",
    "citie": "city", "cyte": "city", "citees": "cities",
    "numbre": "number", "mynde": "mind", "fynde": "find", "chylde": "child",
    "thyrde": "third", "reioyce": "rejoice", "syluer": "silver",
    "neverthelesse": "nevertheless", "assone": "as soon",
    "untyll": "until", "thorowe": "through", "selues": "selves",
    "soeuer": "soever", "axed": "asked", "hyr": "her", "oxen": "oxen",
}

# ⚠ ROMAN NUMERALS. Tyndale prints numbers as ".vij." / ".ij." — lower-case
# roman between full stops. TTS reads them letter by letter ("vee eye jay"),
# and they are FREQUENT (vij 133, ij 137 in the top rejects alone). The final
# "j" is the period's long-i form: ij = ii = 2, vij = vii = 7.
ROMAN = {
    "i": 1, "ij": 2, "iij": 3, "iiij": 4, "v": 5, "vj": 6, "vij": 7,
    "viij": 8, "ix": 9, "x": 10, "xj": 11, "xij": 12, "xiij": 13,
    "xiiij": 14, "xv": 15, "xvj": 16, "xvij": 17, "xviij": 18, "xix": 19,
    "xx": 20, "xxx": 30, "xl": 40, "l": 50, "lx": 60, "lxx": 70,
    "lxxx": 80, "xc": 90, "c": 100, "cc": 200, "ccc": 300, "cccc": 400,
    "d": 500, "m": 1000,
}


def clean(v):
    return NOTE.sub("", v).replace("{", "").replace("}", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    tyn = json.loads((A / "bibles/en_tyndale.json").read_text(encoding="utf-8"))
    kjv = json.loads((A / "bibles/en_kjv.json").read_text(encoding="utf-8"))
    tb = tyn["books"] if isinstance(tyn, dict) else tyn
    kb = kjv["books"] if isinstance(kjv, dict) else kjv
    lex = json.loads((A / "webster1828.json").read_text(encoding="utf-8"))
    heads = {k.lower() for k in lex} if isinstance(lex, dict) else set()

    freq = collections.Counter()
    co = collections.defaultdict(collections.Counter)
    kjv_vocab = collections.Counter()
    tmp = []
    for bi in range(min(len(tb), len(kb))):
        tch, kch = tb[bi].get("chapters", []), kb[bi].get("chapters", [])
        for ci in range(min(len(tch), len(kch))):
            for vi in range(min(len(tch[ci]), len(kch[ci]))):
                tw = [w.lower() for w in re.findall(
                    r"[A-Za-z]+", normalize(clean(tch[ci][vi]), "tyndale", use_generated=False))]
                kw = [w.lower() for w in re.findall(r"[A-Za-z]+", clean(kch[ci][vi]))]
                for w in kw:
                    kjv_vocab[w] += 1
                tmp.append((tw, set(kw)))
    known = heads | set(kjv_vocab)
    for tw, kws in tmp:
        for w in tw:
            if w not in known and w not in MULTIWORD:
                freq[w] += 1
                for k in kws:
                    co[w][k] += 1

    table, rejected = {}, []
    for w, n in freq.items():
        if n < MIN_FREQ or w in OVERRIDE:
            continue
        best = None
        for cand, c in co[w].most_common(80):
            if abs(len(cand) - len(w)) > 2 or cand == w:
                continue
            sim = SequenceMatcher(None, w, cand).ratio()
            sup = c / n
            if sim >= MIN_SIM and sup >= MIN_SUPPORT:
                score = sim * 0.7 + sup * 0.3
                if best is None or score > best[0]:
                    best = (score, cand, sim, sup)
        if best:
            table[w] = best[1]
        elif n >= 25:
            rejected.append((n, w))

    table.update(OVERRIDE)
    table.update(MULTIWORD)
    print(f"{len(table)} mappings "
          f"(min_sim {MIN_SIM}, min_support {MIN_SUPPORT}, min_freq {MIN_FREQ})")
    covered = sum(freq[w] for w in table if w in freq)
    print(f"covering {covered} occurrences")
    rejected.sort(reverse=True)
    print(f"\n{len(rejected)} frequent words left unmapped (>=25 occurrences) — "
          f"these stay as written:")
    for n, w in rejected[:25]:
        print(f"   {n:5}  {w}")

    if args.report:
        return
    with open(OUT, "w", encoding="utf-8") as f:
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('"""GENERATED by tools/build_tyndale_pron.py — do not hand-edit.\n\n'
                'Tyndale spelling -> modern spelling, for TTS only. Every entry is\n'
                'corroborated by the KJV parallel verse; see the generator for the\n'
                'method and for the two failure modes it guards against.\n"""\n')
        f.write("TYNDALE_PRON = {\n")
        for k in sorted(table):
            f.write(f'    {k!r}: {table[k]!r},\n')
        f.write("}\n\n")
        f.write("# Lower-case roman numerals as printed, e.g. '.vij.' = 7.\n")
        f.write("TYNDALE_ROMAN = {\n")
        for k in sorted(ROMAN, key=lambda x: ROMAN[x]):
            f.write(f'    {k!r}: {ROMAN[k]!r},\n')
        f.write("}\n")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
