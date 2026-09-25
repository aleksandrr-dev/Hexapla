// node --experimental-strip-types src/locale.test.ts
// Known-bad control: HEXAPLA_LOCALE_BAD=1 must FAIL.
// Covers locale.ts and the strings.xml converter (scripts/strings.ts),
// including that the committed src/i18n/*.json are what it writes today.
import { readFileSync } from "node:fs";
import { LOCALES, defaultTranslation, format, isRtl, pickLocale, uiTag } from "./locale.ts";
import { build, parse, readWeb, serialise, tagOf, unescape, usedKeys } from "../scripts/strings.ts";

const BAD = process.env.HEXAPLA_LOCALE_BAD === "1";
let bad = 0;
const eq = (label: string, got: unknown, want: unknown): void => {
  const g = JSON.stringify(got), w = JSON.stringify(want);
  if (g !== w) bad++;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
};

// ---- picking ----
eq("ru-RU -> ru", pickLocale(["ru-RU", "en"]), "ru");
eq("unknown then de", pickLocale(["xx", "de-AT"]), "de");
eq("nothing known -> en", pickLocale(["xx", "yy"]), "en");
eq("zh-TW -> Traditional", pickLocale(["zh-TW"]), "zh-Hant");
eq("zh-Hant-HK -> Traditional", pickLocale(["zh-Hant-HK"]), "zh-Hant");
eq("zh-CN -> Simplified", pickLocale(["zh-CN"]), "zh");
eq("sr-Cyrl -> the Latin file we have", pickLocale(["sr-Cyrl-RS"]), "sr-Latn");
eq("old iw -> he", pickLocale(["iw"]), "he");
// ---- first translation (Bible.kt defaultPrimaryId) ----
eq("ru-RU opens the Synodal", defaultTranslation(["ru-RU", "en"]), BAD ? "kjv" : "syn");
eq("en-US first stays KJV", defaultTranslation(["en-US", "ru"]), "kjv");
eq("unmapped then de -> Luther", defaultTranslation(["xx", "de-AT"]), "lut");
eq("nothing mapped -> KJV", defaultTranslation(["xx"]), "kjv");
eq("no languages -> KJV", defaultTranslation([]), "kjv");
eq("zh-TW -> CUV", defaultTranslation(["zh-TW"]), "cuv");
eq("zh-Hant -> CUV", defaultTranslation(["zh-Hant"]), "cuv");
eq("zh-CN -> CUS", defaultTranslation(["zh-CN"]), "cus");
eq("nb -> Danish 1819", defaultTranslation(["nb-NO"]), "da19");
eq("sk -> Kralicka", defaultTranslation(["sk"]), "bkr");
eq("tg -> Persian", defaultTranslation(["tg"]), "mrt");
{
  // Parity with Bible.kt: every language in its `when` maps to the same id here.
  const kt = readFileSync(new URL("../../app/src/main/java/com/aleks/hexapla/Bible.kt", import.meta.url), "utf8");
  const body = kt.slice(kt.indexOf("fun defaultPrimaryId"), kt.indexOf("fun defaultSecondaryId"));
  const diffs: string[] = [];
  let n = 0;
  for (const m of body.matchAll(/^\s*((?:"[a-z]+",?\s*)+)->\s*"([a-z0-9]+)"/gm)) {
    for (const lang of m[1].match(/[a-z]+/g) ?? []) {
      n++;
      const got = defaultTranslation([lang]);
      if (got !== m[2]) diffs.push(lang + ": web " + got + ", Android " + m[2]);
    }
  }
  eq("Bible.kt languages read (sanity)", n >= 30, true);
  eq("every Bible.kt language maps the same", diffs, []);
}
eq("pref overrides browser", uiTag("fa", ["en-US"]), "fa");
eq("auto follows browser", uiTag("auto", ["ja-JP"]), "ja");
eq("unknown pref -> browser", uiTag("klingon", ["it"]), "it");
eq("rtl: fa ar he only", LOCALES.filter(([t]) => isRtl(t)).map(([t]) => t), ["ar", "fa", "he"]);
eq("27 locales", LOCALES.length, 27);

// ---- Android format ----
eq("%1$d", format("Chapter %1$d", [BAD ? 4 : 3]), "Chapter 3");
eq("%1$d of %2$d", format("%1$d of %2$d days completed", [2, 9]), "2 of 9 days completed");
eq("%% is a percent", format("Downloading audio… %1$d%%", [40]), "Downloading audio… 40%");
eq("missing arg left visible", format("Day %1$d", []), "Day %1$d");

// ---- strings.xml parsing ----
eq("folder tags", ["values", "values-b+zh+Hant", "values-sr", "values-ru", "values-night"].map(tagOf), ["en", "zh-Hant", "sr-Latn", "ru", null]);
eq("apostrophe escape", unescape("Webster\\'s"), "Webster's");
eq("quoted keeps space", unescape('"2nd "'), "2nd ");
eq("entity", unescape("Study &amp; Help"), "Study & Help");
eq("parse", parse('<resources><string name="a">x</string>\n<string name="b" tools:ignore="MissingTranslation">y\\\'z</string></resources>'), { a: "x", b: "y'z" });

// ---- the real files ----
const web = new URL("..", import.meta.url);
const res = new URL("../app/src/main/res/", web).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const src = new URL("src/", web).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const keys = usedKeys(src);
const webStrings = readWeb(new URL("strings/", web).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const all = build(res, keys, webStrings);
eq("27 locale files from Android", all.size, 27);
eq("every tag is a LOCALES tag", [...all.keys()].sort(), LOCALES.map(([t]) => t).sort());
eq("en has every key", Object.keys(all.get("en") ?? {}).length, keys.length);
eq("ru nav_settings", all.get("ru")?.nav_settings, "Настройки");
let stale: string[] = [];
for (const [tag, o] of all) {
  let have = "";
  try {
    have = readFileSync(new URL("i18n/" + tag + ".json", new URL("src/", web)), "utf8");
  } catch {
    /* missing */
  }
  if (have !== serialise(o)) stale.push(tag);
}
eq("committed src/i18n/*.json are fresh (run scripts/strings.ts)", stale, []);
let threw = "";
try {
  build(res, [...keys, "no_such_key_xyz"], webStrings);
} catch (e) {
  threw = String(e);
}
eq("a t() key Android lacks is an error", threw.includes("no_such_key_xyz"), true);

// Every locale translates every web-only key (a gap would fall back to
// English silently), and every w_free names «Hexapla», which linked() turns
// into the link. The BAD control drops one key and one «Hexapla».
const webEn = Object.keys(webStrings.get("en") ?? {});
const gaps: string[] = [];
const unlinked: string[] = [];
for (const [tag, o] of webStrings) {
  const t = BAD && tag === "de" ? { ...o, w_free: "Kostenlos.", w_back: undefined } : o;
  for (const k of webEn) if (typeof t[k] !== "string" || t[k] === "") gaps.push(tag + ":" + k);
  if (!String(t.w_free).includes("Hexapla")) unlinked.push(tag);
}
eq("web strings for all 27 locales", webStrings.size, 27);
eq("every locale has every w_ key", gaps, []);
eq("every w_free contains «Hexapla»", unlinked, []);

console.log(bad ? bad + " FAILED" : "all passed");
process.exit(bad ? 1 : 0);
