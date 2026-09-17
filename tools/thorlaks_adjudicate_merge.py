#!/usr/bin/env python
"""Build ONE merge candidate from TWO independent reads plus their adjudication.

WHY THIS EXISTS
---------------
Two independent reads of Luke idx 61 agreed on every structural claim and then
disagreed at 129 word sites - about three per verse, in all forty verses
(`research/_evidence/thorlaks_read_screen_could_not_run_2026-09-17.md`). Neither
read is the authority, and row 48 closes the obvious move: a third open read
buys a different wrong answer.

So the disputes are settled ONE SITE AT A TIME against the line crops, as a
forced choice, and this tool folds those verdicts back into a single text.

WHAT IT GUARANTEES
------------------
  * It re-derives the site list from the two reads with the SAME cut the brief
    generator used. A verdict file that does not cover every derived site
    fails the run - ⛔ nothing is written.
  * Agreement is not assumed to be correctness: where the two reads agree it
    takes that wording, and where they differ ONLY in notation the conventions
    settle (long-s, the virgule's spacing, `[HN]`, the nasal bar) it applies
    the convention.
  * The output is checked with `thorlaks_read_check.py`'s own predicates before
    it is written: no long-s, no ø, no ö, no Cyrillic. A merge candidate that
    would fail the screen is not written at all.
  * ⛔ DRY RUN IS THE DEFAULT.

    python tools/thorlaks_adjudicate_merge.py --a <read1.md> --b <read2.md> \\
        --verdicts <result.md> --page p61 --book Luke --chapter 9
    ... --out research/_parts/luke_p61-65.md --apply

Exit 0 = a candidate was produced (or would be). Exit 1 = it was not, and the
reason is printed. A tool that cannot run has not passed.
"""
import argparse
import difflib
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_read_check as rc

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

LONG_S = u"ſ"


ROMAN = dict(I=1, V=5, X=10, L=50, C=100, D=500, M=1000)


def _roman(s):
    s, tot, prev = s.upper(), 0, 0
    for c in reversed(s):
        if c not in ROMAN:
            return None
        v = ROMAN[c]
        tot += -v if v < prev else v
        prev = max(prev, v)
    return tot or None


def chapter_of_heading(line):
    """The chapter a `## Cap. N` / `### Luke N` heading opens, or None.

    A page can span two chapters (idx 62 is Luke 9:40-62 then 10:1-16) and the
    two reads spell the break differently: read A writes `### Luke 10`, read B
    writes `## Cap. 10`. Both must resolve to 10, or the verses after the break
    are filed under the chapter the page OPENED in and collide.
    """
    h = line.strip().lstrip("#").strip().rstrip(".")
    m = re.match(r"^(?:Cap\.?|Chapter|[A-Z][a-z]+)?\s*([0-9]{1,3}|[IVXLCDM]+)\s*\.?$",
                 h, re.I)
    if not m:
        return None
    tok = m.group(1)
    return int(tok) if tok.isdigit() else _roman(tok)


def verses_with_addr(path, chapter0):
    """{(chapter, verse): text}, {(chapter, verse): addr} - NOT keyed by verse.

    `chapter0` is the chapter open at the page head; every verse before the
    first chapter heading belongs to it.
    """
    text = io.open(path, encoding="utf-8").read()
    out, addr = {}, {}
    # A sheets read WRAPS its verses at ~80 columns (idx 62-65); a verse is
    # its numbered line plus every following line up to the next numbered
    # line or heading. Before 2026-09-17 the continuation lines were dropped.
    joined, chap = [], chapter0
    for line in rc.verses_of(text, verbose=False, strip_headings=False).splitlines():
        if re.match(r"\s*\d{1,3}\s+\S", line):
            joined.append((chap, line.rstrip()))
        elif line.strip() and not line.strip().startswith("#") and joined:
            joined[-1] = (joined[-1][0], joined[-1][1] + " " + line.strip())
        elif line.strip().startswith("#"):
            c = chapter_of_heading(line)
            if c:
                chap = c
            joined.append((chap, ""))   # a heading closes the verse
    for chap, line in joined:
        m = re.match(r"\s*(\d{1,3})\s+(.*)$", line)
        if not m:
            continue
        v, t = (chap, int(m.group(1))), m.group(2)
        # a long bracketed NOTE inside the verse (`[continuation of the verse
        # opened on idx 61 ... rule]`) is apparatus, not a reading
        t = re.sub(r"\[[^\]]{40,}\]", "", t)
        am = re.search(r"line(\d{2})(?:-(?:line)?(\d{2}))?", t)
        if am:
            addr[v] = "line%s%s" % (am.group(1),
                                    "-line" + am.group(2) if am.group(2) else "")
        t = re.sub(r"\s+—\s+line[\d\-]+.*$", "", t)
        t = re.sub(r"\s*\[hedge:.*$", "", t)
        t = re.sub(u"\\s*\\[«.*$", "", t)
        out[v] = t.strip()
    return out, addr


