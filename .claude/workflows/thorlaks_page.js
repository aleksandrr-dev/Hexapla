export const meta = {
  name: 'thorlaks_page',
  description: 'Transcribe Thorlaksbiblia pages: two offset crop reads, stitch, brief, adjudicate, merge candidate',
  whenToUse: 'One batch of Thorlaksbiblia (or Karl XII) page indices, from line crops to a merge candidate the main session only has to rule on. The RULED method, owner 2026-09-17 16:40.',
  phases: [
    { title: 'Plan', detail: 'count the crops on disk, cut A and B chunk plans at OFFSET boundaries' },
    { title: 'Read A', detail: 'Sonnet crop reads, LINE-level, line00 included; each chunk self-screened by thorlaks_chunk_check.py' },
    { title: 'Read B', detail: 'independent Sonnet crop reads, boundaries offset ~7 crops' },
    { title: 'Gate', detail: 'chunk_check --read A/B + numeral seam screen (0 vision); names the crops to re-read' },
    { title: 'Repair', detail: 'one Sonnet agent per failing read re-reads ONLY the named crops and fixes that chunk; re-gated, max 2 rounds' },
    { title: 'Stitch', detail: 're-screen EVERY chunk, then stitch both reads, screen them, generate the adjudication briefs (0 vision)' },
    { title: 'Adjudicate', detail: 'one Sonnet adjudicator per brief chunk, forced choice against the pixels' },
    { title: 'Merge', detail: 'fold the verdicts, cp to research/_parts, chain dry run (0 vision)' },
  ],
}

// ---------------------------------------------------------------------------
// WHY THIS EXISTS
// ---------------------------------------------------------------------------
// Measured 2026-09-17: hand-orchestrating ONE Luke page cost ~10 Sonnet agents
// (~0.7M tokens) AND ~25 main-session turns at 150-200k context each (~4M of
// re-billed context). The MAIN SESSION was 85 % of the bill and 100 % of the
// wall-clock. Luke had ~45 pages left; the Bible ~1,300.
//
// So the main session launches ONE of these and reads ONE result. Every agent
// here is a fresh context, so the 25-image read guard and the 220k context stop
// never bind, and nothing that was read once is re-billed on every later turn.
//
// ⛔ RULED by the owner 2026-09-17 16:40 ("Yes to both"). Not a proposal.
//    Full ruling: docs/SETTLED.md § Transcription. Detail: docs/TRANSCRIPTION.md.
//
// ✅ The 2-of-3 MAJORITY VOTE (item 3 of the ruling) IS BUILT, 2026-09-17:
//   `thorlaks_adjudicate_merge.py --c` and the brief tool's `--c` take a third
//   read and resolve each site in plain code, POSITION BY POSITION (difflib
//   cuts two adjacent disputed words into one site, and one three-way position
//   voids the whole site). Controls: `tools/test_majority_vote.py`, known-bad
//   `HEXAPLA_NO_VOTE=1`, and the two-read path rebuilds idx 62 byte-identical.
//   ⚠ NO READ C HAS EVER BEEN COMMISSIONED, so the vote's effect on a real
//   page is UNKNOWN - ⛔ do not quote a figure for it. This script still runs
//   two reads; the first page given a read C is the measurement.
//
// ✅ The READ STAGE IS NOW GATED, 2026-09-18: `tools/thorlaks_chunk_check.py`
//   screens each CROP READ CHUNK - inside the reader before it returns, and
//   again in the Stitch phase, because a read's self-report is not evidence
//   about the read. It exists because the 2026-09-17 run's three failures
//   (idx 63 text loss, idx 64 long-s, idx 65 a dropped numeral) were ALL
//   visible in the chunk files with no vision, and none was caught until two
//   whole reads had been paid for: ~3.36M tokens, 0 pages merged.
//
// USAGE (args is a JSON value, never a JSON string):
//   { book: "Luke", kit: "luke_kit2", data: "C:/Projects/Hexapla-releases",
//     tools: "C:/Projects/Hexapla/tools", date: "2026-09-17",
//     pages: [ { page: "p63", chapter: 10, firstVerse: 17 }, ... ] }
// `chapter`/`firstVerse` = the chapter open at the page HEAD and the first
// PRINTED numeral expected on it. ⚠ A verse continued from the previous page
// is firstVerse - 1, and the stitcher handles that itself.
// `reuseReads: true` on a page skips Read A/B and starts at the Gate with the
// CROP_READ chunk files already in _work/ (a page blocked by an earlier run).
//
// ✅ A GATE STOP NO LONGER ENDS THE PAGE (2026-09-22, owner: «make sure it
//   doesn't come out blocked»). Batch 1 (p68-p70) lost 2 of 3 pages: p70 to one
//   numeral read B missed (the seam screen named line36/37), p69 to a stitcher
//   gap since fixed in the tool (glued numerals, GLUESPLIT selftest). The Gate
//   now returns the crops it names, and a Repair agent re-reads ONLY those and
//   fixes the chunk - the gate's own instruction, previously left to a main
//   session that never came. Still never a vote: the repair reads pixels.
// ---------------------------------------------------------------------------

