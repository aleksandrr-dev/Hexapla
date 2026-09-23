# -*- coding: utf-8 -*-
"""Derive the COMPLETE lan-/lan- token inventory, verb and noun, across the
Karl XII corpus -- so the re-measure runs against a derived list rather than a
hand-written pattern.

Same corpus construction as kxii_precedent.py: a scripture line is `^[0-9]+ `
or `Argument:`.  Notes are excluded by the same rule, so the counts here and
there are comparable by construction.

Classification is by SUFFIX, and it is deliberately coarse:
  NOUN   laan / lan / lanet / lanen ...  (the thing lent)
  VERB   lana / lanar / lante / laner / lanad ...  (the act)
  OTHER  a prefixed lexeme (forlana, lands-, lange ...) -- reported, never
         silently folded in, because forlane is a DIFFERENT lexeme.

Refuses to report an empty inventory rather than printing a plausible zero.
"""
import glob, io, os, re, sys, collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RELEASES = os.path.join(os.path.dirname(REPO), "Hexapla-releases")
CORPUS = os.path.join(RELEASES, "research", "karlxii_*.md")

VERSE = re.compile(r"^([0-9]+) ")
# any word containing the lan/lan stem, ring or e, with optional doubled vowel
TOKEN = re.compile(r"\b\w*l[åä]{1,2}n\w*\b", re.UNICODE | re.IGNORECASE)

VERB_SUF = ("a", "ar", "ade", "at", "te", "t", "er", "e", "as", "ades")
NOUN_SUF = ("", "et", "en", "s", "ets")

def classify(tok):
    low = tok.lower()
    m = re.match(r"^(.*?)(l[åä]{1,2}n)(\w*)$", low, re.UNICODE)
    if not m:
        return "OTHER", ""
    prefix, stem, suf = m.groups()
    if prefix:
        return "OTHER", suf
    if suf in VERB_SUF and suf:
        return "VERB", suf
    if suf in NOUN_SUF:
        return "NOUN", suf
    return "OTHER", suf

def ring(tok):
    """RING = the a-with-ring; E = the e-diaeresis form."""
    low = tok.lower()
    m = re.search(r"l([åä]{1,2})n", low, re.UNICODE)
    if not m:
        return "?"
    v = m.group(1)
    return "RING" if "å" in v else "E"

def main():
    files = sorted(glob.glob(CORPUS))
    if not files:
        raise SystemExit("NO CORPUS FILES matched %s -- refusing to report" % CORPUS)
    rows = []
    nlines = 0
    for f in files:
        book = os.path.basename(f)[len("karlxii_"):-len(".md")]
        for lineno, line in enumerate(io.open(f, encoding="utf-8"), 1):
            m = VERSE.match(line)
            is_arg = line.startswith("Argument:")
            if not (m or is_arg):
                continue
            nlines += 1
            verse = m.group(1) if m else "Arg"
            for tok in TOKEN.findall(line):
                kind, suf = classify(tok)
                rows.append((book, lineno, verse, tok, kind, ring(tok)))
    if not rows:
        raise SystemExit("NO lan- TOKENS FOUND -- refusing to report an empty inventory")

    print("scanned %d scripture lines from %d file(s)\n" % (nlines, len(files)))
    counts = collections.Counter((r[4], r[5]) for r in rows)
    print("%-6s %-5s %s" % ("kind", "vowel", "count"))
    for (k, v), c in sorted(counts.items()):
        print("%-6s %-5s %d" % (k, v, c))

    for kind in ("VERB", "NOUN", "OTHER"):
        sel = [r for r in rows if r[4] == kind]
        if not sel:
            continue
        print("\n=== %s (%d tokens) ===" % (kind, len(sel)))
        print("%-12s %-7s %-6s %-6s %s" % ("book", "line", "verse", "vowel", "token"))
        for book, lineno, verse, tok, k, rg in sel:
            print("%-12s %-7d %-6s %-6s %s" % (book, lineno, verse, rg, tok))

if __name__ == "__main__":
    main()
