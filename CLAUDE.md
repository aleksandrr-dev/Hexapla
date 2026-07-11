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

## Store status (as of 2026-07-10)

- **RuStore**: LIVE — 1.2.0 (code 5) approved 2026-07-09; 1.3.0 (code 6)
  submitted same day together with the new store title «Гексапла —
  параллельная Библия» (code 4 was never actually submitted there — the
  "1.1.2" draft turned out empty). Every upload re-asks the Safety
  form — answers at the top of `store-assets/STORE_LISTING.md`. Gotcha:
  a new version draft does NOT inherit media — re-upload icon
  (`store-assets/icon_512_store.png`) + 6 screenshots (5 JPGs in
  `store-assets/rustore/`, order 120537, 120212, 120307, 120326, 120426,
  then `screenshot_widget.png`); the browser extension cannot upload
  local files, the owner picks them in the native dialog. Update
  reviews ≈ a day.
- **Google Play**: closed testing (Alpha) — personal account, so production
  needs 12 testers × 14 continuous days. 1.3.0 (code 6) is the current
  closed-track release (in review as of 2026-07-10); see the detailed
  Play notes below. IARC done (purchases
  answered NO — tip products deliberately NOT created so Brazil rates
  Livre; tips exist only in code). Target audience 13+, no ads/ad-ID/health.
  Third-party store syndication: publish-all. Play uses Play App Signing.
- **Landing page** (what the in-app QR encodes, update as stores go live):
  https://aleksandrr-dev.github.io/Hexapla/ — buttons: RuStore (live),
  Play (marked "скоро", flip when production approves), direct APK via
  GitHub releases/latest (`gh release create vX.Y.Z <apk>` each release).
- Privacy policy: https://aleksandrr-dev.github.io/Hexapla/PRIVACY.html
- Listing texts (5 languages) + screenshot order: `store-assets/STORE_LISTING.md`.
- **Google Play (2026-07-08)**: closed track now has 1.2.0 (code 5),
  uploaded same day as 1.1.2 (code 4); the 14-day tester clock
  (started ~2026-07-07) keeps running across uploads to the same track.
- **GitHub release v1.2.0** published (releases/latest serves the
  1.2.0 RuStore-flavor APK for the landing page's direct-APK button).
- **1.3.0 (code 6)** (era headings + 1828 dictionary): submitted to
  RuStore + GitHub release v1.3.0 published 2026-07-09. Play: 1.3.0
  uploaded to the closed track and **submitted for review 2026-07-10**
  (status "In review"). Removing the auto-carried previous bundle
  (code 2) from the release's "Previous release → Included" section was
  needed — otherwise Play errors "APK completely shadowed by higher
  version code". Release notes were refreshed (were still the "First
  release / 12 translations" text).
- **Play production gate — tester count is the blocker, not the clock:**
  as of 2026-07-10 only **8 of 12 required testers are opted in**. The
  14-day countdown only advances on days with ≥12 opted-in testers, so
  it is effectively **not running** until 4 more testers join (via the
  closed-test opt-in link, each on their own Google account).
- **Play store listing refreshed + submitted for review 2026-07-10:**
  all 5 languages — app name → the number-free «Parallel Bible» titles
  (Hexapla — Parallel Bible / Гексапла — параллельная Библия / Biblia
  paralela / Parallelbibel / Bible parallèle), plus short + full
  descriptions updated to the current "13 translations" copy from
  `STORE_LISTING.md`. Was previously the stale "6 languages / 12
  translations" text (Play listing had never been refreshed, only the
  repo file). Edit at Grow users → Store presence → Store listings →
  Default store listing → Edit.
- **1.4.0 (code 7) built + staged 2026-07-11, re-cut same day to add
  the Nordics** (interlinear; +Almeida, Diodati, Meiji, CUV×2 scripts,
  Karl XII 1703, Dansk 1819; −BBE; Play empty-Support fix):
  `C:\Projects\Hexapla-1.4.0-rustore.apk` / `-play.aab`. 18 translations
  / 14 languages; STORE_LISTING.md fully refreshed incl. interlinear line.
