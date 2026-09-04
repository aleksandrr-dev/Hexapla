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
| starting an Icelandic (Þorláksbiblía) book | `python tools/thorlaks_chunk_kit.py --book <Name> --vol N --pages a-b` — builds prep + coverage + sheets + verse grid + report skeleton, 0 tokens; pastes `research/THORLAKS_CONVENTIONS.md` and REFUSES while a convention there is OPEN |
| why a render carried a tail defect, how repairs work now | the newest `RENDER_GATE_BRIEF_*.md` in `Hexapla-releases` (`ls -t … | head -1`) |
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

## ★★ RENDERS AND REPAIRS, SINCE 2026-09-03 — read this block before the one below it

The tail defect (a re-spoken or garbled verse end) hit ~13 % of chapters in
EVERY chatterbox set because the only in-flight guard was Chatterbox's own
token flag (tracked nothing audible, cost half the render) and every real
screen ran days later per chapter. Fixed structurally; the diagnosis and the
evidence are in the newest `RENDER_GATE_BRIEF_*.md` in `Hexapla-releases`
(`ls -t C:\Projects\Hexapla-releases\RENDER_GATE_BRIEF_*.md | head -1`).

- ✅ **`narrate.py` now GATES EVERY VERSE at render time** with the ear-validated
  screens (`tools/qa_gate.py`: ASR self-repeat, English APPEND) and re-draws a
  failing verse up to 3×. Validated 10/10 confirmed / 0/40 controls; Swedish
  control 5/6. It writes `<chapter>.qa.json`; `render_preflight.py report`
  reads them — that IS the "first 50 chapters" screen, at zero model cost.
- ⚠ **THE DETECTOR IS WHISPER, NOT KOKORO.** faster-whisper lives in
  `tools/.kokoro_venv` (venv name only). The self-repeat screen needs no
  reference text, so it works on 1703 Swedish; only APPEND needs readable
  English. Novel hallucinations in sv/wyc/cu have NO screen — never call
  those sets clean, only "clean on what can be detected".
- ✅ **REPAIR BY THE VERSE — `tools/repair_verses.py --set <KEY> --queue …`**
  (dry-run by default, `--apply` to write; backs originals up to
  `narration/<dir>_qa_fail_originals/`, gates the new take, splices, re-aligns).
  ~1 min/verse instead of ~9 min/chapter, and untouched verses stay untouched.
  ⛔ `narrate.py --force` on a chapter is for the truncation class ONLY
  (`zero_duration_verses` hits); the hook blocks it otherwise.
- ✅ **BEFORE ANY RENDER: `render_preflight.py check --lang <set>`** (gate
  stamp, ASR worker, GPU, VRAM, voice, alignment key, fresh log, disk). The
  hook refuses `narrate.py --lang …` without a stamp < 6 h old. `launch`
  prints the command; starting a GPU job stays the owner's call.
- ⚠ **KEEPALIVE-MANAGED JOBS CANNOT BE STOPPED BY KILLING THEM.** Task
  Scheduler re-arms them within seconds (`narration/logs/render_bootstrap.ps1`
  gates on counts). Create `narration/logs/PAUSE_<job>` FIRST, then kill.
  A cu uploader was killed and back under a new PID in under a minute.
- ▶ The seven mistakes that recurred across sessions are now a PreToolUse hook:
  `~/.claude/hooks/guard_hexapla_bash.py` (wrong `--set` key, chapter `--force`,
  unstamped launch, `tools/` from the data dir, kills without `# owner-approved`,
  redirect onto an existing log, second uploader). If it blocks you, it is
  right more often than you are — read its message.

## ★★ SUBSTITUTION IS A FOURTH DEFECT CLASS — added 2026-09-04

The render can SPEAK THE WRONG WORD. ylt Genesis 12:14 (`0/12 v14`) says
«westward» where Young's reads «and **eastward**, and westward» — owner
confirmed BY EAR. Neither existing screen is aimed at it: `qa_asr_sweep`'s
APPEND test never fired because nothing was appended, and `qa_selfrepeat`
caught it only BY LUCK, because the substituted word happened to duplicate its
neighbour.

