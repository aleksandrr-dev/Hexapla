# -*- coding: utf-8 -*-
"""Whole-corpus completeness audit for the Þorláksbiblía chunk reports.

⚠⚠ THIS TOOL EXISTS BEFORE THE FIRST CHUNK, ON PURPOSE.

The Glen Persian campaign learned the hard way that **a chunk report cannot
detect a chunk that did not happen**: `glen_genesis_33-50.md` was a polished
report claiming 572 transcribed verses while holding two verse markers on
disk, and every per-chunk check passed it for three weeks. Only aggregating
the whole corpus against the reference grid found it. So this runs from day
one, and no completeness claim about this campaign is believed without it.

    python tools/thorlaks_corpus_audit.py
    python tools/thorlaks_corpus_audit.py --book 12      # one book, verbose

Exit code is non-zero when anything is missing or unexplained, so it can gate
a build or a handoff note.

## THE CHUNK REPORT FORMAT — this tool defines it

A chunk report is `thorlaks_<something>.md` in the research directory. Inside,
transcribed scripture appears as chapter blocks:

    ## <BookName> <chapter>
    1 <verse text>
    2 <verse text>
    ...

· The `##` line names the book exactly as `en_kjv.json` does ("1 Chronicles",
  "Song of Solomon") followed by the **KJV** chapter number.
· A verse line starts with its number, a space, then the text. Nothing else in
  the file may start with a bare number at line-start inside a chapter block.
· ⚠ Chapters are reported in **KJV coordinates**, not printed-heading ones.
  For 1 Chronicles that means following the marginal "Cap. N" — printed VI is
  reported as chapter 5, and printed V's verses 24-43 are reported as part of
  chapter 4. See THORLAKS_CAMPAIGN.md.
· Prose, tables and commentary outside chapter blocks are ignored, so a report
  can still carry its findings section.
"""
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
KJV = Path(r"C:/Projects/Hexapla/app/src/main/assets/bibles/en_kjv.json")

# Docs in the same directory that are NOT chunk reports.
EXCLUDE = ("campaign", "precampaign", "versified_hunt", "scanhunt", "report")

CHAPTER_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
VERSE_RE = re.compile(r"^(\d+)\s+\S")

# Divergences already pinned by the pre-campaign checks. A chapter listed here
# is EXPECTED to differ from the KJV count; anything else is a real finding.
# (book index, chapter) -> (printed count, note)
KNOWN_DIVERGENCE = {
    (22, 9): (20, "printed v20 merges KJV 9:20 and 9:21 — one versemap run"),
}


def load_kjv():
    d = json.loads(KJV.read_text(encoding="utf-8"))
    names = {b["name"]: i for i, b in enumerate(d)}
    counts = [[len(c) for c in b["chapters"]] for b in d]
    return names, counts, [b["name"] for b in d]


