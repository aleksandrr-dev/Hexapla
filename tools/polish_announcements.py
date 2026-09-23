# -*- coding: utf-8 -*-
"""Remove trailing engine junk from built announcement clips. No GPU, no redraw.

WHY (owner, 2026-08-06: "50s are also cut off. You need to find a better way.
Why are they being cut off?"). They are not cut off — they have junk appended.
CosyVoice keeps generating past the end of a very short formulaic prompt and
emits a stray fragment after a pause; narrate.py's `_trim_and_fade` then chops
that fragment and fades it, which is heard as an abrupt ending. Proven with
whisper word timestamps: ch_52's last word ends at 1,000 ms in a 1,560 ms file,
with a fresh burst of energy after the gap.

So the repair is deterministic rather than another gamble: find where the words
actually end, cut in the silence just after, re-fade. Re-drawing could not fix
this reliably because the artifact is a property of how the model ends short
prompts, not a bad roll.

    python tools/polish_announcements.py --dry-run
    python tools/polish_announcements.py

⚠ ORIGINALS ARE ARCHIVED, NEVER DELETED — every clip this rewrites is first
moved to `superseded/<key>__N.wav`, same guarantee as a rebuild.

⚠ A CHANGE IS ONLY KEPT IF IT MEASURABLY HELPS: the tail score must improve,
the words must still transcribe, and at least 150 ms must be removed. Anything
else is left exactly as it was.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))

import build_announcements as ba

LIB = ba.LIB
MIN_TRIM_MS = 150


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="comma-separated keys")
    args = ap.parse_args()

    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)

    wanted = ba.component_texts()
    if args.only:
        keep = {k.strip() for k in args.only.split(",")}
        wanted = [(k, t) for k, t in wanted if k in keep]

    meta_path = LIB / "components.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    changed, skipped, worse = 0, 0, 0
    for key, text in wanted:
        f = LIB / f"{key}.wav"
        if not f.exists():
            continue
        a, sr = sf.read(str(f), dtype="float32")
        a = a.mean(1) if a.ndim > 1 else a
        before = float(ba.tail_energy(a, sr))
        if before <= 0.30:                    # already ends cleanly
            skipped += 1
            continue

        segs, _ = model.transcribe(str(f), language="ru", beam_size=5,
                                   word_timestamps=True,
                                   condition_on_previous_text=False,
                                   vad_filter=False)
        words = [w for s in segs for w in (s.words or [])]
        if not words:
            skipped += 1
            continue
        end_ms = words[-1].end * 1000
        out, did = ba.polish_tail(a, sr, end_ms)
        if not did:
            skipped += 1
            continue
        removed = (len(a) - len(out)) / sr * 1000
        after = float(ba.tail_energy(out, sr))
        # The polished clip must still say the words — cutting must not have
        # eaten the ending. Checked on the RESULT, not assumed from the cut.
        tmp = LIB / "_polish_check.wav"
        sf.write(str(tmp), (out * 32767).astype(np.int16), sr, subtype="PCM_16")
        heard = ba.asr(tmp)
        ok, ratio, tail = ba.words_present(text, heard)
        tmp.unlink(missing_ok=True)

        verdict = "keep" if (after < before and removed >= MIN_TRIM_MS and ok) else "reject"
        print(f"  {key:9} {text!r:32} cut {before:.2f}->{after:.2f} "
              f"removed {removed:4.0f}ms  {heard!r:28} {verdict}")
        if verdict != "keep":
            worse += 1
            continue
        if not args.dry_run:
            arch = LIB / "superseded"
            arch.mkdir(exist_ok=True)
            n_prev = len(list(arch.glob(f"{key}__*.wav")))
            f.replace(arch / f"{key}__{n_prev + 1}.wav")
            sf.write(str(f), (out * 32767).astype(np.int16), sr, subtype="PCM_16")
            m = meta.setdefault(key, {"text": text})
            m["polished_ms"] = round(removed)
            m["kept_ms"] = round(len(out) / sr * 1000)
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        changed += 1

    print(f"\n{changed} clips {'would be ' if args.dry_run else ''}polished, "
          f"{worse} rejected (no improvement), {skipped} already clean/no cut point")


if __name__ == "__main__":
    main()
