# -*- coding: utf-8 -*-
"""Merge per-page Þorláksbiblía part files into one canonical book file.

    python tools/thorlaks_merge_parts.py --book Hebrews                # DRY RUN
    python tools/thorlaks_merge_parts.py --book Hebrews --apply

## Why this exists

A book is read by several agents at once, one per page range, because a single
agent reading 10 pages dies to a transient API error and loses the lot. Each
writes its OWN file under research/_parts/ so concurrent writers cannot clobber
one another; this script is the join step.

⚠ The join is NOT concatenation. A chapter routinely spans a page boundary, so
two parts can each carry a `## <Book> N` heading for the SAME chapter. Blindly
concatenating emits the heading twice, and tools/thorlaks_corpus_audit.py
resets its key on every heading — so the second occurrence silently REPLACES
the first chapter's verse list instead of extending it, and the audit then
reports a short chapter that is actually complete. This script merges by
(chapter, verse) instead and reports every overlap and gap it finds.

⚠ DRY RUN IS THE DEFAULT and the existing canonical file is never overwritten
without a timestamped .bak — a merge is a bulk edit over hours of vision work.

Output obeys exactly what the corpus audit parses:
  * a chapter heading is `## <Book> <N>` alone on its line
  * a verse begins at column 0 with its printed numeral, then whitespace
Everything else (page tables, findings, PROGRESS lines) is carried into an
appendix so no agent's evidence is lost.
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path("C:/Projects/Hexapla-releases/research")
PARTS = RESEARCH / "_parts"

# ⚠⚠ AGENTS DO NOT WRITE THE HEADING THE AUDIT PARSES, AND THE FAILURE IS SILENT.
# thorlaks_corpus_audit.py matches ONLY `## <Book> <N>` (its CHAPTER_RE below).
# Left to themselves, chunk agents write `## Chapter 8 (continued) - verses
# 14(cont)-39`, `## Chapter 1 - KJV 25 verses`, and so on. None of those match,
# so the audit counts ZERO verses for the book and reports it as untranscribed
# while hours of correct vision work sit in the file. Measured 2026-09-03 on
# romans_p144-145 (0 chapters, 0 verses) and on thorlaks_1peter.md, which an
# agent had written straight to the canonical path.
# ▶ So NORMALISE here, at the join, rather than trusting every agent to obey a
# format: accept what agents actually write, emit only what the audit reads.
AUDIT_CHAPTER_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
LOOSE_CHAPTER_RE = re.compile(
    r"^##+\s*(?:[^A-Za-z0-9]*\s*)?(?:Chapter|Cap\.?|Kafli)\s+(\d+)", re.I)


def chapter_of(line, book):
    """-> chapter number, for any heading style an agent has actually used."""
    m = LOOSE_CHAPTER_RE.match(line)
    if m:
        return int(m.group(1))
    m = AUDIT_CHAPTER_RE.match(line)
    if m and m.group(1).strip().lower() == book.strip().lower():
        return int(m.group(2))
    return None


CHAPTER_RE = AUDIT_CHAPTER_RE
VERSE_RE = re.compile(r"^(\d+)\s+\S")
# romans_p144-145.md / johannine_p213.md -> sort key on the FIRST page number
PAGE_RE = re.compile(r"_p(\d+)")


def parse_part(path, book):
    """-> (chapters {ch: {verse: [lines]}}, prose [lines])."""
    chapters, prose = {}, []
    ch = None
    verse = None
    for line in path.read_text(encoding="utf-8").splitlines():
        c = chapter_of(line, book)
        if c is not None:
            ch, verse = c, None
            chapters.setdefault(ch, {})
            continue
        if ch is None:
            prose.append(line)
            continue
        if line.startswith("#"):
            ch, verse = None, None
            prose.append(line)
            continue
        v = VERSE_RE.match(line)
        if v:
            verse = int(v.group(1))
            chapters[ch].setdefault(verse, [])
            chapters[ch][verse].append(line)
            continue
        if verse is not None:
            chapters[ch][verse].append(line)      # continuation line
        else:
            prose.append(line)
    return chapters, prose


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True,
                    help="book name as it appears in the '## <Book> <N>' headings")
    ap.add_argument("--prefix", help="part-file prefix (default: book name lowercased, spaces stripped)")
    ap.add_argument("--out", help="override the canonical output path")
    ap.add_argument("--apply", action="store_true", help="actually write (default is a dry run)")
    a = ap.parse_args()

    prefix = a.prefix or a.book.lower().replace(" ", "")
    parts = sorted(PARTS.glob(f"{prefix}_p*.md"),
                   key=lambda p: int(PAGE_RE.search(p.name).group(1)))
    if not parts:
        print(f"NO PART FILES matching {PARTS}\{prefix}_p*.md")
        sys.exit(2)

    print(f"book   : {a.book}")
    print(f"parts  : {len(parts)}")
    for p in parts:
        print(f"    {p.name}")

    merged, prose, conflicts = {}, [], []
    for p in parts:
        chs, pr = parse_part(p, a.book)
        prose.append((p.name, pr))
        for ch, verses in chs.items():
            for v, lines in verses.items():
                if v in merged.setdefault(ch, {}):
                    old = "\n".join(merged[ch][v]).strip()
                    new = "\n".join(lines).strip()
                    if old != new:
                        conflicts.append((ch, v, p.name))
                    continue                       # first writer wins; conflict reported
                merged[ch][v] = lines

    total = sum(len(v) for v in merged.values())
    print(f"\nchapters: {len(merged)}   verses: {total}")
    for ch in sorted(merged):
        nums = sorted(merged[ch])
        gaps = [n for n in range(1, max(nums) + 1) if n not in merged[ch]] if nums else []
        flag = f"   ⚠ MISSING {gaps}" if gaps else ""
        print(f"    ch {ch:>3}: {len(nums):>3} verses, {min(nums)}-{max(nums)}{flag}")

    if conflicts:
        print(f"\n⚠⚠ {len(conflicts)} VERSE(S) TRANSCRIBED DIFFERENTLY BY TWO PARTS "
              f"— overlapping page ranges. The FIRST part's text was kept; "
              f"adjudicate these by eye before trusting the merge:")
        for ch, v, name in conflicts[:20]:
            print(f"    ch {ch} v{v}  (also in {name})")

    out = Path(a.out) if a.out else RESEARCH / f"thorlaks_{prefix}.md"
    body = [f"# Þorláksbiblía 1644 — {a.book.upper()} (merged chunk report)", "",
            f"Merged by tools/thorlaks_merge_parts.py from {len(parts)} part files "
            f"on {datetime.now():%Y-%m-%d %H:%M}. Each part was read from page images "
            f"by a separate agent; **the PDF text layer was never consulted.**", ""]
    for ch in sorted(merged):
        body.append(f"## {a.book} {ch}")
        body.append("")
        for v in sorted(merged[ch]):
            body.extend(merged[ch][v])
        body.append("")
    body += ["", "---", "", "# Appendix — per-part notes, page tables and findings", ""]
    for name, pr in prose:
        body += [f"## from {name}", ""] + pr + [""]
    text = "\n".join(body) + "\n"

    if not a.apply:
        print(f"\nDRY RUN — would write {out} ({len(text)} bytes). "
              f"Re-run with --apply to write.")
        return
    if out.exists():
        bak = out.with_suffix(f".md.bak-{datetime.now():%Y-%m-%d-%H%M%S}")
        bak.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\nbacked up existing -> {bak.name}")
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(text)} bytes)")
    print("▶ NOW RUN, and believe the tools rather than this script:")
    print("     python C:/Projects/Hexapla/tools/thorlaks_corpus_audit.py")
    print("     python C:/Projects/Hexapla/tools/thorlaks_variants.py")


if __name__ == "__main__":
    main()
