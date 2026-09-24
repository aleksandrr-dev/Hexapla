// Data access for the built `data/` tree. `fetch` + parse, nothing else:
// no IndexedDB, no service worker, no offline logic — those are P4
// (WEB_APP_PLAN.md § 3) and do not belong in the scaffold.
//
// All URLs are relative to `import.meta.env.BASE_URL`, which Vite fills in
// from `base` in vite.config.ts ("/Hexapla/app/"). Hard-coding a path here
// instead would work under `npm run dev` and 404 on Pages.

import type { Book, BooksIndex, Manifest } from "./types";
import type { VerseMapData } from "./versemap";
import type { GenIndex, LibriVoxIndex } from "./audio";

/** A failed fetch or an unparseable payload. Carries the HTTP status so the
 *  caller can tell a 404 (no such translation) from a 500 (broken deploy). */
export class DataError extends Error {
  readonly url: string;
  readonly status: number;

  constructor(url: string, status: number, message: string) {
    super(message);
    this.name = "DataError";
    this.url = url;
    this.status = status;
  }
}

// Keyed by absolute URL, so two translations with a same-named book file do
// not collide. Values are promises, not resolved data: two components asking
// for the manifest at first paint share one request, not two.
const cache = new Map<string, Promise<unknown>>();

// The deploy puts the app at <site>/app/ and the data at <site>/data/ — a
// SIBLING of the app, not inside it (.github/workflows/pages.yml). So every
// "data/..." path resolves one level above BASE_URL. The scaffold resolved it
// inside, and /Hexapla/app/data/manifest.json was a live 404 on 2026-09-24.
function url(path: string): string {
  const base = import.meta.env.BASE_URL;
  const app = base.endsWith("/") ? base : base + "/";
  return app.replace(/[^/]+\/$/, "") + path;
}

async function fetchJson<T>(path: string): Promise<T> {
  const href = url(path);
  const hit = cache.get(href);
  if (hit !== undefined) return hit as Promise<T>;
  const pending = (async (): Promise<T> => {
    const res = await fetch(href);
    if (!res.ok) {
      throw new DataError(href, res.status, "fetch " + href + " failed: HTTP " + String(res.status));
    }
    return (await res.json()) as T;
  })();
  cache.set(href, pending);
  // A failed load must not be cached as a permanent failure — the reader may
  // be offline for a second and come back.
  pending.catch(() => cache.delete(href));
  return pending;
}

/** `data/manifest.json` — the translation list and the licence credit text. */
export function loadManifest(): Promise<Manifest> {
  return fetchJson<Manifest>("data/manifest.json");
}

/** `data/<id>/books.json` — book names and per-chapter verse counts. */
export function loadBooksIndex(translation: string): Promise<BooksIndex> {
  return fetchJson<BooksIndex>("data/" + translation + "/books.json");
}

/** `data/<id>/<bookIndex>.json` — one book. `bookIndex` is 0-based. */
export function loadBook(translation: string, bookIndex: number): Promise<Book> {
  return fetchJson<Book>("data/" + translation + "/" + String(bookIndex) + ".json");
}

/** `data/versemap.json` — the versification map (versemap.ts). */
export function loadVersemap(): Promise<VerseMapData> {
  return fetchJson<VerseMapData>("data/versemap.json");
}

/** `data/audio_index.json` — LibriVox sections (audio.ts LibriVoxIndex). */
export function loadLibriVoxIndex(): Promise<LibriVoxIndex> {
  return fetchJson<LibriVoxIndex>("data/audio_index.json");
}

/** `data/audio_index_gen.json` — generated narration with verse offsets. */
export function loadGenIndex(): Promise<GenIndex> {
  return fetchJson<GenIndex>("data/audio_index_gen.json");
}

/** Drop every cached response. Exposed for tests and for a future "retry"
 *  affordance; nothing in the scaffold calls it. */
export function clearCache(): void {
  cache.clear();
}
