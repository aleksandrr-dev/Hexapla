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
"""
import argparse
import json
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
    "en": {
        "asset": "en_kjv.json",
        "identifier": "hexapla-audio-en",
        "flat": "kjv_{b}_{c}.ogg",
        # Complete for its purpose, not a canon in progress — see SCOPE_NOTE.
        "scope_note": True,
        "title": "The King James Bible (1611) — narrated audio for the books LibriVox does not cover",
        "title_partial": "The King James Bible (1611) — narrated audio for the books LibriVox does not cover",
        "translation": "King James Version, 1611",
        "language": "eng",
        "voice": "Kokoro text-to-speech (Apache-2.0), voice am_adam",
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
Revelation). Each audio file has a matching <code>.json</code> sidecar
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
        print(f"note      : {extra} rendered chapters sit in apocrypha slots "
              f"(66+). They upload, but today's index CANNOT reach them "
              f"(build_audio_index_gen.py slices [:CANON_BOOKS]).")
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

    def _md5(path):
        import hashlib
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    audio_new, audio_replaced = [], []
    for _f in oggs:
        # ⚠ MUST use the same mapping as the upload itself. With a flat set,
        # comparing "<b>/<c>.ogg" against an item that holds "kjv_<b>_<c>.ogg"
        # makes every existing file look NEW, which queues a full derive over
        # 245 chapters that did not change.
        _name = remote_name(_f.relative_to(src), meta_src)
        if _name not in _remote:
            audio_new.append(_name)
        elif _remote[_name] and _md5(_f) != _remote[_name]:
            audio_replaced.append(_name)
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
    # Write metadata explicitly, so it lands on new AND pre-existing items.
    # Verified afterwards rather than trusted: a stale "in progress" title on a
    # finished set is a public false claim, and it is the one thing here that
    # no amount of successful file uploads would reveal.
    item = get_item(meta_src["identifier"])
    r = item.modify_metadata(metadata)
    code = getattr(r, "status_code", None)
    if code not in (200, None):
        print(f"\nMETADATA WRITE FAILED: HTTP {code}")
        sys.exit(1)
    live = get_item(meta_src["identifier"]).metadata.get("title", "")
    if live != title:
        print("\n⚠ metadata written but the live title does not match yet:")
        print(f"    want: {title}")
        print(f"    live: {live}")
        print("  archive.org applies metadata edits through its task queue;")
        print("  re-check before treating the item as published.")
    else:
        print(f"\ntitle verified: {live}")

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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("set", choices=sorted(SETS))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    build(a.set, a.dry_run)