- ✅ **`tools/qa_substitution.py`** reports only **NEIGHBOUR-COPY**: the heard
  word does not match the text here but EXACTLY matches a word elsewhere in the
  same verse. Printing every mid-verse `replace` is useless (~3/chapter on
  archaic English, ~0 true positives); this sub-class is the one with an
  argument behind it. `--validate` fires on the ground truth and stays silent
  on an identical transcript. End-to-end on the real Genesis 12 audio:
  1 NEIGHBOUR-COPY (the real one), 6 other mid-verse subs suppressed.
- ⚠⚠ **IT IS NOT VALIDATED FOR RECALL AND CANNOT BE.** Exactly ONE ground-truth
  positive exists in this project. `--validate` proves it FIRES; it says nothing
  about what it MISSES, and a screen with false negatives licenses discarding
  real defects. **A substitution into a word that duplicates nothing in its verse
  has no instrument at all.** Report ylt as "clean on what can be detected".

## ★★ MISPRONUNCIATION IS A FIFTH DEFECT CLASS — owner's ear, 2026-09-04

Confirmed on the ylt repair pilot (`0/8 v26`, Genesis 9:26). The owner listened
to the before/after and reported: the repeat is gone, **but the render says
«can-a-yin» where the name is «Canaan»** (/ˈkeɪnən/). The words are all correct;
the PHONETICS are wrong.

- ⚠ **It is PRE-EXISTING, not caused by the repair.** faster-whisper transcribes
  `Kanan` from BOTH the shipped take and the re-drawn one. It is already in the
  shipped audio.
- ⚠⚠ **IT IS NOT INVISIBLE — IT IS DELIBERATELY SUPPRESSED.** The ASR emits a
  different token, so the signal is right there in the diff. But every screen
  discards that class on purpose: mid-verse and end-substitution flags on
  archaic English ran ~3 per chapter with essentially no true positives
  (measured on ylt Genesis 1-34), so they are filtered as ASR noise. **The
  instrument sees it and we throw it away.**
- ⛔ **A screen for it faces the SAME wall as the substitution class:** it must
  separate «the ASR misheard the audio» from «the TTS mispronounced the word»,
  and **text evidence alone cannot do that — only an ear can** (owner's rule,
  established on 0/12 v14). Do not build one that dismisses hits on text.
- ▶ **SCOPE, derived not guessed: «Canaan» alone is in 156 ylt verses across 87
  chapters.** It will not be the only name. Candidate second instance, NOT yet
  ear-confirmed: «he saith» transcribes as «he's safe» in both takes.
- ⛔⛔ **THE CLASS SPLITS IN TWO, AND THEY NEED OPPOSITE TOOLS.**
  * **SYSTEMATIC** — always wrong: `Canaan`, `Levites`, `Abraham`, `Ephraim`,
    `Job` («Jahb»), `Hezekiah` («Hez-a-KEE-yah»), `calleth`/`falleth` (the a of
    apple, not the aw of call), `fleeth`/`seeth` (the «ee»+«eth» syllable
    collapses). A respelling fixes these — `tools/pronounce_lexicon.py`,
    16 entries, **1,485 verses / 493 chapters**, all still UNVALIDATED.
  * **SPORADIC** — `Jehovah`, wrong maybe 1 time in 7 across **6,626 verses**.
    A respelling is the WRONG tool: it would rewrite every one to fix a
    minority. ⛔ **The ASR cannot find the bad ones** (both ear-flagged verses
    transcribe as `jehovah`, same as ones the owner passed), and **acoustic
    clustering was built, validated against his 14 labels, and FAILED** —
    `qa_pronounce_cluster.py --validate` clustered by SURROUNDING PHRASE, not
    pronunciation. ▶ **Owner's decision 2026-09-04: leave it**, recorded as a
    measured limitation. Re-opening it means asking him.
- ⚠ **THE EAR SHRANK THIS THREE TIMES — never scope it from a spelling rule.**
  «-eth is broken» would have condemned 618 forms / 6,499 verses; the ear said
  only the double-e stems, 3 forms / 231 occurrences. «a+ll is broken» would
  have rewritten `all` (5,482 places); the ear said only `calleth`/`falleth`.
  A prefix rule on `canaan` would have missed `Canaanite` and hit nothing else.
