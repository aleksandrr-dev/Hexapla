#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_bakar.py — EXTRACTION + CENSUS ONLY for the TITUS 1743 Moscow (Bakar)
Georgian Bible harvest.

Input : C:/Projects/Hexapla-releases/titus_bakar/bakar008-090.htm (+001-007)
Output: C:/Projects/Hexapla-releases/titus_bakar/extracted/bakar_raw.json
        C:/Projects/Hexapla-releases/titus_bakar/extracted/bakar_census.json

This script does NOT build an app asset, does NOT touch app/src/main/assets,
does NOT repair anything. It parses TITUS's own markup into a structured raw
dump, preserving TITUS's own labels EXACTLY (glued/odd labels are flagged,
never fixed), and computes a forensic census. A later dedicated session
builds the converter from this inventory.

Markup model (verified by direct inspection of the harvest, 2026-07-20):
  <span id=hN><!Level N>Label: value<A NAME="logical">&nbsp;</A>
      [<A NAME="physical">&nbsp;</A>]</sPAN>
  Levels: 1=Text collection (VT/NT/...), 2=Book, 3=Chapter, 4=Verse,
          5=Page, 6=Column, 7=Line.  Levels 5-7 use "<!XLevel N>".
  The physical anchor ends in _page_col_line (print provenance).
  Every word is wrapped in <a id=mxag16 href="javascript:ci(...)">word</a>;
  print-line hyphenation is a literal backslash (rarely a slash) INSIDE the
  word: "მსახურ\\ებისა" — rejoined here, counted per book.
  Span classes seen: mxag16 (running text), mxagl16 (lectionary rubric text),
  mxagt16/mxagtx16 (heading words / alphabetic-numeral glyphs), n16 (closer).

