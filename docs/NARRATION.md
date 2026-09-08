# Narration — render queue, engines, and the machinery around them

Split out of CLAUDE.md 2026-08-09. The render queue, GPU/CPU contention rules, the 75-minute recycle, and the keepalive task.

### ★ RENDER QUEUE (owner, 2026-08-04)

**ru re-render → then Geneva and Church Slavonic (`csl`) SIDE BY SIDE.**

⚠ **THE LIMIT IS ONE *GPU* RENDER, NOT ONE RENDER.** What matters is whether
the engine holds its model IN-PROCESS:

| set | engine | model | contends for GPU? |
|---|---|---|---|
| ru, **cu** | cosyvoice3 | in-process | **YES** |
| sv, tyn | chatterbox | in-process | **YES** |
| **gnv**, wyc, wbt | kokoro | fresh subprocess PER VERSE | **no — CPU** |

Two GPU renders do not merely run slowly, they **OOM on model load**: one
RTX 3080 Laptop, 8 GiB, and a live CosyVoice3 render holds ~5.4 GB leaving
~2.7 GB (chatterbox ~4 GB collides the same way). But a kokoro set is CPU-only
and narrate.py says outright that mixing it with the in-process engines is
fine — so **Geneva (kokoro) can run alongside Slavonic (cosyvoice3)**.
⚠ They still share CPU, and a laptop chassis: watch GPU temp for the first
hour, because the thermal watchdog kills at 90 °C sustained / 94 instant and
a CPU-heavy kokoro job raises chassis temp under the GPU one.

⚠ **THE 75-MIN RECYCLE IS NOT THERMAL** (owner corrected this 2026-08-04;
`render_supervisor.ps1` documents it). Throughput decays with **PROCESS AGE**:
measured 2026-07-28, fresh 151-183 KB/min · +45min ~103 · +4h ~63 · +12h ~35.
Restarting only the process — machine still running, chassis still hot at
79-81 °C with SwThermalSlowdown flagged — took a chapter from **27 -> 137
KB/min**. So recycling applies ONLY to the in-process engines. Kokoro sets get
`-IntervalMin 0` (revive-only); recycling them would pay model-load cost for
nothing.

⚠ **The 10-minute `HexaplaRenderKeepalive` scheduled task** runs
`render_keepalive_hidden.vbs` -> `render_bootstrap.ps1`, an idempotent "start
whatever is missing" check. It lives in Task Scheduler because anything
launched from the Claude Code shell is a child of the app's process tree — on
2026-07-29 both supervisors, both renders and the watchdog vanished together
and cost ~8h of GPU. It starts SUPERVISORS ONLY, never renders, to avoid a
double-launch race. Each language is guarded by a chapter-count test, so
adding a set means adding its `Ensure` block there.

1. **ru re-render** — 36 chapters (`scratchpad/ru_rerender_queue.py`): Job 2+9,
   24 psalms predating the restored titles, 1 Cor 4 + 8 duration-flagged
   candidates. Hours, not days.
2. **Geneva re-render** — all 1,189 chapters, CPU/kokoro. The shipped set is
   defective ("God created the HORN"); the fix is verified live in the render
   path — `archaic_english.normalize(..., "geneva")` turns heauen→heaven,
   moued→moved, prouince→province, euening→evening, Iesus→Jesus. Does NOT
   block a release: that audio streams from archive.org and is not bundled in
   the APK. ⚠ START IT BY QUARANTINING `narration/gnv` (oggs AND sidecars) to
   `gnv_quarantine_<reason>`, NOT by adding `--force`. The bootstrap's
   `ChapterCount 'gnv' -lt 1189` guard then starts the revive-only supervisor
   on its next 10-minute poll, and skip-existing keeps the job resumable —
   with `--force` every revive would restart from Genesis and it would never
   finish. Same pattern as `ru_quarantine_instruction_leak`.
3. **Church Slavonic (`csl`)** — 1,192 canon chapters, same size as ru.
   Already fully configured in `narrate.py`, and the judgment call is
   already made: the owner approved the Пс 22 ear test 2026-07-16 (CosyVoice
   reads civil-script Slavonic like a modern Russian reader — akanye,
   guessed archaic stress — accepted). Before it can SHIP it needs (a) the
   app id **`csl`**, NOT the `cu` narration-folder name, in the
   `build_audio_index_gen.py` SETS entry — a wrong tid yields an index the
   app silently never looks up; (b) an archive.org identifier in
   `upload_narration.py`, which has none; (c) the `cloned` disclosure flag,
   because cu uses the owner's own voice.

