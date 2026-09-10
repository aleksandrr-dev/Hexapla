# Hexapla — project context for Claude sessions

Offline parallel Bible app for Android. Kotlin + Jetpack Compose, single
module, no backend, no analytics. Owner: aleksandrr-dev (GitHub).
Mission: evangelism — maximize reach, keep everything free, nothing locked,
collect no data.

▶ **Auto-loaded into every session, so it holds only what is true now and
needed often.** Records live in the topic docs (table below); this file points
at them. Rewritten 2026-09-09 (389 → ~190 lines; redundant text deleted, owner's
call). Mechanical rules are now enforced by hooks (§ Guards) — do not re-derive
them and do not restate them here.

⚠ **Never pin a dated filename here as "the current one."** Handoffs and
campaign books are superseded within days. Point at the rule or command that
finds the current one.

## Build

- JAVA_HOME: `C:\Program Files\Android\Android Studio\jbr` (user env var set;
  not on PATH in older shells).
- AGP 9.3.0 / Gradle 9.4.1 / Kotlin 2.3.21 (built-in, no kotlin-android
  plugin) / Compose BOM 2024.10 / minSdk 26.
- `./gradlew bundlePlayRelease` (Play AAB) · `assembleRustoreRelease` (RuStore
  APK) · `assembleRustoreDebug` (~20 s, device testing; the owner's phone runs a
  rustore DEBUG build, a release APK will not install over it).
- Flavors (dimension "distribution"): `play` strips the ЮMoney donation path
  via R8; `rustore` shows it when Play Billing is absent; `foss` for F-Droid.
  ⚠ **The donation grep needs its positive control every release** — 0 on the
  Play artifact means nothing unless the same grep gives 1 on the RuStore one;
  0/0 = broken grep. It regressed silently for five releases (1.4.0–1.5.1).

      unzip -p <aab> "base/dex/classes*.dex" | grep -ac yoomoney   # must be 0
      unzip -p <apk> "classes*.dex"          | grep -ac yoomoney   # must be 1

- Signing: `keystore.properties` (gitignored) → keystore in the owner's
  Documents. Play App Signing; our key = upload key. Never commit keys.
- **versionCode 17 / 1.6.4 is on both stores (2026-08-16). Next free
  versionCode is 18.** A rebuilt version must refresh every copy, including the
  GitHub `releases/latest` asset (it once lagged the stores by 15 days).
- ⚠ `Locale.forLanguageTag("sv")`, never `Locale.of` (API 36 vs minSdk 26;
  compiles, crashes on every real device).
- adb: `$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe`; in Git Bash prefix
  device-path commands with `MSYS_NO_PATHCONV=1`.

## Where things are

