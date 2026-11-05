# -*- coding: utf-8 -*-
"""Build is_thorlaks.json (id "thl") from the Thorlaksbiblia 1644 transcription.

    python tools/build_thorlaks_nt.py              # DRY RUN (the default)
    python tools/build_thorlaks_nt.py --write      # write the asset
    python tools/build_thorlaks_nt.py --selftest   # marker-table fixture

SOURCE: C:/Projects/Hexapla-releases/research/thorlaks_<book>.md, 27 NT books
(all required) plus every OT book in OT_FILES whose file EXISTS (Genesis from
2026-10-20; a later OT book needs only an OT_FILES row and an IS_OT_NAMES
name), transcribed by this project from the Landsbokasafn Islands scans
(BibliaTHaderllHe000036976v3; OT = v1). PD by age. Slots are the KJV order of
en_kjv.json (OT 0..38, NT 39..65); a slot with no file ships no chapters, as
en_tyndale.json does. Everything before the first
`## <Book> 1` heading is file apparatus and is ignored; inside the chapters
`N text` lines are verses and no other line is ever dropped (rule l); any
other heading ends the chapter run (appendices, divergence tables).

VERSIFICATION: positional by the print's own numerals as filed (slot = N-1,
no remap onto the KJV grid). A gap is "", a duplicate numeral DIES. The dry
run names every chapter whose slot count differs from en_kjv.json.

MARKERS: the owner-delegated table (a-k, 2026-10-07) plus the EXTRA rows the
build agent added after the inventory found classes the table did not name.
Every EXTRA row is labelled as such below so a later ruling is a one-line
change. Any `[...]` that no row claims ABORTS the build with its sites; a
bracket is never silently stripped. After the transform, any `[`, `]`, `{`,
`}`, `"`, U+2019, `**` or English apparatus word left in a verse also ABORTS.

  a  <...> (angle brackets U+27E8/27E9, nested too)     -> deleted
  b  [ornate initial: X]                                 -> X (joined)
     [ornate cap, letter not legible], [illegible: drop-cap],
     [illegible: ornate initial letter]                  -> U+00B7
     [ornament], [ornament fragment...], [ornamental initial] -> deleted
  c  [X]/[XY], ^[A-Za-zThornthornEthethAEae]{1,2}$ except [HN] -> X
  d  [a/b] alternatives                                  -> a (trimmed)
  e  [?]                                                 -> U+00B7
  f  [HN]  HN_MODE "witness": letter from the owner-authorised witness
          table (HN_TABLE; Gudbrandsbiblia 1584, H/N only, 2026-10-07);
          UNRESOLVED -> U+00B7. "literal": ships "[HN]".
  g  [abbrev], [abbrev.mark], letter+"+(space|punct|end) -> U+02BC
  h  [illegible...] (not b's forms)                      -> U+2026
  i  editorial notes (unnumbered/printed/sic/...)        -> deleted
     [not in this print...]                              -> whole verse ""
  j  sorts, nasal bars, doubled letters                  -> untouched
  k  virgule: \\s*/\\s* -> ", "; collapse commas; no space before
     punctuation; collapse whitespace; strip.
  l  unnumbered / indented-numeral / glued-numeral line inside a chapter run
     -> joined to the open verse of the same printed chapter (chapter-head
     prelude -> prepended to its first numbered verse); never dropped; the
     dry run lists every site (Fable, 2026-10-07).
  m  the verse-end cross «+» (EXTRA, Fable s13a 2026-11-05, owner-delegated O-2; research keeps every token as read):
     «.+», «.+[?]», «.[+?]»            -> «.»   (the stop stands, the cross is absorbed)
     «word+», «word +», «word+[?]»     -> «.»   (a cross with no stop IS the stop position)
     «/+», «/ +» (after other punct.)  -> «»    (the punctuation stands)
     a cross LEADING the verse body    -> «»    (the printed numeral's own mark: Josh 13:11, 18:28)
     A «+» left in a verse after the transform ABORTS (residue).
"""
import argparse
import collections
import io
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
RESEARCH = Path("C:/Projects/Hexapla-releases/research")
OUT = REPO / "app/src/main/assets/bibles/is_thorlaks.json"
KJV_ASSET = REPO / "app/src/main/assets/bibles/en_kjv.json"

MIDDOT = "\u00b7"
ELLIP = "\u2026"
APOS = "\u02bc"

# f: the ONE place the [HN] ruling lives. Owner 2026-10-07: resolve from the
# Gudbrandsbiblia 1584 witness table (H/N only); UNRESOLVED rows -> MIDDOT.
# "literal" ships "[HN]" untouched (the pre-ruling behaviour).
HN_MODE = "witness"
HN_OUT = "[HN]"                      # literal mode only
HN_TABLE = RESEARCH / "_evidence/thorlaks_hn_witness_2026-10-07.tsv"
# Same site grammar and same text view as tools/thorlaks_hn_witness.py, which
# indexes occurrences as enumerate(SITE.finditer(ornate(raw_verse))).
HN_SITE = re.compile(r"((?:[^\W\d_]|\[\?\])*)\[HN\]((?:[^\W\d_]|\[\?\])*)", re.U)

