# -*- coding: utf-8 -*-
"""Upload the KJV apocrypha renders to hexapla-audio-en and index them.

WHY A SEPARATE TOOL
-------------------
`en` is the odd one out and no tool covered it. Everything else this project
renders goes to `audio_index_gen.json` with a `<book>/<chapter>.ogg` layout and
per-verse offsets. The KJV set predates that: it lives on the LibriVox path in
`audio_index.json`, its files are FLAT (`kjv_<book>_<chapter0>.ogg`), and the
item carries no sidecars at all. `upload_narration.py` has sets for wbt, gnv,
sv, cu and ru — never en — so the original 22 gap books were done ad hoc and
left nothing behind. This is that missing tool.

WHAT IT COVERS
--------------
The 8 apocrypha books LibriVox never recorded (114 chapters):
    66 1 Esdras · 67 2 Esdras · 70 Wisdom · 71 Sirach
    78 Additions to Esther · 79 Prayer of Azariah · 80 Susanna
    81 Bel and the Dragon
LibriVox already covers apocrypha books 68, 69, 72, 74, 75 and 76, so those are
deliberately absent — do not "fill" them.

⚠ NAMING IS FLAT AND 0-BASED IN THE FILE, 1-BASED IN THE INDEX:
    file  kjv_71_0.ogg          (book 71, chapter index 0)
    entry [1, 1, ".../kjv_71_0.ogg"]   (chapter 1)
  Getting that off by one silently points every chapter at its neighbour.

⚠ VERSE FOLLOWING IS ESTIMATED, NOT EXACT, on this path. `audio_index.json`
  entries are [first, last, url] with no offsets, so the app falls back to its
  sectionFraction estimate — the same behaviour the other 131 KJV chapters
  already have. We DO hold exact offsets locally; moving KJV to the generated
  path would use them, but that is a separate migration and would mean one
  translation served from two indexes at once.

⚠ queue_derive=False and checksum=True: archive.org queues a task per FILE and
  rations them per access key, so a big upload has to be fed in as the queue
  drains (see tools/upload_when_clear.py). checksum=True makes every re-run
  free — already-present files are skipped.
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "app/src/main/assets"
NARRATION = Path(r"C:\Projects\Hexapla-releases\narration\en")
INDEX = ASSETS / "audio_index.json"
ITEM = "hexapla-audio-en"
BASE = f"https://archive.org/download/{ITEM}"

# The 8 books LibriVox never recorded. NOT the whole apocrypha.
BOOKS = [66, 67, 70, 71, 78, 79, 80, 81]


def local_chapters():
    """{book: [chapter_idx, ...]} for what is actually on disk."""
    out = {}
    for b in BOOKS:
        d = NARRATION / str(b)
        if not d.is_dir():
            continue
        chs = sorted(int(p.stem) for p in d.glob("*.ogg"))
        if chs:
            out[b] = chs
    return out


def expected_chapters():
    """{book: n_chapters} from the asset, so a short render cannot pass."""
    data = json.loads((ASSETS / "bibles/en_kjv.json").read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) else data
    return {b: len(books[b].get("chapters") or []) for b in BOOKS}


def do_upload(dry):
    from internetarchive import upload
    have, want = local_chapters(), expected_chapters()
    files, missing = {}, []
    for b in BOOKS:
        chs = have.get(b, [])
        if len(chs) != want[b]:
            missing.append(f"book {b}: {len(chs)}/{want[b]}")
        for c in chs:
            files[f"kjv_{b}_{c}.ogg"] = str(NARRATION / str(b) / f"{c}.ogg")
    if missing:
        sys.exit("INCOMPLETE, refusing to upload:\n  " + "\n  ".join(missing))
    print(f"item   : {ITEM}")
    print(f"files  : {len(files)} chapters across {len(have)} books")
    if dry:
        for k in list(files)[:4]:
            print(f"   {k}")
        print("\nDRY RUN — nothing uploaded.")
        return
    res = upload(ITEM, files=files, retries=6, retries_sleep=20,
                 verbose=True, checksum=True, queue_derive=False)
    bad = [r for r in res if getattr(r, "status_code", 200) not in (200, None)]
    print(f"\nuploaded {len(res) - len(bad)}/{len(res)} requests, {len(bad)} failed")
    if bad:
        sys.exit(1)


def do_index():
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    have, want = local_chapters(), expected_chapters()
    added = 0
    for b in BOOKS:
        chs = have.get(b, [])
        if len(chs) != want[b]:
            sys.exit(f"book {b} incomplete ({len(chs)}/{want[b]}) — not indexing")
        # [firstChapter, lastChapter, url] with 1-BASED chapter numbers.
        idx[str(b)] = [[c + 1, c + 1, f"{BASE}/kjv_{b}_{c}.ogg"] for c in chs]
        added += len(chs)
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")),
                     encoding="utf-8")
    print(f"indexed {added} chapters across {len(BOOKS)} books -> {INDEX.name}")
    print(f"audio_index.json now covers {len(idx)} books")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--index-only", action="store_true")
    ap.add_argument("--upload-only", action="store_true")
    a = ap.parse_args()
    if not a.index_only:
        do_upload(a.dry_run)
    if not a.upload_only and not a.dry_run:
        do_index()