const A = args || {}
const BOOK = A.book || 'Luke'
const KIT = A.kit || (BOOK.toLowerCase() + '_kit2')
const DATA = A.data || 'C:/Projects/Hexapla-releases'
const TOOLS = A.tools || 'C:/Projects/Hexapla/tools'
const DATE = A.date || 'undated'
const PAGES = A.pages || []
const OFFSET = A.offset || 7          // crops by which read B's boundaries shift
const CHUNK = A.chunk || 14           // crops per read chunk (13-15 measured ok)

if (!PAGES.length) {
  log('⛔ no pages passed in args.pages - nothing to do')
  return { error: 'args.pages was empty', pages: [] }
}

const PY = 'PYTHONIOENCODING=utf-8 python'

// Conventions pasted into EVERY read prompt. ⚠ A rule that is not here does not
// reach the reader: research/THORLAKS_CONVENTIONS.md is the source of truth and
// this is its operating extract.
const CONVENTIONS = `
## Conventions - these are SETTLED. Apply them, do not re-open them.

1. **Long-s is written plain \`s\`.** The sort \`ſ\` never appears in returned
   text. Long-s has NO crossbar; \`f\` HAS one. ⚠ Check every f/s by the
   crossbar at zoom - reads that did not have come back with "fagde"/"Jefus"
   throughout, and each one becomes an adjudication site.
2. ⛔ **No \`ø\` is adjudicated in this book** (owner's ruling, row 48): every o
   stands plain. ⛔ This print also has NO \`ö\` sort (row 40). A horizontal bar
   over a vowel is a NASAL BAR, not an umlaut.
3. **Nasal bars are KEPT as printed** (\`ñ\`, \`ō\`) and NEVER expanded.
4. **A capital that could be H or N is written \`[HN]\`** and left bracketed -
   ⛔ never resolved by what the word "should" be. Report the top-left flourish
   if you can see it.
5. **Report the PRINTED verse numerals** in the NUMERALS table, even when one
   disagrees with what you expect. A printed numeral that disagrees with the
   KJV is a FINDING and is reported as printed, never corrected.
6. **A crop that carries no body text is reported as such**, bracketed at the
   START of the line: \`[running head, not body text] ...\`,
   \`[blank paper under stain, no legible text]\`, \`[chapter heading: Cap. X]\`.
   ⚠ Crops are numbered from **line00**, and line00 is usually the running head.
   ⛔ **A TAG NEVER REPLACES TEXT, and \`not body text\` / \`running head\` is
   the tag the stitcher DISCARDS THE WHOLE LINE ON.** Put it on a line that
   carries verse text and that verse is silently LOST - this is how Luke
   10:19-20 vanished off idx 63. So: if the crop carries ANY body text, it is
   a body line. Transcribe it plainly, with no opening tag. If only ONE letter
   is unreadable (a drop-cap, a swash), that is \`[illegible]\` **inside** the
   line, never a tag in front of it.
7. ⛔ **Do not consult any other text of this book, printed or electronic.** A
   reading that comes from knowing the verse is not evidence about this page.
8. A hedge is a correct answer. \`[?]\` after an uncertain word; \`[illegible]\`
   where there is nothing to read.
9. ⛔ **The printed numerals must come back as a RUN with no holes.** Before you
   write the file, read your own NUMERALS table straight through: 3, 4, 5, 6 -
   if it jumps, you dropped one, and every numeral after it is now wrong (this
   desynchronised 28 of them on idx 65). Go back to that crop and look again.
   If the numeral really is not printed there, say so **in NOTES, naming the
   numeral** - a declared hole is a finding, an undeclared one is a defect.
10. ⛔ **A NUMERAL CAN BE CUT IN HALF BY THE CROP BOUNDARY.** Crops overlap by
   a few rows, so the top and bottom strips of every crop show slivers of the
   neighbouring lines. Those slivers are usually ascenders and descenders and
   are NOT transcribed - but a verse numeral printed low and right is exactly
   the glyph the cut halves: its top bar sits on the bottom edge of lineNN and
   its body in the top strip of lineNN+1 (Luke idx 66, 13:7 - reported
   «confidently absent» twice by a reader who checked lineNN alone). So:
   before you write that a numeral is NOT printed, open **lineNN+1 as well**
   and look at its top strip at the x-position where the numeral should be.
   A digit-shaped mark in an edge strip goes in NOTES as
   \`edge digit at lineNN bottom / lineNN+1 top, x≈NNNN\`, never dropped as bleed.
   A \`z\` (the conjunction ligature) has a mid-crossbar AND a terminal loop;
   a \`7\` has neither.
11. **A chapter heading is written EXACTLY \`[chapter heading: Cap. XVII]\`**
   (the roman numeral as printed). ⛔ A CROP CAN HOLD THE LAST LINE OF A
   CHAPTER *AND* THE CENTRED NUMERAL OF THE NEXT (luke_kit3 p70 line19). Then
   write the body text FIRST and the heading tag AFTER it, on the same row:
   \`lineNN | safnast z Erner. [chapter heading: Cap. XVIII]\`. The stitcher
   splits the row there. ⛔ Never put the heading tag first on such a row, and
   never drop the text to report only the heading. A decorated drop-cap is
   NOT a heading tag: write it inline as \`[ornate initial: X]\` or read it.
12. **Margin apparatus is NOT transcribed** (conventions table, SETTLED): a
   cross-reference in the margin such as \`Matth. 5/18.\` or \`Matth.19/9.\`
   is left out of the LINES row entirely - it is not scripture, and its
   digits look like verse numerals to the stitcher (luke_kit3 p69 read B).
   An INLINE gloss inside the text block IS scripture and IS transcribed.
`

