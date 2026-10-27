# -*- coding: utf-8 -*-
"""Per-verse SYNTHESIS-INPUT overrides. Never touches the displayed text.

    python tools/synthesis_overrides.py --show ylt 12 23 25

## Why a per-VERSE table, when pronounce_lexicon.py already exists

The lexicon respells a WORD everywhere it occurs. Some verses fail for a reason
that has nothing to do with any word: ylt `12/23 v25` doubled its final name in
**12 of 12 draws** across three sessions, and the cause was its trailing
SEMICOLON — the same text with a full stop renders clean. That is a property of
one verse's punctuation, not of a word, so it needs its own table.

## ⛔ RULES, and each one is a bug that already happened elsewhere

1. **The words spoken must not change.** Punctuation and spacing only, or a
   respelling of the same word (the lexicon's own lever). Anything else makes
   the audio disagree with the displayed verse AND with `align_words`'
   reference text, which would silently wreck word-level highlighting.
2. **The displayed text is never rewritten.** This is applied at the synthesis
   boundary, once, exactly like `pronounce_lexicon.apply`.
3. **`validated` is who HEARD it, not who wrote it.** An unvalidated row is a
   proposal and must not ship — a respelling is a hypothesis about how this
   model reads these characters, and 6 of 18 lexicon guesses were wrong, one of
   them actively worse than the original.
4. **Record WHY**, with the draw count it replaces. A future session will
   otherwise "clean up" the odd-looking punctuation and reintroduce the defect.
"""
import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (set, book, chapter, verse) -> (synthesis_text, why, validated_by)
OVERRIDES = {
    # ★ EAR-CONFIRMED 2026-10-11 (owner): the printed text doubles a word and
    #   the model said it a THIRD time (Ps «Ea» x3, Jer «Soñé» x3, John «fué
    #   hecho» x2), failing 3/3 repair draws each. Variant A of each was clean
    #   in 2/2 draws; Jer B and C, John B repeated.
    #   Evidence: _work/es_ear_2026-10-11/es_ear_variants_2026-10-11.mp3 + .txt
    ("es", 18, 39, 15): (
        "Sean asolados en pago de su afrenta los que me dicen: ¡Ea! ¡Ea!",
        "«¡Ea, ea!» was said with a third «Ea» in 3/3 draws",
        "owner ear 2026-10-11"),
    ("es", 23, 22, 25): (
        "Yo he oído lo que aquellos profetas dijeron, profetizando mentira en mi nombre, diciendo: Soñé; soñé.",
        "«Soñé, soñé.» was said with a third «soñé» in 3/3 draws",
        "owner ear 2026-10-11"),
    ("es", 42, 0, 3): (
        "Todas las cosas por él fueron hechas; y sin él nada de lo que es hecho fué hecho.",
        "the comma before «fué hecho» made the model repeat it in 3/3 draws",
        "owner ear 2026-10-11"),
    # ★ EAR-CONFIRMED 2026-09-05 (owner, take 2): "2 sounds good. pronunciation
    #   and no repeat." Variant test: the printed form
    # doubled «Zechariah» (12/12 draws); semicolon -> full stop rendered clean,
    # as did dropping it. colon->comma and a spaced full stop still doubled.
    # Evidence: _work/EAR_variants_ylt_12_23_v25.ogg (take 2).
    ("ylt", 12, 23, 25): (
        "A brother of Michah is Ishshiah; for sons of Ishshiah: Zechariah.",
        "trailing ';' made the model re-say the final name in 12/12 draws",
        "owner ear 2026-09-05"),
    # ★ EAR-CONFIRMED 2026-09-05 (owner): "for the eastward westward thing,
    #   2 and 3 sound good" — take 2 is this row. The printed form says «westward»
    # for «eastward» (a SUBSTITUTION, 4/4 draws). Full stop, dropped semicolon,
    # an «eestward» respelling and a split «eastward; and westward.» all
    # rendered «eastward and westward» in one draw each.
    # ⛔ The gate flags EVERY take of this verse `repeat:k2`, correct ones
    #    included — «eastward»/«westward» score alike. It cannot adjudicate
    #    this verse; only an ear can.
    # ⛔⛔ SUPERSEDED 2026-09-07 — THE 09-05 ROW DID NOT HOLD.
    #   The row above was the printed text with the trailing ';' -> '.', and it
    #   was ear-confirmed on ONE DRAW. Re-tested 2026-09-07 with fresh draws:
    #   that exact string rendered «westward and westward» AGAIN.
    # ⚠⚠ THE 09-05 EVIDENCE WAS «one draw each» — its own note says so. One
    #   clean draw does not clear an input for a defect that is stochastic in
    #   its EXPRESSION even when systematic in its cause; it is the `Eelighsha`
    #   mistake in a different costume. ▶ THAT is why CLAUDE.md kept recording
    #   this verse as unfixed while an ear-confirmed override sat right here:
    #   the override was real, and it did not work.
    # ▶ 2026-09-07, 8 variants, PUNCTUATION ONLY. The defect reproduced in
    #   7 of 8 — so it is repeatable on demand, and this verse is now the
    #   project's only VALIDATABLE fixture for the substitution class.
    #   ⛔ A semicolon after «eastward» FAILED. A semicolon before it FAILED.
    #      An em-dash FAILED. A trailing full stop (the old row) FAILED.
    #      Only a MID-VERSE FULL STOP after «eastward» produced «eastward».
    # ★★ EAR-CONFIRMED TWICE, 2026-09-07 — and the second one is the stronger:
    #    (1) on the variant take: «take 7 is good»;
    #    (2) on the SHIPPED AUDIO after the repair, sliced out of
    #        narration/ylt/0/12.ogg: «audio is correct, eastward, and westward».
    # ▶ THE DISTINCTION MATTERS HERE MORE THAN ANYWHERE. The row this one
    #   replaced was cleared on a test render and the SHIPPED verse stayed
    #   defective for two days, because the repair discarded the correct draw.
    #   A clearance on a variant clip says the INPUT is right; only a clearance
    #   on the shipped file says the SET is right.
    #   Evidence: research/_evidence/gen13_14_substitution_reproduced_2026-09-07.md
    #   Clip: _work/EAR_variants_ylt_0_12_v14.ogg (take 7).
    # ⚠ It KEEPS the trailing ';' — that is what he heard, and a fourth string
    #   nobody has listened to is a guess. Do not "tidy" it into a full stop.
    ("ylt", 0, 12, 14): (
        "And Jehovah said unto Abram, after Lot's being parted from him, "
        "`Lift up, I pray thee, thine eyes, and look from the place where thou "
        "art, northward, and southward, and eastward. And westward;",
        "a MID-VERSE full stop after «eastward» is the only input of 8 that "
        "stopped the substitution of «westward» for «eastward»; the 2026-09-05 "
        "trailing-full-stop row was re-tested and FAILED",
        "owner ear 2026-09-07"),
    # ★ EAR-CONFIRMED 2026-09-05 (owner): "2 and 3 pass" — take 2 is this row.
    # THE THIRD INSTANCE OF THE TRAILING-SEMICOLON FAULT, and the first found by
    # PREDICTION rather than by exhausting draws. The owner heard a real "sh"
    # after «Shaul» ("sh after shaul still"), and it SURVIVED 3 GATED DRAWS —
    # which is what said the defect is in the INPUT, not in any one draw.
    # ⚠ It was nearly dismissed as ASR noise: CLAUDE.md records that this verse's
    #   final word is chronically mistranscribed (shawl / shop / shri), and the
    #   gate-fix notes cite this very verse as the example. Only the ear
    #   separated «the ASR misheard it» from «the TTS spoke it».
    # ▶ Variant test, and it is mechanistic rather than lucky: all THREE takes
    #   keeping the ';' failed (as printed -> append «she»; colon->comma ->
    #   append «shoal»; spaced full stop -> repeat + append «shaul»), and BOTH
    #   takes dropping it were clean. Evidence:
    #   _work/EAR_variants_ylt_12_3_v24.ogg (takes 2 and 3 both passed the ear;
    #   take 2 chosen to match the two rows above).
    ("ylt", 12, 3, 24): (
        "Sons of Simeon: Nemuel, and Jamin, Jarib, Zerah, Shaul.",
        "trailing ';' made the model append a stray «sh» after «Shaul»; "
        "survived 3 gated draws, so redrawing could never fix it",
        "owner ear 2026-09-05"),
}


