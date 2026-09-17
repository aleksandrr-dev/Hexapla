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



## ★★ A PLATEAU PROVES STABILITY, NEVER CORRECTNESS — 2026-09-15

Three instruments here now let a unit pick its own threshold instead of sharing
a constant: `prep_chunk.choose_frac()` (a page picks its side of the line
cliff), `thorlaks_hn_typematch.stable_glyph_cols()` (a glyph picks its gap), and
`thorlaks_hn_wordseg.choose_threshold()` (a line picks its word-gap band). The
shape is right and it has repaired a real defect at each scale.

⛔ **But flatness is not truth, and the word scale proves it.** Mark p37
`line40` has a genuine two-wide plateau at t=7-8 giving **18** words. Its real
count is **17** — and 17 **never appears in its profile at any threshold**
(18, 18, 16, 15, 14, 12 steps straight over it). The plateau is stable, the
answer is wrong, and every internal sign is healthy.

⇒ ★ **Every plateau-selected quantity needs an EXTERNAL check, or it is a
confident guess.** For word segmentation that check is the transcribed word
count, and ⛔ **a line whose segmented count disagrees is SKIPPED, never nudged
to the nearest threshold that would agree.** Tuning the threshold until the
count matches is manufacturing the answer.

⛔ The expected count must not be reachable by the chooser. `choose_threshold`
takes the profile ALONE and `--selftest` asserts the signature stays count-free
— the ordering is the whole guard.

▶ `tools/thorlaks_hn_wordseg.py --selftest` (**0**; `HEXAPLA_NO_WORDPLATEAU=1`
→ **1**). ▶ `research/_evidence/thorlaks_hn_wordseg_perline_2026-09-15.md`

⚠ Ground truth for a segmentation check must be read **blind** — a count the
tool could have influenced is not a control. The p37 counts were read by a
subagent told nothing about any threshold's output, and its **hedges are kept**
(`line25` 16-or-17, `line41` 15-or-16) rather than rounded to single numbers.

⛔ **NOT yet a screen, and NOT shown to beat a global threshold.** A global
t=9 or 10 produces the same outcome line-for-line on this page. The per-line
design rests on the argument and on the letter-scale precedent, not on these
three lines. ⚠ Where a transcribed count may legitimately come from is UNDECIDED
and is the owner's call; the tool reads no corpus file and takes `--expect`.

## ★★ A MEASUREMENT TAKEN BESIDE THE PIPELINE IS NOT A MEASUREMENT OF THE PIPELINE

2026-09-15. A probe that **re-implements** what a function does, instead of
calling it, produces a confident number about nothing.

Luke p66 was carried for two sessions as "56 runs go in, 51 crops come out —
five rows are lost downstream." There is no downstream loss. `line_rects()`
returns exactly `len(_runs(...))` — no filter, no minimum-height test, no rect
merge — and `main()` writes one crop per rect. The arithmetic is
**44 + 7 recovered = 51**, and it balances at every stage.

The "56" came from a probe that sampled the row profile at **zoom 4.0,
`min_len=3`, over the FULL PAGE**. `line_rects()` profiles at `PROFILE_ZOOM`
2.0, `min_len=6`, cropped to the detected text block. The identification is not
a guess: under those probe settings the healthy control page reproduces **all
ten** of the recorded sweep values exactly.

▶ **The rule:** a probe must CALL the function, or copy its body verbatim and
say so in the file. ⛔ Never re-derive "the same" profile with your own
constants — the three candidate causes the wrong number sent two sessions
hunting (a coalescing pass, a rect merge, a `min_len` discard) **do not exist in
the code**.

▶ **The cheap check that would have caught it:** `prep_chunk.py --dry-run`
already prints `would write N line crop(s)` — the pipeline's own number, free.
⛔ Do not build a probe for a quantity the tool already prints.

⚠ p66 remains unreadable and ⛔ must not be re-cut: a re-run reproduces 51
today. Its profile never resolves more than 44 of ~56 lines at ANY threshold
(0.40 is already the best, and `choose_frac` correctly re-chooses it), so the
page is a genuine low-contrast case. The over-wide text block (280.0pt against
239.5–240.0 for its neighbours) was the obvious suspect and is ⛔ **refuted** —
narrowing the band left- and right-anchored at 270/260/250/240/230 and
`--robust-block` all stay CLIFF, while the healthy control stays FLAT under the
identical treatments. ▶ `research/_evidence/thorlaks_luke_p66_no_downstream_loss_2026-09-15b.md`

## ★★ THE MERGED-LINE PAGES ARE SKEWED — measured corpus-wide 2026-09-16

⛔ **The mechanism is NOT horizontal clustering.** That is the right design for
`short_line_rects()`' defect (a one-word line) and is already implemented there.
⛔ Do not spend another session clustering for the merged-line class.

