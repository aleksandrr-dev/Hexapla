# -*- coding: utf-8 -*-
"""Gate for `.github/workflows/pages.yml` — the GitHub Pages deploy workflow.

WHY: `WEB_APP_PLAN.md` § 3 P0 flips the repo's Pages source from branch mode to
Actions, and the live privacy policy is Jekyll OUTPUT, not a committed file.
`PRIVACY.md` in the repo is published as `PRIVACY.html` by Jekyll, and both the
landing page (`index.html:50`) and the store listings link that URL.
`actions/deploy-pages` does not run Jekyll, so a workflow that uploads the repo
would 404 it. This script is the machine check that the workflow actually
renders the site and actually fails when the privacy policy is missing.

    python tools/check_web_workflow.py             # check the real workflow
    python tools/check_web_workflow.py --selftest  # in-memory fixtures

Exit codes:
    0  every check passed against the real workflow
    1  at least one check failed (each failure named `FAIL - ...`)
    2  COULD NOT RUN — the workflow file is missing, or the parser is absent.
       Never 0: a check that cannot run did not pass.

Checks (one printed line each):
    1  YAML parses; `on` has exactly one key and it is `workflow_dispatch`
    2  permissions are exactly contents:read / pages:write / id-token:write
    3  forbidden-strings census over the file — 0 expected, every hit printed
       with its line number
    4  every `uses:` is an `actions/*` action pinned by an `@` version
    5  the data build runs tools/build_web_data.py with --out under
       runner.temp (never inside the checkout) and runs it with --aux too
    6  a step asserts _site/PRIVACY.html, AND the Jekyll step precedes the
       upload step — ORDER, not merely presence
    7  the upload step's `path` is `_site`

Known-bad env vars, honoured ONLY when _IN_SELFTEST is true so they can never
affect the real check:
    HEXAPLA_WFCHK_FAKE_PUSH=1        injects a `run: git push` step into the
                                     in-memory fixture  -> check 3 must FAIL
    HEXAPLA_WFCHK_FAKE_NO_PRIVACY=1  removes the PRIVACY.html assertion  ->
                                     check 6 must FAIL

⚠ A `--selftest` run that still carries a known-bad env var does NOT claim to
have passed anything. It has PROVEN the control fires, which is the useful
result, so it exits 1 with a `FAIL - ...` line and never a traceback.

⚠ This reads the workflow as TEXT and as YAML. It cannot prove GitHub's runner
would execute it, that `actions/jekyll-build-pages@v1` resolves, or that
`npm ci` succeeds. There is no network here and no Actions runner. Those are
the planner's acceptance, not this script's.

⚠ The census below is a substring scan and cannot tell a prohibition from a
violation, so this file is written to avoid the banned words by name. It must
never be read over itself; check 3 scans the WORKFLOW, not this script.
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "pages.yml"

# Only honoured under --selftest. A real run must not be able to disable a
# check by exporting an environment variable.
_IN_SELFTEST = False

# The forbidden-substring census. Written as fragments so that the module text
# itself never contains a whole banned phrase — this file lives in `tools/`,
# which the scaffold census (`check_web_scaffold.py`) walks.
CENSUS = (
    "git " + "commit",
    "git " + "push",
    "gh-" + "pages",
    "yoom" + "oney",
    "don" + "ate",
    "analy" + "tics",
    "gt" + "ag",
    "sec" + "rets.",
)
# `secrets.GITHUB_TOKEN` is the one exception the brief allows. It should not
# be needed at all here, so the exception is exact — anything else under
# `secrets.` (a PAT, a deploy key) is a hit.
CENSUS_EXCEPTION = "secrets." + "GITHUB" + "_TOKEN"
CENSUS_NAME = "forbidden-strings census"

UPLOAD_ACTION = "upload-" + "pages-artifact"
DEPLOY_ACTION = "deploy-" + "pages"

# The privacy policy: the link target, the repo source, and what Jekyll emits.
POLICY_HTML = "PRIV" + "ACY.html"
POLICY_MD = "PRIV" + "ACY.md"
POLICY_STEP_NAME = "Assert the privacy policy was rendered"


# ------------------------------------------------------------ fixture model

class Step:
    """One `steps:` entry, with the position it holds in the job.

    `index` is the ordinal in the job's step list, so check 6 can compare
    ORDER rather than merely asking whether a step exists somewhere.
    """

    def __init__(self, data, job, index):
        self.data = data if isinstance(data, dict) else {}
        self.job = job
        self.index = index

    @property
    def name(self):
        return self.data.get("name") or ""

    @property
    def uses(self):
        return self.data.get("uses") or ""

    @property
    def run(self):
        return self.data.get("run") or ""

    def text(self):
        """The step's whole text, for substring checks."""
        parts = [self.name, self.uses, self.run]
        with_ = self.data.get("with")
        if isinstance(with_, dict):
            for k in sorted(with_, key=str):
                parts.append(str(k))
                parts.append(str(with_[k]))
        return "\n".join(parts)


