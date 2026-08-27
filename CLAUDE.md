# Hexapla — project context for Claude sessions

Offline parallel Bible app for Android. Kotlin + Jetpack Compose, single
module, no backend, no analytics. Owner: aleksandrr-dev (GitHub).
Mission: evangelism — maximize reach, keep everything free, nothing locked,
collect no data.

▶ **THIS FILE IS AUTO-LOADED INTO EVERY SESSION, SO IT HOLDS ONLY WHAT IS TRUE
NOW AND NEEDED OFTEN.** A completed record belongs in a topic doc; a ⚠ that can
still bite belongs here or is pointed at from here — never silently dropped.
Condensed 2026-08-09 (1,636 lines → topic docs) and again 2026-08-25, when it
was costing ~8k tokens of every first turn. **Nothing was deleted either time:**
the 08-25 move appended verbatim blocks under a `── MOVED OUT OF CLAUDE.md ──`
banner at the end of `docs/RELEASE_HISTORY.md` and `docs/NARRATION.md`.

## Build

- JAVA_HOME is NOT on PATH in shells predating 2026-07-06; use
  `C:\Program Files\Android\Android Studio\jbr` (user env var is set).
- AGP 9.3.0 / Gradle 9.4.1 / Kotlin 2.3.21 (built-in Kotlin — no
  kotlin-android plugin) / Compose BOM 2024.10 / minSdk 26. Gradle 9.6 works
  too (rolled back only for reproducibility).
- **Product flavors** (dimension "distribution"):
  - `play` — Google Play. `EXTERNAL_DONATIONS=false`; R8 strips the ЮMoney
    donation path entirely.
  - `rustore` — RuStore + direct APK. External ЮMoney link shows when Play
    Billing is unavailable.
  ⚠⚠ **THE DONATION GREP NEEDS ITS POSITIVE CONTROL, EVERY RELEASE.** 0 on the
  Play artifact only means something because the same grep returns **1** on the
  RuStore one; **a 0/0 result means the grep is broken, not the build clean.**
  Paths differ: `classes*.dex` (APK) vs `base/dex/classes*.dex` (AAB).

      unzip -p <aab> "base/dex/classes*.dex" | grep -ac yoomoney   # must be 0
      unzip -p <apk> "classes*.dex"          | grep -ac yoomoney   # must be 1

  ▶ It exists because the play path silently regressed for five releases
  (1.4.0–1.5.1). Full story: `docs/RELEASE_HISTORY.md`.
- Commands: `./gradlew bundlePlayRelease` (Play AAB),
  `./gradlew assembleRustoreRelease` (RuStore APK),
  `./gradlew assembleRustoreDebug` (~20 s, for device testing).
- Signing: `keystore.properties` in repo root (gitignored) points to the
  keystore in the owner's Documents. Play uses Play App Signing (our key =
  upload key). NEVER commit keys.
- **versionCode 17 / 1.6.4 was uploaded to BOTH stores 2026-08-16. NEXT FREE
  versionCode IS 18.** Bump for every store update.
  ⚠⚠ **NEVER REBUILD A SHIPPED VERSION IN PLACE WITHOUT REFRESHING EVERY COPY
  OF IT.** 1.6.4 was legitimately rebuilt in place (it had not been public), but
  only the two stores were refreshed — the GitHub `releases/latest` asset stayed
  at the older build for 15 days, same version name, different binary, and the
  landing page's direct-APK button served it. Fixed 2026-08-25.
