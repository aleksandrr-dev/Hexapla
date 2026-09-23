# -*- coding: utf-8 -*-
"""Put run-on verses back on their own lines, in the SOURCE part files.

    python tools/thorlaks_split_runons.py --prefix romans              # DRY RUN
    python tools/thorlaks_split_runons.py --prefix romans --apply
    python tools/thorlaks_split_runons.py --all                        # DRY RUN

## Why this exists

Chunk agents write flowing paragraphs with the verse numerals INLINE:

    8 ... Liufer. 9 Endurgiallded ...

Only a numeral at COLUMN 0 is parsed, by thorlaks_merge_parts.py and by
thorlaks_corpus_audit.py alike. Every other verse on that line is invisible to
both. MEASURED 2026-09-03: 3 John's 15 printed verses sit on SIX lines and the
merge captured 5; Romans chapter 2 parsed 4 verses where the agent had
transcribed all 29 and checked them against the KJV grid.

▶ THE TEXT IS NOT LOST. This is a FORMAT problem, not a missing-text problem,
and the audit's "missing verses" line is its detector. Nothing here re-reads a
page or invents a word: it only moves an existing numeral to the start of a
line.

## Why it is conservative, and why --apply is not the default

A regex guessing verse boundaries inside a diplomatic transcription is a silent
bulk mutation of hours of vision work. So a numeral is split out ONLY when all
of these hold:

  * it equals the current verse + 1 (never a jump, never a repeat) - this is
    what stops it firing on «1644», a folio number, or a numeral inside the
    text;
  * it is preceded by whitespace (so it is not part of a longer number or
    glued to the previous word);
  * it is followed by whitespace and then a LETTER (so «12.» in a page table,
    or a numeral ending a line, is left alone);
  * it is inside a verse block - i.e. some column-0 numeral has already been
    seen under a chapter heading. Page tables and findings sections above the
    first verse are never touched.

⚠ It edits the PART FILE, never the merged output: the merge is regenerated
from the parts, so an edit to the merged file is lost on the next --apply.
⚠ A .bak-<timestamp> is written beside every file it changes.
⚠ ALWAYS re-merge and re-audit afterwards, and CHECK THE RESULTING PER-CHAPTER
  COUNTS AGAINST THE KJV GRID. A plausible number is not a verified one.
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path("C:/Projects/Hexapla-releases/research")
PARTS = RESEARCH / "_parts"

VERSE_AT_COL0 = re.compile(r"^(\d+)\s+\S")
HEADING = re.compile(r"^#")
# A line that is plainly not scripture: PROGRESS trails, markdown tables,
# blockquotes, bullets. Agents put verse-looking numerals in tables constantly.
NOT_SCRIPTURE = re.compile(r"^\s*(PROGRESS:|\||>|[-*+]\s|\d+\.\s)")


# ⚠ TWO FALSE POSITIVES, BOTH MEASURED ON THE 2026-09-04 DRY RUN, both in
# 1 Peter - a book that was already 105/105 CORRECT, so either would have
# INVENTED a verse in a finished book:
#   1peter_p203-204: «... ⁊ Frid. [⚠ no separate numeral 2 is printed — see
#       Divergences]» - the agent's note ABOUT a missing numeral, recorded
#       because this print runs 1:1-2 together. Numerals inside [...] are
#       editorial, never scripture.
#   1peter_p205-206: «This is front-matter apparatus for 2 Peter, not
#       scripture» - the numeral is half of a BOOK NAME.
# This is exactly what the dry run exists for. Keep both guards.
BOOKWORD = (r"Peter|John|Timothy|Corinthians|Thessalonians|Kings|Samuel|"
            r"Chronicles|Maccabees|Esdras|Pistill")


def _bracket_spans(line):
    """-> [(start, end)] of bracketed AND quoted runs; numerals inside are notes.

    ⚠ QUOTES MATTER AS MUCH AS BRACKETS. Third false positive, 2026-09-04, in
    2cor_p170-171.md: an editorial note quoting a page-foot catchword —
    «Catchword at foot of p171: **"ar. 4 Og"** — confirms the next page opens…»
    — offered a split at that «4», which is part of the catchword the agent was
    QUOTING, not a verse of the page.
    """
    spans, stack = [], []
    for i, c in enumerate(line):
        if c in "[(":
            stack.append(i)
        elif c in "])" and stack:
            spans.append((stack.pop(), i))
    # Straight and guillemet quotes, paired left-to-right. An unpaired quote
    # protects nothing, which is the safe direction: it proposes the split and
    # the dry run shows it to a human.
    for open_q, close_q in (('"', '"'), ("«", "»"), ("“", "”")):
        idx = [i for i, c in enumerate(line) if c in (open_q, close_q)]
        if open_q == close_q:
            spans += list(zip(idx[0::2], idx[1::2]))
        else:
            o = [i for i, c in enumerate(line) if c == open_q]
            cl = [i for i, c in enumerate(line) if c == close_q]
            spans += [(a, b) for a, b in zip(o, cl) if b > a]
    return spans


# ⚠ THE SCRIPTURE IS ICELANDIC; THE AGENTS' NOTES ARE ENGLISH. That asymmetry
# is the discriminator for a note sitting inside a verse block, and it is what
# finally removed the fourth false positive (2026-09-04, 2cor_p170-171.md):
#   Catchword at foot of p171: **"ar. 4 Og"** — confirms the next page opens
#   completing "ydar" then verse 4 beginning "Og...".
# That line quotes a catchword containing a bare «4» AND says «verse 4» in
# prose, so a quote-span guard only MOVED the false hit to the second numeral.
# ▶ Restricting splits to lines that themselves start with a numeral was tried
#   and is TOO STRICT: agents also hard-wrap a verse across lines, so
#   hebrews_p219.md carries «11 [drop-cap E]nn Christur…» with «12 Ecke» on the
#   NEXT line. Both genuine splits were lost. Continuation lines must stay in
#   scope; only English ones are skipped.
ENGLISH = frozenset("""a an and are as at be by for from has have in is it its not of
on or that the this to was were with verse verse. chapter page line catchword
confirms opens next then beginning otherwise signature area foot""".split())


def is_editorial(line):
    """-> True if this line reads as the agent's own English note, not scripture."""
    toks = [t.strip('.,:;()[]"\'*«»').lower() for t in line.split()[:18]]
    return sum(1 for t in toks if t in ENGLISH) >= 3