function cropReadPrompt(page, chunkIdx, from, to, series) {
  return `Transcribe ONE chunk of line crops from the Þorláksbiblía 1644 print,
${BOOK} PDF idx ${page.page.replace(/^p/, '')}. This is read **${series}** - an
INDEPENDENT read. ⛔ Do not look for, open, or reconcile with any other read of
this page; a second instrument that copies the first measures nothing.

## What to open

\`${DATA}/research/_prep/${KIT}/${page.page}/lineNN.png\` for NN = ${pad(from)}..${pad(to)}
and ONLY those. Each crop holds exactly one line of running text at 8.3x native.
\`page.png\` is for layout only. Zoom anything you are unsure of.

⛔ **That kit directory is READ-ONLY.** It is the ADDRESSING authority for this
page - every record ever merged is addressed by the \`lineNN.png\` names in it,
and a stray \`lineNN_zoom.png\` has already been miscounted as a crop by a gate.
Write every zoom, crop and scratch image to \`${DATA}/_work/_scratch/${page.page}/\`
(create it) and NOTHING into the kit directory.
${CONVENTIONS}${page.notes ? `
## Known about THIS page (from the pre-read triage - verify, do not assume)

${page.notes}
` : ''}
## What to return - write it to a FILE, and return only the path

Write \`${DATA}/_work/${BOOK.toLowerCase()}_${page.page}_CROP_READ${series === 'B' ? 'B' : ''}_CHUNK${chunkIdx}.md\`
with EXACTLY these sections and nothing else:

    # ${BOOK} idx ${page.page.replace(/^p/, '')} - CROP READ${series === 'B' ? ' B' : ''} chunk ${chunkIdx} (line${pad(from)}-line${pad(to)})

    ## LINES
    lineNN | <the line, verbatim, one line per crop, NO line left out>

    ## NUMERALS
    lineNN | <printed numeral> | <the word it precedes>

    ## HN
    lineNN | <the word> | flourish: <what you can see> | written: [HN]

    ## NOTES
    - <anything you hedged, and why>

## ⛔ SCREEN YOUR OWN FILE BEFORE YOU RETURN IT

The three defects that wrecked the last run were all visible in the chunk file
with no vision at all, and none was caught until two whole reads had been paid
for. So screen yourself, at 0 token cost:

    PYTHONIOENCODING=utf-8 python ${TOOLS}/thorlaks_chunk_check.py \\
        --file <the file you just wrote> \\
        --kit-dir ${DATA}/research/_prep/${KIT}/${page.page}

**rc 0 = you may return. rc 1 = go back to the named crop and LOOK AGAIN.**
⛔ Fix it at the CROP, by re-reading the pixels - never by editing the text to
satisfy the gate. A \`[X]\` you cannot clear by looking is a real finding about
the page: say so in NOTES, naming the crop and the numeral, and return anyway.
⚠ rc 2 means the screen could not run, and A CHECK THAT CANNOT RUN DID NOT
PASS - fix the file's structure and run it again.

Then return ONLY the absolute path of the file you wrote, plus the screen's
final rc. ⛔ No summary, no transcription in your reply - the file is the
deliverable.`
}

