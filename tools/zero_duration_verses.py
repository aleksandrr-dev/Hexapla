#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""zero_duration_verses.py - find verses that have TEXT but NO AUDIO.

    python tools/zero_duration_verses.py            # every known set
    python tools/zero_duration_verses.py sv wbt     # named sets

## WHY THIS EXISTS - AND WHY tyn_short_verses.py IS NOT ENOUGH

`tyn_short_verses.py` finds verses whose audio is TOO SHORT FOR THEIR TEXT
(chars/sec). That test found sv 8/23 on 2026-08-21 - but only because the
chapter's LAST verse happened to fall inside its rule. The same chapter was
missing **eight** verses, and the same scan reported wbt Psalm 124 and Psalm 139
as clean while each was missing a verse outright.

The signature this looks for is different and more direct: `<ch>.json` holds ONE
offset per verse, so a verse whose offset EQUALS THE NEXT ONE has **zero
duration** - the render never produced it. The chapter's total size and duration
look completely normal, because the defect REPLACES nothing; it simply stops.

## THE FALSE POSITIVE THAT MATTERS

Most identical-offset runs are CORRECT. Several assets carry **empty verses** -
Geneva Job 38/41, Slavonic Exodus 37-39, Wycliffe Numbers 28:30, Tyndale
Matthew 5:47 - where the translation has no text at that number. No text, no
audio, identical offsets, nothing wrong. On 2026-08-21 twelve of sixteen hits
were exactly this.

▶ So a hit is only real when the verse HAS TEXT in the asset. This script checks
that, and cross-checks the `.w.json` word sidecar: a real defect has text,
zero duration, AND no word timings. All three must agree before it is reported.

