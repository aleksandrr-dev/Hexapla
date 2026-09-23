#!/usr/bin/env python
"""
thorlaks_chunk_check.py - screen ONE CROP READ CHUNK before it is stitched.

WHY THIS EXISTS
---------------
`thorlaks_read_check.py` screens a STITCHED read; `thorlaks_part_check.py`
screens a merged part. Nothing screened the CROP READ CHUNK, which is the
artifact a reading subagent actually produces - so the first gate a bad read
met was two full reads later, after the whole page had been paid for.

The workflow run of 2026-09-17 (idx 63-65, ~3.36M subagent tokens, 0 pages
merged) failed on exactly three chunk-level defects, and EVERY ONE of them is
visible in the chunk file with no vision at all:

  p63 read B  line03 carried a `[running head ... not body text]` tag AND the
              body text of Luke 10:19 behind it. The tag won downstream and
              10:19-20 were lost.            -> check 5, TAG CONTRADICTION
  p64 A and B long-s (U+017F) written into the verse text, 5 and 44 of them,
              against a SETTLED convention.  -> check 2, FORBIDDEN SORTS
  p65 read A  chunk2 returned line17 without its printed numeral 4, and the
              NUMERALS table runs 3,5,6,7... - a GAP, which desynchronised 28
              downstream numerals.           -> check 3, NUMERAL RUN

So this runs INSIDE the reading agent (before it returns) and AGAIN in the
stitch stage over every chunk on disk. A READ'S SELF-REPORT IS NOT EVIDENCE
ABOUT THE READ, so the second pass is not redundant - it is the one that counts.

WHAT IT CHECKS
--------------
  1. COVERAGE      - one `lineNN |` row per crop in the declared range, in
                     order, none missing, none extra, none duplicated.
                     With --kit-dir, the range is also checked against the
                     crops that actually exist on disk.
  2. FORBIDDEN     - U+017F long-s, ø/Ø, ö/Ö, Cyrillic homoglyphs in LINES.
                     ⚠ `f` written for a long-s is NOT checked and must not be:
                     that is a legitimate f/s adjudication site, by design.
  3. NUMERAL RUN   - the NUMERALS table's printed numerals ascend by exactly 1.
                     A gap, a repeat or a reversal is HARD. --first-numeral
                     anchors the chunk's opening numeral when it is known.
                     ⚠ A numeral that disagrees with the KJV is a FINDING and
                     is reported as printed - this checks the RUN, not the text.
  4. NUMERAL SYNC  - every NUMERALS row's numeral appears as a standalone token
                     inside that same LINES row, and every standalone bare
                     integer in a LINES row appears in the NUMERALS table.
  5. TEXT LOSS     - a line tagged with the vocabulary the STITCHER discards a
                     whole line on, that nevertheless carries a verse numeral.
                     ⚠ Scoped to the stitcher's own RUNHEAD rule, not to prose:
                     a tag family the stitcher KEEPS loses no text and is soft.
  6. STRUCTURE     - the four sections exist and the header declares a range.
                     A section that cannot be located is exit 2, never a pass.

WHAT IT DOES NOT DO
-------------------
  - It NEVER edits the chunk. It prints findings; the reader re-reads the crop.
  - It does not know what the page says and is not a spell-checker.
  - It cannot see a line that was read WRONG, only one read INCONSISTENTLY.
  - 0 findings means "passed these checks", never "read correctly".

DESIGN RULE
-----------
  A CHECK THAT CANNOT RUN DID NOT PASS.
Every section boundary is explicit; a missing section raises (exit 2) instead
of scanning an empty string and printing a clean 0.

USAGE
-----
    PYTHONIOENCODING=utf-8 python tools/thorlaks_chunk_check.py \\
        --file C:/Projects/Hexapla-releases/_work/luke_p65_CROP_READ_CHUNK2.md
    ... --kit-dir C:/Projects/Hexapla-releases/research/_prep/luke_kit2/p65
    ... --first-numeral 3
    ... --selftest

Exit 0 = no hard violation. Exit 1 = at least one. Exit 2 = could not run.

KNOWN-BAD CONTROLS (a gate with no control is a rumour)
    HEXAPLA_NO_CHUNKCHK=1      restores the pre-fix behaviour: the NUMERAL RUN
                               is not checked, which is exactly the hole p65's
                               dropped `4` walked through. --selftest proves the
                               fix in BOTH directions against that control.
"""
import argparse
import io
import os
import re
import sys
import unicodedata

LONG_S = chr(0x17F)

# The four sections, spelled as the workflow's read prompt dictates them. Kept
# EXPLICIT: "the first heading" is how thorlaks_read_check.py once scanned one
# chapter of two and reported a pass.
SEC_RE = {
    "LINES":    re.compile(r"^##\s*LINES\s*$", re.M | re.I),
    "NUMERALS": re.compile(r"^##\s*NUMERALS\s*$", re.M | re.I),
    "HN":       re.compile(r"^##\s*HN\s*$", re.M | re.I),
    "NOTES":    re.compile(r"^##\s*NOTES\s*$", re.M | re.I),
}

# `# Luke idx 65 - CROP READ chunk 2 (line14-line27)`
# ⚠ A chunk may declare MORE THAN ONE range - a wrap chunk carries the head of
# the page and its foot: `(line00-line06, line45-line50)`. Before 2026-09-20
# the single-pair regex simply did not match such a header, so `chunk_check`
# REFUSED (exit 2) and those chunks passed NO check at all. Both of the two on
# disk were live. A check that cannot run did not pass.
HEADER_RE = re.compile(r"^#\s.*?\((line\d{1,3}\s*-\s*line\d{1,3}"
                       r"(?:\s*,\s*line\d{1,3}\s*-\s*line\d{1,3})*)\)\s*$", re.M)
PAIR_RE = re.compile(r"line(\d{1,3})\s*-\s*line(\d{1,3})")

ROW_RE = re.compile(r"^line(\d{1,3})\s*\|(.*)$")

