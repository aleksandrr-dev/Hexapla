// The UI strings, from the Android app's own translations (scripts/strings.ts
// writes src/i18n/<tag>.json). English is bundled; any other locale is one
// small file fetched before the first render. A key the locale lacks falls
// back to English, as Android falls back to values/.

import en from "./i18n/en.json";
import { format, isRtl } from "./locale";

const tables = import.meta.glob<Record<string, string>>(["./i18n/*.json", "!./i18n/en.json"], { import: "default" });

let table: Record<string, string> = en;
let current = "en";

export type Key = keyof typeof en;

export function t(key: Key, ...args: (string | number)[]): string {
  const s = table[key] ?? en[key];
  return args.length === 0 && !s.includes("%") ? s : format(s, args);
}

export const locale = (): string => current;

/** Load a locale's table and set <html lang dir>. A failed load keeps
 *  English rather than blanking the interface. */
export async function setLocale(tag: string): Promise<void> {
  let next: Record<string, string> = en;
  if (tag !== "en") {
    const load = tables["./i18n/" + tag + ".json"];
    try {
      if (load !== undefined) next = await load();
    } catch {
      next = en;
    }
  }
  table = next;
  current = next === en ? "en" : tag;
  document.documentElement.lang = current;
  document.documentElement.dir = isRtl(current) ? "rtl" : "ltr";
}
