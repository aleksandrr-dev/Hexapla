# Geneva 1599 generated narration — wiring runbook

Prepared 2026-07-31, while the render was at **995/1189**. Everything below is
verified against the tree as it stood that day; re-verify the numbers before
acting, don't trust them.

**Nothing here is done yet.** The one code change that could be made safely in
advance IS made: the `gen1599` entry sits commented in
`tools/build_audio_index_gen.py`, with the values already checked.

---

## THE TWO IDENTIFIERS THAT ARE EASY TO GET WRONG

| | value | why |
|---|---|---|
| app translation id (`tid`) | **`gen1599`** | from `Bible.kt` — «Geneva Bible, 1599 (EN)» |
| narration folder (`dir`)   | **`gnv`**     | `Hexapla-releases/narration/gnv/` |

⚠ **They differ.** `AudioRepo.generated()` looks the index up by the *app* id,
so keying it `gnv` produces an index the app silently never consults — no
crash, no error, just no audio. Same tid/dir split as the Swedish `kxii`/`sv`.

Archive item: **`hexapla-audio-geneva-1599`** (matches the `hexapla-audio-<name>-<year>`
convention of `hexapla-audio-webster-1833`, `hexapla-audio-karlxii-1703`).
The label says **1599**, not 1560 — use 1599.

---

## PREFLIGHT — ALREADY RUN 2026-07-31, RE-RUN BEFORE ACTIVATING

Verified against `assets/bibles/en_geneva.json`:

    geneva asset grid : 83 book slots, 1189 chapters (apocrypha slots empty)
    rendered          : 995 / 1189
    remaining         : 194  — Luke 23 onward: book 41 (2 left), books 42-65 whole
    sidecars          : 995 .json for 995 .ogg — 1:1, none missing
    offsets           : present and populated → verse-following will work
    stray files       : 0 outside the grid

★ The sidecars matter: `Section.offsets` drives verse highlighting and
exact seek-to-verse for recorded audio. A chapter with an `.ogg` but no
`.json` still plays, but loses both. `partial: False` hard-fails on a missing
sidecar, which is the gate we want.

Re-run the preflight with:

```bash
python tools/build_audio_index_gen.py --dry-run
```

---

## ACTIVATION SEQUENCE — IN THIS ORDER

**1. Wait for the render to reach 1189/1189.** Confirm by count, not by a log
line:

```bash
find C:/Projects/Hexapla-releases/narration/gnv -name "*.ogg" | wc -l
```

**2. Upload to archive.org as `hexapla-audio-geneva-1599`:**

```bash
python tools/upload_narration.py gnv --dry-run
```

then without `--dry-run`. **The tooling and Geneva's metadata already exist**
in `tools/upload_narration.py` — identifier, title, translation, language,
voice, subjects, PD licence, `cover.jpg`, and the `<book>/<chapter>.ogg` +
sidecar layout the index expects. Nothing needs to be written by hand.

★ **The script has an honesty gate**: a set below 1,189 chapters may not
publish under a "complete" title. At 995/1189 it exits with
`995/1189 chapters is a PARTIAL set … Add a title_partial rather than
publishing a 'complete' title.` **That is the gate working — do not add a
`title_partial` to `gnv` just to make it run.** Karl XII has one because it
is deliberately published in progress; Geneva is meant to go up complete.

Wait until the item is public and a chapter URL actually fetches before step 3.

### PRIVACY — POLICY, AND THE ONE FIELD WE CANNOT CONTROL
Owner policy: **no personal name or e-mail anywhere in the metadata.**
Everything the script *writes* complies — `creator` is
`Hexapla (free offline parallel Bible app)`, and no personal name appears in
title, description, subjects or rights. **Keep it that way.**

**BUT archive.org stamps an `uploader` field on every item, automatically,
from the account performing the upload, and it is publicly visible.**
Verified on the live Webster item 2026-07-31:

    uploader = aleksandr@tuta.com

It is account-level: the upload script cannot set, override or suppress it.

✅ **CLOSED BY OWNER DECISION 2026-07-31: risk accepted — "just accept it,
it's fine."** Same documented-deviation pattern as the Van Dyck tashkeel and
Luther 1545 calls: proceed now, respond to feedback if it ever arrives.
▶ **Do NOT re-open this, and do not propose a second archive.org account
each time a new narration set ships.** The decision covers Geneva, Karl XII,
Russian, and any future item uploaded from this account.
▶ It remains true that nothing WE author may name him — the policy above is
unchanged. Only the automatic `uploader` field is accepted.

★ Same decision covers `originalurl` and the description's link to
`https://aleksandrr-dev.github.io/Hexapla/`, which carries the owner's GitHub
handle. It is the app's own public landing page — the same URL as the in-app
QR code and every store listing — so it stays.

**3. Uncomment the `gen1599` entry** in `tools/build_audio_index_gen.py`, then:

```bash
python tools/build_audio_index_gen.py
```

`partial: False` asserts full 1189-chapter coverage and hard-fails on any
missing `.ogg` or sidecar — that assertion IS the upload check, so do not
relax it to `True` to make it pass.

**4. Rebuild.** No Kotlin change is required — the audio path is entirely
index-driven (verified: no translation id is hardcoded anywhere in the audio
or reading code; the only `"gen1599"` in Kotlin is its `Bible.kt` registration).

    ./gradlew bundlePlayRelease        # Play AAB
    ./gradlew assembleRustoreRelease   # RuStore APK

**5. Play-upload gate — re-run the donation-strip check before any Play build:**

```bash
unzip -p app-play-release.apk "classes*.dex" | grep -ac yoomoney
```

Must print `0`.

**6. On-device spot-check.** Geneva → a chapter → verse highlight follows the
audio, and stop/resume lands on the right verse. Then confirm an unrendered
translation still falls back to TTS.

---

## THINGS ALREADY CHECKED SO YOU DON'T RE-CHECK THEM

- **`audio_note` is fine.** CLAUDE.md lists "audio_note string is KJV-worded
  ×13" as still open — **it is NOT; it was fixed.** All 25 locales now read
  generically ("recorded narration where it exists, otherwise the device's
  text-to-speech"). Nothing to reword for Geneva. Correct that CLAUDE.md line.
- **No Kotlin change needed** (see step 4).
- **Download resilience already landed**: `downloadTo` retries 3× with backoff
  and `prefetchAhead` caches the next 2 chapters — the fix for the "reverts to
  TTS after some chapters" bug the owner heard on Webster. Geneva inherits it.

## KNOWN GAP, NOT A BLOCKER

Word-level highlighting does not exist for recorded audio — offsets are
per-verse, so Geneva highlights per verse like Webster. The forced-alignment
idea (WhisperX/MFA → per-word timestamps into the index) is deferred; see the
`ReadingService` notes in CLAUDE.md. Verse-level is the right call for now.
