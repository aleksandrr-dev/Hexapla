# -*- coding: utf-8 -*-
"""Generate Russian samples with all Qwen3-TTS voices for comparison."""
import sys, io, json, torch, soundfile as sf
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from qwen_tts import Qwen3TTSModel

MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
OUT_DIR = "C:/Projects/Hexapla-releases/narration"

VOICES = ["Vivian", "Serena", "Dylan", "Eric", "Aiden", "Leo", "Dan", "Zac"]

print("Loading Qwen3-TTS 0.6B model...")
model = Qwen3TTSModel.from_pretrained(
    MODEL,
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

bible = json.load(open("app/src/main/assets/bibles/ru_synodal.json", encoding="utf-8"))
verses = bible[42]["chapters"][0][:3]
text = " ".join(verses)
print(f"Text length: {len(text)} chars")

for voice in VOICES:
    print(f"\nGenerating voice: {voice}...")
    try:
        wavs, sr = model.generate_custom_voice(
            text=text,
            language="Russian",
            speaker=voice,
        )
        out = f"{OUT_DIR}/ru_qwen3_{voice.lower()}.wav"
        sf.write(out, wavs[0], sr)
        print(f"  Saved {out} ({len(wavs[0])/sr:.1f}s)")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nDone!")
