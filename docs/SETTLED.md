# SETTLED — questions that are CLOSED, and where the evidence lives

▶ **This file exists so the handoff can stop carrying them.** A settled fact on
a handoff rides forever: it is re-read by every session, it crowds out the work
that is actually forward, and it is never true that a reader NEEDS it — they
need to not re-open the question. That is what this file is for.

## How an item gets here

When a question is answered for good, the answering session writes the
**evidence** into the matching topic doc (or leaves it in the code that
enforces it), then adds ONE line here, dated, pointing at that evidence. The
handoff then carries at most a pointer to this file — never the list.

## How an item leaves

It does not. If a settled item turns out to be WRONG, the line stays and gains
a `⚠ REOPENED <date>` note with what changed. A silently deleted line reads as
«never decided» to the next session, which is how a closed question gets
re-litigated.

⛔ **A line here is not a licence to skip a derivation.** These are decisions
and print facts, not live counts. Anything countable is still derived from its
audit script, every time.

---

## Narration — pronunciation and render defects

- **ylt Genesis 13:14 says «eastward»** — ear-confirmed on the SHIPPED audio,
  not on a test render. 2026-09-07. ▶ `docs/NARRATION.md`, the substitution
  class; `research/_evidence/gen13_14_substitution_reproduced_2026-09-07.md`.
- **`Naymen` is the chosen respelling for Naaman** — owner's ear picked take 3
  of three candidates, 2026-09-07. The rejected spellings are kept in the code
  so they are not re-proposed. ▶ `tools/pronounce_lexicon.py`.
- **`Naamite` (Numbers 26:40) is CORRECT AS PRINTED** and must never enter the
  lexicon — owner, 2026-09-07, heard beside the respelled `Naymen`.
  ▶ `tools/pronounce_lexicon.py`.
- **`Elijah` is pronounced CORRECTLY** and must never enter the lexicon.
  ▶ `CLAUDE.md`, narration index.
- **`Eelighsha` was wired in over a stated objection**, 2026-09-07 — the
  owner's call. ⛔ Do not re-litigate it and do not guess a further spelling.
  ▶ `docs/NARRATION.md`, «`Elisha` — `Eelighsha` WIRED IN».

- **ylt's EAR REVIEW IS COMPLETE and the set is cleared to ship.** 2026-09-07:
  18 flagged verses heard on the LIVE tree, 17 good; the one real defect
  (`seeth`, II Chronicles 23:13) was fixed as `seeith`, rendered across 144
  chapters and gated. `ylt_ship_chain.py` reports `append-class: 5 already
  ruled on, 0 UNRULED` with every quality gate PASS.
  ⛔ **`still failing after 3 draws` in a render log is NOT an ear queue** — it
  is a per-draw note that reappears on every render and knows nothing about
  what an ear later ruled. Read the newest chain report, never a render log.
  ⛔ Re-rendering a ruled verse can ship a WORSE take (gate ties fall back to
  attempt 1 — Genesis 13:14 lost a correct draw twice that way).
  ⚠ STILL OPEN, and NOT cleared by that review: the `naaman` / `Naymen`
  spot-check — II Kings 5:25 contains *Elisha* but not *Naaman*.
  ▶ `research/_evidence/ylt_ear_review_2026-09-07.md`.

- **tyn's double-e is cleared: `seeth` -> `seeith`, `fleeth` -> `fleeyeth`**
  (owner ear, 2026-09-08, on three draws each of Genesis 44:31 and
  Deuteronomy 19:11). ⚠ tyn is chatterbox and fed TEXT, so wbt's kokoro G2P
  evidence never applied to it.
  ⛔ **`siyeth` is NOT to be revived**: the owner's ear passed it, but it failed
  the ASR word-presence check 0/3 where `seeith` and `seeyeth` passed 3/3 —
  the `fliyeth` signature. Ear-passed is not word-safe.
  ⛔ **Punctuation is REFUTED as a lever for this defect** — plain 0/4 and
  trailing-stop 0/4. Do not re-propose a trailing stop.
  ▶ `research/_evidence/tyn_seeth_punctuation_refuted_2026-09-08.md`.

