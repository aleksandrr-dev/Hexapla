# -*- coding: utf-8 -*-
"""Is a gate flag explained by the PRINTED text? 0 model tokens.

    python tools/qa_text_explained.py --set ylt --queue _work/ylt_lexicon_rr_FAIL_needs_ear.txt
    python tools/qa_text_explained.py --set ylt --verse 22 23 21     # book chapter verse
    python tools/qa_text_explained.py --validate

## Why this exists

⚠⚠ **A GATE FLAG THAT THE PRINTED TEXT EXPLAINS CAN NEVER PASS AND CAN NEVER BE
REPAIRED BY REDRAWING.** Measured 2026-09-05: `repair_verses.py` re-drew Isaiah
24:21 three times and every draw «failed». It always will — the gate fires on
«on the land on the land», which is scripture. The verse has no defect of any
class; the session that queued it had been told the text printed the phrase
once, and nobody checked.

Run this over any FAIL queue BEFORE queueing draws.

## ⛔ WHAT THIS DOES NOT DO

It does **not clear a hit**. Text evidence cannot tell «the ASR misheard A as B»
from «the TTS SPOKE B where the text has A» — established by ear on ylt 0/12 v14
(«westward» for «and eastward, and westward»). Only an ear removes a verse from
a queue. This tool only separates *redrawing is futile* from *redrawing might
work*, so an ear is not spent on the futile ones.

## ⛔ CHECK THE CHECKER

`--validate` fires on Isaiah 24:21 (printed tail repetition) and stays silent on
1 Kings 17:4 (ordinary prose), and EXITS NON-ZERO if either control is wrong —
a screen that cannot be shown to work must not have its verdicts used.
⚠ Two bugs found in this very check on 2026-09-06, both under-reporting, i.e.
both in the direction that licenses a futile redraw:
  · `[a-z']+` captured the closing quote of «…the God.'» as its own token, so
    the final word was `'` and every tail comparison failed. 1 Kings 18:39 —
    «Jehovah, He is the God, Jehovah, He is the God.» — was reported clean.
  · Returning only the LONGEST repeated n-gram missed a shorter one that ends
    the verse. Ezekiel 48:17 ends «fifty and two hundred» for the fourth time.
Before the fix it found 0 of 11 text-explained; after, 4 of 11.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ASSETS = {
    "ylt": "C:/Projects/Hexapla/app/src/main/assets/bibles/en_ylt.json",
    "kjv": "C:/Projects/Hexapla/app/src/main/assets/bibles/en_kjv.json",
}
NMAX = 8


def load(set_key):
    data = json.loads(Path(ASSETS[set_key]).read_text(encoding="utf-8"))
    return data["books"] if isinstance(data, dict) and "books" in data else data


def bname(books, bi):
    b = books[bi]
    return b.get("name", f"book{bi}") if isinstance(b, dict) else f"book{bi}"


def vtext(books, bi, ci, v):
    b = books[bi]
    chs = b["chapters"] if isinstance(b, dict) else b
    ch = chs[ci]
    return ch[v - 1] if 0 <= v - 1 < len(ch) else ""


def words(text):
    # ⛔ Drop apostrophe-only tokens — see the bug note in the docstring.
    return [w for w in re.findall(r"[a-z']+", text.lower()) if w.strip("'")]


# Words too weak to make a doubling meaningful on their own. Kept deliberately
# short: every entry here is a word we REFUSE to excuse, i.e. it pushes a verse
# back towards the ear, which is the safe direction.
WEAK = {"the", "and", "of", "to", "a", "in", "is", "it", "he", "his", "her",
        "him", "they", "them", "that", "this", "for", "on", "unto", "with",
        "not", "but", "as", "be", "are", "was", "who", "all", "i", "my",
        "thy", "thee", "thou", "you", "your", "we", "us", "so", "up", "out"}
# Connectors thin enough that «X <c> X» still reads as one doubled phrase.
JOINERS = {"and", "or", "of", "to", "a", "the", "even", "unto"}


def local_tail_double(w):
    """Does the verse END in a doubling the PRINT already contains?

    Two shapes, both local on purpose:
      · «Rabbi, Rabbi.» / «Aha, aha.» / «No, no?»   -> w[-n:] == w[-2n:-n]
      · «generation and generation»                 -> w[-1] == w[-3], thin joiner

    ⚠ Locality is the whole safeguard. «tail word appears somewhere earlier in
    the verse» would excuse almost any verse and is NOT what a re-spoken tail
    looks like.
    """
    if len(w) < 3:
        return False
    # adjacent doubling of the last n words, n = 1..4
    for n in range(1, min(4, len(w) // 2) + 1):
        a, b = w[-n:], w[-2 * n:-n]
        if a != b:
            continue
        if n == 1 and (len(a[0]) < 3 or a[0] in WEAK):
            continue          # «…and and» is a typo, not a printed doubling
        return True
    # «X <joiner> X» straddling one thin word
    if len(w) >= 3 and w[-1] == w[-3] and w[-2] in JOINERS:
        if len(w[-1]) >= 3 and w[-1] not in WEAK:
            return True
    return False


def analyse(text):
    """-> (tail_repeats, longest_repeated_gram, count, density)."""
    w = words(text)
    if len(w) < 4:
        return False, "", 0, 0.0
    tail = False
    for n in range(2, min(NMAX, len(w) // 2) + 1):
        if w[-n:] in [w[i:i + n] for i in range(len(w) - n)]:
            tail = True
            break
    # ⛔ A SINGLE-WORD tail doubling was structurally invisible until 2026-09-06:
    # the loop above starts at n=2, so «…by men, Rabbi, Rabbi.» could never be
    # recognised — the bigram (rabbi, rabbi) occurs ONLY at the tail. Matthew
    # 23:7, Psalms 40:15 «Aha, aha.», II Kings 3:16 «ditches—ditches» and
    # Psalms 61:6 «generation and generation» all reached the ear queue that way,
    # every one of them a gate flag firing on scripture.
    #
    # ⚠ The n>=2 rule above asks whether the tail recurs ANYWHERE earlier. That
    # is far too loose at n=1 — a verse ending in «the» would be excused. So the
    # single-word rule is LOCAL and CONTENTFUL instead: the repeat must sit
    # within two tokens of the tail, and the word must not be a short function
    # word. A false TEXT-EXPLAINED discards a real defect, so this stays tight.
    if not tail:
        tail = local_tail_double(w)
    gram, cnt = "", 0
    for n in range(min(NMAX, len(w) // 2), 1, -1):
        grams = [tuple(w[i:i + n]) for i in range(len(w) - n + 1)]
        for g in set(grams):
            if grams.count(g) > 1:
                gram, cnt = " ".join(g), grams.count(g)
                break
        if gram:
            break
    # density: share of tokens sitting inside SOME repeated bigram — the signal
    # for a verse like Isaiah 28:10 that is drenched in repetition without its
    # exact tail recurring.
    bg = [tuple(w[i:i + 2]) for i in range(len(w) - 1)]
    rep = {g for g in set(bg) if bg.count(g) > 1}
    covered = set()
    for i, g in enumerate(bg):
        if g in rep:
            covered.update((i, i + 1))
    return tail, gram, cnt, len(covered) / len(w)


def verdict(tail, density):
    if tail:
        return "TEXT-EXPLAINED — do NOT redraw, the gate is firing on scripture"
    if density >= 0.34:
        return ("HEAVILY REPETITIVE in print (%.0f%% of words) — a redraw is "
                "unlikely to pass; send to an ear before spending GPU" % (density * 100))
    return "not explained by the print — needs an EAR (text cannot clear it)"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="ylt", choices=sorted(ASSETS))
    ap.add_argument("--queue", help="file of `B C vN` or `B C n,n` lines")
    ap.add_argument("--verse", nargs=3, type=int, metavar=("BOOK", "CHAPTER", "VERSE"),
                    help="0-based book and chapter, 1-based verse")
    ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    books = load(a.set)

    if a.validate:
        names = {bname(books, i): i for i in range(len(books))}
        ctl = [(("Isaiah", 23, 21), True), (("I Kings", 16, 4), False),
               # single-word tail doublings — invisible before 2026-09-06
               (("Matthew", 22, 7), True),      # «…by men, Rabbi, Rabbi.»
               (("Psalms", 39, 15), True),      # «…saying to me, `Aha, aha.'»
               (("II Kings", 2, 16), True),     # «…this valley ditches—ditches;»
               (("Psalms", 60, 6), True),       # «…as generation and generation.»
               # …and ordinary prose that must NOT be excused. Genesis 1:1 ends
               # «the heavens and the earth» — a weak-word tail that a looser
               # rule would have swallowed.
               (("Genesis", 0, 1), False),
               (("Genesis", 0, 3), False)]
        ok = True
        for (bn, ci, v), want in ctl:
            if bn not in names:
                sys.exit(f"⛔ control book {bn!r} not in the {a.set} asset")
            got = analyse(vtext(books, names[bn], ci, v))[0]
            print(f"CONTROL {bn} {ci + 1}:{v}  tail-repeat={got}  expected={want}  "
                  f"{'ok' if got == want else '⛔ MISMATCH'}")
            ok &= got == want
        if not ok:
            sys.exit("⛔ controls failed — do not use this screen's verdicts.")
        print("✅ controls pass")
        return

    sites = []
    if a.verse:
        sites = [tuple(a.verse)]
    elif a.queue:
        for ln in Path(a.queue).read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*(\d+)\s+(\d+)\s+v?([\d, ]+)\s*$", ln)
            if m:
                for v in m.group(3).split(","):
                    if v.strip():
                        sites.append((int(m.group(1)), int(m.group(2)), int(v)))
    else:
        sys.exit("give --queue, --verse or --validate")
    if not sites:
        sys.exit("⛔ nothing parsed from the queue — that is a FAILURE, not an "
                 "empty result. Check the line format.")

    n_ex = 0
    for bi, ci, v in sites:
        t = vtext(books, bi, ci, v)
        tail, gram, cnt, dens = analyse(t)
        n_ex += tail
        print(f"{bname(books, bi)} {ci + 1}:{v}   [{bi} {ci} v{v}]")
        print(f"   {verdict(tail, dens)}")
        if gram:
            print(f"   repeated {cnt}x: «{gram}»"
                  + ("  (and the verse ENDS with it)" if tail else ""))
        print(f"   text: {t[:200]}")
        print()
    print(f"{n_ex} of {len(sites)} are TEXT-EXPLAINED — redrawing those is futile.")
    print("⛔ The rest are NOT cleared. Only an ear can clear a gate flag.")


if __name__ == "__main__":
    main()
