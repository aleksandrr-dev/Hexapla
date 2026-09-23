# -*- coding: utf-8 -*-
"""Rebuild chapters whose audio ends abruptly, re-synthesizing only the bad parts.

THE DEFECT. `_trim_and_fade` was called only in synthesize_chatterbox; the
cosyvoice3 path never called it (fixed 2026-08-05). A verse CosyVoice ended
abruptly was therefore spliced onto 600 ms of digital silence at full
amplitude. Sometimes only the fade is missing (a click); sometimes CosyVoice
stopped early and words are GONE. The owner heard it in Numbers 1: the title,
and verses 8, 17, 25, 28, 34. ASR confirmed the title («ЧИСЛО, ГЛАВАЙП» for
«Числа, Глава первая»), v8 (lost «Цуара») and v54 (lost «и сделали»).

Set-wide: 1,077 verses (3.44%) across 801 of 1,192 chapters, plus chapter
ANNOUNCEMENTS failing at ~8% — worse than verses, and invisible to the first
scan, which only walked verse offsets. Announcements are part index 0 here.

⚠ WHY NOT `ffmpeg concat -c copy`. Splicing Opus losslessly at packet
boundaries LOOKS ideal and was tried first: it produced a single stream with
NON-MONOTONIC TIMESTAMPS at every splice. libsndfile refuses the result, and
the app SEEKS to verse offsets — so it would likely have broken seek-to-verse
on exactly the chapters it repaired. Decode, splice in PCM, encode once.

⚠ BITRATE. The originals are Opus 32 kbps. Re-encoding is a second lossy
generation, so repaired chapters go out at 48 kbps to keep it near-transparent
(owner's call 2026-08-05). Mixed bitrates across the set are fine — each
chapter is an independent file.

⚠ OFFSETS MOVE, DELIBERATELY. An earlier version padded replacements to the
exact span they replaced so the index shipped in the APK stayed valid. That
forced tempo-nudging fresh audio to fit, because CosyVoice re-renders a verse
at a different length every time (Numbers 1 v1 came back 10,391 ms against a
10,200 ms span). The owner chose cleaner audio instead: durations change, this
writes a corrected sidecar, and audio_index_gen.json is rebuilt for 1.6.4.

    python tools/repair_abrupt_verses.py --chapter 3/0 --dry-run
    python tools/repair_abrupt_verses.py --all
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import soundfile as sf

import narrate

NARR = Path("C:/Projects/Hexapla-releases/narration/ru")
FLAGS = Path("C:/Projects/Hexapla-releases/narration/logs/abrupt_endings_ru.json")
BACKUP = Path("C:/Projects/Hexapla-releases/narration/ru_prerepair")
GAP_MS = 600
BITRATE = "48k"
NO_WINDOW = getattr(narrate, "_NO_WINDOW", 0)


def tail_ratio(a, sr, ms=40):
    """RMS of the last `ms` over the whole part's RMS — the truncation signal.

    A part that ends naturally decays to near-silence. A part CosyVoice cut
    short ends at speaking level; even after _trim_and_fade turns that into a
    45 ms ramp, the ratio stays around 0.5-0.6, because the RMS of a linear
    ramp from A to 0 is about 0.58A. So this still separates "truncated then
    faded" from "ended properly" AFTER the fade is applied.
    """
    if len(a) < sr // 10:
        return 0.0
    t = a[-int(sr * ms / 1000):]
    return float(np.sqrt((t ** 2).mean()) / (np.sqrt((a ** 2).mean()) + 1e-9))


def synth(text, book_idx, cfg, tmp, tag, tries=5):
    """Synthesize one part, re-rolling until it does not end abruptly.

    ⚠ THIS LOOP IS THE POINT. CosyVoice truncates stochastically, not
    deterministically: the same verse measured 4,525 / 5,741 / 4,592 / 6,039 ms
    across four runs. An earlier version of this tool synthesized once and
    reproduced the very truncation it was repairing — Numbers 1's title came
    back as «Число. Глава…» and v54 as «…так они» a second time. Adding a
    trailing token does not help (tested); re-rolling does, because a clean
    draw is simply likely rather than guaranteed. Keep the best attempt so a
    part that never comes out clean still improves rather than failing.
    """
    best = None
    for k in range(tries):
        wav = Path(tmp) / f"{tag}_{k}.wav"
        if not narrate.synthesize_cosyvoice3(text, cfg, book_idx, wav):
            continue
        a, sr = sf.read(str(wav), dtype="float32")
        a = a.mean(1) if a.ndim > 1 else a
        r = tail_ratio(a, sr)
        if best is None or r < best[2]:
            best = (a, sr, r)
        if r <= 0.35:
            break
    if best is None:
        return None, None, None
    return best[0], best[1], best[2]


def repair_chapter(book, ch, targets, cfg, bible, dry):
    src = NARR / str(book) / f"{ch}.ogg"
    side = NARR / str(book) / f"{ch}.json"
    offsets = json.loads(side.read_text(encoding="utf-8"))["offsets"]
    verses = bible[book]["chapters"][ch]

    audio, sr = sf.read(str(src), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(1)
    total_ms = len(audio) / sr * 1000

    def cut(a_ms, b_ms):
        return audio[int(a_ms / 1000 * sr):int(b_ms / 1000 * sr)]

    # Split the chapter into its parts: announcement, then every verse.
    parts = [cut(0, offsets[0] - GAP_MS)]
    for i in range(len(offsets)):
        end = (offsets[i + 1] - GAP_MS) if i + 1 < len(offsets) else total_ms
        parts.append(cut(offsets[i], end))

    # Level to match: the chapter's own median part RMS. The original went
    # through two-pass loudnorm as a WHOLE; normalising one verse on its own
    # would land elsewhere and the repair would be audible as a jump.
    rms = float(np.median([np.sqrt((p ** 2).mean()) for p in parts
                           if len(p) > sr // 10]))

    if dry:
        for t in sorted(targets):
            what = "ANNOUNCEMENT" if t == 0 else f"verse {t}"
            print(f"    {what}: {len(parts[t]) / sr * 1000:.0f} ms")
        return True, "dry run", None

    with tempfile.TemporaryDirectory() as tmp:
        for t in sorted(targets):
            if t == 0:
                text = narrate.chapter_header_text(
                    "ru", book, ch, len(bible[book]["chapters"]))
            else:
                text = verses[t - 1]
            new, nsr, ratio = synth(text, book, cfg, tmp, f"p{t}")
            if new is None:
                return False, f"part {t}: synthesis failed", None
            if ratio > 0.45:
                print(f"       part {t}: still ends abruptly after retries "
                      f"(ratio {ratio:.2f}) — kept best attempt")
            # ⚠ THE CORPUS IS MIXED-RATE. Chapters exist at BOTH 24 kHz and
            # 48 kHz (364 vs 296 in the first twenty books) — different render
            # eras. CosyVoice emits 24 kHz, so a strict equality check rejected
            # every 48 kHz chapter: 210 of the first 492 skipped, 43%, and the
            # batch would have "finished" having silently left them defective.
            # Resample to the chapter's rate instead.
            if nsr != sr:
                from math import gcd
                g = gcd(int(nsr), int(sr))
                from scipy.signal import resample_poly
                new = resample_poly(new, int(sr) // g, int(nsr) // g).astype("float32")
            cur = float(np.sqrt((new ** 2).mean()))
            if cur > 1e-6:
                new = np.clip(new * (rms / cur), -1.0, 1.0)
            parts[t] = new

        gap = np.zeros(int(sr * GAP_MS / 1000), dtype="float32")
        out, new_offsets, pos = [], [], 0
        for i, p in enumerate(parts):
            if i:                  # verses carry an offset; the header does not
                new_offsets.append(round(pos / sr * 1000))
            out.append(p)
            pos += len(p)
            if i < len(parts) - 1:
                out.append(gap)
                pos += len(gap)
        merged = np.concatenate(out)

        wav = Path(tmp) / "chapter.wav"
        sf.write(str(wav), (merged * 32767).astype(np.int16), sr,
                 subtype="PCM_16")
        ogg = Path(tmp) / "chapter.ogg"
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(wav),
             "-b:a", BITRATE, "-c:a", "libopus", "-ac", "1", str(ogg)],
            capture_output=True, creationflags=NO_WINDOW)
        if r.returncode != 0:
            return False, "encode failed", None

        # Prove the result decodes BEFORE replacing anything. The `-c copy`
        # attempt produced a file ffprobe happily reported a duration for and
        # libsndfile rejected outright — an exit code is not evidence.
        try:
            chk, _ = sf.read(str(ogg), dtype="float32")
        except Exception as e:
            return False, f"result does not decode: {e}", None
        if len(chk) < len(merged) * 0.9:
            return False, "result is truncated", None

        (BACKUP / str(book)).mkdir(parents=True, exist_ok=True)
        for ext in ("ogg", "json"):
            f = NARR / str(book) / f"{ch}.{ext}"
            b = BACKUP / str(book) / f"{ch}.{ext}"
            if not b.exists():
                shutil.copy2(f, b)
        shutil.copy2(ogg, src)
        side.write_text(json.dumps({"offsets": new_offsets}), encoding="utf-8")
        delta = len(merged) / sr * 1000 - total_ms
        return True, f"ok ({len(targets)} parts, {delta:+.0f} ms)", new_offsets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--flags", help="alternate flag file (pass 2)")
    ap.add_argument("--force", action="store_true",
                    help="rebuild even if a backup already exists")
    args = ap.parse_args()

    flags = json.loads(Path(args.flags).read_text(encoding="utf-8")
                       if args.flags else FLAGS.read_text(encoding="utf-8"))
    keys = [args.chapter] if args.chapter else sorted(
        flags, key=lambda k: [int(x) for x in k.split("/")])
    if args.limit:
        keys = keys[:args.limit]

    cfg = narrate.LANG_CONFIG["ru"]
    bible = narrate.load_bible("ru")
    ok = fail = done = 0
    for k in keys:
        book, ch = (int(x) for x in k.split("/"))
        # Resume: a backup exists only for chapters already rebuilt, so this
        # makes the batch restartable without redoing hours of GPU work.
        if not args.force and (BACKUP / str(book) / f"{ch}.ogg").exists():
            done += 1
            continue
        ts = [h["verse"] for h in flags[k]]
        print(f"{k}: {len(ts)} part(s) {ts}", flush=True)
        good, msg, _ = repair_chapter(book, ch, ts, cfg, bible, args.dry_run)
        print(f"    -> {'OK' if good else 'SKIP'}: {msg}", flush=True)
        ok += good
        fail += not good
    print(f"\nrepaired {ok}, skipped {fail}")


if __name__ == "__main__":
    main()
