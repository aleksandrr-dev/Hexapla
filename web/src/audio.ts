// Narration and the bed beneath it — the pure half of P3 (WEB_APP_PLAN.md § 3),
// ported from Audio.kt, MoodMap.kt and ReadingService.kt. Which file plays for
// a chapter, where to seek, which verse and word are sounding, which bed
// belongs under a passage. No DOM, no fetch: `audio.test.ts` runs it under node.
//
// ⚠ 0-BASED here, like the Android service: book, chapter and verse indexes
// are 0-based; Section.first/last are the only 1-based numbers, because the
// LibriVox index writes them that way. Mood lookups pivot through the
// 1-based versemap exactly as MoodMap.moodFor does (convert in, convert out).

import { toKjv, type VerseMapData } from "./versemap.ts";

// ---- the indexes, as data/ ships them (copied from the app's assets) --------

/** `audio_index.json`: book index -> [firstCh, lastCh, url] (1-based chapters).
 *  LibriVox human readings of the KJV; a file may span several chapters. */
export type LibriVoxIndex = Record<string, [number, number, string][]>;

/** `audio_index_gen.json`: set id -> book -> chapter -> file + verse offsets. */
export type GenIndex = Record<string, Record<string, { base: string; chapters: Record<string, { f: string; o?: number[] }> }>>;

export interface Section {
  /** 1-based, inclusive. Generated sections are one chapter: first == last. */
  first: number;
  last: number;
  url: string;
  generated: boolean;
  /** Per-verse start offsets in ms (generated only): verse following. */
  offsets: number[] | null;
}

/** Book index -> ordered sections, for one translation.
 *
 *  kjv is served from BOTH indexes: LibriVox for the books it recorded,
 *  generated narration for the rest. Generated goes in LAST so it wins on a
 *  book present in both — only it carries offsets (ReadingService.kt, the
 *  same order written out on purpose). Every other translation is generated
 *  only. */
export function sectionsFor(translation: string, librivox: LibriVoxIndex, gen: GenIndex): Map<number, Section[]> {
  const out = new Map<number, Section[]>();
  if (translation === "kjv") {
    for (const [bk, rows] of Object.entries(librivox)) {
      out.set(Number(bk), rows.map(([first, last, url]) => ({ first, last, url, generated: false, offsets: null })));
    }
  }
  for (const [bk, book] of Object.entries(gen[translation] ?? {})) {
    const list: Section[] = Object.entries(book.chapters).map(([ck, ch]) => {
      const c1 = Number(ck) + 1;
      return { first: c1, last: c1, url: book.base + "/" + ch.f, generated: true, offsets: ch.o ?? null };
    });
    list.sort((x, y) => x.first - y.first);
    out.set(Number(bk), list);
  }
  return out;
}

/** The section holding 0-based `chapter`, or null (no recording). */
export function sectionFor(sections: Section[] | undefined, chapter: number): Section | null {
  return sections?.find((s) => chapter + 1 >= s.first && chapter + 1 <= s.last) ?? null;
}

/** `<chapter>.w.json` beside a generated `.ogg` — word timings. */
export function wordsUrl(oggUrl: string): string {
  return oggUrl.replace(/\.ogg$/, "") + ".w.json";
}

/** Where to start, in ms, for `verse` (0-based) of `chapter`.
 *
 *  Generated audio has exact offsets: seek to the verse with a 250 ms lead-in
 *  so its first word is not clipped. A LibriVox section has none, so the
 *  verse count stands in for time, landing 4 s early so the verse is not
 *  overshot. Anything under a second plays from the top — verse 0 is the
 *  chapter announcement. `verseCounts` is the book's per-chapter verse count. */
