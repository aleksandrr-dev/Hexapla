#!/usr/bin/env python
"""Stitch chunked LINE-level crop reads into ONE verse-addressed read file.

WHY THIS EXISTS
---------------
A page's ~55-60 line crops exceed the 25-image Read guard, so a crop read is
commissioned as 4-5 chunks (`_work/<book>_pNN_CROP_READ_CHUNK<K>.md`), each
returning `lineNN | <text>` for its crops. Verses cross chunk boundaries, so
no chunk can return verses; this tool joins the crops in order and cuts the
running text at the PRINTED verse numerals, giving each verse the crop range
it actually sits on. That address is what the adjudication brief and
`thorlaks_adjudicate_merge.py` key on.

WHAT IT GUARANTEES
------------------
  * Coverage is checked: every crop from line00 to the highest number seen
    must be present in exactly one chunk, or the run fails. A missing crop
    that the reader reported as "does not exist" is accepted ONLY if the
    file really is absent from the prep directory.
  * A numeral is taken as a verse boundary only when it is the EXPECTED next
    number; anything else is printed as a finding and left INLINE (row 52: a
    printed count that disagrees is a finding, never corrected).
  * A chapter break is a crop the reader flagged as a chapter numeral or
    heading (`[chapter ...]`, `Cap.`, a bare roman numeral). The next verse
    is then 1. `--chapter` and `--first-verse` seed the page's opening.
  * Output carries `## VERSES` and `## Cap. N` headings that
    `thorlaks_read_check.py` accepts, then the chunks' NUMERALS / HN / NOTES
    sections verbatim as apparatus.
  * ⛔ Nothing is rewritten: text is joined with single spaces, a hyphen at a
    crop end is kept as printed, long-s is NOT converted here (the reader
    was told to write plain s; the screen will catch a slip).
  * ⛔ Refuses to overwrite an existing output.

    python tools/thorlaks_crop_read_stitch.py --book Luke --page p62 \\
        --chapter 9 --first-verse 40 --out _work/luke_p62_read2_2026-09-17.md
"""
import argparse
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

DATA = r"C:\Projects\Hexapla-releases"
LINE_RE = re.compile(r"^\s*line(\d{2})\s*\|\s*(.*?)\s*$")
_CHAP_HINT = re.compile(r"\[(?:[^\]]*\b(?:chapter|cap\.?|capitule|roman numeral)\b[^\]]*)\]", re.I)
# ⛔ A NEGATED chapter mention is not a chapter. Luke idx 67 read B line00 came
# back as `[page header, not a chapter heading: S.Lucæ]` - a correct report -
# and the hint matched the word «chapter», opened Cap. 14 at the running head,
# and every numeral on the page was then «left inline». Known-bad control:
# HEXAPLA_NO_CHAPNEG=1.
_CHAP_NEG = re.compile(r"\[[^\]]*\b(?:not|no|never)\b[^\]]*\b(?:chapter|cap\.?|capitule)\b", re.I)


class _Hint(object):
    """CHAP_HINT.search(t) that is blind to «not a chapter heading»."""
    def search(self, t):
        m = _CHAP_HINT.search(t)
        if m and _CHAP_NEG.search(t) and os.environ.get("HEXAPLA_NO_CHAPNEG") != "1":
            return None
        return m


CHAP_HINT = _Hint()
ROMAN_ONLY = re.compile(r"^\s*\[?\s*(?:Cap\.?\s*)?[IVXLC]{1,6}\.?\s*\]?\s*$")
NONTEXT = re.compile(r"^\s*\[[^\]]*\]\s*$")
# ⛔ A crop the reader OPENS by declaring it carries no body text is apparatus,
# whatever else the line then says. idx 62 line00 came back as
# `[running head, not body text] Euangelium ... XXXI (chapter numeral, right
# margin)` - correctly reported - and the stitcher, which only skipped a crop
# whose WHOLE line was one bracket, tokenised the running head into Luke 9:40.
# Every page has a running head at line00, so this was not one page's defect.
# Known-bad control: HEXAPLA_NO_RUNHEAD=1 restores the old behaviour.
RUNHEAD = re.compile(
    r"^\s*\[[^\]]*\b(?:running head|page head|not body text|no body text)\b[^\]]*\]",
    re.I)


