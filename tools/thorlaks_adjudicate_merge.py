#!/usr/bin/env python
"""Build ONE merge candidate from TWO (or THREE) independent reads plus adjudication.

THE 2-OF-3 VOTE (`--c`, owner's ruling 2026-09-17 16:40, item 3)
----------------------------------------------------------------
Given a third read, every site where C corroborates A or B is settled in PLAIN
CODE and never reaches an adjudicator; only a site where all THREE differ is
put to a reader. ⛔ Known-bad control: `HEXAPLA_NO_VOTE=1` disables the vote
and every one of those sites comes back adjudicable (`tools/test_majority_vote.py`
asserts both directions). ⚠ Without `--c` the two-read path is unchanged, byte
for byte - that is the other half of the control.


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


def _c_alignment(wa, wc):
    """Align a THIRD read's tokens onto read A's token indices.

    Read C is diffed against A (not against the A/B opcodes), so C's reading of
    an A-vs-B site is found by mapping that site's A span through this
    alignment. Returns `(per, at)`:
      * `per[i]` = the half-open C range standing in for A token `i`
        (None where C deleted it);
      * `at[i]` = the half-open C range C INSERTED before A token `i` - an
        A-empty site (B inserted a word there) still has a C reading, and
        without this it would read as C agreeing with A's emptiness.
    """
    na, nc = [norm(w) for w in wa], [norm(w) for w in wc]
    per = [None] * len(wa)
    at = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, na, nc).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                per[i1 + k] = (j1 + k, j1 + k + 1)
        elif tag == "insert":
            lo, hi = at.get(i1, (j1, j2))
            at[i1] = (min(lo, j1), max(hi, j2))
        else:                                   # replace / delete
            for i in range(i1, i2):
                per[i] = (j1, j2)
    return per, at


def _c_reading(wc, per, at, i1, i2):
    """What read C has where read A has tokens [i1, i2)."""
    lo = hi = None
    for i in range(i1, i2):
        if per[i] is None:
            continue
        lo = per[i][0] if lo is None else min(lo, per[i][0])
        hi = per[i][1] if hi is None else max(hi, per[i][1])
    for bnd in range(i1, i2 + 1) if i2 > i1 else (i1,):
        if bnd in at:
            blo, bhi = at[bnd]
            lo = blo if lo is None else min(lo, blo)
            hi = bhi if hi is None else max(hi, bhi)
    if lo is None:
        return ""                               # C reads nothing here
    return " ".join(wc[lo:hi])


def _njoin(ws):
    return " ".join(norm(w) for w in ws.split())


def _tally(settled):
    """`A+C 31, B+C 18, mixed 4` - every label, never a hard-coded pair."""
    counts = {}
    for s in settled:
        counts[s["vote"]] = counts.get(s["vote"], 0) + 1
    return ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts))


def _vote(sa, sb, sc):
    """The 2-of-3 wording for ONE site as `(text, vote)`, or None if unsettled.

    Whole span first; then, when the three spans carry the SAME token count,
    position by position. ⚠ That second pass is not a refinement - difflib
    cuts two ADJACENT disputed words into ONE site (`þr sagde` against
    `þeir fagde`), and a span-level vote alone sends such a site to a reader
    although every position in it is settled 2-of-3.

    ⛔ ONE position where all three reads differ voids the WHOLE site: the
    site is the unit a reader is asked about, and half a site cannot be
    briefed.
    """
    ja, jb, jc = " ".join(sa), " ".join(sb), " ".join(sc)
    na, nb, nc = _njoin(ja), _njoin(jb), _njoin(jc)
    if nc == na and nc != nb:
        return settle(prefer(ja, jc)), "A+C"
    if nc == nb and nc != na:
        return settle(prefer(jb, jc)), "B+C"
    if not sa or not (len(sa) == len(sb) == len(sc)):
        return None
    out, saw = [], set()
    for ta, tb, tc in zip(sa, sb, sc):
        xa, xb, xc = norm(ta), norm(tb), norm(tc)
        if xa == xb:
            out.append(settle(prefer(ta, tb)))
        elif xc == xa:
            out.append(settle(prefer(ta, tc)))
            saw.add("A+C")
        elif xc == xb:
            out.append(settle(prefer(tb, tc)))
            saw.add("B+C")
        else:
            return None
    if not saw:
        return None
    return " ".join(out), (saw.pop() if len(saw) == 1 else "mixed")


def sites(a, b, c=None):
    """Every disputed site, in the brief's order. ONE cut, used everywhere.

    With a THIRD read (`c`), every site where C corroborates one of the two
    reads is settled HERE, in plain code, and never reaches an adjudicator -
    item 3 of the owner's 2026-09-17 ruling. A settled site carries
    `majority` (the wording) and `vote` (`A+C` / `B+C`); `adjudicable()`
    excludes it. Only a site where all THREE differ is put to a reader.
    ⛔ Known-bad control: `HEXAPLA_NO_VOTE=1` disables the vote, and every
    2-of-3 site comes back adjudicable.
    """
    vote_off = os.environ.get("HEXAPLA_NO_VOTE") == "1"
    out = []
    for key in sorted(set(a) & set(b)):
        ch, v = key
        wa, wb = words(a[key]), words(b[key])
        na, nb = [norm(w) for w in wa], [norm(w) for w in wb]
        wc = words(c[key]) if (c and key in c) else None
        per, at = _c_alignment(wa, wc) if wc is not None else (None, None)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, na, nb).get_opcodes():
            ra, rb = " ".join(wa[i1:i2]), " ".join(wb[j1:j2])
            s = dict(chapter=ch, verse=v, key=key,
                     tag=tag, i1=i1, i2=i2, j1=j1, j2=j2,
                     a=ra, b=rb, c=None, majority=None, vote=None,
                     notation=(" ".join(na[i1:i2]) == " ".join(nb[j1:j2])))
            if wc is not None:
                s["c"] = _c_reading(wc, per, at, i1, i2)
                if tag != "equal" and not s["notation"] and not vote_off:
                    m = _vote(wa[i1:i2], wb[j1:j2], s["c"].split())
                    if m:
                        s["majority"], s["vote"] = m
            out.append(s)
    return out


def adjudicable(s):
    """The sites a reader was asked about - the brief's own exclusions."""
    if s["tag"] == "equal" or s["notation"]:
        return False
    # ★ Settled 2-of-3 by the third read, in plain code. ⛔ Never briefed:
    # asking a reader about a site two independent instruments already agree
    # on is the spend the vote exists to remove.
    if s.get("majority") is not None:
        return False
    if "[HN]" in s["a"] or "[HN]" in s["b"]:
        return False
    if "decorative initial" in s["a"] or "[OG]" in s["b"]:
        return False
    return True


