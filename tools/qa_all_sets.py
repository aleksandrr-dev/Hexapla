# -*- coding: utf-8 -*-
"""Run every DETERMINISTIC narration check against EVERY set. One report.

    tools\\.chatterbox_venv\\Scripts\\python.exe tools/qa_all_sets.py
    ... --sets ylt sv tyn --drift-sample 200

## Why this exists

Every defect this project has found in rendered audio was found by pointing one
tool at one set, reactively, after something already smelled wrong. That yields
bad news in slices - "15 % of ylt, then something else, then something else" -
and it is a property of HOW WE LOOK, not of the audio.

The two deterministic checks are cheap and cover every set:

  - `zero_duration_verses` - a verse has text but no audio. Caught ylt 1 Sam 28,
    which had passed a 1189/1189 completeness count.
  - `offset_drift` - the sidecar lies about where verses start. Silent in the
    app: verse highlighting and seek-to-verse drift away from the audio.
    ⚠ This one was BLIND until 2026-09-02 (it counted a silence run ending at
    EOF as a boundary, so whole sets came back "0 checked" and looked clean).

Neither needs a GPU, a model, or a human. There is no reason to run them one
set at a time after a problem appears.

⚠⚠ **WHAT THIS DOES NOT COVER.** It cannot hear anything. The repetition defect
confirmed by ear on ylt 2026-09-02 - Chatterbox re-saying the tail of a verse -
is INVISIBLE to both checks: the audio is present, correctly ordered, and the
offsets are right. Only `qa_asr_sweep.py` finds that, and only an ear confirms
it. A clean report here means "no missing and no misplaced audio", never "good".
"""
import argparse
import importlib.util
import io
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
NARRATION = Path("C:/Projects/Hexapla-releases/narration")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sets_present():
    spec = importlib.util.spec_from_file_location("narrate", HERE / "narrate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = []
    for k, cfg in m.LANG_CONFIG.items():
        d = NARRATION / k
        if d.is_dir() and any(d.rglob("*.ogg")):
            out.append((k, cfg.get("engine", "?")))
    return out


def run(cmd, timeout=None):
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="*")
    ap.add_argument("--drift-sample", type=int, default=150,
                    help="chapters per set for offset_drift (0 = all)")
    a = ap.parse_args()

    py = sys.executable
    found = sets_present()
    if a.sets:
        found = [(k, e) for k, e in found if k in a.sets]

    print(f"{len(found)} set(s) with audio on disk\n")
    rows = []
    for name, engine in found:
        n_ogg = len(list((NARRATION / name).rglob("*.ogg")))
        t0 = time.time()

        zd = run([py, str(HERE / "zero_duration_verses.py"), name], timeout=3600)
        zd_line = next((l for l in zd.splitlines()
                        if "chapters checked" in l or "verse(s)" in l), "").strip()
        zd_bad = None
        for tok in zd_line.replace(",", " ").split():
            if tok.isdigit() and "verse" in zd_line:
                pass
        # the tool prints "<set>   N chapters checked, M verse(s) with text but no audio"
        try:
            zd_bad = int(zd_line.split("checked,")[1].split()[0])
        except Exception:
            zd_bad = None

        cmd = [py, str(HERE / "offset_drift.py"), name]
        cmd += ["--all"] if a.drift_sample == 0 else ["--sample", str(a.drift_sample)]
        od = run(cmd, timeout=7200)
        od_line = next((l for l in od.splitlines() if "chapters checked" in l), "").strip()
        try:
            parts = od_line.split()
            checked = int(parts[0])
            drifted = int(parts[parts.index("with") - 1])
            unchk = int(parts[parts.index("uncheckable") - 1])
        except Exception:
            checked = drifted = unchk = None

        el = time.time() - t0
        rows.append((name, engine, n_ogg, zd_bad, checked, drifted, unchk, el))
        print(f"  {name:<5} {engine:<12} {n_ogg:>5} oggs | "
              f"zero-duration {zd_bad if zd_bad is not None else '?':>4} | "
              f"drift {drifted if drifted is not None else '?'}/"
              f"{checked if checked is not None else '?'} checked, "
              f"{unchk if unchk is not None else '?'} uncheckable | {el/60:.1f} min",
              flush=True)

    print("\n" + "=" * 78)
    print(f"{'set':<6}{'engine':<13}{'oggs':>6}{'no-audio':>10}{'drift':>8}"
          f"{'checked':>9}{'unchk':>7}")
    for name, engine, n, zd, ck, dr, un, _ in rows:
        f = lambda x: "?" if x is None else str(x)
        print(f"{name:<6}{engine:<13}{n:>6}{f(zd):>10}{f(dr):>8}{f(ck):>9}{f(un):>7}")
    bad = [r for r in rows if (r[3] or 0) > 0 or (r[5] or 0) > 0]
    print("\n" + ("⚠ SETS WITH FINDINGS: " + ", ".join(r[0] for r in bad)
                  if bad else "no missing or misplaced audio in any set"))
    print("⚠ This says NOTHING about repeated or hallucinated audio - both "
          "checks are\n  blind to it. See qa_asr_sweep.py.")


if __name__ == "__main__":
    main()