def load_chunks(book, page, series="A"):
    # ⚠ The METHOD CHANGE (owner, 2026-09-17) runs TWO independent crop reads of
    # each page with OFFSET chunk boundaries. Read A writes `_CROP_READ_CHUNK*`,
    # read B writes `_CROP_READB_CHUNK*`. ⛔ Without --series, read B silently
    # re-stitches read A and the diff measures nothing.
    tag = "CROP_READ" if series.upper() == "A" else "CROP_READ%s" % series.upper()
    pat = os.path.join(DATA, "_work", "%s_%s_%s_CHUNK*.md" % (book.lower(), page, tag))
    files = sorted(glob.glob(pat), key=lambda p: int(re.search(r"CHUNK(\d+)", p).group(1)))
    if not files:
        print("[X] no chunk files match %s" % pat)
        sys.exit(1)
    lines, appendix = {}, {"NUMERALS": [], "HN": [], "NOTES": []}
    for f in files:
        text = io.open(f, encoding="utf-8").read()
        sec = None
        for raw in text.splitlines():
            m = re.match(r"^##\s*(LINES|NUMERALS|HN|NOTES)\b", raw, re.I)
            if m:
                sec = m.group(1).upper()
                continue
            if sec == "LINES":
                lm = LINE_RE.match(raw)
                if lm:
                    n = int(lm.group(1))
                    if n in lines:
                        print("[X] line%02d returned by two chunks (%s and earlier)" % (n, os.path.basename(f)))
                        sys.exit(1)
                    lines[n] = lm.group(2)
            elif sec in appendix and raw.strip() and not raw.strip().startswith("#"):
                appendix[sec].append(raw.rstrip())
    return files, lines, appendix


def coverage(lines, book, page, kit):
    prep = os.path.join(DATA, "research", "_prep", kit, page)
    # ⛔ STRICT `lineNN.png` - NOT `line*.png`. A reader that zooms a glyph
    # writes its scratch beside the crops (`line06_full.png`,
    # `line06_kglyph.png` landed in luke_kit2/p63 on 2026-09-17), and the loose
    # glob counted each one as another crop: the gate printed «crops on disk
    # 61 (line00-line58)» for a 59-crop page and still reported a clean pass.
    # ⚠ A plausible-but-wrong count is the failure this project names first -
    # and a scratch file numbered ABOVE the last real crop would have invented
    # a missing crop and BLOCKED a sound page.
    scratch = []
    on_disk = []
    for p in glob.glob(os.path.join(prep, "line*.png")):
        m = re.match(r"^line(\d{2})\.png$", os.path.basename(p))
        if m:
            on_disk.append(int(m.group(1)))
        else:
            scratch.append(os.path.basename(p))
    on_disk = sorted(on_disk)
    if not on_disk:
        print("[X] no crops on disk under %s" % prep)
        sys.exit(1)
    if scratch:
        # ⚠ Named, never counted: the kit directory is the ADDRESSING
        # authority, and anything else in it is somebody's scratch.
        print("[!] %d non-crop `line*.png` file(s) in the kit, IGNORED: %s"
              % (len(scratch), ", ".join(sorted(scratch)[:6])))
    missing = [n for n in on_disk if n not in lines]
    extra = [n for n in lines if n not in on_disk]
    # ⛔ The range and the count must agree, or the gate is describing a
    # directory it has not actually understood.
    span = on_disk[-1] - on_disk[0] + 1
    print("crops on disk %d (line%02d-line%02d), returned %d, missing %s, not-on-disk %s"
          % (len(on_disk), on_disk[0], on_disk[-1], len(lines), missing or "-", extra or "-"))
    if len(on_disk) != span or len(set(on_disk)) != len(on_disk):
        print("[X] the crop numbers are not a contiguous run: %d file(s) over a "
              "span of %d. ⛔ NOT a coverage pass - fix the kit." % (len(on_disk), span))
        sys.exit(1)
    if missing:
        print("[X] %d crop(s) never read - commission them, do not stitch a hole" % len(missing))
        sys.exit(1)
    return on_disk


def is_missing_report(t):
    return bool(re.search(r"\b(does not exist|missing|not found|no such file)\b", t, re.I)) and NONTEXT.match(t)


# A numeral column: a digit run, an optional period, an optional hedge marker.
# `5`, `5.`, `5[?]` all parse; prose like «[unclear mark, possibly 6]» does NOT.
NUM_COL = re.compile(r"^(\d{1,3})\.?(\[\?\])?$")