def find_split(line, cur):
    """-> index at which verse cur+1 begins inside `line`, or None.

    Deliberately returns the FIRST such site only; the caller re-scans the
    remainder, so a line holding verses 7-11 is split four times, each split
    re-validated against the verse number it just established.
    """
    want = str(cur + 1)
    spans = _bracket_spans(line)
    # ⚠ THE NUMERAL IS NOT ALWAYS PRECEDED BY A SPACE. Measured 2026-09-04 in
    # hebrews_p219.md: «…sm̄ Testamented giörer.17», «…⁊ allt Folked.20»,
    # «…mð Blodenu.22» — the compositor's period runs straight into the next
    # verse numeral. Requiring whitespace before it missed Hebrews 9:17-28 and
    # 10:2-18 entirely, ~30 verses, while the text sat in the file. Accept
    # sentence-final punctuation as a boundary too; the cur+1 test still does
    # the real work of refusing an arbitrary number.
    for m in re.finditer(r"(?<=[\s./])(\d+)(?=\s+[^\W\d_])", line):
        if m.group(1) != want:
            continue
        if any(s <= m.start() <= e for s, e in spans):
            continue                       # editorial note, not a verse
        if re.match(rf"\s+(?:{BOOKWORD})\b", line[m.end():]):
            continue                       # «2 Peter» - half a book name
        return m.start()
    return None


