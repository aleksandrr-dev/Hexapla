# -*- coding: utf-8 -*-
"""Wycliffite Middle English -> IPA, for Kokoro's phoneme input.

WHY (owner decision, 2026-08-16)
--------------------------------
Wycliffe should sound like 1395, not like modern English: "If people want to
hear modern English, they will listen to the closer KJV."

Two earlier approaches were rejected, each for a measured reason:
  · **archaic_english.normalize** modernizes spelling. Right for Geneva (1.9%
    of tokens unknown after it runs) but wrong here — and it only reached 17.5%
    on Wycliffe, so the engine read Middle English spelling with MODERN letter
    values: "beestis" -> "BEAST-ess", "kynde" -> "KIND-ess". Neither period nor
    modern; the owner caught it by ear in Genesis 1.
  · **Phonetic respelling** (tools/middle_english.py) gets the vowels but can
    never produce /x/ for <gh>, because a modern voice reading "kh" says K.

▶ This module takes the third route: emit IPA and hand it to Kokoro's phoneme
path, bypassing grapheme-to-phoneme entirely.

⚠⚠ IT MUST BE KOKORO, NOT CHATTERBOX. Verified 2026-08-16:
    chatterbox.generate(text, language_id, ...)   <- TEXT ONLY, no phoneme hook
    kokoro   KPipeline.infer(model, ps, pack, s)  <- takes an IPA string
  So the owner's cloned voice (chatterbox) and accurate Middle English are
  MUTUALLY EXCLUSIVE with today's engines. He chose accuracy for Wycliffe and
  his own voice for Tyndale, whose 1525 English barely needs respelling.

⚠ Kokoro's phoneme vocabulary was checked, not assumed — 114 symbols, and it
  contains x(66) ː(158) ə(83) ɪ(102) χ(142) ɣ(139). The sounds this module
  needs are representable.

THE PHONOLOGY (late 14th c., pre-Great-Vowel-Shift)
---------------------------------------------------
Long vowels keep continental values; this is the whole reason Middle English
sounds foreign:
    ī  /iː/   kynde   kiːndə        ō(close) /oː/  good  goːd
    ē  /eː/   beestis beːstɪs       ō(open)  /ɔː/  goon  gɔːn
    ā  /aː/   name    naːmə         ū        /uː/  hous  huːs
Final -e is a schwa (variable by Chaucer's day; we pronounce it, which is the
conservative reading and what makes the metre work).
Consonants: <gh> = /x/, initial kn-/gn-/wr- fully sounded, <sch> = /ʃ/,
<ch> = /tʃ/, and the -ynge ending keeps its /g/: /ɪŋgə/.

⚠ NOT REACHABLE, and deliberately not faked: trilled r (we emit /r/), and the
open/close ē-ō distinction is only applied where the exception table says so —
getting it right everywhere needs etymology per word, not spelling.
"""
import re

