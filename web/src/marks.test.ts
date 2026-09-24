// Behaviour check for marks.ts against the REAL versemap, and for the backup
// file against the Android app's own format (Store.kt exportJson/importJson).
// Run: node --experimental-strip-types src/marks.test.ts   (from web/)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { readFileSync } from "node:fs";
import {
  EMPTY,
  bookmarkKey,
  bookmarksAt,
  bookmarkedIn,
  canonKey,
  decodeBookmark,
  fromBackup,
  placeIn,
  sortedBookmarks,
  toBackup,
  withBookmark,
  withHighlight,
  withNote,
  type Marks,
} from "./marks.ts";
import type { VerseMapData } from "./versemap.ts";

const vm = JSON.parse(readFileSync(new URL("../../app/src/main/assets/versemap.json", import.meta.url), "utf8")) as VerseMapData;

let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) bad += 1;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
}

const PS = 18;
const LUKE = 41;
const JOHN = 42;

// ---- canonical keys: KJV grid, 0-based, through the versemap -----------------
eq("kjv John 3:16 -> 42:2:15", canonKey(vm, "kjv", JOHN, 3, 16), "42:2:15");
// The Synodal psalter is one behind the KJV's here: its Ps 22 is the KJV's 23.
eq("syn Ps 22:1 -> KJV Ps 23:1", canonKey(vm, "syn", PS, 22, 1), "18:22:0");
eq("unmapped translation = identity", canonKey(vm, "zz_none", JOHN, 3, 16), "42:2:15");

// ---- bookmarks: Bookmark.encode/decode, 0-based native -------------------------
const bm = { id: "syn", book: PS, chapter: 21, verse: 0 }; // syn Ps 22:1
eq("encode", bookmarkKey(bm), "syn|18|21|0");
eq("decode round trip", decodeBookmark("syn|18|21|0"), bm);
eq("decode: 3 parts -> null", decodeBookmark("syn|18|21"), null);
eq("decode: negative -> null", decodeBookmark("syn|18|-1|0"), null);
eq("decode: junk id -> null", decodeBookmark("s y|18|1|0"), null);
eq("decode: float -> null", decodeBookmark("kjv|1|1.5|0"), null);

// Display-time pivot (BookmarksScreen.kt): same translation as stored; another
// through the KJV; an omission is null, not a neighbouring verse.
eq("place: same translation, no round trip", placeIn(vm, bm, "syn"), { chapter: 21, verse: 0 });
eq("place: syn Ps 22:1 read in kjv -> Ps 23:1", placeIn(vm, bm, "kjv"), { chapter: 22, verse: 0 });
eq("place: kjv Luke 17:36 in mei (omitted) -> null", placeIn(vm, { id: "kjv", book: LUKE, chapter: 16, verse: 35 }, "mei"), null);

let m: Marks = EMPTY;
m = withBookmark(m, "syn|18|21|0", true);
m = withBookmark(m, "kjv|42|2|15", true);
m = withBookmark(m, "kjv|42|2|15", true); // twice = once
eq("bookmark added once", m.bookmarks.length, 2);
eq("bookmarkedIn kjv Ps 23 (from syn)", [...bookmarkedIn(vm, m, "kjv", PS, 22)], [0]);
eq("bookmarkedIn kjv Ps 22 (none)", [...bookmarkedIn(vm, m, "kjv", PS, 21)], []);
eq("bookmarkedIn kjv John 3", [...bookmarkedIn(vm, m, "kjv", JOHN, 2)], [15]);
eq("bookmarksAt kjv Ps 23:1 finds the syn one", bookmarksAt(vm, m, "kjv", PS, 22, 0), ["syn|18|21|0"]);
eq("bookmarksAt kjv Ps 23:2 finds none", bookmarksAt(vm, m, "kjv", PS, 22, 1), []);
eq("bookmark removed", withBookmark(m, "kjv|42|2|15", false).bookmarks, ["syn|18|21|0"]);
eq("sorted: Psalms before John", sortedBookmarks(vm, withBookmark(EMPTY, "kjv|42|2|15", true)).map(bookmarkKey), ["kjv|42|2|15"]);
eq("sorted across translations", sortedBookmarks(vm, { ...EMPTY, bookmarks: ["kjv|42|2|15", "kjv|18|22|1", "syn|18|21|0", "bad"] }).map(bookmarkKey), [
  "syn|18|21|0",
  "kjv|18|22|1",
  "kjv|42|2|15",
]);

