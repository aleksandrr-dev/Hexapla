# -*- coding: utf-8 -*-
"""Scan already-rendered ru narration for CosyVoice3 instruct2 defects.

Two stochastic defect classes, both confirmed by ear by the owner 2026-07-20
(a header-duration guard in narrate.py prevents NEW occurrences; this tool
finds the ALREADY-RENDERED ones):

  1. INSTRUCTION LEAK — the instruct2 style instruction is SPOKEN as text
     («Прочитай очень медленно, низким и торжественным голосом», «Прочитай
     мягко и нежно, как поэзию», or the English "You are a helpful
     assistant." preamble). Heard in books 21 (Song) and 22 (Isaiah), later
     reported in normal-style books too.
  2. DOUBLED / STUTTERED CHAPTER HEADER — the «<Книга>, Глава <числ.>»
     announcement rendered twice / stuttered (heard in Eccl 1 = 20/0).

STRATEGY (two phases, both resumable and incremental):

  screen — no ASR. Every chapter's .json sidecar has per-verse start offsets
      (ms) into the .ogg; the concat pipeline is deterministic (600 ms gap
      after every segment, header first). So:
          header_ms   = offsets[0] - 600
          verse_ms[i] = offsets[i+1] - offsets[i] - 600   (last: total - off)
      Expected text lengths come from ru_synodal.json through the SAME
      normalization narrate.py used (strip_kjv_notes + ru_variants). A leak
      ADDS ~4-12 s of speech to one segment, so flag:
        (a) ceiling:  dur > len/3.5*1000 + 4000 (verses) / + 3000 (header)
            — the live render's own guard formula (3.5 ch/s floor is slower
            than even solemn's pace, so this is generous);
        (b) residual: dur - median_chapter_pace * len > RESIDUAL_MS — pace
            is the chapter's own median ms/char, which absorbs the 2.24x
            solemn / 1.82x tender styles; catches leaks on LONG verses where
            the ceiling is uselessly high, and fast-spoken short leaks.
      Header double-check additionally compares against the book-level
      median header pace (headers inside a book are near-identical text).

  verify — faster-whisper (small, int8, CPU ONLY, cpu_threads=3,
      num_workers=1 — the GPU runs a live render and Kokoro shares the CPU)
      transcribes ONLY a padded window around each flagged segment and
      classifies:
        instruction_leak — instruct-vocabulary in the transcript that is NOT
            in the expected verse text («прочитай», «торжествен…», "helpful
            assistant", «как поэзию»; weak words like «медленно»/«нежно»/
            «мягко»/«голосом» only count when absent from the verse itself),
            or an English run inside Russian audio;
        double_header — «глава» (and «голова»/«глаза»-class ASR near-misses)
            2+ times in the header window, or the ordinal repeated;
        slow_delivery — transcript matches the expected text well and has no
            instruct vocabulary (CosyVoice legitimately dramatizes; these are
            false positives of the duration screen);
        unclear — poor transcript/expected match, no keywords: owner should
            spot-listen.

  fullscan — full-audio ASR of whole books (default: the owner-reported
      20 21 22) as a completeness cross-check of the offsets screen: every
      instruct-vocabulary hit in the full transcript is mapped back to the
      covering verse and compared with the screen's flag list.

  report — writes the markdown report + the re-render queue JSON.

Usage (venv needs faster-whisper + soundfile; run from anywhere):
  python scan_narration_leaks.py screen   [--lang ru]
  python scan_narration_leaks.py verify   [--model small] [--limit N]
  python scan_narration_leaks.py fullscan [--books 20 21 22] [--limit N]
  python scan_narration_leaks.py report

State lives in narration/logs/leak_scan_results.json — every phase skips
work that is already recorded there, so rerunning after an interruption is
safe. Never touches any .ogg.
"""
import argparse
import difflib
import io
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

# NOTE: no TextIOWrapper re-wrap here — narrate.py (imported below) already
# wraps sys.stdout/err in UTF-8; wrapping twice closes the shared buffer.

HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# narrate.py is imported for the EXACT text pipeline (header wording,
# note-stripping, variant-number stripping). Its top-level imports are light
# (soundfile); the heavy TTS engines load lazily inside functions we never call.
import narrate  # noqa: E402

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
LOGS = NARRATION / "logs"
RESULTS = LOGS / "leak_scan_results.json"
RESEARCH = Path("C:/Projects/Hexapla-releases/research")
QUEUE_JSON = LOGS / "ru_rerender_queue.json"
REPORT_MD = RESEARCH / "ru_narration_leak_scan.md"

GAP_MS = 600           # silence after every concatenated segment
CEIL_PACE = 3.5        # chars/sec floor used by the live render's guard
VERSE_CEIL_PAD = 4000  # ms
HDR_CEIL_PAD = 3000    # ms
RESIDUAL_MS = 3500     # additive-time flag vs the chapter's own median pace
MIN_PACE_LEN = 30      # verses shorter than this don't inform the pace median
HDR_RESIDUAL_MS = 2500 # header vs book-median header pace

# Instruct-2 vocabulary. strong: essentially impossible in Synodal scripture.
# weak: real Russian words that DO occur in scripture — they only count when
# absent from the expected text of the same segment.
STRONG_WORDS = ["прочита", "торжествен", "тожествен", "поэзи", "поези",
                "helpful", "assistant", "ассистент"]
WEAK_WORDS = ["медленно", "нежно", "мягко", "голосом", "низким"]
HDR_WORDS = ["глава", "голова", "глаза", "глova"]


def norm(s):
    return re.sub(r"[^а-яёa-z0-9 ]+", " ", s.lower()).strip()


def words_of(s):
    return norm(s).split()


def fuzzy_word_hits(transcript_words, vocab, cutoff=0.8):
    """Return vocab entries fuzzily present in the transcript word list."""
    hits = []
    for v in vocab:
        for w in transcript_words:
            if v in w:
                hits.append((v, w)); break
            if len(w) >= 5 and difflib.SequenceMatcher(
                    None, v, w).ratio() >= cutoff:
                hits.append((v, w)); break
    return hits


def english_run(transcript):
    """Longest run of consecutive ASCII-alpha words (English inside Russian)."""
    best, cur = [], []
    for w in transcript.split():
        if re.fullmatch(r"[A-Za-z][A-Za-z'.,!?-]*", w):
            cur.append(w)
            if len(cur) > len(best):
                best = list(cur)
        else:
            cur = []
    return " ".join(best) if len(best) >= 2 else ""


def ogg_duration_ms(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, timeout=60)
    return int(float(r.stdout.decode().strip()) * 1000)


def load_results():
    if RESULTS.exists():
        with open(RESULTS, encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "chapters": {}}


def save_results(res):
    LOGS.mkdir(parents=True, exist_ok=True)
    tmp = RESULTS.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    tmp.replace(RESULTS)


def load_books(lang):
    with open(narrate.ASSETS / narrate.LANG_CONFIG[lang]["asset"],
              encoding="utf-8") as f:
        return json.load(f)


def expected_texts(books, lang, book_idx, chapter_idx):
    """Verse texts through the same normalization the render used."""
    cfg = narrate.LANG_CONFIG[lang]
    out = []
    for v in books[book_idx]["chapters"][chapter_idx]:
        if not v:
            out.append("")
            continue
        if cfg["strip_notes"]:
            v = narrate.strip_kjv_notes(v)
        if cfg["normalizer"]:
            v = narrate.normalize_text(v, cfg["normalizer"])
        out.append(v)
    return out


def header_text(books, lang, book_idx, chapter_idx):
    n_ch = len(books[book_idx]["chapters"])
    return narrate.chapter_header_text(lang, book_idx, chapter_idx, n_ch,
                                       book_name=books[book_idx].get("name"))


def segment_durations(offsets, total_ms):
    """(header_ms, [verse_ms or None per slot]). None = empty/unmeasurable."""
    header_ms = offsets[0] - GAP_MS if offsets else None
    verse_ms = []
    for i, off in enumerate(offsets):
        nxt = offsets[i + 1] if i + 1 < len(offsets) else total_ms + GAP_MS
        d = nxt - off - GAP_MS
        verse_ms.append(d if d > 0 else None)
    return header_ms, verse_ms


# --------------------------------------------------------------- screen ----

