# -*- coding: utf-8 -*-
"""Build app/src/main/assets/bibles/ka_bakar.json from the TITUS Bakar dump.

    python tools/build_bakar.py --dry-run   # report only, write nothing
    python tools/build_bakar.py             # build + assert + report

Input : titus_bakar/extracted/bakar_raw.json  (tools/extract_bakar.py)
Spec  : Hexapla-releases/research/BAKAR_CONVERTER_SPEC.md — read it first.
Census: Hexapla-releases/research/bakar_extraction_census.md — the authority
        for every anomaly resolved below; each site is named there.

Bakar 1743 Moscow, Georgian, FULL CANON (owner, 2026-07-20), under Prof. Jost
Gippert's TITUS grant (credit already in sources_text alongside the Zohrab).

★ STATUS: SECOND PASS. Mechanical bulk + every anomaly the census DECODED is
now handled: label normalization, rubric/colophon extraction, continuation and
pipe rejoining, positional repair of print-typo label cascades, psalm titles,
the Job 19 margin block, Esther's additions, book names from the print's own
index. What remains is listed by the build report itself and in
`CURATION REMAINING` below — ~21 sites that need a seam READ, plus the whole
versemap. Nothing here guesses: a site the code cannot resolve from evidence
is reported, not repaired.

⚠⚠ MAP BY PART NUMBER, NEVER BY BOOK LABEL. The label `Jud.` is used for BOTH
Judith (part028, «წიგნი ივდითისა») and Jude (part086). A label-keyed dict
silently collides them — the same class of trap as Zohrab's `Esr.II` prefix,
which merged Ezra into Nehemiah.

⚠ NATIVE NUMBERING IS KEPT (spec: authentic-as-printed). The KJV-grid pairing
is the versemap's job, not this converter's. Do not "fix" a chapter toward the
KJV verse count here.
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, OrderedDict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).parent.parent
ASSETS = REPO / "app" / "src" / "main" / "assets" / "bibles"
RAW = Path("C:/Projects/Hexapla-releases/titus_bakar/extracted/bakar_raw.json")
OUT = ASSETS / "ka_bakar.json"
RUBRICS_OUT = REPO / "app" / "src" / "main" / "assets" / "rubrics_bak.json"

# ---------------------------------------------------------------- slot map
# part number -> app slot. Derived from the dump's own book labels and Georgian
# preambles, checked against the spec's §1 table.
SLOT = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 6, 15: 7,          # Gen..Ruth
    16: 8, 17: 9, 18: 10, 19: 11,                                   # Reg.I-IV
    20: 12, 21: 13,                                                 # Chronicles
    23: 14, 24: 15,                                                 # Ezra, Nehemiah
    29: 16, 30: 17, 31: 18, 33: 19, 34: 20, 35: 21,                 # Esth..Cant
    38: 22, 39: 23,                                                 # Isaiah, Jeremiah
    40: 24, 41: 24,                                                 # Lam.Jer. + Or.Jer. -> Lamentations
    44: 25, 45: 26,                                                 # Ezekiel, Daniel
    46: 27, 47: 28, 48: 29, 49: 30, 50: 31, 51: 32,                 # the Twelve, print order
    52: 33, 53: 34, 54: 35, 55: 36, 56: 37, 57: 38,                 #   = canonical order here
    61: 39, 62: 40, 63: 41, 64: 42, 65: 43, 66: 44, 67: 45, 68: 46, # NT
    69: 47, 70: 48, 71: 49, 72: 50, 73: 51, 74: 52, 75: 53, 76: 54,
    77: 55, 78: 56, 79: 57, 80: 58, 81: 59, 82: 60, 83: 61, 84: 62,
    85: 63, 86: 64, 87: 65,
    25: 66,   # Esr.I_(Esr.III)   = 1 Esdras
    26: 67,   # Esr._III_(Esr._IV) = 2 Esdras   ★ slot empty in every asset
    27: 68,   # Tobit
    28: 69,   # Judith            ⚠ label 'Jud.' collides with Jude (part086)
    36: 70,   # Wisdom
    37: 71,   # Sirach
    42: 72,   # Baruch
    43: 73,   # Epistle of Jeremiah  ★ slot empty in every asset
    22: 74,   # Prayer of Manasses
    58: 75, 59: 76, 60: 77,                                         # 1-3 Maccabees
}
SKIP = {32}          # Od. — the census proved it is a table of contents, not text

# ---------------------------------------------------------------- book names
# From the print's OWN index (part003 `Ind.`, the 77 line-units), trimmed to a
# display name. EVERY name is asserted below to be a contiguous substring of
# the index line it came from, so a name cannot be invented — the Zohrab rule.
# (index line -> slot) is curated, never positional: the print's Pauline list
# carries a spurious extra «კოლასელთა» entry at line 65, which is skipped.
NAME_SRC = {
    0: (1, "შესაქმე"), 1: (2, "გამოსლვათა"), 2: (3, "ლევიტელთა"),
    3: (4, "რიცხვთა"), 5: (6, "ისონავესი"),
    6: (7, "მსაჯულთა"), 7: (8, "რუთ"),
    8: (9, "პირველი მეფეთა"), 9: (10, "მეორე მეფეთა"),
    10: (11, "მესამე მეფეთა"), 11: (12, "მეოთხე მეფეთა"),
    12: (13, "პირველი ნეშტთა"), 13: (14, "მეორე ნეშტთა"),
    14: (15, "პირველი ეზდრა"), 15: (16, "ნემია"),
    16: (21, "ესთერ"), 17: (22, "იობ"), 18: (23, "ფსალმუნი"),
    19: (24, "იგვნი სოლომონისნი"), 20: (25, "ეკლესიასტე"),
    21: (26, "ქება ქებათა"),
    22: (29, "ესაია"), 23: (30, "იერემია"), 24: (31, "გოდება იერემიასი"),
    25: (33, "ეზეკია"), 26: (34, "დანიელ"),
    27: (35, "იოსია"), 28: (36, "იოელ"), 29: (37, "ამოს"), 30: (38, "აბდია"),
    31: (39, "იონა"), 32: (40, "მიქია"), 33: (41, "ნაუმ"), 34: (42, "ამბაკომ"),
    35: (43, "სოფონია"), 36: (44, "ანგია"), 37: (45, "ზაქარია"), 38: (46, "მალაქია"),
    39: (50, "სახარება მათესი"), 40: (51, "სახარება მარკოზისი"),
    41: (52, "სახარება ლუკასი"), 42: (53, "სახარება იონესი"),
    43: (54, "საქმე მოციქულთა"),
    44: (62, "ჰრომაელთა მიმართ"), 45: (63, "კორინთელთა მიმართ ებისტოლე პირველი"),
    46: (64, "კორინთელთა მიმართ ებისტოლე მეორე"), 47: (66, "გალატელთა მიმართ"),
    48: (67, "ეფესელთა მიმართ"), 49: (68, "ფილიპელთა მიმართ"),
    50: (69, "კოლასელთა მიმართ"),
    51: (70, "თესალონიკელთა მიმართ ებისტოლე პირველი"),
    52: (71, "თესალონიკელთა მიმართ ებისტოლე მეორე"),
    53: (72, "ტიმოთეს მიმართ ებისტოლე პირველი"),
    54: (73, "ტიმოთეს მიმართ ებისტოლე მეორე"),
    55: (74, "ტიტეს მიმართ"), 56: (75, "ფილიმონის ებისტოლისა"),
    57: (76, "ებრაელთა მიმართ"),
    58: (55, "კათოლიკე . იაკობისი"), 59: (56, "კათოლიკე პეტრესი პირველი"),
    60: (57, "კათოლიკე პეტრესი მეორე"), 61: (58, "კათოლიკე იოანესი პირველი"),
    62: (59, "კათოლიკე იოანესი მეორე"), 63: (60, "კათოლიკე იოანესი მესამე"),
    64: (61, "კათოლიკე იუდასი"), 65: (77, "იოანეს განცხადებაჲ"),
    66: (17, "მეორე ეზდრა"), 67: (18, "მესამე ეზდრა"),
    68: (19, "ტობია"), 69: (20, "ივდით"),
    70: (27, "სიბრძნე სოლომონისი"), 71: (28, "ისო ზირაქისი"),
    72: (32, "ბარუქ"),
    75: (47, "პირველი მაკაბელთა"), 76: (48, "მეორე მაკაბელთა"),
    77: (49, "მესამე მაკაბელთა"),
}
# Where the index line is unusable, the name comes from the book's OWN
# PREAMBLE instead, substring-asserted against it exactly the same way.
# Deuteronomy is here because its index line spells "second" as the numeral
# «ბ̂» («ბ̂ სჯულთა»), which is apparatus, not a readable name; the preamble
# spells it out.
NAME_FROM_PREAMBLE = {
    4: (12, "მეორე შჯულისა"),                # Deuteronomy
}
# Two units have no index line of their own — the print folds the Epistle of
# Jeremiah into Baruch's entry (as its chapter 6) and gives the Prayer of
# Manasses none. Their names come from their own CHAPTER preamble, and are
# substring-asserted against it the same way.
NAME_FROM_CHAPTER = {
    73: (43, "6", "ებისტოლე ბრძნისა იერემიაჲსი"),
    74: (22, "1", "ლოცვა მანასე მეფისა"),
}

# ---------------------------------------------------------------- numerals
# Georgian alphabetic numerals, in alphabet order (note ჲ = 60, between ნ and ო).
_NUM_LETTERS = [
    ("ა", 1), ("ბ", 2), ("გ", 3), ("დ", 4), ("ე", 5), ("ვ", 6), ("ზ", 7),
    ("ჱ", 8), ("თ", 9),
    ("ი", 10), ("კ", 20), ("ლ", 30), ("მ", 40), ("ნ", 50), ("ჲ", 60),
    ("ო", 70), ("პ", 80), ("ჟ", 90),
    ("რ", 100), ("ს", 200), ("ტ", 300),
]
_VAL = dict(_NUM_LETTERS)


def georgian_numeral(n):
    """Render n in the print's alphabetic numerals (hundreds, tens, units)."""
    out = ""
    for letter, val in sorted(_NUM_LETTERS, key=lambda x: -x[1]):
        while n >= val and val >= 100:
            out += letter
            n -= val
        if val < 100:
            break
    for lo, hi in ((10, 90), (1, 9)):
        for letter, val in sorted(_NUM_LETTERS, key=lambda x: -x[1]):
            if lo <= val <= hi and n >= val:
                out += letter
                n -= val
                break
    return out


