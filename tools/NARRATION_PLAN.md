# Self-generated narration — execution plan (roadmap item 4)

Planned 2026-07-13 (Fable session, full context in CLAUDE.md). This
document is self-contained: an executing session (Sonnet/Haiku) should
be able to work from it plus CLAUDE.md alone. Escalation points where
a stronger model or the owner must decide are marked ⚠ GATE.

## Goal

Generated audio narration hosted on archive.org, served through the
existing per-section download flow (ReadingService MediaPlayer backend,
see audio_index.json), for:
1. RUSSIAN — the whole Synodal (no human narration exists in-app).
2. ENGLISH — the 22 KJV books LibriVox lacks (audio_index.json covers
   50 of 66; the missing books currently fall back to TTS).
Later, same pipeline: Tamil, German, Spanish etc. if voice quality passes.

## ⚠ RESOLVED 2026-07-15 — READ THIS BEFORE THE SECTIONS BELOW

The Russian engine question is **SETTLED**. Much of what follows is now
historical; it is kept because the licensing research is reusable and the dead
ends must not be re-walked. What was actually decided:

- **ENGINE: Fun-CosyVoice3-0.5B-2512** (Apache-2.0 weights, Russian confirmed
  on the model card AND empirically). Repo cloned to `C:/Projects/CosyVoice`,
  model in its `pretrained_models/`. Runs **in-process**, so `--lang ru` must
  use `tools\.cosyvoice_venv\Scripts\python.exe`.
- **VOICE: the owner's own voice.** He recorded 3 takes 2026-07-15;
  `narration/myvoice_take1.wav` (the natural one) is the zero-shot reference
  for all 83 books. Free, no licence question, keeps donations and the F-Droid
  path, and it is *his* voice on his evangelism project.
  NOTE the 3 takes are NOT 3 narrators — measured, they differ by only 0.7-1.2
  semitones and CosyVoice normalised that away entirely (take2 was recorded
  DEEPER but cloned back HIGHER, 88.4Hz -> 99.7Hz). The reference is a speaker
  embedding, not a performance.
- **STYLES: three, via `inference_instruct2`** — normal / solemn / tender, mapped
  per book in `narrate.py` (`RU_STYLES`, `RU_BOOK_STYLES`). Owner's assignment:
  solemn = Job + prophets + Revelation; tender = Ruth, Psalms, Song of Songs.
  Solemn at 2.24x duration was auditioned and **approved** 2026-07-15.
- **STEP 2 (stress dictionary) IS MOOT.** See below.
- **Edge TTS: legally unusable.** MSA §14.f.i is "noncommercial, **personal**
  use only" and bars "redistributing these materials, or using these materials
  ... to build your own products" — which is what cloning its output would be.
  The library computes an anti-abuse token in a module its own maintainer named
  `drm.py`. Do not revisit. **Paid Azure S0 IS usable** if the owner ever wants
  the real `ru-RU-DmitryNeural`: Product Terms grant "for Customers of the paid
  tier TTS Service only ... may use the audio output of prebuilt neural voices
  ... including for commercial purposes". ~$60 for 4,002,105 chars. Two catches:
  the **F0 free tier gets NO output rights** (every shipped char must be S0),
  and disclosing the AI-generated voice is **contractual** (Enterprise AI Code
  of Conduct), though no attribution is required.

## Engines (verify before building — field moves fast)