def silent_defaults(all_sites):
    """Dropped sites that carry MORE THAN ONE WORD - the dangerous shape.

    ★ THE CHEAP GUARD for a bug that is NOT yet fixed. `adjudicable()` excludes
    a site because of ONE token in it - `[HN]`, a drop-cap, notation - but the
    exclusion is applied to the whole SPAN. `SequenceMatcher` emits one
    `replace` opcode when two ADJACENT words both differ, so an ordinary
    content dispute can be carried out of adjudication attached to a token the
    conventions really do settle, and the merge then hands the whole span to
    read B by default.

    Luke idx 63, 2026-09-19: four sites went this way, among them

        v18  A='[HN]ã sagde'      B='[HN]nñ fagde'   <- a long-s/f dispute
        v20  A='hvar Nōfn yðar'   B='ydar [HN]ofn'   <- and a WORD-ORDER one

    while every coverage instrument on the page reported 181/181 full coverage.
    ⛔ A coverage count only ever covers the sites the deriver knew about.

    This function CHANGES NOTHING here - it only names them, so a silent
    default becomes a named one.

    ✅ SINCE 2026-09-21 these are BRIEFED (owner's word). `thorlaks_adjudicate_
    brief.py` asks about this exact list, and the verdict-override path below
    applies the answers in place of the read-B default. ⛔ Site DERIVATION was
    deliberately NOT changed - splitting the opcode would have moved the site
    keys on every page and orphaned every verdict file on disk. So a span
    verdict is OPTIONAL to this tool and MANDATORY to the reader, and the
    warning below still fires for any span that came back unanswered.
    ⛔ Known-bad control: `HEXAPLA_NO_SPANBRIEF=1` (in the brief tool) stops
    them being briefed; `tools/test_span_brief.py` asserts both ways.
    ▶ research/_evidence/thorlaks_hn_exclusion_swallows_neighbours_2026-09-19.md
    ▶ research/_evidence/thorlaks_span_sites_briefed_2026-09-21.md
    """
    out = []
    for s in all_sites:
        if s["tag"] == "equal" or adjudicable(s):
            continue
        if s.get("majority") is not None:
            continue          # the vote decided it; not a silent default
        if len(s["a"].split()) > 1 or len(s["b"].split()) > 1:
            out.append(s)
    return out


