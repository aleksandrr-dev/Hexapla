# -*- coding: utf-8 -*-
"""Owner ear test on tyn, 2026-09-30 (`_work/ear_tyn_stillfail_2026-09-30/`).

Reproduces the defects he heard, as normalizer output (SYNTHESIS INPUT):
  * Rev 7:6 «xii.M» was expanded to the DIGITS «12000.» and the voice said
    «twelve hundred twelven»; Mark 8:20 «.iiii. M.» -> «4000.» likewise.
    Chatterbox reads digits unreliably, so tyn numbers are spoken as WORDS.
  * Num 2:31 «lvij. thousande» - a numeral with no leading stop was never
    expanded; the voice spelled it «ell vay».
  * heddes (Acts 3:17), standertes (Num 2:17, 2:31), meante (Luke 15:26):
    silent final -e/-es voiced as a syllable.

rc 0 = every case passes; rc 1 = at least one fails (printed).
"""
import re
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from archaic_english import normalize  # noqa: E402

CASES = [
    # (tyn text, substrings that MUST appear, regexes that must NOT match)
    ("Of the trybe of Asser were sealed xii.M. Of the trybe of Neptalym were sealed xii.M.",
     ["sealed twelve thousand. Of", "Neptalym were sealed twelve thousand."], [r"\d"]),
    ("When I brake .vii. amonge .iiii. M. How many basketes",
     ["brake seven among four thousand. How"], [r"\d"]),
    ("was an hundred thousande lvij. thousande and .vi. hundred. And they shalbe the last",
     ["hundred thousand fifty-seven thousand and six hundred. And"], [r"\d", r"\blvij\b"]),
    ("then thou shalt adde .iij. cities moo vnto those .iij.",
     ["add three cities more unto those three"], [r"\d"]),
    ("as dyd also youre heddes.", ["your heads."], [r"heddes"]),
    ("with their standertes.", ["their standards."], [r"standert"]),
    ("and axed what thoose thinges meante.", ["things meant."], [r"meante"]),
    # the same class, one stop only (146 sites over the asset)
    ("And Abraham set vij. lambes by them selves.", ["set seven lambs"], [r"\d", r"vij"]),
    ("foure kynges agenste v.", ["against five."], [r"\d"]),
    ("two oxen .v rammes and a golden spone of x. sicles", ["oxen five rams", "of ten "], [r"\d"]),
    ("lyved an hundred and lxxxvij. yere", ["hundred and eighty-seven year"], [r"\d"]),
    # no stops at all (19 sites) and the lone «C.» hundred (Rev 7:4, 14:1)
    ("and had xii gates and at the gates xii. angels", ["had twelve gates", "gates twelve angels"], [r"\d", r"xii"]),
    ("xl kyne and x bulles", ["forty kine and ten bulls"], [r"\d"]),
    ("there were sealed an C. and xliiii. M. of all the trybes",
     ["sealed an hundred and forty-four thousand of all"], [r"\d", r"C", r"xliiii"]),
    ("with him C. and xliiii. thousande havynge", ["him one hundred and forty-four thousand"], [r"\d"]),
    ("we haue broght it agene with us", ["it again with"], [r"agene"]),
    ("the .iiiii.M. and how many", ["the five thousand and"], [r"\d"]),  # Matt 16:10 as PRINTED (owner 2026-09-30)
    # controls: plain words made of roman letters must NOT be read as numerals
    ("I will not lyve in civil strife", ["will", "civil"], [r"\d", r"thousand", r"hundred"]),
    ("he was ill. And it came to passe that I did. So he dyd mix.", ["ill.", "did.", "mix."], [r"\d"]),
    ("Then sayde i. vnto them", ["unto them"], [r"\d", r"one"]),
    ("And the Lorde sayde vnto Moses", ["Moses"], [r"\d"]),
]


def main():
    bad = 0
    for text, must, mustnot in CASES:
        out = re.sub(r"\s+", " ", normalize(text, "tyndale"))
        miss = [m for m in must if m not in out]
        hits = [r for r in mustnot if re.search(r, out)]
        if miss or hits:
            bad += 1
            print(f"FAIL {text!r}\n  -> {out!r}\n  missing {miss} forbidden {hits}")
    print(f"{len(CASES) - bad}/{len(CASES)} pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
