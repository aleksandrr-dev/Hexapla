#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Locate the crop (lineNN) that holds each disputed span, from the reads on disk.

An adjudication brief has to tell the reader WHICH crop to open. Hunting for
the verse costs image reads, which are the expensive thing here, and a reader
that goes looking will open crops that are not in its budget.

This derives the address instead, for free, out of the `lineNN | text` chunk
files both reads already wrote. Nothing here looks at an image.

Input is a TSV of disputed spans:

    page<TAB>verse<TAB>A_reading<TAB>B_reading

Lines beginning `#` are comments. For each span it searches that page's
`luke_<page>_CROP_READ*_CHUNK*.md` files for the span's distinctive tokens and
prints every `lineNN` that matches, per read.

⚠ A span whose address comes back EMPTY or AMBIGUOUS is a finding, not a
nuisance: it means the two reads do not agree on where the words sit, which is
the same class of defect as a bisected numeral. It is printed as such and the
exit code reflects it. ⛔ Do not paper over it by widening the match.

Exit codes
    0  every span located to exactly one crop (or one contiguous pair) in both reads
    1  at least one span is UNLOCATED or AMBIGUOUS -- read those crops first
    2  bad usage / missing input

Self-test
    --selftest    runs both directions against synthetic fixtures and exits 0
                  only if the known-good locates and the known-bad is caught.
    HEXAPLA_NO_SPANLOC=1 disables the ambiguity check, so the selftest can
                  confirm the check is what fails the known-bad case.
"""

import argparse
import glob
import os
import re
import sys
import unicodedata

WORK = r"C:\Projects\Hexapla-releases\_work"

# Tokens that carry no locating power: notation the conventions settle, or
# bracket forms that appear on every line of every page.
NOISE = {
    "[HN]", "[?]", "[HN][?]", "[illegible]", "[ornamental", "initial]",
    "z", "j", "i", "a", "o", "e",
}

LINE_RE = re.compile(r"^\s*(line\d{2})\s*\|\s*(.*)$")


def norm(s):
    """Fold the differences the conventions already settle, so a span matches
    across the two reads' spellings rather than only within one of them."""
    # Bracketed groups are APPARATUS, not ink: `[HN]erodem` and `Herodem` are the
    # same word on the page, hedged in one read and committed in the other. For
    # ADDRESSING we must see through that, or every hedged site looks unlocatable.
    # ⛔ This fold is for finding the crop ONLY. It deliberately destroys the very
    # distinction the adjudication exists to record, so nothing that decides a
    # LETTER may use it.
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    # long-s / f are the disputed sort itself -- fold them together so that a
    # span differing ONLY on that sort still locates. We are finding the crop,
    # not judging the letter.
    s = s.replace("f", "s")
    s = s.replace("\u00fe", "th").replace("\u00f0", "d")
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def tokens(reading):
    out = []
    for t in reading.split():
        if t in NOISE:
            continue
        t = t.strip("/.,?")
        n = norm(t)
        if len(n) >= 4:          # short tokens match everywhere; useless as an address
            out.append(n)
    return out


ADJ_RE = re.compile(
    r"^\s*(line\d{2}(?:-line\d{2})?)\s*\|\s*(v\d+)\s*\|\s*A=(.*?)\s*\|\s*B=(.*?)\s*\|",
    re.UNICODE)


def read_adj(page, workdir):
    """Return [(addr, verse, a_text, b_text)] from the ADJ_RESULT files.

    ⚠ These lines are the record of WHAT WAS DECIDED, not of what the two reads
    independently said. That is fine for ADDRESSING -- we only want to know which
    crop holds the span -- but it is NOT a substitute for the reads when the
    question is what the ink says. Do not let this file answer a textual question.
    """
    out = []
    pat = os.path.join(workdir, "luke_%s_ADJ*RESULT*.md" % page)
    for path in sorted(glob.glob(pat)):
        if path.endswith(".pre-v34span") or path.endswith(".pre_normalize"):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                m = ADJ_RE.match(raw)
                if m:
                    out.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


def locate_adj(a_read, b_read, adj_rows):
    """Exact-ish match of a span against the adjudication rows.

    The span table's A=/B= strings were lifted FROM these rows, so a normalised
    equality is the right test -- far safer than token search, which cannot tell
    one occurrence of a common word from another.
    """
    want_a, want_b = norm(a_read), norm(b_read)
    hits = []
    for addr, verse, a_text, b_text in adj_rows:
        if norm(a_text) == want_a and norm(b_text) == want_b:
            hits.append((addr, verse))
    if not hits:                       # fall back to matching the A side alone
        for addr, verse, a_text, b_text in adj_rows:
            if want_a and norm(a_text) == want_a:
                hits.append((addr, verse))
    return hits


def read_chunks(page, workdir):
    """Return {read_label: {lineNN: text}} for one page."""
    reads = {}
    pat = os.path.join(workdir, "luke_%s_CROP_READ*_CHUNK*.md" % page)
    for path in sorted(glob.glob(pat)):
        base = os.path.basename(path)
        label = "B" if "READB" in base else "A"
        if base.endswith(".pre_normalize"):
            continue
        d = reads.setdefault(label, {})
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                m = LINE_RE.match(raw)
                if m:
                    d[m.group(1)] = m.group(2)
    return reads


def locate(span_tokens, linemap):
    """Every lineNN whose normalised text contains any distinctive token."""
    hits = []
    for name in sorted(linemap):
        body = norm(linemap[name])
        if any(tok in body for tok in span_tokens):
            hits.append(name)
    return hits


def contiguous(hits):
    if len(hits) <= 1:
        return True
    nums = sorted(int(h[4:]) for h in hits)
    return nums[-1] - nums[0] == len(nums) - 1