- ⚠⚠ **USE `Locale.forLanguageTag("sv")`, NOT `Locale.of("sv")`.** `Locale.of`
  is Java's official replacement but it is Java 19 = **API 36** against this
  app's **minSdk 26** — it compiles clean and crashes on essentially every real
  device. `forLanguageTag` is API 21+ and equivalent for plain language codes.
  (Bible.kt's 25 sites were converted and shipped in 1.6.4.)

## ⚠ WHERE THINGS ARE — read this before hunting through the repo

| you need | read |
|---|---|
| what is happening right now | **`SESSION_HANDOFF_2026-08-26-evening.md`** — the ONE current handoff |
| tomorrow's Play production application | `PLAY_PRODUCTION_2026-08-26.md` (self-contained) |
| adding/researching a translation, licence gates, dead ends | `docs/TRANSLATIONS.md` |
| touching a Bible asset — corruption, psalm titles, markup | `docs/ASSET_DEFECTS.md` |
| renders, GPU contention, the recycle and keepalive, the audio backends | `docs/NARRATION.md` |
| what shipped when, and why a behaviour changed | `docs/RELEASE_HISTORY.md` |
| the KJV re-render in the owner's voice | `tools/KJV_VOICE_RUNBOOK.md` |
| transcribing a Karl XII strip | `research/KXII_AGENT_BRIEF.md` — read it BEFORE touching a strip |
| what is actually running (live checks, not logs) | run **`/status`** (`.claude/skills/status/`) |
| adjudicating many diacritics/uncertain glyphs at once | `tools/contact_sheet.py` — tile the crops into ONE image; separate zoom reads cost ~8x more |
| verifying a finished transcription chunk | `tools/kxii_diff.py` — diffs against **kxii.se**, an independent witness. **0 model tokens.** ⚠ WITNESS ONLY, never a correction source: transcribe from the image first, diff after — that order is the legal position |
| finding where a word sits on a strip | `tools/kxii_locate.py` — Tesseract geometry over the cached TSV. **0 tokens, 0.28 s.** ⚠ never run Tesseract inline over many strips, it times out the session |

⚠⚠ **`research/`, `narration/`, `logs/`, `handoff-archive/` and every
`SESSION_HANDOFF_*.md` and `PLAY_*.md` are NOT IN THIS REPO.** They live in the
sibling working directory **`C:\Projects\Hexapla-releases\`** — untracked on
purpose (scans, renders and staged store artifacts are far too large to
version). Paths written as `research/…` throughout this file and the topic docs
are relative to THERE, not to the repo root. A session that greps the repo for
them finds nothing and can conclude the campaign docs were lost; they were not.

## ⚠ CURRENT STATE — read the handoff first

★ **EXACTLY ONE CURRENT HANDOFF** (owner, 2026-08-14). Predecessors were MOVED
to `C:\Projects\Hexapla-releases\handoff-archive\` — consult them only for the
history of a decision, never for current state. When you write a new handoff,
fold forward what is still live and archive the old one.

- **Transcription:** Karl XII 1703 apocrypha, currently Sirach. The resume
  pointer is the `Resume:` line at the top of `research/karlxii_sirach.md` —
  read it there, never from a handoff summary.
- **Next campaign after it:** the Icelandic **Þorláksbiblía 1644** (31,102
  verses). No blockers; brief with folio↔index navigation for all three
  volumes: `research/THORLAKS_CAMPAIGN.md`. The volunteer-overlap question is
  SETTLED (owner, 2026-08-10) — two Icelandic Bibles is the intended outcome.
  ⚠ The print splits KJV 1 Chr 4 at v24 and never re-syncs; **the marginal
  "Cap. N" is the authoritative numeral, NOT the big heading.** Evidence:
  `research/thorlaks_precampaign_checks.md`.
- ⚠⚠ **RUN THE CORPUS AUDIT BEFORE BELIEVING ANY COMPLETENESS CLAIM** —
  `tools/glen_corpus_audit.py`, `tools/thorlaks_corpus_audit.py`,
  `tools/karlxii_apoc_corpus_audit.py`. One of these exists because a chunk
  report claimed 572 transcribed verses while holding two on disk, and every
  per-chunk check passed it for three weeks.

## Store status

⚠ Live status only. Release history is in `docs/RELEASE_HISTORY.md`; translation
research and integration records are in `docs/TRANSLATIONS.md`.

- **RuStore**: LIVE. Latest uploaded **1.6.4 (code 17), 2026-08-16**. Store
  title «Гексапла — параллельная Библия».
  ⚠ Every upload re-asks the Safety form (answers at the top of
  `store-assets/STORE_LISTING.md`), and a new version draft does **NOT** inherit
  media — re-upload the icon (`store-assets/icon_512_store.png`) and 6
  screenshots (5 JPGs in `store-assets/rustore/`, order 120537, 120212, 120307,
  120326, 120426, then `screenshot_widget.png`). The browser extension cannot
  upload local files; the owner picks them in the native dialog. Review ≈ a day.
- **Google Play**: closed testing (Alpha). Latest uploaded **1.6.4 (code 17),
  2026-08-16**. Personal account, so production needs **12 testers × 14
  CONTINUOUS days** — one day below 12 opted-in testers restarts the count.
  ⚠ **Read the real figure off the Play Console; never compute the date here.**
  Play counts opted-in testers in its own timezone and has its own idea of when
  day 1 was. Application prepared for 2026-08-26 —
  see `PLAY_PRODUCTION_2026-08-26.md`.
  IARC done (purchases answered NO — tip products deliberately not created so
  Brazil rates Livre; tips exist only in code). Target audience 13+, no
  ads/ad-ID/health. Third-party syndication: publish-all. Play App Signing.
- **Landing page**: https://aleksandrr-dev.github.io/Hexapla/ (repo root
  `index.html`) — what the in-app QR encodes AND what the archive.org narration
  items link to. English first, Russian second on the same lines.
  ⚠ **PENDING PAGE UPDATES — owner, 2026-07-21: "once it's on Play Store
  officially, and F-Droid, we'll update it again."**
  (1) Play production approved → drop the `soon` class from the Play button
      (`.soon` = `opacity:.45; pointer-events:none`) and retitle it;
  (2) F-Droid/IzzyOnDroid live → ADD a fourth button (the `foss` flavor is
      already ready; IzzyOnDroid takes a released APK, F-Droid proper needs an
      fdroiddata MR with `gradle:[foss]`);
  (3) whenever the count changes, bump the page AND `store-assets/STORE_LISTING.md`
      together — they must agree.
  ⚠ The direct-APK button points at `releases/latest`, and the upload is always
  the **RuStore APK**, never the Play AAB.
  ⚠ **`gh release upload` run from a non-git directory prints "failed to run
  git" AND STILL EXITS 0.** Run it from the repo; verify by re-reading the
  asset size, never by the exit code.
- ✅ **COUNTS: DERIVE, NEVER HAND-COUNT — `python tools/count_translations.py`.**
  Translations = distinct TEXTS (two scripts of one translation count once — zh;
  original-language grc/wlc DO count). Languages = what a READER would name
  (Middle English folds into English; ancient languages count as their own).
  The in-app `welcome_tagline`, the landing page and the current release-notes
  block must agree; last verified together 2026-08-25.
- Privacy policy: https://aleksandrr-dev.github.io/Hexapla/PRIVACY.html
- Listing texts + screenshot order: `store-assets/STORE_LISTING.md`.
  ★ RELEASE-NOTES STANDARD (owner, 2026-07-23): "What's new" is kept there as a
  full Play-Console copy-paste block — EVERY listing locale in its own
  `<locale>…</locale>` tag, so the owner pastes the whole set at once.
  ▶ **Validate before pasting: `python tools/check_release_notes.py`** (locale
  set and ORDER match Play, every entry within the 500-char cap, exactly one
  release block above the descriptions). be/hy/iw/ta = best-effort, native
  review pending.

## Architecture notes (beyond README)

- `ReadingService`: foreground media service, three backends — **TTS**
  (per-verse feeding; ⚠ NEVER pre-queue a chapter, engines drop utterances
  while loading a language), **LibriVox** sections via `assets/audio_index.json`
  (50 books, download+cache), and **self-generated per-chapter narration** via
  `assets/audio_index_gen.json` (built by `tools/build_audio_index_gen.py`).
  Generated audio downloads-and-caches like LibriVox; download-fail or
  unrendered → TTS fallback. Verse-following and word-level highlighting both
  work on recorded audio (per-verse `o` offsets in the index, per-word `.w.json`
  sidecars from `tools/align_words.py`); chapters without a sidecar degrade to
  verse-level.
  ▶ **The audio path is INDEX-DRIVEN: a new narration set needs no Kotlin
  change.** Full record of how it was built, the two sets that shipped on it,
  and the recurring gotchas: `docs/NARRATION.md`.
  ⚠⚠ **`internetarchive.upload(metadata=…)` DOES NOTHING ON AN EXISTING ITEM** —
  Karl XII finished complete and stayed publicly titled «(pågår / in progress)»
  behind a clean "0 failed". `upload_narration.py` now calls `modify_metadata()`
  and re-reads the live title. Any set published in stages hits this.
- Scroll-to-verse: ONE snapshotFlow collector in ReaderScreen owns all
  scrolling (verse jumps beat chapter-top resets). Do not reintroduce split
  effects — they race (bug fixed twice).
- Highlights use an optimistic `mutableStateMapOf` mirror (`liveHighlights`) —
  DataStore flow emissions alone did not recompose lazy items reliably.
- Verse text pipeline strips `{...:...}` translator margin notes (colon = note,
  no colon = supplied words, keep those) in `BibleRepo.parseAsset`.
- Strong's (`en_kjv_strongs.json` + `strongs_lexicon.json`), red letters
  (`red_letters.json`), book cover art (`assets/bookart/<bookIdx>[_N].webp`,
  54 of 83 books; 9 rotate daily, else a generated title page in `BookArt.kt`).
  ★ **THE 29 BOOKS WITHOUT ART ARE DONE BEING HUNTED — do not re-search.** The
  reason is structural (17th-c. picture Bibles illustrate NARRATIVE, so epistles
  were never given plates). Audit: `research/bookart_gap_sources_2026-08-10.md`.
- Widget shows daily verse + book art; deterministic date-seeded pick.
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
- ⚠ **An inner Scaffold under `AppScaffold` must set
  `contentWindowInsets = WindowInsets(0)`.** AppScaffold already applies the
  navigation-bar inset to the NavHost; adding another reserves the nav-bar
  height TWICE — text clipped mid-line with a black bar below.
- Widget tap targets: **quote / reference / cover art → the linked verse** (a
  PEEK — `AppState.peek()`, which suppresses `setLastPosition` AND
  `setLastVerse`, the latter because the verse write runs on a 500 ms scroll
  debounce and would otherwise undo the chapter guard one scroll at a time);
  **everything else → the saved spot** (`EXTRA_PEEK=false`).
  ⚠ Peek is deliberately INVISIBLE. The owner asked for a "back to your spot"
  bar and then rejected it as obtrusive; `PeekReturnBar` and `reader_back_to`
  are deleted from all locales. Do not reintroduce visible chrome without asking.
- Bottom navigation bar: content height pinned to **64.dp** with the system
  inset moved outside the bar (`navigationBarsPadding()`); M3's 80dp default
  plus inset was too tall on 3-button navigation.
- ⚠ **The owner's phone runs a rustore DEBUG build.** A release APK is signed
  with the upload key and will NOT install over it
  (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`). Use `assembleRustoreDebug` for device
  testing. adb lives at `$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe`; in
  Git Bash prefix device-path commands with `MSYS_NO_PATHCONV=1` or `/sdcard/...`
  is mangled.

