#!/usr/bin/env python
"""
build_woodcut_assets.py - ship the print's own initials: woodcuts cut from the
scans become app assets the web reader and Android draw in place of a letter
drop cap (owner 2026-09-29: «Real woodcuts from scans»). 0 model cost.

TWO SETS
    kxii  Karl XII 1703, cut by kxii_initials_crop.py
    thl   Þorláksbiblía 1644, cut by thorlaks_woodcuts.py and addressed by
          thorlaks_woodcut_ocr.py (first test -> ship.json, second test ->
          ship2.json). The set id is the Translation id (`thl`, 2026-10-07;
          the crops dir keeps its old `thor_woodcuts` name).

    python tools/build_woodcut_assets.py --crops DIR --exclude LOOK.txt           # kxii, dry run
    python tools/build_woodcut_assets.py --crops DIR --exclude LOOK.txt --apply
    python tools/build_woodcut_assets.py --set thl                                # thl, dry run
    python tools/build_woodcut_assets.py --set thl --apply
    python tools/build_woodcut_assets.py --selftest

INPUT (kxii)
    DIR/crops.json + DIR/<slot>_<ch>_<v1>.png (grey+alpha, full scan res).
    --exclude: the crop-check look's result mapped to files (one crop file name
    per line, `#` comments) - a cell the look called CUT / TEXT / RULE / NONE /
    UNCLEAR is never shipped; that verse keeps its letter drop cap.
    Only rows with an empty flag list or GREW-OK ship without the look: a
    plain GREW row (detector box cut, possibly half a letter) ships only when
    it is NOT excluded AND --allow-grew names it (the look saw it whole).

INPUT (thl)
    --crops (default _work/_scratch/thor_woodcuts): --ship lists (default
    ship.json,ship2.json there; rows {book, addr "c:v", file}) and the
    crop-check look, read straight from LOOK_RESULT.txt + sheet_key.tsv in
    the same dir: any cell not OK is never shipped, whatever the list says.
    Two files claiming one book:c:v, or one file under two addresses, ship
    NEITHER (never guessed which is right).
    TEXT GATE: the woodcut replaces the verse's first letter, so it ships only
    where the shipped verse (bibles/is_thorlaks.json) is non-empty and opens
    with a capital or U+00B7 (an initial the transcription could not read,
    which the woodcut then supplies - ReaderScreen.kt/text.ts woodcutCapEnd).
    A verse opening lowercase has lost its initial in the text: shipping the
    woodcut there would eat a real letter, so it keeps its letter drop cap.

OUTPUT (--apply)
    app/src/main/assets/woodcuts/<set>/<book>_<c>_<v>.png   height <= MAX_H px
    app/src/main/assets/woodcuts.json   {"<set>": {"<book>": ["c:v", ...]}, ...}
    Only this set's dir and key are replaced; the other sets' entries stay.
    (book = the 0-based book index initials.json uses; c, v 1-based, the
    column's own versification). build_web_data.py --aux copies both.

CONTROL
    --selftest: the index and the files agree both ways on a fixture, an
    excluded crop is absent, a thl look-bad crop and a doubly-claimed
    address are absent, and writing one set keeps the other set's key.
    HEXAPLA_WOODCUT_BAD=1 ignores the exclusions; HEXAPLA_WOODCUT_CLOBBER=1
    writes woodcuts.json with only the current set - either must make the
    selftest fail.
"""
import argparse
import io
import json
import os
import shutil
import sys
import tempfile

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO, "app", "src", "main", "assets")
THOR_DIR = r"C:/Projects/Hexapla-releases/_work/_scratch/thor_woodcuts"
THL_TEXT = os.path.join(ASSETS, "bibles", "is_thorlaks.json")
MAX_H = 160   # 2-line drop cap at 3x DPR (~2.9 x 18 px x 3)

