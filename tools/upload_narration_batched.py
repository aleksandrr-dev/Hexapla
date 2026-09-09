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


def already_running():
    """-> the PID of another live copy of this tool, or None.

    ⛔⛔ TWO WRITERS ON ONE ITEM IS THE FAILURE THIS WHOLE TOOL EXISTS TO
    AVOID, AND THE PAUSE FILE DOES NOT PREVENT IT. Happened 2026-09-09: a
    running copy was asleep in its 600 s poll when the PAUSE file was placed;
    the PAUSE was then cleared and a second copy started BEFORE the first woke
    up, so the first never saw it. Both then uploaded into the same bucket,
    doubling the task rate and re-engaging the ration within two minutes.
    ⚠ The launcher's PAUSE check is not enough on its own: it tests a file,
    and the thing that matters is whether a PROCESS is alive.
    ▶ So: after placing the PAUSE file, WAIT for the process to exit (up to a
    full poll interval) before starting anything.
    """
    import os
    me = os.getpid()
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | "
             "Where-Object { $_.CommandLine -match "
             "'upload_narration_batched' -and $_.CommandLine -notmatch "
             "'CimInstance' } | Select-Object -ExpandProperty ProcessId"],
            capture_output=True, text=True, timeout=60)
        pids = [int(x) for x in out.stdout.split() if x.strip().isdigit()]
    except Exception:                                          # noqa: BLE001
        # ⚠ A check that cannot run is not a check that passed — but refusing
        # to start on an unreadable process table would make the tool
        # unrunnable on a machine that hides it. Say so loudly and continue.
        print("  ⚠ could not read the process table — CANNOT confirm this is "
              "the only copy. Check by hand before trusting a long run.")
        return None
    others = [x for x in pids if x != me]
    return others[0] if others else None


def _ts():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def log(msg):
    print(f"[{_ts()}] {msg}", flush=True)


