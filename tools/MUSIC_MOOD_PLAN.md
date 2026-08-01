# Scene-matched background music — execution plan

Owner-approved 2026-07-31. **Scheduled: after Geneva audio ships, before the
Icelandic canon campaign starts.** This file is the prep so the work can begin
without re-deciding anything.

## The decision, as the owner set it

1. **The 4 tracks already in the APK STAY BAKED IN** and remain the offline
   default set. Nobody loses music by being offline — that is the point.
2. **Everything beyond those 4 is a download**, hosted on archive.org, exactly
   like the generated narration.
3. Music is selected **by mood/setting**, and **the classic, iconic scenes
   must have the right mood** — that is the acceptance criterion, not average
   correctness across 1,189 chapters.

## What this is NOT

KJV Dramatized scores its music **into the recording** — composed and edited
against the pacing of individual lines at production time. We layer a bed
under narration at runtime over chapters of unpredictable length. We can match
MOOD well; we cannot match cue-to-line timing. Do not promise otherwise, and
do not try to fake it by mixing music into the rendered narration oggs — that
would defeat the existing music on/off toggle and volume slider, and would
make any future change cost a full re-render of every chapter.

---

## ⚠⚠ THE PITFALL THAT WILL BITE SILENTLY — KEY THE MAP TO CANONICAL KJV

**The mood map MUST be keyed to canonical KJV book/chapter/verse and resolved
through `VerseMap`, never to the displayed translation's own numbering.**

Translations in this app keep their AUTHENTIC native numbering — the Synodal
and Elizabeth psalters are LXX-numbered, Luther and WLC use Masoretic bounds,
Károli keeps Calvin numbering, and so on. A map keyed to "whatever chapter the
reader is showing" would hand Psalm 23 the wrong mood in Russian, and be
subtly wrong across whole books in Hungarian and Czech.

This is not hypothetical — it is the **same defect class already fixed three
times** in this codebase: plan days pinned to the canonical KJV chapter grid
(2464f04), bookmarks pivoted at display time (845f588), and notes/highlights
rekeyed to canonical coordinates in 1.4.2. `chapterIndexFor` was deleted
precisely because it fixed the chapter but never the verse.

▶ Resolve the mood with the same pivot those use. Assert it in a test with a
Synodal psalm, which is where the bug would show first.

Also: apocrypha slots are book indexes ≥66 and are absent from many
translations — the map needs a default for them, and the resolver must not
throw when a slot is empty (see the 1.4.0 `navigateChapter` IndexOOB crash).

---

## Mood taxonomy — 8 moods, plus silence

Deliberately small. More moods means more tracks to license, more curation to
review, and finer distinctions than a background bed can actually convey.

| id | use | anchor examples |
|---|---|---|
| `awe` | creation, theophany, divine majesty | Gen 1 · Job 38-41 · Isa 6 · Ezek 1 · Rev 4-5 |
| `narrative` | default historical prose | most of Gen-Esther · Acts |
| `lament` | grief, penitence, complaint | Lamentations · Ps 22, 51, 88 · Job 3 |
| `judgment` | warning, wrath, plagues | Nahum · much of Jeremiah · Rev 6-19 |
| `praise` | thanksgiving, doxology | Ps 145-150 · Rev 19 |
| `wisdom` | reflective, aphoristic | Proverbs · Ecclesiastes |
| `hope` | comfort, promise, restoration | Isa 40 · Rom 8 · Rev 21-22 |
| `passion` | the cross, the suffering servant | Isa 53 · Mt 26-27 · Mk 14-15 · Lk 22-23 · Jn 18-19 |
| `tender` *(optional 9th)* | intimate, pastoral | Ps 23 · Lk 2 nativity · Song of Songs |

★ **`silence` is a legitimate value and should be used.** For the most solemn
moments — the darkness at the crucifixion, parts of Lamentations — no bed at
all is stronger and safer than any track we could choose. It also costs
nothing to license and cannot be tonally wrong.

