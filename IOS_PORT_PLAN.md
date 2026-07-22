# Hexapla iOS Port — execution plan (written 2026-07-21, pre-Play-production)

Self-contained plan for a future agent session. **GATE: do not start until
the owner says go** (his stated trigger: Hexapla live on Play Store
production). Read repo CLAUDE.md first for project law (KJV/TR policy,
mission, sources_text obligations); read the `evidence-discipline` and
`fleet-discipline` user skills before long work. Owner: Aleksandr Ratchkov.
Mission unchanged on iOS: evangelism — free, offline, no ads, no accounts,
no data collection, nothing locked.

## 0. Hard prerequisites (owner actions, before any code)

1. **Mac access.** Xcode is non-negotiable for iOS builds/signing/simulator.
   Options, owner's budget call:
   - Used/refurb Apple-silicon Mac mini (best long-term; also enables
     roadmap item 5's sibling ideas).
   - Cloud Mac (MacinCloud/Scaleway) for the build/debug phases only.
   - GitHub Actions macOS runners are FREE for public repos (this repo is
     public) — good for CI + unsigned builds + eventually TestFlight upload
     via fastlane, but interactive debugging still wants a real Mac.
2. **Apple Developer Program**, $99/yr, personal account (mirrors the Play
   situation). Enrollment can take days — start early.
3. Owner decisions to collect at kickoff:
   - App Store name (suggest matching Play: "Hexapla — Parallel Bible").
   - Donations on iOS: **recommend NONE at all** (see §6 — Apple's IAP
     rules make external donation links a rejection risk; the `play` flavor
     precedent = ship with zero donation code, provably absent).
   - Minimum iOS version (recommend iOS 15+; check CMP's current floor —
     Compose Multiplatform 1.8+ requires iOS 13+, but 15+ covers >95% of
     devices and simplifies audio APIs).

## 1. Architecture: Kotlin Multiplatform + Compose Multiplatform (CMP)

Owner-agreed direction (CLAUDE.md roadmap item 5). NOT a Swift rewrite.
Compose Multiplatform for iOS is production-stable (JetBrains declared iOS
stable in 2025); the owner's Opsis project (C:\Projects\Opsis) is already
CMP desktop+Android — use it as the in-house reference for build setup,
and its CLAUDE.md for CMP gotchas already learned.

**Why this fits Hexapla specifically:** the app is 6,590 lines of Kotlin
(measured 2026-07-21), single module, almost all of it either pure logic or
Compose UI. Maybe 15% is Android-platform-bound. A rewrite would forfeit the
most battle-tested code (ReaderScreen's scroll/highlight logic, the VerseMap
pivot) and create a second implementation to keep in sync with every future
translation addition. Shared code = every new translation ships on both
platforms from one commit.

### Module restructure (single `app` module → KMP layout)

```
shared/            KMP module: commonMain + androidMain + iosMain
  commonMain/      ~85% of current code + ALL assets (compose resources)
  androidMain/     actual impls now living in app/
  iosMain/         new actual impls (Kotlin, calling iOS APIs via
                   kotlinx-cinterop / platform.* bindings)
app/               Android app shell (flavors play/rustore/foss unchanged,
                   billing stays Android-only — iOS has NO billing at all)
iosApp/            Xcode project: SwiftUI shell hosting ComposeUIViewController
                   + Swift-only surfaces (WidgetKit, background audio session)
```

⚠ RESTRUCTURE RULE: Android must remain shippable at every commit — the
store release train (RuStore/Play) cannot stall for the port. Move files in
small commits, building `assembleRustoreRelease` + `bundlePlayRelease` +
`assembleFossRelease` after each. The R8 donation-strip grep in CLAUDE.md
(`unzip -p app-play-release.apk "classes*.dex" | grep -ac yoomoney` → 0)
must still pass after restructure.

## 2. Code inventory — what goes where (file-by-file, from the 2026-07-21 tree)

**commonMain as-is or near-as-is (pure logic + Compose UI):**
- Bible.kt (603) — asset registry/parsing. Replace AssetManager with
  compose-resources `Res.readBytes`; JSONObject→kotlinx-serialization or
  a minimal common JSON reader (measure startup perf on the 13MB webster1828
  lazy load — keep it lazy).
- VerseMap.kt (85), ChronoOrder.kt (112), Interlinear.kt (306 — decoders
  take Context only for string resources: swap to compose-resources
  strings), Rubrics.kt (52), plans/topics/bookmarks/notes logic.
- ReaderScreen.kt (1797), SettingsScreen.kt (687), TopicsScreen.kt (230),
  PlansScreen.kt (214), BookmarksScreen.kt (163), TranslationPicker.kt
  (127), Theme.kt (57) — Compose ports near-verbatim under CMP. Navigation:
  navigation-compose has a multiplatform artifact now; else Voyager
  (check what Opsis uses and match it).
  ⚠ PRESERVE THE HARD-WON INVARIANTS — copy these comments across:
  (a) ONE snapshotFlow collector owns all scrolling (verse jumps beat
  chapter-top resets) — the split-effect race was fixed TWICE on Android;
  do not let the port reintroduce it. (b) `liveHighlights` optimistic
  mutableStateMapOf mirror exists because DataStore emissions alone didn't
  recompose lazy items — keep the mirror pattern. (c) navigateChapter
  clamps for apocrypha slots ≥66 when switching to 66-book translations.
- Store.kt (335) — androidx DataStore has multiplatform support
  (datastore-preferences-core works on iOS since 1.1); keep the same keys
  so future migration tooling stays trivial. Notes/highlights stay keyed to
  CANONICAL KJV coordinates (the 1.4.2 rekeying) — identical on iOS, and
  export/import files remain cross-platform compatible.
- ShareImage.kt (182) — Compose-render to ImageBitmap works in common;
  actual share sheet is expect/actual (Android Intent / iOS
  UIActivityViewController).
- QR share: zxing is JVM-only. Either draw the QR from a tiny pure-Kotlin
  matrix generator (qrose library, MIT, multiplatform) or expect/actual
  (iOS CoreImage CIQRCodeGenerator). Encodes the landing page URL — same.

**expect/actual (thin):** asset access, locale/language tag, share sheet,
review prompt, open-URL, haptics, version name.

**iOS-rewritten surfaces (the real work — budget most time here):**
1. **ReadingService.kt (751) + Tts.kt (196) + Audio.kt (98) → iOS audio
   engine.** Android uses a foreground media service; iOS equivalent:
   - AVAudioSession category `.playback` + background-audio entitlement
     (UIBackgroundModes: audio) → screen-off playback.
   - Narration streaming (archive.org LibriVox + the generated
     hexapla-audio-* items): AVPlayer with the same audio_index.json /
     audio_index_gen.json data (parsing stays common; playback actual).
     Port the download-and-cache flow with URLSession background transfers.
   - TTS: AVSpeechSynthesizer with per-verse feeding via
     AVSpeechSynthesizerDelegate didFinish — SAME contract as Android
     (never pre-queue a chapter; engines drop utterances — the Android
     lesson almost certainly has an iOS cousin; keep per-verse).
   - Music bed: AVAudioPlayer looping assets/music with the x² perceptual
     volume curve (port the curve, it's just math).
   - Lock-screen/Now Playing: MPNowPlayingInfoCenter +
     MPRemoteCommandCenter (play/pause/next-chapter) + book art as artwork
     — this is the iOS analogue of the media-notification screenshot the
     stores loved.
   - Verse highlighting during narration: the offsets sidecars
     (<ch>.json per chapter) drive it — timing logic common, playback
     position polled from AVPlayer.
2. **VerseWidget.kt (114) → WidgetKit extension (Swift/SwiftUI, no way
   around it).** Port the deterministic date-seeded verse pick EXACTLY
   (same verse on both platforms on the same day — it's a small pure
   function; translate it to Swift with a shared test vector file so both
   implementations are provably identical). Book art in the widget via
   the shared asset catalog.
3. **Reminders.kt (141) → UNUserNotificationCenter** (local notifications;
   straightforward mapping).

**Deleted on iOS:** billing (all flavors' tip code — iOS ships donation-free),
locales_config.xml (iOS reads app language from system settings +
CFBundleLocalizations), Android widget glue.

## 3. Assets & app size

154MB raw bibles + 13MB dictionary + 17MB music + ~12MB other → ~60-65MB
compressed. App Store cellular-download threshold is 200MB — we're under;
ship everything bundled exactly like Android (offline-first is the
mission; do NOT introduce on-demand resources for scripture).
Options if size ever matters: music via On-Demand Resources (mirrors the
roadmap's "music download-on-demand" idea) — decide with the owner, not
unilaterally.
Fonts/shaping sanity pass required on-device: fa/ar RTL, he with cantillation,
ta (Indic shaping), zh/ja CJK, cu (Church Slavonic — check iOS system font
coverage for Unicode Cyrillic ext; may need a bundled font where Android
used system).

## 4. Localization

All 13 UI locales (326-string set) move to compose-resources
`values-*/strings.xml`-equivalents (CMP supports the same layout) — the
translations themselves carry over verbatim; keep `app_name` fallback
behavior. App Store metadata: reuse the Play listings from
store-assets/STORE_LISTING.md (5+ languages already written; App Store
supports all of them). sources_text ×13 locales is a PROMISE (CC credits,
Tweedale, Ponomar, and — when Bakar/Zohrab ship — TITUS/Gippert/Tbilisi
names): the Text sources dialog must exist on iOS from v1.

## 5. What Hexapla-iOS v1 must contain (scope fence)

Parity list: reader + split view + versemap pivot, all translations,
Compare, xrefs, red letters, translator's notes, Strong's + 1828 dictionary
+ interlinear (tap-a-word), search, plans (incl. chrono + era headings),
topics, bookmarks/notes/highlights (canonical keys, export/import
compatible with Android files), narration (streaming + TTS + music bed),
daily-verse widget, reminders, QR share, share-verse image, Text sources.
NOT in v1: donations (none on iOS, ever, pending owner), anything Android-
flavor-specific. Nothing else new — the port ships parity, features resume
after.

## 6. App Store compliance notes (researched against 2026 guidelines — the
## executing agent MUST re-verify current guideline numbers at build time)

- **Free app, no IAP, no external purchase links → simplest possible
  review.** This is why iOS ships donation-free: Apple historically treats
  in-app donation/tip flows and external payment links as IAP-rule
  territory (rejection risk far exceeding the ЮMoney trickle). The `play`
  flavor is the exact precedent: strip the code path provably.
- Privacy: no data collection AT ALL → App Privacy label "Data Not
  Collected"; privacy policy URL already exists (landing page PRIVACY.html).
- Religious content: fine per guidelines; keep store copy factual (the
  Play/RuStore listings already are).
- Archive.org streaming: outbound media streaming is fine; ensure graceful
  offline behavior (already the app's design).
- Export compliance: uses only HTTPS (exempt encryption) — declare
  ITSAppUsesNonExemptEncryption=false.
- Age rating: mirror the Play/IARC answers (13+ was target-audience there;
  Apple's questionnaire will land at 4+ or 12+ — answer honestly, no
  user-generated content, no web browsing).

## 7. Phases with acceptance gates

**P0 — Feasibility spike (1-2 sessions, Mac available):** empty CMP app
runs on simulator; one screen (TranslationPicker) + Bible.kt parsing one
asset in commonMain; kjv renders in a LazyColumn on iOS. GATE: owner sees
screenshot.
**P1 — Restructure (2-3 sessions):** shared/ module extracted, Android
builds all three flavors bit-identical features; CI green.
GATE: owner installs restructured Android build on his phone, no
regressions (he tests precisely — believe his reports).
**P2 — Reader parity (3-5 sessions):** full reading experience on iOS incl.
split view, interlinear, notes/highlights. GATE: litmus content spot-check
on-device (fa RTL, he, ta, zh rendering) + the scroll-race invariant tested.
**P3 — Audio (2-4 sessions):** narration + TTS + music + lock screen.
GATE: screen-off chapter-chain playback works; owner ear-test.
**P4 — Platform trim (2-3 sessions):** widget, reminders, share, QR,
settings polish, app icon (reuse scroll icon — owner approved it as the
brand), launch screen.
**P5 — TestFlight (1-2 sessions + Apple wait):** signing, fastlane or
manual upload, owner + a few testers (his existing tester circle).
**P6 — App Store submission:** listings from STORE_LISTING.md, screenshots
(reuse tools/make_reader_shot.py + render_text.ps1 pipeline for the
localized shots — sizes differ: 6.7" and 12.9" required), review.
Then: landing page gets its App Store button (CLAUDE.md already records
the owner wants a page update at that milestone).

## 8. Risks & mitigations

- **CMP-iOS text perf on huge LazyColumns** (long chapters, 66+ book grid):
  profile early (P0/P2) on an older device; mitigation = chapter windowing
  (already effectively per-chapter).
- **RTL inside CMP-iOS** less battle-tested than Android: test fa/ar/he in
  P0, not P4. If a blocker surfaces, the fallback for affected text is
  platform UITextView interop for verse bodies (keep as last resort).
- **DataStore-iOS** maturity: if it misbehaves, expect/actual over
  NSUserDefaults + files keeping the SAME serialized formats.
- **Owner has no Mac yet**: P0 can technically run on CI simulators via
  screenshot tests, but debugging will crawl — push for hardware first.
- **Apple review surprises**: ship the most conservative v1 (no donations,
  no links other than the landing page in an About row).

## 9. Session-zero checklist for the executing agent

1. Read repo CLAUDE.md fully; read this file; read Opsis CLAUDE.md for CMP
   setup already solved in-house.
2. Verify prerequisites (§0) with the owner; collect the three decisions.
3. Snapshot current versionCode/features — the port targets THAT parity
   list plus whatever shipped since this plan was written (diff CLAUDE.md's
   store-status section against §5's parity list and update §5 first).
4. Then P0. Keep commits small; Android green at every step.