# --------------------------------------------------------------- exceptions
# Highest-frequency Wycliffite forms, hand-checked. These BEAT the rules.
# The open/close vowel distinctions live here because spelling cannot predict
# them. Drawn from the top unknown-token list measured over the whole text.
WORDS = {
    # ── high-frequency forms added 2026-08-16 from a full-text frequency
    # scan (915,138 tokens). The rules mishandled the commonest SHORT words —
    # "he"->hɛ, "ye"->ɪɛ, "be"->bɛ — because a two-letter word has no room for
    # the magic-e rule to see a long vowel. These are the top ~60 by count and
    # take table coverage from 48.7% of tokens to ~75%.
    "he": "heː", "we": "weː", "ye": "jeː", "me": "meː", "be": "beː",
    "she": "ʃeː", "y": "iː", "a": "aː", "an": "an", "as": "as",
    "hym": "hɪm", "him": "hɪm", "hem": "hɛm", "her": "hɛr", "hers": "hɛrs",
    "my": "miː", "mi": "miː", "thy": "θiː", "fro": "frɔː", "on": "ɔn",
    "out": "uːt", "you": "juː", "vs": "ʊs", "us": "ʊs", "if": "ɪf",
    "but": "bʊt", "this": "ðɪs", "these": "ðeːzə", "tho": "θoː",
    "thingis": "θɪŋgɪs", "thing": "θɪŋg", "thynge": "θɪŋgə",
    "weren": "weːrən", "which": "hwɪtʃ", "whiche": "hwɪtʃə",
    "sones": "soːnəs", "sone": "soːnə", "israel": "ɪsraːɛl",
    "kyng": "kɪŋg", "kynges": "kɪŋgəs", "kyngis": "kɪŋgɪs",
    "forsothe": "fɔrsoːθə", "schalt": "ʃalt", "therfor": "ðɛrfɔr",
    "maad": "maːd", "dai": "dɛi", "daies": "dɛiəs", "do": "doː",
    "also": "alsoː", "go": "goː", "what": "hwat", "haue": "haːvə",
    "hath": "haθ", "han": "han", "seith": "sɛiθ", "sayde": "sɛidə",
    "into": "ɪntoː", "vpon": "ʊpɔn", "vp": "ʊp", "vnto": "ʊntoː",
    "whom": "hwoːm", "hou": "huː", "now": "nuː", "how": "huː",
    # function words
    "the": "ðə", "thee": "ðeː", "thi": "ðiː", "thin": "ðiːn", "thou": "ðuː",
    "bi": "biː", "by": "biː", "til": "til", "to": "toː", "of": "ɔf",
    "and": "and", "in": "ɪn", "is": "ɪs", "it": "ɪt", "his": "hɪs",
    "sche": "ʃeː", "thei": "ðɛi", "thai": "ðɛi", "hem": "hɛm",
    "hir": "hiːr", "hire": "hiːrə", "hise": "hiːzə", "oure": "uːrə",
    "youre": "juːrə", "ony": "ɔːniː", "eny": "ɛniː", "eche": "eːtʃə",
    "sich": "sɪtʃ", "swich": "swɪtʃ", "alle": "alːə", "al": "al",
    "not": "nɔt", "no": "noː", "ne": "nə", "for": "fɔr", "with": "wɪθ",
    "that": "ðat", "whanne": "hwanːə", "thanne": "θanːə", "ther": "ðɛːr",
    "wher": "hwɛːr", "here": "heːrə", "hidur": "hɪdur",
    # verbs
    "hadde": "hadːə", "seide": "sɛidə", "seie": "sɛiə", "seyn": "sɛin",
    "yyue": "jɪvə", "yaf": "jaf", "yeue": "jɛvə", "youen": "jɔːvən",
    "doon": "dɔːn", "doth": "doːθ", "goon": "gɔːn", "goth": "goːθ",
    "ben": "beːn", "beth": "beːθ", "was": "was", "were": "weːrə",
    "woot": "woːt", "wole": "woːlə", "wolde": "woːldə",
    "schal": "ʃal", "schulen": "ʃuːlən", "schulde": "ʃuːldə",
    "made": "maːdə", "make": "maːkə", "brynge": "brɪŋgə",
    "clepid": "klɛpid", "seiden": "sɛidən",
    # nouns the owner flagged, and their families
    "kynde": "kiːndə", "kyndes": "kiːndəs", "kyndis": "kiːndɪs",
    "beeste": "beːstə", "beestis": "beːstɪs", "beestes": "beːstəs",
    "puple": "puːplə", "puplis": "puːplɪs",
    "hous": "huːs", "housis": "huːsɪs",
    "erthe": "ɛrθə", "watris": "watrɪs", "watir": "watɪr",
    "soule": "suːlə", "soulis": "suːlɪs", "soul": "suːl",
    "lond": "lɔnd", "londis": "lɔndɪs", "yeer": "jeːr",
    "man": "man", "men": "mɛn", "womman": "wumːan",
    "god": "gɔd", "lord": "lɔrd", "hevene": "hɛvənə", "heuene": "hɛvənə",
    "liyt": "liːçt", "liif": "liːf", "lyf": "liːf", "lijf": "liːf",
    "nyyt": "niːçt", "niyt": "niːçt", "myyt": "miːçt",
    "doun": "duːn", "awei": "awɛi", "bifor": "biːfɔr", "bifore": "biːfɔrə",
    "aboute": "abuːtə", "withoute": "wɪθuːtə", "ayen": "ajeːn",
    "ayens": "ajeːns", "nouyt": "nuːxt", "ouyt": "uːxt",
    "lyuynge": "liːvɪŋgə", "lyuyng": "liːvɪŋg", "crepynge": "krɛpɪŋgə",
    "werk": "wɛrk", "werkis": "wɛrkɪs", "fruyt": "fryːt",
    "greet": "greːt", "grete": "greːtə", "litil": "lɪtɪl",
    "seynt": "sɛint", "spirit": "spɪrɪt", "sone": "soːnə",
    "fadir": "fadɪr", "modir": "moːdɪr", "brother": "broːðər",
}

