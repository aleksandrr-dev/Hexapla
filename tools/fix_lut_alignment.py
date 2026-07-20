# -*- coding: utf-8 -*-
"""Repair de_luther.json's ten misaligned chapters against the Zefania master.

THE DEFECT (found 2026-07-20 while chasing the "cosmetic" 2 Kgs 15:39 empty
slot): the v1.1 OCR scrape squeezed several native-numbered chapters into
KJV-shaped grids, leaving 8 empty trailing slots and 78 verses sitting one
slot away from where the digitization (and the versemap) put them. Because
fix_de_luther.py (2026-07-15) repairs by coordinate, those 78 verses were
correctly LEFT untouched then — but that also left them OCR-damaged, and
five verses of scripture were missing from the asset outright:

    2 Sam 19:1   the Absalom lament ("Mein Sohn Absalom!")  [KJV 18:33]
    1 Kgs 22:44  the high-places clause                     [KJV 22:43b]
    Acts 7:56    Stephen's "I see the heavens opened"       [KJV 7:56]
    Hag 2:22     "und will die Stühle der Königreiche..."   [KJV 2:22]
    Ps 13:7      "Ich will dem HErrn singen..."             [KJV 13:6]
    (plus 2 Kgs 15:39 and Hag 1:15, present in the master, absent here)

The versemap describes the digitization's true native arrangement, so every
one of these chapters ALSO paired off-by-one in split view.

Three further empty tails (Num 25:19, 1 Chr 12:41, Rev 12:18) are spurious
FOR THIS DIGITIZATION: the Zefania master keeps those chapters KJV-shaped
(Num 25:19's Hebrew content is the tail clause of its 25:18 — "und die
Plage danach kam" — so nothing is textually missing). Those slots are
DROPPED and the corresponding versemap runs move to wlc-only / are removed
in build_versemap.py (edited in the same change; re-run it after this).

Every site is assertion-gated against both the current asset shape and the
master text (skeleton ratio, autojunk=False — see fix_de_luther.py's trap
notes). If any assertion fails the script aborts before writing.

    python tools/fix_lut_alignment.py --master <path-to-zefania-xml> --dry-run
    python tools/fix_lut_alignment.py --master <path-to-zefania-xml>
"""
import argparse
import difflib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSET = (Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
         / "bibles" / "de_luther.json")
BACKUP = Path("C:/Projects/Hexapla-releases/asset-backups/de_luther.json.prealign.bak")


def skel(s):
    s = s.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]", "", s)


def ratio(a, b):
    return difflib.SequenceMatcher(None, skel(a), skel(b), autojunk=False).ratio()


