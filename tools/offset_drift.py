# -*- coding: utf-8 -*-
"""Do a chapter's SIDECAR OFFSETS actually match where the verses are?

    python tools/offset_drift.py wyc                 # sample the set
    python tools/offset_drift.py tyn --all           # every chapter
    python tools/offset_drift.py ylt --book 39

WHY THIS EXISTS (2026-08-21). narrate.py's repetition retry re-synthesized a
verse to the SAME path, so when every attempt stayed flagged the file on disk
was the last take while the recorded duration was the first take's.
concatenate_with_silence() accumulates the DURATIONS and concatenates the
FILES, never re-measuring - so from that verse on, every offset was wrong, and
the error ACCUMULATED down the chapter.

⚠ NOTHING ELSE CATCHES IT. The audio is complete, correctly ordered and passes
qa_narration.py, zero_duration_verses.py and tyn_short_verses.py. Only the
sidecar lies. In the app that is worse than a bad verse: verse highlighting and
word-level following drift away from the audio for the rest of the chapter, and
seek-to-verse lands in the wrong place.

HOW IT WORKS - and why it costs zero model tokens. The concat pipeline inserts
DIGITAL silence (exact zeroes, not room tone) between segments, so verse
boundaries are findable with a threshold no real recording can reach: frames
below -90 dBFS. Verse i begins immediately after gap i. Compare that against
the sidecar and print the drift.

⚠ A chapter whose gap count does not match its verse count is NOT judged - it
is reported as UNCHECKABLE. A wrong comparison is worse than no comparison.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

NARRATION = r"C:\Projects\Hexapla-releases\narration"
# ⚠ MEASURE THE SPREAD, NOT THE MAXIMUM. Every chapter carries a small CONSTANT
# offset (~0.25 s) between the end of the digital silence and the first audible
# sample, because _trim_and_fade leaves a short fade-in on each segment. That is
# calibration, not a defect, and scoring the raw maximum flagged 19 of 40 clean
# wyc chapters at 0.25-0.28 s - a false alarm on a set that had just finished
# uploading. The bug ACCUMULATES, so what identifies it is the spread between
# the smallest and largest per-verse delta within one chapter.
TOL_S = 0.35

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def boundaries(ogg):
    """Start time (s) of each segment, from the digital-silence gaps."""
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "t.wav")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", ogg,
                            "-ac", "1", "-ar", "16000", wav],
                           capture_output=True)
        if r.returncode != 0:
            return None
        x, sr = sf.read(wav)
    h = int(0.02 * sr)
    nw = len(x) // h
    if nw < 10:
        return None
    db = 20 * np.log10(np.sqrt((x[:nw * h].reshape(nw, h) ** 2).mean(1)) + 1e-9)
    quiet = db < -90
    runs, s = [], None
    for i, v in enumerate(quiet):
        if v and s is None:
            s = i
        if not v and s is not None:
            runs.append((s * 0.02, i * 0.02))
            s = None
    if s is not None:
        runs.append((s * 0.02, nw * 0.02))
    gaps = [g for g in runs if g[1] - g[0] > 0.35]
    # ⚠⚠ A SILENCE RUN THAT ENDS AT EOF IS NOT A BOUNDARY - nothing follows it.
    # It is the trailing padding the concat pipeline leaves. Counting it adds one
    # phantom segment, so every chapter comes out as `gaps = verses + 1` and is
    # rejected as UNCHECKABLE. Measured on ylt 2026-09-02: that was EVERY chapter
    # in the set, i.e. the whole 1,189-chapter render was unauditable and the
    # tool reported it as "0 checked" rather than as a failure.
    # ▶ Dropping it cannot corrupt a good comparison: a set with no trailing
    # silence has no such gap, and a set with one was already UNCHECKABLE.
    total = nw * 0.02
    if gaps and abs(gaps[-1][1] - total) < 0.05:
        gaps = gaps[:-1]
    return [0.0] + [b for _, b in gaps]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--book", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--sample", type=int, default=40)
    args = ap.parse_args()

    root = os.path.join(NARRATION, args.set)
    pat = (os.path.join(root, str(args.book), "*.json") if args.book
           else os.path.join(root, "*", "*.json"))
    files = [f for f in sorted(glob.glob(pat))
             if not f.endswith((".w.json", ".eos.json"))]
    if not args.all and not args.book and len(files) > args.sample:
        step = len(files) / args.sample
        files = [files[int(i * step)] for i in range(args.sample)]

    checked = drifted = uncheckable = 0
    for f in files:
        ogg = f[:-5] + ".ogg"
        if not os.path.exists(ogg):
            continue
        try:
            off = json.load(open(f))["offsets"]
        except Exception:
            continue
        starts = boundaries(ogg)
        rel = os.path.relpath(f, root).replace("\\", "/")[:-5]
        if starts is None:
            print(f"  {rel}: could not decode - UNCHECKABLE")
            uncheckable += 1
            continue
        # starts[0] is the header; verse i begins after gap i.
        # ⚠⚠ THE COUNT MUST MATCH EXACTLY, NOT MERELY BE SUFFICIENT. An earlier
        # version rejected too FEW gaps and silently accepted too MANY - and an
        # extra gap maps verse i to the wrong boundary from that point on, so
        # the "drift" is invented and a repair built on it CORRUPTS a chapter
        # that was fine. wyc 66/4 (73 verses, 74 gaps) is the case that exposed
        # it: it reported 32.91 s of drift that does not exist.
        if len(starts) - 1 != len(off):
            print(f"  {rel}: {len(starts)-1} gaps for {len(off)} verses "
                  f"- UNCHECKABLE (empty verses or a merged gap)")
            uncheckable += 1
            continue
        checked += 1
        deltas = [off[i] / 1000 - starts[i + 1] for i in range(len(off))]
        spread = max(deltas) - min(deltas)
        if spread > TOL_S:
            drifted += 1
            print(f"  {rel}: DRIFT SPREAD {spread:.2f}s "
                  f"(delta {min(deltas):+.2f} -> {max(deltas):+.2f})")

    print(f"\n  {checked} chapters checked, {drifted} with drift > {TOL_S}s, "
          f"{uncheckable} uncheckable")
    sys.exit(1 if drifted else 0)


if __name__ == "__main__":
    main()
