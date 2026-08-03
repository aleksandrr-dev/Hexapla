# -*- coding: utf-8 -*-
"""Fetch, re-encode and index the downloadable music pack.

    python tools/build_music_pack.py --fetch     # download + re-encode
    python tools/build_music_pack.py --index     # write music_index.json
    python tools/build_music_pack.py             # both

Sources and their licences are settled in tools/MUSIC_MOOD_PLAN.md and
Hexapla-releases/research/music_shortlist.md. This script does not decide
anything about rights; it carries the decisions and records the attribution
that has to travel with the audio.

DELIVERY
--------
Files land in Hexapla-releases/music_pack/<mood>/<slug>.mp3 and are uploaded to
archive.org as an APP ASSET PACK, not a music release — a deliberate framing,
recorded in the plan, that keeps a downloadable bundle plainly in the spirit of
"synchronised with other media" rather than looking like a standalone album.

⚠ THE BUNDLED FOUR STAY. They are the offline fallback for EVERY mood, so
nobody loses music by being offline, and a mood whose downloaded track is
missing falls back to a bundled one rather than going quiet — unintended
silence must never look like the deliberate `silence` mood.

RE-ENCODING
-----------
Everything is brought to ~68 kbps to match the bundled tracks. This is a bed
played under speech at a low, perceptually-curved volume; 256 kbps is wasted
bandwidth on a phone. Kevin MacLeod's FAQ explicitly permits re-encoding
("chop, splice, compress, lengthen").
⚠ CC BY-SA sources make the RE-ENCODED FILE an adapted work, which we license
onward as CC BY-SA and credit. That obligation attaches to the audio file, not
to the app: bundling or downloading a track beside an app is mere aggregation.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path("C:/Projects/Hexapla-releases/music_pack")
SRC_DIR = Path("C:/Projects/Hexapla-releases/music_src")
INDEX = ROOT / "app/src/main/assets/music_index.json"
ARCHIVE_ITEM = "hexapla-music-pack"
BITRATE = "68k"

KM_URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/{}"
KM_CATALOGUE = "https://incompetech.com/music/royalty-free/pieces.json"
_km_cache = {}


def km_index():
    """title -> catalogue record, from MacLeod's own pieces.json.

    ⚠ THE FILENAME IS NOT DERIVED FROM THE TITLE. "Jesu, Joy of Man's
    Desiring" is served as "Jesu.mp3". Building the URL from the title happens
    to work for most tracks and 404s on the rest — and a 404 is the GOOD
    outcome; the bad one would be silently fetching a different piece that
    happens to match a title-shaped URL. The catalogue also carries `length`,
    which is used below to verify the download is the piece we asked for.
    """
    if not _km_cache:
        with urllib.request.urlopen(KM_CATALOGUE, timeout=120) as r:
            data = json.load(r)
        items = data if isinstance(data, list) else data.get("pieces", data)
        for x in items:
            title = (x.get("title") or "").strip()
            if title:
                _km_cache[title] = x
    return _km_cache

# (mood, title, source, attribution). Kevin MacLeod only in this pass: his URL
# pattern is deterministic and he composes, performs and records everything
# himself, so ONE grant covers both rights layers. The Marine Band and Buckley
# tracks are decided and will be added once their per-file URLs are collected.
TRACKS = [
    ("awe",       "Ever Mindful",        "km"),
    ("awe",       "Infinite Perspective", "km"),
    ("narrative", "Teller of the Tales",  "km"),
    ("narrative", "Angevin",              "km"),
    ("lament",    "Lamentation",          "km"),
    ("lament",    "Plaint",               "km"),
    ("judgment",  "Dark Times",           "km"),
    ("judgment",  "Oppressive Gloom",     "km"),
    ("judgment",  "Long Note Three",      "km"),
    ("praise",    "Jesu, Joy of Man's Desiring", "km"),
    ("praise",    "Procession of the King", "km"),
    ("wisdom",    "Enchanted Journey",    "km"),
    ("hope",      "Frozen Star",          "km"),
    ("passion",   "Lost Time",            "km"),
    ("tender",    "Canon in D for Two Renaissance Harps", "km"),
]

CREDIT = {
    "km": 'Kevin MacLeod (incompetech.com), CC BY 4.0',
}


def slug(title):
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def source_url(title, src):
    if src == "km":
        rec = km_index().get(title)
        if not rec:
            raise ValueError(f"{title!r} is not in the MacLeod catalogue")
        return KM_URL.format(urllib.parse.quote(rec["filename"]))
    raise ValueError(f"no URL rule for source {src!r}")


def expected_ms(title, src):
    """Catalogue duration, so a download can be checked against what we asked
    for rather than merely checked for being non-empty."""
    if src != "km":
        return None
    rec = km_index().get(title) or {}
    hhmmss = rec.get("length") or ""
    parts = [int(p) for p in hhmmss.split(":")] if hhmmss.count(":") == 2 else None
    if not parts:
        return None
    return ((parts[0] * 60 + parts[1]) * 60 + parts[2]) * 1000


def fetch():
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_in = total_out = 0
    for mood, title, src in TRACKS:
        raw = SRC_DIR / f"{slug(title)}.src.mp3"
        dest_dir = OUT_DIR / mood
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{slug(title)}.mp3"
        if not raw.exists():
            url = source_url(title, src)
            try:
                with urllib.request.urlopen(url, timeout=120) as r, open(raw, "wb") as f:
                    f.write(r.read())
            except Exception as e:
                print(f"  FAILED {title}: {e}")
                continue
        if not dest.exists():
            # -vn drops any cover art; mono would save more but stereo keeps the
            # bed's width, which matters more than a few hundred KB.
            r = subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-i", str(raw), "-vn", "-codec:a", "libmp3lame",
                 "-b:a", BITRATE, "-ar", "44100", str(dest)],
                capture_output=True)
            if r.returncode != 0:
                print(f"  ENCODE FAILED {title}: {r.stderr.decode()[-200:]}")
                continue
        # Integrity: the encoded file must match the catalogue's own duration.
        # Catches a wrong-file fetch, a truncated download and a failed encode
        # in one check — none of which a size test would notice.
        exp = expected_ms(title, src)
        got = duration_ms(dest)
        if exp and abs(exp - got) > 2000:
            print(f"  ⚠ DURATION MISMATCH {title}: catalogue {exp/1000:.0f}s, "
                  f"file {got/1000:.0f}s — not indexing this one")
            dest.unlink(missing_ok=True)
            continue
        a, b = raw.stat().st_size, dest.stat().st_size
        total_in += a; total_out += b
        print(f"  {mood:10} {title[:38]:38} {a/1e6:6.1f} MB -> {b/1e6:5.1f} MB")
    print(f"\nsource {total_in/1e6:.0f} MB -> pack {total_out/1e6:.0f} MB")


def duration_ms(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True)
    try:
        return int(float(r.stdout.decode().strip()) * 1000)
    except Exception:
        return 0


def build_index():
    """mood -> tracks, same shape as audio_index_gen.json so the app's existing
    download path can serve it unchanged."""
    base = f"https://archive.org/download/{ARCHIVE_ITEM}"
    out = {"base": base, "moods": {}, "credits": sorted(set(CREDIT.values()))}
    missing = []
    for mood, title, src in TRACKS:
        f = OUT_DIR / mood / f"{slug(title)}.mp3"
        if not f.exists():
            missing.append(f"{mood}/{slug(title)}")
            continue
        out["moods"].setdefault(mood, []).append({
            "f": f"{mood}/{slug(title)}.mp3",
            "t": title,
            "ms": duration_ms(f),
            "by": CREDIT[src],
        })
    if missing:
        print(f"⚠ {len(missing)} track(s) not built, omitted from the index: "
              f"{missing[:5]}")
    # ⚠ A mood with no downloadable track is NOT an error — the bundled four
    # cover every mood offline. But it should be visible, not silent.
    from_plan = {m for m, _, _ in TRACKS}
    for m in sorted(from_plan - set(out["moods"])):
        print(f"⚠ mood {m!r} has no track in the pack; it will use a bundled one")
    INDEX.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    n = sum(len(v) for v in out["moods"].values())
    print(f"wrote {INDEX} — {n} tracks across {len(out['moods'])} moods")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--index", action="store_true")
    a = ap.parse_args()
    do_all = not (a.fetch or a.index)
    if a.fetch or do_all:
        fetch()
    if a.index or do_all:
        build_index()


if __name__ == "__main__":
    main()