def numeral_table(appendix_lines):
    """`lineNN | 51 | Nu` rows -> {16: [(51, 'Nu', hedged)]}: a reader sometimes
    drops the numeral from the LINES text and still reports it here (p62 line16).

    The numeral column may carry the project's hedge marker (`5[?]`) and/or a
    trailing parenthetical note; both are accepted, and a hedged numeral is
    named in FINDINGS wherever it is used as a cut point. The hedge is about the
    GLYPH, not the value - and the rescue below still refuses to cut unless the
    tabled word corroborates, so a hedge alone never moves a verse boundary.

    ⛔ A row carrying a digit that does NOT parse is never dropped in silence -
    it comes back in `unparsed` so the caller says so out loud. A cut point that
    vanished without a word is the p63 defect: read A tabled `5[?]` at line47,
    this regex rejected the row, `expect` stuck at 5, and verses 6-11 were each
    declared «out of sequence» and folded inline - 7 verses mis-addressed while
    both reads held identical text.  ▶ 2026-09-19.
    """
    out, unparsed = {}, []
    for raw in appendix_lines:
        cols = [c.strip() for c in raw.split("|")]
        if len(cols) < 3:
            continue
        if not cols[0].lower().startswith("line"):
            continue
        m_line = re.match(r"^line(\d{2})$", cols[0])
        if not m_line:
            # e.g. «line51/52» - a numeral straddling the gap BETWEEN two crops.
            # ⛔ Never guess which crop owns it; but never drop it in silence
            # either: p64's Luke 11:48 lived in exactly such a row (only the «4»
            # of «48» was cut, the «8» fell in the crop gap) and vanished.
            if re.search(r"\d", cols[1]):
                unparsed.append(raw.strip())
            continue
        col = re.sub(r"\s*\([^)]*\)\s*$", "", cols[1]).strip()
        m_num = NUM_COL.match(col)
        if not m_num:
            if re.search(r"\d", cols[1]):
                unparsed.append(raw.strip())
            continue
        if os.environ.get("HEXAPLA_NO_HEDGED_NUMERAL") == "1" and m_num.group(2):
            unparsed.append(raw.strip())     # known-bad control: the old drop
            continue
        toks = cols[2].split()
        out.setdefault(int(m_line.group(1)), []).append(
            (int(m_num.group(1)), toks[0] if toks else "", bool(m_num.group(2))))
    return out, unparsed


# ⚠ NARROWER than CHAP_HINT on purpose: mid-line, only an explicit heading tag
# that carries its roman numeral splits a crop. Readers put drop-cap tags inline
# all the time - `[ornate cap, letter not legible]n er`, `[ornamental initial,
# chapter-opening]`, `[chapter numeral, decorative capital]` - and the broad
# hint opened a false chapter on four of eleven already-merged Luke stitches
# (p62A, p64B, p67A, p67B). Those eleven re-stitch byte-identical with this.
_CHAP_TAG = re.compile(
    r"\[\s*(?:chapter heading|chapter numeral|cap\.)[^\]]*?\b[IVXL]{1,7}\b[^\]]*\]", re.I)
_CHAP_TAG_NOT = re.compile(r"initial|ornat|ornament|drop|decorat|capital|illegible", re.I)


def _segments(lines):
    u"""Yield (lineNN, text) in crop order, SPLITTING a crop at a chapter tag
    that shares the crop with body text.

    ⛔ A CHAPTER HEADING CAN SHARE ITS CROP WITH THE LAST LINE OF THE CHAPTER
    BEFORE IT. luke_kit3 p70 line19 holds the tail of 16:31 stacked over the
    centred «XVII»; p71 line12 and p76 line54 are the same. Written as ONE row,
    `tail text [chapter heading: XVII]` fell through to the token walk, the
    tag's words became verse text and the chapter break was MISSED. Written
    tag-first, `[chapter heading: XVII] tail text` was not a whole-line bracket
    either, so it tokenised the same way. The crop is split into its body
    text, the tag alone (which the heading branch then takes), and any text
    after it. A running-head tag is never split - it is apparatus whole.
    Known-bad control: HEXAPLA_NO_MIDTAG=1.
    """
    for n in sorted(lines):
        t = lines[n].strip()
        m = None
        if (os.environ.get("HEXAPLA_NO_MIDTAG") != "1" and not RUNHEAD.match(t)
                and not NONTEXT.match(t)):
            m = _CHAP_TAG.search(t)
            if m and (_CHAP_NEG.search(m.group(0)) or _CHAP_TAG_NOT.search(m.group(0))):
                m = None
            if m and re.search(r"\brunning\b|\bfolio\b|\bpage head", m.group(0), re.I):
                m = None
        if not m:
            yield n, t
            continue
        before, after = t[:m.start()].strip(), t[m.end():].strip()
        if before:
            yield n, before
        yield n, m.group(0)
        if after:
            yield n, after


