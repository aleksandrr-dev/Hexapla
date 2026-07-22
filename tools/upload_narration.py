# -*- coding: utf-8 -*-
"""Upload a generated narration set to archive.org (one item per translation).

    python tools/upload_narration.py wbt --dry-run
    python tools/upload_narration.py wbt

Needs the `internetarchive` package and a configured ~/.config/internetarchive/
ia.ini (the owner's account is already linked).

⚠ OWNER POLICY (2026-07-13, restated 2026-07-21): the owner's personal name
must NOT appear anywhere in the metadata. Credit the project/app, never him.
The account that performs the upload is inherently his, but nothing we WRITE
names him.

Item layout mirrors tools/NARRATION_PLAN.md §6: files land as
<bookIdx>/<chapter>.ogg plus the per-chapter <bookIdx>/<chapter>.json verse
offset sidecars (small, and what makes verse highlighting / tap-to-seek
possible in the app — LibriVox audio cannot do that).
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
APP = "https://aleksandrr-dev.github.io/Hexapla/"

# Per-set metadata. Keep descriptions factual: what the text is, that the
# reading is synthetic, and that everything is free.
SETS = {
    "wbt": {
        "identifier": "hexapla-audio-webster-1833",
        "title": "The Holy Bible, Webster's Revision (1833) — complete audio narration",
        "translation": "Webster's Revision of the King James Bible, 1833",
        "language": "eng",
        "voice": "Kokoro text-to-speech (Apache-2.0), voice am_adam",
        "subject": ["bible", "audiobook", "webster bible", "public domain",
                    "scripture", "christianity", "text to speech",
                    "hexapla", "audio bible"],
    },
    "gnv": {
        "identifier": "hexapla-audio-geneva-1599",
        "title": "The Geneva Bible (1599) — complete audio narration",
        "translation": "Geneva Bible, 1599",
        "language": "eng",
        "voice": "Kokoro text-to-speech (Apache-2.0), voice am_adam",
        "subject": ["bible", "audiobook", "geneva bible", "public domain",
                    "scripture", "christianity", "text to speech",
                    "hexapla", "audio bible"],
    },
    # ⚠ NAME POLICY for sv/ru: BOTH are cloned from real people's consented
    # reference recordings (sv = the owner's friend, ru = the owner). The
    # no-personal-names rule covers them BOTH — credit the consent, never
    # the person. Do not "improve" these descriptions with anyone's name.
    "sv": {
        "identifier": "hexapla-audio-karlxii-1703",
        "title": "Karl XII:s Bibel (1703) — komplett ljudinspelning / complete audio narration",
        "translation": "Karl XII:s Bibel, 1703 (Swedish)",
        "language": "swe",
        "voice": "Chatterbox Multilingual (MIT) — synthetic speech cloned "
                 "from a consented reference recording by a native Swedish "
                 "volunteer",
        "subject": ["bible", "audiobook", "karl xii bibel", "svenska",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
    "ru": {
        "identifier": "hexapla-audio-synodal-1876",
        "title": "Синодальный перевод (1876) — полная аудиозапись / complete audio narration",
        "translation": "Russian Synodal Bible, 1876",
        "language": "rus",
        "voice": "Fun-CosyVoice3 — synthetic speech cloned from a consented "
                 "reference recording by a native Russian volunteer",
        "subject": ["bible", "audiobook", "синодальный перевод", "библия",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
}
# ⚠ ru UPLOAD GATE: do not upload ru until (a) the ~381-chapter leak
# re-render has completed under the fixed RU_STYLES, (b) the leak scanner
# has re-screened the re-rendered set clean, and (c) the NT + apocrypha
# passes are done. Uploading a partially-defective corpus wastes the item's
# reputation and everyone's bandwidth.

DESCRIPTION = """<p>A complete chapter-by-chapter audio narration of
<b>{translation}</b>, produced for <a href="{app}">Hexapla</a>, a free and
offline parallel Bible app for Android.</p>

<p>The underlying translation is in the <b>public domain</b> by age. The
reading is <b>synthetic speech</b>, generated with {voice} — it is not a human
performance, and no narrator is credited because none was involved.</p>

<p>Files are one Ogg audio file per chapter, laid out as
<code>&lt;book&gt;/&lt;chapter&gt;.ogg</code> using the standard 66-book
Protestant order with zero-based book numbering (0 = Genesis, 65 =
Revelation). Each audio file has a matching <code>.json</code> sidecar
listing the start time in milliseconds of every verse, so players can
highlight verses or seek to them directly.</p>

<p>{n_chapters} chapters. Free to use, copy and redistribute. The app that
uses these files is free as well: no advertising, no purchases, no accounts,
and no data collection.</p>"""


def build(set_key, dry_run=False):
    meta_src = SETS[set_key]
    src = NARRATION / set_key
    if not src.is_dir():
        sys.exit(f"no narration directory at {src}")

    oggs = sorted(src.rglob("*.ogg"))
    jsons = sorted(src.rglob("*.json"))
    if not oggs:
        sys.exit(f"no .ogg files under {src}")
    # Every chapter must carry its offsets sidecar, or verse highlighting
    # silently degrades for that chapter in the app.
    missing = [str(o.relative_to(src)) for o in oggs
               if not o.with_suffix(".json").exists()]
    if missing:
        sys.exit(f"{len(missing)} chapters lack a .json sidecar: {missing[:5]}")

    total_bytes = sum(f.stat().st_size for f in oggs + jsons)
    metadata = {
        "mediatype": "audio",
        "collection": "opensource_audio",
        "title": meta_src["title"],
        # ⚠ project credit only — never the owner's personal name.
        "creator": "Hexapla (free offline parallel Bible app)",
        "language": meta_src["language"],
        "subject": meta_src["subject"],
        "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
        "rights": "Translation is public domain by age; the narration audio "
                  "is machine-generated and placed in the public domain.",
        "originalurl": APP,
        "description": DESCRIPTION.format(
            translation=meta_src["translation"], app=APP,
            voice=meta_src["voice"], n_chapters=len(oggs)),
    }

    files = {}
    for f in oggs + jsons:
        files[str(f.relative_to(src)).replace("\\", "/")] = str(f)
    cover = NARRATION / "cover.jpg"
    if cover.exists():
        files["cover.jpg"] = str(cover)

    print(f"item      : {meta_src['identifier']}")
    print(f"files     : {len(files)} ({len(oggs)} chapters + sidecars)")
    print(f"size      : {total_bytes / 1e9:.2f} GB")
    print(f"metadata  : {json.dumps(metadata, ensure_ascii=False, indent=1)}")
    if dry_run:
        print("\nDRY RUN — nothing uploaded.")
        return

    from internetarchive import upload
    res = upload(meta_src["identifier"], files=files, metadata=metadata,
                 retries=6, retries_sleep=20, verbose=True)
    bad = [r for r in res if getattr(r, "status_code", 200) not in (200, None)]
    print(f"\nuploaded {len(res) - len(bad)}/{len(res)} requests, {len(bad)} failed")
    if bad:
        for r in bad[:10]:
            print("  FAILED:", getattr(r, "url", "?"), getattr(r, "status_code", "?"))
        sys.exit(1)
    print(f"\nDONE -> https://archive.org/details/{meta_src['identifier']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("set", choices=sorted(SETS))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    build(a.set, a.dry_run)
