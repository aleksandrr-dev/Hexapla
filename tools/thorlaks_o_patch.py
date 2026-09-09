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
import difflib
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

# page ranges -> part file stem, PER BOOK.
# ⚠⚠ A BOOK MISSING FROM THIS TABLE IS NOT "NO SITES" — IT IS A SKIPPED BOOK.
# Until 2026-09-09 part_for() read `if book.lower() != "matthew": return None`,
# so `--book Mark` resolved nothing and reported «no part file — skipped» for
# every one of its 346 candidate sites. The retrofit looked runnable and wrote
# nothing. The only reason that never corrupted anything is that the whole Mark
# read was still in progress. ▶ Adding a book means adding a row HERE.
BOOK_PARTS = {
    "matthew": [(4, 12, "matthew_p4-12"), (13, 21, "matthew_p13-21"),
                (22, 31, "matthew_p22-31")],
    "mark":    [(32, 40, "mark_p32-40"), (41, 49, "mark_p41-49")],
}

# Back-compat: some callers/tests import MATTHEW_PARTS by name.
MATTHEW_PARTS = BOOK_PARTS["matthew"]


def pages_for(book):
    """-> (lo, hi) page range this book's part table covers, or None.

    ⚠⚠ THE RECORD GLOB IS BOOK-BLIND. `--book Mark` matched all 23 record
    files, including Matthew's p12-p18, and every one of their 53 sites landed
    in the SUMMARY as «skipped». A skip the operator is expected to ignore is
    indistinguishable from a skip that matters — and the whole point of the
    summary is to say whether the book is patchable. Filter by the book's OWN
    page range, which the part table already states.
    """
    rows = BOOK_PARTS.get(book.lower())
    if not rows:
        return None
    return min(r[0] for r in rows), max(r[1] for r in rows)


VERSE_REF = re.compile(
    r'^(?:[1-3]\s+)?([A-Za-zÀ-ÿÞþÆæØø]+)\.?\s+(\d+):(\d+)\s')


def verse_ref(raw):
    """-> (chapter, verse) from a record's leading scripture reference, or None.

    ⚠ None means the record is OLD-FORMAT (Matthew's, written before the
    convention made the verse mandatory), NOT that the site is unlocatable.
    Those fall back to the whole-file search, which is the only handle they have.
    """
    head = re.split(r'\s*\|\s*prev:', raw)[0]
    head = re.split(r'\s+--\s+', head)[0].strip()
    m = VERSE_REF.match(head)
    if not m:
        return None
    return int(m.group(2)), int(m.group(3))


VERSE_LINE = re.compile(r'^(\d+)\s', re.M)
CH_HDR = re.compile(r'^##\s+[A-Za-zÀ-ÿÞþ0-9 ]*?(\d+)\s*$', re.M)


def build_verse_index(text):
    """-> {(chapter, verse): (start, end)} spans into `text`.

    ⛔⛔ WHY THIS EXISTS. The part files are VERSE-INDEXED and the records now
    carry the verse, but the locator searched the WHOLE FILE for the plain-o
    form of the word. A part file spans nine pages, so «sogdu», «giora»,
    «honum» and «Sonur» occur many times over and every one of them came back
    AMBIGUOUS — 99 of Mark's sites, plus 86 MISSING that were really «not
    anywhere in nine pages», a claim no one could act on.
    ⚠ It also stopped the search wandering into `## Divergences from the KJV
    grid` and `## Open sites`, which are NOTES, quote the same words, and are
    not scripture. A hit there would have been patched as though it were.

    A `##` heading whose trailing token is a number opens that chapter; any
    other `##` heading CLOSES the scripture region (notes, checksums, grids).
    """
    idx, chapter, pending = {}, None, None
    for line in re.finditer(r'^.*$', text, re.M):
        s, e, body = line.start(), line.end(), line.group(0)
        if body.startswith("##"):
            m = CH_HDR.match(body)
            if pending:
                idx[pending[0]] = (pending[1], s)
                pending = None
            chapter = int(m.group(1)) if m else None
            continue
        if chapter is None:
            continue
        v = VERSE_LINE.match(body)
        if not v:
            continue
        if pending:
            idx[pending[0]] = (pending[1], s)
        pending = ((chapter, int(v.group(1))), s)
    if pending:
        idx[pending[0]] = (pending[1], len(text))
    return idx


