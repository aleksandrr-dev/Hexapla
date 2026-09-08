# -*- coding: utf-8 -*-
"""Cut a WORD as ALREADY RENDERED in several sets, for an ear. 0 GPU, 0 tokens.

    python tools/cross_set_word_clips.py --word seeth --word fleeth \
        --set en --set gnv --set wbt --set tyn --set wyc --out <dir>

## Why this exists

`pronounce_lexicon.py` is hard-gated to ylt in `narrate.py`
(`if ... and lang == "ylt"`). So a defect the owner heard in ylt says NOTHING
about the other English sets — they were rendered with **no respelling at all**,
and three of them run a DIFFERENT ENGINE (kokoro) whose frontend converts
letters to phonemes its own way.

⛔⛔ A RESPELLING IS A HYPOTHESIS ABOUT ONE ENGINE READING ONE STRING. It does
not transfer across engines, and the project has already recorded that it does
not reliably transfer across a ROOT and its own derived form. So the first
question is never «which respelling do we copy over», it is **«is the word even
wrong in that set?»** — and that costs nothing to answer, because the audio
already exists on disk.

⚠ It reads the LIVE tree. A clip here is what that set ships today.
⚠ It reports the set's ENGINE beside every clip, because that is the variable
that decides whether an ylt remedy could ever apply.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DATA = Path(r"C:\Projects\Hexapla-releases")
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"


def set_map():
    """set -> (asset, engine), parsed from narrate.py's LANG_CONFIG."""
    src = (HERE / "narrate.py").read_text(encoding="utf-8")
    out, cur = {}, None
    for line in src[src.index("LANG_CONFIG = {"):].splitlines():
        k = re.match(r'^    "([a-z0-9_]+)": \{', line)
        if k:
            cur = k.group(1)
            out[cur] = [None, None]
        a = re.match(r'^        "asset": "([^"]+)"', line)
        if a and cur:
            out[cur][0] = a.group(1)
        e = re.match(r'^        "engine": "([^"]+)"', line)
        if e and cur:
            out[cur][1] = e.group(1)
    return {k: tuple(v) for k, v in out.items() if v[0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", action="append", required=True)
    ap.add_argument("--set", dest="sets", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=float, default=1.2,
                    help="seconds of lead-in before the word's verse")
    a = ap.parse_args()

    smap = set_map()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in a.sets:
        if s not in smap:
            print(f"⛔ unknown set {s}")
            return 2
        asset, engine = smap[s]
        books = json.loads((ASSETS / asset).read_text(encoding="utf-8"))
        nar = DATA / "narration" / s
        for w in a.word:
            found = None
            for bi, bk in enumerate(books):
                for ci, ch in enumerate(bk["chapters"]):
                    for vi, t in enumerate(ch, 1):
                        if not re.search(rf"\b{w}\b", t, re.I):
                            continue
                        ogg = nar / str(bi) / f"{ci}.ogg"
                        sc = nar / str(bi) / f"{ci}.json"
                        # ⛔ Only a verse whose audio EXISTS can be heard. A set
                        # that is partly rendered must not silently yield the
                        # first textual hit and a missing file.
                        if ogg.exists() and sc.exists():
                            found = (bi, ci, vi, bk["name"], t, ogg, sc)
                            break
                    if found:
                        break
                if found:
                    break
            if not found:
                rows.append((s, engine, w, None, "no rendered verse contains it"))
                continue
            bi, ci, vi, name, text, ogg, sc = found
            offs = json.loads(sc.read_text(encoding="utf-8"))["offsets"]
            if vi > len(offs):
                rows.append((s, engine, w, None, "verse beyond offsets"))
                continue
            start = max(0.0, offs[vi - 1] / 1000.0 - a.pad)
            end = (offs[vi] / 1000.0) if vi < len(offs) else None
            clip = out / f"{w}__{s}_{engine}.mp3"
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(ogg),
                   "-ss", f"{start:.3f}"]
            if end is not None:
                cmd += ["-to", f"{end:.3f}"]
            cmd += ["-c:a", "libmp3lame", "-q:a", "4", str(clip)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            ok = r.returncode == 0 and clip.exists()
            rows.append((s, engine, w, clip if ok else None,
                         f"{name} {ci+1}:{vi}" if ok else "ffmpeg failed"))

    print(f"{'set':<6} {'engine':<12} {'word':<8} where")
    for s, engine, w, clip, where in rows:
        print(f"{s:<6} {engine:<12} {w:<8} {where}"
              + (f"   -> {clip.name}" if clip else "   (no clip)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
