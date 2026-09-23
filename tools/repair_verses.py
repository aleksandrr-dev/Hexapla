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

⚠⚠ **A DEAD RUN LEAVES A MARKER, FROM 2026-09-22.** Until today a run wrote one
log and nothing else, and its LAST LOG LINE looked identical whether the process
had finished, died, or was still working — so "dead at 86 chapters" and "running
at 86 chapters" were distinguishable only by reading the process list, and three
sessions in a row did not. Measured over every `pron_requeue_*.log`: FOUR of
seven runs ended with no completion line, one of them at 105 chapters.

A **marker file** fixes it where a log line cannot, because its presence, its
content and its mtime are all independent of HOW the process ended:

    narration/logs/_jobs/<job>.json    <job> = the --queue basename, else
                                       <set>_<pid>

Three writes: `state:"running"` BEFORE the first chapter (this is the one that
makes death detectable — a marker written only on success cannot tell a dead run
from one that never started); the running counts after each chapter (atomic, via
`os.replace`, so a kill mid-write cannot truncate the JSON); and `state:
"finished"` (or `"crashed"`, from the exception handler) at exit.

▶ Read it with `python tools/repair_job_status.py` — its headline verdict is
**DIED** (marker says `running`, the pid is gone), which is the state that cost
those four runs and which no other instrument reports.
⛔ A SIGKILL or a power loss stamps nothing; that is the common case here, and it
is exactly what the status tool's marker-vs-process-list comparison detects.

