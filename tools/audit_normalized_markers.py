# -*- coding: utf-8 -*-
"""Find chunk reports that SILENTLY NORMALIZED a defective verse numeral.

Owner ruling 2026-08-08: defective numerals are recorded AS PRINTED, in the
marker stream. A normalized marker is invisible to every existing check —
the chapter scans COMPLETE — so the only way to find one is to compare each
report's own FLAG PROSE against its own MARKER STREAM.

    prose flags a numeral defect in chapter N  +  chapter N scans contiguous
        =>  SUSPECT: the marker was normalized away

The inverse is also reported (marker anomaly with no prose) as UNDOCUMENTED.

⚠ No KJV counts are needed here. The question is not "does the chapter have
the right number of verses" but "is the marker run 1..N contiguous" — which is
exactly what normalization restores. So this works for multi-book files too.

⚠ Reuses scan_markers.scan(). Do NOT re-implement the commentary filter — the
campaign file records two separate false-alarm incidents caused by inline
copies of it.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(r"C:/Projects/Hexapla-releases/research")
sys.path.insert(0, str(HERE))

# ⚠ scan_markers.py runs its CLI at module level off sys.argv, so a plain
# import would re-scan our own arguments (and crash on a book-less run).
# Blank argv across the import, then restore.
_argv = sys.argv[:]
sys.argv = ["scan_markers"]
import scan_markers as sm  # noqa: E402
sys.argv = _argv

# ⚠ FIRST ATTEMPT MATCHED "marker|defect|twice" AND RETURNED 203 CHAPTERS,
# almost all of them prose asserting the OPPOSITE ("CH25 CHECK: markers
# extracted 1..18 in order — PASS", "No defect at Ps 77:9", "Retracted — no
# defect here"). That is campaign trap #1: a verification artifact reads
# exactly like a defect. Require a POSITIVE claim that the print shows the
# wrong glyph, then subtract every negation/retraction.
DEFECT_WORDS = re.compile(
    r"print[s]?\s*«?[۰-۹٠-٩]+»?\s*(?:instead of|for|where|in place of)"
    r"|«[۰-۹٠-٩]+»\s*(?:instead of|for|in place of)\s*«?[۰-۹٠-٩]+"
    r"|tens digit"
    r"|numeral\s+(?:is\s+)?(?:omitted|missing|absent|dropped)"
    r"|«[۰-۹٠-٩]+»\s*(?:printed\s*)?twice"
    r"|prints?\b[^.]{0,40}\btwice"
    r"|skips?\b[^.]{0,25}«[۰-۹٠-٩]+»"
    r"|never appears as a printed glyph"
    r"|bare[- ]stroke numeral"
    r"|bare «?[۰-۹٠-٩]+»?"
    # ⚠ ADDED 2026-08-08 after a chunk agent showed these were MISSED. Its
    # reports write "⚠ GENUINE PRINT DEFECT — v9's numeral prints as «۱», not
    # «۹»" — a positive defect claim this detector scored as no-evidence, i.e.
    # a FALSE NEGATIVE, the direction that actually costs something.
    r"|«[۰-۹٠-٩]+»\s*,?\s*not\s*«[۰-۹٠-٩]+»"
    r"|prints? as\s*«?[۰-۹٠-٩]+»?"
    r"|genuine print defect",
    re.I)

# A line asserting there is NO defect, or withdrawing an earlier claim.
# ⚠ A BARE `\bgenuine\b` USED TO BE HERE AND WAS A FALSE-NEGATIVE MACHINE.
# "genuine" appears on BOTH sides of this distinction: "came back genuine"
# (retraction — the glyph really was a ۹) versus "GENUINE PRINT DEFECT"
# (assertion — the print really is wrong). Killing every line containing the
# word discarded real evidence. Match the retraction PHRASES, never the word.
NEGATION = re.compile(
    r"\bno defect\b|\bnot a defect\b|retract|overturn|withdraw|false positive"
    r"|\bPASS\b|no gaps|no skipped|no duplicat|correctly numbered"
    r"|came back genuine|is genuine|are genuine|genuine «?[۰-۹٠-٩]"
    r"|resolved to|not a print defect|innocent",
    re.I)
# A chapter:verse reference, either «34:18» or «ch 34».
REF = re.compile(r"\b(\d{1,3}):(\d{1,3})\b")
CHREF = re.compile(r"\bch(?:apter)?\.?\s*(\d{1,3})\b", re.I)


def prose_flags(path):
    """chapter -> list of evidence lines, from ENGLISH commentary only."""
    out = {}
    for raw in io.open(path, encoding="utf-8"):
        line = raw.strip()
        if not line or not sm.is_commentary(raw):
            continue          # scripture lines are not evidence about scripture
        if not DEFECT_WORDS.search(line):
            continue
        if NEGATION.search(line):
            continue          # the line says there is NO defect — not evidence
        chs = {int(m.group(1)) for m in REF.finditer(line)}
        chs |= {int(m.group(1)) for m in CHREF.finditer(line)}
        for ch in chs:
            out.setdefault(ch, []).append(line[:150])
    return out


def contiguous(got):
    return got == list(range(1, len(got) + 1))


def main(paths):
    suspects = undocumented = 0
    for p in paths:
        order, chapters = sm.scan(p)
        if not order:
            continue
        flags = prose_flags(p)
        rows = []
        for ch in order:
            got = chapters[ch]
            if not got:
                continue
            ok = contiguous(got)
            flagged = ch in flags
            if flagged and ok:
                rows.append(("SUSPECT-NORMALIZED", ch, flags[ch][:2]))
            elif not ok and not flagged:
                rows.append(("UNDOCUMENTED-ANOMALY", ch, []))
        if rows:
            print("=" * 72)
            print(Path(p).name)
            for kind, ch, ev in rows:
                print(f"  ch {ch:>3}  {kind}")
                for e in ev:
                    print(f"        | {e}")
                if kind == "SUSPECT-NORMALIZED":
                    suspects += 1
                else:
                    undocumented += 1
    print("=" * 72)
    print(f"SUSPECT-NORMALIZED chapters : {suspects}")
    print(f"UNDOCUMENTED anomalies      : {undocumented}")


if __name__ == "__main__":
    main(sys.argv[1:])
