// Bookmarks, highlights and notes (WEB_APP_PLAN.md § 2, P2) — the reader's
// own marks, kept in this browser only and exportable as a file.
//
// ⚠ The shapes are the Android app's own (Store.kt), so a backup moves both
// ways between the phone app («Settings › Backup») and the browser:
//
//   notes       "book:chapter:verse" -> text        CANONICAL: KJV grid, 0-based
//   highlights  "book:chapter:verse" -> colour 0-3  CANONICAL: KJV grid, 0-based
//   bookmarks   "id|book|chapter|verse"             NATIVE: that translation's
//                                                    own numbering, 0-based
//
// Notes and highlights follow the verse across translations because their key
// is the KJV position (ReaderScreen.kt pivots through VerseMap on write and on
// lookup). A bookmark remembers the translation it was made in and is pivoted
// at display time, as BookmarksScreen.kt does. Do not «unify» the two: a file
// written here must restore on a phone, and one from a phone here.
//
// The backup is Store.exportJson's document: {version, notes, highlights,
// bookmarks} (+ voices and plans, which the web has no use for and leaves
// alone). Restoring MERGES, incoming wins per key, as Store.importJson does,
// so restoring on a browser that already has marks loses nothing.
//
// Pure: `marks.test.ts` runs it under node. The IndexedDB side is marksdb.ts.

import { fromKjv, toKjv, type VerseMapData } from "./versemap.ts";

/** Highlight colours, as Android's HighlightColors: amber, green, blue, pink. */
export const HL_COUNT = 4;

export interface Marks {
  notes: Record<string, string>;
  highlights: Record<string, number>;
  bookmarks: string[];
}

export const EMPTY: Marks = { notes: {}, highlights: {}, bookmarks: [] };

/** A bookmark, decoded; every index 0-based, in the translation's own numbering. */
export interface Bookmark {
  id: string;
  book: number;
  chapter: number;
  verse: number;
}

const ID_RE = /^[A-Za-z0-9_-]+$/;
const CANON_RE = /^\d+:\d+:\d+$/;

/** The canonical key of a translation's verse: `c` and `v` are 1-BASED (the
 *  versemap's numbering, as `Row` refs are), the key is 0-based like
 *  ReaderScreen.kt's `"$book:${kc - 1}:${kv - 1}"`. */
export function canonKey(vm: VerseMapData, id: string, book: number, c: number, v: number): string {
  const k = toKjv(vm, id, book, c, v);
  return String(book) + ":" + String(k.c - 1) + ":" + String(k.v - 1);
}

/** Bookmark.encode(): 0-based book, chapter, verse. */
export function bookmarkKey(b: Bookmark): string {
  return b.id + "|" + String(b.book) + "|" + String(b.chapter) + "|" + String(b.verse);
}

function nat(s: string): number | null {
  return /^\d+$/.test(s) ? Number(s) : null;
}

/** Bookmark.decode(), stricter: a malformed one is null, not a guess. */
export function decodeBookmark(s: string): Bookmark | null {
  const p = s.split("|");
  if (p.length !== 4 || !ID_RE.test(p[0])) return null;
  const [book, chapter, verse] = [nat(p[1]), nat(p[2]), nat(p[3])];
  if (book === null || chapter === null || verse === null) return null;
  return { id: p[0], book, chapter, verse };
}

/** Store.setNote: a blank note removes it; the text is kept trimmed. */
export function withNote(m: Marks, key: string, text: string): Marks {
  const notes = { ...m.notes };
  if (text.trim() === "") delete notes[key];
  else notes[key] = text.trim();
  return { ...m, notes };
}

/** Store.setHighlight: null clears. */
export function withHighlight(m: Marks, key: string, colour: number | null): Marks {
  const highlights = { ...m.highlights };
  if (colour === null) delete highlights[key];
  else highlights[key] = colour;
  return { ...m, highlights };
}

export function withBookmark(m: Marks, key: string, on: boolean): Marks {
  const rest = m.bookmarks.filter((b) => b !== key);
  return { ...m, bookmarks: on ? [...rest, key] : rest };
}

/** Where a bookmark lands in `primary`: 0-based {chapter, verse}, or null when
 *  that translation has no such verse (an omission, a shorter canon). Same
 *  translation: as stored, no round trip (a block would not come back
 *  verse-exact). Otherwise through the KJV backbone, first position. */
export function placeIn(vm: VerseMapData, b: Bookmark, primary: string): { chapter: number; verse: number } | null {
  if (b.id === primary) return { chapter: b.chapter, verse: b.verse };
  const k = toKjv(vm, b.id, b.book, b.chapter + 1, b.verse + 1);
  const at = fromKjv(vm, primary, b.book, k.c, k.v)[0];
  return at === undefined ? null : { chapter: at.c - 1, verse: at.v - 1 };
}

/** 0-based verses of `primary`'s chapter that carry a bookmark (from any
 *  translation), as ReaderScreen.kt's `bookmarkedVerses`. */
