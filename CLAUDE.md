# Hexapla — project context for Claude sessions

Offline parallel Bible app for Android. Kotlin + Jetpack Compose, single
module, no backend, no analytics. Owner: aleksandrr-dev (GitHub).
Mission: evangelism — maximize reach, keep everything free, nothing locked,
collect no data.

▶ **AUTO-LOADED INTO EVERY SESSION — SO IT HOLDS ONLY WHAT IS TRUE NOW AND
NEEDED OFTEN.** A completed record belongs in a topic doc; a ⚠ that can still
bite belongs here or is pointed at from here — never silently dropped. Condensed
2026-08-09, -08-25, -08-28, **-09-07 (829 -> ~350 lines)**. **Nothing was ever
deleted:** moved blocks sit verbatim under a dated `── MOVED OUT OF CLAUDE.md ──`
marker at the end of `docs/NARRATION.md`, `docs/TRANSCRIPTION.md`,
`docs/RELEASE_HISTORY.md`, `docs/ARCHITECTURE.md`, `store-assets/STORE_LISTING.md`.
▶ **The two ★★ INDEX sections below are POINTERS, not the record.** Each bullet
carries the bite so a session knows whether it must go read the full block; when
you are about to act in that area, go read it.

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
| a render/QA defect class, a screen, or why an instrument was wrong | `docs/NARRATION.md`, under `── MOVED OUT OF CLAUDE.md, 2026-09-07 ──` — the full text of every block the ★★ NARRATION & RENDER QA index points at |
| the Þorláksbiblía ø retrofit, Matthew's completion, the Haiku test | `docs/TRANSCRIPTION.md` — the full text behind the ★★ TRANSCRIPTION index |
| what shipped when, and why a behaviour changed | `docs/RELEASE_HISTORY.md` |
| why a UI/service/widget bug must not be reintroduced | `docs/ARCHITECTURE.md` |
| whether a question is already CLOSED (and where its evidence is) | `docs/SETTLED.md` — the decisions ledger. ⚠ It closes QUESTIONS; it is never a count to quote |
| store listing texts, screenshot order, RuStore/Play upload procedure | `store-assets/STORE_LISTING.md` |
| the KJV re-render in the owner's voice | `tools/KJV_VOICE_RUNBOOK.md` |
| transcribing a Karl XII strip | `research/KXII_AGENT_BRIEF.md` — read it BEFORE touching a strip |
| starting an Icelandic (Þorláksbiblía) book | `python tools/thorlaks_chunk_kit.py --book <Name> --vol N --pages a-b` — builds prep + coverage + sheets + verse grid + report skeleton, 0 tokens; pastes `research/THORLAKS_CONVENTIONS.md` and REFUSES while a convention there is OPEN |
| why a render carried a tail defect, how repairs work now | the newest `RENDER_GATE_BRIEF_*.md` in `Hexapla-releases` (`ls -t … | head -1`) |
| what is actually running (live checks, not logs) | run **`/status`** (`.claude/skills/status/`) |
| adjudicating many diacritics/uncertain glyphs at once | `tools/contact_sheet.py` — tile the crops into ONE image; separate zoom reads cost ~8x more |
| the ø rate of a BOOK (never hand-count it) | `tools/thorlaks_o_rate.py --book <B>` — per page AND whole-book, each shared boundary verse counted once, and it CONTROLS itself against the hand counts recorded in the page records. **0 model tokens.** ⚠ A page whose control disagrees is a finding about that page; do not tune the rule until it fits |
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

