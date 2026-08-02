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

✅ ACCEPTED EXCEPTION (owner decision 2026-07-31, "just accept it, it's fine"):
archive.org automatically stamps a publicly-visible `uploader` field with the
uploading account's e-mail — verified live on hexapla-audio-webster-1833 as
`uploader = aleksandr@tuta.com`. It is account-level and CANNOT be set,
overridden or suppressed from here. The owner accepted this rather than
running a second account. DO NOT re-raise it on every new narration set, and
do NOT treat it as licence to relax the rule above: everything this script
writes must still credit the project only. The same decision covers the
`originalurl` / description link to the app's landing page, which carries his
GitHub handle.

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
        "asset": "en_webster.json",
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
        "asset": "en_geneva.json",
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
        "asset": "sv_karlxii.json",
        "identifier": "hexapla-audio-karlxii-1703",
        "title": "Karl XII:s Bibel (1703) — komplett ljudinspelning / complete audio narration",
        # Used automatically while the set covers fewer than its own canon.
        "title_partial": "Karl XII:s Bibel (1703) — ljudinspelning / audio "
                         "narration (pågår / in progress)",
        "translation": "Karl XII:s Bibel, 1703 (Swedish)",
        "language": "swe",
        "voice": "Chatterbox Multilingual (MIT) — synthetic speech cloned "
                 "from a consented reference recording by a native Swedish "
                 "volunteer",
        "cloned": True,
        "watermark": True,   # Chatterbox embeds Resemble's Perth watermark
        "subject": ["bible", "audiobook", "karl xii bibel", "svenska",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
    "ru": {
        "asset": "ru_synodal.json",
        "identifier": "hexapla-audio-synodal-1876",
        "title": "Синодальный перевод (1876) — полная аудиозапись / complete audio narration",
        "translation": "Russian Synodal Bible, 1876",
        "language": "rus",
        "voice": "Fun-CosyVoice3 — synthetic speech cloned from a consented "
                 "reference recording by a native Russian volunteer",
        "cloned": True,      # CosyVoice3 embeds no watermark
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

# The 66-book Protestant canon. Used to decide whether a set may honestly be
# called "complete" — an archive.org item is a public claim, and shipping a
# partial render under a "complete audio narration" title would be false.
#
# ⚠ 1189 IS THE *KJV-GRID* COUNT AND IS NOT UNIVERSAL. A translation on its own
# native versification has its own total: the Russian Synodal canon is 1192
# chapters (Psalm 151, and Daniel 13-14 for the LXX additions), and Slavonic is
# the same shape. Hardcoding 1189 would have flipped ru to the "complete" title
# three chapters early — the honesty gate inverted in the DANGEROUS direction,
# claiming a finished Bible while Psalm 151 and the end of Daniel were missing.
# The real total is therefore read from each set's own asset.
BIBLES = Path("C:/Projects/Hexapla/app/src/main/assets/bibles")
KJV_CANON_CHAPTERS = 1189


def canon_chapters(asset_name):
    """Chapters in the 66-book canon of this asset, on its OWN versification.
    Apocrypha slots (indexes 66+) are excluded: no set renders them today."""
    data = json.loads((BIBLES / asset_name).read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) else data
    return sum(len(b["chapters"]) for b in books[:66])

DESCRIPTION = """<p>{opening} chapter-by-chapter audio narration of
<b>{translation}</b>, produced for <a href="{app}">Hexapla</a>, a free and
offline parallel Bible app for Android.</p>
{progress}
<p>The underlying translation is in the <b>public domain</b> by age. The
reading is <b>synthetic speech</b>, generated with {voice} — it is not a human
performance.{provenance}</p>

<p>Files are one Ogg audio file per chapter, laid out as
<code>&lt;book&gt;/&lt;chapter&gt;.ogg</code> using the standard 66-book
Protestant order with zero-based book numbering (0 = Genesis, 65 =
Revelation). Each audio file has a matching <code>.json</code> sidecar
listing the start time in milliseconds of every verse, so players can
highlight verses or seek to them directly.</p>

<p>{n_chapters} chapters. Free to use, copy and redistribute. The app that
uses these files is free as well: no advertising, no purchases, no accounts,
and no data collection.</p>"""

# The provenance clause differs by how the voice was made, and getting it wrong
# is a public false statement either way:
#   · stock synthetic voice (kokoro am_adam) -> nobody's voice is involved.
#   · CLONED from a consenting volunteer (sv, ru) -> a real person's voice IS
#     the source. Saying "no narrator was involved" there would be false, and
#     it would also contradict the {voice} clause in the same sentence.
# Set "cloned": True on any set whose reference recording came from a person.
PROVENANCE_STOCK = (" No narrator is credited because none was involved.")
# NB: the {voice} clause already states that the voice was cloned from a
# consented recording, so this must not repeat it — it adds only what {voice}
# does not say: the volunteer never read these chapters, and is not named.
PROVENANCE_CLONED = (
    " The volunteer whose voice it reproduces did not read these chapters, "
    "and is not credited by name.")
# Chatterbox (ResembleAI) embeds Resemble's inaudible "Perth" watermark in
# every file it generates. Disclosing it is an obligation recorded in the
# project notes, not an optional nicety — listeners and re-users are entitled
# to know the audio carries a watermark.
WATERMARK_NOTE = (
    " The generated audio carries Resemble AI's inaudible &quot;Perth&quot; "
    "watermark, embedded by the synthesis engine.")

PROGRESS_NOTE = """
<p><b>This narration is still being produced: {n_chapters} of the 1,189
chapters of the 66-book canon are available so far.</b> The remaining chapters
are added to this item as they are rendered, so a book that is absent today may
be present later. Nothing already uploaded changes.</p>
"""


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
    # Honesty gate: only a set covering the whole canon may say "complete".
    expected = canon_chapters(meta_src["asset"])
    is_partial = len(oggs) < expected
    if is_partial and "title_partial" not in meta_src:
        sys.exit(f"{set_key}: {len(oggs)}/{expected} chapters is a "
                 f"PARTIAL set, but SETS['{set_key}'] has no 'title_partial'. "
                 f"Add one rather than publishing a 'complete' title.")
    title = meta_src["title_partial"] if is_partial else meta_src["title"]
    metadata = {
        "mediatype": "audio",
        "collection": "opensource_audio",
        "title": title,
        # ⚠ project credit only — never the owner's personal name.
        "creator": "Hexapla (free offline parallel Bible app)",
        "language": meta_src["language"],
        "subject": meta_src["subject"],
        "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
        "rights": "Translation is public domain by age; the narration audio "
                  "is machine-generated and placed in the public domain.",
        "originalurl": APP,
        "description": DESCRIPTION.format(
            opening="An in-progress" if is_partial else "A complete",
            progress=PROGRESS_NOTE.format(n_chapters=len(oggs))
                     if is_partial else "",
            translation=meta_src["translation"], app=APP,
            provenance=(PROVENANCE_CLONED if meta_src.get("cloned")
                        else PROVENANCE_STOCK)
                       + (WATERMARK_NOTE if meta_src.get("watermark") else ""),
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
    # checksum=True skips files already on the item whose MD5 matches, which
    # makes a re-upload INCREMENTAL. This matters for any set published in
    # stages: Karl XII was uploaded partial at ~940 chapters, so finishing it
    # would otherwise re-send the whole ~1 GB (Geneva's full 1.03 GB took about
    # four hours). A mismatched or missing file is still uploaded, so this
    # cannot silently skip damaged content.
    #
    # ⚠ THE metadata= ARGUMENT ONLY TAKES EFFECT WHEN upload() *CREATES* THE
    # ITEM. On an item that already exists, archive.org ignores the
    # x-archive-meta headers entirely. An earlier version of this comment
    # claimed metadata was "applied regardless, which is what flips a partial
    # title to the complete one" — that was FALSE, and it failed exactly where
    # it mattered: Karl XII finished at 1189/1189 on 2026-08-01 and stayed
    # publicly titled "(pågår / in progress)", the precise inversion the
    # honesty gate exists to prevent. Geneva looked fine only because it was a
    # brand-new item. Metadata must be written explicitly, below.
    res = upload(meta_src["identifier"], files=files, metadata=metadata,
                 retries=6, retries_sleep=20, verbose=True, checksum=True)
    bad = [r for r in res if getattr(r, "status_code", 200) not in (200, None)]
    print(f"\nuploaded {len(res) - len(bad)}/{len(res)} requests, {len(bad)} failed")
    if bad:
        for r in bad[:10]:
            print("  FAILED:", getattr(r, "url", "?"), getattr(r, "status_code", "?"))
        sys.exit(1)
    # Write metadata explicitly, so it lands on new AND pre-existing items.
    # Verified afterwards rather than trusted: a stale "in progress" title on a
    # finished set is a public false claim, and it is the one thing here that
    # no amount of successful file uploads would reveal.
    from internetarchive import get_item
    item = get_item(meta_src["identifier"])
    r = item.modify_metadata(metadata)
    code = getattr(r, "status_code", None)
    if code not in (200, None):
        print(f"\nMETADATA WRITE FAILED: HTTP {code}")
        sys.exit(1)
    live = get_item(meta_src["identifier"]).metadata.get("title", "")
    if live != title:
        print("\n⚠ metadata written but the live title does not match yet:")
        print(f"    want: {title}")
        print(f"    live: {live}")
        print("  archive.org applies metadata edits through its task queue;")
        print("  re-check before treating the item as published.")
    else:
        print(f"\ntitle verified: {live}")

    print(f"\nDONE -> https://archive.org/details/{meta_src['identifier']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("set", choices=sorted(SETS))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    build(a.set, a.dry_run)
