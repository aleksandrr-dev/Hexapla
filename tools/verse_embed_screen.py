# -*- coding: utf-8 -*-
"""Cross-lingual VERSE-ALIGNMENT SCREEN by embeddings. 0 Claude tokens.

    python tools/verse_embed_screen.py --sets de_luther,es_rv [--books 17,18]
    python tools/verse_embed_screen.py --sets all                 # ~6 h at 42 verses/s
    python tools/verse_embed_screen.py --thorlaks all             # merged Þorláksbiblía books
    python tools/verse_embed_screen.py --selftest                 # and HEXAPLA_NO_EMBEDSCREEN=1 must FAIL

Runs a multilingual embedding model in LM Studio (default
text-embedding-qwen3-embedding-0.6b, 640 MB, fits beside anything) over every
verse of a translation and the KJV, and asks one question per verse: is this
verse more like ITS OWN KJV verse than like a KJV neighbour within ±3? A
verse whose best match is a neighbour is FLAGGED. Three or more consecutive
flags are a RUN - the shape of a shifted, reflowed, merged or misaddressed
stretch (the rv Job 39 reflow, the zh_cuv merged groups, a printed numeral
that runs one behind). A verse unlike every KJV verse near it is LOW (text
from elsewhere, a placeholder, garbage).

WHY: length witnesses cannot see a shift - a verse moved one slot has a
plausible length. Meaning can. And it is free: no Claude tokens, ~1.5 GB VRAM,
negligible RAM, so it runs over the WHOLE corpus, never a sample.

WHAT IT IS NOT: a source. It never says what a verse should read. Its model
is small and multilingual; a flag is a question for a reader, and an unflagged
verse is «no neighbour-sized misalignment», not «correct». Versification is
taken from assets/versemap.json (Þorláksbiblía: the pinned alignment in
thorlaks_verse_length_witness.py) - a flag inside a mapped block may be the
map's error, and that is a finding too.

Controls, every set, every run - a set whose control fails is BLIND and its
result is void (printed as CONTROL-FAIL, rc 1):
  * shift: the set's longest book shifted one verse must flag >= 80 %;
  * merge (proxy): two verses merged (vector sum) and the rest shifted, same.
  * Þorláksbiblía Mark, if included: with HEXAPLA_NO_PINALIGN=1 the pinned
    chapters (5:28-, 9) must come back as RUNS; with the table, not.
  `--selftest` checks the same on Philemon; `HEXAPLA_NO_EMBEDSCREEN=1`
  disables flagging and the selftest must then FAIL.

Embeddings are cached per model per set in
Hexapla-releases/_work/embed_cache/<model>/<set>.npz, keyed by the SHA-1 of the
exact cleaned text, so a re-run only embeds what changed.
Reports: Hexapla-releases/_work/embed_screen/<set>.tsv
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# importing it also rewraps stdout as UTF-8
from thorlaks_verse_length_witness import aligner, kjv_book, merged_book  # noqa: E402

REPO = os.path.dirname(HERE)
DATA = r"C:\Projects\Hexapla-releases"
BIBLES = os.path.join(REPO, "app", "src", "main", "assets", "bibles")
VERSEMAP = os.path.join(REPO, "app", "src", "main", "assets", "versemap.json")
CACHE = os.path.join(DATA, "_work", "embed_cache")
OUT = os.path.join(DATA, "_work", "embed_screen")
URL = "http://localhost:1234/v1/embeddings"
MODEL = "text-embedding-qwen3-embedding-0.6b"
W = 3            # neighbours considered each side
RUN_MIN = 3      # consecutive flags that make a RUN
LOW_Z = -4.0     # robust z of same-verse similarity below which a verse is LOW
CTRL_MIN = 0.80  # a control must flag at least this fraction
BATCH, THREADS = 64, 4
POST_TRIES = 12  # ~8 min of retries: long enough to re-wake a dead LM Studio
LMS = os.path.join(os.path.expanduser("~"), ".lmstudio", "bin", "lms.exe")

NOTE_COLON = re.compile(r"\{[^{}]*:[^{}]*\}")
STRONGS = re.compile(r"\[[HG]\d+[a-z]?\]")
BRACKET = re.compile(r"\[[^\]]*\]")


def clean(t):
    t = NOTE_COLON.sub(" ", t or "")
    t = STRONGS.sub("", t)
    t = t.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", t).strip()


def clean_thorlaks(t):
    t = BRACKET.sub(" ", t or "")
    t = re.sub(r"\{[^}]*\}", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- embeddings
class Cache:
    """sha1(text) -> float16 vector, one .npz per model per namespace."""

    def __init__(self, model, ns):
        self.path = os.path.join(CACHE, re.sub(r"[^\w.-]", "_", model), ns + ".npz")
        self.idx, self.vecs = {}, []
        if os.path.exists(self.path):
            z = np.load(self.path)
            self.vecs = list(z["vecs"])
            self.idx = {k: i for i, k in enumerate(z["keys"].tolist())}
        self.dirty = False

    @staticmethod
    def key(text):
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def get(self, text):
        i = self.idx.get(self.key(text))
        return None if i is None else self.vecs[i]

    def put(self, text, vec):
        k = self.key(text)
        if k not in self.idx:
            self.idx[k] = len(self.vecs)
            self.vecs.append(np.asarray(vec, dtype=np.float16))
            self.dirty = True

    def save(self):
        if not self.dirty:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        keys = np.array(sorted(self.idx, key=self.idx.get))
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as fh:
            np.savez(fh, keys=keys, vecs=np.vstack(self.vecs))
        os.replace(tmp, self.path)
        self.dirty = False


def _wake_lmstudio():
    """LM Studio's service dies with the process tree that woke it (2026-09-24 17:26:
    a Claude session ended and took the overnight run's server with it). Re-wake it."""
    try:
        subprocess.run([LMS, "server", "start"], timeout=120, capture_output=True)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  could not wake LM Studio: {e}", flush=True)


