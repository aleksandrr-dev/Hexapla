# hexapla-web

The browser reader for Hexapla — same data, same mission as the Android app.
Stack per `WEB_APP_PLAN.md` § 0: Vite + TypeScript + Preact, `idb` for
IndexedDB, `vite-plugin-pwa` for offline. Published under the landing page at
`/Hexapla/app/`.

## Running it

    npm install       # first time only; versions in package.json are exact pins
    npm run dev       # dev server, needs data/ (below)
    npm run build     # tsc --noEmit && vite build -> dist/
    npm run preview   # serve dist/ as it will be served in production

## `data/` is built, never committed

The reader fetches `data/manifest.json`, `data/<id>/books.json` and
`data/<id>/<bookIndex>.json`. None of that is in this repo: it is split from
`app/src/main/assets` on every deploy by `tools/build_web_data.py` and is
~200 MB, well past what belongs in git. See `WEB_APP_PLAN.md` § 4. `manifest.json`
also carries the `sources_text` credit, which is a licence obligation — render
it, do not reword it.

For a local run, build the data into `public/`, where Vite serves it as static
files and copies it into `dist/` — and where CI injects it instead:

    python tools/build_web_data.py --out web/public

`web/public/` is therefore empty in git except for a `.gitkeep`.

## What is here, and what is not

`src/route.ts` parses the deep link `#/<translation>/<book>/<chapter>/<verse>`.
The URL counts from 1; everything inside the app counts from 0; that crossing
happens in that one file and nowhere else. `/0` in the hash is refused, not
clamped.

`src/data.ts` is `fetch` + parse with a cache. No IndexedDB, no service worker,
no offline logic yet — those are P4.

`src/app.tsx` renders the route's name and nothing more. The reader UI, the
parallel view and every styling decision are gated behind the P0.5 design gate
(`WEB_APP_PLAN.md` § 3) and must not be anticipated here.

## The four house rules for this tree

`tools/check_web_scaffold.py` enforces these; it is the gate, and it runs on
the whole tree, not a sample:

1. nothing that takes money, anyone's money, in any form;
2. nothing that counts, reports or observes a reader;
3. no remote origin at runtime. Every asset ships with the build — no CDN, no
   hosted fonts, no third-party script. The only host the built app may ever
   name is `archive.org`, as audio data, and that is P3's business, not P0's;
4. no accounts, no cookies, no stored identifier.

Rule 3 is why `web/src/**` and `web/index.html` are censused for a literal
origin scheme, and why this README is written to avoid the four words that
would otherwise trip rule 1 and 2 by name. The census is a substring match
over the whole tree, so a prohibition written out in prose reads the same as
the thing it prohibits.
