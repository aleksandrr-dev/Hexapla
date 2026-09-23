// The deep link: `#/<translation>/<book>/<chapter>/<verse>` (WEB_APP_PLAN.md § 2).
//
// ⚠⚠ THE BOUNDARY — 1-BASED IN THE URL, 0-BASED INTERNAL ⚠⚠
//
// Every number in the hash is written for a human to read, and a human counts
// books, chapters and verses from 1. Every index this project computes with
// (Book lists, chapter arrays, verse arrays, `versemap.json`, narration
// directories) counts from 0. `parseRoute` is the ONLY place allowed to cross
// that line, and it crosses it exactly once, downwards: the returned Route is
// always 0-based. `buildHash` crosses it back, upwards, on the way out.
//
// This is the class of bug that bites this project: `narration/<set>/` is
// 0-indexed while `--verses` is 1-based, and the two look identical in a log.
// So: do not «fix» a route by adding 1 somewhere else, and do not clamp a
// malformed hash into range — return null and let the caller decide.

export interface Route {
  /** Translation id, e.g. "kjv". Never empty. */
  translation: string;
  /** 0-based book index. */
  book: number;
  /** 0-based chapter index. */
  chapter: number;
  /** 0-based verse index, or null when the link names a chapter only. */
  verse: number | null;
}

// Four segments, each optional after the translation: a link to a translation,
// a book, a chapter, a verse. Language tags and ids are [A-Za-z0-9_-] only
// (Bible.kt enforces the same alphabet on translation ids).
const ROUTE_RE = /^\/?([A-Za-z0-9_-]+)(?:\/(\d+))?(?:\/(\d+))?(?:\/(\d+))?$/;

// ⚠ "malformed" and "absent" must NOT share a sentinel. An earlier draft used
// `null` for both, so `#/kjv/1/1` (a legitimate chapter link with no verse)
// came back malformed and the whole route was dropped. BAD is the malformed
// sentinel; `null` means only "this link names no verse".
const BAD: unique symbol = Symbol("malformed segment");

function toSegment(segment: string): number | typeof BAD {
  // A present-but-useless part is an error. `/0` is not "the first chapter",
  // it is a human using the wrong numbering, and silently reading it as
  // chapter 1 hides the bug.
  const n = Number(segment);
  if (!Number.isInteger(n) || n < 1) return BAD;
  return n - 1;
}

/** A segment that defaults when absent (book, chapter). */
function toIndex(segment: string | undefined, fallback: number): number | typeof BAD {
  if (segment === undefined) return fallback;
  return toSegment(segment);
}

/** A segment that is simply absent when absent (verse). */
function toOptionalIndex(segment: string | undefined): number | null | typeof BAD {
  if (segment === undefined) return null;
  return toSegment(segment);
}

/** Parse a `location.hash` into 0-based indices, or null if it is malformed.
 *
 *  Accepts a leading "#" or not, with or without a leading "/". Missing
 *  trailing segments default to book 0 / chapter 0 / no verse. Anything else
 *  (a non-numeric segment, a 0, a negative) returns null — a silently-clamped
 *  route sends the reader to the wrong verse, which is worse than no route.
 */
export function parseRoute(hash: string): Route | null {
  let raw = hash.trim();
  if (raw.startsWith("#")) raw = raw.slice(1);
  const m = ROUTE_RE.exec(raw);
  if (!m) return null;
  const translation = m[1];
  const book = toIndex(m[2], 0);
  const chapter = toIndex(m[3], 0);
  const verse = toOptionalIndex(m[4]);
  if (book === BAD || chapter === BAD || verse === BAD) return null;
  return { translation, book, chapter, verse };
}

/** Build a hash from 0-based indices. Inverse of {@link parseRoute}. */
export function buildHash(route: Route): string {
  let out = "#/" + route.translation + "/" + String(route.book + 1);
  out += "/" + String(route.chapter + 1);
  if (route.verse !== null) out += "/" + String(route.verse + 1);
  return out;
}
