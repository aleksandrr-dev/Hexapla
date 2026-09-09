# -*- coding: utf-8 -*-
"""Structurally check Þorláksbiblía chunk part-files against the KJV grid. 0 model tokens.

    python tools/thorlaks_part_check.py --book Matthew
    python tools/thorlaks_part_check.py --file research/_parts/matthew_p13-21.md

## Why this exists

Every defect found in Matthew on 2026-09-06 was found by this check and by
NOTHING ELSE — not by the chunk agent's own review, not by the coverage report,
not by `thorlaks_corpus_audit.py` (which only sees merged books):

  · idx 13-21 — FOUR verses split across page boundaries into two numbered
    lines each (12:4, 14:19, 16:27, 19:10). The agent reported «no merged
    verses». Each made its numeral appear twice.
  · idx 22-31 — Matthew 25:46 DROPPED ENTIRELY. Chapter 25 ran 1-45 contiguous
    with no gap, so only a count against the KJV grid could reveal it.
  · idx 22-31 — 24:2 merged into 24:1 (its numeral was transcribed as the
    Tironian `z`), and 24:15's numeral absent.

⚠⚠ **RUN IT ON EVERY PART FILE BEFORE THE BOOK IS MERGED.** After the merge the
per-chapter evidence is harder to attribute to a page, and the corpus audit
cannot see a verse whose text was silently joined to its neighbour.

## What it checks

  1. verse count per chapter against the KJV grid
  2. duplicate numerals   — the page-boundary-split signature
  3. gaps in the numeral sequence
  4. heading form: `## <Book> <N>` and nothing else. ⛔ `## Chapter N` is the
     old kit skeleton's form and breaks the merge tools; the skeleton was fixed
     2026-09-06 but part-files written before that still carry it.
  5. one verse per line at column 0 (a chunk written line-per-printed-line
     makes every count above meaningless — it is reported first and loudly)
  6. long-s left un-normalised
  7. the ø rate, against the campaign's expected 19-31 % of o-positions
  8. unnumbered long lines INSIDE a chapter body, split into two named classes:
     page-boundary verse TAILS (join them to the verse above) and editorial
     NOTES (move them to a notes section). Both are defects and the fixes
     differ, so they are never reported under one label.

## ⚠⚠ THE GATE WAS COVERING HALF THE CORPUS — FIXED 2026-09-06

Run over all 44 part files, this script exited non-zero on **44 of 44**, and 22
of those were «<book> not found in the KJV asset; cannot check». A gate that
fails everything gates nothing: the numbered books had NEVER been verse-counted
by it. Two causes, both fixed:

  · the KJV asset spells them «1 Corinthians»; files and headings say
    `1corinthians`, `2cor`, `1 Timothy — Chapter 5`. See `canonical()`.
  · THREE heading forms carry scripture and only one was recognised. See
    `_CONNECTOR`.

Blind files afterwards: **1 of 44** — `romans_p136-137.md`, which really does
carry Romans 1:1-7 under no chapter heading at all. ⚠ Checked before reporting:
those seven verses ARE present in the merged `research/thorlaks_romans.md`, so
the defect is local to the part file and nothing was lost.

⛔ **VALIDATE ANY CHANGE TO THIS FILE AGAINST BOTH A KNOWN-GOOD AND A
KNOWN-BAD CASE.** A refactor on 2026-09-06 made `## Chapter 1` unresolvable and
Matthew 1 silently VANISHED from the report — the tool would have reported
FEWER problems and looked like an improvement. A check that hides a known
defect is worse than no check.

  known-good: `matthew_p13-21.md` = 0 problems (still true, verified 2026-09-09)
  known-bad:  `1corinthians_p158-163.md` = 1 problem, «18 `PROGRESS:` line(s)
              written INTO the transcription»

⚠⚠ **THE OLD KNOWN-BAD WENT STALE AND NOBODY NOTICED.** It was
`matthew_p4-12.md` = Matthew 1 at 24/25. That defect has since been REPAIRED,
so the file now reports 0 problems and the negative control had been silently
passing-by-vacancy — any change to this script could have broken its defect
detection completely and both «controls» would still have looked green. Found
2026-09-09 by running the documented control and noticing it did not fire.
▶ **When a known-bad case is fixed, replace it in this docstring in the same
commit.** A negative control that cannot fail is not a control.

⛔⛔ A LOW ø RATE HAS THREE CAUSES AND THIS SCRIPT CANNOT TELL THEM APART.
Until 2026-09-09 the warning here said a low rate «means the read was done at
sheet resolution», which is one cause of three and the least likely now:

  1. **the retrofit is only partly PLACED.** This script counts ø IN THE FILE.
     Mark's adjudicators confirmed 302 ø across 18 pages — 13.2 % of
     o-positions — but 84 could not be located in the transcription, so the
     file holds 219 and reads ~9.6 %. Nothing was misread.
  2. **VOCABULARY.** p47 read 26.1 % on the same instrument, in the same
     session, that read 8.0 % on p46 one page away. The 19-31 % band is a
     per-BOOK claim, never a per-page one.
  3. sheet-resolution reading, the original hypothesis.

▶ Separate them before acting: `thorlaks_o_rate.py --book <B>` gives what was
read on the PAGE, `thorlaks_o_patch.py --book <B>` gives what could not be
placed. Only when those two agree is resolution a candidate at all — and the
fix for THAT is `tools/thorlaks_o_sheets.py`, not a re-read at the same
magnification.

⛔ EXIT CODE: non-zero if any chapter has a problem, so this can gate a merge.
A check that cannot run must never look like a check that passed: an unreadable
or heading-less file EXITS NON-ZERO rather than reporting zero problems.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parent.parent
DATA = Path("C:/Projects/Hexapla-releases")
KJV = REPO / "app/src/main/assets/bibles/en_kjv.json"

# ── RECORDED EDITION DIFFERENCES ───────────────────────────────────────────
# (canonical book, chapter) -> (printed verse count, note with its evidence)
#
# ⛔⛔ A PRINTED COUNT THAT DISAGREES WITH THE KJV IS A FINDING ABOUT THIS
# EDITION, NOT AN ERROR TO CORRECT. Never supply a verse from a parallel to
# make a count line up. But a finding has to have somewhere to LIVE: until
# 2026-09-07 this tool reported all three Mark divergences as
# «COUNT n/m <-- interior chapter, so this is a REAL gap» forever, so a verse
# that had been read off the page and settled looked identical to an unfixed
# defect and the next session re-litigated it. Ported from
# `karlxii_apoc_corpus_audit.py`, which solved exactly this.
#
# ⚠⚠ AN ENTRY IS REPORTED, NEVER SILENCED — see the "RECORDED EDITION
# DIFFERENCES" block in the output. It must never become a way to make a real
# gap invisible, which is why the count is PINNED: if the file stops matching
# the pinned number the tool SHOUTS a contradiction rather than passing. An
# entry is written only after the page has been read; the note says where.
KNOWN_DIVERGENCE = {
    ("Mark", 3): (36, "chapter genuinely carries 36 printed numerals; "
                      "unaffected by the v34 restoration "
                      "— mark_verse_count_divergences_2026-09-07.md"),
    ("Mark", 5): (42, "v42 runs to the end of its sentence, then the centred "
                      "«VI» heading and Mark 6:1 — no numeral 43, nothing cut "
                      "off at the page or column boundary. The print stops at "
                      "42 (mark_kit/p37 lines 00-06) "
                      "— mark_verse_count_divergences_2026-09-07.md"),
    ("Mark", 8): (39, "KJV 9:1 is set INSIDE chapter VIII: v38 ends «j Dyrd "
                      "sijns Fodurs.», then a clearly printed 39 opens the "
                      "KJV 9:1 material and only then comes the centred «IX» "
                      "heading. Same run-on shape as Mark 2:23-28 "
                      "(mark_kit/p40 lines 22-26) "
                      "— mark_verse_count_divergences_2026-09-07.md"),
}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


_GRIDS = None


def kjv_all():
    """-> {canonical KJV book name: {chapter: verse count}}, read once."""
    global _GRIDS
    if _GRIDS is None:
        data = json.loads(KJV.read_text(encoding="utf-8"))
        books = data["books"] if isinstance(data, dict) and "books" in data else data
        _GRIDS = {}
        for b in books:
            name = b.get("name") if isinstance(b, dict) else None
            if not name:
                continue
            chs = b["chapters"] if isinstance(b, dict) else b
            _GRIDS[name] = {i + 1: len(c) for i, c in enumerate(chs)}
    return _GRIDS


def canonical(name):
    """Resolve a loose book name to its KJV asset name, or None.

    ⚠⚠ WHY THIS IS NOT `name.lower() == book.lower()` — MEASURED 2026-09-06.
    The KJV asset spells the numbered books «1 Corinthians», with a space, while
    a part file is called `1corinthians_p152-157.md` and an agent may head its
    chapters «2 Corinthians» or «Chapter 5». An exact compare therefore failed
    on EVERY numbered book: **22 of 44 part files could not be checked at all**
    and had never once been verse-counted by this gate. They exited non-zero
    saying so, which is the honest failure mode — but «cannot check» printed 22
    times reads like noise, and the gate was silently covering only half the
    corpus.
    ⛔ A unique-PREFIX match is allowed («2cor» -> «2 Corinthians») but an
    ambiguous one is refused rather than guessed: picking one of two books would
    check a file against the wrong grid, which is worse than not checking it.
    """
    if not name:
        return None
    grids = kjv_all()
    n = _norm(name)
    for k in grids:
        if _norm(k) == n:
            return k
    hits = [k for k in grids if _norm(k).startswith(n)] if len(n) >= 3 else []
    return hits[0] if len(hits) == 1 else None


# ⚠ THREE heading forms exist in the corpus and all three carry scripture:
#   `## Matthew 11`                      the settled kit form
#   `## Chapter 5 — KJV 28 verses`       the old skeleton form (book from filename)
#   `## 1 Timothy — Chapter 5 (tail…)`   book AND the word Chapter
# The third was missed until 2026-09-06 and left 1 Timothy p196 (30 verses) and
# 2 Thessalonians p192-193 (48 verses) unchecked. Strip the connector before
# resolving, or the book name reads as «1 Timothy — Chapter» and resolves to
# nothing.
_CONNECTOR = re.compile(r"\s*[—–-]?\s*chapter\s*$", re.I)


def heading_books(lines):
    """-> canonical book names actually used by this file's chapter headings.
    The headings are what the merge tools key on, so they are a better authority
    for «which book is this» than the filename."""
    out = []
    for l in lines:
        m = re.match(r"^## (.+?) (\d+)\b", l)
        if not m:
            continue
        name = _CONNECTOR.sub("", m.group(1).strip()).strip()
        if not name or name.lower() == "chapter":
            continue  # `## Chapter N` names no book — the filename must supply it
        c = canonical(name)
        if c and c not in out:
            out.append(c)
    return out


def kjv_grid(book):
    return kjv_all().get(canonical(book) or "")


def check(path, book):
    txt = path.read_text(encoding="utf-8")
    lines = txt.split("\n")
    problems = []
    pinned = []

    books = heading_books(lines) or ([book] if book else [])
    if not books:
        print(f"⛔ {path.name}: cannot tell which book this is — no resolvable "
              f"`## <Book> <N>` heading and the filename did not resolve either.")
        return ["unresolvable book"]

    bad_heads = [l for l in lines if re.match(r'^## Chapter \d+', l)]
    names = "|".join(re.escape(b) for b in books)
    extra = [l for l in lines
             if re.match(rf'^## (?:{names}) \d+\s*\S', l)
             and not re.match(rf'^## (?:{names}) \d+\s*$', l)]

    # ⛔ ORPHANS ARE COLLECTED IN THIS SAME PASS, ON PURPOSE, so that «is this
    # line inside a chapter body» is answered by the same state machine that
    # counts the verses. Scanning for them separately is what made this check
    # report 19 «page-boundary tails» in Matthew of which 12 were editorial
    # notes sitting in the file's trailing notes sections (measured 2026-09-06).
    # A gate whose loudest finding is 63 % false hides the 7 real ones.
    cur, verses, orphans = None, {}, []
    for l in lines:
        m = re.match(r'^## (.+?) (\d+)\b', l)
        if m:
            # ⛔ `## Chapter 1` strips to the EMPTY string, not to "chapter".
            # Treating empty as unresolvable dropped Matthew 1 from the report
            # entirely (2026-09-06) — and Matthew 1 is the chapter missing 1:25.
            # A refactor that HIDES a known defect is the one failure this whole
            # tool exists to prevent, so both spellings map to «book from the
            # filename» explicitly.
            name = _CONNECTOR.sub("", m.group(1).strip()).strip()
            chapter_only = (not name) or name.lower() == "chapter"
            bk = None if chapter_only else canonical(name)
            if bk or chapter_only:
                cur = (bk or books[0], int(m.group(2)))
                verses.setdefault(cur, []); continue
        if l.startswith("## "):
            cur = None; continue
        v = re.match(r'^(\d+) ', l)
        if v and cur is not None:
            verses[cur].append(int(v.group(1))); continue
        if (cur is not None and l and len(l) > 80
                and not l.startswith(("#", "|", "-", "PROGRESS", "<!--", "`", "*", ">", "["))
                and not re.match(r'^\s', l)):
            orphans.append(l)

    if not verses:
        print(f"⛔ {path.name}: NO CHAPTER HEADINGS RECOGNISED — cannot check this file.")
        return ["no headings"]

    # line-per-printed-line detection: verse lines far fewer than numerals present
    body = [l for l in lines if re.match(r'^\d+ ', l)]
    inline = sum(len(re.findall(r'(?<=[.!?]) \d{1,2} ', l)) for l in body)
    if inline > len(body) * 0.5:
        problems.append("LINE-PER-PRINTED-LINE")
        print(f"⛔⛔ {path.name}: looks written LINE-PER-PRINTED-LINE, not one verse "
              f"per line ({inline} inline numerals in {len(body)} lines).")
        print("    Every count below is meaningless until it is reflowed.")

    print(f"\n=== {path.name} ===")
    if len(books) > 1:
        print(f"  (multi-book file: {', '.join(books)} — each checked against "
              f"its OWN grid)")
    for key in sorted(verses):
        bk, c = key
        vs = verses[key]
        if not vs:
            print(f"  {bk} {c:>2}: EMPTY"); problems.append(f"{bk} {c} empty"); continue
        grid = kjv_all().get(bk) or {}
        exp = grid.get(c)
        dup = sorted({x for x in vs if vs.count(x) > 1})
        lo, hi = min(vs), max(vs)
        gaps = [x for x in range(lo, hi + 1) if x not in vs]
        note = []
        if dup:
            note.append(f"DUPES {dup} (page-boundary split?)")
        if gaps:
            note.append(f"GAPS {gaps}")
        # ⛔ A chapter may only be called "partial" if it sits at the EDGE of
        # this file. Treating any short chapter as partial is what nearly hid
        # Matthew 1:25 (merged into v24) on 2026-09-06: the chapter reported
        # 24/25 and was waved through as a chunk boundary, though chapter 1
        # lies wholly inside its file. A masked defect is worse than a noisy
        # check — an interior chapter that is short is ALWAYS reported.
        # Partial AT THE START only if the text begins mid-chapter, and only in
        # the file's first chapter. Partial AT THE END only in its last chapter.
        # ⛔ Matthew 1 is the FIRST chapter and was still missing its LAST verse
        # (1:25, merged into v24). An "is it an edge chapter" test passes that;
        # only this split test catches it.
        # ⚠ first/last are per BOOK, not per file: in a multi-book part file the
        # file's last chapter belongs to only one of them, and using the file's
        # extremes would grant an interior chapter of the other book a
        # "chunk boundary" pass — exactly the masking this rule exists to stop.
        same = [ch for (b2, ch) in verses if b2 == bk]
        first, last = min(same), max(same)
        partial = (c == first and lo > 1) or (c == last and exp and hi < exp)
        edge = partial
        # A divergence read off the page and recorded is not a gap. ⚠ The
        # pinned count must still MATCH: if it does not, the record and the
        # file disagree and that contradiction is louder than the original
        # mismatch — one of the two is wrong and neither may be assumed.
        pin = KNOWN_DIVERGENCE.get((bk, c))
        if exp and len(vs) != exp and not partial and pin:
            if len(vs) == pin[0]:
                pinned.append(f"{bk} {c}: {len(vs)} printed vs {exp} in the "
                              f"KJV grid — {pin[1]}")
            else:
                note.append(
                    f"COUNT {len(vs)}/{exp}  ⛔ CONTRADICTS THE RECORDED "
                    f"EDITION DIFFERENCE, which pins {pin[0]} printed verse(s). "
                    f"Either the file changed or the record is wrong — read "
                    f"the page, do not edit either to match the other")
        elif exp and len(vs) != exp and not partial:
            note.append(f"COUNT {len(vs)}/{exp}"
                        + ("  <-- interior chapter, so this is a REAL gap"
                           if not edge else ""))
        if note:
            problems.append(f"{bk} {c}: {'; '.join(note)}")
        tag = "  (partial chapter — chunk boundary)" if partial and not note else ""
        print(f"  {bk} {c:>2}: {len(vs):>3}/{exp if exp else '?':<3} "
              f"range {lo}-{hi}  {'; '.join(note) or 'ok'}{tag}")

    if bad_heads:
        problems.append("old `## Chapter N` headings")
        print(f"  ⛔ {len(bad_heads)} heading(s) use the old `## Chapter N` form "
              f"— breaks the merge tools.")
    if extra:
        problems.append("headings carry trailing text")
        print(f"  ⛔ {len(extra)} heading(s) carry trailing text after the number.")

    prog = [l for l in lines if l.startswith("PROGRESS:")]
    if prog:
        problems.append(f"{len(prog)} PROGRESS lines in the file")
        print(f"  ⛔ {len(prog)} `PROGRESS:` line(s) written INTO the transcription "
              f"— those belong on stdout, not in the corpus.")
    # Both classes are DEFECTS — a chapter body must hold verse lines and
    # nothing else — but they are different defects and the fix differs, so
    # they are never reported under one label. Calling a running-head note «a
    # page-boundary tail» sent a reader hunting for missing scripture that was
    # not missing (2026-09-06).
    def _is_note(l):
        return (re.match(r'^\(?(?:Heading|Note|Coverage|Running head)\b', l)
                or re.search(r'\bidx\s?\d+\b', l[:60]))
    notes = [l for l in orphans if _is_note(l)]
    tails = [l for l in orphans if not _is_note(l)]
    if tails:
        problems.append(f"{len(tails)} unnumbered text lines")
        print(f"  ⛔ {len(tails)} long text line(s) inside a chapter body carry NO "
              f"verse numeral — a page-boundary tail left on its own line. "
              f"JOIN each onto the verse it continues; do NOT give it a numeral.")
        for l in tails:
            print(f"      · {l[:88]}")
    if notes:
        problems.append(f"{len(notes)} editorial notes inside chapter bodies")
        print(f"  ⛔ {len(notes)} editorial note(s) sit INSIDE a chapter body — "
              f"move them to a notes section at the end of the file.")
        for l in notes:
            print(f"      · {l[:88]}")

    longs = txt.count("ſ")
    if longs:
        problems.append(f"{longs} long-s")
        print(f"  ⛔ {longs} long-s (ſ) not normalised to plain s.")

    # ⛔⛔ CYRILLIC HOMOGLYPHS — INVISIBLE CORRUPTION, FOUND 2026-09-07.
    # `mark_p41-49.md` came back from a transcriber carrying 22 Cyrillic
    # letters inside otherwise-Latin Icelandic words: «Kuollд», «hrækтu»,
    # «byggеr», «Blessadа», «trydе». They RENDER IDENTICALLY to the Latin
    # letters, so every existing check passed the file and a reader cannot
    # see them. Almost certainly a tokenisation artefact of the model doing
    # the reading, not anything on the page.
    # ▶ Nothing was looking for this class. It costs 0 tokens to look.
    # ⚠ The fix is mechanical ONLY because context disambiguates every case;
    #   this check REPORTS, it does not repair. Never bulk-replace without
    #   printing the surrounding word first.
    # ⚠ Greek β is NOT this defect and must not be swept up with it. It is the
    # `ꝑ` sort (`aβ`=af, `tolβ`=tolf, `β̃`=fyrer), which the corpus writes
    # correctly as U+A751 elsewhere — EXCEPT that romans_p140-141.md also uses
    # β deliberately as a printed FOOTNOTE MARKER. Converting it either way
    # asserts a sort the convention says must be SEEN on the image, so it is an
    # image/owner question. Reported separately, and NOT counted as a problem.
    homo, beta = {}, 0
    for ch in txt:
        if ch == "β":
            beta += 1
        elif 0x0400 <= ord(ch) <= 0x04FF or 0x0370 <= ord(ch) <= 0x03FF:
            homo[ch] = homo.get(ch, 0) + 1
    if homo:
        n = sum(homo.values())
        problems.append(f"{n} Cyrillic homoglyph(s)")
        detail = ", ".join(f"U+{ord(c):04X} «{c}» x{k}"
                           for c, k in sorted(homo.items(), key=lambda x: -x[1]))
        print(f"  ⛔⛔ {n} CYRILLIC HOMOGLYPH(S) — invisible corruption: {detail}")
        print("       They render as Latin letters. Print the containing WORD "
              "for each before changing anything, and map by the Cyrillic "
              "letter's PHONETIC value (р=r, с=s), never its shape.")
    if beta:
        print(f"  ⚠ {beta} Greek β — the `ꝑ`/footnote-marker question, OPEN by "
              f"design; not counted as a problem (see the comment in this tool).")

    vtext = "\n".join(body)
    o = vtext.count("o") + vtext.count("O")
    oe = vtext.count("ø") + vtext.count("Ø")
    rate = 100 * oe / (o + oe) if (o + oe) else 0
    # ⛔⛔ THIS RATE IS WHAT IS IN THE FILE, NOT WHAT WAS READ ON THE PAGE.
    # Those are different numbers whenever a retrofit is only partly placed.
    # Mark, 2026-09-09: the adjudicators confirmed 302 ø across 18 pages
    # (13.2 % of o-positions, `thorlaks_o_rate.py --book Mark`), but 84 of
    # them could not be located in the transcription, so the FILE holds 219
    # and reads ~9.6 %. A reader told «read at sheet resolution?» would go and
    # re-read eighteen correctly-read pages.
    # ⚠ And a low rate is not a defect signal on its own even when the
    # retrofit IS complete: p47 read 26.1 % on the same instrument, in the same
    # session, that read 8.0 % on p46 one page away. The rate tracks VOCABULARY
    # and the 19-31 % band is a per-BOOK claim.
    flag = ("  ⚠ below the 19-31 % per-BOOK band. ⛔ CHECK THE RETROFIT FIRST: "
            "this counts ø IN THE FILE, and an unplaced site is missing from it. "
            "▶ thorlaks_o_rate.py --book <B> for what was read on the PAGE, and "
            "thorlaks_o_patch.py --book <B> for what could not be placed. "
            "Only if those agree is resolution a candidate."
            if rate < 10 else "")
    print(f"  ø rate: {oe}/{o + oe} o-positions = {rate:.1f} %{flag}")
    # ⚠ REPORTED, never silenced — a reader must be able to tell "verified
    # against the page and recorded" from "nobody looked".
    if pinned:
        print("  RECORDED EDITION DIFFERENCES (pinned with page evidence, "
              "not gaps):")
        for n in pinned:
            print(f"    · {n}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book")
    ap.add_argument("--file")
    a = ap.parse_args()
    if a.file:
        files = [Path(a.file)]
    else:
        if not a.book:
            print("give --book or --file"); sys.exit(2)
        stem = _norm(a.book)
        files = sorted(p for p in (DATA / "research/_parts").glob("*_p*.md")
                       if _norm(p.stem.split("_p")[0]) == stem)
        files = [f for f in files if ".bak" not in f.name]
    if not files:
        print(f"⛔ no part files found for {a.book or a.file} — that is a "
              f"FAILURE, not a pass.")
        sys.exit(1)
    # ⚠ The book is resolved PER FILE, from that file's own headings first and
    # its filename second. A single --book applied to every file is what made a
    # multi-book part file (the Johannine epistles) uncheckable.
    allp = []
    for f in files:
        fallback = canonical(a.book) if a.book else canonical(f.stem.split("_p")[0])
        allp += check(f, fallback)
    print(f"\n{len(files)} file(s) checked, {len(allp)} problem(s).")
    sys.exit(1 if allp else 0)


if __name__ == "__main__":
    main()
