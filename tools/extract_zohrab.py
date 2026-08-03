# -*- coding: utf-8 -*-
"""Extract the TITUS Zohrab Bible (1805 Venice, Armenian OT) into a raw dump.

EXTRACTION + CENSUS ONLY. Writes nothing into app/src/main/assets; builds no
asset; repairs nothing. Sibling of tools/extract_bakar.py, whose marker
machinery parses this corpus unmodified (verified: 28,087 <!Level> comments,
28,087 parsed markers, delta 0).

    python tools/extract_zohrab.py            # extract + census
    python tools/extract_zohrab.py --lenient  # census anomalies without dying

Inputs : C:/Projects/Hexapla-releases/titus_zohrab/arm{at,a}NNN.htm (1,048
         numbered files, harvested 2026-07-20 under Prof. Gippert's grant)
Outputs: .../titus_zohrab/extracted/zohrab_raw.json    {book: {ch: {v: text}}}
         .../titus_zohrab/extracted/zohrab_census.json  counts + every anomaly

Scope is the OT only, per the owner's 2026-07-20 decision: the Zohrab NT
authentically lacks the Comma Johanneum, and the app's Armenian NT is the
already-shipped Western Armenian 1853 ("arm").

════════════════════════════════════════════════════════════════════════
HOW THIS DIFFERS FROM THE BAKAR EXTRACTOR — read before reusing either
════════════════════════════════════════════════════════════════════════

Zohrab is far cleaner and one thing about it is far more dangerous.

 · CLEANER: all 26,647 verse labels are plain numeric (Bakar had 33 glued,
   746 lectionary rubrics, 44 continuations, 73 colophons), and there is NO
   line-wrap hyphenation at all (Bakar: 51,512 rejoins). None of that
   machinery is reproduced here.

 · ⚠ ONE FILE PER CHAPTER, and the Book marker appears ONLY at a book's
   first file. Book identity therefore CARRIES ACROSS FILES and the files
   must be walked in numeric order. Bakar's "exactly one Book marker per
   part" assertion is meaningless here and is replaced by an explicit
   carry + an ordering assertion.

 · ⚠⚠ BOOK IDENTITY MUST NOT BE DERIVED FROM THE ANCHOR PREFIX.
   `Esr.II_(Esr.)` (Ezra) and `Esr.II_(Neh.)` (Nehemiah) SHARE the prefix
   `Esr.II`. Splitting an anchor on the first underscore silently merges two
   different books into one. This is not hypothetical — the recon pass that
   preceded this file did exactly that and reported 47 books against 48
   markers. Always key off the full Book-marker value.

 · NO PHYSICAL PRINT PROVENANCE. Bakar's levels 5-7 are Page/Column/Line and
   gave 100% per-verse page anchors. Zohrab's levels 5-6 are Section and
   Paragraph — logical divisions with no page information. The Bakar census's
   headline "page_col_line for 37,736/37,736 units" has NO analogue here, and
   a spec that assumes one is wrong.

 · `Or.Jer.` IS NOT A DEUTEROCANONICAL BOOK. It is Lamentations chapter 5,
   the Vulgate/LXX "Oratio Jeremiae": Lam.Jer. carries 132 verses (chs 1-4 at
   22/22/66/22) and Or.Jer. exactly 22. The two units belong in ONE app slot.
   This extractor keeps them SEPARATE and merely records the finding — the
   merge is a converter decision, not an extraction one.

════════════════════════════════════════════════════════════════════════
THE BRACKET POLICY, AND WHY IT IS MACHINE-CHECKED
════════════════════════════════════════════════════════════════════════

TITUS displays classical Armenian abbreviations expanded, with the SUPPLIED
letters in parentheses: «ա(ստուա)ծ» for աստուած (God), «տ(է)ր» for տէր
(Lord) — the Armenian counterpart of Greek/Latin nomina sacra. 69,904 such
tokens over 26,647 verses, ~2.6 per verse.

OWNER DECISION 2026-08-03: STRIP THE BRACKETS, KEEP THE LETTERS.

That is not a loss of edition fidelity, it is the opposite. The parentheses
are TITUS's editorial apparatus, NOT characters of the text — proven from
TITUS's own data, not assumed: every word carries a `ci(lang,HEX)` index link
whose HEX is the word's canonical form, and those index forms contain ZERO
parentheses while the displayed surfaces contain them. TITUS itself treats
the expanded spelling as the word. Keeping the brackets would reproduce a
modern critical apparatus that is absent from the 1805 print.

⚠ Inferred, NOT verified against the physical page: that the 1805 print shows
these words abbreviated and carries no parentheses of its own. Standard
Armenian practice says so and the bracketed vocabulary is exactly the sacred
names and commonest particles, but no page image was consulted. A scan is
inventoried in research/scanhunt_zohrab_bakar.md if this is ever challenged.

So the policy is verified rather than trusted: for every word where both a
surface and an index form are recoverable, stripping the brackets must
REPRODUCE TITUS'S OWN INDEX FORM. A mismatch is a hard failure. Coverage is
measured and reported rather than assumed, because some surfaces are split
across nested spans and yield no recoverable pair (see WORD_RE).
"""
import argparse
import binascii
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"C:/Projects/Hexapla-releases/titus_zohrab"
OUT = os.path.join(BASE, "extracted")