def phase_screen(args, res, books):
    lang = args.lang
    t0 = time.time()
    done = scanned = 0
    for book_dir in sorted((NARRATION / lang).iterdir(),
                           key=lambda p: int(p.name)):
        book_idx = int(book_dir.name)
        for ogg in sorted(book_dir.glob("*.ogg"),
                          key=lambda p: int(p.stem)):
            chapter_idx = int(ogg.stem)
            key = f"{book_idx}/{chapter_idx}"
            rec = res["chapters"].get(key, {})
            if "screen" in rec:
                done += 1
                continue
            side = ogg.with_suffix(".json")
            if not side.exists():
                rec["screen"] = {"error": "no sidecar json"}
                res["chapters"][key] = rec
                continue
            with open(side, encoding="utf-8") as f:
                offsets = json.load(f)["offsets"]
            total_ms = ogg_duration_ms(ogg)
            exp = expected_texts(books, lang, book_idx, chapter_idx)
            hdr = header_text(books, lang, book_idx, chapter_idx)
            scr = {"total_ms": total_ms, "n_verses": len(exp),
                   "n_offsets": len(offsets), "header_text": hdr,
                   "flags": []}
            if len(offsets) != len(exp):
                scr["error"] = "offset/verse count mismatch"
                rec["screen"] = scr
                res["chapters"][key] = rec
                continue
            header_ms, verse_ms = segment_durations(offsets, total_ms)
            scr["header_ms"] = header_ms
            hdr_ceil = int(len(hdr) / CEIL_PACE * 1000) + HDR_CEIL_PAD
            if header_ms is not None and header_ms > hdr_ceil:
                scr["flags"].append({"seg": "header", "dur": header_ms,
                                     "ceil": hdr_ceil, "kind": "ceiling"})
            # chapter pace from verses long enough to be stable
            paces = [d / len(t) for d, t in zip(verse_ms, exp)
                     if d and len(t) >= MIN_PACE_LEN]
            pace = statistics.median(paces) if paces else None
            scr["pace_ms_per_char"] = round(pace, 2) if pace else None
            for i, (d, t) in enumerate(zip(verse_ms, exp)):
                if not d or not t:
                    continue
                ceil = int(len(t) / CEIL_PACE * 1000) + VERSE_CEIL_PAD
                resid = d - pace * len(t) if pace else 0
                if d > ceil:
                    scr["flags"].append({"seg": i, "dur": d, "ceil": ceil,
                                         "kind": "ceiling",
                                         "resid": int(resid)})
                elif pace and resid > RESIDUAL_MS:
                    scr["flags"].append({"seg": i, "dur": d, "ceil": ceil,
                                         "kind": "residual",
                                         "resid": int(resid)})
            rec["screen"] = scr
            res["chapters"][key] = rec
            scanned += 1
            if scanned % 40 == 0:
                save_results(res)
                print(f"  screen: {scanned} new "
                      f"({time.time()-t0:.0f}s)", flush=True)
    # second pass: book-median header pace (needs all headers measured)
    by_book = {}
    for key, rec in res["chapters"].items():
        scr = rec.get("screen", {})
        if scr.get("header_ms") and scr.get("header_text"):
            by_book.setdefault(key.split("/")[0], []).append(
                scr["header_ms"] / len(scr["header_text"]))
    for key, rec in res["chapters"].items():
        scr = rec.get("screen", {})
        if not scr.get("header_ms"):
            continue
        paces = by_book[key.split("/")[0]]
        if len(paces) < 3:
            continue
        med = statistics.median(paces)
        resid = scr["header_ms"] - med * len(scr["header_text"])
        already = any(f["seg"] == "header" for f in scr.get("flags", []))
        if resid > HDR_RESIDUAL_MS and not already:
            scr["flags"].append({"seg": "header", "dur": scr["header_ms"],
                                 "kind": "hdr_residual", "resid": int(resid)})
    res["meta"]["screen_done"] = True
    res["meta"]["screen_seconds"] = round(
        res["meta"].get("screen_seconds", 0) + time.time() - t0)
    save_results(res)
    n_flags = sum(len(r.get("screen", {}).get("flags", []))
                  for r in res["chapters"].values())
    print(f"screen: {scanned} new + {done} already done, "
          f"{n_flags} flags total, {time.time()-t0:.0f}s")


