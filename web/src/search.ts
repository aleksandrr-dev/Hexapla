// Verse search — a port of ReaderScreen.kt `searchNorm` / `searchTerms` /
// `scanBooks`. Keep the two in step: a reader who finds a verse on the phone
// must find it here with the same words, in the same order.
//
// Pure: no fetch, no DOM. search.worker.ts owns loading and caching.

/** Most hits collected before stopping (Android SEARCH_CAP). */
export const SEARCH_CAP = 300;

/** A query shorter than this (after trim) searches nothing. */
export const SEARCH_MIN = 2;

/** CJK variant fold, {char: key} (app/src/main/assets/cjk_fold.json, derived
 *  by tools/build_cjk_fold.py). Null until setFold: the worker sets it before
 *  normalising anything; the test loads it from disk. */
let fold: Map<string, string> | null = null;

export function setFold(table: Record<string, string> | null): void {
  fold = table === null ? null : new Map(Object.entries(table));
}

/** Every key in the fold table is at or above U+2E80 (CJK Radicals). */
const MAYBE_CJK = /[\u2E80-\u{3FFFF}]/u;

/** Case- and diacritic-insensitive form: strips accents, Hebrew niqqud,
 *  Greek breathing marks; then folds CJK variants (獨/独, 愛/爱) to one key,
 *  so a reader finds Meiji's old kanji and either CUV with the form they know. */
export function searchNorm(s: string): string {
  const n = s.normalize("NFD").replace(/\p{Mn}+/gu, "").toLowerCase();
  if (fold === null || !MAYBE_CJK.test(n)) return n;
  let out = "";
  for (const ch of n) out += fold.get(ch) ?? ch;
  return out;
}

/** Scripts written without spaces between words. Hangul is deliberately NOT
 *  here — Korean does use spaces, so it tokenizes like any Latin text. */
const SPACELESS = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u;
const SPACELESS_ONE = /^[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]$/u;
const LETTER_OR_DIGIT = /^[\p{L}\p{Nd}]$/u;

/** Query terms for the loose (out-of-order) fallback.
 *
 *  Space-delimited scripts split on spaces. A Chinese or Japanese run is
 *  decomposed into single CHARACTERS — never bigrams: reordering a phrase
 *  invents a bigram at the seam that is in no verse, and requiring every
 *  bigram found 1/16 of the queries the fallback exists for on Android, where
 *  characters found 16/16. Latin runs inside a CJK token are kept whole.
 *
 *  Iterates code points, where Kotlin iterates UTF-16 units; the two agree on
 *  every BMP character, and an astral Han character is kept as one term here
 *  instead of being dropped as two unmatched surrogates. */
export function searchTerms(q: string): string[] {
  const out = new Set<string>();
  for (const tok of q.split(" ")) {
    if (tok.trim() === "") continue;
    if (!SPACELESS.test(tok)) {
      out.add(tok);
      continue;
    }
    let run = "";
    for (const ch of tok) {
      if (SPACELESS_ONE.test(ch)) {
        if (run !== "") (out.add(run), (run = ""));
        out.add(ch);
      } else {
        if (LETTER_OR_DIGIT.test(ch)) run += ch;
        else if (run !== "") (out.add(run), (run = ""));
      }
    }
    if (run !== "") out.add(run);
  }
  return [...out];
}

export interface SearchHit {
  /** 0-based book, chapter, verse. */
  b: number;
  c: number;
  v: number;
  text: string;
}

/** A translation ready to scan: `text[b]` is a book's chapters (null = the
 *  translation has no such book), `norm` the same shape through searchNorm. */
export interface Corpus {
  text: (string[][] | null)[];
  norm: (string[][] | null)[];
}

export function toCorpus(books: (string[][] | null)[]): Corpus {
  return { text: books, norm: books.map((ch) => (ch === null ? null : ch.map((vs) => vs.map(searchNorm)))) };
}

/** Scan one translation. `phrase` and `words` are already normalised.
 *
 *  Exact phrase first, then every verse holding each term in any order (only
 *  when there is more than one term). Exact hits are always listed first. */
export function scanBooks(corpus: Corpus, phrase: string, words: string[], cap: number = SEARCH_CAP): SearchHit[] {
  if (cap <= 0) return [];
  const exact: SearchHit[] = [];
  const loose: SearchHit[] = [];
  for (let b = 0; b < corpus.norm.length; b++) {
    const chapters = corpus.norm[b];
    if (chapters === null) continue;
    for (let c = 0; c < chapters.length; c++) {
      const vs = chapters[c];
      for (let v = 0; v < vs.length; v++) {
        const n = vs[v];
        if (n.includes(phrase)) {
          exact.push({ b, c, v, text: corpus.text[b]![c][v] });
          if (exact.length >= cap) return exact;
        } else if (words.length > 1 && loose.length < cap && words.every((w) => n.includes(w))) {
          loose.push({ b, c, v, text: corpus.text[b]![c][v] });
        }
      }
    }
  }
  return exact.concat(loose).slice(0, cap);
}

/** The whole query path, as Android's LaunchedEffect runs it. */
export function search(corpus: Corpus, query: string, cap: number = SEARCH_CAP): SearchHit[] {
  const raw = query.trim();
  if (raw.length < SEARCH_MIN) return [];
  const q = searchNorm(raw);
  return scanBooks(corpus, q, searchTerms(q), cap);
}
