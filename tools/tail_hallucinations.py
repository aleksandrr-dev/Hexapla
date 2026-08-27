# -*- coding: utf-8 -*-
"""Find verses whose audio keeps talking AFTER the last word of the text.

    tools\.chatterbox_venv\Scripts\python.exe tools/tail_hallucinations.py tyn
    ... tools/tail_hallucinations.py ylt --book 39 --clips

WHY THIS EXISTS (2026-08-21). The owner heard Chatterbox append words that are
not in the text at the END of a verse - "pole" after "came to him,", "nass"
after "kindness", "accord" after "Sons of God". He found three and stopped
listening, so three is a FLOOR, not a rate.

Nothing we had could find them:
  . duration/pace screens - a one-syllable insertion moves a five-second verse
    by ~0.3 s, inside the natural spread of a read;
  . `_trim_and_fade` - it removes a vocoder tail ~41 dB down; these are words at
    full speech level;
  . the `token_repetition` retry - v1 was flagged, retried, returned "clean",
    and still said "pole";
  . faster-whisper - handed famous scripture it RECITES THE NEXT VERSE from
    memory. It invented eleven consecutive "tails" on Matthew 5 that were pure
    hallucination on the ASR's part.

▶ THE ORACLE IS THE WORD SIDECAR WE ALREADY BUILD. `.w.json` holds the end
timestamp of every word, from MMS_FA forced alignment against the KNOWN text.
Audio after the last word's end is, by construction, audio that no word in the
verse accounts for. No ASR, no model, no heuristic about what a word sounds
like - and it cannot recite anything from memory, because it is only ever asked
where the text it was given actually lands.

⚠ LIMITS, so nobody over-trusts this:
  . A verse with no `.w.json` (unaligned, or alignment returned null) CANNOT be
    judged and is counted separately - never as clean.
  . MMS_FA can end the last word early on a trailing fricative or a long vowel,
    so TAIL_MIN_MS is deliberately generous. Tune it down and false positives
    appear; the flagged clips are meant for an ear, not for an automatic delete.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

NARRATION = r"C:\Projects\Hexapla-releases\narration"
ASSETS = r"C:\Projects\Hexapla\app\src\main\assets\bibles"
SILENCE_MS = 600
TAIL_MIN_MS = 140          # shorter than this is alignment slack, not a word
TAIL_LEVEL_DB = -28        # relative to the verse's own 90th-percentile level
NOTE = re.compile(r"\{[^{}]*:[^{}]*\}")

ASSET = {"tyn": "en_tyndale.json", "sv": "sv_karlxii.json", "ylt": "en_ylt.json",
         "wbt": "en_webster.json", "gnv": "en_geneva.json",
         "wyc": "enm_wycliffe.json", "en": "en_kjv.json"}

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def chapter_audio(ogg, sr=16000):
    with tempfile.TemporaryDirectory() as td:
        w = os.path.join(td, "t.wav")
        if subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", ogg,
                           "-ac", "1", "-ar", str(sr), w],
                          capture_output=True).returncode:
            return None
        x, _ = sf.read(w)
    return x


def speech_after(a, sr, from_ms, to_ms):
    """Longest run of speech-level audio in (from_ms, to_ms), in ms."""
    s, e = int(from_ms / 1000 * sr), int(to_ms / 1000 * sr)
    if e - s < int(0.06 * sr) or s < 0 or e > len(a):
        return 0.0
    ref = np.percentile(np.abs(a[:e]), 90) + 1e-9
    seg = a[s:e]
    h = int(0.02 * sr)
    nw = len(seg) // h
    if nw < 3:
        return 0.0
    db = 20 * np.log10(np.sqrt((seg[:nw * h].reshape(nw, h) ** 2).mean(1)) + 1e-9)
    loud = db > (20 * np.log10(ref) + TAIL_LEVEL_DB)
    best = cur = 0
    for v in loud:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best * 20.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--book", type=int)
    ap.add_argument("--sample", type=int, default=0, help="0 = every chapter")
    ap.add_argument("--clips", action="store_true",
                    help="write flagged verses to tail_<set>.wav for an ear")
    args = ap.parse_args()

    books = json.loads(open(os.path.join(ASSETS, ASSET[args.set]),
                            encoding="utf-8").read())
    books = books["books"] if isinstance(books, dict) else books
    pat = (os.path.join(NARRATION, args.set, str(args.book), "*.json")
           if args.book is not None
           else os.path.join(NARRATION, args.set, "*", "*.json"))
    files = [f for f in sorted(glob.glob(pat))
             if not f.endswith((".w.json", ".eos.json")) and ".bak" not in f]
    if args.sample and len(files) > args.sample:
        step = len(files) / args.sample
        files = [files[int(i * step)] for i in range(args.sample)]

    flagged = judged = unjudgeable = 0
    clips = []
    for f in files:
        ogg, wj = f[:-5] + ".ogg", f[:-5] + ".w.json"
        if not os.path.exists(ogg):
            continue
        b = int(os.path.basename(os.path.dirname(f)))
        c = int(os.path.basename(f)[:-5])
        off = json.loads(open(f).read())["offsets"]
        vs = books[b]["chapters"][c]
        if len(off) != len(vs):
            continue
        if not os.path.exists(wj):
            unjudgeable += len(vs)
            continue
        words = json.loads(open(wj).read())["v"]
        a = chapter_audio(ogg)
        if a is None:
            continue
        sr = 16000
        total_ms = len(a) / sr * 1000
        for i in range(len(off)):
            txt = NOTE.sub("", vs[i] or "").strip()
            if len(txt) < 20:
                continue
            w = words[i] if i < len(words) else None
            if not w:
                unjudgeable += 1
                continue
            judged += 1
            # ⚠ INDEX 1, NOT 3. A word is [startMs, endMs, charStart, charEnd];
            # taking x[3] reads a CHARACTER offset as a millisecond timestamp,
            # which put every "last word" at ~20 ms and duly flagged 100% of
            # Tyndale Genesis with a suspiciously uniform 2.2 s tail. A result
            # that clean is a bug, not a discovery.
            last_end = max(x[1] for x in w)
            v_end = (off[i + 1] - SILENCE_MS) if i + 1 < len(off) else total_ms
            run = speech_after(a, sr, last_end + 40, v_end)
            if run >= TAIL_MIN_MS:
                flagged += 1
                print(f"  {b}/{c} v{i+1}: {run:.0f} ms of speech after the last "
                      f"word  | ...{txt[-52:]}")
                if args.clips and len(clips) < 8:
                    s0 = int(max(0, last_end - 2500) / 1000 * sr)
                    s1 = int(min(v_end + 150, total_ms) / 1000 * sr)
                    seg = a[s0:s1]
                    clips += [seg / max(np.abs(seg).max(), 1e-9) * 0.7,
                              np.zeros(int(1.0 * sr))]

    if args.clips and clips:
        sf.write(f"tail_{args.set}.wav", np.concatenate(clips), 16000,
                 subtype="PCM_16")
        print(f"\n  wrote tail_{args.set}.wav")
    pct = 100 * flagged / judged if judged else 0
    print(f"\n  {judged} verses judged, {flagged} with audio after the last word "
          f"({pct:.1f}%), {unjudgeable} could not be judged (no word timings)")
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
