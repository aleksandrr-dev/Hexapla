import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Check that every chapter ogg in <set>/<book>/<chapter>.ogg has a "
            "backup in <set>_pre_announce/<book>/<chapter>.ogg.\n"
            "Exit 0: all OK. Exit 1: any MISMATCH. Exit 2: could not run."
        )
    )
    parser.add_argument(
        "--root",
        default=r"C:\Projects\Hexapla-releases\narration",
        help="Root narration directory (default: C:\\Projects\\Hexapla-releases\\narration)",
    )
    parser.add_argument(
        "--set",
        dest="sets",
        action="append",
        default=None,
        help="Optional set key(s) to check; if omitted, scan for all <set>_pre_announce dirs.",
    )

    args = parser.parse_args()
    root = args.root

    # --- pre-flight: root must exist ---
    if not os.path.isdir(root):
        print("COULD NOT RUN - root directory does not exist: " + root)
        sys.exit(2)

    # --- discover _pre_announce dirs ---
    entries = sorted(os.listdir(root))
    pa_dirs = [e for e in entries if e.endswith("_pre_announce")]

    if args.sets is not None:
        requested = []
        for s in args.sets:
            pa_name = s + "_pre_announce"
            if pa_name not in entries:
                print("COULD NOT RUN - asked --set '" + s + "' has no _pre_announce directory.")
                sys.exit(2)
            requested.append((s, pa_name))
        for s, pa_name in requested:
            if s not in entries:
                print("COULD NOT RUN - asked --set '" + s + "' has no directory at all.")
                sys.exit(2)
        pa_lookup = {pa_name: s for s, pa_name in requested}
    else:
        if len(pa_dirs) == 0:
            print("COULD NOT RUN - zero _pre_announce directories found.")
            sys.exit(2)
        pa_lookup = {}
        for pa_name in pa_dirs:
            set_key = pa_name[: -len("_pre_announce")]
            if set_key not in entries:
                continue
            pa_lookup[pa_name] = set_key

    all_ok = True
    for pa_name, set_key in sorted(pa_lookup.items()):
        pa_path = os.path.join(root, pa_name)
        set_path = os.path.join(root, set_key)
        pa_chapters = set()
        for book in sorted(os.listdir(pa_path)):
            bp = os.path.join(pa_path, book)
            if not os.path.isdir(bp):
                continue
            for f in os.listdir(bp):
                if not f.endswith(".ogg"):
                    continue
                stem = f[: -len(".ogg")]
                if not stem.isdigit():
                    continue
                pa_chapters.add((book, stem))

        set_chapters = set()
        if os.path.isdir(set_path):
            for book in sorted(os.listdir(set_path)):
                sp = os.path.join(set_path, book)
                if not os.path.isdir(sp):
                    continue
                for f in sorted(os.listdir(sp)):
                    if not f.endswith(".ogg"):
                        continue
                    stem = f[: -len(".ogg")]
                    if not stem.isdigit():
                        continue
                    set_chapters.add((book, stem))

        total = len(set_chapters)
        backed = 0
        missing_list = []
        extra_pa_list = []
        for book, stem in sorted(set_chapters):
            if (book, stem) in pa_chapters:
                backed += 1
            else:
                missing_list.append((book, stem))
        for book, stem in sorted(pa_chapters):
            if (book, stem) not in set_chapters:
                extra_pa_list.append((book, stem))

        if len(missing_list) == 0 and len(extra_pa_list) == 0:
            print("OK        " + set_key.ljust(18) + str(total).rjust(4) + " chapters, " + str(backed).rjust(4) + " backed up")
        else:
            all_ok = False
            first_10_missing = [b + "/" + s for b, s in missing_list[:10]]
            first_10_extra = [b + "/" + s for b, s in extra_pa_list[:10]]
            miss_str = "; ".join(first_10_missing) if first_10_missing else "none"
            extra_str = "; ".join(first_10_extra) if first_10_extra else "none"
            print("MISMATCH  " + set_key.ljust(18) + str(total).rjust(4) + " chapters, " + str(backed).rjust(4) + " backed up; missing backup: " + miss_str + "; backup without chapter: " + extra_str)

    sys.exit(1 if not all_ok else 0)


if __name__ == "__main__":
    main()