## Mapping method — tiered, so the review is humanly possible

Do **not** hand-author 1,189 rows. Three tiers, each reviewable:

1. **Per-book default** — 66 entries (+ apocrypha default). One sitting.
2. **Range overrides** — canonical chapter ranges that depart from the book
   default (Gen 1 `awe`; Gen 6-9 `judgment`; Gen 22 `passion`; Ps grouped in
   runs). Expect roughly 150-250 ranges total.
3. **Iconic anchors** — an explicit, hand-checked list of passages that MUST
   be right. These are the acceptance criterion. Verse-level overrides are
   allowed here and ONLY here, for chapters that genuinely turn mid-way
   (Luke 23 trial → crucifixion; Ps 22 dereliction → praise). Keep them rare;
   a bed that changes constantly is worse than one that is slightly generic.

**Coverage must be script-asserted**: every one of the 1,189 canonical chapters
resolves to exactly one mood, no chapter matched twice, every mood referenced
has at least one licensed track. This mirrors `build_chrono_plan.py`, which
asserts all 1,189 chapters appear exactly once and that the anchor verses say
what the placements assume — copy that discipline, including its habit of
documenting *why* each non-obvious placement was made.

### ⚠ The review gate, and why it exists
A generated mood map is exactly the "plausible-looking output is the failure
mode" class that `ru_stress.py` demonstrated — it looked entirely reasonable
and shipped 30 corrupt entries out of 197. A wrong mood is far lower stakes
than corrupt scripture: nothing false is asserted, and the user can turn music
off. But there are passages where a tonally wrong bed would genuinely offend —
the crucifixion, Lamentations, the imprecatory psalms, Job's suffering.
▶ **The tier-3 anchor list gets read by a human before it ships.** Tiers 1-2
can be drafted and spot-checked. Do not let "it looked fine" stand in for that.

---

## Technical shape

- **Delivery**: reuse the narration path wholesale. `downloadTo` already
  retries 3× with backoff and `prefetchAhead` already caches ahead — both
  landed fixing the "reverts to TTS after some chapters" bug, and music
  inherits them. An index file (`music_index.json`) keyed mood → track list,
  same shape as `audio_index_gen.json`.
- **Archive item**: follow the existing convention, e.g.
  `hexapla-music-<pack>`. `upload_narration.py` is the model; note its honesty
  gate refuses to publish an incomplete set under a complete title.
- **Offline**: the 4 bundled tracks are the fallback for EVERY mood. If a
  mood's downloaded track is missing, fall back to a bundled one rather than
  going silent unintentionally (distinguish that from a deliberate `silence`).
- **Opt-in download**: a "Download music pack" action, size stated up front.
  Once music is out of the APK, catalogue size stops costing install size —
  30 tracks are as cheap as 5.
- **Crossfade is required.** The current implementation hard-swaps only on
  track completion ([ReadingService.kt:450](../app/src/main/java/com/aleks/hexapla/ReadingService.kt)).
  Changing mood at a chapter boundary with a hard swap is jarring. MediaPlayer
  cannot crossfade — needs two players and a volume ramp. Respect the existing
  perceptual `musicVol()` curve (slider squared) on both.
- **Keep a "uniform bed" setting** for people who prefer today's behaviour.

## Free size win, unrelated but do it here
`assets/music/meditation01.mp3` is encoded at **265 kbps** (7.0 MB for 3.5
minutes) while the other three sit at 64-69 kbps. Re-encoding it to match takes
the bundled folder from 17 MB to ~12 MB with no audible difference under
speech at low volume.

    air_prelude    5.7 min   68 kbps
    canon_in_d     5.9 min   69 kbps
    healing        8.7 min   64 kbps
    meditation01   3.5 min  265 kbps   <- outlier
Total bundled music today: 23.8 minutes, which a long listen loops through
more than once — the variety complaint is well founded.

