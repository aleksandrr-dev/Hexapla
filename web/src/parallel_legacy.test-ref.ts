// FROZEN REFERENCE — the two-column chapterRows the reader shipped with
// (commit f78d7f3). Never edit: parallel.test.ts checks the N-column version
// against it, chapter by chapter, over whole translations. Test-only; nothing
// in the app imports this file.

import { fromKjv, kjvSpan, omissionsIn, type Ref, type VerseMapData } from "./versemap.ts";

export type Side = { kind: "text"; refs: Ref[]; texts: string[] } | { kind: "gap" };
export interface Row2 {
  key: string;
  a: Side;
  b: Side | null;
  kjv: Ref[];
}

const same = (x: Ref, y: Ref) => x.c === y.c && x.v === y.v;
const before = (x: Ref, y: Ref) => x.c < y.c || (x.c === y.c && x.v < y.v);
function addUnique(into: Ref[], more: Ref[]): void {
  for (const r of more) if (!into.some((x) => same(x, r))) into.push(r);
}
const overlaps = (x: Ref[], y: Ref[]) => x.some((r) => y.some((s) => same(r, s)));
function sideOf(refs: Ref[], chapters: string[][]): Side {
  const kept: Ref[] = [];
  const texts: string[] = [];
  for (const r of refs) {
    const t = chapters[r.c - 1]?.[r.v - 1];
    if (t === undefined || t.trim() === "") continue;
    kept.push(r);
    texts.push(t);
  }
  return kept.length === 0 ? { kind: "gap" } : { kind: "text", refs: kept, texts };
}

export function chapterRows2(vm: VerseMapData, book: number, aId: string, aChapter: number, aBook: string[][], bId: string | null, bBook: string[][] | null): Row2[] {
  const verses = aBook[aChapter - 1] ?? [];
  const drafts: { a: Ref[]; b: Ref[]; kjv: Ref[] }[] = [];
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
  if (bId !== null) {
    for (const k of omissionsIn(vm, aId, book, aChapter)) {
      const d = { a: [] as Ref[], b: fromKjv(vm, bId, book, k.c, k.v), kjv: [k] };
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
  return rows.filter((r) => r.a.kind === "text" || (r.b !== null && r.b.kind === "text"));
}