## archive.org uploads

- **The sv (kxii) apocrypha is SHIPPED AND INDEXED.** 2026-09-10. All 147
  deuterocanon chapters are live on `hexapla-audio-karlxii-1703`, the item's
  public title no longer reads «(pågår / in progress)», and the kxii entry in
  `build_audio_index_gen.py` carries `"apocrypha": True` — kxii builds
  1336/1336 across 78/83 books. ⛔ Do not re-run the QA and do not re-render.
  ▶ still true? `python tools/sv_apoc_status.py` — its last block must read
  `78 book(s), 12 apocrypha book(s) indexed`.
- **A 404 on `78/5.ogg` is CORRECT, not a hole.** Additions to Esther's LIVE
  chapters are slots 9,10,12,13,14,15; index 5 is one of the verse-less
  placeholder slots `bible_live_chapters()` exists to skip. ⚠ A probe list
  built by counting `0..n-1` invents a phantom gap here. 2026-09-10.
- **A non-zero MISSING right after an uploader exits is DERIVE-LAG, not loss.**
  ⛔ RE-READ the item; do NOT re-send. Measured twice on 2026-09-10: 10 → 0,
  then 15 → 0, both with nothing sent in between. The item's task queue has to
  drain before its files.xml MD5s settle.
- **A long-running derive on an item does NOT block uploads to it** — the
  blocker is the ACCOUNT-WIDE task ration. Proved by probe 2026-09-07 against
  the 116-hour `derive.php` (task 5601127710, `wait_admin=1`). ⛔ Do not mail
  archive.org about it and do not re-probe.
  ▶ `docs/NARRATION.md`, the archive.org upload section.

## Transcription — completeness and print facts

- **Luke idx 57 and 58 are MERGED; Luke 6 is COMPLETE 49/49.** 2026-09-10. The
  «ei helldur» page-foot was adjudicated a CATCHWORD — idx 58 opens by
  repeating it verbatim — so merged 6:44 carries `ei helldr` ONCE. ⛔ Do not
  re-read or re-merge either page. ▶ still true?
  `python tools/thorlaks_part_check.py --file research/_parts/luke_p50-58.md`
- **Luke idx 59 is NOT truncated — its SUSPECT right edge is a STAIN.**
  2026-09-10. `thorlaks_crop_widths.py` measures DARK PIXELS and cannot tell
  foxing from ink, so a stained leaf edge flags a perfectly intact page. The
  proof is that the identical streak sits on `line49`, which has NO TEXT AT
  ALL — that one observation rules out truncation AND apparatus at once.
  ⛔ Do not re-prep p59 and do not discard judgements made on it.
  ▶ `research/_evidence/luke_p59_edge_adjudication_2026-09-10.md`.
- **`thorlaks_crop_widths.py` takes BARE POSITIONAL kit names** (`kits =
  sys.argv[1:]`); there is **no `--kit` flag**. `--kit luke_kit` makes it treat
  `--kit` as a kit name, print `⛔ no kit at …\_prep\--kit`, and measure the
  real kit anyway — a correct result behind a line that looks like a failure.
  ▶ RIGHT: `python tools/thorlaks_crop_widths.py luke_kit luke_kit2`

- **Matthew (Þorláksbiblía) is merged and complete, 1071/1071.** 2026-09-07.
  ▶ `docs/TRANSCRIPTION.md`.
- **Additions to Esther (Karl XII apocrypha) is COMPLETE.** 2026-09-07.
  ⚠ Derive the current corpus figure from `karlxii_apoc_corpus_audit.py` — this
  line closes the QUESTION, it is not a count to quote.