## ★ Instrumentation the owner asked for (2026-07-31)
In priority order:
1. **Lute and harp above all.** Fits the subject matter directly (David's
   harp, the psaltery, temple music) and is acoustically ideal for a bed
   under speech — plucked strings have a gentle attack and natural decay
   instead of a sustained pad competing with the voice. Solo lute, theorbo,
   baroque guitar, harp, psaltery, lyre; Dowland and the Renaissance plucked
   repertoire. ⚠ The composition being 400 years old decides nothing — the
   RECORDING is the layer that has to be licensed.
2. **Orchestral / genuinely "scored"-sounding**, not generic ambient loops —
   the owner likes how KJV Dramatized feels. Prefer real orchestral or
   chamber texture over synth pads, still subject to "no sudden dynamics".
3. **Classical generally**, same two-layer caveat.
Suggested pairing: lute/harp for `tender`, `wisdom`, `lament`, `hope`;
orchestral for `awe`, `judgment`, `praise`, `passion`.
▶ The highest-value find would be a period-instrument ensemble or university
early-music department releasing recordings under CC-BY/CC0. Worth hunting
specifically, even for a small catalogue.

## Licensing — the gate, and the trap that nearly caught us

**ACCEPTABLE: CC0 · CC-BY · CC-BY-SA. REJECTED: NC · ND.**
CC-BY-SA is long-standing practice here — the shipped credits string already
carries five SA assets (Tamil IRV, Sanskrit NT, Latvian Glück, Open Scriptures
Strong's). ShareAlike attaches to the *adapted work* — our re-encoded audio
file, which we license onward as CC-BY-SA and credit. It does **not** reach the
app: bundling or downloading a track beside an app is mere aggregation, not
adaptation of the app. ND is rejected partly because the re-encode above is
itself a derivative.

### ⛔⛔ IMSLP's "Public Domain" AUDIO TAG IS NOT A US PUBLIC-DOMAIN CLAIM
From IMSLP's own `IMSLP:Copyright_Made_Simple`: recordings published **1962 or
earlier** are PD in the EU, **1964 or earlier** in Canada — but in the USA only
**1922 and earlier**, and anything fixed on or before 14 Feb 1972 that was not
published by 1956 stays protected until **2067**.
So IMSLP legitimately tags as "Public Domain" recordings that are fully
protected in the US: EMI 1962, Decca 1961, Deutsche Grammophon 1953, Erato
1964, L'Oiseau-Lyre 1959, Columbia 1963, RCA 1956. For a worldwide Play Store
app these are **BLOCKED**, whatever the tag says.
▶ **The discriminator that works: trust the licence only where the UPLOADER IS
THE PERFORMER** (ideally also the composer). If `Publisher Information` names a
record label, ignore the tag.
This is the layer-separation lesson again — the composition and the recording
are different rights — dressed as a jurisdiction difference.

### Other traps recorded from the sweep
· **Synthesised uploads that look acoustic.** Several IMSLP entries carry
  `Performers=guitare` / `Performers=Classical Guitar` while sitting under a
  Synthesized/MIDI heading. The `Performers` field alone will fool you; we want
  real instruments.
· **Mutopia has no audio at all** — engraved scores, LilyPond sources and
  synthesised MIDI only. No recording layer exists there to license. (It is a
  legitimate fallback only if we ever commission or perform music ourselves,
  which would clear layer 1 by its licence and give us layer 2 outright.)
· **MuseScore audio: do not rely on it.** Most page audio is their playback
  engine rendering a score through sampled instruments, governed by their
  platform terms rather than the uploader's score licence — and those terms
  could not be fetched (403), so they remain unverified. A score licence never
  transfers to a recording.
· **IMSLP blocks scripted download** (bot check on `/images/`). Files must be
  fetched manually in a browser, or by arrangement with IMSLP.
· **US Marine Band** recordings would clear BOTH layers if the federal-work
  status holds — the single most valuable possibility found — but the claim is
  **UNVERIFIED** (their site 403s, no Wayback snapshot of the copyright page).
  Verify from a primary statement before shipping a note of it.

## SOURCING — verified 2026-07-31 (raw-fetched from each source's own page)

### The four pillars, in build order

**1. Kevin MacLeod / incompetech — CC BY 4.0.** Already shipped and credited, so
zero new licensing surface. The catalogue is **1,442 tracks**, not 4; ~114 are
plucked/early instruments at 3-10 min, ~40 genuinely calm. He composes, performs
and records everything himself — one grant covers both layers.
★ His FAQ is the canonical statement of the two-layer rule: *"Is this music
Copyright Free? No. All of this music is copyrighted. Though some of the baroque
and classical compositions are in the public domain; these recordings are not."*
Re-encoding is explicitly permitted (*"chop, splice, compress, lengthen"*).
⚠ Skip *Aquarium* — his own page warns of third-party Content-ID claims on it.

**2. "The President's Own" U.S. Marine Band, via Wikimedia Commons — PD on both
layers.** Real orchestra, and it delivers two of the owner's asks at once:
Debussy's *Danses sacrée et profane* with a live **harp soloist**, and Respighi's
*Ancient Airs and Dances* — orchestral settings of **16th-century lute music**.
Commons tags both layers explicitly (`;Composition{{PD-old-auto-expired}}` +
`;Performance and Recording{{PD-USGov-Military-Marines}}`), resting on 17 U.S.C.
§105.
⚠⚠ **§105 removes US copyright only — the worldwide position is UNRESOLVED**,
and the Marine Band's own copyright page could not be read (403, no Wayback
snapshot). The archived rights letter that does exist covers their SHEET MUSIC,
not recordings. ▶ **Email Marine Band Public Affairs before shipping any of it**
(same shape as the eBible/TITUS asks). Until then: CLEARED-in-US, OPEN-worldwide.

