# -*- coding: utf-8 -*-
"""Deliver ONLY the files a narration set still owes archive.org, then submit
EXACTLY ONE derive.

## WHY THIS EXISTS (2026-08-24)

`upload_when_clear.py <set>` babysits the queue and then runs the WHOLE-SET
`upload_narration.py`. For a set that owes four files that is the wrong tool
twice over:

  * every invocation costs a full local MD5 pass over ~4 GB, and
  * the whole-set uploader finishes by submitting an item-wide `derive.php`,
    which rebuilds ~1159 mp3 + ~601 png and re-queues ~1000 `archive.php`
    tasks, head-of-line blocking the item for about a day.

When that drains, the keepalive fires again, uploads the whole set again, and
submits another derive. The block is not external misfortune -- it is the
predictable consequence of our own previous attempt. This script breaks the
loop: derive the owed list, send only those files, submit one derive, verify
against live state.

## USAGE

    python tools/deliver_outstanding.py wyc                 # DRY RUN (default)
    python tools/deliver_outstanding.py wyc --confirm
    python tools/deliver_outstanding.py wyc --confirm --wait-threshold 150

`--wait-threshold N` polls until the account's queued-task count is under N
before sending. Nothing sends while rationed, so this is not optional in
practice -- it just makes the wait explicit instead of a failed upload.

⚠ The queued number CAPS AT 1000. `get_tasks_summary()` returning 1000 means
"at least 1000, unknown"; below 1000 it is real. That is fine for a threshold
test (any cap value is above any sane threshold) but never quote it as progress
-- watch COMPLETED tasks on the item instead.

## DERIVE POLICY

Mirrors upload_narration.py, deliberately:

    audio REPLACED -> derive(remove_derived="*")   rebuilds stale .mp3
    audio ADDED    -> derive()                     plain
    no audio       -> NO DERIVE                    sidecar-only delivery is free

The item PAGE streams the derived .mp3, so replacing an .ogg without a
remove_derived derive leaves the public player serving the old audio under a
corrected title. That inversion has shipped twice. Do not "optimise" it away.

## HONESTY CONTRACT (CLAUDE.md)

An API failure, a missing MD5, or an unreadable local file exits 2. It never
returns a plausible-looking 0. The final "done" claim is gated on a re-read of
live state, never on the upload's own return value.
"""
import argparse
import hashlib
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RELEASES = os.path.join(os.path.dirname(REPO), "Hexapla-releases")

AUDIO_EXT = ".ogg"


def config_for(setname):
    sys.path.insert(0, HERE)
    import upload_narration as un
    cfg = getattr(un, "SETS", None) or getattr(un, "LANG_CONFIG", None)
    if not cfg or setname not in cfg:
        raise SystemExit("cannot resolve set %r from upload_narration.py" % setname)
    return un, cfg[setname]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def live_files(ident):
    """Live name -> (md5, size). Raises rather than returning a partial map."""
    import internetarchive as ia
    live = {}
    for f in ia.get_item(ident).get_files():
        live[f.name] = (getattr(f, "md5", None), int(getattr(f, "size", 0) or 0))
    if not live:
        raise RuntimeError("archive.org returned no files for %s" % ident)
    return live


def outstanding_for(setname):
    """[(local_path, remote_name, why, is_replacement)], derived not recalled."""
    un, meta = config_for(setname)
    ident = meta["identifier"]
    src = os.path.join(RELEASES, "narration", setname)
    if not os.path.isdir(src):
        raise SystemExit("no local set at %s" % src)
    live = live_files(ident)

    owed, unknown = [], []
    for dirpath, _dirs, files in os.walk(src):
        for name in files:
            if ".bak" in name:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, src).replace("\\", "/")
            remote = un.remote_name(rel, meta)
            if remote not in live:
                owed.append((path, remote, "not on item", False))
                continue
            lmd5, lsize = live[remote]
            size = os.path.getsize(path)
            if lsize != size:
                owed.append((path, remote, "size %d -> %d" % (lsize, size), True))
                continue
            if not lmd5:
                unknown.append(remote)
                continue
            if md5(path) != lmd5:
                owed.append((path, remote, "md5 differs", True))
    return ident, owed, unknown


