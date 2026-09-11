"""QA gate CLI: run label-legibility over every PNG in a renders dir.

Usage:
    python3 run_qa.py --renders <DIR> --labels "Thalamus,Hippocampus,..."

Prints PASS/FAIL per file, exits 0 iff every PNG passes.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from asserts import labels_present


def main():
    ap = argparse.ArgumentParser(description="code-to-3d QA gate: labels legible in every render")
    ap.add_argument("--renders", required=True, help="directory of render PNGs")
    ap.add_argument("--labels", required=True, help="comma-separated expected labels")
    args = ap.parse_args()

    labels = [s.strip() for s in args.labels.split(",") if s.strip()]
    if not labels:
        print("no labels given", file=sys.stderr)
        return 2
    if not os.path.isdir(args.renders):
        print("not a directory: %s" % args.renders, file=sys.stderr)
        return 2

    pngs = sorted(f for f in os.listdir(args.renders) if f.lower().endswith(".png"))
    if not pngs:
        print("no PNGs in %s" % args.renders, file=sys.stderr)
        return 2

    print("QA gate: %d PNG(s) in %s, labels=%s" % (len(pngs), args.renders, ",".join(labels)))
    all_pass = True
    for name in pngs:
        path = os.path.join(args.renders, name)
        try:
            ok, missing, _text = labels_present(path, labels)
        except RuntimeError as e:
            print("FAIL %s (OCR error: %s)" % (name, e))
            all_pass = False
            continue
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s (missing: %s)" % (name, ", ".join(missing)))
            all_pass = False

    print("RESULT: %s" % ("PASS" if all_pass else "FAIL"))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
