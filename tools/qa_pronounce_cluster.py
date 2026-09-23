# -*- coding: utf-8 -*-
"""Find SPORADIC mispronunciations by clustering one word's audio across the set.

    tools\\.kokoro_venv\\Scripts\\python.exe tools/qa_pronounce_cluster.py --validate
    ...                                       --lang ylt --word Jehovah --scan

## The problem this exists for, and why nothing else solves it

The render mispronounces some words ALWAYS and some SOMETIMES.

  * ALWAYS  — `Canaan` is «can-a-yin» every time. A respelling in the synthesis
    input fixes it (`tools/pronounce_lexicon.py`), and the ASR can even see it:
    faster-whisper transcribes «Kanan», a token that differs from the text.
  * SOMETIMES — `Jehovah` is «Jee-hovah» in roughly 1 occurrence in 7 (owner's
    ear, 2026-09-04: 2 of a random 14). A respelling is the WRONG tool: it would
    rewrite all 6,626 occurrences to fix ~900 and put the ~5,700 good ones at
    risk.

⛔⛔ **AND THE ASR CANNOT SEE THE SPORADIC CASE.** Measured 2026-09-04 on the
owner's own labels: both verses he heard as «Jee-hovah» transcribe as `jehovah`,
identically to four he heard as correct. The mispronunciation is a subtle
first-vowel shift and whisper's language model snaps it back to the expected
word. So every text-comparison screen we have — APPEND, self-repeat,
substitution — is blind to it BY CONSTRUCTION, not by tuning.

## The idea, and the reason to distrust it

Compare the AUDIO of the word against itself across occurrences. The same word
rendered two ways should separate acoustically even when the ASR normalises
both. No reference text is needed, so this works on any set in any language.

⚠ **A closely related idea has already failed once here.** An audio
self-similarity detector was built for the tail-repeat defect and produced no
separation at all (confirmed 1.000 vs random 0.999). That was a different
question — «does this audio contain a repeat» — but it is a standing reason to
demand evidence before believing this one.

⚠ The obvious confound: these are different verses, so the word carries
different prosody, stress and neighbouring phonemes. That variation may swamp
the pronunciation difference. This is exactly what --validate tests.

## --validate is a REAL GATE, and its criterion is fixed in advance

Against the owner's 14 ear-labelled Genesis/Jeremiah occurrences (2 bad, 12
good), k-means with k=2 must put **both** bad clips in one cluster together with
**at most 2** of the good ones. That criterion is written here, before any run,
so it cannot be relaxed afterwards to make a result look like a pass.

⚠ Even a pass is weak: n=14, with only 2 positives. It licenses a bigger
labelled sample, NOT a repair queue.
"""
import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_spec = importlib.util.spec_from_file_location("qav", HERE / "qa_asr_verify.py")
qav = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qav)

OUT = Path("C:/Projects/Hexapla-releases/narration")

# The owner's ear, 2026-09-04, on a random sample of 14 (seed 11).
# (book, chapter, verse, is_mispronounced)
LABELS = [
    (2, 17, 1, False), (2, 18, 1, False), (2, 23, 13, False),
    (3, 8, 9, False), (3, 9, 1, False), (8, 14, 10, False),
    (25, 15, 35, True), (25, 16, 1, True),
    (25, 19, 45, False), (25, 20, 8, False), (25, 27, 20, False),
    (25, 29, 1, False), (25, 34, 1, False), (37, 5, 9, False),
]

N_MFCC, N_FRAMES = 20, 24