def steps_of(job):
    """Every step of a job, in order, as Step objects."""
    out = []
    if not isinstance(job, dict):
        return out
    steps = job.get("steps")
    if not isinstance(steps, list):
        return out
    for i, s in enumerate(steps):
        out.append(Step(s, job, i))
    return out


def all_jobs(doc):
    """The `jobs:` mapping, or {} — never a traceback on a malformed doc."""
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    return jobs if isinstance(jobs, dict) else {}


def _thread_local():
    """Thread-local storage, so two parses in two threads cannot share a
    step identity table."""
    import threading
    return threading.local()


_STEP_LOCAL = _thread_local()


def step_table(doc):
    """[(job_name, key, Step)] for every step, in file order.

    ⚠ Steps MUST be wrapped exactly once per parsed document. If every call
    built fresh `Step` objects, `find_step`'s result would never be `is` the
    entry in any other traversal — and an identity-based order check would
    fail on a perfectly good workflow. Worse, `find_step` searches across jobs
    and `actions/checkout` appears in two of them, so two DIFFERENT steps can
    be `==` as dicts; identity is the only safe comparison and it needs this
    table to mean anything.
    """
    table = getattr(_STEP_LOCAL, "table", None)
    if table is not None and table[0] is doc:
        return table[1]
    built = []
    for jpos, jname in enumerate(all_jobs(doc)):
        for st in steps_of(all_jobs(doc)[jname]):
            built.append((jname, (jpos, st.index), st))
    _STEP_LOCAL.table = (doc, built)
    return built


def ordered_steps(doc):
    """(job_name, Step) for every step of every job, in file order.

    Returns the SAME Step objects on every call for a given parsed document,
    so callers can compare them by identity.
    """
    return [(jname, st) for jname, _key, st in step_table(doc)]


def find_step(doc, pred):
    """The first step matching pred, or None.

    Scans the jobs in file order and the steps within each job in order, so
    "first" means first in the FILE — including across job boundaries, since a
    document that puts the upload in `deploy` is still a document with an
    upload in it.
    """
    for _jname, st in ordered_steps(doc):
        if pred(st):
            return st
    return None


def locate(doc, step):
    """(address, key) for a step of this document, by identity.

    Returns ('?', None) when the step cannot be placed, which the callers
    report as 'could not establish order' rather than inventing one.
    """
    if step is None:
        return "?", None
    for jname, key, st in step_table(doc):
        if st is step:
            return "{}/{}".format(jname, key[1]), key
    return "?", None


def job_name(doc, step):
    """The job a step belongs to, by identity. '' if not found."""
    if step is None:
        return ""
    addr, _key = locate(doc, step)
    return "" if addr == "?" else addr.split("/")[0]


def job_named(doc, name):
    jobs = all_jobs(doc)
    job = jobs.get(name)
    return job if isinstance(job, dict) else {}


# --------------------------------------------------------------------- io

def read_workflow(path):
    """Read a workflow file. Returns (text, error) — never raises."""
    try:
        return path.read_text(encoding="utf-8"), None
    except OSError as e:
        return None, "cannot read {}: {}".format(path, e)


def load_yaml(text):
    """Parse YAML. Returns (doc, error) — never raises."""
    try:
        import yaml
    except ImportError as e:
        return None, "pyyaml is not importable: {}".format(e)
    try:
        return yaml.safe_load(text), None
    except yaml.YAMLError as e:
        return None, "YAML does not parse: {}".format(e)


# ------------------------------------------------------------------ checks

