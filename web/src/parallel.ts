// The rows of a chapter, alone or beside up to five more translations — the
// hexapla — pivoting through the KJV backbone exactly as the Android split
// view does (VerseMap.kt).
//
// The primary translation (A) drives the chapter: its own chapter `c`, its own
// verse numbers. Each A verse is taken to its KJV span, and the span to every
// other translation's own positions. Two rows that share any KJV verse, or any
// verse of ANY other translation, are one row: that is a block, and splitting
// it would pair text that does not correspond. With several columns the block
// is the union — Meiji merging two verses beside a translation that splits
// them differently still yields one row every column agrees on. A KJV verse
// that A omits but another has gets its own row with A as a gap — otherwise,
// with A driving, that verse would vanish without a trace (Meiji driving, KJV
// beside it, Luke 17:36).
//
// With exactly one other translation this is the two-column algorithm the
// reader shipped with; `parallel.test.ts` holds a frozen copy of that and
// checks every chapter of every book gives identical rows.
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
  /** One per other translation, in the order given; empty when reading alone. */
  others: Side[];
  /** The KJV verses this row stands for. */
  kjv: Ref[];
}

/** Another translation beside A: its id and its whole book. */
export interface Other {
  id: string;
  book: string[][];
}

/** The most translations on screen at once: A and five more — six columns. */
export const MAX_COLUMNS = 6;

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
  /** Positions in each other translation, same order as `others`. */
  o: Ref[][];
  kjv: Ref[];
}

/**
 * @param aChapter  A's chapter, 1-based.
 * @param aBook     A's whole book (`chapters[c][v]`, 0-based arrays).
 * @param others    the translations beside A (at most MAX_COLUMNS - 1); their
 *                  whole books, because their positions can fall in other chapters.
 */
export function chapterRows(vm: VerseMapData, book: number, aId: string, aChapter: number, aBook: string[][], others: Other[]): Row[] {
  const verses = aBook[aChapter - 1] ?? [];
  const drafts: Draft[] = [];
  for (let v = 1; v <= verses.length; v++) {
    const span = kjvSpan(vm, aId, book, aChapter, v);
    const oRefs: Ref[][] = others.map((t) => {
      const got: Ref[] = [];
      for (const k of span) addUnique(got, fromKjv(vm, t.id, book, k.c, k.v));
      return got;
    });
    const prev = drafts[drafts.length - 1];
    if (prev !== undefined && (overlaps(prev.kjv, span) || oRefs.some((r, i) => overlaps(prev.o[i], r)))) {
      prev.a.push({ c: aChapter, v });
      addUnique(prev.kjv, span);
      oRefs.forEach((r, i) => addUnique(prev.o[i], r));
    } else {
      drafts.push({ a: [{ c: aChapter, v }], o: oRefs, kjv: span.slice() });
    }
  }

  // KJV verses A omits: only visible when there is another column to show them.
  if (others.length > 0) {
    for (const k of omissionsIn(vm, aId, book, aChapter)) {
      const d: Draft = { a: [], o: others.map((t) => fromKjv(vm, t.id, book, k.c, k.v)), kjv: [k] };
      const at = drafts.findIndex((x) => x.kjv.length > 0 && before(k, x.kjv[0]));
      if (at < 0) drafts.push(d);
      else drafts.splice(at, 0, d);
    }
  }

  const rows: Row[] = drafts.map((d, i) => ({
    key: d.a.length > 0 ? "a" + String(d.a[0].v) : "k" + String(d.kjv[0].c) + ":" + String(d.kjv[0].v) + "#" + String(i),
    a: sideOf(d.a, aBook),
    others: others.map((t, j) => sideOf(d.o[j], t.book)),
    kjv: d.kjv,
  }));
  // ReaderScreen.kt: a blank verse is dropped unless another side has text.
  return rows.filter((r) => r.a.kind === "text" || r.others.some((s) => s.kind === "text"));
}
