# Hexapla — CLAUDE.md archive

Historical/superseded material moved out of CLAUDE.md by /doctor on 2026-07-25
to reduce always-loaded context. Nothing here is deleted — it is preserved verbatim.
This file is NOT auto-loaded; read it when you need release history.

## Store submission chronology (1.2.0 – 1.4.0 staging), superseded by 1.6.0/code 14

- **Google Play (2026-07-08)**: closed track now has 1.2.0 (code 5),
  uploaded same day as 1.1.2 (code 4); the 14-day tester clock
  (started ~2026-07-07) keeps running across uploads to the same track.
- **GitHub release v1.2.0** published (releases/latest serves the
  1.2.0 RuStore-flavor APK for the landing page's direct-APK button).
- **1.3.0 (code 6)** (era headings + 1828 dictionary): submitted to
  RuStore + GitHub release v1.3.0 published 2026-07-09. Play: 1.3.0
  uploaded to the closed track and **submitted for review 2026-07-10**
  (status "In review"). Removing the auto-carried previous bundle
  (code 2) from the release's "Previous release → Included" section was
  needed — otherwise Play errors "APK completely shadowed by higher
  version code". Release notes were refreshed (were still the "First
  release / 12 translations" text).
- **Play store listing refreshed + submitted for review 2026-07-10:**
  all 5 languages — app name → the number-free «Parallel Bible» titles
  (Hexapla — Parallel Bible / Гексапла — параллельная Библия / Biblia
  paralela / Parallelbibel / Bible parallèle), plus short + full
  descriptions updated to the current "13 translations" copy from
  `STORE_LISTING.md`. Was previously the stale "6 languages / 12
  translations" text (Play listing had never been refreshed, only the
  repo file). Edit at Grow users → Store presence → Store listings →
  Default store listing → Edit.
- **1.4.0 (code 7) built + staged 2026-07-11, re-cut same day to add
  the Nordics** (interlinear; +Almeida, Diodati, Meiji, CUV×2 scripts,
  Karl XII 1703, Dansk 1819; −BBE; Play empty-Support fix):
  `C:\Projects\Hexapla-1.4.0-rustore.apk` / `-play.aab`. 18 translations
  / 14 languages; STORE_LISTING.md fully refreshed incl. interlinear line.

## TRANSLATION/LANGUAGE COUNT — RECONCILED 2026-07-26 (owner delegated the call)

THE NUMBERS: **33 translations in 29 languages** (35 texts total).

Derived from Bible.kt, not from memory. 35 Translation() entries; `grc`
(Byzantine Greek NT) and `wlc` (Hebrew OT) are ORIGINAL-LANGUAGE texts, not
translations -> 33 translations. Language count = 29, by these rules:
 · Church Slavonic (csl) counts SEPARATELY from Russian — a distinct liturgical
   language (ISO cu), presented separately in-app. Bible.kt codes it
   Locale("ru") for TTS reasons only; that is a technical detail, and it is
   exactly where the old undercount came from.
 · Ancient/Byzantine Greek (grc) counts SEPARATELY from Modern Greek (vam) —
   ISO grc vs el, both readable as primary/secondary.
 · Middle English (wyc, Wycliffe) FOLDS INTO English — deliberately conservative.
 · Chinese Simplified (cus) + Traditional (cuv) = ONE language, two scripts.
The 29 languages: English, French, German, Swedish, Finnish, Latvian, Polish,
Serbian, Danish, Dutch, Spanish, Portuguese, Italian, Hungarian, Czech,
Japanese, Chinese, Russian, Church Slavonic, Ancient Greek, Modern Greek,
Hebrew, Sanskrit, Tamil, Arabic, Armenian, Latin, Belarusian, Persian.

WHY THE OLD "28" WAS WRONG: it counted distinct LOCALE CODES, which silently
collapses Slavonic into Russian and Ancient into Modern Greek. Not defensible
line-by-line; 29 is.

APPLIED 2026-07-26: welcome_tagline updated in ALL 25 locale files
("seventeen" -> 29 in each language's own numeral form). It had been stale since
the 1.4.3 era — the owner's Russian-speaking friend spotted «17 языках» on the
welcome screen. Resources compile clean.

✅ LOCKSTEP ACHIEVED 2026-07-27 (CLAUDE.md's rule: app, listing and landing page
must agree). Final state, all three now reading **33 translations / 29 languages**:
 · app — welcome_tagline, 29 languages in each locale's own numeral form; the
   app states NO translation count, so it needed no change.
 · store-assets/STORE_LISTING.md — Store-descriptions section only.
 · index.html — landing page.

⚠ AN OVERCOUNT WAS CAUGHT AND CORRECTED ON THE WAY. Between the reconciliation
above and 2026-07-27, the listing and landing page were bumped to "**34**
translations in 29 languages", and a session recorded that as verified-correct.
It was WRONG — an overclaim of one translation in public store copy. Re-derived
from Bible.kt at correction time, the same way as above:
    36 lines match "Translation(" — but ONE is `data class Translation(`,
    the class declaration. So **35 entries**, minus `grc` (Byzantine Greek NT)
    and `wlc` (Hebrew OT), which are ORIGINAL-LANGUAGE texts and not
    translations = **33**.
★ IF THIS NUMBER IS EVER QUESTIONED AGAIN, run that derivation rather than
trusting any recorded figure — including this one. The count has now drifted
twice (28 undercount, then 34 overcount).

THE **1.6.0 RELEASE-NOTES BLOCK WAS ALSO CORRECTED** to 33 (owner instruction,
2026-07-27 — overriding an initial decision to leave it as a record of what was
submitted). 30 replacements, one per locale entry. Rationale for the override:
a wrong number in a copy-paste-to-store file is a live trap regardless of which
release it sits under, and the repo should not carry a figure known to be false.
⚠ CONSEQUENCE TO BE AWARE OF: the 1.6.0 notes in the repo now DIFFER from what
was actually pasted into Play/RuStore for 1.6.0, which really did say 34. That
is a deliberate, recorded divergence — do not "restore" it as a defect.

NOT CHANGED: the ARCHIVE section (925+) keeps its historical counts (the "28"s
and older), per the existing convention. The 1.6.1 notes carry no translation
count at all, so nothing pasted for THIS release ever repeated the error.
VERIFIED after both passes: zero standalone "34" remains anywhere in
STORE_LISTING.md outside the ARCHIVE section, and CRLF line endings intact.
