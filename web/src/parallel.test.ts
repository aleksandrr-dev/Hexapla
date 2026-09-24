// Behaviour check for versemap.ts / parallel.ts / text.ts against the REAL
// app assets (not fixtures): the versemap and two real books.
// Run: node --experimental-strip-types src/parallel.test.ts   (from web/)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { readFileSync } from "node:fs";
import { chapterRows, type Row } from "./parallel.ts";
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
    const b = r.b === null ? "" : r.b.kind === "gap" ? "|-" : "|" + r.b.refs.map((x) => x.v).join("+");
    return a + b;
  });
}

// KJV driving, Meiji beside: KJV 36 has a gap on the right, 37 pairs with mei 36.
const kb = brief(chapterRows(vm, LUKE, "kjv", 17, kjvLuke, "mei", meiLuke));
eq("KJV||mei rows", kb.length, 37);
eq("KJV||mei 35..37", kb.slice(34), ["35|35", "36|-", "37|36"]);

// Meiji driving, KJV beside: the KJV verse Meiji lacks must still appear.
const mb = brief(chapterRows(vm, LUKE, "mei", 17, meiLuke, "kjv", kjvLuke));
eq("mei||KJV rows", mb.length, 37);
eq("mei||KJV 35..37", mb.slice(34), ["35|35", "-|36", "36|37"]);

// Single column: no inserted rows, one row per verse.
eq("mei alone rows", chapterRows(vm, LUKE, "mei", 17, meiLuke, null, null).length, 36);

// Every non-blank B verse of the chapter is shown (KJV||mei, whole Luke).
// Meiji keeps four BLANK slots in Luke where it merges two KJV verses; those
// are not verses and must not count as lost.
let lost = 0;
for (let c = 1; c <= kjvLuke.length; c++) {
  const seen = new Set<string>();
  for (const r of chapterRows(vm, LUKE, "kjv", c, kjvLuke, "mei", meiLuke)) {
    if (r.b?.kind === "text") for (const x of r.b.refs) seen.add(String(x.c) + ":" + String(x.v));
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

// Known-bad control: a map that forgets omissions must FAIL the lost-verse check.
if (process.env.HEXAPLA_PARALLEL_BAD === "1") {
  const broken: VerseMapData = JSON.parse(JSON.stringify(vm));
  broken.mei[String(LUKE)] = broken.mei[String(LUKE)].filter((r) => !(r[0] === 17 && r[1] === 36));
  eq("CONTROL (must fail): broken map keeps 17:36 gap", brief(chapterRows(broken, LUKE, "kjv", 17, kjvLuke, "mei", meiLuke)).slice(34), ["35|35", "36|-", "37|36"]);
}

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