def words(t):
    return t.replace("/", " / ").split()


def norm(w):
    """The axes the conventions ALREADY settle - never a content axis."""
    w = w.replace(LONG_S, "s")
    w = w.replace(u"œ", u"æ").replace(u"Œ", u"Æ")
    w = w.replace(u"ø", "o").replace(u"Ø", "O")
    w = w.replace(u"°", "")
    w = re.sub(r"\[HN\]", "", w)
    w = w.replace(u"ñ", "n").replace(u"Ñ", "N")
    return w.lower()


def settle(w):
    """Write a form the way a merged text must carry it."""
    return w.replace(LONG_S, "s")


# Sorts a merged text does not carry: the slashed o and the umlaut (rows 48 and
# 40), the long-s, the oe ligature and the ring one reader puts on `þr`. ⛔ This
# is NOT a conversion table - nothing is ever rewritten INTO another sort. It
# only decides WHICH OF TWO INDEPENDENT READINGS of the same word to take when
# one of them already complies and the other does not.
DISFAVOURED = u"øØöÖſœŒ°"


def prefer(ta, tb):
    if ta and tb and any(c in ta for c in DISFAVOURED) \
            and not any(c in tb for c in DISFAVOURED):
        return tb
    return ta or tb


def sites(a, b):
    """Every disputed site, in the brief's order. ONE cut, used everywhere."""
    out = []
    for key in sorted(set(a) & set(b)):
        ch, v = key
        wa, wb = words(a[key]), words(b[key])
        na, nb = [norm(w) for w in wa], [norm(w) for w in wb]
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, na, nb).get_opcodes():
            ra, rb = " ".join(wa[i1:i2]), " ".join(wb[j1:j2])
            out.append(dict(chapter=ch, verse=v, key=key,
                            tag=tag, i1=i1, i2=i2, j1=j1, j2=j2,
                            a=ra, b=rb,
                            notation=(" ".join(na[i1:i2]) == " ".join(nb[j1:j2]))))
    return out


def adjudicable(s):
    """The sites a reader was asked about - the brief's own exclusions."""
    if s["tag"] == "equal" or s["notation"]:
        return False
    if "[HN]" in s["a"] or "[HN]" in s["b"]:
        return False
    if "decorative initial" in s["a"] or "[OG]" in s["b"]:
        return False
    return True


VERDICT_RE = re.compile(
    r"^\s*(?P<addr>line[\d\-line]*)\s*\|\s*v(?P<verse>\d{1,3})\s*\|\s*"
    r"A=(?P<a>.*?)\s*\|\s*B=(?P<b>.*?)\s*\|\s*VERDICT:\s*(?P<verdict>.*?)"
    r"(?:\s*\|\s*conf:\s*(?P<conf>.*?))?\s*$")


def parse_verdicts(path):
    got = {}
    bad = []
    for line in io.open(path, encoding="utf-8").read().splitlines():
        if "VERDICT:" not in line:
            continue
        m = VERDICT_RE.match(line)
        if not m:
            bad.append(line.strip())
            continue
        d = m.groupdict()
        # The brief spells an EMPTY side `(nothing)` so a reader can see it;
        # the site list derives it as ''. Without this fold, three answered
        # sites on idx 61 (v17 A=|B=z, v18 A=|B=ad, v40 ...|B=) read as
        # unanswered and the run refused - misdiagnosed on 09-17 as sites
        # "never written into any brief".
        for side in ("a", "b"):
            if (d[side] or "").strip().lower() in ("(nothing)", "(none)", "(empty)"):
                d[side] = ""
        # ⚠ KEYED BY OCCURRENCE, not by (verse, A, B): a verse can carry the
        # SAME dispute twice (idx 61 v7 has two `[uncertain glyph]`/`á` sites,
        # v14 two `fimtig'`/`fimtig`). Keyed by content alone, the second
        # verdict silently REPLACED the first and 119 lines parsed as 117.
        k = (int(d["verse"]), d["a"].strip(), d["b"].strip())
        n = sum(1 for key in got if key[:3] == k)
        got[k + (n,)] = dict(verdict=(d["verdict"] or "").strip(),
                             conf=(d["conf"] or "").strip(), raw=line.strip())
    return got, bad


