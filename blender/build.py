"""code-to-3d Blender entrypoint: spec -> .blend + QA PNGs.

Build order: collections -> materials -> blockout -> cameras -> save .blend
-> views.

The spec is the build JSON that ``spec/scene_spec.py`` derives from
SCENE_SPEC.md -- the same file the web backend reads.

Headless invocation (Blender puts its own flags in sys.argv, so everything
after a bare ``--`` belongs to this script)::

    blender --background --python blender/build.py -- \
        --spec out/build.json --out-dir out/blender --views CAM_Master

Import-safe without Blender: ``bpy`` is imported only inside ``build``.
``python3 -c "import build"`` must pass on a machine with no bpy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Blender runs this file by path, so its own directory is not on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

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
    from ctd_blender.lighting import setup_world, three_point
    from ctd_blender.qa import collect_stats, render_view

    spec = load_spec(args.spec)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scene_name = spec.get("scene", "CTD_SCENE")
    scene = bpy.data.scenes.new(scene_name)
    scene.unit_settings.system = "METRIC"
    engine = args.engine or (spec.get("render") or {}).get("engine")
    if engine:
        # Engine ids drift between Blender versions (5.2 has BLENDER_EEVEE,
        # 4.x had BLENDER_EEVEE_NEXT). Try the alias before giving up.
        for candidate in (engine, engine.replace("_NEXT", ""), engine + "_NEXT"):
            try:
                scene.render.engine = candidate
                break
            except TypeError:
                continue
        else:
            print("CTD unknown engine: %s (left %s)"
                  % (engine, scene.render.engine), file=sys.stderr)

    cols = ensure_collection_tree(
        scene, spec.get("collections", DEFAULT_COLLECTIONS))
    mats = build_material_table(spec.get("palette", DEFAULT_PALETTE))
    if spec.get("objects"):
        from ctd_blender.blockout import build_blockout
        build_blockout(spec["objects"], cols, mats, scene=scene)
    render_cfg = spec.get("render") or {}
    setup_world(scene, render_cfg.get("background", "#F8FAFC"))
    three_point(scene, spec.get("extent", (1.0, 1.0, 1.0)),
                spec.get("center", (0.0, 0.0, 0.0)), cols)
    cams = aim_cameras(spec.get("cameras", DEFAULT_CAMERAS), cols)

    blend_path = out_dir / (spec.get("blend_name", scene_name) + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    views = args.views.split(",") if args.views else spec.get("views", [])
    if isinstance(views, list) and views and isinstance(views[0], dict):
        # Views given as full render specs in the JSON spec.
        for view in views:
            scale = args.res_scale
            render_view(out_dir / view["output"], view["camera"],
                        scene=scene,
                        res_x=max(64, int(view.get("res_x", 1600) * scale)),
                        res_y=max(64, int(view.get("res_y", 1600) * scale)),
                        samples=args.samples or view.get("samples"))
    else:
        for name in [v for v in views if v]:
            cam = cams.get(name) or bpy.data.objects.get(name)
            if cam is None:
                print("CTD unknown view: %s" % name, file=sys.stderr)
                continue
            render_view(out_dir / ("%s.png" % name), cam, scene=scene,
                        res_x=max(64, int(1600 * args.res_scale)),
                        res_y=max(64, int(1600 * args.res_scale)),
                        samples=args.samples)

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
    p.add_argument("--engine", default=None,
                   help="Render engine override, e.g. BLENDER_EEVEE_NEXT.")
    p.add_argument("--samples", type=int, default=None,
                   help="Render samples override (small = fast QA frames).")
    p.add_argument("--res-scale", type=float, default=1.0,
                   help="Scale every view's resolution (0.1 = tiny proof).")
    if argv is None:
        argv = script_argv()
    return p.parse_args(argv)


def script_argv(argv=None):
    """Our own args: everything after a bare ``--`` when Blender ran us."""
    argv = list(sys.argv[1:] if argv is None else argv)
    return argv[argv.index("--") + 1:] if "--" in argv else argv


def main(argv=None):
    args = parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
