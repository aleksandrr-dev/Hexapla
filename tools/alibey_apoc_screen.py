# -*- coding: utf-8 -*-
"""Screen the Ali Bey 1665 apocrypha event stream for editorial matter left
inside verse text - 0 tokens.

    python tools/alibey_apoc_screen.py [--events <events.jsonl>]

Flags, per «v» event: an editor's word or mark (bkz, ayet, bölüm, çeviri, «[»,
«(», önemli not, luther) and a doubled two-word run («a b a b», a catchword
repeated across a facsimile page break). Prints each hit and the counts;
rc 0 = none, rc 1 = hits. A hit is a question, not a verdict: read it.
Known-bad controls live in alibey_apoc_extract.py (HEXAPLA_ALIBEY_*=1 must
raise this screen's count).
"""
import argparse
import json
import re
import sys

# Word-initial: «vilayet», «çevirip» (a verb) are text, not editor's words.
EDITORIAL = re.compile(r"(?i)\bbkz|\bayet|\bbölüm|\bçeviri(?!p)|\[|\(|önemli not|luther")
DOUBLED = re.compile(r"\b(\S+ \S+) \1\b")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="C:/Projects/Hexapla-releases/_work/alibey_apoc/events.jsonl")
    a = ap.parse_args()
    ev = [json.loads(l) for l in open(a.events, encoding="utf-8")]
    verses = [e for e in ev if e["k"] == "v"]
    if not verses:
        print("⛔ no verse events - the screen cannot run")
        return 2
    n_ed = n_dup = 0
    for e in verses:
        for rx, tag in ((EDITORIAL, "editorial"), (DOUBLED, "doubled")):
            for m in rx.finditer(e["t"]):
                s = e["t"]
                print(f"  {tag:9} p{e['p']} v{e['n']}: …{s[max(0, m.start() - 30):m.end() + 30]}…")
                if tag == "editorial":
                    n_ed += 1
                else:
                    n_dup += 1
    # The event mix is half the screen: YSORT/NOSIDE leave verse text clean but
    # raise stray/note or drop catchwords - compare these against the good run.
    kinds = {}
    for e in ev:
        kinds[e["k"]] = kinds.get(e["k"], 0) + 1
    print("events: " + ", ".join(f"{k} {kinds.get(k, 0)}" for k in ("stray", "note", "catch", "head", "colophon")))
    print(f"{len(verses)} verses screened: {n_ed} editorial, {n_dup} doubled")
    return 1 if n_ed + n_dup else 0


if __name__ == "__main__":
    sys.exit(main())