**3. Scott Buckley — CC BY 4.0** — for the "sounds composed, like KJV Dramatized"
register. **261 tracks, every one machine-checked** as CC BY 4.0, and app use is
explicitly ticked in his own licence matrix. Credit form:
`'Title' by Scott Buckley - released under CC-BY 4.0. www.scottbuckley.com.au`.
⚠ Two carve-outs: the licence says "unless stated otherwise" (check each page),
and **his orchestral REMIXES are excluded from the CC library** — they contain
copyrighted thematic material. Never take from that section.

**4. The early-music trio** — small catalogues, but the only genuine
period-instrument performers found with a clean, self-granted licence:
· **Aria Rita** — solo Renaissance lute, **CC0**, performer = recordist. Exactly
  3 tracks (Dalza 1508, Arbeau, anon. 1582/98).
· **Christoph Dalitz** — **CC BY-SA 4.0** — *Lute Ricercars over Genevan Psalm
  Tunes*, composed AND performed AND uploaded by him. A lute setting of Psalm 143
  under a reading of Psalm 143 is the most on-mission music in the report.
· **Phillip W. Serna** — **CC BY-SA 4.0**, **99 files** of viol consort and solo
  viol (Dowland *Lachrimae*, Ortiz, Gibbons, Marais, Manchester Gamba Book),
  self-recorded and self-licensed: the cleanest chain of title found anywhere.
  ⚠ Consort fantasias run 1-4 min — check durations per file.

### Also cleared, lower priority
Walter Börner's Bach chorale preludes (CC BY-SA 4.0 **with a Commons VRT
permission ticket**; BWV 662 7:05 · 663 5:54 · 664 4:44 — slow and quiet, right
register) · Commons user Metzner, Bach/Vivaldi BWV 596 *Largo spiccato*, organ,
CC BY 3.0, 2:37 · the **Musopen Kickstarter recordings via the Commons mirror**
(144 files — the Commons copy records both layers and needs no account; prefer
it to musopen.org) · Audionautix, ~250 CC BY 4.0 tracks, generic but clean.

### BLOCKED — including several that look fine
· **Pixabay** — CC0 applies ONLY to content published before 9 Jan 2019;
  everything since is a Pixabay-granted licence, not passable downstream, and
  they disclaim third-party rights back onto us.
