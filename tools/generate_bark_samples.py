# -*- coding: utf-8 -*-
"""Generate Bark TTS voice samples for Russian narration voice selection.

Produces John 1:1-3 (short, fits Bark's ~13s window) in all 10 Russian
speaker presets so the owner can pick by ear.

Usage (from repo root):
  .kokoro_venv/Scripts/python tools/generate_bark_samples.py

Output: tools/voice_samples/bark_ru_speaker_N_john1.wav
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Force CPU and small models
os.environ.setdefault("SUNO_USE_SMALL_MODELS", "True")

# Patch torch.load for Bark compatibility with PyTorch 2.6+
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

# Short passage: John 1:1-3 (fits in one Bark generation window)
with open(ASSETS / "ru_synodal.json", encoding="utf-8") as f:
    books = json.load(f)
john1 = books[42]["chapters"][0]
# Verses 1-3 only (Bark handles ~30-50 words well)
text = " ".join(john1[0:3])
print(f"Text: {text}\n")

print("Loading Bark models (first run downloads ~1.5 GB)...")
from bark import generate_audio, preload_models, SAMPLE_RATE
preload_models()
print("Models loaded.\n")

import scipy.io.wavfile as wavfile

for i in range(10):
    preset = f"v2/ru_speaker_{i}"
    out = SAMPLES_DIR / f"bark_ru_speaker_{i}_john1.wav"
    if out.exists():
        print(f"[speaker_{i}] already exists, skipping")
        continue
    print(f"[speaker_{i}] generating...", end=" ", flush=True)
    try:
        audio = generate_audio(text, history_prompt=preset)
        wavfile.write(str(out), SAMPLE_RATE, audio)
        size_kb = out.stat().st_size // 1024
        print(f"done ({size_kb} KB)")
    except Exception as e:
        print(f"FAILED: {e}")

print(f"\nSamples in: {SAMPLES_DIR}")
print("Listen to all 10 and pick the deepest male voice!")
