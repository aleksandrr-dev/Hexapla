# -*- coding: utf-8 -*-
"""Per-verse TTS narration pipeline for Bible translations.

Generates per-chapter audio files from Bible translation JSON assets, with
per-verse timing offsets for in-app verse highlighting.

Usage:
  python narrate.py --lang en --book 42 --chapter 0    # John 1, English
  python narrate.py --lang en --book 42                # all of John
  python narrate.py --lang en                          # all 22 gap books
  python narrate.py --lang ru --book 42                # Synodal John

Supported languages:
  en:  KJV (Kokoro am_adam, only LibriVox gap books by default)
  wbt: Webster 1833 (Kokoro am_adam)
  gnv: Geneva 1599 (Kokoro am_adam, with spelling normalization)
  tyn: Tyndale 1525/1531 (Kokoro am_adam, with spelling normalization)
  wyc: Wycliffe ~1395 (Kokoro am_adam, with spelling normalization)
  ru:  Synodal (Bark v1 ru_speaker_2)

Options:
  --book BOOK       Book index (0-65, optional: all if omitted)
  --chapter CH      Chapter index (0-based, optional: all if omitted)
  --force           Overwrite existing output files
  --dry-run         Print what would be generated, don't synthesize
  --all-books       For 'en', generate ALL 66 books (not just gap books)
"""
import argparse
import io
import json
import logging
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import soundfile as sf

# Every subprocess.run() below launches a console-subsystem exe (python.exe,
# ffmpeg.exe). Without this, Windows pops a NEW console window for each one
# even though the parent (this script) may itself be running hidden under the
# render supervisor — the parent's window style does not propagate to
# children spawned this way. This fires once per verse for kokoro/ffmpeg, so
# an unsuppressed flash here is far more disruptive than the supervisor's
# occasional recycle. No-op on non-Windows.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
# ⚠ HEXAPLA_NARRATION_OUT redirects the whole narration tree, for A/B renders
# that must NOT touch shipped audio. Default is unchanged. Note cfg["voice"] is
# built from OUTPUT below, so a redirected run needs the reference wav copied
# into the scratch tree — the chatterbox preflight fails loudly if it is absent.
OUTPUT = Path(os.environ.get("HEXAPLA_NARRATION_OUT",
                             "C:/Projects/Hexapla-releases/narration"))

# ★ THE VERSE GATE (owner decision 2026-09-03) — see synthesize_verse_gated.
# Up to the sv apocrypha render, the ONLY in-flight guard was a retry on
# Chatterbox's own token_repetition warning. Measured on Tobit (297 verses): it
# stayed raised on 23.9 % of verses, cost ~53 % of the render in re-syntheses,
# and tracked the audible defect NOT AT ALL (qa_selfrepeat 0/40 on the flagged
# verses, 0/40 on controls) — while ylt shipped a re-spoken tail in 152 of
# 1,189 chapters that the flag never saw. Every verse is now judged by the
# screens that were validated BY EAR (tools/qa_gate.py) and re-drawn only if
# one fires. The token flag is still RECORDED in .eos.json (data for the
# token-id lead); it no longer spends GPU.
#   HEXAPLA_NO_GATE=1              render without the gate. A/B ONLY — a set
#                                  rendered this way has no .qa.json and must
#                                  be swept the slow way.
#   HEXAPLA_RETRY_ON_TOKEN_FLAG=1  the pre-2026-09-03 trigger, IN ADDITION.
#   HEXAPLA_GATE_TAIL_PEAK=0.75    also fail a verse whose post-word tail peaks
#                                  at/above this. RECORD-ONLY until calibrated
#                                  (qa_gate.py docstring says against what).
#   HEXAPLA_NO_REP_RETRY           retired 2026-09-03 (its A/B is in the
#                                  2026-09-02 handoff §3c); now a no-op.
_GATE_OFF = bool(os.environ.get("HEXAPLA_NO_GATE"))
_RETRY_ON_TOKEN_FLAG = bool(os.environ.get("HEXAPLA_RETRY_ON_TOKEN_FLAG"))
_GATE_TAIL_PEAK = (float(os.environ["HEXAPLA_GATE_TAIL_PEAK"])
                   if os.environ.get("HEXAPLA_GATE_TAIL_PEAK") else None)
GATE_ATTEMPTS = 3
# ASR language per set. ⚠ THIS IS WHISPER (faster-whisper in .kokoro_venv),
# NOT KOKORO. cu has no whisper model; 'ru' is the nearest, and only the
# text-free self-repeat screen is meaningful on it.
ASR_LANG = {"en": "en", "ylt": "en", "tyn": "en", "wbt": "en", "gnv": "en",
            "wyc": "en", "sv": "sv", "ru": "ru", "cu": "ru"}

# ⚠ Do NOT invoke .kokoro_venv's own Scripts/python.exe. On this machine it is
# a launcher that internally re-execs into a SECOND, separate OS process (the
# base interpreter) rather than running in place — confirmed by watching
# conhost.exe (Windows' console-window host) spawn as a child of that inner
# process even when the outer subprocess.run() call is given
# creationflags=CREATE_NO_WINDOW. That flag only covers the process WE
# create; it does not propagate through the launcher's own internal re-exec,
# so every kokoro/bark call was still popping a console. Fix: read the venv's
# own pyvenv.cfg (the same file `venv` itself writes) to find the REAL base
# interpreter, invoke that ONE process directly, and hand it PYTHONPATH so it
# sees the venv's installed packages (kokoro, torch, soundfile, ...) without
# needing the launcher hop at all.
def _resolve_kokoro_python():
    venv_dir = HERE / ".kokoro_venv"
    cfg = venv_dir / "pyvenv.cfg"
    home = None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("home"):
            home = line.split("=", 1)[1].strip()
            break
    base_python = str(Path(home) / "python.exe") if home else str(venv_dir / "Scripts" / "python.exe")
    site_packages = str(venv_dir / "Lib" / "site-packages")
    return base_python, site_packages


KOKORO_PYTHON, KOKORO_SITE_PACKAGES = _resolve_kokoro_python()

LIBRIVOX_GAP_BOOKS = [
    20, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38,
    42, 50, 51, 52, 53, 54, 55, 56, 59, 60,
]

# --- Russian narration styles (CosyVoice3 inference_instruct2) -------------
#
# One voice, three deliveries. The reference recording sets WHO is speaking;
# the instruction sets HOW. This split matters: measured 2026-07-15, the
# owner's three separate takes differed by only 0.7-1.2 semitones and
# CosyVoice normalized that away entirely — take2 was recorded DEEPER than
# take1 but cloned back HIGHER (88.4Hz -> 99.7Hz). The reference is a speaker
# embedding, not a performance. Instructions, by contrast, land hard.
#
# ⚠⚠ THE INSTRUCTION MUST BE IN ENGLISH, NOT RUSSIAN. Fixed 2026-07-20 after
# the owner heard «Прочитай очень медленно…» SPOKEN ALOUD in the finished
# audio. Cause: frontend_instruct2() passes the instruction as the zero-shot
# PROMPT TEXT (cosyvoice/cli/frontend.py:210) — it enters the LLM's text
# stream with only <|endofprompt|> dividing it from the verse, and when
# instruction and verse are the SAME LANGUAGE the model cannot hold that
# boundary and reads the instruction out (often INSTEAD of the verse).
# Measured A/B, 60 samples over header/short/long texts, ASR-verified:
#   solemn_ru 12/12 leaked   tender_ru 12/12 leaked
#   solemn_en  0/12          tender_en  0/12          normal(en) 0/12
# Damage: 344 chapters = all 9 instruct-style books rendered before the fix
# (research/ru_narration_leak_scan.md). Scan with tools/scan_narration_leaks.py
# after any future instruct-engine render — duration heuristics CANNOT catch
# this (a leak can replace the utterance without lengthening it).
#
# Style strength, same A/B, leak-free English instructions vs normal:
#   short 1.37x slower (solemn) / 1.20x (tender)
#   long  1.25x        (solemn) / 1.12x (tender)
# The old comment here claimed 2.24x/1.82x — those figures were measured on
# the LEAKING Russian instructions, so most of that "slowdown" was the model
# reciting the instruction, not style. The real effect is gentler; owner ear
# check pending on whether solemn is still solemn enough.
RU_STYLES = {
    "normal": "You are a helpful assistant.<|endofprompt|>",
    "solemn": "You are a helpful assistant. Read this very slowly, in a "
              "low and solemn voice.<|endofprompt|>",
    "tender": "You are a helpful assistant. Read this softly and tenderly, "
              "like poetry.<|endofprompt|>",
}

# Owner's assignment (2026-07-15): solemn for Job, Lamentations, the prophets;
# tender for Song of Songs, Psalms, Ruth; normal for everything else.
RU_BOOK_STYLES = {}
for _b in [17] + list(range(22, 39)) + [65]:
    # Job; Isaiah..Malachi (incl. Lamentations 24); Revelation.
    RU_BOOK_STYLES[_b] = "solemn"
for _b in [7, 18, 21]:                                     # Ruth, Psalms, Song of Songs
    RU_BOOK_STYLES[_b] = "tender"
# Jonah is the one narrative in the Book of the Twelve — a story ABOUT a
# prophet, not a collection of his oracles — so it reads normal despite sitting
# in the prophets range. Solemn (2.24x) would drag across four chapters of
# flight, sulking and a gourd. Its one weighty passage is the ch.2 prayer, and
# this map is book-level.
RU_BOOK_STYLES[31] = "normal"
del _b
# Revelation reads solemn: it calls itself prophecy (Rev 1:3) and is Daniel's
# genre-pair — Daniel(26) solemn with Revelation normal would be inconsistent.
# Both calls delegated to Claude by the owner 2026-07-15; flip either freely.

# --- Apocrypha (indexes 66+; owner confirmed 2026-07-15 these are covered) ---
# ru_synodal.json is 83 books, not 66. Same genre logic as the canon, with the
# owner's own map as the anchor: Proverbs and Ecclesiastes read NORMAL, so
# wisdom literature is not automatically tender — tender is for lyric/devotional
# poetry (Psalms, Song of Songs) and Ruth.
for _b in [
    67,   # 3 Ездры — NOT the historical one. Slavonic "3 Ezra" = Latin 4 Ezra
          # (2 Esdras): eagle visions, judgment. Apocalyptic, so it pairs with
          # Daniel and Revelation, both solemn.
    72,   # Варух — prophetic
    73,   # Послание Иеремии — prophetic (anti-idolatry oracle)
    74,   # Молитва Манассии — penitential prayer; contrition sits with
          # Lamentations (solemn), not with love poetry.
]:
    RU_BOOK_STYLES[_b] = "solemn"
del _b
# NORMAL by omission: 66 (2 Ездры — the HISTORICAL Ezra, temple rebuilding),
# 68 Товит, 69 Иудифь, 75/76/77 Maccabees (all narrative); 70 Премудрость
# Соломона and 71 Сирах (wisdom lit, matching Proverbs).
# ⚠ Debatable, say the word: Премудрость Соломона(70) is more lyrical than
# Proverbs and could read tender; Молитва Манассии(74) could go either way.
# Empty in the asset, so they render nothing regardless: 78-82.
RU_DEFAULT_STYLE = "normal"

