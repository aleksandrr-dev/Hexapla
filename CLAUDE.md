# Hexapla — project context for Claude sessions

Offline parallel Bible app for Android. Kotlin + Jetpack Compose, single
module, no backend, no analytics. Owner: aleksandrr-dev (GitHub).
Mission: evangelism — maximize reach, keep everything free, nothing locked,
collect no data.

▶ **AUTO-LOADED INTO EVERY SESSION — SO IT HOLDS ONLY WHAT IS TRUE NOW AND
NEEDED OFTEN.** A completed record belongs in a topic doc; a ⚠ that can still
bite belongs here or is pointed at from here — never silently dropped. Condensed
2026-08-09, -08-25, -08-28. **Nothing was ever deleted:** moved blocks sit
verbatim under `── MOVED OUT OF CLAUDE.md ──` at the end of
`docs/RELEASE_HISTORY.md`, `docs/NARRATION.md`, `store-assets/STORE_LISTING.md`.

⚠⚠⚠ **NEVER PIN A DATED FILENAME HERE AS "THE CURRENT ONE."** Handoffs and
campaign books are superseded constantly, so it goes wrong within days — this
file spent 2026-08-27/28 naming an archived handoff and pointing transcription
at a book finished the day before. **Point at the RULE or COMMAND that finds the
current one**, exactly as the handoff skill says of figures.

## Build

- JAVA_HOME is NOT on PATH in shells predating 2026-07-06; use
  `C:\Program Files\Android\Android Studio\jbr` (user env var is set).
- AGP 9.3.0 / Gradle 9.4.1 / Kotlin 2.3.21 (built-in Kotlin — no
  kotlin-android plugin) / Compose BOM 2024.10 / minSdk 26. Gradle 9.6 works
  too (rolled back only for reproducibility).
- Commands: `./gradlew bundlePlayRelease` (Play AAB),
  `./gradlew assembleRustoreRelease` (RuStore APK),
  `./gradlew assembleRustoreDebug` (~20 s, for device testing).
- **Product flavors** (dimension "distribution"): `play` — Google Play,
  `EXTERNAL_DONATIONS=false`, R8 strips the ЮMoney donation path entirely;
  `rustore` — RuStore + direct APK, external ЮMoney link shows when Play
  Billing is unavailable. A `foss` flavor exists for F-Droid (src/foss stub).
  ⚠⚠ **THE DONATION GREP NEEDS ITS POSITIVE CONTROL, EVERY RELEASE.** 0 on the
  Play artifact only means something because the same grep returns **1** on the
  RuStore one; **a 0/0 result means the grep is broken, not the build clean.**
  Paths differ: `classes*.dex` (APK) vs `base/dex/classes*.dex` (AAB).

      unzip -p <aab> "base/dex/classes*.dex" | grep -ac yoomoney   # must be 0
      unzip -p <apk> "classes*.dex"          | grep -ac yoomoney   # must be 1

  ▶ It exists because the play path silently regressed for five releases
  (1.4.0–1.5.1). Full story: `docs/RELEASE_HISTORY.md`.
- Signing: `keystore.properties` in repo root (gitignored) points to the
  keystore in the owner's Documents. Play uses Play App Signing (our key =
  upload key). NEVER commit keys.
