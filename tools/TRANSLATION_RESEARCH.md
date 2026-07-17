# Translation candidate research plan (drafted 2026-07-16)

Self-contained brief for research sessions (any model). Each candidate gets
ONE research pass producing ONE report file. NO integration without the
owner's explicit decision — research and integration are separate steps.

## Context (read once)

Hexapla ships 22 translations / 17 languages, all KJV/TR textual tradition,
all public domain or CC-with-attribution. Every candidate must clear THREE
independent gates:

1. **Deity-verse litmus** (below) — blocks post-1881 critical-text readings.
2. **License** — PD by age, or CC BY / CC BY-SA with attribution. NC or ND
   disqualify. "Freely available" ≠ licensed: a digitization with no stated
   license is BLOCKED until its owner grants permission (see the repo's
   history: BibleQuote, biblian.is, kxii.se — we email, we wait).
3. **Machine-readability** — a real digitization with verse structure.
   Facsimile scans are not sources (OCR projects run 400-800 hours; always
   out of scope for a research pass).

**The 1881 rule of thumb**: Protestant translations MADE before 1881 are TR
by default; anything REVISED after 1881 may have absorbed critical readings.
The revision lineage of the specific digitized edition matters as much as
the original date — Hindi OV and Malayalam 1910 both failed on this.

## The litmus (run on the ACTUAL digitized text, not on claims about it)

Fetch each verse from the candidate digitization itself and quote it in the
report. PASS requires the TR reading; note every deviation.

