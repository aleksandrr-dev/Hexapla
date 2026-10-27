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

⛔ BOOK-ONLY EDITS ARE GUARDED (s46 ruling G1/G2, 2026-10-20). The rebuild comes
from the parts alone, so an edit made only in the book file used to be reverted
silently (Acts: 49 verses + the apparatus section). Now, when the book exists,
every verse whose book text the rebuild would change or drop must belong to a
part named with `--touched <part basename>` (repeatable; thorlaks_chain.py
passes basename(--file)); otherwise all of them are listed and the run exits 4,
writing nothing, in dry run and --apply alike. `--accept-book-regression` is the
explicit override. The section between the «Merged by» line and the first
`## <Book> N` heading is carried forward verbatim. Known-bad controls:
HEXAPLA_NO_MERGE_GUARD=1, HEXAPLA_NO_CARRY_FORWARD=1 (selftest cases 9-12).

Output obeys exactly what the corpus audit parses:
  * a chapter heading is `## <Book> <N>` alone on its line
  * a verse begins at column 0 with its printed numeral, then whitespace
Everything else (page tables, findings, PROGRESS lines) is carried into an
appendix so no agent's evidence is lost.
"""
import argparse
import os
import re
import sys

# The marker an adjudicated part file carries when the PRINT breaks a verse at
# the page foot and the next page owns its tail. ⚠ It must be an explicit
# report by the read - never inferred from punctuation.
SEAM_RE = re.compile(
    r"\[[^\]]*\b(?:breaks off|broke off|continues on|continued on|"
    r"continuation of the verse)\b[^\]]*\]", re.I)
# Looser wording readers actually used for a seam. REPORT-ONLY (see the conflict
# listing in main): never joins, because «continues» also appears in notes.
SEAM_HINT_RE = re.compile(
    r"continues?\b|continuing|cut off|breaks off|runs off|page ends|ends mid|"
    r"mid-word|mid-verse|\(open\b|open —", re.I)
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path("C:/Projects/Hexapla-releases/research")
PARTS = RESEARCH / "_parts"

# ⚠⚠ SELFTEST-ONLY KNOWN-BAD CONTROL. True only while selftest() runs, so it
# can never turn a real merge into a concatenation. See concat_merge().
_IN_SELFTEST = False


def concat_merge():
    """Known-bad control: replace merge-by-(chapter, verse) with naive
    concatenation in page order.

    Reinstates EXACTLY the duplicate-heading defect the docstring describes: a
    chapter spanning a page boundary gets its `## <Book> N` heading emitted
    twice, and thorlaks_corpus_audit.py (which resets its key on every heading)
    then reports a short chapter that is actually complete.

    ⛔ Gated on _IN_SELFTEST so it can never change a real run's merge.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_CONCAT_MERGE") == "1"

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
        # ⛔⛔ ONLY A `##`-LEVEL HEADING ENDS A CHAPTER. A `###` SUB-HEADING DOES NOT.
        # This used to reset on ANY line starting with `#`, and that silently
        # dropped 122 of Matthew's 1071 verses into the appendix — measured
        # 2026-09-07. matthew_p13-21.md heads each page inside the transcription
        # with `### idx 14 (page.png header …)`, so Matthew 12 kept the 4 verses
        # printed before that line and lost the other 46.
        # ⚠ IT LOOKED FINE IN THE GRID. The report said «ch 12: 4 verses, 1-4»,
        # which reads as a legitimately short chunk because the range is
        # CONTIGUOUS — the ⚠ MISSING marker only fires on a hole. Nothing warned.
        # ▶ `##` still resets, because `## Open sites` / `## Divergences` really
        #   do end the scripture; `###` is a page marker inside one.
        if line.startswith("##") and not line.startswith("###"):
            ch, verse = None, None
            prose.append(line)
            continue
        if line.startswith("#"):
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


# ⛔⛔ THE MERGE USED TO REVERT BOOK-ONLY EDITS SILENTLY (s46 ruling G1, Q5-a).
# A merge rebuilds the book from research/_parts/ alone, so every edit made in
# the BOOK file and not in its part - an initials ruling, an in-word fill, a
# β -> ß fix, the «## Reader apparatus» section - is overwritten without a word.
# MEASURED 2026-10-20 on Acts: 49 verses + the apparatus section reverted
# (`.merged-regressed-s45`, 108 diff lines); the class sits in every merged NT
# book but 3 John. ▶ parse_book() reads a canonical book with the EMITTER's own
# grammar (what main() writes below), so the existing book and the rebuild are
# compared like for like; main() then refuses (rc 4) when a verse it would
# change belongs to a part the caller did not name in --touched.
# Known-bad control: HEXAPLA_NO_MERGE_GUARD=1 (the Acts defect, reproduced).
def parse_book(text, book):
    """-> (verses {(ch, v): [lines]}, pre_headings [lines], merged_at, first_ch, lines).

    `pre_headings` = every `## ` line before the first `## <Book> N` heading;
    `merged_at` / `first_ch` = line indices of the «Merged by» line and of that
    first chapter heading (None when absent). The body ends at the emitter's
    level-1 `# Appendix` heading, so appendix prose is never a verse's tail.
    """
    lines = text.split("\n")
    verses, pre = {}, []
    merged_at = first_ch = None
    ch = verse = None
    bk = book.strip().lower()
    for i, line in enumerate(lines):
        m = AUDIT_CHAPTER_RE.match(line)
        if m and m.group(1).strip().lower() == bk:
            if first_ch is None:
                first_ch = i
            ch, verse = int(m.group(2)), None
            continue
        if first_ch is None:
            if merged_at is None and line.startswith("Merged by "):
                merged_at = i
            if line.startswith("## "):
                pre.append(line.rstrip())
            continue
        if line.startswith("# "):
            break                                  # `# Appendix — …`: body ends
        if line.startswith("##") and not line.startswith("###"):
            ch = verse = None                      # parse_part's reset rule
            continue
        if ch is None or line.startswith("#"):
            continue
        v = VERSE_RE.match(line)
        if v:
            verse = int(v.group(1))
            verses.setdefault((ch, verse), []).append(line)
            continue
        if verse is not None:
            verses[(ch, verse)].append(line)       # continuation line
    return verses, pre, merged_at, first_ch, lines


