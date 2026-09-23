# -*- coding: utf-8 -*-
"""Screen every merged Þorláksbiblía / Karl XII book for a DUPLICATE verse
numeral inside one chapter. 0 model tokens, full denominator.

    python tools/thorlaks_duplicate_numerals.py                 # every merged book
    python tools/thorlaks_duplicate_numerals.py --book Luke      # one book
    python tools/thorlaks_duplicate_numerals.py --selftest

## Why this exists — a measured contradiction

`thorlaks_merge_parts.py`'s docstring has claimed for weeks that when a part
file carries a repeated `## <Book> N` heading, the audit's parser RESETS its key
so the second occurrence silently REPLACES the first chapter's verse list, and
the audit then reports a SHORT chapter that is actually complete (DEFLATION).

`thorlaks_corpus_audit.py --selftest` assertion 3 MEASURED the opposite: the
parser uses `out.setdefault(key, [])` then `out[key].append(...)`, so a repeated
heading EXTENDS the list. Overlapping blocks yield 44 entries for a 38-verse
chapter with DUPLICATE numerals `[15, 16, 17, 18, 19, 20]` — INFLATION.

The two point in OPPOSITE directions, and the second is the dangerous one: this
campaign's whole completeness claim rests on the audit, and an inflated count
is exactly the `glen_genesis_33-50.md` shape (a report claiming 572 verses over
two on disk). An inflated chapter can also CANCEL a genuine gap — reading as
complete while actually short.

This tool asks the corpus question that decides it: does any merged book ON DISK
carry a duplicate numeral inside one chapter?

## What it reports

  · every (book, chapter) where a numeral appears more than once, with the
    numerals, their LINE NUMBERS, and the inflation (`entries - distinct`);
  · ⛔ SEPARATELY and LOUDLY, every chapter where a duplicate COINCIDES WITH A
    GAP — an entry count that matches the expectation only because a duplicate
    filled a hole. That is the reads-as-complete-while-short case.

## The parser is the audit's OWN — deliberately

It imports `parse()`, `expected_pair()`, `EXCLUDE` and `RESEARCH` from
`thorlaks_corpus_audit.py` rather than re-implementing them. The question is
about what THAT parser sees; a second implementation would answer a different
question. ⚠ It resolves paths from its own location, so run it by absolute path
or from anywhere — but its data root is the audit's `RESEARCH`.

Exit codes (following `thorlaks_numeral_seam_screen.py`):
    0  no duplicates anywhere
    1  duplicates found
    2  could not run — no merged files, unreadable directory
⛔ A run that could not read the corpus must NEVER return 0.

## --selftest, and its known-bad control

Builds synthetic merged books in a temp root (never reads the real corpus):
a CLEAN chapter (the false-positive control — an ordinary chapter with no
duplicates must come back silent), a chapter with ONE duplicated numeral, and a
chapter where a duplicate exactly CANCELS a gap.

⛔ A control that passes on broken code is not a control.
`HEXAPLA_DISTINCT_NUMERALS=1` de-duplicates before counting, which HIDES the
whole class (every chapter then looks the right size), so the selftest must
exit 1 under it and 0 without it.

    python tools/thorlaks_duplicate_numerals.py --selftest                         # exit 0
    HEXAPLA_DISTINCT_NUMERALS=1 python tools/thorlaks_duplicate_numerals.py --selftest  # exit 1

⛔ This tool NAMES a chapter and stops. It never edits a merged book: a
duplicated numeral is a transcription finding with a page behind it, and this
campaign's rule is that a printed count disagreeing with a parallel is a
finding, never corrected.
"""
import argparse
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import thorlaks_corpus_audit as ca  # noqa: E402  (parse, expected_pair, EXCLUDE, RESEARCH)

# ⚠⚠ SELFTEST-ONLY KNOWN-BAD CONTROL. True only while selftest() runs, so it can
# never hide a real duplicate. See distinct_only().
_IN_SELFTEST = False