function pad(n) { return (n < 10 ? '0' : '') + n }

function scriptsPrompt(page, plan) {
  const lower = BOOK.toLowerCase()
  return `Run these scripts and return their results. ⛔ This is a 0-VISION task:
do NOT open any image, and do NOT \`cat\` a read file into your reply.

Working directory: \`${DATA}\` (⚠ NOT a git repo). Every tool by ABSOLUTE path.
⚠ \`PYTHONIOENCODING=utf-8\` on every one of them - they print ø/þ.

0. ⛔ **RE-SCREEN EACH READ WHOLE - EVERY CHUNK *AND THE SEAMS BETWEEN THEM*.**
   The readers were told to screen themselves; A READ'S SELF-REPORT IS NOT
   EVIDENCE ABOUT THE READ, so this pass is the one that counts.

   ${PY} ${TOOLS}/thorlaks_chunk_check.py --read --book ${BOOK} \\
       --page ${page.page} --series A --data ${DATA} \\
       --kit-dir ${DATA}/research/_prep/${KIT}/${page.page}
   ... and again with \`--series B\`.

   ⛔ **Use \`--read\`, NOT \`--file\` per chunk.** On 2026-09-18 idx 65 read B
   ended chunk1 at the printed numeral 52 and opened chunk2 at 54: Luke 11:53
   was dropped EXACTLY ON THE CHUNK BOUNDARY. Every chunk was internally
   consecutive, so all 9 chunks returned rc 0 - nine plausible clean numbers -
   and the page still died two stages later. A RUN CHECKED ONLY INSIDE ITS OWN
   CHUNK HAS A HOLE AT EVERY SEAM, and the seams are exactly where reads A and
   B are offset from each other.

   Report every \`[X]\` verbatim with its chunk name, and both rcs.
   ⛔ If EITHER read is rc 1, **STOP - do not stitch, do not brief.** Set
   ok=false and name the findings; the page goes back for a re-read of the
   named crops. ⚠ rc 2 is a refusal, and a refusal is not a pass.

   Then, STILL before the stitch, the BISECTED-NUMERAL screen (2026-09-20):
   ${PY} ${TOOLS}/thorlaks_numeral_seam_screen.py --book ${BOOK} --page ${page.page}
   rc 1 names the crop AND its successor for every numeral one read tabled
   and the other has neither tabled nor inline - a numeral halved by the cut
   lives in the TOP strip of lineNN+1 (Luke idx 66, 13:7, reported «absent»
   twice by a reader who checked lineNN alone). ⛔ rc 1 = STOP: re-read the
   named crops in the read that lacks it; a compound key (\`line51/52\`) needs
   a seam crop over both, never a guess. rc 2 = a read is missing.

0. ⛔ MOVE ASIDE this page's DOWNSTREAM files before stitching - never delete:
   mkdir -p _work/_stale/${lower}_${page.page}_$(date +%Y%m%d_%H%M%S) and \`mv\`
   into it every one of these that exists: \`_work/${lower}_${page.page}_readA_*.md\`,
   \`_work/${lower}_${page.page}_readB_*.md\`, \`_work/${lower}_${page.page}_ADJ_CHUNK*.md\`,
   \`_work/${lower}_${page.page}_ADJ_RESULT_CHUNK*.md\`,
   \`_work/${lower}_${page.page}_ADJUDICATION_RESULT_*.md\`,
   \`_work/${lower}_${page.page}_MERGE_CANDIDATE.md\`.
   ⛔ NOT the \`_CROP_READ_\` / \`_CROP_READB_\` chunk files - those ARE the reads.
   Why: the stitcher REFUSES to overwrite \`--out\` (rc 1), and on 2026-09-22
   the p69 reuseReads page stitched nothing, read the STALE pre-fix stitch
   instead, and the brief refused on mismatched keys. List what you moved.
1. Stitch read A:
   ⛔ Stitch rc 1 (including «exists») is a STOP: ok=false, name it. Never
   read or brief an output file this step did not just write.
   ${PY} ${TOOLS}/thorlaks_crop_read_stitch.py --book ${BOOK} --page ${page.page} \\
       --kit ${KIT} --chapter ${page.chapter} --first-verse ${page.firstVerse} \\
       --out _work/${lower}_${page.page}_readA_${DATE}.md
   ⚠ \`--kit ${KIT}\` on BOTH stitches: the tool defaults to \`<book>_kit2\`,
   and a page outside that kit fails its coverage check against the wrong dir.
2. Stitch read B the same way (it reads the \`_CROP_READB_\` chunks; pass
   \`--series B\` if the tool offers it, else set it as that tool's docstring
   directs) to \`_work/${lower}_${page.page}_readB_${DATE}.md\`.
3. Screen BOTH:
   ${PY} ${TOOLS}/thorlaks_read_check.py --file <each read>
   ⛔ A REFUSAL IS NOT A PASS. If the tool refuses, say so and stop.
4. Generate the adjudication briefs:
   ${PY} ${TOOLS}/thorlaks_adjudicate_brief.py --book ${BOOK} --page ${page.page} \\
       --chapter ${page.chapter} --kit ${KIT} \\
       --a _work/${lower}_${page.page}_readA_${DATE}.md \\
       --b _work/${lower}_${page.page}_readB_${DATE}.md

⚠ Expect FINDINGS and report every one verbatim - especially
«running head, contributed NO text», «numeral taken from the NUMERALS table»,
a non-text crop, and an undetected chapter break. A stitch whose chapter break
was missed is WRONG and must not be briefed.

## Return (StructuredOutput)

Every rc, every finding line, and the list of ADJ_CHUNK files that now exist.
If any step failed, set ok=false and say which - ⛔ never report a step that
could not run as passed.`
}