export function bookmarkedIn(vm: VerseMapData, m: Marks, primary: string, book: number, chapter: number): Set<number> {
  const out = new Set<number>();
  for (const s of m.bookmarks) {
    const b = decodeBookmark(s);
    if (b === null || b.book !== book) continue;
    const at = placeIn(vm, b, primary);
    if (at !== null && at.chapter === chapter) out.add(at.verse);
  }
  return out;
}

/** The stored bookmarks that land on `id`'s 0-based (chapter, verse) — made
 *  there or in any other translation. Removing a bookmark removes these. */
export function bookmarksAt(vm: VerseMapData, m: Marks, id: string, book: number, chapter: number, verse: number): string[] {
  return m.bookmarks.filter((s) => {
    const b = decodeBookmark(s);
    if (b === null || b.book !== book) return false;
    const at = placeIn(vm, b, id);
    return at !== null && at.chapter === chapter && at.verse === verse;
  });
}

/** Bookmarks in true verse order across translations (BookmarksScreen.kt):
 *  by book, then by KJV position. Undecodable entries are left out. */
export function sortedBookmarks(vm: VerseMapData, m: Marks): Bookmark[] {
  const pos = (b: Bookmark) => {
    const k = toKjv(vm, b.id, b.book, b.chapter + 1, b.verse + 1);
    return b.book * 1e6 + k.c * 1000 + k.v;
  };
  return m.bookmarks
    .map(decodeBookmark)
    .filter((b): b is Bookmark => b !== null)
    .sort((x, y) => pos(x) - pos(y));
}

/** A canonical key, split: 0-based book, chapter, verse. */
export function parseCanon(key: string): [number, number, number] | null {
  if (!CANON_RE.test(key)) return null;
  const [b, c, v] = key.split(":").map(Number);
  return [b, c, v];
}

/** Canonical keys in Bible order. */
export function sortedCanon(keys: string[]): string[] {
  const n = (k: string) => {
    const p = parseCanon(k);
    return p === null ? Number.MAX_SAFE_INTEGER : p[0] * 1e6 + p[1] * 1000 + p[2];
  };
  return keys.slice().sort((x, y) => n(x) - n(y));
}

/** The backup file's text: Store.exportJson's shape, keys in Bible order so
 *  two exports of the same marks are byte-identical. */
export function toBackup(m: Marks, vm: VerseMapData): string {
  const notes: Record<string, string> = {};
  for (const k of sortedCanon(Object.keys(m.notes))) notes[k] = m.notes[k];
  const highlights: Record<string, number> = {};
  for (const k of sortedCanon(Object.keys(m.highlights))) highlights[k] = m.highlights[k];
  const bookmarks = sortedBookmarks(vm, m).map(bookmarkKey);
  return JSON.stringify({ version: 1, notes, highlights, bookmarks }, null, 2);
}

export interface Restored {
  marks: Marks;
  /** Entries read from the file, per kind. */
  read: { notes: number; highlights: number; bookmarks: number };
  /** Entries the file held that are not marks this app can use. */
  skipped: number;
}

function isObj(x: unknown): x is Record<string, unknown> {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

/** Merge a backup file into `into`, incoming winning per key (Store.importJson).
 *  Null when the text is not a backup at all — nothing is half-applied. */
export function fromBackup(text: string, into: Marks): Restored | null {
  let o: unknown;
  try {
    o = JSON.parse(text);
  } catch {
    return null;
  }
  if (!isObj(o)) return null;
  const hasAny = isObj(o.notes) || isObj(o.highlights) || Array.isArray(o.bookmarks);
  if (!hasAny) return null;
  let skipped = 0;
  const read = { notes: 0, highlights: 0, bookmarks: 0 };
  const notes = { ...into.notes };
  if (isObj(o.notes)) {
    for (const [k, v] of Object.entries(o.notes)) {
      if (CANON_RE.test(k) && typeof v === "string" && v.trim() !== "") {
        notes[k] = v.trim();
        read.notes += 1;
      } else skipped += 1;
    }
  }
  const highlights = { ...into.highlights };
  if (isObj(o.highlights)) {
    for (const [k, v] of Object.entries(o.highlights)) {
      if (CANON_RE.test(k) && typeof v === "number" && Number.isInteger(v) && v >= 0 && v < HL_COUNT) {
        highlights[k] = v;
        read.highlights += 1;
      } else skipped += 1;
    }
  }
  const bookmarks = into.bookmarks.slice();
  if (Array.isArray(o.bookmarks)) {
    for (const s of o.bookmarks) {
      if (typeof s === "string" && decodeBookmark(s) !== null) {
        if (!bookmarks.includes(s)) bookmarks.push(s);
        read.bookmarks += 1;
      } else skipped += 1;
    }
  }
  return { marks: { notes, highlights, bookmarks }, read, skipped };
}