def _post(model, texts):
    body = json.dumps({"model": model, "input": texts}).encode()
    for attempt in range(POST_TRIES):
        try:
            req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                data = json.load(r)["data"]
            if len(data) != len(texts):
                raise RuntimeError(f"asked {len(texts)} embeddings, got {len(data)}")
            return [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
        except Exception as e:  # noqa: BLE001 - retried, then re-raised
            if attempt == POST_TRIES - 1:
                raise
            print(f"  embed retry {attempt + 1}: {e}", flush=True)
            if isinstance(getattr(e, "reason", e), ConnectionError):
                _wake_lmstudio()
            time.sleep(min(5 * (attempt + 1), 60))


def embed(model, cache, texts, label=""):
    """-> unit-normalised float32 matrix, one row per text (cached)."""
    todo = [t for t in dict.fromkeys(texts) if cache.get(t) is None]
    if todo:
        t0, done = time.time(), 0
        chunks = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
        for g in range(0, len(chunks), THREADS * 20):
            group = chunks[g:g + THREADS * 20]
            with ThreadPoolExecutor(THREADS) as ex:
                for chunk, vecs in zip(group, ex.map(lambda c: _post(model, c), group)):
                    for t, v in zip(chunk, vecs):
                        cache.put(t, v)
                    done += len(chunk)
            cache.save()  # a reaped run loses at most one group
            rate = done / max(time.time() - t0, 1e-9)
            print(f"  {label}: embedded {done}/{len(todo)} ({rate:.0f}/s)", flush=True)
    m = np.vstack([cache.get(t) for t in texts]).astype(np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


# ------------------------------------------------------------------- scoring
def score(T, K, w=W, grp=None):
    """-> same[i], best_other[i], best_offset[i] over offsets 1..w each side.

    `grp` (book id per row) keeps neighbours inside one book: a book's last
    verse against the next book's first is noise, not a shift.
    """
    n = len(T)
    same = np.einsum("ij,ij->i", T, K)
    other = np.full(n, -2.0, dtype=np.float32)
    off = np.zeros(n, dtype=int)
    for o in range(-w, w + 1):
        if o == 0:
            continue
        i = np.arange(max(0, -o), min(n, n - o))
        if grp is not None:
            i = i[grp[i] == grp[i + o]]
        if not len(i):
            continue
        s = np.einsum("ij,ij->i", T[i], K[i + o])
        better = s > other[i]
        other[i[better]] = s[better]
        off[i[better]] = o
    return same, other, off


def flags(same, other):
    if os.environ.get("HEXAPLA_NO_EMBEDSCREEN") == "1":
        return np.zeros(len(same), dtype=bool)      # known-bad control
    return other > same


def runs(flag, starts):
    """Consecutive flagged indices, never across a book start. -> [(i0, i1)]"""
    out, i0 = [], None
    for i, f in enumerate(flag):
        if i in starts and i0 is not None:
            if i - i0 >= RUN_MIN:
                out.append((i0, i - 1))
            i0 = None
        if f and i0 is None:
            i0 = i
        elif not f and i0 is not None:
            if i - i0 >= RUN_MIN:
                out.append((i0, i - 1))
            i0 = None
    if i0 is not None and len(flag) - i0 >= RUN_MIN:
        out.append((i0, len(flag) - 1))
    return out


def controls(T, K):
    """Shift and merge controls on one book's rows -> (shift_frac, merge_frac)."""
    if len(T) < 12:
        return None, None
    fs = flags(*score(T[1:], K[:-1])[:2])
    m = T[2] + T[3]
    Tm = np.vstack([T[:2], (m / np.linalg.norm(m))[None], T[4:]])
    fm = flags(*score(Tm, K[:-1])[:2])
    return float(fs[2:].mean()), float(fm[3:].mean())


# --------------------------------------------------------------- asset units
def load(stem):
    with open(os.path.join(BIBLES, stem + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def versemap_for(stem):
    sys.path.insert(0, HERE)
    from build_versemap import IDS  # noqa: E402 - guarded by __main__
    key = {v: k for k, v in IDS.items()}.get(stem)
    with open(VERSEMAP, encoding="utf-8") as fh:
        vm = json.load(fh)
    return vm.get(key, {}) if key else {}


def asset_units(kjv_b, tr_b, runs_):
    """-> [(kjv [(c,v)], tr [(c,v)])] in KJV order for one book."""
    units, by_kjv = [], {}

    def add(kjv, tr):
        u = by_kjv.get(kjv[0])
        if u is not None and len(kjv) == 1:
            u[1].extend(tr)                     # two runs feed one KJV verse
            return
        u = (list(kjv), list(tr))
        units.append(u)
        for k in kjv:
            by_kjv[k] = u

    for kc, kv0, kv1, tc, tv0, tv1 in runs_:
        if tv0 > tv1:                           # documented omission
            for v in range(kv0, kv1 + 1):
                by_kjv[(kc, v)] = None
            continue
        nk, nt = kv1 - kv0 + 1, tv1 - tv0 + 1
        if nk == nt:
            for i in range(nk):
                add([(kc, kv0 + i)], [(tc, tv0 + i)])
        else:
            add([(kc, v) for v in range(kv0, kv1 + 1)], [(tc, v) for v in range(tv0, tv1 + 1)])
    for ci, ch in enumerate(kjv_b["chapters"]):
        for vi in range(len(ch)):
            if (ci + 1, vi + 1) not in by_kjv:
                add([(ci + 1, vi + 1)], [(ci + 1, vi + 1)])
    units.sort(key=lambda u: u[0][0])

    def text(book, refs):
        chs = book["chapters"]
        return " ".join(clean(chs[c - 1][v - 1]) for c, v in refs
                        if 0 < c <= len(chs) and 0 < v <= len(chs[c - 1])).strip()
    return [(u[0], u[1], text(kjv_b, u[0]), text(tr_b, u[1])) for u in units]


def ref(refs):
    (c0, v0), (c1, v1) = refs[0], refs[-1]
    return f"{c0}:{v0}" if refs[0] == refs[-1] else (f"{c0}:{v0}-{v1}" if c0 == c1 else f"{c0}:{v0}-{c1}:{v1}")


# -------------------------------------------------------------------- driver
def screen(label, rows, kjv_cache, tr_cache, model, starts):
    """rows = [(book_name, kjv_refs, tr_refs, kjv_text, tr_text)] -> summary dict."""
    K = embed(model, kjv_cache, [r[3] for r in rows], "KJV")
    T = embed(model, tr_cache, [r[4] for r in rows], label)
    grp = np.zeros(len(rows), dtype=int)
    for s0 in starts[1:]:
        grp[s0:] += 1
    same, other, off = score(T, K, grp=grp)
    fl = flags(same, other)
    med = float(np.median(same))
    mad = float(np.median(np.abs(same - med))) * 1.4826 or 1e-6
    z = (same - med) / mad
    low = (z < LOW_Z) & ~fl
    rr = runs(fl, set(starts))
    # controls on the longest book
    bounds = list(starts) + [len(rows)]
    b0, b1 = max(zip(bounds, bounds[1:]), key=lambda p: p[1] - p[0])
    cs, cm = controls(T[b0:b1], K[b0:b1])
    os.makedirs(OUT, exist_ok=True)
    in_run = np.zeros(len(rows), dtype=bool)
    for a, b in rr:
        in_run[a:b + 1] = True
    with open(os.path.join(OUT, label + ".tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("kind\tbook\tkjv\ttrans\tsame\tbest_other\toffset\tz\ttext\n")
        for i, r in enumerate(rows):
            kind = "RUN" if in_run[i] else "FLAG" if fl[i] else "LOW" if low[i] else None
            if kind:
                fh.write(f"{kind}\t{r[0]}\t{ref(r[1])}\t{ref(r[2])}\t{same[i]:.3f}\t{other[i]:.3f}"
                         f"\t{off[i]:+d}\t{z[i]:.1f}\t{r[4][:80]}\n")
    return dict(units=len(rows), flagged=int(fl.sum()), runs=rr, low=int(low.sum()),
                ctrl_shift=cs, ctrl_merge=cm, same=same, other=other, fl=fl)


def verdict(s):
    ok = s["ctrl_shift"] is not None and s["ctrl_shift"] >= CTRL_MIN and s["ctrl_merge"] >= CTRL_MIN
    return "ok" if ok else "CONTROL-FAIL"


def print_summary(label, s, rows, top=6):
    cs = "-" if s["ctrl_shift"] is None else f"{100 * s['ctrl_shift']:.0f}%"
    cm = "-" if s["ctrl_merge"] is None else f"{100 * s['ctrl_merge']:.0f}%"
    print(f"{label:22s} units {s['units']:6d}  flagged {s['flagged']:5d} ({100 * s['flagged'] / max(s['units'], 1):.2f}%)"
          f"  runs {len(s['runs']):3d}  low {s['low']:4d}  ctrl shift {cs} merge {cm}  {verdict(s)}", flush=True)
    for a, b in sorted(s["runs"], key=lambda p: p[0] - p[1])[:top]:
        print(f"    RUN {rows[a][0]} {ref(rows[a][1])} .. {ref(rows[b][1])}  ({b - a + 1} units)")


def run_sets(stems, books, model):
    kjv = load("en_kjv")
    kjv_cache = Cache(model, "en_kjv")
    bad = 0
    for stem in stems:
        tr = load(stem)
        vm = versemap_for(stem)
        rows, starts = [], []
        for b in range(min(66, len(tr))):
            if books and b not in books:
                continue
            us = [u for u in asset_units(kjv[b], tr[b], vm.get(str(b), [])) if u[2] and u[3]]
            if not us:
                continue
            starts.append(len(rows))
            rows += [(kjv[b]["name"], k, t, kt, tt) for k, t, kt, tt in us]
        if not rows:
            print(f"{stem}: no units")
            continue
        s = screen(stem, rows, kjv_cache, Cache(model, stem), model, starts)
        print_summary(stem, s, rows)
        bad += verdict(s) != "ok"
    return bad


def thorlaks_books():
    out = {}
    for f in sorted(os.listdir(os.path.join(DATA, "research"))):
        if not (f.startswith("thorlaks_") and f.endswith(".md")):
            continue
        with open(os.path.join(DATA, "research", f), encoding="utf-8") as fh:
            head = fh.read(3000)
        m = (re.search(r"^Book:\s*\*\*(.+?)\*\*", head, re.M)
             or re.search(r"^# Þorláksbiblía 1644 — (.+?) \(", head, re.M))
        if m:
            out[m.group(1).title()] = os.path.join(DATA, "research", f)
    return out


def thorlaks_rows(book, path):
    kjv = kjv_book(book)
    if kjv is None:
        print(f"  SKIPPED {book}: no KJV book of that name (not screened)")
        return []
    al = aligner(book)
    rows = []
    for ch, verses in sorted(merged_book(path).items()):
        for v, text in sorted(verses.items()):
            ks = al(ch, v)
            kt = " ".join(clean(kjv.get(c, {}).get(vv, "")) for c, vv in ks).strip()
            tt = clean_thorlaks(text)
            if kt and tt:
                rows.append((book, ks, [(ch, v)], kt, tt))
    return rows


def run_thorlaks(names, model):
    books = thorlaks_books()
    names = sorted(books) if names == ["all"] else names
    kjv_cache, tr_cache = Cache(model, "en_kjv"), Cache(model, "thorlaks")
    rows, starts = [], []
    for b in names:
        starts.append(len(rows))
        rows += thorlaks_rows(b, books[b])
    s = screen("thorlaks", rows, kjv_cache, tr_cache, model, starts)
    print_summary("thorlaks", s, rows, top=8)
    bad = verdict(s) != "ok"
    if "Mark" in names:                          # the real-world control
        old = os.environ.get("HEXAPLA_NO_PINALIGN")
        os.environ["HEXAPLA_NO_PINALIGN"] = "1"
        raw = thorlaks_rows("Mark", books["Mark"])
        if old is None:
            del os.environ["HEXAPLA_NO_PINALIGN"]
        else:
            os.environ["HEXAPLA_NO_PINALIGN"] = old
        K = embed(model, kjv_cache, [r[3] for r in raw], "KJV")
        T = embed(model, tr_cache, [r[4] for r in raw], "thorlaks")
        fl = flags(*score(T, K)[:2])
        pinned = [i for i, r in enumerate(raw) if (r[2][0][0] == 5 and r[2][0][1] >= 28) or r[2][0][0] == 9]
        frac_raw = float(fl[pinned].mean()) if pinned else 0.0
        with_pin = [i for i, r in enumerate(rows) if r[0] == "Mark" and
                    ((r[2][0][0] == 5 and r[2][0][1] >= 28) or r[2][0][0] == 9)]
        frac_pin = float(s["fl"][with_pin].mean()) if with_pin else 1.0
        ok = frac_raw >= CTRL_MIN and frac_pin < 0.2
        print(f"PIN CONTROL Mark 5:28-/9: unpinned flags {100 * frac_raw:.0f}% (must be >= {100 * CTRL_MIN:.0f}), "
              f"pinned {100 * frac_pin:.0f}% (must be < 20)  {'ok' if ok else 'CONTROL-FAIL'}")
        bad += not ok
    return bad


def selftest(model):
    books = thorlaks_books()
    rows = thorlaks_rows("Philemon", books["Philemon"])
    K = embed(model, Cache(model, "en_kjv"), [r[3] for r in rows], "KJV")
    T = embed(model, Cache(model, "thorlaks"), [r[4] for r in rows], "thorlaks")
    real = float(flags(*score(T, K)[:2]).mean())
    cs, cm = controls(T, K)
    ok = real <= 0.2 and cs >= CTRL_MIN and cm >= CTRL_MIN
    print(f"selftest Philemon: real {100 * real:.0f}% (<= 20)  shift {100 * cs:.0f}%  merge {100 * cm:.0f}% "
          f"(>= {100 * CTRL_MIN:.0f})  {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", help="comma list of asset stems, or 'all'")
    ap.add_argument("--books", help="comma list of 0-based KJV book indices")
    ap.add_argument("--thorlaks", help="comma list of book names, or 'all'")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try:
        if a.selftest:
            return selftest(a.model)
        bad = 0
        if a.sets:
            stems = sorted(f[:-5] for f in os.listdir(BIBLES)
                           if f.endswith(".json") and f != "en_kjv.json") if a.sets == "all" else a.sets.split(",")
            books = {int(b) for b in a.books.split(",")} if a.books else None
            bad += run_sets(stems, books, a.model)
        if a.thorlaks:
            bad += run_thorlaks(a.thorlaks.split(","), a.model)
        return 1 if bad else 0
    except (OSError, RuntimeError, ValueError) as e:
        print(f"COULD NOT RUN: {e}")               # a check that cannot run did not pass
        return 2


if __name__ == "__main__":
    sys.exit(main())
