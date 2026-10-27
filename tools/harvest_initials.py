#!/usr/bin/env python
"""
harvest_initials.py - collect the PRINTED INITIALS already recorded in the
research files into one data file per print. 0 model cost.

WHY (owner 2026-09-29: «start wiring the ones we already have»)
    Readers tagged initials inline for months - `[ornate initial: I] Vpphafe`,
    `[unnumbered - ... decorative initial letter opens the paragraph]` - but
    nothing ever collected them, so the app can only guess that a chapter's
    verse 1 opens with a capital. The print also sets initials MID-chapter
    (John 1:6/15/19/29; Karl XII F2), which no guess can reproduce.

SOURCES
    Þorláksbiblía: the MERGED books `research/thorlaks_<book>.md`. Only verse
        lines (`N text`) under a `## <Book> <ch>` heading, before the
        `# Appendix`, count - apparatus that merely MENTIONS an initial
        (page tables, notes) is never a record. Merged text is post-
        adjudication, so a tag there has already passed two reads.
    Karl XII 1703: `research/karlxii_*.md` sentences with an EXPLICIT address
        (`Decorated initials in ch6 ...: v5 «TÅ», v8 «TÅ»`, `10:1 and 10:67`).
        Prose without one is COUNTED as unparsed, never guessed at.

OUTPUT (--apply only; default is a dry run that prints the plan)
    research/initials_<print>.json
        {"print": ..., "generated": ..., "books": {"John": {"1:6": {"letter":
         "Þ", "tag": "..."}}}}
    `letter` is null when the record says an initial is there but not which
    letter ("decorative initial letter opens the paragraph").

KNOWN-BAD CONTROL
    HEXAPLA_NO_VERSEONLY=1 also harvests apparatus lines that mention an
    initial; the verse-line count must RISE (those are the lines the verse-only
    rule keeps out). --selftest checks both directions on fixtures.

    python tools/harvest_initials.py            # dry run
    python tools/harvest_initials.py --apply
    python tools/harvest_initials.py --selftest
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import sys

DATA = r"C:\Projects\Hexapla-releases"
RES = os.path.join(DATA, "research")

CH_RE = re.compile(r"^##\s+(.+?)\s+(\d{1,3})\s*$")
VERSE_RE = re.compile(r"^(\d{1,3})\s+(.*)$")
# The tags an initial is recorded under, in the order they are tried.
LETTER_TAG = re.compile(r"\[(?:ornate|ornamental|decorated)\s+initial:\s*"
                        r"([^\]\s?]+)\??\s*\]", re.I)
PRESENT_TAG = re.compile(r"\[[^\]]*\b(?:ornate|ornamental|decorated|decorative|"
                         r"woodcut|illustration|large verse-)\s*(?:woodcut\s+)?"
                         r"initial\b[^\]]*\]|⟨decorated initial[^⟩]*⟩", re.I)


def harvest_thorlaks_text(text, verse_only=True):
    """{"ch:v": {"letter", "tag"}} for one merged book's text."""
    out, ch = {}, None
    for raw in text.splitlines():
        if raw.startswith("# Appendix"):
            break
        m = CH_RE.match(raw)
        if m:
            ch = int(m.group(2))
            continue
        vm = VERSE_RE.match(raw)
        if ch is None or not vm:
            if not verse_only and ch is not None and \
                    re.search(r"initial", raw, re.I):
                out["%d:?%d" % (ch, len(out))] = {"letter": None,
                                                  "tag": raw.strip()[:80]}
            continue
        v, body = int(vm.group(1)), vm.group(2)
        lm = LETTER_TAG.search(body)
        pm = PRESENT_TAG.search(body)
        if lm:
            out["%d:%d" % (ch, v)] = {"letter": lm.group(1), "tag": lm.group(0)}
        elif pm:
            out["%d:%d" % (ch, v)] = {"letter": None, "tag": pm.group(0)[:80]}
    return out


def book_name(text, path):
    m = re.search(r"^##\s+(.+?)\s+\d{1,3}\s*$", text, re.M)
    return m.group(1) if m else os.path.basename(path)


KX_CH = re.compile(r"Decorated initials in ch(\d+)[^:]*:(.*?)(?:Verse 1 is the "
                   r"unnumbered F1 initial «([^»]+)»|$)", re.I)
KX_V = re.compile(r"\bv(\d{1,3})\s*«([^»]+)»")


def harvest_karlxii_text(text):
    """(records, unparsed_count) - explicit addresses only."""
    out, unparsed = {}, 0
    for raw in text.splitlines():
        if not re.search(r"initial", raw, re.I):
            continue
        m = KX_CH.search(raw)
        if m:
            ch = int(m.group(1))
            for v, word in KX_V.findall(m.group(2)):
                out["%d:%s" % (ch, v)] = {"letter": word[0], "tag": word}
            if m.group(3):
                out["%d:1" % ch] = {"letter": m.group(3)[0], "tag": m.group(3)}
            continue
        unparsed += 1
    return out, unparsed


# The 1703 print sets the letter AFTER a woodcut initial as a capital too
# («MEn», «OCh», «THeras»), and the shipped Karl XII text keeps it. Measured
# 2026-09-29: 21/21 of the explicitly recorded 1 Macc 4-6 initials open this
# way, and those three fully-listed chapters have NO other verse that does.
# «HErre/HErran...» is the print's spelling of LORD, not an initial.
KX_ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app",
                        "src", "main", "assets", "bibles", "sv_karlxii.json")
DOUBLED_CAP = re.compile(u"^[A-ZÅÄÖ][A-ZÅÄÖ](?:[a-zåäöß]|\\b)")
NOT_INITIAL = re.compile(u"^(?:HErr|JEs)")
ASSET_OUT = os.path.join(os.path.dirname(KX_ASSET), "..", "initials.json")
KX_BOOK = {"1maccabees": 75}


