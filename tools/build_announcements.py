# -*- coding: utf-8 -*-
"""Build chapter announcements from a small verified component library.

WHY (owner, 2026-08-06). Announcements were synthesized as one whole utterance
per chapter — «Числа, Глава шестая» — so all 1,192 were independent gambles
against a model that truncates stochastically. Numbers 6 lost «шестая» on every
draw including five re-rolls, and no amount of detector tuning fixed it because
the defect is in the generation, not the measurement.

Assembling instead from components collapses 1,192 gambles into 233 things to
get right: one clip per BOOK NAME (83) and one per «Глава <ordinal>» (150, the
longest book being Psalms). Each is verified ONCE and reused everywhere, so a
bad draw is caught once rather than hiding in some chapter nobody listens to.
Announcements also become identical across books by construction, which they
never were.

⚠⚠ TWO RULES THIS FILE EXISTS TO ENFORCE — both were learned the expensive way.

 1. **THE LIBRARY IS APPEND-ONLY. NOTHING HERE DELETES A COMPONENT.** Three
    separate rebuilds during the 2026-08-05/06 sessions threw away the whole
    directory — including every clip the owner had already listened to and
    approved — to fix a handful of flagged ones, and each time cost him a full
    re-review of 233 clips. A default run builds ONLY what is missing;
    `--rebuild k1,k2` overwrites ONLY the keys named. There is deliberately no
    "clean" or "--all" switch. If a global change ever genuinely needs one,
    move the directory aside by hand so the old clips still exist.

 2. **ACCEPTANCE IS AUTOMATIC, NOT BY EAR.** Every draw is transcribed with
    faster-whisper and rejected unless its words are actually there. The owner
    is not a defect detector; he is the last aesthetic check. Previous rounds
    inverted that — he listened to 233 clips repeatedly to find truncations a
    30-line ASR gate finds for free.

⚠ WHY ASR AND NOT DURATION. The tail-amplitude test that found the original
defect is blind to it once `_trim_and_fade` is in place: the fade drives the
last 40 ms to zero whether or not the words are all there, so a truncated clip
scores identical to a complete one (measured: 1,400 ms and 2,562 ms renders of
the same text both read 0.00). Duration alone was the fallback — "the longest
draw is the complete one" — and it is only a proxy. ASR checks the thing we
actually care about: are the words present. Duration is kept as a secondary
guard for the ONE case ASR is weak at, a single-word clip losing its final
phoneme, where whisper's own language model happily restores «Бытие» from
«Быти».

    python tools/build_announcements.py --components      # build what's missing
    python tools/build_announcements.py --rebuild book_0,ch_63
    python tools/build_announcements.py --reel            # owner review reel
    python tools/build_announcements.py --report
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import soundfile as sf

import narrate

# ⚠⚠ THIS FILE WAS RU-ONLY UNTIL 2026-08-22. It is now parameterised by SET so
# the same verified-component approach can serve any narration set, but the ru
# defaults are preserved EXACTLY — `--set ru` must behave as it always did,
# because its 233-clip library is owner-reviewed and its rules (append-only,
# ASR-gated) were paid for in full re-reviews. A ylt run must never read or
# write ru_announce_lib.
SETS = {
    "ru": {
        "engine": "cosyvoice3",   # synthesize_cosyvoice3(text, cfg, book_idx, wav)
        "asr_lang": "ru",
        "numerals": "ru_ordinal_fem",
        "dative_epistles": True,  # «Евреям» -> «К Евреям»
        "spoken_variants": True,  # the curated Russian respellings
        "spell_out_in_text": False,  # ru MUST be spelled out (no number branch)
        # CosyVoice does not append long hallucinated tails to these short
        # prompts (measured: ru's 217 clips run 600-2560 ms, median 1480), and
        # its library is already built and owner-reviewed. Leave it alone.
        "polish_tail": False,
        "ordinal_book_prefix": False,   # ru titles are already spoken forms
    },
    # ★ PREPPED 2026-08-23, NOT YET ACTIVE. The owner intends to re-render KJV
    # in his own cloned voice ("I would probably replace entire KJV with this
    # voice if it's successful"), gated on the ylt render turning out well.
    # ⚠⚠ THE LIBRARY IS A COPY OF ylt's. Measured that day: with the arabic
    # numerals added to _ROMAN_ORDINAL, 215 of 216 components are IDENTICAL in
    # spoken text between the ylt and en_kjv assets — every chapter numeral
    # (both assets max at Psalms 150, and no book differs in chapter count) and
    # 65 of 66 book names. Only book_65 differs: ylt's asset says «Revelation
    # of John», en_kjv says «Revelation». That one clip must be recorded (or
    # the longer form accepted) before an en splice is honest.
    # ⚠⚠ `--components` FOR THIS SET WILL CRASH UNTIL LANG_CONFIG["en"] IS
    # SWITCHED TO CHATTERBOX, and that is deliberate. LANG_CONFIG["en"] is
    # still kokoro/am_adam (the 22 LibriVox-gap books, 245 of 492 already
    # public), so synthesizing here would quietly produce the WRONG VOICE and
    # mix two voices inside one set - the defect that quarantined 72 Wycliffe
    # chapters. Declaring chatterbox makes it fail loudly instead, because
    # LANG_CONFIG["en"] carries no voice/language_id/cfg_weight.
    # ▶ Switching en to chatterbox means re-rendering all 492 and REPLACING the
    # 245 already live. All-or-nothing, by the same rule.
    "en": {
        "engine": "chatterbox",
        "asr_lang": "en",
        "numerals": "en_cardinal",
        "dative_epistles": False,
        "spoken_variants": True,
        "spell_out_in_text": True,
        "polish_tail": True,
        "ordinal_book_prefix": True,   # en_kjv writes «1 Samuel» - arabic
    },
    "ylt": {
        # ⚠ Chatterbox, and the components are drawn with the TAIL CUTTER OFF
        # (narrate.synthesize_chatterbox cut_tail=False). See that function's
        # docstring: on a chapter header the last aligned word IS the numeral,
        # so the cutter can only eat the word we need.
        "engine": "chatterbox",   # synthesize_chatterbox(text, cfg, wav)
        "asr_lang": "en",
        "numerals": "en_cardinal",
        "dative_epistles": False,
        "spoken_variants": True,
        # English chatterbox reads digits correctly, but spelling them out
        # makes the draw deterministic and lets the ASR gate compare like with
        # like (whisper writes numerals as digits; _spell_digits folds both
        # sides onto words).
        "spell_out_in_text": True,
        # ⚠⚠ REQUIRED FOR CHATTERBOX. Components are drawn with the tail cutter
        # OFF (it would eat the numeral), and chatterbox DOES keep generating
        # past a short prompt — the first ylt draws produced «Isaiah» at 8.0 s
        # and «Song of Solomon» at 12.9 s against a 2.7 s median, all of which
        # passed the ASR gate because the gate asks whether the words are
        # PRESENT, not whether anything follows them. polish_tail cuts just
        # after the last real word and never into speech.
        "polish_tail": True,
        # ⚠ The asset spells numbered books with ROMAN NUMERALS ("I Samuel",
        # "III John"). Chatterbox reads those as letters — the owner heard
        # "eye Samuel" and "eye eye Kings". Expand to the spoken ordinal.
        "ordinal_book_prefix": True,
    },
}

SET = "ru"                        # rebound by _configure()
CFG = SETS["ru"]
LIB = Path("C:/Projects/Hexapla-releases/narration/ru_announce_lib")


def _configure(set_key):
    """Point every module-level path/behaviour at one narration set."""
    global SET, CFG, LIB
    if set_key not in SETS:
        raise SystemExit(f"unknown --set {set_key!r}; known: {sorted(SETS)}")
    SET, CFG = set_key, SETS[set_key]
    LIB = Path(f"C:/Projects/Hexapla-releases/narration/{set_key}_announce_lib")
    return CFG
COMMA_MS = 200       # the pause inside «Бытие, Глава первая»; the reel and the
                     # splice MUST share it, so apply_announcements imports it
MIN_DRAWS = 3        # synthesize this many before judging
MAX_DRAWS = 10       # ... and up to this many until 2 pass the ASR gate
WANT_PASSING = 2

# Books whose Synodal title is a bare dative in the asset — spoken they take
# the preposition: «Евреям» -> «К Евреям». Romans..Hebrews, excluding the
# named-recipient ones that already read naturally.
_DATIVE_EPISTLES = {44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57}
NO_WINDOW = getattr(narrate, "_NO_WINDOW", 0)

# ⚠ PRONUNCIATION RESPELLINGS, tried in order when the literal spelling will
# not verify. CosyVoice has no Russian frontend — it reads graphemes — so some
# Synodal names come out wrong on EVERY draw, which is a mispronunciation, not
# the stochastic truncation the draw loop exists for. «Неемия» collapsed its
# double vowel in all ten draws («не имя», «Ни имя», «Немед»), matching the
# owner's round-1 note that it "sounds like it has an L".
#
# ⚠ THE ASR IS ALWAYS COMPARED AGAINST THE CANONICAL SPELLING, never against
# the respelling. The question is "does the audio sound like the word", so
# feeding the engine «Неэмия» and hearing «Неемия» back is a PASS — while a
# respelling that merely trades one wrong reading for another still fails.
# Keyed by SUBSTRING, so one entry fixes every component containing the word —
# «Иоанна» appears in four book names (От Иоанна, Первое/Второе/Третье Иоанна)
# and was wrong in all of them.
_SPOKEN_VARIANTS = {
    "Неемия": ["Неэмия", "Не-емия", "Нэемия", "Не эмия"],
    # Owner, 2026-08-06: "1 and 2 john are e ooh anna and 3 john is e anna" —
    # the engine spells out И-О-анна instead of reading it with akanye, where
    # the unstressed о is [ɐ]: «и-а-Ан-на». The respellings write that out.
    # ⚠ «Иаанна» WAS TRIED AND IS WRONG — do not put it back. The reasoning
    # (spell the akanye out so a grapheme reader cannot ignore it) was sound,
    # the result was not: the engine read the doubled vowel as a WORD BOUNDARY
    # and said «и Анна» — "Первые и Анна", "Третье – я – Анна". That is worse
    # than the defect it replaced. Marking the stress instead leaves the
    # letters intact and only moves the emphasis.
    "Иоанна": ["Иоа́нна"],
}


# ⚠ ENGLISH RESPELLINGS (2026-08-22). Same mechanism as the Russian table
# above and the same rule: the ASR is ALWAYS compared against the CANONICAL
# spelling, so feeding chatterbox «Jobe» and hearing «Job» back is a PASS.
#
# ⚠⚠ THE ASR GATE CANNOT JUDGE PRONUNCIATION AND MUST NOT BE TRUSTED TO.
# Whisper transcribes «Jobe» and «job» to the same string, so a clip that says
# the WORD "job" instead of the NAME "Jobe" passes the gate cleanly. These
# entries exist because the owner heard the mispronunciations; his ear in the
# review reel is the only real arbiter here, exactly as the Russian table's
# note says. The gate's job is only to catch a respelling that produces a
# different WRONG WORD.
#
# Owner-reported 2026-08-22: Nehemiah, Job, Isaiah, Ezekiel, Obadiah, Nahum
# (book_33) and Habakkuk were all mispronounced.
_SPOKEN_VARIANTS_EN = {
    # ⚠⚠ SINGLE TOKENS ONLY — NO HYPHENS, NO SHOUTED SYLLABLES. Measured
    # 2026-08-22: every hyphenated respelling was read as FRAGMENTS, not as a
    # word. «Nee-uh-MY-uh» came back as "Nia my", «Neh-uh-MY-uh» as "knee my",
    # across 20 draws of Nehemiah. A respelling must still look like one word
    # to a grapheme reader, or it is worse than the spelling it replaces.
    "Nehemiah":  ["Nehemyah", "Neemyah", "Nehhemiah"],
    # The name is "Jobe", not the common noun. ⚠ The ASR gate CANNOT tell these
    # apart — whisper writes both as "Job" — so this one rides entirely on the
    # owner's ear in the reel.
    "Job":       ["Jobe", "Johbe"],
    # Owner still heard Isaiah wrong after the first pair; these are the next
    # candidates. /eye-ZAY-uh/.
    # Round 2 (owner, 2026-08-23): «Izaiah» was STILL wrong. /eye-ZAY-uh/.
    "Isaiah":    ["Eyezayah", "Eyezaya", "Izaiah", "Izayuh"],
    # Owner 2026-08-22 heard "Jerimay" — /jer-uh-MY-uh/. «Jeremyah» FIXED it:
    # owner 2026-08-23 confirms the PRONUNCIATION is correct and the remaining
    # complaint is that the take rises like a QUESTION.
    # ⚠ DO NOT RESPELL THIS ONE. Intonation is a property of the DRAW, not of
    # the grapheme string, and no ASR gate can see it — changing the spelling
    # would only risk losing a pronunciation he has already signed off.
    # The fix is to redraw and let his ear pick.
    "Jeremiah":  ["Jeremyah", "Jerremiah", "Jaremiah"],
    # Round 2: he heard «Ezeekiel» as plain "Ezekiel" and suggested this
    # spelling himself, so it leads.
    # Round 3 (owner, 2026-08-23): «Eezekiel» -> "Eezeekee al" — the final
    # -iel broke into two syllables. «-yul»/«-yel» keeps it as one glide.
    "Ezekiel":   ["Ezeekyul", "Izeekyul", "Ezeekyel", "Eezekiel", "Ezeekiel"],
    # Round 2: «Obadyah» came back as "O bah dee ah" — the stress moved and
    # the word broke apart. Longer single tokens next.
    # Round 3 (owner, 2026-08-23): «Ohbadiyah» -> "oba dee ah". The -di- reads
    # /dee/ and the stress slides off. «-igh-» and «-dye-» are the two English
    # spellings that can ONLY be read /daɪ/. Still single tokens (§2c).
    # Round 4. Round 3's four candidates ALL produced a different WORD, not a
    # different pronunciation — «Obadighah»->"abadiha", «Obadyeuh»->"I bet you",
    # «Ohbadyeah»->"Aberdeer" — so the gate rejected them and fell back to
    # «Ohbadiyah», the very spelling he had just rejected. The defect is narrow:
    # syllable 3 wants /daɪ/ and every spelling so far gives /diː/. "die" is the
    # one English string that cannot be read any other way, so embed it whole.
    "Obadiah":   ["Obadieah", "Ohbadieah", "Ohbadiyah", "Obadyah"],
    # Round 2: NEW — he heard "Zack ah ree ah". Never had an entry before.
    "Zechariah": ["Zekaryah", "Zekarrryah"],
    "Nahum":     ["Nayhum", "Naehum"],
    # Round 3 (owner, 2026-08-23): «Habakuk» -> "habakook" — a single -k lets
    # the final vowel run long. «-uck» is the English spelling that forces the
    # short /ʌk/.
    # Round 4. ⚠ MID-WORD «ck» FRAGMENTS THE WORD — the same failure as a
    # hyphen (§2c), reached by a different route: «Hubackuck» came back
    # "Hu-Bat-Cock" / "You back, cuck" and «Habackuck» "abcock back". Keep the
    # interior single and shorten the FINAL vowel only. The literal leads: its
    # double «kk» is exactly the English device for a short preceding vowel,
    # which is what "habakook" is missing.
    "Habakkuk":  ["Habakkuk", "Habakuck", "Habbakuk", "Habakuk"],
    # ⚠ Hosea is the hard one in BOTH languages. ru's «Осия» came back as
    # «усилия» / «Осень» / «Ай, сия» over ten draws; the English clip
    # exhausted all draws AND tripped the doubling detector (2260 ms, 2 runs).
    "Hosea":     ["Hozaya", "Hohzaya", "Hozeya"],
}

_VARIANT_TABLES = {"ru": None, "ylt": _SPOKEN_VARIANTS_EN}


def _variant_table():
    """The respelling table for the ACTIVE set. ru keeps its own module-level
    _SPOKEN_VARIANTS so nothing about its behaviour moves."""
    t = _VARIANT_TABLES.get(SET)
    return _SPOKEN_VARIANTS if t is None else t


def _spellings(text):
    """Curated respellings FIRST; the literal spelling only as a last resort.

    ⚠ The respelling table is RUSSIAN-SPECIFIC (it exists because CosyVoice
    reads Russian graphemes with no frontend). Sets that do not declare
    `spoken_variants` get the literal spelling only.

    ⚠ ORDER MATTERS AND IS NOT THE OBVIOUS ONE. A word earns an entry in the
    table because its literal spelling is MISPRONOUNCED, and ASR cannot tell
    the two apart — whisper transcribes «Иоанна» whether the engine says
    «и-а-Ан-на» or spells out «и-о-анна». So trying the literal first would
    verify, be kept, and the respelling would never be reached: the fix would
    silently do nothing. Anything built from a respelling is marked in the
    review index, because here the owner's ear is the only real arbiter.
    """
    out = []
    if not CFG["spoken_variants"]:
        return [text]
    for src, reps in _variant_table().items():
        if src in text:
            out += [text.replace(src, r) for r in reps]
    return out + [text]

_ASR = None
_LAST_ASR_WORDS = []
KOKORO_PY = Path("C:/Projects/Hexapla/tools/.kokoro_venv/Scripts/python.exe")


def asr(wav_path):
    """Transcribe one component clip via the persistent worker (see _asr_worker).

    Out-of-process because faster-whisper lives in `.kokoro_venv` and this
    builder runs under `.cosyvoice_venv`; the render venv is left untouched.
    CPU int8 — the GPU belongs to CosyVoice.
    """
    global _ASR
    if _ASR is None:
        _ASR = subprocess.Popen(
            [str(KOKORO_PY), "-u", str(Path(__file__).parent / "_asr_worker.py"),
             "--lang", CFG["asr_lang"]],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        hello = json.loads(_ASR.stdout.readline())
        assert hello.get("ready"), hello
    _ASR.stdin.write(str(wav_path) + "\n")
    _ASR.stdin.flush()
    reply = json.loads(_ASR.stdout.readline())
    # ⚠ The RETURN VALUE IS STILL THE TEXT, so every existing caller is
    # unaffected. Word timestamps are stashed alongside for polish_tail; a
    # tuple return would have broken apply_announcements.verify().
    global _LAST_ASR_WORDS
    _LAST_ASR_WORDS = reply.get("words") or []
    return reply.get("text", "")


def _last_expected_end_ms(expected, words):
    """End time (ms) of the last word of `expected`, as whisper heard it.

    Returns None when it cannot be identified, and the caller MUST then leave
    the audio alone. Guessing a cut point is how you truncate real speech.
    """
    exp = _norm(expected)
    if not exp or not words:
        return None
    target = exp[-1]
    for w in reversed(words):
        got = _norm(w.get("w", ""))
        if got and got[-1] == target:
            return w.get("end")
    return None


def _spell_digits(s):
    """«Глава 151» -> «Глава сто пятьдесят первая».

    ⚠ WITHOUT THIS THE GATE REJECTS EVERY CHAPTER COMPONENT. Whisper writes
    numerals as DIGITS, and the text we asked for is spelled out (it must be —
    CosyVoice has no Russian number branch, see ru_ordinal_fem). Stripping
    digits as punctuation scored «Глава 151» at 0.32 against «Глава сто
    пятьдесят первая», so all ten draws of ch_151 "failed" while being
    perfectly good audio.

    Spelling them back also makes the comparison SHARPER than word-matching:
    a truncated draw is transcribed «глава 150» — the missing «первая» shows
    up as a different NUMBER, which is unmissable, where the word-similarity
    of a long numeral barely moved.
    """
    def sub(m):
        n = int(m.group())
        try:
            if CFG["numerals"] == "ru_ordinal_fem":
                return narrate.ru_ordinal_fem(n)
            # English: cardinal words, matching what chapter_header_text says
            # aloud and what narrate._int_words feeds the aligner elsewhere.
            return narrate._int_words(n) if 0 < n < 1000 else m.group()
        except (ValueError, KeyError):
            return m.group()
    return re.sub(r"\d+", sub, s)


_ORDINAL_FOLD = {"first": "one", "second": "two", "third": "three"}


def _norm(s):
    # ⚠ SPELL DIGITS FIRST, THEN FOLD ё. Doing it the other way round silently
    # failed every «...четвёртая» chapter: ru_ordinal_fem re-introduces ё AFTER
    # the fold, and ё (U+0451) is NOT inside the а-я range (U+0430..U+044F), so
    # the character-class strip below ate it — «четвёртая» became «четв ртая»,
    # scoring 0.62 on the tail check. Eight good clips were rejected as
    # truncated before this was spotted; the pattern (only ordinals ending in
    # «четвёртая») is what gave it away.
    s = unicodedata.normalize("NFC", _spell_digits(s)).lower().replace("ё", "е")
    out = re.sub(r"[^а-яa-z ]+", " ", s).split()
    # ⚠⚠ FOLD THE ENGLISH ORDINAL ONTO ITS CARDINAL, OR EVERY NUMBERED BOOK
    # FAILS THE GATE. spoken_book_name() turns "II Thessalonians" into
    # "Second Thessalonians" (it must — chatterbox reads the roman numeral as
    # letters, "eye eye Kings"). Whisper transcribes that speech as
    # "2 Thessalonians", and _spell_digits above folds the 2 to the CARDINAL
    # "two" — so expected "second …" never matched heard "two …", on the very
    # first token, for all 20+ numbered books.
    # Measured 2026-08-23: book_52 and book_54 went 0/10 with CORRECT audio
    # ("2 Thessalonians, Chapter 1" transcribed cleanly and still scored
    # ok=False). Worse than a false failure — with no draw passing, best_of
    # falls through to the best REJECT ranked by words-present, and a DOUBLED
    # take contains more expected words than a clean one, so the bug actively
    # SELECTED the doubled clip. book_9/13/46/60/61 passed only by luck.
    # Folding both sides onto one token makes them comparable. Safe for the
    # chapter components (English chapter numerals are cardinals, so no
    # ordinal word appears) and for ru (these are English words).
    return [_ORDINAL_FOLD.get(w, w) for w in out]


def words_present(expected, heard, subset=False, strict=False):
    """(ok, ratio, tail_ratio) — are the expected words in the transcript.

    Two checks, because they fail differently:
      * whole-string ratio catches a mangled or substituted reading;
      * the LAST expected word is checked on its own, because truncation —
        the defect this whole file exists for — removes precisely that word
        and a long clip's overall ratio barely notices («Глава сто пятьдесят
        первая» minus «первая» still scores 0.86).
    """
    import difflib
    exp, got = _norm(expected), _norm(heard)
    if not exp:
        return False, 0.0, 0.0
    e, g = " ".join(exp), " ".join(got)
    sm = difflib.SequenceMatcher(None, e, g, autojunk=False)
    if subset:
        # ⚠ COVERAGE, NOT SIMILARITY. When the transcript legitimately runs on
        # past the announcement — reading back a real chapter, where verse 1
        # follows — plain similarity punishes the extra words and would fail
        # every chapter. What we actually want to know is whether the expected
        # words are all IN there, so score how much of `expected` was matched.
        ratio = sum(b.size for b in sm.get_matching_blocks()) / len(e)
    else:
        ratio = sm.ratio()
    tail = exp[-1]
    tail_ratio = max((difflib.SequenceMatcher(None, tail, g).ratio()
                      for g in got), default=0.0)
    # ⚠ BOOK NAMES ARE HELD TO A HIGHER BAR. 0.75 is right for the chapter
    # ordinals, where whisper writes a digit and the spelled-out comparison is
    # near-exact either way. It is far too loose for a short proper noun:
    # «неемия» against a heard «неемьи» scores 0.83 and slipped through, as did
    # «неми». We know exact is achievable — transcribing the EXISTING render
    # returns «НЕЕМИЯ», «Осия», «Исайя» verbatim — so anything less than a
    # near-exact match on a book name is evidence the audio is wrong.
    lo, hi = (0.85, 0.90) if strict else (0.75, 0.75)
    return (ratio >= lo and tail_ratio >= hi), ratio, tail_ratio


# ⚠ TIGHTENED 0.45 -> 0.30 (2026-08-06). Calibration: clips the owner accepted
# score 0.04-0.11, clips he reported as "cut off" score 0.70-1.05. 0.45 was set
# to catch the latter, but a gate leaves the accepted population sitting right
# at its ceiling — after the first repair pass the worst 12 clips were all
# 0.38-0.45, i.e. in the grey zone rather than the good one. He has reported
# this defect twice, so the threshold is set where the good clips actually
# live. The whole distribution is well below it (median 0.13), so this costs
# GPU time, not achievability.
TAIL_MAX = 0.30      # see tail_energy
QUIET_RUN_MS = 80    # how long quiet must HOLD to be silence, not an /s/
PAD_MS = 120         # silence LEFT ON after the cut; see polish_tail


def tail_energy(a, sr):
    """Is the clip still at full speech level when it stops? (higher = cut off)

    ⚠ THE DEFECT ASR CANNOT SEE. Whisper's language model RESTORES a clipped
    final syllable — a “Глава шестидесятая” whose last syllable is chopped
    still transcribes as «Глава 60». The owner heard a run of these in the 60s
    that every text-level check had passed.

    Measure the 120 ms ENDING BEFORE the 40 ms fade, against the clip's own
    speech level. `_trim_and_fade` zeroes the final 40 ms whether or not the
    word finished, which is why the older tail-amplitude test read 0.00 on
    truncated and complete clips alike — but it only trims near-silence, so the
    natural decay of a finished word survives just inside it. Every ordinal
    ends in -ая/-ое, so they all decay alike and a high score really does mean
    "stopped mid-sound" rather than "ends in a hard consonant".

    Calibrated against the owner's report: median across the 151 ordinals is
    0.18, and the ones he flagged score 0.94 / 1.05 / 0.70 while their clean
    neighbours sit at 0.04-0.11.
    """
    fade = int(sr * 0.040)
    w = int(sr * 0.120)
    core = a[:max(1, len(a) - fade)]
    if len(core) < w * 2:
        return 0.0
    win = max(1, sr // 100)
    env = np.array([float(np.sqrt((core[i:i + win] ** 2).mean()))
                    for i in range(0, len(core) - win, win)])
    if not len(env) or env.max() <= 0:
        return 0.0
    speech = env[env > 0.15 * env.max()].mean()
    tail = float(np.sqrt((core[-w:] ** 2).mean()))
    return tail / max(speech, 1e-9)


def polish_tail(a, sr, last_word_end_ms, fade_ms=45, margin_ms=60,
                max_extend_ms=350):
    """Drop anything the engine emitted AFTER the words finished.

    ⚠ THE ACTUAL DEFECT BEHIND "CUT OFF AT THE END" (diagnosed 2026-08-06 from
    the owner's report on the 50s and 60s). These clips are NOT truncated —
    they have JUNK APPENDED. CosyVoice keeps generating past the end of a very
    short formulaic prompt, emitting a stray fragment, repetition or breath
    after a pause; `_trim_and_fade` then cuts that fragment wherever it lands
    and fades it, which is what a listener hears as an abrupt ending.
    Whisper word timestamps prove it: ch_52's last word ends at 1,000 ms in a
    1,560 ms file, with a fresh burst of energy after the gap.

    Redrawing was therefore the wrong instrument — the fix is deterministic.
    Cut just after the last recognized word, at the quietest point in the
    following silence, and re-fade.

    ⚠ NEVER CUT INTO SPEECH. The cut may not fall before the last word's end
    plus a margin, and the chosen point must be genuinely quiet relative to the
    clip; if no such point exists the audio is returned UNCHANGED. Losing the
    end of a word would be far worse than leaving an artifact — the same
    principle as _trim_and_fade's gentle head trim.
    """
    # ⚠⚠ CUT AT THE END OF THE ACOUSTIC VOICED RUN, NOT AT WHISPER'S
    # TIMESTAMP. (Diagnosed 2026-08-23 from the owner's report on the ylt reel:
    # «First King», «Ecclesiaste», «Roman», «1st Corinthian», «chapter
    # fourtee-».) Whisper's word-end timestamp marks where a word is
    # RECOGNISED, not where it stops SOUNDING, and it lands before the final
    # fricative or nasal has finished — so a cut at that timestamp plus a fixed
    # margin lands inside the closing -s / -n. Measured over the 216-clip ylt
    # library built that way: 154 of 216 (71%) scored above TAIL_MAX, median
    # 0.49 against a 0.30 cut-off.
    # The acoustic run CONTAINING the timestamp does know where the sound ends,
    # so extend the floor to the end of that run.
    # ⚠ The extension is CAPPED. A clipped fricative runs ~150 ms and a nasal
    # ~80; anything longer is a hallucinated continuation, which is what this
    # function exists to remove. An uncapped extension would re-admit one
    # whenever the engine ran on without a 250 ms pause to split the run.
    floor_ms = last_word_end_ms + margin_ms
    for r_start, r_end in voiced_runs(a, sr):
        if r_start <= last_word_end_ms <= r_end:
            floor_ms = max(floor_ms,
                           min(r_end, last_word_end_ms + max_extend_ms)
                           + margin_ms)
            break
    lo = int(sr * floor_ms / 1000)
    if lo >= len(a) - int(sr * 0.05):
        return a, False                       # nothing meaningful after it
    win = max(1, sr // 100)                   # 10 ms bins
    env = np.array([float(np.sqrt((a[i:i + win] ** 2).mean()))
                    for i in range(0, len(a) - win, win)])
    if not len(env) or env.max() <= 0:
        return a, False
    quiet = 0.10 * env.max()
    lo_bin = min(len(env) - 1, lo // win)
    # ⚠⚠ ONE QUIET 10 ms BIN IS NOT SILENCE — IT IS OFTEN AN /s/. This is the
    # second half of the 2026-08-23 truncation mechanism. An unvoiced final
    # fricative sits BELOW the 10% threshold (a /s/ runs 10-25 dB under the
    # vowel peak), so the old single-bin test read the «-s» of King*s*,
    # Roman*s*, Corinthian*s*, Ecclesiaste*s* as the silence it was looking for
    # and cut there. Real silence after a word is SUSTAINED; a fricative is
    # 100-150 ms and then the word is over. Requiring the quiet to hold for
    # QUIET_RUN_MS separates them without needing a finer threshold.
    need = max(1, int(QUIET_RUN_MS / 1000 * sr) // win)
    cut = None
    for i in range(lo_bin, len(env)):
        seg = env[i:i + need]
        if len(seg) and (seg < quiet).all():
            # ⚠ KEEP A PAD OF THE SILENCE. Cutting at the instant sound
            # stops makes a clip that IS complete MEASURE as truncated —
            # tail_energy asks "is it still at speech level when it stops", and
            # with no quiet in its 120 ms window a clean clip scored ~0.9 and
            # the guard below rejected a perfectly good trim, handing back the
            # hallucinated tail this function exists to remove (measured on the
            # synthetic hallucination case, 2026-08-23). A clip that ends in
            # PAD_MS of silence is not truncated by construction, and the fade
            # then runs over silence where it is inaudible.
            cut = i * win + win + int(sr * PAD_MS / 1000)
            break
    if cut is None:
        return a, False                       # no silence to cut in — leave it
    if cut >= len(a):
        return a, False
    out = a[:cut].copy()
    fo = int(sr * fade_ms / 1000)
    if fo and len(out) > fo:
        out[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=out.dtype)
    # ⚠⚠ A TRIM MAY NEVER CREATE A TRUNCATION — THIS IS THE GUARD WHOSE
    # ABSENCE LET THE 71% THROUGH. `best_of` measures tail_energy on the RAW
    # draw and must (see the note there), so before 2026-08-23 nothing
    # re-checked the audio AFTER this function had cut it: a clip passed the
    # gate and was then truncated by our own trim, silently.
    # Measuring the FADED `out` is deliberate — that is byte-for-byte what gets
    # written to the library, so whatever this accepts will also pass --audit.
    # If the trim truncates, the untrimmed audio is the lesser evil: a
    # hallucinated tail is audible but complete, a chopped word is not.
    if float(tail_energy(out, sr)) > TAIL_MAX:
        return a, False
    return out, True


def onsets(a, sr):
    """How many times speech STARTS in the first 400 ms.

    ⚠ SELECT, DO NOT TRIM. Two earlier attempts modified the audio and both
    were wrong in opposite directions: cutting at the last quiet moment inside
    400 ms ate the «Б» of «Бытие» (a plosive onset IS burst-closure-vowel), and
    requiring a longer gap then left the pre-plosive the owner heard before
    «Даниил». No threshold separates "artifact + short gap" from "word-initial
    plosive + closure", because they are the same signal.

    What DOES separate them is how many times speech starts. A clean word has
    ONE onset; junk-then-word has two. So generate several draws and keep one
    that starts once — no audio is altered, so nothing can be clipped.
    """
    win = max(1, sr // 100)                       # 10 ms bins
    env = np.array([float(np.sqrt((a[i:i + win] ** 2).mean()))
                    for i in range(0, len(a) - win, win)])
    if len(env) < 8 or env.max() <= 0:
        return 1
    peak = env.max()
    limit = min(len(env), int(0.4 * sr / win))
    hi, lo = 0.20 * peak, 0.04 * peak
    n, armed = 0, True
    for i in range(limit):
        if armed and env[i] > hi:
            n, armed = n + 1, False
        elif not armed and env[i] < lo:
            armed = True
    return max(1, n)


def _synthesize(text, cfg, book_idx, out_wav):
    """Draw one component clip with whatever engine this set uses.

    ⚠⚠ CHATTERBOX IS CALLED WITH cut_tail=False ON PURPOSE. The tail cutter's
    walk starts at the last aligned word's START, and on a chapter header the
    last word IS the numeral — so the only thing it can trim is the word the
    header exists to say. That is the ylt Genesis 14-17 defect the owner
    reported 2026-08-22. Truncation is caught here instead by the ASR gate,
    which tests whether the WORDS ARE PRESENT rather than guessing from a gap.
    """
    if CFG["engine"] == "cosyvoice3":
        return narrate.synthesize_cosyvoice3(text, cfg, book_idx, out_wav)
    if CFG["engine"] == "chatterbox":
        return narrate.synthesize_chatterbox(text, cfg, out_wav, cut_tail=False)
    raise SystemExit(f"no synthesis engine for set {SET!r}")


def best_of_with_variants(text, book_idx, cfg, tmp, tag, context=None,
                          strict=False):
    """Try the literal spelling, then any curated respellings, until one verifies.

    Returns (audio, sr, log, spoken, verified). An unverified best-effort clip
    is still returned — see the note in best_of about never leaving a hole.
    """
    spellings = _spellings(text)
    log_all, fallback = [], None
    for n, spoken in enumerate(spellings):
        a, sr, log, verified = best_of(spoken, book_idx, cfg, tmp,
                                       f"{tag}_v{n}", want=text, context=context,
                                       strict=strict)
        for d in log:
            d["spoken"] = spoken
        log_all += log
        if verified:
            return a, sr, log_all, spoken, True
        if a is not None and fallback is None:
            fallback = (a, sr, spoken)      # keep the LITERAL spelling's take
    if fallback:
        return fallback[0], fallback[1], log_all, fallback[2], False
    return None, None, log_all, None, False


def best_of(text, book_idx, cfg, tmp, tag, want=None, context=None,
            strict=False):
    """Draw until WANT_PASSING clips verify, then pick the best-sounding one.

    Selection among VERIFIED draws (all of which contain the words):
      1. prefer a single onset — no artifact or pre-plosive in front;
      2. among those, take the one nearest the MEDIAN duration. Not the
         longest: with truncation already excluded by ASR, the longest draw is
         just the slowest, and the owner's round-1 complaint about
         «Второзаконие» was that it was oddly PACED, not that it was cut.
    """
    cands, rejects, log = [], [], []
    for k in range(MAX_DRAWS):
        p = Path(tmp) / f"{tag}_{k}.wav"
        if not _synthesize(text, cfg, book_idx, p):
            log.append({"draw": k, "err": "synth failed"})
            continue
        a, sr = sf.read(str(p), dtype="float32")
        a = a.mean(1) if a.ndim > 1 else a
        # ⚠ JUDGE A BOOK NAME IN THE CONTEXT IT SHIPS IN. Whisper-small on a
        # 600 ms isolated proper noun is unreliable — «Осия» came back as
        # «усилия», «Осень», «Ай, сия» over ten draws — but transcribes the
        # SAME word correctly when «Глава первая» follows it (verified against
        # the existing render, which whisper reads as «Осия. Глава первая.»).
        # Judging the isolated clip therefore produced FALSE FAILURES and would
        # have had us "repair" perfectly good audio. What ships is the pair, so
        # the pair is what gets tested.
        if context is not None:
            pause = np.zeros(int(sr * COMMA_MS / 1000), dtype="float32")
            pp = Path(tmp) / f"{tag}_{k}_ctx.wav"
            sf.write(str(pp), (np.concatenate([a, pause, context]) * 32767)
                     .astype(np.int16), sr, subtype="PCM_16")
            heard = asr(pp)
        else:
            heard = asr(p)
        # ⚠ The expected text stays the BOOK NAME ALONE even when the clip is
        # judged in context. Appending «Глава первая» to it would move the
        # tail-word check onto a word supplied by the context clip, so a book
        # name that vanished entirely would still score a passing tail.
        # ⚠ `strict` follows THE KIND OF COMPONENT, not whether context was
        # used. Tying it to context tied it accidentally to chapter count: the
        # single-chapter books (2 John, 3 John, Philemon, Jude, Obadiah) ship
        # their name alone, so they got no context and silently fell back to
        # the loose 0.75 — which is how «Второе и Анна» and «Третье – я – Анна»
        # were accepted as «Иоанна».
        ok, ratio, tail = words_present(want or text, heard,
                                        subset=context is not None,
                                        strict=strict)
        n_on = onsets(a, sr)
        # ⚠⚠ MEASURE tail_energy ON THE RAW DRAW, BEFORE ANY TRIM. It asks "is
        # this clip still at full speech level when it stops", i.e. was the
        # WORD cut off during generation — and that is a property of the draw,
        # not of our post-processing. Trimming first broke its premise: a
        # polish_tail'd clip ends ~60 ms after the last word, so the measure
        # read 0.5-0.8 on perfectly clean audio and REJECTED EVERY DRAW.
        # Measured 2026-08-22: Genesis and Leviticus went 0/10 with ratio=1.0
        # and no repeat, purely from this ordering. Do not move it back.
        # bool() because tail_energy returns a numpy scalar, and numpy.bool_ is
        # not JSON-serializable — it crashed a whole rebuild once.
        te = float(tail_energy(a, sr))
        # ⚠⚠ REJECT A DRAW THAT SAYS IT TWICE. Chatterbox re-utters a short
        # prompt ("Exodus, Exodus Chapter 1" on 4 of 6 draws, measured). The
        # words ARE present so words_present passes it, and polish_tail cannot
        # help — it trims after the LAST expected word, which keeps both
        # copies. Counted against the component's own words, so a book name
        # judged with the «Chapter one» context clip still scores 1.
        rep = repeat_count(want or text, heard)
        # ⚠ ORDER MATTERS THREE WAYS HERE, and each was got wrong once:
        #   1. tail_energy on the RAW draw (above) - it asks whether the word
        #      was cut off during GENERATION.
        #   2. polish_tail next - remove the appended hallucination.
        #   3. looks_doubled on the TRIMMED audio - a hallucinated tail is
        #      itself a separate voiced run, so testing the raw clip would
        #      report a false double and burn all ten draws on a clip that
        #      trimming would have fixed.
        if CFG.get("polish_tail"):
            _end = _last_expected_end_ms(want or text, _LAST_ASR_WORDS)
            if _end is not None:
                a, _trimmed = polish_tail(a, sr, _end)
        # ⚠ BOTH repeat tests run. repeat_count is the cheap transcript one and
        # still catches the identical-transcription case; looks_doubled is the
        # acoustic one that catches everything else (see its docstring).
        dbl = looks_doubled(a, sr, want or text)
        tpr = trailing_partial_repeat(want or text, heard)
        ok = bool(ok and te <= TAIL_MAX and rep <= 1 and not dbl and not tpr)
        ms = len(a) / sr * 1000
        log.append({"draw": k, "ms": round(ms), "heard": heard,
                    "ratio": round(ratio, 2), "tail": round(tail, 2),
                    "cut": round(te, 2), "onsets": n_on, "repeat": rep,
                    "doubled": bool(dbl), "tail_repeat": bool(tpr), "ok": ok})
        if ok:
            cands.append((n_on, ms, a, sr))
        else:
            # Rank the fallbacks by words-right MINUS how badly it was cut, so
            # a best-effort clip is the most complete-sounding draw, not merely
            # the most transcribable one.
            rejects.append((ratio + tail - te, n_on, ms, a, sr))
        if len(cands) >= WANT_PASSING and k + 1 >= MIN_DRAWS:
            break
    if not cands:
        # ⚠ RETURN THE BEST REJECT, DO NOT RETURN NOTHING. Writing no file
        # leaves a HOLE in the library, and a hole means the splice cannot run
        # for that book at all. A best-effort clip that is flagged unverified
        # goes into the review reel where the owner can judge it — which is
        # exactly right for the residue here, names like «Иезекииль» that even
        # the existing render does not transcribe cleanly.
        if not rejects:
            return None, None, log, False
        best = max(rejects, key=lambda r: r[0])
        return best[3], best[4], log, False
    # ⚠⚠ ANCHOR THIS BAND TO THE MEDIAN, NEVER TO THE LONGEST DRAW.
    # This filter exists because a clip can lose its last phoneme without
    # whisper noticing (its language model restores the word). But anchoring it
    # to `longest` is backwards: the longest draw is precisely the one most
    # likely to be carrying EXTRA audio, and anchoring there discards the good
    # draws for being "too short".
    # Measured 2026-08-23, owner-reported on ch_139 and ch_143: ch_139 drew
    # 2910 / 1710 / 1530 ms, all three ASR-verified. The 2910 ms take
    # transcribed «Chapter 139, 39.» — the number, a 640 ms gap, then "thirty
    # nine" AGAIN. `0.80 * longest` = 2328 ms deleted both clean draws and left
    # only the one with the repeat, which then shipped. Same for ch_143
    # («…forty three three»).
    # A band around the MEDIAN rejects both failure directions, and truncation
    # is anyway caught far better by tail_energy on the raw draw than by
    # duration — that is what tail_energy was written for.
    med0 = float(np.median([c[1] for c in cands]))
    cands = [c for c in cands if 0.80 * med0 <= c[1] <= 1.35 * med0] or cands
    clean = [c for c in cands if c[0] == 1] or cands
    med = float(np.median([c[1] for c in clean]))
    pick = min(clean, key=lambda c: abs(c[1] - med))
    return pick[2], pick[3], log, True


# ⚠ BOTH NUMERAL STYLES. Assets are not consistent: the ylt asset writes
# «I Samuel» / «III John» (roman) while en_kjv writes «1 Samuel» / «3 John»
# (arabic). Handling only roman meant a KJV-style asset kept its digit, and the
# component text came out «1 Samuel» — which the engine reads as "one Samuel"
# and which no ylt clip matches, so the 216-clip library could not be reused
# across the two assets. Measured 2026-08-23: 17 of 66 book names differed for
# this reason ALONE, and their AUDIO was already correct ("First Samuel").
_ROMAN_ORDINAL = {"I": "First", "II": "Second", "III": "Third",
                  "1": "First", "2": "Second", "3": "Third"}


def spoken_book_name(name):
    """Turn an asset book name into what the voice should actually SAY.

    ⚠ SHARED ON PURPOSE. apply_announcements.verify() rebuilds the expected
    header independently, and if it did not apply the same transform it would
    compare the spoken clip against the unspoken asset name and fail every
    numbered book. The ru dative rule has exactly this shape; keep them
    together so the two files cannot drift apart.
    """
    if not CFG.get("ordinal_book_prefix"):
        return name
    parts = name.split()
    if parts and parts[0] in _ROMAN_ORDINAL:
        return " ".join([_ROMAN_ORDINAL[parts[0]]] + parts[1:])
    return name


def voiced_runs(a, sr, min_sil_ms=250, floor=0.06):
    """Bursts of speech separated by >= min_sil_ms of quiet.

    ⚠⚠ THIS IS THE REPEAT DETECTOR THAT ACTUALLY WORKS. The transcript-based
    repeat_count() below only fires when whisper renders BOTH copies
    identically, and for a hard proper name it does not: the accepted Nehemiah
    draw transcribed as "Nimia, Nehemiah ..." — two different spellings of the
    same doubled word, so the sequence matched ONCE and the clip passed. Psalms
    failed the other way: whisper simply did not transcribe the second copy.

    A doubled utterance is two bursts with a pause between them, and that is
    measurable without any transcriber. Validated 2026-08-22 against the
    owner's ear on four clips: Nehemiah (he heard a double) = 2 runs; Psalms,
    Genesis, Leviticus (he heard clean) = 1 run each.

    ⚠ min_sil_ms is 250 so an ordinary plosive closure (50-80 ms) never splits
    a word. Raising the floor above ~0.06 starts splitting on breath.
    """
    fr = int(0.02 * sr)
    n = len(a) // fr
    if n < 2:
        return []
    rms = np.array([float(np.sqrt((a[i * fr:(i + 1) * fr] ** 2).mean() + 1e-12))
                    for i in range(n)])
    if rms.max() <= 0:
        return []
    v = rms > max(rms.max() * floor, 1e-4)
    need = max(1, min_sil_ms // 20)
    out, st, gap = [], None, 0
    for i in range(n):
        if v[i]:
            if st is None:
                st = i
            gap = 0
        elif st is not None:
            gap += 1
            if gap >= need:
                out.append((st * 20, (i - gap + 1) * 20))
                st = None
    if st is not None:
        out.append((st * 20, n * 20))
    return out


def looks_doubled(a, sr, text):
    """Did the engine utter this component TWICE?

    ⚠⚠ USE THIS, NOT repeat_count(). The transcript test only fires when
    whisper renders both copies identically, and it usually does not:
      · Nehemiah's accepted draw transcribed "Nimia, Nehemiah ..." - two
        spellings of one doubled word, so the sequence matched ONCE;
      · Psalms' accepted draw transcribed the second copy not at all.
    Both passed the gate and both were caught by the owner's ear.

    MEASURED 2026-08-22 across clips he had judged by ear:
        doubled : Nehemiah 2 runs, Song of Solomon 2 runs
        clean   : Psalms, Genesis, Leviticus, I Chronicles - 1 run EACH
    Chatterbox speaks a short name as ONE continuous burst; a >= 250 ms pause
    inside the clip means it started over.

    ⚠ Spectral similarity between the runs was tried and REJECTED as the
    discriminator: Song of Solomon's two runs score only 0.324 (the repeat is
    partial and differently paced), so a similarity threshold that caught it
    would fire on anything. The RUN COUNT is the signal.

    ⚠ Longer components get one extra run of slack, because a five-word
    «Chapter one hundred forty eight» may legitimately draw breath. Book names
    - which is where every reported defect has been - get none.
    """
    limit = 1 if len(text.split()) <= 3 else 2
    return len(voiced_runs(a, sr)) > limit


def trailing_partial_repeat(expected, heard):
    """Does the transcript say the expected words and then repeat the TAIL of them?

    ⚠⚠ THE DEFECT NEITHER repeat_count() NOR looks_doubled() CATCHES, found
    2026-08-23 from the owner's report on ch_139 and ch_143.
      · repeat_count() misses it because only a SUFFIX repeats, not the whole
        sequence: «Chapter 139, 39» contains «chapter one hundred thirty nine»
        exactly ONCE.
      · looks_doubled() misses it because a component of more than three words
        is allowed two voiced runs (a long numeral may draw breath), and the
        repeat is the second run — «Chapter one hundred thirty nine» is five
        words, so its 640 ms gap plus a trailing "thirty nine" sits inside the
        allowance.
      · tail_energy misses it because the clip ends cleanly AFTER the repeat.
      · polish_tail cannot cut it: _last_expected_end_ms scans the word list in
        REVERSE for the last word matching the final expected word, which lands
        inside the REPEAT, so the trim keeps both.
    The signature is exact and cheap: strip one full occurrence of the expected
    sequence, and ask whether what remains STARTS WITH a non-empty suffix of
    that sequence.
    """
    exp, got = _norm(expected), _norm(heard)
    if not exp or len(got) <= len(exp):
        return False
    for i in range(len(got) - len(exp) + 1):
        if got[i:i + len(exp)] == exp:
            rest = got[i + len(exp):]
            # any non-empty suffix of exp, re-uttered immediately after
            for n in range(1, len(exp) + 1):
                if rest[:n] == exp[len(exp) - n:]:
                    return True
            return False
    return False


def repeat_count(expected, heard):
    """How many times the expected word sequence occurs in the transcript.

    ⚠⚠ THE DEFECT THIS EXISTS FOR: chatterbox re-utters a short prompt, so the
    clip says the book name TWICE ("Deuteronomy ... Deuteronomy"). The owner
    caught it by ear across most of the first library. Nothing else sees it:
    the words ARE present so the ASR gate passes, the clip is only slightly
    long so a duration check is weak, and polish_tail makes it WORSE-looking
    rather than better - it trims after the LAST expected word, which keeps
    both copies and cuts nothing. A repeat has to be detected on its own terms
    and the draw REDRAWN.
    """
    exp, got = _norm(expected), _norm(heard)
    if not exp or len(got) < len(exp):
        return 0
    n, i = 0, 0
    while i <= len(got) - len(exp):
        if got[i:i + len(exp)] == exp:
            n += 1
            i += len(exp)
        else:
            i += 1
    return n


def component_texts():
    """(key, spoken text) for every component the library must hold."""
    bible = narrate.load_bible(SET)
    books, max_ch = {}, 0
    # ⚠⚠ ALL BOOKS, NOT range(66). This was hardcoded to the 66 Protestant
    # books, so NO APOCRYPHA BOOK NAME WAS EVER BUILT — and nothing said so.
    # Found 2026-08-23 when the owner remembered we had not done them.
    # ru and cu each carry 12 deuterocanonical books / 170 chapters (2 Ездры,
    # 3 Ездры, Товит, Иудифь, Премудрость Соломона, Сирах, Варух, Послание
    # Иеремии, Молитва Манассии, 1-3 Маккавейская). Their chapters therefore
    # kept the UNREVIEWED head the renderer synthesized, and
    # `apply_announcements --set ru` silently reported "1192 chapters,
    # 0 errors" — the canon count — while skipping all 170. A skip that
    # reports success is the failure class this file exists to prevent.
    # ⚠ ylt is unaffected (66 books). sv has the slots but they are still
    # empty, so it gains nothing until the Karl XII transcription lands.
    for bi in range(len(bible)):
        chs = bible[bi]["chapters"]
        if not any(any(c) for c in chs):
            continue
        # ⚠ PASS THE ASSET'S OWN NAME. chapter_header_text falls back to the
        # hardcoded BOOK_NAMES_RU when book_name is omitted, and that list is
        # the known-wrong one its own docstring warns about: it uses Protestant
        # versification, so «1 Царств» came out «Первая Самуила» and «3 Царств»
        # came out «Первая Царств» — a different book, announced confidently.
        # The owner caught all four by ear in the component review. The RENDERER
        # always passed the asset name; only this builder did not.
        full = narrate.chapter_header_text(SET, bi, 0, len(chs),
                                           book_name=bible[bi]["name"])
        name = spoken_book_name(full.split(",")[0].strip())
        # Synodal epistle titles are «К Римлянам», «К Евреям» — the asset stores
        # the bare dative («Евреям»), which read aloud sounds like a fragment.
        # Owner asked for the preposition 2026-08-06.
        if CFG["dative_epistles"] and bi in _DATIVE_EPISTLES:
            # ⚠ The preposition follows the ordinal, it does not precede it:
            # «Первое к Коринфянам», not «К первое Коринфянам». Prefixing
            # blindly produced the latter for all eight numbered epistles.
            parts = name.split()
            name = (f"{parts[0]} к {' '.join(parts[1:])}" if len(parts) > 1
                    else f"К {name}")
        books[bi] = name
        max_ch = max(max_ch, len(chs))

    out = [(f"book_{bi}", name) for bi, name in books.items()]
    for ch in range(max_ch):
        full = narrate.chapter_header_text(SET, 18, ch, max_ch)   # Psalms: 150
        text = full.split(",", 1)[1].strip()
        # chapter_header_text leaves the number as a DIGIT for English
        # («Genesis, Chapter 17»). Spell it out so the engine is never asked to
        # normalise and the clip on disk is exactly the words the gate checks.
        if CFG["spell_out_in_text"]:
            text = _spell_digits(text)
        out.append((f"ch_{ch+1}", text))
    return out


def _ch1_label(meta):
    """The 'Chapter one' caption for this set, taken from the ch_1 component
    itself rather than hard-coded, so the reel index reads in the right
    language."""
    return (meta.get("ch_1") or {}).get("text") or "Chapter one"


def build_reel(wanted, meta, tag=""):
    """One ogg of every component, plus an index of timestamps.

    For the owner's aesthetic pass only — correctness is already settled by the
    ASR gate. He replies with keys; those go straight to --rebuild.

    ⚠ BOOK NAMES ARE REVIEWED IN CONTEXT, assembled «Бытие, Глава первая» with
    the very same COMMA_MS pause the splice uses. Reviewing bare clips hides
    the two things most likely to be wrong about an assembled announcement —
    whether the join sounds natural, and whether the two halves match in
    delivery. That mismatch is exactly what round 2 shipped and the owner
    heard as "the New Testament is hurting".
    """
    def clip(key):
        f = LIB / f"{key}.wav"
        if not f.exists():
            return None, None
        a, sr = sf.read(str(f), dtype="float32")
        return (a.mean(1) if a.ndim > 1 else a), sr

    ch1, _ = clip("ch_1")
    # Single-chapter books announce the book alone («К Филимону») — review them
    # the way they ship, not with a «Глава первая» they will never say.
    bible = narrate.load_bible(SET)
    # ⚠ Over ALL books, same reason as component_texts: Послание Иеремии
    # and Молитва Манассии are single-chapter apocrypha and must ship their
    # name alone, exactly like Obadiah and Jude.
    solo = {i for i in range(len(bible)) if len(bible[i]["chapters"]) == 1
            and any(any(c) for c in bible[i]["chapters"])}
    items = []
    for key, text in wanted:
        a, sr = clip(key)
        if a is None:
            continue
        bi = int(key.split("_")[1]) if key.startswith("book_") else -1
        if bi >= 0 and bi not in solo and ch1 is not None:
            pause = np.zeros(int(sr * COMMA_MS / 1000), dtype="float32")
            # ⚠ The LABEL must be in the set's own language. This was
            # hard-coded «Глава первая» and would have printed "Genesis, Глава
            # первая" in an English review index. The AUDIO was always the
            # ch_1 clip, so only the caption was wrong — but the caption is
            # what the owner reads while listening.
            items.append((key, f"{text}, {_ch1_label(meta)}",
                          np.concatenate([a, pause, ch1]), sr))
        else:
            items.append((key, text, a, sr))

    idx, parts, t = [], [], 0.0
    sr_out = None
    for key, text, a, sr in items:
        sr_out = sr_out or sr
        m = meta.get(key, {})
        entry = {"key": key, "text": text,
                 "at": f"{int(t // 60)}:{int(t % 60):02d}"}
        # Surface the two things the owner should listen to hardest: a clip the
        # ASR gate could not confirm, and one produced from a RESPELLING (which
        # can verify while still being a mispronunciation to a native ear).
        if not m.get("verified", True):
            entry["flag"] = "UNVERIFIED"
        # ⚠ COMPARE AGAINST THE COMPONENT'S OWN TEXT, NOT THE REEL LABEL.
        # `text` here has already had the ", Chapter one" context appended for
        # book components, so comparing against it marked EVERY book name as a
        # respelling - 62 of 216 on the first ylt reel, when only 8 were real.
        # A review flag that fires on everything tells the owner nothing, which
        # is worse than no flag: it hides the handful he must actually judge.
        own = m.get("text", text)
        if m.get("spoken") and m["spoken"] != own:
            entry["spoken_as"] = m["spoken"]
        idx.append(entry)
        parts.append(a)
        parts.append(np.zeros(int(sr * 0.7), dtype="float32"))
        t += len(a) / sr + 0.7
    if not parts:
        raise SystemExit("no components in the library yet")
    # ⚠ A partial reel gets its own filename. Writing a round-2 reel over
    # REVIEW_reel.ogg would destroy the record of what the owner reviewed and
    # approved in round 1.
    reel_wav = LIB / f"REVIEW_reel{tag}.wav"
    sf.write(str(reel_wav), (np.concatenate(parts) * 32767).astype(np.int16),
             sr_out, subtype="PCM_16")
    subprocess.run(["ffmpeg", "-y", "-i", str(reel_wav), "-b:a", "48k",
                    "-c:a", "libopus", "-ac", "1",
                    str(LIB / f"REVIEW_reel{tag}.ogg")],
                   capture_output=True, creationflags=NO_WINDOW)
    reel_wav.unlink(missing_ok=True)
    (LIB / f"REVIEW_index{tag}.json").write_text(
        json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"reel: {len(idx)} components, {int(t // 60)}:{int(t % 60):02d} "
          f"-> {LIB / f'REVIEW_reel{tag}.ogg'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--components", action="store_true",
                    help="build every component that is MISSING (never rebuilds)")
    ap.add_argument("--rebuild", help="comma-separated keys to redo, e.g. ch_17,ch_23")
    ap.add_argument("--reel", action="store_true")
    ap.add_argument("--only", help="restrict --reel to these keys, so a review "
                                   "round covers only what was redone")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--audit", action="store_true",
                    help="score every clip on disk for end-truncation; prints "
                         "the --rebuild line for the bad ones only")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--set", default="ru", choices=sorted(SETS),
                    help="narration set (default ru, which behaves exactly as "
                         "before; a non-ru set uses its own library dir)")
    args = ap.parse_args()
    _configure(args.set)

    # ⚠ ONE STYLE FOR EVERY ANNOUNCEMENT. synthesize_cosyvoice3 picks an
    # instruct style from RU_BOOK_STYLES by book index: Job/Isaiah-Malachi/
    # Revelation are "solemn", Ruth/Psalms/Song are "tender", the rest
    # "normal". Book names inherited their own book's style while every
    # «Глава N» was built with book_idx=18 — Psalms, i.e. TENDER. So an
    # assembled header mixed two deliveries («Откровение» solemn + «Глава
    # первая» tender), and the clash was worst across the NT, where the book
    # names are plain "normal". The owner heard it as "the New Testament is
    # hurting". Announcements are chrome, not scripture: they must sound
    # identical everywhere, so the style map is emptied here and everything
    # uses RU_DEFAULT_STYLE.
    cfg = dict(narrate.LANG_CONFIG[SET])
    cfg["book_styles"] = {}

    LIB.mkdir(parents=True, exist_ok=True)
    meta_path = LIB / "components.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    wanted = component_texts()

    if args.report:
        have = [k for k, _ in wanted if (LIB / f"{k}.wav").exists()]
        print(f"library: {len(have)}/{len(wanted)} components present")
        weak = [(k, m) for k, m in meta.items() if not m.get("verified")]
        print(f"unverified (ASR gate never passed): {len(weak)}")
        for k, m in weak:
            print(f"   {k:10} {m.get('text')!r}")
        return

    if args.audit:
        # ⚠ READ-ONLY. This never touches a file; it prints the keys whose
        # audio stops mid-sound so they can be rebuilt individually.
        rows = []
        for key, text in wanted:
            f = LIB / f"{key}.wav"
            if not f.exists():
                continue
            a, sr = sf.read(str(f), dtype="float32")
            a = a.mean(1) if a.ndim > 1 else a
            rows.append((tail_energy(a, sr), key, text))
        rows.sort(reverse=True)
        bad = [r for r in rows if r[0] > TAIL_MAX]
        med = float(np.median([r[0] for r in rows])) if rows else 0.0
        print(f"{len(rows)} clips scored, median {med:.2f}, "
              f"{len(bad)} above the {TAIL_MAX} cut-off threshold\n")
        for te, key, text in bad:
            print(f"   {key:10} {text!r:30} {te:.2f}")
        if bad:
            print("\n--rebuild " + ",".join(k for _, k, _ in bad))
        return

    if args.reel:
        if args.only:
            keep = {k.strip() for k in args.only.split(",") if k.strip()}
            unknown = keep - {k for k, _ in wanted}
            if unknown:
                raise SystemExit(f"unknown key(s): {sorted(unknown)}")
            wanted = [(k, t) for k, t in wanted if k in keep]
        build_reel(wanted, meta, tag="_round2" if args.only else "")
        return

    if args.rebuild:
        want = {k.strip() for k in args.rebuild.split(",") if k.strip()}
        todo = [(k, t) for k, t in wanted if k in want]
        missing = want - {k for k, _ in todo}
        if missing:
            raise SystemExit(f"unknown component(s): {sorted(missing)}")
    else:
        todo = [(k, t) for k, t in wanted if not (LIB / f"{k}.wav").exists()]
    if args.limit:
        todo = todo[:args.limit]
    # ch_1 is the context every book name is judged against, so it must exist
    # before any of them are drawn.
    todo.sort(key=lambda kt: kt[0] != "ch_1")
    print(f"{len(todo)} components to build ({len(wanted)} total, "
          f"{sum(1 for k, _ in wanted if (LIB / f'{k}.wav').exists())} already present)",
          flush=True)

    bible = narrate.load_bible(SET)
    # ⚠ Over ALL books, same reason as component_texts: Послание Иеремии
    # and Молитва Манассии are single-chapter apocrypha and must ship their
    # name alone, exactly like Obadiah and Jude.
    solo = {i for i in range(len(bible)) if len(bible[i]["chapters"]) == 1
            and any(any(c) for c in bible[i]["chapters"])}
    failed = []
    with tempfile.TemporaryDirectory() as tmp:
        for n, (key, text) in enumerate(todo, 1):
            bi = int(key.split("_")[1]) if key.startswith("book_") else 18
            # Book names are judged with «Глава первая» after them, as they
            # ship — except the single-chapter books, which ship alone.
            ctx = None
            if key.startswith("book_") and bi not in solo and (LIB / "ch_1.wav").exists():
                c, _ = sf.read(str(LIB / "ch_1.wav"), dtype="float32")
                ctx = c.mean(1) if c.ndim > 1 else c
            a, sr, log, spoken, verified = best_of_with_variants(
                text, bi, cfg, tmp, key, context=ctx,
                strict=key.startswith("book_"))
            if a is None:
                # ⚠ Leave whatever is already on disk ALONE and move on.
                failed.append(key)
                print(f"  [{n}/{len(todo)}] {key:10} {text!r:28} NO AUDIO "
                      f"after {len(log)} draws", flush=True)
                meta[key] = {"text": text, "verified": False, "draws": log}
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
                continue
            if not verified:
                failed.append(key)
            # ⚠ SUPERSEDED CLIPS ARE ARCHIVED, NEVER LOST. A rebuild can land
            # while the owner is midway through reviewing the library, and the
            # replacement is not guaranteed better than what it replaced. The
            # old take moves to superseded/ so any version can be brought back
            # by copying one file. Nothing in this tool removes audio.
            dst = LIB / f"{key}.wav"
            if dst.exists():
                arch = LIB / "superseded"
                arch.mkdir(exist_ok=True)
                n_prev = len(list(arch.glob(f"{key}__*.wav")))
                dst.replace(arch / f"{key}__{n_prev + 1}.wav")
            sf.write(str(dst), (a * 32767).astype(np.int16), sr,
                     subtype="PCM_16")
            meta[key] = {"text": text, "verified": verified, "spoken": spoken,
                         "kept_ms": round(len(a) / sr * 1000), "sr": sr,
                         "draws": log}
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
            print(f"  [{n}/{len(todo)}] {key:10} {text!r:28} "
                  f"kept {meta[key]['kept_ms']:5} ms "
                  f"({sum(1 for d in log if d.get('ok'))}/{len(log)} verified)"
                  f"{'' if verified else '  <-- UNVERIFIED, needs an ear'}",
                  flush=True)

    print(f"\nlibrary at {LIB}")
    if failed:
        print(f"⚠ {len(failed)} unverified (best-effort audio written, flagged "
              f"in components.json — judge these in the reel):\n   "
              f"--rebuild {','.join(failed)}")


if __name__ == "__main__":
    main()
