#!/usr/bin/env python
"""
thorlaks_read_check.py - screen a RETURNED PAGE READ before it is merged.

WHY THIS EXISTS
---------------
`thorlaks_part_check.py` screens a part file AFTER a merge. Nothing screened
the read artifact BEFORE it, and that is where the defects are born. Four
consecutive Luke reads (p54 reads 2 and 3, p55 read 1, p59 read 1) returned an
artifact whose two halves disagreed, and p59 read 1 reported its own long-s
scan CLEAN while its verses carried four long-s.

  A READ'S SELF-REPORT IS NOT EVIDENCE ABOUT THE READ.

So this runs in the MAIN session, over the file on disk, and derives every
number itself.

WHAT IT CHECKS
--------------
  1. U+017F long-s in the verse text        (SETTLED convention: always `s`)
  2. Cyrillic homoglyphs anywhere           (invisible corruption)
  3. o / O written as ø in the verse text   (a read adjudicates NO ø: the
     stroke is decided only on a half-width crop at native 8.3x)
  4. the o-site lines parse as `p<NN> line<NN> <L|R>` AND carry their verse
     (a malformed site line is dropped SILENTLY by the merge - Mark, 22 vs 23)
  5. the o denominator, DERIVED - never the read's own manual estimate
     (p59 read 2 estimated 128; the real count was 55, a 2.3x error)
  6. cross-half consistency: words quoted in NOTES that never appear in the
     VERSES (this is what caught «Salue» vs «Saluc» in p59 read 1)
  7. the f-family sorts: `þ`/`p`/`f`/`ꝑ` assigned to what is one printed sort.
     Reported as a DISTRIBUTION, never corrected - see the warning below.

WHAT IT DOES NOT DO
-------------------
  - It NEVER edits the artifact. It prints findings; a human merges.
  - It is NOT a spell-checker and does not know what the page says.
  - A `ꝑ`/`f` split it reports is a question for a native half-width pass, NOT
    a regex. The convention is: write `ꝑ` only where the bar is SEEN.
  - 0 findings means "passed these checks", never "read correctly".

DESIGN RULE (the one this tool exists to embody)
------------------------------------------------
  A CHECK THAT CANNOT RUN DID NOT PASS.
The first version of this screen bounded the verse section at the next `^## `
line - which is the artifact's own `## Cap. VIII` chapter heading. It scanned
Luke 7 only, silently skipped the whole of Luke 8, and REPORTED A PASS. So
every section boundary here is explicit, and a section that cannot be located
raises instead of returning empty.

USAGE
-----
    PYTHONIOENCODING=utf-8 python tools/thorlaks_read_check.py \\
        --file C:/Projects/Hexapla-releases/_work/luke_p59_read2_lines_NOT_MERGED.md

Exit 0 = no hard violation. Exit 1 = at least one. Exit 2 = could not run.
"""
import argparse
import io
import os
import re
import sys
import unicodedata

LONG_S = chr(0x17F)
P_SORT = "\uA751"  # ꝑ - the f-family sort with a barred descender


def die(msg):
    sys.stderr.write("thorlaks_read_check: %s\n" % msg)
    sys.exit(2)


# The verse section's heading, as the returned reads actually spell it. Kept as
# an EXPLICIT list, never "the first heading": four held Luke reads (idx 61-65)
# could not be screened AT ALL because they head their verse text `## Verse
# text`, `## Transcription` or `## 1. RECORDS`. A refusal is not a pass, so an
# unscreenable read is a hole in the screen, not a clean page.
START_RE = re.compile(r"^##\s*(?:\d+\.\s*)?"
                      r"(VERSES|VERSE TEXT|RECORDS|TRANSCRIPTION)\b.*?$",
                      re.M | re.I)

# Headings that END the verse text. Everything after one of these is apparatus.
END_RE = re.compile(u"^##.*?(?:[\u00f8\u00d8oO]\\s*(?:CANDIDATE|SITES?)|FOOT|"
                    u"NOTES|SELF|FINDINGS?|LOW.CONFIDENCE|AMBIGUOUS|H/N|"
                    u"\\[HN\\]|STRUCTURAL|PAGE HEAD|MARGIN|PROVENANCE|SEAM|"
                    u"THE HOLD|UNRESOLVED|Lines the reader).*?$", re.M | re.I)

