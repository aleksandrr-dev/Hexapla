"""Original-language interlinear: word-aligned Strong's + morphology tags
for the app's Greek NT (grc_byz.json) and Hebrew Tanakh (he_wlc.json).

Sources:
- Greek: byztxt/byzantine-majority-text (public domain), csv-unicode/
  strongs/with-parsing — word, Strong's number, Robinson parse per verse.
- Hebrew: openscriptures/morphhb (morphology CC-BY 4.0; WLC text public
  domain) — OSIS XML, <w lemma="b/7225" morph="HR/Ncfsa">; qere readings
  appear as nested <w> inside <note><rdg>, in the same document order as
  the app asset (which prints ketiv then qere inline).

Tokenization contract (MUST match Interlinear.kt): a token is a maximal
run of Unicode letters and combining marks containing at least one
letter. Maqaf, sof pasuq, paseq and all punctuation split tokens.

Alignment: per verse, source words are matched positionally after both
sides tokenize; the verse is verified by normalized text comparison
(case/accents/points stripped). Verses that fail verification emit no
tags (fail soft), and are reported.

Output (assets/):
- interlinear_gr.json / interlinear_he.json:
  {"<bookIdx>": [ [ "tag tag ...", ... verses ], ... chapters ]}
  where each word tag is "<strongs>|<morph>" ("|<morph>" may be empty;
  a bare "-" means no data for that word).

Usage: python build_interlinear.py <morphhb-dir> <byztxt-dir>
"""
import csv
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "app", "src", "main", "assets")

OSIS_W = "{http://www.bibletechnologies.net/2003/OSIS/namespace}w"
OSIS_V = "{http://www.bibletechnologies.net/2003/OSIS/namespace}verse"

HEB_BOOKS = [(0, "Gen"), (1, "Exod"), (2, "Lev"), (3, "Num"), (4, "Deut"),
             (5, "Josh"), (6, "Judg"), (7, "Ruth"), (8, "1Sam"), (9, "2Sam"),
             (10, "1Kgs"), (11, "2Kgs"), (12, "1Chr"), (13, "2Chr"),
             (14, "Ezra"), (15, "Neh"), (16, "Esth"), (17, "Job"), (18, "Ps"),
             (19, "Prov"), (20, "Eccl"), (21, "Song"), (22, "Isa"),
             (23, "Jer"), (24, "Lam"), (25, "Ezek"), (26, "Dan"), (27, "Hos"),
             (28, "Joel"), (29, "Amos"), (30, "Obad"), (31, "Jonah"),
             (32, "Mic"), (33, "Nah"), (34, "Hab"), (35, "Zeph"), (36, "Hag"),
             (37, "Zech"), (38, "Mal")]

GRK_BOOKS = [(39, "MAT"), (40, "MAR"), (41, "LUK"), (42, "JOH"), (43, "ACT"),
             (44, "ROM"), (45, "1CO"), (46, "2CO"), (47, "GAL"), (48, "EPH"),
             (49, "PHP"), (50, "COL"), (51, "1TH"), (52, "2TH"), (53, "1TI"),
             (54, "2TI"), (55, "TIT"), (56, "PHM"), (57, "HEB"), (58, "JAM"),
             (59, "1PE"), (60, "2PE"), (61, "1JO"), (62, "2JO"), (63, "3JO"),
             (64, "JUD"), (65, "REV")]

GRK_WORD = re.compile(r"(\S+)\s+(\d+)\s+\{([^}]*)\}")


def tokens(text):
    """Tokenizer contract shared with Interlinear.kt."""
    out, cur = [], []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("M"):
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return [t for t in out if any(unicodedata.category(c).startswith("L") for c in t)]


def norm(w):
    """Strip case, accents, vowel points; fold final sigma."""
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if not unicodedata.category(c).startswith("M"))
    return w.replace("ς", "σ")


def heb_strongs(lemma):
    """morphhb lemma 'c/b/929', '1254 a', '853 b' -> main Strong's 'H929'.
    Aramaic sections keep the same numbering."""
    main = lemma.split("/")[-1]
    m = re.match(r"(\d+)", main.strip())
    return "H" + m.group(1) if m else ""