- ⚠ **A LEXICON ENTRY IS A HYPOTHESIS ABOUT HOW THE MODEL READS LETTERS.**
  Every entry is marked unvalidated and the tool says so on every run. One test
  verse per entry must be rendered and HEARD before any of it ships — and only
  an ear can tell whether the respelling helped, for the same reason text cannot
  clear a self-repeat hit.
- ▶ The fix is a pronunciation lexicon applied to the SYNTHESIS INPUT ONLY (never
  to the displayed text), then a re-render of every affected verse. That is a far
  bigger job than the repeat/append queue, and the lexicon itself needs an ear to
  build. **Do not start it without the owner.**
- ✅ Repeat/append repairs are ORTHOGONAL to this and were explicitly approved to
  proceed anyway (owner, 2026-09-04): they do not make pronunciation worse.

⚠ **So ylt has FIVE known defect classes and screens for two.** Repeat
(`qa_selfrepeat`) and novel-append (`qa_asr_sweep`) are validated; substitution
has an unvalidated screen with one ground-truth positive; mispronunciation has
none; and a substitution into a word that duplicates nothing has no instrument
at all. **Never call the set clean — only "clean on what can be detected".**

## ⛔ DO NOT USE HAIKU FOR THE Þorláksbiblía TRANSCRIPTION — measured 2026-09-04

Controlled test at the owner's request: Haiku and Sonnet read the SAME two
sheets (`2timothy_v3` p199 sheets 1-2, 2 Tim 4:7-22) under the same brief.
Sonnet's output is the one the corpus already accepted (2 Timothy audits 83/83).

| | Sonnet | Haiku |
|---|---|---|
| character similarity to Sonnet | — | **70.9 % mean, 55 % worst** |
| verses identical | — | **0 of 16** |
| proper nouns of 2 Tim 4 recovered | **17/17** | **10/17** |

Haiku lost Crescens, Erastus, Linus, Marcum, Pudens, Titus and Tychicum;
invented an abbreviation «DXDSSE» for DROTTIN and then REPORTED it as faithfully
kept-as-printed; and **shifted verse boundaries** — its v14 opens with the tail
of v13, so text is filed under the wrong verse numbers. It also self-certified
(«current reading stable at native magnification», «no inferences from modern
text»), none of which held. ▶ Confident, wrong, and unverifiable without a
reference — the exact failure the kit manifest warns about: *the failure this
guards against is not misreading, it is supplying the letter the WORD wants.*
Evidence kept at `research/_haiku_test/`.


## ⚠⚠ ONE SCREEN'S OUTPUT FILE IS NOT THE REPAIR SCOPE

`_work/<set>_rerender.txt` holds only the APPEND sweep. The self-repeat screen's
hits sat in 66 per-book logs that nothing had ever merged. Measured for ylt on
2026-09-04: APPEND 169 verses, self-repeat 214, **UNION 280 across 233
chapters** — so a queue built from the one file was **60 % of the real scope and
looked complete**.

- ✅ **`tools/qa_verse_queue.py`** merges every screen into a plain
  `book chapter verses` queue for `repair_verses.py`. It emits data, not
  commands, because `<set>_rerender.txt` LOOKS like a runnable script and
  running it is chapter `--force` — forbidden for this defect class.
- ⛔ It **exits non-zero when a named source is read and yields nothing**, with
  a different message for "no file matched". Both were needed: the first build
  used `re.match` where the pattern needed `search` (the rerender lines start
  with the interpreter path), contributed **+0 verses**, and printed a
  believable 214-verse total.
- ⛔ It also **refuses to build from a self-repeat log with no completion line.**
  The Task Scheduler keepalive can start a SECOND `qa_cpu_chain` instance, which
  goes back to the ylt job whenever sentinels are missing and RE-RUNS complete
  books, truncating each log to in-progress. A rebuild in that window silently
  drops the in-flight book's hits and totals up fine.
- ⚠ **Text evidence cannot clear a hit** — it cannot tell "the ASR misheard A as
  B" from "the TTS SPOKE B where the text has A". Established by ear on
  0/12 v14. Queue every hit; only an ear removes one (`--exclude`).

