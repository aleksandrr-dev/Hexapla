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
import os
import re
import sys

# The marker an adjudicated part file carries when the PRINT breaks a verse at
# the page foot and the next page owns its tail. ⚠ It must be an explicit
# report by the read - never inferred from punctuation.
SEAM_RE = re.compile(
    r"\[[^\]]*\b(?:breaks off|broke off|continues on|continued on|"
    r"continuation of the verse)\b[^\]]*\]", re.I)
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

    def run(book, argv_extra=None):
        """Drive main() via sys.argv; -> (rc, stdout)."""
        old_argv = sys.argv
        buf = io.StringIO()
        rc = 0
        sys.argv = ["thorlaks_merge_parts.py", "--book", book,
                    "--out", str(out_path), "--apply"] + (argv_extra or [])
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

    merged, prose, conflicts, joins = {}, [], [], []
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
                            merged[ch][v] = [(head + " " + tail).strip()]
                            joins.append((ch, v, p.name, head, tail))
                            continue
                        if old != new:
                            conflicts.append((ch, v, p.name))
                        continue                       # first writer wins; conflict reported
                    merged[ch][v] = lines

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