LANG_CONFIG = {
    "en": {
        "asset": "en_kjv.json",
        "engine": "kokoro",
        "voice": "am_adam",
        "strip_notes": True,
        "default_books": LIBRIVOX_GAP_BOOKS,
        "normalizer": None,
    },
    "wbt": {
        "asset": "en_webster.json",
        "engine": "kokoro",
        "voice": "am_adam",
        "strip_notes": True,
        "default_books": None,
        "normalizer": None,
    },
    "gnv": {
        "asset": "en_geneva.json",
        "engine": "kokoro",
        "voice": "am_adam",
        "strip_notes": True,
        "default_books": None,
        "normalizer": "geneva",
    },
    # ── ENGLISH CLONED VOICE (owner's own reading, 2026-08-02) ──────────────
    # Owner picked variant E of the sweep: cfg_weight 0.5, exaggeration 1.0.
    #
    # ⚠ HONEST RESULT, so nobody re-runs this hoping for more: the
    # `exaggeration` knob is effectively INAUDIBLE on this voice. Two rounds,
    # 0.4 / 0.5 / 0.7 / 1.0 / 1.2 / 1.5 — nearly 4x — over both a calm passage
    # (Ps 23) and a declamatory one (1 Cor 15:54-57, "O death, where is thy
    # sting?"), and the owner heard "all about the same" every time. Looser
    # adherence (cfg 0.3) did not unlock it either. The parameters DO affect
    # pacing (exag 1.5 ran 21.9s vs 23.2s at 0.5) but not perceived emotion.
    # So this buys the owner's OWN VOICE in place of a stock synthetic one —
    # NOT the expressive range CosyVoice3 gives Russian. Do not promise
    # expression in any listing copy.
    #
    # ⚠ Chatterbox embeds Resemble's inaudible Perth watermark. upload_
    # narration.py discloses it automatically for sets flagged "watermark".
    # The set must also be flagged "cloned" so the description does not claim
    # "no narrator was involved" — a real person's voice is the source.
    # ⚠ RUN UNDER tools\.chatterbox_venv (in-process model). GPU: ~4 GB, must
    # NOT share the 8 GB card with a live CosyVoice render.
    "tyn": {
        "asset": "en_tyndale.json",
        "engine": "chatterbox",
        # Trimmed from the owner's eng.wav (KJV portion, 16.7s), levelled to
        # match _sv_ref_norm.wav: -1.0 dB peak, ~0.33s lead-in so the opening
        # is not garbled the way the raw Swedish take was.
        "voice": str(OUTPUT / "_en_ref_kjv.wav"),
        "language_id": "en",
        "cfg_weight": 0.5,
        "exaggeration": 1.0,
        "strip_notes": True,
        "default_books": None,
        "normalizer": "tyndale",
        # Previous config, kept for a quick revert: engine "kokoro",
        # voice "am_adam", no language_id/cfg_weight/exaggeration.
    },
    # ★ SWITCHED TO THE OWNER'S VOICE 2026-08-16, on his explicit instruction
    # ("use my voice for wycliffe, Adam for kjv"). This deliberately overrides
    # the hold recorded below — he was the gate on it, and he lifted it.
    #   PREVIOUS (kept for a quick revert): engine "kokoro", voice "am_adam",
    #   no language_id/cfg_weight/exaggeration.
    #   THE HOLD IT REPLACES: "STILL kokoro ON PURPOSE. Tyndale (451 ch,
    #   ~2.7 days) is the trial set; Wycliffe is 1197 chapters / ~a week, so it
    #   waits until the owner has heard a real Tyndale chapter rather than a
    #   25-second sample."
    # ⚠ `_en_ref_wyc.wav`, NOT the KJV reference — the owner recorded a SECOND
    # take reading WYCLIFFE, and a reader already in Middle English cadence is
    # the better prompt for this text. Both are trimmed from his eng.wav.
    # ⚠⚠ THIS MAKES wyc A **GPU** RENDER (chatterbox, ~4 GB, in-process model):
    #   · it must NOT share the 8 GB card with a live CosyVoice render;
    #   · its supervisor now needs the 75-minute RECYCLE, not revive-only —
    #     in-process engines decay with process age, kokoro ones do not;
    #   · it moves from .kokoro_venv to .chatterbox_venv in the supervisor.
    # ⚠ The 72 chapters rendered in am_adam before the switch were QUARANTINED
    #   to narration/wyc_quarantine_am_adam — mixing voices inside one
    #   translation is the defect this avoids. Do not --force; skip-existing is
    #   what keeps the job resumable across the recycle.
    "wyc": {
        "asset": "enm_wycliffe.json",
        # ★ 2026-08-16 — KOKORO + IPA, NOT chatterbox. The owner wants Wycliffe
        # to sound like 1395, and chatterbox takes TEXT ONLY (verified: its
        # generate() has no phoneme argument), so his cloned voice and accurate
        # Middle English are mutually exclusive. He chose accuracy here and his
        # own voice for Tyndale. See docs/NARRATION.md "English pronunciation
        # policy" and tools/me_phonemes.py.
        "engine": "kokoro",
        "voice": "am_adam",
        "ipa": "middle_english",   # -> me_phonemes.to_ipa, bypasses G2P
        "strip_notes": False,
        "default_books": None,
        "normalizer": "wycliffe",
    },
    # ★ SWITCHED TO THE OWNER'S VOICE 2026-08-21, on his pick from the round-2
    # ear test ("the voice at ref_K_dfneq_long sounds great, we can use that").
    #   PREVIOUS (kept for a quick revert): engine "kokoro", voice "am_adam",
    #   no language_id/cfg_weight/exaggeration.
    # ⚠ THE REFERENCE IS DENOISED, and that is not cosmetic. It is cut from a
    # recording made beside a bonfire — speech -28.7 dBFS over a continuous
    # -43.7 dBFS bed, ~15 dB SNR, with no clean stretch anywhere in the two
    # minutes to cut from. Cloning a raw cut puts that bed into EVERY rendered
    # verse: measured over three seeds, a raw reference yields a clone floor
    # 35.9 dB below its own speech (audible on headphones) against 54.7 dB for
    # the scrubbed one. Mixing 20-35% of the original back in - tried, on the
    # theory that it protects timbre - restores the fire and buys 3 dB. Do not
    # re-try it.
    #   PIPELINE: DeepFilterNet3, then a MEASURED corrective EQ (+3.8 dB at
    #   3-6 kHz, +4.0 at 6-12 kHz, +6 capped at 12-16.5 kHz, flat below,
    #   anchored to the 300 Hz-3 kHz core), because the scrub's cost is all at
    #   the top and a scrubbed-flat clip stopped sounding like him. Full
    #   record, scripts and the rejected variants:
    #   narration/_ylt_voice_candidates/README.md.
    # ⚠ Its RMS is -25.5 dB against _en_ref_kjv.wav's -19.8 - that is a crest
    # factor of 24 dB vs 19 dB, i.e. a more dynamic reading, NOT a level error.
    # Do not "fix" it with compression; Chatterbox clones whatever dynamics the
    # reference has.
    # ⚠⚠ THIS MAKES ylt A **GPU** RENDER (chatterbox, ~4 GB, in-process model),
    # with the same consequences recorded for wyc above:
    #   . it must NOT share the 8 GB card with a live CosyVoice render;
    #   . its supervisor needs the 75-minute RECYCLE, not revive-only -
    #     in-process engines decay with process age, kokoro ones do not;
    #   . it runs from .chatterbox_venv, not .kokoro_venv.
    # Nothing was rendered in am_adam before the switch, so unlike wyc there is
    # no quarantine to do - but if that ever changes, quarantine rather than
    # mix voices inside one translation.
    "ylt": {
        "asset": "en_ylt.json",
        "engine": "chatterbox",
        "voice": str(OUTPUT / "_en_ref_ylt.wav"),
        "language_id": "en",
        "cfg_weight": 0.5,
        "exaggeration": 1.0,
        "strip_notes": True,
        "default_books": None,
        # Punctuation only - Young's spelling is modern. See archaic_english.
        "normalizer": "ylt",
    },
    "ru": {
        "asset": "ru_synodal.json",
        "engine": "cosyvoice3",
        # The owner's own voice (recorded 2026-07-15). CosyVoice3 zero-shot
        # clones the speaker from this clip; no transcript is needed because
        # inference_instruct2() takes no prompt_text.
        "voice": str(OUTPUT / "myvoice_take1.wav"),
        "styles": RU_STYLES,
        "book_styles": RU_BOOK_STYLES,
        "strip_notes": False,
        "default_books": None,
        # ⚠ DISABLED 2026-07-15 — ru_stress.py CORRUPTS THE TEXT. Audited over
        # all 37,098 Synodal verses: of 197 entries, 30 do not add a stress
        # mark but REWRITE THE WORD, corrupting 1,029 verses. Strip the
        # combining acute (U+0301) from the output and it still differs from
        # the input — that is the test, and it fails:
        #   Вирсавия  -> Виргавия   (Beersheba -> a non-word; Gen 21:31,32,33...)
        #   Христа    -> Христоса   (invented non-word for Christ)
        #   Ирод      -> Ириод      Михей -> Михай    Иосиф -> Иосифа (case!)
        #   Нерон     -> НерО́н      (Latin capital O)
        #   8 entries inject 'і' U+0456 (Ukrainian, not Russian)
        # The plan's "⚠ GATE (quality): owner/native spot-check" on this table
        # was never satisfied. DO NOT re-enable until it is rebuilt and audited
        # (tools/audit_ru_stress.py-style: stripping U+0301 must be a no-op).
        # RESOLVED 2026-07-15: the owner (native speaker) judged the unstressed
        # Matthew 1 genealogy — ~40 names back to back — and the stress was
        # correct. CosyVoice3 handles Russian stress natively; it is LLM-based,
        # unlike the Piper/Bark engines the table was written for. The whole
        # ru_stress task is therefore MOOT, not merely deferred.
        "normalizer": "ru_variants",
    },
    "sv": {
        "asset": "sv_karlxii.json",
        "engine": "chatterbox",
        # The Swedish friend's voice (take 1, 2026-07-20; consent recorded
        # with the takes). Reference is the normalized+padded version —
        # the raw take's low level (peak 0.36) and abrupt 0.2s onset caused
        # accent drift and a garbled opening in the first ear test.
        # Owner + friend picked variant C of the parameter sweep 2026-07-20:
        # cfg_weight 0.3 (adherence to HIS voice — default 0.5 genericized
        # the accent, "sounds like Västergötland"), exaggeration 0.4.
        # ⚠ RUN UNDER tools\.chatterbox_venv\Scripts\python.exe (in-process
        # model, like cosyvoice under its venv). GPU: Chatterbox (~4 GB)
        # must NOT share the 8 GB GPU with a live CosyVoice render — set
        # CHATTERBOX_DEVICE=cpu to test, or wait for the GPU to free.
        # Disclosure note: Chatterbox embeds Resemble's inaudible Perth
        # watermark — mention alongside the AI-voice notice on upload.
        "voice": str(OUTPUT / "_sv_ref_norm.wav"),
        "language_id": "sv",
        "cfg_weight": 0.3,
        "exaggeration": 0.4,
        "strip_notes": False,
        "default_books": None,
        "normalizer": None,
    },
    "cu": {
        "asset": "cu_elizabeth.json",
        "engine": "cosyvoice3",
        # Same voice and delivery as ru. The owner approved the Пс 22 ear test
        # 2026-07-16: CosyVoice reads civil-script Slavonic the way a modern
        # Russian reader would (akanye, guessed archaic stress — accepted).
        "voice": str(OUTPUT / "myvoice_take1.wav"),
        # Book indexes and names are identical to ru_synodal (verified
        # 2026-07-16: 83 books, name lists byte-identical), so the Russian
        # style map and the «1 Царств»→«Первая Царств» speller apply
        # unchanged. Books 67 and 77-82 are empty in the asset and render
        # nothing.
        "styles": RU_STYLES,
        "book_styles": RU_BOOK_STYLES,
        "strip_notes": False,
        "default_books": None,
        "normalizer": "cu_digits",
    },
}

BOOK_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]

BOOK_NAMES_RU = [
    "Бытие", "Исход", "Левит", "Числа", "Второзаконие",
    "Иисус Навин", "Судьи", "Руфь", "Первая Самуила", "Вторая Самуила",
    "Первая Царств", "Вторая Царств", "Первая Паралипоменон", "Вторая Паралипоменон", "Ездра",
    "Неемия", "Есфирь", "Иов", "Псалтирь", "Притчи",
    "Екклесиаст", "Песнь Песней", "Исаия", "Иеремия", "Плач Иеремии",
    "Иезекииль", "Даниил", "Осия", "Иоиль", "Амос",
    "Авдий", "Иона", "Михей", "Наум", "Аввакум",
    "Софония", "Аггей", "Захария", "Малахия",
    "Матфей", "Марк", "Лука", "Иоанн", "Деяния",
    "Римлянам", "Первое Коринфянам", "Второе Коринфянам", "Галатам", "Ефесянам",
    "Филиппийцам", "Колоссянам", "Первое Фессалоникийцам", "Второе Фессалоникийцам",
    "Первое Тимофею", "Второе Тимофею", "Титу", "Филимону", "Евреям",
    "Иакова", "Первое Петра", "Второе Петра", "Первое Иоанна", "Второе Иоанна",
    "Третье Иоанна", "Иуды", "Откровение",
]

_RU_ONES_ORD = {1: "первая", 2: "вторая", 3: "третья", 4: "четвёртая",
                5: "пятая", 6: "шестая", 7: "седьмая", 8: "восьмая", 9: "девятая"}
_RU_TEENS_ORD = {10: "десятая", 11: "одиннадцатая", 12: "двенадцатая",
                 13: "тринадцатая", 14: "четырнадцатая", 15: "пятнадцатая",
                 16: "шестнадцатая", 17: "семнадцатая", 18: "восемнадцатая",
                 19: "девятнадцатая"}
_RU_TENS_ORD = {20: "двадцатая", 30: "тридцатая", 40: "сороковая",
                50: "пятидесятая", 60: "шестидесятая", 70: "семидесятая",
                80: "восьмидесятая", 90: "девяностая"}
_RU_TENS_CARD = {20: "двадцать", 30: "тридцать", 40: "сорок", 50: "пятьдесят",
                 60: "шестьдесят", 70: "семьдесят", 80: "восемьдесят",
                 90: "девяносто"}
_RU_HUND_ORD = {100: "сотая"}
_RU_HUND_CARD = {100: "сто"}


