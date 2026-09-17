export const meta = {
  name: 'thorlaks_page',
  description: 'Transcribe Thorlaksbiblia pages: two offset crop reads, stitch, brief, adjudicate, merge candidate',
  whenToUse: 'One batch of Thorlaksbiblia (or Karl XII) page indices, from line crops to a merge candidate the main session only has to rule on. The RULED method, owner 2026-09-17 16:40.',
  phases: [
    { title: 'Plan', detail: 'count the crops on disk, cut A and B chunk plans at OFFSET boundaries' },
    { title: 'Read A', detail: 'Sonnet crop reads, LINE-level, line00 included' },
    { title: 'Read B', detail: 'independent Sonnet crop reads, boundaries offset ~7 crops' },
    { title: 'Stitch', detail: 'stitch both reads, screen them, generate the adjudication briefs (0 vision)' },
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
// ⚠ STILL OWED, and deliberately NOT faked here: item 3 of the ruling, the
//   2-of-3 MAJORITY VOTE. It needs a third blind read C and a `sites()` in
//   `thorlaks_adjudicate_merge.py` that takes THREE reads and resolves every
//   2-of-3 site in plain code. Until that tool change exists this script runs
//   the two-read diff, which is the pipeline the tools actually support.
//   ⛔ Do not add a read C here before the tool can consume it - a third read
//   nobody diffs is spend with no instrument behind it.
//
// USAGE (args is a JSON value, never a JSON string):
//   { book: "Luke", kit: "luke_kit2", data: "C:/Projects/Hexapla-releases",
//     tools: "C:/Projects/Hexapla/tools", date: "2026-09-17",
//     pages: [ { page: "p63", chapter: 10, firstVerse: 17 }, ... ] }
// `chapter`/`firstVerse` = the chapter open at the page HEAD and the first
// PRINTED numeral expected on it. ⚠ A verse continued from the previous page
// is firstVerse - 1, and the stitcher handles that itself.
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
7. ⛔ **Do not consult any other text of this book, printed or electronic.** A
   reading that comes from knowing the verse is not evidence about this page.
8. A hedge is a correct answer. \`[?]\` after an uncertain word; \`[illegible]\`
   where there is nothing to read.
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
${CONVENTIONS}
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

Then return ONLY the absolute path of the file you wrote. ⛔ No summary, no
transcription in your reply - the file is the deliverable.`
}

function pad(n) { return (n < 10 ? '0' : '') + n }

function scriptsPrompt(page, plan) {
  const lower = BOOK.toLowerCase()
  return `Run these scripts and return their results. ⛔ This is a 0-VISION task:
do NOT open any image, and do NOT \`cat\` a read file into your reply.

Working directory: \`${DATA}\` (⚠ NOT a git repo). Every tool by ABSOLUTE path.
⚠ \`PYTHONIOENCODING=utf-8\` on every one of them - they print ø/þ.

1. Stitch read A:
   ${PY} ${TOOLS}/thorlaks_crop_read_stitch.py --book ${BOOK} --page ${page.page} \\
       --chapter ${page.chapter} --first-verse ${page.firstVerse} \\
       --out _work/${lower}_${page.page}_readA_${DATE}.md
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
    { label: `plan:${p.page}`, phase: 'Plan', effort: 'low', schema: PLAN_SCHEMA }),

  // 2 · read A - chunks cut from line00
  (plan, p) => {
    if (!plan || plan.crops < 1) {
      log(`⛔ ${p.page}: no crops on disk (${plan ? plan.crops : 'null'}) - prep this page first`)
      throw new Error(`${p.page} has no crops`)
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
    const cuts = chunkPlan(prev.crops, OFFSET)
    return parallel(cuts.map(([f, t], i) => () =>
      agent(cropReadPrompt(p, i + 1, f, t, 'B'),
            { label: `readB:${p.page}:${i + 1}`, phase: 'Read B', model: 'sonnet' })))
      .then(r => Object.assign({}, prev, { b: r.filter(Boolean).length, bcuts: cuts.length }))
  },

  // 4 · stitch both, screen both, brief (0 vision, cheap)
  (prev, p) => agent(scriptsPrompt(p, prev),
    { label: `stitch:${p.page}`, phase: 'Stitch', effort: 'low', schema: CHUNKS_SCHEMA })
    .then(r => Object.assign({}, prev, { stitch: r })),

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
      { label: `merge:${p.page}`, phase: 'Merge', effort: 'low', schema: MERGE_SCHEMA })
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