def s3_ration(identifier):
    """-> (over_limit, detail dict) from S3's own check_limit, or (-1, {}).

    \u26d4\u26d4 THIS, NOT A QUEUE COUNT, IS WHAT DECIDES WHETHER AN UPLOAD IS
    ACCEPTED. The tool spent 2026-09-08/09 waiting for the catalog queue to
    fall below 100 while S3 was answering a different question entirely.
    Measured on this item, 2026-09-09:

        bucket_tasks_queued 264      bucket_ration 149
        bucket_limit        999      over_limit      1
        rationing_engaged     1      rationing_level 9999
        total_tasks_queued 10018     total_global_limit 11999

    \u26a0\u26a0 **THE RATION IS DYNAMIC AND THE LIMIT IS NOT.** The bucket is over
    its RATION of 149 while sitting far under its hard LIMIT of 999, because
    rationing engages when ARCHIVE.ORG AS A WHOLE is congested \u2014 10,018 tasks
    queued globally against a 11,999 limit. So the item is not broken and its
    tasks are not necessarily wedged: they are queued behind everyone else's.
    \u25b6 The gate can therefore open in TWO ways \u2014 our 264 tasks drain, OR the
    global congestion eases and `bucket_ration` rises back toward 999. Waiting
    on the queue count alone can only ever see the first.

    \u26d4 RETURNS -1 ON ANY FAILURE, NEVER 0. 0 is `over_limit: 0`, i.e. "go
    ahead", which is the single most damaging wrong answer here. A network
    error is NO INFORMATION and must BLOCK.
    """
    try:
        import internetarchive as ia
        s = ia.get_session()
        r = s.get("https://s3.us.archive.org",
                  params={"check_limit": 1, "bucket": identifier,
                          "accesskey": s.access_key}, timeout=30)
        if r.status_code != 200:
            log(f"  \u26a0 check_limit returned HTTP {r.status_code} -> "
                f"UNKNOWN, not clear. Blocking.")
            return -1, {}
        d = r.json()
        if "over_limit" not in d:
            log("  \u26a0 check_limit had no over_limit field -> UNKNOWN. "
                "Blocking.")
            return -1, {}
        return int(d["over_limit"]), d.get("detail", {})
    except Exception as e:                                     # noqa: BLE001
        log(f"  \u26a0 check_limit failed ({type(e).__name__}: {e}) -> "
            f"UNKNOWN, not clear. Blocking.")
        return -1, {}


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

    other = already_running()
    if other is not None:
        log(f"⛔⛔ ANOTHER COPY IS ALREADY RUNNING (pid {other}). Refusing to "
            f"start.")
        log("   Two writers on one item's task queue is how the ration gets "
            "blown while each believes it is being careful.")
        log(f"   ▶ Stop it with:  touch {PAUSE}")
        log("   ▶ Then WAIT for the process to actually exit — it is asleep "
            "in a poll and will not see the file until it wakes.")
        return 2

    log(f"set {a.set_key} -> {identifier}")
    log(f"  batch {a.batch} \u00b7 send when S3 accepts "
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

    over, detail = s3_ration(identifier)
    log(f"  S3 right now: over_limit={over} "
        f"queued={detail.get('bucket_tasks_queued')} "
        f"ration={detail.get('bucket_ration')} "
        f"limit={detail.get('bucket_limit')} "
        f"global={detail.get('total_tasks_queued')}/"
        f"{detail.get('total_global_limit')}")

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
    # Names S3 has accepted this run but which have not yet appeared on the
    # item. ⛔ NOT a success set — the completion claim below still reads the
    # LIVE item, never this.
    in_flight = set()
    waits = 0
    prev_q = None
    stalled = 0
    batch_no = 0

    while missing:
        if PAUSE.exists():
            log(f"\u23f9 PAUSE file present ({PAUSE.name}) — stopping cleanly. "
                f"{len(missing)} file(s) still missing.")
            return 1

        over, detail = s3_ration(identifier)
        q = detail.get("bucket_tasks_queued")
        ration = detail.get("bucket_ration")
        if over != 0:
            waits += 1
            if waits > a.max_cycles:
                log(f"\u26d4 hit the {a.max_cycles}-wait bound still over the "
                    f"ration. That is THIS LOOP'S limit, not an upload "
                    f"failure — re-run it.")
                return 1
            # ⚠ Report BOTH numbers. Either can move, and which one moved is
            # the difference between «our tasks are draining» and «archive.org
            # is less busy». A count alone cannot tell them apart.
            if prev_q is not None and (q, ration) == prev_q:
                stalled += 1
            else:
                stalled = 0
            prev_q = (q, ration)
            trend = (f"  \u26a0 NEITHER MOVED for {stalled} poll(s)"
                     if stalled else "")
            log(f"  wait {waits}/{a.max_cycles}: "
                + ("check_limit UNREADABLE — blocking"
                   if over < 0 else
                   f"queued {q} > ration {ration} "
                   f"(hard limit {detail.get('bucket_limit')}; "
                   f"global {detail.get('total_tasks_queued')}/"
                   f"{detail.get('total_global_limit')})")
                + trend)
            time.sleep(a.poll)
            continue
        log(f"  \u2705 S3 ACCEPTS: queued {q}, ration {ration} "
            f"(global {detail.get('total_tasks_queued')}/"
            f"{detail.get('total_global_limit')})")

        batch_no += 1
        chunk = missing[:a.batch]
        log(f"\u25b6 batch {batch_no}: S3 accepting (queued {q}), "
            f"sending {len(chunk)} file(s) ({len(missing)} still missing)")
        files = {n: p for n, p in chunk}
        accepted = []
        try:
            # checksum=True makes a re-run cheap: anything already present with
            # a matching MD5 is skipped rather than re-sent.
            # queue_derive=False suppresses derive.php per file; the single
            # derive is queued later by upload_narration.py. ⚠ It does NOT
            # suppress archive.php — see the module docstring.
            # ⛔⛔ ONE FILE PER CALL, ON PURPOSE.
            # A batch call raises on the FIRST refusal and takes the responses
            # for everything already sent with it. Those files ARE queued at
            # archive.org, so forgetting them means re-sending them next cycle
            # and queueing the same archive.php task TWICE — which is exactly
            # how the backlog this tool waits out was built. Measured
            # 2026-09-09: a batch died on 0/2.w.json having already had several
            # accepted, and the run reported «0 accepted by S3».
            for name, path_ in files.items():
                rs = upload(identifier, files={name: path_}, retries=4,
                            retries_sleep=20, verbose=True, checksum=True,
                            queue_derive=False)
                if rs and all(getattr(r, "status_code", None) in (200, 201)
                              for r in rs):
                    accepted.append(name)
            # ⛔⛔ A 200 HERE MEANS «S3 TOOK IT», NOT «IT IS ON THE ITEM».
            # Each accepted PUT queues an archive.php task, and the file only
            # appears once that task RUNS. Treating an accepted file as still
            # missing is what makes this tool re-send it next cycle — which
            # queues the task AGAIN. That is precisely how the 264-task backlog
            # this tool exists to wait out was built, so the fix is not
            # optional. Measured 2026-09-09: batch 1 was accepted in full and
            # confirmed 0/40 on the item.
            # (attribution happens per file, above)
        except Exception as e:                                 # noqa: BLE001
            # ⚠ A refusal is NOT a reason to retry harder. Fall back to waiting.
            log(f"  \u26a0 batch {batch_no} stopped after "
                f"{len(accepted)} accepted file(s) "
                f"({type(e).__name__}: {e})")
            log("    -> not retrying. The accepted files are QUEUED, "
                "not lost, and are NOT re-sent. Re-reading the item.")

        # ⛔ The upload's own result is not evidence. Re-read the live item.
        names = live_names(identifier)
        if names is None:
            log("  \u26a0 item unreadable after the batch — cannot confirm what "
                "landed. Waiting rather than sending more.")
            time.sleep(a.poll)
            continue
        landed = [n for n, _ in chunk if n in names]
        in_flight.update(n for n in accepted if n not in names)
        in_flight.difference_update(names)
        log(f"  batch {batch_no}: {len(landed)}/{len(chunk)} confirmed on the "
            f"live item; {len(accepted)} accepted by S3; "
            f"{len(in_flight)} in flight overall")
        sent += len(landed)
        # ⚠ «missing» now means NEITHER on the item NOR already accepted.
        # Anything in flight is left alone: it is queued, not lost.
        missing = [(n, p) for n, p in missing
                   if n not in names and n not in in_flight]
        if not missing:
            break
        if not landed:
            # ⚠ Nothing MATERIALISED. That is expected while the catalog is
            # backed up and is not a failure — but it does mean the next batch
            # adds to a queue that is not draining, so slow down rather than
            # press on.
            log("  \u26a0 nothing from that batch has materialised on the item "
                "yet (the catalog is behind). Waiting before sending more.")
            time.sleep(a.poll)

    if in_flight:
        log(f"\u26a0 {len(in_flight)} file(s) were ACCEPTED BY S3 but have not "
            f"appeared on the item yet. They are queued as archive.php tasks "
            f"behind the item's backlog.")
        log(f"   \u26d4 THIS IS NOT COMPLETION. Do not re-send them \u2014 that "
            f"queues the same task twice. Re-run this tool later; it re-reads "
            f"the live item and will report what actually materialised.")
        log(f"   {sent} file(s) confirmed on the live item this run.")
        return 1
    log(f"\u2705 every file landed. {sent} confirmed on the live item this run.")
    log(f"   \u25b6 NOW FINISH: python tools/upload_narration.py {a.set_key}")
    log("     (that writes the metadata and queues the ONE derive; this tool "
        "deliberately does neither)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
