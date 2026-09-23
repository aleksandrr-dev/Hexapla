"""Screen two crop reads of one page for the BISECTED-NUMERAL class. 0 model tokens.

    PYTHONIOENCODING=utf-8 python tools/thorlaks_numeral_seam_screen.py --book Luke --page p66
    PYTHONIOENCODING=utf-8 python tools/thorlaks_numeral_seam_screen.py --selftest

Runs AFTER both crop reads are on disk and BEFORE `thorlaks_crop_read_stitch.py`
/ `thorlaks_adjudicate_brief.py`. Exit 0 = nothing to re-read; 1 = findings,
each naming the crop AND its successor; 2 = a read is missing or the usage is
wrong (⛔ a screen that could not run did not pass).

THE CLASS (Luke idx 66, 13:7, 2026-09-20): `prep_chunk` cuts lines at
brightness valleys, and a verse numeral printed low and right is the glyph
most likely to be halved by the cut - its top bar on the bottom edge of
`lineNN.png`, its body in the top strip of `lineNN+1.png`. A reader that
discards top-edge bleed BY RULE («ascenders/descenders only») then reports the
numeral confidently absent, and a re-check that repeats that framing raises
its confidence while looking at the wrong half of the glyph. The ONLY symptom
was a numeral in one read's NUMERALS table and not the other's, caught by luck
at the moment the brief generator refused the page. This script is that
symptom made deliberate: it does not decide who is right, it names the two
crops a third reader must open.

WHAT IT REPORTS, all HARD unless marked:
  · a NUMERALS row that carries a digit but does not parse - e.g. the p64
    compound key `line51/52 | 48 | Ad`, a numeral the reader itself says
    straddles two crops. A seam crop over both is the instrument, never a
    guess about which crop owns it.
  · a verse numeral tabled by ONE read at lineNN that the OTHER read has
    neither tabled within one crop of it nor carried inline in lineNN /
    lineNN+1 of its LINES. Re-read lineNN AND lineNN+1 of the kit.
  · SOFT: the same verse tabled by both reads more than one crop apart -
    one of them is mis-addressed, and the merge keys on the address.

Verse numbers restart at a chapter heading, so a page can carry «3» twice;
rows are therefore matched by verse AND by proximity (within one crop), never
by verse alone.

Controls, both ways: `--selftest` builds four fixtures in a temp DATA root
(numeral only in A; both tabled; carried inline only; a compound key) and
exits 1 unless each returns exactly what it should. `HEXAPLA_NO_SEAMSCREEN=1`
makes the one-read-only check inert; the selftest must then FAIL (exit 1).
⚠ LIVE positive controls go STALE - the page gets fixed and the example
stops firing. Luke p64 exited 1 on its compound key when this was written; it
exits 0 since the 2026-09-20 right-edge re-cut of its CHUNK4/CHUNK5 resolved
that key (confirmed 2026-09-21). The `--selftest` fixture
`compound key (the p64 class)` still covers the branch, so the screen remains
controlled - but do not cite a page as a control without re-running it.
"""
import argparse
import io
import os
import re
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_crop_read_stitch as st  # noqa: E402  (load_chunks, numeral_table, DATA)

NEAR = 1   # crops: a numeral tabled within this many crops in the other read is the same sighting


def load(book, page, series):
    """-> (files, lines, table, unparsed) or None when no chunk files match."""
    real_exit = sys.exit
    try:
        sys.exit = lambda *_: (_ for _ in ()).throw(FileNotFoundError())
        files, lines, appendix = st.load_chunks(book, page, series)
    except FileNotFoundError:
        return None
    finally:
        sys.exit = real_exit
    table, unparsed = st.numeral_table(appendix["NUMERALS"])
    # ⚠ The RAW rows matter too. `numeral_table()` routes a row to `unparsed`
    # only when its numeral column CARRIES A DIGIT that will not parse; a row
    # whose numeral column has no digit at all (read A's p67
    # `line48 | (no numeral printed; see NOTES) | Og`) is dropped silently and
    # the screen is handed nothing. That is how p67 passed ✅ while the two
    # reads flatly disagreed about a numeral. Keep them and check them.
    return files, lines, table, unparsed, list(appendix["NUMERALS"])


