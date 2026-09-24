// «Keep offline» for a whole translation, and the service-worker registration
// (P4, WEB_APP_PLAN.md § 3). Chapters already read are cached by public/sw.js
// as they load; keeping a translation fetches the rest of it into that same
// cache from the page, with the Cache API, so the worker needs no protocol.
//
// A translation is KEPT when every one of its files is in the cache - derived
// from the cache each time, never a flag that could disagree with it.

/** Cache names, shared with public/sw.js (offline.test.ts checks they match). */
export const SHELL_CACHE = "hx-shell-v1";
export const DATA_CACHE = "hx-data-v1";

/** Where data/ lives: a sibling of the app's base (see data.ts url()). */
export function dataRoot(base: string, origin: string): string {
  const app = base.endsWith("/") ? base : base + "/";
  return origin + app.replace(/[^/]+\/$/, "") + "data/";
}

/** Every file a translation needs to be read offline, in fetch order. */
export function keepUrls(root: string, id: string, bookCount: number): string[] {
  const out = [root + "manifest.json", root + "versemap.json", root + id + "/books.json"];
  for (let b = 0; b < bookCount; b++) out.push(root + id + "/" + String(b) + ".json");
  return out;
}

export interface KeepState {
  have: number;
  total: number;
}

const root = (): string => dataRoot(import.meta.env.BASE_URL, location.origin);
export const offlineSupported = (): boolean => typeof caches !== "undefined" && "serviceWorker" in navigator;

/** What the data cache holds, as URLs: ONE keys() call. A match() per file
 *  (~86 per translation, ~40 translations) never finished in WebKit. */
export async function cachedUrls(): Promise<Set<string>> {
  const cache = await caches.open(DATA_CACHE);
  return new Set((await cache.keys()).map((r) => r.url));
}

/** How much of a translation `have` holds. */
export function stateIn(have: Set<string>, id: string, bookCount: number): KeepState {
  const urls = keepUrls(root(), id, bookCount);
  return { have: urls.filter((u) => have.has(u)).length, total: urls.length };
}

export async function keepState(id: string, bookCount: number): Promise<KeepState> {
  return stateIn(await cachedUrls(), id, bookCount);
}

/** Fetch whatever of the translation is not cached yet. Throws on the first
 *  failed file (offline, or a broken deploy): a partial keep reports as such. */
export async function keep(id: string, bookCount: number, progress: (s: KeepState) => void): Promise<KeepState> {
  void navigator.storage?.persist?.().catch(() => undefined);
  const urls = keepUrls(root(), id, bookCount);
  const cache = await caches.open(DATA_CACHE);
  const already = await cachedUrls();
  let have = 0;
  for (const u of urls) {
    if (!already.has(u)) {
      const res = await fetch(u, { cache: "no-cache" });
      if (!res.ok) throw new Error("fetch " + u + " failed: HTTP " + String(res.status));
      await cache.put(u, res);
    }
    have++;
    progress({ have, total: urls.length });
  }
  return { have, total: urls.length };
}

/** Drop a translation's books (the shared manifest/versemap stay). */
export async function unkeep(id: string, bookCount: number): Promise<void> {
  const cache = await caches.open(DATA_CACHE);
  for (const u of keepUrls(root(), id, bookCount).slice(2)) await cache.delete(u);
}

/** Register the worker, then seed it with what this page loaded before it
 *  was in control. Production only, or `?sw=1` for a dev check. */
export function registerWorker(): void {
  if (!("serviceWorker" in navigator)) return;
  if (!import.meta.env.PROD && !location.search.includes("sw=1")) return;
  const go = async (): Promise<void> => {
    await navigator.serviceWorker.register(import.meta.env.BASE_URL + "sw.js", { scope: import.meta.env.BASE_URL });
    const reg = await navigator.serviceWorker.ready;
    const urls = [location.href.split("#")[0], ...performance.getEntriesByType("resource").map((e) => e.name)];
    reg.active?.postMessage({ type: "seed", urls });
  };
  const start = (): void => void go().catch(() => undefined);
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start, { once: true });
}
