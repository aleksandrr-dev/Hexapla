# -*- coding: utf-8 -*-
"""Find letter-level sites worth a SECOND READ, by measurement. 0 model tokens.

    python tools/thorlaks_variants.py                 # o/ø and f/ꝑ worklists
    python tools/thorlaks_variants.py --charset       # every character used
    python tools/thorlaks_variants.py --pair o,ø --max-ratio 0.25

## Why this exists

The corpus audit counts verse numerals. It is blind to the defect that actually
recurs in this campaign: **the wrong letter**. Ephesians passed 155/155 while
carrying an undetected `ø` defect across four chapters; the Philemon retrofit
found ~1 letter-level correction per 3 verses on a page that had passed every
structural check.

A full second read of 31,102 verses is not affordable. But the two known-bad
classes leave a statistical signature that costs nothing to compute:

  - **o vs ø** - the fount has a distinct stroked `ø` and uses it lexically. At
    2.6x the stroke is not reliably visible, so a chunk can transcribe a whole
    book in plain `o` without noticing the letter exists.
  - **f vs ꝑ** - the barred-p sort. Recorded as *confirmed* = «fyrer» by two
    separate chunks, each with genuine same-page corroboration, and both were
    wrong. It is an f-family sort whose value is context-dependent.

If the SAME word appears both ways in the corpus, one of the two spellings is
probably a misreading - and if one form appears once against forty, the rare one
is the suspect. That is a falsification-shaped query, which is precisely what
this campaign's rules demand and what same-page corroboration cannot give.

⚠⚠ **A VARIANT IS NOT A DEFECT.** The print is genuinely inconsistent with
itself - it sets «Fodur» with a plain o and «ødrum» with a stroke on the SAME
page, and the brief is explicit that this inconsistency is DATA. So this tool
emits a RANKED WORKLIST, never a correction. Nothing here may be applied without
going back to the page.

⚠ It can only see words that occur MORE THAN ONCE in different forms. A book
transcribed uniformly in the wrong letter is invisible to it - that is the
Ephesians failure, and only a second reader catches it.
"""
import argparse
import collections
import io
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
VERSE = re.compile(r"^(\d+)\s+(.*)$")
HEAD = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
# ⚠ THE UNCERTAINTY MARKERS MUST BE EXCLUDED, NOT JUST THE `?` INSIDE THEM.
# Transcribers mark a doubtful glyph inline as `Fodur⟨?ø⟩`. Until 2026-09-03
# this class excluded `?` but not `⟨⟩`, so that tokenised to
# ['Fodur⟨', 'ø⟩'] — `Fodur⟨` never grouped with plain `Fodur`, and EVERY
# marked word silently dropped out of the o/ø grouping. That is the exact
# analysis the markers exist to feed, so the sites needing review were the
# ones being hidden. Colossians alone carries 83 marked sites.
WORD = re.compile(r"[^\s/()\[\]?!.,;:«»⟨⟩]+")

PAIRS = [("o", "\u00f8"), ("f", "\uA751")]   # o/ø, f/ꝑ


def chunk_files():
    return sorted(p for p in RESEARCH.glob("thorlaks_*.md")
                  if not p.name.endswith("_CAMPAIGN.md")
                  and "precampaign" not in p.name)


def verses():
    """-> [(book, chapter, verse, text)] from every chunk file's verse lines."""
    out = []
    for f in chunk_files():
        book, ch = None, None
        for line in io.open(f, encoding="utf-8"):
            h = HEAD.match(line.strip())
            if h:
                book, ch = h.group(1), int(h.group(2))
                continue
            if book is None:
                continue
            m = VERSE.match(line.rstrip("\n"))
            if m:
                out.append((book, ch, int(m.group(1)), m.group(2)))
    return out


def tokens(vs):
    for b, c, v, t in vs:
        for w in WORD.findall(t):
            w = w.strip("\u204a")
            if w:
                yield (b, c, v, w)


def report_pair(vs, plain, marked, max_ratio, limit):
    """Group tokens that differ ONLY by plain-vs-marked and rank by rarity."""
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for b, c, v, w in tokens(vs):
        if marked not in w and plain not in w:
            continue
        key = w.replace(marked, plain)
        groups[key][w].append((b, c, v))
    rows = []
    for key, forms in groups.items():
        if len(forms) < 2:
            continue
        counts = {f: len(hits) for f, hits in forms.items()}
        total = sum(counts.values())
        rare = min(counts, key=counts.get)
        ratio = counts[rare] / total
        if ratio <= max_ratio:
            rows.append((ratio, counts[rare], total, key, rare, counts,
                         forms[rare]))
    rows.sort(key=lambda r: (r[0], -r[2]))
    print(f"\n=== {plain} / {marked} — {len(rows)} site(s) at ratio <= {max_ratio} "
          f"({len(groups)} words touched, {sum(1 for g in groups.values() if len(g) > 1)} "
          f"set both ways) ===")
    if not rows:
        print("  none")
        return
    print("  ratio  rare/total  forms                          where the RARE form sits")
    for ratio, n, total, key, rare, counts, hits in rows[:limit]:
        shown = " ".join(f"{f}\u00d7{c}" for f, c in
                         sorted(counts.items(), key=lambda kv: -kv[1]))
        where = "; ".join(f"{b} {c}:{v}" for b, c, v in hits[:4])
        print(f"  {ratio:5.2f}  {n:>3}/{total:<5}  {shown:<30} {where}")
    if len(rows) > limit:
        print(f"  ... {len(rows) - limit} more (raise --limit)")


def charset(vs):
    """Every character in the verse text, with counts. Catches strays cheaply."""
    cnt = collections.Counter(ch for _, _, _, t in vs for ch in t)
    print(f"\n=== charset — {len(cnt)} distinct characters over "
          f"{sum(cnt.values())} chars ===")
    for ch, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        if ch == " ":
            name = "SPACE"
        else:
            try:
                name = unicodedata.name(ch)
            except ValueError:
                name = "<unnamed>"
        flag = ""
        # A character used a handful of times in a 600-verse corpus is either a
        # rare sort or a typo, and both want eyes on them.
        if n <= 3:
            flag = "   <-- RARE, check it is not a typo"
        print(f"  U+{ord(ch):04X}  {n:>7}  {ch!r:<8} {name}{flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", help="e.g. 'o,\u00f8' (default: both known pairs)")
    ap.add_argument("--max-ratio", type=float, default=0.34,
                    help="report a group when the rarer form is at most this "
                         "share of the group (default 0.34; 0.5 shows every "
                         "word set both ways)")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--charset", action="store_true")
    a = ap.parse_args()

    vs = verses()
    books = sorted({b for b, _, _, _ in vs})
    print(f"{len(vs)} verses across {len(books)} book(s): {', '.join(books)}")
    if a.charset:
        charset(vs)
        return
    pairs = [tuple(a.pair.split(","))] if a.pair else PAIRS
    for plain, marked in pairs:
        report_pair(vs, plain, marked, a.max_ratio, a.limit)
    print("\n\u26a0 A variant is a WORKLIST ENTRY, not a defect. The print is "
          "genuinely\n  inconsistent with itself; go to the page before "
          "changing anything.")


if __name__ == "__main__":
    main()