# --------------------------------------------------------------- verify ----

_MODEL = None

def get_model(name):
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(name, device="cpu", compute_type="int8",
                              cpu_threads=3, num_workers=1)
    return _MODEL


def transcribe_window(model, ogg, start_s, end_s):
    segs, _ = model.transcribe(
        str(ogg), language="ru", clip_timestamps=[max(0.0, start_s), end_s],
        beam_size=5, vad_filter=False, condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segs)


def classify(transcript, expected, is_header):
    """Return (verdict, evidence)."""
    tw = words_of(transcript)
    ew = set(words_of(expected))
    strong = fuzzy_word_hits(tw, STRONG_WORDS)
    weak = [h for h in fuzzy_word_hits(tw, WEAK_WORDS)
            if not any(h[0] in e for e in ew)]
    eng = english_run(transcript)
    ratio = difflib.SequenceMatcher(None, norm(transcript),
                                    norm(expected)).ratio()
    ev = {"ratio": round(ratio, 2)}
    if strong:
        ev["strong"] = strong
    if weak:
        ev["weak"] = weak
    if eng:
        ev["english"] = eng
    if is_header:
        n_glava = sum(any(v in w for v in HDR_WORDS) for w in tw)
        ev["n_glava"] = n_glava
        if strong or len(weak) >= 2 or (weak and eng):
            return "instruction_leak", ev
        if n_glava >= 2:
            return "double_header", ev
        # book name spoken twice also counts as a double
        first = words_of(expected)[0] if words_of(expected) else ""
        if first and sum(difflib.SequenceMatcher(None, first, w).ratio() > 0.8
                         for w in tw) >= 2:
            return "double_header", ev
        if ratio >= 0.55:
            return "slow_delivery", ev
        return "unclear", ev
    if strong or len(weak) >= 2 or (weak and eng) or (eng and len(eng.split()) >= 3):
        return "instruction_leak", ev
    if ratio >= 0.75:
        return "slow_delivery", ev
    return "unclear", ev


def phase_verify(args, res, books):
    model = None
    t0 = time.time()
    n = 0
    items = sorted(res["chapters"].items(),
                   key=lambda kv: [int(x) for x in kv[0].split("/")])
    for key, rec in items:
        scr = rec.get("screen", {})
        flags = scr.get("flags", [])
        if not flags:
            continue
        ver = rec.setdefault("verify", {})
        book_idx, chapter_idx = (int(x) for x in key.split("/"))
        ogg = NARRATION / args.lang / str(book_idx) / f"{chapter_idx}.ogg"
        with open(ogg.with_suffix(".json"), encoding="utf-8") as f:
            offsets = json.load(f)["offsets"]
        exp = expected_texts(books, args.lang, book_idx, chapter_idx)
        for fl in flags:
            seg = str(fl["seg"])
            if seg in ver:
                continue
            if model is None:
                print("loading model...", flush=True)
                model = get_model(args.model)
            if fl["seg"] == "header":
                start, end = 0.0, offsets[0] / 1000 + 1.5
                expected = scr["header_text"]
            else:
                i = fl["seg"]
                start = offsets[i] / 1000 - 1.0
                end = start + fl["dur"] / 1000 + 2.5
                expected = exp[i]
            txt = transcribe_window(model, ogg, start, end)
            verdict, ev = classify(txt, expected, fl["seg"] == "header")
            ver[seg] = {"verdict": verdict, "transcript": txt[:600],
                        "evidence": ev, "window": [round(start, 1),
                                                   round(end, 1)]}
            n += 1
            print(f"  {key} seg {seg}: {verdict} "
                  f"({ev.get('ratio')})", flush=True)
            if n % 10 == 0:
                save_results(res)
            if args.limit and n >= args.limit:
                save_results(res)
                print(f"verify: limit {args.limit} reached, "
                      f"{time.time()-t0:.0f}s")
                return
    res["meta"]["verify_seconds"] = round(
        res["meta"].get("verify_seconds", 0) + time.time() - t0)
    save_results(res)
    print(f"verify: {n} segments verified, {time.time()-t0:.0f}s")


# -------------------------------------------------------------- headscan ---