export function startMs(sec: Section, chapter: number, verse: number, durationMs: number, verseCounts: number[]): number {
  let ms: number;
  if (sec.offsets !== null && verse >= 1 && verse < sec.offsets.length) {
    ms = Math.max(0, sec.offsets[verse] - 250);
  } else {
    let before = 0;
    let total = 0;
    for (let c = sec.first - 1; c < sec.last; c++) {
      const n = verseCounts[c] ?? 0;
      if (c < chapter) before += n;
      else if (c === chapter) before += Math.min(Math.max(verse, 0), n);
      total += n;
    }
    ms = total > 0 && Number.isFinite(durationMs) ? (durationMs * before) / total - 4000 : 0;
  }
  return ms > 1000 ? ms : 0;
}

/** The verse (0-based) sounding at `posMs`: the last offset at or before it. */
export function verseAt(offsets: number[], posMs: number): number {
  let v = 0;
  for (let i = 0; i < offsets.length; i++) {
    if (offsets[i] <= posMs) v = i;
    else break;
  }
  return v;
}

/** One word: [startMs, endMs, charStart, charEnd] into the DISPLAYED verse. */
export type Word = [number, number, number, number];
/** `.w.json` "v": per verse, its words, or null where the aligner could not
 *  place the verse (verse-level highlighting only there). */
export type Words = (Word[] | null)[];

/** The character range of the word sounding at `posMs`, or null in a pause
 *  or past the last word — a finished word must not stay lit. */
export function wordAt(words: Word[] | null | undefined, posMs: number): [number, number] | null {
  if (words == null) return null;
  let w = -1;
  for (let i = 0; i < words.length; i++) {
    if (words[i][0] <= posMs) w = i;
    else break;
  }
  return w >= 0 && posMs <= words[w][1] ? [words[w][2], words[w][3]] : null;
}

/** One poll of the word follower, as ReadingService does it: the highlight
 *  is re-decided only when the word INDEX changes, so a word stays lit
 *  through the pause after it until the next one starts (re-deciding every
 *  poll made the mark blink off between words — 53 of 100 polls in John 5).
 *  `last` is the previous index, -2 for a fresh verse. Returns the new index
 *  and range, or null when nothing changes. */
export function followWord(words: Word[] | null | undefined, posMs: number, last: number): { i: number; word: [number, number] | null } | null {
  if (words == null) return last === -1 ? null : { i: -1, word: null };
  let w = -1;
  for (let i = 0; i < words.length; i++) {
    if (words[i][0] <= posMs) w = i;
    else break;
  }
  if (w === last) return null;
  return { i: w, word: w >= 0 && posMs <= words[w][1] ? [words[w][2], words[w][3]] : null };
}

/** Parse a `.w.json` body. A malformed sidecar is null, never an error:
 *  the chapter simply falls back to verse-level following. */
export function parseWords(body: unknown): Words | null {
  if (body === null || typeof body !== "object" || !Array.isArray((body as { v?: unknown }).v)) return null;
  const v = (body as { v: unknown[] }).v;
  const ok = (w: unknown): w is Word => Array.isArray(w) && w.length >= 4 && w.slice(0, 4).every((n) => typeof n === "number");
  return v.map((verse) => (Array.isArray(verse) && verse.every(ok) ? (verse as Word[]) : null));
}

// ---- the bed: mood map + music pack -----------------------------------------

export const SILENCE = "silence";

/** `mood_map.json`: canonical KJV coordinates, all 0-BASED. */
export interface MoodMapData {
  bookDefault: string[];
  ranges: { book: number; from: number; to: number; mood: string }[];
  anchors: { book: number; chapter: number; mood: string; turns?: { verse: number; mood: string }[] }[];
  trackPin?: { book: number; chapter: number; track: string }[];
}

export interface Bed {
  mood: string;
  /** A pinned track id (music_index «pinned»), which wins over the mood. */
  track: string | null;
}

/** The bed for a passage in `translation`'s OWN numbering — MoodMap.moodFor.
 *
 *  ⚠ The map is keyed to KJV coordinates and the versemap is 1-based, so the
 *  passage is converted in (+1) and back out (-1). Skipping the pivot gives
 *  the Synodal Psalm 87 (= KJV 88, the darkest psalm) a cheerful bed; that
 *  was a real Android defect (2026-08-23). `verse` -1 = nothing playing yet,
 *  which resolves as the chapter's first verse. Resolution order, later
 *  winning: book default -> chapter range -> anchor (and its turns) -> pin. */
