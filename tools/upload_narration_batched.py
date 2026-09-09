# -*- coding: utf-8 -*-
"""Upload a narration set's MISSING files to archive.org in ration-sized batches.

    python tools/upload_narration_batched.py --set ylt                  # DRY RUN (default)
    python tools/upload_narration_batched.py --set ylt --commit         # actually upload
    python tools/upload_narration_batched.py --set ylt --check-only     # read state, exit

⚠⚠ **THIS TOOL UPLOADS FILES AND NOTHING ELSE.** It does not write metadata and
it does not queue the derive. When it reports COMPLETE, finish with the audited
path:

    python tools/upload_narration.py <set>

which finds every file already present (checksum=True skips them), writes the
metadata, and queues ONE derive. That step owns the partial/complete title
logic, and re-implementing it here is how a finished set stays publicly titled
"(pågår / in progress)" — see the long note in upload_narration.build().

## WHY THIS EXISTS — MEASURED 2026-09-08/09

`upload_narration.py` builds ONE `upload()` call over `oggs + jsons`. For ylt
that is ~3,500 files, ~1,188 of them genuinely new (.w.json). The 2026-09-08
run died 35 minutes in:

    HTTPError: error uploading 65/4.ogg to hexapla-audio-ylt-1898,
    Please reduce your request rate. - bucket_tasks_queued exceeds rationed amount

⚠⚠ **`queue_derive=False` DOES NOT MAKE A RUN RATION-SAFE.** That flag
suppresses `derive.php` only. Every uploaded file still creates an
**`archive.php`** task on the item, and THOSE are what the bucket rations.
Measured on the live item that day: 264 green `archive.php` queued beside a
single blue `derive.php`. So the ration is consumed per FILE, and the only
protection is to send fewer files per run and re-read the queue between runs.

⛔⛔ **BATCHING IS NOT A CURE FOR A STUCK QUEUE.** On 2026-09-08 the item's
queue sat at exactly 264 for thirteen hours without moving. This tool will wait
in that situation, correctly and forever, so it PRINTS THE QUEUE TREND on every
poll and says plainly when the queue has not moved. A stall is an observation to
act on, not something to sit through silently.

## The rules this tool is built around, all paid for already

1. ⛔ **DRY RUN IS THE DEFAULT.** `--commit` is required to send a byte. A bulk
   mutation with no preview is the shape behind most damage in this project.
2. ⛔ **A COUNT THAT CANNOT BE TAKEN RETURNS -1, NEVER A PLAUSIBLE NUMBER.**
   `queued_tasks()` returns -1 on any failure and -1 blocks the upload exactly
   like a full queue. Returning 0 there would read as "queue empty, go" and
   would hammer archive.org precisely when it is least reachable.
3. ⛔ **COMPLETION IS DECIDED BY RE-READING THE LIVE ITEM, NEVER BY A RETURN
   CODE.** `upload()` returning 200s is not evidence a file landed. After every
   batch this re-reads the item's file list and counts how many of THAT batch's
   names are actually present.
4. ⚠ **STOPPABLE WITHOUT A KILL.** Touch `narration/logs/PAUSE_upload_batched`
   and the loop exits at the top of its next batch.
5. ⚠ **THE TEE'D LOG IS THE AUTHORITY**, not this process's exit code. Run it as
       python tools/upload_narration_batched.py --set ylt --commit \
           > narration/logs/upload_batched_ylt_$(date +%F).log 2>&1
   and read the log.
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from upload_narration import SETS, NARRATION, remote_name  # noqa: E402

DATA = Path(r"C:\Projects\Hexapla-releases")
LOGS = DATA / "narration" / "logs"
PAUSE = LOGS / "PAUSE_upload_batched"

# The ration archive.org enforces on queued tasks. Not ours to change; it is
# the number upload_narration.py itself warns against.
RATION = 150

# Suffixes that belong on the item. ⚠ ORDER MATTERS NOWHERE HERE because names
# are compared exactly, unlike ia_upload_watch.item_counts() which must sort
# longest-first so '.w.json' is not eaten by '.json'.
WANTED = (".ogg", ".json", ".w.json")

# Diagnostics that must never be published. Mirrors upload_narration.py: these
# are narrate.py's per-chapter QA records, for this machine only.
SKIP = (".eos.json", ".qa.json")


def _ts():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def log(msg):
    print(f"[{_ts()}] {msg}", flush=True)


def queued_tasks(identifier):
    """-> count of ACTIVE tasks on this item, or -1 if UNREADABLE.

    ⛔⛔ NEVER RETURN 0 ON FAILURE. 0 means "the queue is empty, go ahead",
    which is the single most damaging wrong answer this function can give.

    ⚠ `get_tasks()` returns HISTORY as well as the live queue. A finished task
    has `color = None`; green/blue/red are the active states. Counting the raw
    length would have read 359 where the queue held 265 on 2026-09-08, and
    would then have waited on a number that can never fall.

    ⛔⛔ **A BAD IDENTIFIER DOES NOT RAISE — IT RETURNS AN EMPTY TASK SET.**
    Caught by this tool's own control on 2026-09-09: `queued_tasks(
    '///bad identifier///')` returned 0, i.e. "queue empty, go ahead", which is
    precisely the answer rule 2 exists to forbid. So the item is verified to
    EXIST first, and a non-existent or unverifiable item is -1, not 0.
    """
    try:
        import internetarchive as ia
        if not ia.get_item(identifier).exists:
            log(f"  ⚠ item '{identifier}' does not exist -> queue is "
                f"UNKNOWN, not empty. Blocking.")
            return -1
        tasks = ia.get_session().get_tasks(identifier=identifier)
        return sum(1 for t in tasks if getattr(t, "color", None))
    except Exception as e:                                     # noqa: BLE001
        log(f"  \u26a0 could not read the task queue ({type(e).__name__}: {e})"
            f" -> treating as UNKNOWN, which BLOCKS the upload")
        return -1


def live_names(identifier):
    """-> set of file names on the LIVE item, or None if unreadable.

    None is distinct from an empty set on purpose: an unreadable item must not
    look like an empty one, which would make every local file 'missing' and
    queue a full re-upload.

    ⛔⛔ **A NON-EXISTENT ITEM RETURNS AN EMPTY FILE LIST RATHER THAN RAISING.**
    Caught by this tool's own control on 2026-09-09, which read a made-up
    identifier and got back a clean empty set — one typo in `--set` away from
    declaring all 3,567 files missing and re-uploading the entire corpus into
    the teeth of the ration. `.exists` is therefore checked explicitly; the
    try/except alone was NOT enough.
    """
    try:
        import internetarchive as ia
        item = ia.get_item(identifier)
        if not item.exists:
            log(f"  ⚠ item '{identifier}' does not exist -> UNREADABLE, "
                f"not empty.")
            return None
        return {f.name for f in item.get_files()}
    except Exception as e:                                     # noqa: BLE001
        log(f"  \u26a0 could not read the item ({type(e).__name__}: {e})")
        return None


def local_files(set_key):
    """-> [(remote_name, local_path)] for every file that BELONGS on the item."""
    meta_src = SETS[set_key]
    src = NARRATION / set_key
    if not src.is_dir():
        sys.exit(f"\u26d4 no narration directory at {src}")
    out = []
    for f in sorted(src.rglob("*")):
        if not f.is_file() or f.name.endswith(SKIP):
            continue
        if not f.name.endswith(WANTED):
            continue
        out.append((remote_name(f.relative_to(src), meta_src), str(f)))
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Upload a narration set's missing files in ration-sized "
                    "batches. DRY RUN unless --commit is given.")
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--batch", type=int, default=40,
                    help="files per upload call (default 40). Each file makes "
                         "one archive.php task, so this is the number of tasks "
                         "a batch adds to the bucket.")
    ap.add_argument("--resume-at", type=int, default=100,
                    help="only send a batch when the item's queue is BELOW "
                         "this (default 100). Must be under the %d ration, "
                         "and --batch + --resume-at must also stay under it, "
                         "or the batch itself guarantees a refusal." % RATION)
    ap.add_argument("--poll", type=int, default=600,
                    help="seconds between queue checks while waiting "
                         "(default 600). \u26d4 Do not lower this into a hammer.")
    ap.add_argument("--max-cycles", type=int, default=288,
                    help="stop after this many waiting polls (default 288 = "
                         "48h at the default poll). A loop with no bound is a leak.")
    ap.add_argument("--commit", action="store_true",
                    help="actually upload. WITHOUT THIS THE TOOL ONLY REPORTS.")
    ap.add_argument("--check-only", action="store_true",
                    help="print live state and the batch plan, then exit")
    a = ap.parse_args()

    if a.set_key not in SETS:
        print(f"\u26d4 unknown set '{a.set_key}'. Known: {', '.join(sorted(SETS))}")
        return 2
    identifier = SETS[a.set_key]["identifier"]

    # ⚠ Refuse a configuration that cannot succeed, rather than discovering it
    # as a refusal from archive.org half way through a batch.
    if a.resume_at >= RATION:
        print(f"\u26d4 --resume-at {a.resume_at} is not below the ration "
              f"({RATION}). That guarantees a refusal. Refusing.")
        return 2
    if a.resume_at + a.batch > RATION:
        print(f"\u26d4 --resume-at {a.resume_at} + --batch {a.batch} = "
              f"{a.resume_at + a.batch} exceeds the ration ({RATION}). A batch "
              f"started at the threshold would blow it. Lower one of them.")
        return 2

    log(f"set {a.set_key} -> {identifier}")
    log(f"  batch {a.batch} \u00b7 send when queue < {a.resume_at} "
        f"\u00b7 ration {RATION} \u00b7 poll {a.poll}s \u00b7 max {a.max_cycles} waits")
    log(f"  PAUSE file: {PAUSE}")
    if not a.commit:
        log("  \u26a0 DRY RUN — nothing will be uploaded. Pass --commit to send.")

    local = local_files(a.set_key)
    log(f"  local files that belong on the item: {len(local)}")

    names = live_names(identifier)
    if names is None:
        log("\u26d4 the item is unreadable — cannot compute what is missing. "
            "Refusing (an unreadable item is not an empty one).")
        return 2

    missing = [(n, p) for n, p in local if n not in names]
    by_suffix = {}
    for n, _ in missing:
        for s in sorted(WANTED, key=len, reverse=True):
            if n.endswith(s):
                by_suffix[s] = by_suffix.get(s, 0) + 1
                break
    log(f"  on the item: {len(names)} files")
    log(f"  MISSING: {len(missing)}"
        + (" \u00b7 " + " \u00b7 ".join(f"{s} {c}" for s, c in sorted(by_suffix.items()))
           if by_suffix else ""))

    if not missing:
        log("\u2705 nothing missing — every local file is already on the item.")
        log("   \u25b6 finish with:  python tools/upload_narration.py "
            f"{a.set_key}   (metadata + the single derive)")
        return 0

    n_batches = (len(missing) + a.batch - 1) // a.batch
    log(f"  plan: {n_batches} batch(es) of up to {a.batch}")

    q = queued_tasks(identifier)
    log(f"  item queue right now: {'UNREADABLE' if q < 0 else q}")

    if a.check_only or not a.commit:
        log("   first 5 files that would go in batch 1:")
        for n, _ in missing[:5]:
            log(f"     {n}")
        log("--check-only / dry run: read state only, uploaded nothing."
            if a.check_only else
            "DRY RUN: uploaded nothing. Re-run with --commit to send.")
        return 0

    from internetarchive import upload

    sent = 0
    waits = 0
    prev_q = None
    stalled = 0
    batch_no = 0

    while missing:
        if PAUSE.exists():
            log(f"\u23f9 PAUSE file present ({PAUSE.name}) — stopping cleanly. "
                f"{len(missing)} file(s) still missing.")
            return 1

        q = queued_tasks(identifier)
        if q < 0 or q >= a.resume_at:
            waits += 1
            if waits > a.max_cycles:
                log(f"\u26d4 hit the {a.max_cycles}-wait bound with the queue "
                    f"still at {'UNREADABLE' if q < 0 else q}. That is THIS "
                    f"LOOP'S limit, not an upload failure — re-run it.")
                return 1
            # ⚠ Say plainly when the queue is not moving. A silent wait on a
            # stuck queue is how thirteen hours went by on 2026-09-08.
            if prev_q is not None and q == prev_q and q >= 0:
                stalled += 1
            else:
                stalled = 0
            prev_q = q
            trend = ""
            if stalled:
                trend = (f"  \u26a0 UNCHANGED for {stalled} poll(s) "
                         f"\u2014 the queue may be stuck, not draining")
            log(f"  wait {waits}/{a.max_cycles}: queue "
                f"{'UNREADABLE' if q < 0 else q} \u2265 {a.resume_at}{trend}")
            time.sleep(a.poll)
            continue

        batch_no += 1
        chunk = missing[:a.batch]
        log(f"\u25b6 batch {batch_no}: queue {q} < {a.resume_at}, "
            f"sending {len(chunk)} file(s) ({len(missing)} still missing)")
        files = {n: p for n, p in chunk}
        try:
            # checksum=True makes a re-run cheap: anything already present with
            # a matching MD5 is skipped rather than re-sent.
            # queue_derive=False suppresses derive.php per file; the single
            # derive is queued later by upload_narration.py. ⚠ It does NOT
            # suppress archive.php — see the module docstring.
            upload(identifier, files=files, retries=4, retries_sleep=20,
                   verbose=True, checksum=True, queue_derive=False)
        except Exception as e:                                 # noqa: BLE001
            # ⚠ A refusal is NOT a reason to retry harder. Fall back to waiting.
            log(f"  \u26a0 batch {batch_no} raised "
                f"({type(e).__name__}: {e})")
            log("    -> not retrying; re-reading the item to see what landed, "
                "then back to waiting.")

        # ⛔ The upload's own result is not evidence. Re-read the live item.
        names = live_names(identifier)
        if names is None:
            log("  \u26a0 item unreadable after the batch — cannot confirm what "
                "landed. Waiting rather than sending more.")
            time.sleep(a.poll)
            continue
        landed = [n for n, _ in chunk if n in names]
        log(f"  batch {batch_no}: {len(landed)}/{len(chunk)} confirmed on the "
            f"live item")
        sent += len(landed)
        missing = [(n, p) for n, p in missing if n not in names]
        if not landed:
            # Nothing landed: sending another batch now would just collect more
            # refusals and lengthen the queue being waited on.
            log("  \u26a0 nothing from that batch landed — waiting before "
                "trying again.")
            time.sleep(a.poll)

    log(f"\u2705 every file landed. {sent} confirmed on the live item this run.")
    log(f"   \u25b6 NOW FINISH: python tools/upload_narration.py {a.set_key}")
    log("     (that writes the metadata and queues the ONE derive; this tool "
        "deliberately does neither)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