def ru_ordinal_fem(n):
    """Feminine ordinal for 1..199, e.g. 1 -> 'первая', 151 -> 'сто пятьдесят первая'.

    Feminine because it agrees with «глава». Spelled out because CosyVoice's
    frontend has no Russian branch — Cyrillic falls through to the ENGLISH
    path, where spell_out_number() renders «Глава 1» as "Глава ONE" in English
    (owner caught this in Matthew 1, 2026-07-15). Never hand this engine a
    digit in Russian text.

    Range covers Psalms, which reaches 151 in the Orthodox canon.
    """
    if not 1 <= n <= 199:
        raise ValueError(f"ru_ordinal_fem: {n} out of range 1..199")
    parts = []
    hund, rem = (n // 100) * 100, n % 100
    if hund:
        if rem == 0:
            return _RU_HUND_ORD[hund]
        parts.append(_RU_HUND_CARD[hund])
    if 10 <= rem <= 19:
        parts.append(_RU_TEENS_ORD[rem])
        return " ".join(parts)
    tens, ones = (rem // 10) * 10, rem % 10
    if tens:
        if ones == 0:
            parts.append(_RU_TENS_ORD[tens])
            return " ".join(parts)
        parts.append(_RU_TENS_CARD[tens])
    if ones:
        parts.append(_RU_ONES_ORD[ones])
    return " ".join(parts)


_SV_ONES = {1: "ett", 2: "två", 3: "tre", 4: "fyra", 5: "fem", 6: "sex",
            7: "sju", 8: "åtta", 9: "nio", 10: "tio", 11: "elva", 12: "tolv",
            13: "tretton", 14: "fjorton", 15: "femton", 16: "sexton",
            17: "sjutton", 18: "arton", 19: "nitton"}
_SV_TENS = {20: "tjugo", 30: "trettio", 40: "fyrtio", 50: "femtio",
            60: "sextio", 70: "sjuttio", 80: "åttio", 90: "nittio"}


def sv_cardinal(n):
    """Swedish cardinal for 1..199, spelled out so the TTS cannot fall back
    to an English digit reading (the CosyVoice «Глава one» lesson)."""
    if n < 1 or n > 199:
        raise ValueError(f"sv_cardinal: {n} out of range 1..199")
    out = ""
    if n >= 100:
        out = "hundra" if n < 200 else ""
        n -= 100
        if n == 0:
            return out
    if n in _SV_ONES:
        return out + _SV_ONES[n]
    tens, ones = (n // 10) * 10, n % 10
    return out + _SV_TENS[tens] + (_SV_ONES[ones] if ones else "")


# The sv asset gives its APOCRYPHA books ENGLISH names ("Wisdom of Solomon",
# "Bel and the Dragon") while its canonical books are Swedish ("1 Mosebok") —
# so the asset name, correct for books 0-65, would have every apocryphal
# chapter announce an English title inside a Swedish sentence, in the Swedish
# friend's cloned voice. This is exactly the BOOK_NAMES_RU failure described
# below, in a different translation: wrong, confidently, for 147 chapters.
#
# Owner's call 2026-09-02: use THE PRINT'S OWN TITLES for authenticity, not
# modern Swedish forms, falling back to modern only where the print has none.
# Every one of the twelve printed books turned out to carry a title, so there
# is no fallback entry. Each is derived from the 1703 print itself — running
# head, display title, or closing colophon — recorded in the campaign files
# under research/karlxii_*.md; the source is named per line. ⚠ These are 1703
# spellings on purpose. Do NOT "correct" them to modern Swedish.
# ⚠ Books 66, 67, 73, 77 and 82 are absent from this Lutheran print and
# render nothing, so they are deliberately not listed here.
SV_APOC_NAMES = {
    68: "Tobie Book",                        # colophon «Ände på Tobie book.»
    69: "Judiths Book",                      # colophon «Ände på Judiths book.»
    70: "Wijshetenes Book",                  # running head «Wijshetenes Book /»
    71: "Jesu Syrachs Book",                 # running head «Jesu Syrachs Book. Cap. I.»
    72: "Propheten Baruch",                  # colophon «Ände på Propheten Baruch.»
    74: "Manasse Böön",                      # section title «Manasse Böön»
    75: "Then Första Boken the Maccabeers",  # display title
    76: "Then Andra Boken the Maccabeers",   # display title
    78: "Stycker af Esthers Book",           # display title
    79: "Asarie Böön",                       # section title «Asarie Böön»
    80: "Historia om Susanna och Daniel",    # «Historia om Susanna/ och Daniel.»
    81: "Om Bel och Drakan i Babel",         # «Om Bel/ och Drakan i Babel»
}


def chapter_header_text(lang, book_idx, chapter_idx, n_chapters, book_name=None):
    """Generate the spoken chapter header, e.g. 'Genesis, Chapter 5'.

    book_name comes from the ASSET, not a hardcoded list. The old hardcoded
    BOOK_NAMES_RU was both short and wrong (audited 2026-07-15): it had 66
    entries for an 83-book asset, so every apocryphal book announced itself as
    «Книга 68»; and it used English versification names, so «3 Царств» was
    announced as «Первая Царств» — the wrong book, confidently, for 22
    chapters. The asset already carries the correct Synodal names.
    """
    if lang in ("ru", "cu"):
        # cu shares everything here: cu_elizabeth's book names are identical
        # to ru_synodal's, and the headers are announced in Russian either way.
        book = book_name or (BOOK_NAMES_RU[book_idx]
                             if book_idx < len(BOOK_NAMES_RU) else None)
        if not book:
            raise ValueError(f"no Russian book name for index {book_idx}")
        book = ru_book_name_spoken(book)   # «1 Царств» -> «Первая Царств»
        if n_chapters == 1:
            return book
        return f"{book}, Глава {ru_ordinal_fem(chapter_idx + 1)}"
    if lang == "sv":
        # Asset names are Swedish («1 Mosebok», «Psaltaren»); numbers are
        # spelled out (sv_cardinal) so Chatterbox cannot read digits the
        # English way. Swedish convention says «Psalm 23», not «kapitel 23»,
        # for the Psalter. ⚠ Native-review welcome: ask the Swedish friend.
        # SV_APOC_NAMES wins over the asset name for the apocrypha ONLY (see
        # its comment); books 0-65 are untouched and still read the asset.
        book = SV_APOC_NAMES.get(book_idx) or book_name or f"Bok {book_idx + 1}"
        if n_chapters == 1:
            return book
        if book == "Psaltaren":
            return f"Psaltaren, Psalm {sv_cardinal(chapter_idx + 1)}"
        return f"{book}, kapitel {sv_cardinal(chapter_idx + 1)}"
    else:
        book = book_name or (BOOK_NAMES[book_idx]
                             if book_idx < len(BOOK_NAMES) else f"Book {book_idx}")
        if n_chapters == 1:
            return book
        return f"{book}, Chapter {chapter_idx + 1}"


def strip_kjv_notes(text):
    """Strip {x:y} margin notes, keep {supplied words}."""
    text = re.sub(r"\{[^:}]*:[^}]*\}", "", text)
    text = re.sub(r"[{}]", "", text)
    return text.strip()


# Books whose Synodal title is a «книга» (feminine) rather than a «послание»
# (neuter). Determines which ordinal form the spoken header uses:
#   feminine -> «Первая Царств»      neuter -> «Первое Коринфянам»
_RU_FEMININE_BOOKS = ("Царств", "Паралипоменон", "Ездры", "Маккавейская")
_RU_ORD_FEM = {1: "Первая", 2: "Вторая", 3: "Третья", 4: "Четвёртая"}
_RU_ORD_NEU = {1: "Первое", 2: "Второе", 3: "Третье", 4: "Четвёртое"}


def ru_book_name_spoken(name):
    """«1 Царств» -> «Первая Царств»; «3 Иоанна» -> «Третье Иоанна».

    22 of the 83 Synodal book titles start with a digit. Handed to CosyVoice
    as-is they go through its English number speller and come out as "one
    Царств" (the same bug the owner caught on «Глава 1» in Matthew 1).

    Gender follows the implied noun: книга (f) for the OT sets, послание (n)
    for the epistles. NOTE this is exactly what the old hardcoded BOOK_NAMES_RU
    was reaching for — it had the gender right but the index mapping wrong, so
    «3 Царств» (index 10) was announced «Первая Царств». Deriving from the
    asset's own title cannot drift that way.
    """
    m = re.match(r"^(\d+)\s+(.*)$", name)
    if not m:
        return name
    n, rest = int(m.group(1)), m.group(2)
    table = _RU_ORD_FEM if rest.startswith(_RU_FEMININE_BOOKS) else _RU_ORD_NEU
    if n not in table:
        raise ValueError(f"no Russian ordinal for book title {name!r}")
    return f"{table[n]} {rest}"


def strip_ru_markup(text):
    """Drop apparatus notes from Synodal verses.

    The escaped-OSIS defect this function was written for (audited 2026-07-15:
    Иов 2:9's ~600-char Septuagint variant in &lt;note&gt;, Иов 9:9's
    constellations note, Псалтирь 143:15's stray &lt;title&gt;) was fixed in the
    ASSET on 2026-07-16 (commit 534a43d): the surviving two notes are now
    {Примечание: ...} margin notes, the same {x:y} colon-note convention the
    KJV asset uses, which BibleRepo.parseAsset strips for readers.

    So this must strip BRACE notes now, exactly like strip_kjv_notes — the old
    &lt;note&gt; regexes matched nothing after the asset fix, and Иов 2 + Иов 9
    were narrated on 2026-07-18 with the note text spoken as scripture (Иов 2
    tripped qa's digit check via «70-ти»; Иов 9's note has no digit and leaked
    silently). Both chapters need a re-render with this fix in place.

    The escaped-tag stripping is kept as a defensive layer in case a future
    asset regeneration reintroduces the module's raw form.
    """
    text = re.sub(r"\{[^:}]*:[^}]*\}", "", text)       # {Примечание: ...} notes
    text = re.sub(r"[{}]", "", text)                   # unwrap supplied words
    text = re.sub(r"&lt;note&gt;.*?&lt;/note&gt;", "", text, flags=re.S)
    text = re.sub(r"&lt;title[^&]*&gt;.*?&lt;/title&gt;", "", text, flags=re.S)
    text = re.sub(r"&lt;[^&]*&gt;", "", text)          # any stray escaped tag
    text = re.sub(r"&[a-z]+;|&#\d+;", "", text)        # any stray entity
    return re.sub(r"\s{2,}", " ", text).strip()


def strip_ru_variant_numbers(text):
    """Drop bracketed Septuagint variant numbers from Synodal text.

    The Synodal prints the Masoretic number as words and the LXX variant as a
    bracketed digit: «Адам жил сто тридцать [230] лет». Read aloud that becomes
    "сто тридцать two hundred thirty лет" — the apparatus voiced as if it were
    prose, and in English, because CosyVoice routes Cyrillic through its
    English number speller. Only 28 verses (0.08%), all Genesis-5-style
    genealogies.

    Bracketed WORDS are supplied text and must stay: «и родил [сына]» is read.
    Only bracketed bare numbers go.
    """
    return re.sub(r"\s*\[\d+\]", "", text)


def normalize_cu_digits(text):
    """Keep digits out of the Slavonic text — CosyVoice reads them in English.

    The whole 83-book cu_elizabeth asset has exactly TWO digit-bearing verses
    (audited 2026-07-16):
      * Пс 151:1 — the restored superscription reads «вне числа 150 псалмов»;
        the 150 is spelled out in genitive case.
      * 3 Царств 2:35 — the CrossWire module flattened the LXX's lettered
        additions (2:35a-o) into one long verse with bare digit markers
        between sentences. Those are apparatus, not scripture — dropped.
    qa_narration's digit check covers cu like ru, so any digit a future asset
    edit introduces fails QA instead of shipping in English.
    """
    text = text.replace("вне числа 150 псалмов",
                        "вне числа ста пятидесяти псалмов")
    text = re.sub(r"(^|(?<=\s))\d+(?=\s|$)", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


_SHORT_LEAD = re.compile(r"^\s*\[?([^\].!?]{1,24}?)\.\]?\s+(?=\S)")

# The punctuation join_short_lead uses. Overridable per-run so a chapter the
# comma form keeps failing on can be retried with a different one WITHOUT
# editing the asset — «Аллилуия!» and «Аллилуия —» both voiced correctly in
# isolated tests where «Аллилуия.» did not. Only punctuation varies; the words
# are never touched.
LEAD_JOIN = os.environ.get("NARRATE_LEAD_JOIN", ", ")


def join_short_lead(text):
    """Join a very short leading sentence to the one after it, with a comma.

    ⚠⚠ WITHOUT THIS, CosyVoice SILENTLY DROPS PSALM SUPERSCRIPTIONS. Measured
    2026-08-07 after Psalms 135/146/148 rendered with no «Аллилуия» on 4 of 4
    chapter draws each, and the owner's re-render queue kept "fixing" them to
    no effect:

        «Аллилуия. Славьте Господа, ибо Он благ…»   -> title NOT spoken (5/5)
        «[Аллилуия.] Славьте Господа…»              -> title NOT spoken
        «Аллилуия, славьте Господа…»                -> spoken (3/3)
        «Аллилуия — славьте…» / «Аллилуия! Славьте…» -> spoken

    ⚠⚠ MECHANISM, established by elimination — do NOT repeat these tests:
      · NOT the brackets — removing them changed nothing (5/5 still dropped).
      · NOT the splice — the PRE-SPLICE render lacks the word too, while
        Psalm 23's pre-splice render contains it. apply_announcements is
        exonerated.
      · NOT CosyVoice's English text normalizer — running the real `wetext`
        Normalizer over these exact strings returns them UNCHANGED.
      · NOT paragraph splitting — split_paragraph ACCUMULATES short segments
        (frontend_utils.py); a 60-char verse is one utterance, well under the
        80-token limit, so the model receives the whole text.
      · It is THE MODEL, omitting a short leading utterance during generation.

    So this join is a MITIGATION, not a cure: it measurably reduces the failure
    (Psalms 23 and 91 came back correct on the first draw after it, having
    failed 4/4 before), but Psalm 135 still failed with it applied. **No word
    is added or removed; only the punctuation between title and verse
    changes**, which is why it is safe to apply to scripture.

    ⚠ THE REAL GUARD IS VERIFICATION. Because the omission is stochastic, any
    render of a set with superscriptions must be checked by ASR afterwards —
    tools/check_ru_titles_rendered.py — and failures redrawn. That applies to
    the Church Slavonic set as much as to ru.

    ⚠ NOTHING ELSE IN THE PIPELINE CAN SEE THIS DEFECT. The chapter is one
    word shorter and every count, duration, offset and marker check still
    passes; only listening (ASR) catches it. tools/check_ru_titles_rendered.py
    is that check.

    ⚠ It is NOT reliably deterministic — Psalm 106 has byte-identical verse-1
    text to Psalm 135 and DID speak its title. Treat this as "frequently
    dropped", not "always", and keep verifying renders rather than trusting
    the fix blindly.
    """
    return _SHORT_LEAD.sub(lambda m: m.group(1) + LEAD_JOIN, text, count=1)


def normalize_text(text, normalizer_name):
    """Apply language-specific text normalization for TTS."""
    if normalizer_name is None:
        return text
    if normalizer_name == "ru_variants":
        return join_short_lead(strip_ru_variant_numbers(strip_ru_markup(text)))
    if normalizer_name == "cu_digits":
        return join_short_lead(normalize_cu_digits(text))
    if normalizer_name == "ru_stress":
        # ⚠ CORRUPTS TEXT — see the note in LANG_CONFIG["ru"] and
        # tools/audit_ru_stress.py. Do not use until the table is rebuilt.
        import ru_stress
        return strip_ru_variant_numbers(ru_stress.apply_stress(text))
    if normalizer_name in ("geneva", "tyndale", "wycliffe", "ylt"):
        import archaic_english
        return archaic_english.normalize(text, normalizer_name)
    return text


def load_bible(lang):
    cfg = LANG_CONFIG[lang]
    path = ASSETS / cfg["asset"]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_silence_wav(path, duration_ms, sample_rate=24000):
    """Generate a silent WAV file."""
    n_samples = int(sample_rate * duration_ms / 1000)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)


def get_wav_duration_ms(wav_file):
    """Duration of a WAV in ms, for ANY sample format.

    Uses soundfile rather than stdlib `wave`. `wave` cannot read IEEE-float
    WAVs (format code 3) — it raises "unknown format: 3". This function used
    to wrap `wave` in a bare `except: return 0`, which turned that error into
    a silent zero: every Bark verse measured as 0ms, so concatenate_with_silence
    accumulated nothing but the 600ms gaps and the offsets JSON came out as
    600, 1200, 1800... Verified on ru/42/0 (2026-07-15): 441.6s of correct
    audio paired with offsets claiming the last verse starts at 30s. The audio
    was fine; verse highlighting was ruined.

    Never swallow a failure here: a 0 duration silently corrupts every offset
    downstream, and a WAV we cannot measure is a bug, not a verse to skip.
    """
    info = sf.info(str(wav_file))
    duration_ms = int(info.frames / info.samplerate * 1000)
    if duration_ms <= 0:
        raise ValueError(f"{wav_file}: measured {duration_ms}ms "
                         f"(frames={info.frames}, sr={info.samplerate})")
    return duration_ms


_KOKORO_PROC = None
_KOKORO_FAILS = 0


def _kokoro_worker():
    """The persistent worker, started on demand. See tools/_kokoro_worker.py."""
    global _KOKORO_PROC
    if _KOKORO_PROC is None or _KOKORO_PROC.poll() is not None:
        _KOKORO_PROC = subprocess.Popen(
            [KOKORO_PYTHON, "-u", str(HERE / "_kokoro_worker.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONPATH": KOKORO_SITE_PACKAGES},
            creationflags=_NO_WINDOW,
        )
        hello = _KOKORO_PROC.stdout.readline()
        if not hello or not json.loads(hello).get("ready"):
            raise RuntimeError(f"kokoro worker failed to start: {hello!r}")
    return _KOKORO_PROC


def _kokoro_request(text, voice, output_wav, timeout=180, ipa=None):
    """One request/response, with a hard timeout so a hung worker cannot stall.

    ⚠ A blocking readline on a wedged worker would hang the render FOREVER,
    which is strictly worse than the per-verse process it replaced (that had
    subprocess timeout=120). The read therefore runs on a thread and the worker
    is killed if it overruns.
    """
    import threading
    proc = _kokoro_worker()
    proc.stdin.write(json.dumps({"text": text, "voice": voice,
                                 "out": str(output_wav)}) + "\n")
    proc.stdin.flush()

    box = {}

    def _read():
        box["line"] = proc.stdout.readline()

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        proc.kill()
        raise TimeoutError("kokoro worker timed out")
    line = box.get("line")
    if not line:
        raise RuntimeError("kokoro worker closed the pipe")
    resp = json.loads(line)
    if not resp.get("ok"):
        raise RuntimeError(resp.get("err", "unknown kokoro error"))
    return True


# ── ASR worker for the verse gate ─────────────────────────────────────────
# Same shape as the kokoro worker above: ONE process, ONE model load, JSON
# lines, a thread-guarded read so a wedged worker cannot stall the render.
# Lives in .kokoro_venv because that is where faster-whisper is installed.
_ASR_PROC = None
_ASR_FAILS = 0


def _asr_worker():
    global _ASR_PROC
    if _ASR_PROC is None or _ASR_PROC.poll() is not None:
        _ASR_PROC = subprocess.Popen(
            [KOKORO_PYTHON, "-u", str(HERE / "_asr_worker.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONPATH": KOKORO_SITE_PACKAGES},
            creationflags=_NO_WINDOW,
        )
        hello = _ASR_PROC.stdout.readline()
        if not hello or not json.loads(hello).get("ready"):
            raise RuntimeError(f"asr worker failed to start: {hello!r}")
    return _ASR_PROC


def asr_transcribe(wav_path, asr_lang, timeout=240):
    """-> {"text", "tokens", "model"} or None. ⚠ None is VISIBLE: the failure
    count is printed at 1/10/100/1000 like the tail cutter's, because a gate
    that cannot run must never look like a gate that passed."""
    global _ASR_PROC, _ASR_FAILS
    import threading
    try:
        proc = _asr_worker()
        proc.stdin.write(json.dumps({"wav": str(wav_path), "lang": asr_lang}) + "\n")
        proc.stdin.flush()
        box = {}

        def _read():
            box["line"] = proc.stdout.readline()

        t = threading.Thread(target=_read, daemon=True)
        t.start()
        t.join(timeout)
        if t.is_alive():
            proc.kill()
            raise TimeoutError("asr worker timed out")
        line = box.get("line")
        if not line:
            raise RuntimeError("asr worker closed the pipe")
        resp = json.loads(line)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("err", "unknown asr error"))
        return resp
    except Exception as e:
        _ASR_FAILS += 1
        if _ASR_FAILS in (1, 10, 100, 1000):
            print(f"    ⚠ ASR gate UNAVAILABLE ({_ASR_FAILS} so far): "
                  f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
        try:
            if _ASR_PROC is not None:
                _ASR_PROC.kill()
        except Exception:
            pass
        _ASR_PROC = None
        return None


def synthesize_verse_gated(text, lang, temp_dir, verse_idx, book_idx=None):
    """Synthesize one verse and JUDGE it with the validated screens; re-draw
    while a screen fires, up to GATE_ATTEMPTS. -> (wav_path, dur_ms, info).

    info = {"attempts": [{attempt, reasons, tail, cut, tail_peak}], "kept": n,
            "reasons": reasons of the kept take (empty = clean)} or None when
    the gate did not run (header, empty text, HEXAPLA_NO_GATE).

    ⚠ THE DURATION KEPT IS THE DURATION OF THE FILE KEPT. Attempts overwrite
    verse_<i>.wav, so each take is copied aside and the best one copied back;
    the sidecar drifted 5.45 s on ylt Matthew 5 when file and duration once
    disagreed (see the comment that used to live in narrate_chapter).
    ⚠ Kokoro is deterministic — a second draw is the same audio — so kokoro
    sets are judged and RECORDED but never re-drawn.
    ⚠ An unavailable ASR does not burn draws: the take is kept, the verse is
    recorded as UNJUDGED, and the chapter line says so.
    """
    import shutil
    if _GATE_OFF or verse_idx < 0 or not text or not text.strip():
        wav, dur = synthesize_verse(text, lang, temp_dir, verse_idx, book_idx)
        return wav, dur, None
    from qa_gate import gate_reasons
    cfg = LANG_CONFIG[lang]
    max_attempts = 1 if cfg["engine"] == "kokoro" else GATE_ATTEMPTS
    base = Path(temp_dir) / f"verse_{verse_idx:04d}.wav"
    history, best = [], None
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            _eos_watcher.hits.pop(verse_idx, None)
        _cut_info.clear()
        wav, dur = synthesize_verse(text, lang, temp_dir, verse_idx, book_idx)
        if not wav or dur <= 0:
            history.append({"attempt": attempt, "reasons": ["synthesis-failed"]})
            continue
        asr = asr_transcribe(wav, ASR_LANG.get(lang, "en"))
        if asr is None:
            reasons = ["asr-unavailable"]
        else:
            reasons = gate_reasons(asr.get("text"), asr.get("tokens"), text, lang,
                                   tail_peak=_cut_info.get("tail_peak"),
                                   tail_peak_limit=_GATE_TAIL_PEAK)
        if _RETRY_ON_TOKEN_FLAG and _repetition_flagged(verse_idx):
            reasons.append("token-flag")
        history.append({"attempt": attempt, "reasons": reasons,
                        "tail": " ".join(asr["tokens"][-8:]) if asr else None,
                        "cut": bool(_cut_info.get("cut")),
                        "tail_peak": _cut_info.get("tail_peak"),
                        "eos": sorted(set(_eos_watcher.hits.get(verse_idx, [])))})
        keep = Path(temp_dir) / f"verse_{verse_idx:04d}_a{attempt}.wav"
        shutil.copy2(wav, keep)
        judged = [r for r in reasons if r != "asr-unavailable"]
        if best is None or len(judged) < best[0]:
            best = (len(judged), attempt, keep, dur, reasons)
        if not judged or "asr-unavailable" in reasons:
            break
    if best is None:
        return None, 0, {"attempts": history, "kept": None, "reasons": ["synthesis-failed"]}
    if best[2].resolve() != base.resolve():
        shutil.copy2(best[2], base)
    return str(base), best[3], {"attempts": history, "kept": best[1], "reasons": best[4]}


def synthesize_kokoro(text, voice, output_wav, ipa=None):
    """Synthesize with Kokoro, via a persistent worker in the sandboxed venv.

    ⚠ FALLS BACK to the original one-process-per-verse path if the worker
    misbehaves. The speed-up is worth having, but not at the cost of a render
    that nobody is watching dying on a protocol hiccup; three consecutive
    worker failures disable it for the rest of the run.
    """
    global _KOKORO_FAILS
    if _KOKORO_FAILS < 3:
        try:
            _kokoro_request(text, voice, output_wav, ipa=ipa)
            _KOKORO_FAILS = 0
            return True
        except Exception as e:
            _KOKORO_FAILS += 1
            print(f"    Kokoro worker failed ({_KOKORO_FAILS}/3): {e}"
                  f"{' — falling back to per-verse processes' if _KOKORO_FAILS >= 3 else ''}",
                  file=sys.stderr, flush=True)
    return _synthesize_kokoro_isolated(text, voice, output_wav)


def _synthesize_kokoro_isolated(text, voice, output_wav):
    """The original path: one throwaway process per verse. Kept as the fallback."""
    text_file = Path(tempfile.mktemp(suffix=".txt"))
    try:
        text_file.write_text(text, encoding="utf-8")
        script = f"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from pathlib import Path
text = Path(r'{text_file}').read_text(encoding='utf-8')
import kokoro
import soundfile as sf
import numpy as np
pipeline = kokoro.KPipeline(lang_code='a')
generator = pipeline(text, voice='{voice}')
chunks = []
for _, _, audio in generator:
    chunks.append(audio)
if not chunks:
    print('ERROR: no audio generated', file=sys.stderr)
    sys.exit(1)
samples = np.concatenate(chunks)
sf.write(r'{output_wav}', samples, 24000)
print('OK')
"""
        result = subprocess.run(
            [KOKORO_PYTHON, "-c", script],
            capture_output=True, timeout=120, text=True, encoding='utf-8',
            creationflags=_NO_WINDOW,
            env={**os.environ, "PYTHONPATH": KOKORO_SITE_PACKAGES},
        )
        if result.returncode != 0:
            print(f"    Kokoro error: {result.stderr[:300]}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    Kokoro timeout", file=sys.stderr)
        return False
    except Exception as e:
        print(f"    Kokoro error: {e}", file=sys.stderr)
        return False
    finally:
        text_file.unlink(missing_ok=True)


def synthesize_bark(text, voice_preset, output_wav):
    """Synthesize with Bark via the sandboxed Python 3.12 venv.

    Bark handles ~13s of audio per call. Long verses are split on sentence
    boundaries and concatenated.
    """
    text_file = Path(tempfile.mktemp(suffix=".txt"))
    try:
        text_file.write_text(text, encoding="utf-8")
        script = f"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
os.environ.setdefault("SUNO_USE_SMALL_MODELS", "True")
import torch
_orig = torch.load
def _patched(*a, **kw):
    kw.setdefault("weights_only", False)
    return _orig(*a, **kw)
torch.load = _patched
from pathlib import Path
import numpy as np
import re
text = Path(r'{text_file}').read_text(encoding='utf-8')
from bark import generate_audio, preload_models, SAMPLE_RATE
preload_models()
# Split on sentence boundaries if text is long (~50+ words ≈ >13s)
words = text.split()
if len(words) > 40:
    sents = re.split(r'(?<=[.!?;:])\\s+', text)
    sents = [s for s in sents if s.strip()]
else:
    sents = [text]
chunks = []
for s in sents:
    audio = generate_audio(s, history_prompt='{voice_preset}')
    chunks.append(audio)
import scipy.io.wavfile as wavfile
combined = np.concatenate(chunks)
# Write PCM_16, NOT Bark's native float32. Two reasons:
# (1) stdlib `wave` cannot read IEEE-float WAVs, and anything downstream
#     that reaches for it silently mis-measures the file;
# (2) make_silence_wav() writes 16-bit gaps, and `ffmpeg concat -c copy`
#     wants every input in the same format.
combined = np.clip(combined, -1.0, 1.0)
wavfile.write(r'{output_wav}', SAMPLE_RATE, (combined * 32767).astype(np.int16))
print('OK')
"""
        result = subprocess.run(
            [KOKORO_PYTHON, "-c", script],
            capture_output=True, timeout=300, text=True, encoding='utf-8',
            creationflags=_NO_WINDOW,
            env={**os.environ, "PYTHONPATH": KOKORO_SITE_PACKAGES},
        )
        if result.returncode != 0:
            print(f"    Bark error: {result.stderr[:300]}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    Bark timeout", file=sys.stderr)
        return False
    except Exception as e:
        print(f"    Bark error: {e}", file=sys.stderr)
        return False
    finally:
        text_file.unlink(missing_ok=True)


COSYVOICE_REPO = "C:/Projects/CosyVoice"
COSYVOICE_MODEL = f"{COSYVOICE_REPO}/pretrained_models/Fun-CosyVoice3-0.5B"
_cosyvoice_model = None


def _get_cosyvoice():
    """Load Fun-CosyVoice3 once per process and cache it.

    NOTE this engine runs IN-PROCESS, unlike kokoro/bark which are spawned per
    verse. Loading this model takes ~20s; spawning it per verse would add ~7
    days to a Bible. Run narrate.py under the cosyvoice venv for --lang ru:
      tools\\.cosyvoice_venv\\Scripts\\python.exe tools/narrate.py --lang ru
    The kokoro/bark paths still shell out to their own venv, so mixing is fine.
    """
    global _cosyvoice_model
    if _cosyvoice_model is not None:
        return _cosyvoice_model

    sys.path.insert(0, f"{COSYVOICE_REPO}/third_party/Matcha-TTS")
    sys.path.insert(0, COSYVOICE_REPO)
    cwd = os.getcwd()
    os.chdir(COSYVOICE_REPO)
    try:
        import torch
        import torchaudio

        # torchaudio >=2.9 routes load() through torchcodec, which wants FFmpeg
        # DLLs this box does not expose. CosyVoice's load_wav already asks for
        # backend='soundfile' (cosyvoice/utils/file_utils.py) but modern
        # torchaudio ignores that kwarg. Honour the original intent.
        def _load_soundfile(wav, *a, **kw):
            data, sr = sf.read(str(wav), dtype="float32", always_2d=True)
            return torch.from_numpy(data.T.copy()), sr
        torchaudio.load = _load_soundfile

        from cosyvoice.cli.cosyvoice import AutoModel
        _cosyvoice_model = AutoModel(model_dir=COSYVOICE_MODEL)
    finally:
        os.chdir(cwd)
    return _cosyvoice_model


def synthesize_cosyvoice3(text, cfg, book_idx, output_wav):
    """Synthesize one verse with Fun-CosyVoice3, styled per book.

    Uses inference_instruct2, which takes (text, instruction, prompt_wav) and
    NO prompt_text — so the reference-transcript mismatch that silently halves
    output speed on the zero-shot path cannot happen here.
    """
    try:
        cosy = _get_cosyvoice()
        style = cfg.get("book_styles", {}).get(book_idx, RU_DEFAULT_STYLE)
        instruct = cfg["styles"][style]

        chunks = [j["tts_speech"].squeeze(0).cpu().numpy()
                  for j in cosy.inference_instruct2(
                      text, instruct, cfg["voice"], stream=False)]
        if not chunks:
            print("    CosyVoice3: no audio returned", file=sys.stderr)
            return False

        import numpy as np
        audio = np.clip(np.concatenate(chunks), -1.0, 1.0)
        # ⚠ ADDED 2026-08-05. This call was MISSING on the cosyvoice3 path for
        # the whole ru render — `_trim_and_fade` was written for Chatterbox and
        # only ever called there. Consequence: CosyVoice sometimes stops a verse
        # abruptly, and with no fade the waveform was spliced onto 600 ms of
        # digital silence at full amplitude. The owner heard it in Numbers 1 as
        # verses "cutting off"; a set-wide scan found 1,077 such verses (3.44%)
        # across 801 of 1,192 chapters. Same defect, same fix, same reasons as
        # the Chatterbox path — see _trim_and_fade's docstring.
        audio = _trim_and_fade(audio, cosy.sample_rate)
        # PCM_16 to match make_silence_wav()'s gaps (ffmpeg concat -c copy
        # needs one format) and to stay readable by any WAV reader.
        sf.write(str(output_wav), (audio * 32767).astype(np.int16),
                 cosy.sample_rate, subtype="PCM_16")
        return True
    except Exception as e:
        print(f"    CosyVoice3 error: {e}", file=sys.stderr)
        return False


_chatterbox_model = None


def _get_chatterbox():
    """Lazy in-process Chatterbox Multilingual (MIT; ResembleAI/chatterbox).

    Must run under tools\\.chatterbox_venv. Device: CHATTERBOX_DEVICE env
    (default cuda). ⚠ Do not load on the GPU while a CosyVoice render owns
    it — ~4 GB of Chatterbox on the shared 8 GB card can OOM a days-long
    render; use CHATTERBOX_DEVICE=cpu for tests instead.
    """
    global _chatterbox_model
    if _chatterbox_model is not None:
        return _chatterbox_model
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    device = os.environ.get("CHATTERBOX_DEVICE", "cuda")
    _chatterbox_model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    return _chatterbox_model


# ★ VERSE-EDGE RHYTHM (owner, 2026-08-21: "starts and stops awkwardly").
# MEASURED over the word timings of six finished sets - silence before the first
# word and after the last, in ms:
#     kokoro  wbt  lead 306 sd 20 | trail 715 sd 36
#             gnv  lead 305 sd 21 | trail 715 sd 36
#             wyc  lead 304 sd 22 | trail 717 sd 40
#     chatter sv   lead 130 sd 53 | trail 597 sd 264
#             tyn  lead  94 sd143 | trail 292 sd 443  (max 3505)
#             ylt  lead  63 sd 25 | trail 326 sd 393
# Kokoro output is written through UNTOUCHED, so every verse carries the same
# breath and every join is the same ~1.6 s once the 600 ms concat gap is added.
# That is why Wycliffe and Geneva sound composed and the chatterbox sets do not:
# _trim_and_fade runs on the chatterbox and cosyvoice paths ONLY, and it cuts to
# within 40 ms of the first and last loud sample - so a chatterbox verse starts
# the instant the gap ends, with no breath, and the pause after it swings from a
# fifth of a second to three and a half.
# ⚠ The trim is NOT damaging speech and must not be blamed for that: measured on
# eight ylt verses, what it discards at the head is 0-168 ms sitting at -61 to
# -99 dB. The defect is that it removes the PACING along with the artifact.
# So: keep the trim (it exists to kill the click and the vocoder whirr), then
# pad the edges back to the figures the owner already likes.
LEAD_MS = 305
TRAIL_MS = 715
# ⚠⚠ THE PADDING MUST BE SUBTRACTED BEFORE ANY PACE MEASUREMENT. It adds a
# CONSTANT ~940 ms to every verse, which distorts SHORT verses far more than
# long ones - a 2 s verse drops 33% in chars/sec, a 10 s verse only 9%. Left
# uncorrected, repace_outliers reads every short verse as a slow outlier and
# re-rolls audio that was perfectly good, which is both wasted render time and
# a fresh roll of the dice on a verse that had already come out right.
# Caught on the first padded render: the chapter median fell 17.1 -> 15.1 ch/s
# and verse 7 was re-paced for no reason.
EDGE_PAD_MS = (LEAD_MS - 40) + (TRAIL_MS - 40)   # keep_ms is kept by the trim


def _trim_and_fade(audio, sr, thresh=0.0025, keep_ms=40,
                   fade_in_ms=12, fade_out_ms=45,
                   lead_ms=0, trail_ms=0, tail_keep_ms=None):
    """Trim near-silent head/tail, then fade both ends to zero.

    ⚠ WHY THIS EXISTS. Verses are synthesized separately and stitched by
    `ffmpeg concat -c copy` against 600 ms of DIGITAL SILENCE. Chatterbox does
    not end a clip at zero — and it frequently stops early: the owner's Genesis
    1 test logged 34 forced-EOS events across 31 verses (6 token_repetition,
    28 long_tail). A waveform that ends mid-amplitude spliced onto absolute
    silence is a click; a low-level vocoder tail left before the gap is the
    "weird whirr" he reported at 2:36, and a clip that starts mid-amplitude is
    the abrupt "and GOD" he heard at v8. Owner-reported artifacts at 0:46,
    2:17 and 2:36 all sat at or near verse joins, which is what pointed here.

    Trimming is deliberately gentle (keeps 40 ms of room) so no consonant onset
    is clipped — losing the start of a word would be far worse than a click.
    """
    import numpy as np
    # ⚠⚠ THE THRESHOLD MUST BE RELATIVE TO THIS CLIP, NOT ABSOLUTE.
    # Measured 2026-08-16 on the Tyndale Genesis 1 header, which the owner
    # heard as an "uhh" right after "Genesis, Chapter 1":
    #     speech  peak 0.7987   rms 0.1085
    #     tail    peak 0.0101   rms 0.0009      <- 41 dB below the speech
    # The fixed 0.0025 floor is FOUR TIMES BELOW that tail's peak, so 2.1% of
    # the tail's samples cleared it, loud[-1] landed inside the tail, and the
    # trim preserved the very artifact it exists to remove. An absolute floor
    # cannot work here: a vocoder tail scales with the clip's own loudness.
    # 2% of peak is ~-34 dB — far under any real speech, including fricative
    # onsets — and the 40 ms keep-margin below still protects consonants.
    peak = float(np.abs(audio).max()) if len(audio) else 0.0
    thresh = max(thresh, peak * 0.02)
    loud = np.nonzero(np.abs(audio) > thresh)[0]
    if len(loud) == 0:
        return audio
    # ⚠ tail_keep_ms EXISTS BUT NO CALLER PASSES IT (2026-08-22). It was added
    # to preserve word decay after the owner heard "'the earth' ends too
    # abruptly" in a PREVIEW CLIP - and the abruptness turned out to be the
    # preview's own 8-second cut, not the render: he then listened to the full
    # file and retracted ("it sounds good, maybe it was just in the preview").
    # The pipeline he approved by ear uses the plain 40 ms keep, so that is
    # what runs. If a REAL gated-ending complaint ever arrives, this parameter
    # is the fix (tail_keep_ms=220, fade_out_ms=180, and EDGE_PAD_MS must
    # become (LEAD_MS-40)+(TRAIL_MS-tail_keep)) - do not re-derive it.
    if tail_keep_ms is None:
        tail_keep_ms = keep_ms
    keep = int(sr * keep_ms / 1000)
    start = max(0, loud[0] - keep)
    end = min(len(audio), loud[-1] + int(sr * tail_keep_ms / 1000))
    audio = audio[start:end].copy()
    fi = int(sr * fade_in_ms / 1000)
    fo = int(sr * fade_out_ms / 1000)
    if fi and len(audio) > fi:
        audio[:fi] *= np.linspace(0.0, 1.0, fi, dtype=audio.dtype)
    if fo and len(audio) > fo:
        audio[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=audio.dtype)
    # Pad AFTER the fades, so the padding is true digital silence and the fade
    # still lands on the waveform rather than on the padding.
    if lead_ms or trail_ms:
        # ⚠ The trim already left `keep_ms` of sub-threshold material at each
        # end, so pad the DIFFERENCE. Adding the full figure on top overshoots
        # by exactly keep_ms (measured: 345 ms against a 305 ms target), and the
        # point of this is to match the kokoro sets, not to beat them.
        pad_l = max(0, int(sr * (lead_ms - keep_ms) / 1000))
        pad_t = max(0, int(sr * (trail_ms - tail_keep_ms) / 1000))
        audio = np.concatenate([np.zeros(pad_l, dtype=audio.dtype), audio,
                                np.zeros(pad_t, dtype=audio.dtype)])
    return audio


class _EOSWatcher(logging.Handler):
    """Record Chatterbox's own forced-EOS warnings against the verse being
    rendered, so a re-render can target verses instead of whole chapters.

    Chatterbox emits ~4 sampling passes per verse, so warning ORDER cannot be
    used to infer the verse — an earlier attempt to map them that way produced
    a plainly wrong verse list. Attributing them at the call site is the only
    reliable way, and it is what makes QA possible across 451 chapters, where
    listening to everything is not an option and duration checks cannot see
    this defect class at all.
    """
    def __init__(self):
        super().__init__()
        self.current = None
        self.hits = {}

    def emit(self, record):
        msg = record.getMessage()
        if "forcing EOS" not in msg or self.current is None:
            return
        kinds = [k for k in ("token_repetition", "long_tail",
                             "alignment_repetition") if f"{k}=tensor(True)" in msg
                 or f"{k}=True" in msg]
        if kinds:
            self.hits.setdefault(self.current, []).extend(kinds)


def _repetition_flagged(verse_idx):
    """True if Chatterbox reported REPETITION for this verse.

    Deliberately ignores long_tail: it fired on 30 of 31 verses in the Tyndale
    Genesis 1 test, i.e. it is ordinary end-of-clip behaviour and useless as a
    defect signal. token_repetition fired on 6, two of which are exactly where
    the owner heard artifacts by ear (v18 at 2:11, v21 at 2:35).
    """
    kinds = _eos_watcher.hits.get(verse_idx, [])
    return "token_repetition" in kinds or "alignment_repetition" in kinds


_eos_watcher = _EOSWatcher()
logging.getLogger("chatterbox").addHandler(_eos_watcher)
logging.getLogger("chatterbox").setLevel(logging.WARNING)


# ── Hallucinated-tail cutter ─────────────────────────────────────────────
# ⚠ WHY (owner, 2026-08-21, ylt pilot): Chatterbox sometimes fails to stop at
# the end of a verse and re-emits a fragment of the final word as a NEW word -
# "kindness" -> "nass", "saying" -> "say", "enemy" -> "nenemy", or an invented
# one ("pole"). Measured with forced alignment: 9 of 48 verses in one Matthew 5
# render. NOTHING else can catch it:
#   . duration/pace screens - one syllable moves a 5 s verse by ~0.3 s;
#   . _trim_and_fade - it removes a ~-41 dB vocoder tail; this is speech;
#   . the token_repetition retry - flagged verses come back "clean" and still
#     carry a tail (v1 "pole" survived a clean retry);
#   . whisper - handed scripture it recites the next verse from memory.
# THE ORACLE: MMS_FA forced alignment against the KNOWN text. Audio after the
# last aligned word is, by construction, audio no word of the verse accounts
# for. Cut there. The aligner cannot invent content - it is only ever asked
# where the text it was given actually lands.
# ⚠ CPU on purpose (the GPU is mid-render), one model load per process.
# ⚠ FAIL OPEN: if alignment fails, return the audio unchanged - a kept tail is
# a known small defect, an over-cut verse is a missing half-sentence.
_tail_aligner = None
TAIL_GAP_MS = 200         # a hallucinated word sits after >= this much quiet
# ⚠ 60, NOT 100 (owner, 2026-08-22): with the floor at 100 ms a short vocal
# blip - "a slight 'a' sound after the pause" in the Genesis 1 header -
# survived the cutter: the pause-guard confirmed the gap, then dismissed the
# burst as breath. Real breaths sit below the -28 dB relative level; anything
# ABOVE that level after a 200 ms pause is voice, however short.
TAIL_MIN_RUN_MS = 60
# A gap this long means the utterance ENDED; anything voiced after it is
# spurious however short. See the unioned rule in _cut_spoken_tail.
TAIL_LONG_GAP_MS = 800
TAIL_LONG_MIN_RUN_MS = 20
_tail_fail_n = 0              # silent-failure counter, see the except below
# What the cutter saw on the LAST verse, for the gate's record: where the last
# aligned word sits, whether a cut was made, and the peak of whatever follows
# the first ≥ TAIL_GAP_MS quiet gap after it (the metric that separated the
# owner's "garbled tail" verdicts — RECORDED here, gated only once calibrated).
_cut_info = {}


_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _int_words(n):
    """1..999 as spoken English words, chatterbox-style ('a hundred five')."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()
    rest = n % 100
    return (_ONES[n // 100] + " hundred"
            + (" " + _int_words(rest) if rest else ""))


def _cut_spoken_tail(audio, sr, text, script="latin", lang="en"):
    """Trim audio that continues after the last forced-aligned word."""
    global _tail_aligner
    import numpy as np
    try:
        from align_words import Aligner, align_key, WORD
        import torch
        import torchaudio.functional as AF
        if _tail_aligner is None:
            _tail_aligner = Aligner(device="cpu")
        # ⚠⚠ DIGITS ARE SPOKEN BUT NOT ALIGNABLE. align_words' WORD pattern
        # deliberately excludes digits, so "Matthew, Chapter 5" aligned as
        # ["matthew", "chapter"] - and the spoken "five" landed AFTER the last
        # aligned word, where this function cut it off as a hallucinated tail.
        # The owner heard it immediately on the first otherwise-clean render:
        # the ONE defect in the chapter was introduced by the defect-remover.
        # Chapter headers are the main digit carriers; expand them to the words
        # the voice actually says. Non-English chatterbox sets (sv) must FAIL
        # OPEN here rather than cut on an English expansion of a Swedish number.
        if any(ch.isdigit() for ch in text):
            if lang not in ("en", "ylt", "tyn"):
                return audio, False
            text = re.sub(r"\d+",
                          lambda m: _int_words(int(m.group(0)))
                          if 0 < int(m.group(0)) < 1000 else m.group(0),
                          text)
            if any(ch.isdigit() for ch in text):
                return audio, False          # something we cannot expand
        keys = [k for k in (align_key(w, script, lang)
                            for w in WORD.findall(text)) if k]
        if not keys:
            return audio, False
        wav16 = torch.from_numpy(np.ascontiguousarray(audio, dtype=np.float32))
        if sr != _tail_aligner.sample_rate:
            wav16 = AF.resample(wav16, sr, _tail_aligner.sample_rate)
        spans = _tail_aligner.align(wav16, keys)
        if spans is None or spans[-1] is None:
            return audio, False
        # ⚠⚠ SCAN FROM THE LAST WORD'S **START**, NOT ITS END. MMS_FA must
        # assign every frame to some token, so a hallucination that follows the
        # final word gets ABSORBED INTO THAT WORD'S SPAN. Measured on the ylt
        # Genesis 1 header 2026-08-22: the audio is "Genesis chapter one"
        # (290-1550 ms), a 440 ms pause, then 390 ms of "dad did" — and the
        # aligner returned `one` = 1.347-2.353 s, swallowing the tail whole.
        # `last_end` therefore landed AFTER the hallucination, nothing remained
        # to scan, and the cutter reported no cut on a chapter that plainly had
        # one. The owner caught it by ear on the first banked chapter.
        # Starting the walk at the word's START is strictly safer than its end:
        # the discriminator is still the >= TAIL_GAP_MS quiet gap, and a single
        # word contains no such gap (a plosive closure is 50-80 ms, well under
        # 200), so the first gap found is still the one AFTER the real word.
        # This also subsumes the "MMS_FA ends long vowels early" defect that
        # forced the pause rule in the first place — an early end no longer
        # matters when we do not read the end at all.
        last_end = spans[-1][0]                      # seconds
        _cut_info.update(last_word_start_s=float(spans[-1][0]),
                         last_word_end_s=float(spans[-1][1]))
        # ⚠⚠ CUT AT A PAUSE, NEVER AT AN ALIGNMENT TIMESTAMP. The first version
        # cut at last_end + 120 ms, trusting MMS_FA's end time - and MMS_FA
        # ends a word early on a long vowel (the docstring's own warning), so
        # "Matthew, Chapter five" shipped as "Chapter fiii". The owner caught
        # it on the first campaign header; every chapter header was at risk.
        # A REAL hallucinated word is separated from the verse by silence -
        # every confirmed case had a 0.15-1.1 s gap. Contiguous speech after
        # the aligned end is the WORD STILL FINISHING. So: walk forward from
        # last_end, find the first genuine quiet gap (>= TAIL_GAP_MS), and cut
        # there. Speech before any such gap is kept; no gap, no cut.
        ref = np.percentile(np.abs(audio), 90) + 1e-9
        h = max(1, int(0.02 * sr))
        start_i = int(last_end * sr)
        tail = audio[start_i:]
        nw = len(tail) // h
        # ⚠ MUST NOT REFERENCE TAIL_LONG_MIN_RUN_MS — it is None while the
        # long-gap rule is disabled, and `200 + None` raises TypeError
        # straight into this function's bare `except`, which silently
        # returns "no cut" for EVERY verse. That is exactly how a guard
        # dies without a trace: the regression showed 0/121 cuts where the
        # proven rule gives 13/121, and nothing logged anything.
        if nw < (TAIL_GAP_MS + TAIL_MIN_RUN_MS) // 20:
            return audio, False
        db = 20 * np.log10(
            np.sqrt((tail[:nw * h].reshape(nw, h) ** 2).mean(1)) + 1e-9)
        loud = db > (20 * np.log10(ref) - 28)

        # ⚠⚠ TWO RULES, UNIONED — calibrated against the owner's ear 2026-08-22.
        # A single duration floor cannot cover this defect class:
        #   · a hallucinated WORD ("pole", "nass", "accord") sits after a
        #     0.15-1.1 s gap and is long: gap 200 / run 60 catches it;
        #   · a BLIP (the "uh" after Genesis 1:1; the tick after "and I do eat"
        #     in Genesis 3:13) is 20-60 ms — ONE OR TWO FRAMES — and no duration
        #     floor that still suppresses breath noise can reach it.
        # What identifies the blip is not its length but the SILENCE BEFORE IT.
        # Real speech does not resume for 20 ms after 1.26 s of quiet; that
        # verse had ended. So a LONG gap licenses cutting anything voiced, while
        # a shorter gap still demands a substantial run.
        # Measured: ~2 such tails per chapter across the first six ylt chapters,
        # i.e. ~2,300 over the 1189-chapter set. The owner independently
        # reported three of them by ear; all three are in the scanner's list.
        # ⚠ THE FIRST ATTEMPT AT THIS RULE WAS INERT. It derived the gap length
        # by counting quiet frames BACKWARDS from the point where the gap was
        # first declared — which is by construction exactly the `need` minimum,
        # so the long-gap branch could never fire and the 20 ms blip still got
        # through. Measure each quiet stretch FORWARD, in full, per run.
        need = TAIL_GAP_MS // 20
        n = len(loud)

        # ── RULE 1: the PROVEN rule, reproduced exactly ──────────────────────
        # First quiet gap of >= TAIL_GAP_MS after the last word, then ANY run of
        # >= TAIL_MIN_RUN_MS anywhere after it. ⚠ Do not "tighten" this into a
        # gap-immediately-followed-by-run pairing: that is stricter, and on 121
        # verses of approved audio it dropped 3 real cuts (tyn Mt 5:4, 5:19,
        # John 3:29) that this form catches. Proven behaviour stays byte-for-byte.
        rule1_at = None
        quiet = 0
        gap_end = None
        for i, v in enumerate(loud):
            quiet = 0 if v else quiet + 1
            if quiet >= need:
                gap_end = i
                break
        if gap_end is not None:
            _cut_info["tail_peak"] = (float(np.abs(tail[gap_end * h:]).max())
                                      if len(tail) > gap_end * h else 0.0)
            best = cur = 0
            for v in loud[gap_end:]:
                cur = cur + 1 if v else 0
                best = max(best, cur)
            if best * 20 >= TAIL_MIN_RUN_MS:
                rule1_at = gap_end - need + 2

        # ── RULE 2: a LONG silence, then anything voiced ─────────────────────
        # Measures each quiet stretch in FULL and requires the run to follow it
        # directly. This is the blip case; see the calibration note above.
        rule2_at = None
        if TAIL_LONG_MIN_RUN_MS is not None:
            i = 0
            while i < n and loud[i]:
                i += 1
            while i < n:
                q0 = i
                while i < n and not loud[i]:
                    i += 1
                quiet_frames = i - q0
                if i >= n:
                    break
                r0 = i
                while i < n and loud[i]:
                    i += 1
                if (quiet_frames * 20 >= TAIL_LONG_GAP_MS
                        and (i - r0) * 20 >= TAIL_LONG_MIN_RUN_MS):
                    rule2_at = q0 + min(need, quiet_frames) // 2
                    break

        cands = [c for c in (rule1_at, rule2_at) if c is not None and c > 0]
        cut_at = min(cands) if cands else None
        if cut_at is None:
            return audio, False
        cut_from = start_i + cut_at * h
        _cut_info["cut"] = True
        return audio[:cut_from].copy(), True
    except Exception as e:
        # ⚠⚠ NEVER SWALLOW THIS SILENTLY. A bare `except` here once turned a
        # one-character bug (`TAIL_GAP_MS + None`) into "the tail cutter is
        # disabled for every verse in the run", with nothing in any log and a
        # perfectly normal-looking render. Failing open is the right BEHAVIOUR —
        # a cutter that cannot decide must not cut — but it must be VISIBLE.
        # Reported once per process, with the count, so a systematic failure
        # cannot hide behind a plausible-looking output.
        global _tail_fail_n
        _tail_fail_n += 1
        if _tail_fail_n in (1, 10, 100, 1000):
            print(f"    ⚠ tail cutter FAILED OPEN ({_tail_fail_n} so far): "
                  f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
        return audio, False


def synthesize_chatterbox(text, cfg, output_wav, cut_tail=True):
    """Synthesize one verse with Chatterbox Multilingual (zero-shot clone,
    no transcript needed). Params come from the ear-test-picked config.

    ⚠⚠ `cut_tail=False` DISABLES THE TAIL CUTTER FOR THIS CALL, and the
    announcement component builder is the reason it exists. The cutter walks
    forward from the last aligned word's START (see _cut_spoken_tail) and the
    LAST WORD OF A CHAPTER HEADER IS THE NUMERAL — so on a header there is
    nothing after it but the word we most need kept, and any cut is a cut into
    real speech. The owner heard exactly that on ylt Genesis 14-17
    (2026-08-22): «Genesis, Chapter seven-». Chapter 17 is confirmed by
    measurement — forced alignment has to stretch «seventeen» 394 ms into
    audio containing no speech, while «seven» ends exactly where speech stops.
    ⚠ Do NOT "fix" this by retuning TAIL_LONG_GAP_MS instead: that constant is
    calibrated (see the sweep in the 2026-08-22 handoff) and lowering it
    over-cuts real speech across the whole corpus. Components are ASR-gated
    and tail-polished by build_announcements.polish_tail, which is a better
    guard than the cutter and does not depend on a gap threshold at all."""
    try:
        model = _get_chatterbox()
        wav = model.generate(
            text,
            language_id=cfg["language_id"],
            audio_prompt_path=cfg["voice"],
            cfg_weight=cfg.get("cfg_weight", 0.5),
            exaggeration=cfg.get("exaggeration", 0.5),
        )
        import numpy as np
        audio = np.clip(wav.squeeze(0).cpu().numpy(), -1.0, 1.0)
        # Cut a hallucinated tail BEFORE trim/fade/pad, so the fade lands on
        # the true final word and the pad is measured from it.
        if cut_tail:
            audio, cut = _cut_spoken_tail(audio, model.sr, text)
        else:
            cut = False
        if cut:
            print("    [tail cut]", flush=True)
        # ⚠ The padding is applied HERE and not in the cosyvoice path: ru and cu
        # are rendered, uploaded and shipped, and changing their verse edges
        # would mean re-rendering 2,724 chapters to fix a rhythm nobody has
        # complained about. Chatterbox is where the owner heard it.
        audio = _trim_and_fade(audio, model.sr,
                               lead_ms=LEAD_MS, trail_ms=TRAIL_MS)
        # PCM_16 to match make_silence_wav()'s gaps (same reason as CosyVoice).
        sf.write(str(output_wav), (audio * 32767).astype(np.int16),
                 model.sr, subtype="PCM_16")
        return True
    except Exception as e:
        print(f"    Chatterbox error: {e}", file=sys.stderr)
        return False


def synthesize_piper(text, model_path, output_wav, length_scale=1.11):
    """Synthesize with Piper via Python API."""
    try:
        from piper.voice import PiperVoice
        from piper.config import SynthesisConfig
        voice = PiperVoice.load(model_path)
        syn_config = SynthesisConfig(length_scale=length_scale)
        with wave.open(str(output_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(voice.config.sample_rate)
            for chunk in voice.synthesize(text, syn_config):
                wf.writeframes(chunk.audio_int16_bytes)
        return True
    except Exception as e:
        print(f"    Piper error: {e}", file=sys.stderr)
        return False


# --- Pace consistency (cosyvoice3) -----------------------------------------
#
# Each verse is an INDEPENDENT CosyVoice call and the model invents fresh
# prosody every time; nothing ties verse N's pace to verse N-1's. Measured on
# Obadiah (solemn, 2026-07-15): median 8.26 chars/sec but a 2.57x spread —
# verse 6 at 5.66 ch/s against verse 11 at 14.52, the latter FASTER than the
# normal style's average. The owner heard it immediately: "a lot of different
# variants, different speeds". Human narrators hold ~10% CV; this was 22%.
#
# Post-processing with atempo was tried (tools/clamp_pace.py) and barely helped
# — 21.9% -> 20.9% — because the worst outlier needed a 0.65x stretch, past the
# point where atempo sounds processed. So fix it at generation instead: the
# model is STOCHASTIC, so an outlier is a bad roll, not a property of the text.
# Re-roll it and keep whichever take sits closest to the chapter's median.
# Costs GPU only on outliers (typically 1-3 verses per chapter).
PACE_TOL = 1.25          # re-roll verses outside median/TOL .. median*TOL
PACE_MAX_RETRIES = 2
PACE_MIN_CHARS = 20      # shorter verses cannot be rate-measured reliably

# --- Speaker drift ----------------------------------------------------------
#
# CosyVoice DRAMATISES: it performs verses, raising pitch to voice characters.
# The owner likes this — "it's actually a nice edition, having these
# dramatizations ... it adds a nice touch" (2026-07-15). What he does NOT want
# is the model wandering off into a DIFFERENT PERSON: at Gen 1:6 the bracketed
# «[И стало так.]» came out in a woman's voice (F0 leapt 75 -> 337 Hz).
#
# PITCH CANNOT TELL THESE APART, and neither can flatness:
#   Gen 3:19  269 Hz sustained for a whole verse  -> "my voice, a bit higher,
#             imitating a woman"  — WANTED
#   Gen 1:6   337 Hz for 0.5s                     -> "a woman says it" — BUG
# The liked one is higher for longer. Several hypotheses died here: brackets
# (25% vs 16% drift — noise, and the worst case was unbracketed), direct speech
# (12% vs 6% — noise), "vocoder artifact" (the flatness anomaly was really
# partial speaker drift).
#
# SPEAKER IDENTITY separates them perfectly. Using CosyVoice's OWN speaker
# encoder (campplus.onnx — the model it uses to clone the voice), cosine
# similarity against his reference recording:
#     THE WOMAN (bug)          0.068
#     dramatised (liked)       0.636, 0.679
#     plain narration          0.664, 0.710
# A tenfold gap with nothing in between. So: keep anything that is still HIM,
# however theatrical; re-roll only what stops being him.
#
# campplus runs on CPU (onnxruntime CPUExecutionProvider), so this costs no GPU
# beyond the re-rolls it triggers.
SPEAKER_MIN_SIM = 0.40   # well clear of both populations (0.068 vs 0.63+)
SPEAKER_MAX_RETRIES = 3
# Windowed, because the drift is BRIEF: the Gen 1:6 woman is 0.5s of a 5.6s
# verse. A whole-verse embedding averaged her to 0.647 — identical to the
# dramatisations that must be kept. 1.0s windows at 0.5s hop, take the MINIMUM.
# The drift can be BRIEF — the Gen 1:6 woman lasts 0.5s. A 1.0s window never
# contained only her, so every window mixed her with his voice and averaged
# 0.078 up to 0.353, indistinguishable from a liked dramatisation. The window
# must be no larger than the shortest artifact worth catching; campplus stays
# reliable down to ~0.5s (verified: a 0.5s cut of the woman scores 0.078).
SPEAKER_WIN_S = 0.6
SPEAKER_HOP_S = 0.2
# Windows quieter than this fraction of the clip's own RMS are skipped: they are
# pauses, and their embeddings are noise. Without this gate the minimum finds
# silence rather than drift — his own reference scored 0.567 against itself.
SPEAKER_ENERGY_GATE = 0.7
_spk_session = None
_spk_ref_embedding = None


def _verse_rate(text, dur_ms):
    if not text or dur_ms <= 0:
        return None
    return len(text) / (dur_ms / 1000)


def _speaker_embedding(wav_path):
    """L2-normalised speaker embedding via CosyVoice's campplus encoder.

    Returns None only when the encoder is genuinely unavailable — never
    swallows a real error into a false 'fine'.
    """
    global _spk_session
    import numpy as np
    import torch
    import torchaudio.compliance.kaldi as kaldi

    if _spk_session is None:
        import onnxruntime
        model = f"{COSYVOICE_MODEL}/campplus.onnx"
        if not Path(model).exists():
            return None
        opt = onnxruntime.SessionOptions()
        opt.intra_op_num_threads = 1
        # CPU on purpose: keeps the GPU for synthesis.
        _spk_session = onnxruntime.InferenceSession(
            model, sess_options=opt, providers=["CPUExecutionProvider"])

    data, sr = sf.read(str(wav_path), dtype="float32", always_2d=True)
    speech = torch.from_numpy(data.T.copy())
    if sr != 16000:
        import torchaudio
        speech = torchaudio.transforms.Resample(sr, 16000)(speech)
    if speech.shape[1] < 16000 * 0.4:
        return None                      # too short to identify a speaker
    feat = kaldi.fbank(speech, num_mel_bins=80, dither=0, sample_frequency=16000)
    feat = feat - feat.mean(dim=0, keepdim=True)
    e = _spk_session.run(None, {_spk_session.get_inputs()[0].name:
                                feat.unsqueeze(0).cpu().numpy()})[0].flatten()
    n = np.linalg.norm(e)
    return (e / n) if n > 0 else None


def _speaker_similarity(wav_path, cfg):
    """WORST windowed speaker similarity across a verse, or None.

    ⚠ MUST be windowed, not whole-verse. The Gen 1:6 woman occupies 0.5s of a
    5.6s verse (11% of frames). A whole-verse embedding averages her away: she
    scored 0.647 — indistinguishable from the dramatisations at 0.643 that must
    be KEPT — while a 0.6s cut of just her scores 0.068. Averaging destroys the
    signal. Take the minimum over sliding windows: identity loss anywhere in a
    verse is identity loss.
    """
    global _spk_ref_embedding
    import numpy as np
    import soundfile as _sf

    if _spk_ref_embedding is None:
        _spk_ref_embedding = _speaker_embedding(cfg["voice"])
        if _spk_ref_embedding is None:
            return None

    try:
        data, sr = _sf.read(str(wav_path), dtype="float32", always_2d=True)
    except Exception:
        return None
    mono = data.mean(axis=1)
    win = int(sr * SPEAKER_WIN_S)
    hop = int(sr * SPEAKER_HOP_S)
    if len(mono) < win:
        e = _speaker_embedding(wav_path)
        return None if e is None else float(np.dot(_spk_ref_embedding, e))

    # ENERGY GATE. Without it the minimum just finds silence: windows of pauses
    # and transitions produce meaningless embeddings, and his OWN reference
    # scored 0.567 against itself. Only judge windows that actually contain
    # speech, at a level near the clip's own peak.
    peak = float(np.sqrt(np.mean(mono ** 2))) if len(mono) else 0.0
    if peak <= 0:
        return None
    gate = peak * SPEAKER_ENERGY_GATE

    import tempfile as _tf
    worst = None
    with _tf.TemporaryDirectory() as td:
        for start in range(0, len(mono) - win + 1, hop):
            seg = mono[start:start + win]
            if float(np.sqrt(np.mean(seg ** 2))) < gate:
                continue                      # mostly silence — not judgeable
            p = os.path.join(td, f"w{start}.wav")
            _sf.write(p, seg, sr, subtype="PCM_16")
            e = _speaker_embedding(p)
            if e is None:
                continue
            s = float(np.dot(_spk_ref_embedding, e))
            if worst is None or s < worst:
                worst = s
    return worst


def repace_outliers(verses, pairs, lang, temp_dir, book_idx):
    """Re-synthesize verses whose speaking rate is an outlier for the chapter.

    Only meaningful for stochastic engines — kokoro/piper are deterministic, so
    a retry returns the identical audio and would just burn time.
    """
    cfg = LANG_CONFIG[lang]
    if cfg["engine"] not in ("cosyvoice3", "chatterbox"):
        return pairs

    def _resynth(text, alt_path):
        if cfg["engine"] == "chatterbox":
            return synthesize_chatterbox(text, cfg, alt_path)
        return synthesize_cosyvoice3(text, cfg, book_idx, alt_path)

    pad = EDGE_PAD_MS if cfg["engine"] == "chatterbox" else 0
    rates = [r for r in (_verse_rate(verses[i], d - pad)
                         for i, (w, d) in enumerate(pairs)
                         if w and len(verses[i]) >= PACE_MIN_CHARS) if r]
    if len(rates) < 4:
        return pairs
    rates.sort()
    median = rates[len(rates) // 2]
    lo, hi = median / PACE_TOL, median * PACE_TOL

    # NOTE (2026-07-20): an absolute per-verse duration ceiling was added here
    # to catch instruct-instruction leaks, then REMOVED once measured: the
    # arithmetic gives it a catch window only below ~2.7 characters, i.e. it
    # was dead against the defect while still able to re-roll the slow
    # dramatisations the owner likes. Leaks are fixed at the root instead (see
    # RU_STYLES) and audited post-hoc by tools/scan_narration_leaks.py.
    # Duration cannot detect a leak that REPLACES an utterance.
    for i, (wav, dur) in enumerate(pairs):
        if not wav or len(verses[i]) < PACE_MIN_CHARS:
            continue
        rate = _verse_rate(verses[i], dur - pad)
        if rate is None or lo <= rate <= hi:
            continue
        best = (abs(math.log(rate / median)), wav, dur, rate)
        for attempt in range(PACE_MAX_RETRIES):
            alt = Path(temp_dir) / f"verse_{i:04d}_r{attempt}.wav"
            if not _resynth(verses[i], str(alt)):
                break
            try:
                alt_dur = get_wav_duration_ms(alt)
            except Exception:
                break
            alt_rate = _verse_rate(verses[i], alt_dur - pad)
            if alt_rate is None:
                break
            score = abs(math.log(alt_rate / median))
            if score < best[0]:
                best = (score, str(alt), alt_dur, alt_rate)
            if lo <= alt_rate <= hi:
                break
        if best[1] != wav:
            print(f"\n    verse {i+1}: {rate:.1f} -> {best[3]:.1f} ch/s "
                  f"(median {median:.1f})", end="")
            pairs[i] = (best[1], best[2])

    # NOTE reroll_speaker_drift() exists below but is DELIBERATELY NOT CALLED.
    # See its docstring: the detector could not be made to separate "him
    # performing" (wanted) from "a different person" (bug), and shipping it
    # would destroy dramatisations the owner explicitly likes.
    return pairs


def reroll_speaker_drift(verses, pairs, lang, temp_dir, book_idx):
    """⚠ NOT WIRED IN. Kept for a future attempt with more data. Read this first.

    GOAL (owner, 2026-07-15): keep the dramatisations — "it's actually a nice
    edition ... it adds a nice touch" — but re-roll the case where the model
    becomes A DIFFERENT PERSON (Gen 1:6, «[И стало так.]» in a woman's voice).

    WHY IT IS DISABLED: I could not build a detector that separates the two, and
    a wrong one would delete the dramatisations he likes. Four attempts:

      1. Whole-verse campplus embedding. FAILED: the woman is 0.5s of a 5.6s
         verse, so she averages away — she scored 0.647, identical to a liked
         dramatisation at 0.643.
      2. 1.0s sliding windows, min. FAILED: the minimum found SILENCE, not
         drift; his own reference scored 0.567 against itself.
      3. + energy gate. FAILED: woman 0.353 vs liked 0.345 — no separation.
      4. 0.6s windows. FAILED WORSE: his own reference scored 0.374. campplus
         similarity is DURATION-DEPENDENT — short clips score low regardless of
         speaker.

    THE TRAP THAT FOOLED ME: an "apples to apples" test scored the woman at
    0.078 and liked dramatisations at 0.60-0.63, which looked decisive. It was
    not: the woman got a 0.5s cut and the dramatisations 6-10s spans. Most of
    that gap was DURATION, not identity. Any future attempt must hold clip
    length CONSTANT before comparing similarities.

    ALSO RULED OUT as discriminators (all measured, all noise):
      brackets        25% vs 16% drift, and the worst case was UNbracketed
      direct speech   12% vs 6%
      pitch           the LIKED Gen 3:19 sustains 269Hz for a whole verse; the
                      BUG at Gen 1:6 peaks 337Hz for 0.5s. Higher-for-longer is
                      the one he likes.
      flatness        was really partial speaker drift, and re-rolling on it may
                      have been deleting dramatisations

    WHAT IS ACTUALLY KNOWN: the woman is not a separate bug. She is the SAME
    dramatisation feature overshooting. n=1 confirmed sample — far too few to
    tune a threshold against without inventing one.

    NEXT ATTEMPT should collect samples first: run qa_narration.py over a
    finished book, have the owner mark which flagged verses are genuinely
    "another person", and only then fit a rule. Do not tune on one example.
    """
    cfg = LANG_CONFIG[lang]
    if cfg["engine"] != "cosyvoice3":
        return pairs

    for i, (wav, _dur) in enumerate(pairs):
        if not wav or len(verses[i]) < PACE_MIN_CHARS:
            continue
        sim = _speaker_similarity(wav, cfg)
        if sim is None or sim >= SPEAKER_MIN_SIM:
            continue
        best = (sim, wav, pairs[i][1])
        for attempt in range(SPEAKER_MAX_RETRIES):
            alt = Path(temp_dir) / f"verse_{i:04d}_s{attempt}.wav"
            if not synthesize_cosyvoice3(verses[i], cfg, book_idx, str(alt)):
                break
            alt_sim = _speaker_similarity(alt, cfg)
            if alt_sim is None:
                break
            try:
                alt_dur = get_wav_duration_ms(alt)
            except Exception:
                break
            if alt_sim > best[0]:
                best = (alt_sim, str(alt), alt_dur)
            if alt_sim >= SPEAKER_MIN_SIM:
                break
        if best[1] != wav:
            print(f"\n    verse {i+1}: speaker sim {sim:.3f} -> {best[0]:.3f} "
                  f"(min {SPEAKER_MIN_SIM})", end="")
            pairs[i] = (best[1], best[2])
        elif best[0] < SPEAKER_MIN_SIM:
            print(f"\n    verse {i+1}: speaker sim {sim:.3f} — "
                  f"{SPEAKER_MAX_RETRIES} retries all drifted, kept best", end="")
    return pairs


def apply_overrides(lang, book_idx, chapter_idx, verses):
    """Apply per-verse SYNTHESIS-INPUT overrides to a prepared verse list.

    ⚠ SYNTHESIS ONLY. The displayed verse, the asset and `align_words`'
    reference text all keep the printed spelling — an override may change
    punctuation or respell a word, never WHICH words are spoken.
    ⚠ Applied AFTER strip_notes/normalize_text, because an override records the
    final spoken form. Unvalidated rows are inert; see synthesis_overrides.py.
    ▶ Called from narrate_chapter AND repair_verses.spoken_verses, so a fix
      survives both a full re-render and a per-verse repair. A fix wired into
      only one of them would be silently lost by the other.
    """
    try:
        import synthesis_overrides
    except Exception:
        return verses
    out = []
    for i, v in enumerate(verses):
        t, used = synthesis_overrides.apply(lang, book_idx, chapter_idx, i + 1, v)
        if used:
            print(f"    synthesis override applied to v{i+1}", flush=True)
        out.append(t)
    return out


def synthesize_verse(text, lang, temp_dir, verse_idx, book_idx=None):
    """Synthesize one verse. Returns (wav_path, duration_ms) or (None, 0).

    book_idx selects the per-book narration style (cosyvoice3 only).
    """
    if not text or not text.strip():
        return None, 0

    cfg = LANG_CONFIG[lang]
    wav_path = Path(temp_dir) / f"verse_{verse_idx:04d}.wav"

    if cfg["engine"] == "kokoro":
        # ★ If the set declares an "ipa" mode, convert the verse to phonemes
        # and bypass grapheme-to-phoneme. Wycliffe uses this for reconstructed
        # Middle English; every other kokoro set passes ipa=None and is
        # unaffected.
        _ipa = None
        if cfg.get("ipa") == "middle_english":
            from me_phonemes import to_ipa as _to_ipa
            _ipa = _to_ipa(text)
        ok = synthesize_kokoro(text, cfg["voice"], str(wav_path), ipa=_ipa)
    elif cfg["engine"] == "bark":
        ok = synthesize_bark(text, cfg["voice"], str(wav_path))
    elif cfg["engine"] == "cosyvoice3":
        ok = synthesize_cosyvoice3(text, cfg, book_idx, str(wav_path))
    elif cfg["engine"] == "piper":
        ok = synthesize_piper(text, cfg["voice"], str(wav_path))
    elif cfg["engine"] == "chatterbox":
        ok = synthesize_chatterbox(text, cfg, str(wav_path))
    else:
        print(f"    Unknown engine: {cfg['engine']}", file=sys.stderr)
        return None, 0

    if ok and wav_path.exists() and wav_path.stat().st_size > 44:
        return str(wav_path), get_wav_duration_ms(str(wav_path))
    return None, 0


def concatenate_with_silence(wav_files_and_durations, output_wav, silence_ms=600):
    """Concatenate verse WAVs with silence gaps. Returns cumulative offsets."""
    offsets = []
    cumulative_ms = 0

    all_parts = []
    for i, (wav_path, dur_ms) in enumerate(wav_files_and_durations):
        offsets.append(cumulative_ms)
        if wav_path is None:
            continue
        all_parts.append(wav_path)
        cumulative_ms += dur_ms
        if i < len(wav_files_and_durations) - 1:
            silence_path = str(Path(wav_path).parent / f"silence_{i:04d}.wav")
            make_silence_wav(silence_path, silence_ms)
            all_parts.append(silence_path)
            cumulative_ms += silence_ms

    if not all_parts:
        return []

    concat_list = Path(output_wav).parent / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in all_parts:
            f.write(f"file '{p}'\n")

    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(output_wav)],
        capture_output=True, timeout=120,
        creationflags=_NO_WINDOW,
    )
    concat_list.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"    ffmpeg concat error: {result.stderr.decode()[-300:]}", file=sys.stderr)
        return []

    return offsets


def loudnorm_and_encode(input_wav, output_ogg):
    """Two-pass loudnorm + Opus 32kbps mono encoding."""
    # Pass 1: measure
    r1 = subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_wav),
         "-af", "loudnorm=I=-19:TP=-1.5:LRA=11:print_format=json",
         "-f", "null", "-"],
        capture_output=True, timeout=300,
        creationflags=_NO_WINDOW,
    )

    measured_i = "-19"
    measured_tp = "-1.5"
    measured_lra = "11"
    measured_thresh = "-30"
    measured_offset = "0"

    if r1.returncode == 0:
        stderr_text = r1.stderr.decode(errors="replace")
        json_match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr_text, re.DOTALL)
        if json_match:
            try:
                m = json.loads(json_match.group())
                measured_i = m.get("input_i", measured_i)
                measured_tp = m.get("input_tp", measured_tp)
                measured_lra = m.get("input_lra", measured_lra)
                measured_thresh = m.get("input_thresh", measured_thresh)
                measured_offset = m.get("target_offset", measured_offset)
            except json.JSONDecodeError:
                pass

    # Pass 2: apply measured values + encode
    af = (f"loudnorm=I=-19:TP=-1.5:LRA=11:"
          f"measured_I={measured_i}:measured_TP={measured_tp}:"
          f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
          f"offset={measured_offset}:linear=true")

    r2 = subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_wav),
         "-af", af, "-b:a", "32k", "-c:a", "libopus", "-ac", "1",
         str(output_ogg)],
        capture_output=True, timeout=300,
        creationflags=_NO_WINDOW,
    )

    if r2.returncode != 0:
        print(f"    encode error: {r2.stderr.decode()[-300:]}", file=sys.stderr)
        return False
    return True


def narrate_chapter(lang, book_idx, chapter_idx, books, force=False, dry_run=False):
    cfg = LANG_CONFIG[lang]
    book_name = BOOK_NAMES[book_idx] if book_idx < len(BOOK_NAMES) else f"Book{book_idx}"
    n_chapters = len(books[book_idx]["chapters"])

    output_dir = OUTPUT / lang / str(book_idx)
    output_dir.mkdir(parents=True, exist_ok=True)
    ogg_file = output_dir / f"{chapter_idx}.ogg"
    json_file = output_dir / f"{chapter_idx}.json"

    if ogg_file.exists() and json_file.exists() and not force:
        print(f"  [{book_name} {chapter_idx+1}/{n_chapters}] skip (exists)")
        return True

    verses_raw = books[book_idx]["chapters"][chapter_idx]
    if not verses_raw:
        print(f"  [{book_name} {chapter_idx+1}/{n_chapters}] skip (empty)")
        return True

    if dry_run:
        n_nonempty = sum(1 for v in verses_raw if v and v.strip())
        print(f"  [{book_name} {chapter_idx+1}/{n_chapters}] {n_nonempty} verses (dry-run)")
        return True

    print(f"  [{book_name} {chapter_idx+1}/{n_chapters}] {len(verses_raw)} verses...",
          end="", flush=True)

    # Preprocess verses
    verses = []
    for v in verses_raw:
        if not v:
            verses.append("")
            continue
        if cfg["strip_notes"]:
            v = strip_kjv_notes(v)
        if cfg["normalizer"]:
            v = normalize_text(v, cfg["normalizer"])
        verses.append(v)
    verses = apply_overrides(lang, book_idx, chapter_idx, verses)

    with tempfile.TemporaryDirectory() as tmp:
        # An unmeasurable WAV fails THIS chapter loudly rather than killing the
        # run or, worse, writing a plausible-looking offsets JSON built from
        # zero-length verses (see get_wav_duration_ms).
        try:
            header = chapter_header_text(lang, book_idx, chapter_idx, n_chapters,
                                         book_name=books[book_idx].get("name"))
            hdr_wav, hdr_dur = synthesize_verse(header, lang, tmp, -1, book_idx)
            # Headers get their own guard because repace_outliers() cannot
            # cover them — a header has no chapter pace cohort to compare
            # against. This catches the DOUBLED/STUTTERED announcement class
            # (ru 20/0, Eccl 1, owner-reported 2026-07-20), which does inflate
            # duration. It does NOT catch instruction leaks — those are fixed
            # at the root (see RU_STYLES) and can replace an utterance without
            # lengthening it; measured, this ceiling permits 9.9-11.9s while
            # the worst leaked header ran 10.9s. Deterministic engines (kokoro)
            # never trip the limit.
            hdr_limit_ms = int(len(header) / 3.5 * 1000) + 3000
            for _retake in range(3):
                if not hdr_wav or hdr_dur <= hdr_limit_ms:
                    break
                print(f"    header retake {_retake + 1}: "
                      f"{hdr_dur}ms > {hdr_limit_ms}ms limit", flush=True)
                alt_wav, alt_dur = synthesize_verse(header, lang, tmp,
                                                    -(2 + _retake), book_idx)
                if alt_wav and alt_dur > 0 and alt_dur < hdr_dur:
                    hdr_wav, hdr_dur = alt_wav, alt_dur
            if hdr_wav and hdr_dur > hdr_limit_ms:
                print(f"    WARNING: header still {hdr_dur}ms after retakes "
                      f"(limit {hdr_limit_ms}ms) — keeping shortest take", flush=True)

            pairs = []
            _eos_watcher.hits.clear()
            gate_log = {}
            for i, v_text in enumerate(verses):
                _eos_watcher.current = i        # attribute warnings to THIS verse
                # ── THE VERSE GATE (2026-09-03) ─────────────────────────────
                # Judge every take with the ear-validated screens and re-draw
                # while one fires (synthesize_verse_gated). This replaced the
                # retry on Chatterbox's token_repetition flag, which cost ~53 %
                # of a render and tracked nothing audible (see the env block
                # at the top of the file). The overwrite-vs-duration trap that
                # bit ylt Matthew 5 (sidecar 5.45 s ahead of the audio) is
                # handled inside: the duration returned is always the kept
                # file's own.
                wav_path, dur, ginfo = synthesize_verse_gated(v_text, lang, tmp, i,
                                                              book_idx)
                if ginfo:
                    gate_log[i + 1] = ginfo
                pairs.append((wav_path, dur))
            _eos_watcher.current = None
            if gate_log:
                redrawn = [v for v, g in gate_log.items() if len(g["attempts"]) > 1]
                failing = {v: g["reasons"] for v, g in gate_log.items()
                           if g["reasons"] and g["reasons"] != ["asr-unavailable"]}
                unjudged = [v for v, g in gate_log.items()
                            if any("asr-unavailable" in a["reasons"] for a in g["attempts"])]
                line = (f"    gate: {len(gate_log)} judged, {len(redrawn)} re-drawn, "
                        f"{len(failing)} still failing")
                if failing:
                    line += ": " + ", ".join(f"v{v}({'|'.join(r)})"
                                            for v, r in sorted(failing.items()))
                if unjudged:
                    line += f"; ⚠ {len(unjudged)} UNJUDGED (ASR unavailable)"
                print(line, flush=True)
            pairs = repace_outliers(verses, pairs, lang, tmp, book_idx)
        except Exception as e:
            print(f" FAILED (duration: {e})")
            return False

        pad_ms = EDGE_PAD_MS if cfg["engine"] == "chatterbox" else 0
        header_prefix_ms = 0
        if hdr_wav and hdr_dur > 0:
            header_prefix_ms = hdr_dur + 900  # header + longer pause before verses

        concat_wav = str(Path(tmp) / "chapter.wav")
        all_segments = ([(hdr_wav, hdr_dur)] if hdr_wav else []) + pairs
        offsets = concatenate_with_silence(all_segments, concat_wav, silence_ms=600)
        if hdr_wav:
            offsets = offsets[1:]  # drop the header's offset; verse offsets already include header duration
        if not offsets:
            print(" FAILED (concat)")
            return False

        if not loudnorm_and_encode(concat_wav, str(ogg_file)):
            ogg_file.unlink(missing_ok=True)
            print(" FAILED (encode)")
            return False

        # ⚠ RECORD THE EDGE PADDING IN THE SIDECAR, do not hardcode it in the
        # screens. Every pace-based check - qa_narration.py, tyn_short_verses.py,
        # repace_outliers - divides text length by a verse's DURATION and
        # assumes that duration is speech. Padding breaks that assumption, and
        # it breaks it hardest on SHORT verses: the first padded Matthew 5
        # failed qa_narration at 12.2x spread while sounding correct. Writing
        # the figure here means a screen subtracts what this chapter actually
        # carries, instead of four tools each holding a copy of a constant that
        # will drift the first time LEAD_MS or TRAIL_MS is tuned.
        side = {"offsets": offsets}
        if pad_ms:
            side["edge_pad_ms"] = pad_ms
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(side, f, separators=(",", ":"))

    size_kb = ogg_file.stat().st_size // 1024
    print(f" OK ({size_kb} KB)")
    # Verses where Chatterbox forced an early stop. These are the ONLY
    # machine-visible marker of the glitch/whirr/stutter class — duration
    # heuristics cannot see it, because a forced EOS makes the clip SHORTER
    # rather than longer. Recorded next to the audio so a QA pass can re-render
    # named verses instead of guessing, or re-listening to 451 chapters.
    # ⚠ FILTER ON token_repetition ONLY. Measured on Tyndale Genesis 1:
    # long_tail fired on 30 of 31 verses — it is ordinary behaviour (the
    # analyzer closing a clip once speech ends), so treating it as a defect
    # marker would flag 97% of the corpus and be worth nothing. token_repetition
    # fired on 6, and TWO of them are exactly where the owner heard artifacts
    # by ear: v18 at 2:11 ("weird sound before 'and to rule the day'") and v21
    # at 2:35 ("weird whirr"). That is the signal worth acting on.
    if _eos_watcher.hits:
        flagged = {str(k): sorted(set(v)) for k, v in sorted(_eos_watcher.hits.items())}
        with open(str(json_file).replace(".json", ".eos.json"), "w",
                  encoding="utf-8") as f:
            json.dump(flagged, f, separators=(",", ":"))
        suspect = sorted(k for k, v in _eos_watcher.hits.items()
                         if "token_repetition" in v or "alignment_repetition" in v)
        if suspect:
            print(f"    ⚠ repetition-flagged verses: "
                  f"{', '.join(str(k + 1) for k in suspect)}")
    # ★ THE GATE'S RECORD — narration/<set>/<b>/<c>.qa.json. One file per
    # chapter with every take's verdict, so a repair queue is built from these
    # (qa_rerender_queue.py --qa / render_preflight.py report) with ZERO
    # re-sweeping, and "unjudged" is written down instead of vanishing.
    # ⚠ upload_narration.py excludes *.qa.json; keep it that way.
    if gate_log:
        qa = {"gate_version": 1,
              "judged": len(gate_log),
              "redrawn": sorted(v for v, g in gate_log.items() if len(g["attempts"]) > 1),
              "failing": {str(v): g["reasons"] for v, g in gate_log.items()
                          if g["reasons"] and g["reasons"] != ["asr-unavailable"]},
              "unjudged": sorted(v for v, g in gate_log.items()
                                 if any("asr-unavailable" in a["reasons"]
                                        for a in g["attempts"])),
              "gate": {str(v): g for v, g in gate_log.items()}}
        with open(str(json_file).replace(".json", ".qa.json"), "w",
                  encoding="utf-8") as f:
            json.dump(qa, f, separators=(",", ":"), ensure_ascii=False)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate per-verse Bible narration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--lang", required=True,
                        choices=list(LANG_CONFIG.keys()),
                        help="Language/translation code")
    parser.add_argument("--book", type=int, help="Book index (0-65)")
    parser.add_argument("--books", type=str, default=None,
                        help="Ordered book spec, e.g. '1,39-65,2-38' — renders "
                             "in THIS order (skips existing). Overrides the "
                             "default sweep; lets you prioritise, e.g. NT first.")
    parser.add_argument("--chapter", type=int, help="Chapter index (0-based)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    parser.add_argument("--all-books", action="store_true",
                        help="For 'en', generate ALL 66 books")
    args = parser.parse_args()

    cfg = LANG_CONFIG[args.lang]

    if cfg["engine"] in ("kokoro", "bark") and not Path(KOKORO_PYTHON).exists():
        print(f"ERROR: Kokoro venv not found at {KOKORO_PYTHON}", file=sys.stderr)
        sys.exit(1)

    if cfg["engine"] == "chatterbox":
        # Fail now, not 20 minutes into a run.
        if not Path(cfg["voice"]).exists():
            print(f"ERROR: reference recording not found: {cfg['voice']}",
                  file=sys.stderr)
            sys.exit(1)
        try:
            import chatterbox  # noqa: F401
        except ImportError as e:
            print(f"ERROR: cannot import chatterbox ({e}).\n"
                  "  This engine runs IN-PROCESS and needs its venv:\n"
                  "  tools\\.chatterbox_venv\\Scripts\\python.exe tools/narrate.py "
                  f"--lang {args.lang}", file=sys.stderr)
            sys.exit(1)
        dev = os.environ.get("CHATTERBOX_DEVICE", "cuda")
        print(f"Chatterbox | voice: {Path(cfg['voice']).name} | "
              f"lang {cfg['language_id']} | cfg_weight {cfg['cfg_weight']} "
              f"exaggeration {cfg['exaggeration']} | device {dev}")

    if cfg["engine"] == "cosyvoice3":
        # Fail now, not 20 minutes into a run.
        if not Path(COSYVOICE_MODEL).exists():
            print(f"ERROR: CosyVoice3 model not found at {COSYVOICE_MODEL}",
                  file=sys.stderr)
            sys.exit(1)
        if not Path(cfg["voice"]).exists():
            print(f"ERROR: reference recording not found: {cfg['voice']}",
                  file=sys.stderr)
            sys.exit(1)
        if not Path(COSYVOICE_REPO).exists():
            print(f"ERROR: CosyVoice repo not found at {COSYVOICE_REPO}\n"
                  "  git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git "
                  f"{COSYVOICE_REPO}", file=sys.stderr)
            sys.exit(1)
        # cosyvoice is NOT pip-installed — it lives in the cloned repo and only
        # reaches sys.path inside _get_cosyvoice(). Mirror that here so the
        # preflight tests what will actually happen.
        sys.path.insert(0, f"{COSYVOICE_REPO}/third_party/Matcha-TTS")
        sys.path.insert(0, COSYVOICE_REPO)
        try:
            import cosyvoice  # noqa: F401
        except ImportError as e:
            print(f"ERROR: cannot import cosyvoice ({e}).\n"
                  "  This engine runs IN-PROCESS and needs the cosyvoice venv:\n"
                  "  tools\\.cosyvoice_venv\\Scripts\\python.exe tools/narrate.py "
                  f"--lang {args.lang}", file=sys.stderr)
            sys.exit(1)
        styles = sorted({cfg.get("book_styles", {}).get(b, RU_DEFAULT_STYLE)
                         for b in range(len(load_bible(args.lang)))})
        print(f"CosyVoice3 | voice: {Path(cfg['voice']).name} | styles: {', '.join(styles)}")

    books = load_bible(args.lang)
    print(f"Loaded {cfg['asset']} ({len(books)} books)")

    if args.books is not None:
        # Ordered spec like "1,39-65,2-38": explicit priority order, deduped
        # keeping first occurrence. Skip-existing still applies per chapter.
        book_range = []
        for tok in args.books.split(","):
            tok = tok.strip()
            if not tok:
                continue
            if "-" in tok:
                a, b = tok.split("-")
                book_range.extend(range(int(a), int(b) + 1))
            else:
                book_range.append(int(tok))
        seen = set()
        book_range = [b for b in book_range if not (b in seen or seen.add(b))]
    elif args.book is not None:
        book_range = [args.book]
    elif args.all_books or cfg["default_books"] is None:
        book_range = list(range(len(books)))
    else:
        book_range = cfg["default_books"]

    total_chapters = 0
    for b in book_range:
        if b < len(books):
            if args.chapter is not None:
                total_chapters += 1
            else:
                total_chapters += len(books[b]["chapters"])
    print(f"Generating {len(book_range)} books, {total_chapters} chapters")
    print(f"Output: {OUTPUT / args.lang}\n")

    done = 0
    failed = 0
    for book_idx in book_range:
        if book_idx >= len(books):
            continue
        book_name = BOOK_NAMES[book_idx] if book_idx < len(BOOK_NAMES) else f"Book{book_idx}"
        n_ch = len(books[book_idx]["chapters"])
        print(f"\n=== {book_name} ({n_ch} chapters) ===")

        if args.chapter is not None:
            ch_range = [args.chapter]
        else:
            ch_range = range(n_ch)

        for ch in ch_range:
            ok = narrate_chapter(args.lang, book_idx, ch, books,
                                 force=args.force, dry_run=args.dry_run)
            if ok:
                done += 1
            else:
                failed += 1

    print(f"\nDone: {done} chapters generated, {failed} failed")
    print(f"Output: {OUTPUT / args.lang}")


if __name__ == "__main__":
    main()