def run(tsv, workdir, strict=True):
    rows = []
    with open(tsv, encoding="utf-8") as fh:
        for raw in fh:
            if raw.startswith("#") or not raw.strip():
                continue
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            rows.append(parts[:4])

    if not rows:
        print("no spans in %s" % tsv)
        return 2

    by_page = {}
    for r in rows:
        by_page.setdefault(r[0], []).append(r)

    problems = 0
    print("span locator - %d span(s) over %d page(s)\n" % (len(rows), len(by_page)))

    for page in sorted(by_page):
        reads = read_chunks(page, workdir)
        adj_rows = read_adj(page, workdir)
        print("=== %s ===   (%d chunk read(s), %d adjudicated row(s))"
              % (page, len(reads), len(adj_rows)))
        if not reads and not adj_rows:
            print("  NO READS AND NO ADJUDICATION on disk in %s" % workdir)
            print("  (nothing here can address this page's spans)")
            problems += len(by_page[page])
            print("")
            continue

        for _, verse, a_read, b_read in by_page[page]:
            # Prefer the adjudication row: the span table was built from it, so
            # equality is exact and cannot confuse two occurrences of a word.
            adj_hits = locate_adj(a_read, b_read, adj_rows)
            if len(adj_hits) == 1:
                print("  %-7s ADJ=%s (%s)" % (verse, adj_hits[0][0], adj_hits[0][1]))
                continue
            if len(adj_hits) > 1:
                addrs = sorted({h[0] for h in adj_hits})
                if len(addrs) == 1:
                    print("  %-7s ADJ=%s (%d identical row(s))"
                          % (verse, addrs[0], len(adj_hits)))
                    continue
                print("  %-7s ADJ=AMBIGUOUS %s   <-- LOOK"
                      % (verse, ",".join(addrs)))
                problems += 1
                continue

            toks = tokens(a_read) + tokens(b_read)
            toks = list(dict.fromkeys(toks))
            if not toks:
                print("  %-7s NO DISTINCTIVE TOKEN - span is pure notation" % verse)
                problems += 1
                continue

            cells = []
            for label in ("A", "B"):
                if label not in reads:
                    cells.append("%s=(no read)" % label)
                    continue
                hits = locate(toks, reads[label])
                if not hits:
                    cells.append("%s=UNLOCATED" % label)
                elif not contiguous(hits) and strict:
                    cells.append("%s=AMBIGUOUS %s" % (label, ",".join(hits)))
                else:
                    cells.append("%s=%s" % (label, ",".join(hits)))

            bad = any("UNLOCATED" in c or "AMBIGUOUS" in c for c in cells)
            if bad:
                problems += 1
            print("  %-7s %-28s %s%s" % (
                verse, cells[0], cells[1], "   <-- LOOK" if bad else ""))
        print("")

    if problems:
        print("%d span(s) UNLOCATED or AMBIGUOUS - open those crops before briefing."
              % problems)
        return 1
    print("every span located. Addresses are safe to paste into a brief.")
    return 0


def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="spanloc_")
    # known-good: the span's words sit on one crop in both reads
    for label, fname in (("A", "luke_p99_CROP_READ_CHUNK1.md"),
                         ("B", "luke_p99_CROP_READB_CHUNK1.md")):
        with open(os.path.join(tmp, fname), "w", encoding="utf-8") as fh:
            fh.write("line01 | eitthvad allt annad hier\n")
            fh.write("line02 | kasta j Helvite og meira\n" if label == "A"
                     else "line02 | kafta i Helunte og meira\n")
            fh.write("line03 | enn eitthvad annad\n")
    good = os.path.join(tmp, "good.tsv")
    with open(good, "w", encoding="utf-8") as fh:
        fh.write("p99\t12:5\tkasta j Helvite\tkafta i Helunte\n")

    rc_good = run(good, tmp, strict=True)

    # known-bad: the same words also appear on a far-away crop, so the address
    # is ambiguous and the tool must refuse it.
    with open(os.path.join(tmp, "luke_p98_CROP_READ_CHUNK1.md"), "w",
              encoding="utf-8") as fh:
        fh.write("line02 | kasta j Helvite og meira\n")
        fh.write("line40 | kasta j Helvite aftur\n")
    with open(os.path.join(tmp, "luke_p98_CROP_READB_CHUNK1.md"), "w",
              encoding="utf-8") as fh:
        fh.write("line02 | kafta i Helunte og meira\n")
    bad = os.path.join(tmp, "bad.tsv")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("p98\t12:5\tkasta j Helvite\tkafta i Helunte\n")

    strict = os.environ.get("HEXAPLA_NO_SPANLOC") != "1"
    rc_bad = run(bad, tmp, strict=strict)

    print("--- selftest ---")
    print("known-good  rc=%d (want 0)" % rc_good)
    print("known-bad   rc=%d (want 1; want 0 under HEXAPLA_NO_SPANLOC=1)" % rc_bad)
    if not strict:
        ok = rc_good == 0 and rc_bad == 0
        print("HEXAPLA_NO_SPANLOC=1: the check is disabled, so the known-bad PASSES.")
        print("selftest %s" % ("PASS (check confirmed to be what catches it)" if ok
                               else "FAIL"))
        return 0 if ok else 1
    ok = rc_good == 0 and rc_bad == 1
    print("selftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spans", help="TSV of page/verse/A/B")
    ap.add_argument("--work", default=WORK, help="directory holding the CROP_READ chunks")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.spans:
        ap.error("--spans is required (or --selftest)")
    if not os.path.exists(args.spans):
        print("no such spans file: %s" % args.spans)
        return 2
    return run(args.spans, args.work,
               strict=os.environ.get("HEXAPLA_NO_SPANLOC") != "1")


if __name__ == "__main__":
    sys.exit(main())
