# Release history — 1.4.x onward

Split out of CLAUDE.md 2026-08-09. What shipped when, and the fixes that went with each release. Consult when tracing WHEN a behaviour changed; not needed to work on the app today.

- **1.4.0 submitted 2026-07-11**: owner uploaded + submitted for review
  (Play: release to closed track + full listing localization in one
  batch — 13 listing entries / 10 languages incl. pt-BR/pt-PT, es-419/
  es-US, fr-CA, zh-CN/TW/HK, ja; localized feature headers for all 10
  languages via tools/make_feature_graphic.py; CJK reader screenshots
  via tools/make_reader_shot.py). RuStore 1.4.0 confirmed submitted
  same day. GitHub release v1.4.0 published 2026-07-11.
- **Release artifacts convention**: stage builds in
  C:/Projects/Hexapla-releases/ (outside the repo tree, so they cannot
  ride along on a git add). Keep only the current release pair; every
  shipped APK is on GitHub releases, every AAB in Play artifact library.
- **1.4.1 (code 8) in tree 2026-07-11, not yet built/submitted**: UI
  localized into 7 new locales — pt, it, sv, da, ja, zh (values-zh =
  Simplified, values-b+zh+Hant = Traditional) — 12 UI locales total,
  each the full 187-string set (app_name falls back to "Hexapla";
  values-ru overrides it). Terminology follows each language's classic
  Bible (Almeida/Diodati/Karl XII/1819/明治元訳/和合本) and the Play
  listing copy. Android 13+ per-app language picker wired up
  (res/xml/locales_config.xml + android:localeConfig). Stale "six
  languages" tagline → "fourteen" in all locales AND on the landing
  page (index.html). Book names inside de_luther/es_rv/fr_martin/
  pt_almeida assets were ENGLISH since v1 (the app shows books[i].name
  from the asset) — localized via tools/localize_book_names.py
  (curated per-tradition lists; verse text verified untouched;
  he_wlc already had Hebrew OT names — its English names sit only on
  empty NT slots). TTS voice-preview samples added for
  pt/it/sv/da/ja/zh (SettingsScreen). Localized reader screenshots
  (John 1) extended to pt/it/sv/da — make_reader_shot.py now
  word-wraps Latin scripts; on those languages' Play listings lead
  with the reader shot, then the standard order. Welcome screen: the
  three button labels lacked textAlign=Center, so a wrapped 2nd line
  sat left-ragged (owner noticed on RU) — fixed in MainActivity, and
  long labels shortened so every button is single-line at 360dp
  (measured with layoutlib Roboto/NotoCJK: ru/de/fr/it/ja labels,
  ru tagline «на 14 языках» to stay 2-line on 320dp). 1.4.2
  (code 9) built + staged 2026-07-13 but NEVER UPLOADED — superseded
  the same day by 1.4.3 when RuStore approved 1.4.1 (owner decision:
  one review cycle instead of two; delete the 1.4.2 pair from
  Hexapla-releases once 1.4.3 is up). 1.4.3 (code 10) built + staged
  2026-07-13: Hexapla-1.4.3-rustore.apk / -play.aab (59.6 MB APK;
  versionCode 10, ta_irv/la_vulgata/versemap assets and signature
  verified — same upload key). Contents = 1.4.2 items (interlinear
  grammar ×13, canonical notes/highlights, bookmark order) + Tamil
  IRV + values-ta + Vulgate. Release notes ×13 in STORE_LISTING.md
  under "1.4.3". SUBMITTED by owner 2026-07-13 after his on-device
  pass (Vulgate Daniel 3 split-view behavior confirmed by-design:
  primary drives the verse grid, same as Synodal) — both stores in
  review, listings refreshed to 22/17 incl. the new ta-IN entry.
  Tamil tester's terminology review still welcome (values-ta).
  Next versionCode after 1.4.3 ships: 11.
- **1.4.0/1.4.1 verification pass (2026-07-11)** — fixed in tree:
  bottom-nav labels + reader title now shrink-to-fit instead of
  ellipsizing (M3 label budget is ~58dp at 360dp: "Einstellungen",
  "Impostazioni", "Cantique des cantiques N" all truncated);
  crash fixed: switching to a 66-book translation (or toggling
  apocrypha off) while reading an apocrypha slot ≥66 → IndexOOB in
  navigateChapter (ReaderScreen clamps AppState now); interlinear
  morphology decoders fixed — OSHM tails are POSITIONAL (old
  per-char lookup showed construct state as gender "common" on
  ~60k noun segments, Aramaic determined as "dual"), Robinson now
  decodes person+case pronouns (P-1GS etc., ~11k words), -N/-I/-K/
  PRI/NUI qualifiers and V-…-ATT (verified: Python port of the new
  decoders over every distinct code in both assets → only benign
  residue left, 7 Aramaic 'x'-placeholder segs). Lint now clean
  (app_name has tools:ignore, deliberate).