Deterministic, re-runnable, assertion-gated: unknown marker shapes, unknown
tags, or leftover unparsed Georgian text hard-fail (or land in a fully
enumerated "unrecognized" census bucket — nothing is skipped silently).
"""

import html
import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict

BASE = "C:/Projects/Hexapla-releases/titus_bakar"
OUT_DIR = os.path.join(BASE, "extracted")
KJV_PATH = "C:/Projects/Hexapla/app/src/main/assets/bibles/en_kjv.json"
CU_PATH = "C:/Projects/Hexapla/app/src/main/assets/bibles/cu_elizabeth.json"

SCRIPTURE_PARTS = range(8, 88)     # 008-060 OT+deutero, 061-087 NT
FRONT_PARTS = range(1, 8)          # front matter
LIT_PARTS = range(88, 91)          # liturgical tables

# part number -> KJV book index in en_kjv.json (None = no KJV counterpart)
PART_TO_KJV = {}
for p, k in list(zip(range(8, 22), range(0, 14))):   # Gen..2 Chr
    PART_TO_KJV[p] = k
PART_TO_KJV.update({22: None,          # Or.Man.
                    23: 14, 24: 15,    # Esr.II(Esr.)=Ezra, Esr.II(Neh.)=Nehemiah
                    25: None, 26: None,  # Esr.I(Esr.III), Esr.III(Esr.IV)
                    27: None, 28: None,  # Tob., Jud.
                    29: 16, 30: 17,    # Esth. (with LXX additions), Hiob
                    31: 18,            # Ps. (LXX shape -> compared vs cu instead)
                    32: None,          # Od.
                    33: 19, 34: 20, 35: 21,  # Prov. Eccl. Cant.
                    36: None, 37: None,      # Sap.Sal., Sir.
                    38: 22, 39: 23, 40: 24,  # Is. Jer. Lam.Jer.
                    41: None, 42: None, 43: None,  # Or.Jer. Bar. Ep.Jer.
                    44: 25, 45: 26})   # Ez., Dan. (with LXX additions)
for p, k in list(zip(range(46, 58), range(27, 39))):  # Hos..Mal
    PART_TO_KJV[p] = k
PART_TO_KJV.update({58: None, 59: None, 60: None})    # 1-3 Macc.
for p, k in list(zip(range(61, 88), range(39, 66))):  # Mt..Rev
    PART_TO_KJV[p] = k

MARK_RE = re.compile(
    r'<span id=h(\d)><!(X?)Level (\d)>([^<]*)'
    r'<A NAME="([^"]*)">&nbsp;</A>'
    r'(?:<A NAME="([^"]*)">&nbsp;</A>)?'
    r'</sPAN>')
LEVEL_PREFIX = {1: "Text collection", 2: "Book", 3: "Chapter", 4: "Verse",
                5: "Page", 6: "Column", 7: "Line"}
TAG_RE = re.compile(r'<(/?)([A-Za-z!][A-Za-z0-9]*)[^>]*>')
KNOWN_TAGS = {"span", "a", "br", "div", "font", "b", "i", "hr", "img", "sub", "sup"}

GEO = r'Ⴀ-ჿ'
GEO_RE = re.compile('[' + GEO + ']')
BS_JOIN_RE = re.compile(r'(?<=\S)\\(?=\S)')
SL_JOIN_RE = re.compile(r'(?<=[' + GEO + r'])/(?=[' + GEO + r'])')

VERSE_NUM_RE = re.compile(r'^(\d+)$')
VERSE_CONT_RE = re.compile(r'^(\d+)[bბ]$')          # continuation after rubric
VERSE_RUBRIC_RE = re.compile(r'^ხ(.*)ხ$')            # lectionary rubric
VERSE_GLUED_RE = re.compile(r'^(\d+)(\D.*)$')        # number fused with 1st word
VERSE_PAREN_RE = re.compile(r'^\((.*)\)$')           # e.g. (131_11) epigraph


def phys_parts(anchor):
    """physical anchor '..._994_b_5' -> (page, col, line) or None."""
    if not anchor:
        return None
    bits = anchor.rsplit('_', 3)
    # column codes seen in the corpus: a, b, '' (Lev 26:43 / Jos 5:4),
    # a0 (Lk 5 page 844), m (= margin; Job 19:25a-27a variant block)
    if len(bits) == 4 and bits[1].isdigit() \
            and re.fullmatch(r'[a-z0-9]{0,2}', bits[2]) \
            and bits[3].isdigit():
        return bits[1], bits[2], bits[3]
    return None


class Census:
    def __init__(self):
        self.unrecognized = []          # every instance listed, never silent
        self.tag_counter = Counter()
        self.anomalies = []             # label anomalies etc.
        self.notes = []

    def anomaly(self, kind, where, detail):
        self.anomalies.append({"kind": kind, "where": where, "detail": detail})

    def unknown(self, where, what):
        self.unrecognized.append({"where": where, "what": what})


def clean_text(raw_html, stats=None, where=""):
    """Strip tags/entities, rejoin hyphenation, collapse whitespace."""
    txt = TAG_RE.sub(' ', raw_html)
    if '<' in txt or '>' in txt:
        # unmatched tag debris — hard evidence of markup we don't understand
        raise AssertionError("angle bracket residue at %s: %r" % (where, txt[:200]))
    txt = html.unescape(txt).replace('\xa0', ' ')
    nb = len(BS_JOIN_RE.findall(txt))
    txt = BS_JOIN_RE.sub('', txt)
    ns = len(SL_JOIN_RE.findall(txt))
    txt = SL_JOIN_RE.sub('', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    if stats is not None:
        stats["bs"] += nb
        stats["sl"] += ns
    return txt


def parse_file(part, census, strict):
    path = os.path.join(BASE, "bakar%03d.htm" % part)
    with open(path, encoding="utf-8") as f:
        doc = f.read()

    all_marks = []
    n_level_comments = len(re.findall(r'<!X?Level \d>', doc))
    for m in MARK_RE.finditer(doc):
        span_id, xflag, level = int(m.group(1)), m.group(2), int(m.group(3))
        label = m.group(4).strip()
        assert span_id == level, "h%d vs Level %d in %s" % (span_id, level, path)
        prefix = LEVEL_PREFIX[level] + ": "
        if label.startswith(prefix):
            value = label[len(prefix):].strip()
        elif label == LEVEL_PREFIX[level] + ":":
            value = ""  # e.g. "Column:" with empty value at VT_Lev._26_43_96__55
            census.anomaly("empty-marker-value", "part%03d@%d" % (part, m.start()),
                           "level %d label %r anchors %r/%r" %
                           (level, label, m.group(5), m.group(6)))
        else:
            census.unknown("part%03d@%d" % (part, m.start()),
                           "label %r does not match level %d" % (label, level))
            continue
        all_marks.append({
            "level": level, "value": value,
            "logical": m.group(5), "physical": m.group(6),
            "start": m.start(), "end": m.end()})
    n_skipped = len([u for u in census.unrecognized
                     if u["where"].startswith("part%03d@" % part)])
    assert len(all_marks) + n_skipped == n_level_comments, \
        "part%03d: %d <!Level> comments but %d parsed markers (+%d listed)" % (
            part, n_level_comments, len(all_marks), n_skipped)
    if not all_marks:
        # unstructured file (e.g. title page) — capture leniently
        body = re.sub(r'(?is)<script.*?</script>', ' ', doc)
        txt = clean_text(body, where="part%03d(unstructured)" % part)
        return {"part": part, "file": os.path.basename(path),
                "structured": False, "text_chars": len(txt),
                "text_head": txt[:300]}

    # footer cut: first footer marker AFTER the last structural marker
    tail_from = all_marks[-1]["end"]
    cut = len(doc)
    for pat in ('<DIV ALIGN=RIGHT>', '<HR><BR>This text is part'):
        i = doc.find(pat, tail_from)
        if i != -1:
            cut = min(cut, i)
    # head/tail slices must carry no Georgian scripture
    head = clean_text(re.sub(r'(?is)<script.*?</script>', ' ',
                             doc[:all_marks[0]["start"]]),
                      where="part%03d(head)" % part)
    tail = clean_text(doc[cut:], where="part%03d(tail)" % part)
    for nm, sl in (("head", head), ("tail", tail)):
        if GEO_RE.search(sl):
            census.anomaly("georgian-outside-units", "part%03d %s" % (part, nm),
                           sl[:200])

    # tag census over the working region
    for tm in TAG_RE.finditer(doc[all_marks[0]["start"]:cut]):
        name = tm.group(2).lower()
        census.tag_counter[name] += 1
        if not (name in KNOWN_TAGS or name.startswith('!')):
            census.unknown("part%03d@%d" % (part, tm.start()),
                           "tag %r" % tm.group(0)[:80])

    struct = [m for m in all_marks if m["level"] <= 4]
    inner = [m for m in all_marks if m["level"] >= 5]

    # per-unit segment: from marker end to next struct marker start (or cut),
    # with inner (page/col/line) markers excised.
    def segment(i):
        s = struct[i]["end"]
        e = struct[i + 1]["start"] if i + 1 < len(struct) else cut
        parts_, pos = [], s
        for im in inner:
            if im["start"] >= e:
                break
            if im["start"] >= pos:
                parts_.append(doc[pos:im["start"]])
                pos = im["end"]
        parts_.append(doc[pos:e])
        return ''.join(parts_), doc[s:e]

    book = None
    result = {"part": part, "file": os.path.basename(path), "structured": True,
              "collection": None, "book_label": None,
              "book_preamble": None, "chapters": OrderedDict(),
              "rejoins": {"bs": 0, "sl": 0},
              "intrusions": []}
    stats = result["rejoins"]
    n_books = 0
    cur_chap = None

    for i, mk in enumerate(struct):
        text, raw_seg = segment(i)
        txt = clean_text(text, stats,
                         where="part%03d %s %s" % (part, LEVEL_PREFIX[mk["level"]],
                                                   mk["value"]))
        if mk["level"] == 1:
            result["collection"] = mk["value"]
            if txt:
                census.anomaly("text-in-collection-unit", "part%03d" % part,
                               txt[:200])
        elif mk["level"] == 2:
            n_books += 1
            result["book_label"] = mk["value"]
            result["book_anchor"] = mk["logical"]
            result["book_prov"] = phys_parts(mk["physical"])
            if txt:
                result["book_preamble"] = txt
        elif mk["level"] == 3:
            key = mk["value"]
            if key in result["chapters"]:
                census.anomaly("duplicate-chapter-label",
                               "part%03d %s" % (part, result["book_label"]), key)
                key = key + "#dup"
            cur_chap = {"anchor": mk["logical"],
                        "prov": phys_parts(mk["physical"]),
                        "preamble": txt if txt else None,
                        "verses": OrderedDict(),
                        "verse_prov": OrderedDict()}
            result["chapters"][key] = cur_chap
        elif mk["level"] == 4:
            if cur_chap is None:
                # verse directly under book (Ps epigraph, Odes) — synthetic ""
                if "" not in result["chapters"]:
                    result["chapters"][""] = {"anchor": None, "prov": None,
                                              "preamble": None,
                                              "verses": OrderedDict(),
                                              "verse_prov": OrderedDict()}
                    census.anomaly("verses-without-chapter",
                                   "part%03d %s" % (part, result["book_label"]),
                                   "first such verse label: %r" % mk["value"])
                cur_chap = result["chapters"][""]
            vkey = mk["value"]
            if vkey in cur_chap["verses"]:
                n = 2
                while "%s#dup%d" % (vkey, n) in cur_chap["verses"]:
                    n += 1
                census.anomaly("duplicate-verse-label",
                               "part%03d %s ch %s" % (part, result["book_label"],
                                                      mk["logical"]), vkey)
                vkey = "%s#dup%d" % (vkey, n)
            cur_chap["verses"][vkey] = txt
            cur_chap["verse_prov"][vkey] = "_".join(phys_parts(mk["physical"]) or
                                                    ("?",))
            # anchor-vs-label coherence
            la = mk["logical"]
            if la and not la.endswith("_" + mk["value"]):
                census.anomaly("anchor-label-mismatch",
                               "part%03d %s" % (part, result["book_label"]),
                               "label %r anchor %r" % (mk["value"], la))
            # non-scripture span classes inside a verse segment
            for cls in ("mxagl16", "mxagt16"):
                for hit in re.finditer('<span id=%s>' % cls, raw_seg):
                    frag = raw_seg[hit.start():hit.start() + 400]
                    frag = frag[:frag.rfind('>') + 1]  # drop any cut-off tag
                    ctx = clean_text(frag, where="intrusion")
                    result["intrusions"].append(
                        {"class": cls, "chapter": mk["logical"],
                         "verse_label": mk["value"], "sample": ctx[:120]})
                    break  # one sample per class per verse is enough; count=verses listed

    if strict:
        assert n_books == 1, "part%03d has %d Book markers" % (part, n_books)
    return result


# ---------------------------------------------------------------- census ----

ALLOWED_CP = re.compile(r'[Ⴀ-ჿ -~]')


def label_class(v):
    if VERSE_NUM_RE.match(v):
        return "numeric"
    if VERSE_CONT_RE.match(v):
        return "continuation"
    if VERSE_RUBRIC_RE.match(v):
        return "rubric"
    if v == "expl.":
        return "colophon"
    if VERSE_PAREN_RE.match(v):
        return "paren"
    if VERSE_GLUED_RE.match(v):
        return "glued"
    return "other"


def census_book(bk, census, kjv, cu):
    label = bk["book_label"]
    part = bk["part"]
    out = {"part": part, "label": label, "collection": bk["collection"],
           "chapters": OrderedDict(), "label_classes": Counter(),
           "prologue_chapters": [], "n_numeric_chapters": 0,
           "rejoins": bk["rejoins"], "intrusion_count": len(bk["intrusions"])}
    kjv_idx = PART_TO_KJV.get(part)
    ref = None
    ref_name = None
    if label == "Ps.":
        ref = cu[18]["chapters"]
        ref_name = "cu_elizabeth (LXX)"
    elif kjv_idx is not None:
        ref = kjv[kjv_idx]["chapters"]
        ref_name = "en_kjv"
    out["reference"] = ref_name

    numeric_chaps = {}
    for ckey, ch in bk["chapters"].items():
        vlabels = list(ch["verses"].keys())
        classes = Counter(label_class(v.split('#dup')[0]) for v in vlabels)
        out["label_classes"] += classes
        nums = []
        for v in vlabels:
            v0 = v.split('#dup')[0]
            m = VERSE_NUM_RE.match(v0) or VERSE_GLUED_RE.match(v0)
            if m:
                nums.append(int(m.group(1)))
        info = {"n_units": len(vlabels), "n_numeric": len(nums),
                "max_num": max(nums) if nums else 0,
                "classes": dict(classes),
                "has_preamble": bool(ch["preamble"])}
        # sequence anomalies among numeric(+glued) labels
        seen = set()
        prev = 0
        for n in nums:
            if n in seen:
                census.anomaly("repeated-number",
                               "part%03d %s ch %s" % (part, label, ckey), n)
            seen.add(n)
            if n < prev:
                census.anomaly("out-of-order",
                               "part%03d %s ch %s" % (part, label, ckey),
                               "%d after %d" % (n, prev))
            prev = max(prev, n)
        gaps = sorted(set(range(1, info["max_num"] + 1)) - seen)
        if gaps:
            info["gaps"] = gaps
            census.anomaly("gap", "part%03d %s ch %s" % (part, label, ckey),
                           "missing numbers %s (max %d)" % (gaps, info["max_num"]))
        for v in vlabels:
            v0 = v.split('#dup')[0]
            c = label_class(v0)
            if c in ("glued", "other", "paren"):
                census.anomaly("label-" + c,
                               "part%03d %s ch %s" % (part, label, ckey), v0)
        if ckey and not ckey.split('#dup')[0].isdigit():
            out["prologue_chapters"].append(ckey)
        else:
            if ckey:
                numeric_chaps[int(ckey.split('#dup')[0])] = info
        out["chapters"][ckey] = info

    out["n_numeric_chapters"] = len(numeric_chaps)
    if ref is not None:
        out["ref_chapters"] = len(ref)
        diffs = []
        for cn in sorted(set(list(numeric_chaps.keys()) +
                             list(range(1, len(ref) + 1)))):
            got = numeric_chaps.get(cn)
            want = len(ref[cn - 1]) if cn <= len(ref) else None
            g = got["n_numeric"] if got else None
            if g != want:
                diffs.append({"chapter": cn, "bakar_numeric": g,
                              "bakar_max": got["max_num"] if got else None,
                              "ref": want})
        out["vs_ref_diffs"] = diffs
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    census = Census()
    with open(KJV_PATH, encoding="utf-8") as f:
        kjv = json.load(f)
    with open(CU_PATH, encoding="utf-8") as f:
        cu = json.load(f)

    books = OrderedDict()
    extras = OrderedDict()
    for part in list(FRONT_PARTS) + list(SCRIPTURE_PARTS) + list(LIT_PARTS):
        strict = part in SCRIPTURE_PARTS
        bk = parse_file(part, census, strict)
        key = "part%03d" % part
        if part in SCRIPTURE_PARTS:
            books[key] = bk
        else:
            extras[key] = bk
        sys.stderr.write("parsed %s (%s)\n" %
                         (key, bk.get("book_label") or "unstructured"))

    # ---- corpus-wide text censuses (scripture verse text + preambles) ----
    cp_counter = Counter()
    punct = Counter()
    per_book = OrderedDict()
    for key, bk in books.items():
        if not bk["structured"]:
            continue
        texts = []
        if bk.get("book_preamble"):
            texts.append(("book_preamble", bk["book_preamble"]))
        for ckey, ch in bk["chapters"].items():
            if ch["preamble"]:
                texts.append(("pre %s" % ckey, ch["preamble"]))
            for v, t in ch["verses"].items():
                texts.append(("%s:%s" % (ckey, v), t))
        blob = "\n".join(t for _, t in texts)
        for chx in blob:
            if not ALLOWED_CP.match(chx) and chx != '\n':
                cp_counter[chx] += 1
        punct["*"] += blob.count("*")
        punct[":_"] += blob.count(":_")
        punct["//"] += blob.count("//")
        punct["U+0559"] += blob.count("ՙ")
        punct["U+0302"] += blob.count("̂")
        punct["U+0303"] += blob.count("̃")
        punct["backslash-residue"] += blob.count("\\")
        per_book[key] = census_book(bk, census, kjv, cu)

    total_units = sum(sum(len(c["verses"]) for c in bk["chapters"].values())
                      for bk in books.values() if bk["structured"])

    cp_inventory = [{"cp": "U+%04X" % ord(c),
                     "char": c,
                     "name": unicodedata.name(c, "?"),
                     "count": n}
                    for c, n in cp_counter.most_common()]

    raw = {"meta": {"source": "TITUS Biblia Bacarii local harvest 2026-07-20",
                    "generator": "tools/extract_bakar.py",
                    "total_verse_units": total_units},
           "books": books, "extras": extras}
    with open(os.path.join(OUT_DIR, "bakar_raw.json"), "w",
              encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=1)

    cens = {"total_verse_units": total_units,
            "per_book": per_book,
            "punctuation": dict(punct),
            "codepoints_outside_georgian_ascii": cp_inventory,
            "tag_census": dict(census.tag_counter),
            "unrecognized": census.unrecognized,
            "anomalies": census.anomalies,
            "intrusions": {k: b["intrusions"] for k, b in books.items()
                           if b["structured"] and b["intrusions"]}}
    with open(os.path.join(OUT_DIR, "bakar_census.json"), "w",
              encoding="utf-8") as f:
        json.dump(cens, f, ensure_ascii=False, indent=1)

    print("verse units: %d" % total_units)
    print("anomalies: %d, unrecognized: %d" %
          (len(census.anomalies), len(census.unrecognized)))
    for u in census.unrecognized[:50]:
        print("UNRECOGNIZED:", u)


if __name__ == "__main__":
    main()
