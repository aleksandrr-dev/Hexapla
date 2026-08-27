# -*- coding: utf-8 -*-
"""Rewrite a chapter's verse offsets FROM ITS AUDIO, for chapters that drifted.

    python tools/repair_offsets.py tyn                 # DRY RUN (the default)
    python tools/repair_offsets.py tyn --apply
    python tools/repair_offsets.py wyc --apply

WHY A REPAIR AND NOT A RE-RENDER. The defect fixed in narrate.py on 2026-08-21
corrupted only the SIDECAR: the repetition retry re-synthesized a verse to the
same path, so a verse that stayed flagged through every attempt left the LAST
take on disk while `pairs` kept the FIRST take's duration.
concatenate_with_silence() concatenates the files and accumulates the durations,
so the audio is complete, correctly ordered and sounds right - only the numbers
describing it are wrong, and the error accumulates down the chapter.

Re-rendering would re-roll verses that are currently good, on a stochastic
engine, to fix numbers we can recompute exactly. This recomputes them.

HOW. The concat inserts DIGITAL silence - exact zeroes, not room tone - between
segments, so boundaries are findable with a threshold no real recording reaches
(-90 dBFS). Verse i starts immediately after gap i, which is the same definition
the original offsets used; on undrifted chapters the two agree to ~0.00 s, which
is what proves the definition matches.

⚠ SAFETY RULES, each of them load-bearing:
  . DRY RUN IS THE DEFAULT. --apply is required to write anything.
  . A chapter whose gap count does not match its verse count is SKIPPED, never
    guessed. A wrong offset table is worse than a drifted one, because it looks
    deliberate.
  . A chapter that does not drift is left ALONE - not rewritten with
    "equivalent" numbers.
  . Every sidecar is backed up to <ch>.json.bak-offsets before it is replaced.
  . The .w.json word sidecar of a repaired chapter is DELETED, because it was
    built on the wrong offsets. Re-run align_words.py afterwards to rebuild it.
    Deleting is right and leaving it is not: the app degrades a missing word
    sidecar to verse-level following, which is correct-but-coarser, while a
    stale one is confidently wrong.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

NARRATION = r"C:\Projects\Hexapla-releases\narration"
TOL_S = 0.35

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def boundaries(ogg):
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "t.wav")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", ogg,
                            "-ac", "1", "-ar", "16000", wav], capture_output=True)
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
            runs.append((s * 0.02, i * 0.02)); s = None
    if s is not None:
        runs.append((s * 0.02, nw * 0.02))
    gaps = [g for g in runs if g[1] - g[0] > 0.35]
    return [0.0] + [b for _, b in gaps]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--apply", action="store_true",
                    help="actually write; without it this only reports")
    ap.add_argument("--book", type=int)
    args = ap.parse_args()

    root = os.path.join(NARRATION, args.set)
    pat = (os.path.join(root, str(args.book), "*.json") if args.book
           else os.path.join(root, "*", "*.json"))
    files = [f for f in sorted(glob.glob(pat))
             if not f.endswith((".w.json", ".eos.json")) and ".bak" not in f]

    repaired = skipped = clean = 0
    for f in files:
        ogg = f[:-5] + ".ogg"
        if not os.path.exists(ogg):
            continue
        try:
            data = json.load(open(f))
            off = data["offsets"]
        except Exception:
            continue
        rel = os.path.relpath(f, root).replace("\\", "/")[:-5]
        starts = boundaries(ogg)
        # ⚠⚠ THE COUNT MUST MATCH EXACTLY, NOT MERELY BE SUFFICIENT. An earlier
        # version rejected too FEW gaps and silently accepted too MANY - and an
        # extra gap maps verse i to the wrong boundary from that point on, so
        # the "drift" is invented and a repair built on it CORRUPTS a chapter
        # that was fine. wyc 66/4 (73 verses, 74 gaps) is the case that exposed
        # it: it reported 32.91 s of drift that does not exist.
        if starts is None or len(starts) - 1 != len(off):
            print(f"  {rel}: SKIP - cannot align gaps to verses")
            skipped += 1
            continue
        deltas = [off[i] / 1000 - starts[i + 1] for i in range(len(off))]
        spread = max(deltas) - min(deltas)
        if spread <= TOL_S:
            clean += 1
            continue

        new = [int(round(starts[i + 1] * 1000)) for i in range(len(off))]
        print(f"  {rel}: spread {spread:.2f}s -> repairing "
              f"({len(off)} verses; worst move "
              f"{max(abs(a - b) for a, b in zip(off, new)) / 1000:.2f}s)")
        repaired += 1
        if not args.apply:
            continue

        shutil.copy2(f, f + ".bak-offsets")
        data["offsets"] = new
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(data, fh, separators=(",", ":"))
        w = f[:-5] + ".w.json"
        if os.path.exists(w):
            os.remove(w)

    mode = "REPAIRED" if args.apply else "would repair (DRY RUN)"
    print(f"\n  {mode}: {repaired}   already clean: {clean}   skipped: {skipped}")
    if repaired and args.apply:
        print(f"  ▶ Word sidecars deleted for those chapters. Rebuild with:")
        print(f"      python tools/align_words.py --set <align-name> --force")


if __name__ == "__main__":
    main()
