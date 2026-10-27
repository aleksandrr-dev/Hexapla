"""Prove EVERY chapter of a set carries its library announcement (not a synthesized head).

    tools/.kokoro_venv/Scripts/python.exe tools/announce_splice_proof.py --set ylt
    ...                                                   --set ylt --against-backup   # control

WHY (owner, 2026-09-25): ylt shipped with 1,137 of 1,189 chapters still on their
SYNTHESIZED heads — Matthew 16 «chapter sixtee-», Judges 9 with no announcement
at all, Isaiah 40 «Raxac, Raxac, Hia» — although he had asked for every chapter
to be spliced before the upload. `apply_announcements --set ylt` had last run on
2026-08-24 when 52 chapters existed; the render went on to 09-07 and the re-run
the handoff called for never happened. Nothing enforced it, so this does:
build_audio_index_gen.py runs it for every set that has an announce library and
refuses to wire a set that fails.

⛔ THE ASR CANNOT DO THIS JOB. It transcribed the clipped «sixtee-» as «16»
(and a clean Matthew 16 identically), so `apply_announcements --verify` passes a
defective head. This check is structural: a spliced chapter's verse 1 starts at
exactly round(len(library header) + GAP_MS); a synthesized head ends wherever it
ends. ~1 % of unspliced chapters match within 1 ms by coincidence (13/1189 on
ylt's backups), so a pass here plus a 0-error splice log is the proof.

Control: --against-backup reads `<set>_pre_announce/` and must FAIL in bulk.
Exit 0 all spliced · 1 any not · 2 could not run.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--against-backup", action="store_true")
    a = ap.parse_args()
    try:
        import apply_announcements as aa
        aa._configure(a.set)
        comps = aa.load_components()
        bible = json.loads(aa.ASSET.read_text(encoding="utf-8"))
    except Exception as e:  # a check that cannot run did not pass
        print(f"COULD NOT RUN: {type(e).__name__}: {e}")
        return 2
    root = aa.BACKUP if a.against_backup else aa.NARR
    ok, bad = 0, []
    for bi in range(66):
        n = len(bible[bi]["chapters"])
        for ci in range(n):
            js = root / str(bi) / f"{ci}.json"
            if not (root / str(bi) / f"{ci}.ogg").exists() or not js.exists():
                continue
            hdr, err = aa.build_header(comps, bi, ci, n)
            if hdr is None:
                bad.append((bi, ci, f"no library header: {err}"))
                continue
            want = int(round(len(hdr) / aa.SR * 1000 + aa.GAP_MS))
            have = json.loads(js.read_text(encoding="utf-8"))["offsets"][0]
            if abs(have - want) <= 1:
                ok += 1
            else:
                bad.append((bi, ci, f"verse 1 at {have} ms, library head puts it at {want}"))
    print(f"{a.set} ({root.name}): {ok} spliced, {len(bad)} NOT")
    for b in bad[:15]:
        print("  ", b)
    if not ok and not bad:
        print("no chapters found - not a pass")
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
