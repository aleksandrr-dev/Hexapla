# Hexapla — project context for Claude sessions

Offline parallel Bible app for Android. Kotlin + Jetpack Compose, single
module, no backend, no analytics. Owner: Aleksandr Ratchkov
(aleksratchkov@gmail.com; GitHub aleksandrr-dev). Mission: evangelism —
maximize reach, keep everything free, nothing locked, collect no data.

## Build

- JAVA_HOME is NOT on PATH in shells predating 2026-07-06; use
  `C:\Program Files\Android\Android Studio\jbr` (user env var is set).
- AGP 9.2.1 / Gradle 9.4.1 / Kotlin 2.3.21 (built-in Kotlin — no
  kotlin-android plugin) / Compose BOM 2024.10 / minSdk 26 / targetSdk 35.
  Gradle 9.6 works too (was rolled back only for reproducibility).
- **Product flavors** (dimension "distribution"):
  - `play` — Google Play. `EXTERNAL_DONATIONS=false`; R8 strips the ЮMoney
    donation path entirely (verified absent from dex).
  - `rustore` — RuStore + direct APK. External ЮMoney donation link shows
    when Play Billing is unavailable.
- Commands: `./gradlew bundlePlayRelease` (Play AAB),
  `./gradlew assembleRustoreRelease` (RuStore APK).
- Signing: `keystore.properties` in repo root (gitignored) points to the
  keystore in the owner's Documents folder. Play uses Play App Signing
  (our key = upload key). NEVER commit keys. versionCode: next is 3;
  bump for every store update.

## Store status (as of 2026-07-08)

- **RuStore**: LIVE — 1.1.1 (code 3) approved; 1.1.2 (code 4, adds QR share
  screen) submitted. Every upload re-asks the Safety form — answers are at
  the top of `store-assets/STORE_LISTING.md`. Update reviews ≈ a day.
- **Google Play**: closed testing (Alpha) — personal account, so production
  needs 12 testers × 14 continuous days (started ~2026-07-07). Upload
  1.1.2 play AAB to the closed track if not yet done. IARC done (purchases
  answered NO — tip products deliberately NOT created so Brazil rates
  Livre; tips exist only in code). Target audience 13+, no ads/ad-ID/health.
  Third-party store syndication: publish-all. Play uses Play App Signing.
- **Landing page** (what the in-app QR encodes, update as stores go live):
  https://aleksandrr-dev.github.io/Hexapla/ — buttons: RuStore (live),
  Play (marked "скоро", flip when production approves), direct APK via
  GitHub releases/latest (`gh release create vX.Y.Z <apk>` each release).
- Privacy policy: https://aleksandrr-dev.github.io/Hexapla/PRIVACY.html
- Listing texts (5 languages) + screenshot order: `store-assets/STORE_LISTING.md`.
- **Next versionCode: 5.**

## Architecture notes (beyond README)

- `ReadingService`: foreground media service. Two backends — TTS (per-verse
  feeding; NEVER pre-queue a chapter, engines drop utterances while loading
  a language) and MediaPlayer for LibriVox sections (`assets/audio_index.json`,
  50 books covered; missing books fall back to TTS). Music bed rotates
  through `assets/music/` (Kevin MacLeod CC-BY, perceptual x² volume curve).
  Settings are observed live via Store.settings collect in onCreate.
- Scroll-to-verse: ONE snapshotFlow collector in ReaderScreen owns all
  scrolling (verse jumps beat chapter-top resets). Do not reintroduce
  split effects — they race (bug fixed twice).
- Highlights use an optimistic `mutableStateMapOf` mirror (`liveHighlights`)
  — DataStore flow emissions alone did not recompose lazy items reliably.
- Verse text pipeline strips `{...:...}` translator margin notes (colon =
  note, no colon = supplied words, keep those) in BibleRepo.parseAsset.
- Strong's (`en_kjv_strongs.json` + `strongs_lexicon.json`), red letters
  (`red_letters.json`), book cover art (`assets/bookart/<bookIdx>.webp`,
  49 books, Doré + Schnorr, else generated title-page in BookArt.kt).
- Widget shows daily verse + book art; deterministic date-seeded pick.

## Data pipelines (tools/)

Python scripts (need `pillow`, `pymupdf`; ffmpeg via winget for audio):
- `convert_scrollmapper.py` — scrollmapper JSON → app bible asset format.
- `convert_strongs.py` / `convert_lexicon_os.py` — Strong's tagged KJV
  (kaiserlik/kjv, broken JSON handled by regex extraction) + Open
  Scriptures lexicon (CC-BY-SA).
- `build_audio_index2/3.py` — LibriVox section index from archive.org
  (validates chapter coverage; only complete books admitted).
- `build_bookart.py` / `build_bookart2.py` — Doré (Gutenberg #8710) and
  Schnorr (Wikimedia, plate index transcribed from Heidelberg scans)
  cover art. Plate→book mappings are curated in the scripts.
- `make_widget_shot.py` — store screenshot renderer.

## Roadmap (agreed with owner)

0. ~~Tester requests~~ DONE 2026-07-08 (in versionCode 5, not yet released):
   a) ~~Webster Bible 1833~~ shipped (`wbt`, en_webster.json; converter now
      strips scrollmapper's [supplied-word] brackets; book names normalized
      to KJV style). Still ask tester if he also meant the 1828 Dictionary
      → park as v1.3 tap-a-word idea.
   b) ~~1-year chronological plan~~ shipped ("chrono" in Plans; order lives
      in ChronoOrder.kt, curated + verified by tools/build_chrono_plan.py,
      which documents every placement decision and asserts all 1189 canon
      chapters appear exactly once and the anchor verses say what the
      placements assume. KJV numbering; LXX psalters remapped like
      chapterIndexFor; Heb Joel 4 special-cased; partial texts filtered).
1. ~~QR share screen~~ DONE (Settings → Share this app; encodes landing page).
2. IzzyOnDroid listing (repo is public; low effort).
3. v1.2 flagship: **original-language interlinear** (word-tagged WLC/Byz
   via Open Scriptures morphology → tap word → Strong's popup).
4. v1.3: self-generated narration (Kokoro/Piper, host on archive.org) —
   fills 22 KJV books LibriVox lacks + enables Russian audio.
5. iOS port = separate v2.0-scale project (Kotlin/Compose Multiplatform;
   Swift needed for audio/TTS/widget/notifications; Mac + Apple $99/yr).
6. Maybe: fonts (Literata/EB Garamond), music download-on-demand
   (APK 39→23 MB), rotating covers, `foss` flavor for F-Droid proper.

## Owner preferences

- KJV/TR textual tradition only — no Critical Text translations, ever.
- All content must be legally clean: public domain or CC with attribution
  (attribution lives in `sources_text` strings, all 5 locales).
- Voice cloning of real people / game characters: refused once (Joshua
  Graham), keep refusing; owner accepted reasoning.
- Tests changes on his physical phone and reports bugs precisely —
  believe his repro reports even when the code "looks right."
