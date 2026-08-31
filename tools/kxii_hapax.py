# -*- coding: utf-8 -*-
"""kxii_hapax.py - find candidate MISREADINGS in the Karl XII apocrypha without
a witness, by looking for once-only word forms that sit one edit away from a
form the print uses often.

    python tools/kxii_hapax.py                      # whole corpus
    python tools/kxii_hapax.py --unwitnessed        # only the books kxii.se cannot check
    python tools/kxii_hapax.py --book Tobit --min-rival 3

## WHY THIS EXISTS

The kxii.se witness diff found five real defects in seven adjudicated sites on
2026-08-30/31. But only four books have cached witness HTML; the other eight
have NEVER had an independent check of any kind. This tool is the substitute
for a witness in those books, and it costs zero model tokens.

Three of the five defects the witness found share one shape:

    47:29  HEr      -> THer      (the frequent form runs 1215)
    19:10  dood     -> doo
    7:22   graaotet -> graotet

Each was a form appearing EXACTLY ONCE in 4,649 verses while a near-identical
form appeared many times. That is the signature this tool looks for. It is the
same reasoning the campaign already applies by hand with kxii_precedent.py,
run over every token at once instead of one query at a time.

## WHAT IT IS NOT

⚠⚠ **A HIT IS A PLACE TO LOOK, NEVER A CORRECTION.** This print genuinely
varies its spelling - the campaign has measured haerlighet/haarlighet in one
chapter, maechtig/maachtig across a gathering, and blaest/blaast as real
variants. It also sets outright compositor's errors that must be kept as set
(BUlken at Sirach 36:20). So the output is a WORK QUEUE for the image, and
"correct it toward the frequent form" is exactly the move section 4-0e of the
brief forbids.

⚠ Proper nouns are hapaxes by nature and flood the list; they are filtered by
the `--min-rival` gate (a name rarely has a frequent near-twin) and by dropping
anything whose rival differs only in its initial capital.

## THE RANKING

Candidates are sorted by the rival's frequency, because the bigger the gap
between "once" and "the print's habit", the more likely the once is a slip.
Edit distance is Levenshtein 1 (one insert, delete or substitution), computed
on the folded form so that a difference which is ONLY a diacritic is reported
separately - those belong to the ring/e adjudication workflow, not here.
"""
import argparse
import glob
import io
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")

# The four books kxii.se can check; everything else has no witness at all.
WITNESSED = {"Judith", "Wisdom of Solomon", "Sirach", "2 Maccabees"}

EXCLUDE_FILES = ("campaign", "precampaign", "scanhunt", "report", "prompts",
                 "navigation")

CHAPTER_RE = re.compile(r"^##\s+(.+?)\s+(\d+)\s*$")
VERSE_RE = re.compile(r"^(\d+)\s+(\S.*)$")
WORD_RE = re.compile(r"[A-Za-z\u00c0-\u024f\u017f]+")

# Diacritic-only differences are a separate workflow (the ring/e sheets).
FOLD = str.maketrans({"\u017f": "s"})


def defold(w):
    """Strip diacritics so a ring/umlaut-only difference can be spotted."""
    n = unicodedata.normalize("NFD", w)
    return "".join(c for c in n if not unicodedata.combining(c)).lower()


def load():
    """-> {book: [(chapter, verse, text)]}"""
    out = defaultdict(list)
    for f in sorted(glob.glob(str(RESEARCH / "karlxii_*.md"))):
        base = os.path.basename(f).lower()
        if ".bak" in base or any(k in base for k in EXCLUDE_FILES):
            continue
        book = ch = None
        for line in io.open(f, encoding="utf-8"):
            m = CHAPTER_RE.match(line)
            if m:
                book, ch = m.group(1).strip(), int(m.group(2))
                continue
            if line.startswith("#"):
                book = ch = None
                continue
            if book is None:
                continue
            m = VERSE_RE.match(line.rstrip("\n"))
            if m:
                out[book].append((ch, int(m.group(1)), m.group(2)))
    return out


def words(text):
    return [w.translate(FOLD) for w in WORD_RE.findall(text)]


def edits1(w, vocab):
    """Every vocab form at Levenshtein distance 1 from w."""
    hits = set()
    for v in vocab:
        if abs(len(v) - len(w)) > 1 or v == w:
            continue
        if len(v) == len(w):
            diff = sum(1 for a, b in zip(v, w) if a != b)
            if diff == 1:
                hits.add(v)
            continue
        long_, short = (v, w) if len(v) > len(w) else (w, v)
        i = j = 0
        skipped = False
        while i < len(long_) and j < len(short):
            if long_[i] == short[j]:
                i += 1
                j += 1
            elif skipped:
                break
            else:
                skipped = True
                i += 1
        else:
            hits.add(v)
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unwitnessed", action="store_true",
                    help="only the books kxii.se cannot check")
    ap.add_argument("--book", help="restrict to one book name")
    ap.add_argument("--min-rival", type=int, default=5,
                    help="rival form must occur at least this often (default 5)")
    ap.add_argument("--max-self", type=int, default=1,
                    help="candidate must occur at most this often (default 1)")
    args = ap.parse_args(argv)

    corpus = load()
    if not corpus:
        raise SystemExit("parsed ZERO verses - check the research directory")

    freq = Counter()
    for book, verses in corpus.items():
        for _, _, text in verses:
            freq.update(w.lower() for w in words(text))

    targets = sorted(corpus)
    if args.book:
        targets = [b for b in targets if b == args.book]
        if not targets:
            raise SystemExit("no book named %r; have: %s"
                             % (args.book, ", ".join(sorted(corpus))))
    elif args.unwitnessed:
        targets = [b for b in targets if b not in WITNESSED]

    vocab = {w for w, n in freq.items() if n >= args.min_rival}
    seen = set()
    rows = []
    for book in targets:
        for ch, v, text in corpus[book]:
            for w in words(text):
                lw = w.lower()
                if freq[lw] > args.max_self or lw in seen:
                    continue
                seen.add(lw)
                for rival in edits1(lw, vocab):
                    # An initial-capital-only difference is the ornament
                    # convention, not a misreading.
                    if defold(rival) == defold(lw) and rival != lw:
                        kind = "DIACRITIC"
                    elif len(rival) == len(lw):
                        kind = "swap"
                    else:
                        kind = "len"
                    rows.append((freq[rival], book, ch, v, w, rival, kind))

    rows.sort(key=lambda r: (-r[0], r[1], r[2], r[3]))
    print("books scanned: %s" % ", ".join(targets))
    print("corpus vocabulary: %d forms, %d verses"
          % (len(freq), sum(len(v) for v in corpus.values())))
    print("candidates (once-only forms with a frequent near-twin): %d\n" % len(rows))
    print("%-6s %-20s %-8s %-18s %-18s %s"
          % ("rival", "book", "ref", "ours (once)", "rival form", "kind"))
    print("-" * 92)
    for n, book, ch, v, w, rival, kind in rows:
        print("%-6d %-20s %-8s %-18s %-18s %s"
              % (n, book[:20], "%d:%d" % (ch, v), w, rival, kind))
    if rows:
        print("\nA HIT IS A PLACE TO LOOK. Settle every one on the page image.")
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
