# -*- coding: utf-8 -*-
"""Local-model DISAGREEMENT SCREENER for transcription chunk reports.

⚠⚠ THIS IS A SCREEN, NEVER A SOURCE. ⚠⚠

It runs a local vision model (LM Studio, OpenAI-compatible API) over the page
images a chunk was transcribed from, and reports **where the local reading and
our transcription disagree**. It does NOT decide who is right, and its output
must never be written into a chunk file. The local model is expected to be
worse than the transcriber at every individual verse; the point is that its
errors CLUSTER on genuinely hard glyphs, so its disagreements are a cheap
ranked queue for a human or a frontier re-read.

Why this exists: an independent second read of Philemon found ~1 letter-level
correction per 3 verses in a careful first pass, and the Ephesians ø gap ran
48 sites across 4 chapters. Second-reading all 31,102 verses at frontier cost
is not going to happen. Screening all of them locally is free.

    lms server start                       # LM Studio must be serving
    python tools/local_screen.py --file thorlaks_philemon.md --vol 3 --pages 202
    python tools/local_screen.py --file thorlaks_ephesians.md --vol 3 --pages 177-181

## ★★ USE THE FINE-TUNED MODEL: `-l isfrak`

`isfrak.traineddata` in `Hexapla-releases/tessdata/` was fine-tuned on this
very print from the first four completed books (see tools/tesstrain_prep.py).
Measured on 60 held-out lines it never trained on:

    stock Fraktur   mean CER 0.323   median 0.311
    isfrak          mean CER 0.148   median 0.133

Error more than halved, and it emits the actual sorts — ꝥ ⁊ ñ ø þ — where
stock Fraktur produces H, z, #, 0. Screener separation improves with it:

    Philemon vs its own page 202 :  0.723 stock -> 0.809 tuned
    James    vs Philemon page 202:  0.054 stock -> 0.064 tuned  (control)

⚠ 15% CER is a SCREENER, not a transcriber. It is wrong about one character in
seven. Nothing it emits may be pasted into a chunk file, ever.
⚠ Trained and evaluated on v3 (NT) pages only — same fount, same scan run.
Generalisation to v1/v2 is UNTESTED; re-measure before trusting it there.
⚠ Its ground truth is our own transcription, so it learned our conventions
INCLUDING any errors in them. It cannot be evidence that those were right.
⚠ Training error was still falling at 3000 iterations. Every completed book
adds pairs — retrain periodically rather than treating this as final.

## ★ VALIDATED 2026-08-11 — IT IS A PAGE-LEVEL DETECTOR, NOT A VERSE-LEVEL ONE

Measured with Tesseract 5.4 + `Fraktur.traineddata` against Philemon, whose
25 verses have been independently transcribed AND second-read, so the answer
was known before the test:

    Philemon transcription vs its own page 202 :  0.723
    James    transcription vs Philemon page 202:  0.054   <- negative control

A 13x separation. **That is a decisive detector for the failure that has
actually cost this project weeks**: a chunk that was never transcribed, or was
transcribed from the wrong folio. Glen's fabricated Genesis 33-50 would have
scored like the control.

⚠ It is NOT a verse-level checker. Per-verse scores on that same known-good
page ranged 0.15-0.97 with a median of 0.63 — any threshold flags half the
book. Do not use per-verse output as a to-do list.

⚠ Tesseract's Fraktur model is German and its errors here are SYSTEMATIC, not
random: þ->b, ø->o, ſ->f, ⁊->2. That is why comparison runs on a skeleton that
deliberately collapses those confusion classes. It is also why the raw OCR is
worthless as text and must never be pasted into a chunk file.

⚠ Compare like with like: score a chunk's verses against THE PAGES THOSE
VERSES CAME FROM. Scoring a whole 5-page book against one page reads as a
false alarm (Ephesians vs page 178 alone scores 0.356 while being correct).

## ⚠ WHAT IT CAN AND CANNOT SEE

It normalizes hard before comparing — abbreviation sorts are expanded, ø folds
to o, ij to i, nasal strokes to their expansions — because a local model will
silently expand and normalize whatever it reads, and scoring those as
disagreements would flag every verse. So:

  · CATCHES word-level divergence: a dropped clause, a skipped verse, a
    wrong word, a chunk that was never transcribed.
  · DOES NOT CATCH the ø/o, f/p or ſ/f decisions. Those need band zoom and a
    same-page comparison, which is a human/frontier job. A clean screen is
    NOT evidence that the letterforms are right.

## GPU note

CosyVoice holds ~5.9 GB of this machine's 8 GB while a narration render runs.
Run this when the GPU is free, or the model will not load. To pause a render:
create `narration/logs/PAUSE_<lang>` FIRST, then kill the process — a
scheduled keepalive revives it otherwise.
"""
import argparse
import base64
import difflib
import io
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
ENDPOINT = "http://localhost:1234/v1"
CHAPTER_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
VERSE_RE = re.compile(r"^(\d+)\s+(\S.*)$")

