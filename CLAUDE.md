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
- **Interlinear localization (owner-approved 2026-07-12)**:
  (a) ~~1.4.2 item~~ DONE 2026-07-12, in tree for 1.4.2 (code 9):
  grammar labels in Interlinear.kt decoders moved to string
  resources — 136 morph_* strings ×12 locales, terminology table
  curated in tools/localize_morphology.py (idempotent injector;
  Russian seminary terms, Cyrillic binyanim; French Hebrew
  accompli/inaccompli; CBOL vocabulary for zh, katakana stems for
  ja; Latin binyanim kept for Latin-script locales + zh).
  decode() now takes Context. Verified: Python port of old vs new
  decoders over every distinct code in both assets (1055 Greek +
  3454 Hebrew) — Greek byte-identical, Hebrew differs only in the
  intended Tn/Ti/Tr enrichment («negative» → «negative particle»,
  225 codes). Lint clean (47 warnings = pre-change baseline).
  (b) WATCH LIST — localized Strong's LEXICONS (Russian first):
  the definitions in strongs_lexicon.json are English (Open
  Scriptures). Russian Strong's translations circulate in
  e-Sword/MyBible modules but each translation carries its
  translator's ©, though the 1890 base is PD. RESEARCHED 2026-07-12,
  verdict = permission-email path: the de-facto standard text is the
  BibleQuote lineage (github.com/BibleQuote/BibleQuote-Modules
  Strong.zip, gloss-only, complete H1-H8674 + Greek, quality ideal
  for tap-a-word, 0.46 MB deflated) — NO license anywhere; MyBible's
  module credits it «с разрешения Тимофея Ха» (personal permission).
  EMAIL Timothy Ha / BibleQuote (biblequote.org contact form,
  jesuschrist.ru; GitHub maintainer rkazakov) — draft at
  store-assets/biblequote_email_draft.txt: ask (1) permission for
  the gloss-only files in a free attributed app, (2) PROVENANCE —
  is it the 1998 Bob Jones University symphony key? (residual-rights
  question). SENT by owner 2026-07-12 — awaiting reply.
  ⚠ READ THE REPLY WITH THIS IN MIND (audit 2026-07-15): one
  (low-quality, UNVERIFIED) Russian source claims «Тимофей Ха не
  является владельцем прав на публикацию словаря Стронга» — if Ha is
  NOT the rights holder, his permission does not clear the rights and
  a "yes" is not legally load-bearing. Question (2) PROVENANCE
  therefore matters MORE than question (1) permission. Audit
  confirmed BJU's 1998 «Библейская симфония с ключом к еврейским и
  греческим словам» is real (ru.wikipedia, Конкорданция Стронга) BUT
  it is a SYMPHONY/KEY (Strong's numbers → Synodal word occurrences)
  — a DIFFERENT copyrightable layer from a gloss-only H1-H8674
  dictionary. Whether Strong.zip's glosses descend from it remains
  UNVERIFIED. Repo re-checked 2026-07-15: still license: None, no
  LICENSE file, Strong.zip = 611,637 bytes, last push 2022-02-25.
  HARD GATE: MyBible/ph4 builds embed Dvoretsky's 1958
  dictionary in 5,113 Greek entries — use ONLY the pristine
  BibleQuote greek/hebrew.htm (zero Dvoretsky, verified — the gate is
  real: Dvoretsky-merged files circulate under BibleQuote-looking
  names, e.g. a «Греческий лексикон Стронга - словарь Дворецкого»
  module). ⚠ DATE CORRECTED 2026-07-15: the old note read «© until
  ~2046» — WRONG, and wrong in the UNSAFE direction. Dvoretsky died
  3 Jan 1979 (not 1963); ГК РФ ст. 1281 = life+70 counted from 1 Jan
  of the following year → © until end of 2049, PD 1 Jan 2050. If the
  WWII +4 extension applies (ru.wikipedia's biography is explicitly
  incomplete on his wartime activity — UNVERIFIED) → end of 2053.
  Where "2046" came from is unknown. Do not unblock before 2050.
  Zhuromsky fallback is CC BY-NC-ND — BOTH the NC and the ND
  disqualify (re-verified 2026-07-15 at igr.bible, his own site:
  «© 2026, Виктор Р. Журомский. Все права защищены лицензией
  CC BY-NC-ND 4.0» — actively asserted; earlier note cited only the
  ND) + reputational flags — avoid. Tsygankov/azbyka = publisher ©
  (re-verified 2026-07-15: azbyka's own record, «сост. Цыганков
  Ю. А.», СПб.: Библия для всех, 2005, ISBN 5-7454-0933-9; the
  1890 Strong's base is PD but Tsygankov's compilation+commentary is
  a modern authored work), dead end. Architecture
  when a clean source lands: per-locale lexicon file keyed by the
  same H/G ids, chosen by UI locale, English fallback; same model
  later for DE/ES/PT.
- **Translation watch list** (all deity-verse-gated, pipeline ready):
  Matthew Bible 1537 (John Rogers, "Thomas Matthew" — Tyndale's NT +
  Pentateuch + prison OT (Josh–2 Chr, first printing) + Coverdale fill;
  TR, PD; blocker: no machine-readable source — 1537 spelling is
  facsimile/EEBO-TCP only, the modernized New Matthew Bible is ©).
  en_tyndale.json COMPLETED 2026-07-11 (was Gen + 9 NT books): now 33
  books, +5,961 verses via tools/complete_tyndale.py (studybible.info +
  biblestudytools mirrors of the same PD Fedosov digitization as the
  shipped books — those stay byte-identical; KJV-versified, all counts
  match; litmus «God was shewed in the flesshe» ✓, Comma present in
  Tyndale's parentheses; 4 genuinely-absent verses left empty: Ex
  40:14, Lev 27:18, Num 7:22, Gal 5:21). Wycliffe versemap curated
  same day (44 runs; versemap.json now 1496 runs, zero identity
  fallbacks). Tyndale label → "1525/1531".
  Karl XII 1703 Apokryferna — confirmed live at kxii.se (Judith,
  Wisdom, Tobit, Sirach, Baruch, 1-2 Macc, Esther/Daniel additions;
  per-chapter pages, no bulk download; Litteraturbanken-based, text PD
  but transcription license unstated — permission email
  (store-assets/kxii_email_draft.txt, Swedish + English) SENT by
  owner (confirmed 2026-07-13) — awaiting reply; WHEN THEY REPLY YES: build_meiji_nt.py-style
  scrape into the sv asset's apocrypha slots (indexes 66+, alongside
  the 1873 BFBS canon), credit kxii.se in sources_text ×12 locales,
  deity-litmus not applicable to apocrypha but spot-check text
  quality vs the Litteraturbanken facsimile).
  Tamil — INTEGRATED IN TREE 2026-07-13 for 1.4.3 (code 10): IRV
  Tamil 2019 (ebible.org tam2017, Bridge Connectivity Solutions,
  CC BY-SA 4.0 — same publisher/license/pipeline as Sanskrit), the
  21st translation / 16th language, full 66 books. LITMUS 7/7
  (verified from the converted asset): 1 Tim 3:16 «தேவன்
  சரீரத்திலே வெளிப்பட்டார்», Comma present, Acts 8:37 + Rom 16:24
  present, Joseph at Lk 2:33, church of GOD at Acts 20:28. The
  mirror case of Hindi: same IRV project, but the Tamil OV base
  (1871 Bower/Union) predates the 1881 RV, so TR readings survived
  the modernization. Converter tools/convert_tamil_irv.py; whole
  text sits on the KJV grid except 3 Jn 14/15 (versemap-curated);
  values-ta UI locale (344 strings, native Tamil grammar terms —
  native-speaker review welcome, ask the Tamil tester); ta-IN Play
  listing + screenshots in tree (reader shot + feature graphic via
  tools/render_text.ps1 — WPF/DirectWrite shaping bridge, because
  PIL cannot shape Indic scripts; reuse for any future Indic
  language). Owner asked for it for his Tamil/Malayalam tester.
  Malayalam — DEAD END as of 2026-07-13 (verified): the only
  machine-readable PD/CC texts — 1910 Sathyavedapusthakam (tfbf
  GitHub / ebible mal2015) and Malayalam IRV (ebible mal) — are
  RV-conformed: «അവൻ» (He) at 1 Tim 3:16, no Comma, Acts 8:37 +
  Rom 16:24 omitted, "his father" at Lk 2:33. TR-faithful Bailey
  1843 / Gundert 1868 are facsimile-scan-only. RE-CHECK yearly:
  Benjamin Bailey Foundation transcription; ebible.org mal* list.
  Tagalog — OWNER DECISION PENDING (researched 2026-07-13): 1905
  Ang Biblia is ASV/CT-based (fails litmus, verified) BUT «Ang
  Malayang Biblia» (AMB, github.com/SalitaNgDiyos, CC BY-SA 4.0,
  TheWordAMB.nt module) is a TR-based Tagalog NT passing 7/7 with
  every word Strong's-tagged; exact KJV NT grid. CAVEATS for the
  owner: modern conversational register (po/opo honorifics), Luke
  19:13 renders minas as «500,000 piso» (pesos in the verse text),
  iglesia→Kongresyon, bautismo→lublob (Baptist-leaning), digits for
  numerals; living small-team translation (2017-2025), not a
  classic. Textually clean; stylistically a Meiji-plus call.
  Owner decided 2026-07-13: DON'T ship yet — ask the team first
  (store-assets/amb_email_draft.txt: which release is stable; is a
  traditional-renderings edition planned; attribution wording).
  Email SENT by owner 2026-07-13 — decide when they reply.
  Latin — APPROVED + INTEGRATED IN TREE 2026-07-13 for 1.4.3
  ("vul", la_vulgata.json, 73 books incl. deuterocanon in the
  apocrypha slots, 35,811 verses, «Vulgata Clementina, 1592 (LA)»):
  the Clementine Vulgate, Tweedale/VulSearch edition (PUBLIC DOMAIN
  with acknowledgment request — honored in sources_text ×13;
  Quasimodo.zip source archive, converter
  tools/convert_vulgate.py strips the /-linebreak and \\-paragraph
  markers, Latin-1 → UTF-8). 22nd translation / 17th language.
  Litmus: Comma PRESENT, Acts 8:37 + Rom 16:24 PRESENT, ecclesiam
  Dei, qui est in cælo; accepted deviations: 1 Tim 3:16 «quod
  manifestatum est» and Lk 2:33 «pater ejus» — owner approved
  after establishing the shipped WYCLIFFE (translated FROM the
  Vulgate) already carries BOTH readings («that thing that was
  schewid in fleisch»; «his fadir and his modir»), so no new
  doctrinal exposure; the litmus's purpose (block post-1881
  critical-text intrusion) is untouched — Jerome predates the
  TR/CT split by 11 centuries. Versemap: Gallican LXX psalter
  via the existing engine + VUL_PSALTER overrides (Ps 2/4/16,
  text-verified); Daniel via the syn/csl LXX special-case;
  Esther 10:4-16:24 + Dan 13-14 unmapped additions (Wycliffe
  precedent); wyc-shared Vulgate-tradition curation (Gen split
  out — Clementine merges 5:32 into 5:31 where wyc holds it in
  6:1); vul-specific curated books 0/3/5/6/8/10/17/29/42/65
  pre-empt the repartition engine (its flat cumulative pairing
  SMEARED local intra-chapter splits across whole books — caught
  by the pair-report eyeball pass; every curated run text-verified
  against the Latin, incl. the Vulgate Job 39-41 reflow). 1792
  runs / 15 mapped translations. Beza's TR-perfect Latin NT /
  Junius-Tremellius: scan-only, no digitization exists (verified
  across e-Sword/CrossWire/CCEL/GitHub; latinbible.com sells page
  images) — the OCR-project idea remains on the far watch list.
  Nova Vulgata: Vatican © + CT, ruled out. No Play listing for
  Latin (Play has no Latin listing language); no UI locale.
  Hindi — DEAD END as of 2026-07-11 (verified, like Korean): every
  machine-readable Hindi Bible FAILS the litmus — BSI OV re-edit,
  IRV 2019 (the only clean CC BY-SA text), Biblica CV all read «वह
  जो» ("he who") at 1 Tim 3:16, no Comma, "उसका पिता" at Lk 2:33
  (Acts 8:37 present in OV/IRV; IRV drops Rom 16:24 = CT marker).
  The OV's NT absorbed RV/critical readings post-1881. Pre-1881 OV
  editions likely pass but are SCAN-ONLY (e.g. archive.org
  holybibleinhindi00alla — an OCR project if ever). TBS is making a
  fresh Hindi TR translation (only John published; will be TBS ©) —
  RE-CHECK tbsbibles.org/news/698804 yearly.
  Sanskrit — APPROVED + INTEGRATED IN TREE 2026-07-11 ("san",
  sa_nt.json, 7,958 verses, registered in Bible.kt as «संस्कृतम् —
  Sanskrit NT, 1851 (SA)»; CC BY-SA attribution ×12 locales;
  versemap 13 translations/1497 runs). FOLDED INTO 1.4.1 (owner
  decision 2026-07-12 while RuStore moderation queued 1.4.0):
  artifacts re-cut, versionCode 8 verified, sa_nt.json + versemap
  confirmed inside the APK. 1.4.1 = 20 translations / 15 languages —
  update release notes + STORE_LISTING copy accordingly before
  submitting. The eBible sandev edition turned out BETTER
  than scoped: Acts 8:37 PRESENT, Lk 2:33 names Joseph (तस्य माता
  यूषफ् च), all 260 chapters KJV-shaped (3 Jn 14/15 native split
  mapped; source's empty-[] Rev 12:18 dropped — its 13:1 prints the
  KJV arrangement). The ONE standing Griesbach deviation: Acts 20:28
  "church of the Lord (प्रभु)" vs TR "of God" — owner accepted.
  Litmus: 1 Tim 3:16 «ईश्वरो मानवदेहे प्रकाशित», Comma present,
  Jn 1:1 स्वयमीश्वर. 1.4.2 remainder: nothing — data complete.
  Original scoping: the 1808
  Serampore original is effectively unobtainable (no scans survive
  accessibly); its successor, the 1851 Yates/Wenger Calcutta NT, IS
  machine-readable: ebible.org id `sandev` (SanskritBible.in, CC
  BY-SA 4.0, Devanagari, USFM zip). LITMUS MIXED — TR-core with
  Griesbach deviations: 1 Tim 3:16 «ईश्वरो मानवदेहे प्रकाशित» PASS,
  Comma Johanneum PRESENT, Jn 3:13/Rom 9:5 pass; but Acts 8:37
  OMITTED, Acts 20:28 "church of the Lord", Lk 2:33 "his father".
  Meiji-precedent call for the owner. If adopted: NT-only (like grc),
  converter MUST leave empty slots for omitted TR verses (Acts 8:37)
  to keep KJV indexing; CC BY-SA needs license+link in sources_text.
  OT = scans only (archive.org holybibleinsansc00gill + 02-04weng,
  1848); OCR scoped at 400-800 proofreading hours — NOT feasible;
  email SanskritBible.in about their OT progress instead.
  Guðbrandsbiblía 1584 (Icelandic) — PERMISSION DECLINED 2026-07-12
  by Halldór Elías Guðmundsson (framkvæmdastjóri, Icelandic Bible
  Society): they are building an authoritative digital text of BOTH
  Guðbrandsbiblía and Viðeyjarbiblía with the Digital Bible Library
  (based on Jón Hjörleifur Stefánsson's work); the current website
  text has known flaws ("slightly flawed", editorial issues); "we
  are not going to allow any further publication of those texts"
  until the DBL work is finalized — low priority, "not going to
  come out for a while". CLOSED — do NOT scrape biblian.is. Both
  Icelandic texts blocked. RE-ASK when the DBL edition ships
  (check dbl.bible / re-email hib@biblian.is yearly); the DBL text
  would also be cleaner than what we'd have scraped. Earlier
  scoping (litmus PASS, no verse numbers in prose) remains valid
  background for that day. History:
  Þórdís (Árnastofnun): they do NOT have the digital text; it IS
  downloadable section-by-section at biblian.is/gudbrandsbiblia/
  (Icelandic Bible Society). She warns the archive.org copy is full
  of scanning errors — DO NOT use archive.org for this. SCOPED
  2026-07-11: complete (66 + 11 apocrypha books), modernized
  spelling, per-chapter WordPress pages (open REST API, easy
  scrape); LITMUS: 1 Tim 3:16 «Guð er opinberaður í holdinu» PASS,
  Comma PRESENT, Acts 8:37 present, Lk 2:33 "hans faðir" = Luther's
  own reading (same as shipped de_luther — acceptable). TWO GATES:
  (1) transcription is "Allur réttur áskilinn" (all rights
  reserved) — email hib@biblian.is, draft at
  store-assets/biblian_email_draft.txt; (2) PROSE HAS NO VERSE
  NUMBERS (pericope paragraphs; Mt 2 = 6 paragraphs for 23 verses;
  only Psalms/poetry are verse-per-paragraph) → 150-400+ h
  segmentation UNLESS Jón Hjörleifur Stefánsson's working files
  carry verse structure — ASK THIS in the permission email; a yes
  collapses it to a normal converter. Plan B in same email:
  Viðeyjarbiblía 1841 (biblian.is/videy/, presumably versified,
  needs its own litmus pass).
  Korean — no PD TR text exists (개역한글 fails 1 Tim 3:16 with 그는;
  한글킹제임스/흠정역 copyrighted).
  LXX apocrypha — ⚠ RE-SCOPED 2026-07-15, the old note («no
  clean-licensed tagged text (CATSS restrictive)») was OVERBROAD and
  read in practice as "LXX apocrypha can't ship". The truth: it CAN
  ship, just WITHOUT interlinear. The restriction was never on the
  LXX text — only on CATSS's MORPHOLOGY layer. Split the two:
  (a) TEXT — SHIPPABLE TODAY: github.com/nathans/lxx-swete, "The
      Greek text and its annotations in the data directory are
      published under the terms of the Creative Commons
      Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
      license" — same license family + attribution pipeline as the
      shipped Tamil IRV and Sanskrit assets. Swete (1909) via the
      Open Greek and Latin First1KGreek digitization, ZERO CATSS
      dependency. Full apocrypha set verified present (Esdras A,
      Judith, Tobit, 1-4 Macc, Odae, Wisdom, Sirach, Psalms of
      Solomon, Baruch, Ep. Jeremiah, Susanna, Bel, both Daniel
      recensions). ALREADY VERSIFIED — one token per line prefixed
      book.chapter.verse (e.g. «21.1.1 BΙBΛΟΣ / 21.1.1 λόγων»;
      Sirach prologue at 34.0.0), so it is converter-ready, NOT a
      segmentation project (contrast the Guðbrandsbiblía prose trap).
      Deity-litmus n/a for apocrypha (same as the Karl XII note).
      ⚠ OWNER DECISION: whether a Greek LXX apocrypha belongs in the
      app at all, and if so where (grc is currently NT-only).
  (b) INTERLINEAR on it — still genuinely blocked: every mainstream
      TAGGED LXX inherits CATSS ("not to be used for commercial
      purposes without prior written consent", signed User
      Declaration): eliranwong/LXX-Rahlfs-1935 is CC BY-NC-SA AND
      CATSS-derived; CenterBLC/LXX derives from it; openscriptures/
      GreekResources CC BY 4.0 covers only their lemma corrections,
      text still comes from CCAT. RE-CHECK YEARLY: STEPBible TAGOT
      would be CC BY 4.0 and covers apocrypha, but its morphology is
      "based on CCAT" and it is still unposted ("Datasets coming…").
  Also worth recording: RAHLFS 1935 IS PUBLIC DOMAIN — Rahlfs died
  8 Apr 1935, German life+70 → PD since 1 Jan 2006. The © people
  associate with "Rahlfs" attaches to Rahlfs-Hanhart (2006), a
  different, later revision by the German Bible Society.
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
  from fr_martin.json (Beblia web scrape artifact); lut 2 Kgs 15:39
  is an empty slot in the asset (unmapped, cosmetic).
- **Welcome screen "Just start reading" now opens the Gospel of
  John** (AppState.open(42, 0) before the reader restores last
  position — owner's idea: a newcomer's first tap should land on
  something gripping, not Genesis 1), with a small caption under
  the button (welcome_read_note, ×12 locales: "an eyewitness
  account of Jesus… jump anywhere from there").

## ⚠ ASSET DEFECTS FIXED 2026-07-15 (owner-approved; NOT yet rebuilt/shipped)

Both rewrite SHIPPED assets. `.json.bak` backups sit beside each. Next build
must include them; owner should spot-check on-device before submitting.

- **de_luther.json was 75.9% CORRUPTED and had been since v1.1.** Not markup —
  destroyed characters. It is an unproofread OCR of the Bolsinger/
  luther-bibel-1545.de digitization. Census over 4,010,960 chars of German:
  **ä = 0** (master: 11,719), ö = 1, Ä/Ö/Ü = 0. Zero ä in a four-million-char
  German Bible is impossible. 23,508 of 30,964 comparable verses damaged, all
  66 books, none below 50%. über→uber (1,553), soll→soil (1,499), König→Konig
  (1,201), Salomo→Saiomo, daß→dafi/dad/daü. **The deity litmus verse itself
  shipped broken: 1 Tim 3:16 read «Und kundlich GRAFT ist das gottselige
  Geheimnis» (groß → graft).**
  REPAIRED via tools/fix_de_luther.py from the SAME digitization's clean
  upstream — Zefania SF_2009-01-20_GER_LUTH1545 (sourceforge.net/projects/
  zefania-sharp; CrossWire ships it as GerLut1545). Since the app already
  ships this transcription, the clean upstream adds ZERO new licensing
  exposure. Litmus re-run on the master before use: 1 Tim 3:16 «GOtt ist
  offenbaret im Fleisch» PASS, Comma present, Acts 8:37 present, Rom 16:24
  present, Jn 1:1 PASS — same edition, same readings, pure character repair.
  RESULT: 25,915 verses repaired, ä 0→11,688, accented 3.56→14.14 per 1000,
  book/verse counts unchanged (66 / 31,164).
  ⚠ 78 verses deliberately NOT repaired: genuine German-native-vs-KJV-grid
  numbering offsets (all of 2. Samuel 19 is shifted by +1 — our 19:1 IS the
  master's 19:2). Repairing those by coordinate would OVERWRITE SCRIPTURE with
  the neighbouring verse. The audit agent misreported these as the ONLY issue
  and called the other 122 low-ratio verses "offsets" too — they were the
  worst-DAMAGED verses. Both errors sat in the same bucket; the discriminator
  is "does a neighbour match better?", NOT a similarity threshold and NOT
  length (2. Sam 19:7's offset pair has a length ratio of 1.06).
- **la_vulgata.json shipped 194 editorial markers in v1.4.3** (2026-07-13) as
  literal angle brackets: «Alleluja. <Aleph>Beati immaculati in via». 29
  distinct — Hebrew acrostic letters <Aleph>..<Thau> in Psalmi 118 (=119) and
  Lamentationes 1-4; Canticum speaker rubrics <Sponsa> x19, <Sponsus> x14,
  <Chorus>; <Prologus>. tools/convert_vulgate.py never stripped them.
  STRIPPED via tools/fix_vulgate_markers.py (owner chose this 2026-07-15 over
  surfacing them as headings, which needs UI work).
  ⚠ THIS DISCARDED REAL INFORMATION, reversibly: <Sponsa>/<Sponsus> identify
  WHO IS SPEAKING in Song of Songs and print Clementine editions carry them as
  rubrics. The markers are still in the source archive — a later version can
  reinstate them as structure.
- ru_synodal.json: 3 verses carry escaped OSIS (&lt;note&gt; wrapping a ~600-
  char LXX variant at Иов 2:9; a constellations note at Иов 9:9; a stray
  &lt;title type="psalm"&gt; at Псалтирь 143:15). OWNER CONFIRMED the app
  RENDERS this markup to readers. narrate.py keeps it out of the audio
  (strip_ru_markup) but **THE ASSET IS STILL UNFIXED** — BibleRepo.parseAsset
  strips {x:y} notes and knows nothing about escaped tags. Still to do.
- **⚠ ~HALF THE PSALTER IS MISSING ITS TITLES — ru_synodal AND cu_elizabeth.**
  Found 2026-07-15 while fixing the Psalm 144 stray title; NOT yet fixed, needs
  a source and an owner decision. Measured against the app's own Clementine
  Vulgate (same LXX psalter, kept all its titles):
      Vulgate has a title in 144 of 150 psalms
        title is its OWN verse : 46  -> CU missing 5,  SYN missing 7
        title INLINE with text : 98  -> CU missing 73, SYN missing 74
  THE RULE IS EXACT: a title that occupied its own verse SURVIVED; a title
  sharing verse 1 with content was DROPPED by the converter. Examples are not
  obscure — Ps 22 (the Shepherd Psalm) opens «Господь - Пастырь мой» with no
  «Псалом Давида.»; Ps 26 and Ps 16 likewise. The Psalm 144 title that was
  merely MISPLACED (onto 143:15, now fixed) was a survivor of the same bug.
  NOT a versification defect: the titles were inline in v1, so no verse counts
  changed — versemap/bookmarks/notes/highlights are unaffected. It is a text-
  completeness defect only.
  ⚠ The ~74 figure is HEURISTIC (per-language title-prefix matching); direction
  and scale are solid, the exact count is not. tools/ scratch analysis compared
  vul/cu/syn verse 1 across all 150.
  ✅ SYNODAL REPAIR DONE 2026-07-16 (owner-approved): 56 titles restored via
  tools/fix_ru_psalm_titles.py — title-prefix-only prepends to v1, every edit
  body-gated at ratio 1.00 against the source, verse counts unchanged (2,533).
  Vulgate census: inline-missing 74 -> 28 (residual ≈ the ~15 genuinely absent
  from both PD digitizations + census-regex blind spots). Backup:
  asset-backups/ru_synodal.json.pretitles.bak. TWO GATES CAUGHT IN DRY-RUN:
  Пс 139 skipped — its v1 IS an own-verse title and rst carries a stray extra
  «Псалом.» that would have been doubled onto it (own-verse-title guard now in
  the script); Пс 151 RESOLVED 2026-07-16: stays UNTITLED. The module's «на
  единоборстов с Голиафом» is a typo'd editorial paraphrase of the LXX
  heading, NOT a Synodal superscription — azbyka's Synodal prints no title
  there, only the footnote «У Евреев этого псалма нет…», and rst has no
  Ps 151. One typo'd witness vs a contradicting second = do not add.
  The Slavonic (cu_elizabeth) remains OPEN — see (c) below.
  SOURCE RESEARCH DONE 2026-07-15 (Opus agent, byte-level verification):
  (a) ru_synodal.json PROVENANCE SOLVED: it was converted from the CrossWire
      SWORD module **RusSynodal** (crosswire.org rawzip). Proven byte-level:
      the module itself carries our two escaped-markup leaks VERBATIM (the
      Ps 143:15 «&lt;title type="psalm"&gt;Хвала Давида.» and the Job 2:9
      &lt;note&gt; are literal escaped text IN THE MODULE — a module data bug);
      the converter stripped all real <title> elements (the title-dropping
      defect) and only those two escaped ones passed through. The 83-book
      canon incl. «Лаодикийцам» = SWORD Synodal versification, ditto.
  (b) RECOVERY (Synodal): module has clean <title type="psalm"> for 31
      psalms, all 31 currently missing (list in the research transcript);
      lowercase «псалом» needs normalizing to «Псалом». The ascent/hallelujah
      superscriptions the module lacks (Песнь восхождения, Аллилуия) are in
      gratis-bible/bible ru/rst.xml (same Fedosov PD digitization, titles
      inline behind a "(N:N)" prefix; en-dash vs hyphen in bodies). Union =
      verified floor of 58 recoverable titles; ~15 (incl. Аллилуия at Ps
      148-150) are absent from BOTH PD digitizations — not recoverable there.
      LICENSES QUOTED: RusSynodal.conf "DistributionLicense=Public Domain";
      rst.xml <rights> "…Sergej A. Fedosov's Slavic Bible for Windows…Public
      Domain". Repair shape: mirror fix_de_luther.py — coordinate-anchored,
      TITLE-PREFIX-ONLY prepend to v1, body-match gate
      (SequenceMatcher autojunk=False), verse counts asserted unchanged,
      backup outside assets/.
  (c) cu_elizabeth.json: PROVENANCE = CrossWire **CSlElizabeth** (verified,
      matches our asset exactly) — the module has ZERO <title> elements; our
      asset is a FAITHFUL copy of a source that never had the надписания.
      SOURCE HUNT DONE 2026-07-16 (Opus agent, verbatim-quoted evidence):
      ★ **Ponomar Project** (github.com/typiconman/ponomar,
        Ponomar/languages/cu/bible/elis/Psalm.text) is THE source: complete
        Elizabeth psalter, **135 надписания / 151 psalms** as structured
        verse-0 fields (Ps 22 «Ѱало́мъ дв҃дꙋ,», Ps 119 «Пѣ́снь степе́ней,»).
        PROVEN: our asset is a civil transliteration of EXACTLY this text
        (Ps 22:1/143:1/144:1 reduce perfectly under the asset's own
        convention). TWO GATES, both owner calls:
        (1) ORTHOGRAPHY — Ponomar is full CS (titlos, ѣ ѡ ѧ); titles need
            transliteration to civil spelling = an EDITORIAL ACT (nomina
            sacra expansion гдⷭ҇ь→Господь, terminal-ъ elision, ѣ→е etc.).
            Tractable: the missing titles are a small formulaic set — a
            hand-curated table like the project's other curated converters.
        (2) LICENSE — OWNER DECISION 2026-07-16: PROCEED WITHOUT the email,
            on the PD reasoning (1751 text PD by age; transliteration strips
            the accentuation, the only arguably-© layer; the extracted titles
            are short formulaic PD liturgical phrases). This is a deliberate,
            documented deviation from the usual ask-first pattern — owner:
            "skip the email for now. if we get feedback on it, we can act on
            it then." The draft stays at store-assets/ponomar_email_draft.txt
            in case feedback arrives. Ponomar should still be CREDITED in
            sources_text ×13 locales before the titles ship in a release
            (TODO — not yet done).
      ⚠ PARTIAL RESTORATION DONE 2026-07-16 via tools/fix_cu_psalm_titles.py:
      **14 titles applied** — only those whose every word is attested in the
      ~2,400-verse-pair parallel corpus between Ponomar (full CS) and our
      asset (civil), the transliteration LEARNED from that corpus rather than
      hand-written (the ru_stress lesson). Gates, all passing: reliable-word
      accuracy 99.93% case-folded; hold-one-out reconstruction of the 58
      KNOWN titles = 31 exact + 26 flagged-unknown (safe) + 1 punctuation
      variance + **0 silent-wrong** (the gate that matters). Bugs the gates
      caught on the way: reverential-capitalization splits («его»/«Его»)
      disqualifying common words; Ponomar's parenthesized Alleluia titles
      losing their lead paren; NFD accent-stripping destroying й (breve) in
      suggestions.
      ✅ ALL 69 CU TITLES APPLIED (14 corpus-proven + 55 via owner-delegated
      review, 2026-07-16). The owner's review notes were RUSSIAN-SYNODAL
      renderings («Псалом Давида», «Песнь восхождения») of the Slavonic
      entries; the CU titles were kept SLAVONIC («Псалом Давиду», «Песнь
      степеней», «Аллилуиа») because the asset's own shipped text uses those
      forms (Пс 3:1 «Псалом Давиду, внегда отбегаше…» since v1) — Russian
      titles would clash with Slavonic bodies. Flagged to the owner with an
      easy override; his notes were applied as CONTENT decisions (Пс 151
      titled, proper names capitalized, ѱ→пс charmap gap fixed). Final list:
      C:/Projects/Hexapla-releases/cu_titles_final.txt. Backups:
      asset-backups/cu_elizabeth.json.{pretitles,prereview}.bak.
      SYNODAL follow-ups from the same review (tools/fix_ru_titles_owner.py):
      Пс 133 «Песнь восхождения.» — a GAP THE OWNER CAUGHT, the automated
      pass covered only 119-132. Пс 151 was briefly titled per owner
      dictation, then REVERTED when he re-delegated («go with what you think
      is right for the text»): the Synodal edition prints NO superscription
      at Ps 151 (azbyka witness, footnote only) — SYNODAL 151 STAYS
      UNTITLED while the SLAVONIC keeps its long title, because the two
      EDITIONS genuinely differ there. Per-edition fidelity, final.
      FALLBACK: my-bible.info has a complete CIVIL-script CS psalter (no
      transliteration needed) but NO stated license and murky provenance —
      strictly weaker. DEAD ENDS (verified): rusbible.ru IS the gap (drops
      unnumbered titles, keeps numbered ones — explains the 73/98 vs 5/46
      pattern exactly); Wikisource has no CS psalter transcription; azbyka/
      bible-center are publisher-© and JS-rendered; orthlib.ru is legacy
      "HIP"-encoded .rar service books. CrossWire has exactly one cu module.
- en_kjv stray `</title>` (Additions to Esther 10:4) and zh_cuv_s/t `<WAHb>` x2
  (Joshua 24:14, upstream-Traditional defect) — FIXED 2026-07-15 via
  tools/fix_remaining_markup.py, owner-approved. audit_asset_markup.py now
  reports ALL 23 ASSETS CLEAN.
- TOOLS: tools/audit_asset_markup.py scans every asset for this class of
  leakage. Run it before any release. It found 6 of 23 assets dirty.
  ⚠ A MARKUP REGEX CANNOT SEE SILENT CORRUPTION: it found 20 de_luther verses;
  the real number was 23,508 — an undercount of ~1,175x, because 13,781 verses
  differ only by stripped umlauts with no markup to match. Silent damage needs
  a REFERENCE TEXT, not a pattern.

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
4. Self-generated narration (Kokoro for EN, Piper-or-newer for RU,
   host on archive.org) — fills 22 KJV books LibriVox lacks + enables
   Russian audio. FULL EXECUTION PLAN: tools/NARRATION_PLAN.md
   (written 2026-07-13, self-contained for a cheaper-model session;
   honor its ⚠ GATE markers — voice licensing, owner voice pick,
   stress-dictionary quality, ReadingService diff review).
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
