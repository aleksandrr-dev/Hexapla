# -*- coding: utf-8 -*-
"""Upload generated Bible narration to archive.org.

Uses the `ia` CLI (internetarchive package) to upload generated audio files
to an archive.org item. Files are organized by book/chapter indices.

Usage:
  python upload_narration.py --lang en --item hexapla-audio-en
  python upload_narration.py --lang wbt --item hexapla-audio-en
  python upload_narration.py --lang ru --item hexapla-audio-ru

Options:
  --lang LANG       Language code (ru, en)
  --item ITEM       archive.org item identifier
  --dry-run         Print what would be uploaded without uploading
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUTPUT = Path("C:/Projects/Hexapla-releases/narration")

# Remote filename conventions — must match audio_index.json URLs
REMOTE_PREFIX = {
    "en": "kjv",
    "wbt": "wbt",
    "gnv": "gnv",
    "tyn": "tyn",
    "wyc": "wyc",
    "ru": "syn",
}

# Item metadata templates
ITEM_METADATA = {
    "ru": {
        "title": "Hexapla Bible Audio - Russian (Synodal)",
        "description": "Self-generated narration of the Russian Synodal Bible translation using Piper TTS.",
        "subject": ["bible", "audio", "russian", "synodal", "tts", "narration", "hexapla"],
        "creator": "Aleksandr Ratchkov (generator), Piper TTS",
        "licenseurl": "http://creativecommons.org/licenses/by-sa/4.0/",  # Placeholder
        "mediatype": "audio",
        "collection": "texts",
    },
    "en": {
        "title": "Hexapla Bible Audio - English (KJV)",
        "description": "Self-generated narration of King James Bible for books without LibriVox coverage.",
        "subject": ["bible", "audio", "english", "kjv", "tts", "narration", "hexapla"],
        "creator": "Aleksandr Ratchkov (generator), Kokoro TTS",
        "licenseurl": "http://creativecommons.org/licenses/by-sa/4.0/",
        "mediatype": "audio",
        "collection": "texts",
    },
    "wbt": {
        "title": "Hexapla Bible Audio - English (Webster 1833)",
        "description": "Self-generated narration of Webster's Bible Translation (1833), all 66 books.",
        "subject": ["bible", "audio", "english", "webster", "tts", "narration", "hexapla"],
        "creator": "Aleksandr Ratchkov (generator), Kokoro TTS",
        "licenseurl": "http://creativecommons.org/licenses/by-sa/4.0/",
        "mediatype": "audio",
        "collection": "texts",
    },
    "gnv": {
        "title": "Hexapla Bible Audio - English (Geneva 1599)",
        "description": "Self-generated narration of the Geneva Bible (1599), all 66 books.",
        "subject": ["bible", "audio", "english", "geneva", "tts", "narration", "hexapla"],
        "creator": "Aleksandr Ratchkov (generator), Kokoro TTS",
        "licenseurl": "http://creativecommons.org/licenses/by-sa/4.0/",
        "mediatype": "audio",
        "collection": "texts",
    },
    "tyn": {
        "title": "Hexapla Bible Audio - English (Tyndale 1525/1531)",
        "description": "Self-generated narration of Tyndale's Bible (1525 NT / 1531 Pentateuch + partial OT).",
        "subject": ["bible", "audio", "english", "tyndale", "tts", "narration", "hexapla"],
        "creator": "Aleksandr Ratchkov (generator), Kokoro TTS",
        "licenseurl": "http://creativecommons.org/licenses/by-sa/4.0/",
        "mediatype": "audio",
        "collection": "texts",
    },
    "wyc": {
        "title": "Hexapla Bible Audio - English (Wycliffe ~1395)",
        "description": "Self-generated narration of the Wycliffe Bible (~1395), all 66 books.",
        "subject": ["bible", "audio", "english", "wycliffe", "tts", "narration", "hexapla"],
        "creator": "Aleksandr Ratchkov (generator), Kokoro TTS",
        "licenseurl": "http://creativecommons.org/licenses/by-sa/4.0/",
        "mediatype": "audio",
        "collection": "texts",
    },
}

# Book names (canonical order, 66 books)
BOOK_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
    "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]


def check_ia_available():
    """Check if `ia` CLI is available."""
    try:
        subprocess.run(["ia", "--help"], capture_output=True, timeout=5)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def get_uploaded_files(item_id):
    """Get list of files already uploaded to the item."""
    try:
        result = subprocess.run(
            ["ia", "list", item_id],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            files = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("["):
                    files.append(line)
            return set(files)
    except Exception as e:
        print(f"Warning: could not list existing files: {e}", file=sys.stderr)

    return set()


def upload_file(item_id, local_path, remote_path, dry_run=False):
    """Upload a single file to archive.org item."""
    if dry_run:
        print(f"  [DRY] Would upload {local_path} -> {item_id}/{remote_path}")
        return True

    try:
        cmd = [
            "ia",
            "upload",
            item_id,
            str(local_path),
            "--remote-name", remote_path,
            "--quiet",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            print(f"Upload failed: {result.stderr.decode()}", file=sys.stderr)
            return False
        print(f"  Uploaded {remote_path}")
        return True
    except subprocess.TimeoutExpired:
        print(f"Upload timeout for {local_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Upload error: {e}", file=sys.stderr)
        return False


def upload_language(lang, item_id, dry_run=False):
    """Upload all generated files for a language to archive.org."""
    lang_dir = OUTPUT / lang
    if not lang_dir.exists():
        print(f"No output directory for {lang}: {lang_dir}", file=sys.stderr)
        return False

    # Collect all .ogg files
    ogg_files = list(lang_dir.glob("*/*.ogg"))
    if not ogg_files:
        print(f"No .ogg files found in {lang_dir}", file=sys.stderr)
        return False

    print(f"Found {len(ogg_files)} audio files to upload")

    # Get existing files (skip if already there)
    existing = get_uploaded_files(item_id) if not dry_run else set()

    uploaded = 0
    prefix = REMOTE_PREFIX.get(lang, lang)

    for ogg_file in sorted(ogg_files):
        book_idx = ogg_file.parent.name
        chapter = ogg_file.stem  # 0-based, matches audio_index.json URLs
        remote_path = f"{prefix}_{book_idx}_{chapter}.ogg"

        if remote_path in existing:
            print(f"  Skipping {remote_path} (already uploaded)")
            continue

        if upload_file(item_id, ogg_file, remote_path, dry_run=dry_run):
            uploaded += 1

    print(f"\nUploaded {uploaded}/{len(ogg_files)} files")
    return uploaded > 0


def create_item_if_needed(item_id, lang, dry_run=False):
    """Create archive.org item if it doesn't exist."""
    if dry_run:
        print(f"[DRY] Would create item {item_id} if needed")
        return

    try:
        # Check if item exists
        result = subprocess.run(
            ["ia", "metadata", item_id],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(f"Item {item_id} exists")
            return

        # Create item
        meta = ITEM_METADATA.get(lang, ITEM_METADATA["en"])
        cmd = ["ia", "upload", item_id, "--metadata"]
        for key, value in meta.items():
            if isinstance(value, list):
                for v in value:
                    cmd.extend([f"{key}={v}"])
            else:
                cmd.append(f"{key}={value}")

        print(f"Creating item {item_id}...", file=sys.stderr)
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0:
            print(f"Item created: {item_id}")
        else:
            print(f"Warning: item creation may have failed: {result.stderr.decode()}", file=sys.stderr)

    except Exception as e:
        print(f"Warning: could not create item: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Upload generated Bible narration to archive.org.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--lang", required=True, choices=list(REMOTE_PREFIX.keys()), help="Language")
    parser.add_argument("--item", required=True, help="archive.org item identifier")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded")

    args = parser.parse_args()

    # Check ia CLI
    if not args.dry_run and not check_ia_available():
        print("Error: 'ia' CLI not found. Install with: pip install internetarchive", file=sys.stderr)
        print("Then authenticate with: ia configure", file=sys.stderr)
        sys.exit(1)

    print(f"Uploading {args.lang} narration to archive.org item: {args.item}\n")

    # Create item if needed
    if not args.dry_run:
        create_item_if_needed(args.item, args.lang)

    # Upload files
    if upload_language(args.lang, args.item, dry_run=args.dry_run):
        print("\nUpload complete!")
        if not args.dry_run:
            print(f"View at: https://archive.org/details/{args.item}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
