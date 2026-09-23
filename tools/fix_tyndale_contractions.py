# -*- coding: utf-8 -*-
"""Expand dropped nasal-overline contractions in en_tyndale.json.

    python tools/fix_tyndale_contractions.py --report     # diff only, no write
    python tools/fix_tyndale_contractions.py              # apply

THE DEFECT
----------
Early modern printers wrote a nasal (n/m) as an overline over the preceding
vowel to save space: "ãd" = and, "mã" = man, "whã" = when, "wᵗ" = with. Our
digitization dropped the MARK but kept the bare letters, so the asset carries
"ad", "ma", "whe" — which is neither the print's symbol nor its meaning. A
letter was silently deleted. Readers see "sette hymselfe ad his seruantes",
and TTS reads it aloud as written.

Expanding is the standard treatment for a reading edition, and it restores what
the print means rather than altering it. Owner approved 2026-08-02.

WHY THIS TABLE IS HAND-CURATED AND MUST STAY THAT WAY
-----------------------------------------------------
Every automated rule tried on this produced corruption:
  · "insert n/m where it yields a known word"   -> me->men, 1483 times
  · "...where the bare form is not in a lexicon" -> toke->token, eate->eaten
    (Tyndale's own spellings are in no modern lexicon)
  · "...where the expansion is >=2x more frequent" -> best of the three, but
    still proposed noe->none (Noe is NOAH), eve->even (Eve is a PERSON),
    set->sent, may->many, chose->chosen, spoke->spoken, and
    vnderstode->vnderstonde (understood -> understand, a tense change).
Only forms that are not words in ANY reading are listed below, each verified in
context. When in doubt it was left out: this file under-corrects on purpose.

DELIBERATELY EXCLUDED, with reasons (do not "complete" these):
  noe/eve/eue/Ada  proper names collide (Noah, Eve, Adah of Gen 4:19)
  set may chose spoke lade lode hade wet  ordinary words in their own right
  vnderstode       expanding changes the tense
  heve heaue       "heave offering" is real (Num 18:24 "which they heve")
  ye yt            thorn forms; "ye" is BOTH "the" and the pronoun "ye"
  sone maner comaunded  spelling variants, not contractions - harmless as-is
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
              "en_tyndale.json.precontractions.bak")

# bare form -> expansion. Lower-case keys; case of the original is preserved.
EXPAND = {
    # conjunction / prepositions / pronouns
    "ad": "and", "fro": "from", "hi": "him", "whe": "when", "wha": "whan",
    "tha": "than", "ca": "can", "apo": "apon", "vpo": "vpon", "vppo": "vppon",
    "amoge": "amonge", "thece": "thence", "wt": "with",
    # nouns / names whose bare form is not a word
    "ma": "man", "woma": "woman", "childre": "children", "chyldre": "chyldren",
    "brethre": "brethren", "abraha": "abraham", "aaro": "aaron",
    "servaut": "servaunt", "servautes": "servauntes",
    "cogregacion": "congregacion", "habitacio": "habitacion",
    "possessio": "possession", "natios": "nations", "regio": "region",
    "egiptias": "egiptians", "getyls": "gentyls", "labes": "lambes",
    "hudred": "hundred", "raymet": "rayment", "testamet": "testament",
    "iudgemet": "iudgement", "attonemet": "attonement", "tepest": "tempest",
    # ⚠ EXPANSIONS MUST USE THE ASSET'S OWN SPELLING, not modern English.
    # Gate 1 caught "danger" (the asset writes "daunger"); the same check is
    # why these read audyence/grounde/congregacio-n rather than the modern
    # forms. Verified by prefix search over the asset's vocabulary.
    "dager": "daunger", "audyece": "audyence", "groude": "grounde",
    "tet": "tent", "loge": "longe", "roude": "rounde", "foude": "founde",
    "congregacio": "congregacion", "congregacios": "congregacions",
    "possessios": "possessions", "remembrauce": "remembraunce",
    # verbs / participles
    "writte": "written", "bega": "began", "cosumed": "consumed",
    "remebred": "remembred", "comauded": "comaunded", "heceforth": "henceforth",
    "prudet": "prudent",
}


def clean_for_scan(v):
    return v


def apply_case(src, repl):
    """Preserve the original capitalisation pattern."""
    if src.isupper():
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="diff only, no write")
    args = ap.parse_args()

    raw = ASSET.read_text(encoding="utf-8")
    data = json.loads(raw)
    books = data["books"] if isinstance(data, dict) else data

    # ── gate 1: every bare form must actually be present, and every expansion
    # must already occur in the asset. A typo'd table entry fails here rather
    # than silently doing nothing (or inventing a word).
    freq = Counter()
    for b in books:
        for ch in b.get("chapters", []):
            for v in ch:
                for w in re.findall(r"[A-Za-z]+", v):
                    freq[w.lower()] += 1
    missing = [k for k in EXPAND if freq[k] == 0]
    unseen = [v for v in EXPAND.values() if freq[v.lower()] == 0]
    if missing:
        sys.exit(f"table lists forms absent from the asset: {missing}")
    if unseen:
        sys.exit(f"table expands to forms the asset never uses: {unseen}")

    # ── gate 2: "fro" is a real word ONLY in the idiom "to and fro". Refuse if
    # that appears, since expanding it there would produce "to and from".
    # ⚠ An earlier version of this gate matched bare "and fro" and fired on
    # Genesis 4:14. Inspecting all 12 hits showed every one is "and FROM"
    # ("and fro thy syghte must I hyde my selfe", "fro Galile and fro Iurie") —
    # the conjunction followed by the contraction, not the idiom. The gate was
    # over-broad, not the table. Checking the idiom is the correct test.
    for b in books:
        for ci, ch in enumerate(b.get("chapters", [])):
            for vi, v in enumerate(ch):
                if re.search(r"\bto\s+and\s+fro\b", v, re.I):
                    sys.exit(f"idiom 'to and fro' at {b['name']} {ci+1}:{vi+1} — "
                             f"remove 'fro' from the table and re-run")

    pattern = re.compile(r"\b(" + "|".join(sorted(EXPAND, key=len, reverse=True))
                         + r")\b", re.I)
    counts = Counter()
    samples = {}
    n_books = len(books)
    n_verses = sum(len(ch) for b in books for ch in b.get("chapters", []))

    for b in books:
        for ci, ch in enumerate(b.get("chapters", [])):
            for vi, v in enumerate(ch):
                def sub(m):
                    src = m.group(1)
                    repl = apply_case(src, EXPAND[src.lower()])
                    counts[src.lower()] += 1
                    samples.setdefault(src.lower(),
                                       f"{b['name']} {ci+1}:{vi+1}  {v[:95]}")
                    return repl
                new = pattern.sub(sub, v)
                if new != v:
                    ch[vi] = new

    # ── gate 3: structure must be untouched (no versification change, so
    # bookmarks/notes/highlights are unaffected).
    assert len(books) == n_books, "book count changed"
    assert sum(len(ch) for b in books for ch in b.get("chapters", [])) == n_verses, \
        "verse count changed"

    total = sum(counts.values())
    print(f"{total} expansions across {len(counts)} distinct forms "
          f"({n_verses} verses, {n_books} books — both unchanged)\n")
    for w, n in counts.most_common():
        print(f"  {n:6}  {w:14} -> {EXPAND[w]}")
        print(f"          {samples[w][:105]}")

    if args.report:
        print("\n--report: nothing written.")
        return
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(ASSET, BACKUP)
        print(f"\nbackup -> {BACKUP}")
    else:
        print(f"\nbackup already exists, kept: {BACKUP}")
    ASSET.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"wrote {ASSET}")


if __name__ == "__main__":
    main()