# ★ tyn «the» = THEE, per site (owner 2026-09-28: «do thee per verse»).
#   Tyndale spells the pronoun «the»; the narrator read it as the article.
#   Sites are DATA, derived by tools/derive_tyn_thee_sites.py (KJV-aligned,
#   next-word screened, under-correcting) into tools/tyn_thee_sites.json as
#   [book, chapter(1-based), verse, n] = the n-th whole-word «the» of the ASSET
#   verse. Same word respelled (rule 1 holds), display untouched (rule 2).
#   ⚠ If the spoken text no longer holds the same number of «the» as the
#   asset verse (a normalizer change minted or ate one), the site is SKIPPED
#   and said so - a shifted ordinal would put «thee» on an article.
#   Validation: the owner directed the class; the repaired verses go to his
#   ear as a kit like every other tyn repair.
_THEE = None
_THE = __import__("re").compile(r"\bthe\b", __import__("re").I)


def _thee_sites():
    global _THEE
    if _THEE is None:
        import json
        p = Path(__file__).resolve().parent / "tyn_thee_sites.json"
        _THEE = {}
        if p.exists():
            for b, c, v, n in json.loads(p.read_text(encoding="utf-8"))["sites"]:
                _THEE.setdefault((b, c - 1, v), set()).add(n)
    return _THEE


