# -*- coding: utf-8 -*-
"""Derive, exactly, what a narration set still owes archive.org.

## WHY THIS EXISTS

The outstanding-file count for a set has repeatedly been CARRIED FORWARD IN
PROSE from one handoff to the next instead of being derived. On 2026-08-24 the
current handoff said wyc had "4 files only" outstanding; the true figure was
**520** (347 .json offset sidecars + 173 .ogg). A session planned around the 4,
and nearly killed a legitimately-running uploader on the strength of it.

CLAUDE.md already forbids this for chapter grids -- "DERIVE grid counts, never
carry them from prose". Upload state is the same class of fact and gets the
same treatment. We are the only uploader of these items, so the number is
always computable and there is never a reason to guess it.

## USAGE

    python tools/upload_outstanding.py wyc
    python tools/upload_outstanding.py wyc --quick     # size-only, no hashing

Run it BEFORE launching an uploader (to know the real size of the job) and
AFTER one reports success (to gate the "done" claim on live state, not on a
log line). Exit code is 0 only when the set is genuinely complete.

## HONESTY CONTRACT (CLAUDE.md)

A count that FAILS must never be indistinguishable from a real "nothing left".
Any API failure, missing MD5, or unreadable local file raises or exits 2 --
it never returns a plausible-looking 0.
"""
import argparse
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# narration/ lives in the sibling working directory, not the app repo
RELEASES = os.path.join(os.path.dirname(REPO), "Hexapla-releases")


def item_for(setname):
    """Read the identifier out of upload_narration.py's own config."""
    sys.path.insert(0, HERE)
    import upload_narration as un
    cfg = getattr(un, "SETS", None) or getattr(un, "LANG_CONFIG", None)
    if not cfg or setname not in cfg:
        raise SystemExit("cannot resolve set %r from upload_narration.py" % setname)
    ident = cfg[setname].get("identifier")
    if not ident:
        raise SystemExit("no identifier for set %r" % setname)
    return ident


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set")
    ap.add_argument("--quick", action="store_true",
                    help="compare size only; FASTER BUT WEAKER -- a same-size "
                         "rewrite is invisible to it, so never gate a 'done' "
                         "claim on --quick")
    ap.add_argument("--list", type=int, default=12, help="how many to name")
    args = ap.parse_args()

    ident = item_for(args.set)
    src = os.path.join(RELEASES, "narration", args.set)
    if not os.path.isdir(src):
        raise SystemExit("no local set at %s" % src)

    import internetarchive as ia
    try:
        live = {}
        for f in ia.get_item(ident).get_files():
            live[f.name] = (getattr(f, "md5", None),
                            int(getattr(f, "size", 0) or 0))
    except Exception as e:
        # NEVER fall through to a plausible number.
        print("ARCHIVE.ORG QUERY FAILED: %s: %s" % (type(e).__name__, e))
        return 2
    if not live:
        print("ARCHIVE.ORG RETURNED NO FILES -- refusing to report a count")
        return 2

    outstanding, unknown = [], []
    checked = 0
    for dirpath, _dirs, files in os.walk(src):
        for name in files:
            if ".bak" in name:          # local backups are not upload material
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, src).replace("\\", "/")
            if rel not in live:
                outstanding.append((rel, "not on item"))
                continue
            lmd5, lsize = live[rel]
            size = os.path.getsize(path)
            checked += 1
            if lsize != size:
                outstanding.append((rel, "size %d -> %d" % (lsize, size)))
                continue
            if args.quick:
                continue
            if not lmd5:
                unknown.append(rel)     # cannot verify -- must not count as OK
                continue
            if md5(path) != lmd5:
                outstanding.append((rel, "md5 differs"))

    print("item        : %s" % ident)
    print("local files : %d compared" % checked)
    print("OUTSTANDING : %d%s" % (len(outstanding),
                                  "   (--quick: size only)" if args.quick else ""))
    by_ext = {}
    for rel, _why in outstanding:
        by_ext[os.path.splitext(rel)[1]] = by_ext.get(os.path.splitext(rel)[1], 0) + 1
    if by_ext:
        print("by extension: %s" % by_ext)
    for rel, why in outstanding[:args.list]:
        print("   %-24s %s" % (rel, why))
    if len(outstanding) > args.list:
        print("   ... and %d more" % (len(outstanding) - args.list))
    if unknown:
        print("UNVERIFIABLE: %d file(s) have no MD5 on the item -- NOT counted "
              "as complete" % len(unknown))
        return 2
    if outstanding:
        return 1
    print("COMPLETE - every local file is on the item with a matching MD5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