def distinct_only():
    """Known-bad control: de-duplicate the verse list before counting.

    Reinstates exactly the blindness this tool exists to remove: once numerals
    are de-duplicated, `entries == distinct` for every chapter, the duplicate
    class disappears, and an inflated chapter reads as an ordinary one — the
    `glen_genesis` shape, hidden by the very act of tidying it.

    ⛔ Gated on _IN_SELFTEST so a real run is never blinded.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_DISTINCT_NUMERALS") == "1"


def merged_files(root):
    """-> sorted list of merged-book paths under `root`.

    A "merged book" is `thorlaks_<book>.md` or `karlxii_<book>.md` in the
    research directory, minus the audit's EXCLUDE docs and .bak files. The
    audit's own rule, reused deliberately.
    """
    out = []
    for pat in ("thorlaks_*.md", "karlxii_*.md"):
        for path in sorted(root.glob(pat)):
            base = path.name.lower()
            if base.endswith(".bak"):
                continue
            if any(x in base for x in ca.EXCLUDE):
                continue
            out.append(path)
    return out


def parse_yielded_blocks(path, names):
    """-> True if the audit's parser found at least one chapter block here.

    ⚠ The audit's OWN parser, like scan()'s — a second implementation would
    answer a different question, which is the same argument the module docstring
    makes for importing `parse()` rather than re-writing it.
    """
    parsed, _unk = ca.parse(path, names)
    return bool(parsed)


def scan(path, names):
    """-> list of findings for one merged book.

    Each finding is a dict:
        book, chapter, numerals, lines, entries, distinct, inflation, target,
        cancels_gap, note
    `nums` is `[verse numbers, in file order]` from the AUDIT's parser; the line
    numbers are recovered by a second read of the same file with the SAME
    regexes, so both agree on what a verse line is.
    """
    parsed, _unk = ca.parse(path, names)

    # Line numbers, using the audit's own CHAPTER_RE / VERSE_RE and its
    # key-guard discipline, so a numeral is addressed the way `parse()` files it.
    lines_by_key = {}
    key = None
    for lineno, line in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(), 1):
        m = ca.CHAPTER_RE.match(line)
        if m:
            book, ch = m.group(1).strip(), int(m.group(2))
            key = (names[book], ch) if book in names else None
            continue
        if key is None:
            continue
        if line.startswith("#"):
            key = None
            continue
        v = ca.VERSE_RE.match(line)
        if v:
            lines_by_key.setdefault(key, {}).setdefault(
                int(v.group(1)), []).append(lineno)

    findings = []
    for key2, nums in parsed.items():
        work = sorted(set(nums)) if distinct_only() else list(nums)
        counts = {}
        for v in work:
            counts[v] = counts.get(v, 0) + 1
        dupes = sorted(v for v, n in counts.items() if n > 1)
        if not dupes:
            continue
        entries = len(work)
        distinct = len(set(work))
        target, note = ca.expected_pair(_COUNTS, key2)
        # Line numbers of the duplicated numerals, in file order.
        lmap = lines_by_key.get(key2, {})
        dlines = []
        for v in dupes:
            for ln in lmap.get(v, []):
                dlines.append((v, ln))
        # Does the duplicate CANCEL a gap? The chapter reads complete against
        # the expectation only because the extra entries filled missing verses.
        present = set(work)
        gaps = [v for v in range(1, target + 1) if v not in present]
        cancels = bool(dupes) and entries >= target and gaps == []
        # Stronger form: distinct count is short of target, but de-duplicated
        # entries reach it — the duplicate is the ONLY reason it reads complete.
        cancels = cancels or (distinct < target <= entries)
        findings.append(dict(book=key2[0], chapter=key2[1], numerals=dupes,
                             lines=sorted(dlines), entries=entries,
                             distinct=distinct, inflation=entries - distinct,
                             target=target, cancels_gap=cancels, note=note))
    return findings


_COUNTS = None
_BOOKS = None


def load_grid():
    """Load the KJV grid once; make it visible to scan() via module state."""
    global _COUNTS, _BOOKS
    names, counts, booknames = ca.load_kjv()
    _COUNTS = counts
    _BOOKS = booknames
    return names, counts, booknames


def report(paths, names, booknames):
    """-> (findings, could_not_run). Prints the human report."""
    if not paths:
        print("⛔ COULD NOT RUN — no merged book files found under")
        print("    %s" % ca.RESEARCH)
        print("    Expected thorlaks_<book>.md or karlxii_<book>.md.")
        print("    ⛔ Nothing was screened; this is NOT «no duplicates».")
        return [], True

    all_findings = []
    read = 0
    books = 0
    not_books = []
    unreadable = []
    for p in paths:
        try:
            found = scan(p, names)
        except OSError as exc:
            unreadable.append((p.name, exc))
            continue
        all_findings.extend(found)
        read += 1
        # ⛔⛔ «READ» IS NOT «A BOOK». The denominator used to say
        # «38 merged book(s) read (FULL denominator)», but five of the 38 carry
        # NO chapter block at all — they are convention/method docs that happen
        # to match the filename glob:
        #     THORLAKS_CONVENTIONS.md, THORLAKS_METHOD_V2_PILOT.md,
        #     karlxii_apoc_navigation.md, karlxii_lat_class.md,
        #     karlxii_word_diffs.md
        # Nothing in them could duplicate, so counting them as books overstated
        # what was screened — the exact class of claim this repo distrusts,
        # inside the tool built to police it.
        # ▶ Count a file as a BOOK only if it yielded ≥1 chapter block.
        if parse_yielded_blocks(p, names):
            books += 1
        else:
            not_books.append(p.name)

    if unreadable:
        print("⛔ COULD NOT RUN — %d file(s) could not be read:" % len(unreadable))
        for nm, exc in unreadable:
            print("    %s: %s" % (nm, exc))
        print("    ⛔ A partial read is NOT «no duplicates».")
        return all_findings, True

    # ⚑ TWO NUMBERS, because they are two facts. `read` is the FILE count (the
    # full denominator, nothing skipped); `books` is the subset that actually
    # carries a chapter block and is therefore the honest denominator for a
    # question about chapter numerals.
    print("duplicate-numeral screen — %d merged file(s) read (FULL denominator), "
          "%d of them yielded a chapter block and count as books"
          % (read, books))
    if not_books:
        print("  ⚠ %d file(s) read but NOT counted as books (no chapter block, "
              "so nothing in them can duplicate): %s"
              % (len(not_books), ", ".join(sorted(not_books))))
    print("-" * 70)

    dup_chapters = len(all_findings)
    cancel_chapters = [f for f in all_findings if f["cancels_gap"]]

    if not all_findings:
        print("✅ no chapter carries a duplicate verse numeral")
    else:
        print("⛔ %d chapter(s) carry a duplicate verse numeral:\n" % dup_chapters)
        for f in sorted(all_findings, key=lambda d: (d["book"], d["chapter"])):
            bn = booknames[f["book"]] if 0 <= f["book"] < len(booknames) else "?"
            loc = ", ".join("v%d@line%d" % (v, ln) for v, ln in f["lines"])
            print("  ⛔ %s %d: duplicate numeral(s) %s — %s"
                  % (bn, f["chapter"], f["numerals"], loc))
            print("       %d entries vs %d distinct (inflation +%d); "
                  "expected %d%s"
                  % (f["entries"], f["distinct"], f["inflation"], f["target"],
                     ("  [%s]" % f["note"]) if f["note"] else ""))

    if cancel_chapters:
        print()
        print("⛔⛔ DUPLICATE CANCELS A GAP — reads as complete while SHORT:")
        print("-" * 70)
        for f in sorted(cancel_chapters, key=lambda d: (d["book"], d["chapter"])):
            bn = booknames[f["book"]] if 0 <= f["book"] < len(booknames) else "?"
            print("  ⛔⛔ %s %d: %d entries / %d distinct vs %d expected — the "
                  "duplicate numeral(s) %s"
                  % (bn, f["chapter"], f["entries"], f["distinct"], f["target"],
                     f["numerals"]))
            print("        are the ONLY reason this chapter reaches the "
                  "expected count. Read the printed page before believing it "
                  "complete.")
    elif all_findings:
        print()
        print("⚠ No duplicate COINCIDES with a gap: every duplicated chapter "
              "here is inflated, not masking a hole. The inflated ones still "
              "break the audit's count and must be read against their pages.")

    print()
    print("⛔ A duplicate numeral is a transcription finding with a page "
          "behind it — this tool NAMES it and stops. Do not «fix» it from a "
          "parallel.")
    return all_findings, False


# ---------------------------------------------------------------- selftest
def selftest():
    """Known-good / known-bad controls on synthetic merged books.

    ⛔ Never reads the real research dir. MAY read the real KJV asset via
    load_grid() — the grid under test. If it is missing this FAILS loudly
    rather than substituting a fake grid.
    """
    global _IN_SELFTEST, _COUNTS, _BOOKS
    _IN_SELFTEST = True
    fails = []

    def ok(cond, what):
        print(("ok   - " if cond else "FAIL - ") + what, flush=True)
        if not cond:
            fails.append(what)

    if not ca.KJV.exists():
        print("FAIL - KJV asset missing — cannot run the selftest; "
              "⛔ a fake grid is not a pass.", flush=True)
        return 1

    import tempfile
    import shutil
    import contextlib

    names, counts, booknames = ca.load_kjv()
    _COUNTS, _BOOKS = counts, booknames
    if "Luke" not in names:
        print("FAIL - KJV asset has no Luke.", flush=True)
        return 1

    luke = names["Luke"]
    n3 = counts[luke][2]              # Luke 3 KJV verse count

    saved_research = ca.RESEARCH

    def verses(book="Luke", ch=3, count=None, start=1):
        return f"## {book} {ch}\n\n" + "".join(
            f"{v} Verse text for {book} {ch} verse {v}.\n"
            for v in range(start,
                           (count if count is not None else
                            counts[names[book]][ch - 1]) + 1))

    def run_scan(text, fname="thorlaks_luke_test.md"):
        """Write ONE file into a FRESH temp root and scan it, so each assertion
        sees only its own fixture (files in one shared root would all be read)."""
        root = tempfile.mkdtemp(prefix="dup_numerals_case_")
        try:
            ca.RESEARCH = Path(root)
            (Path(root) / fname).write_text(text, encoding="utf-8",
                                            newline="\n")
            found = []
            for p in merged_files(Path(root)):
                found.extend(scan(p, names))
            return found
        finally:
            ca.RESEARCH = saved_research
            shutil.rmtree(root, ignore_errors=True)

    try:
        # ── 1. the FALSE-POSITIVE control ────────────────────────────────
        got = run_scan(verses())
        ok(got == [],
           f"1. a well-formed `## Luke 3` book ({n3} verses) yields NO finding "
           f"(got {len(got)} finding(s)) — the false-positive control")

        # ── 2. ONE duplicated numeral is caught ──────────────────────────
        got2 = run_scan(verses() + "17 A second 17, duplicating the numeral.\n")
        nums2 = sorted({v for f in got2 for v in f["numerals"]})
        ok(len(got2) == 1 and nums2 == [17] and got2[0]["inflation"] == 1,
           f"2. a chapter with ONE duplicated numeral (17) is reported: "
           f"findings={len(got2)}, numerals={nums2}, "
           f"inflation={got2[0]['inflation'] if got2 else None}")

        # ── 3. a duplicate CANCELS a gap ─────────────────────────────────
        # Drop verse n3 entirely and add a second n3-1: entries still reach n3,
        # distinct falls one short, n3 is missing — the duplicate fills the hole.
        dupcancel = ("## Luke 3\n\n"
                     + "".join(f"{v} Verse text for Luke 3 verse {v}.\n"
                               for v in range(1, n3))            # 1..n3-1
                     + f"{n3 - 1} A repeated {n3 - 1}.\n")       # extra dup
        got3 = run_scan(dupcancel)
        cancels = [f for f in got3 if f["cancels_gap"]]
        ok(len(cancels) == 1 and n3 - 1 in cancels[0]["numerals"],
           f"3. a chapter whose duplicate numeral EXACTLY cancels a gap "
           f"(v{n3} absent, v{n3 - 1} doubled) is flagged cancels_gap: "
           f"{[(f['numerals'], f['entries'], f['distinct'], f['target']) for f in cancels]}")

        # ── 4. line numbers are reported ─────────────────────────────────
        if got2:
            dlines = got2[0]["lines"]
            ok(len(dlines) == 2 and all(ln > 0 for _v, ln in dlines),
               f"4. the duplicated numeral 17 is reported at BOTH line numbers "
               f"({dlines})")

        # ── 5. the FALSE-POSITIVE control on a SECOND chapter ────────────
        got5 = run_scan(verses(ch=4))
        ok(got5 == [], f"5. a second clean chapter (Luke 4) also yields no "
                       f"finding (got {len(got5)})")

        # ── 6. THE DENOMINATOR LABEL: a chapter-block-less file is READ but
        #       is NOT a BOOK. ⛔ The verdict logic is untouched — this asserts
        #       the count only.
        # Five real files were being counted as books this way (convention/method
        # docs matching the filename glob), so the printed denominator said 38
        # over a smaller real numerator.
        cab = ("# THORLAKS_CONVENTIONS.md\n\n"
               "This document states conventions. It carries no chapter block,\n"
               "no `## Book N` heading, and no verse lines at all.\n")
        root2 = tempfile.mkdtemp(prefix="dup_numerals_denom_")
        try:
            ca.RESEARCH = Path(root2)
            (Path(root2) / "thorlaks_luke_test.md").write_text(
                verses(), encoding="utf-8", newline="\n")
            (Path(root2) / "THORLAKS_CONVENTIONS.md").write_text(
                cab, encoding="utf-8", newline="\n")
            rp = merged_files(Path(root2))
            read_n = books_n = 0
            notbook = []
            for p in rp:
                if not parse_yielded_blocks(p, names):
                    notbook.append(p.name)
                else:
                    books_n += 1
                read_n += 1
            ok(read_n == 2 and books_n == 1
               and notbook == ["THORLAKS_CONVENTIONS.md"],
               f"6. a chapter-block-less file is counted as READ (2 files) but "
               f"NOT as a book (1 book); it is NAMED as not-a-book "
               f"({notbook}) — the denominator now says what it screened")
        finally:
            ca.RESEARCH = saved_research
            shutil.rmtree(root2, ignore_errors=True)
    finally:
        ca.RESEARCH = saved_research

    print("", flush=True)
    if distinct_only():
        print("⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_DISTINCT_NUMERALS=1 — verse "
              "lists are de-duplicated before counting, so the whole duplicate "
              "class is HIDDEN", flush=True)
    print(f"{len(fails)} failure(s)", flush=True)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book", help="one book by KJV name, e.g. Luke")
    ap.add_argument("--selftest", action="store_true",
                    help="control on synthetic merged books; never reads "
                         "research/")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())

    try:
        names, counts, booknames = load_grid()
    except Exception as exc:
        print("⛔ COULD NOT RUN — the KJV grid could not be loaded: %s: %s"
              % (type(exc).__name__, exc))
        sys.exit(2)

    paths = merged_files(ca.RESEARCH)
    if args.book:
        if args.book not in names:
            print("⛔ COULD NOT RUN — «%s» is not a KJV book name; nothing was "
                  "screened." % args.book)
            sys.exit(2)
        want = args.book.lower().replace(" ", "")
        paths = [p for p in paths
                 if p.stem.lower().replace(" ", "").endswith(want)
                 or want in p.stem.lower()]
        if not paths:
            print("⛔ COULD NOT RUN — no merged file for «%s» under %s"
                  % (args.book, ca.RESEARCH))
            sys.exit(2)

    findings, could_not_run = report(paths, names, booknames)
    if could_not_run:
        sys.exit(2)
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