def stitch(lines, chapter, verse, numerals=None):
    """Walk crops in order; cut at expected numerals; return verses + findings."""
    numerals = numerals or {}
    verses = []          # [chapter, verse, [tokens], first_line, last_line]
    findings, chapters = [], []
    expect = verse       # the number that opens the NEXT verse
    cur = None
    after_break = False  # the first verse after a chapter heading carries no numeral
    unnumbered_ok = False  # ...and the first PRINTED numeral after it may jump (14:1-2)

    def open_verse(ch, v, n):
        verses.append([ch, v, [], n, n])

    for n, t in _segments(lines):
        if not t or is_missing_report(t):
            continue
        # ⚠ `and not CHAP_HINT` so a crop bracketed `[chapter heading, not body
        # text]` still falls through to the chapter-break branch below.
        # ⚠ A RUNNING HEAD THAT MENTIONS A CHAPTER IS STILL A RUNNING HEAD.
        # Luke idx 66 line00 came back as `[chapter heading: running head
        # "Euangelium" with roman numeral XXXIII]` (A) and `[running/chapter
        # heading: ... folio numeral "XXXIII"]` (B): both readers muddled the
        # words, and the old exemption opened a chapter at the page head in
        # both reads. A tag that says running / folio / page head is the
        # running head whatever else it says; only a tag with NONE of those
        # words and a chapter word is a heading. Control: HEXAPLA_NO_RUNWORDS=1.
        runwords = (re.search(r"\brunning\b|\bfolio\b|\bpage head", t, re.I)
                    if os.environ.get("HEXAPLA_NO_RUNWORDS") != "1" else None)
        if ((RUNHEAD.match(t) or (NONTEXT.match(t) and runwords))
                and (runwords or not CHAP_HINT.search(t))
                and os.environ.get("HEXAPLA_NO_RUNHEAD") != "1"):
            findings.append("line%02d running head, contributed NO text: %s"
                            % (n, t[:70]))
            continue
        if NONTEXT.match(t):
            if CHAP_HINT.search(t) or ROMAN_ONLY.match(t):
                chapter += 1
                expect = 1
                chapters.append((n, chapter, t))
                cur = None
                after_break = True
                unnumbered_ok = True
            else:
                findings.append("line%02d non-text crop: %s" % (n, t))
            continue
        # a bare roman numeral line that the reader did not bracket
        if ROMAN_ONLY.match(t):
            chapter += 1
            expect = 1
            chapters.append((n, chapter, t))
            cur = None
            after_break = True
            unnumbered_ok = True
            continue
        toks = t.split()
        fallback = [x for x in numerals.get(n, []) if x[0] == expect]
        if fallback and re.search(r"(?<!\d)%d(?!\d)" % expect, t):
            fallback = []        # the numeral IS inline; the walk below cuts on it
        queue = list(toks)
        while queue:
            tok = queue.pop(0)
            # ⚠ A NUMERAL GLUED TO ITS NEIGHBOURS IS STILL A NUMERAL (luke_kit3
            # p69, 2026-09-22). The branches below know «14», «ncur.10» and
            # «14Og», but not «Lifnade.14Og» (glued on BOTH sides, read B
            # line01), and a glued numeral never reached the HOLE / UNNUMBERED
            # resync, which only the bare-digit branch runs: «skorta.15» and
            # «hafa.3» (read A, the first numeral after Cap. XVI) were lost, the
            # walk sat at one number for the rest of the page, and BOTH reads of
            # p69 collapsed. So split a glued numeral into its own token WHENEVER
            # THE WALK WOULD ACCEPT IT (expected, a one-hole resync, or the
            # unnumbered jump after a heading) and let the bare-digit branch
            # rule. Anything else stays glued, exactly as before. «6[?]» stays
            # with the branch that owns the hedge. Control: HEXAPLA_NO_GLUESPLIT=1.
            # ⚠ A head or tail that carries a digit of its own is a REFERENCE,
            # not a verse numeral: read B of p69 transcribed the margin note
            # «Matth. 5/18.», and «5/» + «18.» opened verse 18 by the hole rule.
            # Control: HEXAPLA_NO_REFGUARD=1.
            refguard = os.environ.get("HEXAPLA_NO_REFGUARD") != "1"
            gs = re.match(r"^(\D*?[^\d])?(\d{1,3}\.?)([^\d.]\D*)?$" if refguard
                          else r"^(.*?[^\d])?(\d{1,3}\.?)([^\d.].*)?$", tok)
            if (gs and (gs.group(1) or gs.group(3)) and gs.group(3) != "[?]"
                    and not (refguard and re.search(r"/$", gs.group(1) or ""))
                    and os.environ.get("HEXAPLA_NO_GLUESPLIT") != "1"):
                gn = int(gs.group(2).rstrip("."))
                if (gn == expect
                        or (gn == expect + 1 and cur is not None
                            and os.environ.get("HEXAPLA_NO_HOLE") != "1")
                        or (unnumbered_ok and expect < gn <= expect + 2
                            and os.environ.get("HEXAPLA_NO_UNNUMBERED") != "1")):
                    queue[:0] = [x for x in gs.groups() if x]
                    continue
            if after_break and not re.match(r"^1\.?$", tok):
                open_verse(chapter, 1, n)
                cur = verses[-1]
                expect = 2
                after_break = False
            elif after_break:
                after_break = False
            forms = [re.sub(r"[^\w]", "", x).lower() for x in
                     (tok, tok.replace("[HN]", "N"), tok.replace("[HN]", "H"))]
            want = re.sub(r"[^\w]", "", fallback[0][1]).lower()[:2] if fallback else None
            if fallback and want and any(f.startswith(want) for f in forms):
                open_verse(chapter, expect, n)
                cur = verses[-1]
                expect += 1
                findings.append("line%02d numeral «%d» taken from the NUMERALS table (absent from LINES)%s"
                                % (n, fallback[0][0],
                                   " - HEDGED in the table, corroborated by the word «%s»"
                                   % fallback[0][1] if fallback[0][2] else ""))
                fallback = []
            m = re.match(r"^(\d{1,3})\.?$", tok)
            if m:
                num = int(m.group(1))
                if num == expect:
                    open_verse(chapter, num, n)
                    cur = verses[-1]
                    expect += 1
                    unnumbered_ok = False
                    continue
                # ⚠ THIS PRINT LEAVES THE FIRST VERSE OR TWO OF A CHAPTER
                # UNNUMBERED (Luke 14:1-2, idx 67: the heading, then text,
                # then «3»). Before 2026-09-20 the walk expected 2 forever,
                # left every later numeral inline and reported ONE verse per
                # chapter. So the FIRST printed numeral after a heading may
                # jump: the verses before it stay in verse 1's bucket (the
                # print gives no cut), and the jump is a FINDING, never
                # silent. Only the first numeral after a heading may do
                # this; a jump anywhere else is still out of sequence.
                # ⚠ Bounded at TWO: this print leaves one or two verses
                # unnumbered, never thirty. A larger jump is a mis-detected
                # heading (idx 66's running head) and stays a finding.
                if (unnumbered_ok and expect < num <= expect + 2
                        and os.environ.get("HEXAPLA_NO_UNNUMBERED") != "1"):
                    findings.append("line%02d first numeral after the heading is «%d» - "
                                    "verses %s carry no printed numeral, so their text "
                                    "stays under verse %d (the print gives no cut)"
                                    % (n, num, ", ".join(str(v) for v in range(expect, num)),
                                       expect - 1))
                    open_verse(chapter, num, n)
                    cur = verses[-1]
                    expect = num + 1
                    unnumbered_ok = False
                    continue
                # ⚠ A ONE-NUMERAL HOLE MID-CHAPTER. Luke 14:6 (idx 67) is not
                # printed - both reads, and a pixel re-read of line48, agree
                # - so «7» arrives where 6 is expected. Before 2026-09-20 the
                # walk sat at 6 forever and left 7, 8, 9, 10 inline. A hole
                # of exactly one, with text already open, resyncs: verse
                # `expect`'s text stays under the verse before it (the print
                # gives no cut) and the hole is a FINDING the chunk NOTES
                # must already declare (thorlaks_chunk_check.py makes the
                # reader say so). A reader's DROPPED numeral looks the same
                # here and lands in the same finding, which is the point:
                # it is never silent. Control: HEXAPLA_NO_HOLE=1.
                if (num == expect + 1 and cur is not None
                        and os.environ.get("HEXAPLA_NO_HOLE") != "1"):
                    findings.append("line%02d numeral «%d» is NOT PRINTED before «%d» - verse %d's "
                                    "text stays under verse %d (the print gives no cut); the "
                                    "chunk NOTES must declare the hole"
                                    % (n, expect, num, expect, expect - 1))
                    open_verse(chapter, num, n)
                    cur = verses[-1]
                    expect = num + 1
                    continue
                findings.append("line%02d printed numeral «%s» where %d was expected - left inline"
                                % (n, tok, expect))
            # a numeral glued to a word: «ncur.10» / «amfett.9»
            g = re.match(r"^(.*?[^\d])(\d{1,3})$", tok)
            if g and int(g.group(2)) == expect and cur is not None:
                cur[2].append(g.group(1))
                cur[4] = n
                open_verse(chapter, expect, n)
                cur = verses[-1]
                expect += 1
                continue
            h = re.match(r"^(\d{1,3})\.?([^\d].*)$", tok)
            if h and int(h.group(1)) == expect:
                open_verse(chapter, expect, n)
                cur = verses[-1]
                expect += 1
                if h.group(2).strip() == "[?]":
                    # «6[?]» - the hedge belongs to the NUMERAL, not to the text.
                    # Appending it would open the verse with a [?] the print does
                    # not carry, and a [?] in a verse body means «uncertain
                    # reading» to every adjudicator downstream.
                    findings.append("line%02d numeral «%d» is HEDGED inline (%s); "
                                    "the hedge is on the digit, not on the text"
                                    % (n, h.group(1) and int(h.group(1)), tok))
                    continue
                cur[2].append(h.group(2))
                continue
            if cur is None:
                # text before any numeral on this page: the tail of the
                # previous page's verse, numbered by --first-verse - 1
                open_verse(chapter, expect - 1, n)
                cur = verses[-1]
                cur.append("continued")
            cur[2].append(tok)
            cur[4] = n
    return verses, findings, chapters


