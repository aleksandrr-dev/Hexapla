# -*- coding: utf-8 -*-
"""Control for the wyc Middle English phoneme path (2026-10-05).

Three defects let the whole wyc set render with kokoro's MODERN G2P while the
config said "ipa": narrate._kokoro_request never put "ipa" in the request;
me_phonemes dropped /ç/ in its letter loop; and its ASCII «g» is not in
kokoro's vocab (the model wants «ɡ», U+0261). Each check below fails on the
code as it stood before the fix.

    python tools/test_kokoro_ipa_request.py              # rc 0 = all pass
    python tools/test_kokoro_ipa_request.py --narrate F  # test another copy
        of narrate.py (known-bad control: the HEAD copy must give rc 1)
"""
import argparse
import importlib.util
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeProc:
    def __init__(self):
        self.stdin = io.StringIO()
        self.stdout = io.StringIO(json.dumps({"ok": True}) + "\n")

    def poll(self):
        return None

    def kill(self):
        pass


def check_request(narrate):
    fake = FakeProc()
    narrate._kokoro_worker = lambda: fake
    narrate._kokoro_request("Y", "am_adam", "x.wav", ipa="iː")
    sent = json.loads(fake.stdin.getvalue().strip())
    return sent.get("ipa") == "iː", f"request sent {sorted(sent)}"


def check_header(narrate):
    """A verse goes through IPA, a header (verse_idx < 0) does not."""
    seen = {}

    def fake(text, voice, out, ipa=None):
        seen[out] = ipa
        return False
    narrate.synthesize_kokoro = fake
    narrate.synthesize_verse("Y schal", "wyc", ".", 0)
    narrate.synthesize_verse("Psalms, Chapter 23", "wyc", ".", -1)
    v, h = seen.get("verse_0000.wav"), seen.get("verse_-001.wav")
    ok = bool(v) and h is None
    return ok, f"verse ipa={v!r} header ipa={h!r}"


def check_phonemes():
    import me_phonemes as mp
    fails = []
    for word, want in [("riyt", "ç"), ("God", "ɡ"), ("Y", "iː")]:
        got = mp.to_ipa(word)
        if want not in got or "g" in got:
            fails.append(f"{word} -> {got!r} (want {want!r}, no ASCII g)")
    return not fails, "; ".join(fails) or "riyt/God/Y ok"


def check_vocab():
    import glob
    cfgs = glob.glob(os.path.expanduser(
        "~/.cache/huggingface/hub/models--hexgrad--Kokoro-82M/snapshots/*/config.json"))
    if not cfgs:
        return None, "kokoro config.json not in the HF cache - NOT RUN"
    import me_phonemes as mp
    vocab = json.load(open(cfgs[0], encoding="utf-8"))["vocab"]
    sample = ("And God seide, Liyt be maad. Y schal distruye the wisdom of "
              "wise men; awey, merci, yatis, sqware, Amalech, worldis.")
    bad = sorted({c for c in mp.to_ipa(sample) if c not in vocab and c != " "})
    return not bad, f"symbols outside vocab: {bad}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--narrate", default=str(HERE / "narrate.py"))
    a = ap.parse_args()
    # ONE load: narrate re-wraps sys.stdout at import, and a second import
    # closes the first wrapper's buffer (ValueError: I/O on closed file).
    narrate = load(a.narrate, "narrate_t")
    results = [("request carries ipa", *check_request(narrate)),
               ("header skips ipa", *check_header(narrate)),
               ("phonemes", *check_phonemes()),
               ("vocab", *check_vocab())]
    rc = 0
    for name, ok, msg in results:
        tag = "PASS" if ok else ("NOT RUN" if ok is None else "FAIL")
        print(f"{tag:8} {name}: {msg}")
        if ok is not True:
            rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
