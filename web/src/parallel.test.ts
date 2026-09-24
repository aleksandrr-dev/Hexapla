// Behaviour check for versemap.ts / parallel.ts / text.ts against the REAL
// app assets (not fixtures): the versemap and two real books.
// Run: node --experimental-strip-types src/parallel.test.ts   (from web/)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { readFileSync } from "node:fs";
import { chapterRows, type Row } from "./parallel.ts";
import { chapterRows2 } from "./parallel_legacy.test-ref.ts";
import { fromKjv, toKjv, type VerseMapData } from "./versemap.ts";
import { directionOf, dropCapEnd } from "./text.ts";

const ASSETS = new URL("../../app/src/main/assets/", import.meta.url);
const vm = JSON.parse(readFileSync(new URL("versemap.json", ASSETS), "utf8")) as VerseMapData;

// The build strips margin notes; the raw asset still has them, and these
// checks are about structure, not text, so the raw chapters are enough.
function book(file: string, i: number): string[][] {
  const d = JSON.parse(readFileSync(new URL("bibles/" + file, ASSETS), "utf8"));
  return (Array.isArray(d) ? d[i] : d.books[i]).chapters as string[][];
}

let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) bad += 1;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
}

const LUKE = 41;
const kjvLuke = book("en_kjv.json", LUKE);
const meiLuke = book("ja_meiji.json", LUKE);

// The map row itself (asserted by the P0.5 canvas too).
eq("mei omits KJV Luke 17:36", fromKjv(vm, "mei", LUKE, 17, 36), []);
eq("mei 17:36 is KJV 17:37", toKjv(vm, "mei", LUKE, 17, 36), { c: 17, v: 37 });
eq("kjv is identity", fromKjv(vm, "kjv", LUKE, 17, 36), [{ c: 17, v: 36 }]);

function brief(rows: Row[]): string[] {
  return rows.map((r) => {
    const a = r.a.kind === "gap" ? "-" : r.a.refs.map((x) => x.v).join("+");
    const o = r.others.map((s) => (s.kind === "gap" ? "|-" : "|" + s.refs.map((x) => x.v).join("+"))).join("");
    return a + o;
  });
}

// KJV driving, Meiji beside: KJV 36 has a gap on the right, 37 pairs with mei 36.
const kb = brief(chapterRows(vm, LUKE, "kjv", 17, kjvLuke, [{ id: "mei", book: meiLuke }]));
eq("KJV||mei rows", kb.length, 37);
eq("KJV||mei 35..37", kb.slice(34), ["35|35", "36|-", "37|36"]);

// Meiji driving, KJV beside: the KJV verse Meiji lacks must still appear.
const mb = brief(chapterRows(vm, LUKE, "mei", 17, meiLuke, [{ id: "kjv", book: kjvLuke }]));
eq("mei||KJV rows", mb.length, 37);
eq("mei||KJV 35..37", mb.slice(34), ["35|35", "-|36", "36|37"]);

// Single column: no inserted rows, one row per verse.
eq("mei alone rows", chapterRows(vm, LUKE, "mei", 17, meiLuke, []).length, 36);

// Every non-blank B verse of the chapter is shown (KJV||mei, whole Luke).
// Meiji keeps four BLANK slots in Luke where it merges two KJV verses; those
// are not verses and must not count as lost.
let lost = 0;
for (let c = 1; c <= kjvLuke.length; c++) {
  const seen = new Set<string>();
  for (const r of chapterRows(vm, LUKE, "kjv", c, kjvLuke, [{ id: "mei", book: meiLuke }])) {
    const b = r.others[0];
    if (b?.kind === "text") for (const x of b.refs) seen.add(String(x.c) + ":" + String(x.v));
  }
  for (let v = 1; v <= (meiLuke[c - 1]?.length ?? 0); v++) if (meiLuke[c - 1][v - 1].trim() !== "" && !seen.has(String(c) + ":" + String(v))) lost += 1;
}
eq("Luke: no Meiji verse lost beside the KJV", lost, 0);

eq("dir fa", directionOf("«خدا» God"), "rtl");
eq("dir en", directionOf("1 In the beginning"), "ltr");
eq("dir none", directionOf("12 — ."), null);
eq("dropcap plain", dropCapEnd("In the beginning"), 1);
eq("dropcap quote", dropCapEnd("“And"), 2);
eq("dropcap cjk none", dropCapEnd("太初に"), -1);
eq("dropcap one letter none", dropCapEnd("O"), -1);
eq("dropcap combining", dropCapEnd("Ábc"), 2);

