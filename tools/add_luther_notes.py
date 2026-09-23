# -*- coding: utf-8 -*-
"""Attach Luther's own 1545 marginal notes to de_luther.json.

«Die gantze Heilige Schrifft mit den Anmerkungen des Reformators» — 4,716 notes,
~300 KB of Luther's German. They surface through the app's existing on-demand
mechanism: a `{lemma: note}` span is stripped from the verse at parse and shown
under "Translator's notes" (the KJV's 7,859 notes already use it). First
non-English translator's notes in the app.

⚠⚠ THE NOTES COME FROM A DIFFERENT TRANSCRIPTION THAN THE SHIPPED TEXT.
Our de_luther.json descends from the Zefania 2009 module in MODERNISED spelling
(«Und GOtt nannte das Trockene Erde»). The notes live only in the 2012 "Letzte
Hand" module, in ORIGINAL 1545 orthography («Vnd Gott nennet das trocken /
Erde»). Same edition, same verse division, different spelling system — so a
note can be placed by coordinate, but coordinate trust alone is not enough:
that is how a note ends up on the wrong verse and reads as scripture.
Every placement is therefore gated on the two verse texts matching after
orthographic normalisation, and any verse that fails the gate is skipped and
counted rather than guessed at.

⚠ The LH module also carries the APOCRYPHA (35,764 verses vs our 31,170).
Books beyond the 66-book canon are ignored here; the apocrypha are a separate,
already-approved project (see docs/TRANSLATIONS.md).

    python tools/add_luther_notes.py --dry-run
    python tools/add_luther_notes.py
"""
import argparse
import io
import json
import re
import shutil
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
ASSET = HERE.parent / "app/src/main/assets/bibles/de_luther.json"
LH = Path(r"C:/Projects/Hexapla-releases/SF_2012-08-14_DEUTSCH_LUT_1545_LH_"
          r"(LUTHER 1545 (LETZTE HAND)).xml")
BACKUP = Path(r"C:/Projects/Hexapla-releases/asset-backups/de_luther.json.prenotes.bak")

# Orthographic normalisation, 1545 -> modern, for COMPARISON ONLY. Never applied
# to text that ships. These are the systematic differences between the two
# transcriptions, read off the mismatches: v/u and j/i are the same letters in
# the older spelling, ß/ss interchange, and doubled consonants vary freely
# («funffzehen» / «fünfzehn»).
def norm(s):
    s = s.lower()
    s = (s.replace("ä", "a").replace("ö", "o").replace("ü", "u")
           .replace("ß", "s").replace("v", "u").replace("j", "i")
           .replace("y", "i"))
    s = re.sub(r"[^a-z ]+", " ", s)
    s = re.sub(r"(.)\1+", r"\1", s)      # collapse doubled letters
    return re.sub(r"\s+", " ", s).strip()


def parse_lh():
    """(book, chapter, verse) -> (verse text without notes, [notes])."""
    t = io.open(LH, encoding="utf-8", errors="replace").read()
    out = {}
    for bn, body in re.findall(
            r'<BIBLEBOOK[^>]*bnumber="(\d+)"[^>]*>(.*?)</BIBLEBOOK>', t, re.S):
        b = int(bn)
        if b > 66:                       # canon only; apocrypha handled elsewhere
            continue
        for cn, cbody in re.findall(
                r'<CHAPTER[^>]*cnumber="(\d+)"[^>]*>(.*?)</CHAPTER>', body, re.S):
            for vn, vbody in re.findall(
                    r'<VERS[^>]*vnumber="(\d+)"[^>]*>(.*?)</VERS>', cbody, re.S):
                notes = [re.sub(r"<[^>]+>", "", n).strip()
                         for n in re.findall(r"<NOTE[^>]*>(.*?)</NOTE>", vbody, re.S)]
                txt = re.sub(r"<NOTE[^>]*>.*?</NOTE>", "", vbody, flags=re.S)
                txt = re.sub(r"<[^>]+>", "", txt)
                out[(b, int(cn), int(vn))] = (
                    re.sub(r"\s+", " ", txt).strip(),
                    [re.sub(r"\s+", " ", n) for n in notes if n.strip()])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--gate", type=float, default=0.72,
                    help="min normalised similarity to accept a placement")
    args = ap.parse_args()

    lh = parse_lh()
    bible = json.load(io.open(ASSET, encoding="utf-8"))
    total_notes = sum(len(v[1]) for v in lh.values())
    print(f"LH canon verses: {len(lh)}   notes in canon: {total_notes}")

    placed = skipped = missing = already = 0
    ratios = []
    examples = []
    for (b, c, v), (lhtext, notes) in sorted(lh.items()):
        if not notes:
            continue
        bi, ci, vi = b - 1, c - 1, v - 1
        if bi >= len(bible) or ci >= len(bible[bi]["chapters"]):
            missing += len(notes); continue
        ch = bible[bi]["chapters"][ci]
        if vi >= len(ch):
            missing += len(notes); continue
        mine = ch[vi]
        if "{" in mine and ":" in mine:
            already += len(notes)
        r = SequenceMatcher(None, norm(mine)[:160], norm(lhtext)[:160]).ratio()
        ratios.append(r)
        if r < args.gate:
            skipped += len(notes)
            if len(examples) < 5:
                examples.append((b, c, v, round(r, 2), mine[:60], lhtext[:60]))
            continue
        # Append as the app's on-demand note spans. "Anm." = Anmerkung, and it
        # is what a German reader expects to see labelling a marginal note.
        add = "".join(" {Anm.: %s}" % n.replace("{", "(").replace("}", ")")
                      for n in notes)
        ch[vi] = mine + add
        placed += len(notes)

    ratios.sort()
    print(f"placed  : {placed}")
    print(f"skipped : {skipped}  (below the {args.gate} gate)")
    print(f"missing : {missing}  (coordinate absent from our asset)")
    print(f"median normalised similarity: "
          f"{ratios[len(ratios)//2]:.2f}" if ratios else "n/a")
    for e in examples:
        print("   GATE-FAIL", e)

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy(ASSET, BACKUP)
    json.dump(bible, io.open(ASSET, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"\nwrote {ASSET}\nbackup {BACKUP}")


if __name__ == "__main__":
    main()