THOR_BOOK = {  # merged-file key -> 0-based KJV book index (= thorlaks_woodcuts.BOOK_IDX)
    "matthew": 39, "mark": 40, "luke": 41, "john": 42, "acts": 43, "romans": 44,
    "1corinthians": 45, "2cor": 46, "galatians": 47, "ephesians": 48,
    "philippians": 49, "colossians": 50, "1thessalonians": 51,
    "2thessalonians": 52, "1timothy": 53, "2timothy": 54, "titus": 55,
    "philemon": 56, "hebrews": 57, "james": 58, "1peter": 59, "2peter": 60,
    "1john": 61, "2john": 62, "3john": 63, "jude": 64, "revelation": 65}


def plan(crops_dir, exclude, allow_grew):
    """kxii: crops.json rows -> (ship [(file, book, c, v)], skip [(file, why)])"""
    rows = json.load(io.open(os.path.join(crops_dir, "crops.json"), encoding="utf-8"))
    if os.environ.get("HEXAPLA_WOODCUT_BAD") == "1":
        exclude = set()
    ship, skip = [], []
    for r in rows:
        if r["kind"] not in ("opening", "mid"):
            continue
        fn = r["file"]
        grew = any(f.startswith("GREW ") for f in r["flags"])
        other = [f for f in r["flags"] if not f.startswith("GREW")]
        if fn in exclude:
            skip.append((fn, "look"))
        elif other:
            skip.append((fn, " ".join(other)))
        elif grew and fn not in allow_grew:
            skip.append((fn, "GREW (box cut) not named by --allow-grew"))
        else:
            ship.append((fn, r["slot"], r["ch"], r["v"] + 1))
    return ship, skip


def thor_look(crops_dir):
    """file -> the look's verdict, for every cell the look did not call OK."""
    key = {}
    for ln in io.open(os.path.join(crops_dir, "sheet_key.tsv"), encoding="utf-8"):
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 3:
            key[p[0]] = p[2]
    bad = {}
    for ln in io.open(os.path.join(crops_dir, "LOOK_RESULT.txt"), encoding="utf-8"):
        p = ln.split()
        if len(p) >= 2 and not ln.startswith("#") and p[0] in key and p[1] != "OK":
            bad[key[p[0]]] = p[1]
    return bad


def thl_text(path=THL_TEXT):
    """(book, c, v) 0-based book, 1-based c:v -> the shipped verse, or None."""
    books = json.load(io.open(path, encoding="utf-8"))

    def get(b, c, v):
        try:
            return books[b]["chapters"][c - 1][v - 1]
        except (IndexError, KeyError, TypeError):
            return None
    return get


def text_gate(t):
    """None when a woodcut may replace this verse's first letter, else why not."""
    t = (t or "").lstrip()
    if not t:
        return "no verse text"
    if os.environ.get("HEXAPLA_WOODCUT_BAD") == "1":
        return None
    if t[0] == "\u00B7" or t[0].isupper():
        return None
    return "text opens lowercase %r: the woodcut would eat a letter" % t[:12]


def plan_thor(crops_dir, ship_files, text=None):
    """thl: ship lists -> (ship [(file, book, c, v)], skip [(file, why)])"""
    bad = thor_look(crops_dir)
    if os.environ.get("HEXAPLA_WOODCUT_BAD") == "1":
        bad = {}
    rows = []
    for sf in ship_files:
        rows += json.load(io.open(os.path.join(crops_dir, sf), encoding="utf-8"))
    by_addr, by_file = {}, {}
    for r in rows:
        by_addr.setdefault((r["book"], r["addr"]), set()).add(r["file"])
        by_file.setdefault(r["file"], set()).add((r["book"], r["addr"]))
    ship, skip, done = [], [], set()
    for r in rows:
        fn, k = r["file"], (r["book"], r["addr"])
        if (fn, k) in done:
            continue
        done.add((fn, k))
        if r["book"] not in THOR_BOOK:
            skip.append((fn, "unknown book key %r" % r["book"]))
        elif fn in bad:
            skip.append((fn, "look " + bad[fn]))
        elif len(by_addr[k]) > 1 and os.environ.get("HEXAPLA_WOODCUT_BAD") != "1":
            skip.append((fn, "%s %s claimed by %d files" % (r["book"], r["addr"], len(by_addr[k]))))
        elif len(by_file[fn]) > 1 and os.environ.get("HEXAPLA_WOODCUT_BAD") != "1":
            skip.append((fn, "one file under %d addresses" % len(by_file[fn])))
        elif not os.path.exists(os.path.join(crops_dir, fn)):
            skip.append((fn, "crop file missing"))
        else:
            c, v = (int(x) for x in r["addr"].split(":"))
            why = text_gate(text(THOR_BOOK[r["book"]], c, v)) if text is not None else None
            if why:
                skip.append((fn, why))
            else:
                ship.append((fn, THOR_BOOK[r["book"]], c, v))
    return ship, skip