def word_clip(model, lang, b, c, v, word, td):
    """-> mono float32 audio of `word` inside that verse, or None."""
    side, ogg = OUT / lang / str(b) / f"{c}.json", OUT / lang / str(b) / f"{c}.ogg"
    if not (side.exists() and ogg.exists()):
        return None
    off = json.loads(side.read_text())["offsets"]
    i = v - 1
    if i >= len(off):
        return None
    wav = Path(td) / f"{b}_{c}_{v}.wav"
    qav.cut(ogg, off[i], off[i + 1] if i + 1 < len(off) else None, wav)
    segs, _ = model.transcribe(str(wav), language="en", beam_size=5,
                               vad_filter=False, condition_on_previous_text=False,
                               hallucination_silence_threshold=0.5,
                               word_timestamps=True)
    hit = None
    for s in segs:
        for w in (s.words or []):
            if word.lower() in "".join(ch for ch in w.word.lower() if ch.isalpha()):
                hit = (w.start, w.end)
                break
        if hit:
            break
    if not hit:
        return None
    import soundfile as sf
    a, sr = sf.read(str(wav), dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    # a little padding: the vowel we care about is at the word's onset
    s0 = max(0, int((hit[0] - 0.06) * sr))
    s1 = min(len(a), int((hit[1] + 0.06) * sr))
    return (a[s0:s1], sr) if s1 - s0 > int(0.08 * sr) else None


def features(a, sr):
    """MFCC, time-normalised to a fixed length, mean/var normalised. -> vector."""
    import torch
    import torchaudio
    t = torch.from_numpy(np.ascontiguousarray(a)).float().unsqueeze(0)
    mf = torchaudio.transforms.MFCC(
        sample_rate=sr, n_mfcc=N_MFCC,
        melkwargs=dict(n_fft=512, hop_length=128, n_mels=64))(t)[0].numpy()
    # resample along time so words of different DURATION stay comparable —
    # otherwise the longest clip dominates every distance.
    idx = np.linspace(0, mf.shape[1] - 1, N_FRAMES)
    mf = np.stack([np.interp(idx, np.arange(mf.shape[1]), row) for row in mf])
    v = mf.flatten()
    v = (v - v.mean()) / (v.std() + 1e-8)
    return v / (np.linalg.norm(v) + 1e-8)


def kmeans2(X, seed=0, iters=80):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), 2, replace=False)]
    lab = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        d = np.stack([((X - c) ** 2).sum(1) for c in C], 1)
        new = d.argmin(1)
        if (new == lab).all():
            break
        lab = new
        for k in (0, 1):
            if (lab == k).any():
                C[k] = X[lab == k].mean(0)
    return lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ylt")
    ap.add_argument("--word", default="Jehovah")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--model", default="small.en")
    a = ap.parse_args()

    if not a.validate:
        print("only --validate is implemented; it gates everything else.")
        sys.exit(2)

    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    X, meta = [], []
    with tempfile.TemporaryDirectory() as td:
        for b, c, v, bad in LABELS:
            r = word_clip(model, a.lang, b, c, v, a.word, td)
            if r is None:
                print(f"  ⚠ no word clip for {b}/{c} v{v} — skipped")
                continue
            X.append(features(*r))
            meta.append((b, c, v, bad))
    X = np.stack(X)
    print(f"\n{len(X)} word clips of {a.word!r}  "
          f"({sum(1 for m in meta if m[3])} labelled MISPRONOUNCED)\n")

    # majority vote over restarts, so the verdict is not one lucky seed
    labs = np.stack([kmeans2(X, seed=s) for s in range(9)])
    labs = np.array([np.bincount(labs[:, i]).argmax() for i in range(len(X))])

    for k in (0, 1):
        mem = [m for m, l in zip(meta, labs) if l == k]
        nb = sum(1 for m in mem if m[3])
        print(f"cluster {k}: {len(mem):>2} clips, {nb} of them ear-labelled bad")
        for b, c, v, bad in mem:
            print(f"    {b}/{c} v{v:<4} {'<-- EAR SAYS MISPRONOUNCED' if bad else ''}")

    bad_cluster = {l for m, l in zip(meta, labs) if m[3]}
    ok = False
    if len(bad_cluster) == 1:
        k = bad_cluster.pop()
        goods = sum(1 for m, l in zip(meta, labs) if l == k and not m[3])
        ok = goods <= 2
        print(f"\nboth bad clips in cluster {k}, with {goods} good clip(s) "
              f"(criterion: <= 2)")
    else:
        print("\nthe two bad clips landed in DIFFERENT clusters")

    print("\n" + ("PASS — the audio separates where the ASR could not. "
                  "⚠ n=14 with 2 positives:\n  this licenses a BIGGER LABELLED "
                  "SAMPLE, not a repair queue."
                  if ok else
                  "⛔ FAIL — no separation on the owner's labels. The confound "
                  "(different verses,\n  different prosody) swamps the "
                  "pronunciation difference, exactly as feared.\n  Do not tune "
                  "this to pass; report it dead and fall back to documenting\n"
                  "  the class as unscreenable."))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