# ⛔ THIS VOCABULARY IS NOT A JUDGEMENT ABOUT PROSE - it is a COPY of the rule
# that actually loses text downstream. `thorlaks_crop_read_stitch.py` drops a
# crop's whole line when, and ONLY when, its opening bracket matches RUNHEAD
# (and CHAP_HINT does not rescue it). So this gate asks the one question that
# matters: DID THE READER TAG A LINE THE STITCHER WILL THROW AWAY?
#
# ⚠ Keep this in step with the stitcher's RUNHEAD. A tag family that the
#   stitcher keeps (`[ornamental initial, illegible under swash]`,
#   `[illegible fragment, cut at crop edge]`) is NOT a text loss, and flagging
#   it HARD would fire on pages that are fine - a gate that flags a page that
#   merged is not a gate. Those become SOFT: internally contradictory, worth a
#   human glance, not a re-read.
DROP_RE = re.compile(
    r"^\s*\[[^\]]*\b(?:running head|page head|not body text|no body text)\b"
    r"[^\]]*\]", re.I)
# The stitcher's own escape: a crop bracketed `[chapter heading, not body text]`
# is a CHAPTER BREAK, not a discarded line.
CHAP_HINT_RE = re.compile(
    r"\[(?:[^\]]*\b(?:chapter|cap\.?|capitule|roman numeral)\b[^\]]*)\]", re.I)
# Any other opening tag that claims something is unreadable. The stitcher KEEPS
# these lines, so they are a soft consistency question only.
VOID_RE = re.compile(
    r"^\s*\[[^\]]*?(no legible text|illegible|blank|nothing legible|no text)"
    r"[^\]]*?\]", re.I)

# A standalone printed verse numeral inside a line of text: a bare integer that
# is not glued to a letter and is not part of a bracketed editorial note.
INLINE_NUM_RE = re.compile(r"(?<![0-9A-Za-z\u00c0-\u024f])([0-9]{1,3})"
                           r"(?![0-9A-Za-z\u00c0-\u024f])")

CROP_RE = re.compile(r"^line(\d{2,3})\.png$")


def die(msg):
    sys.stderr.write("thorlaks_chunk_check: %s\n" % msg)
    sys.exit(2)


def blind():
    return os.environ.get("HEXAPLA_NO_CHUNKCHK") == "1"


def section(text, name):
    """The named section's body, bounded EXPLICITLY at the next `## `.

    Unlike the verse text of a stitched read, a chunk section legitimately
    contains no sub-headings at all, so `## ` IS the right bound here - but the
    section must be FOUND, and a caller asking for one that is absent gets a
    refusal, not an empty string.
    """
    m = SEC_RE[name].search(text)
    if not m:
        die("no `## %s` section - REFUSING to report a pass on a chunk whose "
            "%s cannot be located" % (name, name))
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def rows(body):
    """[(n, text)] for every `lineNN | ...` row, in file order."""
    out = []
    for raw in body.splitlines():
        m = ROW_RE.match(raw.strip())
        if m:
            out.append((int(m.group(1)), m.group(2).strip()))
    return out


def numerals(body):
    """[(line, numeral, word)] from the NUMERALS table, in file order."""
    out = []
    for n, rest in rows(body):
        parts = [p.strip() for p in rest.split("|")]
        if not parts or not parts[0]:
            continue
        m = re.match(r"^(\d{1,3})\b", parts[0])
        if not m:
            continue
        out.append((n, int(m.group(1)), parts[1] if len(parts) > 1 else ""))
    return out


def declared_range(text):
    """-> (want, label). `want` is the UNION of every declared range, ascending;
    it is the COVERAGE DENOMINATOR, so a second range widens what must be
    accounted for - it never narrows it."""
    m = HEADER_RE.search(text)
    if not m:
        die("the `# ...` header does not declare a `(lineAA-lineBB)` range - "
            "REFUSING to guess which crops this chunk was supposed to cover")
    pairs = [(int(a), int(b)) for a, b in PAIR_RE.findall(m.group(1))]
    for lo, hi in pairs:
        if hi < lo:
            die("the header declares a DESCENDING range (line%02d-line%02d) - "
                "REFUSING to guess what was meant" % (lo, hi))
    for (alo, ahi), (blo, bhi) in zip(pairs, pairs[1:]):
        if blo <= ahi:
            die("the header's ranges are not disjoint and ascending "
                "(line%02d-line%02d then line%02d-line%02d) - REFUSING: the "
                "coverage denominator would be ambiguous"
                % (alo, ahi, blo, bhi))
    want = [n for lo, hi in pairs for n in range(lo, hi + 1)]
    label = ", ".join("line%02d-line%02d" % p for p in pairs)
    return want, label, pairs


