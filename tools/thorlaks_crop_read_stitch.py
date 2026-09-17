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
CHAP_HINT = re.compile(r"\[(?:[^\]]*\b(?:chapter|cap\.?|capitule|roman numeral)\b[^\]]*)\]", re.I)
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
    on_disk = sorted(int(re.search(r"line(\d{2})", p).group(1))
                     for p in glob.glob(os.path.join(prep, "line*.png")))
    if not on_disk:
        print("[X] no crops on disk under %s" % prep)
        sys.exit(1)
    missing = [n for n in on_disk if n not in lines]
    extra = [n for n in lines if n not in on_disk]
    print("crops on disk %d (line%02d-line%02d), returned %d, missing %s, not-on-disk %s"
          % (len(on_disk), on_disk[0], on_disk[-1], len(lines), missing or "-", extra or "-"))
    if missing:
        print("[X] %d crop(s) never read - commission them, do not stitch a hole" % len(missing))
        sys.exit(1)
    return on_disk


def is_missing_report(t):
    return bool(re.search(r"\b(does not exist|missing|not found|no such file)\b", t, re.I)) and NONTEXT.match(t)


def numeral_table(appendix_lines):
    """`lineNN | 51 | Nu` rows -> {16: [(51, 'Nu')]}: a reader sometimes drops
    the numeral from the LINES text and still reports it here (p62 line16)."""
    out = {}
    for raw in appendix_lines:
        m = re.match(r"^\s*line(\d{2})\s*\|\s*(\d{1,3})\.?\s*\|\s*(\S+)", raw)
        if m:
            out.setdefault(int(m.group(1)), []).append((int(m.group(2)), m.group(3)))
    return out


def stitch(lines, chapter, verse, numerals=None):
    """Walk crops in order; cut at expected numerals; return verses + findings."""
    numerals = numerals or {}
    verses = []          # [chapter, verse, [tokens], first_line, last_line]
    findings, chapters = [], []
    expect = verse       # the number that opens the NEXT verse
    cur = None
    after_break = False  # the first verse after a chapter heading carries no numeral

    def open_verse(ch, v, n):
        verses.append([ch, v, [], n, n])

    for n in sorted(lines):
        t = lines[n].strip()
        if not t or is_missing_report(t):
            continue
        # ⚠ `and not CHAP_HINT` so a crop bracketed `[chapter heading, not body
        # text]` still falls through to the chapter-break branch below.
        if (RUNHEAD.match(t) and not CHAP_HINT.search(t)
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
            continue
        toks = t.split()
        fallback = [(num, w) for num, w in numerals.get(n, []) if num == expect]
        if fallback and re.search(r"(?<!\d)%d(?!\d)" % expect, t):
            fallback = []        # the numeral IS inline; the walk below cuts on it
        for tok in toks:
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
                findings.append("line%02d numeral «%d» taken from the NUMERALS table (absent from LINES)"
                                % (n, fallback[0][0]))
                fallback = []
            m = re.match(r"^(\d{1,3})\.?$", tok)
            if m:
                num = int(m.group(1))
                if num == expect:
                    open_verse(chapter, num, n)
                    cur = verses[-1]
                    expect += 1
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


def main():
    ap = argparse.ArgumentParser()
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
    verses, findings, chapters = stitch(lines, g.chapter, g.first_verse,
                                        numeral_table(appendix["NUMERALS"]))

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