- **Mark 3 (36 verses), Mark 5 (42) and Mark 8 (39) are PRINT FACTS**, not
  transcription errors — the print diverges from the KJV and is recorded with
  page evidence. ⛔ Never supply the missing verses from a parallel.
  ▶ `research/_evidence/mark_verse_count_divergences_2026-09-07.md`.
- **The Turkish edition to ship FIRST is the 1827 Kieffer OT+NT**, not the
  1665 Ali Bey manuscript. Owner + Osmanlıca Kelâm (Bruce) both agreed,
  2026-09-09/10. 1827 scores 7/7 on the deity litmus and 19/19 on the extended
  TR-presence screen; 1665 scores 6/7 — **John 3:13 omits «ki gökdedir»**, its
  only divergence across 26 screened points. 1665 remains wanted SECOND.
  ⚠ Neither is licensed yet; the transcription licence is still the gate.
  ▶ `research/_evidence/turkish_1665_litmus_2026-09-09.md`.
- **Ali Bey's Apocrypha is LOCATED and BLOCKED.** 2026-09-09. Kadir Akın's
  transliteration is at `https://www.hakikat.net/indir/apokrafi.pdf` (the link
  Osmanlıca Kelâm publishes is dead). Page 2 reserves all rights to Akın by
  name, requires written permission, and caps quotation at 100 sentences.
  ⛔ Do not ship it without his written yes; it is HIS decision, not Bruce's.
  ▶ `research/_evidence/turkish_alibey_apocrypha_2026-09-09.md`.
- **Editions' orthographic legibility does NOT separate 1665 from 1827** —
  measured, not assumed: 101.2 vs 100.3 non-modern-Turkish characters per 1,000
  letters over the same 2,564 verses. The transliteration scheme is the
  TRANSCRIBER's, so it is identical across their editions. ⛔ Do not re-open
  "which is easier to read" on orthography; the real difference is VOCABULARY
  (1665 uses «Bârî/Hakk Teʿâlâ» where 1827 uses «Allah»/«Rab»).
  ⚠ Corollary: the diacritic/font check against the app's fonts is ONE check
  covering both editions, not two. ▶ same evidence file.
- **Mark and Luke are in the corpus audit.** 2026-09-09. They were invisible
  because no `research/thorlaks_<book>.md` existed — the audit globs that path
  and both books lived only under `_parts/`. Merged with
  `thorlaks_merge_parts.py`. ⚠ Any future book is invisible the same way until
  it is merged; the merge is not optional bookkeeping.
- **Mark 9 (49 verses) joins Mark 3/5/8 as a PRINT FACT** — printed chapter IX
  opens at KJV 9:2, so it runs 1-49. All four are now registered in
  `thorlaks_corpus_audit.py`'s `KNOWN_DIVERGENCE`, and the audit prints a
  `RECORDED EDITION DIFFERENCES` block naming every row that fired, so a
  registered chapter can never go silently quiet.
  ⛔ Never add a row to that table without page evidence, or to make a count
  line up. ▶ `research/_evidence/mark_verse_count_divergences_2026-09-07.md`.
- **Volunteer overlap on Icelandic Bibles is intended** — owner, 2026-08-10:
  two Icelandic Bibles is the wanted outcome. ▶ `CLAUDE.md`.
- **The Þorláksbiblía apocrypha IS in scope** — owner, 2026-09-08. Sirach and
  1-2 Maccabees, ~114 pages of v2. ⚠ The audit's denominator is still the
  31,102-verse protestant canon and does NOT enumerate them, so ENUMERATING
  those books remains OPEN work — the scope question is what is closed here.
  ▶ `research/_evidence/thorlaks_ot_apocrypha_scope_2026-09-07.md`.
