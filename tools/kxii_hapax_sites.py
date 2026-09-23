# -*- coding: utf-8 -*-
"""kxii_hapax_sites.py - resolve EXPLICIT (book, chapter, verse, word) sites to
strip + mark box, and attach a ring control and an <e> control from the SAME
strip, ready for kxii_fixed_sheet.py.

    python tools/kxii_hapax_sites.py --sites queue.json --out marks.json

`queue.json` is
    [{"chunk": "research/karlxii_tobit.md", "name": "Tobit",
      "ch": 1, "v": 21, "word": "forsmadelse", "label": "tob_1_21"}, ...]
`word` is matched DIACRITIC-BLIND (folded), so write it in ASCII.

## WHY

kxii_sites.py does this anchoring already, but only for sites it parses out of a
witness diff report. The eight books with no witness have no such report - their
sites come from kxii_hapax.py - and faking a report file to reach the anchor was
how a previous pass nearly mislocated two crops.

⚠ It LOCATES. It never decides ring vs <e>. Every emitted box still has to be
read at 9x beside its controls. A site it cannot anchor is REPORTED, not guessed.
"""
import argparse
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kxii_sites import fold, load_tsv, parse_chunk, anchor, tighten
from PIL import Image

TSV = r"C:\Projects\Hexapla-releases\research\_ocr_kxii\tsv"
STRIPROOT = r"C:\Projects\Hexapla-releases\research\_strips_kxii"

# Controls must be certain by LEXICON, never by the vowel under dispute.
RING_CONTROLS = ["pa", "sadana", "tha", "matte", "gafwo", "nagot", "star"]
E_CONTROLS = ["nar", "an", "ar", "har", "battre", "aro", "vth"]
# 'ar'/'aro' are only fallbacks - they have real rivals in this print.
RING_SAFE = {"pa", "sadana", "nagot"}
E_SAFE = {"nar", "an", "har"}


def strip_cache(dirs):
    cache = {}
    for d in dirs:
        for s in sorted(glob.glob(os.path.join(d, "*.png"))):
            p = os.path.join(TSV, os.path.splitext(os.path.basename(s))[0] + ".tsv")
            if not os.path.isfile(p):
                continue
            toks = load_tsv(p)
            for t in toks:
                t["f"] = fold(t["text"])
            cache[s] = [t for t in toks if t["f"]]
    return cache


def markbox(strip, tok):
    wbox = [tok["left"], tok["top"], tok["left"] + tok["width"],
            tok["top"] + int(tok["height"] * 0.62)]
    return tighten(Image.open(strip), wbox), wbox