- **The LIVE transcription campaign is the Icelandic Þorláksbiblía 1644.**
  ⚠⚠ **NO BOOK NAME IS WRITTEN HERE ON PURPOSE** — derive with
  `python tools/thorlaks_corpus_audit.py` and `thorlaks_part_check.py --book <B>`,
  and take the next chunk from the ONE current handoff, never from a page note.
  Folio↔index navigation for all three volumes AND the ⚠ «Cap. N»
  chapter-numbering rules (subtler than a summary here can carry — a marginal
  «Cap. N» is authoritative, but a verse-level shift can go unmarked) are in
  `research/THORLAKS_CAMPAIGN.md`. Volunteer overlap is SETTLED (owner,
  2026-08-10): two Icelandic Bibles is the intended outcome.
  ✅ **THE APOCRYPHA IS IN SCOPE — OWNER RULED 2026-09-08**
  («in scope as in yes, we will transcribe/render it»). Sirach + 1-2 Maccabees,
  ~114 pages of v2.
  ⚠⚠ **BUT THE AUDIT'S DENOMINATOR IS STILL 31,102 — THE PROTESTANT CANON —
  AND DOES NOT ENUMERATE THOSE BOOKS.** So it could still print
  «31102/31102 OK» with the whole apocrypha untranscribed. Until the books are
  enumerated with real per-chapter expectations, report «N of the PROTESTANT
  canon; apocrypha in scope, un-enumerated» — never a bare «complete».
  ✅ `thorlaks_corpus_audit.py` now prints that caveat on EVERY run, including
  a clean one, which is the run that needs it.
  ▶ `research/_evidence/thorlaks_ot_apocrypha_scope_2026-09-07.md`.
  ⚠ v1's page geometry differs (472x635 vs ~331x484) — prep zoom and crop boxes
  are calibrated for v3 and **cannot be assumed to carry over.**
- **Karl XII 1703 (Swedish) apocrypha — the PREVIOUS campaign, all but done.**
  ⛔ Do not call it finished from this line: derive with
  `python tools/karlxii_apoc_corpus_audit.py`, then read the `Resume:` line at
  the TOP of that book's own `research/karlxii_<book>.md`. **Never take the next
  book from a handoff summary and never from a page note** — "Baruch starts 696"
  is a page location, not a work queue, and a session lost time to exactly that.
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

## ★★ NARRATION & RENDER QA — INDEX

▶ **Full reasoning for every line below: `docs/NARRATION.md`, under
`── MOVED OUT OF CLAUDE.md, 2026-09-07 ──`.** Each is a bug that already
happened. **Read the matching block before touching that area** — several of
these were re-derived from scratch by a session that trusted a summary.

- ⚠⚠ **ylt HAS FIVE KNOWN DEFECT CLASSES AND VALIDATED SCREENS FOR TWO.**
  Repeat (`qa_selfrepeat`) and novel-append (`qa_asr_sweep`) are ear-validated;
  SUBSTITUTION has one ground-truth positive and an unvalidated screen;
  MISPRONUNCIATION has no screen and *cannot* have a text-only one; a mid-verse
  repeat has no instrument at all. ⛔ **Never call a set clean — only "clean on
  what can be detected".**
- ⛔⛔ **ASSUME A NEW SCREEN IS BROKEN UNTIL A CONTROL FIRES.** Nine instrument
  bugs in this family since 2026-09-03 — including two caused by the fix itself,
  so **run the control on your own change too**. Nearly all under-report —
  which is the direction that licenses calling a set clean, or sends an ear and
  a GPU at verses that can never pass. Build the control first.
- ⛔ **THE TEE'D LOG IS THE AUTHORITY — never a task's exit code and never a
  run piped through `tail`.** A repair run showed 2 failures on screen and 4 in
  its log; a launch ending `… > log 2>&1; echo "EXIT=$?"` reported *echo's*
  status over «107 STILL FAILING».
- ⚠ **A CHECK THAT CANNOT RUN IS NOT A CHECK THAT PASSED.** Confirm the
  DENOMINATOR is the whole corpus before believing any green result.
- ★ **REPAIR BY THE VERSE** — `tools/repair_verses.py --set <KEY> --queue …`.
  ⛔ `narrate.py --force` on a chapter is for the TRUNCATION class only.
  ⚠ Its summary counts CHAPTERS, and a chapter counted FAILED has still been
  rewritten — «failed» never means «untouched».
