# -*- coding: utf-8 -*-
"""Cut flagged verses into ONE audio file so a human can ear-check them in a sitting.

    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\qa_asr_clips.py \\
        _work/qa_asr_ylt_full.log --lang ylt --out _work/ylt_earcheck.ogg

## Why

Every layer of this audit ends in the same sentence: *nothing is a defect until
someone listens.* That makes a human ear the bottleneck, and hunting for
`narration/ylt/0/33.ogg`, seeking to verse 2 and guessing where it ends is the
slow part - not the listening.

So this cuts each flagged verse out by its own offsets, joins them with a short
silence, and prints a numbered index. Ten candidates become two minutes.

## ⚠ IT INCLUDES CONTROLS ON PURPOSE

The list is not all suspects. It interleaves verses the duration cross-check
WEAKENED (`qa_asr_confirm.py` says there is no room for the extra audio) among
the CONFIRMED ones, and the printed index says which is which only AFTER the
listener has been told the order.

▶ **This is what validates the screen.** If the CONFIRMED clips audibly repeat
and the WEAKENED clips do not, the heuristic works and its output can be trusted
at scale. If they sound the same, the heuristic is measuring something else and
must not be used to queue 100+ re-renders. Run this on a small sample EARLY,
before the full sweep finishes - a screen nobody has validated is not evidence.
"""
import argparse
import io
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NARRATION = Path("C:/Projects/Hexapla-releases/narration")
HEAD = re.compile(r"^\s*APPEND \[(\d+)/(\d+)\] v(\d+) \+(.*)  ratio ([0-9.]+)\s*$")
GAP = 1.2          # seconds of silence between clips
PAD = 0.25         # seconds kept either side so the tail is audible


def verse_span(lang, b, ch, v):
    import json
    side = NARRATION / lang / str(b) / f"{ch}.json"
    ogg = NARRATION / lang / str(b) / f"{ch}.ogg"
    if not side.exists() or not ogg.exists():
        return None
    off = json.loads(side.read_text())["offsets"]
    i = v - 1
    if i >= len(off):
        return None
    start = off[i] / 1000
    if i + 1 < len(off):
        end = off[i + 1] / 1000
    else:
        import soundfile as sf
        end = sf.info(str(ogg)).duration
    return ogg, max(start - PAD, 0), end + PAD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--lang", default="ylt")
    ap.add_argument("--out", default="_work/earcheck.ogg")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--only", help="restrict to these refs, e.g. '0/33 v2,1/4 v20'")
    a = ap.parse_args()

    wanted = None
    if a.only:
        wanted = set(x.strip() for x in a.only.split(","))

    flags = []
    for ln in io.open(a.log, encoding="utf-8", errors="replace"):
        m = HEAD.match(ln)
        if not m:
            continue
        b, ch, v, added, _ = m.groups()
        ref = f"{b}/{ch} v{v}"
        if wanted and ref not in wanted:
            continue
        flags.append((int(b), int(ch), int(v), added.strip().strip("'\"")))
    if not flags:
        sys.exit("no matching APPEND flags in that log")
    flags = flags[:a.limit]

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        parts, index = [], []
        sil = Path(td) / "sil.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"anullsrc=r=24000:cl=mono", "-t", str(GAP),
                        str(sil)], check=True)
        for n, (b, ch, v, added) in enumerate(flags, 1):
            span = verse_span(a.lang, b, ch, v)
            if not span:
                print(f"  skip {b}/{ch} v{v}: no audio/offsets")
                continue
            ogg, s, e = span
            clip = Path(td) / f"c{n:02d}.wav"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(s),
                            "-to", str(e), "-i", str(ogg), "-ac", "1",
                            "-ar", "24000", str(clip)], check=True)
            parts += [clip, sil]
            index.append((n, f"{b}/{ch} v{v}", added, e - s))
        if not parts:
            sys.exit("nothing cut")
        lst = Path(td) / "list.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts),
                       encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe",
                        "0", "-i", str(lst), "-c:a", "libvorbis", "-q:a", "3",
                        str(out)], check=True)

    print(f"\n{out}  ({len(index)} clips, {sum(i[3] for i in index):.0f}s + gaps)\n")
    print("  #   verse        the ASR claims these words were APPENDED")
    for n, ref, added, dur in index:
        print(f"  {n:<3} {ref:<12} {added!r}")
    print("\n\u26a0 Listen for the appended words being SPOKEN at the end of the "
          "verse.\n  If you do not hear them, the flag is the ASR's and the "
          "render is fine.")


if __name__ == "__main__":
    main()