- **The v2 apocrypha's LAST open book boundary is closed: 2 Maccabees begins on
  idx 359** — 2026-09-12, by a BODY read after a verso-head sweep had narrowed
  35 pages to 2 and could go no further (idx 358 is a recto, and every recto in
  that span prints only «Maccabeorum»). idx 358 carries no book rubric, only the
  chapter numeral «XVI»; idx 359 carries 1 Macc 16:21-24, the colophon «Endiŋ
  þeirrar Fyrstu Bookar Maccabeorum», Luther's formále, and chapter I. Both
  controls fired, and idx 360/361/362 run 2 Macc 1→2→3 monotonically.
  ⛔ Do not re-sweep the heads. ⚠ This closes BOUNDARIES only — every apocrypha
  chapter COUNT is still tradition-derived, not read off this print.
  ▶ `research/_evidence/thorlaks_v2_maccabees_boundary_CLOSED_2026-09-12.md`.

- **Luke gets NO `ø` rate — option B, the owner, 2026-09-15.** The 2026-09-12
  method finding left three options open (A main session one page at a time,
  B no rate, C a non-vision instrument) and the owner has now taken **B**.
  ⛔⛔ **THIS IS NOT A 0 % RATE.** The text needs no repair: every `o` already
  stands plain by the documented default, and a page with no crop data has no
  rate — that is the correct outcome, not a gap to be filled later. ⛔ Do not
  commission a subagent `ø` read for Luke, do not "top up" a page from its
  candidates, and do not report Luke under the 19-31 % band — the band is per
  BOOK and Luke is not in it. ▶ `research/_evidence/thorlaks_o_pass_method_2026-09-12.md`.

- **Luke p66's verse numerals are PRINTED, and 13:3/13:4 is settled against the
  print** — 2026-09-15. 13:3 ends at `aller eins`; the Siloam tower clause and
  `er byggia til Jerufalem?` are both inside 13:4. ⛔ Do not re-adjudicate it
  from sense. ★ The 2026-09-14 sheets-only read also **dropped a whole clause**
  — a contiguous, plausible verse range can be missing content in the middle,
  and the corpus audit cannot see that.
  ⚠ p66 is still NOT mergeable: `line43` is 3.80x the median height and holds
  four scripture rows, so its line addresses are void.
  ▶ `research/_evidence/thorlaks_luke_p66_secondpass_2026-09-15.md`.