def _case(name, lines, chapter, first_verse, env, want, unwanted=()):
    """Run `stitch` once with `env` applied, and report what it did.

    ⚠ The controls are read INSIDE `stitch` at call time, so a case sets the
    variable, calls, and puts it back - no subprocess, and the assertion is
    against this exact code, not against a second copy of it.
    """
    old = {}
    for k, v in env.items():
        old[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        verses, findings, chapters = stitch(dict(lines), chapter, first_verse)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    blob = "\n".join(findings) + "\n" + "\n".join(
        "%d:%d" % (c, v) for c, v, _t, _a, _b in
        [(x[0], x[1], x[2], x[3], x[4]) for x in verses])
    blob += "\nCHAPTERS=%s" % ",".join(str(c) for _n, c, _t in chapters)
    bad = [w for w in want if w not in blob] + \
          [u"(unwanted) " + w for w in unwanted if w in blob]
    return bad, blob


def selftest():
    u"""The four 2026-09-20 stitcher fixes, each asserted BOTH WAYS.

    ⛔ A screen that cannot fail is not a screen. Every case below runs twice:
    once with the fix live (the defect must be gone) and once with the fix's
    own `HEXAPLA_NO_*` control set (the defect must come BACK, by name). A
    case whose known-bad direction still passes is reported as a FAILURE of
    the control, not as a pass.

    The four:
      CHAPNEG   a NEGATED chapter mention (`[..., not a chapter heading: ...]`)
                must not open a chapter.
      RUNWORDS  a running head that mentions a chapter word is still a running
                head, and contributes no text.
      UNNUMBERED  this print leaves the first verse or two of a chapter
                unnumbered; the first printed numeral after a heading may jump
                by <=2, as a FINDING.
      HOLE      a one-numeral hole mid-chapter (Luke 14:6 is not printed)
                resyncs, as a FINDING, instead of leaving every later numeral
                inline.
    """
    cases = [
        # name, lines, chapter, first verse, control var,
        #   fixed: must say / must NOT say, known-bad: must say
        (u"CHAPNEG", {
            0: u"[ornament band, not a chapter heading: Cap. reference]",
            1: u"12 Og hann sagde",
        }, 13, 12, "HEXAPLA_NO_CHAPNEG",
            ([u"non-text crop", u"CHAPTERS="], [u"CHAPTERS=14"]),
            [u"CHAPTERS=14"]),
        (u"RUNWORDS", {
            0: u'[chapter heading: running head "Euangelium" with roman numeral XXXIII]',
            1: u"12 Og hann sagde",
        }, 13, 12, "HEXAPLA_NO_RUNWORDS",
            ([u"running head, contributed NO text", u"CHAPTERS="], [u"CHAPTERS=14"]),
            [u"CHAPTERS=14"]),
        # ⚠ The jump here is TWO, not one, and that is not cosmetic: with
        # HEXAPLA_NO_UNNUMBERED=1 a jump of exactly ONE is still absorbed by
        # the HOLE branch, so a one-jump fixture passes its own known-bad
        # direction and asserts nothing. The two branches overlap; only a
        # jump of two isolates this one.
        (u"UNNUMBERED", {
            0: u"[chapter heading: Cap. XIIII]",
            1: u"Og þad bar til",
            2: u"4 Og Jesus suarade",
        }, 13, 1, "HEXAPLA_NO_UNNUMBERED",
            ([u"first numeral after the heading is «4»", u"14:1", u"14:4"],
             [u"left inline"]),
            [u"left inline"]),
        (u"HOLE", {
            0: u"5 Og hann sagde",
            1: u"7 Enn hann sagde",
        }, 14, 5, "HEXAPLA_NO_HOLE",
            ([u"numeral «6» is NOT PRINTED before «7»", u"14:5", u"14:7"],
             [u"left inline"]),
            [u"left inline"]),
        # MIDTAG (2026-09-22, luke_kit3 p70/p71/p76): a heading sharing its
        # crop with the previous chapter's last line, in both orders.
        (u"MIDTAG-TAIL", {
            0: u"30 Og hann sagde",
            1: u"safnast z Erner. [chapter heading: Cap. XVIII]",
            2: u"Og hann sagde þeim",
            3: u"3 Og hann",
        }, 17, 30, "HEXAPLA_NO_MIDTAG",
            ([u"CHAPTERS=18", u"17:30", u"18:1", u"18:3"], [u"left inline"]),
            [u"left inline"]),
        (u"MIDTAG-HEAD", {
            0: u"30 Og hann sagde",
            1: u"[chapter heading: XVIII] Og hann sagde þeim",
            2: u"3 Og hann",
        }, 17, 30, "HEXAPLA_NO_MIDTAG",
            ([u"CHAPTERS=18", u"18:1", u"18:3"], [u"left inline"]),
            [u"left inline"]),
        # GLUESPLIT (2026-09-22, luke_kit3 p69): a numeral glued on BOTH sides
        # (read B «Lifnade.14Og»), and a glued numeral that needs the HOLE
        # resync (read B «skorta.15»). Before, each sat the walk at one number
        # and every later numeral was left inline.
        (u"GLUESPLIT-BOTH", {
            0: u"12 Og hann",
            1: u"sagde.13Og hann",
            2: u"for.14 Enn",
            3: u"15 Og",
        }, 1, 12, "HEXAPLA_NO_GLUESPLIT",
            ([u"1:13", u"1:14", u"1:15"], [u"left inline"]),
            [u"left inline"]),
        (u"GLUESPLIT-HOLE", {
            0: u"13 Og hann",
            1: u"ad skorta.15 Hann",
            2: u"16 Og",
        }, 15, 13, "HEXAPLA_NO_GLUESPLIT",
            ([u"numeral «14» is NOT PRINTED before «15»", u"15:15", u"15:16"],
             [u"left inline"]),
            [u"left inline"]),
        # ...and the false-positive side: a margin reference «Matth. 5/18.» /
        # «Matth.11/13.» must NOT be split into a verse numeral, while the real
        # numeral after it still cuts.
        (u"GLUESPLIT-REF", {
            0: u"16 Og hann",
            1: u"Matth. 5/18. z Maðr. 17 Eñ",
            2: u"Matth.19/9. falle. 18 Huor",
        }, 16, 16, "HEXAPLA_NO_REFGUARD",
            ([u"16:17", u"16:18"], [u"NOT PRINTED", u"left inline"]),
            [u"NOT PRINTED"]),
    ]
    fails = []
    for name, lines, ch, fv, var, (want, unwanted), bad_want in cases:
        b, blob = _case(name, lines, ch, fv, {}, want, unwanted)
        if b:
            fails.append(u"%s FIXED direction: %s\n--- got ---\n%s"
                         % (name, "; ".join(b), blob))
        else:
            print(u"PASS  %-11s fixed    - %s" % (name, want[0]))
        b, blob = _case(name, lines, ch, fv, {var: "1"}, bad_want)
        if b:
            fails.append(u"%s KNOWN-BAD direction: %s=1 did NOT bring the "
                         u"defect back (%s). The control does not fail, so it "
                         u"is not a control.\n--- got ---\n%s"
                         % (name, var, "; ".join(b), blob))
        else:
            print(u"PASS  %-11s known-bad- %s=1 restores «%s»"
                  % (name, var, bad_want[0]))
    for f in fails:
        print(u"[X] %s" % f)
    if fails:
        print(u"\n%d FAILURE(S)." % len(fails))
        return 1
    print(u"\nall %d fixes hold, and all %d controls fail when disabled"
          % (len(cases), len(cases)))
    return 0


def main():
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="assert the four 2026-09-20 fixes BOTH WAYS and exit")
    ap.add_argument("--book", required=True)
    ap.add_argument("--page", required=True, help="pNN")
    ap.add_argument("--kit", default=None, help="prep kit dir, default <book>_kit2")
    ap.add_argument("--chapter", type=int, required=True, help="chapter open at the page head")
    ap.add_argument("--first-verse", type=int, required=True,
                    help="the first verse NUMERAL expected on the page (a continued verse is first-verse - 1)")
    ap.add_argument("--series", default="A",
                    help="which independent crop read to stitch: A reads "
                         "_CROP_READ_CHUNK*, B reads _CROP_READB_CHUNK* "
                         "(the two reads use OFFSET chunk boundaries)")
    ap.add_argument("--out", required=True)
    g = ap.parse_args()
    kit = g.kit or "%s_kit2" % g.book.lower()

    files, lines, appendix = load_chunks(g.book, g.page, g.series)
    coverage(lines, g.book, g.page, kit)
    table, unparsed = numeral_table(appendix["NUMERALS"])
    verses, findings, chapters = stitch(lines, g.chapter, g.first_verse, table)
    for raw in unparsed:
        # ⛔ Loud on purpose: this row names a verse boundary the stitch could
        # not use. Silence here mis-addresses every verse after it.
        findings.append("NUMERALS row carries a digit but does NOT parse, so it "
                        "could NOT cut a verse - read it yourself: «%s»" % raw)

    body = []
    body.append(u"# %s idx %s - SECOND INDEPENDENT READ, from the line crops (stitched)" % (g.book, g.page.lstrip("p")))
    body.append(u"")
    body.append(u"- Built by `tools/thorlaks_crop_read_stitch.py` from %d chunk file(s):" % len(files))
    for f in files:
        body.append(u"  `%s`" % os.path.basename(f))
    body.append(u"- Crops covered: line%02d-line%02d (%d). Verses cut at the PRINTED numerals;" % (min(lines), max(lines), len(lines)))
    body.append(u"  a numeral out of sequence is left inline and listed under FINDINGS.")
    body.append(u"- ⛔ HELD, not a part file: this read is one instrument of two.")
    body.append(u"")
    body.append(u"## VERSES")
    body.append(u"")
    last_ch = None
    for ch, v, toks, a, b in [x[:5] for x in verses]:
        if ch != last_ch:
            body.append(u"## Cap. %d" % ch)
            body.append(u"")
            last_ch = ch
        text = u" ".join(toks)
        text = re.sub(r"\s+/", "/", text)
        addr = u"line%02d" % a if a == b else u"line%02d-%02d" % (a, b)
        body.append(u"%d %s — %s" % (v, text, addr))
    body.append(u"")
    body.append(u"## FINDINGS")
    body.append(u"")
    for n, ch, t in chapters:
        body.append(u"- line%02d: chapter break -> Cap. %d  (%s)" % (n, ch, t))
    for f in findings:
        body.append(u"- " + f)
    cont = [x for x in verses if len(x) > 5]
    if cont:
        body.append(u"- the page opens mid-verse: v%d continued from the previous page (line%02d)" % (cont[0][1], cont[0][3]))
    if not chapters and not findings and not cont:
        body.append(u"- none")
    for sec in ("NUMERALS", "HN", "NOTES"):
        body.append(u"")
        body.append(u"## %s (from the chunks, verbatim)" % sec)
        body.append(u"")
        body.extend(appendix[sec] or [u"- none returned"])
    out = u"\n".join(body) + u"\n"

    print("verses %d (%s %d:%d .. %d:%d), chapter breaks %d, findings %d"
          % (len(verses), g.book, verses[0][0], verses[0][1], verses[-1][0], verses[-1][1],
             len(chapters), len(findings)))
    for f in findings[:12]:
        print("  ! " + f)
    if os.path.exists(g.out):
        print("[X] %s exists - refusing to overwrite" % g.out)
        sys.exit(1)
    io.open(g.out, "w", encoding="utf-8", newline="\n").write(out)
    print("wrote %s" % g.out)


if __name__ == "__main__":
    main()
