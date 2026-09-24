// Off the main thread: loads every book of a translation ONCE, normalises it
// ONCE, and answers queries against that (search.ts does the matching).
//
// Protocol — in:  { id, t, q }   (q "" = load and cache only, no answer)
//            out: { id, kind: "progress", done, total }
//                 { id, kind: "hits", hits, ms }    ms = the scan alone
//                 { id, kind: "error", message }
// The page keeps the newest id and drops anything older.

import { loadBook, loadBooksIndex } from "./data";
import { search, toCorpus, type Corpus, type SearchHit } from "./search";

export type SearchReq = { id: number; t: string; q: string };
export type SearchMsg =
  | { id: number; kind: "progress"; done: number; total: number }
  | { id: number; kind: "hits"; hits: SearchHit[]; ms: number }
  | { id: number; kind: "error"; message: string };

/** Two translations resident at most (KJV ≈ 5 MB of text, twice that
 *  normalised): the one being read and the one before it. */
const KEEP = 2;
const corpora = new Map<string, Promise<Corpus>>();
const progress = new Map<string, (done: number, total: number) => void>();

function corpus(t: string): Promise<Corpus> {
  const hit = corpora.get(t);
  if (hit !== undefined) {
    corpora.delete(t);
    corpora.set(t, hit); // most recent last
    return hit;
  }
  const pending = (async () => {
    const idx = await loadBooksIndex(t);
    const total = idx.length;
    const books: (string[][] | null)[] = new Array(total).fill(null);
    let done = 0;
    let next = 0;
    // Eight at a time: enough to fill the pipe, few enough that progress moves.
    const lane = async () => {
      while (next < total) {
        const b = next++;
        books[b] = (await loadBook(t, b)).chapters;
        done += 1;
        progress.get(t)?.(done, total);
      }
    };
    await Promise.all(Array.from({ length: Math.min(8, total) }, lane));
    return toCorpus(books);
  })();
  corpora.set(t, pending);
  pending.catch(() => corpora.delete(t));
  while (corpora.size > KEEP) corpora.delete(corpora.keys().next().value as string);
  return pending;
}

self.onmessage = async (e: MessageEvent<SearchReq>) => {
  const { id, t, q } = e.data;
  const post = (m: SearchMsg) => (self as unknown as Worker).postMessage(m);
  progress.set(t, (done, total) => post({ id, kind: "progress", done, total }));
  try {
    const c = await corpus(t);
    if (q === "") return;
    const t0 = performance.now();
    const hits = search(c, q);
    post({ id, kind: "hits", hits, ms: performance.now() - t0 });
  } catch (err) {
    post({ id, kind: "error", message: String(err) });
  }
};
