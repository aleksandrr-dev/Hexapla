#!/usr/bin/env python
"""
kxii_locate.py - find words on a strip with Tesseract and emit crop boxes for
their diacritics, so a contact sheet can be built WITHOUT hunting coordinates
by eye.

    python tools/kxii_locate.py <strip.png> --pattern "l[aao][:.]?t" --top 0.55
    python tools/kxii_locate.py <strip.png> --pattern "w[aao]l" --json boxes.json

## WHY

Locating a mark by eyeballing a low-magnification crop, estimating pixel
offsets and re-cropping when the box misses cost several retries per page in
manual use. Tesseract is wrong about nearly every DIACRITIC in this fount - it
renders a-ring and a-umlaut as a, o, à, â, ä interchangeably - but it is
reliable about WHERE a word sits. So it is useless as a reading and excellent
as a locator, the same "wrong text, right geometry" trick tesstrain_prep.py
uses for line alignment.

Match patterns therefore have to be diacritic-BLIND. Use a character class
covering every way Tesseract might render the vowel (`l[aaoàâä]t`), or pass
--loose which folds all of a/à/â/ä/å/o to `a` before matching.

⚠ This tool LOCATES. It never decides. The crop it emits still has to be read
at 9x or better, against controls, by the rules in the scan-transcription
skill. A box that misses is visible on the sheet and costs one cheap retry;
a box that is trusted without looking is a fabrication.
"""
import argparse
import json
import os
import re
import subprocess
import sys

TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:\Projects\Hexapla-releases\tessdata"
FOLD = {"à": "a", "â": "a", "ä": "a", "å": "a", "á": "a", "o": "a",
        "ô": "a", "ö": "a", "ó": "a"}


CACHE = r"C:\Projects\Hexapla-releases\research\_ocr_kxii\tsv"


def tsv(image, lang="Fraktur", psm="4"):
    """Word boxes for a strip. Uses the pre-built TSV cache when present.

    Running Tesseract inline over ~120 strips takes minutes and will time out
    a session; the cache is built once in the background (see the handoff) and
    makes every later lookup instant and free.
    """
    cached = os.path.join(CACHE, os.path.splitext(os.path.basename(image))[0] + ".tsv")
    if os.path.isfile(cached):
        text = open(cached, encoding="utf-8", errors="replace").read()
    else:
        env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
        out = subprocess.run(
            [TESS, image, "stdout", "-l", lang, "--psm", psm, "tsv"],
            capture_output=True, env=env,
        )
        text = out.stdout.decode("utf-8", "replace")
    rows = []
    for line in text.splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or not f[11].strip():
            continue
        try:
            rows.append({
                "text": f[11].strip(),
                "left": int(f[6]), "top": int(f[7]),
                "width": int(f[8]), "height": int(f[9]),
                "conf": float(f[10]),
            })
        except ValueError:
            continue
    return rows


def fold(s):
    return "".join(FOLD.get(c, c) for c in s.lower())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--pattern", required=True,
                    help="regex matched against the OCR token")
    ap.add_argument("--loose", action="store_true",
                    help="fold a/o/umlaut/ring to 'a' before matching")
    ap.add_argument("--top", type=float, default=0.55,
                    help="keep this top fraction of the word box (the "
                         "diacritic sits above the x-height); default 0.55")
    ap.add_argument("--pad", type=int, default=8)
    ap.add_argument("--json", help="write contact_sheet.py boxes here")
    ap.add_argument("--label", default="")
    ap.add_argument("--min-conf", type=float, default=-10)
    args = ap.parse_args(argv)

    if not os.path.isfile(TESS):
        raise SystemExit("tesseract not found at %s" % TESS)
    rx = re.compile(args.pattern, re.I)
    hits = []
    for r in tsv(args.image):
        tok = fold(r["text"]) if args.loose else r["text"]
        if r["conf"] < args.min_conf:
            continue
        if not rx.search(tok):
            continue
        h = max(1, int(round(r["height"] * args.top)))
        box = [max(0, r["left"] - args.pad), max(0, r["top"] - args.pad),
               r["left"] + r["width"] + args.pad, r["top"] + h + args.pad]
        hits.append(box + ["%s%s" % (args.label, r["text"])])

    base = os.path.basename(args.image)
    print("%s: %d hit(s) for /%s/" % (base, len(hits), args.pattern))
    for b in hits:
        print("  --box %d,%d,%d,%d,%s" % tuple(b))
    if args.json:
        json.dump(hits, open(args.json, "w", encoding="utf-8"), ensure_ascii=False)
        print("wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
