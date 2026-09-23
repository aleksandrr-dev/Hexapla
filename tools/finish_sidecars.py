# -*- coding: utf-8 -*-
"""Drive Geneva + Karl XII to complete word-level narration, unattended.

    python tools/finish_sidecars.py            # run detached; it takes hours

Owner asked (2026-08-11) for word-level highlighting on every rendered set.
ru already has it (1192/1192 live). This finishes the other two shipped sets:

    1. wait for the in-flight gnv alignment and gnv audio upload to end
    2. upload gnv again -> pushes the new .w.json sidecars
       (upload_narration uses checksum=True, so the 1.02 GB of audio already
        uploaded is skipped; only the sidecars go)
    3. align sv (Karl XII) on CPU
    4. upload sv -> pushes its sidecars

⚠ ALIGNMENT RUNS ON THE CPU VENV ON PURPOSE. `tools/.kokoro_venv` holds a
CPU-only torch. The GPU is held by the cu render (~5.9 GB of 8), and the
standing rule is ONE GPU JOB AT A TIME. Do not "speed this up" by pointing it
at .cosyvoice_venv or .chatterbox_venv while a render is running.

⚠ Karl XII's files live in `narration/sv/`, NOT `narration/kxii/` — the set id
and the directory differ (see SETS in align_words.py / upload_narration.py).
Checking the wrong path reports zero files and looks like data loss. It is not.

⚠ Do not delete a local render before its sidecars exist. Aligning a set whose
audio has been cleaned up means downloading ~1 GB back from archive.org first.
"""
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(r"C:/Projects/Hexapla")
NARR = Path(r"C:/Projects/Hexapla-releases/narration")
LOGS = NARR / "logs"
PY_CPU = REPO / "tools" / ".kokoro_venv" / "Scripts" / "python.exe"
PY = sys.executable
STAMP = "2026-08-11"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)


def running(needle):
    """True if a python process whose command line contains `needle` is alive."""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
         "Select-Object -ExpandProperty CommandLine"],
        capture_output=True, text=True, errors="replace")
    return any(needle in l for l in (r.stdout or "").splitlines())


def wait_for(needle, label, poll=120):
    while running(needle):
        log(f"waiting on {label} …")
        time.sleep(poll)
    log(f"{label} finished")


def count(sub, pat):
    return len(list((NARR / sub).rglob(pat)))


def run(cmd, logfile):
    log(f"$ {' '.join(str(c) for c in cmd)}")
    with open(LOGS / logfile, "w", encoding="utf-8", errors="replace") as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                              cwd=REPO).returncode


def main():
    wait_for("align_words.py --set gen1599", "gnv alignment")
    log(f"gnv: {count('gnv', '*.w.json')} sidecars / {count('gnv', '*.ogg')} oggs")

    wait_for("upload_narration.py gnv", "gnv audio upload")

    rc = run([PY, "tools/upload_narration.py", "gnv"],
             f"upload_gnv_sidecars_{STAMP}.log")
    log(f"gnv sidecar upload rc={rc}")

    rc = run([str(PY_CPU), "tools/align_words.py", "--set", "kxii",
              "--device", "cpu"], f"align_sv_{STAMP}.log")
    log(f"sv alignment rc={rc}, "
        f"{count('sv', '*.w.json')} sidecars / {count('sv', '*.ogg')} oggs")

    rc = run([PY, "tools/upload_narration.py", "sv"],
             f"upload_sv_sidecars_{STAMP}.log")
    log(f"sv upload rc={rc}")

    log("DONE — verify both items live before believing this:")
    log("  python tools/check_sidecars_live.py   (or query archive.org metadata)")


if __name__ == "__main__":
    main()
