# Translations — research verdicts, integration records, watch list

## ⚠ ACTIVE WORK — read these first
· **Russian Strong's**: owner approved shipping under risk-acceptance
  2026-08-09; source downloaded and the Dvoretsky gate PASSED. Converter
  and app wiring remain — `research/russian_strongs_status.md`.
· **Cover art gaps**: Weigel's *Biblia Ectypa* (1695, 839 plates, one per
  epistle by design) and Merian's *Icones Biblicae* (1625-30, Part III
  covers the Apocrypha) fill what Doré and Schnorr never drew. Both PD,
  both on archive.org/Wikimedia. Style caveat: 17th-c. baroque against
  19th-c. romantic — monochrome line art either way, but not seamless.

Split out of CLAUDE.md 2026-08-09: it was 612 lines of material needed when ADDING a translation, not every session.
⚠ Every ⚠ in here is load-bearing — licence gates, traps, and dead ends that cost real time to establish. Nothing here was deleted in the split.

- **Interlinear localization (owner-approved 2026-07-12)**:
  (a) ~~1.4.2 item~~ DONE 2026-07-12, in tree for 1.4.2 (code 9):
  grammar labels in Interlinear.kt decoders moved to string
  resources — 136 morph_* strings ×12 locales, terminology table
  curated in tools/localize_morphology.py (idempotent injector;
  Russian seminary terms, Cyrillic binyanim; French Hebrew
  accompli/inaccompli; CBOL vocabulary for zh, katakana stems for
  ja; Latin binyanim kept for Latin-script locales + zh).
  decode() now takes Context. Verified: Python port of old vs new
  decoders over every distinct code in both assets (1055 Greek +
  3454 Hebrew) — Greek byte-identical, Hebrew differs only in the
  intended Tn/Ti/Tr enrichment («negative» → «negative particle»,
  225 codes). Lint clean (47 warnings = pre-change baseline).
  (b) WATCH LIST — localized Strong's LEXICONS (Russian first):
  the definitions in strongs_lexicon.json are English (Open
  Scriptures). Russian Strong's translations circulate in
  e-Sword/MyBible modules but each translation carries its
  translator's ©, though the 1890 base is PD. RESEARCHED 2026-07-12,
  verdict = permission-email path: the de-facto standard text is the
  BibleQuote lineage (github.com/BibleQuote/BibleQuote-Modules
  Strong.zip, gloss-only, complete H1-H8674 + Greek, quality ideal
  for tap-a-word, 0.46 MB deflated) — NO license anywhere; MyBible's
  module credits it «с разрешения [имя удалено]» (personal permission).
  EMAIL the BibleQuote maintainers (biblequote.org contact form,
  jesuschrist.ru) — draft at
  store-assets/biblequote_email_draft.txt: ask (1) permission for
  the gloss-only files in a free attributed app, (2) PROVENANCE —
  is it the 1998 Bob Jones University symphony key? (residual-rights
  question). SENT by owner 2026-07-12 — awaiting reply.
  ⚠ READ THE REPLY WITH THIS IN MIND (audit 2026-07-15): one
  (low-quality, UNVERIFIED) Russian source claims «[the maintainer] не
  является владельцем прав на публикацию словаря Стронга» — if that maintainer is
  NOT the rights holder, their permission does not clear the rights and
  a "yes" is not legally load-bearing. Question (2) PROVENANCE
  therefore matters MORE than question (1) permission. Audit
  confirmed BJU's 1998 «Библейская симфония с ключом к еврейским и
  греческим словам» is real (ru.wikipedia, Конкорданция Стронга) BUT
  it is a SYMPHONY/KEY (Strong's numbers → Synodal word occurrences)
  — a DIFFERENT copyrightable layer from a gloss-only H1-H8674
  dictionary. Whether Strong.zip's glosses descend from it remains
  UNVERIFIED. Repo re-checked 2026-07-15: still license: None, no
  LICENSE file, Strong.zip = 611,637 bytes, last push 2022-02-25.
  HARD GATE: MyBible/ph4 builds embed Dvoretsky's 1958
  dictionary in 5,113 Greek entries — use ONLY the pristine
  BibleQuote greek/hebrew.htm (zero Dvoretsky, verified — the gate is
  real: Dvoretsky-merged files circulate under BibleQuote-looking
  names, e.g. a «Греческий лексикон Стронга - словарь Дворецкого»
  module). ⚠ DATE CORRECTED 2026-07-15: the old note read «© until
  ~2046» — WRONG, and wrong in the UNSAFE direction. Dvoretsky died
  3 Jan 1979 (not 1963); ГК РФ ст. 1281 = life+70 counted from 1 Jan
  of the following year → © until end of 2049, PD 1 Jan 2050. If the
  WWII +4 extension applies (ru.wikipedia's biography is explicitly
  incomplete on his wartime activity — UNVERIFIED) → end of 2053.
  Where "2046" came from is unknown. Do not unblock before 2050.
  Zhuromsky fallback is CC BY-NC-ND — BOTH the NC and the ND
  disqualify (re-verified 2026-07-15 at igr.bible, his own site:
  «© 2026, Виктор Р. Журомский. Все права защищены лицензией
  CC BY-NC-ND 4.0» — actively asserted; earlier note cited only the
  ND) + reputational flags — avoid. Tsygankov/azbyka = publisher ©
  (re-verified 2026-07-15: azbyka's own record, «сост. Цыганков
  Ю. А.», СПб.: Библия для всех, 2005, ISBN 5-7454-0933-9; the
  1890 Strong's base is PD but Tsygankov's compilation+commentary is
  a modern authored work), dead end. Architecture
  when a clean source lands: per-locale lexicon file keyed by the
  same H/G ids, chosen by UI locale, English fallback; same model
  later for DE/ES/PT.
- **PERSIAN MARTYN NT — INTEGRATED IN TREE 2026-07-20** ("mrt",
  fa_martyn.json, 33rd translation / 28th language, «عهد جدید — ترجمهٔ
  هنری مارتین، ۱۸۷۶ (FA)», defaultPrimaryId fa/prs/tg->mrt, NT-only like
  grc/arm, NO sources_text [PD], NO versemap entries [exact KJV grid]):
  THE FIRST TRANSLATION PRODUCED BY THE PROJECT'S OWN MULTIMODAL
  TRANSCRIPTION — 7,957 verses read page-by-page from the archive.org
  scan of the 1876 BFBS reprint by ~16 Sonnet agent-chunks in one day,
  litmus 7/7 TR (incl. Comma, Acts 8:37, Rom 16:24, Jn 5:4 [the
  anti-Bruce marker], Acts 20:28 church-of-GOD, Pericope Adulterae,
  Mark 16:9-20). tools/build_martyn_nt.py = the converter: a strict
  KJV-grid state machine over the reports' verse markers with layered
  audits (per-chapter 1..N, n-gram dittography, ASCII-leak, length-ratio
  vs KJV) that caught what agent self-reports missed. Curated: Acts
  21:21b-32a supplied from the 1837 FIRST PRINTING (folio 295 of the
  1876 scan is a master-scan duplicate; per-verse {یادداشت} witness
  notes); Heb 6:14's 1876-only triple «منتشر» corrected to the 1837's
  doubled form; Jn 21:11 kept as printed (BOTH witnesses read 253, not
  153 — noted); Mark 5:28/29 print-merge resegmented; missing-numeral
  splits at Mk 6:15, Lk 23:17, Rom 15:33, Rev 22:9; five suspect sites
  REPLACED from a page-level re-verify pass (martyn_spot_reverify.md —
  the print was innocent everywhere, all flags were chunk-pass slips);
  ي/ك→ی/ک normalized (mixed transcriber IMEs). All reports in
  Hexapla-releases/research/martyn_*.md. GLEN OT (1856, HathiTrust
  njp.32101076512563, feasibility CONFIRMED same-easy-tier) = the next
  campaign; see SESSION_HANDOFF for access/harvest notes.
  ✅ **OWNER DECISION 2026-08-08 — THE GLEN OT MERGES INTO THIS ASSET.** One
  Persian Bible, not an OT-only plus an NT-only entry: BFBS bound Glen's OT
  with Martyn's NT and that is the Bible a Persian reader recognises. His
  condition: label it correctly, naming BOTH translators and BOTH dates
  (different translators, decades and source languages — Glen from the
  Hebrew, Martyn from the Greek). Proposed, pending his confirmation:
  «کتاب مقدس — عهد عتیق: ولیم گلن، ۱۸۵۶؛ عهد جدید: هنری مارتین، ۱۸۷۶ (FA)»
  («ولیم گلن» = the 1856 title page's own spelling). The present
  «عهد جدید — …» label MUST change once the OT slots are populated.
  **KEEP THE ID `"mrt"`** — it is an opaque storage key, invisible to users,
  so renaming it to something honest buys nothing but tidiness in a file only
  we read. Mechanism, verified in code rather than assumed: the id is
  persisted in DataStore (Store.kt `"primary"`/`"secondary"`) and every
  Bookmark carries its own `translationId`, so a rename orphans a user's
  selection and bookmarks silently — no error, nothing to debug. ⚠ Owner's
  correction 2026-08-08, and he is right: that POPULATION is near nil today
  (Persian shipped only in 1.6.3, Play is still closed testing), so this is a
  no-upside argument, NOT a scary one. Do not cite it as if real users were
  at stake. fa_martyn.json's books 0-38 hold NO chapters at all (verified
  2026-08-08), so the OT slots are being FILLED, not overwritten.
  ✅ **OWNER DECISION 2026-08-08 — DEFECTIVE VERSE NUMERALS ARE RECORDED AS
  PRINTED, in the marker stream itself** ("decide based on the original work
  and faithfulness to the source"). A normalized marker destroys the evidence
  INVISIBLY: the chapter then passes the 1..N check as COMPLETE and nothing
  downstream can see that a defect existed. As-printed makes it scan DEFECT,
  which is how the converter finds the site. The ADDRESSING is the converter's
  job — build_glen_ot.py carries a curated defect table mapping printed glyph
  -> positional slot, so a bare «۱» mid-chapter cannot restart the verse
  counter. The chunk report is a WITNESS DOCUMENT; the asset is an ADDRESSED
  TEXT; only the second owes anything to the KJV grid.
  ⚠ The clash occurred INSIDE one chunk (glen_ezekiel_33-48.md normalized at
  34:18 while recording as-printed at 35:7/8 — repaired 2026-08-08, backup
  .prenormfix.bak), so before conversion EVERY chunk report must be re-scanned
  against its own flag prose. Silently-normalized sites are unrecoverable from
  the corpus and need the page re-read.
  Full step order for conversion is in research/GLEN_RESUME_NOW.md.
- **Candidate research pipeline (2026-07-16)**: tools/TRANSLATION_RESEARCH.md
  is a self-contained brief (litmus table + license gates + report format)
  for agent research passes; verdict reports land in
  C:/Projects/Hexapla-releases/research/. Ukrainian Kulish excluded by owner.
  Dutch — INTEGRATED IN TREE 2026-07-16 for the next release ("svv",
  nl_staten.json, 23rd translation / 18th language): Statenvertaling
  1637 in the 1888 Jongbloed spelling, from eBible.org nld_usfm.zip
  ("De Heilige Schrift 1917", explicitly PD). LITMUS 7/7 verified on the
  converted asset (God is geopenbaard in het vlees; Comma; Acts 8:37;
  Rom 16:24; Jozef at Lk 2:33; Gemeente Gods; Die in den hemel is).
  Converter tools/convert_statenvertaling.py: perfect KJV grid — 31,102
  verses exactly, zero empty/extra slots, NO versemap entries needed
  (identity fallback); 1,397 embedded "(N:N)" native-reference markers
  stripped under a census-match assertion (all other digit-parens are
  real parenthesized passages — do NOT widen that regex). Book names are
  the source's own Dutch (incl. "Richtere" for Judges — edition-faithful).
  sources_text ×13 updated; defaultPrimaryId nl->svv. ⚠ APOCRYPHA HELD
  BACK deliberately: the 1637 included them (with warning preface) but
  the only machine-readable carriers are CrossWire DutSVV (proven psalm
  title-squeeze verse-merging — the sv_karlxii defect class) and
  Isidore-Guild's CC0 module (its own README: apocrypha "not ready for
  use"). Follow-up path documented in the research report §6. The
  Isidore-Guild CC0 base module (Strong's-tagged, kanttekeningen) is a
  future Dutch-interlinear lead — needs an encoding audit first.
  Arabic — INTEGRATED IN TREE 2026-07-16 ("vd", ar_vandyck.json, 24th
  translation / 19th language): Smith-Van Dyck 1865 from eBible.org
  arb-vd (explicitly PD; their catalog marks two OTHER Arabic Bibles ©,
  so the label is deliberate). LITMUS 7/7 verified on the converted
  asset by direct inspection («ٱللهُ ظَهَرَ فِي ٱلْجَسَدِ», Comma with
  Father/Word/Holy Spirit, Acts 8:37, Rom 16:24, Joseph, church of God,
  who-is-in-heaven). Converter tools/convert_vandyck.py: 120 \d psalm
  superscriptions PREPENDED inline (KJV convention; 4 psalms carry
  TWO-line titles — concatenated, the overwrite bug was caught by a
  census-vs-prepend count mismatch); \qa Ps-119 acrostic letters dropped
  (la_vulgata precedent); 31,104 verses = KJV grid + exactly 2
  text-verified native splits, curated in versemap (1 Tim 6:21->21+22
  grace-benediction; 3 Jn 14/15). defaultPrimaryId ar->vd. NO
  sources_text entry (PD policy). ⚠ OPEN QUESTION tracked: vocalization
  (tashkeel) lineage — CrossWire's AraSVD module is NC because ITS
  tashkeel came from Arabic Bible Outreach Ministry; eBible's PD
  declaration trusted (owner decision 2026-07-16), provenance email
  drafted at store-assets/ebible_arabic_email_draft.txt for the owner
  to send. Two Door43 orgs republish the byte-identical text CC BY-SA.
  ✉ ANSWERED 2026-07-20 by the eBible maintainer — honest reading:
  the provenance question is STILL OPEN, not resolved. He believes he
  got arb-vd from the **Digital Bible Society**, treated the text as PD
  by age, "didn't think to inquire about vocalizations separately", and
  has had no objections in all the years he has hosted it. That is a
  named upstream + absence of complaint — NOT an account of where the
  tashkeel layer came from. The practical position IS stronger (extra
  link in the chain of custody, years unchallenged, Door43 CC BY-SA
  fallback).
  ✅ **CLOSED BY OWNER DECISION 2026-07-20: risk accepted — ship as is.**
  His reasoning: years of unchallenged hosting is good enough evidence
  in practice, and if a rights claim ever surfaces we adjust then. Same
  documented-deviation pattern as the Ponomar call (act now, respond to
  feedback if it arrives). ⚠ For any future session: this is a RISK
  ACCEPTANCE, not a provenance finding — the tashkeel's origin remains
  unestablished, so do not cite this entry as proof the vocalization is
  PD. If contact ever comes, the fallbacks are (a) the Door43 CC BY-SA
  republications of the byte-identical text, (b) asking the Digital
  Bible Society directly, (c) an unvocalized edition. No further action
  needed unless that happens; the ebible_arabic thread is closed.
  ⚠ TAMIL PSALM TITLES REPAIRED 2026-07-16: convert_tamil_irv.py had
  DROPPED all 137 \d superscriptions since integration (its comment
  falsely claimed the KJV asset drops titles too) — found while writing
  the Arabic converter. Same defect class as the ru/cu psalter repair.
  Converter fixed (prepend, two-line-title-safe), asset REGENERATED from
  tam2017; diff-proven: exactly 137 changed verses, all Psalms, old text
  a strict suffix of new, everything else byte-identical (litmus
  unchanged). Backup: asset-backups/ta_irv.json.pretitles.bak.
  YLT + Vamvas — INTEGRATED IN TREE 2026-07-16 (owner delegated the
  add decision; both were mechanical):
    "ylt" en_ylt.json «Young's Literal Translation, 1898 (EN)» — 6th
    English; scrollmapper source (= CrossWire compile, PD ×4 sources),
    convert_scrollmapper.py unmodified, EXACT 31,102 KJV grid (zero
    mismatches/empties verified), litmus 7/7 + identity quirks («In the
    beginning of God's preparing», Jehovah). No versemap entries.
    "vam" el_vamvas.json «Η Αγία Γραφή — Βάμβας, 1850 (EL)» — the 25th
    translation / 20th language; modern-Greek companion to grc (Synodal:
    Slavonic :: Vamvas: Byzantine). CrossWire GreVamvas via scrollmapper
    (byte-identical, PD .conf), exact KJV grid incl. 3 Jn 14 + KJV-shaped
    Rev 12 (zero mismatches/empties), litmus 7/7 by inspection, monotonic
    (vs grc's polytonic — deliberate), psalm titles inline in «» (kept,
    edition-authentic). Book names were ENGLISH in the source (the v1
    de_luther defect class) — Greek names curated in
    tools/fix_vamvas_book_names.py (monotonic mirror of grc's style;
    RE-RUN it after any regeneration). defaultPrimaryId el->vam.
    Neither gets sources_text (PD policy). No UI locales for nl/ar/el
    yet — translations only; Play listings for those languages = release
    prep TODO if desired.
  Research verdicts (reports in Hexapla-releases/research/), the
  dedicated-session integration QUEUE — all textually approved by the
  owner's delegation 2026-07-16, roughly by effort:
    1. ~~Biblia 1776 (fi)~~ INTEGRATED IN TREE 2026-07-16 ("fi76",
       fi_biblia1776.json, 26th translation / 21st language, litmus 7/7
       on the asset): scrollmapper FinBiblia (= CrossWire compile, PD);
       tools/convert_biblia1776.py strips the 229 "(H n:m)" apparatus
       fragments (census-asserted, exactly 1 Sam 22/Job 91/Ps 116) and
       BACKFILLS the module's dropped 1 Sam 23:29 with the same
       digitization's own text recovered from finbible.fi via the
       Wayback Machine (kooste page, snapshot 20210226133437 — «Ja David
       meni sieltä ylös ja asui EnGedin linnoissa», asserted against the
       "[]" placeholder so an upstream fix can't be clobbered). Finnish
       book names curated in the converter. Apocrypha excluded (5 of 17
       books empty in the module). versemap: 3 Jn + Rev 12:18 tails.
       defaultPrimaryId fi->fi76.
    2. ~~Gdańska (pl)~~ INTEGRATED IN TREE 2026-07-16 ("gda",
       pl_gdanska.json, 27th translation / 22nd language, litmus 6/7 —
       Lk 2:33 "ojciec", the accepted Luther-class reading):
       tools/convert_gdanska.py, the most forensic converter yet. poland
       .xml (OSIS, PD) primary + CrossWire module (PD) for repairs, both
       the same 1881-lineage wording. Handled: the div after 2 Kgs is a
       2Chr/1Chr per-chapter UNION (2 Chr shadows 1 Chr at shared
       coordinates) — 2 Chr taken from the next (complete) div, 1 Chr
       assembled from the trailing fragment (chs 1-15; it cuts MID-VERSE
       at 16:5) + module (ch 16+), cross-verified against 114 surviving
       poland overflow witnesses at ratio ≥0.9 plus byte-equal boundary
       verses; the module's OWN 1 Chr 7 squeeze defect (empty 7:40,
       shifted content) dodged by taking ch 7 from the fragment. FOUR
       proven content DROPS repaired by whole-chapter module overrides
       (Deut 5 [KJV v22 missing], Ps 105 [v15 "Touch not mine anointed"],
       Ps 107 [KJV 28-29 missing + 30/31 swapped], Ezek 17 [v1 missing])
       — drops distinguished from native merges by module-alignment
       ratio (1.0 = native merge -> versemap; low = drop -> repair).
       Ps 42's gapped verse ids dense-repacked. 1,335 inline "N.N"
       native markers stripped (census); 8 stray "&gt;" entities
       dropped. 14 native-divergent chapters curated in versemap
       (Ps 51/52/54/60 superscriptions as own verse 1, like Synodal;
       6 text-verified merges; Lev 24/1 Sam 20 splits; Num 29/30 seam).
       Gdańska-tradition book names (Żydów, Jakób, 1 Mojżeszowa).
       defaultPrimaryId pl->gda. ⚠ UBG (modernized Gdańska) BLOCKED
       twice over: eBible says CC BY-ND, CrossWire says NC — never use.
    3. ~~Karadžić Serbian~~ INTEGRATED IN TREE 2026-07-17 ("srb",
       sr_karadzic.json, 28th translation / 23rd language, litmus 6/7 —
       Acts 20:28 «crkvu Gospoda i Boga» = the conflate ALREADY SHIPPED
       in cu/syn): eBible srp1865 (LATIN script, ekavian,
       Redistributable=True, PD). tools/convert_serbian.py: 126 \d psalm
       titles prepended; ⚠ eBible's KJV-slot seam duplicates carry
       MODERN-Serbian paraphrases (not 1865 wording) — 6 slots replaced
       with the native slot's authentic text (Num 12:16, 29:40, 1 Sam
       23:29, Job 38:39-41); 17 native-divergent chapters curated in
       versemap incl. the Luther-arrangement Job reflow (srp 39 = KJV
       38:39-40:5 etc., every boundary text-verified). Book names from
       \toc2 («1. Mojsijeva», «Psalmi»). defaultPrimaryId sr/bs/hr->srb.
       UPGRADE PATHS documented: ★ srp1868 (Cyrillic ekavian) is
       **UNBLOCKED 2026-07-20** — the eBible maintainer replied that
       both Serbian entries are now Redistributable=True, PD by age, and
       I VERIFIED it in the live catalog myself (ebible.org/Scriptures/
       translations.csv: srp1868 «Свето писмо или Библија Превод
       Даничић-Караџић», Cyrillic, Redistributable=True, Copyright=
       "public domain"; srp1865 likewise). ⚠ OWNER DECISION PENDING on
       SHAPE — recommendation: ADD srp1868 as a second-script Serbian
       (zh Hans/Hant precedent) rather than replacing srb, with
       defaultPrimaryId sr->Cyrillic and bs/hr staying on the Latin
       1865; Cyrillic is the script Karadžić's own alphabet reform was
       about, so it is the more edition-authentic face of this
       translation, while the Latin still serves the digraphic/Croatian
       readership. ⚠ DO NOT assume convert_serbian.py transfers: the
       1865 needed 6 seam-slot replacements (eBible's KJV-slot
       duplicates carried MODERN paraphrases) and 17 curated chapters
       incl. the Luther-arrangement Job reflow — the 1868 needs its own
       structural audit before any versemap reuse.
       (Historic note, now superseded: this was) CrossWire SrKDIjekav (Cyrillic, Karadžić's authentic
       ijekavian, PD) surveyed 2026-07-17 — 94 divergent chapters (whole
       Psalter native-numbered with vacuous trailing empty slots, its
       own Job reflow) — integrable later as a second-script Serbian
       (zh two-script precedent).
    4. ~~Károli (hu)~~ INTEGRATED IN TREE 2026-07-17 ("kar",
       hu_karoli.json, 29th translation / 24th language, litmus 7/7 on
       the asset): krisek/HunKar RAW OSIS (PD; NEVER the compiled
       module — it pads 44 fake verses and blobs Job 41).
       tools/convert_karoli.py patches the raw OSIS's 3 genuine gaps
       (Jn 21:1, Acts 12:6, Acts 15:18) from the gratis-bible hun.xml
       witness — which DOES have them (the report's uncertainty
       resolved); its degraded Latin-1 õ/û normalized to ő/ű; witness
       lineage cross-checked at ratio 0.994. NATIVE Calvin numbering
       kept: 62 title-psalms handled by the mechanical
       psalm_title_runs engine; 176 versemap runs total, curated
       seam-by-seam with text verified — Eccl is a book-long cascade
       of 5 shifts (KJV 1:18=kar 2:1, 8:16-17=kar 9:1-2, 10:1-3=kar
       9:21-23, 11:9-10=kar 12:1-2), Isa 2:22=kar 3:1 + 4:1=kar 3:28,
       Dan 4:1-3=kar 3:31-33, Hos 2:1=kar 1:12 + 13:16=kar 14:1,
       Lk 23:56 split, Jn 1:38 split, Job = Luther arrangement except
       ch41 identity, plus the usual Exod/Prov/Num/Sam/Kgs seams.
       defaultPrimaryId hu->kar.
    5. ~~Kralická (cs)~~ INTEGRATED IN TREE 2026-07-17 ("bkr",
       cs_kralicka.json, 30th translation / 25th language, litmus 6/7 —
       Lk 2:33 «Otec», the accepted class): eBible ces1613 (PD,
       PGP-signed), the cleanest USFM in the project (7 marker types).
       tools/convert_kralicka.py keeps native numbering; 62 title-
       psalms mechanical; 29 curated chapters ALL text-verified in
       build_versemap.py — notable: Exod 2:11+12 merge (slaying clause
       verified in the tail), Job keeps the lion verses IN ch 38
       (KJV 40:1-5 = bkr 39:31-35, unlike Luther/Serbian), Eccl
       straddles KJV 8:1 across bkr 7:30+8:1, Haggai 1:15=2:1 Hebrew
       seam, John 1:38 split (same as Károli). Book names from toc2
       («1 Mojžíšova», «Žalmy»). defaultPrimaryId cs+sk->bkr (the
       Kralická was historically the Slovak Protestant Bible).
       QUEUE (owner 2026-07-17): next Latvian 1689 (the CC BY-SA
       original-orthography source), then Western Armenian NT 1853;
       Georgian proceeds when TITUS permission arrives (draft ready).
  BLOCKED: Tsarigrad Bulgarian 1871 — litmus 7/7 but the ONLY true-1871
  digitization (CrossWire BulCarigradNT, NT-only) is "Permission granted
  to CrossWire" by name; permission email drafted (BG+EN) at
  store-assets/tsarigrad_email_draft.txt (contact from the .conf:
  the module's named contact). BulVeren claims 1871 but FAILS 3/7 (CT pattern) +
  NC; bibliata/beblia "Tsarigrad" is actively © despite find.bible
  calling it PD (aggregator-mislabel trap — remember for future
  candidates). No 1871 OT digitization exists anywhere.
  SECOND WAVE verdicts (2026-07-17, reports in Hexapla-releases/research/):
    ~~Latvian Glück~~ INTEGRATED IN TREE 2026-07-17 ("glk",
      lv_gluck.json, 32nd translation / 27th language, litmus 7/7 on
      the asset — Joseph at Lk 2:33!, «Deews irr parahdihts Meeẜâ»):
      the ORIGINAL 1685/1689 orthography from the SENIE/CLARIN-LV
      corpus (CC BY-SA 4.0 — attribution added to sources_text ×13),
      per the oldest-faithful-spelling precedent. Full OT+NT structural
      survey + seam-reading (convert_gluck.py's docstring = the map):
      1 Chr = THIRTY native chapters (KJV 4 split at the Simeonites
      with print numbering continuing 24-44 across the seam; 6-30 =
      KJV 5-29), Habakkuk = FOUR (split at 2:4/5), Job = Luther
      arrangement, Eccl Hebrew boundaries at 4/5 + 6/7, Isa 53:2 split,
      Ezek 5:9 = genuine print omission (versemap tv0>tv1), four
      inline-marker merges split at their own printed anchors
      (1 Chr 6:25 «26,», 12:3 «..4.», 12:6 «..7.», 2 Chr 32:19 «20.»),
      17 print-label typos position-repaired (incl. the TRUE{PRINTED}
      correction notation + dotless labels), 215 in-text corrections +
      463 footnote anchors cleaned (the @-code stripper needed a DEPTH
      COUNTER — footnotes nest {corrections} and a regex leaks tails).
      206 versemap runs incl. the 26-run 1 Chr chapter map. Psalms
      mechanical. defaultPrimaryId lv->glk. Apokr1689 (13 books, same
      license) NOT converted yet — versification unassessed, follow-up.
      The old note below records the original source choice:
    Latvian Glück — was SHIP-CANDIDATE 7/7, OWNER CHOICE between sources:
      original 1685/1689 orthography (University of Latvia SENIE/
      CLARIN-LV corpus, explicit CC BY-SA 4.0, incl. 13-book apocrypha;
      needs an orthography-era converter + 4 unresolved NT chapter
      diffs + OT not yet verse-diffed) vs CrossWire LvGluck8 (1898
      modernized spelling, EXACT KJV grid 0/1189, but its PD claim has
      an unresolved tension with its source site's rights footer).
      ⚠ TRAP CONFIRMED: the plain "Latvian" module/gratis lv = a modern
      revision that FAILS the litmus (1 Tim 3:16 "Tas", Lk 2:33
      "father") — never use it.
    Armenian — TWO tracks: classical Zohrab — TITUS PERMISSION GRANTED
      2026-07-20 (TITUS; credit + app-free conditions, same grant as
      the Georgian Bakar) and OWNER-DECIDED 2026-07-20: **OT ONLY** —
      the Zohrab NT authentically lacks the Comma (5th-c. version,
      not a CT edit), but shipping the app's first Comma-less 1 Jn 5:7
      is a doctrinal-boundary call the owner resolved by scoping to
      the OT, which raises none of the deviations and completes the
      Armenian pair (arm 1853 = NT-only, litmus 7/7). Full-Zohrab-
      with-note remains a possible later decision. (Litmus record:
      Vulgate-family readings incl. «որ» at 1 Tim 3:16, no Comma,
      LXX psalm numbering, 9-book deuterocanon.)
      ★ ~~Western Armenian NT 1853~~ INTEGRATED IN TREE 2026-07-17
      ("arm", hy_west1853.json, 31st translation / 26th language,
      litmus 7/7 on the asset). ⚠ The module's "exact KJV grid" claim
      was FALSE — a force-fit hiding: 10 squeeze-empty tails, one
      chapter-boundary fusion (native Mk 8:39 = KJV 9:1, restored by a
      verified split), 5 self-duplicated verses (deduped), and TWO
      verses ABSENT outright (2 Cor 2:1, 6:1 — patched with the 1853's
      own wording from the WARMB digitization; an archive.org scan of
      the print exists for deeper provenance if wanted). All native
      merges seam-read against the KJV and curated in versemap
      (convert_armwestern.py's docstring = the full map; 7,950 verses =
      KJV 7,957 minus exactly the 7 net merges). OPEN OBSERVATION: the
      module's language reads more modernized than the 1853's classic
      register («Որովհետեւ» vs the print's «Վասն զի») — its true
      edition lineage deserves a future look; the label follows the
      module's own 1853 claim. defaultPrimaryId hy->arm.
      ArmEastern is PD but only ~21% complete — blocked.
    Georgian — OWNER-DECISION: the ONLY verse-structured source
      anywhere is TITUS's 1743 Moscow (Bakar) Bible (litmus mostly
      TR-consistent; Comma present but 7/8 swapped; Acts 20:28 "Lord
      God" conflate; LXX psalter, pre-1868 orthography incl. archaic
      letters, 3 Macc in canon) — permission-required.
      ⚠ ONE EMAIL COVERS BOTH: store-assets/titus_email_draft.txt asks
      TITUS (Uni Frankfurt; contact in the local titus_email_draft.txt) for the Zohrab AND
      the Bakar. eBible/CrossWire/gratis/scrollmapper have ZERO
      Armenian-classical or Georgian entries (verified).
    Lithuanian — BLOCKED (license): the 1735 Bible has NO machine-
      readable digitization anywhere (exhaustive hunt). Two gated
      witnesses found: LKI seniejirastai.lki.lt diplomatic
      transcriptions of Bitneris 1701 NT (litmus 6/7, Lk 2:33
      Luther-class) + Ruigys 1727 NT — "all rights reserved"; and
      Vilnius University's Chylinski 1657-60 NT (litmus 7/7 CLEAN,
      Joseph present!) — "scholarly and educational purposes" only.
      Permission drafts: store-assets/lithuanian_emails_draft.txt.
    Estonian — BLOCKED (permission): the 1739 Piibel text itself is a
      CLEAN 7/7 (Comma intact, Joseph, Jn 3:13 clause) via EKI's
      academic corpus (arhiiv.eki.ee/piibel) + piibel.net mirror, but
      NO redistribution terms stated anywhere — email draft at
      store-assets/eki_estonian_email_draft.txt. ⚠ TRAP CONFIRMED:
      CrossWire's "Est" module (+ scrollmapper re-export) is the 1968
      revision — FAILS 3/7 (no Comma, no Jn 3:13 clause, "father") and
      its .conf says "Copyright status unknown" — never mistake it for
      the 1739. Canon incl. apocrypha; continental versification
      (title-psalms own verse, 3 Jn 15, Rev 12:18).
  Welsh Morgan — DECLINED for now (2026-07-16, via the owner's
  delegation): the ONLY live source is Welsh Wikisource's «Beibl (1620)»
  (CC BY-SA, litmus 7/7, KJV grid, full canon + apocrypha) but just
  14.2% of its 1,198 scan pages are proofread and spot-checks found real
  OCR corruption in the rest — the de_luther lesson says a mostly
  unproofread OCR source ships silent damage. WATCH LIST: re-check the
  proofread percentage yearly; template when ready = build_meiji_nt.py
  (Wikisource scrape). No CrossWire/eBible/gratis/scrollmapper Morgan
  exists; Bible.com's two Morgan editions are BFBS-claimed.
  All 9 research passes COMPLETE 2026-07-16.
- **Translation watch list** (all deity-verse-gated, pipeline ready):
  Matthew Bible 1537 (John Rogers, "Thomas Matthew" — Tyndale's NT +
  Pentateuch + prison OT (Josh–2 Chr, first printing) + Coverdale fill;
  TR, PD; blocker: no machine-readable source — 1537 spelling is
  facsimile/EEBO-TCP only, the modernized New Matthew Bible is ©).
  en_tyndale.json COMPLETED 2026-07-11 (was Gen + 9 NT books): now 33
  books, +5,961 verses via tools/complete_tyndale.py (studybible.info +
  biblestudytools mirrors of the same PD Fedosov digitization as the
  shipped books — those stay byte-identical; KJV-versified, all counts
  match; litmus «God was shewed in the flesshe» ✓, Comma present in
  Tyndale's parentheses; 4 genuinely-absent verses left empty: Ex
  40:14, Lev 27:18, Num 7:22, Gal 5:21). Wycliffe versemap curated
  same day (44 runs; versemap.json now 1496 runs, zero identity
  fallbacks). Tyndale label → "1525/1531".
  ★★ PROJECT QUEUE (owner, 2026-07-27, supersedes earlier orderings):
      1. Swedish audio ships  2. Glen OT campaign finishes
      3. **ICELANDIC — the whole 66-book canon (Þorláksbiblía 1644)**
      4. Apocrypha: Karl XII first, then Luther 1545.
  ⚠ SCALE CHECK for (3), so nobody starts it unaware: the Icelandic canon is
  **31,102 verses** — roughly TWICE the ~15,100 verses left in Glen, and the
  largest single campaign this project would have attempted (Martyn NT was
  7,957). Estimate ~70-80 chunks. It is now viable and VERIFIABLE (see the
  Þorláksbiblía entry under the Icelandic notes), which it was not before —
  but it is not a small addition.
  ⚠ OVERLAP TO RESOLVE BEFORE STARTING: the volunteer is transcribing the
  1584 Guðbrandsbiblía while this would transcribe the 1644 Þorláksbiblía —
  the same text tradition, revised. Two Icelandic Bibles is a legitimate
  outcome (the zh Hans/Hant and Serbian two-script precedents), but decide
  deliberately rather than by accident, and tell him what we are doing.
  ★ Karl XII 1703 Apokryferna — **UNBLOCKED, APPROVED, QUEUED AT (4).**
  OWNER DECISION 2026-07-27, revised the same day: originally "next after
  Glen", now **behind the Icelandic canon** — Swedish ships, Glen finishes,
  Icelandic, THEN apocrypha.
  LICENSING IS SETTLED and does NOT depend on kxii.se: the scan-hunt
  (research/scanhunt_karlxii_apocrypha.md) found Litteraturbanken id
  lb2431561, a facsimile of the SAME 1703 print, declared "fritt från
  kända upphovsrättsliga begränsningar" with the API reporting license
  "cc-0"; attribution requested to Göteborgs universitetsbibliotek +
  Litteraturbanken.se (goes in sources_text as a promised credit — the
  Tweedale/Ponomar class). ⚠ The kxii.se permission email is MOOT — it
  BOUNCED TWICE and is not needed; do NOT resend it. Litteraturbanken is
  the STRONGER position anyway, because kxii.se's own transcription
  license was merely unstated. kxii.se remains useful for ONE thing: a
  free independent QA diff target (via Wayback) — the only apocrypha
  candidate on record that has one, which is part of why it outranks the
  Icelandic and Luther routes.
  SHAPE: apocrypha at pp. 636-746 WITH printed verse numbers (so the
  per-chapter checksum discipline of the Glen campaign applies — unlike
  the unversified Icelandic prose); Fraktur, "reads easier than the
  Persian naskh"; ~8-20h estimated. Transcribe into the sv asset's
  apocrypha slots (indexes 66+, alongside the 1873 BFBS canon).
  Deity-litmus is not applicable to apocrypha; spot-check text quality
  against the facsimile and diff against kxii.se.
  ⚠ Karl XII's apocrypha is a 10-12 unit set (no 1/2 Esdras) — the same
  shape as Luther's and Glück's, so expect ~12 of the app's 17 slots.
  ★ LUTHER 1545 APOKRYPHEN — APPROVED, #2 BEHIND KARL XII (2026-07-27).
  Full research: research/apocrypha_sweep_2026-07-27.md (incl. the
  ORCHESTRATOR-VERIFIED ADDENDUM measured from the file itself).
  SOURCE: the Zefania "Luther 1545 (Letzte Hand)" module, identifier
  LUT.1545.LH — two mutually corroborating copies: SF_2012-08-14_DEUTSCH_
  LUT_1545_LH (staged in Hexapla-releases/) and the gratis-bible/bible
  mirror de/lut.1545.lh.xml (gratis-bible is already a trusted source
  here — ru/rst.xml came from it). 76 books = 66 canon + Luther's 10
  apocrypha units (Judit, Weisheit, Tobia, Sirach, Baruch, 1-2 Makkabäer,
  xDaniel, xEster, Manasse; no 1/2 Esdras). Canon litmus PASSES on the
  module (1 Tim 3:16 «Gott ist offenbaret im Fleisch»), same textual
  tradition as the shipped asset.
  ⚠ NOT the zeno.org copy — zeno is BLOCKED by its own terms (asserts
  §§87a UrhG database right; «Übernahme … in eine andere Datenbank ist
  nicht gestattet» restated INSIDE its Gemeinfrei clause; no-scraping;
  non-commercial only; and its "Gemeinfrei" tag is self-described as an
  OPINION, not a warranty). Do not re-propose zeno.
  RIGHTS, two layers, kept separate:
   (a) THE TEXT IS CLEAN, established from the statute, not inferred:
       UrhG §70 protects critical/scientific editions of PD works for
       25 years from publication, so even the Volz 1972 edition layer
       lapsed at the end of 1997; the 1545 text is PD by age. CARVE-OUT:
       any Volz-authored introduction/apparatus is an ordinary §64 work
       (Volz †1978 → © to end of 2048) — TEXT ONLY, never the apparatus.
   (b) THE TRANSCRIPTION LAYER IS AMBIGUOUS: the module's <rights> is an
       INTENT NOTE, «Umsonst habt ihrs empfangen, umsonst gebet es auch.
       (Matthäus 10:8)», from lutherbibel.net (transcriber initialled only; site now
       dead). That is not a licence with terms.
  ✅ **CLOSED BY OWNER DECISION 2026-07-27: risk accepted, explicitly
  "same as Van Dyck."** Same documented-deviation pattern: act now,
  respond to feedback if it ever arrives. Supporting it: the underlying
  text rights are independently clean (a), the stated intent is
  give-it-away-freely, and it is the same Zefania family the app already
  ships de_luther from (so no new counterparty).
  ⚠ For any future session: this is a RISK ACCEPTANCE, NOT a licence
  finding. Do NOT cite this entry as proof the transcription is licensed.
  If contact ever comes, the fallbacks are (a) luth1912ap.xml in the same
  gratis-bible repo — explicit unhedged "Public Domain", same 10 units,
  at the cost of being the 1912 revision (edition mismatch with our 1545
  canon, so a real downgrade, not a free swap), (b) transcribing from a
  PD facsimile like the Karl XII route. No further action needed unless
  that happens.
  ⚠⚠ CONVERTER REQUIREMENTS (both found by direct inspection — do not
  skip):
   1. **4,716 <NOTE> elements are embedded INSIDE <VERS> nodes**, running
      straight on from scripture with no separator (verified at 1 Tim
      3:16). A naive strip-tags-keep-text converter WILL inject Luther's
      marginal notes into verse text — the exact defect class already
      repaired in ru_synodal (escaped OSIS), la_vulgata (<Aleph>/<Sponsa>)
      and zh_cuv (<WAHb>). Extract notes BEFORE text extraction and assert
      zero note text remains. ⚠ The gratis-bible copy was described as
      "clean OSIS" but the two copies were NOT diffed — do not assume the
      mirror is note-free; run tools/audit_asset_markup.py plus an
      explicit note-leak check on whichever copy is actually converted.
   2. Structural fit vs the app's KJV apocrypha slots: SEVEN of ten match
      the KJV chapter grid exactly (Judith 16, Wisdom 19, Tobit 14,
      Sirach 51, Baruch 6, 1 Macc 16, 2 Macc 15). THREE need curation —
      xDaniel bundles what KJV splits into Azariah/Susanna/Bel; xEster is
      arranged differently from Additions to Esther; Manasse is versified
      (16 vv) where the app's KJV slot is ONE unversified block. Verse-
      total gaps in Tobit and Sirach are expected RECENSION differences —
      do NOT "fix" them toward the KJV.
  💡 OPPORTUNITY, scope separately so it cannot delay the apocrypha: those
  notes are Luther's OWN Anmerkungen («Die gantze Heilige Schrifft mit den
  Anmerkungen des Reformators»), and the app already has the mechanism to
  surface them — the KJV's 7,859 {x: y} margin notes shown on demand under
  "Translator's notes". Would be the first non-English translation notes
  in the app.
  Tamil — INTEGRATED IN TREE 2026-07-13 for 1.4.3 (code 10): IRV
  Tamil 2019 (ebible.org tam2017, Bridge Connectivity Solutions,
  CC BY-SA 4.0 — same publisher/license/pipeline as Sanskrit), the
  21st translation / 16th language, full 66 books. LITMUS 7/7
  (verified from the converted asset): 1 Tim 3:16 «தேவன்
  சரீரத்திலே வெளிப்பட்டார்», Comma present, Acts 8:37 + Rom 16:24
  present, Joseph at Lk 2:33, church of GOD at Acts 20:28. The
  mirror case of Hindi: same IRV project, but the Tamil OV base
  (1871 Bower/Union) predates the 1881 RV, so TR readings survived
  the modernization. Converter tools/convert_tamil_irv.py; whole
  text sits on the KJV grid except 3 Jn 14/15 (versemap-curated);
  values-ta UI locale (344 strings, native Tamil grammar terms —
  native-speaker review welcome, ask the Tamil tester); ta-IN Play
  listing + screenshots in tree (reader shot + feature graphic via
  tools/render_text.ps1 — WPF/DirectWrite shaping bridge, because
  PIL cannot shape Indic scripts; reuse for any future Indic
  language). Owner asked for it for his Tamil/Malayalam tester.
  Malayalam — DEAD END as of 2026-07-13 (verified): the only
  machine-readable PD/CC texts — 1910 Sathyavedapusthakam (tfbf
  GitHub / ebible mal2015) and Malayalam IRV (ebible mal) — are
  RV-conformed: «അവൻ» (He) at 1 Tim 3:16, no Comma, Acts 8:37 +
  Rom 16:24 omitted, "his father" at Lk 2:33. TR-faithful Bailey
  1843 / Gundert 1868 are facsimile-scan-only. RE-CHECK yearly:
  Benjamin Bailey Foundation transcription; ebible.org mal* list.
  Tagalog — OWNER DECISION PENDING (researched 2026-07-13): 1905
  Ang Biblia is ASV/CT-based (fails litmus, verified) BUT «Ang
  Malayang Biblia» (AMB, github.com/SalitaNgDiyos, CC BY-SA 4.0,
  TheWordAMB.nt module) is a TR-based Tagalog NT passing 7/7 with
  every word Strong's-tagged; exact KJV NT grid. CAVEATS for the
  owner: modern conversational register (po/opo honorifics), Luke
  19:13 renders minas as «500,000 piso» (pesos in the verse text),
  iglesia→Kongresyon, bautismo→lublob (Baptist-leaning), digits for
  numerals; living small-team translation (2017-2025), not a
  classic. Textually clean; stylistically a Meiji-plus call.
  Owner decided 2026-07-13: DON'T ship yet — ask the team first
  (store-assets/amb_email_draft.txt: which release is stable; is a
  traditional-renderings edition planned; attribution wording).
  Email SENT by owner 2026-07-13 — decide when they reply.
  Latin — APPROVED + INTEGRATED IN TREE 2026-07-13 for 1.4.3
  ("vul", la_vulgata.json, 73 books incl. deuterocanon in the
  apocrypha slots, 35,811 verses, «Vulgata Clementina, 1592 (LA)»):
  the Clementine Vulgate, Tweedale/VulSearch edition (PUBLIC DOMAIN
  with acknowledgment request — honored in sources_text ×13;
  Quasimodo.zip source archive, converter
  tools/convert_vulgate.py strips the /-linebreak and \\-paragraph
  markers, Latin-1 → UTF-8). 22nd translation / 17th language.
  Litmus: Comma PRESENT, Acts 8:37 + Rom 16:24 PRESENT, ecclesiam
  Dei, qui est in cælo; accepted deviations: 1 Tim 3:16 «quod
  manifestatum est» and Lk 2:33 «pater ejus» — owner approved
  after establishing the shipped WYCLIFFE (translated FROM the
  Vulgate) already carries BOTH readings («that thing that was
  schewid in fleisch»; «his fadir and his modir»), so no new
  doctrinal exposure; the litmus's purpose (block post-1881
  critical-text intrusion) is untouched — Jerome predates the
  TR/CT split by 11 centuries. Versemap: Gallican LXX psalter
  via the existing engine + VUL_PSALTER overrides (Ps 2/4/16,
  text-verified); Daniel via the syn/csl LXX special-case;
  Esther 10:4-16:24 + Dan 13-14 unmapped additions (Wycliffe
  precedent); wyc-shared Vulgate-tradition curation (Gen split
  out — Clementine merges 5:32 into 5:31 where wyc holds it in
  6:1); vul-specific curated books 0/3/5/6/8/10/17/29/42/65
  pre-empt the repartition engine (its flat cumulative pairing
  SMEARED local intra-chapter splits across whole books — caught
  by the pair-report eyeball pass; every curated run text-verified
  against the Latin, incl. the Vulgate Job 39-41 reflow). 1792
  runs / 15 mapped translations. Beza's TR-perfect Latin NT /
  Junius-Tremellius: scan-only, no digitization exists (verified
  across e-Sword/CrossWire/CCEL/GitHub; latinbible.com sells page
  images) — the OCR-project idea remains on the far watch list.
  Nova Vulgata: Vatican © + CT, ruled out. No Play listing for
  Latin (Play has no Latin listing language); no UI locale.
  Hindi — DEAD END as of 2026-07-11 (verified, like Korean): every
  machine-readable Hindi Bible FAILS the litmus — BSI OV re-edit,
  IRV 2019 (the only clean CC BY-SA text), Biblica CV all read «वह
  जो» ("he who") at 1 Tim 3:16, no Comma, "उसका पिता" at Lk 2:33
  (Acts 8:37 present in OV/IRV; IRV drops Rom 16:24 = CT marker).
  The OV's NT absorbed RV/critical readings post-1881. Pre-1881 OV
  editions likely pass but are SCAN-ONLY (e.g. archive.org
  holybibleinhindi00alla — an OCR project if ever). TBS is making a
  fresh Hindi TR translation (only John published; will be TBS ©) —
  RE-CHECK tbsbibles.org/news/698804 yearly.
  Sanskrit — APPROVED + INTEGRATED IN TREE 2026-07-11 ("san",
  sa_nt.json, 7,958 verses, registered in Bible.kt as «संस्कृतम् —
  Sanskrit NT, 1851 (SA)»; CC BY-SA attribution ×12 locales;
  versemap 13 translations/1497 runs). FOLDED INTO 1.4.1 (owner
  decision 2026-07-12 while RuStore moderation queued 1.4.0):
  artifacts re-cut, versionCode 8 verified, sa_nt.json + versemap
  confirmed inside the APK. 1.4.1 = 20 translations / 15 languages —
  update release notes + STORE_LISTING copy accordingly before
  submitting. The eBible sandev edition turned out BETTER
  than scoped: Acts 8:37 PRESENT, Lk 2:33 names Joseph (तस्य माता
  यूषफ् च), all 260 chapters KJV-shaped (3 Jn 14/15 native split
  mapped; source's empty-[] Rev 12:18 dropped — its 13:1 prints the
  KJV arrangement). The ONE standing Griesbach deviation: Acts 20:28
  "church of the Lord (प्रभु)" vs TR "of God" — owner accepted.
  Litmus: 1 Tim 3:16 «ईश्वरो मानवदेहे प्रकाशित», Comma present,
  Jn 1:1 स्वयमीश्वर. 1.4.2 remainder: nothing — data complete.
  Original scoping: the 1808
  Serampore original is effectively unobtainable (no scans survive
  accessibly); its successor, the 1851 Yates/Wenger Calcutta NT, IS
  machine-readable: ebible.org id `sandev` (SanskritBible.in, CC
  BY-SA 4.0, Devanagari, USFM zip). LITMUS MIXED — TR-core with
  Griesbach deviations: 1 Tim 3:16 «ईश्वरो मानवदेहे प्रकाशित» PASS,
  Comma Johanneum PRESENT, Jn 3:13/Rom 9:5 pass; but Acts 8:37
  OMITTED, Acts 20:28 "church of the Lord", Lk 2:33 "his father".
  Meiji-precedent call for the owner. If adopted: NT-only (like grc),
  converter MUST leave empty slots for omitted TR verses (Acts 8:37)
  to keep KJV indexing; CC BY-SA needs license+link in sources_text.
  OT = scans only (archive.org holybibleinsansc00gill + 02-04weng,
  1848); OCR scoped at 400-800 proofreading hours — NOT feasible;
  email SanskritBible.in about their OT progress instead.
  Guðbrandsbiblía 1584 (Icelandic) — PERMISSION DECLINED 2026-07-12
  by the framkvæmdastjóri (director) of the Icelandic Bible
  Society): they are building an authoritative digital text of BOTH
  Guðbrandsbiblía and Viðeyjarbiblía with the Digital Bible Library
  (based on a named scholar's academic edition); the current website
  text has known flaws ("slightly flawed", editorial issues); "we
  are not going to allow any further publication of those texts"
  until the DBL work is finalized — low priority, "not going to
  come out for a while". CLOSED — do NOT scrape biblian.is. Both
  Icelandic texts blocked. RE-ASK when the DBL edition ships
  (check dbl.bible / re-email the Icelandic Bible Society yearly — address in the local biblian_email_draft.txt); the DBL text
  would also be cleaner than what we'd have scraped. Earlier
  scoping (litmus PASS, no verse numbers in prose) remains valid
  background for that day. History:
  Árnastofnun: they do NOT have the digital text; it IS
  downloadable section-by-section at biblian.is/gudbrandsbiblia/
  (Icelandic Bible Society). She warns the archive.org copy is full
  of scanning errors — DO NOT use archive.org for this. SCOPED
  2026-07-11: complete (66 + 11 apocrypha books), modernized
  spelling, per-chapter WordPress pages (open REST API, easy
  scrape); LITMUS: 1 Tim 3:16 «Guð er opinberaður í holdinu» PASS,
  Comma PRESENT, Acts 8:37 present, Lk 2:33 "hans faðir" = Luther's
  own reading (same as shipped de_luther — acceptable). TWO GATES:
  (1) transcription is "Allur réttur áskilinn" (all rights
  reserved) — email the Icelandic Bible Society (address in the draft), draft at
  store-assets/biblian_email_draft.txt; (2) PROSE HAS NO VERSE
  NUMBERS (pericope paragraphs; Mt 2 = 6 paragraphs for 23 verses;
  only Psalms/poetry are verse-per-paragraph) → 150-400+ h
  segmentation UNLESS that scholar's working files
  carry verse structure — ASK THIS in the permission email; a yes
  collapses it to a normal converter. Plan B in same email:
  Viðeyjarbiblía 1841 (biblian.is/videy/, presumably versified,
  needs its own litmus pass).
  Korean — no PD TR text exists (개역한글 fails 1 Tim 3:16 with 그는;
  한글킹제임스/흠정역 copyrighted).
  LXX apocrypha — ⚠ RE-SCOPED 2026-07-15, the old note («no
  clean-licensed tagged text (CATSS restrictive)») was OVERBROAD and
  read in practice as "LXX apocrypha can't ship". The truth: it CAN
  ship, just WITHOUT interlinear. The restriction was never on the
  LXX text — only on CATSS's MORPHOLOGY layer. Split the two:
  (a) TEXT — SHIPPABLE TODAY: github.com/nathans/lxx-swete, "The
      Greek text and its annotations in the data directory are
      published under the terms of the Creative Commons
      Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
      license" — same license family + attribution pipeline as the
      shipped Tamil IRV and Sanskrit assets. Swete (1909) via the
      Open Greek and Latin First1KGreek digitization, ZERO CATSS
      dependency. Full apocrypha set verified present (Esdras A,
      Judith, Tobit, 1-4 Macc, Odae, Wisdom, Sirach, Psalms of
      Solomon, Baruch, Ep. Jeremiah, Susanna, Bel, both Daniel
      recensions). ALREADY VERSIFIED — one token per line prefixed
      book.chapter.verse (e.g. «21.1.1 BΙBΛΟΣ / 21.1.1 λόγων»;
      Sirach prologue at 34.0.0), so it is converter-ready, NOT a
      segmentation project (contrast the Guðbrandsbiblía prose trap).
      Deity-litmus n/a for apocrypha (same as the Karl XII note).
      ⚠ OWNER DECISION: whether a Greek LXX apocrypha belongs in the
      app at all, and if so where (grc is currently NT-only).
  (b) INTERLINEAR on it — still genuinely blocked: every mainstream
      TAGGED LXX inherits CATSS ("not to be used for commercial
      purposes without prior written consent", signed User
      Declaration): eliranwong/LXX-Rahlfs-1935 is CC BY-NC-SA AND
      CATSS-derived; CenterBLC/LXX derives from it; openscriptures/
      GreekResources CC BY 4.0 covers only their lemma corrections,
      text still comes from CCAT. RE-CHECK YEARLY: STEPBible TAGOT
      would be CC BY 4.0 and covers apocrypha, but its morphology is
      "based on CCAT" and it is still unposted ("Datasets coming…").
  Also worth recording: RAHLFS 1935 IS PUBLIC DOMAIN — Rahlfs died
  8 Apr 1935, German life+70 → PD since 1 Jan 2006. The © people
  associate with "Rahlfs" attaches to Rahlfs-Hanhart (2006), a
  different, later revision by the German Bible Society.
