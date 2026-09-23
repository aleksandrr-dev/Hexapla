#!/usr/bin/env python3
"""Scripture integrity guard — proves no operation silently altered the texts.

WHY THIS EXISTS
---------------
The 2026-07-27 GitHub history purge rewrote strings across every blob in the
repo's history. It came within one rule of rewriting SCRIPTURE: «Тимофей»
(Timothy) appears in the ru/cu Bible assets, and a bare-given-name redaction
rule would have edited the biblical text silently, in every historical commit,
with nothing to flag it. It was avoided only because the rules were scoped to
full contact strings.

A markup scan cannot catch that class. The de_luther case proved the general
point: audit_asset_markup.py found 20 dirty verses when the real number was
23,508 — a ~1,175x undercount — because 13,781 verses differed only by stripped
umlauts, with no markup to match. SILENT DAMAGE NEEDS A REFERENCE, NOT A PATTERN.
This file is that reference.

WHAT IT GUARDS
--------------
SHA-256 per file over:
  · app/src/main/assets/bibles/*.json     — scripture itself (36 files, ~154 MB)
  · versemap.json                          — verse-level cross-translation map
  · red_letters.json                       — words-of-Christ spans
  · interlinear_gr.json / interlinear_he.json — original-language word tagging
  · rubrics_vul.json                       — Vulgate speaker rubrics
  · strongs_lexicon.json, webster1828.json, xrefs.json — reference data
DELIBERATELY EXCLUDED: audio_index.json and audio_index_gen.json. Those are
regenerated every time narration is uploaded, so including them would make the
baseline diff noisy and train people to ignore it. They carry no scripture.

USAGE
-----
  python tools/check_asset_integrity.py                 # verify (exit 1 on drift)
  python tools/check_asset_integrity.py --update        # re-baseline, DELIBERATE
  python tools/check_asset_integrity.py --update --note "restored 24 psalm titles"

Run VERIFY:
  · before every release build,
  · and immediately after ANY history rewrite, filter-repo run, bulk
    find-and-replace, or converter run.
Run UPDATE only when you INTENDED to change an asset, and say why in --note.
An unexplained diff is a bug, not a baseline that needs refreshing.
"""
import argparse, hashlib, io, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "app" / "src" / "main" / "assets"
BASELINE = REPO / "tools" / "asset_baseline.json"

TOP_LEVEL = [
    "versemap.json", "red_letters.json", "interlinear_gr.json",
    "interlinear_he.json", "rubrics_vul.json", "strongs_lexicon.json",
    "webster1828.json", "xrefs.json",
]
# Regenerated per release; no scripture. Excluded on purpose — see docstring.
EXCLUDED = {"audio_index.json", "audio_index_gen.json"}


def targets():
    out = []
    for p in sorted((ASSETS / "bibles").glob("*.json")):
        out.append(p)
    for name in TOP_LEVEL:
        p = ASSETS / name
        if p.is_file():
            out.append(p)
    return out


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot():
    snap = {}
    for p in targets():
        rel = p.relative_to(ASSETS).as_posix()
        snap[rel] = {"sha256": digest(p), "bytes": p.stat().st_size}
    return snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true",
                    help="re-baseline; use ONLY for intended asset changes")
    ap.add_argument("--note", default="",
                    help="why the baseline changed (recorded in the file)")
    args = ap.parse_args()

    current = snapshot()

    if args.update or not BASELINE.exists():
        if not BASELINE.exists() and not args.update:
            print(f"no baseline at {BASELINE.relative_to(REPO)} — creating it")
        payload = {
            "_comment": "SHA-256 baseline for scripture and scripture-adjacent "
                        "assets. Verify with tools/check_asset_integrity.py. A "
                        "diff you did not intend is damage, not drift — "
                        "investigate before running --update.",
            "_note": args.note,
            "_files": len(current),
            "files": current,
        }
        io.open(BASELINE, "w", encoding="utf-8", newline="\n").write(
            json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
        total = sum(v["bytes"] for v in current.values())
        print(f"baseline written: {len(current)} files, {total/1e6:.1f} MB")
        if args.note:
            print(f"note: {args.note}")
        return 0

    base = json.loads(BASELINE.read_text(encoding="utf-8"))["files"]

    changed, missing, added = [], [], []
    for rel, meta in base.items():
        if rel not in current:
            missing.append(rel)
        elif current[rel]["sha256"] != meta["sha256"]:
            changed.append((rel, meta, current[rel]))
    for rel in current:
        if rel not in base:
            added.append(rel)

    if not (changed or missing or added):
        total = sum(v["bytes"] for v in current.values())
        print(f"OK — {len(current)} assets match the baseline "
              f"({total/1e6:.1f} MB verified byte-for-byte).")
        return 0

    print("!!! ASSET INTEGRITY FAILURE !!!\n")
    for rel, was, now in changed:
        delta = now["bytes"] - was["bytes"]
        print(f"  CHANGED  {rel}")
        print(f"           bytes {was['bytes']} -> {now['bytes']} ({delta:+d})")
        print(f"           sha   {was['sha256'][:16]}… -> {now['sha256'][:16]}…")
    for rel in missing:
        print(f"  MISSING  {rel}   <-- an asset was DELETED")
    for rel in added:
        print(f"  ADDED    {rel}   (new asset; --update if intended)")
    print("\nIf you did NOT intend these, do not re-baseline. A byte delta near "
          "zero with a changed hash is the dangerous case: same length, "
          "different content — exactly what a bad find-and-replace looks like.")
    print("Recover from asset-backups/ or git history, then re-verify.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
