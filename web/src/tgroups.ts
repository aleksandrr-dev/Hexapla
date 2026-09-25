// The translation picker, grouped by language (Android TranslationPicker.kt
// TranslationGroups): the reader's language first, then first appearance, so
// both Chinese scripts share one group. Unlike the app the groups are always
// open — on the web it is one single-select list, and most languages hold one
// translation, so a collapsed group would cost a tap to reveal one row.
import type { Translation } from "./types";

export interface Group {
  lang: string;
  name: string;
  items: Translation[];
}

/** «zh-Hant» -> «zh». */
export const baseLang = (tag: string): string => tag.split("-")[0].toLowerCase();

/** Native language name, capitalised in that language. ICU may lack a name
 *  for some codes, so fall back to the English name, then the bare code. */
export function endonym(lang: string): string {
  const named = (inLang: string): string | null => {
    try {
      const n = new Intl.DisplayNames([inLang], { type: "language", fallback: "none" }).of(lang);
      return n === undefined || n === "" || n.toLowerCase() === lang.toLowerCase() ? null : n;
    } catch {
      return null;
    }
  };
  const n = named(lang) ?? named("en");
  if (n === null) return lang.toUpperCase();
  let cap = n;
  try {
    cap = n.charAt(0).toLocaleUpperCase(lang) + n.slice(1);
  } catch {
    cap = n.charAt(0).toUpperCase() + n.slice(1);
  }
  return cap;
}

/** Groups `list` by base language; `ui` (the interface language tag) goes first. */
export function groupTranslations(list: readonly Translation[], ui: string): Group[] {
  const mine = baseLang(ui);
  const byLang = new Map<string, Translation[]>();
  for (const t of list) {
    const l = baseLang(t.lang);
    const g = byLang.get(l);
    if (g === undefined) byLang.set(l, [t]);
    else g.push(t);
  }
  const groups = [...byLang].map(([lang, items]) => ({ lang, name: endonym(lang), items }));
  const first = groups.findIndex((g) => g.lang === mine);
  if (first > 0) groups.unshift(...groups.splice(first, 1));
  return groups;
}
