#!/usr/bin/env python3
"""Run blender/build.py inside headless Blender. The documented wrapper.

Finds a Blender binary (``REALENGINE_BLENDER``, then ``blender`` on PATH,
then the standard macOS app bundle), runs::

    <blender> --background --factory-startup --python blender/build.py -- ...

and turns the build's ``CTD_BUILD_DONE {json}`` line into a JSON receipt.

No Blender on this machine means no scene: the script says so by name and
exits 3. It never falls back to something else.

Usage:
    python3 blender/run_headless.py --spec build.json --out-dir DIR
                                    [--views CAM_A,CAM_B] [--engine E]
                                    [--samples N] [--res-scale 0.25]

Prints a one-line JSON receipt on stdout; Blender's own chatter goes to
stderr. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_PY = HERE / "build.py"
MAC_BUNDLE = "/Applications/Blender.app/Contents/MacOS/Blender"
REQUIREMENT = ("a Blender binary: set REALENGINE_BLENDER=/path/to/blender, "
               "or put `blender` on PATH (blender.org/download)")


def log(msg):
    print("run_headless: %s" % msg, file=sys.stderr)


def find_blender():
    explicit = os.environ.get("REALENGINE_BLENDER")
    if explicit:
        return explicit if Path(explicit).exists() else None
    found = shutil.which("blender")
    if found:
        return found
    return MAC_BUNDLE if Path(MAC_BUNDLE).exists() else None


def run(spec, out_dir, views="", engine=None, samples=None, res_scale=1.0,
        timeout=1800):
    binary = find_blender()
    if not binary:
        return {"ok": False, "backend": "blender", "rendered": False,
                "reason": "no Blender on this machine",
                "requirement": REQUIREMENT,
                "spec": str(spec),
                "hint": ("The build JSON is ready; run the same command "
                         "anywhere Blender is installed: %s --background "
                         "--factory-startup --python blender/build.py -- "
                         "--spec %s --out-dir %s"
                         % ("<blender>", spec, out_dir))}

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [binary, "--background", "--factory-startup", "--python",
           str(BUILD_PY), "--", "--spec", str(spec), "--out-dir", str(out)]
    if views:
        cmd += ["--views", views]
    if engine:
        cmd += ["--engine", engine]
    if samples is not None:
        cmd += ["--samples", str(samples)]
    if res_scale != 1.0:
        cmd += ["--res-scale", str(res_scale)]

    log(" ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "backend": "blender",
                "error": "Blender timed out after %ds" % timeout}
    except OSError as e:
        return {"ok": False, "backend": "blender",
                "error": "could not launch %s: %s" % (binary, e)}

    sys.stderr.write(proc.stdout[-4000:])
    stats = None
    for line in proc.stdout.splitlines():
        if line.startswith("CTD_BUILD_DONE "):
            try:
                stats = json.loads(line[len("CTD_BUILD_DONE "):])
            except ValueError:
                stats = None

    blends = sorted(str(p) for p in out.glob("*.blend"))
    pngs = sorted(str(p) for p in out.glob("*.png"))
    ok = proc.returncode == 0 and bool(blends)
    receipt = {
        "ok": ok,
        "backend": "blender",
        "binary": binary,
        "returncode": proc.returncode,
        "out_dir": str(out),
        "blend": blends,
        "renders": pngs,
        "stats": stats,
    }
    if not ok:
        receipt["error"] = ("Blender exited %d without writing a .blend"
                            % proc.returncode)
        receipt["stderr_tail"] = proc.stderr.strip()[-800:]
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", required=True, help="build JSON from spec/scene_spec.py")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--views", default="")
    ap.add_argument("--engine", default=None)
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--res-scale", type=float, default=1.0)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args(argv)

    receipt = run(args.spec, args.out_dir, args.views, args.engine,
                  args.samples, args.res_scale, args.timeout)
    print(json.dumps(receipt, sort_keys=True))
    if receipt.get("ok"):
        return 0
    return 3 if "requirement" in receipt else 1


if __name__ == "__main__":
    sys.exit(main())
