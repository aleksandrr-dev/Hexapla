# -*- coding: utf-8 -*-
"""Diagnose WHAT is at the end of a component clip — truncation, or junk.

The tail-energy score says a clip is still at full speech level when it stops.
That has two very different causes and they need opposite fixes:

  * TRUNCATION — the word itself is chopped. The last recognized word runs to
    the very end of the audio.
  * TRAILING JUNK — the words finish cleanly and the engine then emits an
    artifact (vocoder noise, a repeated fragment, a breath). The last word ends
    well BEFORE the audio does.

Whisper word timestamps separate them: compare the end of the last recognized
word against the length of the clip.

    python tools/diag_tails.py ch_50 ch_60 ch_62 ch_53 ch_55
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))

import build_announcements as ba

LIB = Path("C:/Projects/Hexapla-releases/narration/ru_announce_lib")


def main():
    keys = sys.argv[1:]
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)

    print(f"{'key':9} {'ms':>6} {'lastword_end':>12} {'gap_ms':>7} {'cut':>5}  text / heard")
    for k in keys:
        f = LIB / f"{k}.wav"
        if not f.exists():
            print(f"{k:9} MISSING")
            continue
        a, sr = sf.read(str(f), dtype="float32")
        a = a.mean(1) if a.ndim > 1 else a
        ms = len(a) / sr * 1000
        segs, _ = model.transcribe(str(f), language="ru", beam_size=5,
                                   word_timestamps=True,
                                   condition_on_previous_text=False,
                                   vad_filter=False)
        words = [w for s in segs for w in (s.words or [])]
        heard = " ".join(w.word.strip() for w in words)
        end = words[-1].end * 1000 if words else 0.0
        te = float(ba.tail_energy(a, sr))
        print(f"{k:9} {ms:6.0f} {end:12.0f} {ms - end:7.0f} {te:5.2f}  {heard!r}")

        # Envelope of the final 600 ms, 20 ms bins — the shape tells the story:
        # a finished word decays, a chopped one holds level, junk spikes late.
        win = max(1, sr // 50)
        tail = a[-int(sr * 0.6):]
        env = [float(np.sqrt((tail[i:i + win] ** 2).mean()))
               for i in range(0, len(tail) - win, win)]
        peak = max(env) or 1.0
        print("          last 600ms: " + "".join(
            " .:-=+*#%@"[min(9, int(9 * e / peak))] for e in env))


if __name__ == "__main__":
    main()