· **IMSLP · archive.org · Musopen · FMA · Jamendo as BULK sources** — all
  user-upload platforms whose licence fields are uploader assertions. Item-by-item
  only. (`licenseurl:*publicdomain*` on archive.org returns 421,532 audio items,
  including many no uploader could possibly PD-mark.)
· **Musopen "European Archive" and historic-performer rows** — transfers of
  commercial LPs; a PD Mark applied by a digitiser clears nothing.
· **Musopen's Albinoni *Adagio*** — blocked at LAYER 1: it is Giazotto's 1958
  composition, not Albinoni's (Giazotto d. 1998).
· **Commons "PDP-CH" set** — `{{Pdproject}}` is a provenance credit, NOT a
  licence, and the recording layer carries no tag at all.
· **Commons CC-BY-1.0 Silbermann-organ set** — a 1971 East German commercial LP
  relabelled by an uploader who is not the rights holder.
· **Nakarada/creatorchords** (no CC licence any more; "free with attribution"
  enforced by a label's Content-ID claims) · **filmmusic.io/ENDE.APP** (one
  artist who states he "partly use[s] AI as a tool" — unsettled rights) ·
  **FreePD.com** (offline permanently) · **CPDL** (scores, not recordings).
· **Magdalena Tomsińska's solo lute** — the best-matching lute material found
  anywhere, blocked purely because the evidence trail is empty. Unverifiable is
  not verified.

### Attribution
Home: the existing **"Text sources"** dialog — worth retitling *"Sources &
credits"* now that it covers audio. One line per track, in the wording each
licence prescribes, with the correct deed URL per version (BY 3.0, BY 3.0 US,
BY 4.0 and BY-SA 4.0 coexist fine — just cite the right one). Required for
MacLeod, Buckley, Dalitz, Serna, Börner, Metzner, Mitchell.
★ For CC-BY-SA tracks the screen must state that **those specific tracks** are
distributed under CC BY-SA 4.0 — the obligation attaches to our re-encoded file,
never to the app.
▶ **Policy call for the owner:** `sources_text` is REQUIRED + PROMISED credits
only, and PD courtesy credits were deliberately stripped once already. On that
rule the Marine Band and Musopen lines are courtesy and should be OMITTED, or
compressed to one line. The CC-BY / CC-BY-SA ones are mandatory.

### ⚠ Standing operational rules
· **Attribution URLs rot.** `serpentsoundstudios.com`, the credit domain for a
  widely-used CC-BY composer, is now a squatted SEO blog. **Re-check every credit
  URL at each release**, alongside the pre-Play-upload grep checklist.
· **Keep a provenance record per shipped track**: title, artist, source URL,
  licence + deed URL, date fetched, and the **SHA-256 of the original download** —
  same discipline as the scripture-integrity baseline. If a site goes the way of
  FreePD, that record is the only surviving evidence of the grant.
· **Do not hot-link** — FMA's ToU §6.d forbids deep links outright. Download
  once, re-encode, bundle or host on our own archive.org item.
· **Never submit any of it to Content-ID / fingerprinting** — a licence condition
  for Buckley, flagged by MacLeod and FMA.
· **Audition before shipping**: several MacLeod tracks list "Choir"/"Voice" —
  wordless pads, not lyrics, but check them under narration.

### ⛔ TOMSIŃSKA / COLLEGIUM VOCALE BYDGOSZCZ — **BLOCKED. SHIP NOTHING.**

A proceed-while-asking plan was approved on 2026-07-31 and then **REVERSED the
same day** when the research came back. Recorded in full so nobody re-opens it.

