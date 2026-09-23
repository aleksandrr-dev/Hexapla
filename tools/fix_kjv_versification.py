"""Repair the shipped KJV assets' versification (2026-07-11).

The scrollmapper/thiagobodruk-lineage en_kjv.json is one verse SHORT in
six chapters (a verse of scripture is missing outright — most notably
Matthew 2:16, "Then Herod ... slew all the children") and one verse
LONG in four (non-KJV verse splits):

  short: Mt 2 (22/23), Mt 22 (45/46), Mt 26 (74/75),
         Mk 4 (40/41), Mk 7 (36/37), Mk 8 (37/38)
  long:  1 Sam 20 (43/42), 1 Kgs 22 (54/53), 3 Jn (15/14), Rev 12 (18/17)

Authentic counts confirmed against three sources: kaiserlik/kjv,
Crosswire/getbible KJV, and the printed KJV tradition. Because
red_letters.json and xrefs.json are indexed by TRUE KJV numbering,
these chapters were also off-by-one in red letters and cross-refs.

Repair strategy (minimal diff):
  - short chapters: locate the gap by verse-text alignment against
    kaiserlik and INSERT just the missing verse (kaiserlik text,
    <em>...</em> supplied-word markup converted to the asset's {...}
    convention);
  - long chapters: locate the non-KJV split and MERGE the two halves
    (verifying the join matches kaiserlik's verse text).

en_kjv_strongs.json gets the same 10 chapters rebuilt from kaiserlik's
tagged text (convert_strongs.py had reverted them to plain KJV because
their counts disagreed — i.e. they had no Strong's tags at all).

Usage: python fix_kjv_versification.py <kaiserlik-src-dir>
"""
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert_strongs import ORDER, extract_verses, clean, TAG

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLES = os.path.join(HERE, "..", "app", "src", "main", "assets", "bibles")


def norm(s):
    """Comparison form: notes/braces/tags/case/punctuation-insensitive."""
    s = TAG.sub("", s)
    s = re.sub(r"\{[^{}]*:[^{}]*\}", "", s)  # {x: y} translator margin notes
    s = re.sub(r"[{}]", "", s)               # {x} supplied words: keep the words
    s = re.sub(r"[^a-z0-9 ]", "", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def kaiser_plain(text):
    """kaiserlik verse -> plain asset style: strip Strong's tags, keep
    supplied words in {braces} like the rest of en_kjv.json."""
    text = TAG.sub("", clean_keep_em(text))
    text = re.sub(r"<em>\s*", "{", text)
    text = re.sub(r"\s*</em>", "}", text)
    return re.sub(r"\s+", " ", text).strip().replace(" ,", ",").replace(" .", ".")


def clean_keep_em(text):
    import html
    text = html.unescape(text)
    text = re.sub(r"</?(?!em\b)[a-zA-Z][^>]*>", "", text)
    text = re.sub(r"\[(?![HG]\d+\])[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def kaiser_chapter(src_dir, abbr, want_book_idx):
    _, flat = extract_verses(os.path.join(src_dir, abbr + ".json"), abbr)
    chapters = {}
    for (c, v), t in flat.items():
        chapters.setdefault(c, {})[v] = t
    return {c: [vs[i] for i in sorted(vs)] for c, vs in chapters.items()}


def find_gap(old, ref_plain):
    """old is one short. Return index where ref has a verse old lacks."""
    for i in range(len(ref_plain)):
        o = old[i] if i < len(old) else ""
        if sim(o, ref_plain[i]) < 0.55:
            # everything after i in old must match ref shifted by one
            tail_ok = all(
                sim(old[j], ref_plain[j + 1]) > 0.55 for j in range(i, len(old))
            )
            if tail_ok:
                return i
    raise SystemExit("gap not found")


def find_split(old, ref_plain):
    """old is one long. Return index i where old[i]+old[i+1] == ref[i],
    or None (the Rev 12:18 case: the extra verse belongs to the NEXT
    chapter's first verse, not to a split within this one)."""
    for i in range(len(ref_plain)):
        if sim(old[i], ref_plain[i]) < 0.9:
            joined = old[i] + " " + old[i + 1]
            if sim(joined, ref_plain[i]) > 0.85:
                return i
    return None


def main(src_dir):
    kjv_path = os.path.join(BIBLES, "en_kjv.json")
    strongs_path = os.path.join(BIBLES, "en_kjv_strongs.json")
    kjv = json.load(open(kjv_path, encoding="utf-8"))
    strongs = json.load(open(strongs_path, encoding="utf-8"))

    fixed = 0
    for bi, abbr in enumerate(ORDER):
        kch = kaiser_chapter(src_dir, abbr, bi)
        for ci, old in enumerate(kjv[bi]["chapters"]):
            ref_raw = kch.get(ci + 1)
            if ref_raw is None or len(old) == len(ref_raw):
                continue
            ref_plain = [kaiser_plain(v) for v in ref_raw]
            name = f"{kjv[bi]['name']} {ci + 1}"
            if len(old) == len(ref_raw) - 1:
                i = find_gap(old, ref_plain)
                new = old[:i] + [ref_plain[i]] + old[i:]
                print(f"{name}: inserted verse {i + 1}: {ref_plain[i][:60]}...")
            elif len(old) == len(ref_raw) + 1:
                i = find_split(old, ref_plain)
                if i is not None:
                    new = old[:i] + [old[i] + " " + old[i + 1]] + old[i + 2:]
                    print(f"{name}: merged non-KJV split at verse {i + 1}")
                else:
                    # Extra last verse is the next chapter's opening
                    # (KJV Rev 13:1 "And I stood upon the sand of the sea…").
                    nxt = kjv[bi]["chapters"][ci + 1]
                    ref_next = kaiser_plain(kch[ci + 2][0])
                    moved = old[-1] + " " + nxt[0]
                    assert sim(moved, ref_next) > 0.85, (name, moved[:60], ref_next[:60])
                    new = old[:-1]
                    kjv[bi]["chapters"][ci + 1][0] = moved
                    strongs[bi]["chapters"][ci + 1][0] = clean(kch[ci + 2][0])
                    print(f"{name}: moved trailing verse into {kjv[bi]['name']} {ci + 2}:1")
            else:
                raise SystemExit(f"{name}: unexpected count {len(old)} vs {len(ref_raw)}")
            assert len(new) == len(ref_raw)
            # every verse must now match kaiserlik closely
            for v, (a, b) in enumerate(zip(new, ref_plain)):
                assert sim(a, b) > 0.55, (name, v + 1, a[:50], b[:50])
            kjv[bi]["chapters"][ci] = new
            # rebuild the same chapter in the Strong's asset from tagged text
            strongs[bi]["chapters"][ci] = [clean(v) for v in ref_raw]
            fixed += 1

    assert fixed == 10, fixed
    # final gate: canon counts equal kaiserlik everywhere
    for bi, abbr in enumerate(ORDER):
        kch = kaiser_chapter(src_dir, abbr, bi)
        for ci, ch in enumerate(kjv[bi]["chapters"]):
            if ci + 1 in kch:
                assert len(ch) == len(kch[ci + 1]), (abbr, ci + 1)
                assert len(strongs[bi]["chapters"][ci]) == len(kch[ci + 1])

    json.dump(kjv, open(kjv_path, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    json.dump(strongs, open(strongs_path, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"fixed {fixed} chapters in both assets")


if __name__ == "__main__":
    main(sys.argv[1])
