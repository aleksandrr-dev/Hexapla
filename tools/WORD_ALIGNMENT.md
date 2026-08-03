# Word-level alignment for recorded narration

Written 2026-08-03. Covers `tools/align_words.py`, `tools/verify_word_alignment.py`,
the app wiring that consumes them, and the script/language coverage findings —
including the two things a future session would otherwise re-research from
scratch (uroman coverage, and whether CJK needs a segmenter).

**Status: built and verified on four rendered sets. The bulk pass has NOT been
run, nothing is uploaded, and no `.w.json` exists on archive.org yet.**

---

## 1. What this is

Device TTS highlights the current WORD as it speaks, because the engine reports
character ranges live through `onRangeStart`. Recorded narration had no
equivalent — `startVerseFollow` could only highlight the whole verse from the
per-verse `"o"` offsets. Forced alignment recovers the missing information
offline.

The output is deliberately **the contract the app already consumed**:
character ranges into the DISPLAYED verse text, exactly what
`Playback.wordStart` / `Playback.wordEnd` take from TTS. That is why
`ReaderScreen` needed no change at all — it already renders that range.

    narration/<dir>/<book>/<chapter>.w.json
    {"v": [ [[startMs, endMs, charStart, charEnd], ...],   # verse 0
            null,                                           # verse 1 unaligned
            ... ]}

`null` means the aligner could not place that verse; the app falls back to
verse-level highlighting for it alone. **Callers must treat a missing or null
entry as "verse-level only", never as an error** — a set whose audio shipped
before alignment is the normal case, not a broken one.

## 2. Commands

    # align (CPU; use the kokoro venv, see §7)
    tools\.kokoro_venv\Scripts\python.exe tools\align_words.py --set wbt --book 0 --chapter 0 --report
    tools\.kokoro_venv\Scripts\python.exe tools\align_words.py --set wbt          # whole set

    # verify against an independent witness
    tools\.kokoro_venv\Scripts\python.exe tools\verify_word_alignment.py --set syn --book 0 --chapter 0

## 3. Verified results

Genesis 1 on each rendered set. The right-hand column is `verify_word_alignment.py`
comparing our timings against faster-whisper's own word timestamps — a
different model family, so a genuinely independent estimate.

| set | script | verses | words | unmapped | median Δ | p90 Δ |
|---|---|---|---|---|---|---|
| `wbt` Webster | Latin | 31/31 | 794 | 0 | 70 ms | 172 ms |
| `syn` Russian Synodal | Cyrillic | 31/31 | 636 | 0 | 90 ms | 221 ms |
| `kxii` Karl XII | Latin + åäö | 31/31 | 662 | 0 | 82 ms | 173 ms |
| `gen1599` Geneva | Latin, archaic | 31/31 | 814 | 0 | 78 ms | 167 ms |

Whisper's own word timings carry roughly 50-100 ms of slop, so these agree.
The check exists because **the aligner's output always looks plausible** —
every word gets a monotone range inside its verse, so nothing in the FILE
reveals whether the ranges point at the right audio. Only an outside witness
can tell you that.

⚠ HONEST CAVEAT on `kxii`: median was fine but the sampled verse matched only
21/41 words and threw a 2308 ms outlier. Whisper transcribes 17th-century
Swedish poorly, so this is *probably* a bad pairing in the comparison rather
than a bad alignment — but that was never proven. Do not quote Karl XII as
clean without re-checking it.

## 4. The three things that make this harder than "run an aligner"

1. **The audio was not rendered from the displayed text.** `narrate.py` strips
   margin notes and runs a per-language normalizer (archaic English u/v rules,
   Russian stress marks, Slavonic digits). Alignment must run on the NORMALIZED
   text — that is what was spoken — then map each word back to its character
   range in the DISPLAY text, which is what the reader sees. The two token
   streams are not always the same length, so the mapping goes through difflib
   and anything unmappable emits `-1` rather than a guess. Geneva is the proof
   this works: the output reads `heauen@4567`, display spelling in the range,
   alignment done on "heaven".

2. **The chapter ogg is a concatenation.** Verse *i* occupies
   `[offsets[i], offsets[i+1] - 600ms)`, the 600 ms being the silence gap
   `concatenate_with_silence` inserts. Per-verse slicing keeps a bad verse from
   dragging its neighbours' timings.