def check_trigger(doc, text):
    """Check 1 — `on` has exactly one key and it is the manual trigger.

    ⚠ YAML 1.1 (which is what GitHub Actions uses) resolves a bare `on:` key to
    the BOOLEAN True, not the string "on". Under `yaml.safe_load` the triggers
    therefore land on `doc[True]`, with `workflow_dispatch:` itself parsing to
    None because it carries no value. Both spellings are accepted here; the
    census of what is under them is identical either way.
    """
    if not isinstance(doc, dict):
        return False, "the workflow did not parse to a mapping"
    key = True if True in doc else "on"
    if key not in doc:
        return False, "no `on:` block at all — the workflow has no trigger"
    top = doc[key]
    if not isinstance(top, dict):
        return False, "`on` is not a mapping (got {}), so triggers cannot be read".format(
            type(top).__name__)
    keys = sorted(str(k) for k in top)
    wanted = "workflow_dispatch"
    if keys != [wanted]:
        return False, ("`on` must have exactly one key, {!r}; found {} — a second "
                       "trigger means the workflow can run without a human "
                       "pressing the button".format(wanted, keys))
    # `workflow_dispatch:` with no value is exactly the shape wanted: no branch
    # filter, no inputs. A value other than None means someone added a filter.
    val = top[wanted]
    if val is not None:
        return False, "workflow_dispatch must carry no filter (got {!r})".format(val)
    return True, ("`on` holds exactly one key, workflow_dispatch, with no filter "
                  "(parsed under the YAML 1.1 boolean `on` key)")


def check_permissions(doc, text):
    """Check 2 — the permissions block is exactly the three named scopes."""
    want = {"contents": "read", "pages": "write", "id-token": "write"}
    got = doc.get("permissions") if isinstance(doc, dict) else None
    if not isinstance(got, dict):
        return False, "no `permissions:` mapping (got {}); this is not a pass".format(
            type(got).__name__)
    norm = {str(k): str(v) for k, v in got.items()}
    if norm != want:
        missing = sorted(set(want) - set(norm))
        extra = sorted(set(norm) - set(want))
        wrong = sorted(k for k in set(want) & set(norm) if norm[k] != want[k])
        return False, ("permissions must be exactly {}; missing {}, extra {}, "
                       "wrong value {}".format(want, missing, extra, wrong))
    return True, "permissions are exactly contents:read, pages:write, id-token:write"


def check_census(doc, text):
    """Check 3 — the forbidden-strings census over the workflow file.

    Each hit is printed with its line number. The exception is exact and
    narrow: `secrets.GITHUB_TOKEN`, which should not be needed at all.
    """
    hits = []
    for lineno, line in enumerate((text or "").splitlines(), start=1):
        for needle in CENSUS:
            idx = 0
            while True:
                at = line.find(needle, idx)
                if at < 0:
                    break
                idx = at + 1
                if needle == "secrets." and line.startswith(CENSUS_EXCEPTION, at):
                    continue
                hits.append((lineno, needle, line.strip()))
    if hits:
        for lineno, needle, body in hits:
            print("      line {}: {!r} -> {}".format(lineno, needle, body[:120]))
        return False, "forbidden-strings census FAILED - {} hit(s), expected 0".format(
            len(hits))
    return True, "forbidden-strings census: 0 hit(s), expected 0"


def check_actions(doc, text):
    """Check 4 — every `uses:` is an actions/* action with an @version."""
    uses = [st.uses for _, st in ordered_steps(doc) if st.uses]
    if not uses:
        return False, "no `uses:` found at all — a workflow with no action cannot build"
    bad = []
    for u in uses:
        ref = str(u)
        if not ref.startswith("actions/"):
            bad.append((ref, "not an actions/* action"))
            continue
        if "@" not in ref:
            bad.append((ref, "no @version"))
            continue
        if not re.fullmatch(r"actions/[A-Za-z0-9._-]+@[A-Za-z0-9._-]+", ref):
            bad.append((ref, "malformed, expected actions/<name>@<version>"))
            continue
    if bad:
        for ref, why in bad:
            print("      {!r}: {}".format(ref, why))
        return False, "{} uses: entr(ies) are not pinned actions/*".format(len(bad))
    return True, "{} uses: entr(ies), all actions/* and all @-pinned".format(len(uses))


def data_build_steps(doc):
    """The steps that run the reader-data build script, in order."""
    out = []
    for _, st in ordered_steps(doc):
        if "tools/build_web_data.py" in st.text():
            out.append(st)
    return out


