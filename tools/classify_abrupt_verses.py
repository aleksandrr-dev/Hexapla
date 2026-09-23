# -*- coding: utf-8 -*-
"""Split abrupt-ending verses into CONTENT LOST vs fade-only, by ASR.

WHY BOTH CLASSES EXIST. `_trim_and_fade` was never called on the cosyvoice3
path, so a verse CosyVoice ended abruptly was spliced onto 600 ms of digital
silence at full amplitude. Sometimes the words are all there and only the fade
is missing (audible as a click); sometimes CosyVoice stopped early and words
are genuinely gone. Only the second kind loses scripture, and the owner's
decision (2026-08-05) is to repair those first.

WHY DURATION CANNOT DO THIS. A verse that loses its last word is barely shorter
— Numbers 1:8 lost «Цуара» and still measured 13.8 ch/s against a chapter
median of 13.7. Every duration and pace check passes. The defect REMOVES
content without changing the statistics, so a transcript is the only evidence.

⚠ THE TRAP THIS TOOL EXISTS TO AVOID. A naive "are the expected final words in
the transcript?" test called 49% of a sample content-lost. Inspecting the
transcripts showed most of those were Whisper FAILING — returning English or
CJK text for Russian scripture — not audio missing. With a transcript-quality
gate the figure fell to 32%, with a quarter of the sample unjudgeable. So:
  * verses whose transcript does not track the expected text at all are
    reported as UNJUDGED, never as content loss;
  * verses whose final word is a NUMERAL are reported separately, because
    Whisper writes «45650» for «сорок пять тысяч шестьсот пятьдесят» and the
    tail test cannot see it.
An honest "I don't know" bucket is the point, not a nuisance.

Resumable: state is keyed by chapter/verse plus the audio's size+mtime, so a
re-rendered verse is automatically re-judged rather than trusted from cache.

    python tools/classify_abrupt_verses.py            # all flagged verses
    python tools/classify_abrupt_verses.py --limit 50
"""
import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import soundfile as sf

NARR = Path("C:/Projects/Hexapla-releases/narration/ru")
ASSET = Path("C:/Projects/Hexapla/app/src/main/assets/bibles/ru_synodal.json")
FLAGS = Path("C:/Projects/Hexapla-releases/narration/logs/abrupt_endings_ru.json")
STATE = Path("C:/Projects/Hexapla-releases/narration/logs/abrupt_classified.json")
GAP_MS = 600
MATCH_GATE = 0.45

NUMWORD = re.compile(
    r"(один|два|две|три|четыре|пять|шесть|семь|восемь|девять|десят|"
    r"надцат|дцат|сорок|сто|двест|трист|четырест|пятьсот|шестьсот|"
    r"семьсот|восемьсот|девятьсот|тысяч|перв|втор|трет|четверт)", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    flags = json.loads(FLAGS.read_text(encoding="utf-8"))
    bible = json.loads(ASSET.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}

    todo = []
    for key, hits in flags.items():
        b, c = (int(x) for x in key.split("/"))
        ogg = NARR / str(b) / f"{c}.ogg"
        st = ogg.stat()
        stamp = f"{st.st_size}:{int(st.st_mtime)}"
        for h in hits:
            k = f"{key}/{h['verse']}"
            if state.get(k, {}).get("stamp") == stamp:
                continue
            todo.append((k, b, c, h["verse"], stamp))
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} verses to judge "
          f"({sum(len(v) for v in flags.values())} flagged in total)")

    model = WhisperModel(args.model, device="cpu", compute_type="int8",
                         cpu_threads=3, num_workers=1)

    cache_key, cache = None, None
    for n, (k, b, c, v, stamp) in enumerate(todo, 1):
        if cache_key != (b, c):
            a, sr = sf.read(str(NARR / str(b) / f"{c}.ogg"), dtype="float32")
            if a.ndim > 1:
                a = a.mean(1)
            off = json.loads((NARR / str(b) / f"{c}.json")
                             .read_text(encoding="utf-8"))["offsets"]
            cache_key, cache = (b, c), (a, sr, off, len(a) / sr * 1000)
        a, sr, off, total = cache

        text = bible[b]["chapters"][c][v - 1]
        st = off[v - 1]
        en = (off[v] if v < len(off) else total) - GAP_MS
        seg = a[int(st / 1000 * sr):int(en / 1000 * sr)]
        segs, _ = model.transcribe(seg, language="ru", beam_size=5)
        got = " ".join(s.text for s in segs).strip()

        whole = difflib.SequenceMatcher(None, text.lower(), got.lower(),
                                        autojunk=False).ratio()
        words = re.findall(r"[А-Яа-яЁё]+", text)
        last = words[-1] if words else ""
        if whole < MATCH_GATE:
            verdict = "unjudged"
        elif NUMWORD.search(last):
            verdict = "numeric_tail"
        else:
            present = (last.lower()[:5] in got.lower() or
                       difflib.SequenceMatcher(None, last.lower()[:6],
                                               got.lower()[-40:],
                                               autojunk=False).ratio() > 0.55)
            verdict = "fade_only" if present else "content_lost"

        state[k] = {"stamp": stamp, "verdict": verdict,
                    "match": round(whole, 2), "last": last,
                    "heard_tail": got[-60:]}
        if n % 25 == 0 or n == len(todo):
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                             encoding="utf-8")
            counts = {}
            for r in state.values():
                counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
            print(f"  {n}/{len(todo)}  {counts}", flush=True)

    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    counts = {}
    for r in state.values():
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("\nfinal:", counts)
    lost = sorted({k.rsplit("/", 1)[0] for k, r in state.items()
                   if r["verdict"] == "content_lost"},
                  key=lambda s: [int(x) for x in s.split("/")])
    print(f"chapters with content loss: {len(lost)}")
    print(f"-> {STATE}")


if __name__ == "__main__":
    main()