def load_master(path):
    tree = ET.parse(path)
    m = {}
    for bb in tree.getroot().iter("BIBLEBOOK"):
        bn = int(bb.get("bnumber")) - 1
        for ch in bb.iter("CHAPTER"):
            cn = int(ch.get("cnumber")) - 1
            verses = {}
            for v in ch.iter("VERS"):
                verses[int(v.get("vnumber"))] = "".join(v.itertext()).strip()
            m[(bn, cn)] = [verses.get(i + 1, "") for i in range(max(verses))]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    master = load_master(args.master)
    books = json.load(open(ASSET, encoding="utf-8"))
    if isinstance(books, dict):
        books = books["books"]

    def A(bi, ci):
        return books[bi]["chapters"][ci]

    def M(bi, ci):
        return master[(bi, ci)]

    edits = []  # (label, apply_fn) — assertions run eagerly, writes deferred

    def gate(cond, label):
        if not cond:
            raise SystemExit(f"GATE FAILED: {label} — aborting, nothing written")

    # --- 1. 2 Sam 19: whole chapter shifted +1, native 19:1 (the lament) absent
    a, m = A(9, 18), M(9, 18)
    gate(len(a) == 44 and len(m) == 44, "2Sam19 counts")
    gate(a[43] == "", "2Sam19 slot 44 empty")
    gate(all(ratio(a[i], m[i + 1]) >= 0.85 for i in range(43)), "2Sam19 shift proof")
    gate("Absalom" in m[0] and "traurig" in m[0], "2Sam19 lament text sanity")
    edits.append(("2Sam19 <- master 1..44 (restores the Absalom lament at v1)",
                  lambda: A(9, 18).__setitem__(slice(None), list(M(9, 18)))))

    # --- 2. 1 Kgs 22: slots 44-53 shifted +1, native 22:44 absent
    a, m = A(10, 21), M(10, 21)
    gate(len(a) == 54 and len(m) == 54, "1Kgs22 counts")
    gate(a[53] == "", "1Kgs22 slot 54 empty")
    gate(all(ratio(a[i], m[i]) >= 0.85 for i in range(43)), "1Kgs22 head aligned")
    gate(all(ratio(a[i], m[i + 1]) >= 0.85 for i in range(43, 53)), "1Kgs22 tail shift proof")
    gate("Höhen" in m[43], "1Kgs22:44 high-places text sanity")
    edits.append(("1Kgs22 slots 44-54 <- master (restores v44)",
                  lambda: A(10, 21).__setitem__(slice(43, 54), list(M(10, 21))[43:54])))

    # --- 3. Acts 7: slots 56-59 shifted +1, native 7:56 absent
    a, m = A(43, 6), M(43, 6)
    gate(len(a) == 60 and len(m) == 60, "Acts7 counts")
    gate(a[59] == "", "Acts7 slot 60 empty")
    gate(all(ratio(a[i], m[i]) >= 0.85 for i in range(55)), "Acts7 head aligned")
    gate(all(ratio(a[i], m[i + 1]) >= 0.85 for i in range(55, 59)), "Acts7 tail shift proof")
    gate("Himmel offen" in m[55], "Acts7:56 heavens-opened text sanity")
    edits.append(("Acts7 slots 56-60 <- master (restores v56)",
                  lambda: A(43, 6).__setitem__(slice(55, 60), list(M(43, 6))[55:60])))

    # --- 4. 2 Kgs 15: master's final verse absent (native splits KJV 15:38)
    a, m = A(11, 14), M(11, 14)
    gate(len(a) == 39 and len(m) == 39, "2Kgs15 counts")
    gate(a[38] == "" and m[38] != "", "2Kgs15 slot 39 empty, master has text")
    gate(all(ratio(a[i], m[i]) >= 0.85 for i in range(38)), "2Kgs15 aligned")
    gate("Ahas" in m[38], "2Kgs15:39 Ahas text sanity")
    edits.append(("2Kgs15:39 <- master (needs NEW versemap run 15:38 = native 38-39)",
                  lambda: A(11, 14).__setitem__(38, M(11, 14)[38])))

    # --- 5+6. Haggai: 1:15 absent; ch2 has 2:1 duplicated at 2:2, rest shifted -1,
    #          master 2:22 absent
    a1, m1 = A(36, 0), M(36, 0)
    a2, m2 = A(36, 1), M(36, 1)
    gate(len(a1) == 15 and len(m1) == 15, "Hag1 counts")
    gate(a1[14] == "" and m1[14] != "", "Hag1 slot 15 empty, master has text")
    gate(len(a2) == 23 and len(m2) == 23, "Hag2 counts")
    gate(ratio(a2[0], m2[0]) >= 0.95, "Hag2:1 aligned")
    gate(ratio(a2[1], m2[0]) >= 0.85, "Hag2:2 is a duplicate of 2:1")
    gate(all(ratio(a2[i], m2[i - 1]) >= 0.85 for i in range(2, 22)), "Hag2 shift proof")
    gate(ratio(a2[22], m2[22]) >= 0.95, "Hag2:23 aligned")
    gate("Königreiche" in m2[21], "Hag2:22 kingdoms text sanity")
    edits.append(("Hag1:15 <- master", lambda: A(36, 0).__setitem__(14, M(36, 0)[14])))
    edits.append(("Hag2 <- master 1..23 (kills the 2:1 duplicate, restores 2:22)",
                  lambda: A(36, 1).__setitem__(slice(None), list(M(36, 1)))))

    # --- 7. Ps 13: master's 7th verse absent (native title-psalm, KJV has 6)
    a, m = A(18, 12), M(18, 12)
    gate(len(a) == 6 and len(m) == 7, "Ps13 counts")
    gate(all(ratio(a[i], m[i]) >= 0.85 for i in range(6)), "Ps13 aligned")
    gate("singen" in m[6], "Ps13:7 singing text sanity")
    edits.append(("Ps13 append v7 (title-psalm engine will emit runs on rebuild)",
                  lambda: A(18, 12).append(M(18, 12)[6])))

    # --- 8-10. Spurious empty tails (digitization keeps these KJV-shaped;
    #           Num 25:19's Hebrew content is the tail clause of master 25:18)
    for bi, ci, n, label in ((3, 24, 19, "Num25"), (12, 11, 41, "1Chr12"),
                             (65, 11, 18, "Rev12")):
        a, m = A(bi, ci), M(bi, ci)
        gate(len(a) == n and len(m) == n - 1, f"{label} counts")
        gate(a[n - 1] == "", f"{label} tail empty")
        gate(all(ratio(a[i], m[i]) >= 0.85 for i in range(n - 1) if a[i]),
             f"{label} aligned")
        edits.append((f"{label} drop spurious empty tail slot",
                      lambda bi=bi, ci=ci: A(bi, ci).pop()))
    gate("Plage danach kam" in M(3, 24)[17], "Num25:18 tail carries Heb 25:19 clause")

    print(f"All gates passed. {len(edits)} edits:")
    for label, _ in edits:
        print("  -", label)
    if args.dry_run:
        print("dry run — nothing written")
        return

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ASSET, BACKUP)
    for _, fn in edits:
        fn()

    # --- post-verify: every touched chapter must now match the master 1:1
    touched = [(9, 18), (10, 21), (43, 6), (11, 14), (36, 0), (36, 1),
               (18, 12), (3, 24), (12, 11), (65, 11)]
    for bi, ci in touched:
        a, m = A(bi, ci), M(bi, ci)
        assert len(a) == len(m), (bi, ci, len(a), len(m))
        for i in range(len(a)):
            assert ratio(a[i], m[i]) >= 0.95 or (not a[i] and not m[i]), \
                (bi, ci, i + 1, a[i][:50], m[i][:50])
    total = sum(len(c) for b in books for c in b["chapters"])
    empties = sum(1 for b in books for c in b["chapters"] for v in c if not v.strip())
    # Pre-fix: 31,172 slots of which 8 empty (CLAUDE.md's "31,164" counted
    # non-empty). Post-fix: -3 spurious slots, +1 Ps13 verse, 0 empties =
    # 31,170 slots — exactly the master's own verse count (fix_de_luther
    # docstring: "66 books, 31,170 verses"): full convergence.
    print(f"post-verify OK; {total} slots, {empties} empty")
    assert total == 31170 and empties == 0, (total, empties)

    with open(ASSET, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, separators=(",", ":"))
    print(f"written {ASSET}\nbackup at {BACKUP}")


if __name__ == "__main__":
    main()
