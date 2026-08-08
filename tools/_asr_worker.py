# -*- coding: utf-8 -*-
"""Persistent faster-whisper worker: one WAV path per stdin line -> one JSON line.

Exists because faster-whisper is installed in `.kokoro_venv` while the CosyVoice
renderer runs in `.cosyvoice_venv`, and the two must not be merged — installing
into the render venv risks disturbing a torch/CUDA stack that currently works.
A worker also amortizes the ~3 s model load across a whole build instead of
paying it per clip.

    p = subprocess.Popen([kokoro_python, "tools/_asr_worker.py", "--lang", "ru"],
                         stdin=PIPE, stdout=PIPE, text=True, encoding="utf-8")
    p.stdin.write(str(wav) + "\n"); p.stdin.flush()
    heard = json.loads(p.stdout.readline())["text"]
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8",
                         cpu_threads=4, num_workers=1)
    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        path = line.strip()
        if not path:
            continue
        try:
            # ⚠ NO `initial_prompt`. Seeding whisper with the expected text is
            # how you build a detector that always agrees with you: it will
            # decode the words you handed it out of audio lacking them.
            segs, _ = model.transcribe(path, language=args.lang, beam_size=5,
                                       condition_on_previous_text=False,
                                       vad_filter=False)
            print(json.dumps({"text": " ".join(s.text for s in segs).strip()}),
                  flush=True)
        except Exception as e:                      # never kill the build
            print(json.dumps({"text": "", "err": str(e)}), flush=True)


if __name__ == "__main__":
    main()
