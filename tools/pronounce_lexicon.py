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
    "levite":   ("Leevite",   "heard an extra syllable, «Levitite»",      "owner ear 2026-09-05"),
    "levites":  ("Leevites",  "heard «Levitites»",                        "owner ear 2026-09-05"),
    # ✅ RE-CONFIRMED 2026-09-05 in a SHORT CARRIER, not just the long verse it
    # was first validated on. The re-test was run because `Abram` proved that
    # word-initial `Ay` can read /aɪ/ («eye»), which would have made THIS row
    # wrong too across 229 verses. It does not: the owner heard `Aybraham`
    # against printed `Abraham` and called it perfect. The row stands.
    # ⛔⛔ REJECTED IN THE REAL VERSE — owner ear 2026-09-06, on the BEFORE/AFTER
    # set cut from the actual re-rendered audio: «he still says eye-brah-ham».
    # So `Aybraham` reads /aɪ/ after all, EXACTLY like `Aybram` did, and the
    # note above — «RE-CONFIRMED in a SHORT CARRIER ... the row stands» — was
    # WRONG. It is left above verbatim as the record of how it went wrong.
    # ⛔ THE LESSON IS THE OPPOSITE OF THE ONE WE DREW: the short carrier is
    #   what MISLED us here. It was adopted (see `abram`) because a long verse
    #   hid a vowel; it then PASSED a spelling that the long verse fails. So a
    #   short carrier is a fine instrument for HEARING a vowel and NOT a
    #   sufficient one for CLEARING a respelling. ▶ Every row in this table was
    #   validated on a short carrier, so every row is now suspect at exactly
    #   this point; the 2026-09-06 A/B set cleared 8 of them IN A REAL VERSE
    #   (abram, calleth, canaan, canaanite, ephraim, falleth, levite, levites)
    #   and those 8 are the only ones that have ever met that harder test.
    # ⛔ `Aebraham` is the obvious next guess, since `Aebram` is the row that
    #   works. DO NOT SHIP IT UNHEARD. `Aybraham`-right-vs-`Aybram`-wrong was
    #   already proof that these two forms do not track each other; that pair
    #   is now resolved the other way (both wrong), which changes nothing about
    #   the rule — a root and a derived form still need SEPARATE verdicts.
    # ⚠ SCOPE IF WRONG AGAIN: 229 verses / 76 chapters.
    # ✅ SOLVED WITH `Aebraham` — owner ear 2026-09-06, TWICE: once on the
    # candidate set (both draws) and again through the REAL text path
    # (normalize_text applied, Gen 21:24 + Gen 22:1 where the name occurs
    # twice). ▶ `ae` is now the shape that fixes BOTH `Abram` and `Abraham`,
    # where word-initial `Ay` failed on both. That is the first time two rows
    # in this table have agreed on a shape — it is a lead for the next name,
    # NOT a licence to apply it unheard.
    "abraham":  ("Aebraham",  "`Aybraham` read /aɪ/ like `Aybram`; ae gives the acorn a",
                 "owner ear 2026-09-06"),
    # ✅ `Abram` SOLVED 2026-09-05 — and it took FOUR rounds because the first
    # diagnosis was wrong. Rounds 1-3 assumed `Ay` had fixed syllable one and
    # varied syllable TWO (`Aybram`, `Aybramm`, `Aybrahm`, `Ay bram`, `AyBram`,
    # `Aybraam`, `Aybramme`); every one came back «EYE-bram». On a SHORT CARRIER
    # the owner could isolate the vowel and reported the real fault: word-initial
    # `Ay` is read /aɪ/, so syllable one was never fixed at all.
    # ▶ `Aebram` (the `ae` digraph) was heard as perfect.
    # ⛔⛔ NOTE THE PAIR: `Aybraham` is RIGHT and `Aybram` is WRONG — the SAME
    #    word-initial `Ay`, opposite verdicts, in two forms of one name. This is
    #    the third instance of the standing rule that a root and its derived
    #    forms need SEPARATE verdicts and neither licenses the other. Compare
    #    `Kaynen`, where "ay" AFTER A CONSONANT gives /eɪ/ correctly.
    # ⚠ A long verse was the wrong instrument: the vowel was audible only once
    #   the name sat in a short carrier phrase. Prefer short carriers for vowels.
    "abram":    ("Aebram",    "heard «EYE-bram» with Ay-; ae digraph gives the acorn a",
                 "owner ear 2026-09-05"),
    "ephraim":  ("Eefraim",   "heard «EFF-raym»; want «EEF-raym»",        "owner ear 2026-09-05"),
    # ⚠ DERIVED FORMS — the ROOT was ear-confirmed, these were NOT. A word can
    # inherit the root's spelling and not its defect, so each needs its own
    # verdict; they are listed separately rather than folded into a prefix rule.
    # Missed entirely at first: apply() matches whole words, so «Canaanite» is
    # not covered by «canaan». That is also why an earlier count of "Canaan in
    # 156 verses" was too high — it prefix-matched the derived forms.
    # ✅ THE BARE NAME IS FIXED — owner ear 2026-09-05, on Genesis 9:26.
    # Seven takes were heard. Takes 5 (Kaynen), 6 (Kaynon) and 7 (Caynun) were
    # all reported good; take 4 (Kaynun) was NOT, and takes 1-3 were the
    # printed-«Canaan» control (the shipped «can-a-yin»).
    # ▶ THREE PASSED, so this row is a CHOICE among validated options, not the
    #   only one that worked. `Kaynen` is chosen for spelling consistency with
    #   the `Kaynanite`/`Kaynanites` rows below; `Kaynon` and `Caynun` are
    #   equally ear-approved and may be swapped in without a new test.
    # ⚠ It remains true that a root and its derived forms need SEPARATE
    #   verdicts — that rule is what produced four different answers here, and
    #   it is why this row was tested on its own rather than inferred.
    "canaan":       ("Kaynen",       "bare name heard «can-a-yin»; «Kaynan» gave «can i an»",
                     "owner ear 2026-09-05"),
    "canaanite":    ("Kaynanite",    "derived from canaan",     "owner ear 2026-09-05"),
    "canaanites":   ("Kaynanites",   "derived from canaan",     "owner ear 2026-09-05"),
    "levitical":    ("Leevitical",   "derived from levite",     "owner ear 2026-09-05"),

    # ── `Naaman`, 2026-09-07. Owner: "try it the same way we fixed Canaan" ──
    # Heard «Nah min» (broad a) where the name is «Na min»; A/B on II Kings 5:1
    # with three respellings in the `Kaynen` shape (long-a written «ay»).
    # ★ Owner's ear, 2026-09-07: "3 for Naaman" = take 3 = `Naymen`.
    #   `Nayamen` and `Naymun` were heard and NOT chosen — see REJECTED below.
    # ✅✅ SPOT-CHECK PASSED — the `prophesy` standard is MET, 2026-09-07.
    #   Rendered in TWO chapters the ear had not been primed on —
    #   Numbers 26:40 and Genesis 46:21 — and the owner's verdict on the
    #   respelled take in both was «4 works, pronounced correctly».
    #   Clips: _work/EAR_variants_ylt_3_25_v40.ogg, _work/EAR_variants_ylt_0_45_v21.ogg
    # ⚠ THE CLASS CAVEAT STILL STANDS, and it is not pedantry. `Naaman` is the
    #   SPORADIC class: CLAUDE.md records it coming out BOTH right and wrong
    #   from draws of an IDENTICAL input (Luke 4:27, 2026-09-07). So this row
    #   has cleared the procedural bar `prophesy` set, but a sporadic word can
    #   still draw badly on a verse nobody has heard. ⛔ Do not upgrade this
    #   note to «always correct».
    # ⛔ Scope is 15 verses / 5 chapters — DERIVE it, never quote that here.
    #   Genesis 46, Numbers 26, II Kings 5 (10 of them), I Chronicles 8, Luke 4.
    # ⛔⛔ THE LOOK-ALIKES ARE THE `canaan`/`Canaanite` TRAP, AND ONE IS A
    #   DIFFERENT PERSON. A whole-word key excludes all of them, which is why
    #   this row is whole-word and must stay so:
    #     · `Naamite`  (Numbers 26:40) — ✅✅ **CHECKED AND CORRECT AS PRINTED.**
    #       Owner's ear, 2026-09-07, on take 4 of the Numbers 26:40 spot-check
    #       (where it sits UNTOUCHED beside the respelled `Naymen`):
    #       «4th Naamite is correct». ⛔ IT MUST NEVER ENTER THIS LEXICON.
    #       ▶ This is the `Elijah` result repeated: a derived form ASSUMED to
    #         share its root's defect, CHECKED, and found sound. The whole-word
    #         key already excluded it; now there is a verdict saying it should.
    #     · `Naamathite`  (Job x4) — Zophar. A DIFFERENT NAME. Never sweep it in.
    #     · `Naamah`, `Naarah` — different names again.
    "naaman":       ("Naymen",       "heard «Nah min» (broad a); the Kaynen "
                                     "shape. ⚠ SPORADIC class — one draw, "
                                     "un-primed spot-check still owed",
                     "owner ear 2026-09-07"),

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
    #
    # ✅ THE REMEDY, FOUND 2026-09-07 — and it is NOT the hyphen.
    # The owner re-reported the defect on II Chronicles 23:13 («seeth still
    # like seethe, not see-eth»), picked three hyphen-free candidates, and
    # chose by ear from whole-verse renders of that same verse:
    #     **seeith** ✅ · seeyeth · siyeth
    # ⚠⚠ HE CORRECTED HIMSELF, AND THE CORRECTION IS THE RULING. His first
    # message named `seeyeth`; he then re-listened and said «on the short, it
    # is seeith that's correct». The candidates had been sent as ONE clip with
    # the takes 1 s apart, so choosing meant COUNTING POSITIONS — take 2 is
    # `seeith`, take 3 is `seeyeth`. ▶ Never ask for a pick off a positional
    # montage again: send one file per candidate, named for the candidate.
    # ⛔ `seeyeth` is NOT recorded as heard-wrong — it is NOT CHOSEN, which is
    #   weaker evidence, exactly as `naaman__nayamen` distinguishes the two.
    # ▶ Why this family works at all: both winners keep `-eth` out of the bare
    #   double-e environment. The hyphen form fixed the syllable count and
    #   still failed, because the hyphen is read as a PAUSE — see REJECTED.
    # ⛔⛔ THIS SAYS NOTHING ABOUT `fleeth` AND `freeth`. Same defect class, but
    #   one shape passing says nothing about another — the exact lesson the
    #   hyphen rejection recorded. Each needs ITS OWN ear test on a real verse.
    # ▶ research/_evidence/ylt_ear_review_2026-09-07.md
    # ── CLEARED FOR wbt TOO, 2026-09-08, ON PHONEMES NOT ON AN EAR ─────────
    # wbt is a KOKORO set (voice am_adam), and kokoro is fed PHONEMES: the
    # misaki/espeak G2P string IS what the model speaks. So for a kokoro set
    # the G2P output is not a proxy for the pronunciation, it is the
    # pronunciation — a stronger instrument than an ear, at 0 GPU and 0 tokens.
    #     he seeth  -> hi sˈiθ     ONE syllable — the defect, confirmed
    #     seeith    ->    sˈiɪθ    two syllables «SEE-ith» — the fix
    #     he fleeth -> hi flˈiθ    ONE syllable
    #     fleeith   ->    flˈiɪθ   two syllables
    # ⚠ THIS CLEARANCE IS FOR THESE TWO ROWS AND FOR wbt ONLY. The same screen
    # over the whole table showed blanket-applying it to wbt would BREAK three
    # names kokoro already says correctly:
    #     abraham  ˈAbɹəhˌæm -> ˈibɹəhˌæm   («EEB-raham»)
    #     abram    ˈAbɹæm    -> ˈibɹæm
    #     elisha   əlˈIʃə    -> ˈilɪɡʃə     (inserts a /ɡ/ — and əlˈIʃə is
    #                                        ALREADY the «ee-LYE-sha» target)
    # and that calleth/falleth/canaan/canaanite(s)/prophesy are phoneme-IDENTICAL
    # under their respellings on kokoro — pure no-ops. ▶ The per-set gate earned
    # its keep here: «same defect class» did NOT mean «same remedy».
    # ⛔ `freeth` is NOT cleared for wbt: it does not occur in en_webster.json.
    # ⛔ tyn is CHATTERBOX and gets NO clearance from this — chatterbox is not
    #   phoneme-fed, so none of the above is evidence about it. It needs a real
    #   render and an ear. Scope there is 12 verses / 10 chapters.
    # ▶ research/_evidence/wbt_tyn_double_e_2026-09-08.md
    "seeth":    ("seeith",  "double-e stem collapsed to ONE syllable, heard "
                            "«seethe»; want «SEE-eth». Chosen by ear on the "
                            "whole printed II Chronicles 23:13. wbt cleared "
                            "2026-09-08 on kokoro G2P (sˈiθ -> sˈiɪθ)",
                 "owner ear 2026-09-07; wbt by kokoro G2P 2026-09-08",
                 ("ylt", "wbt")),
    # ── the other two double-e stems, ear-tested 2026-09-07 on real verses ──
    # Each got its OWN test rather than inheriting `seeith` by analogy, and
    # the results justify that: the family does NOT take one uniform shape.
    #   fleeth (Genesis 31:21): `fleeith` AND `fleeyeth` BOTH passed his ear.
    #     `fleeith` is wired for consistency with `seeith`; `fleeyeth` is
    #     recorded as ALSO ACCEPTABLE (not rejected) — a real fallback if
    #     `fleeith` ever fails a spot-check.
    #   freeth (I Samuel 19:10): he chose `friyeth` — a DIFFERENT shape from
    #     the other two. Analogy would have got this wrong.
    # ⛔⛔ `fliyeth` WAS DISQUALIFIED ON MEANING, NOT RHYTHM: it renders as
    #   «flyeth» — FLY, not FLEE — which would have changed the sense of 44
    #   verses. Caught by ASR before the owner ruled. ▶ A respelling can change
    #   the WORD, not just its sound; check the transcript, not only the ear.
    #   ⚠ The same shape is FINE for `freeth` (`friyeth` transcribes as
    #   «freeth»), which is why the check is per word and never per pattern.
    "fleeth":   ("fleeith", "same double-e collapse as `seeth`; heard «fleethe»."
                            " `fleeyeth` also passed the ear — see REJECTED "
                            "for that record, it is a fallback not a failure. "
                            "wbt cleared 2026-09-08 on kokoro G2P "
                            "(flˈiθ -> flˈiɪθ)",
                 "owner ear 2026-09-07; wbt by kokoro G2P 2026-09-08",
                 ("ylt", "wbt")),
    "freeth":   ("friyeth", "same double-e collapse; ONE occurrence in ylt "
                            "(I Samuel 19:10). ⚠ owner picked a different "
                            "shape here than for seeth/fleeth",
                 "owner ear 2026-09-07"),

    # ── a VOWEL error, not a syllable error ────────────────────────────────
    # «calleth» heard with the a of APPLE; it is the aw of CALL. Whether
    # `called`/`call`/`calling` share it is OUT FOR AN EAR CHECK — do not
    # assume they do, and do not assume they don't.
    "calleth":  ("cawleth",  "heard «cal-eth» (a as in apple); want «CAWL-eth»",
                 "owner ear 2026-09-05"),
    "falleth":  ("fawleth",  "same defect as calleth, confirmed by ear 2026-09-04",
                 "owner ear 2026-09-05"),
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
    "job":       ("Jobe",      "heard «Jahb»; wanted to rhyme with «robe»",  "owner ear 2026-09-05"),
    # ★ EAR-CONFIRMED 2026-09-04 by the owner on the repair clip set
    # (John 11:35, «Jesus wept» -> heard «jasus wept»).
    # ⚠ THE RESPELLING BELOW IS STILL A GUESS, like every other row here.
    # ⚠ SCOPE: 932 verses / 207 chapters — the LARGEST entry in this table by a
    # wide margin (Canaan is 88/56). If it is wrong, it is wrong 932 times, so
    # it earns its ear test before anything else here.
    # ★ EAR-CONFIRMED 2026-09-04, and the TARGET came from ASKING, not guessing:
    # the owner first said only "mispronounced", then on being asked reported he
    # hears «zee-ka-REE-ah». Wanted: «ZEK-a-RY-ah».
    # ▶ Same defect SHAPE as `hezekiah` (heard «-KEE-yah», want «-KY-ah»), so the
    # respelling follows that row's pattern: «-ryah» for the «-riah» tail, and
    # «Zek-» to stop the leading «Ze-» being read long.

    # ── ear-confirmed 2026-09-06 (evening), on the 24-verse ear clip set ───
    # Both surfaced INCIDENTALLY: the verses were in the ear queue because the
    # GATE flagged them, and the owner reported a mispronunciation instead. That
    # is the fifth defect class doing what this file says it does — the screens
    # cannot see it, only an ear can.
    #
    # ── `elisha` — WIRED IN 2026-09-07 BY THE OWNER'S EXPLICIT DIRECTION, ─────
    #    OVER A STATED OBJECTION. Read this whole block before touching the row.
    #
    # The defect is real and ear-confirmed («el-EE-sha», want «ee-LYE-sha»).
    # `Elysha` was tested 2026-09-06 and heard UNCHANGED — it is in REJECTED.
    # On 2026-09-07 three fresh candidates were rendered on II Kings 5:9 and the
    # owner picked this one: «5 is good.» (`Elighsha` was also good but arrived
    # after a slight pause; `Eelysha` was not named among the good ones, which is
    # what identifies the `y` — not the first vowel — as why `Elysha` failed).
    #
    # ⛔⛔ BUT IT THEN FAILED THE SPOT-CHECK IN TWO OF THREE VERSES:
    #      II Kings 5:9  ✅ good
    #      II Kings 2:1  ❌ not correct — and the AS-PRINTED take was the good one
    #      Luke 4:27     ❌ heard «Eel eesha»
    #    One spelling, three verses, three outcomes. That is the `Jehovah`
    #    signature — SPORADIC — and this file's own rule for that class is that a
    #    respelling is the WRONG tool because it rewrites every occurrence to fix
    #    a minority. It is also NOT the `Hezakyah` «no change» outcome: it does
    #    change the reading, just not reliably in the right direction.
    #
    # ▶ The objection was put to the owner in those terms, with the table above,
    #   and he directed the wire-in anyway (asked twice, because his first answer
    #   was ambiguous between this and «leave it»). That is his call to make and
    #   it is recorded here, not argued again.
    # ⚠ SO THIS ROW IS NOT «ear-validated» IN THE SENSE `prophesy` IS. It is
    #   ear-PREFERRED in one verse and ear-REJECTED in two. If a later session
    #   sees it in the table and assumes the `prophesy` standard, it will be
    #   wrong. Evidence:
    #   research/_evidence/elisha_elijah_naaman_ear_2026-09-07.md
    # ⚠ SCOPE, DERIVED: 55 verses / 13 chapters.
    # ⚠ ONE OF THOSE 55 IS A DIFFERENT PERSON — I Chronicles 1:7, «sons of
    #   Javan: Elisha», normally spelled *Elishah*. YLT sets him without the
    #   final h so this whole-word row sweeps him in. Both names are ordinarily
    #   «ee-LYE-shuh» so it is probably harmless, but it is a `Canaan`/`Canaanite`
    #   -shaped trap and is recorded rather than ignored. `synthesis_overrides.py`
    #   is the per-VERSE table if it ever needs excluding.
    # ⛔ `Elishah`, `Elishama`, `Elishaphat`, `Elisheba` are DIFFERENT NAMES.
    #   apply() matches whole words, so they are safe — do not add a prefix rule.
    # ✅ `Elijah` is pronounced CORRECTLY (owner, 2026-09-07, II Kings 2:1) and
    #   must NEVER enter this table. Scope, derived: 93 verses / 26 chapters.
    "elisha":   ("Eelighsha", "heard «el-EE-sha»; want «ee-LYE-sha». `igh` for /aɪ/ "
                              "after `prophesigh`; `Ee` for the first vowel after "
                              "`Leevite`/`Eefraim`. ⚠ good in II Kings 5:9, WRONG in "
                              "II Kings 2:1 and Luke 4:27 — owner directed the "
                              "wire-in over that objection",
                 "owner direction 2026-09-07 (NOT the prophesy standard)"),

    # ★ `prophesy` — Acts 2:17 (clip 20): heard «prophes-EE». The voice read the
    #   VERB as its own NOUN: `prophesy` is /ˈprɒfɪsaɪ/, `prophecy` is /-si/.
    # ✅✅ EAR-VALIDATED IN THE REAL VERSE — owner, 2026-09-06 evening, on the
    #   BEFORE/AFTER pair cut from the actual re-rendered Acts 2:17: «second
    #   prophesy was correct». Not a short carrier: this is the whole printed
    #   verse, which is the standard `Aybraham` failed. ▶ This is the FIRST row
    #   in this table to be cleared that way.
    # ⚠ SCOPE, DERIVED: 62 verses / 42 chapters.
    # ⛔⛔ AND NOTHING ELSE IN THE FAMILY, ON PURPOSE. `prophesying` (43 verses),
    #   `prophesied` (19) and `prophesieth` (6) share the spelling and were NOT
    #   heard. «-sy is broken» is precisely the shape of rule this project's ear
    #   has cut down three times (see the -eth and a+ll notes above). They are
    #   OUT FOR AN EAR CHECK — do not assume they share it, do not assume they
    #   don't.
    # ⛔ `prophecy` (24 verses) is CORRECTLY said «prophesee» and must never
    #   enter this table. A careless rule on «prophes» would also be wrong for
    #   it, since the noun is spelled with a c.
    "prophesy": ("prophesigh", "verb read as the noun «prophecy»; want «-sigh»",
                 "owner ear 2026-09-06"),
}


