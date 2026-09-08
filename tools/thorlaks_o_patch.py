# -*- coding: utf-8 -*-
"""Patch confirmed ø sites from the retrofit into the Þorláksbiblía part files.

    python tools/thorlaks_o_patch.py --book Matthew            # REPORT only
    python tools/thorlaks_o_patch.py --book Matthew --apply    # write

## ⛔ THE HARD PART IS NOT THE REPLACEMENT, IT IS THE LOCATION

A retrofit record says «p16 line19 L  Kicrøllð». The part files are organised by
VERSE and carry no physical line numbers, so there is no index from (page, line,
half) to a position in the text. The only handle is the WORD itself, plus the
`prev:` word the adjudicator recorded.

So every site falls into one of:

  UNIQUE     — the plain-o form of the word occurs exactly once in the page's
               part file. Safe to patch.
  AMBIGUOUS  — it occurs more than once. `prev:` is tried as a discriminator; if
               that still does not single one out, the site is REPORTED AND
               SKIPPED. ⛔ Never patch the first occurrence and hope.
  MISSING    — it occurs nowhere. That means the recorded word and the
               transcription disagree, which is a finding about one of them, not
               a patch to force through.

⚠ A MISSING site is not noise. `thorlaks_part_check.py` reads the whole file, so
a word the retrofit saw but the transcription never wrote is either a
transcription gap or a misread by the adjudicator. Both are worth a human.

## ⚠ SCOPE, AND WHY A PARTIAL PATCH IS DANGEROUS

Only pages re-adjudicated by the CROP method have trustworthy ø data
(`thorlaks_o_merge.py` prints which). Patching those pages alone raises the
per-file ø rate that `thorlaks_part_check.py` reports, and the next reader
cannot tell a genuinely-low page from a not-yet-re-adjudicated one — the number
stops meaning anything. This tool therefore ALWAYS prints the page coverage
alongside the patch plan, and `--apply` additionally requires `--i-know-the-
retrofit-is-partial` so that the partiality is an explicit choice.

Long-s is normalised (ſ -> s) before matching, because the part files already are.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")
WORK = DATA / "_work"
PARTS = DATA / "research" / "_parts"

REC = re.compile(r'^p(\d+)\s+line(\d+)\s+([LR])\s+(.*)$')
SHEET_HDR = re.compile(r'^#\s*p(\d+)\s+sheet(\d+)')

# page ranges -> part file stem, for Matthew
MATTHEW_PARTS = [(4, 12, "matthew_p4-12"), (13, 21, "matthew_p13-21"),
                 (22, 31, "matthew_p22-31")]


def part_for(book, page):
    if book.lower() != "matthew":
        return None
    for lo, hi, stem in MATTHEW_PARTS:
        if lo <= page <= hi:
            return PARTS / f"{stem}.md"
    return None


def clean_word(raw):
    """Pull the WORD out of a record's free-text tail.

    ⚠ A parenthetical that is itself a single word is the adjudicator's OWN
    CORRECTION and wins over what precedes it. The p17/p18 reader recorded
    «fogdu (sogdu)», «fomu (somu)», «vegfomudu (vegsomudu)» — it read long-s as
    `f` and put the right reading in brackets. Taking the text before the
    bracket produced 17 MISSING sites on the first run, i.e. the tool blamed the
    transcription for the adjudicator's own noted slip.
    ⛔ A MULTI-word parenthetical is a comment («FIRST o only»), not a
    correction, and must not be treated as the word.
    """
    w = re.split(r'\s*\|\s*prev:', raw)[0]
    w = re.split(r'\s+--\s+', w)[0].strip()
    m = re.match(r'^(\S+)\s*\(([^)]+)\)\s*$', w)
    if m and " " not in m.group(2).strip():
        w = m.group(2).strip()
    else:
        w = w.split("(")[0]
    w = w.strip().strip(",;.")
    return w.replace("ſ", "s")


def prev_word(raw):
    m = re.search(r'\|\s*prev:\s*(.*)', raw)
    if not m:
        return ""
    p = re.split(r'\s+--\s+', m.group(1))[0]
    return p.strip().replace("ſ", "s").split("(")[0].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default="Matthew")
    ap.add_argument("--glob", default="o_retrofit_*READJUDICATED*.txt")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--i-know-the-retrofit-is-partial", action="store_true")
    a = ap.parse_args()

    files = sorted(WORK.glob(a.glob))
    if not files:
        print(f"⛔ no crop-method files matched {a.glob} — nothing to patch")
        return 1

    sites, coverage = [], defaultdict(set)
    non_sites = []
    for f in files:
        # ⚠ SCOPE THE SECTION GUARD TO FILES THAT ACTUALLY USE SECTIONS.
        # The pre-2026-09 record files carry no «## CONFIRMED ø» heading at
        # all; treating their records as non-sites discarded every one of
        # them (SHEET-ONLY went 47 -> 0 on the first run of this guard).
        # A file with no such heading is old-format: read it as before.
        sectioned = "## CONFIRMED ø" in f.read_text(encoding="utf-8")
        section = ""
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if line.startswith("##"):
                section = line
            h = SHEET_HDR.match(line)
            if h:
                coverage[int(h.group(1))].add(int(h.group(2)))
                continue
            if not line or line.startswith("#"):
                continue
            m = REC.match(line)
            if not m:
                continue
            tail = m.group(4)
            # ⛔⛔ ONLY A LINE UNDER A «## CONFIRMED ø» HEADING IS A SITE.
            # Record files legitimately carry site-shaped lines under PLAIN,
            # APPARATUS and NOT-A-SITE headings. The tail-level UNCERTAIN test
            # below catches only the ones that happen to repeat that word:
            # `p36 line04 L  Mark 5:20  giort  | prev: hm  -- PLAIN` says PLAIN,
            # has exactly one o, and would have been STROKED to «giørt» —
            # corrupting a word an adjudicator deliberately recorded as the
            # plain half of a minimal pair. Found 2026-09-08, before any run of
            # this tool had a part file to write to.
            if sectioned and "CONFIRMED ø" not in section:
                non_sites.append((f.name, section.lstrip('# ').strip()[:40], line[:70]))
                continue
            if "UNCERTAIN" in tail.upper():
                continue
            w = clean_word(tail)
            flag = None
            if not w or " " in w:
                flag = "UNPARSEABLE-RECORD"
            elif "ø" not in w and "ö" not in w:
                # ⚠ Adjudicators are INCONSISTENT: some write the corrected form
                # («Fødur»), some write the word as the page prints it («Fodur»)
                # and let the CONFIRMED-ø verdict carry the meaning. Rejecting the
                # second kind cost 22 of 34 sites on the first run of this tool —
                # under-reporting, the same failure this project keeps finding in
                # its own screens.
                # ▶ When the word contains exactly ONE o, the target is not
                #   ambiguous at all: that o is the one. Only a word with two or
                #   more o's genuinely needs the adjudicator to say which.
                n_o = w.lower().count("o")
                if n_o == 1:
                    i = w.lower().index("o")
                    w = w[:i] + ("Ø" if w[i].isupper() else "ø") + w[i + 1:]
                elif n_o == 0:
                    flag = "NO-O-IN-RECORD"
                else:
                    flag = f"{n_o}-O-AMBIGUOUS-IN-RECORD"
            if flag:
                sites.append((int(m.group(1)), int(m.group(2)), m.group(3), w,
                              prev_word(tail), f.name, flag))
                continue
            sites.append((int(m.group(1)), int(m.group(2)), m.group(3), w,
                          prev_word(tail), f.name, None))

    print(f"ø patch plan — {a.book}")
    print(f"crop-method files: {len(files)};  candidate sites: {len(sites)}\n")
    print("PAGE COVERAGE (crop method): " +
          ", ".join(f"p{p}({len(coverage[p])})" for p in sorted(coverage)))
    print("⚠ Pages absent above have NO trustworthy ø data in either direction.\n")

    if non_sites:
        print(f"#  {len(non_sites)} record-shaped line(s) skipped: not under a CONFIRMED-o heading")
        for _n, sec, txt in non_sites:
            print(f"     [{sec}] {txt}")

    cache, plan = {}, defaultdict(list)
    unique = ambiguous = missing = skipped = 0

    for page, ln, half, word, prev, src, flag in sites:
        pf = part_for(a.book, page)
        if pf is None or not pf.exists():
            print(f"  ⛔ p{page}: no part file — skipped")
            skipped += 1
            continue
        if pf not in cache:
            cache[pf] = pf.read_text(encoding="utf-8")
        text = cache[pf]

        if flag:
            print(f"  ⚠ p{page} line{ln:02d} {half}: «{word}» — {flag} — SKIPPED  [{src}]")
            skipped += 1
            continue

        plain = word.replace("ø", "o").replace("ö", "o")
        hits = [mm.start() for mm in
                re.finditer(r'(?<!\w)' + re.escape(plain) + r'(?!\w)', text)]
        if not hits:
            print(f"  ⛔ MISSING  p{page} line{ln:02d} {half}: «{plain}» "
                  f"(for «{word}») is not in {pf.name}")
            missing += 1
            continue
        if len(hits) > 1 and prev:
            narrowed = [h for h in hits
                        if prev.split()[-1].lower() in text[max(0, h - 60):h].lower()]
            if len(narrowed) == 1:
                hits = narrowed
        if len(hits) > 1:
            print(f"  ⚠ AMBIGUOUS p{page} line{ln:02d} {half}: «{plain}» occurs "
                  f"{len(hits)}× in {pf.name}; prev «{prev}» did not single one out "
                  f"— SKIPPED")
            ambiguous += 1
            continue
        unique += 1
        plan[pf].append((hits[0], plain, word))

    print(f"\nSUMMARY  unique {unique} · ambiguous {ambiguous} · "
          f"missing {missing} · skipped {skipped}")

    if not a.apply:
        print("\nREPORT ONLY — nothing written. Pass --apply "
              "--i-know-the-retrofit-is-partial to write.")
        return 0
    if not a.i_know_the_retrofit_is_partial:
        print("\n⛔ REFUSING to write: the retrofit covers only some pages, and a "
              "partial patch makes the per-file ø rate unreadable. Pass "
              "--i-know-the-retrofit-is-partial if that is intended.")
        return 1

    for pf, items in plan.items():
        text = cache[pf]
        for pos, plain, word in sorted(items, key=lambda x: -x[0]):
            text = text[:pos] + word + text[pos + len(plain):]
        pf.write_text(text, encoding="utf-8")
        print(f"  wrote {pf.name}: {len(items)} site(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
