// Android `strings.xml` (27 locale folders) -> web/src/i18n/<tag>.json (P4 (e),
// WEB_APP_PLAN.md). Only the keys the web source asks for - `t("key")` in
// web/src - are written, so an unused Android string never ships and a key the
// web uses but the default strings.xml lacks is an error, not a blank label.
//
//   node --experimental-strip-types scripts/strings.ts          write
//   node --experimental-strip-types scripts/strings.ts --check  rc 1 if stale
//
// The Android files stay the one source: fix a translation there, re-run this.

import { readFileSync, readdirSync, statSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

/** values folder -> BCP 47 tag the web uses. `values` is English. */
export function tagOf(dir: string): string | null {
  if (dir === "values") return "en";
  if (dir === "values-b+zh+Hant") return "zh-Hant";
  if (dir === "values-sr") return "sr-Latn"; // the Android file is Latin script
  const m = /^values-([a-z]{2,3})$/.exec(dir);
  return m === null ? null : m[1];
}

const ENT: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };

/** One Android string resource value -> the text it displays. */
export function unescape(raw: string): string {
  let s = raw.replace(/&(amp|lt|gt|quot|apos);/g, (_, e: string) => ENT[e]);
  // A value wrapped in double quotes keeps its spaces verbatim ("2nd ").
  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) s = s.slice(1, -1);
  return s.replace(/\\(.)/g, (_, c: string) => (c === "n" ? "\n" : c === "t" ? "\t" : c));
}

export function parse(xml: string): Record<string, string> {
  const out: Record<string, string> = {};
  const re = /<string\s+name="([^"]+)"[^>]*>([\s\S]*?)<\/string>/g;
  for (let m = re.exec(xml); m !== null; m = re.exec(xml)) out[m[1]] = unescape(m[2]);
  return out;
}

function walk(dir: string, acc: string[] = []): string[] {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) walk(p, acc);
    else if (/\.tsx?$/.test(f) && !/\.test\.ts$/.test(f)) acc.push(p);
  }
  return acc;
}

/** Every key passed literally to t() in the web source. */
export function usedKeys(srcDir: string): string[] {
  const keys = new Set<string>();
  for (const f of walk(srcDir)) {
    const txt = readFileSync(f, "utf8");
    for (const m of txt.matchAll(/\bt\(\s*"([a-z0-9_]+)"/g)) keys.add(m[1]);
  }
  return [...keys].sort();
}

/** The web-only strings (`w_` keys): web/strings/<tag>.json, one flat table
 *  per locale. Android has no such string, so the web keeps its own; a key
 *  here that Android also has would be two sources for one label. */
export function readWeb(webDir: string): Map<string, Record<string, string>> {
  const out = new Map<string, Record<string, string>>();
  for (const f of readdirSync(webDir).sort()) {
    const m = /^(.+)\.json$/.exec(f);
    if (m !== null) out.set(m[1], JSON.parse(readFileSync(join(webDir, f), "utf8")) as Record<string, string>);
  }
  return out;
}

/** The %N$s / %N$d slots a string asks for, sorted: a translation must ask
 *  for exactly the English ones, or t() fills the wrong hole. */
export const slots = (s: string): string[] => [...s.matchAll(/%\d+\$[sd]/g)].map((m) => m[0]).sort();

export function build(resDir: string, keys: string[], web: Map<string, Record<string, string>> = new Map()): Map<string, Record<string, string>> {
  const all = new Map<string, Record<string, string>>();
  const webEn = web.get("en") ?? {};
  const webKeys = keys.filter((k) => k in webEn);
  const droidKeys = keys.filter((k) => !(k in webEn));
  for (const d of readdirSync(resDir).sort()) {
    const tag = tagOf(d);
    const f = join(resDir, d, "strings.xml");
    if (tag === null || !statSync(join(resDir, d)).isDirectory()) continue;
    let xml: string;
    try {
      xml = readFileSync(f, "utf8");
    } catch {
      continue; // values-night and the like hold no strings
    }
    const s = parse(xml);
    const clash = Object.keys(webEn).filter((k) => k in s);
    if (clash.length > 0) throw new Error("web/strings keys Android also has: " + clash.join(", "));
    const o: Record<string, string> = {};
    for (const k of droidKeys) if (k in s) o[k] = s[k];
    const w = web.get(tag) ?? {};
    for (const k of webKeys) {
      if (!(k in w)) continue; // falls back to English at run time
      if (slots(w[k]).join() !== slots(webEn[k]).join()) throw new Error("web/strings/" + tag + ".json " + k + ": slots " + slots(w[k]).join() + " but English has " + slots(webEn[k]).join());
      o[k] = w[k];
    }
    all.set(tag, Object.fromEntries(Object.entries(o).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))));
  }
  const en = all.get("en");
  if (en === undefined) throw new Error("no default values/strings.xml under " + resDir);
  const missing = keys.filter((k) => !(k in en));
  if (missing.length > 0) throw new Error("t() keys in neither values/strings.xml nor web/strings/en.json: " + missing.join(", "));
  const stray = [...web.keys()].filter((t) => !all.has(t));
  if (stray.length > 0) throw new Error("web/strings files for no Android locale: " + stray.join(", "));
  return all;
}

export const serialise = (o: Record<string, string>): string => JSON.stringify(o, null, 1) + "\n";

const main = process.argv[1]?.replace(/\\/g, "/").endsWith("scripts/strings.ts");
if (main) {
  const web = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
  const res = join(web, "..", "app", "src", "main", "res");
  const outDir = join(web, "src", "i18n");
  const check = process.argv.includes("--check");
  const all = build(res, usedKeys(join(web, "src")), readWeb(join(web, "strings")));
  // A key a locale lacks shows in English under that locale's menus (the
  // Russian Settings read «Music»: bed_kind_music was translated into Farsi
  // only). Named here, and --check fails on it.
  const enKeys = Object.keys(all.get("en") ?? {});
  let untranslated = 0;
  for (const [tag, o] of all) {
    const miss = enKeys.filter((k) => !(k in o));
    untranslated += miss.length;
    if (miss.length > 0) console.log("UNTRANSLATED " + tag + ": " + miss.join(", "));
  }
  mkdirSync(outDir, { recursive: true });
  let stale = 0;
  for (const [tag, o] of all) {
    const f = join(outDir, tag + ".json");
    const want = serialise(o);
    let have = "";
    try {
      have = readFileSync(f, "utf8");
    } catch {
      /* new locale */
    }
    if (have === want) continue;
    stale++;
    if (check) console.log("STALE " + f);
    else writeFileSync(f, want);
  }
  console.log(String(all.size) + " locales, " + String(Object.keys(all.get("en") ?? {}).length) + " keys" + (check ? ", " + String(stale) + " stale" : ", " + String(stale) + " written"));
  process.exit(check && (stale > 0 || untranslated > 0) ? 1 : 0);
}
