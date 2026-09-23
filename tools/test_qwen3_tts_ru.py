# -*- coding: utf-8 -*-
"""Test Qwen3-TTS Russian speech generation (0.6B model, fits 8GB VRAM)."""
import sys, io, json, torch, soundfile as sf
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from qwen_tts import Qwen3TTSModel

MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
OUTPUT = "C:/Projects/Hexapla-releases/narration/ru_qwen3_sample.wav"

print("Loading Qwen3-TTS 0.6B model...")
model = Qwen3TTSModel.from_pretrained(
    MODEL,
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

# John 1:1-3 from Synodal
bible = json.load(open("app/src/main/assets/bibles/ru_synodal.json", encoding="utf-8"))
verses = bible[42]["chapters"][0][:3]
text = " ".join(verses)
print(f"Text length: {len(text)} chars")

print("Generating Russian speech...")
wavs, sr = model.generate_custom_voice(
    text=text,
    language="Russian",
    speaker="Ryan",
)

sf.write(OUTPUT, wavs[0], sr)
print(f"Saved {OUTPUT} ({len(wavs[0])/sr:.1f}s)")