def _inline(lines, n, verse):
    """True when lineNN or lineNN+1 of the LINES text carries the numeral as a
    standalone token (not part of a larger number, not inside a hedge)."""
    pat = re.compile(r"(?<![\d\[])%d(?![\d\]])" % verse)
    return any(pat.search(lines.get(k, "")) for k in (n, n + 1))


def _rows(table):
    """{lineNN: [(verse, word, hedged)]} -> [(lineNN, verse)]"""
    return sorted((n, v) for n, rs in table.items() for (v, _w, _h) in rs)


def screen(A, B):
    """-> [(severity, text)]. A and B are load() tuples."""
    findings = []
    for tag, X in (("A", A), ("B", B)):
        for raw in X[3]:
            findings.append(("HARD", "read %s: NUMERALS row carries a digit but does not parse "
                                     "- a numeral the reader says straddles two crops? «%s». "
                                     "Cut a SEAM crop spanning both crops and re-read that; "
                                     "never guess which crop owns it." % (tag, raw)))
    if os.environ.get("HEXAPLA_NO_SEAMSCREEN") == "1":
        return findings                      # known-bad control: the old blindness

    # ---- an UNTABLED numeral is invisible to the comparison below ----------
    # Ruled 2026-09-21 (Luke p67 line48). The screen compares TABLES; a reader
    # that hedges a numeral in PROSE puts it where no table can see it, and the
    # page passes ✅ while the reads disagree. ⛔ Do NOT fix this by parsing the
    # prose - that is a regex against one reader's phrasing and will miss the
    # next one. Fire on the HEDGE ITSELF, and make the read brief table every
    # suspected numeral as `?`.
    hedged_lines = set()
    for tag, X in (("A", A), ("B", B)):
        for n, text in sorted(X[1].items()):
            for m in re.finditer(r"\[([^\]]*)\]", text or ""):
                if "numeral" in m.group(1).lower():
                    hedged_lines.add((tag, n))
                    findings.append(("HARD",
                        "read %s HEDGED A NUMERAL IN PROSE at line%02d - «[%s]» - so it was "
                        "never tabled and the table comparison CANNOT SEE IT. Re-read line%02d "
                        "AND line%02d at native. ⚠ The other read may have tabled nothing here "
                        "and the page will still look clean: that is exactly how Luke 14:6 was "
                        "lost. ▶ Brief rule: table every SUSPECTED numeral as `?`, never prose."
                        % (tag, n, m.group(1), n, n + 1)))

    # ---- a NUMERALS row with no digit at all -------------------------------
    for tag, X in (("A", A), ("B", B)):
        for raw in X[4]:
            cols = [c.strip() for c in str(raw).split("|")]
            if len(cols) < 2:
                continue
            mline = re.search(r"line(\d{2})", cols[0])
            if not mline or re.search(r"\d", cols[1]):
                continue                      # has a digit: the existing paths own it
            n = int(mline.group(1))
            if (tag, n) in hedged_lines:
                continue                      # already fired once; one look is enough
            findings.append(("HARD",
                "read %s tabled a NUMERAL ROW WITH NO DIGIT at line%02d - «%s». The row was "
                "dropped before the comparison, so this line was screened against nothing. "
                "Re-read line%02d AND line%02d. (A carried-from-previous row such as "
                "«(none inline; carried from lineNN)» fires here too and costs one look - "
                "that is the right side to err on.)"
                % (tag, n, str(raw).strip(), n, n + 1)))

    ra, rb = _rows(A[2]), _rows(B[2])
    for tag, mine, other, other_lines in (("A", ra, rb, B[1]), ("B", rb, ra, A[1])):
        for n, v in mine:
            if any(v == v2 and abs(n - n2) <= NEAR for n2, v2 in other):
                continue
            if _inline(other_lines, n, v):
                continue
            o = "B" if tag == "A" else "A"
            findings.append(("HARD", "verse %d numeral tabled at line%02d by read %s ONLY - read %s has it "
                                     "neither tabled nor inline at line%02d/line%02d. Re-read line%02d "
                                     "AND line%02d of the kit at native before believing it absent: a "
                                     "numeral halved by the cut lives in the TOP strip of line%02d "
                                     "(bisected-numeral class, Luke idx 66 v13:7)."
                             % (v, n, tag, o, n, n + 1, n, n + 1, n + 1)))
    for n, v in ra:
        far = [n2 for n2, v2 in rb if v2 == v and abs(n - n2) > NEAR]
        near = [n2 for n2, v2 in rb if v2 == v and abs(n - n2) <= NEAR]
        if far and not near:
            findings.append(("SOFT", "verse %d tabled at line%02d by A but at %s by B - one address is "
                                     "wrong, and the merge keys on it."
                             % (v, n, ", ".join("line%02d" % k for k in far))))
    return findings