## Data pipelines (tools/)

Python scripts (need `pillow`, `pymupdf`; ffmpeg via winget for audio):
- `convert_scrollmapper.py` — scrollmapper JSON → app bible asset format.
- `convert_strongs.py` / `convert_lexicon_os.py` — Strong's tagged KJV +
  Open Scriptures lexicon (CC-BY-SA).
- `build_audio_index2/3.py` — LibriVox section index from archive.org
  (validates chapter coverage; only complete books admitted).
- `build_audio_index_gen.py` — the generated-narration index.
- `build_bookart*.py` — Doré / Schnorr / Merian cover art; plate→book mappings
  are curated in the scripts. ⚠ Plate numbers were DERIVED from the sources'
  own printed scripture references — re-derive rather than hand-edit.
- `count_translations.py`, `check_release_notes.py` — the two store-facing
  derivations; never hand-count either one.
- `make_widget_shot.py` — store screenshot renderer.

## Roadmap (agreed with owner) — LIVE ITEMS ONLY

Shipped roadmap items and their full records are in `docs/RELEASE_HISTORY.md`.

2. **IzzyOnDroid listing** (repo is public; low effort — `foss` flavor exists in
   build.gradle.kts with the src/foss stub, so what remains is the LISTING).
4. **Self-generated narration** — the machinery is built and several sets have
   shipped on it. Current work and the KJV re-render:
   `docs/NARRATION.md` + `tools/KJV_VOICE_RUNBOOK.md`; the original execution
   plan, whose ⚠ GATE markers still apply to any new voice (licensing, owner
   voice pick, stress-dictionary quality), is `tools/NARRATION_PLAN.md`.
   ⚠⚠ **OPEN PRODUCT QUESTION BEFORE THE KJV RE-RENDER:** `ReadingService`
   merges `putAll(librivox); putAll(generated)`, so **generated wins** — a full
   generated KJV silently retires the LibriVox HUMAN narration for the 50 books
   it covers. **Get the owner's explicit yes before rendering 1,371 chapters.**