// ---- notes and highlights -------------------------------------------------------
eq("note trimmed", withNote(EMPTY, "42:2:15", "  so loved  ").notes, { "42:2:15": "so loved" });
eq("blank note removes", withNote(withNote(EMPTY, "42:2:15", "x"), "42:2:15", "   ").notes, {});
eq("highlight set", withHighlight(EMPTY, "42:2:15", 2).highlights, { "42:2:15": 2 });
eq("highlight cleared", withHighlight(withHighlight(EMPTY, "42:2:15", 2), "42:2:15", null).highlights, {});
eq("EMPTY is untouched", EMPTY, { notes: {}, highlights: {}, bookmarks: [] });

// ---- backup: Store.exportJson's document ------------------------------------------
const full: Marks = {
  notes: { "42:2:15": "so loved", "0:0:0": "beginning" },
  highlights: { "42:2:15": 1, "18:22:0": 3 },
  bookmarks: ["kjv|42|2|15", "syn|18|21|0"],
};
const text = toBackup(full, vm);
eq("export shape", JSON.parse(text), {
  version: 1,
  notes: { "0:0:0": "beginning", "42:2:15": "so loved" },
  highlights: { "18:22:0": 3, "42:2:15": 1 },
  bookmarks: ["syn|18|21|0", "kjv|42|2|15"],
});
eq("export is deterministic", toBackup({ ...full, bookmarks: full.bookmarks.slice().reverse() }, vm), text);
eq("export -> restore on empty = same marks", fromBackup(text, EMPTY)?.marks, {
  notes: { "0:0:0": "beginning", "42:2:15": "so loved" },
  highlights: { "18:22:0": 3, "42:2:15": 1 },
  bookmarks: ["syn|18|21|0", "kjv|42|2|15"],
});

// An Android backup, exactly as Store.exportJson writes one (voices and plans
// included): the marks come in, the rest is left alone, nothing breaks.
const android = JSON.stringify({
  version: 1,
  notes: { "42:2:15": "from the phone" },
  voices: { en: "en-us-x-sfg-local" },
  highlights: { "42:2:16": 0 },
  bookmarks: ["kjv|42|2|17"],
  plans: { mcheyne: ["1", "2"] },
});
const mine: Marks = { notes: { "42:2:15": "from the browser", "1:0:0": "kept" }, highlights: { "42:2:16": 3 }, bookmarks: ["kjv|0|0|0"] };
const r = fromBackup(android, mine);
eq("restore merges, incoming wins", r?.marks, {
  notes: { "42:2:15": "from the phone", "1:0:0": "kept" },
  highlights: { "42:2:16": 0 },
  bookmarks: ["kjv|0|0|0", "kjv|42|2|17"],
});
eq("restore counts", r?.read, { notes: 1, highlights: 1, bookmarks: 1 });
eq("restore: voices/plans are not 'skipped' marks", r?.skipped, 0);
eq("restore leaves the input alone", mine.notes["42:2:15"], "from the browser");

// Junk inside a real backup is skipped and counted, never stored.
const junk = fromBackup(JSON.stringify({ notes: { "a:b:c": "x", "1:2:3": 5, "1:2:4": " " }, highlights: { "1:2:3": 4, "1:2:4": 1.5, "1:2:5": "1", "1:2:6": 2 }, bookmarks: ["kjv|1|2", 7, "kjv|1|2|3"] }), EMPTY);
eq("junk: only the good entries", junk?.marks, { notes: {}, highlights: { "1:2:6": 2 }, bookmarks: ["kjv|1|2|3"] });
eq("junk: skipped counted", junk?.skipped, 8);

// Not a backup at all -> null, nothing applied.
eq("not JSON -> null", fromBackup("hello", full), null);
eq("an array -> null", fromBackup("[1,2]", full), null);
eq("other JSON (prefs file) -> null", fromBackup(JSON.stringify({ theme: "dark" }), full), null);

// Control: HEXAPLA_MARKS_BAD=1 asserts the pivot is identity (it is not: the
// Synodal psalter is shifted); =2 asserts a restore replaces instead of
// merging. Each run must FAIL.
if (process.env.HEXAPLA_MARKS_BAD === "1") eq("control 1 (must fail)", canonKey(vm, "syn", PS, 22, 1), "18:21:0");
if (process.env.HEXAPLA_MARKS_BAD === "2") eq("control 2 (must fail)", r?.marks.notes["1:0:0"], undefined);

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