The line pitch is 14 profile rows on every page in the kit, and the merged pages
drift **7–13 rows across the block — half a line or more**. The scan is rotated
about a degree, so a row that is inter-line space at the left of the block is
solid text at the right; `line_rects()` then averages that row to one pixel and
thresholds the mean, by which point gap and text are already mixed. ▶ That is
why the re-threshold, `--robust-block` and the block-narrowing sweep all failed:
**they keep the skew.**

- ▶ The gate is **`median(|step|) >= 1` AND every non-zero step sharing a sign**
  — a rotation is DISTRIBUTED. ⛔ Total drift alone is not it: healthy pages
  carry -4 to -6 of drift entirely in the first strip (a drop cap).
- ▶ The correction is a **SHEAR** (shift column x up by `round(slope*x)`) —
  integer moves, no resampling, no argument about which way a rotation turns.
- ▶ Corpus-wide, 1,248 pages: **148 gated, 0 ungated pages moved, 12 gated pages
  came back with FEWER runs (a finding), 139 unmeasurable.**
- ⚠ **Strip-to-strip lag only.** The correlation is periodic at the line pitch,
  so a far strip against the first ALIASES — it printed +6 then -7 for the same
  page. And ⛔ **a lag pinned at the search ceiling is not a measurement**: every
  page whose block detection had collapsed reported steps of ±4 and an angle of
  11–16°.
- ⛔ **A higher run count is not a correct read.** It says the lines were
  separated, nothing about what they say.
- ⛔ Nothing is re-cut and `prep_chunk.py` is untouched; ~270 pages are merged at
  the current geometry and re-addressing them needs the owner.
  ▶ `tools/prep_deskew_proto.py --selftest` 0 · `HEXAPLA_NO_DESKEW=1` 1
  ▶ `research/_evidence/thorlaks_merged_lines_are_skew_2026-09-16.md`
- ✅ **RESOLVED 2026-09-16 — the 12 gated pages that «LOST runs» lost NO LINES.**
  ⛔ Do not re-open it as a defect. ⚠⚠ **THE RUN COUNT BEFORE AND AFTER A SHEAR IS
  NOT THE SAME MEASUREMENT** — `choose_frac()` re-picks the threshold on the
  sheared band (v2:86 goes 0.400 → 0.650), so the two counts are read at
  different cutoffs and their difference means nothing on its own. Judge a
  sheared page by the PLATEAU RATIO, which is the pipeline's own health test
  (`counts[LINE_FRAC] >= FRAC_KEEP * peak` over `FRAC_SWEEP`, straight out of
  `choose_frac`): **6 of the 12 moved OFF the cliff ON to the plateau, 5 were
  already on it, 1 (v2:207) is still off, and 0 REGRESSED** — peak run count
  moves by at most 4 on any of them. `prep_deskew_proto.py` now prints
  `plat_b`/`plat_a` and only alarms when a page LEAVES the plateau.
  ⚠ An earlier cut of this measurement swept frac to 0.80, **outside
  `FRAC_SWEEP` (0.40-0.75)**, and that alone manufactured a bogus «v2:146 got
  worse» — ⛔ a metric that reads outside the pipeline's own range is not a
  measurement of the pipeline.
  ⛔ Still true and unchanged: a plateau proves STABILITY, never correctness,
  and nobody has read these pages.
  ▶ `research/_evidence/thorlaks_shear_lost_runs_explained_2026-09-16.md`

## ⛔ `research/_parts/` CANNOT WITNESS A PER-LINE WORD COUNT — 2026-09-16

`wordseg --expect` takes a per-LINE count. Part files are **verse-addressed and
do not mark line breaks** — the `/` is the printed virgula. Exhaustively: 47
part files, 25 mention a `lineNN`, **302 mentions, every one in prose or an
`<!-- ADJUDICATED -->` comment.** There is no line→text map in the corpus.
▶ The witness exists at the granularity the corpus records — the **WORD**.
▶ `research/_evidence/thorlaks_wordcount_witness_not_implementable_2026-09-16.md`

## The POSITION screen — read the mid-page COUNT, never the presence

`thorlaks_crop_heights.py` classifies each band by where it sits: `line00` is
the running head, the LAST crop is the printer's foot, and anything between is
the merged-row defect. Both are legitimately tall; only the middle is a defect.

    python tools/thorlaks_crop_heights.py --selftest        0
    HEXAPLA_NO_POSITION=1 ... --selftest                    1   (known-bad)

✅ It named Luke p66's `line42`, `line43`, `line45` — exactly the three crops a
human reader found independently — with no image read at all, and it exonerated
two tall printer's feet the band fraction had counted as defects.

