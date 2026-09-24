// Behaviour check for webster.ts against the BUILT data tree and Bible.kt.
// Run: HEXAPLA_WEB_DATA=<build>/data node --experimental-strip-types src/webster.test.ts   (from web/)
// Exit 0 all pass, 1 any fail. No test runner, no dependency.
import { readFileSync } from "node:fs";
import { IRREGULAR, bucket, candidates, lookup, paragraphs, wordAt, wordSpanAt, type Bucket } from "./webster.ts";

const root = process.env.HEXAPLA_WEB_DATA;
if (root === undefined) {
  console.log("FAIL set HEXAPLA_WEB_DATA to the built data/ directory");
  process.exit(1);
}
const load = (b: string): Promise<Bucket> => Promise.resolve(JSON.parse(readFileSync(root + "/webster/" + b + ".json", "utf8")) as Bucket);

let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) bad += 1;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
}

// ---- drift: the irregular map is Bible.kt's, entry for entry, in order ---------
const kt = readFileSync(new URL("../../app/src/main/java/com/aleks/hexapla/Bible.kt", import.meta.url), "utf8");
const start = kt.indexOf("private val irregular = mapOf(");
const body = kt.slice(start, kt.indexOf("\n    )", start));
const pairs = [...body.matchAll(/"([^"]+)"\s+to\s+"([^"]+)"/g)].map((m) => [m[1], m[2]]);
eq("premise: Bible.kt irregular map found", start >= 0 && pairs.length > 100, true);
eq("IRREGULAR is Bible.kt's map, in order (" + String(pairs.length) + " entries)", Object.entries(IRREGULAR), pairs);

// ---- candidates: Webster1828.candidates, step for step --------------------------
eq("walketh", candidates("walketh"), ["WALKETH", "WALK", "WALKE"]);
eq("carrieth tries CARRY first", candidates("carrieth").slice(0, 2), ["CARRIETH", "CARRY"]);
eq("sitteth reaches SIT", candidates("sitteth").includes("SIT"), true);
eq("an irregular form stops there", candidates("Hath"), ["HATH", "HAVE"]);
eq("punctuation is trimmed", candidates("“brethren,”"), ["BRETHREN", "BROTHER"]);
eq("possessive drops 's (curly too)", candidates("Abraham’s").slice(0, 2), ["ABRAHAM'S", "ABRAHAM"]);
// The trim eats a trailing apostrophe first, so Kotlin's S' branch never fires either.
eq("plural possessive: trimmed, then -s", candidates("fathers'").slice(0, 2), ["FATHERS", "FATHER"]);
eq("-ly adverb", candidates("greatly").at(-1), "GREAT");
eq("a stem no longer than suffix+1 is not cut", candidates("bed"), ["BED"]);

// ---- lookup against the built dictionary -----------------------------------------
const hw = async (w: string) => (await lookup(w, load))?.[0] ?? null;
eq("walketh -> WALK", await hw("walketh"), "WALK");
eq("carrieth -> CARRY", await hw("carrieth"), "CARRY");
eq("hath -> HAVE", await hw("hath"), "HAVE");
eq("brethren is its own 1828 headword", await hw("brethren"), "BRETHREN");
eq("saith -> SAY (irregular, not a headword)", await hw("saith"), "SAY");
eq("loveth -> LOVE", await hw("loveth"), "LOVE");
eq("a proper name is not found", await hw("Abraham's"), null);
eq("buckets", [bucket("WALK"), bucket("abide"), bucket("'TIS"), bucket("")], ["W", "A", "_other", "_other"]);
let asked: string[] = [];
await lookup("walketh", (b) => { asked.push(b); return load(b); });
eq("one bucket fetched once per lookup", asked, ["W"]);
asked = [];
await lookup("zzzz", (b) => { asked.push(b); return load(b); });
eq("a miss fetches its bucket once", asked, ["Z"]);
const walk = (await lookup("walk", load))?.[1] ?? "";
eq("definition splits into paragraphs, first is the head", paragraphs(walk)[0].startsWith("WALK, v.i."), true);
eq("no empty paragraph", paragraphs("a\n\n b \n").length, 2);

// ---- wordAt: the word under a tap ---------------------------------------------
const t = "And Abraham's son walketh, saith the LORD.";
eq("offset inside a word", wordAt(t, 20), "walketh");
eq("offset just past a word", wordAt(t, 25), "walketh");
eq("inner apostrophe kept", wordAt(t, 6), "Abraham's");
eq("offset on a space between words", wordAt("a  b", 2), null);
eq("offset on punctuation after a space", wordAt("x .y", 2), null);
eq("trailing apostrophe is not in the word", wordAt("fathers' God", 3), "fathers");
eq("span of the word", wordSpanAt(t, 20), [18, 25]);

// Control: HEXAPLA_WEBSTER_BAD=1 drops one irregular entry (the drift a stale
// copy would carry); =2 asserts that a stemmed form resolves to itself. Both must FAIL.
if (process.env.HEXAPLA_WEBSTER_BAD === "1") eq("control 1 (must fail)", Object.entries(IRREGULAR).slice(1), pairs);
if (process.env.HEXAPLA_WEBSTER_BAD === "2") eq("control 2 (must fail)", await hw("walketh"), "WALKETH");

console.log(bad === 0 ? "all passed" : String(bad) + " FAILED");
process.exit(bad === 0 ? 0 : 1);
