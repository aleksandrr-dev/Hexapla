# -*- coding: utf-8 -*-
"""Gate the `web/` scaffold (WEB_APP_PLAN.md § 0 stack + § 5 step 4).

    python tools/check_web_scaffold.py             # check the real web/ tree
    python tools/check_web_scaffold.py --selftest  # every check vs FIXTURES

WHAT IT CAN AND CANNOT SEE
    Checks 1-5 and 7 read files as BYTES and parse JSON — that is the whole
    verdict for the scaffold's shape, its pins, its scripts and the forbidden
    strings. Check 6 is weaker by construction: there is no TypeScript runtime
    in this environment, so it greps `src/route.ts` as TEXT for the boundary
    comment and the route regex, plus `!n < 1` in the converter. It proves the
    contract is WRITTEN DOWN, not that it is implemented. It cannot be made
    stronger here. Check 6 is BACKED UP, when node is on PATH, by actually
    running web/src/route.test.ts under node's type stripping - the boundary
    bug it targets (one sentinel for both "malformed" and "no verse given")
    is invisible to a grep. Nothing else here compiles or type-checks the
    TypeScript, and nothing here should be read as having done so.

    The scaffold's own acceptance (`npm install && npm run build`) is the
    planner's number on a networked machine. It is NOT checked here and NOT
    claimed here.

EXIT CODES
    0  every check passed
    1  at least one check FAILED
    2  a check COULD NOT RUN (web/ missing, or a file it must read is
       unreadable). Never 0, and never a plausible «0 problems found».

    A check that cannot run did not pass. If the tree is absent this script
    says so and exits 2, because "I could not look" and "I looked and it was
    clean" are the same number otherwise, and only one of them is a pass.

KNOWN-BAD CONTROLS (honoured ONLY when _IN_SELFTEST is true, i.e. only ever
from --selftest):
    HEXAPLA_WEBSCAF_FAKE_DONATION=1   injects a yoomoney line into the census
                                      input in memory, so check 5 must FAIL;
    HEXAPLA_WEBSCAF_FAKE_LOOSE_PIN=1  injects "preact": "^10.0.0" into the
                                      package.json fixture, so check 2 must FAIL.
    A real run against the real tree cannot reach either: the env vars are
    read only inside the fixture path.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "web"
GITIGNORE = REPO / ".gitignore"

# Flipped only by _selftest(). Every known-bad env var is read behind it.
_IN_SELFTEST = False

# ---------------------------------------------------------------- expected

# The scaffold's inventory. Kept as (relative path, what it is) so a failure
# can say which one is missing rather than «the layout is wrong».
REQUIRED_FILES = (
    ("package.json", "npm manifest"),
    ("tsconfig.json", "TypeScript config"),
    ("vite.config.ts", "Vite config"),
    ("index.html", "app shell"),
    ("README.md", "how to run it"),
    ("src/main.tsx", "mounts <App/>"),
    ("src/app.tsx", "renders the route's name"),
    ("src/data.ts", "data-access layer"),
    ("src/route.ts", "deep-link parser"),
    ("src/types.ts", "Manifest / Translation / Book"),
    ("public/.gitkeep", "so data/ has a home in CI"),
)

# Exactly these six, per the brief. Missing one, or a seventh the brief did not
# ask for, is a finding — the stack decision in § 0 is made.
EXPECTED_DEPS = ("preact", "typescript", "vite", "@preact/preset-vite", "idb",
                 "vite-plugin-pwa")
EXPECTED_SCRIPTS = ("dev", "build", "preview")

# An exact pin: digits and dots, optionally a pre-release / build suffix. No
# ^ ~ * >= x latest workspace: file: link: git+ or a URL. Deliberately strict —
# a range that happens to resolve today is not a reproducible CI build.
PIN_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

# Check 5. Case-insensitive substrings, censused over all of web/**.
FORBIDDEN_SUBSTRINGS = (
    "yoomoney", "donate", "donation", "analytics", "gtag",
    "google-analytics", "plausible", "sentry", "telemetry",
)

# Each needle must start at a word-ish boundary, or `gtag` matches
# `has-tostringtag` and the census cries wolf on half of npm (measured
# 2026-09-22 against the real lockfile: 9 hits, every one a false positive).
FORBIDDEN_RES = tuple(
    (needle, re.compile(r"(?<![a-z0-9])" + re.escape(needle)))
    for needle in FORBIDDEN_SUBSTRINGS
)

# Check 5b. The literal, lower-cased, only inside web/src/** and
# web/index.html. `http` and `https` are censused SEPARATELY so `/Hexapla/app/`
# cannot accidentally satisfy the pattern through an unrelated word.
REMOTE_ORIGIN_RE = re.compile(r"https?://")

# Files whose bytes are censused by 5b rather than 5 alone.
REMOTE_SCOPE = ("web/src/", "web/index.html")

# Never descended into; not present yet, and a build artifact if it is.
SKIP_DIRS = {"node_modules", "dist", ".git"}

# Generated dependency manifests: censused, but their hits are DEPENDENCY
# NAMES, not code. Reported separately rather than failing the run.
CENSUS_DEPENDENCY_FILES = {"web/package-lock.json"}

# Check 7, appended to .gitignore verbatim.
GITIGNORE_LINES = ("web/node_modules/", "web/dist/", "site/")

# Check 4.
VITE_BASE = "/Hexapla/app/"

# The four pins whose npm existence this environment cannot corroborate, or can
# corroborate only weakly (no network, and this machine's npm cache holds none
# of the six). They are pinned to the versions the text of the brief itself
# names — `"preact": "^10.0.0"` for the control, `Vite` + `@preact/preset-vite`
# + `TypeScript` for the stack — on the reasoning that the planner tried those
# versions on the day the brief was written. Check 2 verifies the FORM of every
# pin; it cannot verify EXISTENCE, and it must not pretend to. This tuple is the
# report's `weak` list, and it is a GAP, not a pass.
PINS_UNVERIFIED_OFFLINE = (
    "vite",
    "typescript",
    "@preact/preset-vite",
    "vite-plugin-pwa",
)

# Check 6, the TEXT facts `src/route.ts` must carry. `1-based` and `0-based`
# (case-insensitive) must BOTH appear in a comment, and the parser must
# actually be coming off that hash shape.
ROUTE_TEXT_FACTS = (
    ("the boundary is named in a comment",
     re.compile(r"(?i)\b1-based\b")),
    ("the internal convention is named in a comment",
     re.compile(r"(?i)\b0-based\b")),
    ("the route shape is present",
     re.compile(r"#/<translation>/<book>/<chapter>/<verse>")),
    ("the route regex is present",
     # Literal, not escaped: the regex must be spelled the same way in the
     # comment and in the pattern below it, and `(?:\/(\d+))?` with a literal
     # backslash-d is that spelling. re.escape() of the source text.
     re.compile(re.escape(r"(?:\/(\d+))?"))),
    ("the 1-based URL face is the declared one",
     re.compile(r"1-BASED IN THE URL")),
    ("the 0-based internal face is the declared one",
     re.compile(r"0-BASED INTERNAL")),
)


class CouldNotRun(Exception):
    """A check that had nothing to look at. Turns into exit 2, never 0."""


# ------------------------------------------------------------------ helpers

def fail_line(name, detail):
    """One reportable failure. Always starts with `FAIL - ` so wb_run.py's
    grader can tell it from a traceback."""
    return "FAIL - {}: {}".format(name, detail)


def read_bytes(rel):
    """Read a repo-relative path as bytes, or raise CouldNotRun."""
    p = REPO / rel
    try:
        return p.read_bytes()
    except OSError as e:
        raise CouldNotRun("{}: {}".format(rel, e))


def read_text(rel):
    try:
        return read_bytes(rel).decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise CouldNotRun("{}: not UTF-8: {}".format(rel, e))


def web_files():
    """Every file under web/, repo-relative, sorted. Raises CouldNotRun."""
    if not WEB.is_dir():
        raise CouldNotRun(
            "web/ does not exist at {} — nothing to check. "
            "This is exit 2, not «0 problems found».".format(WEB)
        )
    out = []
    for p in sorted(WEB.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO).as_posix()
        if SKIP_DIRS & set(Path(rel).parts):
            continue
        out.append(rel)
    return out


def decode_lines(rel, blobs):
    """Yield (line_number, text) for one file, replacing undecodable bytes.

    A binary file is not a reason to skip the census — that is how a stray
    artifact with a URL in it hides. Undecodable bytes become U+FFFD and are
    still scanned.
    """
    text = blobs[rel].decode("utf-8", "replace")
    for i, line in enumerate(text.splitlines(), 1):
        yield i, line


# ------------------------------------------------------------------- checks
# Each returns a list of failure strings: [] means it passed. Raising
# CouldNotRun means it did not run, which is its own outcome.

def check_layout(files):
    """1. every file in the layout exists."""
    # Files arrive repo-relative ("web/src/main.tsx"); the inventory is
    # web-relative ("src/main.tsx").
    present = {f[len("web/"):] for f in files if f.startswith("web/")}
    bad = []
    for rel, what in REQUIRED_FILES:
        if rel not in present:
            bad.append(fail_line("layout", "missing web/{} ({})".format(rel, what)))
    return bad


def check_package_json(files, blobs, deps=None):
    """2. package.json: parses, private, exact pins, six deps, three scripts."""
    bad = []
    if "web/package.json" not in files:
        return [fail_line("package.json", "web/package.json is absent")]
    raw = blobs["web/package.json"].decode("utf-8-sig", "replace")
    try:
        pkg = json.loads(raw)
    except ValueError as e:
        return [fail_line("package.json", "does not parse: {}".format(e))]
    if not isinstance(pkg, dict):
        return [fail_line("package.json", "top level is not an object")]

    if pkg.get("private") is not True:
        bad.append(fail_line("package.json", "private is {!r}, must be true".format(
            pkg.get("private"))))
    if pkg.get("type") != "module":
        bad.append(fail_line("package.json", "type is {!r}, must be \"module\"".format(
            pkg.get("type"))))
    if pkg.get("name") != "hexapla-web":
        bad.append(fail_line("package.json", "name is {!r}, must be \"hexapla-web\"".format(
            pkg.get("name"))))

    found = {}
    for section in ("dependencies", "devDependencies"):
        table = pkg.get(section) or {}
        if not isinstance(table, dict):
            bad.append(fail_line("package.json", "{} is not an object".format(section)))
            continue
        for name, version in table.items():
            found[name] = version
            if not isinstance(version, str) or not PIN_RE.match(version):
                bad.append(fail_line(
                    "version pin",
                    '{}.{} = {!r} is not an exact pin '
                    "(no ^ ~ * >= x latest, no URL, no tag range)".format(
                        section, name, version),
                ))
            if deps is not None and name in deps:
                version = deps[name]

    for name in EXPECTED_DEPS:
        if name not in found:
            bad.append(fail_line("dependency", "{} is absent".format(name)))
    for name in sorted(found):
        if name not in EXPECTED_DEPS:
            bad.append(fail_line(
                "dependency",
                "{} is present but the stack decision names only {}".format(
                    name, ", ".join(EXPECTED_DEPS)),
            ))

    scripts = pkg.get("scripts") or {}
    if not isinstance(scripts, dict):
        bad.append(fail_line("scripts", "scripts is not an object"))
    else:
        for name in EXPECTED_SCRIPTS:
            if name not in scripts:
                bad.append(fail_line("scripts", "{} is absent".format(name)))
        build = scripts.get("build", "")
        if isinstance(build, str):
            # The build must type-check before it bundles; a Vite-only build
            # ships type errors that `strict` was turned on to catch.
            if "tsc" not in build or "--noEmit" not in build:
                bad.append(fail_line(
                    "scripts", "build must run `tsc --noEmit` first, is {!r}".format(build)))
            if "vite build" not in build:
                bad.append(fail_line(
                    "scripts", "build must run `vite build`, is {!r}".format(build)))
    return bad


def check_tsconfig(files, blobs):
    """3. tsconfig.json: parses (no comments emitted) and strict is true."""
    if "web/tsconfig.json" not in files:
        return [fail_line("tsconfig.json", "web/tsconfig.json is absent")]
    raw = blobs["web/tsconfig.json"].decode("utf-8-sig", "replace")
    if "//" in raw or "/*" in raw:
        return [fail_line(
            "tsconfig.json",
            "contains a comment; the brief says emit none, because JSON.parse "
            "cannot read one and a future check must not have to strip it",
        )]
    try:
        cfg = json.loads(raw)
    except ValueError as e:
        return [fail_line("tsconfig.json", "does not parse: {}".format(e))]
    if not isinstance(cfg, dict):
        return [fail_line("tsconfig.json", "top level is not an object")]
    co = cfg.get("compilerOptions")
    if not isinstance(co, dict):
        return [fail_line("tsconfig.json", "compilerOptions is absent or not an object")]
    if co.get("strict") is not True:
        return [fail_line("tsconfig.json", "compilerOptions.strict is {!r}, must be true".format(
            co.get("strict")))]
    return []


def check_vite_base(files, blobs):
    """4. vite.config.ts sets base to /Hexapla/app/ and outDir to dist."""
    if "web/vite.config.ts" not in files:
        return [fail_line("vite.config.ts", "web/vite.config.ts is absent")]
    src = blobs["web/vite.config.ts"].decode("utf-8-sig", "replace")
    bad = []
    if not re.search(r"\bbase\s*:\s*[\"']" + re.escape(VITE_BASE) + r"[\"']", src):
        bad.append(fail_line(
            "vite.config.ts",
            "base is not the literal {!r}; a different base 404s every asset "
            "on Pages while `npm run dev` still looks fine".format(VITE_BASE),
        ))
    if not re.search(r"\boutDir\s*:\s*[\"']dist[\"']", src):
        bad.append(fail_line(
            "vite.config.ts", "build.outDir is not the literal 'dist'"))
    return bad


def census(blobs, files, extra_lines=None):
    """5 + 5b. Returns (bad, hits_by_class). Pure over its input, so the
    selftest can hand it fixtures and the known-bad injection works."""
    bad = []
    sub_hits = []
    origin_hits = []
    extra = extra_lines or {}

    dep_hits = []
    for rel in files:
        if rel not in blobs:
            continue
        if rel in CENSUS_DEPENDENCY_FILES:
            # A lockfile names DEPENDENCIES, not code. `workbox-google-analytics`
            # is a transitive package of vite-plugin-pwa; its presence in the
            # dependency graph is not analytics in the app, and censusing it as
            # code makes the check cry wolf. It is still REPORTED (below), never
            # silently skipped - a real analytics package arriving in the graph
            # is a thing the owner should see.
            for n, line in decode_lines(rel, blobs):
                low = line.lower()
                for needle, rx in FORBIDDEN_RES:
                    if rx.search(low):
                        dep_hits.append("{}:{}: [{}] {}".format(rel, n, needle, line.strip()))
            continue
        scope = any(rel.startswith(p) or rel == p for p in REMOTE_SCOPE)
        for n, line in decode_lines(rel, blobs):
            low = line.lower()
            for needle, rx in FORBIDDEN_RES:
                if rx.search(low):
                    sub_hits.append("{}:{}: [{}] {}".format(rel, n, needle, line.strip()))
            if scope and REMOTE_ORIGIN_RE.search(low):
                origin_hits.append("{}:{}: {}".format(rel, n, line.strip()))
        for n, line in extra.get(rel, ()):
            low = line.lower()
            for needle, rx in FORBIDDEN_RES:
                if rx.search(low):
                    sub_hits.append(
                        "{}:{}: [{}] {}  (injected)".format(rel, n, needle, line.strip()))

    if sub_hits:
        bad.append(fail_line(
            "forbidden-strings census",
            "{} hit(s) — donations, analytics and telemetry are forbidden "
            "outright (WEB_APP_PLAN.md § 0):".format(len(sub_hits)),
        ))
        bad.extend("    " + h for h in sub_hits)
    if origin_hits:
        bad.append(fail_line(
            "remote-origin census",
            "{} hit(s) — no remote origin at runtime, every asset ships with "
            "the build:".format(len(origin_hits)),
        ))
        bad.extend("    " + h for h in origin_hits)
    return bad, {"substrings": sub_hits, "remote_origins": origin_hits,
                 "dependency_names": dep_hits}


def check_route_contract(files, blobs):
    """6. the 1-based-URL / 0-based-internal contract, asserted as TEXT.

    ⚠ This is a TEXT check and cannot be anything else here — there is no
    TypeScript runtime in this environment and this script must not pretend
    there is. It confirms the boundary is named, the regex is the one the
    comment describes, and the converter refuses a 1-based 0. It does NOT
    confirm the parser compiles or that its arithmetic is right; `npm run
    build` does that, and it is the planner's number, not this script's.
    """
    if "web/src/route.ts" not in files:
        return [fail_line("route contract", "web/src/route.ts is absent")]
    src = blobs["web/src/route.ts"].decode("utf-8-sig", "replace")
    comment_lines = [ln for ln in src.splitlines() if ln.lstrip().startswith(("//", "*", "/*"))]
    comment = "\n".join(comment_lines)
    bad = []
    for what, rx in ROUTE_TEXT_FACTS:
        hay = comment if rx.pattern.startswith("(?i)\\b") else src
        if not rx.search(hay):
            bad.append(fail_line("route contract", "{} — not found in route.ts".format(what)))
    # The 1-based face must be REFUSED, not clamped. `/0` on the way in has to
    # come back null, which is what makes the boundary a boundary.
    # `return null` or `return <SENTINEL>` - what matters is that a
    # non-1-based segment is REFUSED, not which sentinel carries the
    # refusal. (route.ts uses a BAD symbol so that "malformed" and
    # "no verse given" cannot collide; they did, and it cost a route.)
    if not re.search(r"<\s*1\s*\)?\s*\)\s*return\s+[A-Za-z_][A-Za-z0-9_]*", src):
        bad.append(fail_line(
            "route contract",
            "no guard rejecting a present-but-non-1-based segment "
            "(expected `n < 1` -> null); a clamped route reads the wrong verse",
        ))
    return bad


def check_gitignore(files, blobs):
    """7. .gitignore carries the three appended lines."""
    if ".gitignore" not in blobs:
        raise CouldNotRun(".gitignore is absent from the repo root")
    text = blobs[".gitignore"].decode("utf-8-sig", "replace")
    lines = [ln.strip() for ln in text.splitlines()]
    bad = []
    for want in GITIGNORE_LINES:
        if lines.count(want) != 1:
            bad.append(fail_line(
                ".gitignore",
                "{!r} appears {} time(s), want exactly 1".format(want, lines.count(want)),
            ))
    if not any(ln.startswith("#") and "data" in ln.lower() for ln in lines):
        bad.append(fail_line(
            ".gitignore", "no one-line comment explaining why the three lines are there"))
    return bad


# ------------------------------------------------------------------- driver

def run_all(files, blobs, extra_lines=None, deps=None, check_numbers=None):
    """Run the checks selected by check_numbers. Returns (bad, census_counts).

    Raises CouldNotRun when web/ is absent — the caller decides that this is
    exit 2, never 0.
    """
    if not files:
        raise CouldNotRun("web/ exists but holds no files — nothing to check")

    want = check_numbers or (1, 2, 3, 4, 5, 6, 7)
    bad = []
    counts = None
    if 1 in want:
        bad += check_layout(files)
    if 2 in want:
        bad += check_package_json(files, blobs, deps=deps)
    if 3 in want:
        bad += check_tsconfig(files, blobs)
    if 4 in want:
        bad += check_vite_base(files, blobs)
    if 5 in want:
        b, counts = census(blobs, files, extra_lines=extra_lines)
        bad += b
    if 6 in want:
        bad += check_route_contract(files, blobs)
    if 7 in want:
        bad += check_gitignore(files, blobs)
    return bad, counts


def selftest():
    """Every check against FIXTURES, never against the real tree.

    The fixtures are deliberately shaped like the scaffold. The two known-bad
    env vars corrupt one fixture each, in memory, and that check must then
    FAIL. A control that fires on nothing is not a control, so the clean run
    asserts the other checks still pass.

    The same enforcement runs the other way, on every check: a WRONG fixture
    is handed to the check that should own it, and the clean run asserts that
    it does NOT fire. A check that passes wrong input is not a check either,
    and that is the failure mode this project keeps hitting — nine instrument
    bugs, nearly all under-reporting.
    """
    global _IN_SELFTEST
    _IN_SELFTEST = True
    results = []

    def check(name, fn):
        try:
            res = fn()
        except Exception as e:
            results.append(False)
            print(fail_line(name, "raised {}: {}".format(type(e).__name__, e)))
            return
        if res is False:
            results.append(False)
            print(fail_line(name, "returned False, not a failure list"))
        else:
            results.append(True)
            print("PASS - {}".format(name))

    # ---- the clean fixture: a minimal, well-formed scaffold ----------------
    fixture = {
        "web/package.json": json.dumps({
            "name": "hexapla-web",
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc --noEmit && vite build",
                "preview": "vite preview",
            },
            "dependencies": {"idb": "8.0.0", "preact": "10.24.3"},
            "devDependencies": {
                "@preact/preset-vite": "2.9.1",
                "typescript": "5.6.3",
                "vite": "5.4.10",
                "vite-plugin-pwa": "0.20.5",
            },
        }, indent=2).encode("utf-8"),
        "web/tsconfig.json": json.dumps(
            {"compilerOptions": {"strict": True, "jsx": "react-jsx"}}, indent=2).encode("utf-8"),
        "web/vite.config.ts": (
            'import { defineConfig } from "vite";\n'
            'export default defineConfig({\n'
            '  base: "/Hexapla/app/",\n'
            '  build: { outDir: "dist" },\n'
            '});\n'
        ).encode("utf-8"),
        "web/index.html": (
            b'<!DOCTYPE html>\n<html lang="en" dir="ltr">\n'
            b'<div id="app"></div>\n'
            b'<script type="module" src="/src/main.tsx"></script>\n'
            b"</html>\n"
        ),
        "web/README.md": b"# hexapla-web\n\ndata/ is built, never committed.\n",
        "web/src/main.tsx": b'import { render } from "preact";\n',
        "web/src/app.tsx": b"export function App() { return null; }\n",
        "web/src/data.ts": b"export function loadManifest() { return null; }\n",
        "web/src/route.ts": (
            "// The 1-based URL / 0-based internal boundary: this file and no other.\n"
            "// The deep link is #/<translation>/<book>/<chapter>/<verse>.\n"
            "// 1-BASED IN THE URL, 0-BASED INTERNAL.\n"
            'const ROUTE_RE = /^\\/?([A-Za-z0-9_-]+)(?:\\/(\\d+))?(?:\\/(\\d+))?(?:\\/(\\d+))?$/;\n'
            "function toIndex(segment, fallback) {\n"
            "  if (segment === undefined) return fallback;\n"
            "  const n = Number(segment);\n"
            "  if (!Number.isInteger(n) || n < 1) return null;\n"
            "  return n - 1;\n"
            "}\n"
        ).encode("utf-8"),
        "web/src/types.ts": b"export interface Manifest { translations: unknown[]; }\n",
        "web/public/.gitkeep": b"# placeholder\n",
        ".gitignore": (
            "# Web app (WEB_APP_PLAN.md): the data tree is built, never committed.\n"
            "web/node_modules/\nweb/dist/\nsite/\n"
        ).encode("utf-8"),
    }
    files = sorted(fixture)

    def clean():
        bad, counts = run_all(files, fixture)
        assert not bad, "clean fixture produced failures: {}".format(bad)
        assert counts == {"substrings": [], "remote_origins": [],
                          "dependency_names": []}, counts

    check("clean fixture: all seven checks pass", clean)

    def census_counts_zero():
        _, counts = run_all(files, fixture, check_numbers=(5,))
        assert counts["substrings"] == [], counts
        assert counts["remote_origins"] == [], counts

    check("check 5 census counts 0 forbidden substrings and 0 remote origins",
          census_counts_zero)

    def layout_catches_a_missing_file():
        thin = dict(fixture)
        del thin["web/src/route.ts"]
        bad, _ = run_all([f for f in files if f != "web/src/route.ts"], thin, check_numbers=(1,))
        assert len(bad) == 1 and "src/route.ts" in bad[0], bad

    check("check 1 fails on a missing src/route.ts", layout_catches_a_missing_file)

    def pins_are_exact():
        for name in ("1.2.3", "1.2.3-beta.1", "10.24.3"):
            assert PIN_RE.match(name), name
        for name in ("^1.2.3", "~1.2.3", "*", "latest", ">=1.2.3", "1.x",
                     "workspace:*", "file:../x", "git+https://x"):
            assert not PIN_RE.match(name), name

    check("check 2 exact-pin regex accepts a pin and rejects a range",
          pins_are_exact)

    def loose_pin_is_injected():
        loose = dict(fixture)
        pkg = json.loads(loose["web/package.json"].decode("utf-8"))
        pkg["dependencies"]["preact"] = "^10.0.0"
        loose["web/package.json"] = json.dumps(pkg, indent=2).encode("utf-8")
        bad, _ = run_all(files, loose, check_numbers=(2,))
        assert bad, "a ^10.0.0 pin was accepted"
        assert any("version pin" in b for b in bad), bad

    check("check 2 catches a caret range in dependencies", loose_pin_is_injected)

    def unknown_dep_is_a_finding():
        extra = dict(fixture)
        pkg = json.loads(extra["web/package.json"].decode("utf-8"))
        pkg["dependencies"]["preact-router"] = "4.1.2"
        extra["web/package.json"] = json.dumps(pkg, indent=2).encode("utf-8")
        bad, _ = run_all(files, extra, check_numbers=(2,))
        assert any("preact-router" in b for b in bad), bad

    check("check 2 flags a dependency outside the § 0 stack decision",
          unknown_dep_is_a_finding)

    def strict_off_is_caught():
        loose = dict(fixture)
        loose["web/tsconfig.json"] = json.dumps(
            {"compilerOptions": {"strict": False}}).encode("utf-8")
        bad, _ = run_all(files, loose, check_numbers=(3,))
        assert any("strict" in b for b in bad), bad

    check("check 3 catches strict: false", strict_off_is_caught)

    def tsconfig_comment_is_caught():
        loose = dict(fixture)
        loose["web/tsconfig.json"] = b'{\n  // nope\n  "compilerOptions": { "strict": true }\n}\n'
        bad, _ = run_all(files, loose, check_numbers=(3,))
        assert any("comment" in b for b in bad), bad

    check("check 3 catches a // comment in tsconfig.json (JSON.parse cannot read it)",
          tsconfig_comment_is_caught)

    def wrong_base_is_caught():
        loose = dict(fixture)
        loose["web/vite.config.ts"] = b'export default { base: "/", build: { outDir: "dist" } };\n'
        bad, _ = run_all(files, loose, check_numbers=(4,))
        assert any("base" in b for b in bad), bad

    check("check 4 catches base: \"/\" instead of /Hexapla/app/", wrong_base_is_caught)

    def remote_origin_is_caught():
        loose = dict(fixture)
        loose["web/index.html"] = (
            b'<!DOCTYPE html>\n<html lang="en" dir="ltr">\n'
            b'<link href="https://fonts.googleapis.com/css" rel="stylesheet">\n</html>\n'
        )
        bad, counts = run_all(files, loose, check_numbers=(5,))
        assert counts["remote_origins"], "a Google Fonts <link> was not censused"
        assert any("remote-origin" in b for b in bad), bad

    check("check 5b catches a remote <link href> in web/index.html",
          remote_origin_is_caught)

    def origin_outside_scope_is_not_censused():
        # README.md may name a host in prose; the prohibition is about what
        # the BUILT app loads at runtime.
        loose = dict(fixture)
        loose["web/README.md"] = b"# hexapla-web\n\nSee https://example.invalid for notes.\n"
        bad, counts = run_all(files, loose, check_numbers=(5,))
        assert counts["remote_origins"] == [], counts
        assert not bad, bad

    check("check 5b leaves web/README.md prose alone (scope is src/ + index.html)",
          origin_outside_scope_is_not_censused)

    def telemetry_is_caught():
        loose = dict(fixture)
        loose["web/src/main.tsx"] = b'import "https://cdn.example/telemetry.js";\n'
        bad, counts = run_all(files, loose, check_numbers=(5,))
        assert counts["substrings"], counts
        assert counts["remote_origins"], counts
        assert any("forbidden-strings" in b for b in bad), bad
        assert any("remote-origin" in b for b in bad), bad

    check("check 5 catches telemetry AND the CDN import in one line", telemetry_is_caught)

    def route_without_the_comment_is_caught():
        loose = dict(fixture)
        loose["web/src/route.ts"] = b"export function parseRoute(h) { return null; }\n"
        bad, _ = run_all(files, loose, check_numbers=(6,))
        assert any("0-based" in b or "1-based" in b for b in bad), bad

    check("check 6 catches a route.ts with no boundary comment", route_without_the_comment_is_caught)

    def route_without_the_clamp_guard_is_caught():
        loose = dict(fixture)
        src = fixture["web/src/route.ts"].decode("utf-8").replace(
            "if (!Number.isInteger(n) || n < 1) return null;",
            "if (!Number.isInteger(n)) return null;")
        loose["web/src/route.ts"] = src.encode("utf-8")
        bad, _ = run_all(files, loose, check_numbers=(6,))
        assert any("1-based" in b for b in bad), bad

    check("check 6 catches a parser that accepts /0 instead of returning null",
          route_without_the_clamp_guard_is_caught)

    def gitignore_drift_is_caught():
        loose = dict(fixture)
        loose[".gitignore"] = b"# data is built, never committed\nweb/node_modules/\nweb/dist/\n"
        bad, _ = run_all(files, loose, check_numbers=(7,))
        assert any("site/" in b for b in bad), bad

    check("check 7 catches a .gitignore missing the site/ line", gitignore_drift_is_caught)

    def missing_tree_is_could_not_run():
        try:
            run_all([], {})
        except CouldNotRun:
            return
        raise AssertionError("an empty tree did NOT raise CouldNotRun — it would exit 0-ish")

    check("an absent web/ tree raises CouldNotRun (-> exit 2), never a pass",
          missing_tree_is_could_not_run)

    # ---- anti-under-reporting: a WRONG fixture must go red ----------------
    # `check()` asserts the function RETURNED a non-False value, which is not
    # the same as asserting it FOUND the defect. The clean-fixture assertion
    # above already uses `assert not bad`; this does it per check, so a check
    # that quietly returns [] on bad input fails the selftest instead of
    # sitting green in every future run.
    thin_route = dict(fixture)
    del thin_route["web/src/route.ts"]

    def each_check_goes_red_on_its_own_bad_input():
        """Every check, one corrupted fixture each — all seven, not a sample."""
        # check 2 owns the pins; check 3 owns strict; check 4 owns base;
        # check 5 owns the census; check 6 owns the route contract; check 7
        # owns .gitignore; check 1 owns the file list.
        loose_pin = dict(fixture)
        pkg = json.loads(loose_pin["web/package.json"].decode("utf-8"))
        pkg["devDependencies"]["preact"] = "^10.0.0"
        loose_pin["web/package.json"] = json.dumps(pkg, indent=2).encode("utf-8")
        no_strict = dict(fixture)
        no_strict["web/tsconfig.json"] = b'{"compilerOptions": {"strict": false}}'
        no_base = dict(fixture)
        no_base["web/vite.config.ts"] = b'export default { build: { outDir: "dist" } };'
        analytics = dict(fixture)
        analytics["web/src/app.tsx"] = b'import "gtag";\n'
        no_route_comment = dict(fixture)
        no_route_comment["web/src/route.ts"] = b"export function parseRoute(h) {}\n"
        no_site_line = dict(fixture)
        no_site_line[".gitignore"] = b"# comment\nweb/node_modules/\nweb/dist/\n"

        pairs = (
            ("check 1", thin_route, (1,), [f for f in files if f != "web/src/route.ts"]),
            ("check 2", loose_pin, (2,), files),
            ("check 3", no_strict, (3,), files),
            ("check 4", no_base, (4,), files),
            ("check 5", analytics, (5,), files),
            ("check 6", no_route_comment, (6,), files),
            ("check 7", no_site_line, (7,), files),
        )
        for name, corrupted, numbers, case_files in pairs:
            bad, _ = run_all(case_files, corrupted, check_numbers=numbers)
            assert bad, "{} passed a deliberately wrong fixture".format(name)
            # and the clean fixture still passes the ones that were not corrupted
            clean_bad, _ = run_all(files, fixture, check_numbers=numbers)
            assert not clean_bad, "{} fails the CLEAN fixture: {}".format(name, clean_bad)

    check("all seven checks go red on a wrong fixture (full denominator, no sample)",
          each_check_goes_red_on_its_own_bad_input)

    # ---- the known-bad controls -------------------------------------------
    # Honoured only behind _IN_SELFTEST, only here. Each must make its own
    # check FAIL while the others stay green — 0 and 0 would be a broken
    # control, not a pass.
    donation = os.environ.get("HEXAPLA_WEBSCAF_FAKE_DONATION") == "1"
    loosepin = os.environ.get("HEXAPLA_WEBSCAF_FAKE_LOOSE_PIN") == "1"

    if donation:
        def fake_donation():
            injected = {"web/src/app.tsx": [(1, "const tip = \"https://yoomoney.ru/to/123\";")]}
            bad, counts = run_all(files, fixture, extra_lines=injected, check_numbers=(5,))
            assert counts["substrings"], "the injected yoomoney line was not censused"
            assert any("forbidden-strings census" in b for b in bad), bad
            assert any("yoomoney" in b for b in bad), bad
            # The name must land where the brief says it will: on check 5.
            assert not any(b.startswith("FAIL - version pin") for b in bad), bad
            # The rest of the scaffold is untouched by the injection, so the
            # other checks must still pass — the control isolates check 5.
            other, _ = run_all(files, fixture, check_numbers=(1, 2, 3, 4, 6, 7))
            assert not other, "the injection also broke an unrelated check: {}".format(other)
            # And the CLEAN fixture must still pass check 5, or the control is
            # firing on the fixture rather than on the injection.
            clean_bad, clean_counts = run_all(files, fixture, check_numbers=(5,))
            assert not clean_bad, "check 5 fails the clean fixture: {}".format(clean_bad)
            assert clean_counts["substrings"] == [], clean_counts

        check("known-bad HEXAPLA_WEBSCAF_FAKE_DONATION=1: check 5 FAILS on yoomoney",
              fake_donation)

    if loosepin:
        def fake_loose_pin():
            loose = dict(fixture)
            pkg = json.loads(loose["web/package.json"].decode("utf-8"))
            pkg["devDependencies"]["preact"] = "^10.0.0"
            loose["web/package.json"] = json.dumps(pkg, indent=2).encode("utf-8")
            bad, _ = run_all(files, loose, check_numbers=(2,))
            assert bad, "the injected ^10.0.0 pin was accepted"
            assert any("version pin" in b for b in bad), bad
            assert any("preact" in b for b in bad), bad
            assert not any("forbidden-strings" in b for b in bad), bad
            other, _ = run_all(files, loose, check_numbers=(1, 3, 4, 5, 6, 7))
            assert not other, "the injection also broke an unrelated check: {}".format(other)
            clean_bad, _ = run_all(files, fixture, check_numbers=(2,))
            assert not clean_bad, "check 2 fails the clean fixture: {}".format(clean_bad)

        check("known-bad HEXAPLA_WEBSCAF_FAKE_LOOSE_PIN=1: check 2 FAILS on ^10.0.0",
              fake_loose_pin)

    if not donation and not loosepin:
        print("NOTE - no known-bad env var set: only the clean fixtures ran. "
              "Run once with HEXAPLA_WEBSCAF_FAKE_DONATION=1 and once with "
              "HEXAPLA_WEBSCAF_FAKE_LOOSE_PIN=1 — 0 and 0 would prove nothing.")

    print("")
    print("selftest: {}/{} assertions passed".format(sum(results), sum(1 for r in results)))
    # A control run is a FAILING run: the whole point of it is that the check
    # it targets goes red. A green selftest under a known-bad env var means
    # the control did not fire, which is the same finding as a broken check —
    # so it exits 1, exactly as the brief's controls require. Grading note:
    # wb_run.py extracts rc from the LAST line matching `rc=`, so nothing here
    # may print a second one.
    if not all(results):
        return 1
    if donation or loosepin:
        print("control fired: the known-bad env var made its check fail (above), "
              "so this run is rc 1 BY DESIGN.")
        return 1
    return 0


def run_route_tests():
    """Run web/src/route.test.ts under node's type stripping, if node is here.

    This is the ONE part of route.ts that can be checked by BEHAVIOUR rather
    than by grep, and behaviour is what the boundary bug lived in: an earlier
    draft used `null` for both "malformed" and "no verse given", so a plain
    chapter link parsed as malformed. A text check cannot see that.

    Returns (status, detail) where status is "pass", "fail" or "not-run".
    ⚠ "not-run" is NOT a pass and the caller must print it as a gap.
    """
    test_rel = "web/src/route.test.ts"
    if not (REPO / test_rel).is_file():
        return "not-run", "{} is absent".format(test_rel)
    node = shutil.which("node")
    if not node:
        return "not-run", "no node on PATH in this environment"
    try:
        r = subprocess.run(
            [node, "--experimental-strip-types", "src/route.test.ts"],
            cwd=str(WEB), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return "not-run", "node could not be run: {}".format(e)
    tail = (r.stdout or "").strip().splitlines()
    tail = tail[-1] if tail else (r.stderr or "").strip()[:200]
    if r.returncode == 0:
        return "pass", tail
    return "fail", "rc={} {}".format(r.returncode, tail)


def real_run(root=None):
    """Check the real tree. Returns a process exit code."""
    try:
        files = web_files()
        blobs = {rel: read_bytes(rel) for rel in files}
        blobs[".gitignore"] = read_bytes(".gitignore")
        bad, counts = run_all(files, blobs)
    except CouldNotRun as e:
        print("COULD NOT RUN - {}".format(e))
        return 2

    scanned = len([f for f in files if f != ".gitignore"])
    print("web/ scaffold check — {} file(s) under web/, {} censused for "
          "forbidden strings".format(scanned, scanned))
    print("census: {} forbidden substring hit(s), {} remote-origin hit(s) "
          "(expected 0 and 0)".format(
              len(counts["substrings"]), len(counts["remote_origins"])))
    for line in counts["substrings"] + counts["remote_origins"]:
        print("    " + line)
    dep_hits = counts.get("dependency_names") or []
    if dep_hits:
        print("NOTE - {} forbidden-substring hit(s) in a generated dependency "
              "manifest. These are PACKAGE NAMES in the dependency graph, not "
              "code in the app, and they do not fail the run - but read them:"
              .format(len(dep_hits)))
        for line in dep_hits[:10]:
            print("    " + line)

    route_status, route_detail = run_route_tests()
    if route_status == "fail":
        bad = list(bad) + [fail_line("route behaviour", route_detail)]
    if bad:
        for line in bad:
            print(line)
        print("")
        print("{} problem(s) — web/ scaffold REJECTED".format(len([b for b in bad
                                                                  if b.startswith("FAIL")])))
        return 1
    print("")
    print("OK - layout, pins, strict, base, census and the route contract all pass")
    print("NOTE - pin EXISTENCE is not checked: {} pin(s) could not be "
          "corroborated offline (no network, no npm cache entry on this "
          "machine): {}".format(
              len(PINS_UNVERIFIED_OFFLINE), ", ".join(PINS_UNVERIFIED_OFFLINE)))
    if route_status == "pass":
        print("OK   - route BEHAVIOUR verified by running "
              "web/src/route.test.ts under node: {}".format(route_detail))
    else:
        print("NOTE - route behaviour NOT verified ({}). The text checks above "
              "prove the contract is written down, not that it holds. That is "
              "a gap, not a pass.".format(route_detail))
    print("NOTE - the rest of src/*.ts[x] was NOT compiled or type-checked "
          "here. `npm install && npm run build` is the planner's acceptance, "
          "not this script's.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true",
                    help="run every check against in-memory fixtures, never the real tree")
    ap.add_argument("--root", type=Path, default=None,
                    help="unused; the tree is always the repo's own web/ (kept for symmetry)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return real_run(args.root)


if __name__ == "__main__":
    sys.exit(main())
