import { render } from "preact";
import { App } from "./app";

const host = document.getElementById("app");
if (host === null) {
  throw new Error("web/index.html has no #app element to mount into");
}
render(<App />, host);