# research file stem -> heading name used inside it
FILES = {
    "matthew": "Matthew", "mark": "Mark", "luke": "Luke", "john": "John",
    "acts": "Acts", "romans": "Romans", "1corinthians": "1 Corinthians",
    "2cor": "2 Corinthians", "galatians": "Galatians", "ephesians": "Ephesians",
    "philippians": "Philippians", "colossians": "Colossians",
    "1thessalonians": "1 Thessalonians", "2thessalonians": "2 Thessalonians",
    "1timothy": "1 Timothy", "2timothy": "2 Timothy", "titus": "Titus",
    "philemon": "Philemon", "hebrews": "Hebrews", "james": "James",
    "1peter": "1 Peter", "2peter": "2 Peter", "1john": "1 John",
    "2john": "2 John", "3john": "3 John", "jude": "Jude",
    "revelation": "Revelation",
}
NT_ORDER = list(FILES.values())          # KJV order, slots 39..65

# OT: research file stem -> heading name (= the en_kjv.json name, which gives
# the slot 0..38). Built only WHEN research/thorlaks_<stem>.md EXISTS; a later
# book (Exodus: "exodus": "Exodus") needs this row plus an IS_OT_NAMES name.
OT_FILES = {
    "genesis": "Genesis",
    "exodus": "Exodus",          # owner yes 2026-10-26 (owner_queue_s78 Q-1)
    "leviticus": "Leviticus",
    "numbers": "Numbers",        # owner 2026-11-04: «ship numbers, deutoronomy, and joshua»
    "deuteronomy": "Deuteronomy",
    "joshua": "Joshua",          # partial: unread pages leave chapters short
}

# >>> OT BOOK NAMES -- the ONE place they live. Ruled (s44 Q3, 2026-10-20):
# ordinal-word form, as the NT's «Fyrra/Síðara Korintubréf». A missing name DIES (never an English fallback).
GENESIS_NAME = "Fyrsta Mósebók"
IS_OT_NAMES = {
    "Genesis": GENESIS_NAME,
    # 2026-10-26: the biblian.is Gudbrandsbiblia chapter titles (research/_witness/gudbrandsbiblia,
    # «Önnur Mósebók 1. kafli», «Þriðja Mósebók 1. kafli»); owner yes (owner_queue_s78 Q-1a)
    "Exodus": "Önnur Mósebók",
    "Leviticus": "Þriðja Mósebók",
    # 2026-11-04: same witness titles («Fjórða Mósebók 1. kafli», «Fimmta Mósebók 1. kafli», «Jósúabók 1. kafli»)
    "Numbers": "Fjórða Mósebók",
    "Deuteronomy": "Fimmta Mósebók",
    "Joshua": "Jósúabók",
}
# <<<

# Icelandic NT book names (modern standard forms; recalled, not derived --
# change here if the owner prefers others). OT/apocrypha slots with no
# research file keep the KJV English names with no chapters, as
# en_tyndale.json does.
IS_NAMES = [
    "Matteusargu\u00f0spjall", "Mark\u00fasargu\u00f0spjall", "L\u00fakasargu\u00f0spjall",
    "J\u00f3hannesargu\u00f0spjall", "Postulasagan", "R\u00f3mverjabr\u00e9fi\u00f0",
    "Fyrra Korintubr\u00e9f", "S\u00ed\u00f0ara Korintubr\u00e9f", "Galatabr\u00e9fi\u00f0",
    "Efesusbr\u00e9fi\u00f0", "Filipp\u00edbr\u00e9fi\u00f0", "K\u00f3lossubr\u00e9fi\u00f0",
    "Fyrra \u00deessalon\u00edkubr\u00e9f", "S\u00ed\u00f0ara \u00deessalon\u00edkubr\u00e9f",
    "Fyrra T\u00edm\u00f3teusarbr\u00e9f", "S\u00ed\u00f0ara T\u00edm\u00f3teusarbr\u00e9f",
    "T\u00edtusarbr\u00e9f", "F\u00edlemonsbr\u00e9f", "Hebreabr\u00e9fi\u00f0",
    "Jakobsbr\u00e9f", "Fyrra P\u00e9tursbr\u00e9f", "S\u00ed\u00f0ara P\u00e9tursbr\u00e9f",
    "Fyrsta J\u00f3hannesarbr\u00e9f", "Anna\u00f0 J\u00f3hannesarbr\u00e9f",
    "\u00deri\u00f0ja J\u00f3hannesarbr\u00e9f", "J\u00fadasarbr\u00e9f",
    "Opinberunarb\u00f3k J\u00f3hannesar",
]

# ---------------------------------------------------------------- EXTRA rows
# SITE_FIXES: (book, ch, v, old, new) applied to the RAW line before any rule.
# Each is a source defect the generic table cannot express (malformed bracket,
# margin gloss / next verses spilled into a line, an English colophon note).
# `old` must occur exactly once or the build dies.
SITE_FIXES = [
    # Luke 15:12 "[ornate initial: " retired 2026-10-26: fixed in research s72 (SETTLED 2026-10-24, luke_15_12 ruling)
    # Luke 19:29 "[ornate initial: [illegible]" retired 2026-10-13: in-word I106 T0114 joined it to Oliuestí/ in research
    ("Luke", 6, 1, "{a} ", ""),                            # footnote anchor in braces
    ("Matthew", 24, 1, "marginal heading: XXIIII 1 ", ""),
    # Matthew 28:20 colophon note retired 2026-10-27: moved out of the verse row in research (owner Q-7 D-5)
    ("Romans", 1, 11, None, " 12 (\u00fe er)"),           # None: truncate at `new`
    ("John", 14, 31, None, " 16 (Huggara)"),               # margin gloss spill
    ("2 Corinthians", 8, 13, "jafnt.14", "jafnt."),        # next numeral glued on
    # Acts 1:8 " a (Bipalning)" and 3:26 " c (Illsku)" retired 2026-11-04: the glosses were removed in research s111
    # (2026-10-31; diff vs thorlaks_acts.md.bak-s111), so the anchors no longer occur
    ("John", 4, 38, " c (Adrer)", ""),
    # rule l seams (2026-10-07): a word the print broke across lines/pages
    ("1 Corinthians", 1, 14, "Gu [continued] de", "Gude"),
    ("1 Corinthians", 5, 3, "fra [continued] vande", "fravande"),
    ("1 Corinthians", 7, 4, "si- [continued] sijns", "sijns"),
    ("2 Corinthians", 11, 28, "Has- (cont'd, open — continues onto p171) kasemdum", "Haskasemdum"),
    # page-seam rulings (Fable 2026-10-07, two agreeing looks): p169 opens «nauts/»
    ("2 Corinthians", 8, 19, "Foru [catchword: naurz] [continues idx 169] nauts", "Forunauts"),
    # the sheet-cut head repeated by the second sheet's read
    ("2 Thessalonians", 1, 5, "Huad z mussar/ (cut off at sheet boundary — continues on sheet2) ", ""),
]

