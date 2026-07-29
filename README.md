# Hexapla / Гексапла — parallel Bible app for Android

Offline Bible reader for Android. Kotlin + Jetpack Compose, single module, no backend, no accounts, no analytics. All text is bundled in assets (public-domain translations); optional narrated audio streams from archive.org and is cached for offline use.

## Build

1. Open the project folder in **Android Studio** (JDK 17+; the project uses AGP 9.3.0, Gradle 9.4.1, Kotlin 2.3.21, Compose BOM 2024.10, built-in Kotlin — no `kotlin-android` plugin).
2. Run on a device/emulator with **minSdk 26** (Android 8.0+), compileSdk/targetSdk 36.

CLI: `./gradlew assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk`.

Two product flavors (dimension `distribution`): **`play`** for Google Play (Play Billing tips; the external donation path is compiled out) and **`rustore`** for RuStore and direct APK download. A **`foss`** flavor with billing stubbed out is F-Droid-ready.

Release signing: put a `keystore.properties` next to `settings.gradle.kts` (see `app/build.gradle.kts` for keys: `storeFile`, `storePassword`, `keyAlias`, `keyPassword`). The file and `*.jks` are gitignored. `./gradlew assembleRustoreRelease` / `bundlePlayRelease` produce signed, R8-minified artifacts (~72 MB APK — the bulk is bundled scripture, lexicons and cover art).

## Features

| Feature | Where |
|---|---|
| 35 texts — 33 translations across 29 languages, plus the Hebrew and Greek originals (see table below) | Settings → Primary translation |
| Split view, two translations verse-locked | Settings → Split view (side-by-side or stacked) |
| Verse comparison across all translations at once | Long-press verse → Compare translations (set in Settings) |
| Strong's numbers with Hebrew/Greek lexicon (KJV) | Settings → Strong's numbers; tap a number in the text |
| Audio: device TTS with word-level highlight, speed 0.5–2×, sleep timer, auto-continue | Speaker icon in reader |
| Audio: recorded narration — LibriVox readings plus generated voices for books LibriVox never covered — streamed from archive.org, cached offline, with verse highlighting and exact resume | Settings → Narrated audio |
| Original-language interlinear: tap any Greek or Hebrew word for its Strong's entry and parsed morphology | automatic on the Byzantine NT and Leningrad Codex |
| Verse-level versification map: translations keep their authentic native numbering (LXX psalters, Masoretic bounds, title-psalms) while split view, compare, cross-references and red letters stay aligned | automatic |
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
| UI in 25 languages (follows system; Android 13+ per-app language picker) | `values/` + 24 `values-*/` |
| Last position (book, chapter, and verse) restored on launch | automatic |

## Included texts (all public domain)

**35 texts — 33 translations across 29 languages, plus the Hebrew and Greek originals.** Coverage below is derived from the shipped assets, not claimed.

### Original languages
| Text | Language | Coverage |
|---|---|---|
| Westminster Leningrad Codex | Hebrew (pointed) | OT |
| Byzantine Textform (Robinson–Pierpont) | Koine Greek (polytonic) | NT |

### English
| Text | Coverage |
|---|---|
| King James Version, 1611 | Full + 14 Apocrypha |
| Webster Bible, 1833 | Full |
| Geneva Bible, 1599 | Full |
| Young's Literal Translation, 1898 | Full |
| Wycliffe, c. 1395 (Middle English) | Full + 10 Apocrypha |
| Tyndale, 1525/1531 (Early Modern English) | NT + 6 OT books (what survives) |

### Other languages
| Text | Language | Coverage |
|---|---|---|
| Bible Martin, 1744 | French | Full |
| Lutherbibel, 1545 | German | Full |
| Karl XII:s Bibel, 1703 | Swedish | Full |
| Biblia — Vanha kirkkoraamattu, 1776 | Finnish | Full |
| Glika Bībele, 1685/1689 | Latvian | Full + 12 Apocrypha |
| Biblia Gdańska, 1632 | Polish | Full |
| Sveto pismo — Karadžić/Daničić, 1847/1865 | Serbian (Latin) | Full |
| Dansk Bibel, 1819/1871 | Danish | Full |
| Statenvertaling, 1637/1888 | Dutch | Full |
| Reina-Valera, 1909 | Spanish | Full |
| Almeida — Bíblia Livre (TR) | Portuguese | Full |
| Diodati, 1649/1885 | Italian | Full |
| Károli Biblia, 1590/1908 | Hungarian | Full |
| Bible kralická, 1613 | Czech | Full |
| 明治元訳 Meiji Motoyaku, 1880/87 | Japanese | Full |
| 和合本 Chinese Union, 1919 | Chinese (Simplified) | Full |
| 和合本 Chinese Union, 1919 | Chinese (Traditional) | Full |
| Синодальный перевод | Russian | Full + 12 Apocrypha |
| Елизаветинская Библия, 1757 | Church Slavonic (civil orthography) | Full + 12 Apocrypha |
| Η Αγία Γραφή — Βάμβας, 1850 | Modern Greek | Full |
| Vulgata Clementina, 1592 | Latin | Full + 7 deuterocanonical |
| الكتاب المقدس — Van Dyck, 1865 | Arabic | Full |
| பரிசுத்த வேதாகமம் — IRV, 2019 | Tamil | Full |
| सत्यवेदः — Sanskrit NT, 1851 | Sanskrit | NT |
| Նոր Կտակարան, 1853 | Western Armenian | NT |
| عهد جدید — Henry Martyn, 1876 | Persian | NT |
| Новы Запавет і Псальмы — Дзекуць-Малей/Луцкевіч, 1931 | Belarusian | NT + Psalms |

All translations follow the Textus Receptus / Masoretic tradition — deliberately no Critical Text editions. Each candidate is checked against a seven-verse deity litmus (1 Tim 3:16, the Johannine Comma, Acts 8:37, Rom 16:24, Luke 2:33, Acts 20:28, John 3:13) before it ships; texts that fail are rejected regardless of how good the digitization is.

Translations keep their **authentic native versification** — LXX psalters, Masoretic chapter bounds, title-psalms as their own verse — and `assets/versemap.json` pivots between them so split view, verse comparison, cross-references and red letters stay aligned across editions that number differently.

Strong's concordance data: tagged KJV text (public-domain 1611/1769 text + 1890/1894 numbering) with the Open Scriptures Strong's dictionaries (CC-BY-SA). Original-language interlinear from openscriptures/morphhb (CC-BY) and byztxt (public domain). Cross-references © openbible.info (CC-BY). Tamil IRV © Bridge Connectivity Solutions (CC BY-SA 4.0); Sanskrit NT © SanskritBible.in (CC BY-SA 4.0); Latvian Glück text from the University of Latvia SENIE corpus (CC BY-SA 4.0).

Audio: human narration from LibriVox (public domain) for most KJV books, plus generated narration for the books LibriVox never covered and for other translations, streamed from archive.org and cached for offline use. Anything without recorded audio falls back to device TTS.

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
