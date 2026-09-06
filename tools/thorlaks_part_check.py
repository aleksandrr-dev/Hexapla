# -*- coding: utf-8 -*-
"""Structurally check Þorláksbiblía chunk part-files against the KJV grid. 0 model tokens.

    python tools/thorlaks_part_check.py --book Matthew
    python tools/thorlaks_part_check.py --file research/_parts/matthew_p13-21.md

## Why this exists

Every defect found in Matthew on 2026-09-06 was found by this check and by
NOTHING ELSE — not by the chunk agent's own review, not by the coverage report,
not by `thorlaks_corpus_audit.py` (which only sees merged books):

  · idx 13-21 — FOUR verses split across page boundaries into two numbered
    lines each (12:4, 14:19, 16:27, 19:10). The agent reported «no merged
    verses». Each made its numeral appear twice.
  · idx 22-31 — Matthew 25:46 DROPPED ENTIRELY. Chapter 25 ran 1-45 contiguous
    with no gap, so only a count against the KJV grid could reveal it.
  · idx 22-31 — 24:2 merged into 24:1 (its numeral was transcribed as the
    Tironian `z`), and 24:15's numeral absent.

⚠⚠ **RUN IT ON EVERY PART FILE BEFORE THE BOOK IS MERGED.** After the merge the
per-chapter evidence is harder to attribute to a page, and the corpus audit
cannot see a verse whose text was silently joined to its neighbour.

## What it checks

  1. verse count per chapter against the KJV grid
  2. duplicate numerals   — the page-boundary-split signature
  3. gaps in the numeral sequence
  4. heading form: `## <Book> <N>` and nothing else. ⛔ `## Chapter N` is the
     old kit skeleton's form and breaks the merge tools; the skeleton was fixed
     2026-09-06 but part-files written before that still carry it.
  5. one verse per line at column 0 (a chunk written line-per-printed-line
     makes every count above meaningless — it is reported first and loudly)
  6. long-s left un-normalised
  7. the ø rate, against the campaign's expected 19-31 % of o-positions

⚠ A LOW ø RATE IS NOT A FAILURE OF THIS SCRIPT'S SUBJECT — it means the read was
done at sheet resolution (6.3x), where the stroke is not resolvable. The fix is
`tools/thorlaks_o_sheets.py`, not a re-read at the same magnification.

⛔ EXIT CODE: non-zero if any chapter has a problem, so this can gate a merge.
A check that cannot run must never look like a check that passed: an unreadable
or heading-less file EXITS NON-ZERO rather than reporting zero problems.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parent.parent
DATA = Path("C:/Projects/Hexapla-releases")
KJV = REPO / "app/src/main/assets/bibles/en_kjv.json"


def kjv_grid(book):
    data = json.loads(KJV.read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) and "books" in data else data
    for b in books:
        name = b.get("name") if isinstance(b, dict) else None
        if name and name.lower() == book.lower():
            chs = b["chapters"] if isinstance(b, dict) else b
            return {i + 1: len(c) for i, c in enumerate(chs)}
    return None


def check(path, book, grid):
    txt = path.read_text(encoding="utf-8")
    lines = txt.split("\n")
    problems = []

    bad_heads = [l for l in lines if re.match(r'^## Chapter \d+', l)]
    extra = [l for l in lines
             if re.match(rf'^## {re.escape(book)} \d+\s*\S', l)
             and not re.match(rf'^## {re.escape(book)} \d+\s*$', l)]

    cur, verses = None, {}
    for l in lines:
        m = re.match(rf'^## (?:{re.escape(book)}|Chapter) (\d+)', l)
        if m:
            cur = int(m.group(1)); verses.setdefault(cur, []); continue
        if l.startswith("## "):
            cur = None; continue
        v = re.match(r'^(\d+) ', l)
        if v and cur is not None:
            verses[cur].append(int(v.group(1)))

    if not verses:
        print(f"⛔ {path.name}: NO CHAPTER HEADINGS RECOGNISED — cannot check this file.")
        return ["no headings"]

    # line-per-printed-line detection: verse lines far fewer than numerals present
    body = [l for l in lines if re.match(r'^\d+ ', l)]
    inline = sum(len(re.findall(r'(?<=[.!?]) \d{1,2} ', l)) for l in body)
    if inline > len(body) * 0.5:
        problems.append("LINE-PER-PRINTED-LINE")
        print(f"⛔⛔ {path.name}: looks written LINE-PER-PRINTED-LINE, not one verse "
              f"per line ({inline} inline numerals in {len(body)} lines).")
        print("    Every count below is meaningless until it is reflowed.")

    print(f"\n=== {path.name} ===")
    for c in sorted(verses):
        vs = verses[c]
        if not vs:
            print(f"  {book} {c:>2}: EMPTY"); problems.append(f"{c} empty"); continue
        exp = grid.get(c)
        dup = sorted({x for x in vs if vs.count(x) > 1})
        lo, hi = min(vs), max(vs)
        gaps = [x for x in range(lo, hi + 1) if x not in vs]
        note = []
        if dup:
            note.append(f"DUPES {dup} (page-boundary split?)")
        if gaps:
            note.append(f"GAPS {gaps}")
        # ⛔ A chapter may only be called "partial" if it sits at the EDGE of
        # this file. Treating any short chapter as partial is what nearly hid
        # Matthew 1:25 (merged into v24) on 2026-09-06: the chapter reported
        # 24/25 and was waved through as a chunk boundary, though chapter 1
        # lies wholly inside its file. A masked defect is worse than a noisy
        # check — an interior chapter that is short is ALWAYS reported.
        # Partial AT THE START only if the text begins mid-chapter, and only in
        # the file's first chapter. Partial AT THE END only in its last chapter.
        # ⛔ Matthew 1 is the FIRST chapter and was still missing its LAST verse
        # (1:25, merged into v24). An "is it an edge chapter" test passes that;
        # only this split test catches it.
        first, last = min(verses), max(verses)
        partial = (c == first and lo > 1) or (c == last and exp and hi < exp)
        edge = partial
        if exp and len(vs) != exp and not partial:
            note.append(f"COUNT {len(vs)}/{exp}"
                        + ("  <-- interior chapter, so this is a REAL gap"
                           if not edge else ""))
        if note:
            problems.append(f"{c}: {'; '.join(note)}")
        tag = "  (partial chapter — chunk boundary)" if partial and not note else ""
        print(f"  {book} {c:>2}: {len(vs):>3}/{exp if exp else '?':<3} "
              f"range {lo}-{hi}  {'; '.join(note) or 'ok'}{tag}")

    if bad_heads:
        problems.append("old `## Chapter N` headings")
        print(f"  ⛔ {len(bad_heads)} heading(s) use the old `## Chapter N` form "
              f"— breaks the merge tools.")
    if extra:
        problems.append("headings carry trailing text")
        print(f"  ⛔ {len(extra)} heading(s) carry trailing text after the number.")

    prog = [l for l in lines if l.startswith("PROGRESS:")]
    if prog:
        problems.append(f"{len(prog)} PROGRESS lines in the file")
        print(f"  ⛔ {len(prog)} `PROGRESS:` line(s) written INTO the transcription "
              f"— those belong on stdout, not in the corpus.")
    orphan = [l for l in lines
              if l and not l.startswith(("#", "|", "-", "PROGRESS", "<!--", "`", "*", ">"))
              and not re.match(r'^\d+ ', l) and not re.match(r'^\s', l)
              and not l.startswith("[") and len(l) > 80]
    if orphan:
        problems.append(f"{len(orphan)} unnumbered text lines")
        print(f"  ⛔ {len(orphan)} long text line(s) carry NO verse numeral — a "
              f"page-boundary tail left on its own line. First: {orphan[0][:60]!r}")

    longs = txt.count("ſ")
    if longs:
        problems.append(f"{longs} long-s")
        print(f"  ⛔ {longs} long-s (ſ) not normalised to plain s.")

    vtext = "\n".join(body)
    o = vtext.count("o") + vtext.count("O")
    oe = vtext.count("ø") + vtext.count("Ø")
    rate = 100 * oe / (o + oe) if (o + oe) else 0
    flag = "  ⚠ FAR below the expected 19-31 % — read at sheet resolution?" if rate < 10 else ""
    print(f"  ø rate: {oe}/{o + oe} o-positions = {rate:.1f} %{flag}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--file")
    a = ap.parse_args()
    if a.file:
        files = [Path(a.file)]
        book = a.book or Path(a.file).stem.split("_")[0].capitalize()
    else:
        if not a.book:
            print("give --book or --file"); sys.exit(2)
        book = a.book
        files = sorted((DATA / "research/_parts").glob(f"{book.lower()}_p*.md"))
        files = [f for f in files if ".bak" not in f.name]
    if not files:
        print(f"⛔ no part files found for {book} — that is a FAILURE, not a pass.")
        sys.exit(1)
    grid = kjv_grid(book)
    if not grid:
        print(f"⛔ {book} not found in the KJV asset; cannot check."); sys.exit(1)
    allp = []
    for f in files:
        allp += check(f, book, grid)
    print(f"\n{len(files)} file(s) checked, {len(allp)} problem(s).")
    sys.exit(1 if allp else 0)


if __name__ == "__main__":
    main()