# Headings that are INSIDE the verse text and must NOT end it. This is the bug
# the module docstring records: bounding at "the next `## `" scanned Luke 7 only
# and reported a pass over an unscanned Luke 8.
CHAP_RE = re.compile(r"^##\s*(?:Cap\.?|Chapter|Luke|Mark|Matthew|John|Acts|"
                     r"Romans|Hebrews|[IVXLC]+\b).*?$", re.M | re.I)


def verses_of(text, verbose=True, strip_headings=True):
    """The verse text, bounded EXPLICITLY.

    Not "up to the next heading": a read artifact legitimately contains
    `## Cap. N` chapter headings inside its verse section.

    The end bound is one of exactly three things, and each is printed:
      - a known apparatus heading after the start   (the normal case)
      - END OF FILE, when the verse section is last (not a guess: there is
        no further heading of any kind)
      - a die(), when a heading after the start is neither apparatus nor a
        chapter heading - the tool does not guess which side of it is verse.
    """
    start = START_RE.search(text)
    if not start:
        die("no `## VERSES` / `## Verse text` / `## RECORDS` / "
            "`## Transcription` section - REFUSING to report a pass on a file "
            "whose verse text cannot be located")
    rest = text[start.end():]
    blind = os.environ.get("HEXAPLA_NO_READCHK") == "1"
    if blind:
        # KNOWN-BAD control: bound at the next `## ` of any kind. This is the
        # 2026 bug, kept runnable so the fixture can prove the fix still fixes.
        m = re.search(r"^##\s", rest, re.M)
        end_at, label = (m.start() if m else len(rest)), "BLIND next `## `"
    else:
        end_at, label = len(rest), "END OF FILE"
        for h in re.finditer(r"^##\s.*?$", rest, re.M):
            if CHAP_RE.match(h.group(0)):
                continue
            if END_RE.match(h.group(0)):
                end_at, label = h.start(), h.group(0).strip()
                break
            die("heading %r after the verse section is neither apparatus nor a "
                "chapter heading - REFUSING to guess where the verse text ends"
                % h.group(0).strip()[:60])
    if verbose:
        print("VERSES heading  : %s" % start.group(0).strip())
        print("VERSES ends at  : %s" % label)
    body = rest[:end_at]
    # ⚠ `strip_headings=False` keeps the `## Cap. N` chapter headings INSIDE
    # the verse body. A single-chapter screen does not want them; a caller that
    # must know WHICH chapter a verse belongs to (the adjudication merge on a
    # page spanning two chapters - idx 62 is Luke 9:40-62 + 10:1-16) cannot
    # recover it once they are gone.
    if not strip_headings:
        return body
    return "\n".join(l for l in body.splitlines()
                     if not l.strip().startswith("## "))


def section(text, pattern):
    """A named apparatus section, and WHETHER IT WAS FOUND.

    ⚠ Case-INSENSITIVE on purpose. It was not, and the ø-site check then
    reported «0 site lines listed» on reads carrying `## ø candidate sites`
    (p65, 9 sites) and `## ø sites` (p63, 23) - a check that could not run
    returning a clean-looking 0, which is the failure this file exists to stop.
    """
    if os.environ.get("HEXAPLA_NO_READCHK_SEC") == "1":
        flags = re.M | re.S                      # KNOWN-BAD: case-sensitive
    else:
        flags = re.M | re.S | re.I
    m = re.search(r"^##\s*" + pattern + r".*?$(.*?)(?=^##\s|\Z)", text, flags)
    return (m.group(1), m.group(0).splitlines()[0].strip()) if m else ("", None)


# ⚠ A site carries its verse whether or not the book is named: the held Luke
# reads list theirs as TABLE ROWS (`| 10:17 | sogdu | line01 |`), and a
# book-name-only pattern counted 23 real sites as «0 listed».
SITE_RE = re.compile(r"\b\d{1,3}:\d{1,3}\b")
ADDR_RE = re.compile(r"\bp\d{1,3}\s*line\d{1,2}\s*[LR]\b")


def site_lines(osites):
    """(candidates, not in `p<NN> line<NN> <L|R>` form, carrying NO verse).

    ONE entry point, used by main() AND by the selftest - a fixture that
    re-implements the cut agrees with itself while the shipped tool drifts.
    """
    cand = [l for l in osites.splitlines()
            if (l.strip().startswith("|") and SITE_RE.search(l))
            or re.search(r"\bp\d+\s*line\d+", l)]
    return (cand,
            [l for l in cand if not ADDR_RE.search(l)],
            [l for l in cand if not SITE_RE.search(l)])


