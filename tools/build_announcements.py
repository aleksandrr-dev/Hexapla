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

LIB = Path("C:/Projects/Hexapla-releases/narration/ru_announce_lib")
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


def _spellings(text):
    """Curated respellings FIRST; the literal spelling only as a last resort.

    ⚠ ORDER MATTERS AND IS NOT THE OBVIOUS ONE. A word earns an entry in the
    table because its literal spelling is MISPRONOUNCED, and ASR cannot tell
    the two apart — whisper transcribes «Иоанна» whether the engine says
    «и-а-Ан-на» or spells out «и-о-анна». So trying the literal first would
    verify, be kept, and the respelling would never be reached: the fix would
    silently do nothing. Anything built from a respelling is marked in the
    review index, because here the owner's ear is the only real arbiter.
    """
    out = []
    for src, reps in _SPOKEN_VARIANTS.items():
        if src in text:
            out += [text.replace(src, r) for r in reps]
    return out + [text]

_ASR = None
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
             "--lang", "ru"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
        hello = json.loads(_ASR.stdout.readline())
        assert hello.get("ready"), hello
    _ASR.stdin.write(str(wav_path) + "\n")
    _ASR.stdin.flush()
    return json.loads(_ASR.stdout.readline()).get("text", "")


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
            return narrate.ru_ordinal_fem(n)
        except ValueError:
            return m.group()
    return re.sub(r"\d+", sub, s)


def _norm(s):
    # ⚠ SPELL DIGITS FIRST, THEN FOLD ё. Doing it the other way round silently
    # failed every «...четвёртая» chapter: ru_ordinal_fem re-introduces ё AFTER
    # the fold, and ё (U+0451) is NOT inside the а-я range (U+0430..U+044F), so
    # the character-class strip below ate it — «четвёртая» became «четв ртая»,
    # scoring 0.62 on the tail check. Eight good clips were rejected as
    # truncated before this was spotted; the pattern (only ordinals ending in
    # «четвёртая») is what gave it away.
    s = unicodedata.normalize("NFC", _spell_digits(s)).lower().replace("ё", "е")
    return re.sub(r"[^а-яa-z ]+", " ", s).split()


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


def polish_tail(a, sr, last_word_end_ms, fade_ms=45, margin_ms=60):
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
    lo = int(sr * (last_word_end_ms + margin_ms) / 1000)
    if lo >= len(a) - int(sr * 0.05):
        return a, False                       # nothing meaningful after it
    win = max(1, sr // 100)                   # 10 ms bins
    env = np.array([float(np.sqrt((a[i:i + win] ** 2).mean()))
                    for i in range(0, len(a) - win, win)])
    if not len(env) or env.max() <= 0:
        return a, False
    quiet = 0.10 * env.max()
    lo_bin = min(len(env) - 1, lo // win)
    cand = [i for i in range(lo_bin, len(env)) if env[i] < quiet]
    if not cand:
        return a, False                       # no silence to cut in — leave it
    cut = min(cand) * win + win
    if cut >= len(a):
        return a, False
    out = a[:cut].copy()
    fo = int(sr * fade_ms / 1000)
    if fo and len(out) > fo:
        out[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=out.dtype)
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
        if not narrate.synthesize_cosyvoice3(text, cfg, book_idx, p):
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
        ms = len(a) / sr * 1000
        n_on = onsets(a, sr)
        # bool() because tail_energy returns a numpy scalar, and the resulting
        # numpy.bool_ is NOT JSON-serializable — it crashed the whole rebuild
        # when the draw log was written.
        te = float(tail_energy(a, sr))
        ok = bool(ok and te <= TAIL_MAX)    # words right AND the word finished
        log.append({"draw": k, "ms": round(ms), "heard": heard,
                    "ratio": round(ratio, 2), "tail": round(tail, 2),
                    "cut": round(te, 2), "onsets": n_on, "ok": ok})
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
    # A single-word clip can lose its last phoneme without whisper noticing —
    # its language model restores the word. Duration is the only witness there,
    # so drop any verified draw that is much shorter than its siblings.
    longest = max(c[1] for c in cands)
    cands = [c for c in cands if c[1] >= 0.80 * longest] or cands
    clean = [c for c in cands if c[0] == 1] or cands
    med = float(np.median([c[1] for c in clean]))
    pick = min(clean, key=lambda c: abs(c[1] - med))
    return pick[2], pick[3], log, True


def component_texts():
    """(key, spoken text) for every component the library must hold."""
    bible = narrate.load_bible("ru")
    books, max_ch = {}, 0
    for bi in range(66):
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
        full = narrate.chapter_header_text("ru", bi, 0, len(chs),
                                           book_name=bible[bi]["name"])
        name = full.split(",")[0].strip()
        # Synodal epistle titles are «К Римлянам», «К Евреям» — the asset stores
        # the bare dative («Евреям»), which read aloud sounds like a fragment.
        # Owner asked for the preposition 2026-08-06.
        if bi in _DATIVE_EPISTLES:
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
        full = narrate.chapter_header_text("ru", 18, ch, max_ch)   # Psalms: 150
        out.append((f"ch_{ch+1}", full.split(",", 1)[1].strip()))
    return out


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
    bible = narrate.load_bible("ru")
    solo = {i for i in range(66) if len(bible[i]["chapters"]) == 1}
    items = []
    for key, text in wanted:
        a, sr = clip(key)
        if a is None:
            continue
        bi = int(key.split("_")[1]) if key.startswith("book_") else -1
        if bi >= 0 and bi not in solo and ch1 is not None:
            pause = np.zeros(int(sr * COMMA_MS / 1000), dtype="float32")
            items.append((key, f"{text}, Глава первая",
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
        if m.get("spoken") and m["spoken"] != text:
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
    args = ap.parse_args()

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
    cfg = dict(narrate.LANG_CONFIG["ru"])
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

    bible = narrate.load_bible("ru")
    solo = {i for i in range(66) if len(bible[i]["chapters"]) == 1}
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
