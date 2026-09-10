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

- **A long-running derive on an item does NOT block uploads to it** — the
  blocker is the ACCOUNT-WIDE task ration. Proved by probe 2026-09-07 against
  the 116-hour `derive.php` (task 5601127710, `wait_admin=1`). ⛔ Do not mail
  archive.org about it and do not re-probe.
  ▶ `docs/NARRATION.md`, the archive.org upload section.

## Transcription — completeness and print facts

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

## Product

- **Voice cloning of real people and game characters is refused** (Joshua
  Graham, and any successor request). Owner accepted the reasoning.
  ▶ `CLAUDE.md`, owner preferences.
- **The 29 books without cover art are done being hunted** — the gap is
  structural, not a search failure. 2026-08-10.
  ▶ `research/bookart_gap_sources_2026-08-10.md`.