- ENGLISH: Kokoro-82M (Apache 2.0). Quality reference point.
- RUSSIAN: Kokoro has NO Russian. Candidate sweep run 2026-07-15,
  results below. ⚠ GATE (licensing): each candidate VOICE/model has
  its own training-data lineage — verify it permits redistribution of
  generated audio in a free app BEFORE generating anything public.
  Same discipline as text sources (see the Dvoretsky gate in CLAUDE.md).
  ⚠ GATE (owner): generate Псалом 22 + Иоанна 1 in each candidate
  voice; owner picks by ear. Prefer calm, unhurried, male.

  METHOD RULE, learned the hard way 2026-07-15 — read this first:
  Two whole classes of error were found in this list on one day, and
  both had the same shape: a TRUE statement about ONE variant was
  generalized into a FAMILY-WIDE dead end.
    (a) "Silero is CC BY-NC — ruled out" — true of v4_ru/v5_5_ru/
        v5_cis_ext, FALSE of v5_cis_base (MIT). Nearly cost us the
        best candidate.
    (b) "Piper voices need per-voice license checks" — the check was
        never finished. ruslan is NC, denis+dmitri are CC0. The owner
        auditioned ONLY ruslan (the one voice we could never ship),
        disliked it, and the engine got written off.
  So: (1) CODE license =/= WEIGHTS license =/= TRAINING-DATA license;
  the last one governs redistributable audio. (2) Never write a
  family-wide verdict from one variant. (3) Quote the exact sentence
  + URL, or write UNVERIFIED — a bare assertion is what rots. (4) READ
  THE SUPPORTED-LANGUAGE LIST BEFORE INSTALLING ANYTHING.

  RULED OUT (verified 2026-07-15 against primary sources):
  - Edge TTS (voice "Dmitry") — owner's quality favourite and the
    BENCHMARK to beat, but the audio may not be redistributed.
    Reference only.
  - CosyVoice2 (FunAudioLLM/CosyVoice2-0.5B) — NO RUSSIAN. Scoped
    claim: this is true of CosyVoice **2** only. Trained zh/en/ja/ko
    + dialects; EU fork (Luka512/CosyVoice2-0.5B-EU, pip
    `cosyvoice2-eu`) adds only fr/de. A zero-shot clone of a Russian
    reference produces confident phonetic gibberish (owner: "sounds
    like some african language"). Cost ~2h of MSVC/CUDA/py3.11/
    DeepSpeed/pynini yak-shaving before the model card was read.
    Model deleted (4.5 GB). NOTE the successor DOES do Russian — see
    Fun-CosyVoice3 under LIVE CANDIDATES. Do not generalize "CosyVoice
    = dead"; the 9-language list on the CosyVoice2 HF page describes
    v3, not v2, which is itself a trap.
  - Piper ru_RU-ruslan — CC BY-NC-SA 4.0 training corpus
    (ruslan-corpus.github.io: "Corpus is available here (7 Gb) under
    the CC BY-NC-SA 4.0 license"). NC in the lineage = never
    shippable, independent of the owner's "robotic" verdict.
  - Piper ru_RU-irina — license UNKNOWN upstream. Piper's own
    MODEL_CARD says "License: Unknown"; github.com/RHVoice/irina-rus
    has no LICENSE file. (Repology says CC-BY-SA-4.0 but that is a
    packager's assertion, not upstream.) RHVoice voices carry
    individually restrictive terms (Talgat NC; Natia personal-use).
    Unusable by default — but this is absence of evidence, not proven
    NC. Re-check if upstream ever states a license.
  - XTTS v2 (Coqui) — code MPL-2.0, WEIGHTS Coqui Public Model License
    (NC). CPML reaches the OUTPUT, not just the model: no "direct or
    indirect payment arising from the use of the model or its output".
    Coqui shut down Jan 2024 so no counterparty for a commercial
    license; status effectively frozen. The idiap/coqui-ai-TTS fork
    relicenses only CODE and cannot relicense weights.
  - Fish Speech — Fish Audio Research License covers code AND weights;
    explicitly extends to fine-tunes and LoRA derivatives. Has moved
    TOWARD restriction over time.
  - Silero v4_ru, v5_5_ru, v5_cis_ext — CC-NC-BY. (But NOT the base
    cis models — see below.)
  - Bark — LICENSING IS CLEAN (MIT code + MIT weights; relicensed from
    CC-BY-NC on 2023-05-01). Rejected ONLY on quality (fan/background
    noise). Recorded so a future session doesn't re-rule-it-out on a
    stale "Bark is NC" belief.

  LIVE CANDIDATES:
  - Piper ru_RU-denis / ru_RU-dmitri — **CC0 (public domain)**, the
    cleanest license on this list: no attribution, no conditions.
    Training data github.com/OHF-Voice/voice-datasets: "These datasets
    are licensed under CC0 (public domain)" (crowdsourced for Home
    Assistant's Year of Voice by Nabu Casa). CC0 data + MIT engine =
    zero restriction on redistributing generated audio. Models were
    ALREADY in tools/piper_models/ — downloaded by an earlier session
    and never auditioned. Samples generated 2026-07-15 via
    tools/test_piper_ru.py. Piper is faster than realtime on CPU,
    which also makes it the cheapest option to run for a whole Bible.
    ENGINE NOTE: rhasspy/piper was archived 2025-10-06 and moved to
    OHF-Voice/piper1-gpl (GPL-3.0). GPL is irrelevant here because we
    use Piper BUILD-TIME ONLY to render audio files; generated audio
    is not a derivative of the synthesiser. The archived MIT version
    also still works.
  - Silero v5_cis_base / v5_cis_base_nostress — **MIT**, NOT NC.
    snakers4/silero-models README, V5 CIS Base section: "All of the
    below models are published under `MIT` licence"; and "All of the
    models are published under the main repo license (i.e. CC-NC-BY)
    except for the `base` cis-tts models, which are under MIT."
    v5_cis_base does AUTOMATIC STRESS MARKING — if it holds up this
    may shrink or delete step 2 (the ru_stress.py table) below.
    29 Russian speakers (ru_* prefix; males incl. dmitriy, alexandr,
    igor, roman, bogdan, eduard, marat, gamat). It is a multilingual
    CIS model — non-ru_ speakers (bak_, kaz_, tgk_, ukr_ ...) read
    Russian with an accent; ignore them. Samples 2026-07-15 via
    tools/test_silero_ru.py. Loads via torch.hub.load (clones+executes
    the repo — owner approved 2026-07-15). Weights also at
    models.silero.ai/models/tts/ru/v5_cis_base.pt.
  - vosk-tts (alphacep, Apache 2.0) — `pip install vosk-tts`, model
    vosk-model-tts-ru-0.9-multi (747 MB zip), 5 Russian speakers
    (speaker_id 0-4). Owner 2026-07-15: spk4 "sounded ok", still not
    matching Edge. tools/test_vosk_ru.py.
  - **Fun-CosyVoice3-0.5B-2512 (FunAudioLLM) — ★ CHOSEN, IN PRODUCTION.**
    Apache-2.0 WEIGHTS (license tag verified on the HF model card, not
    just the repo footer). Russian confirmed on the card AND by ear.
    Owner 2026-07-15, cloning his own voice: "This one's actually good,
    closest to Edge yet." Wired into narrate.py as engine "cosyvoice3".
    Install notes, since the CosyVoice2 attempt cost ~2h:
      * `git clone --recursive` FunAudioLLM/CosyVoice -> C:/Projects/CosyVoice
      * requirements.txt marks deepspeed linux-only (skips itself on Win)
        and uses `wetext`, NOT WeTextProcessing/pynini — wetext installs
        clean on Windows via a prebuilt kaldifst wheel. Both of the walls
        that stopped CosyVoice2 are gone.
      * pip install the gaps WITHOUT the pins (they would downgrade the
        cu128 torch): wetext pyworld openai-whisper x-transformers
        hydra-core omegaconf inflect wget onnx gdown networkx matplotlib
        rich pyarrow diffusers lightning librosa gdown
      * DO NOT install torchcodec — it needs FFmpeg DLLs this box does not
        expose. Instead monkeypatch torchaudio.load to use soundfile (see
        _get_cosyvoice() in narrate.py); CosyVoice already asks for
        backend='soundfile' but modern torchaudio ignores that kwarg.
      * `AutoModel(model_dir=...)` needs the files named llm.pt/flow.pt/
        hift.pt. huggingface_hub's snapshot_download RELIABLY HANGS on the
        large LFS files here — curl them directly from
        huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512/resolve/main/<f>
        (skip llm.rl.pt, ~2 GB, unused).
    KNOWN BEHAVIOUR, not bugs:
      * NO Russian branch in its frontend — Cyrillic falls through the
        ENGLISH path, so any DIGIT is spoken in English. narrate.py spells
        chapter numbers and book-title numbers out in Russian. Never hand
        this engine a digit in Russian text.
      * `inference_instruct2` takes NO prompt_text, so the reference
        transcript cannot mismatch. `inference_zero_shot` DOES take one and
        a mismatch silently halves output speed — a 10s clip labelled with
        5s of text made every verse ~2x too fast (2026-07-15). If you ever
        use zero_shot, the transcript must be exact.
      * text under ~60 tokens is not split, and the LLM may emit EOS early
        on a multi-sentence passage. Per-verse synthesis (what narrate.py
        does) sidesteps this.
      * RTF ~1.9-2.2 measured. ~106 h of audio => ~9-10 days of GPU.
  - Qwen3-TTS (Apache-2.0, `pip install -U qwen-tts`) — WORKS, real
    Russian via language="Russian". 9 voices (aiden, dylan, eric,
    ono_anna, ryan, serena, sohee, uncle_fu, vivian). Owner heard all
    9 on 2026-07-15: "just ok". Fallback. tools/test_qwen3_tts_ru.py,
    tools/test_qwen3_voices.py.
  - F5-TTS — NOT for Russian, but recorded to correct the old blanket
    "F5-TTS = NC": code is MIT ("Our code is released under MIT
    License"); official checkpoints are CC-BY-NC "due to the training
    data Emilia"; BUT mrfakename/OpenF5-TTS-Base is **Apache-2.0**,
    trained on Emilia-YODAS (CC-BY) instead of Emilia (CC-BY-NC).
    ENGLISH-ONLY, so it is a possible EN alternative to Kokoro for the
    22 LibriVox gap books — not a Russian answer. CAVEAT: the Apache
    grant is the author's own legal reasoning about training on CC-BY
    data; not independently settled.

## Pipeline (tools/narrate.py, one script, per-language config)

1. TEXT PREP: read the translation asset (ru_synodal.json / en_kjv.json)
   via the same JSON shape all tools use. Per verse: strip nothing for
   ru (Synodal has no {} notes); for KJV strip {...} margin notes the
   same way BibleRepo.parseAsset does (colon = note, drop; no colon =
   supplied word, keep). Expand digits where the engine mishandles them.
2. ~~RUSSIAN STRESS DICTIONARY~~ — **MOOT, DO NOT BUILD. Resolved 2026-07-15.**
   CosyVoice3 handles Russian stress NATIVELY. The owner (native speaker)
   auditioned Matthew 1 — the genealogy, ~40 proper names back to back, no
   stress marks — and confirmed: "the names sound great". It is LLM-based,
   unlike the Piper/Bark engines this step was written for. `narrate.py` uses
   `normalizer: "ru_variants"`, NOT `"ru_stress"`.

   ⚠ AND THE TABLE THAT WAS BUILT IS POISON. tools/ru_stress.py was drafted in
   a cheap-model session working from this very plan. It looked entirely
   plausible. Audited over all 37,098 verses (tools/audit_ru_stress.py): of 197
   entries, **30 rewrite the word instead of accenting it, corrupting 1,029
   verses**:
       Вирсавия -> Виргавия   (Beersheba -> a non-word; Gen 21:31,32,33, 22:19)
       Христа   -> Христоса   (invented non-word for Christ)
       Ирод -> Ириод   Михей -> Михай   Иосиф -> Иосифа (wrong case)
       Нерон -> НерО́н (Latin capital O); 8 entries inject 'і' U+0456 (Ukrainian)
   THE INVARIANT any stress table must satisfy: stripping the combining acute
   (U+0301) from the output must be a NO-OP. Run tools/audit_ru_stress.py; every
   section must report zero before `ru_stress` may ever be re-enabled.

   THE LESSON, worth more than the table: this step carried a "⚠ GATE (quality):
   owner/native spot-check" marker. The gate was written; the check never
   happened; the output looked fine to anyone who does not read Russian. When
   delegating work whose failure is invisible from inside the task, the gate is
   not optional — it IS the work.
3. SYNTHESIS PER VERSE (not per chapter): synth each verse to wav,
   record duration, concatenate with ~600ms gaps (~900ms after
   paragraph-ish breaks is a later nicety). Per-verse synthesis gives
   exact cumulative offsets -> the timing index (feature win: verse
   highlighting + tap-to-seek during narrated audio, which LibriVox
   can't do — the app currently disables highlighting for narration).
4. POST: ffmpeg loudnorm (two-pass, target I=-19 LUFS mono), encode
   Opus 32kbps mono in .ogg (MediaPlayer supports ogg/opus since API 21;
   minSdk is 26 — fine). One file per chapter.
5. SIZES: whole Synodal ≈ 90-100 h ≈ 1.2-1.5 GB opus. 22 KJV books
   ≈ 30 h ≈ 450 MB. Piper is faster than realtime on CPU.
6. UPLOAD: archive.org via `ia` CLI, one item per language
   (e.g. hexapla-audio-ru), files ru/<bookIdx>/<chapter>.ogg.
   Metadata: PD/generated, link the app. Keep the upload script in
   tools/ (upload_narration.py).
7. INDEX: assets/audio_index_gen.json:
   { "<lang>": { "<bookIdx>": { "url": ..., "chapters": { "<ch>":
     { "file": ..., "offsets": [ms per verse] } } } } }
   (exact shape negotiable — design to be read by AudioRepo next to
   audio_index.json; keep verse offsets so the service can highlight).

## App changes (Kotlin, modest)

- ReadingService/AudioRepo: narration source selection becomes
  per-translation-language: kjv -> LibriVox where covered, generated
  for the 22 gap books; syn -> generated ru. Existing download-and-
  cache flow (per section) carries over; generated files are per
  chapter (smaller than LibriVox sections — simpler, keep per-chapter).
- Verse highlighting during narration: feed the offsets timing index
  into the existing Playback.verse mechanism (the TTS path already
  drives per-verse highlight; MediaPlayer path gains a position poll
  against offsets). Disable word-level highlight (verse-level only).
- Settings copy: audio_title/audio_note currently say "(KJV)" and
  "human narration from LibriVox" — reword ×13 locales to cover
  generated narration + credit (e.g. "and computer-narrated audio
  for books/languages without a recording"). Keep the LibriVox credit.
- sources_text ×13: add engine/voice attribution per its license.
- ⚠ GATE (review): the ReadingService diff is concurrency-sensitive
  (see CLAUDE.md architecture notes: never pre-queue TTS, one scroll
  collector, wakelock history). Have a strong model review the final
  service diff before release.

## Rollout

1. PoC: John 1 (ru) in 2-3 candidate voices -> owner listens (⚠ GATE).
2. Pilot: 4 Gospels ru (~9 h audio) end-to-end incl. app playback +
   highlight on-device.
3. Batch: NT ru -> Psalms ru -> OT ru; then the 22 KJV books (Kokoro).
4. Release as 1.4.x with store-notes headline "аудио на русском".

## Definition of done (per language)

- Every chapter of the target set plays from archive.org after a cold
  install with airplane-mode-then-online test.
- Verse highlight tracks within ±1 verse through a whole chapter.
- Spot-listen list: Пс 22/50/90, Ин 1, Быт 1, 1 Пар 1 (name-heavy),
  Откр 13 (numbers) — no mangled names on the curated list, no digit
  misreads.
- sources_text/audio_note updated ×13; lint at baseline; CLAUDE.md
  updated with the archive.org item ids and voice/license verdicts.
