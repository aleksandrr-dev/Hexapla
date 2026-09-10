# Hexapla Web — execution plan (written 2026-09-09, not started)

Self-contained plan for a future session. Read the repo `CLAUDE.md` first for
project law (KJV/TR policy, mission, `sources_text` obligations), then the
global CLAUDE.md «Subagents» and «Turn economy» sections. Owner:
aleksandrr-dev. Mission unchanged on the web: evangelism — free, no ads, no
accounts, no data collection, nothing locked.

**Why now.** A reviewer for the Turkish edition (Bruce) could not see the app
at all: the RuStore button is a Russian Android store page, the Play button is
disabled, the third button is a 78 MB APK. A browser reader is the only demo
that works for everyone, and it doubles as the app for iPhone and desktop users
until the iOS port exists.

## 0. Decisions already made (change only with the owner)

| decision | choice | why |
|---|---|---|
| hosting | GitHub Pages, same site as the landing page, at `/Hexapla/app/` | free, no backend, no telemetry — matches the mission; the QR and archive.org items already point at this domain |
| build/deploy | GitHub Actions builds the data from `app/src/main/assets` and deploys with `actions/deploy-pages` | the split JSON (~200 MB) must never be committed; the source assets already are |
| stack | Vite + TypeScript + Preact, `idb` for IndexedDB, `vite-plugin-pwa` (Workbox) for offline | small bundle, tiny API surface for an agent to hold in context, no build-time magic |
| data unit | one JSON per translation per book, served gzip by Pages | KJV is 5.2 MB raw / 1.6 MB gz whole; per book ~80 KB raw / ~25 KB gz — lazy load per book |
| offline | cache what you read, plus «keep offline» per translation (whole translation into the Cache API) | offline is the app's identity; a first visit must still be instant |
| donations | none on the web, ever | the `play` flavor precedent: zero donation code, provably absent |
| analytics | none, not even Pages' own counter mentioned | mission |

## 1. Data build — `tools/build_web_data.py` (0 model tokens)

Input is the app's own assets, so the web app can never drift from Android.

- `bibles/<id>.json` → `data/<id>/<bookIdx>.json`: the book object as-is
  (name, chapters as arrays of verse strings). Margin notes `{…:…}` are
  stripped at build time exactly as `BibleRepo.parseAsset` does (colon = drop,
  no colon = keep the supplied words); port that rule and control it against
  three known verses.
- `data/manifest.json`: every translation with id, language tag, display
  name, script, book count, licence line and the `sources_text` credit that
  Android shows. **The credit text is a licence obligation (CC-BY / CC-BY-SA
  data), not decoration.**
- `versemap.json` copied whole (it is small); `xrefs.json` split per book;
  `strongs_lexicon*.json` whole (lazy); `interlinear_*.json` split per book;
  `audio_index.json` and `audio_index_gen.json` copied whole.
- `webster1828.json` (13 MB) split by first letter.
- **Control:** for every translation, sum of verses in the split files equals
  the sum in the source file, and `data/manifest.json` translation count equals
  `python tools/count_translations.py`. The build fails loudly on any mismatch.
  A count function that fails returns -1, never a plausible number.

## 2. Scope fence — v1 must contain, and must not contain

**In v1**

- Read any translation; book/chapter navigation; remember position.
- Parallel view (two translations side by side or stacked) pivoting through
  `versemap.json`, the same way `VerseMap.kt` does. Port its run semantics
  exactly (equal-length runs pair verse-for-verse; unequal runs are blocks;
  `transV0 > transV1` is an omission).
- Deep links `#/<translation>/<book>/<chapter>/<verse>` and «copy link /
  copy text» sharing. This is what a reviewer or a tract can point at.
- Search within a translation, in a Web Worker, over the whole translation
  (fetched once, ~1.6 MB gz for KJV). Plain substring first; no stemming.
