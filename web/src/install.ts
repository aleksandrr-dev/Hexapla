// The one-time «Add to Home Screen» hint for iPhone and iPad (P4,
// WEB_APP_PLAN.md: iOS never shows an install prompt). Shown only in Safari
// itself - the one iOS browser whose share sheet is certain to carry the entry -
// never once the app runs from the home screen, and never again once closed.
//
// Pure apart from loadDismissed/saveDismissed: `install.test.ts` runs the rest
// under node.

const KEY = "hexapla.a2hs.v1";

export interface Env {
  ua: string;
  platform: string;
  maxTouchPoints: number;
  /** Launched from the home screen (navigator.standalone or display-mode). */
  standalone: boolean;
}

/** iPhone/iPod/iPad, including iPadOS's desktop-class «Macintosh» UA. */
export function isIos(e: Env): boolean {
  if (/iPhone|iPad|iPod/.test(e.ua)) return true;
  return e.platform === "MacIntel" && e.maxTouchPoints > 1;
}

/** Safari proper: other iOS browsers (Chrome, Firefox, Edge, in-app web views)
 *  carry their own token or lack «Safari/». */
export function isIosSafari(e: Env): boolean {
  if (!isIos(e)) return false;
  if (/CriOS|FxiOS|EdgiOS|OPiOS|YaBrowser|GSA\/|FBAN|FBAV|Instagram|Line\//.test(e.ua)) return false;
  return /Safari\//.test(e.ua) && /Version\//.test(e.ua);
}

export function shouldHint(e: Env, dismissed: boolean): boolean {
  return !dismissed && !e.standalone && isIosSafari(e);
}

export function currentEnv(): Env {
  const nav = navigator as Navigator & { standalone?: boolean };
  return {
    ua: nav.userAgent,
    platform: nav.platform,
    maxTouchPoints: nav.maxTouchPoints ?? 0,
    standalone: nav.standalone === true || window.matchMedia("(display-mode: standalone)").matches,
  };
}

export function loadDismissed(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    // No storage: showing it every visit would nag, so treat it as closed.
    return true;
  }
}

export function saveDismissed(): void {
  try {
    localStorage.setItem(KEY, "1");
  } catch {
    // Nothing to do; the hint is gone for this visit either way.
  }
}
