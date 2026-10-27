# -*- coding: utf-8 -*-
"""Restore the nasal bars that en_tyndale.json lost, from the EEBO-TCP witness.

    python tools/restore_tyndale_nasal_bars.py                 # dry run (default)
    python tools/restore_tyndale_nasal_bars.py --show 20       # + 20 sample verses
    python tools/restore_tyndale_nasal_bars.py --apply         # write the asset

THE DEFECT
----------
Tyndale's printers abbreviated a nasal with a bar over the vowel before it:
«thē» = them, «mē» = men, «whō» = whom, «yōge» = yonge, «groūd» = ground.
The digitization the asset comes from dropped the bar and kept the letters,
so Luke 21:10 reads «Then sayd he vnto the:» where the print says «vnto thē»
= THEM. Readers see a wrong word and the narrator says it.

THE WITNESS (never the KJV)
---------------------------
EEBO-TCP keeps each bar as <g ref="char:cmbAbbrStroke"> (U+0304):
    A68940  The Newe Testament, 1534      A13203  Pentateuch, 1530
    A16000  Jonas
together exactly tyn's 33 books. Files in
C:/Projects/Hexapla-releases/research/_witness/tyndale_tcp/ (raw GitHub,
textcreationpartnership/<ID>). Each TCP book is matched to its tyn book by
content, each chapter token-aligned (difflib) to the tyn chapter, and a tyn
token is changed ONLY where it equals the TCP token with the bar removed
(same letters, same place). Anything else is left exactly as it is.

THE EXPANSION (thorn precedent, fix_tyndale_thorn.py: the asset spells the
abbreviation out rather than carrying the mark)
    bar before b/p/m          -> m        (nōbre -> nombre)
    bar before another letter -> n        (groūd -> ground, yōge -> yonge)
    bar at the word's end     -> m or n, whichever spelled-out form the two
                                 texts themselves use; if BOTH exist
                                 («thē»: them / then) the KJV word at the
                                 aligned place decides, and a site it cannot
                                 decide is left untouched and reported.
A bar over a consonant is reported, never changed. «thē» the KJV cannot
decide: «Thē» opening a sentence = Then, after a preposition = them, else
reported. A TCP chapter agreeing < 0.5 with tyn, and any match block
shorter than 3 tokens, is skipped.
"""
import argparse
import html
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ASSET = ROOT / "app/src/main/assets/bibles/en_tyndale.json"
KJV = ROOT / "app/src/main/assets/bibles/en_kjv.json"
WIT = Path("C:/Projects/Hexapla-releases/research/_witness/tyndale_tcp")
TCP_IDS = ("A68940", "A13203", "A16000")
BACKUP = Path("C:/Projects/Hexapla-releases/asset-backups/en_tyndale.json.prenasal.bak")
BAR = "\u0304"
TOK = re.compile(r"[A-Za-z\u0304\u017f\u25cf]+")


def tcp_text(xml):
    """TEI -> plain text with the bar kept as U+0304 and notes/heads dropped."""
    x = re.sub(r"<note\b.*?</note>", " ", xml, flags=re.S)
    x = re.sub(r"<head\b.*?</head>", " ", x, flags=re.S)
    x = re.sub(r'<g ref="char:cmbAbbrStroke">[^<]*</g>', BAR, x)
    x = re.sub(r'<g ref="char:EOL(un)?hyphen"\s*/>', "", x)
    x = re.sub(r"<gap\b.*?</gap>", "\u25cf", x, flags=re.S)
    x = re.sub(r"<[^>]+>", " ", x)
    return html.unescape(x).replace("\u017f", "s")


def tcp_books():
    """[(label, [chapter_text, ...]), ...] over the three witnesses."""
    out = []
    for tid in TCP_IDS:
        xml = (WIT / f"{tid}.xml").read_text(encoding="utf-8")
        body = xml[xml.find("<body"):]
        chunks = re.split(r'<div n="[^"]*" type="book">', body)
        if len(chunks) == 1:  # Jonas: no book div, chapters only
            chunks = ["", body]
        for bi, ch in enumerate(chunks[1:]):
            chaps = re.split(r'<div n="[^"]*" type="chapter">', ch)[1:]
            # Philemon, 2-3 John, Jude: one chapter, no chapter div
            out.append((f"{tid}#{bi}", [tcp_text(c) for c in (chaps or [ch])]))
    return out