| you need | read |
|---|---|
| what is happening right now | the ONE `SESSION_HANDOFF_*.md` in `C:\Projects\Hexapla-releases\`. Two = a bug; the later date is current, archive the other first |
| the Play production application | `PLAY_PRODUCTION_*.md` in `Hexapla-releases` |
| adding/researching a translation, licence gates, dead ends | `docs/TRANSLATIONS.md` |
| touching a Bible asset | `docs/ASSET_DEFECTS.md` |
| renders, GPU, keepalive, audio backends, every render/QA defect class | `docs/NARRATION.md` |
| Þorláksbiblía / Karl XII records, the Haiku test, the ø retrofit | `docs/TRANSCRIPTION.md`; conventions in `research/THORLAKS_CONVENTIONS.md` (pasted into every kit, so a rule put there reaches every chunk); folio↔index and «Cap. N» rules in `research/THORLAKS_CAMPAIGN.md` |
| what shipped when, why a behaviour changed | `docs/RELEASE_HISTORY.md` |
| why a UI/service/widget bug must not come back | `docs/ARCHITECTURE.md` |
| whether a question is already CLOSED | `docs/SETTLED.md` — closes questions, never a count to quote |
| store texts, screenshot order, upload procedure, landing-page to-do | `store-assets/STORE_LISTING.md` |
| the roadmap in full | `docs/ROADMAP.md`; plans: `WEB_APP_PLAN.md`, `IOS_PORT_PLAN.md` (repo root) |
| the KJV re-render in the owner's voice | `tools/KJV_VOICE_RUNBOOK.md` |
| transcribing a Karl XII strip | `research/KXII_AGENT_BRIEF.md` first |
| starting an Icelandic book | `python tools/thorlaks_chunk_kit.py --book <Name> --vol N --pages a-b` (0 tokens; refuses while a convention is OPEN) |
| why a render carried a tail defect | newest `RENDER_GATE_BRIEF_*.md` in `Hexapla-releases` |
| what is actually running | `/status` skill — live checks, not logs |
| many glyph adjudications at once | `tools/contact_sheet.py` — one composite, not N zooms |
| a book's ø rate | `tools/thorlaks_o_rate.py --book <B>` (self-controlling; a page whose control disagrees is a finding, do not tune the rule) |
| verifying a Karl XII chunk | `tools/kxii_diff.py` against kxii.se — witness only, never a correction source; transcribe first, diff after |
| where a word sits on a strip | `tools/kxii_locate.py` (0.28 s; never Tesseract inline over many strips) |

⚠ `research/`, `narration/`, `logs/`, `handoff-archive/`, `SESSION_HANDOFF_*`
and `PLAY_*` are **not in this repo** — they live in `C:\Projects\Hexapla-releases\`
(untracked on purpose). `tools/` is in the repo; run tools by absolute path
from the data directory.

## Current state — derive it, never read it here

- **Live campaign: Þorláksbiblía 1644 (Icelandic).** No book name is written
  here on purpose: `python tools/thorlaks_corpus_audit.py`, then
  `thorlaks_part_check.py --book <B>`, then the next chunk from the ONE handoff.
  Apocrypha is in scope (owner, 2026-09-08) but the audit's denominator is the
  protestant canon and prints that caveat; never report a bare «complete».
  v1's page geometry differs from v3 — prep calibration does not carry over.
- **Karl XII 1703 apocrypha: previous campaign, all but done.** Derive with
  `tools/karlxii_apoc_corpus_audit.py`, then the `Resume:` line at the top of
  `research/karlxii_<book>.md`. A page location is not a work queue.
- **Run the corpus audit before believing any completeness claim** — a chunk
  report once claimed 572 verses over two on disk, for three weeks.
- Session shape (measured 2026-09-09, global CLAUDE.md «Subagents» and «Turn
  economy»): image reads go to one Sonnet subagent per page; batch commands;
  refresh the handoff and restart at ~200k context.

## Guards — hooks in `~/.claude/hooks/` enforce these; each has a known-bad control

- **Bash:** `narrate.py --lang` without a preflight stamp < 6 h; chapter
  `--force` without `# chapter-force-ok`; wrong `align_words --set` key;
  redirect onto an existing log; relative `tools/` from the data dir; killing a
  campaign process or `git push` without `# owner-approved`; a commit carrying
  an attribution trailer; a second `upload_when_clear.py`.
- **Read:** the 25th image in one transcript (delegate the page; override file
  `_work/IMAGE_GUARD_OFF`).
- **Agent:** model haiku on a transcription task.
- **Write/Edit:** `research/_parts/*.md` and `research/thorlaks_*.md` get
  `thorlaks_part_check.py` run immediately; a second `SESSION_HANDOFF_*.md`;
  non-ASCII in a `.ps1`; CRLF in `.box`-class data files (auto-fixed).

## Store status

- **RuStore** live at the current versionCode. **Google Play** closed testing;
  production needs 12 testers × 14 continuous days — read the figure off the
  Play Console, never compute it.
- **Landing page** https://aleksandrr-dev.github.io/Hexapla/ (repo `index.html`;
  the in-app QR and the archive.org items point at it). Direct-APK button
  serves `releases/latest` = always the RuStore APK. Pending edits and the
  `gh release upload` exit-0 trap: `store-assets/STORE_LISTING.md`.
- ✅ **Derived, never hand-written:** `python tools/count_translations.py`
  (tagline, landing page, release notes must agree) and
  `python tools/check_release_notes.py` before any paste into the console.
- Privacy policy: https://aleksandrr-dev.github.io/Hexapla/PRIVACY.html

## Architecture landmines — full reasoning in `docs/ARCHITECTURE.md`

- `ReadingService`: foreground media service, three backends — TTS (never
  pre-queue a chapter), LibriVox (`assets/audio_index.json`), generated
  narration (`assets/audio_index_gen.json`). Index-driven: a new set needs no
  Kotlin. Verse/word following from per-verse `o` offsets and `.w.json` sidecars.
- `internetarchive.upload(metadata=…)` does nothing on an existing item.
- PendingIntent requestCodes stay distinct: 1 widget continue · 2 media
  notification · 3 daily reminder · 4 widget verse.
- Deep-link extras are consumed in `openFromIntent`, or Android replays them forever.
- An inner Scaffold under `AppScaffold` sets `contentWindowInsets = WindowInsets(0)`.
- Scroll-to-verse: ONE snapshotFlow collector; split halves race.
- Highlights need the optimistic `liveHighlights` mirror.
- Widget peek is deliberately invisible; ask before adding chrome.
- `BibleRepo.parseAsset` strips `{…:…}` notes (colon = note, drop; no colon =
  supplied words, keep).
