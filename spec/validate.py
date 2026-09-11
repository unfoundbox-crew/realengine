#!/usr/bin/env python3
"""Validate a SCENE_SPEC.md against spec/SPEC-SCHEMA.md. Stdlib only.

Checks: required sections present, hex colors well-formed,
camera count >= 1, build-order steps numbered and gapless.
Usage: python3 spec/validate.py [path/to/SCENE_SPEC.md]
Exit 0 on PASS, 1 on FAIL.
"""
import re
import sys

REQUIRED = [  # (label, regex)
    ("units", r"(?im)^#{1,3}\s+.*units"),
    ("palette", r"(?i)palette"),
    ("collections", r"(?im)^#{1,3}\s+.*collections"),
    ("cameras", r"(?im)^#{1,3}\s+.*cameras?"),
    ("build order", r"(?i)build order"),
    ("priority rule", r"(?i)priorit"),
]

HEX_OK = re.compile(r"^(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def section(text, start_pat):
    m = re.search(start_pat, text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"(?m)^#{1,3}\s+\S", rest)
    return rest[: nxt.start() if nxt else len(rest)]


def main(path):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"FAIL: cannot read {path}: {e}")
        return 1
    errors = []

    for label, pat in REQUIRED:
        if not re.search(pat, text):
            errors.append(f"missing required section: {label}")

    bad_hex = [t for t in re.findall(r"#[0-9A-Za-z]+", text)
               if not HEX_OK.match(t[1:])]
    for t in sorted(set(bad_hex)):
        errors.append(f"malformed hex color: {t}")

    cams = sorted(set(re.findall(r"CAM_[A-Za-z0-9_]+",
                                 section(text, r"(?im)^#{1,3}\s+.*cameras?"))))
    if not cams:
        errors.append("camera count < 1 (need >= 1 CAM_* entry)")

    body = section(text, r"(?i)build order")
    nums = [int(m.group(1)) for m in re.finditer(r"(?m)^\s*(\d+)\s+\S", body)]
    if not nums:
        errors.append("build order: no numbered steps found")
    elif nums != list(range(1, len(nums) + 1)):
        errors.append(f"build order: steps not gapless from 1: {nums}")

    if errors:
        print("FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"PASS: {path}")
    print(f"  sections=6/6 hex_ok cameras={len(cams)} "
          f"build_steps={len(nums)} gapless")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "SCENE_SPEC.md"))
