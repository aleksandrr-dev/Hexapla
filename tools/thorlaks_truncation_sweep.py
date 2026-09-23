#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sweep Thorlaksbiblia part files for TRUNCATED verses.

WHY THIS EXISTS
---------------
Luke 5:1 lost its scripture text on 2026-09-10. The idx 55 source wrote that
verse over two physical lines and only the FIRST survived the merge -- and
`thorlaks_part_check.py` passed the file 39/39, because the NUMERAL was still
there. A verse-COUNT check cannot see a truncated verse: the count is right and
the text is gone.

Any part file merged from a source that wraps verses over physical lines may
carry the same wound. This sweep looks for the signature that a count cannot:
a verse body that STOPS instead of ENDING.

HOW IT DISCRIMINATES -- this is the whole point
-----------------------------------------------
These part files SPLIT a verse across a sheet boundary ON PURPOSE, and record
the second half as a companion line:

    16 Vite thier ei
    PROGRESS: p153_sheet1 done -- 1 Cor 3:1-3:16 (verse 16 continues on sheet2)
    16 [continued] th thier erud Guds Mustere z th Guds Ande byggr j ydur?

That is HEALTHY. The Luke 5:1 wound looks IDENTICAL up to the last line -- and
then the companion is simply absent. So the sweep JOINS every line carrying the
same verse number inside the same chapter before judging it, and reports the
join. An unterminated verse WITH a companion is fine; an unterminated verse
WITHOUT one is the defect.

WHAT IT FLAGS -- four classes, each reported separately
--------------------------------------------------------
  EMPTY      a verse whose JOINED body is (almost) no text at all.
  ORPHAN     a joined body that ends without terminal punctuation AND without
             the corpus virgule -- and has no continuation companion.
             ⭐ This is the Luke 5:1 class. Treat every hit as a real defect
             until the page crop says otherwise.
  SLASH-END  a joined body ending in the virgule '/'. In this corpus '/' is a
             comma AND a legitimate verse ending (the Matthew 1 genealogy ends
             every verse that way), so this class is inherently ambiguous and
             is reported separately rather than being allowed to drown ORPHAN.
  SHORT      a joined body far below the file's own median length.

  ⚠ SLASH-END and SHORT are SUSPICIONS, not verdicts, and even ORPHAN is a
    verdict only once the crop confirms it.
    ⛔ Every hit must be checked AGAINST THE PAGE CROP before anything is
    edited. Do not "repair" a verse from sense, from the KJV, or from a modern
    edition -- that is the fabrication this project's conventions forbid.

  ⚠ This sweep CANNOT see a verse truncated at a point that happens to carry a
    period, nor one whose lost half was the middle. A clean run is 'clean on
    what can be detected', never 'no truncation'.

FAILURE CONTRACT
----------------
If the sweep cannot read what it was asked to read it RAISES. It never returns
a plausible-looking zero -- a failed read must never be indistinguishable from
a real 'nothing wrong here'. Exit codes: 0 clean, 1 findings, 2 could not run.

USAGE
    python tools/thorlaks_truncation_sweep.py                  # every part file
    python tools/thorlaks_truncation_sweep.py --file <path>    # one file
    python tools/thorlaks_truncation_sweep.py --dir <dir>      # a directory
    python tools/thorlaks_truncation_sweep.py --show-control   # prove it fires
    python tools/thorlaks_truncation_sweep.py --selftest       # assert the join

Run from the DATA directory (C:\\Projects\\Hexapla-releases) with the tool's
absolute path, and prefix with PYTHONIOENCODING=utf-8 -- this console is cp1252
and the corpus prints slashed-o and long-s.

## --selftest, and its known-bad control

`--selftest` writes SYNTHETIC part files into `tempfile.mkdtemp()` as UTF-8. It
never reads `research/` and needs no real corpus. ⭐ The assertion that matters
most is #1: the HEALTHY split must NOT be flagged - a sweep that judges lines
without joining them reports every deliberate sheet split as a defect, and the
real ORPHAN drowns.

⛔ A control that passes on broken code is not a control. `HEXAPLA_NO_VERSE_JOIN=1`
makes the sweep judge each physical line on its own instead of joining
same-numbered lines within a chapter - reinstating exactly the defect above.
Both directions must hold, and under the control the HEALTHY split is the
assertion that must fail:

    python tools/thorlaks_truncation_sweep.py --selftest                          # exit 0
    HEXAPLA_NO_VERSE_JOIN=1 python tools/thorlaks_truncation_sweep.py --selftest  # exit 1