- Bookmarks, highlights, notes in IndexedDB. Local only, exportable as JSON.
- Cross-references (openbible.info, credit required).
- Strong's numbers on the KJV with the lexicon popover.
- Audio: play a chapter from archive.org through `<audio>`, with verse
  following from the `o` offsets and word highlighting from the `.w.json`
  sidecars — index-driven exactly like `ReadingService`. Generated narration
  wins over LibriVox where both exist, as on Android.
- Installable PWA; offline for anything already read; «keep offline» per
  translation.
- Language of the UI from the 27 Android locale folders (a converter script
  turns `strings.xml` into JSON); dark theme; font size.

**Not in v1** (v2 candidates, in this order): TTS via Web Speech (device-
dependent quality; test before promising), reading plans, Topics and the
mood map, interlinear tap-through, music and ambience, the widget and
reminders (no web equivalent worth building).

## 3. Phases with acceptance gates

Each phase ends deployed and checked in a real browser, not «builds locally».

- **P0 — data build.** `tools/build_web_data.py` with its controls; a
  workflow that builds `site/` = repo `index.html` + `PRIVACY.html` +
  `icon.png` + `app/` + `data/` and deploys it. **Gate:** the owner switches
  Pages source from branch to Actions (repo Settings → Pages) and the landing
  page still serves byte-identical HTML afterwards. ⚠ Until that switch, the
  landing page is served from the branch; do not break it.
- **P1 — reader.** Translation picker, book/chapter, parallel view, deep
  links, share. **Gate:** Bruce's case — a non-Android user opens a link to a
  Turkish or Icelandic verse and reads it in under three seconds on a phone.
- **P2 — search, bookmarks, highlights, notes, cross-references, Strong's.**
  **Gate:** search over the KJV returns in under one second on a mid phone.
- **P3 — audio.** **Gate:** verse following and word highlighting on one
  LibriVox chapter and one generated chapter, verified by eye against the
  Android app on the same chapter. ⚠ Streaming through `<audio>` needs no
  CORS; fetching `.w.json` sidecars does. Confirm archive.org sends
  `Access-Control-Allow-Origin: *` on a real sidecar before building the
  feature, and record the header in `docs/SETTLED.md`.
- **P4 — PWA and offline, UI locales.** **Gate:** airplane mode, reopen the
  app, read a chapter you had opened and one from a translation you «kept»;
  both work. ⚠ iOS Safari evicts unused site storage after seven days of
  non-use; say so in the «keep offline» dialog rather than promising.
- **P5 — landing page and listings.** A fourth button «Read in the browser»;
  the store listings and the tagline mention the web app; counts still come
  from `count_translations.py`. **Gate:** `check_release_notes.py` passes.

## 4. Risks

- **Repo weight.** Never commit `data/`. The workflow builds it in ~1 min.
- **Pages limits.** Soft 1 GB per site; this is ~200 MB. Fine, but do not add
  the music or the book art to the site without measuring.
- **CJK and Persian search.** Substring search works; word boundaries do not.
  Say so, do not hack around it in v1.
- **Licensing.** Same sources as Android, same credits, shown on an About
  page and in the manifest. The Þorláksbiblía and Karl XII texts are the
  project's own transcriptions of public-domain prints; keep the provenance
  line the Android app uses.
- **Feature parity pressure.** The fence in §2 is the answer. A web v1 that
  reads well beats a half-port of everything.

## 5. Session-zero checklist for the executing session

1. Read `CLAUDE.md`, this file, `docs/ROADMAP.md`. Do not read the narration
   or transcription docs; they are irrelevant here.
2. `python tools/count_translations.py` — the number the manifest must match.
3. Write `tools/build_web_data.py` with its controls first; run it; the
   `data/` tree is the contract everything else codes against.
4. Scaffold `web/` with Vite + Preact + TS; commit the scaffold and the
   workflow; ask the owner to flip the Pages source. Everything else waits on
   that gate, so ask early.
5. Work in the shape the global CLAUDE.md prescribes: scripts over reads,
   batched commands, a screenshot only at a phase gate, a fresh session per
   phase.
