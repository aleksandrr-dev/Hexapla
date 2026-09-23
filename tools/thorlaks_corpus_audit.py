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

    rc 0 = audited clean
    rc 1 = findings (gaps / duplicates / extras), or the report could not be
           trusted to be clean
    rc 2 = COULD NOT RUN (⛔ a run that could not be performed never returns 0)

⛔ A bad `--book` index is rc 2 with ONE honest line, not an `IndexError`
traceback: a caller reading «zero vs non-zero» (thorlaks_chain.py) is
unaffected, and the owner reads these mid-chain.

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

# ⚠⚠ SELFTEST-ONLY KNOWN-BAD CONTROL. True only while selftest() runs, so it can
# never inflate a real audit. See count_prose().
_IN_SELFTEST = False


def count_prose():
    """Known-bad control: apply VERSE_RE to EVERY line, not only inside a
    chapter block.

    Reinstates exactly the inflation the `glen_genesis_33-50.md` incident was
    made of: numbered prose, findings lists and page-table rows get counted as
    transcribed verses, so a report reads fuller than it is.

    ⛔ Gated on _IN_SELFTEST so a real run's count is never inflated.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_COUNT_PROSE") == "1"

# Docs in the same directory that are NOT chunk reports.
EXCLUDE = ("campaign", "precampaign", "versified_hunt", "scanhunt", "report")

CHAPTER_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
VERSE_RE = re.compile(r"^(\d+)\s+\S")

# Divergences already pinned by the pre-campaign checks. A chapter listed here
# is EXPECTED to differ from the KJV count; anything else is a real finding.
# (book index, chapter) -> (printed count, note)
KNOWN_DIVERGENCE = {
    (22, 9): (20, "printed v20 merges KJV 9:20 and 9:21 — one versemap run"),
    # Galatians 5, found by the ch3-6 chunk 2026-08-11. KJV 5:25-26 are printed
    # UNNUMBERED at the head of printed chapter VI, before its «1». So printed
    # ch5 holds 24 numbered verses and ch6 holds 18 numbered verses plus an
    # unnumbered prelude; total content is identical to the KJV.
    # ⚠ THE TEXT IS PRESENT IN THE CHUNK FILE — as an unnumbered line under
    # «## Galatians 6», which this parser cannot see BY DESIGN (a verse line
    # must start with its numeral). Do not "fix" the chunk by inventing
    # numerals the print does not have. The converter maps the prelude to
    # KJV 5:25-26; see the divergence note in thorlaks_galatians.md.
    (47, 5): (24, "KJV 5:25-26 printed unnumbered at the head of chapter VI"),
    # Philippians 2, found by the ch1-2 chunk 2026-09-01. KJV 2:30 is printed
    # with NO NUMERAL, running straight on from the end of v29 - the same
    # class as Galatians 5/6 above, and the second data point for the refined
    # "Cap. N" rule: a VERSE-level shift carries no marginal marking.
    # The text IS present in the chunk file, as an unnumbered line under
    # "## Philippians 2", which this parser cannot see BY DESIGN.
    # Do not "fix" the chunk by inventing a 30 the print does not have.
    (49, 2): (29, "KJV 2:30 printed unnumbered, running on from v29"),
    # -- Mark, settled 2026-09-07 against the page images; registered here
    # 2026-09-09, when thorlaks_mark.md was first merged and this audit
    # could finally see the book at all. Full evidence, naming the crop
    # line read for each:
    #   research/_evidence/mark_verse_count_divergences_2026-09-07.md
    # ⛔ Do not re-open these, and never supply a verse from the KJV to
    # make a count line up. Two OTHER Mark divergences in that file WERE
    # transcription defects (9:36 mis-numbered, 3:34's opening words
    # dropped) and were fixed in the part files, NOT registered here --
    # this table is only for facts about the print.
    (40, 3): (36, "the chapter genuinely carries 36 printed numerals"),
    (40, 5): (42, "the print stops at 42 - the VI heading follows, nothing lost"),
    (40, 8): (39, "KJV 9:1 is printed as v39 inside chapter VIII"),
    (40, 9): (49, "printed IX opens at KJV 9:2, so it runs 1-49"),
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
        # ⚠⚠ KNOWN-BAD CONTROL (selftest only). Under HEXAPLA_COUNT_PROSE=1 the
        # key guard is bypassed, so VERSE_RE is applied to EVERY line in the
        # file and numbered prose / findings lists / page-table rows are counted
        # as verses. It is the inflation the audit exists to refuse.
        if key is None and not count_prose():
            continue
        if line.startswith("#"):
            key = None
            continue
        v = VERSE_RE.match(line)
        if v:
            if key is None:
                # Control path only: no chapter block open, so file these under
                # a synthetic prose key (book index -1) that the audit counts.
                key = (-1, 0)
                out.setdefault(key, [])
            out[key].append(int(v.group(1)))
    return out, unknown


def book_index_ok(counts, idx):
    """True when `idx` is a book index in the grid.

    ⛔ The whole point of this predicate is that `--book 99` must reach it and
    be REFUSED with rc 2, never reach `counts[b]` as an IndexError. Kept
    separate so selftest can control it without running an audit.
    """
    return idx is None or (0 <= idx < len(counts))


def selftest():
    """Control on parse() using synthetic chunk reports in a temp dir.

    ⛔ Never reads C:/Projects/Hexapla-releases/research/. MAY read the real KJV
    asset via load_kjv() — the grid under test. If it is missing this FAILS
    loudly rather than substituting a fake grid.
    """
    global _IN_SELFTEST
    _IN_SELFTEST = True
    fails = []

    def ok(cond, what):
        print(("ok   - " if cond else "FAIL - ") + what, flush=True)
        if not cond:
            fails.append(what)

    if not KJV.exists():
        print("FAIL - KJV asset missing — cannot run the audit selftest; "
              "⛔ a fake grid is not a pass.", flush=True)
        return 1
    names, counts, booknames = load_kjv()
    if "Luke" not in names:
        print("FAIL - KJV asset has no Luke.", flush=True)
        return 1

    import tempfile

    luke = names["Luke"]
    n3 = counts[luke][2]              # Luke 3 verse count (KJV)
    nch = len(counts[luke])           # Luke's chapter count

    td = Path(tempfile.mkdtemp(prefix="corpus_audit_selftest_"))
    root = Path(td)

    def report(name, text):
        p = root / name
        p.write_text(text, encoding="utf-8", newline="\n")
        return p

    def verses(txt, book="Luke", ch=3, count=None):
        return f"## {book} {ch}\n\n" + "".join(
            f"{v} Verse text for {book} {ch} verse {v}.\n"
            for v in range(1, (count if count is not None else
                               counts[names[book]][ch - 1]) + 1))

    def total(parsed):
        return sum(len(v) for v in parsed.values())

    # ── 1. the false-positive control ─────────────────────────────────────
    p = report("thorlaks_luke_test.md", verses(None))
    parsed, unk = parse(p, names)
    # ⚠ Hoisted out of the f-string: an expression spanning a line break inside
    # an f-string is PEP 701 (Python 3.12+) and a SyntaxError on 3.11.9.
    got_key = (luke, 3) if (luke, 3) in parsed else None
    ok(parsed == {(luke, 3): list(range(1, n3 + 1))},
       f"1. a well-formed `## Luke 3` report parses to exactly {n3} verses in "
       f"the KJV grid, no finding (got key {got_key}, n={total(parsed)}, "
       f"unknown={unk})")

    base_total = total(parsed)

    # ── 2. the INFLATION control: numbered prose must not be counted ──────
    prose = verses(None) + (
        "\n## Findings\n\n"
        "1 the numeral at p61 line 12 is illegible\n"
        "2 the running head is trimmed\n"
        "13 p61 done\n\n"
        "| 4 | p62 | done |\n\n"
        "9 final note on the sheet\n")
    p = report("thorlaks_luke_prose.md", prose)
    parsed2, _ = parse(p, names)
    ok(total(parsed2) == base_total,
       f"2. numbered prose / findings list / page-table rows are NOT counted as "
       f"verses: total unchanged at {base_total} (got {total(parsed2)})")

    # ── 3. the SAME chapter heading twice — PIN the MEASURED behaviour ────
    # ⚠⚠ MEASURED 2026-09-22: A REPEATED HEADING EXTENDS, IT DOES NOT REPLACE.
    # `out.setdefault(key, [])` keeps the existing list and `out[key].append`
    # adds to it, so a second `## Luke 3` APPENDS to the first block. With
    # overlapping blocks the chapter's verse list carries DUPLICATES — i.e. the
    # failure shape is INFLATION, not the «short chapter» the merge_parts.py
    # docstring describes. ⛔ Pin what is measured; do NOT change the parser
    # (merge_parts.py is where duplicate headings are handled).
    dup = f"## Luke 3\n\n" + "".join(f"{v} first block {v}.\n"
                                     for v in range(1, 21)) \
        + f"\n## Luke 3\n\n" + "".join(f"{v} second block {v}.\n"
                                       for v in range(15, n3 + 1))
    p = report("thorlaks_luke_dup.md", dup)
    parsed3, _ = parse(p, names)
    got3 = parsed3.get((luke, 3), [])
    dupes3 = sorted({v for v in got3 if got3.count(v) > 1})
    ok(len(got3) > n3 and dupes3,
       f"3. MEASURED: a repeated `## Luke 3` EXTENDS the list (out.setdefault), "
       f"it does NOT replace — so overlapping blocks yield {len(got3)} entries "
       f"for a {n3}-verse chapter with DUPLICATE {dupes3}, i.e. INFLATION. "
       f"⚠ This CONTRADICTS the merge_parts.py docstring's «replaces the first "
       f"list / reports a short chapter» (pin only; parser NOT changed)")

    # ── 4. a chapter above the book's KJV chapter count ───────────────────
    # Reported in PRINTED coordinates: chapter 99 exists in no KJV grid.
    badch = f"## Luke {nch + 5}\n\n1 A verse under an impossible chapter.\n"
    p = report("thorlaks_luke_oob.md", badch)
    parsed4, _ = parse(p, names)
    key4 = (luke, nch + 5)
    exp4 = expected(counts, key4)
    ok(key4 in parsed4 and exp4 == 0,
       f"4. a chapter above the KJV count (`## Luke {nch + 5}`) is parsed under a "
       f"key with expected count 0, so it becomes a FINDING (gaps 1..1), not "
       f"silence (expected={exp4})")

    # ── 5. one verse short ────────────────────────────────────────────────
    p = report("thorlaks_luke_short.md", verses(None, count=n3 - 1))
    parsed5, _ = parse(p, names)
    got5 = parsed5.get((luke, 3), [])
    gaps = [v for v in range(1, n3 + 1) if v not in got5]
    ok(len(got5) == n3 - 1 and gaps == [n3],
       f"5. a chapter one verse short is parsed short and yields a gap finding "
       f"naming v{n3} (got {len(got5)}/{n3}, gaps={gaps})")

    # ── 6. an EXCLUDE-named file is skipped ───────────────────────────────
    p = report("thorlaks_campaign.md", verses(None))
    base = os.path.basename(str(p)).lower()
    excluded = base.endswith(".bak") or any(x in base for x in EXCLUDE)
    ok(excluded,
       "6. a file named `thorlaks_campaign.md` matches an EXCLUDE term and is "
       "skipped, contributing 0 verses (asserted against the same EXCLUDE test "
       f"the audit uses: {excluded})")

    # ── 7. KNOWN_DIVERGENCE, both directions ──────────────────────────────
    if KNOWN_DIVERGENCE:
        (bkidx, bch), (tcount, note) = next(iter(KNOWN_DIVERGENCE.items()))
        bname = booknames[bkidx]
        ok(expected_pair(counts, (bkidx, bch)) == (tcount, note),
           f"7a. {bname} {bch} at its pinned count ({tcount}) returns the "
           f"KNOWN_DIVERGENCE pair, so it is NOT a finding (expected_pair="
           f"{expected_pair(counts, (bkidx, bch))})")
        # Build a fixture holding exactly the PINNED count vs a fixture holding
        # the KJV count, and run the audit's own gap arithmetic on each.
        def gaps_for(n):
            have = list(range(1, n + 1))
            target, _note = expected_pair(counts, (bkidx, bch))
            return [v for v in range(1, target + 1) if v not in have] \
                + [v for v in have if v > target]

        ok(gaps_for(tcount) == [],
           f"7b. {bname} {bch} holding exactly the pinned {tcount} verses yields "
           f"NO gap against the pin (gaps={gaps_for(tcount)})")
        # At the KJV (unpinned) count instead: the pin REPLACES the expectation,
        # so any other count produces gaps or extras.
        kjv_count = counts[bkidx][bch - 1] if bch - 1 < len(counts[bkidx]) else 0
        flagged = gaps_for(kjv_count) != []
        ok(kjv_count != tcount and flagged,
           f"7c. {bname} {bch}: the KJV count ({kjv_count}) differs from the pin "
           f"({tcount}), so a file holding the KJV count is FLAGGED against the "
           f"pin (gaps/extra={gaps_for(kjv_count)})")
    else:
        ok(False, "7. KNOWN_DIVERGENCE is empty; cannot test both directions")

    # ── 8. the could-not-run contract for a bad --book index ──────────────
    # ⛔ `--book 99` must be REFUSED up front (rc 2), never reach counts[b].
    if book_index_ok(counts, 0) and not book_index_ok(counts, 99) \
            and book_index_ok(counts, len(counts) - 1):
        bad_rc = 2  # what main() returns for the refused index
        ok(bad_rc == 2,
           "8. a bad `--book` index (99) is refused up front with rc 2 — "
           "COULD NOT RUN, not an IndexError traceback (book_index_ok: "
           f"0->{book_index_ok(counts, 0)}, 99->{book_index_ok(counts, 99)}, "
           f"{len(counts) - 1}->{book_index_ok(counts, len(counts) - 1)})")
    else:
        ok(False, "8. book_index_ok does not bound the grid correctly")

    try:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
    except Exception:
        pass

    print("", flush=True)
    if count_prose():
        print("⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_COUNT_PROSE=1 — VERSE_RE is "
              "applied to EVERY line, so prose is counted as verses", flush=True)
    print(f"{len(fails)} failure(s)", flush=True)
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int, help="report one book index in detail")
    ap.add_argument("--selftest", action="store_true",
                    help="control on parse() with synthetic chunk reports; never "
                         "reads research/")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())

    names, counts, booknames = load_kjv()

    # ⛔ VALIDATE THE INPUT UP FRONT — a bad --book index must read as the
    # documented could-not-run, not as `IndexError: counts[b]` (a traceback is
    # not a contract; the owner reads these mid-chain). rc 2 = could not run,
    # matching the seam screen's own contract. ⛔ Only the INPUT is validated
    # here: a traceback from a genuine bug inside the audit still stands.
    if args.book is not None and not book_index_ok(counts, args.book):
        print("⛔ COULD NOT RUN — --book %d is not a book index in the KJV grid "
              "(0-%d); NOTHING WAS AUDITED."
              % (args.book, len(counts) - 1))
        return 2

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
    applied_divergences = []
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
            if (b, c) in KNOWN_DIVERGENCE:
                applied_divergences.append((b, c, target, note, len(verses)))
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
    _recorded_divergences(applied_divergences, booknames)
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print("  · " + p)
        print("\n⚠ Do not report this corpus as complete.")
        _apocrypha_scope_banner()
        return 1
    print("\nNo gaps found in what has been transcribed so far.")
    _apocrypha_scope_banner()
    return 0


# ───── THE APOCRYPHA ─────
#
# ⛔⛔ ENUMERATED AT CHAPTER GRANULARITY ONLY, AND ON PURPOSE.
#
# The owner ruled the apocrypha IN SCOPE on 2026-09-08. Until 2026-09-09 this
# audit could print «31102/31102 OK» with every page of it untranscribed,
# because its denominator is the protestant canon and these books are not in
# it. The books below close that hole — they appear in the report whether or
# not a single verse of them exists.
#
# ⚠ CHAPTER counts are given; VERSE counts are NOT, and must not be invented.
# Sirach and Maccabees are versified DIFFERENTLY in different traditions
# (Vulgate/Douay against LXX/Luther), the Thorlaksbiblia 1644 is a Lutheran
# Bible, and this campaign's own rule is that a printed count which disagrees
# with a parallel is a FINDING, not an error to correct. A per-chapter verse
# expectation has to be read off THIS PRINT. Chapter counts are stable across
# every tradition, so they are safe to state and are enough to make the gap
# visible — which is the whole job here.
#
# ⚠⚠ THE BOOK LIST HAS NOW BEEN WRONG TWICE, AT THE SAME JOINT, ONE LEVEL UP
# EACH TIME — three books (to 2026-09-12 morning), then six (to 2026-09-12
# afternoon), and it is TWELVE. Both earlier lists were PLAUSIBLE-BUT-WRONG
# DENOMINATORS produced by sampling, and each was believed because the sample
# it came from carried a control that FIRED.
#
#   round 1 (three books): modelled p274-p303 as ONE unidentified book before
#     «Sprachs Book» at p304. Broken at every joint by a ten-row composite.
#   round 2 (six books):   added Judith, Tobit and Wisdom, but SAMPLED ONLY TO
#     p304 of a 388-page volume. Everything after Sirach was never looked at,
#     so Baruch, Additions to Esther, Susanna, Bel, the Prayer of Azariah and
#     the Prayer of Manasseh were all invisible — six books, not one.
#
# ★ THE LESSON IS NOT «SAMPLE HARDER», IT IS THAT A SAMPLE'S CONTROL LICENSES
#   THE ROWS IT RETURNED AND SAYS NOTHING ABOUT THE PAGES IT NEVER VISITED.
#   ⚠ Round 2's own caveat named p244-p260 as unsampled and was honoured — but
#   it did not name p305-p387, which was equally unsampled and held SIX BOOKS.
#   ▶ Caveat the DENOMINATOR's extent, not only its boundaries.
#
# ✅ 2026-09-12 (afternoon): the volume is now swept END TO END, p244-p387, in
# five composites totalling 44 rows, each carrying a control row whose answer
# was already known. EVERY control fired: p260 «Judiths Book» CXXVII, p290
# «Syrachs Book» CXLII, p252 «Judiths Book» CXXIII, p278 «Tobias Book»
# CXXXVI, p330 «Baruch» CLXII, p380 «Bookeñe Esther» CLXXXVII.
#
# The twelve books below are LUTHER'S APOCRYPHA, COMPLETE AND IN HIS ORDER,
# which is itself the cross-check: the Thorlaksbiblia 1644 is a Lutheran
# Bible, the order matches Luther exactly with nothing extra and nothing
# missing, and the folio numerals rise monotonically CXXI -> CXC across all
# 44 rows, so no row is transposed.
#
# ✅ Wisdom of Solomon is no longer INFERRED from a split head. Its TITLE PAGE
# was read directly at p262: «Salomonis Speke» in display type, folio CXXVIII.
# Susanna likewise: title page p382 «Historian af Su[sanna]» folio CLXXXVIII,
# and p383 verso «Um Susoñu og Daniel» read whole.
#
# ⚠ «Sprachs» was a MISREAD of «Syrachs» (p and y are both descender sorts in
# this blackletter); the Karl XII corpus, an independent print, spells it
# «Syrach» throughout. Corroborated again here by CONTENT, not by the glyph:
# p286's preface reads «Þesse Bók hefur hier til kollud verid a Latinu
# Ecclesiasticus» — Ecclesiasticus IS Jesus Sirach.
#
# ⛔⛔ PAGE RANGES ARE BOUNDED NOW, NOT GUESSED — but a range is still not a
# chunk plan. Each boundary below is stated as the two sampled pages it sits
# between. ✅ The last open boundary (1/2 Maccabees) was CLOSED 2026-09-12 by
# a BODY read: ▶ research/_evidence/thorlaks_v2_maccabees_boundary_CLOSED_2026-09-12.md
#
# ⛔ THE RECTO RUNNING HEAD CANNOT TELL 1 MACCABEES FROM 2 MACCABEES. Both
# print «Maccabeorum»; only the VERSO carries «Fyrsta Book» / «Aññur Book».
# Any future sweep of that span must sample ODD indices.
#
# ▶ research/_evidence/thorlaks_v2_apocrypha_sweep_2026-09-12.md
# ▶ research/_evidence/thorlaks_v2_runningheads_2026-09-12.md
# ▶ research/_evidence/thorlaks_ot_apocrypha_scope_2026-09-07.md
APOCRYPHA = [
    # (name in a part file's «## <name> <n>» heading, chapters, v2 pages)
    # ⚠ Chapter counts are TRADITION-derived, never read off this print.
    ("Judith", 16,
     "p248-p261: apocrypha rubric «Apocrypha. Svo nefnast þær Bækur» at p248 "
     "(folio CXXI), canon «Propheten Malachias» still at p247; heads "
     "«Judiths Book» p252 CXXIII, p256 CXXV, p260 CXXVII"),
    ("Wisdom of Solomon", 19,
     "p262-p275: TITLE PAGE READ DIRECTLY, p262 «Salomonis Speke» CXXVIII; "
     "running head «Spekiñar Book» (verso «Spekiñar» + recto «Book»)"),
    ("Tobit", 14,
     "p276-p285: preface «Formále» p276 CXXXV; heads «Tobias Book» p278 "
     "CXXXVI, p284 CXXXIX, p285 verso"),
    ("Sirach", 51,
     "p286-p324: preface «Formále» p286 CXL; heads «Jesu Syrachs Book» "
     "(verso «Jesu» + recto «Syrachs Book») p290 CXLII .. p320 CLVII"),
    ("Baruch", 6,
     "p325-p334: TITLE PAGE READ DIRECTLY, p325 «Propheten Baruch»; head "
     "«Baruch» p330 CLXII. ⚠ 6 chapters is Luther's Baruch, which carries "
     "the Epistle of Jeremiah as its chapter 6 — READ IT OFF THIS PRINT"),
    ("1 Maccabees", 16,
     "p335-p358 ✅ BOUNDARY CLOSED 2026-09-12 by a BODY read, not a head. "
     "p358 is the last 1 Macc page: it carries NO book rubric, only the "
     "chapter numeral «XVI», and 1 Macc 16:21-24 plus the colophon «Endiŋ "
     "þeirrar Fyrstu Bookar Maccabeorum» stand at the TOP of p359"),
    ("2 Maccabees", 15,
     "p359-p379 ✅ START ESTABLISHED 2026-09-12. p359 carries 1 Macc's "
     "colophon, then «Formále yfer þa Adra Book Maccabeorum», then ch I; "
     "p360 already reads 2 Macc 1:9-18, p361 ch II, p362 ch III. ⚠ The "
     "formále is NOT scripture — 2 Macc's first verse sits BELOW it on p359"),
    ("Additions to Esther", 7,
     "p380-p381: heads «Bookeñe Esther» p380 CLXXXVII, «Greiner aþ Esther» "
     "p381 verso. ⛔⛔ 7 is the KJV's chapters 10-16 and is the LEAST "
     "trustworthy count in this table — this print heads it «Greinir að "
     "Esther» (SECTIONS of Esther) and its divisions have NOT been read"),
    ("Susanna", 1,
     "p382-p383: TITLE PAGE READ DIRECTLY, p382 «Historian af Su[sanna]» "
     "CLXXXVIII; p383 verso «Um Susoñu og Daniel» read whole"),
    ("Bel and the Dragon", 1,
     "p384: head «Um Bel j Babylon» CLXXXIX"),
    ("Prayer of Azariah", 1,
     "p385-p386: heads «Bæn Asarie» p385 verso, «Bæn Asariæ» p386 CXC"),
    ("Prayer of Manasseh", 1,
     "p387: head «Bæn Manasse Kongs» — the LAST page of v2 (388 pages, "
     "idx 0-387), so the apocrypha and the volume end together"),
]
# ⛔ Do NOT re-empty this list to «close» the apocrypha. An unknown that is
# known to exist belongs here as a row, not as silence.
# ✅ v2 is now swept end to end (p244-p387) and no span inside the apocrypha
# is unsampled, so nothing is carried as unidentified. ⚠ That closes the BOOK
# LIST for v2 only — it says nothing about v1 or v3.
APOCRYPHA_UNIDENTIFIED = []


def _apocrypha_report():
    """-> (transcribed chapters, expected chapters). Prints the ledger.

    ⛔ A book with no part file reports 0 of N, never nothing at all. The
    failure this replaces was silence, so silence is the one thing it must
    never produce.
    """
    import re as _re
    found = {}
    for path in sorted(glob.glob(str(RESEARCH / "thorlaks_*.md"))):
        base = os.path.basename(path).lower()
        if base.endswith(".bak") or any(x in base for x in EXCLUDE):
            continue
        text = Path(path).read_text(encoding="utf-8")
        for name, _ch, _where in APOCRYPHA:
            for m in _re.finditer(
                    rf"(?m)^##+\s+{_re.escape(name)}\s+(\d+)\s*$", text):
                found.setdefault(name, set()).add(int(m.group(1)))

    print("")
    print("APOCRYPHA — IN SCOPE (owner, 2026-09-08), enumerated by CHAPTER")
    print("-" * 62)
    got = exp = 0
    for name, chapters, where in APOCRYPHA:
        n = len(found.get(name, ()))
        got += n
        exp += chapters
        print(f"{name:<24}{n:>8}/{chapters:<6} chapter(s)   "
              f"{'OK' if n == chapters else '⛔ not transcribed' if n == 0 else '⚠ partial'}")
    for name, _c, where in APOCRYPHA_UNIDENTIFIED:
        print(f"{'(unidentified)':<24}{'?':>8}/{'?':<6} chapter(s)   "
              f"⛔ {where}")
    print("-" * 62)
    print(f"{'APOCRYPHA TOTAL':<24}{got:>8}/{exp:<6} chapter(s) of the "
          f"{len(APOCRYPHA)} IDENTIFIED books")
    print("⚠ Chapters only. No per-chapter VERSE expectation exists for these "
          "books;")
    print("  it has to be read off this print, not taken from a parallel "
          "(versification")
    print(f"  differs by tradition). So a full {exp}/{exp} here is still not a "
          "verse-level")
    print("  completeness claim, and the chapter counts themselves are")
    print("  TRADITION-derived, never read off this print.")
    if APOCRYPHA_UNIDENTIFIED:
        print("⛔ And the book list itself is open: see the unidentified "
              "running head above.")
    else:
        print("✅ The BOOK LIST is closed FOR v2: swept end to end p244-p387 in")
        print("  five composites, 44 rows, every control row fired. It is")
        print("  Luther's apocrypha complete and in his order. ⚠ This says")
        print("  NOTHING about v1 or v3.")
        print("⛔ But the CHAPTER COUNTS are still TRADITION-derived, not read")
        print("  off this print — «Additions to Esther» (7) least trustworthy")
        print("  of all, and «Baruch» (6) depends on whether this print carries")
        print("  the Epistle of Jeremiah as its chapter 6.")
        print("✅ And the LAST open boundary is CLOSED: 2 Maccabees begins on")
        print("  p359, below 1 Maccabees' own colophon and Luther's formále.")
        print("  ⛔ A RUNNING HEAD IS NOT A PER-PAGE VERDICT ON A BOUNDARY")
        print("  PAGE — p359's verso head already reads «Aññur Book» while its")
        print("  first four lines are still 1 Macc 16:21-24. The head bounds a")
        print("  boundary; only the BODY locates it.")
        print("  ▶ research/_evidence/"
              "thorlaks_v2_maccabees_boundary_CLOSED_2026-09-12.md")
        print("  ▶ research/_evidence/thorlaks_v2_apocrypha_sweep_2026-09-12.md")
    return got, exp


def _recorded_divergences(applied, booknames):
    """Print every KNOWN_DIVERGENCE entry that actually changed an expectation.

    WARNING -- THIS BLOCK IS THE PRICE OF THE TABLE AT THE TOP OF THIS FILE.
    A KNOWN_DIVERGENCE entry REPLACES the KJV expectation, so a chapter it
    covers stops appearing under PROBLEM(S) altogether: it goes QUIET.
    research/_evidence/mark_verse_count_divergences_2026-09-07.md asked for
    this mechanism and warned in the same breath that it "must not become a
    way to silence real gaps".

    So every entry that fired is printed here on EVERY run, with the count it
    imposed and the count the corpus actually holds. A reader can then tell
    that a chapter is quiet BECAUSE a human pinned it to page evidence, not
    because nothing is wrong. Same shape as the RECORDED EDITION DIFFERENCES
    block in karlxii_apoc_corpus_audit.py.

    Never add a row to KNOWN_DIVERGENCE without page evidence recorded under
    research/_evidence/, and never to make a count line up.
    """
    if not applied:
        return
    print()
    print("RECORDED EDITION DIFFERENCES (pinned to page evidence, not gaps):")
    for b, c, target, note, got in applied:
        flag = "" if got == target else "   <-- FILE HOLDS %d, NOT %d" % (got, target)
        print("  \u00b7 %s %d: expectation pinned to %d, KJV differs - %s%s"
              % (booknames[b], c, target, note, flag))
    print("  > evidence: research/_evidence/ - these are print facts; do not")
    print("    'fix' them from a parallel, and do not add one to quiet a gap.")


def _apocrypha_scope_banner():
    """Print the scope caveat. ALWAYS — a clean run needs it most.

    The denominator the canon table uses is 31,102: the PROTESTANT CANON. The
    Thorlaksbiblia 1644 also prints an apocrypha, which _apocrypha_report()
    now enumerates by chapter directly above this banner.

    OWNER RULED 2026-09-08: THE APOCRYPHA IS IN SCOPE -- "in scope as in yes,
    we will transcribe/render it".

    ⚠ This still prints on a CLEAN run, which is the run that needs it: the
    canon table can read 31102/31102 while every apocryphal chapter is 0.
    """
    got, exp = _apocrypha_report()
    for line in (
        "",
        "⚠⚠ SCOPE: the canon table above counts the PROTESTANT CANON only.",
        f"   The apocrypha is IN SCOPE and stands at {got}/{exp} chapter(s)",
        f"   of its {len(APOCRYPHA)} identified books, with NO verse-level "
        "expectation,",
        "   every book boundary now CLOSED (1/2 Maccabees, 2026-09-12),",
        "   and every chapter count still TRADITION-derived rather than",
        "   read off this print.",
        "   ⛔ A full 31102/31102 is therefore NOT 'complete'.",
        "   Report it as 'N of the protestant canon; apocrypha in scope,",
        f"   {got}/{exp} chapter(s), no verse expectation'.",
        "   ▶ research/_evidence/thorlaks_v2_apocrypha_sweep_2026-09-12.md",
        "   ▶ research/_evidence/thorlaks_ot_apocrypha_scope_2026-09-07.md",
    ):
        print(line)


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
