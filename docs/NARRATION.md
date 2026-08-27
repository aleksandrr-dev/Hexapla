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