def choose(site, v):
    """The wording this site contributes, or None with a reason."""
    t = v["verdict"]
    up = t.upper()
    if up.startswith("A"):
        return settle(site["a"]), None
    if up.startswith("B"):
        return settle(site["b"]), None
    if up.startswith("NEITHER"):
        own = re.sub(r"^NEITHER\s*[-—:]*\s*", "", t, flags=re.I).strip()
        # A reader's own reading comes with its reasons: `all' (abbreviated
        # with a raised mark ...)`, `Enn hañ hastade - "Enn" is a plain
        # double-n ...`. Only the READING is text; ten idx-61 verses carried
        # the reasons into the merge candidate on 09-17. Parentheticals go,
        # then everything after a spaced dash or semicolon.
        own = re.sub(r"\s*\([^)]*\)", "", own)
        own = re.split(r"\s+[-—–]\s+|;\s+", own, 1)[0].strip()
        own = own.strip(u"\"“” ").strip()   # ⚠ not `'` - `all'` IS the reading
        own = re.sub(r"\(?long-s\)?", "", own, flags=re.I).strip()
        if not own:
            return None, "NEITHER with no reading of its own"
        # ⚠ An adjudicator's OWN reading is not screened by `prefer()` - there
        # is no second reading to prefer over it. idx 62 v56 came back
        # `NEITHER - Sör`, and row 40 closes that: this print has no ö sort.
        # The whole-text screen caught it, but only as «ö somewhere», with no
        # site. Refuse HERE, named, so the one site can be re-adjudicated.
        # ⛔ ø/ö ONLY - long-s is settled by `settle()` and the ligature by the
        # conventions; those are notation, not a claimed sort.
        bad = [c for c in u"øØöÖ" if c in own]
        if bad:
            return None, ("NEITHER reading %r carries %s - no such sort in this "
                          "print (row 40/48); re-adjudicate this site"
                          % (own, "/".join(bad)))
        return settle(own), None
    if up.startswith("ILLEGIBLE"):
        # A hedge is a correct answer; the merged text must SHOW it.
        base = settle(site["b"] or site["a"])
        return (base + "[?]") if base else "[illegible]", None
    return None, "unrecognised verdict %r" % t[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="read 1 (the base wording)")
    ap.add_argument("--b", required=True, help="read 2")
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--page", required=True)
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true")
    g = ap.parse_args()

    a, _ = verses_with_addr(g.a, g.chapter)
    b, addr = verses_with_addr(g.b, g.chapter)
    if sorted(a) != sorted(b):
        print("[X] the two reads do not carry the same (chapter, verse) keys: "
              "only in A %s / only in B %s"
              % (sorted(set(a) - set(b)), sorted(set(b) - set(a))))
        sys.exit(1)
    chapters = sorted(set(ch for ch, _ in a))
    print("chapters on this page            : %s"
          % ", ".join(str(c) for c in chapters))
    # ⚠ The verdict lines key a site by `v<N>` ALONE (the brief writes no
    # chapter). That is unambiguous only while no verse number occurs in two
    # chapters of the same page - true on idx 62 (9:40-62 vs 10:1-16). If it
    # ever is not, the verdicts cannot be attached and nothing is written.
    dupes = sorted(v for v in set(v for _, v in a)
                   if sum(1 for _, w in a if w == v) > 1)
    if dupes:
        print("[X] verse number(s) %s occur in more than one chapter on this "
              "page - the verdict files key by verse alone, so a verdict "
              "cannot be attached. NOTHING WRITTEN." % dupes)
        sys.exit(1)

    all_sites = sites(a, b)
    need = [s for s in all_sites if adjudicable(s)]
    got, bad = parse_verdicts(g.verdicts)
    print("sites derived from the two reads : %d" % len(need))
    print("verdict lines parsed             : %d%s"
          % (len(got), "  (%d unparsable)" % len(bad) if bad else ""))
    for l in bad[:5]:
        print("    ? %s" % l[:100])

    missing, unusable, resolved = [], [], {}
    seen = {}
    for s in need:
        base = (s["verse"], s["a"], s["b"])
        n = seen.get(base, 0)
        seen[base] = n + 1
        key = base + (n,)
        v = got.get(key)
        if not v:
            missing.append(key)
            continue
        text, why = choose(s, v)
        if text is None:
            unusable.append((key, why))
            continue
        resolved[id(s)] = text

    if missing or unusable:
        print("[X] %d site(s) with NO verdict, %d unusable - NOTHING WRITTEN"
              % (len(missing), len(unusable)))
        for k in missing[:10]:
            print("    missing  v%-3d A=%s | B=%s" % (k[0], k[1][:30], k[2][:30]))
        for k, why in unusable[:10]:
            print("    unusable v%-3d %s" % (k[0], why))
        sys.exit(1)

    # rebuild
    out_v = {}
    for key in sorted(a):
        wa, wb = words(a[key]), words(b[key])
        pieces = []
        for s in [x for x in all_sites if x["key"] == key]:
            if s["tag"] == "equal":
                # The two reads agree here - but «agree» is after the
                # conventions' own axes are normalised away, so one of them
                # may still be spelling the word with a sort no merged text
                # carries. Take the compliant one, token by token.
                pieces.append(" ".join(
                    settle(prefer(ta, tb))
                    for ta, tb in zip(wa[s["i1"]:s["i2"]], wb[s["j1"]:s["j2"]])))
            elif not adjudicable(s):
                # Notation, [HN] bracketing, the drop-cap: the convention
                # decides, and read B is the one written to it (it brackets
                # [HN] at 42 % against read A's 14 %).
                # ⚠ EXCEPT where B's form carries a sort no merged text may
                # carry (ø, ö) and A's independent reading of the same word
                # does not. That is not a silent conversion of B - it is
                # taking the reading that already complies, corroborated by
                # the other instrument. If BOTH carry one, nothing is written.
                src_b = " ".join(wb[s["j1"]:s["j2"]])
                src_a = " ".join(wa[s["i1"]:s["i2"]])
                pieces.append(settle(prefer(src_b, src_a)))
            else:
                pieces.append(resolved[id(s)])
        text = " ".join(p for p in pieces if p)
        text = re.sub(r"\s+/", "/", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        out_v[key] = text

    joined = "\n".join(out_v.values())
    fail = []
    if LONG_S in joined:
        fail.append("long-s in the merged text")
    for ch, why in ((u"ø", u"ø (no ø is adjudicated in this book)"),
                    (u"ö", u"ö (row 40: no such sort in this print)")):
        if ch in joined:
            fail.append(why)
    import unicodedata
    if [c for c in joined if "CYRILLIC" in unicodedata.name(c, "")]:
        fail.append("Cyrillic homoglyph")
    if fail:
        print("[X] the merge candidate would FAIL the read screen: %s"
              % "; ".join(fail))
        sys.exit(1)

    # ⚠ Row 46: no prose line in a part file may BEGIN with a digit -
    # `merge_parts`' VERSE_RE is `^(\d+)\s+\S` and it reads one as scripture
    # (the phantom Luke 5:56). Every line below is prefixed or bulleted.
    head = [
        u"# %s - %s, adjudicated" % (g.book, g.page),
        u"",
        u"**SCOPE: this file owns PDF idx %s only.** The SCOPE line is the"
        % g.page.lstrip("p"),
        u"authority, not the filename.",
        u"",
        u"- Built by `tools/thorlaks_adjudicate_merge.py` from TWO independent",
        u"  reads of the page (`%s`, `%s`)" % (os.path.basename(g.a),
                                               os.path.basename(g.b)),
        u"  and a forced-choice adjudication of every site they disagreed on",
        u"  (`%s`)." % os.path.basename(g.verdicts),
        u"- Sites derived from the diff: %d. ⛔ The build refuses to write"
        % len(need),
        u"  while any one of them lacks a verdict.",
        u"- ⚠ Where the two reads AGREE the wording is theirs and is NOT",
        u"  independently confirmed: agreement is not correctness.",
        u"- ⛔ `[HN]` sites stay bracketed (conventions, row 51). ⛔ No ø is",
        u"  adjudicated in this book (row 48, the owner's option B): every o",
        u"  stands plain, and that is NOT a 0 % rate.",
        u"",
    ]
    # ⛔ ONE `## Book N` heading PER CHAPTER on the page. A single heading over
    # two chapters files idx 62's Luke 10:1-16 as Luke 9:1-16 and `merge_parts`
    # writes them over the real chapter 9.
    body = list(head)
    for ch in chapters:
        body.append(u"## %s %d\n" % (g.book, ch))
        for key in sorted(k for k in out_v if k[0] == ch):
            body.append(u"%d %s" % (key[1], out_v[key]))
        body.append(u"")
    text = u"\n".join(body) + u"\n"

    print("")
    for ch in chapters:
        vv = sorted(k[1] for k in out_v if k[0] == ch)
        print("--- merge candidate: %s %d, verses %d-%d (%d) ---"
              % (g.book, ch, min(vv), max(vv), len(vv)))
    print("--- %d chars total ---" % len(text))
    for key in sorted(out_v)[:3]:
        print(u"%d %s" % (key[1], out_v[key][:110]))
    print("...")
    if not g.out:
        print("\n(no --out: nothing to write)")
        sys.exit(0)
    if not g.apply:
        print("\nDRY RUN - would write %s (%d verses). Re-run with --apply."
              % (g.out, len(out_v)))
        sys.exit(0)
    if os.path.exists(g.out):
        print("[X] %s exists - refusing to overwrite a part file" % g.out)
        sys.exit(1)
    io.open(g.out, "w", encoding="utf-8", newline="\n").write(text)
    print("\nwrote %s" % g.out)
    sys.exit(0)


if __name__ == "__main__":
    main()
