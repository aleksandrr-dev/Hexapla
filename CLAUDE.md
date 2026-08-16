# Hexapla — project context for Claude sessions

Offline parallel Bible app for Android. Kotlin + Jetpack Compose, single
module, no backend, no analytics. Owner: aleksandrr-dev (GitHub)
(GitHub aleksandrr-dev). Mission: evangelism —
maximize reach, keep everything free, nothing locked, collect no data.

## Build

- JAVA_HOME is NOT on PATH in shells predating 2026-07-06; use
  `C:\Program Files\Android\Android Studio\jbr` (user env var is set).
- AGP 9.3.0 (bumped from 9.2.1 by Android Studio's updater 2026-07-20,
  owner-confirmed; verified same-day: compile, lint, both release flavors,
  R8 donation stripping) / Gradle 9.4.1 / Kotlin 2.3.21 (built-in Kotlin —
  no kotlin-android plugin) / Compose BOM 2024.10 / minSdk 26 / targetSdk 35.
  Gradle 9.6 works too (was rolled back only for reproducibility).
- **Product flavors** (dimension "distribution"):
  - `play` — Google Play. `EXTERNAL_DONATIONS=false`; R8 strips the ЮMoney
    donation path entirely (verified absent from dex). ⚠ THIS SILENTLY
    REGRESSED IN 1.4.0: the empty-Support restructure moved Donation.links
    into a plain `else` branch — runtime-unreachable on play (outer gate
    requires playTips) but not PROVABLY dead, so the string shipped in every
    1.4.0-1.5.1 play dex. FIXED 2026-07-20: the branch is now
    `else if (BuildConfig.EXTERNAL_DONATIONS)` (identical runtime semantics,
    provably dead for R8); re-verified absent from play dex / present in
    rustore dex, under AGP 9.3.0. Re-check this grep before every Play
    upload: `unzip -p app-play-release.apk "classes*.dex" | grep -ac yoomoney`
    must print 0.
  - `rustore` — RuStore + direct APK. External ЮMoney donation link shows
    when Play Billing is unavailable.
- Commands: `./gradlew bundlePlayRelease` (Play AAB),
  `./gradlew assembleRustoreRelease` (RuStore APK).
- Signing: `keystore.properties` in repo root (gitignored) points to the
  keystore in the owner's Documents folder. Play uses Play App Signing
  (our key = upload key). NEVER commit keys. **versionCode: 17 is built (1.6.4, staged 2026-08-16 with BOTH the
  Slavonic and Russian-deuterocanon narration; not yet uploaded); next free
  is 18.** Bump for every store update.
  ★ **CHURCH SLAVONIC NARRATION FOLDS INTO 1.6.4 / code 17** (owner,
  2026-08-12) — the Karl XII precedent: 1.6.4 has never been public, so it is
  rebuilt in place rather than burning code 18. ⚠ CONSEQUENCES: the STAGED
  `Hexapla-1.6.4-*.aab/.apk` artifacts are now STALE and must be rebuilt after
  `audio_index_gen.json` is regenerated; the donation grep must be re-run on
  the new pair (0 on Play, 1 on RuStore); and 1.6.4's release notes need a
  Slavonic-audio line in every locale per the release-notes standard.
- ★ **TODO, DO IN THE NEXT BUILD** (owner asked 2026-08-05, deliberately
  deferred past 1.6.3 because its artifacts were already built and verified):
  replace the **25 deprecated `Locale("xx")` call sites in `Bible.kt`** — the
  one-arg `Locale(String)` constructor, deprecated in Java 19, which the
  Android Studio JBR (JDK 21) flags on every translation not covered by a
  built-in like `Locale.ENGLISH`. They are warnings only: the constructor
  still works on every supported Android version and the app behaves
  identically. They are worth clearing because 25 sites (reported as ~50
  warnings — Kotlin counts each twice) drown out warnings that DO matter.
  ⚠⚠ **USE `Locale.forLanguageTag("sv")`, NOT `Locale.of("sv")`.** `Locale.of`
  is Java's official replacement but it is Java 19 = **API 36**, against this
  app's **minSdk 26** — it compiles clean and then crashes on essentially every
  real device. `forLanguageTag` is API 21+ and equivalent for the plain
  language codes used here (all 25 are bare two-letter tags, no country or
  variant). Re-run the donation grep with its positive control after, since
  any Bible.kt change invalidates a built artifact.


