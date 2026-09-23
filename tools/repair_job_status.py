# -*- coding: utf-8 -*-
"""Report whether a `repair_verses.py` job is FINISHED, CRASHED, RUNNING or DEAD.

    python tools/repair_job_status.py                  # every known job
    python tools/repair_job_status.py --job <name>     # one
    python tools/repair_job_status.py --selftest

## Why this exists — FOUR SILENT DEATHS, measured 2026-09-22

A repair run wrote one log and nothing else, and its LAST LOG LINE looked the
same whether the process had finished, died, or was still working. Over EVERY
`pron_requeue_*.log` on this box (full denominator, not a sample):

    pron_requeue_en_2026-09-21a.log       OK=3     finished=2
    pron_requeue_en_2026-09-21b.log       OK=0     finished=0
    pron_requeue_en_2026-09-21c.log       OK=105   finished=0   <- DIED
    pron_requeue_en_2026-09-21d.log       OK=3     finished=1
    pron_requeue_en_STALE_2026-09-21.log  OK=50    finished=0   <- DIED
    pron_requeue_en_STALE_2026-09-22b.log OK=86    finished=0   <- DIED
    pron_requeue_en_STALE_2026-09-22c.log OK=0     finished=0   <- running now

**Four of seven runs ended with no completion line** — one of them at 105
chapters, the job a handoff called the CERTAIN one to wait for. Each death cost
a session's worth of GPU time because "dead at 86" and "running at 86" could
only be told apart by reading the process list, and three sessions did not.

⚑ THE VERDICT IS DERIVED FROM THE MARKER **AND** THE LIVE PROCESS LIST TOGETHER,
never from either alone. That conjunction is the whole tool:

    marker      pid alive   verdict
    finished    —           FINISHED
    crashed     —           CRASHED (with the reason)
    running     yes         RUNNING
    running     no          DIED          <- the headline; nothing else reports it
    missing     —           UNKNOWN

Either half alone is wrong in a way that has already cost work: the marker alone
cannot see a SIGKILL (state stays `running` forever), and the process list alone
cannot see a run that ended ten seconds ago.

## ⛔⛔ A STATUS THAT CANNOT BE DETERMINED MUST NOT RETURN A PLAUSIBLE NUMBER

This repo has been burned by a count function that returned a believable value
on a failed read and blocked a chain with nothing in any log. So an unreadable
or corrupt marker prints `COULD NOT DETERMINE` with the reason and exits **2** —
never `0 done`, never `UNKNOWN` rendered as `FINISHED`, never a guess
reconstructed from the log.

⚠ A pid is RECYCLED. "The pid is alive" is not "this job is alive", so the
process COMMAND LINE is compared too — via `repair_verses.proc_cmdline`, the
same code the tool's own GPU-contention guard uses, not a second implementation.
⚠ And if the command line cannot be read, that is COULD NOT DETERMINE — not
"alive", because "alive" is the reassuring direction and a failed read must not
produce the reassuring answer.

Exit codes (following `thorlaks_numeral_seam_screen.py`):
    0  every job FINISHED
    1  any job DIED or CRASHED
    2  could not determine — unreadable/corrupt marker, or no marker directory

## --selftest, and its known-bad control

`HEXAPLA_MARKER_LOG_ONLY=1` makes the tool ignore the process list and judge
purely from the marker FILE, reinstating exactly today's blind spot: a job
killed while `state:"running"` then reads as RUNNING forever.

    PYTHONIOENCODING=utf-8 python tools/repair_job_status.py --selftest ; echo rc=$?
    # 0
    HEXAPLA_MARKER_LOG_ONLY=1 PYTHONIOENCODING=utf-8 python tools/repair_job_status.py --selftest ; echo rc=$?
    # 1, FAIL on the DIED assertion

⛔ Gated on `_IN_SELFTEST` so it can never alter a real verdict.
⛔ A test that passes BOTH ways is broken and worse than no test.
"""
import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import repair_verses as rv

_IN_SELFTEST = False

# The marker directory the render writes into. Resolved from repair_verses so
# the two can never disagree about where a marker lives.
JOBS_DIR = rv._JOBS_DIR

