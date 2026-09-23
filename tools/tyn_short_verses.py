"""Find verses whose AUDIO IS TOO SHORT FOR THEIR TEXT - i.e. truncated renders.

WHY THIS EXISTS
---------------
Chatterbox (and any TTS with a forced end-of-sequence) can stop mid-verse. The
resulting clip is SHORTER than the text requires, so the defect REPLACES
content rather than adding to it - which is why chapter-level size or duration
heuristics never see it: the chapter as a whole looks normal.

It surfaced on 2026-08-20 as an alignment CRASH, not as bad audio:

    RuntimeError: forced_align_impl ... targets length is too long for CTC.
    Found log_probs length: 114, targets length: 124

MMS_FA emits one frame per 20 ms, so 114 frames = 2.28 s of audio carrying 124
characters of text - about 54 chars/s against real speech of roughly 15. That
verse (tyn 42/15 v33) was truncated. align_words.py now degrades such a verse
to a null instead of dying, but THE NULL IS A SYMPTOM: the listener still loses
the end of the verse. This script finds them so they can be RE-RENDERED.

⚠ `long_tail` in the .eos.json sidecars is NOT this defect - it fires on ~97% of
Tyndale verses and is deliberately ignored. `token_repetition` is the flag worth
acting on, and it is reported here alongside the rate for cross-reference.

USAGE
    python tools/tyn_short_verses.py <set-dir> [--threshold CHARS_PER_SEC]
e.g.
    python tools/tyn_short_verses.py tyn
    python tools/tyn_short_verses.py wyc --threshold 28

Exits 1 if any verse is flagged, so a wrapper cannot print success over it.
"""
import argparse
import json
import os
import re
import subprocess
import sys

NARRATION = r"C:\Projects\Hexapla-releases\narration"
ASSETS = r"C:\Projects\Hexapla\app\src\main\assets\bibles"
SILENCE_MS = 600

# Same table align_words.py uses, kept minimal: set dir -> bible asset.
ASSET_FOR = {
    "tyn": "en_tyndale.json", "wyc": "enm_wycliffe.json", "en": "en_kjv.json",
    "wbt": "en_webster.json", "gnv": "en_geneva.json", "sv": "sv_karlxii.json",
    "ru": "ru_synodal.json", "cu": "cu_elizabeth.json",
    "ylt": "en_ylt.json",
}
MARGIN_NOTE = re.compile(r"\{[^{}]*:[^{}]*\}")


def duration_ms(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return -1.0          # (!) never 0.0 - a failed probe must not look like a real duration
    return float(r.stdout.strip()) * 1000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set_dir")
    ap.add_argument("--threshold", type=float, default=30.0,
                    help="chars/sec above which a verse is flagged (default 30, ~2x speech)")
    a = ap.parse_args()

    asset = ASSET_FOR.get(a.set_dir)
    if not asset:
        raise SystemExit("no bible asset mapped for set dir %r" % a.set_dir)
    books = json.load(open(os.path.join(ASSETS, asset), encoding="utf-8"))

    base = os.path.join(NARRATION, a.set_dir)
    flagged, checked, probe_fail = [], 0, 0
    for b in sorted(os.listdir(base), key=lambda x: int(x) if x.isdigit() else 10 ** 9):
        d = os.path.join(base, b)
        if not os.path.isdir(d) or not b.isdigit():
            continue
        bi = int(b)
        if bi >= len(books):
            continue
        chapters = books[bi]["chapters"]
        for f in sorted(os.listdir(d)):
            if not f.endswith(".ogg"):
                continue
            ci = int(f.split(".")[0])
            side = os.path.join(d, "%d.json" % ci)
            if not os.path.exists(side) or ci >= len(chapters):
                continue
            offsets = json.load(open(side, encoding="utf-8"))["offsets"]
            verses = chapters[ci]
            if len(offsets) != len(verses):
                continue
            total = duration_ms(os.path.join(d, f))
            if total < 0:
                probe_fail += 1
                continue
            eos = {}
            ep = os.path.join(d, "%d.eos.json" % ci)
            if os.path.exists(ep):
                eos = json.load(open(ep, encoding="utf-8"))
            for i, raw in enumerate(verses):
                text = MARGIN_NOTE.sub("", raw)
                n = len(re.sub(r"\s+", " ", text).strip())
                start = offsets[i]
                end = (offsets[i + 1] - SILENCE_MS) if i + 1 < len(offsets) else total
                span = (end - start) / 1000.0
                checked += 1
                if span <= 0 or n == 0:
                    continue
                rate = n / span
                if rate > a.threshold:
                    flags = eos.get(str(i), [])
                    flagged.append((bi, ci, i + 1, n, round(span, 2), round(rate, 1),
                                    "token_repetition" in flags))

    print("checked %d verses in set %r; probe failures %d" % (checked, a.set_dir, probe_fail))
    if probe_fail:
        print("  (!) %d chapters could not be probed - NOT counted as clean" % probe_fail)
    if not flagged:
        print("no verse exceeds %.0f chars/sec - nothing to re-render" % a.threshold)
        return 0
    flagged.sort(key=lambda r: -r[5])
    print("\n%d VERSE(S) FLAGGED (audio too short for text) - RE-RENDER THESE:" % len(flagged))
    print("  book ch verse  chars  secs  chars/s  token_repetition")
    for bi, ci, v, n, span, rate, tr in flagged:
        print("  %4d %3d %5d  %5d  %5.2f  %7.1f  %s" % (bi, ci, v, n, span, rate, "YES" if tr else "-"))
    print("\nRe-render with: python tools/narrate.py --lang %s --book <b> --chapter <c> --force"
          % a.set_dir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
