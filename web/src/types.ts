// The shape of `data/` as `tools/build_web_data.py` writes it. If this file and
// that script disagree, one of them is wrong — and the build script is the one
// with the controls, so change this file.
//
// Kept deliberately free of runtime code: it is the contract, not a layer.

/** One translation in `data/manifest.json`, under `translations`. */
export interface Translation {
  /** Translation id, e.g. "kjv" — the first path segment in `data/<id>/…`. */
  id: string;
  /** BCP-47 language tag, e.g. "en", "zh-Hant". */
  lang: string;
  /** Display label, as the Android picker shows it. */
  label: string;
  /** The source asset's filename, e.g. "en_kjv.json". Provenance, not a URL. */
  file: string;
  /** Number of books in this translation. */
  bookCount: number;
  /** Total verses across the whole translation. */
  verseCount: number;
}

/** `data/manifest.json`. `credits` is the `sources_text` body verbatim, and it
 *  is a LICENCE OBLIGATION (CC-BY / CC-BY-SA data) — display it, do not edit,
 *  reflow or shorten it. */
export interface Manifest {
  translations: Translation[];
  credits: string;
}

/** One book, as `data/<id>/<bookIndex>.json`. `chapters[c][v]` is the verse
 *  text; margin notes are already stripped by the build. */
export interface Book {
  name: string;
  chapters: string[][];
  /** The translator's margin notes the build stripped from the text, at
   *  "c:v" 0-based; absent when the book has none. */
  notes?: Record<string, string[]>;
}

/** One row of `data/<id>/books.json` — enough to navigate without fetching
 *  every book. `chapters[n]` is the verse count of chapter n (0-based). */
export interface BookIndexEntry {
  name: string;
  chapters: number[];
}

/** `data/<id>/books.json`. */
export type BooksIndex = BookIndexEntry[];