PROMPT = (
    "This is one line from a 1644 Icelandic Bible printed in blackletter. "
    "Transcribe exactly the letters you see, left to right. Output ONLY the "
    "transcribed line, nothing else — no translation, no commentary, no "
    "explanation. If part is illegible write ?? for that part."
)

# Fold the campaign's sorts to a plain-letter skeleton so that a local model's
# silent expansion is not scored as a disagreement. See the docstring caveat.
FOLD = {
    "ꝥ": "þ", "ꝑ": "fyrer", "⁊": "og", "ʒ": "z", "ſ": "s", "ꝛ": "r",
    "ø": "o", "æ": "ae", "ä": "a", "ö": "o", "ü": "u", "ÿ": "i",
    "ñ": "nn", "ũ": "um", "ã": "am", "ẽ": "em", "õ": "om", "m̃": "onum",
    "þ": "th", "ð": "d",
}


def fold(s):
    s = s.lower()
    for k, v in FOLD.items():
        s = s.replace(k, v)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ij", "i").replace("j", "i").replace("w", "v")
    return re.sub(r"[^a-z]+", "", s)


def parse_chunk(path):
    """-> [(book, chapter, verse_no, text)] in file order."""
    out, book, ch = [], None, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = CHAPTER_RE.match(line)
        if m:
            book, ch = m.group(1).strip(), int(m.group(2))
            continue
        if book is None:
            continue
        m = VERSE_RE.match(line)
        if m:
            out.append((book, ch, int(m.group(1)), m.group(2).strip()))
    return out


def line_boxes(page, zoom=2.0, frac=0.65, min_h=4.0):
    """Text-line rectangles in PDF units, found by horizontal ink profile.

    Uses PIL's resize-to-width-1 trick to get a per-row mean cheaply, so this
    needs no numpy. Returns rects covering the full text width.

    ⚠ THE THRESHOLD MUST BE ADAPTIVE. These scans are aged paper: on
    thorlaks_v3 idx 202 the row means run 0.51 (text) to 0.79 (blank), so a
    fixed cutoff anywhere near "dark" calls the ENTIRE page one line — which
    is exactly what a hardcoded 0.93 did on the first attempt. The threshold
    is therefore placed `frac` of the way from the page's own 1st percentile
    to its 98th. frac=0.65 gives 40 lines on v3:202 and 51 on v3:178, both
    right for this print; 0.85 collapses to 7. Re-tune per volume if a page
    reports an implausible line count, and never trust a run of 1.
    """
    from PIL import Image
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
    im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    col = im.resize((1, im.height))
    rows = [col.getpixel((0, y)) / 255.0 for y in range(im.height)]
    s = sorted(rows)
    lo, hi = s[len(s) // 100], s[-max(len(s) // 50, 1)]
    thresh = lo + (hi - lo) * frac
    runs, start = [], None
    for y, v in enumerate(rows):
        dark = v < thresh
        if dark and start is None:
            start = y
        elif not dark and start is not None:
            runs.append((start, y))
            start = None
    if start is not None:
        runs.append((start, len(rows)))
    r = page.rect
    out = []
    for a, b in runs:
        y0, y1 = r.y0 + a / zoom, r.y0 + b / zoom
        if y1 - y0 >= min_h:
            out.append(fitz.Rect(r.x0, y0 - 1.5, r.x1, y1 + 1.5))
    return out


def ask(model, png_bytes, timeout):
    b64 = base64.b64encode(png_bytes).decode()
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
    }).encode()
    req = urllib.request.Request(f"{ENDPOINT}/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"].strip()


