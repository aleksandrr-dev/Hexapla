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
# ⚠⚠ THE BOOK LIST IS NOT CLOSED. The scope evidence records a running head
# at v2 p274 read only as «Bok», UNIDENTIFIED, sitting inside the apocrypha's
# page range (p274-p388) and BEFORE «Sprachs Book» at p304. Something is
# printed there. Listing three books as though they were the whole apocrypha
# would rebuild, one level up, exactly the silent denominator this block
# exists to remove. It is therefore carried below as an explicit unknown.
# ▶ research/_evidence/thorlaks_ot_apocrypha_scope_2026-09-07.md
APOCRYPHA = [
    # (name in a part file's «## <name> <n>» heading, chapters, v2 pages)
    ("Sirach", 51, "p304-p333, running head «Sprachs Book»"),
    ("1 Maccabees", 16, "p334-p363, running head «Maccabeorum»"),
    ("2 Maccabees", 15, "p364-p388, running head «Maccabeorum»"),
]
APOCRYPHA_UNIDENTIFIED = [
    ("?", None, "p274-p303, running head read only as «Bok» — NOT IDENTIFIED"),
]


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
        print(f"{name:<18}{n:>8}/{chapters:<6} chapter(s)   "
              f"{'OK' if n == chapters else '⛔ not transcribed' if n == 0 else '⚠ partial'}")
    for name, _c, where in APOCRYPHA_UNIDENTIFIED:
        print(f"{'(unidentified)':<18}{'?':>8}/{'?':<6} chapter(s)   "
              f"⛔ {where}")
    print("-" * 62)
    print(f"{'APOCRYPHA TOTAL':<18}{got:>8}/{exp:<6} chapter(s) of the three "
          f"IDENTIFIED books")
    print("⚠ Chapters only. No per-chapter VERSE expectation exists for these "
          "books;")
    print("  it has to be read off this print, not taken from a parallel "
          "(versification")
    print("  differs by tradition). So a full 51/16/15 here is still not a "
          "verse-level")
    print("  completeness claim.")
    print("⛔ And the book list itself is open: see the unidentified running "
          "head above.")
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
        "   of its three identified books, with NO verse-level expectation",
        "   and an unidentified fourth running head.",
        "   ⛔ A full 31102/31102 is therefore NOT 'complete'.",
        "   Report it as 'N of the protestant canon; apocrypha in scope,",
        f"   {got}/{exp} chapter(s), no verse expectation'.",
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
