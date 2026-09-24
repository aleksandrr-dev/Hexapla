# -*- coding: utf-8 -*-
"""Derive the CJK search fold table: app/src/main/assets/cjk_fold.json.

WHY. The Meiji Bible prints old kanji (獨, 爲); the 和合本 is printed twice,
Traditional and Simplified. Search matches characters, so a reader typing the
form they know (独, 为) found nothing. The fold maps every variant of a
character to ONE key, applied to verse text and query alike (ReaderScreen.kt
`searchNorm`, web/src/search.ts `searchNorm`), so any form finds any form.

HOW. fold(c) is a FUNCTION, not a union of pairs: union-find over variant
pairs chains unrelated characters together (乾 -> 干 <- 幹 <- 榦 ...). Each
character instead walks one way, to its simplified form:
  1. a Japanese new form goes to its old form, then on to step 3 (Unihan
     kJapaneseOldVariant, else OpenCC JPShinjitaiCharacters reversed, if
     unambiguous);
  2. a Taiwan/HK variant goes to the OpenCC standard form (TW/HKVariants
     reversed, if unambiguous);
  3. an old/traditional form goes to its simplified form (Unihan
     kSimplifiedVariant, first value; else OpenCC TSCharacters, first value);
  4. a z-variant (same character, different glyph: 說/説) with no mapping of
     its own takes its partner's (Unihan kZVariant).
Every walk ENDS at a simplified form: a character that is both simplified and
Japanese-new (独, 为-like) is its own key, never sent back to its old form.
Compatibility ideographs are never keys or values (search NFDs them away).
Only rows whose key is the fold of some character IN A SHIPPED CJK ASSET are
written — a query character that folds to nothing
the Bibles contain cannot match anyway.

SOURCES (both permissive; notices ship in assets/CJK_FOLD_NOTICE.txt):
  Unicode Unihan_Variants.txt (Unicode License v3), and OpenCC data/dictionary
  at a pinned commit (Apache-2.0). Downloaded, never hand-typed, into --src.

    python tools/build_cjk_fold.py --src <dir>            # dry run: stats, samples, diff
    python tools/build_cjk_fold.py --src <dir> --apply    # write the asset
    python tools/build_cjk_fold.py --selftest --src <dir> # known pairs; exit 1 on any FAIL
      HEXAPLA_FOLD_BAD=1 with --selftest drops step 1: it MUST fail.

Exit 0 ok, 1 selftest failure, 2 bad input (missing source, unreadable asset).
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "app/src/main/assets"
OUT = ASSETS / "cjk_fold.json"
CJK_ASSETS = ["bibles/ja_meiji.json", "bibles/zh_cuv_s.json", "bibles/zh_cuv_t.json"]
OPENCC_COMMIT = "b087c2612ce808f464b0925fc1c497d24971d179"
HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003FFFF]")


class BuildError(Exception):
    pass


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise BuildError("cannot read {}: {}".format(path, e))


def cp(s):
    return chr(int(s.split("<")[0][2:], 16))


def unihan(src):
    """field -> {char: [chars]} for the fields the fold uses."""
    want = {"kJapaneseOldVariant", "kSimplifiedVariant", "kZVariant"}
    out = {f: {} for f in want}
    for line in read(Path(src) / "Unihan_Variants.txt").splitlines():
        if not line.startswith("U+"):
            continue
        parts = line.split("\t")
        if len(parts) < 3 or parts[1] not in want:
            continue
        out[parts[1]][cp(parts[0])] = [cp(v) for v in parts[2].split()]
    if not out["kSimplifiedVariant"]:
        raise BuildError("Unihan_Variants.txt has no kSimplifiedVariant rows")
    return out


def opencc(src, name):
    """key -> [values], comment lines skipped."""
    rows = {}
    for line in read(Path(src) / (name + ".txt")).splitlines():
        if not line or line.startswith("#") or "\t" not in line:
            continue
        k, v = line.split("\t", 1)
        rows[k] = v.split()
    if not rows:
        raise BuildError(name + ".txt has no rows")
    return rows


def reverse_unique(rows):
    """value -> key, only where exactly one key gives that value."""
    seen = {}
    for k, vs in rows.items():
        for v in vs:
            if v != k:
                seen.setdefault(v, set()).add(k)
    return {v: next(iter(ks)) for v, ks in seen.items() if len(ks) == 1 and len(v) == 1 and len(next(iter(ks))) == 1}


def build_fold(src, bad=False):
    u = unihan(src)
    ts = opencc(src, "TSCharacters")
    jp_old = {} if bad else dict(reverse_unique(opencc(src, "JPShinjitaiCharacters")))
    if not bad:
        for c, vs in u["kJapaneseOldVariant"].items():
            jp_old[c] = vs[0]  # Unihan wins over OpenCC
    std = {}
    for name in ("TWVariants", "HKVariants"):
        std.update(reverse_unique(opencc(src, name)))
    simp = {k: vs[0] for k, vs in ts.items() if len(k) == 1 and len(vs[0]) == 1}
    for c, vs in u["kSimplifiedVariant"].items():
        simp[c] = vs[0]  # Unihan wins over OpenCC
    z = u["kZVariant"]

    def norm(c):
        # search NFD-normalises before folding: a compatibility ideograph
        # (U+F900.., U+2F800..) never reaches the fold, so never target one.
        return unicodedata.normalize("NFD", c)

    def key(c, depth=0):
        """The simplified form: simp first, else via the standard/old form."""
        if depth > 4:
            return c
        if c in simp and norm(simp[c]) != c:
            return key(norm(simp[c]), depth + 1)
        if c in std and norm(std[c]) != c:
            return key(norm(std[c]), depth + 1)
        if c in jp_old:
            o = norm(jp_old[c])
            if o != c and o in simp:
                return key(norm(simp[o]), depth + 1)
        for p in z.get(c, []):
            p = norm(p)
            if p != c and (p in simp or p in std):
                return key(p, depth + 1)
        return c

    def fold(c):
        c = norm(c)
        k = key(c)
        # A key must be its own key, or two forms could part company.
        return k if key(k) == k else c

    universe = set(simp) | set(simp.values()) | set(jp_old) | set(jp_old.values()) | set(std) | set(std.values()) | set(z)
    return fold, universe


def asset_chars():
    chars = set()
    for rel in CJK_ASSETS:
        chars.update(HAN.findall(read(ASSETS / rel)))
    if not chars:
        raise BuildError("no Han characters in the CJK assets — wrong paths?")
    return chars


def table(src, bad=False):
    fold, universe = build_fold(src, bad)
    shipped = asset_chars()
    keys = {fold(c) for c in shipped if len(unicodedata.normalize("NFD", c)) == 1}
    cands = {unicodedata.normalize("NFD", c) for c in universe | shipped}
    rows = {c: fold(c) for c in sorted(cands) if len(c) == 1 and fold(c) != c and fold(c) in keys}
    return rows, shipped


def selftest(src):
    bad = os.environ.get("HEXAPLA_FOLD_BAD") == "1"
    rows, _ = table(src, bad)
    f = lambda c: rows.get(c, c)
    fails = 0

    def check(label, ok):
        nonlocal fails
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + label)

    check("獨 (kyujitai/trad) and 独 (shinjitai/simp) meet", f("獨") == f("独"))
    check("爲 (old), 為 (JP/trad), 为 (simp) meet", f("爲") == f("為") == f("为"))
    check("愛 and 爱 meet", f("愛") == f("爱"))
    check("說 (trad), 説 (JP), 说 (simp) meet", f("說") == f("説") == f("说"))
    check("觀 (old) and 観 (JP) meet", f("觀") == f("観"))
    check("神 is its own key (no spurious fold)", f("神") == "神")
    check("主 (no variants) is unchanged", f("主") == "主")
    # Pair chaining would show as big groups; the real simplification merges
    # (發 髮 発 髪 -> 发) top out at 6 (measured 2026-09-24).
    groups = {}
    for v in rows.values():
        groups[v] = groups.get(v, 1) + 1
    check("largest group <= 6 characters (got {})".format(max(groups.values())), max(groups.values()) <= 6)
    check("fold is idempotent over every row", all(f(v) == v for v in rows.values()))
    check("only single characters", all(len(k) == 1 and len(v) == 1 for k, v in rows.items()))
    if bad:
        print("control: Japanese step dropped — this run MUST fail")
    print("selftest: " + ("all passed" if fails == 0 else str(fails) + " FAILED"))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", required=True, help="directory holding Unihan_Variants.txt and the OpenCC .txt tables")
    ap.add_argument("--apply", action="store_true", help="write the asset (default: dry run)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try:
        if a.selftest:
            return selftest(a.src)
        rows, shipped = table(a.src)
    except BuildError as e:
        print("ERROR: " + str(e))
        return 2
    body = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    folded = sum(1 for c in shipped if c in rows)
    print("shipped Han characters: {}  of them folded: {}".format(len(shipped), folded))
    print("rows: {}  size: {} bytes (UTF-8)".format(len(rows), len(body.encode("utf-8"))))
    print("samples: " + "  ".join(k + "->" + rows[k] for k in ["獨", "爲", "為", "愛", "說", "説", "觀"] if k in rows))
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    print("vs existing asset: " + ("none" if old is None else ("identical" if old == body else "DIFFERS")))
    if not a.apply:
        print("dry run — nothing written (--apply to write {})".format(OUT.relative_to(REPO)))
        return 0
    OUT.write_bytes(body.encode("utf-8"))
    back = OUT.read_text(encoding="utf-8")
    if back != body:
        print("ERROR: read-back differs from what was written")
        return 2
    print("wrote " + str(OUT.relative_to(REPO)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
