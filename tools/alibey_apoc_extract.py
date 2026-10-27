# -*- coding: utf-8 -*-
"""Extract the 1665 Ali Bey apocrypha TRANSLITERATION (Kadir Akın) from the
text layer of `apokrafi.pdf` into an event stream - no vision, 0 tokens.

    python tools/alibey_apoc_extract.py --pdf <apokrafi.pdf> --out <events.jsonl>

⛔ LICENCE: page 2 reserves all rights to Kadir Akın (written permission, a
100-sentence quotation cap). Owner 2026-09-25: build it and credit it, do NOT
ship it until the permission answer is reported
(research/_evidence/osmkelam_permission_2026-09-25.md). The output of this
script and of build_tr_alibey_apoc.py stays under _work/ until then.

## The page layout (probed 2026-09-25, PDF from hakikat.net/indir/apokrafi.pdf)
- Printed page number == PDF page number. Even pages are the 1665 clean-copy
  facsimile (text layer = running head only); odd pages carry ONE text column
  at x < 240 with the 1664 draft facsimile beside it.
- In that column every verse appears twice, stacked: the 1665 transliteration
  set UPRIGHT (TimesNewRomanPSMT 10 pt), then Akın's modern-Turkish revision
  set ITALIC. Both open with «N*» (bold only sometimes, so a verse is
  any line opening «N*»). Headings (book title, «… Bâb») are
  bold lines. Footnotes are 8-9 pt and dropped. A LucidaCalligraphy letter is
  a decorative initial - kept.
- ⚠ QuarkXPress left ZERO-ADVANCE spaces inside words at its hyphenation
  points («pâ dişâhlığınıŋ»): the next glyph starts where the space does
  (gap = -space width, measured -2.5 pt), while a real space advances
  (gap >= 0). Spaces are judged by that geometry, never by the text.
- A line-final «-» is a line-break hyphen and is joined, except before an
  izafet vowel («Kuds-» + «i») where the hyphen is the text's own.
- «∞» marks the end of a facsimile page in the transcription - dropped.
- «word*» is a footnote call - the asterisk is dropped.

Events (one JSON object per line): {"p": page, "k": kind, "t": text}
  kind = "head" (bold heading line) | "v" (a transliteration verse: "n" = its
  number, "t" = its text) | "run" (running head of an odd page) | "note"
  (editorial note: a marked line or a side box, never verse text) | "catch"
  (facsimile catchword) | "stray" (unnumbered text with no open verse - a
  subtitle, or LOST TEXT: read every one) | "colophon" (Ali Bey's own
  «… tamam oldu», cut out of the book's last verse).
Screen: `python tools/alibey_apoc_screen.py` (rc 1 = editorial matter left).
Known-bad controls (each must make the screen worse): HEXAPLA_ALIBEY_YSORT=1,
HEXAPLA_ALIBEY_BOLDHEAD=1, HEXAPLA_ALIBEY_NOSIDE=1, HEXAPLA_ALIBEY_NOFIX=1.
The modern-Turkish layer is counted per verse ("mod" = 1 when the verse has
its italic twin) so a verse whose twin is missing is visible, but its text is
not kept.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import fitz

COL_X = 240.0
SIDE_X = 200.0
# A side box opening with a note mark: «*», «**», «+», «++», «[?]», «(+)»,
# «[+]» - but not a verse number «N*» / «[N]*».
SIDE_NOTE = re.compile(r"^(\*+|\++|\[\?\]|\(\+\)|\[\+\])")
SIDE_NOTE_WORDS = re.compile(
    r"(?i)bkz|etiyopça|almancası|arapça|süryanice|latince|grekçe|versiyon|"
    r"karşılaştırın|yukarıdaki|el yazısında|el yazması")
BODY_MIN, BODY_MAX = 9.6, 10.6
# Pages set off the 10 pt body (size survey of p9-p1935, 2026-09-26: the ONLY
# scripture outside the band). p797 is set in 12 pt: Sirach 51:37's tail,
# 51:38 and 51:39 were lost and the next body text glued onto 51:37. Its
# column ends at the colophon «eklesiyâstikus tamam oldu» (y 148.4), which is
# apparatus. p799 is Baruch's title page (all 12 pt, 1:1 repeated at body size
# on p801) whose one 10 pt block is a modern caption «Alttaki resim … biridir:»;
# it carries no scripture. HEXAPLA_ALIBEY_NO797=1 = old behaviour (the control).
_OLD797 = os.environ.get("HEXAPLA_ALIBEY_NO797") == "1"
PAGE_BODY = {} if _OLD797 else {797: (11.6, 12.4, 145.0)}  # page -> (min, max, column end y)
PAGE_SKIP = set() if _OLD797 else {799}
FIRST, LAST = 9, 1935  # the apocrypha, per the contents page (p3)
# Known-bad control: HEXAPLA_ALIBEY_HEAD22=1 restores the old cut (4 verses
# lose their opening; the build's hole count rises).
HEAD_Y = 22.0 if os.environ.get("HEXAPLA_ALIBEY_HEAD22") == "1" else 18.0


def classify(font):
    f = font.lower()
    if "bold" in f:
        return "B"
    if "ital" in f and "lucida" not in f:
        return "I"
    return "R"


def page_lines(pg):
    """The text column's body lines: [(y, [(char, cls)...])] in reading order,
    with zero-advance spaces removed."""
    pno = pg.number + 1
    if pno in PAGE_SKIP:
        return []
    lo, hi, end_y = PAGE_BODY.get(pno, (BODY_MIN, BODY_MAX, 1e9))
    rd = pg.get_text("rawdict")
    lines = []
    for bi, bl in enumerate(rd["blocks"]):
        for li, ln in enumerate(bl.get("lines", [])):
            if ln["bbox"][1] > end_y:
                continue
            chars = []
            for sp in ln["spans"]:
                if not (lo <= sp["size"] <= hi):
                    continue
                if "floralia" in sp["font"].lower() or "arial" in sp["font"].lower():
                    continue
                cls = classify(sp["font"])
                for c in sp["chars"]:
                    chars.append((c["c"], cls, c["bbox"]))
            if not chars:
                continue
            x0 = min(c[2][0] for c in chars)
            y0 = ln["bbox"][1]
            # Running heads sit at y <= 11.7. A threshold of 22 dropped a
            # column's FIRST line when it sat at y 21.6 (p667 «27*Cemiʾ
            # masâlıhıŋda…»): the verse lost its numeral and opening and its
            # tail was glued onto the previous verse (Sirach 33:27, 1 Macc
            # 1:50, 2 Macc 12:12, 2 Esdras 7:31). HEAD_Y is the cut.
            if x0 >= COL_X or y0 < HEAD_Y:  # facsimile side / running head
                continue
            out = []
            for i, (ch, cls, bb) in enumerate(chars):
                if ch == " ":
                    nxt = chars[i + 1] if i + 1 < len(chars) else None
                    if nxt is None:
                        continue
                    if nxt[2][0] < bb[0] + 0.5 * (bb[2] - bb[0]):
                        continue  # zero-advance: not a word break
                out.append((ch, cls))
            lines.append(((bi, li), round(y0, 1), x0, out))
    # SIDE BOXES (x >= SIDE_X, beside the facsimile) hold three things: the
    # column's own overflow (verse text - kept), the facsimile's CATCHWORD (one
    # short line ending «∞», e.g. p803 «ve onlara ∞», which the next page
    # repeats: it doubled «ve onlara ve onlara»), and EDITORIAL NOTES set in the
    # body face and size («*bkz. Ali Bey'in 1664 el yazısında…», «+II.Grekçe
    # çeviride…», «Yukarıdaki 13. ayet alta eklenmiştir.»), which merged into
    # the open verse. Style cannot tell them apart; the box can. Tag per box.
    # HEXAPLA_ALIBEY_NOSIDE=1 = old behaviour (known-bad control).
    tags = {}
    if os.environ.get("HEXAPLA_ALIBEY_NOSIDE") != "1":
        boxes = {}
        for (bi, li), y, x, out in lines:
            boxes.setdefault(bi, []).append((li, y, x, "".join(c for c, _ in out)))
        for bi, ls in boxes.items():
            ls.sort()
            first, whole = ls[0][3].strip(), " ".join(l[3] for l in ls).strip()
            # A note MARK opens a note box anywhere (p1749's «*2 Orjinal Grekçe
            # versiyonu…» is a box in the column itself); note WORDS only on
            # the side, where verse text never carries them.
            if SIDE_NOTE.search(first) and not VERSE.match(first):
                tags[bi] = "note"
                continue
            if min(l[2] for l in ls) < SIDE_X:
                continue
            if SIDE_NOTE_WORDS.search(whole):
                tags[bi] = "note"
            elif (len(ls) == 1 and whole.endswith("∞")
                  and len(whole.rstrip("∞ ").split()) <= 3 and ls[0][1] > 40):
                tags[bi] = "catch"
    # READING ORDER = the layout's own block/line order, never y. Two boxes can
    # share a y: p113's continuation box (modern v23, y 34.0) sorted by y into
    # the transliteration's v16 (y 33.3); p1411's overflow box and its bold
    # footnote term «Fĩçı:» interleaved with the column's first lines, so every
    # line from v19 on was «stray». HEXAPLA_ALIBEY_YSORT=1 restores the old
    # sort (the known-bad control).
    if os.environ.get("HEXAPLA_ALIBEY_YSORT") == "1":
        lines.sort(key=lambda l: (l[1], l[2]))
    else:
        lines.sort(key=lambda l: l[0])
    return [(y, o, tags.get(k[0])) for k, y, _x, o in lines]


def running_head(pg):
    for bl in pg.get_text("dict")["blocks"]:
        for ln in bl.get("lines", []):
            if ln["bbox"][1] < HEAD_Y:
                t = "".join(s["text"] for s in ln["spans"]).strip()
                if t and not t.isdigit():
                    return t
    return ""


# «N*», and «(N)*» in a few passages (Wisdom 9, Solomon's prayer).
# Esther's additions number «(N)[*]» (p1667, p1715).
# «[N]*» (53 lines): a verse the editor SUPPLIED from the 1664 draft (p213
# «[11]*…», with a note «[11]*11. Ayet 1665 temiz kopyasında unutulmuş…» that
# is NOT verse text). «29[28]*» (p1547): the manuscript's number, then the
# standard one in brackets - n is the manuscript's, «alt» kept. «1(4)*» (p361)
# and «23(4)*» (p619): a misprinted number with the editor's digit in
# parentheses; the italic twin carries the intended one (14, 24) and wins.
# Before 2026-09-25 none of these matched, and each verse ran into the one
# before it (p213 v10 «…olayım [11]Hükümde…»).
VERSE = re.compile(r"^\(?\[?(?P<n>\d+)\]?\)?(?:(?P<ak>[(\[])(?P<alt>\d+) ?[)\]])?"
                   r"(?:\*|\[\*\])\s*")
VERSE_NOTE = re.compile(r"^\d+\. [Aa]yet")
# An editorial NOTE opens with a marker - «[Not]», «[+]», «(+)», or a bold
# footnote term alone on its line («Fĩçı:») - and runs until the next verse or
# heading. Its lines are never verse text (p1715's «[+]:(Önemli Not)Almanca
# Martin Luther…» would otherwise merge into the open verse), and it does not
# close the open verse: p1411's «Fĩçı:» sits after v25, which continues on p1413.
# A catchword: the manuscript's next-page cue, «5 zîrâ ∞», repeated on the
# next page as the verse's own opening. Dropped.
CATCH = re.compile(r"^\d+ \S+( \S+)? ∞\s*$")


# Editorial matter the text layer sets INSIDE a verse. Owner 2026-09-25: «the
# authentic way - if the original didn't have them, take them out». Each site
# is named (page, verse, marker) and must match exactly once, so a changed PDF
# fails loudly instead of cutting the wrong words. HEXAPLA_ALIBEY_NOFIX=1 skips
# all of it (known-bad control: the screen must get worse).
# Ali Bey's own colophon: cut from the verse, kept as a «colophon» event.
COLOPHON = [(435, 24, "Kitab-ı Tobit tamam oldu"),
            (1935, 20, "Şemʿon yaʿnî Makâbbî sâlis tamâm oldu (1665)")]
# An editor's note that shares the verse's box: the verse ends at the mark.
NOTE_CUT = [(1585, 19, "Etiyopçası"), (1587, 29, "(3)II."), (1661, 69, "(1)")]
# Editor's supplements in parentheses, not in the 1665 hand: dropped.
# p601 «p(A.S.)» is a line of its own under the verse, absent from the modern
# twin («… miras al.»): the «p» goes with it.
EDITOR = [(287, 5, "(Ki)"), (507, 18, "(ve onları)"), (601, 9, "p(A.S.)"),
          (723, 22, "(an)"), (1731, 24, "(dokuz)")]
# «(13?)» = the editor's guess at a verse boundary the hand does not number.
QSPLIT = re.compile(r"\s*\((\d+)\?\)\s*")
# ...and its guess is one too high: on p277 the modern twins of «(13?)» and
# «(14?)» are 12 and 13, «(14*)» follows as 14, and KJV Wisdom 14:12 «the
# devising of idols» / 14:13 «neither were they from the beginning» agree.
QSPLIT_N = {(275, 11): [12, 13]}
# Uncertainty and addition marks: «[?]», «(?)», «[+]».
MARKS = re.compile(r"\s*(\[\?\]|\(\?\)|\[\+\])\s*")


def editorial_fixes(events):
    if os.environ.get("HEXAPLA_ALIBEY_NOFIX") == "1":
        return events
    at = {(e["p"], e["n"]): e for e in events if e["k"] == "v"}

    def site(p, n, marker):
        e = at.get((p, n))
        if e is None or e["t"].count(marker) != 1:
            raise SystemExit(f"⛔ editorial site p{p} v{n} {marker!r}: "
                             f"{'no such verse' if e is None else str(e['t'].count(marker)) + ' matches'}")
        return e

    out_extra = {}
    for p, n, mk in COLOPHON:
        e = site(p, n, mk)
        i = e["t"].index(mk)
        out_extra[id(e)] = {"p": p, "k": "colophon", "t": e["t"][i:]}
        e["t"] = e["t"][:i].rstrip()
    for p, n, mk in NOTE_CUT:
        e = site(p, n, mk)
        e["t"] = e["t"][:e["t"].index(mk)].rstrip()
    for p, n, mk in EDITOR:
        e = site(p, n, mk)
        e["t"] = re.sub(r"\s+", " ", e["t"].replace(mk, " ")).strip()
    res = []
    for e in events:
        if e["k"] != "v":
            res.append(e)
            continue
        e["t"] = MARKS.sub(" ", e["t"]).strip()
        pieces = QSPLIT.split(e["t"])
        e["t"] = pieces[0].strip()
        res.append(e)
        if len(pieces) > 1:
            nums = QSPLIT_N.get((e["p"], e["n"]))
            if nums is None or len(nums) != len(pieces) // 2:
                raise SystemExit(f"⛔ «(N?)» split at p{e['p']} v{e['n']} has no ruled numbering")
            for j, n in zip(range(1, len(pieces), 2), nums):
                res.append({"p": e["p"], "k": "v", "n": n, "n_printed": f"({pieces[j]}?)",
                            "mod": 1, "t": pieces[j + 1].strip()})
        if id(e) in out_extra:
            res.append(out_extra[id(e)])
    return renumber(res)


def renumber(events):
    """Verse order within a book section (reset at every heading): a numeral
    that breaks the run is repaired from the modern twin, and a «verse» with
    no letters (p591's trailing «(33*):») is dropped. Each change is kept on
    the event («n_printed», «merged»).

    A numeral printed TWICE is one of two things, told apart by the text:
    - a page-turn CATCHWORD (p1719 «14*Batlomyos ∞», p1721 «14*Batlomyos ve
      Kelopâtra…»): the next piece opens with the first one's words, so the
      first is dropped - ONE verse, no doubled word;
    - two DIFFERENT verses under one numeral, in both layers (p317 «(13)» and
      p319 «13» = KJV Wisdom 17:13 and 17:14; p1547 «31[30]» and «[31]»,
      p1549 «[36]» and «[36](?)» = KJV 2 Esdras 8:32/33 and 8:38/39): the
      second gets the next number and the rest of the chapter follows BY
      POSITION (printed value kept in «n_printed»). A first version glued
      these into one verse. HEXAPLA_ALIBEY_GLUEDUP=1 restores that (control).
    """
    glue = os.environ.get("HEXAPLA_ALIBEY_GLUEDUP") == "1"
    res, prev, shift = [], None, 0
    for e in events:
        if e["k"] == "head":
            prev, shift = None, 0
        if e["k"] != "v":
            res.append(e)
            continue
        e["t"] = re.sub(r"^[)\]:;,.\s]+", "", e["t"])
        if not re.search(r"\w", e["t"]):
            continue
        if e["n"] == 1:
            shift = 0
        elif shift and not glue:
            e.setdefault("n_printed", e["n"])
            e["n"] += shift
            if "mod_n" in e:
                e["mod_n"] += shift
        if prev is not None:
            want = prev["n"] + 1
            if e["n"] != want and e.get("mod_n") == want and e["n"] != prev["n"]:
                e.setdefault("n_printed", e["n"] - shift)
                e["n"] = want  # p477 «4», p1511 «6», p1585 «0», p1549 «[30]»
            elif e["n"] == prev["n"] and glue:
                if not (e.get("mod_n", e["n"]) == e["n"]
                        and not e.get("alt") and not prev.get("alt")):
                    res.append(e)
                    prev = e
                    continue
                prev["t"] = (prev["t"] + " " + e["t"]).strip()
                prev["merged"] = prev.get("merged", 0) + 1
                continue
            elif e["n"] == prev["n"]:
                pw = prev["t"].split()
                if len(pw) <= 3 and e["t"].split()[:len(pw)] == pw:
                    e["merged"] = 1  # catchword: keep the full piece only
                    res[res.index(prev)] = e
                    prev = e
                    continue
                e.setdefault("n_printed", e["n"] - shift)
                e["n"] = want
                shift += 1
        res.append(e)
        prev = e
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default="C:/Projects/Hexapla-releases/_work/osm_cache/alibey1665_apoc/akin_apokrafi.pdf")
    ap.add_argument("--out", default="C:/Projects/Hexapla-releases/_work/alibey_apoc/events.jsonl")
    ap.add_argument("--first", type=int, default=FIRST)
    ap.add_argument("--last", type=int, default=LAST)
    a = ap.parse_args()
    doc = fitz.open(a.pdf)
    if doc.page_count != 2000:
        print(f"⛔ expected the 2000-page 2019 PDF, got {doc.page_count} pages")
        return 2
    events = []
    # One open verse PER LAYER: a verse that crosses a page break continues on
    # the next page with no number, the transliteration's tail first, then the
    # modern tail - so an unnumbered line belongs to the last verse of its OWN
    # layer, never simply to the last verse seen.
    last = {"R": None, "I": None}

    def clean(parts):
        txt = " ".join(parts)
        # Join line-break hyphens (izafet hyphens survive), drop ∞ and footnote calls.
        txt = re.sub(r"-\s*(?=[iıuü])", "-", txt)
        txt = re.sub(r"\s*-\s*", "", txt)
        txt = txt.replace("", " ")
        # Whitespace collapsed BEFORE the repeat rules: a line break left two
        # spaces and «ve  gözleriŋ ∞ ve gözleriŋ» (p1891 v31) never matched.
        txt = re.sub(r"[ \t]+", " ", txt)
        # A PAGE TURN (\x02) repeats the words before it as the next page's
        # opening, as a catchword would: «yırtdım ve başımdan | ve başımdan
        # saçları» (p1423 v70), «hükûmâtıŋ | hükûmâtıŋ hakdır» (p1723 v5).
        # HEXAPLA_ALIBEY_NOFIX=1 keeps both (known-bad control).
        if os.environ.get("HEXAPLA_ALIBEY_NOFIX") != "1":
            txt = re.sub(r"(\S+(?: \S+){0,2}) *(?:∞ *)?\x02 *\1(?=\s|$)", r"\1", txt)
        txt = txt.replace("\x02", " ")
        # The facsimile's catchword sits before «∞» and opens the next page
        # again: «… eyle ki ∞ eyle ki bütün …» (p1411 v25). Keep one.
        txt = re.sub(r"(\S+(?: \S+){0,2}) *∞\s+\1(?=\s|$)", r"\1", txt)
        txt = txt.replace("∞", " ").replace("*", "")
        return re.sub(r"\s+", " ", txt).strip()

    for pno in range(a.first, a.last + 1):
        pg = doc[pno - 1]
        rh = running_head(pg)
        if pno % 2 == 1 and rh:
            events.append({"p": pno, "k": "run", "t": rh})
        note = None  # an open editorial note (see NOTE); closes at a verse or heading
        prev = None  # (was a verse line, had bold, ended «-») of the previous line
        side_note = None  # the note event of the current side note box
        for _y, chars, tag in page_lines(pg):
            text = "".join(c for c, _ in chars)
            if tag == "catch":
                events.append({"p": pno, "k": "catch", "t": text.strip()})
                continue
            if tag == "note":
                t = re.sub(r"\s+", " ", text).strip()
                if side_note is None or side_note["p"] != pno:
                    side_note = {"p": pno, "k": "note", "t": t}
                    events.append(side_note)
                else:
                    side_note["t"] += " " + t
                continue
            side_note = None
            if not text.strip() or text.strip() == "*":  # a footnote's 10 pt star
                continue
            if CATCH.match(text.strip()):
                events.append({"p": pno, "k": "catch", "t": text.strip()})
                continue
            body = [cls for c, cls in chars if c.strip()]
            nb = sum(1 for c in body if c != "B")
            m = VERSE.match(text)
            flat = re.sub(r"\s+", " ", text).strip()
            if m and VERSE_NOTE.match(text[m.end():]):
                note = {"p": pno, "k": "note", "t": flat}
                events.append(note)
                prev = None
                continue
            if not m and (re.match(r"^\s*(\[(Not|\+)\]|\(\+\))", text)
                          or (nb == 0 and re.fullmatch(r"\S+:", flat))):
                note = {"p": pno, "k": "note", "t": flat}
                events.append(note)
                prev = None
                continue
            # A BOLD line inside a verse is verse text, not a heading, when the
            # line before it was a verse line that was itself partly bold or
            # broke on a hyphen (p113 «hamdü lillâh…», p179 «geçdiḡi gibi…»:
            # emphasis runs across lines). HEXAPLA_ALIBEY_BOLDHEAD=1 = old rule.
            bold_text = (nb == 0 and not m and prev is not None and prev[0]
                         and (prev[1] or prev[2])
                         and not re.search(r"(?i)b[âa]b\b", flat)
                         and os.environ.get("HEXAPLA_ALIBEY_BOLDHEAD") != "1")
            if nb == 0 and not m and not bold_text:
                events.append({"p": pno, "k": "head", "t": flat})
                last = {"R": None, "I": None}
                note = prev = None
                continue
            if note is not None and not m:
                note["t"] += " " + flat
                continue
            note = None
            prev = (True, any(cls == "B" for c, cls in chars if c.strip()),
                    text.rstrip().endswith("-"))
            rest = [cls for c, cls in chars[(m.end() if m else 0):] if c.strip() and cls != "B"]
            layer = "I" if rest and sum(1 for c in rest if c == "I") * 2 > len(rest) else "R"
            if m:
                ev = {"p": pno, "k": "v" if layer == "R" else "mod", "n": int(m.group("n")), "parts": []}
                if m.group("alt"):
                    ev["alt"] = int(m.group("alt"))
                    ev["altk"] = m.group("ak")
                r = last["R"]
                if (layer == "I" and r is not None and r.get("altk") == "("
                        and ev["n"] != r["n"] and not ev.get("alt")
                        and str(ev["n"]) in (str(r["n"]) + str(r["alt"]),
                                             str(r["n"])[:-1] + str(r["alt"]))):
                    r["n_printed"], r["n"] = r["n"], ev["n"]  # «1(4)» -> 14
                if layer == "I" and r is not None and r["n"] == ev["n"]:
                    r["mod"] = 1
                # The FIRST modern verse after a transliteration verse is its
                # twin: its number is Akın's, set a second time, and catches
                # a misprinted transliteration numeral (p1511 «6» for 16).
                if layer == "I" and r is not None and "mod_n" not in r:
                    r["mod_n"] = ev["n"]
                if layer == "R":
                    ev["mod"] = 0
                events.append(ev)
                last[layer] = ev
                text = text[m.end():]
            elif last[layer] is None:
                events.append({"p": pno, "k": "stray", "layer": layer, "t": text[:120]})
                continue
            elif last[layer]["p"] != pno:
                if last[layer].get("cont") != pno:
                    last[layer]["parts"].append("\x02")  # page turn (see clean)
                last[layer]["cont"] = pno
            #  marks a line break so hyphen joins know where lines ended.
            last[layer]["parts"].append(text.rstrip() + "")
    for e in events:
        if "parts" in e:
            e["t"] = clean(e.pop("parts"))
    events = [e for e in events if e["k"] != "mod"] + [
        {"k": "mod_orphan", "p": e["p"], "n": e["n"]} for e in events if e["k"] == "mod" and False]
    events = editorial_fixes(events)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    kinds = {}
    for e in events:
        kinds[e["k"]] = kinds.get(e["k"], 0) + 1
    print(f"{out}: {kinds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