const GATE_SCHEMA = {
  type: 'object',
  required: ['ok', 'rc', 'targets'],
  properties: {
    ok: { type: 'boolean', description: 'true only if all three screens ran and returned rc 0' },
    rc: { type: 'array', items: { type: 'string' }, description: 'e.g. "chunk_check A rc=0"' },
    targets: {
      type: 'array',
      description: 'one entry per [X] / HARD finding; empty when ok',
      items: {
        type: 'object',
        required: ['series', 'crops', 'finding'],
        properties: {
          series: { type: 'string', enum: ['A', 'B'], description: 'the read that must be repaired' },
          crops: { type: 'array', items: { type: 'string' }, description: 'lineNN names the finding tells you to open' },
          finding: { type: 'string', description: 'the finding line VERBATIM' },
        },
      },
    },
  },
}

function gatePrompt(page) {
  return `Run three screens on the two crop reads of ${BOOK} ${page.page} and report
what they name. ⛔ 0-VISION: open no image, \`cat\` no chunk into your reply.

Working directory \`${DATA}\` (⚠ not a git repo); tools by absolute path.

   ${PY} ${TOOLS}/thorlaks_chunk_check.py --read --book ${BOOK} --page ${page.page} \\
       --series A --data ${DATA} --kit-dir ${DATA}/research/_prep/${KIT}/${page.page}
   ... the same with \`--series B\`, then
   ${PY} ${TOOLS}/thorlaks_numeral_seam_screen.py --book ${BOOK} --page ${page.page}

⛔ Run each UNPIPED (a pipe eats the rc). rc 2 = the screen could not run, and a
screen that could not run DID NOT PASS: set ok=false and put it in \`rc\`.

For EVERY \`[X]\` line (chunk_check) and EVERY \`HARD\` line (seam screen) return
one target: the series whose read must be fixed (for the seam screen, the read
that LACKS the numeral), the lineNN crops the finding tells you to open (for a
bisected numeral, lineNN AND lineNN+1), and the finding VERBATIM. \`[.]\` and
SOFT lines are not targets. ok = every rc 0 and no target.`
}

function repairPrompt(page, series, targets) {
  const lower = BOOK.toLowerCase()
  const crops = [...new Set(targets.flatMap(t => t.crops))].sort()
  return `Repair read **${series}** of ${BOOK} idx ${page.page.replace(/^p/, '')} at the crops a
screen named. ★ This is NOT a re-read of the page: open ONLY these crops -
${crops.join(', ')} - under \`${DATA}/research/_prep/${KIT}/${page.page}/\` (READ-ONLY;
zooms go to \`${DATA}/_work/_scratch/${page.page}/\`).

The screen's findings, verbatim:
${targets.map(t => '  - ' + t.finding).join('\n')}

The read lives in \`${DATA}/_work/${lower}_${page.page}_CROP_READ${series === 'B' ? 'B' : ''}_CHUNK*.md\`.
Find the chunk file(s) whose \`## LINES\` hold those crops. ⛔ Do not open or
reconcile with the other read's files - that is a vote, and a vote is not a
reading.
${CONVENTIONS}
## What to do

1. Look at each named crop at native size, zoomed. A numeral halved by the cut
   lives in the TOP strip of the next crop; a small numeral sits tight to the
   left edge, often beside a swash capital.
2. Correct the chunk file FROM THE PIXELS: the \`lineNN\` row in LINES (the
   numeral inline, where it is printed) AND its \`## NUMERALS\` row
   (\`lineNN | N | <first word>\`). Touch no other row.
3. If after looking you are sure the numeral is NOT PRINTED, change nothing in
   LINES and add a NOTES line naming it:
   \`- numeral N is NOT PRINTED at lineNN (re-read at native, <what you saw>)\`.
⛔ Never edit text to satisfy the screen. Fix only what the pixels show.

4. Re-screen every file you changed, unpiped:
   ${PY} ${TOOLS}/thorlaks_chunk_check.py --file <file> \\
       --kit-dir ${DATA}/research/_prep/${KIT}/${page.page}

Return ONLY: each file you changed, the rows you changed (before -> after), and
the screen rc. No transcription beyond those rows.`
}

