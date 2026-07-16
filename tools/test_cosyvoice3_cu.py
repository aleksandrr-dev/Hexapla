# -*- coding: utf-8 -*-
"""Ear test: can CosyVoice3 read civil-script Church Slavonic acceptably?

Renders Псалом 22 from cu_elizabeth.json (6 verses, the most familiar text —
«Господь пасет мя») in the owner's voice, per-verse with 600ms gaps, exactly
as narrate.py would produce it. instruct2 path (no reference transcript, so
the transcript-mismatch trap cannot occur).

KNOWN RISKS the owner's ear must judge (there is no lexicon fix):
  * akanye — the model learned modern Russian; liturgical reading is
    окающее (о stays [о]);
  * guessed stress on archaic forms (внегда́, ничто́же, воззва́х);
  * it will read Slavonic the way a modern Russian reader would, not the
    way a church reader does. Whether that serves the mission is his call.
"""
import sys, io, os, json

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

def _load_soundfile(wav, *a, **kw):
    data, sr = sf.read(str(wav), dtype="float32", always_2d=True)
    return torch.from_numpy(data.T.copy()), sr
torchaudio.load = _load_soundfile

from cosyvoice.cli.cosyvoice import AutoModel

VOICE = "C:/Projects/Hexapla-releases/narration/myvoice_take1.wav"
OUT = "C:/Projects/Hexapla-releases/narration/cu_test_ps22.wav"
INSTRUCT = "You are a helpful assistant.<|endofprompt|>"

bible = json.load(open("C:/Projects/Hexapla/app/src/main/assets/bibles/cu_elizabeth.json",
                       encoding="utf-8"))
verses = bible[18]["chapters"][21]          # Псалом 22
print(f"Пс 22: {len(verses)} verses")
for v in verses:
    print(f"  {v}")

cosy = AutoModel(model_dir=f"{COSY}/pretrained_models/Fun-CosyVoice3-0.5B")
SR = cosy.sample_rate
gap = np.zeros(int(SR * 0.6), dtype=np.float32)

pieces = []
for i, verse in enumerate(verses):
    got = [j["tts_speech"].squeeze(0).cpu().numpy()
           for j in cosy.inference_instruct2(verse, INSTRUCT, VOICE, stream=False)]
    audio = np.concatenate(got)
    print(f"  v{i+1}: {len(audio)/SR:.1f}s")
    pieces.append(audio)
    if i < len(verses) - 1:
        pieces.append(gap)

combined = np.concatenate(pieces)
sf.write(OUT, combined, SR)
print(f"\nSaved {OUT} ({len(combined)/SR:.1f}s)")