def report(book, page, findings, A, B):
    print("numeral seam screen - %s %s: read A %d numerals in %d chunk(s), read B %d in %d"
          % (book, page, sum(len(r) for r in A[2].values()), len(A[0]),
             sum(len(r) for r in B[2].values()), len(B[0])))
    hard = [t for s, t in findings if s == "HARD"]
    soft = [t for s, t in findings if s == "SOFT"]
    for t in hard:
        print("  ⛔ HARD  " + t)
    for t in soft:
        print("  ⚠ SOFT  " + t)
    if not findings:
        print("  ✅ every tabled numeral is matched by the other read (tabled within one crop, or inline)")
    else:
        print("  %d HARD, %d SOFT - re-read the named crops before the stitch; a numeral absent from "
              "one read is a question about the CUT, not a vote." % (len(hard), len(soft)))
    return 1 if findings else 0


# ---------------------------------------------------------------- selftest
_CHUNK = """# Test idx 01 - CROP READ chunk 1 (line09-line11)

## LINES
line09 | fyrri lina her
line10 | %s
line11 | sidari lina her

## NUMERALS
%s

## NOTES
- none
"""


def _fixture(root, series, line10, numerals):
    tag = "CROP_READ" if series == "A" else "CROP_READB"
    os.makedirs(os.path.join(root, "_work"), exist_ok=True)
    p = os.path.join(root, "_work", "test_p01_%s_CHUNK1.md" % tag)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(_CHUNK % (line10, numerals))


def selftest():
    cases = [
        # name, A line10, A numerals, B line10, B numerals, expected HARD count
        ("only-in-A (the p66 class)", "7 Þa sagde hann", "line10 | 7 | Þa",
                                      "z Þa sagde hann", "", 1),
        ("both tabled",               "7 Þa sagde hann", "line10 | 7 | Þa",
                                      "7 Þa sagde hann", "line10 | 7 | Þa", 0),
        ("inline only in B",          "7 Þa sagde hann", "line10 | 7 | Þa",
                                      "7 Þa sagde hann", "", 0),
        ("compound key (the p64 class)", "þa. 4", "line10/11 | 48 | Ad",
                                      "þa. 4[?]", "", 1),
    ]
    bad = 0
    saved = st.DATA
    try:
        for name, a10, an, b10, bn, want in cases:
            root = tempfile.mkdtemp(prefix="seamscreen_")
            st.DATA = root
            _fixture(root, "A", a10, an)
            _fixture(root, "B", b10, bn)
            A, B = load("Test", "p01", "A"), load("Test", "p01", "B")
            got = sum(1 for s, _ in screen(A, B) if s == "HARD")
            ok = got == want
            bad += 0 if ok else 1
            print("  %s %-32s HARD %d (want %d)" % ("✅" if ok else "⛔", name, got, want))
    finally:
        st.DATA = saved
    print("selftest: %s" % ("OK" if bad == 0 else "%d case(s) FAILED" % bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book")
    ap.add_argument("--page", help="e.g. p66")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not (a.book and a.page):
        print("⛔ usage: --book <B> --page pNN, or --selftest")
        sys.exit(2)
    A, B = load(a.book, a.page, "A"), load(a.book, a.page, "B")
    if A is None or B is None:
        print("⛔ NOTHING WAS SCREENED - read %s has no chunk files for %s %s"
              % ("A" if A is None else "B", a.book, a.page))
        sys.exit(2)
    sys.exit(report(a.book, a.page, screen(A, B), A, B))


if __name__ == "__main__":
    main()
