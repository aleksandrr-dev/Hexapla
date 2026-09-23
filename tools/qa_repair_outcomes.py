# -*- coding: utf-8 -*-
"""What did each BY-THE-VERSE repair actually achieve? 0 model tokens, full corpus.

    python tools/qa_repair_outcomes.py --set kjv
    python tools/qa_repair_outcomes.py --set kjv --class still-failing
    python tools/qa_repair_outcomes.py --selftest

## Why this exists

`repair_verses.py` writes a record per repaired verse into `<chapter>.qa.json`
under "repairs", but nothing ever read those records back across the corpus. So
a repair that REPLACED a text-explained false positive with a REAL defect looked
exactly like a repair that worked.

Measured case that prompted this (Psalms 35:1, `18/34 v1`, 2026-09-20): the
original take's only flag was `repeat:k4` on the tail «fight against them that
fight against me» - which is the printed text. The repair drew three times:
attempt 1 appended «a vite against me» (a REAL defect), attempts 2 and 3 drew
the correct tail and were both flagged `repeat:k4` again - the same
text-explained false positive. The gate kept attempt 1. The owner's ear
confirmed: the kept take has the defect, the discarded original does not.

## The classes it separates

- `still-failing`  - the repair finished with `still_failing` non-empty: the
                     verse is no better, and it may be WORSE than the take it
                     replaced. Needs an ear or a revert.
- `unvouchable`    - the record predates `raw_reasons`, so nothing can say what
                     the kept take was judged on. Neither clean nor cleared.
- `kept-existing`  - the gate preferred the take already on disk; nothing moved.
- `clean`          - repaired and the kept take carries no reason.

⛔ **THIS CLEARS NOTHING.** A `clean` row means the screens are quiet, not that
the audio is good; only an ear clears a verse. This tool decides where to spend
the ear, nothing more.

⛔ A chapter whose qa.json cannot be read is reported as `UNREADABLE` and makes
the exit code non-zero. It is never counted as having no repairs - a read that
failed must not be indistinguishable from a chapter that was never repaired.

## ⛔ ONE ROW PER VERSE - the FINAL record, never every record

`repair_verses.py` APPENDS a record each time a verse is repaired, and a verse
gets repaired more than once on purpose: `--force` is how a condemned take is
redrawn. This tool used to emit one row PER RECORD, so a superseded attempt
stood beside the redraw that replaced it and the reader could not tell which
row described the audio ON DISK.

★ Numbers 7:16 (`3/6 v16`) is the measured case, 2026-09-21. It carries THREE
records: 09-15 (clean), 09-20 19:53 (`still_failing=repeat:k1,append:offering`),
and 09-20 20:12 - the `--force` redraw the owner then CLEARED by ear, whose
`still_failing` is empty. The tool reported it as `still-failing`, on the
middle record, for a defect that no longer exists in the file. Genesis 13:14
and Philemon 1:1 were each counted TWICE in the same class for the same reason.

So `scan()` folds every verse to the record with the LATEST `ts` (file order is
only the tie-break, exactly as `ear_cleared.index()` does it) and `--all-records`
shows the superseded history. ⚠ A record with NO `ts` sorts BELOW every dated
one - it cannot be shown to be the newest, so it never silently becomes the
verdict. ⛔ Known-bad control: `HEXAPLA_NO_REPAIRFOLD=1` restores the
one-row-per-record behaviour and the selftest asserts both directions.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")

# set key -> narration/ directory name. The key is NOT the directory name.
SET_DIR = {
    "kjv": "en",
    "ylt": "ylt",
    "kxii": "sv",
    "syn": "ru",
    "csl": "cu",
    "gen1599": "gnv",
    "wbt": "wbt",
    "wyc": "wyc",
    "tyn": "tyn",
}

CLASSES = ("still-failing", "unvouchable", "kept-existing", "clean")


def classify(rec):
    """Which class is this repair record in? Never guesses a missing field."""
    if rec.get("kept_existing_take") is True:
        return "kept-existing"
    if "raw_reasons" not in rec:
        # predates the field; nothing can vouch for what the kept take was judged on
        return "unvouchable"
    if rec.get("still_failing"):
        return "still-failing"
    return "clean"


def final_per_verse(repairs):
    """The LAST repair record for each verse, plus the superseded ones.

    ⛔ Ordered by the record's own `ts` first and list order only as the
    tie-break - not by list order alone. A record with no `ts` sorts below
    every dated one (`""` < any ISO stamp): it cannot be shown to be the
    newest, and a tool that guessed it was would report a defect that has
    already been redrawn, or hide one that has not.
    """
    if os.environ.get("HEXAPLA_NO_REPAIRFOLD") == "1":
        return list(repairs), []          # known-bad control: no fold at all
    best = {}
    for i, r in enumerate(repairs):
        v = r.get("verse")
        rank = (r.get("ts") or "", i)
        if v not in best or rank >= best[v][0]:
            best[v] = (rank, i, r)
    keep = {i for _, i, _ in best.values()}
    final = [r for i, r in enumerate(repairs) if i in keep]
    superseded = [r for i, r in enumerate(repairs) if i not in keep]
    return final, superseded


def scan(set_key):
    """Walk every chapter of the set. Returns (rows, unreadable, chapters_seen).

    ⛔ ONE ROW PER VERSE - see the module docstring. `rows` carries the FINAL
    record for each repaired verse; the superseded ones are counted and
    returned separately so they can be shown but never classified.
    """
    dirname = SET_DIR[set_key]
    root = DATA / "narration" / dirname
    orig_root = DATA / "narration" / f"{dirname}_qa_fail_originals"
    rows, unreadable, seen, old = [], [], 0, []

    for qa_path in sorted(root.glob("*/*.qa.json")):
        seen += 1
        try:
            rec = json.loads(qa_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - any failure is a reported failure
            unreadable.append((qa_path, repr(exc)))
            continue
        repairs = rec.get("repairs") or []
        if not repairs:
            continue
        book = qa_path.parent.name
        chapter = qa_path.name[: -len(".qa.json")]
        have_orig = (orig_root / book / f"{chapter}.ogg").exists()
        repairs, superseded = final_per_verse(repairs)
        for r in superseded:
            old.append((int(book), int(chapter), r.get("verse"), r.get("ts")))
        # a whole-chapter revert is only equivalent to an ear's verdict on ONE
        # verse when that verse is the ONLY repair in the chapter
        # ⛔ Counted on DISTINCT VERSES, not on records: a verse repaired three
        # times is still the sole repair in its chapter, and calling it `multi`
        # tells the reader a revert would undo other verses' work when it
        # would not. Numbers 7:16 read `multi` on its own re-repairs.
        sole = len({r.get("verse") for r in repairs}) == 1
        for r in repairs:
            rows.append(
                {
                    "book": int(book),
                    "chapter": int(chapter),
                    "verse": r.get("verse"),
                    "cls": classify(r),
                    "kept": r.get("kept"),
                    "attempts": len(r.get("attempts") or []),
                    "still_failing": r.get("still_failing") or [],
                    "text_explained": r.get("text_explained_repeats"),
                    "have_original": have_orig,
                    "sole_repair_in_chapter": sole,
                    "ts": r.get("ts"),
                }
            )
    return rows, unreadable, seen, old


def selftest():
    """Controls in BOTH directions on the classifier - a screen that cannot be
    shown to work must not have its verdicts used."""
    cases = [
        ({"kept_existing_take": True, "raw_reasons": [], "still_failing": []}, "kept-existing"),
        ({"kept_existing_take": False, "still_failing": ["append:x"]}, "unvouchable"),
        ({"kept_existing_take": False, "raw_reasons": ["append:x"], "still_failing": ["append:x"]}, "still-failing"),
        ({"kept_existing_take": False, "raw_reasons": [], "still_failing": []}, "clean"),
        # a record with raw_reasons but an EMPTY still_failing is clean even if
        # the draw was flagged mid-way
        ({"kept_existing_take": False, "raw_reasons": ["repeat:k4"], "still_failing": []}, "clean"),
    ]
    bad = 0
    for rec, expected in cases:
        got = classify(rec)
        ok = "ok" if got == expected else "WRONG"
        if got != expected:
            bad += 1
        print(f"CONTROL {expected:<14} got={got:<14} {ok}")

    # ★ The Numbers 7:16 shape: three records for ONE verse, the middle one
    # still-failing, the LAST one the `--force` redraw that cleared it. ⛔ Both
    # directions - a fold that cannot be shown to fail has not been shown to work.
    n716 = [
        {"verse": 16, "ts": "2026-09-15T06:53:01", "raw_reasons": [], "still_failing": []},
        {"verse": 16, "ts": "2026-09-20T19:53:41", "raw_reasons": ["repeat:k1"],
         "still_failing": ["repeat:k1", "append:offering"]},
        {"verse": 16, "ts": "2026-09-20T20:12:21", "raw_reasons": [], "still_failing": []},
        {"verse": 17, "ts": "2026-09-20T20:20:00", "raw_reasons": [], "still_failing": []},
        # ⚠ no `ts` at all: must NOT outrank a dated record
        {"verse": 17, "raw_reasons": ["append:x"], "still_failing": ["append:x"]},
    ]
    folded = os.environ.get("HEXAPLA_NO_REPAIRFOLD") != "1"
    final, superseded = final_per_verse(n716)
    got_cls = sorted((r["verse"], classify(r)) for r in final)
    if folded:
        want = [(16, "clean"), (17, "clean")]
        note = "one row per verse, the LAST record"
    else:
        want = sorted((r["verse"], classify(r)) for r in n716)
        note = "KNOWN-BAD: every record is a row"
    if got_cls != want:
        bad += 1
        print(f"CONTROL fold           got={got_cls} want={want}  WRONG")
    else:
        print(f"CONTROL fold           {note}: {got_cls}  ok")
    if folded and len(superseded) != 3:
        bad += 1
        print(f"CONTROL superseded     got={len(superseded)} want=3  WRONG")
    elif folded:
        print("CONTROL superseded     3 record(s) folded away, none classified  ok")

    if bad:
        print(f"\n⛔ {bad} control(s) WRONG - do not use this tool's verdicts.")
        return 1
    print("\n✅ controls pass")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", choices=sorted(SET_DIR))
    ap.add_argument("--class", dest="cls", choices=CLASSES, help="print only this class")
    ap.add_argument("--all-records", action="store_true", dest="all_records",
                    help="also list the superseded repair records that were "
                         "folded away (history; ⛔ never a work item)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.set_key:
        ap.error("--set is required unless --selftest")

    rows, unreadable, seen, old = scan(args.set_key)
    print(f"set {args.set_key} -> narration/{SET_DIR[args.set_key]} · {seen} chapter(s) read")
    if os.environ.get("HEXAPLA_NO_REPAIRFOLD") == "1":
        print("⛔ HEXAPLA_NO_REPAIRFOLD=1 - EVERY record is a row, including "
              "superseded ones. Known-bad control: a redrawn verse still shows "
              "the defect of the take it replaced.")
    elif old:
        print(f"⚠ {len(old)} superseded repair record(s) folded away - a verse "
              f"repaired again keeps only its LAST record "
              f"(`--all-records` lists them).")
    if args.all_records and old:
        for b, c, v, ts in old:
            print(f"    superseded  {b:>3} {c:>3} v{v:<4} {ts}")

    if not rows:
        print("no repair records at all")
        return 1 if unreadable else 0

    counts = {c: 0 for c in CLASSES}
    for r in rows:
        counts[r["cls"]] += 1
    chapters = len({(r["book"], r["chapter"]) for r in rows})
    print(f"{len(rows)} repaired verse(s) in {chapters} chapter(s)")
    for c in CLASSES:
        print(f"  {c:<14} {counts[c]}")

    show = [r for r in rows if args.cls is None or r["cls"] == args.cls]
    if args.cls:
        print(f"\n--- {args.cls} ({len(show)}) ---")
        for r in show:
            flags = ",".join(r["still_failing"]) or "-"
            orig = "orig" if r["have_original"] else "NO-ORIGINAL"
            sole = "sole" if r["sole_repair_in_chapter"] else "multi"
            print(
                f"{r['book']:>3} {r['chapter']:>3} v{r['verse']:<4} "
                f"kept={r['kept']} of {r['attempts']}  {orig:<11} {sole:<6} {flags}"
            )
        print(
            "\n⛔ Nothing here is cleared. `orig`+`sole` means a whole-chapter revert\n"
            "   would restore exactly the take the ear compared against; `multi` means\n"
            "   a revert would also undo the other repairs in that chapter."
        )

    rc = 0
    if unreadable:
        rc = 1
        print(f"\n⛔ {len(unreadable)} chapter(s) UNREADABLE - counted as neither:")
        for p, exc in unreadable[:10]:
            print(f"   {p}  {exc}")
    if counts["still-failing"] or counts["unvouchable"]:
        rc = rc or 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