def check(path, kit_dir=None, first_numeral=None, quiet=False):
    """(hard, soft) - lists of finding strings. Prints its own derivation."""
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    hard, soft = [], []
    say = (lambda s: None) if quiet else (lambda s: sys.stdout.write(s + "\n"))

    want, want_label, want_pairs = declared_range(text)
    # Which declared range a crop sits in. For the ordinary one-range chunk
    # every crop is in range 0 and this changes nothing.
    range_of = {n: i for i, (lo, hi) in enumerate(want_pairs)
                for n in range(lo, hi + 1)}
    lines_body = section(text, "LINES")
    nums_body = section(text, "NUMERALS")
    section(text, "HN")          # presence only; refuses if absent
    notes_body = section(text, "NOTES")
    lrows = rows(lines_body)
    say("file            : %s" % os.path.basename(path))
    say("declared range  : %s (%d crops)" % (want_label, len(want)))
    say("LINES rows      : %d" % len(lrows))

    # ---- 1. COVERAGE -------------------------------------------------------
    got = [n for n, _ in lrows]
    missing = [n for n in want if n not in got]
    extra = [n for n in got if n not in want]
    dupes = sorted({n for n in got if got.count(n) > 1})
    if missing:
        hard.append("COVERAGE: %d crop(s) with NO line: %s"
                    % (len(missing), ", ".join("line%02d" % n for n in missing)))
    if extra:
        hard.append("COVERAGE: line(s) outside the declared range: %s"
                    % ", ".join("line%02d" % n for n in sorted(set(extra))))
    if dupes:
        hard.append("COVERAGE: line(s) listed twice: %s"
                    % ", ".join("line%02d" % n for n in dupes))
    if got != sorted(got):
        hard.append("COVERAGE: rows are not in ascending line order")
    if kit_dir:
        if not os.path.isdir(kit_dir):
            die("--kit-dir %s is not a directory" % kit_dir)
        disk = sorted(int(m.group(1)) for m in
                      (CROP_RE.match(f) for f in os.listdir(kit_dir)) if m)
        scratch = [f for f in os.listdir(kit_dir)
                   if f.startswith("line") and f.endswith(".png")
                   and not CROP_RE.match(f)]
        say("crops on disk   : %d (line%02d-line%02d)%s"
            % (len(disk), disk[0], disk[-1],
               (", %d scratch file(s) IGNORED" % len(scratch)) if scratch else "")
            if disk else "crops on disk   : 0")
        off = [n for n in want if n not in disk]
        if off:
            hard.append("COVERAGE: declared crop(s) not on disk: %s"
                        % ", ".join("line%02d" % n for n in off))

    # ---- 2. FORBIDDEN SORTS ------------------------------------------------
    bad_sorts = []
    for n, t in lrows:
        for ch, why in ((LONG_S, "U+017F long-s"), (u"\u00f8", u"o with stroke"),
                        (u"\u00d8", u"O with stroke"), (u"\u00f6", u"o umlaut"),
                        (u"\u00d6", u"O umlaut")):
            if ch in t:
                bad_sorts.append((n, why, t.count(ch)))
    cyr = [(n, c) for n, t in lrows for c in t
           if "CYRILLIC" in unicodedata.name(c, "")]
    say("forbidden sorts : %d" % len(bad_sorts))
    say("Cyrillic        : %d" % len(cyr))
    for n, why, k in bad_sorts:
        hard.append("FORBIDDEN SORT: line%02d carries %d x %s - the convention "
                    "is SETTLED and this is a re-read, not an edit" % (n, k, why))
    if cyr:
        hard.append("CYRILLIC homoglyph(s) (%d) - invisible corruption, on "
                    "line(s) %s" % (len(cyr),
                                    ", ".join("line%02d" % n for n, _ in cyr[:6])))

    # ---- 3. NUMERAL RUN ----------------------------------------------------
    # ⛔ FIRST: a NUMERALS row this parser cannot read is never dropped in
    # SILENCE. `rows()` requires a single `lineNN` key, so a reader's compound
    # key (`line51/52 | 48 | Ad`) vanishes - and with it the numeral it names.
    # That is the Luke idx 64 defect: read A DID table verse 48 across the crop
    # boundary, this gate saw 7 rows where 8 were written, and the RUN check
    # then ran over 41..47 and found no gap. It passed because the row was
    # INVISIBLE, not because the page was sound.  ▶ 2026-09-19.
    # Same family as the stitcher's `unparsed` rows (f9aa584) - loud, not fixed
    # by guessing: only the reader knows which crop a compound key means.
    for raw in nums_body.splitlines():
        s = raw.strip()
        if s.lower().startswith("line") and not ROW_RE.match(s):
            hard.append("NUMERALS row does NOT parse, so this gate NEVER SAW "
                        "the numeral it names - read it yourself and re-table "
                        "it under ONE lineNN key: %r" % s[:100])

    nrows = numerals(nums_body)
    seq = [v for _, v, _ in nrows]
    say("NUMERALS        : %d (%s)"
        % (len(seq), ", ".join(str(v) for v in seq) if seq else "none"))
    if blind():
        say("numeral run     : NOT CHECKED (HEXAPLA_NO_CHUNKCHK=1)")
    else:
        if first_numeral is not None and seq and seq[0] != first_numeral:
            hard.append("NUMERAL RUN: chunk opens at %d, expected %d - the "
                        "previous chunk's last numeral + 1" % (seq[0], first_numeral))
        for i in range(1, len(seq)):
            if seq[i] == seq[i - 1] + 1:
                continue
            # ★ ACROSS THE DECLARED GAP this chunk has NO STANDING. A wrap
            # chunk holds the head of the page and its foot; the crops between
            # them are in OTHER chunks, so whatever the numerals did in there
            # is invisible here. Calling that a drop would invent a defect out
            # of the chunking, and clearing it would invent a pass - so it is
            # reported SOFT, naming the gap, and adjudicated where the whole
            # page is visible (the SEAM check, then part_check).
            # ⛔ NOT a widening of the chapter-break heuristic below: that one
            # is about VALUES, this one is about which crops the chunk covers.
            if range_of.get(nrows[i][0]) != range_of.get(nrows[i - 1][0]):
                soft.append("NUMERAL RUN: %d (line%02d) follows %d (line%02d) "
                            "ACROSS THE DECLARED GAP - the crops between them "
                            "are in other chunks, so this chunk cannot tell a "
                            "drop from a chapter break. Not adjudicated here; "
                            "the page-level check owns it."
                            % (seq[i], nrows[i][0], seq[i - 1], nrows[i - 1][0]))
                continue
            # A CHAPTER BREAK looks like a reversal and is not a defect: idx 62
            # runs Luke 9:40-62 then 10:1-16, so its table reads ... 62, 2 ...
            # ⚠ Reported, never suppressed - a stitch that MISSED a chapter
            #   break is wrong, so the reader must have said which it is.
            if seq[i] <= 3 and seq[i - 1] >= 10:
                soft.append("CHAPTER BREAK: the run drops %d -> %d at line%02d. "
                            "Not a defect IF a `Cap. N` heading is on this page "
                            "- and the NOTES must say so, because a stitch that "
                            "missed a chapter break is WRONG."
                            % (seq[i - 1], seq[i], nrows[i][0]))
                continue
            kind = ("gap" if seq[i] > seq[i - 1] + 1 else
                    "repeat" if seq[i] == seq[i - 1] else "reversal")
            gone = [str(v) for v in range(seq[i - 1] + 1, seq[i])]
            # ⚠ THE ESCAPE, and it is deliberately not a flag. A numeral the
            # PRINT itself omits, or that the crop edge cut off, is a FINDING
            # about the page and must not be an unclearable gate - but it must
            # be DECLARED, in the NOTES, naming the numeral. A hedge is a
            # correct answer; silence is not.
            declared = gone and all(
                re.search(r"\b%s\b" % v, notes_body) for v in gone) and \
                re.search(r"not printed|no numeral|absent|unnumbered|damaged|"
                          r"cut off|cropped|torn|obscured|illegible",
                          notes_body, re.I)
            # A REPEAT the print really has (Luke idx 71 line10 prints «35»
            # twice; owner ruled FILE BY POSITION, 2026-09-23). Nothing is
            # «gone», so the gap escape above can never clear it. It needs ONE
            # NOTES line naming the repeated numeral AND saying it is printed
            # twice - on the same line, so a stray «35» elsewhere cannot
            # blanket it. A reversal has no escape.
            if kind == "repeat" and not declared:
                declared = any(
                    re.search(r"\b%d\b" % seq[i], ln) and
                    re.search(r"printed twice|twice|repeated|repeat", ln, re.I)
                    for ln in notes_body.splitlines())
            if declared:
                soft.append("NUMERAL RUN: %d follows %d (line%02d) - a %s, and "
                            "the NOTES declare it. Reported as printed, never "
                            "corrected." % (seq[i], seq[i - 1], nrows[i][0], kind))
                continue
            hard.append("NUMERAL RUN: %d follows %d (line%02d) - a %s; %s "
                        "missing. Either the crop was misread (re-read it) or "
                        "the print really omits it - and then SAY SO in NOTES, "
                        "naming the numeral. Silence is not a finding."
                        % (seq[i], seq[i - 1], nrows[i][0], kind,
                           ", ".join(gone) if gone else "a numeral"))
        if nrows and [n for n, _, _ in nrows] != sorted(n for n, _, _ in nrows):
            hard.append("NUMERAL RUN: the table's lineNN column is not ascending")

    # ---- 4. NUMERAL SYNC ---------------------------------------------------
    by_line = {}
    for n, t in lrows:
        by_line[n] = t
    tabled = {}
    for n, v, _ in nrows:
        tabled.setdefault(n, set()).add(v)
    for n, v, w in nrows:
        if n not in by_line:
            hard.append("NUMERAL SYNC: the table addresses line%02d, which has "
                        "no LINES row" % n)
            continue
        inline = {int(x) for x in INLINE_NUM_RE.findall(by_line[n])}
        if v not in inline:
            # A numeral printed at the very end of a line legitimately governs
            # the NEXT line's opening word; the reader notes that in the word
            # column. Only flag it when it is nowhere on either line.
            nxt = {int(x) for x in INLINE_NUM_RE.findall(by_line.get(n + 1, ""))}
            if v not in nxt:
                # SOFT on purpose. A reader that tables a verse-opening numeral
                # without writing it inline is the common shape on a chunk's
                # first line, and idx 62 merged carrying it; the stitcher takes
                # the numeral from the table. The RUN above is the hard
                # instrument - a numeral that is missing from BOTH shows there.
                soft.append("NUMERAL SYNC: table says line%02d carries the "
                            "printed numeral %d (%s) but no such numeral is in "
                            "that line's text - tabled, not transcribed"
                            % (n, v, w[:24]))
    for n, t in lrows:
        for x in {int(x) for x in INLINE_NUM_RE.findall(t)}:
            if x not in tabled.get(n, set()) and x not in tabled.get(n - 1, set()):
                soft.append("NUMERAL SYNC: line%02d's text carries a bare %d "
                            "that the NUMERALS table does not list" % (n, x))

    # ---- 5. TAG CONTRADICTION ---------------------------------------------
    dropped = voids = 0
    for n, t in lrows:
        m = DROP_RE.match(t)
        if m and not CHAP_HINT_RE.search(t):
            dropped += 1
            after = re.sub(r"\[[^\]]*\]", "", t[m.end():]).strip()
            if n in tabled:
                # p63's exact defect: line03 tagged a running head while
                # carrying the opening of Luke 10:19. The stitcher discarded
                # the whole line and 10:19-20 were lost.
                hard.append("TEXT LOSS: line%02d opens with %r, which is the "
                            "tag the STITCHER DISCARDS THE WHOLE LINE ON - yet "
                            "the NUMERALS table gives it a printed verse "
                            "numeral (%s). A running head has no verse numeral. "
                            "Re-read line%02d: if it carries body text, drop "
                            "the tag; a TAG NEVER REPLACES TEXT."
                            % (n, m.group(0).strip()[:44],
                               ", ".join(str(v) for v in sorted(tabled[n])), n))
            elif len(after) >= 12:
                # A real running head DOES carry its own text and is meant to
                # go (idx 62 line00). Position is the only other signal, and it
                # is a heuristic, so it is SOFT.
                soft.append("TEXT LOSS?: line%02d opens with %r and the "
                            "stitcher will DISCARD its %d characters of text "
                            "(%r...). Expected at line00-line02; confirm this "
                            "crop really is apparatus."
                            % (n, m.group(0).strip()[:44], len(after),
                               after[:40]))
        elif VOID_RE.match(t):
            voids += 1
            m2 = VOID_RE.match(t)
            after = re.sub(r"\[[^\]]*\]", "", t[m2.end():]).strip()
            if len(after) >= 12:
                # The stitcher KEEPS these, so no text is lost; the read is
                # merely inconsistent with itself.
                soft.append("TAG INCONSISTENCY: line%02d opens %r yet gives %d "
                            "characters of text. No text is lost (the stitcher "
                            "keeps this line) - but say WHAT is illegible."
                            % (n, m2.group(0).strip()[:44], len(after)))
    say("tags            : %d stitcher-dropped, %d void" % (dropped, voids))

    say("")
    for f in hard:
        say("[X] %s" % f)
    for f in soft:
        say("[.] %s" % f)
    if not hard and not soft:
        say("[ok] no findings - passed these checks (NOT 'read correctly')")
    elif not hard:
        say("[ok] no HARD finding")
    return hard, soft


