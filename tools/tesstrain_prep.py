# -*- coding: utf-8 -*-
"""Build line-image + ground-truth pairs for fine-tuning Tesseract on this print.

    python tools/tesstrain_prep.py --book philemon --chunk thorlaks_philemon.md \
        --vol 3 --pages 202 --out gt

## The alignment problem this solves

Tesseract fine-tuning wants `<line>.png` + `<line>.gt.txt` pairs. Our ground
truth is per-VERSE, and verses do not align to lines — a verse spans lines, and
a line holds the tail of one verse and the head of the next. So the verse
stream has to be cut into line-sized pieces.

The trick: stock Fraktur OCR is wrong about nearly every character of this
print (þ->b, ø->o, ſ->f) but it is roughly RIGHT ABOUT ORDER AND LENGTH. So it
is useless as text and useful as an ANCHOR. We OCR each line, collapse both the
OCR and our transcription into a skeleton that folds away the known confusion
classes, align the skeletons with a monotonic cursor, then emit the ORIGINAL
transcription characters for that span via an index map.

⚠⚠ **MISALIGNED PAIRS ARE WORSE THAN NO PAIRS.** Training on a line image
labelled with the neighbouring line's text teaches the model to hallucinate,
which is the one thing this whole campaign exists to prevent. Every pair is
therefore gated on an alignment confidence, low-confidence lines are DROPPED
rather than guessed, and the coverage is reported so a bad run is visible
instead of silently producing a poisoned corpus.

⚠ Ground truth here is the DIPLOMATIC text: ꝥ, ⁊, ñ, ø, ij are kept as printed.
That is deliberate — a model trained on it learns the actual sorts, which is
exactly what stock Fraktur lacks. It also means the .gt.txt files are only as
good as the chunk, so train only from books that have passed the corpus audit.
"""
import argparse
import difflib
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from local_screen import parse_chunk  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
PREP = RESEARCH / "_prep"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:/Projects/Hexapla-releases/tessdata"

# Confusion classes stock Fraktur systematically gets wrong on this print.
# Collapsing them makes the anchor usable; it is ONLY for alignment.
CLS = {**{c: "b" for c in "þbpÞBP"}, **{c: "o" for c in "øoöÖO"},
       **{c: "s" for c in "ſfsFS"}, **{c: "d" for c in "ðdD"},
       **{c: "i" for c in "ijyÿIJY"}, **{c: "u" for c in "uvwUVW"},
       **{c: "n" for c in "ñnN"}}
DROP = set("⁊z2&Z")


def skeleton(s):
    """-> (skel, index map back into s)."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch in DROP:
            continue
        d = unicodedata.normalize("NFD", ch)
        base = "".join(c for c in d if not unicodedata.combining(c))
        if not base:
            continue
        c = CLS.get(base[0], base[0].lower())
        if "a" <= c <= "z":
            out.append(c)
            idx.append(i)
    return "".join(out), idx


def ocr_line(png, lang="Fraktur"):
    env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
    r = subprocess.run([TESS, str(png), "stdout", "-l", lang, "--psm", "7"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return r.stdout.strip()


def snap(text, a, b):
    """Widen [a,b) to whole words inside text."""
    while a > 0 and not text[a - 1].isspace():
        a -= 1
    while b < len(text) and not text[b].isspace():
        b += 1
    return text[a:b].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="prep subdir under _prep/")
    ap.add_argument("--chunk", required=True, help="chunk report filename")
    ap.add_argument("--vol", type=int, required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--out", default="gt")
    ap.add_argument("--min-conf", type=float, default=0.62)
    ap.add_argument("--min-chars", type=int, default=25)
    a = ap.parse_args()

    verses = parse_chunk(RESEARCH / a.chunk)
    if not verses:
        sys.exit(f"{a.chunk}: no parseable verses")
    # ⚠ INCLUDE THE VERSE NUMERALS. The line images contain the inline arabic
    # verse numbers; a label built from verse text alone omits them, and every
    # pair then teaches the model that those digits are not there. Caught by
    # spot-checking philemon line12, whose image reads "8 Fyrer þui… 9 Þa vil"
    # against a label starting "Fyrer þui". Digits are dropped by skeleton()
    # anyway, so alignment is unaffected.
    gt_text = " ".join(f"{no} {t}" for _, _, no, t in verses)
    gt_skel, gt_idx = skeleton(gt_text)

    lo, _, hi = a.pages.partition("-")
    idxs = list(range(int(lo), int(hi or lo) + 1))
    outdir = PREP / a.out
    outdir.mkdir(parents=True, exist_ok=True)

    kept = dropped = 0
    cur = 0
    report = []
    for idx in idxs:
        pdir = PREP / a.book / f"p{idx}"
        if not pdir.exists():
            sys.exit(f"missing prep dir {pdir} — run prep_chunk.py first")
        lines = sorted(p for p in pdir.glob("line*.png")
                       if re.fullmatch(r"line\d+\.png", p.name))
        for png in lines:
            raw = ocr_line(png)
            osk, _ = skeleton(raw)
            if len(osk) < a.min_chars:
                dropped += 1
                report.append((png.name, 0.0, "too short to align"))
                continue
            win_end = min(len(gt_skel), cur + len(osk) * 3 + 200)
            win = gt_skel[cur:win_end]
            if not win:
                break
            sm = difflib.SequenceMatcher(None, osk, win, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size > 3]
            if not blocks:
                dropped += 1
                report.append((png.name, 0.0, "no anchor"))
                continue
            b0, b1 = blocks[0], blocks[-1]
            s = cur + b0.b
            e = cur + b1.b + b1.size
            conf = difflib.SequenceMatcher(
                None, osk, gt_skel[s:e], autojunk=False).ratio()
            if conf < a.min_conf or e <= s:
                dropped += 1
                report.append((png.name, conf, "below confidence"))
                continue
            gt = snap(gt_text, gt_idx[s], gt_idx[min(e, len(gt_idx) - 1)])
            if len(gt) < a.min_chars:
                dropped += 1
                report.append((png.name, conf, "gt span too short"))
                continue
            stem = f"{a.book}_{idx}_{png.stem}"
            shutil.copyfile(png, outdir / f"{stem}.png")
            (outdir / f"{stem}.gt.txt").write_text(gt + "\n", encoding="utf-8")
            kept += 1
            cur = e
            report.append((png.name, conf, gt[:60]))

    print(f"\n{a.book}: kept {kept}, dropped {dropped} "
          f"({kept / max(kept + dropped, 1):.0%} coverage) -> {outdir}")
    print("\nlowest-confidence kept / dropped lines:")
    for name, conf, note in sorted(report, key=lambda r: r[1])[:12]:
        print(f"  {name:<14}{conf:>6.2f}  {note}")
    print("\n⚠ Spot-check several .gt.txt against their .png before training. "
          "A misaligned pair teaches hallucination.")


if __name__ == "__main__":
    main()
