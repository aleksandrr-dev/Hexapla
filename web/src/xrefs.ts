// Cross-references (openbible.info, CC BY — credited in sources_text): the
// Android asset `xrefs.json` as is, the strongest community-voted references,
// top 8 per verse (Bible.kt `Xrefs`).
//
// Both the key and the targets are on the canonical KJV grid, 0-based
// "book:chapter:verse" — the same key marks.ts uses for notes and highlights,
// so a selected row's `canonKey`s look straight up here. A target is shown at
// the reading translation's own position (ReaderScreen.kt XrefsDialog); a
// verse that translation omits is null, not the KJV number read as its own.

import { fromKjv, type VerseMapData } from "./versemap.ts";

export type XrefData = Record<string, string[]>;

/** A target: its KJV position (0-based), and where the reading translation
 *  has it (0-based), or null when that translation lacks the verse. */
export interface Xref {
  book: number;
  kjv: { chapter: number; verse: number };
  at: { chapter: number; verse: number } | null;
}

function parse(s: string): [number, number, number] | null {
  const p = s.split(":");
  if (p.length !== 3) return null;
  const n = p.map((x) => (/^\d+$/.test(x) ? Number(x) : -1));
  return n.some((x) => x < 0) ? null : [n[0], n[1], n[2]];
}

/** The references of a row: the union over its keys (a block row is several
 *  KJV verses), in order, each target once, never the row's own verses. */
export function xrefsFor(data: XrefData, vm: VerseMapData, keys: string[], primary: string): Xref[] {
  const own = new Set(keys);
  const seen = new Set<string>();
  const out: Xref[] = [];
  for (const k of keys) {
    for (const t of data[k] ?? []) {
      if (own.has(t) || seen.has(t)) continue;
      const p = parse(t);
      if (p === null) continue;
      seen.add(t);
      const pos = fromKjv(vm, primary, p[0], p[1] + 1, p[2] + 1)[0];
      out.push({ book: p[0], kjv: { chapter: p[1], verse: p[2] }, at: pos === undefined ? null : { chapter: pos.c - 1, verse: pos.v - 1 } });
    }
  }
  return out;
}