# The print's nasal bars, and what a transcriber expands them to. The
# adjudicator writes the page as it PRINTS - «morgū», «Høndū», «Grøfū» - while
# the part files expand some of them and keep others. Neither is wrong; they
# are two conventions meeting, and the locator was reading the difference as
# «the transcription does not contain this word».
FOLD = [("\u016b", "um"), ("\u016b", "un"), ("\u00f1", "nn"), ("\u00f1", "n"),
        ("\u0101", "an"), ("\u0101", "am"), ("\u014d", "on"), ("\u014d", "om"),
        ("\u0113", "en"), ("\u0113", "em")]
O_ANY = "oO\u00f8\u00d8\u00f6\u00d6"


def fold_variants(w):
    """-> every expansion of w's abbreviation marks (bounded to 3 rounds)."""
    out = {w}
    for _ in range(3):
        new = set(out)
        for v in out:
            for a, b in FOLD:
                if a in v:
                    new.add(v.replace(a, b, 1))
        if new == out:
            break
        out = new
    return out


def fold_key(s):
    """-> the set of case- and stroke-insensitive keys for one token."""
    return {v.replace("\u00f8", "o").replace("\u00f6", "o").lower()
            for v in fold_variants(s)}


def locate_by_abbrev(word, verse):
    """-> [(offset in `verse`, token)] for every token matching `word` once the
    print's abbreviations are expanded on BOTH sides. Empty when nothing does.

    \u26d4 A TOKEN CARRYING MORE THAN ONE LETTER-O IS DROPPED. For those this has
    established WHICH WORD but not WHICH LETTER, and stroking the wrong one is
    the corruption this whole file exists to avoid.
    \u26a0 Returning a LIST rather than a single hit is deliberate: Mark 7:2 prints
    «Høndū» twice and the retrofit confirms both, which the caller resolves by
    saturation exactly as it does for an unabbreviated word. Returning None on
    «more than one» silently dropped those pairs.
    """
    want = fold_key(word)
    out = {}
    for m in re.finditer(r"[^\s/]+", verse):
        tok = m.group(0).strip(".,;:/")
        if not tok or sum(tok.count(c) for c in O_ANY) != 1:
            continue
        if want & fold_key(tok):
            out[m.start() + m.group(0).index(tok)] = tok
    return sorted(out.items())


def _prev_token(text, pos):
    """-> the word immediately before `pos`, lowercased, or ""."""
    m = re.search(r"([A-Za-zÀ-ÿÞþÆæØøĀ-ſ]+)[^A-Za-zÀ-ÿÞþÆæØøĀ-ſ]*$",
                  text[max(0, pos - 40):pos])
    return m.group(1).lower() if m else ""