# ---------------------------------------------------------------------------
# SELFTEST - the rules proved in BOTH directions on fixtures.
# ⛔ These fixtures are not the corpus. They exist because the live corpus
#    cannot demonstrate a failure the tool is supposed to prevent.
# ---------------------------------------------------------------------------
FIX_HEAD = u"# Luke idx 99 - CROP READ chunk 1 (line00-line03)\n\n## LINES\n"
FIX_TAIL = u"\n## HN\n\n## NOTES\n- none\n"


def _fixture(tmp, lines, nums, notes=u"- none\n", head=None):
    body = ((head or FIX_HEAD) + "".join(lines) + "\n## NUMERALS\n" + "".join(nums)
            + u"\n## HN\n\n## NOTES\n" + notes)
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(body)
    return tmp


def selftest():
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "_chunkchk_fixture.md")
    ok = True

    def run(label, lines, nums, want_hard, kw=None, notes=u"- none\n",
            head=None):
        _fixture(tmp, lines, nums, notes, head=head)
        hard, _ = check(tmp, quiet=True, **(kw or {}))
        got = bool(hard)
        good = got == want_hard
        print("  %-46s hard=%-5s want=%-5s %s"
              % (label, got, want_hard, "ok" if good else "FAIL"))
        if not good:
            for h in hard:
                print("      %s" % h)
        return good

    CLEAN = [u"line00 | [running head, not body text] S.Lucae\n",
             u"line01 | 3 Fyrer þui huad þier\n",
             u"line02 | Suefnhufu huifled i AEyra. 4\n",
             u"line03 | 5 AEn eg vil syna ydur\n"]
    CLEAN_N = [u"line01 | 3 | Fyrer\n", u"line02 | 4 | [HN]n\n",
               u"line03 | 5 | AEn\n"]

    print("thorlaks_chunk_check selftest")
    ok &= run("clean chunk passes", CLEAN, CLEAN_N, False)

    # ★ A WRAP chunk declares TWO ranges - the head of the page and its foot.
    # Until 2026-09-20 the header regex did not match, so `chunk_check` refused
    # and the chunk passed no check at all. Three ways, because "it stopped
    # refusing" is not the claim: the second range must be IN the coverage
    # denominator, and the GAP between the ranges must stay OUT of it.
    WRAP_HEAD = (u"# Luke idx 99 - CROP READ chunk 1 "
                 u"(line00-line01, line03-line04)\n\n## LINES\n")
    WRAP = [u"line00 | [running head, not body text] S.Lucae\n",
            u"line01 | 3 Fyrer þui huad þier\n",
            u"line03 | 4 AEn eg vil syna ydur\n",
            u"line04 | Suefnhufu huifled i AEyra.\n"]
    WRAP_N = [u"line01 | 3 | Fyrer\n", u"line03 | 4 | AEn\n"]
    ok &= run("a two-range wrap header is READ, and passes", WRAP, WRAP_N,
              False, head=WRAP_HEAD)
    ok &= run("a hole in the SECOND range is HARD", WRAP[:3], WRAP_N, True,
              head=WRAP_HEAD)
    ok &= run("a line in the GAP between the ranges is HARD",
              WRAP[:2] + [u"line02 | Suefnhufu huifled i AEyra.\n"] + WRAP[2:],
              WRAP_N, True, head=WRAP_HEAD)

    # ★ And the RUN check across that gap. p66/p67 read B both open on the page
    # head and close on its foot, so their tables read `... 36, 7 ...`: the
    # crops in between are in OTHER chunks. That discontinuity is not evidence
    # either way, so it is SOFT - but a gap INSIDE one range still has to be
    # HARD, or the escape has blanketed the whole chunk.
    W2_HEAD = (u"# Luke idx 99 - CROP READ chunk 1 "
               u"(line00-line02, line04-line05)\n\n## LINES\n")
    W2 = [u"line00 | [running head, not body text] S.Lucae\n",
          u"line01 | 3 Fyrer þui huad þier\n",
          u"line02 | 4 AEn eg vil syna ydur\n",
          u"line04 | 9 Suefnhufu huifled i AEyra\n",
          u"line05 | 10 Fyrer þui huad þier\n"]
    ok &= run("a run discontinuity ACROSS the gap is not HARD", W2,
              [u"line01 | 3 | Fyrer\n", u"line02 | 4 | AEn\n",
               u"line04 | 9 | Suefnhufu\n", u"line05 | 10 | Fyrer\n"],
              False, head=W2_HEAD)
    ok &= run("a run gap INSIDE one range is still HARD", W2,
              [u"line01 | 3 | Fyrer\n", u"line02 | 5 | AEn\n",
               u"line04 | 9 | Suefnhufu\n", u"line05 | 10 | Fyrer\n"],
              True, head=W2_HEAD)

    # ★ Luke idx 64, verse 48: a compound line key the row parser cannot read.
    # Before 2026-09-19 this row VANISHED and the gate reported one fewer
    # NUMERALS row without a word, so the RUN check found no gap. Both ways:
    # the compound key is HARD, and the same numeral under ONE key is clean.
    ok &= run("a NUMERALS row with a compound lineNN key is HARD", CLEAN,
              CLEAN_N[:2] + [u"line03/04 | 5 | AEn\n"], True)
    ok &= run("the same row under ONE lineNN key passes", CLEAN, CLEAN_N, False)

    # p65's defect: the printed 4 dropped, so the run goes 3 -> 5.
    P65 = list(CLEAN)
    P65[2] = u"line02 | Suefnhufu huifled i AEyra.\n"
    ok &= run("p65: dropped numeral leaves a run gap", P65,
              [u"line01 | 3 | Fyrer\n", u"line03 | 5 | AEn\n"], True)

    # THE ESCAPE, both ways: a gap the print really has, DECLARED in NOTES,
    # must not be an unclearable gate - and an undeclared one must still be.
    ok &= run("a declared gap is SOFT", P65,
              [u"line01 | 3 | Fyrer\n", u"line03 | 5 | AEn\n"], False,
              notes=u"- the printed numeral 4 is NOT PRINTED on this page; the\n"
                    u"  verse opens unnumbered at line02.\n")
    ok &= run("a gap declared without the numeral stays HARD", P65,
              [u"line01 | 3 | Fyrer\n", u"line03 | 5 | AEn\n"], True,
              notes=u"- a numeral somewhere here is not printed.\n")

    # p71's shape: the print repeats a numeral. Declared on ONE NOTES line
    # (numeral + «twice») it is SOFT; undeclared, or the numeral and the word
    # on different lines, it stays HARD.
    REP_N = [u"line01 | 3 | Fyrer\n", u"line03 | 3 | AEn\n"]
    ok &= run("an undeclared repeat is HARD", CLEAN, REP_N, True)
    ok &= run("a declared repeat is SOFT", CLEAN, REP_N, False,
              notes=u"- the printed numeral 3 is PRINTED TWICE (line01, line03).\n")
    ok &= run("repeat word and numeral on split lines stay HARD", CLEAN,
              REP_N, True, notes=u"- a numeral is printed twice.\n- see 3.\n")

    # p64's defect: long-s written into the verse text.
    P64 = list(CLEAN)
    P64[1] = u"line01 | 3 Fyrer \u017fui huad \u017eier\n"
    ok &= run("p64: U+017F long-s is HARD", P64, CLEAN_N, True)

    # p63's defect: a non-body tag over a line that carries body text.
    P63 = list(CLEAN)
    P63[2] = (u"line02 | [running head/paragraph mark, not body text: inf] "
              u"hrapa af [HN]imne/ Siacd. 4\n")
    ok &= run("p63: tag + body text is HARD", P63, CLEAN_N, True)

    # coverage
    ok &= run("a missing crop is HARD", CLEAN[:3], CLEAN_N, True)
    DUP = CLEAN + [u"line03 | 5 AEn eg vil syna ydur\n"]
    ok &= run("a duplicated crop is HARD", DUP, CLEAN_N, True)

    # numeral sync
    DESYNC = list(CLEAN)
    ok &= run("a desynchronised numeral run is HARD", DESYNC,
              [u"line01 | 3 | Fyrer\n", u"line02 | 4 | x\n",
               u"line03 | 7 | AEn\n"], True)

    # the anchor
    ok &= run("--first-numeral mismatch is HARD", CLEAN, CLEAN_N, True,
              {"first_numeral": 9})
    ok &= run("--first-numeral match passes", CLEAN, CLEAN_N, False,
              {"first_numeral": 3})

    # KNOWN-BAD control: with the run unchecked, p65's defect walks through.
    os.environ["HEXAPLA_NO_CHUNKCHK"] = "1"
    bad = run("KNOWN-BAD: run unchecked lets p65 through", P65,
              [u"line01 | 3 | Fyrer\n", u"line03 | 5 | AEn\n"], False)
    del os.environ["HEXAPLA_NO_CHUNKCHK"]
    ok &= bad

    # ---- THE SEAM, which is what idx 65 cost 4 hours to find -------------
    # Two chunks, each internally consecutive, each rc 0 ALONE - and a numeral
    # dropped in the gap between them. This is the p65 read B defect exactly.
    import tempfile as _tf
    seamdir = os.path.join(_tf.gettempdir(), "_chunkchk_seam", "_work")
    if not os.path.isdir(seamdir):
        os.makedirs(seamdir)

    def seam_fixture(second_opens_at):
        c1 = (u"# Luke idx 98 - CROP READ chunk 1 (line00-line01)\n\n## LINES\n"
              u"line00 | [running head, not body text] S.Lucae\n"
              u"line01 | 52 Ve þr sem\n\n## NUMERALS\nline01 | 52 | Ve\n"
              u"\n## HN\n\n## NOTES\n- none\n")
        c2 = (u"# Luke idx 98 - CROP READ chunk 2 (line02-line03)\n\n## LINES\n"
              u"line02 | %d Beitande þr\nline03 | %d Fyrer þui\n\n## NUMERALS\n"
              u"line02 | %d | Beitande\nline03 | %d | Fyrer\n"
              u"\n## HN\n\n## NOTES\n- none\n"
              % (second_opens_at, second_opens_at + 1,
                 second_opens_at, second_opens_at + 1))
        for i, body in ((1, c1), (2, c2)):
            with io.open(os.path.join(seamdir, "luke_p98_CROP_READ_CHUNK%d.md" % i),
                         "w", encoding="utf-8") as fh:
                fh.write(body)

    for opens, want, label in ((53, False, "a continuous seam passes"),
                               (54, True, "a numeral DROPPED ON THE SEAM is HARD")):
        seam_fixture(opens)
        h, _ = check_read(os.path.dirname(seamdir), "Luke", "p98", "A")
        good = bool(h) == want
        print("  %-46s hard=%-5s want=%-5s %s"
              % (label, bool(h), want, "ok" if good else "FAIL"))
        ok &= good
    # ⛔ and the control that makes the point: with 54, EACH CHUNK ALONE passes.
    seam_fixture(54)
    alone = [bool(check(os.path.join(seamdir,
                                     "luke_p98_CROP_READ_CHUNK%d.md" % i),
                        quiet=True)[0]) for i in (1, 2)]
    good = alone == [False, False]
    print("  %-46s %s %s" % ("...yet each chunk ALONE passes", alone,
                             "ok" if good else "FAIL"))
    ok &= good
    # ★★ THE SAME GAP, THE OPPOSITE CAUSE. Luke idx 65 read B: the numeral run
    # goes 52 -> 54, but the crop between them CARRIES THE WHOLE OF VERSE 53.
    # Nothing was dropped; a row was missing from the NUMERALS table. The gate
    # used to print «DROPPED ... re-read the crops» for both, and two runs were
    # launched on that reading. A verse's text has to live on some crop, so the
    # two causes are told apart for free.
    # ▶ research/_evidence/thorlaks_p65_was_never_a_dropped_verse_2026-09-18.md
    c1 = (u"# Luke idx 99 - CROP READ chunk 1 (line00-line01)\n\n## LINES\n"
          u"line00 | [running head, not body text] S.Lucae\n"
          u"line01 | 52 Ve þr sem\n\n## NUMERALS\nline01 | 52 | Ve\n"
          u"\n## HN\n\n## NOTES\n- none\n")
    c2 = (u"# Luke idx 99 - CROP READ chunk 2 (line02-line03)\n\n## LINES\n"
          u"line02 | [HN]n þa hn habde þuilikt til þra talad\n"
          u"line03 | 54 Beitande þr\n\n## NUMERALS\nline03 | 54 | Beitande\n"
          u"\n## HN\n\n## NOTES\n- none\n")
    for i, body in ((1, c1), (2, c2)):
        with io.open(os.path.join(seamdir, "luke_p99_CROP_READ_CHUNK%d.md" % i),
                     "w", encoding="utf-8") as fh:
            fh.write(body)
    h, _ = check_read(os.path.dirname(seamdir), "Luke", "p99", "A")
    txt = " ".join(h)
    good = bool(h) and "MIS-ADDRESSED" in txt and "DO NOT RE-READ" in txt
    print("  %-46s %s" % ("a numeral gap OVER TEXT is MIS-ADDRESSED",
                          "ok" if good else "FAIL"))
    ok &= good
    # ...and the known-bad control: blinded, it calls the same file a drop.
    os.environ["HEXAPLA_NO_SEAMCAUSE"] = "1"
    h2, _ = check_read(os.path.dirname(seamdir), "Luke", "p99", "A")
    del os.environ["HEXAPLA_NO_SEAMCAUSE"]
    good = bool(h2) and "DROPPED ON THE BOUNDARY" in " ".join(h2)
    print("  %-46s %s" % ("  ...HEXAPLA_NO_SEAMCAUSE=1 calls it a drop",
                          "ok" if good else "FAIL"))
    ok &= good
    for i in (1, 2):
        os.remove(os.path.join(seamdir, "luke_p99_CROP_READ_CHUNK%d.md" % i))

    for i in (1, 2):
        os.remove(os.path.join(seamdir, "luke_p98_CROP_READ_CHUNK%d.md" % i))

    # ★ A WRAP CHUNK (page head + page foot in one file) seams with chunk2 at
    # its HEAD range, not at the file's last numeral. Luke idx 66/67 read B
    # 2026-09-20: «ends at 10, next opens at 15» with 11-14 in the same file.
    c1 = (u"# Luke idx 97 - CROP READ chunk 1 (line00-line01, line04-line05)\n\n"
          u"## LINES\nline00 | [running head, not body text] S.Lucae\n"
          u"line01 | 52 Ve þr sem\nline04 | 7 Enn hañ\nline05 | 8 Nær þu\n\n"
          u"## NUMERALS\nline01 | 52 | Ve\nline04 | 7 | Enn\nline05 | 8 | Nær\n"
          u"\n## HN\n\n## NOTES\n- none\n")
    c2 = (u"# Luke idx 97 - CROP READ chunk 2 (line02-line03)\n\n## LINES\n"
          u"line02 | 53 Beitande þr\nline03 | 54 Fyrer þui\n\n## NUMERALS\n"
          u"line02 | 53 | Beitande\nline03 | 54 | Fyrer\n"
          u"\n## HN\n\n## NOTES\n- none\n")
    for i, body in ((1, c1), (2, c2)):
        with io.open(os.path.join(seamdir, "luke_p97_CROP_READ_CHUNK%d.md" % i),
                     "w", encoding="utf-8") as fh:
            fh.write(body)
    h, _ = check_read(os.path.dirname(seamdir), "Luke", "p97", "A")
    good = not any("SEAM" in x for x in h)
    print("  %-46s %s" % ("a WRAP chunk seams at its head range",
                          "ok" if good else "FAIL"))
    ok &= good
    os.environ["HEXAPLA_NO_WRAPSEAM"] = "1"
    h2, _ = check_read(os.path.dirname(seamdir), "Luke", "p97", "A")
    del os.environ["HEXAPLA_NO_WRAPSEAM"]
    good = any("SEAM" in x for x in h2)
    print("  %-46s %s" % ("  ...HEXAPLA_NO_WRAPSEAM=1 seams at the foot",
                          "ok" if good else "FAIL"))
    ok &= good
    for i in (1, 2):
        os.remove(os.path.join(seamdir, "luke_p97_CROP_READ_CHUNK%d.md" % i))

    # a chunk with no NUMERALS section must REFUSE, not pass
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(FIX_HEAD + "".join(CLEAN))
    try:
        check(tmp, quiet=True)
        print("  %-46s REFUSED=False want=True  FAIL" % "a missing section refuses")
        ok = False
    except SystemExit as e:
        good = e.code == 2
        print("  %-46s exit=%s want=2 %s"
              % ("a missing section refuses (exit 2)", e.code,
                 "ok" if good else "FAIL"))
        ok &= good

    os.remove(tmp)
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def read_chunks(data, book, page, series):
    """Every chunk of ONE read, in chunk order, with its declared range."""
    tag = "CROP_READ" if series.upper() == "A" else "CROP_READ%s" % series.upper()
    pat = os.path.join(data, "_work",
                       "%s_%s_%s_CHUNK*.md" % (book.lower(), page, tag))
    import glob as _glob
    files = sorted(_glob.glob(pat),
                   key=lambda p: int(re.search(r"CHUNK(\d+)", p).group(1)))
    if not files:
        die("no chunk files match %s - a read that cannot be located is not a "
            "read that passed" % pat)
    return files