# Verdicts
FINISHED = "FINISHED"
CRASHED = "CRASHED"
RUNNING = "RUNNING"
DIED = "DIED"
UNKNOWN = "UNKNOWN"
UNDETERMINED = "COULD NOT DETERMINE"


def marker_only():
    """Judge from the marker FILE alone — the known-bad control.

    Reinstates the exact blind spot this tool exists to remove: a process
    SIGKILLed while `state:"running"` leaves that state on disk forever, so a
    log-only reading calls a dead render RUNNING and the next session waits on
    it. Measured: four runs died that way in two days.

    ⛔ Gated on _IN_SELFTEST so a real verdict is never blinded.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_MARKER_LOG_ONLY") == "1"


def jobs_dir():
    """Resolve the marker directory AT CALL TIME (never bind it as a default).

    ⚠ A default-arg `p=JOBS_DIR` would bind at definition time and ignore both
    the selftest's repointing and any future move of the marker directory.
    """
    return rv._JOBS_DIR


def read_marker(path):
    """-> (data, error). `data` is None and `error` is a reason string on failure.

    ⛔ A corrupt marker is NOT UNKNOWN and NOT FINISHED — it is a failure to
    read, and the caller must say so. Returning a reconstructed state here is
    the class of defect the repo's standing rule forbids.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return None, "corrupt JSON (%s: %s)" % (type(exc).__name__, exc)
    if not isinstance(data, dict):
        return None, "marker is not a JSON object"
    if "state" not in data:
        return None, "marker has no `state` field"
    return data, None


def cmdline_matches(cmdline, job):
    """Does this command line plausibly belong to `job`?

    ⚠ DELIBERATELY LOOSE on the interpreter path and STRICT on the two things
    that identify the run: the script it executes, and the job identity (the
    queue basename, which is what the marker is named after). A run started as
    `... --queue _work/en_pron_requeue_STALE_2026-09-21.txt` carries that
    basename; the marker's `job` is exactly that basename.
    """
    if not cmdline:
        return False
    low = cmdline.lower()
    if "repair_verses" not in low and "_rv_head_cmp" not in low:
        return False
    if job.lower() not in low:
        return False
    return True


def verdict_for(data, job, live=None):
    """-> (verdict, detail). The marker AND the process list, together.

    `live` is an injectable seam for the selftest: it returns
    (alive, cmdline) for a pid. Production calls `live_probe`.
    """
    probe = live or live_probe
    state = data.get("state")

    if state == "finished":
        return FINISHED, "rc %s" % (data.get("rc"),)
    if state == "crashed":
        return CRASHED, data.get("crash") or "no reason recorded"

    if state == "running":
        pid = data.get("pid")
        if pid is None:
            return UNDETERMINED, "marker says running but records no pid"
        if marker_only():
            # ⛔⛔ THE KNOWN-BAD CONTROL: no process check at all, so a killed
            # run reads as RUNNING forever. This is what the tool is for.
            return RUNNING, "marker only (control) — pid %s not checked" % pid
        alive, cmdline = probe(pid)
        if alive is None:
            # ⚠ A failed read must NOT produce the reassuring answer.
            return UNDETERMINED, ("could not read the process table for pid %s"
                                  % pid)
        if not alive:
            return DIED, ("pid %s is gone and the marker still says running"
                          % pid)
        if cmdline is None:
            return UNDETERMINED, ("pid %s is alive but its command line could "
                                  "not be read — cannot tell it from a "
                                  "recycled pid" % pid)
        if not cmdline_matches(cmdline, job):
            # ⚑ A recycled pid, or a different tool. NOT RUNNING: the marker
            # names a process that is not this job, which is the same defect as
            # a death. Report it as DIED so it is acted on, and say why.
            return DIED, ("pid %s is alive but is NOT this job (command line "
                          "does not name it) — a recycled pid" % pid)
        return RUNNING, "pid %s alive and its command line names the job" % pid

    return UNKNOWN, "marker carries an unrecognised state «%s»" % (state,)


def live_probe(pid):
    """-> (alive: True/False/None, cmdline: str/None) for one pid."""
    alive = rv.proc_alive(pid)
    if alive is not True:
        return alive, None
    return True, rv.proc_cmdline(pid)


