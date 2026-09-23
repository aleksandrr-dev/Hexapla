# -*- coding: utf-8 -*-
"""Point every already-repaired chapter's `gate`/`failing` at the audio on disk.

    python tools/qa_gate_backfill_repairs.py --set en            # DRY RUN
    python tools/qa_gate_backfill_repairs.py --set en --apply
    python tools/qa_gate_backfill_repairs.py --selftest

## ⛔⛔ WHY THIS EXISTS

`repair_verses.py` used to write only `repairs` and `realigned` into
`<chapter>.qa.json`. `gate` and `failing` kept the ORIGINAL render's verdict,
so `qa_gate_appends.py` re-reported a repaired verse forever — a stale answer
indistinguishable from a fresh one, and `qa_verse_queue.py` re-condemned the
verse on every pass.

▶ Measured 2026-09-20 on the KJV repair: **10 of 45 repaired verses were still
  on the gate list**, with the ASR screen finding no append on any of them.
  The run's benign-looking «already done 31» was 31 chapters re-condemned off
  that stale record.
▶ `research/_evidence/en_kjv_repair_rescreen_2026-09-20.md`

`repair_verses.refresh_gate_record()` now fixes it going forward. This tool is
the one-off backfill for the records already on disk, and it uses **that same
function** — there is exactly one implementation of the rule.

## WHAT IT WILL AND WILL NOT TOUCH

- ✅ A verse whose LATEST repair entry actually replaced the audio.
- ⛔ A `kept_existing_take` repair. The gate could not discriminate, the
  shipped take was kept, the audio did NOT change — so its verdict must not.
- ⛔ Nothing else in the file. The pre-repair verdict is preserved under
  `gate_pre_repair`, so the original is never destroyed.

⚠ DRY RUN BY DEFAULT, and `--apply` backs every file up to `.qa.json.bak-gate`.

## ⚠ CONTROL IT BOTH WAYS BEFORE BELIEVING IT

`--selftest` asserts the rule in both directions on synthetic records:
a repaired-clean verse must LEAVE `failing`; a `still_failing` verse and a
`kept_existing_take` verse must STAY exactly as they were.

After `--apply`, the live control is `qa_gate_appends.py`: the flag count must
FALL by the repaired-clean verses and by nothing else.
"""
import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_spec = importlib.util.spec_from_file_location("rv", HERE / "repair_verses.py")
rv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rv)


def latest_per_verse(repairs):
    """The LAST repair entry for each verse — the one that describes the audio.

    ⚠ A verse can be repaired more than once (kjv 1/7 v3: 11:46 then 14:47).
    Only the last attempt produced the file that is on disk, so an earlier
    entry's reasons are not evidence about it. Order is file order, which is
    append order.
    """
    last = {}
    for r in repairs:
        last[r["verse"]] = r
    return [last[v] for v in sorted(last)]


def plan_chapter(qa):
    """-> (refreshed verses, verses left alone and why) without writing."""
    repairs = qa.get("repairs") or []
    if not repairs:
        return [], []
    probe = json.loads(json.dumps(qa))          # never mutate the caller's dict
    return rv.refresh_gate_record(probe, latest_per_verse(repairs))


