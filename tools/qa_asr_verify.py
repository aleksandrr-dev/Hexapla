# -*- coding: utf-8 -*-
"""Transcribe rendered narration and diff it against the source verse text.

    tools\.kokoro_venv\Scripts\python.exe tools/qa_asr_verify.py --lang ylt --book 39 --chapter 4
    tools\.kokoro_venv\Scripts\python.exe tools/qa_asr_verify.py --lang ylt --book 39

WHY THIS EXISTS. qa_narration.py measures DURATION, rate and spread, and it
passed both ylt pilot chapters with clean numbers while the owner's ear caught
three hallucinated words in Matthew 5 alone:

    v1  "...his disciples came to him,"          -> spoken "...came to him, POLE, and"
    v7  "...they shall find kindness."           -> spoken "...kindness. NASS"
    v9  "...shall be called Sons of God."        -> spoken "...Sons of God. ACCORD"

A one-syllable insertion moves a 5-second verse by ~0.3 s. That is INSIDE the
natural spread of a read, so no duration heuristic can ever see it. Neither can
`_trim_and_fade`: the artifact it removes is a vocoder tail ~41 dB down, while
these are words at full speech level. The only thing that catches a wrong WORD
is reading the words back.

⚠⚠ THIS IS A SCREEN, NOT AN ORACLE. faster-whisper mis-hears archaic English on
its own - "age-during", "Jehovah", "doth", "-eth" endings, and Young's hyphenated
coinages all produce honest ASR errors against a perfectly good render. So this
tool RANKS and SHOWS; it never decides. Read the diff before believing it, and
treat a tail insertion after the final word (which is the defect we are hunting)
as far stronger evidence than a substitution mid-verse.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
OUTPUT = Path("C:/Projects/Hexapla-releases/narration")
NOTE = re.compile(r"\s*\{[^{}]*:[^{}]*\}")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def norm(s):
    """Fold both sides to comparable word tokens."""
    s = s.lower().replace("\u2014", " ").replace("\u2019", "'").replace("`", "")
    s = re.sub(r"[^a-z' ]+", " ", s)
    return [w for w in s.split() if w]


def verse_text(asset, book, chapter):
    d = json.loads((ASSETS / asset).read_text(encoding="utf-8"))
    books = d["books"] if isinstance(d, dict) else d
    return [NOTE.sub("", v).replace("{", "").replace("}", "")
            for v in books[book]["chapters"][chapter]]


def cut(ogg, start_ms, end_ms, dest):
    """Cut one verse, and TRIM THE TRAILING SILENCE.

    ⚠⚠ THE SILENCE IS NOT HARMLESS. The concat pipeline puts 600 ms of digital
    silence after every segment, and faster-whisper, handed a clip of famous
    text that ends in silence, INVENTS THE CONTINUATION. On the Matthew 5
    re-render it "heard" v31's opening at the end of v30, v32's at the end of
    v31, and so on for eleven consecutive verses - a perfect cascade that looked
    exactly like cumulative offset drift and was nothing but the model reciting
    the Sermon on the Mount from memory. The per-verse pace table showed every
    one of those verses at a healthy 14-20 ch/s, which is what proved it.
    Trimming the silence removes the invitation.
    """
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start_ms/1000:.3f}"]
    if end_ms is not None:
        cmd += ["-to", f"{end_ms/1000:.3f}"]
    cmd += ["-i", str(ogg), "-ac", "1", "-ar", "16000",
            "-af", "silenceremove=stop_periods=-1:stop_duration=0.25:"
                   "stop_threshold=-45dB", str(dest)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--quiet", action="store_true", help="only show flagged verses")
    args = ap.parse_args()

    sys.path.insert(0, str(HERE))
    import narrate
    cfg = narrate.LANG_CONFIG[args.lang]

    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    root = OUTPUT / args.lang / str(args.book)
    chapters = ([args.chapter] if args.chapter is not None
                else sorted(int(p.stem) for p in root.glob("*.ogg")))

    total = flagged = 0
    for ch in chapters:
        ogg = root / f"{ch}.ogg"
        side = root / f"{ch}.json"
        if not ogg.exists() or not side.exists():
            print(f"  [{args.book}/{ch}] missing ogg or offsets - SKIP")
            continue
        offsets = json.loads(side.read_text())["offsets"]
        texts = verse_text(cfg["asset"], args.book, ch)
        if len(offsets) != len(texts):
            # ⚠ Not cosmetic: a mismatch means the sidecar and the asset
            # disagree about what is in this file, and every diff below would
            # be against the wrong verse. Refuse rather than report nonsense.
            print(f"  [{args.book}/{ch}] OFFSETS {len(offsets)} != VERSES "
                  f"{len(texts)} - REFUSING to diff")
            continue

        with tempfile.TemporaryDirectory() as td:
            for i, start in enumerate(offsets):
                end = offsets[i + 1] if i + 1 < len(offsets) else None
                wav = Path(td) / f"v{i}.wav"
                cut(ogg, start, end, wav)
                segs, _ = model.transcribe(
                    str(wav), language="en", beam_size=5, vad_filter=False,
                    # Both of these exist to stop the model volunteering text
                    # it was not given audio for.
                    condition_on_previous_text=False,
                    hallucination_silence_threshold=0.5)
                heard = norm(" ".join(s.text for s in segs))
                want = norm(texts[i])
                total += 1
                sm = difflib.SequenceMatcher(None, want, heard)
                ratio = sm.ratio()
                # A TAIL insertion is the defect being hunted: extra words after
                # the last matching one. Score it separately from mid-verse
                # noise, which is usually the ASR's own archaic-English trouble.
                tail = []
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag in ("insert", "replace") and i2 >= len(want) - 1:
                        tail = heard[j1:j2]
                if tail or ratio < 0.90:
                    flagged += 1
                    print(f"  [{args.book}/{ch}] v{i+1}  match {ratio:.2f}"
                          + (f"   TAIL: {' '.join(tail)!r}" if tail else ""))
                    if not args.quiet:
                        print(f"        want:  {' '.join(want[-12:])}")
                        print(f"        heard: {' '.join(heard[-12:])}")
    print(f"\n  {total} verses checked, {flagged} flagged for a human ear")


if __name__ == "__main__":
    main()
