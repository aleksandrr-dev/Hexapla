# Self-generated narration — execution plan (roadmap item 4)

Planned 2026-07-13 (Fable session, full context in CLAUDE.md). This
document is self-contained: an executing session (Sonnet/Haiku) should
be able to work from it plus CLAUDE.md alone. Escalation points where
a stronger model or the owner must decide are marked ⚠ GATE.

## Goal

Generated audio narration hosted on archive.org, served through the
existing per-section download flow (ReadingService MediaPlayer backend,
see audio_index.json), for:
1. RUSSIAN — the whole Synodal (no human narration exists in-app).
2. ENGLISH — the 22 KJV books LibriVox lacks (audio_index.json covers
   50 of 66; the missing books currently fall back to TTS).
Later, same pipeline: Tamil, German, Spanish etc. if voice quality passes.

## Engines (verify before building — field moves fast)

- ENGLISH: Kokoro-82M (Apache 2.0). Quality reference point.
- RUSSIAN: Kokoro has NO Russian. Default candidate: Piper
  (rhasspy/piper, MIT engine) voices ru_RU-{ruslan,dmitri,denis,irina}.
  ⚠ GATE (licensing): each Piper VOICE has its own training-data
  lineage in its model card — verify the chosen voice's dataset
  permits redistribution of generated audio in a free app BEFORE
  generating anything public. Same discipline as text sources
  (see the Dvoretsky gate in CLAUDE.md). Silero is CC BY-NC — ruled
  out (NC, same reason as Zhuromsky). Do a fresh sweep for newer
  Apache/MIT Russian TTS before settling on Piper.
- ⚠ GATE (owner): generate Псалом 22 + Иоанна 1 in each candidate
  Russian voice; owner picks by ear. Prefer calm, unhurried, male.

## Pipeline (tools/narrate.py, one script, per-language config)

1. TEXT PREP: read the translation asset (ru_synodal.json / en_kjv.json)
   via the same JSON shape all tools use. Per verse: strip nothing for
   ru (Synodal has no {} notes); for KJV strip {...} margin notes the
   same way BibleRepo.parseAsset does (colon = note, drop; no colon =
   supplied word, keep). Expand digits where the engine mishandles them.
2. RUSSIAN STRESS DICTIONARY: biblical proper names get wrong stress
   (Авваку́м, Мелхиседе́к, Вирсави́я). Build tools/ru_stress.py: a curated
   name→accented-form table applied as text preprocessing. Start with
   the most frequent ~200 OT/NT names (frequency-count them from the
   asset first); extend after listening. ⚠ GATE (quality): the table
   itself is judgment work — have a strong model draft it, owner/native
   spot-check.
3. SYNTHESIS PER VERSE (not per chapter): synth each verse to wav,
   record duration, concatenate with ~600ms gaps (~900ms after
   paragraph-ish breaks is a later nicety). Per-verse synthesis gives
   exact cumulative offsets -> the timing index (feature win: verse
   highlighting + tap-to-seek during narrated audio, which LibriVox
   can't do — the app currently disables highlighting for narration).
4. POST: ffmpeg loudnorm (two-pass, target I=-19 LUFS mono), encode
   Opus 32kbps mono in .ogg (MediaPlayer supports ogg/opus since API 21;
   minSdk is 26 — fine). One file per chapter.
5. SIZES: whole Synodal ≈ 90-100 h ≈ 1.2-1.5 GB opus. 22 KJV books
   ≈ 30 h ≈ 450 MB. Piper is faster than realtime on CPU.
6. UPLOAD: archive.org via `ia` CLI, one item per language
   (e.g. hexapla-audio-ru), files ru/<bookIdx>/<chapter>.ogg.
   Metadata: PD/generated, link the app. Keep the upload script in
   tools/ (upload_narration.py).
7. INDEX: assets/audio_index_gen.json:
   { "<lang>": { "<bookIdx>": { "url": ..., "chapters": { "<ch>":
     { "file": ..., "offsets": [ms per verse] } } } } }
   (exact shape negotiable — design to be read by AudioRepo next to
   audio_index.json; keep verse offsets so the service can highlight).

## App changes (Kotlin, modest)

- ReadingService/AudioRepo: narration source selection becomes
  per-translation-language: kjv -> LibriVox where covered, generated
  for the 22 gap books; syn -> generated ru. Existing download-and-
  cache flow (per section) carries over; generated files are per
  chapter (smaller than LibriVox sections — simpler, keep per-chapter).
- Verse highlighting during narration: feed the offsets timing index
  into the existing Playback.verse mechanism (the TTS path already
  drives per-verse highlight; MediaPlayer path gains a position poll
  against offsets). Disable word-level highlight (verse-level only).
- Settings copy: audio_title/audio_note currently say "(KJV)" and
  "human narration from LibriVox" — reword ×13 locales to cover
  generated narration + credit (e.g. "and computer-narrated audio
  for books/languages without a recording"). Keep the LibriVox credit.
- sources_text ×13: add engine/voice attribution per its license.
- ⚠ GATE (review): the ReadingService diff is concurrency-sensitive
  (see CLAUDE.md architecture notes: never pre-queue TTS, one scroll
  collector, wakelock history). Have a strong model review the final
  service diff before release.

## Rollout

1. PoC: John 1 (ru) in 2-3 candidate voices -> owner listens (⚠ GATE).
2. Pilot: 4 Gospels ru (~9 h audio) end-to-end incl. app playback +
   highlight on-device.
3. Batch: NT ru -> Psalms ru -> OT ru; then the 22 KJV books (Kokoro).
4. Release as 1.4.x with store-notes headline "аудио на русском".

## Definition of done (per language)

- Every chapter of the target set plays from archive.org after a cold
  install with airplane-mode-then-online test.
- Verse highlight tracks within ±1 verse through a whole chapter.
- Spot-listen list: Пс 22/50/90, Ин 1, Быт 1, 1 Пар 1 (name-heavy),
  Откр 13 (numbers) — no mangled names on the curated list, no digit
  misreads.
- sources_text/audio_note updated ×13; lint at baseline; CLAUDE.md
  updated with the archive.org item ids and voice/license verdicts.
