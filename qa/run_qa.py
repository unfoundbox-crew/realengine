"""QA gate CLI: run label-legibility over every PNG in a renders dir.

Usage:
    python3 run_qa.py --renders <DIR> --labels "Thalamus,Hippocampus,..."
                      [--engine tesseract|apple-vision|...] [--json]
                      [--baseline DIR]

Prints PASS/FAIL per file, exits 0 iff every PNG passes.
``--json`` prints one machine-readable receipt on stdout instead (this is
what the MCP ``qa_assert`` tool consumes); human lines then go to stderr.
``--baseline DIR`` additionally runs ``views_match`` against that directory.
``--build build.json`` additionally runs ``no_overlap`` over that build's named
objects -- it needs no PNGs and no OCR, so it is the one assert that still
works when there is no browser on the machine.

Engine note (measured 2026-09-12 on the brain blockout renders): tesseract
is the portable default and misses some correctly-drawn labels; on macOS
``--engine apple-vision`` reads the same frames cleanly and ~5x faster.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asserts
from asserts import labels_present, no_overlap, views_match


def main(argv=None):
    ap = argparse.ArgumentParser(description="code-to-3d QA gate: labels legible in every render")
    ap.add_argument("--renders", required=True, help="directory of render PNGs")
    ap.add_argument("--labels", required=True, help="comma-separated expected labels")
    ap.add_argument("--engine", default=None,
                    help="OCR engine passed to zero-vision (default: %s)" % asserts.OCR_ENGINE)
    ap.add_argument("--baseline", default=None,
                    help="second renders dir to dimension-compare against")
    ap.add_argument("--build", default=None,
                    help="build.json to run the no_overlap gate over")
    ap.add_argument("--json", action="store_true",
                    help="print a JSON receipt on stdout (human lines to stderr)")
    args = ap.parse_args(argv)

    out = sys.stderr if args.json else sys.stdout
    if args.engine:
        asserts.OCR_ENGINE = args.engine

    labels = [s.strip() for s in args.labels.split(",") if s.strip()]
    receipt = {"ok": False, "renders_dir": args.renders, "labels": labels,
               "engine": asserts.OCR_ENGINE, "files": [], "views_match": None,
               "no_overlap": None}

    def bail(msg, code=2):
        receipt["error"] = msg
        print(msg, file=sys.stderr)
        if args.json:
            print(json.dumps(receipt, sort_keys=True))
        return code

    if not labels:
        return bail("no labels given")
    if not os.path.isdir(args.renders):
        return bail("not a directory: %s" % args.renders)

    pngs = sorted(f for f in os.listdir(args.renders) if f.lower().endswith(".png"))
    if not pngs:
        return bail("no PNGs in %s (render views first)" % args.renders)

    print("QA gate: %d PNG(s) in %s, labels=%s" % (len(pngs), args.renders, ",".join(labels)),
          file=out)
    all_pass = True
    for name in pngs:
        path = os.path.join(args.renders, name)
        try:
            ok, missing, _text = labels_present(path, labels)
        except RuntimeError as e:
            print("FAIL %s (OCR error: %s)" % (name, e), file=out)
            receipt["files"].append({"file": name, "pass": False, "ocr_error": str(e)})
            all_pass = False
            continue
        receipt["files"].append({"file": name, "pass": bool(ok), "missing": missing})
        if ok:
            print("PASS %s" % name, file=out)
        else:
            print("FAIL %s (missing: %s)" % (name, ", ".join(missing)), file=out)
            all_pass = False

    if args.baseline:
        rows = views_match(args.renders, args.baseline)
        receipt["views_match"] = [
            {"file": n, "a": list(a) if a else None, "b": list(b) if b else None,
             "match": m} for n, a, b, m in rows]
        mismatched = [n for n, _a, _b, m in rows if not m]
        if mismatched:
            all_pass = False
            print("FAIL views_match: %s" % ", ".join(mismatched), file=out)
        else:
            print("PASS views_match (%d file(s))" % len(rows), file=out)

    if args.build:
        overlap = no_overlap(args.build)
        receipt["no_overlap"] = overlap
        if overlap["ok"]:
            print("PASS no_overlap (%d pair(s), tolerance %g m)"
                  % (overlap["checked"], overlap["tolerance_m"]), file=out)
        else:
            all_pass = False
            detail = overlap["reason"] or ", ".join(
                "%s/%s" % (p["a"], p["b"]) for p in overlap["pairs"])
            print("FAIL no_overlap: %s" % detail, file=out)

    receipt["ok"] = all_pass
    print("RESULT: %s" % ("PASS" if all_pass else "FAIL"), file=out)
    if args.json:
        print(json.dumps(receipt, sort_keys=True))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