def unwrap(text):
    """Join hard-wrapped verse text back onto its verse line. -> (new_text, n).

    ⚠ SOME AGENTS HARD-WRAP AT ~90 CHARACTERS. hebrews_p219.md writes
        11 [drop-cap E]nn Christur er komen/þ́ hñ sle Byskup epterkomande
        re Tialldbwd/þa ū ecke er med Høndum giörd/… 12 Ecke …
    so a verse numeral can land mid-line OR at the very end of a line, where no
    `numeral + space + letter` test can see it. Nothing is lost — the merge
    files continuation lines under the open verse — but the AUDIT counts one
    verse where the page prints twelve, and the canonical file's verse
    boundaries are wrong.
    ▶ Joined only INSIDE a verse block, and only for a line that is not blank,
    not a heading, not a PROGRESS trail, not an editorial English note, and does
    not itself start with a verse numeral. Everything else is untouched.
    """
    out, n, cur = [], 0, None
    for line in text.split("\n"):
        if HEADING.match(line):
            cur = None
            out.append(line)
            continue
        if not line.strip() or NOT_SCRIPTURE.match(line) or is_editorial(line):
            cur = None if not line.strip() else cur
            out.append(line)
            continue
        if VERSE_AT_COL0.match(line):
            cur = True
            out.append(line)
            continue
        if cur and out:
            out[-1] = out[-1].rstrip() + " " + line.strip()
            n += 1
            continue
        out.append(line)
    return "\n".join(out), n


def process(text):
    """-> (new_text, [(verse, before, after)]) leaving everything else alone."""
    out, splits = [], []
    cur = None
    for line in text.split("\n"):
        if HEADING.match(line):
            cur = None
            out.append(line)
            continue
        if NOT_SCRIPTURE.match(line):
            out.append(line)
            continue
        m = VERSE_AT_COL0.match(line)
        if m:
            cur = int(m.group(1))
        elif cur is None:
            out.append(line)              # prose above the first verse
            continue
        elif is_editorial(line):
            out.append(line)
            continue
        rest = line
        while True:
            i = find_split(rest, cur)
            if i is None:
                break
            head, tail = rest[:i].rstrip(), rest[i:]
            splits.append((cur + 1, head[-46:], tail[:46]))
            out.append(head)
            cur += 1
            rest = tail
        out.append(rest)
    return "\n".join(out), splits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", action="append",
                    help="part-file prefix, e.g. romans. REPEATABLE.")
    ap.add_argument("--all", action="store_true", help="every part file")
    ap.add_argument("--unwrap", action="store_true",
                    help="first join hard-wrapped verse text back onto its "
                         "verse line, then split. Needed where an agent wrapped "
                         "at a fixed width and a numeral landed at a line end.")
    ap.add_argument("--apply", action="store_true",
                    help="actually write (default is a dry run)")
    a = ap.parse_args()

    if a.all:
        files = sorted(PARTS.glob("*.md"))
    elif a.prefix:
        files, seen = [], set()
        for pre in a.prefix:
            for f in sorted(PARTS.glob(f"{pre}_p*.md")):
                if f.name not in seen:
                    seen.add(f.name)
                    files.append(f)
    else:
        print("give --prefix or --all")
        sys.exit(2)
    files = [f for f in files if not f.name.endswith(".bak")
             and ".bak-" not in f.name]
    if not files:
        print("NO PART FILES matched")
        sys.exit(2)

    grand = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        joined = 0
        if a.unwrap:
            text2, joined = unwrap(text)
        else:
            text2 = text
        new, splits = process(text2)
        if not splits and not joined:
            print(f"{f.name}: no run-ons found")
            continue
        if joined:
            print(f"\n{f.name}: {joined} wrapped line(s) joined back onto their "
                  f"verse line")
        grand += len(splits)
        print(f"\n{f.name}: {len(splits)} proposed split(s)")
        for v, before, after in splits:
            print(f"    v{v:<4} ...{before}  ⏐  {after}...")
        if a.apply:
            bak = f.with_name(f"{f.name}.bak-{datetime.now():%Y-%m-%d-%H%M%S}")
            bak.write_text(text, encoding="utf-8", newline="\n")
            f.write_text(new, encoding="utf-8", newline="\n")
            print(f"    wrote {f.name}  (backup {bak.name})")

    print(f"\n{grand} proposed split(s) across {len(files)} file(s)")
    if not a.apply:
        print("DRY RUN — nothing written. Read every line above, then re-run "
              "with --apply.")
    else:
        print("▶ NOW RE-MERGE THE AFFECTED BOOKS AND RE-AUDIT, and check the "
              "per-chapter counts against the KJV grid:")
        print("     python C:/Projects/Hexapla/tools/thorlaks_merge_parts.py "
              "--book <Book> --prefix <prefix> --apply")
        print("     python C:/Projects/Hexapla/tools/thorlaks_corpus_audit.py")


if __name__ == "__main__":
    main()
