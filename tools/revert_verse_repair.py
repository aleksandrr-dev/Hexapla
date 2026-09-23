# -*- coding: utf-8 -*-
"""Put back the PRE-REPAIR take of a chapter, when an ear ruled the repair worse.

    # plan only (DEFAULT - nothing is written)
    python tools/revert_verse_repair.py --set kjv --book 18 --chapter 34
    # do it
    python tools/revert_verse_repair.py --set kjv --book 18 --chapter 34 --apply \
        --reason "owner ear 2026-09-20: A has the repeat, B does not"
    python tools/revert_verse_repair.py --selftest

## Why this exists

`repair_verses.py` re-draws a condemned verse and keeps the best of N draws.
When every draw is defective it still keeps one - and it can keep a take that is
WORSE than the one it replaced. Measured (Psalms 35:1, `18/34 v1`, 2026-09-20):
the original's only flag was `repeat:k4` on the tail «fight against them that
fight against me», which is the printed text; the repair drew three times, kept
the one draw carrying a real appended «a vite against me», and discarded two
draws whose only flag was that same text-explained false positive. The owner's
ear ruled the discarded original clean.

There was no way to undo that. This is it.

## ⛔ WHAT MAKES THIS SAFE

1. ⛔ **DRY RUN IS THE DEFAULT.** `--apply` is required to write a byte.
2. ⛔ **WHOLE-CHAPTER ONLY, AND ONLY WHEN THE REPAIR WAS SOLE.** The backup in
   `<dir>_qa_fail_originals/` is a whole chapter, so restoring it also undoes
   every OTHER repair in that chapter. This REFUSES a chapter with more than one
   repaired verse unless `--force-multi` names every verse that will be undone.
   A partial revert is not offered because splicing a verse back in is the same
   operation that produced the defect.
3. ⛔ **NOTHING IS DELETED.** The current (repaired) files are copied to
   `<dir>_reverted_repairs/` BEFORE anything is overwritten, so the discarded
   repair stays available for an ear exactly like the originals do.
4. ⛔ **THE RESTORED qa.json KEEPS THE HISTORY.** The original qa.json comes
   back (so `gate`/`failing`/offsets describe the audio actually on disk), with
   the discarded repair records preserved under `reverted_repairs` together with
   the reason and who ruled it.
5. ⛔ **VERIFIED AGAINST THE FILES AFTERWARDS**, not against a return code: each
   restored file is re-read and byte-compared to its source, and the offset
   count is checked against the restored ogg. Any mismatch is a reported
   failure and a non-zero exit.

⚠ `.w.json` describes word timings for audio that is being replaced, so it is
restored from the backup too. If the backup has no `.w.json` this REFUSES
rather than leaving a sidecar describing audio that no longer exists.
"""
import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")

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

# every file that describes one chapter's audio
PARTS = (".ogg", ".json", ".w.json", ".eos.json", ".qa.json")
REQUIRED = (".ogg", ".json", ".w.json")


def chapter_paths(root, book, chapter):
    base = root / str(book)
    return {ext: base / f"{chapter}{ext}" for ext in PARTS}


def plan(data, set_key, book, chapter):
    """Read live state. Returns (ok, info, problems) - never guesses."""
    dirname = SET_DIR[set_key]
    live_root = data / "narration" / dirname
    orig_root = data / "narration" / f"{dirname}_qa_fail_originals"
    keep_root = data / "narration" / f"{dirname}_reverted_repairs"

    live = chapter_paths(live_root, book, chapter)
    orig = chapter_paths(orig_root, book, chapter)
    keep = chapter_paths(keep_root, book, chapter)

    problems = []
    for ext in REQUIRED:
        if not live[ext].exists():
            problems.append(f"live {live[ext]} missing")
        if not orig[ext].exists():
            problems.append(f"backup {orig[ext]} missing - nothing to revert to")

    repairs = []
    if live[".qa.json"].exists():
        try:
            qa = json.loads(live[".qa.json"].read_text(encoding="utf-8"))
            repairs = qa.get("repairs") or []
        except Exception as exc:  # noqa: BLE001
            problems.append(f"live qa.json unreadable: {exc!r}")
    else:
        problems.append("live qa.json missing - cannot tell what was repaired")

    if not repairs and not problems:
        problems.append("this chapter has NO repair records - nothing to revert")

    info = {
        "live": live,
        "orig": orig,
        "keep": keep,
        "repairs": repairs,
        "verses": [r.get("verse") for r in repairs],
    }
    return (not problems), info, problems


