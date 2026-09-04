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


# ⛔⛔ LOOSE_CHAPTER_RE IS BOOK-BLIND, AND THAT SILENTLY CROSS-CONTAMINATES.
# `## Chapter 2 - verses 1-14` names no book, so it matches whatever --book you
# happen to pass. MEASURED 2026-09-04: merging --book "2 John" over the parts
# 1john_p209-210.md + 1john_p211-212.md + johannine_p213.md returned
# "chapters: 3  verses: 45" - chapters 1 and 2 with 10 and 29 verses. Those are
# 1 JOHN's chapters, harvested out of p209-210's bare `## Chapter N` headings
# and relabelled `## 2 John 1` / `## 2 John 2` in the output. 2 John has ONE
# chapter and 13 verses; the merge reported three chapters and did not complain.
# ▶ books_named() below lets main() SAY SO. It cannot decide for you: a bare
#   `## Chapter N` in a single-book part file is correct and common, which is
#   why the loose match exists at all. Read the warning and check the grid.
BOOKNAME_RE = re.compile(r"^##\s+([0-9]?\s*[A-Za-z][A-Za-z ]*?)\s+(\d+)\b")


def books_named(path):
    """-> set of book names that this part file's headings EXPLICITLY name."""
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if LOOSE_CHAPTER_RE.match(line):
            continue                       # `## Chapter N` names no book
        m = BOOKNAME_RE.match(line)
        if m:
            out.add(" ".join(m.group(1).split()).lower())
    return out


