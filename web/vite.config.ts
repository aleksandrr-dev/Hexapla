import { createReadStream, existsSync, statSync } from "node:fs";
import { join, normalize, resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import preact from "@preact/preset-vite";

// Dev only: serve a built data tree at /Hexapla/data/, where Pages serves it
// (a SIBLING of /Hexapla/app/ — see src/data.ts). The tree is ~200 MB and
// must live OUTSIDE the repo (tools/build_web_data.py refuses otherwise):
//
//     python tools/build_web_data.py --out <dir>          (+ --aux, same --out)
//     HEXAPLA_WEB_DATA=<dir>/data npm run dev
function devData(): Plugin {
  return {
    name: "hexapla-dev-data",
    apply: "serve",
    configureServer(server) {
      const root = process.env.HEXAPLA_WEB_DATA;
      if (root === undefined || !existsSync(root)) {
        server.config.logger.warn("HEXAPLA_WEB_DATA is not set to a built data/ tree; every data fetch will 404");
        return;
      }
      const base = resolve(root);
      server.middlewares.use("/Hexapla/data", (req, res, next) => {
        const rel = decodeURIComponent((req.url ?? "/").split("?")[0]);
        const file = normalize(join(base, rel));
        if (!file.startsWith(base) || !existsSync(file) || !statSync(file).isFile()) return next();
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        createReadStream(file).pipe(res);
      });
    },
  };
}

// Published under the landing page's domain, as a subdirectory — see
// WEB_APP_PLAN.md § 0. `base` must match the GitHub Pages path exactly, or
// every emitted asset URL 404s while `npm run dev` still looks fine.
export default defineConfig({
  base: "/Hexapla/app/",
  plugins: [preact(), devData()],
  build: {
    outDir: "dist",
  },
  // The reading typeface is the app's own file (app/src/main/res/font), bundled
  // from there so the two can never differ; the dev server must be allowed to
  // read above web/.
  server: {
    fs: { allow: [".."] },
  },
});
