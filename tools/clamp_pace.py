# -*- coding: utf-8 -*-
"""Clamp per-verse speaking-rate outliers in a rendered chapter.

WHY: narrate.py synthesizes each verse as an INDEPENDENT CosyVoice call, and
the model generates fresh prosody every time. Nothing ties verse N's pace to
verse N-1's. Measured on Obadiah (solemn, 2026-07-15): mean 8.89 chars/sec but
a 2.57x spread — verse 6 at 5.66 ch/s against verse 11 at 14.52, the latter
faster than the NORMAL style's average. The owner heard this as "a lot of
different variants, different speeds".

APPROACH: clamp, do not flatten. Verses outside a tolerance band around the
chapter median get time-stretched into it; verses inside are left untouched.
Forcing every verse to an identical rate would sound just as wrong in the other
direction — real narrators vary, they just do not lurch.

Stretching uses ffmpeg atempo, which preserves pitch. Ratios are capped
(MAX_STRETCH) because atempo degrades audibly past roughly +/-35%; a verse
needing more than that is left alone and reported, since a mangled verse is
worse than a fast one.

Rebuilds the offsets JSON to match the new durations.

    python tools/clamp_pace.py --lang ru --book 30 --chapter 0
    python tools/clamp_pace.py --lang ru --book 30 --chapter 0 --dry-run
"""
import argparse
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
# narrate re-wraps sys.stdout on import; wrapping it here too closes the first
# wrapper's buffer and every later print() dies with "I/O operation on closed
# file". Let narrate own it.
import narrate  # noqa: E402

OUTPUT = narrate.OUTPUT
SILENCE_MS = 600

# Verses whose rate is outside [median/TOL, median*TOL] get pulled to the edge
# of the band. 1.15 keeps natural variation while removing lurches.
TOL = 1.15
MAX_STRETCH = 1.35   # atempo ratio ceiling; beyond this it sounds processed
MIN_CHARS = 20       # too short to measure a rate reliably


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace")[-400:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = narrate.LANG_CONFIG[args.lang]
    d = OUTPUT / args.lang / str(args.book)
    ogg, jsn = d / f"{args.chapter}.ogg", d / f"{args.chapter}.json"
    if not ogg.exists():
        sys.exit(f"not rendered: {ogg}")

    offsets = json.load(open(jsn))["offsets"]
    books = narrate.load_bible(args.lang)
    raw = books[args.book]["chapters"][args.chapter]
    texts = []
    for v in raw:
        if not v:
            texts.append("")
            continue
        t = narrate.strip_kjv_notes(v) if cfg["strip_notes"] else v
        texts.append(narrate.normalize_text(t, cfg["normalizer"]))

    total_ms = int(float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(ogg)],
        capture_output=True, text=True).stdout.strip()) * 1000)

    # Verse i spans [offsets[i], offsets[i+1] - gap); the last runs to the end.
    spans = []
    for i, off in enumerate(offsets):
        end = (offsets[i + 1] - SILENCE_MS) if i + 1 < len(offsets) else total_ms
        spans.append((off, max(end, off)))

    rates = [len(texts[i]) / ((e - s) / 1000)
             for i, (s, e) in enumerate(spans)
             if len(texts[i]) >= MIN_CHARS and e > s]
    if not rates:
        sys.exit("no measurable verses")
    median = statistics.median(rates)
    lo, hi = median / TOL, median * TOL

    print(f"{args.lang} book {args.book} ch {args.chapter}: "
          f"{len(rates)} measurable verses")
    print(f"  median {median:.2f} ch/s | band {lo:.2f}-{hi:.2f} "
          f"| spread {max(rates)/min(rates):.2f}x | CV {statistics.pstdev(rates)/median:.1%}")

    plan, skipped = [], []
    for i, (s, e) in enumerate(spans):
        n = len(texts[i])
        if n < MIN_CHARS or e <= s:
            plan.append((i, s, e, 1.0))
            continue
        rate = n / ((e - s) / 1000)
        target = min(max(rate, lo), hi)
        tempo = target / rate          # <1 slows down, >1 speeds up
        if abs(tempo - 1.0) < 0.02:
            plan.append((i, s, e, 1.0))
            continue
        if not (1 / MAX_STRETCH <= tempo <= MAX_STRETCH):
            skipped.append((i + 1, rate, tempo))
            plan.append((i, s, e, 1.0))
            continue
        plan.append((i, s, e, tempo))

    touched = [p for p in plan if p[3] != 1.0]
    print(f"  clamping {len(touched)} verse(s); leaving {len(plan)-len(touched)} untouched")
    for i, s, e, t in touched:
        rate = len(texts[i]) / ((e - s) / 1000)
        print(f"    verse {i+1:>3}: {rate:5.2f} ch/s  x{t:.3f} -> {rate*t:5.2f}")
    for v, rate, tempo in skipped:
        print(f"    verse {v:>3}: {rate:5.2f} ch/s needs x{tempo:.2f} — BEYOND "
              f"{MAX_STRETCH}x, left alone (stretching it would sound worse)")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return
    if not touched:
        print("\nnothing to do")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        parts, new_offsets, cum = [], [], 0
        for i, s, e, tempo in plan:
            new_offsets.append(cum)
            if e <= s:
                continue
            seg = tmp / f"v{i:04d}.wav"
            # Input-seek (-ss before -i) + explicit duration (-t). Using -ss/-to
            # as OUTPUT options is ambiguous about which timeline -to counts on
            # and silently produced a 0-frame file for the final verse.
            cmd = ["ffmpeg", "-y", "-ss", f"{s/1000:.3f}", "-i", str(ogg),
                   "-t", f"{(e-s)/1000:.3f}"]
            if tempo != 1.0:
                cmd += ["-filter:a", f"atempo={tempo:.4f}"]
            cmd += ["-ar", "24000", "-ac", "1", str(seg)]
            run(cmd)
            dur = narrate.get_wav_duration_ms(seg)
            parts.append(seg)
            cum += dur
            if i + 1 < len(plan):
                sil = tmp / f"s{i:04d}.wav"
                narrate.make_silence_wav(sil, SILENCE_MS, 24000)
                parts.append(sil)
                cum += SILENCE_MS

        lst = tmp / "concat.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        joined = tmp / "chapter.wav"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", str(joined)])

        out_ogg = d / f"{args.chapter}.clamped.ogg"
        if not narrate.loudnorm_and_encode(str(joined), str(out_ogg)):
            sys.exit("encode failed")
        json.dump({"offsets": new_offsets},
                  open(d / f"{args.chapter}.clamped.json", "w", encoding="utf-8"),
                  separators=(",", ":"))

    new_rates = [len(texts[i]) / ((new_offsets[i+1] - new_offsets[i] - SILENCE_MS) / 1000)
                 for i in range(len(new_offsets) - 1)
                 if len(texts[i]) >= MIN_CHARS
                 and new_offsets[i+1] - new_offsets[i] - SILENCE_MS > 0]
    print(f"\n  wrote {out_ogg.name}")
    print(f"  spread {max(rates)/min(rates):.2f}x -> {max(new_rates)/min(new_rates):.2f}x")
    print(f"  CV     {statistics.pstdev(rates)/median:.1%} -> "
          f"{statistics.pstdev(new_rates)/statistics.median(new_rates):.1%}")


if __name__ == "__main__":
    main()