def chapter_of(line, book):
    """-> chapter number, for any heading style an agent has actually used."""
    m = LOOSE_CHAPTER_RE.match(line)
    if m:
        return int(m.group(1))
    m = AUDIT_CHAPTER_RE.match(line)
    if m and m.group(1).strip().lower() == book.strip().lower():
        return int(m.group(2))
    # "## 1 Peter 4 - KJV 19 verses", "## 1 Peter 3 (continued from idx 203-204)".
    # Agents annotate the heading, which defeats AUDIT_CHAPTER_RE above (it
    # anchors the number to END of line). Measured 2026-09-03: this silently
    # dropped 49 of 1 Peter's 105 verses into the appendix - the merge reported
    # 56 and looked plausible. Match the book name, take the next token as the
    # chapter, ignore whatever the agent appended.
    t = line.lstrip("#").strip()
    b = book.strip()
    if t.lower().startswith(b.lower()):
        rest = t[len(b):]
        # Agents separate the book from the chapter every way imaginable:
        # "1 Peter 4 - KJV 19 verses", "1 Peter 3 (continued...)",
        # "3 JOHN - chapter 1 (verses 1-4 confirmed...)". Drop a separator run,
        # then an optional "chapter"/"cap"/"kafli", then take the number.
        rest = rest.lstrip(" 	-:.,)(–—")
        m2 = re.match("(?i)^(?:chapter|cap[.]?|kafli)[ 	]+", rest)
        if m2:
            rest = rest[m2.end():]
        toks = rest.split()
        if toks:
            # ⚠ THE COMMA COST 7 VERSES. romans_p136-137.md heads its scripture
            # `### Romans chapter 1, verses 1-7 (...)`; without "," in this set
            # the token is "1," which is not a digit, chapter_of returns None,
            # and Romans 1:1-7 - the book's OPENING, the whole point of the
            # idx-137 correction - went silently into the appendix. Measured
            # 2026-09-04. Strip every separator an agent has actually used.
            num = toks[0].strip(".:,;)(–—-")
            if num.isdigit():
                return int(num)
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
    ap.add_argument("--prefix", action="append",
                    help="part-file prefix; REPEATABLE. A book can straddle two "
                         "prefixes - measured 2026-09-03: 2 John's verses live in "
                         "BOTH 1john_p211-212.md and johannine_p213.md. Passing one "
                         "prefix would silently leave the other half in the appendix. "
                         "(default: book name lowercased, spaces stripped)")
    ap.add_argument("--out", help="override the canonical output path")
    ap.add_argument("--apply", action="store_true", help="actually write (default is a dry run)")
    a = ap.parse_args()

    prefixes = a.prefix or [a.book.lower().replace(" ", "")]
    seen, parts = set(), []
    for pre in prefixes:
        for f in PARTS.glob(f"{pre}_p*.md"):
            if f.name not in seen:
                seen.add(f.name)
                parts.append(f)
    parts.sort(key=lambda p: int(PAGE_RE.search(p.name).group(1)))
    if not parts:
        pats = ", ".join(f"{pre}_p*.md" for pre in prefixes)
        print(f"NO PART FILES matching {PARTS}\{{{pats}}}")
        sys.exit(2)

    print(f"book   : {a.book}")
    print(f"parts  : {len(parts)}")
    blind, others = [], set()
    for p in parts:
        named = books_named(p)
        others |= {n for n in named if n != a.book.strip().lower()}
        loose = any(LOOSE_CHAPTER_RE.match(l)
                    for l in p.read_text(encoding="utf-8").splitlines())
        if loose:
            blind.append(p.name)
        tag = ""
        if named:
            tag += "   names: " + ", ".join(sorted(named))
        if loose:
            tag += "   ⚠ has book-blind '## Chapter N' headings"
        print(f"    {p.name}{tag}")

    if blind and others:
        print(f"\n⛔⛔ CROSS-BOOK CONTAMINATION IS POSSIBLE IN THIS MERGE — CHECK "
              f"THE PER-CHAPTER COUNTS BELOW AGAINST {a.book.upper()}'s KJV GRID "
              f"BEFORE --apply.")
        print(f"    These parts carry bare '## Chapter N' headings, which name no "
              f"book and are therefore attributed to --book '{a.book}':")
        for n in blind:
            print(f"        {n}")
        print(f"    But headings in this merge set explicitly name other book(s): "
              f"{', '.join(sorted(others))}.")
        print(f"    ▶ If a chapter below does not exist in {a.book}, or its verse "
              f"count belongs to one of those other books, it came from a "
              f"book-blind heading. FIX THE SOURCE PART FILE's heading to read "
              f"'## <Book> <N>', then re-run. Do not --apply through this.")

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

    if a.out:
        out = Path(a.out)
    elif len(prefixes) > 1:
        # Deriving a filename from one of several prefixes would overwrite
        # another book's canonical file. Refuse rather than guess.
        print("\n⛔ several --prefix values given: pass --out explicitly, or this "
              "would derive the output name from one prefix and overwrite the "
              "OTHER book's canonical file.")
        sys.exit(2)
    else:
        out = RESEARCH / f"thorlaks_{prefixes[0]}.md"
    body = [f"# Þorláksbiblía 1644 — {a.book.upper()} (merged chunk report)", "",
            f"Merged by tools/thorlaks_merge_parts.py from {len(parts)} part files "
            f"on {datetime.now():%Y-%m-%d %H:%M}. Each part was read from page images "
            f"by a separate agent; **the PDF text layer was never consulted.**", ""]
    for ch in sorted(merged):
        body.append(f"## {a.book} {ch}")
        body.append("")
        for v in sorted(merged[ch]):
            # ⛔ A VERSE SPLIT ACROSS A SHEET BOUNDARY IS ONE VERSE, NOT TWO.
            # Agents label the resumption with the same numeral at column 0:
            # «8 [O][?] Fyrer Truna vard Abraham hlyden…» then, after the page
            # break, «8 (cont'd) [?] hñ erfa skylde…». parse_part correctly
            # files both under verse 8, but emitting both at column 0 makes the
            # audit count two. MEASURED 2026-09-04: Hebrews 11 reported
            # 29 verses, «duplicate [8, 12]», against a real 27.
            # Only the FIRST line of a verse keeps its numeral at column 0.
            for k, l in enumerate(merged[ch][v]):
                body.append(l if k == 0 or not re.match(r"^\d+\s", l)
                            else "  " + l)
        body.append("")
    body += ["", "---", "", "# Appendix — per-part notes, page tables and findings", ""]
    for name, pr in prose:
        # ⛔ DEMOTE EVERY HEADING CARRIED INTO THE APPENDIX.
        # A part file that straddles a book boundary leaves the OTHER book's
        # `## 3 John 1` heading in this prose, and the corpus audit's
        # CHAPTER_RE is `^##\s+…` — it does not care which file it is in or
        # that it sits under "Appendix". MEASURED 2026-09-04: 3 John's verses
        # were counted out of thorlaks_2john.md's appendix as well as out of
        # thorlaks_3john.md, i.e. the same verses in the corpus twice.
        # `######` still reads as a heading to a human and is invisible to
        # `^##\s`. Verse numerals at column 0 are left alone; without a
        # chapter heading above them the audit has no key to file them under.
        # ⛔ AND INDENT ANY APPENDIX LINE THAT LOOKS LIKE A VERSE.
        # Demoting the headings alone is not enough: the audit does not reset
        # its chapter key at the appendix, so it carries the LAST chapter of
        # the BODY into it and counts verse-shaped prose there as that
        # chapter's verses. MEASURED 2026-09-04: 2timothy_p199.md wraps a
        # sentence as «...Only the / 2 Timothy portion is transcribed here»,
        # and «2 Timothy portion is transcribed here» was counted as
        # 2 Timothy 4:2. Two spaces is invisible to `^(\d+)\s` and to a reader.
        body += [f"###### from {name}", ""]
        for l in pr:
            l = re.sub(r"^#{1,6}(?=\s)", "######", l)
            if re.match(r"^\d+\s+\S", l):
                l = "  " + l
            body.append(l)
        body += [""]
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
