# -*- coding: utf-8 -*-
"""Independent check on align_words.py's word timings.

The aligner's own output always looks plausible: every word gets a monotone
range inside its verse, so nothing about the FILE reveals whether the ranges
point at the right audio. This compares them against a second, unrelated
estimate — faster-whisper's word timestamps, produced by a different model
from a different family — and reports the disagreement in milliseconds.

    python tools/verify_word_alignment.py --set wbt --book 0 --chapter 0

This is a REFERENCE-WITNESS check, not a ground truth: Whisper's own word
timings carry roughly 50-100ms of slop. A median disagreement in that range
means the two agree; a median of seconds means our alignment is sliding, which
is the failure that per-word highlighting would make painfully visible and
that no self-consistency check inside the aligner can see.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from align_words import (NARRATION, ASSETS, SETS, SILENCE_MS, WORD,  # noqa: E402
                         align_key, display_text)


# Whisper's own language codes, which are not the narrate.py language keys.
# Church Slavonic has no Whisper code; Russian is the closest relative and is
# good enough for a TIMING comparison, where only word boundaries matter.
WHISPER_LANG = {"wbt": "en", "gen1599": "en", "tyn": "en",
                "kxii": "sv", "syn": "ru", "csl": "ru"}


def cut(ogg, start_ms, end_ms, out_wav):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{start_ms/1000:.3f}",
         "-to", f"{end_ms/1000:.3f}", "-i", str(ogg),
         "-ar", "16000", "-ac", "1", str(out_wav)],
        check=True, capture_output=True, timeout=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=sorted(SETS))
    ap.add_argument("--book", type=int, default=0)
    ap.add_argument("--chapter", type=int, default=0)
    ap.add_argument("--verses", type=int, default=6, help="how many to sample")
    ap.add_argument("--model", default="small")
    ap.add_argument("--lang", help="whisper language code; defaults per set")
    args = ap.parse_args()

    cfg = SETS[args.set]
    whisper_lang = args.lang or WHISPER_LANG[args.set]
    d = NARRATION / cfg["dir"] / str(args.book)
    ogg = d / f"{args.chapter}.ogg"
    words = json.loads((d / f"{args.chapter}.w.json").read_text(encoding="utf-8"))["v"]
    offsets = json.loads((d / f"{args.chapter}.json").read_text(encoding="utf-8"))["offsets"]
    books = json.loads((ASSETS / "bibles" / cfg["asset"]).read_text(encoding="utf-8"))
    if isinstance(books, dict):
        books = books["books"]
    verses_raw = books[args.book]["chapters"][args.chapter]

    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=3)

    # Spread the sample across the chapter rather than taking the first N —
    # drift accumulates, so the end of a chapter is where it shows.
    idxs = [i for i, w in enumerate(words) if w]
    if not idxs:
        sys.exit("no aligned verses in this chapter")
    step = max(1, len(idxs) // args.verses)
    sample = idxs[::step][:args.verses]

    deltas = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in sample:
            start_ms = offsets[i]
            end_ms = (offsets[i + 1] - SILENCE_MS) if i + 1 < len(offsets) else None
            if end_ms is None:
                continue
            wav = Path(tmp) / f"v{i}.wav"
            cut(ogg, start_ms, end_ms, wav)
            segs, _ = model.transcribe(str(wav), word_timestamps=True,
                                       beam_size=1, language=whisper_lang)
            ref = []
            for s in segs:
                for w in (s.words or []):
                    # Whisper's transcript is folded through the SAME romanizer
                    # as our own words, so a Cyrillic set compares like for like
                    # rather than never matching anything.
                    k = align_key(w.word.strip(), cfg["script"], cfg["lang"])
                    if k:
                        ref.append((k, w.start * 1000 + start_ms))
            ours = [(align_key(display_text(verses_raw[i])[w[2]:w[3]],
                               cfg["script"], cfg["lang"]), w[0])
                    for w in words[i]]
            ours = [(k, t) for k, t in ours if k]
            sm = difflib.SequenceMatcher(None, [k for k, _ in ours],
                                         [k for k, _ in ref], autojunk=False)
            n = 0
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op != "equal":
                    continue
                for o in range(i2 - i1):
                    deltas.append(abs(ours[i1 + o][1] - ref[j1 + o][1]))
                    n += 1
            print(f"  v{i+1}: matched {n}/{len(ours)} words against whisper")

    if not deltas:
        sys.exit("FAIL: no words could be matched to the reference at all")
    deltas.sort()
    med = deltas[len(deltas) // 2]
    p90 = deltas[int(len(deltas) * 0.9)]
    print(f"\nwords compared: {len(deltas)}   median |delta| {med:.0f}ms   "
          f"p90 {p90:.0f}ms   max {deltas[-1]:.0f}ms")
    if med > 300:
        print("FAIL: the two alignments disagree by more than Whisper's own slop.")
        sys.exit(2)
    print("PASS: agrees with the independent reference within its slop.")


if __name__ == "__main__":
    main()