**WYCLIFFE WAS CONSIDERED AND DEFERRED** (2026-08-04). It has **0 chapters
rendered** — a full 1,189-chapter run, not a bolt-on — and it would be the
FOURTH English set (KJV, Webster, Geneva), where Slavonic is the only shipped
translation with a distinct audience and no narration at all. It also is not
render-ready: **4,960 verses (13.7%) carry a stray backtick** that survives
normalization (`` `thre and twentithe salm ``, an editorial supplied-word
marker that `audit_asset_markup.py` cannot see because a backtick is not a
tag), and **177 verses still say "salm"** where the normalizer should give
"psalm" — the same mispronunciation class as the Geneva defect. Fix both
BEFORE any render, not by ASR afterwards.

⚠ **GLEN OT CAMPAIGN — resume Thursday 2026-08-06, 16:00** (owner,
2026-08-04), when the usage limit restarts. It is a transcription campaign,
not a GPU job, so it does NOT contend with the render queue above.

★ **ARMENIAN ZOHRAB OT (`zoh`) IS COMPLETE IN TREE** — asset, versemap,
rubrics, registration and the required TITUS credit all landed 2026-08-04.
★ **The owner's device pass is DONE (2026-08-04)** and every finding is fixed:
stichometry colophons stripped, empty-verse rendering, findable picker
sections, shortened book names. `zoh` is gated ONLY on the native-speaker
reply now. See SESSION_HANDOFF_2026-08-04.md §3 and §3a.
⚠ Two things there are NOT bugs and must not be "fixed": the «։» ending
Armenian verses is U+0589 ARMENIAN FULL STOP (22,896 verses), and Daniel 3
showing 30 verses in split view is the primary-drives-the-grid behaviour the
owner already ratified for the Vulgate.

★ **Georgian Bakar is started, foundation only** — `tools/build_bakar.py`
maps and cleans, and prints its own curation list. Its asset is deliberately
untracked. Larger than Zohrab; wants its own session (§5).

★ **GENEVA'S SHIPPED NARRATION IS DEFECTIVE** — ASR-proven: Genesis 1:1 says
"God created the HORN and the earth" ("heauen"), plus "MOO-YUED" for moued and
"PROANCE" for prouince. The fix is in the pipeline; a re-render of all 1,189
chapters is pending an owner decision on timing. Do not ship new English
narration without re-reading that section of the handoff.

★ **THE APP NOW NORMALIZES SPELLING FOR TTS** (Pronounce.kt + pron_*.json).
Before 2026-08-03 it did not, so the device voice read archaic spelling
literally while rendered audio was correct. Regenerate the assets whenever
tools/archaic_english.py or the generated maps change, or the two voices drift.

★ **MUSIC BY MOOD SHIPPED in 1.6.3 (2026-08-05)** — mood_map.json (1,189
chapters), 79-track archive.org pack, MusicRepo + crossfade, all 10 strings in
all 26 locales (landed in the release commit c0588ef). The old 'built but not
shipped / 24 locales missing' note survived here for a month after being
falsified — verified against the res/ tree 2026-08-09.


---

## ⚠ ARCHIVE.ORG UPLOAD — the two things that cost days

**`queue_derive=False` does NOT prevent derives.** `upload_narration.py` sets
it, and archive.org derived anyway on the Russian item: **1,192 VBR MP3s and
1,056 waveform PNGs**, one pair per chapter. archive.org processes an item's
tasks SERIALLY, so a derive blocks every queued upload behind it, and while
the queue is deep the bucket ration refuses new uploads outright. The Russian
set spent days in exactly this state — measured 2026-08-09: a derive running
15+ hours with 1,000 archive.php tasks stacked behind it.
▶ **Publish a set COMPLETE in one pass.** A set uploaded in stages pays the
derive more than once. Karl XII was published partial at ~940 chapters and
Russian went up in stages; Geneva, published in one shot to a brand-new item,
had none of this trouble.
▶ Diagnose with `internetarchive`: `get_tasks(identifier=...)` and check
`task_dict['status']`. A derive that is genuinely working shows new derivative
files appearing on the item every 25-30 s — check `mtime` on the newest files
rather than guessing whether it is stuck.

**Metadata does not reach an EXISTING item.** `upload(metadata=…)` applies only
when it CREATES the item; on a pre-existing one archive.org ignores the
headers. Karl XII therefore finished complete but stayed publicly titled
"(pågår / in progress)" — invisible behind a clean `0 failed`. Fixed:
`upload_narration.py` now calls `modify_metadata()` explicitly and re-reads the
live title to verify.

**The ration message has (at least) two wordings.** The watcher matched only
the access-key form ("exceeds rationed amount") and died on the bucket form
("bucket_tasks_queued exceeds bucket_limit"), stopping a whole upload hours
after the queue had drained. `upload_when_clear.py` now matches both plus the
shared "Please reduce your request rate" prefix.

**A LONG-RUNNING DERIVE ON THE ITEM IS NOT WHAT BLOCKS AN UPLOAD — THE ACCOUNT
TASK RATION IS.** Proved by probe 2026-09-07: a 116-hour `derive.php` on the
ylt item (task 5601127710, `wait_admin=1`) was in flight and a single-file
upload to that same item SUCCEEDED. The refusal
(`bucket_tasks_queued exceeds rationed amount`) is account-wide: it counts
every task under the account catalog against a ration of 150, so an unrelated
set's backlog stalls this one. ⛔ Do not mail archive.org about a stuck derive
on this evidence, and do not re-probe — the question is settled.
▶ **The consequence for practice:** retrying an upload while the ration is
exceeded collects more refusals and lengthens the very queue being waited on.

**⛔ DO NOT BABYSIT A RATIONED UPLOAD BY HAND — `tools/ia_upload_watch.py`.**
It polls the account catalog every 10 min, resumes the set's upload only once
the catalog drops below 100, and decides completion by RE-READING THE LIVE
ITEM, never by a child process's exit code. Its `account_tasks()` returns
**-1** on a failed read, never 0, because a 0 would read as «queue empty, go»
and hammer archive.org exactly when it is least reachable.
- check state without acting: `ia_upload_watch.py --set <KEY> --check-only`
- stop it without a kill: `touch narration/logs/PAUSE_ia_upload_watch`
- ⚠ It is bounded at 288 cycles (48 h). Exiting on the bound is the WATCHER's
  limit, not an upload failure — re-run it.

---

## ★ ENGLISH PRONUNCIATION POLICY (owner, 2026-08-16)

**The audio should match the text on the screen.** Where the app ships archaic
spelling, the voice reads it as it was said in that period; where the asset is
already modern, it is read normally. The owner's framing: *"If people want to
hear modern English, they will listen to the closer KJV."*

⚠ THE FACT THAT SETTLES THE APPARENT INCONSISTENCY: **we already modernized
KJV — in the TEXT, not the audio.** `en_kjv.json` reads "God created the heaven
and the earth"; the 1611 original prints "Heauen". Webster 1833 is modern
natively (that was Webster's project). So nothing was modernized in KJV's
*audio* because nothing was left to modernize. The archaic-spelling assets are
Geneva, Tyndale and Wycliffe, and only those raise the question.

| asset | text | audio should be | engine | voice |
|---|---|---|---|---|
| KJV 1611 | already modern | read normally | kokoro | am_adam |
| Webster 1833 | modern natively | read normally | kokoro | am_adam |
| Tyndale 1525 | archaic, CLOSE | Early Modern, light respelling | chatterbox | **owner** |
| Geneva 1599 | archaic, CLOSE | Early Modern, light respelling | chatterbox | **owner** |
| Wycliffe 1395 | Middle English | full period reconstruction | **kokoro + IPA** | am_adam |

▶ **The split is by how drastic the distance is**, which is also what decides
whether the owner's voice is usable at all:

⚠⚠ **CHATTERBOX CANNOT TAKE PHONEMES — VERIFIED 2026-08-16.**
    `chatterbox.generate(text, language_id, ...)`  <- text only
    `kokoro  KPipeline.infer(model, ps, pack, s)`  <- IPA string
  So the owner's cloned voice and phoneme-exact pronunciation are MUTUALLY
  EXCLUSIVE with today's engines. Middle English needs phonemes (/x/, /ç/, the
  pre-GVS long vowels, geminates) and therefore cannot use his voice. Early
  Modern English is close enough that SPELLING alone carries it, so Tyndale and
  Geneva can.

### The tooling
· `tools/me_phonemes.py` — Wycliffite Middle English -> IPA, for kokoro's
  phoneme path. Pre-Great-Vowel-Shift long vowels, <gh> allophony (/ç/ after
  front vowels, /x/ after back), true geminates, the u/v swap, and a curated
  exception table for words spelling cannot predict.
  ⚠ Kokoro's 114-symbol vocab was CHECKED, not assumed: x ç ː ə ɪ ɛː ɔː r ɹ ɾ
  are all present; ʍ is not.
· `tools/middle_english.py` — the earlier respelling approach, kept because it
  is the right shape for an ENGLISH-SPELLING engine (chatterbox). Extend THIS
  one for Early Modern English (Geneva/Tyndale), not the IPA one.

### ⚠ CONSEQUENCE FOR THE SHIPPED GENEVA NARRATION
Geneva currently DISPLAYS «heauen» and SAYS "heaven" — `archaic_english`
modernizes it for TTS. Under this policy that is the wrong side of the line, so
the shipped Geneva audio (1,189 chapters) would need a re-render in Early
Modern pronunciation to comply. **Owner is aware; not yet scheduled.** Do not
start it without an explicit go — Geneva has already been re-rendered once, for
the "God created the HORN" defect.


## ★★ PRONUNCIATION: USE VOICE CONVERSION, NOT RESPELLING (2026-08-23)

⚠⚠ **DO NOT START A NEW SET'S ANNOUNCEMENTS WITH A RESPELLING TABLE.** That is
what `_SPOKEN_VARIANTS_EN` in `build_announcements.py` is, and on ylt it cost
six review rounds and ~90 draws on ONE book name before the right tool was
tried. The owner's words: "if that worked we should have done that from the
beginning, if we have a full render of right pronunciations."

**Why respelling hits a wall.** Chatterbox `generate()` takes **TEXT ONLY** —
it has no phoneme argument (verified; it is why Wycliffe had to move to Kokoro
to get Middle English IPA, see the `wyc` note in `narrate.py`). So the only
lever is graphemes, and graphemes cannot reach a stress pattern the model will
not produce. Measured on Obadiah: chatterbox says **Messiah** and **Josiah**
correctly, but the diagnostic **`Obasiah`** — the same 4-syllable frame with
only d->s — ALSO fails. The model will not stress syllable 3 of a 4-syllable
word, so `-iah` always reduces to `-ee-ah`. No spelling fixes that.
⚠ And the ASR gate cannot referee pronunciation at all (whisper writes "Jobe"
and "job" identically), so it silently rejects the respelling that would FIX
the sound and falls back to the one already rejected by ear.

**The fix — pronunciation from one render, timbre from another.**

```python
from chatterbox.vc import ChatterboxVC          # ships with the package
m = ChatterboxVC.from_pretrained("cuda")
out = m.generate(source_wav, target_voice_path=REF)   # REF = the set's voice
```

Worked example (Obadiah, owner-approved on first listen):
1. Pick a donor render that says the word correctly. **Webster (`wbt`) is
   kokoro `am_adam` and handles English proper names well.**
2. Cut the word out of the donor. The announcement sits at the HEAD of the
   chapter file and the **offsets sidecar gives the exact boundary** — verse 1
   of `wbt/30/0.ogg` starts at 1975 ms, so the name is before that. Costs no
   model tokens and no guessing.
3. `ChatterboxVC.generate(cut, target_voice_path=_en_ref_ylt.wav)`.
4. Trim to the first voiced run, fade, and run the normal gates
   (`tail_energy`, `looks_doubled`, duration).

⚠ **A single-chapter book is the easy case** — its announcement is the bare
name. For a multi-chapter book the donor says "Genesis, Chapter one" as ONE
utterance, and the library needs the name and the numeral as SEPARATE
components, so it must be split at the comma pause — which is not guaranteed to
exceed the 250 ms `voiced_runs` needs. Budget for that before promising a
wholesale harvest.

⚠ **This only works where a correct-pronunciation donor EXISTS.** Webster covers
English. For `ru`, `cu` and `sv` there is no donor render, so the respelling
table still earns its keep there.


---

# ── MOVED OUT OF CLAUDE.md, 2026-08-25 (context budget) ──

The `ReadingService` audio-backend record, verbatim from the project
`CLAUDE.md`. It is a COMPLETED RECORD of how the generated-narration path was
built and of the two sets that shipped on it. CLAUDE.md keeps only the
behaviour a session must know plus a pointer here.
⚠ The `internetarchive.upload(metadata=…)` landmine below is STILL LIVE and is
also carried in the current SESSION_HANDOFF.

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

# ── MOVED OUT OF CLAUDE.md, 2026-09-07 (context budget) ──

Render/repair QA: the defect classes, the screens, and every instrument
bug found in them. CLAUDE.md keeps a short index pointing here.

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

The render can SPEAK THE WRONG WORD. ylt Genesis 13:14 (`0/12 v14` — the chapter index is ZERO-BASED; this was
mislabelled «Genesis 12:14» here until 2026-09-07) says
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
    collapses). A respelling fixes these — `tools/pronounce_lexicon.py`.
    ✅ **DERIVE the entry count and scope: `pronounce_lexicon.py --scope`.**
    Never quote a figure here; the table changes every time an ear rules on it.
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
  A row is unvalidated until an ear clears it IN A REAL VERSE.
  ⛔⛔ **THIS FILE CLAIMED «the tool says which is which on every run». IT DID
  NOT** — measured 2026-09-07. `validated_by` is ONE free-text stamp, so
  `pronounce_lexicon.py` knew only stamped/unstamped and printed «(all
  ear-confirmed)» over 13 rows, flattening the very distinction this block turns
  on: `prophesy` was cleared in a real verse, `Aybraham` passed a SHORT CARRIER
  and then FAILED one. ▶ Fixed to report «13 carry a validated_by stamp» plus an
  explicit «A STAMP IS NOT A STANDARD» warning; **only the per-row comments in
  that file record which clearance a row actually got.** No per-row
  classification was invented, because there is no evidence for one.
  Only an ear can tell whether the respelling
  helped, for the same reason text cannot clear a self-repeat hit.
  ⚠ **A respelling can also do NOTHING** — `Elysha` and `Hezakyah` both came back
  indistinguishable from the original. «No change» is a third outcome alongside
  «better» and «worse», and it means letters are not the lever for that word.
- ▶ The fix is a pronunciation lexicon applied to the SYNTHESIS INPUT ONLY (never
  to the displayed text), then a re-render of every affected verse. That is a far
  bigger job than the repeat/append queue, and the lexicon itself needs an ear to
  build. **Do not start it without the owner.** ▶ It IS underway with him:
  `prophesy` cleared and wired in 2026-09-06, `Elysha` rejected the same evening.
- ✅ Repeat/append repairs are ORTHOGONAL to this and were explicitly approved to
  proceed anyway (owner, 2026-09-04): they do not make pronunciation worse.

### ✅ THE FIRST ROW EVER CLEARED IN A REAL VERSE — `prophesy`, 2026-09-06

`prophesy` -> `prophesigh`. The voice read the VERB as its own NOUN («prophes-EE»;
`prophesy` is /ˈprɒfɪsaɪ/, `prophecy` is /-si/). Owner confirmed it correct in the
test verse **and** in I Corinthians 14:31 and Amos 3:8, two chapters he had not
previously heard, then said «wire it in». Wired in: 43 chapters / 94 verses.
- ▶ **THIS IS THE STANDARD FOR CLEARING A ROW**: the whole printed verse, plus a
  spot-check in a chapter the ear has not already been primed on. ⛔ A short
  carrier is NOT sufficient — that is how `Aybraham` passed and then failed.
- ⛔ **AND NOTHING ELSE IN THE FAMILY.** `prophesying` (43 verses), `prophesied`
  (19), `prophesieth` (6) share the spelling and were NOT heard; `prophecy` the
  noun (24) is CORRECTLY said and must never enter the table.

### ⚠⚠ `Elisha` — `Eelighsha` WIRED IN 2026-09-07 OVER A STATED OBJECTION

Ear-confirmed 2026-09-06 (II Kings 5:25): «el-EE-sha», want «ee-LYE-sha».
**Scope, derived: 55 verses / 13 chapters.** `Elysha` was tested and heard
UNCHANGED (the `Hezakyah` pattern) and is REJECTED.

On 2026-09-07 three candidates were rendered on II Kings 5:9 and the owner chose
**`Eelighsha`** («5 is good»). `Elighsha` was also good but arrived after a
slight pause; `Eelysha` was NOT named good — **which is what identifies the `y`,
not the first vowel, as why `Elysha` failed.**

⛔⛔ **BUT IT THEN FAILED THE SPOT-CHECK IN TWO VERSES OF THREE:**

| verse | verdict |
|---|---|
| II Kings 5:9 | ✅ good |
| II Kings 2:1 | ❌ wrong — and the **as-printed** take was the good one |
| Luke 4:27 | ❌ «Eel eesha» |

One spelling, three verses, three outcomes = the **`Jehovah` signature,
SPORADIC**, for which this file's own rule says a respelling is the WRONG tool.
▶ **The owner was told exactly that and directed the wire-in anyway** (asked
twice; his first answer was ambiguous). His call, recorded — do not re-litigate.
⚠ **So this row is NOT «ear-validated» in the `prophesy` sense.** It is
ear-preferred in one verse and ear-rejected in two. A later session that sees it
in the table and assumes the `prophesy` standard will be wrong.
▶ Evidence: `research/_evidence/elisha_elijah_naaman_ear_2026-09-07.md`.

- ✅✅ **`Elijah` IS PRONOUNCED CORRECTLY** — owner, 2026-09-07, on II Kings 2:1,
  the one verse carrying both names. **Scope, derived: 93 verses / 26 chapters —
  LARGER than Elisha's.** It was CHECKED, not assumed, and it must NEVER enter
  the lexicon. ⚠ The old line «`Elijah` is not a safe model» was only ever about
  inferring Elisha's SPELLING from it; it said nothing about how Elijah is
  spoken, and nobody had checked until now.
- ⚠ **NEW, UNSCOPED: `Naaman`** — «Na min» right, «Nah min» wrong, varying
  between draws of an IDENTICAL input (owner, 2026-09-07, Luke 4:27). Sporadic
  class. ⚠ It came out right in the `Eelighsha` take in BOTH of two independent
  renders (2/2) though its own spelling never changed — an observation with n=2,
  not a technique.
- ⚠ **One of the 55 is a DIFFERENT PERSON**: I Chronicles 1:7 «sons of Javan:
  Elisha» is normally *Elishah*. YLT drops the final h so the whole-word row
  sweeps him in. Probably harmless; `synthesis_overrides.py` is the per-verse
  table if it ever needs excluding.
- ⛔ **DO NOT GUESS A FOURTH SPELLING.** Guessing produced three dead rows;
  `Elysha` and (on the evidence above) `Eelighsha` make five.
- ⛔ `Elishah`, `Elishama`, `Elishaphat`, `Elisheba` are DIFFERENT NAMES — the
  `canaan`/`Canaanite` trap, one careless prefix rule away.

### ⛔⛔ THE UNION-QUEUE RULE AND THE GATE LOOP NOW CONTRADICT EACH OTHER

**UNRESOLVED as of 2026-09-06. It costs GPU on every repair run.**
1. A queue line MUST name every verse in that chapter carrying a repair record or
   a lexicon change — `repair_verses.py` rebuilds from `<set>_qa_fail_originals/`
   and splices in ONLY the named verses, so an omitted verse **REVERTS**.
   (18 of one run's 43 chapters carried prior repairs.)
2. But a TEXT-EXPLAINED verse sitting in that queue is redrawn **3× and always
   fails** — the gate is firing on scripture, so no draw can ever pass.

Measured: Revelation 11:15 («to the ages of the ages») and Exodus 3:15
(«to generation—generation») each burned 3 futile draws on 2026-09-06.
▶ **The fix is for `repair_verses.py` to splice a text-explained verse WITHOUT
redrawing it** (keep its take, skip the gate loop). Not made — do not make it
mid-campaign without the owner.

### ⚠ `repair_verses.py`'s SUMMARY COUNTS CHAPTERS, AND A "FAILED" CHAPTER STILL WRITES

«repaired 38, failed 4, already done 1» = 43 **chapters**, not verses. ⚠ A chapter
counted as FAILED has still been rewritten — its other verses are spliced and the
live `.ogg` mtime changes; only the named verse is left still-failing.
**Never read "failed" as "untouched"**, and never as "nothing shipped".
✅ Backups are safe: it copies to `_qa_fail_originals/` **once** and never
overwrites, and always reads its source from there (verified 2026-09-06).

⚠ **So ylt has FIVE known defect classes and screens for two.** Repeat
(`qa_selfrepeat`) and novel-append (`qa_asr_sweep`) are validated; substitution
has an unvalidated screen with one ground-truth positive; mispronunciation has
none; and a substitution into a word that duplicates nothing has no instrument
at all. **Never call the set clean — only "clean on what can be detected".**

## ⛔⛔ THE GATE HAD FALSE NEGATIVES — FOUND BY EAR, FIXED, 2026-09-04

The owner listened to six ear-confirmed repeat repairs. **The gate had PASSED two
takes that still contained the defect** — the failure this file elsewhere calls
worse than no screen, because it licenses calling a set clean. Two independent
mechanisms, both now fixed and re-validated (10/10 confirmed, 1/40 controls):

- **`tail_repeat` joined tokens into one string**, so ONE mistranscribed word
  diluted the whole span below FUZZ. ylt 19/30 v21: the kept take's own recorded
  transcript reads «clothed WAS scarlet WITH scarlet» — a real doubling in which
  the ASR merely heard the first copy differently — and scored 0.762 vs FUZZ 0.85.
  ▶ Fixed with a per-token majority path (`STRONG_TOKEN`/`MIN_STRONG_LEN`).
- **`append_tail` fired only on a PURE trailing insert.** When the LAST wanted
  word is also mistranscribed (`shaul` -> `shawl`), difflib emits one `replace`
  and the extra word is swallowed inside it. ylt 12/3 v24: «...zerah shaul SHOP»
  flagged, «...zera shawl SHRI» PASSED. ▶ Fixed by also reading the excess out of
  a final `replace`, gated on the aligned words actually resembling each other.

⚠ **COST, MEASURED, NOT HIDDEN:** controls went 0/40 -> 1/40. The new flag is
Gen 36:29 «chief Lotan, chief Shobal, chief Zibeon...», which repeats IN THE
PRINTED TEXT — the already-known text-repeat class.
⛔ **DO NOT RAISE `PAIR_JOINED_FLOOR` TO 0.75 TO REMOVE IT.** The true positive
scores 0.762 and that control 0.700; picking a number between them is fitting the
threshold to the validation set. A false POSITIVE costs seconds of listening; a
false NEGATIVE ships a defect.

⚠⚠ **SO «repaired 169 chapters OK» FROM THE 2026-09-04 ylt RUN IS NOT EVIDENCE
THE DEFECTS ARE GONE** — that number was produced by the buggy gate. Treat it as
unverified. The build gate stays closed at versionCode 18.

## ⛔⛔ THE REPAIR OVERWRITES THE VALIDATION GROUND TRUTH

`repair_verses.py` splices fresh takes into `narration/<set>/`, so **after a
repair the live tree no longer contains the defects the screens were validated
on.** Measured 2026-09-04: `qa_selfrepeat --validate` scored the ten
ear-confirmed ylt verses **0/10** and printed «⛔ do not use it» — it was reading
REPAIRED audio. Trusting that would have condemned a working detector, or worse,
prompted "retuning" it against audio the defect had been removed from.

- ✅ Both validators now read the confirmed verses from
  `narration/<set>_qa_fail_originals/` and PRINT how many came from there.
- ⚠ **Never delete `*_qa_fail_originals/` — it is the project's only copy of the
  ground truth**, not merely a backup of shipped audio.
- ⛔ `qa_selfrepeat --validate` also **exited 0 while printing «do not use it»**,
  so ✅ and ⛔ were indistinguishable to anything gating on the exit code —
  including the preflight stamp that licenses a render. Now exits non-zero.

## ⛔ A MID-VERSE REPEAT HAS NO INSTRUMENT — structural, but NO CONFIRMED CASE

⚠ **THE GAP IS REAL. Every screen looks at the ends:** `qa_selfrepeat` reads the
TAIL, `qa_asr_sweep` APPEND tests for words AFTER the last text word,
`qa_substitution` reports only single-word neighbour-copies. Nothing looks in the
middle, so a mid-verse repeat in a verse with a clean tail is invisible today.

⛔⛔ **BUT THE ONE ALLEGED INSTANCE WAS WITHDRAWN — owner's ear, 2026-09-05.**
This block was founded entirely on Isaiah 24:21 (`22/23 v21`), recorded on
2026-09-04 as speaking «of the high place OF THE HIGH PLACE» where «the text
prints it once». **Both halves were wrong.**

- **The text prints it TWICE.** YLT reads «on the host of the high place **IN**
  the high place, And on the kings of the land on the land» — doubled twice over,
  and both doublings are scripture.
- **The audio is CORRECT.** Re-heard on the clip set: «it sounds fine, hosts of
  the high place in the high place». The verse has no defect of any class.

▶ It is retracted from `_work/ylt_ear_confirmed_repeats.txt` (commented, not
deleted). ⚠ It was never in `EAR_CONFIRMED_YLT`, so no validator was scored
against it — had it been, every screen would have looked one worse for correctly
PASSING a clean verse.

⚠⚠ **MEASURED COST OF BELIEVING IT: `repair_verses.py` re-drew this clean verse
3× on 2026-09-05 and every draw «failed».** It always will: the gate fires on
«of the land on the land», which is printed, so **a verse whose gate flag is
text-explained can never pass and can never be repaired by redrawing.** Check
whether a flag is explained by the printed text BEFORE queueing draws.

▶ So the honest statement is: **the instrument gap is structural and unfixed, and
there is no confirmed mid-verse repeat in this corpus.** Do not cite Isaiah 24:21
for it. If a real one turns up, record it here in its place.

## ⚠ TWO TOOLS WRITE `<c>.qa.json` AND THEY DO NOT SHARE A SCHEMA

`narrate.py`'s gate writes `{judged, redrawn, failing, unjudged}`;
`repair_verses.py` writes `{repairs:[...], realigned:{}}`. `render_preflight.py
report` read the first with four `q.get(key, 0)` calls, so **every
repair-written record defaulted to zero and it printed «still failing 0» and a
✅ VERDICT over 234 files it had not understood a byte of** (ylt, 2026-09-04 —
all 234 records on disk were repair-schema; it was 100 % blind). Now it reads
both and REFUSES (exit 1) on an unrecognised file instead of defaulting.

## ⛔⛔ TWO MORE SCREENS WERE FOUND UNDER-REPORTING — 2026-09-06

Both failed in the direction that sends an EAR, and GPU, at verses that can never
pass. That is now **five** instrument bugs in this family in four days, every one
of them under-reporting. ▶ **Assume a new screen is broken until a control fires.**

- ⛔ **`qa_text_explained.py` COULD NOT SEE A SINGLE-WORD DOUBLING.** Its tail scan
  started at `n = 2`, so «…by men, Rabbi, Rabbi.» was structurally invisible: the
  bigram `(rabbi, rabbi)` occurs ONLY at the tail, and the scan excludes the tail.
  The midday handoff cited «rabbi rabbi» as a TEXT-EXPLAINED example — it was not;
  that verse was in the ear queue.
  ⚠ **The naive fix is wrong.** Starting the existing «occurs anywhere earlier»
  rule at n=1 excuses any verse ending in «the». **A false TEXT-EXPLAINED discards
  a real defect**, so the rule is LOCAL and CONTENTFUL (`local_tail_double`):
  adjacent doubling of the last n words, or `X <thin joiner> X`, contentful words
  only. ✅ `--validate` now runs **8** controls including two negatives.
  ▶ Re-triage moved **14 of 69** rescreen verses, 13 EAR -> TEXT-EXPLAINED; the
  ear queue went 35 -> 24. Full-corpus sweep: 54 newly caught of 31,102 (0.17 %).
  Write-up: `research/_evidence/qa_text_explained_singleword_bug_2026-09-06.md`.
- ⛔ **`qa_asr_clips.py` TRUNCATED SILENTLY.** Its `--limit` default of 12 kept 12
  of the **169** verses the full sweep log selects, with no warning — an ear set
  built from it would have covered 7 % of the scope and looked complete. Now it
  warns whenever it truncates, `--limit 0` means all, and a `--queue` that yields
  nothing **exits non-zero**. It also takes a plain `book chapter vN` queue and
  prints each verse's PRINTED TEXT (a gate FAIL carries no «appended words» claim).

⛔ **AND THE AUTHORITY IS THE TEE'D LOG, NEVER THE TASK OUTPUT.** A repair run was
launched through `| tail -60`; the visible output showed **2** failures and the
real log had **4**. Caught only because the summary line disagreed. The «do not
pipe through `tail`» rule is elsewhere in this file and was broken anyway.

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

