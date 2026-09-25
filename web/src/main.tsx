import { render } from "preact";
import { App } from "./app";
import { setLocale } from "./i18n";
import { uiTag } from "./locale";
import { registerWorker } from "./offline";
import { loadPrefs } from "./prefs";
import "./styles.css";

const host = document.getElementById("app");
if (host === null) {
  throw new Error("web/index.html has no #app element to mount into");
}
// The interface language is loaded before the first paint, so nobody sees
// English flash into their own language.
void setLocale(uiTag(loadPrefs().uiLang, navigator.languages)).finally(() => render(<App />, host));
registerWorker();