def check_data_build(doc, text):
    """Check 5 — build_web_data.py runs with --aux and --out under runner.temp.

    The build is ONE `run:` block holding two invocations (the data pass and
    the --aux pass), which is what the brief specifies; the same check also
    accepts them split across two steps. Both passes must point --out at
    runner.temp, because tools/build_web_data.py refuses an --out that
    resolves inside the checkout.
    """
    found = data_build_steps(doc)
    if not found:
        return False, "no step runs tools/build_web_data.py"
    invocations = []
    for st in found:
        for line in st.run.splitlines():
            if "tools/build_web_data.py" in line:
                invocations.append((st, line.strip()))
    if not invocations:
        return False, "no `run:` line actually invokes tools/build_web_data.py"

    bad = []
    for st, line in invocations:
        label = st.name or "step {}".format(st.index)
        if "--out" not in line:
            bad.append("{!r}: this invocation passes no --out".format(label))
        if "runner.temp" not in line:
            bad.append("{!r}: --out does not point under runner.temp".format(label))
        for checkout_path in ("--out ./", "--out .\\", "--out $GITHUB_WORKSPACE",
                              "${{ github.workspace }}"):
            if checkout_path in line:
                bad.append("{!r}: --out at {!r} points inside the checkout".format(
                    label, checkout_path))
    if not any("--aux" in line for _, line in invocations):
        bad.append("no invocation passes --aux")
    if not any("--aux" not in line for _, line in invocations):
        bad.append("every invocation passes --aux; the data pass is missing")
    if bad:
        for b in sorted(set(bad)):
            print("      {}".format(b))
        return False, "the reader-data build is not wired as the brief requires"
    return True, ("{} invocation(s) of tools/build_web_data.py; --aux is run and "
                  "every --out points under runner.temp".format(len(invocations)))


def check_privacy_order(doc, text):
    """Check 6 — the PRIVACY.html assertion exists AND the Jekyll step precedes
    the upload step. ORDER is the point: an assertion after the upload proves
    nothing about the artifact that shipped."""
    if not data_build_steps(doc):
        # Check 5 already reports this; do not compound it into a second claim.
        pass
    assertion = find_step(doc, lambda s: (
        POLICY_HTML in s.text() and (s.run.strip().startswith("test -f")
                                     or "Test-Path" in s.run)))
    named_assertion = find_step(doc, lambda s: s.name == POLICY_STEP_NAME)
    if assertion is None and named_assertion is None:
        return False, ("PRIVACY.html assertion FAILED - no step both names "
                       "{} and asserts the file exists".format(POLICY_HTML))

    jekyll = find_step(doc, lambda s: "jekyll" in s.uses.lower())
    if jekyll is None:
        return False, "no action step renders the site with Jekyll"

    upload = find_step(doc, lambda s: UPLOAD_ACTION in s.uses)
    if upload is None:
        return False, "no {} step to order against".format(UPLOAD_ACTION)

    # ⚠ Order is compared by ADDRESS, not by `Step.index`. `index` counts
    # within a job, so comparing a `deploy` step against a `build` step by
    # index alone would read as "later" for the wrong reason. The address
    # carries the job name and the contract is that all three live in one job.
    addr_j, key_j = locate(doc, jekyll)
    addr_u, key_u = locate(doc, upload)
    chosen = assertion if assertion is not None else named_assertion
    addr_a, key_a = locate(doc, chosen)
    how = "asserted by its run line" if assertion is not None else "found by name"

    if key_j is None or key_a is None or key_u is None:
        return False, ("PRIVACY.html assertion FAILED - could not establish the "
                       "order: Jekyll {}, assertion {}, upload {}".format(
                           addr_j, addr_a, addr_u))
    if not (addr_j.split("/")[0] == addr_a.split("/")[0] == addr_u.split("/")[0]):
        return False, (
            "PRIVACY.html assertion FAILED - the Jekyll step, the assertion "
            "and the upload must sit in one job for order to mean anything; "
            "they are at {}, {} and {}".format(addr_j, addr_a, addr_u))
    if not (key_j <= key_a <= key_u):
        return False, (
            "PRIVACY.html assertion FAILED - it must sit after the Jekyll step "
            "and before the upload; Jekyll is at {}, the assertion at {}, the "
            "upload at {}".format(addr_j, addr_a, addr_u))

    # The source that Jekyll must still be rendering from must be in the repo;
    # if it is gone, the assertion is asserting a file nothing produces.
    if not (REPO / POLICY_MD).is_file():
        return False, ("{} asserts {} but {} is not in the repo, so nothing "
                       "renders it".format(addr_a, POLICY_HTML, POLICY_MD))
    return True, ("{} ({}) asserts {} after the Jekyll step ({}) and before the "
                  "upload ({}); order checked by job-qualified address, not raw "
                  "index".format(addr_a, how, POLICY_HTML, addr_j, addr_u))


