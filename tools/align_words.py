# -*- coding: utf-8 -*-
"""Forced alignment of rendered narration -> per-WORD timings.

The app already highlights the current VERSE during recorded narration
(ReadingService.startVerseFollow reads the per-verse "o" offsets that
narrate.py writes). Device TTS goes further: it highlights the current WORD,
because the engine reports character ranges live via onRangeStart. Recorded
audio has no such callback, so this script recovers the same information
offline with a forced aligner, producing exactly what Playback.wordStart /
Playback.wordEnd already consume: CHARACTER RANGES INTO THE DISPLAYED VERSE
TEXT, paired with millisecond timestamps.

    python tools/align_words.py --set wbt --book 0 --chapter 0 --report
    python tools/align_words.py --set wbt              # whole set

Output: narration/<dir>/<book>/<chapter>.w.json, a sibling of the .ogg and the
existing .json offsets sidecar:

    {"v": [[[startMs, endMs, charStart, charEnd], ...],   # verse 0's words
           [...],                                          # verse 1's words
           ...]}

⚠ THREE THINGS THAT MAKE THIS HARDER THAN "RUN AN ALIGNER"

 1. THE AUDIO WAS NOT RENDERED FROM THE DISPLAYED TEXT. narrate.py strips
    margin notes and then runs a per-language normalizer (archaic English u/v
    rules, Russian stress marks, Slavonic digits). The aligner must align
    against the NORMALIZED text — that is what was actually spoken — and then
    map every word back to its character range in the DISPLAYED text, which is
    what the reader is looking at. Those two token streams are not always the
    same length (hyphen joining, dropped words), so the mapping goes through
    difflib and any word that cannot be mapped is emitted with charStart = -1
    rather than guessed. A guessed range highlights the wrong word.

 2. THE CHAPTER OGG IS A CONCATENATION. Verse i occupies
    [offsets[i], offsets[i+1] - 600ms); the 600ms is the silence gap
    concatenate_with_silence inserts. Aligning the whole chapter in one pass
    would let a single bad verse drag its neighbours' timings; per-verse
    slicing keeps errors local and lets a failed verse be dropped alone.

 3. MMS_FA'S TOKEN SET IS ESSENTIALLY a-z. Cyrillic is not in it, nor are the
    Swedish vowels. Latin-script sets fold accents directly; Cyrillic sets go
    through uroman, which is what MMS_FA was TRAINED on — so this is the
    model's intended input path rather than a workaround, and a hand-written
    transliteration table would be the wrong choice here.

Every verse carries a self-check: word ranges must be monotonically
increasing, must lie inside the verse's own audio slice, and must cover a
plausible fraction of it. Verses failing any check are emitted as null so the
app falls back to verse-level highlighting for them alone.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).parent.parent
ASSETS = REPO / "app" / "src" / "main" / "assets"
NARRATION = Path("C:/Projects/Hexapla-releases/narration")

# The gap concatenate_with_silence() puts between verses. Must match narrate.py.
SILENCE_MS = 600

# Mirrors build_audio_index_gen.py's SETS, plus the narrate.py language key so
# the same preprocessing (note stripping + normalizer) can be reproduced here.
SETS = {
    "wbt":     {"dir": "wbt", "asset": "en_webster.json",  "lang": "wbt",        "script": "latin"},
    "kxii":    {"dir": "sv",  "asset": "sv_karlxii.json",  "lang": "sv",         "script": "latin"},
    "gen1599": {"dir": "gnv", "asset": "en_geneva.json",   "lang": "gnv",        "script": "latin"},
    "tyn":     {"dir": "tyn", "asset": "en_tyndale.json",  "lang": "tyn",        "script": "latin"},
    "syn":     {"dir": "ru",  "asset": "ru_synodal.json",  "lang": "ru",         "script": "cyrillic"},
    "csl":     {"dir": "cu",  "asset": "cu_elizabeth.json","lang": "cu",         "script": "cyrillic"},
    # ⚠⚠ THE KJV SET WAS MISSING FROM THIS TABLE ENTIRELY UNTIL 2026-08-17, so
    # our own 245 KJV chapters (22 LibriVox-gap + 114 apocrypha + the rest)
    # could never be aligned — `--set` simply had no value that reached them.
    # Symptom on device: Sirach followed by VERSE while every other generated
    # set followed by WORD, with nothing anywhere reporting an error. The
    # `hexapla-audio-en` item carried 245 oggs and 0 .w.json.
    # ⚠ This is NOT the range(min(66, …)) bug (fixed below) — it is the same
    # family: a missing entry, like a canon-only loop, fails by producing
    # nothing while every command that WAS run still exits 0.
    # ⚠ dir "en" holds the standard <book>/<chapter>.ogg layout; only the
    # ARCHIVE.ORG item is flat (kjv_<book>_<ch>.ogg), which is why
    # build_audio_index_gen.py needs its `flat` option and this table does not.
    "kjv":     {"dir": "en",  "asset": "en_kjv.json",      "lang": "en",         "script": "latin"},
    # ⚠⚠ wyc IS THE ONLY SET WHOSE AUDIO WAS NOT RENDERED FROM GRAPHEMES.
    # narrate.py gives it `"ipa": "middle_english"`, so me_phonemes.to_ipa
    # produced the phoneme string and kokoro's G2P was bypassed entirely — the
    # voice speaks RECONSTRUCTED 1395 pronunciation. MMS_FA, meanwhile, aligns
    # audio against SPELLING. For every other set those two agree closely; here
    # they do not, and nothing in this file can make them agree.
    # ▶ So DO NOT trust a clean exit on this set. Probe one chapter with
    #   `--book 0 --chapter 0 --report` and read the null/unmapped counts before
    #   committing a full sweep: a set that aligns badly emits verses as null
    #   (by design — see the per-verse self-check) and the app then falls back
    #   to verse-level highlighting, which is exactly the outcome word-level
    #   alignment exists to avoid. A high null rate means this entry needs a
    #   phoneme-aware path, not a longer run.
    "wyc":     {"dir": "wyc", "asset": "enm_wycliffe.json","lang": "wyc",        "script": "latin"},
    # ⚠ ylt WAS MISSING TOO (added 2026-08-21) - the same omission as kjv above
    # and as the two render screens and the supervisor's two maps. A set that is
    # not in a table does not fail loudly; it becomes unreachable.
    "ylt":     {"dir": "ylt", "asset": "en_ylt.json",      "lang": "ylt",        "script": "latin"},
}

MARGIN_NOTE = re.compile(r"\{[^{}]*:[^{}]*\}")
MULTI_SPACE = re.compile(r"\s+")
# Word = a run of letters, with internal apostrophes and hyphens kept, so
# "God's" and "Beth-el" are one word each — the unit the reader sees.
WORD = re.compile(r"[^\W\d_]+(?:['\u2019\-][^\W\d_]+)*", re.UNICODE)


def display_text(raw):
    """Exactly what Bible.parseAsset shows the reader (Bible.kt L172-184)."""
    return MULTI_SPACE.sub(" ", MARGIN_NOTE.sub("", raw).replace("{", "").replace("}", "")).strip()


def spoken_text(raw, lang):
    """Exactly what narrate.py fed the voice, for this language."""
    import narrate
    cfg = narrate.LANG_CONFIG[lang]
    v = raw
    if cfg["strip_notes"]:
        v = narrate.strip_kjv_notes(v)
    if cfg["normalizer"]:
        v = narrate.normalize_text(v, cfg["normalizer"])
    return v


# uroman, loaded once on first non-Latin word. MMS_FA was TRAINED on uroman
# output, so this is the intended input path for it, not a workaround — which
# is why a hand-rolled Cyrillic table would be the wrong choice here even
# though it would look simpler and have no dependency.
_UROMAN = None
_UROMAN_CACHE = {}
UROMAN_LCODE = {"ru": "rus", "cu": "chu"}


def romanize(word, lang):
    global _UROMAN
    key = (word, lang)
    hit = _UROMAN_CACHE.get(key)
    if hit is not None:
        return hit
    if _UROMAN is None:
        import uroman as _u
        _UROMAN = _u.Uroman()
    # Romanized PER WORD, never per verse: uroman splits and joins around
    # punctuation, and a word-count change between the spoken text and its
    # romanization would silently shift every later word's timing by one.
    out = _UROMAN.romanize_string(word, lcode=UROMAN_LCODE.get(lang))
    _UROMAN_CACHE[key] = out
    return out


def align_key(word, script="latin", lang=None):
    """Fold a word onto the MMS_FA token set, or return None.

    HYPHEN IS THE BLANK TOKEN in MMS_FA's dictionary ('-' maps to id 0), so it
    must be REMOVED, not kept: passing it through makes forced_align reject the
    ENTIRE verse ("targets shouldn't contain blank index"). "Beth-el" folds to
    "bethel", which is what the voice says anyway; the printed hyphen is still
    covered by the highlight, because the character range comes from the
    DISPLAY text, never from this key.

    Latin script is folded directly: accents are decomposed and dropped
    (Swedish a-ring / a-diaeresis / o-diaeresis all collapse), which is what
    the MMS romanization does for those languages too. Non-Latin scripts go
    through uroman first — Russian stress marks vanish there for free, since
    they are combining accents.

    A word that leaves no usable characters is unalignable and is skipped
    rather than substituted.
    """
    if script != "latin":
        word = romanize(word, lang)
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    w = w.replace("\u2019", "'").replace("\u00df", "ss")
    w = re.sub(r"[^a-z']", "", w)
    return w or None


def map_tokens(spoken_words, display_words, script="latin", lang=None):
    """spoken index -> display index, via difflib; None where unmappable.

    Equal-length is the common case and short-circuits. Where the normalizer
    changed the token count (Geneva joins "Nebuchad-nezzar", note stripping
    drops words) only the matching blocks are trusted; everything inside a
    replace/insert/delete opcode maps to None and loses its highlight rather
    than acquiring a wrong one.
    """
    if len(spoken_words) == len(display_words):
        return list(range(len(spoken_words)))
    from difflib import SequenceMatcher
    a = [align_key(w, script, lang) or w.lower() for w in spoken_words]
    b = [align_key(w, script, lang) or w.lower() for w in display_words]
    out = [None] * len(a)
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                out[i1 + k] = j1 + k
    return out


class Aligner:
    """Lazily-loaded MMS_FA forced aligner. CPU by default — the GPU belongs
    to whatever render is running."""

    def __init__(self, device="cpu"):
        import torch
        from torchaudio.pipelines import MMS_FA
        self.torch = torch
        self.device = torch.device(device)
        self.bundle = MMS_FA
        self.model = MMS_FA.get_model().to(self.device).eval()
        self.dictionary = MMS_FA.get_dict()
        self.sample_rate = MMS_FA.sample_rate

    def align(self, waveform, keys):
        """waveform: 1-D float tensor at self.sample_rate. keys: list of folded
        words. Returns [(startSec, endSec)] per word, or None if the model
        cannot represent the text."""
        torch = self.torch
        tokens = []
        spans = []          # (first token index, token count) per word
        for k in keys:
            ids = [self.dictionary[c] for c in k if c in self.dictionary]
            if not ids:
                return None
            spans.append((len(tokens), len(ids)))
            tokens.extend(ids)
        if not tokens:
            return None
        import torchaudio.functional as AF
        with torch.inference_mode():
            emission, _ = self.model(waveform.unsqueeze(0).to(self.device))
            targets = torch.tensor([tokens], dtype=torch.int32, device=self.device)
            try:
                aligned, scores = AF.forced_align(emission, targets, blank=0)
            except RuntimeError:
                # ⚠⚠ CTC CANNOT ALIGN MORE TARGET TOKENS THAN IT HAS FRAMES, and
                # torchaudio raises rather than returning — so ONE bad verse used
                # to kill the WHOLE SWEEP. Symptom seen 2026-08-20 on tyn 42/15:
                #   "targets length is too long for CTC. Found log_probs length:
                #    114, targets length: 124"
                # 114 frames at MMS_FA's 20 ms = 2.28 s of audio for 124 characters
                # (~54 chars/s, about 4x real speech), i.e. the RENDER truncated
                # that verse. The supervisor then restarted the sweep every 10 min,
                # it hit the same chapter, and it died again — **114 chapters sat
                # unaligned for 80 minutes with a ticking log and a live
                # supervisor.** A crash loop looks exactly like slow progress.
                # This is NOT a reason to widen the alignment: a verse whose audio
                # is too short for its text is a DEFECTIVE RENDER, and the honest
                # outcome is the null that already exists here — the verse degrades
                # to verse-level highlighting and the chapter still aligns.
                # ▶ The real defect is upstream. Find such verses with
                #   tools/tyn_short_verses.py, and RE-RENDER them.
                return None
        # merge_tokens collapses the per-frame labels into one span per TARGET
        # token, in target order — so span index i is tokens[i]. Doing this by
        # hand (counting non-blank runs) miscounts legitimately repeated
        # letters, e.g. the two l's in "all".
        token_spans = AF.merge_tokens(aligned[0], scores[0], blank=0)
        if len(token_spans) != len(tokens):
            return None
        # frames -> seconds, derived from the emission rather than assumed
        ratio = waveform.size(0) / emission.size(1) / self.sample_rate
        out = []
        for start_tok, n_tok in spans:
            group = token_spans[start_tok:start_tok + n_tok]
            if not group:
                out.append(None)
                continue
            out.append((group[0].start * ratio, group[-1].end * ratio))
        return out


def load_chapter_audio(ogg_path, target_rate):
    """Decode the chapter ogg to a mono float tensor at target_rate.

    Via ffmpeg rather than torchaudio.load: torchaudio 2.11 removed its own
    decoders and defers to torchcodec, which is not installed. ffmpeg is
    already a hard dependency of the render pipeline, and it also does the
    downmix and resample in one pass.
    """
    import subprocess
    import numpy as np
    import torch
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(ogg_path),
         "-f", "f32le", "-ac", "1", "-ar", str(target_rate), "-"],
        capture_output=True, timeout=300,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed: {r.stderr.decode()[-300:]}")
    return torch.from_numpy(np.frombuffer(r.stdout, dtype=np.float32).copy())


def align_chapter(aligner, set_cfg, book_idx, chapter_idx, verses_raw, report=False):
    d = NARRATION / set_cfg["dir"] / str(book_idx)
    ogg = d / f"{chapter_idx}.ogg"
    side = d / f"{chapter_idx}.json"
    if not ogg.exists() or not side.exists():
        return None, "missing ogg or sidecar"
    offsets = json.loads(side.read_text(encoding="utf-8"))["offsets"]
    if len(offsets) != len(verses_raw):
        return None, f"offsets {len(offsets)} != verses {len(verses_raw)}"

    wav = load_chapter_audio(ogg, aligner.sample_rate)
    total_ms = wav.size(0) * 1000.0 / aligner.sample_rate

    out = []
    stats = {"ok": 0, "null": 0, "unmapped": 0, "words": 0}
    for i, raw in enumerate(verses_raw):
        disp = display_text(raw or "")
        if not disp:
            out.append(None)
            stats["null"] += 1
            continue
        start_ms = offsets[i]
        end_ms = (offsets[i + 1] - SILENCE_MS) if i + 1 < len(offsets) else total_ms
        if end_ms - start_ms < 200 or end_ms > total_ms + 50:
            out.append(None)
            stats["null"] += 1
            continue
        s = int(start_ms * aligner.sample_rate / 1000)
        e = min(int(end_ms * aligner.sample_rate / 1000), wav.size(0))
        seg = wav[s:e]

        spoken = spoken_text(raw, set_cfg["lang"])
        spoken_words = WORD.findall(spoken)
        disp_matches = list(WORD.finditer(disp))
        keys = [align_key(w, set_cfg["script"], set_cfg["lang"]) for w in spoken_words]
        keep = [j for j, k in enumerate(keys) if k]
        if not keep:
            out.append(None)
            stats["null"] += 1
            continue

        spans = aligner.align(seg, [keys[j] for j in keep])
        if spans is None:
            out.append(None)
            stats["null"] += 1
            continue

        idx_map = map_tokens(spoken_words, [m.group(0) for m in disp_matches],
                             set_cfg["script"], set_cfg["lang"])
        words = []
        last_end = -1
        broken = False
        for pos, j in enumerate(keep):
            sp = spans[pos]
            if sp is None:
                continue
            dj = idx_map[j] if j < len(idx_map) else None
            ws = int(start_ms + sp[0] * 1000)
            we = int(start_ms + sp[1] * 1000)
            if we < ws or ws < last_end - 1:
                broken = True
                break
            last_end = we
            if dj is None:
                stats["unmapped"] += 1
                continue
            m = disp_matches[dj]
            words.append([ws, we, m.start(), m.end()])
        if broken or not words:
            out.append(None)
            stats["null"] += 1
            continue
        # Coverage: aligned words should span most of the verse's audio. A
        # collapsed alignment (everything crammed into the first second) is the
        # failure this catches — it looks fine word-by-word.
        covered = words[-1][1] - words[0][0]
        if covered < 0.5 * (end_ms - start_ms):
            out.append(None)
            stats["null"] += 1
            continue
        out.append(words)
        stats["ok"] += 1
        stats["words"] += len(words)

        if report and i < 3:
            print(f"    v{i+1}: " + "  ".join(
                f"{disp[w[2]:w[3]]}@{w[0]}" for w in words[:8]))

    return {"v": out}, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=sorted(SETS))
    ap.add_argument("--book", type=int)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    cfg = SETS[args.set]
    sys.path.insert(0, str(REPO / "tools"))
    books = json.loads((ASSETS / "bibles" / cfg["asset"]).read_text(encoding="utf-8"))
    if isinstance(books, dict):
        books = books["books"]

    aligner = Aligner(args.device)

    targets = []
    if args.book is not None:
        chs = [args.chapter] if args.chapter is not None else range(len(books[args.book]["chapters"]))
        targets = [(args.book, c) for c in chs]
    else:
        # ⚠⚠ THIS USED TO BE range(min(66, len(books))) — CANON ONLY — and it
        # silently under-covered every set that narrates its deuterocanon.
        # Caught 2026-08-15: csl aligned 1192 of its 1362 chapters and syn
        # reported ok:0, BOTH exiting 0. A canon-only sweep looks exactly like
        # success when the extra books are the ones missing.
        # The sweep now covers every non-empty book the ASSET has; slots with
        # no text are skipped below, and chapters with no rendered audio are
        # skipped by align_chapter, so this is safe for canon-only sets too.
        for b in range(len(books)):
            for c in range(len(books[b]["chapters"])):
                targets.append((b, c))

    total = {"ok": 0, "null": 0, "unmapped": 0, "words": 0}
    for b, c in targets:
        out_path = NARRATION / cfg["dir"] / str(b) / f"{c}.w.json"
        if out_path.exists() and not args.force:
            continue
        verses = books[b]["chapters"][c]
        if not verses:
            continue
        res, stats = align_chapter(aligner, cfg, b, c, verses, report=args.report)
        if res is None:
            print(f"  [{b}/{c}] SKIP: {stats}")
            continue
        out_path.write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
        for k in total:
            total[k] += stats[k]
        print(f"  [{b}/{c}] verses ok {stats['ok']} null {stats['null']} "
              f"words {stats['words']} unmapped {stats['unmapped']}")

    print(f"TOTAL {total}")


if __name__ == "__main__":
    main()
