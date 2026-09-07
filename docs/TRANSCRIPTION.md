# Transcription — Hexapla

# ── MOVED OUT OF CLAUDE.md, 2026-09-07 (context budget) ──

Þorláksbiblía / Karl XII transcription: settled records and the method
findings behind them. CLAUDE.md keeps a short index pointing here.

## ⛔ DO NOT USE HAIKU FOR THE Þorláksbiblía TRANSCRIPTION — measured 2026-09-04

Controlled test at the owner's request: Haiku and Sonnet read the SAME two
sheets (`2timothy_v3` p199 sheets 1-2, 2 Tim 4:7-22) under the same brief.
Sonnet's output is the one the corpus already accepted (2 Timothy audits 83/83).

| | Sonnet | Haiku |
|---|---|---|
| character similarity to Sonnet | — | **70.9 % mean, 55 % worst** |
| verses identical | — | **0 of 16** |
| proper nouns of 2 Tim 4 recovered | **17/17** | **10/17** |

Haiku lost Crescens, Erastus, Linus, Marcum, Pudens, Titus and Tychicum;
invented an abbreviation «DXDSSE» for DROTTIN and then REPORTED it as faithfully
kept-as-printed; and **shifted verse boundaries** — its v14 opens with the tail
of v13, so text is filed under the wrong verse numbers. It also self-certified
(«current reading stable at native magnification», «no inferences from modern
text»), none of which held. ▶ Confident, wrong, and unverifiable without a
reference — the exact failure the kit manifest warns about: *the failure this
guards against is not misreading, it is supplying the letter the WORD wants.*
Evidence kept at `research/_haiku_test/`.

## ✅ THE ø RE-ADJUDICATION IS VINDICATED — the packed-sheet negatives WERE wrong

Measured 2026-09-06, after the packed-sheet method was disproved:
- **p13: 0 confirmed ø under the old method -> 6 under the crop method.**
- **p16/p17: the calibration fired** — `p16 line49 R` and `p16 line52 L`
  («ſøgdu»), the two known false negatives, **both show the stroke**.
▶ So «no ø on this page» from ANY pre-2026-09-06 run is worthless. The owed list
is **p12** (its transcription agent also read ø at sheet scale — its transcription
is sound, its ø negatives are not), p13 (done), p16-18 (in progress).
⚠ **A re-read is not automatically a clean bill:** p13 came back at 6/82 = 7.3 %,
still under the convention's 19-31 % (settled from the Philippians retrofit, 74
sites, stated **per BOOK not per page**; «under 10 % is a defect, not a dialect»).
Spot-checks confirmed both a positive and a negative on the same line, so whether
p13 is a genuinely low page or still under-read is **OPEN**.
⚠ Every Matthew part file still reports 0.1-1.8 % via `thorlaks_part_check.py`
because the retrofit sites have **not been patched into the part files yet**.

## ⛔⛔ AND THE RETROFIT'S RECORDS CANNOT BE APPLIED TO THE CORPUS — 2026-09-07

`tools/thorlaks_o_patch.py` was built to patch confirmed ø sites into the part
files. Report mode over Matthew's **34** crop-method sites:
**UNIQUE 7 · AMBIGUOUS 9 · MISSING 15 · unparseable 3.** ⛔ **Nothing was
written.** That is why the «not patched in yet» note kept surviving: there was no
tool, and the tool now says the job cannot be done this way.

**It is structural.** A record is addressed `p<page> line<NN> <L|R>`; the part
files are indexed by VERSE and hold no line numbers, so the only handle is the
word. `sogdu` occurs **32×** in one part file and two records point at it.
MISSING means the adjudicator's spelling and the transcriber's disagree
(`Kicrollð`, `thorj`, `Spamañoñu`) — a finding about one of the two readings,
never a patch to force.

- ⚠⚠ **TWO BUGS IN THE NEW TOOL, BOTH UNDER-REPORTING** — the sixth and seventh
  such in this family. (1) It demanded a ø/ö in the record, but adjudicators
  inconsistently write the PRINTED form (`Fodur`); a word with exactly one `o`
  is unambiguous. Cost: 22 of 34. (2) It discarded the adjudicator's own
  bracketed correction (`fogdu (sogdu)` — long-s read as `f`), blaming the
  transcription for a noted slip. UNIQUE went 2 → 5 → 7.
  ▶ **Assume a new screen is broken until a control fires** — again.
- ⛔ **A PARTIAL PATCH IS WORSE THAN NONE.** It raises the per-file ø rate that
  `thorlaks_part_check.py` prints, and that rate is the campaign's only signal
  that a page was read at the wrong resolution. `--apply` therefore also demands
  `--i-know-the-retrofit-is-partial`.
- ▶ **THE REAL FIX IS AT SOURCE: make the adjudicator record the VERSE.** It has
  the line image in front of it and the part files are verse-indexed, so this
  costs nothing per site. Put it in the brief BEFORE the next page is read, or
  every future retrofit produces the same unusable records.
