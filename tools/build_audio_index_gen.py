# -*- coding: utf-8 -*-
"""Build app/src/main/assets/audio_index_gen.json from a rendered narration set.

Maps each generated translation's chapters to their archive.org stream URL +
per-verse offsets (ms). Consumed by AudioRepo.generated(); the app streams the
per-chapter .ogg from archive.org (one file per chapter). Offsets are carried
for a future verse-highlighting pass; v1 playback ignores them.

    python tools/build_audio_index_gen.py            # build + assert
    python tools/build_audio_index_gen.py --dry-run  # report only

Each set: narration/<id>/<bookIdx>/<chapterIdx>.ogg + matching .json sidecar
({"offsets":[ms,...]}). Hard-fails if a chapter's .ogg or sidecar is missing,
or if the chapter grid does not match the translation's bible asset.
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
ASSETS = Path(__file__).parent.parent / "app" / "src" / "main" / "assets"
OUT = ASSETS / "audio_index_gen.json"

# Each generated set. `tid` = the app translation id (the index is keyed by
# it; ReadingService looks up AudioRepo.generated(translationId)); `dir` = the
# narration output folder (may differ from tid); `partial` = index whatever
# chapters exist rather than requiring the full 1189 (for a Bible still
# rendering — the missing books fall back to TTS until a later index refresh).
SETS = [
    {"tid": "wbt", "dir": "wbt", "asset": "en_webster.json",
     "item": "hexapla-audio-webster-1833", "partial": False},
    # Swedish Karl XII 1703: narration folder 'sv', app id 'kxii'.
    # COMPLETE 2026-08-01 — 1189/1189 rendered, so `partial` flipped to False.
    # That makes the coverage assertion active: it hard-fails on any missing
    # .ogg or sidecar, which is exactly the check we want now that the set
    # claims completeness in the app and in its archive.org title.
    {"tid": "kxii", "dir": "sv", "asset": "sv_karlxii.json",
     "item": "hexapla-audio-karlxii-1703", "partial": False},
    # ── GENEVA 1599 — PREPARED 2026-07-31, ACTIVATE WHEN THE RENDER FINISHES ──
    # ⚠ tid is "gen1599" (the app id in Bible.kt), NOT "gnv" (the narration
    #   folder). Same tid/dir split as kxii — getting this wrong yields an
    #   index the app silently never looks up.
    # ✅ ACTIVATED 2026-08-01. Render finished 1189/1189; item uploaded
    #   (2379/2379 requests, 0 failed) and verified public — chapter URLs
    #   0/0.ogg, 42/0.ogg and 65/21.ogg all fetch HTTP 200.
    # Activation checklist lives in tools/GENEVA_AUDIO_RUNBOOK.md.
    # ⚠ dir points at the QUARANTINE, deliberately (2026-08-04). The archaic-
    #   spelling re-render moved narration/gnv aside to gnv_quarantine_archaic_
    #   spelling so the render could restart from zero under skip-existing. But
    #   archive.org still SERVES the old audio, and this index embeds the verse
    #   offsets users actually stream — so it must be built from the audio that
    #   is live, which is the quarantined set (byte-identical to the item).
    # ⚠ WHEN THE RE-RENDER FINISHES AND IS UPLOADED: point this back at "gnv"
    #   and REBUILD. The new audio has different offsets; leaving it here would
    #   ship verse highlighting that drifts against the audio being played.
    {"tid": "gen1599", "dir": "gnv_quarantine_archaic_spelling",
     "asset": "en_geneva.json",
     "item": "hexapla-audio-geneva-1599", "partial": False},

    # ── RUSSIAN SYNODAL — PREPARED 2026-08-02, ACTIVATE WHEN THE RENDER ENDS ──
    # Values below are checked against the tree; uncomment when ru is done.
    # ⚠ tid is "syn" (the app id in Bible.kt), dir is "ru" (the narration
    #   folder) — the same tid/dir split as kxii and gen1599.
    # ⚠ ru's canon is 1192 chapters, NOT 1189: Psalm 151, and Daniel 13-14 for
    #   the LXX additions. Do not sanity-check it against the KJV total.
    # ⚠ ru_synodal.json has 83 slots of which 78 are NON-EMPTY — the Synodal
    #   deuterocanon is real text, unlike Geneva's empty apocrypha slots. The
    #   canon-only restriction in build_set() is what makes `partial: False`
    #   reachable here; without it a complete canon fails the guard.
    # ⚠ Do NOT activate before the leak re-render is finished AND the set has
    #   been ASR spot-checked. Duration heuristics cannot see an instruction
    #   leak — that defect replaces the verse rather than lengthening it.
    # ✅ ACTIVATED 2026-08-04. Render 1192/1192; leak screen over every current
    #   chapter plus an ASR headscan census of all 487 instruct-style chapters
    #   found 0 header leaks and 0 genuine mid-verse leaks (the only two hits
    #   were the keyword matcher firing on scripture's own words — «прочитать»
    #   in Daniel 5:15, «торжествуй» in Zechariah 9:9 — both matching the
    #   expected verse at ratio 0.95+). Uploaded: 1192 oggs + 1192 sidecars
    #   verified present ON THE ITEM, complete title verified live.
    # ★ APOCRYPHA ACTIVATED 2026-08-15, after the deuterocanon render (170
    #   chapters, slots 66-77) finished, passed QA fail-0 and was UPLOADED and
    #   file-probe-verified on the item. Same opt-in as csl below.
    # ⚠ THE ORDER MATTERS: adding this flag BEFORE the upload makes the
    #   completeness guard demand 1362 chapters that are not yet published, so
    #   it fails the build — and blocks csl's index too.
    # ⚠ Without it those 170 chapters are UNREACHABLE: no index entry, so the
    #   app silently falls back to TTS while correct audio sits on archive.org.
    {"tid": "syn", "dir": "ru", "asset": "ru_synodal.json",
     "item": "hexapla-audio-synodal-1876", "partial": False,
     "apocrypha": True},
    # ── CHURCH SLAVONIC 1757 — PREPARED 2026-08-07, ACTIVATE WHEN THE RENDER
    #    FINISHES (uncomment). Same prepare-then-activate pattern as Geneva.
    # ⚠⚠ tid is "csl" — the app id in Bible.kt — NOT "cu", which is only the
    #    narration FOLDER name. Getting this wrong yields an index the app
    #    silently never looks up: no error, no audio, nothing to debug. This is
    #    the third set with a tid/dir split (kxii/sv, gen1599/gnv, csl/cu).
    # ⚠ The asset is cu_elizabeth.json and its canon runs to 1,192 chapters
    #    like ru — Psalm 151 plus Daniel 13-14 — NOT the 1,189 of the
    #    Protestant sets. Do not assume 1189 anywhere.
    # ★ ACTIVATED 2026-08-14 WITH "apocrypha": True — owner: "Apocrypha needs
    #   to be built in app too so it can be heard." cu renders all 78 non-empty
    #   books (1192 canon + 170 deuterocanon = 1362). Canon-only indexing would
    #   have left those 170 chapters silently on TTS.
    # ⚠ partial stays False: the guard must still prove ALL 1362 are present.
    {"tid": "csl", "dir": "cu", "asset": "cu_elizabeth.json",
     "item": "hexapla-audio-slavonic-1757", "partial": False,
     "apocrypha": True},
    # ★ KJV, ADDED 2026-08-16 — the 30 books THIS PROJECT rendered (245
    #   chapters): 22 canon books LibriVox never recorded plus 8 apocrypha.
    # ⚠⚠ partial: True IS LOAD-BEARING, NOT LAZINESS. KJV has 80 non-empty
    #   books; we hold audio for 30. The other 50 are LibriVox HUMAN recordings
    #   that stay in audio_index.json — they have no per-verse offsets and 223
    #   of their sections span MULTIPLE chapters, which this one-chapter-per-
    #   entry format cannot express. A complete-set guard here would demand
    #   audio that must never exist.
    # ⚠ The app therefore MERGES both indexes for kjv (ReadingService); the two
    #   book sets are disjoint, verified 2026-08-16.
    # ⚠ "flat" is required: this item names files kjv_<book>_<chapter>.ogg at
    #   the root, not <book>/<chapter>.ogg.
    {"tid": "kjv", "dir": "en", "asset": "en_kjv.json",
     "item": "hexapla-audio-en", "partial": True,
     "apocrypha": True, "flat": "kjv_{b}_{c}.ogg"},
]
ARCHIVE_BASE = "https://archive.org/download"

# Book slots 0-65 are the Protestant canon; 66+ are deuterocanon.
# ⚠ THIS COMMENT USED TO SAY "apocrypha, which no narration set renders".
# That stopped being true on 2026-08-13 when cu rendered its deuterocanon, and
# the stale assumption is exactly what would have made 170 finished chapters
# unreachable. A set opts in per-entry with "apocrypha": True — see build_set().
CANON_BOOKS = 66


def bible_chapter_counts(asset_name):
    data = json.loads((ASSETS / "bibles" / asset_name).read_text(encoding="utf-8"))
    books = data if isinstance(data, list) else data["books"]
    counts = []
    for b in books:
        chapters = b["chapters"] if isinstance(b, dict) else b
        counts.append(len(chapters))
    return counts


def build_set(s, errors):
    tid, ndir, asset_name = s["tid"], s["dir"], s["asset"]
    item_id, partial = s["item"], s["partial"]
    src = NARRATION / ndir
    if not src.is_dir():
        errors.append(f"{tid}: no narration dir at {src}")
        return None
    # Books to index. Canon-only by DEFAULT — every set before cu rendered
    # nothing else, and ru/Geneva depend on the restriction (see below).
    #
    # ★ A SET MAY OPT IN TO ITS DEUTEROCANON with "apocrypha": True. cu is the
    #   first: narrate.py gives it `default_books: None`, so it renders EVERY
    #   non-empty slot — 1192 canon + 170 Slavonic deuterocanon. Without the
    #   opt-in those 170 chapters render, upload, and are then UNREACHABLE:
    #   the index simply has no entry, so the app falls back to TTS while
    #   correct narration sits on archive.org. No error, nothing to debug.
    # ⚠ THE OPT-IN AND THE COMPLETENESS GUARD MUST MOVE TOGETHER. Widening the
    #   book range without widening `expected`/`grid_books` below would demand
    #   audio the set does not have and fail a good build; narrowing one
    #   without the other silently drops chapters. They are one decision.
    # ⚠ DO NOT make this global. ru_synodal and en_geneva also carry apocrypha
    #   SLOTS, but no apocrypha AUDIO — flipping them on would fail their
    #   guard with 12 books of missing files.
    last = len(bible_chapter_counts(asset_name)) if s.get("apocrypha") \
        else CANON_BOOKS
    # ⚠ Restricting this matters for assets whose apocrypha slots are POPULATED
    # rather than empty. en_geneva carries 83 slots with 17 EMPTY ones, so the
    # older "count non-empty books" guard was enough for it. ru_synodal carries
    # 83 slots with 78 NON-EMPTY (the Synodal deuterocanon is real text), so
    # that same guard would demand audio for 78 books, get 66, and fail a
    # perfectly complete canon — the 83-slot trap wearing a different hat.
    counts = bible_chapter_counts(asset_name)[:last]
    base = f"{ARCHIVE_BASE}/{item_id}"
    entry = {}
    total = 0
    for bi, n_ch in enumerate(counts):
        chapters = {}
        for ci in range(n_ch):
            ogg = src / str(bi) / f"{ci}.ogg"   # local layout is always <book>/<ch>
            sidecar = src / str(bi) / f"{ci}.json"
            if not ogg.exists():
                if not partial:
                    errors.append(f"{tid}: missing audio {bi}/{ci}.ogg")
                continue
            offsets = []
            if sidecar.exists():
                offsets = json.loads(sidecar.read_text(encoding="utf-8")).get("offsets", [])
            elif not partial:
                errors.append(f"{tid}: missing sidecar {bi}/{ci}.json")
                continue
            # ★ FLAT NAMING (kjv). The en item predates the <book>/<chapter>
            # layout: its files are kjv_<book>_<chapter>.ogg at the item root.
            # "f" is a path relative to base, so both shapes fit the same index.
            chapters[str(ci)] = {
                "f": (s["flat"].format(b=bi, c=ci) if s.get("flat")
                      else f"{bi}/{ci}.ogg"),
                "o": offsets,
            }
            total += 1
        if chapters:
            entry[str(bi)] = {"base": base, "chapters": chapters}
    expected = sum(counts)
    if not partial:
        # Complete sets must cover the whole grid — catches a broken upload.
        if total != expected:
            errors.append(f"{tid}: {total} chapters built, grid expects {expected}")
        # Compare against books that actually HAVE chapters: an asset may carry
        # empty apocrypha slots (en_geneva has 83 slots, 66 of them non-empty),
        # and those can never have audio. Counting raw slots false-fails them
        # while still catching a genuinely missing book.
        grid_books = sum(1 for c in counts if c)
        if len(entry) != grid_books:
            errors.append(f"{tid}: {len(entry)} books built, grid has {grid_books} non-empty")
    tag = " (partial)" if partial else ""
    print(f"{tid}: {total}/{expected} chapters across "
          f"{len(entry)}/{len(counts)} books{tag}")
    if partial and entry:
        print(f"       books present: {sorted(int(k) for k in entry)}")
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    errors = []
    out = {}
    for s in SETS:
        e = build_set(s, errors)
        if e:
            out[s["tid"]] = e

    if errors:
        print("\nFAILED:")
        for e in errors[:20]:
            print("  " + e)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        sys.exit(1)

    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    print(f"\nasset size: {len(payload.encode('utf-8')) / 1024:.0f} KB")
    if a.dry_run:
        print("DRY RUN — not written.")
        return
    OUT.write_text(payload, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