⚠ ⚠ "IT WAS RE-ENCODED" IS NOT EVIDENCE. Every result is decoded back and
length-checked before it replaces anything; every new verse's gate verdict,
attempts and ASR tail are written to `<chapter>.qa.json` under "repairs"; the
alignment's `verses ok N` line is REQUIRED and its absence is a reported
failure. Re-run the screen that condemned the verse afterwards regardless.
"""
import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import numpy as np
import soundfile as sf

import narrate
import qa_text_explained
from align_words import SETS

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
SR = 48000
GAP_MS = 600
BITRATE = "48k"
NO_WINDOW = getattr(narrate, "_NO_WINDOW", 0)

def text_explained_repeats(verse_text):
    """Does the PRINTED verse itself end in a repetition? -> bool.

    ⚠⚠ A `repeat:kN` flag on a verse whose PRINT repeats is the gate firing on
    scripture. Such a draw is CLEAN, and counting it as a failure is what made
    the tie-rule below protect a defective take — see the note there.

    ⛔ NARROW ON PURPOSE. This explains `repeat:*` reasons ONLY. An `append:*`
    flag is an EXTRA word the print does not contain; no amount of printed
    repetition explains it, and treating one as explained would discard a real
    defect. The same asymmetry qa_text_explained.py's docstring records: text
    evidence can prove redrawing is FUTILE, it can never prove a take is clean.
    """
    return bool(qa_text_explained.analyse(verse_text or "")[0])


def effective_reasons(reasons, explained):
    """Reasons that still stand once the PRINT has explained what it can."""
    if not explained:
        return list(reasons or [])
    return [r for r in (reasons or []) if not r.startswith("repeat:")]


Q_CMD = re.compile(r"--book\s+(\d+)\s+--chapter\s+(\d+).*?#\s*v([\d,]+)")
Q_TRIPLE = re.compile(r"^\s*(\d+)[\s/]+(\d+)\s+v?([\d,]+)\s*$")


def refresh_gate_record(qa, repairs):
    """Point `gate`/`failing` at the audio that is ACTUALLY on disk now.

    ⛔⛔ WHY THIS EXISTS — 2026-09-20. Until today this function did not, and
    a repair wrote only `repairs` and `realigned`. `gate` and `failing` kept
    the ORIGINAL render's verdict forever, so `qa_gate_appends.py` re-reported
    a repaired verse on every pass: a stale answer indistinguishable from a
    fresh one, which is the one shape this project forbids a status function.
    ▶ Measured on the 2026-09-20 KJV repair: 10 of 45 repaired verses were
      still on the gate list, with the ASR screen finding no append on any of
      them; and the run's benign-looking «already done 31» was 31 chapters the
      queue had condemned AGAIN off the stale record.
    ▶ `research/_evidence/en_kjv_repair_rescreen_2026-09-20.md`

    ⚠ `kept_existing_take` REPAIRS ARE SKIPPED, and that is the whole safety
    of this. When the gate could not discriminate, the shipped take was kept —
    the audio did not change, so its verdict must not either.

    ⚠ `failing` and `gate[v]["reasons"]` carry the gate's RAW reasons at render
    time, so they keep carrying raw reasons here. The print-explained filter is
    `qa_text_explained.py`'s job downstream, not this record's.

    The pre-repair verdict is preserved once under `gate_pre_repair` so the
    original is never destroyed by a repair (or by a second one).

    ⛔⛔ A REPAIR RECORD WITH NO `raw_reasons` KEY IS NOT A CLEAN ONE. Five
    entries on disk predate that field (2026-09-20 count). `.get(...) or []`
    read them as «the kept draw had no reasons» and would have written a
    FABRICATED clean verdict over a real one — a failed read made
    indistinguishable from a real «nothing to report», which is exactly what
    this project forbids. Such a verse is HELD and NAMED instead.

    Returns (refreshed verses, [(verse, why-it-was-held)]).
    """
    touched, held = [], []
    for r in repairs:
        if r.get("kept_existing_take"):
            held.append((r["verse"], "kept_existing_take — audio unchanged"))
            continue                      # audio unchanged -> verdict unchanged
        if "raw_reasons" not in r or "attempts" not in r:
            held.append((r["verse"],
                         "repair record predates raw_reasons/attempts — the "
                         "kept draw's verdict is UNKNOWN, not clean"))
            continue
        v = str(r["verse"])
        gate = qa.setdefault("gate", {})
        if v in gate:
            qa.setdefault("gate_pre_repair", {}).setdefault(v, gate[v])
        raw = list(r["raw_reasons"])
        gate[v] = {"attempts": r["attempts"], "kept": r.get("kept"),
                   "reasons": raw, "from_repair": r.get("ts")}
        failing = qa.setdefault("failing", {})
        if raw:
            failing[v] = raw
        else:
            failing.pop(v, None)
        touched.append(r["verse"])
    return touched, held


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


def proc_cmdline(pid):
    """-> the command line of `pid` as one string, or None if it cannot be read.

    ⛔⛔ None IS «COULD NOT DETERMINE», NOT «NOT THIS JOB». The caller must not
    treat an unreadable command line as evidence in either direction: read as
    «not this job» it reports a live render as DIED, and read as «this job» it
    reports a dead pid that has been recycled as alive.

    ⚠ ONE PowerShell trip. `repair_job_status.py` answers this same question and
    imports THIS function rather than re-inventing the process-table walk — a
    second implementation would answer a subtly different question (the repo
    makes the same argument for `qa_gate`'s parser).
    """
    if os.name != "nt":
        return None
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"ProcessId = %d\" | "
         "Select-Object -ExpandProperty CommandLine" % int(pid)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=NO_WINDOW)
    if r.returncode != 0:
        return None
    line = (r.stdout or "").strip()
    return line or None


def proc_alive(pid):
    """-> True / False / None (could not determine) for one pid.

    ⚠ A pid OUTSIDE the platform's range cannot exist, and `os.kill` raises
    `OverflowError` for it rather than `ProcessLookupError`. Treated as NOT
    ALIVE, which is the honest answer — it is the one exception that is a real
    determination rather than a failed read.
    """
    if pid is None:
        return None
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except OverflowError:
        return False         # cannot be a real pid -> cannot be alive
    except PermissionError:
        return True          # exists, owned by someone else
    except OSError:
        return None
    except (TypeError, ValueError):
        return None
    return True


# ------------------------------------------------------------ the job marker
#
# ⛔⛔ ADDITIVE. Nothing in this section may change what is printed to stdout,
# any exit code, the synth_sha resume guard, the GPU guard, the per-chapter
# scratch cleanup, or a single byte of the repair logic. It only writes a
# sidecar; every failure path here is swallowed so that a marker problem can
# never abort a render.
_JOBS_DIR = NARRATION / "logs" / "_jobs"
_IN_SELFTEST = False
_MARKER = {"path": None, "data": None, "finished": True}


def job_name(set_key, queue_path):
    """-> the marker's basename. Queue basename, else `<set>_<pid>`.

    ⚠ The queue name is preferred because it is what a human types and what the
    launcher is named after; a set+pid marker would be unaddressable from the
    next session, which is the session that has to read it.
    """
    if queue_path:
        stem = Path(queue_path).stem
        if stem:
            return stem
    return "%s_%d" % (set_key, os.getpid())


def marker_path(job):
    return _JOBS_DIR / ("%s.json" % job)


def _write_marker(data):
    """Write the marker ATOMICALLY: `<name>.tmp` then os.replace.

    ⛔ A kill mid-write must not leave a truncated JSON. A corrupt marker is
    worse than no marker: the status tool would have to say COULD NOT DETERMINE
    about a job whose state is otherwise perfectly knowable, and this repo has
    already been burned by one count function returning a believable value on a
    failed read.
    """
    path = _MARKER["path"]
    if path is None:
        return
    tmp = path.with_suffix(".json.tmp")
    try:
        _JOBS_DIR.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        os.replace(str(tmp), str(path))
    except OSError:
        # ⚠ A marker that cannot be written must not fail the render — but say
        # so, so the absence of a marker is never mistaken for a live job.
        print("    \u26a0 job marker NOT writable at %s" % path, flush=True)


def marker_start(set_key, queue_path, total, argv):
    """Stamp `state:"running"` BEFORE the first chapter.

    ⛔⛔ THIS IS THE WRITE THAT MATTERS. A marker written only at exit cannot
    distinguish a run that died at chapter 86 from one that never started, which
    is the whole defect: absence of a completion line means both «died» and «not
    yet». `pid` is recorded so the status tool can ask whether it is still alive.
    """
    job = os.environ.get("HEXAPLA_REPAIR_JOB") or job_name(set_key, queue_path)
    _MARKER["path"] = marker_path(job)
    _MARKER["finished"] = False
    _MARKER["data"] = {
        "job": job,
        "set": set_key,
        "state": "running",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "queue": str(Path(queue_path).resolve()) if queue_path else None,
        "total": total,
        "done": 0,
        "ok": 0,
        "fail": 0,
        "last_chapter": None,
        "argv": list(argv),
    }
    _write_marker(_MARKER["data"])
    atexit.register(marker_exit)


def marker_progress(done, ok, fail, b, c):
    """Update the running counts after each chapter (atomic)."""
    if _MARKER["data"] is None:
        return
    _MARKER["data"].update({
        "done": done, "ok": ok, "fail": fail,
        "last_chapter": [b, c],
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    _write_marker(_MARKER["data"])


def marker_exit():
    """Stamp the terminal state once, from atexit.

    ⚠ atexit runs on a normal return AND on an uncaught exception (after the
    traceback is printed), so this covers both. It does NOT run on SIGKILL or a
    power loss — the marker then keeps `state:"running"` forever, and the pid it
    names is gone, which is precisely the pair the status tool reads as DIED.
    ⛔ Guarded so a second call (finally + atexit) writes only one verdict.
    """
    if _MARKER["finished"] or _MARKER["data"] is None:
        return
    _MARKER["finished"] = True
    exc = sys.exc_info()[1]
    if exc is not None:
        _MARKER["data"].update({
            "state": "crashed",
            "crash": "%s: %s" % (type(exc).__name__, exc),
            "traceback": "".join(traceback.format_exception(
                type(exc), exc, exc.__traceback__))[-2000:],
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    else:
        _MARKER["data"].update({
            "state": "finished",
            "rc": _MARKER["data"].get("rc"),
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    _write_marker(_MARKER["data"])


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
    # ⚠ MUST match narrate_chapter: a per-verse synthesis override applies to a
    # repair too, or a repaired verse silently reverts to the printed form that
    # was condemned. ylt 12/23 v25 doubled its final name in 12/12 draws for
    # exactly the punctuation this fixes.
    return narrate.apply_overrides(lang, b, c, out)


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


def repair_chapter(set_key, lang, books, b, c, targets, apply, tmp_root,
                   install_tied=()):
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

    # Prior synthesis-input hashes, so an input CHANGE can be detected without
    # a flag. Absent in records written before 2026-09-07 -> None -> no claim.
    prior_shas = {}
    _qa_live = live / f"{c}.qa.json"
    if _qa_live.exists():
        try:
            for _r in (json.loads(_qa_live.read_text(encoding="utf-8"))
                       .get("repairs") or []):
                if _r.get("synth_sha"):
                    prior_shas[_r.get("verse")] = _r["synth_sha"]
        except (OSError, ValueError):
            pass                      # unreadable history is NO information

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
        reasons = (info or {}).get("reasons", [])
        atts = (info or {}).get("attempts") or []

        # ⛔⛔ DO NOT INSTALL AN ARBITRARY TAKE — owner's instruction 2026-09-07.
        # When NO draw passed and every draw carries the SAME reason set, the
        # gate cannot tell them apart, so `synthesize_verse_gated` falls back to
        # attempt 1 by tie-break. That choice is a coin toss, and a coin toss
        # against SHIPPED AUDIO is a one-way bet: it can only make things worse.
        # ▶ MEASURED: ylt Genesis 13:14 (0/12 v14), 2026-09-05T20:20. Three
        #   draws, all gated `repeat:k2`; attempt 3 said «and eastward and
        #   westward» (CORRECT) and attempt 1 said «and westward and westward».
        #   Attempt 1 was kept. The run BEFORE it had already produced a correct
        #   take, and this one overwrote it. «eastward» and «westward» are
        #   equally good repeats of the «-ward» pattern, so the gate scored them
        #   identically — it was blind to the only thing that mattered.
        # ⚠ This is NARROW on purpose. If the draws differ in their reason sets
        #   the gate DID discriminate and the best take is a justified choice,
        #   so it is installed as before. Only a genuine tie is refused.
        # ⚠⚠ THE PRINT IS CONSULTED BEFORE THE TIE IS CALLED (2026-09-15).
        # ▶ MEASURED: kjv Numbers 5:22 (3/4 v22). The verse ENDS «Amen, amen.»,
        #   so every draw was gated `repeat:k1` — three identical reason sets,
        #   which read as a tie, so the existing take was kept. But the existing
        #   take's own gate record said `append:a` and its tail was «…amen amen
        #   a». The tie was computed AMONG THE DRAWS ONLY; the incumbent was
        #   never scored, and the three "failures" were the gate firing on
        #   scripture. The owner confirmed the stray «a» BY EAR 2026-09-15.
        # ⇒ A draw whose only reasons are explained by the print is CLEAN, and a
        #   clean draw is not tied with anything.
        explained = text_explained_repeats(verses[v - 1])
        reasons = effective_reasons(reasons, explained)
        sigs = {tuple(sorted(effective_reasons(x.get("reasons"), explained)))
                for x in atts
                if "synthesis-failed" not in (x.get("reasons") or [])}
        tails = {(x.get("tail") or "").strip() for x in atts if x.get("tail")}
        gate_blind = (len(atts) >= 2 and len(sigs) == 1
                      and next(iter(sigs), ()) and bool(reasons))
        # ⚠ The tie-rule protects the SHIPPED take on the assumption that it was
        # made from the SAME synthesis string. When an override or a lexicon row
        # changed that string, the old take is not a comparable alternative and
        # protecting it would freeze the defect the change was made to fix.
        # ▶ The hash below is recorded so a FUTURE run can detect this on its
        #   own; records written before 2026-09-07 carry no hash, so the
        #   transition needs --install-tied once.
        synth_sha = hashlib.sha1(verses[v - 1].encode("utf-8")).hexdigest()[:12]
        prior_sha = prior_shas.get(v)
        input_changed = prior_sha is not None and prior_sha != synth_sha
        if gate_blind and (v in install_tied or input_changed):
            why = (f"--install-tied named v{v}" if v in install_tied else
                   f"the synthesis input CHANGED ({prior_sha} -> {synth_sha})")
            print(f"    v{v:<4} installing a tied take because {why}", flush=True)
            gate_blind = False
        if gate_blind:
            kept_old = True
            print(f"    v{v:<4} {len(old)/SR*1000:6.0f} ms  KEPT EXISTING TAKE — "
                  f"{len(atts)} draws all gated {'|'.join(reasons)}, so the gate "
                  f"could not choose between them"
                  + (f"; {len(tails)} DISTINCT tails were produced — an ear may "
                     f"want this verse" if len(tails) > 1 else ""), flush=True)
        else:
            kept_old = False
            parts[pidx + v - 1] = new

        repairs.append({"verse": v, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "old_ms": round(len(old) / SR * 1000),
                        "new_ms": round(len(old if kept_old else new) / SR * 1000),
                        "attempts": atts,
                        "kept": (info or {}).get("kept"),
                        # ⚠ Explicit, so a later reader never has to infer it.
                        "kept_existing_take": kept_old,
                        "synth_sha": synth_sha,
                        "gate_could_not_discriminate": bool(gate_blind),
                        "distinct_tails": sorted(tails) if gate_blind else None,
                        # ⚠ Raw vs effective, both kept: a later reader must be
                        # able to see WHAT the gate said as well as what stood
                        # after the print explained it.
                        "text_explained_repeats": bool(explained),
                        "raw_reasons": list((info or {}).get("reasons") or []),
                        "still_failing": reasons, "secs": round(time.time() - t0)})
        if not kept_old:
            print(f"    v{v:<4} {len(old)/SR*1000:6.0f} -> {len(new)/SR*1000:6.0f} ms  "
                  f"attempts {len(atts)}  "
                  f"{'STILL FAILING ' + '|'.join(reasons) if reasons else 'clean'}",
                  flush=True)

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
    _, _held_gate = refresh_gate_record(qa, repairs)
    for _v, _why in _held_gate:
        if "kept_existing_take" not in _why:
            print(f"    v{_v:<4} ⚠ gate record NOT refreshed — {_why}",
                  flush=True)
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
    # ⚠⚠ USE THIS ONLY WHEN THE SYNTHESIS INPUT ITSELF CHANGED — a new
    #    synthesis_overrides row or a new lexicon respelling for this verse.
    #    In that case the shipped take was made from a DIFFERENT string, so it
    #    is not a comparable alternative and the tie-rule must not protect it.
    # ⛔ It is NOT a way to get past a verse that keeps failing. Redrawing an
    #    unchanged input on a tie is exactly the coin toss this tool now
    #    refuses; forcing it re-opens the Genesis 13:14 bug by hand.
    # ⚠ A VERSE LIST, not a boolean. The union-queue rule forces a repair run to
    #   name every verse in the chapter that carries a prior repair, so a global
    #   flag would strip the tie-protection from verses it was never meant for.
    ap.add_argument("--install-tied", default="",
                    help="comma list of verses (1-based) that may install a "
                         "tied take. ONLY verses whose synthesis input changed.")
    ap.add_argument("--allow-gpu-contention", action="store_true")
    a = ap.parse_args()

    tied_verses = {int(x) for x in a.install_tied.split(",") if x.strip()}
    if tied_verses:
        print(f"⚠ --install-tied: verses {sorted(tied_verses)} may install a "
              f"tied take. Every OTHER verse keeps its existing take on a tie.")
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
    # ⛔⛔ THE MARKER IS STAMPED BEFORE THE FIRST CHAPTER, NOT AFTER THE LAST.
    # This is the write that makes a death detectable: a marker that appears
    # only on success cannot tell a run that died at chapter 86 from one that
    # never started. ⚠ Additive — `total` is the number of chapters THIS run
    # will attempt (post-`--limit`), so `done/total` is readable on its own.
    marker_start(a.set, a.queue, len(keys), sys.argv)
    try:
        with tempfile.TemporaryDirectory() as tmp_root:
            for b, c in keys:
                targets = queue[(b, c)]
                qa_path = NARRATION / SETS[a.set]["dir"] / str(b) / f"{c}.qa.json"
                # ⛔⛔ «ALREADY REPAIRED» IS NOT «REPAIRED FROM THE CURRENT INPUT».
                # This guard used to ask only «has this verse ever been repaired
                # successfully?». A verse repaired last week with the OLD lexicon
                # satisfied it, so a re-render driven by a NEW respelling was
                # skipped silently — measured 2026-09-07: a 70-chapter lexicon
                # re-render skipped 60 of them, printing a benign «already done 1»
                # per chapter while the audio kept the old pronunciation.
                # ▶ So the skip now ALSO requires the recorded `synth_sha` to match
                #   the synthesis input we would use today. Records written before
                #   2026-09-07 carry no sha and therefore never satisfy it — the
                #   conservative direction, since re-repairing a sound verse costs
                #   a GPU minute and skipping a stale one ships the wrong audio.
                if a.apply and not a.force and qa_path.exists():
                    try:
                        recs = json.loads(qa_path.read_text(encoding="utf-8")).get("repairs", [])
                    except (OSError, ValueError):
                        recs = []
                    want = spoken_verses(lang, books, b, c)
                    newest = {}
                    for r in recs:
                        v, ts = r.get("verse"), r.get("ts") or ""
                        if v and ts >= (newest.get(v, {}).get("ts") or ""):
                            newest[v] = r
                    did = set()
                    for v in targets:
                        r = newest.get(v)
                        if not r or r.get("still_failing"):
                            continue
                        sha = hashlib.sha1(want[v - 1].encode("utf-8")).hexdigest()[:12]
                        if r.get("synth_sha") == sha:
                            did.add(v)
                    if set(targets) <= did:
                        done += 1
                        marker_progress(done, ok, fail, b, c)
                        continue
                print(f"{b}/{c}: v{targets}", flush=True)
                try:
                    good, msg = repair_chapter(a.set, lang, books, b, c, targets, a.apply,
                                               tmp_root, install_tied=tied_verses)
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
                marker_progress(done, ok, fail, b, c)

            # ⚠ A `finally` here rather than relying on atexit alone: atexit covers
            # an uncaught exception, but this is where the counts at the moment of
            # exit are known, and `marker_exit` is guarded so only one verdict lands.
            final = 0 if not fail else 1
            if _MARKER["data"] is not None:
                _MARKER["data"]["rc"] = final
            marker_exit()
    except BaseException:
        # ⛔ Terminal state from the EXCEPTION path — a run that dies
        # inside the loop must stamp `crashed`, not be left as `running`.
        marker_exit()
        raise
    print(f"\n{'repaired' if a.apply else 'planned'} {ok}, failed {fail}, "
          f"already done {done}")
    if a.apply:
        print("▶ now re-run the screen that condemned these verses on the NEW audio, "
              "and zero_duration_verses for the set; this tool's OK is not that.")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