const CHUNKS_SCHEMA = {
  type: 'object',
  required: ['ok', 'chunks', 'findings'],
  properties: {
    ok: { type: 'boolean' },
    chunks: { type: 'array', items: { type: 'string' },
              description: 'absolute paths of the ADJ_CHUNK brief files' },
    sites: { type: 'integer', description: 'sites the brief derived, -1 if unknown' },
    findings: { type: 'array', items: { type: 'string' } },
    rc: { type: 'array', items: { type: 'string' } },
  },
}

function adjudicatePrompt(page, chunkPath) {
  return `Settle the disputed word sites in ONE adjudication brief.

★ This is NOT a transcription task and NOT a re-read of the page. Two
independent reads of ${BOOK} idx ${page.page.replace(/^p/, '')} already exist and
DISAGREE at the sites listed in the brief. Settle each one against the pixels.

Read the brief in full first - it carries its own task line, its crop range and
the conventions: \`${chunkPath}\`

Open ONLY the crops the brief names, under
\`${DATA}/research/_prep/${KIT}/${page.page}/\`. ⛔ Not the packed sheets, and
⛔ no other text of this book.
${CONVENTIONS}
## The verdict format - copy the brief's A= and B= EXACTLY

    lineNN | v<N> | A=<exactly as the brief has it> | B=<exactly as the brief has it> | VERDICT: <A | B | NEITHER - <your reading> | ILLEGIBLE> | conf: <high|medium|low>

⛔ **The verdict line carries ONLY the reading.** No parentheses, no reasons, no
prose - a tool folds this line straight into scripture and cuts at the first
reason it finds. Put your reasoning in sentences BELOW the line.
⛔ Never return \`ö\` or \`ø\` in a verdict (rows 40 and 48) - an adjudicator's
own reading is not screened by the two-read preference, and the merge will
refuse the site by name.
⚠ An empty side is written \`(nothing)\` and is a real answer, not a gap.

Write the verdict lines to the brief's matching RESULT file - same name with
\`ADJ_CHUNK\` replaced by \`ADJ_RESULT_CHUNK\` - and return ONLY that path.
⛔ Answer EVERY site in the brief. The merge refuses to write while one lacks a
verdict, and that refusal is the only coverage authority there is.`
}

const MERGE_SCHEMA = {
  type: 'object',
  required: ['ok', 'rc', 'lines'],
  properties: {
    ok: { type: 'boolean' },
    rc: { type: 'array', items: { type: 'string' } },
    lines: { type: 'array', items: { type: 'string' },
             description: 'the [X] lines, the site/verdict counts, the chapter list, every finding' },
    candidate: { type: 'string' },
    needsOwner: { type: 'array', items: { type: 'string' },
                  description: 'anything a script refused to decide' },
  },
}

