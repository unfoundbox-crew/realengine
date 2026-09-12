#!/usr/bin/env python3
"""Zip a built scene into one shippable archive.

Collects whatever the scene directory actually holds -- scene.html,
build.json, views.json, SCENE_SPEC.md, renders/*.png -- into a single zip
with a manifest listing every member and its sha256. Nothing is invented:
a missing part is reported as missing, not faked.

Usage:
    python3 tools/export_scene.py --scene-dir DIR [--out PATH]
                                  [--format zip|html|png]

    --format html   copy scene.html out on its own (no archive)
    --format png    copy one render out (``--view CAM_Name``, default first)

Prints a one-line JSON receipt on stdout; logs go to stderr. Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

PARTS = ["scene.html", "build.json", "views.json", "SCENE_SPEC.md"]


def log(msg):
    print("export_scene: %s" % msg, file=sys.stderr)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(scene_dir):
    scene_dir = Path(scene_dir).resolve()
    members, missing = [], []
    for name in PARTS:
        p = scene_dir / name
        (members if p.exists() else missing).append(p if p.exists() else name)
    renders = sorted((scene_dir / "renders").glob("*.png")) \
        if (scene_dir / "renders").is_dir() else []
    members.extend(renders)
    return scene_dir, members, missing, renders


def export(scene_dir, out=None, fmt="zip", view=None):
    scene_dir, members, missing, renders = collect(scene_dir)
    if not members:
        return {"ok": False, "error": "nothing to export in %s" % scene_dir}

    stem = scene_dir.name
    build_path = scene_dir / "build.json"
    if build_path.exists():
        try:
            stem = json.loads(build_path.read_text(encoding="utf-8"))["scene"]
        except (ValueError, KeyError):
            pass

    if fmt == "html":
        src = scene_dir / "scene.html"
        if not src.exists():
            return {"ok": False, "error": "no scene.html in %s" % scene_dir}
        target = Path(out) if out else scene_dir / ("%s.html" % stem)
        shutil.copyfile(src, target)
        return {"ok": True, "format": "html", "path": str(target),
                "bytes": target.stat().st_size, "sha256": sha256_file(target)}

    if fmt == "png":
        if not renders:
            return {"ok": False, "format": "png",
                    "error": "no PNGs in %s/renders (run the views tool first)"
                             % scene_dir}
        chosen = renders[0]
        if view:
            match = [r for r in renders if r.stem == view or r.name == view]
            if not match:
                return {"ok": False, "format": "png",
                        "error": "no render named %s (have: %s)"
                                 % (view, ", ".join(r.stem for r in renders))}
            chosen = match[0]
        target = Path(out) if out else scene_dir / ("%s_%s.png" % (stem, chosen.stem))
        shutil.copyfile(chosen, target)
        return {"ok": True, "format": "png", "path": str(target),
                "view": chosen.stem, "bytes": target.stat().st_size,
                "sha256": sha256_file(target)}

    target = Path(out) if out else scene_dir / ("%s.zip" % stem)
    entries = []
    for path in members:
        arc = str(path.relative_to(scene_dir))
        entries.append({"path": arc, "bytes": path.stat().st_size,
                        "sha256": sha256_file(path)})
    manifest = {
        "scene": stem,
        "source_dir": str(scene_dir),
        "entries": sorted(entries, key=lambda e: e["path"]),
        "missing": sorted(m for m in missing if isinstance(m, str)),
    }
    # Fixed timestamps: the same inputs must produce the same archive bytes.
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(members, key=lambda p: str(p.relative_to(scene_dir))):
            info = zipfile.ZipInfo(str(path.relative_to(scene_dir)),
                                   date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("manifest.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        zf.writestr(info, json.dumps(manifest, indent=1, sort_keys=True) + "\n")

    return {
        "ok": True,
        "format": "zip",
        "path": str(target),
        "bytes": target.stat().st_size,
        "sha256": sha256_file(target),
        "entries": [e["path"] for e in manifest["entries"]] + ["manifest.json"],
        "missing": manifest["missing"],
        "renders": len(renders),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scene-dir", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--format", default="zip", choices=["zip", "html", "png"])
    ap.add_argument("--view", default=None, help="which render, for --format png")
    args = ap.parse_args(argv)

    receipt = export(args.scene_dir, args.out, args.format, args.view)
    if receipt.get("ok"):
        log("%s (%d bytes)" % (receipt["path"], receipt["bytes"]))
    else:
        log("FAILED: %s" % receipt.get("error"))
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