# Identical to extract_bakar.py's — parses this corpus with delta 0.
MARK_RE = re.compile(
    r'<span id=h(\d)><!(X?)Level (\d)>([^<]*)'
    r'(?:<A NAME="([^"]*)">&nbsp;</A>)?'
    r'(?:<A NAME="([^"]*)">&nbsp;</A>)?'
    r'</sPAN>')
LEVEL_PREFIX = {1: "Text collection", 2: "Book", 3: "Chapter", 4: "Verse",
                5: "Section", 6: "Paragraph"}
STRUCTURAL = (1, 2, 3, 4)      # these end a verse's text; 5/6 sit inside it

TAG_RE = re.compile(r'<(/?)([A-Za-z!][A-Za-z0-9]*)[^>]*>')
KNOWN_TAGS = {"span", "a", "br", "div", "font", "b", "i", "hr", "img",
              "sub", "sup", "p", "html", "head", "title", "meta", "link",
              "script", "body"}

ARM = r'\u0530-\u058F\uFB13-\uFB17'
ARM_RE = re.compile('[' + ARM + ']')

# Word + its index form. The surface must sit directly inside the <a>; where
# TITUS nests a further <span> the pair is unrecoverable and is COUNTED, not
# guessed at.
WORD_RE = re.compile(r"ci\((\d+),'([0-9A-Fa-f]*)'\)\">([^<]*)</a>")
PAREN_RE = re.compile(r'[()]')
VERSE_NUM_RE = re.compile(r'^\d+$')


def file_for(n):
    """TITUS rolls the name over past 999: armat999.htm -> arma1000.htm."""
    return "armat%03d.htm" % n if n <= 999 else "arma%d.htm" % n


class Census:
    def __init__(self):
        self.unrecognized = []
        self.anomalies = []
        self.tag_counter = Counter()
        self.notes = []

    def anomaly(self, kind, where, detail):
        self.anomalies.append({"kind": kind, "where": where, "detail": detail})

    def unknown(self, where, what):
        self.unrecognized.append({"where": where, "what": what})


ARM_LETTER_RE = re.compile(r'[^Ա-Ֆա-ևﬓ-ﬗ]')


def letters_only(s):
    """Armenian letters, case-folded — nothing else. Used ONLY for the bracket
    verification, never on text that reaches the dump."""
    return ARM_LETTER_RE.sub('', s).casefold()


def clean_text(raw_html, where=""):
    """Strip tags/entities, collapse whitespace. Brackets are NOT touched here
    — stripping happens once, in strip_brackets, so the verification can run
    against the untouched surface first."""
    txt = TAG_RE.sub(' ', raw_html)
    if '<' in txt or '>' in txt:
        raise AssertionError("angle bracket residue at %s: %r" % (where, txt[:200]))
    txt = html.unescape(txt).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', txt).strip()