def derive_karlxii_asset(explicit):
    """{book: [[0-based verse, ...] per chapter]} from the shipped text, and
    the explicit records it MISSES (must be none, or nothing is written)."""
    books = json.load(io.open(KX_ASSET, encoding="utf-8"))
    out, found = {}, set()
    for bi, b in enumerate(books):
        chs = b.get("chapters", []) if isinstance(b, dict) else []
        per = []
        for ci, ch in enumerate(chs):
            vs = [vi for vi, t in enumerate(ch) if t and DOUBLED_CAP.match(t)
                  and not NOT_INITIAL.match(t)]
            per.append(vs)
            found.update("%d %d:%d" % (bi, ci + 1, vi + 1) for vi in vs)
        if any(per):
            out[str(bi)] = per
    missed = ["%s %s" % (bk, k) for bk, recs in explicit.items()
              for k in recs if "%d %s" % (KX_BOOK.get(bk, -1), k) not in found]
    return out, missed


def run(verse_only=True):
    th = {}
    for p in sorted(glob.glob(os.path.join(RES, "thorlaks_*.md"))):
        if "precampaign" in p:
            continue
        text = io.open(p, encoding="utf-8").read()
        recs = harvest_thorlaks_text(text, verse_only)
        if recs:
            th[book_name(text, p)] = recs
    kx, kx_unparsed = {}, 0
    for p in sorted(glob.glob(os.path.join(RES, "karlxii_*.md"))):
        recs, un = harvest_karlxii_text(io.open(p, encoding="utf-8").read())
        kx_unparsed += un
        if recs:
            kx[os.path.basename(p)[8:-3]] = recs
    return th, kx, kx_unparsed


def selftest():
    fx = (u"# X\n\n- 1:1 | note about a decorated initial P in the page\n"
          u"## John 1\n1 [ornate initial: I] Vpphafe var Ord\n2 Þetta var\n"
          u"6 [ornate initial: Þ] Ar var eirn Madur\n"
          u"> reader: the decorated initial on this page is worn\n## John 2\n"
          u"1 [unnumbered — decorative initial letter opens the paragraph] Og\n"
          u"# Appendix\n5 [ornate initial: Z] after the appendix\n")
    ok = True
    got = harvest_thorlaks_text(fx)
    want = {"1:1": "I", "1:6": u"Þ", "2:1": None}
    good = {k: r["letter"] for k, r in got.items()} == want
    print("  verse-only harvest gives exactly 1:1, 1:6, 2:1    %s"
          % ("ok" if good else "FAIL %r" % got))
    ok &= good
    ctl = harvest_thorlaks_text(fx, verse_only=False)
    good = len(ctl) > len(got)
    print("  control HEXAPLA_NO_VERSEONLY takes apparatus too  %s"
          % ("ok" if good else "FAIL"))
    ok &= good
    kxt = (u"Decorated initials in ch4 that KEEP their numeral (F2): v26 «MEn», "
           u"v52 «OCh». Verse 1 is the unnumbered F1 initial «OCh».\n"
           u"- Decorated initials: v1 is F1 under a display initial\n")
    k, un = harvest_karlxii_text(kxt)
    good = sorted(k) == ["4:1", "4:26", "4:52"] and un == 1
    print("  Karl XII explicit-address parse, prose counted    %s"
          % ("ok" if good else "FAIL %r %d" % (k, un)))
    ok &= good
    print("selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    verse_only = os.environ.get("HEXAPLA_NO_VERSEONLY") != "1"
    th, kx, kx_un = run(verse_only)
    for name, books in (("thorlaks", th), ("karlxii", kx)):
        n = sum(len(b) for b in books.values())
        nl = sum(1 for b in books.values() for r in b.values() if r["letter"])
        print("%-9s %3d record(s) in %2d book(s), %d with a letter, %d presence-only"
              % (name, n, len(books), nl, n - nl))
        for b in books:
            print("    %-22s %s" % (b, " ".join(sorted(
                books[b], key=lambda s: [int(x) if x.isdigit() else 0
                                         for x in s.replace("?", "").split(":")]))[:150]))
    print("karlxii: %d line(s) mention an initial WITHOUT an explicit address "
          "- not harvested (read them by hand)" % kx_un)
    asset, missed = derive_karlxii_asset(kx)
    print("asset     kxii: %d initial(s) in %d book(s) from the doubled capital; "
          "explicit records missed: %d %s"
          % (sum(len(v) for p in asset.values() for v in p), len(asset),
             len(missed), " ".join(missed[:8])))
    if not verse_only:
        print("⚠ HEXAPLA_NO_VERSEONLY=1: control run, nothing written")
        return
    if missed:
        print("⛔ the derivation misses a recorded initial - nothing written")
        sys.exit(1)
    if not a.apply:
        print("dry run - nothing written (--apply writes research/initials_*.json)")
        return
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    for name, books in (("thorlaks", th), ("karlxii", kx)):
        path = os.path.join(RES, "initials_%s.json" % name)
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"print": name, "generated": stamp,
                       "source": "tools/harvest_initials.py", "books": books},
                      fh, ensure_ascii=False, indent=1)
        print("wrote %s" % path)
    # The app/web asset: translation id -> book index -> per-chapter 0-based
    # verse lists (red_letters.json's shape). Only SHIPPED prints go here.
    with io.open(ASSET_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"kxii": asset}, fh, separators=(",", ":"))
        fh.write("\n")
    print("wrote %s" % os.path.normpath(ASSET_OUT))


if __name__ == "__main__":
    main()