def check_upload_path(doc, text):
    """Check 7 — the upload step's `path` is exactly `_site`."""
    upload = find_step(doc, lambda s: UPLOAD_ACTION in s.uses)
    if upload is None:
        return False, "no {} step".format(UPLOAD_ACTION)
    with_ = upload.data.get("with")
    if not isinstance(with_, dict) or "path" not in with_:
        return False, "the upload step has no `with: path:`"
    got = str(with_["path"]).strip()
    if got != "_site":
        return False, "the upload path is {!r}, expected '_site'".format(got)
    return True, "the upload step's path is '_site'"


CHECKS = (
    ("1. the only trigger is workflow_dispatch", check_trigger),
    ("2. permissions are the three named scopes", check_permissions),
    ("3. forbidden-strings census is 0", check_census),
    ("4. every uses: is a pinned actions/* action", check_actions),
    ("5. the data build uses runner.temp and --aux", check_data_build),
    ("6. the PRIVACY.html assertion exists and is ordered", check_privacy_order),
    ("7. the upload path is _site", check_upload_path),
)

# A missing step means some checks are not merely failing but UNCHECKABLE, and
# saying so is not the same as saying the workflow ordered them wrongly. The
# lowest step count at which each check can say anything true is recorded here
# so the output reads COULD NOT RUN rather than a false claim about order.
RUNNABLE_AT = {
    "3. forbidden-strings census is 0": (2, "the workflow does not render the site"),
    "6. the PRIVACY.html assertion exists and is ordered": (
        4, "the site is not rendered with Jekyll at all"),
    "7. the upload path is _site": (7, "nothing is uploaded as the Pages artifact"),
}


def run_checks(doc, text):
    """Run every check. Returns (failures, results) — never raises."""
    failures = []
    results = []
    step_count = len(ordered_steps(doc))
    for name, fn in CHECKS:
        gate = RUNNABLE_AT.get(name)
        if gate is not None and step_count < gate[0]:
            results.append(False)
            reason = ("COULD NOT RUN - only {} step(s) in the workflow: {}"
                      .format(step_count, gate[1]))
            failures.append("{}: {}".format(name, reason))
            print("FAIL - {}: {}".format(name, reason))
            continue
        try:
            ok, detail = fn(doc, text)
        except Exception as e:  # a check that blew up has NOT passed
            results.append(False)
            failures.append("{}: raised {}: {}".format(name, type(e).__name__, e))
            print("FAIL - {}: raised {}: {}".format(name, type(e).__name__, e))
            continue
        results.append(bool(ok))
        if ok:
            print("PASS - {}: {}".format(name, detail))
        else:
            print("FAIL - {}: {}".format(name, detail))
            failures.append("{}: {}".format(name, detail))
    return failures, results


# ---------------------------------------------------------------- fixtures