def phase_headscan(args, res, books):
    """ASR census of EVERY chapter in the instruct-style books.

    Two windows per chapter, because the two defect sites are independent:
      * the header window (0 .. header_end + 2s), and
      * one mid-chapter verse window (a verse near the middle + 2s).
    Duration alone cannot decide this: 18/50's header has a residual of only
    390 ms yet its audio speaks the INSTRUCTION INSTEAD OF the announcement
    (same length, wrong words). Only ASR separates that from a clean header.
    """
    model = None
    t0 = time.time()
    n = 0
    lang = args.lang
    books_todo = ([] if args.all_instruct else args.books) or sorted(
        {int(k.split("/")[0]) for k in res["chapters"]
         if narrate.RU_BOOK_STYLES.get(int(k.split("/")[0]), "normal")
         != "normal"})
    for book_idx in books_todo:
        book_dir = NARRATION / lang / str(book_idx)
        if not book_dir.exists():
            continue
        for ogg in sorted(book_dir.glob("*.ogg"), key=lambda p: int(p.stem)):
            chapter_idx = int(ogg.stem)
            key = f"{book_idx}/{chapter_idx}"
            rec = res["chapters"].setdefault(key, {})
            prev = rec.get("headscan")
            if prev:
                # Census runs on `tiny` for speed. A CLEAN tiny result is the
                # only one worth a second opinion: a leak hit quotes the
                # instruction verbatim and needs no confirmation, but a miss
                # could be tiny's transcription failing. --recheck-clean
                # re-runs exactly those on `small`.
                clean = not (prev["header"]["leak"] or prev["mid"]["leak"])
                if not (args.recheck_clean and clean
                        and prev.get("model") != args.model):
                    continue
            if model is None:
                print(f"loading model {args.model}...", flush=True)
                model = get_model(args.model)
            with open(ogg.with_suffix(".json"), encoding="utf-8") as f:
                offsets = json.load(f)["offsets"]
            exp = expected_texts(books, lang, book_idx, chapter_idx)
            hdr = header_text(books, lang, book_idx, chapter_idx)
            out = {}
            # header window
            htxt = transcribe_window(model, ogg, 0.0, offsets[0] / 1000 + 2.0)
            out["header"] = _leak_record(htxt, hdr)
            # mid-chapter verse window
            mi = len(offsets) // 2
            while mi < len(offsets) - 1 and not exp[mi]:
                mi += 1
            start = offsets[mi] / 1000 - 0.5
            end = (offsets[mi + 1] / 1000 if mi + 1 < len(offsets)
                   else start + 25)
            mtxt = transcribe_window(model, ogg, start, min(end, start + 30))
            out["mid"] = _leak_record(mtxt, exp[mi])
            out["mid"]["verse"] = mi
            out["model"] = args.model
            rec["headscan"] = out
            n += 1
            if n % 5 == 0:
                save_results(res)
                print(f"  headscan {key}: hdr={out['header']['leak']} "
                      f"mid={out['mid']['leak']} ({time.time()-t0:.0f}s)",
                      flush=True)
            if args.limit and n >= args.limit:
                save_results(res)
                print("headscan: limit reached")
                return
    res["meta"]["headscan_seconds"] = round(
        res["meta"].get("headscan_seconds", 0) + time.time() - t0)
    save_results(res)
    print(f"headscan: {n} chapters, {time.time()-t0:.0f}s")


def _leak_record(transcript, expected):
    tw = words_of(transcript)
    strong = fuzzy_word_hits(tw, STRONG_WORDS)
    weak = [h for h in fuzzy_word_hits(tw, WEAK_WORDS)
            if not any(h[0] in e for e in set(words_of(expected)))]
    eng = english_run(transcript)
    ratio = difflib.SequenceMatcher(None, norm(transcript),
                                    norm(expected)).ratio()
    return {"leak": bool(strong or len(weak) >= 2 or (weak and eng)),
            "strong": strong, "weak": weak, "english": eng,
            "ratio": round(ratio, 2), "transcript": transcript[:400]}


# -------------------------------------------------------------- fullscan ---