# ------------------------------------------------------------------- clusters
# Longest-first. Applied to the remaining (rule-driven) words.
_CLUSTERS = [
    ("sch", "ʃ"), ("ssh", "ʃ"), ("sh", "ʃ"),
    ("tch", "tʃ"), ("ch", "tʃ"),
    ("th", "θ"),
    ("qu", "kw"), ("q", "k"), ("wh", "hw"),
    ("gh", "x"), ("3", "j"), ("y3", "ix"),
    ("ck", "k"), ("cc", "k"),
    ("ynge", "ɪŋgə"), ("yng", "ɪŋg"), ("inge", "ɪŋgə"), ("ing", "ɪŋg"),
]

# --------------------------------------------------------------------- vowels
# Digraphs first — these carry the pre-GVS long values.
_VOWELS = [
    ("ee", "eː"), ("ea", "ɛː"), ("ie", "iː"), ("oo", "oː"),
    ("ou", "uː"), ("ow", "uː"), ("oi", "ɔi"), ("oy", "ɔi"),
    ("ai", "ɛi"), ("ay", "ɛi"), ("ei", "ɛi"), ("ey", "ɛi"),
    ("au", "au"), ("aw", "au"), ("eu", "ɛu"), ("ew", "ɛu"),
    ("ii", "iː"), ("ij", "iː"), ("yy", "iː"), ("uu", "uː"),
    # 2026-10-05: «fruyt», «distruye», «suynge» — French ü, as fruyt already
    # is in WORDS. Without it «distruye» came out dɪstrʊɪɛ.
    ("uy", "yː"),
]
# "aw"/"ew" are diphthongs only when no vowel follows: «awey» is a-wey, not
# au-ɛ (2026-10-05 probe).
_W_DIGRAPHS = {"aw", "ew"}

_SINGLE = {"a": "a", "e": "ɛ", "i": "ɪ", "o": "ɔ", "u": "ʊ", "y": "ɪ"}

_CONS = {
    "b": "b", "c": "k", "d": "d", "f": "f", "g": "g", "h": "h", "j": "dʒ",
    "k": "k", "l": "l", "m": "m", "n": "n", "p": "p", "r": "r", "s": "s",
    "t": "t", "v": "v", "w": "w", "x": "ks", "z": "z",
}

_WORD = re.compile(r"[A-Za-z3]+")
# Magic-e: vowel + single consonant + final e  ->  the vowel is LONG.
# Not after a second vowel: «deeme» is ee+m+e, and the old pattern lengthened
# the second e of the digraph too (deːːmə).
_MAGIC_E = re.compile(r"(?<![aeiouy])([aeiouy])([bcdfgklmnprstvwz])e$")
# Placeholder for consonantal y (/j/), so the letter loop cannot read it as a
# vowel or as <j> = /dʒ/.
_JAY = "ȷ"
_LONG = {"a": "aː", "e": "eː", "i": "iː", "o": "oː", "u": "uː", "y": "iː"}

