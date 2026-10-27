#!/usr/bin/env python
"""
kxii_initials_assign.py - give every detected Karl XII 1703 initial a VERSE
address (book slot, chapter, 0-based verse), 0 model cost. Report only: it
writes one JSON in the scratch dir and never touches a shipped asset.

    python tools/kxii_initials_assign.py --det _work/_scratch/kxii_init/det.json
    python tools/kxii_initials_assign.py --det ... --out assign.json --verbose
    python tools/kxii_initials_assign.py --selftest

INPUT  kxii_initials_detect.py --json output (pages 770-880).

METHOD (measured 2026-09-29 on the detector output, Judith p0770-0775)
    Reading order = the book's pages (research/karlxii_apoc_navigation.md s2,
    image = printed + 134), left column then right, top to bottom.
    * A MID-chapter initial keeps its verse numeral, so it sits AFTER the
      numeral: x offset from the column's text edge >= 45 px (+50..+120).
    * A chapter opens with initials ON the edge (offset < 45): the chapter
      SUMMARY's small initial (~60 px) and then verse 1's bigger one
      (~100-150 px), ~150 px apart. Consecutive edge initials with no mid
      initial between them and < GROUP_GAP px apart are ONE opening; the LAST
      of the group is verse 1. A lone edge initial < BIG_H is flagged
      (summary with v1 missed, or a small v1) - never silently counted.
    * Chapter k of the book = the k-th opening (non-empty chapters of
      sv_karlxii.json, in PRINT_ORDER where the print is not numeric:
      Esther+ 13,14,15,16,11,10). A sub-titled PIECE inside one numbering
      run (Esther+ 13:8, Bel 22, Azariah 51) is RULED_PIECE, not a chapter.
    * A woodcut book's full-width title: the R column above it on that page
      is the PREVIOUS book's tail (Esther+ 10:4 on Susanna's first page).
    * Mid initials in a chapter are matched to the doubled-capital verses of
      that chapter (app/src/main/assets/initials.json, a LOWER BOUND) in order
      when the counts agree -> AGREE. Otherwise each is placed by its position:
      fraction of the chapter's text height -> fraction of the chapter's text
      characters -> nearest verse start, preferring a doubled-capital verse
      within 2 -> ESTIMATE (with the distance), to be checked on a sheet.

    * Offsets are BIMODAL (edge -50..+10, mid +50..+120). The valley 10..44
      is decided per event by numeral_left(), never by moving MID_OFF (no
      single value makes every book agree - tuning it to the counts is
      forbidden). No margin numerals exist: the neighbour/gloss column runs
      to within ~10 px of the edge (measured 2026-09-29).
    * A book's first page: [PREFACE initial] -> summary initial -> woodcut.
      The summary opens the book; the preface initial is marked and left out
      (it is no chapter). A "mid" sharing rows with an adjacent edge initial
      is part of it and dropped. RULED_MID lists two-witness exceptions.
    * A book printing OK can hide a cancellation (one fake opening + one missed
      one): Tobit and 1 Macc did until the preface rule.
    * Locating a MISSING opening: chapter text fractions vs opening
      g-fractions only narrow it down. On Tobit they paired the wrong chapters
      because the g axis counted Wisdom's tail above the title band on p0791.
      One look that transcribes each opening's HEADING decides it (Tobit:
      1-5, 7-14 -> 6). Both misses were detector losses, not assignment:
      1 Macc 9 to the density floor, Tobit 6 to a one-column page (p0794).

STATUS per chapter: AGREE, ESTIMATE, COUNT (openings != chapters: the book's
chapter mapping itself is unproven and every address in it is void).
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles", "sv_karlxii.json")
INIT = os.path.join(HERE, "..", "app", "src", "main", "assets", "initials.json")
MID_OFF = 45
VALLEY_LO = 10     # offsets 10..44: edge OR mid, decided by numeral_left()
GROUP_GAP = 420
BIG_H = 90
DOUBLED_CAP = re.compile(u"^[A-ZÅÄÖ][A-ZÅÄÖ](?:[a-zåäöß]|\\b)")
NOT_INITIAL = re.compile(u"^(?:HErr|JEs)")

# (slot, name, first image, last image, opening) - opening: "woodcut" = the
# book starts at its tall woodcut on the first page; ("head", col, y) = at the
# first EDGE initial in that column of the first page below the book's
# heading at y (a heading look decides y; never the page top: Bel's page
# opens with Susanna's last verses, Azariah's with the Dragon's)
BOOKS = [(69, "Judith", 770, 779, "woodcut"), (70, "Wisdom", 780, 790, "woodcut"),
         (68, "Tobit", 791, 798, "woodcut"), (71, "Sirach", 799, 829, "woodcut"),
         (72, "Baruch", 830, 834, "woodcut"), (75, "1 Macc", 835, 857, "woodcut"),
         (76, "2 Macc", 858, 873, "woodcut"), (78, "Esther+", 874, 876, "woodcut"),
         (80, "Susanna", 876, 877, "woodcut"), (81, "Bel", 878, 879, ("head", "L", 1340)),
         (79, "Azariah", 879, 880, ("head", "L", 1840)), (74, "Manasses", 880, 880, ("head", "R", 940))]

# The PRINT's chapter order where it is not numeric (1-based chapter numbers).
# Esther+ is set in the Vulgate order of the pieces, ch10 running on after 11
# (research/karlxii_esther_additions.md; heading strips 2026-09-29). Without
# this list the k-th opening goes to the k-th NUMERIC chapter and an OK count
# would still be wrong in every address.
PRINT_ORDER = {78: [13, 14, 15, 16, 11, 10]}


def events(det):
    """All kept initials in reading order with a global text coordinate."""
    ev, g = [], 0
    for r in sorted(det, key=lambda r: r["page"]):
        p = int(r["page"][1:5])
        for ci, col in enumerate(r["cols"]):
            t0, t1, c0, c1 = col
            for b in sorted((b for b in r["boxes"] if b["col"] == "LR"[ci] and (b["keep"] or (
                            p, b["col"], b["y"]) in RULED_KEEP)),
                            key=lambda b: b["y"]):
                ev.append({"page": p, "col": b["col"], "x": b["x"], "y": b["y"], "w": b["w"],
                           "h": b["h"], "off": b["x"] - t0, "g": g + (b["y"] - c0)})
                e = ev[-1]
                # a BIG initial (v1 of an opening) is never tested: p0775 L y=562
                # (h 142) hit on a 20 px fleck; mids >= BIG_H are 13/455
                if VALLEY_LO <= e["off"] < MID_OFF and e["h"] < BIG_H \
                        and os.environ.get("HEXAPLA_NO_NUMTEST") != "1":
                    e["numeral"] = numeral_left(r, t0, e)
                if is_mid(e) and os.environ.get("HEXAPLA_NO_V1FRAG") != "1":
                    v1frag(r, t0, e)
            g += max(0, c1 - c0)
    if os.environ.get("HEXAPLA_NO_V1FRAG") != "1":
        # two kept boxes on ONE woodcut -> one event; a fragment whose cluster
        # overlaps an edge initial kept on its own is part of that initial
        # (p0790 L y=806 beside the v1 at 808: the dup-merge case)
        def over(a, b):
            return a["page"] == b["page"] and a["col"] == b["col"] and a["x"] < b["x"] + b["w"] \
                and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]
        seen, keep = set(), []
        for e in ev:
            k = (e["page"], e["col"], e["x"], e["y"], e["w"], e["h"]) if e.get("v1frag") else id(e)
            if e.get("v1frag") and any(not q.get("v1frag") and not is_mid(q) and over(e, q) for q in ev):
                continue
            if k not in seen:
                seen.add(k)
                keep.append(e)
        ev = keep
    if os.environ.get("HEXAPLA_NO_DUPMERGE") != "1":
        # a "mid" on the SAME rows as an edge initial and right beside it is a
        # second component of that initial (p0790 L y=806 beside the v1 at 808,
        # the only case in p0770-0880); left in, it splits the opening in two
        ev = [m for m in ev if not (is_mid(m) and any(
            not is_mid(e) and e["page"] == m["page"] and e["col"] == m["col"]
            and abs(e["y"] - m["y"]) < 40 and m["x"] - (e["x"] + e["w"]) < 30 for e in ev))]
    return [e for e in ev if key(e) not in RULED_ART]


# RULED sites, each on two witnesses (a look + the asset text): a MID initial
# with no numeral to find (it starts a sentence INSIDE a verse)
RULED_MID = {(784, "L", 1648): "Wis 8:18 «...samtaal. JAgh gick» - look 2026-09-29: between lines 18 and 19",
             (807, "R", 2602): "Sir 16:7 «ELden vpbrände then hela ogudachtiga» - heading look 2026-09-29 "
                               "(inside ch16, no heading) + LONE-SMALL look (in-column numeral, p0807 R)",
             (872, "R", 1018): "2 Macc 14:34 «...gick han sin wägh. MEn Presterna» (mid-verse) - "
                               "heading look 2026-09-29 (no heading, between 14 and 15) + asset",
             # numeral_left() missed both numerals (off 16/22 px): look read «4.» / «8.»
             (801, "R", 2348): "Sir 5:4 «TÄnck icke» - look 2026-09-29 «4. Tänck icke» + asset",
             (801, "R", 2814): "Sir 5:8 «THerföre fördrög» - look 2026-09-29 «8. Therföre» + asset; "
                               "heading look: between «5. Capitel» and «6. Capitel»"}


# RULED within-chapter PIECES: an edge group (rubric/argument initial + a
# woodcut on an UNNUMBERED verse) that opens a sub-titled piece inside one
# chapter's numbering run. Keyed by the woodcut; -> 0-based verse. The group
# folds into the chapter before it as one initial on that verse.
RULED_PIECE = {(874, "L", 2672): (7, "Esther+ 13:8 «OCh Mardocheus bad» unnumbered, under the rubric «Thetta "
                                     "stycket må man läsa efter ändan på fierde capitlet» - look 2026-09-29 (E3/E4) "
                                     "+ research/karlxii_esther_additions.md ch13 notes"),
               (878, "R", 2056): (21, "Bel 22 (print) «THer war ock en stoor drake» unnumbered, under «Om Drakan "
                                      "i Babel.» - look 2026-09-29 (D6/D7) + karlxii_daniel_additions.md Bel notes"),
               (879, "R", 2748): (27, "Azariah 51 (Vulgate) «TÅ begynte the tre» unnumbered, under «The tre Måns "
                                      "Loffång i eldenom.» - look 2026-09-29 (D15/D16) + daniel_additions notes")}

# RULED OPENINGS kept as openings although they carry a verse numeral.
RULED_OPEN = {(876, "R", 914): "Esther+ 10:4 «4. OCh Mardocheus sade» - opens ch10, which runs on after 11 "
                                "with no rubric; look 2026-09-29 (E14, numeral 4.) + esther_additions ch10 notes",
              (879, "L", 2108): "Azariah v24 woodcut M (see RULED_KEEP): its kept fragment starts 66 px in, "
                                "so the offset rule would call it a mid"}

# RULED KEEPS: a detector box the density filter dropped, which IS an opening
# woodcut (the box may be only part of it; the crop step takes the ink bbox)
RULED_KEEP = {(879, "L", 2108): "Azariah v24 (print) decorated M «MEn the gingo», under «Asaries Böön» - "
                                "look 2026-09-29 (D12 INITIAL-BIG) + daniel_additions «unnumbered under a "
                                "decorated M»; kept box 48x80 is a fragment of it"}

# RULED V1 BOXES: a LONE-SMALL opening whose small framed initial is the
# chapter SUMMARY's, while the v1 woodcut (a ~4-line «M») was never kept by the
# detector. Keyed by the summary; -> the woodcut's ink box (full-res component
# union, scan_below.py 2026-09-29). The summary becomes a "summary" row (never
# shipped). Two witnesses each: the look's v1 words = the asset's v1 (script),
# and the box's ink below the summary. ▶ _work/_scratch/kxii_init/lone/LONE_FINDINGS_2026-09-29.md
RULED_V1BOX = {(800, "L", 1162): ((862, 1266, 141, 155), "Sir 2:1 «Min son wilt tu wara» - LONE-SMALL look "
                                                         "S2 (summary «En rätt Gudz tienare») + asset v1"),
               (810, "L", 452): ((821, 546, 135, 156), "Sir 20:1 «Man straffar ofta» - LONE-SMALL look S4 "
                                                       "(summary «Undertwijsning om straff») + asset v1"),
               (842, "R", 2132): ((1563, 2417, 137, 148), "1 Macc 6:1 «Men tå Konung Antiochus» - LONE-SMALL "
                                                          "look S6 (summary «Som nu Antiochus») + asset v1"),
               # summary at a column FOOT, woodcut at the next column's top: the box carries its own
               # (page, col). Box by script (lone/top_woodcut_box.py rc 0), right edge agreeing with the
               # resolve look's ruler measurement within 15 px; words = asset v1 (finalize_resolve.py)
               (772, "R", 2914): ((354, 332, 119, 144), "Judith 6:1 «SEdan förgrymmade sigh» - resolve look "
                                                        "T7 (right edge -8 px) + asset v1", (773, "L")),
               (809, "L", 2842): ((1063, 414, 131, 140), "Sir 19:1 «EN arbetare then sigh» - resolve look T8 "
                                                         "(right edge -8 px) + asset v1", (809, "R")),
               (872, "R", 2948): ((388, 509, 130, 143), "2 Macc 15:1 «MEn tå Nicanor hörde» - resolve look T9 "
                                                        "(right edge +14 px) + asset v1", (873, "L"))}

# RULED ART: kept boxes that are no initial (headpiece, title letters).
RULED_ART = {(874, "R", 624): "headpiece flourish (328x154) - look 2026-09-29 E5 ORNAMENT + heading-strip look "
                               "E#3 saw no initial + esther_additions: p740 opens with a full-width headpiece",
             (874, "R", 828): "margin mark beside ch13 v12-18, no letter - look 2026-09-29 E6 OTHER/UNCLEAR + "
                               "heading-strip look E#3 saw no initial",
             (876, "R", 2182): "«D» of the display title «Daniel» - look 2026-09-29 E15 TITLE-LETTER + "
                                "esther_additions: «Daniel» in p742_R4 under the Daniel headpiece",
             (879, "L", 2188): "upper component of the Azariah 25 «OCh» initial (the look put D13 y=2188 and D14 "
                                "y=2252 on ONE «O») + geometry: same x 436, box ends at 2250"}


def key(e):
    return (e["page"], e["col"], e["y"])


def is_mid(e):
    if key(e) in RULED_OPEN:
        return False
    return e["off"] >= MID_OFF or bool(e.get("numeral")) or key(e) in RULED_MID


_PAGE = {}


def numeral_left(r, t0, e):
    """True when a digit-sized ink component sits on the capital's first line
    between the text edge and the capital: the verse numeral a MID initial
    keeps (offsets 10..44 px = a narrow numeral). Window x [t0-30, box-2],
    y [box-10, box+60], ink < 120 at full res. A hit must start at >= t0-8
    (left of that is the neighbour/gloss column), be 0.45 line..40 px tall,
    5..60 px wide, >= 20 px of ink, clear of the window's left edge and of
    the capital. Calibrated 2026-09-29 on CONTROLS, never on chapter counts:
    mid initials (off 50-130) 354/450 found; edge initials of grouped
    openings 0/161. A miss is NOT evidence of an opening (79 % recall)."""
    import numpy as np
    from PIL import Image
    from kxii_initials_detect import PAGES, components
    if r["page"] not in _PAGE:
        _PAGE.clear()
        _PAGE[r["page"]] = np.asarray(Image.open(os.path.join(PAGES, r["page"])).convert("L")) < 120
    m = _PAGE[r["page"]]
    lh = 2 * r["line"]
    x0, x1 = t0 - 30, e["x"] - 2
    y0, y1 = max(0, e["y"] - 10), e["y"] + 60
    if x1 - x0 < 6:
        return False
    for a0, b0, a1, b1, n in components(m[y0:y1, x0:x1]):
        w, h = a1 - a0, b1 - b0
        if a0 > 0 and a1 <= x1 - x0 and 0.45 * lh <= h <= min(40, 1.4 * lh) and 5 <= w <= 60 \
                and n >= 20 and x0 + a0 - t0 >= -8:
            return True
    return False


FRAG_H = 5.0      # cluster height in det "line" units: mid initials ~3.3, the v1 woodcut ~6.5
FRAG_MAX = 9.0    # ... and a chained cluster (text, rules) runs 15-27


def v1frag(r, t0, e):
    """A kept "mid" box that is a FRAGMENT of a chapter's v1 woodcut (a ~4-line
    «M» the detector split into 2-4 ink components, the tallest kept one sitting
    right of the numeral gap): grow a cluster from the box over undilated ink
    components >= 20 px wide and >= 40 px tall (no rule, no text letter) whose
    bbox gap to the cluster is <= 4 px. A cluster >= FRAG_H lines tall that
    starts at the column edge (off < VALLEY_LO) is the woodcut: the event takes
    the cluster box and becomes an EDGE initial (it then groups with the
    chapter's summary initial as its v1). Found 2026-09-29 (LONE_FINDINGS):
    1 Macc 5 p0841 L y=2162 and 1 Macc 8 p0845 R y=1846 were AGREE mids with a
    wrong verse. Control: HEXAPLA_NO_V1FRAG=1 (selftest must fail)."""
    import numpy as np
    from PIL import Image
    from kxii_initials_detect import PAGES, components
    if r["page"] not in _FRAGPAGE:
        _FRAGPAGE.clear()
        _FRAGPAGE[r["page"]] = np.asarray(Image.open(os.path.join(PAGES, r["page"])).convert("L")) < 135
    m = _FRAGPAGE[r["page"]]
    x0, y0 = max(0, t0 - 60), max(0, e["y"] - 260)
    x1, y1 = min(m.shape[1], t0 + 320), min(m.shape[0], e["y"] + e["h"] + 260)
    cs = [(a0 + x0, b0 + y0, a1 + x0, b1 + y0) for a0, b0, a1, b1, n in components(m[y0:y1, x0:x1])
          if a1 - a0 >= 20 and b1 - b0 >= 40]

    def gap(a, b):
        return max(a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3], 0)
    box = (e["x"], e["y"], e["x"] + e["w"], e["y"] + e["h"])
    u = [c for c in cs if gap(c, box) == 0]
    if not u:
        return False
    u = [min(c[0] for c in u), min(c[1] for c in u), max(c[2] for c in u), max(c[3] for c in u)]
    grew = True
    while grew:
        grew = False
        for c in cs:
            if gap(c, u) <= 4 and not (u[0] <= c[0] and u[1] <= c[1] and c[2] <= u[2] and c[3] <= u[3]):
                u = [min(u[0], c[0]), min(u[1], c[1]), max(u[2], c[2]), max(u[3], c[3])]
                grew = True
    # a cluster far larger than any chapter woodcut (130-160 px) chained along
    # text or rules (p0862 L / p0866 L / p0879 L: 334-380 px wide) - no fragment
    if FRAG_H * r["line"] <= u[3] - u[1] <= FRAG_MAX * r["line"] and u[2] - u[0] <= FRAG_MAX * r["line"] \
            and u[0] - t0 < VALLEY_LO:
        e.update(frag_of=(e["x"], e["y"], e["w"], e["h"]), g=e["g"] + u[1] - e["y"], x=u[0], y=u[1], w=u[2] - u[0], h=u[3] - u[1],
                 off=u[0] - t0, v1frag=True)
        e.pop("numeral", None)
        return True
    return False


_FRAGPAGE = {}


def split_books(ev):
    """{slot: [events]} - a book starts at its opening woodcut (h >= 200) on
    its first page, or at the top of its first page."""
    starts = []
    for slot, name, a, z, how in BOOKS:
        s = None
        if how == "woodcut":
            s = next((e["g"] for e in ev if e["page"] == a and e["h"] >= 200), None)
            # the book's SUMMARY initial sits on the edge just above its woodcut
            # (6 books, 80-250 px): it opens the new book, not the old one's last
            # chapter (measured 2026-09-29: p0780/0791/0799/0835/0858/0874)
            if s is not None and os.environ.get("HEXAPLA_NO_BOOKSUM") != "1":
                s = min([s] + [e["g"] for e in ev if e["page"] == a and e["off"] < MID_OFF
                               and 0 < s - e["g"] < GROUP_GAP])
            # the book's PREFACE («Förspråk», Luther's Vorrede) opens with ONE
            # big edge initial right before that summary (Tobit p0791 L y=1638,
            # seen under the «Tobie Book» title; same shape on 8 first pages).
            # It opens the new book but is no chapter: marked, left out of it.
            if s is not None and os.environ.get("HEXAPLA_NO_PREFACE") != "1":
                prev = [e for e in ev if e["g"] < s]
                # the preface may start on the PREVIOUS book's last page and carry
                # its own mid initials: Wisdom's «Om thenna book hafwer långe ett
                # twifwel» p0779 L y=1746, then a mid at R y=594 (heading look
                # 2026-09-29). So: the last EDGE initial, followed only by mids,
                # on pages a-1..a. HEXAPLA_PREFACE_SAMEPAGE=1 = the old rule.
                old = os.environ.get("HEXAPLA_PREFACE_SAMEPAGE") == "1"
                pages = (a,) if old else (a - 1, a)
                k = len(prev) - 1
                while not old and k >= 0 and is_mid(prev[k]) and prev[k]["page"] in pages:
                    k -= 1
                p = prev[k] if k >= 0 else None
                if p and p["page"] in pages and not is_mid(p) and not any(
                        not is_mid(q) and 0 < p["g"] - q["g"] < GROUP_GAP for q in prev[:k]):
                    for q in prev[k:]:          # the preface's own mids too
                        q["preface"] = True
                    s = p["g"]
        elif isinstance(how, tuple) and how[0] == "head":
            _, hc, hy = how
            s = next((e["g"] for e in ev if e["page"] == a and e["col"] == hc and e["y"] >= hy
                      and not is_mid(e)), None)
        if s is None:
            s = next((e["g"] for e in ev if e["page"] >= a), None)
        starts.append((slot, s))
    out = {}
    for i, (slot, s) in enumerate(starts):
        end = next((t for _, t in starts[i + 1:] if t is not None), 10 ** 9)
        out[slot] = [e for e in ev if s is not None and s <= e["g"] < end and not e.get("preface")]
    if os.environ.get("HEXAPLA_NO_ABOVETITLE") != "1":
        # A book that starts in the LEFT column under a FULL-WIDTH title: the
        # right column ABOVE that title is the previous book's tail (Esther+
        # 10:4 on p0876 R y=914 sat in Susanna, whose title band is at ~2180).
        # Reading order is L-above, R-above, title, L-below, R-below; the g axis
        # (column by column) cannot express that, so those events move back.
        for i, (slot, s) in enumerate(starts):
            first = next((e for e in out.get(slot, []) if e["g"] == s), None)
            # only a "woodcut" book has a full-width display title; a ("head")
            # piece title sits IN its column and the R column above it is the
            # new book's own continuation (Bel p0878 R y=674)
            if i == 0 or first is None or first["col"] != "L" or BOOKS[i][4] != "woodcut":
                continue
            prev = starts[i - 1][0]
            up = [e for e in out[slot] if e["page"] == first["page"] and e["col"] == "R"
                  and e["y"] < first["y"]]
            if up:
                out[slot] = [e for e in out[slot] if e not in up]
                out[prev] = out[prev] + up
    return out, dict(starts)


def chapters_of(evs):
    """-> list of chapters: {"open": [edge events], "v1": event|None,
    "mid": [events], "flag": str}"""
    chs, cur_edge, last = [], [], None
    for e in evs:
        if not is_mid(e):
            if cur_edge and e["g"] - cur_edge[-1]["g"] < GROUP_GAP:
                cur_edge.append(e)
            else:
                cur_edge = [e]
                chs.append({"open": cur_edge, "mid": []})
        else:
            cur_edge = []
            if chs:
                chs[-1]["mid"].append(e)
            else:
                chs.append({"open": [], "mid": [e]})     # mid before any opening: flag
    folded = []
    for c in chs:
        w = c["open"][-1] if c["open"] else None
        if w is not None and key(w) in RULED_PIECE and folded \
                and os.environ.get("HEXAPLA_NO_PIECE") != "1":
            # a piece inside the previous chapter's numbering: its woodcut is
            # one initial on a fixed verse; its rubric initial is no row
            w["fixed_v"] = RULED_PIECE[key(w)][0]
            folded[-1]["mid"] += [w] + c["mid"]
        else:
            folded.append(c)
    chs = folded
    for c in chs:
        c["v1"] = c["open"][-1] if c["open"] else None
        c["flag"] = ""
        if not c["open"]:
            c["flag"] = "NO-OPENING"
        elif len(c["open"]) == 1 and c["open"][0]["h"] < BIG_H and key(c["open"][0]) not in RULED_OPEN:
            c["flag"] = "LONE-SMALL"
        elif len(c["open"]) > 2:
            c["flag"] = "OPEN-%d" % len(c["open"])
    return chs


def assign(det, verbose=False):
    asset = json.load(io.open(ASSET, encoding="utf-8"))
    ini = json.load(io.open(INIT, encoding="utf-8"))["kxii"]
    ev = events(det)
    per, starts = split_books(ev)
    report, rows = [], []
    for slot, name, a, z, how in BOOKS:
        chs_text = [(ci, ch) for ci, ch in enumerate(asset[slot]["chapters"]) if any(ch)]
        if slot in PRINT_ORDER and os.environ.get("HEXAPLA_NUMERIC_ORDER") != "1":
            order = PRINT_ORDER[slot]
            assert sorted(order) == [ci + 1 for ci, _ in chs_text], (name, order)
            chs_text = [(n - 1, asset[slot]["chapters"][n - 1]) for n in order]
        chs = chapters_of(per.get(slot, []))
        book_ok = len(chs) == len(chs_text)
        report.append("%-8s slot %d  openings %d  chapters %d  %s" % (
            name, slot, len(chs), len(chs_text), "OK" if book_ok else "COUNT MISMATCH"))
        if not book_ok:
            for c in chs:
                if c["flag"]:
                    e = c["open"][0] if c["open"] else c["mid"][0]
                    report.append("    %s at p%04d %s y=%d" % (c["flag"], e["page"], e["col"], e["y"]))
            continue
        ends = [c["open"][0]["g"] if c["open"] else c["mid"][0]["g"] for c in chs[1:]]
        last = per[slot][-1]["g"] + 1 if per.get(slot) else 0
        ends.append(max(last, ends[-1] if ends else last))
        for k, (c, (ci, text)) in enumerate(zip(chs, chs_text)):
            # the chapter's first PRINTED verse is its opening, never a mid
            # (Esther+ 10 and 15 start at 4: their 1-3 are empty grid placeholders)
            v1 = next(i for i, t in enumerate(text) if t)
            want = [v for v in (ini.get(str(slot), [])[ci] if ci < len(ini.get(str(slot), [])) else []) if v != v1]
            status = "AGREE" if len(want) == len(c["mid"]) else "ESTIMATE"
            vb = RULED_V1BOX.get(key(c["v1"])) if c["v1"] and c["flag"] == "LONE-SMALL" \
                and os.environ.get("HEXAPLA_NO_V1BOX") != "1" else None
            if vb:
                (bx, by, bw, bh), why = vb[:2]
                bpage, bcol = vb[2] if len(vb) > 2 else (c["v1"]["page"], c["v1"]["col"])
                rows.append({"slot": slot, "ch": ci + 1, "v": v1, "page": c["v1"]["page"], "col": c["v1"]["col"],
                             "x": c["v1"]["x"], "y": c["v1"]["y"], "w": c["v1"]["w"], "h": c["v1"]["h"],
                             "kind": "summary", "status": "SUMMARY"})
                rows.append({"slot": slot, "ch": ci + 1, "v": v1, "page": bpage, "col": bcol,
                             "x": bx, "y": by, "w": bw, "h": bh, "kind": "opening", "status": "OPENING-RULED",
                             "why": why})
            elif c["v1"]:
                rows.append({"slot": slot, "ch": ci + 1, "v": v1, "page": c["v1"]["page"], "col": c["v1"]["col"],
                             "x": c["v1"]["x"], "y": c["v1"]["y"], "w": c["v1"]["w"], "h": c["v1"]["h"],
                             "kind": "opening", "status": c["flag"] or "OPENING"})
            g0 = c["v1"]["g"] if c["v1"] else (c["mid"][0]["g"] if c["mid"] else 0)
            span = max(1, ends[k] - g0)
            lens = [len(t or "") for t in text]
            tot = float(sum(lens)) or 1.0
            starts_f, acc = [], 0
            for n in lens:
                starts_f.append(acc / tot)
                acc += n
            for i, e in enumerate(c["mid"]):
                f = (e["g"] - g0) / float(span)
                near = min(range(len(text)), key=lambda v: abs(starts_f[v] - f))
                cand = [v for v in range(max(0, near - 2), min(len(text), near + 3))
                        if text[v] and DOUBLED_CAP.match(text[v]) and not NOT_INITIAL.match(text[v])]
                est = min(cand, key=lambda v: abs(v - near)) if cand else near
                if "fixed_v" in e:
                    near = est = e["fixed_v"]
                v = want[i] if status == "AGREE" else est
                rows.append({"slot": slot, "ch": ci + 1, "v": v, "page": e["page"], "col": e["col"],
                             "x": e["x"], "y": e["y"], "w": e["w"], "h": e["h"], "kind": "mid",
                             "status": status, "est": est, "est_dist": abs(est - near),
                             "agrees_est": v == est})
            if verbose or status != "AGREE" or c["flag"]:
                report.append("    ch%-3d mid det %2d json %2d %s%s" % (
                    ci + 1, len(c["mid"]), len(want), status, (" " + c["flag"]) if c["flag"] else ""))
    return report, rows


def apply_ruled(rows, ruled):
    """Fold a looked-and-ruled ESTIMATE file (est_final.json: label, page, col,
    y, status, ruled_v) into the rows. RULED -> that 0-based verse; ART -> no
    row; RULED-V1 / RULED-V1FRAG -> the box sits on the chapter's v1 woodcut
    (the whole initial, or a flourish at its foot): the mid row goes, and when
    the chapter's opening is a LONE-SMALL summary the opening row moves onto
    this box (V1FRAG rows carry grow_left: crop the woodcut by ink leftwards).
    -> list of unruled ESTIMATE rows (must be empty).
    Control: HEXAPLA_NO_RULED=1 ignores the file, so every ESTIMATE stays."""
    if os.environ.get("HEXAPLA_NO_RULED") == "1":
        ruled = []
    by = {(int(o["page"][1:5]), o["col"], o["y"]): o for o in ruled}
    out, left = [], []
    opening = {(r["slot"], r["ch"]): r for r in rows if r["kind"] == "opening"}
    for r in rows:
        o = by.get((r["page"], r["col"], r["y"])) if r["kind"] == "mid" else None
        if o is None:
            if r["status"] == "ESTIMATE":
                left.append(r)
            out.append(r)
            continue
        st = o["status"]
        if st == "RULED":
            out.append(dict(r, v=o["ruled_v"], status="RULED", why=o.get("why", "")))
        elif st in ("RULED-V1", "RULED-V1FRAG"):
            op = opening.get((r["slot"], r["ch"]))
            if op is not None and op["status"] == "LONE-SMALL":
                op.update(page=r["page"], col=r["col"], x=r["x"], y=r["y"], w=r["w"], h=r["h"],
                          status="OPENING-" + st[6:], grow_left=st == "RULED-V1FRAG", why=o.get("why", ""))
        elif st != "ART":
            left.append(r)
            out.append(r)
    rows[:] = out
    return left


def selftest():
    """Fixtures: a synthetic two-chapter book. Edge group (summary 60 + v1 140)
    opens each chapter; mids after the numeral. Control: HEXAPLA_NO_GROUP=1
    stops grouping, so each chapter opens TWICE and the count must fail."""
    def e(g, off, h):
        return {"page": 1, "col": "L", "x": 0, "y": 0, "w": 60, "h": h, "off": off, "g": g}
    evs = [e(0, 0, 60), e(150, 0, 140), e(900, 90, 66), e(2000, 0, 60), e(2160, 4, 130), e(3000, 85, 66)]
    global GROUP_GAP
    if os.environ.get("HEXAPLA_NO_GROUP") == "1":
        GROUP_GAP = 0
    chs = chapters_of(evs)
    ok = len(chs) == 2 and all(c["v1"]["h"] >= 130 and len(c["mid"]) == 1 and not c["flag"] for c in chs)
    print("SELFTEST %s (%d chapters)" % ("PASS" if ok else "FAIL", len(chs)))
    # book split: Judith's first page (770) opens with summary initial 150 px
    # above the woodcut; it belongs to Judith, not to the book before.
    # Control: HEXAPLA_NO_BOOKSUM=1 must fail this.
    def f(p, g, off, h):
        return {"page": p, "col": "L", "x": 0, "y": 0, "w": 60, "h": h, "off": off, "g": g}
    # ... and a PREFACE initial (g 400, lone, big) before that summary is
    # neither the previous book's chapter nor one of Judith's.
    # Control: HEXAPLA_NO_PREFACE=1 must fail this.
    # (on Wisdom's first page 780, so a wrong split hands it to Judith)
    evb = [f(770, 0, 0, 240), f(779, 100, 90, 66), f(780, 600, 0, 104), f(780, 1000, 0, 60),
           f(780, 1150, 0, 240), f(780, 2000, 90, 66)]
    per, _ = split_books(evb)
    ok2 = [e["g"] for e in per[70]] == [1000, 1150, 2000] and [e["g"] for e in per[69]] == [0, 100]
    print("SELFTEST book-summary %s" % ("PASS" if ok2 else "FAIL"))
    # valley numeral on real pages: p0804 R y=760 (off 42, «8» seen by a look)
    # is MID; p0770 R y=2848 (grouped opening, neighbour text 27 px left of the
    # edge = the loose rule's false positive) stays EDGE. Control:
    # HEXAPLA_NO_NUMTEST=1 must fail this.
    from kxii_initials_detect import PAGES, detect
    # (p0770 R: the woodcut's box is y=2880 since big edge woodcuts keep the
    # 0.18 density floor; it was the smaller overlapping y=2848 box before)
    want = {(804, "R", 760): True, (770, "R", 2880): False, (775, "L", 562): False}
    got = {}
    for p in sorted({k[0] for k in want}):
        d = detect(os.path.join(PAGES, "p%04d.jpg" % p))
        d["page"] = "p%04d.jpg" % p
        for e in events([d]):
            if (e["page"], e["col"], e["y"]) in want:
                got[(e["page"], e["col"], e["y"])] = e["off"] >= VALLEY_LO and is_mid(e)
    ok3 = got == want
    print("SELFTEST valley-numeral %s %s" % ("PASS" if ok3 else "FAIL", sorted(got.items())))
    # same-row duplicate: p0790 L keeps the v1 at y=808 and loses the "mid"
    # component at y=806. Control: HEXAPLA_NO_DUPMERGE=1 must fail this.
    d = detect(os.path.join(PAGES, "p0790.jpg"))
    d["page"] = "p0790.jpg"
    ys = [e["y"] for e in events([d]) if e["col"] == "L" and 780 <= e["y"] <= 830]
    ok4 = ys == [808]
    print("SELFTEST dup-merge %s %s" % ("PASS" if ok4 else "FAIL", ys))
    # full-width title: Susanna's first page 876 has the previous book's mid
    # in the R column ABOVE the title (R y=900 < L y=2360). It belongs to
    # Esther+, not Susanna. Control: HEXAPLA_NO_ABOVETITLE=1 must fail this.
    def h(p, col, y, g, off, hh):
        return {"page": p, "col": col, "x": 0, "y": y, "w": 60, "h": hh, "off": off, "g": g}
    evt = [h(874, "L", 1020, 100, 0, 60), h(874, "L", 1100, 180, 0, 240), h(876, "L", 1080, 780, 0, 60), h(876, "L", 1200, 900, 0, 150),
           h(876, "L", 2360, 1600, 0, 60), h(876, "L", 2780, 1920, 0, 240),
           h(876, "R", 900, 2800, 80, 66), h(876, "R", 2600, 4500, 80, 66)]
    per, _ = split_books(evt)
    ok5 = [e["y"] for e in per[78]] == [1020, 1100, 1080, 1200, 900] and \
        [e["y"] for e in per[80]] == [2360, 2780, 2600]
    print("SELFTEST above-title %s %s" % ("PASS" if ok5 else "FAIL", {k: [x["y"] for x in v] for k, v in per.items() if v}))
    # a within-chapter PIECE (rubric + woodcut on an unnumbered verse) folds
    # into the chapter before it as one initial on its fixed verse.
    # Control: HEXAPLA_NO_PIECE=1 must fail this (two chapters).
    RULED_PIECE[(1, "L", 777)] = (7, "fixture")
    def pe(g, off, hh):
        return {"page": 1, "col": "L", "x": 0, "y": 0, "w": 60, "h": hh, "off": off, "g": g}
    evp = [pe(0, 0, 60), pe(150, 0, 140), pe(900, 90, 66), dict(pe(2000, 0, 60), y=700),
           dict(pe(2160, 4, 130), y=777), pe(3000, 85, 66)]
    chs = chapters_of(evp)
    del RULED_PIECE[(1, "L", 777)]
    ok6 = len(chs) == 1 and [m.get("fixed_v") for m in chs[0]["mid"]] == [None, 7, None]
    print("SELFTEST piece %s (%d chapters)" % ("PASS" if ok6 else "FAIL", len(chs)))
    # v1-woodcut fragment on real pages: 1 Macc 5 p0841 L y=2162 and 1 Macc 8
    # p0845 R y=1846 (kept boxes on the split «M») become EDGE initials >= 130
    # px tall; real mids 1 Macc 6 v5 p0842 L y=982 and p0843 L y=384 stay mids.
    # Control: HEXAPLA_NO_V1FRAG=1 must fail this.
    want = {(841, "L", 2162): False, (845, "R", 1846): False, (842, "L", 982): True, (843, "L", 384): True}
    got = {}
    for p in sorted({k[0] for k in want}):
        d = detect(os.path.join(PAGES, "p%04d.jpg" % p))
        d["page"] = "p%04d.jpg" % p
        for e in events([d]):
            k0 = (e["page"], e["col"], e["frag_of"][1] if e.get("frag_of") else e["y"])
            if k0 in want:
                got[k0] = is_mid(e) and not e.get("v1frag")
                if e.get("v1frag") and e["h"] < 130:
                    got[k0] = "short %d" % e["h"]
    ok7 = got == want
    print("SELFTEST v1-fragment %s %s" % ("PASS" if ok7 else "FAIL", sorted(got.items())))
    return 0 if ok and ok2 and ok3 and ok4 and ok5 and ok6 and ok7 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--det")
    ap.add_argument("--out")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--ruled", help="est_final.json: looked-and-ruled ESTIMATE rows; rc 1 if any stays unruled")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.det:
        ap.error("--det is required")
    det = json.load(io.open(a.det, encoding="utf-8"))
    report, rows = assign(det, a.verbose)
    print("\n".join(report))
    left = []
    if a.ruled:
        left = apply_ruled(rows, json.load(io.open(a.ruled, encoding="utf-8")))
        for r in left:
            print("    UNRULED ESTIMATE slot %d ch%d p%04d %s y=%d" % (r["slot"], r["ch"], r["page"], r["col"], r["y"]))
    n = {}
    for r in rows:
        n[r["status"]] = n.get(r["status"], 0) + 1
    print("ROWS %d  %s" % (len(rows), " ".join("%s=%d" % kv for kv in sorted(n.items()))))
    if a.out:
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=0)
        print("wrote", a.out)
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
