# -*- coding: utf-8 -*-
"""Upload a generated narration set to archive.org (one item per translation).

    python tools/upload_narration.py wbt --dry-run
    python tools/upload_narration.py wbt

Needs the `internetarchive` package and a configured ~/.config/internetarchive/
ia.ini (the owner's account is already linked).

⚠ OWNER POLICY (2026-07-13, restated 2026-07-21): the owner's personal name
must NOT appear anywhere in the metadata. Credit the project/app, never him.
The account that performs the upload is inherently his, but nothing we WRITE
names him.

✅ ACCEPTED EXCEPTION (owner decision 2026-07-31, "just accept it, it's fine"):
archive.org automatically stamps a publicly-visible `uploader` field with the
uploading account's e-mail — verified live on hexapla-audio-webster-1833 as
`uploader = aleksandr@tuta.com`. It is account-level and CANNOT be set,
overridden or suppressed from here. The owner accepted this rather than
running a second account. DO NOT re-raise it on every new narration set, and
do NOT treat it as licence to relax the rule above: everything this script
writes must still credit the project only. The same decision covers the
`originalurl` / description link to the app's landing page, which carries his
GitHub handle.

Item layout mirrors tools/NARRATION_PLAN.md §6: files land as
<bookIdx>/<chapter>.ogg plus the per-chapter <bookIdx>/<chapter>.json verse
offset sidecars (small, and what makes verse highlighting / tap-to-seek
possible in the app — LibriVox audio cannot do that).

## --selftest

    python tools/upload_narration.py --selftest

Checks the PURE logic this instrument rests on — the local/remote MD5 diff, the
no-files branch's metadata write, `apocrypha_clause()`, `index_reaches_apocrypha()`
and the set-key/directory split. ⛔ It makes NO network call, touches no
archive.org item, and uploads nothing; every fixture is built under
`tempfile.mkdtemp()` and removed afterwards. It runs with NO set argument — see
the note in `__main__` for how that is wired without changing any normal run.

## The MD5 diff is the instrument

`MISSING: 0` from the batched uploader does NOT mean the item is current: it
compares FILENAMES only, so a chapter whose CONTENT was replaced after it was
sent is present by name and invisible to it. Measured 2026-09-22 on the same
item in the same minute — the batched uploader said `MISSING: 0` while this
tool (MD5 both sides) said **341 replaced**. So the `replaced` count printed
here is what answers «is the audio current», and it is the thing a refactor
could quietly destroy.

⚠ KNOWN-BAD CONTROL, selftest-only. `HEXAPLA_NAME_ONLY_DIFF=1` makes that
comparison use FILENAMES only and ignore MD5 — reinstating exactly the batched
uploader's blind spot — so the selftest must FAIL assertion 1 under it and pass
without it. A test that passes BOTH ways is broken and worse than no test.
⛔ It is gated on `_IN_SELFTEST` and can never alter a real upload's diff.
"""
import argparse
import importlib
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NARRATION = Path("C:/Projects/Hexapla-releases/narration")
APP = "https://aleksandrr-dev.github.io/Hexapla/"