def _bounds(text):
    """verses_of() or the string `DIED` - for the fixtures only."""
    try:
        return verses_of(text, verbose=False)
    except SystemExit:
        return "DIED"


def selftest():
    """The bounding rule, proved in BOTH directions on fixtures.

    ⛔ These fixtures are not the corpus. They exist because the live corpus
    cannot demonstrate a failure the tool is supposed to prevent.
    """
    ok = True
    LS = LONG_S

    # 1. A chapter heading INSIDE the verse section must not end it.
    f1 = (u"## VERSES\n1 first line\n## Cap. VIII\n2 la%sy line\n"
          u"## NOTES\nnothing here\n" % LS)
    v = _bounds(f1)
    got = (v != "DIED" and v.count(LS) == 1 and "first line" in v)
    print("  [%s] chapter heading does NOT end the verse section" % ("ok" if got else "XX"))
    ok &= got

    # ...and the KNOWN-BAD path must MISS that same long-s. A control that
    # cannot fail proves nothing.
    os.environ["HEXAPLA_NO_READCHK"] = "1"
    vbad = _bounds(f1)
    os.environ.pop("HEXAPLA_NO_READCHK")
    got = (vbad != "DIED" and vbad.count(LS) == 0)
    print("  [%s] KNOWN-BAD blind bound MISSES it (control fires)" % ("ok" if got else "XX"))
    ok &= got

    # 2. Apparatus after the verses ends them: a ø in a SITE LIST is correct
    #    and must never be counted as a ø written into the text.
    f2 = (u"## Verse text\n1 clean line\n"
          u"## ø candidate sites\np61 line04 L høfdu Luke 9:1\n")
    v = _bounds(f2)
    got = (v != "DIED" and v.count(u"ø") == 0 and "clean line" in v)
    print("  [%s] `## Verse text` located, apparatus ø not counted" % ("ok" if got else "XX"))
    ok &= got

    # 3. `## 1. RECORDS` - the spelling four held Luke reads actually use.
    got = (_bounds(u"## 1. RECORDS\n1 a line\n## 6. FINDINGS\nx\n") != "DIED")
    print("  [%s] `## 1. RECORDS` located" % ("ok" if got else "XX"))
    ok &= got

    # 4. No verse heading at all -> REFUSE. A refusal is not a pass.
    got = (_bounds(u"## Provenance\nread by a subagent\n") == "DIED")
    print("  [%s] no verse heading -> REFUSES" % ("ok" if got else "XX"))
    ok &= got

    # 5. An UNKNOWN heading after the verses -> REFUSE, never guess a side.
    got = (_bounds(u"## VERSES\n1 a line\n## Weather report\n2 not scripture\n")
           == "DIED")
    print("  [%s] unknown trailing heading -> REFUSES" % ("ok" if got else "XX"))
    ok &= got

    # 6. The apparatus lookup is case-insensitive - and the case-SENSITIVE
    #    version (the shipped bug) must miss the same section.
    f6 = (u"## Verse text\n1 a line\n"
          u"## ø candidate sites — 9, NOT exhaustive\n"
          u"p65 line04 L høfdu Luke 11:49\n")
    body, head = section(f6, u"(?:\\d+\\.\\s*)?[øØoO]\\s*(?:CANDIDATE|SITES?)")
    got = (head is not None and "line04" in body)
    print("  [%s] `## ø candidate sites` FOUND (site check runs)" % ("ok" if got else "XX"))
    ok &= got
    os.environ["HEXAPLA_NO_READCHK_SEC"] = "1"
    _, head_bad = section(f6, u"(?:\\d+\\.\\s*)?[øØoO]\\s*(?:CANDIDATE|SITES?)")
    os.environ.pop("HEXAPLA_NO_READCHK_SEC")
    got = head_bad is None
    print("  [%s] KNOWN-BAD case-sensitive lookup MISSES it (control fires)"
          % ("ok" if got else "XX"))
    ok &= got

    # 7. A TABLE-shaped site list is counted, and reported as NOT merge-shaped.
    rows = (u"| verse | word | line |\n|---|---|---|\n"
            u"| 10:17 | sogdu | line01 |\n| 10:20 | Nofn | line06 |\n")
    cand, bad_addr, no_verse = site_lines(rows)   # the REAL cut, not a copy
    got = (len(cand) == 2 and len(bad_addr) == 2 and not no_verse)
    print("  [%s] table-shaped sites counted AND flagged not merge-shaped"
          % ("ok" if got else "XX"))
    ok &= got

    # 8. END TO END, through the REAL entry point: a ö in the verse text is a
    #    HARD violation; the same ö in the site list is not.
    import subprocess
    import tempfile
    d = tempfile.mkdtemp()
    f_txt = os.path.join(d, "fixture_p99.md")
    io.open(f_txt, "w", encoding="utf-8", newline="\n").write(
        u"## VERSES\n1 hann og höfud hans\n"
        u"## ø candidate sites\n| 1:1 | höfud | line04 |\n")
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--file", f_txt],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    got = (r.returncode == 1 and u"ö/Ö in VERSES  : 1" in r.stdout
           and "THERE IS NO" in r.stdout)
    print("  [%s] end-to-end: ö in the verse text is HARD (rc 1)" % ("ok" if got else "XX"))
    ok &= got

    io.open(f_txt, "w", encoding="utf-8", newline="\n").write(
        u"## VERSES\n1 hann og hofud hans\n"
        u"## ø candidate sites\n| 1:1 | höfud | line04 |\n")
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "--file", f_txt],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    got = (r.returncode == 0 and u"ö/Ö in VERSES  : 0" in r.stdout)
    print("  [%s] end-to-end: ö in the SITE LIST is not (rc 0)" % ("ok" if got else "XX"))
    ok &= got

    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