def part_for(book, page):
    """-> Path of the part file holding <book> page <page>, or None.

    ⛔ None means "this tool cannot locate the text", NOT "there is nothing to
    patch". Callers must report a None as a SKIP the operator has to see — never
    fold it into a clean run.
    """
    for lo, hi, stem in BOOK_PARTS.get(book.lower(), ()):
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

    ⚠⚠ A LEADING SCRIPTURE REFERENCE IS NOT PART OF THE WORD. Matthew's records
    were written as `p14 line12 L  Eydemørku | prev: …`, with no verse. The
    convention then made the VERSE MANDATORY on every site («EVERY LISTED SITE
    MUST CARRY ITS VERSE» — the fix for Matthew's stranded retrofit), so Mark's
    records read `p32 line03 R  Mark 1:4   Eydemørku | prev: …`. This function
    kept taking everything before the `|`, so the "word" became
    «Mark 1:4   Eydemørku», which contains a space -> UNPARSEABLE-RECORD ->
    SKIPPED. Every one of Mark's 302 sites was silently skipped that way, and
    the tool still printed a clean `REPORT ONLY` summary.
    ⛔⛔ SO THE RULE THAT SAVED THE RETROFIT BROKE THE PATCHER. Found 2026-09-09,
    after all 18 Mark pages were read. Strip the reference FIRST.
    """
    w = re.split(r'\s*\|\s*prev:', raw)[0]
    w = re.split(r'\s+--\s+', w)[0].strip()
    # Leading «<Book> <ch>:<v>» reference, optionally numbered («1 Cor 2:3»)
    # and optionally abbreviated with a dot («Matth. 26:57»).
    w = re.sub(r'^(?:[1-3]\s+)?[A-Za-zÀ-ÿÞþÆæØø]+\.?\s+\d+:\d+\s+', '', w).strip()
    m = re.match(r'^(\S+)\s*\(([^)]+)\)\s*$', w)
    if m and " " not in m.group(2).strip():
        w = m.group(2).strip()
    else:
        w = w.split("(")[0]
    w = w.strip().strip(",;.")
    # ⚠ A [BRACKETED] TAIL IS THE ADJUDICATOR'S COMPLETION, NOT PART OF THE
    # SPELLING. The convention writes a word that runs off the half-sheet as
    # «søg[du]» — the letters in brackets are supplied. Keeping the brackets
    # made the locator search the part files for the literal «søg[du]», which no
    # transcription can contain, and seven Mark sites were reported MISSING as
    # though the transcription disagreed with the page. Strip brackets only when
    # what they hold is LETTERS: «[?]» is the illegible marker and must not be
    # folded into a word.
    w = re.sub(r"\[([^]\W\d_]+)\]", r"\1", w)
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

    rng = pages_for(a.book)
    if rng is None:
        print(f"⛔ «{a.book}» has no row in BOOK_PARTS — it is a "
              f"SKIPPED BOOK, not a book with no sites. Add its page ranges.")
        return 1
    sites, coverage = [], defaultdict(set)
    non_sites, out_of_book = [], 0
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
            if not (rng[0] <= int(m.group(1)) <= rng[1]):
                out_of_book += 1
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
            elif "ø" not in w.lower() and "ö" not in w.lower():
                # ⚠⚠ CASE. This test read `"ø" not in w` until 2026-09-09, so a
                # word whose ø is its INITIAL — «Ølldungar», «Øfluga», «Øndū» —
                # was treated as having no ø. It then counted lowercase o's,
                # and Ø.lower() is ø, not o, so it also had "no o":
                # NO-O-IN-RECORD, nine of Mark's sites, under a clean summary.
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
            sites.append((int(m.group(1)), int(m.group(2)), m.group(3), w,
                          prev_word(tail), f.name, flag, verse_ref(tail)))

    print(f"ø patch plan — {a.book}  (pages p{rng[0]}-p{rng[1]})")
    print(f"crop-method files: {len(files)};  candidate sites: {len(sites)};  "
          f"records on other books' pages: {out_of_book}\n")
    # ⚠ Scope the coverage to THIS book's pages. Printing Matthew's p12-p18
    # under `--book Mark` claims trustworthy ø data for pages this run never
    # looked at, and the coverage line exists precisely to bound that claim.
    print("PAGE COVERAGE (crop method): " +
          ", ".join(f"p{p}({len(coverage[p])})" for p in sorted(coverage)
                    if rng[0] <= p <= rng[1]))
    print("⚠ Pages absent above have NO trustworthy ø data in either direction.\n")

    if non_sites:
        print(f"#  {len(non_sites)} record-shaped line(s) skipped: not under a CONFIRMED-o heading")
        for _n, sec, txt in non_sites:
            print(f"     [{sec}] {txt}")

    cache, vcache, plan = {}, {}, defaultdict(list)
    unique = ambiguous = missing = skipped = 0
    by_verse = noverse = stray = saturated = already = 0
    by_disc = defaultdict(int)

    # How many sites the retrofit confirms for one word in one verse. The
    # saturation rule below needs this, and it must be counted over ALL sites
    # before any of them is resolved.
    confirmed = defaultdict(int)
    confirmed_fold = defaultdict(int)
    for page, ln, half, word, prev, src, flag, ref in sites:
        if flag:
            continue
        pf = part_for(a.book, page)
        pl = (word.replace("ø", "o").replace("ö", "o")
                  .replace("Ø", "O").replace("Ö", "O"))
        confirmed[(pf, ref, pl)] += 1
        # WARN A SECOND COUNTER, FOLD- AND CASE-INSENSITIVE, for the abbreviation
        # path. Mark 7:2's two records read «Høndū» and «høndū»: different keys
        # above, so each counted 1, and a saturation that needs 2 could never
        # fire. The o-position count is what the plain key is for; this key is
        # for «is this the same WORD».
        confirmed_fold[(pf, ref, min(fold_key(word)))] += 1

    for page, ln, half, word, prev, src, flag, ref in sites:
        pf = part_for(a.book, page)
        if pf is None or not pf.exists():
            print(f"  ⛔ p{page}: no part file — skipped")
            skipped += 1
            continue
        if pf not in cache:
            cache[pf] = pf.read_text(encoding="utf-8")
            vcache[pf] = build_verse_index(cache[pf])
        text = cache[pf]

        if flag:
            print(f"  ⚠ p{page} line{ln:02d} {half}: «{word}» — {flag} — SKIPPED  [{src}]")
            skipped += 1
            continue

        # ⚠ The plain form must fold BOTH cases, for the same reason.
        plain = (word.replace("ø", "o").replace("ö", "o")
                     .replace("Ø", "O").replace("Ö", "O"))
        pat = re.compile(r'(?<!\w)' + re.escape(plain) + r'(?!\w)')
        whole = [mm.start() for mm in pat.finditer(text)]

        # ⛔⛔ SCOPE THE SEARCH TO THE VERSE THE RECORD NAMES.
        # The part files are VERSE-INDEXED and every Mark record carries its
        # verse (the convention fix), but the locator searched all nine pages
        # of the part file for the plain-o form of the word. That is what made
        # 99 sites AMBIGUOUS («sogdu», «giora», «honum» recur constantly) and
        # what made 86 MISSING mean «nowhere in nine pages» — a verdict no
        # one could act on.
        # ⚠ A record with NO verse is OLD-FORMAT (Matthew's, written before
        # the verse was mandatory), NOT unlocatable: it falls back to the
        # whole-file search, which is the only handle it has ever had.
        span = vcache[pf].get(ref) if ref else None
        if ref and span is None:
            print(f"  ⛔ NO-SUCH-VERSE p{page} line{ln:02d} {half}: "
                  f"{a.book} {ref[0]}:{ref[1]} is not a verse in {pf.name} "
                  f"(for «{word}») — SKIPPED")
            skipped += 1
            continue
        if span:
            hits = [h for h in whole if span[0] <= h < span[1]]
            scope = f"{a.book} {ref[0]}:{ref[1]}"
        else:
            hits = whole
            scope = pf.name
            noverse += 1

        if not hits:
            # ⛔⛔ A BARE «MISSING» IS NOT ACTIONABLE. It says the word is not in
            # the verse and leaves the reader to work out why, over 100+ sites.
            # Name the reason instead — all three checks are deterministic and
            # cost nothing:
            verse = text[span[0]:span[1]] if span else ""
            # (a) the transcription may ALREADY read ø here. Then there is
            #     nothing to patch and nothing disagrees — the opposite of what
            #     a MISSING implies.
            if span and re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)', verse):
                print(f"  ✅ ALREADY  p{page} line{ln:02d} {half}: «{word}» is "
                      f"already stroked in {scope} — nothing to patch")
                already += 1
                continue
            # (a2) the print's ABBREVIATION MARKS. 27 of Mark's «missing»
            #      sites are the adjudicator writing «mørgū» where the
            #      transcription writes «morgum». Locating through a declared,
            #      symmetric expansion is not a guess: it has to land on
            #      exactly one token carrying exactly one letter-o.
            found = locate_by_abbrev(word, verse) if span else []
            if found:
                n_conf = confirmed_fold[(pf, ref, min(fold_key(word)))]
                if len(found) > 1 and n_conf != len(found):
                    print(f"  \u26a0 ABBREV-CLASH p{page} line{ln:02d} {half}: "
                          f"\u00ab{word}\u00bb expands onto {len(found)} token(s) in "
                          f"{scope} but the retrofit confirms {n_conf} \u2014 "
                          f"SKIPPED, the counts must agree before any is struck")
                    ambiguous += 1
                    continue
                done = False
                for off, tok in found:
                    i = next(k for k, c in enumerate(tok) if c in O_ANY)
                    if tok[i] in "\u00f8\u00d8\u00f6\u00d6":
                        print(f"  \u2705 ALREADY  p{page} line{ln:02d} {half}: "
                              f"\u00ab{word}\u00bb is already stroked in {scope} as "
                              f"\u00ab{tok}\u00bb \u2014 nothing to patch")
                        already += 1
                        done = True
                        continue
                    struck = tok[:i] + ("\u00d8" if tok[i].isupper() else "\u00f8") + tok[i + 1:]
                    plan[pf].append((span[0] + off, tok, struck))
                    print(f"  \u2705 ABBREV   p{page} line{ln:02d} {half}: \u00ab{word}\u00bb "
                          f"= \u00ab{tok}\u00bb in {scope} \u2014 stroked to \u00ab{struck}\u00bb"
                          + (f"  [saturating {len(found)}]" if len(found) > 1 else ""))
                    if not done:
                        unique += 1
                        by_verse += 1
                        by_disc["verse+abbrev"] += 1
                        done = True
                continue
            why = []
            # (b) a NEIGHBOURING verse — a verse-boundary offset, which this
            #     campaign documents as a thing that goes unmarked in the print.
            if span:
                for d in (-2, -1, 1, 2):
                    sp = vcache[pf].get((ref[0], ref[1] + d))
                    if sp and any(sp[0] <= h < sp[1] for h in whole):
                        why.append(f"but IS in {a.book} {ref[0]}:{ref[1] + d} "
                                   f"(verse offset {d:+d})")
                        break
            # (c) the nearest token in the named verse — usually the
            #     adjudicator and the transcriber spelling one word two ways
            #     (an abbreviation mark, or long-s read as f or p).
            if not why and verse:
                near = difflib.get_close_matches(
                    plain, re.findall(r"[^\s/]+", verse), n=2, cutoff=0.8)
                if near:
                    why.append("nearest in the verse: "
                               + ", ".join(f"«{n}»" for n in near))
            if not why and whole:
                why.append(f"occurs {len(whole)}× elsewhere in {pf.name}")
            if why:
                stray += 1
            print(f"  ⛔ MISSING  p{page} line{ln:02d} {half}: «{plain}» "
                  f"(for «{word}») is not in {scope}"
                  + (f"; {'; '.join(why)}" if why else ""))
            missing += 1
            continue
        how = "verse" if span else "file"
        if len(hits) > 1 and prev and not span:
            # ⛔ NO VERSE, NO NEW DISCRIMINATOR. Everything below was designed
            # for a search already narrowed to one verse; over a whole part file
            # it picks positions the evidence does not single out. Keep the
            # original rule for old-format records — see this file's header.
            narrowed = [h for h in hits
                        if prev.split()[-1].lower() in text[max(0, h - 60):h].lower()]
            if len(narrowed) == 1:
                hits, how = narrowed, "file+prev-window"
        elif len(hits) > 1 and prev:
            # (a) the WHOLE prev phrase, immediately before the hit. The old
            #     code used only its last token inside a 60-char window, so
            #     Mark 12:33's prev «num meira z» collapsed to «z», which
            #     occurs four times in that one verse.
            key = re.sub(r"\s+", " ", prev).strip().lower()
            narrowed = [h for h in hits
                        if key and text[max(0, h - len(key) - 2):h].lower()
                        .rstrip().endswith(key)]
            if len(narrowed) == 1:
                hits, how = narrowed, how + "+prev-phrase"
            else:
                # (b) the token immediately before the hit, allowing the
                #     abbreviation the adjudicator wrote («þ» for «þad»).
                tok = key.split()[-1] if key else ""
                narrowed = [h for h in hits if tok and _prev_token(text, h)
                            and (_prev_token(text, h).startswith(tok)
                                 or tok.startswith(_prev_token(text, h)))]
                if len(narrowed) == 1:
                    hits, how = narrowed, how + "+prev-token"
                else:
                    narrowed = [h for h in hits
                                if tok and tok in text[max(0, h - 60):h].lower()]
                    if len(narrowed) == 1:
                        hits, how = narrowed, how + "+prev-window"
        if len(hits) > 1:
            # (c) SATURATION. If the retrofit confirms as many sites for this
            #     word IN THIS VERSE as the verse has occurrences of it, then
            #     every occurrence is stroked and which-is-which cannot matter.
            #     ⛔ It must never fire when the counts differ: that is exactly
            #     the case where picking wrong strokes the plain half of a
            #     minimal pair, which p47 shows sitting one word away.
            if span and confirmed[(pf, ref, plain)] == len(hits):
                for h in hits:
                    plan[pf].append((h, plain, word))
                unique += 1
                if span:
                    by_verse += 1
                saturated += 1
                print(f"  ✅ SATURATED p{page} line{ln:02d} {half}: «{plain}» "
                      f"occurs {len(hits)}× in {scope} and the retrofit confirms "
                      f"{len(hits)} site(s) — all stroked")
                continue
            print(f"  ⚠ AMBIGUOUS p{page} line{ln:02d} {half}: «{plain}» occurs "
                  f"{len(hits)}× in {scope}; the retrofit confirms "
                  f"{confirmed[(pf, ref, plain)]}; prev «{prev}» did not single "
                  f"one out — SKIPPED")
            ambiguous += 1
            continue
        unique += 1
        if span:
            by_verse += 1
        if how != "verse":
            by_disc[how] += 1
        plan[pf].append((hits[0], plain, word))

    print(f"\nSUMMARY  unique {unique} · ambiguous {ambiguous} · "
          f"missing {missing} · already-stroked {already} · skipped {skipped}")
    print(f"         of the unique: {by_verse} located INSIDE the verse the "
          f"record names, {unique - by_verse} by whole-file search "
          f"({noverse} record(s) carry no verse)")
    if saturated or by_disc:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(by_disc.items()))
        print(f"         needed a discriminator: {detail or 'none'}"
              f"{f'; saturation resolved {saturated}' if saturated else ''}")
    if stray:
        print(f"⚠ {stray} of the MISSING carry a diagnosis above (a verse "
              f"offset, a near spelling, or a hit elsewhere in the file). Those "
              f"are findings for a TEXT pass — ⛔ a ø pass must not make silent "
              f"text edits, so none of them is patched here.")

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
        # ⚠ SATURATION adds every occurrence once per site, so two sites in one
        # verse both contribute both positions. Writing a position twice would
        # corrupt the text; dedupe before writing.
        items = list({(pos, plain, word) for pos, plain, word in items})
        for pos, plain, word in sorted(items, key=lambda x: -x[0]):
            text = text[:pos] + word + text[pos + len(plain):]
        pf.write_text(text, encoding="utf-8")
        print(f"  wrote {pf.name}: {len(items)} site(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
