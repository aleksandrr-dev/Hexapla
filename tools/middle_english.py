# -*- coding: utf-8 -*-
"""Respell Wycliffite Middle English so a MODERN English TTS voice produces
something close to late-14th-century pronunciation.

WHY THIS EXISTS (owner decision, 2026-08-16)
--------------------------------------------
Wycliffe was rendering with the archaic_english normalizer, which MODERNIZES
spelling so a modern voice says the modern word — the right call for Geneva
(1.9% of tokens unknown after normalization) but wrong here. Measured on the
Wycliffe text, 17.5% of tokens were still unknown after normalization, so the
engine was reading Middle English spelling with MODERN letter values: "beestis"
came out "BEAST-ess", "kynde" as "KIND-ess". That is neither modern English nor
period pronunciation — the one outcome with nothing to recommend it.

▶ The owner's call: **Wycliffe should sound like 1395.** "If people want to
hear modern English, they will listen to the closer KJV."

THE LINGUISTICS, AND WHAT IS ACTUALLY REACHABLE
-----------------------------------------------
Late Middle English sits BEFORE the Great Vowel Shift, so the long vowels have
roughly continental values:

    ī (y, i…e)   /iː/   kynde   ->  KEEN-duh
    ē (ee, e…e)  /eː/   beestis ->  BAY-stis
    ā (a…e)      /aː/   name    ->  NAH-muh
    ō (oo, o…e)  /oː/   good    ->  GOHD
    ū (ou, ow)   /uː/   hous    ->  HOOS

plus: final -e as a light schwa (already variable by Chaucer's day), fully
pronounced initial kn-/gn-/wr-, and <gh> as /x/ (the Scots "loch" sound).

⚠⚠ TWO THINGS A MODERN TTS CANNOT DO, AND THIS FILE DOES NOT PRETEND TO:
  · **/x/ for <gh>.** No modern English voice has it. Rendering "night" as
    "nikht" makes the engine say a hard K, which is WORSE than the silent gh
    a modern reader expects. We leave <gh> alone — a known, deliberate
    departure from authenticity.
  · **Trilled r, and the finer unstressed vowels.** Out of reach entirely.
So the honest label for the output is **"Middle-English-flavoured"**, not a
scholarly reconstruction. It gets the vowel system — which is what a listener
actually notices — and abandons the consonant detail that cannot be reached.

⚠ ORDER MATTERS. Digraphs (ee, ou, gh…) must be handled before single vowels,
and the whole-word table must win over the rules: it exists precisely for the
words the rules get wrong.
"""
import re
import unicodedata

# ---------------------------------------------------------------- whole words
# High-frequency Wycliffite forms, respelled by hand. These BEAT the rules.
# Ordered by how often they occur in the text (the top-15 unknown-token list
# from the 2026-08-16 coverage scan is all here).
WORDS = {
    # pronouns / function words
    "thi": "thee", "thin": "theen", "bi": "bee", "til": "till",
    "ony": "OH-nee", "eny": "EH-nee", "sich": "sich", "swich": "swich",
    "hem": "hem", "hire": "HEE-ruh", "hir": "heer", "sche": "shay",
    "thei": "thay", "thai": "thay", "hise": "HEE-zuh",
    "oure": "OO-ruh", "youre": "YOO-ruh", "eche": "AY-chuh",
    # very common verbs
    "hadde": "HAH-duh", "seide": "SAY-duh", "seie": "SAY-uh",
    "seyn": "sayn", "yyue": "YIH-vuh", "yaf": "yahf", "yeue": "YEH-vuh",
    "doon": "dohn", "goon": "gohn", "ben": "bayn", "beth": "bayth",
    "woot": "woht", "wole": "WOH-luh", "wolde": "WOHL-duh",
    "schal": "shahl", "schulen": "SHOO-len", "schulde": "SHOOL-duh",
    # nouns the owner flagged, plus their family
    "kynde": "KEEN-duh", "kyndes": "KEEN-duhs", "kyndis": "KEEN-dis",
    "beeste": "BAY-stuh", "beestis": "BAY-stis", "beestes": "BAY-stuhs",
    "puple": "POO-pluh", "puplis": "POO-plis",
    "hous": "hoos", "housis": "HOO-sis",
    "yeer": "yayr", "yeeris": "YAY-ris",
    "erthe": "AIR-thuh", "watris": "WAH-tris", "watir": "WAH-tir",
    "soule": "SOO-luh", "soulis": "SOO-lis",
    "lond": "lohnd", "londis": "LOHN-dis",
    "man": "mahn", "men": "mayn", "womman": "WOO-mahn",
    "God": "Gohd", "lord": "lohrd", "hevene": "HEH-veh-nuh",
    "liyt": "leekht", "liif": "leef", "lyf": "leef",
    # adverbs / prepositions
    "doun": "doon", "awei": "ah-WAY", "bifor": "bee-FOR",
    "bifore": "bee-FOH-ruh", "aboute": "ah-BOO-tuh", "withoute": "with-OO-tuh",
    "ayen": "ah-YAYN", "ayens": "ah-YAYNS", "thanne": "THAH-nuh",
    "whanne": "WHAH-nuh", "wher": "wair", "ther": "thair", "here": "HAY-ruh",
    "saeth": "SAY-eth", "weth": "wayth",
}