def main():
    ap = argparse.ArgumentParser()
    if "--selftest" in sys.argv:
        selftest()
    ap.add_argument("--file", required=True)
    ap.add_argument("--page", help="page token for site lines, e.g. p59; "
                                   "default: derived from the filename")
    a = ap.parse_args()
    if not os.path.isfile(a.file):
        die("no such file: %s" % a.file)
    text = io.open(a.file, encoding="utf-8").read()

    page = a.page
    if not page:
        m = re.search(r"_p(\d+)", os.path.basename(a.file))
        page = "p" + m.group(1) if m else None

    verses = verses_of(text)
    notes, notes_h = section(text, r"(?:\d+\.\s*)?NOTES")
    osites, osites_h = section(text, u"(?:\\d+\\.\\s*)?[\u00f8\u00d8oO]\\s*(?:CANDIDATE|SITES?)")
    print("o-site section  : %s" % (osites_h or "NOT FOUND - the site check did NOT run"))
    print("NOTES section   : %s" % (notes_h or "NOT FOUND - the cross-half check did NOT run"))

    hard, soft = [], []
    vlines = [l for l in verses.splitlines() if re.match(r"\s*\d", l)]
    print("file            : %s" % os.path.basename(a.file))
    print("page token      : %s" % (page or "UNKNOWN"))
    print("VERSES          : %d chars, %d numbered line(s)"
          % (len(verses), len(vlines)))
    if not vlines:
        die("the VERSES section holds no numbered lines - REFUSING to pass")

    # 1. long-s
    n = verses.count(LONG_S)
    print("long-s (U+017F) : %d" % n)
    if n:
        hard.append("U+017F in VERSES (%d) - SETTLED convention is plain `s`" % n)

    # 2. Cyrillic
    cyr = [c for c in text if "CYRILLIC" in unicodedata.name(c, "")]
    print("Cyrillic        : %d" % len(cyr))
    if cyr:
        hard.append("Cyrillic homoglyph(s) (%d) - invisible corruption" % len(cyr))

    # 3. o written as oe
    noe = verses.count(u"\u00f8") + verses.count(u"\u00d8")
    print("\u00f8/\u00d8 in VERSES  : %d" % noe)
    if noe:
        hard.append(u"%d \u00f8 written into VERSES - a read adjudicates NO "
                    u"\u00f8; write plain and list the site" % noe)

    # 3b. ö is NEVER a reading on this print (conventions, row 40): it is
    #     either the NASAL BAR over an o, kept diplomatically as the sort it
    #     is, or an unadjudicated ø candidate written at sheet resolution.
    #     ⛔ Neither is cured by a bulk conversion in either direction.
    numl = verses.count(u"ö") + verses.count(u"Ö")
    print(u"ö/Ö in VERSES  : %d" % numl)
    if numl:
        hard.append(u"%d ö in VERSES - THERE IS NO ö SORT IN THIS "
                    u"PRINT (row 40): each is a nasal bar or an unadjudicated "
                    u"ø candidate, settled one at a time on the native "
                    u"crop" % numl)

    # 3c. the oe ligature is not in the documented inventory either.
    lig = verses.count(u"œ") + verses.count(u"Œ")
    print(u"œ/Œ in VERSES  : %d" % lig)
    if lig:
        soft.append(u"%d œ in VERSES - not a documented sort of this "
                    u"print; the other read of the same page writes æ "
                    u"there. Settle it as a sort, never normalise it silently"
                    % lig)

    # 5. the DERIVED denominator
    o = verses.count("o") + verses.count("O")
    tot = o + noe
    print("o-positions     : %d  (DERIVED - never the read's own estimate)" % tot)

    # 4. site lines
    cand, bad_addr, no_verse = site_lines(osites)
    print("o-site lines    : %d listed, %d unparseable address, %d with NO verse"
          % (len(cand), len(bad_addr), len(no_verse)))
    if tot and cand:
        print("                  %d/%d = %.1f %% of the derived denominator"
              % (len(cand), tot, 100.0 * len(cand) / tot))
    if no_verse:
        hard.append("%d site line(s) carry NO VERSE - unrecoverable later "
                    "(Matthew's retrofit is stranded for exactly this)"
                    % len(no_verse))
    if bad_addr:
        soft.append("%d site line(s) not in `p<NN> line<NN> <L|R>` form - the "
                    "merge drops these SILENTLY" % len(bad_addr))

    # 7. the f-family sorts, ON THE CONTESTED STEMS ONLY.
    # \u26d4 A raw tally of \u00fe / f / p across the whole text is NOISE, not a screen:
    # `\u00fe` is an ordinary letter (95 of them on p59, nearly all correct) and `p`
    # sits inside ordinary words. The first version printed those totals and
    # said nothing. What IS diagnostic is ONE STEM spelled with DIFFERENT
    # sorts in the same read - p59 read 2 wrote \u00ab\u00fegie\u00fe\u00bb, \u00abfyrergiefst\u00bb and
    # \u00ab\u00feyrergiefur\u00bb within four lines, which is one printed sort read three
    # ways.
    FAMILY = u"f\u00fe\uA751p"          # f, thorn, the \uA751 sort, p
    STEMS = ((u"[%s]yrer" % FAMILY, u"?yrer"),
             (u"gie[%s]" % FAMILY, u"gie?"),
             (u"ho[%s]du" % FAMILY, u"ho?du"),
             (u"ga[%s]\\b" % FAMILY, u"ga?"))
    print("f-family sorts  : (contested stems only)")
    split_found = []
    for pat, label in STEMS:
        hits = re.findall(pat, verses)
        if not hits:
            continue
        seen = {}
        for h in hits:
            for ch in h:
                if ch in FAMILY:
                    seen[ch] = seen.get(ch, 0) + 1
        desc = "  ".join("%s=%d" % (k, v) for k, v in sorted(seen.items()))
        print(u"    %-8s %s" % (label, desc))
        if len(seen) > 1:
            split_found.append((label, desc))
    if not split_found:
        print("    no stem is spelled with two different sorts")
    else:
        soft.append(u"ONE stem spelled with DIFFERENT f-family sorts: %s "
                    u"- a QUESTION for a native half-width bar test, NEVER a "
                    u"regex (write \uA751 only where the bar is SEEN)"
                    % "; ".join("%s %s" % (a, b) for a, b in split_found))

    # 6. cross-half consistency
    quoted = set(re.findall(u"\u00ab([^\u00bb]{2,40})\u00bb", notes))
    missing = sorted(q.strip() for q in quoted
                     if q.strip() and " " not in q.strip()
                     and re.search(u"[A-Za-z\u00fe\u00f0\u00e6\u00f8\u00f6]", q)
                     and q.strip() not in verses)
    print("NOTES words not in VERSES: %d" % len(missing))
    for q in missing[:20]:
        print("    ? %s" % q)
    if missing:
        soft.append("%d word(s) quoted in NOTES never appear in VERSES - the "
                    "two halves disagree (this is what caught Salue/Saluc)"
                    % len(missing))

    print("")
    print("HARD violations : %d" % len(hard))
    for h in hard:
        print("   [X] " + h)
    print("SOFT findings   : %d" % len(soft))
    for s in soft:
        print("   [!] " + s)
    print("")
    print("[X] 0 findings means PASSED THESE CHECKS, never «read correctly».")
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