- **versionCode 17 / 1.6.4 went to BOTH stores 2026-08-16. NEXT FREE
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
| what is happening right now | the ONE `SESSION_HANDOFF_*.md` in `C:\Projects\Hexapla-releases\`. **If two exist, the later date is current and the other is a bug — archive it before doing anything else.** |
| the Play production application | the `PLAY_PRODUCTION_*.md` in `Hexapla-releases` (self-contained) |
| adding/researching a translation, licence gates, dead ends | `docs/TRANSLATIONS.md` |
| touching a Bible asset — corruption, psalm titles, markup | `docs/ASSET_DEFECTS.md` |
| renders, GPU contention, the recycle and keepalive, the audio backends | `docs/NARRATION.md` |
| what shipped when, and why a behaviour changed | `docs/RELEASE_HISTORY.md` |
| why a UI/service/widget bug must not be reintroduced | `docs/ARCHITECTURE.md` |
| store listing texts, screenshot order, RuStore/Play upload procedure | `store-assets/STORE_LISTING.md` |
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
version). Paths written as `research/…` here and in the topic docs are relative
to THERE. A session that greps the repo for them finds nothing and can conclude
the campaign docs were lost; they were not. ⚠ `tools/` lives in the REPO and the
data THERE — run tools by absolute path from `C:\Projects\Hexapla-releases`.

## ⚠ CURRENT STATE — derive it, do not read it here

★ **EXACTLY ONE CURRENT HANDOFF** (owner, 2026-08-14). Predecessors are MOVED to
`Hexapla-releases\handoff-archive\` — consult them only for the history of a
decision, never for current state. When you write a new handoff, fold forward
what is still live and archive the old one.

- **Transcription:** the Karl XII 1703 (Swedish) apocrypha.
  ⚠⚠ **NO BOOK NAME IS WRITTEN HERE ON PURPOSE.** Derive what is left with
  `python tools/karlxii_apoc_corpus_audit.py`, then read the `Resume:` line at
  the TOP of that book's own `research/karlxii_<book>.md`. **Never take the next
  book from a handoff summary and never from a page note** — "Baruch starts 696"
  is a page location, not a work queue, and a session lost time to exactly that.
- **Next campaign after it:** the Icelandic **Þorláksbiblía 1644** (31,102
  verses), no blockers. Folio↔index navigation for all three volumes AND the
  ⚠ «Cap. N» chapter-numbering rules (subtler than a summary here can carry —
  a marginal «Cap. N» is authoritative, but a verse-level shift can go unmarked)
  are in `research/THORLAKS_CAMPAIGN.md`. Volunteer overlap is SETTLED (owner,
  2026-08-10): two Icelandic Bibles is the intended outcome.
- ⚠⚠ **RUN THE CORPUS AUDIT BEFORE BELIEVING ANY COMPLETENESS CLAIM** —
  `tools/glen_corpus_audit.py`, `tools/thorlaks_corpus_audit.py`,
  `tools/karlxii_apoc_corpus_audit.py`. One of these exists because a chunk
  report claimed 572 transcribed verses while holding two on disk, and every
  per-chunk check passed it for three weeks.

## Store status

⚠ Live status only. Release history → `docs/RELEASE_HISTORY.md`; translation
research → `docs/TRANSLATIONS.md`; listing texts, screenshot order and the
per-upload procedure for both stores → `store-assets/STORE_LISTING.md`.

- **RuStore**: LIVE, at the current versionCode (see Build). Store title
  «Гексапла — параллельная Библия».
- **Google Play**: closed testing (Alpha), same versionCode. Personal account,
  so production needs **12 testers × 14 CONTINUOUS days** — one day below 12
  opted-in testers restarts the count.
  ⚠ **Read the real figure off the Play Console; never compute the date here.**
  Play counts opted-in testers in its own timezone and has its own idea of when
  day 1 was. The prepared application is the `PLAY_PRODUCTION_*.md` file.
- **Landing page**: https://aleksandrr-dev.github.io/Hexapla/ (repo root
  `index.html`) — what the in-app QR encodes AND what the archive.org narration
  items link to. English first, Russian second on the same lines.
  ⚠ **PENDING — owner, 2026-07-21: "once it's on Play Store officially, and
  F-Droid, we'll update it again."** (1) Play production approved → drop the
  `soon` class from the Play button (`.soon` = `opacity:.45;
  pointer-events:none`) and retitle it; (2) F-Droid/IzzyOnDroid live → ADD a
  fourth button (IzzyOnDroid takes a released APK; F-Droid proper needs an
  fdroiddata MR with `gradle:[foss]`); (3) whenever the count changes, bump the
  page AND `store-assets/STORE_LISTING.md` together — they must agree.
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
- ★ RELEASE-NOTES STANDARD (owner, 2026-07-23): "What's new" lives in
  `store-assets/STORE_LISTING.md` as a full Play-Console copy-paste block —
  EVERY listing locale in its own `<locale>…</locale>` tag, so the owner pastes
  the whole set at once.
  ▶ **Validate before pasting: `python tools/check_release_notes.py`** (locale
  set and ORDER match Play, every entry within the 500-char cap, exactly one
  release block above the descriptions). be/hy/iw/ta = best-effort, native
  review pending.

## Architecture landmines — INDEX

▶ **Full reasoning for every line below: `docs/ARCHITECTURE.md`.** Each is a bug
that already happened; several were fixed twice. **Read the matching entry
before editing that area.**

- `ReadingService` = foreground media service, **three backends**: TTS
  (⚠ NEVER pre-queue a chapter), LibriVox via `assets/audio_index.json`, and
  self-generated narration via `assets/audio_index_gen.json`. Verse-following
  and word-level highlighting work on recorded audio (per-verse `o` offsets,
  per-word `.w.json` sidecars); no sidecar → verse-level.
  ▶ **The audio path is INDEX-DRIVEN: a new narration set needs no Kotlin
  change.** Details + gotchas: `docs/NARRATION.md`.
  ⚠⚠ **`internetarchive.upload(metadata=…)` DOES NOTHING ON AN EXISTING ITEM.**
  Any set published in stages hits this.
- ★ **PendingIntent requestCodes MUST STAY DISTINCT** — identity IGNORES extras.
  **1 = widget continue · 2 = media notification · 3 = daily reminder ·
  4 = widget verse.** Any new PendingIntent needs its own code.
- ⚠ **Deep-link extras must be consumed in `openFromIntent`** — Android replays
  a task's original Intent forever otherwise.
- ⚠ **An inner Scaffold under `AppScaffold` must set
  `contentWindowInsets = WindowInsets(0)`** — otherwise the nav-bar inset is
  reserved twice and text clips mid-line.
- ⚠ Scroll-to-verse: **ONE** snapshotFlow collector owns all scrolling. Do not
  split it — the halves race.
- ⚠ Highlights need the optimistic `liveHighlights` mirror; DataStore emissions
  alone do not recompose lazy items reliably.
- ⚠ Widget peek is deliberately INVISIBLE — the owner rejected a visible "back
  to your spot" bar. Do not reintroduce visible chrome without asking.
- ⚠ Verse text pipeline strips `{...:...}` margin notes (colon = note, drop;
  no colon = supplied words, KEEP) in `BibleRepo.parseAsset`.
- ★ **THE 29 BOOKS WITHOUT COVER ART ARE DONE BEING HUNTED — do not re-search.**
  The reason is structural. Audit: `research/bookart_gap_sources_2026-08-10.md`.
- ⚠ **The owner's phone runs a rustore DEBUG build** — a release APK will NOT
  install over it (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`). Use
  `assembleRustoreDebug`. adb: `$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe`;
  in Git Bash prefix device-path commands with `MSYS_NO_PATHCONV=1`.

