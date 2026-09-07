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
QUEUE = re.compile(r"^(\d+)\s+(\d+)\s+v?(\d+)\s*$")
GAP = 1.2          # seconds of silence between clips
PAD = 0.25         # seconds kept either side so the tail is audible

ASSETS = {
    "ylt": "C:/Projects/Hexapla/app/src/main/assets/bibles/en_ylt.json",
    "kjv": "C:/Projects/Hexapla/app/src/main/assets/bibles/en_kjv.json",
}


def verse_text_loader(lang):
    """Return f(b, ch, v) -> printed text, so the listener can compare.

    ⚠ The text is what the verse SHOULD say. It cannot clear a flag on its own
    (text cannot tell «the ASR misheard A» from «the TTS spoke B»); it is here
    so the ear has something to check the audio against.
    """
    import json
    path = ASSETS.get(lang)
    if not path or not Path(path).exists():
        return lambda b, ch, v: "(no text asset for this set)"
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) and "books" in data else data

    def get(b, ch, v):
        try:
            bk = books[b]
            chs = bk["chapters"] if isinstance(bk, dict) else bk
            return chs[ch][v - 1]
        except Exception:
            return "(verse not found in the text asset)"
    return get


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
    ap.add_argument("log", nargs="?",
                    help="an APPEND-format sweep log (omit when using --queue)")
    ap.add_argument("--lang", default="ylt")
    ap.add_argument("--out", default="_work/earcheck.ogg")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--only", help="restrict to these refs, e.g. '0/33 v2,1/4 v20'")
    ap.add_argument("--queue", help="a plain 'book chapter vN' queue "
                                    "(e.g. _work/ylt_EAR_QUEUE_*.txt). The index "
                                    "then prints the PRINTED TEXT of each verse, "
                                    "because a gate FAIL carries no single "
                                    "'appended words' claim to print.")
    a = ap.parse_args()
    if not a.log and not a.queue:
        sys.exit("give a sweep log, or --queue with a 'book chapter vN' file")

    wanted = None
    if a.only:
        wanted = set(x.strip() for x in a.only.split(","))

    flags = []
    if a.queue:
        text_of = verse_text_loader(a.lang)
        n_lines = 0
        for ln in io.open(a.queue, encoding="utf-8", errors="replace"):
            ln = ln.split("#")[0].strip()
            if not ln:
                continue
            n_lines += 1
            m = QUEUE.match(ln)
            if not m:
                sys.exit(f"queue line not understood: {ln!r}\n"
                         "  expected 'book chapter vN' (e.g. '0 12 v14')")
            b, ch, v = (int(x) for x in m.groups())
            ref = f"{b}/{ch} v{v}"
            if wanted and ref not in wanted:
                continue
            flags.append((b, ch, v, text_of(b, ch, v)))
        # ⛔ A named source that yields nothing must not look like an empty queue.
        if n_lines and not flags:
            sys.exit(f"{a.queue}: {n_lines} verse(s) read but none selected "
                     "(--only filtered them all out?)")
        if not n_lines:
            sys.exit(f"{a.queue}: no verse lines found")
    else:
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
    if a.limit and len(flags) > a.limit:
        print(f"⚠ {len(flags)} verses selected, --limit {a.limit} keeps the "
              f"first {a.limit}. Raise --limit to hear them all.")
    flags = flags[:a.limit] if a.limit else flags

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
    if a.queue:
        print("  #   verse        what the text PRINTS (the audio should match it)")
        for n, ref, txt, dur in index:
            print(f"  {n:<3} {ref:<12} {txt}")
        print("\n\u26a0 These verses FAIL the gate after repair and the printed "
              "text does not\n  explain the flag. Listen for a re-spoken tail, a "
              "wrong word, or a\n  mispronounced name. If the audio matches the "
              "text above, the flag is\n  the ASR's and the render is fine.")
    else:
        print("  #   verse        the ASR claims these words were APPENDED")
        for n, ref, added, dur in index:
            print(f"  {n:<3} {ref:<12} {added!r}")
        print("\n\u26a0 Listen for the appended words being SPOKEN at the end of "
              "the verse.\n  If you do not hear them, the flag is the ASR's and "
              "the render is fine.")


if __name__ == "__main__":
    main()
