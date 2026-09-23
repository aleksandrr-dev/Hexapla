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

## Exit code

0 ONLY on a real all-clear: every requested set checked AND clean. A set whose
child screen crashed (rc != 0) or whose counts never parsed is listed as
COULD NOT CHECK and exits 1 - it is not covered by the report, so it is not
"clean" either.

    python tools/qa_all_sets.py --selftest      # synthetic rows, no real data
    HEXAPLA_NO_RCCHECK=1 python tools/qa_all_sets.py --selftest   # must FAIL

The second line is the known-bad control for the selftest: it restores the old
rc-blind verdict, so a crashed set passes and the selftest must exit 1.
"""
import argparse
import importlib.util
import io
import json
import os
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
    """Child output AND its returncode. ⚠ The rc is the point: a screen that
    crashed prints no parsable counts, and counts alone cannot tell that from
    "clean"."""
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "") + (r.stderr or ""), r.returncode


def summarize(rows):
    """Split rows into (findings, could-not-check).

    ⚠⚠ A set is COULD NOT CHECK when a child screen exited non-zero OR when a
    count did not parse (None). Both used to read as 0 and so as «no findings»,
    which is how a crashed screen printed an all-clear (census 2026-09-22).

    `HEXAPLA_NO_RCCHECK=1` restores that rc-blind behaviour. It exists only so
    `--selftest` can prove the check is doing something; never set it for real.
    """
    if os.environ.get("HEXAPLA_NO_RCCHECK"):
        return [r for r in rows if (r[3] or 0) > 0 or (r[5] or 0) > 0], []
    unchecked = [r for r in rows if r[8] != 0
                 or any(v is None for v in (r[3], r[4], r[5]))]
    names = {r[0] for r in unchecked}
    bad = [r for r in rows if r[0] not in names
           and ((r[3] or 0) > 0 or (r[5] or 0) > 0)]
    return bad, unchecked


def report(rows):
    """Print the verdict. Returns the process rc - 0 only on a real all-clear."""
    bad, unchecked = summarize(rows)
    if unchecked:
        print("\n⚠ COULD NOT CHECK: " + ", ".join(r[0] for r in unchecked))
        print("  a child screen crashed or printed no parsable count; this "
              "report does NOT cover these sets.")
        return 1
    if bad:
        print("\n⚠ SETS WITH FINDINGS: " + ", ".join(r[0] for r in bad))
    else:
        print("\nno missing or misplaced audio in any set")
    print("⚠ This says NOTHING about repeated or hallucinated audio - both "
          "checks are\n  blind to it. See qa_asr_sweep.py.")
    return 1 if bad else 0


def synth(name, zd, checked, drifted, unchk, rc=0):
    """A row shaped exactly like the ones main() builds. --selftest only: no
    narration/, no subprocess, no real screen."""
    return (name, "synthetic", 1, zd, checked, drifted, unchk, 0.0, rc)


def selftest():
    """Synthetic rows only. Exits 0 when both cases behave, 1 otherwise."""
    ok = True

    print("--- (a) every set checked and clean -> all-clear")
    rc = report([synth("alpha", 0, 10, 0, 0), synth("beta", 0, 10, 0, 0)])
    print(f"    rc={rc} (want 0)")
    ok = ok and rc == 0

    print("\n--- (b) beta's screen crashed: rc 1, counts never parsed")
    broken = [synth("alpha", 0, 10, 0, 0),
              synth("beta", None, None, None, None, 1)]
    rc = report(broken)
    named = [r[0] for r in summarize(broken)[1]]
    print(f"    rc={rc} (want 1)  COULD NOT CHECK: {named or 'nobody'}")
    ok = ok and rc == 1 and named == ["beta"]

    print("\nSELFTEST: " + ("PASS" if ok else
          "FAIL - the verdict did not tell a crashed screen apart from a "
          "clean one"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="synthetic rows only - no narration/, no subprocess")
    ap.add_argument("--sets", nargs="*")
    ap.add_argument("--drift-sample", type=int, default=150,
                    help="chapters per set for offset_drift (0 = all)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    py = sys.executable
    found = sets_present()
    if a.sets:
        found = [(k, e) for k, e in found if k in a.sets]

    print(f"{len(found)} set(s) with audio on disk\n")
    rows = []
    for name, engine in found:
        n_ogg = len(list((NARRATION / name).rglob("*.ogg")))
        t0 = time.time()

        zd, zd_rc = run([py, str(HERE / "zero_duration_verses.py"), name],
                        timeout=3600)
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
        od, od_rc = run(cmd, timeout=7200)
        od_line = next((l for l in od.splitlines() if "chapters checked" in l), "").strip()
        try:
            parts = od_line.split()
            checked = int(parts[0])
            drifted = int(parts[parts.index("with") - 1])
            unchk = int(parts[parts.index("uncheckable") - 1])
        except Exception:
            checked = drifted = unchk = None

        el = time.time() - t0
        rc = zd_rc or od_rc      # first non-zero child rc, else 0
        rows.append((name, engine, n_ogg, zd_bad, checked, drifted, unchk, el,
                     rc))
        print(f"  {name:<5} {engine:<12} {n_ogg:>5} oggs | "
              f"zero-duration {zd_bad if zd_bad is not None else '?':>4} | "
              f"drift {drifted if drifted is not None else '?'}/"
              f"{checked if checked is not None else '?'} checked, "
              f"{unchk if unchk is not None else '?'} uncheckable | {el/60:.1f} min"
              + (f"  <-- CHILD rc {rc}, NOT CHECKED" if rc else ""),
              flush=True)

    print("\n" + "=" * 78)
    print(f"{'set':<6}{'engine':<13}{'oggs':>6}{'no-audio':>10}{'drift':>8}"
          f"{'checked':>9}{'unchk':>7}")
    for name, engine, n, zd, ck, dr, un, _el, _rc in rows:
        f = lambda x: "?" if x is None else str(x)
        print(f"{name:<6}{engine:<13}{n:>6}{f(zd):>10}{f(dr):>8}{f(ck):>9}{f(un):>7}")
    return report(rows)


if __name__ == "__main__":
    sys.exit(main())
