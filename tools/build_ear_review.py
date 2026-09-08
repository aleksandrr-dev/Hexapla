# -*- coding: utf-8 -*-
"""Cut the verses that want an EAR out of the live audio, into one review file.

    python tools/build_ear_review.py --set ylt --out <dir>

0 model tokens, 0 GPU. Two sources, unioned:

  1. verses a repair run left `still failing after 3 draws` (from its tee'd log)
  2. verses `qa_discarded_draws.py` says the gate could not separate, so the
     kept take was chosen arbitrarily

⚠⚠ **IT CUTS FROM THE LIVE TREE, NOT FROM THE DRAWS.** The question an ear is
being asked is «is what will SHIP correct?», and that is `narration/<set>/b/c.ogg`
as it stands now. A clip taken from a draw or from `<set>_qa_fail_originals/`
answers a different question and would be worse than no clip, because it sounds
like an answer.

⚠ Verse n starts at `offsets[n-1]` and ends at `offsets[n]` — the sidecar holds
STARTS only, so the last verse runs to end of file. An off-by-one here clips the
wrong verse and the ear rules on the wrong audio; the printed index carries the
verse TEXT so a mismatch is audible immediately.

⛔ A verse absent from the output is not a verse that passed — it is a verse
neither source named. Silence is not a clean bill (see qa_discarded_draws).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(r"C:\Projects\Hexapla-releases")
ASSETS = HERE.parent / "app" / "src" / "main" / "assets" / "bibles"
GAP = 0.9          # seconds of silence between verses in the joined file


def still_failing(log):
    """-> {(b, c, v)} from a repair run's tee'd log."""
    out, ch = set(), None
    for line in Path(log).read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^=== (\d+)/(\d+)\b", line)
        if m:
            ch = (int(m.group(1)), int(m.group(2)))
        if ch and "still failing after 3 draws" in line:
            g = re.search(r"v\[([0-9, ]+)\]", line)
            if g:
                for v in g.group(1).split(","):
                    out.add((ch[0], ch[1], int(v.strip())))
    return out


def discarded(set_key):
    """-> {(b, c, v)} that qa_discarded_draws flags as an arbitrary choice."""
    r = subprocess.run(
        [sys.executable, str(HERE / "qa_discarded_draws.py"), "--set", set_key],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = set()
    for line in (r.stdout or "").splitlines():
        m = re.match(r"^\s+(\d+)/(\d+) v(\d+)\s*$", line)
        if m:
            out.add(tuple(int(x) for x in m.groups()))
    if not out:
        # ⛔ An empty parse and a genuinely clean set look identical. Refuse.
        print("⛔ parsed 0 verses out of qa_discarded_draws — treat as a "
              "BROKEN parse, not a clean set, and fix this before trusting "
              "the bundle.", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_key", default="ylt")
    ap.add_argument("--asset", default="en_ylt.json")
    ap.add_argument("--log", action="append", default=[],
                    help="repair log(s) to read `still failing` out of")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    nar = DATA / "narration" / a.set_key
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    books = json.loads((ASSETS / a.asset).read_text(encoding="utf-8"))

    want = {}
    for lg in a.log:
        for k in still_failing(lg):
            want.setdefault(k, set()).add("gate-failed after 3 draws")
    for k in discarded(a.set_key):
        want.setdefault(k, set()).add("arbitrary choice between draws")
    if not want:
        print("⛔ no verses named by either source — that is a broken run, "
              "not a clean set.")
        return 2

    rows, clips = [], []
    for (b, c, v) in sorted(want):
        ogg = nar / str(b) / f"{c}.ogg"
        sc = nar / str(b) / f"{c}.json"
        if not ogg.exists() or not sc.exists():
            rows.append((b, c, v, None, None, "⛔ NO AUDIO ON DISK", want[(b, c, v)]))
            continue
        offs = json.loads(sc.read_text(encoding="utf-8"))["offsets"]
        if v > len(offs):
            rows.append((b, c, v, None, None,
                         f"⛔ verse {v} beyond {len(offs)} offsets", want[(b, c, v)]))
            continue
        start = offs[v - 1] / 1000.0
        end = offs[v] / 1000.0 if v < len(offs) else None
        try:
            bk = books[b]
            text = bk["chapters"][c][v - 1]
            name = bk.get("name") or bk.get("n") or f"book{b}"
        except (IndexError, KeyError, TypeError):
            text, name = "", f"book{b}"
        clip = out / f"{b:02d}_{c:03d}_v{v:03d}.mp3"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(ogg),
               "-ss", f"{start:.3f}"]
        if end is not None:
            cmd += ["-to", f"{end:.3f}"]
        cmd += ["-c:a", "libmp3lame", "-q:a", "4", str(clip)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not clip.exists():
            rows.append((b, c, v, name, text, "⛔ ffmpeg failed", want[(b, c, v)]))
            continue
        clips.append(clip)
        span = (f"{start:.1f}-{end:.1f}s" if end is not None
                else f"{start:.1f}s-EOF (last verse)")
        rows.append((b, c, v, name, text, span, want[(b, c, v)]))

    joined = None
    if clips:
        sil = out / "_gap.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"anullsrc=r=44100:cl=mono", "-t", str(GAP),
                        "-c:a", "libmp3lame", "-q:a", "4", str(sil)],
                       capture_output=True)
        lst = out / "_concat.txt"
        parts = []
        for c_ in clips:
            parts.append(f"file '{c_.as_posix()}'")
            parts.append(f"file '{sil.as_posix()}'")
        lst.write_text("\n".join(parts) + "\n", encoding="utf-8")
        joined = out / f"{a.set_key}_ear_review.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame",
                        "-q:a", "4", str(joined)], capture_output=True)

    md = [f"# {a.set_key} — verses wanting an ear",
          "",
          f"{len(rows)} verse(s), cut from the LIVE tree (`narration/{a.set_key}/`)"
          " — this is what will ship.",
          "",
          "⛔ A verse not listed here is one neither source named, NOT one that"
          " passed.",
          ""]
    for i, (b, c, v, name, text, span, why) in enumerate(rows, 1):
        md.append(f"## {i}. {name} {c + 1}:{v}   `{b}/{c} v{v}`")
        md.append(f"- why: {'; '.join(sorted(why))}")
        md.append(f"- clip: `{b:02d}_{c:03d}_v{v:03d}.mp3`  ({span})")
        if text:
            md.append(f"- text: {text}")
        md.append("")
    (out / "INDEX.md").write_text("\n".join(md), encoding="utf-8")

    print(f"{len(rows)} verse(s) written to {out}")
    for (b, c, v, name, _t, span, why) in rows:
        print(f"  {name} {c + 1}:{v:<4} [{b}/{c} v{v}]  {span}   "
              f"{'; '.join(sorted(why))}")
    if joined:
        print(f"\n▶ joined review file: {joined}")
    print(f"▶ index: {out / 'INDEX.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
