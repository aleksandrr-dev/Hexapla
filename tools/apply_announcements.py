# -*- coding: utf-8 -*-
"""Splice verified announcements into the already-rendered ru chapter oggs.

The verses in `narration/ru` are good and cost days of GPU. Only the first few
seconds of each file — the spoken «Бытие, Глава первая» — are defective. This
replaces exactly that head, assembled from the verified component library
(build_announcements.py), and leaves every verse untouched.

    python tools/apply_announcements.py --check          # what would change
    python tools/apply_announcements.py --book 0 --chapter 0
    python tools/apply_announcements.py                  # all 1,192

⚠ ORIGINALS ARE NEVER OVERWRITTEN IN PLACE. Every chapter's ogg/json/w.json is
copied to `narration/ru_pre_announce/` before its first splice, and every run
reads its SOURCE from that backup. So this is idempotent and re-runnable: a
second pass re-splices the pristine original rather than stacking a second
Opus generation on an already-spliced file, and a bad announcement can be
fixed by rebuilding one component and running again.

⚠ THE VERSE AUDIO IS RE-ENCODED ONCE, AT 48 kbps. The body is cut at
offsets[0] and carried across as decoded samples; only the concatenated result
is encoded. That is one extra Opus generation on the verses, which is the price
of not re-rendering 1,192 chapters on the GPU for a 2-second defect. The
bitrate is 48k, NOT the render's 32k, for the same reason and by the same
owner's call as `repair_abrupt_verses.py` (2026-08-05): re-encoding at the
original bitrate compounds loss, so repaired chapters go out with headroom.
Encoding this at 32k measurably shrank a chapter from 1,194 KB to 800 KB.
(There is no lossless route — see that file's note on why `concat -c copy`
produces non-monotonic timestamps and breaks seek-to-verse.)

⚠ OFFSETS MOVE, AND THAT IS ALREADY SETTLED. An earlier draft of this file
padded the silence gap so verse 1 landed on its old timestamp, to keep the
index shipped in 1.6.3 valid. That is pointless here: `repair_abrupt_verses.py`
already shifted offsets across 927 chapters and `audio_index_gen.json` is being
rebuilt for 1.6.4 regardless. So the gap is a constant 600 ms everywhere, which
is what the renderer itself used and what keeps every chapter sounding alike.
Rebuild the index before the next release.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import soundfile as sf

import narrate

# ⚠⚠ SET-PARAMETERISED 2026-08-22. Defaults are ru so every existing
# invocation behaves identically; `--set ylt` points all three paths at the
# ylt set and its own library. A run must NEVER mix a library from one set
# with the oggs of another — the voices differ, and the splice would be
# silently audible rather than an error.
_ROOT = Path("C:/Projects/Hexapla-releases/narration")
SET = "ru"
NARR = _ROOT / "ru"
BACKUP = _ROOT / "ru_pre_announce"
LIB = _ROOT / "ru_announce_lib"


def _configure(set_key):
    """Point NARR/BACKUP/LIB at one narration set, and the builder with it."""
    global SET, NARR, BACKUP, LIB
    SET = set_key
    NARR = _ROOT / set_key
    BACKUP = _ROOT / f"{set_key}_pre_announce"
    LIB = _ROOT / f"{set_key}_announce_lib"
    import build_announcements as _ba
    _ba._configure(set_key)          # keeps ba.asr()/words_present() in-language
    global ASSET
    ASSET = _ASSET_DIR / narrate.LANG_CONFIG[set_key]["asset"]
    if not ASSET.exists():
        raise SystemExit(f"asset not found for set {set_key!r}: {ASSET}")
    return SET
# ⚠ Derived from the set's own LANG_CONFIG in _configure(); the literal below
# is only the ru default so an unconfigured import still resolves.
_ASSET_DIR = Path(__file__).parent.parent / "app/src/main/assets/bibles"
ASSET = _ASSET_DIR / "ru_synodal.json"

SR = 48000            # opus decodes at 48 kHz; everything is resampled to it
# Imported, never redefined: the owner reviews an assembled reel, so the pause
# he approves has to be the pause that ships.
from build_announcements import COMMA_MS          # noqa: E402
GAP_MS = 600          # silence before verse 1, as concatenate_with_silence used
BITRATE = "48k"       # see the docstring — matches repair_abrupt_verses.py
NO_WINDOW = getattr(narrate, "_NO_WINDOW", 0)


def load_components():
    """Every component, resampled once to 48 kHz, as float32 arrays."""
    comps = {}
    with tempfile.TemporaryDirectory() as tmp:
        for wav in sorted(LIB.glob("*.wav")):
            if wav.name.startswith("REVIEW"):
                continue
            out = Path(tmp) / wav.name
            r = subprocess.run(["ffmpeg", "-y", "-i", str(wav), "-ar", str(SR),
                                "-ac", "1", str(out)],
                               capture_output=True, creationflags=NO_WINDOW)
            if r.returncode != 0:
                raise SystemExit(f"resample failed for {wav.name}")
            a, _ = sf.read(str(out), dtype="float32")
            comps[wav.stem] = a.mean(1) if a.ndim > 1 else a
    return comps


def speech_rms(a, sr):
    """RMS of the ACTIVE part only.

    Matching whole-file RMS would make an announcement quieter in a chapter
    with long verses (more silence dragging the average down). The original
    header and verses shared ONE loudnorm pass over the concatenated chapter,
    so the level to match is the level of the speech itself.
    """
    win = max(1, sr // 50)
    env = np.array([float(np.sqrt((a[i:i + win] ** 2).mean()))
                    for i in range(0, max(1, len(a) - win), win)])
    if not len(env):
        return float(np.sqrt((a ** 2).mean()))
    active = env[env > 0.15 * env.max()]
    return float(np.sqrt((active ** 2).mean())) if len(active) else float(env.mean())


def build_header(comps, book_idx, chapter_idx, n_chapters):
    """Assemble «<Book>, Глава <N>» from components. Returns audio, or None."""
    bk = comps.get(f"book_{book_idx}")
    if bk is None:
        return None, f"missing component book_{book_idx}"
    if n_chapters == 1:
        return bk, None                      # «К Филимону» — no chapter said
    ch = comps.get(f"ch_{chapter_idx + 1}")
    if ch is None:
        return None, f"missing component ch_{chapter_idx + 1}"
    pause = np.zeros(int(SR * COMMA_MS / 1000), dtype="float32")
    return np.concatenate([bk, pause, ch]), None


def do_chapter(book_idx, chapter_idx, comps, n_chapters, dry=False):
    src_dir, dst_dir = BACKUP / str(book_idx), NARR / str(book_idx)
    ogg, js, wjs = (dst_dir / f"{chapter_idx}.ogg", dst_dir / f"{chapter_idx}.json",
                    dst_dir / f"{chapter_idx}.w.json")
    if not ogg.exists() or not js.exists():
        return None

    # Back up once, then always read the pristine original.
    src_dir.mkdir(parents=True, exist_ok=True)
    for f in (ogg, js, wjs):
        b = src_dir / f.name
        if f.exists() and not b.exists():
            shutil.copy2(f, b)

    src_ogg, src_js = src_dir / ogg.name, src_dir / js.name
    src_wjs = src_dir / wjs.name
    offsets = json.loads(src_js.read_text(encoding="utf-8"))["offsets"]
    old_t0 = offsets[0]

    hdr, err = build_header(comps, book_idx, chapter_idx, n_chapters)
    if hdr is None:
        return {"b": book_idx, "c": chapter_idx, "err": err}

    hdr_ms = len(hdr) / SR * 1000
    gap = GAP_MS
    new_t0 = int(round(hdr_ms + gap))
    delta = new_t0 - old_t0
    if dry:
        return {"b": book_idx, "c": chapter_idx, "hdr_ms": round(hdr_ms),
                "old_t0": old_t0, "new_t0": new_t0, "delta": delta}

    # ⚠ DECODE THROUGH FFMPEG, DO NOT TRUST soundfile's REPORTED RATE. An Ogg
    # Opus stream is always 48 kHz, but libsndfile reports the ORIGINAL INPUT
    # rate recorded in the Opus header — so chapters encoded from the render's
    # 24 kHz WAVs read back as 24000 while chapters re-encoded by
    # repair_abrupt_verses read as 48000, for files ffprobe agrees are both
    # 48 kHz. An equality check on that field rejected 535 of 1,192 chapters.
    with tempfile.TemporaryDirectory() as tmp:
        dec = Path(tmp) / "body.wav"
        r = subprocess.run(["ffmpeg", "-y", "-i", str(src_ogg), "-ar", str(SR),
                            "-ac", "1", str(dec)],
                           capture_output=True, creationflags=NO_WINDOW)
        if r.returncode != 0:
            return {"b": book_idx, "c": chapter_idx, "err": "decode failed"}
        body, sr = sf.read(str(dec), dtype="float32")
    body = body.mean(1) if body.ndim > 1 else body
    tail = body[int(old_t0 / 1000 * sr):]
    if len(tail) < sr:
        return {"b": book_idx, "c": chapter_idx, "err": "body shorter than offsets[0]"}

    # Match the announcement's level to the chapter's own speech, since the
    # body is already loudnorm'd and must not be normalized a second time.
    scale = speech_rms(tail, sr) / max(speech_rms(hdr, SR), 1e-9)
    hdr = np.clip(hdr * scale, -1.0, 1.0)

    out = np.concatenate([hdr, np.zeros(int(SR * gap / 1000), dtype="float32"), tail])
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp) / "c.wav"
        sf.write(str(w), (out * 32767).astype(np.int16), SR, subtype="PCM_16")
        r = subprocess.run(["ffmpeg", "-y", "-i", str(w), "-b:a", BITRATE,
                            "-c:a", "libopus", "-ac", "1", str(ogg)],
                           capture_output=True, creationflags=NO_WINDOW)
        if r.returncode != 0:
            shutil.copy2(src_ogg, ogg)       # never leave a broken chapter behind
            return {"b": book_idx, "c": chapter_idx,
                    "err": r.stderr.decode(errors="replace")[-200:]}

    js.write_text(json.dumps({"offsets": [o + delta for o in offsets]},
                             separators=(",", ":")), encoding="utf-8")
    if src_wjs.exists():
        w = json.loads(src_wjs.read_text(encoding="utf-8"))
        w["v"] = [None if v is None else [[a + delta, b + delta, cs, ce]
                                          for a, b, cs, ce in v] for v in w["v"]]
        wjs.write_text(json.dumps(w, separators=(",", ":")), encoding="utf-8")
    return {"b": book_idx, "c": chapter_idx, "hdr_ms": round(hdr_ms),
            "delta": delta, "ok": True}


def verify(todo, bible):
    """Transcribe the head of each FINISHED ogg and check it says the right thing.

    The end-to-end proof. Everything upstream is verified in isolation — the
    components by ASR, the splice by arithmetic — but only this reads back what
    a listener will actually hear out of the file that ships. It is also the
    check that catches a wiring mistake no component test can: the right audio
    assembled onto the WRONG chapter.
    """
    import build_announcements as ba
    bad = []
    for n, (bi, ci, n_ch) in enumerate(todo, 1):
        ogg = NARR / str(bi) / f"{ci}.ogg"
        t0 = json.loads((NARR / str(bi) / f"{ci}.json").read_text())["offsets"][0]
        # ⚠ INCLUDE 1.5 s OF VERSE 1. Whisper stops after the first utterance
        # on a short clip that ends in silence: the announcement alone came
        # back as «Бытие.» with «Глава шестая» — audibly present — simply not
        # transcribed. With the verse running on underneath, it transcribes
        # everything. The comparison is coverage-based to tolerate the extra.
        a, sr = sf.read(str(ogg), dtype="float32",
                        frames=int((t0 + 1500) / 1000 * SR))
        a = a.mean(1) if a.ndim > 1 else a
        with tempfile.TemporaryDirectory() as tmp:
            w = Path(tmp) / "h.wav"
            sf.write(str(w), (a * 32767).astype(np.int16), sr, subtype="PCM_16")
            heard = ba.asr(w)
        want = narrate.chapter_header_text(SET, bi, ci, n_ch,
                                           book_name=bible[bi]["name"])
        # Same spoken-form transform the builder used, or every numbered book
        # would be compared against the unspoken asset name and fail.
        _head = want.split(",")[0]
        want = want.replace(_head, ba.spoken_book_name(_head), 1)
        if ba.CFG["dative_epistles"] and bi in ba._DATIVE_EPISTLES:
            p = want.split(",")[0].split()
            want = want.replace(want.split(",")[0],
                                f"{p[0]} к {' '.join(p[1:])}" if len(p) > 1
                                else f"К {p[0]}", 1)
        ok, ratio, tail = ba.words_present(want, heard, subset=True)
        if not ok:
            bad.append((bi, ci, want, heard, round(ratio, 2), round(tail, 2)))
        if n % 100 == 0:
            print(f"  verified {n}/{len(todo)}, {len(bad)} suspect", flush=True)
    print(f"\n{len(todo)} chapters read back, {len(bad)} suspect")
    for bi, ci, want, heard, r, t in bad[:40]:
        print(f"  {bi}/{ci}: want {want!r} heard {heard!r} (r{r} tail{t})")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", type=int)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="ASR the head of each finished ogg (end-to-end proof)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--set", default="ru",
                    help="narration set (default ru — unchanged behaviour)")
    args = ap.parse_args()
    _configure(args.set)

    bible = json.loads(ASSET.read_text(encoding="utf-8"))
    comps = {}
    if not args.verify:                 # verify reads finished oggs, not clips
        comps = load_components()
        print(f"{len(comps)} components loaded")

    todo = []
    for bi in range(66):
        if args.book is not None and bi != args.book:
            continue
        n_ch = len(bible[bi]["chapters"])
        for ci in range(n_ch):
            if args.chapter is not None and ci != args.chapter:
                continue
            if (NARR / str(bi) / f"{ci}.ogg").exists():
                todo.append((bi, ci, n_ch))
    print(f"{len(todo)} chapters")

    if args.verify:
        verify(todo, bible)
        return

    res = []
    if args.check:
        for bi, ci, n in todo:
            res.append(do_chapter(bi, ci, comps, n, dry=True))
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(do_chapter, bi, ci, comps, n) for bi, ci, n in todo]
            for i, f in enumerate(futs, 1):
                res.append(f.result())
                if i % 50 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)

    res = [r for r in res if r]
    errs = [r for r in res if r.get("err")]
    deltas = [r["delta"] for r in res if "delta" in r]
    print(f"\n{len(res)} chapters, {len(errs)} errors")
    print(f"offset shift: min {min(deltas, default=0)} / max "
          f"{max(deltas, default=0)} ms  (rebuild audio_index_gen.json)")
    for e in errs[:20]:
        print(f"  ERR {e['b']}/{e['c']}: {e['err']}")
    if errs:
        print("⚠ chapters with errors keep their ORIGINAL audio (restored from backup)")


if __name__ == "__main__":
    main()