function mergePrompt(page, results) {
  const lower = BOOK.toLowerCase()
  return `Fold the adjudication verdicts for ${BOOK} idx ${page.page.replace(/^p/, '')}
into a merge candidate. ⛔ 0-VISION: open no image, \`cat\` no read into your reply.

Working directory \`${DATA}\`; tools by absolute path; \`PYTHONIOENCODING=utf-8\`.

1. Concatenate the RESULT chunks IN ORDER into one verdicts file:
   ${results.map(r => '     ' + r).join('\n')}
   -> \`_work/${lower}_${page.page}_ADJUDICATION_RESULT_${DATE}.md\`
2. Build the candidate, UNPIPED, into \`_work/\` (⚠ the auto-mode classifier
   blocks a script's --apply straight into \`research/_parts/\`):
   ${PY} ${TOOLS}/thorlaks_adjudicate_merge.py \\
       --a _work/${lower}_${page.page}_readA_${DATE}.md \\
       --b _work/${lower}_${page.page}_readB_${DATE}.md \\
       --verdicts _work/${lower}_${page.page}_ADJUDICATION_RESULT_${DATE}.md \\
       --book ${BOOK} --chapter ${page.chapter} --page ${page.page} \\
       --out _work/${lower}_${page.page}_MERGE_CANDIDATE.md --apply
   ⛔ If it prints \`[X] N site(s) with NO verdict\` or \`unusable\`, STOP and
   return those lines verbatim. That line is the ONLY coverage authority; a
   missing verdict is never worked around.
3. Controls on the candidate, and report BOTH numbers:
   - one \`## ${BOOK} <N>\` heading per chapter the page spans;
   - \`grep -E '^[0-9]+ ' <candidate> | grep -c '('\` - the NEITHER-reason leak
     control. Anything above the count of legitimate hedges is a leak.
4. \`cp\` the candidate to \`research/_parts/${lower}_${page.page}.md\`, then the
   chain DRY RUN (⛔ no --apply - the main session rules on the seam):
   ${PY} ${TOOLS}/thorlaks_chain.py --book ${BOOK} --file research/_parts/${lower}_${page.page}.md

⚠ Report a page-break seam verbatim: a verse split across two pages must show
as JOINED, never as «transcribed differently by two parts».

Return every rc and every reported line. ⛔ Report nothing as passed that could
not run.`
}

// --- Plan: how many crops does each page have, and where do the cuts fall? ---
phase('Plan')
const PLAN_SCHEMA = {
  type: 'object',
  required: ['crops'],
  properties: {
    crops: { type: 'integer', description: 'number of lineNN.png files, -1 if the directory is unreadable' },
    notes: { type: 'array', items: { type: 'string' } },
  },
}

function chunkPlan(crops, offset) {
  // Read B's boundaries are shifted by `offset` crops so a chunk-edge error
  // cannot land on the same site in both reads. ⚠ line00 is always included.
  const cuts = []
  let start = 0
  if (offset > 0 && crops > offset) { cuts.push([0, offset - 1]); start = offset }
  for (let i = start; i < crops; i += CHUNK) {
    cuts.push([i, Math.min(i + CHUNK - 1, crops - 1)])
  }
  return cuts
}

