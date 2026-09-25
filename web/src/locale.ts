// UI language: which of the 27 Android locales to show, and Android's
// `%1$d` placeholders. Pure - `locale.test.ts` runs it under node; the
// tables themselves are loaded by i18n.ts.

/** [tag, name in its own language, right-to-left]. Tags match
 *  scripts/strings.ts tagOf(). */
export const LOCALES: [string, string, boolean][] = [
  ["en", "English", false],
  ["ar", "العربية", true],
  ["be", "Беларуская", false],
  ["cs", "Čeština", false],
  ["da", "Dansk", false],
  ["de", "Deutsch", false],
  ["el", "Ελληνικά", false],
  ["es", "Español", false],
  ["fa", "فارسی", true],
  ["fi", "Suomi", false],
  ["fr", "Français", false],
  ["he", "עברית", true],
  ["hu", "Magyar", false],
  ["hy", "Հայերեն", false],
  ["it", "Italiano", false],
  ["ja", "日本語", false],
  ["ka", "ქართული", false],
  ["lv", "Latviešu", false],
  ["nl", "Nederlands", false],
  ["pl", "Polski", false],
  ["pt", "Português", false],
  ["ru", "Русский", false],
  ["sr-Latn", "Srpski", false],
  ["sv", "Svenska", false],
  ["ta", "தமிழ்", false],
  ["zh", "简体中文", false],
  ["zh-Hant", "繁體中文", false],
];

const TAGS = new Set(LOCALES.map(([t]) => t));

export const isTag = (t: string): boolean => TAGS.has(t);

export const isRtl = (tag: string): boolean => LOCALES.some(([t, , r]) => t === tag && r);

/** The browser's language list -> the first one we have, else English. */
export function pickLocale(langs: readonly string[]): string {
  for (const raw of langs) {
    const l = raw.toLowerCase();
    const base = l.split("-")[0];
    if (base === "zh") return /hant|-tw|-hk|-mo/.test(l) ? "zh-Hant" : "zh";
    if (base === "sr") return "sr-Latn";
    if (base === "iw") return "he";
    if (TAGS.has(base)) return base;
  }
  return "en";
}

/** The stored preference ("auto" or a tag) -> the tag to show. */
export function uiTag(pref: string, langs: readonly string[]): string {
  return pref !== "auto" && TAGS.has(pref) ? pref : pickLocale(langs);
}

/** Android format: %1$s / %2$d take the n-th argument, %% is a percent sign. */
export function format(s: string, args: readonly (string | number)[]): string {
  return s.replace(/%(?:(\d+)\$)?([sd%])/g, (m, n: string | undefined, k: string) => {
    if (k === "%") return "%";
    const i = n === undefined ? 0 : Number(n) - 1;
    return i < args.length ? String(args[i]) : m;
  });
}
