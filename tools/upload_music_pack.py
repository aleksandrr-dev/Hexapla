# -*- coding: utf-8 -*-
"""Upload the scene-matched music pack to archive.org.

    python tools/upload_music_pack.py --dry-run
    python tools/upload_music_pack.py

⚠ FRAMED AS AN APP ASSET PACK, NOT A MUSIC RELEASE. That is a deliberate
decision recorded in tools/MUSIC_MOOD_PLAN.md, and the wording below is the
point of it: Scott Buckley's site asks that his music not be redistributed
through music distribution services or submitted to streaming platforms. He
grants CC BY 4.0, which permits redistribution, and those restrictions sit
under a pricing table for the PAID tier — but the respectful reading is to
publish this as what it actually is: the background-audio assets for one
application, not an album. Title, description and subjects all say so.

⚠ OWNER POLICY, same as the narration items: no personal name or e-mail in any
field we write. archive.org stamps an `uploader` field automatically from the
account; that is accepted (2026-07-31) and cannot be suppressed from here.

CREDITS ARE NOT OPTIONAL. All three sources require attribution, and two of
them are the reason this item exists in a form we can defend:
  · Kevin MacLeod — CC BY 4.0
  · Scott Buckley — CC BY 4.0
  · U.S. Marine Band — the owner's exact credit line, no more and no less
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PACK = Path("C:/Projects/Hexapla-releases/music_pack")
INDEX = Path(__file__).resolve().parent.parent / "app/src/main/assets/music_index.json"
IDENTIFIER = "hexapla-music-pack"
APP = "https://aleksandrr-dev.github.io/Hexapla/"

DESCRIPTION = """<p>Background music used by <a href="{app}">Hexapla</a>, a free
and offline parallel Bible app for Android. These are <b>application assets</b>,
not a music release: the app plays a quiet instrumental bed underneath its
spoken narration, and selects a track to suit the passage being read.</p>

<p>{n} tracks, {mins} minutes, arranged by mood
(awe, narrative, lament, judgment, praise, wisdom, hope, passion, tender).
Files are re-encoded to a low bitrate deliberately — they are played quietly
under speech, where higher bitrates cost bandwidth without being audible.</p>

<p><b>Credits, as required by the licences:</b></p>
<ul>{credits}</ul>

<p>The app is free: no advertising, no purchases, no accounts, and no data
collection. Music can be turned off entirely in its settings.</p>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not PACK.is_dir():
        sys.exit(f"no pack at {PACK} — run build_music_pack.py first")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))

    files = {}
    for f in sorted(PACK.rglob("*.mp3")):
        files[str(f.relative_to(PACK)).replace("\\", "/")] = str(f)
    if not files:
        sys.exit("pack directory contains no audio")

    # ⚠ Every file the INDEX references must exist, or the app will ask for a
    # track that 404s and fall back to a bundled one without saying why.
    referenced = {t["f"] for v in idx["moods"].values() for t in v}
    referenced |= {t["f"] for t in idx.get("pinned", {}).values()}
    missing = sorted(referenced - set(files))
    if missing:
        sys.exit(f"{len(missing)} indexed track(s) are not in the pack: {missing[:5]}")
    extra = sorted(set(files) - referenced)
    if extra:
        print(f"note: {len(extra)} file(s) in the pack are not indexed "
              f"(harmless, but they will be uploaded): {extra[:3]}")

    n = len(referenced)
    mins = round(sum(t["ms"] for v in idx["moods"].values() for t in v) / 60000)
    total = sum(Path(p).stat().st_size for p in files.values())
    credits = "".join(f"<li>{c}</li>" for c in idx["credits"])

    metadata = {
        "mediatype": "audio",
        "collection": "opensource_audio",
        "title": "Hexapla background music pack (Bible app assets)",
        "creator": "Hexapla (free offline parallel Bible app)",
        "subject": ["hexapla", "app assets", "background music",
                    "instrumental", "creative commons", "bible app"],
        "licenseurl": "https://creativecommons.org/licenses/by/4.0/",
        "rights": ("Individual tracks remain under their own licences and are "
                   "credited in the description; see each source. Assembled as "
                   "application assets for the Hexapla Bible app."),
        "originalurl": APP,
        "description": DESCRIPTION.format(app=APP, n=n, mins=mins, credits=credits),
    }

    print(f"item      : {IDENTIFIER}")
    print(f"files     : {len(files)} ({n} indexed)")
    print(f"size      : {total / 1e6:.0f} MB")
    print(f"metadata  : {json.dumps(metadata, ensure_ascii=False, indent=1)}")
    if args.dry_run:
        print("\nDRY RUN — nothing uploaded.")
        return

    from internetarchive import get_item, upload
    res = upload(IDENTIFIER, files=files, metadata=metadata,
                 retries=6, retries_sleep=20, verbose=True, checksum=True)
    bad = [r for r in res if getattr(r, "status_code", 200) not in (200, None)]
    print(f"\nuploaded {len(res) - len(bad)}/{len(res)} requests, {len(bad)} failed")
    if bad:
        sys.exit(1)

    # ⚠ upload(metadata=...) only applies on item CREATION — the trap that left
    # Karl XII publicly titled "in progress" after it finished. Write it
    # explicitly and verify, every time.
    item = get_item(IDENTIFIER)
    r = item.modify_metadata(metadata)
    code = getattr(r, "status_code", None)
    if code not in (200, None):
        sys.exit(f"metadata write failed: HTTP {code}")
    live = get_item(IDENTIFIER).metadata.get("title", "")
    print(f"title verified: {live}" if live == metadata["title"]
          else f"⚠ title not applied yet (queued): {live!r}")
    print(f"\nDONE -> https://archive.org/details/{IDENTIFIER}")


if __name__ == "__main__":
    main()