# ------------------------------------------------------------------- digraphs
# Applied BEFORE the single-vowel rules. Longest patterns first.
_DIGRAPHS = [
    (re.compile(r"ee"), "ay"),      # /eː/  beest -> bayst
    (re.compile(r"oo"), "oh"),      # /oː/  good  -> gohd
    (re.compile(r"ou"), "oo"),      # /uː/  hous  -> hoos
    (re.compile(r"ow"), "oo"),      # /uː/  now   -> noo
    (re.compile(r"ie"), "ee"),      # /iː/
    (re.compile(r"ai"), "eye"),     # /ai/ was still a diphthong
    (re.compile(r"ei"), "ay"),
    (re.compile(r"au"), "ow"),
]

# --------------------------------------------------------------- single vowels
# Long-vowel rule: V + consonant + silent final e  ->  continental value.
_MAGIC_E = [
    (re.compile(r"\by([bcdfghklmnprstvwz])e\b"), r"ee\1uh"),
    (re.compile(r"([bcdfgklmnprstvwz])y([bcdfgklmnprstvwz])e\b"), r"\1ee\2uh"),
    (re.compile(r"([bcdfgklmnprstvwz])i([bcdfgklmnprstvwz])e\b"), r"\1ee\2uh"),
    (re.compile(r"([bcdfgklmnprstvwz])a([bcdfgklmnprstvwz])e\b"), r"\1ah\2uh"),
    (re.compile(r"([bcdfgklmnprstvwz])o([bcdfgklmnprstvwz])e\b"), r"\1oh\2uh"),
]

# The -is / -ys plural and 3sg ending is a SYLLABLE in ME: beestis = BAY-stis.
_ENDINGS = [
    (re.compile(r"([bcdfgklmnprstvwz])is\b"), r"\1is"),
    (re.compile(r"([bcdfgklmnprstvwz])ys\b"), r"\1is"),
    (re.compile(r"([bcdfgklmnprstvwz])eth\b"), r"\1eth"),
]

# Final -e as a light schwa, but never on a one-syllable stub ("the", "he").
_FINAL_E = re.compile(r"\b([a-z]{3,}?[bcdfgklmnprstvwz])e\b")

_WORD = re.compile(r"[A-Za-z]+")


def _respell_one(w):
    low = w.lower()
    if low in WORDS:
        out = WORDS[low]
    else:
        out = low
        for pat, rep in _DIGRAPHS:
            out = pat.sub(rep, out)
        for pat, rep in _MAGIC_E:
            out = pat.sub(rep, out)
        for pat, rep in _ENDINGS:
            out = pat.sub(rep, out)
        out = _FINAL_E.sub(r"\1uh", out)
    if w[0].isupper():
        out = out[0].upper() + out[1:]
    return out


def respell(text):
    """Middle-English-flavoured respelling of a verse, for TTS input only.

    ⚠ NEVER store this in the asset or show it to a reader — the app must keep
    displaying the real Wycliffite text. This is a pronunciation hint for the
    synthesizer, the same role pron_*.json plays for the device voice.
    """
    return _WORD.sub(lambda m: _respell_one(m.group(0)), text)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for t in sys.argv[1:] or [
        "And God seide, The erthe brynge forth a lyuynge soul in his kynde, "
        "werk beestis, and crepynge beestis",
        "In the bigynnyng God made of nouyt heuene and erthe",
    ]:
        print(f"{t}\n  -> {respell(t)}\n")