# Editorial parentheticals (English apparatus inside verse lines) -> deleted.
# The note must CLOSE: an optional ")" let "(cont)" + [^()]* eat the rest of the verse
# (Romans 12:7 shipped empty, 2026-10-07).
PAREN_NOTE = re.compile(
    r"\s*\((?:cont\)|(?:open site|cont\.,|cont'd|continues|cut off|verse continues|"
    r"uncertain|o read plain|unnumbered|decorated initial|lines \d|"
    r"superscript|inline|an inline|NOTE:)[^()]*\))")
# Printed footnote anchors "(a)".."(d)" in the running text -> deleted.
PAREN_ANCHOR = re.compile(r"\s*\([a-d]\)")

# i: editorial note classes (prefix match on the bracket content) -> deleted.
NOTE_PREFIXES = (
    "printed \u00ab", "unnumbered", "UNNUMBERED", "no printed numeral",
    "decorated initial, unnumbered", "sic", "continued", "chapter heading",
    "catchword", "page foot", "uncertain word", "see Open sites",
    # EXTRA (agent, 2026-10-07): further apparatus classes found by inventory
    "\u24d8", "numeral ", "printed numeral", "\u26a0 no separate numeral",
    "margin gloss", "marginal note", "apparatus anchor", "anchor letter",
    "footnote", "inline footnote", "end of this agent", "cut off", "cut",
    "...continues", "continues, catchword", "tail, continuing", "printer's foot",
    "printed with the special", "uncertain:", "the decorated \u00ab",
    "p143 foot catchword",
    "continues idx",   # EXTRA (rule l exposed it, 2 Cor 8:18, 2026-10-07)
)
# EXTRA: margin name glosses printed beside 2 Tim 4 (e.g. [Demas.]) -> deleted
MARGIN_NAMES = re.compile(r"^(?:[A-Z][a-z]+\.\s*)+$")
# EXTRA: an initial whose letter is not given -> MIDDOT
INITIAL_UNREAD = (
    "ornate initial", "ornate initial, decorative flourish", "decorated initial",
    "decorative woodcut initial", "illustration initial, letter illegible",
    "drop-cap", "drop-cap unclear",
    "decorated initial, letter unclear \u2014 see Open sites",
)
# EXTRA: an ornament that is explicitly not a letter -> deleted
ORNAMENT_EXTRA = (
    "ornament, not a letter", "ornament?", "decorative flourish, not a letter",
    "ornamental flourish/paragraph mark, not a legible letter", "mark",
)
LETTERS = "A-Za-z\u00de\u00fe\u00d0\u00f0\u00c6\u00e6"
WORDCH = r"[^\W\d_]|[\u0300-\u036f\u1dc0-\u1dff\u2070-\u209f\u1d2c-\u1d6a\u02b0-\u02ff\u0304]"
SUPPLIED = re.compile(r"^(?:%s|[ \u00f1\u0169\u0303\u0304\u0305\u2c65\ua751\ua765])+$" % WORDCH)

COUNTS = collections.Counter()


def classify(c, at_start, joined):
    """Bracket content -> (rule, replacement). None = unclaimed (abort)."""
    # b
    m = re.match(r"^ornate initial: (.+)$", c)
    if m:
        x = m.group(1).strip()
        if x == "?":
            # EXTRA b': "?" is not a letter -> unread glyph; mid-verse, spaced
            # on both sides, it is an ornament mark inside a complete line.
            return ("b", MIDDOT if (at_start or joined) else "")
        return ("b", x.rstrip("?"))
    if c in ("ornate cap, letter not legible", "illegible: drop-cap",
             "illegible: ornate initial letter"):
        return ("b", MIDDOT)
    if c == "ornament" or c.startswith("ornament fragment") or c == "ornamental initial":
        return ("b", "")
    m = re.match(r"^(?:decorated|drop-cap) ([%s])$" % LETTERS, c)      # EXTRA
    if m:
        return ("b+", m.group(1))
    m = re.match(r"^(\w+) \u2014 large verse-initial", c)            # EXTRA
    if m:
        return ("b+", m.group(1)[0])
    if c in INITIAL_UNREAD:
        return ("b+", MIDDOT)
    if c in ORNAMENT_EXTRA:
        return ("b+", "")
    # f before c
    if c == "HN":
        # witness mode resolves every [HN] before transform; one left = abort
        return ("f", HN_OUT) if HN_MODE == "literal" else None
    # c
    if re.match(r"^[%s]{1,2}$" % LETTERS, c):
        return ("c", c)
    # d
    # an editorial note with a slash in it ("rows line50 L/R") is not an
    # alternate reading: it shipped as the word "unnumbered" in 5 verses (2026-10-07)
    if "/" in c and not c.startswith(("ornamental", "word struck") + NOTE_PREFIXES):
        alt = re.split(r"\s+\u2014\s+", c)[0].split("/")[0].strip().lstrip("?")
        if alt and re.match(r"^(?:%s)+$" % WORDCH, alt):
            return ("d", alt)
    # e
    if c == "?":
        return ("e", MIDDOT)
    # g
    if c in ("abbrev", "abbrev.mark"):
        return ("g", APOS)
    # i (before h so "[illegible...]" forms named there win)
    if c.startswith("not in this print"):
        return ("i-verse", None)
    if MARGIN_NAMES.match(c):                                          # EXTRA
        return ("i+", "")
    if c.startswith(NOTE_PREFIXES):
        return ("i", "")
    # h
    if c.startswith("illegible") or c == "illegible mark":
        return ("h", ELLIP)
    if c.startswith(("word struck through", "gap \u2014")):            # EXTRA
        return ("h+", ELLIP)
    # EXTRA c': a supplied / uncertain reading -> its text, query marks and
    # trailing notes dropped ([Frelsara], [Ver?], [Eske -- see Open sites]).
    t = re.split(r"\s+\u2014\s+", c)[0]
    t = re.sub(r"\(\?\)$|\?+$|\.\.\.$", "", t).strip()
    if t and SUPPLIED.match(t):
        return ("c+", t)
    if c == "\u00b0":
        return ("c+", c)
    return None