# ⚠ <gh> IS ALLOPHONIC IN MIDDLE ENGLISH, and kokoro can express both halves
# (ç = 'yes', x = 'yes' in the 114-symbol vocab, checked 2026-08-16):
#     after a FRONT vowel (i, y, e)  ->  /ç/   liyt  = liːçt   (palatal)
#     after a BACK  vowel (a, o, u)  ->  /x/   nouyt = nuːxt   (velar)
# Emitting /x/ everywhere, as the first version did, is wrong for exactly the
# words a listener notices most — "light", "night", "might".
_FRONT = "iey"
# <y> stands for yogh only after i, o, u («riyt», «niy», «nouyt», «thouy»);
# after a/e it is the second half of a diphthong («awey», «dai»), and the old
# pattern turned «awey» into a(w)eç.
_GH = re.compile(r"([aeiouy])gh(?=[td]|$)|([iou])y(?=[td]|$)")

# ME still had real geminates: "alle" /alːə/, "hadde" /hadːə/. Modern English
# lost them, so a G2P would never produce this — it is one of the clearest
# period markers available and costs one rule.
_GEMINATE = re.compile(r"([bcdfgklmnprstvz])\1")


def _gh_rule(w):
    def sub(m):
        v = m.group(1) or m.group(2)
        if v in "iy":
            # The vowel before a palatal yogh is long: «riyt» riːçt, «niy»
            # niːç. "ii" is the long-i digraph in _VOWELS.
            return "iiç"
        return v + ("ç" if v in _FRONT else "x")
    return _GH.sub(sub, w)


def _uv(word):
    """Wycliffite <u> is /v/ between vowels, <v> is /u/ initially.

    "lyuynge" is *living*, "vnresonable" is *unreasonable* — the u/v split is
    typographic, not phonetic, and getting it wrong makes nonsense of the word.
    """
    word = re.sub(r"(?<=[aeiouy])u(?=[aeiouy])", "v", word)
    word = re.sub(r"^v(?=[bcdfgklmnprstvwz])", "u", word)
    return word


_PASS = "ːəɛɪɔʊʃθðŋxdʒç"   # IPA already emitted by an earlier rule
_DROPPED = []               # (word, char) the letter loop could not place


def word_to_ipa(word):
    low = word.lower()
    if low in WORDS:
        return WORDS[low]
    w = _uv(low)
    # Soft c before a front vowel, judged on the LETTERS before final -e
    # becomes a schwa: «merci» mɛrsiː, «abstynence» ...ɛnsə (was mɛrkɪ, ɛnkə).
    w = re.sub(r"c(?=[eiy])", "s", w)
    # Consonantal y before a vowel at the start: «yatis» jatɪs (was ɪatɪs).
    w = re.sub(r"^y(?=[aeo])", _JAY, w)
    # Homorganic lengthening: i/y before -nd/-ld/-mb is long, as «kynde»
    # already is in WORDS: «mynde» miːndə, «blynde» bliːndə (were short).
    w = re.sub(r"(?<![aeiouy])[iy](?=(?:nd|ld|mb)(?:e|is|es)?$)", "ii", w)
    w = _gh_rule(w)                     # before vowels, so it sees the letters
    w = _GEMINATE.sub(r"\1ː", w)        # alle -> alːe, hadde -> hadːe
    m = _MAGIC_E.search(w)
    if m:
        w = w[:m.start()] + _LONG[m.group(1)] + m.group(2) + "ə"
    elif re.fullmatch(r"[^aeiouy]+e", w):
        # A monosyllable whose only vowel is the final e has a long e:
        # «sle» sleː, «tre» treː (was slɛ).
        w = w[:-1] + "ee"               # "ee" is the eː digraph below
    elif len(w) > 3 and w.endswith("e") and (w[-2] in "ːbcdfgklmnprstvwz"):
        # Final -e is a schwa even after a geminate ("fulle" -> fʊlːə), which
        # the magic-e rule cannot see because "lː" is not a single consonant.
        w = w[:-1] + "ə"
    elif len(w) > 3 and w[-1] in "iy" and w[-2] in "bcdfgklmnprstvz":
        # Final -i/-y of a polysyllable is long: «merci», «oneli», «greetli».
        w = w[:-1] + "ii"
    # Hebrew/Greek <ch> is /k/ at the end of a name: «Amalech», «Balaach»
    # (was amalɛtʃ). Lower-case words keep /tʃ/; «Which», «Sich» etc. are in
    # WORDS and never reach here.
    if word[:1].isupper() and w.endswith("ch"):
        w = w[:-2] + "k"
    out = []
    i = 0
    while i < len(w):
        for src, dst in _CLUSTERS:
            if w.startswith(src, i):
                out.append(dst); i += len(src); break
        else:
            for src, dst in _VOWELS:
                if (w.startswith(src, i) and not
                        (src in _W_DIGRAPHS and i + 2 < len(w)
                         and w[i + 2] in "aeiouy")):
                    out.append(dst); i += len(src); break
            else:
                c = w[i]
                if c in "aeiouy" and c in _SINGLE:
                    out.append(_SINGLE[c])
                elif c in _CONS:
                    out.append(_CONS[c])
                elif c == _JAY:
                    out.append("j")
                elif c in _PASS:
                    out.append(c)
                else:
                    # Never silently: the old loop dropped /ç/ here, so
                    # «riyt» was read «rit». screen_corpus() counts these.
                    _DROPPED.append((word, c))
                i += 1
    return "".join(out)


