"""code-to-3d Blender entrypoint: spec -> .blend + QA PNGs.

Build order: collections -> materials -> cameras -> save .blend -> views.

Import-safe without Blender: ``bpy`` is imported only inside ``main``.
``python3 -c "import build"`` must pass on a machine with no bpy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Pure-python helper safe to import anywhere. Everything else is lazy.
from ctd_blender.materials import hex_to_linear  # noqa: F401  (re-export check)


DEFAULT_COLLECTIONS = [
    "00_REFERENCE", "01_HEAD", "02_BRAIN_CORTEX", "03_SUBCORTICAL",
    "04_FLOW_ARROWS", "05_LAYER_STACK", "06_CONTROL_LOOP",
    "07_LABELS", "08_LEGENDS", "09_CAMERAS", "10_LIGHTS",
]

DEFAULT_PALETTE = {
    "Frontal": ("#7EA6FF", 0.62),
    "Parietal": ("#82D6A4", 0.62),
    "Temporal": ("#F0C96C", 0.62),
    "Occipital": ("#A989D8", 0.62),
    "Head": ("#E8EEF3", 0.10),
}

DEFAULT_CAMERAS = [
    {"name": "CAM_Master", "pos": (-0.38, -0.52, 0.23),
     "target": (0.0, 0.0, 0.020)},
]


def load_spec(spec_path):
    """Load a JSON scene spec. Missing keys fall back to defaults.

    Spec shape (all keys optional)::

        {"scene": ..., "collections": [...], "palette": {name: spec},
         "cameras": [{name, pos, target, ...}], "views": [{...}]}
    """
    if spec_path is None:
        return {}
    text = Path(spec_path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"note": text}


def build(args):
    """Run the full build inside Blender. Imports bpy here, not at top."""
    import bpy  # noqa: F811  -- Blender only, lazy on purpose

    from ctd_blender.collections import ensure_collection_tree
    from ctd_blender.materials import build_material_table
    from ctd_blender.cameras import aim_cameras
    from ctd_blender.qa import collect_stats, render_view

    spec = load_spec(args.spec)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scene_name = spec.get("scene", "CTD_SCENE")
    scene = bpy.data.scenes.new(scene_name)
    scene.unit_settings.system = "METRIC"

    cols = ensure_collection_tree(
        scene, spec.get("collections", DEFAULT_COLLECTIONS))
    build_material_table(spec.get("palette", DEFAULT_PALETTE))
    cams = aim_cameras(spec.get("cameras", DEFAULT_CAMERAS), cols)

    blend_path = out_dir / (spec.get("blend_name", scene_name) + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    views = args.views.split(",") if args.views else spec.get("views", [])
    if isinstance(views, list) and views and isinstance(views[0], dict):
        # Views given as full render specs in the JSON spec.
        for view in views:
            render_view(out_dir / view["output"], view["camera"],
                        scene=scene,
                        res_x=view.get("res_x", 1600),
                        res_y=view.get("res_y", 1600),
                        samples=view.get("samples"))
    else:
        for name in [v for v in views if v]:
            cam = cams.get(name) or bpy.data.objects.get(name)
            if cam is None:
                print("CTD unknown view: %s" % name, file=sys.stderr)
                continue
            render_view(out_dir / ("%s.png" % name), cam, scene=scene)

    print("CTD_BUILD_DONE", json.dumps(collect_stats(scene)))
    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Build a .blend + QA views from a scene spec.")
    p.add_argument("--spec", default=None,
                   help="Path to JSON scene spec (optional; defaults used).")
    p.add_argument("--out-dir", default="out",
                   help="Directory for .blend + QA PNGs.")
    p.add_argument("--views", default="",
                   help="Comma-separated camera names to render.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
