# -*- coding: utf-8 -*-
"""Prepend spoken chapter headers to existing narration .ogg files.

Synthesizes just the header ("Ecclesiastes, Chapter 1"), encodes it as
Opus, concatenates header + silence + existing audio, and shifts the
verse-offset JSON by the header duration.

Usage:
  python prepend_headers.py --lang en
  python prepend_headers.py --lang en --book 20          # one book
  python prepend_headers.py --lang en --book 20 --ch 0   # one chapter
  python prepend_headers.py --dry-run --lang en           # preview only
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

OUTPUT = Path("C:/Projects/Hexapla-releases/narration")
KOKORO_PYTHON = str(HERE / ".kokoro_venv" / "Scripts" / "python.exe")
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"

SILENCE_MS = 600

BOOK_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]

LANG_CONFIG = {
    "en": {"engine": "kokoro", "voice": "am_adam", "asset": "en_kjv.json"},
    "wbt": {"engine": "kokoro", "voice": "am_adam", "asset": "en_webster.json"},
    "gnv": {"engine": "kokoro", "voice": "am_adam", "asset": "en_geneva.json"},
    "tyn": {"engine": "kokoro", "voice": "am_adam", "asset": "en_tyndale.json"},
    "wyc": {"engine": "kokoro", "voice": "am_adam", "asset": "en_webster.json"},
}


def chapter_header_text(book_idx, chapter_idx, n_chapters):
    book = BOOK_NAMES[book_idx] if book_idx < len(BOOK_NAMES) else f"Book {book_idx}"
    if n_chapters == 1:
        return book
    return f"{book}, Chapter {chapter_idx + 1}"


def synthesize_header_wav(text, voice, output_wav):
    script = f"""
import sys
sys.path.insert(0, r'{HERE}')
from kokoro import KPipeline
import soundfile as sf
pipe = KPipeline(lang_code='a')
text = open(r'{output_wav}.txt', encoding='utf-8').read()
for result in pipe(text, voice='{voice}'):
    if result.audio is not None:
        sf.write(r'{output_wav}', result.audio.numpy(), 24000)
        print('OK')
        break
