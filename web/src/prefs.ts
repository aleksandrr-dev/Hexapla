// Per-reader conveniences kept in this browser only: the last position, the
// second translation, font size, theme. Nothing here identifies anyone, and
// nothing leaves the device (web/README.md house rule 4).
//
// Storage can be missing or throw (private windows, blocked site data), so
// every access is guarded and the reader works without it.

export type Theme = "auto" | "light" | "dark";
export type Mode = "a" | "both" | "b";
/** Split layout, as Android's «Split layout»; auto = side by side on a wide screen. */
export type Layout = "auto" | "side" | "stacked";

export interface Prefs {
  /** The last hash read, e.g. "#/kjv/43/3/16". */
  last: string | null;
  second: string | null;
  mode: Mode;
  fontSize: number;
  theme: Theme;
  layout: Layout;
}

const KEY = "hexapla.prefs.v1";

export const FONT_MIN = 14;
/** The app's slider max is 30sp; the P0.5 largest-font board is drawn at it. */
export const FONT_MAX = 30;

export const DEFAULTS: Prefs = { last: null, second: null, mode: "both", fontSize: 19, theme: "auto", layout: "auto" };

export function loadPrefs(): Prefs {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw === null) return { ...DEFAULTS };
    const p = JSON.parse(raw) as Partial<Prefs>;
    const size = typeof p.fontSize === "number" ? Math.min(FONT_MAX, Math.max(FONT_MIN, p.fontSize)) : DEFAULTS.fontSize;
    return {
      last: typeof p.last === "string" ? p.last : null,
      second: typeof p.second === "string" ? p.second : null,
      mode: p.mode === "a" || p.mode === "b" || p.mode === "both" ? p.mode : DEFAULTS.mode,
      fontSize: size,
      theme: p.theme === "light" || p.theme === "dark" || p.theme === "auto" ? p.theme : DEFAULTS.theme,
      layout: p.layout === "side" || p.layout === "stacked" || p.layout === "auto" ? p.layout : DEFAULTS.layout,
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function savePrefs(p: Prefs): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    // Storage unavailable: the reader still works, it just will not remember.
  }
}
