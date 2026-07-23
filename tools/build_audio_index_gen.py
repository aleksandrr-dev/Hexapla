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

# Each generated set. `tid` = the app translation id (the index is keyed by
# it; ReadingService looks up AudioRepo.generated(translationId)); `dir` = the
# narration output folder (may differ from tid); `partial` = index whatever
# chapters exist rather than requiring the full 1189 (for a Bible still
# rendering — the missing books fall back to TTS until a later index refresh).
SETS = [
    {"tid": "wbt", "dir": "wbt", "asset": "en_webster.json",
     "item": "hexapla-audio-webster-1833", "partial": False},
    # Swedish Karl XII 1703: narration folder 'sv', app id 'kxii'. PARTIAL —
    # Genesis, Exodus, Psalms and the NT render first (for the friend's
    # deadline), the rest of the OT fills in later. Rebuild this index (and
    # re-upload) after each batch completes.
    {"tid": "kxii", "dir": "sv", "asset": "sv_karlxii.json",
     "item": "hexapla-audio-karlxii-1703", "partial": True},
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


def build_set(s, errors):
    tid, ndir, asset_name = s["tid"], s["dir"], s["asset"]
    item_id, partial = s["item"], s["partial"]
    src = NARRATION / ndir
    if not src.is_dir():
        errors.append(f"{tid}: no narration dir at {src}")
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
                if not partial:
                    errors.append(f"{tid}: missing audio {bi}/{ci}.ogg")
                continue
            offsets = []
            if sidecar.exists():
                offsets = json.loads(sidecar.read_text(encoding="utf-8")).get("offsets", [])
            elif not partial:
                errors.append(f"{tid}: missing sidecar {bi}/{ci}.json")
                continue
            chapters[str(ci)] = {"f": f"{bi}/{ci}.ogg", "o": offsets}
            total += 1
        if chapters:
            entry[str(bi)] = {"base": base, "chapters": chapters}
    expected = sum(counts)
    if not partial:
        # Complete sets must cover the whole grid — catches a broken upload.
        if total != expected:
            errors.append(f"{tid}: {total} chapters built, grid expects {expected}")
        if len(entry) != len(counts):
            errors.append(f"{tid}: {len(entry)} books built, grid has {len(counts)}")
    tag = " (partial)" if partial else ""
    print(f"{tid}: {total}/{expected} chapters across "
          f"{len(entry)}/{len(counts)} books{tag}")
    if partial and entry:
        print(f"       books present: {sorted(int(k) for k in entry)}")
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    errors = []
    out = {}
    for s in SETS:
        e = build_set(s, errors)
        if e:
            out[s["tid"]] = e

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