3. **`-` IS MMS_FA'S BLANK TOKEN** (id 0), not a letter. Keeping hyphens in the
   folded key makes `forced_align` reject the ENTIRE verse with "targets
   shouldn't contain blank index". "Beth-el" folds to "bethel"; the printed
   hyphen is still covered by the highlight because the range comes from the
   display text.

Two smaller traps worth recording:

- **torchaudio 2.11 removed its own decoders** and defers to `torchcodec`,
  which is not installed. `torchaudio.load` therefore fails on the oggs. We
  decode through ffmpeg instead — already a hard dependency, and it does the
  downmix and resample in the same pass.
- **Use `AF.merge_tokens`, not a hand-rolled non-blank-run counter.** Counting
  runs miscounts legitimately repeated letters (the two l's in "all") and
  silently shifts every later word in the verse.

## 5. Script coverage — measured, not assumed

MMS_FA's token set is essentially `a-z`. Latin folds directly (accents
decomposed and dropped). Everything else goes through **uroman**, which is what
MMS_FA was TRAINED on — so this is the model's intended input path, not a
workaround, and a hand-written transliteration table would be the wrong choice.
Russian stress marks vanish for free, being combining accents.

⚠ Romanize **per word, never per verse**: uroman splits and joins around
punctuation, and a word-count change would silently shift every later word's
timing by one.

Measured on real verses, 2026-08-03:

| script | romanizes | word count preserved |
|---|---|---|
| Persian, Greek, Hebrew, Tamil, Armenian, Georgian, Icelandic, German | yes | yes |
| **Chinese, Japanese** | yes | **NO — collapses to one token** |

`起初神创造天地` → `qichushenchuangzaotiande`, a single word.

**Every language in the current project queue** — Icelandic, the Karl XII and
Luther apocrypha, Glen Persian — gets both verse- and word-level following with
no new work.

### CJK needs a segmenter — scoped, deliberately NOT built

There is no Chinese or Japanese narration rendered, in progress, or queued;
`narrate.py` has no `zh`/`ja` entry in `LANG_CONFIG` at all. Building this now
would mean writing code against a pipeline that does not exist and cannot be
tested end to end. It was scoped only to establish that it is **not a blocker**.

Tested 2026-08-03 against the actual shipped assets (`zh_cuv_t.json`,
`ja_meiji.json`), because CUV is 1919 Chinese and Meiji is *classical*
Japanese — neither is what modern dictionaries are tuned for:

    起初，神創造天地。          -> 起初 | 神 | 創造 | 天地           correct
    太初有道，道與神同在…      -> 太初 | 有道 | … | 神同 | 在        WRONG (有|道, 神|同在)
    元始に神天地を創造たまへり  -> 元始|に|神|天地|を|創造|たまへ|り   good
    …乏しきことあらじ           -> 乏し | きこ | と                   WRONG (乏しき|こと)

`jieba` (Chinese, MIT, pure Python) and `fugashi` + `unidic-lite` (Japanese,
MeCab wrapper) both install in about a minute with no compiler and no GPU. Both
are mostly right and both mangle John 1:1, which is not a reassuring place to
fail.

**But the failure mode is mild**: a mis-segmentation moves a HIGHLIGHT
BOUNDARY (the box covers 神同 instead of 神). It does not touch displayed text,
does not affect verse-level following, and does not propagate into any asset.
This is cosmetic imprecision, not the data-corruption class this project
normally guards against.

Both are fixable by the pattern already used elsewhere here:
- **Chinese**: jieba takes a user dictionary — a curated list of biblical
  collocations (同在, 太初, 必不致) fixes the recurring errors. It already knows
  耶和華.
- **Japanese**: the right answer is a different dictionary, not a word list —
  NINJAL publishes **近代文語UniDic** for Meiji-era literary Japanese, exactly
  Meiji Motoyaku's register. Not a pip one-liner, but it exists.

When zh/ja narration is actually queued this is roughly half a day: segment the
display text, romanize each segment, feed the existing aligner. Everything
downstream already works.

## 6. App wiring (in tree, compiles, NOT device-verified)

**`Audio.kt`** — `AudioRepo.words(context, section)` fetches
`<chapter>.w.json` from beside the ogg (`wordsUrl`) and caches it on the same
path as the audio, so it is offline after first listen. A malformed sidecar
deletes itself and returns null rather than breaking playback.

⚠ **Word timings are deliberately NOT in `audio_index_gen.json`.** They run
~17 KB per chapter → ~17 MB per translation, against that index's present
724 KB for four sets. They must stay per-chapter sidecars.

