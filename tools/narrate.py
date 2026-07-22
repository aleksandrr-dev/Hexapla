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

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
OUTPUT = Path("C:/Projects/Hexapla-releases/narration")
KOKORO_PYTHON = str(HERE / ".kokoro_venv" / "Scripts" / "python.exe")

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
    "tyn": {
        "asset": "en_tyndale.json",
        "engine": "kokoro",
        "voice": "am_adam",
        "strip_notes": True,
        "default_books": None,
        "normalizer": "tyndale",
    },
    "wyc": {
        "asset": "enm_wycliffe.json",
        "engine": "kokoro",
        "voice": "am_adam",
        "strip_notes": False,
        "default_books": None,
        "normalizer": "wycliffe",
    },
    "ylt": {
        "asset": "en_ylt.json",
        "engine": "kokoro",
        "voice": "am_adam",
        "strip_notes": True,
        "default_books": None,
        "normalizer": None,
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
        book = book_name or f"Bok {book_idx + 1}"
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


def normalize_text(text, normalizer_name):
    """Apply language-specific text normalization for TTS."""
    if normalizer_name is None:
        return text
    if normalizer_name == "ru_variants":
        return strip_ru_variant_numbers(strip_ru_markup(text))
    if normalizer_name == "cu_digits":
        return normalize_cu_digits(text)
    if normalizer_name == "ru_stress":
        # ⚠ CORRUPTS TEXT — see the note in LANG_CONFIG["ru"] and
        # tools/audit_ru_stress.py. Do not use until the table is rebuilt.
        import ru_stress
        return strip_ru_variant_numbers(ru_stress.apply_stress(text))
    if normalizer_name in ("geneva", "tyndale", "wycliffe"):
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


def synthesize_kokoro(text, voice, output_wav):
    """Synthesize with Kokoro via the sandboxed Python 3.12 venv."""
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


def synthesize_chatterbox(text, cfg, output_wav):
    """Synthesize one verse with Chatterbox Multilingual (zero-shot clone,
    no transcript needed). Params come from the ear-test-picked config."""
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

    rates = [r for r in (_verse_rate(verses[i], d)
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
        rate = _verse_rate(verses[i], dur)
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
            alt_rate = _verse_rate(verses[i], alt_dur)
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


def synthesize_verse(text, lang, temp_dir, verse_idx, book_idx=None):
    """Synthesize one verse. Returns (wav_path, duration_ms) or (None, 0).

    book_idx selects the per-book narration style (cosyvoice3 only).
    """
    if not text or not text.strip():
        return None, 0

    cfg = LANG_CONFIG[lang]
    wav_path = Path(temp_dir) / f"verse_{verse_idx:04d}.wav"

    if cfg["engine"] == "kokoro":
        ok = synthesize_kokoro(text, cfg["voice"], str(wav_path))
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
            for i, v_text in enumerate(verses):
                wav_path, dur = synthesize_verse(v_text, lang, tmp, i, book_idx)
                pairs.append((wav_path, dur))
            pairs = repace_outliers(verses, pairs, lang, tmp, book_idx)
        except Exception as e:
            print(f" FAILED (duration: {e})")
            return False

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

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({"offsets": offsets}, f, separators=(",", ":"))

    size_kb = ogg_file.stat().st_size // 1024
    print(f" OK ({size_kb} KB)")
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

    if args.book is not None:
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