5. **iOS port** = separate v2.0-scale project (Kotlin/Compose Multiplatform;
   Swift needed for audio/TTS/widget/notifications; Mac + Apple $99/yr).
   ★ FULL EXECUTION PLAN: `IOS_PORT_PLAN.md` (repo root) — self-contained;
   GATED on Play production going live + owner go.

## Owner preferences

- KJV/TR textual tradition only — no Critical Text translations, ever.
- All content must be legally clean: public domain or CC with attribution
  (attribution lives in `sources_text` strings).
- sources_text policy (owner, 2026-07-16): REQUIRED + PROMISED credits only —
  CC-licensed data (Open Scriptures ×2, openbible.info, SanskritBible.in,
  Bridge Connectivity/Tamil, MacLeod music) plus the two honored requests
  (Tweedale Vulgate acknowledgment, Ponomar). PD courtesy credits were
  deliberately removed — do not re-add them, and do NOT extend the translation
  list there when new PD translations ship; only new CC/promised credits go in.
- Voice cloning of real people / game characters: refused once (Joshua Graham),
  keep refusing; owner accepted reasoning.
- Tests changes on his physical phone and reports bugs precisely — believe his
  repro reports even when the code "looks right."
- Commits: no `Co-Authored-By` / AI-attribution trailers. Commit or push only
  when asked; everything sits uncommitted by default.
