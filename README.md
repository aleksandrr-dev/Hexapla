# Hexapla / Гексапла — parallel Bible app for Android

Offline Bible reader for Android. Kotlin + Jetpack Compose, single module, no backend, no accounts, no analytics. All text is bundled in assets (public-domain translations); optional narrated audio streams from archive.org and is cached for offline use.

## Build

1. Open the project folder in **Android Studio** (JDK 17+; the project uses AGP 9.2.1, Gradle 9.4.1, Kotlin 2.3.21, Compose BOM 2024.10, built-in Kotlin — no `kotlin-android` plugin).
2. Run on a device/emulator with **minSdk 26** (Android 8.0+), targetSdk 35.

CLI: `./gradlew assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk`.

Release signing: put a `keystore.properties` next to `settings.gradle.kts` (see `app/build.gradle.kts` for keys: `storeFile`, `storePassword`, `keyAlias`, `keyPassword`). The file and `*.jks` are gitignored. `./gradlew assembleRelease` then produces a signed, R8-minified APK (~19 MB).

## Features

| Feature | Where |
|---|---|
| 12 texts across 8 languages (see table below) | Settings → Primary translation |
| Split view, two translations verse-locked | Settings → Split view (side-by-side or stacked) |
| Verse comparison across all translations at once | Long-press verse → Compare translations (set in Settings) |
| Strong's numbers with Hebrew/Greek lexicon (KJV) | Settings → Strong's numbers; tap a number in the text |
| Audio: device TTS with word-level highlight, speed 0.5–2×, sleep timer, auto-continue | Speaker icon in reader |
| Audio: human narration (LibriVox, public domain), downloaded per section, offline after download | Settings → Narrated audio (KJV) |
| Background playback: media notification, lock-screen + headset controls | automatic during audio |
| Colored verse highlights (4 colors) | Long-press verse → color dots |
| Bookmarks, notes, cross-references (openbible.info) | Long-press verse |
| Share verse as text or as an image card | Long-press verse |
| Backup/restore of notes, bookmarks, highlights, plan progress | Settings → Backup (JSON file) |
| Diacritic-insensitive full-text search | Magnifier icon (works for Greek/Hebrew/French without accents) |
| Study guides + life-situation scripture lists | Topics tab |
| Bible-in-1-year + NT-in-90-days plans, progress, reading streak | Plans tab |
| Daily reminder with verse of the day, tap opens that verse | Settings → Daily reminder |
| Home-screen widget: verse of the day + continue reading | Launcher widget picker |
| Dark/light/system theme, serif/sans, font size 14–30 | Settings → Appearance |
| UI in English or Russian (follows system) | `values/` + `values-ru/` |
| Last position (book, chapter, and verse) restored on launch | automatic |

## Included texts (all public domain)

| Text | Language | Coverage |
|---|---|---|
| Westminster Leningrad Codex | Hebrew (pointed) | OT (Tanakh) |
| Byzantine Textform 2018 (Robinson–Pierpont) | Koine Greek (polytonic) | NT |
| Wycliffe Bible, c. 1395 | Middle English | Full |
| Tyndale, 1525/1530 | Early Modern English | Partial (what survives) |
| Geneva Bible, 1599 | Early Modern English | Full |
| King James Version, 1611 | English | Full + Apocrypha |
| Bible in Basic English | English | Full |
| Bible Martin, 1744 | French | Full |
| Lutherbibel, 1545 (modern orthography) | German | Full |
| Reina-Valera, 1909 | Spanish | Full |
| Елизаветинская Библия, 1757 | Church Slavonic (civil orthography) | Full |
| Синодальный перевод | Russian | Full + Deuterocanon |

All translations follow the Textus Receptus / Masoretic tradition — deliberately no Critical Text editions. Strong's concordance data: tagged KJV text (public-domain 1611/1769 text + 1890/1894 numbering) with the Open Scriptures Strong's dictionaries (CC-BY-SA). Cross-references © openbible.info (CC-BY). Narrated audio from LibriVox (public domain), covering 44 of 66 canonical books plus 6 Apocrypha books; the rest fall back to TTS.

### Apocrypha / Deuterocanon

The canon is an 83-slot table: 66 Protestant books plus 17 appended slots shown under an **Apocrypha** section in the book picker. Opt-in via Settings, hidden by default, never interleaved with the canon. The Synodal edition carries the fullest set (12 books); KJV carries the classic 1611 Apocrypha (14); Slavonic and Wycliffe carry 10 each. Slots align across translations so split view pairs e.g. KJV 2 Esdras ‖ Synodal 3 Ездры verse-by-verse.

## Architecture notes

- **Text data**: `assets/bibles/*.json` — book arrays `{name, chapters[[verses]]}`. Loaded once, cached in memory (`BibleRepo`). New translations: drop a JSON in the same format, add one line to `BibleRepo.translations`.
- **Strong's**: `assets/bibles/en_kjv_strongs.json` (inline `[H1234]` tags, display-only) + `assets/strongs_lexicon.json`; see `StrongsRepo`. TTS/search/copy always use the clean text.
- **Audio**: `ReadingService` — a foreground `mediaPlayback` service with MediaSessionCompat. Two backends: device `TextToSpeech` (word-level highlight via `onRangeStart`) and `MediaPlayer` for LibriVox MP3 sections (`assets/audio_index.json` maps book → chapter-range → archive.org URL; files cached under `filesDir/audio`).
- **Persistence**: Preferences DataStore only. Backup = JSON export/import (merge semantics).
- **Widget**: classic `AppWidgetProvider` (`VerseWidget`), deterministic daily verse seeded by date.
- **Reminder**: daily `AlarmManager` alarm + boot receiver; the notification carries the verse of the day and deep-links to it.

## Voluntary support

Settings has an optional "Support the developer" section. Nothing is gated behind payment. Google Play builds use consumable Play Billing tips; builds without Play services (direct APK, RuStore) show a ЮMoney link instead (`Donation` in `Bible.kt`).

## License / data credits

App text data via scrollmapper, thiagobodruk and byztxt projects. Strong's dictionaries © Open Scriptures, CC-BY-SA. Cross-references © openbible.info, CC-BY. Narration recordings by LibriVox volunteers, public domain. Media-card book art: engravings by Gustave Doré (1866) and woodcuts by Julius Schnorr von Carolsfeld (Die Bibel in Bildern, 1860), both public domain, via Project Gutenberg and Wikimedia Commons.
