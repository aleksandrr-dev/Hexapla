# -*- coding: utf-8 -*-
"""Repair a rendered chapter BY THE VERSE: re-synthesise only the condemned
verses, gate each new take, splice it into the existing chapter, re-align.

    # plan only (DEFAULT — nothing is written)
    tools\\.chatterbox_venv\\Scripts\\python.exe tools\\repair_verses.py --set ylt --queue _work\\ylt_rerender.txt
    # do it
    ... --set ylt --queue _work\\ylt_rerender.txt --apply [--limit 3]
    ... --set kxii --book 9 --chapter 8 --verses 3,7 --apply

## Why this and not `narrate.py --force`

`--force` re-renders the WHOLE chapter: ~9 min of GPU, and every untouched
verse is a fresh draw at the same ~0.5 %/verse defect rate, so ~13 % of
re-rendered chapters come back with a NEW defect somewhere and need another
16-hour sweep to find it. Re-synthesising one verse costs ~1 min, the new take
is judged by the same screens that condemned the old one BEFORE it is spliced
in, and the other verses are not touched. ylt: 169 verses ≈ 3 h instead of
152 chapters ≈ 22 h. This is `repair_abrupt_verses.py` (ru, 2026-08-05, 1,077
verses across 801 chapters) generalised to every set.

⚠ ORIGINALS ARE NEVER OVERWRITTEN IN PLACE. Every chapter's ogg/json/w.json/
eos.json/qa.json is copied to `narration/<dir>_qa_fail_originals/` before its
first splice, and every run reads its SOURCE from that backup — so a second
pass re-splices the pristine original rather than stacking a second Opus
generation, and the before/after audio exists for an ear (the 7 repairs of
2026-09-02 have no before-audio because this step was skipped).

⚠ THE CHAPTER IS RE-ENCODED ONCE, AT 48 kbps (owner's call 2026-08-05). Decode
through ffmpeg at 48 kHz — do not trust soundfile's reported rate on Opus (it
reports the ORIGINAL input rate; 24 k and 48 k chapters coexist).

⚠ OFFSETS MOVE. The new verse is a different length; the sidecar is rewritten
with shifted offsets and `edge_pad_ms` preserved, and `align_words.py --set
<KEY> --book B --chapter C --force` is run for the chapter so `.w.json` never
describes audio that no longer exists. The set KEY is not the directory name
(`kxii` for sv, `syn` for ru, `csl` for cu, `gen1599` for gnv).

⚠ THE HEADER (part 0) IS NEVER TOUCHED HERE. A defective announcement goes
through `apply_announcements.py --set …`, which has the verified component
library. `v0` in a queue is refused.

⚠ ONE GPU. Refuses to `--apply` while another `narrate.py` / `repair_verses.py`
process is running, unless `--allow-gpu-contention` (owner's decision).

⚠ ⚠ "IT WAS RE-ENCODED" IS NOT EVIDENCE. Every result is decoded back and
length-checked before it replaces anything; every new verse's gate verdict,
attempts and ASR tail are written to `<chapter>.qa.json` under "repairs"; the
alignment's `verses ok N` line is REQUIRED and its absence is a reported
failure. Re-run the screen that condemned the verse afterwards regardless.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import numpy as np
import soundfile as sf

import narrate
from align_words import SETS

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
SR = 48000
GAP_MS = 600
BITRATE = "48k"
NO_WINDOW = getattr(narrate, "_NO_WINDOW", 0)

Q_CMD = re.compile(r"--book\s+(\d+)\s+--chapter\s+(\d+).*?#\s*v([\d,]+)")
Q_TRIPLE = re.compile(r"^\s*(\d+)[\s/]+(\d+)\s+v?([\d,]+)\s*$")


def read_queue(path):
    """-> {(book, chapter): sorted verse list}. Accepts qa_rerender_queue.py's
    command lines (`... --book B --chapter C --force    # v3,7`) and plain
    `B C v3,7` / `B/C 3,7` lines."""
    out = {}
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = Q_CMD.search(ln) or Q_TRIPLE.match(ln)
        if not m:
            continue
        b, c = int(m.group(1)), int(m.group(2))
        vs = sorted({int(x) for x in m.group(3).split(",") if x})
        out.setdefault((b, c), set()).update(vs)
    return {k: sorted(v) for k, v in out.items()}


def speech_rms(a, sr):
    """RMS of the ACTIVE part only (apply_announcements.speech_rms). The
    chapter was loudnormed as a whole; the new verse must sit at the level of
    the SPEECH it replaces, not be normalised on its own."""
    win = max(1, sr // 50)
    env = np.array([float(np.sqrt((a[i:i + win] ** 2).mean()))
                    for i in range(0, max(1, len(a) - win), win)])
    if not len(env):
        return float(np.sqrt((a ** 2).mean()))
    active = env[env > 0.15 * env.max()]
    return float(np.sqrt((active ** 2).mean())) if len(active) else float(env.mean())


def _own_process_tree():
    """-> {pid} of this process and every ANCESTOR of it.

    ⚠⚠ EXCLUDING ONLY os.getpid() IS NOT ENOUGH — THE TOOL REFUSES ITSELF.
    Measured 2026-09-04: run from a shell, `repair_verses.py --set ylt --book 0
    --chapter 8 --verses 26 --apply` reported «another render/repair holds the
    GPU» and listed FOUR processes, every one of them its own: three ancestor
    bash.exe wrappers whose command line QUOTES the command being run, plus a
    python whose pid was not getpid(). The card was idle. Nothing was repaired.
    ▶ A guard that fires on its own invocation is indistinguishable from a real
    refusal, and it fails CLOSED — so the work silently does not happen and the
    log says something reassuringly sensible. Exclude the whole ancestor chain.
    """
    own = {os.getpid()}
    if os.name != "nt":
        return own
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | ForEach-Object "
         "{ \"$($_.ProcessId) $($_.ParentProcessId)\" }"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW)
    parent = {}
    for line in (r.stdout or "").splitlines():
        bits = line.split()
        if len(bits) == 2 and bits[0].isdigit() and bits[1].isdigit():
            parent[int(bits[0])] = int(bits[1])
    pid, hops = os.getpid(), 0
    while pid in parent and hops < 40:        # bounded: never trust a pid graph
        pid = parent[pid]
        if pid in own:
            break
        own.add(pid)
        hops += 1
    return own


def gpu_busy():
    if os.name != "nt":
        return []
    own = _own_process_tree()
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "
         "'narrate\\.py|repair_verses\\.py' } | ForEach-Object "
         "{ \"$($_.ProcessId) $($_.CommandLine)\" }"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW)
    out = []
    for l in (r.stdout or "").splitlines():
        bits = l.split()
        if not bits or not bits[0].isdigit():
            continue
        if int(bits[0]) in own:
            continue                          # self, or a shell that launched us
        if "python" in l.lower():
            out.append(l)
    return out


def decode(ogg, dst):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ogg), "-ar", str(SR),
                        "-ac", "1", str(dst)], capture_output=True, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise RuntimeError("decode failed: " + r.stderr.decode(errors="replace")[-200:])
    a, sr = sf.read(str(dst), dtype="float32")
    return a.mean(1) if a.ndim > 1 else a


def resample(a, src, dst):
    if src == dst:
        return a.astype("float32")
    from math import gcd
    from scipy.signal import resample_poly
    g = gcd(int(src), int(dst))
    return resample_poly(a, int(dst) // g, int(src) // g).astype("float32")


def spoken_verses(lang, books, b, c):
    cfg = narrate.LANG_CONFIG[lang]
    out = []
    for v in books[b]["chapters"][c]:
        if not v:
            out.append("")
            continue
        if cfg["strip_notes"]:
            v = narrate.strip_kjv_notes(v)
        if cfg["normalizer"]:
            v = narrate.normalize_text(v, cfg["normalizer"])
        out.append(v)
    return out


def align(set_key, b, c):
    """Re-align one chapter. -> (ok, message). `verses ok N` is REQUIRED."""
    r = subprocess.run([sys.executable, str(HERE / "align_words.py"), "--set", set_key,
                        "--book", str(b), "--chapter", str(c), "--force"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=NO_WINDOW, timeout=1800)
    m = re.search(r"verses ok (\d+) null (\d+)", r.stdout or "")
    if r.returncode != 0 or not m:
        return False, ("align_words exit %d, no 'verses ok' line: %s"
                       % (r.returncode, ((r.stderr or "") + (r.stdout or ""))[-300:]))
    return int(m.group(1)) > 0, f"verses ok {m.group(1)} null {m.group(2)}"


def repair_chapter(set_key, lang, books, b, c, targets, apply, tmp_root):
    scfg = SETS[set_key]
    live = NARRATION / scfg["dir"] / str(b)
    backup = NARRATION / f"{scfg['dir']}_qa_fail_originals" / str(b)
    ogg, side = live / f"{c}.ogg", live / f"{c}.json"
    if not ogg.exists() or not side.exists():
        return False, "no ogg/json on disk"
    if 0 in targets:
        return False, "v0 is the header: use apply_announcements.py, not this"

    # Back up once; ALWAYS read the source from the backup.
    src_ogg, src_side = backup / f"{c}.ogg", backup / f"{c}.json"
    if apply:
        backup.mkdir(parents=True, exist_ok=True)
        for ext in ("ogg", "json", "w.json", "eos.json", "qa.json"):
            f = live / f"{c}.{ext}"
            if f.exists() and not (backup / f.name).exists():
                shutil.copy2(f, backup / f.name)
    read_ogg = src_ogg if src_ogg.exists() else ogg
    read_side = src_side if src_side.exists() else side
    sidecar = json.loads(read_side.read_text(encoding="utf-8"))
    offsets = sidecar["offsets"]
    verses = spoken_verses(lang, books, b, c)
    if len(offsets) != len(verses):
        return False, f"offsets {len(offsets)} != verses {len(verses)} — refuse"
    bad = [v for v in targets if v < 1 or v > len(verses) or not verses[v - 1].strip()]
    if bad:
        return False, f"verse(s) {bad} out of range or empty"

    tmp = Path(tmp_root) / f"{b}_{c}"
    tmp.mkdir(parents=True, exist_ok=True)
    audio = decode(read_ogg, tmp / "src.wav")
    total_ms = len(audio) / SR * 1000

    def cut(a_ms, b_ms):
        return audio[int(a_ms / 1000 * SR):int(b_ms / 1000 * SR)]

    has_header = offsets[0] > 0
    parts = [cut(0, max(0, offsets[0] - GAP_MS))] if has_header else []
    for i in range(len(offsets)):
        end = (offsets[i + 1] - GAP_MS) if i + 1 < len(offsets) else total_ms
        parts.append(cut(offsets[i], end))
    pidx = (1 if has_header else 0)          # parts index of verse 1

    if not apply:
        for v in targets:
            p = parts[pidx + v - 1]
            print(f"    v{v:<4} {len(p) / SR * 1000:7.0f} ms   "
                  f"{verses[v - 1][:60]!r}")
        return True, f"plan: {len(targets)} verse(s), backup {'exists' if src_ogg.exists() else 'will be made'}"

    repairs = []
    for v in targets:
        old = parts[pidx + v - 1]
        t0 = time.time()
        wav, dur, info = narrate.synthesize_verse_gated(verses[v - 1], lang, str(tmp),
                                                        v - 1, b)
        if not wav or dur <= 0:
            return False, f"v{v}: synthesis failed"
        a, sr = sf.read(str(wav), dtype="float32")
        a = a.mean(1) if a.ndim > 1 else a
        new = resample(a, sr, SR)
        cur = speech_rms(new, SR)
        if cur > 1e-6:
            new = np.clip(new * (speech_rms(old, SR) / cur), -1.0, 1.0)
        parts[pidx + v - 1] = new
        reasons = (info or {}).get("reasons", [])
        repairs.append({"verse": v, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "old_ms": round(len(old) / SR * 1000),
                        "new_ms": round(len(new) / SR * 1000),
                        "attempts": (info or {}).get("attempts"),
                        "kept": (info or {}).get("kept"),
                        "still_failing": reasons, "secs": round(time.time() - t0)})
        print(f"    v{v:<4} {len(old)/SR*1000:6.0f} -> {len(new)/SR*1000:6.0f} ms  "
              f"attempts {len((info or {}).get('attempts') or [])}  "
              f"{'STILL FAILING ' + '|'.join(reasons) if reasons else 'clean'}", flush=True)

    gap = np.zeros(int(SR * GAP_MS / 1000), dtype="float32")
    out, new_offsets, pos = [], [], 0
    for i, p in enumerate(parts):
        if not has_header or i:
            new_offsets.append(round(pos / SR * 1000))
        out.append(p)
        pos += len(p)
        if i < len(parts) - 1:
            out.append(gap)
            pos += len(gap)
    merged = np.concatenate(out)

    wav = tmp / "chapter.wav"
    sf.write(str(wav), (merged * 32767).astype(np.int16), SR, subtype="PCM_16")
    new_ogg = tmp / "chapter.ogg"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-b:a", BITRATE,
                        "-c:a", "libopus", "-ac", "1", str(new_ogg)],
                       capture_output=True, creationflags=NO_WINDOW)
    if r.returncode != 0:
        return False, "encode failed: " + r.stderr.decode(errors="replace")[-200:]
    chk = decode(new_ogg, tmp / "chk.wav")            # prove it decodes
    if len(chk) < len(merged) * 0.95:
        return False, "result is truncated after encode"

    shutil.copy2(new_ogg, ogg)
    sidecar["offsets"] = new_offsets
    side.write_text(json.dumps(sidecar, separators=(",", ":")), encoding="utf-8")

    ok, msg = align(set_key, b, c)
    qa_path = live / f"{c}.qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.exists() else {}
    qa.setdefault("repairs", []).extend(repairs)
    qa["realigned"] = {"ok": ok, "msg": msg, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    qa_path.write_text(json.dumps(qa, separators=(",", ":"), ensure_ascii=False),
                       encoding="utf-8")
    failing = [r["verse"] for r in repairs if r["still_failing"]]
    delta = len(merged) / SR * 1000 - total_ms
    verdict = (f"ok ({len(targets)} verse(s), {delta:+.0f} ms, align {msg})"
               if ok else f"AUDIO WRITTEN BUT ALIGNMENT FAILED — {msg}")
    if failing:
        verdict += f"; ⚠ v{failing} still failing after {narrate.GATE_ATTEMPTS} draws — needs an ear"
    return ok and not failing, verdict


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True, choices=sorted(SETS),
                    help="alignment set KEY (kxii for sv, syn for ru, csl for cu, gen1599 for gnv)")
    ap.add_argument("--queue", help="file of `--book B --chapter C … # v3,7` or `B C 3,7` lines")
    ap.add_argument("--book", type=int)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--verses", help="comma list, 1-based")
    ap.add_argument("--apply", action="store_true", help="write (default is a dry-run plan)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="redo chapters already repaired")
    ap.add_argument("--allow-gpu-contention", action="store_true")
    a = ap.parse_args()

    if a.queue:
        queue = read_queue(a.queue)
    elif a.book is not None and a.chapter is not None and a.verses:
        queue = {(a.book, a.chapter): sorted({int(x) for x in a.verses.split(",") if x})}
    else:
        sys.exit("give --queue FILE, or --book/--chapter/--verses")
    if not queue:
        sys.exit("queue is empty — nothing parsed")

    lang = SETS[a.set]["lang"]
    books = narrate.load_bible(lang)
    keys = sorted(queue)
    if a.limit:
        keys = keys[:a.limit]
    n_verses = sum(len(queue[k]) for k in keys)
    print(f"set {a.set} (narration/{SETS[a.set]['dir']}, lang {lang}, engine "
          f"{narrate.LANG_CONFIG[lang]['engine']}): {n_verses} verse(s) in "
          f"{len(keys)} chapter(s) — {'APPLY' if a.apply else 'DRY RUN, nothing is written'}")

    if a.apply and not a.allow_gpu_contention:
        busy = gpu_busy()
        if busy:
            sys.exit("⛔ another render/repair holds the GPU:\n  " + "\n  ".join(busy)
                     + "\n  one card — wait, or --allow-gpu-contention on the owner's say-so")

    done = ok = fail = 0
    with tempfile.TemporaryDirectory() as tmp_root:
        for b, c in keys:
            targets = queue[(b, c)]
            qa_path = NARRATION / SETS[a.set]["dir"] / str(b) / f"{c}.qa.json"
            if a.apply and not a.force and qa_path.exists():
                did = {r["verse"] for r in json.loads(qa_path.read_text(encoding="utf-8"))
                       .get("repairs", []) if not r.get("still_failing")}
                if set(targets) <= did:
                    done += 1
                    continue
            print(f"{b}/{c}: v{targets}", flush=True)
            try:
                good, msg = repair_chapter(a.set, lang, books, b, c, targets, a.apply, tmp_root)
            except Exception as e:
                good, msg = False, f"{type(e).__name__}: {e}"
            print(f"    -> {'OK' if good else 'FAIL'}: {msg}", flush=True)
            ok += good
            fail += not good
            # ⛔⛔ FREE THIS CHAPTER'S SCRATCH BEFORE THE NEXT ONE.
            # `tmp_root` is ONE TemporaryDirectory for the whole run, and
            # repair_chapter writes three decoded WAVs into `<b>_<c>/`
            # (src, chk, chapter) — MEASURED 2026-09-04 at ~92 MB per chapter.
            # Nothing removed them until the process exited, so a 233-chapter
            # run accumulates ~21 GB of scratch it never reads again. That run
            # took the disk from 51 GB free to 23 GB in 90 minutes and would
            # have ended with ~5 GB of margin.
            # ▶ Why that matters more than housekeeping: a disk that fills
            #   mid-render produces the 1 Samuel 28 truncation class — offsets
            #   piled at EOF, verses silent — and it does so SILENTLY. The
            #   render-gate brief already records `render_preflight check`
            #   failing below 10 GB for exactly this reason.
            # Each chapter's scratch is dead the moment its chapter is done.
            scratch = Path(tmp_root) / f"{b}_{c}"
            if scratch.exists():
                shutil.rmtree(scratch, ignore_errors=True)
    print(f"\n{'repaired' if a.apply else 'planned'} {ok}, failed {fail}, "
          f"already done {done}")
    if a.apply:
        print("▶ now re-run the screen that condemned these verses on the NEW audio, "
              "and zero_duration_verses for the set; this tool's OK is not that.")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