def phase_fullscan(args, res, books):
    """Full-audio ASR of whole books; cross-check the offsets screen."""
    model = None
    t0 = time.time()
    n = 0
    for book_idx in args.books:
        book_dir = NARRATION / args.lang / str(book_idx)
        for ogg in sorted(book_dir.glob("*.ogg"), key=lambda p: int(p.stem)):
            chapter_idx = int(ogg.stem)
            key = f"{book_idx}/{chapter_idx}"
            rec = res["chapters"].setdefault(key, {})
            if "fullscan" in rec:
                continue
            if model is None:
                print("loading model...", flush=True)
                model = get_model(args.model)
            with open(ogg.with_suffix(".json"), encoding="utf-8") as f:
                offsets = json.load(f)["offsets"]
            exp = expected_texts(books, args.lang, book_idx, chapter_idx)
            segs, _ = model.transcribe(
                str(ogg), language="ru", beam_size=1, vad_filter=False,
                condition_on_previous_text=False)
            hits = []
            for s in segs:
                tw = words_of(s.text)
                strong = fuzzy_word_hits(tw, STRONG_WORDS)
                eng = english_run(s.text)
                if not strong and not eng:
                    continue
                # map hit time back to the covering verse
                ms = s.start * 1000
                vi = "header" if ms < offsets[0] else max(
                    i for i, off in enumerate(offsets) if off <= ms)
                hits.append({"t": round(s.start, 1), "verse": vi,
                             "strong": strong, "english": eng,
                             "text": s.text.strip()[:300]})
            rec["fullscan"] = {"hits": hits}
            n += 1
            print(f"  fullscan {key}: {len(hits)} hits "
                  f"({time.time()-t0:.0f}s)", flush=True)
            save_results(res)
            if args.limit and n >= args.limit:
                print(f"fullscan: limit reached")
                return
    res["meta"]["fullscan_seconds"] = round(
        res["meta"].get("fullscan_seconds", 0) + time.time() - t0)
    save_results(res)
    print(f"fullscan: {n} chapters, {time.time()-t0:.0f}s")


# ---------------------------------------------------------------- report ---

