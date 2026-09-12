#!/usr/bin/env python3
"""Three.js backend: SCENE_SPEC.md (or build JSON) -> a standalone HTML scene.

Reuses web/build_web.py's slot contract (fail loud on any unbound slot or
surviving ``{{...}}``) with the generic template ``web/template_scene.html``.
Geometry stays code; every string is a slot; the scene itself travels as the
embedded build JSON that spec/scene_spec.py derived from the spec.

Outputs, all under ``--out-dir``:
    scene.html      the scene (open it, or drive it with ?view=CAM_Name)
    build.json      the pinned build dict both backends consume
    views.json      the render manifest (one row per named camera)
    SCENE_SPEC.md   copy of the source spec, when a .md was given

Usage:
    python3 web/build_scene.py <SCENE_SPEC.md|build.json> --out-dir DIR

Prints a one-line JSON receipt on stdout; logs go to stderr. Stdlib only.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "spec"))
sys.path.insert(0, str(REPO_ROOT / "web"))

import scene_spec  # noqa: E402
import build_web  # noqa: E402

THREE_VERSION = "0.170.0"
TEMPLATE = REPO_ROOT / "web/template_scene.html"


def log(msg):
    print("build_scene: %s" % msg, file=sys.stderr)


def load_source(path):
    """Return (build_dict, spec_markdown_or_None, hashes)."""
    text = Path(path).read_text(encoding="utf-8")
    if str(path).endswith(".json"):
        build = json.loads(text)
        return build, None, {
            "build_sha256": scene_spec.build_hash(build),
            "spec_sha256": build.get("spec_sha256", ""),
        }
    compiled = scene_spec.compile_spec(text)
    return compiled["build"], text, {
        "build_sha256": compiled["build_sha256"],
        "spec_sha256": compiled["spec_sha256"],
    }


def embed_json(obj):
    """Deterministic JSON safe to paste inside a <script> tag.

    Indented on purpose: build_web.py rejects any surviving ``{{``/``}}`` in
    its output, and compact JSON nests closing braces. Indentation also keeps
    ``<`` escaped so no ``</script`` can appear.
    """
    text = json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False)
    return text.replace("<", "\\u003c")


def views_manifest(build, hashes, html_name="scene.html"):
    labels = []
    for obj in build["objects"]:
        if obj["label"] and obj["label"] not in labels:
            labels.append(obj["label"])
    rows = []
    for view in build["views"]:
        rows.append({
            "name": view["name"],
            "camera": view["camera"],
            "output": view["output"],
            "res_x": view["res_x"],
            "res_y": view["res_y"],
            "url": "%s?view=%s&labels=1&subs=0&hud=0" % (html_name, view["camera"]),
        })
    return {
        "scene": build["scene"],
        "title": build["title"],
        "html": html_name,
        "build_sha256": hashes["build_sha256"],
        "spec_sha256": hashes["spec_sha256"],
        "ready_flag": "window.REALENGINE_READY",
        "labels": labels,
        "views": rows,
        "note": ("Open <html>?view=<camera>&hud=0 in any browser and capture at "
                 "res_x×res_y once window.REALENGINE_READY is true. "
                 "subs=0 drops label subtitles: the OCR gate reads names. "
                 "web/render_views.py does exactly this with Playwright."),
    }


def preset_for(build, hashes, manifest):
    subtitle = "%d objects · %d collections · %d cameras" % (
        len(build["objects"]), len(build["collections"]), len(build["cameras"]))
    default_view = build["cameras"][0]["name"] if build["cameras"] else ""
    return {
        "scene_title": build["title"],
        "scene_subtitle": subtitle,
        "scene_name": build["scene"],
        "background_hex": build["render"]["background"],
        "three_version": THREE_VERSION,
        "build_sha256": hashes["build_sha256"],
        "spec_sha256": hashes["spec_sha256"],
        "build_sha256_short": hashes["build_sha256"][:12],
        "spec_sha256_short": (hashes["spec_sha256"] or "-")[:12],
        "default_view": default_view,
        "scene_json": embed_json(build),
        "views_json": embed_json(manifest),
    }


def build_scene(source, out_dir, template=None):
    template_path = Path(template or TEMPLATE)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    build, spec_md, hashes = load_source(source)
    manifest = views_manifest(build, hashes)
    preset = preset_for(build, hashes, manifest)

    preset_path = out / "_slots.json"
    preset_path.write_text(scene_spec.canonical_json(preset), encoding="utf-8")
    html_path = out / "scene.html"
    # build_web.main exits non-zero on an unbound slot: that is the gate.
    # Its chatter goes to stderr so stdout stays a clean JSON receipt.
    with contextlib.redirect_stdout(sys.stderr):
        build_web.main(["build_web.py", str(preset_path), str(template_path),
                        str(html_path)])
    os.remove(preset_path)

    (out / "build.json").write_text(scene_spec.canonical_json(build), encoding="utf-8")
    (out / "views.json").write_text(scene_spec.canonical_json(manifest), encoding="utf-8")
    spec_out = None
    if spec_md is not None:
        spec_out = out / "SCENE_SPEC.md"
        spec_out.write_text(spec_md, encoding="utf-8")

    return {
        "ok": True,
        "backend": "web",
        "scene": build["scene"],
        "html": str(html_path),
        "build_json": str(out / "build.json"),
        "views_json": str(out / "views.json"),
        "spec_md": str(spec_out) if spec_out else None,
        "build_sha256": hashes["build_sha256"],
        "spec_sha256": hashes["spec_sha256"],
        "objects": len(build["objects"]),
        "cameras": [c["name"] for c in build["cameras"]],
        "labels": manifest["labels"],
        "bytes": html_path.stat().st_size,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="SCENE_SPEC.md or a build JSON")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--template", default=None)
    args = ap.parse_args(argv)

    receipt = build_scene(args.source, args.out_dir, args.template)
    log("%s (%d bytes, %d objects)" % (receipt["html"], receipt["bytes"],
                                       receipt["objects"]))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
