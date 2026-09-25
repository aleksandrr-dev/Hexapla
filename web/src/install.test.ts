// node --experimental-strip-types src/install.test.ts
// Known-bad control: HEXAPLA_INSTALL_BAD=1 must FAIL.
import { isAndroid, isIos, isIosSafari, shouldAppHint, shouldHint, type Env } from "./install.ts";

const BAD = process.env.HEXAPLA_INSTALL_BAD === "1";
let bad = 0;
const eq = (label: string, got: unknown, want: unknown): void => {
  const g = JSON.stringify(got), w = JSON.stringify(want);
  if (g !== w) bad++;
  console.log((g === w ? "ok   " : "FAIL ") + label + (g === w ? "" : "  got " + g + " want " + w));
};

const env = (ua: string, platform = "iPhone", maxTouchPoints = 5, standalone = false): Env => ({ ua, platform, maxTouchPoints, standalone });

const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1";
const IPAD_DESKTOP = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15";
const CRIOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/124.0.6367.88 Mobile/15E148 Safari/604.1";
const FXIOS = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/125.0 Mobile/15E148 Safari/605.1.15";
const WEBVIEW = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148";
const ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36";
const MAC = IPAD_DESKTOP;

eq("iPhone Safari hints", shouldHint(env(IPHONE), false), true);
eq("iPadOS desktop UA with touch hints", shouldHint(env(IPAD_DESKTOP, "MacIntel", 5), false), true);
eq("a real Mac does not", shouldHint(env(MAC, "MacIntel", BAD ? 5 : 0), false), false);
eq("already on the home screen", shouldHint(env(IPHONE, "iPhone", 5, true), false), false);
eq("closed once, never again", shouldHint(env(IPHONE), true), false);
eq("Chrome on iOS: no", isIosSafari(env(CRIOS)), false);
eq("Firefox on iOS: no", isIosSafari(env(FXIOS)), false);
eq("in-app web view: no", isIosSafari(env(WEBVIEW)), false);
eq("Chrome on iOS is still iOS", isIos(env(CRIOS)), true);
eq("Android: no", shouldHint(env(ANDROID, "Linux armv8l"), false), false);

// The «Android app» strip (owner, 2026-09-25): Android browsers only, never
// once installed as a PWA, never again once closed.
const FIREFOX_ANDROID = "Mozilla/5.0 (Android 14; Mobile; rv:125.0) Gecko/125.0 Firefox/125.0";
const ANDROID_TABLET = "Mozilla/5.0 (Linux; Android 13; SM-X700) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
eq("Android Chrome: app strip", shouldAppHint(env(ANDROID, "Linux armv8l"), false), true);
eq("Android Firefox: app strip", shouldAppHint(env(FIREFOX_ANDROID, "Linux armv8l"), false), true);
eq("Android tablet: app strip", shouldAppHint(env(ANDROID_TABLET, "Linux armv8l"), false), true);
eq("Android PWA on the home screen: no", shouldAppHint(env(ANDROID, "Linux armv8l", 5, true), false), false);
eq("Android closed once: no", shouldAppHint(env(ANDROID, "Linux armv8l"), true), false);
eq("iPhone: no app strip", shouldAppHint(env(IPHONE), false), false);
eq("desktop: no app strip", shouldAppHint(env(BAD ? ANDROID : MAC, "MacIntel", 0), false), false);
eq("isAndroid on a Windows UA: no", isAndroid(env("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Win32", 0)), false);

console.log(bad ? bad + " FAILED" : "all passed");
process.exit(bad ? 1 : 0);