# ⛔⛔ A CANDIDATE TEST MUST GO THROUGH `narrate.normalize_text()`.
# Added 2026-09-06 after a test harness produced a defect that does not exist
# in the render. The harness typed the verse out by hand as
#     "And Abraham saith, `I--I do swear.'"
# and fed that straight to the TTS. The REAL pipeline normalizes the asset's
# em-dash first, so what the render actually speaks is
#     "And Abraham saith, I, I do swear.'"
# A bare `--` is not a token the voice handles, and several takes stuttered on
# it. The owner heard the doubling and reported it — correctly — as
# «I do swear, I do swear».
# ▶ THE COST OF NOT CATCHING THIS: it is the tail-repeat signature, on a verse
#   whose PRINTED text already doubles a word (`I—I`). That is precisely the
#   combination this project has twice mis-adjudicated (Isaiah 24:21, and
#   «of the land on the land»), where a text-explained flag was read as a real
#   defect and 3 redraws were burned on a clean verse. Here it would have been
#   read the other way — as evidence against a respelling that is FINE.
# ⚠ So a candidate take differs from a shipped take in TWO ways, and only one
#   of them is the respelling. Build every candidate as:
#       asset verse -> respelling -> narrate.normalize_text(text, lang) -> TTS
#   and PRINT the final string, so the input is auditable rather than assumed.