**`ReadingService.startVerseFollow`** — now also publishes
`Playback.wordStart/wordEnd`. Three decisions worth keeping:
- Word data is fetched in a CHILD coroutine, so verse-following starts on the
  first poll instead of waiting on a network round trip.
- Poll drops to **60 ms only when word data exists**. A word lasts ~300 ms, so
  the 250 ms verse cadence would visibly lag or skip words; unaligned chapters
  keep the cheap 250 ms loop.
- In a gap between words the highlight is CLEARED, not left stuck on a word
  that already finished.

`ReaderScreen` needed no change.

## 7. Environment

Run alignment from **`tools/.kokoro_venv`**, not `.cosyvoice_venv`: the latter
has a live render process reading from it, and pip must not disturb it. The
kokoro venv is the better home anyway — CPU-only torch 2.13 / torchaudio 2.11,
plus faster-whisper for verification.

Added there 2026-08-03: `uroman`, `jieba`, `fugashi`, `unidic-lite` (~60 MB).

⚠ Alignment is CPU-bound and **competes with renders**. Chatterbox already cost
ru half its throughput once (19.1 → 7.1 ch/hr). Do not start a bulk pass while a
render is running.

## 8. Not done

- The bulk pass over any complete set (`wbt`, `kxii`, `gen1599`).
- Uploading `.w.json` files to the archive.org items. ⚠ Remember the metadata
  trap from the Karl XII ship: `internetarchive.upload(metadata=…)` does NOT
  apply to an EXISTING item; `upload_narration.py` now calls `modify_metadata()`
  explicitly.
- On-device verification of the word highlight.
- `tyn` (1 chapter rendered), `wyc` and `cu` (zero rendered) — nothing to align.
- The 22 KJV gap books in `narration/en` use the older `audio_index.json`
  format and are not in `SETS`.

## 9. LibriVox verse alignment — SCOPED, not built

**The prize:** LibriVox audio has NO verse-following at all today, because only
generated sets carry offsets. Alignment could derive verse boundaries as well
as word ones, giving the KJV — the app's most-read translation — the same
highlighting and exact seek-to-verse the self-rendered sets have.

**Measured inputs** (`audio_index.json`): 72 books, **705 sections**. 482 are
single-chapter; **223 span multiple chapters, one as many as 19**. That
distribution is the whole difficulty.

**Four problems, in order of nastiness:**

1. **Trellis blowup on long sections.** Alignment cost is frames × tokens; a
   19-chapter section is ~10⁵ frames against ~5×10⁴ tokens — not holdable in
   memory. Needs windowed alignment: coarse anchors first (Whisper timestamps,
   or a chapter-announcement search), then per-chapter fine alignment. This is
   the bulk of the work.
2. **Audio with no matching text.** LibriVox boilerplate, reader credits,
   chapter announcements, possibly spoken verse numbers. Plain `forced_align`
   assumes every second of audio has corresponding text. MMS_FA's `*` star
   token exists precisely for this.
3. **Data-model change.** `Section.offsets` is per-verse for ONE chapter. A
   section spanning 19 chapters needs offsets keyed by chapter within the
   section — touching `audio_index.json`, `Audio.kt` and `startVerseFollow`.
4. **Multi-reader variance.** Voices change between and within books, so
   alignment quality will not be uniform; per-chapter verification is mandatory
   rather than a spot check.

**Effort:** the aligner core exists and is verified, so this is mostly the
windowing engine plus the data-model change — a solid session, not a campaign.
Compute is the larger cost: the full KJV reading is ~75-90 h of audio, so a CPU
pass is on the order of days and must queue behind ru.

**Resolve this unknown FIRST:** do the readers speak verse numbers aloud? If
yes they are enormous free anchors and problem 1 gets much easier; if no, the
coarse pass leans entirely on Whisper. One ASR run on one sample settles it
(`bible_01a_kjv_64kb.mp3`, PD, the file the app already streams).

⚠⚠ **STRATEGIC CAVEAT — do not start this without an owner decision.** All of
it is worth building ONLY if LibriVox stays. The owner is weighing replacing the
LibriVox KJV with his own cloned-voice render (SESSION_HANDOFF 2026-08-03 §8);
if he does, offsets come free from `narrate.py` and this entire effort is
discarded. The two are not equal in cost: alignment is days of CPU on existing
machinery, whereas a full KJV re-render is ~1,058 chapters, the largest render
yet attempted.