def _asset_the_count(book, chapter, verse):
    import json
    global _TYN_ASSET
    try:
        _TYN_ASSET
    except NameError:
        p = Path(__file__).resolve().parent.parent / "app/src/main/assets/bibles/en_tyndale.json"
        _TYN_ASSET = json.loads(p.read_text(encoding="utf-8"))
    return len(_THE.findall(_TYN_ASSET[book]["chapters"][chapter][verse - 1] or ""))


def apply_thee(book, chapter, verse, text):
    ns = _thee_sites().get((book, chapter, verse))
    if not ns:
        return text, False
    if len(_THE.findall(text)) != _asset_the_count(book, chapter, verse):
        print(f"    ⚠ thee sites skipped for {book}/{chapter} v{verse}: «the» count changed "
              "between asset and spoken text", flush=True)
        return text, False
    k = iter(range(10 ** 6))
    return _THE.sub(lambda m: (m.group(0) + "e") if next(k) in ns else m.group(0), text), True


# ★ tyn «prophesy» the VERB (owner ear 2026-09-28, Acts 2:17 on the tyn voice:
#   «all new draws sound fine»). NOT a lexicon scope: Tyndale spells the NOUN
#   «prophesy» too (Rom 12:6, 1 Tim 4:14, 2 Pet 1:19-20, Rev 1:3, 19:10,
#   22:7-19 = 10 of the 20 sites), and the noun must stay «prophe-see». The
#   spelling is read from the lexicon row so it stays the single source.
#   Keys (book, chapter0, verse), every one read by hand as the verb.
TYN_PROPHESY_VERB = {
    (43, 1, 17), (43, 1, 18), (43, 20, 9),                    # Acts 2:17, 2:18, 21:9
    (45, 12, 2), (45, 13, 1), (45, 13, 24), (45, 13, 31), (45, 13, 39),  # 1 Cor
    (65, 9, 11), (65, 10, 3),                                 # Rev 10:11, 11:3
}


def apply_tyn(book, chapter, verse, text):
    text, used = apply_thee(book, chapter, verse, text)
    if (book, chapter, verse) in TYN_PROPHESY_VERB:
        import re
        import pronounce_lexicon
        sp = pronounce_lexicon.LEXICON["prophesy"][0]
        t2 = re.sub(r"\bprophesy\b", sp, text)
        used, text = used or t2 != text, t2
    return text, used


def apply(set_key, book, chapter, verse, text):
    """-> (synthesis_text, override_used). Falls through to `text` unchanged."""
    e = OVERRIDES.get((set_key, book, chapter, verse))
    if not e or not e[2]:          # unvalidated rows are INERT, like the lexicon
        if set_key == "tyn":
            return apply_tyn(book, chapter, verse, text)
        return text, False
    return e[0], True


def unvalidated():
    return [k for k, v in OVERRIDES.items() if v[2] is None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", nargs=4, metavar=("SET", "B", "C", "V"))
    a = ap.parse_args()
    if a.show:
        s, b, c, v = a.show[0], int(a.show[1]), int(a.show[2]), int(a.show[3])
        e = OVERRIDES.get((s, b, c, v))
        print(f"{s} {b}/{c} v{v}: " + ("no override" if not e else
              f"\n  text     : {e[0]}\n  why      : {e[1]}\n  validated: {e[2]}"))
        return
    print(f"{len(OVERRIDES)} override(s)")
    for (s, b, c, v), (t, why, val) in OVERRIDES.items():
        print(f"  {s} {b}/{c} v{v}  {'VALIDATED ' + val if val else '⚠ UNVALIDATED — inert'}"
              f"\n      why: {why}")
    u = unvalidated()
    if u:
        print(f"\n⛔ {len(u)} row(s) are proposals and will NOT be applied until an "
              "ear confirms them.")
        sys.exit(1)


if __name__ == "__main__":
    main()
