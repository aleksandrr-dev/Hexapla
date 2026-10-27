# -*- coding: utf-8 -*-
"""Line-image + ground-truth pairs for a Kraken recogniser on the Karl XII 1703 apocrypha.

    <kraken_venv>/python tools/kxii_kraken_gt.py --segment   # GPU: strips -> line crops (kraken blla)
    python tools/kxii_kraken_gt.py --ocr                      # stock Fraktur anchor OCR per line
    python tools/kxii_kraken_gt.py [--selftest]               # align, report (dry run)
    python tools/kxii_kraken_gt.py --apply                    # write research/_prep_kxii/kraken_gt/<book>/

Same method as tools/kraken_gt_build.py (read its docstring): OCR is only an
ANCHOR, the label is always the merged text's own characters, every pair is
confidence-gated, labels holding an editorial bracket are dropped.

Differences here: the strips are multi-line bands, so lines are cut by Kraken's
neural baseline segmenter (the ink-profile cutter fails on these low-contrast
strips: runs of 2-220 px on p638_L2); strips can overlap, so a printed line
may be cut twice — the monotonic cursor refuses the second copy.

⚠ AUDIT USE: pairs are written PER BOOK so a model can be trained with whole
books held out. A model that has seen a book's labels agrees with our errors
in that book; only a held-out-book model is a witness for it.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from local_screen import parse_chunk  # noqa: E402
from tesstrain_prep import skeleton, snap  # noqa: E402
from kraken_gt_build import _edge_digits, page_labels  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESEARCH = Path(r"C:/Projects/Hexapla-releases/research")
STRIPS = RESEARCH / "_strips_kxii"
LINES = RESEARCH / "_prep_kxii" / "kraken_lines"
INDEX = LINES / "index.json"
CACHE = Path(r"C:/Projects/Hexapla-releases/_work/kraken/ocr_cache_kxii.json")
OUT = RESEARCH / "_prep_kxii" / "kraken_gt"
TESS = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = r"C:/Projects/Hexapla-releases/tessdata"
# strip dir -> book file, in PRINT order (first strip page ascending)
BOOKS = [("judith", "judith"), ("wisdom", "wisdom"), ("tobit", "tobit"),
         ("sirach", "sirach"), ("baruch", "baruch"), ("macc1", "1maccabees"),
         ("macc2", "2maccabees"), ("esther_add", "esther_additions")]
BRACKET = re.compile(r"[\[\]{}«»<>]")
STRIP_RE = re.compile(r"p(\d+)_([LR])(\d+)\.png$")
EDGE_DIFF = []   # (line, snap() label, page_labels() label) where they differ


def strips():
    out = []
    for d, _ in BOOKS:
        for f in (STRIPS / d).glob("p*_*.png"):
            m = STRIP_RE.match(f.name)
            if m:
                out.append(((int(m.group(1)), m.group(2), int(m.group(3))), d, f))
    return sorted(out)


def _vec_worker(f, d, rets, line_regs, suppl, out):
    """CPU half of blla.segment (baseline vectorising + polygonising, ~90 % of
    its wall time, single-threaded skimage) -> crops written, index row back."""
    from PIL import Image
    from kraken.blla import vec_lines
    lines = vec_lines(**rets, regions=line_regs, text_direction="horizontal-lr",
                      suppl_obj=suppl, topline=False)
    im = Image.open(f)
    rows = []
    for i, ln in enumerate(lines):
        xs = [p[0] for p in ln["boundary"]]
        ys = [p[1] for p in ln["boundary"]]
        box = (max(min(xs) - 6, 0), max(min(ys) - 4, 0),
               min(max(xs) + 6, im.width), min(max(ys) + 4, im.height))
        if box[2] - box[0] < 40 or box[3] - box[1] < 12:
            continue
        name = f"{f.stem}_l{i:02d}.png"
        im.crop(box).save(out / name)
        rows.append({"name": name, "box": box, "y": sum(ys) / len(ys)})
    return f.name, {"book": d, "lines": rows}


def segment(workers=2):
    """blla.segment split in two: the net runs here on the GPU, the CPU half runs
    in `workers` processes (each maps ~2 GB of torch DLLs: commit limit, keep
    <= 2 beside a Whisper job). Serial blla.segment was ~20 s a strip."""
    from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
    from importlib import resources
    from PIL import Image
    from kraken.blla import compute_segmentation_map, vec_regions
    from kraken.lib import vgsl
    from kraken.lib.segmentation import scale_regions
    LINES.mkdir(parents=True, exist_ok=True)
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    todo = [s for s in strips() if s[2].name not in index]
    print(f"segment: {len(todo)} strips to do, {len(index)} done, {workers} workers", flush=True)
    net = vgsl.TorchVGSLModel.load_model(resources.files("kraken").joinpath("blla.mlmodel"))
    env = os.environ.get("CUDA_VISIBLE_DEVICES")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""   # workers inherit it: CPU only
    ex = ProcessPoolExecutor(workers)
    if env is None:
        del os.environ["CUDA_VISIBLE_DEVICES"]
    else:
        os.environ["CUDA_VISIBLE_DEVICES"] = env
    pending, n = set(), 0

    def drain():
        nonlocal pending, n
        done, pending = wait(pending, return_when=FIRST_COMPLETED)
        for fu in done:
            k, v = fu.result()          # a worker error propagates: no silent gaps
            index[k] = v
            n += 1
            if n % 10 == 0:
                INDEX.write_text(json.dumps(index), encoding="utf-8")
                print(f"  {n}/{len(todo)}", flush=True)

    for _, d, f in todo:
        rets = compute_segmentation_map(Image.open(f), None, net, "cuda:0")
        regs = vec_regions(**rets)
        bound = rets["bounding_regions"] or []
        # as blla.segment: all regions go in as `regions`, bounding-class ones also as suppl_obj
        line_regs = scale_regions([r.boundary for rs in regs.values() for r in rs],
                                  1 / rets["scale"])
        suppl = scale_regions([r.boundary for c, rs in regs.items() if c in bound
                               for r in rs], 1 / rets["scale"])
        rets = {k: v for k, v in rets.items() if k in ("heatmap", "cls_map", "scale", "scal_im")}
        pending.add(ex.submit(_vec_worker, f, d, rets, line_regs, suppl, LINES))
        while len(pending) >= workers * 2:
            drain()
    while pending:
        drain()
    ex.shutdown()
    INDEX.write_text(json.dumps(index), encoding="utf-8")
    print(f"segment done: {len(index)} strips, "
          f"{sum(len(v['lines']) for v in index.values())} lines", flush=True)


def ocr(png):
    env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
    r = subprocess.run([TESS, str(png), "stdout", "-l", "Fraktur", "--psm", "7"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if r.returncode != 0:
        raise RuntimeError(f"tesseract rc {r.returncode} on {png}: {r.stderr[:200]}")
    return r.stdout.strip()


def run_ocr():
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    todo = [r["name"] for v in index.values() for r in v["lines"] if r["name"] not in cache]
    print(f"OCR: {len(todo)} lines to do, {len(cache)} cached", flush=True)
    with ThreadPoolExecutor(6) as ex:
        for n, (name, txt) in enumerate(zip(todo, ex.map(lambda x: ocr(LINES / x), todo)), 1):
            cache[name] = txt
            if n % 1000 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                print(f"  {n}/{len(todo)}", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"OCR done: {len(cache)} cached", flush=True)


def reference(shuffle=False):
    """Concatenated merged text in print order + per-char book label."""
    parts, owner = [], []
    for d, b in BOOKS:
        for _, _, no, t in parse_chunk(RESEARCH / f"karlxii_{b}.md"):
            parts.append((d, f"{no} {t}"))
    if shuffle:
        import random
        words = [(d, w) for d, p in parts for w in p.split(" ")]
        groups = [words[i:i + 3] for i in range(0, len(words), 3)]
        random.Random(1).shuffle(groups)
        parts = [(g[0][0], " ".join(w for _, w in g)) for g in groups]
    text = ""
    for d, p in parts:
        text += p + " "
        owner += [d] * (len(p) + 1)
    skel, idx = skeleton(text)
    return text, skel, idx, owner


def align(index, cache, text, skel, idx, min_conf=0.70, min_chars=20):
    why = Counter()
    pairs = []
    cur = 0
    order = sorted(index, key=lambda k: STRIP_RE.match(k).groups()
                   and (int(STRIP_RE.match(k).group(1)), STRIP_RE.match(k).group(2),
                        int(STRIP_RE.match(k).group(3))))
    for strip in order:
        got = []
        for n, r in enumerate(sorted(index[strip]["lines"], key=lambda r: r["y"])):
            raw = cache.get(r["name"], "")
            osk = skeleton(raw)[0]
            if len(osk) < min_chars:
                why["short-ocr"] += 1
                continue
            lo, hi = max(cur - 400, 0), cur + 6000
            votes = Counter()
            for i in range(len(osk) - 6):
                j = skel.find(osk[i:i + 6], lo, hi)
                while j != -1:
                    votes[j - i] += 1
                    j = skel.find(osk[i:i + 6], j + 1, hi)
            if not votes or max(votes.values()) < 3:
                # lost: re-locate globally (page gaps, strips of a book not merged)
                votes = Counter()
                for i in range(0, len(osk) - 8, 2):
                    j = skel.find(osk[i:i + 8])
                    while j != -1:
                        votes[j - i] += 1
                        j = skel.find(osk[i:i + 8], j + 1)
                if not votes or max(votes.values()) < 4:
                    why["no-anchor"] += 1
                    continue
            top = max(votes.values())
            off = min(o for o, c in votes.items() if c >= top * 0.6)
            base = max(off - 30, 0)
            sm = difflib.SequenceMatcher(None, osk, skel[base:off + len(osk) + 30], autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size > 3]
            if not blocks:
                why["no-anchor"] += 1
                continue
            s, e = base + blocks[0].b, base + blocks[-1].b + blocks[-1].size
            if e <= s:
                why["empty-span"] += 1
                continue
            if s < cur - 5:
                why["already-used (strip overlap)"] += 1
                continue
            conf = difflib.SequenceMatcher(None, osk, skel[s:e], autojunk=False).ratio()
            if conf < min_conf:
                why["low-conf"] += 1
                continue
            if not (0.8 <= (e - s) / len(osk) <= 1.25):
                why["span-length"] += 1
                continue
            cur = e
            got.append({"name": r["name"], "n": n, "s": s, "e": e, "conf": conf,
                        "lead": blocks[0].a, "tail": len(osk) - (blocks[-1].a + blocks[-1].size),
                        "dlead": _edge_digits(raw), "dtail": _edge_digits(raw[::-1])})
        # one cut per line break, shared by the two lines (kraken_gt_build.page_labels);
        # snap() swallowed the word after every cleanly matched end
        for g, gt in zip(got, page_labels(got, text, idx)):
            if gt is None:
                why["uncertain-cut"] += 1
                continue
            if EDGE_DIFF is not None:
                old = snap(text, idx[g["s"]], idx[min(g["e"], len(idx) - 1)])
                if old != gt:
                    EDGE_DIFF.append((g["name"], old, gt))
            if len(gt) < min_chars or BRACKET.search(gt):
                why["bracket/short-gt"] += 1
                continue
            pairs.append((index[strip]["book"], strip, g["name"], gt, g["conf"]))
    return pairs, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segment", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--ocr", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.segment:
        segment(a.workers)
        return 0
    if a.ocr:
        run_ocr()
        return 0
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    text, skel, idx, _ = reference()
    pairs, why = align(index, cache, text, skel, idx)
    if a.selftest:
        bt, bs, bi, _ = reference(shuffle=True)
        bad, _ = align(index, cache, bt, bs, bi)
        print(f"selftest: real ref {len(pairs)} pairs, shuffled ref {len(bad)} pairs")
        ok = len(pairs) > 500 and len(bad) < len(pairs) * 0.02
        print("selftest", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    nlines = sum(len(v["lines"]) for v in index.values())
    print(f"strips {len(index)}, lines {nlines}, pairs {len(pairs)}")
    print(f"per book: {dict(Counter(p[0] for p in pairs))}")
    print(f"line drops: {dict(why)}")
    for p in pairs[:: max(len(pairs) // 6, 1)][:6]:
        print(f"  sample {p[2]} {p[4]:.2f} | {p[3]}")
    if not a.apply:
        print("dry run - pass --apply to write pairs")
        return 0
    if OUT.exists():
        shutil.rmtree(OUT)
    for book, strip, name, gt, _ in pairs:
        d = OUT / book
        d.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LINES / name, d / name)
        (d / (name[:-4] + ".gt.txt")).write_text(gt + "\n", encoding="utf-8")
    print(f"wrote {len(pairs)} pairs -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