VERDICT_RE = re.compile(
    r"^\s*(?P<addr>line[\d\-line]*)\s*\|\s*v(?P<verse>\d{1,3})\s*\|\s*"
    r"A=(?P<a>.*?)\s*\|\s*B=(?P<b>.*?)\s*\|\s*VERDICT:\s*(?P<verdict>.*?)"
    r"(?:\s*\|\s*conf:\s*(?P<conf>.*?))?\s*$")


def _lines_of(addr):
    """Every crop line an address covers. `line13-line15` -> [13, 14, 15]."""
    ns = [int(x) for x in re.findall(r"line(\d{1,3})", addr or "")]
    return list(range(min(ns), max(ns) + 1)) if ns else []


def line_chapters(*addr_maps):
    """{crop line: the chapter printed on it} - ambiguous lines OMITTED.

    A page can print the same verse number in TWO chapters (idx 67 carries
    Luke 13:10 and Luke 14:10), and a verdict line keys its site by `v10`
    alone: the brief writes no chapter. Its `lineNN` is what disambiguates,
    because both reads address every verse to the crop line it opens on.

    ⛔ A line that BOTH chapters claim (the seam line, where one chapter ends
    and the next opens) is dropped, not guessed. An unresolvable verdict then
    refuses the run by name instead of being filed under the wrong chapter.
    """
    ch_of, ambiguous = {}, set()
    for m in addr_maps:
        for (ch, _v), a in (m or {}).items():
            for ln in _lines_of(a):
                if ch_of.get(ln, ch) != ch:
                    ambiguous.add(ln)
                ch_of[ln] = ch
    for ln in ambiguous:
        ch_of.pop(ln, None)
    return ch_of


def chapter_resolver(keys, ch_of):
    """`(verse, addr) -> chapter`, or None where the address cannot settle it.

    ⛔ A verse number that occurs in only ONE chapter on the page resolves by
    the verse ALONE and never consults the address. That is deliberate: every
    page without such a collision keys exactly as it did before this fix, so
    its merge output is byte-identical.
    ⚠ Known-bad control: `HEXAPLA_NO_CHAPKEY=1` restores the old verse-only
    key, and a page with a collision mis-files the second chapter's verdicts.
    `tools/test_adjudicate_chapter_key.py` asserts both directions.
    """
    by_verse = {}
    for ch, v in keys:
        by_verse.setdefault(v, []).append(ch)
    off = os.environ.get("HEXAPLA_NO_CHAPKEY") == "1"

    def resolve(verse, addr):
        chs = sorted(set(by_verse.get(verse, [])))
        if not chs:
            return None
        if len(chs) == 1:
            return chs[0]
        if off:
            return chs[0]           # the old behaviour: first chapter wins
        cand = set(ch_of[ln] for ln in _lines_of(addr) if ln in ch_of) & set(chs)
        return cand.pop() if len(cand) == 1 else None

    return resolve


def parse_verdicts(path, resolve):
    got = {}
    bad = []
    unkeyed = []
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
        # ⚠ KEYED BY OCCURRENCE, not by (chapter, verse, A, B): a verse can
        # carry the SAME dispute twice (idx 61 v7 has two `[uncertain glyph]`/
        # `á` sites, v14 two `fimtig'`/`fimtig`). Keyed by content alone, the
        # second verdict silently REPLACED the first and 119 lines parsed as 117.
        # ⚠ The CHAPTER comes from the line address, not from the verdict line:
        # see `chapter_resolver`.
        ch = resolve(int(d["verse"]), d["addr"])
        if ch is None:
            unkeyed.append(line.strip())
            continue
        k = (ch, int(d["verse"]), d["a"].strip(), d["b"].strip())
        n = sum(1 for key in got if key[:4] == k)
        got[k + (n,)] = dict(verdict=(d["verdict"] or "").strip(),
                             conf=(d["conf"] or "").strip(), raw=line.strip())
    return got, bad, unkeyed


def lenient(t):
    """A site's A=/B= text with what adjudicators rewrite when COPYING it
    folded away: a combining mark (`hn̄` copied as `hñ`), `[?]`, trailing
    punctuation, spacing. Luke idx 70 (3 sites) and idx 72 (1) refused with
    every verdict written - the copy differed from the site by one of these."""
    import unicodedata
    t = unicodedata.normalize("NFD", t or "")
    t = u"".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("[?]", "")
    t = re.sub(r"[.,;:!?/]+(\s|$)", r"\1", t)
    return " ".join(t.split())