def check_read(data, book, page, series, kit_dir=None):
    """Screen a WHOLE READ: every chunk, AND THE SEAMS BETWEEN THEM.

    ⛔ THIS IS THE CHECK THAT THE PER-CHUNK PASS CANNOT MAKE, and idx 65 is why
    it exists. On 2026-09-18 read B's chunk1 ended at the printed numeral 52 and
    chunk2 opened at 54: Luke 11:53 was dropped EXACTLY ON THE CHUNK BOUNDARY.
    Every chunk was internally consecutive, so all 9 chunks returned rc 0 - nine
    plausible clean numbers - and the page still failed two stages later, at the
    brief tool's key comparison.

      A RUN CHECKED ONLY INSIDE ITS OWN CHUNK HAS A HOLE AT EVERY SEAM.

    Chunk boundaries are also exactly where read A and read B are OFFSET from
    each other, so a seam defect lands in only one read and looks like a
    disagreement about the text rather than a dropped verse.
    """
    files = read_chunks(data, book, page, series)
    print("=" * 68)
    print("READ %s: %s %s - %d chunk(s)" % (series.upper(), book, page, len(files)))
    print("=" * 68)
    hard, soft = [], []
    # (numeral, chunk name, the crop it sits on, that chunk's LINES rows)
    tail = None
    for f in files:
        h, s = check(f, kit_dir=kit_dir)
        hard += ["%s: %s" % (os.path.basename(f), x) for x in h]
        soft += ["%s: %s" % (os.path.basename(f), x) for x in s]
        with io.open(f, encoding="utf-8") as fh:
            _text = fh.read()
        nrows = numerals(section(_text, "NUMERALS"))
        lrows = dict(rows(section(_text, "LINES")))
        print("")
        if nrows and tail is not None:
            prev, prevf, prevline, prevlines, prevnrows = tail
            first = nrows[0][1]
            firstline = nrows[0][0]
            # ⛔ A WRAP CHUNK'S LAST NUMERAL IS NOT ITS SEAM NUMERAL. Read B's
            # chunk1 holds the page HEAD (line00-06) and its FOOT (line49-55);
            # the file's last numeral is the foot's, but the seam with chunk2
            # is at line06. Measured 2026-09-20 on Luke idx 66 AND idx 67: the
            # check reported «ends at 10 (line53), next opens at 15 - 11..14
            # DROPPED», with the four numerals sitting on line01-05 in the same
            # file. So the seam numeral is the LAST one on a crop BEFORE the
            # next chunk's first crop. Known-bad control: HEXAPLA_NO_WRAPSEAM=1.
            firstcrop = min(lrows) if lrows else firstline
            if not os.environ.get("HEXAPLA_NO_WRAPSEAM"):
                before = [(r[0], r[1]) for r in prevnrows if r[0] < firstcrop]
                if before:
                    prevline, prev = before[-1]
            if first == prev + 1:
                pass
            elif first <= 3 and prev >= 10:
                soft.append("SEAM %s -> %s: the run drops %d -> %d, a CHAPTER "
                            "BREAK across the seam. Confirm the `Cap. N` heading."
                            % (prevf, os.path.basename(f), prev, first))
            else:
                gone = ", ".join(str(v) for v in range(prev + 1, first))
                # ⛔⛔ A NUMERAL GAP HAS TWO CAUSES AND THEY HAVE OPPOSITE
                # REMEDIES. Text can be MISSING, or it can be PRESENT and
                # MIS-ADDRESSED because the reader transcribed the line and
                # simply never tabled its numeral. This branch used to print
                # «DROPPED ON THE BOUNDARY ... re-read the crops» for both,
                # and Luke idx 65 was re-run twice on that reading: 5.4M
                # subagent tokens against a defect that was one missing row
                # in a NUMERALS table. Read A had the numeral; the crop had
                # it printed; read B's LINES row carried the whole verse.
                # ▶ research/_evidence/thorlaks_p65_was_never_a_dropped_verse_2026-09-18.md
                #
                # The two are told apart for FREE, with no vision: a verse's
                # text has to live on some crop, so if the crops BETWEEN the
                # two printed numerals carry body text, the verse is there.
                # Known-bad control: HEXAPLA_NO_SEAMCAUSE=1 restores the old
                # single message.
                blind_cause = bool(os.environ.get("HEXAPLA_NO_SEAMCAUSE"))
                between = []
                if not blind_cause:
                    for n in range(prevline + 1, firstline):
                        t = prevlines.get(n, lrows.get(n, ""))
                        # apparatus-only crops (a whole bracket) are not text
                        if t and not re.match(r"^\s*\[[^\]]*\]\s*$", t):
                            between.append(n)
                if between:
                    # ⛔ Do NOT name one crop as «the» one: the run-on tail of
                    # the previous verse and the head of the unnumbered one
                    # both live in this span, and which crop the numeral sits
                    # on is a question for the pixels, not for this script.
                    hard.append(
                        "SEAM %s -> %s: the printed run goes %d -> %d, so %s "
                        "has NO numeral - but line%02d-line%02d DO carry body "
                        "text, so the verse is PRESENT and MIS-ADDRESSED: a "
                        "row is missing from the NUMERALS table, not a verse "
                        "from the page. ⛔ DO NOT RE-READ THE PAGE. Open those "
                        "%d crop(s) and find where the new verse starts - the "
                        "numeral is small and tight to the left edge, often at "
                        "a swash capital a reader latched onto instead. Add "
                        "`lineNN | %s | <first word>` to that chunk's NUMERALS "
                        "table and re-stitch. ▶ research/_evidence/"
                        "thorlaks_p65_was_never_a_dropped_verse_2026-09-18.md"
                        % (prevf, os.path.basename(f), prev, first,
                           gone if gone else "a numeral",
                           between[0], between[-1], len(between),
                           str(prev + 1)))
                elif blind_cause:
                    hard.append(
                        "SEAM %s -> %s: chunk ends at the printed numeral %d "
                        "and the next opens at %d - %s DROPPED ON THE "
                        "BOUNDARY. Neither chunk can see this on its own and "
                        "both pass alone. Re-read the crops on either side of "
                        "the seam."
                        % (prevf, os.path.basename(f), prev, first,
                           gone if gone else "a numeral"))
                else:
                    hard.append(
                        "SEAM %s -> %s: chunk ends at the printed numeral %d "
                        "and the next opens at %d - %s DROPPED ON THE "
                        "BOUNDARY, and NO crop between them carries body "
                        "text, so the text really is missing. Neither chunk "
                        "can see this on its own and both pass alone. Re-read "
                        "the crops on either side of the seam."
                        % (prevf, os.path.basename(f), prev, first,
                           gone if gone else "a numeral"))
        if nrows:
            tail = (nrows[-1][1], os.path.basename(f), nrows[-1][0], lrows, nrows)
    print("=" * 68)
    print("READ %s TOTAL: %d hard, %d soft" % (series.upper(), len(hard), len(soft)))
    for x in hard:
        print("[X] %s" % x)
    for x in soft:
        print("[.] %s" % x)
    if not hard:
        print("[ok] no HARD finding across %d chunk(s) AND their seams"
              % len(files))
    return hard, soft


