# KJV IN THE OWNER'S VOICE — RUNBOOK (written 2026-08-23)

★ **DECISION (owner, 2026-08-23): "it'll be entire KJV. but after ylt finishes."**
Re-render the **whole** King James Bible with the owner's cloned voice
(chatterbox, `narration/_en_ref_ylt.wav`), replacing the Kokoro `am_adam`
narration. **1,371 chapters** — 1,189 canonical + 182 apocrypha.

⛔ **GATE: DO NOT START WHILE ylt IS RENDERING.** One GPU. ylt was at 23/1189 on
2026-08-23 and is the committed job. Check `find narration/ylt -name '*.ogg' |
wc -l` against 1189 before touching anything here.

---

## 1. WHY THIS EXISTS — the defect that forces the scope

The owner wanted apocrypha *announcements* for KJV in the new voice. That
cannot be done on its own: the existing KJV audio is Kokoro `am_adam`, so a
new-voice announcement spliced onto an `am_adam` chapter puts the seam **inside
every chapter**. Mixing voices inside one set is the defect that quarantined 72
Wycliffe chapters (`narration/wyc_quarantine_am_adam`).
▶ Therefore the announcements imply the render, and the render is all-or-nothing.

## 2. STATE AS MEASURED 2026-08-23 — re-measure, do not trust these

| | value |
|---|---|
| KJV canonical chapters | 1,189 |
| KJV apocrypha chapters (14 non-empty books in `en_kjv.json`) | 182 |
| **Total to render** | **1,371** |
| Rendered today (`narration/en`, Kokoro am_adam) | 492 |
| Live on `hexapla-audio-en` | 245 ogg, **0 sidecars** |
| Apocrypha books never rendered at all | 4 — Tobit (14), Baruch (6), Prayer of Manasses (1), 2 Maccabees (15) = 36 ch |

## 3. ★ THE ARCHITECTURE ALREADY SUPPORTS THIS — no Kotlin change needed

`ReadingService` (~L246) builds the KJV index as
`putAll(librivox); putAll(generated)` — **generated goes in LAST and wins any
key collision**, and the comment says so explicitly. So publishing a full
generated KJV set makes it take precedence for every book automatically.

⚠⚠ **AND THAT IS THE THING TO CONFIRM BEFORE STARTING.** It means shipping a
full generated KJV **silently retires the LibriVox human narration for all 50
books it covers**. That is a product decision, not a technical one: LibriVox is
a *human* reading and some listeners prefer it to any synthetic voice, however
good the clone. The two book sets are currently disjoint, so nothing is lost
today; after this, everything is.
▶ **Get an explicit yes on retiring LibriVox before rendering 1,371 chapters.**

## 4. THREE DECISIONS STILL OPEN

1. **Retire LibriVox?** See §3. Blocking.
2. **Which archive.org item?** `hexapla-audio-en` is *designed* as a permanent
   extension — its title is "narrated audio for the books LibriVox does not
   cover", it uses FLAT names `kjv_{b}_{c}.ogg`, and `upload_narration.py`'s own
   note calls its 492/1,189 partial state "the INTENDED end state". A full set
   is a different artifact.
   · **Option A** — new item (e.g. `hexapla-audio-kjv-1611`): the old item stays
     honest and untouched; no am_adam/clone mixing is even possible. Preferred.
   · **Option B** — expand `hexapla-audio-en`: must rewrite title,
     `scope_note`, `title_partial`, and REPLACE all 245 live am_adam chapters.
3. ~~**`Revelation` clip.**~~ ★ **DECIDED (owner, 2026-08-23): render a new
   clip saying «Revelation», to match the KJV title.** Do NOT reuse ylt's
   «Revelation of John». Build it with the other 14 in step 3.

## 5. ANNOUNCEMENTS — 215 of 230 are already done

`--set en` needs **230** components (80 book names + 150 chapter numbers).

- **150 chapter numbers — reuse ylt's outright.** Verified 2026-08-23: no book
  differs in chapter count between the assets and both max at Psalms 150.
