# -*- coding: utf-8 -*-
"""Persistent faster-whisper worker. TWO protocols on one stdin, one JSON line back each.

Exists because faster-whisper is installed in `.kokoro_venv` while the renderers
run in `.cosyvoice_venv` / `.chatterbox_venv`, and the venvs must not be merged
(installing into a render venv risks a torch/CUDA stack that currently works).
A worker also amortizes the model load across a whole build or render.

⚠ THIS IS WHISPER, NOT KOKORO. Kokoro is a TTS engine that happens to share
the venv. Nothing here is English-only.

## Protocol A — the original (build_announcements.py, since 2026-08), unchanged

    p = Popen([kokoro_python, "tools/_asr_worker.py", "--lang", "ru"], ...)
    p.stdin.write(str(wav) + "\\n")                      # a bare WAV path
    {"text": "...", "words": [{"w","start","end"}, ...]} # word_timestamps=True

## Protocol B — the verse gate (narrate.synthesize_verse_gated, 2026-09-03)

    -> {"wav": "C:/.../verse.wav", "lang": "en"}          # a JSON object
    <- {"ok": true, "model": "small.en", "text": "...", "tokens": [...]}
    <- {"ok": false, "err": "..."}

A line starting with `{` is protocol B; anything else is a path (protocol A).
Protocol B picks the model per request (`small.en` for English, multilingual
`small` otherwise) and uses EXACTLY the settings every validated screen was
measured with (qa_selfrepeat / qa_asr_sweep): beam 5, no VAD, no conditioning
on previous text, hallucination_silence_threshold 0.5. ⚠ Change them and the
10/10 + 0/40 validation no longer applies — re-run `qa_gate.py --validate`.

⚠ NO `initial_prompt`, ever. Seeding whisper with the expected text builds a
detector that always agrees with you.
⚠ A bad clip must never kill the worker — every request is wrapped.
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_MODELS = {}


def get_model(name):
    from faster_whisper import WhisperModel
    m = _MODELS.get(name)
    if m is None:
        m = WhisperModel(name, device="cpu", compute_type="int8",
                         cpu_threads=4, num_workers=1)
        _MODELS[name] = m
    return m


def tokens_of(text):
    """The normalisation `qa_selfrepeat.score_set` validated with: lower-case,
    alphanumerics only, whitespace-split. Kept here so worker and screen agree."""
    txt = text.lower()
    return [t for t in "".join(c if c.isalnum() or c.isspace() else " "
                               for c in txt).split() if t]


def protocol_a(path, lang, model_name):
    model = get_model(model_name)
    segs, _ = model.transcribe(path, language=lang, beam_size=5,
                               condition_on_previous_text=False,
                               vad_filter=False, word_timestamps=True)
    segs = list(segs)
    words = []
    for sg in segs:
        for w in (getattr(sg, "words", None) or []):
            words.append({"w": w.word.strip(),
                          "start": round(w.start * 1000),
                          "end": round(w.end * 1000)})
    return {"text": " ".join(s.text for s in segs).strip(), "words": words}


def protocol_b(req):
    lang = req.get("lang") or "en"
    name = req.get("model") or ("small.en" if lang == "en" else "small")
    model = get_model(name)
    segs, _ = model.transcribe(
        req["wav"], language=lang, beam_size=5, vad_filter=False,
        condition_on_previous_text=False,
        hallucination_silence_threshold=0.5)
    text = " ".join(s.text for s in segs)
    return {"ok": True, "model": name, "text": text, "tokens": tokens_of(text)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--model", default="small")
    args = ap.parse_args()
    # Protocol A callers expect the model loaded before "ready"; protocol B
    # callers pass no args and load lazily per language.
    if "--lang" in sys.argv or "--model" in sys.argv:
        get_model(args.model)
    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                print(json.dumps(protocol_b(json.loads(line)), ensure_ascii=False),
                      flush=True)
            except Exception as e:
                print(json.dumps({"ok": False, "err": f"{type(e).__name__}: {e}"}),
                      flush=True)
        else:
            try:
                print(json.dumps(protocol_a(line, args.lang, args.model)), flush=True)
            except Exception as e:                      # never kill the build
                print(json.dumps({"text": "", "err": str(e)}), flush=True)


if __name__ == "__main__":
    main()