## ⚠ WHERE THINGS ARE — read this before hunting through the repo

This file was 1,636 lines and nobody could find anything in it, including me.
Split 2026-08-09. **Nothing was deleted**; four topic docs now hold the detail,
and every ⚠ landmine moved intact.

| you need | read |
|---|---|
| adding/researching a translation, licence gates, dead ends | `docs/TRANSLATIONS.md` |
| touching a Bible asset — corruption, psalm titles, markup | `docs/ASSET_DEFECTS.md` |
| renders, GPU contention, the recycle and keepalive | `docs/NARRATION.md` |
| what shipped when, and why a behaviour changed | `docs/RELEASE_HISTORY.md` |
| what is happening right now | **`SESSION_HANDOFF_2026-08-15.md`** — the ONE current handoff |
| the Glen Persian campaign specifically | `research/GLEN_RESUME_NOW.md` |

⚠⚠ **`research/`, `narration/`, `logs/` and every `SESSION_HANDOFF_*.md` are
NOT IN THIS REPO.** They live in the sibling working directory
**`C:\Projects\Hexapla-releases\`** — untracked on purpose (scans, renders and
staged store artifacts are far too large to version). Paths written as
`research/…` throughout this file and the topic docs are relative to THERE, not
to the repo root. A session that greps the repo for them finds nothing and can
conclude the campaign docs were lost; they were not. `logs/PAUSE_cu` etc. are
`C:\Projects\Hexapla-releases\narration\logs\`.

▶ **Rule for future edits: this file holds only what is true NOW and needed
OFTEN.** A completed record belongs in a topic doc. A ⚠ that can still bite
belongs here or is pointed at from here — never silently dropped.

## ⚠ CURRENT STATE — read SESSION_HANDOFF_2026-08-15.md first

★ **HANDOFFS WERE CONSOLIDATED 2026-08-14** (owner). There is now exactly ONE
current handoff, **`SESSION_HANDOFF_2026-08-15.md`**, and it is self-contained.
The 15 dated predecessors were MOVED (not deleted) to
`C:\Projects\Hexapla-releases\handoff-archive\` — consult them only for the
history of a decision, never for current state. Keep it to one file: when you
write a new handoff, fold forward what is still live and archive the old one.

★ **GLEN PERSIAN OT SHIPPED 2026-08-09, versionCode 17 / 1.6.4** (APK staged at
`Hexapla-1.6.4-rustore.apk`, NOT yet uploaded or device-checked). fa_martyn.json
is now a complete Persian Bible — Glen's OT 1856 (23,137 verses, transcribed by
this project) + Martyn's NT 1876. Counts are UNCHANGED by this release (an OT was added to the existing
Persian entry). ⚠ But the counts disagree across page/listing/tagline — see
the Store status section; reconcile before the next listing edit. Next campaign is the **Icelandic Þorláksbiblía 1644** — 31,102
verses. ✅ **NO BLOCKERS REMAIN — chunks may launch** (brief, with exact
folio↔index navigation for all three volumes:
`research/THORLAKS_CAMPAIGN.md`; run
`tools/thorlaks_corpus_audit.py` before believing any completeness claim).
The volunteer-overlap question is SETTLED (owner, 2026-08-10): Birgir was told
in advance that we are doing the 1644, and his 1584 Guðbrandsbiblía is a
separate project — two Icelandic Bibles is the intended outcome.
✅ **The 1 Chronicles blocker is CLEARED (2026-08-10).** The print splits KJV
1 Chr 4 at verse **24** (the Simeon genealogy becomes its own chapter "V",
keeping KJV's verse numbers 24-43), so printed VI..XXX = KJV 5..29 and it never
re-syncs; 2 Chronicles starts clean. The **marginal "Cap. N" is the
authoritative numeral, NOT the big heading** — it equals the KJV number and
appears only where the print has drifted, so it doubles as a divergence
detector for chunk agents. Cost is one merge run, not a wholesale shift. Full
evidence + the two corrections to the 08-09 write-up:
`research/thorlaks_precampaign_checks.md` (top section).
⚠ `tools/glen_corpus_audit.py` exists because a chunk report claimed 572
transcribed verses while holding two on disk, and every per-chunk check passed
it for three weeks. Run it before believing any completeness claim.

## ⚠ SUPERSEDED — (was SESSION_HANDOFF_2026-08-04.md, now in handoff-archive/)

**1.6.3 (code 16) was UPLOADED to Play and RuStore on 2026-08-05** — 35
translations in 30 languages, the Georgian Bakar and its UI locale, the
Armenian Zohrab OT, music by mood, the swap-translations button, and the
Russian Synodal narration (1192 chapters, streamed from
`hexapla-audio-synodal-1876`). Next versionCode is 17.

✅ **GITHUB RELEASES ARE CURRENT** (checked 2026-08-10 with `gh release list`).
The old warning here — "v1.6.1 is still `releases/latest`, 1.6.3 was never
published" — was STALE: v1.6.3 was published 2026-08-05 and was `Latest`.
v1.6.4 is now published and is `Latest`. ⚠ 1.6.2 was never published and is
not back-filled; that is a deliberate gap, not an oversight to re-fix. The
landing page's direct-APK button points at `releases/latest`, and the upload
is always the **RuStore APK**, never the Play AAB.


## Store status

⚠ Live status only. Release-by-release history is in `docs/RELEASE_HISTORY.md`; translation research and integration records are in `docs/TRANSLATIONS.md`.


- **RuStore**: LIVE. Latest uploaded: **1.6.3 (code 16), 2026-08-05**.
  **1.6.4 (code 17) is BUILT and staged but not uploaded** — the Persian
  Bible release. Store title «Гексапла — параллельная Библия».
  ⚠ Every upload re-asks the Safety form (answers at the top of
  `store-assets/STORE_LISTING.md`), and a new version draft does **NOT**
  inherit media — re-upload the icon (`store-assets/icon_512_store.png`) and
  6 screenshots (5 JPGs in `store-assets/rustore/`, order 120537, 120212,
  120307, 120326, 120426, then `screenshot_widget.png`). The browser
  extension cannot upload local files; the owner picks them in the native
  dialog. Review ≈ a day.
- **Google Play**: closed testing (Alpha). Latest uploaded 1.6.3 (code 16),
  2026-08-05. Personal account, so production needs **12 testers × 14
  continuous days** — and the blocker has been the tester COUNT, not the
  clock: the countdown only advances on days with ≥12 opted-in testers.
  ★ **THE 12th TESTER JOINED 2026-08-12 — the clock is running as of today**
  (owner). Day 14 is **2026-08-25**, so production can be applied for on
  **2026-08-26**. ⚠ CONTINUOUS: one day below 12 opted-in testers and the
  count restarts, so do not let a tester opt out or uninstall before then.
  ⚠ Read the real figure off the Play Console before acting on that date —
  Play counts opted-in testers in its own timezone and has its own idea of
  when day 1 was.
  IARC done (purchases answered NO — tip products deliberately not created
  so Brazil rates Livre; tips exist only in code). Target audience 13+, no
  ads/ad-ID/health. Third-party syndication: publish-all. Play App Signing.
  ⚠ Before every Play upload run the donation grep on the AAB —
  `unzip -p <aab> "base/dex/classes*.dex" | grep -ac yoomoney` must print
  **0**, and the same grep on the RuStore APK must print **1** (the positive
  control; a 0/0 result means the grep is broken, not that the build is clean).
- **Landing page** (what the in-app QR encodes, AND what the archive.org
  narration items link to — update as stores go live):
  https://aleksandrr-dev.github.io/Hexapla/ (repo root `index.html`).
  REBUILT 2026-07-21 (commit d2e30e3, owner-requested): **English first**
  in title/tagline/every button, Russian second on the same lines; counts
  refreshed 17 languages -> «33 translations in 28 languages» (stale since the 1.4.x era).
  ✅ **COUNTING CONVENTION SETTLED (owner, 2026-08-09) — derive, never
  hand-count: `python tools/count_translations.py`.** Translations = distinct
  TEXTS (two scripts of one translation count once — zh; original-language
  texts grc/wlc DO count). Languages = what a READER would name (Middle
  English folds into English; ancient languages count as their own).
  **Today: «36 translations in 30 languages».**
  ✅ **ALL THREE PLACES NOW AGREE ON 36/30** (2026-08-10). The in-app
  `welcome_tagline` was already right; the landing page was updated (it said
  **35**, not the 33/28 this note used to claim — check `index.html`, do not
  trust a remembered figure); and the store listing carries the count only in
  its release-notes block, which the 1.6.4 notes state as 36. Older blocks
  under the ARCHIVE banner keep their historical numbers on purpose.

  releases/latest, `gh release create vX.Y.Z <apk>` each release),
  RuStore (live), Play (`.soon` class = greyed + non-clickable).
  ⚠ **PENDING PAGE UPDATES — owner, 2026-07-21: "once it's on Play Store
  officially, and F-Droid, we'll update it again."** So on those events:
  (1) Play production approved -> drop the `soon` class from the Play
  button and retitle it (it currently reads "coming soon / скоро");
  (2) F-Droid/IzzyOnDroid listing live -> ADD a fourth button (roadmap
  items 2 + 6; the `foss` flavor is already F-Droid-ready — IzzyOnDroid
  takes a released APK, F-Droid proper needs an fdroiddata MR with
  gradle:[foss]);
  (3) whenever the translation count changes, bump the page AND
  store-assets/STORE_LISTING.md together — they must agree.
  ⚠ Count bookkeeping is currently inconsistent in the repo's own
  history: the 1.5.1 listing copy says «33 translations in 28 languages»
  (Belarusian) while commit 078fc44 calls Persian "33rd/28th". Bible.kt
  literally holds 35 Translation() entries / 28 locale codes (zh counted
  twice, and grc+wlc are original-language texts rather than
  translations — the likely source of the -2). Reconcile once, then keep
  page and listing in lockstep. The page today says 33/28 to match the
  SHIPPED listings; Persian is in tree but unreleased.
- Privacy policy: https://aleksandrr-dev.github.io/Hexapla/PRIVACY.html
- Listing texts + screenshot order: `store-assets/STORE_LISTING.md`.
  ★ RELEASE-NOTES STANDARD (owner, 2026-07-23): "What's new" is kept there as
  a full Play-Console copy-paste block — EVERY listing locale in its own
  `<locale>…</locale>` tag (30 locales, matching Play's list), so the owner
  pastes the whole set at once. For each release, fill every locale (reuse
  prior wording where stable); see the "Release-notes format — STANDARD"
  section at the top of STORE_LISTING.md. be/hy/iw/ta = best-effort, native
  review pending.

⚠ Narration/render machinery lives in `docs/NARRATION.md`.
⚠ Asset-defect history and the tools that find corruption live in `docs/ASSET_DEFECTS.md`.

## Architecture notes (beyond README)

- `ReadingService`: foreground media service. Backends — TTS (per-verse
  feeding; NEVER pre-queue a chapter, engines drop utterances while loading
  a language); MediaPlayer for LibriVox sections (`assets/audio_index.json`,
  50 books covered; download+cache); and (NEW 2026-07-22, in tree for 1.5.2/
  code 13) MediaPlayer STREAMING of self-generated per-chapter narration for
  non-kjv translations via `assets/audio_index_gen.json` (built by
  tools/build_audio_index_gen.py from the rendered narration/<id> sets +
  the archive.org item). Webster (wbt) is the first: streams
  hexapla-audio-webster-1833 per chapter. `AudioRepo.generated()` yields
  single-chapter Sections (first==last, generated=true). Generated audio
  DOWNLOADS-AND-CACHES like LibriVox (offline after first listen) via
  `ensureDownloadedGen`/`generatedFile`; the latter keys the cache by the
  full archive path (`item_book_chapter.ogg`) because generated URLs share
  a `<ch>.ogg` tail that localFile's last-segment rule would collide on
  (the LibriVox `localFile` path is untouched). Download-fail + missing/
  unrendered → TTS fallback.
  ✅ VERSE-FOLLOWING DURING GENERATED NARRATION — DONE 2026-07-24 (in tree,
  uncommitted, compiles; NOT yet on-device-verified or shipped). Section now
  carries the per-verse `o` offsets (Audio.kt), and ReadingService.
  startVerseFollow polls player.currentPosition (~250ms) → offsets → publishes
  Playback.verse, so recorded audio highlights + auto-scrolls exactly like TTS
  (ReaderScreen highlights when Playback.verse==i). No word-level highlight for
  recorded audio (offsets are per-verse). ✅ EXACT seek-to-verse from offsets
  DONE 2026-07-24: playSection takes startVerse; onPreparedListener seeks to
  offsets[startVerse]-250ms when the section carries offsets (verse 0 → no seek,
  chapter announcement plays), else the sectionFraction verse-count estimate.
  Makes stop→resume land exactly on the verse for generated audio (TTS was
  already exact). Translation-agnostic — every render that emits "o" gets it.
  ✅ WORD-LEVEL following on recorded narration SHIPPED (commit 8b0d050):
  tools/align_words.py emits per-word .w.json sidecars; ReadingService
  fetches them in the background and publishes wordStart/wordEnd exactly
  as TTS does. Chapters without a sidecar degrade to verse-level.
  ⚠ The old 'FUTURE IDEA / deferred' note sat here after shipping and
  misled a session into calling this feature missing (2026-08-09).
  ✅ GENERATED AUDIO "REVERTS TO TTS AFTER SOME CHAPTERS" BUG — FIXED
  2026-07-24 (owner heard it on Webster; in tree, uncommitted). Root cause:
  on auto-advance, playSection downloads the next chapter on demand and
  downloadTo had NO retry — one transient archive.org failure → null →
  immediate TTS fallback (ReadingService ~L315). Fix: (a) downloadTo now
  retries 3× with backoff (Audio.kt, helps LibriVox too); (b) new
  ReadingService.prefetchAhead caches the next 2 generated chapters in the
  background while the current one plays (skipped in stream-don't-save mode
  and for LibriVox multi-chapter sections). followJob+prefetchJob cancelled
  in releasePlayer.
  ✅ RESOLVED (verified 2026-07-31): the audio_note string is NO LONGER
  KJV-worded — all 25 locales now read generically ("recorded narration where
  it exists, otherwise the device's text-to-speech"). Nothing to reword for a
  new generated translation.
  ✅ **GENEVA 1599 SHIPPED 2026-08-01 in 1.6.2 (code 15).** Render finished
  1189/1189; uploaded to archive.org `hexapla-audio-geneva-1599` (2379/2379
  requests, 0 failed) and verified public; `gen1599` activated in
  tools/build_audio_index_gen.py — 66 books, 1189 chapters, 31,104 verse
  offsets embedded. No Kotlin change was needed; the audio path is index-driven,
  exactly as the runbook predicted. Full record + two bugs found during
  activation: **tools/GENEVA_AUDIO_RUNBOOK.md** (now marked COMPLETED and kept
  as the model for the next narration set).
  ⚠ Two things that will recur for any FUTURE narration set:
  (a) the index completeness guard compared books-with-audio against ALL grid
      slots, so an asset with empty apocrypha slots (Geneva has 83 slots, 66
      non-empty) false-failed a complete set — fixed to count non-empty books;
  (b) the yoomoney donation check needs a POSITIVE CONTROL — 0 in the Play AAB
      only means something because the same grep returns 1 on the RuStore APK.
      Path differs: `classes*.dex` (APK) vs `base/dex/classes*.dex` (AAB).
  ✅ **KARL XII 1703 SHIPPED 2026-08-01 in the same 1.6.2 (code 15).** Render
  finished 1189/1189; uploaded to `hexapla-audio-karlxii-1703` (2379/2379
  requests, 0 failed — only 1378 files actually sent, the rest skipped by
  `checksum=True` since the set had been published partial at ~940). `kxii`
  is now `partial: False` in tools/build_audio_index_gen.py — 66 books, 1189
  chapters, 31,102 verse offsets. Version was deliberately NOT bumped (owner:
  reuse 1.6.2 / code 15); the staged artifacts were rebuilt in place.
  ⚠⚠ **A BUG THAT WILL BITE EVERY FUTURE NARRATION SET — upload metadata does
  not reach an EXISTING item.** `internetarchive.upload(metadata=…)` applies
  metadata only when it CREATES the item; on a pre-existing one archive.org
  ignores the headers. Karl XII therefore finished complete but stayed
  publicly titled «(pågår / in progress)» — the exact inversion the honesty
  gate exists to prevent, and invisible behind a clean `0 failed`. Geneva
  looked fine only because its item was brand new. FIXED: upload_narration.py
  now calls `modify_metadata()` explicitly and re-reads the live title to
  verify. **Any set published in stages (ru is next) hits this.**
  ⚠ Also fixed there: the description said "no narrator is credited because
  none was involved" — false for sv and ru, whose voices are cloned from
  consenting volunteers. Now branches on a `cloned` flag, plus a `watermark`
  flag disclosing the inaudible Perth watermark Chatterbox embeds.
  Both audio items live on archive.org (webster-1833
  = wbt via audio_index_gen; hexapla-audio-en = 22 KJV Kokoro gap books via
  audio_index.json as kjv_<book>_<ch>.ogg, which also cache offline). Music bed rotates
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
- ★ **PendingIntent requestCodes MUST STAY DISTINCT** (fixed 2026-07-31,
  owner-verified on device). PendingIntent identity IGNORES extras, so the
  widget, the media notification and the daily reminder — all previously at
  requestCode 0 — were literally the same object, and the reminder's
  `FLAG_UPDATE_CURRENT` rewrote the others' extras. Symptom: the widget read
  "Continue reading: Exodus 20" and opened Psalms 41. Allocation now:
  **1 = widget continue · 2 = media notification · 3 = daily reminder ·
  4 = widget verse**. Any new PendingIntent needs its own code.
- **Deep-link extras are consumed in `openFromIntent`.** Android replays a
  task's original Intent on every recreation, so an uncleared deep link
  re-fires forever — including from the app drawer. That was the second half
  of the Psalms-41 bug.
- ⚠ **An inner Scaffold under `AppScaffold` must set
  `contentWindowInsets = WindowInsets(0)`.** AppScaffold already applies the
  navigation-bar inset to the NavHost; ReaderScreen's inner Scaffold added its
  own on top, reserving the nav-bar height TWICE — text clipped mid-line with
  a black bar below. Pre-existing since the nested Scaffold was introduced.
- Widget tap targets: **quote / reference / cover art → the linked verse** (a
  PEEK — `AppState.peek()`, which suppresses `setLastPosition` AND
  `setLastVerse`, the latter because the verse write runs on a 500 ms scroll
  debounce and would otherwise undo the chapter guard one scroll at a time);
  **everything else → the saved spot** (`EXTRA_PEEK=false`). Peek ends when
  the reader leaves the linked chapter.
  ⚠ Peek is deliberately INVISIBLE. The owner asked for a "back to your spot"
  bar and then rejected it as obtrusive; `PeekReturnBar` and `reader_back_to`
  are deleted from all 25 locales. Do not reintroduce visible chrome without
  asking.
- Bottom navigation bar: content height pinned to **64.dp** with the system
  inset moved outside the bar (`navigationBarsPadding()`); M3's 80dp default
  plus inset was too tall on 3-button navigation.
- ⚠ **The owner's phone runs a rustore DEBUG build.** A release APK is signed
  with the upload key and will NOT install over it
  (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`). Use
  `./gradlew assembleRustoreDebug` (~15-60 s) for device testing;
  `assembleRustoreRelease` (~3 min) only for store artifacts. adb lives at
  `$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe`; in Git Bash prefix
  device-path commands with `MSYS_NO_PATHCONV=1` or `/sdcard/...` is mangled.

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
2. IzzyOnDroid listing (repo is public; low effort — flavor ready, see item 6).
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
4. Self-generated narration (Kokoro for EN, Piper-or-newer for RU,
   host on archive.org) — fills 22 KJV books LibriVox lacks + enables
   Russian audio. FULL EXECUTION PLAN: tools/NARRATION_PLAN.md
   (written 2026-07-13, self-contained for a cheaper-model session;
   honor its ⚠ GATE markers — voice licensing, owner voice pick,
   stress-dictionary quality, ReadingService diff review).