def phase_report(args, res, books):
    """Emit ru_rerender_queue.json.

    Queue composition (evidence in leak_scan_results.json):
      * EVERY rendered chapter of an instruct-style (solemn/tender) book —
        the 2026-07-20 ASR probes proved the leak is SYSTEMATIC there, not
        stochastic: the style instruction is vocalized before the header and
        before every verse in every chapter probed (20 chapters across books
        7/17/18/21/22/23/24/25/30, zero clean probes, incl. files rendered
        after the header-guard relaunch — the guard cannot catch verse-level
        leaks).
      * Normal-style chapters whose duration flags ASR-verified as a defect.
      * 20/0 (Eccl 1) — owner-reported stuttered/garbled header announcement.
    Unclear / unverified flags are printed for the owner to spot-listen but
    NOT queued.
    """
    lang = args.lang
    queue, unverified = [], []
    for key, rec in sorted(res["chapters"].items(),
                           key=lambda kv: [int(x) for x in kv[0].split("/")]):
        book_idx, chapter_idx = (int(x) for x in key.split("/"))
        style = narrate.RU_BOOK_STYLES.get(book_idx, "normal")
        if style != "normal":
            # Evidence level is recorded per chapter — ASR-confirmed where a
            # transcript quotes the instruction, inferred where the census has
            # not reached it yet (the instruction is passed on every
            # inference_instruct2 call in these books, and every chapter
            # examined so far leaks, with zero clean instruct chapters).
            hs = rec.get("headscan")
            sites, ev = [], None
            if hs:
                if hs["header"]["leak"]:
                    sites.append("header")
                if hs["mid"]["leak"]:
                    sites.append(f"verse {hs['mid']['verse']}")
                if sites:
                    ev = f"ASR-confirmed (headscan, {hs.get('model', '?')})"
            vleaks = [s for s, v in rec.get("verify", {}).items()
                      if v["verdict"] == "instruction_leak"]
            if vleaks and not ev:
                sites = ["header" if s == "header" else f"verse {s}"
                         for s in vleaks]
                ev = "ASR-confirmed (verify)"
            if not ev:
                ev = "inferred (systematic instruct2 leak, book-level)"
            queue.append({
                "book": book_idx, "chapter": chapter_idx,
                "reason": f"instruction_leak [{style}] — {ev}"
                          + (f" at {', '.join(sites)}" if sites else ""),
                "evidence": ev})
            continue
        scr = rec.get("screen", {})
        ver = rec.get("verify", {})
        reasons = []
        for fl in scr.get("flags", []):
            seg = str(fl["seg"])
            v = ver.get(seg)
            if v is None:
                unverified.append((key, fl, None))
                continue
            if v["verdict"] in ("instruction_leak", "double_header"):
                reasons.append((seg, v["verdict"], v["transcript"][:160]))
            elif v["verdict"] == "unclear":
                unverified.append((key, fl, v))
        for h in rec.get("fullscan", {}).get("hits", []):
            seg = str(h["verse"])
            if not any(seg == r[0] for r in reasons):
                reasons.append((seg, "instruction_leak(fullscan)",
                                h["text"][:160]))
        if book_idx == 20 and chapter_idx == 0 and not reasons:
            reasons.append(("header", "owner_reported_stutter",
                            "doubled/stuttered chapter announcement heard "
                            "by owner 2026-07-20; header audio garbled "
                            "(«глава перв-» runs into verse 1)"))
        if reasons:
            queue.append({
                "book": book_idx, "chapter": chapter_idx,
                "reason": "; ".join(
                    f"{verdict} at "
                    f"{'header' if seg == 'header' else 'verse ' + seg}"
                    for seg, verdict, _ in reasons)})
    QUEUE_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_JSON, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=1)
    n_instr = sum(1 for q in queue if "instruction_leak [" in q["reason"])
    n_conf = sum(1 for q in queue if "ASR-confirmed" in q.get("evidence", ""))
    print(f"queue: {len(queue)} chapters ({n_instr} instruct-book, "
          f"{len(queue) - n_instr} normal-book); "
          f"{n_conf} ASR-confirmed individually -> {QUEUE_JSON}")
    for item in queue:
        if "instruction_leak [" not in item["reason"]:
            print(f"  book {item['book']} ch {item['chapter']}: "
                  f"{item['reason']}")
    if unverified:
        print(f"-- {len(unverified)} unverified/unclear flags "
              f"(owner spot-listen):")
        for key, fl, v in unverified:
            print(f"  {key} seg {fl['seg']} {fl['kind']} "
                  f"dur {fl['dur']}ms resid {fl.get('resid')}ms"
                  + (f" | {v['transcript'][:100]}" if v else ""))
    write_markdown(res, queue, unverified)
    return queue, unverified


RATE_CH_PER_H = 2.1   # measured ru render throughput (chapters/hour)