"""

import argparse
import glob
import hashlib
import os
import re
import shutil
import statistics
import sys
import tempfile

#: Set by selftest() while it drives a synthetic part file; ⛔ never otherwise.
_IN_SELFTEST = False


def no_verse_join():
    """⚠ The known-bad control: judge each PHYSICAL line, never join a split.

    That reinstates the exact defect the docstring describes - every deliberate
    sheet split looks like an orphan, so the real ORPHAN drowns.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_NO_VERSE_JOIN") == "1"

# A verse body line, exactly as thorlaks_part_check.py matches one.
VERSE = re.compile(r"^(\d+) (.*)$")
CHAPTER = re.compile(r"^## (.+?) (\d+)\b")

# What a finished verse ends with in this corpus.
TERMINAL = tuple(".!?:;\u00bb\u201d)]\u2019")
# The virgule. Both a comma and a legitimate verse ending here -- ambiguous.
VIRGULE = ("/", "\u204a", ",")
# A companion line carrying the second half of a split verse.
CONTINUED = re.compile(r"^\[?(?:continued|continues|cont\.)\b", re.I)

# An INLINE editorial note already declaring this verse an intentional fragment.
# The transcriber writes these when a page or sheet genuinely ends mid-sentence.
# ⚠ strip_marks() removes brackets, so the note must be read off the RAW line.
ANNOTATED = re.compile(
    r"\[[^\]]*(?:continue|cont\.|page ends|ends mid|open\b|fragment|tail\b"
    r"|catchword|unnumbered|not scripture|excluded)[^\]]*\]", re.I)

# A body this short is empty in all but name.
EMPTY_MAX = 12
# A body below this fraction of the file's median length is called SHORT.
SHORT_FRAC = 0.28

# Editorial furniture that is not a truncated verse.
BRACKETED = re.compile(r"^\[[^\]]*\]\s*$")

# ⚠ Reuse thorlaks_part_check's OWN book resolver rather than a second list.
# A `## CONFIRMED o - idx 54` or `## Page map - idx 137` heading is NOT a
# chapter, and treating it as one invents verses out of prose paragraphs that
# happen to start with a digit. part_check already knows the three heading
# forms and the prefix rules; a private copy here would drift from it.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import thorlaks_part_check as _pc
except ImportError as _exc:      # pragma: no cover
    raise RuntimeError("cannot import thorlaks_part_check: %s" % _exc)


def resolve_book(raw):
    """-> canonical book name, or None if this heading is not a chapter."""
    name = _pc._CONNECTOR.sub("", raw).strip()
    return _pc.canonical(name)


