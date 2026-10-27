# -*- coding: utf-8 -*-
"""Screen a narration set for UNTIMED TAILS: audio after a verse's last aligned
word and before the next verse's offset (or the chapter end).

Why: tyn Matthew 1:6 (owner, by ear, 2026-10-05) carried «So try» after
«...the wyfe of Vry:». The aligner timed «Vry» and then nothing, so every
alignment-based screen saw a clean verse; the extra words sat in a 1.66 s gap
the screens never measure. A normal verse-end pause is well under that.

    python tools/tail_gap_screen.py --dir narration/tyn [--ms 1200] [--top 30]
    # known-bad control (must flag 39/0 v6):
    python tools/tail_gap_screen.py --dir narration/tyn_qa_fail_originals

Gap = next verse offset - last word end; for the last verse, chapter duration
(ffprobe) - last word end, reported separately because the chapter tail holds
the end pad. A verse with no timed words is reported as UNTIMED (a separate,
worse class). A chapter with no .w.json is counted and reported - a check that
could not run did not pass. rc 1 if anything flags, 2 if any chapter could not
be screened.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys


def duration_ms(ogg):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", ogg],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return int(float(out) * 1000)
    except Exception:
        return -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--ms", type=int, default=1200, help="flag a mid-chapter gap above this")
    ap.add_argument("--tail-ms", type=int, default=0,
                    help="flag a last-verse gap above this (default: --ms + the set's median end pad)")
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()

    mids, lasts, untimed, unscreened = [], [], [], []
    chapters = 0
    for b in sorted(os.listdir(a.dir), key=lambda s: (not s.isdigit(), int(s) if s.isdigit() else s)):
        bd = os.path.join(a.dir, b)
        if not os.path.isdir(bd):
            continue
        for f in sorted(os.listdir(bd)):
            if not f.endswith(".json") or f.count(".") != 1:
                continue
            c = f[:-5]
            sidecar = os.path.join(bd, f)
            wj = os.path.join(bd, c + ".w.json")
            ogg = os.path.join(bd, c + ".ogg")
            if not os.path.exists(ogg):
                continue
            chapters += 1
            try:
                offs = json.load(open(sidecar, encoding="utf-8"))["offsets"]
                words = json.load(open(wj, encoding="utf-8"))["v"]
            except Exception as e:
                unscreened.append(f"{b}/{c}: {type(e).__name__}")
                continue
            if len(words) != len(offs):
                unscreened.append(f"{b}/{c}: {len(words)} word lists vs {len(offs)} offsets")
                continue
            for i, w in enumerate(words):
                if not w:
                    untimed.append(f"{b}/{c} v{i+1}")
                    continue
                end = w[-1][1]
                if i + 1 < len(offs):
                    mids.append((offs[i + 1] - end, f"{b}/{c} v{i+1}"))
                else:
                    d = duration_ms(ogg)
                    if d < 0:
                        unscreened.append(f"{b}/{c}: ffprobe failed")
                    else:
                        lasts.append((d - end, f"{b}/{c} v{i+1}"))

    print(f"{a.dir}: {chapters} chapters, {len(mids)} mid gaps, {len(lasts)} last-verse gaps")
    if mids:
        g = sorted(x[0] for x in mids)
        print(f"  mid gap ms: median {statistics.median(g):.0f}  p95 {g[int(len(g)*.95)]}  p99 {g[int(len(g)*.99)]}  max {g[-1]}")
    tail_ms = a.tail_ms
    if lasts:
        g = sorted(x[0] for x in lasts)
        med = statistics.median(g)
        print(f"  last gap ms: median {med:.0f}  p95 {g[int(len(g)*.95)]}  max {g[-1]}")
        if not tail_ms:
            tail_ms = int(a.ms + med)
    flag_mid = sorted((x for x in mids if x[0] > a.ms), reverse=True)
    flag_last = sorted((x for x in lasts if x[0] > tail_ms), reverse=True)
    print(f"\nMID gaps > {a.ms} ms: {len(flag_mid)}")
    for g, k in flag_mid[:a.top]:
        print(f"  {g:6d}  {k}")
    print(f"LAST-verse gaps > {tail_ms} ms: {len(flag_last)}")
    for g, k in flag_last[:a.top]:
        print(f"  {g:6d}  {k}")
    print(f"UNTIMED verses: {len(untimed)}  {' '.join(untimed[:a.top])}")
    print(f"UNSCREENED chapters: {len(unscreened)}")
    for u in unscreened[:a.top]:
        print("  " + u)
    if unscreened:
        return 2
    return 1 if (flag_mid or flag_last or untimed) else 0


if __name__ == "__main__":
    sys.exit(main())
