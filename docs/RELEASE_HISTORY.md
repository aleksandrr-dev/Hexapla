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


---

# ── MOVED OUT OF CLAUDE.md, 2026-08-25 (context budget) ──

Everything below was in the project `CLAUDE.md` and is a COMPLETED RECORD. It is
kept verbatim. Nothing here is a live warning; the live ⚠ stayed in CLAUDE.md.
Reason for the move: `CLAUDE.md` is auto-loaded into every session, and at ~8k
tokens it was spending a fifth of the first turn's budget on finished history.

## The play-flavor donation regression, in full (fixed 2026-07-20)

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

▶ **The live rule that stayed in CLAUDE.md** is the grep plus its positive
control. This block is why the rule exists.

## The Locale(String) modernization — DONE, shipped in 1.6.4 / code 17

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

✅ **VERIFIED COMPLETE 2026-08-25**: `grep -c 'Locale("' Bible.kt` = **0**,
`grep -c 'Locale.forLanguageTag' Bible.kt` = **25**. The ⚠ about `Locale.of`
being API 36 against minSdk 26 is retained in CLAUDE.md's build section, because
it can still bite anyone modernizing another file.

## 1.6.3 (code 16), and the GitHub-releases correction

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

## Roadmap items that have SHIPPED (were items 0, 1b, 3 and 6)

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