**THE DECISIVE FACT: the rights holder's own published licence for these exact
recordings is CC BY-NC-ND 3.0.** The Collegium Vocale Bydgoszcz album they come
from (CVB 005 *Chansons*, 2010) has a licence page whose sole link is
`creativecommons.org/licenses/by-nc-nd/3.0/`, and the signed licence PDF still
shipping with their free albums reads *"NONCOMMERCIAL … NO DERIVATIVES — You may
not alter, transform, or build upon this work."*
▶ **ND alone ends it**: preparing a track as a background bed (re-encode, trim,
loop, volume curve) is squarely "build upon". Same NC+ND reasoning that blocked
Zhuromsky.

This is NOT a risk-acceptance case, and must not be filed beside Van Dyck or
Luther 1545. Those were *unverified* layers. This is **verified as NOT
PERMITTED** — an affirmative contrary grant from the licensor. The distinction
is the whole point: you may knowingly tolerate an unresolved question; you may
not tolerate a resolved "no".

Supporting findings, any one of which would give pause on its own:
· The competing CC-BY tag on Commons is an **uploader assertion**, unreviewed on
  all five files. They sit in `Category:License review needed (audio)` — the
  queue that has already produced **12 deletions** from this same collection,
  9 of them since Oct 2025. Precedent from a closed deletion request: *"Youtube
  reports that the source video is 'not available' and it's also not archived,
  so the CC-BY license can't be verified" → Deleted, per COM:PCP.*
· The uploader is a **collector, not the ensemble**; `|permission=` is empty on
  all 60 audio files.
· The recordings are **sold commercially** (digital re-release 2023-24;
  Tomsińska's own lute album is DUX 1150, sold new).
· She was a **guest** lutenist — her performer's rights in the solo lute tracks
  are not obviously the ensemble's to license anyway.

★ WORTH KEEPING — the YouTube hypothesis was half right, and the method is
reusable. `video2commons` only emits `{{YouTube CC-BY}}` when yt-dlp actually
read the flag, otherwise it emits a no-licence deletion tag; and four
independent Commons reviewers passed sibling files from this channel while the
videos were live, bracketing these imports. One description was even proven an
unedited live scrape (an embedded YouTube `redir_token` decodes to a timestamp
2 min 11 s before the upload completed). **But the defeater:** a 2020 file from
the same uploader carries a hand-added `{{YouTube CC-BY}}` next to a
`{{No license since}}` tag, proving the field is hand-editable and that he edits
it. So the machine-witness is strong but not airtight — and in any case a CC-BY
flag would merely *conflict* with the licensor's contemporaneous NC-ND. Relying
on the more permissive of two conflicting grants, against evident intent, on
files nobody can verify, is not "legally clean".

▶ **The only route to this music is a fresh permission from Tomsińska herself**,
who is alive, teaches at Wilfrid Laurier University, and plausibly holds her own
performer's rights. Draft: `store-assets/tomsinska_music_email_draft.txt`
(gitignored) — **English**, framed as a fresh ask that explicitly does not claim
any existing CC licence covers this, and asking the provenance question too
(the ensemble dissolved in 2017; director Michał Zieliński died Feb 2024, so who
holds the phonogram rights is genuinely unclear).
⚠ If she declines, that is the end of it — do not approach the ensemble's estate
as a way around a no.

### ★★ THE ONE RULE TO CARRY FORWARD
**On any user-upload platform, trust the licence tag only where the UPLOADER IS
THE PERFORMER.** That single discriminator correctly clears Metzner, Serna,
Dalitz, Aria Rita and Börner — and correctly rejects the 1961 Deutsche Grammophon
cello suite on IMSLP, the 1971 Eterna organ LP on Commons, the "European Archive"
LP transfers on Musopen, and a MIDI-plus-soundfont Goldberg set that two separate
catalogues describe as a performance.
★ The gate that matters: **a recording is at least two rights layers** — the
composition and the performance/recording. "Bach is public domain" clears only
the composition; a modern orchestra's recording of it is fully copyrighted.
Same layer trap as the Van Dyck tashkeel. CC-BY and CC0 are acceptable; **NC
and ND are not** (ND additionally forbids the re-encoding above).
Attribution obligations join `sources_text`, which is REQUIRED-and-PROMISED
credits only — MacLeod is already there.