// ---- N columns ------------------------------------------------------------
// With ONE other translation the N-column rows must be exactly the rows the
// two-column reader shipped with (frozen copy), for every chapter of every
// book, both directions, on pairs whose maps differ most from the KJV.
const FILES: Record<string, string> = { kjv: "en_kjv.json", mei: "ja_meiji.json", syn: "ru_synodal.json", wlc: "he_wlc.json", vul: "la_vulgata.json", lut: "de_luther.json" };
function allBooks(file: string): string[][][] {
  const d = JSON.parse(readFileSync(new URL("bibles/" + file, ASSETS), "utf8"));
  return (Array.isArray(d) ? d : d.books).map((b: { chapters: string[][] }) => b.chapters);
}
const BOOKS: Record<string, string[][][]> = {};
for (const [id, f] of Object.entries(FILES)) BOOKS[id] = allBooks(f);
function asTwo(rows: Row[]): string {
  return JSON.stringify(rows.map((r) => ({ key: r.key, a: r.a, b: r.others.length === 0 ? null : r.others[0], kjv: r.kjv })));
}
let compared = 0;
let differ = 0;
for (const [a, b] of [["kjv", "mei"], ["mei", "kjv"], ["kjv", "syn"], ["syn", "kjv"], ["wlc", "vul"], ["syn", "lut"]]) {
  const A = BOOKS[a];
  const B = BOOKS[b];
  for (let bk = 0; bk < Math.min(A.length, B.length); bk++) {
    for (let c = 1; c <= A[bk].length; c++) {
      compared += 1;
      const want = JSON.stringify(chapterRows2(vm, bk, a, c, A[bk], b, B[bk]));
      if (asTwo(chapterRows(vm, bk, a, c, A[bk], [{ id: b, book: B[bk] }])) !== want) differ += 1;
    }
  }
}
eq("two columns == frozen reference (" + String(compared) + " chapters)", differ, 0);
eq("alone == frozen reference, Psalms (syn)", asTwo(chapterRows(vm, 18, "syn", 23, BOOKS.syn[18], [])), JSON.stringify(chapterRows2(vm, 18, "syn", 23, BOOKS.syn[18], null, null)));

// Six columns: no verse of ANY column is lost, over whole books whose maps
// disagree (Psalms: Hebrew/Latin/Russian numbering; Luke: Meiji's merges).
const SIX = ["mei", "syn", "wlc", "vul", "lut"];
let lost6 = 0;
let rows6 = 0;
for (const bk of [18, 41, 44]) {
  const others = SIX.filter((id) => BOOKS[id][bk] !== undefined).map((id) => ({ id, book: BOOKS[id][bk] }));
  const seen = others.map(() => new Set<string>());
  for (let c = 1; c <= BOOKS.kjv[bk].length; c++) {
    for (const r of chapterRows(vm, bk, "kjv", c, BOOKS.kjv[bk], others)) {
      rows6 += 1;
      if (r.others.length !== others.length) lost6 += 1000;
      r.others.forEach((s, i) => s.kind === "text" && s.refs.forEach((x) => seen[i].add(String(x.c) + ":" + String(x.v))));
    }
  }
  // A verse of another translation counts as lost only if it has text and its
  // KJV home is a chapter of this book (a verse mapped outside the book is not
  // this book's to show).
  others.forEach((o, i) => {
    o.book.forEach((ch, ci) => ch.forEach((t, vi) => {
      if (t.trim() !== "" && !seen[i].has(String(ci + 1) + ":" + String(vi + 1))) {
        const k = toKjv(vm, o.id, bk, ci + 1, vi + 1);
        if (k.c >= 1 && k.c <= BOOKS.kjv[bk].length) { lost6 += 1; if (process.env.HEXAPLA_SHOW_LOST === "1") console.log("  lost", o.id, bk, ci + 1, vi + 1, "->kjv", k.c, k.v); }
      }
    }));
  });
}
eq("six columns (KJV + 5), Psalms/Luke/Acts: no verse lost in any column (" + String(rows6) + " rows)", lost6, 0);

// Known-bad control: pairing without the other-translation overlap test (the
// block rule) must diverge from the frozen reference somewhere.
if (process.env.HEXAPLA_PARALLEL_BAD === "2") {
  let div = 0;
  for (let c = 1; c <= BOOKS.syn[18].length; c++) {
    const legacy = chapterRows2(vm, 18, "syn", c, BOOKS.syn[18], "kjv", BOOKS.kjv[18]).length;
    const noBlocks = BOOKS.syn[18][c - 1].length + 0; // one row per verse: what a missing block rule gives
    if (legacy !== noBlocks) div += 1;
  }
  eq("CONTROL (must fail): no block rule matches the reference on Psalms", div, 0);
}

// Known-bad control: a map that forgets omissions must FAIL the lost-verse check.
if (process.env.HEXAPLA_PARALLEL_BAD === "1") {
  const broken: VerseMapData = JSON.parse(JSON.stringify(vm));
  broken.mei[String(LUKE)] = broken.mei[String(LUKE)].filter((r) => !(r[0] === 17 && r[1] === 36));
  eq("CONTROL (must fail): broken map keeps 17:36 gap", brief(chapterRows(broken, LUKE, "kjv", 17, kjvLuke, [{ id: "mei", book: meiLuke }])).slice(34), ["35|35", "36|-", "37|36"]);
}

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
