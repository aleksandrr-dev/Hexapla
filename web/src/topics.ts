// Study & Help (TopicsScreen.kt): the Good News walk, study guides, and
// Scriptures for life situations - the same topics, verses and order as
// Android's `Topics` (Bible.kt). The data below is generated from Bible.kt and
// `topics.test.ts` re-parses Bible.kt and checks it ref for ref.
//
// Refs are on the canonical KJV grid, ALL 0-BASED: [book, chapter, first
// verse, last verse]. `resolve` pivots both ends through the versemap into the
// reading translation's own numbering, exactly as TopicsScreen.kt resolveIn.
// Each title calls t() on its key literally, so scripts/strings.ts ships it.
//
// Pure: `topics.test.ts` runs it under node.

import type { Book } from "./types.ts";
import { fromKjv, type VerseMapData } from "./versemap.ts";

export type TopicRef = [number, number, number, number];
export interface Topic {
  // `any`: the app's t() takes only its own key union; this module stays pure.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  title: (t: (key: any) => string) => string;
  refs: TopicRef[];
}

export const TOPICS: { gospel: Topic[]; study: Topic[]; help: Topic[] } = {
  gospel: [
    { title: (t) => t("gospel_step1"), refs: [[44, 2, 22, 22], [44, 2, 9, 9]] },
    { title: (t) => t("gospel_step2"), refs: [[44, 5, 22, 22], [65, 20, 7, 7], [65, 19, 13, 14]] },
    { title: (t) => t("gospel_step3"), refs: [[44, 4, 7, 7], [42, 2, 15, 15], [45, 14, 2, 3]] },
    { title: (t) => t("gospel_step4"), refs: [[48, 1, 7, 8], [55, 2, 4, 4]] },
    { title: (t) => t("gospel_step5"), refs: [[43, 15, 29, 30], [42, 2, 17, 17]] },
    { title: (t) => t("gospel_step6"), refs: [[42, 5, 46, 46], [42, 9, 27, 27], [42, 2, 35, 35]] },
    { title: (t) => t("gospel_step7"), refs: [[44, 9, 8, 12]] },
  ],
  study: [
    { title: (t) => t("topic_salvation"), refs: [[43, 3, 11, 11], [42, 13, 5, 5], [46, 4, 16, 16], [46, 4, 20, 20], [59, 0, 17, 18], [47, 1, 15, 15], [57, 6, 24, 24]] },
    { title: (t) => t("topic_prayer"), refs: [[39, 5, 4, 12], [49, 3, 5, 6], [51, 4, 15, 17], [58, 4, 12, 15], [41, 17, 0, 7], [61, 4, 13, 14]] },
    { title: (t) => t("topic_faith"), refs: [[57, 10, 0, 5], [44, 9, 15, 16], [58, 1, 1, 7], [39, 16, 19, 19], [40, 8, 22, 23], [46, 4, 6, 6]] },
    { title: (t) => t("topic_love"), refs: [[45, 12, 0, 12], [61, 3, 6, 20], [42, 12, 33, 34], [44, 7, 37, 38], [59, 3, 7, 7], [21, 7, 5, 6]] },
    { title: (t) => t("topic_forgiveness"), refs: [[39, 5, 13, 14], [39, 17, 20, 21], [48, 3, 31, 31], [50, 2, 12, 13], [61, 0, 8, 8], [18, 102, 7, 13]] },
    { title: (t) => t("topic_holy_spirit"), refs: [[42, 13, 15, 16], [42, 15, 12, 14], [43, 0, 7, 7], [44, 7, 25, 26], [47, 4, 21, 22], [45, 2, 15, 16]] },
    { title: (t) => t("topic_wisdom"), refs: [[19, 2, 4, 6], [58, 0, 4, 4], [19, 8, 9, 9], [20, 11, 12, 13], [50, 1, 1, 2], [17, 27, 27, 27]] },
    { title: (t) => t("topic_hope"), refs: [[23, 28, 10, 12], [44, 14, 12, 12], [24, 2, 21, 25], [44, 4, 1, 4], [59, 0, 2, 3], [65, 20, 3, 4]] },
  ],
  help: [
    { title: (t) => t("help_anxiety"), refs: [[49, 3, 5, 6], [39, 5, 24, 33], [59, 4, 6, 6], [18, 54, 21, 21], [42, 13, 26, 26], [22, 25, 2, 3]] },
    { title: (t) => t("help_fear"), refs: [[22, 40, 9, 12], [18, 22, 0, 5], [18, 26, 0, 2], [54, 0, 6, 6], [61, 3, 17, 17], [4, 30, 5, 5]] },
    { title: (t) => t("help_grief"), refs: [[18, 33, 17, 18], [39, 4, 3, 3], [65, 20, 3, 3], [51, 3, 12, 17], [42, 10, 24, 25], [18, 146, 2, 2]] },
    { title: (t) => t("help_loneliness"), refs: [[4, 30, 7, 7], [18, 67, 4, 5], [22, 42, 1, 1], [39, 27, 19, 19], [57, 12, 4, 5], [18, 138, 6, 9]] },
    { title: (t) => t("help_anger"), refs: [[48, 3, 25, 26], [58, 0, 18, 19], [19, 14, 0, 0], [19, 15, 31, 31], [18, 36, 7, 8], [50, 2, 7, 7]] },
    { title: (t) => t("help_temptation"), refs: [[45, 9, 12, 12], [58, 0, 11, 14], [39, 25, 40, 40], [57, 3, 14, 15], [18, 118, 8, 10], [47, 4, 15, 15]] },
    { title: (t) => t("help_illness"), refs: [[58, 4, 13, 15], [18, 102, 1, 4], [23, 16, 13, 13], [18, 40, 2, 2], [59, 1, 23, 23], [46, 11, 8, 9]] },
    { title: (t) => t("help_finances"), refs: [[49, 3, 18, 18], [39, 5, 30, 32], [19, 2, 8, 9], [57, 12, 4, 4], [18, 36, 24, 24], [38, 2, 9, 9]] },
    { title: (t) => t("help_despair"), refs: [[18, 41, 10, 10], [18, 33, 16, 18], [22, 60, 0, 2], [46, 3, 7, 9], [18, 29, 4, 4], [39, 10, 27, 29]] },
    { title: (t) => t("help_guidance"), refs: [[19, 2, 4, 5], [18, 31, 7, 7], [22, 29, 20, 20], [18, 118, 104, 104], [58, 0, 4, 4], [19, 15, 8, 8]] },
    { title: (t) => t("help_marriage"), refs: [[0, 1, 23, 23], [48, 4, 24, 32], [45, 12, 3, 6], [50, 2, 13, 18], [19, 17, 21, 21], [20, 3, 8, 11]] },
    { title: (t) => t("help_guilt"), refs: [[18, 31, 0, 4], [44, 7, 0, 1], [61, 0, 8, 8], [22, 0, 17, 17], [18, 102, 11, 11], [46, 4, 16, 16]] },
  ],
};

