// Study & Help against the Android source it ports, and against the data.
// Run: HEXAPLA_WEB_DATA=<data dir> node --experimental-strip-types src/topics.test.ts
// Exit 0 all pass, 1 any fail. Known-bad control: HEXAPLA_TOPICS_BAD=1 must FAIL
// (it moves one Kotlin ref by a verse, and resolves Synodal on the KJV's numbers).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { TOPICS, label, resolve, type TopicRef } from "./topics.ts";
import type { VerseMapData } from "./versemap.ts";
import type { Book } from "./types.ts";

const BAD = process.env.HEXAPLA_TOPICS_BAD === "1";
const DATA = process.env.HEXAPLA_WEB_DATA;
if (DATA === undefined) throw new Error("set HEXAPLA_WEB_DATA to the built data directory");
let bad = 0;
function eq(label: string, got: unknown, want: unknown): void {
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  const ok = g === w;
  if (!ok) bad += 1;
  console.log((ok ? "PASS " : "FAIL ") + label + (ok ? "" : "  got " + g + " want " + w));
}

// ---- The data is Android's, ref for ref (an independent parse of Bible.kt) ----
const kt = readFileSync(new URL("../../app/src/main/java/com/aleks/hexapla/Bible.kt", import.meta.url), "utf8");
const body = kt.slice(kt.indexOf("object Topics {"), kt.indexOf("\n}\n", kt.indexOf("object Topics {")));
const lists: Record<string, [string, TopicRef[]][]> = {};
for (const part of body.split(/\n    val /).slice(1)) {
  const name = /^(\w+) =/.exec(part)?.[1] ?? "?";
  lists[name] = [...part.matchAll(/Topic\(R\.string\.(\w+), listOf\(([\s\S]*?)\)\)/g)].map((m) => [
    m[1],
    [...m[2].matchAll(/VerseRef\((\d+), (\d+), (\d+), (\d+)\)/g)].map((r) => [1, 2, 3, 4].map((i) => Number(r[i])) as TopicRef),
  ]);
}
if (BAD) lists.help[0][1][0] = [lists.help[0][1][0][0], lists.help[0][1][0][1], lists.help[0][1][0][2] + 1, lists.help[0][1][0][3] + 1];
const key = (s: string): string => s;
const ours = Object.fromEntries(Object.entries(TOPICS).map(([k, v]) => [k, v.map((tp) => [tp.title(key), tp.refs])]));
eq("TOPICS == Bible.kt Topics (lists, titles, refs)", ours, lists);
eq("27 topics, 137 refs", [Object.values(TOPICS).flat().length, Object.values(TOPICS).flat().reduce((a, tp) => a + tp.refs.length, 0)], [27, 137]);
const xml = readFileSync(new URL("../../app/src/main/res/values/strings.xml", import.meta.url), "utf8");
const missing = Object.values(TOPICS).flat().map((tp) => tp.title(key)).filter((k) => !xml.includes('name="' + k + '"'));
eq("every title is an Android string", missing, []);

// ---- Resolution ----
const vm = JSON.parse(readFileSync(join(DATA, "versemap.json"), "utf8")) as VerseMapData;
const book = (id: string, b: number): Book | undefined => {
  try {
    return JSON.parse(readFileSync(join(DATA, id, String(b) + ".json"), "utf8")) as Book;
  } catch {
    return undefined;
  }
};

const rom = book("kjv", 44);
const r323 = resolve(vm, "kjv", [44, 2, 22, 22], rom);
eq("KJV Rom 3:23", r323 === null ? null : [label(rom!.name, r323), r323.text.startsWith("For all have sinned")], ["Romans 3:23", true]);
const r109 = resolve(vm, "kjv", [44, 9, 8, 9], rom);
eq("a range labels with an en dash", r109 === null ? null : label(rom!.name, r109), "Romans 10:9–10");

// Synodal's LXX psalter: KJV Ps 103:8-14 is its Ps 102:8-14.
const syn = book("syn", 18);
const ps = resolve(BAD ? {} : vm, "syn", [18, 102, 7, 13], syn);
eq("syn: KJV Ps 103:8-14 -> Пс 102:8-14", ps === null ? null : [ps.chapter, ps.from, ps.to, ps.text.startsWith("Щедр и милостив")], [101, 7, 13, true]);

// Synthetic: omission, missing book, a range that crosses into the next chapter.
const tiny: Book = { name: "B", chapters: [["a", "b", "c"], ["d", "e"]] };
eq("an omitted verse is null", resolve({ x: { "0": [[1, 2, 2, 1, 3, 2]] } }, "x", [0, 0, 1, 1], tiny), null);
eq("a book the translation lacks is null", resolve(vm, "kjv", [0, 0, 0, 0], undefined), null);
eq("a range ending in the next chapter reads to chapter end", resolve({ x: { "0": [[1, 3, 3, 2, 1, 1]] } }, "x", [0, 0, 0, 2], tiny), { chapter: 0, from: 0, to: 2, text: "a b c" });
eq("blank verses are skipped", resolve({}, "kjv", [0, 0, 0, 2], { name: "B", chapters: [["a", " ", "c"]] })?.text, "a c");

// ---- Every ref resolves in the KJV (the web's starting translation and the fallback) ----
const unresolved: string[] = [];
for (const tp of Object.values(TOPICS).flat()) for (const r of tp.refs) if (resolve(vm, "kjv", r, book("kjv", r[0])) === null) unresolved.push(r.join(":"));
eq("all 137 refs resolve in the KJV", unresolved, []);

console.log(bad ? bad + " FAILED" : "all passed");
process.exit(bad ? 1 : 0);