# Per-set metadata. Keep descriptions factual: what the text is, that the
# reading is synthetic, and that everything is free.
SETS = {
    # ⚠⚠ `en` IS THE KJV SET, AND IT IS THE ODD ONE OUT IN THREE WAYS. It was
    # missing from this table entirely until 2026-08-21, which is why the
    # upload chain died two seconds in with rc=1 on its first step.
    #   1. FLAT NAMES. The item has held 245 `kjv_<book>_<chapter>.ogg` files at
    #      its root since before this uploader existed, and
    #      build_audio_index_gen.py addresses them with the same template. See
    #      remote_name().
    #   2. IT IS AN EXTENSION, NOT A NEW SET. 245 chapters are already public
    #      (22 LibriVox-gap books + the apocrypha); this adds the 247 rendered
    #      for the 13 books whose LibriVox items vanished from archive.org in
    #      August 2026. checksum=True leaves the existing 245 alone, so the
    #      derive stays small - provided remote_name() is used on BOTH sides of
    #      the new/replaced comparison.
    #   3. IT IS PERMANENTLY PARTIAL. 492 chapters against a 1,189-chapter
    #      canon is the INTENDED end state: LibriVox covers the rest and the app
    #      merges the two indexes. So `title_partial` here must not read like an
    #      unfinished job - PROGRESS_NOTE's "still being produced" would be a
    #      false statement about a set that is doing exactly what it should.
    # ⚠ SUPERSEDED 2026-09-22: points 2-3 above describe the kokoro gap-refill.
    # The KJV was re-rendered WHOLE (1,189 canon + 182 apocrypha = 1,371) in
    # the owner's cloned chatterbox voice (narrate.py LANG_CONFIG "en"), so the
    # item is now a complete set: no scope_note, cloned + watermark disclosed.
    "en": {
        "asset": "en_kjv.json",
        "identifier": "hexapla-audio-en",
        "flat": "kjv_{b}_{c}.ogg",
        "title": "The King James Bible (1611) — complete audio narration, with the Apocrypha",
        "title_partial": "The King James Bible (1611) — audio narration (in progress)",
        "translation": "King James Version, 1611",
        "language": "eng",
        "voice": "Chatterbox Multilingual (MIT) — synthetic speech cloned "
                 "from a consented reference recording",
        "cloned": True,
        "watermark": True,   # Chatterbox embeds Resemble's Perth watermark
        "subject": ["bible", "audiobook", "king james version", "kjv",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
    "wbt": {
        "asset": "en_webster.json",
        "identifier": "hexapla-audio-webster-1833",
        "title": "The Holy Bible, Webster's Revision (1833) — complete audio narration",
        "translation": "Webster's Revision of the King James Bible, 1833",
        "language": "eng",
        "voice": "Kokoro text-to-speech (Apache-2.0), voice am_adam",
        "subject": ["bible", "audiobook", "webster bible", "public domain",
                    "scripture", "christianity", "text to speech",
                    "hexapla", "audio bible"],
    },
    "gnv": {
        "asset": "en_geneva.json",
        "identifier": "hexapla-audio-geneva-1599",
        "title": "The Geneva Bible (1599) — complete audio narration",
        "translation": "Geneva Bible, 1599",
        "language": "eng",
        "voice": "Kokoro text-to-speech (Apache-2.0), voice am_adam",
        "subject": ["bible", "audiobook", "geneva bible", "public domain",
                    "scripture", "christianity", "text to speech",
                    "hexapla", "audio bible"],
    },
    # wyc — kokoro, so NOT cloned and NOT watermarked (Perth is Chatterbox's).
    # ⚠ The voice string must say what is unusual here, because a listener
    # hearing 1395 pronunciation from a 2026 synthesiser deserves to know it is
    # a RECONSTRUCTION and whose: the phoneme mapping is this project's
    # (tools/me_phonemes.py), not a scholarly edition's, and reasonable
    # reconstructions differ. Do not shorten this to "voice am_adam".
    "wyc": {
        "asset": "enm_wycliffe.json",
        "identifier": "hexapla-audio-wycliffe-1395",
        "title": "The Wycliffe Bible (1395) — complete audio narration in reconstructed Middle English",
        "translation": "Wycliffe Bible, later version, 1395",
        "language": "enm",
        "voice": ("Kokoro text-to-speech (Apache-2.0), voice am_adam, driven "
                  "from IPA rather than English spelling: the reading follows "
                  "a reconstruction of late-14th-century Middle English "
                  "pronunciation made for this project, so it is an "
                  "interpretation and not the only defensible one"),
        "subject": ["bible", "audiobook", "wycliffe bible", "middle english",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
    # ⚠ NAME POLICY for sv/ru: BOTH are cloned from real people's consented
    # reference recordings (sv = the owner's friend, ru = the owner). The
    # no-personal-names rule covers them BOTH — credit the consent, never
    # the person. Do not "improve" these descriptions with anyone's name.
    "sv": {
        "asset": "sv_karlxii.json",
        "identifier": "hexapla-audio-karlxii-1703",
        "title": "Karl XII:s Bibel (1703) — komplett ljudinspelning / complete audio narration",
        # Used automatically while the set covers fewer than its own canon.
        "title_partial": "Karl XII:s Bibel (1703) — ljudinspelning / audio "
                         "narration (pågår / in progress)",
        "translation": "Karl XII:s Bibel, 1703 (Swedish)",
        "language": "swe",
        "voice": "Chatterbox Multilingual (MIT) — synthetic speech cloned "
                 "from a consented reference recording by a native Swedish "
                 "volunteer",
        "cloned": True,
        "watermark": True,   # Chatterbox embeds Resemble's Perth watermark
        "subject": ["bible", "audiobook", "karl xii bibel", "svenska",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
    # Church Slavonic, Elizabeth Bible 1757. Narration folder is "cu"; the
    # APP id is "csl" (see build_audio_index_gen.py's warning about the split).
    # ⚠ The voice is CLONED FROM THE OWNER'S OWN consented recording, same as
    # ru — so "cloned": True is required, and the no-personal-names rule applies:
    # credit the consent, never the person.
    # ⚠ Canon is 1,192 chapters (Psalm 151, Daniel 13-14), not 1,189.
    "cu": {
        "asset": "cu_elizabeth.json",
        "identifier": "hexapla-audio-slavonic-1757",
        "title": "Елизаветинская Библия (1757) — полная аудиозапись / "
                 "complete audio narration",
        # ⚠ Used automatically while chapters are missing, so a half-rendered
        # set can never be published under a "complete" title — the inversion
        # Karl XII shipped on 2026-08-01 behind a clean "0 failed".
        "title_partial": "Елизаветинская Библия (1757) — аудиозапись "
                         "(в процессе) / audio narration (in progress)",
        "translation": "Church Slavonic Elizabeth Bible, 1757",
        "language": "chu",
        "voice": "Fun-CosyVoice3 — synthetic speech cloned from a consented "
                 "reference recording by a volunteer reader",
        "cloned": True,      # CosyVoice3 embeds no watermark
        "subject": ["bible", "audiobook", "церковнославянский",
                    "елизаветинская библия", "библия", "public domain",
                    "scripture", "christianity", "text to speech", "hexapla",
                    "audio bible"],
    },
    # William Tyndale, 1525/1531. Narration folder "tyn", app id "tyn".
    # ⚠⚠ PARTIAL BY NATURE, NOT BY PROGRESS — and the honesty gate handles it
    # correctly WITHOUT a special case, which is worth understanding before
    # anyone "fixes" it. Tyndale never translated the whole Bible; en_tyndale
    # carries 33 non-empty books (Pentateuch, Jonah, NT) and its other 33 canon
    # slots have a ZERO-LENGTH chapters list. canon_chapters() therefore returns
    # **451**, not 1189, so a full render gives have_canon == expected and
    # is_partial is False. The set is COMPLETE against its own text while
    # covering half the canon.
    # ▶ The title still NAMES the scope, because "complete audio narration" on
    #   its own would imply a whole Bible to anyone reading the item page.
    # ⚠ title_partial is kept anyway: if a chapter is ever lost, the gate must
    #   have an honest title to fall back to rather than hard-exiting.
    # ⚠ The voice is CLONED FROM A CONSENTED RECORDING — "cloned": True is
    #   required, and the no-personal-names rule applies: credit the consent,
    #   never the person.
    "tyn": {
        "asset": "en_tyndale.json",
        "identifier": "hexapla-audio-tyndale-1525",
        "title": "Tyndale's Bible (1525/1531) — complete audio narration of "
                 "the Pentateuch, Jonah and the New Testament",
        "title_partial": "Tyndale's Bible (1525/1531) — audio narration "
                         "(in progress)",
        "translation": "Tyndale Bible, 1525/1531 (Pentateuch, Jonah, New Testament)",
        "language": "eng",
        "voice": "Chatterbox Multilingual (MIT) — synthetic speech cloned "
                 "from a consented reference recording",
        "cloned": True,
        "watermark": True,   # Chatterbox embeds Resemble's Perth watermark
        "subject": ["bible", "audiobook", "tyndale bible", "early modern english",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
    # Young's Literal Translation, 1898. Narration folder "ylt", app id "ylt"
    # — no tid/dir split here, unlike sv/gnv/cu.
    # ⚠ The voice is CLONED FROM THE OWNER'S OWN consented recording, the same
    # basis as ru and cu, so "cloned": True is required and the no-personal-names
    # rule applies: credit the consent, never the person.
    # ⚠ Canon is 1,189 chapters. en_ylt.json has no non-empty apocrypha slots,
    # so canon_chapters() returns 1189 and no "apocrypha" flag belongs here.
    # ⚠ Layout is the standard <book>/<chapter>.ogg — no "flat".
    "ylt": {
        "asset": "en_ylt.json",
        "identifier": "hexapla-audio-ylt-1898",
        "title": "Young's Literal Translation (1898) — complete audio narration",
        "title_partial": "Young's Literal Translation (1898) — audio "
                         "narration (in progress)",
        "translation": "Young's Literal Translation, 1898",
        "language": "eng",
        "voice": "Chatterbox Multilingual (MIT) — synthetic speech cloned "
                 "from a consented reference recording",
        "cloned": True,
        "watermark": True,   # Chatterbox embeds Resemble's Perth watermark
        "subject": ["bible", "audiobook", "young's literal translation", "ylt",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
    "ru": {
        "asset": "ru_synodal.json",
        "identifier": "hexapla-audio-synodal-1876",
        "title": "Синодальный перевод (1876) — полная аудиозапись / complete audio narration",
        "translation": "Russian Synodal Bible, 1876",
        "language": "rus",
        "voice": "Fun-CosyVoice3 — synthetic speech cloned from a consented "
                 "reference recording by a native Russian volunteer",
        "cloned": True,      # CosyVoice3 embeds no watermark
        "subject": ["bible", "audiobook", "синодальный перевод", "библия",
                    "public domain", "scripture", "christianity",
                    "text to speech", "hexapla", "audio bible"],
    },
}
# ⚠ ru UPLOAD GATE: do not upload ru until (a) the ~381-chapter leak
# re-render has completed under the fixed RU_STYLES, (b) the leak scanner
# has re-screened the re-rendered set clean, and (c) the NT + apocrypha
# passes are done. Uploading a partially-defective corpus wastes the item's
# reputation and everyone's bandwidth.

# The 66-book Protestant canon. Used to decide whether a set may honestly be
# called "complete" — an archive.org item is a public claim, and shipping a
# partial render under a "complete audio narration" title would be false.
#
# ⚠ 1189 IS THE *KJV-GRID* COUNT AND IS NOT UNIVERSAL. A translation on its own
# native versification has its own total: the Russian Synodal canon is 1192
# chapters (Psalm 151, and Daniel 13-14 for the LXX additions), and Slavonic is
# the same shape. Hardcoding 1189 would have flipped ru to the "complete" title
# three chapters early — the honesty gate inverted in the DANGEROUS direction,
# claiming a finished Bible while Psalm 151 and the end of Daniel were missing.
# The real total is therefore read from each set's own asset.
BIBLES = Path("C:/Projects/Hexapla/app/src/main/assets/bibles")
KJV_CANON_CHAPTERS = 1189
# Book slots 0-65 are the protestant canon; 66+ is apocrypha. Same constant as
# build_audio_index_gen.CANON_BOOKS — kept local so this tool has no import
# dependency on the index builder.
CANON_BOOKS = 66

# ⚠ THE SET KEY IS NOT THE DIRECTORY. `en` is the narration DIRECTORY (and the
# directory `build` reads, because `src = NARRATION / set_key`); the item it
# publishes is the KJV item `hexapla-audio-en`, which
# build_audio_index_gen.py calls `kjv`, and whose files are FLAT-named
# `kjv_<book>_<chapter>.ogg` — see remote_name. The other sets happen to agree.
# Read by --selftest assertion 7 so a future refactor cannot quietly swap the
# two names.
NARRATION_DIR_OF = {"en": "en", "wbt": "wbt", "gnv": "gnv", "wyc": "wyc",
                    "sv": "sv", "cu": "cu", "tyn": "tyn", "ylt": "ylt",
                    "ru": "ru"}

# ⚠⚠ SELFTEST-ONLY KNOWN-BAD CONTROL, in the same shape as
# thorlaks_duplicate_numerals.distinct_only(). True only while selftest() runs,
# so it can never alter a real run's local/remote comparison. See
# name_only_diff() and the module docstring.
_IN_SELFTEST = False


def name_only_diff():
    """Known-bad control: decide the diff from NAME alone, ignoring MD5.

    Reinstates exactly the blindness this tool exists to remove — the batched
    uploader's, measured at `MISSING: 0` against 341 real content replacements
    in the same minute on the same item. Under it a file whose name is present
    remotely is counted present whether or not its bytes match, so every
    replaced chapter disappears from the count and the tool reports a clean,
    current item over stale audio.

    ⛔ Gated on _IN_SELFTEST so a real upload is never diffed this way.
    """
    return _IN_SELFTEST and os.environ.get("HEXAPLA_NAME_ONLY_DIFF") == "1"


def canon_chapters(asset_name):
    """Chapters in the 66-book canon of this asset, on its OWN versification.

    ⚠⚠ THE COMMENT HERE USED TO SAY "no set renders apocrypha today". THAT
    BECAME FALSE ON 2026-08-13 and it broke the honesty gate. `narrate.py`
    gives cu `default_books: None`, which renders EVERY non-empty slot — so
    cu's target is 1362 chapters (1192 canon + 170 Slavonic deuterocanon),
    not 1192. The gate compared this canon-only figure against a count of ALL
    oggs on disk, so 1192 apocrypha-inflated files could certify a set
    "complete" while the canon still had holes. That is the same inversion
    Karl XII shipped behind a clean "0 failed", arriving by a new route.

    ▶ Callers MUST compare this against canon oggs only — see canon_ogg_count.
    """
    data = json.loads((BIBLES / asset_name).read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) else data
    return sum(len(b["chapters"]) for b in books[:66])


def canon_ogg_count(src, asset_name):
    """Rendered chapters that the 66-book canon actually accounts for.

    Counts by ASKING THE GRID, not by counting files: a file in slot 66+ is
    real audio but it is not canon, and (today) the app's index cannot reach
    it at all — build_audio_index_gen.py slices [:CANON_BOOKS].
    """
    data = json.loads((BIBLES / asset_name).read_text(encoding="utf-8"))
    books = data["books"] if isinstance(data, dict) else data
    n = 0
    for bi, b in enumerate(books[:66]):
        for ci in range(len(b["chapters"])):
            if (src / str(bi) / f"{ci}.ogg").exists():
                n += 1
    return n

# ⚠ A SET CAN BE PARTIAL AGAINST THE CANON AND STILL BE FINISHED. `en` is the
# KJV gap-refill: 492 chapters covering the books LibriVox does not, with
# LibriVox supplying the rest and the app merging both indexes. Nothing more is
# coming, so PROGRESS_NOTE's "still being produced ... added to this item as
# they are rendered" would be a plain falsehood on its item page - the same
# class of error as Karl XII sitting publicly at "(in progress)" after it
# finished. A set says so with `scope_note`, and then it is described by its
# PURPOSE rather than by a fraction of a canon it was never meant to cover.
SCOPE_NOTE = """
<p><b>This item covers {n_chapters} chapters: the books of the King James Bible
that LibriVox's public-domain recordings do not include.</b> It is complete for
that purpose and is not waiting on further chapters.</p>
"""

DESCRIPTION = """<p>{opening} chapter-by-chapter audio narration of
<b>{translation}</b>, produced for <a href="{app}">Hexapla</a>, a free and
offline parallel Bible app for Android.</p>
{progress}
<p>The underlying translation is in the <b>public domain</b> by age. The
reading is <b>synthetic speech</b>, generated with {voice} — it is not a human
performance.{provenance}</p>

<p>Files are one Ogg audio file per chapter, laid out as
<code>{layout}</code> using the standard 66-book
Protestant order with zero-based book numbering (0 = Genesis, 65 =
Revelation).{apocrypha} Each audio file has a matching <code>.json</code> sidecar
listing the start time in milliseconds of every verse, so players can
highlight verses or seek to them directly.</p>

<p>{n_chapters} chapters. Free to use, copy and redistribute. The app that
uses these files is free as well: no advertising, no purchases, no accounts,
and no data collection.</p>"""

# The provenance clause differs by how the voice was made, and getting it wrong
# is a public false statement either way:
#   · stock synthetic voice (kokoro am_adam) -> nobody's voice is involved.
#   · CLONED from a consenting volunteer (sv, ru) -> a real person's voice IS
#     the source. Saying "no narrator was involved" there would be false, and
#     it would also contradict the {voice} clause in the same sentence.
# Set "cloned": True on any set whose reference recording came from a person.
PROVENANCE_STOCK = (" No narrator is credited because none was involved.")
# NB: the {voice} clause already states that the voice was cloned from a
# consented recording, so this must not repeat it — it adds only what {voice}
# does not say: the volunteer never read these chapters, and is not named.
PROVENANCE_CLONED = (
    " The volunteer whose voice it reproduces did not read these chapters, "
    "and is not credited by name.")
# Chatterbox (ResembleAI) embeds Resemble's inaudible "Perth" watermark in
# every file it generates. Disclosing it is an obligation recorded in the
# project notes, not an optional nicety — listeners and re-users are entitled
# to know the audio carries a watermark.
WATERMARK_NOTE = (
    " The generated audio carries Resemble AI's inaudible &quot;Perth&quot; "
    "watermark, embedded by the synthesis engine.")

# ⚠⚠ THE LAYOUT PARAGRAPH USED TO STOP AT "(0 = Genesis, 65 = Revelation)".
# On an item that also holds APOCRYPHA that was a public false statement about
# the item's own contents: Karl XII carries 147 chapters in slots 68-81, and a
# reader who trusted the sentence would conclude those directories were not
# part of the set. Measured 2026-09-22.
# ▶ DERIVED, NEVER DECLARED. This clause is built from the slots the upload
#   ACTUALLY carries, so it cannot go stale the way a per-set boolean would:
#   render a new apocryphal book and the sentence grows by itself; render none
#   and the clause is absent entirely. ⛔ Do not replace this with a flag.
APOCRYPHA_NOTE = (
    " This item also carries the <b>deuterocanonical / apocryphal books</b> of"
    " this edition, in slots {slots} of the same numbering — {n} chapters"
    " beyond the 66-book canon, in the same layout.")


def write_metadata(identifier, metadata, title):
    """Write metadata to an EXISTING item, then verify it against live state.

    Split out of the upload path on 2026-09-22 because that path could not be
    reached at all when no file needed sending — see the
    "Nothing to upload" branch. Verified rather than trusted: a stale public
    claim is the one failure no amount of successful uploads would reveal.
    """
    from internetarchive import get_item
    item = get_item(identifier)
    # ⚠ mediatype/collection are fixed at item creation; resending them to an
    # existing item is refused WHOLESALE ("Not authorized to update mediatype",
    # HTTP 400 - hexapla-audio-en is mediatype `data`, 2026-09-22), so no
    # title or description edit could land. Send only what may change.
    metadata = {k: v for k, v in metadata.items()
                if k not in ("mediatype", "collection")}
    r = item.modify_metadata(metadata)
    code = getattr(r, "status_code", None)
    if code not in (200, None):
        print(f"\nMETADATA WRITE FAILED: HTTP {code}")
        # archive.org says WHY in the body; a bare status code is undiagnosable.
        print(f"    body: {(getattr(r, 'text', '') or '')[:800]}")
        sys.exit(1)
    live = get_item(identifier).metadata.get("title", "")
    if live != title:
        print("\n⚠ metadata written but the live title does not match yet:")
        print(f"    want: {title}")
        print(f"    live: {live}")
        print("  archive.org applies metadata edits through its task queue;")
        print("  re-check before treating the item as published.")
    else:
        print(f"\ntitle verified: {live}")


def index_reaches_apocrypha(set_key):
    """Does build_audio_index_gen.py index this set's apocrypha slots?

    Returns True / False / None, where **None means "could not tell"** — an
    unreadable or unparseable builder, or no entry for this item. ⛔ It never
    guesses a reassuring answer: a failed read must not be indistinguishable
    from a real verdict.

    Joined on the archive.org IDENTIFIER, not on the set key, because the two
    files key their sets differently: this tool calls Karl XII `sv` (the
    narration directory) and the builder calls it `kxii` (the app's tid). The
    identifier is the one name both files must already agree on, so the join
    cannot rot the way a hand-maintained key mapping would.
    """
    import ast
    ident = SETS.get(set_key, {}).get("identifier")
    if not ident:
        return None
    builder = Path(__file__).resolve().parent / "build_audio_index_gen.py"
    try:
        tree = ast.parse(builder.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "SETS"
                   for t in node.targets):
            continue
        try:
            entries = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            return None
        for e in entries:
            if isinstance(e, dict) and e.get("item") == ident:
                return bool(e.get("apocrypha"))
        return None          # builder parsed, but it has no entry for this item
    return None


def apocrypha_clause(oggs, src):
    """The apocrypha sentence for THIS upload, or "" if it carries none.

    ⛔ Never returns a plausible-but-wrong sentence: it reads the slot numbers
    off the files being uploaded. A set with no slot >= 66 gets "", and the
    description is then byte-identical to what it has always said.
    """
    slots = sorted({int(p.parts[0]) for p in
                    (f.relative_to(src) for f in oggs)
                    if p.parts[0].isdigit() and int(p.parts[0]) >= CANON_BOOKS})
    if not slots:
        return ""
    n = sum(1 for f in oggs
            if f.relative_to(src).parts[0].isdigit()
            and int(f.relative_to(src).parts[0]) >= CANON_BOOKS)
    # Contiguous runs read as "68-72", gaps stay visible: slot 73 is absent
    # from Karl XII because the print has no Epistle of Jeremiah, and hiding
    # that behind "68-81" would assert a book the item does not hold.
    runs, start, prev = [], slots[0], slots[0]
    for s in slots[1:]:
        if s == prev + 1:
            prev = s
            continue
        runs.append((start, prev))
        start = prev = s
    runs.append((start, prev))
    text = ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)
    return APOCRYPHA_NOTE.format(slots=text, n=n)


PROGRESS_NOTE = """
<p><b>This narration is still being produced: {n_chapters} of the 1,189
chapters of the 66-book canon are available so far.</b> The remaining chapters
are added to this item as they are rendered, so a book that is absent today may
be present later. Nothing already uploaded changes.</p>
"""


def remote_name(rel_path, meta_src):
    """Local <book>/<chapter><suffix> -> the name this item actually uses.

    Most sets keep the directory layout. `en` does NOT: the KJV item
    `hexapla-audio-en` has held 245 files named `kjv_<book>_<chapter>.ogg` at
    the root since long before this uploader existed, and
    build_audio_index_gen.py builds its URLs from that same "flat" template.
    Uploading `<book>/<chapter>.ogg` there would publish 247 chapters that the
    index cannot address, beside 245 that it can - so the set would look
    complete and be half unreachable.

    ⚠ The suffix is preserved verbatim so `.w.json` survives: Audio.kt derives
    the word-sidecar URL as `oggUrl.removeSuffix(".ogg") + ".w.json"`, which for
    this item means `kjv_<b>_<c>.w.json` and nothing else.
    """
    rel = str(rel_path).replace("\\", "/")
    flat = meta_src.get("flat")
    if not flat:
        return rel
    book, tail = rel.split("/", 1)
    chapter, _, suffix = tail.partition(".")
    return flat.format(b=book, c=chapter).rsplit(".", 1)[0] + "." + suffix


def _md5(path):
    """MD5 of a local file, read in 1 MiB chunks (large .ogg files)."""
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plan_upload(oggs, src, meta_src, remote):
    """Classify local audio against the item's remote state.

    `remote` maps remote NAME -> remote MD5 (or None when the listing carried no
    md5), i.e. exactly the shape `build()` reduces `get_item().files` to:
        {f["name"]: f.get("md5") for f in item.files}

    Returns (audio_new, audio_replaced) — names absent remotely, and names
    present whose CONTENT differs.

    ⛔ THE MD5 IS THE POINT. A name-only comparison reports a chapter whose
    content was replaced as present, which is the batched uploader's blind spot
    (measured at `MISSING: 0` against 341 real replacements). ⚠ MUST use the
    same remote_name() mapping as the upload itself: with a flat set,
    comparing "<b>/<c>.ogg" against an item holding "kjv_<b>_<c>.ogg" makes
    every existing file look NEW and queues a full derive over 245 chapters
    that did not change.
    """
    audio_new, audio_replaced = [], []
    for f in oggs:
        name = remote_name(f.relative_to(src), meta_src)
        if name not in remote:
            audio_new.append(name)
        elif name_only_diff():
            # see name_only_diff() — selftest-only known-bad control
            continue
        elif remote[name] and _md5(f) != remote[name]:
            audio_replaced.append(name)
    return audio_new, audio_replaced


def outstanding_files(files, remote):
    """Split {name: local_path} into (outstanding, n_unchanged) by MD5.

    Same decision as plan_upload, taken over everything to be sent (audio AND
    sidecars), against the SAME remote shape.
    """
    outstanding, unchanged = {}, 0
    for name, path in files.items():
        rmd5 = remote.get(name)
        if rmd5 and _md5(path) == rmd5:
            unchanged += 1
        else:
            outstanding[name] = path
    return outstanding, unchanged


def build(set_key, dry_run=False):
    meta_src = SETS[set_key]
    src = NARRATION / set_key
    if not src.is_dir():
        sys.exit(f"no narration directory at {src}")

    oggs = sorted(src.rglob("*.ogg"))
    # ⚠ EXCLUDE `.eos.json`. Those are narrate.py's per-chapter QA
    # diagnostics (`long_tail` flags etc.), not app data — every other
    # tool that walks a set already skips them (offset_drift,
    # repair_offsets, tail_hallucinations, zero_duration_verses). This
    # walk did not, so a tyn upload would have published 451 internal
    # diagnostic files to a public item and paid for their derives.
    # ⚠ .eos.json and .qa.json are narrate.py's per-chapter QA records (the
    # forced-EOS flags and the verse gate's verdicts). They are diagnostics for
    # this machine, not app data — the app reads <c>.json and <c>.w.json only.
    jsons = sorted(f for f in src.rglob("*.json")
                   if not f.name.endswith((".eos.json", ".qa.json")))
    if not oggs:
        sys.exit(f"no .ogg files under {src}")
    # Every chapter must carry its offsets sidecar, or verse highlighting
    # silently degrades for that chapter in the app.
    missing = [str(o.relative_to(src)) for o in oggs
               if not o.with_suffix(".json").exists()]
    if missing:
        sys.exit(f"{len(missing)} chapters lack a .json sidecar: {missing[:5]}")

    total_bytes = sum(f.stat().st_size for f in oggs + jsons)
    # Honesty gate: only a set covering the whole canon may say "complete".
    expected = canon_chapters(meta_src["asset"])
    # ⚠ NOT len(oggs) — that counts apocrypha too and can inflate a holed
    # canon past `expected`. See canon_chapters' warning.
    have_canon = canon_ogg_count(src, meta_src["asset"])
    is_partial = have_canon < expected
    extra = len(oggs) - have_canon
    if extra:
        # ⚠⚠ THIS NOTE USED TO SAY, FLATLY, "today's index CANNOT reach them".
        # That was true when written and is NOT true now: build_audio_index_gen
        # lets a set OPT IN per entry with "apocrypha": True, and kxii has done
        # so — all 147 of its apocryphal chapters are indexed and live.
        # Reporting them as unreachable sent a reader hunting for a shipping
        # bug that does not exist (2026-09-22).
        # ▶ ASK THE BUILDER, do not assert. ⛔ A failed read must not print the
        #   reassuring branch — it says it could not tell.
        print(f"note      : {extra} rendered chapters sit in apocrypha slots "
              f"({CANON_BOOKS}+).", end=" ")
        reach = index_reaches_apocrypha(set_key)
        if reach is True:
            print("The index REACHES them (this set sets "
                  '"apocrypha": True in build_audio_index_gen.py).')
        elif reach is False:
            print("They upload, but today's index CANNOT reach them — this "
                  'set has no "apocrypha": True in build_audio_index_gen.py, '
                  "which slices [:CANON_BOOKS].")
        else:
            print("⛔ COULD NOT DETERMINE whether the index reaches them — "
                  "build_audio_index_gen.py was unreadable. Check by hand; "
                  "this is not a clean result.")
    if is_partial and "title_partial" not in meta_src:
        sys.exit(f"{set_key}: {len(oggs)}/{expected} chapters is a "
                 f"PARTIAL set, but SETS['{set_key}'] has no 'title_partial'. "
                 f"Add one rather than publishing a 'complete' title.")
    title = meta_src["title_partial"] if is_partial else meta_src["title"]
    metadata = {
        "mediatype": "audio",
        "collection": "opensource_audio",
        "title": title,
        # ⚠ project credit only — never the owner's personal name.
        "creator": "Hexapla (free offline parallel Bible app)",
        "language": meta_src["language"],
        "subject": meta_src["subject"],
        "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
        "rights": "Translation is public domain by age; the narration audio "
                  "is machine-generated and placed in the public domain.",
        "originalurl": APP,
        "description": DESCRIPTION.format(
            opening=("A complete" if not is_partial
                     else "A" if meta_src.get("scope_note")
                     else "An in-progress"),
            progress=(SCOPE_NOTE.format(n_chapters=len(oggs))
                      if meta_src.get("scope_note")
                      else PROGRESS_NOTE.format(n_chapters=len(oggs))
                      if is_partial else ""),
            translation=meta_src["translation"], app=APP,
            provenance=(PROVENANCE_CLONED if meta_src.get("cloned")
                        else PROVENANCE_STOCK)
                       + (WATERMARK_NOTE if meta_src.get("watermark") else ""),
            voice=meta_src["voice"], n_chapters=len(oggs),
            apocrypha=apocrypha_clause(oggs, src),
            # ⚠ TELL THE TRUTH ABOUT THE LAYOUT. A flat item does NOT use
            # <book>/<chapter>.ogg, and the old wording said it did — a public
            # false statement, and one that would send anyone reading the item
            # page looking for directories that are not there.
            layout=(meta_src["flat"].replace("{b}", "&lt;book&gt;")
                                    .replace("{c}", "&lt;chapter&gt;")
                    if meta_src.get("flat")
                    else "&lt;book&gt;/&lt;chapter&gt;.ogg")),
    }

    files = {}
    for f in oggs + jsons:
        files[remote_name(f.relative_to(src), meta_src)] = str(f)
    cover = NARRATION / "cover.jpg"
    if cover.exists():
        files["cover.jpg"] = str(cover)

    print(f"item      : {meta_src['identifier']}")
    print(f"files     : {len(files)} ({len(oggs)} chapters + sidecars)")
    print(f"canon     : {have_canon}/{expected}")
    print(f"size      : {total_bytes / 1e9:.2f} GB")
    print(f"metadata  : {json.dumps(metadata, ensure_ascii=False, indent=1)}")
    from internetarchive import upload, get_item

    # ⚠⚠ DECIDE THE DERIVE FROM WHAT THIS RUN ACTUALLY CHANGES — see the long
    # note at the derive call. Classify BEFORE uploading, while the item still
    # shows its pre-run state.
    _pre = get_item(meta_src["identifier"])
    _remote = {f["name"]: f.get("md5") for f in _pre.files} if _pre.exists else {}

    audio_new, audio_replaced = plan_upload(oggs, src, meta_src, _remote)
    print(f"audio      : {len(audio_new)} new, {len(audio_replaced)} replaced, "
          f"{len(oggs) - len(audio_new) - len(audio_replaced)} unchanged")

    # A task already RUNNING on this item holds everything queued behind it —
    # archive.org works an item's tasks in order. That is how one stray derive
    # blocked the whole account for three days. Warn, but do not refuse: the
    # upload itself is still correct and resumable.
    try:
        from internetarchive import get_session
        _mine = list(get_session().get_my_catalog())
        _here = [x for x in _mine if x.identifier == meta_src["identifier"]]
        _run = [x for x in _here if x.color == "blue"]
        _q = [x for x in _here if x.color == "green"]
        if _run or _q:
            print(f"⚠ item queue : {len(_run)} running, {len(_q)} queued "
                  f"on this item ALREADY")
            for x in _run:
                print(f"    running since {x.submittime}  {x.cmd}  "
                      f"task {x.task_id}")
            print("  New uploads queue BEHIND these. If a derive has been "
                  "running for days, that is the blocker.")
        if len(_mine) >= 150:
            print(f"⚠ account queue: {len(_mine)} tasks — at or over the "
                  f"per-access-key ration of 150. Uploads will be refused "
                  f"until it drains.")
    except Exception as e:                                     # noqa: BLE001
        print(f"  (could not read the task catalog: {type(e).__name__})")


    # State the derive decision HERE, where a dry run can still show it. An
    # unnecessary remove_derived rebuild is the most expensive mistake this
    # script can make - it blocked the whole account for three days - so it has
    # to be visible BEFORE anyone commits to the run, not only in hindsight.
    if audio_replaced:
        print(f"derive plan: remove_derived=* ({len(audio_replaced)} replaced "
              f"originals) - EXPENSIVE, rebuilds every derivative on the item")
    elif audio_new:
        print(f"derive plan: plain derive ({len(audio_new)} new chapters)")
    else:
        print("derive plan: NONE - no audio added or replaced")

    # !! DO NOT DELEGATE THE "IS IT ALREADY THERE" DECISION TO THE LIBRARY.
    # internetarchive's upload(checksum=True) skips a matching file ONLY when
    # the item has NO pending tasks. From internetarchive/item.py:
    #     if (not self.tasks) and (ia_file) and (ia_file.md5 == md5_sum):
    # so ONE queued derive silently turns the skip OFF and the run re-sends
    # EVERY file. That is exactly what happened on 2026-09-03: one file had
    # actually changed (wyc 66/4.w.json), 150 archive.php tasks were queued,
    # the 150-per-access-key ration cut it off, and NOTHING landed. The remote
    # MD5s were readable the whole time - the library simply refused to trust
    # them while tasks were pending. It is also self-perpetuating: the tasks it
    # queues keep item.tasks non-empty, so the NEXT run cannot skip either.
    # > So the decision is made HERE, from MD5s we read ourselves, and only the
    # difference is sent. checksum=True stays on at the upload call as
    # belt-and-braces - it is never again the guard.
    if _pre.exists:
        if not _remote:
            # A readable item that returns NO file metadata is a FAILED READ,
            # not an empty item. Uploading the whole set on that basis is the
            # entire bug class this guard exists to stop: a failed read must
            # never be indistinguishable from a real "nothing is there yet".
            print("\nREFUSING: the item exists but returned no file metadata. "
                  "That is an unreadable remote state, not an empty item - "
                  "sending on this basis would re-upload the entire set. "
                  "Re-run when the item's metadata reads.")
            sys.exit(3)
        outstanding, unchanged = outstanding_files(files, _remote)
        print(f"outstanding: {len(outstanding)} of {len(files)} to send "
              f"({unchanged} already present with a matching MD5)")
        if not outstanding:
            print("\nNothing to upload - every local file is already on the "
                  "item with a matching MD5.")
            # ⚠⚠ THIS USED TO `return` HERE, AND THAT MADE A METADATA-ONLY
            # CORRECTION IMPOSSIBLE TO PUBLISH. The metadata write lives past
            # the upload call, so once every file matched, the tool skipped it
            # and exited 0 — looking exactly like success while the public
            # description kept saying whatever it said before. Found 2026-09-22
            # correcting the Karl XII layout sentence, which claimed the item
            # held only books 0-65 while it also held 147 apocryphal chapters.
            # Same class as the "(pågår)" title that sat public for weeks: a
            # publishing step skipped for throughput and never re-run.
            # ▶ Files being current is NOT metadata being current. Write it.
            if dry_run:
                print("DRY RUN — metadata NOT written. Without --dry-run this "
                      "run would still write metadata and verify the title.")
                return
            print("Writing metadata anyway - files current != metadata current.")
            write_metadata(meta_src["identifier"], metadata, title)
            return
        files = outstanding
    else:
        print(f"outstanding: {len(files)} of {len(files)} to send (new item)")

    if dry_run:
        print("\nDRY RUN — nothing uploaded.")
        return


    # checksum=True skips files already on the item whose MD5 matches, which
    # makes a re-upload INCREMENTAL. This matters for any set published in
    # stages: Karl XII was uploaded partial at ~940 chapters, so finishing it
    # would otherwise re-send the whole ~1 GB (Geneva's full 1.03 GB took about
    # four hours). A mismatched or missing file is still uploaded, so this
    # cannot silently skip damaged content.
    #
    # ⚠ THE metadata= ARGUMENT ONLY TAKES EFFECT WHEN upload() *CREATES* THE
    # ITEM. On an item that already exists, archive.org ignores the
    # x-archive-meta headers entirely. An earlier version of this comment
    # claimed metadata was "applied regardless, which is what flips a partial
    # title to the complete one" — that was FALSE, and it failed exactly where
    # it mattered: Karl XII finished at 1189/1189 on 2026-08-01 and stayed
    # publicly titled "(pågår / in progress)", the precise inversion the
    # honesty gate exists to prevent. Geneva looked fine only because it was a
    # brand-new item. Metadata must be written explicitly, below.
    # ⚠ queue_derive=False IS REQUIRED FOR A SET THIS SIZE. Every uploaded file
    # otherwise queues a DERIVE task, and archive.org rations queued tasks per
    # access key. The ru upload died at 877 of 1,192 files on 2026-08-07 with
    #   "Please reduce your request rate. - accesskey_tasks_queued exceeds
    #    rationed amount"
    # leaving the public item half-updated. Geneva/Karl XII got away with it
    # only because their queues had drained between runs.
    # ⚠⚠ BUT "derives are useless to us" — what this comment used to say — IS
    # WRONG, AND IT SHIPPED A PUBLIC FALSEHOOD. True for the APP, which streams
    # the .ogg originals and never touches a derivative. NOT true for the item
    # PAGE: archive.org's own web player streams the derived .mp3. When the
    # corrected Geneva re-render replaced the originals on 2026-08-12, no
    # derive was queued, so all 1,189 mp3s stayed at their 2026-08-01 vintage —
    # the defective set, the "God created the HORN" one — and the public page
    # went on playing it under a title claiming the corrected text. Same class
    # of inversion as the "(pågår)" title above, from the same root: a
    # publishing step suppressed for throughput and then never re-run.
    # ▶ Suppress the derive PER FILE (throughput), submit ONE for the item at
    # the end (correctness). One queued task, not 1,189.
    # ⚠ RESUMING IS SAFE AND CHEAP: checksum=True skips every file already
    # present with a matching MD5, so a rate-limited run is re-run, not redone.
    res = upload(meta_src["identifier"], files=files, metadata=metadata,
                 retries=6, retries_sleep=20, verbose=True, checksum=True,
                 queue_derive=False)
    bad = [r for r in res if getattr(r, "status_code", 200) not in (200, None)]
    print(f"\nuploaded {len(res) - len(bad)}/{len(res)} requests, {len(bad)} failed")
    if bad:
        for r in bad[:10]:
            print("  FAILED:", getattr(r, "url", "?"), getattr(r, "status_code", "?"))
        sys.exit(1)
    write_metadata(meta_src["identifier"], metadata, title)

    # ONE derive for the whole item, after every file has landed. remove_derived
    # rebuilds derivatives that already exist — without it derive.php skips them
    # and a re-render's replaced originals keep their stale mp3s (see above).
    # reduced_priority makes the task far likelier to be accepted while a big
    # upload's queue is still draining; it may then sit for a long time, which
    # is fine — nothing we ship waits on it.
    # Best-effort BY DESIGN: the files and the metadata are already correct at
    # this point, and this runs unattended from finish_sidecars.py. A derive
    # that cannot be queued must not turn a good upload into a failed run —
    # it must be LOUD instead, so the next session re-submits it by hand.
    # ⚠⚠⚠ THE DERIVE IS NOW CONDITIONAL. READ THIS BEFORE MAKING IT
    # UNCONDITIONAL AGAIN — an unconditional `remove_derived="*"` is what
    # jammed the account for three days (2026-08-15 to 08-18).
    # WHAT HAPPENED: a SIDECAR-ONLY run (uploading .w.json word timings, which
    # have no derivatives at all and change no audio) still fired a full
    # remove_derived rebuild of all 1,362 cu originals. That derive was still
    # RUNNING three days later; archive.org works an item's tasks IN ORDER, so
    # the 150 archive.php tasks from the next cu run queued behind it, and 150
    # is the per-access-key ration — so every other upload, on every other
    # item, was blocked too. gnv had the same thing running for six days.
    # THE RULE:
    #   audio REPLACED  -> derive(remove_derived="*")  the ONLY case that needs
    #                      it: stale mp3s must be torn down and rebuilt, or the
    #                      web player keeps serving the old take (the Geneva
    #                      "God created the HORN" incident, 2026-08-12).
    #   audio ADDED     -> derive()  plain; archive.org derives what lacks
    #                      derivatives and leaves everything else alone.
    #   neither         -> NO DERIVE. Sidecars and metadata produce no
    #                      derivatives; queuing one is pure cost and is exactly
    #                      the mistake above.
    # `queue_derive=False` on upload() is CORRECT and stays: it suppresses the
    # per-FILE derive tasks (1,362 of them). It was never the bug — this was.
    try:
        # `item` was never bound in this function (only `_pre`, the pre-run
        # state) - every derive died on NameError, sv Sirach 2026-09-23.
        item = get_item(meta_src["identifier"])
        if audio_replaced:
            item.derive(remove_derived="*", reduced_priority=True)
            print(f"derive queued (remove_derived=*) — {len(audio_replaced)} "
                  f"replaced originals have stale derivatives")
        elif audio_new:
            item.derive(reduced_priority=True)
            print(f"derive queued (plain) — {len(audio_new)} new chapters")
        else:
            print("no derive queued: no audio was added or replaced. "
                  "Sidecars and metadata have no derivatives, and an "
                  "unnecessary remove_derived rebuild blocks the item's "
                  "queue for days.")
    except Exception as e:                                    # noqa: BLE001
        print(f"\n⚠ DERIVE NOT QUEUED: {e}")
        print("  Files and metadata ARE correct; only archive.org's own")
        print("  derivatives (mp3/png used by the item's web player) are stale.")
        print(f"  Re-run by hand:  ia tasks {meta_src['identifier']} "
              f"--cmd derive.php")

    print(f"\nDONE -> https://archive.org/details/{meta_src['identifier']}")


def selftest():
    """Known-good / known-bad controls on synthetic fixtures. NO network.

    ⛔ Never reads narration/, never reaches archive.org, never uploads —
    every fixture lives in a `tempfile.mkdtemp()` and is removed afterwards.
    The only real things it reads are this file's own constants and the
    syntactically-parsed build_audio_index_gen.py (assertion 5).
    """
    global _IN_SELFTEST
    _IN_SELFTEST = True
    fails = []

    def ok(cond, what):
        print(("ok   - " if cond else "FAIL - ") + what, flush=True)
        if not cond:
            fails.append(what)

    import tempfile
    import shutil
    import contextlib

    _MISSING = object()

    root = tempfile.mkdtemp(prefix="upload_narration_selftest_")
    try:
        def mkname(rel, body, r):
            p = Path(r) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body if isinstance(body, bytes)
                          else body.encode("utf-8"))
            return p

        # A synthetic set shaped like the flat KJV item, so the flat
        # remote_name() mapping is exercised too (assertion 7 relies on it).
        flat_meta = dict(SETS["en"])
        type7 = {"asset": "synthetic", "flat": "kjv_{b}_{c}.ogg"}

        # ── 1. the MD5 comparison is the instrument ──────────────────────
        r1 = Path(root) / "case1"
        a1 = mkname("0/0.ogg", b"ALPHA", r1)
        b1 = mkname("0/1.ogg", b"BETA", r1)
        c1 = mkname("0/2.ogg", b"GAMMA", r1)
        oggs1 = sorted(r1.rglob("*.ogg"))
        remote1 = {
            "kjv_0_0.ogg": "a" * 32,          # same NAME, DIFFERENT md5 -> replaced
            "kjv_0_1.ogg": _md5(b1),          # matches both ways       -> unchanged
            # kjv_0_2.ogg absent remotely      -> to send
        }
        new1, rep1 = plan_upload(oggs1, r1, flat_meta, remote1)
        ok(new1 == ["kjv_0_2.ogg"] and rep1 == ["kjv_0_0.ogg"],
           f"1. MD5 diff: name-match/content-differs -> replaced {rep1}, "
           f"absent -> to-send {new1}, matching -> neither")

        # ── 2. the false-positive control (matters most) ──────────────────
        remote2 = {f"kjv_0_{i}.ogg": _md5(p)
                   for i, p in enumerate([a1, b1, c1])}
        new2, rep2 = plan_upload(oggs1, r1, flat_meta, remote2)
        # ⚠ `files` is keyed by the REMOTE NAME, exactly as build() keys it —
        # keying it by the local path makes every lookup miss and would look
        # like a genuine "old every file" bug in the code under test.
        files2 = {remote_name(p.relative_to(r1), flat_meta): str(p)
                  for p in oggs1}
        o1, un1 = outstanding_files(files2, remote2)
        ok(new2 == [] and rep2 == [] and len(o1) == 0 and un1 == 3,
           f"2. every local file matches by name AND md5 -> 0 replaced, 0 new, "
           f"0 to send ({un1} unchanged); a tool that always finds work is as "
           f"useless as one that never does")

        # ── 2b. the control is genuinely live: name-only DIFF must break it ─
        # Mirrors the end-to-end known-bad run inside the assertion itself, so
        # a future edit that unhooks HEXAPLA_NAME_ONLY_DIFF from the diff FAILS
        # here rather than only at the CLI level.
        _saved_flag = os.environ.get("HEXAPLA_NAME_ONLY_DIFF")
        os.environ["HEXAPLA_NAME_ONLY_DIFF"] = "1"
        try:
            _flag_live = name_only_diff()          # read INSIDE the window
            new2b, rep2b = plan_upload(oggs1, r1, flat_meta, remote1)
        finally:
            if _saved_flag is None:
                os.environ.pop("HEXAPLA_NAME_ONLY_DIFF", None)
            else:
                os.environ["HEXAPLA_NAME_ONLY_DIFF"] = _saved_flag
        ok(_flag_live and new2b == ["kjv_0_2.ogg"] and rep2b == [],
           f"2b. under HEXAPLA_NAME_ONLY_DIFF=1 the SAME fixture loses its "
           f"replaced file (replaced {rep2b!r}, was ['kjv_0_0.ogg']) — the "
           f"known-bad control is live, not decorative")

        # ── 3. the no-files branch still writes metadata ──────────────────
        calls = []
        # ⚠ The package is NOT imported at module scope — the real code imports
        # it lazily inside build()/write_metadata(). If it is not installed,
        # assertion 3 cannot drive the real branch, so it must REPORT that it
        # could not run, ⛔ never pass.
        try:
            import internetarchive as _ia_mod
            _ia_ok = True
            _real_get_item = getattr(_ia_mod, "get_item", None)
        except ImportError:
            _ia_mod = None
            _ia_ok = False
            _real_get_item = None

        # ⛔ The stub is installed ONLY while assertion 3 drives the branch, and
        # ALWAYS restored — an unconditional install whose restore sits inside
        # the `if _ia_ok:` block leaks the stub into every later assertion that
        # inspects the real write_metadata (assertion 6 did exactly that).
        _real_write_metadata = write_metadata

        # ⛔⛔ build() does `from internetarchive import upload, get_item`
        # INSIDE the function body. `from X import Y` re-resolves Y out of
        # sys.modules[X] at CALL time, so patching the module's attribute alone
        # does NOT intercept it. Verified the hard way: with only the attribute
        # patched, a driven build() reached archive.org for real. The module
        # OBJECT is therefore swapped in sys.modules for the duration, which is
        # the seam `from ... import` actually consults.
        def _swap_ia_attrs(mod):
            """Set the fakes on `mod`; return the previous values to restore."""
            saved = {k: mod.__dict__.get(k, _MISSING)
                     for k in ("upload", "get_item", "get_session")}
            mod.upload = _fake_upload
            mod.get_item = _fake_get_item
            mod.get_session = lambda *a, **k: _Sess()
            return saved

        def _restore_ia_attrs(mod, saved):
            for k, v in saved.items():
                if v is _MISSING:
                    mod.__dict__.pop(k, None)
                else:
                    setattr(mod, k, v)

        # A fake item and session are needed by the real branch that decides
        # "nothing to send" (outstanding == {}) and by the task-catalog
        # warning. ⛔ Type-honest: build() reads the pre-item's `.identifier`,
        # `.exists`, `.files` (dicts with "name"/"md5"), the live item's
        # `.metadata["title"]`, and the catalog tick's `.color` /
        # `.submittime` / `.cmd` / `.task_id` — all reproduced below.
        def _Pre3(remote):
            return type("_Pre", (), {
                "identifier": SETS["tyn"]["identifier"],
                "exists": True,
                "files": [{"name": n, "md5": m} for n, m in remote.items()],
                "metadata": {"title": SETS["tyn"]["title"]},
            })()

        class _Here:
            identifier = SETS["tyn"]["identifier"]
            color = "green"
            submittime = "2026-09-22T00:00:00Z"
            cmd = "derive.php"
            task_id = "t1"

        class _Sess:
            def get_my_catalog(self):
                return [_Here()]

        class _Item3:
            def __init__(self, *a, **k):
                pass

            def modify_metadata(self, *a, **k):
                return type("R", (), {"status_code": 200})()

            def derive(self, *a, **k):
                raise AssertionError(
                    "selftest queued a derive — a no-files run must not")

        _docs = {}
        _the_files = {}

        # ⚠ THE REAL BRANCH IS DRIVEN, NOT IMITATED. This is build()'s own
        # "if not outstanding" path, with its own early return and its own two
        # print() calls. Deleting the metadata write from that path, or the
        # dry-run wording, makes this assertion FAIL.
        #
        # ⛔⛔ NARRATION IS REBOUND TO THE TEMP ROOT FOR THE DURATION, AND
        # ALWAYS RESTORED. build() reads `src = NARRATION / set_key`; left
        # pointing at the live tree it would walk the REAL narration/tyn (451
        # real chapters) and read the REAL item — a network call, which this
        # selftest must never make.
        r3 = Path(root) / "case3"
        for i, body in enumerate([b"ALPHA", b"BETA", b"GAMMA"]):
            mkname(f"tyn/0/{i}.ogg", body, r3)
            mkname(f"tyn/0/{i}.json", b"{}", r3)
        remote3 = {}
        for i in range(3):
            remote3[f"0/{i}.ogg"] = _md5(r3 / "tyn" / "0" / f"{i}.ogg")
            remote3[f"0/{i}.json"] = _md5(r3 / "tyn" / "0" / f"{i}.json")

        def _fake_get_item(ident, *a, **k):
            _docs["n"] = _docs.get("n", 0) + 1
            if _docs["n"] == 1:
                return _Pre3(remote3)
            return _Item3()

        def _fake_upload(ident, files=None, **k):
            # ⛔ NOTHING IS UPLOADED. Remember what would have been sent, so
            # assertion 3 can prove the outstanding set is empty, then return
            # as if every request succeeded.
            _the_files.update(files or {})
            return [type("R", (), {"status_code": 200})()]

        _real_sess = None
        if _ia_ok:
            _real_sess = getattr(_ia_mod, "get_session", None)

        _real_narration = globals()["NARRATION"]
        if _ia_ok:
            globals()["NARRATION"] = r3
            # ⚠ write_metadata is stubbed for the duration of the drive ONLY.
            # It has to be: the real one calls get_item -> archive.org. The
            # branch's CALL to it is what is under test here (metadata is
            # reached, not skipped); the write itself is assertion 6's subject.
            globals()["write_metadata"] = (
                lambda ident, meta, title: calls.append((ident, title))
                or print("title verified: <stub>"))
            _saved_attrs = _swap_ia_attrs(_ia_mod)
            # ⛔ ALSO swap the module OBJECT in sys.modules — `from X import Y`
            # (used inside build()) resolves through it, not the attribute.
            _saved_sys_mod = sys.modules.get("internetarchive")
            sys.modules["internetarchive"] = _ia_mod
            try:
                out3 = io.StringIO()
                with contextlib.redirect_stdout(out3):
                    build("tyn", dry_run=True)
                s3 = out3.getvalue()
            finally:
                _restore_ia_attrs(_ia_mod, _saved_attrs)
                if _saved_sys_mod is not None:
                    sys.modules["internetarchive"] = _saved_sys_mod
                globals()["write_metadata"] = _real_write_metadata
                globals()["NARRATION"] = _real_narration
            ok(("Nothing to upload" in s3)
               and ("metadata NOT written" in s3)
               and ("would still write metadata and verify the title" in s3)
               and (len(_the_files) == 0),
               "3. every local file matching -> the REAL no-files branch is "
               "reached: it says «Nothing to upload», sends nothing, and "
               "--dry-run says in words that metadata was NOT written — "
               "deleting that write from the branch now FAILS here")

            # ── 3b. the SAME branch, NOT dry-run, REACHES write_metadata ────
            # ⚠ --dry-run correctly does NOT write, so the call itself can only
            # be observed on a real run. Same fakes as 3, re-installed: this
            # second drive is OUTSIDE the `finally` above, so it must arm its
            # own guard or it escapes to archive.org (it did, before this).
            calls.clear()
            _docs["n"] = 0          # reset so the 1st get_item is the pre-state
            globals()["NARRATION"] = r3
            globals()["write_metadata"] = (
                lambda ident, meta, title: calls.append((ident, title))
                or print("title verified: <stub>"))
            _saved_attrs = _swap_ia_attrs(_ia_mod)
            _saved_sys_mod = sys.modules.get("internetarchive")
            sys.modules["internetarchive"] = _ia_mod
            try:
                out3b = io.StringIO()
                with contextlib.redirect_stdout(out3b):
                    build("tyn", dry_run=False)
                s3b = out3b.getvalue()
            finally:
                _restore_ia_attrs(_ia_mod, _saved_attrs)
                if _saved_sys_mod is not None:
                    sys.modules["internetarchive"] = _saved_sys_mod
                globals()["write_metadata"] = _real_write_metadata
                globals()["NARRATION"] = _real_narration
            ok(len(calls) == 1
               and calls[0][0] == SETS["tyn"]["identifier"]
               and "Writing metadata anyway - files current != metadata current"
               in s3b,
               f"3b. with files current and NO --dry-run, the branch still "
               f"reaches write_metadata() — {len(calls)} call(s) for "
               f"{calls[0][0] if calls else None!r}. ⛔ The early return that "
               f"made a metadata-only correction unpublishable is GONE, and "
               f"putting it back FAILS here")
        else:
            ok(False,
               "3. the no-files branch could not be exercised: the "
               "`internetarchive` package is not installed on this box, so "
               "build() cannot be driven. ⛔ A check that cannot run did not "
               "pass.")

        # ── 4. apocrypha_clause: names the GAPS, and is ABSENT without ─────
        r4 = Path(root) / "case4"
        apoc = [mkname(f"{s}/0.ogg", b"A", r4)
                for s in (68, 72, 74, 75, 77)]
        clause4 = apocrypha_clause(apoc, r4)
        ok("68, 72, 74-75, 77" in clause4 and "73" not in clause4
           and "76" not in clause4 and APOCRYPHA_NOTE.format(
               slots="x", n=0)[:12] in clause4,
           f"4a. apocrypha_clause names the slots AND PRINTS THE GAPS — a hole "
           f"between 72 and 74 reads as 68, 72, 74-75, 77, not as a smoothed "
           f"68-77: {clause4[clause4.find('slots'):][:60]!r}")

        canon_only = [mkname(f"{b}/0.ogg", b"C",
                             Path(root) / "case4b") for b in (0, 1, 65)]
        ok(apocrypha_clause(canon_only, Path(root) / "case4b") == "",
           "4b. a set with NO slot >= 66 gets an ABSENT clause (\"\"), so its "
           "description stays byte-identical to what it has always said")

        # ── 5. index_reaches_apocrypha: True / False / None ───────────────
        # Three DISTINCT builder entries, so the three states are genuinely
        # distinguishable: an entry whose apocrypha is True, one whose
        # apocrypha is False (explicitly absent), and no entry at all.
        # ⚠ The identifiers are the REAL ones, and the entry for `sv` is keyed
        # by the identifier of the item the uploader calls `sv` and the builder
        # calls `kxii` — the join is on the identifier, not the set key.
        ident_ylt = SETS["ylt"]["identifier"]
        ident_wbt = SETS["wbt"]["identifier"]
        ident_sv = SETS["sv"]["identifier"]
        synth_sets = [{"item": ident_ylt, "apocrypha": True},
                      {"item": ident_wbt, "apocrypha": False},
                      {"item": ident_sv, "apocrypha": True}]
        r5 = Path(root) / "case5"
        mkname("build_audio_index_gen.py",
               "SETS = " + repr(synth_sets) + "\n", r5)
        real_file = globals()["__file__"]
        globals()["__file__"] = str(r5 / "upload_narration.py")
        try:
            t5 = index_reaches_apocrypha("ylt")    # entry, apocrypha True
            f5 = index_reaches_apocrypha("wbt")    # entry, apocrypha False
            n5 = index_reaches_apocrypha("nope")   # no identifier    -> None
            sv5 = index_reaches_apocrypha("sv")    # sv -> kxii's item, True
            real_keys = set(NARRATION_DIR_OF) == set(SETS)
        finally:
            globals()["__file__"] = real_file
        ok(t5 is True and f5 is False and n5 is None and sv5 is True
           and real_keys,
           f"5. index_reaches_apocrypha joins on the archive.org IDENTIFIER "
           f"and returns three DISTINCT states — True {t5!r}, False {f5!r}, "
           f"None {n5!r}; sv ({ident_sv}) joins to the builder's own entry and "
           f"reads {sv5!r}")

        out5 = io.StringIO()
        with contextlib.redirect_stdout(out5):
            reach = n5
            if reach is True:
                print("The index REACHES them")
            elif reach is False:
                print("today's index CANNOT reach them")
            else:
                print("⛔ COULD NOT DETERMINE whether the index reaches them — "
                      "build_audio_index_gen.py was unreadable. Check by hand; "
                      "this is not a clean result.")
        ok("COULD NOT DETERMINE" in out5.getvalue()
           and "CANNOT reach" not in out5.getvalue(),
           "5b. the None state PRINTS «COULD NOT DETERMINE» and is not rendered "
           "as False — a failed read must not be indistinguishable from a real "
           "verdict")

        # ── 6. FINDING: `title verified:` is TITLE-ONLY ────────────────────
        # write_metadata compares ONLY `get_item(identifier).metadata["title"]`.
        # A remote whose title matches but whose DESCRIPTION lacks the
        # apocrypha clause still verifies — labelled a FINDING, not a fix, and
        # the check is deliberately NOT widened.
        real_title = SETS["sv"]["title"]
        src6 = importlib.import_module("inspect").getsource(write_metadata)
        title_only = ('live != title' in src6
                      and 'metadata.get("title"' in src6
                      and "description" not in src6)
        ok(title_only,
           "6. FINDING (not a fix): `title verified:` compares the TITLE ONLY — "
           "a remote whose title matches but whose description LACKS the "
           "apocrypha clause still passes. Pinned, NOT widened")

        # ── 7. the set key is not the directory ───────────────────────────
        r7 = Path(root) / "case7"
        kjv_ogg = mkname("en/0/0.ogg", b"KJV", r7)
        name7 = remote_name(kjv_ogg.relative_to(r7 / "en"), type7)
        parser = argparse.ArgumentParser(prog="upload_narration.py")
        parser.add_argument("set", choices=sorted(SETS))
        err_kxii = err_sv = None
        _err_buf = io.StringIO()
        try:
            # ⚠ argparse writes its usage error to stderr; capture it so one
            # EXPECTED bad choice does not spray a traceback-shaped line over
            # an otherwise clean selftest run.
            with contextlib.redirect_stderr(_err_buf):
                parser.parse_args(["kxii"])
        except SystemExit as e:
            err_kxii = e.code
        try:
            ns = parser.parse_args(["sv"])
            err_sv = ns.set
        except SystemExit:
            err_sv = "ERROR"
        ok(name7 == "kjv_0_0.ogg"
           and err_kxii == 2 and err_sv == "sv"
           and NARRATION_DIR_OF.get("en") == "en"
           and "kxii" not in SETS,
           f"7. the set key is NOT the directory: narration/en publishes as the "
           f"item's flat name {name7!r}; `kxii` is an argparse error "
           f"(rc {err_kxii}) while `sv` is valid ({err_sv!r})")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("", flush=True)
    if name_only_diff():
        print("⚠ KNOWN-BAD CONTROL ACTIVE: HEXAPLA_NAME_ONLY_DIFF=1 — the "
              "local/remote diff uses FILENAMES only and ignores MD5, hiding "
              "every content replacement", flush=True)
    print(f"{len(fails)} failure(s)", flush=True)
    return 1 if fails else 0


_PROG = None


def _main(argv=None):
    argv = sys.argv if argv is None else argv
    if "--selftest" in argv[1:]:
        sys.exit(selftest())
    ap = argparse.ArgumentParser(prog=_PROG)
    ap.add_argument("set", choices=sorted(SETS))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv[1:])
    build(a.set, a.dry_run)


if __name__ == "__main__":
    # ⚠ THE `set` POSITIONAL IS REQUIRED, SO `--selftest` CANNOT BE A FLAG IN
    # THIS PARSER: argparse rejects a bare `--selftest` with rc 2 and a usage
    # line BEFORE any branch in this file runs. Dispatching here — on the
    # truthiness of the program name — is the only route that leaves every
    # existing invocation byte-for-byte identical, including the usage string
    # in `--help` and the error text for a missing set.
    _PROG = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] \
        else "upload_narration.py"
    _main()
