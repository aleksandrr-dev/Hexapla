"""Verse-length witness for LOST TEXT in a merged Þorláksbiblía book. 0 model tokens.

    PYTHONIOENCODING=utf-8 python tools/thorlaks_verse_length_witness.py --book Mark [--verses 4:39-5:41]
    PYTHONIOENCODING=utf-8 python tools/thorlaks_verse_length_witness.py --selftest

WHY: eleven prep rows in already-merged books (ephesians/philippians p180,
mark_kit p36, matthew_kit p4/p10/p30, revelation_v3 p233/p234/p244/p247) were
cut at the pre-cliff-fix geometry, where a `lineNN` held two to four printed
lines. The crop COUNT says their addresses are void; it says nothing about
whether words were lost. A verse-count audit cannot see lost words either - a
verse that lost its second half is still one verse. What CAN see it, for free,
is the verse's length against the KJV: Icelandic and English word counts track
each other closely verse by verse, so a verse whose ratio falls far under the
book's own distribution is a candidate for lost text and is named here.

WHAT IT IS NOT: a proof of completeness. A ratio inside the band says «no
half-verse-sized loss»; a few dropped words are under its floor. A printed
count that disagrees with the KJV is a FINDING and is reported, never
corrected - a verse missing from the merged file is listed as ABSENT, not
scored.

Ratio = merged words / KJV words, on verses where the KJV has >= MIN_KJV
words (short verses are noise). A verse is flagged LOW under FLOOR of the
book's median ratio. `--verses` restricts the listing to a range but the
median is ALWAYS the whole book's, so the page is judged against its book.
⚠ ADDRESSES ARE PRINTED ADDRESSES. Where the print's numbering is pinned and
page-verified as running behind the KJV (see PINNED_ALIGNMENT), a printed verse
is scored against the KJV verse(s) it actually carries. Before that table
existed this tool reported Mark 5:43 and 9:50 ABSENT and 9:5-9:47 short, and
all of it was the blind spot, not the text (ruled 2026-09-20).

Controls, and the selftest fails if EITHER is tripped: `--selftest` scores a
fixture book with one halved verse and must flag exactly it, and a second
fixture at the pinned printed numbering that must come back with NOTHING
flagged; `HEXAPLA_NO_LENGTHWIT=1` disables the floor (fixture 1 must FAIL) and
`HEXAPLA_NO_PINALIGN=1` disables the alignment table (fixture 2 must FAIL,
reproducing the exact false LOW run and ABSENT row that motivated it).
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = r"C:\Projects\Hexapla-releases"
KJV = os.path.join(REPO, "app", "src", "main", "assets", "bibles", "en_kjv.json")
MIN_KJV = 12
FLOOR = 0.55
HEAD_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
VERSE_RE = re.compile(r"^(\d{1,3})\s+(.*)$")
NOTE_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}")


# ⛔⛔ PINNED NUMBERING ALIGNMENT — printed numeral -> KJV address.
#
# WHY THIS EXISTS (2026-09-20). Without it this tool scored printed N against
# KJV N even in chapters whose print is KNOWN to run one behind, and every
# verse in such a chapter came back LOW or ABSENT. It reported Mark 5:43 and
# 9:50 ABSENT and 9:5-9:47 short; a delegated page ruling found ALL of them
# present and complete, the whole run an artifact of this blind spot. A screen
# that cries wolf over a pinned, page-verified fact is worse than no screen.
#
# ⚠ An entry here is a FACT ABOUT THE PRINT, page-verified, never a way to
# silence a finding. The evidence for Mark is
# `research/_evidence/mark_verse_count_divergences_2026-09-07.md` plus the
# 2026-09-20 crop read of `_prep/mark_kit/p36/line05.png` (numeral 27 at
# «Þa hun heyrde af Jesu», NO numeral at KJV 5:28's opening, 28 at KJV 5:29 —
# so this edition sets KJV 5:27+28 under one numeral and runs one behind to
# the end of the chapter). ⛔ Do not add a book on a guess: Galatians 5 and
# Philippians 2 carry unnumbered RUN-ON verses, which is a different shape and
# needs no shift for the verses that ARE numbered. Pin what was read.
#
# Each entry maps a PRINTED verse number to the list of KJV verses it carries.
# A printed verse covering two KJV verses is scored against their COMBINED
# length, which is the only comparison that means anything.
PINNED_ALIGNMENT = {
    # printed IX opens at KJV 9:2, so printed N = KJV N+1 throughout (49 v).
    ("mark", 9): lambda v: [(9, v + 1)],
    # KJV 9:1 is printed as v39 inside chapter VIII.
    ("mark", 8): lambda v: [(9, 1)] if v == 39 else [(8, v)],
    # printed 27 carries KJV 5:27 AND 5:28; from 28 on, printed N = KJV N+1.
    # The print stops at 42 (= KJV 5:43); the VI heading follows.
    ("mark", 5): lambda v: ([(5, 27), (5, 28)] if v == 27
                            else [(5, v + 1)] if v >= 28 else [(5, v)]),
}


def aligner(book):
    """-> f(printed_chapter, printed_verse) -> [(kjv_chapter, kjv_verse), ...]

    Identity for every unpinned chapter, so an unpinned book scores exactly as
    it did before this table existed.
    ⚠ HEXAPLA_NO_PINALIGN=1 disables the table — the known-bad control for it.
    """
    off = os.environ.get("HEXAPLA_NO_PINALIGN") == "1"
    key = book.lower()

    def f(ch, v):
        rule = None if off else PINNED_ALIGNMENT.get((key, ch))
        return rule(v) if rule else [(ch, v)]
    return f


def words(text):
    text = NOTE_RE.sub(" ", text)
    return [w for w in re.split(r"[\s/|]+", text) if re.search(r"[^\W\d_]", w)]


def kjv_book(book):
    with open(KJV, encoding="utf-8") as fh:
        for b in json.load(fh):
            if b["name"].lower() == book.lower():
                return {ci + 1: {vi + 1: v for vi, v in enumerate(c)} for ci, c in enumerate(b["chapters"])}
    return None


def merged_book(path):
    """-> {chapter: {verse: text}} from a merged chunk report."""
    out, ch, v = {}, None, None
    with io.open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = HEAD_RE.match(line)
            if m:
                ch, v = int(m.group(2)), None
                out.setdefault(ch, {})
                continue
            if ch is None or not line.strip() or line.startswith("#") or line.startswith("|"):
                continue
            m = VERSE_RE.match(line)
            if m and (v is None or int(m.group(1)) == v + 1 or int(m.group(1)) not in out[ch]):
                v = int(m.group(1))
                out[ch][v] = m.group(2)
            elif v is not None:
                out[ch][v] += " " + line.strip()
    return out


def parse_range(spec):
    """'4:39-5:41' -> ((4,39),(5,41)); '4' -> ((4,1),(4,999))"""
    if not spec:
        return None
    lo, _, hi = spec.partition("-")
    def cv(s, default_v):
        c, _, v = s.partition(":")
        return (int(c), int(v) if v else default_v)
    a = cv(lo, 1)
    b = cv(hi, 999) if hi else (a[0], 999)
    return a, b


def score(merged, kjv, align=None):
    """-> (rows, absent, median). rows = [(ch, v, is_words, kjv_words, ratio)]

    ch/v in a row is the PRINTED address — what a reader will look up on the
    page. `align` maps it to the KJV verse(s) it carries; the default is the
    identity, so an unpinned book behaves exactly as before.
    ⚠ ABSENT is now «no printed verse claims this KJV verse», computed from
    what the alignment covered. It is still a FINDING, never a correction.
    """
    align = align or (lambda ch, v: [(ch, v)])
    rows, covered = [], set()
    for ch, verses in sorted(merged.items()):
        for v, mt in sorted(verses.items()):
            kw, complete = 0, True
            for kc, kv in align(ch, v):
                text = kjv.get(kc, {}).get(kv)
                if text is None:
                    complete = False
                    continue
                kw += len(words(text))
                covered.add((kc, kv))
            if not complete or kw < MIN_KJV:
                continue
            mw = len(words(mt))
            rows.append((ch, v, mw, kw, mw / float(kw)))
    absent = [(kc, kv)
              for kc in sorted({c for c, _ in covered})
              for kv in sorted(kjv.get(kc, {}))
              if (kc, kv) not in covered]
    ratios = sorted(r[4] for r in rows)
    med = ratios[len(ratios) // 2] if ratios else 0.0
    return rows, absent, med


def flagged(rows, med):
    if os.environ.get("HEXAPLA_NO_LENGTHWIT") == "1":
        return []                                    # known-bad control
    return [r for r in rows if r[4] < med * FLOOR]


def run(book, path, rng):
    kjv = kjv_book(book)
    if kjv is None:
        print("⛔ %s not found in the KJV asset; cannot witness" % book)
        return 2
    merged = merged_book(path)
    if not merged:
        print("⛔ nothing parsed from %s" % path)
        return 2
    rows, absent, med = score(merged, kjv, aligner(book))
    low = flagged(rows, med)
    pinned = sorted(c for b, c in PINNED_ALIGNMENT if b == book.lower())
    if pinned and os.environ.get("HEXAPLA_NO_PINALIGN") != "1":
        print("  ▶ pinned numbering applied to printed chapter(s) %s — addresses "
              "below are PRINTED, scored against the KJV verse(s) they carry."
              % ", ".join(str(c) for c in pinned))
    inr = (lambda ch, v: True) if rng is None else (lambda ch, v: rng[0] <= (ch, v) <= rng[1])
    print("%s: %d scored verses (KJV >= %d words), median ratio %.2f, floor %.2f; "
          "%d LOW in the book, %d chapters merged, %d KJV verses ABSENT from merged chapters"
          % (book, len(rows), MIN_KJV, med, med * FLOOR, len(low), len(merged), len(absent)))
    shown = [r for r in low if inr(r[0], r[1])]
    for ch, v, iw, kw, r in shown:
        print("  ⚠ LOW  %s %d:%-3d  %3d words vs KJV %3d  ratio %.2f" % (book, ch, v, iw, kw, r))
    for ch, v in [a for a in absent if inr(*a)]:
        print("  ⛔ ABSENT %s %d:%d - not in the merged file (a count finding, not corrected here)" % (book, ch, v))
    if rng is not None:
        n = sum(1 for r in rows if inr(r[0], r[1]))
        print("  range %s: %d scored, %d LOW, %d absent" % (
            "%d:%d-%d:%d" % (rng[0] + rng[1]), n, len(shown), sum(1 for a in absent if inr(*a))))
    return 1 if (shown or absent) else 0


def selftest():
    kjv = kjv_book("Mark")
    tmp = tempfile.mkdtemp(prefix="lengthwit_")
    path = os.path.join(tmp, "thorlaks_mark.md")
    # fixture: chapter 4 = the KJV text itself (ratio 1.0), verse 39 halved
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write("# fixture\n\n## Mark 4\n\n")
        for v, text in sorted(kjv[4].items()):
            w = words(text)
            if v == 39:
                w = w[: len(w) // 2]
            fh.write("%d %s\n" % (v, " ".join(w)))
    merged = merged_book(path)
    rows, absent, med = score(merged, kjv, aligner("Mark"))
    low = [(r[0], r[1]) for r in flagged(rows, med)]
    ok1 = low == [(4, 39)] and not absent
    print("  %s fixture Mark 4 with v39 halved -> LOW %s (want [(4, 39)]), absent %s"
          % ("✅" if ok1 else "⛔", low, absent))

    # ★ FIXTURE 2 — the pinned-numbering control, added 2026-09-20.
    # Printed Mark IX carries KJV 9:2-9:50 under numerals 1-49. The fixture is
    # the KJV text itself at the PRINTED numbering, so a correct tool must
    # find NOTHING: a perfect transcription must not be flagged merely for
    # being numbered the way the page numbers it. Before PINNED_ALIGNMENT this
    # fixture produced a long LOW run plus ABSENT — the exact false report
    # that sent a page ruling after Mark 5:43 and 9:50.
    # ⛔ Known-bad both ways: HEXAPLA_NO_PINALIGN=1 must make THIS fail, and
    # HEXAPLA_NO_LENGTHWIT=1 must make fixture 1 fail.
    path2 = os.path.join(tmp, "thorlaks_mark_pinned.md")
    with io.open(path2, "w", encoding="utf-8") as fh:
        fh.write("# fixture — printed numbering\n\n## Mark 9\n\n")
        for v in range(1, 50):
            fh.write("%d %s\n" % (v, kjv[9][v + 1]))
    rows2, absent2, med2 = score(merged_book(path2), kjv, aligner("Mark"))
    low2 = [(r[0], r[1]) for r in flagged(rows2, med2)]
    # KJV 9:1 is printed inside chapter VIII, which this fixture omits, so it
    # is legitimately uncovered here; nothing else may be.
    ok2 = not low2 and absent2 == [(9, 1)] and len(rows2) > 20
    print("  %s fixture printed Mark IX (KJV 9:2-50 under numerals 1-49) -> "
          "%d scored, LOW %s (want []), absent %s (want [(9, 1)], printed in VIII)"
          % ("✅" if ok2 else "⛔", len(rows2), low2, absent2))

    ok = ok1 and ok2
    print("selftest: %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book")
    ap.add_argument("--file", help="merged report; default research/thorlaks_<book>.md")
    ap.add_argument("--verses", help="restrict the LISTING, e.g. 4:39-5:41 (median stays book-wide)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.book:
        print("⛔ usage: --book <B> [--verses c:v-c:v], or --selftest")
        sys.exit(2)
    path = a.file or os.path.join(DATA, "research", "thorlaks_%s.md" % a.book.lower())
    if not os.path.exists(path):
        print("⛔ no merged file at %s" % path)
        sys.exit(2)
    sys.exit(run(a.book, path, parse_range(a.verses)))


if __name__ == "__main__":
    main()
