"""Find DUPLICATED WORD RUNS inside a verse - the strip-overlap defect.

WHY THIS EXISTS
---------------
`kxii_strips.py` cuts each column into strips that OVERLAP: strip X1's last
printed line and strip X2's first line are THE SAME LINE (and occasionally two).
Reading two strips straight through therefore writes the same clause twice.

That defect is invisible to every check the campaign already runs:
  · the verse COUNT is unchanged - the duplicate sits INSIDE one verse;
  · the audit compares counts, so it passes;
  · `grep -c '^[0-9]\\+ '` compares counts, so it passes;
  · the charset scan passes - the characters are all legitimate.

It was found in Wisdom 17:4 only because the kxii.se witness diff happened to be
run on that chunk. This script finds it with no witness and no model tokens.

WHAT IT DOES
------------
For every verse line, look for a run of N or more words that occurs twice in the
SAME verse. Swedish prose does repeat short phrases, so the default N=4 is the
smallest run that was empirically quiet across the finished corpus; lower it to
tighten, raise it to reduce noise.

⚠ A hit is a CANDIDATE, not a verdict. Genuine repetition exists in scripture
("...oc h sade: ... och sade:"). Read the verse, and if it looks like an overlap,
check the strip boundary it sits on before deleting anything.

CALIBRATION - THE KNOWN-BENIGN BASELINE (updated 2026-08-30, n=6)
The corpus yields exactly TWENTY candidates and **all twenty were read and
are genuine PARALLELISM or a printed repetition**, not overlap damage.
⚠ Sirach alone prints FOURTEEN of them, so `kxii_dup_runs.py sirach` printing 14
is the correct result. The other six sit in four different files: Judith 5:3,
Tobit 13:16, 2 Maccabees 3:15 / 5:8 / 15:40, and Bel and the Dragon 23.
⚠ PER-BOOK EXPECTED COUNTS, so a single-book run can be checked on its own:
tobit 1 · judith 1 · sirach 14 · 2maccabees 3 · daniel_additions 1 · wisdom 0 ·
baruch 0 · 1maccabees 0 · esther_additions 0. Anything above these is NEW.
⚠ THE PREVIOUS HEADER SAID "THIRTEEN corpus-wide / TWELVE Sirach" WHILE THE
TABLE BELOW ALREADY LISTED FOURTEEN ROWS - 12 Sirach + Judith + Tobit = 14, not
13. The row list was right and the sentence was wrong; the corpus figure is
corrected here. Count the table, not the prose.

    judith.md    Judith 5:3     «hwad hafwa the för»        (rhetorical questions)
    sirach.md    Sirach 2:12    «hwilken är någon tijd»
    sirach.md    Sirach 7:5     «låt tigh icke tyckia»
    sirach.md    Sirach 10:2    «är så äro ock»              (såsom… så äro ock, x2)
    sirach.md    Sirach 11:27   «går så tänck at»           (antithetical, x2)
    sirach.md    Sirach 12:12   «tigh at han icke»
    sirach.md    Sirach 13:21   «sigh i sälskap medh»
    sirach.md    Sirach 18:25   «tänckia at man åter»
    tobit.md     Tobit 13:16    «skola warda alle the»      (triple parallelism)
    sirach.md    Sirach 22:14   «icke mycket medh en»
    sirach.md    Sirach 28:12   «äro warder wreden thes»     (adjudicated 2026-08-24)
    sirach.md    Sirach 31:10   «och giorde doch icke»       (adjudicated 2026-08-24)
    sirach.md    Sirach 33:12   «somliga b hafwer han»       (adjudicated 2026-08-25)
    sirach.md    Sirach 33:31   «hafwer tu en tienare»       (adjudicated 2026-08-25)
    sirach.md    Sirach 34:4    «är huru kan thet»           (adjudicated 2026-08-25)
    sirach.md    Sirach 37:20   «förr än tu något»           (adjudicated 2026-08-26)
    2maccabees.md 2 Macc 3:15    «i goda troo nedersatt»   (adjudicated 2026-08-30)
    2maccabees.md 2 Macc 5:8     «war och hwar man»        (adjudicated 2026-08-30)
    2maccabees.md 2 Macc 15:40   «watn dricka thet»        (adjudicated 2026-08-30)
    daniel_add.md Bel+Dragon 23  «säija at han icke»     (adjudicated 2026-08-29)

⚠ THE FOUR ROWS ABOVE WERE ADDED 2026-08-30, ALL CLEARED BY THE NEXT-WORD
DISCRIMINATOR ALONE (rule 1 below) - each repetition diverges at the very next
word, which an overlap duplicate cannot do: 3:15 «är/ icke förfara» vs
«hade/ wille thet förwara»; 5:8 «war honom hätsk» vs «förbannade honom»;
15:40 «icke lustigt» vs «lustigt» (the book's closing antithesis);
Bel 23 «annat är» vs «en lefwande gudh är». None needed a sheet or a witness.

★ 37:20 IS THE CHEAPEST CLEAR SO FAR, AND IT SHOWS THE NEXT-WORD TEST WORKING
FIRST TRY. «Förr än tu något begynner/ befråga tigh; och förr än tu något
giör/ tag ther rådh til:» - the run «förr än tu något» is printed twice.
Cleared on four grounds, in ascending cost:
  1. **THE NEXT-WORD DISCRIMINATOR (try this FIRST, it is free)**: an overlap
     duplicate reproduces the NEXT WORD identically; a parallelism diverges.
     Here it diverges immediately - «begynner» vs «giör». That alone is close
     to decisive and it cost nothing;
  2. GEOMETRY: both halves sit on lines INTERIOR to p686_R3. The R2->R3 overlap
     was the single v19 line at the strip top, so no overlap mechanism was even
     available at v20 - check WHERE the run sits before theorising about it;
  3. the kxii.se witness prints the identical doubled structure and its diff
     reports NO SITE at 37:20;
  4. sense: KJV Sirach 37:16 has the same doubled construction («Let reason go
     before every enterprise, and counsel before every action»).

⚠ 31:10 IS THE MODEL FOR HOW TO CLEAR ONE OF THESE. It sits on the p682_R4 ->
R5 strip boundary, which is exactly where an overlap defect would hide, and it
was cleared on FOUR independent grounds rather than on plausibility:
  1. the verse was transcribed from R5 ALONE - R4's copy of its first line was
     clipped and was never written, so no cross-strip duplication was possible;
  2. the phrase is printed TWICE on the R5 image itself, ending two consecutive
     lines («…och giorde doch» / «icke; skada giöra/ och giorde doch icke:»);
  3. **the kxii.se witness diff reports NO SITE at 31:10** - an independent
     transcription of the same page agrees verbatim, and a duplicated clause is
     precisely what a witness diff catches (that is how Wisdom 17:4 was found);
  4. sense: KJV Sirach 31:10 «who might offend, and hath not offended; or done
     evil, and hath not done it» - the parallelism is in the text itself.
▶ Clear a new candidate the same way, and only then add it here.

⚠ 33:12 WAS CLEARED THE SAME FOUR WAYS, and it is the easiest class of all: the
verse sits MID-STRIP on p684_L2, nowhere near a strip boundary, so the overlap
defect cannot produce it; the phrase is printed twice on that image («Somliga (b)
hafwer han wälsignat…» / «…men somliga (b) hafwer han förbannat…»); the kxii.se
diff reports **25 of 25 verses identical and ZERO sites** over the chapter so
far; and KJV 33:12 carries the same antithesis («Some of them hath he blessed…
and some of them hath he cursed»). ▶ **Note the print really does set «(b)»
TWICE in this verse** - that is the page, not a transcription slip, and it is
what pushes the run over n=4.

⚠⚠ 33:31 IS THE ONE TO STUDY, because it is the DANGEROUS shape: the repetition
straddles a seam (p684_L5 -> p684_R1) and a duplicated clause there is exactly
what this tool exists to catch. It is nonetheless benign, on four grounds:
  1. the seam is a COLUMN seam, not a strip seam - strips overlap WITHIN a
     column, so the L5->R1 boundary cannot duplicate a line by construction;
  2. L5's foot breaks the word mid-hyphen at «haf=» and R1's first line opens
     «wer tu en tienare/…», so the two halves JOIN rather than repeat - and the
     first «Hafwer tu en tienare» is four lines earlier on L5, in plain view;
  3. **the kxii.se witness diff reports 32 of 32 verses identical and ZERO
     sites** for the whole chapter;
  4. KJV 33:31 doubles the clause itself («If thou have a servant, let him be
     unto thee as thyself… If thou have a servant, entreat him as a brother»).

⚠ 34:4 IS THE SAME DANGEROUS SHAPE AS 33:31 - it straddles the p684_R2 -> R3
STRIP boundary, which unlike a column seam really can duplicate a line. It is
nonetheless benign:
  1. the verse was transcribed from **R2 ALONE**, where BOTH halves are printed:
     «4. Hwad oreent (a) är/ huru kan thet reent wa=» ends one line and
     «ra; och hwad falskt är/ huru kan thet sant wara?» ends the next. R3's copy
     of that second line is the one-line overlap and was never written;
  2. the phrase is therefore printed TWICE on the R2 image itself;
  3. **the two occurrences DIVERGE in the very next word** - «reent wara» vs
     «sant wara». A strip-overlap duplicate reproduces the continuation
     identically; a parallelism does not. This is the cheapest discriminator in
     the whole class and it should be tried FIRST on any new candidate;
  4. KJV 34:4 carries the same double question («Of an unclean thing what can be
     cleansed? and from that thing which is false what truth can come?»).
  ⚠ Leg 3 of the 31:10 model - the kxii.se witness diff - is NOT yet available
  here: ch34 is not closed, so no chapter diff has been run. **That leg is OWED
  at the close of ch34**, and if the diff ever reports a site at 34:4 this
  adjudication must be reopened.

▶ **So a run that returns MORE than these fifteen has found something new.**
Diff against this list rather than treating any hit as a failure.
⚠ n=4 is deliberate: the one KNOWN real instance, Wisdom 17:4's duplicated
«then the förskräckte them/», is exactly four words. Raising n to silence the
parallelism would also silence the defect. A dozen easily-dismissed candidates
across a whole corpus is the right trade.
(Wisdom 17:4 does not appear above because it was corrected on 2026-08-20.)

USAGE
    python tools/kxii_dup_runs.py                 # every karlxii_*.md
    python tools/kxii_dup_runs.py sirach --n 5
Exits 1 if any candidate is found, so a wrapper cannot print success over it.
"""
import argparse
import glob
import os
import re
import sys