def do_revert(info, reason, ruled_by):
    """Copy current -> _reverted_repairs, then backup -> live. Verify both."""
    live, orig, keep = info["live"], info["orig"], info["keep"]
    keep[".ogg"].parent.mkdir(parents=True, exist_ok=True)

    # 1. preserve the repaired take first - nothing is ever deleted
    preserved = []
    for ext in PARTS:
        if live[ext].exists():
            shutil.copy2(live[ext], keep[ext])
            if keep[ext].read_bytes() != live[ext].read_bytes():
                return False, f"preserve FAILED to verify: {keep[ext]}"
            preserved.append(ext)

    # 2. restore audio + offsets + word timings from the pristine backup
    for ext in (".ogg", ".json", ".w.json", ".eos.json"):
        if not orig[ext].exists():
            if ext == ".eos.json":
                continue
            return False, f"backup missing {ext}"
        shutil.copy2(orig[ext], live[ext])
        if live[ext].read_bytes() != orig[ext].read_bytes():
            return False, f"restore FAILED to verify: {live[ext]}"

    # 3. the original qa.json comes back, carrying the discarded repair records
    qa = json.loads(orig[".qa.json"].read_text(encoding="utf-8"))
    qa.setdefault("reverted_repairs", []).append(
        {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "ruled_by": ruled_by,
            "discarded": info["repairs"],
            "discarded_audio": str(info["keep"][".ogg"]),
        }
    )
    live[".qa.json"].write_text(
        json.dumps(qa, ensure_ascii=False, indent=4), encoding="utf-8"
    )

    # 4. the restored sidecar must describe the restored audio
    # the sidecar key is "offsets" (with "edge_pad_ms" beside it) - NOT "o".
    # This check read "o", so a completed revert reported FAILED (2026-09-20).
    sidecar = json.loads(live[".json"].read_text(encoding="utf-8"))
    offsets = sidecar.get("offsets")
    if not offsets:
        return False, f"restored .json has no 'offsets' (keys: {sorted(sidecar)})"
    return True, f"restored {len(preserved)} file(s); {len(offsets)} verse offsets"


