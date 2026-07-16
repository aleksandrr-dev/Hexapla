# -*- coding: utf-8 -*-
"""Test vosk-tts Russian (Apache 2.0, Alpha Cephei) — all 5 speakers.

Model: vosk-model-tts-ru-0.9-multi (3 female, 2 male; speaker_id 0-4).
Generates John 1:1-3 Synodal for each speaker.
"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from vosk_tts import Model, Synth

OUT_DIR = "C:/Projects/Hexapla-releases/narration"

# John 1:1-3 from Synodal
bible = json.load(open("app/src/main/assets/bibles/ru_synodal.json", encoding="utf-8"))
verses = bible[42]["chapters"][0][:3]
text = " ".join(verses)
print(f"Text ({len(text)} chars): {text[:60]}...")

print("Loading vosk-model-tts-ru-0.9-multi (downloads on first run)...")
model = Model(model_name="vosk-model-tts-ru-0.9-multi")
synth = Synth(model)

for spk in range(5):
    out = f"{OUT_DIR}/ru_vosk_spk{spk}.wav"
    print(f"  speaker {spk} -> {out}")
    synth.synth(text, out, speaker_id=spk)

print("Done! 5 samples written.")