# A chapter heading is «თავი» + the chapter number (an alphabetic numeral,
# sometimes Arabic digits, sometimes the word «პირველი») + optional punctuation.
# ⚠ ANCHORED AT THE START on purpose. «თავი» is also the ordinary word "head",
# and it occurs inside real scripture — Sirach 11:1 reads «აღამაღლნაჲ თავი
# მისი», "shall lift up his head". An unanchored strip would eat scripture.
# This is the «Տունք»/houses trap from the Zohrab colophon work, in Georgian.
HEADING_RE = re.compile(
    r"^\s*თავი\s*[,.]?\s*(?:პირველი|[ՙ̂̃Ⴀ-ჿ0-9]{1,6})\s*[.,:]*\s*")


def strip_heading(pre):
    """Remove a leading «თავი , N.» chapter heading, twice at most.

    Twice, because a few chapter-1 preambles carry the BOOK heading and then
    the chapter heading («სახარება ლუკასი თავი ՙა̂»); the book heading is
    handled by the PREAMBLE table, the trailing chapter heading here.
    """
    out = HEADING_RE.sub("", pre, count=1)
    tail = re.sub(
        r"\s*თავი\s*[,.]?\s*(?:პირველი|[ՙ̂̃Ⴀ-ჿ0-9]{1,6})"
        r"\s*[.,:]*\s*$", "", out)
    return tail if tail.strip() else out