⛔ **But it is a sorting aid, not a verdict:** 161 of 276 pages carry a mid-page
band, so it exonerates only 11 pages of the 172 the fraction flags. A centred
chapter heading lands in it too. Read the **count**, against the page's own kit
(p66 has 3; every other `luke_kit2` page has ≤1). The crop-count screen remains
the instrument that indicts a collapsed line finder.

## STRUCTURE IS THE CHEAP HALF — two reads of one page, 129 word disputes, 2026-09-17

Luke idx 61 has two independent reads: one from the packed sheets (~6.3x),
one from the line crops at native 8.3x. They agree on the running head, the
bare roman `IX`, the verse range 1-40, the same mid-verse break inside v40 and
the stained, catchword-less foot — every structural claim — and they disagree
at **129 word sites, about three per verse, in all forty verses.**

The split is systematic, not random: the crop read carries `f`, `p` or `c`
where the sheet read carries `s`, `l`, `v` or `m` (`hef`/`bef`,
`Leifum`/`Lerfum`, `toludu`/`fyludu`, `tueir`/`tucir`, `voru`/`poru`,
`kiemr`/`kicmr`). That is one printed sort family read two ways at scale, with
the mirror risk that the sheet read is reading by EXPECTATION toward the
Icelandic word it knows.

⛔ **Neither read may be merged as returned, and a third open read is not the
cure** — the ø precedent stands: a fresh read buys a different wrong answer and
a tuned brief buys more confident wrongness.

▶ The cure is a **forced choice** at the sites the two reads already fight
over: `tools/thorlaks_adjudicate_merge.py` derives them (129 content sites, of
which 119 are adjudicable once `[HN]` bracketing and the drop-cap are set by
convention), a reader settles each against the crop that holds it with
`NEITHER — <own reading>` and `ILLEGIBLE` named as expected answers, and the
tool folds the verdicts back. ⛔ It refuses to write while any derived site
lacks a verdict, and it re-screens its own output for long-s, ø, ö and
Cyrillic before writing. ⚠ Where the two reads AGREE it takes that wording
unchecked — **agreement is not correctness**, and that half of the page rests
on two readers, not on pixels.

⚠ **Consequence for every sheets-only read in the queue** (idx 62, 63, 64, 65):
each has line crops available and none has been read from them. Their text is
sheet-grade, which this page measured at about three disputed sites per verse.
Whether that is accepted or adjudicated is the owner's call, not a default.

## A REFUSAL IS NOT A PASS — five held reads the screen could not run on

`thorlaks_read_check.py` exited **2** on idx 61 read 1, idx 62, 63, 64 and 65:
they head their verse text `## Verse text`, `## Transcription` or
`## 1. RECORDS`, and the screen locates it by `## VERSES` alone. Four of them
had sat in `_work/` since 09-13/09-14 believed held only on the H/N ruling,
never once screened.

Two more holes in the same tool, both of the same family:

- the ø-site section was looked up **case-sensitively**, so `## ø candidate
  sites` (9 sites) and `## ø sites` (23) were never found and the site check
  printed a clean-looking **«0 listed»**;
- `ö` was not checked at all, though the conventions have said since 2026-09-10
  that there is no ö sort in this print — three sat unseen in idx 61 read 2.

★★ **A check that cannot run returns a clean-looking 0 — here, three times,
inside the tool written to stop exactly that.**

Fixed: the start heading is an explicit list, the end bound is an apparatus
heading, end-of-file, or a refusal (never a guess), and both are PRINTED.
`--selftest` is new and runs **9/9, exit 0**, with three known-bad halves that
must fail and do:

    python tools/thorlaks_read_check.py --selftest           0
    HEXAPLA_NO_READCHK=1      (blind `## ` bound)            misses a long-s
    HEXAPLA_NO_READCHK_SEC=1  (case-sensitive apparatus)     misses the section

▶ `research/_evidence/thorlaks_read_screen_could_not_run_2026-09-17.md`

## ★★ THE PAGE METHOD, RULED 2026-09-17 — one Workflow per page batch

⛔ **RULED by the owner 2026-09-17 16:40 («Yes to both»). Not a proposal, not
re-openable.** The full ruling and the next-campaign pilot items (a)-(e) are in
`docs/SETTLED.md` § Transcription; this section is the operating detail.

### What it replaces, and the measurement that forced it

Hand-orchestrating ONE Luke page on 2026-09-17 cost:

    ~10 Sonnet subagents   5 crop-read chunks + stitch + brief + 4 adjudications + merge
                           ~70k tokens each                            ≈ 0.7M tokens
    ~25 main-session turns at 150-200k context each                    ≈ 4M tokens

