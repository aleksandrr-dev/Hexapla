# -*- coding: utf-8 -*-
"""Respell words for the TTS so it says them correctly. SYNTHESIS INPUT ONLY.

    python tools/pronounce_lexicon.py --scope --lang ylt      # what it would touch
    python tools/pronounce_lexicon.py --show "And Abraham giveth all that he hath"

## Why this exists

The render can say the RIGHT WORD with the WRONG PHONETICS. Confirmed by the
owner's ear, 2026-09-04, on ylt:

  * `Canaan`  -> heard «can-a-yin», should be «CAY-nan»
  * `Levites` -> heard «Levitites» — an extra syllable
  * `Abraham` -> the first `a` is read as in *apple*; it is as in *acorn*
  * `Ephraim` -> heard «EFF-raym», should be «EEF-raym»

None of the four screens sees this. `qa_selfrepeat` finds re-spoken tails,
`qa_asr_sweep` finds appended words, `qa_substitution` finds a wrong word — but
here the word is right. The ASR *does* emit a different token (it transcribes
«Kanan»), so the signal exists; every screen throws that class away on purpose,
because mid-verse substitution flags on archaic English ran ~3 per chapter with
essentially no true positives. **The instrument sees it and we discard it.**

## ⛔⛔ THE ENTRIES BELOW ARE GUESSES UNTIL AN EAR CONFIRMS THEM

A respelling is a hypothesis about how *this* model reads *these* letters. It is
not knowledge. Nothing here may be used in a real render until each entry has
been rendered on one verse and listened to. `validated:` records who confirmed
it and when; an entry with `validated: None` is a proposal.

▶ This mirrors the rule already settled on 0/12 v14: text evidence cannot tell
«the ASR misheard» from «the TTS said it wrong», and it equally cannot tell
whether a respelling FIXED anything. Only an ear closes the loop.

## ⛔ JEHOVAH IS NOT IN THIS LEXICON, AND THAT IS A DECISION, NOT AN OVERSIGHT

`Jehovah` is mispronounced «Jee-hovah» SOME of the time — 2 of a random 14, then
"a lot" in a 40-clip sample (owner, 2026-09-04). It is in **6,626 verses**, and:

  * a respelling would rewrite all 6,626 to fix a minority and put the majority
    at risk — the entries here are for words that are ALWAYS wrong;
  * **the ASR cannot find the bad ones** — both ear-flagged verses transcribe as
    `jehovah`, identically to verses the owner passed;
  * **acoustic clustering of the word was BUILT, VALIDATED AND FAILED** —
    `tools/qa_pronounce_cluster.py --validate` put both known-bad clips in a
    9-clip cluster against a criterion of «both bad, at most 2 good». It had
    separated the verses by SURROUNDING PHRASE, not by pronunciation.

▶ **The owner's call, 2026-09-04: leave it.** «I think we can leave it, as it is
a lot to listen to.» Recorded as a known, measured limitation of the ylt
narration. Do not quietly add a `jehovah` entry here; re-opening it means asking
him, not inferring.

## ⚠ IT MUST NEVER TOUCH THE DISPLAYED TEXT

`apply()` is for the string handed to the synthesiser and nothing else. The
verse the reader sees, the asset JSON, the alignment text and every screen's
reference text all keep the real spelling — otherwise the app would show
«Aybraham», and `align_words` would align audio against a word that is not in
the Bible. Call it at the synthesis boundary, once, and nowhere else.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# word (lowercased key) -> (respelling, why, validated_by)
# Case is restored from the original token, so "abraham" covers "Abraham".
# ⚠ Keep the respelling ORTHOGRAPHIC, not IPA: the model reads letters.
LEXICON = {
    "canaan":   ("Kaynan",    "heard «can-a-yin»; want «CAY-nan»",        None),
    "levite":   ("Leevite",   "heard an extra syllable, «Levitite»",      None),
    "levites":  ("Leevites",  "heard «Levitites»",                        None),
    "abraham":  ("Aybraham",  "first «a» read as in apple; want acorn",   None),
    "ephraim":  ("Eefraim",   "heard «EFF-raym»; want «EEF-raym»",        None),
    # ⚠ DERIVED FORMS — the ROOT was ear-confirmed, these were NOT. A word can
    # inherit the root's spelling and not its defect, so each needs its own
    # verdict; they are listed separately rather than folded into a prefix rule.
    # Missed entirely at first: apply() matches whole words, so «Canaanite» is
    # not covered by «canaan». That is also why an earlier count of "Canaan in
    # 156 verses" was too high — it prefix-matched the derived forms.
    "canaanite":    ("Kaynanite",    "derived from canaan — UNHEARD",     None),
    "canaanites":   ("Kaynanites",   "derived from canaan — UNHEARD",     None),
    "canaanitess":  ("Kaynanitess",  "derived from canaan — UNHEARD",     None),
    "levitical":    ("Leevitical",   "derived from levite — UNHEARD",     None),

    # ── the -eth question, SETTLED SMALL by ear 2026-09-04 ──────────────────
    # The owner heard 13 forms. Wrong: `fleeth`, `seeth`. FINE: `goeth`,
    # `dieth`, `lieth` — so it is NOT vowel-stems in general — and fine across
    # every consonant-stem form (`cometh`, `taketh`, `speaketh`, `maketh`,
    # `giveth`), plus both controls (`hath`, `saith`).
    # ▶ The defect is the DOUBLE-E stem: «ee» + «eth» collapses to one syllable.
    #   That is 3 forms and 231 occurrences, NOT the 618 forms / 6,499 verses
    #   an unexamined "-eth is broken" would have condemned.
    # ⛔ `teeth` and `jaw-teeth` match the same spelling shape and are CORRECTLY
    #   one syllable. They must never enter this lexicon.
    "fleeth":   ("flee-eth", "heard one syllable; want «FLEE-eth»",       None),
    "seeth":    ("see-eth",  "heard one syllable; want «SEE-eth»",        None),
    "freeth":   ("free-eth", "same double-e shape — UNHEARD",             None),

    # ── a VOWEL error, not a syllable error ────────────────────────────────
    # «calleth» heard with the a of APPLE; it is the aw of CALL. Whether
    # `called`/`call`/`calling` share it is OUT FOR AN EAR CHECK — do not
    # assume they do, and do not assume they don't.
    "calleth":  ("cawleth",  "heard «cal-eth» (a as in apple); want «CAWL-eth»",
                 None),
    "falleth":  ("fawleth",  "same defect as calleth, confirmed by ear 2026-09-04",
                 None),
    # ⛔ AND NOTHING ELSE IN THE a+ll FAMILY. The owner heard `called`, `call`,
    # `calling`, `fall`, `wall`, `small` and `all` and reported every one FINE.
    # So this is NOT a general «aw» vowel problem — `all` alone is in 5,482
    # places and a prefix rule would have rewritten all of them for nothing.
    # It is confined to the -eth forms of call/fall, where the added syllable
    # appears to shift the stress off the vowel. 468 occurrences, not 6,000.

    # ── two more names, ear-confirmed 2026-09-04 ───────────────────────────
    # ⛔ `Jobab` (9 occurrences) is a DIFFERENT NAME and must never be rewritten.
    #    apply() matches whole words, so it is safe — but the trap is one
    #    careless prefix rule away, exactly like `Canaanite` vs `canaan`.
    # ⚠ There is no lowercase «job» anywhere in the ylt text, so this entry
    #    cannot collide with the ordinary noun.
    "job":       ("Jobe",      "heard «Jahb»; wanted to rhyme with «robe»",  None),
    "hezekiah":  ("Hezakyah",  "heard «Hez-a-KEE-yah»; want «Hez-a-KY-ah»",  None),
}

WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def _match_case(src, repl):
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def apply(text):
    """-> (synthesis_text, [words replaced]). NEVER use on displayed text."""
    hits = []

    def sub(m):
        w = m.group(0)
        # possessive is carried, so «Abraham's» -> «Aybraham's»
        base, tail = w, ""
        for suf in ("'s", "’s", "'", "’"):
            if base.lower().endswith(suf):
                base, tail = base[: -len(suf)], suf
                break
        e = LEXICON.get(base.lower())
        if not e:
            return w
        hits.append(base)
        return _match_case(base, e[0]) + tail

    return WORD.sub(sub, text), hits


def unvalidated():
    return [k for k, v in LEXICON.items() if v[2] is None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", help="apply to one string and print the result")
    ap.add_argument("--scope", action="store_true",
                    help="count the verses each entry would change")
    ap.add_argument("--lang", default="ylt")
    ap.add_argument("--asset",
                    default="C:/Projects/Hexapla/app/src/main/assets/bibles/en_ylt.json")
    a = ap.parse_args()

    if a.show:
        out, hits = apply(a.show)
        print(f"in : {a.show}")
        print(f"out: {out}")
        print(f"replaced: {hits or '(nothing)'}")
        return

    if not a.scope:
        print("give --scope or --show")
        sys.exit(2)

    data = json.loads(Path(a.asset).read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) and "books" in data else data
    per, chapters, total = {}, set(), 0
    for bi, b in enumerate(books):
        for ci, ch in enumerate(b["chapters"] if isinstance(b, dict) else b):
            for v in ch:
                if not isinstance(v, str):
                    continue
                _, hits = apply(v)
                if hits:
                    total += 1
                    chapters.add((bi, ci))
                    for h in {x.lower() for x in hits}:
                        per[h] = per.get(h, 0) + 1
    print(f"lexicon entries: {len(LEXICON)}  "
          f"({len(unvalidated())} UNVALIDATED — no ear has confirmed them)")
    print(f"\n{'entry':<12}{'verses':>8}")
    for k in sorted(per, key=lambda x: -per[x]):
        print(f"{k:<12}{per[k]:>8}")
    print(f"\nverses that would change : {total}")
    print(f"chapters to re-render     : {len(chapters)}")
    print("\n⛔ A re-render is per VERSE, not per chapter — a chapter --force is")
    print("   forbidden for a defect class that is not truncation.")
    if unvalidated():
        print("\n⛔⛔ DO NOT RENDER WITH THIS LEXICON YET. Unvalidated entries:")
        print("   " + ", ".join(sorted(unvalidated())))
        print("   Render ONE verse per entry, listen, then set validated_by.")


if __name__ == "__main__":
    main()
