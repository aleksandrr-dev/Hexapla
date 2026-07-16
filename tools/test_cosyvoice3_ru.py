# -*- coding: utf-8 -*-
"""Test Fun-CosyVoice3-0.5B-2512 Russian — zero-shot clone of Edge Dmitry.

WHY THIS EXISTS: CosyVoice **2** was a dead end (no Russian at all — it
produced phonetic gibberish). CosyVoice **3** is a different model and
DOES list Russian: "Covers 9 common languages (Chinese, English,
Japanese, Korean, German, Spanish, French, Italian, Russian)" — verified
on the HF model card for this exact checkpoint, weights license tag
apache-2.0.

Run from the CosyVoice repo dir (relative asset paths) or use the
absolute paths below.
"""
import sys, io, json, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

COSY = "C:/Projects/CosyVoice"
sys.path.insert(0, f"{COSY}/third_party/Matcha-TTS")
sys.path.insert(0, COSY)
os.chdir(COSY)

import soundfile as sf
import numpy as np
import torch
import torchaudio

# torchaudio >=2.9 routes .load() through torchcodec, which needs FFmpeg
# DLLs on PATH and does not resolve them on this box. CosyVoice's
# load_wav already asks for backend='soundfile' (cosyvoice/utils/
# file_utils.py:45) but modern torchaudio ignores that kwarg. Honour the
# original intent: read via soundfile, return [channels, samples].
def _load_soundfile(wav, *args, **kwargs):
    data, sr = sf.read(str(wav), dtype="float32", always_2d=True)
    return torch.from_numpy(data.T.copy()), sr

torchaudio.load = _load_soundfile

from cosyvoice.cli.cosyvoice import AutoModel

MODEL_DIR = f"{COSY}/pretrained_models/Fun-CosyVoice3-0.5B"
REF_WAV = "C:/Projects/Hexapla-releases/narration/_ref_dmitry_v1_16k.wav"
OUT_DIR = "C:/Projects/Hexapla-releases/narration"

# REF_TEXT must transcribe REF_WAV *exactly*. This bit me: a 10s clip
# (verses 1-3ish) labelled with verse-1-only text told the model that
# Russian maps to ~2.4x less audio than it does, and every output came
# out ~half length. ffmpeg silencedetect on ru_edge_dmitry.mp3 puts the
# verse boundaries at 4.13s / 6.76s / 12.42s, so _ref_dmitry_v1_16k.wav
# is cut at 4.3s = verse 1 exactly, matching the line below.
REF_TEXT = "В начале было Слово, и Слово было у Бога, и Слово было Бог."

# John 1:1-3 from Synodal — same text as every other candidate sample,
# so the owner can A/B directly.
bible = json.load(open("C:/Projects/Hexapla/app/src/main/assets/bibles/ru_synodal.json", encoding="utf-8"))
verses = bible[42]["chapters"][0][:3]

# PER-VERSE synthesis, matching the production pipeline (narrate.py
# synthesizes each verse separately and concatenates with silence gaps).
# Passing all 3 verses as one string yields 59 tokens, just under
# split_paragraph's token_min_n=60, so the frontend does NOT split them —
# the LLM then emits EOS after the first sentence and you get ~5s instead
# of ~15s. Per-verse sidesteps that entirely and is what we'd ship anyway.
print("Loading Fun-CosyVoice3-0.5B...")
cosyvoice = AutoModel(model_dir=MODEL_DIR)
SR = cosyvoice.sample_rate
print(f"Loaded. sample_rate={SR}")

# v3 zero-shot wants the system-prompt prefix on prompt_text.
prompt_text = f"You are a helpful assistant.<|endofprompt|>{REF_TEXT}"

GAP_MS = 600
gap = np.zeros(int(SR * GAP_MS / 1000), dtype=np.float32)

pieces = []
for vi, verse in enumerate(verses):
    print(f"  verse {vi+1} ({len(verse)} chars): {verse[:45]}...")
    got = []
    for j in cosyvoice.inference_zero_shot(
        verse, prompt_text, REF_WAV, stream=False
    ):
        got.append(j["tts_speech"].squeeze(0).cpu().numpy())
    if not got:
        print(f"    !! no audio for verse {vi+1}")
        continue
    v_audio = np.concatenate(got)
    print(f"    -> {len(v_audio)/SR:.1f}s")
    pieces.append(v_audio)
    if vi < len(verses) - 1:
        pieces.append(gap)

combined = np.concatenate(pieces)
out = f"{OUT_DIR}/ru_cosyvoice3_dmitry_clone.wav"
sf.write(out, combined, SR)
print(f"Saved {out} ({len(combined)/SR:.1f}s total)")