def parse(path, names):
    """-> {(bookIdx, chapter): [verse numbers, in file order]}"""
    out = {}
    key = None
    unknown = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = CHAPTER_RE.match(line)
        if m:
            book, ch = m.group(1).strip(), int(m.group(2))
            if book in names:
                key = (names[book], ch)
                out.setdefault(key, [])
            else:
                key = None
                unknown.add(book)
            continue
        if key is None:
            continue
        if line.startswith("#"):
            key = None
            continue
        v = VERSE_RE.match(line)
        if v:
            out[key].append(int(v.group(1)))
    return out, unknown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int, help="report one book index in detail")
    args = ap.parse_args()

    names, counts, booknames = load_kjv()

    # Chunk ranges overlap at their seams: a chapter can appear as a trailing
    # fragment of one chunk AND in full in the chunk that owns it. Keep the
    # BEST copy per chapter, or the fragment manufactures a phantom "short".
    best, sources, unknown_books = {}, {}, set()
    files = 0
    for path in sorted(glob.glob(str(RESEARCH / "thorlaks_*.md"))):
        base = os.path.basename(path).lower()
        if base.endswith(".bak") or any(x in base for x in EXCLUDE):
            continue
        files += 1
        got, unk = parse(path, names)
        unknown_books |= unk
        for key, verses in got.items():
            if not verses:
                continue
            exp = expected(counts, key)
            prev = best.get(key)
            if prev is None or better(verses, prev, exp):
                best[key] = verses
                sources[key] = os.path.basename(path)

    if unknown_books:
        print("⚠ chapter headings naming a book en_kjv.json does not have:")
        for b in sorted(unknown_books):
            print(f"    {b!r}")
        print()

    if files == 0:
        print("No chunk reports found yet — nothing transcribed.")
        print(f"(looked for {RESEARCH}/thorlaks_*.md)")
        return 0

    books = [args.book] if args.book is not None else range(66)
    problems = []
    grand = grand_exp = 0

    print(f"{'book':<18}{'chapters':>10}{'verses':>16}   status")
    print("-" * 62)
    for b in books:
        exp = counts[b]
        have = [c for c in range(1, len(exp) + 1) if (b, c) in best]
        tot = sum(len(best[(b, c)]) for c in have)
        want = sum(exp)
        grand += tot
        grand_exp += want
        if not have:
            continue
        missing = [c for c in range(1, len(exp) + 1) if c not in have]
        bad = []
        for c in have:
            verses = best[(b, c)]
            target, note = expected_pair(counts, (b, c))
            dupes = sorted({v for v in verses if verses.count(v) > 1})
            gaps = [v for v in range(1, target + 1) if v not in verses]
            extra = [v for v in verses if v > target]
            if dupes or gaps or extra:
                bad.append((c, len(verses), target, dupes, gaps, extra, note))
        status = "OK" if not missing and not bad else "!!"
        print(f"{booknames[b]:<18}{len(have):>4}/{len(exp):<5}"
              f"{tot:>8}/{want:<7}   {status}")
        if missing:
            problems.append(f"{booknames[b]}: chapters absent {compress(missing)}")
        for c, got_n, target, dupes, gaps, extra, note in bad:
            bits = []
            if gaps:
                bits.append(f"missing verses {compress(gaps)}")
            if dupes:
                bits.append(f"duplicate {dupes}")
            if extra:
                bits.append(f"beyond count {extra}")
            tag = f"  [{note}]" if note else ""
            problems.append(
                f"{booknames[b]} {c}: {got_n} verses vs {target} expected — "
                + "; ".join(bits) + tag
                + f"   ({sources[(b, c)]})")

        if args.book is not None:
            for c in have:
                print(f"    ch {c:>3}: {len(best[(b, c)]):>3} verses "
                      f"(expect {expected_pair(counts, (b, c))[0]})  "
                      f"{sources[(b, c)]}")

    print("-" * 62)
    print(f"{'TOTAL':<18}{'':>10}{grand:>8}/{grand_exp:<7}")
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print("  · " + p)
        print("\n⚠ Do not report this corpus as complete.")
        return 1
    print("\nNo gaps found in what has been transcribed so far.")
    return 0


def expected(counts, key):
    return expected_pair(counts, key)[0]


def expected_pair(counts, key):
    b, c = key
    if key in KNOWN_DIVERGENCE:
        return KNOWN_DIVERGENCE[key]
    return (counts[b][c - 1] if c - 1 < len(counts[b]) else 0), ""


def better(new, old, exp):
    """Prefer the copy that matches the expected count, else the longer one."""
    if len(new) == exp and len(old) != exp:
        return True
    if len(old) == exp:
        return False
    return len(new) > len(old)


def compress(nums):
    """[1,2,3,7] -> '1-3, 7'"""
    if not nums:
        return ""
    runs, start, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        runs.append((start, prev))
        start = prev = n
    runs.append((start, prev))
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)


if __name__ == "__main__":
    sys.exit(main())
