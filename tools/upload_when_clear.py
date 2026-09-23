# -*- coding: utf-8 -*-
"""Wait for archive.org's task queue to drain, then run an upload. Retry forever.

WHY (2026-08-07). The ru narration upload died twice with

    Please reduce your request rate. - accesskey_tasks_queued exceeds rationed amount

archive.org queues an `archive.php` task for EVERY uploaded file, and rations
how many an access key may have queued at once. A 1,192-chapter set (plus
sidecars) exceeds that on its own, so a big upload cannot simply be re-run —
it has to be fed in as the queue drains. The first run committed 877 files and
left 876 tasks queued; four minutes of observation showed ZERO draining with
one task running, and the oldest queued task was 90 minutes old.

`queue_derive=False` (set in upload_narration.py) removes the *derive* tasks,
which is a real reduction, but the per-file archive.php task is unavoidable.

So this babysits: poll the queue, run the upload when there is headroom, and if
it still gets rationed, go back to waiting. `checksum=True` in the uploader
makes every attempt resumable — files already present with a matching MD5 are
skipped, so nothing is re-sent once archive.org has committed it.

    python tools/upload_when_clear.py ru
    python tools/upload_when_clear.py ru --threshold 100 --poll 900

⚠ Run under system Python 3.13 — `internetarchive` is not in the venvs.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent

# Signatures of a dropped/refused socket rather than a refusal by archive.org.
TRANSIENT = ("ConnectionError", "ProtocolError", "ConnectionResetError",
             "ReadTimeout", "ConnectTimeout", "RemoteDisconnected",
             "IncompleteRead", "ChunkedEncodingError")

# ⚠ ARCHIVE.ORG RATIONS AT (AT LEAST) TWO LEVELS, WITH DIFFERENT WORDING.
# 2026-08-08: this watcher died on
#     "Please reduce your request rate. - bucket_tasks_queued exceeds
#      bucket_limit amount"
# because it only recognised the ACCESS-KEY form ("exceeds rationed amount").
# The bucket form fell through to "failed for a different reason" and the whole
# upload stopped, hours after the queue had drained — the one failure mode this
# script exists to survive. Match on the shared prefix too, so a third variant
# of the same refusal does not kill it again.
RATIONED = ("exceeds rationed amount", "exceeds bucket_limit",
            "bucket_tasks_queued", "accesskey_tasks_queued",
            "Please reduce your request rate")


def queued():
    from internetarchive import get_session
    try:
        return get_session().get_tasks_summary().get("queued", -1)
    except Exception as e:
        print(f"  [queue check failed: {e}]", flush=True)
        return -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--threshold", type=int, default=150,
                    help="start uploading when queued tasks fall below this")
    ap.add_argument("--poll", type=int, default=600, help="seconds between checks")
    ap.add_argument("--max-hours", type=float, default=48.0)
    ap.add_argument("--max-transient", type=int, default=8,
                    help="consecutive network failures tolerated before giving up")
    args = ap.parse_args()

    deadline = time.time() + args.max_hours * 3600
    attempt = 0
    transient = 0
    while time.time() < deadline:
        q = queued()
        print(f"[{time.strftime('%H:%M:%S')}] queued={q}", flush=True)
        if q < 0 or q >= args.threshold:
            time.sleep(args.poll)
            continue

        attempt += 1
        print(f"[{time.strftime('%H:%M:%S')}] queue clear ({q}) — upload attempt "
              f"{attempt}", flush=True)
        r = subprocess.run([sys.executable, "-u", str(HERE / "upload_narration.py"),
                            args.set],
                           cwd=str(HERE.parent), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        if "requests," in out and "0 failed" in out:
            print("\n=== UPLOAD COMPLETE ===", flush=True)
            for line in out.splitlines():
                if any(k in line for k in ("uploaded ", "title verified", "DONE ->",
                                           "live:", "want:", "METADATA")):
                    print(line, flush=True)
            return 0
        if any(k in out for k in RATIONED):
            print("  rationed again — back to waiting", flush=True)
            transient = 0  # archive.org answered us; the network is fine
            time.sleep(args.poll)
            continue
        # A dropped socket mid-transfer is archive.org's S3 endpoint hanging up,
        # not a reason to abandon a 1,192-chapter upload. checksum=True makes the
        # next attempt resume from what already landed, so this is safe to retry;
        # only give up after several consecutive network deaths.
        if any(k in out for k in TRANSIENT):
            transient += 1
            if transient > args.max_transient:
                print(f"\n=== GAVE UP: {transient} consecutive network failures ===",
                      flush=True)
                print(out[-2000:], flush=True)
                return 1
            print(f"  network error (transient {transient}/{args.max_transient})"
                  f" — retrying in 120s", flush=True)
            time.sleep(120)
            continue
        # Any other failure is not something to retry blindly in a loop.
        print("\n=== UPLOAD FAILED FOR A DIFFERENT REASON ===", flush=True)
        print(out[-2000:], flush=True)
        return 1

    print("\n=== GAVE UP: max-hours reached, queue never cleared ===", flush=True)
    return 2


if __name__ == "__main__":
    sys.exit(main())