- The 29 books without cover art are done being hunted (structural; audit in
  `research/bookart_gap_sources_2026-08-10.md`).

## Narration & render QA — full text in `docs/NARRATION.md`

- ylt has five defect classes and validated screens for two: a set is only
  ever «clean on what can be detected».
- A new screen is broken until a control fires — including your own fix. Nine
  instrument bugs since 2026-09-03, nearly all under-reporting.
- The tee'd log is the authority, never an exit code, never a run through `tail`.
- A check that cannot run did not pass; confirm the denominator is the whole corpus.
- Repair by the verse (`tools/repair_verses.py`); `narrate.py --force` on a
  chapter is for truncation only; its «failed» chapters were still rewritten.
- A gate flag the printed text explains cannot pass a redraw
  (`qa_text_explained.py` first); ties keep the existing take since 2026-09-07;
  audit history with `qa_discarded_draws.py`.
- Never delete `narration/<set>_qa_fail_originals/` — the only ground truth.
- Keepalive-managed jobs: create `narration/logs/PAUSE_<job>` first, then kill.
- Repair scope = every screen merged by `tools/qa_verse_queue.py`, never one file.
- The detector is Whisper (in `tools/.kokoro_venv`, name only); `qa_asr_sweep`
  is English-only, `qa_selfrepeat` for sv/wyc/cu.
- The pronunciation lexicon is owner-gated: `prophesigh` is the only validated
  row, `Eelighsha` is closed, `Elijah` is correct — never add it. Scope:
  `pronounce_lexicon.py --scope`.
- No long render passes 50 chapters without an ASR screen of those 50.
- KJV re-render: generated narration silently replaces LibriVox for 50 books —
  owner's explicit yes before rendering 1,371 chapters.

## Transcription (Þorláksbiblía / Karl XII) — full text in `docs/TRANSCRIPTION.md`

- Sonnet only; Haiku measured unusable (hook enforces). One subagent per page.
- ø is read on half-width crops at native 8.3x or not at all; a packed-sheet
  verdict is void in both directions; a page with no crop data has no ø rate.
- Every ø site carries its VERSE (Matthew's page-addressed retrofit is
  stranded); a partial patch is worse than none.
- The ø band (19–31 %) is per BOOK; a page below it is a question, not a
  verdict — the rate tracks vocabulary (Mark p46 8.0 %, p47 26.1 %).
- A record's spelling need not match the transcription's; `thorlaks_o_patch.py`
  folds nasal bars and bracketed tails, never long-s/`p` and never across a
  verse boundary — those are text findings.
- A contiguous verse range is not completeness; run both `thorlaks_corpus_audit.py`
  and `thorlaks_part_check.py` — a defect shows only when they disagree.
- Cyrillic homoglyphs are invisible corruption; substitute by phonetic value
  (`р`=r, `с`=s); β is the `ꝑ` sort, not this defect.
- `thorlaks_crop_widths.py` before reading a kit (says SUSPECT, ~73 % false
  positives; and it PASSES a crop whose edge is in the wrong place — Luke idx 54).
  Cure per page: `prep_chunk.py --robust-block` or `--full-width`; rebuild the
  sheets too.
- A printed count that disagrees with the KJV is a finding, never corrected.

## Data pipelines (`tools/`)

Python (`pillow`, `pymupdf`; ffmpeg via winget). Each script's docstring is
the reference. `count_translations.py` and `check_release_notes.py` are the
store-facing derivations; `build_bookart*.py` mappings are derived from the
sources' printed references — re-derive, never hand-edit.

## Roadmap — live items only, full text in `docs/ROADMAP.md`

IzzyOnDroid listing (low effort) · self-generated narration (see the KJV
re-render gate above) · **web app** (`WEB_APP_PLAN.md`, planned 2026-09-09, not
started) · iOS port (`IOS_PORT_PLAN.md`, gated on Play production + owner go).

## Owner preferences

- KJV/TR textual tradition only — no Critical Text translations, ever.
- Everything legally clean: public domain or CC with attribution.
  `sources_text` holds REQUIRED + PROMISED credits only (owner, 2026-07-16);
  do not add PD courtesy credits or extend it for new PD translations.
- Voice cloning of real people / characters: refused, stays refused.
- He tests on his phone and reports precisely — believe the repro over the code.
- Commits: no AI-attribution trailers. Commit or push only when asked.