def queued_now():
    from internetarchive import get_session
    return get_session().get_tasks_summary().get("queued", -1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--confirm", action="store_true",
                    help="actually upload; without it this is a dry run")
    ap.add_argument("--wait-threshold", type=int, default=0,
                    help="poll until queued tasks fall below N before sending")
    ap.add_argument("--poll", type=int, default=600)
    ap.add_argument("--max-hours", type=float, default=96.0)
    ap.add_argument("--derive", choices=("auto", "none", "plain", "full"),
                    default="auto")
    args = ap.parse_args()

    try:
        ident, owed, unknown = outstanding_for(args.set)
    except Exception as e:
        print("DERIVATION FAILED: %s: %s" % (type(e).__name__, e))
        return 2
    if unknown:
        print("UNVERIFIABLE: %d file(s) have no MD5 on the item -- refusing to "
              "act on a partial picture" % len(unknown))
        return 2

    print("item        : %s" % ident)
    print("OUTSTANDING : %d" % len(owed))
    for path, remote, why, _repl in owed:
        print("   %-24s %s" % (remote, why))
    if not owed:
        print("COMPLETE - nothing to deliver.")
        return 0

    audio = [o for o in owed if o[1].lower().endswith(AUDIO_EXT)]
    replaced = [o for o in audio if o[3]]
    if args.derive != "auto":
        plan = args.derive
    elif replaced:
        plan = "full"
    elif audio:
        plan = "plain"
    else:
        plan = "none"
    print("derive plan : %s   (%d audio owed, %d of them replacements)"
          % (plan, len(audio), len(replaced)))
    if plan == "full":
        print("   remove_derived=* rebuilds EVERY derivative on this item and "
              "will block it for roughly a day. That is the cost of replacing "
              "an .ogg whose .mp3 the public player serves.")

    if not args.confirm:
        print("\nDRY RUN - nothing sent. Re-run with --confirm.")
        return 1

    if args.wait_threshold:
        deadline = time.time() + args.max_hours * 3600
        while time.time() < deadline:
            q = queued_now()
            print("[%s] queued=%s (threshold %d)"
                  % (time.strftime("%H:%M:%S"), q, args.wait_threshold), flush=True)
            if 0 <= q < args.wait_threshold:
                break
            time.sleep(args.poll)
        else:
            print("GAVE UP: max-hours reached, queue never cleared")
            return 2

    from internetarchive import get_item, upload
    files = {remote: path for path, remote, _why, _r in owed}
    res = upload(ident, files=files, retries=6, retries_sleep=20,
                 verbose=True, checksum=True, queue_derive=False)
    bad = [r for r in res if getattr(r, "status_code", 200) not in (200, None)]
    print("\nuploaded %d/%d requests, %d failed"
          % (len(res) - len(bad), len(res), len(bad)))
    if bad:
        for r in bad[:10]:
            print("  FAILED:", getattr(r, "url", "?"), getattr(r, "status_code", "?"))
        return 1

    item = get_item(ident)
    if plan == "full":
        item.derive(remove_derived="*", reduced_priority=True)
        print("derive queued (remove_derived=*)")
    elif plan == "plain":
        item.derive(reduced_priority=True)
        print("derive queued (plain)")
    else:
        print("no derive queued: no audio was added or replaced")

    # Gate the claim on live state, not on the upload's return value.
    print("\nre-deriving outstanding from the live item...")
    time.sleep(20)
    try:
        _ident, still, unk = outstanding_for(args.set)
    except Exception as e:
        print("VERIFY FAILED: %s: %s" % (type(e).__name__, e))
        return 2
    if unk:
        print("VERIFY INCONCLUSIVE: %d file(s) still have no MD5" % len(unk))
        return 2
    if still:
        print("STILL OUTSTANDING: %d" % len(still))
        for path, remote, why, _r in still[:12]:
            print("   %-24s %s" % (remote, why))
        print("(archive.org can lag by a few minutes on a fresh write; re-run "
              "upload_outstanding.py before concluding this failed)")
        return 1
    print("DELIVERED - every local file is on the item with a matching MD5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