def pick_model(explicit):
    try:
        with urllib.request.urlopen(f"{ENDPOINT}/models", timeout=10) as r:
            ids = [m["id"] for m in json.loads(r.read()).get("data", [])]
    except urllib.error.URLError as e:
        sys.exit(f"No LM Studio server on {ENDPOINT} ({e.reason}).\n"
                 f"Start it with:  lms server start")
    if not ids:
        sys.exit("LM Studio is serving but has no model loaded.")
    if explicit:
        if explicit not in ids:
            sys.exit(f"Model {explicit!r} not loaded. Available: {ids}")
        return explicit
    print(f"models loaded: {ids}\nusing: {ids[0]}  "
          f"(⚠ must be a VISION model — a text-only model will return noise)\n")
    return ids[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="chunk report in research/")
    ap.add_argument("--vol", type=int, required=True, choices=(1, 2, 3))
    ap.add_argument("--pages", required=True, help="PDF index, e.g. 202 or 177-181")
    ap.add_argument("--model", default=None)
    ap.add_argument("--zoom", type=float, default=4.0, help="line render zoom")
    ap.add_argument("--limit", type=int, default=0, help="stop after N lines")
    ap.add_argument("--flag-below", type=float, default=0.55)
    ap.add_argument("--timeout", type=int, default=180)
    a = ap.parse_args()

    chunk = RESEARCH / a.file
    if not chunk.exists():
        sys.exit(f"no such chunk report: {chunk}")
    verses = parse_chunk(chunk)
    if not verses:
        sys.exit(f"{a.file} holds no parseable verse lines")

    model = pick_model(a.model)
    lo, _, hi = a.pages.partition("-")
    idxs = list(range(int(lo), int(hi or lo) + 1))

    doc = fitz.open(RESEARCH / f"thorlaks_v{a.vol}.pdf")
    local_parts = []
    n = 0
    for idx in idxs:
        page = doc[idx]
        boxes = line_boxes(page)
        print(f"idx {idx}: {len(boxes)} text lines", flush=True)
        for i, box in enumerate(boxes):
            if a.limit and n >= a.limit:
                break
            png = page.get_pixmap(matrix=fitz.Matrix(a.zoom, a.zoom),
                                  clip=box).tobytes("png")
            try:
                txt = ask(model, png, a.timeout)
            except Exception as e:                      # noqa: BLE001
                print(f"  line {i}: ERROR {e}", flush=True)
                continue
            n += 1
            local_parts.append(txt)
            print(f"  [{idx}:{i:02d}] {txt[:96]}", flush=True)
        if a.limit and n >= a.limit:
            break
    doc.close()

    if not local_parts:
        sys.exit("no lines were read — nothing to compare")

    local = fold(" ".join(local_parts))
    print(f"\nlocal reading: {len(local)} folded chars from {n} lines")

    # Monotonic walk: verses are in print order, so scan forward with a cursor.
    print(f"\n{'ref':<18}{'score':>7}  our text (folded head)")
    print("-" * 78)
    rows, cur = [], 0
    for book, ch, vno, text in verses:
        ours = fold(text)
        if len(ours) < 8:
            continue
        window = local[cur:cur + max(len(ours) * 4, 300)]
        if not window:
            break
        sm = difflib.SequenceMatcher(None, ours, window, autojunk=False)
        m = sm.find_longest_match(0, len(ours), 0, len(window))
        score = (2.0 * m.size) / (len(ours) + max(m.size, 1))
        ratio = difflib.SequenceMatcher(
            None, ours, window[m.b:m.b + len(ours)], autojunk=False).ratio()
        score = max(score, ratio)
        rows.append((score, f"{book} {ch}:{vno}", text))
        if m.size > 12:
            cur += m.b + m.size
    rows.sort(key=lambda r: r[0])
    for score, ref, text in rows:
        mark = "  <-- CHECK" if score < a.flag_below else ""
        print(f"{ref:<18}{score:>7.2f}  {fold(text)[:44]}{mark}")

    flagged = [r for r in rows if r[0] < a.flag_below]
    print("-" * 78)
    print(f"{len(rows)} verses compared, {len(flagged)} below {a.flag_below}")
    print("\n⚠ Disagreements are a QUEUE, not a verdict. Re-read the page at "
          "band zoom before changing a single letter of a chunk file.\n"
          "⚠ A clean screen says nothing about ø/o, f/p or ſ/f — those are "
          "folded away before comparison by design.")


if __name__ == "__main__":
    main()