"""
    txt_path = Path(f"{output_wav}.txt")
    txt_path.write_text(text, encoding="utf-8")
    try:
        result = subprocess.run(
            [KOKORO_PYTHON, "-c", script],
            capture_output=True, timeout=60, text=True, encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"    Synth error: {result.stderr[:200]}", file=sys.stderr)
            return False
        return Path(output_wav).exists()
    except Exception as e:
        print(f"    Synth error: {e}", file=sys.stderr)
        return False
    finally:
        txt_path.unlink(missing_ok=True)


def get_wav_duration_ms(wav_file):
    with wave.open(str(wav_file), "rb") as w:
        return int(w.getnframes() / w.getframerate() * 1000)


def make_silence_wav(path, duration_ms, sample_rate=24000):
    n_samples = int(sample_rate * duration_ms / 1000)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)


def prepend_header(ogg_file, json_file, header_text, voice, dry_run=False):
    if dry_run:
        print(f"    Would prepend: \"{header_text}\"")
        return True

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        header_wav = str(tmp / "header.wav")
        silence_wav = str(tmp / "silence.wav")
        header_ogg = str(tmp / "header.ogg")
        combined_ogg = str(tmp / "combined.ogg")

        if not synthesize_header_wav(header_text, voice, header_wav):
            return False

        header_dur_ms = get_wav_duration_ms(header_wav)

        make_silence_wav(silence_wav, SILENCE_MS)

        # Encode header+silence to a temp ogg (loudnorm not needed for a short header)
        concat_list = tmp / "concat.txt"
        concat_list.write_text(
            f"file '{header_wav}'\nfile '{silence_wav}'\n", encoding="utf-8"
        )
        concat_wav = str(tmp / "header_full.wav")
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_list), "-c", "copy", concat_wav],
            capture_output=True, timeout=30,
        )
        if r.returncode != 0:
            print(f"    ffmpeg concat error", file=sys.stderr)
            return False

        # Encode header to opus ogg
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", concat_wav,
             "-b:a", "32k", "-c:a", "libopus", "-ac", "1", header_ogg],
            capture_output=True, timeout=30,
        )
        if r.returncode != 0:
            print(f"    ffmpeg encode error", file=sys.stderr)
            return False

        # Concatenate header.ogg + existing.ogg at the container level
        cat_list = tmp / "cat2.txt"
        cat_list.write_text(
            f"file '{header_ogg}'\nfile '{ogg_file}'\n", encoding="utf-8"
        )
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(cat_list), "-c", "copy", combined_ogg],
            capture_output=True, timeout=60,
        )
        if r.returncode != 0:
            print(f"    ffmpeg splice error: {r.stderr.decode()[-200:]}", file=sys.stderr)
            return False

        # Shift offsets
        shift_ms = header_dur_ms + SILENCE_MS
        data = json.loads(Path(json_file).read_text(encoding="utf-8"))
        data["offsets"] = [o + shift_ms for o in data["offsets"]]

        # Replace files atomically
        import shutil
        shutil.copy2(combined_ogg, str(ogg_file))
        Path(json_file).write_text(
            json.dumps(data, separators=(",", ":")), encoding="utf-8"
        )

        new_kb = Path(ogg_file).stat().st_size // 1024
        print(f" OK (+{shift_ms}ms, {new_kb} KB)")
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prepend chapter headers to existing narration.")
    parser.add_argument("--lang", required=True, choices=list(LANG_CONFIG.keys()))
    parser.add_argument("--book", type=int, help="Single book index")
    parser.add_argument("--ch", type=int, help="Single chapter index (0-based)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = LANG_CONFIG[args.lang]
    lang_dir = OUTPUT / args.lang

    # Load bible to get chapter counts
    bible = json.loads((ASSETS / cfg["asset"]).read_text(encoding="utf-8"))

    book_dirs = sorted(lang_dir.iterdir()) if lang_dir.exists() else []
    if args.book is not None:
        book_dirs = [lang_dir / str(args.book)]

    done = 0
    skipped = 0
    failed = 0

    for book_dir in book_dirs:
        if not book_dir.is_dir():
            continue
        book_idx = int(book_dir.name)
        if book_idx >= len(bible):
            continue
        n_chapters = len(bible[book_idx].get("chapters", []))
        book_name = BOOK_NAMES[book_idx] if book_idx < len(BOOK_NAMES) else f"Book{book_idx}"

        ogg_files = sorted(book_dir.glob("*.ogg"))
        if args.ch is not None:
            ogg_files = [book_dir / f"{args.ch}.ogg"]

        print(f"\n=== {book_name} ({len(ogg_files)} chapters) ===")

        for ogg_file in ogg_files:
            if not ogg_file.exists():
                continue
            ch_idx = int(ogg_file.stem)
            json_file = ogg_file.with_suffix(".json")
            if not json_file.exists():
                print(f"  [ch {ch_idx+1}] skip (no JSON)")
                skipped += 1
                continue

            # Check if header already prepended (offset[0] > 0 suggests it has one)
            data = json.loads(json_file.read_text(encoding="utf-8"))
            if data["offsets"] and data["offsets"][0] > 500:
                print(f"  [ch {ch_idx+1}] skip (already has header, offset[0]={data['offsets'][0]}ms)")
                skipped += 1
                continue

            header = chapter_header_text(book_idx, ch_idx, n_chapters)
            print(f"  [ch {ch_idx+1}] \"{header}\"...", end="", flush=True)

            if prepend_header(str(ogg_file), str(json_file), header, cfg["voice"], args.dry_run):
                done += 1
            else:
                failed += 1

    print(f"\n\nDone: {done} prepended, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