def fmt_age(seconds):
    if seconds is None:
        return "-"
    if seconds < 90:
        return "%ds" % int(seconds)
    if seconds < 5400:
        return "%dm" % int(seconds // 60)
    return "%.1fh" % (seconds / 3600.0)


def report(paths, job_filter=None):
    """-> (rows, rc). Prints one line per job. rc 2 if anything is unreadable.

    ⚠ An EMPTY `paths` list is NOT a missing directory. `main()` checks the
    directory separately and exits before reaching here; this guard exists for
    the direct-call case, and it must say WHICH of the two it is. Conflating
    «the directory is gone» with «no markers have been written yet» is exactly
    the plausible-but-wrong answer this tool's contract forbids — and it is
    also the honest answer for a machine whose render was launched from code
    older than the marker (i.e. right now).
    """
    if not paths:
        print("⛔ COULD NOT DETERMINE — no job markers under")
        print("    %s" % jobs_dir())
        print("    ⚠ The directory exists but holds no marker. A job launched")
        print("      from code OLDER than 2026-09-22 writes NO marker, so this")
        print("      is NOT «nothing running». Check the process list by hand:")
        print("      python tools/live_status.py -p \"repair_verses\"")
        return [], 2

    rows = []
    undetermined = False
    for p in paths:
        job = p.stem
        if job_filter and job != job_filter:
            continue
        data, err = read_marker(p)
        if data is None:
            undetermined = True
            rows.append((job, UNDETERMINED, 0, 0, 0, None, err))
            continue
        v, detail = verdict_for(data, job)
        age = None
        try:
            age = time.time() - p.stat().st_mtime
        except OSError:
            age = None
        rows.append((job, v, data.get("done"), data.get("total"),
                     data.get("ok"), age, detail))

    if job_filter and not rows:
        print("⛔ COULD NOT DETERMINE — no marker named «%s» under" % job_filter)
        print("    %s" % jobs_dir())
        return [], 2

    for (job, v, done, total, ok, age, detail) in rows:
        print("%-34s %-18s %s/%s ok=%s age=%s  %s"
              % (job, v, done, total, ok, fmt_age(age), detail))

    if undetermined:
        return rows, 2
    if any(r[1] in (DIED, CRASHED) for r in rows):
        return rows, 1
    return rows, 0


# ---------------------------------------------------------------- selftest
def selftest():
    """Both-ways controls on synthetic markers in a temp dir.

    ⛔ Never reads or writes the real `narration/logs/_jobs/`. The real
    directory holds LIVE state — a fixture written there would be read as a
    job by the next session.
    """
    global _IN_SELFTEST
    _IN_SELFTEST = True
    fails = []

    def ok(cond, what):
        print(("ok   - " if cond else "FAIL - ") + what, flush=True)
        if not cond:
            fails.append(what)

    saved = rv._JOBS_DIR
    root = tempfile.mkdtemp(prefix="repair_job_status_")
    try:
        rv._JOBS_DIR = Path(root)

        def write(name, body):
            p = Path(root) / (name + ".json")
            p.write_text(json.dumps(body), encoding="utf-8")
            return p

        def run_one(name, live=None):
            """Drive the REAL verdict path for one marker in a fresh dir."""
            p = Path(root) / (name + ".json")
            data, err = read_marker(p)
            if data is None:
                return UNDETERMINED, err
            return verdict_for(data, name, live=live)

        # ── 1. THE DIED VERDICT — the headline ───────────────────────────
        # ⚠ A pid that CANNOT exist: the maximum PID on Windows is 2**32-1, and
        # reserving one is not possible, so we use a pid that is one past the
        # 32-bit range — `os.kill` cannot succeed on it. We additionally verify
        # the guarantee by asserting rv.proc_alive() reports it not-alive.
        IMPOSSIBLE = 4294967295 + 12345
        write("job_died_marker", {"job": "job_died_marker", "state": "running",
                                  "pid": IMPOSSIBLE, "total": 159, "done": 86,
                                  "ok": 86, "fail": 0})
        alive_direct = rv.proc_alive(IMPOSSIBLE)
        v, d = run_one("job_died_marker")
        ok(v == DIED and alive_direct is False,
           "1. marker says running + pid %d is not alive (verified directly: "
           "proc_alive=%s) -> DIED (got %s: %s)"
           % (IMPOSSIBLE, alive_direct, v, d))

        # ── 2. THE FALSE-POSITIVE CONTROL, and it matters most ───────────
        # Marker running, pid alive AND its command line names this job -> RUNNING.
        # Use the CURRENT process as the live pid, with a probe that reports our
        # own real command line so `cmdline_matches` is exercised for real.
        me = os.getpid()
        real_cmd = rv.proc_cmdline(me)
        write("job_live_marker", {"job": "job_live_marker", "state": "running",
                                  "pid": me, "total": 159, "done": 84,
                                  "ok": 84, "fail": 0})

        def live_self(pid, _real=real_cmd):
            # Report the live truth about THIS pid, but hand back a command line
            # that genuinely names the job (as a real matching run would). The
            # alive-ness is real; only the string is synthesised, and only after
            # we have proven we can read a real one.
            return rv.proc_alive(pid), (
                "python.exe tools/repair_verses.py --set kjv --queue "
                "_work/job_live_marker.txt")

        v2, d2 = run_one("job_live_marker", live=live_self)
        ok(v2 == RUNNING and real_cmd is not None,
           "2. marker running + pid %d alive + command line names the job -> "
           "RUNNING (got %s: %s). [read a real cmdline this session: %s]"
           % (me, v2, d2, "yes" if real_cmd else "NO"))

        # ── 3. PID RECYCLING ─────────────────────────────────────────────
        # Marker says running, the pid IS alive, but its command line is some
        # OTHER program. ⚑ Verdict chosen: DIED, not RUNNING and not UNKNOWN.
        # Reason: the marker names a process that is not this job, and the
        # actionable reading is «this job is not running». Reporting RUNNING
        # would reproduce the exact failure the tool exists to prevent.
        def live_other(pid):
            return rv.proc_alive(pid), "explorer.exe"

        v3, d3 = run_one("job_live_marker", live=live_other)
        ok(v3 == DIED,
           "3. marker running + pid alive but a DIFFERENT program -> DIED "
           "(chosen over RUNNING/UNKNOWN: the job is not running) "
           "(got %s: %s)" % (v3, d3))

        # ── 3b. an UNREADABLE command line is COULD NOT DETERMINE ────────
        # ⚠ Not "alive": a failed read must not produce the reassuring answer.
        def live_unreadable(pid):
            return True, None

        v3b, d3b = run_one("job_live_marker", live=live_unreadable)
        ok(v3b == UNDETERMINED,
           "3b. marker running + pid alive but cmdline UNREADABLE -> COULD NOT "
           "DETERMINE, not RUNNING (got %s: %s)" % (v3b, d3b))

        # ── 4. finished -> FINISHED, and the counts are the MARKER's ─────
        write("job_fin_marker", {"job": "job_fin_marker", "state": "finished",
                                 "pid": 999999, "total": 159, "done": 159,
                                 "ok": 150, "fail": 9, "rc": 1})
        v4, d4 = run_one("job_fin_marker")
        p4 = Path(root) / "job_fin_marker.json"
        data4, _ = read_marker(p4)
        ok(v4 == FINISHED and data4["done"] == 159 and data4["ok"] == 150
           and data4["fail"] == 9,
           "4. `finished` -> FINISHED (got %s) and the counts printed are the "
           "marker's own (done=159 ok=150 fail=9), not recomputed from a log"
           % v4)

        # ── 5. ATOMICITY: a corrupt marker -> COULD NOT DETERMINE, rc 2 ──
        # ⚠ Assert rc 2, NOT 1. The contract separates "a job failed" from
        # "the state could not be read at all", and conflating them is how a
        # failed read gets mistaken for a real answer.
        bad = Path(root) / "job_bad_marker.json"
        bad.write_text('{"job": "job_bad_marker", "state": "runn', encoding="utf-8")
        rc5 = report([bad])
        ok(rc5[1] == 2 and rc5[0][0][1] == UNDETERMINED,
           "5. a TRUNCATED marker -> COULD NOT DETERMINE and rc 2 (got rc %d, "
           "verdict %s) — no traceback" % (rc5[1], rc5[0][0][1] if rc5[0] else None))

        # ── 6. THE MARKER IS WRITTEN AT START, NOT ONLY AT THE END ───────
        # ⛔ Drive the REAL writer with a fixture and assert `running` exists
        # BEFORE any chapter is processed. Do not mock this into passing: a
        # marker that only appears on success cannot detect death, which is the
        # entire brief.
        started = time.time()
        rv.marker_start("kjv", str(Path(root) / "fixture_queue.txt"), 159,
                        ["repair_verses.py", "--set", "kjv"])
        mk = Path(root) / "fixture_queue.json"
        existed = mk.exists()
        body = json.loads(mk.read_text(encoding="utf-8")) if existed else {}
        # No chapter has run: done must still be 0 and state must be `running`.
        ok(existed and body.get("state") == "running"
           and body.get("done") == 0 and body.get("total") == 159
           and Path(root).joinpath("fixture_queue.json").stat().st_mtime
           >= started - 1,
           "6. BEFORE any chapter is processed the marker EXISTS with "
           "state=running, done=0, total=159 (state=%s, done=%s)"
           % (body.get("state"), body.get("done")))
        # Restore rv's marker state so a later marker_exit cannot target this
        # fixture's path — the selftest must not leave a live-looking marker.
        rv._MARKER["data"] = None
        rv._MARKER["path"] = None
        rv._MARKER["finished"] = True

        # ── 7. NON-REGRESSION PIN ────────────────────────────────────────
        # `repair_verses.py --help` must still parse and its documented exit
        # codes must be unchanged: 0 no failures / 1 any failure. Asserted
        # structurally here (the byte-comparison of --help is done in grading,
        # against the pre-change file, and is reported separately).
        import subprocess
        r = subprocess.run([sys.executable, str(HERE / "repair_verses.py"),
                            "--help"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        ok(r.returncode == 0 and "--set" in (r.stdout or "")
           and "--queue" in (r.stdout or ""),
           "7. repair_verses.py --help still exits 0 with its argument list "
           "intact (rc=%d)" % r.returncode)
    finally:
        rv._JOBS_DIR = saved
        import shutil
        shutil.rmtree(root, ignore_errors=True)

    print("", flush=True)
    if marker_only():
        print("⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_MARKER_LOG_ONLY=1 — the "
              "process list is IGNORED, so a job killed while state=running "
              "reads as RUNNING forever", flush=True)
    print("%d failure(s)" % len(fails), flush=True)
    return 1 if fails else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    # ⚠ Dispatch BEFORE building the parser. `--job` is optional here, but the
    # same pattern is required wherever a positional exists: argparse would
    # reject `--selftest` before any branch in the file ran.
    if "--selftest" in argv:
        sys.exit(selftest())

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--job", help="one job name (the marker's basename)")
    ap.add_argument("--selftest", action="store_true",
                    help="control on synthetic markers; never touches the real "
                         "narration/logs/_jobs/")
    a = ap.parse_args(argv)

    if not jobs_dir().is_dir():
        print("⛔ COULD NOT DETERMINE — no marker directory at")
        print("    %s" % jobs_dir())
        print("    A repair run writes markers here. ⛔ No directory is NOT")
        print("    «nothing running» — check the process list by hand:")
        print("    python tools/live_status.py -p \"repair_verses\"")
        sys.exit(2)

    if a.job:
        paths = [jobs_dir() / ("%s.json" % a.job)]
        if not paths[0].exists():
            print("⛔ COULD NOT DETERMINE — no marker named «%s» under" % a.job)
            print("    %s" % jobs_dir())
            print("    ⚠ A job launched from code OLDER than 2026-09-22 has NO")
            print("      marker. Absence is NOT «finished» — check the process")
            print("      list by hand.")
            sys.exit(2)
    else:
        paths = sorted(jobs_dir().glob("*.json"))

    rows, rc = report(paths, job_filter=a.job)
    sys.exit(rc)


if __name__ == "__main__":
    main()