⇒ **The main session was 85 % of the bill and 100 % of the wall-clock.** Luke
had ~45 pages left and the Bible ~1,300. ⛔ Hand-orchestration is years, and no
number of extra agents fixes it — the cost is the MAIN SESSION's re-billed
context, not the agents.

### The pipeline

    crop read A (Sonnet, LINE-level, line00 INCLUDED)  ─┐
    crop read B (Sonnet, chunk boundaries OFFSET ~7)   ─┼─> 2-of-3 vote in code
    crop read C (blind, third instrument)              ─┘        │
                                                                 v
      tools/thorlaks_crop_read_stitch.py   chunks -> verse-addressed read
      tools/thorlaks_read_check.py --file  screen; ⛔ a refusal is NOT a pass
      tools/thorlaks_adjudicate_brief.py   read A + read B -> ADJ_CHUNK briefs
      Sonnet adjudicators, one per chunk   -> ADJ_RESULT_CHUNK files
      tools/thorlaks_adjudicate_merge.py   verdicts -> candidate; refuses if a
                                           site lacks one
      cp to research/_parts/ ; tools/thorlaks_chain.py --apply

▶ The brief tool IMPORTS the merge tool's own `sites()`/`adjudicable()` cut, so
the two cannot disagree about what was asked.

### Rules that cost a session each

- ⚠ **No sheets read.** 6.3x is the weaker instrument and needs a hand-built
  kit. Two 8.3x crop reads give a diff at full resolution.
- ⚠ **Offset the two reads' chunk boundaries** (~7 crops) — a chunk-edge error
  must not be able to land on the same site twice.
- ⚠ **Scripts run in `effort:'low'` agents.** stitch / read_check / brief /
  merge / chain are 0-vision; the agent returns rc plus the `[X]` lines. ⛔ The
  main session never `cat`s a read.
- ⚠ `PYTHONIOENCODING=utf-8` on every tool that prints ø/þ.
- ⚠ The auto-mode classifier BLOCKS a script's `--apply` straight into
  `research/_parts/`. Write to `_work/`, then `cp`.
- ⚠ Crops are numbered from **line00**; a chunk plan starting at line01 leaves
  the running head unread.
- ⚠ Expect a crop chunk to write `f` for every long-s. Those become f/s
  adjudication sites **by design** — ⛔ do not re-commission the read for it.
- ★ **`[X] N site(s) with NO verdict` is the only coverage authority.**
- ★ **A verdict line carries PROSE.** Any tool folding free text into scripture
  must cut at the first reason; control = count `(` in the candidate's verse
  lines (expect only legitimate hedges).
- ★ **An adjudicator's OWN reading is not screened by the two-read preference**
  — there is no second reading to prefer over it. idx 62 v56 came back
  `NEITHER - Sör` and row 40 closes that this print has no `ö` sort. The merge
  now refuses that site BY NAME (2026-09-17) instead of failing the whole-text
  screen with a bare «ö».

### Two defects fixed at source on 2026-09-17, both with controls

- **The stitcher folded the RUNNING HEAD into the page's first verse.** idx 62
  line00 was correctly reported as `[running head, not body text] Euangelium …
  XXXI`, and the stitcher — which skipped only a crop whose WHOLE line was one
  bracket — tokenised it into Luke 9:40. ⚠ **Every page has a running head, so
  this was never one page's defect.** Fixed in
  `thorlaks_crop_read_stitch.RUNHEAD`; a crop whose line OPENS with a bracket
  declaring no body text contributes no text and prints a finding.
  ⛔ Control: `HEXAPLA_NO_RUNHEAD=1` puts the leak back.
- **`merge_parts` DELETED the tail of a verse the print breaks at a page foot.**
  Luke 9:40 is split (idx 61 head + idx 62 tail); the overlap was reported as
  «transcribed differently by two parts» and «the FIRST part's text was kept»,
  i.e. the tail was dropped silently. Fixed in `thorlaks_merge_parts.SEAM_RE`:
  when the earlier part EXPLICITLY marks the verse as breaking off, the halves
  are JOINED, the seam marker (apparatus, not scripture) is dropped, and the
  tail's repeated verse number is stripped. ⚠ The marker must be an explicit
  report by the read — ⛔ never inferred from punctuation.
  ⛔ Control: `HEXAPLA_NO_SEAMJOIN=1` restores the first-wins drop.
- **The merge tool is now MULTI-CHAPTER.** A page spanning two chapters (idx 62
  is Luke 9:40-62 + 10:1-16) is keyed by `(chapter, verse)` and emits one
  `## Book N` heading per chapter. ⚠ Verdict files still key a site by `v<N>`
  alone, so the tool REFUSES outright if a verse number occurs in two chapters
  of the same page.