- ⛔⛔ **A GATE FLAG THE PRINTED TEXT EXPLAINS CAN NEVER PASS A REDRAW, AND A
  REDRAW CAN MAKE THE VERSE WORSE.** Check `qa_text_explained.py` before
  queueing draws. It is not only wasted GPU: when the gate cannot separate the
  draws it falls back to attempt 1, so **a correct take can be discarded in
  favour of a defective one.** ylt Genesis 13:14 lost a correct draw twice this
  way and shipped «westward and westward» for two days.
  ✅ FIXED 2026-09-07: `repair_verses.py` now KEEPS THE EXISTING TAKE on a
  genuine tie, records a `synth_sha` of the synthesis input so a real input
  change is still installed, and `--install-tied` takes a VERSE LIST.
  ▶ Audit the whole history for free: `tools/qa_discarded_draws.py --set <KEY>`.
  ⚠ A verse can be gate-flagged for a text-explained reason AND carry a real
  defect the gate cannot see — «text-explained» never means «that verse is fine».
- ⚠⚠ **NEVER DELETE `narration/<set>_qa_fail_originals/`** — it is the project's
  only copy of the validation ground truth, not merely an audio backup. The
  repair overwrites the live tree, so validators read the originals.
- ⚠ **BEFORE ANY RENDER: `render_preflight.py check --lang <set>`**; the hook
  refuses `narrate.py --lang …` without a stamp < 6 h old. Starting a GPU job
  stays the owner's call, per job.
- ⚠⚠ **KEEPALIVE-MANAGED JOBS CANNOT BE STOPPED BY KILLING THEM** — create
  `narration/logs/PAUSE_<job>` FIRST, then kill. Task Scheduler re-arms in
  seconds.
- ⚠ **ONE SCREEN'S OUTPUT FILE IS NOT THE REPAIR SCOPE** — merge every screen
  with `tools/qa_verse_queue.py`. A queue built from `<set>_rerender.txt` alone
  was 60 % of the real scope and looked complete.
- ⚠ **THE DETECTOR IS WHISPER, NOT KOKORO** (faster-whisper lives in
  `tools/.kokoro_venv` — venv name only). `qa_asr_sweep` is English-only in
  practice; use `qa_selfrepeat` for sv/wyc/cu.
- ⛔ **THE PRONUNCIATION LEXICON IS OWNER-GATED AND MOSTLY UNVALIDATED.**
  `prophesy -> prophesigh` is the ONLY row cleared to the real-verse standard.
  `Eelighsha` was wired in **over a stated objection** — good in one verse,
  ear-rejected in two; ⛔ do not re-litigate it and do not guess a fourth
  spelling. ✅ `Elijah` is pronounced CORRECTLY (checked) — never add it.
  ⛔ Do not start a lexicon re-render without him. **Derive scope:**
  `pronounce_lexicon.py --scope` — a `validated_by` stamp is NOT a standard.
- ⛔ **NO LONG RENDER PASSES ITS FIRST 50 CHAPTERS WITHOUT AN ASR SCREEN OF
  THOSE 50** (owner, 2026-09-02). ylt shipped a defect in ~15 % of chapters
  after 11 days; 90 minutes of CPU on day 1 would have caught it.

## ★★ TRANSCRIPTION (Þorláksbiblía / Karl XII) — INDEX

▶ **Full records: `docs/TRANSCRIPTION.md`, under
`── MOVED OUT OF CLAUDE.md, 2026-09-07 ──`.** Conventions live in
`research/THORLAKS_CONVENTIONS.md`, which `thorlaks_chunk_kit.py` pastes
verbatim into every kit — **so a rule put THERE reaches every future chunk.**

- ⛔⛔ **DO NOT USE HAIKU FOR THIS TRANSCRIPTION** — measured head-to-head
  2026-09-04: 70.9 % character similarity to Sonnet, 0 of 16 verses identical,
  10/17 proper nouns recovered, invented an abbreviation and **shifted verse
  boundaries**, then self-certified. Sonnet only, fan-out 2-3.
