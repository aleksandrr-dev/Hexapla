// The Kotlin decoder as an oracle for interlinear.ts: compiles the decode half
// of app/.../Interlinear.kt UNCHANGED except `R.string.x` -> `"x"` (so a
// string resource reads as its key), runs it over every morph code in the
// built interlinear data, and writes what it printed.
//
// Run: HEXAPLA_WEB_DATA=<data dir> node --experimental-strip-types scripts/interlinear_oracle.ts <out.json>
// Needs Android Studio's bundled Kotlin compiler jars and its jbr. Under a minute.
// interlinear.test.ts reads <out.json> and refuses it once Interlinear.kt has
// changed since (the file carries the source's sha256).
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const out = process.argv[2];
const DATA = process.env.HEXAPLA_WEB_DATA;
if (out === undefined || DATA === undefined) throw new Error("usage: HEXAPLA_WEB_DATA=<dir> ... interlinear_oracle.ts <out.json>");
const KT = new URL("../../app/src/main/java/com/aleks/hexapla/Interlinear.kt", import.meta.url);
const KOTLIN_LIB = process.env.KOTLIN_LIB ?? "C:/Program Files/Android/Android Studio/plugins/Kotlin/kotlinc/lib";
const JAVA = join(process.env.JAVA_HOME ?? "C:/Program Files/Android/Android Studio/jbr", "bin", "java");

const kt = readFileSync(KT, "utf8");
const from = kt.indexOf("    /* ---- Robinson (Greek) ---- */");
const to = kt.lastIndexOf("\n}");
if (from < 0 || to < from) throw new Error("Interlinear.kt: decoder section not found");
const body = kt
  .slice(from, to)
  .replace(/R\.string\.(\w+)/g, '"$1"')
  .replace(/\(Int\) -> String/g, "(String) -> String");
if (/R\.string|context/.test(body)) throw new Error("Interlinear.kt: decoder section still needs Android");

// Every distinct code, per language.
const codes: Record<"gr" | "he", Set<string>> = { gr: new Set(), he: new Set() };
for (const lang of ["gr", "he"] as const) {
  const dir = join(DATA, "interlinear", lang);
  for (const f of readdirSync(dir)) {
    const o = JSON.parse(readFileSync(join(dir, f), "utf8")) as Record<string, string[][]>;
    for (const chs of Object.values(o))
      for (const vs of chs)
        for (const v of vs)
          for (const tag of v.split(" ")) {
            const bar = tag.indexOf("|");
            if (bar >= 0) codes[lang].add(tag.slice(bar + 1));
          }
  }
}

const work = mkdtempSync(join(tmpdir(), "interlinear-oracle-"));
const src = `object Oracle {
${body}
    fun gr(c: String) = decodeRobinson({ it }, c)
    fun he(c: String) = decodeOshm({ it }, c)
}

fun main(args: Array<String>) {
    val w = java.io.File(args[1]).printWriter(Charsets.UTF_8)
    java.io.File(args[0]).readLines(Charsets.UTF_8).forEach { line ->
        val (lang, code) = line.split('\\t', limit = 2)
        w.println(if (lang == "gr") Oracle.gr(code) else Oracle.he(code))
    }
    w.close()
}
`;
writeFileSync(join(work, "Oracle.kt"), src);
const lines = [...[...codes.gr].map((c) => "gr\t" + c), ...[...codes.he].map((c) => "he\t" + c)];
writeFileSync(join(work, "in.tsv"), lines.join("\n") + "\n");
// The compiler class straight off its jars: the bundled kotlinc.bat wants a
// preloader jar Android Studio does not ship.
execFileSync(JAVA, ["-cp", KOTLIN_LIB + "/*", "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler", join(work, "Oracle.kt"), "-include-runtime", "-no-reflect", "-d", join(work, "oracle.jar")], { stdio: "inherit" });
execFileSync(JAVA, ["-cp", join(work, "oracle.jar"), "OracleKt", join(work, "in.tsv"), join(work, "out.txt")], { stdio: "inherit" });
const res = readFileSync(join(work, "out.txt"), "utf8").split(/\r?\n/);
if (res.length < lines.length) throw new Error("oracle printed " + String(res.length) + " lines for " + String(lines.length) + " codes");
const result: { kt_sha256: string; gr: Record<string, string>; he: Record<string, string> } = {
  kt_sha256: createHash("sha256").update(kt).digest("hex"),
  gr: {},
  he: {},
};
lines.forEach((l, i) => {
  const [lang, code] = l.split("\t") as ["gr" | "he", string];
  result[lang][code] = res[i];
});
writeFileSync(out, JSON.stringify(result));
console.log("oracle: " + String(codes.gr.size) + " Robinson + " + String(codes.he.size) + " OSHM codes -> " + out);