/** A ref in one translation's own numbering, 0-based, with its text. */
export interface Resolved {
  chapter: number;
  from: number;
  to: number;
  text: string;
}

/** TopicsScreen.kt resolveIn: null when the translation lacks the book, the
 *  chapter, or omits the verse, or when the text comes out blank. */
export function resolve(vm: VerseMapData, id: string, ref: TopicRef, book: Book | undefined): Resolved | null {
  if (book === undefined) return null;
  const [b, c, v0, v1] = ref;
  // fromKjv is empty for a verse this translation omits, identity when unmapped.
  const start = fromKjv(vm, id, b, c + 1, v0 + 1)[0];
  if (start === undefined) return null;
  const ends = fromKjv(vm, id, b, c + 1, v1 + 1);
  const end = ends[ends.length - 1] ?? start;
  const chapter = start.c - 1;
  const verses = book.chapters[chapter];
  if (verses === undefined || verses.length === 0) return null;
  const clamp = (x: number, lo: number, hi: number): number => Math.min(Math.max(x, lo), hi);
  const from = clamp(start.v - 1, 0, verses.length - 1);
  // A range end that maps into the next chapter (rare) reads to chapter end.
  const to = end.c === start.c ? clamp(end.v - 1, from, verses.length - 1) : verses.length - 1;
  const text = verses.slice(from, to + 1).filter((s) => s.trim() !== "").join(" ");
  return text.trim() === "" ? null : { chapter, from, to, text };
}

/** "John 3:16" or "Romans 10:9–10" (en dash, as Android). */
export function label(bookName: string, r: Resolved): string {
  return bookName + " " + String(r.chapter + 1) + ":" + String(r.from + 1) + (r.to === r.from ? "" : "–" + String(r.to + 1));
}