# (!) Windows consoles default to cp1252 and this script prints «» and ⚠.
#     Without this the tool CRASHES after printing its findings, which loses the
#     exit code and looks like a pass. Same trap as tools/kxii_locate.py.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = r"C:\Projects\Hexapla-releases\research"
VERSE = re.compile(r"^(\d+) (.*)$")
# Word = letters only; the print's "/" comma and apparatus marks are dropped so
# they cannot break an otherwise-identical run.
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def dup_runs(words, n):
    """Return the first duplicated run of >= n words, or None."""
    seen = {}
    for i in range(len(words) - n + 1):
        key = tuple(w.lower() for w in words[i:i + n])
        if key in seen and i - seen[key] >= n:
            return " ".join(words[i:i + n]), seen[key], i
        seen.setdefault(key, i)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("books", nargs="*", help="book slugs, e.g. sirach 1maccabees (default: all)")
    ap.add_argument("--n", type=int, default=4, help="minimum run length in words (default 4)")
    a = ap.parse_args()

    if a.books:
        paths = [os.path.join(RESEARCH, "karlxii_%s.md" % b) for b in a.books]
    else:
        paths = sorted(p for p in glob.glob(os.path.join(RESEARCH, "karlxii_*.md"))
                       if ".bak" not in p)

    hits, checked = [], 0
    for p in paths:
        if not os.path.exists(p):
            print("MISSING: %s" % p)
            return 2                      # (!) never report "clean" for a file we could not read
        chapter = "?"
        for ln, line in enumerate(open(p, encoding="utf-8"), 1):
            if line.startswith("##"):
                chapter = line.strip().lstrip("#").strip()
                continue
            m = VERSE.match(line.rstrip("\n"))
            if not m:
                continue
            checked += 1
            words = WORD.findall(m.group(2))
            r = dup_runs(words, a.n)
            if r:
                hits.append((os.path.basename(p), chapter, m.group(1), ln, r[0]))

    print("checked %d verse lines in %d file(s), run length >= %d"
          % (checked, len(paths), a.n))
    if not hits:
        print("no duplicated word runs - no sign of the strip-overlap defect")
        return 0
    print("\n%d CANDIDATE(S) - read the verse and check its strip boundary:" % len(hits))
    for f, ch, v, ln, run in hits:
        print("  %-26s %-22s v%-4s line %-6d  \u00ab%s\u00bb" % (f, ch, v, ln, run))
    print("\n\u26a0 A hit is a CANDIDATE, not a verdict - scripture does repeat phrases.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
