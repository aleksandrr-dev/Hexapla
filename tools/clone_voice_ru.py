# -*- coding: utf-8 -*-
"""Clone an arbitrary reference voice with Fun-CosyVoice3 and read John 1:1-3 (Synodal).

Usage:
  python tools/clone_voice_ru.py --ref C:/path/take1.wav --name take1
  python tools/clone_voice_ru.py --ref take1.wav --name deep --text "..."

The reference may be any format/rate ffmpeg can read; it is converted to
16 kHz mono automatically.

⚠ THE ONE RULE: --text must transcribe --ref EXACTLY, word for word.
A mismatch teaches the model a wrong text→audio ratio. A 10s clip
labelled with 5s of text produced ~2x-fast output and nearly got this
model wrongly written off (2026-07-15). Default --text is John 1:1.

LICENSE: Fun-CosyVoice3-0.5B-2512 weights are Apache-2.0. The REFERENCE
you supply carries its own rights — use your own voice, a public-domain
recording, or something you have permission for. Do NOT use edge-tts
output: the Microsoft Services Agreement restricts it to noncommercial
personal use and bars "using these materials to build your own products",
which is what cloning it would be.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

COSY = "C:/Projects/CosyVoice"
MODEL_DIR = f"{COSY}/pretrained_models/Fun-CosyVoice3-0.5B"
OUT_DIR = "C:/Projects/Hexapla-releases/narration"
SYNODAL = "C:/Projects/Hexapla/app/src/main/assets/bibles/ru_synodal.json"

# John 1:1 — the default reference line. ~4-5s read at a calm pace,
# inside CosyVoice's 3-10s reference sweet spot.
DEFAULT_REF_TEXT = "В начале было Слово, и Слово было у Бога, и Слово было Бог."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="Reference recording (any format)")
    ap.add_argument("--name", required=True, help="Label for the output file")
    ap.add_argument("--text", default=DEFAULT_REF_TEXT,
                    help="EXACT transcript of --ref (default: John 1:1)")
    ap.add_argument("--verses", type=int, default=3, help="How many verses of John 1")
    args = ap.parse_args()

    sys.path.insert(0, f"{COSY}/third_party/Matcha-TTS")
    sys.path.insert(0, COSY)
    os.chdir(COSY)

    import soundfile as sf
    import numpy as np
    import torch
    import torchaudio

    # torchaudio >=2.9 routes load() via torchcodec, which needs FFmpeg DLLs
    # this box does not expose. CosyVoice already asks for backend='soundfile'
    # (cosyvoice/utils/file_utils.py:45) but modern torchaudio ignores it.
    def _load_soundfile(wav, *a, **kw):
        data, sr = sf.read(str(wav), dtype="float32", always_2d=True)
        return torch.from_numpy(data.T.copy()), sr
    torchaudio.load = _load_soundfile

    from cosyvoice.cli.cosyvoice import AutoModel

    # Normalize the reference to 16 kHz mono.
    ref16 = os.path.join(tempfile.gettempdir(), f"_ref_{args.name}_16k.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", args.ref, "-ar", "16000", "-ac", "1", ref16],
        capture_output=True, check=True,
    )
    info = sf.info(ref16)
    print(f"Reference: {args.ref}")
    print(f"  -> {info.duration:.1f}s @16kHz mono")
    if info.duration < 2.5:
        print("  ⚠ shorter than ~3s — cloning quality will suffer")
    if info.duration > 11:
        print("  ⚠ longer than ~10s — trim it, and make sure --text still matches EXACTLY")
    print(f"  transcript: {args.text}")

    bible = json.load(open(SYNODAL, encoding="utf-8"))
    verses = bible[42]["chapters"][0][:args.verses]

    print("Loading Fun-CosyVoice3-0.5B...")
    cosy = AutoModel(model_dir=MODEL_DIR)
    SR = cosy.sample_rate

    prompt_text = f"You are a helpful assistant.<|endofprompt|>{args.text}"
    gap = np.zeros(int(SR * 0.6), dtype=np.float32)  # 600ms, matches narrate.py

    pieces = []
    for vi, verse in enumerate(verses):
        print(f"  verse {vi+1}: {verse[:45]}...")
        got = [j["tts_speech"].squeeze(0).cpu().numpy()
               for j in cosy.inference_zero_shot(verse, prompt_text, ref16, stream=False)]
        if not got:
            print(f"    !! no audio for verse {vi+1}")
            continue
        v = np.concatenate(got)
        print(f"    -> {len(v)/SR:.1f}s")
        pieces.append(v)
        if vi < len(verses) - 1:
            pieces.append(gap)

    combined = np.concatenate(pieces)
    out = f"{OUT_DIR}/ru_myvoice_{args.name}.wav"
    sf.write(out, combined, SR)
    print(f"\nSaved {out} ({len(combined)/SR:.1f}s)")
    print("Compare against ru_edge_dmitry.mp3 (same text, 13.3s).")


if __name__ == "__main__":
    main()