def screen_corpus(path):
    """0-token check over EVERY verse: words whose letters the loop dropped.

    Returns (n_tokens, Counter of (word, char)). A non-empty counter is a
    finding. Known-bad control: with "ç" removed from _PASS, «riyt» must
    appear here.
    """
    import json
    from collections import Counter
    with open(path, encoding="utf-8") as f:
        bible = json.load(f)
    del _DROPPED[:]
    n = 0

    def walk(x):
        nonlocal n
        if isinstance(x, str):
            for m in _WORD.finditer(x.replace("`", "")):
                n += 1
                word_to_ipa(m.group(0))
        elif isinstance(x, list):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            for y in x.values():
                walk(y)
    walk(bible)
    return n, Counter(_DROPPED)


def to_ipa(text):
    """Verse text -> IPA for Kokoro. Punctuation is kept: it drives prosody."""
    # ⚠⚠ KOKORO'S /g/ IS «ɡ» (U+0261), NOT ASCII «g» — the vocab has no
    #   ASCII g, so the model DROPS it: «God» would be said «od». Every rule
    #   and WORDS entry here writes ASCII g, so convert once, at the boundary.
    #   Found 2026-10-05 by diffing the emitted symbols against the model's
    #   config.json vocab (49,010 g's over the asset) — the IPA path had never
    #   actually run, so no ear had heard it. A hyphen is not in the vocab
    #   either; between two words it becomes a space, not a glue.
    ipa = _WORD.sub(lambda m: word_to_ipa(m.group(0)), text.replace("-", " "))
    return ipa.replace("g", "ɡ")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.argv[1:2] == ["--screen"]:
        # python tools/me_phonemes.py --screen [asset]   rc 1 = letters dropped
        p = (sys.argv[2] if len(sys.argv) > 2 else
             "C:/Projects/Hexapla/app/src/main/assets/bibles/enm_wycliffe.json")
        n, bad = screen_corpus(p)
        print(f"tokens {n}  dropped-letter tokens {sum(bad.values())}  "
              f"distinct {len(bad)}")
        for (w, c), k in bad.most_common(30):
            print(f"  {k:6}  {w!r}  char {c!r}")
        sys.exit(1 if bad else 0)
    for t in sys.argv[1:] or [
        "In the bigynnyng God made of nouyt heuene and erthe.",
        "And God seide, The erthe brynge forth a lyuynge soul in his kynde, "
        "werk beestis, and crepynge beestis.",
    ]:
        print(f"{t}\n  -> {to_ipa(t)}\n")