def verse_text(ls):
    """Comparable text of one parsed verse: trailing blanks per line dropped, and
    the blank / `---` lines that separate a chapter or the appendix trimmed."""
    ls = [l.rstrip() for l in ls]
    while ls and ls[-1].strip() in ("", "---"):
        ls.pop()
    while ls and not ls[0].strip():
        ls.pop(0)
    return "\n".join(ls)


def selftest():
    """Control on the merge using synthetic part files in a temp dir.

    ⛔ Never touches C:/Projects/Hexapla-releases/. Drives main() via sys.argv
    and asserts on the PRODUCED OUTPUT TEXT, not on an internal variable.

    ⚠ UNIT NOTE. The tool prints `({len(text)} bytes)` where `text` is a `str`,
    so that number is CHARACTERS, not bytes. The selftest asserts the expected
    value in the SAME unit the tool uses (characters) and pins the distinction
    explicitly — see assertion 8b, which is a FINDING, not a fix.
    """
    global _IN_SELFTEST, RESEARCH, PARTS
    _IN_SELFTEST = True
    fails = []

    def ok(cond, what):
        print(("ok   - " if cond else "FAIL - ") + what, flush=True)
        if not cond:
            fails.append(what)

    import contextlib
    import io
    import shutil
    import tempfile

    saved_research, saved_parts = RESEARCH, PARTS
    td = Path(tempfile.mkdtemp(prefix="merge_parts_selftest_"))
    root = Path(td)
    parts_dir = root / "_parts"
    parts_dir.mkdir()
    out_path = root / "out.md"

    def part(name, text):
        p = parts_dir / name
        p.write_text(text, encoding="utf-8", newline="\n")
        return p

    def run(book, argv_extra=None, apply=True):
        """Drive main() via sys.argv; -> (rc, stdout)."""
        old_argv = sys.argv
        buf = io.StringIO()
        rc = 0
        sys.argv = (["thorlaks_merge_parts.py", "--book", book,
                     "--out", str(out_path)] + (["--apply"] if apply else [])
                    + (argv_extra or []))
        try:
            with contextlib.redirect_stdout(buf):
                main()
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
        except Exception as e:  # noqa: BLE001 - surfaced as a FAIL below
            rc = f"EXC {type(e).__name__}: {e}"
        finally:
            sys.argv = old_argv
        return rc, buf.getvalue()

    def emitted():
        return out_path.read_text(encoding="utf-8") if out_path.exists() else ""

    try:
        RESEARCH, PARTS = root, parts_dir

        # ── 1. the false-positive control: disjoint chapters ───────────────
        part("luke_p10-11.md",
             "## Luke 1\n\n1 First verse of chapter one.\n"
             "2 Second verse of chapter one.\n")
        part("luke_p12-13.md",
             "## Luke 2\n\n1 First verse of chapter two.\n"
             "2 Second verse of chapter two.\n"
             "3 Third verse of chapter two.\n")
        rc, sout = run("Luke")
        txt = emitted()
        h1 = [l for l in txt.splitlines() if l.strip() == "## Luke 1"]
        h2 = [l for l in txt.splitlines() if l.strip() == "## Luke 2"]
        ok(rc == 0 and len(h1) == 1 and len(h2) == 1,
           f"1. disjoint chapters merge clean: no exception, `## Luke 1` and "
           f"`## Luke 2` each emitted exactly once (rc={rc}, h1={len(h1)}, "
           f"h2={len(h2)})")
        ok(all(x in txt for x in ("1 First verse of chapter one.",
                                  "2 Second verse of chapter one.",
                                  "1 First verse of chapter two.",
                                  "3 Third verse of chapter two.")),
           "1b. every verse of both parts is present in page order")

        # ── 2. the straddling chapter — the central case ───────────────────
        out_path.unlink(missing_ok=True)
        part("luke_p10-11.md",
             "## Luke 8\n\n" + "".join(f"{v} Luke 8 verse {v}.\n"
                                       for v in range(1, 21)))
        part("luke_p12-13.md",
             "## Luke 8\n\n" + "".join(f"{v} Luke 8 verse {v}.\n"
                                       for v in range(21, 57)))
        rc, sout = run("Luke")
        txt = emitted()
        h8 = [l for l in txt.splitlines() if l.strip() == "## Luke 8"]
        has1 = "1 Luke 8 verse 1." in txt
        has56 = "56 Luke 8 verse 56." in txt
        ok(rc == 0 and len(h8) == 1 and has1 and has56,
           f"2. straddling chapter: ONE `## Luke 8` heading, verse 1 AND verse "
           f"56 both present (h8={len(h8)}, v1={has1}, v56={has56})")

        # ── 3. loose heading normalisation ─────────────────────────────────
        out_path.unlink(missing_ok=True)
        part("luke_p10-11.md",
             "## Chapter 8 (continued) - verses 14(cont)-39\n\n"
             "14 A verse under a loose heading.\n15 Another verse.\n")
        rc, sout = run("Luke")
        txt = emitted()
        em = [l for l in txt.splitlines()
              if l.startswith("## ") and "Luke" in l and l.strip().endswith("8")]
        clean = bool(em) and re.match(r"^##\s+\S.*\s+\d+\s*$", em[0])
        ok(rc == 0 and clean,
           f"3. loose heading `## Chapter 8 (continued) - verses 14(cont)-39` is "
           f"recognised and re-emitted as the audit form "
           f"(emitted {em[0]!r})" if em else
           f"3. loose heading not recognised/normalised (emitted {em!r})")

        # ── 4. overlap reported, resolved once ─────────────────────────────
        out_path.unlink(missing_ok=True)
        part("luke_p10-11.md",
             "## Luke 8\n\n20 Luke 8 verse 20 from p10.\n21 Tail from p10.\n")
        part("luke_p12-13.md",
             "## Luke 8\n\n20 Luke 8 verse 20 from p12.\n22 Verse 22.\n")
        rc, sout = run("Luke")
        txt = emitted()
        ok("8 v20" in sout and txt.count("20 Luke 8 verse 20") == 1,
           "4. an overlap on 8:20 is REPORTED and the verse appears exactly once "
           f"(reported={'8 v20' in sout}, occurrences="
           f"{txt.count('20 Luke 8 verse 20')})")

        # ── 5. a gap is reported ───────────────────────────────────────────
        out_path.unlink(missing_ok=True)
        # ⚠ The tool scans gaps from verse 1 upward, so a partial chunk prints a
        # huge MISSING list. Emit 1-34 and 36 so the ONLY gap is 35.
        part("luke_p10-11.md",
             "## Luke 8\n\n" + "".join(f"{v} Verse {v}.\n"
                                       for v in list(range(1, 35)) + [36]))
        rc, sout = run("Luke")
        ok("MISSING [35]" in sout,
           f"5. a gap (8:35 in neither part) is reported (MISSING [35] in "
           f"stdout: {'MISSING [35]' in sout})")

        # ── 6. non-scripture carried into the appendix ─────────────────────
        out_path.unlink(missing_ok=True)
        # ⚠⚠ MEASURED SHAPE (this is what the tool actually does, and it is
        # narrower than the docstring implies). A page table / PROGRESS line /
        # findings paragraph is routed to `prose` — and thence to the appendix —
        # only when it sits BEFORE the first chapter heading, or after a `##`
        # level heading that resets the chapter (parse_part: a line with no
        # current chapter is prose). A non-scripture line that follows a VERSE
        # line becomes a CONTINUATION of that verse and stays in the BODY.
        # ▶ The docstring's «everything else is carried into an appendix» is
        # true for pre-heading / post-reset material only. The evidence is still
        # never lost either way — but it is not always in the appendix. See the
        # report; the label is NOT changed here.
        part("luke_p10-11.md",
             "PROGRESS: read page 10\n\n"
             "| col | text |\n| --- | --- |\n| a | b |\n\n"
             "Findings: the ink is faded along the gutter.\n\n"
             "## Open sites\n\n"
             "unplaced ink at the foot of the page\n\n"
             "## Luke 8\n\n1 A verse.\n")
        rc, sout = run("Luke")
        txt = emitted()
        app = txt.split("# Appendix", 1)[-1]
        ok(all(x in app for x in ("PROGRESS: read page 10", "| col | text |",
                                  "the ink is faded along the gutter")),
           "6. pre-heading non-scripture (a page table, a PROGRESS line and a "
           "findings paragraph) is carried into the appendix — nothing dropped")
        ok("unplaced ink at the foot of the page" in app,
           "6b. material AFTER a `## <non-scripture>` heading is also carried "
           "into the appendix (the chapter reset routes it to prose)")

        # ── 6c. FINDING: non-scripture after a verse stays in the body ─────
        out_path.unlink(missing_ok=True)
        part("luke_p10-11.md",
             "## Luke 8\n\n1 A verse.\n\nPROGRESS: read page 10\n")
        rc, sout = run("Luke")
        txt = emitted()
        app = txt.split("# Appendix", 1)[-1]
        body = txt.split("# Appendix", 1)[0]
        ok("PROGRESS: read page 10" in body
           and "PROGRESS: read page 10" not in app,
           "6c. FINDING: non-scripture immediately AFTER a verse is kept in the "
           "BODY as a verse continuation, NOT moved to the appendix (the "
           "docstring's «everything else → appendix» holds only before the "
           "first heading or after a `##` reset; label NOT changed)")

        # ── 7. seam markers ────────────────────────────────────────────────
        out_path.unlink(missing_ok=True)
        # The earlier part marks verse 5 as breaking off; the later part owns
        # its tail. The documented behaviour: JOIN them and DROP the marker.
        part("luke_p10-11.md",
             "## Luke 9\n\n5 Head of verse five "
             "[the verse breaks off at the page foot]\n")
        part("luke_p12-13.md",
             "## Luke 9\n\n5 tail of verse five continues here.\n")
        rc, sout = run("Luke")
        txt = emitted()
        body = txt.split("# Appendix", 1)[0]
        joined = ("JOINED across a page break" in sout
                  and "tail of verse five" in body
                  and "breaks off" not in body)
        # ⚠ Hoisted out of the f-string: an expression spanning a line break
        # inside an f-string is PEP 701 (Python 3.12+) and a SyntaxError on
        # this machine's 3.11.9.
        seam_seen = "JOINED across a page break" in sout
        ok(joined,
           "7. an explicit seam marker JOINs the two halves into one verse and "
           f"drops the marker from the body (seam reported={seam_seen})")
        # ⚠ A bare `-` with NO seam marker must NOT be treated as a seam.
        out_path.unlink(missing_ok=True)
        part("luke_p10-11.md", "## Luke 9\n\n5 Head of verse five -\n")
        part("luke_p12-13.md", "## Luke 9\n\n5 A different reading entirely.\n")
        rc, sout = run("Luke")
        ok("JOINED across a page break" not in sout,
           "7b. a verse ending in a bare `-` with NO seam marker is NOT treated "
           "as a seam (no JOINED block printed)")
        # 7c (s60 F1a): a marker that says «mid-word» joins with NO space; the
        # plain marker of case 7 keeps one. HEXAPLA_NO_MIDWORD=1 = known-bad.
        out_path.unlink(missing_ok=True)
        part("luke_p10-11.md", "## Luke 9\n\n5 Head of verse five z saman "
             "[the verse breaks off at the page foot, mid-word]\n")
        part("luke_p12-13.md", "## Luke 9\n\n5 saßnade ollum here.\n")
        rc, sout = run("Luke")
        body = emitted().split("# Appendix", 1)[0]
        ok(rc == 0 and "z samansaßnade ollum here." in body
           and "breaks off" not in body and "mid-word" not in body,
           f"7c. a «mid-word» seam marker joins with NO space (rc={rc})")
        out_path.unlink(missing_ok=True)
        os.environ["HEXAPLA_NO_MIDWORD"] = "1"
        try:
            rc, sout = run("Luke")
        finally:
            os.environ.pop("HEXAPLA_NO_MIDWORD", None)
        body = emitted().split("# Appendix", 1)[0]
        ok("z saman saßnade ollum here." in body,
           f"7c-bad. KNOWN-BAD HEXAPLA_NO_MIDWORD=1: the space is back (rc={rc})")

        # ── 8. nothing is written by default ───────────────────────────────
        before = {p.name for p in root.rglob("*")}
        out2 = root / "dryrun.md"
        old_argv = sys.argv
        sys.argv = ["thorlaks_merge_parts.py", "--book", "Luke",
                    "--out", str(out2)]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                main()
        except SystemExit:
            pass
        sys.argv = old_argv
        ok(not out2.exists()
           and "DRY RUN" in buf.getvalue()
           and not list(root.rglob("*.bak*")),
           "8. a plain (no --apply) run writes NOTHING and leaves no .bak "
           f"(dryrun.md exists={out2.exists()}, baks="
           f"{[p.name for p in root.rglob('*.bak*')]})")

        # ── 8b. CHARS vs BYTES — a FINDING, pinned not fixed ───────────────
        # The tool prints `len(text)` where text is a str => CHARACTERS, but
        # labels it "bytes". Assert the tool's number equals the CHARACTER
        # count (and generally differs from the UTF-8 byte count when the file
        # carries Þ/á/ø). Do NOT relabel the message.
        out_path.unlink(missing_ok=True)
        part("luke_p10-11.md", "## Luke 8\n\n1 Ðorláks þá á ø.\n")
        rc, sout = run("Luke")
        txt = emitted()
        m = re.search(r"wrote .*\((\d+) characters\)", sout)
        charc = len(txt)
        bytec = len(txt.encode("utf-8"))
        ok(bool(m) and int(m.group(1)) == charc,
           f"8b. FINDING: the printed size is CHARACTERS ({charc}), not bytes "
           f"({bytec}) — the message calls it «bytes» (label NOT changed). "
           f"printed={m.group(1) if m else None}")

        # ── 9-12. the book-only-edit guard (G1) and carry-forward (G2) ─────
        # s46 ruling § 2: a merge rebuilt from the parts silently reverted every
        # edit made only in the book (Acts: 49 verses + the apparatus section).
        def baks():
            return sorted(p.name for p in root.rglob("*.bak*"))

        def fresh_book():
            """Merge two parts into out.md, then hand-edit the BOOK only."""
            for b in list(root.rglob("*.bak*")):
                b.unlink()
            out_path.unlink(missing_ok=True)
            part("luke_p10-11.md", "## Luke 3\n\n1 Alpha.\n2 Beta.\n")
            part("luke_p12-13.md", "## Luke 3\n\n3 Gamma.\n")
            rc0, _ = run("Luke")
            t = emitted()
            out_path.write_text(t.replace("2 Beta.", "2 Beta EDITED IN THE BOOK."),
                                encoding="utf-8", newline="\n")
            return rc0

        def guard_env(name, val):
            if val is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = val

        saved_env = {k: os.environ.get(k) for k in
                     ("HEXAPLA_NO_MERGE_GUARD", "HEXAPLA_NO_CARRY_FORWARD")}
        try:
            for k in saved_env:
                guard_env(k, None)

            # 9. hand edit in the book, its part NOT in --touched -> rc 4, no write
            rc0 = fresh_book()
            before_txt, before_baks = emitted(), baks()
            rc, sout = run("Luke", ["--touched", "luke_p12-13.md"])
            ok(rc0 == 0 and rc == 4
               and "BOOK-ONLY EDIT 3:2 (part luke_p10-11.md) would be REVERTED" in sout
               and emitted() == before_txt and baks() == before_baks == [],
               f"9. a book-only edit outside --touched: rc 4, listed, book unchanged, "
               f"no .bak (rc={rc}, baks={baks()})")
            rc, sout = run("Luke", ["--touched", "luke_p12-13.md"], apply=False)
            ok(rc == 4 and "BOOK-ONLY EDIT 3:2" in sout and "DRY RUN" not in sout,
               f"9b. the same refusal in a DRY RUN (rc={rc})")
            # a verse present in the book and in NO part is listed even when
            # every part is touched
            out_path.write_text(before_txt.replace(
                "3 Gamma.", "3 Gamma.\n4 Delta added by hand."),
                encoding="utf-8", newline="\n")
            rc, sout = run("Luke", ["--touched", "luke_p10-11.md",
                                    "--touched", "luke_p12-13.md"])
            ok(rc == 4 and "BOOK-ONLY EDIT 3:4 (part NONE - in no part) would be "
                           "REVERTED" in sout and "3:2" not in sout,
               f"9c. a verse ABSENT from every part is listed even with all parts "
               f"touched; the touched 3:2 is not (rc={rc})")
            rc, sout = run("Luke", ["--touched", "luke_p12-13.md",
                                    "--accept-book-regression"])
            ok(rc == 0 and "--accept-book-regression GIVEN" in sout
               and "EDITED IN THE BOOK" not in emitted(),
               f"9d. --accept-book-regression writes, loudly (rc={rc})")

            # 9e (s60 F1b): an existing book whose verse carries a seam marker is
            # re-merged with the TAIL part only touched: the joined verse belongs
            # to the head part, and the tail part is its co-owner -> rc 0. With
            # neither part touched -> rc 4. HEXAPLA_NO_SEAMOWNER=1 = known-bad.
            for b in list(root.rglob("*.bak*")):
                b.unlink()
            out_path.unlink(missing_ok=True)
            part("luke_p10-11.md", "## Luke 3\n\n1 Alpha.\n2 Beta head "
                 "[the verse breaks off at the page foot]\n")
            part("luke_p12-13.md", "## Luke 3\n\n3 Gamma.\n")
            run("Luke")
            marker_book = emitted()
            part("luke_p12-13.md", "## Luke 3\n\n2 tail of beta.\n3 Gamma.\n")
            rc, sout = run("Luke", ["--touched", "luke_p12-13.md"])
            ok(rc == 0 and "BOOK-ONLY" not in sout
               and "2 Beta head tail of beta." in emitted(),
               f"9e. a seam JOIN into an existing book with only the TAIL part "
               f"touched: rc 0, joined (rc={rc})")
            out_path.write_text(marker_book, encoding="utf-8", newline="\n")
            rc, sout = run("Luke", ["--touched", "luke_p99.md"])
            ok(rc == 4 and "BOOK-ONLY EDIT 3:2" in sout,
               f"9e-2. the same join with NEITHER part touched: rc 4 (rc={rc})")
            out_path.write_text(marker_book, encoding="utf-8", newline="\n")
            os.environ["HEXAPLA_NO_SEAMOWNER"] = "1"
            try:
                rc, sout = run("Luke", ["--touched", "luke_p12-13.md"])
            finally:
                os.environ.pop("HEXAPLA_NO_SEAMOWNER", None)
            ok(rc == 4 and "BOOK-ONLY EDIT 3:2" in sout,
               f"9e-bad. KNOWN-BAD HEXAPLA_NO_SEAMOWNER=1: the tail-only merge is "
               f"refused again (rc={rc})")

            # 10. same edit, its part IN --touched -> writes
            fresh_book()
            rc, sout = run("Luke", ["--touched", "luke_p10-11.md"])
            ok(rc == 0 and "BOOK-ONLY" not in sout and "2 Beta.\n" in emitted()
               and len(baks()) == 1,
               f"10. the same edit with its part in --touched: writes, .bak taken "
               f"(rc={rc}, baks={baks()})")

            # 11. case 9 under the known-bad switch -> writes (defect reproduced)
            fresh_book()
            guard_env("HEXAPLA_NO_MERGE_GUARD", "1")
            rc, sout = run("Luke", ["--touched", "luke_p12-13.md"])
            guard_env("HEXAPLA_NO_MERGE_GUARD", None)
            ok(rc == 0 and "EDITED IN THE BOOK" not in emitted()
               and "KNOWN-BAD CONTROL ACTIVE: HEXAPLA_NO_MERGE_GUARD=1" in sout,
               f"11. KNOWN-BAD HEXAPLA_NO_MERGE_GUARD=1: the book-only edit is "
               f"silently REVERTED again (rc={rc})")

            # 12. an apparatus block between «Merged by» and `## Luke 3` is
            # re-emitted byte-exact; dropped under HEXAPLA_NO_CARRY_FORWARD=1
            fresh_book()
            t = emitted().replace("2 Beta EDITED IN THE BOOK.", "2 Beta.")
            app_block = ("## Reader apparatus moved out of the verse text (test)\n\n"
                         "Each item names the verse.  \n\n"
                         "- 3:2 (inline) | [a note þ ø]\n")
            i = t.index("## Luke 3")
            t = t[:i] + app_block + "\n" + t[i:]
            out_path.write_text(t, encoding="utf-8", newline="\n")

            def segment(s):
                ls = s.split("\n")
                m_ = next(k for k, l in enumerate(ls) if l.startswith("Merged by "))
                c_ = ls.index("## Luke 3")
                return "\n".join(ls[m_ + 1:c_])
            seg_before = segment(t)
            rc, sout = run("Luke", ["--touched", "luke_p10-11.md"])
            ok(rc == 0 and segment(emitted()) == seg_before
               and app_block in emitted(),
               f"12. the existing apparatus block is re-emitted BYTE-EXACT (rc={rc})")
            guard_env("HEXAPLA_NO_CARRY_FORWARD", "1")
            rc, sout = run("Luke", ["--touched", "luke_p10-11.md"])
            ok(rc == 4 and "BOOK-ONLY HEADING '## Reader apparatus moved out of the "
                           "verse text (test)' would be LOST" in sout
               and app_block in emitted(),
               f"12b. KNOWN-BAD HEXAPLA_NO_CARRY_FORWARD=1: the block is dropped from "
               f"the rebuild, and the guard reports the lost heading (rc={rc})")
            rc, sout = run("Luke", ["--touched", "luke_p10-11.md",
                                    "--accept-book-regression"])
            guard_env("HEXAPLA_NO_CARRY_FORWARD", None)
            ok(rc == 0 and "Reader apparatus" not in emitted()
               and "a note þ ø" not in emitted(),
               f"12c. ... and forced through, the block is GONE from the book (rc={rc})")
        finally:
            for k, val in saved_env.items():
                guard_env(k, val)

    finally:
        RESEARCH, PARTS = saved_research, saved_parts
        shutil.rmtree(td, ignore_errors=True)

    print("", flush=True)
    if concat_merge():
        print("⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_CONCAT_MERGE=1 — naive "
              "concatenation in page order", flush=True)
    print(f"{len(fails)} failure(s)", flush=True)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book",
                    help="book name as it appears in the '## <Book> <N>' headings")
    ap.add_argument("--selftest", action="store_true",
                    help="control on the merge with synthetic part files; never "
                         "reads or writes C:/Projects/Hexapla-releases/")
    ap.add_argument("--prefix", action="append",
                    help="part-file prefix; REPEATABLE. A book can straddle two "
                         "prefixes - measured 2026-09-03: 2 John's verses live in "
                         "BOTH 1john_p211-212.md and johannine_p213.md. Passing one "
                         "prefix would silently leave the other half in the appendix. "
                         "(default: book name lowercased, spaces stripped)")
    ap.add_argument("--out", help="override the canonical output path")
    ap.add_argument("--apply", action="store_true", help="actually write (default is a dry run)")
    ap.add_argument("--touched", action="append", default=[],
                    help="part file basename this merge is FOR; REPEATABLE. A verse "
                         "whose existing book text differs from the rebuild is "
                         "allowed to change only when its owner part is named here "
                         "(thorlaks_chain.py passes basename(--file)). Any other "
                         "difference = a book-only edit the merge would REVERT: rc 4, "
                         "nothing written")
    ap.add_argument("--accept-book-regression", action="store_true",
                    help="write even though book-only edits would be REVERTED "
                         "(explicit override of the rc-4 guard; printed loudly)")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.book:
        ap.error("--book is required (unless --selftest)")

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

    # owner[(ch, v)] = the part that FIRST set merged[ch][v] (a join keeps the
    # head's part) - the unit the --touched guard below reasons in.
    merged, prose, conflicts, joins, owner = {}, [], [], [], {}
    coowner = {}   # F1b (s60): (ch, v) -> parts whose TAIL was joined into the verse
    # ⚠⚠ KNOWN-BAD CONTROL PATH. Under HEXAPLA_CONCAT_MERGE=1 the merge is NAIVE
    # CONCATENATION in page order: each part's chapter blocks are appended as
    # they appear, so a chapter straddling a page boundary emits its
    # `## <Book> N` heading TWICE. Only reachable inside --selftest, because
    # concat_merge() is gated on _IN_SELFTEST.
    concat_blocks = None
    if concat_merge():
        concat_blocks = []
        for p in parts:
            chs, pr = parse_part(p, a.book)
            prose.append((p.name, pr))
            for ch in sorted(chs):
                concat_blocks.append((ch, chs[ch]))
                for v in chs[ch]:
                    owner.setdefault((ch, v), p.name)
        for ch, verses in concat_blocks:
            merged.setdefault(ch, {})       # only so the summary counts exist
            merged[ch].update(verses)
    else:
        for p in parts:
            chs, pr = parse_part(p, a.book)
            prose.append((p.name, pr))
            for ch, verses in chs.items():
                for v, lines in verses.items():
                    if v in merged.setdefault(ch, {}):
                        old = "\n".join(merged[ch][v]).strip()
                        new = "\n".join(lines).strip()
                        # ⛔ A verse the print BREAKS at a page foot is not an
                        # overlap: page N owns its head, page N+1 its tail, and
                        # «first writer wins» DELETES the tail silently. Luke 9:40
                        # is the first (idx 61 head + idx 62 tail). Join them, and
                        # drop the seam marker - it is apparatus, not scripture.
                        # Known-bad control: HEXAPLA_NO_SEAMJOIN=1 restores the
                        # first-wins drop, and the tail disappears again.
                        if (SEAM_RE.search(old)
                                and os.environ.get("HEXAPLA_NO_SEAMJOIN") != "1"):
                            head = SEAM_RE.sub("", old).strip()
                            # ⚠ both halves carry the verse NUMBER at their head -
                            # the tail's is a repeat, and row 46 would then read it
                            # as scripture opening with a digit.
                            tail = re.sub(r"^%d\s+" % v, "", new).strip()
                            head = re.sub(r"\s{2,}", " ", head)
                            # F1a (s60): a marker that says «mid-word» joins with NO space.
                            # Known-bad control: HEXAPLA_NO_MIDWORD=1 keeps the space.
                            joiner = "" if (re.search(r"mid-word", old, re.I)
                                            and os.environ.get("HEXAPLA_NO_MIDWORD") != "1") else " "
                            merged[ch][v] = [(head + joiner + tail).strip()]
                            # F1b (s60): the tail's part is a co-owner for the --touched guard.
                            if os.environ.get("HEXAPLA_NO_SEAMOWNER") != "1":
                                coowner.setdefault((ch, v), set()).add(p.name)
                            joins.append((ch, v, p.name, head, tail))
                            continue
                        if old != new:
                            conflicts.append((ch, v, p.name))
                        continue                       # first writer wins; conflict reported
                    merged[ch][v] = lines
                    owner[(ch, v)] = p.name

    if joins:
        print(f"\n★ {len(joins)} verse(s) JOINED across a page break (the earlier "
              f"part marked the verse as breaking off; its tail would otherwise "
              f"have been dropped):")
        for ch, v, name, head, new in joins:
            print(f"    ch {ch} v{v}  head …{head[-40:]!r} + tail {new[:40]!r}… "
                  f"(from {name})")

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
        # ⛔ A conflict whose KEPT head reads like a page seam in words SEAM_RE does
        # not accept («[continues p144]», «continues onto idx 166», «cut off at page
        # foot», «page ends») is a lost TAIL, not an overlap. 14 verses in 7 books
        # merged 2026-09-04 lost their tails this way, found 2026-09-28
        # (research/_evidence/thorlaks_seam_tails_other_books_2026-09-28.md).
        # Report-only: the join still needs the explicit marker. These are listed
        # in FULL, never cut at 20. Known-bad control: HEXAPLA_NO_SEAMHINT=1.
        hint = [c for c in conflicts
                if os.environ.get("HEXAPLA_NO_SEAMHINT") != "1"
                and SEAM_HINT_RE.search(" ".join(merged[c[0]][c[1]]))]
        for ch, v, name in conflicts[:20]:
            print(f"    ch {ch} v{v}  (also in {name})")
        if hint:
            print(f"\n⛔ {len(hint)} of them LOOK LIKE A PAGE SEAM (the kept head says the "
                  f"verse continues) - the later part's TAIL IS DROPPED. Mark the head "
                  f"«[continues on next page]» and re-run:")
            for ch, v, name in hint:
                print(f"    ch {ch} v{v}  tail in {name}")

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

    # ⛔ G2 (s46 ruling): CARRY THE EXISTING BOOK'S APPARATUS SECTION FORWARD.
    # Everything between the «Merged by» line and the first `## <Book> N`
    # heading (Acts: «## Reader apparatus moved out of the verse text») exists
    # ONLY in the book file - no part holds it - so a rebuild from the parts
    # deleted it. Re-emitted verbatim, in the same place.
    # Known-bad control: HEXAPLA_NO_CARRY_FORWARD=1 drops it again (and the
    # book-only guard below then reports the lost heading).
    existing = out.read_text(encoding="utf-8") if out.exists() else None
    carried = []
    if existing is not None:
        ex_verses, ex_pre, ex_merged, ex_first, ex_lines = parse_book(existing, a.book)
        if ex_merged is not None and ex_first is not None and ex_first > ex_merged:
            carried = ex_lines[ex_merged + 1:ex_first]
            while carried and not carried[0].strip():
                carried.pop(0)
            while carried and not carried[-1].strip():
                carried.pop()
    if carried and os.environ.get("HEXAPLA_NO_CARRY_FORWARD") == "1":
        print(f"\n⚠⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_NO_CARRY_FORWARD=1 — the "
              f"existing book's apparatus section ({len(carried)} lines) is DROPPED")
        carried = []
    elif carried:
        print(f"\ncarried forward {len(carried)} line(s) of the existing book's "
              f"apparatus section (between «Merged by» and its first `## {a.book} N`)")

    body = [f"# Þorláksbiblía 1644 — {a.book.upper()} (merged chunk report)", "",
            f"Merged by tools/thorlaks_merge_parts.py from {len(parts)} part files "
            f"on {datetime.now():%Y-%m-%d %H:%M}. Each part was read from page images "
            f"by a separate agent; **the PDF text layer was never consulted.**", ""]
    if carried:
        body += carried + [""]
    if concat_blocks is not None:
        # ⚠⚠ KNOWN-BAD EMIT PATH. Each part's chapter block is emitted as its own
        # `## <Book> N` section, in page order — so a chapter spanning a page
        # boundary appears under the SAME heading TWICE, which is the defect.
        body_blocks = concat_blocks
    else:
        body_blocks = [(ch, merged[ch]) for ch in sorted(merged)]
    for ch, verses in body_blocks:
        body.append(f"## {a.book} {ch}")
        body.append("")
        for v in sorted(verses):
            # ⛔ A VERSE SPLIT ACROSS A SHEET BOUNDARY IS ONE VERSE, NOT TWO.
            # Agents label the resumption with the same numeral at column 0:
            # «8 [O][?] Fyrer Truna vard Abraham hlyden…» then, after the page
            # break, «8 (cont'd) [?] hñ erfa skylde…». parse_part correctly
            # files both under verse 8, but emitting both at column 0 makes the
            # audit count two. MEASURED 2026-09-04: Hebrews 11 reported
            # 29 verses, «duplicate [8, 12]», against a real 27.
            # Only the FIRST line of a verse keeps its numeral at column 0.
            for k, l in enumerate(verses[v]):
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

    # ⛔ G1 (s46 ruling, Q5-a): REFUSE TO REVERT BOOK-ONLY EDITS. Runs in dry run
    # AND --apply, before anything (file or .bak) is written. Every hit is
    # printed - never cut at 20.
    if existing is not None and os.environ.get("HEXAPLA_NO_MERGE_GUARD") == "1":
        print("\n⚠⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_NO_MERGE_GUARD=1 — book-only "
              "edits are NOT checked; any the parts lack WILL be reverted")
    elif existing is not None:
        touched = {os.path.basename(t) for t in a.touched}
        names = {p.name for p in parts}
        for t in sorted(touched - names):
            print(f"\n⚠ --touched {t} is not one of this merge's part files")
        new_verses, new_pre = parse_book(text, a.book)[:2]
        lost = []
        for key in sorted(ex_verses):
            if (key in new_verses
                    and verse_text(new_verses[key]) == verse_text(ex_verses[key])):
                continue
            if owner.get(key) in touched or (touched & coowner.get(key, set())):
                continue                           # the caller's own part (head OR joined tail): intended
            lost.append((key, owner.get(key)))
        lost_h = [h for h in ex_pre if h not in new_pre]
        cannot = not ex_verses
        if lost or lost_h or cannot:
            print(f"\n⛔⛔ {len(lost)} BOOK-ONLY EDIT(S) + {len(lost_h)} HEADING(S): "
                  f"{out.name} holds text its parts do not, and this merge would "
                  f"overwrite it (touched: {', '.join(sorted(touched)) or 'none'}):")
            if cannot:
                print(f"    ⛔ GUARD CANNOT RUN: {out.name} parsed 0 verses under "
                      f"`## {a.book} N` headings - a check that cannot run did not pass")
            for (ch, v), part_name in lost:
                print(f"    BOOK-ONLY EDIT {ch}:{v} (part "
                      f"{part_name or 'NONE - in no part'}) would be REVERTED")
            for h in lost_h:
                print(f"    BOOK-ONLY HEADING {h!r} would be LOST")
            if not a.accept_book_regression:
                print("▶ Put each edit into its owner part first (book + part together, "
                      "exact-once), or name the part with --touched if the change IS "
                      "this merge's. Nothing written, no .bak. "
                      "(--accept-book-regression overrides.)")
                sys.exit(4)
            print("\n⚠⚠⚠ --accept-book-regression GIVEN: the book-only edits above "
                  "WILL BE REVERTED by explicit request.")

    if not a.apply:
        print(f"\nDRY RUN — would write {out} ({len(text)} characters). "
              f"Re-run with --apply to write.")
        return
    if out.exists():
        bak = out.with_suffix(f".md.bak-{datetime.now():%Y-%m-%d-%H%M%S}")
        bak.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\nbacked up existing -> {bak.name}")
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(text)} characters)")
    print("▶ NOW RUN, and believe the tools rather than this script:")
    print("     python C:/Projects/Hexapla/tools/thorlaks_corpus_audit.py")
    print("     python C:/Projects/Hexapla/tools/thorlaks_variants.py")


if __name__ == "__main__":
    main()
