# -*- coding: utf-8 -*-
"""Whole-corpus completeness audit for the Karl XII 1703 apocrypha chunks.

⚠⚠ THIS TOOL EXISTS BEFORE THE FIRST CHUNK, ON PURPOSE.

Sibling of `thorlaks_corpus_audit.py`, and it exists for the same reason: the
Glen Persian campaign proved that **a chunk report cannot detect a chunk that
did not happen** — `glen_genesis_33-50.md` was a polished report claiming 572
transcribed verses while holding two verse markers on disk, and every per-chunk
check passed it for three weeks. Only aggregating the whole corpus against a
reference grid found it. So this runs from day one, and no completeness claim
about this campaign is believed without it.

    python tools/karlxii_apoc_corpus_audit.py
    python tools/karlxii_apoc_corpus_audit.py --book 71     # Sirach, verbose

Exit code is non-zero when anything is missing or unexplained, so it can gate a
build or a handoff note.

## ⚠⚠ THE GRID IS A REFERENCE, NOT AN AUTHORITY

Þorláks audits against a KJV grid describing the same canon. This one does not.
Karl XII prints the **Lutheran** apocrypha and `en_kjv.json` slots 66-82 hold
the **KJV** one, and they genuinely disagree about what a book even is:

  · 1/2 Esdras (66/67), 3 Maccabees (77) and Laodiceans (82) are NOT IN THIS
    PRINT at all. Empty here is the correct and expected result, not a gap.
  · The KJV grid folds the Epistle of Jeremiah into Baruch 6 (slot 73 empty,
    Baruch 6 chapters). Where THIS print puts it is unestablished — record what
    the page does and decide the slot at integration.
  · «Stycker af Daniel» was believed to be ONE continuously-numbered
    sequence feeding slots 79/80/81 (and Manasse Bon, 74). ✗ IT IS NOT, and
    the PRINT_UNITS entry below is retained only as a record of that belief.
    Read off the pages (2026-08-29): it is an UMBRELLA TITLE over four pieces,
    each with its own title and its own numbering - Susanna 1-64, Bel and the
    Dragon 1-41, Prayer of Azariah 24-91 (the Vulgate Daniel 3 numbering,
    declared on the page), Prayer of Manasses 1-14. So each one IS auditable
    against its own slot, and all four are, via KNOWN_DIVERGENCE.
  · «Stycker af Esthers Book» will not match the KJV's 10-16 chapter fiction.

▶ So a count mismatch here is a QUESTION, not a verdict. Every one must be
resolved into either a real transcription gap or a recorded edition difference
pinned in KNOWN_DIVERGENCE with its evidence. **Do not silence one by editing
the transcription toward the grid** — that is correcting the source toward a
reference, which is the one thing this campaign must never do.

## ⚠⚠ CHUNKS REPORT THE PRINT'S **NATIVE** NUMBERING, NOT KJV COORDINATES

This is the opposite of `thorlaks_corpus_audit.py`, and it is deliberate. Karl
XII sets **continental (Vulgate-style) versification**, which breaks verses more
finely than the KJV throughout — the July Tobit pilot measured a divergence in
**every one of its 14 chapters**, 297 native verses against the grid's 244.
The canon has already been through this: `tools/fix_sv_karlxii.py` re-flowed the
shipped text into the KJV grid with 15 curated verse splits, rather than a
versemap, and the apocrypha will be integrated the same way.

▶ Therefore **a native count ABOVE the grid count is the normal case here**, and
the audit reports it as an open question rather than a gap. What it is really
policing is the thing that is always a defect regardless of edition: a chapter
absent, a numbering sequence with holes, or a duplicate numeral.
▶ ⚠ Which means the chunk-level guarantee is WEAKER than on Þorláks: an
inflated count cannot distinguish "continental versification" from "this chunk
invented verse breaks". The diff against kxii.se is what closes that gap, and it
is not optional for this campaign.

## THE CHUNK REPORT FORMAT — this tool defines it

A chunk report is `karlxii_<something>.md` in the research directory. Inside,
transcribed scripture appears as chapter blocks:

    ## <BookName> <chapter>
    1 <verse text>
    2 <verse text>

· The `##` line names the book exactly as `en_kjv.json` does ("Wisdom of
  Solomon", "1 Maccabees"), or is one of the PRINT_UNITS names below, followed
  by the chapter number **as the print gives it**.
· A verse line starts with its number, a space, then the text. Nothing else in
  the file may start with a bare number at line-start inside a chapter block.
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

APOC = range(66, 83)          # the apocrypha slots of the 83-slot grid

# Docs in the same directory that are NOT chunk reports.
EXCLUDE = ("campaign", "precampaign", "scanhunt", "report", "prompts",
           "navigation")

CHAPTER_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
VERSE_RE = re.compile(r"^(\d+)\s+\S")

# Books this print does not contain. Empty is the CORRECT result; the audit says
# so out loud rather than staying silent, because "no output" and "not in this
# edition" must not look the same to a later reader.
NOT_IN_PRINT = {
    66: "1 Esdras — not in the Lutheran apocrypha of this print",
    67: "2 Esdras — not in the Lutheran apocrypha of this print",
    77: "3 Maccabees — not in the Lutheran apocrypha of this print",
    82: "Laodiceans — not in the Lutheran apocrypha of this print",
}

# CHAPTERS of a present book that this print does not set. Same rule as
# NOT_IN_PRINT and the same discipline as KNOWN_DIVERGENCE: an entry means the
# page was READ and the chapter is not there, never "the numbers disagreed".
# ⚠ These are REPORTED in their own block, not silenced — a later reader must
# be able to tell "verified absent from this edition" from "nobody looked".
# (book index, chapter) -> note
CHAPTER_NOT_IN_PRINT = {
    # Additions to Esther (slot 78). KJV ch1-9 are single-verse EMPTY
    # placeholders in en_kjv.json (verified: each holds one verse whose text is
    # "…"), marking where the Additions interleave with canonical Esther. They
    # have no counterpart in ANY print, so an absence here is correct.
    **{(78, c): "KJV grid ch%d is a single-verse EMPTY placeholder in "
                "en_kjv.json (text is «…»), not text any print can carry "
                "— karlxii_esther_additions.md" % c for c in range(1, 10)},
    # ch12 is REAL text in the KJV (6 verses, Mordecai and the two eunuchs) and
    # is genuinely not printed in this edition — verified by zoom on p742_R2:
    # the print runs straight from the dream at ch11 v12 to the interpretation
    # at ch10 v4. ⚠ This one is an edition fact, not a grid artifact.
    (78, 12): "6 real KJV verses, but this edition does NOT print them "
              "anywhere — verified by zoom on p742_R2, the print runs from "
              "ch11 v12 straight to ch10 v4 — karlxii_esther_additions.md",
}

# Units the PRINT sets as one continuously-numbered sequence, which therefore
# cannot be checked against per-book KJV counts. They are counted and reported,
# never pass/failed, and they stay flagged until a curated split map exists.
# name -> (slots it feeds, note)
PRINT_UNITS = {
    # ✗✗ FALSIFIED 2026-08-29 - kept so the claim cannot come back.
    # The pages show four separately-titled, separately-numbered pieces, each
    # audited against its own slot. NO chunk file uses this heading, and none
    # should: use the en_kjv book names. See karlxii_daniel_additions.md.
    "Stycker af Daniel": ((79, 80, 81, 74),
                          "SUPERSEDED: the print does NOT number this unit "
                          "continuously. Four pieces, four numberings; they "
                          "are pinned individually in KNOWN_DIVERGENCE"),
}

# Edition differences established WITH EVIDENCE by a chunk. Until a mismatch is
# investigated it does NOT belong here — an entry means "we looked at the page
# and the print really says this", not "the numbers disagreed".
# (book index, chapter) -> (printed count, note)
#   or           -> (printed count, note, expected verse NUMERALS)
# The third form exists because a divergence is not always a matter of COUNT:
# «Asarie Böön» carries exactly 68 verses, the grid's number, but numbers them
# 24-91 because the print declares the Vulgate's Daniel 3 numbering on the page.
# Without an explicit numeral set the audit reports that as "missing 1-23" —
# a 23-verse gap that does not exist. An entry here is still only ever written
# after the page has been read; see the note text for where the evidence lives.
#
# ⚠ A pinned entry is REPORTED, not silenced — see the "RECORDED EDITION
# DIFFERENCES" block in the output. It must never become a way to make a real
# gap invisible.
KNOWN_DIVERGENCE = {
    # Bel and the Dragon (slot 81), one chapter.
    (81, 1): (41, "print merges KJV 1+2 into an UNNUMBERED v1 carrying a "
                  "§F5 paragraph break (decorated O, no numeral, next numeral "
                  "is 2 at KJV v3); thereafter print v(n) = KJV v(n+1), so "
                  "print 41 = KJV 42 and nothing is missing "
                  "— karlxii_daniel_additions.md", range(1, 42)),
    # Prayer of Azariah (slot 79) = «Asarie Böön» + «The tre Måns Loffång».
    (79, 1): (68, "print sets the Vulgate's Daniel 3 numbering, declared on "
                  "the page in the sub-title «Efter Daniels 3 cap. 23 v.»: "
                  "verses run 24-91, which is 68 verses, the grid's own count. "
                  "grid v(n) = print v(n+23) "
                  "— karlxii_daniel_additions.md", range(24, 92)),
    # Prayer of Manasses (slot 74) = «Manasse Böön», p746 right column.
    (74, 1): (14, "en_kjv.json holds the whole prayer as ONE verse; this print "
                  "versifies it into 14. Same prayer, a versification "
                  "difference — karlxii_daniel_additions.md", range(1, 15)),
    # Additions to Esther (slot 78), the two chapters the print DOES set but
    # numbers against the Vulgate rather than the KJV.
    (78, 10): (10, "KJV 10:1-3 are EMPTY placeholder verses in en_kjv.json; "
                   "the print numbers this piece 4-13, exactly the KJV "
                   "numbering for the text that actually exists "
                   "— karlxii_esther_additions.md", range(4, 14)),
    # ⚠ 16 verses, the grid's own count, but the numeral 14 IS NOT PRINTED:
    # the column runs «13.» then «15.». So a naive check reports "missing
    # 1-3, 14" and "beyond count 17-20" — four gaps and four extras that do
    # not exist. Numerals are 4-13 then 15-20.
    (78, 15): (16, "print numbers this piece 4-13 then 15-20: the numeral 14 "
                   "is NOT printed (the column runs «13.» then «15.»), and "
                   "KJV 15:1-3 have no counterpart here. 16 verses, the "
                   "grid's own count — karlxii_esther_additions.md",
               list(range(4, 14)) + list(range(15, 21))),
}


def load_kjv():
    d = json.loads(KJV.read_text(encoding="utf-8"))
    names = {b["name"]: i for i, b in enumerate(d)}
    counts = [[len(c) for c in b["chapters"]] for b in d]
    return names, counts, [b["name"] for b in d]


def parse(path, names):
    """-> ({(bookIdx, chapter): [verse numbers]}, {unit: {ch: [v]}}, unknown)"""
    out, units, unknown = {}, {}, set()
    key = unit = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = CHAPTER_RE.match(line)
        if m:
            book, ch = m.group(1).strip(), int(m.group(2))
            key = unit = None
            if book in PRINT_UNITS:
                unit = (book, ch)
                units.setdefault(unit, [])
            elif book in names:
                key = (names[book], ch)
                out.setdefault(key, [])
            else:
                unknown.add(book)
            continue
        if key is None and unit is None:
            continue
        if line.startswith("#"):
            key = unit = None
            continue
        v = VERSE_RE.match(line)
        if v:
            (units[unit] if unit else out[key]).append(int(v.group(1)))
    return out, units, unknown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int, help="report one book index in detail")
    args = ap.parse_args()

    names, counts, booknames = load_kjv()

    # Chunk ranges overlap at their seams: a chapter can appear as a trailing
    # fragment of one chunk AND in full in the chunk that owns it. Keep the BEST
    # copy per chapter, or the fragment manufactures a phantom "short".
    best, sources, all_units, unknown_books = {}, {}, {}, set()
    pinned_notes = []
    chapter_absences = []
    mute = []
    files = 0
    for path in sorted(glob.glob(str(RESEARCH / "karlxii_*.md"))):
        base = os.path.basename(path).lower()
        if base.endswith(".bak") or any(x in base for x in EXCLUDE):
            continue
        files += 1
        got, units, unk = parse(path, names)
        unknown_books |= unk
        # ⚠ A file sitting in the chunk namespace that yields NO chapter block
        # is the dangerous case, not the harmless one: it looks like transcribed
        # work to a human skimming the directory and contributes nothing to the
        # corpus. `karlxii_tobit.md` (the July pilot) is exactly this — it uses
        # `### Chapter N — ...` headings, so the parser cannot see it, AND most
        # of its text is kxii.se-only rather than read off the scan. Say so.
        if not got and not units:
            mute.append(os.path.basename(path))
        for u, verses in units.items():
            if len(verses) > len(all_units.get(u, [])):
                all_units[u] = verses
                sources[u] = os.path.basename(path)
        for key, verses in got.items():
            if not verses:
                continue
            exp = expected(counts, key)
            prev = best.get(key)
            if prev is None or better(verses, prev, exp):
                best[key] = verses
                sources[key] = os.path.basename(path)

    if unknown_books:
        print("⚠ chapter headings naming neither an en_kjv.json book nor a "
              "declared PRINT_UNIT:")
        for b in sorted(unknown_books):
            print(f"    {b!r}")
        print()

    if mute:
        print("⚠ file(s) in the `karlxii_*.md` chunk namespace contributing NO "
              "chapter block — they are not part of the corpus, whatever they "
              "appear to contain:")
        for m in mute:
            print(f"    {m}")
        print()

    if files == 0:
        print("No chunk reports found yet — nothing transcribed.")
        print(f"(looked for {RESEARCH}/karlxii_*.md)")
        return 0

    books = [args.book] if args.book is not None else APOC
    problems, notes = [], []
    not_started = []
    grand = grand_exp = 0

    print(f"{'book':<22}{'chapters':>10}{'verses':>16}   status")
    print("-" * 66)
    for b in books:
        exp = counts[b]
        have = [c for c in range(1, len(exp) + 1) if (b, c) in best]
        # chapters beyond the KJV grid's length for this book
        over = sorted(c for (bb, c) in best if bb == b and c > len(exp))
        tot = sum(len(best[(b, c)]) for c in have) + \
            sum(len(best[(b, c)]) for c in over)
        want = sum(exp)
        if not have and not over:
            if b in NOT_IN_PRINT:
                notes.append(f"{booknames[b]}: absent — expected. "
                             f"{NOT_IN_PRINT[b]}")
                continue
            # ⚠⚠ A BOOK WITH NO CHUNK FILE USED TO BE SKIPPED HERE, WHICH TOOK
            # ITS GRID OUT OF THE DENOMINATOR TOO. The headline then read
            # 3016/3665 (82%) while 2 Maccabees (555) and the four «Stycker af
            # Daniel» slots (175) — 730 verses, strips already cut — were not
            # in the total at all. Unstarted work must COUNT AGAINST US, or
            # the audit flatters the campaign exactly where it should not.
            # Owner-approved fix 2026-08-22.
            # A slot with a ZERO-length grid cannot meaningfully be "not
            # started" — e.g. Epistle of Jeremiah, which this grid folds into
            # Baruch 6. Stay silent rather than print a 0/0 row.
            if want == 0:
                continue
            unit = next((n for n, (slots, _) in PRINT_UNITS.items()
                         if b in slots), None)
            grand_exp += want
            not_started.append((b, want, unit))
            print(f"{booknames[b]:<22}{0:>4}/{len(exp):<5}"
                  f"{0:>8}/{want:<7}   NOT STARTED")
            continue
        if b in NOT_IN_PRINT:
            problems.append(
                f"{booknames[b]}: text was transcribed into a slot recorded as "
                f"NOT IN THIS PRINT — {NOT_IN_PRINT[b]}. Either the record is "
                f"wrong or the chunk filed it under the wrong book.")
        grand += tot
        grand_exp += want
        missing = [c for c in range(1, len(exp) + 1) if c not in have]
        # A chapter verified absent from this edition is not a gap. It is
        # moved into its own REPORTED block, never dropped silently.
        absent_ok = [c for c in missing if (b, c) in CHAPTER_NOT_IN_PRINT]
        for c in absent_ok:
            chapter_absences.append(
                f"{booknames[b]} {c}: {CHAPTER_NOT_IN_PRINT[(b, c)]}")
        missing = [c for c in missing if c not in absent_ok]
        # ⛔ And the converse: text filed into a chapter recorded as absent is
        # a contradiction that must shout, exactly as NOT_IN_PRINT does.
        for c in have:
            if (b, c) in CHAPTER_NOT_IN_PRINT:
                problems.append(
                    f"{booknames[b]} {c}: verses were transcribed into a "
                    f"chapter recorded as NOT SET BY THIS PRINT — "
                    f"{CHAPTER_NOT_IN_PRINT[(b, c)]}. Either the record is "
                    f"wrong or the chunk filed it under the wrong chapter.")
        bad = []
        for c in have:
            verses = best[(b, c)]
            target, note, numerals = expected_triple(counts, (b, c))
            if (b, c) in KNOWN_DIVERGENCE:
                pinned_notes.append(f"{booknames[b]} {c}: {note}")
            if numerals is None:
                numerals = list(range(1, target + 1))
            dupes = sorted({v for v in verses if verses.count(v) > 1})
            want_set = set(numerals)
            gaps = [v for v in numerals if v not in verses]
            extra = sorted({v for v in verses if v not in want_set})
            if dupes or gaps or extra:
                bad.append((c, len(verses), target, dupes, gaps, extra, note))
        status = "OK" if not missing and not bad and not over else "!!"
        print(f"{booknames[b]:<22}{len(have):>4}/{len(exp):<5}"
              f"{tot:>8}/{want:<7}   {status}")
        if missing:
            problems.append(f"{booknames[b]}: chapters absent "
                            f"{compress(missing)}")
        if over:
            problems.append(
                f"{booknames[b]}: printed chapters {compress(over)} lie beyond "
                f"the KJV grid's {len(exp)} — a real edition difference is "
                f"likely, but it must be pinned with page evidence before this "
                f"book is called complete.")
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
                + "; ".join(bits) + tag + f"   ({sources[(b, c)]})")

        if args.book is not None:
            for c in have + over:
                t = expected_pair(counts, (b, c))[0]
                print(f"    ch {c:>3}: {len(best[(b, c)]):>3} verses "
                      f"(grid {t})  {sources[(b, c)]}")

    print("-" * 66)
    print(f"{'TOTAL (grid books)':<22}{'':>10}{grand:>8}/{grand_exp:<7}"
          f"   {100.0 * grand / grand_exp:.1f}%" if grand_exp else "")

    # ⚠ THE GRID IS A YARDSTICK, NOT A TARGET. This print follows the
    # Luther/Vulgate tradition and genuinely carries MORE verses than the KJV
    # apocrypha — measured on the closed books: Tobit +21.7%, Judith +1.8%,
    # Wisdom +0.9%, Baruch +0.5%, 1 Macc +0.4%. So the percentage above is a
    # PROGRESS INDICATOR against a yardstick, never a completion figure, and a
    # book can legitimately finish at over 100%.
    if not_started:
        tot_ns = sum(w for _, w, _ in not_started)
        print("")
        print(f"WARN {len(not_started)} BOOK(S) NOT STARTED - "
              f"{tot_ns} grid verses, counted in the total above:")
        for b, w, unit in not_started:
            tag = f"  (part of the «{unit}» print unit)" if unit else ""
            print(f"   · {booknames[b]:<22} {w:>4} grid verses{tag}")

    if all_units:
        print("\nPRINT UNITS — counted, NOT verified against the grid:")
        for (name, ch), verses in sorted(all_units.items()):
            print(f"  {name} {ch}: {len(verses)} verses  ({sources[(name, ch)]})")
            dupes = sorted({v for v in verses if verses.count(v) > 1})
            seq = [v for v in range(1, max(verses) + 1) if v not in verses] \
                if verses else []
            if dupes:
                problems.append(f"{name} {ch}: duplicate verse numbers {dupes}")
            if seq:
                problems.append(f"{name} {ch}: numbering breaks — "
                                f"{compress(seq)} absent from a sequence "
                                f"running to {max(verses)}")
        for name, (slots, note) in PRINT_UNITS.items():
            if any(n == name for n, _ in all_units):
                problems.append(
                    f"{name}: feeds slots {list(slots)} and has NO curated "
                    f"split map yet, so none of it is in the asset. {note}")

    if pinned_notes:
        # A pinned divergence is REPORTED, never silenced. If one of these
        # ever stops matching the page, delete the entry - do not widen it.
        print("\nRECORDED EDITION DIFFERENCES (pinned with page evidence, "
              "not gaps):")
        for n in pinned_notes:
            print("  · " + n)

    if chapter_absences:
        # Same contract as the block above: verified absent, therefore
        # reported rather than counted as a gap — and never merely omitted.
        print("\nCHAPTERS VERIFIED ABSENT FROM THIS PRINT (recorded, "
              "not gaps):")
        for n in chapter_absences:
            print("  · " + n)

    if notes:
        print("\nEXPECTED ABSENCES (recorded, not gaps):")
        for n in notes:
            print("  · " + n)

    if problems:
        print(f"\n{len(problems)} PROBLEM(S) / OPEN QUESTION(S):")
        for p in problems:
            print("  · " + p)
        print("\n⚠ Do not report this corpus as complete.")
        return 1
    print("\nNo gaps found in what has been transcribed so far.")
    return 0


def expected(counts, key):
    return expected_pair(counts, key)[0]


def expected_pair(counts, key):
    return expected_triple(counts, key)[:2]


def expected_triple(counts, key):
    """-> (count, note, expected numerals or None for the default 1..count)"""
    b, c = key
    if key in KNOWN_DIVERGENCE:
        pinned = KNOWN_DIVERGENCE[key]
        if len(pinned) == 3:
            return pinned[0], pinned[1], sorted(pinned[2])
        return pinned[0], pinned[1], None
    return (counts[b][c - 1] if c - 1 < len(counts[b]) else 0), "", None


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
    nums = sorted(nums)
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
