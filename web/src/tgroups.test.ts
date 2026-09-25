// node --experimental-strip-types src/tgroups.test.ts
// Known-bad control: HEXAPLA_TGROUPS_BAD=1 must FAIL.
// Runs over the real manifest (HEXAPLA_WEB_DATA) — every translation, every language.
import { readFileSync } from "node:fs";
import { baseLang, endonym, groupTranslations } from "./tgroups.ts";
import type { Manifest } from "./types.ts";

const BAD = process.env.HEXAPLA_TGROUPS_BAD === "1";
const DATA = process.env.HEXAPLA_WEB_DATA;
if (DATA === undefined) throw new Error("set HEXAPLA_WEB_DATA to the web data/ directory");
let bad = 0;
const eq = (label: string, got: unknown, want: unknown): void => {
  const g = JSON.stringify(got), w = JSON.stringify(want);
  if (g !== w) bad++;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
};

const list = (JSON.parse(readFileSync(DATA + "/manifest.json", "utf8")) as Manifest).translations;
const ids = list.map((t) => t.id);

for (const ui of ["en", "ru", "zh-Hant", "sr-Latn", "xx"]) {
  const gs = groupTranslations(list, BAD && ui === "ru" ? "xx" : ui);
  const flat = gs.flatMap((g) => g.items.map((t) => t.id));
  eq(ui + ": every translation exactly once", [...flat].sort(), [...ids].sort());
  eq(ui + ": one group per base language", gs.length, new Set(list.map((t) => baseLang(t.lang))).size);
  eq(ui + ": every item sits in its own language's group", gs.every((g) => g.items.every((t) => baseLang(t.lang) === g.lang)), true);
  const want = list.some((t) => baseLang(t.lang) === baseLang(ui)) ? baseLang(ui) : baseLang(list[0].lang);
  eq(ui + ": first group", gs[0].lang, want);
  // Within a group the manifest order is kept.
  eq(ui + ": manifest order inside groups", gs.every((g) => g.items.every((t, i) => i === 0 || ids.indexOf(g.items[i - 1].id) < ids.indexOf(t.id))), true);
}

const zh = groupTranslations(list, "en").find((g) => g.lang === "zh");
eq("both Chinese scripts share a group", zh?.items.map((t) => t.lang).sort(), ["zh-Hans", "zh-Hant"]);
eq("ru endonym", endonym("ru"), "Русский");
eq("en endonym", endonym("en"), "English");
eq("de endonym", endonym("de"), "Deutsch");
eq("unknown code -> upper-case code", endonym("qqq"), "QQQ");
for (const l of new Set(list.map((t) => baseLang(t.lang)))) {
  const n = endonym(l);
  eq(l + " has a name, not its code", n !== l && n !== "" , true);
}

console.log(bad === 0 ? "\nALL PASS" : "\n" + bad + " FAILED");
process.exit(bad === 0 ? 0 : 1);