# EXTRA (Fable, 2026-10-07): beta = the p-with-stroke sort, the superset sign =
# the Tironian et, combining overline = the combining macron
SORT_CANON = (("β", "ꝑ"), ("⊃", "⁊"), ("̅", "̄"))
BRACKET = re.compile(r"\[([^\[\]]*)\]")
# EXTRA m (Fable s13a 2026-11-05): the hedged cross forms consume their bracket BEFORE the bracket
# pass - the [?] hedges a punctuation mark, not a letter (U+00B7 would claim a missing letter).
CROSS_HEDGE = re.compile(r"\.\s*\+\[\?\]|\.\[\+\?\]|(?<=\S)\s*\+\[\?\]")
QUOTE = re.compile(r'(?<=[A-Za-z\u00fe\u00f0\u00e6\u00de\u00d0\u00c6])"(?=[ /,.;:?!)]|$)')


def transform(text, where, unclaimed):
    """Apply a..k to one verse body. Returns (out, whole_verse_empty)."""
    # a: angle-bracket notes, innermost first (nested ones exist)
    n = 1
    while n:
        text, n = re.subn("\u27e8[^\u27e8\u27e9]*\u27e9", "", text)
        COUNTS["a"] += n
    # EXTRA: English parenthetical notes and printed anchor letters
    text, n = PAREN_NOTE.subn("", text); COUNTS["paren-note+"] += n
    text, n = PAREN_ANCHOR.subn("", text); COUNTS["paren-anchor+"] += n
    # m1: hedged cross forms -> the stop (EXTRA m)
    text, n = CROSS_HEDGE.subn(".", text); COUNTS["m-hedge+"] += n
    # b-i: brackets
    empty = False
    out, pos = [], 0
    for m in BRACKET.finditer(text):
        pre = text[:m.start()]
        at_start = pre.strip() == ""
        joined = m.end() < len(text) and not text[m.end()].isspace()
        r = classify(m.group(1), at_start, joined)
        if r is None:
            unclaimed.append((where, m.group(0)))
            rep = m.group(0)
        else:
            rule, rep = r
            COUNTS[rule] += 1
            if rule == "i-verse":
                empty, rep = True, ""
        out.append(text[pos:m.start()]); out.append(rep); pos = m.end()
    out.append(text[pos:])
    text = "".join(out)
    if empty:
        return "", True
    # m2: the bare cross (EXTRA m)
    text, n = re.subn(r"^\s*\+\s*", "", text); COUNTS["m-lead+"] += n          # leads the body: the numeral's mark
    text, n = re.subn(r"\.\s*\+", ".", text); COUNTS["m-stop+"] += n            # «.+» -> «.»
    text, n = re.subn(r"(?<=[/,;:!?])\s*\+", "", text); COUNTS["m-punct+"] += n # after other punctuation: dropped
    text, n = re.subn(r"(?<=\S)\s*\+", ".", text); COUNTS["m-word+"] += n       # after a word: the stop position
    # g: closing-quote abbreviation mark
    text, n = QUOTE.subn(APOS, text); COUNTS["g"] += n
    # k: virgule and whitespace
    text, n = re.subn(r"\s*/\s*", ", ", text); COUNTS["k"] += n
    text = re.sub(r",(?:\s*,)+", ",", text)
    text = re.sub(r"\s+([,;:.?!])", r"\1", text)
    text = re.sub(r"\s+\u2014\s*$", "", text)          # dash left by a deleted note
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[,\s]+", "", text)
    # EXTRA (Fable, 2026-10-07): one sort transcribed two ways -> one code point,
    # shipped text only (research stays diplomatic)
    for a, b in SORT_CANON:
        COUNTS["sort-canon+"] += text.count(a)
        text = text.replace(a, b)
    return text, False


JOINED = []   # (book, chapter, numeral or "head", text[:50]) -- rule l, listed by the dry run


