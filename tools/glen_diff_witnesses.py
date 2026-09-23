# -*- coding: utf-8 -*-
"""Diff two independent transcriptions of the same Glen chapters.

WHY. The campaign's quality method is BLIND RE-DERIVATION: a second agent
transcribes the same pages without ever seeing the first's answer, and the
disagreements are the signal. Isaiah 36-38 produced 41 real disagreements that
way. This script does the mechanical comparison so the human/orchestrator only
has to adjudicate what actually differs.

    python tools/glen_diff_witnesses.py --first glen_isaiah_1-17.md \
        --second glen_isaiah_spotcheck_2026-08-07.md --chapters 5,14

⚠ NORMALIZE BEFORE COMPARING, OR THE RESULT IS MEANINGLESS. The two witnesses
record vowel diacritics, ezafe marks and ZWNJ inconsistently — a raw compare of
the 2026-08-07 Isaiah sample reported 70% "disagreement", of which the great
majority was orthography. After stripping harakat/tatweel/ZWNJ and folding
Arabic yeh/kaf to Persian, the real figure was 46%, and the substantive cases
rose to the top of the sorted list where they belong.

⚠ A LOW RATIO IS A CANDIDATE, NOT A VERDICT. Both witnesses make mistakes: in
the first adjudicated sample the FIRST pass had dropped a clause at Isa 22:20
and inverted word order at 41:8, while the SECOND had its own smaller slips.
Every disagreement must be settled by rendering the page and reading it — never
by preferring the newer reading, and never by preferring whichever matches the
KJV (this print's own defects are real and must survive).
"""
import argparse
import difflib
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path("C:/Projects/Hexapla-releases/research")
_D = "۰۱۲۳۴۵۶۷۸۹"
# harakat, superscript alef, tatweel, ZWNJ/ZWJ — recorded inconsistently by
# different witnesses and never meaning-bearing for this comparison.
_DIA = "".join(chr(c) for c in list(range(0x064B, 0x0653)) + [0x0654, 0x0655,
                                                             0x0670, 0x0640,
                                                             0x200C, 0x200D])


def _num(s):
    return int("".join(str(_D.index(c)) for c in s))


def norm(s):
    # ⚠ DO NOT STRIP FROM A LATIN CHARACTER TO END OF LINE. That was the first
    # version, and a single stray Latin letter INSIDE a Persian word — the
    # ASCII-leak defect class, e.g. «میiنمائید» in the Isaiah re-witness —
    # silently truncated the whole verse, which then showed up at the top of
    # the disagreement list as if the witnesses differed wildly. Drop lines
    # that are genuinely English prose, then delete stray Latin characters.
    kept = []
    for line in s.splitlines():
        lat = len(re.findall(r"[A-Za-z]", line))
        per = len(re.findall(r"[؀-ۿ]", line))
        if per == 0 and lat > 0:
            continue                              # English commentary line
        if lat > per:
            continue                              # predominantly English
        kept.append(line)
    s = "\n".join(kept)
    s = re.sub(r"[A-Za-z]+", "", s)               # stray leaks inside words
    s = unicodedata.normalize("NFC", s)
    s = "".join(ch for ch in s if ch not in _DIA)
    s = (s.replace("ي", "ی").replace("ك", "ک")
          .replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
          .replace("ۀ", "ه").replace("ة", "ه"))
    return " ".join(re.sub(r"[^؀-ۿ ]", " ", s).split())