- **DATA DEFECTS FIXED 2026-07-11 (in tree for 1.4.1)**:
  (a) en_kjv.json + en_kjv_strongs.json repaired via
  tools/fix_kjv_versification.py (needs a kaiserlik/kjv clone as
  arg): Mt 2:16 ("Herod… slew all the children"), Mt 22:1, Mt
  26:38, Mk 4:40, Mk 7:11, Mk 8:8 were MISSING (scrollmapper AND
  thiagobodruk share the defect — same lineage; kaiserlik +
  Crosswire agree on authentic KJV in all 10 divergent chapters);
  non-KJV splits merged in 1 Sam 20:42, 1 Kgs 22:43, 3 Jn 14; Rev
  12:18 moved into 13:1. Canon now exactly 31,102 verses; the 10
  chapters got Strong's tags for the first time (convert_strongs
  had reverted them to plain text on count mismatch); red letters/
  xrefs now align there. NOTE: existing users' bookmarks/highlights
  in those 10 chapters shift by one verse.
  (b) sv_karlxii.json re-versified in place via
  tools/fix_sv_karlxii.py: the shipped text (= CrossWire
  SweKarlXII1873, byte-identical to Beblia's) had ALL the text but
  squeezed continental numbering into a KJV grid — 27 empty slots,
  neighbors shifted, overflow merged (Job 39:30 held NINE KJV
  verses). 15 curated splits + book re-flow; text proven
  character-identical, only redistributed. Epistle colophons kept
  (authentic Karl XII content, present in 6 other epistles).
  (c) da_1819.json REBUILT from the emg OSIS pair (github.com/emg/
  Danish-Bible-{NT-1819,OT-1871}, PD, proofread) via
  tools/convert_emg_danish.py: native continental numbering
  remapped to KJV (psalm-title merges, 11 repartitioned books,
  9 curated merges/splits, Rev 12:18→13:1); recovers all 16
  placeholder verses + Lev 6:1-7 etc. There was never an 1819 OT —
  the OT is the 1871 authorized; label updated to "Dansk Bibel,
  1819/1871" in Bible.kt and sources_text ×12 locales (store
  listings still say "1819" loosely — owner may update). The 1819
  NT prints the Johannine Comma in [brackets] (1 Jn 5:7-8) — kept
  verbatim, Comma present. convert_beblia.py now hard-fails on
  placeholder verses and documents the versification hazard.
- **Plans screen remembers the last-opened plan** (Store LAST_PLAN
  + AppSettings.lastPlanId; restores instantly, no flash) and
  plan_chrono now reads "Chronological Bible in 1 year"-style in
  all 12 locales (was the odd-one-out em-dash form).
- **Verse-level versification map (1.4.1)**: translations keep their
  authentic native numbering (Synodal/Elizabeth LXX psalter + Dan 3
  Song-of-Three, Luther/WLC Masoretic bounds + title-psalms, Martin
  merges, Meiji omissions, Byz Rom doxology at 14:24-26, 3 Jn/Rev
  12:18 tails) and pairing features pivot through assets/versemap.json
  (tools/build_versemap.py — 1452 runs, every curated site
  text-verified; Wycliffe degrades to identity in 16 rough books).
  VerseMap.kt applies it in split view (incl. secondary interlinear
  tap indexes; taps disabled on rare cross-chapter rows), Compare,
  xrefs (key + targets), red letters. Fixes the long-standing whole-
  chapter split-view offset for Synodal Psalms and psalm-title
  off-by-one vs Luther. Topics + Reminders now pivot through the
  versemap too (chapterIndexFor deleted — the old shim fixed only
  the chapter, never the verse, in Synodal psalms). Late-2026-07-12
  additions, all in 1.4.1: verse menu gained "Show original" (any
  verse → grc/wlc via the pivot, tappable interlinear words keyed to
  the ORIGINAL's own chapter/verse) and "Translator's notes" (KJV's
  7,859 {x: y} margin notes retained at parse, shown on demand;
  entry hidden when absent); follow-scroll pinned to 1x
  MotionDurationScale (the "snap" was the system animator scale
  zeroing animations — code was never wrong); Text sources is one
  tap-to-open dialog row; `foss` flavor F-Droid-ready (billing
  flavor-scoped into src/billing, no-op stub in src/foss, zero
  billingclient in foss dex/manifest; submission: IzzyOnDroid takes
  a released APK, F-Droid proper = fdroiddata MR with gradle:[foss]
  — do either after Play production). The three data-model gaps are
  now ALL CLOSED: plan days pinned to the canonical KJV chapter grid
  (commit 2464f04) and the bookmarks display-time pivot (845f588)
  landed 2026-07-12; notes/highlights rekeyed to canonical KJV
  coordinates in 1.4.2 (ReaderScreen pivots via VerseMap on write
  AND lookup; data format unchanged so export/import untouched;
  legacy keys read as canonical — identical for KJV-grid
  translations, shifts only where display was already broken).
  Also fixed: 98 "Retournez au début" scraping-junk suffixes stripped
  from fr_martin.json (Beblia web scrape artifact). ~~lut 2 Kgs 15:39
  empty slot~~ — that "cosmetic" note understated a real defect family,
  FIXED 2026-07-20, see the de_luther alignment entry in ASSET DEFECTS.
- **Welcome screen "Just start reading" now opens the Gospel of
  John** (AppState.open(42, 0) before the reader restores last
  position — owner's idea: a newcomer's first tap should land on
  something gripping, not Genesis 1), with a small caption under
  the button (welcome_read_note, ×12 locales: "an eyewitness
  account of Jesus… jump anywhere from there").