def strip_marks(s):
    """Drop the numeral-decoration marks so a numeral compares by letters only."""
    return "".join(c for c in s if c not in "\u0559\u0302\u0303")


# ---------------------------------------------------------------- labels
# Every non-plain label in the corpus, resolved. Keys: (part, chapter, label).
# value = ("num", n)                  -> plain verse n
#         ("num_word", n, word)       -> verse n; `word` was fused into the
#                                        label by TITUS and is MISSING from the
#                                        head of the verse text — prepend it
#         ("dual", n, alt)            -> verse n, print also carries `alt`
#         ("append_prev",)            -> unnumbered fragment; append to previous
#         ("margin", n)               -> margin-column reading for verse n
#         ("scholion", n)             -> exegetical gloss on verse n
#         ("drop",)                   -> not scripture, not apparatus we keep
LABELS = {
    (8, "10", "21:"): ("num", 21),
    (8, "11", "32:_"): ("num", 32),
    (8, "16", "ფ8"): ("num", 8),                       # stray ფ glyph
    (9, "14", "23sdevdes"): ("num_word", 23, "სდევდეს"),  # Latin translit. leak
    (10, "23", "19და"): ("num_word", 19, "და"),
    (13, "19", "22და"): ("num_word", 22, "და"),
    (18, "12", "(33)"): ("num", 33),
    # ⚠ The two dual-numbered sites take OPPOSITE conventions, and which number
    # is native is DERIVED, not preferred: in 2 Chronicles 17 the chapter
    # already carries a plain «15», so reading the first number as native
    # collides — the parenthesized value is the print's own, giving a clean
    # 1..20. In Nehemiah 11 the opposite holds (plain 19, 20, 21, 22 coexist
    # with «17(19)» and «18(22)»), so there the FIRST number is native. Each
    # site is settled by the reading that leaves no collision.
    (21, "17", "15(16)"): ("dual", 16, 15),
    (21, "17", "16(17)"): ("dual", 17, 16),
    (21, "17", "17(18)"): ("dual", 18, 17),
    (21, "17", "18(19)"): ("dual", 19, 18),
    (21, "17", "19(20)"): ("dual", 20, 19),
    (24, "11", "16(17)"): ("dual", 16, 17),
    (24, "11", "17(19)"): ("dual", 17, 19),
    (24, "11", "18(22)"): ("dual", 18, 22),
    (24, "11", "24(30)"): ("dual", 24, 30),
    (24, "11", "26(36)"): ("dual", 26, 36),
    (24, "12", "5;"): ("num", 5),
    (24, "12", "34(36)"): ("dual", 34, 36),
    (30, "19", "25a"): ("margin", 25),
    (30, "19", "26a"): ("margin", 26),
    (30, "19", "27a"): ("margin", 27),
    (30, "39", "x13x"): ("scholion", 13),
    (34, "10", "?"): ("append_prev",),
    (36, "7", "30რამეთუ"): ("num_word", 30, "რამეთუ"),
    (36, "9", "7//"): ("num", 7),
    (36, "11", "6ამით"): ("num_word", 6, "ამით"),
    (39, "20", "18."): ("num", 18),
    (39, "48", "13_(14)"): ("dual", 13, 14),
    (61, "5", "24:"): ("num", 24),
    (64, "11", "24ჰრქუა"): ("num_word", 24, "ჰრქუა"),
    (67, "15", "40და"): ("num_word", 40, "და"),
    (69, "5", "ՙი̂ე"): ("num", 15),                     # numeral label = 15
    (85, "1", "10ამისათჳს"): ("num_word", 10, "ამისათჳს"),
}
# 3 Kingdoms 1: four units TITUS labelled «1,». Their true numbers survive as
# leading DIGITS INSIDE the verse text; the chapter's gap [26,27,28,37] and the
# four labels cancel exactly (census). The digits are stripped from the text.
REG3_1 = {"1,": 26, "1,#dup2": 27, "1,#dup3": 28, "1,#dup4": 37}

# The Psalter frontispiece (Ps 131:11 quoted on print page 448) sits in a
# synthetic no-chapter bucket. Not a verse of any psalm.
PSALTER_EPIGRAPH = (31, "", "(131_11)")

# Psalm 118:74 carries an embedded «|76», but unlike the other pipe sites its
# target is already occupied and the marker falls MID-PHRASE («განკითხვანი |76
# შენნი» — "thy judgments" split between the noun and its possessive). The
# unit's text is complete either way; the psalm's 175-against-176 shape is a
# versemap matter, not a split. Left intact deliberately.
# Psalm 34:8 is the same judgement. Its «|910» does not name one verse: the
# unit's tail («ხოლო სული ჩემი იხარებდეს უფლისაჲ მიმართ … და იშუჱბდეს
# მაცხოვარებითა მისითა») is LXX 34:9, while the separately-labelled «9» that
# follows is LXX 34:10 — so the marker sits astride a one-off label shift and
# no single split point follows from it. Reading «910» as a verse number
# produced a 910-slot psalm, which is how this was caught. Text is complete
# either way; the shape is the versemap's problem.
NO_SPLIT = {(18, 118, 74), (18, 34, 8)}

# Luke 4 is a print-typo cascade with NO duplicate label to trip the ordinary
# detector: the print's numbers run 1-40 and then jump to 51-54, and the census
# verified verse by verse that no text is missing (44 units against the KJV's
# 44). Renumbered by position.
#
# ⚠ A TEMPTING HEURISTIC WAS REJECTED HERE. "Gapped chapter whose unit count
# equals the KJV's" looks like it should identify this class automatically, and
# it flags ten more chapters — but they are NOT the same thing. Genesis 32 has
# 32 units, max label 33, KJV 32: that is the ordinary Hebrew/LXX numbering
# running one ahead of the KJV, NOT a misprint, and renumbering it by position
# would shift every verse in the chapter onto its neighbour's number. That is
# the de_luther lesson — repairing by coordinate overwrites scripture — so the
# only sites repaired positionally are the ones a reader verified.
TYPO_CASCADE = {(63, "4")}