def write(crops_dir, ship, assets, set_id):
    out = os.path.join(assets, "woodcuts", set_id)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    index = {}
    for fn, book, c, v in ship:
        im = Image.open(os.path.join(crops_dir, fn))
        if im.size[1] > MAX_H:
            im = im.resize((max(1, round(im.size[0] * MAX_H / im.size[1])), MAX_H), Image.LANCZOS)
        im.save(os.path.join(out, "%d_%d_%d.png" % (book, c, v)), optimize=True)
        index.setdefault(str(book), []).append("%d:%d" % (c, v))
    for k in index:
        index[k].sort(key=lambda s: tuple(int(x) for x in s.split(":")))
    jp = os.path.join(assets, "woodcuts.json")
    allsets = {}
    if os.path.exists(jp) and os.environ.get("HEXAPLA_WOODCUT_CLOBBER") != "1":
        allsets = json.load(io.open(jp, encoding="utf-8"))
    allsets[set_id] = dict(sorted(index.items(), key=lambda kv: int(kv[0])))
    with io.open(jp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dict(sorted(allsets.items())), fh, separators=(",", ":"))
    return out


def verify(assets, set_id):
    """index <-> files, both ways, for one set. -> number of problems"""
    idx = json.load(io.open(os.path.join(assets, "woodcuts.json"), encoding="utf-8")).get(set_id, {})
    want = {"%s_%s.png" % (b, cv.replace(":", "_")) for b, cvs in idx.items() for cv in cvs}
    have = set(os.listdir(os.path.join(assets, "woodcuts", set_id)))
    bad = len(want - have) + len(have - want)
    print("verify %s: index %d, files %d, missing %d, unindexed %d" % (
        set_id, len(want), len(have), len(want - have), len(have - want)))
    return bad