⚠ The handoff instruction to "backfill sentinels because the running chain is
OLD code" is **obsolete**: `qa_cpu_chain.ps1` was fixed 2026-09-03 08:52, three
hours after that instance started, and its pattern already handles both
`^[0-9]+ verses scored,` and `^\[book .* done\]`. Any instance started since
sentinels correctly. Backfill only what an anchored grep proves finished.


## ⛔⛔ THE RENDER GATE — SCREEN THE FIRST 50 CHAPTERS BEFORE RENDERING 1,189

**No render longer than ~100 chapters continues past its first 50 without an
ASR screen of those 50.** Owner's instruction, 2026-09-02.

    tools\.kokoro_venv\Scripts\python.exe tools\qa_asr_sweep.py --lang <set> --every 8
    python tools\qa_asr_triage.py _work\qa_asr_<set>.log      # APPEND -> NOVEL/REPEAT/NOISE
    tools\.chatterbox_venv\Scripts\python.exe tools\qa_asr_clips.py \
        _work\qa_asr_<set>.log --lang <set> --out _work\<set>_earcheck.ogg   # then LISTEN

▶ **WHY.** ylt rendered for ~11 days and shipped a repetition defect in roughly
**15 % of chapters** — Chatterbox re-saying the tail of a verse
(«putteth washing putteth washing»). The tool that finds it existed since the
2026-08-21 pilot and had never been run across a whole set, because it took
`--book`, rebuilt its model per call, and cost ~36 h. It was found on day 12.
**90 minutes of CPU on the first 50 chapters would have caught it on day 1.**

⚠ **THE COUNT IS NOT A CHECK.** ylt passed 1189/1189 while 1 Samuel 28 held
141.8 s of audio for 25 verses — twelve verses silent. Size and count heuristics
both waved it through; `zero_duration_verses.py` caught it in one run.

⚠⚠ **A CHECK THAT CANNOT RUN IS NOT A CHECK THAT PASSED.** Three separate tools
returned "no information" while printing clean-looking output on 2026-09-02:
`offset_drift` reported `0 chapters checked` on the whole set (it counted a
silence run ending at EOF as a boundary — now fixed), and `tail_hallucinations`
reported `0 verses judged` because ylt has no `.w.json`. **Confirm the
denominator is the whole corpus before believing any green result.**

⚠ **VALIDATE A SCREEN AGAINST GROUND TRUTH BEFORE TRUSTING IT, AND BEFORE
WRITING IT INTO A HANDOFF.** Two heuristics built for this defect failed:
a duration cross-check (a doubled tail does NOT reliably lengthen a verse —
disproved by ear on 4/4 controls) and an audio self-similarity detector
(confirmed 1.000 vs random 0.999, no separation). `qa_asr_sweep`'s APPEND flag
is the one that works, and only because the owner confirmed it 10/10 by ear.
**A screen that produces false NEGATIVES is worse than no screen** — it licenses
discarding real defects.

⚠ **`qa_asr_sweep` IS ENGLISH-ONLY IN PRACTICE** — it now refuses an `.en`
model on a non-English set, but whisper cannot read Karl XII's 1703 Swedish
either (measured: 97.5 % of verses flagged, i.e. useless).

✅ **USE `qa_selfrepeat.py` FOR NON-ENGLISH SETS.** It finds a re-spoken tail
from ASR **self-repetition** and needs NO reference text, so the ASR does not
have to read the language — it only has to emit the same tokens twice when the
audio says them twice. Validated against the ten ear-confirmed ylt verses:
**9/10 caught, 0/40 false positives.**

    tools\.kokoro_venv\Scripts\python.exe tools\qa_selfrepeat.py --validate
    tools\.kokoro_venv\Scripts\python.exe tools\qa_selfrepeat.py --lang sv --every 10

⚠ It finds REPEATS only, never a novel hallucination («saying suik») — use
`qa_asr_sweep` for those where the reference text is readable. ru/cu are
cosyvoice3 and have never shown this defect class.

▶ Deterministic checks are cheap and cover every set at once — run them after
any render, and they need no GPU, model or ear:

    tools\.chatterbox_venv\Scripts\python.exe tools\qa_all_sets.py

  It reports missing audio and sidecar drift for all nine sets in ~20 minutes.
  ⚠ It is BLIND to repeated/hallucinated audio; a clean report means "nothing
  missing or misplaced", never "good".

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
