// Per-reader conveniences kept in this browser only: the last position, the
// translations read alongside, font size, theme. Nothing here identifies
// anyone, and nothing leaves the device (web/README.md house rule 4).
//
// Storage can be missing or throw (private windows, blocked site data), so
// every access is guarded and the reader works without it.
//
// Pure apart from loadPrefs/savePrefs: `prefs.test.ts` runs the rest under node.

export type Theme = "auto" | "light" | "dark";
/** Split layout, as Android's «Split layout»; auto = side by side when the
 *  columns fit, stacked otherwise. */
export type Layout = "auto" | "side" | "stacked";
/** What plays under the narration (Android «Background while listening»). */
export type BedKind = "music" | "fireside";

/** Translations beside the primary one: five, so six columns at most
 *  (`parallel.ts` MAX_COLUMNS). */
export const MAX_PARALLEL = 5;

export interface Prefs {
  /** The last hash read, e.g. "#/kjv/43/3/16". */
  last: string | null;
  /** Translation ids read alongside the primary one, in column order. */
  parallel: string[];
  /** "all", or the one translation id read alone (the Show bar). */
  show: string;
  fontSize: number;
  theme: Theme;
  layout: Layout;
  // ---- Listening: the Android `Store.kt` defaults (player.ts AudioPrefs) ----
  /** Reading speed, RATE_MIN-RATE_MAX. */
  rate: number;
  /** Continue to the next chapter at the end of one. */
  autoNext: boolean;
  /** Something plays underneath the narration. */
  bed: boolean;
  bedKind: BedKind;
  /** VOL_MIN-1, the slider position; loudness is its square. */
  bedVolume: number;
  /** «Same music throughout»: no mood matching. */
  uniformBed: boolean;
}

const KEY = "hexapla.prefs.v1";

export const FONT_MIN = 14;
/** The app's slider max is 30sp; the P0.5 largest-font board is drawn at it. */
export const FONT_MAX = 30;

export const RATE_MIN = 0.5;
export const RATE_MAX = 2;
export const VOL_MIN = 0.1;

export const DEFAULTS: Prefs = {
  last: null,
  parallel: [],
  show: "all",
  fontSize: 19,
  theme: "auto",
  layout: "auto",
  rate: 1,
  autoNext: true,
  bed: false,
  bedKind: "music",
  bedVolume: 0.45,
  uniformBed: false,
};

/** A stored number inside [lo, hi], or the default when it is not a number. */
function num(x: unknown, lo: number, hi: number, dflt: number): number {
  return typeof x === "number" && Number.isFinite(x) ? Math.min(hi, Math.max(lo, x)) : dflt;
}

function bool(x: unknown, dflt: boolean): boolean {
  return typeof x === "boolean" ? x : dflt;
}

const ID_RE = /^[A-Za-z0-9_-]+$/;

/** Valid ids only, no repeats, at most MAX_PARALLEL — whatever the source. */
export function cleanIds(xs: unknown[]): string[] {
  const out: string[] = [];
  for (const x of xs) {
    if (typeof x === "string" && ID_RE.test(x) && !out.includes(x)) out.push(x);
    if (out.length === MAX_PARALLEL) break;
  }
  return out;
}

/** `?with=a,b,c` from a shared link; the old single `?with=a` is the same
 *  thing with one id. Null when the link names none. */
export function parseWith(search: string): string[] | null {
  const w = new URLSearchParams(search).get("with");
  if (w === null) return null;
  const ids = cleanIds(w.split(","));
  return ids.length === 0 ? null : ids;
}

/** Stored JSON -> Prefs. Reads the two-column shape the reader shipped with
 *  (`second` + `mode` "a" | "both" | "b") as well as the current one. */
export function migrate(p: Record<string, unknown>): Prefs {
  const size = num(p.fontSize, FONT_MIN, FONT_MAX, DEFAULTS.fontSize);
  let parallel: string[];
  let show: string;
  if (Array.isArray(p.parallel)) {
    parallel = cleanIds(p.parallel);
    show = typeof p.show === "string" && ID_RE.test(p.show) ? p.show : "all";
  } else {
    parallel = typeof p.second === "string" ? cleanIds([p.second]) : [];
    // Old "a" meant the primary alone; its id was never stored, and «All» is
    // the harmless reading of it. Old "b" named the second translation.
    show = p.mode === "b" && parallel.length > 0 ? parallel[0] : "all";
  }
  return {
    last: typeof p.last === "string" ? p.last : null,
    parallel,
    show,
    fontSize: size,
    theme: p.theme === "light" || p.theme === "dark" || p.theme === "auto" ? p.theme : DEFAULTS.theme,
    layout: p.layout === "side" || p.layout === "stacked" || p.layout === "auto" ? p.layout : DEFAULTS.layout,
    rate: num(p.rate, RATE_MIN, RATE_MAX, DEFAULTS.rate),
    autoNext: bool(p.autoNext, DEFAULTS.autoNext),
    bed: bool(p.bed, DEFAULTS.bed),
    bedKind: p.bedKind === "music" || p.bedKind === "fireside" ? p.bedKind : DEFAULTS.bedKind,
    bedVolume: num(p.bedVolume, VOL_MIN, 1, DEFAULTS.bedVolume),
    uniformBed: bool(p.uniformBed, DEFAULTS.uniformBed),
  };
}

export function loadPrefs(): Prefs {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw === null) return { ...DEFAULTS };
    const p: unknown = JSON.parse(raw);
    return p !== null && typeof p === "object" ? migrate(p as Record<string, unknown>) : { ...DEFAULTS };
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
