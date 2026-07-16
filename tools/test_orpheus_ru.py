# -*- coding: utf-8 -*-
"""Test Orpheus TTS Russian community fine-tune."""
import json
import sys
import torch
import numpy as np
import soundfile as sf
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from snac import SNAC

MODEL = "papacliff/orpheus-3b-0.1-ft-ru"
OUTPUT = "C:/Projects/Hexapla-releases/narration/ru_orpheus_sample.wav"

print("Loading model (4-bit quantized)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    ),
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained(MODEL)

print("Loading SNAC decoder...")
snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").eval().cpu()


def decode_audio(token_ids):
    n = (len(token_ids) // 7) * 7
    if n == 0:
        return None
    L1, L2, L3 = [], [], []
    for i in range(0, n, 7):
        L1.append(token_ids[i])
        L2.append(token_ids[i + 1] - 4096)
        L3.append(token_ids[i + 2] - 2 * 4096)
        L3.append(token_ids[i + 3] - 3 * 4096)
        L2.append(token_ids[i + 4] - 4 * 4096)
        L3.append(token_ids[i + 5] - 5 * 4096)
        L3.append(token_ids[i + 6] - 6 * 4096)
    clamp = lambda v: [max(0, min(4095, x)) for x in v]
    codes = [torch.tensor(clamp(l)).unsqueeze(0) for l in [L1, L2, L3]]
    with torch.inference_mode():
        return snac.decode(codes).squeeze().numpy().astype(np.float32)


def speak(text, voice="tara", max_tokens=4000):
    ids = tokenizer(f"{voice}: {text}", return_tensors="pt").input_ids
    input_ids = torch.cat([
        torch.tensor([[128259]]), ids,
        torch.tensor([[128009, 128260, 128261, 128257]])
    ], dim=1).to(model.device)

    out = model.generate(
        input_ids=input_ids,
        attention_mask=torch.ones_like(input_ids),
        max_new_tokens=max_tokens,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
        repetition_penalty=1.1,
        eos_token_id=128258,
        use_cache=True,
    )

    gen = out[0][input_ids.shape[1]:]
    BASE = 128266
    audio_tokens = [t.item() - BASE for t in gen if BASE <= t.item() < BASE + 7 * 4096]
    print(f"  Generated {len(audio_tokens)} audio tokens")
    return decode_audio(audio_tokens)


# John 1:1-3 from Synodal
bible = json.load(open("app/src/main/assets/bibles/ru_synodal.json", encoding="utf-8"))
verses = bible[42]["chapters"][0][:3]
text = " ".join(verses)
print(f"Text: {text[:80]}...")

print("Generating speech...")
wav = speak(text)
if wav is not None:
    sf.write(OUTPUT, wav, 24000)
    print(f"Saved {OUTPUT} ({len(wav)/24000:.1f}s)")
else:
    print("ERROR: no audio generated")
