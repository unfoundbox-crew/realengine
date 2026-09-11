"""Camera aiming, generalized from 06_layout.py + render_views.py.

Seed logic: ``aim`` points a camera at a target via ``to_track_quat``,
and render_views.py switches ``scene.camera`` per view with per-view
resolution/framing. No view names, positions, or counts are hardcoded
here — every camera comes from a caller-supplied spec dict::

    {"name": ..., "pos": (x, y, z), "target": (x, y, z),
     "lens": 62, "ortho": False, "ortho_scale": 0.35,
     "shift_x": 0.0, "shift_y": 0.0}
"""
from __future__ import annotations


def aim_camera(cam, pos, target):
    """Place ``cam`` at ``pos`` looking at ``target``. Requires Blender."""
    from mathutils import Vector

    cam.location = pos
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat(
        "-Z", "Y").to_euler()
    return cam


def create_camera(name, pos, target, collections=None, lens=62.0,
                  ortho=False, ortho_scale=0.35, shift_x=0.0, shift_y=0.0,
                  clip_start=0.001, clip_end=100.0):
    """Create one camera object. Requires Blender (lazy bpy)."""
    import bpy

    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    if collections is not None:
        target_col = (collections.get("09_CAMERAS") if isinstance(
            collections, dict) else collections)
        target_col.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
    aim_camera(obj, pos, target)
    data.lens = lens
    data.clip_start = clip_start
    data.clip_end = clip_end
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    data.shift_x = shift_x
    data.shift_y = shift_y
    return obj


def aim_cameras(specs, collections=None):
    """Create/aim one camera per spec dict. Requires Blender.

    Existing objects with a matching name are re-aimed in place;
    missing ones are created. Returns {name: camera object}.
    """
    import bpy

    cams = {}
    for spec in specs:
        name = spec["name"]
        obj = bpy.data.objects.get(name)
        if obj is None:
            obj = create_camera(
                name, spec["pos"], spec["target"],
                collections=collections,
                lens=spec.get("lens", 62.0),
                ortho=spec.get("ortho", False),
                ortho_scale=spec.get("ortho_scale", 0.35),
                shift_x=spec.get("shift_x", 0.0),
                shift_y=spec.get("shift_y", 0.0),
                clip_start=spec.get("clip_start", 0.001),
                clip_end=spec.get("clip_end", 100.0),
            )
        else:
            aim_camera(obj, spec["pos"], spec["target"])
            if "lens" in spec:
                obj.data.lens = spec["lens"]
            if "shift_x" in spec:
                obj.data.shift_x = spec["shift_x"]
            if "shift_y" in spec:
                obj.data.shift_y = spec["shift_y"]
        cams[name] = obj
    return cams
