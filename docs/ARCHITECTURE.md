# Hexapla — architecture landmines

Why this file exists: these are hard-won "do not reintroduce this bug" notes.
Each one only matters when you touch that area, so they were costing context in
every session. `CLAUDE.md` keeps a one-line index that names the symptom; the
full reasoning is here, one hop away.

⚠ **If you are editing ReaderScreen, the widget, notifications, Scaffold layout,
the audio path or the verse-text parser, read the matching entry BEFORE you
start.** Several of these bugs were fixed twice.

# ── MOVED OUT OF CLAUDE.md, 2026-08-28 (context budget) ──

Verbatim. Nothing was changed.

## Architecture notes (beyond README)


- `ReadingService`: foreground media service, three backends — **TTS**
  (per-verse feeding; ⚠ NEVER pre-queue a chapter, engines drop utterances
  while loading a language), **LibriVox** sections via `assets/audio_index.json`
  (50 books, download+cache), and **self-generated per-chapter narration** via
  `assets/audio_index_gen.json` (built by `tools/build_audio_index_gen.py`).
  Generated audio downloads-and-caches like LibriVox; download-fail or
  unrendered → TTS fallback. Verse-following and word-level highlighting work on
  recorded audio (per-verse `o` offsets in the index, per-word `.w.json`
  sidecars from `tools/align_words.py`); chapters without a sidecar degrade to
  verse-level.
  ▶ **The audio path is INDEX-DRIVEN: a new narration set needs no Kotlin
  change.** How it was built, the sets that shipped on it, and the recurring
  gotchas: `docs/NARRATION.md`.
  ⚠⚠ **`internetarchive.upload(metadata=…)` DOES NOTHING ON AN EXISTING ITEM** —
  Karl XII finished complete and stayed publicly titled «(pågår / in progress)»
  behind a clean "0 failed". `upload_narration.py` now calls `modify_metadata()`
  and re-reads the live title. Any set published in stages hits this.
- ★ **PendingIntent requestCodes MUST STAY DISTINCT.** PendingIntent identity
  IGNORES extras, so the widget, the media notification and the daily reminder —
  all previously at requestCode 0 — were literally the same object, and the
  reminder's `FLAG_UPDATE_CURRENT` rewrote the others' extras. Symptom: the
  widget read "Continue reading: Exodus 20" and opened Psalms 41. Allocation:
  **1 = widget continue · 2 = media notification · 3 = daily reminder ·
  4 = widget verse**. Any new PendingIntent needs its own code.
- **Deep-link extras are consumed in `openFromIntent`.** Android replays a
  task's original Intent on every recreation, so an uncleared deep link re-fires
  forever — including from the app drawer. Second half of the Psalms-41 bug.
- Scroll-to-verse: ONE snapshotFlow collector in ReaderScreen owns all
  scrolling (verse jumps beat chapter-top resets). Do not reintroduce split
  effects — they race (bug fixed twice).
- Highlights use an optimistic `mutableStateMapOf` mirror (`liveHighlights`) —
  DataStore flow emissions alone did not recompose lazy items reliably.
- ⚠ **An inner Scaffold under `AppScaffold` must set
  `contentWindowInsets = WindowInsets(0)`.** AppScaffold already applies the
  navigation-bar inset to the NavHost; adding another reserves the nav-bar
  height TWICE — text clipped mid-line with a black bar below.
- Bottom navigation bar: content height pinned to **64.dp** with the system
  inset moved outside the bar (`navigationBarsPadding()`); M3's 80dp default
  plus inset was too tall on 3-button navigation.
- Widget: daily verse + book art, deterministic date-seeded pick. Tap targets —
  **quote / reference / cover art → the linked verse** (a PEEK, `AppState.peek()`,
  which suppresses `setLastPosition` AND `setLastVerse`, the latter because the
  verse write runs on a 500 ms scroll debounce and would otherwise undo the
  chapter guard one scroll at a time); **everything else → the saved spot**
  (`EXTRA_PEEK=false`).
  ⚠ Peek is deliberately INVISIBLE. The owner asked for a "back to your spot"
  bar and then rejected it as obtrusive; `PeekReturnBar` and `reader_back_to`
  are deleted from all locales. Do not reintroduce visible chrome without asking.
- Verse text pipeline strips `{...:...}` translator margin notes (colon = note,
  no colon = supplied words, keep those) in `BibleRepo.parseAsset`.
- Strong's (`en_kjv_strongs.json` + `strongs_lexicon.json`), red letters
  (`red_letters.json`), book cover art (`assets/bookart/<bookIdx>[_N].webp`,
  54 of 83 books; 9 rotate daily, else a generated title page in `BookArt.kt`).
  ★ **THE 29 BOOKS WITHOUT ART ARE DONE BEING HUNTED — do not re-search.** The
  reason is structural (17th-c. picture Bibles illustrate NARRATIVE, so epistles
  were never given plates). Audit: `research/bookart_gap_sources_2026-08-10.md`.
- ⚠ **The owner's phone runs a rustore DEBUG build.** A release APK is signed
  with the upload key and will NOT install over it
  (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`). Use `assembleRustoreDebug` for device
  testing. adb lives at `$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe`; in
  Git Bash prefix device-path commands with `MSYS_NO_PATHCONV=1` or `/sdcard/...`
  is mangled.