def parse_file(path, book):
    """-> {chapter: {numeral: raw_text}} ; dies on duplicates.

    Rule l (Fable, 2026-10-07): a line inside a chapter run is never dropped.
    An unnumbered, indented-numeral or glued-numeral line joins the verse open
    above it in the same printed chapter; a chapter-head line (no verse open
    yet, e.g. Gal 6 carrying KJV 5:25-26) is prepended to the chapter's first
    numbered verse. A continuation numeral that is not the open verse DIES.
    """
    chapters, ch, started, last, prelude = {}, None, False, None, {}
    for ln in io.open(path, encoding="utf-8"):
        ln = ln.rstrip("\r\n")
        m = re.match(r"^## (.+?) (\d+)\s*$", ln)
        if m and m.group(1) == book and (started or m.group(2) == "1"):
            started, ch, last = True, int(m.group(2)), None
            if ch in chapters:
                sys.exit("DIE: %s: chapter %d heading twice" % (book, ch))
            chapters[ch] = {}
            continue
        if not started:
            continue
        if re.match(r"^#{1,6} ", ln):
            ch, last = None, None
            continue
        if ch is None or not ln.strip() or re.match(r"^\s*-{3,}\s*$", ln) \
                or re.match(r"^\s*\|", ln):
            continue
        m = re.match(r"^(\d+)\s+(.*)$", ln)
        if m:
            if m.group(2).startswith("|"):
                continue
            v = int(m.group(1))
            if v in chapters[ch]:
                sys.exit("DIE: duplicate numeral %s %d:%d" % (book, ch, v))
            chapters[ch][v] = m.group(2)
            last = v
            continue
        s = ln.strip()
        m = re.match(r"^(\d+)\s*(.*)$", s)
        if m:
            if int(m.group(1)) != last:
                sys.exit("DIE: continuation numeral %s != open verse %s at %s %d"
                         % (m.group(1), last, book, ch))
            s = m.group(2)
        if last is None:
            prelude[ch] = (prelude.get(ch, "") + " " + s).strip()
            JOINED.append((book, ch, "head", s[:50]))
        else:
            JOINED.append((book, ch, last, chapters[ch][last][-30:] + " || " + s[:40]))
            chapters[ch][last] += " " + s
    for c, text in prelude.items():
        if not chapters[c]:
            sys.exit("DIE: %s %d: chapter-head line but no numbered verse" % (book, c))
        first = min(chapters[c])
        chapters[c][first] = text + " " + chapters[c][first]
    return chapters


def apply_site_fixes(raw):
    for bk, c, v, old, new in SITE_FIXES:
        s = raw[bk][c][v]
        if old is None:
            i = s.find(new)
            if i < 0 or s.count(new) != 1:
                sys.exit("DIE: site fix %s %d:%d marker not found once" % (bk, c, v))
            raw[bk][c][v] = s[:i]
        else:
            if s.count(old) != 1:
                sys.exit("DIE: site fix %s %d:%d %r not found once" % (bk, c, v, old))
            raw[bk][c][v] = s.replace(old, new)
        COUNTS["site-fix+"] += 1


ENGLISH = re.compile(r"\b(?:the|see|printed|numeral|verse|idx|transcrib\w*|uncertain|"
                     r"continues|page|likely|possibly|scripture|margin\w*|footnote|"
                     r"read|heading)\b")


def residue_hit(out):
    """Post-transform ABORT set. U+2019 (F4-a, Fable ruling s44 2026-10-20): a reader's curly hook;
    conventions row 65 writes the raised hook `'` - the NT ships none, Genesis research had 10."""
    s = out.replace(HN_OUT, "") if HN_MODE == "literal" else out
    return bool(re.search(r'[\[\]{}"’+]|\*\*', s) or ENGLISH.search(s))


def hn_ornate(text):
    # must match thorlaks_hn_witness.ornate(): an unread woodcut is a `[?]` wildcard, or occurrence indices drift
    return re.sub(r"\[ornate initial: ?([^\]]*)\]", lambda m: "[?]" if m.group(1) == "?" else m.group(1), text)


def load_hn_table(path):
    """-> {(book, ch, v): {occ: (token, letter, basis)}}; dies on a malformed row."""
    rows = {}
    lines = io.open(path, encoding="utf-8").read().split("\n")
    if not lines[0].startswith("book\tchapter\tverse\toccurrence_index_in_verse\ttoken\tletter\tbasis"):
        sys.exit("DIE: %s: unexpected header %r" % (path, lines[0]))
    for i, ln in enumerate(lines[1:], 2):
        if not ln.strip():
            continue
        f = ln.rstrip("\r").split("\t")
        if len(f) < 7:
            sys.exit("DIE: %s:%d: %d columns" % (path, i, len(f)))
        bk, c, v, occ, tok, letter, basis = f[:7]
        # PINNED (F2, Fable ruling s44 2026-10-20): a durable in-word-look fill, applied by
        # thorlaks_hn_witness.py from research/_evidence/thorlaks_hn_pins.tsv
        ok = ((letter in ("H", "N") and basis in ("WITNESS", "CORPUS", "PINNED"))
              or (letter == "" and basis == "UNRESOLVED"))
        if not ok or "[HN]" not in tok:
            sys.exit("DIE: %s:%d: bad row %r" % (path, i, f[:7]))
        key = (bk, int(c), int(v))
        if int(occ) in rows.setdefault(key, {}):
            sys.exit("DIE: %s:%d: duplicate row %s occ %s" % (path, i, key, occ))
        rows[key][int(occ)] = (tok, letter, basis)
    return rows


