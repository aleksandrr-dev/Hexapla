#!/usr/bin/env python
"""Write the CHUNKED adjudication briefs for one page from its two reads.

WHY THIS EXISTS
---------------
idx 61's brief was assembled by hand and then split by hand; the split lost
nothing, but the original generator spelled an empty side `(nothing)` and the
merge tool did not fold it back, so three answered sites read as unanswered
(fixed in `thorlaks_adjudicate_merge.parse_verdicts` 2026-09-17). This tool
derives the sites with the merge tool's OWN `sites()` / `adjudicable()` cut,
so the brief and the merge can never disagree about what was asked.

WHAT IT GUARANTEES
------------------
  * Site list = exactly what `thorlaks_adjudicate_merge.py` will demand a
    verdict for. Same code, imported.
  * Chunks are cut on ADDRESS boundaries and hold at most `--max-crops`
    distinct line crops (default 15), under the 25-image Read guard with
    room for a re-open. A page's sites are never given to one agent.
  * An empty side is written `(nothing)` so a reader sees it; the merge tool
    folds it back to ''.
  * ⛔ Refuses to overwrite existing chunk files.
  * ⚠ Verse numbers must be unique across the page (the merge tool keys by
    verse number only): a page whose two chapters repeat a number fails here
    instead of silently overwriting.

    python tools/thorlaks_adjudicate_brief.py --a _work/luke_p62_read_2026-09-13.md \\
        --b _work/luke_p62_read2_2026-09-17.md --book Luke --page p62 --kit luke_kit2
"""
import argparse
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_adjudicate_merge as am

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

HEAD = u"""# {book} idx {idx} - ADJUDICATION of {total} disputed word sites, chunk {k} of {nk} ({crops})

★ **This is NOT a transcription task and NOT a re-read of the page.** Two
independent reads of this page already exist - one from the packed sheets,
one from the line crops (8.3x native) - and they DISAGREE at the sites below.
Your job is to settle those sites, one at a time, against the pixels.

## What to open

Line crops: `C:\\Projects\\Hexapla-releases\\research\\_prep\\{kit}\\{page}\\lineNN.png`
- ONLY the crops named in this chunk ({crops}). Each holds exactly one line of
running text. `page.png` is for layout only.
⛔ Do not open the packed sheets. ⛔ Do not consult any other text of {book},
printed or electronic: a reading that comes from knowing the verse is not
evidence about this page.

## Conventions that are ALREADY SETTLED - apply them, do not re-open them

1. **Long-s is written plain `s`.** The sort `ſ` never appears in returned
   text. Long-s has NO crossbar; `f` has one. Many sites below are exactly
   this: one reader wrote `f` where the print carries long-s, or the reverse.
   Say which SORT the print carries; write long-s as plain `s` in the verdict
   and add the word «long-s» after it.
2. **No `ø` is adjudicated in {book}, ever** - the owner ruled the book gets NO
   `ø` rate. Every o stands plain. If you see a stroked o, write it plain and
   say so in NOTES; do not write the stroked sort.
3. **Capital H / N**: decide ONLY by the top-left flourish (`N` hooks DOWN,
   `H` sweeps UP, the owner's ruling 2026-09-14). If it is not legible, the
   verdict is `[HN]` + the rest of the word. ⛔ Never by what the word should be.
4. **A nasal bar is kept as the sort it is** (`hñ`, `ñ`, `ū`) - it is not
   expanded. `Enn` vs `Eñ` IS a real dispute: report what the print carries.
5. **The address is the VERSE's crop range, not the word's crop.** A site
   headed `line05-line07` means the word is on ONE of those crops - open them
   until you find it. If you cannot find the word on any crop in the range,
   say so: an address that does not hold its word is itself a finding.
6. **Keep your hedges.** `[?]` after a glyph you cannot settle is a correct
   answer. A confident wrong answer is the expensive one.
7. A side written `(nothing)` means that reader has NO word there: the
   dispute is whether the word exists in the print at all.

## How to answer

For EVERY site, one line, in this exact shape - copy the A= and B= parts
EXACTLY as printed here, do not normalise them:

    <lineNN-lineMM> | v<N> | A=<read1 form> | B=<read2 form> | VERDICT: A | conf: high

- `VERDICT: A` or `VERDICT: B` - the form that matches the pixels.
- `VERDICT: NEITHER - <your own reading>` when neither matches. ★ Expected,
  not a failure. Put ONLY the reading after the dash; reasons go in NOTES.
- `VERDICT: ILLEGIBLE` when the crop cannot settle it - say what blocks it.
- `conf: high | medium | low`.
- ⛔ Do not return a corrected transcription. Return ONLY these verdict lines
  (every site of this chunk, {n_sites} of them), then a short NOTES section,
  then a NUMERALS section: every printed verse numeral on the crops you
  opened, as `NUMERAL: lineNN | printed <N> | precedes the word <w>`.

Write the file named in your task. Reply with the path and the count of
VERDICT lines written.

## The sites - {n_sites} in this chunk, grouped by the line crops that hold them

"""


