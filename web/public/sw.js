// Hexapla web - the service worker (P4, WEB_APP_PLAN.md § 3).
//
// Offline for anything already read, by caching as it is used - there is NO
// big precache: the book art and the music are ~20 MB and most readers never
// touch most of it. Registered from src/main.tsx with scope /; a
// service worker sees every fetch its pages make, so the data tree at
// /data/ (a sibling of the scope) is served from here too.
//
//   navigation        network first, the cached page when offline
//   .../data/...      cache first, refreshed in the background (a repaired
//                     asset reaches a kept translation on the next read)
//   hashed /assets/   cache first (their names change when they do)
//   anything else     network first, cache as fallback
//   Range requests    never touched: <audio> streams, and a 206 cannot be
//                     cached. Other origins (archive.org audio) untouched.
//
// ⚠ The cache NAMES are shared with src/offline.ts («keep offline» writes
// into DATA from the page); offline.test.ts fails if the two ever differ.
const SHELL = "hx-shell-v1";
const DATA = "hx-data-v1";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== SHELL && k !== DATA) await caches.delete(k);
    await self.clients.claim();
  })());
});

const isData = (u) => u.pathname.includes("/data/");
const isAsset = (u) => u.pathname.startsWith(new URL("assets/", self.registration.scope).pathname);
const isMedia = (u) => /\.(mp3|ogg|m4a|opus)$/i.test(u.pathname);

async function put(cacheName, req, res) {
  if (res && res.ok && res.status === 200) await (await caches.open(cacheName)).put(req, res.clone());
  return res;
}

// The page sends what it loaded BEFORE this worker controlled it (the very
// first visit), so the chapter just read and the app shell work offline at once.
self.addEventListener("message", (e) => {
  const m = e.data;
  if (!m || m.type !== "seed" || !Array.isArray(m.urls)) return;
  e.waitUntil((async () => {
    for (const s of m.urls) {
      let u;
      try { u = new URL(s, self.location.href); } catch { continue; }
      if (u.origin !== self.location.origin || isMedia(u)) continue;
      u.hash = "";
      const name = isData(u) ? DATA : SHELL;
      const cache = await caches.open(name);
      if (await cache.match(u.href)) continue;
      try { await put(name, u.href, await fetch(u.href)); } catch { /* offline: next time */ }
    }
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || req.headers.has("range")) return;
  const u = new URL(req.url);
  if (u.origin !== self.location.origin) return;

  if (req.mode === "navigate") {
    // One cached page for the whole app: the route lives in the hash.
    const key = self.registration.scope;
    // ONLY the app's own page. With the scope at the site root this worker
    // also sees /download/ and /PRIVACY.html; caching those under `key` would
    // replace the app, and the reader opened offline would show them.
    const root = new URL(key).pathname;
    if (u.pathname !== root && u.pathname !== root + "index.html") return;
    e.respondWith(fetch(req).then((r) => put(SHELL, key, r)).catch(async () =>
      (await caches.match(key)) ?? Response.error()));
    return;
  }
  if (isData(u)) {
    // ⚠ waitUntil/respondWith SYNCHRONOUSLY, in the event's own dispatch:
    // WebKit throws on a waitUntil made after an await, which failed every
    // data read offline there (Chromium tolerates it; 2026-09-24).
    const fresh = fetch(req).then((r) => put(DATA, req, r));
    e.waitUntil(fresh.catch(() => undefined));
    e.respondWith(caches.open(DATA).then((c) => c.match(req)).then((hit) => hit ?? fresh));
    return;
  }
  if (isMedia(u)) return;
  if (isAsset(u)) {
    e.respondWith((async () => (await caches.match(req)) ?? put(SHELL, req, await fetch(req)))());
    return;
  }
  e.respondWith(fetch(req).then((r) => put(SHELL, req, r)).catch(async () =>
    (await caches.match(req)) ?? Response.error()));
});