## Data pipelines (tools/)

Python (needs `pillow`, `pymupdf`; ffmpeg via winget for audio). Each script's
own docstring is the reference — what matters here is the two derivation rules:

- ✅ **`count_translations.py` and `check_release_notes.py` are the two
  store-facing derivations. NEVER hand-count either one.**
- ⚠ **`build_bookart*.py` plate→book mappings were DERIVED from the sources' own
  printed scripture references — re-derive rather than hand-edit.**

The rest (`convert_scrollmapper`, `convert_strongs`, `convert_lexicon_os`,
`build_audio_index2/3`, `build_audio_index_gen`, `make_widget_shot`) are
self-describing — read the docstring.

## Roadmap (agreed with owner) — LIVE ITEMS ONLY

Shipped roadmap items and their full records are in `docs/RELEASE_HISTORY.md`.
Numbering is from the original plan; the gaps are shipped items.

2. **IzzyOnDroid listing** (repo is public; low effort — the `foss` flavor
   already exists, so what remains is the LISTING).
4. **Self-generated narration** — the machinery is built and several sets have
   shipped on it. Current work and the KJV re-render: `docs/NARRATION.md` +
   `tools/KJV_VOICE_RUNBOOK.md`; the original execution plan, whose ⚠ GATE
   markers still apply to any new voice (licensing, owner voice pick, stress-
   dictionary quality), is `tools/NARRATION_PLAN.md`.
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