def strip_brackets(txt, stats):
    n = len(PAREN_RE.findall(txt))
    if n:
        stats["parens_stripped"] += n
        txt = PAREN_RE.sub('', txt)
        # Collapse any space the removal exposed (there should be none, but a
        # silent double space would show up in the asset).
        txt = re.sub(r'\s+', ' ', txt).strip()
    return txt


def verify_brackets(doc, where, census, stats):
    """The gate that makes the strip policy checkable rather than trusted.

    For every recoverable (surface, index-form) pair whose surface carries
    parentheses, the bracket-stripped surface must equal TITUS's own index
    form. Case-folded: chapter headings print the word in capitals
    («ԳԼ(ՈՒԽ)») while the index stores it lowercase («գլուխ»).
    """
    for m in WORD_RE.finditer(doc):
        surface = html.unescape(m.group(3)).strip()
        if not surface:
            stats["pairs_unrecoverable"] += 1       # nested-span surface
            continue
        try:
            idx = binascii.unhexlify(m.group(2)).decode("utf-16-le")
        except Exception:
            stats["pairs_unrecoverable"] += 1
            continue
        if not idx:
            stats["pairs_unrecoverable"] += 1
            continue
        if '(' not in surface and ')' not in surface:
            stats["pairs_plain"] += 1
            continue
        stats["pairs_bracketed"] += 1
        stripped = PAREN_RE.sub('', surface)
        # Compare on ARMENIAN LETTERS ONLY. The displayed surface carries
        # punctuation (a leading comma, the interpunct ·) and accent marks
        # (շեշտ, e.g. «ա(ստուա́)ծ») that TITUS's index form normalizes away;
        # comparing raw would report those as bracket failures. 111 such false
        # mismatches appeared before this narrowing, every one of them an
        # artifact of the comparison rather than a bad strip. The gate exists
        # to prove BRACKET REMOVAL is sound, so it must vary only brackets.
        if letters_only(stripped) != letters_only(idx):
            stats["mismatches"] += 1
            census.anomaly("bracket-strip-mismatch", where,
                           "surface %r -> %r but TITUS index says %r"
                           % (surface, stripped, idx))