# ------------------------------------------------------------------- seams
# Chapters where the print repeats a verse number, resolved by READING the
# text against a reference grid — never by arithmetic, which cannot settle
# them (for most of these sites both "the dup is the next verse" and "the dup
# is the second half of this verse" produce a self-consistent chapter; the
# difference is only whether a passage is one verse or two).
#
# The table gives an explicit verse number PER UNIT, keyed by the print's own
# label. Units are consumed in document order and two units assigned the SAME
# number are concatenated in that order — so a rejoin, a renumber and a shift
# are all expressed the same auditable way. Only labels whose number differs
# from their own stem need listing; anything unlisted keeps its printed number.
#
# A value of "RUBRIC" moves the unit out of scripture into rubrics_bak.json.
# Evidence for each site is in research/BAKAR_BUILD_LOG.md.
SEAM = {
    # Joshua 17 — TWO independent defects that together land the chapter on
    # exactly 18 verses, the KJV's count. «2#dup2» is the opening clause of
    # verse 3 (Zelophehad had no sons) and «3» its closing clause (the
    # daughters' names), one KJV sentence the print broke in two; and the
    # stray late «1» is verse 11, whose number the print never printed at all
    # — its content is the Bethshean/Dor list, and the label stream's only gap
    # is [11].
    (13, "17"): {"2#dup2": 3, "3": 3, "1#dup2": 11},
    # 1 Samuel 23 — the chapter runs 1-28 with no gap, so the trailing stray
    # «1» is necessarily the last verse; its text is «დავით … ენღადისასა»,
    # David dwelling in the strongholds of Engedi = KJV 23:29.
    (16, "23"): {"1#dup2": 29},
    # 3 Kingdoms 4 — [25] closes on the proverb/song count and the dup opens a
    # new subject (trees, beasts, birds, fishes), so it is the next verse, not
    # a continuation; the three units run one-to-one onto KJV 4:32, 33, 34.
    (18, "4"): {"25#dup2": 26, "26": 27},
    # 3 Kingdoms 10 — the census independently records this: a «10» printed at
    # the POSITION OF VERSE 2, which is why the chapter's only gap is [2]. The
    # unit's content is the queen of Sheba arriving at Jerusalem with camels
    # and spices (KJV 10:2); the later «10» is the true verse 10 (the 120
    # talents of gold). Relabelling the first closes the gap and the dup at
    # once. ⚠ This chapter's OTHER repeat, «23#dup2», is NOT resolved — see
    # the unresolved list in the build log.
    (18, "10"): {"10": 2, "10#dup2": 10},
    # 3 Kingdoms 21 — a textbook mid-sentence split: [29] is the bare speech
    # tag «და ჰრქუა უფალმან» ("And the LORD said:"), twenty characters with no
    # reported speech at all, and the dup supplies the oracle KJV 21:29
    # contains. Same number = concatenated.
    (18, "21"): {"29#dup2": 29},
    # Proverbs 17 — two different answers in one chapter. «6#dup2» completes a
    # noun phrase [6] leaves hanging («crown of old men» → «…of grandchildren»)
    # and then carries the LXX-only addition at 17:6a, so it rejoins verse 6.
    # «12#dup2» is an unrelated complete sentence matching KJV 17:13, and the
    # label 13 is missing from the stream — so it takes it.
    (33, "17"): {"6#dup2": 6, "12#dup2": 13},
    # Luke 1 — the base «50» is not scripture: «გარდახედ ღმრთის მშობლისასა»,
    # "turn to [the reading of] the Mother of God", is a lectionary rubric the
    # print left unbracketed, phrased almost exactly like the bracketed ხ55ხ
    # rubric a few lines later. Moving it to the rubric file leaves 80 verses
    # — the KJV's count — with the dup as the real verse 50 (God's mercy on
    # them that fear him).
    (63, "1"): {"50": "RUBRIC", "50#dup2": 50},
    # Genesis 41 and Deuteronomy 32 — REJOIN, and note this contradicts the
    # first reading of both. The reader proposed shifting the dup to the next
    # number, but its OWN verse-by-verse alignment shows the unit AFTER the
    # duplicate already matches the KJV ([50] = KJV 41:50; [24] = KJV 32:24).
    # Shifting would push that unit off its match and leave a permanent offset
    # for the rest of the chapter, whereas rejoining absorbs the +1 the
    # chapter had been carrying since an earlier split — and lands Genesis 41
    # on exactly the KJV's 57. The alignment table is evidence; the verdict
    # label was a summary of it, so the table wins.
    (8, "41"): {"49#dup2": 49},
    (12, "32"): {"23#dup2": 23},
    # Exodus 8 — the chapter runs a consistent +1 against the KJV from an
    # earlier split at v16 and nothing follows the dup to contradict it, so
    # the extra final verse stands: 33 native against the KJV's 32.
    (9, "8"): {"32#dup2": 33},
    # Exodus 31 — three units carrying three sequential, non-overlapping
    # contents ([16] = KJV 16 without its tail, the dup = that tail plus
    # KJV 17, the second dup = KJV 18) running to the chapter's natural end.
    # Lands on exactly 18 verses, the KJV's count.
    (9, "31"): {"15#dup2": 17, "16#dup2": 18},
    # Daniel 6 — the tail runs consistently one behind from the dup onward
    # ([21] = KJV 22 … [27] = KJV 28), so the whole tail shifts up one and the
    # chapter closes on 28, the KJV's count. «O king, live for ever» is a
    # complete verse, not a continuation of the king's cry.
    (45, "6"): {"20#dup2": 21, "21": 22, "22": 23, "23": 24, "24": 25,
                "25": 26, "26": 27, "27": 28},
    # ★ Sirach 37 and 41 — the best-corroborated sites in the whole pass, and
    # a different defect from all the others: each chapter carries a stray
    # «35» in the position where 3 belongs, and each chapter's label stream is
    # missing exactly [3]. Reading it as a two-digit slip for «3» makes BOTH
    # chapters perfectly contiguous (37 → 1..34, 41 → 1..29) and closes six
    # census gaps at once. The content confirms it: Sirach 37's unit is the
    # whole of «O wicked imagination, whence camest thou…» = KJV 37:3.
    (37, "37"): {"35": 3},
    (37, "41"): {"35": 3},
}