def resolve_hn(raw, table):
    """Replace every [HN] in raw verse text from `table`. Returns the list of
    problem sites (non-empty = caller aborts; nothing is guessed)."""
    problems, used, badkeys = [], set(), set()
    for bk in raw:
        for c in raw[bk]:
            for v, text in list(raw[bk][c].items()):
                if "[HN]" not in text:
                    continue
                key, where = (bk, c, v), "%s %d:%d" % (bk, c, v)
                sites = [m.group(0) for m in HN_SITE.finditer(hn_ornate(text))]
                pos = [m.start() for m in re.finditer(r"\[HN\]", text)]
                rows = table.get(key, {})
                if len(sites) != len(pos):
                    problems.append("%s: %d site(s) in ornate view vs %d [HN] in raw" % (where, len(sites), len(pos)))
                    badkeys.add(key)
                    continue
                out, prev, bad = [], 0, False
                for occ, (site, p) in enumerate(zip(sites, pos)):
                    r = rows.get(occ)
                    if r is None:
                        problems.append("%s occ %d: no table row for %r" % (where, occ, site))
                        bad = True
                        continue
                    tok, letter, basis = r
                    tail = tok[tok.index("[HN]"):]
                    if tok != site or not text.startswith(tail, p):
                        problems.append("%s occ %d: token %r != text %r" % (where, occ, tok, site))
                        bad = True
                        continue
                    used.add((key, occ))
                    out.append(text[prev:p])
                    out.append(letter or MIDDOT)
                    prev = p + 4
                    COUNTS["f-" + (letter or "unresolved")] += 1
                out.append(text[prev:])
                if bad:
                    badkeys.add(key)
                else:
                    raw[bk][c][v] = "".join(out)
    for key, rws in table.items():
        if key[0] not in raw:  # table rows of a book this build does not include (no research file yet) are not its to check
            continue
        for occ, (tok, _, _) in rws.items():
            if (key, occ) not in used and key not in badkeys:
                problems.append("%s %d:%d occ %d: table row %r matches no [HN] in the text"
                                % (key + (occ, tok)))
    return problems


def slot_map(kjv):
    """-> {slot: heading name} for every book this build includes: the 27 NT
    books (slots 39..65, required) and each OT_FILES book whose research file
    exists (slot = its index among en_kjv.json's first 39 names)."""
    names = [b["name"] for b in kjv]
    slots = {39 + i: bk for i, bk in enumerate(NT_ORDER)}
    for stem, book in OT_FILES.items():
        if not (RESEARCH / ("thorlaks_%s.md" % stem)).exists():
            continue
        if book not in names[:39]:
            sys.exit("DIE: OT_FILES %r is not an OT name in %s" % (book, KJV_ASSET.name))
        if book not in IS_OT_NAMES:
            sys.exit("DIE: OT book %r has no IS_OT_NAMES entry" % book)
        slots[names.index(book)] = book
    return slots


def is_name(bi, book):
    return IS_NAMES[bi - 39] if bi >= 39 else IS_OT_NAMES[book]


def build():
    kjv = json.load(io.open(KJV_ASSET, encoding="utf-8"))
    raw = {}
    for stem, book in list(FILES.items()) + list(OT_FILES.items()):
        p = RESEARCH / ("thorlaks_%s.md" % stem)
        if book in OT_FILES.values() and not p.exists():
            continue                       # OT book not transcribed yet
        raw[book] = parse_file(p, book)
    if HN_MODE == "witness":
        probs = resolve_hn(raw, load_hn_table(HN_TABLE))
        if probs:
            print("ABORT: %d [HN] site(s) not resolvable from %s:" % (len(probs), HN_TABLE))
            for p in probs:
                print("  " + p)
            sys.exit(2)
    elif HN_MODE != "literal":
        sys.exit("DIE: HN_MODE %r" % HN_MODE)
    apply_site_fixes(raw)
    unclaimed, books, residue = [], [], []
    built = slot_map(kjv)
    if set(built.values()) != set(raw):
        sys.exit("DIE: slot map %s != parsed books %s" % (sorted(built.values()), sorted(raw)))
    for bi in range(83):
        name = kjv[bi]["name"]
        if bi not in built:
            books.append({"name": name, "chapters": []})
            continue
        bk = built[bi]
        chs = []
        for c in range(1, max(raw[bk]) + 1):
            vs = raw[bk].get(c)
            if vs is None:
                sys.exit("DIE: %s chapter %d missing" % (bk, c))
            slots = [""] * max(vs)
            for v, t in vs.items():
                out, _ = transform(t, "%s %d:%d" % (bk, c, v), unclaimed)
                slots[v - 1] = out
                if residue_hit(out):
                    residue.append(("%s %d:%d" % (bk, c, v), out[:160]))
            chs.append(slots)
        books.append({"name": is_name(bi, bk), "chapters": chs})
    if unclaimed:
        print("ABORT: %d bracket(s) claimed by no rule:" % len(unclaimed))
        for w, b in unclaimed:
            print("  %s  %s" % (w, b))
        sys.exit(2)
    if residue:
        print("ABORT: %d verse(s) still carry apparatus residue:" % len(residue))
        for w, t in residue:
            print("  %s  %s" % (w, t))
        sys.exit(2)
    return books, kjv, raw, built