- **Translation watch list** (all deity-verse-gated, pipeline ready):
  Guðbrandsbiblía 1584 (Icelandic) — transcription likely exists in the
  Árnastofnun Textasafn corpus; owner to email arnastofnun@arnastofnun.is
  (corpus editor: Þórdís Úlfarsdóttir, disa@hi.is) + hib@biblian.is
  (Icelandic Bible Society; also has Viðeyjarbiblía 1841 as fallback ask).
  Korean — no PD TR text exists (개역한글 fails 1 Tim 3:16 with 그는;
  한글킹제임스/흠정역 copyrighted). LXX apocrypha — no clean-licensed
  tagged text (CATSS restrictive).
- **1.4.0 submitted 2026-07-11**: owner uploaded + submitted for review
  (Play: release to closed track + full listing localization in one
  batch — 13 listing entries / 10 languages incl. pt-BR/pt-PT, es-419/
  es-US, fr-CA, zh-CN/TW/HK, ja; localized feature headers for all 10
  languages via tools/make_feature_graphic.py; CJK reader screenshots
  via tools/make_reader_shot.py). RuStore 1.4.0 confirmed submitted
  same day. GitHub release v1.4.0 published 2026-07-11.
- **Next versionCode: 8** (planned 1.4.1: UI localization for the new
  reading languages, then automated localized screenshots).**

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
      to KJV style). Tester confirmed he also wanted the 1828 Dictionary —
      ~~tap-a-word~~ shipped in-tree for versionCode 6: Webster1828 in
      Bible.kt (lazy 13 MB asset, +5.5 MB APK; archaic-form lemmatizer
      mirrored in tools/check_1828_coverage.py, 95.9% token coverage,
      misses ≈ proper names), converter tools/convert_webster1828.py from
      the DataWar/1828-dictionary MySQL dump (mshaffer digitization, PD).
      Off by default; toggle under Strong's. Tap word → definition dialog
      (word taps and Strong's superscript numbers are separate targets).
   b) ~~1-year chronological plan~~ shipped ("chrono" in Plans; order lives
      in ChronoOrder.kt, curated + verified by tools/build_chrono_plan.py,
      which documents every placement decision and asserts all 1189 canon
      chapters appear exactly once and the anchor verses say what the
      placements assume. KJV numbering; LXX psalters remapped like
      chapterIndexFor; Heb Joel 4 special-cased; partial texts filtered).
      Era headings (18, ×5 locales) over the chrono day list added
      post-1.2.0 — in-tree for the NEXT release (versionCode 6).
1. ~~QR share screen~~ DONE (Settings → Share this app; encodes landing page).
1b. **Translation lineup for v1.4** (all deity-verse-tested, see commits):
   BBE removed (Critical Text — failed every litmus verse). Added:
   Almeida Bíblia Livre TR (pt, scrollmapper PorBLivreTR, passes all 8),
   明治元訳 Meiji Motoyaku 1880/87 (ja, Wikisource NT scrape via
   tools/build_meiji_nt.py + scrollmapper Meiji OT; TR-core, committee
   omissions documented in commit), 和合本 CUV 1919 (zh, both scripts —
   Simplified derived from the PD Traditional text via OpenCC t2s in
   tools/convert_cuv.py, avoiding the UBS 1988 punctuation layer).
   Now 15 translations / 11 languages; zh default picks script by
   locale (Hant/TW/HK/MO → traditional).
2. IzzyOnDroid listing (repo is public; low effort).
3. ~~Original-language interlinear~~ shipped in-tree for v1.4/code 7:
   tap any word in grc/wlc → Strong's entry + decoded morphology
   (Robinson for Greek, OSHM for Hebrew; decoders in Interlinear.kt).
   Data via tools/build_interlinear.py from openscriptures/morphhb
   (CC-BY) + byztxt csv-unicode (PD); per-verse text-verified alignment
   with difflib recovery for split names/enlarged letters — 100% of
   verses tagged both testaments; word-level 100% Greek, 98.0% Hebrew
   (the rest have no Strong's number in morphhb itself). Tokenizer
   contract proven identical Java-vs-Python over all 31,166 tagged
   verses (scratch TokCheck). No settings toggle — always
   active on the original texts. +1.7 MB compressed in APK.
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