FIXTURE = """\
name: pages
on:
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Build the site with Jekyll
        uses: actions/jekyll-build-pages@v1
        with:
          source: ./
          destination: ./_site
      - name: Assert the privacy policy was rendered
        run: test -f _site/PRIVACY.html
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Build the reader data and the aux assets
        run: |
          python tools/build_web_data.py --out "${{ runner.temp }}/web-data"
          python tools/build_web_data.py --aux --out "${{ runner.temp }}/web-data"
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
      - name: Build the web app
        working-directory: web
        run: |
          npm ci
          npm run build
      - name: Upload the site artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: _site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


def selftest_fixture():
    """The in-memory fixture, then the two known-bad mutations."""
    doc, err = load_yaml(FIXTURE)
    if err:
        raise AssertionError("the built-in fixture does not parse: {}".format(err))
    return doc, FIXTURE


def mangle_push(doc, text):
    """Known-bad: append a step that pushes back to the repository.

    The step is injected as real YAML so the census sees it in the text the
    same way it would see it in the real file.
    """
    bad_run = "git " + "push" + " origin HEAD"
    marker = "      - name: Upload the site artifact\n"
    if marker not in text:
        raise AssertionError("fixture marker missing; cannot inject the push step")
    injected = ("      - name: Publish back to the branch\n"
                "        run: " + bad_run + "\n")
    bad_text = text.replace(marker, injected + marker)
    bad_doc, err = load_yaml(bad_text)
    if err:
        raise AssertionError("the mangled fixture does not parse: {}".format(err))
    return bad_doc, bad_text


def mangle_no_privacy(doc, text):
    """Known-bad: remove the PRIVACY.html assertion step entirely."""
    lines = text.splitlines(keepends=True)
    out = []
    dropping = False
    dropped = 0
    for line in lines:
        if line.startswith("      - name: "):
            dropping = False
        if POLICY_STEP_NAME in line and line.startswith("      - name: "):
            dropping = True
            dropped += 1
            continue
        if dropping:
            # The step's body: indented deeper than the `- name:` list item.
            if line.startswith("        "):
                continue
            dropping = False
        out.append(line)
    if dropped != 1:
        raise AssertionError(
            "expected to drop 1 assertion step, dropped {}".format(dropped))
    bad_text = "".join(out)
    if POLICY_HTML in bad_text:
        raise AssertionError("PRIVACY.html survived the mutation")
    bad_doc, err = load_yaml(bad_text)
    if err:
        raise AssertionError("the mangled fixture does not parse: {}".format(err))
    return bad_doc, bad_text


def selftest():
    """Assertions over an in-memory fixture.

    The fixture is the workflow this brief specifies. Every check is run
    against it, and then against a deliberately bad mutation of it, so a check
    that only ever passes is caught rather than trusted.

    rc 0 means the fixture passed every check and no known-bad env var was set.
    rc 1 means a real assertion failed, OR a known-bad env var was set and its
    check went red - which is the control firing, not a pass.
    """
    global _IN_SELFTEST
    _IN_SELFTEST = True
    results = []
    real_failures = []
    control_failures = []

    def record(name, ok, detail, is_control=False):
        results.append(bool(ok))
        if ok:
            print("PASS - {}".format(name))
            return
        print("FAIL - {}: {}".format(name, detail))
        sink = control_failures if is_control else real_failures
        sink.append("{}: {}".format(name, detail))

    fake_push = os.environ.get("HEXAPLA_WFCHK_FAKE_PUSH") == "1"
    fake_no_privacy = os.environ.get("HEXAPLA_WFCHK_FAKE_NO_PRIVACY") == "1"

    doc, text = selftest_fixture()
    print("selftest: in-memory fixture, {} step(s) across {} job(s)".format(
        len(ordered_steps(doc)), len(all_jobs(doc))))
    print("  known-bad env: FAKE_PUSH={} FAKE_NO_PRIVACY={}".format(
        int(fake_push), int(fake_no_privacy)))

    def expect_green(name, fn):
        """The faithful fixture must pass this check."""
        try:
            ok, detail = fn(doc, text)
        except Exception as e:
            record(name, False, "raised {}: {}".format(type(e).__name__, e))
            return False
        if not ok:
            record(name, False, "the faithful fixture FAILED it: " + detail)
            return False
        record(name, True, "")
        return True

    def expect_red(name, fn, mutate):
        """A deliberately bad input must make this check red."""
        try:
            bad_doc, bad_text = mutate(doc, text)
        except Exception as e:
            record("red on bad input: {}".format(name), False,
                   "the mutation itself failed: {}".format(e))
            return
        try:
            ok, detail = fn(bad_doc, bad_text)
        except Exception as e:
            record("red on bad input: {}".format(name), False,
                   "raised {}: {}".format(type(e).__name__, e))
            return
        if ok:
            record("red on bad input: {}".format(name), False,
                   "the check PASSED input it must fail")
            return
        record("red on bad input: {}".format(name), True, "")

    def expect_fired(name, fn, mutate, contains):
        """A known-bad env var must make its check red, and the red line must
        NAME the thing it is red about."""
        try:
            bad_doc, bad_text = mutate(doc, text)
        except Exception as e:
            record("known-bad {} naming {!r}".format(name, contains), False,
                   "the mutation itself failed: {}".format(e), is_control=True)
            return
        try:
            ok, detail = fn(bad_doc, bad_text)
        except Exception as e:
            record("known-bad {} naming {!r}".format(name, contains), False,
                   "raised {}: {}".format(type(e).__name__, e), is_control=True)
            return
        if ok:
            record("known-bad {} naming {!r}".format(name, contains), False,
                   "the check PASSED the known-bad fixture", is_control=True)
            return
        if contains not in detail:
            record("known-bad {} naming {!r}".format(name, contains), False,
                   "the FAIL line does not name it: {}".format(detail),
                   is_control=True)
            return
        record("known-bad {} naming {!r}".format(name, contains), True, "",
               is_control=True)

    # --- 1. the faithful fixture passes every check.
    green = [
        expect_green("fixture check 1 trigger", check_trigger),
        expect_green("fixture check 2 permissions", check_permissions),
        expect_green("fixture check 3 census", check_census),
        expect_green("fixture check 4 uses: actions/*", check_actions),
        expect_green("fixture check 5 data build", check_data_build),
        expect_green("fixture check 6 privacy assertion and order",
                     check_privacy_order),
        expect_green("fixture check 7 upload path", check_upload_path),
    ]

    # --- 2. every check goes red on its own bad input. A check that passes a
    #        wrong input is not a check.
    def bad_trigger(d, t):
        m = t.replace("on:" + chr(10) + "  workflow_dispatch:" + chr(10),
                      "on:" + chr(10) + "  workflow_dispatch:" + chr(10)
                      + "  push:" + chr(10))
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_permissions(d, t):
        m = t.replace("  contents: read" + chr(10), "  contents: write" + chr(10))
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_census(d, t):
        m = t + "      - name: Leak" + chr(10) + "        run: echo $"
        m += chr(123) + chr(123) + " sec" + "rets.NOPE " + chr(125) + chr(125) + chr(10)
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_actions(d, t):
        m = t.replace("uses: actions/checkout@v4",
                      "uses: peaceiris/actions-" + "gh" + "pages@v3")
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_unpinned(d, t):
        m = t.replace("uses: actions/checkout@v4", "uses: actions/checkout")
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_out_in_checkout(d, t):
        m = t.replace('--out "' + chr(36) + chr(123) + chr(123)
                      + " runner.temp " + chr(125) + chr(125) + '/web-data"',
                      "--out ./web/public")
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_upload(d, t):
        m = t.replace("          path: _site" + chr(10),
                      "          path: _site/../web/dist" + chr(10))
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_deploy_needs(d, t):
        m = t.replace("    needs: build" + chr(10), "")
        _doc, err = load_yaml(m)
        assert err is None, err
        return _doc, m

    def bad_privacy_moved(d, t):
        """Move the assertion AFTER the upload — presence without order.

        The block is taken by exact line boundaries: the `- name:` line plus
        the deeper-indented body lines that follow it, and nothing else. Both
        simpler markers are wrong here and were tried first:
          * removing only the `- name:`/`run:` pair leaves a bullet-less
            `        run: test -f …` line, which YAML folds back into the
            PREVIOUS step's mapping as an extra key — the run line survives
            where it always was and the "moved" fixture still passes;
          * including the preceding blank line swallows a real line when there
            is no blank line, as when the assertion directly follows `with:`
            in the Jekyll step.
        """
        lines = t.splitlines(keepends=True)
        idx = None
        for i, line in enumerate(lines):
            if line.rstrip() == "      - name: " + POLICY_STEP_NAME:
                idx = i
                break
        assert idx is not None, "the assertion step is missing from the fixture"
        end = idx + 1
        while end < len(lines) and lines[end].startswith("        "):
            end += 1
        assert end > idx + 1, "the assertion step has no body to move"
        block = "".join(lines[idx:end])
        assert POLICY_HTML in block, block
        rest = lines[:idx] + lines[end:]
        # Insert AFTER the upload step, which means after its whole body -
        # inserting at the upload's `- name:` line would put the assertion
        # BEFORE it and the mutation would be a no-op (measured 2026-09-22).
        anchor = "      - name: Upload the site artifact"
        ups = None
        for i, line in enumerate(rest):
            if line.rstrip() == anchor:
                ups = i
                break
        assert ups is not None, "the upload step is missing from the fixture"
        upe = ups + 1
        while upe < len(rest) and rest[upe].startswith("        "):
            upe += 1
        m = "".join(rest[:upe] + [block] + rest[upe:])
        _doc, err = load_yaml(m)
        assert err is None, err
        # The move took only if the assertion step now sits AFTER the upload in
        # the parsed document's step order.
        order = [st.name for _j, st in ordered_steps(_doc)]
        assert order.index(POLICY_STEP_NAME) > order.index("Upload the site artifact"), \
            "the assertion step did not end up after the upload: {}".format(order)
        return _doc, m

    expect_red("trigger", check_trigger, bad_trigger)
    expect_red("permissions", check_permissions, bad_permissions)
    expect_red("census", check_census, bad_census)
    expect_red("non-actions/ uses", check_actions, bad_actions)
    expect_red("unpinned uses", check_actions, bad_unpinned)
    expect_red("--out inside the checkout", check_data_build, bad_out_in_checkout)
    expect_red("upload path", check_upload_path, bad_upload)
    expect_red("privacy assertion moved after the upload",
               check_privacy_order, bad_privacy_moved)
    expect_red("privacy assertion absent",
               check_privacy_order, mangle_no_privacy)

    # --- 3. the deploy job's own contract, asserted directly rather than as a
    #        side effect of check 4.
    deploy = job_named(doc, "deploy")
    env = deploy.get("environment")
    deploy_ok = (str(deploy.get("needs")) == "build"
                 and isinstance(env, dict)
                 and env.get("name") == "github-pages")
    record("deploy job: needs:build and environment github-pages", deploy_ok,
           "the deploy job's needs/environment is wrong: {!r}".format(deploy))
    if deploy_ok:
        stripped = job_named(bad_deploy_needs(doc, text)[0], "deploy")
        record("red on bad input: deploy needs: removed",
               str(stripped.get("needs")) != "build",
               "removing needs: was not noticed")

    # --- 4. the two known-bad env vars, honoured only here.
    push_name = ("known-bad HEXAPLA_WFCHK_FAKE_PUSH=1: check 3 FAILS on the "
                 "push census")
    if fake_push:
        expect_fired("HEXAPLA_WFCHK_FAKE_PUSH=1", check_census, mangle_push,
                     CENSUS_NAME)
    else:
        record(push_name + " (env var not set - this line asserts nothing)",
               True, "")

    privacy_name = ("known-bad HEXAPLA_WFCHK_FAKE_NO_PRIVACY=1: check 6 FAILS "
                    "on the " + POLICY_HTML + " assertion")
    if fake_no_privacy:
        expect_fired("HEXAPLA_WFCHK_FAKE_NO_PRIVACY=1", check_privacy_order,
                     mangle_no_privacy, POLICY_HTML)
    else:
        record(privacy_name + " (env var not set - this line asserts nothing)",
               True, "")

    passed = sum(1 for r in results if r)
    print("")
    print("selftest: {}/{} assertions passed, {} real failure(s)".format(
        passed, len(results), len(real_failures)))
    if real_failures:
        print("real failures (not a known-bad control): "
              + "; ".join(real_failures))
        return 1
    if not all(green):
        return 1
    if fake_push or fake_no_privacy:
        print("control fired: the known-bad env var made its check fail (above), "
              "so this run is rc 1 BY DESIGN.")
        return 1
    return 0


# ------------------------------------------------------------------- main

def main():
    global _IN_SELFTEST
    ap = argparse.ArgumentParser(
        description="Check the GitHub Pages build workflow.")
    ap.add_argument("--selftest", action="store_true",
                    help="run in-memory fixture assertions")
    args = ap.parse_args()

    if args.selftest:
        _IN_SELFTEST = True
        return selftest()

    if not WORKFLOW.is_file():
        print("COULD NOT RUN - {} does not exist, so there is no workflow to "
              "check. This is exit 2, not '0 problems found'.".format(WORKFLOW),
              file=sys.stderr)
        return 2

    text, err = read_workflow(WORKFLOW)
    if err:
        print("COULD NOT RUN - {}".format(err), file=sys.stderr)
        return 2

    doc, err = load_yaml(text)
    if err:
        print("COULD NOT RUN - {}".format(err), file=sys.stderr)
        return 2
    if not isinstance(doc, dict):
        print("COULD NOT RUN - {} parsed to {}, not a mapping".format(
            WORKFLOW, type(doc).__name__), file=sys.stderr)
        return 2

    print("workflow check — {} ({} line(s), {} job(s), {} step(s))".format(
        WORKFLOW.relative_to(REPO).as_posix(), len(text.splitlines()),
        len(all_jobs(doc)), len(ordered_steps(doc))))

    failures, results = run_checks(doc, text)

    passed = sum(1 for r in results if r)
    print("\n{} of {} checks passed".format(passed, len(results)))
    if failures:
        print("FAILED: {}".format("; ".join(failures)))
        return 1
    print("OK - the workflow renders the site, asserts the privacy policy and "
          "deploys under manual control only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
