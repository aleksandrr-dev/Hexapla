# -*- coding: utf-8 -*-
"""Resume a rate-limited archive.org upload, but ONLY once the account task
ration has actually drained.

    python tools/ia_upload_watch.py --set ylt --check-only     # read state, do nothing
    python tools/ia_upload_watch.py --set ylt                  # watch and resume
    python tools/ia_upload_watch.py --set ylt --resume-at 80 --poll 900

## Why this exists

The 2026-09-08 ylt upload died on
`HTTPError: Please reduce your request rate - bucket_tasks_queued exceeds
rationed amount`, having sent enough files to push the ACCOUNT catalog to 363
tasks against a per-access-key ration of 150. The fix is not a retry loop. A
retry while the ration is exceeded collects more refusals and lengthens the
very queue it is waiting on.

⛔⛔ SO THE DEFAULT BEHAVIOUR OF THIS TOOL IS TO WAIT, AND EVERY UNCERTAINTY
RESOLVES TOWARDS WAITING. It uploads only when it has POSITIVELY READ a drained
queue. A catalog read that fails is NOT a drained queue.

## The three rules this tool is built around, all paid for already

1. ⛔ A COUNT THAT CANNOT BE TAKEN MUST NOT RETURN A PLAUSIBLE NUMBER.
   `account_tasks()` returns -1 on any failure and the caller treats -1 as
   "do not upload". Returning 0 there would read as "queue empty, go" and
   would hammer archive.org precisely when it is least reachable.

2. ⛔ THE CHILD'S RETURN CODE IS NOT THE RESULT, AND NEITHER IS THIS TOOL'S.
   The 2026-09-08 launcher reported exit 0 while its child had failed, because
   the wrapper's last statement was an `echo`. Completion here is decided ONLY
   by re-reading the LIVE item and comparing file counts.

3. ⚠ A KEEPALIVE-STYLE JOB MUST BE STOPPABLE WITHOUT A KILL.
   Touch the PAUSE file and the loop exits at the top of its next cycle:
       narration/logs/PAUSE_ia_upload_watch
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")
LOGS = DATA / "narration" / "logs"
PAUSE = LOGS / "PAUSE_ia_upload_watch"
TOOLS = Path(__file__).parent

# The per-access-key ration archive.org enforces. Not ours to change; it is
# the number the uploader itself warns against.
RATION = 150

# Expected final shape of the ylt item. `.w.json` is the whole point of the
# 2026-09-08 pass: before it the item held exactly ONE (a probe file), so
# ylt shipped with verse-level highlighting only.
EXPECT = {
    "ylt": {
        "identifier": "hexapla-audio-ylt-1898",
        "chapters": 1189,
        "suffixes": (".ogg", ".json", ".w.json"),
    },
}


def _ts():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def log(msg):
    line = f"[{_ts()}] {msg}"
    print(line, flush=True)


def account_tasks():
    """-> number of tasks in this access key's catalog, or -1 if UNREADABLE.

    ⛔⛔ NEVER RETURN 0 ON FAILURE. 0 means "the queue is empty, go ahead",
    which is the single most damaging wrong answer this function can give:
    it would launch an upload into a service that just refused us. A read that
    did not happen is -1, and -1 blocks the upload exactly like a full queue.
    """
    try:
        from internetarchive import get_session
        return len(list(get_session().get_my_catalog()))
    except Exception as e:                                     # noqa: BLE001
        log(f"  \u26a0 could not read the task catalog ({type(e).__name__}: {e})"
            f" -> treating as UNKNOWN, which blocks the upload")
        return -1


def item_counts(identifier, suffixes):
    """-> {suffix: count} from the LIVE item, or None if unreadable.

    ⚠ Order matters: '.w.json' also ends with '.json', so the longest suffix
    must win. Getting this wrong would report 1189 word sidecars that are not
    there — the exact claim this whole watcher exists to be able to make
    honestly.
    """
    try:
        import internetarchive as ia
        ordered = sorted(suffixes, key=len, reverse=True)
        out = {s: 0 for s in suffixes}
        for f in ia.get_item(identifier).get_files():
            for s in ordered:
                if f.name.endswith(s):
                    out[s] += 1
                    break
        return out
    except Exception as e:                                     # noqa: BLE001
        log(f"  \u26a0 could not read the item ({type(e).__name__}: {e})")
        return None


def is_complete(counts, spec):
    if counts is None:
        return False
    return all(counts.get(s, 0) >= spec["chapters"] for s in spec["suffixes"])


def report(counts, spec):
    if counts is None:
        return "   live item: UNREADABLE"
    return "   live item: " + " \u00b7 ".join(
        f"{s} {counts.get(s, 0)}/{spec['chapters']}"
        + ("" if counts.get(s, 0) >= spec["chapters"] else "  \u26a0")
        for s in spec["suffixes"])


def run_upload(set_key, launcher):
    """Run the upload once. -> child return code (never this function's own)."""
    if launcher and Path(launcher).exists():
        cmd = ["bash", str(launcher)]
    else:
        cmd = [sys.executable, str(TOOLS / "upload_narration.py"), set_key]
    log(f"  -> launching: {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=str(DATA))
    log(f"  -> CHILD_RC={p.returncode}")
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--resume-at", type=int, default=100,
                    help="only upload when the account catalog is BELOW this. "
                         "Default 100, deliberately under the 150 ration so a "
                         "run has headroom to finish rather than dying "
                         "mid-way and re-filling the queue.")
    ap.add_argument("--poll", type=int, default=600,
                    help="seconds between catalog checks (default 600). "
                         "\u26d4 Do not lower this into a hammer.")
    ap.add_argument("--max-cycles", type=int, default=288,
                    help="stop after this many polls (default 288 = 48h at "
                         "the default poll). A watcher with no bound is a leak.")
    ap.add_argument("--launcher", default=str(
        LOGS / "run_upload_ylt_2026-09-08.sh"))
    ap.add_argument("--check-only", action="store_true",
                    help="read and print state, upload nothing, exit")
    a = ap.parse_args()

    if a.set_key not in EXPECT:
        print(f"\u26d4 no completion spec for set '{a.set_key}' — refusing. "
              f"Known: {', '.join(sorted(EXPECT))}")
        return 2
    spec = EXPECT[a.set_key]

    if a.resume_at >= RATION:
        print(f"\u26d4 --resume-at {a.resume_at} is not below the ration "
              f"({RATION}). That guarantees a refusal. Refusing.")
        return 2

    log(f"watching {a.set_key} ({spec['identifier']})")
    log(f"  resume when account catalog < {a.resume_at} (ration {RATION}); "
        f"poll {a.poll}s; max {a.max_cycles} cycles")
    log(f"  PAUSE file: {PAUSE}")

    counts = item_counts(spec["identifier"], spec["suffixes"])
    print(report(counts, spec))
    n = account_tasks()
    log(f"   account catalog: {n if n >= 0 else 'UNREADABLE'} task(s)")

    if is_complete(counts, spec):
        log("\u2705 ALREADY COMPLETE on the live item — nothing to do.")
        return 0

    if a.check_only:
        log("--check-only: read state only, uploaded nothing.")
        return 0

    for cycle in range(1, a.max_cycles + 1):
        if PAUSE.exists():
            log(f"\u23f8 PAUSE file present ({PAUSE.name}) — stopping. "
                f"Delete it to allow a restart.")
            return 0

        n = account_tasks()
        if n < 0:
            log(f"cycle {cycle}: catalog UNREADABLE — WAITING "
                f"(an unknown queue is never a green light)")
        elif n >= a.resume_at:
            log(f"cycle {cycle}: account catalog {n} \u2265 {a.resume_at} "
                f"— WAITING for it to drain")
        else:
            log(f"cycle {cycle}: account catalog {n} < {a.resume_at} "
                f"— RESUMING the upload")
            rc = run_upload(a.set_key, a.launcher)

            # \u26d4 The child's rc is a hint, never the verdict. Re-read the item.
            counts = item_counts(spec["identifier"], spec["suffixes"])
            print(report(counts, spec))
            if is_complete(counts, spec):
                log("\u2705 COMPLETE — verified on the LIVE item, not on an "
                    "exit code.")
                log("\u25b6 NEXT: ylt_ship_chain.py --advance  (re-runs the "
                    "~80-min ASR pass; the build gate is delegated)")
                return 0
            log(f"   still incomplete after that run (child rc={rc}) — "
                f"back to waiting")

        time.sleep(a.poll)

    log(f"\u26a0 max cycles ({a.max_cycles}) reached WITHOUT completing. "
        f"This is not a failure of the upload — it is this watcher's bound. "
        f"Re-run it, or check whether the ration is stuck.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
