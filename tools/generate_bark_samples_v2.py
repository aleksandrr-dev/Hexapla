# -*- coding: utf-8 -*-
"""Generate Bark v1 + multilingual speaker samples for Russian voice selection.

Produces John 1:1-3 in:
  - v1 ru_speaker_0..9 (different embeddings from the v2 set already tested)
  - multilingual speaker_0..9 (language-neutral, fed Russian text)

Usage (from repo root):
  .kokoro_venv/Scripts/python tools/generate_bark_samples_v2.py
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

os.environ.setdefault("SUNO_USE_SMALL_MODELS", "True")

import torch
_orig_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)
torch.load = _patched_load

from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
SAMPLES_DIR = HERE / "voice_samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

with open(ASSETS / "ru_synodal.json", encoding="utf-8") as f:
    books = json.load(f)
john1 = books[42]["chapters"][0]
text = " ".join(john1[0:3])
print(f"Text: {text}\n")

print("Loading Bark models...")
from bark import generate_audio, preload_models, SAMPLE_RATE
preload_models()
print("Models loaded.\n")

import scipy.io.wavfile as wavfile

presets = []
for i in range(10):
    presets.append((f"ru_speaker_{i}", f"bark_v1_ru_speaker_{i}_john1.wav"))
for i in range(10):
    presets.append((f"speaker_{i}", f"bark_multi_speaker_{i}_john1.wav"))

for preset_name, filename in presets:
    out = SAMPLES_DIR / filename
    if out.exists():
        print(f"[{preset_name}] already exists, skipping")
        continue
    print(f"[{preset_name}] generating...", end=" ", flush=True)
    try:
        audio = generate_audio(text, history_prompt=preset_name)
        wavfile.write(str(out), SAMPLE_RATE, audio)
        size_kb = out.stat().st_size // 1024
        print(f"done ({size_kb} KB)")
    except Exception as e:
        print(f"FAILED: {e}")

print(f"\nSamples in: {SAMPLES_DIR}")