Exits 1 if any real defect is found, so a wrapper cannot print success over it.
"""
import io
import json
import os
import re
import subprocess
import sys

# The per-chapter offsets file, and nothing else in the directory beside it.
CHAPTER_JSON = re.compile(r"^\d+\.json$")

NARRATION = r"C:\Projects\Hexapla-releases\narration"
BIBLES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app", "src", "main", "assets", "bibles")

# narration set -> the bible asset it was rendered from
SETS = {
    "sv": "sv_karlxii.json",
    "gnv": "en_geneva.json",
    "wbt": "en_webster.json",
    "cu": "cu_elizabeth.json",
    "ru": "ru_synodal.json",
    "wyc": "enm_wycliffe.json",
    "tyn": "en_tyndale.json",
    "en": "en_kjv.json",
    "ylt": "en_ylt.json",
}


def probe_ms(ogg):
    """Audio length in ms, or None if ffprobe cannot say. Never guesses."""
    if not os.path.isfile(ogg):
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", ogg], capture_output=True, text=True).stdout.strip()
        return int(float(out) * 1000)
    except Exception:
        return None


def books_of(asset):
    d = json.load(io.open(os.path.join(BIBLES, asset), encoding="utf-8"))
    return d["books"] if isinstance(d, dict) and "books" in d else d


def scan_set(name):
    """Return (chapters_checked, [defect, ...]). A defect is a dict."""
    asset = SETS.get(name)
    if asset is None:
        raise SystemExit("unknown set %r - known: %s" % (name, ", ".join(sorted(SETS))))
    books = books_of(asset)
    root = os.path.join(NARRATION, name)
    if not os.path.isdir(root):
        raise SystemExit("no such narration dir: %s" % root)

    checked = 0
    defects = []
    for bdir in sorted(os.listdir(root)):
        bpath = os.path.join(root, bdir)
        if not (bdir.isdigit() and os.path.isdir(bpath)):
            continue
        b = int(bdir)
        for fn in sorted(os.listdir(bpath)):
            # ⚠⚠ ALLOWLIST, NOT A BLOCKLIST. The offsets file is exactly
            # `<chapter>.json`; anything else beside it is a sidecar.
            # This used to blocklist `.w.json` and `.eos.json`, and the render
            # gate's NEW `<chapter>.qa.json` (added 2026-09-03) was not on that
            # list — so `int(fn[:-5])` was handed '8.qa' and the ENTIRE scan
            # died with a ValueError. Measured 2026-09-04 on the first repaired
            # ylt chapter. That matters more than an ordinary crash: this is the
            # tool that caught 1 Samuel 28's twelve silent verses when both the
            # count and the size heuristics waved them through, and a
            # just-repaired set is exactly when it has to run. A blocklist
            # breaks again on the next sidecar anyone adds; an allowlist will not.
            if not CHAPTER_JSON.match(fn):
                continue
            c = int(fn[:-5])
            checked += 1
            off = json.load(io.open(os.path.join(bpath, fn), encoding="utf-8"))["offsets"]
            try:
                verses = books[b]["chapters"][c]
            except (IndexError, KeyError):
                defects.append(dict(book=b, chapter=c, verse=0, kind="NO SUCH CHAPTER IN ASSET",
                                    words=0, name="?"))
                continue
            wpath = os.path.join(bpath, fn[:-5] + ".w.json")
            timed = None
            if os.path.isfile(wpath):
                timed = json.load(io.open(wpath, encoding="utf-8")).get("v")

            audio_ms = None
            for i in range(len(off)):
                # duration of verse i: next offset, or end-of-audio for the last
                if i + 1 < len(off):
                    dur = off[i + 1] - off[i]
                else:
                    # ⚠ THE LAST VERSE MUST BE JUDGED ON AUDIO LENGTH, NOT ON THE
                    # WORD SIDECAR. A chapter whose last verse is very short can
                    # legitimately have NO word timings - the aligner's self-check
                    # rejects clips that brief. The 9 fully-null Additions to
                    # Esther chapters in `en` are exactly that, are EXPECTED, and
                    # must not be "fixed". Only real silence counts here.
                    if audio_ms is None:
                        audio_ms = probe_ms(os.path.join(bpath, fn[:-5] + ".ogg"))
                    dur = None if audio_ms is None else audio_ms - off[i]
                    if dur is not None:
                        if dur >= 400:
                            continue  # there IS audio after the last offset
                        # ⚠ a tiny remainder is silence, not a verse. Fold it to 0
                        # so it takes the NO AUDIO branch below - an earlier draft
                        # let 26 ms fall through every branch and vanish, which is
                        # the "a failed check must not look like a pass" trap.
                        dur = 0
                text = str(verses[i]).strip() if i < len(verses) else ""
                if not text:
                    continue                      # empty verse - correct silence
                has_words = bool(timed[i]) if (timed and i < len(timed)) else None
                if dur == 0 and has_words is not False:
                    # zero duration but the aligner did find words: report as suspect
                    defects.append(dict(book=b, chapter=c, verse=i + 1, kind="zero duration (words present - verify)",
                                        words=len(text.split()), name=books[b].get("name", "?")))
                elif dur == 0 and has_words is False:
                    defects.append(dict(book=b, chapter=c, verse=i + 1, kind="NO AUDIO",
                                        words=len(text.split()), name=books[b].get("name", "?")))
                elif dur is None and has_words is False:
                    defects.append(dict(book=b, chapter=c, verse=i + 1, kind="NO AUDIO (last verse)",
                                        words=len(text.split()), name=books[b].get("name", "?")))
    return checked, defects


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    names = argv or sorted(SETS)
    bad_total = 0
    for name in names:
        checked, defects = scan_set(name)
        print("%-5s %4d chapters checked, %d verse(s) with text but no audio"
              % (name, checked, len(defects)))
        for d in defects:
            print("        %-16s %d/%-4d v%-4d %-32s %d words of text"
                  % (d["name"], d["book"], d["chapter"], d["verse"], d["kind"], d["words"]))
        bad_total += len(defects)
    if bad_total:
        print("\n%d VERSE(S) NEED A RE-RENDER. Re-render the affected chapter with:" % bad_total)
        print("    python tools/narrate.py --lang <set> --book <b> --chapter <c> --force")
        print("then DELETE the stale .w.json before re-aligning, or align_words.py skips it.")
        return 1
    print("\nno verse has text without audio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
