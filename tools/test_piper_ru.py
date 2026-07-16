# -*- coding: utf-8 -*-
"""Test Piper Russian voices denis + dmitri (CC0 training data).

LICENSE (verified 2026-07-15):
  denis, dmitri -> OHF-Voice/voice-datasets, "These datasets are licensed
    under CC0 (public domain)." Crowdsourced for Home Assistant's Year of
    Voice by Nabu Casa. CC0 data + MIT engine = no restriction on
    redistributing generated audio. USABLE.
  ruslan -> RUSLAN corpus, CC BY-NC-SA 4.0 (ruslan-corpus.github.io).
    NC in the lineage = NOT usable. This is the voice the owner
    auditioned and rejected in an earlier session; it was never
    shippable regardless of quality.
  irina -> RHVoice, license "Unknown" upstream. Cannot clear.

Generates John 1:1-3 Synodal for the two CC0 voices.
"""
import sys, io, json, wave
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from piper import PiperVoice, SynthesisConfig

OUT_DIR = "C:/Projects/Hexapla-releases/narration"
MODELS = "tools/piper_models"
VOICES = ["denis", "dmitri"]  # CC0 only. Do NOT add ruslan (NC) or irina (unknown).

# John 1:1-3 from Synodal
bible = json.load(open("app/src/main/assets/bibles/ru_synodal.json", encoding="utf-8"))
verses = bible[42]["chapters"][0][:3]
text = " ".join(verses)
print(f"Text ({len(text)} chars): {text[:60]}...")

# length_scale 1.11 = slightly slower than default; plan asks for
# "calm, unhurried" narration.
syn_config = SynthesisConfig(length_scale=1.11)

for name in VOICES:
    model_path = f"{MODELS}/ru_RU-{name}-medium.onnx"
    out = f"{OUT_DIR}/ru_piper_{name}.wav"
    try:
        voice = PiperVoice.load(model_path)
        with wave.open(out, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(voice.config.sample_rate)
            for chunk in voice.synthesize(text, syn_config):
                wf.writeframes(chunk.audio_int16_bytes)
        with wave.open(out, "rb") as w:
            dur = w.getnframes() / w.getframerate()
        print(f"  {name}: {dur:.1f}s -> {out}")
    except Exception as e:
        print(f"  {name}: FAILED — {e}")

print("Done!")
