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
    ("ylt", 0, 12, 14): (
        "And Jehovah said unto Abram, after Lot's being parted from him, "
        "`Lift up, I pray thee, thine eyes, and look from the place where thou "
        "art, northward, and southward, and eastward, and westward.",
        "trailing ';' preceded a substitution of «westward» for «eastward»",
        "owner ear 2026-09-05"),
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


def apply(set_key, book, chapter, verse, text):
    """-> (synthesis_text, override_used). Falls through to `text` unchanged."""
    e = OVERRIDES.get((set_key, book, chapter, verse))
    if not e or not e[2]:          # unvalidated rows are INERT, like the lexicon
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
