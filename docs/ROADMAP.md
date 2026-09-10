# Hexapla roadmap — the live list, full text

CLAUDE.md carries a one-line pointer; this file holds the record.


── MOVED OUT OF CLAUDE.md, 2026-09-09 ──
(verbatim; CLAUDE.md now carries a pointer to this block)

## Roadmap (agreed with owner) — LIVE ITEMS ONLY

Shipped roadmap items and their full records are in `docs/RELEASE_HISTORY.md`.
Numbering is from the original plan; the gaps are shipped items.

2. **IzzyOnDroid listing** (repo is public; low effort — the `foss` flavor
   already exists, so what remains is the LISTING).
4. **Self-generated narration** — the machinery is built and several sets have
   shipped on it. Current work and the KJV re-render: `docs/NARRATION.md` +
   `tools/KJV_VOICE_RUNBOOK.md`; the original execution plan, whose ⚠ GATE
   markers still apply to any new voice (licensing, owner voice pick, stress-
   dictionary quality), is `tools/NARRATION_PLAN.md`.
   ⚠⚠ **OPEN PRODUCT QUESTION BEFORE THE KJV RE-RENDER:** `ReadingService`
   merges `putAll(librivox); putAll(generated)`, so **generated wins** — a full
   generated KJV silently retires the LibriVox HUMAN narration for the 50 books
   it covers. **Get the owner's explicit yes before rendering 1,371 chapters.**
5. **iOS port** = separate v2.0-scale project (Kotlin/Compose Multiplatform;
   Swift needed for audio/TTS/widget/notifications; Mac + Apple $99/yr).
   ★ FULL EXECUTION PLAN: `IOS_PORT_PLAN.md` (repo root) — self-contained;
   GATED on Play production going live + owner go.
