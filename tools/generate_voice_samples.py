# -*- coding: utf-8 -*-
"""Generate voice samples for owner to pick narration voices.

Produces Psalm 23 and John 1:1-14 in each candidate voice so the owner
can listen and choose.

Usage:
  python generate_voice_samples.py --russian     # Russian candidates only
  python generate_voice_samples.py --english     # English candidates only
  python generate_voice_samples.py               # both

Prerequisites:
  pip install piper-tts kokoro
  Piper models download automatically on first use.
  Kokoro voices: pip install kokoro (includes voices).

Output: tools/voice_samples/<engine>_<voice>_<passage>.wav
"""
import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
SAMPLES_DIR = HERE / "voice_samples"
KOKORO_PYTHON = str(HERE / ".kokoro_venv" / "Scripts" / "python.exe")

# --- Sample passages ---

# Psalm 23 (book 18, chapter 22 in 0-indexed) — universally known
# John 1:1-14 (book 42, chapter 0, verses 0-13) — the plan's PoC passage

def load_verses(asset_name, book_idx, chapter_idx, verse_start=0, verse_end=None):
    path = ASSETS / asset_name
    with open(path, encoding="utf-8") as f:
        books = json.load(f)
    chapter = books[book_idx]["chapters"][chapter_idx]
    end = verse_end if verse_end is not None else len(chapter)
    return chapter[verse_start:end]


def build_passage(verses):
    return " ".join(v for v in verses if v)


# --- Russian samples (Piper) ---

PIPER_MODELS = HERE / "piper_models"

RU_VOICES = [
    ("piper", str(PIPER_MODELS / "ru_RU-dmitri-medium.onnx")),
    ("piper", str(PIPER_MODELS / "ru_RU-denis-medium.onnx")),
]

RU_PASSAGES = {
    "psalm23": ("ru_synodal.json", 18, 22, 0, None),   # Psalm 23
    "john1":   ("ru_synodal.json", 42, 0,  0, 14),     # John 1:1-14
}

# --- English samples (Kokoro) ---

EN_VOICES = [
    ("kokoro", "am_onyx"),
    ("kokoro", "am_fenrir"),
    ("kokoro", "am_michael"),
    ("kokoro", "am_adam"),
    ("kokoro", "am_echo"),
    ("kokoro", "am_eric"),
    ("kokoro", "am_liam"),
    ("kokoro", "am_puck"),
    ("kokoro", "bm_daniel"),
    ("kokoro", "bm_fable"),
    ("kokoro", "bm_george"),
    ("kokoro", "bm_lewis"),
]

EN_PASSAGES = {
    "psalm23": ("en_kjv.json", 18, 22, 0, None),       # Psalm 23
    "john1":   ("en_kjv.json", 42, 0,  0, 14),         # John 1:1-14
}


def strip_kjv_notes(text):
    """Strip {x:y} margin notes, keep {supplied words}."""
    import re
    text = re.sub(r"\{[^:}]*:[^}]*\}", "", text)
    text = re.sub(r"[{}]", "", text)
    return text.strip()


def synthesize_piper(text, model_path, output_wav, length_scale=1.11):
    """Synthesize with Piper TTS via Python API (CLI has encoding bugs on Windows).

    length_scale > 1.0 = slower speech. 1.11 ≈ 0.9x speed.
    """
    import wave as wave_mod
    try:
        from piper.voice import PiperVoice
        from piper.config import SynthesisConfig
        voice = PiperVoice.load(model_path)
        syn_config = SynthesisConfig(length_scale=length_scale)
        with wave_mod.open(str(output_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(voice.config.sample_rate)
            for chunk in voice.synthesize(text, syn_config):
                wf.writeframes(chunk.audio_int16_bytes)
        return True
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return False


def synthesize_kokoro(text, voice, output_wav):
    """Synthesize with Kokoro TTS via the sandboxed Python 3.12 venv."""
    import tempfile
    text_file = Path(tempfile.mktemp(suffix=".txt"))
    try:
        text_file.write_text(text, encoding="utf-8")
        script = f"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from pathlib import Path
text = Path(r'{text_file}').read_text(encoding='utf-8')
import kokoro
import soundfile as sf
import numpy as np
pipeline = kokoro.KPipeline(lang_code='a')
generator = pipeline(text, voice='{voice}')
chunks = []
for _, _, audio in generator:
    chunks.append(audio)
samples = np.concatenate(chunks)
sf.write(r'{output_wav}', samples, 24000)
print('OK')
"""
        result = subprocess.run(
            [KOKORO_PYTHON, "-c", script],
            capture_output=True, timeout=600, text=True,
        )
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[:500]}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return False
    finally:
        text_file.unlink(missing_ok=True)


def generate_samples(voices, passages, lang, strip_notes=False):
    for passage_name, (asset, book, chapter, v_start, v_end) in passages.items():
        verses = load_verses(asset, book, chapter, v_start, v_end)
        text = build_passage(verses)
        if strip_notes:
            text = strip_kjv_notes(text)

        # Truncate display
        preview = text[:80] + "..." if len(text) > 80 else text
        print(f"\n  Passage: {passage_name} ({len(verses)} verses)")
        print(f"  Text: {preview}")

        for engine, voice in voices:
            voice_label = Path(voice).stem if "/" in voice or "\\" in voice else voice
            out = SAMPLES_DIR / f"{engine}_{voice_label}_{passage_name}.wav"
            if out.exists():
                print(f"  [{voice_label}] already exists, skipping")
                continue

            print(f"  [{voice_label}] generating...", end=" ", flush=True)

            if engine == "piper":
                ok = synthesize_piper(text, voice, out)
            elif engine == "kokoro":
                ok = synthesize_kokoro(text, voice, out)
            else:
                print(f"unknown engine {engine}", file=sys.stderr)
                continue

            if ok:
                size_kb = out.stat().st_size // 1024
                print(f"done ({size_kb} KB)")
            else:
                print("FAILED")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--russian", action="store_true", help="Russian voices only")
    parser.add_argument("--english", action="store_true", help="English voices only")
    args = parser.parse_args()

    do_both = not args.russian and not args.english
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    if do_both or args.russian:
        print("=== Russian voice candidates (Piper, CC0) ===")
        print("Voices: dmitri, denis")
        generate_samples(RU_VOICES, RU_PASSAGES, "ru")

    if do_both or args.english:
        print("\n=== English voice candidates (Kokoro, Apache 2.0) ===")
        print("Voices: am_onyx, am_fenrir, am_michael")
        generate_samples(EN_VOICES, EN_PASSAGES, "en", strip_notes=True)

    print(f"\nSamples in: {SAMPLES_DIR}")
    print("Listen and pick your voices!")


if __name__ == "__main__":
    main()