def pick_control(strip, toks, wanted, safe, used, n=2):
    """Up to n controls from `wanted` whose marks are isolable on this strip.

    Two exemplars per class, not one: a single control that happens to be
    lightly inked reads as the other class, and a sheet carrying one of each
    then has no way to show it.
    """
    got = []
    for w in wanted:
        for t in toks:
            if t["f"] != w or id(t) in used:
                continue
            mb, _ = markbox(strip, t)
            if mb:
                used.add(id(t))
                got.append({"form": w, "box": mb, "safe": w in safe,
                            "ocr": t["text"]})
                if len(got) >= n:
                    return got
    return got


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sites", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-score", type=float, default=0.40)
    ap.add_argument("--strips", default=STRIPROOT)
    args = ap.parse_args(argv)

    queue = json.load(io.open(args.sites, encoding="utf-8"))
    cache = strip_cache(sorted(glob.glob(os.path.join(args.strips, "*"))))
    chunks = {}

    out, weak = [], []
    for q in queue:
        key = (q["chunk"], q["name"])
        if key not in chunks:
            chunks[key] = parse_chunk(os.path.join(
                r"C:\Projects\Hexapla-releases", q["chunk"]), q["name"])
        text = chunks[key].get(q["ch"], {}).get(q["v"])
        if not text:
            weak.append((q["label"], "verse not found in chunk"))
            continue
        vw = [fold(w) for w in text.split() if fold(w)]
        target = fold(q["word"])
        if target not in vw:
            weak.append((q["label"], "word not in verse after folding"))
            continue
        pos = vw.index(target)
        best = (0.0, None, -1)
        for s, toks in cache.items():
            r, i = anchor(vw, toks)
            if r > best[0]:
                best = (r, s, i)
        score, strip, start = best
        if strip is None or start < 0 or score < args.min_score:
            weak.append((q["label"], "anchor score %.2f" % score))
            continue
        toks = cache[strip]
        idx = start + pos
        if idx >= len(toks):
            weak.append((q["label"], "index past strip"))
            continue
        # Tesseract drops and merges tokens, so start+pos drifts. Re-seat the
        # index on the nearest token that actually folds to the target; a site
        # whose target is not near the anchor is REPORTED, never cropped blind.
        lo, hi = max(0, idx - 20), min(len(toks), idx + 21)
        def near(pred):
            return [j for j in range(lo, hi) if pred(toks[j]["f"])]
        # Tesseract glues punctuation on ("walgierningar/|"), breaks words at a
        # line end ("flyd-"), and mangles the very letter under dispute. So try
        # exact, then prefix either way, then one-edit - and always take the
        # candidate NEAREST the anchor, never the first in reading order.
        cand = (near(lambda f: f == target)
                or near(lambda f: len(f) >= 4 and f.startswith(target[:len(f)])
                        and len(target) - len(f) <= 3)
                or near(lambda f: len(target) >= 4 and f.startswith(target)
                        and len(f) - len(target) <= 3)
                or near(lambda f: len(f) == len(target)
                        and sum(a != b for a, b in zip(f, target)) <= 2))
        positional = False
        if not cand:
            if not q.get("positional"):
                weak.append((q["label"], "target %r not within +-20 tokens of anchor "
                             "(anchor token %r)" % (target, toks[idx]["text"])))
                continue
            # Opt-in last resort: Tesseract mangled the disputed word past every
            # match rule, so fall back to the token at the anchor's own position.
            # ⚠ This is a GUESS about which token it is. It is only usable with a
            # WIDE site frame, where a wrong token is visible on the sheet - never
            # with a tight mark tile, where it would look perfectly decidable.
            positional = True
        else:
            idx = min(cand, key=lambda j: abs(j - idx))
        tok = toks[idx]
        mb, wbox = markbox(strip, tok)
        frame = "POSITIONAL-GUESS" if positional else "mark"
        if not mb:
            # A mark over a CAPITAL fails every component test in tighten():
            # it is small, it sits beside rather than above the letter's apex,
            # and the capital fills the band tighten() calls "upper half". That
            # is a locator limit, not an absent mark - so fall back to the WORD
            # box and say so, instead of dropping a real site.
            mb, frame = wbox, "word"
            print("  note: %s - no mark component isolated (ocr=%r); "
                  "falling back to the WORD frame" % (q["label"], tok["text"]))
        used = set()
        ring = pick_control(strip, toks,
                            [fold(w) for w in q.get("ring", [])] + RING_CONTROLS,
                            RING_SAFE | {fold(w) for w in q.get("ring", [])}, used)
        ev = pick_control(strip, toks,
                          [fold(w) for w in q.get("e", [])] + E_CONTROLS,
                          E_SAFE | {fold(w) for w in q.get("e", [])}, used)
        out.append({"label": q["label"], "word": q["word"], "ch": q["ch"], "v": q["v"],
                    "strip": strip, "box": mb, "wordbox": wbox, "frame": frame,
                    "score": round(score, 3), "ocr": tok["text"],
                    "ring": ring, "e": ev})

    json.dump(out, io.open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("resolved %d/%d -> %s" % (len(out), len(queue), args.out))
    for r in out:
        print("  %-16s %-12s %-22s score=%.2f ocr=%r ring=%s e=%s" % (
            r["label"], r["word"], os.path.basename(r["strip"]), r["score"], r["ocr"],
            "+".join(c["form"] for c in r["ring"]) or None,
            "+".join(c["form"] for c in r["e"]) or None))
    if weak:
        print("\nUNRESOLVED (find by hand, do NOT guess):")
        for lab, why in weak:
            print("  %-16s %s" % (lab, why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
