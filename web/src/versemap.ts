// Verse-level versification map — a port of VerseMap.kt, run semantics exact.
//
// `data/versemap.json` (copied byte for byte from the app's assets) holds, per
// translation per book, runs of [kjvCh, kjvV0, kjvV1, transCh, transV0, transV1],
// ALL 1-BASED. Equal-length runs pair verse-for-verse; unequal runs are blocks
// (all their verses correspond together); transV0 > transV1 marks an omission
// (the translation has no verse for that KJV range). Anything not listed is
// identity. The KJV itself has no entry, so it is always identity.
//
// ⚠ This file is 1-based throughout, because the data is. The 0-based world
// starts in the caller; `route.ts` owns the URL boundary, this file owns none.
//
// Pure: no imports, no fetch — `parallel.test.ts` runs it under node directly.

export type Run = [number, number, number, number, number, number];
/** translation id -> book index (0-based, as a string key) -> runs. */
export type VerseMapData = Record<string, Record<string, Run[]>>;

/** A (chapter, verse) pair, 1-based. */
export interface Ref {
  c: number;
  v: number;
}

function runs(vm: VerseMapData, id: string, book: number): Run[] | undefined {
  return vm[id]?.[String(book)];
}

/** The translation's own (c, v) -> the KJV (c, v). Identity when unmapped.
 *  Same answer as VerseMap.kt `toKjv`: a verse inside a block maps to the
 *  block's first KJV verse. */
export function toKjv(vm: VerseMapData, id: string, book: number, c: number, v: number): Ref {
  for (const r of runs(vm, id, book) ?? []) {
    if (r[3] === c && r[4] <= r[5] && v >= r[4] && v <= r[5]) {
      return r[2] - r[1] === r[5] - r[4] ? { c: r[0], v: r[1] + (v - r[4]) } : { c: r[0], v: r[1] };
    }
  }
  return { c, v };
}

/** Every KJV verse a translation's (c, v) stands for: one for a paired verse,
 *  the whole KJV side of a block for a verse inside a block. `toKjv` gives the
 *  block's first verse only, which is right for a cross-reference and wrong
 *  for a parallel view — the rest of the block would silently vanish. */
export function kjvSpan(vm: VerseMapData, id: string, book: number, c: number, v: number): Ref[] {
  for (const r of runs(vm, id, book) ?? []) {
    if (r[3] === c && r[4] <= r[5] && v >= r[4] && v <= r[5]) {
      if (r[2] - r[1] === r[5] - r[4]) return [{ c: r[0], v: r[1] + (v - r[4]) }];
      const out: Ref[] = [];
      for (let kv = r[1]; kv <= r[2]; kv++) out.push({ c: r[0], v: kv });
      return out;
    }
  }
  return [{ c, v }];
}

/** KJV (c, v) -> the translation's positions: usually one, several for
 *  merged/moved verses, EMPTY for an omission. Same as VerseMap.kt `fromKjv`. */
export function fromKjv(vm: VerseMapData, id: string, book: number, c: number, v: number): Ref[] {
  const rs = runs(vm, id, book);
  if (rs === undefined) return [{ c, v }];
  const out: Ref[] = [];
  let matched = false;
  for (const r of rs) {
    if (r[0] === c && v >= r[1] && v <= r[2]) {
      matched = true;
      if (r[4] > r[5]) continue; // omitted verse
      if (r[2] - r[1] === r[5] - r[4]) out.push({ c: r[3], v: r[4] + (v - r[1]) });
      else for (let tv = r[4]; tv <= r[5]; tv++) out.push({ c: r[3], v: tv });
    }
  }
  return matched ? out : [{ c, v }];
}

/** KJV verses a translation OMITS whose run sits in the translation's chapter
 *  `c` — the rows a parallel view must insert, or the omission is invisible
 *  when this translation drives the chapter. */
export function omissionsIn(vm: VerseMapData, id: string, book: number, c: number): Ref[] {
  const out: Ref[] = [];
  for (const r of runs(vm, id, book) ?? []) {
    if (r[3] === c && r[4] > r[5]) {
      for (let kv = r[1]; kv <= r[2]; kv++) out.push({ c: r[0], v: kv });
    }
  }
  return out;
}