def report(books, kjv, raw, built):
    total, diffs, gaps = 0, [], []
    print("per-book verses (non-empty / slots):")
    for bi in sorted(built):
        b, bk = books[bi], built[bi]
        ne = sum(1 for ch in b["chapters"] for v in ch if v)
        sl = sum(len(ch) for ch in b["chapters"])
        total += ne
        print("  %-16s %5d / %5d" % (bk, ne, sl))
        kc = kjv[bi]["chapters"]
        if len(kc) != len(b["chapters"]):
            diffs.append("%s: %d chapters vs KJV %d" % (bk, len(b["chapters"]), len(kc)))
        for ci, ch in enumerate(b["chapters"]):
            if ci < len(kc) and len(ch) != len(kc[ci]):
                diffs.append("%s %d: %d slots vs KJV %d" % (bk, ci + 1, len(ch), len(kc[ci])))
            for vi, v in enumerate(ch):
                if not v:
                    gaps.append("%s %d:%d" % (bk, ci + 1, vi + 1))
    print("TOTAL non-empty verses: %d (%s)" % (total, ", ".join(
        "%s %d" % (k, sum(1 for bi in built if (bi < 39) == (k == "OT")
                          for ch in books[bi]["chapters"] for v in ch if v)) for k in ("OT", "NT"))))
    print("chapters differing from KJV grid (%d):" % len(diffs))
    for d in diffs:
        print("  " + d)
    print("empty slots (%d): %s" % (len(gaps), ", ".join(gaps)))
    print("marker substitutions:")
    for k in sorted(COUNTS):
        print("  %-14s %d" % (k, COUNTS[k]))
    for bk, c, v in (("Genesis", 1, 1), ("John", 3, 16), ("Acts", 2, 1), ("Revelation", 22, 21)):
        if bk not in raw:
            continue
        bi = next(i for i, b in built.items() if b == bk)
        print("\n%s %d:%d\n  before: %s\n  after:  %s" % (
            bk, c, v, raw[bk][c][v], books[bi]["chapters"][c - 1][v - 1]))


