// Behaviour check for xrefs.ts against the REAL xrefs.json and versemap.
// Run: node --experimental-strip-types src/xrefs.test.ts   (from web/)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { readFileSync } from "node:fs";
import { xrefsFor, type XrefData } from "./xrefs.ts";
import { canonKey } from "./marks.ts";
import type { VerseMapData } from "./versemap.ts";

const asset = (f: string) => JSON.parse(readFileSync(new URL("../../app/src/main/assets/" + f, import.meta.url), "utf8"));
const vm = asset("versemap.json") as VerseMapData;
const xr = asset("xrefs.json") as XrefData;

let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) bad += 1;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
}
const refs = (xs: ReturnType<typeof xrefsFor>) => xs.map((x) => x.book + ":" + (x.at === null ? "-" : x.at.chapter + ":" + x.at.verse));

const PS = 18;
const SONG = 21;

// ---- the asset as Android reads it: KJV grid, 0-based, top 8 in vote order ----
const gen = xrefsFor(xr, vm, [canonKey(vm, "kjv", 0, 1, 1)], "kjv");
eq("kjv Gen 1:1: 8 refs", gen.length, 8);
eq("kjv Gen 1:1: first is Heb 11:3", refs(gen)[0], "57:10:2");
eq("kjv Gen 1:1: then Isa 45:18, John 1:1", refs(gen).slice(1, 3), ["22:44:17", "42:0:0"]);
eq("no refs = empty, not an error", xrefsFor(xr, vm, ["65:21:99"], "kjv"), []);

// ---- the key comes through the versemap: syn Ps 22:1 is the KJV's Ps 23:1 ----
eq("syn Ps 22:1 looks up KJV Ps 23:1", refs(xrefsFor(xr, vm, [canonKey(vm, "syn", PS, 22, 1)], "kjv")), xr["18:22:0"].map((t) => t.split(":").join(":")));

// ---- a target is shown at the reading translation's own place ----------------
// KJV Ps 51 -> Ps 51:9 is a target; the Synodal has it at Ps 50:11.
const ps51 = xrefsFor(xr, vm, ["18:50:0"], "syn").find((x) => x.book === PS && x.kjv.chapter === 50 && x.kjv.verse === 8);
eq("KJV Ps 51:9 read in syn -> 50:11", ps51?.at, { chapter: 49, verse: 10 });
eq("... and keeps its KJV position", ps51?.kjv, { chapter: 50, verse: 8 });

// An omission is null, never the KJV number read as the Synodal's own:
// 1 Kings 4:32 -> Song 1:1, a verse the Synodal does not have.
const song = xrefsFor(xr, vm, ["10:3:31"], "syn").find((x) => x.book === SONG);
eq("syn lacks Song 1:1 -> at null", song?.at, null);
eq("kjv has it -> 1:1", xrefsFor(xr, vm, ["10:3:31"], "kjv").find((x) => x.book === SONG)?.at, { chapter: 0, verse: 0 });

// ---- a block row (several KJV verses) takes the union, each target once ------
const a = xr["0:0:0"];
const b = xr["0:0:1"];
const both = refs(xrefsFor(xr, vm, ["0:0:0", "0:0:1"], "kjv"));
const want = [...new Set([...a, ...b])];
eq("union in order, deduped", both, want);
eq("Isa 45:18 is in both, listed once", both.filter((r) => r === "22:44:17").length, 1);
// The row's own verses are not references to themselves.
// Gen 1:5 lists Gen 1:8 and Gen 1:8 lists Gen 1:5 (the premise is checked too).
eq("premise: Gen 1:5 alone lists Gen 1:8", refs(xrefsFor(xr, vm, ["0:0:4"], "kjv")).includes("0:0:7"), true);
const row58 = refs(xrefsFor(xr, vm, ["0:0:4", "0:0:7"], "kjv"));
eq("row Gen 1:5+8 lists neither of its own", row58.includes("0:0:7") || row58.includes("0:0:4"), false);

// ---- malformed data is dropped, not thrown on --------------------------------
eq("junk targets dropped", refs(xrefsFor({ k: ["1:2", "a:1:1", "1:-1:0", "0:0:1"] }, vm, ["k"], "kjv")), ["0:0:1"]);

// Controls: HEXAPLA_XREFS_BAD=1 asserts the KJV number stands in the Synodal
// (it does not: Ps 50:11); =2 asserts Isa 45:18 twice in the union. Must FAIL.
if (process.env.HEXAPLA_XREFS_BAD === "1") eq("control 1 (must fail)", ps51?.at, { chapter: 50, verse: 8 });
if (process.env.HEXAPLA_XREFS_BAD === "2") eq("control 2 (must fail)", both.filter((r) => r === "22:44:17").length, 2);

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