def chapters(path, chap_patterns):
    """{chapter: {verse: text}} — tolerant of the campaign's heading styles."""
    text = Path(path).read_text(encoding="utf-8")
    for pat in chap_patterns:
        secs = re.split(pat, text)
        if len(secs) < 3:
            continue
        out = {}
        for i in range(1, len(secs), 2):
            ch = int(secs[i])
            # ⚠ CUT AT THE NEXT SUB-HEADING. Each chapter is followed by a
            # «### Flags ch7» style section, and its prose quotes Persian — so
            # the capture for the chapter's LAST verse swallowed the commentary
            # and reported a huge fake disagreement (Isaiah 7:25 came out as
            # «عمانوئیل» vs «خود خداوند خود خداوند», neither of which is in the
            # verse; the first pass's 7:25 matches the folio exactly).
            body = re.split(r"(?m)^#{2,6} ", secs[i + 1])[0]
            verses = {}
            for m in re.finditer(r"\(([۰-۹]{1,2})\)([^()]*)", body):
                verses.setdefault(_num(m.group(1)), []).append(norm(m.group(2)))
            # ⚠ DUPLICATE MARKERS MEAN THE SECTION SPLIT FAILED, and the
            # concatenated text then shows up as a huge phantom disagreement.
            # Isaiah 7:25 was reported as «عمانوئیل» vs «خود خداوند خود خداوند»
            # — neither of which is in the print; the first pass's 7:25 in fact
            # matches the folio exactly. Never let this pass quietly again.
            dupes = sorted(k for k, v in verses.items() if len(v) > 1)
            if dupes:
                print(f"⚠ ch {ch} in {Path(path).name}: verse marker(s) {dupes[:8]}"
                      f" appear more than once — the chapter split has probably "
                      f"run into the next chapter. Comparisons for this chapter "
                      f"are NOT trustworthy.")
            out[ch] = {k: " ".join(v) for k, v in verses.items()}
        if out:
            return out
    return {}


PATTERNS = [r"(?m)^#{2,4} فصل.*?\(Chapter (\d+)\)",
            r"(?m)^#{2,4} .*?ISAIAH (\d+)",
            r"(?m)^#{2,4} .*?Chapter (\d+)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", required=True)
    ap.add_argument("--second", required=True)
    ap.add_argument("--chapters", help="comma-separated; default = all shared")
    ap.add_argument("--threshold", type=float, default=0.98)
    args = ap.parse_args()

    a = chapters(RESEARCH / args.first, PATTERNS)
    b = chapters(RESEARCH / args.second, PATTERNS)
    if not a or not b:
        raise SystemExit(f"parse failed (first={len(a)} chapters, second={len(b)})")
    chs = ([int(x) for x in args.chapters.split(",")] if args.chapters
           else sorted(set(a) & set(b)))

    total = 0
    flagged = []
    for ch in chs:
        va, vb = a.get(ch, {}), b.get(ch, {})
        if not va or not vb:
            print(f"ch {ch}: MISSING from {'first' if not va else 'second'}")
            continue
        if sorted(va) != sorted(vb):
            print(f"⚠ ch {ch}: MARKER SETS DIFFER — first={sorted(va)[:8]}… "
                  f"second={sorted(vb)[:8]}…  (a numbering disagreement is a "
                  f"print-defect claim; adjudicate on the page)")
        n = 0
        for v in sorted(set(va) | set(vb)):
            ta, tb = va.get(v, ""), vb.get(v, "")
            r = (difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio()
                 if ta and tb else 0.0)
            total += 1
            if r < args.threshold:
                flagged.append((r, ch, v, ta, tb))
                n += 1
        print(f"ch {ch:<3} {len(set(va) | set(vb)):3} verses, {n} disagree")

    flagged.sort()
    print(f"\n{total} verses compared, {len(flagged)} disagree "
          f"(<{args.threshold}) = {100 * len(flagged) / max(total, 1):.1f}%")
    print("\nWORST FIRST — adjudicate each against the page, top-down:\n")
    for r, ch, v, ta, tb in flagged[:25]:
        print(f"── {ch}:{v}  ratio {r:.3f}")
        sm = difflib.SequenceMatcher(None, ta.split(), tb.split(), autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                print(f"     {tag:8} first={' '.join(ta.split()[i1:i2])!r}"
                      f"  second={' '.join(tb.split()[j1:j2])!r}")


if __name__ == "__main__":
    main()