def selftest():
    tmp = tempfile.mkdtemp()
    try:
        cd, ad = os.path.join(tmp, "crops"), os.path.join(tmp, "assets")
        os.makedirs(cd)
        os.makedirs(ad)
        rows = []
        for i, (fl, kind) in enumerate([([], "opening"), ([], "mid"), (["GREW-OK 1x1>1x1"], "mid"),
                                        (["GREW 9x9>1x1"], "mid"), ([], "mid")]):
            fn = "70_1_%d.png" % (i + 1)
            Image.new("LA", (40, 300 if i == 0 else 50), (0, 200)).save(os.path.join(cd, fn))
            rows.append({"slot": 70, "ch": 1, "v": i, "kind": kind, "flags": fl, "file": fn})
        json.dump(rows, open(os.path.join(cd, "crops.json"), "w"))
        ship, skip = plan(cd, {"70_1_5.png"}, set())
        write(cd, ship, ad, "kxii")
        got = sorted(json.load(open(os.path.join(ad, "woodcuts.json")))["kxii"]["70"])
        h0 = Image.open(os.path.join(ad, "woodcuts", "kxii", "70_1_1.png")).size[1]
        ok1 = got == ["1:1", "1:2", "1:3"] and verify(ad, "kxii") == 0 and h0 == MAX_H

        # thor: t3 is look-bad, t4 + t5 both claim john 3:16, t6 sits under two addresses
        td = os.path.join(tmp, "thor")
        os.makedirs(os.path.join(td, "small"))
        names = ["small/john_p1_%d.png" % i for i in range(1, 8)]
        for n in names:
            Image.new("LA", (30, 40), (0, 200)).save(os.path.join(td, n))
        with io.open(os.path.join(td, "sheet_key.tsv"), "w", encoding="utf-8") as fh:
            fh.write("cell\tsheet\tfile\n" + "".join("C%d\t1\t%s\n" % (i + 1, n) for i, n in enumerate(names)))
        with io.open(os.path.join(td, "LOOK_RESULT.txt"), "w", encoding="utf-8") as fh:
            fh.write("# fixture\nC3 CUT\n")
        json.dump([{"book": "john", "addr": "1:6", "file": names[0]},
                   {"book": "mark", "addr": "2:1", "file": names[1]},
                   {"book": "john", "addr": "2:1", "file": names[2]},
                   {"book": "john", "addr": "3:16", "file": names[3]},
                   {"book": "john", "addr": "3:16", "file": names[4]},
                   {"book": "john", "addr": "4:1", "file": names[5]}], open(os.path.join(td, "s1.json"), "w"))
        json.dump([{"book": "john", "addr": "4:2", "file": names[5]},
                   {"book": "john", "addr": "4:3", "file": names[6]}], open(os.path.join(td, "s2.json"), "w"))
        verses = {(42, 1, 6): "\u00B7Ar var", (40, 2, 1): "Og", (42, 4, 3): "mun Himnarijke"}
        ship, skip = plan_thor(td, ["s1.json", "s2.json"], text=lambda b, c, v: verses.get((b, c, v), "X"))
        write(td, ship, ad, "thl")
        allsets = json.load(open(os.path.join(ad, "woodcuts.json")))
        thor = allsets.get("thl", {})
        ok2 = thor == {"40": ["2:1"], "42": ["1:6"]} and verify(ad, "thl") == 0
        ok3 = sorted(allsets.get("kxii", {}).get("70", [])) == ["1:1", "1:2", "1:3"]
        ok = ok1 and ok2 and ok3
        print("SELFTEST woodcuts %s (kxii %s, thl %s %s, kxii kept after thl write %s)" % (
            "PASS" if ok else "FAIL", got, "ok" if ok2 else "BAD", thor, ok3))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=("kxii", "thl"), default="kxii")
    ap.add_argument("--crops")
    ap.add_argument("--exclude", help="kxii: the look's excluded files")
    ap.add_argument("--allow-grew", default="")
    ap.add_argument("--ship", default="ship.json,ship2.json", help="thl: ship lists in --crops")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    g = ap.parse_args()
    if g.selftest:
        return selftest()
    if g.set == "thl":
        crops = g.crops or THOR_DIR
        lists = [s.strip() for s in g.ship.split(",") if s.strip()]
        missing = [s for s in lists if not os.path.exists(os.path.join(crops, s))]
        if missing:
            ap.error("ship list(s) not found in %s: %s" % (crops, missing))
        ship, skip = plan_thor(crops, lists, text=thl_text())
        print("thl: lists %s" % lists)
    else:
        if not (g.crops and g.exclude):
            ap.error("--crops and --exclude are required (the crop-check look must have run)")
        crops = g.crops
        exclude = {l.split("#")[0].strip() for l in io.open(g.exclude, encoding="utf-8")} - {""}
        allow = {s.strip() for s in g.allow_grew.split(",")} - {""}
        ship, skip = plan(crops, exclude, allow)
        print("exclude list %d" % len(exclude))
    print("ship %d, skip %d" % (len(ship), len(skip)))
    for fn, why in skip:
        print("   skip %-40s %s" % (fn, why))
    if not g.apply:
        print("DRY RUN - --apply writes %s/woodcuts/%s/ + the %s key of woodcuts.json" % (ASSETS, g.set, g.set))
        return 0
    write(crops, ship, ASSETS, g.set)
    return 1 if verify(ASSETS, g.set) else 0


if __name__ == "__main__":
    sys.exit(main())