def selftest():
    cases = [
        ("a", "Hoꝑ\u27e8?f\u27e9samer huoriu\u27e8m\u27e8\u00f8?\u27e9\u27e9 sem", "Hoꝑsamer huoriu sem"),
        ("b", "[ornate initial: O]G j", "OG j"),
        ("b", "[ornate cap, letter not legible]n er", MIDDOT + "n er"),
        ("b", "x [ornament] y [ornament fragment, top-left, partial] z [ornamental initial]aupu", "x y z aupu"),
        ("b'", "[ornate initial: ?]Ar var", MIDDOT + "Ar var"),
        ("c", "hñ[er] [OG] ꝥ", "hñer OG ꝥ"),
        ("d", "a[f/ p]nockrum blif[\u00fe/\u00df]a", "afnockrum blif\u00fea"),
        ("e", "orneñ[?] kan", "orneñ" + MIDDOT + " kan"),
        ("g", "Musterenu[abbrev] va\" sa, hag\".", "Musterenu" + APOS + " va" + APOS + " sa, hag" + APOS + "."),
        ("h", "sijn [illegible short word]na z [illegible] x", "sijn " + ELLIP + "na z " + ELLIP + " x"),
        ("i", "[unnumbered \u2014 printed v1] Og [printed \u00ab32\u00bb] sia [sic] ecke [catchword \u00abx\u00bb].", "Og sia ecke."),
        ("i", "[unnumbered — printed v46; rows line50 L/R] Og munu.", "Og munu."),
        ("i-verse", "[not in this print \u2014 Luther's text omits KJV 17:36]", ""),
        ("j", "ñ ū ꝥ ꝑ \u204a z m\u0304", "ñ ū ꝥ ꝑ \u204a z m\u0304"),
        ("k", "Mañ a mzal Phariseaña/ Nicodemus ad Nafne// hñ var ,", "Mañ a mzal Phariseaña, Nicodemus ad Nafne, hñ var,"),
        ("c+", "Guds vors [Frelsara] z [Ver?]kamadureñ [Eske \u2014 see Open sites] er", "Guds vors Frelsara z Verkamadureñ Eske er"),
        ("paren", "Enda. (inline footnote-marker \"a\" not transcribed) Og (b) sia (sagde hñ)", "Enda. Og sia (sagde hñ)"),
        ("paren", "(cont) sie hñ Truñe lijkur. Hefur nockur Embætte", "sie hñ Truñe lijkur. Hefur nockur Embætte"),
        ("m", "Borgena.+ Vered", "Borgena. Vered"),
        ("m", "tuffugu Gera.+[?]", "tuffugu Gera."),
        ("m", "reidubwner.[+?]", "reidubwner."),
        ("m", "þangad+[?] Og", "þangad. Og"),
        ("m", "haßa lastad+", "haßa lastad."),
        ("m", "af Reykelse +", "af Reykelse."),
        ("m", "so Dryckiaroffrenu/ +", "so Dryckiaroffrenu,"),
        ("m", "+ Zela/ Eleph", "Zela, Eleph"),
        ("m", "[unnumbered — reads A+B declared] Eñ x", "Eñ x"),
    ]
    COUNTS.clear()
    fails = 0
    for rule, inp, exp in cases:
        unc = []
        got, _ = transform(inp, "fixture " + rule, unc)
        ok = got == exp and not unc
        fails += not ok
        print("%s %-8s %r -> %r%s" % ("ok  " if ok else "FAIL", rule, inp, got,
                                      "" if ok else "  (expected %r, unclaimed %r)" % (exp, unc)))
    unc = []
    transform("x [some brand-new class] y", "fixture abort", unc)
    if not unc:
        print("FAIL abort: an unknown bracket class was claimed"); fails += 1
    else:
        print("ok   abort: unknown class left unclaimed -> build would abort")
    # f: [HN] from a witness table (H, N, UNRESOLVED -> middot, missing row,
    # token mismatch, orphan row -> each reported, i.e. the build aborts)
    raw = {"Luke": {1: {1: "[HN]ofud og [HN]ann", 2: "E[HN]n [HN]ws"},
                    2: {3: "x [HN]erra y"}}}
    table = {("Luke", 1, 1): {0: ("[HN]ofud", "H", "WITNESS"), 1: ("[HN]ann", "N", "CORPUS")},
             ("Luke", 1, 2): {0: ("E[HN]n", "", "UNRESOLVED"), 1: ("[HN]ws", "H", "WITNESS")}}
    probs = resolve_hn(raw, table)
    ok = (raw["Luke"][1][1] == "Hofud og Nann"
          and raw["Luke"][1][2] == "E" + MIDDOT + "n Hws"
          and raw["Luke"][2][3] == "x [HN]erra y"
          and len(probs) == 1 and "2:3" in probs[0] and "no table row" in probs[0])
    fails += not ok
    print("%s f        H / N / unresolved->middot / missing row -> %r %r %r"
          % ("ok  " if ok else "FAIL", raw["Luke"][1][1], raw["Luke"][1][2], probs))
    raw = {"Luke": {1: {1: "[HN]ofud"}}}
    probs = resolve_hn(raw, {("Luke", 1, 1): {0: ("[HN]afud", "H", "WITNESS")}})
    ok = len(probs) == 1 and "!=" in probs[0] and raw["Luke"][1][1] == "[HN]ofud"
    fails += not ok
    print("%s f-abort  token mismatch -> %r" % ("ok  " if ok else "FAIL", probs))
    raw = {"Luke": {1: {1: "[HN]ofud"}}}
    probs = resolve_hn(raw, {("Luke", 1, 1): {0: ("[HN]ofud", "H", "WITNESS")},
                             ("Luke", 1, 9): {0: ("[HN]x", "N", "WITNESS")}})
    ok = len(probs) == 1 and "matches no [HN]" in probs[0]
    fails += not ok
    print("%s f-abort  orphan table row -> %r" % ("ok  " if ok else "FAIL", probs))
    # F4-a: a curly U+2019 hook left after the transform aborts the build (residue)
    unc = []
    got, _ = transform("Gud’ sagde", "fixture u2019", unc)
    ok = residue_hit(got) and not residue_hit("Gud' sagde")
    fails += not ok
    print("%s abort    U+2019 left in a verse -> residue (build aborts): %r" % ("ok  " if ok else "FAIL", got))
    # EXTRA m (Fable s13a): a cross left in a verse aborts the build (the Luke 14:1 shipped form)
    ok = residue_hit("vord a hm̄+ z") and not residue_hit("vord a hm̄. z")
    fails += not ok
    print("%s abort    a cross left in a verse -> residue (build aborts)" % ("ok  " if ok else "FAIL"))
    # F2: a PINNED row of the witness table resolves like WITNESS/CORPUS
    import os
    import tempfile
    fd, tp = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    io.open(tp, "w", encoding="utf-8", newline="\n").write(
        "book\tchapter\tverse\toccurrence_index_in_verse\ttoken\tletter\tbasis\twitness_word_or_count\n"
        "Acts\t27\t34\t0\t[HN]opde\tH\tPINNED\tinword3 WITNESS höfði; [?] filled by in-word look\n")
    try:
        tbl = load_hn_table(tp)
        raw = {"Acts": {27: {34: "sitt [HN]opde"}}}
        probs = resolve_hn(raw, tbl)
        ok = not probs and raw["Acts"][27][34] == "sitt Hopde"
        got = raw["Acts"][27][34]
    except SystemExit as e:
        ok, got = False, "DIE %s" % e
    finally:
        os.remove(tp)
    fails += not ok
    print("%s f-pin    PINNED table row resolves -> %r" % ("ok  " if ok else "FAIL", got))
    subs = sum(v for k, v in COUNTS.items())
    print("substitutions counted: %d" % subs)
    if subs == 0:
        print("FAIL: zero substitutions -- the fixture is not exercising the rules"); fails += 1
    print("SELFTEST %s" % ("PASS" if not fails else "FAIL (%d)" % fails))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write the asset (default: dry run)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    books, kjv, raw, built = build()
    report(books, kjv, raw, built)
    print("\nrule l joins: %d" % len(JOINED))
    for bk, c, v, s in JOINED:
        print("  l  %s %d:%s  <- %s" % (bk, c, v, s))
    if not a.write:
        print("\nDRY RUN -- nothing written. --write to write %s" % OUT)
        return
    s = json.dumps(books, ensure_ascii=False, separators=(",", ":"))
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(s)
    back = json.load(io.open(OUT, encoding="utf-8"))
    flat = [v for b in back for ch in b["chapters"] for v in ch]
    strip = (lambda v: v.replace(HN_OUT, "")) if HN_MODE == "literal" else (lambda v: v)
    bad = [v for v in flat if "[" in strip(v) or "]" in strip(v)]
    assert len(back) == 83, len(back)
    assert not bad, "brackets remain: %r" % bad[:5]
    assert all(not back[i]["chapters"] for i in range(83) if i not in built)
    assert all(back[i]["chapters"] for i in built)
    if HN_MODE == "literal":
        hn = "%d [HN] sites literal, no other '['" % sum(v.count(HN_OUT) for v in flat)
    else:
        hn = ("[HN] from witness table: H %d, N %d, unresolved->middot %d; no '[' or ']' at all"
              % (COUNTS["f-H"], COUNTS["f-N"], COUNTS["f-unresolved"]))
    print("\nWROTE %s: %d books (%s built), %d verse slots, %d non-empty verses, %s"
          % (OUT, len(back), len(built), len(flat), sum(1 for v in flat if v), hn))


if __name__ == "__main__":
    main()