- ★★ **THE PAGE METHOD IS RULED — owner, 2026-09-17 16:40, «Yes to both».**
  ⛔ Do not re-propose hand-orchestration and do not re-ask for this. Measured
  that day: ONE Luke page cost ~10 Sonnet agents (~0.7M tokens) **plus ~25
  main-session turns at 150-200k of re-billed context (~4M)** — the main
  session was 85 % of the bill and 100 % of the wall-clock, and Luke alone had
  ~45 pages left. The method from now on:
  1. **One `Workflow` per page batch**, never a hand-run pipeline: the main
     session launches one workflow and reads one result. Every agent is a fresh
     context, so the 25-image guard and the 220k stop stop binding.
     ▶ `.claude/workflows/thorlaks_page.js` in the repo.
  2. **Two CROP reads (A and B), no sheets read** — the sheets read is the
     weaker instrument (6.3x vs 8.3x) and needs a hand-built kit. The two reads
     take **different chunk boundaries** (offset ~7 crops) so a chunk-edge error
     cannot land on the same site twice.
  3. **Majority vote BEFORE adjudication**: a third blind crop read resolves
     every 2-of-3 site in plain code; only three-way splits and empty sides go
     to a forced-choice adjudicator.
  4. **Scripts run in `effort:'low'` agents, never in the main session.** The
     main session never `cat`s a read.
  5. Kept from the old method: brief files as the cached prompt prefix;
     `(nothing)` for an empty side; the merge tool's `[X] N site(s) with NO
     verdict` line as the ONLY coverage authority; a control that must fire.
  ⚠ The lever is never «more agents» — it is moving checks into scripts,
  batching images, and not re-reading what was already read.

- ★★ **THE NEXT CAMPAIGN'S PILOT ITEMS ARE RULED** — same ruling, 2026-09-17
  16:40. These are conditions on starting the print AFTER Þorláksbiblía, not
  suggestions:
  (a) choose the next print **partly on whether a digital WITNESS text exists**;
  (b) one session tests a public **blackletter OCR model** (Kraken /
      Transkribus family) on three ALREADY-MERGED Luke pages, diffed against
      the merged text, 0 vision tokens — if it reads acceptably it replaces one
      of the two reads as a witness; ⛔ not assumed to work until that diff
      exists;
  (c) **freeze the sort conventions on a three-page pilot with him BEFORE any
      reading starts** — no mid-campaign convention change;
  (d) **validate prep on the whole kit before the first read** — crop widths
      AND heights with their controls, plus the line-cliff test;
  (e) **log tokens per page per stage from day one.**
  ⚠ A witness text is a WITNESS, never a source: the `kxii_diff.py` rule holds
  — transcribe first, diff after, and readers never see the witness. Its licence
  is gated by `docs/TRANSLATIONS.md` like any other text.

## Product

- **Voice cloning of real people and game characters is refused** (Joshua
  Graham, and any successor request). Owner accepted the reasoning.
  ▶ `CLAUDE.md`, owner preferences.
- **The 29 books without cover art are done being hunted** — the gap is
  structural, not a search failure. 2026-08-10.
  ▶ `research/bookart_gap_sources_2026-08-10.md`.
- **Playback does not follow a page turn, and that is INTENDED** — owner,
  2026-09-16. `navigateChapter` never touches `Playback`, so turning the page
  while audio plays leaves the audio where it was. ⛔ Do not "fix" it, and ⛔ do
  not add a UI cue for it — he was offered that option and took plain
  «intended». Reading ahead of the narration is a use, not a bug.
  ▶ mechanism in `docs/ARCHITECTURE.md`.

## Narration

- **`Aebraham` is FIXED and the fix reached the RUNNING render** — owner's ear,
  2026-09-13, on a two-way control: Genesis 17:5 (rendered before the lexicon
  recycle) wrong, 1 Chronicles 29:18 (rendered after) correct. ⛔ Do not re-ask
  whether the lexicon is live. ⚠ Chapters rendered BEFORE the recycle still
  carry it and the affected count was never derived — that part is OPEN.
  ▶ `research/_evidence/en_lexicon_abraham_confirmed_2026-09-13.md`.
- **The gate-append side of books 8, 9 and 10 is CLOSED with ZERO real
  appends** — 2026-09-13. 16 distinct flags: 4 cleared mechanically by the
  printed-word route, 9 by the owner's ear over kits 13c/13d/13e, 3 earlier.
  ⛔ Do not rebuild an ear kit for books 8-10 appends.
  ★ And the gate has a known FALSE NEGATIVE: Leviticus 22:17's ear-confirmed
  doubling is NOT among book 2's flags. The gate and the ASR sweep are disjoint
  in BOTH directions — a book screened by one is not screened.
  ▶ `research/_evidence/en_gate_append_coverage_2026-09-13.md`.

## Translations

- **Every question put to the AMB translator is ANSWERED** — Bro. Edmund,
  2026-09-13. Final text + release tag `2026`; litmus **7/7 re-run on the final
  text** with the exact KJV NT grid (7,957 verses) verified; attribution wording
  given ("my AMB Github website", REQUIRED under CC BY-SA so it goes in
  `sources_text`); Luke 19:13 DECLINED with reasons. ⛔ Nothing is pending from
  him and the "wait for a traditional edition" branch stays closed.
  ⚠ Only the owner's ship / don't-ship call remains, and it is about a
  **29-verse** peso policy, not one verse.
  ▶ `research/_evidence/amb_final_litmus_2026-09-13.md`.