def selftest():
    """Controls in BOTH directions, on a throwaway tree."""
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        data = Path(td)
        live = data / "narration" / "en" / "18"
        orig = data / "narration" / "en_qa_fail_originals" / "18"
        live.mkdir(parents=True)
        orig.mkdir(parents=True)

        (live / "34.ogg").write_bytes(b"REPAIRED-AUDIO")
        (live / "34.json").write_text(json.dumps({"offsets": [0, 100], "edge_pad_ms": 940}), encoding="utf-8")
        (live / "34.w.json").write_text("{}", encoding="utf-8")
        (live / "34.qa.json").write_text(
            json.dumps({"repairs": [{"verse": 1, "still_failing": ["append:x"]}]}),
            encoding="utf-8",
        )
        (orig / "34.ogg").write_bytes(b"ORIGINAL-AUDIO")
        (orig / "34.json").write_text(json.dumps({"offsets": [0, 90], "edge_pad_ms": 940}), encoding="utf-8")
        (orig / "34.w.json").write_text("{}", encoding="utf-8")
        (orig / "34.qa.json").write_text(json.dumps({"failing": {"1": ["repeat:k4"]}}), encoding="utf-8")

        ok, info, probs = plan(data, "kjv", 18, 34)
        print(f"CONTROL plan-ok            got={ok} expected=True  {'ok' if ok else 'WRONG'}")
        bad += 0 if ok else 1

        ok2, msg = do_revert(info, "selftest", "selftest")
        restored = (live / "34.ogg").read_bytes()
        print(f"CONTROL restores-original  got={restored!r} {'ok' if restored == b'ORIGINAL-AUDIO' else 'WRONG'}")
        bad += 0 if restored == b"ORIGINAL-AUDIO" else 1

        kept = data / "narration" / "en_reverted_repairs" / "18" / "34.ogg"
        keptb = kept.read_bytes() if kept.exists() else b""
        print(f"CONTROL preserves-repaired got={keptb!r} {'ok' if keptb == b'REPAIRED-AUDIO' else 'WRONG'}")
        bad += 0 if keptb == b"REPAIRED-AUDIO" else 1

        newqa = json.loads((live / "34.qa.json").read_text(encoding="utf-8"))
        has = bool(newqa.get("reverted_repairs")) and "failing" in newqa
        print(f"CONTROL qa-history-kept    got={has} expected=True  {'ok' if has else 'WRONG'}")
        bad += 0 if has else 1

        # a chapter with NO repair record must be refused
        ok3, _, probs3 = plan(data, "kjv", 18, 99)
        refused = (not ok3) and bool(probs3)
        print(f"CONTROL refuses-missing    got={refused} expected=True  {'ok' if refused else 'WRONG'}")
        bad += 0 if refused else 1

    if bad:
        print(f"\n⛔ {bad} control(s) WRONG - do not use this tool.")
        return 1
    print("\n✅ controls pass")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", choices=sorted(SET_DIR))
    ap.add_argument("--book", type=int)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force-multi", nargs="*", type=int, default=None,
                    help="acknowledge every verse that a whole-chapter revert will undo")
    ap.add_argument("--reason", default="")
    ap.add_argument("--ruled-by", default="owner ear")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.set_key is None or args.book is None or args.chapter is None:
        ap.error("--set, --book and --chapter are required unless --selftest")

    ok, info, problems = plan(DATA, args.set_key, args.book, args.chapter)
    print(f"set {args.set_key} · book {args.book} chapter {args.chapter}")
    for r in info["repairs"]:
        sf = ",".join(r.get("still_failing") or []) or "-"
        print(f"  repair v{r.get('verse')}  kept={r.get('kept')}  still_failing={sf}  ts={r.get('ts')}")
    if problems:
        print("\n⛔ REFUSING:")
        for p in problems:
            print(f"   {p}")
        return 1

    verses = info["verses"]
    if len(verses) > 1:
        if args.force_multi is None or sorted(args.force_multi) != sorted(verses):
            print(
                f"\n⛔ REFUSING: this chapter has {len(verses)} repaired verses {verses}.\n"
                f"   A whole-chapter revert undoes ALL of them. Re-run with\n"
                f"   --force-multi {' '.join(str(v) for v in verses)}  to acknowledge that."
            )
            return 1

    if not args.apply:
        print(f"\n⚠ DRY RUN - nothing written. Would revert {len(verses)} repaired verse(s):")
        print(f"   restore from : {info['orig']['.ogg']}")
        print(f"   preserve to  : {info['keep']['.ogg']}")
        print("   pass --apply to do it.")
        return 0

    if not args.reason:
        print("\n⛔ REFUSING: --reason is required with --apply (who ruled, and on what).")
        return 1

    ok2, msg = do_revert(info, args.reason, args.ruled_by)
    if not ok2:
        print(f"\n⛔ FAILED: {msg}")
        return 1
    print(f"\n✅ REVERTED: {msg}")
    print("▶ Re-run the screen that condemned it, and re-align if the offsets moved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
