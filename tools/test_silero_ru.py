# -*- coding: utf-8 -*-
"""Test Silero v5_cis_base Russian TTS (MIT licensed).

LICENSE GATE: only v5_cis_base / v5_cis_base_nostress are MIT.
The v5_cis_ext and v4_ru/v5_5_ru models are CC-NC-BY — DO NOT USE.
Ref: github.com/snakers4/silero-models README, "All of the below models
are published under MIT licence" (V5 CIS Base section).

v5_cis_base does automatic stress marking, which is why it is preferred
over the _nostress variant for Bible narration.
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import torch
import soundfile as sf

OUT_DIR = "C:/Projects/Hexapla-releases/narration"
MODEL = "v5_cis_base"  # MIT. Do not switch to v5_cis_ext (CC-NC-BY).
SAMPLE_RATE = 48000

# John 1:1-3 from Synodal
bible = json.load(open("app/src/main/assets/bibles/ru_synodal.json", encoding="utf-8"))
verses = bible[42]["chapters"][0][:3]
text = " ".join(verses)
print(f"Text ({len(text)} chars): {text[:60]}...")

print(f"Loading Silero {MODEL} (MIT)...")
model, example_text = torch.hub.load(
    repo_or_dir="snakers4/silero-models",
    model="silero_tts",
    language="ru",
    speaker=MODEL,
    trust_repo=True,
)
model.to(torch.device("cpu"))

speakers = getattr(model, "speakers", [])
print(f"Available speakers ({len(speakers)}): {speakers}")

# Generate for every available speaker so the owner can pick by ear.
for spk in speakers:
    if spk == "random":
        continue
    try:
        audio = model.apply_tts(text=text, speaker=spk, sample_rate=SAMPLE_RATE)
        out = f"{OUT_DIR}/ru_silero_{spk}.wav"
        sf.write(out, audio.numpy(), SAMPLE_RATE)
        print(f"  {spk}: {len(audio)/SAMPLE_RATE:.1f}s -> {out}")
    except Exception as e:
        print(f"  {spk}: FAILED — {e}")

print("Done!")
