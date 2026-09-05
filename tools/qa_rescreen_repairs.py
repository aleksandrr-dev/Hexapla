# -*- coding: utf-8 -*-
"""Re-judge every REPAIRED verse on the LIVE audio, with the FIXED gate.

    tools\.chatterbox_venv\Scripts\python.exe tools\qa_rescreen_repairs.py --set ylt

## Why this exists

The 2026-09-04 ylt repair reported «169 chapters OK». That verdict was produced
by a gate with TWO FALSE-NEGATIVE MECHANISMS, both found by the owner's ear and
fixed on 2026-09-05 (CLAUDE.md, «THE GATE HAD FALSE NEGATIVES»). A pass from a
broken screen is not evidence, so every one of those OKs is unverified.

This re-runs the CURRENT gate over exactly the verses the repair touched,
reading the audio that is on disk NOW — i.e. the repaired takes.

## ⚠ It reads the LIVE tree on purpose

`qa_gate --validate` reads `narration/<set>_qa_fail_originals/` because it needs
the PRE-repair defect to prove the detector fires. This tool needs the opposite:
the post-repair audio, to find out whether the defect is still there. Do not
"fix" it to prefer originals — that would re-measure the old audio and report
the repair had failed everywhere.

## ⛔ It refuses rather than guesses

Two tools write `<c>.qa.json` and they do not share a schema. `render_preflight
report` once printed a ✅ VERDICT over 234 records it could not parse, because
it defaulted every missing key to 0. Here an unrecognised record is a hard exit,
and the counts of what was read are printed before any verdict.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NAR = Path("C:/Projects/Hexapla-releases/narration")


def collect(set_key):
    """-> (items, n_records, n_chapters). Hard-exits on an unknown schema."""
    root = NAR / set_key
    if not root.is_dir():
        sys.exit(f"no narration tree for '{set_key}' at {root}")
    items, records, chapters = [], 0, 0
    for js in sorted(root.glob("*/*.qa.json"),
                     key=lambda p: (int(p.parent.name), int(p.name.split(".")[0]))):
        b, ch = int(js.parent.name), int(js.name.split(".")[0])
        try:
            q = json.loads(js.read_text(encoding="utf-8"))
        except Exception as e:
            sys.exit(f"⛔ {js}: unreadable ({e}) — refusing to report over it")
        records += 1
        if "repairs" in q:                       # repair_verses.py schema
            vs = [r["verse"] for r in q["repairs"] if "verse" in r]
            if len(vs) != len(q["repairs"]):
                sys.exit(f"⛔ {js}: a repair record has no 'verse' key")
            if vs:
                chapters += 1
                items += [(b, ch, v) for v in vs]
        elif {"judged", "redrawn", "failing"} & set(q):   # narrate.py gate schema
            continue                             # render-time record, no repair
        else:
            sys.exit(f"⛔ {js}: UNRECOGNISED SCHEMA, keys {sorted(q)} — "
                     "refusing to default it to zero")
    return items, records, chapters


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--limit", type=int, help="score only the first N (a smoke test)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    items, records, chapters = collect(a.set_key)
    print(f"{a.set_key}: {records} qa.json record(s) read, "
          f"{chapters} carrying repairs, {len(items)} repaired verse(s)")
    if not items:
        sys.exit("no repaired verses found — refusing to print a verdict over nothing")
    if a.limit:
        items = items[: a.limit]
        print(f"⚠ --limit {a.limit}: scoring a SUBSET, this is a smoke test")

    import qa_gate
    print(f"judging {len(items)} verse(s) against the LIVE (repaired) audio\n",
          flush=True)
    with tempfile.TemporaryDirectory() as td:
        hits = qa_gate._judge(a.set_key, items, td, show=False)

    print(f"\nSUMMARY  {len(items)} repaired verse(s) re-judged, {hits} STILL FAILING")
    if a.out:
        Path(a.out).write_text(
            f"{a.set_key}\t{len(items)}\t{hits}\n", encoding="utf-8")
    # ⚠ 0 here is not "the set is clean" — it is "no repeat or append remains in
    # the verses that were repaired". Substitution, mid-verse repeats and
    # mispronunciation have no instrument; CLAUDE.md lists all five classes.
    print("⚠ scope: the REPAIRED verses only, and only the repeat/append classes.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