const out = await pipeline(
  PAGES,

  // 1 · count the crops on disk (cheap, mechanical, 0 vision)
  p => agent(
    `Count the line crops for ${BOOK} ${p.page}: how many \`lineNN.png\` files are in
\`${DATA}/research/_prep/${KIT}/${p.page}/\`? Report the count and the highest NN.
⛔ Open none of them - this is an \`ls\`, not a read. If the directory does not
exist, return crops = -1 and say so; ⛔ do not return 0 for a read that failed.`,
    { label: `plan:${p.page}`, phase: 'Plan', model: 'sonnet', effort: 'low', schema: PLAN_SCHEMA }),

  // 2 · read A - chunks cut from line00
  (plan, p) => {
    if (!plan || plan.crops < 1) {
      log(`⛔ ${p.page}: no crops on disk (${plan ? plan.crops : 'null'}) - prep this page first`)
      throw new Error(`${p.page} has no crops`)
    }
    if (p.reuseReads) {
      log(`${p.page}: reuseReads - Read A/B skipped, the chunk files in _work/ go to the Gate`)
      return { crops: plan.crops, a: 'reused', cuts: 0 }
    }
    const cuts = chunkPlan(plan.crops, 0)
    log(`${p.page}: ${plan.crops} crops -> read A in ${cuts.length} chunk(s)`)
    return parallel(cuts.map(([f, t], i) => () =>
      agent(cropReadPrompt(p, i + 1, f, t, 'A'),
            { label: `readA:${p.page}:${i + 1}`, phase: 'Read A', model: 'sonnet' })))
      .then(r => ({ crops: plan.crops, a: r.filter(Boolean).length, cuts: cuts.length }))
  },

  // 3 · read B - SAME crops, DIFFERENT boundaries
  (prev, p) => {
    if (p.reuseReads) return Object.assign({}, prev, { b: 'reused', bcuts: 0 })
    const cuts = chunkPlan(prev.crops, OFFSET)
    return parallel(cuts.map(([f, t], i) => () =>
      agent(cropReadPrompt(p, i + 1, f, t, 'B'),
            { label: `readB:${p.page}:${i + 1}`, phase: 'Read B', model: 'sonnet' })))
      .then(r => Object.assign({}, prev, { b: r.filter(Boolean).length, bcuts: cuts.length }))
  },

  // 3½ · gate, and REPAIR what it names (max 2 rounds) instead of stopping
  async (prev, p) => {
    const repairs = []
    let gate = null
    for (let round = 0; round <= 2; round++) {
      gate = await agent(gatePrompt(p),
        { label: `gate:${p.page}:${round}`, phase: 'Gate', model: 'sonnet', effort: 'low', schema: GATE_SCHEMA })
      if (!gate || gate.ok) break
      if (!gate.targets || !gate.targets.length) break   // rc 2 / a refusal: nothing to re-read
      if (round === 2) break
      log(`${p.page}: gate round ${round} named ${gate.targets.length} finding(s) - repairing`)
      const bySeries = ['A', 'B'].map(s => [s, gate.targets.filter(t => t.series === s)])
        .filter(([, ts]) => ts.length)
      const r = await parallel(bySeries.map(([s, ts]) => () =>
        agent(repairPrompt(p, s, ts),
          { label: `repair:${p.page}:${s}:${round}`, phase: 'Repair', model: 'sonnet' })))
      repairs.push(...r.filter(Boolean))
    }
    if (!gate || !gate.ok)
      log(`⛔ ${p.page}: the gate still fails after repair - ${gate ? (gate.targets || []).map(t => t.finding).join(' | ') : 'gate agent returned nothing'}`)
    return Object.assign({}, prev, { gate, repairs, gateOk: !!(gate && gate.ok) })
  },

  // 4 · stitch both, screen both, brief (0 vision, cheap)
  (prev, p) => {
    if (!prev.gateOk) {
      return Object.assign({}, prev, { stitch: { ok: false, chunks: [],
        findings: ['gate failed after repair: ' + ((prev.gate && prev.gate.targets) || []).map(t => t.finding).join(' | ')] } })
    }
    return agent(scriptsPrompt(p, prev),
      { label: `stitch:${p.page}`, phase: 'Stitch', model: 'sonnet', effort: 'low', schema: CHUNKS_SCHEMA })
      .then(r => Object.assign({}, prev, { stitch: r }))
  },

  // 5 · one adjudicator per brief chunk
  (prev, p) => {
    const s = prev.stitch
    if (!s || !s.ok || !s.chunks || !s.chunks.length) {
      log(`⛔ ${p.page}: the stitch/brief stage did not produce briefs - NOT adjudicated`)
      return Object.assign({}, prev, { results: [], blocked: true })
    }
    return parallel(s.chunks.map((c, i) => () =>
      agent(adjudicatePrompt(p, c),
            { label: `adj:${p.page}:${i + 1}`, phase: 'Adjudicate', model: 'sonnet' })))
      .then(r => Object.assign({}, prev, { results: r.filter(Boolean) }))
  },

  // 6 · merge, cp, chain dry run (0 vision, cheap)
  (prev, p) => {
    if (prev.blocked || !prev.results.length) {
      return Object.assign({}, prev, {
        merge: { ok: false, rc: [], lines: ['blocked before adjudication'], needsOwner: [] } })
    }
    return agent(mergePrompt(p, prev.results),
      { label: `merge:${p.page}`, phase: 'Merge', model: 'sonnet', effort: 'low', schema: MERGE_SCHEMA })
      .then(r => Object.assign({}, prev, { merge: r }))
  },
)

// ⛔ No silent caps: say plainly which pages did not get through.
const report = PAGES.map((p, i) => {
  const r = out[i]
  if (!r) return { page: p.page, ok: false, why: 'the page chain threw - see the phase that stopped' }
  return {
    page: p.page,
    ok: !!(r.merge && r.merge.ok),
    crops: r.crops,
    readChunks: { a: r.a, b: r.b },
    gateOk: !!r.gateOk,
    gateRc: r.gate ? r.gate.rc : [],
    repairs: r.repairs || [],
    briefChunks: r.stitch ? (r.stitch.chunks || []).length : 0,
    sites: r.stitch ? r.stitch.sites : null,
    stitchFindings: r.stitch ? r.stitch.findings : [],
    mergeLines: r.merge ? r.merge.lines : [],
    needsOwner: (r.merge && r.merge.needsOwner) || [],
  }
})
const bad = report.filter(r => !r.ok).map(r => r.page)
if (bad.length) log(`⛔ ${bad.length} page(s) did NOT reach a merge candidate: ${bad.join(', ')}`)
log(`★ ${report.length - bad.length} of ${report.length} page(s) have a candidate in _work/ and a chain DRY RUN only`)

return {
  book: BOOK,
  pages: report,
  reminder: 'Candidates are cp-ed to research/_parts/ and the chain was DRY RUN only. ' +
            'The main session rules on the seam and on every finding, then runs the chain with --apply.',
}
