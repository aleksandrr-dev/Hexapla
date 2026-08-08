# -*- coding: utf-8 -*-
"""Persistent Kokoro synthesis worker: one JSON request per stdin line.

WHY (owner-approved 2026-08-06). `synthesize_kokoro` spawned a FRESH Python
process for every verse and rebuilt `KPipeline` inside it. Measured on this
machine:

    import kokoro     7.5 s
    KPipeline(...)    4.8 s     <- model loaded from scratch, every verse
    actual synthesis  3.3 s     <- for a 6.4 s verse

So ~79% of the Geneva render was model loading, and the observed rate matched:
6.4 chapters/hour, i.e. ~6 days for the remaining 942 chapters. Loading once
and holding the pipeline removes that overhead entirely.

The separate INTERPRETER is still required — Kokoro lives in its own sandboxed
Python 3.12 venv and cannot be imported into the render process. What was never
required was a separate PROCESS PER VERSE.

Protocol, one JSON object per line each way:
    -> {"text": "...", "voice": "am_michael", "out": "C:/.../v.wav"}
    <- {"ok": true}   |   {"ok": false, "err": "..."}

⚠ A bad verse must never kill the worker — every request is wrapped, because a
dead worker stalls a render that nobody is watching.
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    import kokoro
    import numpy as np
    import soundfile as sf

    pipeline = kokoro.KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            chunks = [a for _, _, a in pipeline(req["text"], voice=req["voice"])]
            if not chunks:
                print(json.dumps({"ok": False, "err": "no audio generated"}),
                      flush=True)
                continue
            # 24000 Hz to match the previous per-verse path exactly; the
            # concatenator and offsets depend on it.
            sf.write(req["out"], np.concatenate(chunks), 24000)
            print(json.dumps({"ok": True}), flush=True)
        except Exception as e:
            print(json.dumps({"ok": False, "err": f"{type(e).__name__}: {e}"}),
                  flush=True)


if __name__ == "__main__":
    main()