- ⛔⛔ **DECIDING ø FROM A PACKED SHEET IS DISPROVED IN BOTH DIRECTIONS** — it
  produced false negatives AND a false positive. ø is read on half-width crops
  at native 8.3x, or it is not read. ⚠ **A page with no crop-method data has NO
  ø measurement — not a low rate.**
- ⚠ **AN AGENT'S ø RATE IS NOT THE CONVENTION'S ø RATE** (19-31 %, per BOOK).
  The convention counts EVERY letter o (~121/page); an adjudicator examines
  only the positions it selects (~30 %). Always ask for the page's total
  o-count beside the number examined.
- ⛔⛔ **MATTHEW'S ø RETROFIT IS STRANDED AND UNPATCHABLE** — records addressed
  `p<page> line<NN> <L|R>` cannot be located in verse-indexed part files
  (34 sites, 7 locatable). ✅ The fix at source is in the conventions now: every
  site must carry its VERSE. ⚠ A PARTIAL patch is worse than none — it raises
  the per-file ø rate that is the campaign's only signal of a bad-resolution read.
- ⚠⚠ **A CONTIGUOUS VERSE RANGE IS NOT EVIDENCE OF COMPLETENESS** — compare
  against the expected count. A `###` page marker once ended a chapter and put
  **122 Matthew verses in an appendix** while the grid read as a short chunk;
  two verses were transcribed in full and unreachable under no chapter heading.
  ▶ **«Transcribed» is not «reachable».** Run BOTH `thorlaks_corpus_audit.py`
  and `thorlaks_part_check.py`; a defect shows only when they disagree.
- ⛔⛔ **CYRILLIC HOMOGLYPHS ARE INVISIBLE CORRUPTION** — transcribers emit
  `о д а е с т` inside Latin words. `thorlaks_part_check.py` detects them and
  REFUSES to repair. ▶ Substitution is by the letter's **PHONETIC** value
  (`р`=r never p, `с`=s never c) — a visual map turned `Vppriса` into a
  non-word. ⚠ β is NOT this defect (it is the `ꝑ` sort) — do not sweep it up.
- ⛔⛔ **BELOW THE CONVENTION'S ø BAND IS A QUESTION, NOT A VERDICT.** Mark derives at **13.2 %** over all 18 pages against a 19–31 % per-BOOK band — and that is NOT evidence of under-detection: p47 read 26.1 % on the same instrument, same session, that read 8.0 % on p46 one page away. The rate tracks VOCABULARY. ⚠ Never quote a per-PAGE rate against the band; the band is per-book, exactly as written.
- ⚠⚠ **A RECORD'S WORD NEED NOT MATCH THE TRANSCRIPTION'S SPELLING, AND THAT IS NOT A FAULT IN EITHER** — the adjudicator writes the page as it PRINTS. `thorlaks_o_patch.py` folds the print's nasal bars («mørgū»/«morgum») and the adjudicator's [bracketed] completions («søg[du]»), accepting only a token with exactly ONE letter-o. ⛔ It does NOT fold long-s read as `p` for `f`, and it does NOT move a ø across a verse boundary: **those are TEXT findings and a ø pass must not make silent text edits.**
- ⚠ **RUN `thorlaks_crop_widths.py` ON A KIT BEFORE READING A PAGE OF IT.**
  Truncated preps slice glyphs mid-stroke and every judgement on them is void.
  ⚠ It has a ~73 % false-positive rate and says SUSPECT, never TRUNCATED — an
  eye adjudicates. Cure is `prep_chunk.py --robust-block`, **per page**.
  ⚠ Fixing line crops does NOT fix the packed sheets; rebuild those too.
- ⚠ **A tall blank block merged into a line crop makes a full sheet look
  empty.** Measure ink PER LINE before calling a crop defective.
- ⛔ **A PRINTED COUNT THAT DISAGREES WITH THE KJV IS A FINDING, NOT AN ERROR
  TO CORRECT.** Printer's duplicates and unnumbered verses are RECORDED
  (pinned by position), never supplied from a parallel.

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