def build_hebrew(morphhb_dir, bible):
    out = {}
    verses_total = verses_tagged = 0
    failures = []
    for b, name in HEB_BOOKS:
        tree = ET.parse(os.path.join(morphhb_dir, "wlc", f"{name}.xml"))
        book_out = [["" for _ in ch] for ch in bible[b]["chapters"]]
        for verse in tree.iter(OSIS_V):
            _, ch, vs = verse.get("osisID").split(".")
            ch, vs = int(ch) - 1, int(vs) - 1
            verses_total += 1
            try:
                asset_toks = tokens(bible[b]["chapters"][ch][vs])
            except IndexError:
                failures.append(f"{name} {ch+1}:{vs+1} not in asset")
                continue
            ws = list(verse.iter(OSIS_W))
            if len(ws) != len(asset_toks):
                failures.append(f"{name} {ch+1}:{vs+1} count {len(asset_toks)} vs {len(ws)}")
                continue
            # verify text: morphhb words use '/' as segment separator
            okay = all(
                norm(w.text.replace("/", "") if w.text else "") == norm(t)
                for w, t in zip(ws, asset_toks)
            )
            if not okay:
                failures.append(f"{name} {ch+1}:{vs+1} text mismatch")
                continue
            tags = []
            for w in ws:
                s = heb_strongs(w.get("lemma", ""))
                m = w.get("morph", "")
                tags.append(f"{s}|{m}" if s else "-")
            book_out[ch][vs] = " ".join(tags)
            verses_tagged += 1
        out[str(b)] = book_out
    return out, verses_total, verses_tagged, failures


def build_greek(byz_dir, bible):
    out = {}
    verses_total = verses_tagged = 0
    failures = []
    src_dir = os.path.join(byz_dir, "csv-unicode", "strongs", "with-parsing")
    for b, name in GRK_BOOKS:
        rows = list(csv.DictReader(open(os.path.join(src_dir, f"{name}.csv"),
                                        encoding="utf-8")))
        book_out = [["" for _ in ch] for ch in bible[b]["chapters"]]
        for r in rows:
            ch, vs = int(r["chapter"]) - 1, int(r["verse"]) - 1
            verses_total += 1
            try:
                asset_toks = tokens(bible[b]["chapters"][ch][vs])
            except IndexError:
                failures.append(f"{name} {ch+1}:{vs+1} not in asset")
                continue
            src = GRK_WORD.findall(r["text"])
            if len(src) != len(asset_toks):
                failures.append(f"{name} {ch+1}:{vs+1} count {len(asset_toks)} vs {len(src)}")
                continue
            if not all(norm(w) == norm(t) for (w, _, _), t in zip(src, asset_toks)):
                failures.append(f"{name} {ch+1}:{vs+1} text mismatch")
                continue
            book_out[ch][vs] = " ".join(f"G{n}|{m}" for _, n, m in src)
            verses_tagged += 1
        out[str(b)] = book_out
    return out, verses_total, verses_tagged, failures


def main(morphhb_dir, byz_dir):
    wlc = json.load(open(os.path.join(ASSETS, "bibles", "he_wlc.json"), encoding="utf-8"))
    byz = json.load(open(os.path.join(ASSETS, "bibles", "grc_byz.json"), encoding="utf-8"))

    he, ht, hg, hf = build_hebrew(morphhb_dir, wlc)
    gr, gt, gg, gf = build_greek(byz_dir, byz)

    for fname, data in (("interlinear_he.json", he), ("interlinear_gr.json", gr)):
        with open(os.path.join(ASSETS, fname), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Hebrew: {hg}/{ht} verses tagged ({100*hg/ht:.3f}%), {len(hf)} skipped")
    for x in hf[:10]:
        print("   ", x)
    print(f"Greek:  {gg}/{gt} verses tagged ({100*gg/gt:.3f}%), {len(gf)} skipped")
    for x in gf[:10]:
        print("   ", x)
    for fname in ("interlinear_he.json", "interlinear_gr.json"):
        sz = os.path.getsize(os.path.join(ASSETS, fname))
        print(f"{fname}: {sz/1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
