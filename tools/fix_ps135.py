# -*- coding: utf-8 -*-
"""Force Psalm 135's «Аллилуия» to be spoken, then hand the GPU back to `cu`.

Ps 135 lost its superscription on 7 consecutive draws (4 before
narrate.join_short_lead, 3 after) while Psalms 106 and 117 — whose spoken text
is BYTE-IDENTICAL — always keep theirs. Every deterministic cause was tested
and eliminated (brackets, the splice, CosyVoice's English TN normalizer,
split_paragraph, repace_outliers, hidden characters), leaving model sampling.

So this walks the join punctuation as well as redrawing: «, » is the default,
and «! » / « — » both voiced correctly in isolated tests where «. » did not.
Only punctuation between title and verse changes — never a word.

⚠ IT PAUSES AND RESUMES THE SLAVONIC RENDER. Two CosyVoice models do not fit
on the 8 GiB card, and killing `cu` alone is futile — render_bootstrap.ps1
revives it within 10 minutes, so PAUSE_cu must exist first. The finally-block
restores it whatever happens.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
COSY = HERE / ".cosyvoice_venv/Scripts/python.exe"
KOKORO = HERE / ".kokoro_venv/Scripts/python.exe"
LOGS = Path("C:/Projects/Hexapla-releases/narration/logs")
PAUSE = LOGS / "PAUSE_cu"
BACKUP = Path("C:/Projects/Hexapla-releases/narration/ru_pre_announce")
BOOK, CHAP = 18, 134                      # 0-based: Psalm 135
VARIANTS = [", ", "! ", " — "]
DRAWS_PER_VARIANT = 3


def ps(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout.strip()


def stop_cu():
    PAUSE.write_text("", encoding="utf-8")
    ps("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
       "Where-Object { $_.CommandLine -like '*narrate.py*' -and "
       "$_.CommandLine -like '*--lang cu*' } | "
       "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    ps("Get-CimInstance Win32_Process -Filter \"Name like 'powershell%'\" | "
       "Where-Object { $_.CommandLine -like '*supervisor*' -and "
       "$_.CommandLine -like '*cu*' } | "
       "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    time.sleep(8)
    print("cu paused and stopped", flush=True)


def start_cu():
    PAUSE.unlink(missing_ok=True)
    ps(f"& powershell -NoProfile -ExecutionPolicy Bypass -File "
       f"'{LOGS / 'render_bootstrap.ps1'}'")
    time.sleep(20)
    alive = ps("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
               "Where-Object { $_.CommandLine -like '*--lang cu*' } | "
               "Measure-Object | Select-Object -ExpandProperty Count")
    print(f"cu resumed (processes: {alive})", flush=True)


def main():
    sys.path.insert(0, str(HERE))
    import rerender_ru_stale as rr

    stop_cu()
    try:
        for join in VARIANTS:
            env = {**os.environ, "NARRATE_LEAD_JOIN": join}
            for draw in range(1, DRAWS_PER_VARIANT + 1):
                r = subprocess.run(
                    [str(COSY), "-u", str(HERE / "narrate.py"), "--lang", "ru",
                     "--book", str(BOOK), "--chapter", str(CHAP), "--force"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", cwd=str(HERE.parent), env=env)
                if r.returncode != 0:
                    print(f"  join={join!r} draw {draw}: RENDER FAILED", flush=True)
                    continue
                for ext in ("ogg", "json", "w.json"):
                    f = BACKUP / str(BOOK) / f"{CHAP}.{ext}"
                    if f.exists():
                        f.unlink()
                subprocess.run(
                    [str(KOKORO), "-u", str(HERE / "apply_announcements.py"),
                     "--book", str(BOOK), "--chapter", str(CHAP)],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", cwd=str(HERE.parent))
                ok, heard = rr.title_spoken(BOOK, CHAP)
                print(f"  join={join!r} draw {draw}: title="
                      f"{'YES' if ok else 'NO'}  heard={heard[:58]!r}", flush=True)
                if ok:
                    print(f"\n✅ FIXED with join {join!r}", flush=True)
                    return 0
        print("\n⚠ STILL NOT SPOKEN after every variant — needs a human ear",
              flush=True)
        return 1
    finally:
        start_cu()


if __name__ == "__main__":
    sys.exit(main())
