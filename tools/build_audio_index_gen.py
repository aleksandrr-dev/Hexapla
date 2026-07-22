# -*- coding: utf-8 -*-
"""Build app/src/main/assets/audio_index_gen.json from a rendered narration set.

Maps each generated translation's chapters to their archive.org stream URL +
per-verse offsets (ms). Consumed by AudioRepo.generated(); the app streams the
per-chapter .ogg from archive.org (one file per chapter). Offsets are carried
for a future verse-highlighting pass; v1 playback ignores them.

    python tools/build_audio_index_gen.py            # build + assert
    python tools/build_audio_index_gen.py --dry-run  # report only

Each set: narration/<id>/<bookIdx>/<chapterIdx>.ogg + matching .json sidecar
({"offsets":[ms,...]}). Hard-fails if a chapter's .ogg or sidecar is missing,
or if the chapter grid does not match the translation's bible asset.
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
ASSETS = Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
OUT = ASSETS / "audio_index_gen.json"

# Each generated set: (narration dir id, bible asset, archive.org item id).
SETS = [
    ("wbt", "en_webster.json", "hexapla-audio-webster-1833"),
]
ARCHIVE_BASE = "https://archive.org/download"


def bible_chapter_counts(asset_name):
    data = json.loads((ASSETS / "bibles" / asset_name).read_text(encoding="utf-8"))
    books = data if isinstance(data, list) else data["books"]
    counts = []
    for b in books:
        chapters = b["chapters"] if isinstance(b, dict) else b
        counts.append(len(chapters))
    return counts


def build_set(set_id, asset_name, item_id, errors):
    src = NARRATION / set_id
    if not src.is_dir():
        errors.append(f"{set_id}: no narration dir at {src}")
        return None
    counts = bible_chapter_counts(asset_name)
    base = f"{ARCHIVE_BASE}/{item_id}"
    entry = {}
    total = 0
    for bi, n_ch in enumerate(counts):
        chapters = {}
        for ci in range(n_ch):
            ogg = src / str(bi) / f"{ci}.ogg"
            sidecar = src / str(bi) / f"{ci}.json"
            if not ogg.exists():
                errors.append(f"{set_id}: missing audio {bi}/{ci}.ogg")
                continue
            if not sidecar.exists():
                errors.append(f"{set_id}: missing sidecar {bi}/{ci}.json")
                continue
            offsets = json.loads(sidecar.read_text(encoding="utf-8")).get("offsets", [])
            chapters[str(ci)] = {"f": f"{bi}/{ci}.ogg", "o": offsets}
            total += 1
        if chapters:
            entry[str(bi)] = {"base": base, "chapters": chapters}
    # Assertions: every chapter of the grid present, book count matches.
    expected = sum(counts)
    if total != expected:
        errors.append(f"{set_id}: {total} chapters built, grid expects {expected}")
    if len(entry) != len(counts):
        errors.append(f"{set_id}: {len(entry)} books built, grid has {len(counts)}")
    print(f"{set_id}: {total}/{expected} chapters across {len(entry)}/{len(counts)} books")
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    errors = []
    out = {}
    for set_id, asset, item in SETS:
        e = build_set(set_id, asset, item, errors)
        if e is not None:
            out[set_id] = e

    if errors:
        print("\nFAILED:")
        for e in errors[:20]:
            print("  " + e)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        sys.exit(1)

    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    print(f"\nasset size: {len(payload.encode('utf-8')) / 1024:.0f} KB")
    if a.dry_run:
        print("DRY RUN — not written.")
        return
    OUT.write_text(payload, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