def main():
    ap = argparse.ArgumentParser(
        description="Screen one CROP READ CHUNK before it is stitched.")
    ap.add_argument("--file", help="the _CROP_READ*_CHUNKn.md to screen")
    ap.add_argument("--read", action="store_true",
                    help="screen a WHOLE READ - every chunk AND THE SEAMS. "
                         "Needs --book/--page/--series. ⛔ A per-chunk pass "
                         "cannot see a numeral dropped on a chunk boundary.")
    ap.add_argument("--book")
    ap.add_argument("--page")
    ap.add_argument("--series", default="A")
    ap.add_argument("--data", default=r"C:\Projects\Hexapla-releases")
    ap.add_argument("--kit-dir", help="the page's crop directory, to check the "
                                      "declared range against the crops on disk")
    ap.add_argument("--first-numeral", type=int,
                    help="the printed numeral this chunk must open at")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.read:
        if not (a.book and a.page):
            ap.error("--read needs --book and --page")
        hard, _ = check_read(a.data, a.book, a.page, a.series, kit_dir=a.kit_dir)
        sys.exit(1 if hard else 0)
    if not a.file:
        ap.error("--file is required (or --read, or --selftest)")
    if not os.path.isfile(a.file):
        die("no such file: %s" % a.file)
    hard, _ = check(a.file, kit_dir=a.kit_dir, first_numeral=a.first_numeral)
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