# ------------------------------------------------------- chapter preambles
# Every chapter whose preamble carries something beyond the print's «თავი , N.»
# heading, resolved individually. Actions:
#   "drop"    — a BOOK heading repeated over chapter 1; the book name already
#               carries it, so prepending would print the title twice
#   "title"   — a genuine superscription; prepended to verse 1, the psalm-title
#               convention (a title sharing a verse with content is never
#               dropped — the ru/cu lesson)
#   "verse1"  — ★ not a title at all but the chapter's MISSING VERSE 1: in both
#               cases the census independently records a gap at [1], so the
#               preamble and the gap cancel exactly. Real content recovery.
#   "acrostic"— the Hebrew acrostic letter opening Lamentations 1-4; apparatus
#               of the same class as the la_vulgata <Aleph> markers
PREAMBLE = {
    (9, "30"): "drop",       # bare numeral «ლ.» = 30
    (16, "1"): "drop", (20, "1"): "drop", (21, "1"): "drop",
    (23, "1"): "drop", (38, "1"): "drop", (39, "1"): "drop",
    (42, "1"): "drop", (54, "1"): "drop",
    (22, "1"): "title",      # Or.Man. — the prayer itself (unversified)
    (29, "1"): "title",      # Esther — the whole of LXX Addition A (spec §6)
    (37, "11"): "verse1",    # ★ Sirach 11:1   (census gap [1])
    (37, "51"): "title",     # «ლოცვა ისოსი ძისა ზირაქისა» — Prayer of Sirach
    (38, "17"): "title",     # «სიტყვა დამასკისა» — the burden of Damascus
    (39, "25"): "verse1",    # ★ Jeremiah 25:1 (census gap [1])
    (40, "1"): "acrostic", (40, "2"): "acrostic",
    (40, "3"): "acrostic", (40, "4"): "acrostic",
    (43, "6"): "title",      # the Epistle's own superscription
}
for _p in list(range(61, 67)) + list(range(67, 87)):
    PREAMBLE.setdefault((_p, "1"), "drop")   # NT book headings over chapter 1

# ---------------------------------------------------------------- apparatus
# `*` = the print's verse-end mark, `//` = its line/column break. Added on the
# second pass, found by reading the built asset rather than the census: TITUS's
# own editorial sigla, which the census's parenthesis total (373) had absorbed
# into "parenthesized passages" and so did not surface as apparatus —
#   (#)  345×  lection-start mark (the print's «დასაწყისი» count: Matthew's
#              index line advertises 116 of them)
#   (!)    7×  sic
#   (?)    4×  uncertain reading
#   (!?)   2×  both
# All four are the editor's marks, not the 1743 print's words. Longer
# parenthesized runs — «(იო)», «(27)», «(1, 11)» — are genuine references and
# parenthesized passages, and are KEPT (spec §2.3).
APPARATUS = ["*", "//", "(#)", "(!?)", "(!)", "(?)"]
APPARATUS_EXPECTED = {"*": 33888, "//": 2237, "(#)": 345, "(!)": 7,
                      "(?)": 4, "(!?)": 2, "{}": 1}


def clean(txt, stats):
    for sym in APPARATUS:
        stats[sym] += txt.count(sym)
        txt = txt.replace(sym, " ")
    # ⚠ TITUS brace-marks a restored letter run — «უფროს {ვე}ფხისა», "than the
    # leopard" (Habakkuk 1:8), the only site in the corpus. The braces must go
    # but the LETTERS MUST STAY: this is the Zohrab's restored-letter
    # parentheses in another costume. It matters doubly here because the app's
    # verse parser reads `{...}` as markup, so a surviving brace would be
    # swallowed along with the text inside it.
    stats["{}"] += txt.count("{")
    txt = txt.replace("{", "").replace("}", "")
    stats[":_"] += txt.count(":_")
    txt = txt.replace(":_", ":")
    stats["_"] += txt.count("_")
    txt = txt.replace("_", " ")
    return re.sub(r"\s+", " ", txt).strip()