def _selftest():
    ok = True

    def chk(name, got, exp):
        nonlocal ok
        good = got == exp
        ok = ok and good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: {got!r}")

    base = {"gate": {"3": {"attempts": [], "kept": 1,
                           "reasons": ["append:troes"]},
                     "9": {"attempts": [], "kept": 1,
                           "reasons": ["repeat:k2"]},
                     "12": {"attempts": [], "kept": 1,
                            "reasons": ["append:x"]}},
            "failing": {"3": ["append:troes"], "9": ["repeat:k2"],
                        "12": ["append:x"]}}

    print("known-GOOD: a repaired-clean verse must LEAVE failing")
    qa = json.loads(json.dumps(base))
    qa["repairs"] = [{"verse": 3, "ts": "t", "attempts": [], "kept": 1,
                      "kept_existing_take": False, "raw_reasons": [],
                      "still_failing": []}]
    touched, held = plan_chapter(qa)
    rv.refresh_gate_record(qa, latest_per_verse(qa["repairs"]))
    chk("planned v3", touched, [3])
    chk("v3 gone from failing", "3" in qa["failing"], False)
    chk("original preserved", qa["gate_pre_repair"]["3"]["reasons"],
        ["append:troes"])
    chk("v9 untouched", qa["failing"]["9"], ["repeat:k2"])

    print("known-BAD 1: a STILL FAILING repair must STAY on the list")
    qa = json.loads(json.dumps(base))
    qa["repairs"] = [{"verse": 9, "ts": "t", "attempts": [], "kept": 2,
                      "kept_existing_take": False,
                      "raw_reasons": ["repeat:k2"],
                      "still_failing": ["repeat:k2"]}]
    rv.refresh_gate_record(qa, latest_per_verse(qa["repairs"]))
    chk("v9 still failing", qa["failing"].get("9"), ["repeat:k2"])

    print("known-BAD 2: a kept_existing_take repair must change NOTHING")
    qa = json.loads(json.dumps(base))
    qa["repairs"] = [{"verse": 12, "ts": "t", "attempts": [], "kept": 1,
                      "kept_existing_take": True, "raw_reasons": [],
                      "still_failing": ["append:x"]}]
    touched, held = plan_chapter(qa)
    rv.refresh_gate_record(qa, latest_per_verse(qa["repairs"]))
    chk("nothing planned", touched, [])
    chk("held and named", held, [(12, "kept_existing_take — audio unchanged")])
    chk("v12 untouched", qa["failing"]["12"], ["append:x"])
    chk("no gate_pre_repair written", "gate_pre_repair" in qa, False)

    print("known-BAD 3: the LAST repair wins, not the first")
    qa = json.loads(json.dumps(base))
    qa["repairs"] = [{"verse": 3, "ts": "t1", "attempts": [], "kept": 1,
                      "kept_existing_take": False,
                      "raw_reasons": ["append:troes"],
                      "still_failing": ["append:troes"]},
                     {"verse": 3, "ts": "t2", "attempts": [], "kept": 1,
                      "kept_existing_take": False, "raw_reasons": [],
                      "still_failing": []}]
    rv.refresh_gate_record(qa, latest_per_verse(qa["repairs"]))
    chk("v3 cleared by the later repair", "3" in qa["failing"], False)

    print("known-BAD 4: a record with NO raw_reasons is UNKNOWN, never clean")
    qa = json.loads(json.dumps(base))
    qa["repairs"] = [{"verse": 3, "ts": "t", "attempts": [], "kept": 1,
                      "kept_existing_take": False, "still_failing": []}]
    touched, held = plan_chapter(qa)
    rv.refresh_gate_record(qa, latest_per_verse(qa["repairs"]))
    chk("nothing planned", touched, [])
    chk("held for the right reason",
        [w.startswith("repair record predates") for _, w in held], [True])
    chk("v3 STAYS on the list", qa["failing"]["3"], ["append:troes"])

    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", help="alignment set KEY, e.g. en / ylt / kxii")
    ap.add_argument("--apply", action="store_true",
                    help="write (default is a dry run)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()
    if not a.set:
        ap.error("--set is required (or --selftest)")
    if a.set not in rv.SETS:
        ap.error(f"unknown set {a.set!r}; known: {', '.join(sorted(rv.SETS))}")

    root = rv.NARRATION / rv.SETS[a.set]["dir"]
    if not root.is_dir():
        sys.exit(f"⛔ {root} does not exist — nothing to read")

    files = sorted(root.glob("*/*.qa.json"),
                   key=lambda p: (int(p.parent.name), int(p.name.split(".")[0])))
    n_files = n_touch = n_held = n_held_keep = n_held_unknown = 0
    for p in files:
        try:
            qa = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            # ⛔ Never a silent skip. A file this tool cannot read is a file it
            #    cannot speak for, and the run must not look complete.
            print(f"⛔ UNREADABLE {p}: {e}")
            return 2
        touched, held = plan_chapter(qa)
        if not touched and not held:
            continue
        b, c = p.parent.name, p.name.split(".")[0]
        if touched:
            n_files += 1
            n_touch += len(touched)
            print(f"{b}/{c}  refresh v{touched}")
        if held:
            n_held += len(held)
            n_held_keep += sum(1 for _, w in held if "kept_existing_take" in w)
            n_held_unknown += sum(1 for _, w in held
                                  if "kept_existing_take" not in w)
            for v, why in held:
                print(f"{b}/{c}  HELD   v{v} — {why}")
        if a.apply and touched:
            shutil.copy2(p, p.with_suffix(".json.bak-gate"))
            rv.refresh_gate_record(qa, latest_per_verse(qa["repairs"]))
            p.write_text(json.dumps(qa, separators=(",", ":"),
                                    ensure_ascii=False), encoding="utf-8")

    print(f"\n{'APPLIED' if a.apply else 'DRY RUN'}: {n_touch} verse(s) in "
          f"{n_files} chapter(s) refreshed, {n_held} held "
          f"({n_held_keep} kept_existing_take, {n_held_unknown} UNKNOWN — "
          f"record predates raw_reasons), over {len(files)} qa.json file(s)")
    if n_held_unknown:
        # ⚠ Named on purpose. These verses keep a verdict about audio that may
        #   no longer exist; they are not refreshed and they are not clean.
        print(f"⚠ {n_held_unknown} verse(s) keep a verdict this tool cannot "
              f"vouch for — listed above as UNKNOWN. They were NOT cleared.")
    if not a.apply:
        print("▶ nothing was written. Re-run with --apply.")
    else:
        print("▶ NOW CONTROL IT LIVE: `qa_gate_appends.py --lang <lang> "
              "--books 0-79` must have FALLEN by the repaired-clean verses "
              "and by nothing else. A count that did not move is a broken "
              "backfill, not a clean corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