export function moodFor(map: MoodMapData, vm: VerseMapData | null, translation: string, book: number, chapter: number, verse: number): Bed {
  if (book < 0 || chapter < 0) return { mood: "narrative", track: null };
  const k = vm === null ? { c: chapter + 1, v: verse >= 0 ? verse + 1 : 1 } : toKjv(vm, translation, book, chapter + 1, verse >= 0 ? verse + 1 : 1);
  const kc = k.c - 1;
  const kv = k.v - 1;
  let mood = map.bookDefault[book] ?? "narrative";
  for (const r of map.ranges) if (r.book === book && kc >= r.from && kc <= r.to) mood = r.mood;
  const a = map.anchors.find((x) => x.book === book && x.chapter === kc);
  if (a !== undefined) {
    mood = a.mood;
    for (const t of a.turns ?? []) if (kv >= t.verse) mood = t.mood;
  }
  const pin = map.trackPin?.find((p) => p.book === book && p.chapter === kc);
  return { mood, track: pin?.track ?? null };
}

/** `music_index.json`. */
export interface MusicIndex {
  base: string;
  moods: Record<string, { f: string; t: string; ms: number; by: string }[]>;
  pinned?: Record<string, { f: string; t: string; ms: number; by: string }>;
  ambience?: { f: string; t: string; ms: number; by: string };
  credits?: string[];
}

/** Stable pick from a list: the same seed always draws the same item, so a
 *  chapter's bed does not reshuffle while it is read (MusicRepo.cachedFor). */
export function pick<T>(xs: T[], seed: number): T | null {
  if (xs.length === 0) return null;
  return xs[((seed % xs.length) + xs.length) % xs.length];
}

/** Which bundled track stands in for a mood: a hash of the NAME, so adding a
 *  mood never reshuffles the others (ReadingService.bundledFor). Kotlin Int
 *  arithmetic wraps at 32 bits; Math.imul and `| 0` do the same. */
export function bundledFor<T>(tracks: T[], mood: string): T | null {
  let h = 7;
  for (const ch of mood) h = (Math.imul(h, 31) + (ch.codePointAt(0) as number)) | 0;
  return pick(tracks, h);
}

/** The URL of the music bed for `bed`, best source first: a pinned track, then
 *  the mood's pack track for this chapter, then null (caller uses a bundled
 *  track). ⚠ Only SILENCE means no bed, and the caller checks it before this. */
export function packUrl(idx: MusicIndex | null, bed: Bed, book: number, chapter: number): string | null {
  if (idx === null) return null;
  const pinned = bed.track !== null ? idx.pinned?.[bed.track] : undefined;
  const t = pinned ?? pick(idx.moods[bed.mood] ?? [], book * 1000 + chapter);
  return t != null ? idx.base + "/" + t.f : null;
}

/** The book's cover plate for the lock screen, as BookArt.forBook picks it:
 *  `names` are the bookart/ file names (`<book>.webp`, `<book>_<n>.webp`);
 *  a book with several plates turns them over daily, offset by book so the
 *  library does not change in lockstep. null = no plate (Android draws one;
 *  the web shows the app icon). `day` = year * 1000 + day of year. */
export function plateFor(names: string[], book: number, day: number): string | null {
  const plates = names.filter((n) => Number(n.replace(/\.[^.]*$/, "").split("_")[0]) === book && /^\d/.test(n)).sort();
  if (plates.length === 0) return null;
  const n = plates.length;
  return plates[(((day + book * 7) % n) + n) % n];
}

/** Calendar.YEAR * 1000 + Calendar.DAY_OF_YEAR, local time. */
export function artDay(d: Date): number {
  const start = new Date(d.getFullYear(), 0, 1);
  const doy = Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime() - start.getTime()) / 86400000) + 1;
  return d.getFullYear() * 1000 + doy;
}
