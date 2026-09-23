# -*- coding: utf-8 -*-
"""Locate a Glen 1856 verse on a page of the 1845 first edition.

For the witness adjudication: given (book, chapter, verse) from our 1856
transcription, find which 1845 page carries the same text, so the page can be
rendered and READ.

⚠ THE OCR IS ONLY A LOCATOR. It is far too degraded to adjudicate anything —
measured 2026-08-09, known-good verses score 0.28-0.76 similarity against it,
so no threshold separates a real difference from OCR noise. It is used here for
one thing only: narrowing 1,695 pages to one. Every actual reading is done from
the rendered image.

⚠ The 1845's text layer is REVERSED (RTL stored LTR) and mixes Arabic ي/ك with
Persian ی/ک — both normalised before matching.

    python tools/glen_locate_1845.py --class v9      # the 26-site verse-9 class
    python tools/glen_locate_1845.py --book 29 --chapter 1 --verse 9
"""
import argparse
import csv
import difflib
import io
import os
import pickle
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
sys.path.insert(0, str(RESEARCH))
_argv = sys.argv[:]
sys.argv = ["scan_markers"]
import scan_markers as sm  # noqa: E402
sys.argv = _argv
sys.path.insert(0, str(Path(__file__).parent))
import glen_defect_inventory as inv  # noqa: E402

PDF1845 = RESEARCH / "GlenOldTestamentPersian1845.pdf"
CACHE = RESEARCH / "_1845_ocr.pkl"


def norm(s):
    return s[::-1].replace("ك", "ک").replace("ي", "ی")


def squash(s):
    s = re.sub(r"[\u064b-\u0652\u0640]", "", s)
    return re.sub(r"[^\u0600-\u06ff]", "", s)


def ocr_pages():
    """Reversed-normalised, squashed text of every 1845 page (cached)."""
    if CACHE.exists():
        return pickle.loads(CACHE.read_bytes())
    import fitz
    d = fitz.open(str(PDF1845))
    pages = [squash(norm(d[i].get_text() or "")) for i in range(d.page_count)]
    CACHE.write_bytes(pickle.dumps(pages))
    return pages


def verses_of(path, bidx, chapter):
    """marker -> text for one chapter, walking the file exactly as the scanner
    does so the chapter boundaries are the same ones scan_markers sees.

    ⚠ An earlier version regex-searched the WHOLE FILE for «(۹)» and took the
    longest hit. That returns the same verse for every chapter in the file —
    every Amos site resolved to one page. Track the current chapter properly.
    """
    text = io.open(path, encoding="utf-8").read()
    # restrict to this book's section in a multi-book file
    base = os.path.basename(path)
    if base in inv.MULTI:
        marks = []
        for idx, pat in inv.MULTI[base]:
            s = 0 if pat is None else re.search(pat, text).start()
            marks.append((s, idx))
        marks.sort()
        for i, (s, idx) in enumerate(marks):
            if idx == bidx:
                e = marks[i + 1][0] if i + 1 < len(marks) else len(text)
                text = text[s:e]
                break
        else:
            return {}
    # ⚠ ORDERED BY POSITION, NOT KEYED BY MARKER VALUE. Under the as-printed
    # ruling a defective marker does NOT equal its verse position — Amos 1
    # prints «۱» at both verse 1 and verse 9, so a dict keyed on the glyph
    # merges the two and verse 9 vanishes. These sites are precisely the ones
    # being adjudicated, so the bug would hide every case of interest.
    out, cur = [], None
    for raw in text.splitlines():
        m = sm.CH_RE.match(raw)
        if not m and raw.startswith("#"):
            m2 = sm.CH_RE_PAREN.match(raw.rstrip())
            if m2:
                cur = int(m2.group(2))
                continue
        if m:
            cur = int(m.group(1))
            continue
        if cur != chapter or sm.is_commentary(raw):
            continue
        for mk in re.finditer(r"\(([۰-۹]+)\)([^()]*)", raw):
            out.append((int(mk.group(1).translate(sm.P2A)), mk.group(2)))
    return out


def our_verse(bidx, chapter, verse):
    """Text of one verse from our 1856 chunk reports."""
    for path in sorted(RESEARCH.glob("glen_*.md")):
        if ".bak" in path.name or any(x in path.name for x in inv.EXCLUDE):
            continue
        try:
            vs = verses_of(str(path), bidx, chapter)
        except Exception:
            continue
        # `verse` is a POSITION in the marker run, 1-based.
        if len(vs) >= verse and len(vs) > 3:
            for b, chapters in inv.sections(str(path), None):
                if b == bidx and chapter in chapters:
                    printed, txt = vs[verse - 1]
                    return txt.strip(), f"{path.name} (marker printed «{printed}»)"
    return None, None


def locate(pages, needle, window=None):
    """Best-matching page index for a squashed needle."""
    n = squash(needle)[:120]
    if len(n) < 30:
        return None, 0.0
    best_i, best_r = None, 0.0
    rng = range(len(pages)) if window is None else window
    for i in rng:
        p = pages[i]
        if len(p) < 50:
            continue
        # cheap prefilter: require a distinctive 12-gram to appear
        r = difflib.SequenceMatcher(None, n, p).quick_ratio()
        if r < 0.25:
            continue
        m = difflib.SequenceMatcher(None, n, p)
        _, _, size = m.find_longest_match(0, len(n), 0, len(p))
        score = size / len(n)
        if score > best_r:
            best_i, best_r = i, score
    return best_i, best_r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="klass")
    ap.add_argument("--book", type=int)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--verse", type=int)
    ap.add_argument("--csv", default=str(RESEARCH / "glen_defect_inventory.csv"))
    args = ap.parse_args()

    pages = ocr_pages()
    print(f"1845 OCR cached for {len(pages)} pages\n")

    sites = []
    if args.klass == "v9":
        for r in csv.DictReader(io.open(args.csv, encoding="utf-8")):
            if r["position"] == "9" and r["printed"] == "۱":
                sites.append((int(r["bidx"]), int(r["chapter"]), 9, r["book"]))
    else:
        sites.append((args.book, args.chapter, args.verse, "?"))

    print(f"{'book':<12}{'ref':>8}   {'1845 page':>10}{'match':>7}   source")
    print("-" * 66)
    for bidx, ch, v, name in sites:
        txt, src = our_verse(bidx, ch, v)
        if not txt:
            print(f"{name:<12}{ch}:{v:<6}   {'NO TEXT':>10}")
            continue
        i, r = locate(pages, txt)
        print(f"{name:<12}{str(ch)+':'+str(v):>8}   {str(i):>10}{r:>7.2f}   {src}")


if __name__ == "__main__":
    main()
