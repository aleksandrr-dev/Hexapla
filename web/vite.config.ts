import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// Published under the landing page's domain, as a subdirectory — see
// WEB_APP_PLAN.md § 0. `base` must match the GitHub Pages path exactly, or
// every emitted asset URL 404s while `npm run dev` still looks fine.
export default defineConfig({
  base: "/Hexapla/app/",
  plugins: [preact()],
  build: {
    outDir: "dist",
  },
});