# ---------------------------------------------------------------- helpers
RUBRIC_RE = re.compile(r"^ხ(\d+)ხ(#dup\d+)?$")
CONT_RE = re.compile(r"^(\d+)[ბb]$")
DUP_RE = re.compile(r"^(.+)#dup(\d+)$")
PIPE_RE = re.compile(r"\|\s*(\d+)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RAW.read_text(encoding="utf-8"))
    books = raw["books"]
    kjv = json.loads((ASSETS / "en_kjv.json").read_text(encoding="utf-8"))
    slots = [{"name": kjv[i]["name"], "chapters": []} for i in range(83)]
    native = {}                       # slot -> {chapter: {verse: text}}
    rubrics = []                      # rubrics_bak.json rows
    notes = {}                        # (slot, ch, v) -> margin note text
    stats = Counter()
    todo = Counter()
    report = OrderedDict()

    def flag(key, item):
        report.setdefault(key, []).append(item)
        todo[key] += 1

    # ---- index lines, for the book names -------------------------------
    index = raw["extras"]["part003"]["chapters"]
    idx_line = {}
    for sec in ("OT", "NT"):
        for vk, t in index[sec]["verses"].items():
            idx_line[int(vk)] = t

    # ---- main pass ------------------------------------------------------
    for pk in sorted(books, key=lambda x: int(x[4:])):
        n = int(pk[4:])
        if n in SKIP:
            stats["parts_skipped"] += 1
            continue
        if n not in SLOT:
            continue
        p = books[pk]
        slot = SLOT[n]
        dest = native.setdefault(slot, {})

        for ck, ch in p["chapters"].items():
            if ck.startswith("Prol."):
                # Patristic/Euthalian prologues — 26 across the NT. NOT
                # scripture; excluded from the verse flow (spec §10). They
                # could later ship the way the rubrics do — owner decision.
                todo["nt_prologues_excluded"] += 1
                continue

            # -- chapter preamble: apparatus, or a psalm title ------------
            pre = (ch.get("preamble") or "").strip()
            title = None
            recovered = None
            if ck.isdigit() and pre:
                if n == 31:
                    title, kath = psalm_title(pre, int(ck), stats, flag)
                    if kath:
                        rubrics.append({"book": slot, "chapter": int(ck) - 1,
                                        "verse": 0, "kind": "kathisma",
                                        "text": kath})
                else:
                    residue = clean(strip_heading(pre), stats)
                    if not re.search(r"[^\W\d_]", residue, re.UNICODE):
                        residue = ""      # punctuation-only leftovers
                    if not residue:
                        stats["chapter_headings_dropped"] += 1
                    else:
                        action = PREAMBLE.get((n, ck))
                        if action is None:
                            flag("unresolved_chapter_preamble",
                                 (p["book_label"], ck, residue[:60]))
                        elif action == "drop":
                            stats["book_headings_dropped"] += 1
                        elif action == "acrostic":
                            stats["acrostic_letters_dropped"] += 1
                        elif action == "verse1":
                            recovered = residue
                            stats["verse1_recovered_from_preamble"] += 1
                        elif action == "title":
                            title = residue
                            stats["titles_from_preamble"] += 1

            if not ck.isdigit():
                if ck == "":
                    # the Psalter frontispiece bucket
                    stats["psalter_epigraph_dropped"] += 1
                else:
                    flag("non_numeric_chapter", (p["book_label"], ck))
                continue

            cnum = int(ck)
            verses = OrderedDict()     # native verse number -> text
            order = []                 # document order of resolved numbers
            prev = None
            for vk, rawtxt in ch["verses"].items():
                stats["units_seen"] += 1
                t = clean(rawtxt, stats).replace("|d", "").strip()

                m = RUBRIC_RE.match(vk)
                if m:
                    rubrics.append({"book": slot, "chapter": cnum - 1,
                                    "verse": int(m.group(1)), "kind": "lection",
                                    "text": t})
                    stats["rubrics"] += 1
                    continue
                if vk == "expl.":
                    rubrics.append({"book": slot, "chapter": cnum - 1,
                                    "verse": -1, "kind": "colophon", "text": t})
                    stats["colophons"] += 1
                    continue
                m = CONT_RE.match(vk)
                if m:
                    # a verse resumed after an interrupting rubric
                    base = int(m.group(1))
                    if base in verses:
                        verses[base] = (verses[base] + " " + t).strip()
                        stats["continuations_rejoined"] += 1
                    else:
                        flag("continuation_without_base", (p["book_label"], ck, vk))
                    continue

                if (n, ck, vk) in LABELS:
                    kind = LABELS[(n, ck, vk)]
                    if kind[0] == "num":
                        num = kind[1]
                    elif kind[0] == "num_word":
                        num, word = kind[1], kind[2]
                        t = (word + " " + t).strip()
                        stats["fused_words_restored"] += 1
                    elif kind[0] == "dual":
                        num = kind[1]
                        stats["dual_numbered"] += 1
                    elif kind[0] == "append_prev":
                        if prev is None:
                            flag("append_prev_without_base", (p["book_label"], ck, vk))
                            continue
                        verses[prev] = (verses[prev] + " " + t).strip()
                        stats["fragments_appended"] += 1
                        continue
                    elif kind[0] == "margin":
                        notes[(slot, cnum, kind[1])] = t.strip("[] ")
                        stats["margin_notes"] += 1
                        continue
                    elif kind[0] == "scholion":
                        rubrics.append({"book": slot, "chapter": cnum - 1,
                                        "verse": kind[1], "kind": "scholion",
                                        "text": t})
                        stats["scholia"] += 1
                        continue
                    else:
                        continue
                elif n == 18 and ck == "1" and vk in REG3_1:
                    num = REG3_1[vk]
                    t = re.sub(r"^%d\s+" % num, "", t)
                    stats["reg3_relabelled"] += 1
                else:
                    seam = SEAM.get((n, ck), {})
                    if vk in seam:
                        if seam[vk] == "RUBRIC":
                            rubrics.append({"book": slot, "chapter": cnum - 1,
                                            "verse": 0, "kind": "lection",
                                            "text": t})
                            stats["rubrics"] += 1
                            stats["seam_units_moved_to_rubrics"] += 1
                            continue
                        num = seam[vk]
                        stats["seam_units_renumbered"] += 1
                        order.append((num, t))
                        stats["to_verse_stream"] += 1
                        if num in verses:
                            verses[num] = (verses[num] + " " + t).strip()
                            stats["seam_units_rejoined"] += 1
                        else:
                            verses[num] = t
                        prev = num
                        continue
                    m = DUP_RE.match(vk)
                    stem = m.group(1) if m else vk
                    if not stem.isdigit():
                        flag("unresolved_label", (p["book_label"], ck, vk))
                        stats["unresolved_labels"] += 1
                        continue
                    num = int(stem)
                    if m:
                        # a repeated print number: recorded in document order,
                        # resolved after the chapter is read (see below)
                        num = -num          # provisional marker
                stats["to_verse_stream"] += 1
                order.append((num, t))
                prev = abs(num) if num else prev
                if num >= 0:
                    if num in verses:
                        flag("silent_collision", (p["book_label"], ck, num))
                    verses[num] = t
                    prev = num

            resolve_chapter(p, n, ck, order, verses, flag, stats)
            if recovered:
                if 1 in verses:
                    flag("verse1_recovery_collided", (p["book_label"], ck))
                else:
                    verses[1] = recovered
            if title:
                if 1 in verses:
                    verses[1] = (title + " " + verses[1]).strip()
                    stats["titles_prepended"] += 1
                else:
                    # no verse 1 to carry it (Or.Man., Ps 151) — unversified()
                    # ships the whole preamble as the single verse instead
                    stats["titles_deferred_to_unversified"] += 1
            if verses:
                dest[cnum] = verses

        if p.get("book_preamble"):
            stats["book_preambles_seen"] += 1

    # ---- pipes -----------------------------------------------------------
    split_pipes(native, stats, flag)

    # ---- the two unversified texts --------------------------------------
    unversified(books, native, stats)

    # ---- Esther Addition E ----------------------------------------------
    # (handled inside resolve_chapter; see the Esther note there)

    # ---- margin notes onto their verses ---------------------------------
    for (slot, cnum, vnum), text in sorted(notes.items()):
        vs = native.get(slot, {}).get(cnum)
        if not vs or vnum not in vs:
            flag("margin_note_without_verse", (slot, cnum, vnum))
            continue
        # the app's on-demand translator's-note mechanism: {label: text}
        vs[vnum] = vs[vnum] + " {%s: %s}" % (MARGIN_LABEL, text)

    # ---- names -----------------------------------------------------------
    name_report = apply_names(slots, idx_line, books, flag)

    # ---- positional lists ------------------------------------------------
    total = 0
    empties = 0
    for slot, chs in native.items():
        out = []
        for c in range(1, max(chs) + 1):
            vs = chs.get(c, {})
            if not vs:
                out.append([])
                continue
            lst = [""] * max(vs)
            for num, t in vs.items():
                lst[num - 1] = t
            total += sum(1 for x in lst if x)
            empties += sum(1 for x in lst if not x)
            out.append(lst)
        slots[slot]["chapters"] = out

    # ---- accounting ------------------------------------------------------
    # Every verse-level unit the dump carries must leave through exactly ONE
    # branch above. This is the guard that a unit cannot be silently skipped —
    # the class of bug that let a bad glob "succeed" on 5% of the Zohrab.
    classified = (stats["to_verse_stream"] + stats["rubrics"]
                  + stats["colophons"] + stats["continuations_rejoined"]
                  + stats["continuation_without_base"]
                  + stats["margin_notes"] + stats["scholia"]
                  + stats["fragments_appended"] + stats["unresolved_labels"])
    assert classified == stats["units_seen"], (
        "unit accounting: %d classified vs %d seen (%d unaccounted)" % (
            classified, stats["units_seen"], stats["units_seen"] - classified))
    print("unit accounting      : %d units in, all classified ✓" % stats["units_seen"])
    for sym, want in sorted(APPARATUS_EXPECTED.items()):
        assert stats[sym] == want, (
            "apparatus %r: stripped %d, census says %d" % (sym, stats[sym], want))
    print("apparatus counts     : all %d match the census ✓" % len(APPARATUS_EXPECTED))

    # ---- report ----------------------------------------------------------
    print("apparatus stripped   : %s" % {k: stats[k] for k in ("*", "//", ":_", "_")})
    print("verses placed        : %d   (empty grid slots: %d)" % (total, empties))
    print("books with text      : %d / 83" % sum(1 for s in slots if any(s["chapters"])))
    print("rubrics extracted    : lection %d  colophon %d  kathisma %d  scholion %d" % (
        stats["rubrics"], stats["colophons"],
        sum(1 for r in rubrics if r["kind"] == "kathisma"), stats["scholia"]))
    print("repairs              : continuations %d  fused words %d  fragments %d"
          "  dual-numbered %d  3Kgdms relabels %d  margin notes %d  pipes %d" % (
              stats["continuations_rejoined"], stats["fused_words_restored"],
              stats["fragments_appended"], stats["dual_numbered"],
              stats["reg3_relabelled"], stats["margin_notes"], stats["pipe_splits"]))
    print("psalm titles         : %d prepended, %d numerals stripped, %d kathisma lifted" % (
        stats["psalm_titles"], stats["psalm_numerals_stripped"],
        sum(1 for r in rubrics if r["kind"] == "kathisma")))
    print("positional repairs   : %d chapters" % stats["positional_chapters"])
    print()
    print(name_report)
    print()
    print("CURATION REMAINING (reported, not done):")
    for k, v in todo.most_common():
        print("   %-30s %d" % (k, v))
        for item in report.get(k, [])[:12]:
            print("        %s" % (item,))

    print()
    print("CHAPTER-COUNT vs KJV (canonical books only):")
    bad = 0
    for i in range(66):
        if not any(slots[i]["chapters"]):
            continue
        a, b = len(slots[i]["chapters"]), len(kjv[i]["chapters"])
        if a != b:
            bad += 1
            print("   %-18s bakar %3d  kjv %3d" % (kjv[i]["name"], a, b))
    print("   books off-grid: %d  (Esther 9 and Daniel 14 are spec-intended)" % bad)

    if args.dry_run:
        print("\n[dry-run] nothing written")
        return
    OUT.write_text(json.dumps(slots, ensure_ascii=False), encoding="utf-8")
    RUBRICS_OUT.write_text(json.dumps(rubrics, ensure_ascii=False), encoding="utf-8")
    print("\nwrote %s (%.1f MB)" % (OUT, OUT.stat().st_size / 1e6))
    print("wrote %s (%d rows)" % (RUBRICS_OUT, len(rubrics)))


MARGIN_LABEL = "მიწერილი"      # "margin", the print's own side-column reading


def psalm_title(pre, num, stats, flag):
    """Split a psalm preamble into (title, kathisma-heading-or-None).

    The preamble is the print's psalm TITLE with the psalm's own number
    appended as an alphabetic numeral, and — in the 20 psalms that open a
    kathisma — a «კანონი <numeral>» heading fused in. Both are apparatus.
    The numeral is not guessed: it is COMPUTED from the psalm number and
    only stripped where the computed form is actually present.
    """
    text = pre
    kath = None
    m = re.search(r"კანონი\s*[,.]?\s*([^\s,.]+)\s*[.,:]?", text)
    if m:
        kath = m.group(0).strip()
        text = (text[:m.start()] + " " + text[m.end():]).strip()
    want = georgian_numeral(num)
    # the numeral may be written in letters or (rarely) Arabic digits
    stripped = False
    for cand in (str(num), want):
        for mm in list(re.finditer(r"[^\s,.:]+", text))[::-1]:
            if strip_marks(mm.group(0)).strip(".,:") == cand:
                text = (text[:mm.start()] + text[mm.end():])
                stripped = True
                break
        if stripped:
            break
    if stripped:
        stats["psalm_numerals_stripped"] += 1
    else:
        flag("psalm_numeral_not_found", (num, pre[:60]))
    text = re.sub(r"\s+", " ", text).strip(" ,.:")
    stats["psalm_titles"] += 1
    return text, kath


def resolve_chapter(p, part, ck, order, verses, flag, stats):
    """Resolve repeated print numbers within one chapter.

    `order` holds (num, text) in DOCUMENT order, with repeats marked negative.
    Two classes, distinguished by evidence rather than by threshold:

      * POSITIONAL — the chapter's unit count equals its maximum label, so the
        label stream is a slip over a complete, ordered set of verses. The
        spec (§5) sanctions repairing these by position; the print's own
        content order is the witness. Renumber 1..N.
      * OTHERWISE — reported, never guessed. These need a seam read against a
        reference text, which is a curation job, not a mechanical one.
    """
    if (part, ck) in TYPO_CASCADE:
        verses.clear()
        for i, (_, t) in enumerate(order, 1):
            verses[i] = t
        stats["positional_chapters"] += 1
        return
    if all(num >= 0 for num, _ in order):
        return
    nums = [abs(n) for n, _ in order]
    mx = max(nums) if nums else 0
    label = "%s %s" % (p["book_label"], ck)

    # Esther 8's second «12» is LXX Addition E — the royal letter, which the
    # print numbers as a second verse 12. Concatenate in label order (spec §6).
    if part == 29 and ck == "8":
        for num, t in order:
            if num < 0 and abs(num) == 12:
                verses[12] = (verses[12] + " " + t).strip()
                stats["esther_addition_e_merged"] += 1
        return

    if len(order) == mx:
        verses.clear()
        for i, (_, t) in enumerate(order, 1):
            verses[i] = t
        stats["positional_chapters"] += 1
        return

    flag("repeated_labels_need_seam_read",
         (label, "units=%d max=%d" % (len(order), mx)))
    # keep the first occurrence; the repeat is preserved by appending so no
    # scripture is lost while the site awaits curation
    for num, t in order:
        if num < 0:
            k = abs(num)
            verses[k] = (verses.get(k, "") + " " + t).strip()


def split_pipes(native, stats, flag):
    """Split the 16 pipe-marked merged units at the print's own numbers.

    Where a pipe carries a number the print HAS that verse — TITUS simply did
    not split the unit (census §punctuation). A bare pipe carries no number and
    is reported instead.
    """
    for slot, chs in native.items():
        for cnum, vs in chs.items():
            for vnum in sorted(vs):
                t = vs[vnum]
                if "|" not in t:
                    continue
                if (slot, cnum, vnum) in NO_SPLIT:
                    vs[vnum] = re.sub(r"\s*\|\s*\d*\s*", " ", t).strip()
                    stats["pipes_left_unsplit"] += 1
                    continue
                parts = PIPE_RE.split(t)
                if len(parts) == 1:
                    # A pipe carrying no number marks nothing splittable — the
                    # print did not number a second verse there. Removing the
                    # marker is the whole repair. (One of these is Matthew
                    # 11:14's «|d», the keystroke artifact the census names.)
                    vs[vnum] = re.sub(r"\s*\|\s*", " ", t).strip()
                    stats["bare_pipes_removed"] += 1
                    continue
                head, rest = parts[0], parts[1:]
                vs[vnum] = re.sub(r"\s+", " ", head).strip()
                ok = True
                for i in range(0, len(rest), 2):
                    tgt, body = int(rest[i]), rest[i + 1]
                    if tgt in vs and vs[tgt]:
                        flag("pipe_target_occupied", (slot, cnum, vnum, tgt))
                        ok = False
                        break
                    vs[tgt] = re.sub(r"\s+", " ", body).strip()
                if ok:
                    stats["pipe_splits"] += 1


def unversified(books, native, stats):
    """Or.Man. and Ps 151 are printed as continuous prose with no verse numbers.

    Both ship as a single verse, exactly as printed (spec §4). Their text lives
    in the chapter-1 preamble, which no verse unit carries.
    """
    for part, slot, cnum in ((22, 74, 1), (31, 18, 151)):
        ch = books["part%03d" % part]["chapters"].get(str(cnum))
        if not ch:
            continue
        pre = (ch.get("preamble") or "").strip()
        if not pre:
            continue
        s = Counter()
        text = clean(re.sub(r"თავი\s*[,.]?\s*\S+?\s*[.,:]", " ", pre, count=1), s)
        native.setdefault(slot, {}).setdefault(cnum, {})
        if not native[slot][cnum]:
            native[slot][cnum] = {1: text}
            stats["unversified_texts"] += 1


def apply_names(slots, idx_line, books, flag):
    """Georgian book names from the print's own index, substring-asserted."""
    lines = []
    for slot, (line, name) in sorted(NAME_SRC.items()):
        src = idx_line.get(line, "")
        assert name in src, "name %r not a substring of index line %d: %r" % (
            name, line, src)
        slots[slot]["name"] = name
    for slot, (part, name) in NAME_FROM_PREAMBLE.items():
        src = (books["part%03d" % part].get("book_preamble") or "")
        assert name in src, "name %r not in preamble of part%03d: %r" % (
            name, part, src)
        slots[slot]["name"] = name
    for slot, (part, ck, name) in NAME_FROM_CHAPTER.items():
        src = (books["part%03d" % part]["chapters"][ck].get("preamble") or "")
        assert name in src, "name %r not in preamble of part%03d ch%s: %r" % (
            name, part, ck, src)
        slots[slot]["name"] = name
    named = sum(1 for s in slots if not re.match(r"^[A-Za-z0-9 ]+$", s["name"]))
    lines.append("book names           : %d Georgian (index-attested), "
                 "%d still English" % (named, 83 - named))
    return "\n".join(lines)


if __name__ == "__main__":
    main()
