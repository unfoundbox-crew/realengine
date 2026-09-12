#!/usr/bin/env python3
"""Render the named camera views of a built web scene to PNGs.

Reads ``views.json`` (written by web/build_scene.py), opens
``scene.html?view=<camera>&hud=0`` in headless Chromium, waits for
``window.REALENGINE_READY``, and screenshots at the view's resolution.

Headless Chromium is an OPTIONAL dependency. Without it this script writes
no PNGs, exits 3, and says exactly what is missing -- it never pretends.
Install with::

    pip install playwright && python3 -m playwright install chromium

Any browser can drive the same contract by hand: every row in ``views.json``
carries a ``url`` (``?view=…&labels=1&hud=0``) and a target resolution, and
the page sets ``window.REALENGINE_READY`` / ``<body data-ready="1">`` when
the frame is settled.

Usage:
    python3 web/render_views.py --scene-dir DIR [--out-dir DIR/renders]
                                [--views CAM_A,CAM_B] [--scale 1.0]

Prints a one-line JSON receipt on stdout; logs go to stderr.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIREMENT = ("headless Chromium via Playwright: "
               "pip install playwright && python3 -m playwright install chromium")


def log(msg):
    print("render_views: %s" % msg, file=sys.stderr)


def have_playwright():
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


def png_size(path):
    """(width, height) from the IHDR chunk. Same reader shape as qa/asserts."""
    import struct
    with open(path, "rb") as f:
        head = f.read(33)
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    return struct.unpack(">II", head[16:24])


def render(scene_dir, out_dir=None, only=None, scale=1.0, timeout_ms=30000):
    scene_dir = Path(scene_dir).resolve()
    manifest_path = scene_dir / "views.json"
    if not manifest_path.exists():
        return {"ok": False, "rendered": False,
                "error": "no views.json in %s (run web/build_scene.py first)"
                         % scene_dir}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    html = scene_dir / manifest["html"]
    if not html.exists():
        return {"ok": False, "rendered": False,
                "error": "manifest points at a missing page: %s" % html}

    rows = manifest["views"]
    if only:
        wanted = set(only)
        rows = [r for r in rows if r["camera"] in wanted]
        if not rows:
            return {"ok": False, "rendered": False,
                    "error": "no manifest view matches %s" % sorted(wanted)}

    out = Path(out_dir) if out_dir else scene_dir / "renders"
    out.mkdir(parents=True, exist_ok=True)

    if not have_playwright():
        return {
            "ok": False,
            "rendered": False,
            "reason": "no headless browser on this machine",
            "requirement": REQUIREMENT,
            "manifest": str(manifest_path),
            "html": str(html),
            "views": [{"camera": r["camera"], "url": r["url"],
                       "res_x": r["res_x"], "res_y": r["res_y"]} for r in rows],
            "hint": ("Drive the manifest with any browser: open "
                     "<html>?view=<camera>&hud=0, wait for "
                     "window.REALENGINE_READY, capture at res_x×res_y."),
        }

    from playwright.sync_api import sync_playwright

    renders = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=swiftshader",
                                          "--enable-unsafe-swiftshader"])
        try:
            for row in rows:
                w = max(320, int(row["res_x"] * scale))
                h = max(240, int(row["res_y"] * scale))
                page = browser.new_page(viewport={"width": w, "height": h},
                                        device_scale_factor=1)
                url = html.as_uri() + "?" + row["url"].split("?", 1)[1]
                try:
                    page.goto(url, wait_until="load", timeout=timeout_ms)
                    page.wait_for_function("window.REALENGINE_READY === true",
                                           timeout=timeout_ms)
                    target = out / row["output"]
                    page.screenshot(path=str(target))
                    size = png_size(target)
                    renders.append({"camera": row["camera"],
                                    "path": str(target),
                                    "width": size[0], "height": size[1],
                                    "bytes": target.stat().st_size})
                    log("%s -> %s (%dx%d)" % (row["camera"], target.name,
                                              size[0], size[1]))
                except Exception as exc:  # one bad view must not kill the rest
                    errors.append({"camera": row["camera"],
                                   "error": str(exc).splitlines()[0][:300]})
                    log("FAILED %s: %s" % (row["camera"],
                                           str(exc).splitlines()[0][:200]))
                finally:
                    page.close()
        finally:
            browser.close()

    return {
        "ok": bool(renders) and not errors,
        "rendered": bool(renders),
        "renders_dir": str(out),
        "renders": renders,
        "errors": errors,
        "labels": manifest.get("labels", []),
        "build_sha256": manifest.get("build_sha256", ""),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scene-dir", required=True,
                    help="directory containing scene.html + views.json")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--views", default="",
                    help="comma-separated camera names (default: all)")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--timeout-ms", type=int, default=30000)
    args = ap.parse_args(argv)

    only = [s.strip() for s in args.views.split(",") if s.strip()]
    receipt = render(args.scene_dir, args.out_dir, only, args.scale,
                     args.timeout_ms)
    print(json.dumps(receipt, sort_keys=True))
    if receipt.get("rendered"):
        return 0 if receipt.get("ok") else 1
    return 3 if "requirement" in receipt else 1


if __name__ == "__main__":
    sys.exit(main())