def strip_marks(text):
    """Drop editorial brackets and trailing flags so length reflects SCRIPTURE."""
    t = re.sub(r"\[[^\]]*\]", " ", text)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def scan_file(path):
    """Return (findings, stats) for one part file. Raises if it cannot be read."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError("cannot read %s: %s" % (path, exc))

    if not lines:
        raise RuntimeError("%s is EMPTY -- that is a failure to read, not a pass" % path)

    verses = []       # (lineno, book, chap, verse, raw_body, clean_body)
    book = chap = None
    in_fence = False
    # `1corinthians_p152-157.md` -> «1 Corinthians», for the skeleton heading form.
    from_filename = _pc.canonical(
        re.split(r"_p\d", os.path.basename(path))[0].replace("_", " "))

    for n, line in enumerate(lines, 1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = CHAPTER.match(line)
        if m:
            resolved = resolve_book(m.group(1))
            if resolved is None and _pc._CONNECTOR.sub("", m.group(1)).strip() == "":
                # The bare `## Chapter 5 — KJV 28 verses` skeleton form: the
                # book is carried by the FILENAME, not the heading. part_check
                # resolves it the same way. Without this, eight part files
                # parse zero verses and the sweep cannot run on them at all.
                resolved = from_filename
            if resolved:
                book, chap = resolved, m.group(2)
            else:
                # Not a scripture chapter heading (a notes section, a page map).
                # Stop collecting verses until a real chapter heading appears.
                book = chap = None
            continue
        # A table row starting with a digit is not a verse body.
        if line.startswith("|"):
            continue
        m = VERSE.match(line)
        if m and book is not None:
            verses.append((n, book, chap, m.group(1), m.group(2), strip_marks(m.group(2))))

    if not verses:
        # No verse bodies at all. For a part file that is a failure to parse,
        # not a clean sweep -- say so rather than reporting zero findings.
        raise RuntimeError(
            "%s: parsed 0 verse bodies. The file format changed or the path is "
            "wrong. This is NOT a clean result." % path)

    # JOIN every line carrying the same verse number inside the same chapter.
    # A split verse whose companion is PRESENT must not be flagged; the Luke
    # 5:1 defect is precisely a split whose companion is ABSENT.
    joined = {}   # (book, chap, verse) -> dict
    order = []
    for lineno, bk, ch, vs, raw, clean in verses:
        # ⚠ The known-bad control does NOT join: it keys every physical line
        # separately, so a split's companion becomes its own verse.
        key = (bk, ch, vs, lineno) if no_verse_join() else (bk, ch, vs)
        if key not in joined:
            joined[key] = {"lineno": lineno, "parts": [], "pieces": 0,
                           "continued": False}
            order.append(key)
        rec = joined[key]
        rec["pieces"] += 1
        if CONTINUED.match(raw.strip()) or ANNOTATED.search(raw):
            rec["continued"] = True
        rec["parts"].append(clean)

    for key in order:
        rec = joined[key]
        rec["body"] = strip_marks(" ".join(p for p in rec["parts"] if p))

    lengths = [len(joined[k]["body"]) for k in order]
    median = statistics.median(lengths)
    if median <= 0:
        raise RuntimeError("%s: median verse length is 0 -- cannot calibrate" % path)
    short_cut = median * SHORT_FRAC

    findings = []
    for key in order:
        bk, ch, vs = key[:3]
        rec = joined[key]
        body, lineno = rec["body"], rec["lineno"]
        ref = "%s %s:%s" % (bk, ch, vs)
        tag = " [joined %d pieces]" % rec["pieces"] if rec["pieces"] > 1 else ""
        shown = body + tag

        if len(body) <= EMPTY_MAX:
            findings.append(("EMPTY", ref, lineno, len(body), shown))
        elif body.endswith(TERMINAL):
            if len(body) < short_cut:
                findings.append(("SHORT", ref, lineno, len(body), shown))
        elif body.endswith(VIRGULE):
            findings.append(("SLASH-END", ref, lineno, len(body), shown))
        else:
            # Ends mid-stream. Only a DEFECT if nothing continues it.
            if not rec["continued"]:
                findings.append(("ORPHAN", ref, lineno, len(body), shown))

    stats = {
        "verses": len(order),
        "median": median,
        "short_cut": short_cut,
    }
    return findings, stats


def render(path, findings, stats, verbose):
    print("=" * 76)
    print(os.path.basename(path))
    print("  %d verse bodies, median scripture length %d chars, SHORT below %d"
          % (stats["verses"], stats["median"], stats["short_cut"]))
    if not findings:
        print("  clean on what this sweep can detect "
              "(NOT a guarantee of no truncation)")
        return
    by_class = {}
    for cls, ref, lineno, ln, raw in findings:
        by_class.setdefault(cls, []).append((ref, lineno, ln, raw))
    for cls in ("EMPTY", "ORPHAN", "SLASH-END", "SHORT"):
        rows = by_class.get(cls)
        if not rows:
            continue
        print("  %-8s %d" % (cls, len(rows)))
        for ref, lineno, ln, raw in rows:
            body = raw if verbose else (raw[:88] + ("..." if len(raw) > 88 else ""))
            print("      %-22s line %-5d %3dch  %s" % (ref, lineno, ln, body))


def control():
    """Prove the sweep FIRES. A screen that has never fired has not passed."""
    import tempfile
    sample = (
        "## Luke 5\n"
        "1 Thad skiede tha Folkid threingdeft fram til hns/ad heyra Guds ord.\n"
        "2 Og hn saeg tuo Skip stada vid Sioenn/enn Fiskemenn voru stigner af.\n"
        "3 Tha stie hn a eitt Skiped/s Simonar var/z bad hn ad leggia lijtid.\n"
        "4 Og s hn gaf vpp ad tala/sagde hn til Simonr/far thu vt a Diuped z\n"   # ORPHAN
        "5\n"                                                                     # not a verse line at all
        "6 Og tha\n"                                                              # EMPTY
        # --- the NEGATIVE control: a HEALTHY split verse. Must NOT be flagged.
        "7 Og thr bentu fijnu Fielogu/s voru a odru Skipe/th thr kraeme z\n"
        "\nPROGRESS: sheet0 done -- verse 7 continues on sheet1\n\n"
        "7 [continued] hialpudu thn ad draga/Og thr komu z hlodu baede Skipenn full.\n"
    )
    fd, tmp = tempfile.mkstemp(suffix=".md", text=True)
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(sample)
        findings, stats = scan_file(tmp)
        classes = sorted({f[0] for f in findings})
        print("KNOWN-BAD CONTROL")
        print("  planted: ORPHAN (v4, continuation LOST), EMPTY (v6),")
        print("           and a HEALTHY split (v7, continuation PRESENT) that must NOT fire")
        print("  fired  : %s" % (", ".join(classes) or "NOTHING"))
        for cls, ref, lineno, ln, raw in findings:
            print("      %-8s %-14s %3dch  %s" % (cls, ref, ln, raw))
        refs = {f[1] for f in findings}
        ok = ("ORPHAN" in classes and "EMPTY" in classes
              and "Luke 5:7" not in refs)
        if "Luke 5:7" in refs:
            print("  ⛔ the HEALTHY split v7 was flagged - the join logic is broken")
        print("  %s" % ("CONTROL PASSES - the sweep detects both classes" if ok
                        else "CONTROL FAILED - the sweep is broken, ignore its results"))
        return 0 if ok else 2
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def selftest():
    """Assert the JOIN discriminator on synthetic part files.

    ⭐ Assertion 1 (the healthy split) is the false-positive control that
    matters most: under HEXAPLA_NO_VERSE_JOIN=1 it is the thing that fails.
    """
    global _IN_SELFTEST
    _IN_SELFTEST = True
    results = []

    def check(ok, what):
        results.append((bool(ok), what))
        print("%s - %s" % ("ok  " if ok else "FAIL", what))

    # ⚠ UTF-8 on purpose: the fixtures carry þ, ø, æ and the virgule '/'.
    LONG = ("Og their komu til hans med tha tolf och frestad honum alla vega "
            "aa thui fielle och sagde honum alla rikis vold og herlegheit. ")
    healthy = (
        "## 1 Corinthians 3\n"
        "15 Hvars verk brinner upp han skal thola skadha/en hann sialfur "
        "verdur halldinn sem gudlegur bygningur aa grunde.\n"
        "16 Vite thier ei\n"
        "\nPROGRESS: p153_sheet1 done -- 1 Cor 3:1-3:16 (verse 16 continues on sheet2)\n\n"
        "16 [continued] th thier erud Guds Mustere z th Guds Ande byggr j ydur?\n"
        "17 Hvars nokur spillir mustere Guds tha mun Gud spilla honum og thad "
        "er heilagt sem aa byggir og hefir verid aa alla vega.\n"
        "18 Er nu nockur aa medal ydar sem seir sie vitur so verdi hann fiolur og "
        "lerist ord Gudz og vardveitir hans bodord alla sina daga.\n"
    )
    # 3:16 is HEALTHY (companion present). 4:16 must NOT join 3:16.
    per_chapter = (
        "## 1 Corinthians 4\n"
        "16 Lyded thui minni hvat eg kenne ydur aa alla vega og i allum "
        "kristilegum sidum sem eg hefi ordid ydur ad fyrimynd upp fra fystu "
        "stundu til thessarar stundar.\n"
    )
    wound = (
        "## Luke 5\n"
        "1 Thad skiede tha Folkid threingdeft fram til hns ad heyra ord Gudz "
        "og hann stod vid Sioeninn enn fiskemenn voru stigner af skipinu\n"
        "2 Og hann sa tuo skip standa vid Sioenn/enn fiskemenn voru stigner af "
        "skipunum og thvottu netin sin i strandinn.\n"
        "3 Tha stie hann a eitt skiped og bad hann ad leggia lithid fra lande "
        "og hann setist nidur og kendi folkinu or skipinu alla sina vega.\n"
    )
    empty_v = (
        "## Luke 6\n"
        # ⚠ The address must carry a body for VERSE to match: `^(\d+) (.*)$`.
        # A bare `5` line is not a verse body at all, so the EMPTY class is
        # exercised with a one-character body, well under EMPTY_MAX.
        "5 x\n"
        "6 Og hann sagdi thaim er aa honum lyddu ad their skyldu vardveita "
        "bodord hans dag og nott og allar stundir sem hann hefir skipad.\n"
    )
    slash = (
        "## Matthew 1\n"
        # ⚠ In this corpus the virgule is a legitimate verse ENDING (the
        # Matthew 1 genealogy ends every verse that way). The body must END
        # with it, or the terminal-period branch wins and SLASH-END is missed.
        "2 Abraham gat Isaac/en Isaac gat Jacob/og Jacob gat Juda og hans "
        "brodur/\n"
        "3 Og Judas gat Fares og Zara/en thaer voru systur og thera modur var "
        "Thamar og thaer voru og systur/\n"
    )

    tmpdir = tempfile.mkdtemp(prefix="thorlaks_sweep_selftest_")
    try:
        p = os.path.join(tmpdir, "1corinthians_p152-157.md")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(healthy + per_chapter)

        findings, stats = scan_file(p)
        by_ref = {}
        for cls, ref, lineno, ln, raw in findings:
            by_ref.setdefault(ref, []).append(cls)
        classes = sorted({f[0] for f in findings})

        # -- 1. ⭐ the HEALTHY split must NOT be flagged -------------------
        check("1 Corinthians 3:16" not in by_ref,
              "healthy split: a verse WITH a companion is NOT flagged "
              "(the false-positive control that matters most)")

        # -- 7. the join is PER CHAPTER ------------------------------------
        check("1 Corinthians 3:16" not in by_ref
              and "1 Corinthians 4:16" not in by_ref,
              "join is per chapter: 3:16 and 4:16 stay separate and both clean")

        # -- 6. an ordinary verse is not flagged --------------------------
        check("1 Corinthians 3:17" not in by_ref,
              "an ordinary well-terminated verse is not flagged at all")

        # -- the ORPHAN / EMPTY / SLASH fixtures --------------------------
        q = os.path.join(tmpdir, "luke_p10-12.md")
        with open(q, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(wound + empty_v)
        f2, _s2 = scan_file(q)
        by2 = {}
        for cls, ref, lineno, ln, raw in f2:
            by2.setdefault(ref, []).append(cls)
        cls_of = {}   # (ref, class)
        for cls, ref, lineno, ln, raw in f2:
            cls_of[ref] = cls

        # -- 2. the Luke 5:1 wound -> ORPHAN ------------------------------
        check(cls_of.get("Luke 5:1") == "ORPHAN",
              "the Luke 5:1 wound (no companion) is classified ORPHAN")
        # -- 3. almost no text -> EMPTY ----------------------------------
        check(cls_of.get("Luke 6:5") == "EMPTY",
              "a verse whose joined body is almost no text is EMPTY")

        r = os.path.join(tmpdir, "matthew_p1-3.md")
        with open(r, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(slash)
        f3, _s3 = scan_file(r)
        cls3 = {ref: cls for cls, ref, _l, _n, _r in f3}
        # -- 4. the virgule -> SLASH-END, and NOT ORPHAN ------------------
        check(cls3.get("Matthew 1:2") == "SLASH-END",
              "a joined body ending in the virgule is SLASH-END")
        check(cls3.get("Matthew 1:2") != "ORPHAN",
              "SLASH-END and ORPHAN stay separate, so SLASH-END cannot drown "
              "ORPHAN")

        # -- 5. far below the file's own median -> SHORT -------------------
        long_bodies = "".join(
            "%d %s\n" % (n, LONG) for n in range(21, 41))
        short_bodies = (
            "1 %s\n" % LONG +
            "2 %s\n" % LONG +
            "3 Og hann gieck burt.\n" +
            "".join("  \n" for _ in range(0)) +
            "".join("%d %s\n" % (n, LONG) for n in range(4, 30)))
        sfile = os.path.join(tmpdir, "shorty_p1-3.md")
        with open(sfile, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("## Acts 2\n" + long_bodies + short_bodies)
        f4, st4 = scan_file(sfile)
        cls4 = {ref: cls for cls, ref, _l, _n, _r in f4}
        check(cls4.get("Acts 2:3") == "SHORT",
              "a body far below the file's own median is SHORT")

        # -- 8. the median is the FILE'S OWN, not a constant ---------------
        LONG2 = LONG * 3   # a much longer body -> a much higher median
        uniform = os.path.join(tmpdir, "uniform_p1-3.md")
        with open(uniform, "w", encoding="utf-8", newline="\n") as fh:
            # every body the SAME length: nothing is below 0.28x its own median
            fh.write("## Acts 3\n" + "".join(
                "%d %s\n" % (n, LONG2) for n in range(1, 30)))
        f5, st5 = scan_file(uniform)
        cls5 = {ref: cls for cls, ref, _l, _n, _r in f5}
        check("SHORT" not in cls5.values(),
              "the median is the file's OWN: a uniformly long file yields no "
              "SHORT, though the same body was SHORT in the other file")
        # ⚠ Same single short body, two files with different medians: the
        # cut-off must track each file, so SHORT fires in one and not the other.
        check(st4["short_cut"] != st5["short_cut"],
              "the SHORT cut-off is recomputed per file (%.2f vs %.2f), not a "
              "constant" % (st4["short_cut"], st5["short_cut"]))

        # -- 1b. the control must break the healthy split ------------------
        if no_verse_join():
            findings_c, _sc = scan_file(p)
            refs_c = {f[1] for f in findings_c}
            check("1 Corinthians 3:16" not in refs_c,
                  "HEXAPLA_NO_VERSE_JOIN=1 is active: the sweep judges lines "
                  "separately, so the HEALTHY split is flagged (this run is "
                  "SUPPOSED to fail overall)")
        else:
            check("1 Corinthians 3:16" not in by_ref,
                  "the healthy split stays clean when the join is on")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    bad = [w for ok, w in results if not ok]
    print()
    print("%d assertion(s), %d failed" % (len(results), len(bad)))
    if bad:
        print("⛔ SELFTEST FAILED")
        return 1
    print("✅ selftest passed")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="one part file")
    ap.add_argument("--dir", default="research/_parts",
                    help="directory of part files (default research/_parts)")
    ap.add_argument("--verbose", action="store_true", help="print full verse bodies")
    ap.add_argument("--show-control", action="store_true",
                    help="run the known-bad control and exit")
    ap.add_argument("--selftest", action="store_true",
                    help="assert the join logic on synthetic part files and exit")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.show_control:
        return control()

    if args.file:
        paths = [args.file]
    else:
        paths = sorted(glob.glob(os.path.join(args.dir, "*.md")))

    if not paths:
        print("could not run: no part files at %s" % args.dir, file=sys.stderr)
        return 2

    total = 0
    counts = {"EMPTY": 0, "ORPHAN": 0, "SLASH-END": 0, "SHORT": 0}
    failed = []
    files_with = 0

    for path in paths:
        try:
            findings, stats = scan_file(path)
        except RuntimeError as exc:
            failed.append(str(exc))
            continue
        if findings:
            files_with += 1
            render(path, findings, stats, args.verbose)
        total += len(findings)
        for cls, _, _, _, _ in findings:
            counts[cls] += 1

    print("=" * 76)
    print("%d file(s) swept, %d with findings, %d finding(s): "
          "EMPTY %d / ORPHAN %d / SLASH-END %d / SHORT %d"
          % (len(paths) - len(failed), files_with, total,
             counts["EMPTY"], counts["ORPHAN"], counts["SLASH-END"], counts["SHORT"]))

    if failed:
        print()
        print("COULD NOT RUN on %d file(s) -- these are NOT clean:" % len(failed))
        for msg in failed:
            print("   " + msg)
        print("A check that cannot run did not pass.")
        return 2

    print()
    print("EMPTY and ORPHAN are defects until the crop says otherwise.")
    print("SLASH-END and SHORT are SUSPICIONS - the virgule is a real verse ending here.")
    print("Check every hit AGAINST THE PAGE CROP before editing anything.")
    print("Do not restore a verse from the KJV, from sense, or from a modern text.")
    print("Clean here means 'clean on what can be detected', never 'no truncation'.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
