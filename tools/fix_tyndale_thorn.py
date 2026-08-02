# -*- coding: utf-8 -*-
"""Expand thorn abbreviations in en_tyndale.json:  ye -> the,  yt -> that.

    python tools/fix_tyndale_thorn.py --report
    python tools/fix_tyndale_thorn.py

THE DEFECT
----------
Early modern printers used the thorn (þ) with a superscript letter as a
space-saver: þe = "the", þt = "that". In blackletter and in later digitizations
thorn is rendered as "y", so the asset carries "ye" and "yt". Readers see
"ye childern of heth" for "the children of Heth", and TTS says "yee".

⚠ BOTH FORMS ARE AMBIGUOUS, which is why this is separate from
fix_tyndale_contractions.py and far more conservative:
  · "ye" is ALSO the second-person plural pronoun — extremely common in
    Tyndale ("ye shall", "ye are"). Converting those to "the" would corrupt
    scripture, not repair it.
  · "yt" is USUALLY "that", but Gen 31:27 "broughte yt on the waye" is
    "brought THEE on the way".
So neither is converted wholesale. Each occurrence must pass a positional
test, and anything that fails is left exactly as it is. This under-corrects
on purpose: a leftover "ye" is a cosmetic blemish, a wrong one is a textual
error.

THE TESTS (both derived from the asset's own statistics)
  ye -> the   if the PRECEDING word is a preposition (a pronoun never follows
              "of"/"in"/"vpon"), or if the FOLLOWING word is one that occurs
              >=5x after the spelled-out "the" and is not a verb/auxiliary.
  yt -> that  if the FOLLOWING word can open a clause (pronoun, auxiliary,
              determiner). "yt on the waye" fails this and stays.
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ASSET = ROOT / "app/src/main/assets/bibles/en_tyndale.json"
BACKUP = Path("C:/Projects/Hexapla-releases/asset-backups/"
              "en_tyndale.json.prethorn.bak")

PREP = {"of", "in", "to", "into", "vnto", "unto", "vpon", "apon", "vppon",
        "from", "fro", "with", "wt", "by", "before", "after", "amonge",
        "among", "at", "out", "ouer", "over", "vnder", "under", "thorow",
        "thurgh", "through", "betwene", "agaynst", "agenst", "aboute",
        "vpo", "throughout", "besyde", "beside", "vntill", "till", "vp"}

# Words that follow the PRONOUN "ye", never the article. Kept deliberately
# broad: a false entry here only means a missed fix, never a wrong one.
VERBISH = {
    "shall", "shalbe", "shalt", "have", "haue", "hath", "are", "art", "is",
    "was", "were", "be", "bene", "not", "no", "maye", "may", "myght",
    "myghte", "must", "will", "wyll", "wolde", "shuld", "shulde", "should",
    "can", "ca", "cannot", "do", "doo", "doth", "dyd", "did", "knowe",
    "know", "se", "see", "sawe", "saye", "say", "sayde", "goo", "go",
    "come", "came", "eate", "eat", "drynke", "drinke", "take", "toke",
    "geve", "geue", "gave", "make", "made", "beare", "bere", "receave",
    "receyve", "praye", "pray", "aske", "axe", "thynke", "think", "beleve",
    "beleue", "loke", "look", "hyre", "heare", "here", "walke", "stonde",
    "stande", "sytte", "syt", "lyve", "live", "dye", "die", "feare",
    "judge", "iudge", "love", "loue", "hate", "kepe", "seke", "seeke",
    "fynde", "finde", "shewe", "tell", "speake", "call", "sende", "sent",
    "put", "bringe", "bring", "brought", "let", "loose", "bynde", "wepe",
    "reioyce", "remembre", "forgeve", "forgeue", "myn", "youre", "your",
    "them", "him", "her", "vs", "us", "me", "it", "yt", "he", "she", "they",
    "i", "thou", "we", "ye",
}

# Conjunctions/relatives/prepositions. "ye" before one of these is the pronoun
# at a clause boundary ("with ye and wyll blesse", "vnto ye that", "into ye
# which"), never the article.
FUNCTION = {
    "and", "or", "but", "that", "which", "whiche", "for", "so", "as", "then",
    "than", "therfore", "therefore", "wherfore", "when", "whan", "yf", "if",
    "because", "vnto", "unto", "to", "of", "in", "with", "wt", "from", "fro",
    "by", "vpon", "apon", "at", "into", "before", "after", "vp", "out",
    "also", "yet", "neither", "nether", "nor", "both", "shall", "there",
}

# What can legitimately open a clause after "yt" = "that".
CLAUSE_OPENERS = {
    "he", "she", "it", "they", "we", "i", "thou", "ye", "you", "the", "a",
    "an", "this", "these", "those", "his", "her", "their", "my", "thy",
    "youre", "your", "oure", "our", "is", "was", "were", "are", "am", "be",
    "shall", "shalbe", "shulde", "should", "wyll", "will", "wolde", "maye",
    "may", "myght", "myghte", "must", "hath", "have", "haue", "had", "hade",
    "doth", "do", "dyd", "did", "which", "whiche", "there", "god", "lorde",
    "man", "men", "no", "not", "all", "eny", "any", "every", "one", "when",
    "whan", "yf", "if", "as", "so", "thou", "whosoever", "he",
}

WORD = re.compile(r"[A-Za-z]+")


def apply_case(src, repl):
    if src.isupper():
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--samples", type=int, default=12)
    args = ap.parse_args()

    data = json.loads(ASSET.read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) else data

    # collocation stats: what follows the spelled-out "the"?
    the_next = Counter()
    for b in books:
        for ch in b.get("chapters", []):
            for v in ch:
                ws = [w.lower() for w in WORD.findall(v)]
                for i, w in enumerate(ws[:-1]):
                    if w == "the":
                        the_next[ws[i + 1]] += 1

    n_books = len(books)
    n_verses = sum(len(ch) for b in books for ch in b.get("chapters", []))
    stats = Counter()
    samples = {"ye": [], "yt": []}

    for b in books:
        for ci, ch in enumerate(b.get("chapters", [])):
            for vi, v in enumerate(ch):
                toks = list(WORD.finditer(v))
                lowers = [t.group(0).lower() for t in toks]
                out = v
                edits = []            # (start, end, replacement)
                for i, t in enumerate(toks):
                    lw = lowers[i]
                    prev = lowers[i - 1] if i else ""
                    nxt = lowers[i + 1] if i + 1 < len(lowers) else ""
                    if lw == "ye":
                        # ⚠ The FOLLOWING word decides. An earlier version
                        # treated a preceding preposition as sufficient on its
                        # own; that would have corrupted 21 genuine pronouns
                        # ("I wyll be with ye", "I saye vnto ye that", "wher of
                        # ye are now ashamed") — a pronoun follows "of"/"vnto"
                        # perfectly happily. A preposition before it is now
                        # only corroboration, never a licence.
                        # ⚠ A capitalised "Ye" opening a sentence is a VOCATIVE
                        # and must never become "the". All 10 such cases in the
                        # asset are direct address — "Ye men and brethren"
                        # (Acts 2:37), "Ye men of Israel" (Acts 2:22), "Ye lust
                        # and have not" (James 4:2) — and the noun test alone
                        # would have converted every one of them.
                        before = v[:t.start()].rstrip()
                        vocative = (t.group(0)[0].isupper()
                                    and (before == "" or before[-1] in ".:;!?—"))
                        ok = (not vocative and nxt and nxt not in VERBISH
                              and nxt not in FUNCTION
                              and the_next[nxt] >= 5)
                        if ok:
                            edits.append((t.start(), t.end(),
                                          apply_case(t.group(0), "the")))
                            stats["ye"] += 1
                            if len(samples["ye"]) < args.samples:
                                samples["ye"].append(
                                    f"{b['name']} {ci+1}:{vi+1}  {v[:100]}")
                        else:
                            stats["ye_left"] += 1
                    elif lw == "yt":
                        if nxt in CLAUSE_OPENERS:
                            edits.append((t.start(), t.end(),
                                          apply_case(t.group(0), "that")))
                            stats["yt"] += 1
                            if len(samples["yt"]) < args.samples:
                                samples["yt"].append(
                                    f"{b['name']} {ci+1}:{vi+1}  {v[:100]}")
                        else:
                            stats["yt_left"] += 1
                for s, e, r in reversed(edits):
                    out = out[:s] + r + out[e:]
                ch[vi] = out

    assert len(books) == n_books
    assert sum(len(ch) for b in books for ch in b.get("chapters", [])) == n_verses

    print(f"ye -> the : {stats['ye']:5}   left as pronoun: {stats['ye_left']}")
    print(f"yt -> that: {stats['yt']:5}   left alone     : {stats['yt_left']}")
    print(f"(verses {n_verses}, books {n_books} — unchanged)\n")
    for k in ("ye", "yt"):
        print(f"--- sample {k} conversions")
        for s in samples[k]:
            print("   ", s)
        print()

    if args.report:
        print("--report: nothing written.")
        return
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(ASSET, BACKUP)
        print(f"backup -> {BACKUP}")
    ASSET.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"wrote {ASSET}")


if __name__ == "__main__":
    main()
