#!/usr/bin/env python
"""
live_status.py - one call, one screen: every campaign process, the GPU, and
the newest logs, from LIVE state (CIM + nvidia-smi + file mtimes), never from
a log line or a handoff.

Why this exists (measured 2026-09-10 over 7 sessions): 46 hand-typed
Get-CimInstance blocks (median 524 chars) and 132 log peeks (median 330
chars) per campaign week. Each is re-billed on every later turn. This script
replaces both with ~40 chars of command and a compact, fixed-shape output.

    python C:/Projects/Hexapla/tools/live_status.py            # everything
    python C:/Projects/Hexapla/tools/live_status.py -p narrate  # procs matching
    python C:/Projects/Hexapla/tools/live_status.py -l sv_apoc -n 5   # tail logs
    python C:/Projects/Hexapla/tools/live_status.py --json     # machine-readable

Rules honoured (global CLAUDE.md):
  * a query that FAILS prints FAILED and exits 1 - it never prints 0 procs or
    an empty log list as if that were the truth;
  * no wmic (CIM via powershell), ASCII only, read-only - it kills nothing.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

# Windows consoles default to cp1252; logs carry UTF-8 (and emoji). Never crash
# on output: replace what the console cannot show.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa
    pass

DATA = r"C:\Projects\Hexapla-releases"
LOGDIRS = [os.path.join(DATA, "narration", "logs"), os.path.join(DATA, "_work"),
           os.path.join(DATA, "logs")]
# Anything a campaign runs detached. Extend here, not in the session.
CAMPAIGN = ("narrate", "render_supervisor", "upload_narration_batched",
            "ia_upload_watch", "ship_chain", "repair_verses", "tail_hallucinations",
            "qa_", "align_words", "thorlaks_", "kxii_", "keepalive", "sv_apoc",
            "deliver_outstanding", "whisper", "chatterbox", "kokoro")
INTERESTING_ARGS = re.compile(r"(--lang\s+\S+|--set\s+\S+|--book\s+\S+|-Lang\s+\S+|--file\s+\S+)")

PS_PROCS = (
    "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|powershell|pwsh|cmd|ffmpeg|node)' } "
    "| Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Compress -Depth 2"
)


def ps(cmd, timeout=40):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("powershell rc=%d: %s" % (r.returncode, r.stderr.strip()[:300]))
    return r.stdout


def procs(pattern):
    out = ps(PS_PROCS)
    out = out.strip()
    if not out:
        return []
    rows = json.loads(out)
    if isinstance(rows, dict):
        rows = [rows]
    me = os.getpid()
    hits = []
    for p in rows:
        cl = p.get("CommandLine") or ""
        if p.get("ProcessId") in (me,) or "live_status" in cl or "CimInstance" in cl:
            continue
        if pattern:
            if not re.search(pattern, cl, re.I):
                continue
        elif not any(k in cl for k in CAMPAIGN):
            continue
        cd = p.get("CreationDate") or ""
        m = re.search(r"/Date\((\d+)\)/", str(cd))
        started = dt.datetime.fromtimestamp(int(m.group(1)) / 1000) if m else None
        age = (dt.datetime.now() - started) if started else None
        script = ""
        ms = re.search(r"([A-Za-z0-9_.-]+\.(py|ps1))", cl)
        if ms:
            script = ms.group(1)
        args = " ".join(a for a in INTERESTING_ARGS.findall(cl))
        hits.append({"pid": p.get("ProcessId"), "ppid": p.get("ParentProcessId"),
                     "name": p.get("Name"), "script": script, "args": args,
                     "started": started.strftime("%m-%d %H:%M") if started else "?",
                     "age_min": int(age.total_seconds() // 60) if age else -1,
                     "cmd": cl[:160]})
    hits.sort(key=lambda h: (h["script"], h["pid"]))
    return hits


def gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return {"error": "nvidia-smi rc=%d" % r.returncode}
        def num(x):
            x = x.strip()
            return int(float(x)) if re.match(r"^[0-9.]+$", x) else -1   # [N/A] -> -1, never a fake 0
        u, mu, mt, t = [num(x) for x in r.stdout.strip().splitlines()[0].split(",")]
        r2 = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory",
                             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
        apps = [tuple(x.strip() for x in ln.split(",")) for ln in r2.stdout.strip().splitlines() if ln.strip()]
        return {"util_pct": u, "mem_used_mb": mu, "mem_total_mb": mt, "temp_c": t,
                "apps": [{"pid": num(a[0]), "mem_mb": num(a[1])} for a in apps if len(a) == 2]}
    except FileNotFoundError:
        return {"error": "nvidia-smi not found"}
    except Exception as e:  # noqa
        return {"error": str(e)[:200]}


def tail_bytes(path, n):
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 64 * 1024))
            lines = fh.read().decode("utf-8", "replace").splitlines()
        return [ln.rstrip() for ln in lines[-n:]]
    except Exception as e:  # noqa
        return ["<unreadable: %s>" % e]


def logs(substr, n, count):
    found = []
    for d in LOGDIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            p = os.path.join(d, f)
            if not os.path.isfile(p):
                continue
            if substr and substr.lower() not in f.lower():
                continue
            found.append((os.path.getmtime(p), p))
    found.sort(reverse=True)
    now = dt.datetime.now().timestamp()
    out = []
    for mt, p in found[:count]:
        out.append({"path": p, "age_min": int((now - mt) // 60), "size": os.path.getsize(p),
                    "tail": tail_bytes(p, n)})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("-p", "--procs", metavar="REGEX", help="only processes whose command line matches")
    ap.add_argument("-l", "--log", metavar="SUBSTR", help="only logs whose file name contains this")
    ap.add_argument("-n", "--lines", type=int, default=3, help="tail lines per log (default 3)")
    ap.add_argument("-c", "--count", type=int, default=6, help="how many newest logs (default 6)")
    ap.add_argument("--no-gpu", action="store_true")
    ap.add_argument("--no-logs", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        pr = procs(a.procs)
    except Exception as e:  # noqa
        print("FAILED: process query: %s" % e)
        return 1
    g = None if a.no_gpu else gpu()
    lg = None if a.no_logs else logs(a.log, a.lines, a.count)

    if a.json:
        print(json.dumps({"procs": pr, "gpu": g, "logs": lg}, indent=1))
        return 0

    print("=== procs (%d)%s ===" % (len(pr), " matching /%s/" % a.procs if a.procs else " campaign"))
    if not pr:
        print("  none")
    for h in pr:
        print("  %6s  %-28s %-24s started %s  %4d min  %s" % (
            h["pid"], h["script"] or h["name"], h["args"], h["started"], h["age_min"],
            "" if h["script"] else h["cmd"][:70]))
    if g is not None:
        if "error" in g:
            print("=== gpu: FAILED (%s) ===" % g["error"])
        else:
            print("=== gpu: %d%% util, %d/%d MB, %dC, %d compute app(s)%s ===" % (
                g["util_pct"], g["mem_used_mb"], g["mem_total_mb"], g["temp_c"], len(g["apps"]),
                " pids " + ",".join(str(x["pid"]) for x in g["apps"]) if g["apps"] else ""))
    if lg is not None:
        print("=== newest logs (%d)%s ===" % (len(lg), " matching '%s'" % a.log if a.log else ""))
        if not lg:
            print("  none found in " + "; ".join(LOGDIRS))
        for L in lg:
            print("  %s  (%d min old, %d B)" % (L["path"].replace(DATA + os.sep, ""), L["age_min"], L["size"]))
            for ln in L["tail"]:
                print("      | " + ln[:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