def parse_file(n, census, state, stats, strict):
    path = os.path.join(BASE, file_for(n))
    with open(path, encoding="utf-8") as f:
        doc = f.read()
    where = file_for(n)

    for t in TAG_RE.finditer(doc):
        name = t.group(2).lower()
        census.tag_counter[name] += 1
        if name not in KNOWN_TAGS and not name.startswith('!'):
            census.unknown(where, "unknown tag <%s>" % name)

    verify_brackets(doc, where, census, stats)

    n_comments = len(re.findall(r'<!X?Level \d>', doc))
    marks = []
    for m in MARK_RE.finditer(doc):
        span_id, level = int(m.group(1)), int(m.group(3))
        label = m.group(4).strip()
        assert span_id == level, "h%d vs Level %d in %s" % (span_id, level, where)
        prefix = LEVEL_PREFIX[level] + ":"
        if not label.startswith(prefix):
            census.unknown(where, "label %r does not match level %d" % (label, level))
            continue
        marks.append({"level": level, "value": label[len(prefix):].strip(),
                      "anchor": m.group(5), "start": m.start(), "end": m.end()})
    n_skipped = len([u for u in census.unrecognized if u["where"] == where])
    assert len(marks) + n_skipped == n_comments, \
        "%s: %d <!Level> comments but %d markers (+%d listed)" % (
            where, n_comments, len(marks), n_skipped)

    # ⚠ THE FOOTER CUT MUST BE VISIBLE TO THE VERSE WALK, NOT JUST TO THE TAIL
    # CHECK. It was originally local to the tail check, so the LAST verse of a
    # file ran to len(doc) and swallowed TITUS's copyright boilerplate as
    # scripture: «…ապաշաւեսջիր ։ This text is part of the TITUS edition …
    # Copyright TITUS Project, Frankfurt a/M». One contaminated verse per file
    # x 1,048 files. Same defect class as the ru_synodal escaped-OSIS and
    # la_vulgata marker leaks, and invisible to the tail check because the
    # boilerplate is English — the check only looks for ARMENIAN escaping the
    # units, never for English leaking into them.
    footer_cut = len(doc)
    if marks:
        for pat in ('<DIV ALIGN=RIGHT>', 'This text is part'):
            i = doc.find(pat, marks[-1]["end"])
            if i != -1:
                footer_cut = min(footer_cut, i)
        if footer_cut == len(doc):
            census.anomaly("no-footer-found", where, "verse text may run to EOF")

    # Head/tail must carry no Armenian scripture — proof nothing was cut off.
    if marks:
        head = clean_text(re.sub(r'(?is)<script.*?</script>', ' ',
                                 doc[:marks[0]["start"]]), where + "(head)")
        cut = footer_cut
        tail = clean_text(doc[cut:], where + "(tail)")
        for nm, sl in (("head", head), ("tail", tail)):
            if ARM_RE.search(sl):
                census.anomaly("armenian-outside-units", "%s %s" % (where, nm),
                               sl[:200])

    # Walk the markers, slicing text between them.
    for i, mk in enumerate(marks):
        lvl = mk["level"]
        if lvl == 2:
            state["book"] = mk["value"]
            state["book_files"].setdefault(mk["value"], where)
            state["book_order"].append(mk["value"])
        elif lvl == 3:
            if state["book"] is None:
                census.anomaly("chapter-before-book", where, mk["value"])
                continue
            state["chapter"] = mk["value"]
        elif lvl == 4:
            if state["book"] is None or state["chapter"] is None:
                census.anomaly("verse-before-chapter", where, mk["value"])
                continue
            if not VERSE_NUM_RE.match(mk["value"]):
                census.anomaly("non-numeric-verse-label", where, mk["value"])
            # Text runs to the next STRUCTURAL marker; Section/Paragraph
            # markers sit inside verses and are stripped with the tags.
            end = footer_cut
            for nxt in marks[i + 1:]:
                if nxt["level"] in STRUCTURAL:
                    end = nxt["start"]
                    break
            raw = doc[mk["end"]:end]
            txt = clean_text(raw, "%s v%s" % (where, mk["value"]))
            txt = strip_brackets(txt, stats)
            b, c, v = state["book"], state["chapter"], mk["value"]
            if v in state["data"][b][c]:
                # ⚠ NEVER overwrite. Esther's chapters 5-8 and 11 each occur
                # TWICE in the file sequence, because TITUS interleaves the
                # Greek Additions (numbered as chapters 11-16, Vulgate style)
                # into their narrative positions and then RESUMES the canonical
                # chapter — armat447 is ch15 (Addition D, which stands in for
                # 5:1-3) and armat448 picks canonical ch5 back up at verse 4.
                # A plain dict assignment silently dropped the first copy: 41
                # verses of Esther were being lost while the census cheerfully
                # reported them as "anomalies". Both copies are kept, with the
                # file each came from, and the converter decides.
                state["collisions"].append(
                    {"book": b, "chapter": c, "verse": v, "file": where,
                     "kept_from": state["provenance"]["%s|%s|%s" % (b, c, v)],
                     "text": txt})
                census.anomaly("duplicate-verse", where, "%s %s:%s" % (b, c, v))
                continue
            state["data"][b][c][v] = txt
            state["provenance"]["%s|%s|%s" % (b, c, v)] = where
            state["anchors"]["%s|%s|%s" % (b, c, v)] = mk["anchor"]
            stats["verses"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lenient", action="store_true")
    args = ap.parse_args()

    census = Census()
    state = {"book": None, "chapter": None,
             "data": defaultdict(lambda: defaultdict(dict)),
             "anchors": {}, "book_files": {}, "book_order": [],
             "collisions": [], "provenance": {}}
    stats = Counter()

    # 'at' must be tried before 'a', or armatNNN.htm never matches and only the
    # 49 rolled-over arma1NNN files are seen — which the contiguity assertion
    # below catches rather than silently extracting 5% of the Bible.
    files = sorted(f for f in os.listdir(BASE) if re.fullmatch(r'arm(?:at|a)\d+\.htm', f))
    nums = sorted(int(re.search(r'(\d+)\.htm$', f).group(1)) for f in files)
    assert nums == list(range(1, len(nums) + 1)), "file numbering is not contiguous"
    print("files: %d (armat001..%s)" % (len(nums), file_for(nums[-1])))

    for n in nums:            # numeric order matters: Book identity carries
        parse_file(n, census, state, stats, not args.lenient)

    books = {b: {c: dict(v) for c, v in chs.items()}
             for b, chs in state["data"].items()}

    # ── assertions over the assembled corpus ────────────────────────────
    # NOTE: the bracket-mismatch assertion deliberately fires at the END, after
    # the census has been written. An assertion that aborts before dumping the
    # evidence it is complaining about cannot be diagnosed.
    dupes = [b for b in state["book_order"]
             if state["book_order"].count(b) > 1]
    if dupes:
        census.anomaly("book-marker-repeated", "corpus", str(sorted(set(dupes))))

    # Non-numeric chapter labels are MEANINGFUL and must never be silent: the
    # contiguity check below only looks at digit keys, so an asterisked block
    # would pass unnoticed while carrying real scripture. Three exist:
    #   Prov. 24* / 30* / 31* — Septuagint-order continuation blocks
    #   Cant. 8a              — a 6-verse unit after ch 8's full 14
    #   Abd.  _               — TITUS's empty label for a 1-chapter book
    for b, chs in books.items():
        for c in sorted(c for c in chs if not c.isdigit()):
            census.anomaly("non-numeric-chapter-label", b,
                           "chapter %r holds %d verses" % (c, len(chs[c])))

    # Chapters must be 1..N contiguous within each book.
    for b, chs in books.items():
        got = sorted(int(c) for c in chs if c.isdigit())
        if got and got != list(range(1, len(got) + 1)):
            census.anomaly("chapter-gap", b, "chapters %s" % got)
        for c, vs in chs.items():
            nv = sorted(int(v) for v in vs if v.isdigit())
            if nv and nv != list(range(1, len(nv) + 1)):
                census.anomaly("verse-gap", "%s %s" % (b, c),
                               "first %s last %s count %d" % (nv[0], nv[-1], len(nv)))

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "zohrab_raw.json"), "w", encoding="utf-8") as f:
        json.dump({"books": books, "anchors": state["anchors"],
                   "collisions": state["collisions"],
                   "book_order": state["book_order"],
                   "book_first_file": state["book_files"]},
                  f, ensure_ascii=False)

    per_book = {b: {"chapters": len(chs),
                    "verses": sum(len(v) for v in chs.values())}
                for b, chs in sorted(books.items())}
    census_out = {
        "stats": dict(stats),
        "books": per_book,
        "unrecognized": census.unrecognized,
        "anomalies": census.anomalies,
        "collisions": state["collisions"],
        "tags": dict(census.tag_counter.most_common()),
    }
    with open(os.path.join(OUT, "zohrab_census.json"), "w", encoding="utf-8") as f:
        json.dump(census_out, f, ensure_ascii=False, indent=1)

    # ── report ──────────────────────────────────────────────────────────
    print("books: %d   chapters: %d   verses: %d"
          % (len(books), sum(x["chapters"] for x in per_book.values()),
             stats["verses"]))
    print("brackets stripped: %d" % stats["parens_stripped"])
    print("bracket verification: %d bracketed pairs checked, %d plain, "
          "%d unrecoverable, MISMATCHES %d"
          % (stats["pairs_bracketed"], stats["pairs_plain"],
             stats["pairs_unrecoverable"], stats["mismatches"]))
    print("unrecognized elements: %d" % len(census.unrecognized))
    print("anomalies: %d" % len(census.anomalies))
    kinds = Counter(a["kind"] for a in census.anomalies)
    for k, v in kinds.most_common():
        print("    %-28s %d" % (k, v))
    print("\nwrote %s" % OUT)

    assert stats["mismatches"] == 0, (
        "%d bracket-strip mismatches against TITUS's own index — the strip "
        "policy is NOT safe as written; inspect zohrab_census.json "
        "(kind=bracket-strip-mismatch) before touching this assertion"
        % stats["mismatches"])


if __name__ == "__main__":
    main()