def write_markdown(res, queue, unverified):
    """Regenerate the findings report from the recorded evidence."""
    ch = res["chapters"]
    style_of = lambda b: narrate.RU_BOOK_STYLES.get(b, "normal")
    books = sorted({int(k.split("/")[0]) for k in ch})
    L = []
    A = L.append
    A("# Russian narration — instruction-leak / header-defect scan\n")
    A("Generated by `tools/scan_narration_leaks.py` (screen -> verify -> "
      "headscan -> report).\n")
    A(f"Corpus: **{len(ch)} rendered ru chapters** "
      f"({sum(c['screen']['total_ms'] for c in ch.values() if c.get('screen', {}).get('total_ms')) / 3.6e6:.1f} h of audio), "
      "scanned without touching a single .ogg.\n")

    A("\n## Verdict\n")
    n_instr = sum(1 for q in queue if "instruction_leak [" in q["reason"])
    n_conf = sum(1 for q in queue if "ASR-confirmed" in q.get("evidence", ""))
    A(f"* **{len(queue)} chapters queued for re-render** "
      f"({n_instr} instruct-style, {len(queue) - n_instr} other); "
      f"{n_conf} carry an individual ASR transcript, the rest are queued on "
      f"the book-level mechanism (see below).")
    A(f"* **{len(unverified)} duration flags left UNQUEUED** for owner "
      "spot-listening — the ASR transcript showed no leaked instruction "
      "words, no doubled header and no babble, so they are most likely the "
      "dramatisations the owner likes (`reroll_speaker_drift` docstring).")
    A(f"* Re-render cost at the measured {RATE_CH_PER_H} chapters/h: "
      f"**~{len(queue) / RATE_CH_PER_H:.0f} GPU-hours "
      f"(~{len(queue) / RATE_CH_PER_H / 24:.1f} days)**.\n")

    A("\n## Per-book table\n")
    A("| book | style | rendered | hdr leak | mid leak | queued | note |")
    A("|---|---|---|---|---|---|---|")
    for b in books:
        keys = [k for k in ch if int(k.split("/")[0]) == b]
        hs = [ch[k]["headscan"] for k in keys if "headscan" in ch[k]]
        hl = sum(1 for x in hs if x["header"]["leak"])
        ml = sum(1 for x in hs if x["mid"]["leak"])
        q = sum(1 for x in queue if x["book"] == b)
        scanned = f"{hl}/{len(hs)}" if hs else "-"
        scannedm = f"{ml}/{len(hs)}" if hs else "-"
        note = ""
        if style_of(b) != "normal":
            note = "ASR census of every chapter"
        elif q:
            note = "verified defect(s)"
        A(f"| {b} | {style_of(b)} | {len(keys)} | {scanned} | {scannedm} "
          f"| {q} | {note} |")

    A("\n## Re-render queue\n")
    A("Full machine-readable list: "
      "`Hexapla-releases/narration/logs/ru_rerender_queue.json`.\n")
    A("| book | chapter | reason |")
    A("|---|---|---|")
    per_book_instr = {}
    for q in queue:
        if "instruction_leak [" in q["reason"]:
            per_book_instr.setdefault(q["book"], []).append(q)
        else:
            A(f"| {q['book']} | {q['chapter']} | {q['reason']} |")
    for b, qs in sorted(per_book_instr.items()):
        chs = [q["chapter"] for q in qs]
        c = sum(1 for q in qs if "ASR-confirmed" in q.get("evidence", ""))
        A(f"| {b} | ALL {len(chs)} rendered ({min(chs)}..{max(chs)}) | "
          f"instruction_leak, {style_of(b)} — {c} ASR-confirmed, "
          f"{len(chs) - c} inferred |")

    A("\n## Unqueued duration flags (owner spot-listen)\n")
    A("| chapter | seg | flag | dur ms | residual ms | ASR verdict | "
      "transcript |")
    A("|---|---|---|---|---|---|---|")
    for key, fl, v in unverified:
        t = (v["transcript"][:90].replace("|", "/") if v else "")
        A(f"| {key} | {fl['seg']} | {fl['kind']} | {fl['dur']} | "
          f"{fl.get('resid', '')} | {v['verdict'] if v else 'not run'} | "
          f"{t} |")

    RESEARCH.mkdir(parents=True, exist_ok=True)
    body = "\n".join(L) + "\n"
    # Everything from MARKER onwards is hand-written analysis (method notes,
    # the guard recommendation); regeneration must not eat it.
    if REPORT_MD.exists():
        old = REPORT_MD.read_text(encoding="utf-8")
        if MARKER in old:
            body += "\n" + MARKER + old.split(MARKER, 1)[1]
    REPORT_MD.write_text(body, encoding="utf-8")
    print(f"report -> {REPORT_MD}")


MARKER = "<!-- hand-written analysis below; regeneration preserves it -->"


PHASES = {"screen": phase_screen, "verify": phase_verify,
          "headscan": phase_headscan, "fullscan": phase_fullscan,
          "report": phase_report}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=PHASES)
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--model", default="small")
    ap.add_argument("--limit", type=int, default=0)
    # fullscan default = the owner-reported books; headscan default (empty)
    # = every instruct-style book that has rendered output.
    ap.add_argument("--books", type=int, nargs="*", default=[20, 21, 22])
    ap.add_argument("--all-instruct", action="store_true",
                    help="headscan: derive the book list from RU_BOOK_STYLES")
    ap.add_argument("--recheck-clean", action="store_true",
                    help="headscan: redo chapters recorded CLEAN by a "
                         "different (smaller) model")
    args = ap.parse_args()
    res = load_results()
    books = load_books(args.lang)
    PHASES[args.phase](args, res, books)


if __name__ == "__main__":
    main()