# ⛔ RESPELLINGS THE EAR REJECTED — 2026-09-05, on the 18-clip A/B set.
# Kept as a RECORD, never applied. A rejected row is not an untested row: it
# says this SHAPE of respelling was tried on this model and did not work, so
# the next attempt must differ in shape, not merely in spelling.
REJECTED = {
    # ⛔⛔ WITHDRAWN 2026-09-05 BY THE OWNER: «Jesus sounded fine.»
    # THE FOUNDING OBSERVATION WAS AN ARTEFACT OF A DIFFERENT DEFECT. This row
    # was created from John 11:35, where the shipped take reads «Jesus wept.»
    # — correctly — and then re-says «ratcher, jazus wept». The «jasus» is
    # inside a HALLUCINATED APPEND, not in the model's reading of the word.
    # That verse was already queued for repair as `42 10 26,35`, so the repeat
    # screens had it; the pronunciation reading of it was simply wrong.
    # ▶ It would have rewritten 931 verses — by far the largest row in the
    #   table — to fix a defect that does not exist.
    # ⚠⚠ THE LESSON GENERALISES: A CLIP CARRYING ONE DEFECT CANNOT BE USED AS
    #   EVIDENCE FOR ANOTHER. Source every future pronunciation candidate from
    #   a verse that the repeat/append screens PASS, or the same trap recurs.
    "jesus": ("Jeezus", "WITHDRAWN: «jasus» was inside a hallucinated append"),
    # ⛔⛔ THE ROOT FAILED WHILE ITS DERIVED FORMS PASSED. «Kaynanite» and
    # «Kaynanites» are both ear-confirmed right, but bare «Kaynan» is heard
    # «can i an» — wrong in a NEW way, not the old «can-a-yin». So the Kayn-
    # stem is fine and it is the bare word ending in -an that the model
    # mishandles; a suffix protects it. ⚠ This is the direct refutation of
    # reasoning from a root to its derivatives OR BACK: the four Canaan rows
    # needed four verdicts and got four different answers.
    # ▶ Consequence, stated plainly: shipping this lexicon today fixes
    #   «Canaanite»/«Canaanites» and leaves «Canaan» itself mispronounced.
    #   A retry needs a different SHAPE and its own ear test.
    # ✅ SUPERSEDED 2026-09-05 — `Kaynan` stays REJECTED, but the WORD is now
    # FIXED by a different shape; see the `canaan` row in LEXICON. The
    # prediction above («a retry needs a different SHAPE») was tested and held:
    # varying the FINAL SYLLABLE while keeping the ear-validated Kayn- stem
    # produced three passes on the first attempt.
    "canaan__kaynan": ("Kaynan", "REJECTED: heard «can i an» — superseded by Kaynen"),
    # ⚠ NOT CHOSEN is weaker evidence than HEARD WRONG, and the difference
    # matters: the owner picked take 3 (`Naymen`) out of three candidates on
    # II Kings 5:1 and said nothing about how these two sounded. They are
    # recorded so nobody re-proposes them as if they were untried — NOT as a
    # finding that they are bad. If `Naymen` fails its owed spot-check, either
    # of these is a legitimate next test rather than a known dead end.
    "naaman__nayamen": ("Nayamen", "NOT CHOSEN 2026-09-07 (owner picked Naymen); "
                                   "no verdict recorded on this one"),
    "naaman__naymun":  ("Naymun",  "NOT CHOSEN 2026-09-07 (owner picked Naymen); "
                                   "no verdict recorded on this one"),
    # ★ THE HYPHEN IS READ AS A PAUSE. All three double-e stems came back with
    # the two syllables separated by an audible gap — «flee-eeth», not
    # «FLEE-eth». The syllable count was fixed and the word still wrong.
    # ▶ So the defect diagnosis stands; the REMEDY does not. Any retry must
    #   avoid the hyphen (e.g. a doubled vowel or an inserted consonant), and
    #   it needs its own ear test — one shape failing says nothing about another.
    "fleeth__flee_eth": ("flee-eth", "REJECTED: hyphen read as a pause, "
                                     "«flee-eeth». ✅ SUPERSEDED by `fleeith`, "
                                     "owner ear 2026-09-07"),
    # ⚠ NOT A REJECTION — the owner said `fleeith` and `fleeyeth` BOTH sound
    # good. `fleeith` was wired only for consistency with `seeith`. This is the
    # strongest kind of fallback: ear-PASSED but not chosen.
    "fleeth__fleeyeth": ("fleeyeth", "ALSO PASSED the ear 2026-09-07; not "
                                     "wired only because `fleeith` matches "
                                     "`seeith`. A tested fallback, NOT a "
                                     "dead end"),
    # ⛔⛔ DISQUALIFIED ON MEANING: renders as «flyeth» (FLY, not FLEE). It
    # would have changed the sense of 44 verses. Never retry this shape for
    # `fleeth` — but note it is harmless for `freeth`, where `friyeth` won.
    "fleeth__fliyeth": ("fliyeth", "⛔ REJECTED 2026-09-07 — renders as "
                                   "«flyeth», a DIFFERENT WORD. Caught by ASR "
                                   "before it reached an ear"),
    # ⚠ KEY SUFFIXED 2026-09-07: `seeth` now has a LIVE row (`seeyeth`), and a
    # bare "seeth" key in both tables would read as the word itself being
    # rejected. The attempt is what was rejected, not the word.
    "seeth__see_eth": ("see-eth", "REJECTED: hyphen read as a pause, "
                                  "«see-eeth». ✅ SUPERSEDED by `seeith`, "
                                  "owner ear 2026-09-07"),
    # ⚠ NOT CHOSEN is weaker evidence than HEARD WRONG. The owner's first
    # message named this one and he then corrected to `seeith` off the same
    # clip; no verdict on how `seeyeth` actually sounded was ever recorded.
    # If `seeith` fails a later check, this is a legitimate next test rather
    # than a known dead end.
    "seeth__seeyeth": ("seeyeth", "NOT CHOSEN 2026-09-07 (owner corrected to "
                                  "`seeith`); no verdict recorded on this one"),
    "freeth__free_eth": ("free-eth", "REJECTED: hyphen read as a pause, "
                                     "«free-eeth». ✅ SUPERSEDED by `friyeth`, "
                                     "owner ear 2026-09-07"),
    # ⚠ The root and the two shorter derived forms PASSED («Kaynanite»,
    # «Kaynanites»), so this is not the Kayn- spelling failing — the long tail
    # «-itess» is what breaks, heard as «cane an eetus». Length, not stem.
    "canaanitess": ("Kaynanitess", "REJECTED: heard «cane an eetus»"),
    # ⚠ CHANGED NOTHING: «hez ah key ah» is the ORIGINAL defect verbatim, so
    # «-akyah» is read the same as «-ekiah». Contrast `zechariah` below, where
    # the same «-ryah» pattern made it actively worse — the pattern is not
    # merely unhelpful, it is unreliable in both directions.
    "hezekiah": ("Hezakyah", "REJECTED: unchanged, still «Hez-a-KEE-yah»"),
    # ⚠ WORSE THAN THE SHIPPED AUDIO by the owner's ear. A respelling can
    # degrade a word the model already handled acceptably — which is the whole
    # argument for testing every row before it ships.
    "zechariah": ("Zekaryah", "REJECTED: A sounds better than B"),
    # ⛔ REJECTED 2026-09-06 evening, owner's ear on the BEFORE/AFTER pair cut
    # from the real re-rendered II Kings 5:25: «elisha still needs to be redone».
    # The DEFECT IS STILL LIVE AND EAR-CONFIRMED — heard «el-EE-sha», want
    # «ee-LYE-sha» (/ɪˈlaɪʃə/), 55 verses / 13 chapters. Only the respelling is
    # dead.
    # ⚠ The bet was that `y` forces /aɪ/ as it does in `Elijah`. It does not do
    # so before `sh` in this voice, so `Elijah` is NOT a safe model for it.
    # ▶ NEXT ATTEMPT MUST START BY ASKING WHAT HE NOW HEARS, not by guessing.
    # That is how `zechariah`'s target was finally pinned («zee-ka-REE-ah»);
    # guessing produced three dead rows above.
    # ⛔ Do NOT ship any `elisha` respelling until one is heard in a REAL verse.
    "elisha__elysha": ("Elysha", "REJECTED: still wrong; defect live, target "
                                 "«ee-LYE-sha», next spelling needs his ear"),
}


WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def _match_case(src, repl):
    if src.isupper() and len(src) > 1:
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


DEFAULT_SETS = ("ylt",)


def row_sets(entry):
    """Which sets a row is CLEARED for. Rows carry an optional 4th element.

    ⚠⚠ A ROW IS CLEARED FOR THE SET ITS EAR TEST WAS RUN ON, AND NO OTHER.
    Every row here was validated on ylt's voice, so ylt is the default and a
    row reaches another set only by naming it — never by being in the table.
    """
    return tuple(entry[3]) if len(entry) > 3 else DEFAULT_SETS


def rows_for(set_key):
    """-> {word: entry} cleared for this set."""
    return {w: e for w, e in LEXICON.items() if set_key in row_sets(e)}


def apply(text, set_key="ylt"):
    """-> (synthesis_text, [words replaced]). NEVER use on displayed text.

    ⛔⛔ `set_key` DEFAULTS TO ylt ON PURPOSE — never to «every row». Until
    2026-09-07 the whole table was gated by one `lang == "ylt"` test inside
    narrate.py, so widening it to another set was all-or-nothing: turning it on
    for tyn would have applied ALL rows, including `Aebraham`, `Kaynen`,
    `Eelighsha` and `Naymen`, none of which has ever been heard on tyn's voice.
    ▶ This table has already proved VOICE-SENSITIVE — `Aybraham` was judged
      right in one context and wrong in another, and `Aybraham`-right vs
      `Aybram`-wrong was one spelling with opposite verdicts. So «same engine»
      is not clearance; only an ear on THAT set is.
    ⚠ A caller that passes nothing gets ylt's rows, which is the conservative
      direction: a missing argument under-applies rather than silently
      respelling a set nobody tested.
    """
    hits = []
    live = rows_for(set_key)

    def sub(m):
        w = m.group(0)
        # possessive is carried, so «Abraham's» -> «Aybraham's»
        base, tail = w, ""
        for suf in ("'s", "’s", "'", "’"):
            if base.lower().endswith(suf):
                base, tail = base[: -len(suf)], suf
                break
        e = live.get(base.lower())
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
    n_un = len(unvalidated())
    # ⚠⚠ THIS LINE USED TO READ «(all ear-confirmed)» AND THAT OVERSTATED IT.
    # `validated_by` is a single free-text stamp, so the tool knows only
    # stamped/unstamped. It CANNOT distinguish the two clearances that this
    # project treats as different things:
    #   * cleared in a REAL VERSE (whole printed verse + a spot-check in a
    #     chapter the ear was not primed on) — the standard `prophesy` met;
    #   * cleared on a SHORT CARRIER — the standard `Aybraham` passed and then
    #     FAILED in a real verse.
    # CLAUDE.md claimed «the tool says which is which on every run». It did not.
    # Rather than invent a per-row classification there is no evidence for, the
    # line now reports exactly what the data supports and points at the comments.
    print(f"lexicon entries: {len(LEXICON)}  "
          + (f"({n_un} UNVALIDATED — no ear has confirmed them)" if n_un
             else f"({len(LEXICON)} carry a validated_by stamp)")
          + (f"; {len(REJECTED)} rejected respellings on record" if REJECTED else ""))
    if not n_un:
        print("   ⚠ A STAMP IS NOT A STANDARD. This tool cannot tell a row cleared in a")
        print("     REAL VERSE from one cleared on a SHORT CARRIER — `Aybraham` passed a")
        print("     carrier and then failed a real verse. Only the per-row comments in")
        print("     this file record which clearance a row actually got.")
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