- **65 of 66 canonical book names — reuse ylt's.** This works only because
  `_ROMAN_ORDINAL` now also maps arabic `1/2/3` (ylt writes «I Samuel», KJV
  writes «1 Samuel»; both must speak "First Samuel"). Without that, 17 names
  mismatch on text alone while their AUDIO is already correct.
- **15 genuinely new**: `Revelation` (owner-decided 2026-08-23 to match the
  KJV title, not ylt's «Revelation of John») + the 14 apocrypha names —
  First Esdras · Second Esdras · Tobit · Judith · Wisdom of Solomon · Sirach ·
  Baruch · Prayer of Manasses · First Maccabees · Second Maccabees ·
  Additions to Esther · Prayer of Azariah · Susanna · Bel and the Dragon.

★ **BUILD THE 15 WITH VOICE CONVERSION, NOT RESPELLING** — see
`docs/NARRATION.md` "PRONUNCIATION: USE VOICE CONVERSION". Chatterbox
`generate()` takes text only and will not stress syllable 3 of a 4-syllable
word, which is how six respelling rounds failed on «Obadiah». Cut the correctly
pronounced word from a Kokoro render and run `ChatterboxVC` with
`target_voice_path=_en_ref_ylt.wav`.
⚠ The existing `narration/en` am_adam render is itself a usable donor for the
apocrypha names — it already covers 10 of the 14 apocrypha books.

## 6. STEPS

```
0. GATE: ylt render complete (1189/1189).
1. Switch LANG_CONFIG["en"] in narrate.py to chatterbox + _en_ref_ylt.wav.
   ⚠ Until this is done, `build_announcements.py --set en --components` CRASHES
     ON PURPOSE (the set declares chatterbox; LANG_CONFIG["en"] carries no
     voice/language_id/cfg_weight). A crash is the intended guard against
     quietly synthesizing in the WRONG voice.
2. cp narration/ylt_announce_lib/*.wav narration/en_announce_lib/   (215 reused)
   ⚠ Copy at THIS moment, not earlier - a copy made in advance goes stale
     silently if any ylt clip is revised.
3. Build the 15 new components (VC per §5), then run ALL THREE gates:
   tail_energy <= 0.30, looks_doubled == 0, duration <= ~3000 ms,
   trailing_partial_repeat == false. Then --reel and get an ear on them.
4. Render 1,371 chapters under render_supervisor.ps1 -Lang en.
   (Rate reference: ylt ran ~6 ch/hr on this GPU. Budget accordingly.)
5. apply_announcements --set en   (and AGAIN at the end of the render -
   chapters rendered after a splice get a synthesized head).
6. Screens before upload: offset_drift.py, tail_hallucinations.py,
   verse_tail_scan.py - all three, gating on child return codes.
7. build_audio_index_gen.py for kjv; rebuild after the splice because the
   splice moves verse offsets (ylt's moved -229/+461 ms).
8. Upload per the item decision in §4.2.
```

## 7. LANDMINES

- ⚠⚠ **The `en` item uses FLAT names** `kjv_{b}_{c}.ogg`, not `<book>/<ch>.ogg`.
  `remote_name()` must be used on BOTH sides of the new/replaced comparison or
  the uploader will re-send everything.
- ⚠ **`component_texts()` covered only `range(66)` until 2026-08-23**, so no
  apocrypha name existed for ANY set and `apply_announcements --set ru`
  reported "1192 chapters, 0 errors" while silently skipping 170. Fixed, but
  re-check the count against the asset, not against a remembered number.
- ⚠ **A derive blocks an item's whole queue.** archive.org works one item's
  tasks in order; on 2026-08-23 a single `derive.php` at priority -6 on the wyc
  item held ~1,000 `archive.php` tasks for 4+ hours and blocked every other
  upload via the account ration. Expect the same after a 1,371-chapter upload.
- ⚠ **ru/cu apocrypha announcements are still missing** (12 components, 170
  chapters each) and are a SEPARATE job from this one.
- ⚠ Do not lower `TAIL_LONG_GAP_MS`/`TAIL_LONG_MIN_RUN_MS` in narrate.py, and
  keep `cut_tail=False` for announcement components.
