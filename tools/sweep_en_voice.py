# -*- coding: utf-8 -*-
"""Parameter sweep for an English Chatterbox voice clone (owner ear test).

    tools\\.chatterbox_venv\\Scripts\\python.exe tools/sweep_en_voice.py \
        --ref C:/Projects/Hexapla-releases/narration/_en_ref_kjv.wav

Mirrors the Swedish sweep of 2026-07-20 that picked variant C. Chatterbox
exposes two knobs and both are FLOATS, not text — which is why this engine is
the right choice for expressive English: the instruction-leak class that ruined
345 Russian chapters (a Russian-language instruction read aloud as scripture)
cannot occur when there is no instruction string at all.

  cfg_weight    adherence to the reference speaker. Lower = closer to the
                actual voice; the Swedish default of 0.5 "genericised the
                accent".
  exaggeration  expressive range / pitch movement. This is the knob the owner
                asked about — whether English can have emotion like Russian.

⚠ GPU: Chatterbox needs ~4 GB and MUST NOT share the 8 GB card with a live
CosyVoice render. Set CHATTERBOX_DEVICE=cpu, or pause the other render first.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = sys.stderr if False else sys.stdout
HERE = Path(__file__).parent
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
OUT = Path("C:/Projects/Hexapla-releases/narration/_en_sweep")

NOTE = re.compile(r"\s*\{[^{}]*:[^{}]*\}")

# (label, cfg_weight, exaggeration). C is the setting the Swedish pair chose,
# so it is the natural starting point; D and E probe more expression, which is
# the actual question being asked.
# ⚠ Round 1 (2026-08-02) found 0.4 vs 0.7 exaggeration essentially INAUDIBLE
# to the owner — "isn't expressive enough, sounds the same pretty much". The
# useful range is clearly higher than the Swedish sweep suggested. He liked
# cfg_weight 0.5 (the default), unlike Swedish where 0.5 genericised the
# accent, so round 2 holds adherence near his pick and pushes exaggeration
# hard. Lower cfg_weight gives the model more freedom to emote, so one variant
# pairs a high exaggeration with 0.3 to see whether that unlocks more.
VARIANTS = [
    ("E_exag10", 0.5, 1.0),
    ("F_exag15", 0.5, 1.5),
    ("G_loose",  0.3, 1.2),
]

PASSAGES = {
    # Short, familiar, and covers both plain narrative and raised feeling.
    "ps23": (18, 22, 0, 4),      # Psalm 23:1-4
    "jn1":  (42, 0, 0, 5),       # John 1:1-5
    # Deliberately declamatory — Psalm 23 is calm, so it hides expression
    # differences. "O death, where is thy sting?" does not.
    "1co15": (45, 14, 53, 57),   # 1 Corinthians 15:54-57
}


def verses(book, chapter, first, last, asset="en_kjv.json"):
    data = json.loads((ASSETS / asset).read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) else data
    vs = books[book]["chapters"][chapter][first:last]
    out = []
    for v in vs:
        t = NOTE.sub("", v).replace("{", "").replace("}", "")
        out.append(re.sub(r"\s+", " ", t).strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="reference wav (the voice)")
    ap.add_argument("--passages", default="ps23",
                    help="comma-separated: " + ",".join(PASSAGES))
    ap.add_argument("--device", default=os.environ.get("CHATTERBOX_DEVICE", "cuda"))
    args = ap.parse_args()

    ref = Path(args.ref)
    if not ref.exists():
        sys.exit(f"reference not found: {ref}")
    OUT.mkdir(parents=True, exist_ok=True)

    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    print(f"loading Chatterbox on {args.device} ...", flush=True)
    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device=args.device)
    print(f"  loaded in {time.time() - t0:.0f}s", flush=True)

    for pname in args.passages.split(","):
        b, c, f, l = PASSAGES[pname]
        text = " ".join(verses(b, c, f, l))
        print(f"\n{pname}: {len(text)} chars\n  {text[:90]}...", flush=True)
        for label, cfg, exag in VARIANTS:
            dest = OUT / f"{pname}_{label}.wav"
            t0 = time.time()
            wav = model.generate(text, language_id="en",
                                 audio_prompt_path=str(ref),
                                 cfg_weight=cfg, exaggeration=exag)
            torchaudio.save(str(dest), wav, model.sr)
            dur = torchaudio.info(str(dest)).num_frames / model.sr
            print(f"  {label:16} cfg={cfg} exag={exag}  "
                  f"{time.time() - t0:5.0f}s render -> {dur:4.1f}s audio  {dest.name}",
                  flush=True)
    print(f"\nwrote to {OUT}")


if __name__ == "__main__":
    main()