| # | Verse        | TR reading (what PASS looks like)                     |
|---|--------------|-------------------------------------------------------|
| 1 | 1 Tim 3:16   | "GOD was manifest in the flesh" — not "He who"        |
| 2 | 1 Jn 5:7-8   | Comma Johanneum PRESENT (Father, Word, Holy Ghost)    |
| 3 | Acts 8:37    | verse PRESENT (eunuch's confession)                   |
| 4 | Rom 16:24    | verse PRESENT                                         |
| 5 | Lk 2:33      | "JOSEPH and his mother" — not "his father and mother" |
| 6 | Acts 20:28   | "church OF GOD" — not "of the Lord"                   |
| 7 | Jn 3:13      | "...Son of man WHICH IS IN HEAVEN" (clause present)   |

Precedents the owner has accepted, for calibration: Luther's own Lk 2:33
"sein Vater" (the translator's genuine pre-1881 reading, not CT intrusion);
Sanskrit 1851's Griesbach deviations (mixed TR-core, owner call); Vulgate's
readings (predates the TR/CT split entirely). A pre-1881 deviation is an
OWNER DECISION; a post-1881 revision toward NA/WH readings is a FAIL.

## Verification discipline (non-negotiable)

- WebFetch summarizers FABRICATE quotes. For license texts and scripture,
  fetch RAW files (curl / raw.githubusercontent / plain-text endpoints) and
  quote exact sentences with their URL.
- Never generalize a license across a family (code ≠ data ≠ that other
  repo by the same people). Quote the sentence or write UNVERIFIED.
- CrossWire module licenses live in the module's .conf
  (DistributionLicense= line) — quote it, don't assume.
- eBible.org: per-translation copyright page. Quote it.

## Report format (one file per candidate)

Write to C:\Projects\Hexapla-releases\research\<candidate>_report.md:
verdict up top (SHIP-CANDIDATE / OWNER-DECISION / BLOCKED + one line why),
then: litmus table with quoted verses; license quotes + URLs; best source
(format, verse structure, canon size, versification notes — psalm titles!
continental numbering!); converter shape (which existing tools/*.py is the
nearest template); open questions. Flag anything UNVERIFIED explicitly.

## Candidates, in priority order

1. **Dutch — Statenvertaling 1637** (top candidate: near-certain pass, huge
   digitization surface). Leads: CrossWire DutSVV; statenvertaling.net;
   github.com/gratis-bible/bible (nl); ebible.org. Editions: original 1637
   spelling vs 1888 "Jongbloed" spelling revision — check WHICH is digitized
   and whether the revision touched readings (expected: spelling only).
   GBS (Gereformeerde Bijbelstichting) editions are recent typesettings —
   check their claims separately if encountered.
2. **Arabic — Smith–Van Dyck 1865** (highest reach). Leads: ebible.org
   (arbvdyck or similar), CrossWire, unfoldingWord? Multiple digitizations
   circulate; license per digitization. Risk: later "revised" SVD editions;
   confirm the digitized edition's lineage. Litmus verses need someone able
   to read Arabic script — quote the Arabic and translate the key phrase.
3. **Hungarian — Károli** (1590 original; 1908 spelling revision is the
   usual digitization). Leads: CrossWire HunKar; ebible.org. Risk: 1908
   revision's textual (not just spelling) changes — litmus decides.
4. **Polish — Biblia Gdańska 1632**. Leads: CrossWire PolGdanska; the
   modernized UBG (Uwspółcześniona Biblia Gdańska, Wrota Nadziei) claims
   free distribution — verify its exact license text separately from the
   1632 original (PD by age).
5. **Czech — Bible kralická 1613**. Leads: CrossWire CzeBKR; obohu.cz.
6. **Finnish — Biblia 1776**. Leads: CrossWire FinBiblia; finbible.fi
   (check their transcription's license — the TEXT is PD by age).
7. **Greek (modern) — Vamvas 1850**. Leads: CrossWire GreVamvas. Pairs
   with the shipped Byzantine NT the way Synodal pairs with Slavonic.
8. **English — Young's Literal Translation 1862**. Trivially available
   (CrossWire YLT, scrollmapper?). Easy add if wanted; low urgency (6th
   English translation).
9. **Welsh — William Morgan 1588/1620**. Digitization quality unknown —
   this pass is mostly a source hunt. Leads: CrossWire? bible.com has ©
   editions (unusable); beibl.net is a MODERN translation (not Morgan).
10. ~~Ukrainian — Kulish~~ EXCLUDED by the owner 2026-07-16. Do not research.
11. **Bulgarian — Tsarigrad 1871**. Source hunt + litmus. Later "1940
    revision" digitizations are a different, possibly CT-touched text.
12. **Serbian — Karadžić NT 1847 / Daničić OT**. Translated via Slavonic/
    Luther lineage; litmus decides. CrossWire SrKDIjekav (check script:
    Cyrillic vs Latin, ijekavian).

Second wave (added 2026-07-17, owner-requested):

13. **Latvian — Glück Bible 1689** (Ernst Glück; the Latvian classic,
    TR-era). Leads: CrossWire Latvian modules (check names/conf); eBible
    lav entries (which edition? the 1965 revision is a different text);
    gratis-bible lv directory (a prior listing showed 'lv' EXISTS —
    check its edition + <rights>); scrollmapper. Trap: modern "1965
    revised" Glück is a later reworking — identify editions precisely.
14. **Estonian — Piibel 1739** (Anton Thor Helle; the Estonian classic,
    TR-era). Leads: eBible est entries; CrossWire; the Estonian Bible
    Society's digitizations of the 1739 (piibel.net hosts multiple
    editions — find the license for their transcriptions); scrollmapper.
15. **Lithuanian — the 1735 Bible** (Kvedlinburg/Quandt edition; also
    Chylinski 1660s partial as background). Primarily a SOURCE HUNT —
    machine-readable old Lithuanian scripture may not exist. Also assess
    the 1897-1902 Šventasis Raštas lineage if encountered. A BLOCKED
    verdict with re-check leads is a valid outcome.
16. **Armenian — ancient version** (5th c.; standard edition = Zohrab
    1805, classical Armenian/Grabar). Rides the VULGATE PRECEDENT
    (predates the TR/CT split — Jerome reasoning applies), so the
    litmus is informational, not pass/fail; note readings anyway.
    Leads: digilib.aua.am, arak29, TITUS (titus.uni-frankfurt.de —
    scholarly digitizations, CHECK THEIR LICENSE TERMS, often
    restrictive), CrossWire, eBible hy entries (which are likely the
    MODERN Ararat 1896 Eastern / 1853 Western translations — evaluate
    those separately: 19th-c. missionary-era, litmus applies).
    Canon: Armenian tradition includes deuterocanon — report the shape.
17. **Georgian — ancient version** (5th c.; Mtskheta/Giorgi recensions;
    also the 1743 Moscow/Bakar Bible). Same Vulgate-precedent framing
    as Armenian. Leads: TITUS Georgian corpus (license!), CrossWire,
    eBible kat/geo entries (the 1989 Patriarchate translation is © —
    do not confuse). Likely hard; honest BLOCKED is fine.

Deferred idea (owner-decision scale, not a research pass): Syriac
Peshitta via the Vulgate precedent — its canon gaps (no Rev, 2 Pet,
2-3 Jn, Jude) make it a bigger call.

## What done looks like for the whole effort

Each report sits in Hexapla-releases/research/. The owner reads verdicts
and picks what ships. Integration (converter + versemap + sources_text
attribution ×13 locales + Play listing) is a separate session per
translation, using the report as its brief.
