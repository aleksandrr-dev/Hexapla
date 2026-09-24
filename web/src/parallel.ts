// The rows of a chapter, alone or beside a second translation, pivoting through
// the KJV backbone exactly as the Android split view does (VerseMap.kt).
//
// The primary translation (A) drives the chapter: its own chapter `c`, its own
// verse numbers. Each A verse is taken to its KJV span, and the span to the
// secondary's (B) own positions. Two rows that share any KJV verse or any B
// verse are one row: that is a block, and splitting it would pair text that
// does not correspond. A KJV verse that A omits but B has gets its own row
// with A as a gap — otherwise, with A driving, B's verse would vanish without
// a trace (Meiji driving, KJV beside it, Luke 17:36).
//
// 1-based throughout, like the data. Pure: `parallel.test.ts` runs it under node.

import { fromKjv, kjvSpan, omissionsIn, type Ref, type VerseMapData } from "./versemap.ts";

export type Side =
  | { kind: "text"; refs: Ref[]; texts: string[] }
  /** The translation has no verse here (an omission in the map). */
  | { kind: "gap" };

export interface Row {
  key: string;
  a: Side;
  /** null when there is no second translation. */
  b: Side | null;
  /** The KJV verses this row stands for. */
  kjv: Ref[];
}

function same(x: Ref, y: Ref): boolean {
  return x.c === y.c && x.v === y.v;
}

function before(x: Ref, y: Ref): boolean {
  return x.c < y.c || (x.c === y.c && x.v < y.v);
}

function addUnique(into: Ref[], more: Ref[]): void {
  for (const r of more) if (!into.some((x) => same(x, r))) into.push(r);
}

function overlaps(x: Ref[], y: Ref[]): boolean {
  return x.some((r) => y.some((s) => same(r, s)));
}

function sideOf(refs: Ref[], chapters: string[][]): Side {
  const kept: Ref[] = [];
  const texts: string[] = [];
  for (const r of refs) {
    const t = chapters[r.c - 1]?.[r.v - 1];
    // A blank slot is not a verse (Meiji keeps empty slots where it merges
    // two KJV verses); the Android reader skips it the same way.
    if (t === undefined || t.trim() === "") continue;
    kept.push(r);
    texts.push(t);
  }
  return kept.length === 0 ? { kind: "gap" } : { kind: "text", refs: kept, texts };
}

interface Draft {
  a: Ref[];
  b: Ref[];
  kjv: Ref[];
}

/**
 * @param aChapter  A's chapter, 1-based.
 * @param aBook     A's whole book (`chapters[c][v]`, 0-based arrays).
 * @param bId       the secondary translation, or null for a single column.
 * @param bBook     B's whole book; B's positions can fall in other chapters.
 */
export function chapterRows(
  vm: VerseMapData,
  book: number,
  aId: string,
  aChapter: number,
  aBook: string[][],
  bId: string | null,
  bBook: string[][] | null,
): Row[] {
  const verses = aBook[aChapter - 1] ?? [];
  const drafts: Draft[] = [];
  for (let v = 1; v <= verses.length; v++) {
    const span = kjvSpan(vm, aId, book, aChapter, v);
    const bRefs: Ref[] = [];
    if (bId !== null) for (const k of span) addUnique(bRefs, fromKjv(vm, bId, book, k.c, k.v));
    const prev = drafts[drafts.length - 1];
    if (prev !== undefined && (overlaps(prev.kjv, span) || overlaps(prev.b, bRefs))) {
      prev.a.push({ c: aChapter, v });
      addUnique(prev.kjv, span);
      addUnique(prev.b, bRefs);
    } else {
      drafts.push({ a: [{ c: aChapter, v }], b: bRefs, kjv: span.slice() });
    }
  }

  // KJV verses A omits: only visible when there is a second column to show them.
  if (bId !== null) {
    for (const k of omissionsIn(vm, aId, book, aChapter)) {
      const d: Draft = { a: [], b: fromKjv(vm, bId, book, k.c, k.v), kjv: [k] };
      const at = drafts.findIndex((x) => x.kjv.length > 0 && before(k, x.kjv[0]));
      if (at < 0) drafts.push(d);
      else drafts.splice(at, 0, d);
    }
  }

  const rows = drafts.map((d, i) => ({
    key: d.a.length > 0 ? "a" + String(d.a[0].v) : "k" + String(d.kjv[0].c) + ":" + String(d.kjv[0].v) + "#" + String(i),
    a: sideOf(d.a, aBook),
    b: bId === null || bBook === null ? null : sideOf(d.b, bBook),
    kjv: d.kjv,
  }));
  // ReaderScreen.kt: a blank verse is dropped unless the other side has text.
  return rows.filter((r) => r.a.kind === "text" || (r.b !== null && r.b.kind === "text"));
}