5. iOS port = separate v2.0-scale project (Kotlin/Compose Multiplatform;
   Swift needed for audio/TTS/widget/notifications; Mac + Apple $99/yr).
   ★ FULL EXECUTION PLAN: IOS_PORT_PLAN.md (repo root, written 2026-07-21
   by Fable-5 with whole-architecture context — self-contained for a
   future agent; GATED on Play production going live + owner go).
6. ~~fonts~~ SHIPPED (Literata bundled for reading, commit 8c04580 — the
   "NOT in the app" note here was true only until that landed).
   ~~rotating covers~~ DONE 2026-08-10: `BookArt.kt` indexes
   `bookart/<idx>_N.webp` variants and picks one with the widget's own
   date-seeded trick (`year*1000 + dayOfYear`, offset by bookIdx so books do
   not turn over in lockstep). `tools/build_bookart3.py` added 31 extra Doré
   plates — **9 books rotate** (Genesis 7 plates, Matthew 6, Luke 6, Mark 5,
   Acts 5, John 4, Daniel 3, 1 Samuel 2, 1 Kings 2) for **+1.36 MB
   compressed**, far under the 2.5 MB the plan assumed.
   ⚠ Its plate numbers were DERIVED from Gutenberg #8710's own printed
   scripture references, not recalled, and the derivation reproduces
   build_bookart.py's existing curated map exactly. Re-derive rather than
   hand-edit. Psalms/Proverbs/Isaiah/Exodus/Revelation cannot rotate yet —
   Doré has only the one plate each; Schnorr has 219 unused plates but no
   transcribed index.
   ★ **COVER GAPS: 54 of 83 books now have art; the remaining 29 are DONE
   being hunted — do not re-search.** `tools/build_bookart4.py` filled the
   last coverable five (Song of Solomon, Hosea, Haggai, Malachi from Merian's
   *Icones Biblicae*; 1 Peter from Schnorr plate 231). What is left is
   **16 epistles, 8 apocrypha, 5 minor prophets**, and the reason is
   structural, not a gap in our sources: **17th-c. picture Bibles illustrate
   NARRATIVE**, so epistles were never given plates, and the leftover
   apocrypha (1/2 Esdras, 3 Macc, Laodiceans…) are not even in the Lutheran
   canon. Both Weigel volumes were indexed page by page to prove it — the
   1708 *Historiae celebriores* (Luyken engravings) runs Genesis → Acts 28
   and stops. These 29 keep `BookArt.kt`'s generated title pages, which is
   the right answer. Full audit:
   `research/bookart_gap_sources_2026-08-10.md`.
   ~~music download-on-demand~~ SHIPPED
   (Settings → Download music pack; music_pack_* strings ×26 locales).
   ~~`foss` flavor~~ EXISTS in build.gradle.kts with the src/foss stub —
   what remains is the LISTING (IzzyOnDroid takes a released APK; F-Droid
   proper needs an fdroiddata MR with gradle:[foss]).

## Owner preferences

- KJV/TR textual tradition only — no Critical Text translations, ever.
- All content must be legally clean: public domain or CC with attribution
  (attribution lives in `sources_text` strings, all 13 locales).
- sources_text policy (owner, 2026-07-16): REQUIRED + PROMISED credits only —
  CC-licensed data (Open Scriptures ×2, openbible.info, SanskritBible.in,
  Bridge Connectivity/Tamil, MacLeod music) plus the two honored requests
  (Tweedale Vulgate acknowledgment, Ponomar). PD courtesy credits
  (translation enumeration, mshaffer 1828, Robinson, scrollmapper/
  thiagobodruk/byztxt/Wikisource) were deliberately removed — do not
  re-add them, and do NOT extend the translation list there when new PD
  translations ship; only new CC/promised credits go in.
- Voice cloning of real people / game characters: refused once (Joshua
  Graham), keep refusing; owner accepted reasoning.
- Tests changes on his physical phone and reports bugs precisely —
  believe his repro reports even when the code "looks right."
