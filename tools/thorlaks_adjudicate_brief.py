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
    verdict for, PLUS every multi-word site the merge would otherwise settle
    by the read-B default (see THE SPAN SITES below). Same code, imported.
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

THE SPAN SITES (2026-09-21, owner's word)
-----------------------------------------
⛔ `adjudicable()` drops a site because of ONE token in it - `[HN]`, a
drop-cap, notation the conventions settle - but the exclusion applies to the
whole SPAN, and `SequenceMatcher` emits ONE `replace` opcode when two adjacent
words both differ. So an ordinary content dispute rode out of adjudication
attached to a settled token, and the merge handed the whole span to read B with
no verdict, no vote and no findings line. Luke idx 66: 14 sites dropped, 6 of
them multi-word, and read A's `[HN]erra` (10x) became `Herra` by what the word
should be - which convention rule 4 forbids. ⛔ The merge's `[X] N site(s) with
NO verdict` gate CANNOT catch this: a site that was never briefed has no
verdict to be missing.

★ The fix is HERE and not in `sites()`. Site DERIVATION is unchanged - the
merge still demands a verdict for exactly the `adjudicable()` set, so every
existing verdict file still keys against the same sites and an already-merged
page re-merges byte-identically. What changed is that the brief now ALSO asks
about `silent_defaults()` - the multi-word dropped spans - and the merge's
existing verdict-override path (`HEXAPLA_NO_VERDICT_OVERRIDE`) applies those
answers in place of the default. A span verdict is therefore OPTIONAL to the
merge and mandatory to the reader.

⛔ Known-bad control: `HEXAPLA_NO_SPANBRIEF=1` restores the old behaviour, the
spans go unbriefed, and the merge prints them under «WILL BE SETTLED BY THE
READ-B DEFAULT, UNEXAMINED». `tools/test_span_brief.py` asserts both ways.
"""
import argparse
import glob
import io
import os
import re
import subprocess
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
8. **A site marked ★ SPAN carries SEVERAL WORDS.** Settle the WHOLE span, not
   one word of it: your verdict replaces all of it. These are the sites where
   one word is settled by a convention above (an `[HN]` capital, a drop-cap)
   and the word BESIDE it is an ordinary dispute that has been riding along
   unasked. ⚠ Applying the conventions still applies INSIDE the span: if the
   capital is not legible it stays `[HN]` in your reading. ⛔ Never resolve an
   `[HN]` by what the word should be, not even to tidy up a span.

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


def apparatus_only(s):
    """Is this span made ENTIRELY of apparatus - a drop-cap note, `[OG]`?

    ⚠ `silent_defaults()` counts a site as multi-word by its token count, and
    one reader spells the drop-cap as PROSE (`[under decorative initial
    «[O]»]`) against the other's `[OG]`. That is several tokens and no printed
    words: idx 61 carries four of them. Briefing those spends a reader on a
    site the conventions settle, so they are the ONE exclusion from the span
    brief - and only when NEITHER side has a word left outside the brackets.
    ⛔ `[HN][?]` vs `G hñ` is NOT apparatus-only: B carries words.
    """
    for side in ("a", "b"):
        rest = s[side] or ""
        # ⚠ INNERMOST-first, repeatedly: the drop-cap note NESTS brackets
        # (`[under decorative initial «[O]»]`), and a single non-greedy pass
        # leaves `»]` behind - which read as «this side has content» and
        # briefed all four of idx 61's drop-caps.
        for _ in range(6):
            new = re.sub(r"\[[^\[\]]*\]", " ", rest)
            if new == rest:
                break
            rest = new
        # ⛔ Leftover punctuation is not a word. Only a LETTER OR DIGIT outside
        # the apparatus makes this a site a reader must look at.
        if re.search(r"[^\W_]", rest, flags=re.UNICODE):
            return False
    return True


def brief_sites(all_s):
    """(need, spans, brief) - what this tool asks about, in `all_s` order.

    `need`  = exactly what the merge will DEMAND a verdict for (`adjudicable`).
    `spans` = the multi-word sites the merge would otherwise settle by the
              read-B default (`silent_defaults`) - optional to the merge,
              mandatory to the reader. See the module docstring.
    ⛔ Known-bad control: `HEXAPLA_NO_SPANBRIEF=1` empties `spans`.
    """
    need = [s for s in all_s if am.adjudicable(s)]
    spans = ([] if os.environ.get("HEXAPLA_NO_SPANBRIEF") == "1"
             else [s for s in am.silent_defaults(all_s)
                   if not apparatus_only(s)])
    span_ids = set(id(s) for s in spans)
    brief = [s for s in all_s if am.adjudicable(s) or id(s) in span_ids]
    return need, spans, brief


def crops_of(addr):
    m = re.match(r"line(\d{2})(?:-(?:line)?(\d{2}))?$", addr)
    if not m:
        return set()
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return set(range(a, b + 1))


def screen_reads(paths):
    """Run `thorlaks_read_check.py` on every read. Returns the failures.

    ⛔ The tool is run as a SUBPROCESS, on its documented `--file` interface
    and its documented exit code (1 = HARD violation), so this gate cannot
    drift away from the screen it claims to be running.
    ⚠ A screen that could not RUN is a failure too - `[X] a check that cannot
    run did not pass`. An rc the tool does not define (2 = died) is never
    read as a pass.
    """
    check = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "thorlaks_read_check.py")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    failed = []
    for p in paths:
        proc = subprocess.Popen([sys.executable, check, "--file", p], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, _ = proc.communicate()
        out = out.decode("utf-8", "replace")
        hard = [l.strip() for l in out.splitlines() if l.strip().startswith("[X]")]
        if proc.returncode == 0:
            print(u"  screen %-40s rc 0 - passed these checks (⛔ not «read correctly»)"
                  % os.path.basename(p))
            continue
        print(u"[X] screen %s FAILED (rc %d)" % (os.path.basename(p), proc.returncode))
        for l in hard[:8]:
            print(u"      %s" % l)
        if not hard:
            print(u"      (no [X] line - the screen DIED; ⛔ that is not a pass)")
        failed.append((p, proc.returncode, hard))
    return failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--c", help="read 3 (OPTIONAL): sites it settles 2-of-3 are "
                                "never briefed - see thorlaks_adjudicate_merge.py")
    ap.add_argument("--book", required=True)
    ap.add_argument("--page", required=True)
    ap.add_argument("--chapter", type=int, required=True,
                    help="the chapter OPEN AT THE PAGE HEAD (a page may span two)")
    ap.add_argument("--kit", default=None)
    ap.add_argument("--allow-failed-screen", action="store_true",
                    help="build the briefs even though a read FAILED "
                         "thorlaks_read_check.py. ⛔ Last resort: it stamps "
                         "every brief with the violations, and the reader is "
                         "told the read under it is unscreened.")
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

    # ★★ THE SCREEN IS A GATE, NOT A STEP SOMEBODY ELSE RUNS.
    # Measured 2026-09-17 on Luke idx 64: both reads FAILED `read_check` with
    # two HARD violations each (long-s in the verses, a ø, a ö) and this tool
    # briefed 153 sites on top of them anyway. Nothing downstream re-checks,
    # so an adjudicator was one honest agent away from settling word sites on
    # a read the project's own screen had rejected.
    screen_failed = screen_reads([p for p in (g.a, g.b, g.c) if p])
    if screen_failed and not g.allow_failed_screen:
        print(u"⛔ NO BRIEF WRITTEN. Fix the read, or re-run with "
              u"--allow-failed-screen (which stamps every brief).")
        sys.exit(1)

    c = None
    if g.c:
        c, _ = am.verses_with_addr(g.c, g.chapter)
        if sorted(c) != sorted(a):
            print("[X] read 3 does not carry the same (chapter, verse) keys as read A: "
                  "only in C %s / missing from C %s"
                  % (sorted(set(c) - set(a)), sorted(set(a) - set(c))))
            print("    ▶ fix the READ (a missing verse is a finding), not this tool")
            sys.exit(1)

    all_s = am.sites(a, b, c)
    # ★ THE SPAN SITES - see the module docstring. These are NOT derived here:
    # they come from the merge tool's own `silent_defaults()`, so the brief
    # cannot ask about a span the merge would not accept a verdict for.
    need, spans, brief = brief_sites(all_s)
    span_ids = set(id(s) for s in spans)
    span_off = os.environ.get("HEXAPLA_NO_SPANBRIEF") == "1"
    if span_off:
        print(u"⛔ HEXAPLA_NO_SPANBRIEF=1 - multi-word dropped spans are NOT "
              u"briefed (known-bad control). %d span(s) will be settled by the "
              u"read-B default, unexamined."
              % len(am.silent_defaults(all_s)))
    elif spans:
        print(u"★ %d multi-word span(s) dropped by adjudicable() ARE briefed "
              u"(each would otherwise take read B's wording unexamined)"
              % len(spans))
    if c is not None:
        settled = [s for s in all_s if s.get("majority") is not None]
        print("★ 2-of-3 vote: %d site(s) settled in code, %d left to adjudicate"
              % (len(settled), len(need)))
    if not brief:
        if c is not None and settled:
            # ★ The vote settled every site. That is a RESULT, not a failure -
            # the merge then takes an EMPTY verdicts file and refuses nothing.
            print("★ every disputed site was settled 2-of-3; no brief is needed.")
            print("  ▶ run the merge with --c and an empty --verdicts file.")
            sys.exit(0)
        print("[X] no disputed sites - nothing to adjudicate (or the reads are identical)")
        sys.exit(1)
    groups = []           # [(addr, [sites])] in verse order
    for s in brief:
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
    print("sites %d (%d adjudicable + %d multi-word span) in %d verse-address "
          "groups -> %d chunk(s), max %d crops each"
          % (len(brief), len(need), len(spans), len(groups), len(chunks), g.max_crops))
    for k, (grp, crops) in enumerate(chunks, 1):
        n_sites = sum(len(ss) for _, ss, _ in grp)
        span = "line%02d-line%02d" % (min(crops), max(crops)) if crops else "?"
        body = [HEAD.format(book=g.book, idx=g.page.lstrip("p"), total=len(brief), k=k,
                            nk=len(chunks), crops=span, kit=kit, page=g.page, n_sites=n_sites)]
        for ad, ss, key in grp:
            body.append(u"### %s\n" % ad)
            for s in ss:
                if id(s) in span_ids:
                    # ⛔ No `VERDICT:` on this line - `parse_verdicts` skips
                    # every line without it, and a marker that parsed as a
                    # site would key nothing.
                    body.append(u"★ SPAN - several words; settle the WHOLE span "
                                u"(rule 8). Convention rule 3 still applies inside it.")
                body.append(u"    %s | v%d | A=%s | B=%s | VERDICT: | conf:"
                            % (ad, key[1], s["a"] or "(nothing)", s["b"] or "(nothing)"))
            body.append(u"")
        out = "%s%d.md" % (prefix, k)
        io.open(out, "w", encoding="utf-8", newline="\n").write(u"\n".join(body) + u"\n")
        print("  chunk %d: %2d sites, %2d crops (%s) -> %s" % (k, n_sites, len(crops), span, out))


if __name__ == "__main__":
    main()
