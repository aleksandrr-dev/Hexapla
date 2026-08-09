# Asset defects — found, fixed, and the tools that find them

Split out of CLAUDE.md 2026-08-09.
⚠ READ THIS BEFORE TOUCHING ANY BIBLE ASSET. It records how a 75%-corrupted de_luther, a squeezed sv_karlxii, ~half the Psalter's missing titles and several markup leaks were found — and the one rule that matters: a markup regex cannot see silent corruption. Silent damage needs a REFERENCE TEXT, not a pattern.

## ⚠ ASSET DEFECTS FIXED 2026-07-15 (owner-approved; NOT yet rebuilt/shipped)

Both rewrite SHIPPED assets. `.json.bak` backups sit beside each. Next build
must include them; owner should spot-check on-device before submitting.

- **de_luther.json was 75.9% CORRUPTED and had been since v1.1.** Not markup —
  destroyed characters. It is an unproofread OCR of the Bolsinger/
  luther-bibel-1545.de digitization. Census over 4,010,960 chars of German:
  **ä = 0** (master: 11,719), ö = 1, Ä/Ö/Ü = 0. Zero ä in a four-million-char
  German Bible is impossible. 23,508 of 30,964 comparable verses damaged, all
  66 books, none below 50%. über→uber (1,553), soll→soil (1,499), König→Konig
  (1,201), Salomo→Saiomo, daß→dafi/dad/daü. **The deity litmus verse itself
  shipped broken: 1 Tim 3:16 read «Und kundlich GRAFT ist das gottselige
  Geheimnis» (groß → graft).**
  REPAIRED via tools/fix_de_luther.py from the SAME digitization's clean
  upstream — Zefania SF_2009-01-20_GER_LUTH1545 (sourceforge.net/projects/
  zefania-sharp; CrossWire ships it as GerLut1545). Since the app already
  ships this transcription, the clean upstream adds ZERO new licensing
  exposure. Litmus re-run on the master before use: 1 Tim 3:16 «GOtt ist
  offenbaret im Fleisch» PASS, Comma present, Acts 8:37 present, Rom 16:24
  present, Jn 1:1 PASS — same edition, same readings, pure character repair.
  RESULT: 25,915 verses repaired, ä 0→11,688, accented 3.56→14.14 per 1000,
  book/verse counts unchanged (66 / 31,164).
  ⚠ 78 verses deliberately NOT repaired: genuine German-native-vs-KJV-grid
  numbering offsets (all of 2. Samuel 19 is shifted by +1 — our 19:1 IS the
  master's 19:2). Repairing those by coordinate would OVERWRITE SCRIPTURE with
  the neighbouring verse. The audit agent misreported these as the ONLY issue
  and called the other 122 low-ratio verses "offsets" too — they were the
  worst-DAMAGED verses. Both errors sat in the same bucket; the discriminator
  is "does a neighbour match better?", NOT a similarity threshold and NOT
  length (2. Sam 19:7's offset pair has a length ratio of 1.06).
- **la_vulgata.json shipped 194 editorial markers in v1.4.3** (2026-07-13) as
  literal angle brackets: «Alleluja. <Aleph>Beati immaculati in via». 29
  distinct — Hebrew acrostic letters <Aleph>..<Thau> in Psalmi 118 (=119) and
  Lamentationes 1-4; Canticum speaker rubrics <Sponsa> x19, <Sponsus> x14,
  <Chorus>; <Prologus>. tools/convert_vulgate.py never stripped them.
  STRIPPED via tools/fix_vulgate_markers.py (owner chose this 2026-07-15 over
  surfacing them as headings, which needs UI work).
  ⚠ THIS DISCARDED REAL INFORMATION, reversibly: <Sponsa>/<Sponsus> identify
  WHO IS SPEAKING in Song of Songs and print Clementine editions carry them as
  rubrics. ✅ REINSTATED AS STRUCTURE 2026-07-20 (in tree, not yet shipped):
  tools/build_vul_rubrics.py extracts all 198 rubrics across 194 verses (the
  old "194 markers" figure counted verses; 4 verses carry two) from the
  clemtext source (Quasimodo.zip re-fetched, cached at Hexapla-releases/
  clemtext/) into assets/rubrics_vul.json (4.6 KB) with per-marker character
  offsets verified against the shipped verse text; Rubrics.kt loads it and
  ReaderScreen shows the labels as small italic headers above their verses
  when the primary is vul (offsets recorded for a future inline renderer;
  secondary-pane rubrics deliberately not rendered yet).
- ru_synodal.json escaped OSIS: ✅ ASSET FIXED 2026-07-16 (commit 534a43d,
  owner-verified on device) — the Иов 2:9 LXX-variant note and Иов 9:9
  constellations note were converted to {Примечание: ...} margin notes
  (the KJV {x:y} convention BibleRepo strips at parse; readers see them
  under "Translator's notes"); the stray Пс 143:15 title was removed.
  ⚠ FOLLOW-UP FIXED 2026-07-20: narrate.py's strip_ru_markup still
  targeted the OLD &lt;note&gt; form, so Иов 2+9 were NARRATED 2026-07-18
  with the note text spoken as scripture (Иов 9's leak was silent — no
  digit to trip QA). strip_ru_markup now strips brace notes like
  strip_kjv_notes; qa_narration's tail check now scales its allowance by
  the final verse's length (Есфирь 4/10 + Иов 42 end in 1.1-3.5k-char
  LXX additions — were false FAILs under the flat 60s allowance).
  PENDING: re-render ru books 17 chapters 1+8 (narrate.py --lang ru
  --book 17 --chapter N --force) AFTER the main ru render finishes —
  don't run two CosyVoice processes concurrently on the GPU.
- ⚠ **TRUNCATED CHAPTER ANNOUNCEMENTS IN THE ru RENDER (found 2026-08-04)**:
  the owner heard 1 Corinthians 4 announce itself with the number «4» cut off.
  NOT a bug in ru_ordinal_fem — «четвёртая» announcements average the LONGEST
  of chapters 1-10 across the whole set (3278 ms), so this is an isolated
  CosyVoice generation defect: the genai-pipeline-qa class where a defect
  REPLACES content instead of adding it.
  DETECTION, no listening required: a chapter's `<n>.json` first offset IS the
  length of its announcement. Compare each chapter against its OWN BOOK's
  median — book-name length dominates the announcement, so comparing across
  books produces false positives — and exclude the genuinely short ordinals
  (1-3, 5-10, 20, 30…), which are short for real reasons. 1 Cor 4 sits at
  0.72 of its book's median.
  RE-RENDER QUEUE — the confirmed one plus 8 candidates of the same shape,
  all AFTER the main render finishes. ⚠ Listed 1-based; narrate.py's
  --book/--chapter are 0-BASED, so subtract one, and pass --force:
  **1 Cor 4** (owner-confirmed) · Judges 16 · Numbers 4 · Numbers 14 ·
  Genesis 16 · Proverbs 16 · Proverbs 17 · Luke 17 · Leviticus 25.
  ⚠ The 8 are UNCONFIRMED — flagged by duration alone, nobody has listened.
  Re-rendering is cheap and idempotent, so a false positive costs a few
  minutes of GPU; afterwards check the new first offset lands near the book
  median. Worth folding this check into qa_narration.py so the next set
  catches it automatically.
- **⚠ ~HALF THE PSALTER IS MISSING ITS TITLES — ru_synodal AND cu_elizabeth.**
  Found 2026-07-15 while fixing the Psalm 144 stray title; NOT yet fixed, needs
  a source and an owner decision. Measured against the app's own Clementine
  Vulgate (same LXX psalter, kept all its titles):
      Vulgate has a title in 144 of 150 psalms
        title is its OWN verse : 46  -> CU missing 5,  SYN missing 7
        title INLINE with text : 98  -> CU missing 73, SYN missing 74
  THE RULE IS EXACT: a title that occupied its own verse SURVIVED; a title
  sharing verse 1 with content was DROPPED by the converter. Examples are not
  obscure — Ps 22 (the Shepherd Psalm) opens «Господь - Пастырь мой» with no
  «Псалом Давида.»; Ps 26 and Ps 16 likewise. The Psalm 144 title that was
  merely MISPLACED (onto 143:15, now fixed) was a survivor of the same bug.
  NOT a versification defect: the titles were inline in v1, so no verse counts
  changed — versemap/bookmarks/notes/highlights are unaffected. It is a text-
  completeness defect only.
  ⚠ The ~74 figure is HEURISTIC (per-language title-prefix matching); direction
  and scale are solid, the exact count is not. tools/ scratch analysis compared
  vul/cu/syn verse 1 across all 150.
  ✅ SYNODAL REPAIR DONE 2026-07-16 (owner-approved): 56 titles restored via
  tools/fix_ru_psalm_titles.py — title-prefix-only prepends to v1, every edit
  body-gated at ratio 1.00 against the source, verse counts unchanged (2,533).
  Vulgate census: inline-missing 74 -> 28 (residual ≈ the ~15 genuinely absent
  from both PD digitizations + census-regex blind spots). Backup:
  asset-backups/ru_synodal.json.pretitles.bak. TWO GATES CAUGHT IN DRY-RUN:
  Пс 139 skipped — its v1 IS an own-verse title and rst carries a stray extra
  «Псалом.» that would have been doubled onto it (own-verse-title guard now in
  the script); Пс 151: the 2026-07-16 "stays untitled" resolution was
  REVERSED 2026-07-20 on decisive new evidence — see the completion-pass
  entry below (the 1904 print titles it; the module's «единоборстов» was a
  typo'd COPY of that genuine title, not an editorial paraphrase).
  The Slavonic (cu_elizabeth) remains OPEN — see (c) below.
  SOURCE RESEARCH DONE 2026-07-15 (Opus agent, byte-level verification):
  (a) ru_synodal.json PROVENANCE SOLVED: it was converted from the CrossWire
      SWORD module **RusSynodal** (crosswire.org rawzip). Proven byte-level:
      the module itself carries our two escaped-markup leaks VERBATIM (the
      Ps 143:15 «&lt;title type="psalm"&gt;Хвала Давида.» and the Job 2:9
      &lt;note&gt; are literal escaped text IN THE MODULE — a module data bug);
      the converter stripped all real <title> elements (the title-dropping
      defect) and only those two escaped ones passed through. The 83-book
      canon incl. «Лаодикийцам» = SWORD Synodal versification, ditto.
  (b) RECOVERY (Synodal): module has clean <title type="psalm"> for 31
      psalms, all 31 currently missing (list in the research transcript);
      lowercase «псалом» needs normalizing to «Псалом». The ascent/hallelujah
      superscriptions the module lacks (Песнь восхождения, Аллилуия) are in
      gratis-bible/bible ru/rst.xml (same Fedosov PD digitization, titles
      inline behind a "(N:N)" prefix; en-dash vs hyphen in bodies). Union =
      verified floor of 58 recoverable titles; ~15 (incl. Аллилуия at Ps
      148-150) are absent from BOTH PD digitizations — not recoverable there.
      LICENSES QUOTED: RusSynodal.conf "DistributionLicense=Public Domain";
      rst.xml <rights> "…Sergej A. Fedosov's Slavic Bible for Windows…Public
      Domain". Repair shape: mirror fix_de_luther.py — coordinate-anchored,
      TITLE-PREFIX-ONLY prepend to v1, body-match gate
      (SequenceMatcher autojunk=False), verse counts asserted unchanged,
      backup outside assets/.
  (c) cu_elizabeth.json: PROVENANCE = CrossWire **CSlElizabeth** (verified,
      matches our asset exactly) — the module has ZERO <title> elements; our
      asset is a FAITHFUL copy of a source that never had the надписания.
      SOURCE HUNT DONE 2026-07-16 (Opus agent, verbatim-quoted evidence):
      ★ **Ponomar Project** (github.com/typiconman/ponomar,
        Ponomar/languages/cu/bible/elis/Psalm.text) is THE source: complete
        Elizabeth psalter, **135 надписания / 151 psalms** as structured
        verse-0 fields (Ps 22 «Ѱало́мъ дв҃дꙋ,», Ps 119 «Пѣ́снь степе́ней,»).
        PROVEN: our asset is a civil transliteration of EXACTLY this text
        (Ps 22:1/143:1/144:1 reduce perfectly under the asset's own
        convention). TWO GATES, both owner calls:
        (1) ORTHOGRAPHY — Ponomar is full CS (titlos, ѣ ѡ ѧ); titles need
            transliteration to civil spelling = an EDITORIAL ACT (nomina
            sacra expansion гдⷭ҇ь→Господь, terminal-ъ elision, ѣ→е etc.).
            Tractable: the missing titles are a small formulaic set — a
            hand-curated table like the project's other curated converters.
        (2) LICENSE — OWNER DECISION 2026-07-16: PROCEED WITHOUT the email,
            on the PD reasoning (1751 text PD by age; transliteration strips
            the accentuation, the only arguably-© layer; the extracted titles
            are short formulaic PD liturgical phrases). This is a deliberate,
            documented deviation from the usual ask-first pattern — owner:
            "skip the email for now. if we get feedback on it, we can act on
            it then." The draft stays at store-assets/ponomar_email_draft.txt
            in case feedback arrives. Ponomar credit in sources_text ×13:
            ✅ DONE 2026-07-16 (added during the sources_text trim).
      ⚠ PARTIAL RESTORATION DONE 2026-07-16 via tools/fix_cu_psalm_titles.py:
      **14 titles applied** — only those whose every word is attested in the
      ~2,400-verse-pair parallel corpus between Ponomar (full CS) and our
      asset (civil), the transliteration LEARNED from that corpus rather than
      hand-written (the ru_stress lesson). Gates, all passing: reliable-word
      accuracy 99.93% case-folded; hold-one-out reconstruction of the 58
      KNOWN titles = 31 exact + 26 flagged-unknown (safe) + 1 punctuation
      variance + **0 silent-wrong** (the gate that matters). Bugs the gates
      caught on the way: reverential-capitalization splits («его»/«Его»)
      disqualifying common words; Ponomar's parenthesized Alleluia titles
      losing their lead paren; NFD accent-stripping destroying й (breve) in
      suggestions.
      ✅ ALL 69 CU TITLES APPLIED (14 corpus-proven + 55 via owner-delegated
      review, 2026-07-16). The owner's review notes were RUSSIAN-SYNODAL
      renderings («Псалом Давида», «Песнь восхождения») of the Slavonic
      entries; the CU titles were kept SLAVONIC («Псалом Давиду», «Песнь
      степеней», «Аллилуиа») because the asset's own shipped text uses those
      forms (Пс 3:1 «Псалом Давиду, внегда отбегаше…» since v1) — Russian
      titles would clash with Slavonic bodies. Flagged to the owner with an
      easy override; his notes were applied as CONTENT decisions (Пс 151
      titled, proper names capitalized, ѱ→пс charmap gap fixed). Final list:
      C:/Projects/Hexapla-releases/cu_titles_final.txt. Backups:
      asset-backups/cu_elizabeth.json.{pretitles,prereview}.bak.
      SYNODAL follow-ups from the same review (tools/fix_ru_titles_owner.py):
      Пс 133 «Песнь восхождения.» — a GAP THE OWNER CAUGHT, the automated
      pass covered only 119-132. Пс 151 was briefly titled per owner
      dictation, then REVERTED when he re-delegated («go with what you think
      is right for the text»): the Synodal edition prints NO superscription
      at Ps 151 (azbyka witness, footnote only) — SYNODAL 151 STAYS
      UNTITLED while the SLAVONIC keeps its long title, because the two
      EDITIONS genuinely differ there. Per-edition fidelity, final.
      ✅ SYNODAL COMPLETION PASS 2026-07-20 (tools/fix_ru_psalm_titles2.py,
      in tree): the residual 24 titles absent from BOTH PD digitizations
      were recovered by multimodal page-reading of a genuine 1904
      Синодальная типография print (archive.org B-001-026-985-ALL /
      bibliiailiknigis00sankuoft, 7-е изд., 600ppi; full report
      research/ru_psalm_titles_completion.md) — Пс 32, 90, 92-96, 103,
      106, 113-118, 135-137, 145-150. Convention mirrors print AND asset:
      print-(parens) = LXX-supplied -> asset [brackets] (Пс 98 precedent);
      print-bare = Hebrew-attested -> bare (only Пс 137 «Давида.», whose
      MT 138 carries לדוד — the print's parens distinction is precise).
      Пс 42/70/104 print-confirmed genuinely untitled (104 diverges from
      the Vulgate's "Alleluja" — per-edition fidelity). Пс 7 was a census
      false positive (own-verse title). THE PSALTER TITLE RESTORATION IS
      NOW COMPLETE — every psalm titled or witness-confirmed untitled.
      Backup: asset-backups/ru_synodal.json.pretitles2.bak.
      ✅ Пс 151 TITLED 2026-07-20 (owner delegated the call same day,
      reversing 2026-07-16): the 1904 print titles it «(Псалом Давида на
      единоборство съ Голіаѳомъ *)» — correctly spelled, parenthesized
      under the same LXX-supplied convention as the other 24 — applied as
      «[Псалом Давида на единоборство с Голиафом.]» plus the print's own
      footnote as a {Примечание: У Евреев этого псалма нет; он переведен
      с Греческого.} brace note (on-demand translator's-note mechanism).
      The Slavonic keeps its own longer title — editions still differ in
      WORDING, and now both are faithful to their prints.
      ⚠ RU NARRATION STALENESS: the ru render passed Psalms before these
      24 titles (and before the Job 2/9 note fix) — re-render queue after
      the main ru render finishes: book 18 chapters (1-based psalms) 32,
      90, 92-96, 103, 106, 113-118, 135-137, 145-151 + book 17 chapters
      2 and 9 (--book/--chapter are 0-based in narrate.py; use --force).
      FALLBACK: my-bible.info has a complete CIVIL-script CS psalter (no
      transliteration needed) but NO stated license and murky provenance —
      strictly weaker. DEAD ENDS (verified): rusbible.ru IS the gap (drops
      unnumbered titles, keeps numbered ones — explains the 73/98 vs 5/46
      pattern exactly); Wikisource has no CS psalter transcription; azbyka/
      bible-center are publisher-© and JS-rendered; orthlib.ru is legacy
      "HIP"-encoded .rar service books. CrossWire has exactly one cu module.
- en_kjv stray `</title>` (Additions to Esther 10:4) and zh_cuv_s/t `<WAHb>` x2
  (Joshua 24:14, upstream-Traditional defect) — FIXED 2026-07-15 via
  tools/fix_remaining_markup.py, owner-approved. audit_asset_markup.py now
  reports ALL 23 ASSETS CLEAN.
- **de_luther ALIGNMENT REPAIR 2026-07-20 (tools/fix_lut_alignment.py; in
  tree, not yet shipped)**: the "lut 2 Kgs 15:39 empty slot (cosmetic)" note
  hid a defect family — the v1.1 scrape had squeezed several native-numbered
  chapters, leaving 8 empty tail slots, 78 verses one slot off their
  versemap-described positions (= fix_de_luther's 78 deliberately-skipped,
  still-OCR-damaged verses), and FIVE verses of scripture missing outright:
  2 Sam 19:1 (the "Mein Sohn Absalom!" lament), 1 Kgs 22:44, Acts 7:56
  ("I see the heavens opened"), Hag 2:22, Ps 13:7 — plus 2 Kgs 15:39 and
  Hag 1:15; Hag 2 also carried a DUPLICATE of 2:1 at 2:2. Split view paired
  all those chapters off-by-one. All repaired from the Zefania master
  (assertion-gated, whole-Bible re-scan = 0 problems, asset now exactly the
  master's 31,170 verses, zero empties; backup
  asset-backups/de_luther.json.prealign.bak; master XML cached at
  Hexapla-releases/SF_2009-01-20_GER_LUTH1545_(LUTHER 1545).xml). Num 25:19 /
  1 Chr 12:41 / Rev 12:18 empty tails were SPURIOUS for this digitization
  (it keeps those KJV-shaped; Num 25:19's Hebrew content is 25:18's tail
  clause) — slots dropped, and build_versemap.py's shared ("lut","wlc")
  table SPLIT: those runs are now wlc-only, lut gained the 2 Kgs 15:38=38-39
  split run, Ps 13 title runs now auto-emit (was silently identity = KJV
  13:1 paired with the German TITLE). versemap.json regenerated; diff
  verified lut-only (+ harmless wlc run reorder). ⚠ Existing users'
  bookmarks/notes in the 7 shifted chapters referenced wrong-by-one verses
  before; canonical-key pivot makes them correct after this ships.
- TOOLS: tools/audit_asset_markup.py scans every asset for this class of
  leakage. Run it before any release. It found 6 of 23 assets dirty.
  ⚠ A MARKUP REGEX CANNOT SEE SILENT CORRUPTION: it found 20 de_luther verses;
  the real number was 23,508 — an undercount of ~1,175x, because 13,781 verses
  differ only by stripped umlauts with no markup to match. Silent damage needs
  a REFERENCE TEXT, not a pattern.
