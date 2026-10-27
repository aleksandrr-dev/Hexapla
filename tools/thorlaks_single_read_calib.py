"""Calibrate a SINGLE read against pages already double-read and merged.
0 model tokens.

For each page: align read A (or B) to the merged part verse by verse, token
by token; every token where the single read differs from the merged text is
an ERROR of the single read (a LOWER bound: errors both reads shared survive
into the merged part). Then run the 0-token screens on the single read and
count how many of those error tokens they flag:
  witness NEAR   thorlaks_witness_diff NEAR class (plausible misread)
  witness OTHER  no aligned witness token (revision noise lives here too)
  forbidden      a character/sort the 1644 print does not use
Reports recall (errors flagged / errors) and load (flags / tokens), and the
unflagged residual per 1,000 words, with the residual listed for review.
Usage: thorlaks_single_read_calib.py [--read A|B] [--show N] BOOK:PAGE ...
  e.g. John:80 John:87 Luke:77
"""
import difflib, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thorlaks_witness_diff as W

REL = "C:/Projects/Hexapla-releases"
# characters the 1644 fount does not print (modern forms a reader drifts into)
FORBID = re.compile(r"[ðÐáéíóúýÁÉÍÓÚÝ3Ǫöø]")


def newest(pat):
    fs = sorted(glob.glob(pat))
    return fs[-1] if fs else None


def main():
    args = [a for a in sys.argv[1:]]
    read = args[args.index("--read") + 1] if "--read" in args else "A"
    show = int(args[args.index("--show") + 1]) if "--show" in args else 0
    pages = [a for a in args if ":" in a]
    T = {"err": 0, "tok": 0, "near": 0, "other": 0, "forb": 0, "err_near": 0,
         "err_other": 0, "err_forb": 0, "err_any": 0, "near_ok": 0}
    resid = []
    for bp in pages:
        book, p = bp.split(":")
        b = book.lower().replace(" ", "")
        rd = newest("%s/_work/%s_p%s_read%s_*.md" % (REL, b, p, read))
        pt = "%s/research/_parts/%s_p%s.md" % (REL, b, p)
        if not rd or not os.path.exists(pt):
            print("skip %s: read %s part %s" % (bp, rd, os.path.exists(pt)))
            continue
        mer = {(c, v): W.toks(t) for c, vs in W.ours(pt).items() for v, t in vs}
        cls = {(c, v, i): (k, w) for c, v, i, t, k, w in W.classify(book, rd)}
        e = n = 0
        for c, vs in W.ours(rd).items():
            for v, t in vs:
                a = W.toks(t)
                m = mer.get((c, v))
                if m is None:
                    continue
                n += len(a)
                bad, sortlvl = set(), set()
                sm = difflib.SequenceMatcher(a=a, b=m, autojunk=False)
                for op, i1, i2, j1, j2 in sm.get_opcodes():
                    if op != "equal":
                        # a word the single read LOST is charged to its neighbour
                        bad.update(range(i1, i2) if i2 > i1 else [max(0, i1 - 1)])
                    if op == "replace" and i2 - i1 == j2 - j1:
                        for k in range(i2 - i1):
                            if W.skel(a[i1 + k], True) == W.skel(m[j1 + k], True):
                                sortlvl.add(i1 + k)  # case/nasal bar/accent: witness-blind by design
                for i, tok in enumerate(a):
                    k, w = cls.get((c, v, i), ("OTHER", ""))
                    f = bool(FORBID.search(tok))
                    T["near"] += k == "NEAR"
                    T["other"] += k == "OTHER"
                    T["forb"] += f
                    T["cls_" + k] = T.get("cls_" + k, 0) + 1
                    T["flag"] = T.get("flag", 0) + (k in W.FLAG or f)
                    if i in bad and i in sortlvl:
                        T["sort"] = T.get("sort", 0) + 1
                        T["sort_forb"] = T.get("sort_forb", 0) + f
                    elif i in bad:
                        e += 1
                        T["err_near"] += k == "NEAR"
                        T["err_other"] += k == "OTHER"
                        T["err_forb"] += f
                        T["ecls_" + k] = T.get("ecls_" + k, 0) + 1
                        hit = k in W.FLAG or f
                        T["err_any"] += hit
                        if not hit:
                            resid.append("%s %d:%d #%d A«%s» merged«%s» wit«%s» %s" % (
                                bp, c, v, i, tok, " ".join(m[max(0, i - 1):i + 2]), w, k))
                    elif k == "NEAR":
                        T["near_ok"] += 1
        T["err"] += e
        T["tok"] += n
        print("%-9s tokens %4d  single-read errors %3d (%.1f %%)" % (bp, n, e, 100.0 * e / max(n, 1)))
    n, e = T["tok"], T["err"]
    if not n:
        sys.exit(2)
    print("\nTOTAL tokens %d, read-%s errors vs merged %d = %.1f per 1,000 words (LOWER bound)" % (
        n, read, e, 1000.0 * e / n))
    print("flags: NEAR %d (%.1f %% of tokens), OTHER %d (%.1f %%), forbidden %d" % (
        T["near"], 100.0 * T["near"] / n, T["other"], 100.0 * T["other"] / n, T["forb"]))
    print("recall: NEAR %d/%d, OTHER %d/%d, forbidden %d/%d, NEAR|forbidden %d/%d = %.0f %%" % (
        T["err_near"], e, T["err_other"], e, T["err_forb"], e, T["err_any"], e, 100.0 * T["err_any"] / max(e, 1)))
    print("NEAR precision: %d of %d NEAR flags are single-read errors" % (T["err_near"], T["near"]))
    print("per class (tokens / of which single-read errors):", ", ".join(
        "%s %d/%d" % (c, T.get("cls_" + c, 0), T.get("ecls_" + c, 0))
        for c in ("MATCH", "NEAR", "ISO", "GAP", "EXTRA", "DUP", "OTHER")))
    print("ALL FLAGS (NEAR|ISO|GAP|EXTRA|DUP|forbidden): load %d = %.1f %% of tokens, recall %d/%d = %.0f %%" % (
        T.get("flag", 0), 100.0 * T.get("flag", 0) / n, T["err_any"], e, 100.0 * T["err_any"] / max(e, 1)))
    print("residual (unflagged): %d = %.1f per 1,000 words" % (
        e - T["err_any"], 1000.0 * (e - T["err_any"]) / n))
    for r in resid[:show]:
        print("  " + r)


main()