def base(w):
    return w.replace(BAR, "").replace("\u017f", "s").lower()


def verse_tokens(chapter):
    """[(verse_idx, match_obj), ...] for a tyn chapter."""
    return [(vi, m) for vi, v in enumerate(chapter) if v for m in TOK.finditer(v)]


PREP = {"vnto", "unto", "to", "of", "with", "wt", "amonge", "among", "for", "from", "fro",
        "by", "before", "after", "vpon", "apon", "on", "in", "into", "at", "agaynst",
        "betwene", "thorow", "aboute", "over", "ouer", "vnder", "towarde"}


def expand(word, vocab, kjv_word, prev_word, sentence_start):
    """thē -> them etc.  Returns (new_word, reason) or (None, why_not).

    Every bar that has a letter after it is decided by that letter; only a
    bar on the word's LAST letter needs vocab / KJV / position.
    """
    out, why = "", "rule"
    for i, ch in enumerate(word):
        if ch != BAR:
            out += ch
            continue
        if i == 0 or word[i - 1].lower() not in "aeiouy":
            return None, "bar not over a vowel"
        tail = word[i + 1:].replace(BAR, "")
        if tail:
            out += "m" if tail[0].lower() in "bpm" else "n"
            continue
        cands = [out + c for c in "mn" if (out + c).lower() in vocab]
        if len(cands) == 1:
            return cands[0], "vocab"
        if kjv_word:
            hit = [out + c for c in "mn" if kjv_word.startswith((out + c).lower())]
            if len(hit) == 1:
                return hit[0], "kjv"
        if out.lower() == "the":
            # thē: «Thē» opening a sentence is Then; after a preposition it
            # is them (a preposition never governs «then»).
            if sentence_start and out[0].isupper():
                return out + "n", "position"
            if prev_word in PREP:
                return out + "m", "position"
        return None, "undecided " + "/".join(out + c for c in "mn")
    return out, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--show", type=int, default=0)
    a = ap.parse_args()

    tyn = json.loads(ASSET.read_text(encoding="utf-8"))
    kjv = json.loads(KJV.read_text(encoding="utf-8"))
    books = tcp_books()

    vocab = Counter()
    for _, chs in books:
        for c in chs:
            vocab.update(w.lower() for w in TOK.findall(c) if BAR not in w)
    for b in tyn:
        for c in b["chapters"]:
            for v in c:
                if v:
                    vocab.update(w.lower() for w in TOK.findall(v))

    present = [i for i, b in enumerate(tyn) if any(any(v for v in c) for c in b["chapters"])]
    edits = {}            # (b, c, v) -> [(start, end, old, new, reason)]
    stats, notdone = Counter(), Counter()
    samples = defaultdict(list)
    chap_ratio = []
    used = set()
    for label, chs in books:
        head = [base(w) for w in TOK.findall(chs[0])][:300]
        best, bi = 0, None
        for i in present:
            if i in used:
                continue
            t = [base(w) for w in TOK.findall(" ".join(v for v in tyn[i]["chapters"][0] if v))][:300]
            r = SequenceMatcher(None, head, t, autojunk=False).ratio()
            if r > best:
                best, bi = r, i
        if bi is None or best < 0.5:
            print(f"!! {label}: no tyn book matches (best {best:.2f}) - skipped")
            continue
        used.add(bi)
        tb = tyn[bi]["chapters"]
        if len(tb) != len(chs):
            print(f"!! {tyn[bi]['name']}: tyn {len(tb)} chapters, TCP {len(chs)} - aligning the shorter prefix")
        for ci in range(min(len(tb), len(chs))):
            tt = verse_tokens(tb[ci])
            wt = TOK.findall(chs[ci])
            sm = SequenceMatcher(None, [base(m.group()) for _, m in tt], [base(w) for w in wt], autojunk=False)
            chap_ratio.append(sm.ratio())
            kch = kjv[bi]["chapters"][ci] if ci < len(kjv[bi]["chapters"]) else []
            if sm.ratio() < 0.5:
                print(f"   low agreement {sm.ratio():.2f}: {tyn[bi]['name']} {ci + 1} - skipped")
                continue
            for blk in sm.get_matching_blocks():
                if blk.size < 3:   # a lone matching token proves nothing
                    continue
                for k in range(blk.size):
                    vi, m = tt[blk.a + k]
                    w = wt[blk.b + k]
                    if BAR not in w or BAR in m.group():
                        continue
                    old = m.group()
                    # the KJV word at the same relative place, for thē only
                    kw = None
                    if vi < len(kch) and kch[vi]:
                        ktoks = [x.lower() for x in TOK.findall(re.sub(r"\{[^}]*\}", "", kch[vi]))]
                        vt = [x for x in TOK.findall(tb[ci][vi])]
                        pos = sum(1 for x in TOK.finditer(tb[ci][vi]) if x.start() < m.start())
                        vs = SequenceMatcher(None, [x.lower() for x in vt], ktoks, autojunk=False)
                        for op, a1, a2, b1, b2 in vs.get_opcodes():
                            if a1 <= pos < a2 and a2 - a1 == b2 - b1:
                                kw = ktoks[b1 + pos - a1]
                    before = tb[ci][vi][:m.start()]
                    pw = TOK.findall(before)
                    prev = pw[-1].lower() if pw else ""
                    start = not before.strip() or before.rstrip()[-1] in ".:?!"
                    new, why = expand(w, vocab, kw, prev, start)
                    if new is None:
                        notdone[(base(w), why)] += 1
                        continue
                    # keep the asset's own capitalisation
                    if old[:1].isupper():
                        new = new[:1].upper() + new[1:]
                    if new == old:
                        continue
                    edits.setdefault((bi, ci, vi), []).append((m.start(), m.end(), old, new, why))
                    stats[(old.lower(), new.lower(), why)] += 1
                    if len(samples[(old.lower(), new.lower())]) < 2:
                        samples[(old.lower(), new.lower())].append(f"{tyn[bi]['name']} {ci + 1}:{vi + 1}")

    rs = sorted(chap_ratio)
    print(f"books matched {len(used)}/{len(books)}; chapters aligned {len(rs)}; "
          f"token agreement min {rs[0]:.2f} median {rs[len(rs) // 2]:.2f}")
    print(f"verses to change {len(edits)}, tokens {sum(stats.values())}")
    for (o, n, why), c in stats.most_common(40):
        print(f"  {c:5d}  {o} -> {n}  [{why}]  {samples[(o, n)]}")
    print(f"not changed (reported): {sum(notdone.values())}")
    for (w, why), c in notdone.most_common(15):
        print(f"  {c:5d}  {w}  {why}")
    for (bi, ci, vi), ed in list(edits.items())[:a.show]:
        v = tyn[bi]["chapters"][ci][vi]
        new = v
        for s, e, o, n, _ in sorted(ed, reverse=True):
            new = new[:s] + n + new[e:]
        print(f"\n{tyn[bi]['name']} {ci + 1}:{vi + 1}\n  - {v}\n  + {new}")

    if not a.apply:
        print("\nDRY RUN - nothing written. --apply to write the asset.")
        return 0
    if not BACKUP.exists():
        shutil.copy2(ASSET, BACKUP)
    for (bi, ci, vi), ed in edits.items():
        v = tyn[bi]["chapters"][ci][vi]
        for s, e, o, n, _ in sorted(ed, reverse=True):
            assert v[s:e] == o, (bi, ci, vi, o)
            v = v[:s] + n + v[e:]
        tyn[bi]["chapters"][ci][vi] = v
    # the asset's own layout: indent 1, LF (Windows write_text would add CR)
    ASSET.write_text(json.dumps(tyn, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    back = json.loads(ASSET.read_text(encoding="utf-8"))
    orig = json.loads(BACKUP.read_text(encoding="utf-8"))
    diff = sum(1 for bi, b in enumerate(back) for ci, c in enumerate(b["chapters"])
               for vi, v in enumerate(c) if v != orig[bi]["chapters"][ci][vi])
    print(f"APPLIED; verses differing from backup {diff} (planned {len(edits)}); backup {BACKUP}")
    return 0 if diff == len(edits) else 1


if __name__ == "__main__":
    sys.exit(main())