- ✅ `tools/thorlaks_o_merge.py` merges the adjudication files and **labels each
  by METHOD**, because they are not interchangeable: CROP (validated) vs SHEET
  (disproved). It prints which pages have crop data at all.
  ⚠⚠ **THE SHEET METHOD ERRED IN BOTH DIRECTIONS.** Measured 2026-09-07:
  `p17 line02 høpdu` was a sheet-method POSITIVE and the crop read shows a clean
  open bowl — a FALSE POSITIVE. **So its positives are no more usable than its
  negatives**, and its 47 Matthew claims are claims, not findings.
  ⚠ Crop-method coverage as of 2026-09-07 is **p12, p13, p16, p17, p18 only**.
  Every other Matthew page has NO trustworthy ø measurement in either direction —
  not a low rate, no measurement.
- ⚠ The 2026-09-06 p16/p17 pass was **sound but not exhaustive**: its verdicts
  held 3 of 4 on re-audit, but `p16 line19 L «Kicrøllð»` was never listed as a
  candidate at all and IS ø.

## ✅ MATTHEW IS MERGED AND COMPLETE — 1071/1071, 2026-09-07

`thorlaks_corpus_audit.py` reports **Matthew 28/28 chapters, 1071/1071 verses,
OK**; `thorlaks_part_check.py --book Matthew` reports **0 problems**. Corpus
total went 2756 -> 3827 of 31,102. ⚠ Derive both; never quote these here.

Getting there took two SILENT verse-losing bugs, both found only because the
merge grid and the per-file check disagreed:

- ⛔⛔ **`thorlaks_merge_parts.py` RESET THE CHAPTER ON ANY `#` LINE**, so a
  `### idx 14 (…)` page marker *inside* a chapter ended it. **122 of Matthew's
  1071 verses went into the appendix.** ⚠⚠ **AND THE GRID LOOKED FINE:** it
  printed «ch 12: 4 verses, 1-4», which reads as a legitimately short chunk
  because the range is CONTIGUOUS — the ⚠ MISSING marker only fires on a HOLE.
  ▶ Fixed: only a `##`-level heading ends a chapter; `###` does not.
  ▶ **A contiguous range is not evidence of completeness.** Compare against the
  expected verse count, which is what the corpus audit (not the merge) does.
- ⛔ **MATTHEW 10:41-42 WERE TRANSCRIBED BUT UNREACHABLE.** They open
  `matthew_p13-21.md`, whose first chapter heading is `## Matthew 11` — so they
  sat under no chapter and every tool dropped them. ▶ Fixed by adding a
  `## Matthew 10` heading there; the merge joins by (chapter, verse), so a
  chapter living in two part files is normal.
  ⚠ **«Transcribed in full» is not the same as «reachable».** The 2026-09-06 note
  saying these two verses were safe in p13-21 was TRUE and they were still lost.
- ⚠ Matthew 10:3-4 were printed INLINE inside v2's paragraph. The audit reads
  only the FIRST numeral on a line, so it reported them missing while both sat in
  plain sight. Split onto their own lines — a formatting fix, nothing recovered.

▶ Also fixed this session, all image-verified: **Mt 1:25 and Mt 9:38** were
merged into the preceding verse and are UNNUMBERED in the print (pinned by
position per convention, not supplied from the KJV); **Mt 8:32 is printed
TWICE** — a printer's error, so it is RECORDED, not corrected, and
`_work/MATTHEW_REPAIR_LIST.md`'s instruction to drop the second numeral was
WRONG; **Mt 4:19's «Fiskemeñ»** was a page-top tail the transcriber numbered
(the print has no numeral there) and now ends v18. ⚠ The checker could not see
that last one — it reads the first numeral per line, so Matthew 4 said 25/25 ok
while scripture sat under the wrong number.

## ⛔ MATTHEW idx 12 ENDS AT 10:40 — the «prep defect» is WITHDRAWN, do not re-open

A transcription agent reported sheets o13/o14 blank and Matthew **10:41-42
missing**, and recommended a re-prep. All of that is wrong, verified at native
resolution 2026-09-06:
- `line56` carries v40 at **21.6 % ink** — a full line.
- `line57` holds exactly ONE word, «ſende» (v40's last word), in its first 68
  rows, then a **424 px bottom margin merged into the crop**. That is why the
  sheet averaged 0.83 % ink and read as blank.
- **10:41-42 are on idx 13** and are transcribed in full in `matthew_p13-21.md`.
▶ The false `41 [... NOT RECOVERED]` placeholder is removed. Matthew 10 in
`matthew_p4-12.md` now reads **38/42 range 1-40**, correct for a chunk ending at
v40; its `GAPS [3, 4]` is a **parser artifact** — vv. 3-4 are present as inline
numerals inside v2's paragraph.
⚠ **A tall blank block merged into a line crop makes a full sheet look empty.**
Measure ink PER LINE, not per sheet, before calling a crop defective.
✅ The agent's refusal to fabricate 41-42 from the KJV parallel was RIGHT. Its
reasoning was wrong; its discipline was not — that is the trade this project wants.