def crops_of(addr):
    m = re.match(r"line(\d{2})(?:-(?:line)?(\d{2}))?$", addr)
    if not m:
        return set()
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return set(range(a, b + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--page", required=True)
    ap.add_argument("--chapter", type=int, required=True,
                    help="the chapter OPEN AT THE PAGE HEAD (a page may span two)")
    ap.add_argument("--kit", default=None)
    ap.add_argument("--max-crops", type=int, default=15)
    ap.add_argument("--out-prefix", default=None,
                    help="default _work/<book>_<page>_ADJ_CHUNK")
    g = ap.parse_args()
    kit = g.kit or "%s_kit2" % g.book.lower()
    prefix = g.out_prefix or os.path.join(am.DATA if hasattr(am, "DATA") else ".",
                                          "_work", "%s_%s_ADJ_CHUNK" % (g.book.lower(), g.page))

    a, na = am.verses_with_addr(g.a, g.chapter)
    b, addr = am.verses_with_addr(g.b, g.chapter)
    for path, d in ((g.a, a), (g.b, b)):
        n_lines = sum(1 for l in io.open(path, encoding="utf-8").read().splitlines()
                      if re.match(r"\s*\d{1,3}\s+\S", l))
        if n_lines != len(d):
            print("[!] %s: %d verse lines but %d distinct verse numbers - a number repeats"
                  " across chapters, or prose lines start with a digit (row 46)"
                  % (os.path.basename(path), n_lines, len(d)))
    if sorted(a) != sorted(b):
        print("[X] the two reads do not carry the same (chapter, verse) keys: only in A %s / only in B %s"
              % (sorted(set(a) - set(b)), sorted(set(b) - set(a))))
        print("    ▶ fix the READ (a missing verse is a finding), not this tool")
        sys.exit(1)

    need = [s for s in am.sites(a, b) if am.adjudicable(s)]
    if not need:
        print("[X] no disputed sites - nothing to adjudicate (or the reads are identical)")
        sys.exit(1)
    groups = []           # [(addr, [sites])] in verse order
    for s in need:
        ad = addr.get(s["key"], "line??")
        if groups and groups[-1][0] == ad and groups[-1][2] == s["key"]:
            groups[-1][1].append(s)
        else:
            groups.append([ad, [s], s["key"]])

    chunks, cur, cur_crops = [], [], set()
    for ad, ss, key in groups:
        c = crops_of(ad)
        if cur and len(cur_crops | c) > g.max_crops:
            chunks.append((cur, cur_crops))
            cur, cur_crops = [], set()
        cur.append((ad, ss, key))
        cur_crops |= c
    if cur:
        chunks.append((cur, cur_crops))

    existing = glob.glob(prefix + "*.md")
    if existing:
        print("[X] %d chunk file(s) already exist under %s - refusing to overwrite" % (len(existing), prefix))
        sys.exit(1)
    print("sites %d in %d verse-address groups -> %d chunk(s), max %d crops each"
          % (len(need), len(groups), len(chunks), g.max_crops))
    for k, (grp, crops) in enumerate(chunks, 1):
        n_sites = sum(len(ss) for _, ss, _ in grp)
        span = "line%02d-line%02d" % (min(crops), max(crops)) if crops else "?"
        body = [HEAD.format(book=g.book, idx=g.page.lstrip("p"), total=len(need), k=k,
                            nk=len(chunks), crops=span, kit=kit, page=g.page, n_sites=n_sites)]
        for ad, ss, key in grp:
            body.append(u"### %s\n" % ad)
            for s in ss:
                body.append(u"    %s | v%d | A=%s | B=%s | VERDICT: | conf:"
                            % (ad, key[1], s["a"] or "(nothing)", s["b"] or "(nothing)"))
            body.append(u"")
        out = "%s%d.md" % (prefix, k)
        io.open(out, "w", encoding="utf-8", newline="\n").write(u"\n".join(body) + u"\n")
        print("  chunk %d: %2d sites, %2d crops (%s) -> %s" % (k, n_sites, len(crops), span, out))


if __name__ == "__main__":
    main()