def lenient_pass(missing, got, used):
    """Match each still-missing site to an UNUSED verdict of the same
    (chapter, verse) by the lenient key. Both sides equal leniently, or - when
    exactly one site and one verdict are left over in that verse - one side.
    Anything ambiguous stays missing. Returns (matched [(site_key, got_key,
    how)], still_missing)."""
    left = [k for k in got if k not in used]
    matched, still = [], []
    for key in missing:
        ch, v, sa, sb = key[:4]
        pool = [k for k in left if k[:2] == (ch, v)]
        both = [k for k in pool
                if lenient(k[2]) == lenient(sa) and lenient(k[3]) == lenient(sb)]
        how = "A and B equal once folded"
        if len(both) != 1:
            miss_here = [m for m in missing if m[:2] == (ch, v)]
            one = [k for k in pool if lenient(k[2]) == lenient(sa)
                   or lenient(k[3]) == lenient(sb)]
            both = one if (len(pool) == 1 and len(miss_here) == 1
                           and len(one) == 1) else []
            how = "one side equal, the verse's only leftover site and verdict"
        if len(both) == 1:
            matched.append((key, both[0], how))
            left.remove(both[0])
        else:
            still.append(key)
    return matched, still


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
    ap.add_argument("--c", help="read 3 (OPTIONAL). Given, every site where it "
                                "corroborates read 1 or read 2 is settled 2-of-3 "
                                "in code and is never adjudicated")
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--page", required=True)
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true")
    g = ap.parse_args()

    a, _ = verses_with_addr(g.a, g.chapter)
    b, addr = verses_with_addr(g.b, g.chapter)
    c = None
    if g.c:
        c, _ = verses_with_addr(g.c, g.chapter)
        # ⛔ A third read that does not carry the same verses is a STRUCTURAL
        # disagreement, not a vote. Nothing is written on it.
        if sorted(c) != sorted(a):
            print("[X] read 3 does not carry the same (chapter, verse) keys as "
                  "read 1: only in C %s / missing from C %s. NOTHING WRITTEN."
                  % (sorted(set(c) - set(a)), sorted(set(a) - set(c))))
            sys.exit(1)
    if sorted(a) != sorted(b):
        print("[X] the two reads do not carry the same (chapter, verse) keys: "
              "only in A %s / only in B %s"
              % (sorted(set(a) - set(b)), sorted(set(b) - set(a))))
        sys.exit(1)
    chapters = sorted(set(ch for ch, _ in a))
    print("chapters on this page            : %s"
          % ", ".join(str(c) for c in chapters))
    # ⚠ The verdict lines key a site by `v<N>` ALONE (the brief writes no
    # chapter). Where a verse number occurs in TWO chapters of the same page
    # (idx 67: Luke 13:10 and 14:10) the site is keyed by (chapter, verse),
    # and the chapter is read off the verdict's own `lineNN`.
    _, addr_a = verses_with_addr(g.a, g.chapter)
    ch_of = line_chapters(addr, addr_a)
    resolve = chapter_resolver(sorted(a), ch_of)
    dupes = sorted(v for v in set(v for _, v in a)
                   if sum(1 for _, w in a if w == v) > 1)
    if dupes:
        print("verse numbers printed twice      : %s  (keyed by (chapter, "
              "verse) from each verdict's lineNN)"
              % ", ".join(str(v) for v in dupes))

    all_sites = sites(a, b, c)
    need = [s for s in all_sites if adjudicable(s)]
    settled = [s for s in all_sites if s.get("majority") is not None]
    got, bad, unkeyed = parse_verdicts(g.verdicts, resolve)
    if c is not None:
        disputed = len([s for s in all_sites
                        if s["tag"] != "equal" and not s["notation"]])
        print("reads                            : 3 (2-of-3 vote ACTIVE%s)"
              % ("" if os.environ.get("HEXAPLA_NO_VOTE") != "1"
                 else " - DISABLED by HEXAPLA_NO_VOTE=1"))
        print("disputed sites before the vote   : %d" % disputed)
        print("settled 2-of-3 in code           : %d  (%s)"
              % (len(settled), _tally(settled) or "none"))
    print("sites derived from the two reads : %d" % len(need))
    quiet = silent_defaults(all_sites)
    print("dropped, never briefed           : %d  (of these, %d carry MORE "
          "THAN ONE WORD)"
          % (len([s for s in all_sites
                  if s["tag"] != "equal" and not adjudicable(s)
                  and s.get("majority") is None]), len(quiet)))
    # ⚠ The list of these is printed AFTER the verdict pass below, not here:
    # a site with an explicit verdict is NOT about to be defaulted, and an
    # instrument that says it is would be lying about its own output.
    print("verdict lines parsed             : %d%s"
          % (len(got), "  (%d unparsable)" % len(bad) if bad else ""))
    for l in bad[:5]:
        print("    ? %s" % l[:100])
    if unkeyed:
        # ⛔ Not a warning. A verdict whose chapter the address cannot settle
        # would be filed under a guess; the site it answers then reads as
        # unanswered and the run refuses below anyway - but by the wrong name.
        print("[X] %d verdict line(s) carry a verse number printed in two "
              "chapters on this page and an address that does not settle "
              "which. NOTHING WRITTEN." % len(unkeyed))
        for l in unkeyed[:10]:
            print("    unkeyed  %s" % l[:100])
        sys.exit(1)

    missing, unusable, resolved = [], [], {}
    used, site_of = set(), {}
    seen = {}
    for s in need:
        base = (s["chapter"], s["verse"], s["a"], s["b"])
        n = seen.get(base, 0)
        seen[base] = n + 1
        key = base + (n,)
        v = got.get(key)
        if not v:
            missing.append(key)
            site_of[key] = s
            continue
        used.add(key)
        text, why = choose(s, v)
        if text is None:
            unusable.append((key, why))
            continue
        resolved[id(s)] = text

    # ★ AN EXPLICIT VERDICT OUTRANKS THE READ-B DEFAULT.
    # A site `adjudicable()` dropped is normally settled by convention (read B).
    # That is right for the `[HN]` token itself and wrong for a content word
    # that got dropped ALONGSIDE it - see silent_defaults() above. This is the
    # door: if someone has actually LOOKED at a dropped site and written a
    # verdict line for it, that verdict is used instead of the default.
    # ✅ Since 2026-09-21 the brief ASKS about those spans, so this path is the
    #    normal one rather than the exception - but it is still the only thing
    #    that changed. ⛔ This does NOT change which sites are DERIVED on any
    #    page. Where no span verdict was written the output is byte-identical,
    #    so every verdict file already on disk still keys against the same sites.
    # ⚠ Known-bad control: HEXAPLA_NO_VERDICT_OVERRIDE=1 restores the blind
    #    read-B default, and idx 63 reverts to `[HN]nñ fagde` / `[HN]u` / `G hñ`.
    overridden = []
    if os.environ.get("HEXAPLA_NO_VERDICT_OVERRIDE") != "1":
        seen_d = {}
        for s in silent_defaults(all_sites):
            base = (s["chapter"], s["verse"], s["a"], s["b"])
            n = seen_d.get(base, 0)
            seen_d[base] = n + 1
            v = got.get(base + (n,))
            if not v:
                continue
            used.add(base + (n,))
            text, why = choose(s, v)
            if text is None:
                unusable.append((base + (n,), why))
                continue
            resolved[id(s)] = text
            overridden.append((s, text))
    if overridden:
        print("verdicts applied to dropped sites: %d  "
              "(an explicit verdict outranks the read-B default)"
              % len(overridden))
        for s, text in overridden:
            print("      v%-4s A=%-24s B=%-24s -> %s"
                  % (s["verse"], s["a"][:24], s["b"][:24], text[:34]))
    still = [s for s in quiet if id(s) not in resolved]
    if still:
        # ⛔ Loud on purpose. Each of these is about to be settled by the
        # read-B default with no vote, no verdict and no findings line.
        print("  ⚠ %d MULTI-WORD SITE(S) WILL BE SETTLED BY THE READ-B "
              "DEFAULT, UNEXAMINED:" % len(still))
        # ⛔ NOT truncated. This print is the only place a span about to be
        # taken by the read-B default is shown, and it is shown BECAUSE it may
        # hide a content dispute - cutting it at 28 characters hides exactly
        # the thing the warning exists to surface. Luke idx 67 v34's span is
        # 68 characters and the dispute (`s[?]ter` vs `sier`) sits at its END.
        # It is also the exact text a verdict line must carry to override the
        # default, so it has to be copyable.
        for s in still:
            print(u"      %d:%-4s A=%s" % (s["chapter"], s["verse"], s["a"]))
            print(u"                B=%s" % s["b"])
        print("  ▶ A dropped site carrying one word is notation and fine. One "
              "carrying several\n    can hide an ordinary content dispute - "
              "read them before you trust this merge.")

    # ★ A verdict whose A=/B= copy differs from its site only by what
    # `lenient()` folds is that site's verdict. Runs ONLY on sites that would
    # otherwise refuse, so every page that merged before is byte-identical.
    # Each match is printed - it is a claim, and it is checkable.
    # ⚠ Known-bad control: HEXAPLA_NO_LENIENT_KEY=1 -> idx 70/72 refuse again.
    if missing and os.environ.get("HEXAPLA_NO_LENIENT_KEY") != "1":
        matched, missing = lenient_pass(missing, got, used)
        if matched:
            print("verdicts matched by lenient key  : %d" % len(matched))
        for key, gk, how in matched:
            print(u"      %d:%-4s site A=%s | B=%s" % (key[0], key[1], key[2], key[3]))
            print(u"             verdict A=%s | B=%s  (%s)" % (gk[2], gk[3], how))
            text, why = choose(site_of[key], got[gk])
            if text is None:
                unusable.append((key, why))
                continue
            resolved[id(site_of[key])] = text

    if missing or unusable:
        print("[X] %d site(s) with NO verdict, %d unusable - NOTHING WRITTEN"
              % (len(missing), len(unusable)))
        for k in missing[:10]:
            print("    missing  %d:%-3d A=%s | B=%s"
                  % (k[0], k[1], k[2][:30], k[3][:30]))
        for k, why in unusable[:10]:
            print("    unusable %d:%-3d %s" % (k[0], k[1], why))
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
            elif s.get("majority") is not None:
                # ★ Two of three independent reads carry this wording. ⛔ This
                # branch must stand BEFORE the notation branch below - a
                # majority site is `adjudicable() == False` and would otherwise
                # be handed to read B's spelling with no vote consulted.
                pieces.append(s["majority"])
            elif id(s) in resolved:
                # ★ Someone LOOKED at this dropped site and wrote a verdict.
                # ⛔ Must stand before the notation branch, for the same reason
                # the majority branch does: otherwise the default silently
                # overwrites a verdict that exists.
                pieces.append(resolved[id(s)])
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
    ]
    if c is not None:
        head += [
            u"- THIRD read `%s`: %d site(s) settled 2-of-3 in plain code"
            % (os.path.basename(g.c), len(settled)),
            u"  (%s) and never put to an adjudicator."
            % (_tally(settled) or "none"),
        ]
    head += [
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

    # ⛔ DUPLICATION GATE (2026-09-21, Luke 14:1). A verse is rebuilt by
    # appending one piece per site IN ORDER. Two ADJACENT sites can carry
    # verdict TEXTS that overlap -- a delete-site whose NEITHER verdict supplied
    # `þ° framme` beside a replace-site whose B verdict supplied `framme þ hm̄.`
    # -- and both pieces get appended, writing `framme þ` twice. Nothing checked.
    # ⛔ `thorlaks_verse_length_witness.py` CANNOT catch this: it flags only
    # ratio < med*FLOOR and has NO UPPER BOUND, so a LONGER verse never trips it.
    # This gate fires on the DRY RUN too -- the candidate is the place to stop it.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from thorlaks_dup_screen import dup_bigrams as _dup, enabled as _dup_on
    except ImportError:
        _dup = _dup_on = None
    if _dup is not None and _dup_on():
        dups = []
        for key in sorted(out_v):
            for snip in _dup(out_v[key]):
                dups.append((key[0], key[1], snip))
        if dups:
            print("")
            print("[X] DUPLICATED TEXT in the merge candidate - refusing to write:")
            for ch, v, snip in dups:
                print(u"    %s %d:%d  «%s»" % (g.book, ch, v, snip))
            print("  Two ADJACENT sites' verdict TEXTS overlap and both were appended.")
            print(u"  ⚠ Scripture DOES repeat («Gud miñ Gud miñ» = Mark 15:34,")
            print("     Matthew 27:46 is the real text) - so this is a QUESTION.")
            print("  ▶ Confirm against the CROP, then override: HEXAPLA_NO_DUPCHK=1")
            print("  ⛔ NEVER edit a verdict line or a read to satisfy this gate.")
            sys.exit(1)

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
